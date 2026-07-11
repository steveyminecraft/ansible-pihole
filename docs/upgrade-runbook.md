# Upgrade Runbook

## Goal

Upgrade packages and roles while keeping DNS service available through rolling updates.

## Production change checklist

Use this as the entry point for a planned production change. Complete the
linked runbooks in order:

- [ ] **Backup** — follow the
  [pre-change backup checklist](backup-and-restore.md#pre-change-backup-checklist)
  for both nodes, inventory, and vaulted secrets.
- [ ] **Pre-check DNS** — query both nodes and the VIP as shown below.
- [ ] **Rolling update** — run `playbooks/update-pihole.yaml` and confirm each
  node passes its local DNS and optional Unbound health gates before keepalived
  resumes.
- [ ] **Node and VIP validation** — complete the
  [manual production checks](failover-testing.md#manual-production-checks).
- [ ] **Failover validation** — during the maintenance window, move the VIP to
  the peer and restore it as described in
  [Failover testing](failover-testing.md).
- [ ] **Nebula Sync verification** — run `playbooks/sync.yaml`, confirm the
  Nebula Sync container is running on the controller only, and verify a known
  Pi-hole setting from the primary appears on the replica.
- [ ] **Record the result** — note backup location, playbook revision, affected
  hosts, validation results, and any rollback action in the change record.

## Steps

1. Ensure inventory is current and credentials are valid.
2. Confirm the health query name is reachable before maintenance:

   ```bash
   dig +short @<node1-ip> <pihole_verify_qname>
   dig +short @<node2-ip> <pihole_verify_qname>
   dig +short @<vip-ip> <pihole_verify_qname>
   ```

   The playbook uses `pihole_verify_qname`, then
   `pihole_unbound_verify_qname`, then `cloudflare.com` as its fallback health
   query name.
3. Run update playbook:

   ```bash
   ansible-playbook -i /path/to/inventory.yml playbooks/update-pihole.yaml
   ```

4. Observe the per-node drain/resume sequence:
   - stop keepalived on the current node so the VIP can move away before changes
   - apply OS updates and Pi-hole role changes
   - wait for the local Pi-hole DNS listener on `127.0.0.1:53` for up to 180 seconds
   - run `dig +short @127.0.0.1 <health-qname>` and require at least one IPv4 answer
   - when Unbound is deployed, run `dig` from inside the Pi-hole container to the Unbound target and require at least one IPv4 answer
   - resume keepalived only after local DNS and optional Unbound checks pass
5. Verify VIP answers DNS after run:

   ```bash
   dig +short @<vip-ip> <pihole_verify_qname>
   ```

## Health gates

`playbooks/update-pihole.yaml` runs with `serial: 1`, so only one node is
drained and updated at a time. A failure stops the play before the next node is
touched.

| Gate | When it runs | Failure behavior |
|------|--------------|------------------|
| Drain current node | Before package and Pi-hole changes | keepalived is stopped when present; the VIP should move to the other node |
| Local DNS listener | After updates, before keepalived resumes | waits up to 180 seconds for `127.0.0.1:53`; failure leaves the node drained |
| Local Pi-hole DNS | After listener is open | `dig +short @127.0.0.1 <health-qname>` must return an IPv4 line; failure leaves the node drained |
| Local Unbound DNS | Only when `pihole_unbound_present` is true | `dig` from inside the Pi-hole container to Unbound must return an IPv4 line; failure leaves the node drained |
| Keepalived resume | After local DNS gates pass | keepalived starts only for a locally healthy node |
| VIP DNS verify | After all nodes update, when HA and `pihole_vip_ipv4` are set | retries for up to about 60 seconds (`30` retries, `2` seconds delay) and fails the run if the VIP does not answer |

## Retry guidance

- If a node fails before keepalived resumes, leave it out of VIP service until
  local DNS is healthy. Check `docker ps`, Pi-hole logs, Unbound logs, and direct
  DNS with `dig +short @127.0.0.1 <health-qname>` on that node.
- After repair, re-run `playbooks/update-pihole.yaml`. Because the playbook is
  rolling and idempotent, it will re-check the repaired node before moving on.
- If only the final VIP check fails, verify keepalived status on both nodes,
  confirm `pihole_vip_ipv4` matches the expected address, and query each node
  directly before testing the VIP again.

## Rollback notes

- Re-run previous collection version/playbook commit against the same inventory.
- If one node fails health checks, playbook halts before touching the next node.
- Restore service on failed node, then re-run update playbook.
