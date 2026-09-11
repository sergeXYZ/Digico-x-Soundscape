"""Entry point for the DiGiCo ↔ DS100 OSC bridge."""

import sys


def main() -> None:
    # Default: WebKit app window hosting the web UI (no Tk — blank on this macOS).
    # --web-only: Flask only + system browser
    # --launcher-tk: legacy Tk launcher (often blank grey window on macOS)
    # --tk: legacy full tkinter bridge GUI (no web UI)
    if "--tk" in sys.argv:
        from bridge.gui import run_gui

        run_gui()
    elif "--launcher-tk" in sys.argv:
        from bridge.launcher_gui import run_launcher

        run_launcher()
    elif "--web-only" in sys.argv:
        from bridge.webview_app import run_headless_server

        run_headless_server(open_browser=True)
    else:
        try:
            from bridge.webview_app import run_webview_app

            run_webview_app()
        except Exception as exc:  # noqa: BLE001
            # Last resort: browser-only so the product still runs
            print(f"WebView unavailable ({exc}); falling back to browser.", file=sys.stderr)
            from bridge.webview_app import run_headless_server

            run_headless_server(open_browser=True)


if __name__ == "__main__":
    main()
