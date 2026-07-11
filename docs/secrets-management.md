# Secrets Management

See also [production-deployment.md](production-deployment.md) for inventory layout
and [backup-and-restore.md](backup-and-restore.md) for pre-change backups.

## Required secrets

| Secret | Inventory keys | Used by |
|--------|----------------|---------|
| Pi-hole Web/API password | `pihole_environment_variables.FTLCONF_webserver_api_password` | Pi-hole container, Nebula Sync API auth |
| Nebula Sync primary credential | `nebula_sync_primary_password` | Nebula Sync → primary Pi-hole |
| Nebula Sync replica credentials | `nebula_sync_replicas[*].password` | Nebula Sync → each replica |

Nebula Sync passwords usually match the Pi-hole API password on each node when
all instances share one operator credential. They can differ if you rotate per
host — keep URLs and passwords consistent with the node Nebula Sync calls.

## Vault naming and layout

Recommended gitignored layout (see [production-deployment.md](production-deployment.md)):

```text
inventory/
  rnet.yml                      # hosts, groups, non-secret vars
  group_vars/all/vars.yml       # optional shared non-secret defaults
  group_vars/all/vault.yml      # ansible-vault encrypted secrets
```

**Naming convention:** prefix vault-only variables with `vault_` in
`group_vars/all/vars.yml` and define the secret values in `vault.yml`:

```yaml
# group_vars/all/vars.yml (plaintext)
pihole_environment_variables:
  FTLCONF_webserver_api_password: "{{ vault_pihole_api_password }}"
nebula_sync_primary_password: "{{ vault_pihole_api_password }}"
nebula_sync_replicas:
  - url: http://192.0.2.11
    # credential: same vault var as primary (see nebula_sync README)
```

```yaml
# group_vars/all/vault.yml (encrypted)
vault_pihole_api_password: "your-long-random-secret-here"
```

Alternative filenames operators use:

| Pattern | Notes |
|---------|--------|
| `group_vars/all/vault.yml` | Common; encrypt entire file |
| `host_vars/<host>/vault.yml` | Host-specific secrets (rare for Pi-hole HA) |
| Inline in `rnet.yml` | Homelab-only; never commit |

Create or edit vault:

```bash
ansible-vault create inventory/group_vars/all/vault.yml
ansible-vault edit inventory/group_vars/all/vault.yml
ansible-playbook -i inventory/rnet.yml playbooks/bootstrap-pihole.yaml --ask-vault-pass
```

Use `ANSIBLE_VAULT_PASSWORD_FILE` in automation instead of `--ask-vault-pass`.

## Validation behavior

Role tasks fail fast before containers change if secrets are missing or weak:

- Pi-hole deploy asserts a non-placeholder password with **minimum 16 characters**.
- Nebula Sync deploy asserts non-placeholder primary and replica credentials.
- Known placeholders are rejected: `CHANGE_ME`, `Intranet`, `Testing 101`, empty string.

Lab inventories (`inventory/vagrant.yml`) use fixture passwords intentionally;
do not copy those values to production.

## Storage recommendations

- Store production credentials in Ansible Vault or an equivalent secret backend.
- Keep plaintext credentials out of versioned inventory files.
- Do not log secrets: role assertions use `no_log: true` where credentials are checked.

## File permissions on targets

After deploy, the collection enforces restrictive modes on disk:

- Pi-hole compose file — root-owned, mode `0600`.
- Nebula Sync secret files — mode `0400` when `nebula_sync_use_secret_files: true`
  (default).

## Nebula Sync secret delivery

Default is `nebula_sync_use_secret_files: true`. Credentials are written under
`nebula_sync_secret_dir` on the controller host and mounted into the container;
the compose environment references `PRIMARY_FILE` and `REPLICAS_FILE` instead of
inline env vars.

Set `nebula_sync_use_secret_files: false` only when debugging; prefer secret
files for production.

## Rotating the Pi-hole API password

Use a maintenance window and the [production change checklist](upgrade-runbook.md#production-change-checklist).

1. **Backup** — Pi-hole volumes and inventory/vault per [backup-and-restore.md](backup-and-restore.md).
2. **Update vault** — set a new `vault_pihole_api_password` (≥16 chars).
3. **Rolling update** — run `playbooks/update-pihole.yaml` so each node receives
   the new `FTLCONF_webserver_api_password` and passes DNS health gates.
4. **Verify** — log in to each Pi-hole UI/API and query DNS on node IPs and VIP.
5. **Nebula Sync** — if primary/replica passwords reference the same vault var,
   re-run `playbooks/sync.yaml` on the controller after both nodes are updated so
   Nebula Sync authenticates with the new API password.
6. **Record** — note rotation time and validation in your change log.

Rotating **only** on one node while the other keeps the old password causes
Nebula Sync auth failures and inconsistent replica sync until both match.

## Rotating Nebula Sync credentials independently

If replica passwords must differ from the primary (unusual):

1. Update the specific `nebula_sync_replicas[*].password` (or vault vars) in inventory.
2. Ensure each `url` points at the correct node API endpoint.
3. Run `playbooks/sync.yaml` on the `nebula_sync_controller` host.
4. Confirm sync logs and a known Pi-hole list/setting on the replica.

Primary password changes still require updating `nebula_sync_primary_password` and
re-running sync.

## Detecting drift between nodes

**Credential drift** — primary and replicas disagree on API passwords while Nebula
Sync still uses a single vault reference:

| Symptom | Likely cause |
|---------|----------------|
| Nebula Sync 401/403 in controller logs | Password on one Pi-hole node not updated |
| Replica missing lists/gravity | Sync failing silently or cron not running |
| UI login works on one node only | Partial rotation or manual change on one host |

**Checks before/after changes:**

```bash
# Same vault var referenced everywhere (grep plaintext inventory only)
grep -E 'FTLCONF_webserver_api_password|nebula_sync_.*password' inventory/rnet.yml

# Nebula container running on controller only
ansible -i inventory/rnet.yml nebula_sync_controller -m command \
  -a "docker ps --filter name=nebula --format '{{.Names}} {{.Status}}'"

# Optional: re-run sync and verify a known setting (see failover-testing.md)
ansible-playbook -i inventory/rnet.yml playbooks/sync.yaml
```

**Configuration drift** — inventory says one thing, a node was edited manually:

- Re-run `playbooks/update-pihole.yaml` to reconcile Pi-hole/Unbound containers.
- Re-run `playbooks/sync.yaml` after inventory secret changes.
- Compare Nebula Sync cron and primary URL in inventory with the controller's
  rendered compose under `nebula_sync_dir`.

Use the pre-flight inventory validator (`scripts/validate-inventory.py`) before
bootstrap or update to catch missing HA groups and placeholder secrets early.

## Related docs

- [production-deployment.md](production-deployment.md) — inventory → example mapping
- [upgrade-runbook.md](upgrade-runbook.md) — rolling updates and health gates
- [backup-and-restore.md](backup-and-restore.md) — pre-change backups
