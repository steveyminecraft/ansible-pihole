#!/usr/bin/env python3
"""
Replace the Pi-hole \"wait for healthy\" task in Galaxy-installed docker-pihole
``roles/pihole/tasks/unbound.yml`` with the container-running / non-unhealthy check.

Avoids ``patch(1)``: GNU patch on Ubuntu 22.04 rejects some unified-diff blank lines.

Idempotent: exits 0 if ``Wait until Pi-hole container is running`` is already present.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "Wait until Pi-hole container is running"

OLD = """    - pihole_unbound_present
    - pihole_unbound_container_ipv4 | default('') | length > 0

# Wait for Pi-hole to be ready
- name: Wait until Pi-hole is healthy
  ansible.builtin.command:
    argv:
      - docker
      - inspect
      - -f
      - "{{ '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' }}"
      - "{{ pihole_container_name | default('pihole') }}"
  register: pihole_health
  retries: 30
  delay: 2
  until: (pihole_health.stdout | default('', true) | trim) in ['healthy', 'none']
  changed_when: false
  when: pihole_unbound_present"""

NEW = """    - pihole_unbound_present
    - pihole_unbound_container_ipv4 | default('') | length > 0

# Wait for Pi-hole to be ready enough for functional checks. Docker health can remain
# "starting" during the image start period even while DNS is already available.
- name: Wait until Pi-hole container is running
  ansible.builtin.command:
    argv:
      - docker
      - inspect
      - -f
      - "{{ '{{.State.Running}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' }}"
      - "{{ pihole_container_name | default('pihole') }}"
  register: pihole_health
  retries: 30
  delay: 2
  until:
    - (pihole_health.stdout | default('', true) | trim).split()[0] == 'true'
    - (pihole_health.stdout | default('', true) | trim).split()[1] | default('none') != 'unhealthy'
  changed_when: false
  when: pihole_unbound_present"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: apply_pihole_unbound_health_wait.py <path-to-unbound.yml>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return 0
    if OLD not in text:
        print(
            "apply_pihole_unbound_health_wait: expected upstream wait-for-healthy block not found "
            "(docker-pihole unbound.yml changed?)",
            file=sys.stderr,
        )
        return 1
    path.write_text(text.replace(OLD, NEW, 1), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
