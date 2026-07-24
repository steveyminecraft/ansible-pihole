"""Contract and Jinja selection tests for Pi-hole Unbound DNS target."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[2]
UNBOUND_TASKS = ROOT / "roles" / "pihole" / "tasks" / "unbound.yml"


def _ansible_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes")


def _render_target(**variables: object) -> str:
    """Evaluate the same selection expression used by unbound.yml."""
    env = Environment(undefined=StrictUndefined)
    env.filters["bool"] = _ansible_bool
    template = env.from_string(
        """
{%- set use_ip = (
  (pihole_unbound_container_ipv4 | default('') | length > 0)
  and (
    (not (pihole_docker_manage_iptables | default(true) | bool))
    or (pihole_docker_dns | default([]) | length > 0)
    or (pihole_override_container_resolver | default(false) | bool)
  )
) -%}
{{- pihole_unbound_container_ipv4 if use_ip else (unbound_container_name | default('unbound')) -}}
"""
    )
    return template.render(**variables)


class PiholeUnboundDnsTargetTests(unittest.TestCase):
    def test_unbound_tasks_prefer_ip_when_embedded_dns_unavailable(self) -> None:
        tasks = yaml.safe_load(UNBOUND_TASKS.read_text(encoding="utf-8"))
        target_task = next(
            task for task in tasks if task.get("name") == "Set Pi-hole Unbound DNS target"
        )
        expression = target_task["ansible.builtin.set_fact"]["pihole_unbound_dns_target"]
        self.assertIn("pihole_unbound_container_ipv4", expression)
        self.assertIn("pihole_docker_manage_iptables", expression)
        self.assertIn("pihole_docker_dns", expression)

        verify_task = next(
            task
            for task in tasks
            if task.get("name") == "Verify Pi-hole can resolve Unbound via Docker embedded DNS"
        )
        when_clause = verify_task.get("when")
        self.assertIsInstance(when_clause, list)
        self.assertTrue(
            any("pihole_unbound_dns_target ==" in str(item) for item in when_clause),
            msg="embedded DNS verify must run only when target is the Docker service name",
        )

    def test_production_defaults_keep_docker_service_name(self) -> None:
        self.assertEqual(
            _render_target(
                pihole_unbound_container_ipv4="172.18.0.2",
                pihole_docker_manage_iptables=True,
                pihole_docker_dns=[],
                pihole_override_container_resolver=False,
                unbound_container_name="unbound",
            ),
            "unbound",
        )

    def test_vagrant_iptables_false_with_custom_dns_uses_bridge_ip(self) -> None:
        self.assertEqual(
            _render_target(
                pihole_unbound_container_ipv4="172.18.0.2",
                pihole_docker_manage_iptables=False,
                pihole_docker_dns=["1.1.1.1", "8.8.8.8"],
                pihole_override_container_resolver=False,
                unbound_container_name="unbound",
            ),
            "172.18.0.2",
        )

    def test_explicit_resolver_override_uses_bridge_ip(self) -> None:
        self.assertEqual(
            _render_target(
                pihole_unbound_container_ipv4="172.18.0.2",
                pihole_docker_manage_iptables=True,
                pihole_docker_dns=[],
                pihole_override_container_resolver=True,
                unbound_container_name="unbound",
            ),
            "172.18.0.2",
        )


if __name__ == "__main__":
    unittest.main()
