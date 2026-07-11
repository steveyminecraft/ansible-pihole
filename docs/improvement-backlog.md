# Improvement Backlog

Action items identified from a project review (2026-07-09). Use this as a
prioritized checklist when planning issues or PRs.

## Priority 1 — Testing (highest impact)

The repo has a three-layer test model (GitHub CI → Molecule/Vagrant → AWS
remote), but coverage is uneven on the riskiest path: rolling HA updates.

- [x] **Add `update-pihole` to the HA Molecule path** ([#153](https://github.com/steveyminecraft/ansible-pihole/issues/153))
  - Today only `molecule/pihole-no-unbound` runs it via `side_effect.yml`.
  - Main `ubuntu` scenario exercises failover (`molecule/common/verify_ha.yml`)
    but never rolls an update.
  - Suggested: add `side_effect.yml` to `molecule/ubuntu` importing
    `playbooks/update-pihole.yaml`, then extend HA verify post-update.

- [x] **Scheduled or label-triggered AWS remote tests** ([#155](https://github.com/steveyminecraft/ansible-pihole/issues/155))
  - Runs on the **1st and 15th** of each month on `master`, or via PR label `run-aws-tests`.
  - Profile: amd64-only, `pihole-unbound`, includes update (not `--skip-update`).
  - Manual `workflow_dispatch` matrix unchanged.

- [x] **Check-mode for `update-pihole.yaml` in CI** ([#157](https://github.com/steveyminecraft/ansible-pihole/issues/157))
  - CI already runs check-mode for `ci-bootstrap.yaml`.
  - `inventory/ci/group_vars/all.yml` supplies CI-safe vars; live DNS/container steps skip in `--check`.

- [x] **Expand unit/integration tests beyond scripts** ([#159](https://github.com/steveyminecraft/ansible-pihole/issues/159))
  - Added `scripts/update-pihole-health.py` plus unit tests for dig health-gate logic.
  - Playbook contract tests cover rolling `serial: 1`, check-mode guards, VIP retry, Molecule update path.
  - Compose template smoke tests cover DHCP port gating.

## Priority 2 — Operations documentation

Docs are clear at a high level but thin relative to playbook complexity.

- [x] **Document `update-pihole.yaml` health gates** ([#161](https://github.com/steveyminecraft/ansible-pihole/issues/161))
  - Cover: local DNS wait, Unbound check, VIP verify, keepalived resume.
  - Include: what fails, expected timing, retry guidance.

- [x] **Expand stub role READMEs** ([#163](https://github.com/steveyminecraft/ansible-pihole/issues/163))
  - Documented `start_keepalived`, `stop_keepalived`, `sshd`, `nebula_sync`.
  - Cover drain/resume pattern, when each role runs, relevant tags.

- [x] **Cross-link production change runbooks** ([#167](https://github.com/steveyminecraft/ansible-pihole/issues/167))
  - Chain: `upgrade-runbook.md` → `failover-testing.md` →
    `backup-and-restore.md` as a single checklist (backup → update → VIP →
    Nebula sync verify).

## Priority 3 — Inventory and secrets ergonomics

Real inventory (`inventory/rnet.yml`) is gitignored; examples exist but mapping
is implicit.

- [x] **Document real inventory → example mapping** ([#174](https://github.com/steveyminecraft/ansible-pihole/issues/174))
  - In `docs/production-deployment.md`: required vs optional vars, vault file
    layout, HA-specific fields (`pihole_vip_ipv4`, nebula primary/replicas).

- [x] **Expand `docs/secrets-management.md`** ([#176](https://github.com/steveyminecraft/ansible-pihole/issues/176))
  - Vault naming convention, Nebula Sync password rotation, drift between nodes.

- [ ] **Pre-flight inventory validator**
  - Playbook or script asserting HA completeness and rejecting placeholders
    before bootstrap/update (fail fast vs mid-deploy).

## Priority 4 — Image and dependency maintenance

Image bumps currently touch multiple files manually (defaults, CI playbooks,
Trivy legacy list).

- [ ] **Wire upstream image check into CI**
  - `tests/unit/test_check_pihole_image_upstream.py` exists; run in CI
    (informational or blocking on drift).

- [ ] **Single source of truth for image pin**
  - Generate CI inventory pins from `roles/pihole/defaults/main.yml` (or
    reverse) so bumps are one-line changes.

## Priority 5 — Developer experience (knowledge vault)

Local graphify setup is valuable; graph quality can be improved.

- [ ] **Install `graphify hook`** for post-commit auto-update
  - See `docs/knowledge-vault.md` and `./scripts/setup-knowledge-vault.sh`.

- [ ] **Reduce graph noise**
  - ~405 isolated nodes; duplicate concepts (e.g. `update-pihole.yaml` vs
    `update-pihole playbook`). Periodic full rebuild + dedupe pass.

- [ ] **Optional: graphify MCP server**
  - Lets Cursor/agents query the graph without shelling out.

## Priority 6 — Architecture hygiene (medium-term)

- [ ] **Legacy unprefixed variable deprecation**
  - README documents compatibility lookups; add deprecation timeline + lint
    warning for unprefixed names (prefer `pihole_*`).

- [ ] **Unified testing index**
  - New or expanded `docs/testing.md`: CI / Molecule / AWS / manual checks in
    one page (graph suggested splits: Remote HA Inventories, Failover
    Verification, Molecule scenarios).

## Priority 7 — CI polish (lower effort)

- [ ] **Molecule in CI alternatives**
  - Vanilla GitHub runners can't run Vagrant easily.
  - Options: self-hosted runner, or smoke job on `molecule/docker` (no Vagrant).

- [ ] **PR template checkbox for HA changes**
  - Add: "Ran `molecule test -s ubuntu` locally" for HA-touching PRs.

---

## Quick reference — current test coverage

| Layer | Runs today | Gap |
|-------|------------|-----|
| GitHub CI | Lint, syntax, check-mode bootstrap + update-pihole, compose validation | No functional HA or update path |
| Molecule | 6 scenarios locally; HA verify on `ubuntu` | Not in CI; `update-pihole` in `ubuntu`, `ubuntu-26.04`, and `pihole-no-unbound` |
| AWS remote | Bootstrap + optional `update-pihole` | Scheduled 1st/15th + PR label; manual dispatch for full matrix |

## Suggested first issues

1. `ubuntu` Molecule side_effect for `update-pihole` + post-update HA verify
2. ~~Scheduled AWS remote test on `master` (twice monthly, amd64)~~ ([#155](https://github.com/steveyminecraft/ansible-pihole/issues/155))
3. Runbook section for rolling updates / drain-resume
4. Inventory pre-flight validator
5. Upstream image check in CI

---

*Generated from project review. Update checkboxes as items ship; link PR/issue
numbers inline when work starts.*
