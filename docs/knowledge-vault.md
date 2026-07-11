# Knowledge vault (local graphify)

This collection can be mapped with [graphify](https://github.com/safishamsi/graphify) into a **local** knowledge graph. Outputs stay on your machine under `graphify-out/` (gitignored) so nothing is pushed to GitHub.

Agents and contributors use the graph for architecture questions; humans can browse the Obsidian vault or `graph.html`.

## Quick start

```bash
# From repo root — installs graphify if needed, builds code graph, exports HTML/Obsidian
./scripts/setup-knowledge-vault.sh

# Optional: rebuild code graph after every commit (local only)
./scripts/install-graphify-hook.sh
# Or: ./scripts/setup-knowledge-vault.sh --hook
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
| Python/shell | `graphify update .` (automatic with post-commit hook) |
| Roles, playbooks, docs | `/graphify .` or full rebuild |
| After full rebuild | `python3 scripts/dedupe-graphify-graph.py --prune-isolated` |
| Re-export Obsidian | `graphify export obsidian` |
| Re-export HTML | `graphify export html` |

### Post-commit hook

```bash
./scripts/install-graphify-hook.sh
```

Installs graphify's post-commit hook locally. After each commit, changed Python/shell
files are re-extracted into `graphify-out/graph.json`. Doc and YAML changes still
need a full `/graphify .` rebuild.

Check status: `graphify hook status`

### Reduce graph noise

Duplicate concepts (e.g. `update-pihole.yaml` in docs vs `update-pihole playbook`
in playbooks) can appear after a full corpus build. Run a dedupe pass:

```bash
python3 scripts/dedupe-graphify-graph.py --dry-run          # preview
python3 scripts/dedupe-graphify-graph.py                    # merge duplicates
python3 scripts/dedupe-graphify-graph.py --prune-isolated  # also drop isolated nodes
```

Prefer a periodic full rebuild (`/graphify .`) then dedupe, rather than incremental
AST-only updates when exploring roles and playbooks.

## Cursor MCP (optional)

Agents can query the graph via MCP instead of shelling out to `graphify query`.

1. Bootstrap the vault: `./scripts/setup-knowledge-vault.sh`
2. Copy `.cursor/mcp.json.example` to `.cursor/mcp.json` (gitignored)
3. Replace `GRAPHIFY_PYTHON` and `GRAPH_PATH` with values from your machine:

```bash
cat graphify-out/.graphify_python   # interpreter path
realpath graphify-out/graph.json    # absolute graph path
```

4. Reload Cursor MCP servers

Tools exposed: `query_graph`, `get_node`, `get_neighbors`, `get_community`,
`god_nodes`, `graph_stats`, `shortest_path`.

## Security

- `graphify-out/` is **not committed** — lab fixture passwords in inventory YAML stay out of any graph artifact on GitHub.
- Graphify skips `.env`, keys, and `secrets/` paths during detection.
- Before sharing `graphify-out/` manually, scan for accidental secrets.

## Role deployment chain (reference)

```
stop_keepalived → bootstrap → updates → sshd → keepalived → docker → unbound → pihole
```

Key playbooks: `playbooks/bootstrap-pihole.yaml`, `sync.yaml`, `update-pihole.yaml`, `keepalived.yaml`.
