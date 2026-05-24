#!/usr/bin/env python3
"""V799 host-only post-V798 route classifier.

V798 proves the current lower-only path completes modem PIL notifications but
does not publish service-notifier 74/180.  Older service74-positive evidence
already exists, so this classifier reconciles the current negative lower path
with those positive service74/CNSS/PeripheralManager gates and selects the next
smallest live replay.  It does not contact the device.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v799-post-v798-route-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v799-post-v798-route-classifier.txt")
DEFAULT_V798_MANIFEST = Path("tmp/wifi/v798-pil-code-gap-classifier/manifest.json")
DEFAULT_V797_MANIFEST = Path("tmp/wifi/v797-pil-trace-payload/manifest.json")
DEFAULT_V653_MANIFEST = Path("tmp/wifi/v653-service74-gated-live-20260523-085337/manifest.json")
DEFAULT_V657_MANIFEST = Path("tmp/wifi/v657-service74-v106-replay-live/manifest.json")
DEFAULT_V659_MANIFEST = Path("tmp/wifi/v659-vndservicemanager-readiness-only-live/manifest.json")
DEFAULT_V668_MANIFEST = Path("tmp/wifi/v668-cnss2-focused-capture-live/manifest.json")
DEFAULT_V694_MANIFEST = Path("tmp/wifi/v694-peripheral-vndservice-query-orchestrated-live-rerun/manifest.json")
READ_LIMIT_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v798-manifest", type=Path, default=DEFAULT_V798_MANIFEST)
    parser.add_argument("--v797-manifest", type=Path, default=DEFAULT_V797_MANIFEST)
    parser.add_argument("--v653-manifest", type=Path, default=DEFAULT_V653_MANIFEST)
    parser.add_argument("--v657-manifest", type=Path, default=DEFAULT_V657_MANIFEST)
    parser.add_argument("--v659-manifest", type=Path, default=DEFAULT_V659_MANIFEST)
    parser.add_argument("--v668-manifest", type=Path, default=DEFAULT_V668_MANIFEST)
    parser.add_argument("--v694-manifest", type=Path, default=DEFAULT_V694_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def safe_read(path: Path) -> tuple[str, dict[str, Any]]:
    resolved = resolve(path)
    info: dict[str, Any] = {"path": str(resolved), "exists": resolved.exists()}
    if not resolved.exists() or not resolved.is_file():
        return "", info
    data = resolved.read_bytes()[:READ_LIMIT_BYTES]
    info.update({
        "is_file": True,
        "size": resolved.stat().st_size,
        "bytes_read": len(data),
        "truncated": resolved.stat().st_size > len(data),
    })
    return data.decode("utf-8", errors="replace"), info


def load_json(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    if not text:
        return {"file": info, "data": {}}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"file": info, "data": {}, "error": str(exc)}
    return {"file": info, "data": payload if isinstance(payload, dict) else {}}


def get_nested(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "pass"}
    return bool(value)


def best_counts(payload: dict[str, Any]) -> dict[str, int]:
    reason_counts = parse_reason_counts(str(payload.get("reason") or ""))
    candidates = (
        reason_counts,
        get_nested(payload, "arm_v694", "counts", default={}),
        get_nested(payload, "live", "v659_counts", default={}),
        get_nested(payload, "live", "v655_counts", default={}),
        get_nested(payload, "live", "v644_counts", default={}),
        get_nested(payload, "live", "markers", "counts", default={}),
    )
    merged: dict[str, int] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for key, value in candidate.items():
            merged.setdefault(str(key), int_value(value))
    if "service_notifier_180" not in merged and "service_notifier" in merged:
        merged["service_notifier_180"] = 1 if merged["service_notifier"] > 0 else 0
    if "service_notifier_74" not in merged and "service_notifier" in merged:
        merged["service_notifier_74"] = 1 if merged["service_notifier"] > 1 else 0
    if "wlfw_start" not in merged and "wlfw" in merged:
        merged["wlfw_start"] = merged["wlfw"]
    return merged


def parse_reason_counts(reason: str) -> dict[str, int]:
    match = re.search(r"counts=(\{.*?\})(?:;|$)", reason)
    if not match:
        return {}
    try:
        parsed = ast.literal_eval(match.group(1))
    except (SyntaxError, ValueError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): int_value(value) for key, value in parsed.items()}


def summarize_candidate(label: str, entry: dict[str, Any]) -> dict[str, Any]:
    payload = entry["data"]
    counts = best_counts(payload)
    query = get_nested(payload, "arm_v694", "vndservice_query", default={}) or {}
    phases = query.get("phases") if isinstance(query, dict) else {}
    peripheral_seen = False
    if isinstance(phases, dict):
        peripheral_seen = any(bool_value((phase or {}).get("peripheral_seen")) for phase in phases.values() if isinstance(phase, dict))
    return {
        "label": label,
        "path": entry["file"]["path"],
        "exists": entry["file"].get("exists", False),
        "decision": payload.get("decision", ""),
        "pass": bool(payload.get("pass", False)),
        "device_commands_executed": bool(payload.get("device_commands_executed", False)),
        "external_ping_executed": bool(payload.get("external_ping_executed", False)),
        "service180": int_value(counts.get("service_notifier_180")),
        "service74": int_value(counts.get("service_notifier_74")),
        "cnss_netlink": int_value(counts.get("cnss_daemon_netlink")),
        "cnss_cld80211": int_value(counts.get("cnss_daemon_cld80211")),
        "binder_fail": int_value(counts.get("binder_transaction_failed")) + int_value(counts.get("cnss_binder_transaction_failed")),
        "wlfw": int_value(counts.get("wlfw_start")) + int_value(counts.get("wlfw_service_request")),
        "wlan_pd": int_value(counts.get("wlan_pd")),
        "qmi_server_connected": int_value(counts.get("qmi_server_connected")),
        "bdf": int_value(counts.get("bdf_regdb")) + int_value(counts.get("bdf_bdwlan")) + int_value(counts.get("bdf")),
        "wlan0": int_value(counts.get("wlan0")),
        "kernel_warning": int_value(counts.get("kernel_warning")),
        "peripheral_vndservice_seen": peripheral_seen,
    }


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    inputs = {
        "v798": load_json(args.v798_manifest),
        "v797": load_json(args.v797_manifest),
        "v653": load_json(args.v653_manifest),
        "v657": load_json(args.v657_manifest),
        "v659": load_json(args.v659_manifest),
        "v668": load_json(args.v668_manifest),
        "v694": load_json(args.v694_manifest),
    }
    v798 = inputs["v798"]["data"]
    v797 = inputs["v797"]["data"]
    current_gap = {
        "decision": v798.get("decision", ""),
        "modem_pil_sequence_complete": bool(get_nested(v798, "analysis", "derived", "modem_pil_sequence_complete", default=False)),
        "service_notifier_gap": bool(get_nested(v798, "analysis", "derived", "service_notifier_gap_after_modem_powerup", default=False)),
        "mdm3_gap": bool(get_nested(v798, "analysis", "derived", "mdm3_gap_remains", default=False)),
        "service_notifier_current": int_value(get_nested(v798, "analysis", "gap", "native_v797_service_notifier", default=0)),
        "service69_current": int_value(get_nested(v798, "analysis", "gap", "native_v797_service69", default=0)),
        "trace_events": int_value(get_nested(v797, "live", "trace_payload", "event_count", default=0)),
        "external_ping_executed": bool(v797.get("external_ping_executed", False)) or bool(v798.get("external_ping_executed", False)),
    }
    candidates = [
        summarize_candidate(label, inputs[label])
        for label in ("v653", "v657", "v659", "v668", "v694")
    ]
    positive = [
        item for item in candidates
        if item["pass"] and item["service180"] > 0 and item["service74"] > 0
    ]
    peripheral_ready = any(item["peripheral_vndservice_seen"] for item in candidates)
    cnss_tail_ready = any(item["cnss_netlink"] > 0 and item["cnss_cld80211"] > 0 for item in positive)
    wlfw_absent_after_positive = all(item["wlfw"] == 0 and item["wlan_pd"] == 0 and item["wlan0"] == 0 for item in positive)
    return {
        "inputs": {key: value["file"] for key, value in inputs.items()},
        "current_gap": current_gap,
        "candidates": candidates,
        "positive_service74_candidates": positive,
        "derived": {
            "current_lower_only_is_negative": current_gap["modem_pil_sequence_complete"] and current_gap["service_notifier_gap"],
            "service74_positive_path_exists": len(positive) >= 3,
            "peripheral_vndservice_ready": peripheral_ready,
            "cnss_tail_reached_after_service74": cnss_tail_ready,
            "wlfw_still_absent_after_positive_path": wlfw_absent_after_positive,
            "safe_to_select_below_hal_replay": len(positive) >= 3 and peripheral_ready and cnss_tail_ready and wlfw_absent_after_positive,
        },
    }


def build_checks(command: str, analysis: dict[str, Any]) -> list[Check]:
    if command == "plan":
        return [Check("plan-only", "pass", "info", "no device command executed", [], "run host-only classifier")]
    missing = [key for key, info in analysis["inputs"].items() if not info.get("exists")]
    derived = analysis["derived"]
    return [
        Check("inputs", "pass" if not missing else "blocked", "blocker", ",".join(missing), [info["path"] for info in analysis["inputs"].values()], "restore missing evidence manifests"),
        Check("current-gap", "pass" if derived["current_lower_only_is_negative"] else "blocked", "blocker", json.dumps(analysis["current_gap"], sort_keys=True), ["v798", "v797"], "refresh V797/V798 if current lower gap is stale"),
        Check("service74-positive-path", "pass" if derived["service74_positive_path_exists"] else "blocked", "blocker", json.dumps([[item["label"], item["service180"], item["service74"]] for item in analysis["positive_service74_candidates"]]), ["v653", "v657", "v659", "v668", "v694"], "do not widen to CNSS tail without reproducible service74 evidence"),
        Check("peripheral-vndservice", "pass" if derived["peripheral_vndservice_ready"] else "blocked", "blocker", "PeripheralManager vndservice query observed" if derived["peripheral_vndservice_ready"] else "missing", ["v694"], "prove peripheral service registration before CNSS tail retry"),
        Check("cnss-tail-boundary", "pass" if derived["cnss_tail_reached_after_service74"] and derived["wlfw_still_absent_after_positive_path"] else "blocked", "blocker", json.dumps([[item["label"], item["cnss_netlink"], item["cnss_cld80211"], item["wlfw"], item["wlan_pd"], item["wlan0"]] for item in analysis["positive_service74_candidates"]]), ["v653", "v657", "v659", "v668", "v694"], "select below-HAL CNSS tail replay only if WLFW remains absent after service74"),
        Check("safety", "pass", "blocker", "host-only; no HAL, scan/connect, credential, DHCP, external ping, reboot, flash, or partition write", [], "preserve V799 boundary"),
    ]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v799-post-v798-route-classifier-plan-ready", True, "plan-only; no device command executed", "run host-only classifier"
    blocked = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blocked:
        return "v799-post-v798-route-classifier-blocked", False, "blocked by " + ", ".join(blocked), "repair input evidence before selecting live replay"
    return (
        "v799-service74-positive-peripheral-cnss-tail-replay-selected",
        True,
        "current V797 lower-only path is negative, but prior service74-positive paths and V694 PeripheralManager registration show the next useful gate is a below-HAL CNSS tail replay, not another lower-only or custom-kernel attempt",
        "V800 should replay a service74-positive, PeripheralManager-confirmed CNSS tail with PIL trace/readback, still no HAL, scan/connect, credentials, DHCP, routes, or external ping",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    candidate_rows = [
        [
            item["label"],
            item["decision"],
            item["service180"],
            item["service74"],
            item["cnss_netlink"],
            item["cnss_cld80211"],
            item["binder_fail"],
            item["wlfw"],
            item["wlan_pd"],
            item["wlan0"],
            item["peripheral_vndservice_seen"],
        ]
        for item in analysis["candidates"]
    ]
    return "\n".join([
        "# V799 Post-V798 Route Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Current Gap",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["current_gap"].items()]),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["case", "decision", "svc180", "svc74", "cnss_netlink", "cld80211", "binder_fail", "wlfw", "wlan_pd", "wlan0", "peripheral"], candidate_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [[check["name"], check["status"], check["severity"], check["detail"], check["next_step"]] for check in manifest["checks"]]),
        "",
        "## Safety",
        "",
        "- Host-only classifier. No device command executed.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, reboot, flash, partition write, or custom kernel path.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.command == "plan":
        analysis: dict[str, Any] = {
            "inputs": {},
            "current_gap": {},
            "candidates": [],
            "positive_service74_candidates": [],
            "derived": {},
        }
    else:
        analysis = build_analysis(args)
    checks = build_checks(args.command, analysis)
    decision, passed, reason, next_step = decide(args.command, checks, analysis)
    manifest = {
        "cycle": "v799",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "reboot_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
