#!/usr/bin/env python3
"""V1256 read-only gpiochip devnode feasibility classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1256-gpiochip-devnode-feas-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1256-gpiochip-devnode-feas-live.txt")
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEBUGFS_ROOT = "/sys/kernel/debug"
APPROVAL_PHRASE = (
    "approve v1256 read-only gpiochip devnode feasibility only; "
    "no mknod, no GPIO line request, no eSoC ioctl, no daemon start and no Wi-Fi bring-up"
)
SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)


@dataclass
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
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1 [redacted]", text)


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._+-" else "-" for ch in value).strip("-") or "capture"


def capture_native(
    args: argparse.Namespace,
    store: EvidenceStore,
    name: str,
    command: list[str],
    *,
    timeout: float | None = None,
    allow_error: bool = False,
) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = capture.text if capture.text else capture.error + "\n"
    stripped = strip_cmdv1_text(text) if capture.text else text
    stripped = redact(stripped)
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, stripped.rstrip() + "\n")
    data = asdict(capture)
    data["text"] = redact(data.get("text") or "")
    if len(data["text"]) > 4096:
        data["text_sha256_like"] = "omitted-large-text"
        data["text"] = data["text"][:4096] + "\n[truncated in manifest]\n"
    data["file"] = rel
    data["ok"] = bool(capture.ok or allow_error)
    data["raw_ok"] = bool(capture.ok)
    return data


def read_step_text(store: EvidenceStore, step: dict[str, Any]) -> str:
    rel = str(step.get("file") or "")
    if not rel:
        return ""
    path = store.run_dir / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def step_text(store: EvidenceStore, steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return read_step_text(store, step)
    return ""


def debugfs_mounted(text: str) -> bool:
    return re.search(rf"\s{re.escape(DEBUGFS_ROOT)}\s+debugfs\s", text) is not None


def proc_mounts_command(args: argparse.Namespace) -> list[str]:
    return ["run", args.toybox, "cat", "/proc/mounts"]


def gpiochip_probe_script(args: argparse.Namespace) -> list[str]:
    script = r"""
set -u
BB=__BB__
echo "== dev-gpiochip =="
$BB ls -l /dev/gpiochip* 2>&1 || true
echo "== proc-devices =="
$BB cat /proc/devices 2>&1 | $BB grep -i gpio || true
echo "== sys-class-gpio =="
$BB ls -la /sys/class/gpio 2>&1 || true
for d in /sys/class/gpio/gpiochip*; do
  [ -e "$d" ] || continue
  echo "CLASS_CHIP $d"
  for f in base label ngpio dev uevent; do
    [ -r "$d/$f" ] && { printf "CLASS_FILE %s/%s=" "$d" "$f"; $BB cat "$d/$f" 2>&1; }
  done
  $BB readlink "$d" 2>/dev/null | $BB sed "s#^#CLASS_LINK $d -> #"
done
echo "== sys-bus-gpio =="
$BB ls -la /sys/bus/gpio/devices 2>&1 || true
for d in /sys/bus/gpio/devices/gpiochip*; do
  [ -e "$d" ] || continue
  echo "BUS_CHIP $d"
  for f in base label ngpio dev uevent; do
    [ -r "$d/$f" ] && { printf "BUS_FILE %s/%s=" "$d" "$f"; $BB cat "$d/$f" 2>&1; }
  done
  $BB readlink "$d" 2>/dev/null | $BB sed "s#^#BUS_LINK $d -> #"
done
echo "== debug-gpio-focus =="
if [ -r /sys/kernel/debug/gpio ]; then
  $BB cat /sys/kernel/debug/gpio 2>&1 | $BB grep -Ei 'gpiochip2|1263-1273|pm8150l|c440000|gpio9|gpio-9' || true
else
  echo "debug_gpio_readable=0"
