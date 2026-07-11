# Backup and Restore

For planned production changes, start with the
[production change checklist](upgrade-runbook.md#production-change-checklist).
This page covers its backup and recovery steps.

## What to back up

- Pi-hole persistent data:
  - `/opt/pihole/etc/pihole`
  - `/opt/pihole/etc/dnsmasq.d`
- Inventory and vaulted secrets used for deployment.

## Backup pattern

1. Snapshot/export Pi-hole directories from both nodes.
2. Store backups off-host.
3. Keep retention policy (daily/weekly) appropriate for your environment.

## Pre-change backup checklist

- [ ] Back up `/opt/pihole/etc/pihole` and `/opt/pihole/etc/dnsmasq.d` from
  both nodes.
- [ ] Back up the production inventory and vaulted secrets without decrypting
  secrets into the change record.
- [ ] Store the backup off-host and record its location and timestamp.
- [ ] Confirm the backup is readable before starting maintenance.
- [ ] Continue with the
  [rolling update steps](upgrade-runbook.md#steps).

## Restore (single node loss)

1. Rebuild host and baseline access.
2. Restore Pi-hole persistent directories.
3. Re-run bootstrap playbook for that host.
4. Validate local DNS and VIP behavior.

## Restore (dual node loss)

1. Rebuild node 1, restore data, run bootstrap.
2. Rebuild node 2, restore data, run bootstrap.
3. Run sync playbook and verify replicated settings.

## Post-restore checks

- `dig +short @<node-ip> <pihole_verify_qname>`
- `dig +short @<vip-ip> <pihole_verify_qname>`
- Keepalived service running on both nodes.
- Nebula Sync containers running and pointed at expected endpoints.

After recovery, complete the
[manual failover checks](failover-testing.md#manual-production-checks) before
closing the incident or change.
