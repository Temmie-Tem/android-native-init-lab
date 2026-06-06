#!/usr/bin/env python3
"""V635 firmware mount plus CDSP-only bounded proof.

This proof recreates the V634 read-only firmware mount surface, writes only
`/sys/kernel/boot_cdsp/boot` in a bounded child, captures lower Wi-Fi readiness
markers, then attempts mount cleanup. It does not start daemons, service-manager,
Wi-Fi HAL, supplicant, hostapd, scan/connect/link-up, credentials, DHCP, route
changes, or external ping.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v635-firmware-cdsp-only-proof")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_CDSP_TIMEOUT_SEC = 8

CDSP_NODE = "/sys/kernel/boot_cdsp/boot"
FIRMWARE_CLASS_PATH = "/vendor/firmware_mnt/image"

FORBIDDEN_COMMAND_TERMS = (
    "boot_adsp",
    "boot_slpi",
    "boot_wlan",
    "qcwlanstate",
    "shutdown_wlan",
    "IWifi",
    "wpa_supplicant",
    "hostapd",
    "dhcp",
    "ping",
)

MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cdsp_pil", re.compile(r"subsys-pil.*(?:turing|cdsp).*cdsp: loading|cdsp: loading", re.I)),
    ("cdsp_power_clock", re.compile(r"cdsp: Power/Clock ready interrupt received", re.I)),
    ("cdsp_brought_reset", re.compile(r"cdsp: Brought out of reset", re.I)),
    ("sysmon_cdsp", re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*wlan_pd|wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("wlfw_start", re.compile(r"wlfw_start|wlfw_send", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("pm_qos_warning", re.compile(r"pm_qos_add_request\(\) called for already added request", re.I)),
    ("direct_firmware_fail", re.compile(r"Direct firmware load.*failed|Falling back to sysfs fallback|Failed to locate blob|Failed to load", re.I)),
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
    parser.add_argument("--cdsp-timeout-sec", type=int, default=DEFAULT_CDSP_TIMEOUT_SEC)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "preflight", "cdsp-proof"), nargs="?", default="preflight")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return safe_name(args.proof_id)
    return "run-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def validate_v635_command(command: list[str]) -> None:
    joined = " ".join(command)
    for term in FORBIDDEN_COMMAND_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden command term in V635: {joined}")
    if CDSP_NODE in joined:
        if "native-init-v635-cdsp-only.log" in joined:
            return
        if joined.count(CDSP_NODE) == 1 and "boot_cdsp" in joined:
            return
        raise RuntimeError(f"unexpected CDSP node command in V635: {joined}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             allow_error: bool = False) -> dict[str, Any]:
    validate_v635_command(command)
    capture = run_capture(args, name, command, timeout=timeout if timeout is not None else args.timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    item["allowed_error"] = allow_error
    steps.append(item)
    if not allow_error and not item.get("ok"):
        item["blocking_error"] = True
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def count_markers(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in MARKERS}


def marker_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {name: max(0, after.get(name, 0) - before.get(name, 0)) for name, _ in MARKERS}


def first_line(text: str, pattern: str) -> str:
    compiled = re.compile(pattern, re.I)
    for line in text.splitlines():
        if compiled.search(line):
            return line.strip()
    return "missing"


def cdsp_shell_script(timeout_sec: int, busybox: str) -> str:
    timeout = max(1, min(timeout_sec, 30))
    return f"""BB={busybox}
LOG=/cache/native-init-v635-cdsp-only.log
$BB rm -f "$LOG"
echo "v635 cdsp-only begin timeout_sec={timeout}" > "$LOG"
(
  echo "child start path={CDSP_NODE}" >> "$LOG"
  printf "1\\n" > {CDSP_NODE}
  rc=$?
  echo "child write rc=$rc" >> "$LOG"
  exit "$rc"
) &
pid=$!
echo "parent pid=$pid" >> "$LOG"
i=0
while $BB kill -0 "$pid" 2>/dev/null; do
  if [ "$i" -ge {timeout} ]; then
    echo "parent timeout sec=$i" >> "$LOG"
    $BB kill -9 "$pid" 2>/dev/null
    wait "$pid"
    status=$?
    echo "parent rc=-110 status=$status reaped=1" >> "$LOG"
    $BB cat "$LOG"
    exit 110
  fi
  $BB sleep 1
  i=$((i + 1))
