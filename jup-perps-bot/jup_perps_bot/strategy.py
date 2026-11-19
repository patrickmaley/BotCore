"""Decision rules for the 8-hour green-candle short.

The short opens at the close of a green 8-hour candle. It covers when price
trades the take-profit percent below that entry, or at the close of the next
8-hour candle if the target never trades.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import EIGHT_H_MS, Config


@dataclass(frozen=True)
class Candle:
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float

    @property
    def close_time_ms(self) -> int:
        return self.open_time_ms + EIGHT_H_MS

    @property
    def is_green(self) -> bool:
        return self.close > self.open


@dataclass
class Position:
    entry_price: float
    take_profit_price: float
    notional_usd: float
    collateral_usd: float
    signal_open_ms: int
    deadline_ms: int
    opened_at_ms: int
    position_pubkey: str | None = None
    entry_txid: str | None = None


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    consume_signal_open_ms: int | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    signal_open_ms: int | None = None
    deadline_ms: int | None = None


def take_profit_price(entry_price: float, take_profit_pct: float) -> float:
    return entry_price * (1 - take_profit_pct / 100)


def drift_bps(mark: float, reference: float) -> float:
    if reference <= 0:
        raise ValueError("reference price must be positive")
    return abs(mark - reference) / reference * 10_000


def trade_pnl(
    entry_price: float,
    exit_price: float,
    notional_usd: float,
    open_fee_bps: float,
    close_fee_bps: float,
) -> dict[str, float]:
    """Short PnL. A lower exit is a profit."""
    gross = (entry_price - exit_price) / entry_price * notional_usd
    fees = notional_usd * (open_fee_bps + close_fee_bps) / 10_000
    return {"gross_pnl_usd": gross, "fees_usd": fees, "net_pnl_usd": gross - fees}


def decide(
    *,
    position: Position | None,
    latest_closed: Candle | None,
    mark: float,
    now_ms: int,
    last_signal_open_ms: int | None,
    config: Config,
) -> Decision:
    """Choose the next action from information available at now_ms."""
    if mark <= 0:
        return Decision("hold", "mark price is not usable")

    if position is not None:
        if mark <= position.take_profit_price:
            return Decision(
                "close_short",
                "price traded the take-profit below the entry",
                exit_price=position.take_profit_price,
            )
        if now_ms >= position.deadline_ms:
            exit_price = mark
            management_open = position.signal_open_ms + EIGHT_H_MS
            if latest_closed is not None and latest_closed.open_time_ms == management_open:
                exit_price = latest_closed.close
            return Decision(
                "close_short",
                "next 8-hour candle closed without the take-profit",
                exit_price=exit_price,
            )
        return Decision("hold", "short is open and the target has not traded")

    if latest_closed is None:
        return Decision("hold", "no closed 8-hour candle")
    if latest_closed.open_time_ms == last_signal_open_ms:
        return Decision("hold", "this candle was already handled")

    age_ms = now_ms - latest_closed.close_time_ms
    if age_ms > config.max_signal_age_ms:
        return Decision(
            "hold",
            "latest green-or-red close is too old to trade",
            consume_signal_open_ms=latest_closed.open_time_ms,
        )
    if not latest_closed.is_green:
        return Decision(
            "hold",
            "8-hour candle closed red",
            consume_signal_open_ms=latest_closed.open_time_ms,
        )
    if drift_bps(mark, latest_closed.close) > config.max_entry_drift_bps:
        return Decision(
            "hold",
            "mark has moved away from the green close",
            consume_signal_open_ms=latest_closed.open_time_ms,
        )
    return Decision(
        "open_short",
        "8-hour candle closed green",
        consume_signal_open_ms=latest_closed.open_time_ms,
        entry_price=latest_closed.close,
        signal_open_ms=latest_closed.open_time_ms,
        deadline_ms=latest_closed.close_time_ms + EIGHT_H_MS,
    )


def resolve_candle_exit(position: Position, candle: Candle) -> tuple[float, str]:
    """How a resting take-profit fills against one completed 8-hour candle."""
    target = position.take_profit_price
    if candle.open <= target:
        return candle.open, "take_profit"
    if candle.low <= target:
        return target, "take_profit"
    return candle.close, "time_stop"


@dataclass(frozen=True)
class ClosedTrade:
    reason: str
    entry_price: float
    exit_price: float
    notional_usd: float
    collateral_usd: float
    signal_open_ms: int
    gross_pnl_usd: float
    fees_usd: float
    net_pnl_usd: float
    adverse_bps: float


def replay(candles: list[Candle], config: Config) -> list[ClosedTrade]:
    """Walk completed candles with the same open and cover rules as the bot."""
    ordered = sorted(candles, key=lambda candle: candle.open_time_ms)
    position: Position | None = None
    trades: list[ClosedTrade] = []
    for candle in ordered:
        if position is not None:
            exit_price, reason = resolve_candle_exit(position, candle)
            pnl = trade_pnl(
                position.entry_price,
                exit_price,
                position.notional_usd,
                config.open_fee_bps,
                config.close_fee_bps,
            )
            adverse = max(0.0, (candle.high - position.entry_price) / position.entry_price * 10_000)
            trades.append(
                ClosedTrade(
                    reason=reason,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    notional_usd=position.notional_usd,
                    collateral_usd=position.collateral_usd,
                    signal_open_ms=position.signal_open_ms,
                    adverse_bps=adverse,
                    **pnl,
                )
            )
            position = None
        if candle.is_green:
            entry = candle.close
            position = Position(
                entry_price=entry,
                take_profit_price=take_profit_price(entry, config.take_profit_pct),
                notional_usd=config.notional_usd,
                collateral_usd=config.collateral_usdc,
                signal_open_ms=candle.open_time_ms,
                deadline_ms=candle.close_time_ms + EIGHT_H_MS,
                opened_at_ms=candle.close_time_ms,
            )
    return trades
