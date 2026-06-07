#!/usr/bin/env python3
# Copyright (c) 2026-06-07 RADRILONIUMA / TRIANIUMA Kingdom. All rights reserved.
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = ROOT / ".gateway" / "routing_policy.json"
GATEWAY_SCRIPT = ROOT / "scripts" / "lam_gateway.py"
MCP_PACKAGE = ROOT / "mcp_server" / "package.json"
MCP_ENTRYPOINT = ROOT / "mcp_server" / "index.js"


def run(args: list[str], timeout: int = 8) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {"ok": proc.returncode == 0, "rc": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    except FileNotFoundError:
        return {"ok": False, "rc": 127, "stdout": "", "stderr": "command not found"}
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "rc": 124,
            "stdout": exc.stdout or "",
            "stderr": f"timeout after {timeout}s",
        }


def item(name: str, status: str, detail: str, evidence: Any = None) -> dict[str, Any]:
    payload = {"name": name, "status": status, "detail": detail}
    if evidence not in (None, "", [], {}):
        payload["evidence"] = evidence
    return payload


def command_check(command: str, required: bool = True) -> dict[str, Any]:
    path = shutil.which(command)
    if path:
        return item(f"command:{command}", "PASS", f"available at {path}")
    return item(f"command:{command}", "FAIL" if required else "WARN", "not found")


def read_policy() -> dict[str, Any]:
    if not POLICY_FILE.exists():
        return {}
    return json.loads(POLICY_FILE.read_text(encoding="utf-8"))


def local_root_from_policy(policy: dict[str, Any]) -> str:
    return str(policy.get("providers", {}).get("local", {}).get("root", "")).strip()


def gateway_health() -> dict[str, Any]:
    result = run([sys.executable, str(GATEWAY_SCRIPT), "health", "--json"])
    if not result["ok"]:
        return {"ok": False, "error": result["stderr"] or result["stdout"]}
    try:
        return {"ok": True, "payload": json.loads(result["stdout"])}
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"invalid health JSON: {exc}"}


def local_health_item(policy: dict[str, Any]) -> dict[str, Any]:
    health = gateway_health()
    if not health["ok"]:
        return item("gateway:health", "FAIL", health["error"])

    providers = health["payload"].get("providers", [])
    local = next((p for p in providers if p.get("provider") == "local"), None)
    if not local:
        return item("gateway:local", "FAIL", "local provider missing from health report")

    hard_min = int(policy.get("routing", {}).get("local_hard_min_free_gb", 20))
    if not local.get("reachable"):
        return item("gateway:local", "FAIL", "local provider is not reachable", local)
    if int(local.get("free_gb", 0)) < hard_min:
        return item("gateway:local", "FAIL", f"free_gb below hard minimum {hard_min}", local)
    return item("gateway:local", "PASS", "local provider reachable with sufficient free space", local)


def mount_item(local_root: str) -> dict[str, Any]:
    if not local_root:
        return item("mount:local_root", "FAIL", "local provider root is not configured")
    result = run(["findmnt", "-T", local_root, "-o", "TARGET,SOURCE,FSTYPE,OPTIONS", "--noheadings"])
    if not result["ok"]:
        return item("mount:local_root", "FAIL", "local root is not covered by a mounted filesystem", result["stderr"])
    return item("mount:local_root", "PASS", "local root mount resolved", result["stdout"].strip())


def systemd_item(service_name: str, required_online: bool = True) -> dict[str, Any]:
    result = run(["systemctl", "show", service_name, "--property=ActiveState,SubState,MainPID,Result"], timeout=5)
    if not result["ok"]:
        return item(f"systemd:{service_name}", "FAIL" if required_online else "WARN", f"service not found or systemctl error: {result['stderr']}")
    
    props = {}
    for line in result["stdout"].splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            props[k] = v
            
    active_state = props.get("ActiveState", "unknown")
    sub_state = props.get("SubState", "unknown")
    res = props.get("Result", "unknown")
    pid = props.get("MainPID", "0")
    
    if active_state == "active":
        return item(f"systemd:{service_name}", "PASS", f"service {active_state} ({sub_state})", {"pid": pid, "status": active_state})
    
    # Handle oneshot services that exit successfully
    if active_state == "inactive" and sub_state == "dead" and res == "success":
        return item(f"systemd:{service_name}", "PASS", f"service {active_state} ({sub_state}) - last run successful", {"status": active_state, "result": res})

    return item(f"systemd:{service_name}", "FAIL" if required_online else "WARN", f"service status is {active_state} ({sub_state}), result={res}")


