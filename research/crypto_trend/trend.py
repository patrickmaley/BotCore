"""Daily trend-following rules, a perp-style backtest and its statistics. See PROTOCOL.md."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"
SOL_STUDY = HERE.parent / "sol_8h_green_short" / "data"

DAY_MS = 86_400_000
MS_8H = 8 * 3600 * 1000
ASSETS = ("SOL", "BTC", "ETH")
DISCOVERY_END_MS = int(pd.Timestamp("2025-01-01", tz="UTC").timestamp() * 1000)  # last discovery close
WARMUP_DAYS = 200
FEE = 0.0006  # per side, on notional
SMA_N = (10, 20, 30, 50, 100, 200)
DON_N = (10, 20, 30, 50, 100)
MOM_N = (7, 14, 28, 56, 112)
MODES = ("long_short", "long_flat")


def load_meta() -> dict:
    return json.loads((SOL_STUDY / "meta.json").read_text())


def borrow_rates() -> tuple[float, float]:
    """(long, short) borrow as a fraction of notional per hour, from the frozen Jupiter snapshot."""
    p = load_meta()["jupiter_perps_sol_pool_info"]
    return float(p["longBorrowRatePercent"]) / 100.0, float(p["shortBorrowRatePercent"]) / 100.0


def load_8h(asset: str) -> pd.DataFrame:
    path = SOL_STUDY / "binance_spot_SOLUSDT_8h.csv" if asset == "SOL" else DATA / f"binance_spot_{asset}USDT_8h.csv"
    df = pd.read_csv(path)[["open_time_ms", "open", "high", "low", "close"]]
    return df[df.open_time_ms + MS_8H <= load_meta()["t_end_ms"]].sort_values("open_time_ms").reset_index(drop=True)


def daily_bars(df8: pd.DataFrame, end_close_ms: int | None = None) -> pd.DataFrame:
    """One row per UTC day that has its last 8h bar. close_ms is the instant the day closes.

    exec_delayed is the close of the first 8h bar of the next day: the price 8 hours after the daily close.
    end_close_ms drops every day that closes after it, so discovery code cannot see the holdout.
    """
    d = df8.copy()
    d["day"] = d.open_time_ms // DAY_MS
    g = d.groupby("day")
    out = pd.DataFrame({
        "open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
        "bars": g.size(), "last_open_ms": g.open_time_ms.last(),
    }).reset_index()
    out = out[out.last_open_ms == out.day * DAY_MS + 2 * MS_8H].copy()
    out["close_ms"] = (out.day + 1) * DAY_MS
    first = d[d.open_time_ms % DAY_MS == 0].set_index("open_time_ms").close
    out["exec_delayed"] = out.close_ms.map(first)
    if end_close_ms is not None:
        out = out[out.close_ms <= end_close_ms].copy()
        # The delayed fill of the last kept day lies beyond the cut.
        out.loc[out.index[-1], "exec_delayed"] = np.nan
    return out.drop(columns=["last_open_ms"]).reset_index(drop=True)


def signals(close: np.ndarray) -> dict[str, np.ndarray]:
    """Every rule as an array of +1 / -1 / 0 (0 until the rule has enough history). No look-ahead."""
    c = pd.Series(close, dtype=float)
    out: dict[str, np.ndarray] = {}
    for n in SMA_N:
        ma = c.rolling(n).mean()
        out[f"sma_{n}"] = np.sign(c - ma).fillna(0.0).to_numpy()
    for n in DON_N:
        hi, lo = c.rolling(n).max(), c.rolling(n).min()
        raw = pd.Series(np.where(c >= hi, 1.0, np.where(c <= lo, -1.0, np.nan)))
        raw[hi.isna()] = np.nan
        out[f"don_{n}"] = raw.ffill().fillna(0.0).to_numpy()
    for n in MOM_N:
        out[f"mom_{n}"] = np.sign(c - c.shift(n)).fillna(0.0).to_numpy()
    return out


def vote(sig: dict[str, np.ndarray]) -> np.ndarray:
    return np.sign(np.sum(list(sig.values()), axis=0))


def apply_mode(sig: np.ndarray, mode: str) -> np.ndarray:
    if mode == "long_short":
        return sig.copy()
    if mode == "long_flat":
        return np.maximum(sig, 0.0)
    if mode == "short_flat":
        return np.minimum(sig, 0.0)
    raise ValueError(mode)


def backtest(close: np.ndarray, pos: np.ndarray, start: int, end: int | None = None, exec_px: np.ndarray | None = None,
             fee: float = FEE, borrow_long_h: float = 0.0, borrow_short_h: float = 0.0,
             high: np.ndarray | None = None, low: np.ndarray | None = None) -> tuple[np.ndarray, list[dict]]:
    """Trade pos[t] from the close of day t, for t in [start, end). Returns equity over [start, end] and the trades.

    A position has notional equal to equity when it is opened and is linear in price until it is closed,
    like a perp. exec_px[t] is the fill price for a change decided at close t (default: that close).
    Equity is marked at each daily close before any trade on that day.
    """
    end = len(close) - 1 if end is None else end
    px_fill = close if exec_px is None else exec_px
    eq = np.empty(end - start + 1)
    e = 1.0
    side, p0, e0, notional, t0 = 0, np.nan, np.nan, 0.0, 0
    worst = 0.0
    trades: list[dict] = []
    for t in range(start, end + 1):
        if side:
            rate = borrow_long_h if side > 0 else borrow_short_h
            carry = notional * rate * 24.0 * (t - t0)
            e = e0 + side * notional * (close[t] / p0 - 1.0) - carry
            if high is not None and t > t0:
                worst = max(worst, (p0 / low[t] - 1.0) if side > 0 else (high[t] / p0 - 1.0))
        eq[t - start] = e
        if t == end or e <= 0:
            if e <= 0:
                eq[t - start:] = 0.0
            break
        new = int(pos[t])
        if new != side and np.isfinite(px_fill[t]):
            px = px_fill[t]
            if side:
                e = e0 + side * notional * (px / p0 - 1.0) - carry - fee * notional * px / p0
                trades.append({"side": side, "entry_idx": t0, "exit_idx": t, "entry": p0, "exit": px, "days": t - t0,
                               "ret": e / notional - 1.0, "worst_adverse": worst, "open": False})
            side, worst = new, 0.0
            if side:
                notional, p0, t0 = e, px, t
                e0 = e - fee * notional
                e = e0
    if side and e > 0:
        trades.append({"side": side, "entry_idx": t0, "exit_idx": end, "entry": p0, "exit": close[end], "days": end - t0,
                       "ret": eq[-1] / notional - 1.0, "worst_adverse": worst, "open": True})
    return eq, trades


def sharpe(eq: np.ndarray) -> float:
    """Annualised Sharpe ratio of daily returns. NaN if equity was wiped out."""
    if eq.min() <= 0:
        return float("nan")
    r = eq[1:] / eq[:-1] - 1.0
    sd = r.std(ddof=1)
    return float(r.mean() / sd * np.sqrt(365.0)) if sd > 0 else 0.0


def max_drawdown(eq: np.ndarray) -> float:
    return float(np.max(1.0 - eq / np.maximum.accumulate(eq)))


def stats(eq: np.ndarray, trades: list[dict]) -> dict:
    days = len(eq) - 1
    bust = bool(eq.min() <= 0)
    live = eq[: int(np.argmax(eq <= 0)) + 1] if bust else eq
    r = live[1:] / live[:-1] - 1.0
    r = r[np.isfinite(r)]
    tr = pd.DataFrame(trades)
    closed = tr[~tr.open] if len(tr) else tr
    wins = closed.ret[closed.ret > 0] if len(closed) else pd.Series(dtype=float)
    losses = closed.ret[closed.ret <= 0] if len(closed) else pd.Series(dtype=float)
    in_market = tr.days.sum() if len(tr) else 0
    return {
        "days": days, "wiped_out": bust, "total_return": eq[-1] - 1.0,
        "cagr": eq[-1] ** (365.0 / days) - 1.0 if eq[-1] > 0 else -1.0,
        "ann_vol": float(r.std(ddof=1) * np.sqrt(365.0)), "sharpe": sharpe(eq), "max_drawdown": max_drawdown(eq),
        "trades": len(closed), "win_rate": float((closed.ret > 0).mean()) if len(closed) else np.nan,
        "avg_win": float(wins.mean()) if len(wins) else np.nan, "avg_loss": float(losses.mean()) if len(losses) else np.nan,
        "best_trade": float(closed.ret.max()) if len(closed) else np.nan,
        "worst_trade": float(closed.ret.min()) if len(closed) else np.nan,
        "median_days_held": float(closed.days.median()) if len(closed) else np.nan,
        "time_in_market": in_market / days if days else np.nan,
        "worst_adverse_move": float(tr.worst_adverse.max()) if len(tr) else np.nan,
    }


def sharpe_ci(eq: np.ndarray, block: int = 30, reps: int = 4000, seed: int = 7) -> tuple[float, float]:
    """95% interval for the Sharpe ratio from a circular block bootstrap of daily returns."""
    r = eq[1:] / eq[:-1] - 1.0
    n = len(r)
    rng = np.random.default_rng(seed)
    k = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(reps, k))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    s = r[idx.reshape(reps, -1)[:, :n]]
    sh = s.mean(axis=1) / s.std(axis=1, ddof=1) * np.sqrt(365.0)
    return float(np.quantile(sh, 0.025)), float(np.quantile(sh, 0.975))


def shift_test(close: np.ndarray, pos: np.ndarray, start: int, end: int, reps: int = 500, seed: int = 11, **kw) -> float:
    """Share of randomly time-shifted copies of the same position series with a Sharpe at least as high.

    Shifting keeps how often and how long the rule is long or short but breaks its link to the price,
    so it measures timing rather than a lucky average position.
    """
    actual = sharpe(backtest(close, pos, start, end, **kw)[0])
    seg = pos[start:end].copy()
    n = len(seg)
    rng = np.random.default_rng(seed)
    hits = 0
    for k in rng.integers(30, n - 30, size=reps):
        p = pos.copy()
        p[start:end] = np.roll(seg, int(k))
        hits += sharpe(backtest(close, p, start, end, **kw)[0]) >= actual
    return (1 + hits) / (1 + reps)
