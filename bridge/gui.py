"""tkinter GUI for the DiGiCo ↔ DS100 OSC bridge."""

from __future__ import annotations

import ipaddress
import queue
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext

from bridge.bridge_app import BridgeApp
from bridge.constants import DS100_LISTEN_PORT, DS100_SEND_PORT
from bridge.net_utils import get_local_ip
from bridge.settings import BridgeSettings, clamp_poll_interval_ms, load_settings, save_settings

FONT = ("Helvetica", 12)
FONT_BOLD = ("Helvetica", 12, "bold")
FONT_TITLE = ("Helvetica", 16, "bold")
LOG_FONT = ("Monaco", 11) if sys.platform == "darwin" else ("Consolas", 11)

LED_OFF = "#bdbdbd"
LED_ON = "#00c853"


class ActivityLed(tk.Canvas):
    def __init__(self, parent: tk.Misc, size: int = 16) -> None:
        super().__init__(parent, width=size, height=size, highlightthickness=0, bd=0)
        self._size = size
        self._oval = self.create_oval(2, 2, size - 2, size - 2, fill=LED_OFF, outline="#666")
        self._off_timer: str | None = None

    def flash(self) -> None:
        self.itemconfigure(self._oval, fill=LED_ON)
        if self._off_timer:
            self.after_cancel(self._off_timer)
        self._off_timer = self.after(450, self._turn_off)

    def _turn_off(self) -> None:
        self.itemconfigure(self._oval, fill=LED_OFF)
        self._off_timer = None


class BridgeGUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("DiGiCo Aux1 - DS100 Reverb Send Gain Bridge")
        self.root.geometry("720x820")
        self.root.minsize(680, 780)

        self._log_queue: queue.Queue[str] = queue.Queue()
        self._activity_queue: queue.Queue[str] = queue.Queue()
        self._bridge: BridgeApp | None = None
        self._settings = load_settings()
        self._vars: dict[str, tk.StringVar] = {}
        self._entries: list[tk.Entry] = []
        self._leds: dict[str, ActivityLed] = {}

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)

        self._build_header()
        self._build_controls()
        self._build_channels()
        self._build_devices()
        self._build_log()
        self._load_fields()
        self._append_log("Ready. Configure devices and click Start Bridge.")
        self._poll_queues()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def run(self) -> None:
        self.root.mainloop()

    def _build_header(self) -> None:
        hdr = tk.Frame(self.root, pady=8)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="DiGiCo Aux1  ↔  DS100 Reverb Send Gain", font=FONT_TITLE).pack()
        bridge_ip = get_local_ip(target_host=load_settings().digico_host)
        tk.Label(
            hdr,
            text=f"Bridge IP (set as DiGiCo Pad in External Control): {bridge_ip}",
            font=("Helvetica", 11),
            fg="#004488",
        ).pack(pady=(4, 0))

    def _build_controls(self) -> None:
        frame = tk.Frame(self.root, padx=12, pady=4)
        frame.grid(row=1, column=0, sticky="ew")

        self._start_btn = tk.Button(
            frame,
            text="▶  Start Bridge",
            font=("Helvetica", 14, "bold"),
            bg="#28a745",
            fg="white",
            padx=20,
            pady=8,
            command=self._start_bridge,
        )
        self._start_btn.pack(side="left")

        self._stop_btn = tk.Button(
            frame,
            text="■  Stop Bridge",
            font=("Helvetica", 14, "bold"),
            bg="#dc3545",
            fg="white",
            padx=20,
            pady=8,
            state="disabled",
            command=self._stop_bridge,
        )
        self._stop_btn.pack(side="left", padx=(10, 0))

        self._status_var = tk.StringVar(value="Stopped")
        tk.Label(frame, text="Status:", font=FONT).pack(side="right", padx=(0, 4))
        tk.Label(frame, textvariable=self._status_var, font=FONT_BOLD, fg="blue").pack(side="right")

    def _build_channels(self) -> None:
        frame = tk.LabelFrame(self.root, text=" Channel Range ", font=FONT_BOLD, padx=12, pady=8)
        frame.grid(row=2, column=0, sticky="ew", padx=12, pady=4)

        tk.Label(frame, text="Start Kanal", font=FONT).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self._vars["start_channel"] = tk.StringVar()
        e1 = tk.Entry(frame, textvariable=self._vars["start_channel"], font=FONT, width=8)
        e1.grid(row=0, column=1, sticky="w")
        self._entries.append(e1)

        tk.Label(frame, text="End Kanal", font=FONT).grid(row=0, column=2, sticky="w", padx=(24, 8))
        self._vars["end_channel"] = tk.StringVar()
        e2 = tk.Entry(frame, textvariable=self._vars["end_channel"], font=FONT, width=8)
        e2.grid(row=0, column=3, sticky="w")
        self._entries.append(e2)

    def _build_devices(self) -> None:
        outer = tk.Frame(self.root, padx=12, pady=4)
        outer.grid(row=3, column=0, sticky="ew")
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)

        self._build_digico_panel(outer)
        self._build_ds100_panel(outer)

    def _port_row(
        self,
        parent: tk.Frame,
        row: int,
        label: str,
        port_text: str,
        led_key: str,
        editable_var: tk.StringVar | None = None,
    ) -> None:
        tk.Label(parent, text=label, font=FONT, anchor="w").grid(
            row=row, column=0, sticky="w", pady=4, columnspan=2
        )

        if editable_var is not None:
            port_widget = tk.Entry(parent, textvariable=editable_var, font=FONT, width=8)
            self._entries.append(port_widget)
        else:
            port_widget = tk.Label(parent, text=port_text, font=FONT_BOLD, anchor="w")

        port_widget.grid(row=row, column=2, sticky="w", padx=(8, 0), pady=4)

        led = ActivityLed(parent)
        led.grid(row=row, column=3, sticky="w", padx=(10, 0), pady=4)
        self._leds[led_key] = led

    def _build_digico_panel(self, parent: tk.Frame) -> None:
        frame = tk.LabelFrame(parent, text=" DiGiCo Console ", font=FONT_BOLD, padx=12, pady=10)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        tk.Label(frame, text="IP Address", font=FONT).grid(row=0, column=0, sticky="w", pady=4)
        self._vars["digico_host"] = tk.StringVar()
        ip_entry = tk.Entry(frame, textvariable=self._vars["digico_host"], font=FONT, width=18)
        ip_entry.grid(row=0, column=1, columnspan=3, sticky="ew", pady=4, padx=(8, 0))
        self._entries.append(ip_entry)

        self._vars["digico_listen_port"] = tk.StringVar()
        self._port_row(
            frame,
            1,
            "Receive  (Console → Bridge)",
            "",
            "digico_rx",
            self._vars["digico_listen_port"],
        )

        self._vars["digico_send_port"] = tk.StringVar()
        self._port_row(
            frame,
            2,
            "Send     (Bridge → Console)",
            "",
            "digico_tx",
            self._vars["digico_send_port"],
        )

        frame.columnconfigure(1, weight=1)

    def _build_ds100_panel(self, parent: tk.Frame) -> None:
        frame = tk.LabelFrame(parent, text=" DS100 Soundscape ", font=FONT_BOLD, padx=12, pady=10)
        frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        tk.Label(frame, text="IP Address", font=FONT).grid(row=0, column=0, sticky="w", pady=4)
        self._vars["ds100_host"] = tk.StringVar()
        ip_entry = tk.Entry(frame, textvariable=self._vars["ds100_host"], font=FONT, width=18)
        ip_entry.grid(row=0, column=1, columnspan=3, sticky="ew", pady=4, padx=(8, 0))
        self._entries.append(ip_entry)

        self._port_row(
            frame,
            1,
            "Receive  (DS100 → Bridge)",
            str(DS100_LISTEN_PORT),
            "ds100_rx",
        )

        self._port_row(
            frame,
            2,
            "Send     (Bridge → DS100)",
            str(DS100_SEND_PORT),
            "ds100_tx",
        )

        tk.Label(frame, text="Polling (ms)", font=FONT).grid(row=3, column=0, sticky="w", pady=4)
        self._vars["ds100_poll_interval_ms"] = tk.StringVar()
        poll_entry = tk.Entry(
            frame, textvariable=self._vars["ds100_poll_interval_ms"], font=FONT, width=8
        )
        poll_entry.grid(row=3, column=1, sticky="w", pady=4, padx=(8, 0))
        self._entries.append(poll_entry)

        frame.columnconfigure(1, weight=1)

    def _build_log(self) -> None:
        frame = tk.LabelFrame(self.root, text=" Log ", font=FONT_BOLD, padx=8, pady=8)
        frame.grid(row=4, column=0, sticky="nsew", padx=12, pady=(4, 12))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self._log_text = scrolledtext.ScrolledText(
            frame,
            height=14,
            width=80,
            state="normal",
            wrap="word",
            font=LOG_FONT,
            bg="#1e1e1e",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
        )
        self._log_text.grid(row=0, column=0, sticky="nsew")
        self._log_text.configure(state="disabled")

    def _load_fields(self) -> None:
        s = self._settings
        self._vars["start_channel"].set(str(s.start_channel))
        self._vars["end_channel"].set(str(s.end_channel))
        self._vars["digico_host"].set(s.digico_host)
        self._vars["digico_send_port"].set(str(s.digico_send_port))
        self._vars["digico_listen_port"].set(str(s.digico_listen_port))
        self._vars["ds100_host"].set(s.ds100_host)
        self._vars["ds100_poll_interval_ms"].set(str(s.ds100_poll_interval_ms))

    def _read_settings(self) -> BridgeSettings:
        start = int(self._vars["start_channel"].get().strip())
        end = int(self._vars["end_channel"].get().strip())
        digico_send = int(self._vars["digico_send_port"].get().strip())
        digico_listen = int(self._vars["digico_listen_port"].get().strip())
        poll_ms = clamp_poll_interval_ms(int(self._vars["ds100_poll_interval_ms"].get().strip()))

        ipaddress.ip_address(self._vars["digico_host"].get().strip())
        ipaddress.ip_address(self._vars["ds100_host"].get().strip())

        if start < 1 or end < 1:
            raise ValueError("Channel numbers must be >= 1")
        if start > end:
            raise ValueError("Start channel must be <= end channel")
        for port_name, port in [
            ("DiGiCo Send Port", digico_send),
            ("DiGiCo Listen Port", digico_listen),
        ]:
            if not 1 <= port <= 65535:
                raise ValueError(f"{port_name} must be between 1 and 65535")

        return BridgeSettings(
            start_channel=start,
            end_channel=end,
            digico_host=self._vars["digico_host"].get().strip(),
            digico_send_port=digico_send,
            digico_listen_port=digico_listen,
            ds100_host=self._vars["ds100_host"].get().strip(),
            ds100_poll_interval_ms=poll_ms,
        )

    def _set_form_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for entry in self._entries:
            entry.configure(state=state)

    def _start_bridge(self) -> None:
        try:
            settings = self._read_settings()
        except (ValueError, ipaddress.AddressValueError) as exc:
            messagebox.showerror("Invalid configuration", str(exc))
            return

        save_settings(settings)
        self._settings = settings

        self._bridge = BridgeApp(
            settings=settings,
            log=self._enqueue_log,
            on_activity=self._enqueue_activity,
        )
        try:
            self._bridge.start()
        except OSError as exc:
            messagebox.showerror("Start failed", str(exc))
            self._bridge = None
            return

        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._set_form_enabled(False)
        self._status_var.set("Running")

    def _stop_bridge(self) -> None:
        if self._bridge:
            self._bridge.stop()
            self._bridge = None

        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._set_form_enabled(True)
        self._status_var.set("Stopped")

    def _enqueue_log(self, message: str) -> None:
        self._log_queue.put(message)

    def _enqueue_activity(self, key: str) -> None:
        self._activity_queue.put(key)

    def _poll_queues(self) -> None:
        while True:
            try:
                self._append_log(self._log_queue.get_nowait())
            except queue.Empty:
                break

        while True:
            try:
                key = self._activity_queue.get_nowait()
                led = self._leds.get(key)
                if led:
                    led.flash()
            except queue.Empty:
                break

        self.root.after(80, self._poll_queues)

    def _append_log(self, message: str) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert("end", message + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _on_close(self) -> None:
        self._stop_bridge()
        self.root.destroy()


def run_gui() -> None:
    try:
        BridgeGUI().run()
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Bridge startup error", str(exc))
        raise
