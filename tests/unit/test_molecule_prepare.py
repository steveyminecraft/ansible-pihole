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
        self.assertIn("Ubuntu", when)
        self.assertIn("172\\.(1[6-9]|2[0-9]|3[0-1])\\.", when)
        apt_index = names.index("Install Python and DNS tools (Debian/Ubuntu)")
        self.assertLess(names.index(pin["name"]), apt_index)

    def test_debian_prepare_pins_debian_mirrors_on_rfc1918_dns(self) -> None:
        plays = yaml.safe_load(PREPARE.read_text(encoding="utf-8"))
        tasks = plays[0]["tasks"]
        names = [task["name"] for task in tasks]
        self.assertIn("Check whether Debian archive DNS is hijacked to RFC1918", names)
        self.assertIn("Pin public Debian mirrors when lab DNS hijacks them", names)
        pin = next(
            task
            for task in tasks
            if task["name"] == "Pin public Debian mirrors when lab DNS hijacks them"
        )
        self.assertIn("deb.debian.org", pin["ansible.builtin.blockinfile"]["block"])
        when = " ".join(str(item) for item in pin["when"])
        self.assertIn("Debian", when)
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

    def test_alpine_prepare_installs_apk_tools_and_pins_release(self) -> None:
        plays = yaml.safe_load(PREPARE.read_text(encoding="utf-8"))
        tasks = plays[0]["tasks"]
        apk = next(
            task
            for task in tasks
            if task["name"] == "Install Python and DNS tools (Alpine)"
        )
        self.assertEqual(apk["when"], "ansible_facts['os_family'] == 'Alpine'")
        names = apk["community.general.apk"]["name"]
        for package in (
            "python3",
            "py3-requests",
            "py3-packaging",
            "bind-tools",
            "iproute2",
            "sqlite",
            "curl",
            "openssl",
            "bash",
        ):
            self.assertIn(package, names)
        upgrade = next(
            task
            for task in tasks
            if task["name"] == "Upgrade Alpine to the 3.24.4 patch release"
        )
        self.assertTrue(upgrade["community.general.apk"]["upgrade"])
        task_names = [task["name"] for task in tasks]
        self.assertLess(
            task_names.index(upgrade["name"]),
            task_names.index("Reboot Alpine onto the upgraded kernel"),
        )
        self.assertLess(
            task_names.index("Reboot Alpine onto the upgraded kernel"),
            task_names.index("Assert Alpine release is 3.24.4 or newer"),
        )
        release = next(
            task for task in tasks if task["name"] == "Assert Alpine release is 3.24.4 or newer"
        )
        that = " ".join(str(item) for item in release["ansible.builtin.assert"]["that"])
        self.assertIn("version('3.24.4', '>=')", that)
        self.assertIn("alpine-release", release["ansible.builtin.assert"]["fail_msg"])

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
