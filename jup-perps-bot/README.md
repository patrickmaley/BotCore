# SOL 8-hour short on Jupiter Perps

The bot shorts SOL-PERP when an 8-hour candle closes green, then buys it back when price trades a set percentage below that entry. If the next 8-hour candle ends without that print, the bot covers at the close.

It talks to `https://perps-api.jup.ag/v1`. Reads use `/market-stats` and `/positions`. A live short is `POST /positions/increase` with `side: short`, signed locally, then `POST /transaction/execute`. The cover is `POST /positions/decrease` with `entirePosition: true`.

Paper mode is the default. It does not sign or send a transaction.

## Run on paper

```bash
cd jup-perps-bot
python3 -m jup_perps_bot status
python3 -m jup_perps_bot once --take-profit-pct 1 --collateral-usdc 10 --leverage 2
python3 -m jup_perps_bot replay --candles 300
python3 -m jup_perps_bot run
```

`once` acts on the latest closed 8-hour candle only if that close is still fresh (15 minutes by default) and the Jupiter mark is within 25 bps of it. A green candle from earlier in the day is ignored, so starting the bot does not fire a stale short.

State is written to `state.json` in the current directory. That file is gitignored.

## Go live

Live mode can lose the USDC you post as collateral. Jupiter charges about 6 bps to open and 6 bps to close, plus borrow and price impact. Leverage is capped at 5 unless you set `JUP_BOT_ALLOW_HIGH_LEVERAGE=1`. Collateral is capped at 250 USDC unless you raise `JUP_BOT_MAX_COLLATERAL_USDC`.

Install the signer, point at a Solana CLI keypair file, and set both locks:

```bash
python3 -m pip install -r requirements.txt
export JUP_BOT_LIVE=1
export JUP_BOT_WALLET=<pubkey>
export JUP_BOT_KEYPAIR=/absolute/path/to/keypair.json
python3 -m jup_perps_bot once --live --i-understand --collateral-usdc 10 --leverage 2 --take-profit-pct 1
```

The keypair file is the JSON array from `solana-keygen`. It is never written into the repo. The bot refuses to send if `JUP_BOT_WALLET` does not match that file, or if the wallet already has a SOL short.

A live entry uses Jupiter's quoted price, not a historical print. The unsigned transaction is thrown away when that quote is more than 25 bps from the green close.
