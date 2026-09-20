# traefik

Optional Traefik reverse proxy for hosts already running this collection's
rootful **Docker** stack. The feature is off by default.

This repository does **not** switch the runtime to Podman. Traefik consumes the
Docker-compatible API through a local Unix socket (`/var/run/docker.sock` when
`traefik_socket: auto`). Socket access is privileged — equivalent to root on
the container host. Do not publish that API over TCP.

## Enable

```yaml
traefik_enabled: true
traefik_domain: home.example.com
traefik_acme_email: admin@example.com
traefik_acme_dns_provider: cloudflare
traefik_acme_environment:
  CLOUDFLARE_DNS_API_TOKEN: "{{ vault_cloudflare_token }}"
```

The Pi-hole role follows `traefik_enabled`: it joins the `proxy` network, applies
routing labels, and stops publishing host TCP 80/443. DNS 53 and optional DHCP
67 stay published.

## TLS

| `traefik_tls_mode` | Behaviour |
|--------------------|-----------|
| `dns01` | Let's Encrypt DNS-01. Preferred when you own a public zone. |
| `supplied` | Operator-provided certificate and key. No self-signed stand-in. |
| `internal_acme` | Reserved; the role fails until a private-CA flow exists. |

CI and labs that cannot issue real Let's Encrypt certificates should use
`supplied` with a lab cert, or `traefik_acme_staging: true` against Let's
Encrypt staging. This role never performs live ACME in GitHub Actions.

## Adding another application

Join `{{ traefik_network_name }}` (default `proxy`) and set labels. Traefik
watches the Docker API, so a new labelled container is routed without rerunning
Ansible or restarting Traefik.

See the collection README for a complete `whoami` example.

Part of the `steveyminecraft.pihole` collection.
