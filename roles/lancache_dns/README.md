# lancache_dns

Installs **one** isolated file, `lancache.conf`, into the existing Pi-hole
`etc/dnsmasq.d` bind mount. Steam CDN names only. No `lancache-dns` container.
Does not recreate Pi-hole.

## Commands

`check` (default), `generate`, `validate`, `apply`, `rollback`, `fail_open`,
`status`.

Live writes need `-e lancache_dns_live_apply=true`. Fail-open deletes only
`lancache.conf` and restarts the existing Pi-hole container (v6 FTL does
not re-read `dnsmasq.d` on `reloaddns`).

Origin cache IP default: `172.16.7.51`. This LAN is IPv4-only; Steam
names get `local=/` so they do not grow other address-family answers.
Upstream domain pin is `roles/lancache_dns/files/cache-domains/PIN`.
