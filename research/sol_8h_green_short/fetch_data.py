"""Download SOL/USDT candles and freeze the sample.

Venues
  binance  spot SOLUSDT   native 8h klines + 1m klines (public archive + API)
  okx      spot SOL-USDT  1H candles, aggregated to 8h on 00/08/16 UTC
  kucoin   spot SOL-USDT  native 8h candles

Only completed bars are kept. The forming 8h bar is dropped on every venue.
Run once; the outputs under data/ are the frozen sample every other script reads.
"""
from __future__ import annotations

import io
import json
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CACHE = HERE / "cache"
MS_8H = 8 * 3600 * 1000
COLS = ["open_time_ms", "open", "high", "low", "close", "volume"]


def http_get(url: str, tries: int = 6, timeout: int = 60) -> bytes:
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sol-8h-research/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            last = e
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(1.5 * 2**i)
    raise RuntimeError(f"GET failed {url}: {last}")


def binance_klines_api(interval: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    rows = []
    cur = start_ms
    while cur < end_ms:
        url = (
            "https://data-api.binance.vision/api/v3/klines?symbol=SOLUSDT"
            f"&interval={interval}&startTime={cur}&endTime={end_ms - 1}&limit=1000"
        )
        batch = json.loads(http_get(url))
        if not batch:
            break
        rows.extend(batch)
        cur = batch[-1][0] + 1
        if len(batch) < 1000:
            break
    df = pd.DataFrame([r[:6] for r in rows], columns=COLS)
    return df.astype({"open_time_ms": "int64", "open": float, "high": float, "low": float, "close": float, "volume": float})


def binance_1m_month(ym: str) -> pd.DataFrame | None:
    url = f"https://data.binance.vision/data/spot/monthly/klines/SOLUSDT/1m/SOLUSDT-1m-{ym}.zip"
    try:
        raw = http_get(url)
    except urllib.error.HTTPError:
        return None
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, header=None, usecols=range(6), names=COLS)
    # The archive switched from millisecond to microsecond timestamps in 2025.
    ts = df["open_time_ms"].astype("int64")
    df["open_time_ms"] = np.where(ts > 10**14, ts // 1000, ts)
    return df


def fetch_binance(now_ms: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    k8 = binance_klines_api("8h", 0, now_ms)
    k8 = k8[k8["open_time_ms"] + MS_8H <= now_ms].reset_index(drop=True)
    t_end = int(k8["open_time_ms"].iloc[-1]) + MS_8H

    months = pd.period_range(
        pd.Timestamp(k8["open_time_ms"].iloc[0], unit="ms"), pd.Timestamp(t_end, unit="ms"), freq="M"
    ).strftime("%Y-%m")
    with ThreadPoolExecutor(8) as ex:
        parts = list(ex.map(binance_1m_month, months))
    missing = [m for m, p in zip(months, parts) if p is None]
    got = [p for p in parts if p is not None]
    m1 = pd.concat(got, ignore_index=True)
    # Months the archive has not published yet come from the REST API.
    tail_start = int(m1["open_time_ms"].max()) + 60_000
    if missing:
        print("archive missing months (filled from API):", missing)
    tail = binance_klines_api("1m", tail_start, t_end)
    m1 = pd.concat([m1, tail], ignore_index=True)
    m1 = m1[m1["open_time_ms"] < t_end].drop_duplicates("open_time_ms").sort_values("open_time_ms")
    return k8, m1.reset_index(drop=True)


def fetch_okx_1h(t_end: int) -> pd.DataFrame:
    rows = []
    after = t_end
    while True:
        url = f"https://www.okx.com/api/v5/market/history-candles?instId=SOL-USDT&bar=1H&after={after}&limit=100"
        d = json.loads(http_get(url))
        if d.get("code") != "0":
            raise RuntimeError(f"okx error {d}")
        batch = d["data"]
        if not batch:
            break
        rows.extend(batch)
        after = int(batch[-1][0])
        time.sleep(0.11)
    df = pd.DataFrame([r[:6] for r in rows], columns=COLS)
    df = df.astype({"open_time_ms": "int64", "open": float, "high": float, "low": float, "close": float, "volume": float})
    return df.drop_duplicates("open_time_ms").sort_values("open_time_ms").reset_index(drop=True)


def aggregate_to_8h(df: pd.DataFrame, expected_per_bar: int) -> pd.DataFrame:
    b = df["open_time_ms"] // MS_8H * MS_8H
    g = df.groupby(b)
    out = pd.DataFrame(
        {
            "open": g["open"].first(),
            "high": g["high"].max(),
            "low": g["low"].min(),
            "close": g["close"].last(),
            "volume": g["volume"].sum(),
            "n_sub": g["open"].size(),
        }
    )
    out.index.name = "open_time_ms"
    out = out.reset_index()
    out["complete"] = out["n_sub"] == expected_per_bar
    return out


def fetch_kucoin_8h(t_end: int) -> pd.DataFrame:
    rows = []
    end_s = t_end // 1000
    span = 1400 * 8 * 3600
    empty = 0
    while empty < 2:
        start_s = end_s - span
        url = f"https://api.kucoin.com/api/v1/market/candles?type=8hour&symbol=SOL-USDT&startAt={start_s}&endAt={end_s}"
        d = json.loads(http_get(url))
        batch = d.get("data") or []
        empty = 0 if batch else empty + 1
        rows.extend(batch)
        end_s = start_s
        time.sleep(0.4)
    df = pd.DataFrame(rows, columns=["t", "open", "close", "high", "low", "volume", "turnover"])
    df["open_time_ms"] = df["t"].astype("int64") * 1000
    df = df[COLS].astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    df = df[df["open_time_ms"] + MS_8H <= t_end]
    return df.drop_duplicates("open_time_ms").sort_values("open_time_ms").reset_index(drop=True)


def main() -> None:
    DATA.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    now_ms = int(time.time() * 1000)

    k8, m1 = fetch_binance(now_ms)
    t_end = int(k8["open_time_ms"].iloc[-1]) + MS_8H
    k8.to_csv(DATA / "binance_spot_SOLUSDT_8h.csv", index=False)
    m1.to_parquet(CACHE / "binance_spot_SOLUSDT_1m.parquet", index=False)
    print("binance 8h bars", len(k8), "1m bars", len(m1))

    okx1h = fetch_okx_1h(t_end)
    okx8 = aggregate_to_8h(okx1h, 8)
    okx8 = okx8[okx8["open_time_ms"] + MS_8H <= t_end]
    okx8.to_csv(DATA / "okx_spot_SOL-USDT_8h_from_1h.csv", index=False)
    print("okx 1h bars", len(okx1h), "8h bars", len(okx8), "incomplete", int((~okx8["complete"]).sum()))

    ku8 = fetch_kucoin_8h(t_end)
    ku8.to_csv(DATA / "kucoin_spot_SOL-USDT_8h.csv", index=False)
    print("kucoin 8h bars", len(ku8))

    jup = json.loads(http_get("https://perps-api.jup.ag/v1/pool-info?mint=So11111111111111111111111111111111111111112"))

    meta = {
        "fetched_at_utc": pd.Timestamp(now_ms, unit="ms", tz="UTC").isoformat(),
        "last_completed_8h_close_utc": pd.Timestamp(t_end, unit="ms", tz="UTC").isoformat(),
        "t_end_ms": t_end,
        "binance_first_8h_open_utc": pd.Timestamp(int(k8["open_time_ms"].iloc[0]), unit="ms", tz="UTC").isoformat(),
        "okx_first_8h_open_utc": pd.Timestamp(int(okx8["open_time_ms"].iloc[0]), unit="ms", tz="UTC").isoformat(),
        "kucoin_first_8h_open_utc": pd.Timestamp(int(ku8["open_time_ms"].iloc[0]), unit="ms", tz="UTC").isoformat(),
        "jupiter_perps_sol_pool_info": jup,
    }
    (DATA / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    sys.exit(main())
