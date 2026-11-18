"""Run the full X x cost x strategy x period grid for one stage.

stage 'discovery'     only trades entered before the last 90 days exist in memory.
stage 'confirmation'  every period that reaches into the last 90 days.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib import (
    BASE_COST_BPS,
    BODY_BINS,
    CONFIRM_DAYS,
    COSTS_BPS,
    X_GRID,
    build_pairs,
    load_8h,
    load_meta,
    net_return,
    period_masks,
    random_half_stats,
    same_size_random_rank,
    simulate,
    strategy_defs,
    trade_stats,
)

RANDOM_DRAWS = 1000
RANDOM_SEED = 20261118
VENUES = ["binance", "okx", "kucoin"]
ENTRY_MODES = ["c_close", "n_open"]
BORROW_STRESS_BPS = 8.0  # 0.01%/h for 8h, the cap of Jupiter's original utilisation x 0.01%/h rule
RANDOM_PERIODS = {"discovery", "confirmation (last 90d)", "full history", "last 365d"}


def borrow_live_bps(meta: dict, side: str) -> float:
    key = "shortBorrowRatePercent" if side == "short" else "longBorrowRatePercent"
    return float(meta["jupiter_perps_sol_pool_info"][key]) * 8.0 * 100.0  # %/h -> bps per 8h


def load_pairs(venue: str, stage: str, meta: dict) -> pd.DataFrame:
    pairs = build_pairs(load_8h(venue))
    if stage == "discovery":
        conf_start = meta["t_end_ms"] - CONFIRM_DAYS * 86_400_000
        pairs = pairs[pairs["entry_time_ms"] < conf_start].reset_index(drop=True)
    return pairs


def run_grid(stage: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    meta = load_meta()
    rows: list[dict] = []
    tests: list[dict] = []
    for venue in VENUES:
        pairs = load_pairs(venue, stage, meta)
        masks = period_masks(pairs, meta["t_end_ms"], stage)
        strats = strategy_defs(pairs)
        body = pairs["body_pct"].to_numpy()
        for entry_mode in ENTRY_MODES:
            for x in X_GRID:
                sims = {side: simulate(pairs, x, side, entry_mode) for side in ("short", "long")}
                for pname, pmask in masks.items():
                    n_bars = int(pmask.sum())
                    base = {"venue": venue, "entry_mode": entry_mode, "period": pname, "x": x}
                    for sname, (side, smask) in strats.items():
                        sim = sims[side]
                        m = pmask & smask
                        gross, ratio, outc = (
                            sim["gross"].to_numpy()[m],
                            sim["exit_ratio"].to_numpy()[m],
                            sim["outcome"].to_numpy()[m],
                        )
                        for cost in COSTS_BPS:
                            net = net_return(gross, ratio, cost)
                            rows.append({**base, "strategy": sname, "body_bin": "all", "cost_bps": cost, "borrow_bps": 0.0,
                                         **trade_stats(net, outc, n_bars)})
                        for b in (borrow_live_bps(meta, side), BORROW_STRESS_BPS):
                            net = net_return(gross, ratio, BASE_COST_BPS, b)
                            rows.append({**base, "strategy": sname, "body_bin": "all", "cost_bps": BASE_COST_BPS,
                                         "borrow_bps": b, **trade_stats(net, outc, n_bars)})
                        if sname in ("green_short", "green_long_flipped"):
                            for label, lo, hi in BODY_BINS:
                                bm = (body[m] >= lo) & (body[m] < hi)
                                for cost in COSTS_BPS:
                                    net = net_return(gross[bm], ratio[bm], cost)
                                    rows.append({**base, "strategy": sname, "body_bin": label, "cost_bps": cost,
                                                 "borrow_bps": 0.0, **trade_stats(net, outc[bm], n_bars)})

                    if venue == "binance" and pname in RANDOM_PERIODS:
                        sim = sims["short"]
                        g_all, r_all, o_all = (
                            sim["gross"].to_numpy()[pmask],
                            sim["exit_ratio"].to_numpy()[pmask],
                            sim["outcome"].to_numpy()[pmask],
                        )
                        for cost in COSTS_BPS:
                            net_all = net_return(g_all, r_all, cost)
                            rows.append({**base, "strategy": "random_half_short", "body_bin": "all", "cost_bps": cost,
                                         "borrow_bps": 0.0,
                                         **random_half_stats(net_all, o_all, n_bars, RANDOM_DRAWS, RANDOM_SEED)})
                        for b in (borrow_live_bps(meta, "short"), BORROW_STRESS_BPS):
                            net_all = net_return(g_all, r_all, BASE_COST_BPS, b)
                            rows.append({**base, "strategy": "random_half_short", "body_bin": "all",
                                         "cost_bps": BASE_COST_BPS, "borrow_bps": b,
                                         **random_half_stats(net_all, o_all, n_bars, RANDOM_DRAWS, RANDOM_SEED)})

                        # Head-to-head tests at the base cost.
                        net_all = net_return(g_all, r_all, BASE_COST_BPS)
                        gm = pairs["green"].to_numpy()[pmask]
                        rm = pairs["red"].to_numpy()[pmask]
                        g, r = net_all[gm], net_all[rm]
                        diff = g.mean() - r.mean()
                        se = np.sqrt(g.var(ddof=1) / len(g) + r.var(ddof=1) / len(r))
                        tests.append({
                            **base,
                            "green_mean": g.mean(), "red_mean": r.mean(), "all_mean": net_all.mean(),
                            "green_minus_red": diff, "diff_ci_lo": diff - 1.96 * se, "diff_ci_hi": diff + 1.96 * se,
                            "diff_t": diff / se,
                            "p_green_beats_random_same_size": same_size_random_rank(
                                net_all, int(gm.sum()), g.mean(), 5000, RANDOM_SEED),
                        })
    return pd.DataFrame(rows), pd.DataFrame(tests)
