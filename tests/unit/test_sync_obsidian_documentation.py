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
            self.assertTrue((obsidian / "00 - Architecture and CI.md").is_file())

    def test_sync_ci_workflow_and_diagram_hub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            obsidian = Path(tmp) / "graphify-out" / "obsidian"
            (root / "docs").mkdir(parents=True)
            (root / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
            (root / "docs" / "diagrams").mkdir(parents=True)
            (root / "docs" / "diagrams" / "ansible-pihole-layers.png").write_bytes(b"png")
            (root / "docs" / "diagrams" / "ansible-pihole-layers.drawio").write_text("<mxfile/>", encoding="utf-8")
            obsidian.mkdir(parents=True)
            graph = {
                "nodes": [
                    {"label": "CI Pipeline", "source_file": ".github/workflows/ci.yml"},
                    {"label": "Six-Layer Architecture", "source_file": "docs/diagrams/ansible-pihole-layers.png"},
                ],
                "links": [],
            }
            (obsidian.parent / "graph.json").write_text(json.dumps(graph), encoding="utf-8")

            count = self.mod.sync_documentation(root, obsidian)
            self.assertGreaterEqual(count, 2)

            ci_note = obsidian / "Documentation" / "ci-workflows" / "ci.md"
            self.assertTrue(ci_note.is_file())
            self.assertIn("ci-workflow", ci_note.read_text(encoding="utf-8"))
            self.assertTrue((obsidian / "Documentation" / "diagrams" / "ansible-pihole-layers.png").is_file())

            hub = (obsidian / "00 - Architecture and CI.md").read_text(encoding="utf-8")
            self.assertIn("![[Documentation/diagrams/ansible-pihole-layers.png]]", hub)
            self.assertIn("[[Documentation/ci-workflows/ci]]", hub)
            self.assertIn("[[CI Pipeline]]", hub)


if __name__ == "__main__":
    unittest.main()
