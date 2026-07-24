"""Contract tests for keepalived Pi-hole health script template."""

from __future__ import annotations

import unittest
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "roles" / "keepalived" / "templates" / "check_pihole.sh.j2"


class KeepalivedHealthScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        env = Environment(
            loader=FileSystemLoader(TEMPLATE.parent),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )
        env.filters["bool"] = lambda value: (
            value if isinstance(value, bool) else str(value).lower() in ("true", "1", "yes")
        )
        cls.env = env

    def _render(self, **overrides: object) -> str:
        variables = {
            "ansible_user": "vagrant",
            "pihole_container_name": "pihole",
            "pihole_verify_qname": "cloudflare.com",
            "pihole_enable_unbound": True,
            "unbound_container_name": "unbound",
            "unbound_port": 5335,
            "pihole_unbound_dns_target": "unbound",
        }
        variables.update(overrides)
        return self.env.get_template(TEMPLATE.name).render(**variables)

    def test_unbound_probe_discovers_container_ip_at_runtime(self) -> None:
        rendered = self._render()
        self.assertIn("UNBOUND_CHECK_TARGET=", rendered)
        self.assertIn("NetworkSettings.Networks", rendered)
        self.assertIn("@${UNBOUND_CHECK_TARGET}", rendered)
        self.assertIn("UNBOUND_DNS_TARGET", rendered)

    def test_unbound_probe_omitted_when_unbound_disabled(self) -> None:
        rendered = self._render(pihole_enable_unbound=False)
        self.assertNotIn("UNBOUND_CHECK_TARGET=", rendered)
        self.assertNotIn("UNBOUND_CONTAINER", rendered)


if __name__ == "__main__":
    unittest.main()
