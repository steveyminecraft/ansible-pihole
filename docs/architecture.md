# Architecture

Visual overview: [Project layers diagram](diagrams/ansible-pihole-layers.png) (source: `diagrams/ansible-pihole-layers.drawio`).

Repository and CI map: [Repository map](diagrams/ansible-pihole-repo-map.png) (source: `diagrams/ansible-pihole-unit-tests.drawio`, page “Repository and CI”).

`ansible-pihole` deploys a two-node DNS stack using collection roles:

- `steveyminecraft.pihole.docker`
- `steveyminecraft.pihole.unbound` (optional upstream resolver)
- `steveyminecraft.pihole.traefik` (optional reverse proxy, off by default)
- `steveyminecraft.pihole.pihole`
- `steveyminecraft.pihole.keepalived` (VIP failover)
- `steveyminecraft.pihole.nebula_sync` (configuration replication)

## Runtime flow

1. Docker and network prerequisites are configured.
2. Unbound (optional) is deployed to shared Docker network `dns_net`.
3. Traefik (optional) is deployed to a reusable Docker network `proxy` and
   consumes the local Docker API socket. It is not deployed unless
   `traefik_enabled` is true.
4. Pi-hole is deployed and points upstream at Unbound when present. When Traefik
   is enabled, Pi-hole also joins `proxy` and is routed by labels.
5. Keepalived manages a virtual IP and checks functional DNS health.
6. Nebula Sync replicates Pi-hole config between nodes.


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
- Traefik is opt-in (`traefik_enabled: false`). The Docker API socket is mounted
  read-only into Traefik and is never published over TCP. ACME DNS credentials
  are written to a `0600` env file and are not rendered into `traefik.yml`.
