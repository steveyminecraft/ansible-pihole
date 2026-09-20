"""Playbook contract and template tests for rolling HA update paths."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


ROOT = Path(__file__).resolve().parents[2]
UPDATE_PIHOLE = ROOT / "playbooks" / "update-pihole.yaml"
ROLLING_PLAYBOOKS = (
    ROOT / "playbooks" / "update-pihole.yaml",
    ROOT / "playbooks" / "bootstrap-pihole.yaml",
    ROOT / "playbooks" / "keepalived.yaml",
)
UBUNTU_MOLECULE = ROOT / "molecule" / "default" / "molecule.yml"
COMPOSE_TEMPLATE = ROOT / "roles" / "pihole" / "templates" / "docker-compose.yml.j2"
PIHOLE_DEFAULTS = ROOT / "roles" / "pihole" / "defaults" / "main.yml"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class RollingHaPlaybookContractTests(unittest.TestCase):
    def test_rolling_ha_playbooks_use_serial_one(self) -> None:
        for path in ROLLING_PLAYBOOKS:
            with self.subTest(playbook=path.name):
                doc = load_yaml(path)
                self.assertEqual(doc[0].get("serial"), 1)

    def test_update_and_bootstrap_stop_containers_after_drain_before_updates(
        self,
    ) -> None:
        for path in (
            ROOT / "playbooks" / "update-pihole.yaml",
            ROOT / "playbooks" / "bootstrap-pihole.yaml",
        ):
            with self.subTest(playbook=path.name):
                roles = [role["role"] for role in load_yaml(path)[0]["roles"]]
                drain = roles.index("steveyminecraft.pihole.stop_keepalived")
                stop = roles.index("steveyminecraft.pihole.stop_containers")
                updates = roles.index("steveyminecraft.pihole.updates")
                self.assertLess(drain, stop)
                self.assertLess(stop, updates)

    def test_update_pihole_ensures_unbound_before_pihole(self) -> None:
        roles = [role["role"] for role in load_yaml(UPDATE_PIHOLE)[0]["roles"]]
        updates = roles.index("steveyminecraft.pihole.updates")
        unbound = roles.index("steveyminecraft.pihole.unbound")
        pihole = roles.index("steveyminecraft.pihole.pihole")
        self.assertLess(updates, unbound)
        self.assertLess(unbound, pihole)
        unbound_role = next(
            role
            for role in load_yaml(UPDATE_PIHOLE)[0]["roles"]
            if role["role"] == "steveyminecraft.pihole.unbound"
        )
        when = yaml.dump(unbound_role.get("when"))
        self.assertIn("pihole_enable_unbound", when)
        self.assertIn("ansible_check_mode", when)

    def test_update_pihole_playbook_ha_safety_flags(self) -> None:
        first_play = load_yaml(UPDATE_PIHOLE)[0]
        self.assertTrue(first_play.get("any_errors_fatal"))

        pihole_role = next(
            role for role in first_play["roles"] if role["role"].endswith(".pihole")
        )
        self.assertEqual(pihole_role.get("when"), "not ansible_check_mode")

        post_task = first_play["post_tasks"][0]
        self.assertEqual(post_task.get("when"), "not ansible_check_mode")
        self.assertIn("rescue", post_task)
        self.assertIn("block", post_task)

    def test_update_pihole_vip_verify_retries_until_ipv4(self) -> None:
        vip_task = load_yaml(UPDATE_PIHOLE)[1]["tasks"][0]
        self.assertEqual(vip_task.get("retries"), 30)
        self.assertEqual(vip_task.get("delay"), 2)
        self.assertIn("until", vip_task)
        self.assertIn("pihole_ha_mode", str(vip_task.get("when")))

    def test_default_molecule_exercises_update_side_effect(self) -> None:
        sequence = load_yaml(UBUNTU_MOLECULE)["scenario"]["test_sequence"]
        side_effect_index = sequence.index("side_effect")
        verify_indices = [index for index, step in enumerate(sequence) if step == "verify"]
        self.assertGreater(side_effect_index, verify_indices[0])
        self.assertLess(side_effect_index, verify_indices[-1])

    def test_update_pihole_requires_peer_dns_before_drain(self) -> None:
        first_play = load_yaml(UPDATE_PIHOLE)[0]
        pre_tasks = first_play.get("pre_tasks") or []
        self.assertTrue(pre_tasks, "update-pihole must probe peer DNS before draining")

        def named(items):
            found = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                if "name" in item:
                    found.append(item)
                found.extend(named(item.get("block") or []))
            return found

        tasks = named(pre_tasks)
        names = [task["name"] for task in tasks]
        self.assertIn("Collect peer DNS addresses before drain", names)
        self.assertIn("Probe peer DNS listeners before drain", names)
        self.assertIn("Refuse to drain the last healthy DNS node", names)
        self.assertLess(
            names.index("Collect peer DNS addresses before drain"),
            names.index("Probe peer DNS listeners before drain"),
        )
        self.assertLess(
            names.index("Probe peer DNS listeners before drain"),
            names.index("Refuse to drain the last healthy DNS node"),
        )

        collect = next(
            task for task in tasks if task["name"] == "Collect peer DNS addresses before drain"
        )
        fact = yaml.dump(collect["ansible.builtin.set_fact"])
        self.assertIn("groups['all']", fact)
        self.assertIn("inventory_hostname", fact)
        self.assertIn("ansible_host", fact)

        probe = next(
            task for task in tasks if task["name"] == "Probe peer DNS listeners before drain"
        )
        wait_for = probe["ansible.builtin.wait_for"]
        self.assertEqual(wait_for["port"], 53)
        self.assertTrue(probe.get("ignore_errors"))
        probe_when = yaml.dump(probe.get("when"))
        self.assertIn("ansible_check_mode", probe_when)

        refuse = next(
            task for task in tasks if task["name"] == "Refuse to drain the last healthy DNS node"
        )
        that = yaml.dump(refuse["ansible.builtin.assert"]["that"])
        self.assertIn("rejectattr('failed')", that)
        self.assertIn("last healthy", refuse["ansible.builtin.assert"]["fail_msg"].lower())

        roles = [role["role"] for role in first_play["roles"]]
        self.assertEqual(roles[0], "steveyminecraft.pihole.stop_keepalived")

    def test_bootstrap_does_not_require_peer_dns_before_first_install(self) -> None:
        bootstrap = load_yaml(ROOT / "playbooks" / "bootstrap-pihole.yaml")[0]
        blob = yaml.dump(bootstrap.get("pre_tasks") or [])
        self.assertNotIn("Refuse to drain the last healthy DNS node", blob)


class PiholeComposeTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        loader = FileSystemLoader(COMPOSE_TEMPLATE.parent)
        env = Environment(loader=loader, undefined=StrictUndefined)
        env.filters["bool"] = lambda value: (
            value if isinstance(value, bool) else str(value).lower() in ("true", "1", "yes")
        )
        env.filters["string"] = str
        cls.env = env

    def _render(self, **overrides) -> str:
        defaults = yaml.safe_load(PIHOLE_DEFAULTS.read_text(encoding="utf-8")) or {}
        variables = {
            "pihole_container_name": "pihole",
            "inventory_hostname": "node1",
            "pihole_image": defaults["pihole_image"],
            "pihole_use_host_network": False,
            "pihole_enable_unbound": True,
            "pihole_network_name": "dns_net",
            "pihole_dir_loc": "/opt/pihole",
            "pihole_environment_variables": {
                "TZ": "UTC",
                "DHCP_ACTIVE": False,
                "FTLCONF_dns_listeningMode": "ALL",
            },
            "pihole_container_cap_add": ["NET_ADMIN"],
            "pihole_rocky_network_debug": False,
            "pihole_docker_dns": [],
            "pihole_webport_http": "80",
            "pihole_webport_https": "443",
        }
        variables.update(overrides)
        template = self.env.get_template(COMPOSE_TEMPLATE.name)
        return template.render(**variables)

    def test_dhcp_disabled_omits_dhcp_port(self) -> None:
        rendered = self._render()
        self.assertNotIn("67:67/udp", rendered)

    def test_dhcp_enabled_publishes_dhcp_port(self) -> None:
        rendered = self._render(
            pihole_environment_variables={
                "TZ": "UTC",
                "DHCP_ACTIVE": True,
                "FTLCONF_dns_listeningMode": "ALL",
            }
        )
        self.assertIn("67:67/udp", rendered)


if __name__ == "__main__":
    unittest.main()
