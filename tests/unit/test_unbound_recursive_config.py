"""Unbound must recurse (Pi-hole upstream), not inherit mvance DNS-over-TLS forwards."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = ROOT / "roles" / "unbound" / "defaults" / "main.yml"
TEMPLATE = ROOT / "roles" / "unbound" / "templates" / "unbound.conf.j2"
VERIFY = ROOT / "roles" / "unbound" / "tasks" / "verify.yml"


class UnboundRecursiveConfigTests(unittest.TestCase):
    def test_template_does_not_include_image_dot_forwards(self) -> None:
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assertNotIn(
            "include: /opt/unbound/etc/unbound/forward-records.conf",
            text,
            "mvance forward-records.conf forwards to 1.1.1.1@853; "
            "DoT SERVFAILs immediately when TLS cannot complete",
        )
        self.assertIn("unbound_forward_addrs", text)
        self.assertIn('module-config: "iterator"', text)

    def test_vagrant_inventory_forwards_when_roots_are_intercepted(self) -> None:
        for name in ("vagrant.yml", "vagrant_libvirt.yml"):
            text = (ROOT / "inventory" / name).read_text(encoding="utf-8")
            self.assertIn("unbound_forward_addrs:", text, name)
            self.assertIn("1.1.1.1@53", text, name)

    def test_container_chroot_is_disabled(self) -> None:
        defaults = yaml.safe_load(DEFAULTS.read_text(encoding="utf-8"))
        chroot = defaults.get("unbound_chroot")
        self.assertTrue(
            chroot in (None, "", "/"),
            f"container chroot {chroot!r} hides /etc/ssl and root.key paths",
        )
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("unbound_chroot", text)

    def test_verify_requires_noerror_a_record(self) -> None:
        text = VERIFY.read_text(encoding="utf-8")
        self.assertIn("status: NOERROR", text)
        self.assertIn("ANSWER SECTION:", text)
        self.assertNotIn("+short", text)
        self.assertIn("nsenter", text)
        self.assertIn("127.0.0.1", text)
