# unbound_docker

Runs Unbound DNS resolver in Docker via Docker Compose v2.

## Variables

- `unbound_compose_dir` (default `/opt/unbound`)
- `unbound_network_name` (default `dns_net`)
- `unbound_publish_to_host` (default `false`)
- `unbound_publish_host_ip` (default `127.0.0.1`)
- `unbound_publish_host_port` (default `5335`)
- `unbound_port` (default `5335`)

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