done
wait "$pid"
status=$?
echo "parent rc=0 status=$status reaped=1" >> "$LOG"
$BB cat "$LOG"
exit "$status"
"""


def capture_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    mount_preflight_steps: list[dict[str, Any]] = []
    mount_preflight = mountv.capture_preflight(args, store, mount_preflight_steps)
    steps.extend(mount_preflight_steps)
    run_step(args, store, steps, "firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0)
    run_step(args, store, steps, "stat-cdsp-node", ["stat", CDSP_NODE], 10.0, allow_error=True)
    run_step(
        args,
        store,
        steps,
        "subsys-cdsp-state",
        ["run", args.busybox, "sh", "-c", f"BB={args.busybox}; for d in /sys/bus/msm_subsys/devices/*; do [ -e \"$d/name\" ] && $BB grep -q '^cdsp$' \"$d/name\" && {{ echo $d; $BB cat \"$d/name\"; $BB cat \"$d/state\"; $BB cat \"$d/firmware_name\"; }}; done; true"],
        15.0,
        allow_error=True,
    )
    return mount_preflight


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(command: str, preflight: dict[str, Any], steps: list[dict[str, Any]], proof: dict[str, Any] | None) -> list[Check]:
    checks: list[Check] = []
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", "run V635 preflight")
        return checks
    parts = preflight.get("partitions") or {}
    pre_hits = preflight.get("pre_mount_hits") or {}
    firmware_path = step_payload(steps, "firmware-class-path").strip()
    cdsp_stat = step_payload(steps, "stat-cdsp-node")
    add_check(checks, "native-current-health", "pass" if preflight.get("native_healthy") else "blocked", "blocker", f"native_healthy={preflight.get('native_healthy')}", "restore native baseline")
    add_check(checks, "vfat-supported", "pass" if preflight.get("vfat_supported") else "blocked", "blocker", f"vfat_supported={preflight.get('vfat_supported')}", "kernel must support vfat")
    add_check(checks, "apnhlos-modem-partitions-resolved", "pass" if "apnhlos" in parts and "modem" in parts else "blocked", "blocker", f"apnhlos={parts.get('apnhlos')} modem={parts.get('modem')}", "resolve firmware partitions")
    already_mounted = [target for target in mountv.PARTITION_TARGETS.values() if pre_hits.get(target)]
    add_check(checks, "firmware-targets-not-mounted", "pass" if not already_mounted else "blocked", "blocker", f"already_mounted={already_mounted}", "inspect existing mounts")
    add_check(checks, "firmware-class-path-android", "pass" if firmware_path == FIRMWARE_CLASS_PATH else "blocked", "blocker", f"path={firmware_path}", "restore Android-equivalent firmware path")
    cdsp_node_present = "No such" not in cdsp_stat and "mode=" in cdsp_stat
    add_check(checks, "cdsp-node-present", "pass" if cdsp_node_present else "blocked", "blocker", f"stat_mode_present={cdsp_node_present}", "confirm CDSP boot node exists")
    if proof is None:
        return checks
    mounted_hits = proof.get("mounted_hits") or {}
    post_hits = proof.get("post_mount_hits") or {}
    add_check(checks, "readonly-mounts-established", "pass" if all(mounted_hits.get(target) for target in mountv.PARTITION_TARGETS.values()) else "blocked", "blocker", f"mounted_hits={mounted_hits}", "fix firmware mounts")
    add_check(checks, "cleanup-complete", "pass" if not any(post_hits.get(target) for target in mountv.PARTITION_TARGETS.values()) else "blocked", "blocker", f"post_mount_hits={post_hits}", "unmount or reboot")
    add_check(checks, "post-health", "pass" if proof.get("post_healthy") else "blocked", "blocker", f"post_healthy={proof.get('post_healthy')}", "restore native health")
    add_check(checks, "no-wifi-bringup", "pass", "blocker", "wifi_bringup_executed=False", "continue blocking scan/connect until lower markers advance")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def run_mounts(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], preflight: dict[str, Any]) -> str:
    base = mountv.PROOF_BASE_PREFIX.replace("v584", "v635") + proof_id(args)
    for name, command, timeout in mountv.build_mount_commands(preflight, base):
        item = mountv.run_step(args, store, steps, f"v635-{name}", command, timeout)
        item["payload"] = item.get("payload") or ""
    return base


def cleanup_mounts(args: argparse.Namespace,
                   store: EvidenceStore,
                   steps: list[dict[str, Any]],
                   base: str,
                   vendor_symlink_target: str | None) -> None:
    for name, command, timeout in mountv.build_cleanup_commands(base, vendor_symlink_target):
        mountv.run_step(args, store, steps, f"v635-{name}", command, timeout)
    run_step(args, store, steps, "post-proc-mounts", ["cat", "/proc/mounts"], 20.0)
    run_step(args, store, steps, "post-status", ["status"], 25.0)


def run_cdsp_proof(args: argparse.Namespace,
                   store: EvidenceStore,
                   steps: list[dict[str, Any]],
                   preflight: dict[str, Any]) -> dict[str, Any]:
    base = ""
    vendor_symlink_target = preflight.get("vendor_symlink_target")
    try:
        run_step(args, store, steps, "dmesg-before-cdsp", ["run", args.toybox, "dmesg"], 45.0)
        base = run_mounts(args, store, steps, preflight)
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0)
        run_step(args, store, steps, "mounted-firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 10.0)
        run_step(args, store, steps, "mounted-stat-cdsp-fw", ["stat", "/vendor/firmware-modem/image/cdsp.mdt"], 10.0, allow_error=True)
        script = cdsp_shell_script(args.cdsp_timeout_sec, args.busybox)
        run_step(
            args,
            store,
            steps,
            "cdsp-only-write",
            ["run", args.busybox, "sh", "-c", script],
            max(args.cdsp_timeout_sec + 12.0, 20.0),
            allow_error=True,
        )
        run_step(args, store, steps, "subsys-after-cdsp", ["run", args.busybox, "sh", "-c", f"BB={args.busybox}; for d in /sys/bus/msm_subsys/devices/*; do [ -e \"$d/name\" ] && $BB grep -q '^cdsp$' \"$d/name\" && {{ echo $d; $BB cat \"$d/name\"; $BB cat \"$d/state\"; $BB cat \"$d/firmware_name\"; }}; done; true"], 15.0, allow_error=True)
        run_step(args, store, steps, "dmesg-after-cdsp", ["run", args.toybox, "dmesg"], 45.0)
    finally:
        if base:
            cleanup_mounts(args, store, steps, base, vendor_symlink_target)

    before = count_markers(step_payload(steps, "dmesg-before-cdsp"))
    after = count_markers(step_payload(steps, "dmesg-after-cdsp"))
    mounted_mounts = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    post_mounts = mountv.parse_mounts(step_payload(steps, "post-proc-mounts"))
    cdsp_text = step_payload(steps, "cdsp-only-write")
    return {
        "base": base,
        "mounted_hits": {target: target in mounted_mounts for target in mountv.PARTITION_TARGETS.values()},
        "post_mount_hits": {target: target in post_mounts for target in mountv.PARTITION_TARGETS.values()},
        "marker_before": before,
        "marker_after": after,
        "marker_delta": marker_delta(before, after),
        "cdsp_write_text": cdsp_text,
        "cdsp_timed_out": "parent rc=-110" in cdsp_text,
        "cdsp_returned": "parent rc=0" in cdsp_text,
        "cdsp_child_write_rc0": "child write rc=0" in cdsp_text,
        "cdsp_state_after": step_payload(steps, "subsys-after-cdsp"),
        "post_healthy": "fail=0" in step_payload(steps, "post-status"),
    }


def decide(command: str, checks: list[Check], proof: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v635-firmware-cdsp-only-proof-plan-ready", True, "plan-only; no device command executed", "run V635 preflight"
    blocking = blockers(checks)
    if blocking:
        return "v635-firmware-cdsp-only-proof-blocked", False, "blocked by " + ", ".join(blocking), "clear blockers before live proof"
    if command == "preflight":
        return "v635-firmware-cdsp-only-proof-preflight-ready", True, "firmware mount and CDSP node prerequisites are present", "run V635 cdsp-proof"
    if proof is None:
        return "v635-firmware-cdsp-only-proof-missing", False, "missing proof result", "inspect runner failure"
    delta = proof.get("marker_delta") or {}
    if int(delta.get("service_notifier_74", 0) or 0) > 0 or int(delta.get("wlan_pd", 0) or 0) > 0:
        return "v635-cdsp-service74-advanced", True, "CDSP-only proof advanced service 74/WLAN-PD markers", "plan bounded CNSS/HAL readiness gate; still no credentials until link surface exists"
    if int(delta.get("sysmon_cdsp", 0) or 0) > 0:
        return "v635-cdsp-sysmon-only", True, "CDSP-only proof reached CDSP sysmon but not service 74/WLAN-PD", "classify service 74 publication after CDSP sysmon"
    if proof.get("cdsp_timed_out"):
        return "v635-cdsp-still-times-out-with-firmware", True, "CDSP write still timed out even with read-only firmware mounts", "classify remaining CDSP loader prerequisite before another write"
    if proof.get("cdsp_returned"):
        return "v635-cdsp-returned-no-lower-marker", True, "CDSP write returned but no lower readiness marker advanced", "inspect dmesg/state for non-QMI CDSP result"
    return "v635-cdsp-proof-inconclusive", True, "CDSP proof completed without a recognized outcome", "inspect evidence before continuing"


def render_summary(manifest: dict[str, Any]) -> str:
    proof = manifest.get("proof") or {}
    return "\n".join([
        "# Native Init V635 Firmware CDSP-Only Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- sysfs_writes_executed: `{manifest['sysfs_writes_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]),
        "",
        "## Proof",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["base", proof.get("base", "")],
                ["mounted_hits", proof.get("mounted_hits", {})],
                ["post_mount_hits", proof.get("post_mount_hits", {})],
                ["marker_delta", proof.get("marker_delta", {})],
                ["cdsp_timed_out", proof.get("cdsp_timed_out", "")],
                ["cdsp_returned", proof.get("cdsp_returned", "")],
                ["cdsp_child_write_rc0", proof.get("cdsp_child_write_rc0", "")],
                ["post_healthy", proof.get("post_healthy", "")],
            ],
        ),
        "",
        "## CDSP Write Log",
        "",
        "```text",
        str(proof.get("cdsp_write_text") or "not-run").strip(),
        "```",
        "",
        "## Guardrails",
        "",
        "- no ADSP/SLPI boot-node write",
        "- no `boot_wlan`, `qcwlanstate`, or `shutdown_wlan` write",
        "- no daemon/service-manager/CNSS/Wi-Fi HAL start",
        "- no scan/connect/link-up, credentials, DHCP, routes, or external ping",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    preflight: dict[str, Any] = {}
    proof: dict[str, Any] | None = None
    if args.command in {"preflight", "cdsp-proof"}:
        preflight = capture_preflight(args, store, steps)
    pre_checks = build_checks(args.command, preflight, steps, None)
    if args.command == "cdsp-proof" and not blockers(pre_checks):
        proof = run_cdsp_proof(args, store, steps, preflight)
    checks = build_checks(args.command, preflight, steps, proof)
    decision, pass_ok, reason, next_step = decide(args.command, checks, proof)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "preflight": preflight,
        "proof": proof or {},
        "device_commands_executed": args.command in {"preflight", "cdsp-proof"},
        "device_mutations": args.command == "cdsp-proof" and proof is not None,
        "mount_unmount_executed": args.command == "cdsp-proof" and proof is not None,
        "sysfs_writes_executed": args.command == "cdsp-proof" and proof is not None,
        "cdsp_write_executed": args.command == "cdsp-proof" and proof is not None,
        "adsp_write_executed": False,
        "slpi_write_executed": False,
        "partition_write_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
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
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"sysfs_writes_executed: {manifest['sysfs_writes_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
