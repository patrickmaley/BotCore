"""Trade rule, cost model and trade statistics for the SOL 8h green-candle short.

Everything here is a pure function of candle arrays so the rule can be unit
tested on hand-built candles (see test_rules.py).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CACHE = HERE / "cache"
RESULTS = HERE / "results"

X_GRID = [0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0]
COSTS_BPS = [0, 6, 12, 20, 40]
BASE_COST_BPS = 12
MS_8H = 8 * 3600 * 1000
CONFIRM_DAYS = 90
BODY_BINS = [("<1%", 0.0, 1.0), ("1-3%", 1.0, 3.0), ("3-6%", 3.0, 6.0), (">=6%", 6.0, np.inf)]

VENUE_FILES = {
    "binance": "binance_spot_SOLUSDT_8h.csv",
    "okx": "okx_spot_SOL-USDT_8h_from_1h.csv",
    "kucoin": "kucoin_spot_SOL-USDT_8h.csv",
}


def load_meta() -> dict:
    return json.loads((DATA / "meta.json").read_text())


def load_8h(venue: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / VENUE_FILES[venue])
    if "complete" in df.columns:
        df = df[df["complete"]]
    df = df[["open_time_ms", "open", "high", "low", "close"]].sort_values("open_time_ms")
    return df.reset_index(drop=True)


def build_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (signal candle C, next candle N). N must be the very next 8h bar."""
    d = df.copy()
    for c in ["open_time_ms", "open", "high", "low", "close"]:
        d["n_" + c] = d[c].shift(-1)
    d = d[d["n_open_time_ms"] == d["open_time_ms"] + MS_8H].copy()
    d["n_open_time_ms"] = d["n_open_time_ms"].astype("int64")
    d["entry_time_ms"] = d["n_open_time_ms"]
    d["body_pct"] = (d["close"] / d["open"] - 1.0) * 100.0
    d["green"] = d["close"] > d["open"]
    d["red"] = d["close"] < d["open"]
    return d.reset_index(drop=True)


def simulate(pairs: pd.DataFrame, x_pct: float, side: str = "short", entry_mode: str = "c_close") -> pd.DataFrame:
    """Apply the one-candle take-profit rule to every row of `pairs`.

    side        'short': cover X% below entry.  'long': sell X% above entry.
    entry_mode  'c_close': enter at C's close.  'n_open': enter at N's open.

    outcome: 'gap' (N opened through the take-profit, filled at N's open),
             'tp'  (N's extreme touched it, filled at the limit price),
             'expire' (never touched, closed at N's close).
    """
    entry = (pairs["close"] if entry_mode == "c_close" else pairs["n_open"]).to_numpy(float)
    n_open = pairs["n_open"].to_numpy(float)
    n_close = pairs["n_close"].to_numpy(float)
    if side == "short":
        tp = entry * (1.0 - x_pct / 100.0)
        gap = n_open <= tp
        touch = ~gap & (pairs["n_low"].to_numpy(float) <= tp)
    elif side == "long":
        tp = entry * (1.0 + x_pct / 100.0)
        gap = n_open >= tp
        touch = ~gap & (pairs["n_high"].to_numpy(float) >= tp)
    else:
        raise ValueError(side)
    exit_px = np.where(gap, n_open, np.where(touch, tp, n_close))
    gross = (entry - exit_px) / entry if side == "short" else (exit_px - entry) / entry
    return pd.DataFrame(
        {
            "entry": entry,
            "tp": tp,
            "exit": exit_px,
            "outcome": np.where(gap, "gap", np.where(touch, "tp", "expire")),
            "gross": gross,
            "exit_ratio": exit_px / entry,
        },
        index=pairs.index,
    )


def net_return(gross: np.ndarray, exit_ratio: np.ndarray, cost_bps: float, borrow_bps: float = 0.0) -> np.ndarray:
    """Round-trip cost split half/half, each half charged on that leg's notional.

    Entry notional is 1. Exit notional is exit/entry. Borrow is a flat charge
    on entry notional for the full 8 hours.
    """
    half = cost_bps / 2.0 / 1e4
    return gross - half * (1.0 + exit_ratio) - borrow_bps / 1e4


def max_drawdown(net: np.ndarray) -> float:
    if len(net) == 0:
        return np.nan
    eq = np.concatenate([[1.0], np.cumprod(1.0 + net)])
    peak = np.maximum.accumulate(eq)
    return float(np.max(1.0 - eq / peak))


