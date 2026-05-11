#!/usr/bin/env python3
"""
Apply Galaxy docker-pihole role overrides without ``patch(1)``.

GNU patch 2.7 on Ubuntu 22.04 (GitHub Actions) rejects several unified diffs that
newer patch accepts. This module performs the same edits as the former
``patches/docker-pihole-*.patch`` files for defaults and unbound.

Usage:
  apply_pihole_galaxy_install_overrides.py defaults <path/to/roles/pihole/defaults/main.yml>
  apply_pihole_galaxy_install_overrides.py unbound <path/to/roles/pihole/tasks/unbound.yml>
"""
from __future__ import annotations

import sys
from pathlib import Path

# --- defaults/main.yml (was docker-pihole-default-docker-dns.patch) ---

DEFAULTS_OLD = """# Docker Compose `dns:` for the Pi-hole service — written into the container's resolv.conf.
# Public DNS first: with Docker `"iptables": false"` (common on EL/Vagrant), 127.0.0.11 is often
# refused; gravity needs resolvers that work. Keep 127.0.0.11 last so Docker hostnames (e.g.
# unbound) still resolve after earlier servers return NXDOMAIN. Set to [] to omit `dns:`.
pihole_docker_dns:
  - "8.8.8.8"
  - "8.8.4.4"
  - "127.0.0.11"
"""

DEFAULTS_NEW = """# Docker Compose `dns:` for the Pi-hole service. Keep empty by default so Docker's
# embedded resolver can resolve shared-network service names such as `unbound`.
pihole_docker_dns: []
"""


