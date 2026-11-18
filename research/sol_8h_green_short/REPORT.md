# SOL/USDT 8h: short the close of a green candle, cover X% lower

## Verdict: discard

**After 12 bps the short lost 10.0 bps per trade over 3,286 discovery trades (95% interval -17.1 to -2.9 bps), at the best X on the menu.** No X from 0.3% to 3% was positive after 12 bps on discovery data. The best was X = 1%, so that is the X that was locked.

Locked X = 1% on the last 90 days, after 12 bps, Binance spot, entry at C's close:

|  | Signals | TP hit | Mean per trade (bps) | 95% interval (bps) | Sum of trade returns | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| Green short (the idea) | 139 | 56.1% | -0.6 | -22.5 to +21.3 | -0.83% | 0.99 |
| Red short (baseline) | 131 | 47.3% | -18.3 | -42.0 to +5.4 | -24.02% | 0.70 |

- The confirmation result is not profitable after 12 bps: -0.6 bps per trade. Entry at N's open gives -0.6 bps (red short: -18.4 bps).
- It did beat all four baselines on the last 90 days, but the margin over the red short, +17.7 bps, has a 95% interval of -14.5 to +50.0 bps, and the sign is the opposite of discovery, where the green short was 3.0 bps worse than the red short and worse than it at 7 of 7 X values.
- The dip is not specific to green candles. On discovery data the next candle traded 1% below the close after 68.2% of green candles and 68.2% of red candles.
- Before costs the idea earned +2.0 bps per trade on discovery data (95% interval -5.1 to +9.1). That is not distinguishable from zero and is far below a 12 bps fee.
- SOL fell 15.9% over the confirmation window. Every short had that tailwind and the idea still did not clear costs.
- Break-even round-trip cost at X = 1%: about 2 bps on discovery data and 11 bps on the last 90 days. Jupiter charges 12 before borrow and price impact.

**The one future result that would change this:** on trades entered after 2026-11-18 16:00 UTC, with X still 1% and 12 bps charged, a mean return per green short whose 95% interval sits wholly above zero. At the trade-to-trade spread seen in the last 90 days (132 bps) and a similar count of about 139 signals, that needs roughly +22 bps per trade after costs. Until then nothing here supports a bot, and no new exit is proposed.

## What was tested

- Signal candle C is a completed 8h candle with close > open. Short one unit at C's close. Take-profit at entry x (1 - X/100).
- Managed on the next candle N only. N opens at or below the take-profit: cover at N's open. N's low touches it: cover at the take-profit price. Otherwise cover at N's close. No stop. Every trade is closed by N's close, so trades never overlap.
- Returns are per trade on one unit of notional. A round-trip cost of c bps is charged as c/2 on entry notional and c/2 on exit notional.
- `test_rules.py` checks each fill case and the cost arithmetic on hand-built candles.

### Data

- Primary venue: **Binance spot SOLUSDT**, native 8h klines opening at 00:00, 08:00 and 16:00 UTC. 6,872 completed candles from 2020-08-11 00:00 UTC to the candle that closed 2026-11-18 16:00 UTC. No 8h bar is missing. The candle forming at fetch time was dropped. 3,425 green, 3,421 red, 26 with close = open (neither).
- Second venue: **OKX spot SOL-USDT**, 1h candles aggregated to the same 8h grid (OKX has no 8h bar), from 2020-09-30. Third venue for the lows: **KuCoin spot SOL-USDT**, native 8h, from 2021-08-04.
- Binance 1m candles (3,296,775 bars) are used only for the adverse-move and holding-time numbers. Aggregated to 8h they reproduce the 8h low and close on every bar (0 low mismatches, 0 close mismatches).
- **Discovery**: trades entered before 2026-08-20 16:00 UTC. **Confirmation**: trades entered from 2026-08-20 16:00 to 2026-11-18 08:00 UTC, 270 candles.
- X was chosen by one rule written down and committed before any result existed: the X with the highest mean return per trade after 12 bps on discovery data. The discovery results and the locked X were committed before the confirmation script was run. The other six X values on the last 90 days are printed below because the report asks for them. They were not used to choose anything.
- I do not know which dates the dip was noticed on. If the chart that prompted this idea included any of the last 90 days, the confirmation slice is not clean and its result flatters the idea.

### Execution: C's close versus N's open

Binance, OKX and KuCoin spot candles are not stitched. N's open is the first trade of the new candle, which is often but not always C's close.

| Venue | N open = C close, full history | Same, last 365 days | Median gap (bps) | 99th percentile gap (bps) | Largest gap (bps) |
|---|---:|---:|---:|---:|---:|
| Binance | 43.6% | 50.4% | 0.55 | 23.9 | 138 |
| OKX | 27.4% | 44.7% | 0.82 | 23.1 | 2159 |
| KuCoin | 16.7% | 31.4% | 1.12 | 11.5 | 64 |

Gap = |N open / C close - 1|. On Binance the two prices are the same on 43.6% of candles and within 24 bps on 99% of them. Both entries are reported. At the locked X the difference is small:

| Sample | Cost (bps) | Mean, entry at C close (bps) | Mean, entry at N open (bps) | TP hit, C close | TP hit, N open | Filled at N's open through the TP |
|---|---:|---:|---:|---:|---:|---:|
| Discovery | 0 | +2.0 | +2.5 | 68.2% | 68.2% | 0.00% |
| Discovery | 6 | -4.0 | -3.5 | 68.2% | 68.2% | 0.00% |
| Discovery | 12 | -10.0 | -9.5 | 68.2% | 68.2% | 0.00% |
| Discovery | 20 | -18.0 | -17.5 | 68.2% | 68.2% | 0.00% |
| Discovery | 40 | -38.0 | -37.5 | 68.2% | 68.2% | 0.00% |
| Confirmation | 0 | +11.4 | +11.4 | 56.1% | 56.1% | 0.00% |
| Confirmation | 6 | +5.4 | +5.4 | 56.1% | 56.1% | 0.00% |
| Confirmation | 12 | -0.6 | -0.6 | 56.1% | 56.1% | 0.00% |
| Confirmation | 20 | -8.6 | -8.6 | 56.1% | 56.1% | 0.00% |
| Confirmation | 40 | -28.6 | -28.6 | 56.1% | 56.1% | 0.00% |

Jupiter perps fill against an oracle price, not against Binance prints, and a Jupiter take-profit is a trigger that a keeper executes at the oracle price when it gets there. Neither a fill at exactly C's close nor a fill at exactly the limit is guaranteed. The rule as specified assumes both, which favours the trade.

## Discovery data

Trades entered before 2026-08-20 16:00 UTC. Binance spot, entry at C's close. Returns are in basis points per trade after the stated round-trip cost.

### Green-candle short, every X and every cost

