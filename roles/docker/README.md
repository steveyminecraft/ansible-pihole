# docker

Install and configure Docker Engine and Docker Compose for Pi-hole deployment targets.

Security-sensitive defaults:

- `docker_group_users: []` grants no Docker group membership. List users
  explicitly only when root-equivalent Docker access is intended.
- `docker_enable_ip_forward: false` leaves host IPv4 forwarding unchanged.
  Enable it for routed bridge/NAT topologies that require it.
- `docker_manage_iptables` is false on Vagrant. Debian/Ubuntu `daemon.json`
  honors that flag, and `docker_el_nat_fallback` adds nftables masquerade
  (including `172.16.0.0/12`) so Unbound/Pi-hole containers can reach the
  internet.

Part of the `steveyminecraft.pihole` collection.
