#!/usr/bin/env python3
"""V444 explicit Android Wi-Fi scan/connect preflight.

V444 is host-side only.  It consumes the private V442/V443 policy and verifies
that local environment values match the hashed allowlist before any future
explicit scan/connect live run.  It never executes ADB/device commands and never
writes raw SSID/BSSID/password/passphrase/PSK values to evidence.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v444-android-wifi-explicit-connect-preflight")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--policy", type=Path, default=None)
    parser.add_argument("--v441-manifest", type=Path, default=None)
    parser.add_argument("--allow-read-wifi-env", action="store_true")
    parser.add_argument("--i-understand-wifi-secret-env", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def latest_v441_manifest() -> Path | None:
    candidates = sorted(
        [
            path / "manifest.json"
            for path in repo_path("tmp/wifi").glob("v441-android-wifi-exposure-stability-live-*")
            if (path / "manifest.json").exists()
        ],
        key=lambda path: path.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def latest_v443_policy() -> Path | None:
    candidates: list[Path] = []
    for path in repo_path("tmp/wifi").glob("v443-*"):
        manifest = path / "manifest.json"
        if not manifest.exists():
            continue
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("decision") != "v443-wifi-private-policy-materialized-pass":
            continue
        policy_file = payload.get("policy_file")
        if not policy_file:
            continue
        candidate = path / policy_file
        if candidate.exists():
            candidates.append(candidate)
    candidates.sort(key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def load_json(path: Path | None) -> tuple[dict[str, Any] | None, str, str]:
    if path is None:
        return None, "", ""
    resolved = repo_path(path)
    try:
        text = resolved.read_text(encoding="utf-8")
        return json.loads(text), str(resolved), text
    except FileNotFoundError:
        return None, str(resolved), ""
    except json.JSONDecodeError as exc:
        return {"_json_error": str(exc)}, str(resolved), resolved.read_text(encoding="utf-8", errors="replace")


def load_v441(path: Path | None) -> dict[str, Any]:
    manifest = path or latest_v441_manifest()
    payload, resolved, _ = load_json(manifest)
    if payload is None:
        return {"present": False, "path": resolved, "decision": "missing", "pass": False, "state": {}}
    classification = payload.get("classification") or {}
    return {
        "present": True,
        "path": resolved,
        "decision": payload.get("decision"),
        "pass": payload.get("pass"),
        "reason": payload.get("reason"),
        "state": classification,
    }


def approval_ok(args: argparse.Namespace) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not args.allow_read_wifi_env:
        missing.append("--allow-read-wifi-env")
    if not args.i_understand_wifi_secret_env:
        missing.append("--i-understand-wifi-secret-env")
    return not missing, missing


def read_env_state(read_values: bool) -> tuple[dict[str, Any], dict[str, str]]:
    import os

    values: dict[str, str] = {}
    state: dict[str, Any] = {}
    for name in ("A90_WIFI_SSID", "A90_WIFI_PSK"):
        value = os.environ.get(name, "")
        state[name] = {"present": name in os.environ, "length": len(value)}
        if read_values:
            values[name] = value
    return state, values


def source_name(source: Any) -> str:
    return source.split(":", 1)[1] if isinstance(source, str) and source.startswith("env:") else ""


def command_template(target: dict[str, Any]) -> str:
    security = str(target.get("security"))
    parts = ["cmd", "wifi", "connect-network", "$A90_WIFI_SSID", security]
    if security in {"wpa2", "wpa3"}:
        parts.append("$A90_WIFI_PSK")
    if target.get("autojoin") is False:
        parts.append("-d")
    if target.get("metered") is True:
        parts.append("-m")
    if target.get("private") is True:
        parts.append("-p")
    randomization = target.get("mac_randomization")
    if randomization and randomization != "auto":
        parts.extend(["-r", str(randomization)])
    return " ".join(parts)


def build_command_plan(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for target in policy.get("targets") or []:
        target_id = target.get("id", "target")
        rows.extend(
            [
                {"target": target_id, "phase": "enable", "command": "cmd wifi set-wifi-enabled enabled"},
                {"target": target_id, "phase": "scan", "command": "cmd wifi start-scan"},
                {"target": target_id, "phase": "scan-results", "command": "cmd wifi list-scan-results", "evidence_rule": "redact SSID/BSSID before write"},
                {"target": target_id, "phase": "connect", "command": command_template(target), "evidence_rule": "do not write env values"},
                {"target": target_id, "phase": "observe", "command": "cmd wifi status + route/connectivity/listener captures"},
                {"target": target_id, "phase": "cleanup", "command": "cmd wifi list-networks; cmd wifi forget-network <resolved-id>; cmd wifi set-wifi-enabled disabled"},
            ]
        )
    return rows


def validate_env_against_policy(policy: dict[str, Any], env_values: dict[str, str]) -> dict[str, Any]:
    issues: list[str] = []
    target_rows: list[dict[str, Any]] = []
    for index, target in enumerate(policy.get("targets") or []):
        prefix = f"targets[{index}]"
        ssid_env = source_name(target.get("ssid_source"))
        ssid = env_values.get(ssid_env, "")
        ssid_hash = hashlib.sha256(ssid.encode("utf-8")).hexdigest() if ssid else ""
        expected_hash = target.get("ssid_sha256")
        if not ssid:
            issues.append(f"{prefix}: {ssid_env or 'ssid env'} is missing")
        elif ssid_hash != expected_hash:
            issues.append(f"{prefix}: SSID sha256 does not match policy")

        security = target.get("security")
        credential_env = source_name(target.get("credential_source"))
        credential = env_values.get(credential_env, "") if credential_env else ""
        if security in {"wpa2", "wpa3"}:
            if not credential:
                issues.append(f"{prefix}: {credential_env or 'credential env'} is missing")
            elif not (8 <= len(credential) <= 63):
                issues.append(f"{prefix}: WPA passphrase length must be 8..63 characters")
        elif credential:
            issues.append(f"{prefix}: credential env must be empty for open/owe")
        target_rows.append(
            {
                "id": target.get("id"),
                "security": security,
                "ssid_env": ssid_env,
                "ssid_hash_match": bool(ssid and ssid_hash == expected_hash),
                "credential_env": credential_env,
                "credential_present": bool(credential),
                "credential_length": len(credential),
                "command_template": command_template(target),
            }
        )
    return {"ready": not issues, "issues": issues, "targets": target_rows, "target_count": len(target_rows)}


def classify(
    args: argparse.Namespace,
    v441: dict[str, Any],
    policy: dict[str, Any] | None,
    policy_path: str,
    policy_validation: dict[str, Any],
    env_validation: dict[str, Any],
    env_state: dict[str, Any],
) -> dict[str, Any]:
    state = v441.get("state") or {}
    v441_ready = (
        bool(v441.get("present"))
        and bool(v441.get("pass"))
        and bool(state.get("stable_all_samples"))
        and bool(state.get("cleanup_contained"))
        and bool(state.get("listener_safe"))
    )
    approval, missing = approval_ok(args)
    if args.command == "plan":
        decision = "v444-wifi-explicit-connect-preflight-plan-ready"
        pass_ok = True
        reason = "explicit scan/connect preflight plan generated"
        next_gate = "run V444 with a private policy and Wi-Fi env values"
    elif not v441.get("present"):
        decision = "v444-wifi-explicit-connect-preflight-missing-v441"
        pass_ok = False
        reason = "V441 evidence is missing"
        next_gate = "rerun V441 before explicit scan/connect preflight"
    elif not v441_ready:
        decision = "v444-wifi-explicit-connect-preflight-v441-not-ready"
        pass_ok = False
        reason = "V441 did not prove stable Wi-Fi exposure and cleanup containment"
        next_gate = "repair or rerun V441"
    elif policy is None:
        decision = "v444-wifi-explicit-connect-preflight-missing-policy"
        pass_ok = False
        reason = "private Wi-Fi target policy is missing"
        next_gate = "run V443 after setting private env values"
    elif not policy_validation.get("ready"):
        decision = "v444-wifi-explicit-connect-preflight-policy-invalid"
        pass_ok = False
        reason = "private Wi-Fi target policy failed V442 validation"
        next_gate = "fix or regenerate private policy"
    elif not approval:
        decision = "v444-wifi-explicit-connect-preflight-approval-required"
        pass_ok = False
        reason = "explicit approval is required before reading Wi-Fi env values"
        next_gate = "rerun with approval flags"
    elif not env_validation.get("ready"):
        decision = "v444-wifi-explicit-connect-preflight-env-invalid"
        pass_ok = False
        reason = "Wi-Fi env values are missing or do not match the private policy"
        next_gate = "set matching private env values and rerun V444"
    else:
        decision = "v444-wifi-explicit-connect-preflight-ready"
        pass_ok = True
        reason = "private policy, env hashes, and command plan are ready for a bounded explicit scan/connect live gate"
        next_gate = "V445 bounded explicit scan/connect live run; server exposure remains blocked"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
        "v441_ready": v441_ready,
        "policy_path": policy_path,
        "policy_validation": policy_validation,
        "env_state": env_state,
        "env_validation": env_validation,
        "approval_ok": approval,
        "missing_approval_flags": missing,
        "command_plan": build_command_plan(policy) if policy else [],
    }


def guardrails() -> list[str]:
    return [
        "host-side preflight only",
        "no ADB/device commands and no device mutations",
        "raw SSID/BSSID/password/passphrase/PSK values are never written",
        "server exposure and external packet probes remain blocked",
        "future live run must cleanup forget-network and disable Wi-Fi",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    env_rows = [[name, str(data.get("present")), str(data.get("length"))] for name, data in (classification.get("env_state") or {}).items()]
    target_rows = [
        [
            target.get("id", "-"),
            target.get("security", "-"),
            target.get("ssid_env", "-"),
            str(target.get("ssid_hash_match", "-")),
            target.get("credential_env", "-") or "-",
            str(target.get("credential_present", "-")),
            str(target.get("credential_length", "-")),
            target.get("command_template", "-"),
        ]
        for target in (classification.get("env_validation") or {}).get("targets", [])
    ]
    issue_rows = [[issue] for issue in (classification.get("env_validation") or {}).get("issues", [])]
    issue_rows.extend([[issue] for issue in (classification.get("policy_validation") or {}).get("issues", [])])
    command_rows = [
        [item.get("target", "-"), item.get("phase", "-"), item.get("command", "-"), item.get("evidence_rule", "-")]
        for item in classification.get("command_plan", [])
    ]
    return "\n".join(
        [
            "# V444 Explicit Wi-Fi Scan/connect Preflight",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{classification.get('next_gate', '-')}`",
            f"- policy_path: `{classification.get('policy_path') or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Env State",
            "",
            markdown_table(["name", "present", "length"], env_rows if env_rows else [["-", "-", "-"]]),
            "",
            "## Target Validation",
            "",
            markdown_table(
                ["id", "security", "ssid_env", "hash_match", "credential_env", "credential_present", "credential_length", "command_template"],
                target_rows if target_rows else [["-", "-", "-", "-", "-", "-", "-", "-"]],
            ),
            "",
            "## Command Plan",
            "",
            markdown_table(["target", "phase", "command", "evidence_rule"], command_rows if command_rows else [["-", "-", "-", "-"]]),
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
    v441 = load_v441(args.v441_manifest)
    policy_path = args.policy or latest_v443_policy()
    policy, resolved_policy_path, policy_text = load_json(policy_path)
    policy_validation = validate_policy(policy, policy_text)
    approval, _ = approval_ok(args)
    env_state, env_values = read_env_state(read_values=(args.command == "run" and approval and policy is not None and policy_validation.get("ready")))
    env_validation = validate_env_against_policy(policy, env_values) if policy and policy_validation.get("ready") and approval else {"ready": False, "issues": [], "targets": [], "target_count": 0}
    classification = classify(args, v441, policy, resolved_policy_path, policy_validation, env_validation, env_state)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "v441": v441,
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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