def apply_defaults(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    if "pihole_docker_dns: []" in text and "embedded resolver" in text:
        return 0
    if "Public DNS first" not in text:
        return 0
    if DEFAULTS_OLD not in text:
        print("apply_pihole_galaxy_install_overrides: defaults block not found (upstream changed?)", file=sys.stderr)
        return 1
    path.write_text(text.replace(DEFAULTS_OLD, DEFAULTS_NEW, 1), encoding="utf-8", newline="\n")
    return 0


# --- unbound.yml: insert IP / DNS target tasks (was docker-pihole-unbound-ip-upstream.patch) ---

UNBOUND_INSERT_AFTER_SET_FACT = """- name: Set fact if Unbound is running
  ansible.builtin.set_fact:
    pihole_unbound_present: "{{ (unbound_running.rc == 0) and (unbound_running.stdout | trim == 'true') }}"

- name: Ensure shared external docker network exists (dns_net)"""

UNBOUND_INSERT_BLOCK = """- name: Set fact if Unbound is running
  ansible.builtin.set_fact:
    pihole_unbound_present: "{{ (unbound_running.rc == 0) and (unbound_running.stdout | trim == 'true') }}"

- name: Set docker inspect format
  ansible.builtin.set_fact:
    docker_inspect_networks_fmt: "{{ '{{json .NetworkSettings.Networks}}' }}"
  when: pihole_unbound_present

- name: Inspect Unbound container networks
  ansible.builtin.command:
    argv:
      - docker
      - inspect
      - --format
      - "{{ docker_inspect_networks_fmt }}"
      - "{{ unbound_container_name | default('unbound') }}"
  register: unbound_net_json
  changed_when: false
  failed_when: unbound_net_json.rc != 0
  when: pihole_unbound_present

- name: Set Unbound container primary IPv4 for Pi-hole upstream
  ansible.builtin.set_fact:
    pihole_unbound_container_ipv4: >-
      {{
        (
          unbound_net_json.stdout | from_json
          | dict2items
          | map(attribute='value.IPAddress')
          | reject('equalto', '')
          | list
          | first
          | default('', true)
        )
      }}
  when: pihole_unbound_present

- name: Set Pi-hole Unbound DNS target
  ansible.builtin.set_fact:
    pihole_unbound_dns_target: >-
      {{
        pihole_unbound_container_ipv4
        if (pihole_unbound_container_ipv4 | default('') | length > 0)
        else (unbound_container_name | default('unbound'))
      }}
  when: pihole_unbound_present

- name: Ensure shared external docker network exists (dns_net)"""

FTL_OLD = "            'FTLCONF_dns_upstreams': (pihole_unbound_upstream | default('unbound#5335')),"
FTL_NEW = (
    "            'FTLCONF_dns_upstreams': "
    "((pihole_unbound_dns_target | default(unbound_container_name | default('unbound'))) "
    "~ '#' ~ (unbound_port | default(5335) | string)),"
)

DIG_UNBOUND_OLD = (
    '    sh -lc "dig @{{ unbound_container_name | default(\'unbound\') }} '
    "-p {{ unbound_port | default(5335) }} {{ pihole_unbound_verify_qname }} +short\""
)
DIG_UNBOUND_NEW = (
    '    sh -lc "dig @{{ pihole_unbound_dns_target | default(unbound_container_name | default(\'unbound\')) }} '
    "-p {{ unbound_port | default(5335) }} {{ pihole_unbound_verify_qname }} +short\""
)

# --- local DNS retry (was docker-pihole-local-dns-retry.patch) ---

LOCAL_DIG_OLD = (
    '    sh -lc "dig @127.0.0.1 -p 53 {{ pihole_unbound_verify_qname }} +short"\n'
    "  register: pihole_dns_test\n"
    "  changed_when: false\n"
    "  failed_when: >"
)

LOCAL_DIG_NEW = (
    '    sh -lc "dig @127.0.0.1 -p 53 {{ pihole_unbound_verify_qname }} +short +tries=1 +time=2"\n'
    "  register: pihole_dns_test\n"
    "  retries: 60\n"
    "  delay: 2\n"
    "  until: >\n"
    "    (pihole_dns_test.stdout_lines\n"
    "      | select('match', '^[0-9]+\\\\.[0-9]+\\\\.[0-9]+\\\\.[0-9]+$')\n"
    "      | list\n"
    "      | length) > 0\n"
    "  changed_when: false\n"
    "  failed_when: >"
)

# --- startup resolver + force recreate (was docker-pihole-unbound-startup-resolver.patch) ---

STARTUP_INSERT_OLD = """      }}
  when: pihole_unbound_present

- name: Ensure shared external docker network exists (dns_net)"""

STARTUP_INSERT_NEW = """      }}
  when: pihole_unbound_present

- name: Use public DNS as Pi-hole container startup resolver
  ansible.builtin.set_fact:
    pihole_docker_dns: "{{ pihole_startup_dns | default(['8.8.8.8', '8.8.4.4']) }}"
  when:
    - pihole_unbound_present
    - pihole_unbound_container_ipv4 | default('') | length > 0

- name: Ensure shared external docker network exists (dns_net)"""

COMPOSE_UP_OLD = '    cmd: docker compose -f "{{ pihole_compose_file }}" up -d'
COMPOSE_UP_NEW = '    cmd: docker compose -f "{{ pihole_compose_file }}" up -d --force-recreate'

# --- resolv.conf override (was docker-pihole-resolv-conf-override.patch) ---

RESOLV_INSERT_OLD = """  failed_when: pihole_compose_up.rc != 0
  when: pihole_unbound_present

- name: Inspect Docker DNS network for attached containers"""

RESOLV_INSERT_NEW = """  failed_when: pihole_compose_up.rc != 0
  when: pihole_unbound_present

- name: Override Pi-hole container resolv.conf when Docker DNS redirect is unavailable
  ansible.builtin.shell:
    cmd: docker exec -i "{{ pihole_container_name | default('pihole') }}" sh -c 'cat > /etc/resolv.conf'
    stdin: |
      {% for nameserver in pihole_docker_dns | default([]) %}
      nameserver {{ nameserver }}
      {% endfor %}
      options ndots:0
  changed_when: true
  when:
    - pihole_unbound_present
    - not (docker_manage_iptables | default(true) | bool)
    - pihole_docker_dns | default([]) | length > 0

- name: Inspect Docker DNS network for attached containers"""


def _apply_resolve_unbound_when(text: str) -> str:
    """Narrow `when` on *Verify Pi-hole can resolve Unbound* (not other tasks)."""
    hdr = "- name: Verify Unbound answers DNS queries (from Pi-hole container)"
    if hdr not in text:
        return text
    i = text.index(hdr)
    prev = text[:i]
    if "pihole_resolve_unbound.stdout_lines" not in prev[-4000:]:
        return text
    when_old = "  when: pihole_unbound_present\n\n"
    when_new = (
        "  when:\n"
        "    - pihole_unbound_present\n"
        "    - pihole_unbound_dns_target == (unbound_container_name | default('unbound'))\n\n"
    )
    j = prev.rfind(when_old)
    if j == -1:
        return text
    gap = text[j:i]
    if "pihole_unbound_dns_target ==" in gap:
        return text
    return text[:j] + when_new + text[j + len(when_old) :]


def apply_unbound(path: Path) -> int:
    orig = path.read_text(encoding="utf-8")
    text = orig

    if UNBOUND_INSERT_AFTER_SET_FACT in text and "pihole_unbound_dns_target" not in text:
        text = text.replace(UNBOUND_INSERT_AFTER_SET_FACT, UNBOUND_INSERT_BLOCK, 1)

    if FTL_OLD in text:
        text = text.replace(FTL_OLD, FTL_NEW, 1)

    text = _apply_resolve_unbound_when(text)

    if DIG_UNBOUND_OLD in text:
        text = text.replace(DIG_UNBOUND_OLD, DIG_UNBOUND_NEW, 1)

    if "retries: 60" not in text and LOCAL_DIG_OLD in text:
        text = text.replace(LOCAL_DIG_OLD, LOCAL_DIG_NEW, 1)

    if "Use public DNS as Pi-hole container startup resolver" not in text and STARTUP_INSERT_OLD in text:
        text = text.replace(STARTUP_INSERT_OLD, STARTUP_INSERT_NEW, 1)

    if COMPOSE_UP_OLD in text:
        text = text.replace(COMPOSE_UP_OLD, COMPOSE_UP_NEW, 1)

    if "Override Pi-hole container resolv.conf when Docker DNS redirect is unavailable" not in text and RESOLV_INSERT_OLD in text:
        text = text.replace(RESOLV_INSERT_OLD, RESOLV_INSERT_NEW, 1)

    if text != orig:
        path.write_text(text, encoding="utf-8", newline="\n")
    return 0


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: apply_pihole_galaxy_install_overrides.py "
            "{defaults|unbound} <path>",
            file=sys.stderr,
        )
        return 2
    mode, p = sys.argv[1], Path(sys.argv[2])
    if not p.is_file():
        print(f"not a file: {p}", file=sys.stderr)
        return 2
    if mode == "defaults":
        return apply_defaults(p)
    if mode == "unbound":
        return apply_unbound(p)
    print(f"unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
