"""Stage 2. Apply the locked X to the last 90 days once, then fill in the rest of the report.

Refuses to run until stage 1 has written results/chosen_x.json.

Order of work:
  1. The single confirmation read: locked X, 12 bps, green short next to every baseline.
  2. The full grid for every period that reaches into the last 90 days
     (confirmation slice, full history, last 365 days, calendar years).
  3. Adverse excursion and holding time for the locked X from Binance 1m bars.
  4. Cross-venue take-profit agreement.
  5. The last 30 green-candle shorts in America/Phoenix time.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from grid import BORROW_STRESS_BPS, borrow_live_bps, run_grid
from lib import (
    BASE_COST_BPS,
    CACHE,
    CONFIRM_DAYS,
    RESULTS,
    X_GRID,
    build_pairs,
    load_8h,
    load_meta,
    net_return,
    simulate,
)

BOOT_DRAWS = 20_000
SEED = 20261118


def headline(grid: pd.DataFrame, tests: pd.DataFrame, x: float, meta: dict) -> dict:
    period = "confirmation (last 90d)"
    out: dict = {"x_pct": x, "cost_bps": BASE_COST_BPS, "period": period}
    for mode in ("c_close", "n_open"):
        g = grid[(grid.venue == "binance") & (grid.entry_mode == mode) & (grid.period == period)
                 & (grid.x == x) & (grid.body_bin == "all") & (grid.cost_bps == BASE_COST_BPS)
                 & (grid.borrow_bps == 0)].set_index("strategy")
        keep = ["signals", "tp_share", "expire_share", "mean", "median", "win_rate", "profit_factor", "max_dd",
                "ci_lo", "ci_hi", "sum"]
        res = {s: {k: float(g.loc[s, k]) for k in keep} for s in g.index}
        gs = res["green_short"]["mean"]
        baselines = {s: res[s]["mean"] for s in res if s != "green_short"}
        t = tests[(tests.venue == "binance") & (tests.entry_mode == mode) & (tests.period == period)
                  & (tests.x == x)].iloc[0]
        out[mode] = {
            "strategies": res,
            "green_short_profitable_after_12bps": bool(gs > 0),
            "green_short_beats_every_baseline": bool(all(gs > v for v in baselines.values())),
            "baselines_beaten": [s for s, v in baselines.items() if gs > v],
            "baselines_not_beaten": [s for s, v in baselines.items() if gs <= v],
            "green_minus_red": float(t["green_minus_red"]),
            "green_minus_red_ci": [float(t["diff_ci_lo"]), float(t["diff_ci_hi"])],
            "p_green_beats_random_same_size": float(t["p_green_beats_random_same_size"]),
        }
    return out


def excursions(x: float, meta: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-trade adverse excursion and holding time for the green short, from 1m bars."""
    pairs = build_pairs(load_8h("binance"))
    pairs = pairs[pairs["green"]].reset_index(drop=True)
    m1 = pd.read_parquet(CACHE / "binance_spot_SOLUSDT_1m.parquet")
    t1 = m1["open_time_ms"].to_numpy()
    hi, lo, op = m1["high"].to_numpy(), m1["low"].to_numpy(), m1["open"].to_numpy()
    conf_start = meta["t_end_ms"] - CONFIRM_DAYS * 86_400_000
    rows = []
    for mode in ("c_close", "n_open"):
        sim = simulate(pairs, x, "short", mode)
        for i in range(len(pairs)):
            t0 = int(pairs.at[i, "n_open_time_ms"])
            a, b = np.searchsorted(t1, t0), np.searchsorted(t1, t0 + 8 * 3600 * 1000)
            entry, tp, outcome = sim.at[i, "entry"], sim.at[i, "tp"], sim.at[i, "outcome"]
            h, l, o = hi[a:b], lo[a:b], op[a:b]
            if outcome == "gap":
                mae_incl = mae_excl = 0.0
                hold = 0
                agree = True
            else:
                hit = np.flatnonzero(l <= tp)
                agree = (len(hit) > 0) == (outcome == "tp")
                if outcome == "tp" and len(hit):
                    k = int(hit[0])
                    # The high and the low of the fill minute cannot be ordered, so bracket it.
                    mae_incl = h[: k + 1].max() / entry - 1.0
                    mae_excl = max(h[:k].max() if k else o[0], o[k]) / entry - 1.0
                    hold = k + 1
                else:
                    mae_incl = mae_excl = (h.max() if len(h) else pairs.at[i, "n_high"]) / entry - 1.0
                    hold = 480
            rows.append({
                "entry_mode": mode,
                "entry_time_ms": int(pairs.at[i, "entry_time_ms"]),
                "sample": "confirmation" if pairs.at[i, "entry_time_ms"] >= conf_start else "discovery",
                "outcome": outcome,
                "mae_incl": max(mae_incl, 0.0),
                "mae_excl": max(mae_excl, 0.0),
                "hold_min": hold,
                "minute_path_agrees_with_8h": agree,
            })
    tr = pd.DataFrame(rows)

    summ = []
    for mode in ("c_close", "n_open"):
        for sample in ("discovery", "confirmation", "full history"):
            base = tr[(tr.entry_mode == mode) & ((tr["sample"] == sample) | (sample == "full history"))]
            for label, sub in (("all", base), ("take-profit hit", base[base.outcome != "expire"]),
                               ("expired", base[base.outcome == "expire"])):
                if len(sub) == 0:
                    continue
                summ.append({
                    "entry_mode": mode, "sample": sample, "subset": label, "trades": len(sub),
                    "mae_median": sub.mae_incl.median(), "mae_p90": sub.mae_incl.quantile(0.9),
                    "mae_p99": sub.mae_incl.quantile(0.99), "mae_max": sub.mae_incl.max(),
                    "mae_median_excl_fill_minute": sub.mae_excl.median(),
                    "mae_p90_excl_fill_minute": sub.mae_excl.quantile(0.9),
                    "hold_min_median": sub.hold_min.median(), "hold_min_mean": sub.hold_min.mean(),
                    "time_in_market_share_of_all_bars": np.nan,
                    "minute_path_agreement": sub.minute_path_agrees_with_8h.mean(),
                })
    return tr, pd.DataFrame(summ)


