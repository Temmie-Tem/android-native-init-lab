#!/usr/bin/env python3
"""V434 host-side Android Wi-Fi auto-connect policy gate.

V434 consumes V433 containment evidence and selects the next safe Wi-Fi policy.
It does not talk to the device directly and does not enable Wi-Fi, scan,
connect, change credentials, send traffic, start daemons, or mutate routing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v434-android-wifi-autoconnect-policy")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v433-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def latest_v433_manifest() -> Path | None:
    patterns = [
        "v433-android-autoconnect-containment-handoff-live-redactfix2-*",
        "v433-android-autoconnect-containment-handoff-live-redactfix-*",
        "v433-android-autoconnect-containment-handoff-live-*",
    ]
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(repo_path("tmp/wifi").glob(pattern))
    manifests = sorted(
        [candidate / "manifest.json" for candidate in candidates if (candidate / "manifest.json").exists()],
        key=lambda path: path.stat().st_mtime,
    )
    return manifests[-1] if manifests else None


def load_v433(path: Path | None) -> dict[str, Any]:
    manifest = path or latest_v433_manifest()
    if manifest is None:
        return {"present": False, "path": "", "decision": "missing", "pass": False, "state": {}}
    resolved = repo_path(manifest)
    if not resolved.exists():
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False, "state": {}}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    comparison = (payload.get("context") or {}).get("comparison") or {}
    state = comparison.get("state") or (payload.get("classification") or {})
    return {
        "present": True,
        "path": str(resolved),
        "decision": payload.get("decision"),
        "pass": payload.get("pass"),
        "reason": payload.get("reason"),
        "wifi_bringup_executed": payload.get("wifi_bringup_executed"),
        "state": state,
    }


def bool_state(state: dict[str, Any], key: str) -> bool:
    return bool(state.get(key))


def select_policy(v433: dict[str, Any]) -> dict[str, Any]:
    state = v433.get("state") or {}
    v433_pass = bool(v433.get("pass"))
    exposure = any(
        bool_state(state, key)
        for key in (
            "default_route_wlan",
            "route_get_wlan",
            "connectivity_validated_wifi",
            "dns_surface_wlan",
        )
    )
    connected = bool_state(state, "wifi_connected")
    stable = bool_state(state, "wifi_connected_stable") and bool_state(state, "route_stable")
    listener = bool_state(state, "global_listener_observed")

    if not v433.get("present"):
        decision = "v434-android-wifi-policy-missing-v433"
        pass_ok = False
        policy = "blocked"
        reason = "V433 containment evidence is missing"
        next_gate = "rerun V433 containment before policy selection"
    elif not v433_pass:
        decision = "v434-android-wifi-policy-v433-failed"
        pass_ok = False
        policy = "blocked"
        reason = "V433 containment evidence did not pass"
        next_gate = "repair V433 containment before policy selection"
    elif exposure and listener:
        decision = "v434-android-wifi-policy-hard-contain-pass"
        pass_ok = True
        policy = "hard-contain-first"
        reason = "V433 mapped Wi-Fi exposure and global listeners; server exposure must remain blocked"
        next_gate = "V435 disable/contain auto-connect and listener surface before any server work"
    elif exposure and connected and stable:
        decision = "v434-android-wifi-policy-contain-first-pass"
        pass_ok = True
        policy = "contain-first"
        reason = "V433 mapped stable Wi-Fi auto-connect with route/DNS exposure; choose containment before serverization"
        next_gate = "V435 bounded auto-connect disable/containment proof; no scan/connect/server exposure"
    elif exposure:
        decision = "v434-android-wifi-policy-review-exposure-pass"
        pass_ok = True
        policy = "review-exposure"
        reason = "V433 mapped Wi-Fi exposure, but stability markers were incomplete"
        next_gate = "V435 repeat containment or cleanup policy proof"
    elif connected:
        decision = "v434-android-wifi-policy-stability-first-pass"
        pass_ok = True
        policy = "stability-first"
        reason = "V433 mapped connected Wi-Fi without route/DNS exposure; continue bounded read-only stability"
        next_gate = "V435 longer read-only Wi-Fi stability window"
    else:
        decision = "v434-android-wifi-policy-enable-gate-reconsider-pass"
        pass_ok = True
        policy = "enable-gate-reconsider"
        reason = "V433 did not show active auto-connect; enable-only gate may be reconsidered"
        next_gate = "V435 enable-only or status gate, still no scan/connect credentials"

    return {
        "decision": decision,
        "pass": pass_ok,
        "policy": policy,
        "reason": reason,
        "next_gate": next_gate,
        "evidence_state": {
            "wifi_connected": state.get("wifi_connected"),
            "wifi_connected_stable": state.get("wifi_connected_stable"),
            "wlan0_has_ip": state.get("wlan0_has_ip"),
            "default_route_wlan": state.get("default_route_wlan"),
            "route_get_wlan": state.get("route_get_wlan"),
            "route_stable": state.get("route_stable"),
            "connectivity_validated_wifi": state.get("connectivity_validated_wifi"),
            "dns_surface_wlan": state.get("dns_surface_wlan"),
            "global_listener_observed": state.get("global_listener_observed"),
        },
        "blocked_actions": [
            "server exposure",
            "explicit scan/connect",
            "credential operations",
            "DHCP or routing mutation",
            "external packet probes",
            "new listeners on Wi-Fi-facing routes",
        ],
        "allowed_next_actions": allowed_next_actions(policy),
    }


def allowed_next_actions(policy: str) -> list[str]:
    if policy in {"contain-first", "hard-contain-first"}:
        return [
            "bounded Wi-Fi disable/containment proof",
            "post-cleanup route/DNS/listener verification",
            "native rollback verification",
            "documentation of lab auto-connect policy",
        ]
    if policy == "stability-first":
        return [
            "longer read-only route/DNS/connectivity stability sampling",
            "listener-surface sampling",
            "native rollback verification",
        ]
    if policy == "enable-gate-reconsider":
        return [
            "enable-only plan with immediate cleanup",
            "status-only recheck",
            "native rollback verification",
        ]
    return [
        "manual evidence review",
        "repeat read-only containment sampling",
        "native rollback verification",
    ]


def guardrails() -> list[str]:
    return [
        "host-side policy selection only",
        "no device commands and no device mutations",
        "no Wi-Fi enable/disable, scan/connect, credentials, DHCP/routing mutation, or external packet probes",
        "server exposure remains blocked unless a later gate explicitly changes policy",
    ]


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v433 = load_v433(args.v433_manifest)
    if args.command == "plan":
        policy = {
            "decision": "v434-android-wifi-policy-plan-ready",
            "pass": True,
            "policy": "not-selected",
            "reason": "host-side Android Wi-Fi auto-connect policy gate plan generated",
            "next_gate": "run V434 against V433 containment evidence",
            "evidence_state": {},
            "blocked_actions": [
                "server exposure",
                "explicit scan/connect",
                "credential operations",
                "DHCP or routing mutation",
                "external packet probes",
            ],
            "allowed_next_actions": ["host-side policy selection from V433 evidence"],
        }
    else:
        policy = select_policy(v433)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": policy["decision"],
        "pass": policy["pass"],
        "reason": policy["reason"],
        "host": collect_host_metadata(),
        "v433": v433,
        "policy": policy,
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    policy = manifest["policy"]
    state_rows = [[key, str(value)] for key, value in policy.get("evidence_state", {}).items()]
    blocked_rows = [[item] for item in policy.get("blocked_actions", [])]
    allowed_rows = [[item] for item in policy.get("allowed_next_actions", [])]
    return "\n".join(
        [
            "# V434 Android Wi-Fi Auto-connect Policy Gate",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- policy: `{policy['policy']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{policy['next_gate']}`",
            f"- v433_manifest: `{manifest['v433'].get('path') or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Evidence State",
            "",
            markdown_table(["item", "value"], state_rows if state_rows else [["-", "-"]]),
            "",
            "## Blocked Actions",
            "",
            markdown_table(["action"], blocked_rows if blocked_rows else [["-"]]),
            "",
            "## Allowed Next Actions",
            "",
            markdown_table(["action"], allowed_rows if allowed_rows else [["-"]]),
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
