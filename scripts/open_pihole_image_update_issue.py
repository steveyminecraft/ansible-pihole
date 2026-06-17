#!/usr/bin/env python3
"""Open a GitHub issue when a newer pihole/pihole calendar tag is available."""

from __future__ import annotations

import os
import subprocess
import sys


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def issue_body(pinned_tag: str, latest_tag: str, pinned_image: str) -> str:
    return f"""## Summary

A newer **pihole/pihole** calendar release tag is available on Docker Hub.

| | Tag |
|---|---|
| Pinned in `roles/pihole/defaults/main.yml` | `{pinned_tag}` |
| Latest on Docker Hub | `{latest_tag}` |

Full image reference today: `{pinned_image}`

## Suggested follow-up

1. Review the [Pi-hole release notes](https://github.com/pi-hole/pi-hole/releases) and Docker Hub tag `{latest_tag}`.
2. Bump `pihole_image` in `roles/pihole/defaults/main.yml` and mirrored CI defaults if appropriate.
3. Re-run Trivy/security scanning and Molecule or AWS RC tests before merging.
4. Close this issue after the pin is updated or consciously deferred.

This issue was opened automatically by [`pihole-image-watch.yml`](.github/workflows/pihole-image-watch.yml).
"""


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=check, text=True, capture_output=True)


def main() -> int:
    pinned_tag = required_env("PINNED_TAG")
    latest_tag = required_env("LATEST_TAG")
    pinned_image = required_env("PINNED_IMAGE")

    title = f"Pi-hole Docker image update available: {latest_tag}"
    existing = run(
        [
            "gh",
            "issue",
            "list",
            "--state",
            "open",
            "--search",
            f"in:title {latest_tag}",
            "--json",
            "title",
            "--jq",
            ".[].title",
        ],
        check=False,
    )
    if existing.returncode == 0 and title in existing.stdout.splitlines():
        print(f"Open issue already exists for {latest_tag}.")
        return 0

    run(
        [
            "gh",
            "label",
            "create",
            "pihole-upstream-update",
            "--color",
            "d93f0b",
            "--description",
            "New pihole/pihole calendar tag published on Docker Hub",
        ],
        check=False,
    )

    body_file = os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), "pihole-image-update-issue.md")
    with open(body_file, "w", encoding="utf-8") as handle:
        handle.write(issue_body(pinned_tag, latest_tag, pinned_image))

    run(
        [
            "gh",
            "issue",
            "create",
            "--title",
            title,
            "--label",
            "pihole-upstream-update",
            "--body-file",
            body_file,
        ]
    )
    print(f"Opened issue: {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