def mcp_item() -> dict[str, Any]:
    if not MCP_PACKAGE.exists() or not MCP_ENTRYPOINT.exists():
        return item("mcp:server", "FAIL", "mcp_server package or entrypoint missing")
    node_modules = ROOT / "mcp_server" / "node_modules" / "@modelcontextprotocol" / "sdk"
    if not node_modules.exists():
        return item("mcp:server", "FAIL", "@modelcontextprotocol/sdk is not installed")
    result = run(["node", "--check", str(MCP_ENTRYPOINT)])
    if not result["ok"]:
        return item("mcp:server", "FAIL", result["stderr"] or result["stdout"])
    return item("mcp:server", "PASS", "entrypoint syntax and SDK install verified")


def write_test_item(local_root: str) -> dict[str, Any]:
    if not local_root:
        return item("storage:write_test", "FAIL", "local provider root is not configured")
    root = Path(local_root)
    target = root / f".ubuntu_env_write_test_{os.getpid()}_{int(time.time())}"
    try:
        root.mkdir(parents=True, exist_ok=True)
        target.write_text("radriloniuma-env-test\n", encoding="utf-8")
        if target.read_text(encoding="utf-8") != "radriloniuma-env-test\n":
            return item("storage:write_test", "FAIL", "readback mismatch")
        target.unlink()
    except OSError as exc:
        return item("storage:write_test", "FAIL", str(exc))
    return item("storage:write_test", "PASS", "write/read/delete verified")


def install_plan() -> list[str]:
    return [
        "sudo apt-get update",
        "sudo apt-get install -y libsecret-1-0 udisks2 ntfs-3g smartmontools nvme-cli",
        "cd mcp_server && npm install",
        "sudo systemctl daemon-reload",
        "sudo systemctl enable lam_gateway.service trianiuma_mcp_bridge.service lam_sync.timer",
    ]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    policy = read_policy()
    local_root = local_root_from_policy(policy)
    checks: list[dict[str, Any]] = []

    checks.append(item("repo", "PASS", "RADRILONIUMA workspace detected", str(ROOT)))
    checks.append(item("policy", "PASS" if policy else "FAIL", "routing policy loaded" if policy else "routing policy missing"))
    checks.append(item("policy:local_root", "PASS" if local_root else "FAIL", local_root or "not configured"))

    for command in ["python3", "node", "npm", "git", "lsblk", "findmnt", "udisksctl"]:
        checks.append(command_check(command, required=True))
    for command in ["pm2", "ntfsfix", "smartctl", "nvme", "gemini", "google-chrome", "chromium", "chromium-browser"]:
        checks.append(command_check(command, required=False))

    checks.append(mount_item(local_root))
    checks.append(local_health_item(policy))
    checks.append(mcp_item())
    checks.append(systemd_item("lam_gateway.service", required_online=True))
    checks.append(systemd_item("trianiuma_mcp_bridge.service", required_online=True))
    checks.append(systemd_item("lam_queue_worker.service", required_online=False))
    checks.append(systemd_item("validating_eye.service", required_online=True))


    if args.write_test:
        checks.append(write_test_item(local_root))

    fail_count = sum(1 for check in checks if check["status"] == "FAIL")
    warn_count = sum(1 for check in checks if check["status"] == "WARN")
    status = "FAIL" if fail_count else "WARN" if warn_count else "PASS"
    return {
        "status": status,
        "summary": {"fail": fail_count, "warn": warn_count, "pass": sum(1 for c in checks if c["status"] == "PASS")},
        "checks": checks,
        "install_plan": install_plan() if args.install_plan else [],
    }


def print_text(report: dict[str, Any]) -> None:
    print(f"RADRILONIUMA Ubuntu gateway env requirements: {report['status']}")
    summary = report["summary"]
    print(f"PASS={summary['pass']} WARN={summary['warn']} FAIL={summary['fail']}")
    for check in report["checks"]:
        print(f"[{check['status']}] {check['name']}: {check['detail']}")
        if "evidence" in check and check["status"] != "PASS":
            print(f"  evidence: {check['evidence']}")
    if report.get("install_plan"):
        print("\nInstall/update plan:")
        for command in report["install_plan"]:
            print(f"  {command}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ubuntu hardware/software/device env tests for RADRILONIUMA gateway.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--write-test", action="store_true", help="Verify write/read/delete on the configured local provider root.")
    parser.add_argument("--install-plan", action="store_true", help="Print suggested install/update commands without executing them.")
    args = parser.parse_args()

    report = build_report(args)
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print_text(report)
    return 1 if report["summary"]["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
