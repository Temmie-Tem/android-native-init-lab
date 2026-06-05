#!/usr/bin/env python3
"""V731 current-build firmware-mounted modem holder gate.

This runner recreates the known-good lower modem prerequisite from V594/V595/V596
on the current native build: mount Android firmware partitions read-only, open
and hold only `subsys_modem`, observe modem/QRTR movement, then reboot as the
cleanup boundary. It does not create/open `esoc0`, write subsystem state, start
daemons, start service-manager, start Wi-Fi HAL, scan/connect, use credentials,
DHCP, route, or ping.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v731-firmware-mounted-modem-holder")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_HOLD_SEC = 120
DEFAULT_QRTR_RX_TIMEOUT_SEC = 45.0
DEFAULT_QRTR_RX_POLL_SEC = 2.0
DEFAULT_V730_MANIFEST = Path("tmp/wifi/v730-modem-trigger-reconcile/manifest.json")

MSS_STATE = "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"
MSS_CRASH_COUNT = "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/crash_count"
MDM3_STATE = "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"
MDM3_CRASH_COUNT = "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/crash_count"
SUBSYS_MODEM_DEV = "/sys/class/subsys/subsys_modem/dev"
FIRMWARE_CLASS_PATH = "/sys/module/firmware_class/parameters/path"
GLOBAL_MODEM_BLOB_PATHS = (
    "/vendor/firmware_mnt/image/modem.b00",
    "/vendor/firmware-modem/image/modem.b00",
    "/firmware/image/modem.b00",
)
FORBIDDEN_TERMS = (
    "subsys_esoc0",
    "/sys/class/subsys/subsys_esoc0",
    "/dev/subsys_esoc0",
    "echo online",
    "> /sys/devices",
    "qcwlanstate",
    "svc wifi",
    "cmd wifi",
    "IWifi",
    "wpa_supplicant",
    "hostapd",
    "wificond",
    "dhcp",
    " ping ",
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_TS_RE = re.compile(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]")
FOCUS_PATTERNS: dict[str, re.Pattern[str]] = {
    "qrtr_rx": re.compile(r"qrtr: Modem QMI Readiness RX", re.I),
    "qrtr_tx": re.compile(r"qrtr: Modem QMI Readiness TX", re.I),
    "sysmon_qmi": re.compile(r"sysmon-qmi", re.I),
    "rpmsg": re.compile(r"rpmsg|IPCRTR", re.I),
    "service_notifier": re.compile(r"service-notifier|service_notifier", re.I),
    "wlan_pd": re.compile(r"wlan[_-]?pd|msm/modem/wlan_pd", re.I),
    "mhi": re.compile(r"\bmhi\b|mhi_sync_power_up", re.I),
    "qca6390": re.compile(r"qca6390|wcn3990", re.I),
    "wlfw": re.compile(r"\bwlfw\b|service 69|QMI Server Connected", re.I),
    "bdf": re.compile(r"\bBDF\b|bdwlan\.bin|regdb\.bin", re.I),
    "wlan0": re.compile(r"\bwlan0\b", re.I),
    "kernel_warning": re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put: esoc0 count:0|pm_qos_add_request", re.I),
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
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=DEFAULT_HOLD_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v730-manifest", type=Path, default=DEFAULT_V730_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
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
            raise RuntimeError(f"forbidden V731 command term {term!r}: {joined}")
    if command[0] in {"version", "status", "selftest", "cat", "stat", "mkdir", "mknodb", "umount", "reboot"}:
        return
    if command[:2] == ["run", DEFAULT_TOYBOX] and len(command) >= 3:
        if command[2] in {"mount", "rm", "rmdir", "dmesg", "ls", "ln", "ps"}:
            return
    if command[:2] == ["run", DEFAULT_BUSYBOX] and len(command) >= 3:
        if command[2] in {"sh", "sleep"}:
            script = command[-1] if command[2] == "sh" else ""
            if proof_base and script and proof_base not in script:
                raise RuntimeError(f"V731 shell script missing proof path: {joined}")
            return
    raise RuntimeError(f"unexpected V731 command: {joined}")


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


def parse_dev(text: str) -> tuple[str, str] | None:
    match = re.search(r"\b([0-9]+):([0-9]+)\b", text)
    if not match:
        return None
    return match.group(1), match.group(2)


def path_exists(text: str) -> bool:
    lowered = text.lower()
    return bool(text.strip()) and "no such file" not in lowered and "errno=2" not in lowered and "[err]" not in lowered


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return safe_name(args.proof_id)
    return "v731-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def dmesg_last_timestamp(text: str) -> float | None:
    last: float | None = None
    for raw_line in text.splitlines():
        line = ANSI_RE.sub("", raw_line).strip()
        match = DMESG_TS_RE.match(line)
        if match:
            last = float(match.group(1))
    return last


def dmesg_delta(before: str, after: str) -> str:
    before_last = dmesg_last_timestamp(before)
    if before_last is None:
        return after
    lines: list[str] = []
    for raw_line in after.splitlines():
        line = ANSI_RE.sub("", raw_line).strip()
        match = DMESG_TS_RE.match(line)
        if match and float(match.group(1)) > before_last:
            lines.append(raw_line)
    return "\n".join(lines) + ("\n" if lines else "")


def marker_summary(text: str) -> dict[str, Any]:
    focus: list[str] = []
    events: dict[str, list[str]] = {name: [] for name in FOCUS_PATTERNS}
    for raw_line in text.splitlines():
        line = ANSI_RE.sub("", raw_line).strip()
        if not line:
            continue
        matched = False
        for name, pattern in FOCUS_PATTERNS.items():
            if pattern.search(line):
                events[name].append(line[:360])
                matched = True
        if matched:
            focus.append(line[:360])
    return {
        "counts": {name: len(lines) for name, lines in events.items()},
        "first_lines": {name: lines[0] for name, lines in events.items() if lines},
        "focus_tail": focus[-220:],
    }


def holder_script(args: argparse.Namespace, node: str, status: str, pidfile: str, major: str, minor: str) -> str:
    hold_sec = max(30, min(args.hold_sec, 300))
    return "\n".join([
        "set -u",
        f"node={shell_quote(node)}",
        f"status={shell_quote(status)}",
        f"pidfile={shell_quote(pidfile)}",
        f"{args.toybox} rm -f \"$node\" \"$status\" \"$pidfile\"",
        f"{args.toybox} mknod -m 600 \"$node\" c {major} {minor}",
        "(",
        "  exec 3<\"$node\"",
        "  echo opened > \"$status\"",
        f"  {args.busybox} sleep {hold_sec}",
        ") &",
        "holder_pid=$!",
        "echo \"$holder_pid\" > \"$pidfile\"",
        "for i in 1 2 3 4 5 6 7 8 9 10; do",
        "  test -s \"$status\" && break",
        f"  {args.busybox} sleep 1",
        "done",
        "echo v731.holder.node=$node",
        "echo v731.holder.pid=$holder_pid",
        f"echo v731.holder.status=$({args.toybox} cat \"$status\" 2>/dev/null || true)",
        f"{args.toybox} ps -A -o pid,stat,comm,args | {args.toybox} grep \"$holder_pid\" | {args.toybox} grep -v grep || true",
    ])


def wait_for_qrtr_rx(args: argparse.Namespace,
                     store: EvidenceStore,
                     steps: list[dict[str, Any]],
                     before_text: str) -> dict[str, Any]:
    started = time.monotonic()
    attempts: list[dict[str, Any]] = []
    last_delta = ""
    attempt = 0
    while time.monotonic() - started <= args.qrtr_rx_timeout_sec:
        attempt += 1
        item = run_step(args, store, steps, f"wait-qrtr-rx-dmesg-{attempt:02d}", ["run", args.toybox, "dmesg"], 60.0)
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


def reboot_and_wait(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    reboot_capture = run_capture(args, "reboot-cleanup", ["reboot"], timeout=5.0)
    write_capture(store, "reboot-cleanup", reboot_capture.text or reboot_capture.error)
    started = time.monotonic()
    version_text = ""
    status_text = ""
    for _ in range(90):
        try:
            result = run_cmdv1_command(args.host, args.port, 3.0, ["version"], retry_unsafe=False)
            if result.rc == 0 and result.status == "ok":
                version_text = result.text
                status = run_cmdv1_command(args.host, args.port, 5.0, ["status"], retry_unsafe=False)
                status_text = status.text
                break
        except Exception:
            time.sleep(2.0)
    write_capture(store, "post-reboot-version", version_text or "<missing>")
    write_capture(store, "post-reboot-status", status_text or "<missing>")
    return {
        "reboot_command_ok": reboot_capture.ok,
        "reboot_command_status": reboot_capture.status,
        "reboot_command_error": reboot_capture.error,
        "wait_sec": round(time.monotonic() - started, 3),
        "version_seen": args.expect_version in version_text,
        "status_healthy": "fail=0" in status_text,
    }


def capture_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    mount_steps: list[dict[str, Any]] = []
    mount_args = argparse.Namespace(**vars(args))
    mount_args.command = "preflight"
    preflight = mountv.capture_preflight(mount_args, store, mount_steps)
    steps.extend(mount_steps)
    run_step(args, store, steps, "firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 10.0)
    run_step(args, store, steps, "subsys-modem-dev", ["cat", SUBSYS_MODEM_DEV], 10.0)
    run_step(args, store, steps, "mss-state-before", ["cat", MSS_STATE], 10.0)
    run_step(args, store, steps, "mss-crash-before", ["cat", MSS_CRASH_COUNT], 10.0)
    run_step(args, store, steps, "mdm3-state-before", ["cat", MDM3_STATE], 10.0)
    run_step(args, store, steps, "mdm3-crash-before", ["cat", MDM3_CRASH_COUNT], 10.0)
    run_step(args, store, steps, "ps-before", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    return preflight


def active_holder_hits(ps_text: str) -> list[str]:
    return [line.strip() for line in ps_text.splitlines() if "a90-v731-" in line or "a90-v596-subsys-modem" in line or "a90-v729-" in line]


def preflight_blockers(args: argparse.Namespace, steps: list[dict[str, Any]], preflight: dict[str, Any], v730: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if args.expect_version not in step_payload(steps, "version"):
        blockers.append("unexpected-native-version")
    if "fail=0" not in step_payload(steps, "status") or "fail=0" not in step_payload(steps, "selftest"):
        blockers.append("native-not-healthy")
    if v730.get("decision") != "v730-global-firmware-mounted-modem-holder-required":
        blockers.append("v730-decision-missing")
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
    return blockers


def run_live(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], preflight: dict[str, Any]) -> dict[str, Any]:
    label = proof_id(args)
    base = mountv.PROOF_BASE_PREFIX.replace("v584", "v731") + label
    node = f"{base}/subsys_modem"
    status_file = f"{base}/holder.status"
    pid_file = f"{base}/holder.pid"
    before = run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    mount_results: list[str] = []
    holder_started = False
    reboot = {}
    try:
        for name, command, timeout in mountv.build_mount_commands(preflight, base):
            item = run_step(args, store, steps, f"v731-{name}", command, timeout, base)
            mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0)
        run_step(args, store, steps, "mounted-firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 10.0)
        for blob_path in GLOBAL_MODEM_BLOB_PATHS:
            run_step(args, store, steps, f"mounted-stat-{safe_name(blob_path)}", ["stat", blob_path], 10.0)
        dev = parse_dev(step_payload(steps, "subsys-modem-dev"))
        if not dev:
            raise RuntimeError("subsys_modem dev missing after preflight")
        script = holder_script(args, node, status_file, pid_file, dev[0], dev[1])
        write_capture(store, "holder-script-redacted", script)
        holder = run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", script], 25.0, base)
        holder_started = holder.get("ok") is True
        run_step(args, store, steps, "mss-state-after-holder", ["cat", MSS_STATE], 10.0)
        run_step(args, store, steps, "mss-crash-after-holder", ["cat", MSS_CRASH_COUNT], 10.0)
        run_step(args, store, steps, "mdm3-state-after-holder", ["cat", MDM3_STATE], 10.0)
        run_step(args, store, steps, "mdm3-crash-after-holder", ["cat", MDM3_CRASH_COUNT], 10.0)
        run_step(args, store, steps, "rpmsg-after-holder", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0)
        qrtr_wait = wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""))
        run_step(args, store, steps, "mss-state-after-wait", ["cat", MSS_STATE], 10.0)
        run_step(args, store, steps, "mdm3-state-after-wait", ["cat", MDM3_STATE], 10.0)
        run_step(args, store, steps, "proc-net-qrtr-after-wait", ["cat", "/proc/net/qrtr"], 10.0)
        run_step(args, store, steps, "ps-before-reboot", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
        after = run_step(args, store, steps, "dmesg-after-holder", ["run", args.toybox, "dmesg"], 60.0)
        delta = dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
        write_capture(store, "dmesg-delta", delta)
        markers = marker_summary(delta)
    finally:
        reboot = reboot_and_wait(args, store)
    mounted = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    return {
        "base": base,
        "node": node,
        "mount_results": mount_results,
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": {
            blob_path: path_exists(step_payload(steps, f"mounted-stat-{safe_name(blob_path)}"))
            for blob_path in GLOBAL_MODEM_BLOB_PATHS
        },
        "holder_started": holder_started,
        "holder_status": step_payload(steps, "start-modem-holder"),
        "holder_opened": "v731.holder.status=opened" in step_payload(steps, "start-modem-holder"),
        "mss_before": step_payload(steps, "mss-state-before").strip(),
        "mss_after_holder": step_payload(steps, "mss-state-after-holder").strip(),
        "mss_after_wait": step_payload(steps, "mss-state-after-wait").strip(),
        "mdm3_before": step_payload(steps, "mdm3-state-before").strip(),
        "mdm3_after_holder": step_payload(steps, "mdm3-state-after-holder").strip(),
        "mdm3_after_wait": step_payload(steps, "mdm3-state-after-wait").strip(),
        "mss_crash_before": step_payload(steps, "mss-crash-before").strip(),
        "mss_crash_after_holder": step_payload(steps, "mss-crash-after-holder").strip(),
        "mdm3_crash_before": step_payload(steps, "mdm3-crash-before").strip(),
        "mdm3_crash_after_holder": step_payload(steps, "mdm3-crash-after-holder").strip(),
        "rpmsg_after_holder": step_payload(steps, "rpmsg-after-holder"),
        "proc_qrtr_after_wait": step_payload(steps, "proc-net-qrtr-after-wait"),
        "qrtr_rx_wait": qrtr_wait,
        "markers": markers if "markers" in locals() else {},
        "reboot_cleanup": reboot,
    }


def build_checks(args: argparse.Namespace,
                 steps: list[dict[str, Any]],
                 preflight: dict[str, Any],
                 v730: dict[str, Any],
                 live: dict[str, Any] | None,
                 blockers: list[str]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command executed",
            "next_step": "run V731 firmware-mounted modem holder gate",
        }]
    checks: list[dict[str, Any]] = [
        {
            "name": "preflight-blockers",
            "status": "pass" if not blockers else "blocked",
            "detail": {"blockers": blockers},
            "next_step": "clear blockers before live V731",
        },
        {
            "name": "v730-routing",
            "status": "pass" if v730.get("decision") == "v730-global-firmware-mounted-modem-holder-required" else "blocked",
            "detail": {"decision": v730.get("decision"), "pass": v730.get("pass")},
            "next_step": "rerun V730 if routing evidence is stale",
        },
    ]
    if not live:
        return checks
    counts = ((live.get("markers") or {}).get("counts") or {})
    reboot = live.get("reboot_cleanup") or {}
    checks.extend([
        {
            "name": "firmware-mounted",
            "status": "pass" if all((live.get("mounted_hits") or {}).get(target) for target in mountv.PARTITION_TARGETS.values()) and any((live.get("modem_blob_visible") or {}).values()) else "blocked",
            "detail": {"mounted_hits": live.get("mounted_hits"), "modem_blob_visible": live.get("modem_blob_visible")},
            "next_step": "inspect partition resolution and mount commands",
        },
        {
            "name": "subsys-modem-holder-opened",
            "status": "pass" if live.get("holder_opened") or live.get("mss_after_holder") == "ONLINE" or (live.get("qrtr_rx_wait") or {}).get("seen") else "finding",
            "detail": {"holder_opened": live.get("holder_opened"), "mss_after_holder": live.get("mss_after_holder"), "qrtr_seen": (live.get("qrtr_rx_wait") or {}).get("seen")},
            "next_step": "if not opened, inspect holder transcript under mounted firmware parity",
        },
        {
            "name": "mss-online-window",
            "status": "pass" if "ONLINE" in {live.get("mss_after_holder"), live.get("mss_after_wait")} else "finding",
            "detail": {"before": live.get("mss_before"), "after_holder": live.get("mss_after_holder"), "after_wait": live.get("mss_after_wait")},
            "next_step": "if still offlining, firmware mount parity did not restore modem PIL on current build",
        },
        {
            "name": "qrtr-rx-window",
            "status": "pass" if (live.get("qrtr_rx_wait") or {}).get("seen") or counts.get("qrtr_rx", 0) else "finding",
            "detail": {"wait": live.get("qrtr_rx_wait"), "counts": {key: counts.get(key, 0) for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "rpmsg")}},
            "next_step": "if QRTR RX appears, next gate can add lower companion in the held window",
        },
        {
            "name": "postflight-reboot-cleanup",
            "status": "pass" if reboot.get("version_seen") and reboot.get("status_healthy") else "blocked",
            "detail": reboot,
            "next_step": "manually verify bridge/device if reboot cleanup did not prove healthy native",
        },
        {
            "name": "kernel-warning-review",
            "status": "review" if counts.get("kernel_warning", 0) else "pass",
            "detail": {"kernel_warning": counts.get("kernel_warning", 0), "first": ((live.get("markers") or {}).get("first_lines") or {}).get("kernel_warning", "")},
            "next_step": "if warnings appeared, do not broaden live work until warning source is classified",
        },
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v731-firmware-mounted-modem-holder-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V731 live gate",
        )
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v731-firmware-mounted-modem-holder-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear blocker before further live work",
        )
    if not live:
        return (
            "v731-firmware-mounted-modem-holder-preflight-ready",
            True,
            "preflight ready",
            "run live V731 gate",
        )
    counts = ((live.get("markers") or {}).get("counts") or {})
    if counts.get("kernel_warning", 0):
        return (
            "v731-firmware-mounted-modem-holder-warning-classified",
            True,
            "firmware-mounted holder completed with kernel warning markers; reboot cleanup restored native",
            "classify warning source before adding lower companion",
        )
    if (live.get("qrtr_rx_wait") or {}).get("seen") or counts.get("qrtr_rx", 0):
        return (
            "v731-firmware-mounted-modem-holder-qrtr-rx-pass",
            True,
            "current-build firmware-mounted subsys_modem holder restored modem QRTR RX without esoc0, daemon/HAL, scan/connect, or credentials",
            "plan V732 lower companion inside firmware-mounted modem holder window; still no Wi-Fi scan/connect",
        )
    if "ONLINE" in {live.get("mss_after_holder"), live.get("mss_after_wait")}:
        return (
            "v731-firmware-mounted-modem-holder-online-no-qrtr",
            True,
            "firmware-mounted holder moved mss ONLINE but QRTR RX was not observed",
            "inspect dmesg delta and QRTR routing before companion",
        )
    return (
        "v731-firmware-mounted-modem-holder-no-readiness",
        True,
        "firmware-mounted holder did not move mss ONLINE or QRTR RX on current build",
        "compare V595/V596 command deltas before retrying",
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
        ["holder_opened", live.get("holder_opened", "")],
        ["mss", f"{live.get('mss_before', '')}->{live.get('mss_after_holder', '')}->{live.get('mss_after_wait', '')}"],
        ["mdm3", f"{live.get('mdm3_before', '')}->{live.get('mdm3_after_holder', '')}->{live.get('mdm3_after_wait', '')}"],
        ["reboot_cleanup", json.dumps(live.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    marker_rows = [[name, str(counts.get(name, 0))] for name in FOCUS_PATTERNS]
    return "\n".join([
        "# V731 Firmware-mounted Modem Holder",
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
        f"- esoc0_open_executed: `{manifest['esoc0_open_executed']}`",
        f"- daemon_or_hal_start_executed: `{manifest['daemon_or_hal_start_executed']}`",
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
        "## Dmesg Marker Counts",
        "",
        markdown_table(["marker", "count"], marker_rows),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    v730 = load_json_if_exists(args.v730_manifest)
    preflight: dict[str, Any] = {}
    live: dict[str, Any] | None = None
    blockers: list[str] = []
    if args.command == "run":
        preflight = capture_preflight(args, store, steps)
        blockers = preflight_blockers(args, steps, preflight, v730)
        if not blockers:
            live = run_live(args, store, steps, preflight)
    checks = build_checks(args, steps, preflight, v730, live, blockers)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v731",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "v730": {"decision": v730.get("decision"), "pass": v730.get("pass"), "path": v730.get("path", str(repo_path(args.v730_manifest)))},
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
    latest = repo_path("tmp/wifi/latest-v731-firmware-mounted-modem-holder.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"subsys_modem_open_attempted: {manifest['subsys_modem_open_attempted']}")
    print(f"subsys_modem_opened: {manifest['subsys_modem_opened']}")
    print(f"esoc0_open_executed: {manifest['esoc0_open_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
