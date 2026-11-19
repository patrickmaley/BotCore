"""JSON state for the open short and the trades it has closed."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .strategy import Position


@dataclass
class BotState:
    position: Position | None = None
    last_signal_open_ms: int | None = None
    realized_pnl_usd: float = 0.0
    trades: list[dict] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "position": None if self.position is None else asdict(self.position),
            "last_signal_open_ms": self.last_signal_open_ms,
            "realized_pnl_usd": self.realized_pnl_usd,
            "trades": self.trades[-200:],
        }

    @classmethod
    def from_json(cls, payload: dict) -> BotState:
        raw_position = payload.get("position")
        position = None if raw_position is None else Position(**raw_position)
        return cls(
            position=position,
            last_signal_open_ms=payload.get("last_signal_open_ms"),
            realized_pnl_usd=float(payload.get("realized_pnl_usd") or 0),
            trades=list(payload.get("trades") or []),
        )


def load_state(path: str) -> BotState:
    file_path = Path(path)
    if not file_path.exists():
        return BotState()
    return BotState.from_json(json.loads(file_path.read_text()))


def save_state(path: str, state: BotState) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state.to_json(), indent=2)
    descriptor, temporary_name = tempfile.mkstemp(dir=file_path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(payload)
        os.replace(temporary_name, file_path)
    except Exception:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
        raise
