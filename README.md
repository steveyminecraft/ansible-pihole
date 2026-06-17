# ansible-pihole

Bootstrap hosts with Ansible, install Docker and Pi-hole (optionally Unbound),
and optionally run **high availability** with keepalived plus config sync
(Nebula Sync).

Playbooks live under [`playbooks/`](playbooks/). Example inventories for CI and
Molecule are under [`inventory/`](inventory/); for real hardware you maintain
your own inventory (YAML or INI) with your hosts and variables.

For the upstream Pi-hole container image, see: https://github.com/pi-hole/docker-pi-hole

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

First-time (and repeatable) full bootstrap: system prep, Docker, optional Unbound,
Pi-hole, keepalived, etc. (see the play for the exact role list).

If Docker tasks fail on a first run, reboot the host and re-run.

Roles include (among others):

- [`bootstrap`](roles/bootstrap/tasks/main.yml): SSH key from GitHub (`github_user_for_ssh_key`), optional password lock, aliases, timezone, hostname, packages such as firewalld on Debian/Ubuntu.
- [`updates`](roles/updates/tasks/main.yml), [`sshd`](roles/sshd/tasks/main.yml), [`docker`](roles/docker/tasks/main.yml), [`unbound`](roles/unbound/tasks/main.yml), [`pihole`](roles/pihole/tasks/main.yml), [`keepalived`](roles/keepalived/tasks/main.yml), [`start_keepalived`](roles/start_keepalived/tasks/main.yml) / [`stop_keepalived`](roles/stop_keepalived/tasks/main.yml) as used in the play (FQCN prefix `steveyminecraft.pihole.` in playbooks).

On RedHat/Rocky hosts the Docker role installs `kernel-modules-extra` by default for Docker/netfilter support. If a real host already has the needed modules and `/boot` is too tight for kernel package changes, opt out in inventory:

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
policy fix is prepared.

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

Role-local variable naming now consistently uses the `pihole_` prefix to satisfy ansible-lint role scoping rules (for example `pihole_dir_loc`, `pihole_webport_http`, `pihole_docker_manage_iptables`). Existing inventories that still define legacy unprefixed names continue to work via compatibility lookups, but new configs should use the prefixed names.

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
running and Pi-hole DNS to answer functionally. Container checks use `sg docker`
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
container needs an explicit resolver list.

### `playbooks/keepalived.yaml`

Deploy or adjust keepalived HA between Pi-hole instances. Priorities and VIPs are inventory-driven (see comments in [`inventory/vagrant.yml`](inventory/vagrant.yml) for examples).

### `playbooks/sync.yaml`

