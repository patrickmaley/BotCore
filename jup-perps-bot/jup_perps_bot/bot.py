"""One decision cycle: read the market, then paper-fill or send a perps order."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from .candles import fetch_closed_candles
from .config import Config
from .perps import PerpsClient, parse_usd
from .state import BotState, load_state, save_state
from .strategy import Decision, Position, decide, replay, trade_pnl

PHOENIX = timezone(timedelta(hours=-7))


def phoenix_now(now_ms: int | None = None) -> str:
    moment = datetime.fromtimestamp((now_ms or time.time() * 1000) / 1000, PHOENIX)
    return moment.strftime("%Y-%m-%d %H:%M:%S Phoenix")


class LiveGuardError(RuntimeError):
    pass


def apply_paper(state: BotState, decision: Decision, config: Config, now_ms: int) -> str:
    if decision.consume_signal_open_ms is not None:
        state.last_signal_open_ms = decision.consume_signal_open_ms
    if decision.action == "open_short":
        assert decision.entry_price is not None
        assert decision.signal_open_ms is not None
        assert decision.deadline_ms is not None
        state.position = Position(
            entry_price=decision.entry_price,
            take_profit_price=decision.entry_price * (1 - config.take_profit_pct / 100),
            notional_usd=config.notional_usd,
            collateral_usd=config.collateral_usdc,
            signal_open_ms=decision.signal_open_ms,
            deadline_ms=decision.deadline_ms,
            opened_at_ms=now_ms,
        )
        return (
            f"paper short at {decision.entry_price:.4f}, "
            f"cover at {state.position.take_profit_price:.4f}"
        )
    if decision.action == "close_short":
        assert state.position is not None
        assert decision.exit_price is not None
        text = _record_close(state, decision.exit_price, decision.reason, config, now_ms, None)
        return f"paper {text}"
    return decision.reason


def _record_close(
    state: BotState,
    exit_price: float,
    reason: str,
    config: Config,
    now_ms: int,
    exit_txid: str | None,
) -> str:
    position = state.position
    assert position is not None
    pnl = trade_pnl(
        position.entry_price,
        exit_price,
        position.notional_usd,
        config.open_fee_bps,
        config.close_fee_bps,
    )
    state.realized_pnl_usd += pnl["net_pnl_usd"]
    state.trades.append(
        {
            "reason": reason,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "notional_usd": position.notional_usd,
            "net_pnl_usd": pnl["net_pnl_usd"],
            "fees_usd": pnl["fees_usd"],
            "opened_at_ms": position.opened_at_ms,
            "closed_at_ms": now_ms,
            "entry_txid": position.entry_txid,
            "exit_txid": exit_txid,
        }
    )
    state.position = None
    return (
        f"cover {reason} at {exit_price:.4f}, "
        f"net {pnl['net_pnl_usd']:+.4f} USD, "
        f"realized {state.realized_pnl_usd:+.4f} USD"
    )


def apply_live(
    state: BotState,
    decision: Decision,
    config: Config,
    client: PerpsClient,
    now_ms: int,
    sign_transaction,
) -> str:
    if decision.consume_signal_open_ms is not None:
        state.last_signal_open_ms = decision.consume_signal_open_ms
    if decision.action == "hold":
        return decision.reason
    wallet = config.wallet_address
    assert wallet is not None
    existing = client.sol_short(wallet)
    if decision.action == "open_short":
        if existing is not None:
            raise LiveGuardError("wallet already has a SOL short; refusing to add")
        if state.position is not None:
            raise LiveGuardError("local state already has a short")
        built = client.build_short(
            wallet_address=wallet,
            collateral_usdc=config.collateral_usdc,
            leverage=config.leverage,
            slippage_bps=config.slippage_bps,
        )
        quote = built.get("quote") or {}
        fill = parse_usd(quote["averagePriceUsd"])
        reference = decision.entry_price or fill
        from .strategy import drift_bps

        if drift_bps(fill, reference) > config.max_entry_drift_bps:
            return (
                f"discarded unsigned short: quote {fill:.4f} drifted from close {reference:.4f}"
            )
        txid = _sign_and_send(client, built, "increase-position", sign_transaction)
        assert decision.signal_open_ms is not None
        assert decision.deadline_ms is not None
        state.position = Position(
            entry_price=fill,
            take_profit_price=fill * (1 - config.take_profit_pct / 100),
            notional_usd=parse_usd(quote.get("positionSizeUsd") or quote.get("sizeUsdDelta")),
            collateral_usd=config.collateral_usdc,
            signal_open_ms=decision.signal_open_ms,
            deadline_ms=decision.deadline_ms,
            opened_at_ms=now_ms,
            position_pubkey=built.get("positionPubkey"),
            entry_txid=txid,
        )
        return f"live short tx {txid} at {fill:.4f}, cover at {state.position.take_profit_price:.4f}"
    if decision.action == "close_short":
        pubkey = (state.position.position_pubkey if state.position else None) or (
            existing.get("positionPubkey") if existing else None
        )
        if pubkey is None:
            raise LiveGuardError("no position pubkey to close")
        built = client.build_close(pubkey, config.slippage_bps)
        txid = _sign_and_send(client, built, "decrease-position", sign_transaction)
        exit_price = decision.exit_price if decision.exit_price is not None else client.mark_price()
        text = _record_close(state, exit_price, decision.reason, config, now_ms, txid)
        return f"live {text}, tx {txid}"
    return decision.reason


def _sign_and_send(client: PerpsClient, built: dict, action: str, sign_transaction) -> str:
    raw_tx = built.get("serializedTxBase64")
    if not raw_tx:
        raise LiveGuardError("Jupiter did not return a transaction")
    signed = sign_transaction(raw_tx)
    return client.execute(action, signed)


def cycle(config: Config, *, live: bool, now_ms: int | None = None) -> str:
    now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
    state = load_state(config.state_path)
    client = PerpsClient(config.perps_url)
    mark = client.mark_price()
    candles = fetch_closed_candles(now_ms=now_ms, url=config.candle_url)
    latest = candles[-1] if candles else None
    decision = decide(
        position=state.position,
        latest_closed=latest,
        mark=mark,
        now_ms=now_ms,
        last_signal_open_ms=state.last_signal_open_ms,
        config=config,
    )
    if live:
        from .signer import load_keypair, sign_serialized_transaction

        assert config.keypair_path is not None
        keypair = load_keypair(config.keypair_path)
        if config.wallet_address != str(keypair.pubkey()):
            raise LiveGuardError("JUP_BOT_WALLET does not match the keypair")

        def sign_transaction(raw_tx: str) -> str:
            return sign_serialized_transaction(raw_tx, keypair)

        def act(choice: Decision) -> str:
            return apply_live(state, choice, config, client, now_ms, sign_transaction)
    else:
        def act(choice: Decision) -> str:
            return apply_paper(state, choice, config, now_ms)

    message = act(decision)
    # A time stop happens at a candle close, which can itself be a new green signal.
    if decision.action == "close_short" and state.position is None:
        follow_up = decide(
            position=None,
            latest_closed=latest,
            mark=mark,
            now_ms=now_ms,
            last_signal_open_ms=state.last_signal_open_ms,
            config=config,
        )
        if follow_up.action == "open_short":
            message = f"{message} | {act(follow_up)}"
    save_state(config.state_path, state)
    close_text = f"{latest.close:.4f}" if latest else "none"
    return f"{phoenix_now(now_ms)} mark {mark:.4f} last close {close_text} | {message}"


def replay_recent(config: Config, candles_to_load: int = 300) -> str:
    now_ms = int(time.time() * 1000)
    candles = fetch_closed_candles(now_ms=now_ms, limit=candles_to_load, url=config.candle_url)
    trades = replay(candles, config)
    if not trades:
        return "replay found no closed shorts"
    net = sum(trade.net_pnl_usd for trade in trades)
    hits = sum(1 for trade in trades if trade.reason == "take_profit")
    return (
        f"replay {len(trades)} shorts, take-profit {hits / len(trades) * 100:.1f}%, "
        f"net {net:+.2f} USD after {config.round_trip_fee_bps:.0f} bps "
        f"on ${config.notional_usd:.2f} notional"
    )
