#!/usr/bin/env python3
"""Ensure CI/lab mirror files use the canonical pihole_image from role defaults."""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files that must mirror roles/pihole/defaults/main.yml pihole_image exactly.
MIRROR_PATHS = (
    "inventory/ci/group_vars/all.yml",
    "playbooks/ci-bootstrap.yaml",
    "playbooks/ci-validate-pihole-modes.yaml",
)

PIHOLE_IMAGE_LINE = re.compile(
    r'^(?P<prefix>\s*pihole_image:\s*")(?P<value>[^"]+)(".*)$',
    re.MULTILINE,
)


def pinned_pihole_image() -> str:
    script = ROOT / "scripts" / "default-container-images.py"
    spec = importlib.util.spec_from_file_location("default_container_images", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.pinned_pihole_image()


def read_mirror_value(relative_path: str) -> str | None:
    path = ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    match = PIHOLE_IMAGE_LINE.search(text)
    if not match:
        return None
    return match.group("value")


def sync_mirror(relative_path: str, canonical_image: str) -> bool:
    path = ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    updated, count = PIHOLE_IMAGE_LINE.subn(
        lambda match: f'{match.group("prefix")}{canonical_image}{match.group(3)}',
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"Expected one pihole_image line in {relative_path}, found {count}")
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def validate_pins() -> list[str]:
    canonical = pinned_pihole_image()
    errors: list[str] = []
    for relative_path in MIRROR_PATHS:
        mirror_value = read_mirror_value(relative_path)
        if mirror_value is None:
            errors.append(f"{relative_path}: pihole_image line not found")
        elif mirror_value != canonical:
            errors.append(
                f"{relative_path}: pihole_image is {mirror_value!r}, "
                f"expected canonical {canonical!r} from roles/pihole/defaults/main.yml"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Rewrite mirror files to match roles/pihole/defaults/main.yml",
    )
    args = parser.parse_args(argv)

    canonical = pinned_pihole_image()
    print(f"Canonical pihole_image: {canonical}")

    if args.sync:
        for relative_path in MIRROR_PATHS:
            if sync_mirror(relative_path, canonical):
                print(f"Updated {relative_path}")
            else:
                print(f"Already current: {relative_path}")
        return 0

    errors = validate_pins()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(
            "Run: python scripts/check-pihole-image-pins.py --sync",
            file=sys.stderr,
        )
        return 1

    print("All CI mirror pins match role defaults.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
