#!/usr/bin/env python3
"""V500 native-init Wi-Fi connect/DHCP/external-ping execution gate.

V500 is the first gate that is allowed to read private Wi-Fi env values for a
native-init connect attempt, but only after V497 scan-only, V498 private policy,
and V499 connect-readiness evidence are all ready.  It remains fail-closed: if
the live helper-side executor is not present, no device mutation is attempted.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from native_wifi_private_policy_materialize_v498 import (
    KNOWN_SYNTHETIC_VALUES,
    SECURITY_TYPES,
    validate_policy,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v500-native-wifi-connect-ping")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "2a3b83f852e17f93cf82a9617f396457718024f28ac510fb915848e3e3547a7d"
EXPECTED_V497_DECISION = "v497-native-scan-only-pass-redacted"
EXPECTED_V498_DECISIONS = {
    "v498-native-private-policy-ready",
    "v498-native-private-policy-ready-awaiting-v497",
}
EXPECTED_V499_DECISION = "v499-native-connect-ping-readiness-ready"
EXECUTOR_MODE = "wifi-active-session-connect-ping"
APPROVAL_PHRASE = (
    "approve v500 native connect DHCP external ping only; "
    "cleanup required; no server exposure"
)
RAW_SECRET_RE = re.compile(
    r'"(?:ssid|bssid|password|passphrase|psk|pre_shared_key|targetConfigKey)"\s*:',
    re.IGNORECASE,
)
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--v497-manifest", type=Path, default=None)
    parser.add_argument("--v498-manifest", type=Path, default=None)
    parser.add_argument("--v499-manifest", type=Path, default=None)
    parser.add_argument("--policy", type=Path, default=None)
    parser.add_argument("--target-id", default="lab-primary")
    parser.add_argument("--security", choices=SECURITY_TYPES, default="wpa2")
    parser.add_argument("--iface", default="auto")
    parser.add_argument("--ping-target", action="append", default=[])
    parser.add_argument("--allow-read-wifi-env", action="store_true")
    parser.add_argument("--i-understand-wifi-secret-env", action="store_true")
    parser.add_argument("--allow-native-connect-dhcp-ping", action="store_true")
    parser.add_argument("--i-understand-native-wifi-connect-ping", action="store_true")
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument(
        "--refresh-v499",
        action="store_true",
        help="run V499 read-only readiness preflight before classifying V500",
    )
    parser.add_argument(
        "--skip-secret-guard",
        action="store_true",
        help="for tests only: do not run V446 repository secret guard",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def run_host(command: list[str], timeout: float) -> tuple[int | None, str, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, "", time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - evidence should preserve host failure
        return None, "", str(exc), time.monotonic() - started


def latest_manifest(pattern: str, decisions: set[str]) -> Path | None:
    candidates: list[Path] = []
    for path in repo_path("tmp/wifi").glob(pattern):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("decision") in decisions and payload.get("pass") is True:
            candidates.append(path)
    candidates.sort(key=lambda item: item.stat().st_mtime)
    return candidates[-1] if candidates else None


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"present": False, "path": "", "decision": "missing", "pass": False}
    resolved = repo_path(path)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False}
    except Exception as exc:  # noqa: BLE001
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


def selected_v497(args: argparse.Namespace) -> Path | None:
    return args.v497_manifest or latest_manifest("v497*/manifest.json", {EXPECTED_V497_DECISION})


def selected_v498(args: argparse.Namespace) -> Path | None:
    return args.v498_manifest or latest_manifest("v498*/manifest.json", EXPECTED_V498_DECISIONS)


def selected_v499(args: argparse.Namespace) -> Path | None:
    return args.v499_manifest or latest_manifest("v499*/manifest.json", {EXPECTED_V499_DECISION})


def v497_ready(payload: dict[str, Any]) -> bool:
    live = payload.get("live_result") or {}
    return (
        payload.get("decision") == EXPECTED_V497_DECISION
        and payload.get("pass") is True
        and payload.get("scan_only_executed") is True
        and live.get("raw_results_redacted") is True
        and payload.get("connect_executed") is False
        and payload.get("link_up_executed") is False
        and payload.get("wifi_bringup_executed") is False
        and payload.get("credentials_read") is False
        and payload.get("external_ping_executed") is False
    )


def v498_ready(payload: dict[str, Any]) -> bool:
    classification = payload.get("classification") or {}
    validation = classification.get("validation") or {}
    return (
        payload.get("decision") in EXPECTED_V498_DECISIONS
        and payload.get("pass") is True
        and classification.get("policy_materialized") is True
        and classification.get("synthetic_placeholder_detected") is False
        and validation.get("ready") is True
        and payload.get("credentials_read") is True
        and payload.get("device_commands_executed") is False
        and payload.get("device_mutations") is False
        and payload.get("scan_connect_executed") is False
        and payload.get("external_ping_executed") is False
    )


def v499_ready(payload: dict[str, Any]) -> bool:
    return (
        payload.get("decision") == EXPECTED_V499_DECISION
        and payload.get("pass") is True
        and payload.get("wifi_bringup_executed") is False
        and payload.get("credentials_read") is False
        and payload.get("scan_connect_executed") is False
        and payload.get("external_ping_executed") is False
    )


def policy_path(args: argparse.Namespace, v498: dict[str, Any]) -> Path | None:
    if args.policy:
        return repo_path(args.policy)
    policy_file = v498.get("policy_file")
    manifest_path = v498.get("path")
    if not policy_file or not manifest_path:
        return None
    return Path(str(manifest_path)).parent / str(policy_file)


def load_policy(path: Path | None) -> tuple[dict[str, Any] | None, str, str]:
    if path is None:
        return None, "", ""
    try:
        text = repo_path(path).read_text(encoding="utf-8")
        return json.loads(text), str(repo_path(path)), text
    except FileNotFoundError:
        return None, str(repo_path(path)), ""
    except Exception as exc:  # noqa: BLE001
        return {"_error": str(exc)}, str(repo_path(path)), ""


def approval_state(args: argparse.Namespace) -> dict[str, Any]:
    missing: list[str] = []
    if not args.allow_read_wifi_env:
        missing.append("--allow-read-wifi-env")
    if not args.i_understand_wifi_secret_env:
        missing.append("--i-understand-wifi-secret-env")
    if not args.allow_native_connect_dhcp_ping:
        missing.append("--allow-native-connect-dhcp-ping")
    if not args.i_understand_native_wifi_connect_ping:
        missing.append("--i-understand-native-wifi-connect-ping")
    if args.approval_phrase != APPROVAL_PHRASE:
        missing.append("--approval-phrase=<exact-v500-phrase>")
    return {"ok": not missing, "missing": missing, "phrase": APPROVAL_PHRASE}


def env_presence() -> dict[str, Any]:
    return {
        "A90_WIFI_SSID": {"present": "A90_WIFI_SSID" in os.environ},
        "A90_WIFI_PSK": {"present": "A90_WIFI_PSK" in os.environ},
    }


def env_values(args: argparse.Namespace) -> dict[str, str]:
    if not (args.allow_read_wifi_env and args.i_understand_wifi_secret_env):
        return {}
    return {
        "A90_WIFI_SSID": os.environ.get("A90_WIFI_SSID", ""),
        "A90_WIFI_PSK": os.environ.get("A90_WIFI_PSK", ""),
    }


def validate_env(policy: dict[str, Any] | None, args: argparse.Namespace) -> dict[str, Any]:
    values = env_values(args)
    issues: list[str] = []
    if policy is None:
        return {"ready": False, "issues": ["policy is missing"], "target": {}, "env_state": env_presence()}
    if "_error" in policy:
        return {"ready": False, "issues": [str(policy["_error"])], "target": {}, "env_state": env_presence()}
    targets = policy.get("targets")
    if not isinstance(targets, list) or not targets:
        return {"ready": False, "issues": ["policy target list is empty"], "target": {}, "env_state": env_presence()}
    target = next((item for item in targets if isinstance(item, dict) and item.get("id") == args.target_id), None)
    if target is None:
        issues.append(f"target id {args.target_id!r} not found")
        target = targets[0] if isinstance(targets[0], dict) else {}
    ssid = values.get("A90_WIFI_SSID", "")
    psk = values.get("A90_WIFI_PSK", "")
    security = target.get("security")
    if not ssid:
        issues.append("A90_WIFI_SSID is required")
    if security in {"wpa2", "wpa3"} and not psk:
        issues.append("A90_WIFI_PSK is required")
    if security in {"open", "owe"} and psk:
        issues.append("A90_WIFI_PSK must be unset for open/owe")
    if ssid in KNOWN_SYNTHETIC_VALUES:
        issues.append("A90_WIFI_SSID must not use a known synthetic placeholder")
    if psk in KNOWN_SYNTHETIC_VALUES:
        issues.append("A90_WIFI_PSK must not use a known synthetic placeholder")
    expected_hash = target.get("ssid_sha256")
    if ssid and expected_hash != hashlib.sha256(ssid.encode("utf-8")).hexdigest():
        issues.append("A90_WIFI_SSID does not match policy ssid_sha256")
    return {
        "ready": not issues,
        "issues": issues,
        "target": {
            "id": target.get("id", ""),
            "security": security or "",
            "ssid_hash_match": not any("ssid_sha256" in issue for issue in issues),
            "credential_source": target.get("credential_source", ""),
        },
        "env_state": env_presence(),
    }


def run_secret_guard(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.command == "plan" or args.skip_secret_guard:
        return {
            "name": "v446-secret-guard",
            "ok": True,
            "rc": 0,
            "decision": "skipped" if args.skip_secret_guard else "plan-not-run",
            "pass": True,
            "file": "",
        }
    out_dir = store.path("v446-secret-guard")
    command = [
        sys.executable,
        "scripts/revalidation/wifi_private_secret_guard_v446.py",
        "--out-dir",
        str(out_dir),
        "--include-untracked",
        "run",
    ]
    rc, output, error, duration = run_host(command, timeout=max(60.0, args.timeout * 8))
    store.write_text("host/v446-secret-guard.txt", (output + error).rstrip() + "\n")
    manifest = load_json(out_dir / "manifest.json")
    return {
        "name": "v446-secret-guard",
        "ok": rc == 0,
        "rc": rc,
        "duration_sec": duration,
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
        "file": "host/v446-secret-guard.txt",
    }


def run_v499_refresh(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.command == "plan" or not args.refresh_v499:
        return {}
    out_dir = store.path("v499-readiness-refresh")
    command = [
        sys.executable,
        "scripts/revalidation/native_wifi_connect_ping_v499.py",
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "preflight",
    ]
    rc, output, error, duration = run_host(command, timeout=max(180.0, args.timeout * 6))
    store.write_text("host/v499-readiness-refresh.txt", (output + error).rstrip() + "\n")
    manifest = load_json(out_dir / "manifest.json")
    return {
        "name": "v499-readiness-refresh",
        "ok": rc == 0,
        "rc": rc,
        "duration_sec": duration,
        "decision": manifest.get("decision", "missing"),
        "pass": manifest.get("pass", False),
        "manifest": str(out_dir / "manifest.json"),
        "file": "host/v499-readiness-refresh.txt",
    }


def add_check(checks: list[dict[str, Any]],
              name: str,
              ok: bool,
              severity: str,
              detail: str,
              next_step: str) -> None:
    checks.append({
        "name": name,
        "status": "pass" if ok else "blocked",
        "severity": severity,
        "detail": detail,
        "next_step": next_step,
    })


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "approval_phrase": APPROVAL_PHRASE,
        "executor_mode_required": EXECUTOR_MODE,
        "target_id": args.target_id,
        "iface": args.iface,
        "strategy": "active session -> private supplicant config -> supplicant association -> DHCP -> interface-bound external ping -> cleanup",
        "ping_targets": args.ping_target or ["1.1.1.1", "8.8.8.8"],
        "required_preconditions": [
            EXPECTED_V497_DECISION,
            "v498 native private policy ready and non-placeholder env match",
            EXPECTED_V499_DECISION,
            f"helper mode {EXECUTOR_MODE}",
        ],
        "blocked_until_executor": [
            "temporary secret file transfer contract",
            "helper-side private supplicant config materializer",
            "bounded DHCP script/cleanup contract",
            "redacted association/DHCP/ping result parser",
            "helper v53 live executor body",
        ],
    }


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    guard = run_secret_guard(args, store)
    refresh = run_v499_refresh(args, store)
    v497 = load_json(selected_v497(args))
    v498 = load_json(selected_v498(args))
    refreshed_v499_path = refresh.get("manifest") if refresh else None
    v499 = load_json(Path(refreshed_v499_path)) if refreshed_v499_path else load_json(selected_v499(args))
    policy, resolved_policy_path, policy_text = load_policy(policy_path(args, v498))
    policy_validation = validate_policy(policy, policy_text) if policy_text else {
        "present": policy is not None,
        "ready": False,
        "decision": "policy-missing",
        "issues": ["policy file missing or unreadable"],
        "targets": [],
        "target_count": 0,
    }
    secret_text_safe = not policy_text or (RAW_SECRET_RE.search(policy_text) is None and MAC_RE.search(policy_text) is None)
    approvals = approval_state(args)
    env_validation = validate_env(policy, args) if args.command == "run" and approvals["ok"] else {
        "ready": False,
        "issues": ["not read outside approved run"],
        "target": {},
        "env_state": env_presence(),
    }
    checks: list[dict[str, Any]] = []
    if args.command == "plan":
        add_check(checks, "plan-only", True, "info", "no device command executed", "run preflight")
    else:
        add_check(checks, "secret-guard", bool(guard.get("pass")), "blocker", str(guard.get("decision")), "remove repository-visible Wi-Fi secrets")
        add_check(checks, "v497-scan-only", v497_ready(v497), "blocker", str(v497.get("decision")), "complete V497 scan-only proof")
        add_check(checks, "v498-private-policy", v498_ready(v498), "blocker", str(v498.get("decision")), "run V498 with real private env")
        add_check(checks, "v499-readiness", v499_ready(v499), "blocker", str(v499.get("decision")), "deploy helper v51 and satisfy V499")
        add_check(checks, "policy-redacted", bool(policy_validation.get("ready")) and secret_text_safe, "blocker", str(policy_validation.get("decision")), "fix private native target policy")
        if args.command == "run":
            add_check(checks, "run-approval", bool(approvals["ok"]), "blocker", ", ".join(approvals["missing"]), "rerun with exact V500 approval and flags")
            add_check(checks, "env-policy-match", bool(env_validation.get("ready")), "blocker", "; ".join(env_validation.get("issues", [])), "set matching private A90_WIFI_SSID/A90_WIFI_PSK")
            add_check(checks, "helper-live-executor", False, "blocker", f"{EXECUTOR_MODE} live body is not implemented yet", "implement helper v53 executor before live device mutation")
    blockers = [item["name"] for item in checks if item["severity"] == "blocker" and item["status"] != "pass"]
    if args.command == "plan":
        decision = "v500-native-connect-ping-plan-ready"
        pass_ok = True
        reason = "plan-only; no secret read and no device command executed"
        next_step = "run V500 preflight, then implement helper v53 live executor"
    elif blockers:
        decision = "v500-native-connect-ping-blocked"
        pass_ok = False
        reason = "blocked before native connect/DHCP/ping by " + ", ".join(blockers)
        next_step = "resolve blockers; no Wi-Fi bring-up was attempted"
    else:
        decision = "v500-native-connect-ping-ready"
        pass_ok = True
        reason = "all V500 checks passed"
        next_step = "run bounded native connect/DHCP/ping"
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "plan": build_plan(args),
        "secret_guard": guard,
        "v499_refresh": refresh,
        "v497": {
            "path": v497.get("path", ""),
            "decision": v497.get("decision", ""),
            "pass": v497.get("pass", False),
            "ready": v497_ready(v497),
        },
        "v498": {
            "path": v498.get("path", ""),
            "decision": v498.get("decision", ""),
            "pass": v498.get("pass", False),
            "ready": v498_ready(v498),
        },
        "v499": {
            "path": v499.get("path", ""),
            "decision": v499.get("decision", ""),
            "pass": v499.get("pass", False),
            "ready": v499_ready(v499),
        },
        "policy": {
            "path": resolved_policy_path,
            "validation": policy_validation,
            "redacted": secret_text_safe,
        },
        "approval": approvals,
        "env_validation": env_validation,
        "checks": checks,
        "device_commands_executed": args.command != "plan" and bool(refresh),
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "cnss_start_executed": False,
        "iwifi_start_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": bool(args.command == "run" and approvals["ok"]),
        "scan_connect_executed": False,
        "connect_executed": False,
        "dhcp_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [
        [item["name"], item["status"], item["severity"], item["detail"], item["next_step"]]
        for item in manifest["checks"]
    ]
    state_rows = [
        ["v497", manifest["v497"]["decision"], str(manifest["v497"]["ready"]), manifest["v497"]["path"]],
        ["v498", manifest["v498"]["decision"], str(manifest["v498"]["ready"]), manifest["v498"]["path"]],
        ["v499", manifest["v499"]["decision"], str(manifest["v499"]["ready"]), manifest["v499"]["path"]],
    ]
    policy = manifest["policy"]
    return "\n".join([
        "# V500 Native Wi-Fi Connect/DHCP/Ping Gate",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- credentials_read: `{manifest['credentials_read']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Gate State",
        "",
        markdown_table(["gate", "decision", "ready", "path"], state_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], checks if checks else [["-", "-", "-", "-", "-"]]),
        "",
        "## Policy",
        "",
        f"- path: `{policy['path'] or '-'}`",
        f"- ready: `{policy['validation'].get('ready')}`",
        f"- redacted: `{policy['redacted']}`",
        "",
    ]) + "\n"


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
    print(f"credentials_read: {manifest['credentials_read']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
