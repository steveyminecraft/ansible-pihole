# Production Deployment

## Prerequisites

- Controller:
  - Python 3.13+ and ansible-core 2.20 or 2.21
  - collections installed via `./scripts/install-ansible-collections.sh`
- Targets:
  - Supported Linux hosts with static/reserved IPs
  - SSH access and privilege escalation

## Inventory files in this repository

| File | Committed | Purpose |
|------|-----------|---------|
| `inventory/rnet.yml` | No (`.gitignore`) | Operator production inventory — hosts, HA, Nebula Sync, Unbound wiring |
| `inventory/inventory.yaml` | No (`.gitignore`) | Alternate local filename some operators use |
| `inventory/vagrant.yml` | Yes | Molecule/Vagrant HA lab (VirtualBox `192.168.56.0/24`) |
| `inventory/vagrant_libvirt.yml` | Yes | Same topology on libvirt (`192.168.121.0/24`) |
| `inventory/ci/` | Yes | Localhost-only vars for CI syntax/check-mode |
| `tests/remote/inventories/example-lab-ha.yml` | Yes | Dual-node HA template for remote functional tests |
| `tests/remote/inventories/example-aws.yml` | Yes | Single-node AWS-style template (HA off) |

Production inventory is **never** checked in. Start from
[`tests/remote/inventories/example-lab-ha.yml`](../tests/remote/inventories/example-lab-ha.yml)
for a dual-node HA layout, or from [`inventory/vagrant.yml`](../inventory/vagrant.yml)
when comparing against the Molecule lab. Copy the template outside the repo or
to a gitignored path such as `inventory/rnet.yml` before filling in real
addresses and secrets.

## Recommended production layout

Keep secrets out of plaintext inventory. A common layout:

```text
inventory/
  rnet.yml                 # hosts, groups, non-secret vars (gitignored)
  group_vars/
    all/
      vars.yml             # optional shared non-secret defaults
      vault.yml            # ansible-vault encrypted secrets (gitignored)
```

Run playbooks with vault when secrets live in `group_vars/all/vault.yml`:

```bash
ansible-playbook -i inventory/rnet.yml playbooks/bootstrap-pihole.yaml \
  --ask-vault-pass
# or: export ANSIBLE_VAULT_PASSWORD_FILE=~/.ansible/vault-pass
```

Plaintext `rnet.yml` with inline passwords is supported for small homelabs but
is discouraged — prefer vault for
`FTLCONF_webserver_api_password` and Nebula Sync credentials.

## Host and group structure (HA)

Dual-node HA expects:

- Two Pi-hole hosts in `all.hosts`, each with:
  - `ansible_host` — management/DNS IP on the LAN
  - `priority` — keepalived priority (higher wins when healthy)
  - `keepalive_role` — `MASTER` or `BACKUP` (initial preference; keepalived still elects)
- Child group `nebula_sync_controller` with **exactly one** host — the node that
  runs the Nebula Sync container (`playbooks/sync.yaml` targets this group only)
- Shared `all.vars` for Pi-hole, VIP, Unbound, and Nebula Sync settings

Example skeleton (replace addresses and use vault for secrets):

```yaml
all:
  hosts:
    pihole-01:
      ansible_host: 192.0.2.10
      priority: 110
      keepalive_role: MASTER
    pihole-02:
      ansible_host: 192.0.2.11
      priority: 100
      keepalive_role: BACKUP
  children:
    nebula_sync_controller:
      hosts:
        pihole-01:
  vars:
    pihole_compose_dir: /opt/pihole
    pihole_ha_mode: true
    pihole_vip_ipv4: 192.0.2.53/24
    # pihole_vip_ipv6: fd00::53/64   # optional
    pihole_environment_variables:
      FTLCONF_webserver_api_password: "{{ vault_pihole_api_password }}"
      # ... see mapping table below
    nebula_sync_primary_url: http://192.0.2.10
    nebula_sync_replicas:
      - url: http://192.0.2.11
        # replica credential: same vault var as primary (see nebula_sync README)
```

Do not reuse lab-only fixture credentials from
[`inventory/vagrant.yml`](../inventory/vagrant.yml) (`LabOnly-Molecule-Pihole-Password!`,
`:latest` image tags, `vagrant_env: true`, etc.).

## Variable mapping — production → examples

