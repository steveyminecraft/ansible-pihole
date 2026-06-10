# keepalived

Configure keepalived for Pi-hole high availability with VIP failover.

The health script requires the configured Pi-hole container (`PIHOLE_CONTAINER`,
default `pihole`) to be running, then performs a functional DNS query against
local Pi-hole on `127.0.0.1:53`. Container checks use `sg docker` so they still
work when keepalived runs the script without supplementary groups. The script
uses `set -o pipefail` only (never `set -e`) because keepalived's script runner
mishandles common bash control-flow patterns. Set `PIHOLE_HA_HEALTH_DOMAIN` in
the keepalived service environment to override the default `cloudflare.com`
query name.

The role leaves IPv4 forwarding disabled by default because a local service VIP
does not normally require routing. Set `keepalived_enable_ip_forward: true`
only for a routed topology.

On RedHat-family hosts, `keepalived_t` remains enforcing by default. Setting
`keepalived_selinux_permissive: true` is a compatibility escape hatch that
weakens SELinux enforcement; prefer correcting labels, ports, capabilities, or
a narrowly scoped policy.

Part of the `steveyminecraft.pihole` collection.
