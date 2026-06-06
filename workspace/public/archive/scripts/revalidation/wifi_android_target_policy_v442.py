#!/usr/bin/env python3
"""V442 Android Wi-Fi target and credential policy gate.

V442 is host-side only.  It turns the V441 functional Wi-Fi proof into a
precondition contract for any later explicit scan/connect test.  It never reads
or writes real Wi-Fi credentials, never executes ADB/device commands, and never
prints SSID/BSSID/passphrase values.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v442-android-wifi-target-policy")
SECRET_FIELD_RE = re.compile(r'"(?:ssid|bssid|password|passphrase|psk|pre_shared_key|targetConfigKey)"\s*:', re.IGNORECASE)
MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ENV_SOURCE_RE = re.compile(r"^env:A90_WIFI_[A-Z0-9_]+$")
TARGET_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SECURITY_TYPES = {"open", "owe", "wpa2", "wpa3"}
RANDOMIZATION_TYPES = {"auto", "none", "persistent", "non_persistent"}


POLICY_TEMPLATE: dict[str, Any] = {
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
    "targets": [
        {
            "id": "lab-primary",
            "ssid_source": "env:A90_WIFI_SSID",
            "ssid_sha256": "<64 lowercase hex sha256 of SSID bytes>",
            "security": "wpa2",
            "credential_source": "env:A90_WIFI_PSK",
            "autojoin": False,
            "metered": True,
            "private": True,
            "mac_randomization": "non_persistent",
            "allow_bssid_lock": False,
            "post_test_cleanup": "forget-network-and-disable-wifi",
        }
    ],
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v441-manifest", type=Path, default=None)
    parser.add_argument("--policy", type=Path, default=None)
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
        "wifi_enable_executed": payload.get("wifi_enable_executed"),
        "wifi_disable_executed": payload.get("wifi_disable_executed"),
        "wifi_bringup_executed": payload.get("wifi_bringup_executed"),
        "state": classification,
    }


def source_reference_rows() -> list[list[str]]:
    return [
        [
            "AOSP WifiShellCommand android13",
            "connect-network accepts ssid/security/passphrase plus flags like -d, -p, -b, -r",
            "https://android.googlesource.com/platform/packages/modules/Wifi/+/refs/heads/android13-release/service/java/com/android/server/wifi/WifiShellCommand.java",
        ],
        [
            "AOSP Wi-Fi network selection",
            "Android can auto-select/connect saved networks based on scan results and quality",
            "https://source.android.com/docs/core/connect/wifi-network-selection",
        ],
        [
            "Android Developers save networks",
            "Saved configuration APIs can trigger connection after accepted configuration",
            "https://developer.android.com/develop/connectivity/wifi/wifi-save-network-passpoint-config",
        ],
    ]


def add_issue(issues: list[str], target: str, message: str) -> None:
    issues.append(f"{target}: {message}")


def source_name(source: Any) -> str:
    return source.split(":", 1)[1] if isinstance(source, str) and source.startswith("env:") else ""


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
        add_issue(issues, prefix, "ssid_source must be env:A90_WIFI_SSID for V443")

    ssid_hash = target.get("ssid_sha256")
    hash_ready = isinstance(ssid_hash, str) and bool(SHA256_RE.fullmatch(ssid_hash)) and ssid_hash != "0" * 64
    if not hash_ready:
        add_issue(issues, prefix, "ssid_sha256 must be a real 64-char lowercase sha256, not a placeholder")

    security = target.get("security")
    if security not in SECURITY_TYPES:
        add_issue(issues, prefix, "security must be one of open, owe, wpa2, wpa3")

    credential_source = target.get("credential_source")
    if security in {"wpa2", "wpa3"}:
        if not isinstance(credential_source, str) or not ENV_SOURCE_RE.fullmatch(credential_source):
            add_issue(issues, prefix, "wpa2/wpa3 targets require credential_source env:A90_WIFI_*")
        elif source_name(credential_source) != "A90_WIFI_PSK":
            add_issue(issues, prefix, "credential_source must be env:A90_WIFI_PSK for V443")
    elif credential_source not in (None, "", "none"):
        add_issue(issues, prefix, "open/owe targets must not declare credential_source")

    if target.get("autojoin") is not False:
        add_issue(issues, prefix, "autojoin must be false so future connect uses -d")
    if target.get("post_test_cleanup") != "forget-network-and-disable-wifi":
        add_issue(issues, prefix, "post_test_cleanup must be forget-network-and-disable-wifi")
    if target.get("allow_bssid_lock") not in (False, None):
        add_issue(issues, prefix, "BSSID lock is blocked until scan-result redaction/selection is designed")
    randomization = target.get("mac_randomization", "non_persistent")
    if randomization not in RANDOMIZATION_TYPES:
        add_issue(issues, prefix, "mac_randomization must be auto, none, persistent, or non_persistent")

    command_flags = ["-d"]
    if target.get("metered") is True:
        command_flags.append("-m")
    if target.get("private") is True:
        command_flags.append("-p")
    if randomization != "auto":
        command_flags.extend(["-r", randomization])
    return {
        "id": target_id or f"target-{index}",
        "security": security,
        "ssid_source": ssid_source,
        "ssid_hash_ready": hash_ready,
        "credential_source": credential_source if security in {"wpa2", "wpa3"} else "",
        "autojoin": target.get("autojoin"),
        "post_test_cleanup": target.get("post_test_cleanup"),
        "command_template": "cmd wifi connect-network $A90_WIFI_SSID "
        + str(security or "<security>")
        + (" $A90_WIFI_PSK" if security in {"wpa2", "wpa3"} else "")
        + (" " + " ".join(command_flags) if command_flags else ""),
    }, issues


def validate_policy(policy: dict[str, Any] | None, policy_text: str) -> dict[str, Any]:
    if policy is None:
        return {
            "present": False,
            "ready": False,
            "decision": "policy-missing",
            "issues": ["policy file was not provided"],
            "targets": [],
            "target_count": 0,
        }
    if "_json_error" in policy:
        return {
            "present": True,
            "ready": False,
            "decision": "policy-json-invalid",
            "issues": [str(policy["_json_error"])],
            "targets": [],
            "target_count": 0,
        }
    issues: list[str] = []
    if SECRET_FIELD_RE.search(policy_text):
        add_issue(issues, "policy", "raw SSID/BSSID/password/passphrase/psk-like fields are forbidden")
    if MAC_RE.search(policy_text):
        add_issue(issues, "policy", "raw BSSID/MAC values are forbidden")
    if policy.get("version") != "v442":
        add_issue(issues, "policy", "version must be v442")
    if policy.get("mode") != "explicit-scan-connect-allowlist":
        add_issue(issues, "policy", "mode must be explicit-scan-connect-allowlist")

    contract = policy.get("runner_contract") or {}
    required_contract = {
        "allow_start_scan": True,
        "allow_connect_network": True,
        "allow_add_network": False,
        "allow_forget_network_cleanup": True,
        "allow_external_probes": False,
        "allow_server_exposure": False,
        "require_cleanup_disable": True,
        "require_native_rollback": True,
    }
    for key, expected in required_contract.items():
        if contract.get(key) is not expected:
            add_issue(issues, "runner_contract", f"{key} must be {expected}")

    raw_targets = policy.get("targets")
    targets: list[dict[str, Any]] = []
    if not isinstance(raw_targets, list) or not raw_targets:
        add_issue(issues, "targets", "at least one target is required for live scan/connect readiness")
    else:
        seen: set[str] = set()
        for index, target in enumerate(raw_targets):
            if not isinstance(target, dict):
                add_issue(issues, f"targets[{index}]", "target must be an object")
                continue
            normalized, target_issues = validate_target(target, index)
            targets.append(normalized)
            issues.extend(target_issues)
            if normalized["id"] in seen:
                add_issue(issues, f"targets[{index}]", "duplicate target id")
            seen.add(normalized["id"])
    return {
        "present": True,
        "ready": not issues,
        "decision": "policy-ready" if not issues else "policy-review-required",
        "issues": issues,
        "targets": targets,
        "target_count": len(targets),
    }


def classify(v441: dict[str, Any], policy_validation: dict[str, Any], command: str) -> dict[str, Any]:
    state = v441.get("state") or {}
    v441_ready = (
        bool(v441.get("present"))
        and bool(v441.get("pass"))
        and bool(state.get("stable_all_samples"))
        and bool(state.get("cleanup_contained"))
        and bool(state.get("listener_safe"))
    )
    if command == "plan":
        decision = "v442-wifi-target-policy-plan-ready"
        pass_ok = True
        reason = "host-side target and credential policy plan generated"
        next_gate = "run V442 against V441 evidence and optional private target policy"
    elif not v441.get("present"):
        decision = "v442-wifi-target-policy-missing-v441"
        pass_ok = False
        reason = "V441 exposure-aware stability evidence is missing"
        next_gate = "rerun V441 before target policy"
    elif not v441_ready:
        decision = "v442-wifi-target-policy-v441-not-ready"
        pass_ok = False
        reason = "V441 did not prove stable exposure plus cleanup containment"
        next_gate = "rerun or repair V441 before target policy"
    elif not policy_validation.get("present"):
        decision = "v442-wifi-target-policy-template-pass"
        pass_ok = True
        reason = "V441 is ready; generated secret-free target policy template, but no private target policy was provided"
        next_gate = "create a private untracked V442 policy file before V443 explicit scan/connect preflight"
    elif policy_validation.get("ready"):
        decision = "v442-wifi-target-policy-allowlist-ready"
        pass_ok = True
        reason = "private target policy is valid and contains no raw credentials or network identifiers"
        next_gate = "V443 explicit scan/connect preflight can be planned; server exposure remains blocked"
    else:
        decision = "v442-wifi-target-policy-review-required"
        pass_ok = False
        reason = "target policy exists but failed the V442 safety contract"
        next_gate = "fix the private policy file before any explicit scan/connect work"
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_gate": next_gate,
        "v441_ready": v441_ready,
        "policy_validation": policy_validation,
        "blocked_actions": [
            "raw SSID/BSSID/password/passphrase in tracked files or evidence",
            "server exposure",
            "external packet probes",
            "unbounded autojoin persistence",
            "explicit scan/connect without private target allowlist",
        ],
        "v443_contract": [
            "read SSID from A90_WIFI_SSID and verify sha256 before use",
            "read PSK from A90_WIFI_PSK only for wpa2/wpa3 and never write it to evidence",
            "use cmd wifi connect-network with -d and cleanup forget-network-and-disable-wifi",
            "redact scan results before writing evidence",
            "restore native v319 and keep server exposure blocked",
        ],
    }


def guardrails() -> list[str]:
    return [
        "host-side policy gate only",
        "no device commands and no device mutations",
        "no raw SSID, BSSID, passphrase, password, or PSK values in policy/evidence",
        "no server exposure or external packet probes",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    validation = classification.get("policy_validation") or {}
    state_rows = [[key, str(value)] for key, value in (manifest["v441"].get("state") or {}).items() if key in {"sample_count", "exposure_sample_count", "stable_all_samples", "cleanup_contained", "listener_safe"}]
    target_rows = [
        [
            target.get("id", "-"),
            target.get("security", "-"),
            target.get("ssid_source", "-"),
            target.get("credential_source", "-") or "-",
            target.get("command_template", "-"),
        ]
        for target in validation.get("targets", [])
    ]
    issue_rows = [[item] for item in validation.get("issues", [])]
    return "\n".join(
        [
            "# V442 Android Wi-Fi Target Policy",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{classification.get('next_gate', '-')}`",
            f"- v441_manifest: `{manifest['v441'].get('path') or '-'}`",
            f"- policy_path: `{manifest.get('policy_path') or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## V441 Evidence",
            "",
            markdown_table(["item", "value"], state_rows if state_rows else [["-", "-"]]),
            "",
            "## Policy Targets",
            "",
            markdown_table(["id", "security", "ssid_source", "credential_source", "command_template"], target_rows if target_rows else [["-", "-", "-", "-", "-"]]),
            "",
            "## Policy Issues",
            "",
            markdown_table(["issue"], issue_rows if issue_rows else [["-"]]),
            "",
            "## References",
            "",
            markdown_table(["source", "relevance", "url"], source_reference_rows()),
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
    policy_payload, policy_path, policy_text = load_json(args.policy)
    policy_validation = validate_policy(policy_payload, policy_text)
    classification = classify(v441, policy_validation, args.command)
    store.write_json("target-policy.template.json", POLICY_TEMPLATE)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "v441": v441,
        "policy_path": policy_path,
        "policy_template_file": "target-policy.template.json",
        "classification": classification,
        "references": source_reference_rows(),
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
