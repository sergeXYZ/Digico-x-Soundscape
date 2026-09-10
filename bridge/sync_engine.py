"""Bidirectional sync engine with multi-mapping, mute store and FG mute."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from bridge.constants import DB_MAX, DB_MIN, DS100_PREFIX, ECHO_THRESHOLD_DB
from bridge.mapping import Ds100ParamKind, MappingSpec


class Source(Enum):
    DIGICO = "digico"
    DS100 = "ds100"
    BRIDGE = "bridge"


@dataclass
class ChannelState:
    value: float | None = None
    aux_on: bool = True
    last_source: Source | None = None
    last_sent_at: float = 0.0


def clamp_db(value: float) -> float:
    return max(DB_MIN, min(DB_MAX, value))


def parse_digico_aux_level(address: str) -> tuple[int, int] | None:
    """Return (channel, aux) from Digico aux send level path."""
    patterns = [
        r"/Input_Channels/(\d+)/Aux_Send/(\d+)/send_level",
        r"/channel/(\d+)/send/(\d+)/level",
        r"/Input_Channels/(\d+)/send/(\d+)/level",
    ]
    for pattern in patterns:
        match = re.fullmatch(pattern, address, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def parse_digico_aux_on(address: str) -> tuple[int, int] | None:
    """Return (channel, aux) from Digico Aux Send On path."""
    patterns = [
        r"/Input_Channels/(\d+)/Aux_Send/(\d+)/send_on",
        r"/Input_Channels/(\d+)/Aux_Send/(\d+)/On",
        r"/channel/(\d+)/send/(\d+)/on",
    ]
    for pattern in patterns:
        match = re.fullmatch(pattern, address, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def parse_ds100_reverb_send_gain(address: str, prefix: str = DS100_PREFIX) -> int | None:
    path = f"{prefix}/matrixinput/reverbsendgain/"
    if not address.startswith(path):
        return None
    suffix = address[len(path) :]
    return int(suffix) if suffix.isdigit() else None


def parse_ds100_fg_routing_gain(
    address: str, prefix: str = DS100_PREFIX
) -> tuple[int, int] | None:
    """Return (function_group, sound_object) from soundobjectrouting/gain."""
    path = f"{prefix}/soundobjectrouting/gain/"
    if not address.startswith(path):
        return None
    parts = address[len(path) :].split("/")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    return int(parts[0]), int(parts[1])


def parse_ds100_fg_routing_mute(
    address: str, prefix: str = DS100_PREFIX
) -> tuple[int, int] | None:
    path = f"{prefix}/soundobjectrouting/mute/"
    if not address.startswith(path):
        return None
    parts = address[len(path) :].split("/")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    return int(parts[0]), int(parts[1])


def digico_aux_level_path(channel: int, aux_number: int) -> str:
    return f"/Input_Channels/{channel}/Aux_Send/{aux_number}/send_level"


def digico_aux_on_path(channel: int, aux_number: int) -> str:
    return f"/Input_Channels/{channel}/Aux_Send/{aux_number}/send_on"


def ds100_reverb_send_gain_path(channel: int, prefix: str = DS100_PREFIX) -> str:
    return f"{prefix}/matrixinput/reverbsendgain/{channel}"


def ds100_fg_routing_gain_path(
    function_group: int, channel: int, prefix: str = DS100_PREFIX
) -> str:
    return f"{prefix}/soundobjectrouting/gain/{function_group}/{channel}"


def ds100_fg_routing_mute_path(
    function_group: int, channel: int, prefix: str = DS100_PREFIX
) -> str:
    return f"{prefix}/soundobjectrouting/mute/{function_group}/{channel}"


def osc_truthy(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) >= 0.5
    return None


# Callbacks used by the sync engine
SendLevelCb = Callable[[MappingSpec, int, float], None]
SendMuteCb = Callable[[MappingSpec, int, bool], None]  # muted=True means DS100 muted


class SyncEngine:
    def __init__(
        self,
        start_channel: int,
        end_channel: int,
        mappings: list[MappingSpec],
        on_to_ds100_level: SendLevelCb,
        on_to_ds100_mute: SendMuteCb,
        on_to_digico_level: Callable[[int, int, float], None],  # channel, aux, value
        on_to_digico_on: Callable[[int, int, bool], None],  # channel, aux, is_on
        log: Callable[[str], None] | None = None,
        on_mapping_activity: Callable[[str], None] | None = None,
    ) -> None:
        if start_channel > end_channel:
            raise ValueError("start_channel must be <= end channel")
        if not mappings:
            raise ValueError("At least one mapping is required")

        self.start_channel = start_channel
        self.end_channel = end_channel
        self.mappings = list(mappings)
        self._on_to_ds100_level = on_to_ds100_level
        self._on_to_ds100_mute = on_to_ds100_mute
        self._on_to_digico_level = on_to_digico_level
        self._on_to_digico_on = on_to_digico_on
        self._log = log or (lambda _msg: None)
        self._on_mapping_activity = on_mapping_activity or (lambda _mid: None)
        self._lock = threading.Lock()
        # key: (mapping_id, channel)
        self._channels: dict[tuple[str, int], ChannelState] = {}

    def _in_range(self, channel: int) -> bool:
        return self.start_channel <= channel <= self.end_channel

    def _mappings_for_aux(self, aux: int) -> list[MappingSpec]:
        return [m for m in self.mappings if m.digico_aux == aux]

    def _mappings_enspace(self) -> list[MappingSpec]:
        return [m for m in self.mappings if m.ds100_kind == Ds100ParamKind.ENSPACE_SEND.value]

    def _mappings_fg(self, function_group: int) -> list[MappingSpec]:
        return [
            m
            for m in self.mappings
            if m.ds100_kind == Ds100ParamKind.FG_ROUTING.value
            and m.function_group == function_group
        ]

    def _get_state(self, mapping_id: str, channel: int) -> ChannelState:
        key = (mapping_id, channel)
        if key not in self._channels:
            self._channels[key] = ChannelState()
        return self._channels[key]

    def _is_echo(self, mapping_id: str, channel: int, value: float) -> bool:
        state = self._get_state(mapping_id, channel)
        if state.last_source != Source.BRIDGE:
            return False
        if state.value is None:
            return False
        if time.monotonic() - state.last_sent_at > 0.5:
            return False
        return abs(state.value - value) < ECHO_THRESHOLD_DB

    def handle_digico_level(self, channel: int, aux: int, raw_value: float) -> None:
        if not self._in_range(channel):
            return
        value = clamp_db(raw_value)
        for mapping in self._mappings_for_aux(aux):
            self._digico_level_for_mapping(mapping, channel, value)

    def _digico_level_for_mapping(
        self, mapping: MappingSpec, channel: int, value: float
    ) -> None:
        with self._lock:
            if self._is_echo(mapping.id, channel, value):
                return
            state = self._get_state(mapping.id, channel)
            if state.value is not None and abs(state.value - value) < ECHO_THRESHOLD_DB:
                if state.last_source == Source.DIGICO:
                    return
            state.value = value
            state.last_source = Source.DIGICO
            aux_on = state.aux_on

        if mapping.uses_mute_store() and not aux_on:
            self._log(
                f"[{mapping.label()}] ch{channel} level stored (Aux OFF): {value:.2f} dB"
            )
            return

        self._log(f"[{mapping.label()}] DiGiCo ch{channel} → DS100: {value:.2f} dB")
        self._on_mapping_activity(mapping.id)
        self._forward_to_ds100_level(mapping, channel, value)

    def handle_digico_aux_on(self, channel: int, aux: int, is_on: bool) -> None:
        if not self._in_range(channel):
            return
        for mapping in self._mappings_for_aux(aux):
            self._digico_on_for_mapping(mapping, channel, is_on)

    def _digico_on_for_mapping(
        self, mapping: MappingSpec, channel: int, is_on: bool
    ) -> None:
        with self._lock:
            state = self._get_state(mapping.id, channel)
            if state.aux_on == is_on:
                return
            state.aux_on = is_on
            stored = state.value

        if mapping.uses_mute_store():
            if not is_on:
                self._log(
                    f"[{mapping.label()}] ch{channel} Aux OFF → DS100: {DB_MIN:.1f} dB"
                )
                self._on_mapping_activity(mapping.id)
                self._forward_to_ds100_level(
                    mapping, channel, DB_MIN, update_logical_value=False
                )
                return
            if stored is None:
                self._log(f"[{mapping.label()}] ch{channel} Aux ON — no stored level")
                return
            self._log(
                f"[{mapping.label()}] ch{channel} Aux ON → restore: {stored:.2f} dB"
            )
            self._on_mapping_activity(mapping.id)
            self._forward_to_ds100_level(mapping, channel, stored)
            return

        # Function Group: Aux On = Mute Off
        muted = not is_on
        self._log(
            f"[{mapping.label()}] ch{channel} Aux {'ON' if is_on else 'OFF'} "
            f"→ DS100 mute={'1' if muted else '0'}"
        )
        self._on_mapping_activity(mapping.id)
        self._on_to_ds100_mute(mapping, channel, muted)

    def handle_ds100_enspace_gain(self, channel: int, raw_value: float) -> None:
        if not self._in_range(channel):
            return
        value = clamp_db(raw_value)
        for mapping in self._mappings_enspace():
            self._ds100_level_for_mapping(mapping, channel, value)

    def handle_ds100_fg_gain(
        self, function_group: int, channel: int, raw_value: float
    ) -> None:
        if not self._in_range(channel):
            return
        value = clamp_db(raw_value)
        for mapping in self._mappings_fg(function_group):
            self._ds100_level_for_mapping(mapping, channel, value)

    def handle_ds100_fg_mute(
        self, function_group: int, channel: int, muted: bool
    ) -> None:
        if not self._in_range(channel):
            return
        is_on = not muted
        for mapping in self._mappings_fg(function_group):
            with self._lock:
                state = self._get_state(mapping.id, channel)
                if state.aux_on == is_on:
                    continue
                state.aux_on = is_on
            self._log(
                f"[{mapping.label()}] DS100 mute={'1' if muted else '0'} "
                f"→ DiGiCo Aux {'ON' if is_on else 'OFF'} ch{channel}"
            )
            self._on_mapping_activity(mapping.id)
            self._on_to_digico_on(channel, mapping.digico_aux, is_on)

    def _ds100_level_for_mapping(
        self, mapping: MappingSpec, channel: int, value: float
    ) -> None:
        with self._lock:
            state = self._get_state(mapping.id, channel)
            aux_on = state.aux_on

            if mapping.uses_mute_store() and not aux_on:
                if abs(value - DB_MIN) < ECHO_THRESHOLD_DB:
                    return

            if self._is_echo(mapping.id, channel, value):
                return

            if state.value is not None and abs(state.value - value) < ECHO_THRESHOLD_DB:
                if state.last_source == Source.DS100:
                    return

            state.value = value
            state.last_source = Source.DS100

        self._log(f"[{mapping.label()}] DS100 ch{channel} → DiGiCo: {value:.2f} dB")
        self._on_mapping_activity(mapping.id)
        self._on_to_digico_level(channel, mapping.digico_aux, value)

        if mapping.uses_mute_store() and not aux_on:
            self._forward_to_ds100_level(
                mapping, channel, DB_MIN, update_logical_value=False
            )

    def _forward_to_ds100_level(
        self,
        mapping: MappingSpec,
        channel: int,
        value: float,
        *,
        update_logical_value: bool = True,
    ) -> None:
        with self._lock:
            state = self._get_state(mapping.id, channel)
            if update_logical_value:
                state.value = value
            state.last_source = Source.BRIDGE
            state.last_sent_at = time.monotonic()
        self._on_to_ds100_level(mapping, channel, value)
