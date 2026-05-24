#!/usr/bin/env python3
"""V723 late QRTR/service-locator rearm proof.

This runner checks whether starting only the lower QRTR companion set after a
native boot service-locator timeout can re-arm the CNSS2/SERVREG path.

It may mount `/mnt/system` read-only and selinuxfs, then starts only:

    qrtr-ns -> pd-mapper -> rmt_storage -> tftp_server

It does not start CNSS daemon, service-manager, Wi-Fi HAL, wificond,
supplicant, hostapd, scan/connect, DHCP, route changes, credentials, or
external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import socket
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v723-qrtr-servloc-rearm")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 60.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "547232ddb352740bb7a7f1d0f9116162584e34a536b9d9b77869ed8d838e7c89"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v121"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
APPROVAL_PHRASE = (
    "approve v723 QRTR/service-locator late rearm proof only; "
    "no CNSS daemon, no service-manager, no Wi-Fi HAL start, "
    "no scan/connect/link-up, no DHCP and no external ping"
)
MODE = "wifi-companion-android-order-post-sysmon-observer-start-only"
EXPECTED_ORDER = "qrtr_ns,pd_mapper,rmt_storage,tftp_server"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_TS_RE = re.compile(r"\[\s*(?P<ts>\d+(?:\.\d+)?)\]")
MARKERS: dict[str, re.Pattern[str]] = {
    "servloc_timeout": re.compile(r"servloc:.*wait for locator service timed out|Unable to connect to service locator", re.I),
    "service_locator_connected": re.compile(r"service_locator_new_server: Connection established with the Service locator", re.I),
    "service_notifier_180": re.compile(r"service-notifier:.*\b180 service\b|msm/modem/wlan_pd|wlan_pd", re.I),
    "service_notifier_74": re.compile(r"service-notifier:.*\b74 service\b", re.I),
    "pd_notifier": re.compile(r"\bpd[_ -]?notifier\b|\bserver[_ -]?arrive\b", re.I),
    "cnss_netlink": re.compile(r"wlan_cnss.*netlink|cnss.*netlink", re.I),
    "qca6390": re.compile(r"\bqca6390\b", re.I),
    "wlfw": re.compile(r"\bWLFW\b|wlfw[_ -]?start|service\s+69", re.I),
    "bdf": re.compile(r"\bBDF\b|bdwlan|regdb", re.I),
    "fw_ready": re.compile(r"WLAN FW is ready|fw_ready", re.I),
    "wlan0": re.compile(r"\bwlan0\b", re.I),
    "kernel_warning": re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put: esoc0 count:0", re.I),
}


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
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--companion-runtime-sec", type=int, default=8)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def bridge_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def write_capture(store: EvidenceStore, name: str, capture_text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, capture_text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    validate_device_command(args, command)
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


def validate_device_command(args: argparse.Namespace, command: list[str]) -> None:
    joined = " ".join(command)
    forbidden = (
        "cnss-daemon",
        "servicemanager",
        "hwservicemanager",
        "vndservicemanager",
        "android.hardware.wifi",
        "wificond",
        "wpa_supplicant",
        "hostapd",
        "qcwlanstate",
        "svc wifi",
        "dhcp",
        "ip route",
        " ping ",
    )
    if command[:2] == ["run", args.helper] and command[2:] == ["--help"]:
        return
    if command[:2] == ["run", args.helper]:
        if MODE not in command:
            raise RuntimeError(f"unexpected helper mode in V723: {joined}")
        allowed_tokens = {
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
        }
        unexpected = [token for token in command if token not in allowed_tokens]
        if unexpected:
            raise RuntimeError(f"unexpected helper token in V723: {unexpected}")
        return
    for term in forbidden:
        if term in joined:
            raise RuntimeError(f"forbidden Wi-Fi bring-up command term in V723: {joined}")
    if command in (
        ["version"],
        ["status"],
        ["selftest"],
        ["mountsystem", "ro"],
        ["cat", "/proc/mounts"],
        ["cat", "/sys/module/firmware_class/parameters/path"],
        ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"],
        ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"],
        ["stat", "/sys/fs/selinux/status"],
        ["stat", "/mnt/system/system"],
    ):
        return
    if command[:3] == ["run", args.toybox, "dmesg"]:
        return
    if command[:3] == ["run", args.toybox, "sha256sum"] and command[3:] == [args.helper]:
        return
    if command == ["run", args.toybox, "mount", "-t", "selinuxfs", "selinuxfs", "/sys/fs/selinux"]:
        return
    if command == ["run", args.toybox, "cat", "/proc/net/qrtr"]:
        return
    if command == ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"]:
        return
    raise RuntimeError(f"unexpected device command in V723: {joined}")


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


def parse_key_values(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in text.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        if key:
            parsed[key] = value.strip().strip('"')
    return parsed


def dmesg_timestamp(line: str) -> float | None:
    match = DMESG_TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def clean_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def last_dmesg_timestamp(text: str) -> float | None:
    last = None
    for line in text.splitlines():
        ts = dmesg_timestamp(clean_line(line))
        if ts is not None:
            last = ts
    return last


def dmesg_delta(before: str, after: str) -> str:
    before_ts = last_dmesg_timestamp(before)
    if before_ts is None:
        return after
    lines = []
    for raw in after.splitlines():
        line = clean_line(raw)
        ts = dmesg_timestamp(line)
        if ts is not None and ts > before_ts:
            lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def marker_scan(text: str) -> dict[str, Any]:
    events: dict[str, list[dict[str, Any]]] = {name: [] for name in MARKERS}
    focus: list[str] = []
    for index, raw in enumerate(text.splitlines()):
        line = clean_line(raw)
        if not line:
            continue
        matched = False
        for name, pattern in MARKERS.items():
            if pattern.search(line):
                events[name].append({"index": index, "ts": dmesg_timestamp(line), "line": line[:360]})
                matched = True
        if matched:
            focus.append(line[:360])
    return {
        "counts": {name: len(rows) for name, rows in events.items()},
        "first_ts": {name: rows[0]["ts"] for name, rows in events.items() if rows and rows[0]["ts"] is not None},
        "first_lines": {name: rows[0]["line"] for name, rows in events.items() if rows},
        "focus_tail": focus[-120:],
    }


def int_key(keys: dict[str, str], key: str) -> int:
    try:
        return int(keys.get(key, "0"))
    except ValueError:
        return 0


def helper_surface(helper_text: str) -> dict[str, Any]:
    keys = parse_key_values(helper_text)
    return {
        "helper_status": keys.get("helper_status", ""),
        "setup_error": keys.get("setup_error", ""),
        "mode": keys.get("mode", ""),
        "order": keys.get("wifi_companion_start.order", ""),
        "child_started": int_key(keys, "wifi_companion_start.child_started"),
        "all_observable": int_key(keys, "wifi_companion_start.all_observable"),
        "all_postflight_safe": int_key(keys, "wifi_companion_start.all_postflight_safe"),
        "timed_out": int_key(keys, "wifi_companion_start.timed_out"),
        "result": keys.get("wifi_companion_start.result", ""),
        "reason": keys.get("wifi_companion_start.reason", ""),
        "net_after_qipcrtr": int_key(keys, "wifi_companion_start.net_after_spawn.qipcrtr_present"),
        "net_window_qipcrtr": int_key(keys, "wifi_companion_start.net_window.qipcrtr_present"),
        "net_after_cleanup_qipcrtr": int_key(keys, "wifi_companion_start.net_after_cleanup.qipcrtr_present"),
        "scan_connect_linkup": int_key(keys, "wifi_companion_start.scan_connect_linkup"),
        "external_ping": int_key(keys, "wifi_companion_start.external_ping"),
        "cnss_daemon": int_key(keys, "wifi_companion_start.cnss_daemon"),
        "service_manager": int_key(keys, "wifi_companion_start.service_manager"),
        "wifi_hal": int_key(keys, "wifi_companion_start.wifi_hal"),
        "wificond": int_key(keys, "wifi_companion_start.wificond"),
    }


def build_preflight(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "bridge_port_open": bridge_port_open(args.host, args.port),
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": bool(args.apply),
        "assume_yes": bool(args.assume_yes),
        "companion_runtime_sec": args.companion_runtime_sec,
        "runtime_valid": 1 <= args.companion_runtime_sec <= 30,
        "helper": args.helper,
        "helper_sha256": args.helper_sha256,
        "helper_marker": args.helper_marker,
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def collect_live(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    store.mkdir("native")
    run_step(args, store, steps, "version", ["version"], 15.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "selftest", ["selftest"], 25.0)
    run_step(args, store, steps, "mountsystem-ro", ["mountsystem", "ro"], 25.0)
    run_step(args, store, steps, "selinuxfs-stat-before", ["stat", "/sys/fs/selinux/status"], 10.0)
    if not step_payload(steps, "selinuxfs-stat-before") or "No such file" in step_payload(steps, "selinuxfs-stat-before"):
        run_step(
            args,
            store,
            steps,
            "mount-selinuxfs",
            ["run", args.toybox, "mount", "-t", "selinuxfs", "selinuxfs", "/sys/fs/selinux"],
            20.0,
        )
    run_step(args, store, steps, "selinuxfs-stat-after", ["stat", "/sys/fs/selinux/status"], 10.0)
    run_step(args, store, steps, "system-root-stat", ["stat", "/mnt/system/system"], 10.0)
    run_step(args, store, steps, "sha-helper", ["run", args.toybox, "sha256sum", args.helper], 15.0)
    run_step(args, store, steps, "helper-usage", ["run", args.helper, "--help"], 25.0)
    run_step(args, store, steps, "firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0)
    run_step(args, store, steps, "mss-state-before", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
    run_step(args, store, steps, "mdm3-state-before", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"], 10.0)
    before = run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    helper = run_step(args, store, steps, "late-qrtr-companion", helper_command(args), args.companion_runtime_sec + 70.0)
    after = run_step(args, store, steps, "dmesg-after", ["run", args.toybox, "dmesg"], 60.0)
    run_step(args, store, steps, "proc-net-qrtr-after", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0)
    run_step(args, store, steps, "ps-after", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    run_step(args, store, steps, "mss-state-after", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
    run_step(args, store, steps, "mdm3-state-after", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"], 10.0)
    delta = dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
    store.write_text("native/dmesg-delta.txt", delta)
    live = {
        "dmesg_before": marker_scan(str(before.get("payload") or "")),
        "dmesg_after": marker_scan(str(after.get("payload") or "")),
        "dmesg_delta": marker_scan(delta),
        "helper": helper_surface(str(helper.get("payload") or "")),
        "helper_ok": bool(helper.get("ok")),
        "helper_rc": helper.get("rc"),
        "helper_status": helper.get("status"),
        "mss_state_before": step_payload(steps, "mss-state-before").strip(),
        "mdm3_state_before": step_payload(steps, "mdm3-state-before").strip(),
        "mss_state_after": step_payload(steps, "mss-state-after").strip(),
        "mdm3_state_after": step_payload(steps, "mdm3-state-after").strip(),
        "firmware_class_path": step_payload(steps, "firmware-class-path").strip(),
        "proc_net_qrtr_after_present": bool(step_payload(steps, "proc-net-qrtr-after").strip())
        and "No such file" not in step_payload(steps, "proc-net-qrtr-after"),
    }
    return steps, live


def helper_contract_ok(args: argparse.Namespace, steps: list[dict[str, Any]]) -> bool:
    sha = step_payload(steps, "sha-helper")
    usage = step_payload(steps, "helper-usage")
    return args.helper_sha256 in sha and args.helper_marker in usage and MODE in usage


def build_checks(args: argparse.Namespace,
                 preflight: dict[str, Any],
                 steps: list[dict[str, Any]],
                 live: dict[str, Any] | None) -> list[Check]:
    checks: list[Check] = []
    add_check(
        checks,
        "scope-no-wifi-bringup",
        "pass",
        "blocker",
        "runner starts only qrtr-ns/pd-mapper/rmt_storage/tftp_server below CNSS/HAL/connect",
        [],
        "keep credentials and external ping blocked until wlan0 exists",
    )
    if args.command == "run":
        add_check(
            checks,
            "approval",
            "pass" if approved(args) else "blocked",
            "blocker",
            "exact V723 approval phrase plus --apply --assume-yes required",
            [],
            "rerun with exact V723 approval",
        )
    add_check(
        checks,
        "runtime-limit",
        "pass" if preflight.get("runtime_valid") else "blocked",
        "blocker",
        f"companion_runtime_sec={args.companion_runtime_sec}",
        [],
        "use a 1..30 second bounded companion window",
    )
    if live is None:
        return checks
    version = step_payload(steps, "version")
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    helper = live.get("helper") or {}
    delta_counts = (live.get("dmesg_delta") or {}).get("counts") or {}
    add_check(
        checks,
        "native-baseline",
        "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked",
        "blocker",
        f"expect_version={args.expect_version}",
        [line for line in version.splitlines() if "A90 Linux init" in line][:2],
        "restore current native baseline before interpreting V723",
    )
    add_check(
        checks,
        "system-root-and-selinuxfs",
        "pass" if "No such file" not in step_payload(steps, "system-root-stat") and "No such file" not in step_payload(steps, "selinuxfs-stat-after") else "blocked",
        "blocker",
        "read-only system root and selinuxfs status must be visible for execns helper",
        [],
        "run mountsystem ro and V401 selinuxfs mount before helper",
    )
    add_check(
        checks,
        "helper-v121-contract",
        "pass" if helper_contract_ok(args, steps) else "blocked",
        "blocker",
        f"helper_marker={args.helper_marker}",
        [args.helper_sha256, args.helper_marker, MODE],
        "deploy helper v121 before V723",
    )
    add_check(
        checks,
        "helper-lower-only-contract",
        "pass" if helper.get("order") == EXPECTED_ORDER and helper.get("child_started") == 4 else "blocked",
        "blocker",
        f"order={helper.get('order')} child_started={helper.get('child_started')}",
        [],
        "inspect helper mode before rerun",
    )
    add_check(
        checks,
        "helper-cleanup-safe",
        "pass" if helper.get("all_postflight_safe") == 1 and helper.get("all_observable") == 1 else "blocked",
        "blocker",
        f"all_observable={helper.get('all_observable')} all_postflight_safe={helper.get('all_postflight_safe')}",
        [],
        "reboot cleanup before any further Wi-Fi proof if unsafe",
    )
    add_check(
        checks,
        "no-cnss-hal-connect",
        "pass" if all(int(helper.get(key) or 0) == 0 for key in ("cnss_daemon", "service_manager", "wifi_hal", "wificond", "scan_connect_linkup", "external_ping")) else "blocked",
        "blocker",
        json.dumps({key: helper.get(key) for key in ("cnss_daemon", "service_manager", "wifi_hal", "wificond", "scan_connect_linkup", "external_ping")}, sort_keys=True),
        [],
        "stop if V723 scope accidentally crossed into CNSS/HAL/connect",
    )
    add_check(
        checks,
        "servloc-rearm-observed",
        "pass" if int(delta_counts.get("service_locator_connected", 0)) > 0 else "warn",
        "info",
        f"delta_service_locator_connected={delta_counts.get('service_locator_connected', 0)}",
        [],
        "if absent, boot-time QRTR path still unproven",
    )
    add_check(
        checks,
        "service180-after-rearm",
        "pass" if int(delta_counts.get("service_notifier_180", 0)) > 0 else "warn",
        "info",
        f"delta_service180={delta_counts.get('service_notifier_180', 0)}",
        [],
        "if absent, late QRTR rearm does not restore WLAN-PD publication",
    )
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(args: argparse.Namespace,
           preflight: dict[str, Any],
           checks: list[Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v723-qrtr-servloc-rearm-plan-ready",
            True,
            "plan-only; no device command executed",
            "run preflight, then approved V723 lower-only late rearm proof",
            False,
        )
    if args.command == "preflight":
        if not preflight.get("runtime_valid"):
            return (
                "v723-qrtr-servloc-rearm-preflight-blocked",
                False,
                "companion runtime must be 1..30 seconds",
                "rerun with bounded runtime",
                False,
            )
        return (
            "v723-qrtr-servloc-rearm-preflight-ready",
            True,
            f"bridge_port_open={preflight.get('bridge_port_open')}",
            "run approved V723 live proof",
            False,
        )
    blocked = blockers(checks)
    if blocked:
        if blocked == ["approval"]:
            return (
                "v723-qrtr-servloc-rearm-approval-required",
                True,
                "approval missing; no live command executed",
                "rerun with exact V723 approval",
                False,
            )
        return (
            "v723-qrtr-servloc-rearm-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "fix blocked setup before interpreting V723",
            live is not None,
        )
    if live is None:
        return "v723-qrtr-servloc-rearm-missing-live", False, "live missing", "inspect runner failure", False
    delta_counts = (live.get("dmesg_delta") or {}).get("counts") or {}
    after_counts = (live.get("dmesg_after") or {}).get("counts") or {}
    if int(delta_counts.get("kernel_warning", 0)) > 0:
        return (
            "v723-kernel-warning",
            False,
            "kernel warning appeared during lower-only rearm",
            "reboot cleanup and inspect dmesg before retry",
            True,
        )
    if any(int(after_counts.get(name, 0)) > 0 for name in ("wlfw", "bdf", "fw_ready", "wlan0")):
        return (
            "v723-wlfw-or-wlan0-progressed",
            True,
            f"post-rearm progression counts={after_counts}",
            "move to wlan0 readiness before scan/connect",
            True,
        )
    if int(delta_counts.get("service_notifier_180", 0)) > 0 or int(delta_counts.get("service_notifier_74", 0)) > 0:
        return (
            "v723-late-rearm-service-positive-no-wlfw",
            True,
            f"late rearm produced service notifier delta={delta_counts}",
            "continue with CNSS2 callback/power edge, still below HAL/connect",
            True,
        )
    if int(delta_counts.get("service_locator_connected", 0)) > 0:
        return (
            "v723-late-servloc-rearm-no-wlanpd",
            True,
            f"service-locator reconnected but service180/74 stayed absent; delta={delta_counts}",
            "move QRTR/service-locator companion earlier in boot before SERVREG timeout",
            True,
        )
    return (
        "v723-late-rearm-no-servloc-change",
        True,
        f"late rearm did not produce service-locator or WLAN-PD markers; delta={delta_counts}",
        "plan boot-time QRTR/service-locator proof before servloc timeout",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    live = manifest.get("live") or {}
    helper = live.get("helper") or {}
    delta = live.get("dmesg_delta") or {}
    rows = [
        [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
        for check in checks
    ]
    helper_rows = [[key, str(value)] for key, value in sorted(helper.items())]
    count_rows = [[key, str(value)] for key, value in sorted((delta.get("counts") or {}).items())]
    lines = [
        "# V723 QRTR/Service-Locator Late Rearm",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_linkup_executed: `{manifest['scan_connect_linkup_executed']}`",
        f"- dhcp_or_external_ping_executed: `{manifest['dhcp_or_external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], rows) if rows else "- none",
        "",
        "## Helper Surface",
        "",
        markdown_table(["key", "value"], helper_rows) if helper_rows else "- not executed",
        "",
        "## Dmesg Delta Counts",
        "",
        markdown_table(["marker", "count"], count_rows) if count_rows else "- not collected",
        "",
        "## Guardrails",
        "",
    ]
    lines.extend(f"- {item}" for item in manifest["guardrails"])
    return "\n".join(lines) + "\n"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    preflight = build_preflight(args)
    steps: list[dict[str, Any]] = []
    live: dict[str, Any] | None = None
    if args.command == "run" and approved(args) and preflight.get("runtime_valid"):
        steps, live = collect_live(args, store)
    checks = build_checks(args, preflight, steps, live)
    decision, pass_ok, reason, next_step, live_executed = decide(args, preflight, checks, live)
    return {
        "generated_at": now_iso(),
        "cycle": "v723",
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "preflight": preflight,
        "checks": [asdict(check) for check in checks],
        "steps": [{key: value for key, value in step.items() if key != "payload"} for step in steps],
        "live": live or {},
        "approval_phrase": APPROVAL_PHRASE,
        "approval_supplied": approved(args),
        "device_commands_executed": live_executed,
        "device_mutations": live_executed,
        "daemon_start_executed": live_executed,
        "cnss_daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_linkup_executed": False,
        "dhcp_or_external_ping_executed": False,
        "credentials_used": False,
        "guardrails": [
            "starts only qrtr-ns, pd-mapper, rmt_storage, and tftp_server through helper mode",
            "does not start CNSS daemon or Android service managers",
            "does not start Wi-Fi HAL, wificond, supplicant, or hostapd",
            "does not scan, connect, run DHCP, change routes, use credentials, or ping externally",
            "helper window is bounded and postflight cleanup-safe is required",
        ],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"dhcp_or_external_ping_executed: {manifest['dhcp_or_external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
