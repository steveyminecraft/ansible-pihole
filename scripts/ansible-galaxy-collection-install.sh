#!/usr/bin/env bash
# Retry ansible-galaxy collection install on transient Galaxy API errors
# (Connection reset by peer, timeouts) seen in GitHub Actions.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <ansible-galaxy collection install arguments...>" >&2
  exit 2
fi

max_attempts="${GALAXY_INSTALL_MAX_ATTEMPTS:-5}"
delay="${GALAXY_INSTALL_RETRY_DELAY_SECONDS:-5}"

if ! [[ "${max_attempts}" =~ ^[1-9][0-9]*$ ]]; then
  echo "GALAXY_INSTALL_MAX_ATTEMPTS must be a positive integer" >&2
  exit 2
fi
if ! [[ "${delay}" =~ ^[0-9]+$ ]]; then
  echo "GALAXY_INSTALL_RETRY_DELAY_SECONDS must be a non-negative integer" >&2
  exit 2
fi

attempt=1
while (( attempt <= max_attempts )); do
  set +e
  ansible-galaxy collection install "$@"
  status=$?
  set -e
  if [[ "${status}" -eq 0 ]]; then
    exit 0
  fi
  if (( attempt == max_attempts )); then
    echo "ansible-galaxy collection install failed after ${max_attempts} attempts (exit ${status})" >&2
    exit "${status}"
  fi
  echo "ansible-galaxy collection install failed (attempt ${attempt}/${max_attempts}, exit ${status}); retrying in ${delay}s..." >&2
  sleep "${delay}"
  attempt=$((attempt + 1))
done
