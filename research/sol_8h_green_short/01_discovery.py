"""Stage 1. Discovery data only: every trade entered before the last 90 days.

Writes the discovery grid and locks the X that stage 2 applies to the last 90 days.

Selection rule, fixed before any number was looked at:
  the X with the highest mean return per trade after 12 bps for the green-candle
  short, entry at C's close, on Binance spot, over the discovery sample.
"""
from __future__ import annotations

import json

import pandas as pd

from grid import run_grid
from lib import BASE_COST_BPS, CONFIRM_DAYS, RESULTS, load_meta


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    meta = load_meta()
    grid, tests = run_grid("discovery")
    grid.to_csv(RESULTS / "grid_discovery.csv", index=False)
    tests.to_csv(RESULTS / "tests_discovery.csv", index=False)

    sel = grid[
        (grid.venue == "binance") & (grid.entry_mode == "c_close") & (grid.strategy == "green_short")
        & (grid.period == "discovery") & (grid.body_bin == "all") & (grid.cost_bps == BASE_COST_BPS)
        & (grid.borrow_bps == 0)
    ].set_index("x")
    chosen = float(sel["mean"].idxmax())
    conf_start = pd.Timestamp(meta["t_end_ms"] - CONFIRM_DAYS * 86_400_000, unit="ms", tz="UTC")
    out = {
        "rule": "argmax over X of mean net return per trade at 12 bps, green short, entry at C close, "
                "Binance spot, discovery sample only",
        "discovery_entries_before_utc": conf_start.isoformat(),
        "confirmation_entries_from_utc": conf_start.isoformat(),
        "confirmation_entries_to_utc": pd.Timestamp(meta["t_end_ms"] - 8 * 3600 * 1000, unit="ms", tz="UTC").isoformat(),
        "chosen_x_pct": chosen,
        "discovery_mean_net_12bps_by_x": {str(k): v for k, v in sel["mean"].items()},
        "discovery_t_stat_by_x": {str(k): v for k, v in sel["t_stat"].items()},
        "any_x_positive_after_12bps": bool((sel["mean"] > 0).any()),
    }
    (RESULTS / "chosen_x.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
