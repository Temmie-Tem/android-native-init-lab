#!/usr/bin/env python3
"""V751 read-only classifier for the ICNSS modules-initialized blocker.

This runner consumes V750 evidence, captures the current native ICNSS/WLAN
surface read-only, and classifies whether the remaining blocker is before
QCACLD/HDD module initialization completes. It does not write boot_wlan,
qcwlanstate, bind/unbind, driver_override, module state, daemon state, Wi-Fi
HAL, scan/connect, credentials, DHCP/routes, or external ping.
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
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v751-icnss-module-init-classifier")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_WLANBOOTCTL = "/cache/bin/a90_wlanbootctl"
DEFAULT_V750_MANIFEST = Path("tmp/wifi/v750-lower-window-boot-wlan/manifest.json")
DEFAULT_V750_DMESG = Path("tmp/wifi/v750-lower-window-boot-wlan/native/dmesg-delta.txt")
DEFAULT_V703_REPORT = Path("docs/reports/NATIVE_INIT_V703_ANDROID_NATIVE_BINDING_COMPARE_2026-05-24.md")

SOURCE_REFS = [
    {
        "name": "android-qcacld-wlan-boot-callback",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9406",
        "signal": "static boot_wlan callback calls __hdd_module_init and sets loaded_state only after success",
    },
    {
        "name": "android-qcacld-module-init",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9341",
        "signal": "__hdd_module_init creates qcwlanstate, initializes PLD/HDD, registers the driver, then logs driver loaded",
    },
    {
        "name": "android-qcacld-qcwlanstate-wait",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#9266",
        "signal": "qcwlanstate ON waits for cds_is_driver_loaded before completing",
    },
    {
        "name": "android-qcacld-stop-uninitialized",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c#7947",
        "signal": "Modules not initialized just return is emitted when driver_status is DRIVER_MODULES_UNINITIALIZED",
    },
]


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
    parser.add_argument("--v750-manifest", type=Path, default=DEFAULT_V750_MANIFEST)
    parser.add_argument("--v750-dmesg", type=Path, default=DEFAULT_V750_DMESG)
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


def write_step(store: EvidenceStore, name: str, item: dict[str, Any]) -> None:
    payload = str(item.get("payload") or "")
    store.write_text(f"native/{safe_name(name)}.txt", payload.rstrip() + "\n")


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    commands: list[tuple[str, list[str], float]] = [
        ("hide-menu", ["hide"], 8.0),
        ("version", ["version"], 10.0),
        ("status", ["status"], 20.0),
        ("selftest-verbose", ["selftest", "verbose"], 25.0),
        ("wlanboot-status", ["run", args.wlanbootctl, "status"], 25.0),
        (
            "icnss-wlan-current-surface",
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
                    "/sys/devices/platform/soc/18800000.qcom,icnss/net "
                    "/sys/devices/platform/soc/18800000.qcom,icnss/ieee80211 "
                    "/sys/class/net /sys/class/ieee80211 /sys/bus/mhi/devices "
                    "/sys/module/icnss /sys/module/icnss/parameters "
                    "/sys/module/wlan /sys/module/wlan/parameters "
                    "/sys/kernel/boot_wlan /sys/wifi; do "
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
        ),
        (
            "dmesg-icnss-focus",
            [
                "run",
                args.busybox,
                "sh",
                "-c",
                (
                    f"BB={args.busybox}; "
                    "\"$BB\" dmesg 2>&1 | "
                    "\"$BB\" grep -Ei 'boot_wlan|qcwlanstate|wlan: Loading driver|wlan_hdd_state|driver loaded|driver load failure|hdd_init|pld_|icnss|qmi|wlfw|BDF|wlan0|ieee80211|Modules not initialized' | "
                    "\"$BB\" tail -n 220"
                ),
            ],
            args.timeout,
        ),
    ]
    steps: list[dict[str, Any]] = []
    for name, command, timeout in commands:
        capture = run_capture(args, name, command, timeout=timeout)
        item = capture_to_manifest(capture)
        item["payload"] = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
        item["file"] = f"native/{safe_name(name)}.txt"
        write_step(store, name, item)
        steps.append(item)
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


def section_exists(surface: str, marker: str) -> bool:
    token = f"== {marker} =="
    if token not in surface:
        return False
    section = surface.split(token, 1)[1].split("\n== ", 1)[0]
    return not has(section, r"No such file|can't open|No such device|not found")


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    v750_manifest = load_json(args.v750_manifest)
    v750_live = v750_manifest.get("live") or {}
    v750_dmesg = read_text(args.v750_dmesg)
    v703_report = read_text(args.v703_report)
    surface = step_payload(steps, "icnss-wlan-current-surface")
    dmesg = step_payload(steps, "dmesg-icnss-focus")
    wlanboot = step_payload(steps, "wlanboot-status")
    return {
        "v750": {
            "manifest": str(repo_path(args.v750_manifest)),
            "decision": v750_manifest.get("decision", ""),
            "pass": v750_manifest.get("pass", False),
            "boot_wlan_ok": bool(v750_live.get("boot_wlan_ok")),
            "wlan0_after": bool(v750_live.get("wlan0_after")),
            "wiphy_after": bool(v750_live.get("wiphy_after")),
            "qrtr_services_after_boot": v750_live.get("qrtr_services_after_boot", {}),
            "dmesg_wlan_loading": has(v750_dmesg, r"wlan: Loading driver"),
            "dmesg_hdd_state_major": has(v750_dmesg, r"wlan_hdd_state wlan major"),
            "dmesg_driver_loaded": has(v750_dmesg, r"wlan: driver loaded"),
            "dmesg_modules_not_initialized_count": count(v750_dmesg, r"Modules not initialized just return"),
            "dmesg_qmi_connected": has(v750_dmesg, r"icnss_qmi: QMI Server Connected"),
            "dmesg_wlan_fw_ready": has(v750_dmesg, r"WLAN FW is ready"),
        },
        "current": {
            "icnss_parent_bound": section_exists(surface, "/sys/bus/platform/devices/18800000.qcom,icnss") and has(surface, r"DRIVER=icnss|18800000\.qcom,icnss"),
            "icnss_net_dir": section_exists(surface, "/sys/devices/platform/soc/18800000.qcom,icnss/net"),
            "icnss_ieee80211_dir": section_exists(surface, "/sys/devices/platform/soc/18800000.qcom,icnss/ieee80211"),
            "class_wlan0": has(surface, r"\bwlan0\b"),
            "class_wiphy": has(surface, r"\bphy[0-9]+\b"),
            "mhi_devices": section_exists(surface, "/sys/bus/mhi/devices") and not has(surface, r"total 0"),
            "qcwlanstate_off": has(wlanboot + "\n" + surface, r"qcwlanstate(?:\.value)?=OFF|\nOFF\n"),
            "boot_wlan_present": has(wlanboot + "\n" + surface, r"boot_wlan(?:\.exists)?=1|boot_wlan"),
            "dmesg_modules_not_initialized_count": count(dmesg, r"Modules not initialized just return"),
            "dmesg_driver_loaded": has(dmesg, r"wlan: driver loaded"),
        },
        "android_reference": {
            "report": str(repo_path(args.v703_report)),
            "has_icnss_qmi": has(v703_report, r"icnss_qmi: QMI Server Connected|icnss_qmi_connected=1"),
            "has_bdf": has(v703_report, r"BDF file\s*:\s*(regdb|bdwlan)\.bin|bdf_(regdb|bdwlan).*1"),
            "has_wlan_fw_ready": has(v703_report, r"WLAN FW is ready|wlan_fw_ready=1"),
            "has_wlan0": has(v703_report, r"\bwlan0\b"),
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


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    v750 = analysis["v750"]
    current = analysis["current"]
    android = analysis["android_reference"]
    checks: list[Check] = []
    add_check(
        checks,
        "v750-input",
        "pass" if v750["decision"] == "v750-lower-window-boot-wlan-control-surface-only" and v750["pass"] else "blocked",
        "blocker",
        f"decision={v750['decision']} pass={v750['pass']}",
        [v750["manifest"]],
        "finish V750 before V751 classification",
    )
    add_check(
        checks,
        "boot-wlan-entered-hdd-init",
        "pass" if v750["boot_wlan_ok"] and v750["dmesg_wlan_loading"] and v750["dmesg_hdd_state_major"] else "blocked",
        "blocker",
        f"boot_ok={v750['boot_wlan_ok']} loading={v750['dmesg_wlan_loading']} hdd_state_major={v750['dmesg_hdd_state_major']}",
        [str(repo_path(DEFAULT_V750_DMESG))],
        "do not classify module-init gap without proof boot_wlan entered HDD init",
    )
    add_check(
        checks,
        "driver-loaded-not-reached",
        "pass" if not v750["dmesg_driver_loaded"] and not v750["dmesg_qmi_connected"] and not v750["dmesg_wlan_fw_ready"] else "review",
        "finding",
        f"driver_loaded={v750['dmesg_driver_loaded']} qmi_connected={v750['dmesg_qmi_connected']} fw_ready={v750['dmesg_wlan_fw_ready']} modules_not_initialized={v750['dmesg_modules_not_initialized_count']}",
        [str(repo_path(DEFAULT_V750_DMESG))],
        "if driver loaded appears, switch to WLFW/BDF classifier",
    )
    add_check(
        checks,
        "current-link-still-absent",
        "pass" if not current["class_wlan0"] and not current["class_wiphy"] else "blocked",
        "blocker",
        f"wlan0={current['class_wlan0']} wiphy={current['class_wiphy']} icnss_net_dir={current['icnss_net_dir']} ieee80211_dir={current['icnss_ieee80211_dir']}",
        [],
        "if wlan0/wiphy exists, move to scan-only gate",
    )
    add_check(
        checks,
        "icnss-parent-bound-no-netdev",
        "pass" if current["icnss_parent_bound"] and not current["icnss_net_dir"] and not current["icnss_ieee80211_dir"] else "review",
        "finding",
        f"bound={current['icnss_parent_bound']} net_dir={current['icnss_net_dir']} ieee80211_dir={current['icnss_ieee80211_dir']} mhi_devices={current['mhi_devices']}",
        [],
        "target initialization below ICNSS parent bind, not bind/unbind",
    )
    add_check(
        checks,
        "android-reference-continues",
        "pass" if android["has_icnss_qmi"] and android["has_bdf"] and android["has_wlan_fw_ready"] and android["has_wlan0"] else "review",
        "finding",
        f"qmi={android['has_icnss_qmi']} bdf={android['has_bdf']} fw_ready={android['has_wlan_fw_ready']} wlan0={android['has_wlan0']}",
        [android["report"]],
        "refresh Android reference if these markers are stale",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v751-icnss-module-init-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run read-only current capture",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v751-icnss-module-init-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear blocker before selecting next live gate",
        )
    v750 = analysis["v750"]
    current = analysis["current"]
    if (
        v750["dmesg_wlan_loading"]
        and v750["dmesg_hdd_state_major"]
        and not v750["dmesg_driver_loaded"]
        and v750["dmesg_modules_not_initialized_count"] > 0
        and current["icnss_parent_bound"]
        and not current["class_wlan0"]
    ):
        return (
            "v751-boot-wlan-hdd-init-stalls-before-driver-loaded",
            True,
            "boot_wlan enters QCACLD/HDD init and creates qcwlanstate, but driver-loaded/QMI/FW-ready/netdev markers never appear; current ICNSS parent is bound with no netdev/wiphy",
            "plan V752 around bounded CNSS-daemon plus boot_wlan ordering or deeper HDD/PLD init instrumentation; still no HAL/connect",
        )
    return (
        "v751-icnss-module-init-classified-review",
        True,
        "read-only classification completed but did not match the strict pre-driver-loaded pattern",
        "inspect manifest before choosing the next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    v750 = analysis.get("v750") or {}
    current = analysis.get("current") or {}
    android = analysis.get("android_reference") or {}
    return "\n".join([
        "# V751 ICNSS Module-init Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
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
        "## V750 Signals",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in v750.items()]) if v750 else "- plan only",
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
            for item in manifest.get("source_refs", [])
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
        "cycle": "v751",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": args.command != "plan",
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "bind_unbind_executed": False,
        "driver_override_executed": False,
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
    latest = repo_path("tmp/wifi/latest-v751-icnss-module-init-classifier.txt")
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(str(store.run_dir.relative_to(repo_path("."))) + "\n", encoding="utf-8")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
