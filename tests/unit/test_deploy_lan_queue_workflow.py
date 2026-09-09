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

    def test_uses_shared_queue_variables_not_github_build_secret(self) -> None:
        self.assertIn("vars.AWS_DEPLOY_QUEUE_ROLE_ARN", self.text)
        self.assertIn("vars.AWS_DEPLOY_QUEUE_URL", self.text)
        self.assertIn("vars.AWS_REGION", self.text)
        self.assertNotIn("secrets.AWS_TEST_ROLE_ARN", self.text)
        self.assertIn("aws sqs send-message", self.text)

    def test_enqueues_after_successful_master_ci(self) -> None:
        self.assertIn("CI - Ansible-Pihole Checks", self.text)
        self.assertIn("workflow_run", self.text)
        self.assertIn("head_branch == 'master'", self.text)
        self.assertIn("id-token: write", self.text)


if __name__ == "__main__":
    unittest.main()
