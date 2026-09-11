"""App shell: embed the web UI in a native WebKit window (no Tk).

Tkinter on this macOS/Python stack fails to paint widgets (blank grey window).
pywebview uses Cocoa/WebKit and matches the web GUI 1:1.
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request


def _wait_for_http(url: str, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as resp:
                if 200 <= getattr(resp, "status", 200) < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.1)
    return False


def run_webview_app() -> None:
    from bridge.web_gui import WebBridgeServer

    server = WebBridgeServer(host="127.0.0.1", port=8765)
    try:
        server.start(open_browser=False)
    except OSError as exc:
        _show_startup_error(f"Could not start web server:\n{exc}")
        raise SystemExit(1) from exc

    if not _wait_for_http(server.url):
        server.stop()
        _show_startup_error("Web UI did not become ready in time.")
        raise SystemExit(1)

    import webview

    def _on_closed() -> None:
        try:
            server.stop()
        except Exception:  # noqa: BLE001
            pass

    window = webview.create_window(
        title="Digico×Soundscape",
        url=server.url,
        width=1120,
        height=860,
        min_size=(900, 640),
        background_color="#050505",
        text_select=True,
    )
    window.events.closed += _on_closed

    try:
        webview.start(debug=False)
    finally:
        try:
            server.stop()
        except Exception:  # noqa: BLE001
            pass


def _show_startup_error(message: str) -> None:
    """Best-effort native alert without Tk."""
    try:
        import subprocess

        safe = message.replace("\\", "\\\\").replace('"', '\\"')
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display dialog "{safe}" with title "Digico×Soundscape" buttons {{"OK"}} default button 1',
            ],
            check=False,
        )
    except Exception:  # noqa: BLE001
        print(message, file=sys.stderr)


def run_headless_server(*, open_browser: bool = True) -> None:
    """Fallback: server + system browser, no embedded window."""
    from bridge.web_gui import WebBridgeServer

    server = WebBridgeServer(host="127.0.0.1", port=8765)
    server.start(open_browser=open_browser)
    try:
        while server.is_serving():
            time.sleep(0.4)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
