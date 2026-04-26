# ansible-pihole

Bootstrap hosts with Ansible, install Docker and Pi-hole (optionally Unbound), and optionally run **high availability** with keepalived plus config sync (Nebula Sync).

Playbooks live under [`playbooks/`](playbooks/). Example inventories for CI and Molecule are under [`inventory/`](inventory/); for real hardware you maintain your own inventory (YAML or INI) with your hosts and variables.

For the upstream Pi-hole container image, see: https://github.com/pi-hole/docker-pi-hole

## Controller setup (your laptop or CI)

- Install [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/index.html) (ansible-core 2.15+ is a practical minimum; CI pins a newer release in [`.github/workflows/ci.yml`](.github/workflows/ci.yml)).
- Clone this repo and from the **repository root** run:

```bash
./scripts/install-ansible-collections.sh
```

This installs Galaxy **roles** ([`roles/requirements.yml`](roles/requirements.yml)), **`ansible.posix` from git** (branch with the ansible-core 2.24-safe imports from [ansible.posix PR #690](https://github.com/ansible-collections/ansible.posix/pull/690) until a Galaxy release includes it), then **collections** listed in [`collections/requirements.yml`](collections/requirements.yml). **Git** is required for that `ansible.posix` step.

Ansible uses [`ansible.cfg`](ansible.cfg) (`roles_path`, `collections_path`). Re-run the script after changing dependency files.

## Base setup (targets)

- Targets can be **Raspberry Pi OS** (as originally documented) or other Linux distros supported by the roles (Molecule uses Ubuntu 24.04 and Rocky-style images).
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
- [`updates`](roles/updates/tasks/main.yml), [`sshd`](roles/sshd/tasks/main.yml), [`docker`](roles/docker/tasks/main.yml), [`unbound`](roles/unbound/tasks/main.yml), [`pihole`](roles/pihole/tasks/main.yml) (often from Galaxy; see [`roles/requirements.yml`](roles/requirements.yml)), [`keepalived`](roles/keepalived/tasks/main.yml), [`start_keepalived`](roles/start_keepalived/tasks/main.yml) / [`stop_keepalived`](roles/stop_keepalived/tasks/main.yml) as used in the play.

Pi-hole-related variables (e.g. `pihole_environment_variables`, `pihole_ha_mode`, `pihole_vip_ipv4` / `pihole_vip_ipv6`) are typically set in inventory; see the [docker-pi-hole environment docs](https://github.com/pi-hole/docker-pi-hole#environment-variables) for image variables.

### `playbooks/update-pihole.yaml`

Faster follow-up runs (updates + Pi-hole-focused changes).

### `playbooks/keepalived.yaml`

Deploy or adjust keepalived HA between Pi-hole instances. Priorities and VIPs are inventory-driven (see comments in [`inventory/vagrant.yml`](inventory/vagrant.yml) for examples).

### `playbooks/sync.yaml`

Deploy [Nebula Sync](https://github.com/lovelaze/nebula-sync) via [`roles/nebula_sync`](roles/nebula_sync/tasks/main.yml). Override `nebula_sync_image_tag` in inventory if you do not want `latest`.

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
| [`molecule/common/verify_ha.yml`](molecule/common/verify_ha.yml) | Shared verify (keepalived, firewalld, DNS, Pi-hole container checks) |
| `molecule/<scenario>/` | `molecule.yml`, `Vagrantfile`, `create.yml`, `destroy.yml`, thin `prepare.yml` / `verify.yml` |

**`molecule test`** sequence: **dependency** (same [`scripts/install-ansible-collections.sh`](scripts/install-ansible-collections.sh) as above), **syntax**, **create** (`vagrant up` in the scenario directory), **prepare**, **converge**, **verify**, **destroy**. Localhost lifecycle playbooks use `chdir: "{{ playbook_dir }}"` so Vagrant runs in the right folder.

For **idempotence** tuning (second converge should report no changes), run `molecule converge` twice after `molecule create`, or add an `idempotence` step in the scenario `molecule.yml` once the stack is idempotent enough.

### Requirements

- Molecule, Ansible, Vagrant, and **VirtualBox** or **libvirt** (`vagrant-libvirt`) as appropriate.
- Run Molecule from the **repository root** so paths and inventory links resolve.
- **Lint:** CI runs [ansible-lint](https://ansible-lint.readthedocs.io/) on `roles`, `playbooks`, and `molecule`; [yamllint](https://yamllint.readthedocs.io/) includes `molecule/`.

### Scenarios

| Scenario | Path | Platforms |
|----------|------|-----------|
| `ubuntu` | [`molecule/ubuntu/`](molecule/ubuntu/) | Ubuntu 24.04 (`bento/ubuntu-24.04`) |
| `default` | [`molecule/default/`](molecule/default/) | Rocky-style box (see `molecule.yml`) |

Examples:

```bash
molecule test -s ubuntu
molecule converge -s ubuntu    # iterate without full test sequence
```

### VirtualBox vs libvirt and inventory

Private guest IPs depend on the provider (see [`molecule/ubuntu/Vagrantfile`](molecule/ubuntu/Vagrantfile)):

- **VirtualBox** — typically `192.168.56.0/24` → [`inventory/vagrant.yml`](inventory/vagrant.yml)
- **libvirt** — typically `192.168.121.0/24` → [`inventory/vagrant_libvirt.yml`](inventory/vagrant_libvirt.yml)

Molecule links inventory via `inventory/${MOLECULE_VAGRANT_INVENTORY:-vagrant.yml}` (basename only). Match **Vagrant’s provider** to the inventory file:

```bash
export VAGRANT_DEFAULT_PROVIDER=libvirt
export MOLECULE_VAGRANT_INVENTORY=vagrant_libvirt.yml
molecule test -s ubuntu
```

### Helper: `scripts/molecule-vagrant`

- **Interactive:** `./scripts/molecule-vagrant` — choose VirtualBox or libvirt, copy the printed exports/commands, or confirm to run `molecule test -s ubuntu`.
- **Non-interactive:** forwards to `molecule` and sets `MOLECULE_VAGRANT_INVENTORY` from `VAGRANT_DEFAULT_PROVIDER` when unset:

```bash
VAGRANT_DEFAULT_PROVIDER=libvirt ./scripts/molecule-vagrant test -s ubuntu
```

## CI

GitHub Actions workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs lint (ansible-lint, yamllint), installs dependencies via [`scripts/install-ansible-collections.sh`](scripts/install-ansible-collections.sh), and syntax-checks / check-modes selected playbooks against [`inventory/ci/`](inventory/ci/).
