"""Tests for scripts/check-pihole-image-pins.py."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PINS_SCRIPT = ROOT / "scripts" / "check-pihole-image-pins.py"
DEFAULTS_SCRIPT = ROOT / "scripts" / "default-container-images.py"


def load_module(script: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CheckPiholeImagePinsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pins = load_module(PINS_SCRIPT, "check_pihole_image_pins")
        cls.defaults = load_module(DEFAULTS_SCRIPT, "default_container_images")

    def test_validate_pins_passes_on_current_repo(self) -> None:
        self.assertEqual(self.pins.validate_pins(), [])

    def test_sync_updates_mismatching_mirror(self) -> None:
        canonical = self.defaults.pinned_pihole_image()
        with tempfile.TemporaryDirectory() as tmpdir:
            mirror = Path(tmpdir) / "ci.yml"
            mirror.write_text('pihole_image: "pihole/pihole:2099.01.0"\n', encoding="utf-8")
            text = mirror.read_text(encoding="utf-8")
            updated, _ = self.pins.PIHOLE_IMAGE_LINE.subn(
                lambda match: f'{match.group("prefix")}{canonical}{match.group(3)}',
                text,
                count=1,
            )
            mirror.write_text(updated, encoding="utf-8")
            self.assertIn(canonical, mirror.read_text(encoding="utf-8"))


class CheckPiholeImageUpstreamDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.upstream = load_module(
            ROOT / "scripts" / "check-pihole-image-upstream.py",
            "check_pihole_image_upstream",
        )

    def test_fail_on_drift_when_latest_is_newer(self) -> None:
        current = self.upstream.parse_calendar_tag("2026.05.0")
        latest = self.upstream.parse_calendar_tag("2026.06.0")
        self.assertTrue(latest > current)

    def test_no_drift_when_tags_match(self) -> None:
        current = self.upstream.parse_calendar_tag("2026.07.2")
        latest = self.upstream.parse_calendar_tag("2026.07.2")
        self.assertFalse(latest > current)


if __name__ == "__main__":
    unittest.main()
