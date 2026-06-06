#!/usr/bin/env python3
"""V458 Wi-Fi operator session bundle and leak audit.

V458 is host-side only.  It builds a private, sanitized index of the current
V456/V457/V447/V452 Wi-Fi handoff evidence and scans the referenced evidence
files for obvious Wi-Fi secret leakage without copying raw captures.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_operator_session_outcome_v457 import evidence_state as v457_evidence_state
from wifi_operator_session_outcome_v457 import classify as v457_classify


DEFAULT_OUT_DIR = Path("tmp/wifi/v458-wifi-operator-session-bundle")
DEFAULT_WIFI_ROOT = Path("tmp/wifi")
MAX_FILE_BYTES = 2 * 1024 * 1024
ENV_ASSIGN_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:export\s+|env\s+)?(?P<name>A90_WIFI_(?:SSID|PSK))="
    r"(?:'(?P<sq>[^']*)'|\"(?P<dq>[^\"]*)\"|(?P<bare>[^\s\\;#]+))"
)
JSON_SECRET_FIELD_RE = re.compile(
    r'"(?P<key>ssid|bssid|password|passphrase|psk|pre_shared_key|targetConfigKey)"'
    r"\s*:\s*(?P<value>\"[^\"\n]{0,160}\"|[^,\s}\]]{1,160})",
    re.IGNORECASE,
)
CONNECT_RE = re.compile(r"\bcmd\s+wifi\s+connect-network\b(?P<args>[^\n`]*)", re.IGNORECASE)
CONNECTED_SSID_RE = re.compile(r'Wifi is connected to "(?P<value>[^"\n]+)"', re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--wifi-root", type=Path, default=DEFAULT_WIFI_ROOT)
    parser.add_argument("--include-synthetic", action="store_true")
    parser.add_argument("--max-findings", type=int, default=200)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def normalize_value(value: str) -> str:
    return value.strip().strip("'\"").strip()


def placeholder_value(value: str) -> bool:
    value = normalize_value(value)
    lowered = value.lower()
    return (
        not value
        or value in {"12345678", "codex-test-network"}
        or value.startswith("$A90_WIFI_")
        or value.startswith("${A90_WIFI_")
        or value.startswith("env:A90_WIFI_")
        or (value.startswith("<") and value.endswith(">"))
        or lowered in {"-", "none", "null", "redacted", "<redacted>", "placeholder"}
    )


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def safe_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".").resolve()))
    except ValueError:
        return str(path)


def add_finding(
    findings: list[dict[str, Any]],
    path: Path,
    line: int,
    rule: str,
    detail: str,
    max_findings: int,
) -> None:
    if len(findings) >= max_findings:
        return
    findings.append(
        {
            "path": safe_rel(path),
            "line": line,
            "rule": rule,
            "detail": detail,
        }
    )


def manifest_summary(name: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {"name": name, "present": False}
    classification = payload.get("classification") or {}
    return {
        "name": name,
        "present": True,
        "path": str(payload.get("_path") or ""),
        "run_dir": str(payload.get("_run_dir") or ""),
        "decision": str(payload.get("decision") or ""),
        "pass": payload.get("pass"),
        "reason": str(payload.get("reason") or ""),
        "next_gate": str(classification.get("next_gate") or ""),
        "recommended_command": str(classification.get("recommended_command") or ""),
        "device_commands_executed": bool(payload.get("device_commands_executed")),
        "device_mutations": bool(payload.get("device_mutations")),
        "wifi_bringup_executed": bool(payload.get("wifi_bringup_executed")),
    }


def selected_manifests(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        manifest_summary("operator_packet", state.get("operator_packet")),
        manifest_summary("v456_packet", state.get("v456")),
        manifest_summary("v447_private_preflight", state.get("preflight")),
        manifest_summary("v447_live", state.get("live")),
        manifest_summary("v447_stale_live", state.get("stale_live")),
        manifest_summary("nested_v445", state.get("nested_v445")),
        manifest_summary("v452_cleanup", state.get("cleanup")),
        manifest_summary("v449_after_preflight", state.get("router_after_preflight")),
        manifest_summary("v450_after_preflight", state.get("readiness_after_preflight")),
        manifest_summary("v452_after_preflight", state.get("cleanup_after_preflight")),
        manifest_summary("v449_after_live", state.get("router_after_live")),
        manifest_summary("v450_after_live", state.get("readiness_after_live")),
        manifest_summary("v452_after_live", state.get("cleanup_after_live")),
    ]


def candidate_dirs(summaries: list[dict[str, Any]]) -> list[Path]:
    dirs: list[Path] = []
    for item in summaries:
        run_dir = str(item.get("run_dir") or "")
        if not run_dir:
            continue
        path = Path(run_dir)
        if path.is_dir() and path not in dirs:
            dirs.append(path)
    return dirs


def text_files(paths: list[Path]) -> list[Path]:
    rows: list[Path] = []
    for root in paths:
        for path in root.rglob("*"):
            if path.is_file():
                rows.append(path)
    return sorted(rows)


def scan_text(path: Path, text: str, findings: list[dict[str, Any]], max_findings: int) -> None:
    for match in ENV_ASSIGN_RE.finditer(text):
        value = match.group("sq") if match.group("sq") is not None else match.group("dq") if match.group("dq") is not None else match.group("bare") or ""
        if not placeholder_value(value):
            add_finding(
                findings,
                path,
                line_number(text, match.start()),
                "wifi-env-assignment",
                f"{match.group('name')} assignment uses a non-placeholder value",
                max_findings,
            )
    for match in JSON_SECRET_FIELD_RE.finditer(text):
        value = normalize_value(match.group("value"))
        if not placeholder_value(value):
            add_finding(
                findings,
                path,
                line_number(text, match.start()),
                "wifi-json-private-field",
                f"{match.group('key')} field contains a non-placeholder value",
                max_findings,
            )
    for match in CONNECT_RE.finditer(text):
        args = match.group("args")
        if "$A90_WIFI_" not in args and "<" not in args and "env-derived" not in args:
            add_finding(
                findings,
                path,
                line_number(text, match.start()),
                "raw-connect-network-command",
                "cmd wifi connect-network appears without env placeholder",
                max_findings,
            )
    for match in CONNECTED_SSID_RE.finditer(text):
        if not placeholder_value(match.group("value")):
            add_finding(
                findings,
                path,
                line_number(text, match.start()),
                "raw-connected-ssid",
                "Wi-Fi status appears to contain a raw connected SSID",
                max_findings,
            )


def leak_audit(dirs: list[Path], max_findings: int) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0
    skipped: list[dict[str, str]] = []
    for path in text_files(dirs):
        try:
            data = path.read_bytes()
        except Exception as exc:  # noqa: BLE001
            skipped.append({"path": safe_rel(path), "reason": f"read-error: {exc}"})
            continue
        if len(data) > MAX_FILE_BYTES:
            skipped.append({"path": safe_rel(path), "reason": f"too-large: {len(data)}"})
            continue
        if b"\0" in data:
            skipped.append({"path": safe_rel(path), "reason": "binary"})
            continue
        scanned += 1
        scan_text(path, data.decode("utf-8", errors="replace"), findings, max_findings)
    return {
        "ok": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "scanned_text_files": scanned,
        "skipped": skipped[:50],
    }


def classify(command: str, v457: dict[str, Any], leak: dict[str, Any]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v458-wifi-session-bundle-plan-ready",
            "pass": True,
            "reason": "session bundle and leak-audit plan generated",
            "next_gate": "run V458 before or after the V456 one-session operator script",
            "recommended_command": "",
        }
    if not leak.get("ok", False):
        return {
            "decision": "v458-wifi-session-bundle-leak-audit-blocked",
            "pass": False,
            "reason": f"referenced Wi-Fi evidence contains {leak.get('finding_count')} secret-like findings",
            "next_gate": "inspect V458 leak-findings.json and sanitize evidence handling before sharing",
            "recommended_command": "",
        }
    decision = str(v457.get("decision") or "")
    if decision == "v457-wifi-session-awaiting-operator":
        return {
            "decision": "v458-wifi-session-bundle-awaiting-operator",
            "pass": True,
            "reason": "sanitized session bundle is ready and the session is awaiting local Wi-Fi input",
            "next_gate": str(v457.get("next_gate") or "run generated one-session script locally"),
            "recommended_command": str(v457.get("recommended_command") or ""),
        }
    if decision == "v457-wifi-session-live-cleanup-pass":
        return {
            "decision": "v458-wifi-session-bundle-live-cleanup-pass",
            "pass": True,
            "reason": "sanitized session bundle is ready and live cleanup proof passed",
            "next_gate": "plan bounded Wi-Fi stability or server binding policy",
            "recommended_command": "",
        }
    return {
        "decision": "v458-wifi-session-bundle-outcome-routed",
        "pass": bool(v457.get("pass")),
        "reason": "sanitized session bundle is ready; V457 outcome is " + (decision or "unknown"),
        "next_gate": str(v457.get("next_gate") or "inspect V457 outcome"),
        "recommended_command": str(v457.get("recommended_command") or ""),
    }


def guardrails() -> list[str]:
    return [
        "host-side sanitized bundle only",
        "does not copy raw captures into the bundle",
        "does not read Wi-Fi secret env values",
        "does not execute generated operator scripts",
        "does not run device commands or Wi-Fi bring-up",
        "server exposure remains blocked",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            item.get("name", "-"),
            str(item.get("present")),
            str(item.get("decision") or "-"),
            str(item.get("pass")),
            str(item.get("run_dir") or "-"),
        ]
        for item in manifest["session_index"]["manifests"]
    ]
    return "\n".join(
        [
            "# V458 Wi-Fi Operator Session Bundle",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{manifest['classification']['next_gate']}`",
            f"- recommended_command: `{manifest['classification'].get('recommended_command') or '-'}`",
            f"- leak_findings: `{manifest['leak_audit']['finding_count']}`",
            f"- scanned_text_files: `{manifest['leak_audit']['scanned_text_files']}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Session Index",
            "",
            markdown_table(["item", "present", "decision", "pass", "run_dir"], rows),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "run":
        state_args = argparse.Namespace(wifi_root=args.wifi_root, include_synthetic=args.include_synthetic)
        state = v457_evidence_state(state_args)
        v457_result = v457_classify("run", state)
        summaries = selected_manifests(state)
        dirs = candidate_dirs(summaries)
        leak = leak_audit(dirs, args.max_findings)
    else:
        state = {}
        v457_result = {}
        summaries = []
        dirs = []
        leak = {"ok": True, "finding_count": 0, "findings": [], "scanned_text_files": 0, "skipped": []}
    session_index = {
        "v457": v457_result,
        "manifests": summaries,
        "referenced_dirs": [str(path) for path in dirs],
    }
    classification = classify(args.command, v457_result, leak)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "classification": classification,
        "session_index": session_index,
        "leak_audit": leak,
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }
    store.write_json("session-index.json", session_index)
    store.write_json("leak-findings.json", leak)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next_gate: {classification['next_gate']}")
    if classification.get("recommended_command"):
        print(f"recommended_command: {classification['recommended_command']}")
    print(f"leak_findings: {leak['finding_count']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
