"""Unbound root.hints must not fail the update when internic is unreachable."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / "roles" / "unbound" / "tasks" / "prep.yml"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class UnboundRootHintsTests(unittest.TestCase):
    def test_download_keeps_existing_root_hints_on_failure(self) -> None:
        tasks = load_yaml(PREP)
        names = [task.get("name") for task in tasks]
        self.assertIn("Stat existing Unbound root.hints", names)
        self.assertIn("Download root.hints for Unbound", names)
        self.assertLess(
            names.index("Stat existing Unbound root.hints"),
            names.index("Download root.hints for Unbound"),
        )

        download = next(
            task for task in tasks if task.get("name") == "Download root.hints for Unbound"
        )
        self.assertEqual(
            download["ansible.builtin.get_url"]["dest"],
            "{{ unbound_root_hints_host_path }}",
        )
        failed_when = yaml.dump(download.get("failed_when"))
        self.assertIn("unbound_root_hints_download is failed", failed_when)
        self.assertIn("unbound_root_hints_stat.stat.exists", failed_when)

    def test_missing_root_hints_still_fails_closed(self) -> None:
        download = next(
            task
            for task in load_yaml(PREP)
            if task.get("name") == "Download root.hints for Unbound"
        )
        failed_when = yaml.dump(download.get("failed_when"))
        self.assertIn("not", failed_when)
        self.assertIn("exists", failed_when)


if __name__ == "__main__":
    unittest.main()
