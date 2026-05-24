#!/usr/bin/env python3
"""V729 modem-only subsystem hold proof.

This runner opens only the `subsys_modem` character device for a bounded window
from a background shell process. It does not create or open an `esoc0` node, does
not write subsystem state, does not start CNSS daemon/service-manager/Wi-Fi HAL,
and does not scan/connect/DHCP/route/ping.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v729-modem-only-hold")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_HOLD_SEC = 8
PROBE_PREFIX = "/tmp/a90-v729-"

MSS_STATE = "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"
MSS_CRASH_COUNT = "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/crash_count"
MDM3_STATE = "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"
MDM3_CRASH_COUNT = "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/crash_count"
SUBSYS_MODEM_DEV = "/sys/class/subsys/subsys_modem/dev"

FORBIDDEN_TERMS = (
    "subsys_esoc0",
    "/sys/class/subsys/subsys_esoc0",
    "/dev/subsys_esoc0",
    "svc wifi",
    "cmd wifi",
    "qcwlanstate",
    "wpa_supplicant",
    "hostapd",
    "dhcp",
    "ping",
    "rfkill",
    "insmod",
    "rmmod",
    "modprobe",
    "ip link",
    "echo online",
    "> /sys/devices",
)
DMESG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.I)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.I)),
    ("sysmon", re.compile(r"sysmon-qmi", re.I)),
    ("rpmsg", re.compile(r"rpmsg|IPCRTR", re.I)),
    ("service_notifier", re.compile(r"service-notifier|service_notifier", re.I)),
    ("wlan_pd", re.compile(r"wlan[_-]?pd|msm/modem/wlan_pd", re.I)),
    ("mhi", re.compile(r"\bmhi\b|mhi_sync_power_up", re.I)),
    ("qca6390", re.compile(r"qca6390|wcn3990", re.I)),
    ("wlfw", re.compile(r"\bwlfw\b|service 69|QMI Server Connected", re.I)),
    ("bdf", re.compile(r"\bBDF\b|bdwlan\.bin|regdb\.bin", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("warning", re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put|pm_qos_add_request", re.I)),
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@dataclass(frozen=True)
class ProbePaths:
    run_id: str
    base: str
    node: str
    pid_file: str
    log_file: str


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
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def make_probe_paths() -> ProbePaths:
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = f"{PROBE_PREFIX}{run_id}"
    return ProbePaths(
        run_id=run_id,
        base=base,
        node=f"{base}/subsys_modem",
        pid_file=f"{base}/holder.pid",
        log_file=f"{base}/holder.log",
    )


def is_under_probe(path: str, probe: ProbePaths) -> bool:
    return path == probe.base or path.startswith(probe.base + "/")


def validate_device_command(command: list[str], probe: ProbePaths | None = None, args: argparse.Namespace | None = None) -> None:
    joined = " ".join(command)
    lowered = joined.lower()
    for term in FORBIDDEN_TERMS:
        if term in lowered:
            raise RuntimeError(f"forbidden V729 command term {term!r}: {joined}")
    if command[0] in {"version", "status", "selftest", "cat", "stat", "mkdir"}:
        if command[0] == "mkdir" and probe and len(command) == 2 and is_under_probe(command[1], probe):
            return
        if command[0] != "mkdir":
            return
    if args and command[:2] == ["run", args.busybox]:
        subcmd = command[2] if len(command) > 2 else ""
        if subcmd == "mknod" and probe and len(command) == 7 and command[3] == probe.node and command[4] == "c":
            return
        if subcmd == "chmod" and probe and len(command) == 5 and command[4] == probe.node:
            return
        if subcmd == "sh" and len(command) == 5 and command[3] == "-c":
            script = command[4]
            for required_path in (probe.base if probe else "",):
                if required_path and required_path not in script:
                    raise RuntimeError(f"V729 shell script does not reference probe path: {joined}")
            return
        if subcmd in {"sleep", "kill"}:
            return
    if args and command[:2] == ["run", args.toybox]:
        subcmd = command[2] if len(command) > 2 else ""
        if subcmd in {"rm", "rmdir", "dmesg"}:
            return
    raise RuntimeError(f"unexpected V729 command: {joined}")


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
    validate_device_command(command, probe, args)
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


def parse_dev(text: str) -> tuple[str, str] | None:
    match = re.search(r"(?m)^(\d+):(\d+)\s*$", text.strip())
    if not match:
        return None
    return match.group(1), match.group(2)


def parse_holder_log(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in text.splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.strip().split("=", 1)
        parsed[key] = value
    return parsed


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
        "focus_tail": focus[-220:],
    }


def read_state_steps(args: argparse.Namespace,
                     store: EvidenceStore,
                     steps: list[dict[str, Any]],
                     phase: str) -> None:
    run_step(args, store, steps, f"{phase}-mss-state", ["cat", MSS_STATE], 10.0)
    run_step(args, store, steps, f"{phase}-mss-crash-count", ["cat", MSS_CRASH_COUNT], 10.0)
    run_step(args, store, steps, f"{phase}-mdm3-state", ["cat", MDM3_STATE], 10.0)
    run_step(args, store, steps, f"{phase}-mdm3-crash-count", ["cat", MDM3_CRASH_COUNT], 10.0)


def collect_live(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    probe = make_probe_paths()
    hold_sec = max(2, min(args.hold_sec, 20))

    run_step(args, store, steps, "version", ["version"], 15.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "selftest", ["selftest"], 25.0)
    run_step(args, store, steps, "subsys-modem-dev", ["cat", SUBSYS_MODEM_DEV], 10.0)
    read_state_steps(args, store, steps, "before")

    dev = parse_dev(step_payload(steps, "subsys-modem-dev"))
    holder_started = False
    if dev:
        major, minor = dev
        run_step(args, store, steps, "mkdir-base", ["mkdir", probe.base], 10.0, probe)
        run_step(args, store, steps, "mknod-subsys-modem", ["run", args.busybox, "mknod", probe.node, "c", major, minor], 10.0, probe)
        run_step(args, store, steps, "chmod-subsys-modem", ["run", args.busybox, "chmod", "600", probe.node], 10.0, probe)
        script = (
            f"(exec 3<{probe.node}; rc=$?; echo open_rc=$rc > {probe.log_file}; "
            f"if [ $rc -eq 0 ]; then {args.busybox} sleep {hold_sec}; fi; "
            f"echo done=1 >> {probe.log_file}) & echo $! > {probe.pid_file}"
        )
        status_script = (
            f"pid=$({args.busybox} cat {probe.pid_file} 2>/dev/null); echo pid=$pid; "
            f"if [ -n \"$pid\" ] && {args.busybox} kill -0 $pid 2>/dev/null; then echo alive=1; else echo alive=0; fi; "
            f"if [ -e {probe.log_file} ]; then echo log_exists=1; else echo log_exists=0; fi"
        )
        run_step(args, store, steps, "start-holder", ["run", args.busybox, "sh", "-c", script], 10.0, probe)
        holder_started = step_ok(steps, "start-holder")
        run_step(args, store, steps, "settle-holder", ["run", args.busybox, "sleep", "1"], 5.0, probe)
        run_step(args, store, steps, "holder-status-during", ["run", args.busybox, "sh", "-c", status_script], 10.0, probe)
        run_step(args, store, steps, "holder-log-during", ["cat", probe.log_file], 10.0)
        read_state_steps(args, store, steps, "hold")
        run_step(args, store, steps, "dmesg-hold", ["run", args.toybox, "dmesg"], 60.0)
        run_step(args, store, steps, "wait-holder", ["run", args.busybox, "sleep", str(hold_sec + 2)], hold_sec + 7.0, probe)
        run_step(args, store, steps, "holder-status-after", ["run", args.busybox, "sh", "-c", status_script], 10.0, probe)
        run_step(args, store, steps, "holder-log-after", ["cat", probe.log_file], 10.0)
        cleanup_script = (
            f"pid=$({args.busybox} cat {probe.pid_file} 2>/dev/null); "
            f"if [ -n \"$pid\" ]; then {args.busybox} kill -TERM $pid 2>/dev/null; "
            f"{args.busybox} sleep 1; {args.busybox} kill -KILL $pid 2>/dev/null; fi"
        )
        run_step(args, store, steps, "cleanup-kill-holder", ["run", args.busybox, "sh", "-c", cleanup_script], 10.0, probe)
        read_state_steps(args, store, steps, "after")
        run_step(args, store, steps, "dmesg-after", ["run", args.toybox, "dmesg"], 60.0)
        run_step(args, store, steps, "cleanup-rm-node", ["run", args.toybox, "rm", "-f", probe.node, probe.pid_file, probe.log_file], 10.0, probe)
        run_step(args, store, steps, "cleanup-rmdir-base", ["run", args.toybox, "rmdir", probe.base], 10.0, probe)

    dmesg_hold = parse_dmesg(step_payload(steps, "dmesg-hold"))
    dmesg_after = parse_dmesg(step_payload(steps, "dmesg-after"))
    store.write_text("native/dmesg-hold-focus.txt", "\n".join(dmesg_hold["focus_tail"]) + ("\n" if dmesg_hold["focus_tail"] else ""))
    store.write_text("native/dmesg-after-focus.txt", "\n".join(dmesg_after["focus_tail"]) + ("\n" if dmesg_after["focus_tail"] else ""))
    holder_during = parse_holder_log(step_payload(steps, "holder-log-during"))
    holder_after = parse_holder_log(step_payload(steps, "holder-log-after"))
    holder_status_during = parse_holder_log(step_payload(steps, "holder-status-during"))
    holder_status_after = parse_holder_log(step_payload(steps, "holder-status-after"))
    live = {
        "probe": probe.__dict__,
        "subsys_modem_dev": dev,
        "holder_started": holder_started,
        "holder_pid_during": holder_status_during.get("pid", ""),
        "holder_alive_during": holder_status_during.get("alive", "") == "1",
        "holder_log_exists_during": holder_status_during.get("log_exists", "") == "1",
        "holder_pid_after": holder_status_after.get("pid", ""),
        "holder_alive_after": holder_status_after.get("alive", "") == "1",
        "holder_log_exists_after": holder_status_after.get("log_exists", "") == "1",
        "holder_open_pending_during": holder_status_during.get("alive", "") == "1" and holder_status_during.get("log_exists", "") != "1",
        "holder_open_pending_after": holder_status_after.get("alive", "") == "1" and holder_status_after.get("log_exists", "") != "1",
        "holder_open_rc_during": holder_during.get("open_rc", ""),
        "holder_open_rc_after": holder_after.get("open_rc", ""),
        "holder_done": holder_after.get("done", "") == "1",
        "before_mss_state": step_payload(steps, "before-mss-state").strip(),
        "hold_mss_state": step_payload(steps, "hold-mss-state").strip(),
        "after_mss_state": step_payload(steps, "after-mss-state").strip(),
        "before_mdm3_state": step_payload(steps, "before-mdm3-state").strip(),
        "hold_mdm3_state": step_payload(steps, "hold-mdm3-state").strip(),
        "after_mdm3_state": step_payload(steps, "after-mdm3-state").strip(),
        "before_mss_crash_count": step_payload(steps, "before-mss-crash-count").strip(),
        "after_mss_crash_count": step_payload(steps, "after-mss-crash-count").strip(),
        "before_mdm3_crash_count": step_payload(steps, "before-mdm3-crash-count").strip(),
        "after_mdm3_crash_count": step_payload(steps, "after-mdm3-crash-count").strip(),
        "dmesg_hold": dmesg_hold,
        "dmesg_after": dmesg_after,
        "cleanup_ok": step_ok(steps, "cleanup-rmdir-base"),
    }
    return steps, live


def build_checks(args: argparse.Namespace, steps: list[dict[str, Any]], live: dict[str, Any]) -> list[dict[str, Any]]:
    if not live:
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command executed",
            "next_step": "run V729 modem-only hold proof",
        }]
    hold_counts = (live.get("dmesg_hold") or {}).get("counts") or {}
    after_counts = (live.get("dmesg_after") or {}).get("counts") or {}
    crash_stable = (
        live.get("before_mss_crash_count") == live.get("after_mss_crash_count")
        and live.get("before_mdm3_crash_count") == live.get("after_mdm3_crash_count")
    )
    return [
        {
            "name": "native-v724-clean",
            "status": "pass" if args.expect_version in step_payload(steps, "version") and "fail=0" in step_payload(steps, "status") and "fail=0" in step_payload(steps, "selftest") else "blocked",
            "detail": {"expect_version": args.expect_version},
            "next_step": "restore expected native baseline before modem hold proof",
        },
        {
            "name": "subsys-modem-node-created",
            "status": "pass" if live.get("subsys_modem_dev") and step_ok(steps, "mknod-subsys-modem") else "blocked",
            "detail": {"subsys_modem_dev": live.get("subsys_modem_dev")},
            "next_step": "cannot test modem-only hold without subsys_modem cdev",
        },
        {
            "name": "modem-only-holder-started",
            "status": "pass" if live.get("holder_started") else "blocked",
            "detail": {"pid_during": live.get("holder_pid_during"), "pid_after": live.get("holder_pid_after")},
            "next_step": "if the holder cannot start, fix the bounded cdev proof harness first",
        },
        {
            "name": "modem-only-open-outcome",
            "status": "pass" if live.get("holder_open_rc_after") == "0" else ("finding" if live.get("holder_open_pending_during") or live.get("holder_open_pending_after") else "blocked"),
            "detail": {
                "open_rc_during": live.get("holder_open_rc_during"),
                "open_rc_after": live.get("holder_open_rc_after"),
                "pending_during": live.get("holder_open_pending_during"),
                "pending_after": live.get("holder_open_pending_after"),
                "done": live.get("holder_done"),
            },
            "next_step": "if open stays pending, compare Android mdm_helper ioctl/property path before broadening triggers",
        },
        {
            "name": "mss-online-window",
            "status": "pass" if "ONLINE" in {live.get("hold_mss_state"), live.get("after_mss_state")} else "finding",
            "detail": {"before": live.get("before_mss_state"), "hold": live.get("hold_mss_state"), "after": live.get("after_mss_state")},
            "next_step": "if still offline, modem-only holder is not enough to trigger MPSS",
        },
        {
            "name": "mdm3-online-window",
            "status": "pass" if "ONLINE" in {live.get("hold_mdm3_state"), live.get("after_mdm3_state")} else "finding",
            "detail": {"before": live.get("before_mdm3_state"), "hold": live.get("hold_mdm3_state"), "after": live.get("after_mdm3_state")},
            "next_step": "if mdm3 remains offlining, WLAN-PD/WLFW are still not expected",
        },
        {
            "name": "qrtr-sysmon-movement",
            "status": "pass" if hold_counts.get("qrtr_rx", 0) or hold_counts.get("qrtr_tx", 0) or hold_counts.get("sysmon", 0) else "finding",
            "detail": {"hold": {key: hold_counts.get(key, 0) for key in ("qrtr_rx", "qrtr_tx", "sysmon", "rpmsg")}},
            "next_step": "next gate should add lower companion only if modem-only hold creates a modem window",
        },
        {
            "name": "wlfw-wlan0-movement",
            "status": "pass" if after_counts.get("wlfw", 0) or after_counts.get("wlan0", 0) else "finding",
            "detail": {"after": {key: after_counts.get(key, 0) for key in ("mhi", "qca6390", "wlfw", "bdf", "wlan0")}},
            "next_step": "Wi-Fi HAL/scan/connect remains blocked until WLFW/BDF/wlan0 appears",
        },
        {
            "name": "postflight-safe",
            "status": "pass" if live.get("cleanup_ok") and crash_stable and after_counts.get("warning", 0) == 0 else "review",
            "detail": {
                "cleanup_ok": live.get("cleanup_ok"),
                "crash_stable": crash_stable,
                "warning_count": after_counts.get("warning", 0),
                "mss_crash": [live.get("before_mss_crash_count"), live.get("after_mss_crash_count")],
                "mdm3_crash": [live.get("before_mdm3_crash_count"), live.get("after_mdm3_crash_count")],
            },
            "next_step": "review warnings or crash-count changes before broader live work",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], live: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v729-modem-only-hold-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V729 modem-only hold proof",
        )
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v729-modem-only-hold-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear modem-only cdev/open blocker before further live work",
        )
    finding_names = {check["name"] for check in checks if check["status"] == "finding"}
    if live.get("holder_open_pending_during") or live.get("holder_open_pending_after"):
        return (
            "v729-subsys-modem-open-pending-no-online-window",
            True,
            "subsys_modem open attempt remained pending/blocking and did not create a modem ONLINE window",
            "plan V730 around Android mdm_helper/ioctl/property trigger comparison before trying broader subsystem actions",
        )
    if "mss-online-window" not in finding_names and "qrtr-sysmon-movement" not in finding_names:
        return (
            "v729-modem-only-hold-created-modem-readiness-window",
            True,
            "opening only subsys_modem created an observable modem readiness window without esoc0 or Wi-Fi bring-up",
            "plan V730 lower companion observer inside this modem-only window; keep CNSS daemon/HAL/scan/connect blocked",
        )
    if "mss-online-window" not in finding_names:
        return (
            "v729-modem-only-hold-online-no-qrtr-window",
            True,
            "opening only subsys_modem changed modem state but did not produce QRTR/sysmon markers",
            "plan V730 around lower companion ordering or longer bounded modem-only window",
        )
    return (
        "v729-modem-only-hold-opened-no-online-window",
        True,
        "subsys_modem opened but did not create an ONLINE modem readiness window",
        "inspect V729 evidence before deciding whether a different safe trigger is needed",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    hold_counts = ((live.get("dmesg_hold") or {}).get("counts") or {})
    after_counts = ((live.get("dmesg_after") or {}).get("counts") or {})
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    state_rows = [
        ["holder_open_rc_after", live.get("holder_open_rc_after", "")],
        ["holder_open_pending_during", live.get("holder_open_pending_during", "")],
        ["holder_open_pending_after", live.get("holder_open_pending_after", "")],
        ["holder_done", live.get("holder_done", "")],
        ["mss_state_before", live.get("before_mss_state", "")],
        ["mss_state_hold", live.get("hold_mss_state", "")],
        ["mss_state_after", live.get("after_mss_state", "")],
        ["mdm3_state_before", live.get("before_mdm3_state", "")],
        ["mdm3_state_hold", live.get("hold_mdm3_state", "")],
        ["mdm3_state_after", live.get("after_mdm3_state", "")],
        ["mss_crash_count", f"{live.get('before_mss_crash_count', '')}->{live.get('after_mss_crash_count', '')}"],
        ["mdm3_crash_count", f"{live.get('before_mdm3_crash_count', '')}->{live.get('after_mdm3_crash_count', '')}"],
    ]
    marker_rows = [
        [name, str(hold_counts.get(name, 0)), str(after_counts.get(name, 0))]
        for name, _ in DMESG_PATTERNS
    ]
    return "\n".join([
        "# V729 Modem-only Hold Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- subsys_modem_open_attempted: `{manifest['subsys_modem_open_attempted']}`",
        f"- subsys_modem_open_executed: `{manifest['subsys_modem_open_executed']}`",
        f"- esoc0_open_executed: `{manifest['esoc0_open_executed']}`",
        f"- subsystem_state_writes_executed: `{manifest['subsystem_writes_executed']}`",
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
        markdown_table(["marker", "hold", "after"], marker_rows),
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
        "cycle": "v729",
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
        "subsys_modem_open_attempted": bool(live.get("holder_started")),
        "subsys_modem_open_executed": live.get("holder_open_rc_after") == "0",
        "esoc0_node_created": False,
        "esoc0_open_executed": False,
        "subsystem_writes_executed": False,
        "module_load_unload_executed": False,
        "cnss_daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    latest = repo_path("tmp/wifi/latest-v729-modem-only-hold.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"subsys_modem_open_attempted: {manifest['subsys_modem_open_attempted']}")
    print(f"subsys_modem_open_executed: {manifest['subsys_modem_open_executed']}")
    print(f"esoc0_open_executed: {manifest['esoc0_open_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
