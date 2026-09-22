# ansible-pihole

Bootstrap hosts with Ansible, install Docker and Pi-hole (optionally Unbound),
and optionally run **high availability** with keepalived plus config sync
(Nebula Sync).

Playbooks live under [`playbooks/`](playbooks/). Example inventories for CI and
Molecule are under [`inventory/`](inventory/); for real hardware you maintain
your own inventory (YAML or INI) with your hosts and variables.

For the upstream Pi-hole container image, see: https://github.com/pi-hole/docker-pi-hole

> **Notice:** Going forward, supported targets are Ubuntu, Debian, and Raspberry
> Pi OS (Debian ARM). Rocky Linux and Red Hat Enterprise Linux are
> **deprecated**. The existing RedHat-family tasks still run in this release;
> they are not being rewritten. Plan to move those hosts to Debian or Ubuntu.

## Controller setup (your laptop or CI)

- **ansible-core 2.20 or 2.21**. The normal developer environment uses 2.21
  (see [`requirements.txt`](requirements.txt)); CI also tests the 2.20 runtime floor.
- **Python 3.13 or 3.14** for the controller
  (CI tests both; Ubuntu 26.04 ships 3.14—see
  [`.python-version`](.python-version)).

```bash
./scripts/setup-env.sh
source env/bin/activate
./scripts/install-ansible-collections.sh
ansible --version   # ansible-core 2.21.x from env/bin/ansible
```

Manual venv (if you prefer): `python3.13 -m venv env` or
`python3.14 -m venv env`, then `pip install -r requirements.txt`.

