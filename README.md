# Digico×Soundscape

Bidirectional OSC bridge between a **DiGiCo Quantum** console (External Control → DiGiCo Pad) and a **d&b Soundscape DS100** processor.

Maps configurable **DiGiCo Aux sends** to **DS100 En-Space Send** and/or **Function Group Routing 1–32**.

## Value range

All values are clamped to **-120.0 dB … +10.0 dB** in both directions so both devices use the same scale.

## Deployment

The bridge runs on a **dedicated computer**, separate from the DiGiCo console (offline software or physical desk on site). This is the intended production setup.

```
┌─────────────────┐     OSC      ┌──────────────────┐     OSC      ┌─────────┐
│ DiGiCo Console  │ ◄──────────► │  Bridge PC       │ ◄──────────► │  DS100  │
│ (offline/desk)  │  Pad ports   │  (this app)      │ 50010/50011  │         │
└─────────────────┘              └──────────────────┘              └─────────┘
```

- **DiGiCo IP** in the GUI = IP of the mixing console (not the bridge PC).
- **External Control** on the console → DiGiCo Pad → IP of the **bridge PC** (shown as **Bridge IP**).
- **DS100 IP** = IP of the physical Soundscape processor.
- All three devices must be on the same network.

## Beta releases

Download platform packages from the [GitHub Releases](https://github.com/sergeXYZ/Digico-x-Soundscape/releases) page.

| Zip | Platform | Start |
|---|---|---|
| `Digico-x-Soundscape-macos-arm64.zip` | macOS Apple Silicon | Double-click `Digico-x-Soundscape.app` |
| `Digico-x-Soundscape-windows-portable.zip` | Windows (no system Python) | `start_bridge.bat` |
| `Digico-x-Soundscape-linux.zip` | Linux x86_64 | `./install.sh` then `./Digico-x-Soundscape.sh` |
| `Digico-x-Soundscape-raspberrypi.zip` | Raspberry Pi (64-bit) | `./install.sh` then `./Digico-x-Soundscape.sh` |

Build all zips locally:

```bash
./scripts/pack_release.sh
```

**Notes**

- Windows EXE and Linux/Pi single-file binaries must be built **on that machine** (`build_exe.bat` / `./build_binary.sh`).
- macOS Gatekeeper may warn (unsigned app): right-click → Open.
- Launcher starts/stops the web server; configure the OSC bridge in the browser UI.
- Web UI: http://127.0.0.1:8765/

## Requirements (dev / source)

- Python 3.9+
- Network access to DiGiCo console and DS100

## Install (from source)

```bash
cd Digico-x-Soundscape
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (from source)

**macOS:** Double-click `run_bridge.command` — opens the desktop launcher.

**Windows:** Double-click `start_bridge.bat`

Optional: `python -m bridge.main --web-only` runs only the Flask UI (no launcher window).

## GUI fields

| Field | Description |
|---|---|
| Start / End Channel | Input channel range (DiGiCo Console panel) |
| DiGiCo IP / ports | Console IP and Pad Send/Receive ports |
| DS100 IP | Soundscape processor IP |
| Mappings | DiGiCo Aux → En-Space Send or Function Group Routing 1–32 |
| Aux Master → En-Space Zones | Optional: Aux Master fader/mute → En-Space zone 1–4 gain/mute |

DS100 OSC ports are fixed: **50010** (send), **50011** (listen).

## Manual

English user manual: [docs/MANUAL.md](docs/MANUAL.md) (PDF attached to [releases](https://github.com/sergeXYZ/Digico-x-Soundscape/releases)).

## DiGiCo setup

1. Open **Setup → External Control** on the Quantum.
2. Enable External Control.
3. **Add Device → DiGiCo Pad**.
4. Enter the **Bridge IP** of the computer running Digico×Soundscape.
5. Set Send / Receive ports to match the GUI.
6. Enable the device and load Pad commands.

## OSC mapping

Configurable in the GUI (**Add Mapping**).

| DiGiCo | DS100 |
|---|---|
| Aux send level | En-Space reverb send gain, or FG routing gain |
| Aux on/off | En-Space: −120 dB store/restore · FG: mute (Aux On = Mute Off) |

**DS100 polling:** configurable (**Polling Interval (ms)**, default 500).

Settings are saved to `settings.json` next to the app.

## License

MIT — see [LICENSE](LICENSE).
