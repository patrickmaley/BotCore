# Trend following on SOL, BTC and ETH: protocol

Written before any result was computed. The scripts enforce it; this file says what they are allowed to do.

## The idea

Crypto prices have trended: moves up and down have tended to continue for weeks. A trend rule goes long while price is rising and short while it is falling, with no price target. It expects to lose often and by a little, and to win rarely and by a lot. This is the opposite shape to the green-candle short, which won often by a little and lost rarely by a lot.

The family is taken from published trend-following research, not from anything measured in this repository.

## Data

- Binance spot SOLUSDT, BTCUSDT, ETHUSDT 8h candles, frozen at the candle that closed 2026-11-18 16:00 UTC (the same freeze as the green-candle study).
- Daily bars are built from them. A day closes at 00:00 UTC (5:00 PM in Phoenix).
- **Discovery:** every day that closes on or before 2025-01-01 00:00 UTC.
- **Holdout:** every day after that, through the day that closes 2026-11-18 00:00 UTC.

## Rules tested (16 signals, 2 modes, 32 configurations)

Computed at each daily close from closes up to and including that one. The position is taken at that close and held until the signal changes.

- `sma_N`: long if the close is above its N-day average, short if below. N = 10, 20, 30, 50, 100, 200.
- `don_N`: long from a new N-day closing high, short from a new N-day closing low, unchanged in between. N = 10, 20, 30, 50, 100.
- `mom_N`: long if the close is above the close N days ago, short if below. N = 7, 14, 28, 56, 112.

Modes: long/short (always in the market) and long/flat (in cash when the signal is short).

Every configuration is evaluated from the same first day: 200 days after an asset's first candle.

## Position and costs

- One position of notional equal to current equity (1x). No stop, no target.
- 6 bps of notional per side. A flip from long to short pays both.
- Borrow at the rates Jupiter's perps API reported when the data was frozen: 0.0015% per hour long, 0.0007% per hour short, on entry notional, for the time held. The same rates are applied to BTC and ETH.
- Fill at the daily close.

## Selection, on discovery data only

1. Sharpe ratio after costs for each of the 32 configurations on each of the three assets.
2. Score a configuration by its **lowest** Sharpe across the three assets. Pick the highest score. Ties go to the larger N.
3. Stop without reading the holdout unless the pick is positive after costs on all three assets in discovery.

## Holdout, read once

Primary test: the picked configuration on SOL, at the costs above.

Verdict, fixed in advance:

- **Discard**: SOL holdout return after costs is zero or negative.
- **Watch**: positive on SOL, but negative on two of the three assets, or negative on SOL when the fill is delayed by 8 hours or when costs are doubled.
- **Paper trade**: positive on SOL, positive on at least two of the three assets, and still positive on SOL with an 8-hour delayed fill and with doubled costs.

No verdict here is "proven". The holdout is under two years and holds a few dozen trades at most.

Also reported, not used for the verdict: buy and hold, the vote of all 16 signals, a test against randomly shifted signals, and the leverage at which each trade would have been liquidated.

## What is already known about the holdout

The green-candle study read SOL prices through 2026-11-18. From it I know that SOL's median price was about 167 in 2025 and 87 in 2026, and that it fell from about 124 to 73 in the last 90 days. A rule that can go short was therefore likely to look good on the end of the holdout before any test was run. BTC and ETH have not been looked at.
