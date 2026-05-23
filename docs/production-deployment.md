# Production Deployment

## Prerequisites

- Controller:
  - Python 3.13+ and ansible-core 2.20.x
  - collections installed via `./scripts/install-ansible-collections.sh`
- Targets:
  - Supported Linux hosts with static/reserved IPs
  - SSH access and privilege escalation

## Inventory guidance

Define production inventory with explicit values for:

- `pihole_environment_variables.FTLCONF_webserver_api_password`
- `pihole_vip_ipv4` (and optional `pihole_vip_ipv6`)
- `unbound_*` values when Unbound is enabled
- `nebula_sync_*` values

Do not reuse any lab-only fixture credentials from Vagrant examples.

## Recommended defaults

- Keep `unbound_publish_to_host: false` unless host-side queries are required.
- Keep `pihole_override_container_resolver: false` unless troubleshooting requires it.
- Keep `docker_ipv6_enabled: false` unless you provide an explicit real IPv6 subnet
  in `docker_ipv6_fixed_cidr`.

## Deploy

Bootstrap:

```bash
ansible-playbook -i /path/to/inventory.yml playbooks/bootstrap-pihole.yaml
```

Update:

```bash
ansible-playbook -i /path/to/inventory.yml playbooks/update-pihole.yaml
```

Both playbooks run one host at a time and include DNS health gates before moving to
the next node.
