"""Jupiter Perpetuals REST client.

Trading routes return an unsigned-or-partially-signed transaction. This client
does not sign or send one unless the caller asks it to execute.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .config import SOL_MINT, USDC_DECIMALS


class PerpsError(RuntimeError):
    def __init__(self, status: int, body: Any):
        self.status = status
        self.body = body
        message = body.get("message") if isinstance(body, dict) else body
        super().__init__(f"Jupiter perps HTTP {status}: {message}")


def parse_usd(value: str | float | int) -> float:
    """Accept a decimal string or a 1e6-scaled integer string."""
    text = str(value)
    if "." in text:
        return float(text)
    return int(text) / 1_000_000


class PerpsClient:
    def __init__(self, base_url: str, timeout: float = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, *, query: dict | None = None, body: dict | None = None) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            pairs = "&".join(f"{key}={value}" for key, value in query.items() if value is not None)
            url = f"{url}?{pairs}"
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "jup-perps-bot",
                "x-perps-api-version": "v2",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                parsed = json.loads(raw.decode() or "null")
            except json.JSONDecodeError:
                parsed = raw.decode(errors="replace")
            raise PerpsError(exc.code, parsed) from exc
        if not raw:
            return None
        return json.loads(raw.decode())

    def mark_price(self) -> float:
        payload = self._request("GET", "/market-stats", query={"mint": SOL_MINT})
        return parse_usd(payload["price"])

    def positions(self, wallet_address: str) -> list[dict]:
        payload = self._request(
            "GET",
            "/positions",
            query={"walletAddress": wallet_address, "includeClosedPositions": "false"},
        )
        return list(payload.get("dataList") or [])

    def sol_short(self, wallet_address: str) -> dict | None:
        shorts = [
            position
            for position in self.positions(wallet_address)
            if position.get("asset") == "SOL" and position.get("side") == "short"
        ]
        return shorts[0] if shorts else None

    def build_short(
        self,
        *,
        wallet_address: str,
        collateral_usdc: float,
        leverage: float,
        slippage_bps: int,
    ) -> dict:
        amount = str(int(round(collateral_usdc * 10**USDC_DECIMALS)))
        return self._request(
            "POST",
            "/positions/increase",
            body={
                "walletAddress": wallet_address,
                "asset": "SOL",
                "inputToken": "USDC",
                "inputTokenAmount": amount,
                "side": "short",
                "leverage": f"{leverage:.1f}",
                "maxSlippageBps": str(slippage_bps),
            },
        )

    def build_close(self, position_pubkey: str, slippage_bps: int) -> dict:
        return self._request(
            "POST",
            "/positions/decrease",
            body={
                "positionPubkey": position_pubkey,
                "receiveToken": "USDC",
                "entirePosition": True,
                "maxSlippageBps": str(slippage_bps),
            },
        )

    def execute(self, action: str, serialized_tx_base64: str) -> str:
        payload = self._request(
            "POST",
            "/transaction/execute",
            body={"action": action, "serializedTxBase64": serialized_tx_base64},
        )
        txid = payload.get("txid") or payload.get("signature")
        if not txid:
            raise PerpsError(200, payload)
        return str(txid)
