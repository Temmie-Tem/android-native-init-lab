#!/usr/bin/env python3
"""V596 global firmware modem-holder plus companion start-only proof.

This proof keeps only `subsys_modem` open while Android-style global firmware
mounts are active, then starts the bounded companion stack. It intentionally
does not close the modem fd during the live window; reboot is the cleanup
boundary. It does not start service-manager, Wi-Fi HAL, qcwlanstate,
scan/connect, DHCP, routing, credentials, or external ping.
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

import native_wifi_companion_start_only_v527 as companion
import native_wifi_firmware_mount_parity_v584 as mountv
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90ctl import run_cmdv1_command
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v596-modem-holder-companion-proof")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "916b5c68a3357c79604db4532b457e30fcb9a70c99aaabb6f95519af138abd29"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v100"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_V490_MANIFEST = Path("tmp/wifi/v596-v490-current-run/manifest.json")
DEFAULT_V525_MANIFEST = companion.DEFAULT_V525_MANIFEST
FIRMWARE_CLASS_PATH = "/vendor/firmware_mnt/image"
APPROVAL_PHRASE = (
    "approve v596 modem holder companion proof only; "
    "no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)
GLOBAL_MODEM_BLOB_PATHS = (
    "/vendor/firmware_mnt/image/modem.b00",
    "/vendor/firmware-modem/image/modem.b00",
    "/firmware/image/modem.b00",
)
FORBIDDEN_TERMS = (
    "qcwlanstate",
    "IWifi",
    "wpa_supplicant",
    "hostapd",
    "wificond",
    "svc wifi",
    " ping ",
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_TS_RE = re.compile(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]")
FOCUS_PATTERNS = {
    "qrtr_rx": re.compile(r"qrtr: Modem QMI Readiness RX", re.IGNORECASE),
    "qrtr_tx": re.compile(r"qrtr: Modem QMI Readiness TX", re.IGNORECASE),
    "sysmon_qmi": re.compile(r"sysmon-qmi", re.IGNORECASE),
    "service_notifier": re.compile(r"service-notifier", re.IGNORECASE),
    "wlan_pd": re.compile(r"wlan[_-]pd|msm/modem/wlan_pd", re.IGNORECASE),
    "qmi_server_connected": re.compile(r"icnss_qmi: QMI Server Connected", re.IGNORECASE),
    "wlfw": re.compile(r"\bWLFW\b|wlfw", re.IGNORECASE),
    "bdf": re.compile(r"BDF file|bdwlan\.bin|regdb\.bin", re.IGNORECASE),
    "wlan_fw_ready": re.compile(r"WLAN FW is ready", re.IGNORECASE),
    "wlan0": re.compile(r"\bwlan0\b", re.IGNORECASE),
    "kernel_warning": re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put: esoc0 count:0", re.IGNORECASE),
}
ADVANCE_MARKERS = (
    "qrtr_tx",
    "sysmon_qmi",
    "service_notifier",
    "wlan_pd",
    "qmi_server_connected",
    "wlfw",
    "bdf",
    "wlan_fw_ready",
    "wlan0",
)


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
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v490-manifest", type=Path, default=DEFAULT_V490_MANIFEST)
    parser.add_argument("--v525-manifest", type=Path, default=DEFAULT_V525_MANIFEST)
    parser.add_argument("--holder-sec", type=int, default=90)
    parser.add_argument("--companion-runtime-sec", type=int, default=18)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=35.0)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=2.0)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"))
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def validate_command(command: list[str]) -> None:
    joined = " " + " ".join(command) + " "
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden command term in V596: {joined.strip()}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    validate_command(command)
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    steps.append(item)
    return item


def skipped_step(store: EvidenceStore,
                 steps: list[dict[str, Any]],
                 name: str,
                 reason: str) -> dict[str, Any]:
    text = f"skipped: {reason}\n"
    item = {
        "name": name,
        "command": "<skipped>",
        "ok": False,
        "rc": None,
        "status": "skipped",
        "duration_sec": 0.0,
        "text": text,
        "error": reason,
        "file": write_capture(store, name, text),
        "payload": text,
    }
    steps.append(item)
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def parse_dev(text: str) -> tuple[str, str] | None:
    match = re.search(r"\b([0-9]+):([0-9]+)\b", text)
    return (match.group(1), match.group(2)) if match else None


def path_exists(text: str) -> bool:
    lowered = text.lower()
    return "no such file" not in lowered and "errno=2" not in lowered and "not found" not in lowered


def capture_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    mount_steps: list[dict[str, Any]] = []
    mount_preflight = mountv.capture_preflight(args, store, mount_steps)
    steps.extend(mount_steps)
    run_step(args, store, steps, "firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0)
    run_step(args, store, steps, "subsys-modem-dev", ["cat", "/sys/class/subsys/subsys_modem/dev"], 10.0)
    run_step(args, store, steps, "mss-state", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
    run_step(args, store, steps, "mdm3-state", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"], 10.0)
    run_step(args, store, steps, "sha-helper", ["run", args.toybox, "sha256sum", args.helper], 20.0)
    run_step(args, store, steps, "helper-usage", ["run", args.helper, "--help"], 20.0)
    run_step(args, store, steps, "ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    run_step(args, store, steps, "proc-net-dev", ["cat", "/proc/net/dev"], 10.0)
    run_step(args, store, steps, "proc-net-qrtr", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0)
    return mount_preflight


def helper_ready(args: argparse.Namespace, steps: list[dict[str, Any]]) -> bool:
    helper_sha = step_payload(steps, "sha-helper")
    helper_usage = step_payload(steps, "helper-usage")
    return args.helper_sha256 in helper_sha and args.helper_marker in helper_usage and "wifi-companion-start-only" in helper_usage


def build_checks(args: argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V596 preflight")
        return checks
    version = step_payload(steps, "version")
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    firmware_path = step_payload(steps, "firmware-class-path").strip()
    modem_dev = parse_dev(step_payload(steps, "subsys-modem-dev"))
    ps = step_payload(steps, "ps")
    netdev = step_payload(steps, "proc-net-dev")
    process_hits = [line.strip() for line in ps.splitlines() if companion.PROCESS_RE.search(line)]
    holder_hits = [line.strip() for line in ps.splitlines() if "a90-v596-subsys-modem" in line]
    wifi_hits = [line.strip() for line in netdev.splitlines() if companion.WIFI_RE.search(line)]
    pre_hits = mount_preflight.get("pre_mount_hits") or {}
    already_mounted = [target for target in mountv.PARTITION_TARGETS.values() if pre_hits.get(target)]
    parts = mount_preflight.get("partitions") or {}
    shim_required = bool(mount_preflight.get("vendor_rootfs_shim_required"))
    shim_allowed = bool(mount_preflight.get("vendor_rootfs_shim_allowed_target"))
    v490_fresh, v490_detail = companion.v490_current_for_boot(v490, status) if v490.get("exists") else (False, "manifest-missing")
    v525_summary = v525.get("android_summary") or {}

    add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:2],
              "restore native baseline before V596")
    add_check(checks, "v490-current-policy-load", "pass" if v490.get("decision") == "v490-selinux-policy-load-proof-pass" and v490.get("policy_load_executed") is True and v490_fresh else "blocked", "blocker",
              f"decision={v490.get('decision')} policy_load={v490.get('policy_load_executed')} fresh={v490_fresh} {v490_detail}",
              [str(v490.get("path"))], "run approved V490 after current boot before V596")
    add_check(checks, "v525-identity-contract", "pass" if v525.get("decision") == "v525-companion-identity-captured" and v525.get("pass") is True and v525_summary.get("all_required_process_identities") else "blocked", "blocker",
              f"decision={v525.get('decision')} pass={v525.get('pass')} identities={v525_summary.get('all_required_process_identities')}",
              [str(v525.get("path"))], "capture Android companion identities before native replay")
    add_check(checks, "helper-v100-ready", "pass" if helper_ready(args, steps) else "blocked", "blocker",
              f"sha={args.helper_sha256} marker={args.helper_marker}", [args.helper_sha256, args.helper_marker],
              "deploy helper v100 before V596")
    add_check(checks, "firmware-class-path-android-equivalent", "pass" if firmware_path == FIRMWARE_CLASS_PATH else "blocked", "blocker",
              f"path={firmware_path or 'missing'}", [firmware_path], "preserve Android-equivalent firmware_class path")
    add_check(checks, "apnhlos-modem-partitions-resolved", "pass" if "apnhlos" in parts and "modem" in parts else "blocked", "blocker",
              f"apnhlos={parts.get('apnhlos')} modem={parts.get('modem')}", [], "resolve firmware partitions")
    add_check(checks, "global-firmware-targets-not-mounted", "pass" if not already_mounted else "blocked", "blocker",
              f"already_mounted={already_mounted}", sum((mount_preflight.get("pre_mount_lines") or {}).values(), []),
              "inspect existing firmware mounts before V596")
    add_check(checks, "vendor-rootfs-shim-safe", "pass" if not shim_required or shim_allowed else "blocked", "blocker",
              f"required={shim_required} target={mount_preflight.get('vendor_symlink_target')} allowed={shim_allowed}", [],
              "only replace known native /vendor symlink")
    add_check(checks, "subsys-modem-cdev-visible", "pass" if modem_dev else "blocked", "blocker",
              f"dev={modem_dev}", [], "subsys_modem char dev must be visible")
    add_check(checks, "no-active-target-processes", "pass" if not process_hits and not holder_hits else "blocked", "blocker",
              f"process_count={len(process_hits)} holder_count={len(holder_hits)}", (process_hits + holder_hits)[:8],
              "cleanup residual companion/holder processes before V596")
    add_check(checks, "no-wifi-link-surface", "pass" if not wifi_hits else "blocked", "blocker",
              f"wifi_hits={len(wifi_hits)}", wifi_hits[:8], "if wlan0 already exists, move to scan-only")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def proof_id() -> str:
    return "v596-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def holder_script(args: argparse.Namespace, major: str, minor: str, label: str) -> str:
    node = f"/tmp/a90-v596-subsys-modem-{label}"
    status = f"/tmp/a90-v596-holder-{label}.status"
    pidfile = f"/tmp/a90-v596-holder-{label}.pid"
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
        f"  sleep {max(args.holder_sec, args.companion_runtime_sec + 45)}",
        ") &",
        "holder_pid=$!",
        "echo \"$holder_pid\" > \"$pidfile\"",
        "for i in 1 2 3 4 5 6 7 8 9 10; do",
        "  test -s \"$status\" && break",
        "  sleep 1",
        "done",
        "echo v596.holder.node=$node",
        "echo v596.holder.pid=$holder_pid",
        f"echo v596.holder.status=$({args.toybox} cat \"$status\" 2>/dev/null || true)",
        f"{args.toybox} ps -A -o pid,stat,comm,args | {args.toybox} grep \"$holder_pid\" | {args.toybox} grep -v grep || true",
    ])


def companion_command(args: argparse.Namespace) -> list[str]:
    return [
        "run", args.helper,
        "--system-root", "/mnt/system/system",
        "--vendor-block", "/dev/block/sda29",
        "--vendor-fstype", "ext4",
        "--mode", "wifi-companion-start-only",
        "--null-device-mode", "dev-null",
        "--vndk-apex-alias-mode", "v30-to-system-ext-v30",
        "--linkerconfig-mode", "minimal-vendor",
        "--android-selinux-context-mode", "service-defaults",
        "--timeout-sec", str(args.companion_runtime_sec),
        "--allow-cnss-start-only",
        "--allow-wifi-companion-start-only",
    ]


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
    lines = []
    for raw_line in after.splitlines():
        line = ANSI_RE.sub("", raw_line).strip()
        match = DMESG_TS_RE.match(line)
        if match and float(match.group(1)) > before_last:
            lines.append(raw_line)
    return "\n".join(lines) + ("\n" if lines else "")


def marker_summary(text: str) -> dict[str, Any]:
    lines = [line for line in text.splitlines() if any(pattern.search(line) for pattern in FOCUS_PATTERNS.values())]
    counts = {name: len([line for line in lines if pattern.search(line)]) for name, pattern in FOCUS_PATTERNS.items()}
    return {
        "counts": counts,
        "advance_markers": [name for name in ADVANCE_MARKERS if counts.get(name, 0) > 0],
        "focus_tail": lines[-120:],
    }


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
            "advance_markers": summary.get("advance_markers", []),
        })
        if summary["counts"].get("qrtr_rx", 0) > 0:
            write_capture(store, "wait-qrtr-rx-delta", delta)
            return {
                "seen": True,
                "elapsed_sec": time.monotonic() - started,
                "attempts": attempts,
                "delta_file": "native/wait-qrtr-rx-delta.txt",
                "markers": summary,
            }
        time.sleep(max(0.5, args.qrtr_rx_poll_sec))
    write_capture(store, "wait-qrtr-rx-delta", last_delta)
    return {
        "seen": False,
        "elapsed_sec": time.monotonic() - started,
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
    for _ in range(60):
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
        "wait_sec": time.monotonic() - started,
        "version_seen": args.expect_version in version_text,
        "status_healthy": "fail=0" in status_text,
    }


def run_live(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    label = proof_id()
    base_dir = mountv.PROOF_BASE_PREFIX.replace("v584", "v596") + label
    before = run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    for name, command, timeout in mountv.build_mount_commands(mount_preflight, base_dir):
        run_step(args, store, steps, f"v596-{name}", command, timeout)
    run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0)
    run_step(args, store, steps, "mounted-firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0)
    for path in GLOBAL_MODEM_BLOB_PATHS:
        run_step(args, store, steps, f"mounted-stat-{safe_name(path)}", ["stat", path], 10.0)
    dev = parse_dev(step_payload(steps, "subsys-modem-dev"))
    if not dev:
        raise RuntimeError("subsys_modem dev missing after preflight")
    script = holder_script(args, dev[0], dev[1], label)
    write_capture(store, "holder-script-redacted", script)
    holder = run_step(args, store, steps, "start-modem-holder", ["run", args.busybox, "sh", "-c", script], 20.0)
    run_step(args, store, steps, "mss-state-after-holder", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
    run_step(args, store, steps, "rpmsg-after-holder", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0)
    qrtr_wait = wait_for_qrtr_rx(args, store, steps, str(before.get("payload") or ""))
    if qrtr_wait.get("seen"):
        live = run_step(args, store, steps, "companion-start-only-with-holder", companion_command(args), args.companion_runtime_sec + 60.0)
        companion_executed = True
    else:
        live = skipped_step(store, steps, "companion-start-only-with-holder", "QRTR RX marker was not observed after subsys_modem holder open")
        companion_executed = False
    run_step(args, store, steps, "mss-state-after-companion", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
    run_step(args, store, steps, "mdm3-state-after-companion", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"], 10.0)
    run_step(args, store, steps, "rpmsg-after-companion", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0)
    run_step(args, store, steps, "proc-net-qrtr-after-companion", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0)
    run_step(args, store, steps, "ps-before-reboot", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    after = run_step(args, store, steps, "dmesg-after-companion", ["run", args.toybox, "dmesg"], 60.0)
    delta = dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
    write_capture(store, "dmesg-delta", delta)
    reboot = reboot_and_wait(args, store)
    mounted = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    modem_blob_visible = {
        path: path_exists(step_payload(steps, f"mounted-stat-{safe_name(path)}"))
        for path in GLOBAL_MODEM_BLOB_PATHS
    }
    keys = companion.parse_keys(str(live.get("payload") or ""))
    return {
        "base": base_dir,
        "holder_started": (
            holder.get("ok") is True
            and (
                "v596.holder.status=opened" in str(holder.get("payload") or "")
                or qrtr_wait.get("seen") is True
                or step_payload(steps, "mss-state-after-holder").strip() == "ONLINE"
            )
        ),
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": modem_blob_visible,
        "mss_after_holder": step_payload(steps, "mss-state-after-holder").strip(),
        "qrtr_rx_wait": qrtr_wait,
        "companion_executed": companion_executed,
        "mss_after_companion": step_payload(steps, "mss-state-after-companion").strip(),
        "mdm3_after_companion": step_payload(steps, "mdm3-state-after-companion").strip(),
        "rpmsg_after_companion": step_payload(steps, "rpmsg-after-companion"),
        "proc_qrtr_after_companion": step_payload(steps, "proc-net-qrtr-after-companion"),
        "companion_keys": keys,
        "helper_result": keys.get("wifi_companion_start.result", "missing"),
        "all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe") == "1",
        "all_observable": keys.get("wifi_companion_start.all_observable") == "1",
        "dmesg_delta": delta,
        "markers": marker_summary(delta),
        "reboot_cleanup": reboot,
    }


def decide(args: argparse.Namespace,
           checks: list[Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v596-modem-holder-companion-plan-ready", True, "plan-only; no device command executed", "run V401/V490 current preconditions, then V596 preflight", False
    blocked = blockers(checks)
    if blocked:
        return "v596-modem-holder-companion-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V596", False
    if args.command == "preflight":
        return "v596-modem-holder-companion-preflight-ready", True, "preflight ready; live run needs approval and uses reboot cleanup", "run V596 live proof", False
    if not approved(args):
        return "v596-modem-holder-companion-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V596 approval", False
    if not live:
        return "v596-modem-holder-companion-review-required", False, "missing live result", "inspect runner failure", True
    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v596-modem-holder-companion-reboot-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", True
    markers = live.get("markers") or {}
    counts = markers.get("counts") or {}
    if counts.get("kernel_warning", 0) > 0:
        return "v596-modem-holder-companion-kernel-warning", False, "kernel WARNING/reference mismatch appeared during live window", "do not repeat; inspect dmesg and design safer kernel trigger", True
    if not live.get("holder_started"):
        return "v596-modem-holder-not-started", False, "modem holder did not report opened", "inspect holder transcript", True
    qrtr_wait = live.get("qrtr_rx_wait") or {}
    if not qrtr_wait.get("seen"):
        return "v596-modem-holder-qrtr-rx-missing", False, "QRTR RX was not observed after subsys_modem holder; companion was not started", "inspect modem PIL dmesg before retrying companion", True
    if not live.get("companion_executed"):
        return "v596-companion-skipped", False, "companion was skipped by readiness gate", "inspect QRTR wait evidence", True
    if not live.get("all_postflight_safe"):
        return "v596-companion-cleanup-review", False, f"helper_result={live.get('helper_result')}", "inspect companion transcript before retry", True
    advance = markers.get("advance_markers") or []
    if advance:
        return "v596-modem-holder-companion-readiness-advance", True, "companion under modem holder observed: " + ",".join(advance), "advance toward bounded qcwlanstate/HAL retry; still no scan/connect until next gate", True
    if counts.get("qrtr_rx", 0) > 0:
        return "v596-modem-holder-companion-qrtr-rx-only", True, "modem holder reproduced QRTR RX but companion did not advance to QRTR TX/sysmon/service-notifier", "inspect companion stdout/stderr and missing QRTR namespace routing", True
    return "v596-modem-holder-companion-no-readiness", True, "live proof cleaned by reboot but no lower readiness marker appeared", "inspect dmesg and helper transcript", True


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    live = manifest.get("live") or {}
    live_rows = [
        [key, value]
        for key, value in sorted(live.items())
        if key not in {"dmesg_delta", "rpmsg_after_companion", "proc_qrtr_after_companion", "companion_keys"}
    ]
    return "\n".join([
        "# V596 Modem Holder Companion Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], checks),
        "",
        "## Live",
        "",
        markdown_table(["key", "value"], live_rows) if live_rows else "- none",
        "",
        "## Evidence",
        "",
        f"- `{manifest['out_dir']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    mount_preflight: dict[str, Any] = {}
    live: dict[str, Any] | None = None
    v490 = load_manifest(args.v490_manifest)
    v525 = load_manifest(args.v525_manifest)
    if args.command != "plan":
        mount_preflight = capture_preflight(args, store, steps)
    checks = build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "run" and approved(args) and not blockers(checks):
        live = run_live(args, store, steps, mount_preflight)
    decision, pass_ok, reason, next_step, live_executed = decide(args, checks, live)
    companion_executed = bool(live and live.get("companion_executed"))
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "mount_preflight": mount_preflight,
        "live": live,
        "v490_manifest": {"exists": v490.get("exists"), "path": v490.get("path"), "decision": v490.get("decision"), "pass": v490.get("pass"), "policy_load_executed": v490.get("policy_load_executed"), "generated_at": v490.get("generated_at")},
        "v525_manifest": {"exists": v525.get("exists"), "path": v525.get("path"), "decision": v525.get("decision"), "pass": v525.get("pass")},
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan",
        "device_mutations": live_executed,
        "daemon_start_executed": companion_executed,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "explicitly_not_approved": [
            "service-manager, hwservicemanager, vndservicemanager start",
            "Wi-Fi HAL, wificond, supplicant, or hostapd start",
            "qcwlanstate or sysfs driver-state writes",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
            "boot image changes or partition writes",
        ],
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
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