def venue_agreement(meta: dict) -> pd.DataFrame:
    """Same signal candle on two venues: does the take-profit trigger on both?"""
    b = build_pairs(load_8h("binance")).set_index("open_time_ms")
    conf_start = meta["t_end_ms"] - CONFIRM_DAYS * 86_400_000
    rows = []
    for v in ("okx", "kucoin"):
        o = build_pairs(load_8h(v)).set_index("open_time_ms")
        j = b.merge(o, left_index=True, right_index=True, suffixes=("", "_o"))
        j = j[j["green"] & j["green_o"]]
        for sample, m in (("discovery", j["entry_time_ms"] < conf_start), ("confirmation", j["entry_time_ms"] >= conf_start),
                          ("last 365d", j["entry_time_ms"] >= meta["t_end_ms"] - 365 * 86_400_000)):
            jj = j[m]
            for x in X_GRID:
                hit_b = jj["n_low"] <= jj["close"] * (1 - x / 100)
                hit_o = jj["n_low_o"] <= jj["close_o"] * (1 - x / 100)
                # Jupiter marks to an oracle, so also price one fixed level against both venues' lows.
                hit_o_same_level = jj["n_low_o"] <= jj["close"] * (1 - x / 100)
                rows.append({
                    "other_venue": v, "sample": sample, "x": x, "shared_green_signals": len(jj),
                    "tp_hit_binance": hit_b.mean(), "tp_hit_other": hit_o.mean(),
                    "disagree_share": (hit_b != hit_o).mean(),
                    "binance_only": (hit_b & ~hit_o).mean(), "other_only": (~hit_b & hit_o).mean(),
                    "disagree_share_same_level": (hit_b != hit_o_same_level).mean(),
                    "both_venues_hit": (hit_b & hit_o).mean(),
                })
    return pd.DataFrame(rows)


