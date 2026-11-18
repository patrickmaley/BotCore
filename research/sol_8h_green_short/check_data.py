"""Data integrity and venue comparison. No trade returns are computed here.

  1. Binance 8h bars are contiguous and equal the aggregation of Binance 1m bars.
  2. How often N's open equals C's close on each venue (candle stitching).
  3. How far the venues disagree on the 8h low.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from lib import CACHE, MS_8H, RESULTS, build_pairs, load_8h, load_meta


def pct(a, q):
    return float(np.percentile(a, q))


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    meta = load_meta()
    out: dict = {"t_end_utc": meta["last_completed_8h_close_utc"]}

    b = load_8h("binance")
    steps = np.diff(b["open_time_ms"])
    out["binance_8h"] = {
        "bars": len(b),
        "first_open_utc": str(pd.Timestamp(int(b.open_time_ms.iloc[0]), unit="ms", tz="UTC")),
        "last_open_utc": str(pd.Timestamp(int(b.open_time_ms.iloc[-1]), unit="ms", tz="UTC")),
        "missing_8h_bars": int((steps != MS_8H).sum()),
        "aligned_to_00_08_16_utc": bool((b["open_time_ms"] % MS_8H == 0).all()),
        "doji_bars": int((b.close == b.open).sum()),
        "green_bars": int((b.close > b.open).sum()),
        "red_bars": int((b.close < b.open).sum()),
    }

    m1 = pd.read_parquet(CACHE / "binance_spot_SOLUSDT_1m.parquet")
    g = m1.groupby(m1["open_time_ms"] // MS_8H * MS_8H)
    agg = pd.DataFrame(
        {"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last(), "n": g["open"].size()}
    )
    j = b.set_index("open_time_ms").merge(agg, left_index=True, right_index=True, how="left", suffixes=("", "_1m"))
    out["binance_1m_vs_8h"] = {
        "minutes": len(m1),
        "expected_minutes": len(b) * 480,
        "bars_with_missing_minutes": int((j["n"] != 480).sum()),
        "bars_with_no_minutes": int(j["n"].isna().sum()),
        "open_mismatch": int((j["open"] != j["open_1m"]).sum()),
        "high_mismatch": int((j["high"] != j["high_1m"]).sum()),
        "low_mismatch": int((j["low"] != j["low_1m"]).sum()),
        "close_mismatch": int((j["close"] != j["close_1m"]).sum()),
    }

    stitch = {}
    for v in ["binance", "okx", "kucoin"]:
        p = build_pairs(load_8h(v))
        gap_bps = (p["n_open"] / p["close"] - 1.0) * 1e4
        recent = p["entry_time_ms"] >= meta["t_end_ms"] - 365 * 86_400_000
        stitch[v] = {
            "pairs": len(p),
            "first_open_utc": str(pd.Timestamp(int(p.open_time_ms.iloc[0]), unit="ms", tz="UTC")),
            "share_n_open_equals_c_close": float((p["n_open"] == p["close"]).mean()),
            "share_equal_last_365d": float((p.loc[recent, "n_open"] == p.loc[recent, "close"]).mean()),
            "mean_gap_bps": float(gap_bps.mean()),
            "median_abs_gap_bps": float(gap_bps.abs().median()),
            "p90_abs_gap_bps": pct(gap_bps.abs(), 90),
            "p99_abs_gap_bps": pct(gap_bps.abs(), 99),
            "max_abs_gap_bps": float(gap_bps.abs().max()),
            "median_abs_gap_bps_last_365d": float(gap_bps[recent].abs().median()),
            "p99_abs_gap_bps_last_365d": pct(gap_bps[recent].abs(), 99),
        }
    out["stitching"] = stitch

    lows = {}
    bi = b.set_index("open_time_ms")
    for v in ["okx", "kucoin"]:
        o = load_8h(v).set_index("open_time_ms")
        jj = bi.merge(o, left_index=True, right_index=True, how="inner", suffixes=("", "_o"))
        d = (jj["low_o"] / jj["low"] - 1.0) * 1e4
        recent = jj.index >= meta["t_end_ms"] - 365 * 86_400_000
        lows[v] = {
            "shared_bars": len(jj),
            "mean_bps_vs_binance": float(d.mean()),
            "median_abs_bps": float(d.abs().median()),
            "p90_abs_bps": pct(d.abs(), 90),
            "p99_abs_bps": pct(d.abs(), 99),
            "max_abs_bps": float(d.abs().max()),
            "share_over_10bps": float((d.abs() > 10).mean()),
            "share_over_30bps": float((d.abs() > 30).mean()),
            "median_abs_bps_last_365d": float(d[recent].abs().median()),
            "p99_abs_bps_last_365d": pct(d[recent].abs(), 99),
            "share_over_10bps_last_365d": float((d[recent].abs() > 10).mean()),
            "color_disagreement_share": float(
                ((jj["close"] > jj["open"]) != (jj["close_o"] > jj["open_o"])).mean()
            ),
        }
    out["low_disagreement"] = lows

    (RESULTS / "data_checks.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
