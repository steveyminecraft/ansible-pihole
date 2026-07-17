# Architecture

Visual overview: [Project layers diagram](diagrams/ansible-pihole-layers.png) (source: `diagrams/ansible-pihole-layers.drawio`).

Repository and CI map: [Repository map](diagrams/ansible-pihole-repo-map.png) (source: `diagrams/ansible-pihole-unit-tests.drawio`, page “Repository and CI”).

`ansible-pihole` deploys a two-node DNS stack using collection roles:

- `steveyminecraft.pihole.docker`
- `steveyminecraft.pihole.unbound` (optional upstream resolver)
- `steveyminecraft.pihole.pihole`
- `steveyminecraft.pihole.keepalived` (VIP failover)
- `steveyminecraft.pihole.nebula_sync` (configuration replication)

## Runtime flow

1. Docker and network prerequisites are configured.
2. Unbound (optional) is deployed to shared Docker network `dns_net`.
3. Pi-hole is deployed and points upstream at Unbound when present.
4. Keepalived manages a virtual IP and checks functional DNS health.
5. Nebula Sync replicates Pi-hole config between nodes.

## Health and failover

- VIP failover uses `/etc/keepalived/check_pihole.sh`.
- The health script requires local Pi-hole DNS to return an IPv4 answer for an
  external qname, and (when Unbound is enabled) a direct Unbound query as well.
  Container/Docker health alone is not sufficient — cached Pi-hole answers must
  not keep the VIP on a node whose upstream resolver is down.
- Rolling playbooks (`bootstrap-pihole.yaml`, `update-pihole.yaml`) run with `serial: 1`
  and now include post-role DNS health gates per node before proceeding.

## Security defaults

- Pi-hole API password must be set in inventory/vault and pass validation.
- Pi-hole compose files are rendered root-owned with `0600`.
- Nebula Sync defaults to secret-file mode (`PRIMARY_FILE`, `REPLICAS_FILE`).
- Unbound host publishing is disabled by default.
