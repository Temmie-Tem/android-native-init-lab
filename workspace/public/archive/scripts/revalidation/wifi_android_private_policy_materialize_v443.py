#!/usr/bin/env python3
"""V443 private Wi-Fi target policy materializer.

V443 is host-side only.  It may read A90_WIFI_SSID/A90_WIFI_PSK from the process
environment only when explicitly approved, then writes a private V442-compatible
policy containing hashes and env references, never raw network identifiers or
credentials.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_android_target_policy_v442 import validate_policy


DEFAULT_OUT_DIR = Path("tmp/wifi/v443-android-wifi-private-policy")
SECURITY_TYPES = ("open", "owe", "wpa2", "wpa3")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--target-id", default="lab-primary")
    parser.add_argument("--security", choices=SECURITY_TYPES, default="wpa2")
    parser.add_argument("--allow-read-wifi-env", action="store_true")
    parser.add_argument("--i-understand-wifi-secret-env", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def approval_ok(args: argparse.Namespace) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not args.allow_read_wifi_env:
        missing.append("--allow-read-wifi-env")
    if not args.i_understand_wifi_secret_env:
        missing.append("--i-understand-wifi-secret-env")
    return not missing, missing


def read_env_present() -> dict[str, Any]:
    import os

    return {
        "A90_WIFI_SSID": {
            "present": "A90_WIFI_SSID" in os.environ,
            "length": len(os.environ.get("A90_WIFI_SSID", "")),
        },
        "A90_WIFI_PSK": {
            "present": "A90_WIFI_PSK" in os.environ,
            "length": len(os.environ.get("A90_WIFI_PSK", "")),
        },
    }


def build_policy_from_env(args: argparse.Namespace) -> tuple[dict[str, Any] | None, dict[str, Any], list[str]]:
    import os

    env_state = read_env_present()
    issues: list[str] = []
    ssid = os.environ.get("A90_WIFI_SSID", "")
    psk = os.environ.get("A90_WIFI_PSK", "")
    if not ssid:
        issues.append("A90_WIFI_SSID is required")
    if args.security in {"wpa2", "wpa3"} and not psk:
        issues.append("A90_WIFI_PSK is required for wpa2/wpa3")
    if args.security in {"open", "owe"} and psk:
        issues.append("A90_WIFI_PSK must be unset for open/owe")
    if not ssid or issues:
        return None, env_state, issues

    target: dict[str, Any] = {
        "id": args.target_id,
        "ssid_source": "env:A90_WIFI_SSID",
        "ssid_sha256": hashlib.sha256(ssid.encode("utf-8")).hexdigest(),
        "security": args.security,
        "autojoin": False,
        "metered": True,
        "private": True,
        "mac_randomization": "non_persistent",
        "allow_bssid_lock": False,
        "post_test_cleanup": "forget-network-and-disable-wifi",
    }
    if args.security in {"wpa2", "wpa3"}:
        target["credential_source"] = "env:A90_WIFI_PSK"
    policy = {
        "version": "v442",
        "mode": "explicit-scan-connect-allowlist",
        "runner_contract": {
            "allow_start_scan": True,
            "allow_connect_network": True,
            "allow_add_network": False,
            "allow_forget_network_cleanup": True,
            "allow_external_probes": False,
            "allow_server_exposure": False,
            "require_cleanup_disable": True,
            "require_native_rollback": True,
        },
        "targets": [target],
    }
    return policy, env_state, []


def classify(args: argparse.Namespace, policy: dict[str, Any] | None, validation: dict[str, Any], env_state: dict[str, Any], issues: list[str]) -> dict[str, Any]:
    approval, missing = approval_ok(args)
    if args.command == "plan":
        decision = "v443-wifi-private-policy-materialize-plan-ready"
        pass_ok = True
        reason = "private policy materialization plan generated"
        next_gate = "run with A90_WIFI_SSID/A90_WIFI_PSK env and explicit approval flags"
    elif not approval:
        decision = "v443-wifi-private-policy-approval-required"
        pass_ok = False
        reason = "explicit approval flags are required before reading Wi-Fi env values"
        next_gate = "rerun with approval flags after setting private env"
    elif issues:
        decision = "v443-wifi-private-policy-env-missing"
        pass_ok = False
        reason = "required Wi-Fi env values are missing or inconsistent"
        next_gate = "set private env values and rerun V443"
    elif policy is None:
        decision = "v443-wifi-private-policy-not-materialized"
        pass_ok = False
        reason = "policy was not materialized"
        next_gate = "inspect V443 env state"
    elif validation.get("ready"):
        decision = "v443-wifi-private-policy-materialized-pass"
        pass_ok = True
        reason = "private policy materialized and validated without storing raw network identifiers or credentials"
        next_gate = "V444 explicit scan/connect preflight can consume the private policy"
    else:
        decision = "v443-wifi-private-policy-validation-failed"
        pass_ok = False
        reason = "materialized policy failed V442 validation"
        next_gate = "fix V443 materializer or policy contract before scan/connect"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
        "approval_ok": approval,
        "missing_approval_flags": missing,
        "env_state": env_state,
        "issues": issues,
        "policy_materialized": policy is not None,
        "validation": validation,
    }


def guardrails() -> list[str]:
    return [
        "host-side private policy materialization only",
        "reads Wi-Fi env values only with explicit approval flags",
        "does not write raw SSID, BSSID, password, passphrase, or PSK",
        "does not execute device commands or mutate device state",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    env_rows = [
        [name, str(data.get("present")), str(data.get("length"))]
        for name, data in (classification.get("env_state") or {}).items()
    ]
    issue_rows = [[issue] for issue in classification.get("issues", [])]
    validation = classification.get("validation") or {}
    validation_rows = [
        ["ready", validation.get("ready", "-")],
        ["target_count", validation.get("target_count", "-")],
        ["decision", validation.get("decision", "-")],
    ]
    return "\n".join(
        [
            "# V443 Private Wi-Fi Target Policy Materializer",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{classification.get('next_gate', '-')}`",
            f"- policy_file: `{manifest.get('policy_file') or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Env State",
            "",
            markdown_table(["name", "present", "length"], env_rows if env_rows else [["-", "-", "-"]]),
            "",
            "## Validation",
            "",
            markdown_table(["item", "value"], [[str(a), str(b)] for a, b in validation_rows]),
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
    if args.command == "plan" or not approval:
        policy = None
        env_state = read_env_present()
        issues: list[str] = []
        validation = {"present": False, "ready": False, "decision": "not-run", "issues": [], "targets": [], "target_count": 0}
    else:
        policy, env_state, issues = build_policy_from_env(args)
        if policy is not None:
            store.write_json("wifi-target-policy.private.json", policy)
            validation = validate_policy(policy, json.dumps(policy, ensure_ascii=False, sort_keys=True))
        else:
            validation = {"present": False, "ready": False, "decision": "env-missing", "issues": issues, "targets": [], "target_count": 0}
    classification = classify(args, policy, validation, env_state, issues)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "target_id": args.target_id,
        "security": args.security,
        "policy_file": "wifi-target-policy.private.json" if policy is not None else "",
        "classification": classification,
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next_gate: {classification['next_gate']}")
    print(f"policy_file: {manifest['policy_file'] or '-'}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
