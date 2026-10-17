#!/usr/bin/env bash
# Install the kubernetes MCP server on this machine.
# - Creates a venv next to this script and installs requirements.txt
# - Registers the server in ~/.claude.json (merging, not overwriting)
# - Checks kubectl + kubeconfig
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SRC_DIR/.venv"
SERVER_PY="$SRC_DIR/server.py"
CLAUDE_JSON="$HOME/.claude.json"

echo "==> Server directory: $SRC_DIR"

# --- Python venv ---------------------------------------------------------
if ! command -v python3 >/dev/null; then
  echo "ERROR: python3 not found on PATH" >&2
  exit 1
fi
PY_MINOR="$(python3 -c 'import sys; print(sys.version_info[1])')"
PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info[0])')"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  echo "ERROR: need Python 3.10+ (found $(python3 -V))" >&2
  exit 1
fi

if [ ! -d "$VENV" ]; then
  echo "==> Creating venv at $VENV"
  python3 -m venv "$VENV"
fi
echo "==> Installing requirements"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$SRC_DIR/requirements.txt"

# Smoke-test import
"$VENV/bin/python" -c "from mcp.server.mcpserver import MCPServer" || {
  echo "ERROR: mcp SDK import failed after install" >&2
  exit 1
}

# --- Register with Claude Code ------------------------------------------
echo "==> Registering MCP server in $CLAUDE_JSON"
PY="$VENV/bin/python" SERVER_PY="$SERVER_PY" CLAUDE_JSON="$CLAUDE_JSON" \
"$VENV/bin/python" <<'PYEOF'
import json, os, pathlib, sys
path = pathlib.Path(os.environ["CLAUDE_JSON"])
cfg = json.loads(path.read_text()) if path.exists() else {}
cfg.setdefault("mcpServers", {})
cfg["mcpServers"]["kubernetes"] = {
    "type": "stdio",
    "command": os.environ["PY"],
    "args": [os.environ["SERVER_PY"]],
    "env": {},
}
path.write_text(json.dumps(cfg, indent=2))
print(f"   wrote mcpServers.kubernetes -> {os.environ['PY']}")
PYEOF

# --- kubectl prereq check -----------------------------------------------
echo "==> Checking kubectl"
if ! command -v kubectl >/dev/null; then
  echo "WARNING: kubectl not found on PATH — install it before using the server" >&2
elif ! kubectl config current-context >/dev/null 2>&1; then
  echo "WARNING: kubectl has no current context — set up ~/.kube/config" >&2
else
  echo "   current context: $(kubectl config current-context)"
fi

echo
echo "Done. Restart Claude Code (or run /mcp) to connect."
