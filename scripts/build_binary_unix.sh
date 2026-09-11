#!/usr/bin/env bash
# Build Digico×Soundscape with PyInstaller (macOS / Linux / Raspberry Pi).
# Run on the target architecture — does not cross-compile.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Avoid broken pip when another project's PYTHONPATH/PYTHONHOME is set (e.g. zerAI).
unset PYTHONHOME PYTHONPATH
export PYTHONUNBUFFERED=1

APP_SLUG="Digico-x-Soundscape"

if ! command -v python3 >/dev/null 2>&1; then
  echo "FEHLER: python3 nicht gefunden."
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
"$ROOT/.venv/bin/python" -m pip install -q --upgrade pip
"$ROOT/.venv/bin/python" -m pip install -q -r requirements.txt -r requirements-build.txt

echo "PyInstaller: ${APP_SLUG} ..."
"$ROOT/.venv/bin/python" -m PyInstaller digibridge.spec --noconfirm --clean

# Default settings next to the built app / binary
write_settings() {
  local dest="$1"
  cat > "$dest" <<'EOF'
{
  "start_channel": 1,
  "end_channel": 1,
  "digico_host": "192.168.1.10",
  "digico_send_port": 9000,
  "digico_listen_port": 8000,
  "ds100_host": "192.168.1.20",
  "ds100_poll_interval_ms": 500
}
EOF
}

if [ -d "dist/${APP_SLUG}.app" ]; then
  # macOS .app — settings live next to the bundle
  if [ -f settings.json ]; then
    cp -f settings.json "dist/settings.json"
  else
    write_settings "dist/settings.json"
  fi
  echo
  echo "Fertig: $ROOT/dist/${APP_SLUG}.app"
  echo "settings.json liegt in dist/ (neben der .app ablegen)"
elif [ -f "dist/${APP_SLUG}" ]; then
  if [ -f settings.json ]; then
    cp -f settings.json dist/settings.json
  else
    write_settings dist/settings.json
  fi
  echo
  echo "Fertig: $ROOT/dist/${APP_SLUG}"
  echo "Optional: settings.json liegt in dist/"
else
  echo "FEHLER: Build-Artefakt nicht gefunden in dist/" >&2
  exit 1
fi
