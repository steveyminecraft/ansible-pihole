#!/usr/bin/env python3
"""Pre-flight checks for Pi-hole HA inventory before bootstrap or update."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REJECTED_SECRET_VALUES = frozenset(
    {
        "",
        "CHANGE_ME",
        "Intranet",
        "Testing 101",
        "REPLACE_WITH_ANSIBLE_VAULT",
        "LabOnly-Molecule-Pihole-Password!",
        "replace-me",
    }
)

HA_HOST_KEYS = ("ansible_host", "priority", "keepalive_role")


def load_ansible_inventory(inventory_path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ansible-inventory", "-i", str(inventory_path), "--list"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"ansible-inventory failed for {inventory_path}:\n{result.stderr.strip()}"
        )
    return json.loads(result.stdout)


def inventory_hosts(inventory: dict[str, Any]) -> list[str]:
    hostvars = inventory.get("_meta", {}).get("hostvars", {})
    return sorted(hostvars.keys())


def host_var(hostvars: dict[str, Any], host: str, key: str, default: Any = None) -> Any:
    return hostvars.get(host, {}).get(key, default)


def merged_var(hostvars: dict[str, Any], hosts: list[str], key: str, default: Any = None) -> Any:
    for host in hosts:
        value = host_var(hostvars, host, key, default=None)
        if value is not None:
            return value
    return default


def is_unresolved_secret(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if "{{" in text and "}}" in text:
        return False
    if text in REJECTED_SECRET_VALUES:
        return True
    return False


def validate_structure(inventory: dict[str, Any], errors: list[str]) -> None:
    hostvars = inventory.get("_meta", {}).get("hostvars", {})
    hosts = inventory_hosts(inventory)
    if not hosts:
        errors.append("Inventory defines no hosts.")
        return

    if merged_var(hostvars, hosts, "pihole_compose_dir") in (None, ""):
        errors.append("Set pihole_compose_dir in inventory (not role-defaulted for production).")

    ha_mode = merged_var(hostvars, hosts, "pihole_ha_mode", False)
    if not ha_mode:
        return

    if len(hosts) < 2:
        errors.append("pihole_ha_mode is true but fewer than two hosts are defined.")

    if not merged_var(hostvars, hosts, "pihole_vip_ipv4"):
        errors.append("pihole_ha_mode is true but pihole_vip_ipv4 is missing.")

    for host in hosts:
        for key in HA_HOST_KEYS:
            if host_var(hostvars, host, key) in (None, ""):
                errors.append(f"Host {host} is missing required HA key '{key}'.")

    controller_group = inventory.get("nebula_sync_controller", {})
    hosts_entry = controller_group.get("hosts") or []
    if isinstance(hosts_entry, dict):
        controller_hosts = list(hosts_entry.keys())
    else:
        controller_hosts = list(hosts_entry)
    if len(controller_hosts) != 1:
        errors.append(
            "nebula_sync_controller group must exist with exactly one host "
            f"(found {len(controller_hosts)})."
        )

    primary_url = merged_var(hostvars, hosts, "nebula_sync_primary_url")
    if primary_url:
        replicas = merged_var(hostvars, hosts, "nebula_sync_replicas", [])
        if not replicas:
            errors.append("nebula_sync_primary_url is set but nebula_sync_replicas is empty.")


def validate_secrets(inventory: dict[str, Any], errors: list[str]) -> None:
    hostvars = inventory.get("_meta", {}).get("hostvars", {})
    hosts = inventory_hosts(inventory)
    if not hosts:
        return

    reference_host = hosts[0]
    env = host_var(hostvars, reference_host, "pihole_environment_variables", {}) or {}
    api_password = env.get("FTLCONF_webserver_api_password")
    if is_unresolved_secret(api_password):
        errors.append(
            "Pi-hole FTLCONF_webserver_api_password is missing, placeholder, or vault unresolved."
        )
    elif isinstance(api_password, str) and len(api_password) < 16:
        errors.append("Pi-hole FTLCONF_webserver_api_password must be at least 16 characters.")

    primary_url = merged_var(hostvars, hosts, "nebula_sync_primary_url")
    if not primary_url:
        return

    primary_password = merged_var(hostvars, hosts, "nebula_sync_primary_password")
    if is_unresolved_secret(primary_password):
        errors.append("nebula_sync_primary_password is missing, placeholder, or vault unresolved.")

    replicas = merged_var(hostvars, hosts, "nebula_sync_replicas", []) or []
    for index, replica in enumerate(replicas):
        if not isinstance(replica, dict):
            errors.append(f"nebula_sync_replicas[{index}] must be a mapping with url and password.")
            continue
        if not str(replica.get("url", "")).strip():
            errors.append(f"nebula_sync_replicas[{index}].url is empty.")
        replica_password = replica.get("password")
        if is_unresolved_secret(replica_password):
            errors.append(
                f"nebula_sync_replicas[{index}].password is missing, placeholder, or vault unresolved."
            )


def validate_inventory(inventory_path: Path, *, structure_only: bool = False) -> list[str]:
    inventory = load_ansible_inventory(inventory_path)
    errors: list[str] = []
    validate_structure(inventory, errors)
    if not structure_only:
        validate_secrets(inventory, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inventories",
        nargs="+",
        type=Path,
        help="Inventory file or directory passed to ansible-inventory -i",
    )
    parser.add_argument(
        "--structure-only",
        action="store_true",
        help="Validate HA layout and groups without checking secret values.",
    )
    args = parser.parse_args(argv)

    exit_code = 0
    for inventory_path in args.inventories:
        errors = validate_inventory(inventory_path, structure_only=args.structure_only)
        if errors:
            exit_code = 1
            print(f"{inventory_path}: FAIL", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
        else:
            print(f"{inventory_path}: OK")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
