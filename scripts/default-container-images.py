#!/usr/bin/env python3
"""Emit the default deployed container images from role defaults."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_defaults(role: str) -> dict:
    path = ROOT / "roles" / role / "defaults" / "main.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--github-matrix",
        action="store_true",
        help="emit a GitHub Actions include matrix",
    )
    args = parser.parse_args()

    images = default_images()
    if args.github_matrix:
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

    print("\n".join(images))


if __name__ == "__main__":
    main()
