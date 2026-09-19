"""Guards for the Traefik-enabled Molecule scenario and HTTP/HTTPS verify."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "molecule" / "ubuntu-traefik"
PROXY_VERIFY = ROOT / "molecule" / "common" / "verify" / "proxy.yml"


class MoleculeTraefikScenarioTests(unittest.TestCase):
    def test_ubuntu_traefik_scenario_enables_supplied_tls(self) -> None:
        molecule = yaml.safe_load((SCENARIO / "molecule.yml").read_text(encoding="utf-8"))
        extra = yaml.safe_load((SCENARIO / "group_vars" / "all.yml").read_text(encoding="utf-8"))
        self.assertEqual(molecule["scenario"]["name"], "ubuntu-traefik")
        self.assertEqual(
            molecule["provisioner"]["inventory"]["links"]["group_vars"],
            "group_vars",
        )
        self.assertTrue(extra["traefik_enabled"])
        self.assertTrue(extra["traefik_tls_enabled"])
        self.assertEqual(extra["traefik_tls_mode"], "supplied")
        self.assertTrue(extra["traefik_tls_remote_src"])
        self.assertTrue(str(extra["traefik_tls_cert_src"]).endswith("tls.crt"))
        self.assertTrue(str(extra["traefik_tls_key_src"]).endswith("tls.key"))

    def test_proxy_verify_covers_http_and_https_both_modes(self) -> None:
        text = PROXY_VERIFY.read_text(encoding="utf-8")
        self.assertIn("Check HTTP to HTTPS redirect for Pi-hole", text)
        self.assertIn("Check HTTPS reaches Pi-hole through Traefik", text)
        self.assertIn("Check Pi-hole HTTP without Traefik", text)
        self.assertIn("Check Pi-hole HTTPS without Traefik", text)
        self.assertIn("Check Pi-hole HTTP through Traefik", text)
        self.assertIn("molecule_verify_proxy_dns", text)
