# SOL/USDT 8h green-candle short with a one-dollar take-profit

Follow-up to `REPORT.md`. Same signal, same next-candle management, same costs and baselines. The only change: the cover price is **entry - 1.00 USDT** instead of a percentage below entry.

## Result

| Sample, after 12 bps | Signals | TP hit | Green short mean (bps) | 95% interval (bps) | Sum of returns | Red short mean (bps) | Green minus red (bps) | 95% interval |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Discovery (before 2026-08-20 16:00 UTC) | 3286 | 49.8% | -16.3 | -26.0 to -6.6 | -535.4% | -14.2 | -2.0 | -15.5 to +11.4 |
| Last 90 days | 139 | 55.4% | -1.9 | -23.7 to +20.0 | -2.57% | -22.6 | +20.7 | -12.0 to +53.4 |

- One dollar is not one distance. It was 44% of the entry price in 2020, 2.7% in 2021, 4.5% in 2023, 0.60% in 2025 and 0.96% over the last 90 days (range 0.84% to 1.12% for the middle 80% of signals). Fees are a percentage of notional, so the percentage is what decides whether a fill pays.
- On the last 90 days one dollar was close to the 1% target of the percentage study (median 0.96% of entry), and the result is close to that one: -1.9 bps against -0.6 bps. At the latest close of 73.49 one dollar is 1.36%, so from here it is a wider target than the one this slice tested. The percentage targets on either side of that, 1% and 1.5%, returned -0.6 and +7.2 bps on the last 90 days and -10.0 and -12.9 bps on discovery data.
- It hit on 55.4% of green signals in the last 90 days and 48.4% in the last 365 days (after red candles: 45.8% and 48.2%). The average winner after 12 bps was +82.2 bps and the average loser -134.2 bps, so a 61.2% win rate does not cover the losers.
- On discovery data it is worse than every percentage target (the best of those was -10.0 bps) and it beat 0 of the 4 baselines. On the last 90 days it beat 4 of 4, with a margin over the red short of +20.7 bps and a 95% interval of -12.0 to +53.4.
- By venue on the last 90 days: Binance -1.9 bps, OKX -3.2 bps, KuCoin -1.3 bps.
- The last 90 days are not a clean test of this exit. They were read for seven percentage targets before the one-dollar exit was specified, and the wider targets were already known to look better on that slice.

## Green short, every cost

### Discovery

