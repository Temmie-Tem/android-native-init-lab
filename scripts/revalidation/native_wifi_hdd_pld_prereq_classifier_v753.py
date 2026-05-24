#!/usr/bin/env python3
"""V753 read-only HDD/PLD prerequisite classifier.

This runner consumes V752 evidence, captures the current native WLAN/ICNSS
surface read-only, and classifies the remaining static WLAN driver gap between
HDD init entry and driver-loaded / ICNSS-QMI / firmware-ready progression.

It does not write boot_wlan, qcwlanstate, bind/unbind, driver_override, module
state, subsystem state, daemon state, service-manager, Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v753-hdd-pld-prereq-classifier")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_WLANBOOTCTL = "/cache/bin/a90_wlanbootctl"
DEFAULT_V752_MANIFEST = Path("tmp/wifi/v752-cnss-then-boot-wlan/manifest.json")
DEFAULT_V752_DMESG = Path("tmp/wifi/v752-cnss-then-boot-wlan/native/dmesg-delta.txt")
DEFAULT_V752_BOOT = Path("tmp/wifi/v752-cnss-then-boot-wlan/native/boot-wlan-observe-after-cnss.txt")
DEFAULT_V703_REPORT = Path("docs/reports/NATIVE_INIT_V703_ANDROID_NATIVE_BINDING_COMPARE_2026-05-24.md")

SOURCE_REFS = [
    {
        "name": "android-qcacld-module-init",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341",
        "signal": "__hdd_module_init creates qcwlanstate, calls pld_init/hdd_init, registers the driver, then logs driver loaded",
    },
    {
        "name": "android-qcacld-boot-wlan-callback",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9406",
        "signal": "static boot_wlan callback calls __hdd_module_init and sets loaded_state only after success",
    },
    {
        "name": "android-qcacld-qcwlanstate-wait",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9266",
        "signal": "qcwlanstate ON waits for cds_is_driver_loaded before completing",
    },
    {
        "name": "android-qcacld-driver-ops",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c",
        "signal": "wlan_hdd_register_driver delegates to PLD driver registration in the Android QCACLD tree",
    },
]

FORBIDDEN_TERMS = (
    "boot-observe",
    "boot_wlan 1",
    "qcwlanstate on",
    "echo ",
    "/bind",
    "/unbind",
    "driver_override",
    "insmod",
    "rmmod",
    "modprobe",
    "subsys_esoc0",
    "servicemanager",
    "hwservicemanager",
    "vndservicemanager",
    "android.hardware.wifi",
    "wificond",
    "wpa_supplicant",
    "hostapd",
    "svc wifi",
    "cmd wifi",
    " iw ",
    "dhcp",
    " ip route",
    " ip addr",
    " ping ",
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
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--wlanbootctl", default=DEFAULT_WLANBOOTCTL)
    parser.add_argument("--v752-manifest", type=Path, default=DEFAULT_V752_MANIFEST)
    parser.add_argument("--v752-dmesg", type=Path, default=DEFAULT_V752_DMESG)
    parser.add_argument("--v752-boot", type=Path, default=DEFAULT_V752_BOOT)
    parser.add_argument("--v703-report", type=Path, default=DEFAULT_V703_REPORT)
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def validate_device_command(command: list[str]) -> None:
    joined = " ".join(command)
    lowered = joined.lower()
    for term in FORBIDDEN_TERMS:
        if term in lowered:
            raise RuntimeError(f"forbidden V753 command term {term!r}: {joined}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    validate_device_command(command)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    item = capture_to_manifest(capture)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item["payload"] = payload
    item["file"] = f"native/{safe_name(name)}.txt"
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "hide-menu", ["hide"], 8.0)
    run_step(args, store, steps, "version", ["version"], 10.0)
    run_step(args, store, steps, "status", ["status"], 20.0)
    run_step(args, store, steps, "selftest-verbose", ["selftest", "verbose"], 25.0)
    run_step(args, store, steps, "wlanbootctl-status", ["run", args.wlanbootctl, "status"], 25.0)
    run_step(
        args,
        store,
        steps,
        "wlan-icnss-surface",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "for p in "
                "/sys/bus/platform/devices/18800000.qcom,icnss "
                "/sys/bus/platform/drivers/icnss "
                "/sys/devices/platform/soc/18800000.qcom,icnss "
                "/sys/devices/platform/soc/18800000.qcom,icnss/net "
                "/sys/devices/platform/soc/18800000.qcom,icnss/ieee80211 "
                "/sys/class/net /sys/class/ieee80211 /sys/bus/mhi/devices "
                "/sys/module/icnss /sys/module/icnss/parameters "
                "/sys/module/wlan /sys/module/wlan/parameters "
                "/sys/kernel/debug/icnss /sys/wifi /dev/wlan; do "
                "printf '== %s ==\\n' \"$p\"; "
                "\"$BB\" ls -laL \"$p\" 2>&1 || true; "
                "done; "
                "for f in "
                "/sys/bus/platform/devices/18800000.qcom,icnss/uevent "
                "/sys/bus/platform/devices/18800000.qcom,icnss/power/runtime_status "
                "/sys/wifi/qcwlanstate "
                "/sys/module/wlan/parameters/con_mode "
                "/sys/module/wlan/parameters/fwpath; do "
                "printf '== %s ==\\n' \"$f\"; "
                "\"$BB\" cat \"$f\" 2>&1 || true; "
                "done"
            ),
        ],
        args.timeout,
    )
    run_step(
        args,
        store,
        steps,
        "dmesg-hdd-pld-focus",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            (
                f"BB={args.busybox}; "
                "\"$BB\" dmesg 2>&1 | "
                "\"$BB\" grep -Ei 'boot_wlan|qcwlanstate|wlan: Loading driver|wlan_hdd_state|driver loaded|driver load failure|hdd_init|pld_|icnss|qmi|wlfw|BDF|wlan0|ieee80211|Modules not initialized|cds_is_driver_loaded|FW is ready' | "
                "\"$BB\" tail -n 260"
            ),
        ],
        args.timeout,
    )
    return steps


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def has(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.IGNORECASE))


def section_text(surface: str, marker: str) -> str:
    token = f"== {marker} =="
    if token not in surface:
        return ""
    return surface.split(token, 1)[1].split("\n== ", 1)[0]


def section_exists(surface: str, marker: str) -> bool:
    section = section_text(surface, marker)
    if not section:
        return False
    return not has(section, r"No such file|can't open|No such device|not found")


def bool_int(value: Any) -> bool:
    try:
        return int(value or 0) > 0
    except (TypeError, ValueError):
        return bool(value)


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    v752 = load_json(args.v752_manifest)
    live = v752.get("live") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    helper = live.get("helper_result") or {}
    v752_dmesg = read_text(args.v752_dmesg)
    v752_boot = read_text(args.v752_boot)
    v703_report = read_text(args.v703_report)
    surface = step_payload(steps, "wlan-icnss-surface")
    dmesg = step_payload(steps, "dmesg-hdd-pld-focus")
    wlanboot = step_payload(steps, "wlanbootctl-status")
    combined_v752 = "\n".join([v752_dmesg, v752_boot, json.dumps(counts, sort_keys=True)])
    return {
        "v752": {
            "manifest": str(repo_path(args.v752_manifest)),
            "decision": v752.get("decision", ""),
            "pass": bool(v752.get("pass")),
            "helper_order": helper.get("order", ""),
            "helper_all_postflight_safe": bool_int(helper.get("all_postflight_safe")),
            "cnss_diag_started": bool(v752.get("cnss_diag_start_executed")),
            "cnss_daemon_started": bool(v752.get("cnss_daemon_start_executed")),
            "boot_wlan_write_executed": bool(v752.get("boot_wlan_write_executed")),
            "service_manager_started": bool(v752.get("service_manager_start_executed")),
            "wifi_hal_started": bool(v752.get("wifi_hal_start_executed")),
            "scan_connect_executed": bool(v752.get("scan_connect_executed")),
            "credential_use_executed": bool(v752.get("credential_use_executed")),
            "dhcp_route_executed": bool(v752.get("dhcp_route_executed")),
            "external_ping_executed": bool(v752.get("external_ping_executed")),
            "wlan_loading": int(counts.get("wlan_loading", 0) or 0),
            "hdd_state_major": int(counts.get("hdd_state_major", 0) or 0),
            "qcwlanstate": int(counts.get("qcwlanstate", 0) or 0),
            "driver_loaded": int(counts.get("wlan_driver_loaded", 0) or 0),
            "driver_failure": int(counts.get("wlan_driver_failure", 0) or 0),
            "icnss_qmi_connected": int(counts.get("icnss_qmi_connected", 0) or 0),
            "fw_ready": int(counts.get("fw_ready", 0) or 0),
            "wlfw": int(counts.get("wlfw", 0) or 0),
            "bdf": int(counts.get("bdf", 0) or 0),
            "wlan0": int(counts.get("wlan0", 0) or 0),
            "wiphy": int(counts.get("wiphy", 0) or 0),
            "explicit_hdd_failure": has(combined_v752, r"hdd_init failed|driver load failure|wlan driver initialization failed|pld_.*fail"),
            "modules_uninitialized_count": count(combined_v752, r"Modules not initialized just return"),
            "qcwlanstate_after_off": bool((live.get("qcwlanstate_after_off"))),
            "wlan0_after": bool(live.get("wlan0_after")),
            "wiphy_after": bool(live.get("wiphy_after")),
            "icnss_net_after": bool(live.get("icnss_net_after")),
            "qrtr_service_69": int((live.get("qrtr_services_after_boot") or {}).get("69", 0) or 0),
        },
        "current": {
            "version_ok": "A90 Linux init" in step_payload(steps, "version"),
            "status_ok": "BOOT OK" in step_payload(steps, "status"),
            "selftest_fail0": has(step_payload(steps, "selftest-verbose"), r"fail=0"),
            "boot_wlan_present": has(wlanboot + "\n" + surface, r"boot_wlan(?:\.exists)?=1|== /sys/kernel/boot_wlan =="),
            "qcwlanstate_off": has(wlanboot + "\n" + surface, r"qcwlanstate(?:\.value)?=OFF|\nOFF\n"),
            "wlan_module_surface": section_exists(surface, "/sys/module/wlan"),
            "wlan_parameter_surface": section_exists(surface, "/sys/module/wlan/parameters"),
            "icnss_parent_surface": section_exists(surface, "/sys/devices/platform/soc/18800000.qcom,icnss"),
            "icnss_net_dir": section_exists(surface, "/sys/devices/platform/soc/18800000.qcom,icnss/net"),
            "icnss_ieee80211_dir": section_exists(surface, "/sys/devices/platform/soc/18800000.qcom,icnss/ieee80211"),
            "debug_icnss_dir": section_exists(surface, "/sys/kernel/debug/icnss"),
            "dev_wlan": section_exists(surface, "/dev/wlan"),
            "wlan0": has(surface, r"\bwlan0\b"),
            "wiphy": has(surface, r"\bphy[0-9]+\b"),
            "mhi_devices": section_exists(surface, "/sys/bus/mhi/devices") and not has(section_text(surface, "/sys/bus/mhi/devices"), r"total 0"),
            "recent_driver_loaded": has(dmesg, r"wlan: driver loaded"),
            "recent_icnss_qmi": has(dmesg, r"icnss_qmi: QMI Server Connected"),
            "recent_fw_ready": has(dmesg, r"WLAN FW is ready|FW is ready"),
            "recent_hdd_failure": has(dmesg, r"hdd_init failed|driver load failure|wlan driver initialization failed|pld_.*fail"),
            "recent_modules_uninitialized_count": count(dmesg, r"Modules not initialized just return"),
        },
        "android_reference": {
            "report": str(repo_path(args.v703_report)),
            "has_icnss_qmi": has(v703_report, r"icnss_qmi: QMI Server Connected|icnss_qmi_connected=1"),
            "has_bdf": has(v703_report, r"BDF file\s*:\s*(regdb|bdwlan)\.bin|bdf_(regdb|bdwlan).*1"),
            "has_fw_ready": has(v703_report, r"WLAN FW is ready|wlan_fw_ready=1"),
            "has_wlan0": has(v703_report, r"\bwlan0\b"),
        },
        "source_model": {
            "hdd_state_before_pld_hdd_register": True,
            "driver_loaded_after_wlan_hdd_register_driver": True,
            "qcwlanstate_on_waits_for_cds_driver_loaded": True,
            "refs": SOURCE_REFS,
        },
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    v752 = analysis["v752"]
    current = analysis["current"]
    android = analysis["android_reference"]
    checks: list[Check] = []
    add_check(
        checks,
        "v752-input",
        "pass" if v752["decision"] == "v752-cnss-then-boot-wlan-hdd-init-still-stalls" and v752["pass"] else "blocked",
        "blocker",
        f"decision={v752['decision']} pass={v752['pass']}",
        [v752["manifest"]],
        "complete V752 before classifying HDD/PLD gap",
    )
    forbidden = any(v752[key] for key in ("service_manager_started", "wifi_hal_started", "scan_connect_executed", "credential_use_executed", "dhcp_route_executed", "external_ping_executed"))
    add_check(
        checks,
        "v752-safety-envelope",
        "pass" if not forbidden else "blocked",
        "blocker",
        f"service_manager={v752['service_manager_started']} wifi_hal={v752['wifi_hal_started']} scan_connect={v752['scan_connect_executed']} credential={v752['credential_use_executed']} dhcp_route={v752['dhcp_route_executed']} external_ping={v752['external_ping_executed']}",
        [v752["manifest"]],
        "discard V752 as prerequisite if it crossed connection-level behavior",
    )
    add_check(
        checks,
        "hdd-entry-confirmed",
        "pass" if v752["boot_wlan_write_executed"] and v752["wlan_loading"] and v752["hdd_state_major"] else "blocked",
        "blocker",
        f"boot_wlan={v752['boot_wlan_write_executed']} loading={v752['wlan_loading']} hdd_state_major={v752['hdd_state_major']} qcwlanstate={v752['qcwlanstate']}",
        [str(repo_path(DEFAULT_V752_DMESG))],
        "do not classify PLD/register-driver gap without HDD entry evidence",
    )
    add_check(
        checks,
        "success-markers-absent",
        "pass" if not any(v752[key] for key in ("driver_loaded", "icnss_qmi_connected", "fw_ready", "wlfw", "bdf", "wlan0", "wiphy", "qrtr_service_69")) else "review",
        "finding",
        f"driver_loaded={v752['driver_loaded']} icnss_qmi={v752['icnss_qmi_connected']} fw_ready={v752['fw_ready']} wlfw={v752['wlfw']} bdf={v752['bdf']} wlan0={v752['wlan0']} wiphy={v752['wiphy']} service69={v752['qrtr_service_69']}",
        [str(repo_path(DEFAULT_V752_DMESG))],
        "if any success marker appears, move to WLFW/netdev readiness classifier",
    )
    add_check(
        checks,
        "explicit-failure-marker-absent",
        "pass" if not v752["explicit_hdd_failure"] else "review",
        "finding",
        f"explicit_hdd_failure={v752['explicit_hdd_failure']} modules_uninitialized={v752['modules_uninitialized_count']}",
        [str(repo_path(DEFAULT_V752_DMESG))],
        "if explicit failure appears, target that exact error before adding instrumentation",
    )
    add_check(
        checks,
        "current-native-still-contained",
        "pass" if current["version_ok"] and current["status_ok"] and current["selftest_fail0"] and not current["wlan0"] and not current["wiphy"] else "blocked",
        "blocker",
        f"version_ok={current['version_ok']} status_ok={current['status_ok']} selftest_fail0={current['selftest_fail0']} wlan0={current['wlan0']} wiphy={current['wiphy']}",
        [],
        "if wlan0/wiphy exists, route to scan-only containment gate",
    )
    add_check(
        checks,
        "surface-points-before-netdev",
        "pass" if current["boot_wlan_present"] and current["wlan_module_surface"] and current["icnss_parent_surface"] and not current["icnss_net_dir"] and not current["icnss_ieee80211_dir"] else "review",
        "finding",
        f"boot_wlan={current['boot_wlan_present']} wlan_module={current['wlan_module_surface']} icnss_parent={current['icnss_parent_surface']} icnss_net={current['icnss_net_dir']} ieee80211={current['icnss_ieee80211_dir']} mhi={current['mhi_devices']} debug_icnss={current['debug_icnss_dir']}",
        [],
        "capture narrower PLD/HDD debug if available before any new trigger",
    )
    add_check(
        checks,
        "android-reference-has-complete-path",
        "pass" if android["has_icnss_qmi"] and android["has_bdf"] and android["has_fw_ready"] and android["has_wlan0"] else "review",
        "finding",
        f"qmi={android['has_icnss_qmi']} bdf={android['has_bdf']} fw_ready={android['has_fw_ready']} wlan0={android['has_wlan0']}",
        [android["report"]],
        "refresh Android reference if these markers are stale",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v753-hdd-pld-prereq-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run read-only preflight/current capture",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v753-hdd-pld-prereq-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear blocker before selecting next Wi-Fi gate",
        )
    v752 = analysis["v752"]
    current = analysis["current"]
    if current["wlan0"] or current["wiphy"] or v752["driver_loaded"] or v752["icnss_qmi_connected"] or v752["fw_ready"]:
        return (
            "v753-driver-advanced-route-to-link-gate",
            True,
            "driver or netdev readiness marker is present",
            "plan scan-only/link-readiness gate before credentials",
        )
    if v752["explicit_hdd_failure"] or current["recent_hdd_failure"]:
        return (
            "v753-hdd-pld-explicit-failure-found",
            True,
            "HDD/PLD/register-driver failure marker is present",
            "target the explicit failure with source-backed instrumentation",
        )
    if v752["wlan_loading"] and v752["hdd_state_major"] and not any(v752[key] for key in ("driver_loaded", "icnss_qmi_connected", "fw_ready", "wlfw", "bdf", "wlan0", "wiphy")):
        return (
            "v753-hdd-pld-register-driver-gap-needs-instrumentation",
            True,
            "V752 proves HDD entry and qcwlanstate creation, but no failure or success marker identifies whether PLD init, hdd_init, or wlan_hdd_register_driver is the stall point",
            "V754 should add bounded, source-backed HDD/PLD/register-driver observability before another trigger attempt",
        )
    return (
        "v753-hdd-pld-prereq-classified-review",
        True,
        "read-only classifier completed but did not match a strict route",
        "inspect manifest before choosing the next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    v752 = analysis.get("v752") or {}
    current = analysis.get("current") or {}
    android = analysis.get("android_reference") or {}
    return "\n".join([
        "# V753 HDD/PLD Prerequisite Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- credential_use_executed: `{manifest['credential_use_executed']}`",
        f"- dhcp_route_executed: `{manifest['dhcp_route_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- plan only",
        "",
        "## V752 Signals",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in v752.items()]) if v752 else "- plan only",
        "",
        "## Current Native Surface",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in current.items()]) if current else "- plan only",
        "",
        "## Android Reference",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in android.items()]) if android else "- plan only",
        "",
        "## Source References",
        "",
        markdown_table(["name", "signal", "url"], [
            [item["name"], item["signal"], item["url"]]
            for item in SOURCE_REFS
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    checks: list[Check] = []
    if args.command != "plan":
        steps = collect_steps(args, store)
        analysis = build_analysis(args, steps)
        checks = build_checks(analysis)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v753",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": args.command != "plan",
        "device_mutations": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "bind_unbind_executed": False,
        "driver_override_executed": False,
        "module_load_unload_executed": False,
        "subsystem_state_writes_executed": False,
        "qcwlanstate_write_executed": False,
        "boot_wlan_write_executed": False,
        "source_refs": SOURCE_REFS,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "steps": steps,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v753-hdd-pld-prereq-classifier.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"dhcp_route_executed: {manifest['dhcp_route_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
