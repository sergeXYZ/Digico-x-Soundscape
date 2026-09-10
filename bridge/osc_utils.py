"""OSC / UDP helpers."""

from __future__ import annotations

import socket


def is_udp_port_free(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def port_owner_hint(port: int) -> str:
    import subprocess

    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iUDP:{port}"],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = [ln for ln in result.stdout.strip().splitlines()[1:] if ln.strip()]
        if not lines:
            return ""
        parts = lines[0].split()
        if len(parts) >= 2:
            return f" (used by {parts[0]} PID {parts[1]})"
    except OSError:
        pass
    return ""


def require_udp_port(port: int, label: str) -> None:
    if is_udp_port_free(port):
        return

    hint = port_owner_hint(port)
    extra = ""
    if port == 50011:
        extra = " Stop Bitfocus Companion DS100 module if running on this Mac."
    elif port == 9000:
        extra = " Stop other bridge instances."

    raise OSError(f"Port {port} ({label}) already in use{hint}.{extra}")
