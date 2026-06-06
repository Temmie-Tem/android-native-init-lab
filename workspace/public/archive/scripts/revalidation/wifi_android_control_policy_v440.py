#!/usr/bin/env python3
"""V440 host-side Android Wi-Fi control policy gate.

V440 consumes V439 evidence and chooses the next safe operating policy.  It is
host-side only: it does not talk to the device, enable/disable Wi-Fi, scan,
connect, change credentials, send traffic, expose servers, or mutate routing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v440-android-wifi-control-policy")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v439-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def latest_v439_manifest() -> Path | None:
    candidates = sorted(
        [
            path / "manifest.json"
            for path in repo_path("tmp/wifi").glob("v439-android-wifi-post-reenable-handoff-live-*")
            if (path / "manifest.json").exists()
        ],
        key=lambda path: path.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def load_v439(path: Path | None) -> dict[str, Any]:
    manifest = path or latest_v439_manifest()
    if manifest is None:
        return {"present": False, "path": "", "decision": "missing", "pass": False, "state": {}}
    resolved = repo_path(manifest)
    if not resolved.exists():
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False, "state": {}}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    comparison = (payload.get("context") or {}).get("comparison") or {}
    state = comparison.get("state") or (payload.get("classification") or {})
    v439 = comparison.get("v439") or {}
    return {
        "present": True,
        "path": str(resolved),
        "decision": payload.get("decision"),
        "pass": payload.get("pass"),
        "reason": payload.get("reason"),
        "wifi_disable_executed": payload.get("wifi_disable_executed", v439.get("wifi_disable_executed")),
        "wifi_bringup_executed": payload.get("wifi_bringup_executed", v439.get("wifi_bringup_executed")),
        "state": state,
    }


def state_view(v439: dict[str, Any]) -> dict[str, Any]:
    state = v439.get("state") or {}
    summary = state.get("sample_summary") or {}
    return {
        "sample_count": summary.get("sample_count"),
        "enabled_seen": summary.get("enabled_seen"),
        "disabled_seen": summary.get("disabled_seen"),
        "wifi_connected_seen": summary.get("wifi_connected_seen"),
        "exposure_seen": summary.get("exposure_seen"),
        "first_exposure_phase": summary.get("first_exposure_phase"),
        "listener_safe": summary.get("listener_safe"),
        "cleanup_requested": state.get("cleanup_requested"),
        "cleanup_ok": state.get("cleanup_ok"),
        "cleanup_contained": state.get("cleanup_contained"),
        "wifi_disable_executed": v439.get("wifi_disable_executed"),
        "wifi_bringup_executed": v439.get("wifi_bringup_executed"),
    }


def select_policy(v439: dict[str, Any]) -> dict[str, Any]:
    evidence = state_view(v439)
    exposure_seen = bool(evidence.get("exposure_seen"))
    cleanup_contained = bool(evidence.get("cleanup_contained"))
    listener_safe = bool(evidence.get("listener_safe"))
    if not v439.get("present"):
        decision = "v440-android-wifi-policy-missing-v439"
        pass_ok = False
        policy = "blocked"
        reason = "V439 post-reenable observation evidence is missing"
        next_gate = "rerun V439 post-reenable observation"
    elif not v439.get("pass"):
        decision = "v440-android-wifi-policy-v439-failed"
        pass_ok = False
        policy = "blocked"
        reason = "V439 post-reenable observation did not pass"
        next_gate = "repair or rerun V439 before policy selection"
    elif exposure_seen and cleanup_contained and listener_safe:
        decision = "v440-android-wifi-policy-contained-lab-default-pass"
        pass_ok = True
        policy = "contained-lab-default"
        reason = "Android-managed Wi-Fi is functional and externally routed, while cleanup containment is proven"
        next_gate = "V441 exposure-aware Wi-Fi stability plan or credential/target allowlist plan; no server exposure yet"
    elif exposure_seen and not cleanup_contained:
        decision = "v440-android-wifi-policy-cleanup-required"
        pass_ok = False
        policy = "cleanup-required"
        reason = "Android Wi-Fi exposure was observed but cleanup containment was not proven"
        next_gate = "rerun cleanup containment before additional Wi-Fi work"
    elif evidence.get("enabled_seen"):
        decision = "v440-android-wifi-policy-extended-observation-pass"
        pass_ok = True
        policy = "extended-observation"
        reason = "Android Wi-Fi enabled state was observed without active route/DNS/connectivity exposure"
        next_gate = "run longer observation or explicit scan/connect design after credential policy"
    else:
        decision = "v440-android-wifi-policy-reenable-needed-pass"
        pass_ok = True
        policy = "controlled-reenable-needed"
        reason = "V439 did not observe Android Wi-Fi enabled state"
        next_gate = "repeat controlled re-enable before further Wi-Fi control work"
    return {
        "decision": decision,
        "pass": pass_ok,
        "policy": policy,
        "reason": reason,
        "next_gate": next_gate,
        "evidence_state": evidence,
        "policy_rules": [
            "default lab state is Wi-Fi disabled unless a bounded Wi-Fi test is active",
            "Android-managed Wi-Fi may be used only in explicit exposure-aware test windows",
            "cleanup disable must run after Android Wi-Fi exposure tests unless the next step needs continuous Wi-Fi",
            "server exposure remains blocked until binding, ACL, authentication, and listener policy are explicit",
            "explicit scan/connect remains blocked until credential handling and target-network allowlisting are documented",
        ],
        "blocked_actions": [
            "server exposure",
            "unbounded Android Wi-Fi enabled state",
            "explicit scan/connect",
            "credential mutation or capture",
            "external traffic probes outside a bounded test",
            "new Wi-Fi-facing listeners",
        ],
    }


def guardrails() -> list[str]:
    return [
        "host-side policy decision only",
        "no device commands and no device mutations",
        "no Wi-Fi enable/disable, scan/connect, credentials, server exposure, routing mutation, or external probes",
    ]


def plan_policy() -> dict[str, Any]:
    return {
        "decision": "v440-android-wifi-policy-plan-ready",
        "pass": True,
        "policy": "not-selected",
        "reason": "host-side Android Wi-Fi control policy plan generated",
        "next_gate": "run V440 against V439 post-reenable evidence",
        "evidence_state": {},
        "policy_rules": [
            "select contained lab default when V439 proves auto-connect exposure plus cleanup containment",
            "keep server exposure and explicit scan/connect blocked until policy is explicit",
        ],
        "blocked_actions": [
            "server exposure",
            "explicit scan/connect",
            "credential operations",
            "new Wi-Fi-facing listeners",
        ],
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v439 = load_v439(args.v439_manifest)
    policy = plan_policy() if args.command == "plan" else select_policy(v439)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": policy["decision"],
        "pass": policy["pass"],
        "reason": policy["reason"],
        "host": collect_host_metadata(),
        "v439": v439,
        "policy": policy,
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_disable_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    policy = manifest["policy"]
    state_rows = [[key, str(value)] for key, value in policy.get("evidence_state", {}).items()]
    rules_rows = [[item] for item in policy.get("policy_rules", [])]
    blocked_rows = [[item] for item in policy.get("blocked_actions", [])]
    return "\n".join(
        [
            "# V440 Android Wi-Fi Control Policy",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- policy: `{policy['policy']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{policy['next_gate']}`",
            f"- v439_manifest: `{manifest['v439'].get('path') or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_disable_executed: `{manifest['wifi_disable_executed']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Evidence State",
            "",
            markdown_table(["item", "value"], state_rows if state_rows else [["-", "-"]]),
            "",
            "## Policy Rules",
            "",
            markdown_table(["rule"], rules_rows if rules_rows else [["-"]]),
            "",
            "## Blocked Actions",
            "",
            markdown_table(["action"], blocked_rows if blocked_rows else [["-"]]),
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
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"policy: {manifest['policy']['policy']}")
    print(f"next_gate: {manifest['policy']['next_gate']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_disable_executed: {manifest['wifi_disable_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
