"""Guards for shared Molecule prepare (lab DNS hijack of Ubuntu archives)."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
PREPARE = ROOT / "molecule" / "common" / "prepare.yml"


class MoleculePrepareTests(unittest.TestCase):
    def test_debian_prepare_pins_ubuntu_mirrors_on_rfc1918_dns(self) -> None:
        plays = yaml.safe_load(PREPARE.read_text(encoding="utf-8"))
        tasks = plays[0]["tasks"]
        names = [task["name"] for task in tasks]
        self.assertIn("Check whether Ubuntu archive DNS is hijacked to RFC1918", names)
        self.assertIn("Pin public Ubuntu mirrors when lab DNS hijacks them", names)
        pin = next(
            task
            for task in tasks
            if task["name"] == "Pin public Ubuntu mirrors when lab DNS hijacks them"
        )
        self.assertIn("91.189.91.81", pin["ansible.builtin.blockinfile"]["block"])
        when = " ".join(str(item) for item in pin["when"])
        self.assertIn("172\\.(1[6-9]|2[0-9]|3[0-1])\\.", when)
        apt_index = names.index("Install Python and DNS tools (Debian/Ubuntu)")
        self.assertLess(names.index(pin["name"]), apt_index)

    def test_debian_prepare_installs_curl_before_verify(self) -> None:
        plays = yaml.safe_load(PREPARE.read_text(encoding="utf-8"))
        apt = next(
            task
            for task in plays[0]["tasks"]
            if task["name"] == "Install Python and DNS tools (Debian/Ubuntu)"
        )
        self.assertIn("curl", apt["ansible.builtin.apt"]["name"])

    def test_prepare_mints_supplied_traefik_certs_when_enabled(self) -> None:
        plays = yaml.safe_load(PREPARE.read_text(encoding="utf-8"))
        names = [task["name"] for task in plays[0]["tasks"]]
        self.assertIn("Generate lab Traefik certificate", names)
        cert = next(
            task
            for task in plays[0]["tasks"]
            if task["name"] == "Generate lab Traefik certificate"
        )
        when = " ".join(str(item) for item in cert["when"])
        self.assertIn("traefik_enabled", when)
        self.assertIn("supplied", when)
