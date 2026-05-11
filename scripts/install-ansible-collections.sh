#!/usr/bin/env bash
# Install Galaxy roles and collections for this repo.
# ansible.posix is installed from git (PR #690) via CLI so ansible-galaxy does not mix git refs
# with semver resolution in a single requirements file (avoids LooseVersion errors with SHAs).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COL="${ANSIBLE_COLLECTIONS_INSTALL_PATH:-$ROOT/.ansible/collections}"
mkdir -p "$COL"

if [[ -f "$ROOT/roles/requirements.yml" ]]; then
  ansible-galaxy role install -r "$ROOT/roles/requirements.yml" -p "$ROOT/roles"
fi

# Pinned merge commit from https://github.com/ansible-collections/ansible.posix/pull/690
ansible-galaxy collection install \
  git+https://github.com/ansible-collections/ansible.posix.git,2022c1bd86e42d8f8f682caa1c7fffd301f80ab9 \
  -p "$COL" \
  --force

if [[ -f "$ROOT/collections/requirements.yml" ]]; then
  ansible-galaxy collection install -r "$ROOT/collections/requirements.yml" -p "$COL"
fi
