#!/usr/bin/env bash
set -o pipefail

PIHOLE_CONTAINER="${PIHOLE_CONTAINER:-pihole}"
PIHOLE_HEALTH_DOMAIN="${PIHOLE_HA_HEALTH_DOMAIN:-cloudflare.com}"
PIHOLE_HEALTH_SERVER="${PIHOLE_HA_HEALTH_SERVER:-127.0.0.1}"
PIHOLE_HEALTH_PORT="${PIHOLE_HA_HEALTH_PORT:-53}"

# Keepalived drops supplementary groups for script_user. Use sg(1) for docker
# inspect/exec. Avoid set -e and compound conditionals: keepalived's script
# runner mishandles them. Run the container check first, then functional DNS.
sg docker -c "docker inspect --format '{{.State.Running}}' ${PIHOLE_CONTAINER}" 2>/dev/null \
  | grep -qx true

if command -v dig >/dev/null 2>&1; then
  dig +time=2 +tries=1 +short "@${PIHOLE_HEALTH_SERVER}" -p "${PIHOLE_HEALTH_PORT}" "${PIHOLE_HEALTH_DOMAIN}" \
    | grep -q .
else
  sg docker -c "docker exec ${PIHOLE_CONTAINER} sh -lc \
    'dig +time=2 +tries=1 +short @127.0.0.1 -p 53 ${PIHOLE_HEALTH_DOMAIN}'" \
    | grep -q .
fi
