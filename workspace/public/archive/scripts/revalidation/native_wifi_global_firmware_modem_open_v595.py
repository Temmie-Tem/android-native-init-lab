#!/usr/bin/env python3
"""V595 global firmware mount plus modem-only subsystem open proof.

This proof temporarily recreates Android's global read-only firmware mounts,
opens only `/sys/class/subsys/subsys_modem` through a temporary char device,
and observes whether modem/QRTR readiness changes without opening `esoc0`.
It does not start daemons, Wi-Fi HAL, qcwlanstate, scan/connect, DHCP,
routing, credentials, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import native_wifi_firmware_mount_parity_v584 as mountv
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v595-global-firmware-modem-open-proof")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
FIRMWARE_CLASS_PATH = "/vendor/firmware_mnt/image"
APPROVAL_PHRASE = (
    "approve v595 global firmware modem-only open proof only; "
    "no daemon start, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)
GLOBAL_MODEM_BLOB_PATHS = (
    "/vendor/firmware_mnt/image/modem.b00",
    "/vendor/firmware-modem/image/modem.b00",
    "/firmware/image/modem.b00",
)
READINESS_RE = re.compile(
    r"Modem QMI Readiness|qcom,glink:modem\.IPCRTR|sysmon-qmi|service-notifier|"
    r"icnss_qmi: QMI Server Connected|WLAN FW is ready|wlan0",
    re.IGNORECASE,
)
PIL_RE = re.compile(r"subsys-pil-tz .*modem:|__subsystem_get\(\): .*modem", re.IGNORECASE)
KERNEL_WARNING_RE = re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put: esoc0 count:0", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_TS_RE = re.compile(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]")
FORBIDDEN_TERMS = (
    "qcwlanstate",
    "IWifi",
    "wpa_supplicant",
    "hostapd",
    "wificond",
    "svc wifi",
    "ping",
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
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
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
    joined = " ".join(command)
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden command term in V595: {joined}")


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


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def parse_dev(text: str) -> tuple[str, str] | None:
    match = re.search(r"\b([0-9]+):([0-9]+)\b", text)
    if not match:
        return None
    return match.group(1), match.group(2)


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
    run_step(args, store, steps, "ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    return mount_preflight


def build_checks(args: argparse.Namespace, steps: list[dict[str, Any]], mount_preflight: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V595 preflight")
        return checks
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    version = step_payload(steps, "version")
    firmware_path = step_payload(steps, "firmware-class-path").strip()
    modem_dev = parse_dev(step_payload(steps, "subsys-modem-dev"))
    ps = step_payload(steps, "ps")
    helper_hits = [line.strip() for line in ps.splitlines() if "a90_android_execns_probe" in line]
    pre_hits = mount_preflight.get("pre_mount_hits") or {}
    already_mounted = [target for target in mountv.PARTITION_TARGETS.values() if pre_hits.get(target)]
    parts = mount_preflight.get("partitions") or {}
    shim_required = bool(mount_preflight.get("vendor_rootfs_shim_required"))
    shim_allowed = bool(mount_preflight.get("vendor_rootfs_shim_allowed_target"))
    add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:2],
              "restore native baseline before V595")
    add_check(checks, "firmware-class-path-android-equivalent", "pass" if firmware_path == FIRMWARE_CLASS_PATH else "blocked", "blocker",
              f"path={firmware_path or 'missing'}", [firmware_path], "preserve Android-equivalent firmware_class path")
    add_check(checks, "apnhlos-modem-partitions-resolved", "pass" if "apnhlos" in parts and "modem" in parts else "blocked", "blocker",
              f"apnhlos={parts.get('apnhlos')} modem={parts.get('modem')}", [], "resolve firmware partitions")
    add_check(checks, "global-firmware-targets-not-mounted", "pass" if not already_mounted else "blocked", "blocker",
              f"already_mounted={already_mounted}", sum((mount_preflight.get("pre_mount_lines") or {}).values(), []),
              "inspect existing firmware mounts before V595")
    add_check(checks, "vendor-rootfs-shim-safe", "pass" if not shim_required or shim_allowed else "blocked", "blocker",
              f"required={shim_required} target={mount_preflight.get('vendor_symlink_target')} allowed={shim_allowed}",
              [], "only replace known native /vendor symlink")
    add_check(checks, "subsys-modem-cdev-visible", "pass" if modem_dev else "blocked", "blocker",
              f"dev={modem_dev}", [], "subsys_modem char dev must be visible")
    add_check(checks, "no-active-execns-helper", "pass" if not helper_hits else "blocked", "blocker",
              f"helper_count={len(helper_hits)}", helper_hits[:8], "reboot/cleanup before V595")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def proof_id() -> str:
    return "v595-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def modem_open_script(args: argparse.Namespace, major: str, minor: str) -> str:
    node = f"/tmp/a90-v595-subsys-modem-{proof_id()}"
    return "\n".join([
        "set -u",
        f"node={shell_quote(node)}",
        'echo "v595.modem_open.begin=1"',
        f"{args.toybox} rm -f \"$node\"",
        f"{args.toybox} mknod -m 600 \"$node\" c {major} {minor}",
        'echo "v595.modem_open.node_ready=1"',
        'exec 3<"$node"',
        'echo "v595.modem_open.opened=1"',
        "sleep 3",
        "exec 3<&-",
        'echo "v595.modem_open.closed=1"',
        f"{args.toybox} rm -f \"$node\"",
        'echo "v595.modem_open.end=1"',
    ])


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
        before_lines = before.splitlines()
        after_lines = after.splitlines()
        if len(after_lines) >= len(before_lines) and after_lines[:len(before_lines)] == before_lines:
            return "\n".join(after_lines[len(before_lines):]) + ("\n" if len(after_lines) > len(before_lines) else "")
        return after
    lines = []
    for raw_line in after.splitlines():
        line = ANSI_RE.sub("", raw_line).strip()
        match = DMESG_TS_RE.match(line)
        if match and float(match.group(1)) > before_last:
            lines.append(raw_line)
    return "\n".join(lines) + ("\n" if lines else "")


def marker_summary(text: str) -> dict[str, Any]:
    lines = [line for line in text.splitlines() if PIL_RE.search(line) or READINESS_RE.search(line) or KERNEL_WARNING_RE.search(line)]
    return {
        "pil_count": len([line for line in lines if PIL_RE.search(line)]),
        "readiness_count": len([line for line in lines if READINESS_RE.search(line)]),
        "kernel_warning_count": len([line for line in lines if KERNEL_WARNING_RE.search(line)]),
        "readiness_lines": [line for line in lines if READINESS_RE.search(line)][-40:],
        "kernel_warning_lines": [line for line in lines if KERNEL_WARNING_RE.search(line)][-40:],
        "focus_tail": lines[-80:],
    }


def run_live(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    base_dir = mountv.PROOF_BASE_PREFIX.replace("v584", "v595") + proof_id()
    vendor_symlink_target = mount_preflight.get("vendor_symlink_target")
    cleanup_results: list[str] = []
    before = run_step(args, store, steps, "dmesg-before", ["run", args.toybox, "dmesg"], 60.0)
    try:
        for name, command, timeout in mountv.build_mount_commands(mount_preflight, base_dir):
            run_step(args, store, steps, f"v595-{name}", command, timeout)
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0)
        run_step(args, store, steps, "mounted-firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0)
        for path in GLOBAL_MODEM_BLOB_PATHS:
            run_step(args, store, steps, f"mounted-stat-{safe_name(path)}", ["stat", path], 10.0)
        dev = parse_dev(step_payload(steps, "subsys-modem-dev"))
        if not dev:
            raise RuntimeError("subsys_modem dev missing after preflight")
        script = modem_open_script(args, dev[0], dev[1])
        write_capture(store, "modem-open-script-redacted", script)
        run_step(
            args,
            store,
            steps,
            "modem-open",
            ["run", args.busybox, "timeout", "-k", "2", "15", args.busybox, "sh", "-c", script],
            25.0,
        )
        run_step(args, store, steps, "mss-state-after-open", ["cat", "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"], 10.0)
        run_step(args, store, steps, "mdm3-state-after-open", ["cat", "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"], 10.0)
        run_step(args, store, steps, "rpmsg-devices-after-open", ["run", args.toybox, "ls", "/sys/bus/rpmsg/devices"], 10.0)
        run_step(args, store, steps, "proc-net-qrtr-after-open", ["run", args.toybox, "cat", "/proc/net/qrtr"], 10.0)
    finally:
        for name, command, timeout in mountv.build_cleanup_commands(base_dir, vendor_symlink_target):
            item = run_step(args, store, steps, f"v595-{name}", command, timeout)
            cleanup_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
        run_step(args, store, steps, "post-proc-mounts", ["cat", "/proc/mounts"], 20.0)
        run_step(args, store, steps, "post-ps", ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
        run_step(args, store, steps, "post-status", ["status"], 25.0)
    after = run_step(args, store, steps, "dmesg-after", ["run", args.toybox, "dmesg"], 60.0)
    delta = dmesg_delta(str(before.get("payload") or ""), str(after.get("payload") or ""))
    write_capture(store, "dmesg-delta", delta)
    mounted = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    post_mounts = mountv.parse_mounts(step_payload(steps, "post-proc-mounts"))
    modem_blob_visible = {
        path: path_exists(step_payload(steps, f"mounted-stat-{safe_name(path)}"))
        for path in GLOBAL_MODEM_BLOB_PATHS
    }
    return {
        "base": base_dir,
        "cleanup_results": cleanup_results,
        "mounted_hits": {target: target in mounted for target in mountv.PARTITION_TARGETS.values()},
        "post_mount_hits": {target: target in post_mounts for target in mountv.PARTITION_TARGETS.values()},
        "firmware_class_path": step_payload(steps, "mounted-firmware-class-path").strip(),
        "modem_blob_visible": modem_blob_visible,
        "modem_open_text": step_payload(steps, "modem-open"),
        "mss_after": step_payload(steps, "mss-state-after-open").strip(),
        "mdm3_after": step_payload(steps, "mdm3-state-after-open").strip(),
        "rpmsg_after": step_payload(steps, "rpmsg-devices-after-open"),
        "proc_qrtr_after": step_payload(steps, "proc-net-qrtr-after-open"),
        "dmesg_delta": delta,
        "markers": marker_summary(delta),
        "post_status_ok": "fail=0" in step_payload(steps, "post-status"),
        "post_helper_hits": [
            line.strip()
            for line in step_payload(steps, "post-ps").splitlines()
            if "a90_android_execns_probe" in line or "a90-v595-subsys-modem" in line
        ],
    }


def decide(args: argparse.Namespace,
           checks: list[Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v595-global-firmware-modem-open-plan-ready", True, "plan-only; no device command executed", "run V595 preflight", False
    blocked = blockers(checks)
    if blocked:
        return "v595-global-firmware-modem-open-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V595", False
    if args.command == "preflight":
        return "v595-global-firmware-modem-open-preflight-ready", True, "preflight ready; live run needs approval", "run V595 live proof", False
    if not approved(args):
        return "v595-global-firmware-modem-open-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V595 approval", False
    if not live:
        return "v595-global-firmware-modem-open-review-required", False, "missing live result", "inspect runner failure", True
    if any((live.get("post_mount_hits") or {}).values()) or live.get("post_helper_hits"):
        return "v595-global-firmware-modem-open-cleanup-review", False, "post cleanup not clean", "reboot or cleanup before continuing", True
    if "v595.modem_open.opened=1" not in str(live.get("modem_open_text") or ""):
        return "v595-modem-open-failed", False, "modem char device open did not complete", "inspect modem-open transcript", True
    if (live.get("markers") or {}).get("kernel_warning_count", 0) > 0:
        return "v595-global-firmware-modem-open-kernel-warning", False, "modem-only open produced kernel WARNING/reference mismatch", "do not repeat raw char-device close; design a kernel-safe hold/release strategy before companion retry", True
    readiness = (live.get("markers") or {}).get("readiness_count", 0) > 0
    mss_online = str(live.get("mss_after") or "").strip().upper() == "ONLINE"
    rpmsg_ready = "IPCRTR" in str(live.get("rpmsg_after") or "") or bool(str(live.get("proc_qrtr_after") or "").strip())
    if readiness or mss_online or rpmsg_ready:
        return "v595-global-firmware-modem-open-readiness-delta", True, "modem-only open reached lower readiness without esoc0 open", "advance to bounded companion/CNSS retry while preserving global firmware mounts", True
    return "v595-global-firmware-modem-open-no-readiness-delta", True, "modem-only open cleaned but no readiness marker appeared", "inspect dmesg delta before daemon/HAL retry", True


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    live = manifest.get("live") or {}
    live_rows = [[key, value] for key, value in sorted(live.items()) if key not in {"dmesg_delta", "modem_open_text", "rpmsg_after", "proc_qrtr_after"}]
    return "\n".join([
        "# V595 Global Firmware Modem-Only Open Proof",
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
    if args.command != "plan":
        mount_preflight = capture_preflight(args, store, steps)
    checks = build_checks(args, steps, mount_preflight)
    if args.command == "run" and approved(args) and not blockers(checks):
        live = run_live(args, store, steps, mount_preflight)
    decision, pass_ok, reason, next_step, live_executed = decide(args, checks, live)
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
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan",
        "device_mutations": live_executed,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "explicitly_not_approved": [
            "service-manager, CNSS, diag, Wi-Fi HAL, wificond, supplicant, or hostapd daemon start",
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
