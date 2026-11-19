"""Download Binance spot BTCUSDT and ETHUSDT 8h candles up to the freeze used by the SOL study.

SOL is read from ../sol_8h_green_short/data, so all three assets end at the same candle.
"""
from __future__ import annotations

import json
import time
import urllib.request

import pandas as pd

from trend import DATA, MS_8H, load_meta

COLS = ["open_time_ms", "open", "high", "low", "close", "volume"]


def http_get(url: str, tries: int = 6) -> bytes:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "crypto-trend-research/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * 2**i)
    raise RuntimeError(f"GET failed {url}: {last}")


def klines_8h(symbol: str, end_ms: int) -> pd.DataFrame:
    rows, cur = [], 0
    while cur < end_ms:
        url = (f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=8h"
               f"&startTime={cur}&endTime={end_ms - 1}&limit=1000")
        batch = json.loads(http_get(url))
        if not batch:
            break
        rows.extend(batch)
        cur = batch[-1][0] + 1
        if len(batch) < 1000:
            break
    df = pd.DataFrame([r[:6] for r in rows], columns=COLS).astype(
        {"open_time_ms": "int64", "open": float, "high": float, "low": float, "close": float, "volume": float})
    return df[df.open_time_ms + MS_8H <= end_ms].drop_duplicates("open_time_ms").reset_index(drop=True)


def main() -> None:
    t_end = load_meta()["t_end_ms"]
    DATA.mkdir(exist_ok=True)
    for asset in ("BTC", "ETH"):
        df = klines_8h(f"{asset}USDT", t_end)
        df.to_csv(DATA / f"binance_spot_{asset}USDT_8h.csv", index=False)
        gaps = int((df.open_time_ms.diff().dropna() != MS_8H).sum())
        print(asset, len(df), "bars", pd.to_datetime(df.open_time_ms.iloc[[0, -1]], unit="ms", utc=True).dt.strftime("%Y-%m-%d %H:%M").tolist(),
              "gaps:", gaps)


if __name__ == "__main__":
    main()
