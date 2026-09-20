"""systemd-resolved is Ubuntu-typical; skip when the config file is absent."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEPLOYPI = ROOT / "roles" / "pihole" / "tasks" / "deploypi.yml"


class PiholeResolvedTests(unittest.TestCase):
    def test_resolved_block_requires_config_file(self) -> None:
        tasks = yaml.safe_load(DEPLOYPI.read_text(encoding="utf-8"))
        names = [task["name"] for task in tasks]
        self.assertIn("Check whether systemd-resolved config exists", names)
        configure = next(
            task
            for task in tasks
            if task["name"] == "Configure systemd-resolved for Pi-hole (Debian family)"
        )
        when = " ".join(str(item) for item in configure["when"])
        self.assertIn("pihole_resolved_conf_stat.stat.exists", when)
