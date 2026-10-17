# Kubernetes MCP Server Setup

## Instruction

> set @/home/eli/.claude/mcp-servers/kubernetes as mcp server

## What was done

### 1. Inspected the server directory

`~/.claude/mcp-servers/kubernetes/` contains:

- `server.py`: MCP server that wraps `kubectl`, written for `mcp` SDK v2 (`from mcp.server.mcpserver import MCPServer`)
- `requirements.txt`: `mcp>=2.0`
- `install.sh` / `package.sh`: install and migration helpers
- `README.md`, `MIGRATION.md`: docs

There was no `.venv` yet.

### 2. Built the Python environment

```bash
D=~/.claude/mcp-servers/kubernetes
python3 -m venv $D/.venv
$D/.venv/bin/pip install --quiet --upgrade pip
$D/.venv/bin/pip install --quiet -r $D/requirements.txt
$D/.venv/bin/python -c "from mcp.server.mcpserver import MCPServer; print('import ok')"
```

Result: Python 3.14.4, and the SDK import works.

### 3. Registered the server with Claude Code (user scope)

```bash
claude mcp add kubernetes --scope user -- \
  ~/.claude/mcp-servers/kubernetes/.venv/bin/python \
  ~/.claude/mcp-servers/kubernetes/server.py
```

I used `claude mcp add` instead of `install.sh` because the script rewrites
`~/.claude.json` directly, which isn't safe while Claude Code is running.

Verification (`claude mcp get kubernetes`):

```
kubernetes:
  Scope: User config (available in all your projects)
  Status: ✔ Connected
  Type: stdio
  Command: /home/eli/.claude/mcp-servers/kubernetes/.venv/bin/python
  Args: /home/eli/.claude/mcp-servers/kubernetes/server.py
```

### 4. Checked kubectl

- Binary: `/home/eli/google-cloud-sdk/bin/kubectl`
- Current context: `gke_gcp-dev-netcourt-mewest1_me-west1_gcp-dev-netcourt-gke-mewest1-k8s-02`

## Notes

- Run `/mcp` or restart Claude Code to load the tools into a session.
- **Write tools** (`restart_deployment`, `scale_deployment`, `delete_pod`,
  `rollback_deployment`, `apply_manifest`) act on the current kubectl context.
  Check it with `kubectl config current-context` before you let Claude run them.
- `kubectl` lives in `~/google-cloud-sdk/bin`. If Claude Code starts from an
  environment where that folder isn't on `PATH`, add it to the server's `env`:
  ```bash
  claude mcp remove kubernetes -s user
  claude mcp add kubernetes --scope user \
    -e PATH=/home/eli/google-cloud-sdk/bin:/usr/local/bin:/usr/bin:/bin -- \
    ~/.claude/mcp-servers/kubernetes/.venv/bin/python \
    ~/.claude/mcp-servers/kubernetes/server.py
  ```
- To remove the server: `claude mcp remove kubernetes -s user`
