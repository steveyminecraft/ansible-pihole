# Failover Testing

Use Molecule shared HA verification and manual checks to confirm failover behavior.

## Automated (Molecule)

Run:

```bash
molecule test -s ubuntu
```

`molecule/common/verify_ha.yml` validates:

- VRRP VIP failover and failback
- Local DNS and VIP DNS responses
- container-stop-triggered failover
- DNS-functional failover (service loss while container exists)

## Manual production checks

1. Query each node directly:

   ```bash
   dig +short @<node1-ip> google.com
   dig +short @<node2-ip> google.com
   ```

2. Query VIP:

   ```bash
   dig +short @<vip-ip> google.com
   ```

3. Simulate primary outage (maintenance window) and confirm VIP moves to backup.
4. Restore primary and confirm failback policy outcome.
