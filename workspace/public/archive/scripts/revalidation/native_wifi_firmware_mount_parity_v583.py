#!/usr/bin/env python3
"""V583 read-only firmware/modem mount parity classifier.

This tool compares Android firmware/modem mount evidence with the current
native-init global mount namespace and targeted ICNSS/remoteproc surfaces. It
does not mount, unmount, write sysfs, start daemons, scan, connect, or ping.
"""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v583-firmware-mount-parity")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_ANDROID_DMESG = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/dmesg-wifi-cnss-tail.txt")
DEFAULT_ANDROID_MOUNTS = Path("tmp/wifi/v206-android-icnss-cnss-map/android/commands/mounts-core.txt")
DEFAULT_V582_MANIFEST = Path("tmp/wifi/v582-modem-companion-classifier/manifest.json")

ANDROID_MOUNT_PATTERNS = {
    "vendor_firmware_mnt": re.compile(r"target=/vendor/firmware_mnt.*Success|/vendor/firmware_mnt", re.I),
    "vendor_firmware_modem": re.compile(r"target=/vendor/firmware-modem.*Success|/vendor/firmware-modem", re.I),
    "firmware_alias": re.compile(r"\s/firmware\s|symlink /vendor/firmware_mnt /firmware", re.I),
    "bt_firmware_alias": re.compile(r"\s/bt_firmware\s|symlink /vendor/bt_firmware /bt_firmware", re.I),
}
NATIVE_MOUNT_TARGETS = (
    "/system",
    "/mnt/system",
    "/vendor/firmware_mnt",
    "/vendor/firmware-modem",
    "/firmware",
    "/bt_firmware",
    "/vendor",
    "/system/vendor",
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
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-mounts", type=Path, default=DEFAULT_ANDROID_MOUNTS)
    parser.add_argument("--v582-manifest", type=Path, default=DEFAULT_V582_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def read_text_if_exists(path: Path) -> tuple[bool, str, str]:
    resolved = repo_path(path)
    if not resolved.exists():
        return False, str(resolved), ""
    return True, str(resolved), resolved.read_text(encoding="utf-8", errors="replace")


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def collect_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    return [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 25.0),
        run_step(args, store, "selftest", ["selftest"], 25.0),
        run_step(args, store, "proc-mounts", ["cat", "/proc/mounts"], 15.0),
        run_step(args, store, "proc-partitions", ["cat", "/proc/partitions"], 15.0),
        run_step(args, store, "ls-vendor", ["ls", "/vendor"], 10.0),
        run_step(args, store, "ls-vendor-firmware-mnt", ["ls", "/vendor/firmware_mnt"], 10.0),
        run_step(args, store, "ls-vendor-firmware-modem", ["ls", "/vendor/firmware-modem"], 10.0),
        run_step(args, store, "ls-firmware", ["ls", "/firmware"], 10.0),
        run_step(args, store, "ls-bt-firmware", ["ls", "/bt_firmware"], 10.0),
        run_step(args, store, "icnss-uevent", ["cat", "/sys/devices/platform/soc/18800000.qcom,icnss/uevent"], 10.0),
        run_step(args, store, "remoteproc-class", ["run", args.toybox, "find", "/sys/class/remoteproc", "-maxdepth", "2"], 20.0),
        run_step(args, store, "rpmsg-bus", ["run", args.toybox, "find", "/sys/bus/rpmsg", "-maxdepth", "3"], 20.0),
    ]


def android_mount_summary(args: argparse.Namespace) -> dict[str, Any]:
    dmesg_exists, dmesg_path, dmesg = read_text_if_exists(args.android_dmesg)
    mounts_exists, mounts_path, mounts = read_text_if_exists(args.android_mounts)
    combined = dmesg + "\n" + mounts
    hits = {name: bool(pattern.search(combined)) for name, pattern in ANDROID_MOUNT_PATTERNS.items()}
    lines = {}
    for name, pattern in ANDROID_MOUNT_PATTERNS.items():
        matched = []
        for raw in combined.splitlines():
            line = raw.strip()
            if line and pattern.search(line):
                matched.append(line)
                if len(matched) >= 6:
                    break
        lines[name] = matched
    return {
        "exists": dmesg_exists and mounts_exists,
        "paths": {"dmesg": dmesg_path, "mounts": mounts_path},
        "hits": hits,
        "lines": lines,
    }


def parse_mounts(text: str) -> dict[str, list[str]]:
    mounts: dict[str, list[str]] = {}
    for raw in text.splitlines():
        parts = raw.split()
        if len(parts) < 3:
            continue
        mounts.setdefault(parts[1], []).append(raw)
    return mounts


def native_summary(steps: list[dict[str, Any]]) -> dict[str, Any]:
    status_text = step_payload(steps, "status")
    selftest_text = step_payload(steps, "selftest")
    mounts_text = step_payload(steps, "proc-mounts")
    partitions_text = step_payload(steps, "proc-partitions")
    icnss_text = step_payload(steps, "icnss-uevent")
    remoteproc_text = step_payload(steps, "remoteproc-class")
    rpmsg_text = step_payload(steps, "rpmsg-bus")
    mounts = parse_mounts(mounts_text)
    mount_hits = {target: target in mounts for target in NATIVE_MOUNT_TARGETS}
    mount_lines = {target: mounts.get(target, []) for target in NATIVE_MOUNT_TARGETS}
    path_exists = {}
    for name in ("ls-vendor", "ls-vendor-firmware-mnt", "ls-vendor-firmware-modem", "ls-firmware", "ls-bt-firmware"):
        text = step_payload(steps, name)
        path_exists[name] = "No such file" not in text and "No such file or directory" not in text and bool(text.strip())
    return {
        "native_healthy": "fail=0" in status_text and "fail=0" in selftest_text,
        "mount_hits": mount_hits,
        "mount_lines": mount_lines,
        "path_exists": path_exists,
        "sda28_present": "sda28" in partitions_text,
        "sda29_present": "sda29" in partitions_text,
        "icnss_uevent_present": bool(icnss_text.strip()) and "No such file" not in icnss_text,
        "remoteproc_present": "No such file" not in remoteproc_text and bool(remoteproc_text.strip()),
        "rpmsg_present": "No such file" not in rpmsg_text and bool(rpmsg_text.strip()),
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace,
                 android: dict[str, Any],
                 native: dict[str, Any],
                 v582: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V583 classifier")
        return checks
    android_hits = android.get("hits") or {}
    native_mounts = native.get("mount_hits") or {}
    add_check(
        checks,
        "v582-reference-ready",
        "pass" if v582.get("decision") == "v582-kernel-modem-companion-readiness-gap-classified" else "blocked",
        "blocker",
        f"decision={v582.get('decision')} pass={v582.get('pass')}",
        [str(v582.get("path"))],
        "run V582 before V583 mount parity",
    )
    add_check(
        checks,
        "android-firmware-modem-mounts-present",
        "pass" if android_hits.get("vendor_firmware_mnt") and android_hits.get("vendor_firmware_modem") else "blocked",
        "blocker",
        f"firmware_mnt={android_hits.get('vendor_firmware_mnt')} firmware_modem={android_hits.get('vendor_firmware_modem')}",
        (android.get("lines") or {}).get("vendor_firmware_mnt", [])[:2] + (android.get("lines") or {}).get("vendor_firmware_modem", [])[:2],
        "refresh Android firmware mount evidence",
    )
    add_check(
        checks,
        "native-current-health",
        "pass" if native.get("native_healthy") else "blocked",
        "blocker",
        f"native_healthy={native.get('native_healthy')}",
        [],
        "restore native baseline before Wi-Fi work",
    )
    add_check(
        checks,
        "native-firmware-modem-mounts-missing",
        "pass" if not native_mounts.get("/vendor/firmware_mnt") and not native_mounts.get("/vendor/firmware-modem") else "blocked",
        "blocker",
        f"native_firmware_mnt={native_mounts.get('/vendor/firmware_mnt')} native_firmware_modem={native_mounts.get('/vendor/firmware-modem')}",
        (native.get("mount_lines") or {}).get("/vendor/firmware_mnt", []) + (native.get("mount_lines") or {}).get("/vendor/firmware-modem", []),
        "if present, inspect QRTR readiness instead of mount parity",
    )
    add_check(
        checks,
        "native-system-mounted-but-vendor-firmware-absent",
        "pass" if native_mounts.get("/system") and not native_mounts.get("/vendor") else "warn",
        "warning",
        f"system={native_mounts.get('/system')} vendor={native_mounts.get('/vendor')} system_vendor={native_mounts.get('/system/vendor')}",
        (native.get("mount_lines") or {}).get("/system", [])[:2],
        "define a bounded mount-parity proof before more qcwlanstate work",
    )
    add_check(
        checks,
        "native-icnss-surface-present",
        "pass" if native.get("icnss_uevent_present") and native.get("sda29_present") else "blocked",
        "blocker",
        f"icnss={native.get('icnss_uevent_present')} sda28={native.get('sda28_present')} sda29={native.get('sda29_present')}",
        [],
        "if ICNSS or modem partitions are absent, refresh kernel inventory",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v583-firmware-mount-parity-plan-ready", True, "plan-only; read-only classifier is ready", "run V583 classifier"
    blockers = blocking_checks(checks)
    if blockers:
        return "v583-firmware-mount-parity-blocked", False, "blocked by " + ", ".join(blockers), "refresh missing evidence before next Wi-Fi gate"
    return (
        "v583-native-firmware-modem-mount-parity-gap-classified",
        True,
        "Android mounts /vendor/firmware_mnt and /vendor/firmware-modem before QRTR modem readiness, while native currently has no global firmware/modem mount parity",
        "plan V584 bounded firmware/modem mount-parity proof before qcwlanstate/IWifi retry; keep scan/connect blocked",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    android = manifest.get("android_mounts") or {}
    native = manifest.get("native_surface") or {}
    native_rows = [
        ["native_healthy", native.get("native_healthy", "")],
        ["mount_hits", native.get("mount_hits", {})],
        ["path_exists", native.get("path_exists", {})],
        ["sda28_present", native.get("sda28_present", "")],
        ["sda29_present", native.get("sda29_present", "")],
        ["icnss_uevent_present", native.get("icnss_uevent_present", "")],
        ["remoteproc_present", native.get("remoteproc_present", "")],
        ["rpmsg_present", native.get("rpmsg_present", "")],
    ]
    android_rows = [
        ["exists", android.get("exists", "")],
        ["hits", android.get("hits", {})],
    ]
    return "\n".join([
        "# V583 Firmware Mount Parity Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], checks),
        "",
        "## Android Mount Evidence",
        "",
        markdown_table(["key", "value"], android_rows),
        "",
        "## Native Surface",
        "",
        markdown_table(["key", "value"], native_rows),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v582 = load_json_if_exists(args.v582_manifest)
    android = android_mount_summary(args)
    steps: list[dict[str, Any]] = []
    native: dict[str, Any] = {}
    if args.command == "run":
        steps = collect_steps(args, store)
        native = native_summary(steps)
    checks = build_checks(args, android, native, v582)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
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
        "v582_manifest": {
            "exists": v582.get("exists"),
            "path": v582.get("path"),
            "decision": v582.get("decision"),
            "pass": v582.get("pass"),
            "reason": v582.get("reason"),
        },
        "android_mounts": android,
        "native_surface": native,
        "device_commands_executed": args.command == "run",
        "device_mutations": False,
        "daemon_start_executed": False,
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
