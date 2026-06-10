#!/usr/bin/env bash
# Create project virtualenv (env/) with Python 3.13 or 3.14 (first match wins).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pick_python() {
  for candidate in python3.14 python3.13 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return
    fi
  done
  echo "No python3 found. Install Python 3.13 or 3.14 (e.g. sudo apt install python3.14 python3.14-venv)." >&2
  exit 1
}

PY="$(pick_python)"
VER="$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

if [[ "$VER" != "3.13" && "$VER" != "3.14" ]]; then
  echo "Unsupported Python $VER (supported: 3.13, 3.14)." >&2
  exit 1
fi

echo "Using $PY ($VER) -> $ROOT/env"
rm -rf env
"$PY" -m venv env
# shellcheck source=/dev/null
source env/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo
echo "Activate: source env/bin/activate"
echo "Then:     ./scripts/install-ansible-collections.sh"
ansible --version | head -3