Deploy [Nebula Sync](https://github.com/lovelaze/nebula-sync) on the **`nebula_sync_controller`** inventory group only (one orchestrator per primary→replica topology). Lab inventories define that group in [`inventory/vagrant.yml`](inventory/vagrant.yml) with `vagrant-pihole-01` as controller. The role defaults to pinned tag `v0.11.1`; override `nebula_sync_image_tag` to test a different version.

Nebula Sync defaults `nebula_sync_use_secret_files: true` so `PRIMARY` and `REPLICAS` credentials are written to mounted secret files (`PRIMARY_FILE` / `REPLICAS_FILE`) instead of plain env values where possible. The role defaults ownership to UID/GID `1001`, matching the upstream container user, and rejects placeholder credentials by default.

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
| [`molecule/common/verify_ha.yml`](molecule/common/verify_ha.yml) | Shared verify orchestrator for focused tasks under `molecule/common/verify/` |
| `molecule/{scenario}/` | `molecule.yml`, `Vagrantfile`, `create.yml`, `destroy.yml`, thin `prepare.yml` / `verify.yml` |

**`molecule test`** sequence: **dependency** (same [`scripts/install-ansible-collections.sh`](scripts/install-ansible-collections.sh) as above), **syntax**, **create** (`vagrant up` in the scenario directory), **prepare**, **converge**, **verify**, **destroy**. Localhost lifecycle playbooks use `chdir: "{{ playbook_dir }}"` so Vagrant runs in the right folder.

The bundled scenarios intentionally omit Molecule's `idempotence` step because
the HA flow drains/resumes keepalived and can restart resolver/container
services during each converge.

### Requirements

- Molecule, Ansible, Vagrant, and **VirtualBox** or **libvirt** (`vagrant-libvirt`) as appropriate.
- Run Molecule from the **repository root** so paths and inventory links resolve.
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
| `ubuntu` | [`molecule/ubuntu/`](molecule/ubuntu/) | Ubuntu 24.04 (`bento/ubuntu-24.04`) |
| `ubuntu-26.04` | [`molecule/ubuntu-26.04/`](molecule/ubuntu-26.04/) | Ubuntu 26.04 — VirtualBox: `konstruktoid/ubuntu-26.04` (Bento); libvirt: `cloud-image/ubuntu-26.04` |
| `default` | [`molecule/default/`](molecule/default/) | Rocky-style box (see `molecule.yml`) |
| `nebula-sync-migration` | [`molecule/nebula-sync-migration/`](molecule/nebula-sync-migration/) | Seeds legacy plaintext credentials, then verifies migration to secret-file mode |
| `pihole-no-unbound` | [`molecule/pihole-no-unbound/`](molecule/pihole-no-unbound/) | Runs bootstrap and update workflows with Pi-hole-only DNS |

Examples:

```bash
molecule test -s ubuntu
molecule test -s ubuntu-26.04
molecule test -s nebula-sync-migration
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
./scripts/molecule-test-all pihole-no-unbound
./scripts/molecule-test-all --ubuntu-only
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

GitHub Actions workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
runs lint (ansible-lint, yamllint), installs dependencies via
[`scripts/install-ansible-collections.sh`](scripts/install-ansible-collections.sh),
and syntax-checks / check-modes selected playbooks against [`inventory/ci/`](inventory/ci/)
on GitHub-hosted Ubuntu 24.04 x64 and ARM64 runners.

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
default pin updates the scan matrix without duplicating image names.
The scheduled weekly scan keeps upstream findings visible for periodic triage;
persistent Critical findings should trigger a pinned-image upgrade review.

The dedicated `pihole-no-unbound` Molecule scenario runs the real bootstrap and
update playbooks with public upstream resolvers. It verifies after each
workflow that Pi-hole resolves DNS without an Unbound container, shared Unbound
network, or Unbound health check dependency. Hosted CI also unit tests the
default-image matrix so malformed, empty, incomplete, or floating `latest` scan
targets fail before Trivy jobs are created.

AWS remote functional tests use ephemeral EC2 hosts and lifecycle hooks wired
into `tests/remote/run.sh`:

- `.github/workflows/rc-aws-remote-tests.yml` — RC tags (`v*-rc*`), Ubuntu 26.04
- `.github/workflows/aws-remote-tests.yml` — manual dispatch and weekly smoke

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
- [Backup and restore](docs/backup-and-restore.md)
- [Secrets management](docs/secrets-management.md)

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
| [Validate collection for Ansible Galaxy](.github/workflows/galaxy-publish.yml) | Push/PR to `master`, manual | Builds the collection artifact and runs `galaxy-importer` |

Add repository secret **`GALAXY_API_KEY`** (Galaxy → Preferences → API Key).

**Install a specific version**:

```bash
ansible-galaxy collection install steveyminecraft.pihole:==VERSION
```

Replace `VERSION` with the published release required, for example `1.3.0`. <!-- x-release-please-version -->

See [GitHub releases](https://github.com/steveyminecraft/ansible-pihole/releases) and [`CHANGELOG.md`](CHANGELOG.md) for version history.

The collection is licensed under Apache-2.0. Selected imported files retain
their original license notices; see [`LICENSES.md`](LICENSES.md).

Legacy Galaxy **roles** `steveyminecraft.ansible-pihole` and `steveyminecraft.docker-pihole` are superseded by this collection; use `ansible-galaxy collection install steveyminecraft.pihole` instead.
