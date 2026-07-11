# Testing guide

Single index for how this collection is validated: GitHub CI, local Molecule,
AWS remote tests, and manual production checks.

## Coverage at a glance

| Layer | Where it runs | What it proves | Gap |
|-------|---------------|----------------|-----|
| **GitHub CI** | Every PR (code paths) | Lint, syntax, check-mode bootstrap + `update-pihole`, compose validation, script unit tests, inventory structure, **Molecule `docker-ci` smoke** | No functional HA failover on hosted runners |
| **Molecule** | Local / self-hosted | Full Vagrant HA bootstrap, rolling update, post-update verify | HA scenarios not in default GitHub matrix (needs Vagrant) |
| **AWS remote** | Scheduled + label + manual | Ephemeral EC2 → production playbooks → teardown | Cost; amd64-only on schedule/label |
| **Manual** | Production change windows | VIP failover, per-node DNS, Nebula Sync | Operator-driven |

---

## GitHub CI (`.github/workflows/ci.yml`)

**Triggers:** pull requests and pushes to `master`.

**Docs-only PRs** skip the heavy Ansible matrix when only documentation changes
(path filter with `predicate-quantifier: every`).

| Job | Purpose |
|-----|---------|
| PR title check | Conventional commit format on PR titles |
| Lint | `ansible-lint`, `yamllint`, Molecule YAML schema smoke |
| Ansible tests (Ubuntu matrix) | Syntax + check-mode for `bootstrap-pihole.yaml`, `update-pihole.yaml`; `ci-validate-pihole-modes.yaml` |
| Policy & script validation | Python unit tests, `validate-secure-defaults.py`, `validate-inventory.py`, image pin/upstream checks, legacy variable lint |
| Molecule docker smoke | `molecule test -s docker-ci` — docker role on docker driver (no Vagrant) |
| Security | CodeQL, Trivy filesystem + pinned container images |
| Galaxy build | Collection build for advertised ansible-core range |

**Python unit tests:** `python -m unittest discover -s tests/unit -p 'test_*.py'`

**Inventory checks (structure-only in CI):**

```bash
python scripts/validate-inventory.py \
  tests/remote/inventories/example-lab-ha.yml \
  inventory/vagrant.yml \
  --structure-only
python scripts/check-legacy-inventory-vars.py
```

---

## Molecule (local integration)

Six scenarios under `molecule/`:

| Scenario | Path | Focus |
|----------|------|-------|
| `ubuntu` | `molecule/ubuntu/` | Ubuntu 24.04 HA — bootstrap, verify, rolling `update-pihole`, re-verify |
| `ubuntu-26.04` | `molecule/ubuntu-26.04/` | Ubuntu 26.04 — same HA + update sequence |
| `default` | `molecule/default/` | Rocky-style lab box |
| `docker` | `molecule/docker/` | Docker role focus (Vagrant — local) |
| `docker-ci` | `molecule/docker-ci/` | Docker role on docker driver (hosted CI smoke) |
| `pihole-no-unbound` | `molecule/pihole-no-unbound/` | Pi-hole-only DNS bootstrap + update |
| `nebula-sync-migration` | `molecule/nebula-sync-migration/` | Legacy plaintext → secret-file credential migration |

**Hosted CI smoke (no Vagrant):**

```bash
molecule test -s docker-ci
```

Runs in GitHub Actions on code-changing PRs. Exercises docker role `debian_repo`
tasks inside a docker-driver Molecule container — not a full in-container
`docker.service` start (that path stays on local Vagrant scenarios).
Full HA still requires local `molecule test -s ubuntu` (see PR template checkbox).

**Typical HA run:**

```bash
molecule test -s ubuntu
```

Sequence: dependency → syntax → create (Vagrant) → prepare → converge → verify →
**side_effect** (`update-pihole`) → verify → destroy.

Shared verify logic: `molecule/common/verify_ha.yml` and tasks under
`molecule/common/verify/`.

**Helpers:**

```bash
./scripts/molecule-vagrant test -s ubuntu
./scripts/molecule-test-all --ubuntu-only
```

