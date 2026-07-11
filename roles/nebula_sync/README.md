# nebula_sync

Deploy the [Nebula Sync](https://github.com/lovelaze/nebula-sync) container on
the HA **controller** host to replicate Pi-hole settings to replica nodes.

This role is separate from the keepalived drain/resume path. It runs after both
nodes are bootstrapped and answers DNS.

## When it runs

| Playbook | Hosts | Tags |
|----------|-------|------|
| `playbooks/sync.yaml` | `nebula_sync_controller` (exactly one host in inventory) | `nebulasync`, `nebula`, `sync` |

`bootstrap-pihole.yaml` and `update-pihole.yaml` do **not** invoke this role.
Run `sync.yaml` when you need to (re)deploy or migrate the Nebula Sync controller.

## Requirements

Define in inventory/vault (non-placeholder values):

- `nebula_sync_primary_url` and `nebula_sync_primary_password`
- `nebula_sync_replicas` — list of `{ url, password }` entries for replica
  Pi-hole API endpoints

Optional tuning lives in `defaults/main.yml` (`nebula_sync_cron`, sync toggles,
image tag, secret-file layout).

By default the role:

- Renders Compose under `nebula_sync_dir` (default `/opt/nebula-sync`)
- Stores credentials in read-only secret files mounted into the container
- Recreates the container when config changes or legacy plaintext env is detected

Replica hosts do not run this container — Molecule and remote verify playbooks
assert the sync container is absent on replicas.

## Example

Deploy or refresh Nebula Sync on the controller:

```bash
ansible-playbook -i inventory.yml playbooks/sync.yaml
```

Tag-scoped run:

```bash
ansible-playbook -i inventory.yml playbooks/sync.yaml --tags nebulasync
```

After bootstrap or restore, confirm replication with the checks in
[Backup and restore](../../docs/backup-and-restore.md#post-restore-checks).

Part of the `steveyminecraft.pihole` collection.
