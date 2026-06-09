#!/usr/bin/env python3
"""Fail when the documented and tested ansible-core support policy drifts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MINIMUM = ">=2.20.5,<2.21"
LATEST = ">=2.21.0,<2.22"


def require(path: str, text: str) -> None:
    content = (ROOT / path).read_text(encoding="utf-8")
    if text not in content:
        raise SystemExit(f"{path} must contain {text!r}")


require("requirements.txt", f"ansible-core{LATEST}")
require("meta/runtime.yml", 'requires_ansible: ">=2.20.0"')
require("README.md", "ansible-core 2.20 or 2.21")
require("docs/production-deployment.md", "ansible-core 2.20 or 2.21")

for workflow in (".github/workflows/ci.yml", ".github/workflows/galaxy-publish.yml"):
    require(workflow, MINIMUM)
    require(workflow, LATEST)

require(".github/workflows/release-please.yml", LATEST)
require(".github/actions/import-galaxy-role/action.yml", LATEST)
print("Ansible Core support policy is aligned.")
