"""Orchestrates DiGiCo and DS100 OSC clients with the sync engine."""

from __future__ import annotations

import threading
from typing import Callable

from bridge.connection_monitor import ConnectionMonitor, run_connection_test
from bridge.constants import DS100_LISTEN_PORT, DS100_SEND_PORT
from bridge.digico_client import DigicoClient
from bridge.ds100_client import DS100Client
from bridge.mapping import Ds100ParamKind, MappingSpec
from bridge.net_utils import get_local_ip
from bridge.osc_utils import require_udp_port
from bridge.settings import BridgeSettings
from bridge.sync_engine import SyncEngine


class BridgeApp:
    def __init__(
        self,
        settings: BridgeSettings,
        log: Callable[[str], None],
        on_activity: Callable[[str], None] | None = None,
    ) -> None:
        self.settings = settings
        self._log = log
        self._external_activity = on_activity or (lambda _key: None)
        self._monitor = ConnectionMonitor()
        self._digico: DigicoClient | None = None
        self._ds100: DS100Client | None = None
        self._engine: SyncEngine | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def connection_monitor(self) -> ConnectionMonitor:
        return self._monitor

    def connection_status(self) -> dict[str, bool]:
        return self._monitor.status()

    def _on_activity(self, key: str) -> None:
        self._monitor.note_activity(key)
        self._external_activity(key)

    def _on_mapping_activity(self, mapping_id: str) -> None:
        self._external_activity(f"map:{mapping_id}")

    def _aux_numbers(self) -> list[int]:
        return sorted({m.digico_aux for m in self.settings.mappings})

    def start(self) -> None:
        if self._running:
            return

        if self.settings.start_channel > self.settings.end_channel:
            raise ValueError("Start channel must be <= end channel")
        if not self.settings.mappings:
            raise ValueError("Add at least one mapping")

        for mapping in self.settings.mappings:
            mapping.validate()

        self._monitor.reset()

        self._ds100 = DS100Client(
            host=self.settings.ds100_host,
            on_enspace_gain=self._on_ds100_enspace,
            on_fg_gain=self._on_ds100_fg_gain,
            on_fg_mute=self._on_ds100_fg_mute,
            on_activity=self._on_activity,
            log=self._log,
        )
        self._digico = DigicoClient(
            host=self.settings.digico_host,
            send_port=self.settings.digico_send_port,
            listen_port=self.settings.digico_listen_port,
            on_aux_level=self._on_digico_level,
            on_aux_on=self._on_digico_aux_on,
            on_activity=self._on_activity,
            log=self._log,
        )

        self._engine = SyncEngine(
            start_channel=self.settings.start_channel,
            end_channel=self.settings.end_channel,
            mappings=self.settings.mappings,
            on_to_ds100_level=self._send_ds100_level,
            on_to_ds100_mute=self._send_ds100_mute,
            on_to_digico_level=self._send_digico_level,
            on_to_digico_on=self._send_digico_on,
            log=self._log,
            on_mapping_activity=self._on_mapping_activity,
        )

        require_udp_port(DS100_LISTEN_PORT, "DS100 Listen")
        require_udp_port(self.settings.digico_listen_port, "DiGiCo Listen")

        try:
            self._ds100.start()
            self._digico.start()
        except OSError:
            self.stop()
            raise

        self._running = True
        self._log(
            f"Bridge running: channels {self.settings.start_channel}"
            f"–{self.settings.end_channel}, {len(self.settings.mappings)} mapping(s)"
        )
        for mapping in self.settings.mappings:
            self._log(f"  • {mapping.label()}")

        bridge_ip = get_local_ip(target_host=self.settings.digico_host)
        self._log(
            f"DiGiCo Pad → {bridge_ip}:{self.settings.digico_listen_port}  "
            f"(Console {self.settings.digico_host}:{self.settings.digico_send_port})"
        )
        self._log(
            f"DS100 → {self.settings.ds100_host} "
            f"(ports {DS100_SEND_PORT}/{DS100_LISTEN_PORT})"
        )

        auxes = self._aux_numbers()
        self._ds100.start_polling(
            self.settings.start_channel,
            self.settings.end_channel,
            self.settings.mappings,
            self.settings.ds100_poll_interval_ms,
        )
        self._digico.request_aux_on(
            self.settings.start_channel, self.settings.end_channel, auxes
        )
        self._digico.request_aux_levels(
            self.settings.start_channel, self.settings.end_channel, auxes
        )

        threading.Thread(
            target=self.test_connections, daemon=True, name="conn-test-start"
        ).start()

    def test_connections(self) -> dict[str, bool]:
        if not self._running or not self._ds100 or not self._digico:
            return {"digico": False, "ds100": False}

        end = min(self.settings.start_channel + 2, self.settings.end_channel)
        auxes = self._aux_numbers()

        def query_few_channels() -> None:
            self._digico.request_aux_levels(self.settings.start_channel, end, auxes)
            self._digico.request_aux_on(self.settings.start_channel, end, auxes)

        return run_connection_test(
            ds100_resync=self._ds100.poll_mapped,
            digico_handshake=self._digico.send_handshake,
            digico_query=query_few_channels,
            monitor=self._monitor,
            log=self._log,
            digico_host=self.settings.digico_host,
            digico_port=self.settings.digico_send_port,
            digico_listen_port=self.settings.digico_listen_port,
            ds100_host=self.settings.ds100_host,
            ds100_port=DS100_SEND_PORT,
        )

    def stop(self) -> None:
        if self._digico:
            self._digico.stop()
            self._digico = None
        if self._ds100:
            self._ds100.stop()
            self._ds100 = None

        was_running = self._running
        self._engine = None
        self._running = False
        self._monitor.reset()
        if was_running:
            self._log("Bridge stopped")

    def _on_digico_level(self, channel: int, aux: int, value: float) -> None:
        if self._engine:
            self._engine.handle_digico_level(channel, aux, value)

    def _on_digico_aux_on(self, channel: int, aux: int, is_on: bool) -> None:
        if self._engine:
            self._engine.handle_digico_aux_on(channel, aux, is_on)

    def _on_ds100_enspace(self, channel: int, value: float) -> None:
        if self._engine:
            self._engine.handle_ds100_enspace_gain(channel, value)

    def _on_ds100_fg_gain(self, function_group: int, channel: int, value: float) -> None:
        if self._engine:
            self._engine.handle_ds100_fg_gain(function_group, channel, value)

    def _on_ds100_fg_mute(self, function_group: int, channel: int, muted: bool) -> None:
        if self._engine:
            self._engine.handle_ds100_fg_mute(function_group, channel, muted)

    def _send_ds100_level(self, mapping: MappingSpec, channel: int, value: float) -> None:
        if not self._ds100:
            return
        if mapping.ds100_kind == Ds100ParamKind.ENSPACE_SEND.value:
            self._ds100.send_enspace_gain(channel, value)
        elif (
            mapping.ds100_kind == Ds100ParamKind.FG_ROUTING.value
            and mapping.function_group is not None
        ):
            self._ds100.send_fg_gain(mapping.function_group, channel, value)

    def _send_ds100_mute(self, mapping: MappingSpec, channel: int, muted: bool) -> None:
        if not self._ds100:
            return
        if (
            mapping.ds100_kind == Ds100ParamKind.FG_ROUTING.value
            and mapping.function_group is not None
        ):
            self._ds100.send_fg_mute(mapping.function_group, channel, muted)

    def _send_digico_level(self, channel: int, aux: int, value: float) -> None:
        if self._digico:
            self._digico.send_aux_level(channel, aux, value)

    def _send_digico_on(self, channel: int, aux: int, is_on: bool) -> None:
        if self._digico:
            self._digico.send_aux_on(channel, aux, is_on)
