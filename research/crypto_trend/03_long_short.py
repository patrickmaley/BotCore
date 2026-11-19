"""Follow-up: the same trend rules with shorts allowed.

Two long/short rules, neither chosen by looking at the holdout:
  picked  the long/short configuration the protocol's selection rule picks on discovery data
          (highest worst-asset Sharpe after costs), read from results/discovery_grid.csv
  vote    long when most of the 16 signals are long, short when most are short, flat on a tie.
          Defined in PROTOCOL.md before any result; it has no fitted parameter.

This is not a second clean test. The holdout was read by 02_holdout.py first, and that run already
showed the vote's long/short return and every configuration's return. Writes REPORT_LONG_SHORT.md.
"""
from __future__ import annotations

import importlib
import json

import numpy as np
import pandas as pd

from trend import (ASSETS, DISCOVERY_END_MS, FEE, HERE, RESULTS, WARMUP_DAYS, backtest, borrow_rates, daily_bars, load_8h,
                   sharpe_ci, shift_test, signals, stats, vote)

h = importlib.import_module("02_holdout")
pct, table, PHX = h.pct, h.table, h.PHX
LEVERAGES = (1, 2, 3, 5, 15)
MAINTENANCE = 1.0 / 500.0


def pick_long_short() -> str:
    g = pd.read_csv(RESULTS / "discovery_grid.csv")
    g = g[(g["mode"] == "long_short") & ~g.rule.isin(["vote", "buy_and_hold"])]
    sh = g.pivot_table(index="rule", columns="asset", values="sharpe", dropna=False)[list(ASSETS)]
    sh["score"] = sh.min(axis=1, skipna=False).fillna(-np.inf)
    sh["n"] = [int(r.split("_")[1]) for r in sh.index]
    return sh.sort_values(["score", "n"], ascending=False).index[0]


def verdict(ret: dict, late: float, doubled: float) -> str:
    if ret["SOL"] <= 0:
        return "discard"
    if sum(v > 0 for v in ret.values()) >= 2 and late > 0 and doubled > 0:
        return "paper trade"
    return "watch"


