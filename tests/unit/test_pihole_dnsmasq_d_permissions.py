"""FTL runs as UID 1000 and cannot traverse root:root 0750 dnsmasq.d."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEPLOYPI = ROOT / "roles" / "pihole" / "tasks" / "deploypi.yml"
PROXY = ROOT / "roles" / "pihole" / "tasks" / "proxy.yml"
VERIFY = ROOT / "roles" / "pihole" / "tasks" / "verify.yml"
DNS_VERIFY = ROOT / "molecule" / "common" / "verify" / "dns.yml"


def load_tasks(path: Path) -> list[dict]:
    tasks = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(tasks, list):
        raise AssertionError(f"{path} did not parse as a YAML list")
    return tasks


def task_by_name(path: Path, name: str) -> dict:
    for task in load_tasks(path):
        if task.get("name") == name:
            return task
    raise AssertionError(f"{path.name} is missing task {name!r}")


def task_names(path: Path) -> list[str]:
    return [str(task.get("name", "")) for task in load_tasks(path)]


def assert_dnsmasq_d_mode_0755(path: Path, stat_register: str) -> None:
    stat_task = task_by_name(path, "Stat Pi-hole dnsmasq.d directory")
    assert_task = task_by_name(path, "Assert dnsmasq.d is traversable by FTL")
    stat_path = stat_task["ansible.builtin.stat"]["path"]
    conditions = assert_task["ansible.builtin.assert"]["that"]
    self_joined = "\n".join(str(item) for item in conditions)
    if "dnsmasq.d" not in stat_path:
        raise AssertionError(f"{path.name} stats the wrong path: {stat_path}")
    if stat_register not in self_joined:
        raise AssertionError(f"{path.name} assert does not use {stat_register}")
    if "0755" not in self_joined:
        raise AssertionError(f"{path.name} assert does not require mode 0755")


class PiholeDnsmasqDPermissionTests(unittest.TestCase):
    def test_deploypi_creates_ftl_readable_dnsmasq_d_before_compose(self) -> None:
        names = task_names(DEPLOYPI)
        create = task_by_name(DEPLOYPI, "Ensure Pi-hole dnsmasq.d is readable by FTL")
        file_task = create["ansible.builtin.file"]
        self.assertEqual(file_task["path"], "{{ pihole_dir_loc }}/etc/dnsmasq.d")
        self.assertEqual(file_task["state"], "directory")
        self.assertEqual(file_task["mode"], "0755")
        self.assertLess(
            names.index("Ensure Pi-hole dnsmasq.d is readable by FTL"),
            names.index("Start Pi-hole service (docker compose v2)"),
        )

    def test_deploypi_repairs_existing_dnsmasq_d_file_modes(self) -> None:
        find = task_by_name(DEPLOYPI, "Find Pi-hole dnsmasq.d config files")
        chmod = task_by_name(
            DEPLOYPI, "Ensure dnsmasq.d config files are readable by FTL"
        )
        self.assertEqual(
            find["ansible.builtin.find"]["paths"],
            "{{ pihole_dir_loc }}/etc/dnsmasq.d",
        )
        self.assertEqual(find["register"], "pihole_dnsmasq_d_files")
        self.assertEqual(chmod["ansible.builtin.file"]["mode"], "0644")
        self.assertEqual(chmod["loop"], "{{ pihole_dnsmasq_d_files.files }}")

    def test_traefik_proxy_dnsmasq_volume_is_ftl_readable(self) -> None:
        create = task_by_name(PROXY, "Create Pi-hole dnsmasq.d directory")
        publish = task_by_name(PROXY, "Publish Traefik hostnames through Pi-hole DNS")
        self.assertEqual(create["ansible.builtin.file"]["mode"], "0755")
        self.assertEqual(publish["ansible.builtin.template"]["mode"], "0644")

    def test_role_verify_asserts_dnsmasq_d_mode(self) -> None:
        assert_dnsmasq_d_mode_0755(VERIFY, "pihole_dnsmasq_d_stat")

    def test_molecule_dns_verify_asserts_dnsmasq_d_mode(self) -> None:
        assert_dnsmasq_d_mode_0755(DNS_VERIFY, "molecule_dnsmasq_d")


if __name__ == "__main__":
    unittest.main()
