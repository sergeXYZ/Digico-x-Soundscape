#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
export PYTHONUNBUFFERED=1
unset PYTHONHOME PYTHONPATH
.venv/bin/pip install -q -r requirements.txt
echo "Starting Digico×Soundscape launcher…"
exec .venv/bin/python -m bridge.main
