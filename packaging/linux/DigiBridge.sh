#!/usr/bin/env bash
# DigiBridge — start Web UI
set -euo pipefail
cd "$(dirname "$0")"
unset PYTHONHOME PYTHONPATH
export PYTHONUNBUFFERED=1

if [ ! -d .venv ]; then
  echo "Noch nicht installiert — starte install.sh ..."
  ./install.sh
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Digico×Soundscape — Launcher startet…"
exec ./.venv/bin/python -m bridge.main
