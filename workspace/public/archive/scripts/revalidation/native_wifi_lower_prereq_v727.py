#!/usr/bin/env python3
"""V727 lower prerequisite classifier for native Wi-Fi bring-up.

This classifier stays below CNSS daemon, service-manager, Wi-Fi HAL, scan,
connect, DHCP, routes, and external ping.  It narrows the V726 lower blocker by
checking two specific prerequisites:

1. whether native's current `/vendor` view exposes the real Wi-Fi firmware, or
   whether the actual vendor partition is only visible through an isolated
   read-only `sda29` mount;
2. whether `/sys/module/wlan` with no `/proc/modules` entry looks like a static
   built-in parameter surface rather than a loadable `wlan.ko` path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v727-lower-prereq")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
PROBE_PREFIX = "/tmp/a90-v727-"

CURRENT_VENDOR_FIRMWARE = (
    "/vendor/firmware/wlanmdsp.mbn",
    "/vendor/firmware/wlan/qca_cld/bdwlan.bin",
    "/vendor/firmware/wlan/qca_cld/regdb.bin",
    "/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
)
VENDOR_RELATIVE_FIRMWARE = (
    "firmware/wlanmdsp.mbn",
    "firmware/wlan/qca_cld/bdwlan.bin",
    "firmware/wlan/qca_cld/regdb.bin",
    "firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
)
WLAN_PARAM_PATHS = (
    "/sys/module/wlan/parameters/fwpath",
    "/sys/module/wlan/parameters/con_mode",
    "/sys/module/wlan/parameters/country_code",
)
DMESG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cnss", re.compile(r"\bcnss\b|icnss|18800000\.qcom,icnss", re.I)),
    ("mhi", re.compile(r"\bmhi\b|mhi_sync_power_up", re.I)),
    ("qca6390", re.compile(r"qca6390|wcn3990", re.I)),
    ("wlfw", re.compile(r"\bwlfw\b|service 69|QMI Server Connected", re.I)),
    ("bdf", re.compile(r"\bBDF\b|bdwlan\.bin|regdb\.bin", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("modem_readiness", re.compile(r"qrtr: Modem QMI Readiness|sysmon-qmi", re.I)),
)
FORBIDDEN_TERMS = (
    "qcwlanstate",
    "svc wifi",
    "cmd wifi",
    "iw ",
    "wpa_supplicant",
    "hostapd",
    "dhcp",
    "ping",
    "rfkill",
    "insmod",
    "rmmod",
    "modprobe",
    "ip link",
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@dataclass(frozen=True)
class ProbePaths:
    run_id: str
    base: str
    node: str
    mountpoint: str


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


def make_probe_paths() -> ProbePaths:
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = f"{PROBE_PREFIX}{run_id}"
    return ProbePaths(run_id=run_id, base=base, node=f"{base}/sda29", mountpoint=f"{base}/vendor")


def is_under_probe(path: str, probe: ProbePaths) -> bool:
    return path == probe.base or path.startswith(probe.base + "/")


def validate_device_command(command: list[str], probe: ProbePaths | None = None) -> None:
    joined = " ".join(command)
    lowered = joined.lower()
    for term in FORBIDDEN_TERMS:
        if term in lowered:
            raise RuntimeError(f"forbidden Wi-Fi bring-up term in V727 command: {joined}")
    if command[0] in {"version", "status", "selftest", "cat", "stat", "ls", "umount"}:
        return
    if command[0] == "mkdir" and probe and len(command) == 2 and is_under_probe(command[1], probe):
        return
    if command[0] == "mknodb" and probe and len(command) == 4 and command[1] == probe.node:
        return
    if command[:2] == ["run", DEFAULT_TOYBOX]:
        subcmd = command[2] if len(command) > 2 else ""
        if subcmd in {"ls", "find", "dmesg", "rm", "rmdir"}:
            return
        if subcmd == "mount" and probe:
            expected_prefix = ["run", DEFAULT_TOYBOX, "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint]
            if command == expected_prefix:
                return
        raise RuntimeError(f"unexpected V727 toybox command: {joined}")
    raise RuntimeError(f"unexpected V727 command: {joined}")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             probe: ProbePaths | None = None) -> dict[str, Any]:
    validate_device_command(command, probe)
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
    return bool(text.strip()) and all(token not in lowered for token in ("no such file", "not found", "cannot stat"))


def parse_dev(text: str) -> tuple[str, str] | None:
    match = re.search(r"(?m)^(\d+):(\d+)\s*$", text.strip())
    if not match:
        return None
    return match.group(1), match.group(2)


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
        "focus_tail": focus[-160:],
    }


def module_loaded(proc_modules: str, name: str) -> bool:
    return any(line.split()[:1] == [name] for line in proc_modules.splitlines())


def filtered_hits(text: str, tokens: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if line and any(token in lowered for token in tokens):
            hits.append(line)
    return hits[:120]


def collect_live(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "version", ["version"], 15.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "selftest", ["selftest"], 25.0)
    run_step(args, store, steps, "vendor-links", ["run", args.toybox, "ls", "-ld", "/vendor", "/mnt/system/vendor", "/system/vendor"], 15.0)
    run_step(args, store, steps, "firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0)
    for path in CURRENT_VENDOR_FIRMWARE:
        run_step(args, store, steps, f"current-stat-{safe_name(path)}", ["stat", path], 10.0)
    run_step(args, store, steps, "proc-modules", ["cat", "/proc/modules"], 20.0)
    run_step(args, store, steps, "sys-module-wlan-ls", ["run", args.toybox, "ls", "-l", "/sys/module/wlan"], 10.0)
    run_step(args, store, steps, "sys-module-wlan-find", ["run", args.toybox, "find", "/sys/module/wlan", "-maxdepth", "2"], 15.0)
    run_step(args, store, steps, "sys-module-wlan-initstate", ["cat", "/sys/module/wlan/initstate"], 10.0)
    run_step(args, store, steps, "sys-module-wlan-refcnt", ["cat", "/sys/module/wlan/refcnt"], 10.0)
    for path in WLAN_PARAM_PATHS:
        run_step(args, store, steps, f"param-{safe_name(path)}", ["cat", path], 10.0)
    run_step(args, store, steps, "mss-state", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
    run_step(args, store, steps, "mdm3-state", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"], 10.0)
    run_step(args, store, steps, "dmesg", ["run", args.toybox, "dmesg"], 60.0)
    run_step(args, store, steps, "sda29-dev", ["cat", "/sys/class/block/sda29/dev"], 10.0)
    run_step(args, store, steps, "sda29-uevent", ["cat", "/sys/class/block/sda29/uevent"], 10.0)

    probe = make_probe_paths()
    dev = parse_dev(step_payload(steps, "sda29-dev"))
    mount_ok = False
    if dev:
        major, minor = dev
        run_step(args, store, steps, "probe-mkdir-base", ["mkdir", probe.base], 10.0, probe)
        run_step(args, store, steps, "probe-mkdir-vendor", ["mkdir", probe.mountpoint], 10.0, probe)
        run_step(args, store, steps, "probe-mknodb-sda29", ["mknodb", probe.node, major, minor], 10.0, probe)
        run_step(args, store, steps, "probe-mount-vendor-ro-noload", ["run", args.toybox, "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint], 45.0, probe)
        mount_ok = step_ok(steps, "probe-mount-vendor-ro-noload")
        run_step(args, store, steps, "probe-mounted-proc-mounts", ["cat", "/proc/mounts"], 10.0)
        for rel_path in VENDOR_RELATIVE_FIRMWARE:
            run_step(args, store, steps, f"probe-stat-{safe_name(rel_path)}", ["stat", f"{probe.mountpoint}/{rel_path}"], 10.0)
        run_step(args, store, steps, "probe-find-firmware", ["run", args.toybox, "find", f"{probe.mountpoint}/firmware", "-maxdepth", "4"], 30.0, probe)
        run_step(args, store, steps, "probe-find-lib-modules", ["run", args.toybox, "find", f"{probe.mountpoint}/lib/modules", "-maxdepth", "4"], 30.0, probe)
        if mount_ok:
            run_step(args, store, steps, "cleanup-umount-vendor", ["umount", probe.mountpoint], 20.0, probe)
        run_step(args, store, steps, "cleanup-post-proc-mounts", ["cat", "/proc/mounts"], 10.0)
        run_step(args, store, steps, "cleanup-rm-node", ["run", args.toybox, "rm", "-f", probe.node], 10.0, probe)
        run_step(args, store, steps, "cleanup-rmdir-vendor", ["run", args.toybox, "rmdir", probe.mountpoint], 10.0, probe)
        run_step(args, store, steps, "cleanup-rmdir-base", ["run", args.toybox, "rmdir", probe.base], 10.0, probe)

    dmesg = parse_dmesg(step_payload(steps, "dmesg"))
    store.write_text("native/dmesg-focus.txt", "\n".join(dmesg["focus_tail"]) + ("\n" if dmesg["focus_tail"] else ""))
    proc_modules = step_payload(steps, "proc-modules")
    sys_module_find = step_payload(steps, "sys-module-wlan-find")
    current_firmware_hits = [
        path for path in CURRENT_VENDOR_FIRMWARE
        if path_exists_payload(step_payload(steps, f"current-stat-{safe_name(path)}"))
    ]
    isolated_firmware_hits = [
        f"/vendor/{rel_path}" for rel_path in VENDOR_RELATIVE_FIRMWARE
        if path_exists_payload(step_payload(steps, f"probe-stat-{safe_name(rel_path)}"))
    ]
    lib_module_hits = filtered_hits(step_payload(steps, "probe-find-lib-modules"), ("wlan", "qca", "cld", "cnss", "mhi"))
    post_mounts = step_payload(steps, "cleanup-post-proc-mounts")
    cleanup_ok = (not mount_ok or step_ok(steps, "cleanup-umount-vendor")) and probe.mountpoint not in post_mounts and step_ok(steps, "cleanup-rmdir-base")
    live = {
        "probe": probe.__dict__,
        "sda29_dev": dev,
        "current_vendor_firmware_hits": current_firmware_hits,
        "isolated_vendor_firmware_hits": isolated_firmware_hits,
        "isolated_firmware_tree_hits": filtered_hits(step_payload(steps, "probe-find-firmware"), ("wlanmdsp", "bdwlan", "regdb", "wcnss")),
        "vendor_lib_module_hits": lib_module_hits,
        "firmware_class_path": step_payload(steps, "firmware-class-path").strip(),
        "vendor_links": step_payload(steps, "vendor-links").strip().splitlines(),
        "proc_modules_has_wlan": module_loaded(proc_modules, "wlan"),
        "sys_module_wlan_exists": step_ok(steps, "sys-module-wlan-ls"),
        "sys_module_wlan_has_initstate": step_ok(steps, "sys-module-wlan-initstate"),
        "sys_module_wlan_has_refcnt": step_ok(steps, "sys-module-wlan-refcnt"),
        "sys_module_wlan_entries": [line.strip() for line in sys_module_find.splitlines() if line.strip()],
        "wlan_fwpath": step_payload(steps, f"param-{safe_name('/sys/module/wlan/parameters/fwpath')}").strip(),
        "wlan_con_mode": step_payload(steps, f"param-{safe_name('/sys/module/wlan/parameters/con_mode')}").strip(),
        "wlan_country_code": step_payload(steps, f"param-{safe_name('/sys/module/wlan/parameters/country_code')}").strip(),
        "mss_state": step_payload(steps, "mss-state").strip(),
        "mdm3_state": step_payload(steps, "mdm3-state").strip(),
        "dmesg": dmesg,
        "isolated_vendor_mount_ok": mount_ok,
        "cleanup_ok": cleanup_ok,
    }
    return steps, live


def build_checks(args: argparse.Namespace, steps: list[dict[str, Any]], live: dict[str, Any]) -> list[dict[str, Any]]:
    if not live:
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command executed",
            "next_step": "run V727 lower prerequisite classifier",
        }]
    counts = (live.get("dmesg") or {}).get("counts") or {}
    static_surface = (
        live.get("sys_module_wlan_exists")
        and not live.get("proc_modules_has_wlan")
        and not live.get("sys_module_wlan_has_initstate")
        and not live.get("sys_module_wlan_has_refcnt")
        and any("/sys/module/wlan/parameters/" in entry for entry in live.get("sys_module_wlan_entries", []))
    )
    return [
        {
            "name": "native-v724-clean",
            "status": "pass" if args.expect_version in step_payload(steps, "version") and "fail=0" in step_payload(steps, "status") and "fail=0" in step_payload(steps, "selftest") else "blocked",
            "detail": {"expect_version": args.expect_version},
            "next_step": "restore expected native baseline before lower prerequisite changes",
        },
        {
            "name": "isolated-vendor-mount-cleanup",
            "status": "pass" if live.get("isolated_vendor_mount_ok") and live.get("cleanup_ok") else "blocked",
            "detail": {"sda29_dev": live.get("sda29_dev"), "cleanup_ok": live.get("cleanup_ok")},
            "next_step": "cleanup isolated vendor mount before any further live work",
        },
        {
            "name": "current-vendor-firmware-visible",
            "status": "pass" if live.get("current_vendor_firmware_hits") else "finding",
            "detail": {"hits": live.get("current_vendor_firmware_hits"), "vendor_links": live.get("vendor_links")},
            "next_step": "if absent, native root is not exposing the Android vendor Wi-Fi firmware view",
        },
        {
            "name": "isolated-vendor-firmware-visible",
            "status": "pass" if set(live.get("isolated_vendor_firmware_hits") or {}).issuperset({"/vendor/firmware/wlanmdsp.mbn", "/vendor/firmware/wlan/qca_cld/bdwlan.bin", "/vendor/firmware/wlan/qca_cld/regdb.bin"}) else "finding",
            "detail": {"hits": live.get("isolated_vendor_firmware_hits")},
            "next_step": "map actual vendor partition into the runtime namespace before expecting WLAN-PD firmware service",
        },
        {
            "name": "wlan-static-parameter-surface",
            "status": "pass" if static_surface else "review",
            "detail": {
                "sys_module_wlan_exists": live.get("sys_module_wlan_exists"),
                "proc_modules_has_wlan": live.get("proc_modules_has_wlan"),
                "has_initstate": live.get("sys_module_wlan_has_initstate"),
                "has_refcnt": live.get("sys_module_wlan_has_refcnt"),
                "vendor_lib_module_hits": live.get("vendor_lib_module_hits"),
            },
            "next_step": "treat wlan as built-in/static unless later evidence proves a loadable wlan.ko path",
        },
        {
            "name": "modem-online",
            "status": "pass" if live.get("mss_state") == "ONLINE" and live.get("mdm3_state") == "ONLINE" else "finding",
            "detail": {"mss_state": live.get("mss_state"), "mdm3_state": live.get("mdm3_state")},
            "next_step": "modem ONLINE trigger is still required after vendor firmware namespace is correct",
        },
        {
            "name": "mhi-wlfw-wlan0-progression",
            "status": "pass" if counts.get("mhi", 0) and counts.get("wlfw", 0) and counts.get("wlan0", 0) else "finding",
            "detail": {"mhi": counts.get("mhi", 0), "qca6390": counts.get("qca6390", 0), "wlfw": counts.get("wlfw", 0), "wlan0": counts.get("wlan0", 0)},
            "next_step": "do not start HAL/scan/connect until WLFW/BDF/wlan0 appears",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], live: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v727-lower-prereq-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V727 lower prerequisite classifier",
        )
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v727-lower-prereq-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear baseline or cleanup blocker before further live work",
        )
    current_missing = not live.get("current_vendor_firmware_hits")
    isolated_present = bool(live.get("isolated_vendor_firmware_hits"))
    static_wlan = next((check for check in checks if check["name"] == "wlan-static-parameter-surface"), {}).get("status") == "pass"
    if current_missing and isolated_present and static_wlan:
        return (
            "v727-vendor-root-alias-gap-and-static-wlan-surface-classified",
            True,
            "native /vendor does not expose Android vendor Wi-Fi firmware, while isolated sda29 vendor does; wlan appears as a static parameter surface rather than a loadable /proc/modules entry",
            "plan V728 around private vendor root layout proof, then smallest safe modem ONLINE trigger; keep daemon/HAL/scan/connect blocked",
        )
    if current_missing and isolated_present:
        return (
            "v727-vendor-root-alias-gap-classified",
            True,
            "native /vendor misses Wi-Fi firmware but isolated sda29 vendor contains it",
            "plan vendor root layout proof before modem ONLINE or CNSS daemon retry",
        )
    return (
        "v727-lower-prereq-review",
        True,
        "lower prerequisite evidence does not match the expected vendor alias/static wlan gap",
        "inspect V727 manifest before selecting the next live gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    counts = ((live.get("dmesg") or {}).get("counts") or {})
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    state_rows = [
        ["firmware_class.path", live.get("firmware_class_path", "")],
        ["current_vendor_firmware_hits", len(live.get("current_vendor_firmware_hits") or [])],
        ["isolated_vendor_firmware_hits", len(live.get("isolated_vendor_firmware_hits") or [])],
        ["proc_modules_has_wlan", live.get("proc_modules_has_wlan", "")],
        ["sys_module_wlan_exists", live.get("sys_module_wlan_exists", "")],
        ["sys_module_wlan_has_initstate", live.get("sys_module_wlan_has_initstate", "")],
        ["sys_module_wlan_has_refcnt", live.get("sys_module_wlan_has_refcnt", "")],
        ["wlan_fwpath", live.get("wlan_fwpath", "")],
        ["mss_state", live.get("mss_state", "")],
        ["mdm3_state", live.get("mdm3_state", "")],
    ]
    dmesg_rows = [[name, str(counts.get(name, 0))] for name, _ in DMESG_PATTERNS]
    return "\n".join([
        "# V727 Lower Prerequisite Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- isolated_read_only_vendor_mount_executed: `{manifest['isolated_read_only_vendor_mount_executed']}`",
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
        markdown_table(["marker", "count"], dmesg_rows),
        "",
        "## Firmware Hits",
        "",
        "- current `/vendor`:",
        "\n".join(f"  - `{path}`" for path in (live.get("current_vendor_firmware_hits") or [])) or "  - none",
        "- isolated `sda29` vendor:",
        "\n".join(f"  - `{path}`" for path in (live.get("isolated_vendor_firmware_hits") or [])) or "  - none",
        "- isolated firmware tree sample:",
        "\n".join(f"  - `{path}`" for path in (live.get("isolated_firmware_tree_hits") or [])) or "  - none",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    live: dict[str, Any] = {}
    if args.command == "run":
        steps, live = collect_live(args, store)
    checks = build_checks(args, steps, live)
    decision, pass_ok, reason, next_step = decide(args.command, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v727",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": checks,
        "live": live,
        "device_commands_executed": args.command == "run",
        "device_mutations": bool(live),
        "isolated_read_only_vendor_mount_executed": bool(live.get("isolated_vendor_mount_ok")),
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
    latest = repo_path("tmp/wifi/latest-v727-lower-prereq.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"isolated_read_only_vendor_mount_executed: {manifest['isolated_read_only_vendor_mount_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
