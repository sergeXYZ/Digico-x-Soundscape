"""Connection status tracking and OSC reachability tests."""

from __future__ import annotations

import socket
import time
from typing import Callable

CONN_STALE_SEC = 30.0
TEST_WAIT_SEC = 3.0


class ConnectionMonitor:
    """Tracks whether each device has responded recently on OSC."""

    def __init__(self) -> None:
        self._digico_rx_at: float | None = None
        self._ds100_rx_at: float | None = None
        self.digico_rx_count = 0
        self.ds100_rx_count = 0

    def note_activity(self, key: str) -> None:
        now = time.time()
        if key == "digico_rx":
            self.digico_rx_count += 1
            self._digico_rx_at = now
        elif key == "ds100_rx":
            self.ds100_rx_count += 1
            self._ds100_rx_at = now

    def digico_connected(self) -> bool:
        if self._digico_rx_at is None:
            return False
        return (time.time() - self._digico_rx_at) < CONN_STALE_SEC

    def ds100_connected(self) -> bool:
        if self._ds100_rx_at is None:
            return False
        return (time.time() - self._ds100_rx_at) < CONN_STALE_SEC

    def reset(self) -> None:
        self._digico_rx_at = None
        self._ds100_rx_at = None
        self.digico_rx_count = 0
        self.ds100_rx_count = 0

    def status(self) -> dict[str, bool]:
        return {
            "digico": self.digico_connected(),
            "ds100": self.ds100_connected(),
        }


def probe_udp_host(host: str, port: int, timeout: float = 1.0) -> bool:
    """Best-effort check that a UDP destination is reachable (no ICMP guarantee)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(b"\x00", (host, port))
        sock.close()
        return True
    except OSError:
        return False


def run_connection_test(
    *,
    ds100_resync: Callable[[], None],
    digico_handshake: Callable[[], None],
    digico_query: Callable[[], None],
    monitor: ConnectionMonitor,
    log: Callable[[str], None],
    digico_host: str,
    digico_port: int,
    digico_listen_port: int,
    ds100_host: str,
    ds100_port: int,
    wait_sec: float = TEST_WAIT_SEC,
) -> dict[str, bool]:
    log("Verbindungstest gestartet…")

    digico_reachable = probe_udp_host(digico_host, digico_port)
    ds100_reachable = probe_udp_host(ds100_host, ds100_port)
    log(
        f"  UDP erreichbar: DiGiCo {digico_host}:{digico_port} "
        f"{'OK' if digico_reachable else '?'}  |  DS100 {ds100_host}:{ds100_port} "
        f"{'OK' if ds100_reachable else '?'}"
    )

    baseline_d = monitor.digico_rx_count
    baseline_s = monitor.ds100_rx_count

    ds100_resync()
    digico_handshake()
    digico_query()

    deadline = time.time() + wait_sec
    osc_digico = False
    osc_ds100 = False

    while time.time() < deadline:
        if monitor.digico_rx_count > baseline_d:
            osc_digico = True
        if monitor.ds100_rx_count > baseline_s:
            osc_ds100 = True
        if osc_digico and osc_ds100:
            break
        time.sleep(0.05)

    results = {
        "digico": osc_digico,
        "ds100": osc_ds100,
    }

    log(
        f"Verbindungstest: DiGiCo OSC {'OK' if osc_digico else 'KEINE ANTWORT'}  |  "
        f"DS100 OSC {'OK' if osc_ds100 else 'KEINE ANTWORT'}"
    )
    if not osc_digico:
        log(
            f"  → DiGiCo: External Control → DiGiCo Pad → "
            f"Bridge-IP und Send-Port {digico_listen_port} prüfen"
        )
    if not osc_ds100:
        log("  → DS100: IP und Netzwerk prüfen (Ports 50010/50011)")

    return results
