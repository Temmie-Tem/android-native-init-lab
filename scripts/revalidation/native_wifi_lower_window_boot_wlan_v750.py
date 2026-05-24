#!/usr/bin/env python3
"""V750 bounded lower-window boot_wlan proof.

This runner combines the proven firmware-mounted modem holder/lower companion
window with exactly one bounded `boot_wlan` trigger observation:

    firmware ro mounts -> subsys_modem holder -> QRTR RX wait
      -> qrtr-ns/rmt_storage/tftp_server/pd-mapper start-only
      -> /cache/bin/a90_wlanbootctl boot-observe <seconds>

It does not start service-manager, Wi-Fi HAL, wificond, supplicant, hostapd,
scan/connect, credential use, DHCP/routes, external ping, bind/unbind,
driver_override, module load/unload, esoc0, or qcwlanstate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
import native_wifi_holder_lower_companion_v733 as base
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v750-lower-window-boot-wlan")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v124"
DEFAULT_WLANBOOTCTL = "/cache/bin/a90_wlanbootctl"
DEFAULT_WLANBOOTCTL_SHA256 = "5f66cc97afb92ce6af45c2584d7fa04e0d0aa23f0442b54a047fb710ed5648c0"
DEFAULT_WLANBOOTCTL_MARKER = "a90_wlanbootctl v2"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_HOLD_SEC = 150
DEFAULT_COMPANION_RUNTIME_SEC = 12
DEFAULT_BOOT_OBSERVE_SEC = 25
DEFAULT_V731_MANIFEST = Path("tmp/wifi/v731-firmware-mounted-modem-holder/manifest.json")
DEFAULT_V732_MANIFEST = Path("tmp/wifi/v732-cnss2-mhi-holder-window/manifest.json")
DEFAULT_V490_MANIFEST = Path("tmp/wifi/v733-v490-current-run/manifest.json")
PROOF_PREFIX = "/tmp/a90-v750-"
MODE = base.MODE
EXPECTED_ORDER = base.EXPECTED_ORDER

POST_BOOT_PATHS = (
    "/proc/net/dev",
    "/proc/net/qrtr",
    "/sys/class/net",
    "/sys/class/ieee80211",
    "/sys/bus/rpmsg/devices",
    "/sys/bus/mhi/devices",
    "/sys/bus/pci/devices",
    "/sys/kernel/boot_wlan",
    "/sys/wifi",
)

FORBIDDEN_TERMS = (
    "subsys_esoc0",
    "/sys/class/subsys/subsys_esoc0",
    "/dev/subsys_esoc0",
    "echo online",
    "driver_override",
    "/bind",
    "/unbind",
    "insmod",
    "rmmod",
    "modprobe",
    "qcwlanstate on",
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

EXTRA_MARKERS: dict[str, re.Pattern[str]] = {
    "boot_wlan": re.compile(r"boot_wlan|Wifi Turning On", re.I),
    "qcwlanstate": re.compile(r"qcwlanstate|Modules not initialized", re.I),
    "wiphy": re.compile(r"ieee80211|wiphy|cfg80211", re.I),
    "dev_wlan": re.compile(r"/dev/wlan|qcwlanstate", re.I),
}


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
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--wlanbootctl", default=DEFAULT_WLANBOOTCTL)
    parser.add_argument("--wlanbootctl-sha256", default=DEFAULT_WLANBOOTCTL_SHA256)
    parser.add_argument("--wlanbootctl-marker", default=DEFAULT_WLANBOOTCTL_MARKER)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--boot-observe-sec", type=int, default=DEFAULT_BOOT_OBSERVE_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=base.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=base.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=DEFAULT_V732_MANIFEST)
    parser.add_argument("--v490-manifest", type=Path, default=DEFAULT_V490_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("--allow-lower-window-boot-wlan", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return base.safe_name(value)


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return safe_name(args.proof_id)
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    return base.step_payload(steps, name)


def validate_device_command(args: argparse.Namespace, command: list[str], proof_base: str | None = None) -> None:
    joined = " ".join(command)
    lowered = joined.lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in lowered:
            raise RuntimeError(f"forbidden V750 command term {term!r}: {joined}")
    if command == ["run", args.wlanbootctl]:
        return
    if command[:2] == ["run", args.wlanbootctl] and len(command) >= 3:
        if command[2] in {"status", "observe"}:
            return
        if command[2] == "boot-observe" and len(command) == 4:
            seconds = int(command[3])
            if 5 <= seconds <= 60:
                return
    try:
        base.validate_device_command(args, command, proof_base)
    except RuntimeError as exc:
        raise RuntimeError(f"unexpected V750 command: {joined}") from exc


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


def capture_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    preflight = base.capture_preflight(args, store, steps)
    run_step(args, store, steps, "wlanbootctl-sha", ["run", args.toybox, "sha256sum", args.wlanbootctl], 15.0)
    run_step(args, store, steps, "wlanbootctl-usage", ["run", args.wlanbootctl], 20.0)
    run_step(args, store, steps, "wlanbootctl-status", ["run", args.wlanbootctl, "status"], 25.0)
    return preflight


def helper_command(args: argparse.Namespace) -> list[str]:
    return base.helper_command(args)


def helper_surface(text: str) -> dict[str, Any]:
    return base.helper_surface(text)


def extended_marker_summary(text: str) -> dict[str, Any]:
    summary = base.marker_summary(text)
    counts = dict(summary.get("counts") or {})
    first_lines = dict(summary.get("first_lines") or {})
    focus_tail = list(summary.get("focus_tail") or [])
    for name, pattern in EXTRA_MARKERS.items():
        matches = [line.strip()[:360] for line in text.splitlines() if pattern.search(line)]
        counts[name] = len(matches)
        if matches:
            first_lines[name] = matches[0]
            focus_tail.extend(matches[-20:])
    summary["counts"] = counts
    summary["first_lines"] = first_lines
    summary["focus_tail"] = focus_tail[-260:]
    return summary


def read_path_capture(args: argparse.Namespace,
                      store: EvidenceStore,
                      steps: list[dict[str, Any]],
                      path: str,
                      proof_base: str) -> None:
    if path in {"/proc/net/dev", "/proc/net/qrtr"}:
        run_step(args, store, steps, f"post-boot-cat-{safe_name(path)}", ["cat", path], 10.0, proof_base)
    else:
        run_step(args, store, steps, f"post-boot-ls-{safe_name(path)}", ["run", args.toybox, "ls", "-la", path], 15.0, proof_base)


def wlanboot_ready(args: argparse.Namespace, steps: list[dict[str, Any]]) -> bool:
    sha = step_payload(steps, "wlanbootctl-sha")
    usage = step_payload(steps, "wlanbootctl-usage")
    status = step_payload(steps, "wlanbootctl-status")
    return (
        args.wlanbootctl_sha256 in sha
        and args.wlanbootctl_marker in usage
        and "boot-observe" in usage
        and "wlanboot.status.boot_wlan.exists=1" in status
    )


def active_process_hits(ps_text: str) -> list[str]:
    hits = base.active_process_hits(ps_text)
    hits.extend(line.strip() for line in ps_text.splitlines() if "a90-v750-" in line)
    return hits


def preflight_blockers(args: argparse.Namespace,
                       steps: list[dict[str, Any]],
                       preflight: dict[str, Any],
                       v731: dict[str, Any],
                       v732: dict[str, Any],
                       v490: dict[str, Any]) -> list[str]:
    blockers = base.preflight_blockers(args, steps, preflight, v731, v732, v490)
    blockers = ["helper-current-not-ready" if item == "helper-v121-not-ready" else item for item in blockers]
    if not wlanboot_ready(args, steps):
        blockers.append("wlanbootctl-v2-not-ready")
    if "wlanboot.status.qcwlanstate.exists=1" not in step_payload(steps, "wlanbootctl-status"):
        blockers.append("qcwlanstate-surface-missing")
    if active_process_hits(step_payload(steps, "ps-before")):
        if "residual-target-process" not in blockers:
            blockers.append("residual-target-process")
    if args.command == "run" and not (args.allow_lower_window_boot_wlan and args.assume_yes):
        blockers.append("live-boot-wlan-not-approved")
    if not (5 <= args.boot_observe_sec <= 60):
        blockers.append("boot-observe-window-out-of-range")
    return sorted(set(blockers))


def run_live(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             preflight: dict[str, Any]) -> dict[str, Any]:
    label = proof_id(args)
    proof_base = PROOF_PREFIX + label
    node = f"{proof_base}/subsys_modem"
    status_file = f"{proof_base}/holder.status"
    pid_file = f"{proof_base}/holder.pid"
    before = run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    mount_results: list[str] = []
    helper_item: dict[str, Any] | None = None
    boot_item: dict[str, Any] | None = None
    qrtr_wait: dict[str, Any] = {}
    reboot: dict[str, Any] = {}
    try:
        for name, command, timeout in mountv.build_mount_commands(preflight, proof_base):
            item = run_step(args, store, steps, f"v750-{name}", command, timeout, proof_base)
            mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0, proof_base)
        run_step(args, store, steps, "mounted-firmware-class-path", ["cat", base.FIRMWARE_CLASS_PATH], 10.0, proof_base)
        for path in base.GLOBAL_MODEM_BLOB_PATHS + base.WLAN_FIRMWARE_PATHS:
            run_step(args, store, steps, f"mounted-stat-{safe_name(path)}", ["stat", path], 10.0, proof_base)

        dev = base.parse_dev(step_payload(steps, "subsys-modem-dev"))
        if not dev:
            raise RuntimeError("subsys_modem dev missing after preflight")
        holder = base.holder_script(args, node, status_file, pid_file, dev[0], dev[1])
        write_capture(store, "holder-script-redacted", holder.replace(node, "$PROOF/subsys_modem").replace(proof_base, "$PROOF"))
        run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", holder], 25.0, proof_base)
        run_step(args, store, steps, "mss-state-after-holder", ["cat", base.MSS_STATE], 10.0, proof_base)
        run_step(args, store, steps, "mss-crash-after-holder", ["cat", base.MSS_CRASH_COUNT], 10.0, proof_base)
        run_step(args, store, steps, "mdm3-state-after-holder", ["cat", base.MDM3_STATE], 10.0, proof_base)
        run_step(args, store, steps, "mdm3-crash-after-holder", ["cat", base.MDM3_CRASH_COUNT], 10.0, proof_base)
        qrtr_wait = base.wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""), proof_base)
        if qrtr_wait.get("seen"):
            helper_item = run_step(args, store, steps, "lower-companion-start-only", helper_command(args), args.companion_runtime_sec + 75.0, proof_base)
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
        run_step(args, store, steps, "wlanbootctl-status-before-boot", ["run", args.wlanbootctl, "status"], 25.0, proof_base)
        boot_item = run_step(
            args,
            store,
            steps,
            "boot-wlan-observe",
            ["run", args.wlanbootctl, "boot-observe", str(args.boot_observe_sec)],
            args.boot_observe_sec + 35.0,
            proof_base,
        )
        run_step(args, store, steps, "wlanbootctl-status-after-boot", ["run", args.wlanbootctl, "status"], 25.0, proof_base)
        run_step(args, store, steps, "mss-state-after-boot", ["cat", base.MSS_STATE], 10.0, proof_base)
        run_step(args, store, steps, "mdm3-state-after-boot", ["cat", base.MDM3_STATE], 10.0, proof_base)
        for path in POST_BOOT_PATHS:
            read_path_capture(args, store, steps, path, proof_base)
        run_step(args, store, steps, "ps-before-reboot", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0, proof_base)
        after = run_step(args, store, steps, "dmesg-after-boot", ["run", args.toybox, "dmesg"], 60.0, proof_base)
        delta = base.dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
        write_capture(store, "dmesg-delta", delta)
        markers = extended_marker_summary(delta)
    finally:
        reboot = base.reboot_and_wait(args, store)

    mounted = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    helper = helper_surface(str((helper_item or {}).get("payload") or ""))
    boot_payload = str((boot_item or {}).get("payload") or "")
    after_status = step_payload(steps, "wlanbootctl-status-after-boot")
    proc_net_dev = step_payload(steps, "post-boot-cat-proc-net-dev")
    ieee80211 = step_payload(steps, "post-boot-ls-sys-class-ieee80211")
    sys_class_net = step_payload(steps, "post-boot-ls-sys-class-net")
    return {
        "base": proof_base,
        "node": node,
        "mount_results": mount_results,
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": {
            path: base.path_exists(step_payload(steps, f"mounted-stat-{safe_name(path)}"))
            for path in base.GLOBAL_MODEM_BLOB_PATHS
        },
        "wlan_firmware_visible": {
            path: base.path_exists(step_payload(steps, f"mounted-stat-{safe_name(path)}"))
            for path in base.WLAN_FIRMWARE_PATHS
        },
        "holder_opened": "v731.holder.status=opened" in step_payload(steps, "start-modem-holder"),
        "mss_before": step_payload(steps, "mss-state-before").strip(),
        "mss_after_holder": step_payload(steps, "mss-state-after-holder").strip(),
        "mss_after_boot": step_payload(steps, "mss-state-after-boot").strip(),
        "mdm3_before": step_payload(steps, "mdm3-state-before").strip(),
        "mdm3_after_holder": step_payload(steps, "mdm3-state-after-holder").strip(),
        "mdm3_after_boot": step_payload(steps, "mdm3-state-after-boot").strip(),
        "mss_crash_before": step_payload(steps, "mss-crash-before").strip(),
        "mss_crash_after_holder": step_payload(steps, "mss-crash-after-holder").strip(),
        "mdm3_crash_before": step_payload(steps, "mdm3-crash-before").strip(),
        "mdm3_crash_after_holder": step_payload(steps, "mdm3-crash-after-holder").strip(),
        "qrtr_rx_wait": qrtr_wait,
        "companion_executed": bool(qrtr_wait.get("seen")),
        "helper_result": helper,
        "helper_ok": bool((helper_item or {}).get("ok")),
        "helper_status": (helper_item or {}).get("status"),
        "boot_wlan_write_executed": bool(boot_item),
        "boot_wlan_ok": bool((boot_item or {}).get("ok")),
        "boot_wlan_status": (boot_item or {}).get("status"),
        "boot_wlan_payload_file": (boot_item or {}).get("file"),
        "boot_wlan_payload_tail": "\n".join(boot_payload.splitlines()[-60:]),
        "qcwlanstate_after": "wlanboot.status.qcwlanstate.value=ON" in after_status,
        "dev_wlan_after": "wlanboot.status.dev_wlan.exists=1" in after_status,
        "wlan0_after": "wlan0" in proc_net_dev or "wlan0" in sys_class_net,
        "wiphy_after": "phy" in ieee80211 or "wlan" in ieee80211.lower(),
        "qrtr_services_after_boot": base.qrtr_service_counts(step_payload(steps, "post-boot-cat-proc-net-qrtr")),
        "post_boot_files": {
            "proc_net_dev": "native/post-boot-cat-proc-net-dev.txt",
            "proc_net_qrtr": "native/post-boot-cat-proc-net-qrtr.txt",
            "sys_class_net": "native/post-boot-ls-sys-class-net.txt",
            "sys_class_ieee80211": "native/post-boot-ls-sys-class-ieee80211.txt",
        },
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
            "next_step": "run preflight; live run requires --allow-lower-window-boot-wlan --assume-yes",
        }]
    checks = base.build_checks(args, steps, preflight, v731, v732, v490, None, blockers)
    checks.append({
        "name": "wlanbootctl-contract",
        "status": "pass" if wlanboot_ready(args, steps) else "blocked",
        "detail": {"sha": args.wlanbootctl_sha256, "marker": args.wlanbootctl_marker},
        "next_step": "deploy the expected a90_wlanbootctl before V750 live",
    })
    if args.command == "run":
        checks.append({
            "name": "live-approval",
            "status": "pass" if args.allow_lower_window_boot_wlan and args.assume_yes else "blocked",
            "detail": {"allow_lower_window_boot_wlan": args.allow_lower_window_boot_wlan, "assume_yes": args.assume_yes},
            "next_step": "rerun with explicit V750 gate flags",
        })
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
            "status": "pass" if live.get("holder_opened") and "ONLINE" in {live.get("mss_after_holder"), live.get("mss_after_boot")} and (live.get("qrtr_rx_wait") or {}).get("seen") else "finding",
            "detail": {"holder_opened": live.get("holder_opened"), "mss": [live.get("mss_before"), live.get("mss_after_holder"), live.get("mss_after_boot")], "qrtr_rx": (live.get("qrtr_rx_wait") or {}).get("seen")},
            "next_step": "if missing, compare V731/V733 current deltas before boot_wlan retry",
        },
        {
            "name": "lower-companion-contract",
            "status": "pass" if helper.get("order") == EXPECTED_ORDER and helper.get("child_started") == 4 and helper.get("all_observable") == 1 and helper.get("all_postflight_safe") == 1 else "blocked",
            "detail": {"mode": helper.get("mode"), "order": helper.get("order"), "child_started": helper.get("child_started"), "all_observable": helper.get("all_observable"), "all_postflight_safe": helper.get("all_postflight_safe"), "result": helper.get("result")},
            "next_step": "inspect helper transcript before interpreting boot_wlan result",
        },
        {
            "name": "forbidden-helper-actions",
            "status": "pass" if all(int(value or 0) == 0 for value in forbidden_helper_values.values()) else "blocked",
            "detail": forbidden_helper_values,
            "next_step": "stop if helper crossed into CNSS/HAL/connect or QMI payload",
        },
        {
            "name": "boot-wlan-observe",
            "status": "pass" if live.get("boot_wlan_write_executed") and live.get("boot_wlan_ok") else "blocked",
            "detail": {"executed": live.get("boot_wlan_write_executed"), "status": live.get("boot_wlan_status"), "tail": live.get("boot_wlan_payload_tail", "")[-800:]},
            "next_step": "if write failed, inspect fixed-control helper transcript",
        },
        {
            "name": "readiness-progression",
            "status": "pass" if live.get("wlan0_after") or live.get("wiphy_after") or counts.get("wlfw", 0) or counts.get("bdf", 0) or (live.get("qrtr_services_after_boot") or {}).get("69", 0) else "finding",
            "detail": {"markers": {key: counts.get(key, 0) for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "rpmsg", "service_notifier", "wlan_pd", "mhi", "qca6390", "wlfw", "bdf", "wlan0", "boot_wlan", "qcwlanstate", "wiphy")}, "qrtr_services": live.get("qrtr_services_after_boot"), "wlan0_after": live.get("wlan0_after"), "wiphy_after": live.get("wiphy_after")},
            "next_step": "if no progression, standalone boot_wlan remains eliminated even inside lower window",
        },
        {
            "name": "kernel-warning-review",
            "status": "blocked" if counts.get("kernel_warning", 0) else "pass",
            "detail": {"kernel_warning": counts.get("kernel_warning", 0), "first": ((live.get("markers") or {}).get("first_lines") or {}).get("kernel_warning", "")},
            "next_step": "do not widen if warning appears",
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
            "v750-lower-window-boot-wlan-plan-ready",
            True,
            "plan-only; no device command executed",
            "run preflight, then gated live proof",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v750-lower-window-boot-wlan-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear blocker before retry",
        )
    if not live:
        return (
            "v750-lower-window-boot-wlan-preflight-ready",
            True,
            "preflight ready; live proof remains below HAL/connect",
            "run with --allow-lower-window-boot-wlan --assume-yes",
        )
    counts = ((live.get("markers") or {}).get("counts") or {})
    services = live.get("qrtr_services_after_boot") or {}
    if live.get("wlan0_after") or live.get("wiphy_after"):
        return (
            "v750-lower-window-boot-wlan-netdev-appeared",
            True,
            "bounded lower-window boot_wlan produced wlan0/wiphy evidence without HAL, scan/connect, credentials, DHCP, routes, or external ping",
            "plan link-readiness/scan-only gate before credential use",
        )
    if counts.get("wlfw", 0) or counts.get("bdf", 0) or services.get("69", 0):
        return (
            "v750-lower-window-boot-wlan-wlfw-advanced",
            True,
            "bounded lower-window boot_wlan advanced WLFW/BDF/service69 but no wlan0",
            "classify fw-ready-to-netdev gap before HAL/connect",
        )
    if live.get("dev_wlan_after") or counts.get("boot_wlan", 0) or counts.get("qcwlanstate", 0):
        return (
            "v750-lower-window-boot-wlan-control-surface-only",
            True,
            "boot_wlan write executed in the lower-ready window but only control-surface/log movement was observed",
            "route next work toward QCA/WLFW trigger gap, not standalone boot_wlan repetition",
        )
    return (
        "v750-lower-window-boot-wlan-no-lower-progress",
        True,
        "boot_wlan write executed in lower window but no WLFW/BDF/wlan0 progression was observed",
        "select the next non-bind QCA/WLFW trigger candidate",
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
        ["mss", f"{live.get('mss_before', '')}->{live.get('mss_after_holder', '')}->{live.get('mss_after_boot', '')}"],
        ["mdm3", f"{live.get('mdm3_before', '')}->{live.get('mdm3_after_holder', '')}->{live.get('mdm3_after_boot', '')}"],
        ["helper", json.dumps({key: helper.get(key) for key in ('mode', 'order', 'child_started', 'all_observable', 'all_postflight_safe', 'result', 'qmi_attempted')}, sort_keys=True)],
        ["boot_wlan", json.dumps({key: live.get(key) for key in ('boot_wlan_write_executed', 'boot_wlan_ok', 'boot_wlan_status', 'dev_wlan_after', 'wlan0_after', 'wiphy_after')}, sort_keys=True)],
        ["qrtr_services", json.dumps(live.get("qrtr_services_after_boot", {}), sort_keys=True)],
        ["reboot_cleanup", json.dumps(live.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    marker_names = ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "rpmsg", "service_notifier", "wlan_pd", "mhi", "qca6390", "wlfw", "bdf", "wlan0", "boot_wlan", "qcwlanstate", "wiphy", "kernel_warning")
    marker_rows = [[name, str(counts.get(name, 0))] for name in marker_names]
    return "\n".join([
        "# V750 Lower-window Boot WLAN Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- subsys_modem_open_attempted: `{manifest['subsys_modem_open_attempted']}`",
        f"- lower_companion_start_executed: `{manifest['lower_companion_start_executed']}`",
        f"- boot_wlan_write_executed: `{manifest['boot_wlan_write_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- credential_use_executed: `{manifest['credential_use_executed']}`",
        f"- dhcp_route_executed: `{manifest['dhcp_route_executed']}`",
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
    v731 = base.load_json_if_exists(args.v731_manifest)
    v732 = base.load_json_if_exists(args.v732_manifest)
    v490 = base.load_json_if_exists(args.v490_manifest)
    preflight: dict[str, Any] = {}
    live: dict[str, Any] | None = None
    blockers: list[str] = []
    if args.command != "plan":
        preflight = capture_preflight(args, store, steps)
        blockers = preflight_blockers(args, steps, preflight, v731, v732, v490)
        if args.command == "run" and not blockers:
            live = run_live(args, store, steps, preflight)
    checks = build_checks(args, steps, preflight, v731, v732, v490, live, blockers)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v750",
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
        "device_commands_executed": args.command != "plan",
        "device_mutations": bool(live),
        "firmware_mounts_executed": bool(live),
        "subsys_modem_open_attempted": bool(live),
        "subsys_modem_opened": bool((live or {}).get("holder_opened")),
        "esoc0_node_created": False,
        "esoc0_open_executed": False,
        "subsystem_state_writes_executed": False,
        "module_load_unload_executed": False,
        "bind_unbind_executed": False,
        "driver_override_executed": False,
        "qcwlanstate_write_executed": False,
        "lower_companion_start_executed": bool((live or {}).get("companion_executed")),
        "boot_wlan_write_executed": bool((live or {}).get("boot_wlan_write_executed")),
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
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v750-lower-window-boot-wlan.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"subsys_modem_open_attempted: {manifest['subsys_modem_open_attempted']}")
    print(f"subsys_modem_opened: {manifest['subsys_modem_opened']}")
    print(f"lower_companion_start_executed: {manifest['lower_companion_start_executed']}")
    print(f"boot_wlan_write_executed: {manifest['boot_wlan_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"dhcp_route_executed: {manifest['dhcp_route_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
