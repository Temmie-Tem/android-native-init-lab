#!/usr/bin/env python3
"""V749 read-only selector for the next non-bind Wi-Fi trigger gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v749-nonbind-trigger-selector")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_WLANBOOTCTL = "/cache/bin/a90_wlanbootctl"
DEFAULT_V748_SOURCE = Path("tmp/wifi/latest-v748-nonbind-powerup-trigger.txt")
DEFAULT_V508_SUMMARY = Path("tmp/wifi/v508-wlan-boot-run-20260521-100318/summary.md")
DEFAULT_V513_REPORT = Path("docs/reports/NATIVE_INIT_V513_DUAL_HAL_DRIVER_STATE_ON_2026-05-21.md")
DEFAULT_V514_REPORT = Path("docs/reports/NATIVE_INIT_V514_ICNSS_MODULE_READINESS_2026-05-21.md")
DEFAULT_V748_REPORT = Path("docs/reports/NATIVE_INIT_V748_NONBIND_POWERUP_TRIGGER_2026-05-24.md")

SOURCE_REFS = [
    {
        "name": "android-cnss2-main-fs-ready",
        "url": "https://android.googlesource.com/kernel/msm/+/53f9955dd5876826f623fb9a1a736cfe36bec176/drivers/net/wireless/cnss2/main.c",
        "signal": "cnss2 exposes an fs_ready store in some Qualcomm kernel branches",
    },
    {
        "name": "android-qcacld-hdd-qcwlanstate",
        "url": "https://android.googlesource.com/kernel/msm/+/android-msm-wahoo-4.4-oreo-m4/drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
        "signal": "qcwlanstate ON path reaches WLAN driver start and waits for module readiness",
    },
]

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


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
    parser.add_argument("--v748-source", type=Path, default=DEFAULT_V748_SOURCE)
    parser.add_argument("--v508-summary", type=Path, default=DEFAULT_V508_SUMMARY)
    parser.add_argument("--v513-report", type=Path, default=DEFAULT_V513_REPORT)
    parser.add_argument("--v514-report", type=Path, default=DEFAULT_V514_REPORT)
    parser.add_argument("--v748-report", type=Path, default=DEFAULT_V748_REPORT)
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def resolve_manifest(source: Path) -> Path:
    path = repo_path(source)
    if path.is_file() and path.name != "manifest.json":
        text = path.read_text(encoding="utf-8").strip()
        if text:
            path = repo_path(Path(text))
    if path.is_dir():
        path = path / "manifest.json"
    return path


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    return json.loads(resolved.read_text(encoding="utf-8")) if resolved.exists() else {}


def clean_text(text: str) -> str:
    return ANSI_RE.sub("", text)


def write_step(store: EvidenceStore, name: str, item: dict[str, Any]) -> None:
    payload = str(item.get("payload") or "")
    store.write_text(f"native/{name}.txt", payload.rstrip() + "\n")


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    commands: list[tuple[str, list[str], float]] = [
        ("hide-menu", ["hide"], 8.0),
        ("version", ["version"], 10.0),
        ("status", ["status"], 20.0),
        ("selftest-verbose", ["selftest", "verbose"], 25.0),
        ("wlanboot-status", ["run", args.wlanbootctl, "status"], 25.0),
        (
            "control-surface-ls",
            [
                "run",
                args.busybox,
                "sh",
                "-c",
                (
                    f"BB={args.busybox}; "
                    "for p in "
                    "/sys/kernel/boot_wlan /sys/kernel/boot_wlan/boot_wlan "
                    "/sys/kernel/shutdown_wlan /sys/kernel/shutdown_wlan/shutdown "
                    "/sys/wifi /sys/wifi/qcwlanstate "
                    "/sys/bus/platform/devices/18800000.qcom,icnss "
                    "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390 "
                    "/sys/bus/platform/drivers/icnss /sys/bus/platform/drivers/cnss2 "
                    "/sys/module/wlan/parameters /sys/module/icnss/parameters "
                    "/sys/kernel/debug/icnss; do "
                    "printf '== %s ==\\n' \"$p\"; "
                    "\"$BB\" ls -laL \"$p\" 2>&1 || true; "
                    "done"
                ),
            ],
            20.0,
        ),
        (
            "control-values",
            [
                "run",
                args.busybox,
                "sh",
                "-c",
                (
                    f"BB={args.busybox}; "
                    "for f in "
                    "/sys/bus/platform/devices/18800000.qcom,icnss/fs_ready "
                    "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/fs_ready "
                    "/sys/wifi/qcwlanstate "
                    "/sys/module/wlan/parameters/fwpath "
                    "/sys/module/wlan/parameters/con_mode "
                    "/sys/module/wlan/parameters/con_mode_ftm "
                    "/sys/module/wlan/parameters/con_mode_epping "
                    "/sys/module/icnss/parameters/quirks "
                    "/sys/module/icnss/parameters/dynamic_feature_mask; do "
                    "printf '== %s ==\\n' \"$f\"; "
                    "\"$BB\" cat \"$f\" 2>&1 || true; "
                    "done"
                ),
            ],
            20.0,
        ),
        (
            "dmesg-focus",
            [
                "run",
                args.busybox,
                "sh",
                "-c",
                (
                    f"BB={args.busybox}; "
                    "\"$BB\" dmesg 2>&1 | "
                    "\"$BB\" grep -Ei 'fs_ready|boot_wlan|qcwlanstate|Wifi Turning On|Modules not initialized|icnss|cnss|qca6390|wlfw|BDF|wlan0|MHI|QMI Server' | "
                    "\"$BB\" tail -n 140"
                ),
            ],
            args.timeout,
        ),
    ]
    steps: list[dict[str, Any]] = []
    for name, command, timeout in commands:
        capture = run_capture(args, name, command, timeout=timeout)
        item = capture_to_manifest(capture)
        payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
        item["payload"] = clean_text(payload)
        item["file"] = f"native/{name}.txt"
        write_step(store, name, item)
        steps.append(item)
    return steps


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "=" not in line or line.startswith("=="):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def has_regex(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE) is not None


def section_text(text: str, path: str) -> str:
    marker = f"== {path} =="
    if marker not in text:
        return ""
    tail = text.split(marker, 1)[1]
    return tail.split("\n== ", 1)[0]


def path_section_exists(text: str, path: str) -> bool:
    section = section_text(text, path)
    if not section:
        return False
    return not has_regex(section, r"No such file|can't open|not found|No such device")


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    v748_manifest_path = resolve_manifest(args.v748_source)
    v748_manifest = load_json(v748_manifest_path)
    v508_text = read_text(args.v508_summary)
    v513_text = read_text(args.v513_report)
    v514_text = read_text(args.v514_report)
    v748_text = read_text(args.v748_report)
    wlanboot = parse_key_values(step_payload(steps, "wlanboot-status"))
    surface = step_payload(steps, "control-surface-ls") + "\n" + step_payload(steps, "control-values")
    dmesg_focus = step_payload(steps, "dmesg-focus")
    return {
        "v748_manifest_path": str(v748_manifest_path),
        "v748_decision": v748_manifest.get("decision"),
        "v748_report_has_nonbind_selection": has_regex(v748_text, r"non-bind ICNSS/QCA WLFW trigger capture"),
        "v508_boot_wlan_write_rc0": has_regex(v508_text, r"boot_write_rc\s*\|\s*0|boot_write_rc.*0"),
        "v508_no_wlan0": has_regex(v508_text, r'"wlan0": false|sys_class_net_wlan0.*0|wlan0.*false'),
        "v513_qcwlanstate_errno22": has_regex(v513_text, r"write_errno=22|errno=22"),
        "v513_modules_not_initialized": has_regex(v513_text, r"Modules not initialized"),
        "v514_module_readiness_gap": has_regex(v514_text, r"v514-wlan-module-init-timeout-classified|ICNSS/WLFW firmware readiness sequence gap"),
        "current": {
            "boot_wlan_exists": wlanboot.get("wlanboot.status.boot_wlan.exists") == "1",
            "qcwlanstate_exists": wlanboot.get("wlanboot.status.qcwlanstate.exists") == "1",
            "qcwlanstate_value": wlanboot.get("wlanboot.status.qcwlanstate.value", ""),
            "wlan_fwpath": wlanboot.get("wlanboot.status.wlan_fwpath.value", ""),
            "dev_wlan_exists": wlanboot.get("wlanboot.status.dev_wlan.exists") == "1",
            "wlan0_exists": wlanboot.get("wlanboot.status.sys_class_net_wlan0.exists") == "1",
            "ieee80211_count": wlanboot.get("wlanboot.status.sys_class_ieee80211.count", ""),
            "proc_devices_qcwlanstate": wlanboot.get("wlanboot.status.proc_devices.qcwlanstate_present", ""),
            "fs_ready_present": any(
                path_section_exists(surface, path)
                for path in (
                    "/sys/bus/platform/devices/18800000.qcom,icnss/fs_ready",
                    "/sys/bus/platform/devices/a0000000.qcom,cnss-qca6390/fs_ready",
                )
            ),
            "cnss2_driver_present": path_section_exists(surface, "/sys/bus/platform/drivers/cnss2"),
            "icnss_driver_present": path_section_exists(surface, "/sys/bus/platform/drivers/icnss"),
            "modules_not_initialized_recent": has_regex(dmesg_focus, r"Modules not initialized"),
        },
    }


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    current = analysis["current"]
    checks: list[Check] = []
    add_check(
        checks,
        "v748-route-input",
        "pass" if analysis.get("v748_decision") == "v748-icnss-qmi-wlfw-nonbind-trigger-selected" else "blocked",
        "blocker",
        f"decision={analysis.get('v748_decision')}",
        [str(analysis.get("v748_manifest_path", ""))],
        "finish V748 before selecting V749 live gate",
    )
    add_check(
        checks,
        "current-wlan-control-surface",
        "pass" if current["boot_wlan_exists"] and current["qcwlanstate_exists"] else "blocked",
        "blocker",
        f"boot_wlan={current['boot_wlan_exists']} qcwlanstate={current['qcwlanstate_exists']} value={current['qcwlanstate_value']}",
        [],
        "do not plan driver boot retry without fixed control nodes",
    )
    add_check(
        checks,
        "fs-ready-current-surface",
        "finding" if not current["fs_ready_present"] else "pass",
        "finding",
        f"fs_ready_present={current['fs_ready_present']} source_ref={SOURCE_REFS[0]['url']}",
        [],
        "if Android exposes fs_ready, capture it read-only before any write",
    )
    add_check(
        checks,
        "standalone-boot-wlan-eliminated",
        "pass" if analysis["v508_boot_wlan_write_rc0"] and analysis["v508_no_wlan0"] else "blocked",
        "blocker",
        f"v508_write_rc0={analysis['v508_boot_wlan_write_rc0']} v508_no_wlan0={analysis['v508_no_wlan0']}",
        [str(repo_path(DEFAULT_V508_SUMMARY))],
        "do not repeat standalone boot_wlan without lower-ready window",
    )
    add_check(
        checks,
        "standalone-qcwlanstate-eliminated",
        "pass" if analysis["v513_qcwlanstate_errno22"] and analysis["v513_modules_not_initialized"] else "blocked",
        "blocker",
        f"errno22={analysis['v513_qcwlanstate_errno22']} modules_not_initialized={analysis['v513_modules_not_initialized']}",
        [str(repo_path(DEFAULT_V513_REPORT))],
        "do not repeat standalone qcwlanstate before lower readiness",
    )
    add_check(
        checks,
        "module-readiness-gap-confirmed",
        "pass" if analysis["v514_module_readiness_gap"] else "blocked",
        "blocker",
        f"v514_gap={analysis['v514_module_readiness_gap']}",
        [str(repo_path(DEFAULT_V514_REPORT))],
        "capture WLFW/BDF/wlan0 before scan/connect",
    )
    add_check(
        checks,
        "connection-still-blocked",
        "pass" if not current["wlan0_exists"] else "blocked",
        "blocker",
        f"wlan0_exists={current['wlan0_exists']} ieee80211_count={current['ieee80211_count']}",
        [],
        "if wlan0 appears, switch to link-readiness and scan/connect gate",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def candidate_matrix(analysis: dict[str, Any], checks: list[Check]) -> dict[str, dict[str, str]]:
    blocked = blocking_checks(checks)
    current = analysis["current"]
    return {
        "fs_ready": {
            "status": "android-handoff-needed" if not current["fs_ready_present"] else "candidate",
            "reason": "official CNSS2 source has fs_ready, but current native ICNSS/QCA sysfs does not expose it" if not current["fs_ready_present"] else "current native exposes fs_ready; write still requires a separate bounded proof",
        },
        "standalone_boot_wlan": {
            "status": "rejected",
            "reason": "V508 write returned rc=0 but did not create wlan0/wiphy; repeat without lower readiness is not useful.",
        },
        "standalone_qcwlanstate": {
            "status": "rejected",
            "reason": "V513 qcwlanstate ON reached the driver but failed with errno 22 and modules-not-initialized.",
        },
        "lower_window_boot_wlan": {
            "status": "selected" if not blocked else "blocked",
            "reason": "V748 selected non-bind trigger work; current boot_wlan/qcwlanstate nodes exist, but prior writes were not combined with the later firmware-mounted holder/lower companion window.",
        },
        "hal_or_scan_connect": {
            "status": "rejected",
            "reason": "No wlan0/wiphy/WLFW/BDF evidence exists; connection-level work remains blocked.",
        },
    }


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v749-nonbind-trigger-selector-plan-ready",
            True,
            "plan-only; no device command executed",
            "run read-only preflight",
        )
    blockers = blocking_checks(checks)
    if blockers:
        return (
            "v749-nonbind-trigger-selector-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh source evidence before selecting a live gate",
        )
    if command == "preflight":
        return (
            "v749-nonbind-trigger-selector-preflight-ready",
            True,
            "read-only current surface and prior evidence are sufficient",
            "run V749 selector",
        )
    return (
        "v749-lower-window-boot-wlan-trigger-selected",
        True,
        "fs_ready is not exposed in current native sysfs, standalone boot_wlan/qcwlanstate were already insufficient, and the remaining non-bind gate is boot_wlan inside the proven lower-ready window",
        "plan V750 bounded lower-window boot_wlan proof; no HAL, scan/connect, DHCP, credentials, routes, or external ping",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    candidates = manifest.get("candidate_matrix") or {}
    return "\n".join([
        "# V749 Non-bind Trigger Selector",
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
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "status", "reason"], [
            [name, value["status"], value["reason"]]
            for name, value in candidates.items()
        ]) if candidates else "- plan only",
        "",
        "## Current Surface",
        "",
        markdown_table(["item", "value"], [
            [key, value]
            for key, value in (manifest.get("analysis", {}).get("current", {}) or {}).items()
        ]) if manifest.get("analysis") else "- plan only",
        "",
        "## Guardrail",
        "",
        "- V749 is read-only; it does not write `boot_wlan`, `qcwlanstate`, `fs_ready`, bind/unbind, or driver state.",
        "- V750, if implemented, must remain below service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    checks: list[Check] = []
    if args.command != "plan":
        steps = collect_steps(args, store)
        analysis = build_analysis(args, steps)
        checks = build_checks(analysis)
    decision, ok, reason, next_step = decide(args.command, checks)
    manifest: dict[str, Any] = {
        "cycle": "v749",
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
        "external_ping_executed": False,
        "source_refs": SOURCE_REFS,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "candidate_matrix": candidate_matrix(analysis, checks) if checks else {},
        "steps": steps,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v749-nonbind-trigger-selector.txt")
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
