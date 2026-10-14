# lancache_dns

Installs **one** isolated file, `lancache.conf`, into the existing Pi-hole
`etc/dnsmasq.d` bind mount. Steam CDN names only. No `lancache-dns` container.
Does not recreate Pi-hole.

## Commands

`check` (default), `generate`, `validate`, `apply`, `rollback`, `fail_open`,
`status`.

Live writes need `-e lancache_dns_live_apply=true`. Fail-open deletes only
`lancache.conf` and reloads FTL.

Origin cache IP default: `172.16.7.51`. Upstream domain pin is
`roles/lancache_dns/files/cache-domains/PIN`.
