"""Command line for the Jupiter perps short."""

from __future__ import annotations

import argparse
import sys
import time

from .bot import cycle, phoenix_now, replay_recent
from .config import ConfigError, build_config
from .state import load_state


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--take-profit-pct", type=float, default=None)
    common.add_argument("--collateral-usdc", type=float, default=None)
    common.add_argument("--leverage", type=float, default=None)
    common.add_argument("--state", default=None, help="path to the paper or live state file")
    common.add_argument("--live", action="store_true", help="sign and send Jupiter perps transactions")
    common.add_argument(
        "--i-understand",
        action="store_true",
        help="required with --live. This can lose the collateral.",
    )
    parser = argparse.ArgumentParser(
        description="Short SOL perps after a green 8-hour close and cover a set percent lower."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("once", parents=[common], help="read the market once and act if the rule says to")
    sub.add_parser("run", parents=[common], help="poll until stopped")
    sub.add_parser("status", parents=[common], help="show the saved position and realized paper PnL")
    replay = sub.add_parser(
        "replay",
        parents=[common],
        help="run the rule over recent completed candles",
    )
    replay.add_argument("--candles", type=int, default=300)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = build_config(
            live=args.live,
            i_understand=args.i_understand,
            take_profit_pct=args.take_profit_pct,
            collateral_usdc=args.collateral_usdc,
            leverage=args.leverage,
            state_path=args.state,
        )
    except (ConfigError, ValueError) as exc:
        print(f"config: {exc}", file=sys.stderr)
        return 2

    if args.command == "status":
        state = load_state(config.state_path)
        position = "flat" if state.position is None else (
            f"short {state.position.notional_usd:.2f} USD from {state.position.entry_price:.4f}, "
            f"cover at {state.position.take_profit_price:.4f}"
        )
        print(
            f"{phoenix_now()} {position}, "
            f"realized {state.realized_pnl_usd:+.4f} USD, "
            f"{len(state.trades)} closed trades"
        )
        return 0

    if args.command == "replay":
        try:
            print(replay_recent(config, args.candles))
        except Exception as exc:  # noqa: BLE001 - CLI boundary
            print(f"replay failed: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.live:
        print("Live mode. Jupiter will open a real SOL short with your USDC collateral.")

    def run_once() -> int:
        try:
            print(cycle(config, live=args.live))
        except Exception as exc:  # noqa: BLE001 - keep the loop alive on one bad poll
            print(f"{phoenix_now()} cycle failed: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.command == "once":
        return run_once()

    while True:
        run_once()
        time.sleep(config.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
