"""Paper cycle, candle parsing, and the live-trading locks."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from jup_perps_bot.bot import cycle
from jup_perps_bot.candles import parse_mexc_klines
from jup_perps_bot.config import EIGHT_H_MS, ConfigError, build_config
from jup_perps_bot.perps import parse_usd
from jup_perps_bot.state import BotState, Position, save_state


class ParseTests(unittest.TestCase):
    def test_scaled_and_decimal_usd(self) -> None:
        self.assertAlmostEqual(parse_usd("74684000"), 74.684)
        self.assertAlmostEqual(parse_usd("74.684"), 74.684)

    def test_forming_candle_is_dropped(self) -> None:
        forming_open = EIGHT_H_MS * 10
        rows = [
            [forming_open - EIGHT_H_MS, "100", "102", "99", "101", "1", forming_open],
            [forming_open, "101", "103", "100", "102", "1", forming_open + EIGHT_H_MS],
        ]
        candles = parse_mexc_klines(rows, now_ms=forming_open + 1_000)
        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0].close, 101)


class ConfigLockTests(unittest.TestCase):
    def test_live_requires_both_locks_and_a_wallet(self) -> None:
        with self.assertRaises(ConfigError):
            build_config(live=True, i_understand=True)
        with self.assertRaises(ConfigError):
            build_config(live=True, i_understand=False)

    def test_leverage_cap(self) -> None:
        with self.assertRaises(ConfigError):
            build_config(leverage=20)


class PaperCycleTests(unittest.TestCase):
    def test_time_stop_then_new_green_close_opens_again(self) -> None:
        state_path = Path("/tmp/jup-perps-bot-paper-test.json")
        signal_open = 0
        management_open = EIGHT_H_MS
        management = [
            management_open,
            "100",
            "102",
            "100.2",
            "101",
            "1",
            management_open + EIGHT_H_MS,
        ]
        # The management candle is the one that just closed, and it is green.
        # Entry was the previous candle. Its close is not in this fetch; state holds the short.
        save_state(
            str(state_path),
            BotState(
                position=Position(
                    entry_price=100,
                    take_profit_price=99,
                    notional_usd=20,
                    collateral_usd=10,
                    signal_open_ms=signal_open,
                    deadline_ms=management_open + EIGHT_H_MS,
                    opened_at_ms=management_open,
                ),
                last_signal_open_ms=signal_open,
            ),
        )
        config = build_config(state_path=str(state_path), take_profit_pct=1, collateral_usdc=10, leverage=2)

        import jup_perps_bot.bot as bot_module

        def fake_candles(**_kwargs):
            return parse_mexc_klines([management], now_ms=management_open + EIGHT_H_MS + 5_000)

        original_price = bot_module.PerpsClient.mark_price
        original_fetch = bot_module.fetch_closed_candles
        bot_module.PerpsClient.mark_price = lambda self: 101.05  # type: ignore[method-assign]
        bot_module.fetch_closed_candles = fake_candles  # type: ignore[assignment]
        try:
            text = cycle(
                config,
                live=False,
                now_ms=management_open + EIGHT_H_MS + 5_000,
            )
        finally:
            bot_module.PerpsClient.mark_price = original_price  # type: ignore[method-assign]
            bot_module.fetch_closed_candles = original_fetch  # type: ignore[assignment]

        self.assertIn("cover", text)
        self.assertIn("paper short at 101.0000", text)
        saved = json.loads(state_path.read_text())
        self.assertIsNotNone(saved["position"])
        self.assertAlmostEqual(saved["position"]["entry_price"], 101)
        self.assertAlmostEqual(saved["position"]["take_profit_price"], 99.99)
        state_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
