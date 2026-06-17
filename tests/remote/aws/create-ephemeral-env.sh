#!/usr/bin/env bash
set -euo pipefail

required_vars=(
  AWS_REGION
  AWS_SUBNET_ID
  AWS_KEY_NAME
  AWS_INSTANCE_TYPE
  AWS_OS_FAMILY
  AWS_ARCH
  AWS_TEST_SCENARIO
  AWS_SSH_PRIVATE_KEY_PATH
  AWS_INVENTORY_FILE
  AWS_STATE_FILE
  AWS_METADATA_FILE
  AWS_INVENTORY_TEMPLATE
  PIHOLE_API_PASSWORD
  GITHUB_USER_FOR_SSH_KEY
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required environment variable: ${var_name}" >&2
    exit 2
  fi
done

if [[ ! -f "${AWS_INVENTORY_TEMPLATE}" ]]; then
  echo "Inventory template not found: ${AWS_INVENTORY_TEMPLATE}" >&2
  exit 2
fi

AWS_OS_VERSION="${AWS_OS_VERSION:-}"
arch_suffix="${AWS_ARCH}"
if [[ "${AWS_ARCH}" == "arm64" ]]; then
  arch_suffix="arm64"
fi

resolve_ubuntu_ami() {
  local version="${1:-26.04}"
  local arch="${2:-amd64}"
  aws ssm get-parameter \
    --region "${AWS_REGION}" \
    --name "/aws/service/canonical/ubuntu/server/${version}/stable/current/${arch}/hvm/ebs-gp3/ami-id" \
    --query 'Parameter.Value' \
    --output text
}

if [[ "${AWS_OS_FAMILY}" != "ubuntu" ]]; then
  echo "Unsupported AWS_OS_FAMILY: ${AWS_OS_FAMILY} (only ubuntu is supported for AWS remote tests)" >&2
  exit 2
fi

ubuntu_version="${AWS_OS_VERSION:-26.04}"
ami_id="$(resolve_ubuntu_ami "${ubuntu_version}" "${arch_suffix}")"

if [[ -z "${ami_id}" || "${ami_id}" == "None" ]]; then
  echo "Unable to resolve AMI for ${AWS_OS_FAMILY} ${AWS_OS_VERSION:-default} (${arch_suffix})." >&2
  exit 2
fi

echo "Selected AMI ${ami_id} for ${AWS_OS_FAMILY} ${AWS_OS_VERSION:-default} (${arch_suffix})"

name_suffix="$(date +%s)-${RANDOM}"
name_prefix="${AWS_TEST_PREFIX:-ansible-pihole-remote}"
security_group_name="${name_prefix}-sg-${name_suffix}"
resource_name="${name_prefix}-${AWS_OS_FAMILY}-${AWS_ARCH}-${name_suffix}"

if [[ -s "${AWS_STATE_FILE}" ]]; then
  echo "State file already exists (${AWS_STATE_FILE}); refusing to overwrite." >&2
  exit 2
fi

if [[ -z "${AWS_SSH_CIDR:-}" ]]; then
  AWS_SSH_CIDR="0.0.0.0/0"
fi

vpc_id="$(aws ec2 describe-subnets \
  --region "${AWS_REGION}" \
  --subnet-ids "${AWS_SUBNET_ID}" \
  --query 'Subnets[0].VpcId' \
  --output text)"

if [[ -z "${vpc_id}" || "${vpc_id}" == "None" ]]; then
  echo "Unable to resolve VPC for subnet ${AWS_SUBNET_ID}" >&2
  exit 2
fi

security_group_id="$(aws ec2 create-security-group \
  --region "${AWS_REGION}" \
  --vpc-id "${vpc_id}" \
  --group-name "${security_group_name}" \
  --description "Ephemeral ansible-pihole remote test SG (${name_suffix})" \
  --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=${security_group_name}},{Key=Project,Value=ansible-pihole},{Key=Ephemeral,Value=true}]" \
  --query 'GroupId' \
  --output text)"

