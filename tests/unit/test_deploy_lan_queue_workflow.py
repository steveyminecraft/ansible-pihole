"""Guard the LAN deploy-queue workflow contract."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-lan-queue.yml"


class DeployLanQueueWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_file_exists(self) -> None:
        self.assertTrue(WORKFLOW.is_file())

    def test_does_not_ssh_or_run_ansible(self) -> None:
        self.assertNotIn("ansible-playbook", self.text)
        self.assertNotRegex(self.text, r"(?m)^\s+ssh\s")
        self.assertNotIn("appleboy/ssh-action", self.text)

    def test_uses_shared_queue_secrets_not_public_vars(self) -> None:
        self.assertIn("secrets.AWS_DEPLOY_QUEUE_ROLE_ARN", self.text)
        self.assertIn("secrets.AWS_DEPLOY_QUEUE_URL", self.text)
        self.assertIn("secrets.AWS_REGION", self.text)
        self.assertNotIn("vars.AWS_DEPLOY_QUEUE_ROLE_ARN", self.text)
        self.assertNotIn("vars.AWS_DEPLOY_QUEUE_URL", self.text)
        self.assertNotIn("vars.AWS_REGION", self.text)
        self.assertNotIn("secrets.AWS_TEST_ROLE_ARN", self.text)
        self.assertIn("aws sqs send-message", self.text)

    def test_enqueues_after_successful_master_ci(self) -> None:
        self.assertIn("CI - Ansible-Pihole Checks", self.text)
        self.assertIn("workflow_run", self.text)
        self.assertIn("head_branch == 'master'", self.text)
        self.assertIn("id-token: write", self.text)

    def test_actions_display_name_is_release_alert(self) -> None:
        self.assertRegex(self.text, r"(?m)^name: Release-Alert$")

    def test_does_not_use_release_event_trigger(self) -> None:
        """OIDC send role is master/main refs only; release events run on tag refs."""
        self.assertNotRegex(self.text, r"(?m)^\s+release:")

    def test_skips_master_ci_unless_sha_is_latest_published_release(self) -> None:
        self.assertIn("releases/latest", self.text)
        self.assertIn("enqueue=false", self.text)
        self.assertIn("steps.target.outputs.enqueue == 'true'", self.text)

    def test_message_includes_release_version_and_keeps_master_ref(self) -> None:
        self.assertIn("version:$version", self.text)
        self.assertIn('ref="refs/heads/${WORKFLOW_BRANCH}"', self.text)

    def test_workflow_run_fields_are_passed_via_env_not_shell_interpolation(self) -> None:
        """CodeQL actions/code-injection: do not expand workflow_run into run: scripts."""
        self.assertNotIn(
            'SHA="${{ github.event.workflow_run.head_sha }}"',
            self.text,
        )
        self.assertNotIn(
            'REF="refs/heads/${{ github.event.workflow_run.head_branch }}"',
            self.text,
        )
        self.assertIn(
            "WORKFLOW_SHA: ${{ github.event.workflow_run.head_sha }}",
            self.text,
        )
        self.assertIn(
            "WORKFLOW_BRANCH: ${{ github.event.workflow_run.head_branch }}",
            self.text,
        )


if __name__ == "__main__":
    unittest.main()
