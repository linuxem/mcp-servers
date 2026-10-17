#!/usr/bin/env python3
"""Kubernetes MCP server — inspect and remediate cluster issues via kubectl."""
from __future__ import annotations

import json
import subprocess
from typing import Optional

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("kubernetes")

KUBECTL_TIMEOUT = 60


def _kubectl(args: list[str], stdin: Optional[str] = None) -> dict:
    try:
        result = subprocess.run(
            ["kubectl", *args],
            capture_output=True,
            text=True,
            input=stdin,
            timeout=KUBECTL_TIMEOUT,
        )
    except FileNotFoundError:
        return {"error": "kubectl not found on PATH"}
    except subprocess.TimeoutExpired:
        return {"error": f"kubectl timed out after {KUBECTL_TIMEOUT}s", "args": args}
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@mcp.tool()
def list_pods(
    namespace: str = "default",
    all_namespaces: bool = False,
    status: Optional[str] = None,
) -> str:
    """List pods with wide output. all_namespaces=True spans the cluster. status
    filters by phase: Running, Pending, Failed, Succeeded, Unknown."""
    args = ["get", "pods", "-o", "wide"]
    if all_namespaces:
        args.append("-A")
    else:
        args.extend(["-n", namespace])
    if status:
        args.extend(["--field-selector", f"status.phase={status}"])
    return json.dumps(_kubectl(args), indent=2)


@mcp.tool()
def describe_pod(name: str, namespace: str = "default") -> str:
    """Describe a pod — containers, conditions, recent events, volumes."""
    return json.dumps(_kubectl(["describe", "pod", name, "-n", namespace]), indent=2)


@mcp.tool()
def get_pod_logs(
    name: str,
    namespace: str = "default",
    container: Optional[str] = None,
    tail: int = 200,
    previous: bool = False,
) -> str:
    """Fetch pod logs. previous=True reads the prior crashed container, which is
    the only way to see why a CrashLoopBackOff pod died."""
    args = ["logs", name, "-n", namespace, f"--tail={tail}"]
    if container:
        args.extend(["-c", container])
    if previous:
        args.append("--previous")
    return json.dumps(_kubectl(args), indent=2)


@mcp.tool()
def get_events(
    namespace: Optional[str] = None,
    warnings_only: bool = False,
) -> str:
    """Recent events, newest last. warnings_only filters to type=Warning."""
    args = ["get", "events", "--sort-by=.lastTimestamp"]
    if namespace:
        args.extend(["-n", namespace])
    else:
        args.append("-A")
    if warnings_only:
        args.extend(["--field-selector", "type=Warning"])
    return json.dumps(_kubectl(args), indent=2)


@mcp.tool()
def get_nodes() -> str:
    """Node status and conditions across the cluster."""
    return json.dumps(_kubectl(["get", "nodes", "-o", "wide"]), indent=2)


@mcp.tool()
def get_deployments(namespace: str = "default", all_namespaces: bool = False) -> str:
    """Deployments with ready/updated/available counts."""
    args = ["get", "deployments", "-o", "wide"]
    if all_namespaces:
        args.append("-A")
    else:
        args.extend(["-n", namespace])
    return json.dumps(_kubectl(args), indent=2)


@mcp.tool()
def get_services(namespace: str = "default", all_namespaces: bool = False) -> str:
    """Services with cluster/external IPs and ports."""
    args = ["get", "services", "-o", "wide"]
    if all_namespaces:
        args.append("-A")
    else:
        args.extend(["-n", namespace])
    return json.dumps(_kubectl(args), indent=2)


@mcp.tool()
def diagnose_pod(name: str, namespace: str = "default") -> str:
    """One-shot pod diagnosis: describe + pod-scoped events + current and previous
    logs. Call this first for any misbehaving pod — it collects everything needed
    to classify CrashLoopBackOff, ImagePullBackOff, OOMKilled, scheduling failures."""
    describe = _kubectl(["describe", "pod", name, "-n", namespace])
    events = _kubectl([
        "get", "events", "-n", namespace,
        "--field-selector", f"involvedObject.name={name}",
        "--sort-by=.lastTimestamp",
    ])
    logs_current = _kubectl(["logs", name, "-n", namespace, "--tail=100"])
    logs_previous = _kubectl(["logs", name, "-n", namespace, "--tail=100", "--previous"])
    return json.dumps(
        {
            "describe": describe,
            "events": events,
            "logs_current": logs_current,
            "logs_previous": logs_previous,
        },
        indent=2,
    )


@mcp.tool()
def restart_deployment(name: str, namespace: str = "default") -> str:
    """Rolling restart a deployment — kicks a fresh rollout of all pods."""
    return json.dumps(
        _kubectl(["rollout", "restart", f"deployment/{name}", "-n", namespace]),
        indent=2,
    )


@mcp.tool()
def rollout_status(name: str, namespace: str = "default", timeout: str = "60s") -> str:
    """Watch a deployment rollout until complete or timeout."""
    return json.dumps(
        _kubectl([
            "rollout", "status", f"deployment/{name}",
            "-n", namespace, f"--timeout={timeout}",
        ]),
        indent=2,
    )


@mcp.tool()
def scale_deployment(name: str, replicas: int, namespace: str = "default") -> str:
    """Scale a deployment to replicas."""
    return json.dumps(
        _kubectl([
            "scale", f"deployment/{name}",
            f"--replicas={replicas}", "-n", namespace,
        ]),
        indent=2,
    )


@mcp.tool()
def delete_pod(name: str, namespace: str = "default") -> str:
    """Delete a pod. Deployment/ReplicaSet-managed pods get recreated — useful to
    force a single restart without rolling the whole deployment."""
    return json.dumps(_kubectl(["delete", "pod", name, "-n", namespace]), indent=2)


@mcp.tool()
def rollback_deployment(
    name: str,
    namespace: str = "default",
    to_revision: Optional[int] = None,
) -> str:
    """Roll a deployment back to its previous revision (or a specific one)."""
    args = ["rollout", "undo", f"deployment/{name}", "-n", namespace]
    if to_revision is not None:
        args.append(f"--to-revision={to_revision}")
    return json.dumps(_kubectl(args), indent=2)


@mcp.tool()
def apply_manifest(yaml_content: str, namespace: Optional[str] = None) -> str:
    """Apply a Kubernetes manifest from a YAML string via `kubectl apply -f -`."""
    args = ["apply", "-f", "-"]
    if namespace:
        args.extend(["-n", namespace])
    return json.dumps(_kubectl(args, stdin=yaml_content), indent=2)


@mcp.tool()
def get_resource(
    kind: str,
    name: Optional[str] = None,
    namespace: str = "default",
    output: str = "yaml",
) -> str:
    """Generic get for any resource kind (configmap, secret, ingress, pvc, etc.).
    output: yaml, json, wide, name."""
    args = ["get", kind]
    if name:
        args.append(name)
    args.extend(["-n", namespace, "-o", output])
    return json.dumps(_kubectl(args), indent=2)


@mcp.tool()
def current_context() -> str:
    """Which cluster/context kubectl is talking to."""
    return json.dumps(_kubectl(["config", "current-context"]), indent=2)


if __name__ == "__main__":
    mcp.run()
