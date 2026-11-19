"""Hand-checked cases for the signals and the backtest. Run: python3 test_trend.py"""
from __future__ import annotations

import numpy as np
import pandas as pd

import trend
from trend import DAY_MS, MS_8H, apply_mode, backtest, daily_bars, max_drawdown, signals, stats


def close(a, b, tol=1e-12):
    return abs(a - b) < tol


def main():
    # Signals use only closes up to and including today: changing a later close must not change an earlier signal.
    rng = np.random.default_rng(0)
    c = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.03, 400)))
    full = signals(c)
    for cut in (250, 320, 399):
        part = signals(c[: cut + 1])
        for k in full:
            assert np.array_equal(full[k][: cut + 1], part[k]), (k, cut)

    # sma_10 on a rising then falling line.
    c = np.concatenate([np.arange(1.0, 21.0), np.arange(19.0, 0.0, -1.0)])
    s = signals(np.concatenate([c, np.ones(200)]))
    assert s["sma_10"][8] == 0 and s["sma_10"][9] == 1 and s["sma_10"][19] == 1
    # At index 25 the close is 14 and the 10-day average of 20,19,...,14 with 17..20 before it is above 14.
    assert s["sma_10"][25] == -1
    # mom_7: 0 until 7 days of history, then the sign of the 7-day change.
    assert s["mom_7"][6] == 0 and s["mom_7"][7] == 1 and s["mom_7"][30] == -1
    # don_10: long from the first 10-day closing high, held until a 10-day closing low.
    assert s["don_10"][8] == 0 and s["don_10"][9] == 1
    assert s["don_10"][20] == 1  # 19 is neither a 10-day high nor a 10-day low yet
    # First 10-day closing low: index 24, close 15, window 16,17,18,19,20,19,18,17,16,15.
    first_short = int(np.argmax(s["don_10"][:39] == -1))
    assert first_short == 24 and c[24] == 15.0 and s["don_10"][23] == 1

    # Backtest: long 1x from 100 to 110 over two days, no costs. Equity follows price.
    px = np.array([100.0, 105.0, 110.0, 99.0])
    eq, tr = backtest(px, np.array([1, 1, 0, 0]), 0, 3, fee=0.0)
    assert np.allclose(eq, [1.0, 1.05, 1.10, 1.10]) and len(tr) == 1 and close(tr[0]["ret"], 0.10)
    # The position decided at close t earns the move from t to t+1, never the move into t.
    eq, _ = backtest(px, np.array([0, 0, 1, 0]), 0, 3, fee=0.0)
    assert np.allclose(eq, [1.0, 1.0, 1.0, 0.9])
    # Short: linear in price, like a perp. 100 -> 110 loses 10%, then 110 -> 99 on a fresh short of 0.9 notional.
    eq, tr = backtest(px, np.array([-1, 0, -1, 0]), 0, 3, fee=0.0)
    assert np.allclose(eq, [1.0, 0.95, 0.95, 0.95 * 1.1]) and close(tr[1]["ret"], 0.1)
    # Fees: 6 bps on entry notional and on exit notional.
    eq, tr = backtest(px, np.array([1, 1, 0, 0]), 0, 3, fee=0.0006)
    assert close(eq[1], 1.0 - 0.0006 + 0.05) and close(eq[3], 1.0 - 0.0006 + 0.10 - 0.0006 * 1.10)
    # A flip pays an exit and an entry.
    eq, tr = backtest(px, np.array([1, -1, 0, 0]), 0, 3, fee=0.0006)
    e1 = 1.0 - 0.0006 + 0.05 - 0.0006 * 1.05
    assert close(eq[2], e1 - 0.0006 * e1 - e1 * (110.0 / 105.0 - 1.0)) and len(tr) == 2
    # Borrow: 0.001% per hour on entry notional for two days long.
    eq, _ = backtest(px, np.array([1, 1, 0, 0]), 0, 3, fee=0.0, borrow_long_h=1e-5)
    assert close(eq[2], 1.10 - 1e-5 * 48)
    # Delayed fill: the change decided at close 0 fills at 102, so only 102 -> 105 is earned on day 1.
    eq, _ = backtest(px, np.array([1, 1, 0, 0]), 0, 3, fee=0.0, exec_px=np.array([102.0, 106.0, 108.0, np.nan]))
    assert close(eq[1], 105.0 / 102.0) and close(eq[3], 108.0 / 102.0)
    # Worst adverse move of a short uses the highs after entry.
    _, tr = backtest(px, np.array([-1, -1, 0, 0]), 0, 3, fee=0.0, high=np.array([101.0, 112.0, 111.0, 100.0]), low=px - 1)
    assert close(tr[0]["worst_adverse"], 0.12)
    # Start index: nothing is traded before it and equity starts at 1.
    eq, _ = backtest(px, np.array([1, 1, 1, 0]), 1, 3, fee=0.0)
    assert np.allclose(eq, [1.0, 110.0 / 105.0, 99.0 / 105.0])

    assert close(max_drawdown(np.array([1.0, 1.2, 0.9, 1.5])), 0.25)
    st = stats(*backtest(px, np.array([1, 1, 0, 0]), 0, 3, fee=0.0))
    assert st["trades"] == 1 and st["win_rate"] == 1.0 and close(st["total_return"], 0.10)
    assert np.array_equal(apply_mode(np.array([1.0, -1.0, 0.0]), "long_flat"), [1.0, 0.0, 0.0])

    # Daily bars: three 8h bars per UTC day, a day is dropped if its last bar is missing, and the cut hides later days.
    t = np.arange(8) * MS_8H
    d8 = pd.DataFrame({"open_time_ms": t, "open": 10.0 + np.arange(8), "high": 20.0 + np.arange(8),
                       "low": 5.0 - np.arange(8) * 0.1, "close": 11.0 + np.arange(8)})
    d = daily_bars(d8)
    assert len(d) == 2 and list(d.close) == [13.0, 16.0] and list(d.high) == [22.0, 25.0] and list(d.close_ms) == [DAY_MS, 2 * DAY_MS]
    assert d.exec_delayed.iloc[0] == 14.0 and d.exec_delayed.iloc[1] == 17.0
    cut = daily_bars(d8, end_close_ms=DAY_MS)
    assert len(cut) == 1 and np.isnan(cut.exec_delayed.iloc[0])
    assert trend.DISCOVERY_END_MS == 1735689600000
    print("all trend tests passed")


if __name__ == "__main__":
    main()
