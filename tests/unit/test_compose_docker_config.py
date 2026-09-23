"""docker compose config on rendered Traefik/Pi-hole YAML (catches a broken deploy)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import test_traefik_templates as _templates


class ComposeDockerConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _templates.TraefikJinjaTests.setUpClass()
        cls.helper = _templates.TraefikJinjaTests()

    def _compose_config(self, rendered: str) -> None:
        docker = shutil.which("docker")
        if docker is None:
            self.skipTest("docker not installed")
        with tempfile.TemporaryDirectory() as tmp:
            compose = Path(tmp) / "docker-compose.yml"
            compose.write_text(rendered, encoding="utf-8")
            proc = subprocess.run(
                ["docker", "compose", "-f", str(compose), "config", "--quiet"],
                cwd=tmp,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                proc.returncode,
                0,
                msg=f"stdout={proc.stdout}\nstderr={proc.stderr}",
            )

    def test_traefik_compose_config(self) -> None:
        rendered = _templates.TraefikJinjaTests.traefik_env.get_template(
            "docker-compose.yml.j2"
        ).render(**self.helper._traefik_vars(traefik_acme_environment={}))
        self._compose_config(rendered)

    def test_pihole_compose_config_without_proxy(self) -> None:
        rendered = _templates.TraefikJinjaTests.pihole_env.get_template(
            "docker-compose.yml.j2"
        ).render(**self.helper._pihole_vars())
        self._compose_config(rendered)

    def test_pihole_compose_config_with_proxy(self) -> None:
        rendered = _templates.TraefikJinjaTests.pihole_env.get_template(
            "docker-compose.yml.j2"
        ).render(**self.helper._pihole_vars(pihole_proxy_enabled=True))
        self._compose_config(rendered)


if __name__ == "__main__":
    unittest.main()
