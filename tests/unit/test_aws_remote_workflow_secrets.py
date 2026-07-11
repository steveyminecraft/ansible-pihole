"""Guard AWS remote workflow configuration for infra secrets."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = (
    REPO_ROOT / ".github" / "workflows" / "aws-remote-tests.yml",
    REPO_ROOT / ".github" / "workflows" / "rc-aws-remote-tests.yml",
)

INFRA_SECRETS = (
    "AWS_TEST_REGION",
    "AWS_TEST_ROLE_ARN",
    "AWS_TEST_SUBNET_ID",
)


class AwsRemoteWorkflowSecretsTests(unittest.TestCase):
    def test_infra_config_uses_repository_secrets_not_variables(self) -> None:
        for workflow in WORKFLOWS:
            text = workflow.read_text(encoding="utf-8")
            with self.subTest(workflow=workflow.name):
                for name in INFRA_SECRETS:
                    self.assertIn(
                        f"secrets.{name}",
                        text,
                        f"{workflow.name} should reference secrets.{name}",
                    )
                    self.assertNotIn(
                        f"vars.{name}",
                        text,
                        f"{workflow.name} must not reference vars.{name}",
                    )


if __name__ == "__main__":
    unittest.main()
