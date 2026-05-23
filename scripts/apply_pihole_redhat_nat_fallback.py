#!/usr/bin/env python3
"""
Apply compatibility edits to Galaxy-installed docker-pihole
``roles/pihole/tasks/redhat_nat_fallback.yml``.

We avoid ``patch(1)`` for this file: GNU patch on Ubuntu 22.04 (GitHub Actions) rejects
some unified-diff hunks that newer patch accepts (e.g. lines containing only ``+``).

Idempotent: exits 0 if ``Add nftables masquerade rules per Docker subnet`` is already present.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "Add nftables masquerade rules per Docker subnet"
DONE_LINE = '        done < <(docker network inspect "$id" 2>/dev/null | python3 "$H" 2>/dev/null || true)'

OLD_AFTER_FAILED = (
    "  failed_when: false\n\n"
    "- name: Apply Docker bridge egress NAT (nftables masquerade)"
)

OLD_AFTER_FAILED_TIGHT = (
    "  failed_when: false\n"
    "- name: Apply Docker bridge egress NAT (nftables masquerade)"
)

# Upstream docker-pihole shell block (without stdin / per-rule loop).
OLD_NFT = (
    "      nft delete table ip ansible_docker_nat 2>/dev/null || true\n"
    "      nft add table ip ansible_docker_nat\n"
    "      nft add chain ip ansible_docker_nat postrouting "
    "'{ type nat hook postrouting priority 100; policy accept; }'\n"
    "      buf=$(cat || true)\n"
    "      if [ -z \"${buf//[$'\\t\\r\\n ']}\" ]; then\n"
    "        buf=$'172.16.0.0/12'\n"
    "      fi\n"
    "      printf '%s\\n' \"$buf\" | sort -u | while IFS= read -r raw; do\n"
    "        cidr=\"${raw//[$'\\t\\r\\n ']}\"\n"
    "        [ -z \"$cidr\" ] && continue\n"
    "        [[ \"$cidr\" =~ ^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+/[0-9]+$ ]] || continue\n"
    "        nft add rule ip ansible_docker_nat postrouting ip saddr \"$cidr\" ip daddr != \"$cidr\" masquerade\n"
    "      done"
)

NEW_NFT = (
    "      timeout 20s nft delete table ip ansible_docker_nat 2>/dev/null || true\n"
    "      timeout 20s nft add table ip ansible_docker_nat\n"
    "      timeout 20s nft add chain ip ansible_docker_nat postrouting "
    "'{ type nat hook postrouting priority 100; policy accept; }'"
)

OLD_STDIN_TAIL = (
    "    executable: /bin/bash\n"
    "    stdin: \"{{ pihole_docker_nat_subnets.stdout | default('') }}\"\n"
    "  register: pihole_docker_nat_nft\n"
    "  changed_when: \"'CHANGED' in (pihole_docker_nat_nft.stdout | default(''))\""
)


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _reference_text() -> str:
    p = _root() / "roles/docker/tasks/redhat_nat_fallback.yml"
    return p.read_text(encoding="utf-8")


def _compute_block() -> str:
    ref = _reference_text()
    s = ref.index("- name: Compute NAT fallback subnet list")
    e = ref.index("- name: Apply Docker bridge egress NAT (nftables masquerade)")
    return ref[s:e]


def _add_nft_task_block() -> str:
    ref = _reference_text()
    s = ref.index("- name: Add nftables masquerade rules per Docker subnet")
    rest = ref[s:]
    eol = rest.index("\n", rest.index('loop: "{{ pihole_docker_nat_fallback_subnets }}"')) + 1
    return rest[:eol]


def _insert_block() -> str:
    return "  failed_when: false\n\n" + _compute_block() + "- name: Apply Docker bridge egress NAT (nftables masquerade)"


def _new_stdin_tail() -> str:
    return (
        "    executable: /bin/bash\n"
        "  register: pihole_docker_nat_nft\n"
        "  changed_when: \"'CHANGED' in (pihole_docker_nat_nft.stdout | default(''))\"\n"
        "\n"
        + _add_nft_task_block()
    )


def dedupe_done_line(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        if (
            i + 1 < len(lines)
            and lines[i].rstrip("\n") == DONE_LINE
            and lines[i + 1].rstrip("\n") == DONE_LINE
        ):
            out.append(lines[i])
            i += 2
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: apply_pihole_redhat_nat_fallback.py <path-to-redhat_nat_fallback.yml>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2

    try:
        _reference_text()
    except OSError as exc:
        print(f"apply_pihole_redhat_nat_fallback: need roles/docker/tasks/redhat_nat_fallback.yml: {exc}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return 0

    text = dedupe_done_line(text)

    if "Compute NAT fallback subnet list" not in text:
        if OLD_AFTER_FAILED in text:
            text = text.replace(OLD_AFTER_FAILED, _insert_block(), 1)
        elif OLD_AFTER_FAILED_TIGHT in text:
            text = text.replace(OLD_AFTER_FAILED_TIGHT, _insert_block(), 1)
        else:
            print(
                "apply_pihole_redhat_nat_fallback: anchor after failed_when not found "
                "(upstream docker-pihole redhat_nat_fallback.yml changed?)",
                file=sys.stderr,
            )
            return 1

    if OLD_NFT not in text:
        print(
            "apply_pihole_redhat_nat_fallback: nft masquerade block not found (upstream changed?)",
            file=sys.stderr,
        )
        return 1
    text = text.replace(OLD_NFT, NEW_NFT, 1)

    if OLD_STDIN_TAIL not in text:
        print(
            "apply_pihole_redhat_nat_fallback: stdin/register block not found (upstream changed?)",
            file=sys.stderr,
        )
        return 1
    text = text.replace(OLD_STDIN_TAIL, _new_stdin_tail(), 1)

    if MARKER not in text:
        print("apply_pihole_redhat_nat_fallback: transforms did not produce expected marker", file=sys.stderr)
        return 1

    path.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
