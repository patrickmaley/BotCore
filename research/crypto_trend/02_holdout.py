"""Holdout: test the locked rule on the days after 2025-01-01 and write REPORT.md.

Reads results/locked.json. Selects nothing. The verdict logic is the one fixed in PROTOCOL.md.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from trend import (ASSETS, DISCOVERY_END_MS, FEE, HERE, MODES, RESULTS, WARMUP_DAYS, apply_mode, backtest, borrow_rates,
                   daily_bars, load_8h, sharpe_ci, shift_test, signals, stats, vote)

LEVERAGES = (2, 3, 5, 10, 15)
MAINTENANCE = 1.0 / 500.0
PHX = "America/Phoenix"


def pct(x: float, d: int = 1) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def table(head: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] + ["---:"] * (len(head) - 1)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main() -> None:
    lock = json.loads((RESULTS / "locked.json").read_text())
    assert lock["proceed_to_holdout"]
    rule, mode = lock["rule"], lock["mode"]
    bl, bs = borrow_rates()
    base = {"fee": FEE, "borrow_long_h": bl, "borrow_short_h": bs}
    double = {"fee": 2 * FEE, "borrow_long_h": 2 * bl, "borrow_short_h": 2 * bs}
    spot = {"fee": FEE, "borrow_long_h": 0.0, "borrow_short_h": 0.0}

    data = {}
    for a in ASSETS:
        d = daily_bars(load_8h(a))
        c = d.close.to_numpy()
        sig = signals(c)
        sig["vote"] = vote(sig)
        s = int(np.flatnonzero(d.close_ms.to_numpy() == DISCOVERY_END_MS)[0])
        data[a] = (d, c, sig, s, len(c) - 1)

    rows, grid, detail = [], [], {}
    for a in ASSETS:
        d, c, sig, s, e = data[a]
        hl = {"high": d.high.to_numpy(), "low": d.low.to_numpy()}
        pos = apply_mode(sig[rule], mode)
        variants = {
            "locked rule": (pos, base, None),
            "locked rule, fill 8h late": (pos, base, d.exec_delayed.to_numpy()),
            "locked rule, doubled costs": (pos, double, None),
            "locked rule, fill 8h late and doubled costs": (pos, double, d.exec_delayed.to_numpy()),
            "locked rule, spot (no borrow)": (pos, spot, None),
            "vote of 16 signals, long/flat": (apply_mode(sig["vote"], "long_flat"), base, None),
            "vote of 16 signals, long/short": (sig["vote"], base, None),
            "buy and hold (spot)": (np.ones(len(c)), spot, None),
        }
        for name, (p, cost, ex) in variants.items():
            eq, tr = backtest(c, p, s, e, exec_px=ex, **cost, **hl)
            rows.append({"asset": a, "variant": name, **stats(eq, tr)})
            if name == "locked rule":
                lo, hi = sharpe_ci(eq)
                detail[a] = {"sharpe_ci": [lo, hi], "shift_test_p": shift_test(c, p, s, e, **cost), "equity": eq, "trades": tr}
        for r, sg in sig.items():
            if r == "vote":
                continue
            for m in MODES:
                eq, tr = backtest(c, apply_mode(sg, m), s, e, **base)
                grid.append({"asset": a, "rule": r, "mode": m, **stats(eq, tr)})
    summ = pd.DataFrame(rows)
    summ.to_csv(RESULTS / "holdout_summary.csv", index=False)
    grid = pd.DataFrame(grid)
    grid.to_csv(RESULTS / "holdout_grid.csv", index=False)

    def get(a, v):
        return summ[(summ.asset == a) & (summ.variant == v)].iloc[0]

    # Verdict, exactly as written in PROTOCOL.md.
    sol = get("SOL", "locked rule")
    n_pos = sum(get(a, "locked rule").total_return > 0 for a in ASSETS)
    late_ok = get("SOL", "locked rule, fill 8h late").total_return > 0
    cost_ok = get("SOL", "locked rule, doubled costs").total_return > 0
    if sol.total_return <= 0:
        verdict = "discard"
    elif n_pos >= 2 and late_ok and cost_ok:
        verdict = "paper trade"
    else:
        verdict = "watch"

    # Full history of the locked rule, for the trade list, calendar years and leverage.
    full, lev_rows, year_rows = {}, [], []
    for a in ASSETS:
        d, c, sig, s, e = data[a]
        pos = apply_mode(sig[rule], mode)
        eq, tr = backtest(c, pos, WARMUP_DAYS, e, **base, high=d.high.to_numpy(), low=d.low.to_numpy())
        bh, _ = backtest(c, np.ones(len(c)), WARMUP_DAYS, e, **spot)
        t = pd.DataFrame(tr)
        t["asset"] = a
        t["entry_close_ms"] = d.close_ms.to_numpy()[t.entry_idx]
        t["exit_close_ms"] = d.close_ms.to_numpy()[t.exit_idx]
        t["sample"] = np.where(t.entry_close_ms >= DISCOVERY_END_MS, "holdout", "discovery")
        full[a] = t
        for L in LEVERAGES:
            thr = 1.0 / L - FEE - MAINTENANCE - bl * 24.0 * t.days
            for smp in ("discovery", "holdout"):
                x = t[t["sample"] == smp]
                lev_rows.append({"asset": a, "sample": smp, "leverage": L, "trades": len(x),
                                 "liquidated": int((x.worst_adverse >= thr[x.index]).sum())})
        # A day that closes at 00:00 on Jan 1 belongs to the year that just ended.
        years = pd.to_datetime(d.close_ms.to_numpy()[WARMUP_DAYS:] - 1, unit="ms", utc=True).year
        for y in sorted(set(years)):
            idx = np.flatnonzero(years == y)
            i0, i1 = max(idx[0] - 1, 0), idx[-1]
            year_rows.append({"asset": a, "year": int(y), "rule": eq[i1] / eq[i0] - 1.0, "buy_and_hold": bh[i1] / bh[i0] - 1.0,
                              "sample": "holdout" if y >= 2025 else "discovery"})
    lev = pd.DataFrame(lev_rows)
    lev.to_csv(RESULTS / "leverage.csv", index=False)
    yr = pd.DataFrame(year_rows)
    yr.to_csv(RESULTS / "calendar_years.csv", index=False)
    all_trades = pd.concat(full.values(), ignore_index=True)
    for col in ("entry", "exit"):
        all_trades[f"{col}_time_phoenix"] = (pd.to_datetime(all_trades[f"{col}_close_ms"], unit="ms", utc=True)
                                             .dt.tz_convert(PHX).dt.strftime("%Y-%m-%d %H:%M"))
    all_trades.drop(columns=["entry_idx", "exit_idx"]).to_csv(RESULTS / "locked_rule_trades.csv", index=False)

    d, c, sig, s, e = data["SOL"]
    now_pos = int(apply_mode(sig[rule], mode)[-1])
    last_close = pd.Timestamp(int(d.close_ms.iloc[-1]), unit="ms", tz="UTC")
    n = int(rule.split("_")[1])
    hi_n, lo_n = float(d.close.iloc[-n:].max()), float(d.close.iloc[-n:].min())
    headline = {
        "rule": rule, "mode": mode, "verdict": verdict,
        "sol_holdout": {k: (float(sol[k]) if isinstance(sol[k], (float, np.floating)) else int(sol[k]))
                        for k in ("total_return", "cagr", "sharpe", "max_drawdown", "trades", "win_rate", "avg_win", "avg_loss")},
        "sol_holdout_sharpe_ci": detail["SOL"]["sharpe_ci"], "sol_holdout_shift_test_p": detail["SOL"]["shift_test_p"],
        "holdout_total_return": {a: float(get(a, "locked rule").total_return) for a in ASSETS},
        "holdout_buy_and_hold": {a: float(get(a, "buy and hold (spot)").total_return) for a in ASSETS},
        "assets_positive": int(n_pos), "sol_positive_fill_8h_late": bool(late_ok), "sol_positive_doubled_costs": bool(cost_ok),
        "holdout_configs_positive_on_sol": int((grid[grid.asset == "SOL"].total_return > 0).sum()), "configs": 32,
        "sol_position_now": now_pos, "sol_last_close": float(c[-1]), "sol_n_day_high_close": hi_n, "sol_n_day_low_close": lo_n,
    }
    (RESULTS / "holdout_headline.json").write_text(json.dumps(headline, indent=2) + "\n")
    print(json.dumps(headline, indent=2))

    # ---- report ----
    L: list[str] = []
    A = L.append
    hold_from = pd.Timestamp(DISCOVERY_END_MS, unit="ms", tz="UTC")
    A("# Trend following on SOL, BTC and ETH\n")
    A(f"Protocol: `PROTOCOL.md`. Verdict by its rules: **{verdict}**.\n")
    A("## The rule\n")
    A(f"At each daily close (00:00 UTC, 5:00 PM in Phoenix): if the close is the highest close of the last {n} days, be long. "
      f"If it is the lowest close of the last {n} days, be in cash. Otherwise do nothing. No target, no stop, 1x notional.\n")
    A(f"It was picked from 32 configurations on data through {hold_from:%Y-%m-%d} because it had the highest worst-asset Sharpe ratio "
      f"after costs (SOL {lock['discovery_sharpe']['SOL']:.2f}, BTC {lock['discovery_sharpe']['BTC']:.2f}, ETH {lock['discovery_sharpe']['ETH']:.2f}). "
      f"{lock['positive_configs_all_assets']} of the 32 were positive on all three assets in discovery.\n")
    A(f"## Holdout: {hold_from:%Y-%m-%d} to {last_close:%Y-%m-%d}, after costs\n")
    rows_ = []
    for a in ASSETS:
        r, b = get(a, "locked rule"), get(a, "buy and hold (spot)")
        ci = detail[a]["sharpe_ci"]
        rows_.append([a, pct(r.total_return), pct(b.total_return), f"{r.sharpe:.2f}", f"{ci[0]:.2f} to {ci[1]:.2f}", pct(-r.max_drawdown),
                      pct(-b.max_drawdown), int(r.trades), pct(r.win_rate, 0).lstrip("+"), pct(r.avg_win), pct(r.avg_loss),
                      pct(r.time_in_market, 0).lstrip("+"), f"{detail[a]['shift_test_p']:.2f}"])
    A(table(["Asset", "Rule return", "Buy and hold", "Sharpe", "95% interval", "Rule max drawdown", "Buy and hold max drawdown",
             "Closed trades", "Win rate", "Average win", "Average loss", "Time in market", "Shift test p"], rows_))
    A("")
    A("Shift test p: share of randomly time-shifted copies of the same positions that did at least as well. Small means the timing mattered.\n")
    A("## Holdout sensitivities, total return after costs\n")
    names = [v for v in summ.variant.unique()]
    A(table(["Variant"] + list(ASSETS), [[v] + [pct(get(a, v).total_return) for a in ASSETS] for v in names]))
    A("")
    g = grid.pivot_table(index=["rule", "mode"], columns="asset", values="total_return")[list(ASSETS)]
    A(f"All 32 configurations on the holdout (for context, not selection): positive on SOL {int((g.SOL > 0).sum())}, "
      f"on BTC {int((g.BTC > 0).sum())}, on ETH {int((g.ETH > 0).sum())}. Median return: SOL {pct(g.SOL.median())}, "
      f"BTC {pct(g.BTC.median())}, ETH {pct(g.ETH.median())}. Long/flat only: SOL {pct(g.xs('long_flat', level='mode').SOL.median())}; "
      f"long/short only: SOL {pct(g.xs('long_short', level='mode').SOL.median())}.\n")
    A("## Calendar years, locked rule against buy and hold\n")
    ys = sorted(yr.year.unique())
    rows_ = []
    for y in ys:
        row = [f"{y}" + (" (holdout)" if y >= 2025 else "")]
        for a in ASSETS:
            x = yr[(yr.asset == a) & (yr.year == y)]
            row += [pct(x.rule.iloc[0]), pct(x.buy_and_hold.iloc[0])] if len(x) else ["", ""]
        rows_.append(row)
    A(table(["Year"] + [f"{a} {k}" for a in ASSETS for k in ("rule", "buy and hold")], rows_))
    A("")
    A("The first year of each asset starts 200 days after its first candle. 2026 ends on the last close in the data.\n")
    A("## Leverage\n")
    A("Trades of the locked rule that would have been liquidated before their exit, using daily lows and Jupiter's formula.\n")
    rows_ = []
    for Lv in LEVERAGES:
        row = [f"{Lv}x"]
        for a in ASSETS:
            x = lev[(lev.asset == a) & (lev.leverage == Lv)]
            row.append(f"{int(x.liquidated.sum())} of {int(x.trades.sum())}")
        rows_.append(row)
    A(table(["Leverage"] + list(ASSETS), rows_))
    A("")
    A("## SOL trades in the holdout\n")
    A("Times are America/Phoenix (UTC-7).\n")
    t = all_trades[(all_trades.asset == "SOL") & (all_trades["sample"] == "holdout")]
    A(table(["Entry", "Entry price", "Exit", "Exit price", "Days", "Return after costs", "Worst move against"],
            [[r.entry_time_phoenix, f"{r.entry:.2f}", r.exit_time_phoenix + (" (still open)" if r.open else ""), f"{r.exit:.2f}",
              int(r.days), pct(r.ret), pct(-r.worst_adverse)] for r in t.itertuples()]))
    A("")
    A(f"As of the close on {last_close.tz_convert(PHX):%Y-%m-%d %H:%M} Phoenix time SOL closed at {c[-1]:.2f} and the rule is "
      f"{'long' if now_pos > 0 else 'in cash'}. The {n}-day closing high is {hi_n:.2f} and the {n}-day closing low is {lo_n:.2f}.\n")
    A("Regenerate: `python3 fetch_data.py && python3 01_discovery.py && python3 02_holdout.py`.")
    (HERE / "REPORT.md").write_text("\n".join(L) + "\n")
    print("wrote REPORT.md")


if __name__ == "__main__":
    main()
