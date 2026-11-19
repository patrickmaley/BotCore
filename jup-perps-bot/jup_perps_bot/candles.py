"""8-hour SOL/USDT candles. The forming candle is never a signal."""

from __future__ import annotations

import json
import urllib.request

from .config import DEFAULT_CANDLE_URL, EIGHT_H_MS
from .strategy import Candle


class CandleError(RuntimeError):
    pass


def parse_mexc_klines(rows: list[list], now_ms: int) -> list[Candle]:
    candles: list[Candle] = []
    for row in rows:
        open_time_ms = int(row[0])
        if open_time_ms % EIGHT_H_MS != 0:
            raise CandleError(f"candle open {open_time_ms} is not aligned to 8 hours")
        candle = Candle(
            open_time_ms=open_time_ms,
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
        )
        if candle.close_time_ms <= now_ms:
            candles.append(candle)
    candles.sort(key=lambda candle: candle.open_time_ms)
    return candles


def fetch_closed_candles(
    *,
    now_ms: int,
    limit: int = 10,
    url: str = DEFAULT_CANDLE_URL,
    timeout: float = 20,
) -> list[Candle]:
    request_url = f"{url}?symbol=SOLUSDT&interval=8h&limit={limit}"
    request = urllib.request.Request(request_url, headers={"User-Agent": "jup-perps-bot"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except Exception as exc:  # noqa: BLE001 - surface a single candle error to the loop
        raise CandleError(f"candle request failed: {exc}") from exc
    if not isinstance(payload, list):
        raise CandleError("candle response was not a list")
    return parse_mexc_klines(payload, now_ms)
