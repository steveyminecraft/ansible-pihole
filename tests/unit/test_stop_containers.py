"""Contract tests for stopping stack containers on a drained node."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TASKS = ROOT / "roles" / "stop_containers" / "tasks" / "main.yml"
DEFAULTS = ROOT / "roles" / "stop_containers" / "defaults" / "main.yml"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class StopContainersRoleTests(unittest.TestCase):
    def test_role_stops_running_named_containers(self) -> None:
        tasks = load_yaml(TASKS)
        names = [task.get("name") for task in tasks]
        self.assertIn("Inspect stack containers", names)
        self.assertIn("Stop running stack containers on drained node", names)
        self.assertLess(
            names.index("Inspect stack containers"),
            names.index("Stop running stack containers on drained node"),
        )
        stop = next(
            task
            for task in tasks
            if task.get("name") == "Stop running stack containers on drained node"
        )
        self.assertEqual(
            stop["community.docker.docker_container"]["state"], "stopped"
        )

    def test_defaults_include_pihole_and_traefik(self) -> None:
        defaults = load_yaml(DEFAULTS)
        blob = yaml.dump(defaults["stop_containers_names"])
        self.assertIn("pihole_container_name", blob)
        self.assertIn("traefik_container_name", blob)


if __name__ == "__main__":
    unittest.main()
