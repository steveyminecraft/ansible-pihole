#!/usr/bin/env python3
"""DNS health-gate helpers mirroring playbooks/update-pihole.yaml expressions."""

from __future__ import annotations

import re

# Keep aligned with failed_when / until filters in playbooks/update-pihole.yaml.
IPV4_LINE_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$")


def dig_stdout_has_ipv4_answer(stdout_lines: list[str] | tuple[str, ...] | None) -> bool:
    """Return True when dig +short output contains at least one IPv4 A-record line."""
    if not stdout_lines:
        return False
    return any(IPV4_LINE_PATTERN.match(line.strip()) for line in stdout_lines)
