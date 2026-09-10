"""Persist GUI settings to a local JSON file."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from bridge.constants import (
    DS100_POLL_INTERVAL_MAX_MS,
    DS100_POLL_INTERVAL_MIN_MS,
    DS100_POLL_INTERVAL_MS,
)
from bridge.mapping import (
    MappingSpec,
    default_mappings,
    mapping_from_dict,
    mappings_to_dicts,
)


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


SETTINGS_PATH = _app_dir() / "settings.json"


def clamp_poll_interval_ms(value: int) -> int:
    return max(DS100_POLL_INTERVAL_MIN_MS, min(DS100_POLL_INTERVAL_MAX_MS, int(value)))


@dataclass
class BridgeSettings:
    start_channel: int = 1
    end_channel: int = 64
    digico_host: str = "192.168.1.10"
    digico_send_port: int = 9000
    digico_listen_port: int = 8000
    ds100_host: str = "192.168.1.20"
    ds100_poll_interval_ms: int = DS100_POLL_INTERVAL_MS
    mappings: list[MappingSpec] = field(default_factory=default_mappings)


def load_settings() -> BridgeSettings:
    if not SETTINGS_PATH.exists():
        return BridgeSettings()

    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        mappings_raw = data.get("mappings")
        if isinstance(mappings_raw, list) and mappings_raw:
            mappings = [mapping_from_dict(m) for m in mappings_raw]
        else:
            mappings = default_mappings()

        return BridgeSettings(
            start_channel=int(data.get("start_channel", 1)),
            end_channel=int(data.get("end_channel", 64)),
            digico_host=str(data.get("digico_host", "192.168.1.10")),
            digico_send_port=int(data.get("digico_send_port", 9000)),
            digico_listen_port=int(data.get("digico_listen_port", 8000)),
            ds100_host=str(data.get("ds100_host", "192.168.1.20")),
            ds100_poll_interval_ms=clamp_poll_interval_ms(
                int(data.get("ds100_poll_interval_ms", DS100_POLL_INTERVAL_MS))
            ),
            mappings=mappings,
        )
    except (json.JSONDecodeError, TypeError, ValueError, KeyError):
        return BridgeSettings()


def save_settings(settings: BridgeSettings) -> None:
    payload: dict[str, Any] = asdict(settings)
    payload["mappings"] = mappings_to_dicts(settings.mappings)
    SETTINGS_PATH.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
