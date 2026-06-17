#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_root"

inventory=""
scenario=""
skip_converge=false
skip_update=false

usage() {
  cat <<'EOF'
Usage: tests/remote/run.sh --inventory PATH --scenario SCENARIO [options]

Scenarios:
  single       Pi-hole with Unbound on independent nodes
  no-unbound   Pi-hole with explicit upstream resolvers and no Unbound
  ha           Pi-hole, Unbound, keepalived VIP, and optional Nebula Sync

Options:
  --skip-converge  Verify an existing deployment without bootstrapping it.
  --skip-update    Do not exercise playbooks/update-pihole.yaml.
  -h, --help       Show this help.

Optional lifecycle hooks:
  REMOTE_CREATE_COMMAND       Provision or start hosts before converge.
  REMOTE_IDEMPOTENCE_COMMAND  Run an environment-specific idempotence check.
  REMOTE_RESET_COMMAND        Reset or destroy hosts after verification.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --inventory)
      inventory="${2:-}"
      shift 2
      ;;
    --scenario)
      scenario="${2:-}"
      shift 2
      ;;
    --skip-converge)
      skip_converge=true
      shift
      ;;
    --skip-update)
      skip_update=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$inventory" || -z "$scenario" ]]; then
  usage >&2
  exit 2
fi

case "$scenario" in
  single)
    verify_playbooks=(pihole.yml unbound.yml)
    ;;
  no-unbound)
    verify_playbooks=(pihole.yml no-unbound.yml)
    ;;
  ha)
    verify_playbooks=(pihole.yml unbound.yml keepalived.yml vip-dns.yml nebula-sync.yml)
    ;;
  *)
    echo "Unknown scenario: $scenario" >&2
    usage >&2
    exit 2
    ;;
esac

run_hook() {
  local name="$1"
  local command="$2"

  if [[ -z "$command" ]]; then
    echo "Skipping optional $name hook."
    return
  fi

  echo "Running $name hook."
  /bin/bash -lc "$command"
}

run_verification() {
  local playbook

  for playbook in "${verify_playbooks[@]}"; do
    echo "Running remote verification: $playbook"
    ansible-playbook -i "$inventory" "tests/remote/verify/$playbook"
  done
}

cleanup() {
  run_hook reset "${REMOTE_RESET_COMMAND:-}"
}
trap cleanup EXIT

run_hook create "${REMOTE_CREATE_COMMAND:-}"

if [[ ! -f "$inventory" ]]; then
  echo "Inventory not found after create hook: $inventory" >&2
  exit 2
fi

echo "Validating inventory: $inventory"
ansible-inventory -i "$inventory" --graph

if ! $skip_converge; then
  echo "Converging remote deployment."
  ansible-playbook -i "$inventory" playbooks/bootstrap-pihole.yaml
  run_verification
fi

run_hook idempotence "${REMOTE_IDEMPOTENCE_COMMAND:-}"

if ! $skip_update; then
  echo "Exercising remote update workflow."
  ansible-playbook -i "$inventory" playbooks/update-pihole.yaml
fi

run_verification

echo "Remote scenario passed: $scenario"
