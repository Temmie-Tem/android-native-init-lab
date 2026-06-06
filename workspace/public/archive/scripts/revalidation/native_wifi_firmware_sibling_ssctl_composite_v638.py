#!/usr/bin/env python3
"""V638 firmware-backed sibling SSCTL composite observer.

This bounded live observer recreates the V634/V635 read-only firmware mount
surface, writes ADSP/CDSP/SLPI boot nodes one at a time in child processes with
timeouts, captures lower Wi-Fi readiness markers, cleans mounts, then reboots
back to the native baseline. It does not start service-manager, Wi-Fi HAL,
supplicant, hostapd, scan/connect/link-up, credentials, DHCP, route changes, or
external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import native_wifi_firmware_cdsp_only_proof_v635 as v635
import native_wifi_firmware_mount_parity_v584 as mountv
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90ctl import run_cmdv1_command
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v638-firmware-sibling-ssctl-composite")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_NODE_TIMEOUT_SEC = 8

NODES = (
    ("adsp", "/sys/kernel/boot_adsp/boot"),
    ("cdsp", "/sys/kernel/boot_cdsp/boot"),
    ("slpi", "/sys/kernel/boot_slpi/boot"),
)

FORBIDDEN_TERMS = (
    "boot_wlan",
    "qcwlanstate",
    "shutdown_wlan",
    "IWifi",
    "wpa_supplicant",
    "hostapd",
    "dhcp",
    " ping ",
)

MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sysmon_slpi", re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.I)),
    ("sysmon_cdsp", re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I)),
    ("sysmon_adsp", re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.I)),
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*wlan_pd|wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("wlfw_start", re.compile(r"wlfw_start|wlfw_send|cnss-daemon wlfw_start", re.I)),
    ("bdf_regdb", re.compile(r"BDF file\s*:\s*regdb\.bin", re.I)),
    ("bdf_bdwlan", re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.I)),
    ("wlan_fw_ready", re.compile(r"WLAN FW is ready", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("pm_qos_warning", re.compile(r"pm_qos_add_request\(\) called for already added request", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|Reference count mismatch|subsystem_put:|Oops|Call trace", re.I)),
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
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--node-timeout-sec", type=int, default=DEFAULT_NODE_TIMEOUT_SEC)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "preflight", "sibling-proof"), nargs="?", default="preflight")
    return parser.parse_args()


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
            raise RuntimeError(f"forbidden V638 command term: {joined.strip()}")
    boot_node_hits = sum(1 for _, path in NODES if path in joined)
    if boot_node_hits:
        if "native-init-v638-sibling" not in joined and "stat " not in joined:
            raise RuntimeError(f"unexpected V638 boot-node command: {joined.strip()}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             allow_error: bool = False) -> dict[str, Any]:
    validate_command(command)
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


def marker_counts(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in MARKERS}


def marker_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {name: max(0, after.get(name, 0) - before.get(name, 0)) for name, _ in MARKERS}


def node_write_script(node: str, path: str, timeout_sec: int, busybox: str) -> str:
    timeout = max(1, min(timeout_sec, 30))
    log = f"/cache/native-init-v638-sibling-{node}.log"
    return f"""BB={busybox}
