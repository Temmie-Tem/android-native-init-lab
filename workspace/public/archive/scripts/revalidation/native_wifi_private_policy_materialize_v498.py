#!/usr/bin/env python3
"""V498 native-init Wi-Fi private target policy materializer.

V498 is host-side only. It may read A90_WIFI_SSID/A90_WIFI_PSK from the process
environment only with explicit approval flags, then writes a private native-init
connect policy containing source references and an SSID hash, never raw network
identifiers or credentials. It does not execute device commands, trigger scans,
connect, request DHCP, route traffic, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v498-native-wifi-private-policy")
SECURITY_TYPES = ("open", "owe", "wpa2", "wpa3")
TARGET_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ENV_SOURCE_RE = re.compile(r"^env:A90_WIFI_[A-Z0-9_]+$")
RAW_SECRET_FIELD_RE = re.compile(
    r'"(?:ssid|bssid|password|passphrase|psk|pre_shared_key|targetConfigKey)"\s*:',
    re.IGNORECASE,
)
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
EXPECTED_V497_DECISION = "v497-native-scan-only-pass-redacted"
KNOWN_SYNTHETIC_VALUES = {
    "12345678",
    "codex-test-network",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v497-manifest", type=Path, default=None)
    parser.add_argument("--target-id", default="lab-primary")
    parser.add_argument("--security", choices=SECURITY_TYPES, default="wpa2")
    parser.add_argument("--allow-read-wifi-env", action="store_true")
    parser.add_argument("--i-understand-wifi-secret-env", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def latest_v497_manifest() -> Path | None:
    candidates: list[Path] = []
    for path in repo_path("tmp/wifi").glob("v497*/manifest.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("decision") == EXPECTED_V497_DECISION:
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
    except Exception as exc:  # noqa: BLE001 - evidence should preserve parse failures
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
    return args.v497_manifest or latest_v497_manifest()


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


def approval_ok(args: argparse.Namespace) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not args.allow_read_wifi_env:
        missing.append("--allow-read-wifi-env")
    if not args.i_understand_wifi_secret_env:
        missing.append("--i-understand-wifi-secret-env")
    return not missing, missing


def env_presence() -> dict[str, Any]:
    return {
        "A90_WIFI_SSID": {"present": "A90_WIFI_SSID" in os.environ},
        "A90_WIFI_PSK": {"present": "A90_WIFI_PSK" in os.environ},
    }


def source_name(source: Any) -> str:
    return source.split(":", 1)[1] if isinstance(source, str) and source.startswith("env:") else ""


def build_policy_from_env(args: argparse.Namespace) -> tuple[dict[str, Any] | None, dict[str, Any], list[str]]:
    state = env_presence()
    issues: list[str] = []
    ssid = os.environ.get("A90_WIFI_SSID", "")
    psk = os.environ.get("A90_WIFI_PSK", "")

    if not ssid:
        issues.append("A90_WIFI_SSID is required")
    if args.security in {"wpa2", "wpa3"} and not psk:
        issues.append("A90_WIFI_PSK is required for wpa2/wpa3")
    if args.security in {"open", "owe"} and psk:
        issues.append("A90_WIFI_PSK must be unset for open/owe")
    if ssid in KNOWN_SYNTHETIC_VALUES:
        issues.append("A90_WIFI_SSID must not use a known synthetic placeholder")
    if psk in KNOWN_SYNTHETIC_VALUES:
        issues.append("A90_WIFI_PSK must not use a known synthetic placeholder")
    if issues:
        return None, state, issues

    target: dict[str, Any] = {
        "id": args.target_id,
        "ssid_source": "env:A90_WIFI_SSID",
        "ssid_sha256": hashlib.sha256(ssid.encode("utf-8")).hexdigest(),
        "security": args.security,
        "credential_source": "env:A90_WIFI_PSK" if args.security in {"wpa2", "wpa3"} else "",
        "autojoin": False,
        "private": True,
        "persistent_storage": False,
        "allow_bssid_lock": False,
        "post_test_cleanup": "disconnect-and-stop-private-session",
    }
    return {
        "version": "v498",
        "mode": "native-init-connect-allowlist",
        "runner_contract": {
            "allow_scan_only_precondition": True,
            "allow_connect": True,
            "allow_dhcp": True,
            "allow_external_ping": True,
            "allow_persistent_storage": False,
            "allow_server_exposure": False,
            "require_v497_scan_only_pass": True,
            "require_usb_local_control": True,
            "require_redacted_evidence": True,
            "require_cleanup_stop_private_session": True,
        },
        "external_ping": {
            "targets": ["1.1.1.1", "8.8.8.8"],
            "count": 3,
            "timeout_sec": 5,
        },
        "targets": [target],
    }, state, []


def add_issue(issues: list[str], target: str, message: str) -> None:
    issues.append(f"{target}: {message}")


def validate_target(target: dict[str, Any], index: int) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    prefix = f"targets[{index}]"
    target_id = target.get("id")
    if not isinstance(target_id, str) or not TARGET_ID_RE.fullmatch(target_id):
        add_issue(issues, prefix, "id must match [A-Za-z0-9_.-]{1,64}")

    ssid_source = target.get("ssid_source")
    if not isinstance(ssid_source, str) or not ENV_SOURCE_RE.fullmatch(ssid_source):
        add_issue(issues, prefix, "ssid_source must be env:A90_WIFI_*")
    elif source_name(ssid_source) != "A90_WIFI_SSID":
        add_issue(issues, prefix, "ssid_source must be env:A90_WIFI_SSID")

    ssid_hash = target.get("ssid_sha256")
    ssid_hash_ready = isinstance(ssid_hash, str) and bool(SHA256_RE.fullmatch(ssid_hash)) and ssid_hash != "0" * 64
    if not ssid_hash_ready:
        add_issue(issues, prefix, "ssid_sha256 must be a real 64-char lowercase sha256")

    security = target.get("security")
    if security not in SECURITY_TYPES:
        add_issue(issues, prefix, "security must be one of open, owe, wpa2, wpa3")

    credential_source = target.get("credential_source")
    if security in {"wpa2", "wpa3"}:
        if not isinstance(credential_source, str) or not ENV_SOURCE_RE.fullmatch(credential_source):
            add_issue(issues, prefix, "wpa2/wpa3 targets require credential_source env:A90_WIFI_*")
        elif source_name(credential_source) != "A90_WIFI_PSK":
            add_issue(issues, prefix, "credential_source must be env:A90_WIFI_PSK")
    elif credential_source not in (None, "", "none"):
        add_issue(issues, prefix, "open/owe targets must not declare credential_source")

    if target.get("autojoin") is not False:
        add_issue(issues, prefix, "autojoin must be false")
    if target.get("persistent_storage") is not False:
        add_issue(issues, prefix, "persistent_storage must be false")
    if target.get("allow_bssid_lock") not in (False, None):
        add_issue(issues, prefix, "BSSID lock remains blocked")
    if target.get("post_test_cleanup") != "disconnect-and-stop-private-session":
        add_issue(issues, prefix, "post_test_cleanup must be disconnect-and-stop-private-session")

    return {
        "id": target_id or f"target-{index}",
        "security": security or "",
        "ssid_source": ssid_source or "",
        "ssid_hash_ready": ssid_hash_ready,
        "credential_source": credential_source if security in {"wpa2", "wpa3"} else "",
        "persistent_storage": target.get("persistent_storage"),
        "post_test_cleanup": target.get("post_test_cleanup"),
    }, issues


def validate_policy(policy: dict[str, Any] | None, policy_text: str) -> dict[str, Any]:
    if policy is None:
        return {
            "present": False,
            "ready": False,
            "decision": "policy-missing",
            "issues": ["policy was not materialized"],
            "targets": [],
            "target_count": 0,
        }
    issues: list[str] = []
    if RAW_SECRET_FIELD_RE.search(policy_text):
        add_issue(issues, "policy", "raw SSID/BSSID/password/passphrase/psk-like fields are forbidden")
    if MAC_RE.search(policy_text):
        add_issue(issues, "policy", "raw BSSID/MAC values are forbidden")
    if policy.get("version") != "v498":
        add_issue(issues, "policy", "version must be v498")
    if policy.get("mode") != "native-init-connect-allowlist":
        add_issue(issues, "policy", "mode must be native-init-connect-allowlist")

    contract = policy.get("runner_contract") or {}
    required_contract = {
        "allow_scan_only_precondition": True,
        "allow_connect": True,
        "allow_dhcp": True,
        "allow_external_ping": True,
        "allow_persistent_storage": False,
        "allow_server_exposure": False,
        "require_v497_scan_only_pass": True,
        "require_usb_local_control": True,
        "require_redacted_evidence": True,
        "require_cleanup_stop_private_session": True,
    }
    for key, expected in required_contract.items():
        if contract.get(key) is not expected:
            add_issue(issues, "runner_contract", f"{key} must be {expected}")

    ping = policy.get("external_ping") or {}
    targets = ping.get("targets")
    if not isinstance(targets, list) or not targets:
        add_issue(issues, "external_ping", "at least one external ping target is required for final proof")
    if ping.get("count", 0) < 1:
        add_issue(issues, "external_ping", "count must be >= 1")
    if ping.get("timeout_sec", 0) < 1:
        add_issue(issues, "external_ping", "timeout_sec must be >= 1")

    raw_targets = policy.get("targets")
    normalized_targets: list[dict[str, Any]] = []
    if not isinstance(raw_targets, list) or not raw_targets:
        add_issue(issues, "targets", "at least one target is required")
    else:
        seen: set[str] = set()
        for index, target in enumerate(raw_targets):
            if not isinstance(target, dict):
                add_issue(issues, f"targets[{index}]", "target must be an object")
                continue
            normalized, target_issues = validate_target(target, index)
            normalized_targets.append(normalized)
            issues.extend(target_issues)
            if normalized["id"] in seen:
                add_issue(issues, f"targets[{index}]", "duplicate target id")
            seen.add(normalized["id"])
    return {
        "present": True,
        "ready": not issues,
        "decision": "policy-ready" if not issues else "policy-review-required",
        "issues": issues,
        "targets": normalized_targets,
        "target_count": len(normalized_targets),
    }


def classify(args: argparse.Namespace,
             policy: dict[str, Any] | None,
             validation: dict[str, Any],
             env_state: dict[str, Any],
             issues: list[str],
             v497: dict[str, Any]) -> dict[str, Any]:
    approval, missing = approval_ok(args)
    state = v497_state(v497)
    synthetic_placeholder_detected = any("synthetic placeholder" in item for item in issues)
    v497_ready = (
        state["decision"] == EXPECTED_V497_DECISION
        and state["pass"]
        and state["scan_only_executed"]
        and state["raw_results_redacted"]
        and not state["connect_executed"]
        and not state["link_up_executed"]
        and not state["wifi_bringup_executed"]
        and not state["credentials_read"]
        and not state["external_ping_executed"]
    )
    if args.command == "plan":
        decision = "v498-native-private-policy-plan-ready"
        pass_ok = True
        reason = "native private target policy plan generated"
        next_step = "run V498 with private Wi-Fi env after or before V497; V499 still requires V497 pass"
    elif not approval:
        decision = "v498-native-private-policy-approval-required"
        pass_ok = False
        reason = "explicit approval flags are required before reading Wi-Fi env values"
        next_step = "rerun with approval flags after setting private env"
    elif issues:
        decision = "v498-native-private-policy-env-missing"
        pass_ok = False
        reason = "required Wi-Fi env values are missing or inconsistent"
        next_step = "set private A90_WIFI_SSID/A90_WIFI_PSK env values and rerun V498"
    elif policy is None:
        decision = "v498-native-private-policy-not-materialized"
        pass_ok = False
        reason = "policy was not materialized"
        next_step = "inspect V498 env state"
    elif not validation.get("ready"):
        decision = "v498-native-private-policy-validation-failed"
        pass_ok = False
        reason = "materialized native policy failed validation"
        next_step = "fix V498 materializer or private policy contract"
    elif v497_ready:
        decision = "v498-native-private-policy-ready"
        pass_ok = True
        reason = "private native policy is ready and V497 scan-only proof is already passing"
        next_step = "implement/run V499 bounded native connect, DHCP, and external ping"
    else:
        decision = "v498-native-private-policy-ready-awaiting-v497"
        pass_ok = True
        reason = "private native policy is ready; V497 scan-only proof is still required before connect"
        next_step = "complete V490-V497, then run V499 bounded native connect/DHCP/external ping"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "approval_ok": approval,
        "missing_approval_flags": missing,
        "env_state": env_state,
        "issues": issues,
        "synthetic_placeholder_detected": synthetic_placeholder_detected,
        "policy_materialized": policy is not None,
        "validation": validation,
        "v497_state": state,
        "v497_ready": v497_ready,
    }


def guardrails() -> list[str]:
    return [
        "host-side private policy materialization only",
        "reads Wi-Fi env values only with explicit approval flags",
        "does not write raw SSID, BSSID, password, passphrase, PSK, or PSK hash",
        "does not execute device commands or mutate device state",
        "does not scan, connect, request DHCP, route traffic, or ping externally",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    env_rows = [
        [name, str(data.get("present"))]
        for name, data in (classification.get("env_state") or {}).items()
    ]
    validation = classification.get("validation") or {}
    target_rows = [
        [
            target.get("id", "-"),
            target.get("security", "-"),
            target.get("ssid_source", "-"),
            target.get("credential_source", "-") or "-",
            str(target.get("persistent_storage", "-")),
            target.get("post_test_cleanup", "-"),
        ]
        for target in validation.get("targets", [])
    ]
    issue_rows = [[issue] for issue in classification.get("issues", []) + validation.get("issues", [])]
    v497_rows = [[key, str(value)] for key, value in classification.get("v497_state", {}).items()]
    return "\n".join(
        [
            "# V498 Native Wi-Fi Private Policy",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {classification.get('next_step', '-')}",
            f"- policy_file: `{manifest.get('policy_file') or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            f"- credentials_read: `{manifest['credentials_read']}`",
            f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
            f"- external_ping_executed: `{manifest['external_ping_executed']}`",
            "",
            "## Env State",
            "",
            markdown_table(["name", "present"], env_rows if env_rows else [["-", "-"]]),
            "",
            "## V497 State",
            "",
            markdown_table(["item", "value"], v497_rows if v497_rows else [["-", "-"]]),
            "",
            "## Policy Targets",
            "",
            markdown_table(["id", "security", "ssid_source", "credential_source", "persistent", "cleanup"], target_rows if target_rows else [["-", "-", "-", "-", "-", "-"]]),
            "",
            "## Issues",
            "",
            markdown_table(["issue"], issue_rows if issue_rows else [["-"]]),
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
    approval, _ = approval_ok(args)
    v497 = load_json(selected_v497(args))
    if args.command == "plan" or not approval:
        policy = None
        env_state = env_presence()
        issues: list[str] = []
        validation = {"present": False, "ready": False, "decision": "not-run", "issues": [], "targets": [], "target_count": 0}
    else:
        policy, env_state, issues = build_policy_from_env(args)
        if policy is not None:
            store.write_json("native-wifi-target-policy.private.json", policy)
            validation = validate_policy(policy, json.dumps(policy, ensure_ascii=False, sort_keys=True))
        else:
            validation = {"present": False, "ready": False, "decision": "env-missing", "issues": issues, "targets": [], "target_count": 0}
    classification = classify(args, policy, validation, env_state, issues, v497)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "target_id": args.target_id,
        "security": args.security,
        "v497": v497_state(v497),
        "policy_file": "native-wifi-target-policy.private.json" if policy is not None else "",
        "classification": classification,
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "cnss_start_executed": False,
        "iwifi_start_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": bool(args.command == "run" and approval),
        "scan_connect_executed": False,
        "connect_executed": False,
        "dhcp_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next_step: {classification['next_step']}")
    print(f"policy_file: {manifest['policy_file'] or '-'}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
