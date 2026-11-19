"""Minute-by-minute simulation of one leveraged short, for exits the 8h candles cannot order.

Used for stop-losses, holds longer than one candle, and adding to a losing
short. All prices come from 1m candles. Within one minute the high and the low
cannot be ordered, so when a minute reaches both the take-profit and an
adverse level (stop, add or liquidation) the adverse one is assumed first.

Liquidation follows Jupiter's published formula for a short:
    liq = entry x (1 + 1/leverage - close fee - 1/500 - borrow accrued / size)
A liquidated position loses its collateral and the open fee.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from lib import MS_8H

FEE = 0.0006  # per side, on notional
MAINTENANCE = 1.0 / 500.0
MIN_MS = 60_000


@dataclass
class Minutes:
    t: np.ndarray  # open time of each minute, ms
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray


def _scan(m: Minutes, s: int, b: int, t0: int, down: float, up_fixed: float, ref: float, liq_base: float, borrow_per_min: float):
    """First minute in [s, b) whose low reaches `down` or whose high reaches min(up_fixed, liquidation)."""
    step = 480
    while s < b:
        e = min(s + step, b)
        liq = ref * (1.0 + liq_base - borrow_per_min * (m.t[s:e] - t0) / MIN_MS)
        dn = m.l[s:e] <= down
        up = m.h[s:e] >= np.minimum(up_fixed, liq)
        both = dn | up
        if both.any():
            j = int(np.argmax(both))
            return s + j, bool(dn[j]), bool(up[j]), float(liq[j])
        s, step = e, step * 2
    return None


def run_trade(m: Minutes, t_entry: int, entry: float, *, target: float, stop: float | None = None,
              hold_candles: int | None = 1, add: float | None = None, size: float = 1.0,
              leverage: float = 15.0, borrow_per_hour: float = 0.0) -> dict | None:
    """Short `size` units at `entry` at time `t_entry`.

    target        cover this many dollars below the (average) entry
    stop          buy back this many dollars above entry; None for no stop
    hold_candles  close at market after this many 8h candles; None holds until target, stop or liquidation
    add           short `size` more once price is this many dollars above entry, then
                  cover everything `target` dollars below the average entry
    """
    a = int(np.searchsorted(m.t, t_entry))
    b = len(m.t) if hold_candles is None else int(np.searchsorted(m.t, t_entry + hold_candles * MS_8H))
    if b <= a:
        return None
    liq_base = 1.0 / leverage - FEE - MAINTENANCE
    bpm = borrow_per_hour / 60.0
    up1 = np.inf
    if stop is not None:
        up1 = entry + stop
    if add is not None:
        up1 = min(up1, entry + add)

    legs = [(size, entry, t_entry)]  # (units, fill price, fill time)
    outcome = exit_px = exit_t = None
    ambiguous = False
    ref, tp, s = entry, entry - target, a
    while outcome is None:
        phase2 = len(legs) == 2
        hit = _scan(m, s, b, t_entry, tp, np.inf if phase2 else up1, ref, liq_base, bpm)
        if hit is None:
            outcome, exit_px, exit_t = "expire", float(m.c[b - 1]), int(m.t[b - 1]) + MIN_MS
            break
        k, dn, up, liq = hit
        t_k = int(m.t[k])
        if m.o[k] <= tp:
            # Opened through the target. Only the entry minute fills better than the limit, as in the 8h rule.
            outcome, exit_px, exit_t = "tp", (float(m.o[k]) if k == a and not phase2 else tp), t_k
        elif up:
            ambiguous = dn
            level = np.inf if phase2 else up1
            fill = max(level, float(m.o[k]))
            if fill >= liq:
                outcome, exit_px, exit_t = "liquidated", liq, t_k
            elif add is not None and not phase2 and (stop is None or entry + add <= entry + stop):
                legs.append((size, fill, t_k))
                ref = (entry + fill) / 2.0
                tp = ref - target
                if m.h[k] >= ref * (1.0 + liq_base - bpm * (t_k - t_entry) / MIN_MS):
                    outcome, exit_px, exit_t = "liquidated", ref * (1.0 + liq_base), t_k
                s = k + 1
                if s >= b and outcome is None:
                    outcome, exit_px, exit_t = "expire", float(m.c[b - 1]), int(m.t[b - 1]) + MIN_MS
            else:
                outcome, exit_px, exit_t = "stop", fill, t_k
        else:
            outcome, exit_px, exit_t = "tp", tp, t_k

    notional = sum(u * p for u, p, _ in legs)
    units = sum(u for u, _, _ in legs)
    borrow = sum(u * p * borrow_per_hour * max(exit_t - t, 0) / 3_600_000 for u, p, t in legs)
    if outcome == "liquidated":
        usd = -notional * (1.0 / leverage + FEE)
    else:
        usd = notional - units * exit_px - FEE * (notional + units * exit_px) - borrow
    return {"outcome": outcome, "exit": exit_px, "exit_time_ms": exit_t, "usd": usd, "added": len(legs) == 2,
            "ambiguous_minute": ambiguous, "hold_hours": (exit_t - t_entry) / 3_600_000, "notional": notional}
