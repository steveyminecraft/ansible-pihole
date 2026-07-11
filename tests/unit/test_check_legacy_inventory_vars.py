"""Unit tests for scripts/check-legacy-inventory-vars.py."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check-legacy-inventory-vars.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_legacy_inventory_vars", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CheckLegacyInventoryVarsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()

    def test_scan_file_flags_legacy_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "lab.yml"
            inventory.write_text(
                "all:\n  vars:\n    webport_http: '8080'\n    pihole_dir_loc: /opt/pihole\n",
                encoding="utf-8",
            )
            findings = self.mod.scan_file(inventory)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].key, "all.vars.webport_http")
            self.assertEqual(findings[0].replacement, "pihole_webport_http")

    def test_main_warn_only_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "lab.yml"
            inventory.write_text("all:\n  vars:\n    dir_loc: /opt/pihole\n", encoding="utf-8")
            rc = self.mod.main([str(inventory)])
            self.assertEqual(rc, 0)

    def test_main_fail_on_find_exits_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "lab.yml"
            inventory.write_text("all:\n  vars:\n    dir_loc: /opt/pihole\n", encoding="utf-8")
            rc = self.mod.main([str(inventory), "--fail-on-find"])
            self.assertEqual(rc, 1)

    def test_scan_file_clean_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inventory = Path(tmp) / "lab.yml"
            inventory.write_text(
                "all:\n  vars:\n    pihole_webport_http: '80'\n",
                encoding="utf-8",
            )
            self.assertEqual(self.mod.scan_file(inventory), [])


if __name__ == "__main__":
    unittest.main()
