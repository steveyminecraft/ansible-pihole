"""Guard AWS remote workflow configuration for infra secrets."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AWS_REMOTE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "aws-remote-tests.yml"
RC_AWS_REMOTE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "rc-aws-remote-tests.yml"
WORKFLOWS = (AWS_REMOTE_WORKFLOW, RC_AWS_REMOTE_WORKFLOW)

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

    def test_aws_region_is_not_passed_through_job_outputs(self) -> None:
        """Secrets in job outputs are redacted to empty by the Actions runner."""
        text = AWS_REMOTE_WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn(
            "aws_region: ${{ steps.matrix.outputs.aws_region }}",
            text,
        )
        self.assertNotIn(
            "AWS_REGION: ${{ needs.prepare-matrix.outputs.aws_region }}",
            text,
        )
        self.assertIn(
            "AWS_REGION: ${{ github.event.inputs.aws_region || secrets.AWS_TEST_REGION }}",
            text,
        )

    def test_cleanup_skips_when_checkout_did_not_run(self) -> None:
        text = AWS_REMOTE_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Repository checkout did not run; skipping destroy.", text)
        self.assertIn(
            "Repository checkout did not run; skipping cleanup verification.",
            text,
        )


if __name__ == "__main__":
    unittest.main()
