#!/usr/bin/env bash
# DigiBridge — first-time setup (Linux / Raspberry Pi)
set -euo pipefail
cd "$(dirname "$0")"
unset PYTHONHOME PYTHONPATH

if ! command -v python3 >/dev/null 2>&1; then
  echo "FEHLER: python3 nicht gefunden. Bitte Python 3.9+ installieren."
  exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python $PY_VER"

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'; then
  echo "FEHLER: Python 3.9 oder neuer erforderlich."
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "FEHLER: python3-venv fehlt."
  echo "  Debian/Ubuntu/Pi:  sudo apt install python3-venv python3-pip"
  exit 1
fi

echo "Erstelle virtuelle Umgebung .venv ..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

echo
echo "Fertig. Starten mit:  ./Digico-x-Soundscape.sh"
echo "Web-UI: http://127.0.0.1:8765/"
