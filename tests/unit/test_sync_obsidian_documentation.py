"""Unit tests for scripts/sync-obsidian-documentation.py."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "sync-obsidian-documentation.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sync_obsidian_documentation", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SyncObsidianDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()

    def test_sync_writes_full_doc_with_graph_banner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            obsidian = Path(tmp) / "graphify-out" / "obsidian"
            docs = root / "docs"
            docs.mkdir(parents=True)
            (docs / "testing.md").write_text("# Testing\n\nBody text.\n", encoding="utf-8")
            obsidian.mkdir(parents=True)
            graph = {
                "nodes": [
                    {
                        "label": "Testing Guide",
                        "source_file": "docs/testing.md",
                    }
                ],
                "links": [],
            }
            (obsidian.parent / "graph.json").write_text(json.dumps(graph), encoding="utf-8")

            count = self.mod.sync_documentation(root, obsidian)
            self.assertEqual(count, 1)

            out = obsidian / "Documentation" / "testing.md"
            self.assertTrue(out.is_file())
            text = out.read_text(encoding="utf-8")
            self.assertIn("source_file: \"docs/testing.md\"", text)
            self.assertIn("[[Testing Guide]]", text)
            self.assertIn("# Testing", text)
            self.assertIn("Body text.", text)
            self.assertTrue((obsidian / "00 - Documentation Index.md").is_file())


if __name__ == "__main__":
    unittest.main()
