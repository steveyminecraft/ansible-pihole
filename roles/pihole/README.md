# pihole

Set `pihole_enable_unbound: false` for a Pi-hole-only deployment and provide
explicit upstreams:

```yaml
pihole_enable_unbound: false
pihole_upstream_resolvers:
  - "1.1.1.1"
  - "1.0.0.1"
```

Disabling Unbound removes the managed Unbound container and keeps Pi-hole off
the shared Unbound network.

The default Pi-hole image is pinned. Override `pihole_image` deliberately when
testing or upgrading to another release.

Deploy Pi-hole in Docker (Pi-hole v6) with optional Unbound upstream integration.

Sourced from [docker-pihole](https://github.com/steveyminecraft/docker-pihole) with ansible-pihole compatibility changes applied in this collection.

Part of the `steveyminecraft.pihole` collection.
