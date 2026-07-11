"""Unit tests for scripts/dedupe-graphify-graph.py."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "dedupe-graphify-graph.py"


def load_module():
    spec = importlib.util.spec_from_file_location("dedupe_graphify_graph", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DedupeGraphifyGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_module()

    def test_normalize_concept_strips_playbook_suffix(self) -> None:
        self.assertEqual(
            self.mod.normalize_concept("`playbooks/update-pihole.yaml`"),
            "update-pihole",
        )
        self.assertEqual(
            self.mod.normalize_concept("update-pihole playbook"),
            "update-pihole",
        )

    def test_merge_duplicate_nodes_prefers_playbook_source(self) -> None:
        nodes = [
            {
                "id": "docs_ref",
                "label": "update-pihole.yaml",
                "source_file": "docs/production-deployment.md",
            },
            {
                "id": "playbook_ref",
                "label": "update-pihole playbook",
                "source_file": "playbooks/update-pihole.yaml",
            },
        ]
        merged, id_map, merge_count = self.mod.merge_duplicate_nodes(nodes)
        self.assertEqual(merge_count, 1)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["id"], "playbook_ref")
        self.assertIn("update-pihole.yaml", merged[0]["aliases"])
        self.assertEqual(id_map["docs_ref"], "playbook_ref")

    def test_rewire_links_follows_id_map(self) -> None:
        links = [
            {"source": "docs_ref", "target": "other", "relation": "mentions"},
            {"source": "other", "target": "docs_ref", "relation": "uses"},
        ]
        id_map = {"docs_ref": "playbook_ref"}
        rewired = self.mod.rewire_links(links, id_map)
        self.assertEqual(len(rewired), 2)
        self.assertEqual(rewired[0]["source"], "playbook_ref")
        self.assertEqual(rewired[1]["target"], "playbook_ref")

    def test_prune_isolated_nodes_removes_zero_degree(self) -> None:
        nodes = [
            {"id": "a", "label": "connected"},
            {"id": "b", "label": "lonely"},
        ]
        links = [{"source": "a", "target": "c", "relation": "rel"}]
        kept, removed = self.mod.prune_isolated_nodes(nodes, links)
        self.assertEqual(removed, 1)
        self.assertEqual([node["id"] for node in kept], ["a"])

    def test_main_dry_run_reports_stats(self) -> None:
        graph = {
            "nodes": [
                {
                    "id": "docs_ref",
                    "label": "update-pihole.yaml",
                    "source_file": "docs/production-deployment.md",
                },
                {
                    "id": "playbook_ref",
                    "label": "update-pihole playbook",
                    "source_file": "playbooks/update-pihole.yaml",
                },
                {"id": "lonely", "label": "orphan", "source_file": "docs/x.md"},
            ],
            "links": [
                {"source": "docs_ref", "target": "playbook_ref", "relation": "same"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            graph_path = Path(tmp) / "graph.json"
            graph_path.write_text(json.dumps(graph), encoding="utf-8")
            before = graph_path.read_text(encoding="utf-8")
            rc = self.mod.main(["--graph", str(graph_path), "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertEqual(graph_path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
