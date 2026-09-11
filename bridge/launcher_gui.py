"""Native launcher: start/stop the Digico×Soundscape web server.

Designed for macOS Tk (Aqua): Label-buttons, no ttk, no early Flask import.
"""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox

APP_TITLE = "Digico×Soundscape"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

BG = "#050505"
BG_BAR = "#000000"
BG_PANEL = "#0c0c0c"
BG_ROW = "#141414"
BG_HOVER = "#1c1c1c"
BORDER = "#2a5a2e"
TEXT = "#f2f2f2"
MUTED = "#8a9a8c"
ACCENT = "#39ff14"
OK_BG = "#0d2410"
DANGER_BG = "#2a1010"
DANGER_FG = "#ffb0b0"
ERR = "#ff4d4d"

FONT = ("Helvetica", 13)
FONT_BOLD = ("Helvetica", 13, "bold")
FONT_BRAND = ("Helvetica", 16, "bold")
FONT_SMALL = ("Helvetica", 12)
FONT_SECTION = ("Helvetica", 11, "bold")
LOG_FONT = ("Menlo", 12) if sys.platform == "darwin" else ("Consolas", 12)


def _asset(name: str) -> Path | None:
    from bridge.resources import asset_path

    path = asset_path(name)
    return path if path.is_file() else None


