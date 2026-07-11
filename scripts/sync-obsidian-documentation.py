#!/usr/bin/env python3
"""Copy repository documentation into the local Obsidian vault with graph links."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

DIAGRAM_ASSETS = ("ansible-pihole-layers.png", "ansible-pihole-layers.drawio")

LAYER_GUIDE: list[tuple[str, str, list[str]]] = [
    (
        "1 · Development & CI",
        "Entry points: operator runs, GitHub Actions, Molecule, AWS remote tests, scripts, docs, unit tests.",
        [
            "Documentation/testing",
            "Documentation/ci-workflows/ci",
            "Documentation/ci-workflows/aws-remote-tests",
            "Documentation/ci-workflows/security",
            "Documentation/ci-workflows/galaxy-publish",
            "Documentation/ci-workflows/release-please",
        ],
    ),
    (
        "2 · Playbooks",
        "Orchestration playbooks: bootstrap, rolling update, keepalived, sync, CI helpers.",
        [
            "Documentation/architecture",
            "Documentation/upgrade-runbook",
            "Documentation/production-deployment",
        ],
    ),
    (
        "3 · Ansible roles",
        "Collection roles: bootstrap → updates → sshd → keepalived → docker → unbound → pihole (+ nebula_sync).",
        [
            "Documentation/knowledge-vault",
            "Documentation/roles/docker/README",
            "Documentation/roles/keepalived/README",
            "Documentation/roles/pihole/README",
            "Documentation/roles/nebula_sync/README",
        ],
    ),
    (
        "4 · Inventory & variables",
        "Production, lab, CI, and remote-test inventories; group_vars and host patterns.",
        [
            "Documentation/production-deployment",
            "Documentation/tests/remote/README",
        ],
    ),
    (
        "5 · Verification",
        "Molecule scenarios (docker-ci smoke, Vagrant HA), remote verify playbooks, failover tests.",
        [
            "Documentation/testing",
            "Documentation/failover-testing",
            "Documentation/aws-remote-tests-workflow",
        ],
    ),
    (
        "6 · Runtime stack",
        "Docker-hosted Pi-hole (+ optional Unbound), Keepalived VIP, Nebula Sync replication.",
        [
            "Documentation/architecture",
            "Documentation/backup-and-restore",
            "Documentation/secrets-management",
        ],
    ),
]

CI_WORKFLOW_FILES = (
    "ci.yml",
    "security.yml",
    "galaxy-publish.yml",
    "release-please.yml",
    "auto-run-release-please-checks.yml",
    "aws-remote-tests.yml",
    "rc-aws-remote-tests.yml",
    "pihole-image-watch.yml",
)


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


def frontmatter(rel_path: str, labels: list[str], *, extra_tags: list[str] | None = None) -> str:
    lines = [
        "---",
        f'source_file: "{rel_path}"',
        "tags:",
        "  - documentation",
        "  - graphify/source",
    ]
    for tag in extra_tags or []:
        lines.append(f"  - {tag}")
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
    *,
    extra_tags: list[str] | None = None,
) -> tuple[str, Path, list[str]]:
    labels = labels_by_source.get(rel_path, [])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        frontmatter(rel_path, labels, extra_tags=extra_tags)
        + graph_banner(labels)
        + source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return rel_path, dest, labels


def sync_ci_workflow(
    source: Path,
    dest: Path,
    rel_path: str,
    labels_by_source: dict[str, list[str]],
) -> tuple[str, Path, list[str]]:
    labels = labels_by_source.get(rel_path, [])
    dest.parent.mkdir(parents=True, exist_ok=True)
    body = source.read_text(encoding="utf-8")
    dest.write_text(
        frontmatter(rel_path, labels, extra_tags=["ci-workflow"])
        + graph_banner(labels)
        + f"# {source.stem}\n\n"
        + f"Repository path: `{rel_path}`\n\n"
        + "```yaml\n"
        + body
        + "\n```\n",
        encoding="utf-8",
    )
    return rel_path, dest, labels


def sync_diagram_assets(repo_root: Path, obsidian_dir: Path) -> list[str]:
    copied: list[str] = []
    src_dir = repo_root / "docs" / "diagrams"
    if not src_dir.is_dir():
        return copied
    dest_dir = obsidian_dir / "Documentation" / "diagrams"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name in DIAGRAM_ASSETS:
        src = src_dir / name
        if src.is_file():
            shutil.copy2(src, dest_dir / name)
            copied.append(name)
    return copied


def build_architecture_ci_hub(
    obsidian_dir: Path,
    labels_by_source: dict[str, list[str]],
    diagram_assets: list[str],
) -> None:
    diagram_links = labels_by_source.get("docs/diagrams/ansible-pihole-layers.png", [])
    ci_labels = labels_by_source.get(".github/workflows/ci.yml", [])

    lines = [
        "---",
        "tags:",
        "  - documentation",
        "  - graphify/index",
        "  - architecture",
        "  - ci-workflow",
        "---",
        "",
        "# Architecture & CI",
        "",
        "Map of **project layers** (playbooks → roles → runtime) alongside the **GitHub CI workflow** surface.",
        "",
        "Vault hub: [[00 - Knowledge Vault Index]] · Docs index: [[00 - Documentation Index]]",
        "",
    ]

    if diagram_links:
        lines.append("> **Graph:** " + " · ".join(wikilink(label) for label in diagram_links[:4]) + "\n")

    if "ansible-pihole-layers.png" in diagram_assets:
        lines.extend(
            [
                "## Project layers (diagram)",
                "",
                "![[Documentation/diagrams/ansible-pihole-layers.png]]",
                "",
                "Editable source: [[Documentation/diagrams/ansible-pihole-layers.drawio]]",
                "",
                "Maintain with the draw.io skill (`.cursor/skills/drawio-skill/`) after PR #194 lands.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "## Project layers (diagram)",
                "",
                "_Diagram assets not synced yet — add `docs/diagrams/ansible-pihole-layers.{png,drawio}` "
                "(see PR #194) and re-run `python3 scripts/sync-obsidian-documentation.py`._",
                "",
            ]
        )

    lines.extend(["## Layers → vault notes", ""])
    for title, summary, vault_paths in LAYER_GUIDE:
        links = " · ".join(f"[[{path}]]" for path in vault_paths)
        lines.append(f"### {title}")
        lines.append("")
        lines.append(summary)
        lines.append("")
        lines.append(links)
        lines.append("")

    lines.extend(["## CI workflows", ""])
    if ci_labels:
        lines.append("> **Graph:** " + " · ".join(wikilink(label) for label in ci_labels[:5]) + "\n")
    lines.append("| Workflow | Vault note |")
    lines.append("|----------|------------|")
    for name in CI_WORKFLOW_FILES:
        stem = Path(name).stem
        rel = f".github/workflows/{name}"
        lines.append(f"| `{name}` | [[Documentation/ci-workflows/{stem}]] |")
    lines.extend(
        [
            "",
            "## Related graph communities",
            "",
            "- [[_COMMUNITY_Architecture & Docs]]",
            "- [[_COMMUNITY_CI & Release Workflow]]",
            "- [[_COMMUNITY_Pi-hole HA Stack]]",
            "",
            "## Draw.io skill",
            "",
            "Regenerate or extend the layer diagram with [[Draw.io Diagram Skill]] (graph node) or "
            "`.cursor/skills/drawio-skill/SKILL.md` in the repo.",
            "",
            "#architecture #ci-workflow #graphify/index",
        ]
    )
    (obsidian_dir / "00 - Architecture and CI.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_index(
    entries: list[tuple[str, Path, list[str]]],
    obsidian_dir: Path,
    diagram_assets: list[str],
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
        "**Start here for layers + CI:** [[00 - Architecture and CI]]",
        "",
    ]
    if diagram_assets:
        lines.append(
            "Layer diagram: [[Documentation/diagrams/ansible-pihole-layers.png]] "
            "(source: [[Documentation/diagrams/ansible-pihole-layers.drawio]])"
        )
        lines.append("")

    lines.extend(["## All documentation", ""])
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

    for workflow in CI_WORKFLOW_FILES:
        src = repo_root / ".github" / "workflows" / workflow
        if not src.is_file():
            continue
        rel = str(src.relative_to(repo_root)).replace("\\", "/")
        dest = obsidian_dir / "Documentation" / "ci-workflows" / f"{src.stem}.md"
        entries.append(sync_ci_workflow(src, dest, rel, labels_by_source))

    diagram_assets = sync_diagram_assets(repo_root, obsidian_dir)
    build_architecture_ci_hub(obsidian_dir, labels_by_source, diagram_assets)
    build_index(entries, obsidian_dir, diagram_assets)
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
    print(f"Hub: {obsidian_dir / '00 - Architecture and CI.md'}")
    print(f"Index: {obsidian_dir / '00 - Documentation Index.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
