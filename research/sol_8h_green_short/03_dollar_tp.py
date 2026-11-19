"""Follow-up variant: cover the short when SOL trades one dollar below the entry.

Same signal, same one-candle management, same costs and baselines as the
percentage study. Only the take-profit distance changes: entry - 1.00 USDT
instead of entry x (1 - X/100).

This is not a clean out-of-sample test. The last 90 days were already read for
the percentage study before this exit was specified, and nothing was fitted
here: the one-dollar distance is taken as given.
"""
from __future__ import annotations

import importlib
import json

import numpy as np
import pandas as pd

from grid import BORROW_STRESS_BPS, borrow_live_bps, run_grid
from lib import BASE_COST_BPS, BODY_BINS, CONFIRM_DAYS, COSTS_BPS, HERE, RESULTS, build_pairs, load_8h, load_meta
from make_report import STRAT_LABEL, STRATS, bps, num, pc, table

DOLLARS = 1.0
TARGET = {"tp_abs": DOLLARS}
CONF = "confirmation (last 90d)"
VENUE_NAME = {"binance": "Binance", "okx": "OKX", "kucoin": "KuCoin"}


def pick(g, period, strategy="green_short", cost=BASE_COST_BPS, venue="binance", entry_mode="c_close", borrow=0.0, body="all"):
    r = g[(g.venue == venue) & (g.entry_mode == entry_mode) & (g.strategy == strategy) & (g.period == period)
          & (g.cost_bps == cost) & np.isclose(g.borrow_bps, borrow) & (g.body_bin == body)]
    assert len(r) == 1, (period, strategy, cost, venue, entry_mode, borrow, body, len(r))
    return r.iloc[0]


def implied_pct(meta: dict) -> pd.DataFrame:
    """How large one dollar is relative to the entry price, by period, for green signals."""
    p = build_pairs(load_8h("binance"))
    p = p[p["green"]]
    et = p["entry_time_ms"]
    day = 86_400_000
    conf_start = meta["t_end_ms"] - CONFIRM_DAYS * day
    years = pd.to_datetime(et, unit="ms", utc=True).dt.year
    pct = DOLLARS / p["close"] * 100.0
    masks = {"discovery": et < conf_start, CONF: et >= conf_start, "full history": et > 0,
             "last 365d": et >= meta["t_end_ms"] - 365 * day}
    masks.update({str(y): years == y for y in sorted(years.unique())})
    rows = []
    for name, m in masks.items():
        rows.append({"period": name, "entry_min": p.loc[m, "close"].min(), "entry_median": p.loc[m, "close"].median(),
                     "entry_max": p.loc[m, "close"].max(), "pct_median": pct[m].median(),
                     "pct_p10": pct[m].quantile(0.1), "pct_p90": pct[m].quantile(0.9)})
    return pd.DataFrame(rows).set_index("period")


def stat_row(label: str, r: pd.Series) -> list[str]:
    return [label, f"{int(r.signals)}", pc(r.tp_share), pc(r.expire_share), bps(r["mean"]), bps(r["median"]), pc(r.win_rate),
            bps(r.avg_win), bps(r.avg_loss), num(r.profit_factor), pc(r.max_dd), pc(r.bars_in_position),
            f"{bps(r.ci_lo)} to {bps(r.ci_hi)}"]


STAT_HEAD = ["Signals", "TP hit", "Expired", "Mean (bps)", "Median (bps)", "Win rate", "Avg win (bps)", "Avg loss (bps)",
             "Profit factor", "Max DD", "Bars in position", "95% interval for mean (bps)"]


