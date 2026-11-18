"""Render REPORT.md from the result files. Every number in the report is read from results/."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from lib import BASE_COST_BPS, BODY_BINS, COSTS_BPS, HERE, RESULTS, X_GRID, load_meta

STRATS = ["green_short", "red_short", "all_short", "random_half_short", "green_long_flipped"]
STRAT_LABEL = {
    "green_short": "Green short (the idea)",
    "red_short": "Red short",
    "all_short": "Every-candle short",
    "random_half_short": "Random-half short",
    "green_long_flipped": "Green long (flipped)",
}
CONF = "confirmation (last 90d)"


def bps(v: float, d: int = 1) -> str:
    return "n/a" if pd.isna(v) else f"{v * 1e4:+.{d}f}"


def pc(v: float, d: int = 1) -> str:
    return "n/a" if pd.isna(v) else f"{v * 100:.{d}f}%"


def num(v: float, d: int = 2) -> str:
    return "n/a" if pd.isna(v) else ("inf" if np.isinf(v) else f"{v:.{d}f}")


def table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] + ["---:"] * (len(headers) - 1)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pick(g, venue="binance", entry_mode="c_close", strategy="green_short", period=None, x=None, cost=None,
         borrow=0.0, body="all"):
    m = (g.venue == venue) & (g.entry_mode == entry_mode) & (g.strategy == strategy) & (g.body_bin == body)
    m &= np.isclose(g.borrow_bps, borrow)
    if period is not None:
        m &= g.period == period
    if x is not None:
        m &= g.x == x
    if cost is not None:
        m &= g.cost_bps == cost
    return g[m]


def one(g, **kw) -> pd.Series:
    r = pick(g, **kw)
    assert len(r) == 1, (kw, len(r))
    return r.iloc[0]


FULL_HEAD = ["X", "Cost (bps)", "Signals", "TP hit", "Expired", "Mean (bps)", "Median (bps)", "Win rate",
             "Avg win (bps)", "Avg loss (bps)", "Profit factor", "Max DD", "Bars in position", "95% interval for mean (bps)"]


def full_row(r: pd.Series) -> list[str]:
    return [f"{r.x:g}%", f"{int(r.cost_bps)}", f"{int(r.signals)}", pc(r.tp_share), pc(r.expire_share), bps(r["mean"]),
            bps(r["median"]), pc(r.win_rate), bps(r.avg_win), bps(r.avg_loss), num(r.profit_factor), pc(r.max_dd),
            pc(r.bars_in_position), f"{bps(r.ci_lo)} to {bps(r.ci_hi)}"]


def full_grid(g, period, entry_mode="c_close", strategy="green_short", venue="binance") -> str:
    rows = [full_row(one(g, venue=venue, entry_mode=entry_mode, strategy=strategy, period=period, x=x, cost=c))
            for x in X_GRID for c in COSTS_BPS]
    return table(FULL_HEAD, rows)


def baseline_means(g, period, entry_mode="c_close") -> str:
    head = ["X", "Cost (bps)"] + [STRAT_LABEL[s] for s in STRATS]
    rows = []
    for x in X_GRID:
        for c in COSTS_BPS:
            rows.append([f"{x:g}%", str(c)] + [bps(one(g, entry_mode=entry_mode, strategy=s, period=period, x=x, cost=c)["mean"])
                                               for s in STRATS])
    return table(head, rows)


def baseline_at_base(g, t, period, entry_mode="c_close") -> str:
    head = ["X"] + [STRAT_LABEL[s] for s in STRATS] + ["Green minus red (bps)", "95% interval", "Beats every baseline",
                                                       "P(random same-size set >= green)"]
    rows = []
    for x in X_GRID:
        means = {s: one(g, entry_mode=entry_mode, strategy=s, period=period, x=x, cost=BASE_COST_BPS)["mean"] for s in STRATS}
        tt = t[(t.venue == "binance") & (t.entry_mode == entry_mode) & (t.period == period) & (t.x == x)].iloc[0]
        beats = all(means["green_short"] > v for s, v in means.items() if s != "green_short")
        rows.append([f"{x:g}%"] + [bps(means[s]) for s in STRATS]
                    + [bps(tt.green_minus_red), f"{bps(tt.diff_ci_lo)} to {bps(tt.diff_ci_hi)}", "yes" if beats else "no",
                       f"{tt.p_green_beats_random_same_size:.2f}"])
    return table(head, rows)


def strategy_detail(g, period, x, entry_mode="c_close") -> str:
    head = ["Strategy", "Signals", "TP hit", "Expired", "Mean (bps)", "Median (bps)", "Win rate", "Avg win (bps)",
            "Avg loss (bps)", "Profit factor", "Max DD", "Bars in position", "95% interval (bps)"]
    rows = []
    for s in STRATS:
        r = one(g, entry_mode=entry_mode, strategy=s, period=period, x=x, cost=BASE_COST_BPS)
        rows.append([STRAT_LABEL[s], f"{int(r.signals)}", pc(r.tp_share), pc(r.expire_share), bps(r["mean"]), bps(r["median"]),
                     pc(r.win_rate), bps(r.avg_win), bps(r.avg_loss), num(r.profit_factor), pc(r.max_dd),
                     pc(r.bars_in_position), f"{bps(r.ci_lo)} to {bps(r.ci_hi)}"])
    return table(head, rows)


def main() -> None:
    meta = load_meta()
    chosen = json.loads((RESULTS / "chosen_x.json").read_text())
    X = float(chosen["chosen_x_pct"])
    head = json.loads((RESULTS / "confirmation_headline.json").read_text())
    checks = json.loads((RESULTS / "data_checks.json").read_text())
    gd = pd.read_csv(RESULTS / "grid_discovery.csv")
    gc = pd.read_csv(RESULTS / "grid_confirmation.csv")
    td = pd.read_csv(RESULTS / "tests_discovery.csv")
    tc = pd.read_csv(RESULTS / "tests_confirmation.csv")
    exc = pd.read_csv(RESULTS / "excursion_summary.csv")
    ven = pd.read_csv(RESULTS / "venue_tp_agreement.csv")
    last = pd.read_csv(RESULTS / "last_30_green_shorts.csv")
    boot = pd.read_csv(RESULTS / "bootstrap_chosen_x.csv")
    live_b = head["borrow_live_bps_per_8h_short"]
    stress_b = head["borrow_stress_bps_per_8h"]
    jup = meta["jupiter_perps_sol_pool_info"]

    dg = one(gd, period="discovery", x=X, cost=BASE_COST_BPS)
    dg0 = one(gd, period="discovery", x=X, cost=0)
    dr = one(gd, strategy="red_short", period="discovery", x=X, cost=BASE_COST_BPS)
    cg = one(gc, period=CONF, x=X, cost=BASE_COST_BPS)
    cg0 = one(gc, period=CONF, x=X, cost=0)
    cr = one(gc, strategy="red_short", period=CONF, x=X, cost=BASE_COST_BPS)
    cgo = one(gc, entry_mode="n_open", period=CONF, x=X, cost=BASE_COST_BPS)
    cro = one(gc, entry_mode="n_open", strategy="red_short", period=CONF, x=X, cost=BASE_COST_BPS)
    dgo = one(gd, entry_mode="n_open", period="discovery", x=X, cost=BASE_COST_BPS)
    tdx = td[(td.venue == "binance") & (td.entry_mode == "c_close") & (td.period == "discovery") & (td.x == X)].iloc[0]
    tcx = tc[(tc.venue == "binance") & (tc.entry_mode == "c_close") & (tc.period == CONF) & (tc.x == X)].iloc[0]
    hc = head["c_close"]
    disc_best = max(one(gd, period="discovery", x=x, cost=BASE_COST_BPS)["mean"] for x in X_GRID)
    disc_worse_than_red = sum(
        one(gd, period="discovery", x=x, cost=BASE_COST_BPS)["mean"]
        < one(gd, strategy="red_short", period="discovery", x=x, cost=BASE_COST_BPS)["mean"] for x in X_GRID)
    sd_conf = (cg.ci_hi - cg.ci_lo) / (2 * 1.96) * np.sqrt(cg.signals)
    need = 1.96 * sd_conf / np.sqrt(cg.signals)
    st = checks["stitching"]
    lows = checks["low_disagreement"]
    conf_from = pd.Timestamp(chosen["confirmation_entries_from_utc"])
    conf_to = pd.Timestamp(chosen["confirmation_entries_to_utc"])
    first = pd.Timestamp(meta["binance_first_8h_open_utc"])
    t_end = pd.Timestamp(meta["last_completed_8h_close_utc"])

    L: list[str] = []
    A = L.append

    A("# SOL/USDT 8h: short the close of a green candle, cover X% lower\n")
    A("## Verdict: discard\n")
    A(f"**After 12 bps the short lost {abs(dg['mean']) * 1e4:.1f} bps per trade over {int(dg.signals):,} discovery trades "
      f"(95% interval {bps(dg.ci_lo)} to {bps(dg.ci_hi)} bps), at the best X on the menu.** "
      f"No X from 0.3% to 3% was positive after 12 bps on discovery data. The best was X = {X:g}%, so that is the X that was locked.\n")
    A(f"Locked X = {X:g}% on the last 90 days, after 12 bps, Binance spot, entry at C's close:\n")
    A(table(["", "Signals", "TP hit", "Mean per trade (bps)", "95% interval (bps)", "Sum of trade returns", "Profit factor"], [
        ["Green short (the idea)", int(cg.signals), pc(cg.tp_share), bps(cg["mean"]), f"{bps(cg.ci_lo)} to {bps(cg.ci_hi)}",
         pc(cg["sum"], 2), num(cg.profit_factor)],
        ["Red short (baseline)", int(cr.signals), pc(cr.tp_share), bps(cr["mean"]), f"{bps(cr.ci_lo)} to {bps(cr.ci_hi)}",
         pc(cr["sum"], 2), num(cr.profit_factor)],
    ]))
    A("")
    A(f"- The confirmation result is not profitable after 12 bps: {bps(cg['mean'])} bps per trade. "
      f"Entry at N's open gives {bps(cgo['mean'])} bps (red short: {bps(cro['mean'])} bps).")
    A(f"- It did beat all four baselines on the last 90 days, but the margin over the red short, {bps(tcx.green_minus_red)} bps, "
      f"has a 95% interval of {bps(tcx.diff_ci_lo)} to {bps(tcx.diff_ci_hi)} bps, and the sign is the opposite of discovery, "
      f"where the green short was {abs(tdx.green_minus_red) * 1e4:.1f} bps worse than the red short and worse than it at "
      f"{disc_worse_than_red} of {len(X_GRID)} X values.")
    A(f"- The dip is not specific to green candles. On discovery data the next candle traded {X:g}% below the close after "
      f"{pc(dg.tp_share)} of green candles and {pc(dr.tp_share)} of red candles.")
    A(f"- Before costs the idea earned {bps(dg0['mean'])} bps per trade on discovery data "
      f"(95% interval {bps(dg0.ci_lo)} to {bps(dg0.ci_hi)}). That is not distinguishable from zero and is far below a 12 bps fee.")
    A(f"- SOL fell {pc(-CONF_BH, 1)} over the confirmation window. Every short had that tailwind and the idea still did not clear costs.")
    A(f"- Break-even round-trip cost at X = {X:g}%: about {dg0['mean'] * 1e4:.0f} bps on discovery data and {cg0['mean'] * 1e4:.0f} bps on the last 90 days. "
      f"Jupiter charges 12 before borrow and price impact.")
    A("")
    A(f"**The one future result that would change this:** on trades entered after {t_end:%Y-%m-%d %H:%M} UTC, with X still {X:g}% "
      f"and 12 bps charged, a mean return per green short whose 95% interval sits wholly above zero. At the trade-to-trade "
      f"spread seen in the last 90 days ({sd_conf * 1e4:.0f} bps) and a similar count of about {int(cg.signals)} signals, that "
      f"needs roughly {need * 1e4:+.0f} bps per trade after costs. Until then nothing here supports a bot, and no new exit is proposed.\n")

    A("## What was tested\n")
    A("- Signal candle C is a completed 8h candle with close > open. Short one unit at C's close. Take-profit at entry x (1 - X/100).")
    A("- Managed on the next candle N only. N opens at or below the take-profit: cover at N's open. N's low touches it: cover at the "
      "take-profit price. Otherwise cover at N's close. No stop. Every trade is closed by N's close, so trades never overlap.")
    A("- Returns are per trade on one unit of notional. A round-trip cost of c bps is charged as c/2 on entry notional and c/2 on exit notional.")
    A("- `test_rules.py` checks each fill case and the cost arithmetic on hand-built candles.\n")
    A("### Data\n")
    b8 = checks["binance_8h"]
    A(f"- Primary venue: **Binance spot SOLUSDT**, native 8h klines opening at 00:00, 08:00 and 16:00 UTC. "
      f"{b8['bars']:,} completed candles from {first:%Y-%m-%d %H:%M} UTC to the candle that closed {t_end:%Y-%m-%d %H:%M} UTC. "
      f"No 8h bar is missing. The candle forming at fetch time was dropped. {b8['green_bars']:,} green, {b8['red_bars']:,} red, "
      f"{b8['doji_bars']} with close = open (neither).")
    A(f"- Second venue: **OKX spot SOL-USDT**, 1h candles aggregated to the same 8h grid (OKX has no 8h bar), from {pd.Timestamp(meta['okx_first_8h_open_utc']):%Y-%m-%d}. "
      f"Third venue for the lows: **KuCoin spot SOL-USDT**, native 8h, from {pd.Timestamp(meta['kucoin_first_8h_open_utc']):%Y-%m-%d}.")
    m18 = checks["binance_1m_vs_8h"]
    A(f"- Binance 1m candles ({m18['minutes']:,} bars) are used only for the adverse-move and holding-time numbers. "
      f"Aggregated to 8h they reproduce the 8h low and close on every bar ({m18['low_mismatch']} low mismatches, {m18['close_mismatch']} close mismatches).")
    A(f"- **Discovery**: trades entered before {conf_from:%Y-%m-%d %H:%M} UTC. **Confirmation**: trades entered from "
      f"{conf_from:%Y-%m-%d %H:%M} to {conf_to:%Y-%m-%d %H:%M} UTC, 270 candles.")
    A(f"- X was chosen by one rule written down and committed before any result existed: the X with the highest mean return per "
      f"trade after 12 bps on discovery data. The discovery results and the locked X were committed before the confirmation "
      f"script was run. The other six X values on the last 90 days are printed below because the report asks for them. They were not used to choose anything.")
    A("- I do not know which dates the dip was noticed on. If the chart that prompted this idea included any of the last 90 days, "
      "the confirmation slice is not clean and its result flatters the idea.\n")

    A("### Execution: C's close versus N's open\n")
    A("Binance, OKX and KuCoin spot candles are not stitched. N's open is the first trade of the new candle, which is often but "
      "not always C's close.\n")
    A(table(["Venue", "N open = C close, full history", "Same, last 365 days", "Median gap (bps)", "99th percentile gap (bps)", "Largest gap (bps)"],
            [[{"binance": "Binance", "okx": "OKX", "kucoin": "KuCoin"}[v], pc(s["share_n_open_equals_c_close"]), pc(s["share_equal_last_365d"]),
              f"{s['median_abs_gap_bps']:.2f}", f"{s['p99_abs_gap_bps']:.1f}", f"{s['max_abs_gap_bps']:.0f}"] for v, s in st.items()]))
    A("")
    A(f"Gap = |N open / C close - 1|. On Binance the two prices are the same on {pc(st['binance']['share_n_open_equals_c_close'])} of candles "
      f"and within {st['binance']['p99_abs_gap_bps']:.0f} bps on 99% of them. Both entries are reported. At the locked X the difference is small:\n")
    rows = []
    for label, g, per in (("Discovery", gd, "discovery"), ("Confirmation", gc, CONF)):
        for c in COSTS_BPS:
            a = one(g, period=per, x=X, cost=c)
            b = one(g, entry_mode="n_open", period=per, x=X, cost=c)
            rows.append([label, c, bps(a["mean"]), bps(b["mean"]), pc(a.tp_share), pc(b.tp_share), pc(a.gap_share, 2)])
    A(table(["Sample", "Cost (bps)", "Mean, entry at C close (bps)", "Mean, entry at N open (bps)", "TP hit, C close", "TP hit, N open",
             "Filled at N's open through the TP"], rows))
    A("")
    A("Jupiter perps fill against an oracle price, not against Binance prints, and a Jupiter take-profit is a trigger that a keeper "
      "executes at the oracle price when it gets there. Neither a fill at exactly C's close nor a fill at exactly the limit is "
      "guaranteed. The rule as specified assumes both, which favours the trade.\n")

    A("## Discovery data\n")
    A(f"Trades entered before {conf_from:%Y-%m-%d %H:%M} UTC. Binance spot, entry at C's close. Returns are in basis points per trade after the stated round-trip cost.\n")
    A("### Green-candle short, every X and every cost\n")
    A(full_grid(gd, "discovery"))
    A("")
    A("TP hit includes the rare fills at N's open through the take-profit. Max DD is the largest peak-to-trough fall of the curve "
      "that compounds every trade at one unit of notional. Bars in position is the share of 8h bars during which a short was open at some point.\n")
    A("### Against the baselines at 12 bps\n")
    A(baseline_at_base(gd, td, "discovery"))
    A("")
    A("Mean return per trade in bps. Random-half is the average over 1,000 random halves of the candles. The last column is the share "
      "of 5,000 random candle sets, the same size as the green set, whose mean short return was at least as good as the green set's. "
      "A value near 0 would mean green candles are a better-than-random place to short. These are not.\n")
    A(f"### All five strategies at X = {X:g}% and 12 bps\n")
    A(strategy_detail(gd, "discovery", X))
    A("")
    A("The interval for the random-half row is the 2.5th to 97.5th percentile of the mean across the 1,000 draws.\n")
    A("### Mean return per trade, every strategy at every cost\n")
    A(baseline_means(gd, "discovery"))
    A("")

    A("## Confirmation slice: the last 90 days\n")
    A(f"Trades entered {conf_from:%Y-%m-%d %H:%M} to {conf_to:%Y-%m-%d %H:%M} UTC. X = {X:g}% is the only row that was pre-chosen. "
      f"SOL went from {CONF_P0:.2f} to {CONF_P1:.2f} over the window ({pc(CONF_BH)}).\n")
    A(f"### All five strategies at the locked X = {X:g}% and 12 bps\n")
    A(strategy_detail(gc, CONF, X))
    A("")
    bt = boot[(boot.entry_mode == "c_close") & (boot["sample"] == "confirmation") & (boot.strategy == "green_short")].iloc[0]
    A(f"A bootstrap of the {int(bt.trades)} green-short returns gives a 95% interval of {bps(bt.boot_ci_lo)} to {bps(bt.boot_ci_hi)} bps for the mean; "
      f"{pc(bt.share_of_draws_above_zero)} of resamples were above zero. That is a coin flip around zero, after costs, in a falling market.\n")
    A("### Green-candle short, every X and every cost\n")
    A(full_grid(gc, CONF))
    A("")
    pos = [x for x in X_GRID if one(gc, period=CONF, x=x, cost=BASE_COST_BPS)["mean"] > 0]
    A(f"The rows for X = {', '.join(f'{x:g}%' for x in pos)} are positive after 12 bps on this slice. They were not chosen in advance, "
      f"none has an interval that excludes zero, and on discovery data those same X values returned "
      f"{', '.join(bps(one(gd, period='discovery', x=x, cost=BASE_COST_BPS)['mean']) for x in pos)} bps. "
      f"What happened in these 90 days is that candles reversed: the candle after a green one averaged {bps(NEXT['conf_green'])} bps "
      f"and the candle after a red one {bps(NEXT['conf_red'])} bps. Over the six years before, the candle after a green one averaged "
      f"{bps(NEXT['disc_green'])} bps and after a red one {bps(NEXT['disc_red'])} bps, the opposite ordering. "
      f"One 90-day window of {int(cg.signals)} trades cannot tell a new pattern from noise.\n")
    assert all(one(gc, period=CONF, x=x, cost=BASE_COST_BPS)["ci_lo"] < 0 for x in pos)
    A("### Against the baselines at 12 bps\n")
    A(baseline_at_base(gc, tc, CONF))
    A("")
    A("### Mean return per trade, every strategy at every cost\n")
    A(baseline_means(gc, CONF))
    A("")

    A("## By period\n")
    A(f"Green short and red short at X = {X:g}%, Binance, entry at C's close. 2026 is year to date.\n")
    periods = ["full history"] + [str(y) for y in range(first.year, t_end.year + 1)] + ["last 365d", CONF]
    rows = []
    for p in periods:
        for c in COSTS_BPS:
            g_ = one(gc, period=p, x=X, cost=c)
            r_ = one(gc, strategy="red_short", period=p, x=X, cost=c)
            rows.append([p, c, int(g_.signals), pc(g_.tp_share), bps(g_["mean"]), f"{bps(g_.ci_lo)} to {bps(g_.ci_hi)}",
                         num(g_.profit_factor), pc(g_.max_dd), bps(r_["mean"]), pc(r_.tp_share)])
    A(table(["Period", "Cost (bps)", "Green signals", "Green TP hit", "Green mean (bps)", "95% interval (bps)", "Green profit factor",
             "Green max DD", "Red mean (bps)", "Red TP hit"], rows))
    A("")
    A("### Green short, mean per trade after 12 bps, every X by period\n")
    rows = [[p] + [bps(one(gc, period=p, x=x, cost=BASE_COST_BPS)["mean"]) for x in X_GRID] for p in periods]
    A(table(["Period"] + [f"X = {x:g}%" for x in X_GRID], rows))
    A("")
    A("### Red short, mean per trade after 12 bps, every X by period\n")
    rows = [[p] + [bps(one(gc, strategy="red_short", period=p, x=x, cost=BASE_COST_BPS)["mean"]) for x in X_GRID] for p in periods]
    A(table(["Period"] + [f"X = {x:g}%" for x in X_GRID], rows))
    A("")
    A("The only calendar year in which the green short made money after 12 bps is 2022, when SOL lost most of its value. "
      "The trade is a short position in SOL with a capped upside, and it earns when SOL falls.\n")

    A("## Green signals by body size\n")
    A("Body = (close - open) / open of the signal candle. Mean return per trade after 12 bps, Binance, entry at C's close.\n")
    for label, g, per in (("Discovery", gd, "discovery"), ("Confirmation (last 90 days)", gc, CONF)):
        A(f"### {label}\n")
        rows = []
        for x in X_GRID:
            row = [f"{x:g}%"]
            for bl, _, _ in BODY_BINS:
                r = one(g, period=per, x=x, cost=BASE_COST_BPS, body=bl)
                row.append(f"{bps(r['mean'])} (n={int(r.signals)})" if r.signals else "none")
            rows.append(row)
        A(table(["X"] + [f"Body {bl}" for bl, _, _ in BODY_BINS], rows))
        A("")
        rows = []
        for bl, _, _ in BODY_BINS:
            for c in COSTS_BPS:
                r = one(g, period=per, x=X, cost=c, body=bl)
                if r.signals:
                    rows.append([bl, c, int(r.signals), pc(r.tp_share), bps(r["mean"]), bps(r["median"]), pc(r.win_rate),
                                 num(r.profit_factor), f"{bps(r.ci_lo)} to {bps(r.ci_hi)}"])
                else:
                    rows.append([bl, c, 0, "n/a", "n/a", "n/a", "n/a", "n/a", "n/a"])
        A(f"At X = {X:g}%, every cost:\n")
        A(table(["Body", "Cost (bps)", "Signals", "TP hit", "Mean (bps)", "Median (bps)", "Win rate", "Profit factor", "95% interval (bps)"], rows))
        A("")
    bb = gd[(gd.venue == "binance") & (gd.entry_mode == "c_close") & (gd.strategy == "green_short") & (gd.period == "discovery")
            & (gd.cost_bps == BASE_COST_BPS) & (gd.borrow_bps == 0) & (gd.body_bin != "all")]
    above = bb[bb["mean"] > 0]
    assert (bb["ci_lo"] < 0).all()
    A(f"On discovery data {len(above)} of the {len(bb)} body-size and X combinations is above zero after 12 bps"
      + ("".join(f": body {r.body_bin} at X = {r.x:g}%, {bps(r['mean'])} bps with a 95% interval of {bps(r.ci_lo)} to {bps(r.ci_hi)}"
                 for _, r in above.iterrows()) if len(above) else "")
      + f". The under-1% bucket is the worst of the four at {int((bb.loc[bb.groupby('x')['mean'].idxmin(), 'body_bin'] == '<1%').sum())} "
        f"of the {len(X_GRID)} X values. The buckets on the confirmation slice hold too few trades to read.\n")

    A("## Borrow sensitivity\n")
    A(f"Jupiter's perps API reported a SOL short borrow rate of {jup['shortBorrowRatePercent']}% per hour at "
      f"{jup['shortUtilizationPercent']}% utilisation when the data was fetched ({pd.Timestamp(meta['fetched_at_utc']):%Y-%m-%d %H:%M} UTC), "
      f"and an open fee of {jup['openFeePercent']}%. Charged for the full 8 hours that is **{live_b:.2f} bps** per trade. "
      f"A stress case charges 0.01% per hour, {stress_b:.0f} bps per 8 hours. Both are added on top of 12 bps. "
      f"The flipped long is charged the long rate ({jup['longBorrowRatePercent']}% per hour). Price impact fees are not modelled.\n")
    rows = []
    for label, g, per in (("Discovery", gd, "discovery"), ("Confirmation", gc, CONF)):
        for x in X_GRID:
            a = one(g, period=per, x=x, cost=BASE_COST_BPS)
            b = one(g, period=per, x=x, cost=BASE_COST_BPS, borrow=live_b)
            s = one(g, period=per, x=x, cost=BASE_COST_BPS, borrow=stress_b)
            rb = one(g, strategy="red_short", period=per, x=x, cost=BASE_COST_BPS, borrow=live_b)
            rows.append([label, f"{x:g}%", bps(a["mean"]), bps(b["mean"]), f"{bps(b.ci_lo)} to {bps(b.ci_hi)}", num(b.profit_factor),
                         bps(s["mean"]), bps(rb["mean"])])
    A(table(["Sample", "X", "Green, 12 bps (bps)", f"Green, 12 bps + {live_b:.2f} borrow", "95% interval (bps)", "Profit factor",
             f"Green, 12 bps + {stress_b:.0f} borrow", f"Red, 12 bps + {live_b:.2f} borrow"], rows))
    A("")

    A("## Do the venues agree on the lows?\n")
    A("The take-profit depends on N's low, so a wick on one venue can fill a trade that another venue would not.\n")
    A(table(["Venue vs Binance", "Shared 8h bars", "Median low gap (bps)", "90th pct (bps)", "99th pct (bps)", "Largest (bps)",
             "Bars over 10 bps apart", "Last 365d: median (bps)", "Last 365d: 99th pct (bps)", "Last 365d: over 10 bps"],
            [[("OKX" if v == "okx" else "KuCoin"), f"{s['shared_bars']:,}", f"{s['median_abs_bps']:.1f}", f"{s['p90_abs_bps']:.1f}",
              f"{s['p99_abs_bps']:.0f}", f"{s['max_abs_bps']:.0f}", pc(s["share_over_10bps"]), f"{s['median_abs_bps_last_365d']:.1f}",
              f"{s['p99_abs_bps_last_365d']:.1f}", pc(s["share_over_10bps_last_365d"])] for v, s in lows.items()]))
    A("")
    oy = lows["okx"]["share_over_30bps_by_year"]
    big = lows["okx"]["largest_gaps"][0]
    crash = [g_ for g_ in lows["okx"]["largest_gaps"] if g_["candle_open_utc"] >= "2022"][0]
    A(f"The venues disagreed often in the early data and agree closely now: OKX and Binance lows were more than 30 bps apart on "
      f"{pc(oy['2020'])} of 2020 candles, {pc(oy['2021'])} in 2021 and {pc(oy[str(t_end.year)])} in {t_end.year}. The largest gap is "
      f"{abs(big['low_gap_bps']) / 100:.0f}% on the candle that opened {big['candle_open_utc']} UTC, and single-venue wicks still appear in crashes "
      f"({abs(crash['low_gap_bps']) / 100:.0f}% on {crash['candle_open_utc']} UTC). "
      "Does it change which trades fill? Signals that are green on both venues:\n")
    rows = []
    for _, r in ven[ven["sample"].isin(["discovery", "confirmation"])].iterrows():
        rows.append([("OKX" if r.other_venue == "okx" else "KuCoin"), r["sample"].capitalize(), f"{r.x:g}%", int(r.shared_green_signals),
                     pc(r.tp_hit_binance), pc(r.tp_hit_other), pc(r.disagree_share, 2), pc(r.binance_only, 2), pc(r.other_only, 2)])
    A(table(["Other venue", "Sample", "X", "Shared green signals", "TP hit on Binance", "TP hit on other venue", "Venues disagree",
             "Binance only", "Other venue only"], rows))
    A("")
    vd = ven[ven["sample"] == "discovery"]
    assert (vd.binance_only > vd.other_only).all()
    A("On discovery data Binance fills slightly more often than the other venue at every X, so Binance lows flatter the trade a little. "
      "The same rule run end to end on each venue's own candles, mean per trade after 12 bps, entry at C's close:\n")
    rows = []
    for label, g, per in (("Discovery", gd, "discovery"), ("Confirmation", gc, CONF), ("Last 365d", gc, "last 365d")):
        for v in ("binance", "okx", "kucoin"):
            for s in ("green_short", "red_short"):
                rows.append([label, {"binance": "Binance", "okx": "OKX", "kucoin": "KuCoin"}[v], STRAT_LABEL[s],
                             int(one(g, venue=v, strategy=s, period=per, x=X, cost=BASE_COST_BPS).signals)]
                            + [bps(one(g, venue=v, strategy=s, period=per, x=x, cost=BASE_COST_BPS)["mean"]) for x in X_GRID])
    A(table(["Sample", "Venue", "Strategy", "Signals"] + [f"X = {x:g}%" for x in X_GRID], rows))
    A("")
    A("OKX starts in September 2020 and KuCoin in August 2021, so their discovery samples are shorter than Binance's. "
      "No venue turns the discovery result positive at any X.\n")

    A(f"## How far price rose against the short before exit, X = {X:g}%\n")
    A("From Binance 1m candles. Adverse move = highest price reached before the exit, relative to entry. For a take-profit fill the "
      "high of the fill minute is included, which can only overstate it. Leaving that minute out changes neither the median nor the 90th percentile at the precision shown.\n")
    rows = []
    for _, r in exc.iterrows():
        rows.append([{"c_close": "C close", "n_open": "N open"}[r.entry_mode], r["sample"].capitalize(), r.subset.capitalize(), int(r.trades),
                     pc(r.mae_median, 2), pc(r.mae_p90, 2), pc(r.mae_p99, 2), pc(r.mae_max, 1), f"{r.hold_min_median:.0f}",
                     pc(r.time_in_market_share_of_all_bars) if not pd.isna(r.time_in_market_share_of_all_bars) else ""])
    assert (exc.mae_median.round(5) == exc.mae_median_excl_fill_minute.round(5)).all()
    assert (exc.mae_p90.round(5) == exc.mae_p90_excl_fill_minute.round(5)).all()
    A(table(["Entry", "Sample", "Subset", "Trades", "Median adverse move", "90th percentile", "99th percentile", "Worst",
             "Median minutes held", "Share of all clock time in a position"], rows))
    A("")
    ea = exc[(exc.entry_mode == "c_close") & (exc["sample"] == "discovery") & (exc.subset == "all")].iloc[0]
    ee = exc[(exc.entry_mode == "c_close") & (exc["sample"] == "discovery") & (exc.subset == "expired")].iloc[0]
    A(f"To collect {X:g}%, the median discovery trade sat through a {pc(ea.mae_median, 2)} rise and one trade in ten sat through "
      f"{pc(ea.mae_p90, 2)} or more. The trades that never filled were carried a median {pc(ee.mae_median, 2)} against, with no stop, "
      f"and the worst was {pc(ee.mae_max, 1)} in one candle.\n")

    A("## The last 30 green-candle shorts\n")
    A(f"Times are America/Phoenix (UTC-7). X = {X:g}%. Binance spot. Newest first.\n")
    rows = []
    for _, r in last.iterrows():
        rows.append([r.candle_open_phoenix, r.entry_time_phoenix, f"{r.entry:.2f}", f"{r.x_pct:g}%", f"{r.take_profit:.4f}",
                     r.outcome, f"{r.exit:.4f}", f"{r.net_12bps * 100:+.2f}%", f"{r.n_open:.2f}", f"{r.n_open_entry_net_12bps * 100:+.2f}%"])
    A(table(["Signal candle open", "Entry time (C close)", "Entry", "X", "Take-profit", "Result", "Exit price", "Return after 12 bps",
             "N open", "Return if entered at N open"], rows))
    A("")
    A(f"Sum of the 30 returns after 12 bps: {last.net_12bps.sum() * 100:+.2f}%. "
      f"{int((last.outcome != 'expired').sum())} hit the take-profit and {int((last.outcome == 'expired').sum())} expired.\n")

    A("## Reproduce\n")
    A("```bash\npip install -r requirements.txt\npython3 test_rules.py        # fill rule and cost arithmetic\n"
      "python3 fetch_data.py        # only to refresh; data/ holds the frozen sample, cache/ the 1m bars\n"
      "python3 check_data.py\npython3 01_discovery.py      # discovery grid, locks X\n"
      "python3 02_confirmation.py   # reads the last 90 days\npython3 make_report.py\n```\n")
    A("Full grids for every venue, entry, strategy, X, cost and period are in `results/grid_discovery.csv` and `results/grid_confirmation.csv`.")

    (HERE / "REPORT.md").write_text("\n".join(L) + "\n")
    print("wrote REPORT.md", len(L), "blocks")


def _confirmation_price_move() -> tuple[float, float, float]:
    from lib import CONFIRM_DAYS, build_pairs, load_8h

    meta = load_meta()
    p = build_pairs(load_8h("binance"))
    c = p[p["entry_time_ms"] >= meta["t_end_ms"] - CONFIRM_DAYS * 86_400_000]
    p0, p1 = float(c["close"].iloc[0]), float(c["n_close"].iloc[-1])
    return p0, p1, p1 / p0 - 1.0


def _next_candle_means() -> dict[str, float]:
    from lib import CONFIRM_DAYS, build_pairs, load_8h

    meta = load_meta()
    p = build_pairs(load_8h("binance"))
    r = p["n_close"] / p["close"] - 1.0
    conf = p["entry_time_ms"] >= meta["t_end_ms"] - CONFIRM_DAYS * 86_400_000
    return {
        "disc_green": float(r[~conf & p["green"]].mean()), "disc_red": float(r[~conf & p["red"]].mean()),
        "conf_green": float(r[conf & p["green"]].mean()), "conf_red": float(r[conf & p["red"]].mean()),
    }


CONF_P0, CONF_P1, CONF_BH = _confirmation_price_move()
NEXT = _next_candle_means()

if __name__ == "__main__":
    main()
