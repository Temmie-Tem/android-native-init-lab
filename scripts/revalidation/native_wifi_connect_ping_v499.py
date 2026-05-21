#!/usr/bin/env python3
"""V499 native-init Wi-Fi connect/ping readiness gate.

V499 is a fail-closed readiness gate for the first bounded native connect,
DHCP, and external ping implementation. It does not read SSID/PSK values, start
supplicant, connect, request DHCP, mutate routes, or send external packets. It
requires V497 scan-only pass evidence, V498 private policy evidence, and helper
v51 connect-tool-surface evidence before a later live implementation can run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v499-native-wifi-connect-ping-readiness")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "2a3b83f852e17f93cf82a9617f396457718024f28ac510fb915848e3e3547a7d"
ACCEPTED_HELPER_MARKERS = (
    "a90_android_execns_probe v51",
    "a90_android_execns_probe v52",
    "a90_android_execns_probe v53",
)
EXPECTED_V497_DECISION = "v497-native-scan-only-pass-redacted"
EXPECTED_V498_DECISIONS = {
    "v498-native-private-policy-ready",
    "v498-native-private-policy-ready-awaiting-v497",
}
CONNECT_KEY_RE = re.compile(r"^wifi_connect_tool_surface\.([A-Za-z0-9_.]+)=(.*)$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--v497-manifest", type=Path, default=None)
    parser.add_argument("--v498-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    return parser.parse_args()


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"present": False, "path": "", "decision": "missing", "pass": False}
    resolved = repo_path(path)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False}
    except Exception as exc:  # noqa: BLE001 - preserve parse issue
        return {
            "present": True,
            "path": str(resolved),
            "decision": "invalid-json",
            "pass": False,
            "error": str(exc),
        }
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def latest_manifest(pattern: str, expected: set[str]) -> Path | None:
    candidates: list[Path] = []
    for path in repo_path("tmp/wifi").glob(pattern):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("decision") in expected and payload.get("pass") is True:
            candidates.append(path)
    candidates.sort(key=lambda item: item.stat().st_mtime)
    return candidates[-1] if candidates else None


def selected_v497(args: argparse.Namespace) -> Path | None:
    return args.v497_manifest or latest_manifest("v497*/manifest.json", {EXPECTED_V497_DECISION})


def selected_v498(args: argparse.Namespace) -> Path | None:
    return args.v498_manifest or latest_manifest("v498*/manifest.json", EXPECTED_V498_DECISIONS)


def v497_state(payload: dict[str, Any]) -> dict[str, Any]:
    live = payload.get("live_result") or {}
    return {
        "path": payload.get("path", ""),
        "present": bool(payload.get("present")),
        "decision": payload.get("decision", ""),
        "pass": bool(payload.get("pass")),
        "scan_only_executed": bool(payload.get("scan_only_executed")),
        "connect_executed": bool(payload.get("connect_executed")),
        "link_up_executed": bool(payload.get("link_up_executed")),
        "wifi_bringup_executed": bool(payload.get("wifi_bringup_executed")),
        "credentials_read": bool(payload.get("credentials_read")),
        "external_ping_executed": bool(payload.get("external_ping_executed")),
        "raw_results_redacted": bool(live.get("raw_results_redacted")),
    }


def v498_state(payload: dict[str, Any]) -> dict[str, Any]:
    classification = payload.get("classification") or {}
    validation = classification.get("validation") or {}
    return {
        "path": payload.get("path", ""),
        "present": bool(payload.get("present")),
        "decision": payload.get("decision", ""),
        "pass": bool(payload.get("pass")),
        "policy_file": payload.get("policy_file", ""),
        "policy_materialized": bool(classification.get("policy_materialized")),
        "synthetic_placeholder_detected": bool(classification.get("synthetic_placeholder_detected", True)),
        "validation_ready": bool(validation.get("ready")),
        "credentials_read": bool(payload.get("credentials_read")),
        "device_commands_executed": bool(payload.get("device_commands_executed")),
        "device_mutations": bool(payload.get("device_mutations")),
        "scan_connect_executed": bool(payload.get("scan_connect_executed")),
        "external_ping_executed": bool(payload.get("external_ping_executed")),
    }


def write_step(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/{name}.txt", text.rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def run_step(args: argparse.Namespace, store: EvidenceStore, name: str, command: list[str], timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_step(store, name, text)
    item["payload"] = text
    return item


def run_preflight_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    return [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 25.0),
        run_step(args, store, "helper-sha256", ["run", "/cache/bin/toybox", "sha256sum", args.helper], 20.0),
        run_step(args, store, "helper-usage", ["run", args.helper, "--help"], 20.0),
        run_step(
            args,
            store,
            "connect-tool-surface",
            [
                "run",
                args.helper,
                "--system-root",
                "/mnt/system/system",
                "--vendor-block",
                "/dev/block/sda29",
                "--vendor-fstype",
                "ext4",
                "--mode",
                "wifi-connect-tool-surface",
                "--target-profile",
                "system-toybox",
                "--timeout-sec",
                "5",
            ],
            45.0,
        ),
    ]


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def parse_connect_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = CONNECT_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def add_check(checks: list[dict[str, Any]],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str],
              next_step: str) -> None:
    checks.append({
        "name": name,
        "status": status,
        "severity": severity,
        "detail": detail,
        "evidence": evidence,
        "next_step": next_step,
    })


def build_checks(args: argparse.Namespace,
                 command: str,
                 steps: list[dict[str, Any]],
                 v497: dict[str, Any],
                 v498: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight")
        return checks

    version = step_payload(steps, "version")
    status = step_payload(steps, "status")
    helper_sha = step_payload(steps, "helper-sha256")
    helper_usage = step_payload(steps, "helper-usage")
    connect_text = step_payload(steps, "connect-tool-surface")
    connect_keys = parse_connect_keys(connect_text)
    v497_info = v497_state(v497)
    v498_info = v498_state(v498)
    native_clean = args.expect_version in version and "fail=0" in status
    helper_marker_ready = any(marker in helper_usage for marker in ACCEPTED_HELPER_MARKERS)
    helper_ready = (
        args.helper_sha256 in helper_sha
        and helper_marker_ready
        and "wifi-connect-tool-surface" in helper_usage
    )
    v497_ready = (
        v497_info["decision"] == EXPECTED_V497_DECISION
        and v497_info["pass"]
        and v497_info["scan_only_executed"]
        and v497_info["raw_results_redacted"]
        and not v497_info["connect_executed"]
        and not v497_info["link_up_executed"]
        and not v497_info["wifi_bringup_executed"]
        and not v497_info["credentials_read"]
        and not v497_info["external_ping_executed"]
    )
    v498_ready = (
        v498_info["decision"] in EXPECTED_V498_DECISIONS
        and v498_info["pass"]
        and v498_info["policy_materialized"]
        and not v498_info["synthetic_placeholder_detected"]
        and v498_info["validation_ready"]
        and v498_info["credentials_read"]
        and not v498_info["device_commands_executed"]
        and not v498_info["device_mutations"]
        and not v498_info["scan_connect_executed"]
        and not v498_info["external_ping_executed"]
    )
    tools_ready = connect_keys.get("result") == "connect-tools-ready"

    add_check(checks, "native-health", "pass" if native_clean else "blocked", "blocker", f"expect_version={args.expect_version} fail0={'fail=0' in status}", [], "restore native health before connect readiness")
    add_check(checks, "helper-v51plus-connect-tool-surface", "pass" if helper_ready else "blocked", "blocker", f"sha={args.helper_sha256 in helper_sha} marker={helper_marker_ready} mode={'wifi-connect-tool-surface' in helper_usage}", [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy helper v51 or later before V499 preflight")
    add_check(checks, "v497-scan-only-pass-redacted", "pass" if v497_ready else "blocked", "blocker", f"path={v497_info['path']} decision={v497_info['decision']} scan={v497_info['scan_only_executed']} redacted={v497_info['raw_results_redacted']}", [v497_info["path"]], "complete V490-V497 scan-only proof first")
    add_check(checks, "v498-private-policy-ready", "pass" if v498_ready else "blocked", "blocker", f"path={v498_info['path']} decision={v498_info['decision']} materialized={v498_info['policy_materialized']} validation={v498_info['validation_ready']} credentials_read={v498_info['credentials_read']} synthetic={v498_info['synthetic_placeholder_detected']}", [v498_info["path"]], "run V498 with private non-placeholder Wi-Fi env and approval flags")
    add_check(checks, "connect-tool-surface-ready", "pass" if tools_ready else "blocked", "blocker", f"result={connect_keys.get('result', 'missing')} supplicant={connect_keys.get('supplicant_ready', '0')} dhcp={connect_keys.get('dhcp_ready', '0')} ping={connect_keys.get('ping_ready', '0')}", [line for line in connect_text.splitlines() if "wifi_connect_tool_surface." in line][:12], "provide supplicant, DHCP client, and ping tools before live connect")
    return checks


def blockers(checks: list[dict[str, Any]]) -> list[str]:
    return [check["name"] for check in checks if check["severity"] == "blocker" and check["status"] != "pass"]


def classify(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v499-native-connect-ping-readiness-plan-ready", True, "plan-only; no device command executed", "deploy helper v51 and run preflight"
    blocked = blockers(checks)
    if blocked:
        return "v499-native-connect-ping-readiness-blocked", False, "blocked before live connect implementation by " + ", ".join(blocked), "resolve blockers before V500 live connect/DHCP/ping"
    return "v499-native-connect-ping-readiness-ready", True, "scan-only proof, private policy, and connect tools are ready", "implement approved V500 bounded native connect/DHCP/external ping"


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "helper": args.helper,
        "helper_sha256": args.helper_sha256,
        "helper_mode": "wifi-connect-tool-surface",
        "strategy": "wpa_supplicant for WPA/WPA2/WPA3 association, DHCP client for address lease, interface-bound ping for proof",
        "preconditions": [
            EXPECTED_V497_DECISION,
            "v498-native-private-policy-ready or ready-awaiting-v497",
            "a90_android_execns_probe v51 or later deployed",
            "supplicant, DHCP client, ip, and ping tools present",
        ],
        "blocked_actions": [
            "credential read in V499",
            "supplicant start",
            "connect/link-up",
            "DHCP/routing mutation",
            "external ping",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"]), item["next_step"]]
        for item in manifest["checks"]
    ]
    step_rows = [
        [item["name"], "PASS" if item.get("ok") else "FAIL", str(item.get("rc")), item.get("status", "-"), item.get("file", "")]
        for item in manifest["steps"]
    ]
    connect_rows = [[key, value] for key, value in sorted((manifest.get("connect_tool_surface") or {}).items())]
    return "\n".join([
        "# V499 Native Wi-Fi Connect/Ping Readiness",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- credentials_read: `{manifest['credentials_read']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next"], check_rows),
        "",
        "## Native Steps",
        "",
        markdown_table(["step", "ok", "rc", "status", "file"], step_rows) if step_rows else "- none",
        "",
        "## Connect Tool Surface",
        "",
        markdown_table(["key", "value"], connect_rows) if connect_rows else "- none",
        "",
    ]) + "\n"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v497 = load_json(selected_v497(args))
    v498 = load_json(selected_v498(args))
    steps = [] if args.command == "plan" else run_preflight_steps(args, store)
    checks = build_checks(args, args.command, steps, v497, v498)
    decision, pass_ok, reason, next_step = classify(args.command, checks)
    connect_keys = parse_connect_keys(step_payload(steps, "connect-tool-surface")) if steps else {}
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "plan": build_plan(args),
        "v497": v497_state(v497),
        "v498": v498_state(v498),
        "steps": steps,
        "checks": checks,
        "connect_tool_surface": connect_keys,
        "device_commands_executed": args.command != "plan",
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "cnss_start_executed": False,
        "iwifi_start_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "connect_executed": False,
        "dhcp_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next_step: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
