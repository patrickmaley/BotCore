"""Rules for opening and covering the short."""

from __future__ import annotations

import unittest

from jup_perps_bot.config import EIGHT_H_MS, Config
from jup_perps_bot.strategy import Candle, Position, decide, replay, trade_pnl


def candle(open_ms: int, open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(open_ms, open_, high, low, close)


class DecideTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config(take_profit_pct=1.0, max_signal_age_ms=15 * 60 * 1000)

    def test_green_close_opens_a_short_at_that_close(self) -> None:
        signal = candle(0, 100, 102, 99, 101)
        decision = decide(
            position=None,
            latest_closed=signal,
            mark=101.1,
            now_ms=signal.close_time_ms + 1_000,
            last_signal_open_ms=None,
            config=self.config,
        )
        self.assertEqual(decision.action, "open_short")
        self.assertEqual(decision.entry_price, 101)
        self.assertEqual(decision.deadline_ms, signal.close_time_ms + EIGHT_H_MS)

    def test_red_close_does_not_open(self) -> None:
        signal = candle(0, 101, 102, 99, 100)
        decision = decide(
            position=None,
            latest_closed=signal,
            mark=100,
            now_ms=signal.close_time_ms + 1_000,
            last_signal_open_ms=None,
            config=self.config,
        )
        self.assertEqual(decision.action, "hold")
        self.assertEqual(decision.consume_signal_open_ms, signal.open_time_ms)

    def test_old_green_candle_is_not_traded_on_startup(self) -> None:
        signal = candle(0, 100, 102, 99, 101)
        decision = decide(
            position=None,
            latest_closed=signal,
            mark=101,
            now_ms=signal.close_time_ms + 60 * 60 * 1000,
            last_signal_open_ms=None,
            config=self.config,
        )
        self.assertEqual(decision.action, "hold")
        self.assertIn("too old", decision.reason)

    def test_mark_that_ran_away_from_the_close_is_skipped(self) -> None:
        signal = candle(0, 100, 105, 99, 101)
        decision = decide(
            position=None,
            latest_closed=signal,
            mark=103,
            now_ms=signal.close_time_ms + 1_000,
            last_signal_open_ms=None,
            config=self.config,
        )
        self.assertEqual(decision.action, "hold")
        self.assertIn("moved away", decision.reason)

    def test_cover_when_price_trades_the_target(self) -> None:
        position = Position(
            entry_price=100,
            take_profit_price=99,
            notional_usd=20,
            collateral_usd=10,
            signal_open_ms=0,
            deadline_ms=EIGHT_H_MS * 2,
            opened_at_ms=EIGHT_H_MS,
        )
        decision = decide(
            position=position,
            latest_closed=None,
            mark=98.5,
            now_ms=EIGHT_H_MS + 60_000,
            last_signal_open_ms=0,
            config=self.config,
        )
        self.assertEqual(decision.action, "close_short")
        self.assertEqual(decision.exit_price, 99)
        self.assertIn("take-profit", decision.reason)

    def test_cover_at_the_next_close_when_the_target_never_trades(self) -> None:
        position = Position(
            entry_price=100,
            take_profit_price=99,
            notional_usd=20,
            collateral_usd=10,
            signal_open_ms=0,
            deadline_ms=EIGHT_H_MS * 2,
            opened_at_ms=EIGHT_H_MS,
        )
        management = candle(EIGHT_H_MS, 100, 101, 99.4, 100.4)
        decision = decide(
            position=position,
            latest_closed=management,
            mark=100.5,
            now_ms=management.close_time_ms + 1_000,
            last_signal_open_ms=0,
            config=self.config,
        )
        self.assertEqual(decision.action, "close_short")
        self.assertEqual(decision.exit_price, 100.4)

    def test_a_handled_candle_is_not_reused(self) -> None:
        signal = candle(0, 100, 102, 99, 101)
        decision = decide(
            position=None,
            latest_closed=signal,
            mark=101,
            now_ms=signal.close_time_ms + 1_000,
            last_signal_open_ms=signal.open_time_ms,
            config=self.config,
        )
        self.assertEqual(decision.action, "hold")
        self.assertIn("already handled", decision.reason)


class ReplayTests(unittest.TestCase):
    def test_limit_fills_at_the_target_not_the_low(self) -> None:
        config = Config(take_profit_pct=1, collateral_usdc=10, leverage=2, open_fee_bps=6, close_fee_bps=6)
        trades = replay(
            [
                candle(0, 100, 102, 99, 101),
                candle(EIGHT_H_MS, 101, 101.5, 99.2, 100.5),
            ],
            config,
        )
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].reason, "take_profit")
        self.assertAlmostEqual(trades[0].exit_price, 101 * 0.99)
        self.assertAlmostEqual(trades[0].net_pnl_usd, trade_pnl(101, 101 * 0.99, 20, 6, 6)["net_pnl_usd"])

    def test_gap_through_the_target_fills_at_the_open(self) -> None:
        config = Config(take_profit_pct=1, collateral_usdc=10, leverage=2)
        trades = replay(
            [
                candle(0, 100, 102, 99, 101),
                candle(EIGHT_H_MS, 99, 100, 98, 99.5),
            ],
            config,
        )
        self.assertEqual(trades[0].exit_price, 99)
        self.assertEqual(trades[0].reason, "take_profit")

    def test_missing_target_exits_at_the_next_close(self) -> None:
        config = Config(take_profit_pct=1, collateral_usdc=10, leverage=2)
        trades = replay(
            [
                candle(0, 100, 102, 99, 101),
                candle(EIGHT_H_MS, 101, 103, 100.5, 102),
            ],
            config,
        )
        self.assertEqual(trades[0].reason, "time_stop")
        self.assertEqual(trades[0].exit_price, 102)

    def test_a_green_exit_candle_can_open_the_next_short(self) -> None:
        config = Config(take_profit_pct=1, collateral_usdc=10, leverage=2)
        trades = replay(
            [
                candle(0, 100, 101, 99, 100.5),
                candle(EIGHT_H_MS, 100.5, 102, 100.2, 101.5),
                candle(EIGHT_H_MS * 2, 101.5, 102, 100, 101),
            ],
            config,
        )
        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[1].entry_price, 101.5)


if __name__ == "__main__":
    unittest.main()
