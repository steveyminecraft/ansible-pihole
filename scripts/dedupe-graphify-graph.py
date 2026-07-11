#!/usr/bin/env python3
"""Merge duplicate graphify nodes and optionally prune isolated vertices."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

LINK_KEYS = ("links", "edges")


def link_list(graph: dict[str, Any]) -> list[dict[str, Any]]:
    for key in LINK_KEYS:
        links = graph.get(key)
        if isinstance(links, list):
            return links
    return []


def set_link_list(graph: dict[str, Any], links: list[dict[str, Any]]) -> None:
    primary = "links" if "links" in graph else "edges" if "edges" in graph else "links"
    graph[primary] = links
    for key in LINK_KEYS:
        if key != primary and key in graph:
            graph[key] = []


def normalize_concept(label: str) -> str:
    text = label.lower().strip().strip("`")
    text = re.sub(r"^playbooks/", "", text)
    text = re.sub(r"^roles/", "", text)
    text = text.replace(" playbook", "").replace("playbook", "")
    text = text.replace(".yaml", "").replace(".yml", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def node_preference_score(node: dict[str, Any]) -> int:
    score = 0
    source_file = str(node.get("source_file", ""))
    if source_file.startswith(("playbooks/", "roles/", "molecule/")):
        score += 100
    elif source_file.startswith("docs/") or source_file == "README.md":
        score -= 50
    if node.get("_origin") == "ast":
        score += 10
    score += len(str(node.get("label", "")))
    return score


def degree_by_node(links: list[dict[str, Any]]) -> dict[str, int]:
    degree: dict[str, int] = defaultdict(int)
    for link in links:
        source = link.get("source")
        target = link.get("target")
        if source:
            degree[str(source)] += 1
        if target:
            degree[str(target)] += 1
    return degree


def merge_duplicate_nodes(
    nodes: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str], int]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        label = str(node.get("label", ""))
        key = normalize_concept(label)
        if not key:
            continue
        groups[key].append(node)

    id_map: dict[str, str] = {}
    merged: list[dict[str, Any]] = []
    merge_count = 0

    for group in groups.values():
        if len(group) == 1:
            merged.append(group[0])
            continue

        canonical = max(group, key=node_preference_score)
        canonical_id = str(canonical["id"])
        aliases = sorted(
            {
                str(item.get("label", ""))
                for item in group
                if str(item.get("label", "")) != str(canonical.get("label", ""))
            }
        )
        if aliases:
            canonical = dict(canonical)
            canonical["aliases"] = aliases
        merged.append(canonical)

        for item in group:
            item_id = str(item["id"])
            if item_id != canonical_id:
                id_map[item_id] = canonical_id
                merge_count += 1

    for node in nodes:
        label = str(node.get("label", ""))
        if not normalize_concept(label):
            merged.append(node)

    return merged, id_map, merge_count


def rewire_links(
    links: list[dict[str, Any]], id_map: dict[str, str]
) -> list[dict[str, Any]]:
    if not id_map:
        return links

    rewritten: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for link in links:
        updated = dict(link)
        source = str(updated.get("source", ""))
        target = str(updated.get("target", ""))
        updated["source"] = id_map.get(source, source)
        updated["target"] = id_map.get(target, target)
        if updated["source"] == updated["target"]:
            continue
        relation = str(updated.get("relation", ""))
        key = (updated["source"], updated["target"], relation)
        if key in seen:
            continue
        seen.add(key)
        rewritten.append(updated)
    return rewritten


def prune_isolated_nodes(
    nodes: list[dict[str, Any]], links: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int]:
    degree = degree_by_node(links)
    kept = [node for node in nodes if degree.get(str(node["id"]), 0) > 0]
    removed = len(nodes) - len(kept)
    return kept, removed


def dedupe_graph(
    graph: dict[str, Any], *, prune_isolated: bool
) -> dict[str, Any]:
    nodes = list(graph.get("nodes", []))
    links = link_list(graph)

    merged_nodes, id_map, merge_count = merge_duplicate_nodes(nodes)
    merged_links = rewire_links(links, id_map)

    pruned = 0
    if prune_isolated:
        merged_nodes, pruned = prune_isolated_nodes(merged_nodes, merged_links)

    result = dict(graph)
    result["nodes"] = merged_nodes
    set_link_list(result, merged_links)
    result["_dedupe"] = {
        "merged_nodes": merge_count,
        "pruned_isolated": pruned,
    }
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge duplicate graphify concepts and optionally prune isolated nodes."
    )
    parser.add_argument(
        "--graph",
        type=Path,
        default=Path("graphify-out/graph.json"),
        help="Path to graph.json (default: graphify-out/graph.json)",
    )
    parser.add_argument(
        "--prune-isolated",
        action="store_true",
        help="Remove nodes with zero link degree after deduplication",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stats without writing graph.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    graph_path = args.graph
    if not graph_path.is_file():
        print(f"Graph not found: {graph_path}", file=sys.stderr)
        return 1

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    before_nodes = len(graph.get("nodes", []))
    before_links = len(link_list(graph))
    before_isolated = len(
        [
            node
            for node in graph.get("nodes", [])
            if degree_by_node(link_list(graph)).get(str(node["id"]), 0) == 0
        ]
    )

    result = dedupe_graph(graph, prune_isolated=args.prune_isolated)
    stats = result.pop("_dedupe", {})
    after_nodes = len(result.get("nodes", []))
    after_links = len(link_list(result))
    after_isolated = len(
        [
            node
            for node in result.get("nodes", [])
            if degree_by_node(link_list(result)).get(str(node["id"]), 0) == 0
        ]
    )

    print(
        f"nodes {before_nodes} -> {after_nodes} "
        f"(merged {stats.get('merged_nodes', 0)}, pruned {stats.get('pruned_isolated', 0)})"
    )
    print(
        f"links {before_links} -> {after_links}; "
        f"isolated {before_isolated} -> {after_isolated}"
    )

    if args.dry_run:
        return 0

    graph_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
