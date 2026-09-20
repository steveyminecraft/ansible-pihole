"""Running-install contract for Traefik deploy (existing Pi-hole holds :80/:443)."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEPLOY = ROOT / "roles" / "traefik" / "tasks" / "deploy.yml"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class TraefikDeployRunningInstallTests(unittest.TestCase):
    def test_stops_running_pihole_before_starting_traefik(self) -> None:
        tasks = load_yaml(DEPLOY)
        names = [task.get("name") for task in tasks]
        inspect_idx = names.index(
            "Inspect existing Pi-hole container before Traefik bind"
        )
        stop_idx = names.index(
            "Stop running Pi-hole so Traefik can bind host UI ports"
        )
        start_idx = names.index("Start Traefik service")
        self.assertLess(inspect_idx, stop_idx)
        self.assertLess(stop_idx, start_idx)

    def test_stop_pihole_only_when_a_running_bridge_container_exists(self) -> None:
        tasks = load_yaml(DEPLOY)
        inspect = next(
            task
            for task in tasks
            if task.get("name")
            == "Inspect existing Pi-hole container before Traefik bind"
        )
        stop = next(
            task
            for task in tasks
            if task.get("name")
            == "Stop running Pi-hole so Traefik can bind host UI ports"
        )
        self.assertIn("community.docker.docker_container_info", inspect)
        self.assertEqual(
            stop["community.docker.docker_container"]["state"], "stopped"
        )
        when = stop.get("when") or []
        when_blob = yaml.dump(when)
        self.assertIn("traefik_existing_pihole.exists", when_blob)
        self.assertIn("State.Running", when_blob)
        self.assertIn("pihole_use_host_network", when_blob)


if __name__ == "__main__":
    unittest.main()
