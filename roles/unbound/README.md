# unbound_docker

Runs Unbound DNS resolver in Docker via Docker Compose v2.

## Variables

- `unbound_compose_dir` (default `/opt/unbound-docker`)
- `unbound_network_name` (default `dns_net`)
- `unbound_publish_to_host` (default `false`)
- `unbound_port` (default `5335`)

## Example

```yaml
- hosts: dns_hosts
  become: true
  roles:
    - role: unbound_docker
      vars:
        unbound_publish_to_host: true
        unbound_publish_host_ip: "0.0.0.0"
        unbound_publish_host_port: 5335
