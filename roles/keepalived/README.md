# keepalived

Configure keepalived for Pi-hole high availability with VIP failover.

The health script (`/etc/keepalived/check_pihole.sh`) requires:

1. The configured Pi-hole container (`PIHOLE_CONTAINER`, default `pihole`) to be
   running.
2. A functional DNS query against local Pi-hole on `127.0.0.1:53` that returns
   at least one IPv4 answer for `pihole_verify_qname` (default `cloudflare.com`).
3. When `pihole_enable_unbound` is true, Unbound must also be running and answer
   the same qname on port `5335`. The script prefers Unbound's live container
   IPv4 from `docker inspect` (fallback: `UNBOUND_DNS_TARGET` / the Docker
   service name) so VIP health still works when keepalived was configured before
   Unbound's address was known, or when Docker embedded DNS is unavailable.
   Pi-hole cache alone is not enough — otherwise upstream failure would not
   trigger VIP failover.

Container checks use `sg docker` so they still work when keepalived runs the
script without supplementary groups. The script uses `set -o pipefail` only
(never `set -e`) because keepalived's script runner mishandles common bash
control-flow patterns. Override the query name with `PIHOLE_HA_HEALTH_DOMAIN`
in the keepalived service environment if needed.

The role leaves IPv4 forwarding disabled by default because a local service VIP
does not normally require routing. Set `keepalived_enable_ip_forward: true`
only for a routed topology.

On RedHat-family hosts, `keepalived_t` remains enforcing by default. Setting
`keepalived_selinux_permissive: true` is a compatibility escape hatch that
weakens SELinux enforcement; prefer correcting labels, ports, capabilities, or
a narrowly scoped policy.

Part of the `steveyminecraft.pihole` collection.
