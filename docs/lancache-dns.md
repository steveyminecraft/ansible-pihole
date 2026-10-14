# LanCache DNS (Steam, isolated `lancache.conf`)

Pi-hole remains the only advertised DNS. This role never starts `lancache-dns`,
never recreates Pi-hole, and never edits OpenWrt DHCP.

Cache IPv4: **172.16.7.51** on prod-01. Domain pin:
`roles/lancache_dns/files/cache-domains/PIN`
(`9061355d60e7643cc70aa3cc395f2777c2d86b5d`). Steam name:
`lancache.steamcontent.com` plus `local=/`. This LAN is IPv4-only;
`local=/` keeps Steam names from growing other address-family answers.

**Steam HTTPS often misses the cache.** Do not call DNS success a cache hit.

## Commands

```bash
ansible-playbook -i inventory/rnet.yml playbooks/lancache-dns.yaml
ansible-playbook -i inventory/rnet.yml playbooks/lancache-dns.yaml \
  -e lancache_dns_command=status

# Live writes (Richard only, after the cache container is up):
ansible-playbook -i inventory/rnet.yml playbooks/lancache-dns.yaml \
  -e lancache_dns_command=apply -e lancache_dns_live_apply=true
ansible-playbook -i inventory/rnet.yml playbooks/lancache-dns.yaml \
  -e lancache_dns_command=fail_open -e lancache_dns_live_apply=true
ansible-playbook -i inventory/rnet.yml playbooks/lancache-dns.yaml \
  -e lancache_dns_command=rollback -e lancache_dns_live_apply=true
```

Fail-open deletes **only** `/opt/pihole/etc/dnsmasq.d/lancache.conf` on each
node and restarts the existing Pi-hole container so FTL re-reads
`dnsmasq.d`. v6 `pihole restartdns` is gone; `reloaddns` does not pick up
new files. Package-cache, QoS, proxy DNS, and `custom.list` stay.

## Checks after a future apply

```bash
dig @172.16.7.25 lancache.steamcontent.com A +short   # 172.16.7.51
dig @172.16.7.30 lancache.steamcontent.com A +short   # 172.16.7.51
dig @172.16.7.25 lancache.steamcontent.com AAAA +short # empty
dig @172.16.7.25 cloudflare.com A +short              # public
dig @172.16.7.25 archive.ubuntu.com A +short          # 172.16.7.50
dig @172.16.7.25 pihole.coalhill.zz A +short          # 172.16.7.35
```

Clients on DoH, static DNS, or the guest Hotel PSK SSID will not hit this path.
