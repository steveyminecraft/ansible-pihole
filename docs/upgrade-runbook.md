# Upgrade Runbook

## Goal

Upgrade packages and roles while keeping DNS service available through rolling updates.

## Steps

1. Ensure inventory is current and credentials are valid.
2. Run update playbook:

   ```bash
   ansible-playbook -i /path/to/inventory.yml playbooks/update-pihole.yaml
   ```

3. Observe per-node sequence:
   - stop keepalived on current node
   - apply updates and role changes
   - restart keepalived
   - run local DNS health checks
4. Verify VIP answers DNS after run:

   ```bash
   dig +short @<vip-ip> google.com
   ```

## Rollback notes

- Re-run previous collection version/playbook commit against the same inventory.
- If one node fails health checks, playbook halts before touching the next node.
- Restore service on failed node, then re-run update playbook.
