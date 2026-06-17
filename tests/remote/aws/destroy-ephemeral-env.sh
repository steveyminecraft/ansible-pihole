#!/usr/bin/env bash
set -euo pipefail

state_file="${AWS_STATE_FILE:-}"
cleanup_file="${AWS_CLEANUP_STATUS_FILE:-}"

if [[ -z "${cleanup_file}" ]]; then
  cleanup_file="$(mktemp)"
fi

write_cleanup_file() {
  local cleanup_verified="$1"
  local sg_deleted="$2"
  local instances_remaining="$3"
  cat > "${cleanup_file}" <<EOF
{
  "cleanup_verified": ${cleanup_verified},
  "security_group_deleted": ${sg_deleted},
  "instances_remaining": ${instances_remaining}
}
EOF
}

if [[ -z "${state_file}" || ! -f "${state_file}" ]]; then
  write_cleanup_file "true" "true" 0
  echo "No AWS state file found; nothing to destroy."
  exit 0
fi

state_region="$(python3 - <<'PY'
import json
import os
from pathlib import Path

state = json.loads(Path(os.environ["AWS_STATE_FILE"]).read_text(encoding="utf-8"))
print(state.get("region", ""))
PY
)"

if [[ -z "${AWS_REGION:-}" ]]; then
  AWS_REGION="${state_region}"
fi

if [[ -z "${AWS_REGION:-}" ]]; then
  echo "Missing AWS region while attempting cleanup." >&2
  write_cleanup_file "false" "false" 1
  exit 2
fi

instance_ids="$(python3 - <<'PY'
import json
import os
from pathlib import Path

state = json.loads(Path(os.environ["AWS_STATE_FILE"]).read_text(encoding="utf-8"))
print(" ".join(state.get("instance_ids", [])))
PY
)"

security_group_id="$(python3 - <<'PY'
import json
import os
from pathlib import Path

state = json.loads(Path(os.environ["AWS_STATE_FILE"]).read_text(encoding="utf-8"))
print(state.get("security_group_id", ""))
PY
)"

if [[ -n "${instance_ids}" ]]; then
  aws ec2 terminate-instances \
    --region "${AWS_REGION}" \
    --instance-ids ${instance_ids} >/dev/null
  aws ec2 wait instance-terminated \
    --region "${AWS_REGION}" \
    --instance-ids ${instance_ids}
fi

sg_deleted="true"
if [[ -n "${security_group_id}" ]]; then
  if ! aws ec2 delete-security-group --region "${AWS_REGION}" --group-id "${security_group_id}" >/dev/null 2>&1; then
    sg_deleted="false"
  fi
fi

remaining=0
if [[ -n "${instance_ids}" ]]; then
  remaining="$(aws ec2 describe-instances \
    --region "${AWS_REGION}" \
    --instance-ids ${instance_ids} \
    --query 'length(Reservations[].Instances[?State.Name!=`terminated`][])' \
    --output text)"
  if [[ -z "${remaining}" || "${remaining}" == "None" ]]; then
    remaining=0
  fi
fi

cleanup_verified="true"
if [[ "${remaining}" != "0" || "${sg_deleted}" != "true" ]]; then
  cleanup_verified="false"
fi

write_cleanup_file "${cleanup_verified}" "${sg_deleted}" "${remaining}"
rm -f "${state_file}"
echo "AWS cleanup complete (verified=${cleanup_verified})."
