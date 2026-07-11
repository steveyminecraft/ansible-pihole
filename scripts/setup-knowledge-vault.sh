#!/usr/bin/env bash
# Bootstrap local graphify knowledge vault (graphify-out/ is gitignored).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FULL=0
INSTALL_HOOK=0
for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    --hook) INSTALL_HOOK=1 ;;
    -h|--help)
      cat <<'EOF'
Usage: ./scripts/setup-knowledge-vault.sh [--full] [--hook]

  (default)  Install graphify if needed, run graphify update (code/AST graph),
             export HTML + Obsidian when graph.json exists.
  --full     Print how to run a full /graphify . build for YAML/docs coverage.
  --hook     Also run: graphify hook install (post-commit code graph refresh).

graphify-out/ is local only — not committed to git.
See docs/knowledge-vault.md.
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $arg (try --help)" >&2
      exit 1
      ;;
  esac
done

ensure_graphify() {
  if command -v graphify >/dev/null 2>&1; then
    return 0
  fi
  if command -v uv >/dev/null 2>&1; then
    echo "Installing graphify via uv tool..."
    uv tool install --upgrade graphifyy -q
    return 0
  fi
  echo "graphify not found. Install with: uv tool install graphifyy" >&2
  echo "Or: pip install graphifyy" >&2
  exit 1
}

write_local_index() {
  mkdir -p graphify-out
  local nodes edges communities commit
  nodes="$(python3 -c "import json; g=json.load(open('graphify-out/graph.json')); print(len(g.get('nodes',[])))" 2>/dev/null || echo '?')"
  edges="$(python3 -c "import json; g=json.load(open('graphify-out/graph.json')); print(len(g.get('links', g.get('edges',[]))))" 2>/dev/null || echo '?')"
  communities="$(python3 -c "import json; g=json.load(open('graphify-out/graph.json')); print(len({n.get('community') for n in g.get('nodes',[]) if n.get('community') is not None}))" 2>/dev/null || echo '?')"
  commit="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"

  {
    cat "$ROOT/docs/knowledge-vault.md"
    echo ""
    echo "---"
    echo ""
    echo "## Local build"
    echo ""
    echo "- **Built:** $(date -u +%Y-%m-%d) · **Graph:** ${nodes} nodes · ${edges} edges · ${communities} communities · commit \`${commit}\`"
    echo "- **Regenerate:** \`./scripts/setup-knowledge-vault.sh\` or \`/graphify .\` for full corpus"
  } > graphify-out/KNOWLEDGE_VAULT.md

  if [[ -d graphify-out/obsidian ]]; then
    cp graphify-out/KNOWLEDGE_VAULT.md "graphify-out/obsidian/00 - Knowledge Vault Index.md"
    python3 "$ROOT/scripts/sync-obsidian-documentation.py"
  fi
}

ensure_graphify

if [[ "$FULL" -eq 1 ]]; then
  cat <<'EOF'

Full graphify build (Ansible YAML, markdown docs, rich Obsidian vault):

  In Cursor, run:  /graphify .

Or invoke the graphify skill on this repo root. That extracts the full corpus
(roles, playbooks, molecule scenarios, docs) — not just Python/shell AST.

Optional: export GEMINI_API_KEY for unattended semantic extraction.

After the agent build finishes:
  graphify export html
  graphify export obsidian
  ./scripts/setup-knowledge-vault.sh   # refresh KNOWLEDGE_VAULT.md index

EOF
  if [[ -f graphify-out/graph.json ]]; then
    echo "graphify-out/graph.json already exists ($(wc -c < graphify-out/graph.json) bytes)."
    echo "Delete graphify-out/ and re-run /graphify . for a clean full rebuild."
  fi
  exit 0
fi

echo "Building local code graph (graphify update)..."
graphify update .

write_local_index

echo "Exporting HTML..."
graphify export html

if [[ -f graphify-out/graph.json ]]; then
  echo "Exporting Obsidian vault..."
  graphify export obsidian
  echo "Syncing full documentation into Obsidian..."
  python3 "$ROOT/scripts/sync-obsidian-documentation.py"
  write_local_index
fi

if [[ "$INSTALL_HOOK" -eq 1 ]]; then
  "$ROOT/scripts/install-graphify-hook.sh"
fi

cat <<EOF

Knowledge vault ready under graphify-out/ (local, gitignored).

  graphify-out/graph.html
  graphify-out/GRAPH_REPORT.md
  graphify-out/KNOWLEDGE_VAULT.md
  graphify-out/obsidian/

For full YAML/docs coverage: ./scripts/setup-knowledge-vault.sh --full
Docs: docs/knowledge-vault.md
EOF
