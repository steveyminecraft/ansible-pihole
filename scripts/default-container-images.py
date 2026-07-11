#!/usr/bin/env python3
"""Emit the default deployed container images from role defaults."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

# GitHub code scanning keeps historical default-branch Trivy configurations in
# PR comparisons even after the deployed default image is bumped. Keep retired
# categories here until the repository security state no longer reports them as
# required for PR alert comparison.
LEGACY_CODE_SCANNING_IMAGES = (
    "pihole/pihole:2026.05.0",
    "pihole/pihole:2026.06.0",
)


def load_defaults(role: str) -> dict:
    path = ROOT / "roles" / role / "defaults" / "main.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def pinned_pihole_image() -> str:
    """Canonical Pi-hole image pin from role defaults."""
    image = load_defaults("pihole").get("pihole_image")
    if not isinstance(image, str) or ":" not in image:
        raise RuntimeError("Unable to read pihole_image from roles/pihole/defaults/main.yml")
    return image


def image_key(image: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", image).strip("-")


def default_images() -> list[str]:
    pihole = load_defaults("pihole")
    unbound = load_defaults("unbound")
    nebula = load_defaults("nebula_sync")

    images = {
        pihole["pihole_image"],
        unbound["unbound_image_arch_default"],
        *unbound["unbound_image_arch_map"].values(),
        f"{nebula['nebula_sync_image']}:{nebula['nebula_sync_image_tag']}",
    }
    return sorted(images)


def code_scanning_images() -> list[str]:
    return sorted({*default_images(), *LEGACY_CODE_SCANNING_IMAGES})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--github-matrix",
        action="store_true",
        help="emit a GitHub Actions include matrix",
    )
    args = parser.parse_args()

    if args.github_matrix:
        images = code_scanning_images()
        print(
            json.dumps(
                {
                    "include": [
                        {"image": image, "key": image_key(image)}
                        for image in images
                    ]
                },
                separators=(",", ":"),
            )
        )
        return

    print("\n".join(default_images()))


if __name__ == "__main__":
    main()
