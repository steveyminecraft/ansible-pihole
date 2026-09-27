"""Rendering tests for keepalived.conf (production and Vagrant branches)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "roles" / "keepalived" / "templates" / "keepalived.j2"
DEFAULTS = ROOT / "roles" / "keepalived" / "defaults" / "main.yml"


def instance_block(rendered: str, name: str) -> str:
    match = re.search(r"vrrp_instance " + re.escape(name) + r" \{(.*?)\n\}", rendered, re.S)
    if match is None:
        raise AssertionError(f"{name} not rendered")
    return match.group(1)


class KeepalivedConfigTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        env = Environment(
            loader=FileSystemLoader(TEMPLATE.parent),
            undefined=StrictUndefined,
            trim_blocks=True,
        )
        env.filters["bool"] = lambda value: (
            value if isinstance(value, bool) else str(value).lower() in ("true", "1", "yes")
        )
        cls.env = env

    def _render(self, **overrides: object) -> str:
        variables = yaml.safe_load(DEFAULTS.read_text(encoding="utf-8")) or {}
        variables.update(
            {
                "ansible_user": "service",
                "ansible_facts": {
                    "default_ipv4": {"interface": "eth0", "address": "172.16.7.25"},
                    "default_ipv6": {"interface": "eth0"},
                },
                "keepalive_role": "MASTER",
                "priority": 110,
                "keepalived_peer_list": ["172.16.7.30"],
                "pihole_vip_ipv4": "172.16.7.35/24",
                "pihole_vip_ipv6": "fd00::10/64",
                "vagrant_env": False,
            }
        )
        variables.update(overrides)
        return self.env.get_template(TEMPLATE.name).render(**variables)

    def test_production_tracks_script_only_on_sync_group(self) -> None:
        rendered = self._render()
        self.assertIn("vrrp_sync_group PIHOLE", rendered)
        self.assertEqual(rendered.count("track_script"), 1)
        self.assertNotIn("track_script", instance_block(rendered, "PIHOLE-IPv6"))
        self.assertIn("weight -50", rendered)

    def test_production_unicast_peers_are_plain_addresses(self) -> None:
        ipv4 = instance_block(self._render(), "PIHOLE-IPv4")
        self.assertIn("unicast_src_ip 172.16.7.25", ipv4)
        self.assertRegex(ipv4, r"unicast_peer \{\s*172\.16\.7\.30\s*\}")
        self.assertNotIn("[", ipv4)

    def test_production_master_damps_failback_on_ipv6_only(self) -> None:
        rendered = self._render()
        self.assertNotIn("preempt_delay", instance_block(rendered, "PIHOLE-IPv4"))
        self.assertIn("preempt_delay 30", instance_block(rendered, "PIHOLE-IPv6"))

    def test_production_backup_has_no_preempt_delay(self) -> None:
        rendered = self._render(keepalive_role="BACKUP", priority=100)
        self.assertNotIn("preempt_delay", rendered)

    def test_vagrant_tracks_script_on_ipv4_instance(self) -> None:
        rendered = self._render(vagrant_env=True, keepalive_role="BACKUP", priority=100)
        self.assertNotIn("vrrp_sync_group", rendered)
        self.assertNotIn("PIHOLE-IPv6", rendered)
        ipv4 = instance_block(rendered, "PIHOLE-IPv4")
        self.assertIn("track_script", ipv4)
        self.assertIn("preempt_delay 5", ipv4)


if __name__ == "__main__":
    unittest.main()
