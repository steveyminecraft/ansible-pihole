# ansible-pihole

Bootstrap hosts with Ansible, install Docker and Pi-hole (optionally Unbound), and optionally run **high availability** with keepalived plus config sync (Nebula Sync).

Playbooks live under [`playbooks/`](playbooks/). Example inventories for CI and Molecule are under [`inventory/`](inventory/); for real hardware you maintain your own inventory (YAML or INI) with your hosts and variables.

For the upstream Pi-hole container image, see: https://github.com/pi-hole/docker-pi-hole

## Controller setup (your laptop or CI)

- **ansible-core 2.20.x** (see [`requirements.txt`](requirements.txt)).
- **Python 3.13 or 3.14** for the controller (CI tests both; Ubuntu 26.04 ships 3.14—see [`.python-version`](.python-version)).

```bash
./scripts/setup-env.sh
source env/bin/activate
./scripts/install-ansible-collections.sh
ansible --version   # ansible-core 2.20.x from env/bin/ansible
```

Manual venv (if you prefer): `python3.13 -m venv env` or `python3.14 -m venv env`, then `pip install -r requirements.txt`.

This repository is an **Ansible collection** published as **`steveyminecraft.pihole`** on [Ansible Galaxy](https://galaxy.ansible.com/ui/collections/). Collection metadata is in [`galaxy.yml`](galaxy.yml); runtime requirements are in [`meta/runtime.yml`](meta/runtime.yml).

**From Galaxy** (consumers):

```bash
ansible-galaxy collection install steveyminecraft.pihole
```

**From a git clone** (development):

```bash
./scripts/install-ansible-collections.sh
```

That script builds and installs this collection locally, installs **`ansible.posix` from git** (merged [ansible.posix PR #690](https://github.com/ansible-collections/ansible.posix/pull/690) until a Galaxy release includes it), then installs dependencies in [`collections/requirements.yml`](collections/requirements.yml). **Git** is required for the `ansible.posix` step.

[`ansible.cfg`](ansible.cfg) sets `roles_path`, `collections_path`, and disables top-level fact injection so roles use `ansible_facts[...]` with ansible-core 2.20+. Playbooks reference roles by FQCN (for example `steveyminecraft.pihole.pihole`). Re-run the install script after changing [`galaxy.yml`](galaxy.yml) or [`collections/requirements.yml`](collections/requirements.yml).

The Pi-hole Docker role lives in this collection as [`roles/pihole`](roles/pihole/) (sourced from [`docker-pihole`](https://github.com/steveyminecraft/docker-pihole) with ansible-pihole compatibility changes applied in-tree).

## Base setup (targets)

- Targets can be **Raspberry Pi OS** (as originally documented) or other Linux distros supported by the roles (Molecule uses Ubuntu 24.04, Ubuntu 26.04, and Rocky-style images).
- The [openssh_keypair](https://docs.ansible.com/ansible/latest/collections/community/crypto/openssh_keypair_module.html) collection module is pulled in via `collections/requirements.yml`.
- **Headless Pi** (if applicable): enable SSH, configure user and networking, set static IPs (DHCP reservation is enough).
- **Inventory:** define hosts and group vars (see examples in [`inventory/vagrant.yml`](inventory/vagrant.yml) for lab-style vars such as `pihole_*`, `nebula_sync_*`, VIPs). There is no single checked-in “production” inventory filename; use `-i` pointing at your file.

## Playbooks

Run from the repo root, for example:

```bash
ansible-playbook -i /path/to/your/inventory.yml playbooks/bootstrap-pihole.yaml
```

### `playbooks/bootstrap-pihole.yaml`

First-time (and repeatable) full bootstrap: system prep, Docker, Unbound, Pi-hole, keepalived, etc. (see the play for the exact role list).

If Docker tasks fail on a first run, reboot the host and re-run.

Roles include (among others):

- [`bootstrap`](roles/bootstrap/tasks/main.yml): SSH key from GitHub (`github_user_for_ssh_key`), optional password lock, aliases, timezone, hostname, packages such as firewalld on Debian/Ubuntu.
- [`updates`](roles/updates/tasks/main.yml), [`sshd`](roles/sshd/tasks/main.yml), [`docker`](roles/docker/tasks/main.yml), [`unbound`](roles/unbound/tasks/main.yml), [`pihole`](roles/pihole/tasks/main.yml), [`keepalived`](roles/keepalived/tasks/main.yml), [`start_keepalived`](roles/start_keepalived/tasks/main.yml) / [`stop_keepalived`](roles/stop_keepalived/tasks/main.yml) as used in the play (FQCN prefix `steveyminecraft.pihole.` in playbooks).

On RedHat/Rocky hosts the Docker role installs `kernel-modules-extra` by default for Docker/netfilter support. If a real host already has the needed modules and `/boot` is too tight for kernel package changes, opt out in inventory:

```yaml
docker_install_kernel_modules_extra: false
```

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

Role-local variable naming now consistently uses the `pihole_` prefix to satisfy ansible-lint role scoping rules (for example `pihole_dir_loc`, `pihole_webport_http`, `pihole_docker_manage_iptables`). Existing inventories that still define legacy unprefixed names continue to work via compatibility fallbacks, but new configs should use the prefixed names.

Security defaults:

- `FTLCONF_webserver_api_password` must be provided from inventory/vault and should be at least 16 characters.
- Known placeholders/defaults (`Testing 101`, `Intranet`, `CHANGE_ME`, empty value) are rejected by role assertions.
- Pi-hole compose files are rendered with root-only permissions (`0600`) in both normal and Unbound integration paths.

Unbound is deployed before Pi-hole and can be used as Pi-hole's upstream resolver over a shared Docker network. By default the Unbound role now chooses an image from `unbound_image_arch_map` using the target host architecture:

```yaml
unbound_image: ""  # empty means auto-select
unbound_image_arch_map:
  x86_64: "mvance/unbound:latest"
  amd64: "mvance/unbound:latest"
  aarch64: "vincejv/unbound:latest"
  arm64: "vincejv/unbound:latest"
  armv7l: "vincejv/unbound:latest"
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

Both `bootstrap-pihole.yaml` and `update-pihole.yaml` include post-task DNS checks.
When Unbound integration is enabled, the Unbound probe now runs from inside the
Pi-hole container (`docker exec`) so Docker-network upstream names (for example
`unbound`) are resolved in the same network context Pi-hole uses.

### `playbooks/keepalived.yaml`

Deploy or adjust keepalived HA between Pi-hole instances. Priorities and VIPs are inventory-driven (see comments in [`inventory/vagrant.yml`](inventory/vagrant.yml) for examples).

### `playbooks/sync.yaml`

Deploy [Nebula Sync](https://github.com/lovelaze/nebula-sync) via [`roles/nebula_sync`](roles/nebula_sync/tasks/main.yml). Override `nebula_sync_image_tag` in inventory if you do not want `latest`.

Nebula Sync now defaults `nebula_sync_use_secret_files: true` so `PRIMARY` and `REPLICAS` credentials are written to mounted secret files (`PRIMARY_FILE` / `REPLICAS_FILE`) instead of plain env values where possible. The role defaults ownership to UID/GID `1001`, matching the upstream container user, and rejects placeholder credentials by default.

### Playbook tags

Roles are tagged (e.g. `pihole`, `docker`, `unbound`, `ha`, `stopkeepalived`, `startkeepalived`; `sync.yaml` uses `nebulasync`, `nebula`, `sync`). Limit execution, for example:

```bash
ansible-playbook -i your/inventory.yml playbooks/bootstrap-pihole.yaml --tags pihole
```

## Molecule integration tests

Two Vagrant VMs run the real playbooks (see [`molecule/ubuntu/converge.yml`](molecule/ubuntu/converge.yml) and [`molecule/default/converge.yml`](molecule/default/converge.yml)).

### Layout

| Path | Purpose |
|------|---------|
| [`molecule/common/prepare.yml`](molecule/common/prepare.yml) | Shared prepare (Python, `dig`, `ip` — apt vs dnf by OS) |
| [`molecule/common/verify_ha.yml`](molecule/common/verify_ha.yml) | Shared verify (keepalived, firewalld, DNS, Nebula Sync when inventory sets it, Pi-hole container failover) |
| `molecule/<scenario>/` | `molecule.yml`, `Vagrantfile`, `create.yml`, `destroy.yml`, thin `prepare.yml` / `verify.yml` |

**`molecule test`** sequence: **dependency** (same [`scripts/install-ansible-collections.sh`](scripts/install-ansible-collections.sh) as above), **syntax**, **create** (`vagrant up` in the scenario directory), **prepare**, **converge**, **verify**, **destroy**. Localhost lifecycle playbooks use `chdir: "{{ playbook_dir }}"` so Vagrant runs in the right folder.

The bundled scenarios intentionally omit Molecule's `idempotence` step because
the HA flow drains/resumes keepalived and can restart resolver/container
services during each converge.

### Requirements

- Molecule, Ansible, Vagrant, and **VirtualBox** or **libvirt** (`vagrant-libvirt`) as appropriate.
- Run Molecule from the **repository root** so paths and inventory links resolve.
- **Lint:** CI runs [ansible-lint](https://ansible-lint.readthedocs.io/) on `roles`, `playbooks`, and `molecule`; [yamllint](https://yamllint.readthedocs.io/) includes `molecule/`.
- Full `molecule test` with Vagrant providers is intended for local or self-hosted
  environments where Vagrant + provider support is guaranteed.

### Scenarios

| Scenario | Path | Platforms |
|----------|------|-----------|
| `ubuntu` | [`molecule/ubuntu/`](molecule/ubuntu/) | Ubuntu 24.04 (`bento/ubuntu-24.04`) |
| `ubuntu-26.04` | [`molecule/ubuntu-26.04/`](molecule/ubuntu-26.04/) | Ubuntu 26.04 — VirtualBox: `konstruktoid/ubuntu-26.04` (Bento); libvirt: `cloud-image/ubuntu-26.04` |
| `default` | [`molecule/default/`](molecule/default/) | Rocky-style box (see `molecule.yml`) |

Examples:

```bash
molecule test -s ubuntu
molecule test -s ubuntu-26.04
molecule converge -s ubuntu    # iterate without full test sequence
```

### VirtualBox vs libvirt and inventory

Private guest IPs depend on the provider (see scenario `Vagrantfile`s such as [`molecule/ubuntu/Vagrantfile`](molecule/ubuntu/Vagrantfile) and [`molecule/ubuntu-26.04/Vagrantfile`](molecule/ubuntu-26.04/Vagrantfile)):

- **VirtualBox** — typically `192.168.56.0/24` → [`inventory/vagrant.yml`](inventory/vagrant.yml)
- **libvirt** — typically `192.168.121.0/24` → [`inventory/vagrant_libvirt.yml`](inventory/vagrant_libvirt.yml)

Molecule links inventory via `inventory/${MOLECULE_VAGRANT_INVENTORY:-vagrant.yml}` (basename only). Match **Vagrant’s provider** to the inventory file:

```bash
export VAGRANT_DEFAULT_PROVIDER=libvirt
export MOLECULE_VAGRANT_INVENTORY=vagrant_libvirt.yml
molecule test -s ubuntu
```

**`ubuntu-26.04`:** do not use `cloud-image/ubuntu-26.04` on VirtualBox (vmwgfx DRM errors). The scenario [`Vagrantfile`](molecule/ubuntu-26.04/Vagrantfile) selects **`konstruktoid/ubuntu-26.04`** (Bento build) for VirtualBox and **`cloud-image/ubuntu-26.04`** only for libvirt. After changing boxes, run `molecule destroy -s ubuntu-26.04` then `molecule test -s ubuntu-26.04`.

### ARM64 local testing

VirtualBox on an x86_64 Linux host does not emulate ARM64 guests. For full-system
ARM64 validation, prefer real ARM64 hardware (for example a Raspberry Pi), an
ARM64 cloud VM, or a custom QEMU/libvirt aarch64 VM. Docker `buildx`/QEMU
binfmt can emulate ARM64 containers locally, but it is not equivalent to these
Vagrant scenarios because systemd, firewall, keepalived, Docker daemon, and
networking behavior are part of the test surface.

### Helper: `scripts/molecule-vagrant`

- **Interactive:** `./scripts/molecule-vagrant` — choose VirtualBox or libvirt, copy the printed exports/commands, or confirm to run `molecule test -s ubuntu`.
- **Non-interactive:** forwards to `molecule` and sets `MOLECULE_VAGRANT_INVENTORY` from `VAGRANT_DEFAULT_PROVIDER` when unset:

```bash
VAGRANT_DEFAULT_PROVIDER=libvirt ./scripts/molecule-vagrant test -s ubuntu
```

### Helper: `scripts/molecule-test-all`

Run all discovered Molecule scenarios in `molecule/*` (or pass a subset):

```bash
./scripts/molecule-test-all
./scripts/molecule-test-all ubuntu ubuntu-26.04
./scripts/molecule-test-all --ubuntu-only
VAGRANT_DEFAULT_PROVIDER=libvirt ./scripts/molecule-test-all
./scripts/molecule-test-all --list
```

Like `scripts/molecule-vagrant`, this helper auto-selects
`MOLECULE_VAGRANT_INVENTORY` from `VAGRANT_DEFAULT_PROVIDER` when unset
(`vagrant.yml` for VirtualBox, `vagrant_libvirt.yml` for libvirt/kvm).

For Vagrant/Molecule inventories (`vagrant_env: true`), the bootstrap role now
skips rebooting after hostname file updates to avoid long guest-network waits
during test runs.

### `scripts/word_analysis.py`

Small utility to count **total words**, **unique word types**, type–token ratio, and per-word frequencies from a text file or stdin:

```bash
./scripts/word_analysis.py path/to/file.txt
echo 'some text' | ./scripts/word_analysis.py
./scripts/word_analysis.py --json --sort alpha notes.md
```

## CI

GitHub Actions workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
runs lint (ansible-lint, yamllint), installs dependencies via
[`scripts/install-ansible-collections.sh`](scripts/install-ansible-collections.sh),
and syntax-checks / check-modes selected playbooks against [`inventory/ci/`](inventory/ci/)
on GitHub-hosted Ubuntu 24.04 x64 and ARM64 runners.

Hosted CI also runs lightweight safety checks for Molecule configuration files (YAML/schema
sanity) that do not require Vagrant or a VM provider. Full Molecule Vagrant scenarios remain
local/self-hosted validation steps.

## Operational docs

- [Architecture](docs/architecture.md)
- [Production deployment](docs/production-deployment.md)
- [Upgrade runbook](docs/upgrade-runbook.md)
- [Failover testing](docs/failover-testing.md)
- [Backup and restore](docs/backup-and-restore.md)
- [Secrets management](docs/secrets-management.md)

### Releases and Ansible Galaxy

Collection metadata is in [`galaxy.yml`](galaxy.yml). The collection is published as **`steveyminecraft.pihole`** on [galaxy.ansible.com](https://galaxy.ansible.com/ui/collections/).

Releases and **git tags** are only created from **`master`** (not `dev` or topic branches). There is no manual release workflow or tag-push publish path.

Uses **[release-please](https://github.com/googleapis/release-please)** (same approach as [ansible-pihole-cluster](https://github.com/danylomikula/ansible-pihole-cluster)):

1. Land work on **`dev`**, then open a PR **`dev` → `master`** and merge (promotion to the release branch).
2. That push to **`master`** makes release-please open or update a **Release PR** targeting `master` (changelog + `galaxy.yml` version bump).
3. Merge the **Release PR** into **`master`** to create the **git tag** (`v*.*.*`), **GitHub release**, and **Galaxy publish**.

Use conventional commits on PRs (`feat:`, `fix:`, etc.) so release-please can choose semver correctly.

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| [Release](.github/workflows/release-please.yml) | Push to `master` only | Release PR; tag + GitHub release + Galaxy publish when the Release PR merges |
| [Validate collection for Ansible Galaxy](.github/workflows/galaxy-publish.yml) | Push/PR to `master`, manual | Builds the collection artifact and runs `galaxy-importer` |

Add repository secret **`GALAXY_API_KEY`** (Galaxy → Preferences → API Key).

**Install a specific version:**

```bash
ansible-galaxy collection install steveyminecraft.pihole:==1.1.0
```

See [GitHub releases](https://github.com/steveyminecraft/ansible-pihole/releases) and [`CHANGELOG.md`](CHANGELOG.md) for version history.

Legacy Galaxy **roles** `steveyminecraft.ansible-pihole` and `steveyminecraft.docker-pihole` are superseded by this collection; use `ansible-galaxy collection install steveyminecraft.pihole` instead.
