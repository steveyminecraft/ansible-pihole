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

PIHOLE_NAT_TASKS="$ROOT/roles/pihole/tasks/redhat_nat_fallback.yml"
if [[ -f "$PIHOLE_NAT_TASKS" ]] && ! grep -q "Add nftables masquerade rules per Docker subnet" "$PIHOLE_NAT_TASKS"; then
  # Python, not patch(1): older GNU patch (e.g. Ubuntu 22.04 CI) rejects some valid unified hunks.
  python3 "$ROOT/scripts/apply_pihole_redhat_nat_fallback.py" "$PIHOLE_NAT_TASKS"
fi

PIHOLE_UNBOUND_TASKS="$ROOT/roles/pihole/tasks/unbound.yml"
if [[ -f "$PIHOLE_UNBOUND_TASKS" ]] && grep -q "Wait until Pi-hole is healthy" "$PIHOLE_UNBOUND_TASKS"; then
  python3 "$ROOT/scripts/apply_pihole_unbound_health_wait.py" "$PIHOLE_UNBOUND_TASKS"
fi

PIHOLE_DEFAULTS="$ROOT/roles/pihole/defaults/main.yml"
if [[ -f "$PIHOLE_DEFAULTS" ]] && grep -q "Public DNS first" "$PIHOLE_DEFAULTS"; then
  python3 "$ROOT/scripts/apply_pihole_galaxy_install_overrides.py" defaults "$PIHOLE_DEFAULTS"
fi

if [[ -f "$PIHOLE_UNBOUND_TASKS" ]]; then
  python3 "$ROOT/scripts/apply_pihole_galaxy_install_overrides.py" unbound "$PIHOLE_UNBOUND_TASKS"
fi

# Pinned merge commit from https://github.com/ansible-collections/ansible.posix/pull/690
ansible-galaxy collection install \
  git+https://github.com/ansible-collections/ansible.posix.git,2022c1bd86e42d8f8f682caa1c7fffd301f80ab9 \
  -p "$COL" \
  --force

if [[ -f "$ROOT/collections/requirements.yml" ]]; then
  ansible-galaxy collection install -r "$ROOT/collections/requirements.yml" -p "$COL"
fi
