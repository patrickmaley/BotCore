"""Runtime settings. Live trading stays off unless every lock is set."""

from __future__ import annotations

import os
from dataclasses import dataclass


EIGHT_H_MS = 8 * 60 * 60 * 1000
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_DECIMALS = 6
DEFAULT_PERPS_URL = "https://perps-api.jup.ag/v1"
DEFAULT_CANDLE_URL = "https://api.mexc.com/api/v3/klines"


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    take_profit_pct: float = 1.0
    collateral_usdc: float = 10.0
    leverage: float = 2.0
    open_fee_bps: float = 6.0
    close_fee_bps: float = 6.0
    max_entry_drift_bps: float = 25.0
    max_signal_age_ms: int = 15 * 60 * 1000
    poll_seconds: float = 30.0
    slippage_bps: int = 100
    max_collateral_usdc: float = 250.0
    allow_high_leverage: bool = False
    state_path: str = "state.json"
    perps_url: str = DEFAULT_PERPS_URL
    candle_url: str = DEFAULT_CANDLE_URL
    wallet_address: str | None = None
    keypair_path: str | None = None
    live: bool = False

    @property
    def notional_usd(self) -> float:
        return self.collateral_usdc * self.leverage

    @property
    def round_trip_fee_bps(self) -> float:
        return self.open_fee_bps + self.close_fee_bps


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def build_config(
    *,
    live: bool = False,
    i_understand: bool = False,
    take_profit_pct: float | None = None,
    collateral_usdc: float | None = None,
    leverage: float | None = None,
    state_path: str | None = None,
    wallet_address: str | None = None,
    keypair_path: str | None = None,
) -> Config:
    """Build a config and refuse an accidental live launch."""
    cfg = Config(
        take_profit_pct=take_profit_pct
        if take_profit_pct is not None
        else _env_float("JUP_BOT_TAKE_PROFIT_PCT", 1.0),
        collateral_usdc=collateral_usdc
        if collateral_usdc is not None
        else _env_float("JUP_BOT_COLLATERAL_USDC", 10.0),
        leverage=leverage if leverage is not None else _env_float("JUP_BOT_LEVERAGE", 2.0),
        open_fee_bps=_env_float("JUP_BOT_OPEN_FEE_BPS", 6.0),
        close_fee_bps=_env_float("JUP_BOT_CLOSE_FEE_BPS", 6.0),
        max_entry_drift_bps=_env_float("JUP_BOT_MAX_ENTRY_DRIFT_BPS", 25.0),
        max_signal_age_ms=int(_env_float("JUP_BOT_MAX_SIGNAL_AGE_SEC", 15 * 60) * 1000),
        poll_seconds=_env_float("JUP_BOT_POLL_SEC", 30.0),
        slippage_bps=int(_env_float("JUP_BOT_SLIPPAGE_BPS", 100)),
        max_collateral_usdc=_env_float("JUP_BOT_MAX_COLLATERAL_USDC", 250.0),
        allow_high_leverage=_env_flag("JUP_BOT_ALLOW_HIGH_LEVERAGE"),
        state_path=state_path or os.environ.get("JUP_BOT_STATE", "state.json"),
        perps_url=os.environ.get("JUP_BOT_PERPS_URL", DEFAULT_PERPS_URL),
        candle_url=os.environ.get("JUP_BOT_CANDLE_URL", DEFAULT_CANDLE_URL),
        wallet_address=wallet_address or os.environ.get("JUP_BOT_WALLET") or None,
        keypair_path=keypair_path or os.environ.get("JUP_BOT_KEYPAIR") or None,
        live=live,
    )
    _validate(cfg, i_understand=i_understand)
    return cfg


def _validate(cfg: Config, *, i_understand: bool) -> None:
    if not 0 < cfg.take_profit_pct <= 20:
        raise ConfigError("take-profit percent must be between 0 and 20")
    if cfg.collateral_usdc <= 0:
        raise ConfigError("collateral must be positive")
    if cfg.collateral_usdc > cfg.max_collateral_usdc:
        raise ConfigError(
            f"collateral {cfg.collateral_usdc} USDC exceeds the cap of "
            f"{cfg.max_collateral_usdc}. Raise JUP_BOT_MAX_COLLATERAL_USDC to override."
        )
    if cfg.leverage < 1.1:
        raise ConfigError("Jupiter perps minimum leverage is 1.1")
    if cfg.leverage > 5 and not cfg.allow_high_leverage:
        raise ConfigError(
            "leverage is capped at 5. Set JUP_BOT_ALLOW_HIGH_LEVERAGE=1 to raise it."
        )
    if cfg.leverage > 250:
        raise ConfigError("leverage above 250 is rejected")
    if cfg.max_entry_drift_bps < 0:
        raise ConfigError("entry drift cap cannot be negative")
    if cfg.poll_seconds <= 0:
        raise ConfigError("poll interval must be positive")
    if cfg.live:
        if not _env_flag("JUP_BOT_LIVE"):
            raise ConfigError("live trading also requires JUP_BOT_LIVE=1")
        if not i_understand:
            raise ConfigError("live trading requires --i-understand")
        if not cfg.wallet_address:
            raise ConfigError("live trading requires JUP_BOT_WALLET")
        if not cfg.keypair_path:
            raise ConfigError("live trading requires JUP_BOT_KEYPAIR pointing at a keypair file")
