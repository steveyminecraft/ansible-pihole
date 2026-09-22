#!/usr/bin/env bash
# Two-node upgrade for molecule/upgrade.
#
# bootstrap: install the previous Galaxy release on every host in the Molecule
# inventory (the playbook is hosts: all, serial: 1).
# upgrade: run this checkout's update-pihole.yaml on those same hosts with
# Traefik enabled.
#
# --plan and --print-from-version do not contact the hosts.
# The baseline release is molecule/upgrade/from-version. A pull request edits
# that file to move it. UPGRADE_FROM_VERSION overrides the file for one run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FROM_CACHE="${ROOT}/.ansible/upgrade-from"
BASELINE_VARS="${ROOT}/molecule/upgrade/baseline.yml"
CUTOVER_VARS="${ROOT}/molecule/upgrade/cutover.yml"

usage() {
  echo "usage: $0 bootstrap | upgrade | ci | --plan | --print-from-version" >&2
}

resolve_from_version() {
  local raw="${UPGRADE_FROM_VERSION:-}"
  local version_file="${ROOT}/molecule/upgrade/from-version"
  if [[ -z "${raw}" && -f "${version_file}" ]]; then
    raw="$(tr -d '[:space:]' < "${version_file}")"
  fi
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
  local -a skip=()
  if [[ -n "${UPGRADE_SKIP_TAGS:-}" ]]; then
    skip+=(--skip-tags "${UPGRADE_SKIP_TAGS}")
  fi
  ANSIBLE_CONFIG="${cfg}" ansible-playbook -i "${inventory}" "${playbook}" -e @"${BASELINE_VARS}" "${skip[@]}" || status=$?
  rm -f "${cfg}"
  return "${status}"
}

cmd_upgrade() {
  local inventory
  inventory="$(inventory_arg)"
  cd "${ROOT}"
  local -a skip=()
  if [[ -n "${UPGRADE_SKIP_TAGS:-}" ]]; then
    skip+=(--skip-tags "${UPGRADE_SKIP_TAGS}")
  fi
  ANSIBLE_COLLECTIONS_PATH="${ROOT}/.ansible/collections:${ROOT}/collections" \
    ANSIBLE_ROLES_PATH="${ROOT}/roles" \
    ANSIBLE_INJECT_FACTS_AS_VARS=false \
    ANSIBLE_HOST_KEY_CHECKING=False \
    ansible-playbook -i "${inventory}" "${ROOT}/playbooks/update-pihole.yaml" \
    -e @"${CUTOVER_VARS}" "${skip[@]}"
}

http_ok() {
  case "$1" in
    200|301|302|308) return 0 ;;
    *) return 1 ;;
  esac
}

admin_code() {
  local host="${1:-}"
  if [[ -n "${host}" ]]; then
    curl -sS -o /dev/null -w '%{http_code}' --max-time 15 -H "Host: ${host}" "http://127.0.0.1/admin/"
  else
    curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "http://127.0.0.1/admin/"
  fi
}

wait_for_dns() {
  local attempt
  for attempt in $(seq 1 30); do
    if dig +short +time=2 +tries=1 @127.0.0.1 cloudflare.com | grep -Eq '^[0-9]+(\.[0-9]+){3}$'; then
      return 0
    fi
    sleep 2
  done
  echo "Pi-hole did not answer DNS on 127.0.0.1" >&2
  return 1
}

wait_for_admin() {
  local host="${1:-}"
  local attempt code
  for attempt in $(seq 1 12); do
    code="$(admin_code "${host}")"
    if http_ok "${code}"; then
      return 0
    fi
    sleep 5
  done
  echo "Admin HTTP ${code} for host '${host:-<none>}'" >&2
  return 1
}

publishes_80() {
  docker port "$1" 2>/dev/null | grep -q '^80/tcp'
}

dump_container_logs() {
  docker logs --tail 80 pihole >&2 || true
  docker logs --tail 80 traefik >&2 || true
}

cmd_ci() {
  export MOLECULE_INVENTORY_FILE="${ROOT}/molecule/upgrade/ci-inventory.yml"
  export UPGRADE_SKIP_TAGS="${UPGRADE_SKIP_TAGS:-ha,updates,sshd}"
  trap dump_container_logs ERR
  if ! command -v dig >/dev/null || ! /usr/bin/python3 -c 'import docker' >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y dnsutils python3-docker
  fi
  "${ROOT}/scripts/install-ansible-collections.sh"
  cmd_bootstrap
  wait_for_dns
  publishes_80 pihole
  wait_for_admin
  cmd_upgrade
  wait_for_dns
  if publishes_80 pihole; then
    echo "Pi-hole still publishes 80/tcp after Traefik cutover" >&2
    return 1
  fi
  publishes_80 traefik
  wait_for_admin "upgrade-ci.lab.example.com"
  wait_for_admin "pihole.lab.example.com"
  local dir_mode conf_mode
  dir_mode="$(stat -c %a /opt/pihole/etc/dnsmasq.d)"
  conf_mode="$(stat -c %a /opt/pihole/etc/dnsmasq.d/99-proxy-dns.conf)"
  if [[ "${dir_mode}" != "755" || "${conf_mode}" != "644" ]]; then
    echo "dnsmasq.d mode ${dir_mode}, 99-proxy-dns.conf mode ${conf_mode}" >&2
    return 1
  fi
}

case "${1:-}" in
  bootstrap) cmd_bootstrap ;;
  upgrade) cmd_upgrade ;;
  ci) cmd_ci ;;
  --plan) cmd_plan ;;
  --print-from-version) resolve_from_version ;;
  *) usage; exit 2 ;;
esac
