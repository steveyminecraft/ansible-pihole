# AWS remote tests — workflow guide

This document explains how the GitHub Actions AWS remote test workflows operate, from trigger to teardown.
For a single index of all test layers (CI, Molecule, AWS, manual), see [Testing guide](testing.md).

There are **two related workflows**. They share the same scripts and AWS setup; they differ mainly in **when they run** and **how much they test**.

| | **CI — Pi-hole: AWS EC2 (RC)** | **CI — Pi-hole: AWS EC2 (remote tests)** |
|---|---|---|
| File | `.github/workflows/rc-aws-remote-tests.yml` | `.github/workflows/aws-remote-tests.yml` |
| Triggers | RC tags (`v1.0.0-rc.1`) or manual | Twice monthly on `master`, PR label `run-aws-tests`, or manual |
| OS | Ubuntu 26.04 amd64 only | Scheduled/label: Ubuntu 26.04 amd64; manual: one or all archs |
| Purpose | Pre-release gate on every RC tag | Scheduled smoke + on-demand operator / PR testing |

Both follow the same core pattern: **assume AWS role → launch EC2 → Ansible → always destroy**.

---

## End-to-end flow

```mermaid
sequenceDiagram
    participant GH as GitHub Actions
    participant OIDC as GitHub OIDC
    participant AWS as build-ci account
    participant EC2 as Ephemeral Ubuntu host
    participant Ansible as Ansible playbooks

    GH->>OIDC: Request short-lived token
    OIDC->>AWS: Assume build-ci-github-build role
    GH->>AWS: create-ephemeral-env.sh
    AWS->>EC2: Launch instance + SG + inventory
    GH->>EC2: bootstrap-pihole.yaml (SSH)
    GH->>EC2: verify playbooks
    GH->>EC2: update-pihole.yaml (optional)
    GH->>EC2: verify again
    GH->>AWS: destroy-ephemeral-env.sh (always)
    GH->>GH: verify-cleanup.sh
```

---

## `aws-remote-tests.yml` — section by section

### 1. Triggers (`on`)

```yaml
schedule:
  - cron: "0 6 1,15 * *"   # 1st and 15th of each month at 06:00 UTC on master
pull_request:
  types: [labeled, synchronize, reopened]   # when label run-aws-tests is present
workflow_dispatch:   # Full manual matrix from GitHub UI
```

**Automatic profile** (scheduled + labeled PRs): Ubuntu 26.04 **amd64**,
`pihole-unbound`, **includes** `update-pihole.yaml` (does not pass `--skip-update`).

Scheduled runs fire on the **1st and 15th** of each month at 06:00 UTC.

**PR label:** add `run-aws-tests` to a pull request to run the same profile against
the PR head commit. Re-runs on new pushes while the label remains.

**Manual inputs** (`workflow_dispatch` only):

| Input | Purpose |
|---|---|
| `scenario` | `pihole-unbound` or `pihole-upstream-only` |
| `platform_coverage` | `one-arch` or `all-archs` |
| `arch` | For `one-arch` only: `amd64` or `arm64` |
| `skip_update` | Skip the update playbook |
| `aws_region` | Optional override; defaults to `AWS_TEST_REGION` repository secret |

### 2. Permissions and concurrency

```yaml
permissions:
  contents: read
  id-token: write      # Required for OIDC → AWS (no long-lived keys in GitHub)

concurrency:
  cancel-in-progress: true   # A new run cancels an in-flight one
```

### 3. Job 1: `prepare-matrix`

This job turns your manual inputs into a JSON matrix for job 2.

| Input profile | Matrix produced |
|---|---|
| `one-arch` + amd64 | 1 job: Ubuntu 26.04 amd64 |
| `one-arch` + arm64 | 1 job: Ubuntu 26.04 arm64 |
| `all-archs` | 2 jobs: amd64 + arm64 |

It also passes through **scenario** and **skip_update**. Region is resolved in job 2 directly from `github.event.inputs.aws_region` or `secrets.AWS_TEST_REGION` (Actions redacts secret-bearing job outputs to empty, so region must not cross the job boundary via outputs).

### 4. Job 2: `aws-remote-tests` (main work)

Runs once per matrix row (in parallel when `full`).

**Environment variables** wire GitHub configuration to the scripts:

| Name | Source | Purpose |
|---|---|---|
| `AWS_TEST_ROLE_ARN` | repo secret | OIDC role in build-ci |
| `AWS_TEST_REGION` | repo secret | e.g. `eu-west-1` |
| `AWS_TEST_SUBNET_ID` | repo secret | Public ephemeral subnet |
| `AWS_TEST_KEY_NAME` | repo variable | EC2 key pair name |
| `AWS_TEST_INSTANCE_TYPE_*` | repo variable | e.g. `t3.small` |
| `AWS_TEST_SSH_PRIVATE_KEY` | repo secret | SSH to the new host |
| `AWS_TEST_PIHOLE_API_PASSWORD` | repo secret | Pi-hole API password in inventory |

**Step sequence:**

1. **Validate** — fail fast if vars/secrets are missing
2. **Checkout** — clone ansible-pihole
3. **Configure AWS credentials (OIDC)** — short-lived session as `build-ci-github-build`
4. **Set up Python + Ansible + collections**
5. **Prepare SSH** — write private key to a temp file (`chmod 600`)
6. **Run remote test harness** — calls `tests/remote/run.sh`
7. **Ensure cleanup** (`if: always()`) — destroy even if Ansible failed
8. **Verify cleanup** — confirm instance terminated and security group deleted
9. **Publish summary** — table in the Actions run summary

