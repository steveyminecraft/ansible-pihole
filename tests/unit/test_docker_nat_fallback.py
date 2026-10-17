"""Container egress NAT must apply on Vagrant Debian, not only EL."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKER_MAIN = ROOT / "roles" / "docker" / "tasks" / "main.yml"
DOCKER_DAEMON = ROOT / "roles" / "docker" / "tasks" / "daemon.yml"
NAT_FALLBACK = ROOT / "roles" / "docker" / "tasks" / "redhat_nat_fallback.yml"
UNBOUND_DEPLOY = ROOT / "roles" / "unbound" / "tasks" / "deploy.yml"
UNBOUND_DEFAULTS = ROOT / "roles" / "unbound" / "defaults" / "main.yml"


class DockerNatFallbackTests(unittest.TestCase):
    def test_nat_fallback_is_not_redhat_only(self) -> None:
        text = DOCKER_MAIN.read_text(encoding="utf-8")
        self.assertIn("redhat_nat_fallback.yml", text)
        self.assertNotIn(
            "os_family'] == 'RedHat'",
            text[text.index("NAT fallback") :],
            "Ubuntu Vagrant also has docker_manage_iptables false",
        )

    def test_nat_subnet_list_always_covers_docker_rfc1918(self) -> None:
        text = NAT_FALLBACK.read_text(encoding="utf-8")
        self.assertIn("172.16.0.0/12", text)
        self.assertIn("unique", text)
        self.assertIn("ansible_docker_filter", text)
        self.assertIn("FORWARD ACCEPT", text)
        self.assertIn("firewall-cmd", text)
        self.assertIn("trusted", text)

    def test_debian_daemon_json_honors_iptables_flag(self) -> None:
        text = DOCKER_DAEMON.read_text(encoding="utf-8")
        debian = text.split("Configure Docker without explicit IPv6")[-1]
        self.assertIn("'iptables'", debian)

    def test_unbound_refresh_nat_after_compose(self) -> None:
        text = UNBOUND_DEPLOY.read_text(encoding="utf-8")
        self.assertIn("redhat_nat_fallback.yml", text)
        self.assertIn("flush_handlers", text)

    def test_unbound_defaults_disable_ip6_with_docker(self) -> None:
        text = UNBOUND_DEFAULTS.read_text(encoding="utf-8")
        self.assertRegex(text, r"unbound_do_ip6:\s+false")
