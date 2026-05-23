# Backup and Restore

## What to back up

- Pi-hole persistent data:
  - `/opt/pihole/etc/pihole`
  - `/opt/pihole/etc/dnsmasq.d`
- Inventory and vaulted secrets used for deployment.

## Backup pattern

1. Snapshot/export Pi-hole directories from both nodes.
2. Store backups off-host.
3. Keep retention policy (daily/weekly) appropriate for your environment.

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

- `dig +short @<node-ip> google.com`
- `dig +short @<vip-ip> google.com`
- Keepalived service running on both nodes.
- Nebula Sync containers running and pointed at expected endpoints.