Steps 7–8 are the “never leave orphan EC2” safety net. Step 6 also registers cleanup inside `run.sh` via an exit trap.

---

## What `tests/remote/run.sh` does

The workflow sets:

```bash
REMOTE_CREATE_COMMAND=tests/remote/aws/create-ephemeral-env.sh
REMOTE_RESET_COMMAND=tests/remote/aws/destroy-ephemeral-env.sh
```

Then `run.sh`:

1. **CREATE hook** → `create-ephemeral-env.sh`
2. Check inventory exists (create script writes it)
3. **Converge** → `playbooks/bootstrap-pihole.yaml`
4. **Verify** → scenario-specific playbooks under `tests/remote/verify/`
5. **Update** → `playbooks/update-pihole.yaml` (unless `--skip-update`)
6. **Verify again**
7. **RESET hook** (on exit via `trap`) → `destroy-ephemeral-env.sh`

| Scenario | Verification playbooks |
|---|---|
| `single` | `pihole.yml`, `unbound.yml` |
| `no-unbound` | `pihole.yml`, `no-unbound.yml` |
| `ha` | Pi-hole, Unbound, keepalived, VIP DNS, Nebula Sync (not used by default AWS workflows) |

### HA / scope — single-node only (dual-node declined)

Remote AWS tests launch **one ephemeral EC2 instance** per matrix row: bootstrap,
verify, optional update, teardown. That is the intended scope for scheduled, RC,
and PR-label runs.

**Dual-node AWS HA is explicitly declined / out of scope.** The operational burden
does not justify the incremental confidence over local Molecule:

| Burden | Why it matters |
|--------|----------------|
| 2× EC2 per run | Doubles cost and runtime on every scheduled, RC, and label-triggered job |
| VRRP security group | Keepalived needs multicast/VRRP between instances on a public subnet |
| Private/public IP inventory | Dual-node keepalived requires per-node and VIP addressing in ephemeral inventory |
| Porting failover verify | Molecule HA checks (`molecule/common/verify_ha.yml`) are not wired into remote verify playbooks |
| Longer runs | Create, converge, verify, and destroy scale with two hosts |

Local Molecule already exercises full failover and failback on same-subnet Vagrant
boxes. AWS remote stays **single-node smoke**; full HA coverage is **local Molecule
only** (`molecule test -s ubuntu`).

The `ha` scenario in `tests/remote/run.sh` exists for ad-hoc manual experimentation
only — **no default workflow** (scheduled, RC, or PR label) invokes it, and there
is no plan to add dual-node AWS HA to CI.

See [Testing guide — HA testing scope](testing.md#ha-testing-scope).

---

## What `create-ephemeral-env.sh` does

Each run gets a **fresh** host:

1. Resolve Ubuntu 26.04 AMI from SSM (`/aws/service/canonical/ubuntu/server/26.04/...`)
2. Create a **new security group** tagged `Project=ansible-pihole`, `Ephemeral=true`
3. Open SSH (22) and DNS (53) from `AWS_SSH_CIDR`
4. **RunInstances** with your key pair in the build-ci subnet
5. Wait for running + status OK
6. Write state files:
   - `AWS_STATE_FILE` — instance ID + SG ID (for destroy)
   - `AWS_INVENTORY_FILE` — Ansible inventory from template
   - `AWS_METADATA_FILE` — run metadata for the summary

The GitHub role can only create/terminate resources with `Project=ansible-pihole` (configured in the `AWS-Cloud` Terraform build stack).

---

## What cleanup does

**`destroy-ephemeral-env.sh`**

- Terminate instance(s) from the state file
- Wait until terminated
- Delete the per-run security group
- Write cleanup status JSON

**`verify-cleanup.sh`**

- Fails the job if anything is still running or the security group remains

You get cleanup from both `run.sh`'s exit trap **and** the workflow's `if: always()` steps.

---

## RC workflow differences

`rc-aws-remote-tests.yml` skips the matrix job:

- Fixed: Ubuntu 26.04 amd64
- Checks out the **tag ref** (`ref: ${{ github.ref_name }}`)
- Same create → run → destroy pipeline
- Instance name prefix `ansible-pihole-rc` (vs `ansible-pihole-remote` for manual runs)

That is what runs when you push a tag like `v1.0.0-rc.1`.

---

## Where AWS infrastructure lives

Not in ansible-pihole. The **build-ci** account (`290488660479`) is provisioned by `AWS-Cloud/build-account-isolation/build/`:

- OIDC trust for `steveyminecraft/ansible-pihole`
- Ephemeral test subnet and internet gateway
- EC2 key pair `build-ci-github-test`
- IAM permissions for tagged ephemeral hosts

GitHub repository **variables and secrets** are the bridge between that Terraform and these workflows.

See also: [AWS remote tests — authentication](aws-remote-tests-auth.md).

---

## Mental model

Three layers:

1. **GitHub** — orchestration, secrets, when to run
2. **AWS build-ci** — disposable compute per run (create/destroy scripts)
3. **Ansible** — the actual Pi-hole test (same playbooks used on real hardware)

The remote-tests workflow covers **twice-monthly smoke on `master`**, **PR label
`run-aws-tests`**, and **on-demand operator testing**. The RC workflow is the
**release gate** (tag-triggered, single fixed config). New upstream Pi-hole Docker
tags are tracked by **`pihole-image-watch.yml`** (daily issue alert, no EC2 cost).
