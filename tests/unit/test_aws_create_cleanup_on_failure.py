"""Tests AWS create script failure cleanup behavior."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CREATE_SCRIPT = REPO_ROOT / "tests" / "remote" / "aws" / "create-ephemeral-env.sh"


class AwsCreateCleanupOnFailureTests(unittest.TestCase):
    def run_create_with_failure(self, fail_on: str) -> tuple[subprocess.CompletedProcess[str], str, Path]:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            fake_bin = temp_dir / "bin"
            fake_bin.mkdir()
            aws_log = temp_dir / "aws.log"
            aws_script = fake_bin / "aws"
            aws_script.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "$AWS_LOG"
if [[ "$1" == "ssm" && "$2" == "get-parameter" ]]; then
  echo "ami-1234567890"
  exit 0
fi
if [[ "$1" == "ec2" && "$2" == "describe-subnets" ]]; then
  echo "vpc-1234567890"
  exit 0
fi
if [[ "$1" == "ec2" && "$2" == "create-security-group" ]]; then
  echo "sg-1234567890"
  exit 0
fi
if [[ "$1" == "ec2" && "$2" == "authorize-security-group-ingress" ]]; then
  if [[ "${FAIL_ON:-}" == "authorize-ingress" ]]; then
    exit 99
  fi
  exit 0
fi
if [[ "$1" == "ec2" && "$2" == "run-instances" ]]; then
  echo "i-1234567890"
  exit 0
fi
if [[ "$1" == "ec2" && "$2" == "wait" && "$3" == "instance-running" ]]; then
  if [[ "${FAIL_ON:-}" == "instance-running-wait" ]]; then
    exit 98
  fi
  exit 0
fi
if [[ "$1" == "ec2" && "$2" == "wait" && "$3" == "instance-status-ok" ]]; then
  exit 99
fi
if [[ "$1" == "ec2" && "$2" == "delete-security-group" ]]; then
  exit 0
fi
if [[ "$1" == "ec2" && "$2" == "describe-instances" ]]; then
  echo "0"
  exit 0
fi
if [[ "$1" == "ec2" && "$2" == "terminate-instances" ]]; then
  exit 0
fi
if [[ "$1" == "ec2" && "$2" == "wait" ]]; then
  exit 0
fi
exit 0
""",
                encoding="utf-8",
            )
            aws_script.chmod(aws_script.stat().st_mode | stat.S_IXUSR)

            inventory_template = temp_dir / "inventory-template.yml"
            inventory_template.write_text("all:\n  hosts: {}\n", encoding="utf-8")

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{fake_bin}:{env.get('PATH', '')}",
                    "AWS_LOG": str(aws_log),
                    "FAIL_ON": fail_on,
                    "AWS_REGION": "eu-west-1",
                    "AWS_SUBNET_ID": "subnet-123",
                    "AWS_KEY_NAME": "example-key",
                    "AWS_INSTANCE_TYPE": "t3.micro",
                    "AWS_OS_FAMILY": "ubuntu",
                    "AWS_OS_VERSION": "26.04",
                    "AWS_ARCH": "amd64",
                    "AWS_TEST_SCENARIO": "pihole-unbound",
                    "AWS_SSH_PRIVATE_KEY_PATH": str(temp_dir / "id_rsa"),
                    "AWS_INVENTORY_FILE": str(temp_dir / "inventory.yml"),
                    "AWS_STATE_FILE": str(temp_dir / "state.json"),
                    "AWS_METADATA_FILE": str(temp_dir / "metadata.json"),
                    "AWS_CLEANUP_STATUS_FILE": str(temp_dir / "cleanup.json"),
                    "AWS_INVENTORY_TEMPLATE": str(inventory_template),
                    "PIHOLE_API_PASSWORD": "not-a-secret",
                    "GITHUB_USER_FOR_SSH_KEY": "ubuntu",
                }
            )

            result = subprocess.run(
                [str(CREATE_SCRIPT)],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            log_lines = aws_log.read_text(encoding="utf-8")
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue((temp_dir / "cleanup.json").exists())
            self.assertFalse((temp_dir / "state.json").exists())
            return result, log_lines, temp_dir

    def test_authorize_ingress_failure_triggers_cleanup(self) -> None:
        _, log_lines, _ = self.run_create_with_failure("authorize-ingress")
        self.assertIn("create-security-group", log_lines)
        self.assertIn("authorize-security-group-ingress", log_lines)
        self.assertIn("delete-security-group", log_lines)
        self.assertIn("sg-1234567890", log_lines)

    def test_instance_wait_failure_terminates_instance_and_cleans_up(self) -> None:
        _, log_lines, _ = self.run_create_with_failure("instance-running-wait")
        self.assertIn("run-instances", log_lines)
        self.assertIn("terminate-instances", log_lines)
        self.assertIn("i-1234567890", log_lines)
        self.assertIn("delete-security-group", log_lines)


if __name__ == "__main__":
    unittest.main()
