#!/usr/bin/env python3
"""V726 CNSS2/PCIe modem and wlan module prerequisite classifier.

This classifier reflects the SM8250 CNSS2 path:

    cnss2 probe -> QCA6390 PCIe/MHI power-up -> WLFW service 69

It checks whether the current native boot has the prerequisites for that path:
modem MPSS online state, wlan module load state, CNSS2/MHI/QCA6390 dmesg
evidence, and wlanmdsp firmware visibility. It does not open esoc0, open
subsys_modem, write subsystem state, start CNSS daemon, start service-manager,
start Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, or
ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v726-cnss2-pcie-prereq")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"

FIRMWARE_PATHS = (
    "/vendor/firmware_mnt/image/wlanmdsp.mbn",
    "/vendor/firmware_mnt/image/wlanmdsp.mdt",
    "/vendor/firmware_mnt/image/wlanmdsp.b00",
    "/vendor/firmware-modem/image/wlanmdsp.mbn",
    "/vendor/firmware-modem/image/wlanmdsp.mdt",
    "/vendor/firmware-modem/image/wlanmdsp.b00",
    "/vendor/firmware/image/wlanmdsp.mbn",
    "/mnt/system/vendor/firmware_mnt/image/wlanmdsp.mbn",
    "/mnt/system/vendor/firmware/wlanmdsp.mbn",
    "/mnt/system/vendor/firmware/wlanmdsp.mdt",
)
MODEM_FIRMWARE_PATHS = (
    "/vendor/firmware_mnt/image/modem.b00",
    "/vendor/firmware_mnt/image/modem.mdt",
    "/vendor/firmware-modem/image/modem.b00",
    "/vendor/firmware-modem/image/modem.mdt",
)

DMESG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cnss_probe", re.compile(r"cnss.*probe|icnss: Platform driver probed successfully|Platform driver probed successfully", re.I)),
    ("cnss2", re.compile(r"\bcnss2\b|cnss-qca|qcom,cnss|18800000\.qcom,icnss|icnss", re.I)),
    ("pci", re.compile(r"\bpci(?:e)?\b|pcie", re.I)),
    ("mhi", re.compile(r"\bmhi\b|mhi_sync_power_up|mhi power", re.I)),
    ("qca6390", re.compile(r"qca6390|wcn3990|wcnss", re.I)),
    ("wlan_module", re.compile(r"\bwlan\b.*(?:module|loading|init)|wlan: loading", re.I)),
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|\bwlan_pd\b", re.I)),
    ("wlfw", re.compile(r"\bwlfw\b|service 69|QMI Server Connected", re.I)),
    ("bdf", re.compile(r"\bBDF\b|regdb\.bin|bdwlan\.bin", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put", re.I)),
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    steps.append(item)
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def step_ok(steps: list[dict[str, Any]], name: str) -> bool:
    for step in steps:
        if step.get("name") == name:
            return bool(step.get("ok")) and step.get("status") == "ok"
    return False


def path_exists_payload(text: str) -> bool:
    lowered = text.lower()
    return bool(text.strip()) and "no such file" not in lowered and "not found" not in lowered and "cannot stat" not in lowered


def parse_dmesg(text: str) -> dict[str, Any]:
    events: dict[str, list[str]] = {name: [] for name, _ in DMESG_PATTERNS}
    focus: list[str] = []
    for raw_line in text.splitlines():
        line = ANSI_RE.sub("", raw_line).strip()
        if not line:
            continue
        matched = False
        for name, pattern in DMESG_PATTERNS:
            if pattern.search(line):
                events[name].append(line[:360])
                matched = True
        if matched:
            focus.append(line[:360])
    return {
        "counts": {name: len(lines) for name, lines in events.items()},
        "first_lines": {name: lines[0] for name, lines in events.items() if lines},
        "focus_tail": focus[-200:],
    }


def module_loaded(proc_modules: str, name: str) -> bool:
    return any(line.split()[:1] == [name] for line in proc_modules.splitlines())


def collect_live(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    mount_steps: list[dict[str, Any]] = []
    mount_preflight = mountv.capture_preflight(args, store, mount_steps)
    steps.extend(mount_steps)

    run_step(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], 30.0)
    run_step(args, store, steps, "proc-modules", ["cat", "/proc/modules"], 20.0)
    run_step(args, store, steps, "cnss2-driver-ls", ["run", args.toybox, "ls", "-l", "/sys/bus/platform/drivers/cnss2"], 10.0)
    run_step(args, store, steps, "icnss-driver-ls", ["run", args.toybox, "ls", "-l", "/sys/bus/platform/drivers/icnss"], 10.0)
    run_step(args, store, steps, "cnss-device-ls", ["run", args.toybox, "ls", "-l", "/sys/devices/platform/soc/18800000.qcom,icnss"], 10.0)
    run_step(args, store, steps, "wlan-module-ls", ["run", args.toybox, "ls", "-l", "/sys/module/wlan"], 10.0)
    run_step(args, store, steps, "mss-name", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/name"], 10.0)
    run_step(args, store, steps, "mss-state", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
    run_step(args, store, steps, "mss-crash-count", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/crash_count"], 10.0)
    run_step(args, store, steps, "mdm3-name", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/name"], 10.0)
    run_step(args, store, steps, "mdm3-state", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"], 10.0)
    run_step(args, store, steps, "mdm3-crash-count", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/crash_count"], 10.0)
    run_step(args, store, steps, "system-find-wlanmdsp", ["run", args.toybox, "find", "/mnt/system", "-maxdepth", "8", "-name", "wlanmdsp*"], 25.0)
    run_step(args, store, steps, "dmesg", ["run", args.toybox, "dmesg"], 60.0)

    base_dir = "/tmp/a90-v726-cnss2-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    cleanup: list[dict[str, Any]] = []
    try:
        for name, command, timeout in mountv.build_mount_commands(mount_preflight, base_dir):
            run_step(args, store, steps, f"firmware-mount-{name}", command, timeout)
        run_step(args, store, steps, "firmware-mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0)
        for path in FIRMWARE_PATHS:
            run_step(args, store, steps, f"stat-{safe_name(path)}", ["stat", path], 10.0)
        for path in MODEM_FIRMWARE_PATHS:
            run_step(args, store, steps, f"stat-{safe_name(path)}", ["stat", path], 10.0)
    finally:
        for name, command, timeout in mountv.build_cleanup_commands(base_dir, mount_preflight.get("vendor_symlink_target")):
            cleanup.append(run_step(args, store, steps, f"firmware-cleanup-{name}", command, timeout))

    dmesg = parse_dmesg(step_payload(steps, "dmesg"))
    store.write_text("native/dmesg-focus.txt", "\n".join(dmesg["focus_tail"]) + ("\n" if dmesg["focus_tail"] else ""))
    cleanup_ok = all(item.get("ok") or item.get("rc") in {1, None} for item in cleanup)
    live = {
        "dmesg": dmesg,
        "wlan_module_loaded": module_loaded(step_payload(steps, "proc-modules"), "wlan"),
        "proc_modules_has_wlan": module_loaded(step_payload(steps, "proc-modules"), "wlan"),
        "sys_module_wlan_exists": step_ok(steps, "wlan-module-ls"),
        "cnss2_driver_exists": step_ok(steps, "cnss2-driver-ls") or step_ok(steps, "icnss-driver-ls"),
        "cnss_device_exists": step_ok(steps, "cnss-device-ls"),
        "mss_name": step_payload(steps, "mss-name").strip(),
        "mss_state": step_payload(steps, "mss-state").strip(),
        "mss_crash_count": step_payload(steps, "mss-crash-count").strip(),
        "mdm3_name": step_payload(steps, "mdm3-name").strip(),
        "mdm3_state": step_payload(steps, "mdm3-state").strip(),
        "mdm3_crash_count": step_payload(steps, "mdm3-crash-count").strip(),
        "wlanmdsp_find_hits": [line.strip() for line in step_payload(steps, "system-find-wlanmdsp").splitlines() if "wlanmdsp" in line],
        "wlanmdsp_stat_hits": [
            path for path in FIRMWARE_PATHS
            if path_exists_payload(step_payload(steps, f"stat-{safe_name(path)}"))
        ],
        "modem_blob_stat_hits": [
            path for path in MODEM_FIRMWARE_PATHS
            if path_exists_payload(step_payload(steps, f"stat-{safe_name(path)}"))
        ],
        "firmware_mount_hits": {
            target: target in mountv.parse_mounts(step_payload(steps, "firmware-mounted-proc-mounts"))
            for target in mountv.PARTITION_TARGETS.values()
        },
        "firmware_cleanup_ok": cleanup_ok,
        "read_only_mounts_executed": True,
    }
    return steps, mount_preflight, live


def build_checks(args: argparse.Namespace, steps: list[dict[str, Any]], mount_preflight: dict[str, Any], live: dict[str, Any]) -> list[dict[str, Any]]:
    if not live:
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command executed",
            "next_step": "run V726 classifier",
        }]
    counts = (live.get("dmesg") or {}).get("counts") or {}
    return [
        {
            "name": "native-v724-clean",
            "status": "pass" if args.expect_version in step_payload(steps, "version") and "fail=0" in step_payload(steps, "status") and "fail=0" in step_payload(steps, "selftest") else "blocked",
            "detail": {"expect_version": args.expect_version},
            "next_step": "restore V724 native baseline before Wi-Fi prerequisite analysis",
        },
        {
            "name": "firmware-mount-cleanup",
            "status": "pass" if live.get("firmware_cleanup_ok") else "blocked",
            "detail": {"mount_hits": live.get("firmware_mount_hits")},
            "next_step": "cleanup firmware mounts before any further live work",
        },
        {
            "name": "cnss2-platform-surface",
            "status": "pass" if live.get("cnss2_driver_exists") or live.get("cnss_device_exists") or counts.get("cnss_probe", 0) > 0 else "review",
            "detail": {"driver": live.get("cnss2_driver_exists"), "device": live.get("cnss_device_exists"), "dmesg_cnss_probe": counts.get("cnss_probe", 0)},
            "next_step": "verify platform driver binding if this regresses",
        },
        {
            "name": "wlan-module-loaded",
            "status": "pass" if live.get("wlan_module_loaded") else "finding",
            "detail": {
                "proc_modules_has_wlan": live.get("proc_modules_has_wlan"),
                "sys_module_wlan_exists": live.get("sys_module_wlan_exists"),
                "interpretation": "sys_module_wlan alone is not proof that wlan.ko is loaded via /proc/modules",
            },
            "next_step": "distinguish built-in/static sys_module surface from loadable wlan.ko before expecting MHI/WLFW",
        },
        {
            "name": "modem-mpss-online",
            "status": "pass" if live.get("mss_state") == "ONLINE" and live.get("mdm3_state") == "ONLINE" else "finding",
            "detail": {"mss_state": live.get("mss_state"), "mdm3_state": live.get("mdm3_state"), "mss_crash_count": live.get("mss_crash_count"), "mdm3_crash_count": live.get("mdm3_crash_count")},
            "next_step": "modem ONLINE is prerequisite for wlan_pd/wlanmdsp/WLFW path",
        },
        {
            "name": "wlanmdsp-firmware-visible",
            "status": "pass" if live.get("wlanmdsp_find_hits") or live.get("wlanmdsp_stat_hits") else "finding",
            "detail": {"find_hits": live.get("wlanmdsp_find_hits"), "stat_hits": live.get("wlanmdsp_stat_hits")},
            "next_step": "if absent, map firmware partition paths before modem ONLINE trigger",
        },
        {
            "name": "cnss2-mhi-wlfw-progression",
            "status": "pass" if counts.get("mhi", 0) > 0 and counts.get("wlfw", 0) > 0 else "finding",
            "detail": {"mhi": counts.get("mhi", 0), "qca6390": counts.get("qca6390", 0), "wlfw": counts.get("wlfw", 0), "wlan0": counts.get("wlan0", 0)},
            "next_step": "do not start HAL/scan/connect until WLFW/BDF/wlan0 appears",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], live: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v726-cnss2-pcie-prereq-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V726 read-only prerequisite classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v726-cnss2-pcie-prereq-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "resolve cleanup/baseline blockers before further live work",
        )
    finding_names = {check["name"] for check in checks if check["status"] == "finding"}
    if "modem-mpss-online" in finding_names and "wlan-module-loaded" in finding_names:
        return (
            "v726-cnss2-pcie-modem-and-wlan-module-prereq-gap-classified",
            True,
            "native lacks ONLINE modem/MDM3 and loaded wlan module evidence, so WLFW service 69 and wlan0 are not expected yet",
            "plan V727 around safe modem ONLINE trigger and wlan module/load-state proof before CNSS daemon or HAL",
        )
    if "modem-mpss-online" in finding_names:
        return (
            "v726-cnss2-pcie-modem-online-prereq-gap-classified",
            True,
            "native modem/MDM3 is not ONLINE, so wlan_pd/wlanmdsp/WLFW cannot progress",
            "plan V727 safe modem ONLINE trigger proof; no CNSS daemon or HAL",
        )
    if "wlan-module-loaded" in finding_names:
        return (
            "v726-cnss2-pcie-wlan-module-prereq-gap-classified",
            True,
            "native lacks loaded wlan module evidence, so cnss_pci_dev_powerup/MHI completion may be absent",
            "plan V727 wlan module/load-state proof; no scan/connect",
        )
    return (
        "v726-cnss2-pcie-prereq-review",
        True,
        "prerequisite evidence does not match the expected modem/wlan gap",
        "inspect V726 manifest before selecting next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    counts = ((live.get("dmesg") or {}).get("counts") or {})
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    state_rows = [
        ["mss_state", live.get("mss_state", "")],
        ["mdm3_state", live.get("mdm3_state", "")],
        ["wlan_module_loaded", live.get("wlan_module_loaded", "")],
        ["cnss2_driver_exists", live.get("cnss2_driver_exists", "")],
        ["cnss_device_exists", live.get("cnss_device_exists", "")],
        ["wlanmdsp_hits", len(live.get("wlanmdsp_find_hits") or []) + len(live.get("wlanmdsp_stat_hits") or [])],
        ["modem_blob_hits", len(live.get("modem_blob_stat_hits") or [])],
    ]
    count_rows = [[name, str(counts.get(name, 0))] for name, _ in DMESG_PATTERNS]
    return "\n".join([
        "# V726 CNSS2/PCIe Prerequisite Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- read_only_mounts_executed: `{manifest['read_only_mounts_executed']}`",
        f"- subsystem_writes_executed: `{manifest['subsystem_writes_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], check_rows),
        "",
        "## State Summary",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## Dmesg Counts",
        "",
        markdown_table(["marker", "count"], count_rows),
        "",
        "## Firmware Hits",
        "",
        "- wlanmdsp:",
        "\n".join(f"  - `{path}`" for path in (live.get("wlanmdsp_find_hits") or []) + (live.get("wlanmdsp_stat_hits") or [])) or "  - none",
        "- modem blobs:",
        "\n".join(f"  - `{path}`" for path in (live.get("modem_blob_stat_hits") or [])) or "  - none",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    mount_preflight: dict[str, Any] = {}
    live: dict[str, Any] = {}
    if args.command == "run":
        steps, mount_preflight, live = collect_live(args, store)
    checks = build_checks(args, steps, mount_preflight, live)
    decision, pass_ok, reason, next_step = decide(args.command, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v726",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": checks,
        "mount_preflight": mount_preflight,
        "live": live,
        "device_commands_executed": args.command == "run",
        "device_mutations": False,
        "read_only_mounts_executed": bool(live.get("read_only_mounts_executed")),
        "subsystem_writes_executed": False,
        "subsys_modem_holder_executed": False,
        "esoc0_open_executed": False,
        "cnss_daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"read_only_mounts_executed: {manifest['read_only_mounts_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
