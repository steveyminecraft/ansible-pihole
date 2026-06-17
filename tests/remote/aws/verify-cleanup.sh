#!/usr/bin/env bash
set -euo pipefail

cleanup_file="${AWS_CLEANUP_STATUS_FILE:-}"
if [[ -z "${cleanup_file}" ]]; then
  echo "AWS_CLEANUP_STATUS_FILE is not set." >&2
  exit 2
fi

if [[ ! -f "${cleanup_file}" ]]; then
  echo "Cleanup status file not found: ${cleanup_file}" >&2
  exit 2
fi

cleanup_verified="$(python3 - <<'PY'
import json
import os
from pathlib import Path

data = json.loads(Path(os.environ["AWS_CLEANUP_STATUS_FILE"]).read_text(encoding="utf-8"))
print(str(data.get("cleanup_verified", False)).lower())
PY
)"

if [[ "${cleanup_verified}" != "true" ]]; then
  echo "AWS cleanup verification failed." >&2
  cat "${cleanup_file}" >&2
  exit 1
fi

echo "AWS cleanup verification passed."