def last_trades(x: float, n: int = 30) -> pd.DataFrame:
    pairs = build_pairs(load_8h("binance"))
    pairs = pairs[pairs["green"]].reset_index(drop=True)
    a = simulate(pairs, x, "short", "c_close")
    b = simulate(pairs, x, "short", "n_open")
    tz = "America/Phoenix"
    fmt = "%Y-%m-%d %H:%M"
    out = pd.DataFrame({
        "candle_open_phoenix": pd.to_datetime(pairs["open_time_ms"], unit="ms", utc=True).dt.tz_convert(tz).dt.strftime(fmt),
        "entry_time_phoenix": pd.to_datetime(pairs["entry_time_ms"], unit="ms", utc=True).dt.tz_convert(tz).dt.strftime(fmt),
        "body_pct": pairs["body_pct"],
        "entry": a["entry"],
        "x_pct": x,
        "take_profit": a["tp"],
        "n_open": pairs["n_open"],
        "n_low": pairs["n_low"],
        "outcome": a["outcome"].map({"tp": "take-profit hit", "gap": "take-profit hit (gap, at open)", "expire": "expired"}),
        "exit": a["exit"],
        "net_12bps": net_return(a["gross"].to_numpy(), a["exit_ratio"].to_numpy(), BASE_COST_BPS),
        "n_open_entry_outcome": b["outcome"].map({"tp": "take-profit hit", "expire": "expired"}),
        "n_open_entry_net_12bps": net_return(b["gross"].to_numpy(), b["exit_ratio"].to_numpy(), BASE_COST_BPS),
    })
    return out.tail(n).iloc[::-1].reset_index(drop=True)


def bootstrap(x: float, meta: dict) -> pd.DataFrame:
    pairs = build_pairs(load_8h("binance"))
    conf_start = meta["t_end_ms"] - CONFIRM_DAYS * 86_400_000
    rng = np.random.default_rng(SEED)
    rows = []
    for mode in ("c_close", "n_open"):
        sim = simulate(pairs, x, "short", mode)
        net = net_return(sim["gross"].to_numpy(), sim["exit_ratio"].to_numpy(), BASE_COST_BPS)
        for sample, pm in (("discovery", pairs["entry_time_ms"] < conf_start),
                           ("confirmation", pairs["entry_time_ms"] >= conf_start)):
            for strat, sm in (("green_short", pairs["green"]), ("red_short", pairs["red"])):
                r = net[(pm & sm).to_numpy()]
                idx = rng.integers(0, len(r), size=(BOOT_DRAWS, len(r)))
                means = r[idx].mean(axis=1)
                rows.append({"entry_mode": mode, "sample": sample, "strategy": strat, "trades": len(r),
                             "mean": r.mean(), "boot_ci_lo": np.percentile(means, 2.5),
                             "boot_ci_hi": np.percentile(means, 97.5), "share_of_draws_above_zero": (means > 0).mean()})
    return pd.DataFrame(rows)


def main() -> None:
    chosen_path = RESULTS / "chosen_x.json"
    if not chosen_path.exists():
        raise SystemExit("run 01_discovery.py first: X must be locked before the last 90 days are read")
    x = float(json.loads(chosen_path.read_text())["chosen_x_pct"])
    meta = load_meta()

    grid, tests = run_grid("confirmation")
    grid.to_csv(RESULTS / "grid_confirmation.csv", index=False)
    tests.to_csv(RESULTS / "tests_confirmation.csv", index=False)

    head = headline(grid, tests, x, meta)
    head["borrow_live_bps_per_8h_short"] = borrow_live_bps(meta, "short")
    head["borrow_stress_bps_per_8h"] = BORROW_STRESS_BPS
    (RESULTS / "confirmation_headline.json").write_text(json.dumps(head, indent=2) + "\n")
    print(json.dumps(head, indent=2))

    trades, summ = excursions(x, meta)
    n_bars_all = len(build_pairs(load_8h("binance")))
    conf_bars = CONFIRM_DAYS * 3
    for i, r in summ.iterrows():
        if r["subset"] == "all":
            bars = {"discovery": n_bars_all - conf_bars, "confirmation": conf_bars, "full history": n_bars_all}[r["sample"]]
            summ.at[i, "time_in_market_share_of_all_bars"] = r["trades"] * r["hold_min_mean"] / (bars * 480)
    trades.to_csv(RESULTS / "excursion_trades.csv", index=False)
    summ.to_csv(RESULTS / "excursion_summary.csv", index=False)
    venue_agreement(meta).to_csv(RESULTS / "venue_tp_agreement.csv", index=False)
    last_trades(x).to_csv(RESULTS / "last_30_green_shorts.csv", index=False)
    bootstrap(x, meta).to_csv(RESULTS / "bootstrap_chosen_x.csv", index=False)


if __name__ == "__main__":
    main()
