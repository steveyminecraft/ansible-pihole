#!/usr/bin/env python3
"""Validate security-sensitive collection defaults and lab opt-ins."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(relative_path: str) -> dict:
    path = ROOT / relative_path
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    docker = load_yaml("roles/docker/defaults/main.yml")
    keepalived = load_yaml("roles/keepalived/defaults/main.yml")
    pihole = load_yaml("roles/pihole/defaults/main.yml")
    vagrant = load_yaml("inventory/vagrant.yml")["all"]["vars"]
    vagrant_libvirt = load_yaml("inventory/vagrant_libvirt.yml")["all"]["vars"]

    require(docker["docker_group_users"] == [], "Docker group users must default to empty")
    require(not docker["docker_enable_ip_forward"], "Docker IPv4 forwarding must default off")
    require(
        not keepalived["keepalived_enable_ip_forward"],
        "Keepalived IPv4 forwarding must default off",
    )
    require(
        not keepalived["keepalived_selinux_permissive"],
        "Keepalived SELinux permissive mode must default off",
    )
    require(pihole["pihole_enable_unbound"], "Unbound compatibility default must remain enabled")
    require(
        pihole["pihole_upstream_resolvers"] == [],
        "Pi-hole fallback upstreams must not be silently supplied",
    )
    require(":latest" not in pihole["pihole_image"], "Pi-hole default image must be pinned")

    for name, lab in (("vagrant", vagrant), ("vagrant_libvirt", vagrant_libvirt)):
        require(
            lab["docker_group_users"] == ["vagrant"],
            f"{name} must explicitly request Docker group membership",
        )
        require(
            lab["docker_enable_ip_forward"] is True,
            f"{name} must explicitly request its lab forwarding topology",
        )

    print("Security-sensitive defaults and lab opt-ins are valid.")


if __name__ == "__main__":
    main()
