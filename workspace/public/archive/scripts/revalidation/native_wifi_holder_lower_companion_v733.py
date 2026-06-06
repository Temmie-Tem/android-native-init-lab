#!/usr/bin/env python3
"""V733 lower companion observer inside the firmware-mounted modem holder window.

This runner extends V732 by adding only the lower companion/TFTP stack after
modem QRTR RX is observed:

    qrtr-ns -> rmt_storage -> tftp_server -> pd-mapper

It does not start CNSS daemon, service-manager, Wi-Fi HAL, wificond,
supplicant, hostapd, scan/connect, credential use, DHCP, route changes,
external ping, module load/unload, esoc0, or subsystem state writes.
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
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v733-holder-lower-companion")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX_PATH = DEFAULT_BUSYBOX
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "547232ddb352740bb7a7f1d0f9116162584e34a536b9d9b77869ed8d838e7c89"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v121"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_HOLD_SEC = 150
DEFAULT_COMPANION_RUNTIME_SEC = 12
DEFAULT_V731_MANIFEST = Path("tmp/wifi/v731-firmware-mounted-modem-holder/manifest.json")
DEFAULT_V732_MANIFEST = Path("tmp/wifi/v732-cnss2-mhi-holder-window/manifest.json")
DEFAULT_V490_MANIFEST = Path("tmp/wifi/v733-v490-current-run/manifest.json")
PROOF_PREFIX = "/tmp/a90-v733-"
MODE = "wifi-companion-post-sysmon-observer-start-only"
EXPECTED_ORDER = "qrtr_ns,rmt_storage,tftp_server,pd_mapper"

WLAN_FIRMWARE_PATHS = (
    "/vendor/firmware/wlanmdsp.mbn",
    "/vendor/firmware/wlan/qca_cld/bdwlan.bin",
    "/vendor/firmware/wlan/qca_cld/regdb.bin",
    "/vendor/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
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
    "cnss-daemon",
    "cnss_diag",
    "servicemanager",
    "hwservicemanager",
    "vndservicemanager",
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
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX_PATH)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=DEFAULT_V732_MANIFEST)
    parser.add_argument("--v490-manifest", type=Path, default=DEFAULT_V490_MANIFEST)
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


def helper_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        MODE,
        "--null-device-mode",
        "dev-null",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "minimal-vendor",
        "--android-selinux-context-mode",
        "service-defaults",
        "--timeout-sec",
        str(args.companion_runtime_sec),
        "--allow-wifi-companion-start-only",
        "--allow-qrtr-ns-readback",
    ]


def validate_device_command(args: argparse.Namespace, command: list[str], proof_base: str | None = None) -> None:
    joined = " ".join(command)
    if command[:2] == ["run", args.helper] and command[2:] == ["--help"]:
        return
    if command == helper_command(args):
        return
    lowered = joined.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in lowered:
            raise RuntimeError(f"forbidden V733 command term {term!r}: {joined}")
    if command[0] in {"version", "status", "selftest", "hide", "cat", "stat", "mkdir", "mknodb", "umount", "reboot"}:
        return
    if command == ["mountsystem", "ro"]:
        return
    if command[:2] == ["run", args.toybox] and len(command) >= 3:
        if command[2] in {"mount", "rm", "rmdir", "dmesg", "ls", "ps", "cat", "sha256sum"}:
            return
    if command[:2] == ["run", args.busybox] and len(command) >= 4 and command[2] == "sh":
        script = command[-1]
        if proof_base and proof_base not in script:
            raise RuntimeError(f"V733 holder script missing proof path: {joined}")
        return
    raise RuntimeError(f"unexpected V733 command: {joined}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             proof_base: str | None = None) -> dict[str, Any]:
    validate_device_command(args, command, proof_base)
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


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return safe_name(args.proof_id)
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw in text.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        if key:
            keys[key] = value.strip().strip('"')
    return keys


def int_key(keys: dict[str, str], key: str) -> int:
    try:
        return int(keys.get(key, "0"))
    except ValueError:
        return 0


def helper_surface(text: str) -> dict[str, Any]:
    keys = parse_keys(text)
    return {
        "keys": keys,
        "mode": keys.get("mode", ""),
        "order": keys.get("wifi_companion_start.order", ""),
        "child_started": int_key(keys, "wifi_companion_start.child_started"),
        "all_observable": int_key(keys, "wifi_companion_start.all_observable"),
        "all_postflight_safe": int_key(keys, "wifi_companion_start.all_postflight_safe"),
        "timed_out": int_key(keys, "wifi_companion_start.timed_out"),
        "result": keys.get("wifi_companion_start.result", ""),
        "reason": keys.get("wifi_companion_start.reason", ""),
        "qipcrtr_after_spawn": int_key(keys, "wifi_companion_start.net_after_spawn.qipcrtr_present"),
        "qipcrtr_window": int_key(keys, "wifi_companion_start.net_window.qipcrtr_present"),
        "qipcrtr_after_cleanup": int_key(keys, "wifi_companion_start.net_after_cleanup.qipcrtr_present"),
        "cnss_daemon": int_key(keys, "wifi_companion_start.cnss_daemon"),
        "service_manager": int_key(keys, "wifi_companion_start.service_manager"),
        "wifi_hal": int_key(keys, "wifi_companion_start.wifi_hal"),
        "wificond": int_key(keys, "wifi_companion_start.wificond"),
        "scan_connect_linkup": int_key(keys, "wifi_companion_start.scan_connect_linkup"),
        "external_ping": int_key(keys, "wifi_companion_start.external_ping"),
        "qmi_attempted": int_key(keys, "qrtr_readback.qmi_attempted"),
        "service_events": int_key(keys, "qrtr_readback.service_events"),
        "timeouts": int_key(keys, "qrtr_readback.timeouts"),
    }


def active_process_hits(ps_text: str) -> list[str]:
    patterns = (
        "a90-v596-subsys-modem",
        "a90-v729-",
        "a90-v731-",
        "a90-v732-",
        "a90-v733-",
        "qrtr-ns",
        "rmt_storage",
        "tftp_server",
        "pd-mapper",
        "cnss-daemon",
        "wificond",
        "wpa_supplicant",
        "android.hardware.wifi",
    )
    return [line.strip() for line in ps_text.splitlines() if any(pattern in line for pattern in patterns)]


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
    run_step(args, store, steps, "proc-mounts", ["cat", "/proc/mounts"], 20.0)
    run_step(args, store, steps, "selinux-status", ["stat", "/sys/fs/selinux/status"], 10.0)
    run_step(args, store, steps, "helper-sha", ["run", args.toybox, "sha256sum", args.helper], 15.0)
    run_step(args, store, steps, "helper-usage", ["run", args.helper, "--help"], 25.0)
    run_step(args, store, steps, "firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 10.0)
    run_step(args, store, steps, "subsys-modem-dev", ["cat", SUBSYS_MODEM_DEV], 10.0)
    run_step(args, store, steps, "mss-state-before", ["cat", MSS_STATE], 10.0)
    run_step(args, store, steps, "mss-crash-before", ["cat", MSS_CRASH_COUNT], 10.0)
    run_step(args, store, steps, "mdm3-state-before", ["cat", MDM3_STATE], 10.0)
    run_step(args, store, steps, "mdm3-crash-before", ["cat", MDM3_CRASH_COUNT], 10.0)
    run_step(args, store, steps, "ps-before", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    return preflight


def helper_ready(args: argparse.Namespace, steps: list[dict[str, Any]]) -> bool:
    sha = step_payload(steps, "helper-sha")
    usage = step_payload(steps, "helper-usage")
    return (
        args.helper_sha256 in sha
        and args.helper_marker in usage
        and MODE in usage
        and "--allow-wifi-companion-start-only" in usage
        and "--allow-qrtr-ns-readback" in usage
    )


def preflight_blockers(args: argparse.Namespace,
                       steps: list[dict[str, Any]],
                       preflight: dict[str, Any],
                       v731: dict[str, Any],
                       v732: dict[str, Any],
                       v490: dict[str, Any]) -> list[str]:
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
    if "/sys/fs/selinux" not in step_payload(steps, "proc-mounts") or "No such file" in step_payload(steps, "selinux-status"):
        blockers.append("selinuxfs-not-mounted")
    if not helper_ready(args, steps):
        blockers.append("helper-v121-not-ready")
    if not parse_dev(step_payload(steps, "subsys-modem-dev")):
        blockers.append("subsys-modem-dev-missing")
    if active_process_hits(step_payload(steps, "ps-before")):
        blockers.append("residual-target-process")
    if v731.get("decision") != "v731-firmware-mounted-modem-holder-qrtr-rx-pass":
        blockers.append("v731-reference-missing")
    if v732.get("decision") != "v732-cnss2-mhi-holder-window-cnss2-gap-classified":
        blockers.append("v732-reference-missing")
    if v490.get("decision") != "v490-selinux-policy-load-proof-pass":
        blockers.append("v490-current-policy-load-missing")
    if not (1 <= args.companion_runtime_sec <= 30):
        blockers.append("companion-runtime-out-of-range")
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
    helper_item: dict[str, Any] | None = None
    qrtr_wait: dict[str, Any] = {}
    try:
        for name, command, timeout in mountv.build_mount_commands(preflight, base):
            item = run_step(args, store, steps, f"v733-{name}", command, timeout, base)
            mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0, base)
        run_step(args, store, steps, "mounted-firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 10.0, base)
        for path in GLOBAL_MODEM_BLOB_PATHS + WLAN_FIRMWARE_PATHS:
            run_step(args, store, steps, f"mounted-stat-{safe_name(path)}", ["stat", path], 10.0, base)

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
        if qrtr_wait.get("seen"):
            helper_item = run_step(args, store, steps, "lower-companion-start-only", helper_command(args), args.companion_runtime_sec + 75.0, base)
        else:
            helper_item = {
                "name": "lower-companion-start-only",
                "ok": True,
                "rc": 0,
                "status": "skipped",
                "command": " ".join(helper_command(args)),
                "duration_sec": 0,
                "payload": "skipped: QRTR RX marker was not observed\n",
                "file": write_capture(store, "lower-companion-start-only-skipped", "skipped: QRTR RX marker was not observed\n"),
            }
            steps.append(helper_item)
        run_step(args, store, steps, "mss-state-after-companion", ["cat", MSS_STATE], 10.0, base)
        run_step(args, store, steps, "mdm3-state-after-companion", ["cat", MDM3_STATE], 10.0, base)
        run_step(args, store, steps, "rpmsg-after-companion", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0, base)
        run_step(args, store, steps, "proc-net-qrtr-after-companion", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0, base)
        run_step(args, store, steps, "proc-net-dev-after-companion", ["cat", "/proc/net/dev"], 10.0, base)
        run_step(args, store, steps, "ps-before-reboot", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0, base)
        after = run_step(args, store, steps, "dmesg-after-companion", ["run", args.toybox, "dmesg"], 60.0, base)
        delta = dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
        write_capture(store, "dmesg-delta", delta)
        markers = marker_summary(delta)
    finally:
        reboot = reboot_and_wait(args, store)

    mounted = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    helper = helper_surface(str((helper_item or {}).get("payload") or ""))
    return {
        "base": base,
        "node": node,
        "mount_results": mount_results,
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": {
            path: path_exists(step_payload(steps, f"mounted-stat-{safe_name(path)}"))
            for path in GLOBAL_MODEM_BLOB_PATHS
        },
        "wlan_firmware_visible": {
            path: path_exists(step_payload(steps, f"mounted-stat-{safe_name(path)}"))
            for path in WLAN_FIRMWARE_PATHS
        },
        "holder_opened": "v731.holder.status=opened" in step_payload(steps, "start-modem-holder"),
        "mss_before": step_payload(steps, "mss-state-before").strip(),
        "mss_after_holder": step_payload(steps, "mss-state-after-holder").strip(),
        "mss_after_companion": step_payload(steps, "mss-state-after-companion").strip(),
        "mdm3_before": step_payload(steps, "mdm3-state-before").strip(),
        "mdm3_after_holder": step_payload(steps, "mdm3-state-after-holder").strip(),
        "mdm3_after_companion": step_payload(steps, "mdm3-state-after-companion").strip(),
        "mss_crash_before": step_payload(steps, "mss-crash-before").strip(),
        "mss_crash_after_holder": step_payload(steps, "mss-crash-after-holder").strip(),
        "mdm3_crash_before": step_payload(steps, "mdm3-crash-before").strip(),
        "mdm3_crash_after_holder": step_payload(steps, "mdm3-crash-after-holder").strip(),
        "qrtr_rx_wait": qrtr_wait,
        "companion_executed": bool(qrtr_wait.get("seen")),
        "helper_result": helper,
        "helper_ok": bool((helper_item or {}).get("ok")),
        "helper_status": (helper_item or {}).get("status"),
        "qrtr_services_after_companion": qrtr_service_counts(step_payload(steps, "proc-net-qrtr-after-companion")),
        "rpmsg_after_companion": step_payload(steps, "rpmsg-after-companion"),
        "proc_net_dev_after_companion_file": "native/proc-net-dev-after-companion.txt",
        "markers": markers if "markers" in locals() else {},
        "reboot_cleanup": reboot,
    }


def build_checks(args: argparse.Namespace,
                 steps: list[dict[str, Any]],
                 preflight: dict[str, Any],
                 v731: dict[str, Any],
                 v732: dict[str, Any],
                 v490: dict[str, Any],
                 live: dict[str, Any] | None,
                 blockers: list[str]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command executed",
            "next_step": "refresh V401/V490 current boot, then run V733 lower companion observer",
        }]
    checks: list[dict[str, Any]] = [
        {
            "name": "preflight-blockers",
            "status": "pass" if not blockers else "blocked",
            "detail": {"blockers": blockers},
            "next_step": "clear blockers before V733 live",
        },
        {
            "name": "references",
            "status": "pass" if v731.get("decision") == "v731-firmware-mounted-modem-holder-qrtr-rx-pass" and v732.get("decision") == "v732-cnss2-mhi-holder-window-cnss2-gap-classified" and v490.get("decision") == "v490-selinux-policy-load-proof-pass" else "review",
            "detail": {"v731": v731.get("decision"), "v732": v732.get("decision"), "v490": v490.get("decision")},
            "next_step": "refresh stale prerequisite evidence before interpreting V733",
        },
    ]
    if not live:
        return checks
    counts = ((live.get("markers") or {}).get("counts") or {})
    helper = live.get("helper_result") or {}
    reboot = live.get("reboot_cleanup") or {}
    forbidden_helper_values = {
        key: helper.get(key)
        for key in ("cnss_daemon", "service_manager", "wifi_hal", "wificond", "scan_connect_linkup", "external_ping", "qmi_attempted")
    }
    checks.extend([
        {
            "name": "firmware-mounted",
            "status": "pass" if all((live.get("mounted_hits") or {}).get(target) for target in mountv.PARTITION_TARGETS.values()) and any((live.get("modem_blob_visible") or {}).values()) else "blocked",
            "detail": {"mounted_hits": live.get("mounted_hits"), "modem_blob_visible": live.get("modem_blob_visible")},
            "next_step": "fix firmware mount parity before retry",
        },
        {
            "name": "modem-holder-window",
            "status": "pass" if live.get("holder_opened") and "ONLINE" in {live.get("mss_after_holder"), live.get("mss_after_companion")} and (live.get("qrtr_rx_wait") or {}).get("seen") else "finding",
            "detail": {"holder_opened": live.get("holder_opened"), "mss": [live.get("mss_before"), live.get("mss_after_holder"), live.get("mss_after_companion")], "qrtr_rx": (live.get("qrtr_rx_wait") or {}).get("seen")},
            "next_step": "if missing, compare V731/V732 current deltas before companion retry",
        },
        {
            "name": "lower-companion-contract",
            "status": "pass" if helper.get("order") == EXPECTED_ORDER and helper.get("child_started") == 4 and helper.get("all_observable") == 1 and helper.get("all_postflight_safe") == 1 else "blocked",
            "detail": {"mode": helper.get("mode"), "order": helper.get("order"), "child_started": helper.get("child_started"), "all_observable": helper.get("all_observable"), "all_postflight_safe": helper.get("all_postflight_safe"), "result": helper.get("result")},
            "next_step": "inspect helper transcript before interpreting kernel markers",
        },
        {
            "name": "forbidden-helper-actions",
            "status": "pass" if all(int(value or 0) == 0 for value in forbidden_helper_values.values()) else "blocked",
            "detail": forbidden_helper_values,
            "next_step": "stop if helper crossed into CNSS/HAL/connect or QMI payload",
        },
        {
            "name": "readiness-progression",
            "status": "pass" if counts.get("qrtr_tx", 0) or counts.get("sysmon_qmi", 0) or counts.get("wlfw", 0) or counts.get("wlan0", 0) else "finding",
            "detail": {"markers": {key: counts.get(key, 0) for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "rpmsg", "service_notifier", "wlan_pd", "mhi", "qca6390", "wlfw", "bdf", "wlan0")}, "qrtr_services": live.get("qrtr_services_after_companion")},
            "next_step": "if only QRTR TX/sysmon advances, next blocker remains post-sysmon publication",
        },
        {
            "name": "kernel-warning-review",
            "status": "blocked" if counts.get("kernel_warning", 0) else "pass",
            "detail": {"kernel_warning": counts.get("kernel_warning", 0), "first": ((live.get("markers") or {}).get("first_lines") or {}).get("kernel_warning", "")},
            "next_step": "do not repeat or widen if warning appears",
        },
        {
            "name": "postflight-reboot-cleanup",
            "status": "pass" if reboot.get("version_seen") and reboot.get("status_healthy") else "blocked",
            "detail": reboot,
            "next_step": "manually verify native if cleanup did not prove health",
        },
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v733-holder-lower-companion-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current V401/V490 and run V733 live observer",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v733-holder-lower-companion-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear blocker before retry",
        )
    if not live:
        return (
            "v733-holder-lower-companion-preflight-ready",
            True,
            "preflight ready",
            "run live V733 observer",
        )
    counts = ((live.get("markers") or {}).get("counts") or {})
    services = live.get("qrtr_services_after_companion") or {}
    if counts.get("wlan0", 0) or counts.get("wlfw", 0) or services.get("69", 0):
        return (
            "v733-holder-lower-companion-wlfw-advance",
            True,
            "lower companion window produced WLFW/service69 or wlan0 evidence without CNSS/HAL/scan/connect",
            "capture BDF/fw-ready before Wi-Fi HAL",
        )
    if counts.get("mhi", 0) or counts.get("qca6390", 0):
        return (
            "v733-holder-lower-companion-mhi-advance",
            True,
            "lower companion window produced MHI/QCA6390 evidence but no WLFW/service69",
            "classify MHI-to-WLFW firmware/runtime gap",
        )
    if counts.get("qrtr_tx", 0) or counts.get("sysmon_qmi", 0):
        return (
            "v733-holder-lower-companion-sysmon-advance",
            True,
            "lower companion restored QRTR TX/sysmon but service-notifier/WLFW/service69 remained absent",
            "next gate should compare post-sysmon publication prerequisites; still below CNSS/HAL/connect",
        )
    if (live.get("qrtr_rx_wait") or {}).get("seen"):
        return (
            "v733-holder-lower-companion-no-post-rx-advance",
            True,
            "modem QRTR RX returned but lower companion did not produce QRTR TX/sysmon or WLFW",
            "compare helper output and V609/V724 order before retrying",
        )
    return (
        "v733-holder-lower-companion-no-modem-readiness",
        True,
        "holder did not reproduce QRTR RX in this run",
        "compare with V731/V732 before widening live work",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    helper = live.get("helper_result") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    state_rows = [
        ["mounted_hits", json.dumps(live.get("mounted_hits", {}), sort_keys=True)],
        ["modem_blob_visible", json.dumps(live.get("modem_blob_visible", {}), sort_keys=True)],
        ["wlan_firmware_visible", json.dumps({path: value for path, value in (live.get("wlan_firmware_visible") or {}).items() if value}, sort_keys=True)],
        ["holder_opened", live.get("holder_opened", "")],
        ["mss", f"{live.get('mss_before', '')}->{live.get('mss_after_holder', '')}->{live.get('mss_after_companion', '')}"],
        ["mdm3", f"{live.get('mdm3_before', '')}->{live.get('mdm3_after_holder', '')}->{live.get('mdm3_after_companion', '')}"],
        ["helper", json.dumps({key: helper.get(key) for key in ('mode', 'order', 'child_started', 'all_observable', 'all_postflight_safe', 'result', 'qmi_attempted')}, sort_keys=True)],
        ["qrtr_services", json.dumps(live.get("qrtr_services_after_companion", {}), sort_keys=True)],
        ["reboot_cleanup", json.dumps(live.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    marker_rows = [[name, str(counts.get(name, 0))] for name in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "rpmsg", "service_notifier", "wlan_pd", "mhi", "qca6390", "wlfw", "bdf", "wlan0", "kernel_warning")]
    return "\n".join([
        "# V733 Holder Lower Companion Observer",
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
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
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
    v732 = load_json_if_exists(args.v732_manifest)
    v490 = load_json_if_exists(args.v490_manifest)
    preflight: dict[str, Any] = {}
    live: dict[str, Any] | None = None
    blockers: list[str] = []
    if args.command == "run":
        preflight = capture_preflight(args, store, steps)
        blockers = preflight_blockers(args, steps, preflight, v731, v732, v490)
        if not blockers:
            live = run_live(args, store, steps, preflight)
    checks = build_checks(args, steps, preflight, v731, v732, v490, live, blockers)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v733",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "v731": {"decision": v731.get("decision"), "pass": v731.get("pass"), "path": v731.get("path", str(repo_path(args.v731_manifest)))},
        "v732": {"decision": v732.get("decision"), "pass": v732.get("pass"), "path": v732.get("path", str(repo_path(args.v732_manifest)))},
        "v490": {"decision": v490.get("decision"), "pass": v490.get("pass"), "path": v490.get("path", str(repo_path(args.v490_manifest)))},
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
        "lower_companion_start_executed": bool((live or {}).get("companion_executed")),
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
    latest = repo_path("tmp/wifi/latest-v733-holder-lower-companion.txt")
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
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
