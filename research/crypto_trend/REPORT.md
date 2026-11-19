# Trend following on SOL, BTC and ETH

Protocol: `PROTOCOL.md`. Verdict by its rules: **discard**.

On discovery data (2021-02-28 to 2025-01-01) the locked rule returned +2691% on SOL after costs, with a Sharpe ratio of 1.47 and a worst drawdown of -72%. On the holdout it returned -46.2% on SOL, -21.5% on BTC and +27.2% on ETH. It lost less than buy and hold on all three and made money on 1 of them.

## The rule

At each daily close (00:00 UTC, 5:00 PM in Phoenix): if the close is the highest close of the last 20 days, be long. If it is the lowest close of the last 20 days, be in cash. Otherwise do nothing. No target, no stop, 1x notional.

It was picked from 32 configurations on data through 2025-01-01 because it had the highest worst-asset Sharpe ratio after costs (SOL 1.47, BTC 1.03, ETH 0.99). 29 of the 32 were positive on all three assets in discovery.

## Holdout: 2025-01-01 to 2026-11-18, after costs

| Asset | Rule return | Buy and hold | Sharpe | 95% interval | Rule max drawdown | Buy and hold max drawdown | Closed trades | Win rate | Average win | Average loss | Time in market | Shift test p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SOL | -46.2% | -60.3% | -0.50 | -1.88 to 0.85 | -55.2% | -76.3% | 13 | 15% | +19.4% | -8.3% | 47% | 0.66 |
| BTC | -21.5% | -30.7% | -0.40 | -1.97 to 1.11 | -35.0% | -53.0% | 12 | 33% | +9.9% | -7.4% | 45% | 0.39 |
| ETH | +27.2% | -45.4% | 0.50 | -1.28 to 1.98 | -44.6% | -67.6% | 10 | 30% | +43.2% | -11.0% | 50% | 0.07 |

Shift test p: share of randomly time-shifted copies of the same positions that did at least as well. Small means the timing mattered.

## Holdout sensitivities, total return after costs

| Variant | SOL | BTC | ETH |
|---|---:|---:|---:|
| locked rule | -46.2% | -21.5% | +27.2% |
| locked rule, fill 8h late | -41.4% | -14.6% | +41.7% |
| locked rule, doubled costs | -53.0% | -30.5% | +13.2% |
| locked rule, fill 8h late and doubled costs | -48.8% | -24.4% | +26.2% |
| locked rule, spot (no borrow) | -39.5% | -12.6% | +41.0% |
| vote of 16 signals, long/flat | -9.5% | +6.8% | +36.9% |
| vote of 16 signals, long/short | +6.0% | +27.9% | +78.9% |
| buy and hold (spot) | -60.3% | -30.7% | -45.4% |

All 32 configurations on the holdout (for context, not selection): positive on SOL 7, on BTC 8, on ETH 20. Median return: SOL -21.8%, BTC -15.2%, ETH +22.8%. Long/flat only: SOL -26.4%; long/short only: SOL -10.0%.

## Calendar years, locked rule against buy and hold

| Year | SOL rule | SOL buy and hold | BTC rule | BTC buy and hold | ETH rule | ETH buy and hold |
|---|---:|---:|---:|---:|---:|---:|
| 2018 |  |  | -37.9% | -65.5% | +5.7% | -83.9% |
| 2019 |  |  | +103.2% | +94.5% | -9.7% | -1.7% |
| 2020 |  |  | +377.8% | +302.3% | +650.7% | +471.9% |
| 2021 | +644.0% | +1188.6% | +32.6% | +59.8% | +295.2% | +399.5% |
| 2022 | -51.1% | -94.1% | -44.4% | -64.2% | -47.5% | -67.5% |
| 2023 | +409.7% | +921.0% | +81.1% | +155.7% | +35.9% | +90.8% |
| 2024 | +50.4% | +86.1% | +59.5% | +121.3% | -15.3% | +46.3% |
| 2025 (holdout) | -42.7% | -34.2% | -21.0% | -6.3% | +3.0% | -11.0% |
| 2026 (holdout) | -6.1% | -39.7% | -0.6% | -25.9% | +23.6% | -38.6% |

The first year of each asset starts 200 days after its first candle. 2026 ends on the last close in the data.

## Leverage

Trades of the locked rule that would have been liquidated before their exit, using daily lows and Jupiter's formula.

| Leverage | SOL | BTC | ETH |
|---|---:|---:|---:|
| 2x | 0 of 35 | 0 of 50 | 0 of 47 |
| 3x | 1 of 35 | 0 of 50 | 0 of 47 |
| 5x | 7 of 35 | 3 of 50 | 6 of 47 |
| 10x | 22 of 35 | 20 of 50 | 20 of 47 |
| 15x | 25 of 35 | 30 of 50 | 28 of 47 |

## SOL trades in the holdout

Times are America/Phoenix (UTC-7).

| Entry | Entry price | Exit | Exit price | Days | Return after costs | Worst move against |
|---|---:|---:|---:|---:|---:|---:|
| 2025-01-06 17:00 | 218.22 | 2025-01-13 17:00 | 182.87 | 7 | -16.6% | -22.6% |
| 2025-01-17 17:00 | 219.51 | 2025-02-05 17:00 | 196.12 | 19 | -11.5% | -19.9% |
| 2025-03-25 17:00 | 143.64 | 2025-04-02 17:00 | 117.42 | 8 | -18.7% | -18.5% |
| 2025-04-17 17:00 | 134.83 | 2025-05-30 17:00 | 156.20 | 43 | +14.2% | -1.8% |
| 2025-07-09 17:00 | 157.05 | 2025-08-02 17:00 | 158.48 | 24 | -0.1% | -0.9% |
| 2025-08-12 17:00 | 191.78 | 2025-09-25 17:00 | 192.74 | 44 | -1.2% | -8.4% |
| 2025-12-03 17:00 | 144.67 | 2025-12-17 17:00 | 123.27 | 14 | -15.4% | -16.1% |
| 2026-01-02 17:00 | 132.29 | 2026-01-20 17:00 | 125.80 | 18 | -5.7% | -5.8% |
| 2026-02-25 17:00 | 88.06 | 2026-03-28 17:00 | 82.09 | 31 | -8.0% | -12.4% |
| 2026-04-16 17:00 | 89.05 | 2026-05-26 17:00 | 83.72 | 40 | -7.5% | -8.6% |
| 2026-06-29 17:00 | 75.16 | 2026-07-24 17:00 | 73.96 | 25 | -2.6% | -4.3% |
| 2026-08-18 17:00 | 77.05 | 2026-09-15 17:00 | 96.88 | 28 | +24.6% | -0.5% |
| 2026-09-18 17:00 | 112.72 | 2026-10-08 17:00 | 109.62 | 20 | -3.6% | -6.2% |

As of the close on 2026-11-17 17:00 Phoenix time SOL closed at 75.19 and the rule is in cash. The 20-day closing high is 96.38 and the 20-day closing low is 70.28.

Regenerate: `python3 fetch_data.py && python3 01_discovery.py && python3 02_holdout.py`.
