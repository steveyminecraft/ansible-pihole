#!/usr/bin/env bash
# Install this collection and third-party collections for local dev / CI.
# ansible.posix is installed from git (PR #690) via CLI so ansible-galaxy does not mix git refs
# with semver resolution in a single requirements file (avoids LooseVersion errors with SHAs).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COL="${ANSIBLE_COLLECTIONS_INSTALL_PATH:-$ROOT/.ansible/collections}"
mkdir -p "$COL"

# Install steveyminecraft.pihole from a local build of this repository.
version="$(awk '/^version:/{print $2; exit}' "$ROOT/galaxy.yml")"
rm -f steveyminecraft-pihole-*.tar.gz
ansible-galaxy collection build --force
artifact="steveyminecraft-pihole-${version}.tar.gz"
if [[ ! -f "$artifact" ]]; then
  echo "Expected collection artifact not found: ${artifact}" >&2
  exit 1
fi
ansible-galaxy collection install "${artifact}" -p "$COL" --force

# Pinned merge commit from https://github.com/ansible-collections/ansible.posix/pull/690
ansible-galaxy collection install \
  git+https://github.com/ansible-collections/ansible.posix.git,2022c1bd86e42d8f8f682caa1c7fffd301f80ab9 \
  -p "$COL" \
  --force

if [[ -f "$ROOT/collections/requirements.yml" ]]; then
  ansible-galaxy collection install -r "$ROOT/collections/requirements.yml" -p "$COL"
fi
