"""Unit tests for scripts/validate-inventory.py."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate-inventory.py"
REPO = SCRIPT.parents[1]
EXAMPLE_HA = REPO / "tests/remote/inventories/example-lab-ha.yml"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_inventory", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidateInventoryHelpersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()

    def test_unresolved_secret_rejects_placeholders(self) -> None:
        self.assertTrue(self.mod.is_unresolved_secret("CHANGE_ME"))
        self.assertTrue(self.mod.is_unresolved_secret("REPLACE_WITH_ANSIBLE_VAULT"))

    def test_unresolved_secret_accepts_vault_jinja(self) -> None:
        self.assertFalse(self.mod.is_unresolved_secret("{{ vault_pihole_api_password }}"))

    def test_structure_only_passes_example_lab_ha(self) -> None:
        errors = self.mod.validate_inventory(EXAMPLE_HA, structure_only=True)
        self.assertEqual(errors, [])

    def test_secret_check_fails_example_lab_ha_placeholders(self) -> None:
        errors = self.mod.validate_inventory(EXAMPLE_HA, structure_only=False)
        self.assertTrue(any("FTLCONF_webserver_api_password" in err for err in errors))

    def test_ha_requires_controller_group(self) -> None:
        inventory = {
            "_meta": {
                "hostvars": {
                    "a": {
                        "ansible_host": "10.0.0.1",
                        "priority": 110,
                        "keepalive_role": "MASTER",
                        "pihole_compose_dir": "/opt/pihole",
                        "pihole_ha_mode": True,
                        "pihole_vip_ipv4": "10.0.0.53/24",
                    },
                    "b": {
                        "ansible_host": "10.0.0.2",
                        "priority": 100,
                        "keepalive_role": "BACKUP",
                        "pihole_compose_dir": "/opt/pihole",
                        "pihole_ha_mode": True,
                        "pihole_vip_ipv4": "10.0.0.53/24",
                    },
                }
            }
        }
        errors: list[str] = []
        self.mod.validate_structure(inventory, errors)
        self.assertTrue(any("nebula_sync_controller" in err for err in errors))


class ValidateInventoryCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()

    def test_main_returns_nonzero_on_failure(self) -> None:
        with mock.patch.object(
            self.mod,
            "validate_inventory",
            return_value=["missing vip"],
        ):
            code = self.mod.main([str(EXAMPLE_HA)])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
