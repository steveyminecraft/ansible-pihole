# Failover Testing

Use Molecule shared HA verification and manual checks to confirm failover behavior.

## Automated (Molecule)

Run:

```bash
molecule test -s ubuntu
```

`molecule/common/verify_ha.yml` orchestrates focused verifier task files under
`molecule/common/verify/` and validates:

- VRRP VIP failover and failback
- Local DNS and VIP DNS responses
- container-stop-triggered failover
- DNS-functional failover (service loss while container exists)

## Manual production checks

1. Query each node directly:

   ```bash
   dig +short @<node1-ip> <pihole_verify_qname>
   dig +short @<node2-ip> <pihole_verify_qname>
   ```

2. Query VIP:

   ```bash
   dig +short @<vip-ip> <pihole_verify_qname>
   ```

3. Simulate primary outage (maintenance window) and confirm VIP moves to backup.
4. Restore primary and confirm failback policy outcome.
