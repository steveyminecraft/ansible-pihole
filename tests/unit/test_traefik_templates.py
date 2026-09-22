"""Template and default tests for the optional Traefik role."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


ROOT = Path(__file__).resolve().parents[2]
TRAEFIK_DEFAULTS = ROOT / "roles" / "traefik" / "defaults" / "main.yml"
TRAEFIK_TEMPLATES = ROOT / "roles" / "traefik" / "templates"
PIHOLE_DEFAULTS = ROOT / "roles" / "pihole" / "defaults" / "main.yml"
PIHOLE_COMPOSE = ROOT / "roles" / "pihole" / "templates" / "docker-compose.yml.j2"
BOOTSTRAP = ROOT / "playbooks" / "bootstrap-pihole.yaml"
UPDATE_PIHOLE = ROOT / "playbooks" / "update-pihole.yaml"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def ansible_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes")


class TraefikJinjaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        traefik_env = Environment(
            loader=FileSystemLoader(str(TRAEFIK_TEMPLATES)),
            undefined=StrictUndefined,
        )
        pihole_env = Environment(
            loader=FileSystemLoader(str(PIHOLE_COMPOSE.parent)),
            undefined=StrictUndefined,
        )
        for env in (traefik_env, pihole_env):
            env.filters["bool"] = ansible_bool
            env.filters["string"] = str
            env.filters["lower"] = lambda value: str(value).lower()
        cls.traefik_env = traefik_env
        cls.pihole_env = pihole_env
        cls.traefik_defaults = load_yaml(TRAEFIK_DEFAULTS)
        cls.pihole_defaults = load_yaml(PIHOLE_DEFAULTS)

    def _traefik_vars(self, **overrides):
        variables = {
            "traefik_enabled": False,
            "traefik_image": self.traefik_defaults["traefik_image"],
            "traefik_version": self.traefik_defaults["traefik_version"],
            "traefik_container_name": "traefik",
            "traefik_restart_policy": "unless-stopped",
            "traefik_network_name": "proxy",
            "traefik_http_port": 80,
            "traefik_https_port": 443,
            "traefik_log_level": "INFO",
            "traefik_dashboard_enabled": False,
            "traefik_dashboard_hostname": "",
            "traefik_dashboard_basicauth_users": [],
            "traefik_tls_enabled": True,
            "traefik_tls_mode": "dns01",
            "traefik_domain": "lab.example.com",
            "traefik_acme_email": "admin@example.com",
            "traefik_acme_resolver_name": "letsencrypt",
            "traefik_acme_dns_provider": "cloudflare",
            "traefik_acme_staging": False,
            "traefik_acme_wildcard": True,
            "traefik_acme_environment": {"CLOUDFLARE_DNS_API_TOKEN": "super-secret-token"},
            "traefik_config_path": "/opt/traefik/traefik.yml",
            "traefik_dynamic_dir": "/opt/traefik/dynamic",
            "traefik_certs_dir": "/opt/traefik/certs",
            "traefik_acme_json_path": "/opt/traefik/acme.json",
            "traefik_acme_env_path": "/opt/traefik/acme.env",
            "traefik_resolved_socket": "/var/run/docker.sock",
        }
        variables.update(overrides)
        return variables

    def _pihole_vars(self, **overrides):
        variables = {
            "pihole_container_name": "pihole",
            "inventory_hostname": "node1",
            "pihole_image": self.pihole_defaults["pihole_image"],
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
            "pihole_proxy_enabled": False,
            "pihole_proxy_hostname": "pihole.lab.example.com",
            "pihole_proxy_router_name": "pihole",
            "pihole_proxy_backend_port": 80,
            "ansible_host": "192.0.2.10",
            "traefik_network_name": "proxy",
            "traefik_tls_enabled": True,
            "traefik_tls_mode": "dns01",
            "traefik_acme_resolver_name": "letsencrypt",
        }
        variables.update(overrides)
        return variables

    def test_defaults_keep_traefik_opt_in_and_pinned(self) -> None:
        defaults = self.traefik_defaults
        self.assertFalse(defaults["traefik_enabled"])
        self.assertFalse(defaults["traefik_dashboard_enabled"])
        self.assertEqual(defaults["traefik_tls_mode"], "dns01")
        self.assertEqual(defaults["traefik_acme_environment"], {})
        self.assertEqual(defaults["traefik_acme_email"], "")
        self.assertNotIn("latest", defaults["traefik_version"])
        self.assertTrue(str(defaults["traefik_version"]).startswith("v"))
        self.assertEqual(defaults["traefik_container_runtime"], "docker")
        self.assertEqual(defaults["traefik_socket"], "auto")

    def test_pihole_proxy_defaults_follow_traefik_disabled(self) -> None:
        self.assertIn("traefik_enabled", self.pihole_defaults["pihole_proxy_enabled"])
        self.assertIn("pihole_proxy_enabled", self.pihole_defaults["pihole_proxy_dns_enabled"])

    def test_static_config_uses_secure_docker_provider(self) -> None:
        rendered = self.traefik_env.get_template("traefik.yml.j2").render(**self._traefik_vars())
        parsed = yaml.safe_load(rendered)
        self.assertFalse(parsed["providers"]["docker"]["exposedByDefault"])
        self.assertTrue(parsed["providers"]["docker"]["watch"])
        self.assertEqual(parsed["providers"]["docker"]["network"], "proxy")
        self.assertEqual(
            parsed["providers"]["docker"]["endpoint"],
            "unix:///var/run/docker.sock",
        )
        self.assertFalse(parsed["api"]["insecure"])
        self.assertFalse(parsed["api"]["dashboard"])
        self.assertEqual(
            parsed["entryPoints"]["web"]["http"]["redirections"]["entryPoint"]["to"],
            "websecure",
        )
        self.assertIn("certificatesResolvers", parsed)
        self.assertNotIn("super-secret-token", rendered)
        self.assertNotIn("CLOUDFLARE_DNS_API_TOKEN", rendered)

    def test_supplied_tls_mode_omits_acme(self) -> None:
        rendered = self.traefik_env.get_template("traefik.yml.j2").render(
            **self._traefik_vars(traefik_tls_mode="supplied")
        )
        parsed = yaml.safe_load(rendered)
        self.assertNotIn("certificatesResolvers", parsed)

    def test_compose_mounts_unix_socket_read_only(self) -> None:
        rendered = self.traefik_env.get_template("docker-compose.yml.j2").render(
            **self._traefik_vars()
        )
        parsed = yaml.safe_load(rendered)
        service = parsed["services"]["traefik"]
        self.assertIn("/var/run/docker.sock:/var/run/docker.sock:ro", service["volumes"])
        self.assertIn("80:80/tcp", [str(port) for port in service["ports"]])
        self.assertIn("443:443/tcp", [str(port) for port in service["ports"]])
        self.assertNotIn("labels", service)
        self.assertNotIn("tcp://", rendered)

    def test_pihole_without_proxy_still_publishes_web_ports(self) -> None:
        rendered = self.pihole_env.get_template("docker-compose.yml.j2").render(
            **self._pihole_vars()
        )
        parsed = yaml.safe_load(rendered)
        ports = parsed["services"]["pihole"]["ports"]
        self.assertIn("53:53/tcp", ports)
        self.assertIn("80:80/tcp", ports)
        self.assertIn("443:443/tcp", ports)
        self.assertNotIn("labels", parsed["services"]["pihole"])
        self.assertNotIn("proxy", parsed.get("networks", {}))

    def test_pihole_with_proxy_uses_labels_and_hides_web_ports(self) -> None:
        rendered = self.pihole_env.get_template("docker-compose.yml.j2").render(
            **self._pihole_vars(pihole_proxy_enabled=True)
        )
        parsed = yaml.safe_load(rendered)
        service = parsed["services"]["pihole"]
        self.assertIn("dns_net", parsed["networks"])
        self.assertIn("proxy", parsed["networks"])
        self.assertIn("proxy", service["networks"])
        self.assertIn("dns_net", service["networks"])
        self.assertEqual(service["labels"]["traefik.enable"], "true")
        self.assertEqual(service["labels"]["traefik.docker.network"], "proxy")
        self.assertEqual(
            service["labels"]["traefik.http.routers.pihole.rule"],
            "Host(`pihole.lab.example.com`) || Host(`192.0.2.10`)",
        )
        self.assertEqual(
            service["labels"]["traefik.http.routers.pihole.entrypoints"],
            "websecure",
        )
        self.assertEqual(service["labels"]["traefik.http.routers.pihole.tls"], "true")
        self.assertEqual(
            service["labels"]["traefik.http.services.pihole.loadbalancer.server.port"],
            "80",
        )
        self.assertIn("53:53/tcp", service["ports"])
        self.assertIn("53:53/udp", service["ports"])
        self.assertNotIn("80:80/tcp", service["ports"])
        self.assertNotIn("443:443/tcp", service["ports"])

    def test_pihole_proxy_host_rule_includes_ansible_host(self) -> None:
        rendered = self.pihole_env.get_template("docker-compose.yml.j2").render(
            **self._pihole_vars(
                pihole_proxy_enabled=True,
                ansible_host="192.168.121.4",
            )
        )
        parsed = yaml.safe_load(rendered)
        rule = parsed["services"]["pihole"]["labels"][
            "traefik.http.routers.pihole.rule"
        ]
        self.assertIn("Host(`pihole.lab.example.com`)", rule)
        self.assertIn("Host(`192.168.121.4`)", rule)
        self.assertNotIn("Host(`node1`)", rule)

    def test_pihole_proxy_host_rule_includes_node_dns_name(self) -> None:
        rendered = self.pihole_env.get_template("docker-compose.yml.j2").render(
            **self._pihole_vars(
                pihole_proxy_enabled=True,
                inventory_hostname="pihole-01",
                traefik_domain="coalhill.zz",
                ansible_host="172.16.7.25",
                pihole_proxy_hostname="pihole.coalhill.zz",
            )
        )
        parsed = yaml.safe_load(rendered)
        self.assertEqual(
            parsed["services"]["pihole"]["labels"]["traefik.http.routers.pihole.rule"],
            "Host(`pihole.coalhill.zz`) || Host(`172.16.7.25`) || Host(`pihole-01.coalhill.zz`)",
        )

    def test_pihole_proxy_extra_hostnames_replace_node_dns_name(self) -> None:
        rendered = self.pihole_env.get_template("docker-compose.yml.j2").render(
            **self._pihole_vars(
                pihole_proxy_enabled=True,
                inventory_hostname="pihole-01",
                traefik_domain="coalhill.zz",
                pihole_proxy_extra_hostnames=[],
            )
        )
        parsed = yaml.safe_load(rendered)
        rule = parsed["services"]["pihole"]["labels"]["traefik.http.routers.pihole.rule"]
        self.assertEqual(
            rule,
            "Host(`pihole.lab.example.com`) || Host(`192.0.2.10`)",
        )

    def test_host_network_proxy_file_includes_node_dns_name(self) -> None:
        rendered = self.pihole_env.get_template("dynamic-pihole-host.yml.j2").render(
            **self._pihole_vars(
                pihole_proxy_enabled=True,
                inventory_hostname="pihole-02",
                traefik_domain="coalhill.zz",
                ansible_host="172.16.7.30",
                pihole_proxy_hostname="pihole.coalhill.zz",
            )
        )
        parsed = yaml.safe_load(rendered)
        self.assertEqual(
            parsed["http"]["routers"]["pihole"]["rule"],
            "Host(`pihole.coalhill.zz`) || Host(`172.16.7.30`) || Host(`pihole-02.coalhill.zz`)",
        )

    def test_static_config_omits_redirect_when_tls_disabled(self) -> None:
        rendered = self.traefik_env.get_template("traefik.yml.j2").render(
            **self._traefik_vars(traefik_tls_enabled=False)
        )
        parsed = yaml.safe_load(rendered)
        self.assertNotIn("redirections", parsed["entryPoints"]["web"].get("http", {}))

    def test_pihole_http_proxy_uses_web_entrypoint(self) -> None:
        rendered = self.pihole_env.get_template("docker-compose.yml.j2").render(
            **self._pihole_vars(
                pihole_proxy_enabled=True,
                traefik_tls_enabled=False,
            )
        )
        parsed = yaml.safe_load(rendered)
        labels = parsed["services"]["pihole"]["labels"]
        self.assertEqual(labels["traefik.http.routers.pihole.entrypoints"], "web")
        self.assertNotIn("traefik.http.routers.pihole.tls", labels)
        self.assertNotIn("traefik.http.routers.pihole.tls.certresolver", labels)

    def test_pihole_proxy_keeps_dhcp_port(self) -> None:
        rendered = self.pihole_env.get_template("docker-compose.yml.j2").render(
            **self._pihole_vars(
                pihole_proxy_enabled=True,
                pihole_environment_variables={
                    "TZ": "UTC",
                    "DHCP_ACTIVE": True,
                    "FTLCONF_dns_listeningMode": "ALL",
                },
            )
        )
        parsed = yaml.safe_load(rendered)
        self.assertIn("67:67/udp", parsed["services"]["pihole"]["ports"])

    def test_pihole_proxy_without_unbound_only_joins_proxy_network(self) -> None:
        rendered = self.pihole_env.get_template("docker-compose.yml.j2").render(
            **self._pihole_vars(pihole_proxy_enabled=True, pihole_enable_unbound=False)
        )
        parsed = yaml.safe_load(rendered)
        self.assertEqual(list(parsed["networks"]), ["proxy"])
        self.assertEqual(parsed["services"]["pihole"]["networks"], ["proxy"])
        self.assertNotIn("80:80/tcp", parsed["services"]["pihole"]["ports"])

    def test_playbooks_include_traefik_role(self) -> None:
        bootstrap_roles = [
            role["role"] for role in load_yaml(BOOTSTRAP)[0]["roles"]
        ]
        update_roles = [
            role["role"] for role in load_yaml(UPDATE_PIHOLE)[0]["roles"]
        ]
        self.assertIn("steveyminecraft.pihole.traefik", bootstrap_roles)
        self.assertIn("steveyminecraft.pihole.traefik", update_roles)
        traefik_index = bootstrap_roles.index("steveyminecraft.pihole.traefik")
        pihole_index = bootstrap_roles.index("steveyminecraft.pihole.pihole")
        self.assertLess(traefik_index, pihole_index)


if __name__ == "__main__":
    unittest.main()
