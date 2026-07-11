"""Unit tests for scripts/update-pihole-health.py (update-pihole DNS health gates)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "update-pihole-health.py"


def load_module():
    spec = importlib.util.spec_from_file_location("update_pihole_health", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UpdatePiholeHealthGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.helper = load_module()

    def test_accepts_single_ipv4_line(self) -> None:
        self.assertTrue(self.helper.dig_stdout_has_ipv4_answer(["104.16.132.229"]))

    def test_accepts_ipv4_among_blank_lines(self) -> None:
        self.assertTrue(
            self.helper.dig_stdout_has_ipv4_answer(["", "104.16.132.229", ""])
        )

    def test_rejects_empty_output(self) -> None:
        self.assertFalse(self.helper.dig_stdout_has_ipv4_answer([]))
        self.assertFalse(self.helper.dig_stdout_has_ipv4_answer(None))

    def test_rejects_dig_errors_and_cnames(self) -> None:
        self.assertFalse(
            self.helper.dig_stdout_has_ipv4_answer(
                [";; connection timed out; no servers could be reached"]
            )
        )
        self.assertFalse(self.helper.dig_stdout_has_ipv4_answer(["cloudflare.com."]))

    def test_rejects_ipv6_only_answers(self) -> None:
        self.assertFalse(
            self.helper.dig_stdout_has_ipv4_answer(["2606:4700:4700::1111"])
        )


if __name__ == "__main__":
    unittest.main()
