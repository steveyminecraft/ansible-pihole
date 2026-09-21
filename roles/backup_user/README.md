# backup_user

Create a dump-only SSH user on Pi-hole hosts for off-box config collection.

This role does **not** drain keepalived, stop containers, change Traefik, or
rewrite Pi-hole compose. Use the dedicated playbook on live HA nodes.

## When it runs

| Playbook | Position | Tags |
|----------|----------|------|
| `playbooks/backup-user.yaml` | Sole role | `backup_user`, `pihole_backup_user` |

`playbooks/bootstrap-pihole.yaml` and `playbooks/update-pihole.yaml` do **not**
include this role.

## What it changes

- Installs `/usr/local/sbin/pihole-backup-dump` (config + gravity DB tarball to stdout)
- Creates system user `backup` with a locked password. The login shell is
  `/bin/bash` because Rocky/RHEL sshd does not honour key `command=` when the
  shell is `nologin`. Access is still dump-only via exclusive forced command,
  `no-pty`, and no forwarding.
- Sudoers: NOPASSWD for that dump wrapper only
- Exclusive `authorized_keys` with a forced command and no forwarding/pty

Set `backup_user_authorized_key` (ed25519 public key string) or
`backup_user_authorized_key_file` on the controller. Do not commit live keys.

## Example

```bash
ansible-playbook -i inventory/rnet.yml playbooks/backup-user.yaml \
  -e backup_user_authorized_key_file=/path/to/id_ed25519_network_backup.pub
```

Part of the `steveyminecraft.pihole` collection.