fi
""".replace("__BB__", args.busybox)
    return ["run", args.busybox, "sh", "-c", script]


def preflight_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    return [
        capture_native(args, store, "hide", ["hide"], timeout=10.0),
        capture_native(args, store, "version", ["version"], timeout=10.0),
        capture_native(args, store, "selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "netservice-status", ["netservice", "status"], timeout=10.0),
        capture_native(args, store, "debugfs-mounts-before", proc_mounts_command(args), timeout=15.0),
    ]


def run_steps(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    mounted_before = debugfs_mounted(step_text(store, steps, "debugfs-mounts-before"))
    mounted_by_v1256 = False
    if not mounted_before:
        mount_step = capture_native(
            args,
            store,
            "debugfs-mount",
            ["run", args.busybox, "mount", "-t", "debugfs", "debugfs", DEBUGFS_ROOT],
            timeout=20.0,
        )
        steps.append(mount_step)
        mounted_by_v1256 = bool(mount_step.get("raw_ok"))
    steps.append(capture_native(args, store, "debugfs-mounts-during", proc_mounts_command(args), timeout=15.0))
    steps.append(capture_native(args, store, "gpiochip-devnode-probe", gpiochip_probe_script(args), timeout=args.timeout))
    if mounted_by_v1256:
        steps.append(
            capture_native(
                args,
                store,
                "debugfs-umount",
                ["run", args.busybox, "umount", DEBUGFS_ROOT],
                timeout=20.0,
                allow_error=True,
            )
        )
    steps.append(capture_native(args, store, "debugfs-mounts-after", proc_mounts_command(args), timeout=15.0))
    steps.append(capture_native(args, store, "post-selftest", ["selftest", "verbose"], timeout=15.0))
    return {"mounted_before": mounted_before, "mounted_by_v1256": mounted_by_v1256}


def extract_lines(text: str, pattern: str) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [line.strip() for line in text.splitlines() if regex.search(line)]


def analyze(store: EvidenceStore, steps: list[dict[str, Any]], mount_info: dict[str, Any]) -> dict[str, Any]:
    probe = step_text(store, steps, "gpiochip-devnode-probe")
    mounts_during = step_text(store, steps, "debugfs-mounts-during")
    mounts_after = step_text(store, steps, "debugfs-mounts-after")
    selftest = step_text(store, steps, "selftest")
    post_selftest = step_text(store, steps, "post-selftest")
    dev_lines = extract_lines(probe, r"/dev/gpiochip|No such file|cannot access")
    class_lines = extract_lines(probe, r"CLASS_(CHIP|FILE|LINK)|gpiochip")
    bus_lines = extract_lines(probe, r"BUS_(CHIP|FILE|LINK)|gpiochip")
    debug_lines = extract_lines(probe, r"gpiochip2|1263-1273|pm8150l|c440000|gpio9|gpio-9")
    devnode_absent = any("No such file" in line or "cannot access" in line for line in dev_lines)
    sysfs_dev_metadata_seen = bool(extract_lines(probe, r"/dev=|MAJOR=|MINOR="))
    range_seen = any("1263-1273" in line for line in debug_lines + class_lines + bus_lines)
    pmic_identity_seen = any("pm8150l" in line or "c440000" in line for line in debug_lines + class_lines + bus_lines)
    feasibility_candidate = devnode_absent and sysfs_dev_metadata_seen and range_seen and pmic_identity_seen
    mounted_before = bool(mount_info.get("mounted_before"))
    mounted_after = debugfs_mounted(mounts_after)
    return {
        "mounted_before": mounted_before,
        "mounted_by_v1256": bool(mount_info.get("mounted_by_v1256")),
        "mounted_during": debugfs_mounted(mounts_during),
        "mounted_after": mounted_after,
        "cleanup_ok": mounted_before or not mounted_after,
        "selftest_fail0": "fail=0" in selftest,
        "post_selftest_fail0": "fail=0" in post_selftest,
        "dev_lines": dev_lines[:40],
        "class_lines": class_lines[:80],
        "bus_lines": bus_lines[:80],
        "debug_lines": debug_lines[:80],
        "devnode_absent": devnode_absent,
        "sysfs_dev_metadata_seen": sysfs_dev_metadata_seen,
        "range_seen": range_seen,
        "pmic_identity_seen": pmic_identity_seen,
        "feasibility_candidate": feasibility_candidate,
    }


def build_checks(command: str, args: argparse.Namespace, analysis: dict[str, Any], steps: list[dict[str, Any]]) -> list[Check]:
    step_ok = {str(step.get("name")): bool(step.get("ok")) for step in steps}
    checks = [
        Check("approval-gate", "pass" if command != "run" or approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} assume_yes={args.assume_yes}", "provide exact approval phrase before live run"),
        Check("native-clean", "pass" if step_ok.get("selftest") and analysis["selftest_fail0"] else "blocked", "blocker", "selftest fail0 before run", "fix native health first"),
    ]
    if command == "run":
        checks.extend([
            Check("debugfs-mounted", "pass" if analysis["mounted_during"] else "blocked", "blocker", f"mounted={analysis['mounted_during']}", "inspect debugfs mount"),
            Check("probe-command", "pass" if step_ok.get("gpiochip-devnode-probe") else "blocked", "blocker", "gpiochip probe completed", "inspect probe command"),
            Check("debugfs-cleanup", "pass" if analysis["cleanup_ok"] else "blocked", "blocker", f"before={analysis['mounted_before']} after={analysis['mounted_after']}", "unmount debugfs if V1256 mounted it"),
            Check("post-selftest", "pass" if analysis["post_selftest_fail0"] else "blocked", "blocker", f"fail0={analysis['post_selftest_fail0']}", "recheck device health"),
        ])
    return checks


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    blockers = [check.name for check in checks if check.status not in {"pass", "warn"}]
    if command == "plan":
        return ("v1256-gpiochip-devnode-feas-plan-ready", True, "plan-only; no device command executed", "run preflight then approved read-only V1256")
    if blockers:
        return ("v1256-gpiochip-devnode-feas-blocked", False, "blocked by " + ", ".join(blockers), "fix blockers before continuing")
    if command == "preflight":
        return ("v1256-gpiochip-devnode-feas-ready", True, "native health ready for read-only gpiochip devnode feasibility", "run approved read-only V1256")
    if analysis["feasibility_candidate"]:
        return ("v1256-gpiochip-temporary-devnode-feasible", True, "sysfs exposes device metadata for a temporary gpiochip node candidate", "design source/build mknod preflight; still no line request")
    if analysis["range_seen"] and analysis["pmic_identity_seen"] and analysis["devnode_absent"]:
        return ("v1256-gpiochip-devnode-missing-no-dev-metadata", True, "PMIC gpiochip is visible in debugfs but no /dev node or sysfs dev metadata was found", "classify kernel GPIO chardev availability before mknod design")
    return ("v1256-gpiochip-surface-incomplete", True, "gpiochip feasibility surface incomplete", "inspect sysfs/debugfs output")


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [
        ["decision", manifest["decision"]],
        ["pass", manifest["pass"]],
        ["mounted_by_v1256", analysis["mounted_by_v1256"]],
        ["cleanup_ok", analysis["cleanup_ok"]],
        ["devnode_absent", analysis["devnode_absent"]],
        ["sysfs_dev_metadata_seen", analysis["sysfs_dev_metadata_seen"]],
        ["range_seen", analysis["range_seen"]],
        ["pmic_identity_seen", analysis["pmic_identity_seen"]],
        ["feasibility_candidate", analysis["feasibility_candidate"]],
    ]
    return "\n".join([
        "# V1256 GPIOChip Devnode Feasibility Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Summary",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]),
        "",
        "## Safety",
        "",
        "- read-only classifier; temporary debugfs mount is cleaned up when V1256 mounted it",
        "- no mknod, GPIO line request, PMIC/GPIO/debugfs/regulator write, eSoC ioctl, daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, reboot, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    steps: list[dict[str, Any]] = []
    mount_info: dict[str, Any] = {}
    if args.command != "plan":
        steps.extend(preflight_steps(args, store))
        if args.command == "run" and approved(args):
            mount_info = run_steps(args, store, steps)
    analysis = analyze(store, steps, mount_info)
    checks = build_checks(args.command, args, analysis, steps)
    decision, passed, reason, next_step = decide(args.command, checks, analysis)
    manifest = {
        "cycle": "v1256",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "steps": steps,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": args.command != "plan",
        "mknod_executed": False,
        "gpio_line_request_executed": False,
        "pmic_write_executed": False,
        "debugfs_write_executed": False,
        "regulator_write_executed": False,
        "gpio_write_executed": False,
        "esoc_ioctl_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "reboot_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {passed}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
