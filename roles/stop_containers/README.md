# stop_containers

Stop running stack containers on a drained node before package updates or
Traefik bind.

This role is the **container drain** step of the HA maintenance pattern. It does
not rewrite compose files or start services — later roles do that. Missing
container names are ignored.

## When it runs

| Playbook | Position | Tags |
|----------|----------|------|
| `playbooks/bootstrap-pihole.yaml` | After `stop_keepalived`, before bootstrap/updates | `stopcontainers`, `drain`, `container` |
| `playbooks/update-pihole.yaml` | After `stop_keepalived`, before updates | `stopcontainers`, `drain`, `container` |

The role checks for `/var/run/docker.sock`, inspects each name in
`stop_containers_names`, and stops containers that exist and are running.

Default names: Pi-hole, Traefik, Unbound, and Nebula Sync (when those variables
are set; otherwise `pihole`, `traefik`, `unbound`, `nebula`).

## Drain/resume pattern

1. `stop_keepalived` — release the VIP from this node
2. **`stop_containers`** — free host ports (especially 80/443) on a running install
3. Package/Pi-hole/Traefik changes
4. Local DNS gates
5. `start_keepalived` — return the node to VIP candidacy

On a running install, Traefik cannot bind `:80`/`:443` while Pi-hole still
publishes those ports. Stopping the stack after VIP drain avoids that bind
failure.

## Example

Skip container stop while testing non-HA changes:

```bash
ansible-playbook -i inventory.yml playbooks/update-pihole.yaml --skip-tags drain,container
```

Part of the `steveyminecraft.pihole` collection.
