"""Web-based GUI (browser) for Digico×Soundscape."""

from __future__ import annotations

import ipaddress
import os
import threading
import time
import webbrowser
from typing import Any

from flask import Flask, jsonify, render_template_string, request

from bridge.bridge_app import BridgeApp
from bridge.constants import DS100_LISTEN_PORT, DS100_SEND_PORT
from bridge.mapping import (
    DIGICO_AUX_MAX,
    FUNCTION_GROUP_MAX,
    MappingSpec,
    ds100_param_choices,
    mapping_from_dict,
)
from bridge.net_utils import get_local_ip
from bridge.settings import BridgeSettings, clamp_poll_interval_ms, load_settings, save_settings

APP_NAME = "Digico×Soundscape"

HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Digico×Soundscape</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #12141a;
  --bg-panel: #1a1d26;
  --bg-row: #222633;
  --bg-row-hover: #2a2f3d;
  --border: #32384a;
  --text: #e8eaf0;
  --muted: #9aa3b5;
  --accent: #3d9cf0;
  --accent-dim: #2a6fa8;
  --ok: #3ecf8e;
  --warn: #e6b84d;
  --err: #e85d5d;
  --font: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", "SF Mono", ui-monospace, monospace;
}
* { box-sizing: border-box; }
html, body {
  margin: 0; min-height: 100%;
  background: var(--bg); color: var(--text);
  font-family: var(--font); font-size: 14px;
}
button, input, select { font: inherit; color: inherit; }
.status-bar {
  position: sticky; top: 0; z-index: 20;
  display: flex; flex-wrap: wrap; align-items: center; gap: 12px 18px;
  padding: 10px 16px; background: #0e1015; border-bottom: 1px solid var(--border);
}
.brand { font-weight: 700; letter-spacing: 0.02em; font-size: 15px; }
.brand .x { color: var(--accent); margin: 0 1px; }
.pill {
  background: var(--bg-row); border: 1px solid var(--border);
  border-radius: 4px; padding: 2px 8px; font-size: 12px;
}
.mono { font-family: var(--mono); font-size: 13px; }
.header-actions { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.btn {
  background: var(--bg-row); border: 1px solid var(--border);
  border-radius: 4px; padding: 6px 12px; cursor: pointer;
}
.btn:hover { background: var(--bg-row-hover); }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn.primary { background: var(--accent-dim); border-color: var(--accent); }
.btn.danger { background: #3d1e1e; border-color: var(--err); color: #f0b0b0; }
.btn.ok { background: #1e3d2a; border-color: var(--ok); color: var(--ok); }
.led-wrap { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); font-size: 12px; }
.led {
  width: 10px; height: 10px; border-radius: 50%; background: #3a4050;
  box-shadow: inset 0 0 0 1px #0006; flex-shrink: 0;
}
.led.on { background: var(--ok); }
.led.recent { background: var(--accent); }
.conn-dot {
  width: 10px; height: 10px; border-radius: 50%; display: inline-block;
  background: #3a4050; border: 1px solid #555; margin-right: 6px;
}
.conn-dot.ok { background: var(--ok); border-color: #2a9a68; box-shadow: 0 0 6px #3ecf8e88; }
.layout { max-width: 1100px; margin: 0 auto; padding: 16px; display: grid; gap: 14px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 800px) { .row { grid-template-columns: 1fr; } }
.panel {
  background: var(--bg-panel); border: 1px solid var(--border);
  border-radius: 4px; padding: 14px 16px;
}
.panel h2 {
  margin: 0 0 12px; font-size: 12px; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--muted); font-weight: 600;
  display: flex; align-items: center;
}
.panel h2.toggle {
  cursor: pointer; user-select: none; margin-bottom: 0;
}
.panel h2.toggle:hover { color: var(--text); }
.chevron { display: inline-block; width: 1em; margin-right: 6px; color: var(--accent); }
label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
input[type=text], input[type=number], select {
  width: 100%; padding: 8px 10px; margin-bottom: 10px;
  background: var(--bg-row); border: 1px solid var(--border); border-radius: 4px;
}
input:disabled, select:disabled { opacity: 0.55; }
input.no-spin::-webkit-outer-spin-button,
input.no-spin::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
input.no-spin {
  -moz-appearance: textfield;
  appearance: textfield;
}
.port-line {
  display: flex; align-items: center; gap: 10px; margin: 8px 0; font-size: 0.92rem;
}
.port-line .lbl { flex: 1; color: var(--muted); }
.port-line .port, .port-line input { width: 90px; margin: 0; font-family: var(--mono); }
.channels { display: flex; gap: 14px; flex-wrap: wrap; }
.ch-field { width: 140px; }
.mapping-row {
  display: grid;
  grid-template-columns: auto 1fr 1fr auto;
  gap: 10px; align-items: end;
  padding: 10px; margin-bottom: 8px;
  background: var(--bg-row); border-radius: 3px; border: 1px solid var(--border);
}
.mapping-led-col {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding-bottom: 14px; min-width: 28px;
}
.mapping-led-col .lbl-mini {
  font-size: 9px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted);
}
.mapping-row .remove { margin-bottom: 10px; }
.mapping-toolbar { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.hint { color: var(--muted); font-size: 12px; margin: 0 0 10px; }
.log-body { margin-top: 12px; }
.log-body.collapsed { display: none; }
.log-box {
  background: #0e1015; border: 1px solid var(--border); border-radius: 4px;
  font-family: var(--mono); font-size: 12px; color: var(--muted);
  height: 260px; overflow: auto; padding: 10px; white-space: pre-wrap;
}
.sub { color: var(--accent); font-size: 13px; }
</style>
</head>
<body>
<header class="status-bar">
  <div class="brand">Digico<span class="x">×</span>Soundscape</div>
  <span class="pill" id="statusPill">Stopped</span>
  <span class="mono sub" id="bridgeIp">—</span>
  <div class="header-actions">
    <span class="led-wrap"><span class="led" id="led_digico_rx"></span> DiGiCo RX</span>
    <span class="led-wrap"><span class="led" id="led_digico_tx"></span> DiGiCo TX</span>
    <span class="led-wrap"><span class="led" id="led_ds100_rx"></span> DS100 RX</span>
    <span class="led-wrap"><span class="led" id="led_ds100_tx"></span> DS100 TX</span>
    <button type="button" class="btn ok" id="startBtn" onclick="startBridge()">Start</button>
    <button type="button" class="btn danger" id="stopBtn" onclick="stopBridge()" disabled>Stop</button>
    <button type="button" class="btn" id="testBtn" onclick="testConn()" disabled>Test</button>
    <button type="button" class="btn danger" id="quitBtn" onclick="quitServer()">Quit</button>
  </div>
</header>

<main class="layout">
  <div class="channels">
    <div class="ch-field"><label>Start Kanal</label><input type="number" id="start_channel" min="1"></div>
    <div class="ch-field"><label>End Kanal</label><input type="number" id="end_channel" min="1"></div>
  </div>

  <div class="row">
    <div class="panel">
      <h2><span class="conn-dot" id="conn_digico"></span> DiGiCo Console</h2>
      <label>IP Address</label>
      <input type="text" id="digico_host">
      <div class="port-line">
        <span class="lbl">Receive (Console → Bridge)</span>
        <input type="number" class="no-spin" id="digico_listen_port" min="1" max="65535">
      </div>
      <div class="port-line">
        <span class="lbl">Send (Bridge → Console)</span>
        <input type="number" class="no-spin" id="digico_send_port" min="1" max="65535">
      </div>
    </div>
    <div class="panel">
      <h2><span class="conn-dot" id="conn_ds100"></span> DS100 Soundscape</h2>
      <label>IP Address</label>
      <input type="text" id="ds100_host">
      <div class="port-line">
        <span class="lbl">Receive (DS100 → Bridge)</span>
        <span class="port mono" id="ds100_listen_display"></span>
      </div>
      <div class="port-line">
        <span class="lbl">Send (Bridge → DS100)</span>
        <span class="port mono" id="ds100_send_display"></span>
      </div>
      <div class="port-line">
        <span class="lbl">Polling Interval (ms)</span>
        <input type="number" id="ds100_poll_interval_ms" min="100" max="60000" step="50">
      </div>
    </div>
  </div>

  <div class="panel">
    <h2>Mappings</h2>
    <p class="hint">DiGiCo Aux → DS100 Parameter. En-Space Send: Aux Off speichert Level und setzt −120 dB.
      Function Group Routing: Aux On = Mute Off (kein Zwischenspeicher).</p>
    <div class="mapping-toolbar">
      <button type="button" class="btn primary" id="addMappingBtn" onclick="addMapping()">+ Add Mapping</button>
    </div>
    <div id="mappings"></div>
  </div>

  <div class="panel">
    <h2 class="toggle" onclick="toggleLog()">
      <span class="chevron" id="logChevron">▶</span> Log
    </h2>
    <div class="log-body collapsed" id="logBody">
      <div class="log-box" id="log"></div>
    </div>
  </div>
</main>

<script>
const DIGICO_AUX_MAX = __DIGICO_AUX_MAX__;
const FG_MAX = __FG_MAX__;
const DS100_CHOICES = __DS100_CHOICES__;
const fieldIds = ['start_channel','end_channel','digico_host','digico_send_port','digico_listen_port','ds100_host','ds100_poll_interval_ms'];
const ledKeys = ['digico_rx','digico_tx','ds100_rx','ds100_tx'];
let mappings = [];
let lastShownStartError = null;
let logOpen = false;
let lastActivity = {};

function uid() { return Math.random().toString(16).slice(2, 12); }

function toggleLog() {
  logOpen = !logOpen;
  document.getElementById('logBody').classList.toggle('collapsed', !logOpen);
  document.getElementById('logChevron').textContent = logOpen ? '▼' : '▶';
}

function ds100SelectHtml(selectedKind, selectedFg) {
  let html = '<select class="ds100-param">';
  DS100_CHOICES.forEach(c => {
    let sel = false;
    if (c.id === 'enspace_send') sel = selectedKind === 'enspace_send';
    else sel = selectedKind === 'fg_routing' && Number(selectedFg) === Number(c.function_group);
    html += `<option value="${c.id}" ${sel ? 'selected' : ''}>${c.label}</option>`;
  });
  html += '</select>';
  return html;
}

function auxSelectHtml(selected) {
  let html = '<select class="digico-aux">';
  for (let a = 1; a <= DIGICO_AUX_MAX; a++) {
    html += `<option value="${a}" ${Number(selected)===a?'selected':''}>Aux ${a}</option>`;
  }
  html += '</select>';
  return html;
}

function renderMappings() {
  const root = document.getElementById('mappings');
  root.innerHTML = '';
  mappings.forEach((m, idx) => {
    const row = document.createElement('div');
    row.className = 'mapping-row';
    row.dataset.idx = idx;
    row.dataset.mapId = m.id;
    row.innerHTML = `
      <div class="mapping-led-col">
        <span class="lbl-mini">Act</span>
        <span class="led" id="led_map_${m.id}"></span>
      </div>
      <div><label>DiGiCo Aux</label>${auxSelectHtml(m.digico_aux)}</div>
      <div><label>DS100 Parameter</label>${ds100SelectHtml(m.ds100_kind, m.function_group)}</div>
      <button type="button" class="btn danger remove" onclick="removeMapping(${idx})">Remove</button>`;
    root.appendChild(row);
  });
  bindMappingInputs();
  updateMappingLeds(lastActivity, Date.now()/1000);
}

function bindMappingInputs() {
  document.querySelectorAll('.mapping-row').forEach(row => {
    const idx = Number(row.dataset.idx);
    row.querySelector('.digico-aux').onchange = (e) => {
      mappings[idx].digico_aux = Number(e.target.value);
    };
    row.querySelector('.ds100-param').onchange = (e) => {
      const v = e.target.value;
      if (v === 'enspace_send') {
        mappings[idx].ds100_kind = 'enspace_send';
        mappings[idx].function_group = null;
      } else {
        const fg = Number(v.split(':')[1]);
        mappings[idx].ds100_kind = 'fg_routing';
        mappings[idx].function_group = fg;
      }
    };
  });
}

function addMapping() {
  mappings.push({ id: uid(), digico_aux: 1, ds100_kind: 'enspace_send', function_group: null });
  renderMappings();
}
function removeMapping(idx) {
  if (mappings.length <= 1) { alert('Mindestens ein Mapping nötig'); return; }
  mappings.splice(idx, 1);
  renderMappings();
}

function setLedState(el, age) {
  if (!el) return;
  el.classList.remove('on', 'recent');
  if (age != null && age < 1.5) el.classList.add('on');
  else if (age != null && age < 10) el.classList.add('recent');
}

function updateConnections(d) {
  const conn = d.connections || {};
  ['digico','ds100'].forEach(name => {
    const dot = document.getElementById('conn_' + name);
    if (dot) dot.classList.toggle('ok', !!conn[name]);
  });
}

function updateMappingLeds(last, now) {
  mappings.forEach(m => {
    const key = 'map:' + m.id;
    const age = last[key] != null ? (now - last[key]) : null;
    setLedState(document.getElementById('led_map_' + m.id), age);
  });
}

function updateActivity(d) {
  const now = d.server_time || (Date.now()/1000);
  lastActivity = d.activity_last || {};
  ledKeys.forEach(key => {
    const age = lastActivity[key] != null ? (now - lastActivity[key]) : null;
    setLedState(document.getElementById('led_' + key), age);
  });
  updateMappingLeds(lastActivity, now);
}

async function poll() {
  try {
    const r = await fetch('/api/state');
    const d = await r.json();
    setRunning(d);
    if (logOpen) {
      document.getElementById('log').textContent = (d.log || []).join('\\n');
      const logEl = document.getElementById('log');
      logEl.scrollTop = logEl.scrollHeight;
    }
    updateActivity(d);
    updateConnections(d);
    if (d.bridge_ip) {
      document.getElementById('bridgeIp').textContent = 'Bridge IP: ' + d.bridge_ip;
    }
  } catch (e) {}
  setTimeout(poll, 300);
}

function setFields(data) {
  fieldIds.forEach(id => { if (data[id] !== undefined) document.getElementById(id).value = data[id]; });
  document.getElementById('bridgeIp').textContent = 'Bridge IP: ' + (data.bridge_ip || '—');
  document.getElementById('ds100_listen_display').textContent = data.ds100_listen_port;
  document.getElementById('ds100_send_display').textContent = data.ds100_send_port;
  mappings = (data.mappings && data.mappings.length) ? data.mappings : [{id:uid(), digico_aux:1, ds100_kind:'enspace_send', function_group:null}];
  renderMappings();
}

function setRunning(d) {
  const running = d.running;
  const starting = d.starting;
  document.getElementById('startBtn').disabled = running || starting;
  document.getElementById('stopBtn').disabled = !running && !starting;
  document.getElementById('testBtn').disabled = !running;
  document.getElementById('addMappingBtn').disabled = running || starting;
  fieldIds.forEach(id => document.getElementById(id).disabled = running || starting);
  document.querySelectorAll('#mappings select, #mappings button').forEach(el => el.disabled = running || starting);
  const pill = document.getElementById('statusPill');
  if (starting) pill.textContent = 'Starting…';
  else if (running) pill.textContent = 'Running';
  else pill.textContent = d.start_error ? 'Error' : 'Stopped';
  if (d.start_error && d.start_error !== lastShownStartError) {
    lastShownStartError = d.start_error;
    alert('Start failed: ' + d.start_error);
  }
  if (running) lastShownStartError = null;
}

function getForm() {
  const o = {};
  fieldIds.forEach(id => o[id] = document.getElementById(id).value);
  o.mappings = mappings.map(m => ({
    id: m.id,
    digico_aux: Number(m.digico_aux),
    ds100_kind: m.ds100_kind,
    function_group: m.ds100_kind === 'fg_routing' ? Number(m.function_group) : null
  }));
  return o;
}

async function startBridge() {
  document.getElementById('startBtn').disabled = true;
  try {
    const r = await fetch('/api/start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(getForm())});
    const d = await r.json();
    if (!d.ok) alert(d.error || 'Start failed');
  } catch (e) { alert(String(e)); }
}
async function stopBridge() {
  await fetch('/api/stop', {method:'POST'});
}
async function testConn() {
  await fetch('/api/test', {method:'POST'});
}
async function quitServer() {
  if (!confirm('Server beenden und Digico×Soundscape schließen?')) return;
  try {
    await fetch('/api/quit', {method:'POST'});
  } catch (e) {}
  document.body.innerHTML = '<div style="padding:40px;font-family:IBM Plex Sans,sans-serif;background:#12141a;color:#e8eaf0;min-height:100vh">Server beendet. Fenster kann geschlossen werden.</div>';
}

fetch('/api/settings').then(r=>r.json()).then(setFields).then(poll);
</script>
</body>
</html>
"""


class WebBridgeServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self._bridge: BridgeApp | None = None
        self._lock = threading.Lock()
        self._log_lines: list[str] = ["Ready. Click Start."]
        self._activity_flash: list[str] = []
        self._activity_last: dict[str, float] = {}
        self._activity_counts: dict[str, int] = {}
        self._running = False
        self._starting = False
        self._start_error: str | None = None
        self._started_at: float | None = None

        self.app.add_url_rule("/", view_func=self._index)
        self.app.add_url_rule("/api/settings", view_func=self._api_settings)
        self.app.add_url_rule("/api/state", view_func=self._api_state)
        self.app.add_url_rule("/api/start", view_func=self._api_start, methods=["POST"])
        self.app.add_url_rule("/api/stop", view_func=self._api_stop, methods=["POST"])
        self.app.add_url_rule("/api/test", view_func=self._api_test, methods=["POST"])
        self.app.add_url_rule("/api/quit", view_func=self._api_quit, methods=["POST"])

    def _index(self) -> str:
        import json

        html = HTML.replace("__DIGICO_AUX_MAX__", str(DIGICO_AUX_MAX))
        html = html.replace("__FG_MAX__", str(FUNCTION_GROUP_MAX))
        html = html.replace("__DS100_CHOICES__", json.dumps(ds100_param_choices()))
        return render_template_string(html)

    def _api_settings(self) -> Any:
        s = load_settings()
        return jsonify(
            {
                "start_channel": s.start_channel,
                "end_channel": s.end_channel,
                "digico_host": s.digico_host,
                "digico_send_port": s.digico_send_port,
                "digico_listen_port": s.digico_listen_port,
                "ds100_host": s.ds100_host,
                "ds100_poll_interval_ms": s.ds100_poll_interval_ms,
                "ds100_send_port": DS100_SEND_PORT,
                "ds100_listen_port": DS100_LISTEN_PORT,
                "bridge_ip": get_local_ip(target_host=s.digico_host),
                "mappings": [
                    {
                        "id": m.id,
                        "digico_aux": m.digico_aux,
                        "ds100_kind": m.ds100_kind,
                        "function_group": m.function_group,
                    }
                    for m in s.mappings
                ],
            }
        )

    def _api_state(self) -> Any:
        with self._lock:
            activity = list(self._activity_flash)
            self._activity_flash.clear()
            uptime = time.time() - self._started_at if self._started_at else 0
            connections = {"digico": False, "ds100": False}
            digico_host = load_settings().digico_host
            if self._bridge:
                connections = self._bridge.connection_status()
                digico_host = self._bridge.settings.digico_host
            return jsonify(
                {
                    "running": self._running,
                    "starting": self._starting,
                    "start_error": self._start_error,
                    "log": list(self._log_lines),
                    "activity": activity,
                    "activity_last": dict(self._activity_last),
                    "activity_counts": dict(self._activity_counts),
                    "connections": connections,
                    "server_time": time.time(),
                    "uptime_sec": uptime,
                    "bridge_ip": get_local_ip(target_host=digico_host),
                }
            )

    def _api_test(self) -> Any:
        with self._lock:
            bridge = self._bridge
            if not bridge or not self._running:
                return jsonify(ok=False, error="Bridge is not running")

        def _test_worker() -> None:
            bridge.test_connections()

        threading.Thread(target=_test_worker, name="bridge-test", daemon=True).start()
        return jsonify(ok=True)

    def _parse_mappings(self, data: dict[str, Any]) -> list[MappingSpec]:
        raw = data.get("mappings")
        if not isinstance(raw, list) or not raw:
            raise ValueError("At least one mapping is required")
        mappings = [mapping_from_dict(m) for m in raw]
        return mappings

    def _api_start(self) -> Any:
        data = request.get_json(silent=True) or {}
        try:
            mappings = self._parse_mappings(data)
            settings = BridgeSettings(
                start_channel=int(data["start_channel"]),
                end_channel=int(data["end_channel"]),
                digico_host=str(data["digico_host"]).strip(),
                digico_send_port=int(data["digico_send_port"]),
                digico_listen_port=int(data["digico_listen_port"]),
                ds100_host=str(data["ds100_host"]).strip(),
                ds100_poll_interval_ms=clamp_poll_interval_ms(
                    int(data.get("ds100_poll_interval_ms", 500))
                ),
                mappings=mappings,
            )
            ipaddress.ip_address(settings.digico_host)
            ipaddress.ip_address(settings.ds100_host)
            if settings.start_channel > settings.end_channel:
                raise ValueError("Start channel must be <= end channel")
        except (ValueError, KeyError, TypeError, ipaddress.AddressValueError) as exc:
            return jsonify(ok=False, error=str(exc))

        save_settings(settings)

        with self._lock:
            if self._running or self._starting:
                return jsonify(ok=False, error="Bridge already running or starting")
            self._starting = True
            self._start_error = None

        def _start_worker() -> None:
            bridge = BridgeApp(
                settings=settings,
                log=self._log,
                on_activity=self._activity,
            )
            try:
                bridge.start()
                with self._lock:
                    self._bridge = bridge
                    self._running = True
                    self._starting = False
                    self._started_at = time.time()
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._starting = False
                    self._start_error = str(exc)
                self._log(f"Start failed: {exc}")

        threading.Thread(target=_start_worker, name="bridge-start", daemon=True).start()
        return jsonify(ok=True)

    def _api_stop(self) -> Any:
        with self._lock:
            bridge = self._bridge
            self._bridge = None
            self._running = False
            self._starting = False
            self._started_at = None
        if bridge:
            bridge.stop()
        return jsonify(ok=True)

    def _api_quit(self) -> Any:
        """Stop OSC bridge and terminate the web server process."""
        with self._lock:
            bridge = self._bridge
            self._bridge = None
            self._running = False
            self._starting = False
        if bridge:
            try:
                bridge.stop()
            except Exception:  # noqa: BLE001
                pass
        self._log("Quit requested — shutting down.")

        def _exit() -> None:
            time.sleep(0.35)
            os._exit(0)

        threading.Thread(target=_exit, name="quit", daemon=True).start()
        return jsonify(ok=True)

    def _log(self, message: str) -> None:
        with self._lock:
            self._log_lines.append(message)
            if len(self._log_lines) > 500:
                self._log_lines = self._log_lines[-500:]

    def _activity(self, key: str) -> None:
        now = time.time()
        with self._lock:
            self._activity_flash.append(key)
            self._activity_last[key] = now
            self._activity_counts[key] = self._activity_counts.get(key, 0) + 1

    def run(self, open_browser: bool = True) -> None:
        url = f"http://{self.host}:{self.port}/"
        self._log(f"Web UI: {url}")
        s = load_settings()
        self._log(
            f"Bridge IP for DiGiCo Pad: {get_local_ip(target_host=s.digico_host)}"
        )
        if open_browser:
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        self.app.run(
            host=self.host,
            port=self.port,
            debug=False,
            use_reloader=False,
            threaded=True,
        )


def run_web_gui() -> None:
    WebBridgeServer().run()
