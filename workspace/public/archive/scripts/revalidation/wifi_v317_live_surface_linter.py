#!/usr/bin/env python3
"""Host-only static linter for the V317 live command surface."""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v339-v317-live-surface-linter")
DEFAULT_RUNNER = Path("scripts/revalidation/wifi_private_property_namespace_proof.py")
DEFAULT_PACKET = Path("tmp/wifi/v331-v317-live-readiness-packet/manifest.json")
DEFAULT_PRELIVE = Path("tmp/wifi/v336-v317-prelive-gate-audit/manifest.json")

APPROVAL_PHRASE = "approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up"

ALLOWED_SIGNATURES = {
    "mkdir {path}",
    "run {TOYBOX} rm -rf {REMOTE_WORKDIR}",
    "run {TOYBOX} rm -f {tmp_uue} {tmp_file} {remote_path}",
    "appendfile {tmp_uue} {chunk}",
    "run {TOYBOX} uudecode -o {tmp_file} {tmp_uue}",
    "run {TOYBOX} sha256sum {tmp_file}",
    "run {TOYBOX} mv -f {tmp_file} {remote_path}",
    "run {TOYBOX} rm -f {tmp_uue}",
}

FORBIDDEN_TOKENS = {
    "a90_tcpctl",
    "a90_usbnet",
    "cnss",
    "cnss-daemon",
    "diag",
    "dhcp",
    "hostapd",
    "ifconfig",
    "insmod",
    "ip",
    "iw",
    "modprobe",
    "mount",
    "netservice",
    "rfkill",
    "rmmod",
    "route",
    "setprop",
    "svc",
    "supplicant",
    "wificond",
    "wpa_supplicant",
}

REQUIRED_PACKET_NOT_APPROVED = {
    "global /dev/__properties__ replacement or bind mount",
    "global /dev/socket/property_service creation",
    "property mutation or setprop-like writes",
    "service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
    "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
    "rfkill write, module load/unload, firmware mutation, or partition write",
}


@dataclass
class DeviceCall:
    line: int
    function: str
    signature: str
    status: str
    detail: str


@dataclass
class LintCheck:
    name: str
    status: str
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--runner", type=Path, default=DEFAULT_RUNNER)
    parser.add_argument("--packet-manifest", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--prelive-manifest", type=Path, default=DEFAULT_PRELIVE)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("lint")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def expr_token(node: ast.AST) -> str:
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Name):
        return "{" + node.id + "}"
    if isinstance(node, ast.Attribute):
        return "{" + ast.unparse(node) + "}"
    if isinstance(node, ast.Subscript):
        return "{" + ast.unparse(node) + "}"
    return "{" + ast.unparse(node) + "}"


def signature_from_list(node: ast.AST) -> str:
    if not isinstance(node, ast.List):
        return "<non-list>"
    return " ".join(expr_token(item) for item in node.elts)


def enclosing_function(tree: ast.AST, target: ast.Call) -> str:
    parent: ast.AST | None = None
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            if child is target:
                parent = node
                break
    while parent is not None:
        if isinstance(parent, ast.FunctionDef):
            return parent.name
        next_parent: ast.AST | None = None
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                if child is parent:
                    next_parent = node
                    break
            if next_parent is not None:
                break
        parent = next_parent
    return "<module>"


def collect_device_calls(source: str) -> list[DeviceCall]:
    tree = ast.parse(source)
    calls: list[DeviceCall] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "device_cmd":
            continue
        argv_node = node.args[4] if len(node.args) >= 5 else None
        signature = signature_from_list(argv_node) if argv_node is not None else "<missing-argv>"
        tokens = set(signature.replace("{", " ").replace("}", " ").split())
        forbidden = sorted(token for token in tokens if token.lower() in FORBIDDEN_TOKENS)
        allowed = signature in ALLOWED_SIGNATURES and not forbidden
        detail = "allowed"
        if signature not in ALLOWED_SIGNATURES:
            detail = "signature not in allowlist"
        if forbidden:
            detail = "forbidden tokens: " + ", ".join(forbidden)
        calls.append(DeviceCall(
            line=int(getattr(node, "lineno", 0)),
            function=enclosing_function(tree, node),
            signature=signature,
            status="pass" if allowed else "blocked",
            detail=detail,
        ))
    return sorted(calls, key=lambda item: item.line)


