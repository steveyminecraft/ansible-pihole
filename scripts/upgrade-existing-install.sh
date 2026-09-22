#!/usr/bin/env bash
# Two-node upgrade for molecule/upgrade.
#
# bootstrap: install the previous Galaxy release on every host in the Molecule
# inventory (the playbook is hosts: all, serial: 1).
# upgrade: run this checkout's update-pihole.yaml on those same hosts with
# Traefik enabled.
#
# --plan and --print-from-version do not contact the hosts.
# Set UPGRADE_FROM_VERSION=1.9.4 to pin the baseline. Unset uses the latest
# GitHub release tag.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FROM_CACHE="${ROOT}/.ansible/upgrade-from"
BASELINE_VARS="${ROOT}/molecule/upgrade/baseline.yml"
CUTOVER_VARS="${ROOT}/molecule/upgrade/cutover.yml"

usage() {
  echo "usage: $0 bootstrap | upgrade | --plan | --print-from-version" >&2
}

resolve_from_version() {
  local raw="${UPGRADE_FROM_VERSION:-}"
  if [[ -z "${raw}" ]]; then
    raw="$(gh release view --repo steveyminecraft/ansible-pihole --json tagName --jq .tagName)"
  fi
  raw="${raw#v}"
  if [[ ! "${raw}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "UPGRADE_FROM_VERSION must look like 1.9.4 (got '${raw}')" >&2
    exit 1
  fi
  printf '%s\n' "${raw}"
}

inventory_arg() {
  if [[ -n "${MOLECULE_EPHEMERAL_DIRECTORY:-}" && -d "${MOLECULE_EPHEMERAL_DIRECTORY}/inventory" ]]; then
    printf '%s\n' "${MOLECULE_EPHEMERAL_DIRECTORY}/inventory"
    return
  fi
  if [[ -n "${MOLECULE_INVENTORY_FILE:-}" ]]; then
    printf '%s\n' "${MOLECULE_INVENTORY_FILE}"
    return
  fi
  echo "MOLECULE_INVENTORY_FILE is not set; run this from molecule/upgrade." >&2
  exit 1
}

plan_inventory() {
  if [[ -n "${MOLECULE_EPHEMERAL_DIRECTORY:-}" && -d "${MOLECULE_EPHEMERAL_DIRECTORY}/inventory" ]]; then
    printf '%s\n' "${MOLECULE_EPHEMERAL_DIRECTORY}/inventory"
  elif [[ -n "${MOLECULE_INVENTORY_FILE:-}" ]]; then
    printf '%s\n' "${MOLECULE_INVENTORY_FILE}"
  else
    printf '%s\n' "<molecule-inventory>"
  fi
}

install_previous_release() {
  local version="$1"
  local installed="${FROM_CACHE}/ansible_collections/steveyminecraft/pihole/galaxy.yml"
  local playbook="${FROM_CACHE}/ansible_collections/steveyminecraft/pihole/playbooks/bootstrap-pihole.yaml"
  if [[ -f "${installed}" && -f "${playbook}" ]]; then
    local have
    have="$(awk '/^version:/{print $2; exit}' "${installed}")"
    if [[ "${have}" == "${version}" ]]; then
      return 0
    fi
  fi
  mkdir -p "${FROM_CACHE}"
  "${ROOT}/scripts/ansible-galaxy-collection-install.sh" \
    "steveyminecraft.pihole:==${version}" \
    -p "${FROM_CACHE}" \
    --force \
    --no-cache
}

cmd_plan() {
  local version inventory
  version="$(resolve_from_version)"
  inventory="$(plan_inventory)"
  printf 'phase=bootstrap version=%s inventory=%s playbook=bootstrap-pihole.yaml hosts=all\n' \
    "${version}" "${inventory}"
  printf 'phase=upgrade version=checkout inventory=%s playbook=update-pihole.yaml hosts=all extra=molecule/upgrade/cutover.yml\n' \
    "${inventory}"
}

cmd_bootstrap() {
  local version inventory playbook
  version="$(resolve_from_version)"
  inventory="$(inventory_arg)"
  install_previous_release "${version}"
  playbook="${FROM_CACHE}/ansible_collections/steveyminecraft/pihole/playbooks/bootstrap-pihole.yaml"
  if [[ ! -f "${playbook}" ]]; then
    echo "Previous release ${version} has no ${playbook}" >&2
    exit 1
  fi
  cd "${ROOT}"
  # 1.9.4 must come before this checkout. Dependencies live in the second path.
  # Ansible rejects ANSIBLE_CONFIG=/dev/null, so use a real cfg file.
  local cfg
  cfg="$(mktemp --suffix=.cfg)"
  cat >"${cfg}" <<EOF
[defaults]
collections_path = ${FROM_CACHE}:${ROOT}/.ansible/collections
roles_path = ${FROM_CACHE}/ansible_collections/steveyminecraft/pihole/roles
inject_facts_as_vars = False
host_key_checking = False
EOF
  local status=0
  ANSIBLE_CONFIG="${cfg}" ansible-playbook -i "${inventory}" "${playbook}" -e @"${BASELINE_VARS}" || status=$?
  rm -f "${cfg}"
  return "${status}"
}

cmd_upgrade() {
  local inventory
  inventory="$(inventory_arg)"
  cd "${ROOT}"
  ANSIBLE_COLLECTIONS_PATH="${ROOT}/.ansible/collections:${ROOT}/collections" \
    ANSIBLE_ROLES_PATH="${ROOT}/roles" \
    ANSIBLE_INJECT_FACTS_AS_VARS=false \
    ANSIBLE_HOST_KEY_CHECKING=False \
    ansible-playbook -i "${inventory}" "${ROOT}/playbooks/update-pihole.yaml" \
    -e @"${CUTOVER_VARS}"
}

case "${1:-}" in
  bootstrap) cmd_bootstrap ;;
  upgrade) cmd_upgrade ;;
  --plan) cmd_plan ;;
  --print-from-version) resolve_from_version ;;
  *) usage; exit 2 ;;
esac
