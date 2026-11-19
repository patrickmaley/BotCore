"""Win rate of the one-dollar green-candle short when it is run with leverage on a fixed SOL size.

Leverage does not change the price path, so the take-profit hit rate is the
same as in 03_dollar_tp.py unless the position is liquidated first. This
script adds that check and restates returns in dollars for a fixed position size.

    python3 04_leverage_15x.py [--size 40] [--leverage 15]

Liquidation follows Jupiter's published formula for a short:
    liq = entry x (1 + collateral/size - close fee - borrow fee - 1/500)
with collateral/size = 1/leverage, close fee 0.06% and the borrow rate fetched with
the data. A liquidated position loses all of its collateral. The adverse move
is measured on Binance spot 1m highs, not on Jupiter's oracle.
"""
from __future__ import annotations

import argparse
import importlib

import numpy as np
import pandas as pd

from lib import BASE_COST_BPS, RESULTS, build_pairs, load_8h, load_meta, net_return, simulate

LEVERAGE = 15.0
SIZE_SOL = 40.0
DOLLARS = 1.0
OPEN_FEE = CLOSE_FEE = 0.0006
MAINTENANCE = 1.0 / 500.0
DAY_MS = 86_400_000
PRICE_BANDS = [0.0, 200.0 / 3.0, 80.0, 100.0, 400.0 / 3.0, 200.0, np.inf]
BAND_LABELS = ["under 66.67", "66.67 to 80", "80 to 100", "100 to 133.33", "133.33 to 200", "200 and over"]


def trades(size_sol: float, leverage: float) -> tuple[pd.DataFrame, float, dict]:
    meta = load_meta()
    borrow = float(meta["jupiter_perps_sol_pool_info"]["shortBorrowRatePercent"]) / 100.0 * 8.0
    liq_move = 1.0 / leverage - CLOSE_FEE - borrow - MAINTENANCE

    c2 = importlib.import_module("02_confirmation")
    tr, _ = c2.excursions({"tp_abs": DOLLARS}, meta)
    tr = tr[tr.entry_mode == "c_close"].reset_index(drop=True)
    pairs = build_pairs(load_8h("binance"))
    pairs = pairs[pairs["green"]].reset_index(drop=True)
    assert (tr.entry_time_ms.to_numpy() == pairs.entry_time_ms.to_numpy()).all()
    sim = simulate(pairs, side="short", entry_mode="c_close", tp_abs=DOLLARS)

    d = pd.concat([tr, sim[["entry", "tp", "exit", "gross", "exit_ratio"]]], axis=1)
    d["net"] = net_return(d.gross.to_numpy(), d.exit_ratio.to_numpy(), BASE_COST_BPS)
    d["hit"] = d.outcome != "expire"
    d["liquidated"] = d.mae_incl >= liq_move
    # The fill minute's high and low cannot be ordered; the count must not depend on it.
    assert (d.liquidated == (d.mae_excl >= liq_move)).all()
    size_usd = d.entry * size_sol
    d["usd_unlevered"] = d.net * size_usd
    d["usd_levered"] = np.where(d.liquidated, -size_usd * (1.0 / leverage + OPEN_FEE), d.usd_unlevered)
    d["hit_levered"] = d.hit & ~d.liquidated
    d["win_levered"] = d.usd_levered > 0
    d["band"] = pd.cut(d.entry, PRICE_BANDS, labels=BAND_LABELS, right=False)
    return d, liq_move, meta


def summarise(s: pd.DataFrame) -> dict:
    win, loss = s.usd_levered[s.win_levered], s.usd_levered[~s.win_levered]
    return {
        "trades": len(s),
        "entry_min": s.entry.min(), "entry_max": s.entry.max(),
        "dollar_as_pct_of_entry_median": (DOLLARS / s.entry).median() * 100.0,
        "target_hit": s.hit.mean(),
        "target_hit_before_liquidation": s.hit_levered.mean(),
        "profitable_after_12bps": s.win_levered.mean(),
        "liquidated": int(s.liquidated.sum()), "liquidated_share": s.liquidated.mean(),
        "liquidated_then_target_would_have_hit": int((s.liquidated & s.hit).sum()),
        "avg_win_usd": win.mean(), "avg_loss_usd": loss.mean(),
        "breakeven_win_rate": -loss.mean() / (win.mean() - loss.mean()),
        "mean_usd_per_trade": s.usd_levered.mean(), "sum_usd": s.usd_levered.sum(), "worst_usd": s.usd_levered.min(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=float, default=SIZE_SOL, help="position size in SOL")
    ap.add_argument("--leverage", type=float, default=LEVERAGE)
    args = ap.parse_args()
    d, liq_move, meta = trades(args.size, args.leverage)
    te = meta["t_end_ms"]
    samples = {"last 90d": d.entry_time_ms >= te - 90 * DAY_MS, "last 365d": d.entry_time_ms >= te - 365 * DAY_MS,
               "full history": d.entry_time_ms > 0}
    tag = {"size_sol": args.size, "leverage": args.leverage, "liquidation_move_pct": liq_move * 100.0}
    rows = [{**tag, "sample": name, "price_band": "all", **summarise(d[m])} for name, m in samples.items()]
    for name in ("last 365d", "full history"):
        for band in BAND_LABELS:
            s = d[samples[name] & (d.band == band)]
            if len(s):
                rows.append({**tag, "sample": name, "price_band": band, **summarise(s)})
    out = pd.DataFrame(rows)
    out.to_csv(RESULTS / f"leverage_{args.leverage:g}x_{args.size:g}sol_summary.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(f"liquidation at +{liq_move * 100:.2f}% above entry; collateral for {args.size:g} SOL at the last close: "
          f"{load_8h('binance')['close'].iloc[-1] * args.size / args.leverage:.2f} USD")
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
