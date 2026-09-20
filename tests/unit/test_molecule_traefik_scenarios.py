"""Guards for Traefik-on Molecule scenarios (HTTP and HTTPS)."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class MoleculeTraefikScenarioTests(unittest.TestCase):
    def test_https_scenario_enables_supplied_tls(self) -> None:
        cfg = load_yaml(ROOT / "molecule" / "debian-traefik" / "molecule.yml")
        vars_all = load_yaml(
            ROOT / "molecule" / "debian-traefik" / "group_vars" / "all.yml"
        )
        self.assertEqual(cfg["scenario"]["name"], "debian-traefik")
        self.assertTrue(vars_all["traefik_enabled"])
        self.assertTrue(vars_all["traefik_tls_enabled"])
        self.assertEqual(vars_all["traefik_tls_mode"], "supplied")
        self.assertTrue(vars_all["traefik_tls_remote_src"])
        self.assertTrue(vars_all["nebula_sync_primary_url"].startswith("https://"))

    def test_http_scenario_disables_tls(self) -> None:
        cfg = load_yaml(ROOT / "molecule" / "debian-traefik-http" / "molecule.yml")
        vars_all = load_yaml(
            ROOT / "molecule" / "debian-traefik-http" / "group_vars" / "all.yml"
        )
        self.assertEqual(cfg["scenario"]["name"], "debian-traefik-http")
        self.assertTrue(vars_all["traefik_enabled"])
        self.assertFalse(vars_all["traefik_tls_enabled"])
        self.assertNotIn("traefik_tls_mode", vars_all)
