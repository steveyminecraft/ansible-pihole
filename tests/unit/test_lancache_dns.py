"""Tests for scripts/lancache_dns.py (Steam-only isolated dnsmasq)."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "lancache_dns.py"


def load_module():
    spec = importlib.util.spec_from_file_location("lancache_dns", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load lancache_dns.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LancacheDnsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()
        cls.cache_ip = "172.16.7.51"

    def test_generate_from_vendored_tree_is_steam_only(self) -> None:
        conf = self.mod.generate_from_tree(ROOT, self.cache_ip)
        self.assertIn("address=/lancache.steamcontent.com/172.16.7.51", conf)
        self.assertIn("local=/lancache.steamcontent.com/", conf)
        self.assertNotIn("origin.com", conf)
        self.assertNotIn("blizzard", conf)
        self.assertNotIn("0.0.0.0", conf)
        self.assertNotIn("172.16.7.25", conf)
        self.assertNotIn("172.16.7.50", conf)

    def test_generated_conf_is_ipv4_only(self) -> None:
        conf = self.mod.generate_from_tree(ROOT, self.cache_ip)
        self.assertNotIn("filter-AAAA", conf)
        for line in conf.splitlines():
            if not line.startswith("address=/"):
                continue
            ip = line.rsplit("/", 1)[-1]
            self.mod.ipaddress.IPv4Address(ip)

    def test_validate_rejects_ipv6_address_target(self) -> None:
        text = (
            "address=/lancache.steamcontent.com/2001:db8::51\n"
            "local=/lancache.steamcontent.com/\n"
        )
        errors = self.mod.validate_conf(
            text, self.cache_ip, ["lancache.steamcontent.com"]
        )
        self.assertTrue(any("IPv6" in item for item in errors))

    def test_committed_generated_file_matches_generator(self) -> None:
        expected = (
            ROOT / "roles" / "lancache_dns" / "files" / "generated" / "lancache.conf"
        ).read_text(encoding="utf-8")
        self.assertEqual(self.mod.generate_from_tree(ROOT, self.cache_ip), expected)

    def test_validate_rejects_empty(self) -> None:
        errors = self.mod.validate_conf("", self.cache_ip, ["lancache.steamcontent.com"])
        self.assertTrue(errors)

    def test_validate_rejects_wrong_ip(self) -> None:
        text = "address=/lancache.steamcontent.com/172.16.7.50\nlocal=/lancache.steamcontent.com/\n"
        errors = self.mod.validate_conf(text, self.cache_ip, ["lancache.steamcontent.com"])
        self.assertTrue(any("cache IPv4" in item for item in errors))

    def test_validate_rejects_package_cache_suffix(self) -> None:
        text = "address=/archive.ubuntu.com/172.16.7.51\nlocal=/archive.ubuntu.com/\n"
        errors = self.mod.validate_conf(text, self.cache_ip, ["archive.ubuntu.com"])
        self.assertTrue(any("reserved suffix" in item for item in errors))

    def test_validate_rejects_unexpected_directive(self) -> None:
        text = "server=/lancache.steamcontent.com/1.1.1.1\n"
        errors = self.mod.validate_conf(text, self.cache_ip, ["lancache.steamcontent.com"])
        self.assertTrue(any("unsupported" in item for item in errors))

    def test_load_enabled_domains_rejects_extra_services(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tree = Path(tmpdir)
            (tree / "cache_domains.json").write_text(
                '{"cache_domains":[{"name":"steam","domain_files":["steam.txt"]},'
                '{"name":"blizzard","domain_files":["blizzard.txt"]}]}',
                encoding="utf-8",
            )
            (tree / "steam.txt").write_text("lancache.steamcontent.com\n", encoding="utf-8")
            (tree / "blizzard.txt").write_text("blizzard.com\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.mod.load_enabled_domains(tree, ("steam",))

    def test_pin_must_be_full_sha(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pin = Path(tmpdir) / "PIN"
            pin.write_text("latest\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.mod.read_pin(pin)


if __name__ == "__main__":
    unittest.main()