| Production / operator need | Required for HA bootstrap | `inventory/vagrant.yml` | `example-lab-ha.yml` | Notes |
|----------------------------|-------------------------|-------------------------|----------------------|-------|
| SSH access | Yes | `ansible_user`, `ansible_password` (first run) | `ansible_user` | Prefer key-based auth; set `password_lock: true` in production |
| Compose path | Yes | `pihole_compose_dir` | *(inherit defaults)* | Not role-defaulted; set explicitly |
| Pi-hole API password | Yes | `pihole_environment_variables.FTLCONF_webserver_api_password` | same key, vault placeholder | Min 16 chars; see [secrets-management.md](secrets-management.md) |
| HA enabled | Yes | `pihole_ha_mode: true` | `pihole_ha_mode: true` | Drives keepalived roles in bootstrap/update |
| IPv4 VIP | Yes | `pihole_vip_ipv4` | `pihole_vip_ipv4` | CIDR form, e.g. `192.0.2.53/24` |
| IPv6 VIP | No | `pihole_vip_ipv6` | — | Omit if not using IPv6 VIP |
| keepalived per host | Yes | `priority`, `keepalive_role` | same | On each host, not in `vars` only |
| Nebula controller group | Yes | `nebula_sync_controller` child group | same | **Required** for `playbooks/sync.yaml` |
| Nebula primary URL | Yes (if syncing) | `nebula_sync_primary_url` | same | HTTP(S) to primary Pi-hole API |
| Nebula replica list | Yes (if syncing) | `nebula_sync_replicas[]` | same | One entry per replica node |
| Nebula passwords | Yes (if syncing) | `nebula_sync_primary_password`, replica passwords | vault placeholders | Often same as Pi-hole API password |
| Unbound enabled | Typical | via `pihole_unbound_upstream`, network vars | `pihole_enable_unbound: true` | See Unbound rows below |
| Pi-hole image pin | Yes | `:latest` in lab only | *(not set — uses role default)* | Pin `pihole_image` in production |
| Lab-only toggles | No | `vagrant_env`, `pihole_rocky_network_debug`, `docker_enable_ip_forward` | — | Do not copy to production |

### Unbound and Docker networking (when `pihole_enable_unbound: true`)

| Production need | `inventory/vagrant.yml` | Typical production pattern |
|-----------------|-------------------------|----------------------------|
| Shared Docker network | `unbound_network_name`, `pihole_network_name` | e.g. `dns_net` |
| Unbound container name / port | `unbound_container_name`, `unbound_port` | `unbound`, `5335` |
| Pi-hole upstream to Unbound | `pihole_unbound_upstream` | `"{{ unbound_container_name }}#{{ unbound_port }}"` |
| Publish Unbound on host | — | `unbound_publish_to_host: false` (default) |
| Unbound ACLs | — | `unbound_access_control` for LAN/docker ranges |

### Nebula Sync optional tuning

| Variable | Lab example | Production guidance |
|----------|-------------|---------------------|
| `nebula_sync_dir` | `/opt/nebula` | Writable path on controller node |
| `nebula_sync_cron` | `*/15 * * * *` | Adjust sync cadence |
| `nebula_sync_full_sync` | `true` in vagrant | `false` unless initial sync |
| `nebula_sync_use_secret_files` | `true` in role defaults | Keep `true`; see secrets doc |
| `nebula_sync_run_gravity` | varies | Enable if gravity sync required |

## Required vs optional (quick checklist)

**Required before `bootstrap-pihole.yaml` on HA:**

- [ ] Two (or more) hosts with `ansible_host`, `priority`, `keepalive_role`
- [ ] `pihole_compose_dir`
- [ ] `pihole_ha_mode: true`
- [ ] `pihole_vip_ipv4` (and `pihole_vip_ipv6` if used)
- [ ] `pihole_environment_variables.FTLCONF_webserver_api_password` (vault)
- [ ] `nebula_sync_controller` with exactly one host (if using Nebula Sync)
- [ ] `nebula_sync_primary_url`, `nebula_sync_primary_password`, `nebula_sync_replicas` (if syncing)
- [ ] Pinned `pihole_image` (avoid `:latest`)

**Commonly optional:**

- `pihole_firewall_deploy`, `pihole_webport_*`, REV_SERVER fields
- `pihole_vip_ipv6`, custom `unbound_access_control`
- `github_user_for_ssh_key` (only when deploying SSH keys via `sshd` role)

Role tasks reject known placeholders (`CHANGE_ME`, `Intranet`, `Testing 101`, empty
values) for Pi-hole and Nebula Sync passwords.

## Recommended defaults

- Keep `unbound_publish_to_host: false` unless host-side queries are required.
- Keep `pihole_override_container_resolver: false` unless troubleshooting requires it.
- Keep `docker_ipv6_enabled: false` unless you provide an explicit real IPv6 subnet
  in `docker_ipv6_fixed_cidr`.

## Deploy

Bootstrap:

```bash
ansible-playbook -i inventory/rnet.yml playbooks/bootstrap-pihole.yaml
```

Update:

```bash
ansible-playbook -i inventory/rnet.yml playbooks/update-pihole.yaml
```

Nebula Sync (controller node only):

```bash
ansible-playbook -i inventory/rnet.yml playbooks/sync.yaml
```

Both bootstrap and update run one host at a time (`serial: 1`) and include DNS
health gates before moving to the next node. See
[upgrade-runbook.md](upgrade-runbook.md) for the full production change checklist.

## Related docs

- [secrets-management.md](secrets-management.md) — vault naming, rotation (P3 item 2)
- [upgrade-runbook.md](upgrade-runbook.md) — rolling update and health gates
- [tests/remote/README.md](../tests/remote/README.md) — validating inventory against remote scenarios
