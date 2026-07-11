#!/usr/bin/env python3
"""Warn when inventory YAML still defines legacy unprefixed Pi-hole variables."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover - CI always has PyYAML
    yaml = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]

# Legacy inventory keys accepted by roles/pihole compatibility lookups.
DEPRECATED_VARS: dict[str, tuple[str, str]] = {
    "dir_loc": ("pihole_dir_loc", "v2.0.0"),
    "firewall_deploy": ("pihole_firewall_deploy", "v2.0.0"),
    "webport_http": ("pihole_webport_http", "v2.0.0"),
    "webport_https": ("pihole_webport_https", "v2.0.0"),
    "docker_manage_iptables": ("pihole_docker_manage_iptables", "v2.0.0"),
    "docker_el_nat_fallback": ("pihole_docker_el_nat_fallback", "v2.0.0"),
    "pihole_unbound_verify_qname": ("pihole_verify_qname", "v2.0.0"),
}

DEFAULT_SCAN_ROOTS = (
    REPO_ROOT / "inventory",
    REPO_ROOT / "tests" / "remote" / "inventories",
    REPO_ROOT / "molecule",
)


@dataclass(frozen=True)
class Finding:
    path: Path
    key: str
    replacement: str
    removal: str


def inventory_yaml_files(roots: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.yml")) + sorted(root.rglob("*.yaml")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel.startswith("molecule/") and "/group_vars/" not in rel and "/host_vars/" not in rel:
                continue
            if "/tasks/" in rel or "/handlers/" in rel or "/verify/" in rel:
                continue
            if path.name in {"converge.yml", "converge.yaml", "prepare.yml", "verify.yml"}:
                continue
            files.append(path)
    return files


def walk_mapping(
    node: Any,
    *,
    path: Path,
    prefix: str,
    findings: list[Finding],
) -> None:
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        key_text = str(key)
        dotted = f"{prefix}.{key_text}" if prefix else key_text
        if key_text in DEPRECATED_VARS:
            replacement, removal = DEPRECATED_VARS[key_text]
            findings.append(
                Finding(
                    path=path,
                    key=dotted,
                    replacement=replacement,
                    removal=removal,
                )
            )
        if isinstance(value, dict):
            walk_mapping(value, path=path, prefix=dotted, findings=findings)


def scan_file(path: Path) -> list[Finding]:
    if yaml is None:
        raise SystemExit("PyYAML is required (pip install pyyaml)")
    findings: list[Finding] = []
    try:
        documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    except yaml.YAMLError as exc:
        print(f"{path}: unable to parse YAML ({exc})", file=sys.stderr)
        return findings
    for document in documents:
        if document is None:
            continue
        walk_mapping(document, path=path, prefix="", findings=findings)
    return findings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Inventory files or directories (default: inventory/, tests/remote/inventories/, molecule group/host vars)",
    )
    parser.add_argument(
        "--fail-on-find",
        action="store_true",
        help="Exit 1 when deprecated variables are found (default: warn only)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.paths:
        targets: list[Path] = []
        for path in args.paths:
            if path.is_dir():
                targets.extend(inventory_yaml_files([path]))
            elif path.is_file():
                targets.append(path)
            else:
                print(f"{path}: not found", file=sys.stderr)
                return 1
    else:
        targets = inventory_yaml_files(DEFAULT_SCAN_ROOTS)

    all_findings: list[Finding] = []
    for path in targets:
        all_findings.extend(scan_file(path))

    if not all_findings:
        print(f"OK — no legacy unprefixed variables in {len(targets)} file(s)")
        return 0

    for finding in all_findings:
        try:
            rel = finding.path.relative_to(REPO_ROOT)
        except ValueError:
            rel = finding.path
        print(
            f"WARN {rel}: `{finding.key}` is deprecated; "
            f"use `{finding.replacement}` (removal target {finding.removal})",
            file=sys.stderr,
        )

    print(
        f"Found {len(all_findings)} deprecated variable(s) in {len({f.path for f in all_findings})} file(s)",
        file=sys.stderr,
    )
    return 1 if args.fail_on_find else 0


if __name__ == "__main__":
    raise SystemExit(main())
