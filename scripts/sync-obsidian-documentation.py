#!/usr/bin/env python3
"""Copy repository documentation into the local Obsidian vault with graph links."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_graph_labels(graph_path: Path) -> dict[str, list[str]]:
    if not graph_path.is_file():
        return {}
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    labels_by_source: dict[str, list[str]] = {}
    for node in graph.get("nodes", []):
        source = (node.get("source_file") or node.get("path") or "").replace("\\", "/")
        label = (node.get("label") or "").strip()
        if not source or not label:
            continue
        labels_by_source.setdefault(source, [])
        if label not in labels_by_source[source]:
            labels_by_source[source].append(label)
    return labels_by_source


def wikilink(label: str) -> str:
    return f"[[{label.replace(']]', '')}]]"


def vault_link(dest: Path, obsidian_dir: Path) -> str:
    rel = dest.relative_to(obsidian_dir).with_suffix("")
    return f"[[{rel.as_posix()}]]"


def frontmatter(rel_path: str, labels: list[str]) -> str:
    lines = [
        "---",
        f'source_file: "{rel_path}"',
        "tags:",
        "  - documentation",
        "  - graphify/source",
    ]
    if labels:
        lines.append("graph_connections:")
        for label in labels:
            lines.append(f'  - "{label}"')
    lines.extend(["---", ""])
    return "\n".join(lines)


def graph_banner(labels: list[str]) -> str:
    if not labels:
        return ""
    links = " · ".join(wikilink(label) for label in labels[:6])
    more = f" (+{len(labels) - 6} more)" if len(labels) > 6 else ""
    return f"> **Graph connections:** {links}{more}\n\n"


def sync_file(
    source: Path,
    dest: Path,
    rel_path: str,
    labels_by_source: dict[str, list[str]],
) -> tuple[str, Path, list[str]]:
    labels = labels_by_source.get(rel_path, [])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        frontmatter(rel_path, labels) + graph_banner(labels) + source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return rel_path, dest, labels


def build_index(
    entries: list[tuple[str, Path, list[str]]],
    obsidian_dir: Path,
) -> None:
    lines = [
        "---",
        "tags:",
        "  - documentation",
        "  - graphify/index",
        "---",
        "",
        "# Documentation",
        "",
        "Full-text copies of repository docs, linked to graphify concept notes.",
        "",
        "Vault hub: [[00 - Knowledge Vault Index]]",
        "",
        "## All documentation",
        "",
    ]
    for rel_path, dest, labels in sorted(entries, key=lambda item: item[0]):
        graph = ""
        if labels:
            graph = " — " + ", ".join(wikilink(label) for label in labels[:3])
        lines.append(f"- `{rel_path}` → {vault_link(dest, obsidian_dir)}{graph}")

    lines.extend(
        [
            "",
            "## Graph communities",
            "",
            "- [[_COMMUNITY_Architecture & Docs]]",
            "- [[_COMMUNITY_CI & Release Workflow]]",
            "- [[_COMMUNITY_HA Failover Testing]]",
            "",
            "#documentation #graphify/index",
        ]
    )
    (obsidian_dir / "00 - Documentation Index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_documentation(
    repo_root: Path,
    obsidian_dir: Path,
    graph_path: Path | None = None,
) -> int:
    labels_by_source = load_graph_labels(graph_path or obsidian_dir.parent / "graph.json")
    entries: list[tuple[str, Path, list[str]]] = []

    for src in sorted((repo_root / "docs").glob("**/*.md")):
        rel = str(src.relative_to(repo_root)).replace("\\", "/")
        dest = obsidian_dir / "Documentation" / src.relative_to(repo_root / "docs")
        entries.append(sync_file(src, dest, rel, labels_by_source))

    for name in ("README.md", "CONTRIBUTING.md", "CHANGELOG.md"):
        src = repo_root / name
        if src.is_file():
            entries.append(sync_file(src, obsidian_dir / "Documentation" / name, name, labels_by_source))

    for readme in sorted(repo_root.glob("roles/*/README.md")):
        role = readme.parent.name
        rel = str(readme.relative_to(repo_root)).replace("\\", "/")
        dest = obsidian_dir / "Documentation" / "roles" / role / "README.md"
        entries.append(sync_file(readme, dest, rel, labels_by_source))

    remote = repo_root / "tests" / "remote" / "README.md"
    if remote.is_file():
        rel = "tests/remote/README.md"
        dest = obsidian_dir / "Documentation" / "tests" / "remote" / "README.md"
        entries.append(sync_file(remote, dest, rel, labels_by_source))

    build_index(entries, obsidian_dir)
    return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--obsidian-dir", type=Path, default=None)
    parser.add_argument("--graph", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    obsidian_dir = (args.obsidian_dir or repo_root / "graphify-out" / "obsidian").resolve()
    graph_path = (args.graph or repo_root / "graphify-out" / "graph.json").resolve()

    if not obsidian_dir.is_dir():
        print(f"Obsidian vault not found: {obsidian_dir}")
        print("Run: graphify export obsidian")
        return 1

    count = sync_documentation(repo_root, obsidian_dir, graph_path)
    print(f"Synced {count} documentation files to {obsidian_dir / 'Documentation'}/")
    print(f"Index: {obsidian_dir / '00 - Documentation Index.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
