# start_keepalived

Start the keepalived (or legacy `keepalive`) service after maintenance once the
node passes local DNS health checks.

This role is the **resume** half of the HA maintenance pattern. It does not
configure keepalived — use the `keepalived` role for that.

## When it runs

| Playbook | Position | Tags |
|----------|----------|------|
| `playbooks/bootstrap-pihole.yaml` | Included in post-tasks after local DNS/Unbound validation | (inherits `pihole`, `dns`, `ha` from the block) |
| `playbooks/update-pihole.yaml` | Included in post-tasks after local DNS/Unbound validation | (inherits `pihole`, `dns`, `ha` from the block) |

The role is **not** listed in the main `roles:` section. Playbooks call it with
`include_role` only after:

- `wait_for` on `127.0.0.1:53` succeeds, and
- `dig +short @127.0.0.1 <health-qname>` returns an IPv4 answer, and
- optional Unbound `dig` from inside the Pi-hole container passes when Unbound is
  deployed.

If validation fails, the rescue block stops the play and this role does not run,
leaving the node drained until you repair it and re-run the playbook.

## Drain/resume pattern

Pair with `stop_keepalived` at the start of the same playbook run:

1. `stop_keepalived` — release the VIP from this node
2. Package/Pi-hole changes
3. Local DNS gates
4. **`start_keepalived`** — return the node to VIP candidacy

See [Upgrade runbook](../../docs/upgrade-runbook.md#health-gates) for timing and
retry details.

## Example

Re-run rolling update after fixing a drained node:

```bash
ansible-playbook -i inventory.yml playbooks/update-pihole.yaml --limit node2
```

Part of the `steveyminecraft.pihole` collection.
