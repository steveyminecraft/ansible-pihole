"""Retry ansible-galaxy collection install on Galaxy RST flakes."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts" / "ansible-galaxy-collection-install.sh"
GALAXY_PUBLISH = ROOT / ".github" / "workflows" / "galaxy-publish.yml"
INSTALL_COLLECTIONS = ROOT / "scripts" / "install-ansible-collections.sh"

FAKE_GALAXY = """#!/usr/bin/env bash
set -euo pipefail
state="${GALAXY_FAKE_STATE_DIR:?}"
count_file="${state}/count"
fail_until="${GALAXY_FAKE_FAIL_UNTIL:-0}"
count=0
if [[ -f "${count_file}" ]]; then
  count="$(cat "${count_file}")"
fi
count=$((count + 1))
printf '%s\\n' "${count}" > "${count_file}"
printf '%s\\n' "$*" >> "${state}/args"
if (( count <= fail_until )); then
  echo "[ERROR]: Connection reset by peer" >&2
  exit 1
fi
exit 0
"""


class AnsibleGalaxyCollectionInstallTests(unittest.TestCase):
    def test_helper_exists_and_is_executable(self) -> None:
        self.assertTrue(HELPER.is_file(), f"missing {HELPER}")
        self.assertTrue(
            os.access(HELPER, os.X_OK),
            f"{HELPER} must be executable",
        )

    def test_retries_then_succeeds(self) -> None:
        result, count, args = self._run_helper(fail_until=2, max_attempts=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(count, 3)
        self.assertIn("collection install artifact.tar.gz -p collections --force --no-cache", args)

    def test_gives_up_after_max_attempts(self) -> None:
        result, count, _args = self._run_helper(fail_until=9, max_attempts=3)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(count, 3)
        self.assertIn("failed after 3 attempts", result.stderr)

    def test_rejects_invalid_max_attempts(self) -> None:
        env = os.environ.copy()
        env["GALAXY_INSTALL_MAX_ATTEMPTS"] = "0"
        result = subprocess.run(
            [str(HELPER), "artifact.tar.gz"],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("positive integer", result.stderr)

    def test_galaxy_publish_consumer_install_uses_helper(self) -> None:
        text = GALAXY_PUBLISH.read_text(encoding="utf-8")
        self.assertIn("scripts/ansible-galaxy-collection-install.sh", text)
        self.assertNotIn(
            'ansible-galaxy collection install "${artifact}" -p collections --force --no-cache',
            text,
        )

    def test_install_ansible_collections_uses_helper(self) -> None:
        text = INSTALL_COLLECTIONS.read_text(encoding="utf-8")
        self.assertIn("ansible-galaxy-collection-install.sh", text)
        self.assertNotIn(
            'ansible-galaxy collection install "${artifact}" -p "$COL" --force --no-cache',
            text,
        )
        self.assertNotIn(
            'ansible-galaxy collection install -r "$ROOT/collections/requirements.yml"',
            text,
        )

    def _run_helper(
        self, *, fail_until: int, max_attempts: int
    ) -> tuple[subprocess.CompletedProcess[str], int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir()
            fake = bin_dir / "ansible-galaxy"
            fake.write_text(FAKE_GALAXY, encoding="utf-8")
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            state_dir = tmp_path / "state"
            state_dir.mkdir()
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
            env["GALAXY_FAKE_STATE_DIR"] = str(state_dir)
            env["GALAXY_FAKE_FAIL_UNTIL"] = str(fail_until)
            env["GALAXY_INSTALL_MAX_ATTEMPTS"] = str(max_attempts)
            env["GALAXY_INSTALL_RETRY_DELAY_SECONDS"] = "0"
            result = subprocess.run(
                [
                    str(HELPER),
                    "artifact.tar.gz",
                    "-p",
                    "collections",
                    "--force",
                    "--no-cache",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            count_file = state_dir / "count"
            count = int(count_file.read_text(encoding="utf-8")) if count_file.exists() else 0
            args_file = state_dir / "args"
            args = args_file.read_text(encoding="utf-8") if args_file.exists() else ""
            return result, count, args


if __name__ == "__main__":
    unittest.main()
