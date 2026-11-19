"""Hand-checked cases for the fill rule and the cost model. Run: python3 test_rules.py"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib import MS_8H, build_pairs, max_drawdown, net_return, simulate, trade_stats
from path_sim import Minutes, run_trade


def minutes(rows, start=0):
    a = np.array(rows, dtype=float)
    return Minutes(start + np.arange(len(a), dtype=np.int64) * 60_000, a[:, 0], a[:, 1], a[:, 2], a[:, 3])


def path_tests():
    flat = (100.0, 100.1, 99.9, 100.0)
    kw = dict(size=10.0, leverage=15.0)
    fee = lambda entry, exit_, units=10.0: 0.0006 * units * (entry + exit_)

    # Target one dollar below: filled at the limit, not at the low.
    r = run_trade(minutes([flat, (100.0, 100.2, 98.5, 98.8), flat]), 0, 100.0, target=1.0, **kw)
    assert r["outcome"] == "tp" and close(r["exit"], 99.0) and close(r["usd"], 10.0 - fee(100.0, 99.0))
    # Entry minute opens through the target: filled at that open.
    r = run_trade(minutes([(98.7, 98.9, 98.5, 98.8), flat]), 0, 100.0, target=1.0, **kw)
    assert r["outcome"] == "tp" and close(r["exit"], 98.7)
    # Never reached: closed at the last close inside the hold window (2 minutes of data inside one 8h candle).
    r = run_trade(minutes([flat, (100.0, 100.6, 99.5, 100.4)]), 0, 100.0, target=1.0, **kw)
    assert r["outcome"] == "expire" and close(r["exit"], 100.4) and close(r["usd"], -4.0 - fee(100.0, 100.4))
    # Stop two dollars above: filled at the stop.
    r = run_trade(minutes([flat, (100.0, 102.5, 99.8, 102.2), flat]), 0, 100.0, target=1.0, stop=2.0, **kw)
    assert r["outcome"] == "stop" and close(r["exit"], 102.0) and close(r["usd"], -20.0 - fee(100.0, 102.0))
    # A minute that opens above the stop fills at its open.
    r = run_trade(minutes([flat, (102.6, 102.9, 102.4, 102.7)]), 0, 100.0, target=1.0, stop=2.0, **kw)
    assert r["outcome"] == "stop" and close(r["exit"], 102.6)
    # Same minute reaches stop and target: the stop is assumed first.
    r = run_trade(minutes([flat, (100.0, 102.1, 98.9, 100.0)]), 0, 100.0, target=1.0, stop=2.0, **kw)
    assert r["outcome"] == "stop" and r["ambiguous_minute"]
    # Liquidation at 15x: 100 x (1 + 1/15 - 0.0006 - 0.002) = 106.4067. Loses collateral plus the open fee.
    r = run_trade(minutes([flat, (100.0, 106.5, 99.9, 106.0), (106.0, 106.1, 98.0, 98.5)]), 0, 100.0, target=1.0, **kw)
    assert r["outcome"] == "liquidated" and close(r["usd"], -1000.0 * (1 / 15 + 0.0006))
    r = run_trade(minutes([flat, (100.0, 106.3, 99.9, 106.0), (106.0, 106.1, 98.0, 98.5)]), 0, 100.0, target=1.0, **kw)
    assert r["outcome"] == "tp"
    # A stop beyond the liquidation level never fills.
    r = run_trade(minutes([flat, (100.0, 108.0, 99.9, 107.0)]), 0, 100.0, target=1.0, stop=7.0, **kw)
    assert r["outcome"] == "liquidated"
    # Add 10 more at +2: average entry 101, new target 100. Both legs covered at 100.
    r = run_trade(minutes([flat, (100.0, 102.3, 99.9, 102.0), (102.0, 102.1, 99.5, 99.8)]), 0, 100.0, target=1.0, add=2.0, **kw)
    assert r["outcome"] == "tp" and r["added"] and close(r["exit"], 100.0)
    assert close(r["usd"], 0.0 + 20.0 - 0.0006 * (1000.0 + 1020.0 + 2000.0))
    # Added, then never came back: both legs closed at the last close.
    r = run_trade(minutes([flat, (100.0, 102.3, 99.9, 102.0), (102.0, 103.2, 101.5, 103.0)]), 0, 100.0, target=1.0, add=2.0, **kw)
    assert r["outcome"] == "expire" and close(r["usd"], -30.0 - 10.0 - 0.0006 * (1000.0 + 1020.0 + 2060.0))
    # Hold window: one candle ends the trade at the 8h boundary, no limit carries on to the target.
    m = Minutes(np.array([0, 60_000, MS_8H], dtype=np.int64), *(np.array(x, dtype=float) for x in
                ([100.0, 100.0, 100.5], [100.1, 100.6, 100.6], [99.9, 99.9, 98.9], [100.0, 100.5, 99.0])))
    r = run_trade(m, 0, 100.0, target=1.0, **kw)
    assert r["outcome"] == "expire" and close(r["exit"], 100.5) and r["exit_time_ms"] == 120_000
    r = run_trade(m, 0, 100.0, target=1.0, hold_candles=None, **kw)
    assert r["outcome"] == "tp" and r["exit_time_ms"] == MS_8H
    # Borrow: 0.001% per hour on 1000 dollars, target reached in the minute that opens one hour after entry.
    r = run_trade(minutes([flat] * 60 + [(100.0, 100.1, 98.9, 99.0)]), 0, 100.0, target=1.0, borrow_per_hour=1e-5, **kw)
    assert r["outcome"] == "tp" and close(r["hold_hours"], 1.0) and close(r["usd"], 10.0 - fee(100.0, 99.0) - 0.01)


def candles(rows):
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df.insert(0, "open_time_ms", np.arange(len(df)) * MS_8H)
    return df


def one(c, n, x=None, side="short", entry_mode="c_close", tp_abs=None):
    p = build_pairs(candles([c, n]))
    return simulate(p, x, side, entry_mode, tp_abs=tp_abs).iloc[0]


def close(a, b):
    return abs(a - b) < 1e-12


def main():
    green = (99.0, 101.0, 98.0, 100.0)

    # Low touches the take-profit, open above it: fill is the limit price, not the low.
    r = one(green, (100.0, 100.5, 97.0, 100.2), 1.0)
    assert r.outcome == "tp" and close(r.tp, 99.0) and close(r.exit, 99.0) and close(r.gross, 0.01)

    # Low exactly equal to the take-profit counts as a touch.
    r = one(green, (100.0, 100.5, 99.0, 100.2), 1.0)
    assert r.outcome == "tp" and close(r.exit, 99.0)

    # N opens below the take-profit: cover at N's open, which is better than the limit.
    r = one(green, (98.5, 99.5, 98.0, 99.2), 1.0)
    assert r.outcome == "gap" and close(r.exit, 98.5) and close(r.gross, 0.015)

    # N opens exactly at the take-profit: cover at the open.
    r = one(green, (99.0, 99.5, 98.0, 99.2), 1.0)
    assert r.outcome == "gap" and close(r.exit, 99.0)

    # Never trades down to the take-profit: cover at N's close, here a loss.
    r = one(green, (100.0, 104.0, 99.01, 103.0), 1.0)
    assert r.outcome == "expire" and close(r.exit, 103.0) and close(r.gross, -0.03)

    # Entry at N's open moves the take-profit with it and cannot gap-fill.
    r = one(green, (100.4, 100.5, 99.3, 100.2), 1.0, entry_mode="n_open")
    assert close(r.entry, 100.4) and close(r.tp, 99.396) and r.outcome == "tp"
    r0 = one(green, (100.4, 100.5, 99.3, 100.2), 1.0)
    assert r0.outcome == "expire" and close(r0.gross, -0.002)

    # Flipped trade: buy the close, sell X% higher, mirror of the short.
    r = one(green, (100.0, 101.5, 99.0, 100.2), 1.0, side="long")
    assert r.outcome == "tp" and close(r.exit, 101.0) and close(r.gross, 0.01)
    r = one(green, (101.5, 102.0, 101.0, 101.2), 1.0, side="long")
    assert r.outcome == "gap" and close(r.exit, 101.5) and close(r.gross, 0.015)
    r = one(green, (100.0, 100.9, 97.0, 98.0), 1.0, side="long")
    assert r.outcome == "expire" and close(r.gross, -0.02)

    # Fixed-dollar take-profit: one dollar below a 100.00 entry is 99.00, below a 50.00 entry is 49.00.
    r = one(green, (100.0, 100.5, 98.9, 100.2), tp_abs=1.0)
    assert r.outcome == "tp" and close(r.tp, 99.0) and close(r.exit, 99.0) and close(r.gross, 0.01)
    r = one((49.0, 51.0, 48.0, 50.0), (50.0, 50.5, 48.9, 50.2), tp_abs=1.0)
    assert r.outcome == "tp" and close(r.tp, 49.0) and close(r.gross, 0.02)
    r = one((49.0, 51.0, 48.0, 50.0), (50.0, 50.5, 49.01, 50.4), tp_abs=1.0)
    assert r.outcome == "expire" and close(r.gross, -0.008)
    r = one(green, (98.9, 99.5, 98.0, 99.2), tp_abs=1.0)
    assert r.outcome == "gap" and close(r.exit, 98.9)
    r = one(green, (100.2, 100.5, 99.1, 100.2), tp_abs=1.0, entry_mode="n_open")
    assert close(r.tp, 99.2) and r.outcome == "tp"
    r = one(green, (100.0, 101.0, 99.0, 100.2), tp_abs=1.0, side="long")
    assert r.outcome == "tp" and close(r.exit, 101.0)
    # Below a one-dollar price the target is unreachable and the trade is a one-candle hold.
    r = one((0.7, 0.9, 0.6, 0.8), (0.8, 0.85, 0.5, 0.6), tp_abs=1.0)
    assert r.outcome == "expire" and close(r.gross, 0.25)
    try:
        one(green, green, 1.0, tp_abs=1.0)
        raise AssertionError("both targets accepted")
    except ValueError:
        pass

    # Costs: 12 bps round trip = 6 bps on entry notional + 6 bps on exit notional.
    net = net_return(np.array([0.01]), np.array([0.99]), 12)
    assert close(net[0], 0.01 - 0.0006 - 0.0006 * 0.99)
    net = net_return(np.array([0.01]), np.array([0.99]), 12, borrow_bps=0.56)
    assert close(net[0], 0.01 - 0.0006 - 0.0006 * 0.99 - 0.000056)
    assert close(net_return(np.array([0.01]), np.array([0.99]), 0)[0], 0.01)

    # A missing 8h bar must not pair C with a later candle.
    df = candles([green, green, green]).drop(index=1)
    assert len(build_pairs(df)) == 0

    # Doji is neither green nor red.
    p = build_pairs(candles([(100.0, 101.0, 99.0, 100.0), green]))
    assert not p.green.iloc[0] and not p.red.iloc[0]

    # Drawdown of the compounded curve and basic stats.
    assert close(max_drawdown(np.array([0.10, -0.50, 0.20])), 0.5)
    s = trade_stats(np.array([0.02, -0.01, 0.01, -0.03]), np.array(["tp", "expire", "gap", "expire"]), 8)
    assert s["signals"] == 4 and close(s["tp_share"], 0.5) and close(s["expire_share"], 0.5)
    assert close(s["win_rate"], 0.5) and close(s["avg_win"], 0.015) and close(s["avg_loss"], -0.02)
    assert close(s["profit_factor"], 0.75) and close(s["bars_in_position"], 0.5)

    path_tests()
    print("all rule tests passed")


if __name__ == "__main__":
    main()
