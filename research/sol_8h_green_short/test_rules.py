"""Hand-checked cases for the fill rule and the cost model. Run: python3 test_rules.py"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lib import MS_8H, build_pairs, max_drawdown, net_return, simulate, trade_stats


def candles(rows):
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df.insert(0, "open_time_ms", np.arange(len(df)) * MS_8H)
    return df


def one(c, n, x, side="short", entry_mode="c_close"):
    p = build_pairs(candles([c, n]))
    return simulate(p, x, side, entry_mode).iloc[0]


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

    print("all rule tests passed")


if __name__ == "__main__":
    main()