def main() -> None:
    meta = load_meta()
    targets = [(DOLLARS, TARGET)]
    gd, td = run_grid("discovery", targets)
    gc, tc = run_grid("confirmation", targets)
    # The confirmation stage already carries every calendar year in full.
    gd, td = gd[gd.period == "discovery"], td[td.period == "discovery"]
    g = pd.concat([gd, gc], ignore_index=True)
    t = pd.concat([td, tc], ignore_index=True)
    g.to_csv(RESULTS / "dollar_tp_grid.csv", index=False)
    t.to_csv(RESULTS / "dollar_tp_tests.csv", index=False)

    c2 = importlib.import_module("02_confirmation")
    trades, exc = c2.excursions(TARGET, meta)
    exc.to_csv(RESULTS / "dollar_tp_excursion_summary.csv", index=False)
    last = c2.last_trades(TARGET)
    last.to_csv(RESULTS / "dollar_tp_last_30_green_shorts.csv", index=False)
    boot = c2.bootstrap(TARGET, meta)
    boot.to_csv(RESULTS / "dollar_tp_bootstrap.csv", index=False)
    imp = implied_pct(meta)
    imp.to_csv(RESULTS / "dollar_tp_implied_pct.csv")

    pct_d = pd.read_csv(RESULTS / "grid_discovery.csv")
    pct_c = pd.read_csv(RESULTS / "grid_confirmation.csv")

    def pct_mean(grid, period, x, strategy="green_short"):
        r = grid[(grid.venue == "binance") & (grid.entry_mode == "c_close") & (grid.strategy == strategy) & (grid.period == period)
                 & (grid.x == x) & (grid.cost_bps == BASE_COST_BPS) & (grid.borrow_bps == 0) & (grid.body_bin == "all")]
        return float(r["mean"].iloc[0])

    t_end = pd.Timestamp(meta["last_completed_8h_close_utc"])
    conf_from = t_end - pd.Timedelta(days=CONFIRM_DAYS)
    live_b = borrow_live_bps(meta, "short")
    dg, cg = pick(g, "discovery"), pick(g, CONF)
    dr, cr = pick(g, "discovery", "red_short"), pick(g, CONF, "red_short")
    yg = pick(g, "last 365d")
    tdx = t[(t.venue == "binance") & (t.entry_mode == "c_close") & (t.period == "discovery")].iloc[0]
    tcx = t[(t.venue == "binance") & (t.entry_mode == "c_close") & (t.period == CONF)].iloc[0]
    conf_means = {s: pick(g, CONF, s)["mean"] for s in STRATS}
    disc_means = {s: pick(g, "discovery", s)["mean"] for s in STRATS}
    beats_conf = [s for s in STRATS[1:] if conf_means["green_short"] > conf_means[s]]
    beats_disc = [s for s in STRATS[1:] if disc_means["green_short"] > disc_means[s]]

    headline = {
        "tp_abs_usdt": DOLLARS,
        "discovery_green_mean_12bps": float(dg["mean"]), "discovery_green_ci": [float(dg.ci_lo), float(dg.ci_hi)],
        "discovery_red_mean_12bps": float(dr["mean"]),
        "last90_green_mean_12bps": float(cg["mean"]), "last90_green_ci": [float(cg.ci_lo), float(cg.ci_hi)],
        "last90_red_mean_12bps": float(cr["mean"]),
        "last90_profitable_after_12bps": bool(cg["mean"] > 0),
        "last90_ci_excludes_zero": bool(cg.ci_lo > 0),
        "last90_baselines_beaten": beats_conf, "discovery_baselines_beaten": beats_disc,
        "last90_green_minus_red": float(tcx.green_minus_red),
        "last90_green_minus_red_ci": [float(tcx.diff_ci_lo), float(tcx.diff_ci_hi)],
        "last90_by_venue": {v: float(pick(g, CONF, venue=v)["mean"]) for v in VENUE_NAME},
    }
    (RESULTS / "dollar_tp_headline.json").write_text(json.dumps(headline, indent=2) + "\n")
    print(json.dumps(headline, indent=2))

    L: list[str] = []
    A = L.append
    A("# SOL/USDT 8h green-candle short with a one-dollar take-profit\n")
    A("Follow-up to `REPORT.md`. Same signal, same next-candle management, same costs and baselines. The only change: "
      f"the cover price is **entry - {DOLLARS:.2f} USDT** instead of a percentage below entry.\n")
    A("## Result\n")
    A(table(["Sample, after 12 bps", "Signals", "TP hit", "Green short mean (bps)", "95% interval (bps)", "Sum of returns",
             "Red short mean (bps)", "Green minus red (bps)", "95% interval"], [
        ["Discovery (before " + f"{conf_from:%Y-%m-%d %H:%M} UTC)", int(dg.signals), pc(dg.tp_share), bps(dg["mean"]),
         f"{bps(dg.ci_lo)} to {bps(dg.ci_hi)}", pc(dg["sum"], 1), bps(dr["mean"]), bps(tdx.green_minus_red),
         f"{bps(tdx.diff_ci_lo)} to {bps(tdx.diff_ci_hi)}"],
        ["Last 90 days", int(cg.signals), pc(cg.tp_share), bps(cg["mean"]), f"{bps(cg.ci_lo)} to {bps(cg.ci_hi)}", pc(cg["sum"], 2),
         bps(cr["mean"]), bps(tcx.green_minus_red), f"{bps(tcx.diff_ci_lo)} to {bps(tcx.diff_ci_hi)}"],
    ]))
    A("")
    A(f"- One dollar is not one distance. It was {imp.loc['2020', 'pct_median']:.0f}% of the entry price in 2020, "
      f"{imp.loc['2021', 'pct_median']:.1f}% in 2021, {imp.loc['2023', 'pct_median']:.1f}% in 2023, {imp.loc['2025', 'pct_median']:.2f}% in 2025 "
      f"and {imp.loc[CONF, 'pct_median']:.2f}% over the last 90 days (range {imp.loc[CONF, 'pct_p10']:.2f}% to {imp.loc[CONF, 'pct_p90']:.2f}% "
      f"for the middle 80% of signals). Fees are a percentage of notional, so the percentage is what decides whether a fill pays.")
    last_px = float(load_8h("binance")["close"].iloc[-1])
    pct_disc = {x: pct_mean(pct_d, "discovery", x) for x in (0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0)}
    assert dg["mean"] < min(pct_disc.values())
    A(f"- On the last 90 days one dollar was close to the 1% target of the percentage study (median {imp.loc[CONF, 'pct_median']:.2f}% of entry), "
      f"and the result is close to that one: {bps(cg['mean'])} bps against {bps(pct_mean(pct_c, CONF, 1.0))} bps. "
      f"At the latest close of {last_px:.2f} one dollar is {DOLLARS / last_px * 100:.2f}%, so from here it is a wider target than the one this slice tested. "
      f"The percentage targets on either side of that, 1% and 1.5%, returned {bps(pct_mean(pct_c, CONF, 1.0))} and {bps(pct_mean(pct_c, CONF, 1.5))} bps "
      f"on the last 90 days and {bps(pct_disc[1.0])} and {bps(pct_disc[1.5])} bps on discovery data.")
    A(f"- It hit on {pc(cg.tp_share)} of green signals in the last 90 days and {pc(yg.tp_share)} in the last 365 days "
      f"(after red candles: {pc(cr.tp_share)} and {pc(pick(g, 'last 365d', 'red_short').tp_share)}). "
      f"The average winner after 12 bps was {bps(cg.avg_win)} bps and the average loser {bps(cg.avg_loss)} bps, so a "
      f"{pc(cg.win_rate)} win rate does not cover the losers.")
    A(f"- On discovery data it is worse than every percentage target (the best of those was {bps(max(pct_disc.values()))} bps) "
      f"and it beat {len(beats_disc)} of the 4 baselines. On the last 90 days it beat {len(beats_conf)} of 4, with a margin over the red short of "
      f"{bps(tcx.green_minus_red)} bps and a 95% interval of {bps(tcx.diff_ci_lo)} to {bps(tcx.diff_ci_hi)}.")
    A("- By venue on the last 90 days: " + ", ".join(f"{VENUE_NAME[v]} {bps(pick(g, CONF, venue=v)['mean'])} bps" for v in VENUE_NAME) + ".")
    A("- The last 90 days are not a clean test of this exit. They were read for seven percentage targets before the one-dollar exit "
      "was specified, and the wider targets were already known to look better on that slice.\n")

    A("## Green short, every cost\n")
    for label, per in (("Discovery", "discovery"), ("Last 90 days", CONF), ("Last 365 days", "last 365d"), ("Full history", "full history")):
        A(f"### {label}\n")
        A(table(["Cost (bps)"] + STAT_HEAD, [stat_row(str(c), pick(g, per, cost=c)) for c in COSTS_BPS]))
        A("")

    A("## Against the baselines\n")
    for label, per in (("Discovery", "discovery"), ("Last 90 days", CONF), ("Last 365 days", "last 365d")):
        A(f"### {label}, after 12 bps\n")
        A(table(["Strategy"] + STAT_HEAD, [stat_row(STRAT_LABEL[s], pick(g, per, s)) for s in STRATS]))
        A("")
        tt = t[(t.venue == "binance") & (t.entry_mode == "c_close") & (t.period == per)].iloc[0]
        A(f"Green minus red: {bps(tt.green_minus_red)} bps (95% interval {bps(tt.diff_ci_lo)} to {bps(tt.diff_ci_hi)}). "
          f"Share of random candle sets of the same size that shorted at least as well as the green set: {tt.p_green_beats_random_same_size:.2f}.\n")
        A(table(["Cost (bps)"] + [STRAT_LABEL[s] for s in STRATS],
                [[str(c)] + [bps(pick(g, per, s, cost=c)["mean"]) for s in STRATS] for c in COSTS_BPS]))
        A("")
        A("Mean return per trade in bps at each cost. The flipped long sells one dollar above entry.\n")

    A("## By period, after 12 bps\n")
    periods = ["full history"] + [str(y) for y in range(2020, t_end.year + 1)] + ["last 365d", CONF]
    rows = []
    for p in periods:
        a, r = pick(g, p), pick(g, p, "red_short")
        rows.append([p, f"{imp.loc[p, 'entry_median']:.2f}", f"{imp.loc[p, 'pct_median']:.2f}%", int(a.signals), pc(a.tp_share),
                     bps(a["mean"]), f"{bps(a.ci_lo)} to {bps(a.ci_hi)}", num(a.profit_factor), pc(a.max_dd), bps(r["mean"]), pc(r.tp_share)])
    A(table(["Period", "Median entry price", "One dollar as % of entry (median)", "Green signals", "Green TP hit", "Green mean (bps)",
             "95% interval (bps)", "Green profit factor", "Green max DD", "Red mean (bps)", "Red TP hit"], rows))
    A("")
    A(f"In 2020 SOL traded near {imp.loc['2020', 'entry_median']:.0f} dollars and the target was reached on {pc(pick(g, '2020').tp_share)} of signals; "
      f"in 2023 it was reached on {pc(pick(g, '2023').tp_share)}. In those years the trade was close to a plain one-candle short. "
      f"In 2024 and 2025, with SOL above 150, one dollar was about 0.6% and was reached on three signals in four.\n")
    assert pick(g, "2024").tp_share > 0.74 and pick(g, "2025").tp_share > 0.74 and imp.loc["2024", "entry_median"] > 150 and imp.loc["2025", "entry_median"] > 150

    A("## Entry at N's open, venues, borrow\n")
    rows = []
    for label, per in (("Discovery", "discovery"), ("Last 90 days", CONF), ("Last 365 days", "last 365d")):
        a = pick(g, per)
        rows.append([label, bps(a["mean"]), bps(pick(g, per, entry_mode="n_open")["mean"]),
                     bps(pick(g, per, venue="okx")["mean"]), bps(pick(g, per, venue="kucoin")["mean"]),
                     bps(pick(g, per, borrow=live_b)["mean"]), bps(pick(g, per, borrow=BORROW_STRESS_BPS)["mean"]),
                     bps(pick(g, per, "red_short", venue="okx")["mean"]), bps(pick(g, per, "red_short", venue="kucoin")["mean"])])
    A(table(["Sample, 12 bps", "Binance, C close", "Binance, N open", "OKX, C close", "KuCoin, C close",
             f"Binance + {live_b:.2f} bps borrow", f"Binance + {BORROW_STRESS_BPS:.0f} bps borrow", "Red short, OKX", "Red short, KuCoin"], rows))
    A("")
    A("Green short mean per trade in bps unless the column says red. OKX history starts 2020-09-30 and KuCoin 2021-08-04.\n")

    A("## Green signals by body size, after 12 bps\n")
    rows = []
    for label, per in (("Discovery", "discovery"), ("Last 90 days", CONF)):
        row = [label]
        for bl, _, _ in BODY_BINS:
            r = pick(g, per, body=bl)
            row.append(f"{bps(r['mean'])} (n={int(r.signals)}, {bps(r.ci_lo)} to {bps(r.ci_hi)})" if r.signals > 1 else
                       (f"{bps(r['mean'])} (n=1)" if r.signals == 1 else "none"))
        rows.append(row)
    A(table(["Sample"] + [f"Body {bl}" for bl, _, _ in BODY_BINS], rows))
    A("")

    A("## How far price rose against the short before exit\n")
    rows = []
    for _, r in exc[exc.entry_mode == "c_close"].iterrows():
        rows.append([r["sample"].capitalize(), r.subset.capitalize(), int(r.trades), pc(r.mae_median, 2), pc(r.mae_p90, 2),
                     pc(r.mae_p99, 2), pc(r.mae_max, 1), f"{r.hold_min_median:.0f}"])
    A(table(["Sample", "Subset", "Trades", "Median adverse move", "90th percentile", "99th percentile", "Worst", "Median minutes held"], rows))
    A("")
    A("From Binance 1m candles, entry at C's close. Highest price before exit relative to entry.\n")

    A("## The last 30 green-candle shorts\n")
    A("Times are America/Phoenix (UTC-7). Binance spot. Newest first.\n")
    rows = []
    for _, r in last.iterrows():
        rows.append([r.candle_open_phoenix, r.entry_time_phoenix, f"{r.entry:.2f}", f"{r.take_profit:.2f}",
                     f"{r.tp_distance_pct_of_entry:.2f}%", r.outcome, f"{r.exit:.2f}", f"{r.net_12bps * 100:+.2f}%"])
    A(table(["Signal candle open", "Entry time (C close)", "Entry", "Take-profit (entry - 1.00)", "Distance as % of entry", "Result",
             "Exit price", "Return after 12 bps"], rows))
    A("")
    A(f"Sum of the 30 returns after 12 bps: {last.net_12bps.sum() * 100:+.2f}%. "
      f"{int((last.outcome != 'expired').sum())} hit the take-profit and {int((last.outcome == 'expired').sum())} expired.\n")
    A("Full grid: `results/dollar_tp_grid.csv`. Run `python3 03_dollar_tp.py` to regenerate.")

    (HERE / "REPORT_DOLLAR_TP.md").write_text("\n".join(L) + "\n")
    print("wrote REPORT_DOLLAR_TP.md")


if __name__ == "__main__":
    main()
