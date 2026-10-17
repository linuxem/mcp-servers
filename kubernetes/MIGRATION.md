# Moving the Kubernetes MCP Server to Another Machine

This server has **no state of its own** — it's a Python script that shells out to `kubectl`. Moving it means transferring the code, rebuilding the Python environment on the new machine, and registering it with Claude Code there.

Two helper scripts automate this:

- `package.sh` — run on the **old** machine to produce a tarball
- `install.sh` — runs on the **new** machine to set everything up

---

## Prerequisites on the new machine

| Requirement | Why |
|---|---|
| Python 3.10+ | The `mcp` SDK needs it |
| `kubectl` on `PATH` | The server shells out to it for every call |
| A working `~/.kube/config` | Otherwise every tool call returns an error |
| Claude Code installed | So there's a `~/.claude.json` to register into |

Network access to PyPI is needed **once** during install (to fetch `mcp`).

---

## Step 1 — Package on the old machine

```bash
~/.claude/mcp-servers/kubernetes/package.sh
```

This writes `k8s-mcp.tgz` into your current directory. The tarball contains:

- `server.py` — the MCP server
- `requirements.txt` — Python dependencies
- `README.md` — server-tool reference
- `install.sh`, `package.sh` — the migration helpers
- `MIGRATION.md` — this file

It explicitly **excludes** `.venv/` and `__pycache__/` — those are machine-specific and get rebuilt on the other end.

You can pass a custom output path: `package.sh /tmp/my-bundle.tgz`.

Transfer the tarball to the new machine however you like:

```bash
scp k8s-mcp.tgz newhost:~/
# or rsync, Google Drive, USB stick, …
```

---

## Step 2 — Install on the new machine

```bash
mkdir -p ~/.claude/mcp-servers
tar xzf ~/k8s-mcp.tgz -C ~/.claude/mcp-servers
bash ~/.claude/mcp-servers/kubernetes/install.sh
```

`install.sh` does four things, in order:

1. **Checks Python** — refuses to continue below 3.10.
2. **Builds the venv** — creates `.venv/` next to `server.py` and installs `requirements.txt`. Smoke-tests that the `mcp` SDK imports.
3. **Registers with Claude Code** — merges a `mcpServers.kubernetes` entry into `~/.claude.json`. Uses a Python JSON parser rather than string editing, so it won't clobber other MCP servers or unrelated config. Idempotent — safe to re-run.
4. **Checks `kubectl`** — warns (does not fail) if `kubectl` is missing or has no current context, since fixing that is up to you.

The entry written into `~/.claude.json` looks like:

```json
"kubernetes": {
  "type": "stdio",
  "command": "/home/USER/.claude/mcp-servers/kubernetes/.venv/bin/python",
  "args": ["/home/USER/.claude/mcp-servers/kubernetes/server.py"],
  "env": {}
}
```

The paths use the new machine's `$HOME`, so moving between users (`eli` → `alice`) works automatically.

---

## Step 3 — Connect

Open Claude Code and run `/mcp`. The `kubernetes` server should show as connected.

If it doesn't:

```bash
# Reproduce the exact command Claude Code runs — read stderr for the real error
~/.claude/mcp-servers/kubernetes/.venv/bin/python \
  ~/.claude/mcp-servers/kubernetes/server.py < /dev/null
```

A clean process (no traceback) means the server is fine and the issue is on Claude Code's side — restart it. A traceback tells you what to fix.

---

## Common pitfalls

- **"kubectl not found"** — the server runs under Claude Code's `PATH`, which may differ from your interactive shell. If `which kubectl` works in a terminal but the server can't find it, add `"env": {"PATH": "/usr/local/bin:/usr/bin:/bin"}` (or wherever `kubectl` lives) to the entry in `~/.claude.json`.
- **"MCP error -32000: Connection closed"** — the subprocess died at startup. Run the reproducer above to see the Python traceback.
- **`mcp` SDK version mismatch** — `server.py` is written for `mcp` v2 (`from mcp.server.mcpserver import MCPServer`). If you downgrade to v1, change the import to `from mcp.server.fastmcp import FastMCP` and the instantiation to `FastMCP(...)`.
- **Shared `~/.claude.json` across machines (e.g. via dotfiles)** — the file hard-codes absolute paths to the venv's Python. If the new machine's home directory differs, re-run `install.sh` there to rewrite the paths.

---

## Uninstalling

```bash
# remove the server files
rm -rf ~/.claude/mcp-servers/kubernetes

# remove the registration (uses Python so the rest of the config is preserved)
python3 - <<'PY'
import json, pathlib
p = pathlib.Path.home() / ".claude.json"
cfg = json.loads(p.read_text())
cfg.get("mcpServers", {}).pop("kubernetes", None)
p.write_text(json.dumps(cfg, indent=2))
PY
```
