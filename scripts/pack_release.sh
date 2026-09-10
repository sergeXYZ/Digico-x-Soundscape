#!/usr/bin/env bash
# Assemble Digico×Soundscape release zips for macOS, Windows, Linux, Raspberry Pi.
# macOS binary is built here; Windows uses portable-staging; Linux/Pi are source installers.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

unset PYTHONHOME PYTHONPATH
export PYTHONUNBUFFERED=1

APP_SLUG="Digico-x-Soundscape"
VERSION="${DIGIBRIDGE_VERSION:-${VERSION:-$(date +%Y%m%d)}}"
RELEASES="$ROOT/releases"
STAGE="$ROOT/releases/.staging"
ARCH="$(uname -m)"

die() { echo "FEHLER: $*" >&2; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "$1 fehlt"; }

need_cmd zip
need_cmd python3

rm -rf "$STAGE"
mkdir -p "$RELEASES" "$STAGE"

default_settings() {
  local dest="$1"
  cat > "$dest" <<'EOF'
{
  "start_channel": 1,
  "end_channel": 64,
  "digico_host": "192.168.1.10",
  "digico_send_port": 9000,
  "digico_listen_port": 8000,
  "ds100_host": "192.168.1.20",
  "ds100_poll_interval_ms": 500
}
EOF
}

copy_bridge_tree() {
  local dest="$1"
  mkdir -p "$dest"
  rsync -a --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    "$ROOT/bridge/" "$dest/bridge/"
  cp "$ROOT/requirements.txt" "$dest/"
  cp "$ROOT/run_bridge.py" "$dest/"
  default_settings "$dest/settings.json"
}

zip_dir() {
  local src="$1"
  local zipname="$2"
  local out="$RELEASES/$zipname"
  rm -f "$out"
  (
    cd "$(dirname "$src")"
    zip -rq "$out" "$(basename "$src")"
  )
  echo "  → $out ($(du -h "$out" | awk '{print $1}'))"
}

# ---------------------------------------------------------------------------
# macOS (PyInstaller on this machine)
# ---------------------------------------------------------------------------
echo "==> macOS binary ($ARCH)"
chmod +x "$ROOT/scripts/build_binary_unix.sh"
"$ROOT/scripts/build_binary_unix.sh"

MAC_NAME="${APP_SLUG}-macos-${ARCH}"
MAC_DIR="$STAGE/$MAC_NAME"
rm -rf "$MAC_DIR"
mkdir -p "$MAC_DIR"
cp "$ROOT/dist/${APP_SLUG}" "$MAC_DIR/${APP_SLUG}"
chmod +x "$MAC_DIR/${APP_SLUG}"
default_settings "$MAC_DIR/settings.json"
cp "$ROOT/packaging/macos/README.txt" "$MAC_DIR/README.txt"
zip_dir "$MAC_DIR" "${MAC_NAME}-${VERSION}.zip"
cp -f "$RELEASES/${MAC_NAME}-${VERSION}.zip" "$RELEASES/${MAC_NAME}.zip"

# ---------------------------------------------------------------------------
# Windows portable
# ---------------------------------------------------------------------------
echo "==> Windows portable"
STAGING_PY="$ROOT/portable-staging"
[ -d "$STAGING_PY/python" ] || die "portable-staging/python fehlt"
[ -d "$STAGING_PY/wheels" ] || die "portable-staging/wheels fehlt"
[ -f "$STAGING_PY/get-pip.py" ] || die "portable-staging/get-pip.py fehlt"

WIN_NAME="${APP_SLUG}-windows-portable"
WIN_DIR="$STAGE/$WIN_NAME"
rm -rf "$WIN_DIR"
mkdir -p "$WIN_DIR"

copy_bridge_tree "$WIN_DIR"
cp "$ROOT/requirements-build.txt" "$WIN_DIR/"
cp "$ROOT/digibridge.spec" "$WIN_DIR/"
cp "$ROOT/start_bridge.bat" "$WIN_DIR/"
cp "$ROOT/setup_portable.bat" "$WIN_DIR/"
cp "$ROOT/build_exe.bat" "$WIN_DIR/"
cp "$ROOT/start_DigiBridge.bat" "$WIN_DIR/start_${APP_SLUG}.bat" 2>/dev/null || true
cp "$ROOT/WINDOWS-ANLEITUNG.txt" "$WIN_DIR/"
cp "$ROOT/packaging/windows/README.txt" "$WIN_DIR/README.txt"

rsync -a "$STAGING_PY/python/" "$WIN_DIR/python/"
rsync -a "$STAGING_PY/wheels/" "$WIN_DIR/wheels/"
cp "$STAGING_PY/get-pip.py" "$WIN_DIR/"

zip_dir "$WIN_DIR" "${WIN_NAME}-${VERSION}.zip"
cp -f "$RELEASES/${WIN_NAME}-${VERSION}.zip" "$RELEASES/${WIN_NAME}.zip"

# ---------------------------------------------------------------------------
# Shared Unix source package helper
# ---------------------------------------------------------------------------
pack_unix_source() {
  local name="$1"
  local readme_src="$2"
  local dir="$STAGE/$name"
  rm -rf "$dir"
  mkdir -p "$dir"
  copy_bridge_tree "$dir"
  cp "$ROOT/requirements-build.txt" "$dir/"
  cp "$ROOT/digibridge.spec" "$dir/"
  cp "$ROOT/packaging/linux/install.sh" "$dir/"
  cp "$ROOT/packaging/linux/DigiBridge.sh" "$dir/${APP_SLUG}.sh"
  cat > "$dir/build_binary.sh" <<EOF
#!/usr/bin/env bash
# Build Digico×Soundscape single-file binary on this machine (Linux / Pi / macOS).
set -euo pipefail
cd "\$(dirname "\$0")"
unset PYTHONHOME PYTHONPATH
export PYTHONUNBUFFERED=1
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
./.venv/bin/python -m pip install -q --upgrade pip
./.venv/bin/python -m pip install -q -r requirements.txt -r requirements-build.txt
./.venv/bin/python -m PyInstaller digibridge.spec --noconfirm --clean
cp -f settings.json dist/settings.json 2>/dev/null || true
echo "Fertig: \$(pwd)/dist/${APP_SLUG}"
EOF
  cp "$readme_src" "$dir/README.txt"
  chmod +x "$dir/install.sh" "$dir/${APP_SLUG}.sh" "$dir/build_binary.sh"
  zip_dir "$dir" "${name}-${VERSION}.zip"
  cp -f "$RELEASES/${name}-${VERSION}.zip" "$RELEASES/${name}.zip"
}

echo "==> Linux source installer"
pack_unix_source "${APP_SLUG}-linux" "$ROOT/packaging/linux/README.txt"

echo "==> Raspberry Pi source installer"
pack_unix_source "${APP_SLUG}-raspberrypi" "$ROOT/packaging/raspberrypi/README.txt"

rm -rf "$STAGE"

echo
echo "Release-Pakete in $RELEASES:"
ls -lh "$RELEASES"/*.zip
