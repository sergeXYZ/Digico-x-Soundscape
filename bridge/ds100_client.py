"""DS100 Soundscape OSC client."""

from __future__ import annotations

import threading
from typing import Callable

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from bridge.constants import (
    DS100_LISTEN_PORT,
    DS100_POLL_INTERVAL_MS,
    DS100_PREFIX,
    DS100_SEND_PORT,
    ENSPACE_ZONE_COUNT,
)
from bridge.mapping import Ds100ParamKind, MappingSpec
from bridge.settings import clamp_poll_interval_ms
from bridge.sync_engine import (
    ds100_enspace_zone_gain_path,
    ds100_enspace_zone_mute_path,
    ds100_fg_routing_gain_path,
    ds100_fg_routing_mute_path,
    ds100_reverb_send_gain_path,
    parse_ds100_fg_routing_gain,
    parse_ds100_fg_routing_mute,
    parse_ds100_reverb_send_gain,
)


class DS100Client:
    def __init__(
        self,
        host: str,
        on_enspace_gain: Callable[[int, float], None],
        on_fg_gain: Callable[[int, int, float], None],  # fg, channel, value
        on_fg_mute: Callable[[int, int, bool], None],  # fg, channel, muted
        on_activity: Callable[[str], None] | None = None,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self.host = host
        self._on_enspace_gain = on_enspace_gain
        self._on_fg_gain = on_fg_gain
        self._on_fg_mute = on_fg_mute
        self._on_activity = on_activity or (lambda _key: None)
        self._log = log or (lambda _msg: None)
        self._client: SimpleUDPClient | None = None
        self._server: ThreadingOSCUDPServer | None = None
        self._thread: threading.Thread | None = None
        self._poll_thread: threading.Thread | None = None
        self._poll_stop = threading.Event()
        self._poll_start = 1
        self._poll_end = 1
        self._poll_interval_ms = DS100_POLL_INTERVAL_MS
        self._mappings: list[MappingSpec] = []

    def start(self) -> None:
        self._client = SimpleUDPClient(self.host, DS100_SEND_PORT)

        dispatcher = Dispatcher()
        dispatcher.set_default_handler(self._handle_message)

        self._server = ThreadingOSCUDPServer(
            ("0.0.0.0", DS100_LISTEN_PORT),
            dispatcher,
        )
        self._server.allow_reuse_address = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="ds100-osc-server",
            daemon=True,
        )
        self._thread.start()
        self._log(f"DS100 listener on port {DS100_LISTEN_PORT}")

    def start_polling(
        self,
        start_channel: int,
        end_channel: int,
        mappings: list[MappingSpec],
        interval_ms: int = DS100_POLL_INTERVAL_MS,
    ) -> None:
        self.stop_polling()
        self._poll_start = start_channel
        self._poll_end = end_channel
        self._mappings = list(mappings)
        self._poll_interval_ms = clamp_poll_interval_ms(interval_ms)
        self._poll_stop.clear()
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            name="ds100-poll",
            daemon=True,
        )
        self._poll_thread.start()
        self._log(
            f"DS100 polling every {self._poll_interval_ms} ms "
            f"for channels {start_channel}–{end_channel} "
            f"({len(mappings)} mapping(s))"
        )
        self.poll_mapped()

    def stop_polling(self) -> None:
        self._poll_stop.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2.0)
        self._poll_thread = None

    def stop(self) -> None:
        self.stop_polling()
        if self._server:
            self._server.shutdown()
            self._server = None
        self._client = None

    def poll_mapped(self) -> None:
        if not self._client:
            return
        for mapping in self._mappings:
            for channel in range(self._poll_start, self._poll_end + 1):
                if mapping.ds100_kind == Ds100ParamKind.ENSPACE_SEND.value:
                    self._client.send_message(ds100_reverb_send_gain_path(channel), [])
                    self._on_activity("ds100_tx")
                elif (
                    mapping.ds100_kind == Ds100ParamKind.FG_ROUTING.value
                    and mapping.function_group is not None
                ):
                    fg = mapping.function_group
                    self._client.send_message(
                        ds100_fg_routing_gain_path(fg, channel), []
                    )
                    self._client.send_message(
                        ds100_fg_routing_mute_path(fg, channel), []
                    )
                    self._on_activity("ds100_tx")

    def send_enspace_gain(self, channel: int, value: float) -> None:
        if not self._client:
            return
        self._client.send_message(ds100_reverb_send_gain_path(channel), value)
        self._on_activity("ds100_tx")

    def send_fg_gain(self, function_group: int, channel: int, value: float) -> None:
        if not self._client:
            return
        self._client.send_message(
            ds100_fg_routing_gain_path(function_group, channel), value
        )
        self._on_activity("ds100_tx")

    def send_fg_mute(self, function_group: int, channel: int, muted: bool) -> None:
        if not self._client:
            return
        self._client.send_message(
            ds100_fg_routing_mute_path(function_group, channel),
            1.0 if muted else 0.0,
        )
        self._on_activity("ds100_tx")

    def send_enspace_zones_gain(self, value: float) -> None:
        """Set En-Space zone processing gain on zones 1–4."""
        if not self._client:
            return
        for zone in range(1, ENSPACE_ZONE_COUNT + 1):
            self._client.send_message(ds100_enspace_zone_gain_path(zone), value)
        self._on_activity("ds100_tx")

    def send_enspace_zones_mute(self, muted: bool) -> None:
        """Set En-Space zone mute on zones 1–4 (1 = muted)."""
        if not self._client:
            return
        flag = 1.0 if muted else 0.0
        for zone in range(1, ENSPACE_ZONE_COUNT + 1):
            self._client.send_message(ds100_enspace_zone_mute_path(zone), flag)
        self._on_activity("ds100_tx")

    def _poll_loop(self) -> None:
        interval = self._poll_interval_ms / 1000.0
        while not self._poll_stop.wait(interval):
            self.poll_mapped()

    def _handle_message(self, address: str, *args: object) -> None:
        if not args:
            return
        value = args[0]
        if not isinstance(value, (int, float)):
            return

        ch = parse_ds100_reverb_send_gain(address, DS100_PREFIX)
        if ch is not None:
            self._on_activity("ds100_rx")
            self._on_enspace_gain(ch, float(value))
            return

        fg_gain = parse_ds100_fg_routing_gain(address, DS100_PREFIX)
        if fg_gain is not None:
            fg, channel = fg_gain
            self._on_activity("ds100_rx")
            self._on_fg_gain(fg, channel, float(value))
            return

        fg_mute = parse_ds100_fg_routing_mute(address, DS100_PREFIX)
        if fg_mute is not None:
            fg, channel = fg_mute
            muted = float(value) >= 0.5
            self._on_activity("ds100_rx")
            self._on_fg_mute(fg, channel, muted)
