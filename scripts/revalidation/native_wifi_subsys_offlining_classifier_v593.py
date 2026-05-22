#!/usr/bin/env python3
"""V593 read-only native modem/esoc OFFLINING classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v593-subsys-offlining-classifier")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
TOYBOX = "/cache/bin/toybox"
BUSYBOX = "/cache/bin/busybox"

FOCUS_RE = re.compile(
    r"PIL|modem|mss|mdm|esoc|subsys|subsystem|ssr|remoteproc|glink|rpmsg|qrtr|qmi|"
    r"service-notifier|sysmon|wlan_pd|icnss|cnss|wlfw|bdf|crash|fatal|ramdump",
    re.IGNORECASE,
)
READINESS_RE = re.compile(
    r"Modem QMI Readiness|QMI Server Connected|WLAN FW is ready|BDF file|wlan_pd|"
    r"qcom,glink:modem\.IPCRTR|sysmon-qmi|service-notifier",
    re.IGNORECASE,
)
CRASH_RE = re.compile(r"crash|fatal|ramdump|subsys.*restart|ssr|watchdog bite|restart sequence", re.IGNORECASE)
FIRMWARE_LOAD_RE = re.compile(r"firmware state wait timeout|Failed to locate blob|Failed to load the segment", re.IGNORECASE)
ONLINE_RE = re.compile(r"\bONLINE\b")
OFFLINING_RE = re.compile(r"\bOFFLINING\b")


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


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             name: str,
             command: list[str],
             timeout: float | None = None,
             strip: bool = True) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if strip and capture.text else capture.text or capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def shell(script: str) -> list[str]:
    return ["run", BUSYBOX, "sh", "-c", script]


SUBSYS_SCRIPT = r'''
for d in /sys/bus/msm_subsys/devices/*; do
  [ -d "$d" ] || continue
  echo "## $d"
  for f in name state restart_level firmware_name crash_count uevent; do
    if [ -e "$d/$f" ]; then
      printf "%s=" "$f"
      /cache/bin/toybox cat "$d/$f" 2>/dev/null || echo "<read-error>"
    fi
  done
done
'''

PLATFORM_SCRIPT = r'''
for d in /sys/devices/platform/soc/4080000.qcom,mss /sys/devices/platform/soc/soc:qcom,mdm3; do
  [ -d "$d" ] || continue
  echo "## $d"
  for p in \
    "$d/subsys0/name" "$d/subsys0/state" "$d/subsys0/restart_level" "$d/subsys0/firmware_name" "$d/subsys0/crash_count" "$d/subsys0/uevent" \
    "$d/subsys9/name" "$d/subsys9/state" "$d/subsys9/restart_level" "$d/subsys9/firmware_name" "$d/subsys9/crash_count" "$d/subsys9/uevent" \
    "$d/esoc0/esoc_name" "$d/esoc0/esoc_link" "$d/esoc0/esoc_link_info"; do
    if [ -e "$p" ]; then
      printf "%s=" "$p"
      /cache/bin/toybox cat "$p" 2>/dev/null || echo "<read-error>"
    fi
  done
done
'''

ESOC_SCRIPT = r'''
for p in /sys/bus/esoc /sys/kernel/debug/esoc /sys/kernel/debug/msm_subsys /sys/kernel/debug/subsys; do
  echo "## $p"
  if [ -e "$p" ]; then
    find "$p" -maxdepth 3 -type f -o -type l -o -type d 2>/dev/null | head -200
  else
    echo "<absent>"
  fi
done
'''

FIRMWARE_VISIBILITY_SCRIPT = r'''
for p in /lib/firmware /vendor/firmware_mnt/image /vendor/firmware-modem/image /firmware/image /mnt/system/vendor/firmware /mnt/system/system/vendor/firmware; do
  echo "## $p"
  if [ -e "$p" ]; then
    /cache/bin/toybox ls -la "$p" 2>/dev/null | head -80
  else
    echo "<absent>"
  fi
done
'''


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    if args.command == "plan":
        return []
    store.mkdir("native")
    steps = [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 20.0),
        run_step(args, store, "selftest", ["selftest"], 20.0),
        run_step(args, store, "ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
        run_step(args, store, "subsys-snapshot", shell(SUBSYS_SCRIPT), 20.0),
        run_step(args, store, "platform-subsys-snapshot", shell(PLATFORM_SCRIPT), 20.0),
        run_step(args, store, "esoc-debug-snapshot", shell(ESOC_SCRIPT), 20.0),
        run_step(args, store, "rpmsg-devices", ["run", TOYBOX, "ls", "-la", "/sys/bus/rpmsg/devices"], 10.0),
        run_step(args, store, "rpmsg-drivers", ["run", TOYBOX, "ls", "-la", "/sys/bus/rpmsg/drivers"], 10.0),
        run_step(args, store, "remoteproc", ["run", TOYBOX, "ls", "-la", "/sys/class/remoteproc"], 10.0),
        run_step(args, store, "service-notifier", ["run", TOYBOX, "ls", "-la", "/sys/kernel/debug/service_notifier"], 10.0),
        run_step(args, store, "proc-net-qrtr", ["run", TOYBOX, "cat", "/proc/net/qrtr"], 10.0),
        run_step(args, store, "firmware-class-path", ["run", TOYBOX, "cat", "/sys/module/firmware_class/parameters/path"], 10.0),
        run_step(args, store, "firmware-visibility", shell(FIRMWARE_VISIBILITY_SCRIPT), 20.0),
        run_step(args, store, "dmesg", ["run", TOYBOX, "dmesg"], 60.0),
    ]
    dmesg = step_payload(steps, "dmesg")
    focus = "\n".join(line for line in dmesg.splitlines() if FOCUS_RE.search(line))
    write_capture(store, "dmesg-focus", focus or "<none>")
    steps.append({
        "name": "dmesg-focus",
        "command": "host-filter dmesg focus",
        "ok": True,
        "rc": 0,
        "status": "ok",
        "duration_sec": 0.0,
        "file": "native/dmesg-focus.txt",
        "error": "",
        "payload": focus,
    })
    return steps


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def parse_state(snapshot: str, name: str) -> str:
    current_section = ""
    for raw_line in snapshot.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current_section = line
            continue
        if name in current_section and line.startswith("state="):
            return line.split("=", 1)[1].strip()
    return ""


def parse_crash_counts(snapshot: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    current_section = ""
    for raw_line in snapshot.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current_section = line[3:]
            continue
        if line.startswith("crash_count="):
            try:
                counts[current_section] = int(line.split("=", 1)[1].strip())
            except ValueError:
                counts[current_section] = -1
    return counts


def build_analysis(steps: list[dict[str, Any]]) -> dict[str, Any]:
    subsys = step_payload(steps, "subsys-snapshot")
    platform = step_payload(steps, "platform-subsys-snapshot")
    ps = step_payload(steps, "ps")
    rpmsg = step_payload(steps, "rpmsg-devices")
    service_notifier = step_payload(steps, "service-notifier")
    proc_qrtr = step_payload(steps, "proc-net-qrtr")
    firmware_class_path = step_payload(steps, "firmware-class-path").strip()
    firmware_visibility = step_payload(steps, "firmware-visibility")
    dmesg_focus = step_payload(steps, "dmesg-focus")
    mss_state = parse_state(subsys, "subsys0") or ("ONLINE" if "mss/subsys0/state=ONLINE" in platform else "")
    mdm3_state = parse_state(subsys, "subsys9") or ("ONLINE" if "mdm3/subsys9/state=ONLINE" in platform else "")
    crash_counts = parse_crash_counts(subsys + "\n" + platform)
    helper_residual = [line.strip() for line in ps.splitlines() if "a90_android_execns_probe" in line]
    return {
        "mss_state": mss_state,
        "mdm3_state": mdm3_state,
        "any_offlining": mss_state == "OFFLINING" or mdm3_state == "OFFLINING" or bool(OFFLINING_RE.search(subsys)),
        "any_online": mss_state == "ONLINE" or mdm3_state == "ONLINE" or bool(ONLINE_RE.search(subsys)),
        "crash_counts": crash_counts,
        "crash_count_positive": any(value > 0 for value in crash_counts.values()),
        "helper_residual": helper_residual,
        "helper_residual_d_state": any(re.search(r"\sD\w*\s+.*a90_android_execns_probe", line) for line in helper_residual),
        "rpmsg_ipcrtr_present": "IPCRTR" in rpmsg,
        "service_notifier_present": "No such file" not in service_notifier and "<absent>" not in service_notifier and "service_notifier" in service_notifier,
        "proc_qrtr_present": "No such file" not in proc_qrtr and "open-error" not in proc_qrtr and bool(proc_qrtr.strip()),
        "firmware_class_path": firmware_class_path,
        "global_modem_blobs_visible": bool(re.search(r"\bmodem\.(?:mdt|b[0-9]{2})\b", firmware_visibility)),
        "readiness_lines": [line for line in dmesg_focus.splitlines() if READINESS_RE.search(line)][-80:],
        "crash_lines": [line for line in dmesg_focus.splitlines() if CRASH_RE.search(line)][-80:],
        "firmware_load_failure_lines": [line for line in dmesg_focus.splitlines() if FIRMWARE_LOAD_RE.search(line)][-80:],
        "focus_tail": dmesg_focus.splitlines()[-160:],
    }


def build_checks(args: argparse.Namespace, steps: list[dict[str, Any]], analysis: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run read-only classifier")
        return checks
    version = step_payload(steps, "version")
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    add_check(checks, "native-readable", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "warn", "warning",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:2], "refresh baseline if expected version changed")
    add_check(checks, "subsys-offlining-observed", "pass" if analysis["any_offlining"] else "warn", "warning",
              f"mss={analysis['mss_state'] or 'missing'} mdm3={analysis['mdm3_state'] or 'missing'}", [], "if not OFFLINING, route to current state-specific classifier")
    add_check(checks, "helper-residual", "blocked" if analysis["helper_residual_d_state"] else ("warn" if analysis["helper_residual"] else "pass"), "blocker" if analysis["helper_residual_d_state"] else "warning",
              f"residual_count={len(analysis['helper_residual'])} d_state={analysis['helper_residual_d_state']}", analysis["helper_residual"][:8], "reboot before further live subsystem experiments")
    return checks


def decide(args: argparse.Namespace, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v593-subsys-offlining-classifier-plan-ready", True, "plan-only; no device command executed", "run classifier"
    if analysis.get("helper_residual_d_state"):
        return (
            "v593-subsys-offlining-captured-reboot-required",
            True,
            "native modem/esoc OFFLINING captured, but a prior subsystem hold-open helper is stuck in D-state and contaminates further live tests",
            "reboot to clear D-state helper, then rerun V593 immediately after native boot before any trigger proof",
        )
    if analysis.get("firmware_load_failure_lines"):
        return (
            "v593-subsys-pil-firmware-load-failed",
            True,
            "subsystem get path attempted PIL modem load, but modem firmware blobs timed out or were not visible to firmware_class",
            "compare Android firmware_class path/root namespace and mount global modem firmware visibility before any cdev/HAL retry",
        )
    if analysis.get("crash_count_positive") or analysis.get("crash_lines"):
        return (
            "v593-subsys-offlining-crash-suspected",
            True,
            "OFFLINING is present with crash/restart evidence in dmesg or crash_count",
            "compare Android early dmesg transition around modem ONLINE and identify missing native trigger",
        )
    if analysis.get("readiness_lines") or analysis.get("any_online"):
        return (
            "v593-subsys-transition-observed",
            True,
            "readiness or ONLINE markers are present in native evidence",
            "isolate which native event caused the transition before daemon/HAL retry",
        )
    if analysis.get("any_offlining"):
        return (
            "v593-subsys-offlining-no-crash-marker",
            True,
            "mss/mdm3 are OFFLINING without captured crash_count or readiness markers",
            "collect immediate-post-boot V593 and Android dmesg delta to distinguish early shutdown from missing boot trigger",
        )
    return (
        "v593-subsys-state-review-required",
        False,
        "subsystem state is not classified by current OFFLINING rules",
        "inspect sysfs and dmesg focus evidence manually",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    analysis = manifest["analysis"]
    state_rows = [
        ["mss_state", analysis.get("mss_state", "")],
        ["mdm3_state", analysis.get("mdm3_state", "")],
        ["any_offlining", analysis.get("any_offlining", "")],
        ["any_online", analysis.get("any_online", "")],
        ["rpmsg_ipcrtr_present", analysis.get("rpmsg_ipcrtr_present", "")],
        ["service_notifier_present", analysis.get("service_notifier_present", "")],
        ["proc_qrtr_present", analysis.get("proc_qrtr_present", "")],
        ["firmware_class_path", analysis.get("firmware_class_path", "")],
        ["global_modem_blobs_visible", analysis.get("global_modem_blobs_visible", "")],
        ["crash_count_positive", analysis.get("crash_count_positive", "")],
        ["firmware_load_failure_count", len(analysis.get("firmware_load_failure_lines") or [])],
        ["helper_residual_d_state", analysis.get("helper_residual_d_state", "")],
    ]
    return "\n".join([
        "# V593 Subsys OFFLINING Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## State Summary",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Crash/Restart Focus",
        "",
        "```text",
        "\n".join(analysis.get("crash_lines") or ["<none>"]),
        "```",
        "",
        "## Firmware Load Failure Focus",
        "",
        "```text",
        "\n".join(analysis.get("firmware_load_failure_lines") or ["<none>"]),
        "```",
        "",
        "## Readiness Focus",
        "",
        "```text",
        "\n".join(analysis.get("readiness_lines") or ["<none>"]),
        "```",
        "",
        "## Evidence",
        "",
        f"- `{manifest['out_dir']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps = collect_steps(args, store)
    analysis = build_analysis(steps) if steps else {}
    checks = build_checks(args, steps, analysis)
    decision, pass_ok, reason, next_step = decide(args, checks, analysis)
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
        "analysis": analysis,
        "device_commands_executed": args.command != "plan",
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "explicitly_not_approved": [
            "mounts, writes, daemon starts, HAL starts, scan/connect/link-up, credentials, DHCP, routes, external ping",
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
