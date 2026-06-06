#!/usr/bin/env python3
"""V757 host-only Android/native HDD/PLD differential classifier.

V756 showed that live ftrace, dynamic-debug, and kprobe observability are not
available for the current kernel state. This classifier uses existing Android
and native evidence only. It extracts Wi-Fi bring-up timelines and decides
whether existing dmesg differential evidence can locate the HDD/PLD/register
boundary, or whether the next unit must be rollback-safe boot-image/kernel-log
instrumentation feasibility.

It executes no device commands and performs no live mutation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v757-android-native-hdd-pld-diff")
DEFAULT_V753_MANIFEST = Path("tmp/wifi/v753-hdd-pld-prereq-classifier/manifest.json")
DEFAULT_V756_MANIFEST = Path("tmp/wifi/v756-nonftrace-hdd-pld-observability/manifest.json")

ANDROID_INPUTS = {
    "v649-filtered": Path("tmp/wifi/v649-android-full-audio-wifi-handoff-live-20260523-074556/v649-android-full-audio-wifi-recapture-run/android/commands/dmesg-audio-wifi-tail.txt"),
    "v649-unfiltered": Path("tmp/wifi/v649-android-full-audio-wifi-handoff-live-20260523-074556/v649-android-full-audio-wifi-recapture-run/android/commands/dmesg-unfiltered-tail.txt"),
    "v612-filtered": Path("tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/v611-android-lower-surface-recapture-run/android/commands/dmesg-lower-surface-tail.txt"),
    "v622-filtered": Path("tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/v622-android-mdm-helper-timing-recapture-run/android/commands/dmesg-lower-surface-tail.txt"),
}

NATIVE_INPUTS = {
    "v752-summary": Path("tmp/wifi/v752-cnss-then-boot-wlan/summary.md"),
    "v752-dmesg-delta": Path("tmp/wifi/v752-cnss-then-boot-wlan/native/dmesg-delta.txt"),
    "v753-summary": Path("tmp/wifi/v753-hdd-pld-prereq-classifier/summary.md"),
    "v756-focused-dmesg": Path("tmp/wifi/v756-nonftrace-hdd-pld-observability/native/focused-dmesg.txt"),
}

SOURCE_REFS = [
    {
        "name": "android-qcacld-module-init",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341",
        "signal": "__hdd_module_init creates qcwlanstate, initializes PLD/HDD, registers the driver, then logs driver loaded",
    },
    {
        "name": "android-qcacld-boot-wlan-callback",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9406",
        "signal": "boot_wlan callback reaches __hdd_module_init and only marks loaded after successful init",
    },
    {
        "name": "android-qcacld-driver-ops",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c",
        "signal": "wlan_hdd_register_driver is the source-level PLD registration boundary",
    },
]

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
TIME_RE = re.compile(r"\[\s*(\d+\.\d+)\]")

MARKERS = {
    "sysmon_modem": r"sysmon-qmi:.*modem.*SSCTL service",
    "service_180": r"service-notifier:.*(?:180 service|instance 180)",
    "service_74": r"service-notifier:.*74 service",
    "cnss_diag": r"cnss_diag",
    "cnss_daemon": r"cnss-daemon",
    "wlfw_start": r"cnss-daemon wlfw_start: Starting",
    "wlan_pd_ind": r"msm/modem/wlan_pd",
    "icnss_qmi": r"icnss_qmi: QMI Server Connected",
    "bdf_regdb": r"BDF file\s*:\s*regdb\.bin",
    "bdf_bdwlan": r"BDF file\s*:\s*bdwlan\.bin",
    "fw_ready": r"WLAN FW is ready",
    "wlan0": r"\bwlan0\b",
    "hdd_driver_status": r"hdd_sysfs_update_driver_status",
    "hdd_platform_mac": r"hdd_platform_wlan_mac",
    "hdd_open_adapter": r"hdd_open_adapter",
    "hdd_psoc_idle": r"hdd_psoc_idle_timeout_callback",
    "wlan_loading": r"wlan: Loading driver",
    "wlan_driver_loaded": r"wlan: driver loaded",
    "qcwlanstate": r"qcwlanstate",
    "modules_not_initialized": r"Modules not initialized",
    "pld_init": r"\bpld_init\b",
    "hdd_init": r"\bhdd_init\b",
    "wlan_hdd_register_driver": r"\bwlan_hdd_register_driver\b",
}

ORDERED_MARKERS = (
    "sysmon_modem",
    "service_180",
    "service_74",
    "cnss_diag",
    "cnss_daemon",
    "wlfw_start",
    "wlan_pd_ind",
    "icnss_qmi",
    "bdf_regdb",
    "bdf_bdwlan",
    "fw_ready",
    "hdd_driver_status",
    "wlan0",
    "hdd_open_adapter",
)


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
    parser.add_argument("--v753-manifest", type=Path, default=DEFAULT_V753_MANIFEST)
    parser.add_argument("--v756-manifest", type=Path, default=DEFAULT_V756_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def clean_text(text: str) -> str:
    return ANSI_RE.sub("", text).replace("\r", "")


def load_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return clean_text(resolved.read_text(encoding="utf-8", errors="replace"))


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_time(line: str) -> float | None:
    match = TIME_RE.search(line)
    return float(match.group(1)) if match else None


def summarize_text(text: str) -> dict[str, Any]:
    lines = [line for line in text.splitlines() if not line.lstrip().startswith("$ ")]
    summary: dict[str, Any] = {}
    for name, pattern in MARKERS.items():
        regex = re.compile(pattern, re.IGNORECASE)
        matches = [line for line in lines if regex.search(line)]
        summary[name] = {
            "count": len(matches),
            "first_time": first_time(matches[0]) if matches else None,
            "first_line": matches[0][:240] if matches else "",
        }
    return summary


def event_timeline(summary: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for name in ORDERED_MARKERS:
        item = summary.get(name) or {}
        if item.get("count", 0) <= 0:
            continue
        events.append({
            "marker": name,
            "count": item["count"],
            "first_time": item.get("first_time"),
            "first_line": item.get("first_line", ""),
        })
    return events


def max_marker_count(summaries: dict[str, dict[str, Any]], marker: str) -> int:
    return max((int((summary.get(marker) or {}).get("count") or 0) for summary in summaries.values()), default=0)


def first_marker_time(summaries: dict[str, dict[str, Any]], marker: str) -> float | None:
    values = [
        (summary.get(marker) or {}).get("first_time")
        for summary in summaries.values()
        if (summary.get(marker) or {}).get("first_time") is not None
    ]
    return min(values) if values else None


def write_selected_extracts(store: EvidenceStore, text_inputs: dict[str, str]) -> None:
    pattern = re.compile(
        r"sysmon-qmi|service-notifier|wlan_pd|icnss_qmi|BDF file|WLAN FW is ready|"
        r"wlan0|hdd_sysfs_update_driver_status|hdd_platform_wlan_mac|hdd_open_adapter|"
        r"hdd_psoc_idle|wlan: Loading driver|wlan: driver loaded|qcwlanstate|"
        r"Modules not initialized|pld_init|hdd_init|wlan_hdd_register_driver",
        re.IGNORECASE,
    )
    for name, text in text_inputs.items():
        matches = [line for line in text.splitlines() if pattern.search(line)]
        store.write_text(f"host/extract-{name}.txt", "\n".join(matches[:400]) + ("\n" if matches else ""))


def build_analysis(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    android_texts = {name: load_text(path) for name, path in ANDROID_INPUTS.items()}
    native_texts = {name: load_text(path) for name, path in NATIVE_INPUTS.items()}
    write_selected_extracts(store, {**android_texts, **native_texts})
    android_summaries = {name: summarize_text(text) for name, text in android_texts.items()}
    native_summaries = {name: summarize_text(text) for name, text in native_texts.items()}
    v753 = load_json(args.v753_manifest)
    v756 = load_json(args.v756_manifest)
    v753_analysis = v753.get("analysis") or {}
    v753_v752 = v753_analysis.get("v752") or {}
    v756_analysis = v756.get("analysis") or {}
    android_complete = all(max_marker_count(android_summaries, marker) > 0 for marker in ("icnss_qmi", "bdf_regdb", "bdf_bdwlan", "fw_ready", "wlan0"))
    android_pre_qmi_hdd = any(max_marker_count(android_summaries, marker) > 0 for marker in ("wlan_loading", "pld_init", "hdd_init", "wlan_hdd_register_driver", "wlan_driver_loaded"))
    android_post_fw_hdd = any(max_marker_count(android_summaries, marker) > 0 for marker in ("hdd_driver_status", "hdd_platform_mac", "hdd_open_adapter", "hdd_psoc_idle"))
    native_hdd_entry = bool(v753_v752.get("boot_wlan_write_executed")) and int(v753_v752.get("qcwlanstate", 0) or 0) > 0
    native_success_absent = all(int(v753_v752.get(marker, 0) or 0) == 0 for marker in ("icnss_qmi_connected", "fw_ready", "bdf", "wlan0", "wiphy"))
    native_modules_uninitialized = int(v753_v752.get("modules_uninitialized_count", 0) or 0) > 0 or max_marker_count(native_summaries, "modules_not_initialized") > 0
    return {
        "inputs": {
            "android": {name: str(repo_path(path)) for name, path in ANDROID_INPUTS.items()},
            "native": {name: str(repo_path(path)) for name, path in NATIVE_INPUTS.items()},
            "v753_manifest": str(repo_path(args.v753_manifest)),
            "v756_manifest": str(repo_path(args.v756_manifest)),
        },
        "v753": {
            "decision": v753.get("decision", ""),
            "pass": bool(v753.get("pass")),
            "device_mutations": bool(v753.get("device_mutations")),
            "v752": v753_v752,
        },
        "v756": {
            "decision": v756.get("decision", ""),
            "pass": bool(v756.get("pass")),
            "device_mutations": bool(v756.get("device_mutations")),
            "dynamic_debug": v756_analysis.get("dynamic_debug") or {},
            "kprobe": v756_analysis.get("kprobe") or {},
        },
        "android": {
            "summaries": android_summaries,
            "complete_path": android_complete,
            "has_pre_qmi_hdd_boundary": android_pre_qmi_hdd,
            "has_post_fw_hdd_markers": android_post_fw_hdd,
            "first_times": {marker: first_marker_time(android_summaries, marker) for marker in ORDERED_MARKERS},
            "timeline": event_timeline(android_summaries.get("v649-filtered") or {}) + event_timeline(android_summaries.get("v649-unfiltered") or {}),
        },
        "native": {
            "summaries": native_summaries,
            "hdd_entry_proven": native_hdd_entry,
            "success_markers_absent": native_success_absent,
            "modules_uninitialized": native_modules_uninitialized,
            "v752_key_counts": {
                "wlan_loading": int(v753_v752.get("wlan_loading", 0) or 0),
                "hdd_state_major": int(v753_v752.get("hdd_state_major", 0) or 0),
                "qcwlanstate": int(v753_v752.get("qcwlanstate", 0) or 0),
                "driver_loaded": int(v753_v752.get("driver_loaded", 0) or 0),
                "icnss_qmi_connected": int(v753_v752.get("icnss_qmi_connected", 0) or 0),
                "fw_ready": int(v753_v752.get("fw_ready", 0) or 0),
                "bdf": int(v753_v752.get("bdf", 0) or 0),
                "wlan0": int(v753_v752.get("wlan0", 0) or 0),
            },
        },
        "route": {
            "existing_dmesg_can_resolve_hdd_pld": android_pre_qmi_hdd and native_hdd_entry and native_success_absent,
            "live_kernel_observers_available": False,
            "boot_image_instrumentation_needed": android_complete and native_hdd_entry and native_success_absent and not android_pre_qmi_hdd,
        },
        "source_refs": SOURCE_REFS,
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(analysis: dict[str, Any] | None) -> list[Check]:
    if not analysis:
        return []
    v753 = analysis["v753"]
    v756 = analysis["v756"]
    android = analysis["android"]
    native = analysis["native"]
    route = analysis["route"]
    checks: list[Check] = []
    add_check(
        checks,
        "v753-input",
        "pass" if v753["decision"] == "v753-hdd-pld-register-driver-gap-needs-instrumentation" and v753["pass"] else "blocked",
        "blocker",
        f"decision={v753['decision']} pass={v753['pass']} mutations={v753['device_mutations']}",
        [analysis["inputs"]["v753_manifest"]],
        "complete V753 before host-only differential",
    )
    add_check(
        checks,
        "v756-input",
        "pass" if v756["decision"] == "v756-nonftrace-live-observers-exhausted" and v756["pass"] else "blocked",
        "blocker",
        f"decision={v756['decision']} pass={v756['pass']} mutations={v756['device_mutations']}",
        [analysis["inputs"]["v756_manifest"]],
        "complete V756 before selecting instrumentation route",
    )
    add_check(
        checks,
        "android-complete-reference",
        "pass" if android["complete_path"] else "blocked",
        "blocker",
        f"complete_path={android['complete_path']} first_times={android['first_times']}",
        ["host/extract-v649-filtered.txt", "host/extract-v649-unfiltered.txt"],
        "refresh Android reference if QMI/BDF/FW-ready/wlan0 markers are missing",
    )
    add_check(
        checks,
        "native-gap-reference",
        "pass" if native["hdd_entry_proven"] and native["success_markers_absent"] else "blocked",
        "blocker",
        f"hdd_entry={native['hdd_entry_proven']} success_absent={native['success_markers_absent']} counts={native['v752_key_counts']}",
        ["host/extract-v752-summary.txt", "host/extract-v752-dmesg-delta.txt"],
        "rerun native lower-window proof if the gap input is stale",
    )
    add_check(
        checks,
        "android-dmesg-boundary-resolution",
        "pass" if route["existing_dmesg_can_resolve_hdd_pld"] else "review",
        "finding",
        f"pre_qmi_hdd_boundary={android['has_pre_qmi_hdd_boundary']} post_fw_hdd={android['has_post_fw_hdd_markers']}",
        ["host/extract-v649-unfiltered.txt"],
        "if review, existing Android dmesg is not enough to locate PLD/HDD/register-driver",
    )
    add_check(
        checks,
        "instrumentation-need",
        "review" if route["boot_image_instrumentation_needed"] else "pass",
        "finding",
        f"needed={route['boot_image_instrumentation_needed']} live_observers={route['live_kernel_observers_available']}",
        [],
        "if needed, next classify source/boot-image feasibility before patching",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v757-android-native-hdd-pld-diff-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only Android/native differential classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v757-android-native-hdd-pld-diff-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear blocker before selecting V758",
        )
    if not analysis:
        return (
            "v757-android-native-hdd-pld-diff-missing-analysis",
            False,
            "analysis missing",
            "rerun V757",
        )
    route = analysis["route"]
    if route["existing_dmesg_can_resolve_hdd_pld"]:
        return (
            "v757-existing-dmesg-boundary-route-selected",
            True,
            "Android/native dmesg contains enough HDD/PLD boundary markers to choose the next live gate",
            "V758 should implement the selected low-level live gate without boot-image instrumentation",
        )
    if route["boot_image_instrumentation_needed"]:
        return (
            "v757-boot-image-log-instrumentation-selected",
            True,
            "Android proves the full path, native proves HDD entry and success-marker absence, but existing dmesg cannot locate PLD/HDD/register-driver and live tracing routes are closed",
            "V758 should classify rollback-safe kernel/source/boot-image log instrumentation feasibility before any patch",
        )
    return (
        "v757-differential-review-needed",
        True,
        "host-only differential completed but did not select a single route",
        "inspect manifest before V758",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    android = analysis.get("android") or {}
    native = analysis.get("native") or {}
    route = analysis.get("route") or {}
    return "\n".join([
        "# V757 Android/Native HDD/PLD Differential",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- boot_wlan_write_executed: `{manifest['boot_wlan_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- plan only",
        "",
        "## Route",
        "",
        markdown_table(["signal", "value"], [
            ["android_complete_path", android.get("complete_path")],
            ["android_pre_qmi_hdd_boundary", android.get("has_pre_qmi_hdd_boundary")],
            ["android_post_fw_hdd_markers", android.get("has_post_fw_hdd_markers")],
            ["native_hdd_entry_proven", native.get("hdd_entry_proven")],
            ["native_success_markers_absent", native.get("success_markers_absent")],
            ["native_modules_uninitialized", native.get("modules_uninitialized")],
            ["existing_dmesg_can_resolve_hdd_pld", route.get("existing_dmesg_can_resolve_hdd_pld")],
            ["boot_image_instrumentation_needed", route.get("boot_image_instrumentation_needed")],
        ]) if analysis else "- plan only",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis: dict[str, Any] | None = None
    if args.command != "plan":
        store.mkdir("host")
        analysis = build_analysis(args, store)
        store.write_json("host/android-summaries.json", analysis["android"]["summaries"])
        store.write_json("host/native-summaries.json", analysis["native"]["summaries"])
    checks = build_checks(analysis)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v757",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "tracefs_mount_executed": False,
        "ftrace_write_executed": False,
        "dynamic_debug_write_executed": False,
        "kprobe_write_executed": False,
        "boot_wlan_write_executed": False,
        "qcwlanstate_write_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "analysis": analysis or {},
        "checks": [asdict(check) for check in checks],
        "source_refs": SOURCE_REFS,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v757-android-native-hdd-pld-diff.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"boot_wlan_write_executed: {manifest['boot_wlan_write_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
