# stop_keepalived

Stop the keepalived (or legacy `keepalive`) service before maintenance so the VIP
can move to another node.

This role is the **drain** half of the HA maintenance pattern. It does not
configure keepalived — use the `keepalived` role for that.

## When it runs

| Playbook | Position | Tags |
|----------|----------|------|
| `playbooks/bootstrap-pihole.yaml` | First role on each host (`serial: 1`) | `stopkeepalived`, `drain`, `ha` |
| `playbooks/update-pihole.yaml` | First role on each host (`serial: 1`) | `stopkeepalived`, `drain`, `ha` |

The role gathers service facts, detects `keepalived.service` or the Ubuntu typo
`keepalive.service`, and stops the unit when present. If keepalived is not
installed, the role is a no-op.

## Drain/resume pattern

1. **Drain** — this role stops keepalived on the current node.
2. **Change** — bootstrap, updates, or Pi-hole role tasks run while the node is
   out of VIP service.
3. **Validate** — playbook post-tasks wait for local DNS and optional Unbound.
4. **Resume** — `start_keepalived` runs only after validation passes.

If DNS validation fails, keepalived is **not** restarted on that node. See
[Upgrade runbook](../../docs/upgrade-runbook.md#health-gates) for failure and
retry guidance.

## Example (maintenance window)

Drain and update one node only:

```bash
ansible-playbook -i inventory.yml playbooks/update-pihole.yaml --limit node1
```

Skip drain/resume helpers while testing non-HA changes:

```bash
ansible-playbook -i inventory.yml playbooks/update-pihole.yaml --skip-tags drain,ha
```

Part of the `steveyminecraft.pihole` collection.
