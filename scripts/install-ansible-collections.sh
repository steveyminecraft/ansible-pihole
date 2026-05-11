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
PIHOLE_HEALTH_PATCH="$ROOT/patches/docker-pihole-unbound-health-wait.patch"
if [[ -f "$PIHOLE_UNBOUND_TASKS" ]] && grep -q "Wait until Pi-hole is healthy" "$PIHOLE_UNBOUND_TASKS"; then
  patch --forward -p0 -d "$ROOT" -i "$PIHOLE_HEALTH_PATCH"
fi

PIHOLE_DEFAULTS="$ROOT/roles/pihole/defaults/main.yml"
PIHOLE_DNS_PATCH="$ROOT/patches/docker-pihole-default-docker-dns.patch"
if [[ -f "$PIHOLE_DEFAULTS" ]] && grep -q "Public DNS first" "$PIHOLE_DEFAULTS"; then
  patch --forward -p0 -d "$ROOT" -i "$PIHOLE_DNS_PATCH"
fi

PIHOLE_UPSTREAM_PATCH="$ROOT/patches/docker-pihole-unbound-ip-upstream.patch"
if [[ -f "$PIHOLE_UNBOUND_TASKS" ]] && grep -q "pihole_unbound_upstream | default('unbound#5335')" "$PIHOLE_UNBOUND_TASKS"; then
  patch --forward -p0 -d "$ROOT" -i "$PIHOLE_UPSTREAM_PATCH"
fi

PIHOLE_LOCAL_DNS_PATCH="$ROOT/patches/docker-pihole-local-dns-retry.patch"
if [[ -f "$PIHOLE_UNBOUND_TASKS" ]] && ! grep -q "retries: 60" "$PIHOLE_UNBOUND_TASKS"; then
  patch --forward -p0 -d "$ROOT" -i "$PIHOLE_LOCAL_DNS_PATCH"
fi

PIHOLE_STARTUP_RESOLVER_PATCH="$ROOT/patches/docker-pihole-unbound-startup-resolver.patch"
if [[ -f "$PIHOLE_UNBOUND_TASKS" ]] && ! grep -q "Use public DNS as Pi-hole container startup resolver" "$PIHOLE_UNBOUND_TASKS"; then
  patch --forward -p0 -d "$ROOT" -i "$PIHOLE_STARTUP_RESOLVER_PATCH"
fi

PIHOLE_RESOLV_PATCH="$ROOT/patches/docker-pihole-resolv-conf-override.patch"
if [[ -f "$PIHOLE_UNBOUND_TASKS" ]] && ! grep -q "Override Pi-hole container resolv.conf" "$PIHOLE_UNBOUND_TASKS"; then
  patch --forward -p0 -d "$ROOT" -i "$PIHOLE_RESOLV_PATCH"
fi

# Pinned merge commit from https://github.com/ansible-collections/ansible.posix/pull/690
ansible-galaxy collection install \
  git+https://github.com/ansible-collections/ansible.posix.git,2022c1bd86e42d8f8f682caa1c7fffd301f80ab9 \
  -p "$COL" \
  --force

if [[ -f "$ROOT/collections/requirements.yml" ]]; then
  ansible-galaxy collection install -r "$ROOT/collections/requirements.yml" -p "$COL"
fi