This repository is an **Ansible collection** published as
**`steveyminecraft.pihole`** on
[Ansible Galaxy](https://galaxy.ansible.com/ui/collections/). Collection
metadata is in [`galaxy.yml`](galaxy.yml); runtime requirements are in
[`meta/runtime.yml`](meta/runtime.yml).

**From Galaxy** (consumers):

```bash
ansible-galaxy collection install steveyminecraft.pihole
```

**From a git clone** (development):

```bash
./scripts/install-ansible-collections.sh
```

That script builds and installs this collection locally, then installs released
dependencies from [`collections/requirements.yml`](collections/requirements.yml).
Local build output and development-only directories such as `.ansible/`,
virtualenvs, Vagrant state, and generated collection tarballs are excluded from
the collection artifact.

[`ansible.cfg`](ansible.cfg) sets `roles_path`, `collections_path`, and disables
top-level fact injection so roles use `ansible_facts[...]` with ansible-core
2.20+. Playbooks reference roles by FQCN (for example
`steveyminecraft.pihole.pihole`). Re-run the install script after changing
[`galaxy.yml`](galaxy.yml) or
[`collections/requirements.yml`](collections/requirements.yml).

The Pi-hole Docker role lives in this collection as
[`roles/pihole`](roles/pihole/) (sourced from
[`docker-pihole`](https://github.com/steveyminecraft/docker-pihole) with
ansible-pihole compatibility changes applied in-tree).
Docker host installation is organized into focused platform repository,
package, networking, diagnostics, user, daemon, and NAT task files under
[`roles/docker/tasks/`](roles/docker/tasks/).

## Base setup (targets)

- Targets can be **Raspberry Pi OS** (Debian ARM) or Ubuntu/Debian. Molecule `default` is Ubuntu 24.04; `debian` is Debian 12 (closer to Pi OS). Raspberry Pi OS ARM is **phase two** (AWS remote / hardware). Rocky/RHEL task paths still exist but are deprecated (see the notice above).
- The [openssh_keypair](https://docs.ansible.com/ansible/latest/collections/community/crypto/openssh_keypair_module.html) collection module is pulled in via `collections/requirements.yml`.
- **Headless Pi** (if applicable): enable SSH, configure user and networking, set static IPs (DHCP reservation is enough).
- **Inventory:** define hosts and group vars (see examples in [`inventory/vagrant.yml`](inventory/vagrant.yml) for lab-style vars such as `pihole_*`, `nebula_sync_*`, VIPs). There is no single checked-in “production” inventory filename; use `-i` pointing at your file.

## Playbooks

Run from the repo root, for example:

```bash
ansible-playbook -i /path/to/your/inventory.yml playbooks/bootstrap-pihole.yaml
```

### `playbooks/bootstrap-pihole.yaml`

First-time (and repeatable) full bootstrap: system prep, Docker, optional Unbound,
Pi-hole, keepalived, etc. (see the play for the exact role list).

If Docker tasks fail on a first run, reboot the host and re-run.

Roles include (among others):

- [`bootstrap`](roles/bootstrap/tasks/main.yml): SSH key from GitHub (`github_user_for_ssh_key`), optional password lock, aliases, timezone, hostname, packages such as firewalld on Debian/Ubuntu.
- [`updates`](roles/updates/tasks/main.yml), [`sshd`](roles/sshd/tasks/main.yml), [`docker`](roles/docker/tasks/main.yml), [`unbound`](roles/unbound/tasks/main.yml), [`traefik`](roles/traefik/tasks/main.yml) (opt-in), [`pihole`](roles/pihole/tasks/main.yml), [`keepalived`](roles/keepalived/tasks/main.yml), [`start_keepalived`](roles/start_keepalived/tasks/main.yml) / [`stop_keepalived`](roles/stop_keepalived/tasks/main.yml) as used in the play (FQCN prefix `steveyminecraft.pihole.` in playbooks).

On RedHat/Rocky hosts the Docker role still installs `kernel-modules-extra` by default for Docker/netfilter support. If a real host already has the needed modules and `/boot` is too tight for kernel package changes, opt out in inventory:

```yaml
docker_install_kernel_modules_extra: false
```

Docker group membership is root-equivalent and defaults to no users. Lab or
administrative inventories can grant it explicitly:

```yaml
docker_group_users:
  - vagrant
```

The Docker and keepalived roles leave IPv4 forwarding unchanged by default.
Enable it only for a topology that routes traffic between interfaces:

```yaml
docker_enable_ip_forward: true
# or, for a keepalived-specific routed topology:
keepalived_enable_ip_forward: true
```

On RedHat/Rocky, `keepalived_t` remains enforcing by default. The
`keepalived_selinux_permissive: true` compatibility escape hatch weakens
SELinux enforcement and should only be used for a known denial while a narrow
policy fix is prepared. Vagrant lab inventories enable it so keepalived can run
the docker/dig VIP health script under Molecule without a custom SELinux module.

`docker_disable_ipv6` now defaults to `false` for production safety. Set it explicitly in
lab inventories where guest networking requires the workaround (for example Vagrant/Rocky).

On Debian/Ubuntu, Docker IPv6 is now opt-in:

```yaml
docker_ipv6_enabled: true
docker_ipv6_fixed_cidr: "fd12:3456:789a::/64"
```

When `docker_ipv6_enabled` is true, `docker_ipv6_fixed_cidr` must be set to a real
environment subnet (documentation ranges such as `2001:db8::/32` are rejected).

Pi-hole-related variables (e.g. `pihole_environment_variables`, `pihole_ha_mode`, `pihole_vip_ipv4` / `pihole_vip_ipv6`) are typically set in inventory; see the [docker-pi-hole environment docs](https://github.com/pi-hole/docker-pi-hole#environment-variables) for image variables.

Role-local variable naming now consistently uses the `pihole_` prefix to satisfy ansible-lint role scoping rules (for example `pihole_dir_loc`, `pihole_webport_http`, `pihole_docker_manage_iptables`). Existing inventories that still define legacy unprefixed names continue to work via compatibility lookups in `roles/pihole/defaults/main.yml`, but new configs should use the prefixed names.

| Legacy (deprecated) | Use instead | Removal target |
|---------------------|-------------|----------------|
| `dir_loc` | `pihole_dir_loc` | v2.0.0 |
| `firewall_deploy` | `pihole_firewall_deploy` | v2.0.0 |
| `webport_http` | `pihole_webport_http` | v2.0.0 |
| `webport_https` | `pihole_webport_https` | v2.0.0 |
| `docker_manage_iptables` | `pihole_docker_manage_iptables` | v2.0.0 |
| `docker_el_nat_fallback` | `pihole_docker_el_nat_fallback` | v2.0.0 |
| `pihole_unbound_verify_qname` | `pihole_verify_qname` | v2.0.0 |

Lint inventories locally: `python scripts/check-legacy-inventory-vars.py` (warn-only; `--fail-on-find` after v2.0.0). See [Testing guide](docs/testing.md).

Pi-hole image pulls map common host architectures to Docker platform strings via
`pihole_docker_platform_arch_map` (`x86_64`/`amd64` -> `linux/amd64`,
`aarch64`/`arm64` -> `linux/arm64`, `armv7l` -> `linux/arm/v7`,
`armv6l` -> `linux/arm/v6`). Unknown architectures omit the platform argument
and let Docker choose the best matching image.

DNS health checks use `pihole_verify_qname` (default `cloudflare.com`) in
Pi-hole, Unbound, Molecule, and HA verification paths. The older
`pihole_unbound_verify_qname` remains as a compatibility alias.

Pi-hole container Linux capabilities are controlled by `pihole_container_cap_add`.
The defaults preserve existing behavior (`NET_ADMIN`, `SYS_TIME`, `SYS_NICE`,
`CAP_NET_BIND_SERVICE`, `CAP_NET_RAW`, `CAP_CHOWN`). Override with a smaller list
only after validating the required Pi-hole features in your deployment mode.

Security defaults:

- `FTLCONF_webserver_api_password` must be provided from inventory/vault and should be at least 16 characters.
- Known placeholders/defaults (`Testing 101`, `Intranet`, `CHANGE_ME`, empty value) are rejected by role assertions.
- Pi-hole compose files are rendered with root-only permissions (`0600`) in both normal and Unbound integration paths.

Unbound is deployed before Pi-hole by default and can be used as Pi-hole's
upstream resolver over a shared Docker network. Disable it explicitly and
provide upstream resolvers for a Pi-hole-only deployment:

```yaml
pihole_enable_unbound: false
pihole_upstream_resolvers:
  - "1.1.1.1"
  - "1.0.0.1"
```

When Unbound is disabled, the Pi-hole role removes the managed Unbound
container, Pi-hole is not attached to the shared Unbound network, and the role
requires either `pihole_upstream_resolvers` or an explicit
`pihole_environment_variables.FTLCONF_dns_upstreams` value.

## Optional Traefik reverse proxy

Traefik is **disabled by default**. Existing Pi-hole web ports, DNS, and DHCP
behaviour do not change until you set `traefik_enabled: true`.

This collection deploys **rootful Docker Compose**, not Podman. Traefik uses
the Docker-compatible API over a local Unix socket. That socket is
security-sensitive (root-equivalent on the host). This role never exposes it
over TCP.

```text
                     LAN
                      │
                DNS resolves
            service.lab.example.com
                      │
                      ▼
             ┌─────────────────┐
             │     Traefik     │
             │ :80  → HTTPS    │
             │ :443 TLS        │
             └────────┬────────┘
                      │
                proxy network
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
     Pi-hole       Homepage      Future app
    web :80         :3000          :xxxx
```

### Requirements

- Docker API socket on the host (default `/var/run/docker.sock`)
- A DNS zone you control if you use Let's Encrypt DNS-01
- Provider-specific ACME credentials in Ansible Vault (`traefik_acme_environment`)
- LAN DNS that points `*.your.domain` (or each hostname) at the Traefik host
  or keepalived VIP — not at a public home IP

### Basic example

```yaml
traefik_enabled: true
traefik_domain: home.example.com
traefik_acme_email: admin@example.com
traefik_acme_dns_provider: cloudflare
traefik_acme_environment:
  CLOUDFLARE_DNS_API_TOKEN: "{{ vault_cloudflare_token }}"
```

Pi-hole is then published at `https://pihole.home.example.com` (`pihole_proxy_hostname`).
Each node also accepts `https://<inventory_hostname>.<traefik_domain>/admin`
(for example `pihole-01.home.example.com`), which stays on that node. The
shared name follows the keepalived VIP.
HTTP on port 80 redirects permanently to HTTPS. Traefik is pinned to
`traefik_image`/`traefik_version` (currently `docker.io/library/traefik:v3.7.13`).

TLS modes:

- `dns01` — Let's Encrypt DNS-01 (default). Can request `domain` plus `*.domain`.
- `supplied` — you provide `traefik_tls_cert_src` and `traefik_tls_key_src`.
- `internal_acme` — not implemented; the role fails rather than minting a
  self-signed certificate and calling that finished.

Containers are **not** exposed unless they set `traefik.enable=true`.
`exposedByDefault` is false.

When Traefik is enabled, Pi-hole keeps DNS 53 (and DHCP 67 if configured) on the
host and stops publishing 80/443 so Traefik can bind them. Host-networked
Pi-hole is not converted to bridge networking; that mode requires moving
Pi-hole's web port off 80/443 and setting `pihole_proxy_backend_port`.

If you use Nebula Sync, point `nebula_sync_*_url` at the HTTPS hostname (or
another reachable API URL) after the web port is no longer published on the
host.

Optional LAN wildcard DNS through Pi-hole (off the public internet):

```yaml
pihole_proxy_dns_enabled: true
pihole_proxy_dns_domain: home.example.com
# empty → keepalived VIP when set, otherwise the host IPv4
pihole_proxy_dns_target: ""
```

That writes `etc/dnsmasq.d/99-proxy-dns.conf` at mode `0644` in a `0755`
directory. Do not tighten those modes: FTL 2026.09.0+ runs as UID 1000 and will
not bind port 53 if it cannot read `/etc/dnsmasq.d`.

### Adding another application

1. Attach the container to the shared `proxy` network (default `traefik_network_name`).
2. Set Traefik labels, including an explicit backend port.
3. Create LAN DNS for the hostname (or rely on the optional wildcard).

```yaml
# Example: Homepage (or any other labelled container)
services:
  homepage:
    image: ghcr.io/gethomepage/homepage:<pinned-tag>
    networks:
      - proxy
    labels:
      traefik.enable: "true"
      traefik.docker.network: "proxy"
      traefik.http.routers.homepage.rule: "Host(`home.example.com`)"
      traefik.http.routers.homepage.entrypoints: "websecure"
      traefik.http.routers.homepage.tls: "true"
      traefik.http.routers.homepage.tls.certresolver: "letsencrypt"
      traefik.http.services.homepage.loadbalancer.server.port: "3000"
```

Starting that container is enough for Traefik to route it. Removing it drops
the route. You do not restart Traefik or rerun Ansible for discovery.

The dashboard stays off (`traefik_dashboard_enabled: false`). If you enable it,
it is only reachable through an authenticated HTTPS router.

See [`roles/traefik/README.md`](roles/traefik/README.md) and
[`docs/architecture.md`](docs/architecture.md).

By default the Unbound role chooses a pinned image from
`unbound_image_arch_map` using the target host architecture:

```yaml
unbound_image: ""  # empty means auto-select
unbound_image_arch_map:
  x86_64: "mvance/unbound:1.19.3"
  amd64: "mvance/unbound:1.19.3"
  aarch64: "vincejv/unbound:1.25.1"
  arm64: "vincejv/unbound:1.25.1"
  armv7l: "vincejv/unbound:1.25.1"
```

Set `unbound_image` explicitly in inventory to override that selection. For Pi-hole v6, use `FTLCONF_dns_upstreams` rather than the older `PIHOLE_DNS_` variable:

```yaml
unbound_network_name: "dns_net"
pihole_network_name: "{{ unbound_network_name }}"
unbound_container_name: "unbound"
unbound_port: 5335
pihole_unbound_upstream: "{{ unbound_container_name }}#{{ unbound_port }}"

pihole_environment_variables:
  FTLCONF_dns_upstreams: "{{ pihole_unbound_upstream }}"
  FTLCONF_dns_listeningMode: "all"
```

When Pi-hole talks to Unbound on the shared Docker network, `unbound_publish_to_host` now defaults to `false`; publish Unbound only if you also want to query it directly from the host. If enabled, bind it explicitly (default loopback):

```yaml
unbound_publish_to_host: true
unbound_publish_host_ip: "127.0.0.1"
unbound_publish_host_port: 5335
```

Container resolver override is now explicit. By default Pi-hole does not override the
container resolver list. Enable only when needed for lab troubleshooting:

```yaml
pihole_override_container_resolver: true
pihole_startup_dns:
  - 8.8.8.8
  - 8.8.4.4
```

### `playbooks/update-pihole.yaml`

Faster follow-up runs (updates + Pi-hole-focused changes).

Both `bootstrap-pihole.yaml` and `update-pihole.yaml` use `serial: 1` for HA
nodes and keep the current node drained from keepalived VIP ownership until local
Pi-hole DNS passes. When Unbound is actually deployed for the node, the Unbound
probe runs from inside the Pi-hole container (`docker exec`) so Docker-network
upstream names (for example `unbound`) are resolved in the same network context
Pi-hole uses. After all nodes pass and rejoin, the playbooks verify DNS through
the VIP.

Keepalived health checks require both the configured Pi-hole container to be
running and Pi-hole DNS to answer functionally. When Unbound is enabled, the
check also probes Unbound (preferring the container's live IPv4 from
`docker inspect` so VIP health still works if Docker embedded DNS is down).
Container checks use `sg docker`
so they work under keepalived's script execution context. This prevents another
local DNS listener from masking a stopped Pi-hole container during HA failover.

Pi-hole container recreation is driven by Compose/configuration changes or an
explicit maintenance override:

```yaml
pihole_force_recreate: true
```

Docker NAT/firewall reconciliation for lab modes does not by itself force a
Pi-hole application-container recreate.

The Vagrant inventories set `docker_daemon_dns` and `pihole_docker_dns` to
public resolvers so Docker Hub image pulls and fresh Pi-hole gravity bootstrap
do not depend on guest-local stub or embedded Docker DNS before Pi-hole/Unbound
are healthy. Leave these unset or empty in production unless the host or
container needs an explicit resolver list. On lab hosts where Docker does not
manage iptables (typical Vagrant/`vagrant_env`), the Pi-hole role falls back to
Unbound's bridge IPv4 for `FTLCONF_dns_upstreams` because `127.0.0.11` is often
refused inside the container.

### `playbooks/backup-user.yaml`

Install a dump-only SSH user (`backup`) and `/usr/local/sbin/pihole-backup-dump`
on both HA nodes without draining keepalived, restarting Traefik, or rewriting
Pi-hole compose. The user has a locked password, sudo only for the
dump wrapper, and an exclusive forced-command authorized key (`/bin/bash`
shell so Rocky/RHEL sshd honours `command=`; not an interactive login).

Pass an **ed25519 public** key via gitignored inventory or extra-vars. Do not
commit live keys or private keys:

```bash
ansible-playbook -i inventory/rnet.yml playbooks/backup-user.yaml \
  -e backup_user_authorized_key_file=/path/to/id_ed25519_network_backup.pub
```

CI uses a disposable public key in `inventory/ci/group_vars/all.yml`. This
playbook is **not** part of `update-pihole.yaml`.

### `playbooks/keepalived.yaml`

Deploy or adjust keepalived HA between Pi-hole instances. Priorities and VIPs are inventory-driven (see comments in [`inventory/vagrant.yml`](inventory/vagrant.yml) for examples).

### `playbooks/sync.yaml`

Deploy [Nebula Sync](https://github.com/lovelaze/nebula-sync) on the **`nebula_sync_controller`** inventory group only (one orchestrator per primary→replica topology). Lab inventories define that group in [`inventory/vagrant.yml`](inventory/vagrant.yml) with `vagrant-pihole-01` as controller. The role defaults to pinned tag `v0.11.1`; override `nebula_sync_image_tag` to test a different version.

Nebula Sync defaults `nebula_sync_use_secret_files: true` so `PRIMARY` and `REPLICAS` credentials are written to mounted secret files (`PRIMARY_FILE` / `REPLICAS_FILE`) instead of plain env values where possible. The service directory, compose file, and optional `.env` file default to `root:root` ownership with non-world-readable modes. Secret files remain owned by UID/GID `1001` with mode `0400`, matching the upstream container user, and placeholder credentials are rejected by default.

### Playbook tags

Roles are tagged (e.g. `pihole`, `docker`, `unbound`, `traefik`, `ha`, `stopkeepalived`, `startkeepalived`; `sync.yaml` uses `nebulasync`, `nebula`, `sync`). Limit execution, for example:

```bash
ansible-playbook -i your/inventory.yml playbooks/bootstrap-pihole.yaml --tags pihole
```

## Molecule integration tests

Two Vagrant VMs run the real playbooks (see [`molecule/default/converge.yml`](molecule/default/converge.yml) and [`molecule/debian/converge.yml`](molecule/debian/converge.yml)).

### Layout

| Path | Purpose |
|------|---------|
| [`molecule/common/prepare.yml`](molecule/common/prepare.yml) | Shared prepare (Python, `dig`, `ip` — apt vs dnf by OS) |
| [`molecule/common/verify_ha.yml`](molecule/common/verify_ha.yml) | Shared verify orchestrator for focused tasks under `molecule/common/verify/` |
| `molecule/{scenario}/` | `molecule.yml`, `Vagrantfile`, `create.yml`, `destroy.yml`, thin `prepare.yml` / `verify.yml` |

**`molecule test`** sequence: **dependency** (same [`scripts/install-ansible-collections.sh`](scripts/install-ansible-collections.sh) as above), **syntax**, **create** (`vagrant up` in the scenario directory), **prepare**, **converge**, **verify**, and for HA/update scenarios **side_effect** then **verify** again, then **destroy**. Localhost lifecycle playbooks use `chdir: "{{ playbook_dir }}"` so Vagrant runs in the right folder.

The bundled scenarios intentionally omit Molecule's `idempotence` step because
the HA flow drains/resumes keepalived and can restart resolver/container
services during each converge.

### Requirements

- Molecule, Ansible, Vagrant, and **VirtualBox** or **libvirt** (`vagrant-libvirt`) as appropriate.
- Run Molecule from the **repository root** so paths and inventory links resolve.
- Vagrant inventories set `IdentitiesOnly=yes` in `ansible_ssh_common_args` so a busy
  `ssh-agent` does not exhaust MaxAuthTries before the Vagrant key (or password) is tried.
- **Lint:** CI runs [ansible-lint](https://ansible-lint.readthedocs.io/) on
  roles, playbooks, Molecule, and remote verification playbooks;
  [yamllint](https://yamllint.readthedocs.io/) covers their YAML inventories and
  configuration.
- Full `molecule test` with Vagrant providers is intended for local or self-hosted
  environments where Vagrant + provider support is guaranteed.

Provider-neutral remote functional tests live under
[`tests/remote/`](tests/remote/). They run the production bootstrap/update
playbooks and reusable verification against externally provisioned AWS
instances, lab VMs, or Raspberry Pi hardware.

### Scenarios

| Scenario | Path | Platforms |
|----------|------|-----------|
| `default` | [`molecule/default/`](molecule/default/) | **Ubuntu 24.04** (`bento/ubuntu-24.04`); HA bootstrap, verify, rolling `update-pihole`, post-update verify (Traefik off, HTTP+HTTPS on Pi-hole) |
| `debian` | [`molecule/debian/`](molecule/debian/) | Debian 12 — closer to Raspberry Pi OS; same HA + update sequence. VirtualBox: `bento/debian-12`. libvirt: `debian/bookworm64` (`bento/debian-12` has no libvirt provider) |
| `debian-traefik` | [`molecule/debian-traefik/`](molecule/debian-traefik/) | Debian 12 HA with Traefik enabled (supplied lab TLS; HTTP redirect + HTTPS UI) |
| `debian-traefik-http` | [`molecule/debian-traefik-http/`](molecule/debian-traefik-http/) | Debian 12 HA with Traefik enabled, TLS off (HTTP UI) |
| `nebula-sync-migration` | [`molecule/nebula-sync-migration/`](molecule/nebula-sync-migration/) | Seeds legacy plaintext credentials, then verifies migration to secret-file mode |
| `pihole-no-unbound` | [`molecule/pihole-no-unbound/`](molecule/pihole-no-unbound/) | Runs bootstrap and update workflows with Pi-hole-only DNS |

Examples:

```bash
molecule test                 # default = Ubuntu 24.04 HA
molecule test -s default
molecule test -s debian
molecule test -s debian-traefik
molecule test -s debian-traefik-http
molecule test -s nebula-sync-migration
molecule converge -s default    # iterate without full test sequence
```

### VirtualBox vs libvirt and inventory

Private guest IPs depend on the provider (see scenario `Vagrantfile`s such as [`molecule/default/Vagrantfile`](molecule/default/Vagrantfile) and [`molecule/debian/Vagrantfile`](molecule/debian/Vagrantfile)):

- **VirtualBox** — typically `192.168.56.0/24` → [`inventory/vagrant.yml`](inventory/vagrant.yml)
- **libvirt** — typically `192.168.121.0/24` → [`inventory/vagrant_libvirt.yml`](inventory/vagrant_libvirt.yml)

Molecule links inventory via `inventory/${MOLECULE_VAGRANT_INVENTORY:-vagrant.yml}` (basename only). Match **Vagrant’s provider** to the inventory file:

```bash
export VAGRANT_DEFAULT_PROVIDER=libvirt
export MOLECULE_VAGRANT_INVENTORY=vagrant_libvirt.yml
molecule test -s default
```

**Phase two (Raspberry Pi OS ARM)** is not a local Vagrant scenario. Use AWS
remote `platform_coverage: phase-two-pi-os-arm` (Debian 12 arm64 stand-in, or a
real Pi OS AMI via `AWS_PI_OS_AMI_ID`) or hardware listed under
[`tests/remote/inventories/example-pi.yml`](tests/remote/inventories/example-pi.yml).
See [Testing guide](docs/testing.md#test-phases).

### ARM64 local testing

VirtualBox on an x86_64 Linux host does not emulate ARM64 guests. For full-system
ARM64 validation, prefer real ARM64 hardware (for example a Raspberry Pi), an
ARM64 cloud VM, or a custom QEMU/libvirt aarch64 VM. Docker `buildx`/QEMU
binfmt can emulate ARM64 containers locally, but it is not equivalent to these
Vagrant scenarios because systemd, firewall, keepalived, Docker daemon, and
networking behavior are part of the test surface.

### Helper: `scripts/molecule-vagrant`

- **Interactive:** `./scripts/molecule-vagrant` — choose VirtualBox or libvirt, copy the printed exports/commands, or confirm to run `molecule test -s default`.
- **Non-interactive:** forwards to `molecule` and sets `MOLECULE_VAGRANT_INVENTORY` from `VAGRANT_DEFAULT_PROVIDER` when unset:

```bash
VAGRANT_DEFAULT_PROVIDER=libvirt ./scripts/molecule-vagrant test -s default
```

### Helper: `scripts/molecule-test-all`

Run all discovered Molecule scenarios in `molecule/*` (or pass a subset):

```bash
./scripts/molecule-test-all
./scripts/molecule-test-all default debian
./scripts/molecule-test-all pihole-no-unbound
./scripts/molecule-test-all --debian-only
VAGRANT_DEFAULT_PROVIDER=libvirt ./scripts/molecule-test-all
./scripts/molecule-test-all --list
```

Like `scripts/molecule-vagrant`, this helper auto-selects
`MOLECULE_VAGRANT_INVENTORY` from `VAGRANT_DEFAULT_PROVIDER` when unset
(`vagrant.yml` for VirtualBox, `vagrant_libvirt.yml` for libvirt/kvm).
It also selects the corresponding one-host inventory for the
`pihole-no-unbound` scenario.

For Vagrant/Molecule inventories (`vagrant_env: true`), roles skip disruptive
reboots after hostname and package-update changes to avoid long guest-network
waits during test runs.

## CI

### Test layers

| Layer | What runs | Where |
|-------|-----------|--------|
| **Unit** | Python checks for scripts (`default-container-images`, upstream image watch, AWS cleanup, update-pihole health gates) and HA playbook/Compose contracts | `tests/unit/`, PR-only job in `ci.yml` |
| **Static / dry-run** | ansible-lint, yamllint, playbook `--syntax-check`, check-mode `ci-bootstrap` and `update-pihole` | `ci.yml` on code changes (skipped for docs-only PRs) |
| **Molecule integration** | Full bootstrap/update on Vagrant VMs | Local / self-hosted (`molecule/*`) |
| **AWS integration** | Ephemeral EC2 → production playbooks → teardown | `rc-aws-remote-tests.yml`, `aws-remote-tests.yml` |

GitHub Actions workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
runs lint (ansible-lint, yamllint), installs dependencies via
[`scripts/install-ansible-collections.sh`](scripts/install-ansible-collections.sh),
and syntax-checks / check-modes selected playbooks against [`inventory/ci/`](inventory/ci/)
on GitHub-hosted Ubuntu 24.04 x64 and ARM64 runners.

Pull requests that touch only `docs/**` and `**/*.md` skip the heavy Ansible lint
and test matrix. Those PRs still run the PR title check and a lightweight
`CI checks complete` gate. Use `workflow_dispatch` to force a full run.

Hosted CI also runs lightweight safety checks for Molecule configuration files (YAML/schema
sanity) that do not require Vagrant or a VM provider. Full Molecule Vagrant scenarios remain
local/self-hosted validation steps.

CI tests the advertised ansible-core 2.20 and 2.21 support range. It also builds
and installs the collection artifact into an empty temporary collections path,
resolves its Galaxy dependencies, and syntax-checks playbooks from the installed
artifact rather than the source checkout.

The security workflow hard-fails on HIGH/CRITICAL findings in repository
content. It also uploads code-scanning SARIF for every default deployed
container image; image scans are report-only because those findings belong to
upstream images we do not build in this repository. Image targets are derived
from role defaults by `scripts/default-container-images.py`, so changing a
default pin updates the scan matrix without duplicating image names. The
GitHub matrix may also include retired image pins when GitHub code scanning
still expects those historical Trivy categories during PR alert comparison.
The scheduled weekly scan keeps upstream findings visible for periodic triage;
persistent Critical findings should trigger a pinned-image upgrade review.

The dedicated `pihole-no-unbound` Molecule scenario runs the real bootstrap and
update playbooks with public upstream resolvers. It verifies after each
workflow that Pi-hole resolves DNS without an Unbound container, shared Unbound
network, or Unbound health check dependency. Hosted CI runs Python unit tests in
`tests/unit/` so malformed, empty, incomplete, or floating `latest` scan
targets fail before Trivy jobs are created.

AWS EC2 workflows use ephemeral hosts and lifecycle hooks wired into
`tests/remote/run.sh`:

- `.github/workflows/rc-aws-remote-tests.yml` — **CI — Pi-hole: AWS EC2 (RC)** (`v*-rc*`, Ubuntu 26.04)
- `.github/workflows/aws-remote-tests.yml` — **CI — Pi-hole: AWS EC2 (remote tests)** (1st and 15th monthly on `master`, PR label `run-aws-tests`, or `workflow_dispatch`)
- `.github/workflows/pihole-image-watch.yml` — daily check for new `pihole/pihole` Docker tags (GitHub issue alert)
- `.github/workflows/deploy-lan-queue.yml` — **Release-Alert** (after successful master CI, enqueue that SHA to the LAN deploy queue only when it is the latest published GitHub Release)

Infrastructure (VPC subnet, OIDC role, SSH key pair) is provisioned in the
separate `AWS-Cloud/build-account-isolation/build/` Terraform stack. Apply that
stack and map `terraform output -json ansible_remote_test_configuration` to the
GitHub repository variables documented in `tests/remote/README.md`.

## Operational docs

- [Architecture](docs/architecture.md)
- [Production deployment](docs/production-deployment.md)
- [Git branch workflow](docs/git-branch-workflow.md)
- [Upgrade runbook](docs/upgrade-runbook.md)
- [Failover testing](docs/failover-testing.md)
- [Testing guide](docs/testing.md) — CI, Molecule, AWS remote, manual checks
- [Backup and restore](docs/backup-and-restore.md)
- [Secrets management](docs/secrets-management.md)
- [Knowledge vault (local graphify)](docs/knowledge-vault.md) — optional agent architecture map; `graphify-out/` stays local

### Releases and Ansible Galaxy

Collection metadata is in [`galaxy.yml`](galaxy.yml). The collection is published as **`steveyminecraft.pihole`** on [galaxy.ansible.com](https://galaxy.ansible.com/ui/collections/).

Releases and **git tags** are only created from **`master`**.
There is no manual release workflow or tag-push publish path.

Uses **[release-please](https://github.com/googleapis/release-please)** (same approach as [ansible-pihole-cluster](https://github.com/danylomikula/ansible-pihole-cluster)):

1. Merge topic PRs into **`master`**.
2. That push to **`master`** makes release-please open or update a
   **Release PR** targeting `master` (changelog + `galaxy.yml`
   version bump).
3. Merge the **Release PR** into **`master`** to create the **git tag**
   (`v*.*.*`), **GitHub release**, and **Galaxy publish**.

Use descriptive conventional commits on PRs so release-please can choose semver
correctly and generate useful release notes. Prefer a specific user-facing
summary such as `fix: reject floating latest image defaults` over a generic
message such as `fix: updates`.

Recommended commit style for high-signal release notes:

- Use `feat:` only for user-visible capabilities or behavior additions.
- Use `fix:` only for user-visible bug fixes or regressions.
- Use short imperative subjects that name the changed behavior, not the process.
- Avoid release-only noise commits (`fix: release`, `chore: updates`) unless they
  are truly user-facing and should appear in release notes.
- Keep release-maintenance/documentation-only work under `docs:`, `ci:`, or
  `chore:` so those entries do not crowd end-user change summaries.

PR quality scaffolding is now included in-repo:

- `.github/pull_request_template.md` prompts release-note summary, validation,
  and risk/rollback details.
- `.github/commit-message-template.txt` provides optional local commit-message
  guidance (`git config commit.template .github/commit-message-template.txt`).
- CI checks PR titles on pull requests for conventional commit format.

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| [Release](.github/workflows/release-please.yml) | Push to `master` only | Release PR; tag + GitHub release + Galaxy publish when the Release PR merges |
| [Release-Alert](.github/workflows/deploy-lan-queue.yml) | Successful master CI for the latest published GitHub Release | Enqueue that SHA to the LAN deploy queue |
| [Validate collection for Ansible Galaxy](.github/workflows/galaxy-publish.yml) | Push/PR to `master`, manual | Builds the collection artifact and runs `galaxy-importer` |

The Release workflow uses repository secret **`RELEASE_PLEASE_TOKEN`** for
opening release PRs and pushing RC tags used by AWS remote tests. Without a
valid token, release-please falls back to `GITHUB_TOKEN`, release PRs are
authored by `github-actions[bot]`, and CI may wait for manual workflow approval.
If the token is unavailable, RC tagging and AWS RC tests are skipped with a warning.
Add repository secret **`GALAXY_API_KEY`** (Galaxy → Preferences → API Key).

**Install a specific version**:

```bash
ansible-galaxy collection install steveyminecraft.pihole:==VERSION
```

Replace `VERSION` with the published release required, for example `1.9.2`. <!-- x-release-please-version -->

See [GitHub releases](https://github.com/steveyminecraft/ansible-pihole/releases) and [`CHANGELOG.md`](CHANGELOG.md) for version history.

The collection is licensed under Apache-2.0. Selected imported files retain
their original license notices; see [`LICENSES.md`](LICENSES.md).

Legacy Galaxy **roles** `steveyminecraft.ansible-pihole` and `steveyminecraft.docker-pihole` are superseded by this collection; use `ansible-galaxy collection install steveyminecraft.pihole` instead.
