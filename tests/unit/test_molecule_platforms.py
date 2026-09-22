"""Guards for Molecule default=Ubuntu and Debian (Pi-OS-adjacent) scenarios."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MOLECULE = ROOT / "molecule"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def effective_vagrantfile(scenario: str) -> str:
    path = MOLECULE / scenario / "Vagrantfile"
    text = path.read_text(encoding="utf-8")
    if "Vagrant.configure" not in text and "../default/Vagrantfile" in text:
        return (MOLECULE / "default" / "Vagrantfile").read_text(encoding="utf-8")
    if "Vagrant.configure" not in text and "../debian/Vagrantfile" in text:
        return (MOLECULE / "debian" / "Vagrantfile").read_text(encoding="utf-8")
    return text


class MoleculePlatformTests(unittest.TestCase):
    def test_ubuntu_named_scenarios_are_removed(self) -> None:
        self.assertFalse((MOLECULE / "ubuntu").exists())
        self.assertFalse((MOLECULE / "ubuntu-26.04" / "molecule.yml").exists())
        self.assertFalse((MOLECULE / "ubuntu-traefik").exists())
        self.assertFalse((MOLECULE / "ubuntu-traefik-http").exists())

    def test_default_scenario_is_ubuntu_ha(self) -> None:
        cfg = load_yaml(MOLECULE / "default" / "molecule.yml")
        self.assertEqual(cfg["scenario"]["name"], "default")
        boxes = {platform["box"] for platform in cfg["platforms"]}
        self.assertEqual(boxes, {"bento/ubuntu-24.04"})
        sequence = cfg["scenario"]["test_sequence"]
        self.assertIn("side_effect", sequence)
        side_effect_index = sequence.index("side_effect")
        verify_indices = [index for index, step in enumerate(sequence) if step == "verify"]
        self.assertGreater(side_effect_index, verify_indices[0])
        self.assertLess(side_effect_index, verify_indices[-1])

    def test_debian_scenario_uses_debian_12(self) -> None:
        cfg = load_yaml(MOLECULE / "debian" / "molecule.yml")
        self.assertEqual(cfg["scenario"]["name"], "debian")
        boxes = {platform["box"] for platform in cfg["platforms"]}
        self.assertEqual(boxes, {"bento/debian-12"})

    def test_debian_libvirt_box_is_bookworm64(self) -> None:
        vagrantfile = (MOLECULE / "debian" / "Vagrantfile").read_text(encoding="utf-8")
        self.assertIn('box_libvirt: "debian/bookworm64"', vagrantfile)
        self.assertIn('box: "bento/debian-12"', vagrantfile)

    def test_nebula_vagrantfile_loads_default(self) -> None:
        vagrantfile = (
            MOLECULE / "nebula-sync-migration" / "Vagrantfile"
        ).read_text(encoding="utf-8")
        self.assertIn("../default/Vagrantfile", vagrantfile)
        self.assertNotIn("../ubuntu/Vagrantfile", vagrantfile)

    def test_debian_traefik_scenarios_use_debian_12(self) -> None:
        for name in ("debian-traefik", "debian-traefik-http"):
            cfg = load_yaml(MOLECULE / name / "molecule.yml")
            with self.subTest(scenario=name):
                self.assertEqual(cfg["scenario"]["name"], name)
                boxes = {platform["box"] for platform in cfg["platforms"]}
                self.assertEqual(boxes, {"bento/debian-12"})

    def test_docker_vagrantfile_loads_default(self) -> None:
        vagrantfile = (MOLECULE / "docker" / "Vagrantfile").read_text(encoding="utf-8")
        self.assertIn("../default/Vagrantfile", vagrantfile)

    def test_vagrant_scenarios_declare_virtualbox_and_libvirt(self) -> None:
        scenarios = (
            "default",
            "debian",
            "debian-traefik",
            "debian-traefik-http",
            "docker",
            "nebula-sync-migration",
            "pihole-no-unbound",
            "upgrade",
        )
        for name in scenarios:
            with self.subTest(scenario=name):
                text = effective_vagrantfile(name)
                self.assertIn('vm.provider "virtualbox"', text)
                self.assertIn('vm.provider "libvirt"', text)
                self.assertIn("192.168.56.", text)
                self.assertIn("192.168.121.", text)

    def test_molecule_test_all_maps_provider_inventory(self) -> None:
        script = (ROOT / "scripts" / "molecule-test-all").read_text(encoding="utf-8")
        self.assertIn("libvirt|kvm", script)
        self.assertIn("vagrant_libvirt.yml", script)
        self.assertIn("vagrant.yml", script)
        self.assertTrue((ROOT / "inventory" / "vagrant.yml").is_file())
        self.assertTrue((ROOT / "inventory" / "vagrant_libvirt.yml").is_file())

    def test_libvirt_inventory_uses_vagrant_machine_key(self) -> None:
        inventory = (ROOT / "inventory" / "vagrant_libvirt.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(".vagrant/machines/", inventory)
        self.assertIn("/libvirt/private_key", inventory)
