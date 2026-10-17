#!/usr/bin/env bash
# Package the kubernetes MCP server for transfer to another machine.
# Produces k8s-mcp.tgz in the current directory. Excludes machine-specific
# artifacts (.venv, __pycache__). The tarball bundles its own install.sh.
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$PWD/k8s-mcp.tgz}"

cd "$(dirname "$SRC_DIR")"
tar czf "$OUT" \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='k8s-mcp.tgz' \
  "$(basename "$SRC_DIR")"

echo "Wrote $OUT"
echo
echo "On the new machine:"
echo "  tar xzf $(basename "$OUT") -C \"\$HOME/.claude/mcp-servers\"  # creates ~/.claude/mcp-servers/kubernetes"
echo "  bash \"\$HOME/.claude/mcp-servers/kubernetes/install.sh\""
