# sshd

Apply baseline OpenSSH server hardening on Pi-hole hosts.

## When it runs

| Playbook | Position | Tags |
|----------|----------|------|
| `playbooks/bootstrap-pihole.yaml` | After `bootstrap` and `updates`, before `keepalived` | `sshd`, `system` |

This role is part of **initial bootstrap**, not the rolling update path.
`playbooks/update-pihole.yaml` does not include it.

## What it changes

- Creates `/run/sshd` on Debian-family hosts when needed
- Sets in `/etc/ssh/sshd_config`:
  - `PermitRootLogin no`
  - `PasswordAuthentication no`
  - `MaxSessions 5`
  - `MaxAuthTries 3`
- Validates the config with `sshd -T` before applying each line
- Restarts SSH via `Restart_SSH` (Debian) or `Restart_SSHD` (RedHat)

Ensure key-based access works before running bootstrap on a new host. The role
does not manage authorized keys — the `bootstrap` role handles SSH keys.

## Example

Bootstrap only SSH-related tasks on lab hosts:

```bash
ansible-playbook -i inventory.yml playbooks/bootstrap-pihole.yaml --tags sshd
```

Part of the `steveyminecraft.pihole` collection.