class _Btn(tk.Frame):
    """Clickable colored control — avoids Aqua tk.Button chrome."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        command,
        *,
        fg: str,
        bg: str,
        border: str,
        hover: str,
    ) -> None:
        super().__init__(
            parent,
            bg=border,
            highlightthickness=0,
            bd=0,
        )
        self._command = command
        self._fg = fg
        self._bg = bg
        self._hover = hover
        self._border = border
        self._enabled = True
        self._label = tk.Label(
            self,
            text=text,
            font=FONT_BOLD,
            fg=fg,
            bg=bg,
            padx=14,
            pady=8,
            cursor="hand2",
            bd=0,
        )
        self._label.pack(padx=1, pady=1)
        for w in (self, self._label):
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", self._enter)
            w.bind("<Leave>", self._leave)

    def _click(self, _event=None) -> None:
        if self._enabled:
            self._command()

    def _enter(self, _event=None) -> None:
        if self._enabled:
            self._label.configure(bg=self._hover)

    def _leave(self, _event=None) -> None:
        if self._enabled:
            self._label.configure(bg=self._bg)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            self.configure(bg=self._border)
            self._label.configure(fg=self._fg, bg=self._bg, cursor="hand2")
        else:
            self.configure(bg=BORDER)
            self._label.configure(fg=MUTED, bg=BG_ROW, cursor="arrow")


class LauncherGUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("680x540")
        self.root.minsize(560, 420)
        self.root.configure(bg=BG)

        self._server = None
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._url = f"http://{DEFAULT_HOST}:{DEFAULT_PORT}/"
        self._logo_image: tk.PhotoImage | None = None

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        try:
            self._build_bar()
            self._build_info()
            self._build_log()
        except Exception as exc:  # noqa: BLE001
            tk.Label(
                self.root,
                text=f"UI build error:\n{exc}",
                fg=ERR,
                bg=BG,
                justify="left",
                font=FONT,
            ).grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
            return

        self._append_log("Ready. Starting web server…")
        self._poll_log()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(300, self._start_server)

    def run(self) -> None:
        self.root.mainloop()

    def _build_bar(self) -> None:
        # Do NOT use grid_propagate(False) without an explicit width — on macOS
        # that collapses the bar to ~0px and leaves an empty-looking window.
        bar = tk.Frame(self.root, bg=BG_BAR, highlightbackground=BORDER, highlightthickness=1)
        bar.grid(row=0, column=0, sticky="ew")

        inner = tk.Frame(bar, bg=BG_BAR)
        inner.pack(fill="x", padx=14, pady=12)

        left = tk.Frame(inner, bg=BG_BAR)
        left.pack(side="left")

        logo = _asset("logo-64.png")
        if logo is not None:
            try:
                self._logo_image = tk.PhotoImage(file=str(logo))
                box = tk.Frame(left, bg=ACCENT)
                box.pack(side="left", padx=(0, 12))
                tk.Label(box, image=self._logo_image, bg=BG_BAR, bd=0).pack(
                    padx=1, pady=1
                )
            except tk.TclError:
                self._logo_image = None

        brand = tk.Frame(left, bg=BG_BAR)
        brand.pack(side="left")
        tk.Label(brand, text="Digico", font=FONT_BRAND, fg=TEXT, bg=BG_BAR).pack(
            side="left"
        )
        tk.Label(brand, text="<x>", font=FONT_BRAND, fg=ACCENT, bg=BG_BAR).pack(
            side="left"
        )
        tk.Label(brand, text="Soundscape", font=FONT_BRAND, fg=TEXT, bg=BG_BAR).pack(
            side="left"
        )

        self._pill_border = tk.Frame(left, bg=BORDER)
        self._pill_border.pack(side="left", padx=(16, 0))
        self._status_var = tk.StringVar(value="Stopped")
        self._status_label = tk.Label(
            self._pill_border,
            textvariable=self._status_var,
            font=FONT_SMALL,
            fg=MUTED,
            bg=BG_ROW,
            padx=10,
            pady=4,
        )
        self._status_label.pack(padx=1, pady=1)

        actions = tk.Frame(inner, bg=BG_BAR)
        actions.pack(side="right")

        self._start_btn = _Btn(
            actions, "Start", self._start_server,
            fg=ACCENT, bg=OK_BG, border=ACCENT, hover="#14351a",
        )
        self._start_btn.pack(side="left")

        self._stop_btn = _Btn(
            actions, "Stop", self._stop_server,
            fg=DANGER_FG, bg=DANGER_BG, border=ERR, hover="#3a1818",
        )
        self._stop_btn.pack(side="left", padx=(8, 0))
        self._stop_btn.set_enabled(False)

        self._browser_btn = _Btn(
            actions, "Open Browser", self._open_browser,
            fg=TEXT, bg=BG_ROW, border=BORDER, hover=BG_HOVER,
        )
        self._browser_btn.pack(side="left", padx=(8, 0))
        self._browser_btn.set_enabled(False)

    def _build_info(self) -> None:
        wrap = tk.Frame(self.root, bg=BG)
        wrap.grid(row=1, column=0, sticky="ew", padx=16, pady=(16, 0))

        border = tk.Frame(wrap, bg=BORDER)
        border.pack(fill="x")
        panel = tk.Frame(border, bg=BG_PANEL)
        panel.pack(fill="x", padx=1, pady=1)
        inner = tk.Frame(panel, bg=BG_PANEL)
        inner.pack(fill="x", padx=16, pady=14)

        tk.Label(inner, text="WEB UI", font=FONT_SECTION, fg=MUTED, bg=BG_PANEL).pack(
            anchor="w"
        )
        self._url_var = tk.StringVar(value=self._url)
        tk.Label(
            inner, textvariable=self._url_var, font=LOG_FONT, fg=ACCENT, bg=BG_PANEL
        ).pack(anchor="w", pady=(8, 0))
        tk.Label(
            inner,
            text="Desktop launcher · configure Digico ↔ DS100 in the browser.",
            font=FONT_SMALL,
            fg=MUTED,
            bg=BG_PANEL,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

    def _build_log(self) -> None:
        wrap = tk.Frame(self.root, bg=BG)
        wrap.grid(row=2, column=0, sticky="nsew", padx=16, pady=16)
        wrap.rowconfigure(1, weight=1)
        wrap.columnconfigure(0, weight=1)

        head = tk.Frame(wrap, bg=BG)
        head.grid(row=0, column=0, sticky="w", pady=(0, 8))
        tk.Label(head, text="▶", font=FONT_SECTION, fg=ACCENT, bg=BG).pack(side="left")
        tk.Label(head, text=" LOG", font=FONT_SECTION, fg=MUTED, bg=BG).pack(side="left")

        border = tk.Frame(wrap, bg=BORDER)
        border.grid(row=1, column=0, sticky="nsew")
        border.rowconfigure(0, weight=1)
        border.columnconfigure(0, weight=1)

        panel = tk.Frame(border, bg="#000000")
        panel.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)

        self._log_text = tk.Text(
            panel,
            height=14,
            state="disabled",
            wrap="word",
            font=LOG_FONT,
            bg="#000000",
            fg=MUTED,
            insertbackground=ACCENT,
            selectbackground="#1a5c14",
            selectforeground=ACCENT,
            highlightthickness=0,
            bd=0,
            padx=12,
            pady=12,
        )
        scroll = tk.Scrollbar(panel, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scroll.set)
        self._log_text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

    def _enqueue_log(self, message: str) -> None:
        self._log_queue.put(message)

    def _poll_log(self) -> None:
        while True:
            try:
                self._append_log(self._log_queue.get_nowait())
            except queue.Empty:
                break
        self.root.after(100, self._poll_log)

    def _append_log(self, message: str) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert("end", message + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _set_running_ui(self, running: bool) -> None:
        if running:
            self._status_var.set("Running")
            self._status_label.configure(fg=ACCENT, bg=BG_ROW)
            self._pill_border.configure(bg=ACCENT)
        else:
            self._status_var.set("Stopped")
            self._status_label.configure(fg=MUTED, bg=BG_ROW)
            self._pill_border.configure(bg=BORDER)
        self._start_btn.set_enabled(not running)
        self._stop_btn.set_enabled(running)
        self._browser_btn.set_enabled(running)

    def _start_server(self) -> None:
        if self._server is not None:
            try:
                if self._server.is_serving():
                    return
            except Exception:  # noqa: BLE001
                pass

        self._start_btn.set_enabled(False)
        self._append_log("Starting web server…")

        def _worker() -> None:
            try:
                # Lazy import so Tk UI can show before Flask loads
                from bridge.web_gui import WebBridgeServer

                server = WebBridgeServer(host=DEFAULT_HOST, port=DEFAULT_PORT)
                original_log = server._log

                def _log(message: str) -> None:
                    original_log(message)
                    self._enqueue_log(message)

                server._log = _log  # type: ignore[method-assign]
                server.start(open_browser=True)
                self.root.after(0, lambda: self._on_server_started(server))
            except Exception as exc:  # noqa: BLE001
                self.root.after(0, lambda: self._on_server_start_failed(str(exc)))

        threading.Thread(target=_worker, name="web-server-start", daemon=True).start()

    def _on_server_started(self, server) -> None:
        self._server = server
        self._url = server.url
        self._url_var.set(self._url)
        self._set_running_ui(True)

    def _on_server_start_failed(self, error: str) -> None:
        self._server = None
        self._set_running_ui(False)
        messagebox.showerror("Start failed", error)
        self._append_log(f"Start failed: {error}")

    def _stop_server(self) -> None:
        server = self._server
        self._server = None
        self._set_running_ui(False)
        if server is None:
            return
        self._append_log("Stopping web server…")

        def _worker() -> None:
            try:
                server.stop()
            except Exception as exc:  # noqa: BLE001
                self._enqueue_log(f"Stop warning: {exc}")
            else:
                self._enqueue_log("Server stopped.")

        threading.Thread(target=_worker, name="web-server-stop", daemon=True).start()

    def _open_browser(self) -> None:
        webbrowser.open(self._url)

    def _on_close(self) -> None:
        if self._server is not None:
            try:
                self._server.stop()
            except Exception:  # noqa: BLE001
                pass
            self._server = None
        self.root.destroy()


def run_launcher() -> None:
    try:
        LauncherGUI().run()
    except Exception as exc:
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Launcher startup error", str(exc))
            root.destroy()
        except Exception:  # noqa: BLE001
            print(f"Launcher startup error: {exc}", file=sys.stderr)
        raise
