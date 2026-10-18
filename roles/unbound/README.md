# unbound_docker

Runs Unbound DNS resolver in Docker via Docker Compose v2.

## Variables

- `unbound_compose_dir` (default `/opt/unbound`)
- `unbound_network_name` (default `dns_net`)
- `unbound_publish_to_host` (default `false`)
- `unbound_publish_host_ip` (default `127.0.0.1`)
- `unbound_publish_host_port` (default `5335`)
- `unbound_port` (default `5335`)
- `unbound_access_control` (RFC1918 + loopback `allow`; required for host `dig`
  to the container IP on Vagrant, where Docker does not manage iptables)
- `unbound_chroot` (empty by default; do not chroot inside the container)
- Recursion uses root hints unless `unbound_forward_addrs` is set. Vagrant
  inventories forward to `1.1.1.1`/`8.8.8.8` because lab DNS intercepts root NS.
  The mvance image `forward-records.conf` (DoT on 853) is not included.
- `unbound_do_ip6` defaults to `false` (Docker IPv6 is off unless opted in).
- After compose, the role refreshes Docker NAT fallback so `dns_net` can egress.
- Verify queries Unbound via `nsenter` to `127.0.0.1` in the container netns
  (host `dig` to the bridge IP times out when Docker does not manage iptables).
- `unbound_image` (default empty, selects from `unbound_image_arch_map`)

The default image map uses pinned tags by architecture. x86_64/amd64 hosts use
`mvance/unbound:1.19.3`; ARM hosts use `vincejv/unbound:1.25.1` because the
`vincejv/unbound` repository does not publish a `1.19.3` tag.

## Example

```yaml
- hosts: dns_hosts
  become: true
  roles:
    - role: unbound_docker
      vars:
        unbound_publish_to_host: true
        # Prefer loopback unless external host access is explicitly required.
        unbound_publish_host_ip: "127.0.0.1"
        unbound_publish_host_port: 5335
```
