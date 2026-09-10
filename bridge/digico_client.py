"""DiGiCo Pad OSC client."""

from __future__ import annotations

import threading
from typing import Callable

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_server import ThreadingOSCUDPServer

from bridge.constants import DIGICO_HANDSHAKE_PATH
from bridge.net_utils import get_local_ip
from bridge.sync_engine import (
    digico_aux_level_path,
    digico_aux_on_path,
    osc_truthy,
    parse_digico_aux_level,
    parse_digico_aux_on,
)


class DigicoClient:
    """DiGiCo Pad client — RX and TX share the listen_port UDP socket."""

    def __init__(
        self,
        host: str,
        send_port: int,
        listen_port: int,
        on_aux_level: Callable[[int, int, float], None],  # channel, aux, value
        on_aux_on: Callable[[int, int, bool], None] | None = None,
        on_activity: Callable[[str], None] | None = None,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self.host = host
        self.send_port = send_port
        self.listen_port = listen_port
        self._on_aux_level = on_aux_level
        self._on_aux_on = on_aux_on or (lambda _ch, _aux, _on: None)
        self._on_activity = on_activity or (lambda _key: None)
        self._log = log or (lambda _msg: None)
        self._unknown_addresses: set[str] = set()
        self._server: ThreadingOSCUDPServer | None = None
        self._thread: threading.Thread | None = None
        self._bind_ip = "0.0.0.0"

    def start(self) -> None:
        dispatcher = Dispatcher()
        dispatcher.set_default_handler(self._handle_message)

        self._bind_ip = get_local_ip(target_host=self.host)
        self._server = ThreadingOSCUDPServer(
            (self._bind_ip, self.listen_port),
            dispatcher,
        )
        self._server.allow_reuse_address = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="digico-osc-server",
            daemon=True,
        )
        self._thread.start()
        self._log(
            f"DiGiCo listener on {self._bind_ip}:{self.listen_port} "
            f"(sends to {self.host}:{self.send_port} from same port)"
        )
        self.send_handshake()
        self._log(
            f"Waiting for DiGiCo OSC on port {self.listen_port} — "
            "Pad device must use this Mac's IP"
        )

    def request_aux_levels(
        self, start_channel: int, end_channel: int, aux_numbers: list[int]
    ) -> None:
        for aux in aux_numbers:
            for channel in range(start_channel, end_channel + 1):
                self._send_message(f"{digico_aux_level_path(channel, aux)}/?")
        self._log(
            f"DiGiCo aux level query ch {start_channel}–{end_channel} "
            f"aux {sorted(set(aux_numbers))}"
        )

    def request_aux_on(
        self, start_channel: int, end_channel: int, aux_numbers: list[int]
    ) -> None:
        for aux in aux_numbers:
            for channel in range(start_channel, end_channel + 1):
                self._send_message(f"{digico_aux_on_path(channel, aux)}/?")
        self._log(
            f"DiGiCo Aux Send On query ch {start_channel}–{end_channel} "
            f"aux {sorted(set(aux_numbers))}"
        )

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None

    def send_handshake(self) -> None:
        self._send_message(DIGICO_HANDSHAKE_PATH)
        self._log(f"DiGiCo handshake sent to {self.host}:{self.send_port}")

    def send_aux_level(self, channel: int, aux_number: int, value: float) -> None:
        self._send_message(digico_aux_level_path(channel, aux_number), value)

    def send_aux_on(self, channel: int, aux_number: int, is_on: bool) -> None:
        self._send_message(digico_aux_on_path(channel, aux_number), 1.0 if is_on else 0.0)

    def _send_message(self, address: str, *args: float) -> None:
        if not self._server:
            return
        builder = OscMessageBuilder(address=address)
        for arg in args:
            builder.add_arg(float(arg), OscMessageBuilder.ARG_TYPE_FLOAT)
        msg = builder.build()
        self._server.socket.sendto(msg.dgram, (self.host, self.send_port))
        self._on_activity("digico_tx")

    def _handle_message(self, address: str, *args: object) -> None:
        on_parsed = parse_digico_aux_on(address)
        if on_parsed is not None:
            if not args:
                return
            is_on = osc_truthy(args[0])
            if is_on is None:
                return
            channel, aux = on_parsed
            self._on_activity("digico_rx")
            self._on_aux_on(channel, aux, is_on)
            return

        level_parsed = parse_digico_aux_level(address)
        if level_parsed is None:
            if address not in self._unknown_addresses:
                self._unknown_addresses.add(address)
                self._log(f"DiGiCo OSC (unmapped): {address} {list(args)}")
            return
        if not args:
            return
        value = args[0]
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            channel, aux = level_parsed
            self._on_activity("digico_rx")
            self._on_aux_level(channel, aux, float(value))
