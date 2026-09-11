# Digico×Soundscape — User Manual

**Version:** 0.2.0-beta  
**Date:** 10 September 2026  
**Product:** Digico×Soundscape  
**Repository:** https://github.com/sergeXYZ/Digico-x-Soundscape

---

## 1. Overview

Digico×Soundscape is a bidirectional OSC bridge between a **DiGiCo Quantum** mixing console (External Control → DiGiCo Pad) and a **d&b audiotechnik DS100 Soundscape** processor.

It maps DiGiCo Aux send levels to DS100 parameters such as:

- **En-Space Send** (per sound object / matrix input)
- **Function Group Routing 1–32** (gain + mute)

Optionally, the DiGiCo **Aux Master** fader and mute can control all four **En-Space zone** gains and mutes.

All continuous levels are clamped to **-120.0 dB … +10.0 dB**.

---

## 2. System architecture

```
┌─────────────────┐     OSC      ┌──────────────────┐     OSC      ┌─────────┐
│ DiGiCo Console  │ ◄──────────► │  Bridge computer │ ◄──────────► │  DS100  │
│ (desk / offline)│  Pad ports   │ Digico×Soundscape│ 50010/50011  │         │
└─────────────────┘              └──────────────────┘              └─────────┘
```

| Setting | Meaning |
|---|---|
| **DiGiCo IP** | IP of the console (or offline PC), **not** the bridge |
| **Bridge IP** | IP of the computer running Digico×Soundscape (shown in the UI) |
| **DS100 IP** | IP of the Soundscape processor |

All three devices must share the same show network.

---

## 3. Installation

### 3.1 Download packages

From [GitHub Releases](https://github.com/sergeXYZ/Digico-x-Soundscape/releases):

| Package | Platform | How to start |
|---|---|---|
| `Digico-x-Soundscape-macos-arm64-*.zip` | macOS Apple Silicon | Run `./Digico-x-Soundscape` |
| `Digico-x-Soundscape-windows-portable-*.zip` | Windows | Double-click `start_bridge.bat` |
| `Digico-x-Soundscape-linux-*.zip` | Linux x86_64 | `./install.sh` then `./Digico-x-Soundscape.sh` |
| `Digico-x-Soundscape-raspberrypi-*.zip` | Raspberry Pi 64-bit | `./install.sh` then `./Digico-x-Soundscape.sh` |

Web UI: **http://127.0.0.1:8765/**

### 3.2 macOS notes

- Unsigned binary: if Gatekeeper blocks it, right-click → **Open**.
- Allow incoming UDP in the firewall for the DiGiCo listen port and DS100 port **50011**.

### 3.3 Windows notes

- Portable package includes Python; first start runs a one-time setup.
- Allow inbound UDP on the DiGiCo receive port and **50011** in Windows Firewall.

### 3.4 Linux / Raspberry Pi

```bash
sudo apt install python3 python3-venv python3-pip
chmod +x install.sh Digico-x-Soundscape.sh
./install.sh
./Digico-x-Soundscape.sh
```

### 3.5 Run from source (developers)

```bash
cd Digico-x-Soundscape
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m bridge.main
```

---

## 4. DiGiCo console setup

1. Open **Setup → External Control**.
2. Enable External Control.
3. **Add Device → DiGiCo Pad**.
4. Set the device IP to the **Bridge IP** shown in Digico×Soundscape.
5. Match **Send** / **Receive** ports with the GUI:
   - Console **Send** = Bridge **Receive (Console → Bridge)**
   - Console **Receive** = Bridge **Send (Bridge → Console)**
6. Enable the device and load Pad commands.

Example (common defaults):

| Side | Port |
|---|---|
| Bridge listen (Receive) | 8000 |
| Bridge send | 9000 |

---

## 5. DS100 setup

- DS100 OSC ports are **fixed**:
  - Bridge → DS100: **50010**
  - DS100 → Bridge: **50011**
- Ensure Companion or other apps do not occupy **50011** on the bridge computer unless you intend to share carefully.
- Enter the DS100 IP in the GUI.

---

## 6. Using the web UI

1. Start Digico×Soundscape — the browser opens http://127.0.0.1:8765/
2. Configure **Start Channel** / **End Channel** (inside the DiGiCo Console panel).
3. Set DiGiCo and DS100 IPs and Digico ports.
4. Add **Mappings** (Aux → DS100 parameter).
5. Optionally enable **Aux Master → En-Space Zones**.
6. Click **Start**.
7. Use **Test** to probe connections; **Stop** to stop the OSC bridge. Close the desktop launcher (or click **Stop Server**) to shut down the web server.

Status LEDs:

- Header: DiGiCo / DS100 RX & TX activity
- Per mapping: Act LED when that mapping syncs
- Aux Master panel: LED when master→zone link is active

The **Log** section is collapsed by default; click **Log** to expand.

---

## 7. Mappings

Each mapping links one DiGiCo Aux to one DS100 parameter for every channel in Start–End.

### 7.1 En-Space Send

| Direction | Behaviour |
|---|---|
| Digico Aux send level ↔ DS100 | `/dbaudio1/matrixinput/reverbsendgain/{N}` |
| Digico Aux Off | Store last level; force DS100 to **-120 dB** |
| Digico Aux On | Restore stored level |

### 7.2 Function Group Routing 1–32

| Direction | Behaviour |
|---|---|
| Level | `/dbaudio1/soundobjectrouting/gain/{FG}/{N}` |
| Digico Aux On / Off | Maps to mute off / mute on (`…/mute/{FG}/{N}`) — **no store** |
| Aux On = Mute Off | As designed for DS100 FG mute |

Click **+ Add Mapping** for additional Aux → parameter pairs. At least one mapping is required.

---

## 8. Aux Master → En-Space Zones

Enable switch in the UI. When enabled for a chosen Aux Master:

| Digico | DS100 (zones 1–4) |
|---|---|
| `/Aux_Outputs/{AUX}/fader` | `/dbaudio1/reverbinputprocessing/gain/1` … `/4` |
| `/Aux_Outputs/{AUX}/mute` | `/dbaudio1/reverbinputprocessing/mute/1` … `/4` |

**One-way only (console → DS100).** En-Space zone gain/mute are not polled back from the DS100 — there is no reverse path for this link.

---

## 9. Polling

- **Polling Interval (ms):** 100–60000 (default 500).
- Only mapped channels in the Start–End range are polled on the DS100 (Companion-style: En-Space Send / FG routing).
- Aux Master → En-Space Zones is **not** included in polling.

---

## 10. Settings file

Settings are saved to `settings.json` next to the application when you click **Start**.

---

## 11. Troubleshooting

| Symptom | Check |
|---|---|
| No Digico activity | Pad IP = Bridge IP; ports swapped correctly; External Control enabled |
| Digico RX but no DS100 | DS100 IP; ports 50010/50011 free; network route |
| Reverse Digico update missing | Windows firewall inbound on Digico receive port |
| Port already in use | Stop Companion / Protokol / previous Digico×Soundscape instance |
| macOS won’t open binary | Right-click → Open (unsigned) |

---

## 12. License

MIT — see `LICENSE` in the repository.

---

*Digico×Soundscape — manual dated 10 September 2026.*
