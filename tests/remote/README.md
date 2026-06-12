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
