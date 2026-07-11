## Summary

- Describe the user-visible behavior change in 1-3 bullets.
- If this is internal-only work, say so explicitly.

## Release notes

- Proposed release note sentence:
  - `<one sentence describing operator/user impact>`
- Changelog type (pick one):
  - [ ] `feat`
  - [ ] `fix`
  - [ ] `perf`
  - [ ] `refactor`
  - [ ] non-user-facing (`docs` / `ci` / `chore` / `test` / `build`)

## Validation

- [ ] `ansible-lint` / `yamllint` pass locally or in CI
- [ ] syntax checks pass for changed playbooks/roles
- [ ] Molecule or remote functional checks run when behavior changes
- [ ] README/operational docs updated when needed

## HA / failover changes (when applicable)

If this PR touches keepalived, VIP failover, rolling updates (`update-pihole.yaml`), or HA verification:

- [ ] Ran `molecule test -s ubuntu` locally (or noted why not — e.g. no Vagrant box)
- [ ] Updated [failover testing](docs/failover-testing.md) / runbooks if operator steps changed

## Scope and risk

- Risk level:
  - [ ] low
  - [ ] medium
  - [ ] high
- Rollback plan:
  - `<how to revert/mitigate if needed>`
