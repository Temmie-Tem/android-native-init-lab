#!/usr/bin/env python3
"""V807 host-only classifier for pre-WLFW publication overlap gap."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v807-pre-wlfw-overlap-classifier")
DEFAULT_V806_MANIFEST = Path("tmp/wifi/v806-wlfw-service69-live-gate/manifest.json")
DEFAULT_V805_MANIFEST = Path("tmp/wifi/v805-icnss-fw-ready-wlfw-gate-classifier/manifest.json")
DEFAULT_V802_DIRECT_MANIFEST = Path(
    "tmp/wifi/v806-wlfw-service69-live-gate/v802-provider-first-boot-wlan/arm-v802-provider-first-boot-wlan/live/manifest.json"
)
DEFAULT_V752_SOURCE = Path("scripts/revalidation/native_wifi_cnss_then_boot_wlan_v752.py")
DEFAULT_V802_SOURCE = Path("scripts/revalidation/native_wifi_provider_first_boot_wlan_observe_v802.py")

FORBIDDEN_ACTIONS = (
    "device command",
    "custom kernel flash or boot image write",
    "partition write or reboot",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "qcwlanstate or boot_wlan write",
    "esoc0 open or hold",
    "bind/unbind, driver_override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v806-manifest", type=Path, default=DEFAULT_V806_MANIFEST)
    parser.add_argument("--v805-manifest", type=Path, default=DEFAULT_V805_MANIFEST)
    parser.add_argument("--v802-direct-manifest", type=Path, default=DEFAULT_V802_DIRECT_MANIFEST)
    parser.add_argument("--v752-source", type=Path, default=DEFAULT_V752_SOURCE)
    parser.add_argument("--v802-source", type=Path, default=DEFAULT_V802_SOURCE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def line_of(text: str, pattern: str, flags: int = 0) -> int | None:
    regex = re.compile(pattern, flags)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def contains(text: str, pattern: str, flags: int = re.MULTILINE | re.DOTALL) -> bool:
    return re.search(pattern, text, flags) is not None


def timestamp(line: str) -> float | None:
    clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)
    match = re.search(r"\[\s*(\d+(?:\.\d+)?)\]", clean)
    if not match:
        return None
    return float(match.group(1))


def analyze_v806(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v806_manifest)
    signals = manifest.get("signals") if isinstance(manifest.get("signals"), dict) else {}
    checks = manifest.get("checks") if isinstance(manifest.get("checks"), list) else []
    return {
        "manifest": str(repo_path(args.v806_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "signals": signals,
        "checks": [(check.get("name"), check.get("status")) for check in checks if isinstance(check, dict)],
        "service69_absent": manifest.get("decision") == "v806-service69-absent-after-provider-first-boot-wlan"
        and bool(manifest.get("pass"))
        and int_value(signals.get("qrtr_service69")) == 0
        and int_value(signals.get("wlfw")) == 0,
    }


def analyze_v805(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v805_manifest)
    return {
        "manifest": str(repo_path(args.v805_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "ready": manifest.get("decision") == "v805-wlfw-service69-arrival-gate-selected" and bool(manifest.get("pass")),
    }


def analyze_direct(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.v802_direct_manifest)
    live = manifest.get("live") if isinstance(manifest.get("live"), dict) else {}
    helper = live.get("helper_result") if isinstance(live.get("helper_result"), dict) else {}
    children = helper.get("children") if isinstance(helper.get("children"), dict) else {}
    markers = live.get("markers") if isinstance(live.get("markers"), dict) else {}
    counts = markers.get("counts") if isinstance(markers.get("counts"), dict) else {}
    first_lines = markers.get("first_lines") if isinstance(markers.get("first_lines"), dict) else {}
    service_ts = min(
        [value for value in (timestamp(first_lines.get("service_notifier", "")), timestamp(first_lines.get("sysmon_qmi", ""))) if value is not None],
        default=None,
    )
    wlan_loading_ts = timestamp(first_lines.get("wlan_loading", ""))
    child_exit_summary = {
        name: {
            "observable": data.get("observable"),
            "exited": data.get("exited"),
            "exit_code": data.get("exit_code"),
            "signal": data.get("signal"),
            "postflight_safe": data.get("postflight_safe"),
            "start_order": data.get("start_order"),
        }
        for name, data in children.items()
        if isinstance(data, dict)
    }
    critical_children = ("servicemanager", "hwservicemanager", "vndservicemanager", "cnss_daemon_retry")
    critical_exited = all(child_exit_summary.get(name, {}).get("exited") == "1" for name in critical_children)
    critical_safe = all(child_exit_summary.get(name, {}).get("postflight_safe") == "1" for name in critical_children)
    return {
        "manifest": str(repo_path(args.v802_direct_manifest)),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "helper": {
            "order": helper.get("order"),
            "all_postflight_safe": helper.get("all_postflight_safe"),
            "service74_gate": helper.get("service74_gate"),
            "provider_query_exact": helper.get("provider_query_exact"),
            "initial_cnss_suppressed": helper.get("initial_cnss_suppressed"),
            "cnss_retry_started": helper.get("cnss_retry_started"),
            "children": child_exit_summary,
        },
        "counts": counts,
        "qrtr_services_after_boot": live.get("qrtr_services_after_boot") or {},
        "timing": {
            "service_or_sysmon_first_ts": service_ts,
            "wlan_loading_ts": wlan_loading_ts,
            "delta_sec": (wlan_loading_ts - service_ts) if service_ts is not None and wlan_loading_ts is not None else None,
        },
        "child_lifetime_closed_before_boot_result": critical_exited and critical_safe and helper.get("all_postflight_safe") == 1,
        "service_notifier_before_wlan_loading": (
            service_ts is not None and wlan_loading_ts is not None and service_ts < wlan_loading_ts
        ),
        "service69_absent_after_boot": int_value((live.get("qrtr_services_after_boot") or {}).get("69")) == 0,
    }


def analyze_source(args: argparse.Namespace) -> dict[str, Any]:
    v752 = read_text(args.v752_source)
    v802 = read_text(args.v802_source)
    helper_line = line_of(v752, r'helper_item = run_step\(.*"cnss-companion-start-only"', re.DOTALL)
    boot_line = line_of(v752, r'boot_item = run_step\(', re.DOTALL)
    helper_before_boot = (
        helper_line is not None
        and boot_line is not None
        and helper_line < boot_line
        and contains(v752, r'helper_item = run_step\(.*?"cnss-companion-start-only".*?boot_item = run_step\(', re.DOTALL)
    )
    return {
        "v752_source": str(repo_path(args.v752_source)),
        "v802_source": str(repo_path(args.v802_source)),
        "anchors": {
            "v752_helper_run_step": helper_line,
            "v752_boot_run_step": boot_line,
            "v802_provider_first_mode": line_of(v802, r"V802_MODE = "),
            "v802_helper_command": line_of(v802, r"def helper_command"),
        },
        "derived": {
            "v752_helper_completes_before_boot_wlan": helper_before_boot,
            "v802_wraps_v752_sequential_arm": contains(v802, r"import native_wifi_cnss_then_boot_wlan_v752 as v752"),
            "v802_provider_first_mode_used": contains(v802, r"provider-first-cnss-start-only"),
        },
    }


def build_checks(command: str,
                 v805: dict[str, Any],
                 v806: dict[str, Any],
                 direct: dict[str, Any],
                 source: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only classifier; no device command",
            "next_step": "run V807 host-only classifier",
        }]
    derived = source.get("derived") if isinstance(source.get("derived"), dict) else {}
    return [
        {
            "name": "v805-v806-route-ready",
            "status": "pass" if v805.get("ready") and v806.get("service69_absent") else "blocked",
            "detail": {"v805": v805, "v806_decision": v806.get("decision"), "v806_signals": v806.get("signals")},
            "next_step": "complete V805/V806 before selecting overlap route",
        },
        {
            "name": "sequential-source-order-proven",
            "status": "pass" if derived.get("v752_helper_completes_before_boot_wlan") and derived.get("v802_wraps_v752_sequential_arm") else "blocked",
            "detail": {"anchors": source.get("anchors"), "derived": derived},
            "next_step": "inspect V752/V802 source before inferring lifetime",
        },
        {
            "name": "companion-postflight-closed",
            "status": "pass" if direct.get("child_lifetime_closed_before_boot_result") else "blocked",
            "detail": direct.get("helper", {}),
            "next_step": "inspect helper transcript if children were still alive",
        },
        {
            "name": "service-context-precedes-boot-window",
            "status": "pass" if direct.get("service_notifier_before_wlan_loading") else "finding",
            "detail": direct.get("timing", {}),
            "next_step": "if timing is unclear, capture explicit host-side overlap timing in next live gate",
        },
        {
            "name": "service69-still-absent",
            "status": "pass" if direct.get("service69_absent_after_boot") else "finding",
            "detail": {
                "qrtr_services_after_boot": direct.get("qrtr_services_after_boot"),
                "counts": direct.get("counts"),
            },
            "next_step": "if service69 appears, route to ICNSS-QMI handshake classifier",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v807-pre-wlfw-overlap-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V807 classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return "v807-pre-wlfw-overlap-classifier-blocked", False, "blocked by " + ", ".join(blocked), "clear host evidence blocker"
    return (
        "v807-overlapped-companion-boot-wlan-gate-selected",
        True,
        "V806/V802 executed provider-first companion and boot_wlan sequentially; critical companions were postflight-cleaned before boot_wlan, so service74/180 context was not held across the WLFW publication attempt",
        "run V808 bounded live gate with companion services kept alive concurrently across boot_wlan observe, still below HAL/scan/connect",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v805 = analyze_v805(args)
    v806 = analyze_v806(args)
    direct = analyze_direct(args)
    source = analyze_source(args)
    checks = build_checks(args.command, v805, v806, direct, source)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v807",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v805_manifest": str(repo_path(args.v805_manifest)),
            "v806_manifest": str(repo_path(args.v806_manifest)),
            "v802_direct_manifest": str(repo_path(args.v802_direct_manifest)),
            "v752_source": str(repo_path(args.v752_source)),
            "v802_source": str(repo_path(args.v802_source)),
        },
        "v805": v805,
        "v806": v806,
        "v802_direct": direct,
        "source": source,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "reboot_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    direct = manifest["v802_direct"]
    source = manifest["source"]
    rows = [
        ["v806_decision", manifest["v806"].get("decision", "")],
        ["v802_direct_decision", direct.get("decision", "")],
        ["child_lifetime_closed_before_boot_result", str(direct.get("child_lifetime_closed_before_boot_result"))],
        ["service_notifier_before_wlan_loading", str(direct.get("service_notifier_before_wlan_loading"))],
        ["timing", json.dumps(direct.get("timing", {}), sort_keys=True)],
        ["qrtr_services_after_boot", json.dumps(direct.get("qrtr_services_after_boot", {}), sort_keys=True)],
        ["source_derived", json.dumps(source.get("derived", {}), sort_keys=True)],
    ]
    return "\n".join([
        "# V807 Pre-WLFW Overlap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Evidence",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
