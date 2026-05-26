# keepalived

Configure keepalived for Pi-hole high availability with VIP failover.

The health script performs a functional DNS query against local Pi-hole on
`127.0.0.1:53`; set `PIHOLE_HA_HEALTH_DOMAIN` in the service environment to
override the default `cloudflare.com` query name.

Part of the `steveyminecraft.pihole` collection.
