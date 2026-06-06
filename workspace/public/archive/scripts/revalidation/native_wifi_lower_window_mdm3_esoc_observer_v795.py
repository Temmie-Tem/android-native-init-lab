#!/usr/bin/env python3
"""V795 lower-window mdm3/esoc observer.

V794 showed the idle native surface has modem/esoc0 OFFLINING while ICNSS is
bound.  V795 opens only the proven firmware-backed subsys_modem holder window,
then reads mdm3/esoc/ICNSS/WLFW surfaces.  It intentionally does not start lower
companions, CNSS, service-manager, Wi-Fi HAL, boot_wlan, qcwlanstate, scan,
connect, DHCP, routes, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
import native_wifi_holder_lower_companion_v733 as v733
import native_wifi_mdm3_icnss_surface_observer_v794 as v794
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90ctl import bridge_exchange
from a90harness.evidence import EvidenceStore, write_private_text
from native_wifi_firmware_mounted_modem_holder_v731 import (
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v795-lower-window-mdm3-esoc-observer")
LATEST_POINTER = Path("tmp/wifi/latest-v795-lower-window-mdm3-esoc-observer.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_V794_MANIFEST = Path("tmp/wifi/v794-mdm3-icnss-surface-observer/manifest.json")
PROOF_PREFIX = "/tmp/a90-v795-"
FORBIDDEN_ACTIONS = (
    "lower companion start",
    "cnss_diag/cnss-daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "boot_wlan/qcwlanstate write",
    "scan/connect/link-up",
    "Wi-Fi credential use",
    "DHCP/routing/external ping",
    "esoc0 open/hold",
    "module load/unload or bind/unbind",
    "boot image or partition write",
    "custom kernel flash",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


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
    parser.add_argument("--hold-sec", type=int, default=90)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=25.0)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=2.0)
    parser.add_argument("--v794-manifest", type=Path, default=DEFAULT_V794_MANIFEST)
    parser.add_argument("--v793-manifest", type=Path, default=v794.DEFAULT_V793_MANIFEST)
    parser.add_argument("--allow-firmware-mounts", action="store_true")
    parser.add_argument("--allow-subsys-modem-holder", action="store_true")
    parser.add_argument("--allow-cleanup-reboot", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def send_hide(args: argparse.Namespace) -> None:
    bridge_exchange(args.host, args.port, "hide", min(args.timeout, 8.0), markers=(b"[busy]", b"[done]", b"[err]"))


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def validate_command(args: argparse.Namespace, command: list[str], proof_base: str | None = None) -> None:
    joined = " ".join(command).lower()
    forbidden = (
        "qcwlanstate on",
        "boot_wlan 1",
        "cnss-daemon",
        "cnss_diag",
        "qrtr-ns",
        "rmt_storage",
        "tftp_server",
        "pd-mapper",
        "servicemanager",
        "android.hardware.wifi",
        "wpa_supplicant",
        "dhcp",
        " ping ",
        "echo online",
        "insmod",
        "rmmod",
        "driver_override",
        "bind",
        "unbind",
        "subsys_esoc0",
    )
    for term in forbidden:
        if term in joined:
            raise RuntimeError(f"forbidden V795 command term {term!r}: {' '.join(command)}")
    if proof_base and ("/tmp/a90-v795-" in joined or command[:1] in [["mkdir"], ["mknodb"], ["stat"], ["umount"]]):
        return
    if command[:2] == ["run", args.busybox] and len(command) >= 4 and command[2] == "sh":
        return
    if command[:2] == ["run", args.toybox] and len(command) >= 3 and command[2] in {"dmesg", "ls", "cat", "ps", "mount", "rm"}:
        return
    if command[0] in {"version", "status", "selftest", "hide", "cat", "stat", "mkdir", "mknodb", "umount", "reboot", "mountsystem"}:
        return
    raise RuntimeError(f"unexpected V795 command: {' '.join(command)}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             proof_base: str | None = None) -> dict[str, Any]:
    validate_command(args, command, proof_base)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    if "[busy]" in text and args.hide_on_busy:
        send_hide(args)
        capture = run_capture(args, name, command, timeout=timeout or args.timeout)
        text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    text = v794.clean_text(text)
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


def required_flags(args: argparse.Namespace) -> list[str]:
    checks = {
        "--assume-yes": args.assume_yes,
        "--allow-firmware-mounts": args.allow_firmware_mounts,
        "--allow-subsys-modem-holder": args.allow_subsys_modem_holder,
        "--allow-cleanup-reboot": args.allow_cleanup_reboot,
    }
    return [flag for flag, present in checks.items() if not present]


def capture_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    run_step(args, store, steps, "hide-menu", ["hide"], 10.0)
    run_step(args, store, steps, "version", ["version"], 15.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "selftest", ["selftest"], 25.0)
    run_step(args, store, steps, "proc-filesystems", ["cat", "/proc/filesystems"], 20.0)
    run_step(args, store, steps, "pre-proc-mounts", ["cat", "/proc/mounts"], 20.0)
    run_step(args, store, steps, "proc-partitions", ["cat", "/proc/partitions"], 20.0)
    run_step(args, store, steps, "pre-ls-root", ["run", args.toybox, "ls", "-l", "/"], 20.0)
    run_step(args, store, steps, "pre-ls-vendor-links", ["run", args.toybox, "ls", "-ld", "/vendor", "/mnt/system/vendor", "/system/vendor"], 20.0)
    for target in mountv.TARGET_DIRS + ("/firmware", "/bt_firmware"):
        run_step(args, store, steps, f"pre-stat-{safe_name(target)}", ["stat", target], 10.0)
    partitions = mountv.parse_proc_partitions(step_payload(steps, "proc-partitions"))
    for devname in sorted(partitions):
        if not re.match(r"^(sd[a-z][0-9]+|mmcblk[0-9]+p[0-9]+)$", devname):
            continue
        run_step(args, store, steps, f"block-uevent-{safe_name(devname)}", ["cat", f"/sys/class/block/{devname}/uevent"], 8.0)
    preflight = mountv.summarize_preflight(steps)
    run_step(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], 30.0)
    run_step(args, store, steps, "proc-mounts", ["cat", "/proc/mounts"], 20.0)
    run_step(args, store, steps, "firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 10.0)
    run_step(args, store, steps, "subsys-modem-dev", ["cat", SUBSYS_MODEM_DEV], 10.0)
    run_step(args, store, steps, "mss-state-before", ["cat", MSS_STATE], 10.0)
    run_step(args, store, steps, "mss-crash-before", ["cat", MSS_CRASH_COUNT], 10.0)
    run_step(args, store, steps, "mdm3-state-before", ["cat", MDM3_STATE], 10.0)
    run_step(args, store, steps, "mdm3-crash-before", ["cat", MDM3_CRASH_COUNT], 10.0)
    run_step(args, store, steps, "ps-before", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    return preflight


def proof_label() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def wait_for_qrtr_rx(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], before: str, proof_base: str) -> dict[str, Any]:
    deadline = time.monotonic() + args.qrtr_rx_timeout_sec
    attempts = 0
    last_delta = ""
    seen = False
    while time.monotonic() < deadline:
        attempts += 1
        item = run_step(args, store, steps, f"wait-qrtr-rx-dmesg-{attempts:02d}", ["run", args.toybox, "dmesg"], 40.0, proof_base)
        last_delta = dmesg_delta(before, str(item.get("payload") or ""))
        if "qrtr: Modem QMI Readiness RX" in last_delta:
            seen = True
            break
        time.sleep(args.qrtr_rx_poll_sec)
    write_capture(store, "wait-qrtr-rx-delta", last_delta)
    return {"seen": seen, "attempts": attempts, "timeout_sec": args.qrtr_rx_timeout_sec, "file": "native/wait-qrtr-rx-delta.txt"}


def read_surface(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], proof_base: str) -> None:
    run_step(args, store, steps, "msm-subsys-after-holder", v794.shell_cmd(args, "BB=/cache/bin/busybox; for d in /sys/bus/msm_subsys/devices/*; do [ -e \"$d\" ] || continue; printf '== %s ==\\n' \"$d\"; \"$BB\" ls -ld \"$d\" 2>&1 || true; for f in name state crash_count restart_level; do printf '%s=' \"$f\"; \"$BB\" cat \"$d/$f\" 2>&1 || true; done; done"), 25.0, proof_base)
    run_step(args, store, steps, "esoc-after-holder", v794.shell_cmd(args, "BB=/cache/bin/busybox; for p in /sys/bus/esoc/devices /sys/bus/esoc/devices/* /sys/kernel/debug/esoc /sys/kernel/debug/esoc/*; do printf '== %s ==\\n' \"$p\"; \"$BB\" ls -ld \"$p\" 2>&1 || true; if [ -f \"$p\" ]; then \"$BB\" cat \"$p\" 2>&1 || true; fi; if [ -d \"$p\" ]; then \"$BB\" ls -la \"$p\" 2>&1 | \"$BB\" head -80; fi; done"), 20.0, proof_base)
    run_step(args, store, steps, "icnss-wlan-after-holder", v794.shell_cmd(args, "BB=/cache/bin/busybox; for p in /sys/bus/platform/devices/18800000.qcom,icnss /sys/bus/platform/devices/18800000.qcom,icnss/driver /sys/module/wlan /sys/module/wlan/parameters /sys/kernel/boot_wlan /sys/kernel/shutdown_wlan /dev/qcwlanstate /dev/wlan; do printf '== %s ==\\n' \"$p\"; \"$BB\" ls -ld \"$p\" 2>&1 || true; \"$BB\" readlink \"$p\" 2>/dev/null || true; if [ -d \"$p\" ]; then \"$BB\" ls -la \"$p\" 2>&1 | \"$BB\" head -100; fi; done"), 25.0, proof_base)
    run_step(args, store, steps, "proc-net-qrtr-after-holder", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0, proof_base)
    run_step(args, store, steps, "proc-net-dev-after-holder", ["cat", "/proc/net/dev"], 10.0, proof_base)
    run_step(args, store, steps, "dmesg-after-holder", ["run", args.toybox, "dmesg"], 60.0, proof_base)


def run_live(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    preflight = capture_preflight(args, store, steps)
    label = proof_label()
    base = PROOF_PREFIX + label
    node = f"{base}/subsys_modem"
    status_file = f"{base}/holder.status"
    pid_file = f"{base}/holder.pid"
    before = run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    reboot: dict[str, Any] = {}
    qrtr_wait: dict[str, Any] = {}
    try:
        for name, command, timeout in mountv.build_mount_commands(preflight, base):
            run_step(args, store, steps, f"v795-{name}", command, timeout, base)
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0, base)
        run_step(args, store, steps, "mounted-firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 10.0, base)
        for path in GLOBAL_MODEM_BLOB_PATHS + v733.WLAN_FIRMWARE_PATHS:
            run_step(args, store, steps, f"mounted-stat-{safe_name(path)}", ["stat", path], 10.0, base)
        dev = parse_dev(step_payload(steps, "subsys-modem-dev"))
        if not dev:
            raise RuntimeError("subsys_modem dev missing after preflight")
        script = holder_script(args, node, status_file, pid_file, dev[0], dev[1])
        write_capture(store, "holder-script-redacted", script.replace(node, "$PROOF/subsys_modem").replace(base, "$PROOF"))
        run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", script], 25.0, base)
        run_step(args, store, steps, "mss-state-after-holder", ["cat", MSS_STATE], 10.0, base)
        run_step(args, store, steps, "mss-crash-after-holder", ["cat", MSS_CRASH_COUNT], 10.0, base)
        run_step(args, store, steps, "mdm3-state-after-holder", ["cat", MDM3_STATE], 10.0, base)
        run_step(args, store, steps, "mdm3-crash-after-holder", ["cat", MDM3_CRASH_COUNT], 10.0, base)
        qrtr_wait = wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""), base)
        read_surface(args, store, steps, base)
        after = step_payload(steps, "dmesg-after-holder")
        delta = dmesg_delta(str(before.get("payload") or ""), after)
        write_capture(store, "dmesg-delta", delta)
        markers = marker_summary(delta)
    finally:
        reboot = reboot_and_wait(args, store)
    mounted = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    surface = v794.build_surface(args, [
        {"name": "msm-subsys", "payload": step_payload(steps, "msm-subsys-after-holder")},
        {"name": "esoc-surface", "payload": step_payload(steps, "esoc-after-holder")},
        {"name": "icnss-wlan-surface", "payload": step_payload(steps, "icnss-wlan-after-holder")},
        {"name": "icnss-wlan-values", "payload": ""},
        {"name": "binder-surface", "payload": ""},
        {"name": "proc-net-dev", "payload": step_payload(steps, "proc-net-dev-after-holder")},
        {"name": "proc-net-qrtr", "payload": step_payload(steps, "proc-net-qrtr-after-holder")},
        {"name": "proc-modules", "payload": ""},
        {"name": "dmesg-focus-tail", "payload": step_payload(steps, "dmesg-delta") or locals().get("delta", "")},
    ])
    live = {
        "base": base,
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": {path: path_exists(step_payload(steps, f"mounted-stat-{safe_name(path)}")) for path in GLOBAL_MODEM_BLOB_PATHS},
        "wlan_firmware_visible": {path: path_exists(step_payload(steps, f"mounted-stat-{safe_name(path)}")) for path in v733.WLAN_FIRMWARE_PATHS},
        "holder_opened": "v731.holder.status=opened" in step_payload(steps, "start-modem-holder"),
        "mss_before": step_payload(steps, "mss-state-before").strip(),
        "mss_after_holder": step_payload(steps, "mss-state-after-holder").strip(),
        "mdm3_before": step_payload(steps, "mdm3-state-before").strip(),
        "mdm3_after_holder": step_payload(steps, "mdm3-state-after-holder").strip(),
        "mss_crash_before": step_payload(steps, "mss-crash-before").strip(),
        "mss_crash_after_holder": step_payload(steps, "mss-crash-after-holder").strip(),
        "mdm3_crash_before": step_payload(steps, "mdm3-crash-before").strip(),
        "mdm3_crash_after_holder": step_payload(steps, "mdm3-crash-after-holder").strip(),
        "qrtr_rx_wait": qrtr_wait,
        "surface": surface,
        "qrtr_services_after_holder": v733.qrtr_service_counts(step_payload(steps, "proc-net-qrtr-after-holder")),
        "markers": markers if "markers" in locals() else {},
        "reboot_cleanup": reboot,
    }
    return steps, live


def build_checks(args: argparse.Namespace, flags_missing: list[str], v794_ref: dict[str, Any], live: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check("v794-reference", "pass" if v794_ref.get("decision") == "v794-idle-modem-esoc-offlining-icnss-bound-captured" and v794_ref.get("pass") is True else "blocked", "blocker", f"decision={v794_ref.get('decision')} pass={v794_ref.get('pass')}", "complete V794 before V795"))
    if args.command == "plan":
        checks.append(Check("plan-only", "pass", "info", "no device command executed", "run V795 with explicit lower-window flags"))
        return checks
    checks.append(Check("explicit-live-flags", "pass" if not flags_missing else "blocked", "blocker", "missing=" + ",".join(flags_missing), "pass all explicit V795 allow flags"))
    if not live:
        checks.append(Check("live-surface", "blocked", "blocker", "not collected", "inspect live failure"))
        return checks
    surface = live.get("surface") or {}
    markers = (live.get("markers") or {}).get("counts") or live.get("markers") or {}
    cleanup = live.get("reboot_cleanup") or {}
    checks.extend([
        Check("firmware-mounted", "pass" if all((live.get("mounted_hits") or {}).values()) else "blocked", "blocker", json.dumps(live.get("mounted_hits"), sort_keys=True), "repair firmware mounts before holder observation"),
        Check("holder-opened", "pass" if live.get("holder_opened") else "blocked", "blocker", f"mss={live.get('mss_before')}->{live.get('mss_after_holder')} mdm3={live.get('mdm3_before')}->{live.get('mdm3_after_holder')}", "do not interpret lower window without holder"),
        Check("surface-collected", "pass" if surface.get("icnss_device_present") else "blocked", "blocker", f"icnss={surface.get('icnss_device_present')} qrtr={surface.get('qrtr_table_available')}", "recapture if read-only surface is missing"),
        Check("wlfw-absent", "pass" if not markers.get("wlfw") and not markers.get("bdf") and not surface.get("wlan0_visible") else "advanced", "info", f"wlfw={markers.get('wlfw')} bdf={markers.get('bdf')} wlan0={surface.get('wlan0_visible')}", "if advanced, stop before connect and capture interface state"),
        Check("forbidden-actions", "pass", "blocker", "no lower companion/CNSS/service-manager/HAL/boot_wlan/connect command generated", "preserve V795 scope"),
        Check("cleanup-health", "pass" if cleanup.get("version_seen") and cleanup.get("status_healthy") else "blocked", "blocker", json.dumps(cleanup, sort_keys=True), "recover v724 health before continuing"),
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[Check], live: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v795-lower-window-mdm3-esoc-observer-plan-ready", True, "plan-only; no device command executed", "run bounded lower-window observer"
    blocked = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blocked:
        return "v795-lower-window-mdm3-esoc-observer-blocked", False, "blocked by " + ", ".join(blocked), "repair lower-window observer before next route"
    surface = live.get("surface") or {}
    markers = (live.get("markers") or {}).get("counts") or live.get("markers") or {}
    if markers.get("wlfw") or markers.get("bdf") or surface.get("wlan0_visible"):
        return "v795-lower-window-wlfw-advance", True, "lower-window holder produced WLFW/BDF/wlan0 evidence without HAL/connect", "capture interface/BDF state before credentials or DHCP"
    if live.get("mss_after_holder") == "ONLINE" and live.get("mdm3_after_holder") == "OFFLINING":
        return "v795-holder-modem-online-mdm3-offlining-classified", True, "subsys_modem holder brings modem ONLINE but mdm3 remains OFFLINING and WLFW/BDF/wlan0 stay absent", "plan V796 around esoc0/mdm3 trigger contract or Android vendor-init delta; still no boot_wlan/HAL/connect"
    return "v795-lower-window-surface-captured", True, "lower-window mdm3/esoc surface captured", "review surface before next action"


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    surface = live.get("surface") or {}
    markers = (live.get("markers") or {}).get("counts") or live.get("markers") or {}
    return "\n".join([
        "# V795 Lower-Window mdm3/esoc Observer",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Live Surface",
        "",
        markdown_table(["signal", "value"], [
            ["holder_opened", live.get("holder_opened")],
            ["mss", f"{live.get('mss_before')} -> {live.get('mss_after_holder')}"],
            ["mdm3", f"{live.get('mdm3_before')} -> {live.get('mdm3_after_holder')}"],
            ["surface modem/esoc0", f"{surface.get('modem_state')} / {surface.get('esoc0_subsys_state')}"],
            ["ICNSS device/driver", f"{surface.get('icnss_device_present')} / {surface.get('icnss_driver_link_present')}"],
            ["QRTR RX/services", f"{(live.get('qrtr_rx_wait') or {}).get('seen')} / {live.get('qrtr_services_after_holder')}"],
            ["WLFW/BDF/wlan0", f"{markers.get('wlfw', 0)} / {markers.get('bdf', 0)} / {surface.get('wlan0_visible')}"],
        ]),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [[check["name"], check["status"], check["severity"], check["detail"], check["next_step"]] for check in manifest["checks"]]),
        "",
        "## Safety",
        "",
        "- Firmware mounts and subsys_modem holder only.",
        "- No lower companion, CNSS daemon, service-manager, Wi-Fi HAL, boot_wlan/qcwlanstate write, scan/connect, credentials, DHCP/routes, external ping, esoc0 open, module bind/unbind, boot image write, partition write, or custom kernel flash.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v794_ref = read_json(args.v794_manifest)
    flags_missing = required_flags(args)
    steps: list[dict[str, Any]] = []
    live: dict[str, Any] = {}
    if args.command == "run" and not flags_missing:
        steps, live = run_live(args, store)
    checks = build_checks(args, flags_missing, v794_ref, live)
    decision, passed, reason, next_step = decide(args, checks, live)
    manifest = {
        "cycle": "v795",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "v794_reference": {"decision": v794_ref.get("decision"), "pass": v794_ref.get("pass"), "path": str(repo_path(args.v794_manifest))},
        "live": live,
        "checks": [asdict(check) for check in checks],
        "steps": [{key: value for key, value in step.items() if key != "payload"} for step in steps],
        "device_commands_executed": args.command == "run" and not flags_missing,
        "device_mutations": args.command == "run" and not flags_missing,
        "firmware_mounts_executed": bool(live.get("mounted_hits")),
        "subsys_modem_opened": bool(live.get("holder_opened")),
        "lower_companion_start_executed": False,
        "cnss_diag_start_executed": False,
        "cnss_daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "boot_wlan_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
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
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"boot_wlan_executed: {manifest['boot_wlan_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