LOG={log}
$BB rm -f "$LOG"
echo "v638 node={node} begin timeout_sec={timeout}" > "$LOG"
(
  echo "child start node={node} path={path}" >> "$LOG"
  printf "1\\n" > {path}
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


def capture_node_state(args: argparse.Namespace,
                       store: EvidenceStore,
                       steps: list[dict[str, Any]],
                       name: str) -> None:
    names = "|".join(node for node, _ in NODES)
    script = (
        f"BB={args.busybox}; "
        "for d in /sys/bus/msm_subsys/devices/*; do "
        "[ -e \"$d/name\" ] && $BB grep -Eq '^(" + names + ")$' \"$d/name\" && "
        "{ echo $d; $BB cat \"$d/name\"; $BB cat \"$d/state\"; $BB cat \"$d/firmware_name\"; }; "
        "done; true"
    )
    run_step(args, store, steps, name, ["run", args.busybox, "sh", "-c", script], 15.0, allow_error=True)


def capture_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    preflight = v635.capture_preflight(args, store, steps)
    for node, path in NODES:
        run_step(args, store, steps, f"stat-{node}-node", ["stat", path], 10.0, allow_error=True)
    capture_node_state(args, store, steps, "initial-sibling-state")
    return preflight


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(command: str,
                 preflight: dict[str, Any],
                 steps: list[dict[str, Any]],
                 proof: dict[str, Any] | None) -> list[Check]:
    checks: list[Check] = []
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", "run V638 preflight")
        return checks
    parts = preflight.get("partitions") or {}
    pre_hits = preflight.get("pre_mount_hits") or {}
    already_mounted = [target for target in mountv.PARTITION_TARGETS.values() if pre_hits.get(target)]
    add_check(checks, "native-current-health", "pass" if preflight.get("native_healthy") else "blocked", "blocker", f"native_healthy={preflight.get('native_healthy')}", "restore native baseline")
    add_check(checks, "vfat-supported", "pass" if preflight.get("vfat_supported") else "blocked", "blocker", f"vfat_supported={preflight.get('vfat_supported')}", "kernel must support vfat")
    add_check(checks, "firmware-partitions-resolved", "pass" if "apnhlos" in parts and "modem" in parts else "blocked", "blocker", f"apnhlos={parts.get('apnhlos')} modem={parts.get('modem')}", "resolve firmware partitions")
    add_check(checks, "firmware-targets-not-mounted", "pass" if not already_mounted else "blocked", "blocker", f"already_mounted={already_mounted}", "start from clean mount state")
    for node, _ in NODES:
        stat_text = step_payload(steps, f"stat-{node}-node")
        present = "No such" not in stat_text and "mode=" in stat_text
        add_check(checks, f"{node}-node-present", "pass" if present else "blocked", "blocker", f"present={present}", f"confirm {node} boot node")
    if proof is None:
        return checks
    mounted_hits = proof.get("mounted_hits") or {}
    post_hits = proof.get("post_mount_hits") or {}
    delta = proof.get("marker_delta") or {}
    warning_count = int(delta.get("kernel_warning", 0) or 0) + int(delta.get("pm_qos_warning", 0) or 0)
    add_check(checks, "readonly-mounts-established", "pass" if all(mounted_hits.get(target) for target in mountv.PARTITION_TARGETS.values()) else "blocked", "blocker", f"mounted_hits={mounted_hits}", "fix firmware mounts")
    add_check(checks, "cleanup-complete", "pass" if not any(post_hits.get(target) for target in mountv.PARTITION_TARGETS.values()) else "blocked", "blocker", f"post_mount_hits={post_hits}", "unmount or reboot")
    add_check(checks, "reboot-cleanup", "pass" if (proof.get("reboot_cleanup") or {}).get("version_seen") and (proof.get("reboot_cleanup") or {}).get("status_healthy") else "blocked", "blocker", f"reboot_cleanup={proof.get('reboot_cleanup')}", "verify post-reboot native health")
    add_check(checks, "kernel-warning-clean", "pass" if warning_count == 0 else "blocked", "blocker", f"warning_count={warning_count}", "do not repeat until warnings are explained")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return safe_name(args.proof_id)
    return "run-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def run_mounts(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], preflight: dict[str, Any]) -> str:
    base = mountv.PROOF_BASE_PREFIX.replace("v584", "v638") + proof_id(args)
    for name, command, timeout in mountv.build_mount_commands(preflight, base):
        item = mountv.run_step(args, store, steps, f"v638-{name}", command, timeout)
        item["payload"] = item.get("payload") or ""
    return base


def cleanup_mounts(args: argparse.Namespace,
                   store: EvidenceStore,
                   steps: list[dict[str, Any]],
                   base: str,
                   vendor_symlink_target: str | None) -> None:
    for name, command, timeout in mountv.build_cleanup_commands(base, vendor_symlink_target):
        mountv.run_step(args, store, steps, f"v638-{name}", command, timeout)
    run_step(args, store, steps, "post-proc-mounts", ["cat", "/proc/mounts"], 20.0)


def reboot_and_wait(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    capture = run_capture(args, "reboot-cleanup", ["reboot"], timeout=5.0)
    write_capture(store, "reboot-cleanup", capture.text or capture.error)
    started = time.monotonic()
    version_text = ""
    status_text = ""
    for _ in range(60):
        try:
            version = run_cmdv1_command(args.host, args.port, 3.0, ["version"], retry_unsafe=False)
            if version.rc == 0 and version.status == "ok":
                version_text = version.text
                status = run_cmdv1_command(args.host, args.port, 5.0, ["status"], retry_unsafe=False)
                status_text = status.text
                break
        except Exception:
            time.sleep(2.0)
    write_capture(store, "post-reboot-version", version_text or "<missing>")
    write_capture(store, "post-reboot-status", status_text or "<missing>")
    return {
        "reboot_command_ok": capture.ok,
        "reboot_command_status": capture.status,
        "reboot_command_error": capture.error,
        "wait_sec": round(time.monotonic() - started, 3),
        "version_seen": args.expect_version in version_text,
        "status_healthy": "fail=0" in status_text,
    }


def run_sibling_proof(args: argparse.Namespace,
                      store: EvidenceStore,
                      steps: list[dict[str, Any]],
                      preflight: dict[str, Any]) -> dict[str, Any]:
    base = ""
    vendor_symlink_target = preflight.get("vendor_symlink_target")
    try:
        run_step(args, store, steps, "dmesg-before-sibling", ["run", args.toybox, "dmesg"], 45.0)
        base = run_mounts(args, store, steps, preflight)
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0)
        capture_node_state(args, store, steps, "mounted-initial-sibling-state")
        for node, path in NODES:
            run_step(
                args,
                store,
                steps,
                f"{node}-bounded-write",
                ["run", args.busybox, "sh", "-c", node_write_script(node, path, args.node_timeout_sec, args.busybox)],
                max(args.node_timeout_sec + 12.0, 20.0),
                allow_error=True,
            )
            capture_node_state(args, store, steps, f"state-after-{node}")
        run_step(args, store, steps, "dmesg-after-sibling", ["run", args.toybox, "dmesg"], 45.0)
    finally:
        if base:
            cleanup_mounts(args, store, steps, base, vendor_symlink_target)
    before = marker_counts(step_payload(steps, "dmesg-before-sibling"))
    after = marker_counts(step_payload(steps, "dmesg-after-sibling"))
    mounted_mounts = mountv.parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    post_mounts = mountv.parse_mounts(step_payload(steps, "post-proc-mounts"))
    node_results = {}
    for node, _ in NODES:
        text = step_payload(steps, f"{node}-bounded-write")
        node_results[node] = {
            "returned": "parent rc=0" in text,
            "timed_out": "parent rc=-110" in text,
            "child_write_rc0": "child write rc=0" in text,
            "text": text,
        }
    reboot = reboot_and_wait(args, store)
    return {
        "base": base,
        "mounted_hits": {target: target in mounted_mounts for target in mountv.PARTITION_TARGETS.values()},
        "post_mount_hits": {target: target in post_mounts for target in mountv.PARTITION_TARGETS.values()},
        "node_results": node_results,
        "marker_before": before,
        "marker_after": after,
        "marker_delta": marker_delta(before, after),
        "reboot_cleanup": reboot,
    }


def decide(command: str, checks: list[Check], proof: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v638-firmware-sibling-ssctl-composite-plan-ready", True, "plan-only; no device command executed", "run V638 preflight"
    blocked = blockers(checks)
    if blocked:
        return "v638-firmware-sibling-ssctl-composite-blocked", False, "blocked by " + ", ".join(blocked), "clear blockers before live proof"
    if command == "preflight":
        return "v638-firmware-sibling-ssctl-composite-preflight-ready", True, "firmware-backed sibling SSCTL prerequisites are present", "run V638 sibling-proof"
    if proof is None:
        return "v638-firmware-sibling-composite-inconclusive", False, "missing proof result", "inspect runner failure"
    delta = proof.get("marker_delta") or {}
    if int(delta.get("service_notifier_74", 0) or 0) > 0 or int(delta.get("wlan_pd", 0) or 0) > 0:
        return "v638-sibling-sysmon-service74-advanced", True, f"marker_delta={delta}", "plan bounded WLFW/CNSS gate; still block credentials"
    if any(int(delta.get(marker, 0) or 0) > 0 for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp")):
        return "v638-sibling-sysmon-only", True, f"marker_delta={delta}", "combine with V598-class observer only if warning-free"
    if int(delta.get("service_notifier_180", 0) or 0) > 0:
        return "v638-service180-only", True, f"marker_delta={delta}", "classify why sibling writes did not publish service 74"
    if any(result.get("timed_out") for result in (proof.get("node_results") or {}).values()):
        return "v638-sibling-write-timeout-blocked", True, f"node_results={proof.get('node_results')}", "classify timed-out node before retry"
    return "v638-firmware-sibling-composite-inconclusive", True, f"marker_delta={delta}", "inspect evidence before another live action"


def render_summary(manifest: dict[str, Any]) -> str:
    proof = manifest.get("proof") or {}
    return "\n".join([
        "# Native Init V638 Firmware-Backed Sibling SSCTL Composite",
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
                ["mounted_hits", proof.get("mounted_hits", {})],
                ["post_mount_hits", proof.get("post_mount_hits", {})],
                ["node_results", {key: {k: v for k, v in value.items() if k != "text"} for key, value in (proof.get("node_results") or {}).items()}],
                ["marker_delta", proof.get("marker_delta", {})],
                ["reboot_cleanup", proof.get("reboot_cleanup", {})],
            ],
        ) if proof else "- none",
        "",
        "## Guardrails",
        "",
        "- no `boot_wlan`, `qcwlanstate`, or `shutdown_wlan` write",
        "- no service-manager or Wi-Fi HAL start",
        "- no scan/connect/link-up, credentials, DHCP, routes, or external ping",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    preflight: dict[str, Any] = {}
    proof: dict[str, Any] | None = None
    if args.command != "plan":
        preflight = capture_preflight(args, store, steps)
    checks = build_checks(args.command, preflight, steps, None)
    if args.command == "sibling-proof" and not blockers(checks):
        proof = run_sibling_proof(args, store, steps, preflight)
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
        "device_commands_executed": args.command != "plan",
        "device_mutations": args.command == "sibling-proof" and proof is not None,
        "mount_unmount_executed": args.command == "sibling-proof" and proof is not None,
        "sysfs_writes_executed": args.command == "sibling-proof" and proof is not None,
        "adsp_write_executed": args.command == "sibling-proof" and proof is not None,
        "cdsp_write_executed": args.command == "sibling-proof" and proof is not None,
        "slpi_write_executed": args.command == "sibling-proof" and proof is not None,
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
    print(f"sysfs_writes_executed: {manifest['sysfs_writes_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
