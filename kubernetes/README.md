# Kubernetes MCP server

A small MCP server that wraps `kubectl` so Claude Code can inspect your cluster
and remediate common problems.

## Prerequisites

- `kubectl` on PATH, with a working kubeconfig (whatever context is current is
  the one Claude will touch — check with `kubectl config current-context`).
- Python 3.10+.

## Install

```bash
python3 -m venv ~/.claude/mcp-servers/kubernetes/.venv
~/.claude/mcp-servers/kubernetes/.venv/bin/pip install -r ~/.claude/mcp-servers/kubernetes/requirements.txt
```

## Register with Claude Code

```bash
claude mcp add kubernetes \
  ~/.claude/mcp-servers/kubernetes/.venv/bin/python \
  ~/.claude/mcp-servers/kubernetes/server.py \
  --scope user
```

Or, equivalently, add this to `~/.claude.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "/home/eli/.claude/mcp-servers/kubernetes/.venv/bin/python",
      "args": ["/home/eli/.claude/mcp-servers/kubernetes/server.py"]
    }
  }
}
```

Restart Claude Code (or `/mcp` reconnect) to pick it up.

## Tools

Read-only:
- `current_context` — which cluster am I talking to
- `list_pods`, `describe_pod`, `get_pod_logs`
- `get_events`, `get_nodes`, `get_deployments`, `get_services`
- `get_resource` — generic get for any kind
- `diagnose_pod` — describe + events + current/previous logs in one call

Write (cluster-mutating):
- `restart_deployment`, `rollout_status`, `scale_deployment`
- `delete_pod`, `rollback_deployment`
- `apply_manifest`

## Safety

Write tools act on whatever `kubectl config current-context` points to. Verify
your context before letting Claude run them. The `k8s-troubleshoot` skill (see
`~/.claude/skills/k8s-troubleshoot/`) tells Claude to diagnose before mutating.
