# mcp-servers

A collection of [Model Context Protocol](https://modelcontextprotocol.io) (MCP)
servers that give Claude Code (and other MCP clients) real capabilities against
local tools and infrastructure.

Each subdirectory is a self-contained server with its own code, dependencies,
and install helpers.

## Servers

| Server | What it does | Docs |
|---|---|---|
| [`kubernetes/`](kubernetes/) | Wraps `kubectl` so the agent can inspect a cluster and remediate common problems (CrashLoopBackOff, scaling, rollbacks, restarts, manifest apply). | [README](kubernetes/README.md) · [Migration](kubernetes/MIGRATION.md) |

## Requirements

- **Python 3.10+**
- **Claude Code** (or any MCP-compatible client) installed, so there is a
  `~/.claude.json` to register servers into
- Whatever each server shells out to — e.g. the `kubernetes` server needs
  `kubectl` on `PATH` with a working `~/.kube/config`

## Install

Each server bundles an `install.sh` that builds a virtualenv, installs its
dependencies, and registers the server with Claude Code. Using the
`kubernetes` server as the example:

```bash
# 1. Clone the repo
git clone <this-repo-url> mcp-servers
cd mcp-servers

# 2. Run the server's installer
bash kubernetes/install.sh
```

`install.sh` is idempotent and does four things:

1. Verifies Python 3.10+.
2. Creates `kubernetes/.venv/` and installs `kubernetes/requirements.txt`.
3. Merges an `mcpServers.kubernetes` entry into `~/.claude.json` (it parses the
   JSON, so existing servers and config are preserved).
4. Checks `kubectl` and warns if it's missing or has no current context.

### Manual install

If you'd rather not run the script:

```bash
python3 -m venv kubernetes/.venv
kubernetes/.venv/bin/pip install -r kubernetes/requirements.txt

claude mcp add kubernetes --scope user -- \
  "$PWD/kubernetes/.venv/bin/python" \
  "$PWD/kubernetes/server.py"
```

Or add this block to `~/.claude.json` under `mcpServers` (use absolute paths):

```json
{
  "mcpServers": {
    "kubernetes": {
      "type": "stdio",
      "command": "/absolute/path/to/mcp-servers/kubernetes/.venv/bin/python",
      "args": ["/absolute/path/to/mcp-servers/kubernetes/server.py"]
    }
  }
}
```

## Use

After installing, restart Claude Code (or run `/mcp` in a session) to connect.
Run `/mcp` to confirm the server shows as **connected**, then ask the agent to
use its tools — for example:

> List all pods that aren't Running, then diagnose the first failing one.

The `kubernetes` server exposes read-only tools (`list_pods`, `describe_pod`,
`get_pod_logs`, `get_events`, `get_nodes`, `diagnose_pod`, …) and
cluster-mutating tools (`restart_deployment`, `scale_deployment`, `delete_pod`,
`rollback_deployment`, `apply_manifest`). See
[kubernetes/README.md](kubernetes/README.md) for the full tool list.

### Verify a server runs

If a server shows as disconnected, run it directly to read the real error —
a clean exit (no traceback) means the problem is on the client side:

```bash
kubernetes/.venv/bin/python kubernetes/server.py < /dev/null
```

## Safety

Mutating tools act on **whatever context `kubectl config current-context`
points to**. Verify your context before letting the agent run them:

```bash
kubectl config current-context
```

## Moving a server to another machine

Servers are stateless (just code that shells out to a CLI). Use the bundled
`package.sh` / `install.sh` helpers — see
[kubernetes/MIGRATION.md](kubernetes/MIGRATION.md) for the full walkthrough.

## Uninstall

```bash
# remove the registration (preserves the rest of ~/.claude.json)
claude mcp remove kubernetes -s user

# remove the virtualenv
rm -rf kubernetes/.venv
```

## Adding a new server

Create a new subdirectory with a `server.py`, a `requirements.txt`, and an
`install.sh` modeled on `kubernetes/`, then add a row to the **Servers** table
above.
