"""Unbound ACL must allow host-side Docker-bridge queries from RFC1918 sources."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = ROOT / "roles" / "unbound" / "defaults" / "main.yml"
TEMPLATE = ROOT / "roles" / "unbound" / "templates" / "unbound.conf.j2"


def load_defaults() -> dict:
    return yaml.safe_load(DEFAULTS.read_text(encoding="utf-8"))


class UnboundAccessControlTests(unittest.TestCase):
    def test_default_acl_allows_loopback_and_rfc1918(self) -> None:
        """Host dig @container_ip comes from Vagrant/LAN, not 172.18.0.0/16."""
        acls = load_defaults()["unbound_access_control"]
        joined = " ".join(acls)
        for cidr in (
            "127.0.0.1/32",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
        ):
            self.assertIn(cidr, joined, f"missing {cidr} allow in {acls!r}")
            self.assertTrue(
                any(cidr in entry and "allow" in entry for entry in acls),
                cidr,
            )

    def test_acl_is_not_docker_18_only(self) -> None:
        acls = load_defaults()["unbound_access_control"]
        self.assertFalse(
            acls == ["172.18.0.0/16 allow"],
            "narrow 172.18/16 ACL refuses Vagrant host queries to the container IP",
        )

    def test_template_documents_rfc1918_acl_default(self) -> None:
        text = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("172.16.0.0/12 allow", text)
        self.assertIn("192.168.0.0/16 allow", text)