| Cost (bps) | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval for mean (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 3286 | 49.8% | 50.2% | -4.3 | +56.4 | 67.3% | +126.9 | -273.8 | 0.95 | 96.2% | 49.8% | -13.9 to +5.4 |
| 6 | 3286 | 49.8% | 50.2% | -10.3 | +50.4 | 66.9% | +121.6 | -276.8 | 0.89 | 99.4% | 49.8% | -19.9 to -0.6 |
| 12 | 3286 | 49.8% | 50.2% | -16.3 | +44.5 | 66.1% | +117.0 | -276.6 | 0.83 | 99.9% | 49.8% | -26.0 to -6.6 |
| 20 | 3286 | 49.8% | 50.2% | -24.3 | +36.5 | 65.4% | +110.4 | -278.5 | 0.75 | 100.0% | 49.8% | -34.0 to -14.6 |
| 40 | 3286 | 49.8% | 50.2% | -44.3 | +16.5 | 62.5% | +95.0 | -276.6 | 0.57 | 100.0% | 49.8% | -54.0 to -34.6 |

### Last 90 days

| Cost (bps) | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval for mean (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 139 | 55.4% | 44.6% | +10.1 | +82.8 | 62.6% | +92.2 | -127.1 | 1.21 | 18.5% | 51.5% | -11.7 to +32.0 |
| 6 | 139 | 55.4% | 44.6% | +4.1 | +76.9 | 62.6% | +86.2 | -133.2 | 1.08 | 19.1% | 51.5% | -17.7 to +26.0 |
| 12 | 139 | 55.4% | 44.6% | -1.9 | +70.9 | 61.2% | +82.2 | -134.2 | 0.96 | 20.1% | 51.5% | -23.7 to +20.0 |
| 20 | 139 | 55.4% | 44.6% | -9.8 | +62.9 | 61.2% | +74.2 | -142.2 | 0.82 | 23.1% | 51.5% | -31.7 to +12.0 |
| 40 | 139 | 55.4% | 44.6% | -29.8 | +43.0 | 59.7% | +55.8 | -156.8 | 0.53 | 36.6% | 51.5% | -51.7 to -8.0 |

### Last 365 days

| Cost (bps) | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval for mean (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 535 | 48.4% | 51.6% | +5.7 | +68.7 | 63.6% | +87.4 | -136.7 | 1.12 | 28.0% | 48.9% | -5.8 to +17.3 |
| 6 | 535 | 48.4% | 51.6% | -0.2 | +62.7 | 62.6% | +82.7 | -139.2 | 1.00 | 32.9% | 48.9% | -11.8 to +11.3 |
| 12 | 535 | 48.4% | 51.6% | -6.2 | +56.8 | 60.2% | +80.0 | -136.6 | 0.89 | 42.9% | 48.9% | -17.8 to +5.4 |
| 20 | 535 | 48.4% | 51.6% | -14.2 | +48.8 | 58.7% | +73.9 | -139.5 | 0.75 | 60.5% | 48.9% | -25.8 to -2.6 |
| 40 | 535 | 48.4% | 51.6% | -34.2 | +28.9 | 54.4% | +59.0 | -145.5 | 0.48 | 85.3% | 48.9% | -45.9 to -22.6 |

### Full history

| Cost (bps) | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval for mean (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 3425 | 50.0% | 50.0% | -3.7 | +56.8 | 67.1% | +125.6 | -267.0 | 0.96 | 96.2% | 49.8% | -13.0 to +5.6 |
| 6 | 3425 | 50.0% | 50.0% | -9.7 | +50.8 | 66.7% | +120.3 | -270.3 | 0.89 | 99.4% | 49.8% | -19.0 to -0.4 |
| 12 | 3425 | 50.0% | 50.0% | -15.7 | +44.8 | 65.9% | +115.7 | -270.0 | 0.83 | 99.9% | 49.8% | -25.0 to -6.4 |
| 20 | 3425 | 50.0% | 50.0% | -23.7 | +36.8 | 65.2% | +109.0 | -272.4 | 0.75 | 100.0% | 49.8% | -33.0 to -14.4 |
| 40 | 3425 | 50.0% | 50.0% | -43.7 | +16.9 | 62.4% | +93.5 | -271.4 | 0.57 | 100.0% | 49.8% | -53.0 to -34.4 |

## Against the baselines

### Discovery, after 12 bps

| Strategy | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval for mean (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Green short (the idea) | 3286 | 49.8% | 50.2% | -16.3 | +44.5 | 66.1% | +117.0 | -276.6 | 0.83 | 99.9% | 49.8% | -26.0 to -6.6 |
| Red short | 3289 | 48.8% | 51.2% | -14.2 | +43.1 | 63.5% | +121.0 | -249.4 | 0.84 | 99.8% | 49.8% | -23.6 to -4.9 |
| Every-candle short | 6601 | 49.2% | 50.8% | -15.5 | +43.7 | 64.7% | +119.3 | -262.5 | 0.83 | 100.0% | 100.0% | -22.2 to -8.7 |
| Random-half short | 3300 | 49.2% | 50.8% | -15.2 | +43.7 | 64.7% | +119.4 | -262.3 | 0.84 | 99.8% | 50.0% | -21.9 to -8.5 |
| Green long (flipped) | 3286 | 49.1% | 50.9% | -3.9 | +41.3 | 63.0% | +130.0 | -231.4 | 0.95 | 98.1% | 49.8% | -13.1 to +5.3 |

Green minus red: -2.0 bps (95% interval -15.5 to +11.4). Share of random candle sets of the same size that shorted at least as well as the green set: 0.59.

| Cost (bps) | Green short (the idea) | Red short | Every-candle short | Random-half short | Green long (flipped) |
|---|---:|---:|---:|---:|---:|
| 0 | -4.3 | -2.2 | -3.5 | -3.2 | +8.1 |
| 6 | -10.3 | -8.2 | -9.5 | -9.2 | +2.1 |
| 12 | -16.3 | -14.2 | -15.5 | -15.2 | -3.9 |
| 20 | -24.3 | -22.2 | -23.5 | -23.2 | -11.9 |
| 40 | -44.3 | -42.2 | -43.5 | -43.2 | -31.9 |

Mean return per trade in bps at each cost. The flipped long sells one dollar above entry.

### Last 90 days, after 12 bps

| Strategy | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval for mean (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Green short (the idea) | 139 | 55.4% | 44.6% | -1.9 | +70.9 | 61.2% | +82.2 | -134.2 | 0.96 | 20.1% | 51.5% | -23.7 to +20.0 |
| Red short | 131 | 45.8% | 54.2% | -22.6 | +14.5 | 51.9% | +81.2 | -134.6 | 0.65 | 28.1% | 48.5% | -46.9 to +1.8 |
| Every-candle short | 270 | 50.7% | 49.3% | -11.9 | +70.1 | 56.7% | +81.8 | -134.4 | 0.80 | 37.6% | 100.0% | -28.2 to +4.4 |
| Random-half short | 135 | 50.6% | 49.4% | -11.9 | +58.4 | 56.6% | +81.8 | -133.9 | 0.81 | 23.2% | 50.0% | -27.2 to +3.6 |
| Green long (flipped) | 139 | 43.9% | 56.1% | -27.3 | +21.2 | 53.2% | +75.5 | -144.2 | 0.60 | 35.2% | 51.5% | -50.1 to -4.4 |

Green minus red: +20.7 bps (95% interval -12.0 to +53.4). Share of random candle sets of the same size that shorted at least as well as the green set: 0.11.

| Cost (bps) | Green short (the idea) | Red short | Every-candle short | Random-half short | Green long (flipped) |
|---|---:|---:|---:|---:|---:|
| 0 | +10.1 | -10.6 | +0.1 | +0.1 | -15.3 |
| 6 | +4.1 | -16.6 | -5.9 | -5.9 | -21.3 |
| 12 | -1.9 | -22.6 | -11.9 | -11.9 | -27.3 |
| 20 | -9.8 | -30.6 | -19.9 | -19.9 | -35.2 |
| 40 | -29.8 | -50.6 | -39.9 | -39.9 | -55.2 |

Mean return per trade in bps at each cost. The flipped long sells one dollar above entry.

### Last 365 days, after 12 bps

| Strategy | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval for mean (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Green short (the idea) | 535 | 48.4% | 51.6% | -6.2 | +56.8 | 60.2% | +80.0 | -136.6 | 0.89 | 42.9% | 48.9% | -17.8 to +5.4 |
| Red short | 558 | 48.2% | 51.8% | -13.0 | +55.8 | 55.4% | +86.0 | -135.9 | 0.79 | 60.4% | 51.0% | -25.0 to -1.1 |
| Every-candle short | 1095 | 48.3% | 51.7% | -9.7 | +56.1 | 57.7% | +83.0 | -136.1 | 0.83 | 72.8% | 100.0% | -18.0 to -1.3 |
| Random-half short | 547 | 48.3% | 51.7% | -9.8 | +51.4 | 57.7% | +83.0 | -136.4 | 0.83 | 51.1% | 50.0% | -17.9 to -1.4 |
| Green long (flipped) | 535 | 44.7% | 55.3% | -20.6 | +22.9 | 54.4% | +79.7 | -140.3 | 0.68 | 69.1% | 48.9% | -32.3 to -8.9 |

Green minus red: +6.8 bps (95% interval -9.9 to +23.4). Share of random candle sets of the same size that shorted at least as well as the green set: 0.22.

| Cost (bps) | Green short (the idea) | Red short | Every-candle short | Random-half short | Green long (flipped) |
|---|---:|---:|---:|---:|---:|
| 0 | +5.7 | -1.0 | +2.3 | +2.2 | -8.6 |
| 6 | -0.2 | -7.0 | -3.7 | -3.8 | -14.6 |
| 12 | -6.2 | -13.0 | -9.7 | -9.8 | -20.6 |
| 20 | -14.2 | -21.0 | -17.7 | -17.8 | -28.6 |
| 40 | -34.2 | -41.0 | -37.7 | -37.8 | -48.6 |

Mean return per trade in bps at each cost. The flipped long sells one dollar above entry.

## By period, after 12 bps

| Period | Median entry price | One dollar as % of entry (median) | Green signals | Green TP hit | Green mean (bps) | 95% interval (bps) | Green profit factor | Green max DD | Red mean (bps) | Red TP hit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full history | 87.36 | 1.14% | 3425 | 50.0% | -15.7 | -25.0 to -6.4 | 0.83 | 99.9% | -14.6 | 48.7% |
| 2020 | 2.26 | 44.25% | 198 | 0.0% | -21.0 | -91.6 to +49.7 | 0.89 | 52.9% | +5.4 | 0.4% |
| 2021 | 37.58 | 2.66% | 546 | 52.4% | -39.0 | -75.0 to -3.0 | 0.76 | 93.3% | -30.8 | 54.0% |
| 2022 | 40.33 | 2.48% | 528 | 48.1% | +16.9 | -2.8 to +36.6 | 1.22 | 46.5% | -8.4 | 44.4% |
| 2023 | 22.33 | 4.48% | 559 | 18.2% | -34.3 | -59.6 to -9.1 | 0.70 | 89.6% | -25.4 | 14.3% |
| 2024 | 151.25 | 0.66% | 571 | 76.5% | -9.6 | -21.6 to +2.3 | 0.81 | 52.6% | -3.8 | 77.0% |
| 2025 | 166.75 | 0.60% | 550 | 75.3% | -18.1 | -30.3 to -5.8 | 0.67 | 67.8% | -13.7 | 75.8% |
| 2026 | 86.84 | 1.15% | 473 | 46.7% | -5.5 | -17.9 to +6.9 | 0.90 | 38.2% | -13.8 | 46.3% |
| last 365d | 89.37 | 1.12% | 535 | 48.4% | -6.2 | -17.8 to +5.4 | 0.89 | 42.9% | -13.0 | 48.2% |
| confirmation (last 90d) | 104.11 | 0.96% | 139 | 55.4% | -1.9 | -23.7 to +20.0 | 0.96 | 20.1% | -22.6 | 45.8% |

In 2020 SOL traded near 2 dollars and the target was reached on 0.0% of signals; in 2023 it was reached on 18.2%. In those years the trade was close to a plain one-candle short. In 2024 and 2025, with SOL above 150, one dollar was about 0.6% and was reached on three signals in four.

## Entry at N's open, venues, borrow

| Sample, 12 bps | Binance, C close | Binance, N open | OKX, C close | KuCoin, C close | Binance + 0.56 bps borrow | Binance + 8 bps borrow | Red short, OKX | Red short, KuCoin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Discovery | -16.3 | -16.1 | -14.8 | -14.0 | -16.9 | -24.3 | -15.1 | -12.3 |
| Last 90 days | -1.9 | -1.9 | -3.2 | -1.3 | -2.4 | -9.9 | -22.4 | -22.5 |
| Last 365 days | -6.2 | -6.2 | -6.1 | -5.9 | -6.8 | -14.2 | -12.4 | -13.5 |

Green short mean per trade in bps unless the column says red. OKX history starts 2020-09-30 and KuCoin 2021-08-04.

## Green signals by body size, after 12 bps

| Sample | Body <1% | Body 1-3% | Body 3-6% | Body >=6% |
|---|---:|---:|---:|---:|
| Discovery | -14.2 (n=1164, -27.0 to -1.3) | -18.2 (n=1257, -32.8 to -3.5) | -24.8 (n=589, -51.6 to +1.9) | +1.6 (n=276, -49.4 to +52.7) |
| Last 90 days | -9.6 (n=77, -40.0 to +20.8) | +23.8 (n=51, -4.2 to +51.7) | -81.6 (n=10, -203.2 to +40.1) | +86.0 (n=1) |

## How far price rose against the short before exit

| Sample | Subset | Trades | Median adverse move | 90th percentile | 99th percentile | Worst | Median minutes held |
|---|---:|---:|---:|---:|---:|---:|---:|
| Discovery | All | 3286 | 1.03% | 5.04% | 12.95% | 57.7% | 480 |
| Discovery | Take-profit hit | 1637 | 0.46% | 1.79% | 4.59% | 7.5% | 67 |
| Discovery | Expired | 1649 | 2.28% | 7.15% | 16.42% | 57.7% | 480 |
| Confirmation | All | 139 | 0.75% | 2.81% | 5.98% | 9.6% | 412 |
| Confirmation | Take-profit hit | 77 | 0.43% | 1.22% | 5.06% | 9.6% | 159 |
| Confirmation | Expired | 62 | 1.24% | 4.13% | 5.80% | 6.3% | 480 |
| Full history | All | 3425 | 1.00% | 4.98% | 12.83% | 57.7% | 475 |
| Full history | Take-profit hit | 1714 | 0.46% | 1.75% | 4.65% | 9.6% | 70 |
| Full history | Expired | 1711 | 2.21% | 7.06% | 16.06% | 57.7% | 480 |

From Binance 1m candles, entry at C's close. Highest price before exit relative to entry.

## The last 30 green-candle shorts

Times are America/Phoenix (UTC-7). Binance spot. Newest first.

| Signal candle open | Entry time (C close) | Entry | Take-profit (entry - 1.00) | Distance as % of entry | Result | Exit price | Return after 12 bps |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-17 17:00 | 2026-11-18 01:00 | 75.19 | 74.19 | 1.33% | take-profit hit | 74.19 | +1.21% |
| 2026-11-17 09:00 | 2026-11-17 17:00 | 75.19 | 74.19 | 1.33% | take-profit hit | 74.19 | +1.21% |
| 2026-11-16 17:00 | 2026-11-17 01:00 | 72.96 | 71.96 | 1.37% | take-profit hit | 71.96 | +1.25% |
| 2026-11-16 09:00 | 2026-11-16 17:00 | 71.58 | 70.58 | 1.40% | expired | 72.96 | -2.05% |
| 2026-11-15 09:00 | 2026-11-15 17:00 | 72.77 | 71.77 | 1.37% | take-profit hit | 71.77 | +1.26% |
| 2026-11-15 01:00 | 2026-11-15 09:00 | 71.24 | 70.24 | 1.40% | expired | 72.77 | -2.27% |
| 2026-11-13 01:00 | 2026-11-13 09:00 | 80.03 | 79.03 | 1.25% | take-profit hit | 79.03 | +1.13% |
| 2026-11-12 09:00 | 2026-11-12 17:00 | 81.72 | 80.72 | 1.22% | take-profit hit | 80.72 | +1.10% |
| 2026-11-11 01:00 | 2026-11-11 09:00 | 84.85 | 83.85 | 1.18% | take-profit hit | 83.85 | +1.06% |
| 2026-11-10 17:00 | 2026-11-11 01:00 | 83.37 | 82.37 | 1.20% | expired | 84.85 | -1.90% |
| 2026-11-10 09:00 | 2026-11-10 17:00 | 83.35 | 82.35 | 1.20% | take-profit hit | 82.35 | +1.08% |
| 2026-11-09 01:00 | 2026-11-09 09:00 | 87.94 | 86.94 | 1.14% | take-profit hit | 86.94 | +1.02% |
| 2026-11-08 01:00 | 2026-11-08 09:00 | 89.71 | 88.71 | 1.11% | take-profit hit | 88.71 | +1.00% |
| 2026-11-07 09:00 | 2026-11-07 17:00 | 89.81 | 88.81 | 1.11% | expired | 89.35 | +0.39% |
| 2026-11-06 17:00 | 2026-11-07 01:00 | 90.23 | 89.23 | 1.11% | take-profit hit | 89.23 | +0.99% |
| 2026-11-06 01:00 | 2026-11-06 09:00 | 90.75 | 89.75 | 1.10% | take-profit hit | 89.75 | +0.98% |
| 2026-11-05 17:00 | 2026-11-06 01:00 | 89.68 | 88.68 | 1.12% | expired | 90.75 | -1.31% |
| 2026-11-04 17:00 | 2026-11-05 01:00 | 95.90 | 94.90 | 1.04% | take-profit hit | 94.90 | +0.92% |
| 2026-11-04 01:00 | 2026-11-04 09:00 | 96.70 | 95.70 | 1.03% | take-profit hit | 95.70 | +0.91% |
| 2026-11-03 17:00 | 2026-11-04 01:00 | 93.05 | 92.05 | 1.07% | expired | 96.70 | -4.04% |
| 2026-11-03 01:00 | 2026-11-03 09:00 | 93.75 | 92.75 | 1.07% | expired | 92.83 | +0.86% |
| 2026-11-02 17:00 | 2026-11-03 01:00 | 92.11 | 91.11 | 1.09% | expired | 93.75 | -1.90% |
| 2026-10-31 17:00 | 2026-11-01 01:00 | 95.60 | 94.60 | 1.05% | take-profit hit | 94.60 | +0.93% |
| 2026-10-31 01:00 | 2026-10-31 09:00 | 95.98 | 94.98 | 1.04% | expired | 95.54 | +0.34% |
| 2026-10-30 09:00 | 2026-10-30 17:00 | 96.38 | 95.38 | 1.04% | expired | 95.64 | +0.65% |
| 2026-10-29 17:00 | 2026-10-30 01:00 | 97.35 | 96.35 | 1.03% | take-profit hit | 96.35 | +0.91% |
| 2026-10-29 01:00 | 2026-10-29 09:00 | 102.70 | 101.70 | 0.97% | take-profit hit | 101.70 | +0.85% |
| 2026-10-28 09:00 | 2026-10-28 17:00 | 102.44 | 101.44 | 0.98% | take-profit hit | 101.44 | +0.86% |
| 2026-10-27 17:00 | 2026-10-28 01:00 | 102.33 | 101.33 | 0.98% | take-profit hit | 101.33 | +0.86% |
| 2026-10-27 09:00 | 2026-10-27 17:00 | 101.35 | 100.35 | 0.99% | expired | 102.33 | -1.09% |

Sum of the 30 returns after 12 bps: +7.21%. 19 hit the take-profit and 11 expired.

Full grid: `results/dollar_tp_grid.csv`. Run `python3 03_dollar_tp.py` to regenerate.