See [README — Molecule integration tests](../README.md#molecule-integration-tests) for provider notes (VirtualBox vs libvirt, ARM64, box selection).

---

## HA testing scope

Full **failover and failback** (keepalived, VIP movement, per-node DNS after
primary outage) is validated only in the **local Molecule HA lab** — same-subnet
Vagrant boxes where two nodes can share a virtual IP:

```bash
molecule test -s ubuntu
```

Shared verify logic (`molecule/common/verify_ha.yml`) exercises VIP DNS, keepalived
state, and post-update HA checks. The `ubuntu-26.04` scenario follows the same
pattern on Ubuntu 26.04.

| Layer | HA coverage | Why |
|-------|-------------|-----|
| **GitHub CI** | **No** — `molecule test -s docker-ci` smoke only | Hosted runners have no Vagrant; docker-ci exercises the docker role, not keepalived/VIP failover |
| **AWS remote** | **No** — single-node smoke only | Dual-node AWS HA is **declined / out of scope** (see below) |
| **Local Molecule** | **Yes** — full HA path | Only environment with same-subnet dual nodes and existing HA verify tasks |

**Decision — dual-node AWS HA declined:** Running full HA failover in AWS remote tests is
**not worth the operational burden** for the value it adds. Local Molecule already
covers keepalived, VIP movement, and post-update HA verification; AWS remote tests
remain **single-node smoke** (bootstrap → verify → optional update → teardown).

This is an explicit **out-of-scope** choice, not a backlog item. Operational cost
exceeds benefit:

- **2× EC2** per run (primary + secondary) and longer wall-clock time
- **VRRP security group** rules and cross-instance networking on a public subnet
- **Private/public IP inventory** wiring for keepalived and Ansible groups
- **Porting failover verify** — remote playbooks would need the Molecule HA verify
  path (`molecule/common/verify_ha.yml`) adapted for ephemeral multi-host orchestration
- **Higher AWS spend** on every scheduled, RC, and label-triggered run

The `ha` scenario in `tests/remote/run.sh` remains for ad-hoc experimentation only;
no scheduled, RC, or PR-label workflow will invoke dual-node AWS HA.

**Gate for HA-touching PRs:** the PR template checkbox ("Ran `molecule test -s ubuntu`
locally") remains the required attestation when changes touch keepalived, VIP
failover, rolling updates, or HA verification. CI and AWS remote tests do not
substitute for that run.

See also: [Failover testing](failover-testing.md) (manual production checks).

---

## AWS remote tests

Two workflows share scripts under `tests/remote/`:

| Workflow | File | When |
|----------|------|------|
| RC gate | `.github/workflows/rc-aws-remote-tests.yml` | RC tags (`v*-rc*`) |
| Remote tests | `.github/workflows/aws-remote-tests.yml` | 1st & 15th monthly on `master`, PR label `run-aws-tests`, or manual dispatch |

Flow: OIDC → launch EC2 → `bootstrap-pihole.yaml` → verify → optional `update-pihole.yaml` → verify → always destroy.

**Detail:** [AWS remote tests — workflow guide](aws-remote-tests-workflow.md)  
**Auth / repo variables:** [AWS remote tests auth](aws-remote-tests-auth.md)

**Manual dispatch highlights:**

- `scenario`: `pihole-unbound` or `pihole-upstream-only`
- `platform_coverage`: `one-arch` or `all-archs`
- `skip_update`: skip rolling update playbook

---

## Manual production checks

Use during planned changes (see [upgrade runbook](upgrade-runbook.md)):

1. **Per-node DNS** — `dig +short @<node-ip> <pihole_verify_qname>`
2. **VIP DNS** — `dig +short @<vip> <pihole_verify_qname>`
3. **Failover / failback** — simulate primary outage; confirm VIP and DNS
4. **Nebula Sync** — replication after HA nodes are healthy

**Detail:** [Failover testing](failover-testing.md)

**Pre-flight inventory (before bootstrap or update):**

```bash
python scripts/validate-inventory.py -i your-inventory.yml
python scripts/check-legacy-inventory-vars.py path/to/your-inventory.yml
```

---

## Related docs

- [Production deployment](production-deployment.md) — inventory mapping, health gates
- [Improvement backlog](improvement-backlog.md) — planned test gaps
- [Knowledge vault](knowledge-vault.md) — architecture graph for agents
