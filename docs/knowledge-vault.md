# Knowledge vault (local graphify)

This collection can be mapped with [graphify](https://github.com/safishamsi/graphify) into a **local** knowledge graph. Outputs stay on your machine under `graphify-out/` (gitignored) so nothing is pushed to GitHub.

Agents and contributors use the graph for architecture questions; humans can browse the Obsidian vault or `graph.html`.

## Quick start

```bash
# From repo root — installs graphify if needed, builds code graph, exports HTML/Obsidian
./scripts/setup-knowledge-vault.sh

# Optional: rebuild code graph after every commit (local only)
graphify hook install
```

Open the interactive map: `graphify-out/graph.html`  
Open Obsidian vault: `graphify-out/obsidian/`

## What gets generated (all local)

| Path | Purpose |
|------|---------|
| `graphify-out/graph.json` | Query target for agents (`graphify query`, MCP) |
| `graphify-out/graph.html` | Browser visualization |
| `graphify-out/GRAPH_REPORT.md` | God nodes, communities, surprising connections |
| `graphify-out/KNOWLEDGE_VAULT.md` | Local entry point (copied from this doc + build stats) |
| `graphify-out/obsidian/` | Wikilinked notes + `graph.canvas` |

## Bootstrap modes

### Fast (default) — no API key

`./scripts/setup-knowledge-vault.sh`

Runs `graphify update .`: AST extraction for Python/shell **code** only. Good for scripts and unit tests. Ansible YAML and markdown are not fully covered until a full build.

### Full — docs, roles, playbooks, Obsidian

`./scripts/setup-knowledge-vault.sh --full`

Prints instructions to run **`/graphify .`** in Cursor (or any graphify-capable agent). That pipeline extracts all 180+ corpus files, merges semantic + AST edges, and is the same process used to produce the rich HA/role/playbook map.

Optional: set `GEMINI_API_KEY` or `GOOGLE_API_KEY` for automated semantic extraction instead of agent subagents.

## Agent workflow

Cursor rule `.cursor/rules/graphify-knowledge-base.mdc` tells agents to:

1. Check for `graphify-out/graph.json`
2. Run `./scripts/setup-knowledge-vault.sh` if missing
3. Use `graphify query` before `Grep`/`Read` for architecture questions
4. Run `graphify update .` after code edits

Example queries:

```bash
graphify query "How does HA failover work?"
graphify path "playbooks/bootstrap-pihole.yaml" "nebula_sync"
graphify explain "molecule/default/molecule.yml"
```

## Refresh after changes

| Change type | Command |
|-------------|---------|
| Python/shell | `graphify update .` |
| Roles, playbooks, docs | `/graphify .` or full rebuild |
| Re-export Obsidian | `graphify export obsidian` |
| Re-export HTML | `graphify export html` |

## Security

- `graphify-out/` is **not committed** — lab fixture passwords in inventory YAML stay out of any graph artifact on GitHub.
- Graphify skips `.env`, keys, and `secrets/` paths during detection.
- Before sharing `graphify-out/` manually, scan for accidental secrets.

## Role deployment chain (reference)

```
stop_keepalived → bootstrap → updates → sshd → keepalived → docker → unbound → pihole
```

Key playbooks: `playbooks/bootstrap-pihole.yaml`, `sync.yaml`, `update-pihole.yaml`, `keepalived.yaml`.
