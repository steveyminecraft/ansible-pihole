"""Unit tests for scripts/default-container-images.py (Trivy scan matrix)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "default-container-images.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("default_container_images", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DefaultContainerImagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.helper = load_helper()

    def test_default_images_include_each_deployed_service(self) -> None:
        images = set(self.helper.default_images())
        pihole = self.helper.load_defaults("pihole")
        unbound = self.helper.load_defaults("unbound")
        nebula = self.helper.load_defaults("nebula_sync")

        self.assertIn(pihole["pihole_image"], images)
        self.assertIn(unbound["unbound_image_arch_default"], images)
        self.assertTrue(set(unbound["unbound_image_arch_map"].values()) <= images)
        self.assertIn(
            f"{nebula['nebula_sync_image']}:{nebula['nebula_sync_image_tag']}",
            images,
        )

    def test_default_images_reject_latest_tag(self) -> None:
        latest_images = [
            image for image in self.helper.default_images() if image.endswith(":latest")
        ]

        self.assertEqual([], latest_images)

    def test_github_matrix_is_valid_and_has_unique_keys(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--github-matrix"],
            check=True,
            capture_output=True,
            text=True,
        )
        matrix = json.loads(result.stdout)
        entries = matrix["include"]

        self.assertGreaterEqual(len(entries), 3)
        self.assertEqual(len(entries), len(self.helper.default_images()))
        self.assertEqual(len({entry["key"] for entry in entries}), len(entries))
        self.assertEqual(
            {entry["image"] for entry in entries},
            set(self.helper.default_images()),
        )


if __name__ == "__main__":
    unittest.main()
