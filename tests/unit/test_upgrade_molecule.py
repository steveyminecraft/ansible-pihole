"""The upgrade Molecule scenario installs the previous release on both nodes, then upgrades both."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCENARIO = ROOT / "molecule" / "upgrade"
SCRIPT = ROOT / "scripts" / "upgrade-existing-install.sh"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class UpgradeMoleculeScenarioTests(unittest.TestCase):
    def test_scenario_targets_both_vagrant_nodes(self) -> None:
        cfg = load_yaml(SCENARIO / "molecule.yml")
        self.assertEqual(cfg["driver"]["name"], "vagrant")
        self.assertEqual(cfg["scenario"]["name"], "upgrade")
        names = [platform["name"] for platform in cfg["platforms"]]
        self.assertEqual(names, ["vagrant-pihole-01", "vagrant-pihole-02"])
        inventory = cfg["provisioner"]["inventory"]["links"]["hosts"]
        self.assertIn("vagrant.yml", inventory)

    def test_sequence_installs_then_upgrades_with_a_verify_each_time(self) -> None:
        sequence = load_yaml(SCENARIO / "molecule.yml")["scenario"]["test_sequence"]
        self.assertEqual(
            sequence,
            [
                "dependency",
                "syntax",
                "create",
                "prepare",
                "converge",
                "verify",
                "side_effect",
                "verify",
                "destroy",
            ],
        )

    def test_converge_bootstraps_and_side_effect_upgrades(self) -> None:
        converge = (SCENARIO / "converge.yml").read_text(encoding="utf-8")
        side_effect = (SCENARIO / "side_effect.yml").read_text(encoding="utf-8")
        self.assertIn("upgrade-existing-install.sh", converge)
        self.assertIn("bootstrap", converge)
        self.assertNotIn("\n          - upgrade\n", converge)
        self.assertIn("upgrade-existing-install.sh", side_effect)
        self.assertIn("\n          - upgrade\n", side_effect)
        self.assertNotIn("bootstrap", side_effect)

    def test_phases_only_toggle_traefik(self) -> None:
        baseline = load_yaml(SCENARIO / "baseline.yml")
        cutover = load_yaml(SCENARIO / "cutover.yml")
        self.assertFalse(baseline["traefik_enabled"])
        self.assertFalse(baseline["pihole_proxy_enabled"])
        self.assertNotIn("pihole_ha_mode", baseline)
        self.assertNotIn("pihole_webport_http", baseline)
        self.assertTrue(cutover["traefik_enabled"])
        self.assertFalse(cutover["traefik_tls_enabled"])
        self.assertTrue(cutover["pihole_proxy_dns_enabled"])
        self.assertEqual(cutover["traefik_domain"], "lab.example.com")
        verify = (SCENARIO / "verify.yml").read_text(encoding="utf-8")
        self.assertIn("hosts: all", verify)
        self.assertIn("lab.example.com", verify)
        self.assertIn("0755", verify)
        self.assertIn("0644", verify)

    def test_playbooks_cover_every_host_one_at_a_time(self) -> None:
        for name in ("bootstrap-pihole.yaml", "update-pihole.yaml"):
            document = next(
                yaml.safe_load_all((ROOT / "playbooks" / name).read_text(encoding="utf-8"))
            )
            plays = document if isinstance(document, list) else [document]
            with self.subTest(playbook=name):
                self.assertEqual(plays[0]["hosts"], "all")
                self.assertEqual(plays[0]["serial"], 1)

    def test_ci_requires_the_scenario_file(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn('"molecule/upgrade/molecule.yml"', workflow)

    def test_github_job_upgrades_one_runner_host(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        inventory = load_yaml(SCENARIO / "ci-inventory.yml")
        hosts = inventory["all"]["hosts"]
        self.assertEqual(list(hosts), ["upgrade-ci"])
        self.assertEqual(hosts["upgrade-ci"]["ansible_connection"], "local")
        self.assertFalse(inventory["all"]["vars"]["pihole_ha_mode"])
        self.assertIn("upgrade-existing:", workflow)
        self.assertIn('UPGRADE_FROM_VERSION: "1.9.4"', workflow)
        self.assertIn("./scripts/upgrade-existing-install.sh ci", workflow)

    def test_print_from_version_strips_v_prefix(self) -> None:
        result = subprocess.run(
            [str(SCRIPT), "--print-from-version"],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "UPGRADE_FROM_VERSION": "v1.9.4"},
        )
        self.assertEqual(result.stdout.strip(), "1.9.4")

    def test_plan_lists_both_phases_against_the_molecule_inventory(self) -> None:
        env = {
            **os.environ,
            "UPGRADE_FROM_VERSION": "1.9.4",
            "MOLECULE_INVENTORY_FILE": "/tmp/molecule-upgrade-inventory",
        }
        env.pop("MOLECULE_EPHEMERAL_DIRECTORY", None)
        result = subprocess.run(
            [str(SCRIPT), "--plan"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        lines = result.stdout.splitlines()
        self.assertEqual(
            lines[0],
            "phase=bootstrap version=1.9.4 inventory=/tmp/molecule-upgrade-inventory "
            "playbook=bootstrap-pihole.yaml hosts=all",
        )
        self.assertEqual(
            lines[1],
            "phase=upgrade version=checkout inventory=/tmp/molecule-upgrade-inventory "
            "playbook=update-pihole.yaml hosts=all extra=molecule/upgrade/cutover.yml",
        )

    def test_bootstrap_refuses_without_an_inventory(self) -> None:
        env = {**os.environ, "UPGRADE_FROM_VERSION": "1.9.4"}
        env.pop("MOLECULE_INVENTORY_FILE", None)
        env.pop("MOLECULE_EPHEMERAL_DIRECTORY", None)
        result = subprocess.run(
            [str(SCRIPT), "bootstrap"],
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("MOLECULE_INVENTORY_FILE", result.stderr)
        self.assertNotIn("ansible-galaxy", result.stderr)

    def test_bad_version_is_rejected(self) -> None:
        result = subprocess.run(
            [str(SCRIPT), "--print-from-version"],
            capture_output=True,
            text=True,
            env={**os.environ, "UPGRADE_FROM_VERSION": "latest"},
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("1.9.4", result.stderr)
