"""Variations on the fixed-dollar green-candle short: stop-loss, longer holds, adding to a loser.

Every variant shorts 40 SOL at 15x at the close of a green 8h candle and is
simulated minute by minute (path_sim.py). One position at a time: a signal
that arrives while a position is still open is skipped. Costs are 12 bps round
trip plus the borrow rate fetched with the data, charged for the time held.

These are many variations tried on data that has already been read. Some will
look good by chance. The table reports each one after red candles as well, and
over three windows, so a lucky window is visible as such.

    python3 05_variants.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib import CACHE, RESULTS, build_pairs, load_8h, load_meta
from path_sim import Minutes, run_trade

SIZE_SOL = 40.0
LEVERAGE = 15.0
DAY_MS = 86_400_000
TARGETS = (0.5, 1.0)


def variants() -> list[dict]:
    v = []
    for t in TARGETS:
        v.append({"group": "baseline", "label": f"${t:g} target, next candle only, no stop", "target": t})
        for s in (0.5, 1.0, 2.0, 3.0):
            v.append({"group": "stop-loss", "label": f"${t:g} target, ${s:g} stop, next candle only", "target": t, "stop": s})
        for h in (2, 3):
            v.append({"group": "hold longer", "label": f"${t:g} target, hold up to {h} candles", "target": t, "hold_candles": h})
        v.append({"group": "hold longer", "label": f"${t:g} target, hold until hit or liquidated", "target": t, "hold_candles": None})
        for s in ((0.5, 1.0) if t == 0.5 else (1.0, 2.0)):
            v.append({"group": "target or stop, no time limit", "label": f"${t:g} target, ${s:g} stop, no time limit",
                      "target": t, "stop": s, "hold_candles": None})
        for a in (1.0, 2.0):
            v.append({"group": "add to loser", "label": f"${t:g} target, add 40 SOL at +${a:g}, next candle only", "target": t, "add": a})
    return v


def run_signals(m: Minutes, sig: pd.DataFrame, borrow: float, **kw) -> pd.DataFrame:
    rows, busy_until, skipped = [], 0, 0
    for t_entry, entry in zip(sig.entry_time_ms.to_numpy(), sig.close.to_numpy()):
        if t_entry < busy_until:
            skipped += 1
            continue
        r = run_trade(m, int(t_entry), float(entry), size=SIZE_SOL, leverage=LEVERAGE, borrow_per_hour=borrow, **kw)
        if r is None:
            continue
        busy_until = r["exit_time_ms"]
        rows.append({"entry_time_ms": int(t_entry), "entry": float(entry), **r})
    out = pd.DataFrame(rows)
    out.attrs["skipped"] = skipped
    return out


def stats(tr: pd.DataFrame, prefix: str = "") -> dict:
    n = len(tr)
    if n == 0:
        return {prefix + "trades": 0}
    usd = tr.usd
    win, loss = usd[usd > 0], usd[usd <= 0]
    se = usd.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    d = {
        "trades": n,
        "target_hit": (tr.outcome == "tp").mean(),
        "profitable": (usd > 0).mean(),
        "breakeven_win_rate": -loss.mean() / (win.mean() - loss.mean()) if len(win) and len(loss) else np.nan,
        "avg_win_usd": win.mean(), "avg_loss_usd": loss.mean(),
        "mean_usd": usd.mean(), "ci_lo": usd.mean() - 1.96 * se, "ci_hi": usd.mean() + 1.96 * se,
        "sum_usd": usd.sum(), "worst_usd": usd.min(),
        "stopped": int((tr.outcome == "stop").sum()), "liquidated": int((tr.outcome == "liquidated").sum()),
        "expired": int((tr.outcome == "expire").sum()), "added": int(tr.added.sum()),
        "ambiguous_minutes": int(tr.ambiguous_minute.sum()),
        "median_hold_hours": tr.hold_hours.median(), "max_hold_days": tr.hold_hours.max() / 24.0,
    }
    return {prefix + k: v for k, v in d.items()}


def check_against_8h_rule(m: Minutes, green: pd.DataFrame, te: int) -> None:
    """With no borrow, the minute path must reproduce the 8h-candle result for the plain one-dollar rule."""
    ref = pd.read_csv(RESULTS / "leverage_15x_40sol_summary.csv")
    ref = ref[ref.price_band == "all"].set_index("sample")
    tr = run_signals(m, green, 0.0, target=1.0)
    for name, t0 in (("last 90d", te - 90 * DAY_MS), ("last 365d", te - 365 * DAY_MS)):
        s = tr[tr.entry_time_ms >= t0]
        r = ref.loc[name]
        assert len(s) == r.trades and int((s.outcome == "liquidated").sum()) == r.liquidated, name
        assert abs((s.outcome == "tp").mean() - r.target_hit_before_liquidation) < 1e-12, name
        assert abs(s.usd.sum() - r.sum_usd) < 0.005 * abs(r.sum_usd), (name, s.usd.sum(), r.sum_usd)


def main() -> None:
    meta = load_meta()
    te = meta["t_end_ms"]
    borrow = float(meta["jupiter_perps_sol_pool_info"]["shortBorrowRatePercent"]) / 100.0
    m1 = pd.read_parquet(CACHE / "binance_spot_SOLUSDT_1m.parquet")
    m = Minutes(*(m1[c].to_numpy() for c in ("open_time_ms", "open", "high", "low", "close")))
    pairs = build_pairs(load_8h("binance"))
    green, red = pairs[pairs["green"]], pairs[pairs["red"]]
    check_against_8h_rule(m, green, te)

    starts = {"last 90d": te - 90 * DAY_MS, "last 365d": te - 365 * DAY_MS, "full history": 0}
    rows = []
    for v in variants():
        kw = {k: v[k] for k in ("target", "stop", "hold_candles", "add") if k in v}
        g, r = run_signals(m, green, borrow, **kw), run_signals(m, red, borrow, **kw)
        for name, t0 in starts.items():
            gs, rs = g[g.entry_time_ms >= t0], r[r.entry_time_ms >= t0]
            red_stats = stats(rs, "red_")
            rows.append({"group": v["group"], "variant": v["label"], "target": v["target"], "stop": v.get("stop"),
                         "hold_candles": "no limit" if v.get("hold_candles", 1) is None else v.get("hold_candles", 1),
                         "add": v.get("add"), "sample": name,
                         "signals": int((green.entry_time_ms >= t0).sum()), **stats(gs),
                         **{k: red_stats.get(k) for k in ("red_trades", "red_profitable", "red_mean_usd", "red_sum_usd")}})
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "variants_summary.csv", index=False)

    pd.set_option("display.width", 260, "display.max_columns", 40, "display.max_colwidth", 60)
    cols = ["variant", "trades", "target_hit", "profitable", "breakeven_win_rate", "avg_win_usd", "avg_loss_usd", "mean_usd",
            "ci_lo", "ci_hi", "sum_usd", "worst_usd", "stopped", "liquidated", "red_mean_usd", "red_sum_usd"]
    for name in starts:
        print(f"\n== {name} ==")
        print(out[out["sample"] == name][cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
