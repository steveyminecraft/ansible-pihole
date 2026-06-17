"""Tests for scripts/check-pihole-image-upstream.py."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check-pihole-image-upstream.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_pihole_image_upstream", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CheckPiholeImageUpstreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.helper = load_module()

    def test_parse_calendar_tag(self) -> None:
        self.assertEqual(
            self.helper.parse_calendar_tag("2026.05.0"),
            (2026, 5, 0),
        )
        self.assertIsNone(self.helper.parse_calendar_tag("latest"))
        self.assertIsNone(self.helper.parse_calendar_tag("v5.1.2"))

    def test_latest_calendar_tag(self) -> None:
        tags = ["2026.04.0", "2026.05.0", "2026.06.0", "latest", "nightly"]
        self.assertEqual(self.helper.latest_calendar_tag(tags), "2026.06.0")

    def test_pinned_tag(self) -> None:
        self.assertEqual(
            self.helper.pinned_tag("pihole/pihole:2026.05.0"),
            "2026.05.0",
        )


if __name__ == "__main__":
    unittest.main()
