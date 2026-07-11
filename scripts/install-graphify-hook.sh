#!/usr/bin/env bash
# Install graphify post-commit hook for local knowledge vault refresh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

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
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: ./scripts/install-graphify-hook.sh

Installs graphify git hooks (post-commit code graph refresh, post-checkout).
Local only — nothing is committed to the repository.

Requires graphify (installed automatically via uv when available).
See docs/knowledge-vault.md.
EOF
  exit 0
fi

ensure_graphify

if [[ ! -f graphify-out/graph.json ]]; then
  echo "graphify-out/graph.json missing — bootstrapping local graph first..."
  "$ROOT/scripts/setup-knowledge-vault.sh"
fi

graphify hook install
graphify hook status

cat <<'EOF'

Post-commit hook installed. After each commit, graphify re-extracts changed
Python/shell files into graphify-out/graph.json.

For roles, playbooks, or docs changes, run a full rebuild: /graphify .
EOF
