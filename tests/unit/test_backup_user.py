"""Contract tests for the dump-only Pi-hole backup SSH user."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ROLE = ROOT / "roles" / "backup_user"
TASKS = ROLE / "tasks" / "main.yml"
DEFAULTS = ROLE / "defaults" / "main.yml"
DUMP = ROLE / "files" / "pihole-backup-dump.sh"
PLAYBOOK = ROOT / "playbooks" / "backup-user.yaml"
BOOTSTRAP = ROOT / "playbooks" / "bootstrap-pihole.yaml"
UPDATE = ROOT / "playbooks" / "update-pihole.yaml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
GALAXY_PUBLISH = ROOT / ".github" / "workflows" / "galaxy-publish.yml"
CI_VARS = ROOT / "inventory" / "ci" / "group_vars" / "all.yml"


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def named_tasks(doc):
    tasks = []
    for item in doc:
        if not isinstance(item, dict) or "name" not in item:
            continue
        tasks.append(item)
        block = item.get("block")
        if isinstance(block, list):
            tasks.extend(named_tasks(block))
    return tasks


class BackupUserRoleTests(unittest.TestCase):
    def test_role_has_galaxy_readme(self) -> None:
        readme = ROLE / "README.md"
        self.assertTrue(readme.is_file())
        text = readme.read_text(encoding="utf-8")
        self.assertIn("backup_user", text)
        self.assertIn("playbooks/backup-user.yaml", text)
        self.assertIn("do **not**", text)
        self.assertIn("update-pihole.yaml", text)

    def test_defaults_are_disabled_and_dump_only(self) -> None:
        defaults = load_yaml(DEFAULTS)
        self.assertFalse(defaults["backup_user_enable"])
        self.assertEqual(defaults["backup_user_name"], "backup")
        self.assertEqual(defaults["backup_user_dump_path"], "/usr/local/sbin/pihole-backup-dump")
        self.assertEqual(defaults["backup_user_shell"], "/bin/bash")
        self.assertEqual(defaults["backup_user_authorized_key"], "")

    def test_tasks_require_ed25519_and_forced_command(self) -> None:
        tasks = {task["name"]: task for task in named_tasks(load_yaml(TASKS))}
        self.assertIn("Require an ed25519 authorized key for the dump user", tasks)
        self.assertIn("Install exclusive forced-command authorized key", tasks)
        self.assertIn("Install sudoers rule for dump wrapper only", tasks)
        auth = tasks["Install exclusive forced-command authorized key"]["ansible.posix.authorized_key"]
        self.assertTrue(auth["exclusive"])
        self.assertIn("command=", auth["key_options"])
        self.assertIn("no-pty", auth["key_options"])
        sudoers = tasks["Install sudoers rule for dump wrapper only"]["ansible.builtin.copy"]
        self.assertEqual(sudoers["mode"], "0440")
        self.assertIn("visudo", sudoers["validate"])
        self.assertIn("NOPASSWD", sudoers["content"])
        user = tasks["Create dump-only backup user"]["ansible.builtin.user"]
        self.assertTrue(user["password_lock"])
        self.assertTrue(user["system"])
        self.assertEqual(user["shell"], "{{ backup_user_shell }}")
        self.assertFalse(user.get("groups") or user.get("group") == "sudo")

    def test_dump_wrapper_is_config_only(self) -> None:
        script = DUMP.read_text(encoding="utf-8")
        self.assertIn("etc/dnsmasq.d", script)
        self.assertIn("etc/pihole/gravity.db", script)
        self.assertIn("etc/pihole/pihole.toml", script)
        tar_args = script.split("exec tar", 1)[1]
        self.assertNotIn("pihole-FTL.db", tar_args)
        self.assertNotIn("keepalived", script)
        self.assertNotIn("traefik", script)

    def test_dedicated_playbook_does_not_touch_ha_or_proxy(self) -> None:
        plays = load_yaml(PLAYBOOK)
        self.assertEqual(len(plays), 1)
        play = plays[0]
        self.assertEqual(play.get("serial"), 1)
        self.assertTrue(play.get("any_errors_fatal"))
        self.assertEqual(play["vars"]["backup_user_enable"], True)
        roles = [role["role"] for role in play["roles"]]
        self.assertEqual(roles, ["steveyminecraft.pihole.backup_user"])
        blob = yaml.dump(play)
        for forbidden in (
            "traefik",
            "keepalived",
            "stop_keepalived",
            "stop_containers",
            "steveyminecraft.pihole.pihole",
            "sshd",
        ):
            self.assertNotIn(forbidden, blob)

    def test_rolling_playbooks_do_not_install_backup_user(self) -> None:
        for path in (BOOTSTRAP, UPDATE):
            blob = path.read_text(encoding="utf-8")
            with self.subTest(playbook=path.name):
                self.assertNotIn("backup_user", blob)

    def test_ci_uses_non_secret_ed25519_public_key(self) -> None:
        vars_text = CI_VARS.read_text(encoding="utf-8")
        self.assertIn("ssh-ed25519 ", vars_text)
        self.assertIn("ci-pihole-backup", vars_text)
        self.assertNotIn("BEGIN OPENSSH PRIVATE KEY", vars_text)

    def test_ci_and_galaxy_syntax_check_backup_user_playbook(self) -> None:
        ci = CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("playbooks/backup-user.yaml --syntax-check", ci)
        self.assertIn("playbooks/backup-user.yaml --check", ci)
        galaxy = GALAXY_PUBLISH.read_text(encoding="utf-8")
        self.assertIn("backup-user.yaml", galaxy)


if __name__ == "__main__":
    unittest.main()
