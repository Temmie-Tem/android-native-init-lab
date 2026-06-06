#!/usr/bin/env python3
"""V494 native Wi-Fi active-session gate.

This host-side gate connects the V490..V493 native-init SELinux/HAL chain to
the real end goal: a bounded native Wi-Fi session that can eventually scan,
connect, obtain IPv4, and prove external ping.  It never executes device
commands and never reads credentials.  Its main job is to prevent a false jump
from the cleaned-up V493 `IWifi.start()` proof to V462 ping: V493 intentionally
cleans up helper-owned daemons, so a successful cleaned surface still needs a
new bounded active-session helper before scan/connect/ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v494-native-wifi-active-session-gate")
CHAIN = (
    (
        "v490",
        "tmp/wifi/v490*/manifest.json",
        "v490-selinux-policy-load-proof-pass",
        "policy_load_executed",
        "run V490 approved SELinux policy-load proof first",
    ),
    (
        "v491",
        "tmp/wifi/v491*/manifest.json",
        "v491-post-load-domain-handoff-present",
        "",
        "run V491 post-load domain proof with the V490 pass manifest",
    ),
    (
        "v492",
        "tmp/wifi/v492*/manifest.json",
        "v492-samsung-registration-post-load-present",
        "",
        "run V492 Samsung registration proof with the V491 pass manifest",
    ),
    (
        "v493",
        "tmp/wifi/v493*/manifest.json",
        "",
        "",
        "run V493 post-registration IWifi.start surface proof with the V492 pass manifest",
    ),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v490-manifest", type=Path, default=None)
    parser.add_argument("--v491-manifest", type=Path, default=None)
    parser.add_argument("--v492-manifest", type=Path, default=None)
    parser.add_argument("--v493-manifest", type=Path, default=None)
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


def latest_manifest(pattern: str, expected_decision: str) -> Path | None:
    candidates: list[Path] = []
    for path in repo_path(".").glob(pattern):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if expected_decision and payload.get("decision") != expected_decision:
            continue
        candidates.append(path)
    candidates.sort(key=lambda item: item.stat().st_mtime)
    return candidates[-1] if candidates else None


def selected_paths(args: argparse.Namespace) -> dict[str, Path | None]:
    explicit = {
        "v490": args.v490_manifest,
        "v491": args.v491_manifest,
        "v492": args.v492_manifest,
        "v493": args.v493_manifest,
    }
    paths: dict[str, Path | None] = {}
    for version, pattern, expected, _, _ in CHAIN:
        paths[version] = explicit[version] or latest_manifest(pattern, expected)
    if paths["v493"] is None:
        paths["v493"] = latest_manifest("tmp/wifi/v493*/manifest.json", "")
    return paths


def check_chain(paths: dict[str, Path | None]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for version, _, expected_decision, required_flag, next_step in CHAIN:
        manifest = load_json(paths.get(version))
        decision = manifest.get("decision", "")
        flag_ok = True if not required_flag else manifest.get(required_flag) is True
        expected_ok = True if not expected_decision else decision == expected_decision
        pass_ok = bool(manifest.get("pass")) and expected_ok and flag_ok
        checks.append(
            {
                "name": f"{version}-ready",
                "status": "pass" if pass_ok else "blocked",
                "path": manifest.get("path", ""),
                "decision": decision,
                "pass": bool(manifest.get("pass")),
                "required_flag": required_flag,
                "required_flag_ok": flag_ok,
                "expected_decision": expected_decision,
                "next_step": next_step,
            }
        )
    return checks


def v493_surface_state(v493: dict[str, Any]) -> dict[str, Any]:
    live = v493.get("live_result") or {}
    decision = str(v493.get("decision") or "")
    return {
        "decision": decision,
        "iwifi_transaction_executed": bool(v493.get("iwifi_start_executed")),
        "surface_observed": decision == "v493-iwifi-start-post-registration-surface-observed-cleaned"
        or bool(live.get("surface_present_after_iwifi_start"))
        or bool(live.get("surface_present_during")),
        "service_null": decision == "v493-iwifi-start-post-registration-service-null",
        "transaction_failed": decision == "v493-iwifi-start-post-registration-transaction-failed",
        "no_surface_delta": decision == "v493-iwifi-start-post-registration-no-surface-delta",
        "cleanup_clean": bool((v493.get("postflight") or {}).get("clean")) if v493.get("postflight") else False,
        "surface_after_cleanup": bool(live.get("surface_present_after_cleanup")),
        "wifi_bringup_executed": bool(v493.get("wifi_bringup_executed")),
        "scan_connect_executed": bool(v493.get("scan_connect_executed")),
        "external_ping_executed": bool(v493.get("external_ping_executed")),
    }


def planned_active_session_contract() -> list[dict[str, str]]:
    return [
        {
            "version": "v495",
            "gate": "active-session helper contract",
            "purpose": "extend helper beyond cleanup-only V493 into a bounded keepalive window with HAL/CNSS/IWifi.start still alive",
        },
        {
            "version": "v496",
            "gate": "native scan-only proof",
            "purpose": "run scan/list result observation only after a live active-session surface exists; still no credentials",
        },
        {
            "version": "v497",
            "gate": "native credential materializer",
            "purpose": "consume A90_WIFI_SSID/A90_WIFI_PSK from env under explicit approval and write only private redacted evidence",
        },
        {
            "version": "v498",
            "gate": "native connect DHCP external ping",
            "purpose": "bounded connect, IPv4 route acquisition, interface-bound external ping, and cleanup/rollback evidence",
        },
    ]


def classify(command: str, checks: list[dict[str, Any]], v493: dict[str, Any]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v494-native-wifi-active-session-plan-ready",
            "pass": True,
            "reason": "host-side active-session gate plan generated; no device command executed",
            "next_step": "run preflight after V490/V491/V492/V493 pass manifests exist",
            "branch": "plan",
        }
    blocked = [check["name"] for check in checks if check["status"] != "pass"]
    if blocked:
        return {
            "decision": "v494-native-wifi-active-session-blocked",
            "pass": False,
            "reason": "required upstream proof missing or not passing: " + ", ".join(blocked),
            "next_step": next(check["next_step"] for check in checks if check["status"] != "pass"),
            "branch": "upstream-blocked",
        }
    surface = v493_surface_state(v493)
    if surface["wifi_bringup_executed"] or surface["scan_connect_executed"] or surface["external_ping_executed"]:
        return {
            "decision": "v494-native-wifi-active-session-review-required",
            "pass": False,
            "reason": "V493 manifest unexpectedly reports scan/connect/bring-up/ping execution",
            "next_step": "inspect V493 evidence before widening scope",
            "branch": "unexpected-v493-mutation",
        }
    if surface["surface_after_cleanup"]:
        return {
            "decision": "v494-native-wifi-active-session-cleanup-review-required",
            "pass": False,
            "reason": "V493 left a WLAN surface after cleanup; device state must be inspected before connect/ping",
            "next_step": "run cleanup/reboot review before any active Wi-Fi test",
            "branch": "cleanup-review",
        }
    if surface["surface_observed"] and surface["cleanup_clean"]:
        return {
            "decision": "v494-native-wifi-active-session-contract-ready",
            "pass": True,
            "reason": "V493 proved a transient WLAN surface and clean cleanup; direct V462 ping is insufficient because the surface is intentionally gone after cleanup",
            "next_step": "implement V495 bounded active-session helper before native scan/connect/ping",
            "branch": "active-session-needed",
        }
    if surface["service_null"]:
        return {
            "decision": "v494-native-wifi-active-session-service-null",
            "pass": True,
            "reason": "V493 still lacks IWifi/default despite earlier registration evidence",
            "next_step": "inspect V492/V493 service-manager namespace mismatch before active-session work",
            "branch": "service-null",
        }
    if surface["transaction_failed"]:
        return {
            "decision": "v494-native-wifi-active-session-transaction-review",
            "pass": True,
            "reason": "IWifi.start transaction executed but did not return cleanly",
            "next_step": "inspect raw hwbinder reply before active-session work",
            "branch": "transaction-review",
        }
    if surface["no_surface_delta"]:
        return {
            "decision": "v494-native-wifi-active-session-driver-gap",
            "pass": True,
            "reason": "IWifi.start returned cleanly but no WLAN/wiphy/rfkill surface appeared",
            "next_step": "route to driver/CNSS mode-set primitive before scan/connect",
            "branch": "driver-gap",
        }
    return {
        "decision": "v494-native-wifi-active-session-review-required",
        "pass": False,
        "reason": "V493 result does not map to a known active-session branch",
        "next_step": "inspect V493 manifest and helper transcript",
        "branch": "unclassified",
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [
            check["name"],
            check["status"],
            check["decision"],
            str(check["pass"]),
            check["path"] or "-",
            check["next_step"],
        ]
        for check in manifest["checks"]
    ]
    contract_rows = [
        [item["version"], item["gate"], item["purpose"]]
        for item in manifest["planned_active_session_contract"]
    ]
    surface = manifest["v493_surface_state"]
    surface_rows = [[key, str(value)] for key, value in surface.items()]
    return "\n".join(
        [
            "# V494 Native Wi-Fi Active-Session Gate",
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
            "## Chain Checks",
            "",
            markdown_table(["name", "status", "decision", "pass", "path", "next"], check_rows),
            "",
            "## V493 Surface State",
            "",
            markdown_table(["item", "value"], surface_rows if surface_rows else [["-", "-"]]),
            "",
            "## Planned Active-Session Contract",
            "",
            markdown_table(["version", "gate", "purpose"], contract_rows),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    paths = selected_paths(args)
    loaded = {version: load_json(path) for version, path in paths.items()}
    checks = check_chain(paths)
    classification = classify(args.command, checks, loaded["v493"])
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "branch": classification["branch"],
        "host": collect_host_metadata(),
        "selected_manifests": {key: value.get("path", "") for key, value in loaded.items()},
        "checks": checks,
        "v493_surface_state": v493_surface_state(loaded["v493"]),
        "planned_active_session_contract": planned_active_session_contract(),
        "guardrails": [
            "host-side classification only",
            "no device commands and no device mutations",
            "no credential env reads and no raw SSID/BSSID/password/passphrase/PSK evidence",
            "does not scan, connect, DHCP, route, or ping",
            "does not treat cleaned-up V493 surfaces as persistent connectivity",
        ],
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
