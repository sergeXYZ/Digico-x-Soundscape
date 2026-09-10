"""Network helpers."""

from __future__ import annotations

import socket


def get_local_ip(preferred_prefix: str = "10.", target_host: str | None = None) -> str:
    """Return local IPv4 on the route towards target_host (if given)."""
    if target_host and not target_host.startswith("127."):
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect((target_host, 1))
            ip = probe.getsockname()[0]
            probe.close()
            if not ip.startswith("127."):
                return ip
        except OSError:
            pass

    candidates: list[str] = []

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                candidates.append(ip)
    except OSError:
        pass

    for probe_host in ("10.150.1.1", "192.168.20.1", "192.168.1.1"):
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect((probe_host, 1))
            ip = probe.getsockname()[0]
            probe.close()
            if not ip.startswith("127.") and ip not in candidates:
                candidates.insert(0, ip)
        except OSError:
            pass

    for ip in candidates:
        if ip.startswith(preferred_prefix):
            return ip

    return candidates[0] if candidates else "127.0.0.1"