def trade_stats(net: np.ndarray, outcome: np.ndarray, n_bars: int) -> dict:
    n = len(net)
    if n == 0:
        return {"signals": 0}
    wins = net[net > 0]
    losses = net[net <= 0]
    sd = float(np.std(net, ddof=1)) if n > 1 else np.nan
    se = sd / np.sqrt(n) if n > 1 else np.nan
    mean = float(np.mean(net))
    gl = float(-losses.sum())
    return {
        "signals": n,
        "tp_share": float(np.mean(outcome != "expire")),
        "gap_share": float(np.mean(outcome == "gap")),
        "expire_share": float(np.mean(outcome == "expire")),
        "mean": mean,
        "median": float(np.median(net)),
        "win_rate": float(np.mean(net > 0)),
        "avg_win": float(wins.mean()) if len(wins) else np.nan,
        "avg_loss": float(losses.mean()) if len(losses) else np.nan,
        "profit_factor": float(wins.sum() / gl) if gl > 0 else np.inf,
        "max_dd": max_drawdown(net),
        "final_equity": float(np.prod(1.0 + net)),
        "bars_in_position": n / n_bars if n_bars else np.nan,
        "ci_lo": mean - 1.96 * se,
        "ci_hi": mean + 1.96 * se,
        "t_stat": mean / se if se and se > 0 else np.nan,
        "sum": float(net.sum()),
    }


def period_masks(pairs: pd.DataFrame, t_end_ms: int, stage: str) -> dict[str, np.ndarray]:
    """Boolean masks over `pairs`, keyed by period label. A trade belongs to the
    period that contains its entry time (C's close).

    stage 'discovery' never returns a mask that reaches into the last 90 days.
    """
    et = pairs["entry_time_ms"].to_numpy()
    day = 86_400_000
    conf_start = t_end_ms - CONFIRM_DAYS * day
    years = pd.to_datetime(et, unit="ms", utc=True).year.to_numpy()
    disc = et < conf_start
    masks: dict[str, np.ndarray] = {}
    if stage == "discovery":
        masks["discovery"] = disc
        for y in sorted(set(years[disc])):
            label = str(y) if not ((years == y) & ~disc).any() else f"{y} (to cutoff)"
            masks[label] = disc & (years == y)
    elif stage == "confirmation":
        masks["confirmation (last 90d)"] = ~disc
        masks["full history"] = np.ones(len(et), bool)
        masks["last 365d"] = et >= t_end_ms - 365 * day
        for y in sorted(set(years)):
            masks[str(y)] = years == y
    else:
        raise ValueError(stage)
    return masks


def strategy_defs(pairs: pd.DataFrame) -> dict[str, tuple[str, np.ndarray]]:
    """name -> (side, row mask). The random-half baseline is handled separately."""
    allm = np.ones(len(pairs), bool)
    return {
        "green_short": ("short", pairs["green"].to_numpy()),
        "red_short": ("short", pairs["red"].to_numpy()),
        "all_short": ("short", allm),
        "green_long_flipped": ("long", pairs["green"].to_numpy()),
    }


def random_half_stats(
    net: np.ndarray, outcome: np.ndarray, n_bars: int, n_draws: int, seed: int
) -> dict:
    """Short a random half of the candles in the period. Average every statistic
    over `n_draws` draws and keep the spread of the mean trade return."""
    rng = np.random.default_rng(seed)
    n = len(net)
    k = n // 2
    acc: dict[str, list[float]] = {}
    for _ in range(n_draws):
        idx = np.sort(rng.choice(n, size=k, replace=False))
        s = trade_stats(net[idx], outcome[idx], n_bars)
        for key, v in s.items():
            acc.setdefault(key, []).append(v)
    out = {key: float(np.mean(v)) for key, v in acc.items()}
    means = np.array(acc["mean"])
    out["signals"] = k
    # For this baseline the interval is the 2.5-97.5 percentile of the mean across draws.
    out["ci_lo"], out["ci_hi"] = float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
    return out


def same_size_random_rank(net_all: np.ndarray, k: int, observed_mean: float, n_draws: int, seed: int) -> float:
    """Share of random k-candle subsets whose mean short return is >= the observed mean.
    This is a one-sided p-value for 'green candles are a better short than random candles'."""
    rng = np.random.default_rng(seed)
    n = len(net_all)
    hits = 0
    for _ in range(n_draws):
        if net_all[rng.choice(n, size=k, replace=False)].mean() >= observed_mean:
            hits += 1
    return (hits + 1) / (n_draws + 1)
