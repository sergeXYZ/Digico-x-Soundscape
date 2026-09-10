"""Entry point for the DiGiCo ↔ DS100 OSC bridge."""

import sys


def main() -> None:
    # Web UI is default — tkinter is unreliable on some macOS Python builds.
    if "--tk" in sys.argv:
        from bridge.gui import run_gui

        run_gui()
    else:
        from bridge.web_gui import run_web_gui

        run_web_gui()


if __name__ == "__main__":
    main()
