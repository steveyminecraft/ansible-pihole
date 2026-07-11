#!/usr/bin/env python3
"""Compare pinned pihole/pihole image tag against Docker Hub calendar releases."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKER_HUB_TAGS_URL = (
    "https://hub.docker.com/v2/repositories/pihole/pihole/tags?page_size=100"
)
CALENDAR_TAG = re.compile(r"^(?P<year>\d{4})\.(?P<month>\d{2})\.(?P<patch>\d+)$")


def _load_default_container_images_module():
    script = ROOT / "scripts" / "default-container-images.py"
    spec = importlib.util.spec_from_file_location("default_container_images", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_pinned_image() -> str:
    return _load_default_container_images_module().pinned_pihole_image()


def parse_calendar_tag(tag: str) -> tuple[int, int, int] | None:
    match = CALENDAR_TAG.match(tag.strip())
    if not match:
        return None
    return (
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("patch")),
    )


def pinned_tag(image: str) -> str:
    return image.rsplit(":", 1)[-1]


def fetch_calendar_tags() -> list[str]:
    tags: list[str] = []
    url: str | None = DOCKER_HUB_TAGS_URL

    while url:
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "ansible-pihole-upstream-watch"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)

        for result in payload.get("results", []):
            name = result.get("name")
            if isinstance(name, str) and parse_calendar_tag(name):
                tags.append(name)

        url = payload.get("next")

    return tags


def latest_calendar_tag(tags: list[str]) -> str | None:
    parsed = [(parse_calendar_tag(tag), tag) for tag in tags]
    valid = [(version, tag) for version, tag in parsed if version is not None]
    if not valid:
        return None
    return max(valid, key=lambda item: item[0])[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit 1 when Docker Hub has a newer calendar tag than the pinned default.",
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="Write update_available, pinned_tag, and latest_tag to GITHUB_OUTPUT",
    )
    args = parser.parse_args()

    image = load_pinned_image()
    current = pinned_tag(image)
    current_version = parse_calendar_tag(current)
    if current_version is None:
        print(f"Pinned tag is not a calendar release: {current}", file=sys.stderr)
        return 2

    upstream_tags = fetch_calendar_tags()
    latest = latest_calendar_tag(upstream_tags)
    if latest is None:
        print("No calendar-version tags found on Docker Hub.", file=sys.stderr)
        return 2

    update_available = parse_calendar_tag(latest) > current_version
    summary = {
        "pinned_image": image,
        "pinned_tag": current,
        "latest_tag": latest,
        "update_available": update_available,
    }

    print(json.dumps(summary, indent=2))

    if args.github_output:
        output_path = Path(os.environ["GITHUB_OUTPUT"])
        lines = [
            f"update_available={'true' if update_available else 'false'}",
            f"pinned_tag={current}",
            f"latest_tag={latest}",
            f"pinned_image={image}",
        ]
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.fail_on_drift and update_available:
        print(
            f"Pinned Pi-hole tag {current} is behind Docker Hub latest {latest}. "
            "Bump roles/pihole/defaults/main.yml and run "
            "python scripts/check-pihole-image-pins.py --sync.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