| X | Cost (bps) | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval for mean (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.3% | 0 | 3286 | 90.1% | 9.9% | -2.9 | +30.0 | 90.2% | +30.0 | -306.2 | 0.90 | 79.9% | 49.8% | -7.6 to +1.7 |
| 0.3% | 6 | 3286 | 90.1% | 9.9% | -8.9 | +24.0 | 90.2% | +24.0 | -312.3 | 0.71 | 96.7% | 49.8% | -13.6 to -4.3 |
| 0.3% | 12 | 3286 | 90.1% | 9.9% | -14.9 | +18.0 | 90.1% | +18.0 | -316.4 | 0.52 | 99.5% | 49.8% | -19.6 to -10.3 |
| 0.3% | 20 | 3286 | 90.1% | 9.9% | -22.9 | +10.0 | 90.1% | +10.0 | -324.6 | 0.28 | 100.0% | 49.8% | -27.6 to -18.3 |
| 0.3% | 40 | 3286 | 90.1% | 9.9% | -42.9 | -9.9 | 0.1% | +6.2 | -43.0 | 0.00 | 100.0% | 49.8% | -47.6 to -38.3 |
| 0.5% | 0 | 3286 | 83.9% | 16.1% | -2.3 | +50.0 | 84.4% | +49.8 | -285.3 | 0.95 | 80.6% | 49.8% | -8.1 to +3.4 |
| 0.5% | 6 | 3286 | 83.9% | 16.1% | -8.3 | +44.0 | 84.4% | +43.8 | -290.3 | 0.82 | 96.9% | 49.8% | -14.1 to -2.6 |
| 0.5% | 12 | 3286 | 83.9% | 16.1% | -14.3 | +38.0 | 84.3% | +37.9 | -294.1 | 0.69 | 99.5% | 49.8% | -20.1 to -8.6 |
| 0.5% | 20 | 3286 | 83.9% | 16.1% | -22.3 | +30.0 | 84.1% | +30.0 | -298.8 | 0.53 | 100.0% | 49.8% | -28.1 to -16.6 |
| 0.5% | 40 | 3286 | 83.9% | 16.1% | -42.3 | +10.1 | 83.9% | +10.1 | -316.2 | 0.17 | 100.0% | 49.8% | -48.1 to -36.6 |
| 0.8% | 0 | 3286 | 74.5% | 25.5% | +1.3 | +80.0 | 77.2% | +78.2 | -259.3 | 1.02 | 69.4% | 49.8% | -5.3 to +7.9 |
| 0.8% | 6 | 3286 | 74.5% | 25.5% | -4.7 | +74.0 | 77.1% | +72.4 | -263.6 | 0.92 | 92.4% | 49.8% | -11.3 to +1.9 |
| 0.8% | 12 | 3286 | 74.5% | 25.5% | -10.7 | +68.0 | 76.5% | +66.9 | -263.8 | 0.83 | 98.8% | 49.8% | -17.3 to -4.1 |
| 0.8% | 20 | 3286 | 74.5% | 25.5% | -18.7 | +60.1 | 76.2% | +59.2 | -268.2 | 0.71 | 99.9% | 49.8% | -25.3 to -12.1 |
| 0.8% | 40 | 3286 | 74.5% | 25.5% | -38.7 | +40.2 | 75.3% | +39.9 | -277.8 | 0.44 | 100.0% | 49.8% | -45.3 to -32.1 |
| 1% | 0 | 3286 | 68.2% | 31.8% | +2.0 | +100.0 | 72.9% | +95.7 | -250.4 | 1.03 | 72.1% | 49.8% | -5.1 to +9.1 |
| 1% | 6 | 3286 | 68.2% | 31.8% | -4.0 | +94.0 | 72.6% | +90.1 | -253.6 | 0.94 | 92.1% | 49.8% | -11.1 to +3.1 |
| 1% | 12 | 3286 | 68.2% | 31.8% | -10.0 | +88.1 | 72.0% | +84.9 | -253.9 | 0.86 | 98.7% | 49.8% | -17.1 to -2.9 |
| 1% | 20 | 3286 | 68.2% | 31.8% | -18.0 | +80.1 | 71.5% | +77.5 | -257.8 | 0.75 | 99.9% | 49.8% | -25.1 to -10.9 |
| 1% | 40 | 3286 | 68.2% | 31.8% | -38.0 | +60.2 | 69.9% | +59.1 | -263.9 | 0.52 | 100.0% | 49.8% | -45.2 to -30.9 |
| 1.5% | 0 | 3286 | 54.0% | 46.0% | -0.9 | +150.0 | 64.7% | +133.0 | -246.4 | 0.99 | 88.2% | 49.8% | -9.4 to +7.6 |
| 1.5% | 6 | 3286 | 54.0% | 46.0% | -6.9 | +144.0 | 64.2% | +128.2 | -248.6 | 0.92 | 97.5% | 49.8% | -15.4 to +1.6 |
| 1.5% | 12 | 3286 | 54.0% | 46.0% | -12.9 | +138.1 | 63.2% | +124.1 | -248.0 | 0.86 | 99.6% | 49.8% | -21.4 to -4.4 |
| 1.5% | 20 | 3286 | 54.0% | 46.0% | -20.9 | +130.1 | 62.2% | +118.0 | -249.6 | 0.78 | 100.0% | 49.8% | -29.4 to -12.4 |
| 1.5% | 40 | 3286 | 54.0% | 46.0% | -40.9 | +110.3 | 59.8% | +102.6 | -254.1 | 0.60 | 100.0% | 49.8% | -49.4 to -32.4 |
| 2% | 0 | 3286 | 42.5% | 57.5% | -2.6 | +63.5 | 59.3% | +161.3 | -241.8 | 0.97 | 93.5% | 49.8% | -11.9 to +6.6 |
| 2% | 6 | 3286 | 42.5% | 57.5% | -8.6 | +57.5 | 58.6% | +157.2 | -243.8 | 0.91 | 98.8% | 49.8% | -17.9 to +0.6 |
| 2% | 12 | 3286 | 42.5% | 57.5% | -14.6 | +51.5 | 57.5% | +154.3 | -243.3 | 0.86 | 99.8% | 49.8% | -23.9 to -5.3 |
| 2% | 20 | 3286 | 42.5% | 57.5% | -22.6 | +43.5 | 56.4% | +149.3 | -245.0 | 0.79 | 100.0% | 49.8% | -31.9 to -13.3 |
| 2% | 40 | 3286 | 42.5% | 57.5% | -42.6 | +23.6 | 53.5% | +137.1 | -249.2 | 0.63 | 100.0% | 49.8% | -51.9 to -33.3 |
| 3% | 0 | 3286 | 27.1% | 72.9% | -1.8 | +26.6 | 54.6% | +196.0 | -240.0 | 0.98 | 94.1% | 49.8% | -12.0 to +8.3 |
| 3% | 6 | 3286 | 27.1% | 72.9% | -7.8 | +20.6 | 53.9% | +192.7 | -242.2 | 0.93 | 98.9% | 49.8% | -18.0 to +2.3 |
| 3% | 12 | 3286 | 27.1% | 72.9% | -13.8 | +14.6 | 52.5% | +191.8 | -241.1 | 0.88 | 99.8% | 49.8% | -24.0 to -3.7 |
| 3% | 20 | 3286 | 27.1% | 72.9% | -21.8 | +6.6 | 51.1% | +188.9 | -242.3 | 0.82 | 100.0% | 49.8% | -32.0 to -11.7 |
| 3% | 40 | 3286 | 27.1% | 72.9% | -41.8 | -13.4 | 47.8% | +181.4 | -246.6 | 0.67 | 100.0% | 49.8% | -52.0 to -31.6 |

TP hit includes the rare fills at N's open through the take-profit. Max DD is the largest peak-to-trough fall of the curve that compounds every trade at one unit of notional. Bars in position is the share of 8h bars during which a short was open at some point.

### Against the baselines at 12 bps

| X | Green short (the idea) | Red short | Every-candle short | Random-half short | Green long (flipped) | Green minus red (bps) | 95% interval | Beats every baseline | P(random same-size set >= green) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.3% | -14.9 | -9.1 | -12.1 | -12.1 | -10.8 | -5.8 | -11.7 to +0.0 | no | 0.97 |
| 0.5% | -14.3 | -6.6 | -10.7 | -10.8 | -10.4 | -7.8 | -15.1 to -0.4 | no | 0.97 |
| 0.8% | -10.7 | -6.3 | -8.9 | -8.8 | -10.2 | -4.4 | -13.3 to +4.4 | no | 0.79 |
| 1% | -10.0 | -7.0 | -8.9 | -8.8 | -10.7 | -3.0 | -12.9 to +6.9 | no | 0.67 |
| 1.5% | -12.9 | -5.8 | -9.8 | -9.6 | -11.5 | -7.1 | -18.8 to +4.6 | no | 0.85 |
| 2% | -14.6 | -4.9 | -10.1 | -9.9 | -8.6 | -9.8 | -22.6 to +3.0 | no | 0.91 |
| 3% | -13.8 | -6.6 | -10.5 | -10.3 | -5.0 | -7.2 | -21.4 to +6.9 | no | 0.81 |

Mean return per trade in bps. Random-half is the average over 1,000 random halves of the candles. The last column is the share of 5,000 random candle sets, the same size as the green set, whose mean short return was at least as good as the green set's. A value near 0 would mean green candles are a better-than-random place to short. These are not.

### All five strategies at X = 1% and 12 bps

| Strategy | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Green short (the idea) | 3286 | 68.2% | 31.8% | -10.0 | +88.1 | 72.0% | +84.9 | -253.9 | 0.86 | 98.7% | 49.8% | -17.1 to -2.9 |
| Red short | 3289 | 68.2% | 31.8% | -7.0 | +88.1 | 70.5% | +86.1 | -229.9 | 0.90 | 97.4% | 49.8% | -13.9 to -0.2 |
| Every-candle short | 6601 | 68.1% | 31.9% | -8.9 | +88.1 | 71.2% | +85.5 | -242.0 | 0.87 | 100.0% | 100.0% | -13.8 to -3.9 |
| Random-half short | 3300 | 68.1% | 31.9% | -8.8 | +88.1 | 71.2% | +85.5 | -241.8 | 0.88 | 97.4% | 50.0% | -13.7 to -3.6 |
| Green long (flipped) | 3286 | 65.2% | 34.8% | -10.7 | +87.9 | 68.8% | +84.7 | -221.4 | 0.84 | 98.7% | 49.8% | -16.9 to -4.6 |

The interval for the random-half row is the 2.5th to 97.5th percentile of the mean across the 1,000 draws.

### Mean return per trade, every strategy at every cost

| X | Cost (bps) | Green short (the idea) | Red short | Every-candle short | Random-half short | Green long (flipped) |
|---|---:|---:|---:|---:|---:|---:|
| 0.3% | 0 | -2.9 | +2.9 | -0.1 | -0.1 | +1.2 |
| 0.3% | 6 | -8.9 | -3.1 | -6.1 | -6.1 | -4.8 |
| 0.3% | 12 | -14.9 | -9.1 | -12.1 | -12.1 | -10.8 |
| 0.3% | 20 | -22.9 | -17.1 | -20.1 | -20.1 | -18.8 |
| 0.3% | 40 | -42.9 | -37.1 | -40.1 | -40.1 | -38.8 |
| 0.5% | 0 | -2.3 | +5.4 | +1.3 | +1.2 | +1.6 |
| 0.5% | 6 | -8.3 | -0.6 | -4.7 | -4.8 | -4.4 |
| 0.5% | 12 | -14.3 | -6.6 | -10.7 | -10.8 | -10.4 |
| 0.5% | 20 | -22.3 | -14.6 | -18.7 | -18.8 | -18.4 |
| 0.5% | 40 | -42.3 | -34.6 | -38.7 | -38.8 | -38.4 |
| 0.8% | 0 | +1.3 | +5.7 | +3.1 | +3.2 | +1.8 |
| 0.8% | 6 | -4.7 | -0.3 | -2.9 | -2.8 | -4.2 |
| 0.8% | 12 | -10.7 | -6.3 | -8.9 | -8.8 | -10.2 |
| 0.8% | 20 | -18.7 | -14.3 | -16.9 | -16.8 | -18.2 |
| 0.8% | 40 | -38.7 | -34.3 | -36.9 | -36.8 | -38.2 |
| 1% | 0 | +2.0 | +5.0 | +3.1 | +3.2 | +1.3 |
| 1% | 6 | -4.0 | -1.0 | -2.9 | -2.8 | -4.7 |
| 1% | 12 | -10.0 | -7.0 | -8.9 | -8.8 | -10.7 |
| 1% | 20 | -18.0 | -15.0 | -16.9 | -16.8 | -18.7 |
| 1% | 40 | -38.0 | -35.0 | -36.9 | -36.8 | -38.8 |
| 1.5% | 0 | -0.9 | +6.2 | +2.2 | +2.4 | +0.5 |
| 1.5% | 6 | -6.9 | +0.2 | -3.8 | -3.6 | -5.5 |
| 1.5% | 12 | -12.9 | -5.8 | -9.8 | -9.6 | -11.5 |
| 1.5% | 20 | -20.9 | -13.8 | -17.8 | -17.6 | -19.5 |
| 1.5% | 40 | -40.9 | -33.8 | -37.8 | -37.6 | -39.5 |
| 2% | 0 | -2.6 | +7.1 | +1.9 | +2.1 | +3.4 |
| 2% | 6 | -8.6 | +1.1 | -4.1 | -3.9 | -2.6 |
| 2% | 12 | -14.6 | -4.9 | -10.1 | -9.9 | -8.6 |
| 2% | 20 | -22.6 | -12.9 | -18.1 | -17.9 | -16.6 |
| 2% | 40 | -42.6 | -32.8 | -38.1 | -37.9 | -36.6 |
| 3% | 0 | -1.8 | +5.4 | +1.5 | +1.7 | +7.1 |
| 3% | 6 | -7.8 | -0.6 | -4.5 | -4.3 | +1.0 |
| 3% | 12 | -13.8 | -6.6 | -10.5 | -10.3 | -5.0 |
| 3% | 20 | -21.8 | -14.6 | -18.5 | -18.3 | -13.0 |
| 3% | 40 | -41.8 | -34.6 | -38.5 | -38.3 | -33.0 |

## Confirmation slice: the last 90 days

Trades entered 2026-08-20 16:00 to 2026-11-18 08:00 UTC. X = 1% is the only row that was pre-chosen. SOL went from 87.37 to 73.49 over the window (-15.9%).

### All five strategies at the locked X = 1% and 12 bps

| Strategy | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Green short (the idea) | 139 | 56.1% | 43.9% | -0.6 | +88.1 | 61.2% | +84.3 | -134.2 | 0.99 | 19.6% | 51.5% | -22.5 to +21.3 |
| Red short | 131 | 47.3% | 52.7% | -18.3 | +20.7 | 53.4% | +80.5 | -131.8 | 0.70 | 26.5% | 48.5% | -42.0 to +5.4 |
| Every-candle short | 270 | 51.9% | 48.1% | -9.2 | +88.1 | 57.4% | +82.6 | -132.9 | 0.84 | 35.7% | 100.0% | -25.3 to +6.9 |
| Random-half short | 135 | 51.7% | 48.3% | -9.3 | +74.6 | 57.3% | +82.6 | -132.5 | 0.85 | 21.9% | 50.0% | -24.5 to +6.8 |
| Green long (flipped) | 139 | 40.3% | 59.7% | -30.0 | +19.0 | 52.5% | +74.7 | -146.0 | 0.57 | 37.4% | 51.5% | -53.0 to -7.1 |

A bootstrap of the 139 green-short returns gives a 95% interval of -23.2 to +20.6 bps for the mean; 48.7% of resamples were above zero. That is a coin flip around zero, after costs, in a falling market.

### Green-candle short, every X and every cost

| X | Cost (bps) | Signals | TP hit | Expired | Mean (bps) | Median (bps) | Win rate | Avg win (bps) | Avg loss (bps) | Profit factor | Max DD | Bars in position | 95% interval for mean (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.3% | 0 | 139 | 88.5% | 11.5% | +9.6 | +30.0 | 89.2% | +29.8 | -157.3 | 1.57 | 8.0% | 51.5% | -2.4 to +21.7 |
| 0.3% | 6 | 139 | 88.5% | 11.5% | +3.6 | +24.0 | 89.2% | +23.8 | -163.3 | 1.21 | 10.6% | 51.5% | -8.4 to +15.7 |
| 0.3% | 12 | 139 | 88.5% | 11.5% | -2.4 | +18.0 | 88.5% | +18.0 | -159.1 | 0.87 | 13.3% | 51.5% | -14.4 to +9.7 |
| 0.3% | 20 | 139 | 88.5% | 11.5% | -10.4 | +10.0 | 88.5% | +10.0 | -167.1 | 0.46 | 17.8% | 51.5% | -22.4 to +1.7 |
| 0.3% | 40 | 139 | 88.5% | 11.5% | -30.4 | -9.9 | 0.0% | n/a | -30.4 | 0.00 | 34.7% | 51.5% | -42.4 to -18.3 |
| 0.5% | 0 | 139 | 78.4% | 21.6% | +10.2 | +50.0 | 79.1% | +49.6 | -139.3 | 1.35 | 14.5% | 51.5% | -5.9 to +26.3 |
| 0.5% | 6 | 139 | 78.4% | 21.6% | +4.2 | +44.0 | 79.1% | +43.6 | -145.3 | 1.14 | 15.1% | 51.5% | -11.9 to +20.3 |
| 0.5% | 12 | 139 | 78.4% | 21.6% | -1.8 | +38.0 | 78.4% | +38.0 | -146.5 | 0.94 | 15.7% | 51.5% | -17.9 to +14.3 |
| 0.5% | 20 | 139 | 78.4% | 21.6% | -9.8 | +30.0 | 78.4% | +30.1 | -154.5 | 0.71 | 20.4% | 51.5% | -25.9 to +6.3 |
| 0.5% | 40 | 139 | 78.4% | 21.6% | -29.8 | +10.1 | 78.4% | +10.1 | -174.6 | 0.21 | 34.6% | 51.5% | -45.9 to -13.6 |
| 0.8% | 0 | 139 | 62.6% | 37.4% | +5.9 | +80.0 | 65.5% | +77.6 | -130.1 | 1.13 | 18.6% | 51.5% | -14.6 to +26.3 |
| 0.8% | 6 | 139 | 62.6% | 37.4% | -0.1 | +74.0 | 65.5% | +71.6 | -136.1 | 1.00 | 19.2% | 51.5% | -20.6 to +20.4 |
| 0.8% | 12 | 139 | 62.6% | 37.4% | -6.1 | +68.0 | 64.0% | +67.2 | -136.6 | 0.88 | 19.7% | 51.5% | -26.6 to +14.4 |
| 0.8% | 20 | 139 | 62.6% | 37.4% | -14.1 | +60.1 | 64.0% | +59.2 | -144.7 | 0.73 | 21.8% | 51.5% | -34.6 to +6.4 |
| 0.8% | 40 | 139 | 62.6% | 37.4% | -34.1 | +40.2 | 63.3% | +39.8 | -161.6 | 0.42 | 39.2% | 51.5% | -54.7 to -13.6 |
| 1% | 0 | 139 | 56.1% | 43.9% | +11.4 | +100.0 | 62.6% | +94.2 | -127.1 | 1.24 | 18.3% | 51.5% | -10.5 to +33.3 |
| 1% | 6 | 139 | 56.1% | 43.9% | +5.4 | +94.0 | 62.6% | +88.2 | -133.2 | 1.11 | 18.8% | 51.5% | -16.5 to +27.3 |
| 1% | 12 | 139 | 56.1% | 43.9% | -0.6 | +88.1 | 61.2% | +84.3 | -134.2 | 0.99 | 19.6% | 51.5% | -22.5 to +21.3 |
| 1% | 20 | 139 | 56.1% | 43.9% | -8.6 | +80.1 | 61.2% | +76.3 | -142.2 | 0.84 | 22.6% | 51.5% | -30.5 to +13.3 |
| 1% | 40 | 139 | 56.1% | 43.9% | -28.6 | +60.2 | 59.7% | +57.9 | -156.8 | 0.55 | 34.8% | 51.5% | -50.5 to -6.6 |
| 1.5% | 0 | 139 | 37.4% | 62.6% | +19.2 | +56.4 | 58.3% | +118.8 | -120.0 | 1.38 | 20.7% | 51.5% | -5.0 to +43.3 |
| 1.5% | 6 | 139 | 37.4% | 62.6% | +13.2 | +50.4 | 57.6% | +114.3 | -124.0 | 1.25 | 21.5% | 51.5% | -11.0 to +37.3 |
| 1.5% | 12 | 139 | 37.4% | 62.6% | +7.2 | +44.4 | 56.1% | +111.2 | -125.9 | 1.13 | 22.6% | 51.5% | -17.0 to +31.3 |
| 1.5% | 20 | 139 | 37.4% | 62.6% | -0.8 | +36.4 | 56.1% | +103.3 | -133.9 | 0.99 | 24.6% | 51.5% | -25.0 to +23.3 |
| 1.5% | 40 | 139 | 37.4% | 62.6% | -20.8 | +16.5 | 54.0% | +86.9 | -147.1 | 0.69 | 31.9% | 51.5% | -45.0 to +3.4 |
| 2% | 0 | 139 | 27.3% | 72.7% | +22.9 | +47.2 | 56.1% | +135.8 | -121.5 | 1.43 | 21.2% | 51.5% | -3.5 to +49.3 |
| 2% | 6 | 139 | 27.3% | 72.7% | +16.9 | +41.2 | 55.4% | +131.6 | -125.5 | 1.30 | 22.2% | 51.5% | -9.5 to +43.3 |
| 2% | 12 | 139 | 27.3% | 72.7% | +10.9 | +35.2 | 54.0% | +129.1 | -127.5 | 1.19 | 23.2% | 51.5% | -15.5 to +37.3 |
| 2% | 20 | 139 | 27.3% | 72.7% | +3.0 | +27.2 | 54.0% | +121.2 | -135.6 | 1.05 | 25.3% | 51.5% | -23.5 to +29.4 |
| 2% | 40 | 139 | 27.3% | 72.7% | -17.0 | +7.3 | 51.1% | +107.4 | -147.0 | 0.76 | 33.1% | 51.5% | -43.5 to +9.4 |
| 3% | 0 | 139 | 12.9% | 87.1% | +27.1 | +38.6 | 54.7% | +148.7 | -119.6 | 1.50 | 22.1% | 51.5% | -1.4 to +55.7 |
| 3% | 6 | 139 | 12.9% | 87.1% | +21.1 | +32.6 | 54.0% | +144.7 | -123.7 | 1.37 | 23.5% | 51.5% | -7.4 to +49.7 |
| 3% | 12 | 139 | 12.9% | 87.1% | +15.1 | +26.6 | 52.5% | +142.7 | -125.9 | 1.25 | 25.3% | 51.5% | -13.4 to +43.7 |
| 3% | 20 | 139 | 12.9% | 87.1% | +7.1 | +18.6 | 52.5% | +134.7 | -134.0 | 1.11 | 27.6% | 51.5% | -21.4 to +35.7 |
| 3% | 40 | 139 | 12.9% | 87.1% | -12.8 | -1.4 | 49.6% | +121.9 | -145.7 | 0.83 | 34.1% | 51.5% | -41.4 to +15.8 |

The rows for X = 1.5%, 2%, 3% are positive after 12 bps on this slice. They were not chosen in advance, none has an interval that excludes zero, and on discovery data those same X values returned -12.9, -14.6, -13.8 bps. What happened in these 90 days is that candles reversed: the candle after a green one averaged -24.2 bps and the candle after a red one +15.8 bps. Over the six years before, the candle after a green one averaged +12.8 bps and after a red one +8.7 bps, the opposite ordering. One 90-day window of 139 trades cannot tell a new pattern from noise.

### Against the baselines at 12 bps

| X | Green short (the idea) | Red short | Every-candle short | Random-half short | Green long (flipped) | Green minus red (bps) | 95% interval | Beats every baseline | P(random same-size set >= green) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.3% | -2.4 | -9.7 | -5.9 | -6.1 | -12.0 | +7.4 | -11.6 to +26.4 | yes | 0.23 |
| 0.5% | -1.8 | -19.1 | -10.2 | -10.2 | -20.5 | +17.3 | -8.8 to +43.4 | yes | 0.10 |
| 0.8% | -6.1 | -17.2 | -11.5 | -11.7 | -25.5 | +11.1 | -19.2 to +41.4 | yes | 0.24 |
| 1% | -0.6 | -18.3 | -9.2 | -9.3 | -30.0 | +17.7 | -14.5 to +50.0 | yes | 0.14 |
| 1.5% | +7.2 | -22.1 | -7.0 | -7.0 | -40.7 | +29.3 | -6.5 to +65.0 | yes | 0.05 |
| 2% | +10.9 | -14.4 | -1.4 | -1.1 | -36.5 | +25.4 | -13.5 to +64.3 | yes | 0.10 |
| 3% | +15.1 | -15.6 | +0.2 | +0.7 | -30.6 | +30.7 | -11.1 to +72.6 | yes | 0.08 |

### Mean return per trade, every strategy at every cost

| X | Cost (bps) | Green short (the idea) | Red short | Every-candle short | Random-half short | Green long (flipped) |
|---|---:|---:|---:|---:|---:|---:|
| 0.3% | 0 | +9.6 | +2.3 | +6.1 | +5.9 | +0.0 |
| 0.3% | 6 | +3.6 | -3.7 | +0.1 | -0.1 | -6.0 |
| 0.3% | 12 | -2.4 | -9.7 | -5.9 | -6.1 | -12.0 |
| 0.3% | 20 | -10.4 | -17.7 | -13.9 | -14.1 | -20.0 |
| 0.3% | 40 | -30.4 | -37.7 | -33.9 | -34.1 | -40.0 |
| 0.5% | 0 | +10.2 | -7.1 | +1.8 | +1.8 | -8.5 |
| 0.5% | 6 | +4.2 | -13.1 | -4.2 | -4.2 | -14.5 |
| 0.5% | 12 | -1.8 | -19.1 | -10.2 | -10.2 | -20.5 |
| 0.5% | 20 | -9.8 | -27.1 | -18.2 | -18.2 | -28.5 |
| 0.5% | 40 | -29.8 | -47.1 | -38.2 | -38.2 | -48.5 |
| 0.8% | 0 | +5.9 | -5.2 | +0.5 | +0.3 | -13.5 |
| 0.8% | 6 | -0.1 | -11.2 | -5.5 | -5.7 | -19.5 |
| 0.8% | 12 | -6.1 | -17.2 | -11.5 | -11.7 | -25.5 |
| 0.8% | 20 | -14.1 | -25.2 | -19.5 | -19.7 | -33.5 |
| 0.8% | 40 | -34.1 | -45.2 | -39.5 | -39.7 | -53.5 |
| 1% | 0 | +11.4 | -6.3 | +2.8 | +2.7 | -18.1 |
| 1% | 6 | +5.4 | -12.3 | -3.2 | -3.3 | -24.1 |
| 1% | 12 | -0.6 | -18.3 | -9.2 | -9.3 | -30.0 |
| 1% | 20 | -8.6 | -26.3 | -17.2 | -17.3 | -38.0 |
| 1% | 40 | -28.6 | -46.3 | -37.2 | -37.3 | -58.0 |
| 1.5% | 0 | +19.2 | -10.1 | +5.0 | +5.0 | -28.7 |
| 1.5% | 6 | +13.2 | -16.1 | -1.0 | -1.0 | -34.7 |
| 1.5% | 12 | +7.2 | -22.1 | -7.0 | -7.0 | -40.7 |
| 1.5% | 20 | -0.8 | -30.1 | -15.0 | -15.0 | -48.7 |
| 1.5% | 40 | -20.8 | -50.1 | -35.0 | -35.0 | -68.6 |
| 2% | 0 | +22.9 | -2.4 | +10.6 | +10.9 | -24.5 |
| 2% | 6 | +16.9 | -8.4 | +4.6 | +4.9 | -30.5 |
| 2% | 12 | +10.9 | -14.4 | -1.4 | -1.1 | -36.5 |
| 2% | 20 | +3.0 | -22.4 | -9.4 | -9.1 | -44.5 |
| 2% | 40 | -17.0 | -42.4 | -29.4 | -29.1 | -64.5 |
| 3% | 0 | +27.1 | -3.6 | +12.2 | +12.7 | -18.6 |
| 3% | 6 | +21.1 | -9.6 | +6.2 | +6.7 | -24.6 |
| 3% | 12 | +15.1 | -15.6 | +0.2 | +0.7 | -30.6 |
| 3% | 20 | +7.1 | -23.6 | -7.8 | -7.3 | -38.5 |
| 3% | 40 | -12.8 | -43.6 | -27.8 | -27.3 | -58.5 |

## By period

Green short and red short at X = 1%, Binance, entry at C's close. 2026 is year to date.

| Period | Cost (bps) | Green signals | Green TP hit | Green mean (bps) | 95% interval (bps) | Green profit factor | Green max DD | Red mean (bps) | Red TP hit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| full history | 0 | 3425 | 67.7% | +2.3 | -4.5 to +9.2 | 1.03 | 72.1% | +4.5 | 67.4% |
| full history | 6 | 3425 | 67.7% | -3.7 | -10.5 to +3.2 | 0.95 | 92.1% | -1.5 | 67.4% |
| full history | 12 | 3425 | 67.7% | -9.7 | -16.5 to -2.8 | 0.86 | 98.7% | -7.5 | 67.4% |
| full history | 20 | 3425 | 67.7% | -17.7 | -24.5 to -10.8 | 0.76 | 99.9% | -15.5 | 67.4% |
| full history | 40 | 3425 | 67.7% | -37.7 | -44.5 to -30.8 | 0.52 | 100.0% | -35.5 | 67.4% |
| 2020 | 0 | 198 | 81.3% | -3.5 | -42.0 to +35.0 | 0.96 | 37.8% | +37.0 | 85.7% |
| 2020 | 6 | 198 | 81.3% | -9.5 | -48.0 to +29.0 | 0.89 | 38.7% | +31.0 | 85.7% |
| 2020 | 12 | 198 | 81.3% | -15.5 | -54.0 to +23.0 | 0.82 | 40.5% | +25.1 | 85.7% |
| 2020 | 20 | 198 | 81.3% | -23.5 | -62.0 to +15.0 | 0.73 | 46.4% | +17.1 | 85.7% |
| 2020 | 40 | 198 | 81.3% | -43.5 | -82.1 to -5.0 | 0.53 | 62.7% | -2.9 | 85.7% |
| 2021 | 0 | 546 | 80.4% | -10.7 | -33.6 to +12.2 | 0.88 | 63.0% | +5.4 | 81.2% |
| 2021 | 6 | 546 | 80.4% | -16.7 | -39.6 to +6.2 | 0.82 | 72.4% | -0.6 | 81.2% |
| 2021 | 12 | 546 | 80.4% | -22.7 | -45.6 to +0.2 | 0.76 | 79.7% | -6.6 | 81.2% |
| 2021 | 20 | 546 | 80.4% | -30.7 | -53.6 to -7.8 | 0.68 | 86.4% | -14.5 | 81.2% |
| 2021 | 40 | 546 | 80.4% | -50.7 | -73.7 to -27.8 | 0.49 | 95.2% | -34.5 | 81.2% |
| 2022 | 0 | 528 | 75.9% | +26.4 | +12.1 to +40.7 | 1.52 | 18.3% | -3.4 | 69.8% |
| 2022 | 6 | 528 | 75.9% | +20.4 | +6.1 to +34.7 | 1.39 | 18.7% | -9.4 | 69.8% |
| 2022 | 12 | 528 | 75.9% | +14.4 | +0.1 to +28.7 | 1.27 | 21.3% | -15.4 | 69.8% |
| 2022 | 20 | 528 | 75.9% | +6.4 | -7.9 to +20.7 | 1.12 | 29.2% | -23.4 | 69.8% |
| 2022 | 40 | 528 | 75.9% | -13.6 | -27.9 to +0.8 | 0.77 | 60.0% | -43.4 | 69.8% |
| 2023 | 0 | 559 | 62.6% | -13.6 | -33.8 to +6.6 | 0.83 | 67.4% | +5.5 | 64.4% |
| 2023 | 6 | 559 | 62.6% | -19.6 | -39.8 to +0.6 | 0.76 | 76.2% | -0.5 | 64.4% |
| 2023 | 12 | 559 | 62.6% | -25.6 | -45.8 to -5.4 | 0.69 | 82.7% | -6.5 | 64.4% |
| 2023 | 20 | 559 | 62.6% | -33.6 | -53.8 to -13.4 | 0.60 | 88.7% | -14.5 | 64.4% |
| 2023 | 40 | 559 | 62.6% | -53.6 | -73.8 to -33.4 | 0.42 | 96.1% | -34.5 | 64.4% |
| 2024 | 0 | 571 | 66.9% | +8.6 | -4.8 to +22.0 | 1.14 | 24.2% | +5.7 | 64.4% |
| 2024 | 6 | 571 | 66.9% | +2.6 | -10.8 to +16.0 | 1.04 | 33.3% | -0.3 | 64.4% |
| 2024 | 12 | 571 | 66.9% | -3.4 | -16.8 to +10.0 | 0.95 | 44.7% | -6.3 | 64.4% |
| 2024 | 20 | 571 | 66.9% | -11.4 | -24.8 to +2.0 | 0.83 | 58.3% | -14.3 | 64.4% |
| 2024 | 40 | 571 | 66.9% | -31.4 | -44.9 to -17.9 | 0.56 | 85.6% | -34.3 | 64.4% |
| 2025 | 0 | 550 | 62.2% | -2.4 | -17.0 to +12.3 | 0.96 | 29.1% | -1.0 | 62.6% |
| 2025 | 6 | 550 | 62.2% | -8.4 | -23.0 to +6.3 | 0.88 | 47.8% | -7.0 | 62.6% |
| 2025 | 12 | 550 | 62.2% | -14.4 | -29.0 to +0.3 | 0.80 | 61.8% | -13.0 | 62.6% |
| 2025 | 20 | 550 | 62.2% | -22.4 | -37.0 to -7.7 | 0.69 | 74.8% | -21.0 | 62.6% |
| 2025 | 40 | 550 | 62.2% | -42.4 | -57.1 to -27.7 | 0.47 | 91.3% | -41.0 | 62.6% |
| 2026 | 0 | 473 | 51.6% | +9.8 | -1.9 to +21.5 | 1.21 | 24.5% | +1.2 | 52.2% |
| 2026 | 6 | 473 | 51.6% | +3.8 | -7.9 to +15.5 | 1.08 | 26.5% | -4.7 | 52.2% |
| 2026 | 12 | 473 | 51.6% | -2.2 | -13.9 to +9.5 | 0.96 | 30.4% | -10.7 | 52.2% |
| 2026 | 20 | 473 | 51.6% | -10.2 | -21.9 to +1.5 | 0.81 | 47.6% | -18.7 | 52.2% |
| 2026 | 40 | 473 | 51.6% | -30.2 | -41.9 to -18.5 | 0.51 | 77.4% | -38.7 | 52.2% |
| last 365d | 0 | 535 | 51.8% | +6.8 | -4.8 to +18.4 | 1.14 | 30.6% | +1.4 | 51.8% |
| last 365d | 6 | 535 | 51.8% | +0.8 | -10.8 to +12.4 | 1.02 | 36.7% | -4.6 | 51.8% |
| last 365d | 12 | 535 | 51.8% | -5.2 | -16.8 to +6.4 | 0.90 | 42.2% | -10.6 | 51.8% |
| last 365d | 20 | 535 | 51.8% | -13.2 | -24.8 to -1.6 | 0.77 | 58.6% | -18.6 | 51.8% |
| last 365d | 40 | 535 | 51.8% | -33.2 | -44.8 to -21.6 | 0.49 | 84.2% | -38.6 | 51.8% |
| confirmation (last 90d) | 0 | 139 | 56.1% | +11.4 | -10.5 to +33.3 | 1.24 | 18.3% | -6.3 | 47.3% |
| confirmation (last 90d) | 6 | 139 | 56.1% | +5.4 | -16.5 to +27.3 | 1.11 | 18.8% | -12.3 | 47.3% |
| confirmation (last 90d) | 12 | 139 | 56.1% | -0.6 | -22.5 to +21.3 | 0.99 | 19.6% | -18.3 | 47.3% |
| confirmation (last 90d) | 20 | 139 | 56.1% | -8.6 | -30.5 to +13.3 | 0.84 | 22.6% | -26.3 | 47.3% |
| confirmation (last 90d) | 40 | 139 | 56.1% | -28.6 | -50.5 to -6.6 | 0.55 | 34.8% | -46.3 | 47.3% |

### Green short, mean per trade after 12 bps, every X by period

| Period | X = 0.3% | X = 0.5% | X = 0.8% | X = 1% | X = 1.5% | X = 2% | X = 3% |
|---|---:|---:|---:|---:|---:|---:|---:|
| full history | -14.4 | -13.8 | -10.5 | -9.7 | -12.1 | -13.6 | -12.7 |
| 2020 | -32.0 | -35.5 | -28.5 | -15.5 | -25.5 | -19.6 | -3.2 |
| 2021 | -28.0 | -22.0 | -19.3 | -22.7 | -32.2 | -42.1 | -31.0 |
| 2022 | -3.3 | -4.7 | +7.0 | +14.4 | +13.4 | +14.9 | +16.9 |
| 2023 | -12.9 | -15.5 | -19.4 | -25.6 | -28.0 | -31.9 | -38.3 |
| 2024 | -10.7 | -9.4 | -6.1 | -3.4 | -1.1 | -2.7 | -8.0 |
| 2025 | -18.1 | -17.5 | -13.6 | -14.4 | -14.6 | -12.8 | -13.3 |
| 2026 | -6.0 | -4.6 | -3.9 | -2.2 | -3.3 | -2.4 | -3.0 |
| last 365d | -5.6 | -4.9 | -5.0 | -5.2 | -5.3 | -2.5 | -2.2 |
| confirmation (last 90d) | -2.4 | -1.8 | -6.1 | -0.6 | +7.2 | +10.9 | +15.1 |

### Red short, mean per trade after 12 bps, every X by period

| Period | X = 0.3% | X = 0.5% | X = 0.8% | X = 1% | X = 1.5% | X = 2% | X = 3% |
|---|---:|---:|---:|---:|---:|---:|---:|
| full history | -9.1 | -7.0 | -6.7 | -7.5 | -6.5 | -5.2 | -7.0 |
| 2020 | -1.4 | +3.3 | +16.0 | +25.1 | +28.8 | +33.7 | +30.9 |
| 2021 | -1.2 | +0.8 | -0.7 | -6.6 | -9.9 | -14.3 | -20.0 |
| 2022 | -12.6 | -12.1 | -16.3 | -15.4 | -9.7 | -10.1 | -3.6 |
| 2023 | -4.7 | -4.4 | -1.0 | -6.5 | -10.5 | -13.5 | -19.7 |
| 2024 | -14.2 | -8.9 | -6.0 | -6.3 | -5.9 | -1.9 | -6.6 |
| 2025 | -12.4 | -10.0 | -15.2 | -13.0 | -6.2 | -2.9 | -4.0 |
| 2026 | -13.3 | -12.4 | -10.5 | -10.7 | -11.9 | -5.1 | -3.9 |
| last 365d | -12.2 | -11.4 | -10.0 | -10.6 | -12.0 | -6.3 | -4.9 |
| confirmation (last 90d) | -9.7 | -19.1 | -17.2 | -18.3 | -22.1 | -14.4 | -15.6 |

The only calendar year in which the green short made money after 12 bps is 2022, when SOL lost most of its value. The trade is a short position in SOL with a capped upside, and it earns when SOL falls.

## Green signals by body size

Body = (close - open) / open of the signal candle. Mean return per trade after 12 bps, Binance, entry at C's close.

### Discovery

| X | Body <1% | Body 1-3% | Body 3-6% | Body >=6% |
|---|---:|---:|---:|---:|
| 0.3% | -18.5 (n=1164) | -13.4 (n=1257) | -13.0 (n=589) | -11.2 (n=276) |
| 0.5% | -19.3 (n=1164) | -11.6 (n=1257) | -12.2 (n=589) | -10.1 (n=276) |
| 0.8% | -15.4 (n=1164) | -9.9 (n=1257) | -6.1 (n=589) | -4.7 (n=276) |
| 1% | -16.2 (n=1164) | -8.6 (n=1257) | -4.7 (n=589) | -2.2 (n=276) |
| 1.5% | -16.8 (n=1164) | -11.7 (n=1257) | -12.9 (n=589) | -2.1 (n=276) |
| 2% | -17.1 (n=1164) | -12.7 (n=1257) | -15.3 (n=589) | -11.6 (n=276) |
| 3% | -14.3 (n=1164) | -15.5 (n=1257) | -15.9 (n=589) | +0.2 (n=276) |

At X = 1%, every cost:

| Body | Cost (bps) | Signals | TP hit | Mean (bps) | Median (bps) | Win rate | Profit factor | 95% interval (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| <1% | 0 | 1164 | 60.4% | -4.2 | +100.0 | 67.6% | 0.94 | -14.6 to +6.3 |
| <1% | 6 | 1164 | 60.4% | -10.2 | +94.0 | 67.3% | 0.85 | -20.6 to +0.3 |
| <1% | 12 | 1164 | 60.4% | -16.2 | +88.1 | 66.3% | 0.77 | -26.6 to -5.7 |
| <1% | 20 | 1164 | 60.4% | -24.2 | +80.1 | 65.9% | 0.67 | -34.6 to -13.7 |
| <1% | 40 | 1164 | 60.4% | -44.2 | +60.2 | 63.2% | 0.45 | -54.6 to -33.7 |
| 1-3% | 0 | 1257 | 68.6% | +3.4 | +100.0 | 73.0% | 1.05 | -7.7 to +14.4 |
| 1-3% | 6 | 1257 | 68.6% | -2.6 | +94.0 | 72.6% | 0.96 | -13.7 to +8.4 |
| 1-3% | 12 | 1257 | 68.6% | -8.6 | +88.1 | 71.8% | 0.88 | -19.7 to +2.5 |
| 1-3% | 20 | 1257 | 68.6% | -16.6 | +80.1 | 71.3% | 0.77 | -27.7 to -5.5 |
| 1-3% | 40 | 1257 | 68.6% | -36.6 | +60.2 | 69.9% | 0.53 | -47.7 to -25.5 |
| 3-6% | 0 | 589 | 75.0% | +7.3 | +100.0 | 77.2% | 1.11 | -9.9 to +24.6 |
| 3-6% | 6 | 589 | 75.0% | +1.3 | +94.0 | 76.9% | 1.02 | -15.9 to +18.6 |
| 3-6% | 12 | 589 | 75.0% | -4.7 | +88.1 | 76.9% | 0.93 | -21.9 to +12.6 |
| 3-6% | 20 | 589 | 75.0% | -12.7 | +80.1 | 76.6% | 0.83 | -29.9 to +4.6 |
| 3-6% | 40 | 589 | 75.0% | -32.7 | +60.2 | 75.9% | 0.58 | -49.9 to -15.4 |
| >=6% | 0 | 276 | 84.8% | +9.8 | +100.0 | 85.9% | 1.13 | -26.6 to +46.2 |
| >=6% | 6 | 276 | 84.8% | +3.8 | +94.0 | 85.9% | 1.05 | -32.6 to +40.2 |
| >=6% | 12 | 276 | 84.8% | -2.2 | +88.1 | 85.9% | 0.97 | -38.6 to +34.3 |
| >=6% | 20 | 276 | 84.8% | -10.2 | +80.1 | 85.5% | 0.87 | -46.6 to +26.3 |
| >=6% | 40 | 276 | 84.8% | -30.2 | +60.2 | 85.5% | 0.63 | -66.7 to +6.3 |

### Confirmation (last 90 days)

| X | Body <1% | Body 1-3% | Body 3-6% | Body >=6% |
|---|---:|---:|---:|---:|
| 0.3% | -9.9 (n=77) | +11.9 (n=51) | -18.9 (n=10) | +18.0 (n=1) |
| 0.5% | -1.4 (n=77) | +12.5 (n=51) | -81.8 (n=10) | +38.0 (n=1) |
| 0.8% | -13.8 (n=77) | +20.7 (n=51) | -91.2 (n=10) | +68.0 (n=1) |
| 1% | -7.0 (n=77) | +23.5 (n=51) | -83.2 (n=10) | +88.1 (n=1) |
| 1.5% | -1.1 (n=77) | +36.1 (n=51) | -89.6 (n=10) | +138.1 (n=1) |
| 2% | +11.4 (n=77) | +31.9 (n=51) | -99.7 (n=10) | +14.5 (n=1) |
| 3% | +13.0 (n=77) | +42.5 (n=51) | -108.4 (n=10) | +14.5 (n=1) |

At X = 1%, every cost:

| Body | Cost (bps) | Signals | TP hit | Mean (bps) | Median (bps) | Win rate | Profit factor | 95% interval (bps) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| <1% | 0 | 77 | 53.2% | +5.0 | +100.0 | 59.7% | 1.10 | -25.7 to +35.7 |
| <1% | 6 | 77 | 53.2% | -1.0 | +94.0 | 59.7% | 0.98 | -31.7 to +29.7 |
| <1% | 12 | 77 | 53.2% | -7.0 | +88.1 | 58.4% | 0.87 | -37.7 to +23.7 |
| <1% | 20 | 77 | 53.2% | -15.0 | +80.1 | 58.4% | 0.75 | -45.7 to +15.7 |
| <1% | 40 | 77 | 53.2% | -35.0 | +60.2 | 55.8% | 0.48 | -65.7 to -4.2 |
| 1-3% | 0 | 51 | 62.7% | +35.5 | +100.0 | 70.6% | 2.13 | +7.7 to +63.3 |
| 1-3% | 6 | 51 | 62.7% | +29.5 | +94.0 | 70.6% | 1.89 | +1.7 to +57.3 |
| 1-3% | 12 | 51 | 62.7% | +23.5 | +88.1 | 68.6% | 1.67 | -4.3 to +51.3 |
| 1-3% | 20 | 51 | 62.7% | +15.5 | +80.1 | 68.6% | 1.41 | -12.3 to +43.3 |
| 1-3% | 40 | 51 | 62.7% | -4.5 | +60.2 | 68.6% | 0.90 | -32.3 to +23.4 |
| 3-6% | 0 | 10 | 40.0% | -71.2 | -56.8 | 40.0% | 0.36 | -191.5 to +49.2 |
| 3-6% | 6 | 10 | 40.0% | -77.2 | -62.8 | 40.0% | 0.33 | -197.6 to +43.2 |
| 3-6% | 12 | 10 | 40.0% | -83.2 | -68.8 | 40.0% | 0.30 | -203.6 to +37.2 |
| 3-6% | 20 | 10 | 40.0% | -91.2 | -76.8 | 40.0% | 0.26 | -211.7 to +29.3 |
| 3-6% | 40 | 10 | 40.0% | -111.3 | -96.9 | 40.0% | 0.18 | -231.9 to +9.3 |
| >=6% | 0 | 1 | 100.0% | +100.0 | +100.0 | 100.0% | inf | n/a to n/a |
| >=6% | 6 | 1 | 100.0% | +94.0 | +94.0 | 100.0% | inf | n/a to n/a |
| >=6% | 12 | 1 | 100.0% | +88.1 | +88.1 | 100.0% | inf | n/a to n/a |
| >=6% | 20 | 1 | 100.0% | +80.1 | +80.1 | 100.0% | inf | n/a to n/a |
| >=6% | 40 | 1 | 100.0% | +60.2 | +60.2 | 100.0% | inf | n/a to n/a |

On discovery data 1 of the 28 body-size and X combinations is above zero after 12 bps: body >=6% at X = 3%, +0.2 bps with a 95% interval of -53.1 to +53.5. The under-1% bucket is the worst of the four at 6 of the 7 X values. The buckets on the confirmation slice hold too few trades to read.

## Borrow sensitivity

Jupiter's perps API reported a SOL short borrow rate of 0.0007% per hour at 60.30% utilisation when the data was fetched (2026-11-18 21:01 UTC), and an open fee of 0.06%. Charged for the full 8 hours that is **0.56 bps** per trade. A stress case charges 0.01% per hour, 8 bps per 8 hours. Both are added on top of 12 bps. The flipped long is charged the long rate (0.0015% per hour). Price impact fees are not modelled.

| Sample | X | Green, 12 bps (bps) | Green, 12 bps + 0.56 borrow | 95% interval (bps) | Profit factor | Green, 12 bps + 8 borrow | Red, 12 bps + 0.56 borrow |
|---|---:|---:|---:|---:|---:|---:|---:|
| Discovery | 0.3% | -14.9 | -15.5 | -20.2 to -10.9 | 0.50 | -22.9 | -9.7 |
| Discovery | 0.5% | -14.3 | -14.9 | -20.6 to -9.1 | 0.68 | -22.3 | -7.1 |
| Discovery | 0.8% | -10.7 | -11.3 | -17.9 to -4.7 | 0.82 | -18.7 | -6.8 |
| Discovery | 1% | -10.0 | -10.6 | -17.7 to -3.5 | 0.85 | -18.0 | -7.6 |
| Discovery | 1.5% | -12.9 | -13.5 | -22.0 to -5.0 | 0.85 | -20.9 | -6.4 |
| Discovery | 2% | -14.6 | -15.2 | -24.5 to -5.9 | 0.85 | -22.6 | -5.4 |
| Discovery | 3% | -13.8 | -14.4 | -24.6 to -4.2 | 0.87 | -21.8 | -7.2 |
| Confirmation | 0.3% | -2.4 | -2.9 | -15.0 to +9.1 | 0.84 | -10.4 | -10.3 |
| Confirmation | 0.5% | -1.8 | -2.3 | -18.5 to +13.8 | 0.93 | -9.8 | -19.6 |
| Confirmation | 0.8% | -6.1 | -6.7 | -27.2 to +13.8 | 0.86 | -14.1 | -17.8 |
| Confirmation | 1% | -0.6 | -1.2 | -23.1 to +20.8 | 0.98 | -8.6 | -18.9 |
| Confirmation | 1.5% | +7.2 | +6.6 | -17.5 to +30.8 | 1.12 | -0.8 | -22.7 |
| Confirmation | 2% | +10.9 | +10.4 | -16.0 to +36.8 | 1.18 | +2.9 | -15.0 |
| Confirmation | 3% | +15.1 | +14.6 | -14.0 to +43.1 | 1.24 | +7.1 | -16.2 |

## Do the venues agree on the lows?

The take-profit depends on N's low, so a wick on one venue can fill a trade that another venue would not.

| Venue vs Binance | Shared 8h bars | Median low gap (bps) | 90th pct (bps) | 99th pct (bps) | Largest (bps) | Bars over 10 bps apart | Last 365d: median (bps) | Last 365d: 99th pct (bps) | Last 365d: over 10 bps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| OKX | 6,720 | 2.2 | 15.0 | 94 | 7873 | 14.0% | 1.2 | 11.9 | 1.7% |
| KuCoin | 5,797 | 1.9 | 9.0 | 53 | 2478 | 8.5% | 1.3 | 10.8 | 1.1% |

The venues disagreed often in the early data and agree closely now: OKX and Binance lows were more than 30 bps apart on 49.1% of 2020 candles, 9.5% in 2021 and 0.1% in 2026. The largest gap is 79% on the candle that opened 2020-10-28 16:00 UTC, and single-venue wicks still appear in crashes (14% on 2025-10-10 16:00 UTC). Does it change which trades fill? Signals that are green on both venues:

| Other venue | Sample | X | Shared green signals | TP hit on Binance | TP hit on other venue | Venues disagree | Binance only | Other venue only |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OKX | Discovery | 0.3% | 3194 | 90.0% | 89.4% | 1.31% | 1.00% | 0.31% |
| OKX | Discovery | 0.5% | 3194 | 83.8% | 83.1% | 1.38% | 1.03% | 0.34% |
| OKX | Discovery | 0.8% | 3194 | 74.3% | 73.8% | 1.19% | 0.85% | 0.34% |
| OKX | Discovery | 1% | 3194 | 67.9% | 67.1% | 1.19% | 0.97% | 0.22% |
| OKX | Discovery | 1.5% | 3194 | 53.4% | 52.7% | 1.13% | 0.91% | 0.22% |
| OKX | Discovery | 2% | 3194 | 41.9% | 41.5% | 1.16% | 0.75% | 0.41% |
| OKX | Discovery | 3% | 3194 | 26.3% | 25.8% | 1.03% | 0.78% | 0.25% |
| OKX | Confirmation | 0.3% | 137 | 88.3% | 87.6% | 2.19% | 1.46% | 0.73% |
| OKX | Confirmation | 0.5% | 137 | 78.1% | 78.1% | 0.00% | 0.00% | 0.00% |
| OKX | Confirmation | 0.8% | 137 | 62.0% | 62.8% | 0.73% | 0.00% | 0.73% |
| OKX | Confirmation | 1% | 137 | 55.5% | 55.5% | 0.00% | 0.00% | 0.00% |
| OKX | Confirmation | 1.5% | 137 | 36.5% | 36.5% | 0.00% | 0.00% | 0.00% |
| OKX | Confirmation | 2% | 137 | 26.3% | 26.3% | 0.00% | 0.00% | 0.00% |
| OKX | Confirmation | 3% | 137 | 12.4% | 12.4% | 0.00% | 0.00% | 0.00% |
| KuCoin | Discovery | 0.3% | 2754 | 89.5% | 89.0% | 0.91% | 0.73% | 0.18% |
| KuCoin | Discovery | 0.5% | 2754 | 82.8% | 82.1% | 1.27% | 0.98% | 0.29% |
| KuCoin | Discovery | 0.8% | 2754 | 72.6% | 72.3% | 1.05% | 0.69% | 0.36% |
| KuCoin | Discovery | 1% | 2754 | 65.8% | 65.1% | 1.60% | 1.16% | 0.44% |
| KuCoin | Discovery | 1.5% | 2754 | 50.2% | 49.9% | 0.98% | 0.62% | 0.36% |
| KuCoin | Discovery | 2% | 2754 | 38.2% | 37.9% | 0.87% | 0.58% | 0.29% |
| KuCoin | Discovery | 3% | 2754 | 22.1% | 21.8% | 0.76% | 0.54% | 0.22% |
| KuCoin | Confirmation | 0.3% | 139 | 88.5% | 87.1% | 1.44% | 1.44% | 0.00% |
| KuCoin | Confirmation | 0.5% | 139 | 78.4% | 77.7% | 0.72% | 0.72% | 0.00% |
| KuCoin | Confirmation | 0.8% | 139 | 62.6% | 62.6% | 0.00% | 0.00% | 0.00% |
| KuCoin | Confirmation | 1% | 139 | 56.1% | 56.1% | 1.44% | 0.72% | 0.72% |
| KuCoin | Confirmation | 1.5% | 139 | 37.4% | 36.7% | 0.72% | 0.72% | 0.00% |
| KuCoin | Confirmation | 2% | 139 | 27.3% | 27.3% | 0.00% | 0.00% | 0.00% |
| KuCoin | Confirmation | 3% | 139 | 12.9% | 12.9% | 0.00% | 0.00% | 0.00% |

On discovery data Binance fills slightly more often than the other venue at every X, so Binance lows flatter the trade a little. The same rule run end to end on each venue's own candles, mean per trade after 12 bps, entry at C's close:

| Sample | Venue | Strategy | Signals | X = 0.3% | X = 0.5% | X = 0.8% | X = 1% | X = 1.5% | X = 2% | X = 3% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Discovery | Binance | Green short (the idea) | 3286 | -14.9 | -14.3 | -10.7 | -10.0 | -12.9 | -14.6 | -13.8 |
| Discovery | Binance | Red short | 3289 | -9.1 | -6.6 | -6.3 | -7.0 | -5.8 | -4.9 | -6.6 |
| Discovery | OKX | Green short (the idea) | 3213 | -18.3 | -16.6 | -12.6 | -13.0 | -14.2 | -16.0 | -16.8 |
| Discovery | OKX | Red short | 3222 | -9.7 | -8.1 | -8.3 | -9.4 | -8.1 | -7.9 | -8.6 |
| Discovery | KuCoin | Green short (the idea) | 2775 | -14.5 | -14.1 | -10.3 | -10.2 | -11.0 | -13.6 | -16.2 |
| Discovery | KuCoin | Red short | 2748 | -11.4 | -9.4 | -10.8 | -9.5 | -8.5 | -7.2 | -5.8 |
| Confirmation | Binance | Green short (the idea) | 139 | -2.4 | -1.8 | -6.1 | -0.6 | +7.2 | +10.9 | +15.1 |
| Confirmation | Binance | Red short | 131 | -9.7 | -19.1 | -17.2 | -18.3 | -22.1 | -14.4 | -15.6 |
| Confirmation | OKX | Green short (the idea) | 137 | -3.7 | -2.5 | -6.5 | -2.0 | +5.1 | +8.2 | +11.5 |
| Confirmation | OKX | Red short | 131 | -9.7 | -19.0 | -15.7 | -18.2 | -21.9 | -14.3 | -15.4 |
| Confirmation | KuCoin | Green short (the idea) | 139 | -3.2 | -2.6 | -6.2 | +1.6 | +6.0 | +10.8 | +15.0 |
| Confirmation | KuCoin | Red short | 130 | -11.9 | -20.3 | -16.2 | -19.4 | -22.0 | -14.4 | -15.6 |
| Last 365d | Binance | Green short (the idea) | 535 | -5.6 | -4.9 | -5.0 | -5.2 | -5.3 | -2.5 | -2.2 |
| Last 365d | Binance | Red short | 558 | -12.2 | -11.4 | -10.0 | -10.6 | -12.0 | -6.3 | -4.9 |
| Last 365d | OKX | Green short (the idea) | 534 | -6.2 | -5.5 | -5.0 | -4.0 | -5.4 | -2.3 | -2.4 |
| Last 365d | OKX | Red short | 557 | -12.9 | -11.8 | -9.4 | -10.8 | -11.1 | -5.6 | -4.2 |
| Last 365d | KuCoin | Green short (the idea) | 536 | -8.0 | -7.3 | -4.6 | -3.2 | -4.8 | -1.9 | -1.8 |
| Last 365d | KuCoin | Red short | 557 | -13.9 | -12.4 | -11.6 | -11.9 | -12.1 | -6.7 | -4.7 |

OKX starts in September 2020 and KuCoin in August 2021, so their discovery samples are shorter than Binance's. No venue turns the discovery result positive at any X.

## How far price rose against the short before exit, X = 1%

From Binance 1m candles. Adverse move = highest price reached before the exit, relative to entry. For a take-profit fill the high of the fill minute is included, which can only overstate it. Leaving that minute out changes neither the median nor the 90th percentile at the precision shown.

| Entry | Sample | Subset | Trades | Median adverse move | 90th percentile | 99th percentile | Worst | Median minutes held | Share of all clock time in a position |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| C close | Discovery | All | 3286 | 0.87% | 4.15% | 10.15% | 35.3% | 185 | 24.7% |
| C close | Discovery | Take-profit hit | 2241 | 0.53% | 1.98% | 5.15% | 14.9% | 75 |  |
| C close | Discovery | Expired | 1045 | 2.58% | 7.02% | 14.48% | 35.3% | 480 |  |
| C close | Confirmation | All | 139 | 0.74% | 2.81% | 5.98% | 9.6% | 398 | 34.1% |
| C close | Confirmation | Take-profit hit | 78 | 0.38% | 1.20% | 5.00% | 9.6% | 158 |  |
| C close | Confirmation | Expired | 61 | 1.26% | 4.15% | 5.81% | 6.3% | 480 |  |
| C close | Full history | All | 3425 | 0.86% | 4.10% | 10.13% | 35.3% | 189 | 25.0% |
| C close | Full history | Take-profit hit | 2319 | 0.52% | 1.95% | 5.20% | 14.9% | 77 |  |
| C close | Full history | Expired | 1106 | 2.46% | 6.91% | 14.22% | 35.3% | 480 |  |
| N open | Discovery | All | 3286 | 0.86% | 4.12% | 10.14% | 35.3% | 185 | 24.6% |
| N open | Discovery | Take-profit hit | 2242 | 0.53% | 1.98% | 5.13% | 15.2% | 75 |  |
| N open | Discovery | Expired | 1044 | 2.57% | 7.03% | 14.41% | 35.3% | 480 |  |
| N open | Confirmation | All | 139 | 0.74% | 2.81% | 5.98% | 9.6% | 398 | 34.2% |
| N open | Confirmation | Take-profit hit | 78 | 0.38% | 1.20% | 4.99% | 9.6% | 158 |  |
| N open | Confirmation | Expired | 61 | 1.26% | 4.14% | 5.81% | 6.3% | 480 |  |
| N open | Full history | All | 3425 | 0.86% | 4.06% | 10.13% | 35.3% | 189 | 25.0% |
| N open | Full history | Take-profit hit | 2320 | 0.52% | 1.94% | 5.18% | 15.2% | 77 |  |
| N open | Full history | Expired | 1105 | 2.46% | 6.93% | 14.21% | 35.3% | 480 |  |

To collect 1%, the median discovery trade sat through a 0.87% rise and one trade in ten sat through 4.15% or more. The trades that never filled were carried a median 2.58% against, with no stop, and the worst was 35.3% in one candle.

## The last 30 green-candle shorts

Times are America/Phoenix (UTC-7). X = 1%. Binance spot. Newest first.

| Signal candle open | Entry time (C close) | Entry | X | Take-profit | Result | Exit price | Return after 12 bps | N open | Return if entered at N open |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-17 17:00 | 2026-11-18 01:00 | 75.19 | 1% | 74.4381 | take-profit hit | 74.4381 | +0.88% | 75.18 | +0.88% |
| 2026-11-17 09:00 | 2026-11-17 17:00 | 75.19 | 1% | 74.4381 | take-profit hit | 74.4381 | +0.88% | 75.18 | +0.88% |
| 2026-11-16 17:00 | 2026-11-17 01:00 | 72.96 | 1% | 72.2304 | take-profit hit | 72.2304 | +0.88% | 72.96 | +0.88% |
| 2026-11-16 09:00 | 2026-11-16 17:00 | 71.58 | 1% | 70.8642 | expired | 72.9600 | -2.05% | 71.58 | -2.05% |
| 2026-11-15 09:00 | 2026-11-15 17:00 | 72.77 | 1% | 72.0423 | take-profit hit | 72.0423 | +0.88% | 72.77 | +0.88% |
| 2026-11-15 01:00 | 2026-11-15 09:00 | 71.24 | 1% | 70.5276 | expired | 72.7700 | -2.27% | 71.24 | -2.27% |
| 2026-11-13 01:00 | 2026-11-13 09:00 | 80.03 | 1% | 79.2297 | take-profit hit | 79.2297 | +0.88% | 80.03 | +0.88% |
| 2026-11-12 09:00 | 2026-11-12 17:00 | 81.72 | 1% | 80.9028 | take-profit hit | 80.9028 | +0.88% | 81.72 | +0.88% |
| 2026-11-11 01:00 | 2026-11-11 09:00 | 84.85 | 1% | 84.0015 | take-profit hit | 84.0015 | +0.88% | 84.84 | +0.88% |
| 2026-11-10 17:00 | 2026-11-11 01:00 | 83.37 | 1% | 82.5363 | expired | 84.8500 | -1.90% | 83.37 | -1.90% |
| 2026-11-10 09:00 | 2026-11-10 17:00 | 83.35 | 1% | 82.5165 | take-profit hit | 82.5165 | +0.88% | 83.35 | +0.88% |
| 2026-11-09 01:00 | 2026-11-09 09:00 | 87.94 | 1% | 87.0606 | take-profit hit | 87.0606 | +0.88% | 87.94 | +0.88% |
| 2026-11-08 01:00 | 2026-11-08 09:00 | 89.71 | 1% | 88.8129 | take-profit hit | 88.8129 | +0.88% | 89.72 | +0.88% |
| 2026-11-07 09:00 | 2026-11-07 17:00 | 89.81 | 1% | 88.9119 | take-profit hit | 88.9119 | +0.88% | 89.82 | +0.88% |
| 2026-11-06 17:00 | 2026-11-07 01:00 | 90.23 | 1% | 89.3277 | take-profit hit | 89.3277 | +0.88% | 90.22 | +0.88% |
| 2026-11-06 01:00 | 2026-11-06 09:00 | 90.75 | 1% | 89.8425 | take-profit hit | 89.8425 | +0.88% | 90.74 | +0.88% |
| 2026-11-05 17:00 | 2026-11-06 01:00 | 89.68 | 1% | 88.7832 | expired | 90.7500 | -1.31% | 89.68 | -1.31% |
| 2026-11-04 17:00 | 2026-11-05 01:00 | 95.90 | 1% | 94.9410 | take-profit hit | 94.9410 | +0.88% | 95.90 | +0.88% |
| 2026-11-04 01:00 | 2026-11-04 09:00 | 96.70 | 1% | 95.7330 | take-profit hit | 95.7330 | +0.88% | 96.71 | +0.88% |
| 2026-11-03 17:00 | 2026-11-04 01:00 | 93.05 | 1% | 92.1195 | expired | 96.7000 | -4.04% | 93.05 | -4.04% |
| 2026-11-03 01:00 | 2026-11-03 09:00 | 93.75 | 1% | 92.8125 | take-profit hit | 92.8125 | +0.88% | 93.75 | +0.88% |
| 2026-11-02 17:00 | 2026-11-03 01:00 | 92.11 | 1% | 91.1889 | expired | 93.7500 | -1.90% | 92.10 | -1.91% |
| 2026-10-31 17:00 | 2026-11-01 01:00 | 95.60 | 1% | 94.6440 | take-profit hit | 94.6440 | +0.88% | 95.61 | +0.88% |
| 2026-10-31 01:00 | 2026-10-31 09:00 | 95.98 | 1% | 95.0202 | expired | 95.5400 | +0.34% | 95.99 | +0.35% |
| 2026-10-30 09:00 | 2026-10-30 17:00 | 96.38 | 1% | 95.4162 | expired | 95.6400 | +0.65% | 96.38 | +0.65% |
| 2026-10-29 17:00 | 2026-10-30 01:00 | 97.35 | 1% | 96.3765 | take-profit hit | 96.3765 | +0.88% | 97.35 | +0.88% |
| 2026-10-29 01:00 | 2026-10-29 09:00 | 102.70 | 1% | 101.6730 | take-profit hit | 101.6730 | +0.88% | 102.70 | +0.88% |
| 2026-10-28 09:00 | 2026-10-28 17:00 | 102.44 | 1% | 101.4156 | take-profit hit | 101.4156 | +0.88% | 102.44 | +0.88% |
| 2026-10-27 17:00 | 2026-10-28 01:00 | 102.33 | 1% | 101.3067 | take-profit hit | 101.3067 | +0.88% | 102.34 | +0.88% |
| 2026-10-27 09:00 | 2026-10-27 17:00 | 101.35 | 1% | 100.3365 | expired | 102.3300 | -1.09% | 101.34 | -1.10% |

Sum of the 30 returns after 12 bps: +4.92%. 21 hit the take-profit and 9 expired.

## Reproduce

```bash
pip install -r requirements.txt
python3 test_rules.py        # fill rule and cost arithmetic
python3 fetch_data.py        # only to refresh; data/ holds the frozen sample, cache/ the 1m bars
python3 check_data.py
python3 01_discovery.py      # discovery grid, locks X
python3 02_confirmation.py   # reads the last 90 days
python3 make_report.py
```

Full grids for every venue, entry, strategy, X, cost and period are in `results/grid_discovery.csv` and `results/grid_confirmation.csv`.