aws ec2 authorize-security-group-ingress \
  --region "${AWS_REGION}" \
  --group-id "${security_group_id}" \
  --ip-permissions "[
    {\"IpProtocol\":\"tcp\",\"FromPort\":22,\"ToPort\":22,\"IpRanges\":[{\"CidrIp\":\"${AWS_SSH_CIDR}\"}]},
    {\"IpProtocol\":\"udp\",\"FromPort\":53,\"ToPort\":53,\"IpRanges\":[{\"CidrIp\":\"${AWS_SSH_CIDR}\"}]},
    {\"IpProtocol\":\"tcp\",\"FromPort\":53,\"ToPort\":53,\"IpRanges\":[{\"CidrIp\":\"${AWS_SSH_CIDR}\"}]}
  ]"

instance_id="$(aws ec2 run-instances \
  --region "${AWS_REGION}" \
  --image-id "${ami_id}" \
  --instance-type "${AWS_INSTANCE_TYPE}" \
  --key-name "${AWS_KEY_NAME}" \
  --subnet-id "${AWS_SUBNET_ID}" \
  --security-group-ids "${security_group_id}" \
  --associate-public-ip-address \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${resource_name}},{Key=Project,Value=ansible-pihole},{Key=Ephemeral,Value=true}]" \
  --count 1 \
  --query 'Instances[0].InstanceId' \
  --output text)"

aws ec2 wait instance-running --region "${AWS_REGION}" --instance-ids "${instance_id}"
aws ec2 wait instance-status-ok --region "${AWS_REGION}" --instance-ids "${instance_id}"

public_ip="$(aws ec2 describe-instances \
  --region "${AWS_REGION}" \
  --instance-ids "${instance_id}" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)"

private_ip="$(aws ec2 describe-instances \
  --region "${AWS_REGION}" \
  --instance-ids "${instance_id}" \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text)"

if [[ -z "${public_ip}" || "${public_ip}" == "None" ]]; then
  echo "Instance ${instance_id} has no public IP for SSH." >&2
  exit 2
fi

if [[ -z "${private_ip}" || "${private_ip}" == "None" ]]; then
  echo "Instance ${instance_id} has no private IP." >&2
  exit 2
fi

mkdir -p "$(dirname "${AWS_STATE_FILE}")" "$(dirname "${AWS_INVENTORY_FILE}")" "$(dirname "${AWS_METADATA_FILE}")"

cat > "${AWS_STATE_FILE}" <<EOF
{
  "region": "${AWS_REGION}",
  "instance_ids": ["${instance_id}"],
  "security_group_id": "${security_group_id}"
}
EOF

cat > "${AWS_METADATA_FILE}" <<EOF
{
  "scenario": "${AWS_TEST_SCENARIO}",
  "region": "${AWS_REGION}",
  "os_family": "${AWS_OS_FAMILY}",
  "os_version": "${AWS_OS_VERSION:-}",
  "arch": "${AWS_ARCH}",
  "instance_ids": ["${instance_id}"],
  "public_ips": ["${public_ip}"],
  "private_ips": ["${private_ip}"],
  "security_group_id": "${security_group_id}"
}
EOF

vault_value_lines="FTLCONF_webserver_api_password: \"${PIHOLE_API_PASSWORD}\""
if [[ -f "${ANSIBLE_VAULT_PASSWORD_FILE:-}" ]]; then
  vault_value_raw="$(ansible-vault encrypt_string \
    --vault-password-file "${ANSIBLE_VAULT_PASSWORD_FILE}" \
    --name FTLCONF_webserver_api_password \
    "${PIHOLE_API_PASSWORD}")"
  vault_value_lines="$(printf '%s\n' "${vault_value_raw}" | sed 's/^/      /')"
fi

cat "${AWS_INVENTORY_TEMPLATE}" > "${AWS_INVENTORY_FILE}"

PUBLIC_IP="${public_ip}" PRIVATE_IP="${private_ip}" VAULT_VALUE_LINES="${vault_value_lines}" python3 - <<'PY'
import os
from pathlib import Path

inventory_path = Path(os.environ["AWS_INVENTORY_FILE"])
content = inventory_path.read_text(encoding="utf-8")
replacements = {
    "REPLACE_PUBLIC_IP": os.environ["PUBLIC_IP"],
    "REPLACE_SSH_KEY_PATH": os.environ["AWS_SSH_PRIVATE_KEY_PATH"],
    "REPLACE_PRIVATE_IP_CIDR": f"{os.environ['PRIVATE_IP']}/24",
    "replace-me": os.environ["GITHUB_USER_FOR_SSH_KEY"],
}
for old, new in replacements.items():
    content = content.replace(old, new)

if os.environ["AWS_TEST_SCENARIO"] in ("no-unbound", "pihole-upstream-only"):
    content = content.replace("pihole_enable_unbound: true", "pihole_enable_unbound: false")

vault_block = os.environ["VAULT_VALUE_LINES"]
content = content.replace("      FTLCONF_webserver_api_password: REPLACE_WITH_ANSIBLE_VAULT", vault_block)
inventory_path.write_text(content, encoding="utf-8")
PY

echo "Created ephemeral AWS test environment:"
echo "  region: ${AWS_REGION}"
echo "  instance_id: ${instance_id}"
echo "  public_ip: ${public_ip}"
echo "  inventory: ${AWS_INVENTORY_FILE}"
