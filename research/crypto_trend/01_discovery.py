"""Discovery: score all 32 configurations on data that closes on or before 2025-01-01 and lock one.

Nothing here can read the holdout: daily_bars() is always called with the discovery cut.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from trend import (ASSETS, DISCOVERY_END_MS, MODES, RESULTS, WARMUP_DAYS, apply_mode, backtest, borrow_rates, daily_bars,
                   load_8h, sharpe_ci, shift_test, signals, stats, vote)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    bl, bs = borrow_rates()
    costs = {"borrow_long_h": bl, "borrow_short_h": bs}
    rows, cache = [], {}
    for a in ASSETS:
        d = daily_bars(load_8h(a), end_close_ms=DISCOVERY_END_MS)
        assert d.close_ms.max() <= DISCOVERY_END_MS
        c = d.close.to_numpy()
        sig = signals(c)
        sig["vote"] = vote(sig)
        cache[a] = (d, c, sig)
        for rule, s in sig.items():
            for mode in MODES:
                eq, tr = backtest(c, apply_mode(s, mode), WARMUP_DAYS, **costs)
                rows.append({"asset": a, "rule": rule, "mode": mode, **stats(eq, tr)})
        eq, tr = backtest(c, np.ones(len(c)), WARMUP_DAYS)
        rows.append({"asset": a, "rule": "buy_and_hold", "mode": "spot", **stats(eq, tr)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RESULTS / "discovery_grid.csv", index=False)

    cand = grid[~grid.rule.isin(["vote", "buy_and_hold"])]
    sh = cand.pivot_table(index=["rule", "mode"], columns="asset", values="sharpe", dropna=False)[list(ASSETS)]
    # A configuration that lost all its equity on any asset has no Sharpe and scores last.
    sh["score"] = sh[list(ASSETS)].min(axis=1, skipna=False).fillna(-np.inf)
    sh["n"] = [int(r.split("_")[1]) for r, _ in sh.index]
    sh = sh.sort_values(["score", "n"], ascending=False)
    (rule, mode), best = sh.index[0], sh.iloc[0]
    go = bool((best[list(ASSETS)] > 0).all())

    pd.set_option("display.width", 200)
    print("Sharpe after costs, discovery, all 32 configurations (sorted by lowest across assets):")
    print(sh.round(2).to_string())
    print("\nvote and buy-and-hold:")
    print(grid[grid.rule.isin(["vote", "buy_and_hold"])][["asset", "rule", "mode", "total_return", "cagr", "sharpe", "max_drawdown", "trades"]]
          .round(3).to_string(index=False))

    detail = {}
    for a in ASSETS:
        d, c, sig = cache[a]
        pos = apply_mode(sig[rule], mode)
        eq, tr = backtest(c, pos, WARMUP_DAYS, **costs)
        lo, hi = sharpe_ci(eq)
        detail[a] = {**stats(eq, tr), "sharpe_ci": [lo, hi],
                     "shift_test_p": shift_test(c, pos, WARMUP_DAYS, len(c) - 1, **costs),
                     "first_day": str(pd.Timestamp(int(d.close_ms.iloc[WARMUP_DAYS]), unit="ms", tz="UTC").date()),
                     "last_day": str(pd.Timestamp(int(d.close_ms.iloc[-1]), unit="ms", tz="UTC").date())}
    lock = {"rule": rule, "mode": mode, "score_min_sharpe": float(best.score), "proceed_to_holdout": go,
            "discovery_sharpe": {a: float(best[a]) for a in ASSETS}, "discovery_detail": detail,
            "positive_configs_all_assets": int((sh[list(ASSETS)] > 0).all(axis=1).sum()), "configs": len(sh)}
    (RESULTS / "locked.json").write_text(json.dumps(lock, indent=2) + "\n")
    print("\nlocked:", json.dumps(lock, indent=2))


if __name__ == "__main__":
    main()
