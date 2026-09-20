"""Guards for AWS remote OS families, including phase-two Pi OS ARM."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AWS_REMOTE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "aws-remote-tests.yml"
CREATE_EPHEMERAL = REPO_ROOT / "tests" / "remote" / "aws" / "create-ephemeral-env.sh"


class AwsRemoteOsFamilyTests(unittest.TestCase):
    def test_phase_two_pi_os_arm_is_a_manual_coverage_option(self) -> None:
        text = AWS_REMOTE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("phase-two-pi-os-arm", text)
        self.assertIn('row("pi-os", "12", "arm64", "admin")', text)
        self.assertIn("AWS_PI_OS_AMI_ID", text)
        # Scheduled/label runs stay Ubuntu amd64 (phase 1).
        self.assertIn('row("ubuntu", "26.04", "amd64", "ubuntu")', text)

    def test_create_ephemeral_supports_debian_and_pi_os(self) -> None:
        text = CREATE_EPHEMERAL.read_text(encoding="utf-8")
        self.assertIn("resolve_debian_ami", text)
        self.assertIn("/aws/service/debian/release/", text)
        self.assertIn('pi-os)', text)
        self.assertIn("AWS_PI_OS_AMI_ID", text)
        self.assertIn("Phase 2 stand-in", text)
        self.assertNotIn("only ubuntu is supported", text)
