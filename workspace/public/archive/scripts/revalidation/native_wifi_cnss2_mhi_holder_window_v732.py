#!/usr/bin/env python3
"""V732 CNSS2/MHI observation inside a firmware-mounted modem holder window.

This runner applies the V731 safe prerequisite window, then observes only the
SM8250 CNSS2/QCA6390 path:

    firmware mounts -> subsys_modem holder -> modem QRTR RX -> CNSS2/MHI/WLFW?

It intentionally does not start lower companion services, CNSS daemon,
service-manager, Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, DHCP,
route changes, credential use, external ping, module load/unload, esoc0, or
subsystem state writes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90ctl import run_cmdv1_command
from a90harness.evidence import EvidenceStore, write_private_text
from native_wifi_firmware_mounted_modem_holder_v731 import (
    DEFAULT_BUSYBOX,
    DEFAULT_QRTR_RX_POLL_SEC,
    DEFAULT_QRTR_RX_TIMEOUT_SEC,
    FIRMWARE_CLASS_PATH,
    GLOBAL_MODEM_BLOB_PATHS,
    MDM3_CRASH_COUNT,
    MDM3_STATE,
    MSS_CRASH_COUNT,
    MSS_STATE,
    SUBSYS_MODEM_DEV,
    dmesg_delta,
    holder_script,
    marker_summary,
    parse_dev,
    path_exists,
    reboot_and_wait,
    shell_quote,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v732-cnss2-mhi-holder-window")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_HOLD_SEC = 150
DEFAULT_V731_MANIFEST = Path("tmp/wifi/v731-firmware-mounted-modem-holder/manifest.json")
PROOF_PREFIX = "/tmp/a90-v732-"

WLAN_FIRMWARE_PATHS = (
    "/vendor/firmware_mnt/image/wlanmdsp.mbn",
    "/vendor/firmware_mnt/image/wlanmdsp.mdt",
    "/vendor/firmware_mnt/image/wlanmdsp.b00",
    "/vendor/firmware-modem/image/wlanmdsp.mbn",
    "/vendor/firmware-modem/image/wlanmdsp.mdt",
    "/vendor/firmware-modem/image/wlanmdsp.b00",
    "/vendor/firmware/wlanmdsp.mbn",
    "/vendor/firmware/wlan/qca_cld/bdwlan.bin",
    "/vendor/firmware/wlan/qca_cld/regdb.bin",
    "/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
    "/mnt/system/vendor/firmware/wlanmdsp.mbn",
    "/mnt/system/vendor/firmware/wlan/qca_cld/bdwlan.bin",
    "/mnt/system/vendor/firmware/wlan/qca_cld/regdb.bin",
)
CNSS_SYSFS_PATHS = (
    "/sys/bus/platform/drivers/cnss2",
    "/sys/bus/platform/drivers/icnss",
    "/sys/devices/platform/soc/18800000.qcom,icnss",
    "/sys/module/wlan",
    "/sys/module/wlan/initstate",
    "/sys/module/wlan/refcnt",
    "/sys/module/wlan/parameters/fwpath",
    "/sys/module/wlan/parameters/con_mode",
    "/sys/module/wlan/parameters/country_code",
)
FORBIDDEN_TERMS = (
    "subsys_esoc0",
    "/sys/class/subsys/subsys_esoc0",
    "/dev/subsys_esoc0",
    "echo online",
    "> /sys/devices",
    "insmod",
    "rmmod",
    "modprobe",
    "qcwlanstate",
    "wifi-companion-start-only",
    "cnss-daemon",
    "service-manager",
    "android.hardware.wifi",
    "IWifi",
    "wificond",
    "wpa_supplicant",
    "hostapd",
    "svc wifi",
    "cmd wifi",
    "iw ",
    "dhcp",
    " ip route",
    " ip addr",
    " ping ",
)
QRTR_SERVICE_RE = re.compile(r"(?<![0-9])(?P<svc>69|74|180)(?![0-9])")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=DEFAULT_HOLD_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=DEFAULT_V731_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def validate_device_command(command: list[str], proof_base: str | None = None) -> None:
    joined = " ".join(command)
    lowered = joined.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in lowered:
            raise RuntimeError(f"forbidden V732 command term {term!r}: {joined}")
    if command[0] in {"version", "status", "selftest", "hide", "cat", "stat", "mkdir", "mknodb", "umount", "reboot"}:
        return
    if command == ["mountsystem", "ro"]:
        return
    if command[:2] == ["run", DEFAULT_TOYBOX] and len(command) >= 3:
        if command[2] in {"mount", "rm", "rmdir", "dmesg", "ls", "ps", "cat"}:
            return
    if command[:2] == ["run", DEFAULT_BUSYBOX] and len(command) >= 4 and command[2] == "sh":
        script = command[-1]
        if proof_base and proof_base not in script:
            raise RuntimeError(f"V732 holder script missing proof path: {joined}")
        return
    raise RuntimeError(f"unexpected V732 command: {joined}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             proof_base: str | None = None) -> dict[str, Any]:
    validate_device_command(command, proof_base)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
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


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return safe_name(args.proof_id)
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def active_holder_hits(ps_text: str) -> list[str]:
    patterns = (
        "a90-v596-subsys-modem",
        "a90-v729-",
        "a90-v731-",
        "a90-v732-",
    )
    return [line.strip() for line in ps_text.splitlines() if any(pattern in line for pattern in patterns)]


def module_loaded(proc_modules: str, name: str) -> bool:
    return any(line.split()[:1] == [name] for line in proc_modules.splitlines())


def qrtr_service_counts(text: str) -> dict[str, int]:
    counts = {"69": 0, "74": 0, "180": 0}
    for match in QRTR_SERVICE_RE.finditer(text):
        counts[match.group("svc")] += 1
    return counts


def capture_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    run_step(args, store, steps, "hide-menu", ["hide"], 10.0)
    mount_steps: list[dict[str, Any]] = []
    mount_args = argparse.Namespace(**vars(args))
    mount_args.command = "preflight"
    preflight = mountv.capture_preflight(mount_args, store, mount_steps)
    steps.extend(mount_steps)
    run_step(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], 30.0)
    run_step(args, store, steps, "firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 10.0)
    run_step(args, store, steps, "subsys-modem-dev", ["cat", SUBSYS_MODEM_DEV], 10.0)
    run_step(args, store, steps, "mss-state-before", ["cat", MSS_STATE], 10.0)
    run_step(args, store, steps, "mss-crash-before", ["cat", MSS_CRASH_COUNT], 10.0)
    run_step(args, store, steps, "mdm3-state-before", ["cat", MDM3_STATE], 10.0)
    run_step(args, store, steps, "mdm3-crash-before", ["cat", MDM3_CRASH_COUNT], 10.0)
    run_step(args, store, steps, "proc-modules-before", ["cat", "/proc/modules"], 20.0)
    run_step(args, store, steps, "wlan-module-ls-before", ["run", args.toybox, "ls", "-l", "/sys/module/wlan"], 10.0)
    run_step(args, store, steps, "cnss2-driver-ls-before", ["run", args.toybox, "ls", "-l", "/sys/bus/platform/drivers/cnss2"], 10.0)
    run_step(args, store, steps, "cnss-device-ls-before", ["run", args.toybox, "ls", "-l", "/sys/devices/platform/soc/18800000.qcom,icnss"], 10.0)
    run_step(args, store, steps, "ps-before", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    return preflight


def preflight_blockers(args: argparse.Namespace,
                       steps: list[dict[str, Any]],
                       preflight: dict[str, Any],
                       v731: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if args.expect_version not in step_payload(steps, "version"):
        blockers.append("unexpected-native-version")
    if "fail=0" not in step_payload(steps, "status") or "fail=0" not in step_payload(steps, "selftest"):
        blockers.append("native-not-healthy")
    if preflight.get("pre_mount_hits") and any(preflight["pre_mount_hits"].get(target) for target in mountv.PARTITION_TARGETS.values()):
        blockers.append("firmware-target-already-mounted")
    if not {"apnhlos", "modem"}.issubset(set((preflight.get("partitions") or {}).keys())):
        blockers.append("firmware-partitions-missing")
    if preflight.get("vendor_rootfs_shim_required") and not preflight.get("vendor_rootfs_shim_allowed_target"):
        blockers.append("vendor-shim-not-allowed")
    if not parse_dev(step_payload(steps, "subsys-modem-dev")):
        blockers.append("subsys-modem-dev-missing")
    if active_holder_hits(step_payload(steps, "ps-before")):
        blockers.append("residual-holder-process")
    if v731.get("exists") and v731.get("decision") != "v731-firmware-mounted-modem-holder-qrtr-rx-pass":
        blockers.append("v731-reference-not-qrtr-rx-pass")
    return blockers


def wait_for_qrtr_rx(args: argparse.Namespace,
                     store: EvidenceStore,
                     steps: list[dict[str, Any]],
                     before_text: str,
                     proof_base: str) -> dict[str, Any]:
    started = time.monotonic()
    attempts: list[dict[str, Any]] = []
    last_delta = ""
    attempt = 0
    while time.monotonic() - started <= args.qrtr_rx_timeout_sec:
        attempt += 1
        item = run_step(args, store, steps, f"wait-qrtr-rx-dmesg-{attempt:02d}", ["run", args.toybox, "dmesg"], 60.0, proof_base)
        delta = dmesg_delta(before_text, str(item.get("payload") or ""))
        summary = marker_summary(delta)
        last_delta = delta
        attempts.append({
            "attempt": attempt,
            "elapsed_sec": round(time.monotonic() - started, 3),
            "qrtr_rx": summary["counts"].get("qrtr_rx", 0),
            "qrtr_tx": summary["counts"].get("qrtr_tx", 0),
            "sysmon_qmi": summary["counts"].get("sysmon_qmi", 0),
            "mhi": summary["counts"].get("mhi", 0),
            "wlfw": summary["counts"].get("wlfw", 0),
            "kernel_warning": summary["counts"].get("kernel_warning", 0),
        })
        if summary["counts"].get("qrtr_rx", 0) > 0:
            write_capture(store, "wait-qrtr-rx-delta", delta)
            return {
                "seen": True,
                "elapsed_sec": round(time.monotonic() - started, 3),
                "attempts": attempts,
                "delta_file": "native/wait-qrtr-rx-delta.txt",
                "markers": summary,
            }
        time.sleep(max(0.5, args.qrtr_rx_poll_sec))
    write_capture(store, "wait-qrtr-rx-delta", last_delta)
    return {
        "seen": False,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "attempts": attempts,
        "delta_file": "native/wait-qrtr-rx-delta.txt",
        "markers": marker_summary(last_delta),
    }


def capture_observation_window(args: argparse.Namespace,
                               store: EvidenceStore,
                               steps: list[dict[str, Any]],
                               proof_base: str) -> None:
    run_step(args, store, steps, "proc-modules-after-holder", ["cat", "/proc/modules"], 20.0, proof_base)
    run_step(args, store, steps, "proc-net-qrtr-after-holder", ["cat", "/proc/net/qrtr"], 15.0, proof_base)
    run_step(args, store, steps, "proc-net-dev-after-holder", ["cat", "/proc/net/dev"], 15.0, proof_base)
    run_step(args, store, steps, "rpmsg-after-holder", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0, proof_base)
    run_step(args, store, steps, "pci-devices-after-holder", ["run", args.toybox, "ls", "-l", "/sys/bus/pci/devices"], 10.0, proof_base)
    for path in CNSS_SYSFS_PATHS:
        if path.endswith(("initstate", "refcnt")) or "/parameters/" in path:
            run_step(args, store, steps, f"cat-{safe_name(path)}", ["cat", path], 10.0, proof_base)
        else:
            run_step(args, store, steps, f"ls-{safe_name(path)}", ["run", args.toybox, "ls", "-l", path], 10.0, proof_base)
    for path in GLOBAL_MODEM_BLOB_PATHS + WLAN_FIRMWARE_PATHS:
        run_step(args, store, steps, f"stat-{safe_name(path)}", ["stat", path], 10.0, proof_base)
    run_step(args, store, steps, "ps-after-holder", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0, proof_base)


def run_live(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             preflight: dict[str, Any]) -> dict[str, Any]:
    label = proof_id(args)
    base = PROOF_PREFIX + label
    node = f"{base}/subsys_modem"
    status_file = f"{base}/holder.status"
    pid_file = f"{base}/holder.pid"
    before = run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    mount_results: list[str] = []
    reboot: dict[str, Any] = {}
    try:
        for name, command, timeout in mountv.build_mount_commands(preflight, base):
            item = run_step(args, store, steps, f"v732-{name}", command, timeout, base)
            mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0, base)
        run_step(args, store, steps, "mounted-firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 10.0, base)
        dev = parse_dev(step_payload(steps, "subsys-modem-dev"))
        if not dev:
            raise RuntimeError("subsys_modem dev missing after preflight")
        script = holder_script(args, node, status_file, pid_file, dev[0], dev[1])
        safe_script = script.replace(node, "$PROOF/subsys_modem").replace(base, "$PROOF")
        write_capture(store, "holder-script-redacted", safe_script)
        run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", script], 25.0, base)
        run_step(args, store, steps, "mss-state-after-holder", ["cat", MSS_STATE], 10.0, base)
        run_step(args, store, steps, "mss-crash-after-holder", ["cat", MSS_CRASH_COUNT], 10.0, base)
        run_step(args, store, steps, "mdm3-state-after-holder", ["cat", MDM3_STATE], 10.0, base)
        run_step(args, store, steps, "mdm3-crash-after-holder", ["cat", MDM3_CRASH_COUNT], 10.0, base)
        qrtr_wait = wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""), base)
        capture_observation_window(args, store, steps, base)
        run_step(args, store, steps, "mss-state-after-observe", ["cat", MSS_STATE], 10.0, base)
        run_step(args, store, steps, "mdm3-state-after-observe", ["cat", MDM3_STATE], 10.0, base)
        after = run_step(args, store, steps, "dmesg-after-observe", ["run", args.toybox, "dmesg"], 60.0, base)
        delta = dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
        write_capture(store, "dmesg-delta", delta)
        markers = marker_summary(delta)
    finally:
        reboot = reboot_and_wait(args, store)
    mounted = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    proc_modules_before = step_payload(steps, "proc-modules-before")
    proc_modules_after = step_payload(steps, "proc-modules-after-holder")
    proc_qrtr = step_payload(steps, "proc-net-qrtr-after-holder")
    return {
        "base": base,
        "node": node,
        "mount_results": mount_results,
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": {
            path: path_exists(step_payload(steps, f"stat-{safe_name(path)}"))
            for path in GLOBAL_MODEM_BLOB_PATHS
        },
        "wlan_firmware_visible": {
            path: path_exists(step_payload(steps, f"stat-{safe_name(path)}"))
            for path in WLAN_FIRMWARE_PATHS
        },
        "holder_opened": "v731.holder.status=opened" in step_payload(steps, "start-modem-holder"),
        "mss_before": step_payload(steps, "mss-state-before").strip(),
        "mss_after_holder": step_payload(steps, "mss-state-after-holder").strip(),
        "mss_after_observe": step_payload(steps, "mss-state-after-observe").strip(),
        "mdm3_before": step_payload(steps, "mdm3-state-before").strip(),
        "mdm3_after_holder": step_payload(steps, "mdm3-state-after-holder").strip(),
        "mdm3_after_observe": step_payload(steps, "mdm3-state-after-observe").strip(),
        "mss_crash_before": step_payload(steps, "mss-crash-before").strip(),
        "mss_crash_after_holder": step_payload(steps, "mss-crash-after-holder").strip(),
        "mdm3_crash_before": step_payload(steps, "mdm3-crash-before").strip(),
        "mdm3_crash_after_holder": step_payload(steps, "mdm3-crash-after-holder").strip(),
        "wlan_module_loaded_before": module_loaded(proc_modules_before, "wlan"),
        "wlan_module_loaded_after": module_loaded(proc_modules_after, "wlan"),
        "wlan_sys_module_exists": path_exists(step_payload(steps, "wlan-module-ls-before")) or path_exists(step_payload(steps, "ls-sys-module-wlan")),
        "wlan_initstate": step_payload(steps, "cat-sys-module-wlan-initstate").strip(),
        "wlan_refcnt": step_payload(steps, "cat-sys-module-wlan-refcnt").strip(),
        "cnss2_driver_exists": path_exists(step_payload(steps, "cnss2-driver-ls-before")) or path_exists(step_payload(steps, "ls-sys-bus-platform-drivers-cnss2")),
        "cnss_device_exists": path_exists(step_payload(steps, "cnss-device-ls-before")) or path_exists(step_payload(steps, "ls-sys-devices-platform-soc-18800000.qcom-icnss")),
        "qrtr_services_after_holder": qrtr_service_counts(proc_qrtr),
        "proc_qrtr_after_holder_file": "native/proc-net-qrtr-after-holder.txt",
        "proc_net_dev_after_holder_file": "native/proc-net-dev-after-holder.txt",
        "qrtr_rx_wait": qrtr_wait,
        "markers": markers if "markers" in locals() else {},
        "reboot_cleanup": reboot,
    }


def build_checks(args: argparse.Namespace,
                 steps: list[dict[str, Any]],
                 preflight: dict[str, Any],
                 v731: dict[str, Any],
                 live: dict[str, Any] | None,
                 blockers: list[str]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command executed",
            "next_step": "run V732 CNSS2/MHI holder-window observer",
        }]
    checks: list[dict[str, Any]] = [
        {
            "name": "preflight-blockers",
            "status": "pass" if not blockers else "blocked",
            "detail": {"blockers": blockers},
            "next_step": "clear blockers before live V732",
        },
        {
            "name": "v731-reference",
            "status": "pass" if v731.get("decision") == "v731-firmware-mounted-modem-holder-qrtr-rx-pass" else "review",
            "detail": {"decision": v731.get("decision"), "pass": v731.get("pass"), "path": v731.get("path")},
            "next_step": "rerun V731 if current firmware-mounted holder baseline is stale",
        },
    ]
    if not live:
        return checks
    counts = ((live.get("markers") or {}).get("counts") or {})
    reboot = live.get("reboot_cleanup") or {}
    wlan_visible = live.get("wlan_firmware_visible") or {}
    checks.extend([
        {
            "name": "firmware-mounted",
            "status": "pass" if all((live.get("mounted_hits") or {}).get(target) for target in mountv.PARTITION_TARGETS.values()) and any((live.get("modem_blob_visible") or {}).values()) else "blocked",
            "detail": {"mounted_hits": live.get("mounted_hits"), "modem_blob_visible": live.get("modem_blob_visible")},
            "next_step": "fix firmware mount parity before modem holder retry",
        },
        {
            "name": "modem-holder-window",
            "status": "pass" if live.get("holder_opened") and "ONLINE" in {live.get("mss_after_holder"), live.get("mss_after_observe")} else "finding",
            "detail": {"holder_opened": live.get("holder_opened"), "mss": [live.get("mss_before"), live.get("mss_after_holder"), live.get("mss_after_observe")], "mdm3": [live.get("mdm3_before"), live.get("mdm3_after_holder"), live.get("mdm3_after_observe")]},
            "next_step": "if mss is not ONLINE, retry only after firmware mount regression is explained",
        },
        {
            "name": "wlan-load-semantics",
            "status": "pass" if live.get("wlan_sys_module_exists") and not live.get("wlan_module_loaded_after") else "review",
            "detail": {"sys_module_exists": live.get("wlan_sys_module_exists"), "proc_modules_before": live.get("wlan_module_loaded_before"), "proc_modules_after": live.get("wlan_module_loaded_after"), "initstate": live.get("wlan_initstate"), "refcnt": live.get("wlan_refcnt")},
            "next_step": "treat wlan as built-in/static unless Android proves a loadable wlan.ko path",
        },
        {
            "name": "wlan-firmware-visibility",
            "status": "pass" if any(wlan_visible.values()) else "finding",
            "detail": {"visible": {path: visible for path, visible in wlan_visible.items() if visible}, "checked_count": len(wlan_visible)},
            "next_step": "if no global wlan firmware is visible, keep real vendor-root proof separate before companion/tftp retry",
        },
        {
            "name": "cnss2-surface",
            "status": "pass" if live.get("cnss2_driver_exists") or live.get("cnss_device_exists") else "finding",
            "detail": {"cnss2_driver_exists": live.get("cnss2_driver_exists"), "cnss_device_exists": live.get("cnss_device_exists")},
            "next_step": "if absent, inspect platform probe and device tree binding before any daemon retry",
        },
        {
            "name": "mhi-wlfw-progress",
            "status": "pass" if counts.get("wlan0", 0) or counts.get("wlfw", 0) else "finding",
            "detail": {"markers": {key: counts.get(key, 0) for key in ("mhi", "qca6390", "wlfw", "bdf", "wlan0")}, "qrtr_services": live.get("qrtr_services_after_holder")},
            "next_step": "if still zero, next work is lower-prereq gap, not HAL/scan/connect",
        },
        {
            "name": "kernel-warning-review",
            "status": "review" if counts.get("kernel_warning", 0) else "pass",
            "detail": {"kernel_warning": counts.get("kernel_warning", 0), "first": ((live.get("markers") or {}).get("first_lines") or {}).get("kernel_warning", "")},
            "next_step": "classify warnings before widening live actions",
        },
        {
            "name": "postflight-reboot-cleanup",
            "status": "pass" if reboot.get("version_seen") and reboot.get("status_healthy") else "blocked",
            "detail": reboot,
            "next_step": "manually verify native if reboot cleanup did not prove health",
        },
        {
            "name": "forbidden-actions",
            "status": "pass",
            "detail": "no esoc0, state write, module load, daemon, service-manager, Wi-Fi HAL, scan/connect, credential, DHCP/route, external ping, or boot write",
            "next_step": "keep same guardrails until WLFW/service 69 appears",
        },
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v732-cnss2-mhi-holder-window-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V732 read-only holder-window observer",
        )
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v732-cnss2-mhi-holder-window-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear blocker before live retry",
        )
    if not live:
        return (
            "v732-cnss2-mhi-holder-window-preflight-ready",
            True,
            "preflight ready",
            "run live V732 observer",
        )
    counts = ((live.get("markers") or {}).get("counts") or {})
    services = live.get("qrtr_services_after_holder") or {}
    if counts.get("kernel_warning", 0):
        return (
            "v732-cnss2-mhi-holder-window-warning-classified",
            True,
            "observer completed but kernel warning markers appeared; reboot cleanup restored native",
            "classify warning before widening live work",
        )
    if counts.get("wlan0", 0) or counts.get("wlfw", 0) or services.get("69", 0):
        return (
            "v732-cnss2-mhi-holder-window-wlfw-advance",
            True,
            "firmware-mounted holder produced WLFW/service69 or wlan0 evidence without daemon/HAL/scan/connect",
            "capture bounded BDF/fw-ready evidence before Wi-Fi HAL",
        )
    if counts.get("mhi", 0) or counts.get("qca6390", 0):
        return (
            "v732-cnss2-mhi-holder-window-mhi-advance",
            True,
            "firmware-mounted holder produced MHI/QCA6390 evidence but no WLFW/service69",
            "classify MHI-to-WLFW firmware/vendor-root gap",
        )
    if (live.get("qrtr_rx_wait") or {}).get("seen") and "ONLINE" in {live.get("mss_after_holder"), live.get("mss_after_observe")}:
        return (
            "v732-cnss2-mhi-holder-window-cnss2-gap-classified",
            True,
            "modem ONLINE and QRTR RX returned, but CNSS2/MHI/WLFW/service69 did not advance in the read-only holder window",
            "next gate should address real vendor-root/tftp or exact CNSS2 trigger, still below HAL/scan/connect",
        )
    return (
        "v732-cnss2-mhi-holder-window-no-modem-readiness",
        True,
        "holder window did not restore modem QRTR readiness on this run",
        "compare with V731 evidence before adding companion services",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    state_rows = [
        ["mounted_hits", json.dumps(live.get("mounted_hits", {}), sort_keys=True)],
        ["modem_blob_visible", json.dumps(live.get("modem_blob_visible", {}), sort_keys=True)],
        ["wlan_firmware_visible_any", str(any((live.get("wlan_firmware_visible") or {}).values()))],
        ["holder_opened", live.get("holder_opened", "")],
        ["mss", f"{live.get('mss_before', '')}->{live.get('mss_after_holder', '')}->{live.get('mss_after_observe', '')}"],
        ["mdm3", f"{live.get('mdm3_before', '')}->{live.get('mdm3_after_holder', '')}->{live.get('mdm3_after_observe', '')}"],
        ["wlan_module", json.dumps({"sys": live.get("wlan_sys_module_exists"), "proc": live.get("wlan_module_loaded_after"), "initstate": live.get("wlan_initstate"), "refcnt": live.get("wlan_refcnt")}, sort_keys=True)],
        ["cnss2", json.dumps({"driver": live.get("cnss2_driver_exists"), "device": live.get("cnss_device_exists")}, sort_keys=True)],
        ["qrtr_services", json.dumps(live.get("qrtr_services_after_holder", {}), sort_keys=True)],
        ["reboot_cleanup", json.dumps(live.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    marker_rows = [[name, str(counts.get(name, 0))] for name in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "rpmsg", "mhi", "qca6390", "wlfw", "bdf", "wlan0", "kernel_warning")]
    return "\n".join([
        "# V732 CNSS2/MHI Holder-window Observer",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- subsys_modem_open_attempted: `{manifest['subsys_modem_open_attempted']}`",
        f"- lower_companion_start_executed: `{manifest['lower_companion_start_executed']}`",
        f"- daemon_or_hal_start_executed: `{manifest['daemon_or_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
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
        "## Dmesg Marker Counts",
        "",
        markdown_table(["marker", "count"], marker_rows),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    v731 = load_json_if_exists(args.v731_manifest)
    preflight: dict[str, Any] = {}
    live: dict[str, Any] | None = None
    blockers: list[str] = []
    if args.command == "run":
        preflight = capture_preflight(args, store, steps)
        blockers = preflight_blockers(args, steps, preflight, v731)
        if not blockers:
            live = run_live(args, store, steps, preflight)
    checks = build_checks(args, steps, preflight, v731, live, blockers)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v732",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "v731": {"decision": v731.get("decision"), "pass": v731.get("pass"), "path": v731.get("path", str(repo_path(args.v731_manifest)))},
        "preflight": preflight,
        "steps": steps,
        "checks": checks,
        "live": live or {},
        "device_commands_executed": args.command == "run",
        "firmware_mounts_executed": bool(live),
        "subsys_modem_open_attempted": bool(live),
        "subsys_modem_opened": bool((live or {}).get("holder_opened")),
        "esoc0_node_created": False,
        "esoc0_open_executed": False,
        "subsystem_writes_executed": False,
        "module_load_unload_executed": False,
        "lower_companion_start_executed": False,
        "cnss_daemon_start_executed": False,
        "daemon_or_hal_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
        "reboot_cleanup_executed": bool(live),
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    latest = repo_path("tmp/wifi/latest-v732-cnss2-mhi-holder-window.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"subsys_modem_open_attempted: {manifest['subsys_modem_open_attempted']}")
    print(f"subsys_modem_opened: {manifest['subsys_modem_opened']}")
    print(f"lower_companion_start_executed: {manifest['lower_companion_start_executed']}")
    print(f"daemon_or_hal_start_executed: {manifest['daemon_or_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
