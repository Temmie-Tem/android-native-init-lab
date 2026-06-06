#!/usr/bin/env python3
"""V496 native Wi-Fi scan-only contract gate.

This host-side gate prepares the step after V495. It does not execute device
commands and it does not read credentials. It verifies that V495 produced a
bounded active-session WLAN surface, then selects the next implementation
strategy for a native-init scan-only proof.

The selected strategy is intentionally an integrated execns helper mode, not a
standalone host/native command: scan must occur while the private service
manager, HAL, CNSS, and IWifi.start surface are alive in the helper-owned
namespace. Android `cmd wifi`, `wpa_supplicant`, and standalone post-cleanup
probes are explicitly rejected as substitutes for the native-init path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v496-native-wifi-scan-only-contract")
EXPECTED_V495_DECISION = "v495-native-active-session-surface-observed-cleaned"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v495-manifest", type=Path, default=None)
    parser.add_argument("--nl80211-ro-source", type=Path, default=Path("stage3/linux_init/helpers/a90_nl80211_ro.c"))
    parser.add_argument("--execns-helper-source", type=Path, default=Path("stage3/linux_init/helpers/a90_android_execns_probe.c"))
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


def latest_v495_manifest() -> Path | None:
    candidates: list[Path] = []
    for path in repo_path("tmp/wifi").glob("v495*/manifest.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("decision") == EXPECTED_V495_DECISION:
            candidates.append(path)
    candidates.sort(key=lambda item: item.stat().st_mtime)
    return candidates[-1] if candidates else None


def selected_v495(args: argparse.Namespace) -> Path | None:
    return args.v495_manifest or latest_v495_manifest()


def source_state(path: Path, tokens: list[str]) -> dict[str, Any]:
    resolved = repo_path(path)
    result: dict[str, Any] = {
        "path": str(resolved),
        "present": resolved.exists(),
        "tokens": {token: False for token in tokens},
    }
    if not resolved.exists():
        return result
    text = resolved.read_text(encoding="utf-8", errors="replace")
    result["tokens"] = {token: token in text for token in tokens}
    return result


def v495_state(v495: dict[str, Any]) -> dict[str, Any]:
    live = v495.get("live_result") or {}
    active = live.get("active_session") or {}
    return {
        "path": v495.get("path", ""),
        "present": bool(v495.get("present")),
        "decision": v495.get("decision", ""),
        "pass": bool(v495.get("pass")),
        "active_session_started": bool(live.get("active_session_started")) or active.get("begin") == "1",
        "surface_observed": bool(live.get("surface_present_after_iwifi_start")) or bool(live.get("surface_present_during")),
        "cleanup_clean": bool((v495.get("postflight") or {}).get("clean")) if v495.get("postflight") else False,
        "surface_after_cleanup": bool(live.get("surface_present_after_cleanup")),
        "wifi_bringup_executed": bool(v495.get("wifi_bringup_executed")),
        "credentials_read": bool(v495.get("credentials_read")),
        "scan_connect_executed": bool(v495.get("scan_connect_executed")),
        "external_ping_executed": bool(v495.get("external_ping_executed")),
    }


def strategy_matrix(args: argparse.Namespace) -> list[dict[str, Any]]:
    nl80211 = source_state(args.nl80211_ro_source, [
        "NL80211_CMD_GET_WIPHY",
        "NL80211_CMD_GET_INTERFACE",
        "NL80211_CMD_TRIGGER_SCAN",
        "NL80211_CMD_GET_SCAN",
    ])
    execns = source_state(args.execns_helper_source, [
        "wifi-active-session-surface",
        "wifi_active_session.begin",
        "wifi_scan_only.begin",
        "NL80211_CMD_TRIGGER_SCAN",
    ])
    return [
        {
            "name": "execns-integrated-nl80211-scan",
            "status": "selected",
            "reason": "scan must run inside the same bounded helper-owned active session before cleanup",
            "next_version": "v497",
            "requires_new_helper_mode": "wifi-active-session-scan-only",
            "source": execns,
        },
        {
            "name": "standalone-a90-nl80211-ro",
            "status": "not-sufficient",
            "reason": "current helper is read-only and cannot coordinate with the V495 active-session lifetime",
            "next_version": "",
            "source": nl80211,
        },
        {
            "name": "android-cmd-wifi-start-scan",
            "status": "rejected",
            "reason": "framework command path is not native-init and bypasses the HAL/CNSS namespace proof chain",
            "next_version": "",
            "source": {},
        },
        {
            "name": "wpa-supplicant-scan",
            "status": "rejected",
            "reason": "supplicant introduces association/credential state and belongs after a scan-only native proof",
            "next_version": "",
            "source": {},
        },
    ]


def build_checks(command: str, v495: dict[str, Any]) -> list[dict[str, Any]]:
    state = v495_state(v495)
    if command == "plan":
        return [
            {
                "name": "plan-only",
                "status": "pass",
                "severity": "info",
                "detail": "no device command executed",
                "next_step": "run preflight after V495 surface-observed-cleaned exists",
            }
        ]
    v495_ready = (
        state["decision"] == EXPECTED_V495_DECISION
        and state["pass"]
        and state["active_session_started"]
        and state["surface_observed"]
        and state["cleanup_clean"]
        and not state["surface_after_cleanup"]
        and not state["wifi_bringup_executed"]
        and not state["credentials_read"]
        and not state["scan_connect_executed"]
        and not state["external_ping_executed"]
    )
    return [
        {
            "name": "v495-active-session-surface-ready",
            "status": "pass" if v495_ready else "blocked",
            "severity": "blocker",
            "detail": (
                f"path={state['path']} present={state['present']} "
                f"decision={state['decision']} active={state['active_session_started']} "
                f"surface={state['surface_observed']} cleanup_clean={state['cleanup_clean']} "
                f"surface_after_cleanup={state['surface_after_cleanup']}"
            ),
            "next_step": "run V495 active-session proof and pass its surface-observed-cleaned manifest",
        }
    ]


def classify(command: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v496-native-scan-only-contract-plan-ready",
            "pass": True,
            "reason": "host-side scan-only contract plan generated; no device command executed",
            "next_step": "run V496 preflight after V495 surface-observed-cleaned",
        }
    blockers = [check["name"] for check in checks if check["severity"] == "blocker" and check["status"] != "pass"]
    if blockers:
        return {
            "decision": "v496-native-scan-only-contract-blocked",
            "pass": False,
            "reason": "required active-session proof missing or incomplete: " + ", ".join(blockers),
            "next_step": "complete V490/V491/V492/V493/V494/V495 first",
        }
    return {
        "decision": "v496-native-scan-only-contract-ready",
        "pass": True,
        "reason": "V495 active-session evidence is ready; implement integrated nl80211 scan-only helper mode next",
        "next_step": "implement v497 helper mode wifi-active-session-scan-only; still no credentials/connect/DHCP/ping",
    }


def guardrails() -> list[str]:
    return [
        "host-side contract classification only",
        "no device commands and no device mutations",
        "no SSID/PSK env reads",
        "no scan/connect/DHCP/routing/external ping execution in V496",
        "scan-only implementation must redact SSID/BSSID/details and report only counts plus bounded status",
        "scan-only implementation must run inside the helper-owned active session before cleanup",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [item["name"], item["status"], item["severity"], item["detail"], item["next_step"]]
        for item in manifest["checks"]
    ]
    strategy_rows = [
        [item["name"], item["status"], item["reason"], item.get("requires_new_helper_mode", ""), item.get("next_version", "")]
        for item in manifest["strategy_matrix"]
    ]
    state_rows = [[key, str(value)] for key, value in manifest["v495_state"].items()]
    return "\n".join(
        [
            "# V496 Native Wi-Fi Scan-Only Contract",
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
            "",
            "## V495 State",
            "",
            markdown_table(["item", "value"], state_rows),
            "",
            "## Checks",
            "",
            markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
            "",
            "## Strategy Matrix",
            "",
            markdown_table(["name", "status", "reason", "new_mode", "next_version"], strategy_rows),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v495 = load_json(selected_v495(args))
    checks = build_checks(args.command, v495)
    classification = classify(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "v495_state": v495_state(v495),
        "checks": checks,
        "strategy_matrix": strategy_matrix(args),
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "cnss_start_executed": False,
        "iwifi_start_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
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