def main() -> None:
    bl, bs = borrow_rates()
    base = {"fee": FEE, "borrow_long_h": bl, "borrow_short_h": bs}
    double = {"fee": 2 * FEE, "borrow_long_h": 2 * bl, "borrow_short_h": 2 * bs}
    picked = pick_long_short()
    rules = {"picked": picked, "vote": "vote"}
    label = {"picked": f"{picked}, long/short (picked on discovery)", "vote": "vote of 16 signals, long/short"}

    rows, trades, state = [], [], {}
    for a in ASSETS:
        d = daily_bars(load_8h(a))
        c, hi, lo = d.close.to_numpy(), d.high.to_numpy(), d.low.to_numpy()
        sig = signals(c)
        sig["vote"] = vote(sig)
        s = int(np.flatnonzero(d.close_ms.to_numpy() == DISCOVERY_END_MS)[0])
        e = len(c) - 1
        for key, rule in rules.items():
            pos = sig[rule]
            for sample, (i0, i1) in {"discovery": (WARMUP_DAYS, s), "holdout": (s, e)}.items():
                eq, tr = backtest(c, pos, i0, i1, **base, high=hi, low=lo)
                ci = sharpe_ci(eq) if eq.min() > 0 else (np.nan, np.nan)
                t = pd.DataFrame(tr)
                by_side = {sd: float(np.prod(1.0 + t.ret[t.side == v]) - 1.0) for sd, v in (("long", 1), ("short", -1))}
                liq = {}
                for L in LEVERAGES:
                    rate = np.where(t.side > 0, bl, bs)
                    liq[f"liquidated_{L}x"] = int((t.worst_adverse >= 1.0 / L - FEE - MAINTENANCE - rate * 24.0 * t.days).sum())
                bh, _ = backtest(c, np.ones(len(c)), i0, i1, fee=FEE)
                row = {"asset": a, "rule": key, "sample": sample, **stats(eq, tr), "sharpe_lo": ci[0], "sharpe_hi": ci[1],
                       "shift_test_p": shift_test(c, pos, i0, i1, **base) if eq.min() > 0 else np.nan,
                       "long_trades_return": by_side["long"], "short_trades_return": by_side["short"],
                       "all_trades": len(t), **liq, "buy_and_hold": bh[-1] - 1.0}
                if sample == "holdout":
                    row["fill_8h_late"] = backtest(c, pos, i0, i1, exec_px=d.exec_delayed.to_numpy(), **base)[0][-1] - 1.0
                    row["doubled_costs"] = backtest(c, pos, i0, i1, **double)[0][-1] - 1.0
                    t["asset"], t["rule"] = a, key
                    for col in ("entry", "exit"):
                        t[f"{col}_time_phoenix"] = (pd.to_datetime(d.close_ms.to_numpy()[t[f"{col}_idx"]], unit="ms", utc=True)
                                                    .tz_convert(PHX).strftime("%Y-%m-%d %H:%M"))
                    trades.append(t.drop(columns=["entry_idx", "exit_idx"]))
                rows.append(row)
            if a == "SOL":
                since = int(np.flatnonzero(pos != pos[-1])[-1]) + 1
                state[key] = {"position": int(pos[-1]),
                              "since_phoenix": pd.Timestamp(int(d.close_ms.iloc[since]), unit="ms", tz="UTC").tz_convert(PHX).strftime("%Y-%m-%d %H:%M"),
                              "price_then": float(c[since]), "last_close": float(c[-1]),
                              "signals_long": int(sum(v[-1] > 0 for k, v in sig.items() if k != "vote")),
                              "signals_short": int(sum(v[-1] < 0 for k, v in sig.items() if k != "vote"))}
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / "long_short_summary.csv", index=False)
    pd.concat(trades, ignore_index=True).to_csv(RESULTS / "long_short_holdout_trades.csv", index=False)

    def get(a, key, sample="holdout"):
        return out[(out.asset == a) & (out.rule == key) & (out["sample"] == sample)].iloc[0]

    verdicts = {k: verdict({a: get(a, k).total_return for a in ASSETS}, get("SOL", k).fill_8h_late, get("SOL", k).doubled_costs)
                for k in rules}
    grid = pd.read_csv(RESULTS / "holdout_grid.csv")
    ls = grid[grid["mode"] == "long_short"]
    headline = {"picked_rule": picked, "criteria_outcome": verdicts, "sol_state": state,
                "holdout": {k: {a: float(get(a, k).total_return) for a in ASSETS} for k in rules},
                "long_short_configs_positive": {a: int((ls[ls.asset == a].total_return > 0).sum()) for a in ASSETS}}
    (RESULTS / "long_short_headline.json").write_text(json.dumps(headline, indent=2) + "\n")
    print(json.dumps(headline, indent=2))

    L: list[str] = []
    A = L.append
    A("# Trend following with shorts allowed\n")
    A("Follow-up to `REPORT.md`. Same data, costs and holdout. Two long/short rules, neither chosen from holdout results:\n")
    n = int(picked.split("_")[1])
    A(f"- **Picked**: `{picked}` long/short, the configuration the protocol's selection rule picks among the 16 long/short ones on discovery data. "
      f"Long from a new {n}-day closing high, short from a new {n}-day closing low.")
    A("- **Vote**: long when most of the 16 signals are long, short when most are short, flat on a tie. Written into `PROTOCOL.md` before any result.\n")
    A("**This is not a clean test.** The holdout had already been read, and that run showed the vote's long/short return.\n")
    for sample, title in (("holdout", "Holdout, 2025-01-01 to 2026-11-18, after costs"), ("discovery", "Discovery, through 2025-01-01, after costs")):
        A(f"## {title}\n")
        body = []
        for k in rules:
            for a in ASSETS:
                r = get(a, k, sample)
                body.append([label[k], a, pct(r.total_return), pct(r.buy_and_hold), f"{r.sharpe:.2f}", f"{r.sharpe_lo:.2f} to {r.sharpe_hi:.2f}",
                             pct(-r.max_drawdown), int(r.trades), pct(r.win_rate, 0).lstrip("+"), pct(r.avg_win), pct(r.avg_loss),
                             pct(r.long_trades_return), pct(r.short_trades_return), f"{r.shift_test_p:.3f}"])
        A(table(["Rule", "Asset", "Return", "Buy and hold", "Sharpe", "95% interval", "Max drawdown", "Closed trades", "Win rate",
                 "Average win", "Average loss", "From long trades", "From short trades", "Shift test p"], body))
        A("")
    A("## Holdout sensitivities and the protocol's criteria\n")
    body = []
    for k in rules:
        for a in ASSETS:
            r = get(a, k)
            body.append([label[k], a, pct(r.total_return), pct(r.fill_8h_late), pct(r.doubled_costs)])
    A(table(["Rule", "Asset", "Base", "Fill 8h late", "Doubled costs"], body))
    A("")
    for k in rules:
        A(f"- {label[k]}: the protocol's criteria give **{verdicts[k]}**.")
    A("")
    A(f"All 16 long/short configurations on the holdout: positive on SOL {headline['long_short_configs_positive']['SOL']}, "
      f"BTC {headline['long_short_configs_positive']['BTC']}, ETH {headline['long_short_configs_positive']['ETH']}. "
      f"Median return: SOL {pct(ls[ls.asset == 'SOL'].total_return.median())}, BTC {pct(ls[ls.asset == 'BTC'].total_return.median())}, "
      f"ETH {pct(ls[ls.asset == 'ETH'].total_return.median())}.\n")
    A("## Leverage\n")
    A("Trades that would have been liquidated before their exit, discovery and holdout together, from daily highs and lows.\n")
    body = []
    for k in rules:
        for Lv in LEVERAGES:
            body.append([label[k], f"{Lv}x"] + [
                f"{int(get(a, k, 'discovery')[f'liquidated_{Lv}x'] + get(a, k)[f'liquidated_{Lv}x'])} of "
                f"{int(get(a, k, 'discovery').all_trades + get(a, k).all_trades)}" for a in ASSETS])
    A(table(["Rule", "Leverage"] + list(ASSETS), body))
    A("")
    A("## Where the rules stand on SOL\n")
    word = {1: "long", -1: "short", 0: "flat"}
    for k in rules:
        st = state[k]
        A(f"- {label[k]}: **{word[st['position']]}** since {st['since_phoenix']} Phoenix time (SOL {st['price_then']:.2f}); last close {st['last_close']:.2f}."
          + (f" Of the 16 signals, {st['signals_long']} long and {st['signals_short']} short." if k == "vote" else ""))
    A("")
    A("Trades: `results/long_short_holdout_trades.csv`. Regenerate: `python3 03_long_short.py`.")
    (HERE / "REPORT_LONG_SHORT.md").write_text("\n".join(L) + "\n")
    print("wrote REPORT_LONG_SHORT.md")


if __name__ == "__main__":
    main()
