# Remote functional tests

This harness runs the production playbooks and reusable verification playbooks
against externally provisioned AWS instances, lab VMs, or Raspberry Pi
hardware.

The repository does not assume ownership of remote hosts. Set optional
lifecycle hooks when a test environment can be created, checked for
idempotence, or reset automatically:

```bash
export REMOTE_CREATE_COMMAND='./path/to/create-test-hosts'
export REMOTE_IDEMPOTENCE_COMMAND='ansible-playbook -i inventory.yml playbooks/bootstrap-pihole.yaml --check'
export REMOTE_RESET_COMMAND='./path/to/reset-test-hosts'
```

Run a scenario from the repository root:

```bash
tests/remote/run.sh \
  --inventory tests/remote/inventories/example-no-unbound.yml \
  --scenario no-unbound
```

| Scenario | Verification |
|----------|--------------|
| `single` | Pi-hole and Unbound containers plus local DNS |
| `no-unbound` | Pi-hole DNS, explicit upstreams, and no Unbound resources |
| `ha` | Pi-hole, Unbound, keepalived, VIP DNS, and optional Nebula Sync placement |

Copy an example inventory outside the repository and replace all placeholder
addresses and credentials. Never commit production credentials.

The harness verifies immediately after bootstrap and again after exercising the
update playbook. Use `--skip-converge` to verify an existing deployment or
`--skip-update` when the environment must not be updated.

Idempotence is an explicit hook because the current HA bootstrap workflow
intentionally drains and resumes services. Environments that require a strict
zero-change assertion should provide a topology-specific command.

## GitHub Actions AWS ephemeral workflow

The repository includes an AWS integration workflow at
`.github/workflows/aws-remote-tests.yml` that runs this harness against
ephemeral EC2 hosts and always executes teardown.

### Trigger modes

- `workflow_dispatch` for on-demand runs
- weekly `schedule` smoke test (`single`, Ubuntu AMD64)

### Runtime matrix

- Profiles:
  - `single` (Ubuntu 26.04 on one architecture selected by inputs)
  - `full` (Ubuntu 26.04 on AMD64 and ARM64)
- Scenarios:
  - `single`
  - `no-unbound`

The scheduled run intentionally stays on a low-cost smoke profile. Expand only
after repeated stable executions.

### Required repository configuration

Repository variables:

- `AWS_TEST_ROLE_ARN`
- `AWS_TEST_REGION`
- `AWS_TEST_SUBNET_ID`
- `AWS_TEST_KEY_NAME`
- `AWS_TEST_INSTANCE_TYPE_AMD64`
- `AWS_TEST_INSTANCE_TYPE_ARM64`
- optional `AWS_TEST_SSH_CIDR` (defaults to `0.0.0.0/0` if unset)

Repository secrets:

- `AWS_TEST_SSH_PRIVATE_KEY`
- `AWS_TEST_PIHOLE_API_PASSWORD`
- optional `AWS_TEST_ANSIBLE_VAULT_PASSWORD`

The workflow uses OIDC role assumption (`id-token: write`) and does not require
static AWS API keys.

### Build-ci infrastructure (Terraform)

Remote test networking and GitHub OIDC access live in the **`AWS-Cloud`**
repository under `build-account-isolation/build/`. After `terraform apply`,
map `terraform output -json ansible_remote_test_configuration` to repository
variables:

- `AWS_TEST_ROLE_ARN`
- `AWS_TEST_REGION`
- `AWS_TEST_SUBNET_ID`
- `AWS_TEST_KEY_NAME`
- `AWS_TEST_INSTANCE_TYPE_AMD64`

RC tag runs (`.github/workflows/rc-aws-remote-tests.yml`) use Ubuntu 26.04 only.
The manual workflow (`.github/workflows/aws-remote-tests.yml`) supports broader
matrix profiles when needed.