def check_packet(packet: dict[str, Any], prelive: dict[str, Any]) -> list[LintCheck]:
    packet_not_approved = set(packet.get("explicitly_not_approved") or [])
    live_command = str(packet.get("live_command") or "")
    cleanup_command = str(packet.get("cleanup_command") or "")
    checks = packet.get("checks") if isinstance(packet.get("checks"), list) else []
    v336_check = next((item for item in checks if item.get("name") == "v336-prelive-gate"), {})
    return [
        LintCheck(
            "packet-decision",
            "pass" if packet.get("decision") == "v317-live-readiness-packet-ready" and bool(packet.get("pass")) else "blocked",
            f"decision={packet.get('decision')} pass={packet.get('pass')}",
        ),
        LintCheck(
            "packet-approval-state",
            "pass" if not bool(packet.get("live_execution_approved")) and not bool(packet.get("device_commands_executed")) and not bool(packet.get("device_mutations")) else "blocked",
            f"live_execution_approved={packet.get('live_execution_approved')} device_commands={packet.get('device_commands_executed')} mutations={packet.get('device_mutations')}",
        ),
        LintCheck(
            "packet-v336-check",
            "pass" if v336_check.get("status") == "pass" else "blocked",
            f"v336_status={v336_check.get('status')} detail={v336_check.get('detail')}",
        ),
        LintCheck(
            "packet-command-contract",
            "pass" if "--prelive-gate-manifest" in live_command and "--prelive-gate-manifest" in cleanup_command else "blocked",
            "prelive gate argument present in live and cleanup commands",
        ),
        LintCheck(
            "packet-forbidden-scope",
            "pass" if REQUIRED_PACKET_NOT_APPROVED.issubset(packet_not_approved) else "blocked",
            f"missing={sorted(REQUIRED_PACKET_NOT_APPROVED - packet_not_approved)}",
        ),
        LintCheck(
            "prelive-state",
            "pass" if prelive.get("decision") == "v317-prelive-gate-awaiting-approval" and prelive.get("remaining_blockers") == ["exact-v317-approval-phrase"] else "blocked",
            f"decision={prelive.get('decision')} blockers={prelive.get('remaining_blockers')}",
        ),
        LintCheck(
            "approval-phrase",
            "pass" if packet.get("approval_phrase") == APPROVAL_PHRASE and prelive.get("required_approval_phrase") == APPROVAL_PHRASE else "blocked",
            "packet and prelive approval phrase match expected V317 phrase",
        ),
    ]


def decide(calls: list[DeviceCall], checks: list[LintCheck]) -> tuple[str, bool, str, str]:
    blocked_calls = [item for item in calls if item.status != "pass"]
    blocked_checks = [item for item in checks if item.status != "pass"]
    if blocked_calls or blocked_checks:
        parts = []
        if blocked_calls:
            parts.append("blocked device call signatures")
        if blocked_checks:
            parts.append("blocked packet checks: " + ", ".join(item.name for item in blocked_checks))
        return (
            "v317-live-surface-lint-blocked",
            False,
            "; ".join(parts),
            "repair V317 live surface before requesting live approval",
        )
    return (
        "v317-live-surface-lint-pass",
        True,
        "V317 live surface is limited to approved private-workdir file operations",
        "V317 live proof remains blocked only by exact operator approval",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    runner_path = repo_path(args.runner)
    packet = load_json(args.packet_manifest)
    prelive = load_json(args.prelive_manifest)
    source = runner_path.read_text(encoding="utf-8")
    calls = collect_device_calls(source)
    checks = check_packet(packet, prelive)
    decision, pass_ok, reason, next_step = decide(calls, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "runner": str(runner_path),
        "packet_manifest": str(repo_path(args.packet_manifest)),
        "prelive_manifest": str(repo_path(args.prelive_manifest)),
        "allowed_signatures": sorted(ALLOWED_SIGNATURES),
        "forbidden_tokens": sorted(FORBIDDEN_TOKENS),
        "device_calls": [asdict(item) for item in calls],
        "checks": [asdict(item) for item in checks],
        "live_execution_approved": False,
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    call_rows = [
        [str(item["line"]), item["function"], item["status"], item["signature"], item["detail"]]
        for item in manifest["device_calls"]
    ]
    check_rows = [[item["name"], item["status"], item["detail"]] for item in manifest["checks"]]
    return "\n".join([
        "# v339 V317 Live Surface Linter",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_execution_approved: `{manifest['live_execution_approved']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Device Command Calls",
        "",
        markdown_table(["line", "function", "status", "signature", "detail"], call_rows),
        "",
        "## Packet Checks",
        "",
        markdown_table(["name", "status", "detail"], check_rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
