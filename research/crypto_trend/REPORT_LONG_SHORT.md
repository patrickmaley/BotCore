# Trend following with shorts allowed

Follow-up to `REPORT.md`. Same data, costs and holdout. Two long/short rules, neither chosen from holdout results:

- **Picked**: `don_20` long/short, the configuration the protocol's selection rule picks among the 16 long/short ones on discovery data. Long from a new 20-day closing high, short from a new 20-day closing low.
- **Vote**: long when most of the 16 signals are long, short when most are short, flat on a tie. Written into `PROTOCOL.md` before any result.

**This is not a clean test.** The holdout had already been read, and that run showed the vote's long/short return.

## Holdout, 2025-01-01 to 2026-11-18, after costs

| Rule | Asset | Return | Buy and hold | Sharpe | 95% interval | Max drawdown | Closed trades | Win rate | Average win | Average loss | From long trades | From short trades | Shift test p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| don_20, long/short (picked on discovery) | SOL | -54.0% | -60.3% | -0.26 | -1.63 to 1.10 | -70.5% | 26 | 23% | +21.2% | -10.1% | -46.2% | -14.6% | 0.623 |
| don_20, long/short (picked on discovery) | BTC | -23.7% | -30.7% | -0.18 | -1.90 to 1.39 | -50.6% | 24 | 33% | +11.8% | -8.0% | -21.5% | -2.9% | 0.367 |
| don_20, long/short (picked on discovery) | ETH | +108.6% | -45.4% | 0.94 | -0.73 to 2.43 | -44.9% | 20 | 40% | +28.5% | -11.5% | +27.2% | +63.9% | 0.056 |
| vote of 16 signals, long/short | SOL | +6.0% | -60.3% | 0.37 | -1.02 to 1.64 | -50.8% | 53 | 30% | +10.7% | -4.4% | -9.5% | +17.1% | 0.232 |
| vote of 16 signals, long/short | BTC | +27.9% | -30.7% | 0.54 | -0.80 to 1.73 | -28.0% | 58 | 22% | +9.0% | -2.1% | +6.8% | +19.8% | 0.106 |
| vote of 16 signals, long/short | ETH | +78.9% | -45.4% | 0.82 | -0.65 to 2.12 | -40.9% | 55 | 20% | +21.0% | -3.5% | +36.9% | +30.7% | 0.076 |

## Discovery, through 2025-01-01, after costs

| Rule | Asset | Return | Buy and hold | Sharpe | 95% interval | Max drawdown | Closed trades | Win rate | Average win | Average loss | From long trades | From short trades | Shift test p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| don_20, long/short (picked on discovery) | SOL | +1362.9% | +1335.0% | 1.18 | 0.09 to 2.31 | -73.5% | 43 | 42% | +60.0% | -14.4% | +2691.5% | -47.6% | 0.002 |
| don_20, long/short (picked on discovery) | BTC | +1121.1% | +773.1% | 0.91 | 0.20 to 1.61 | -62.5% | 75 | 41% | +26.9% | -8.8% | +1183.1% | -4.8% | 0.002 |
| don_20, long/short (picked on discovery) | ETH | +1439.8% | +310.4% | 0.90 | 0.20 to 1.61 | -88.5% | 74 | 42% | +34.9% | -11.3% | +1609.1% | -9.9% | 0.006 |
| vote of 16 signals, long/short | SOL | +1678.0% | +1335.0% | 1.25 | 0.11 to 2.44 | -78.4% | 102 | 29% | +45.8% | -6.3% | +2567.3% | -33.3% | 0.010 |
| vote of 16 signals, long/short | BTC | +997.0% | +773.1% | 0.89 | 0.11 to 1.66 | -55.6% | 171 | 26% | +23.9% | -3.7% | +1716.7% | -39.6% | 0.016 |
| vote of 16 signals, long/short | ETH | +325.8% | +310.4% | 0.66 | -0.14 to 1.47 | -82.2% | 159 | 26% | +25.8% | -5.4% | +609.3% | -40.0% | 0.024 |

## Holdout sensitivities and the protocol's criteria

| Rule | Asset | Base | Fill 8h late | Doubled costs |
|---|---:|---:|---:|---:|
| don_20, long/short (picked on discovery) | SOL | -54.0% | -48.6% | -62.7% |
| don_20, long/short (picked on discovery) | BTC | -23.7% | -7.7% | -37.4% |
| don_20, long/short (picked on discovery) | ETH | +108.6% | +165.6% | +74.3% |
| vote of 16 signals, long/short | SOL | +6.0% | +19.6% | -14.2% |
| vote of 16 signals, long/short | BTC | +27.9% | +48.9% | +1.6% |
| vote of 16 signals, long/short | ETH | +78.9% | +129.0% | +45.2% |

- don_20, long/short (picked on discovery): the protocol's criteria give **discard**.
- vote of 16 signals, long/short: the protocol's criteria give **watch**.

All 16 long/short configurations on the holdout: positive on SOL 7, BTC 5, ETH 11. Median return: SOL -10.0%, BTC -6.3%, ETH +69.0%.

## Leverage

Trades that would have been liquidated before their exit, discovery and holdout together, from daily highs and lows.

| Rule | Leverage | SOL | BTC | ETH |
|---|---:|---:|---:|---:|
| don_20, long/short (picked on discovery) | 1x | 0 of 71 | 0 of 101 | 0 of 96 |
| don_20, long/short (picked on discovery) | 2x | 1 of 71 | 0 of 101 | 0 of 96 |
| don_20, long/short (picked on discovery) | 3x | 3 of 71 | 0 of 101 | 0 of 96 |
| don_20, long/short (picked on discovery) | 5x | 17 of 71 | 5 of 101 | 14 of 96 |
| don_20, long/short (picked on discovery) | 15x | 49 of 71 | 59 of 101 | 59 of 96 |
| vote of 16 signals, long/short | 1x | 0 of 156 | 0 of 231 | 0 of 216 |
| vote of 16 signals, long/short | 2x | 0 of 156 | 0 of 231 | 0 of 216 |
| vote of 16 signals, long/short | 3x | 0 of 156 | 0 of 231 | 1 of 216 |
| vote of 16 signals, long/short | 5x | 4 of 156 | 1 of 231 | 5 of 216 |
| vote of 16 signals, long/short | 15x | 58 of 156 | 32 of 231 | 65 of 216 |

## Where the rules stand on SOL

- don_20, long/short (picked on discovery): **short** since 2026-10-08 17:00 Phoenix time (SOL 109.62); last close 75.19.
- vote of 16 signals, long/short: **short** since 2026-10-22 17:00 Phoenix time (SOL 103.65); last close 75.19. Of the 16 signals, 1 long and 15 short.

Trades: `results/long_short_holdout_trades.csv`. Regenerate: `python3 03_long_short.py`.
