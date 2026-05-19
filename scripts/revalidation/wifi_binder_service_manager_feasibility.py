#!/usr/bin/env python3
"""Read-only Binder/service-manager feasibility inventory for Wi-Fi HAL work."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v289-binder-service-manager")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_V288 = Path("tmp/wifi/v288-hal-framework-boundary-live-20260519-135154/manifest.json")
DEFAULT_TOYBOX = "/cache/bin/toybox"

LIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("config-zcat", ["run", DEFAULT_TOYBOX, "zcat", "/proc/config.gz"], 30.0),
    ("proc-filesystems", ["run", DEFAULT_TOYBOX, "cat", "/proc/filesystems"], 10.0),
    ("proc-devices", ["run", DEFAULT_TOYBOX, "cat", "/proc/devices"], 10.0),
    ("proc-misc", ["run", DEFAULT_TOYBOX, "cat", "/proc/misc"], 10.0),
    ("proc-mounts", ["run", DEFAULT_TOYBOX, "cat", "/proc/mounts"], 10.0),
    ("ls-dev", ["ls", "/dev"], 10.0),
    ("stat-dev-binder", ["stat", "/dev/binder"], 10.0),
    ("stat-dev-hwbinder", ["stat", "/dev/hwbinder"], 10.0),
    ("stat-dev-vndbinder", ["stat", "/dev/vndbinder"], 10.0),
    ("stat-sys-module-binder", ["stat", "/sys/module/binder"], 10.0),
    ("stat-sys-module-binder-linux", ["stat", "/sys/module/binder_linux"], 10.0),
    ("cat-binder-devices", ["run", DEFAULT_TOYBOX, "cat", "/sys/module/binder/parameters/devices"], 10.0),
    ("cat-binder-linux-devices", ["run", DEFAULT_TOYBOX, "cat", "/sys/module/binder_linux/parameters/devices"], 10.0),
    ("find-binder-sysfs", ["run", DEFAULT_TOYBOX, "find", "/sys", "-maxdepth", "4", "-iname", "*binder*"], 20.0),
    ("ps", ["run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm"], 20.0),
    ("stat-system-servicemanager", ["stat", "/mnt/system/system/bin/servicemanager"], 10.0),
    ("stat-system-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
    ("stat-system-vndservicemanager", ["stat", "/mnt/system/vendor/bin/vndservicemanager"], 10.0),
    ("find-service-manager-binaries", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "5", "-name", "*servicemanager*"], 20.0),
)

CONFIG_RE = re.compile(r"^(CONFIG_ANDROID_[A-Z0-9_]+)=(.*)$")
CONFIG_NOT_SET_RE = re.compile(r"^# (CONFIG_ANDROID_[A-Z0-9_]+) is not set$")


@dataclass
class CaptureSummary:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v288-manifest", type=Path, default=DEFAULT_V288)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def live_collect(args: argparse.Namespace, store: EvidenceStore) -> list[CaptureSummary]:
    captures: list[CaptureSummary] = []
    store.mkdir("native")
    for name, command, timeout in LIVE_COMMANDS:
        record = run_capture(args, name, command, timeout=timeout)
        text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
        rel = f"native/{safe_name(name)}.txt"
        store.write_text(rel, text)
        captures.append(
            CaptureSummary(
                name=name,
                command=record.command,
                ok=record.ok,
                rc=record.rc,
                status=record.status,
                duration_sec=record.duration_sec,
                file=rel,
                error=record.error,
            )
        )
    return captures


def capture_ok(captures: list[CaptureSummary], name: str) -> bool:
    return any(capture.name == name and capture.ok for capture in captures)


def capture_text(store: EvidenceStore, captures: list[CaptureSummary], name: str) -> str:
    for capture in captures:
        if capture.name != name:
            continue
        path = store.path(capture.file)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def parse_config(text: str) -> dict[str, str]:
    config: dict[str, str] = {}
    if text.startswith("\x1f\x8b"):
        try:
            text = gzip.decompress(text.encode("latin1")).decode("utf-8", errors="replace")
        except Exception:
            pass
    for raw in text.splitlines():
        line = raw.strip()
        match = CONFIG_RE.match(line)
        if match:
            config[match.group(1)] = match.group(2).strip().strip('"')
            continue
        match = CONFIG_NOT_SET_RE.match(line)
        if match:
            config[match.group(1)] = "n"
    return config


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(store: EvidenceStore, captures: list[CaptureSummary], expect_version: str) -> list[Check]:
    checks: list[Check] = []
    version_text = capture_text(store, captures, "version")
    config_text = capture_text(store, captures, "config-zcat")
    filesystems = capture_text(store, captures, "proc-filesystems")
    proc_misc = capture_text(store, captures, "proc-misc")
    proc_devices = capture_text(store, captures, "proc-devices")
    ps_text = capture_text(store, captures, "ps")
    sysfs_text = capture_text(store, captures, "find-binder-sysfs")
    manager_find = capture_text(store, captures, "find-service-manager-binaries")
    config = parse_config(config_text)

    binder_ipc = config.get("CONFIG_ANDROID_BINDER_IPC", "unknown")
    binder_devices = config.get("CONFIG_ANDROID_BINDER_DEVICES", "")
    binderfs = config.get("CONFIG_ANDROID_BINDERFS", "unknown")

    add_check(
        checks,
        "native-version",
        "present" if expect_version in version_text else "mismatch",
        "info" if expect_version in version_text else "warning",
        f"expect_version={expect_version}",
        [line for line in version_text.splitlines() if "A90 Linux init" in line][:3],
        "refresh baseline if device build changed",
    )
    add_check(
        checks,
        "kernel-config-binder-ipc",
        "enabled" if binder_ipc == "y" else ("module" if binder_ipc == "m" else "missing"),
        "info" if binder_ipc in {"y", "m"} else "blocker",
        f"CONFIG_ANDROID_BINDER_IPC={binder_ipc}",
        [line for line in config_text.splitlines() if "CONFIG_ANDROID_BINDER" in line][:10],
        "kernel support is required before any Binder devnode plan",
    )
    add_check(
        checks,
        "kernel-config-binder-devices",
        "configured" if all(name in binder_devices for name in ("binder", "hwbinder", "vndbinder")) else "incomplete",
        "info" if binder_devices else "warning",
        f"CONFIG_ANDROID_BINDER_DEVICES={binder_devices or 'missing'}",
        [line for line in config_text.splitlines() if "CONFIG_ANDROID_BINDER_DEVICES" in line][:4],
        "if configured, missing /dev nodes may be a device-node creation issue",
    )
    add_check(
        checks,
        "kernel-config-binderfs",
        "enabled" if binderfs in {"y", "m"} else ("missing" if binderfs == "n" else "unknown"),
        "info" if binderfs in {"y", "m"} else "warning",
        f"CONFIG_ANDROID_BINDERFS={binderfs}",
        [line for line in config_text.splitlines() if "CONFIG_ANDROID_BINDERFS" in line][:4],
        "binderfs remains a separate explicit mount/ioctl plan if supported",
    )
    binderfs_filesystem = any("binder" in line for line in filesystems.splitlines())
    add_check(
        checks,
        "proc-filesystems-binderfs",
        "present" if binderfs_filesystem else "absent",
        "info" if binderfs_filesystem else "warning",
        "binder filesystem listed in /proc/filesystems" if binderfs_filesystem else "binder filesystem not listed",
        [line for line in filesystems.splitlines() if "binder" in line][:8],
        "do not mount binderfs without a separate plan",
    )
    misc_hits = [line.strip() for line in proc_misc.splitlines() if "binder" in line]
    device_hits = [line.strip() for line in proc_devices.splitlines() if "binder" in line.lower()]
    add_check(
        checks,
        "proc-registered-binder-devices",
        "present" if misc_hits or device_hits else "absent",
        "info" if misc_hits or device_hits else "warning",
        f"proc_misc_hits={len(misc_hits)} proc_devices_hits={len(device_hits)}",
        (misc_hits + device_hits)[:12],
        "registered misc devices can guide future private devnode plan",
    )
    for node in ("binder", "hwbinder", "vndbinder"):
        name = f"stat-dev-{node}"
        add_check(
            checks,
            f"native-devnode-{node}",
            "present" if capture_ok(captures, name) else "absent",
            "info" if capture_ok(captures, name) else "blocker",
            f"/dev/{node} {'visible' if capture_ok(captures, name) else 'not visible'}",
            capture_text(store, captures, name).splitlines()[:4],
            "future fix may be devtmpfs/uevent/device-node creation, not HAL execution",
        )
    sysfs_hits = [line.strip() for line in sysfs_text.splitlines() if "binder" in line.lower()]
    add_check(
        checks,
        "binder-sysfs-surface",
        "present" if sysfs_hits else "absent",
        "info" if sysfs_hits else "warning",
        f"binder_sysfs_hits={len(sysfs_hits)}",
        sysfs_hits[:12],
        "use read-only sysfs clues before deciding mknod or binderfs plan",
    )
    manager_binaries = [
        name
        for name in ("stat-system-servicemanager", "stat-system-hwservicemanager", "stat-system-vndservicemanager")
        if capture_ok(captures, name)
    ]
    manager_processes = [
        line.strip()
        for line in ps_text.splitlines()
        if any(term in line for term in ("servicemanager", "hwservicemanager", "vndservicemanager"))
    ]
    add_check(
        checks,
        "service-manager-binaries",
        "present" if manager_binaries or manager_find.strip() else "absent",
        "warning" if manager_binaries or manager_find.strip() else "blocker",
        f"stat_hits={len(manager_binaries)} find_lines={len(manager_find.splitlines()) if manager_find.strip() else 0}",
        manager_binaries + manager_find.splitlines()[:8],
        "binary visibility is only inventory; do not execute service managers yet",
    )
    add_check(
        checks,
        "service-manager-processes",
        "present" if manager_processes else "absent",
        "info" if manager_processes else "blocker",
        f"process_count={len(manager_processes)}",
        manager_processes[:8],
        "service-manager process model is required before HAL/wificond execution",
    )
    return checks


def classify(input_errors: list[str], checks: list[Check], mode: str) -> tuple[bool, str, str]:
    if input_errors:
        return False, "binder-service-manager-input-missing", "; ".join(input_errors)
    if mode == "plan":
        return True, "binder-service-manager-feasibility-ready", "plan inputs are ready"
    by_name = {check.name: check for check in checks}
    binder_ipc_ready = by_name.get("kernel-config-binder-ipc", Check("", "", "", "", [], "")).status in {"enabled", "module"}
    devnodes_missing = any(
        by_name.get(f"native-devnode-{node}", Check("", "", "", "", [], "")).status == "absent"
        for node in ("binder", "hwbinder", "vndbinder")
    )
    binderfs_ready = by_name.get("kernel-config-binderfs", Check("", "", "", "", [], "")).status == "enabled" or by_name.get("proc-filesystems-binderfs", Check("", "", "", "", [], "")).status == "present"
    if binder_ipc_ready and devnodes_missing and binderfs_ready:
        return True, "binderfs-feasible-devnodes-missing", "binder kernel support appears present; /dev nodes are missing and binderfs may be feasible"
    if binder_ipc_ready and devnodes_missing:
        return True, "binder-kernel-present-devnodes-missing", "binder kernel support appears present but /dev nodes are missing"
    if not binder_ipc_ready:
        return True, "binder-kernel-support-missing", "binder kernel support not visible in read-only evidence"
    return True, "binder-service-manager-feasibility-ready", "binder inventory completed"


def render_summary(manifest: dict[str, Any]) -> str:
    rows = []
    for check in manifest["checks"]:
        rows.append([check["name"], check["status"], check["severity"], check["detail"], check["next_step"]])
    lines = [
        "# v289 Binder / Service-Manager Feasibility\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- mode: `{manifest['mode']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: {manifest['reason']}\n\n",
        "## Checks\n\n",
        markdown_table(["check", "status", "severity", "detail", "next"], rows),
        "\n\n## Guardrails\n\n",
    ]
    lines.extend(f"- {item}\n" for item in manifest["guardrails"])
    lines.extend([
        "\n## Recommendation\n\n",
        "- Do not create Binder nodes, mount binderfs, or start service managers until a separate v290 plan approves the exact primitive.\n",
        "- HAL and `wificond` remain blocked while Binder nodes or service-manager processes are missing.\n",
    ])
    return "".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v288 = load_manifest(args.v288_manifest)
    input_errors: list[str] = []
    if not v288.get("present"):
        input_errors.append(f"v288 missing: {v288.get('path')}")
    elif v288.get("pass") is not True:
        input_errors.append("v288 pass expected true")
    elif v288.get("decision") not in {"hal-framework-boundary-native-blocked", "hal-framework-boundary-inventory-ready"}:
        input_errors.append(f"unexpected v288 decision: {v288.get('decision')}")

    captures: list[CaptureSummary] = []
    checks: list[Check] = []
    if args.command == "run" and not input_errors:
        captures = live_collect(args, store)
        checks = build_checks(store, captures, args.expect_version)
    pass_ok, decision, reason = classify(input_errors, checks, args.command)
    return {
        "created": now_iso(),
        "mode": args.command,
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "inputs": {"v288_manifest": str(repo_path(args.v288_manifest))},
        "source_decisions": {"v288": v288.get("decision")},
        "input_errors": input_errors,
        "captures": [asdict(capture) for capture in captures],
        "checks": [asdict(check) for check in checks],
        "execution_ready": False,
        "next_recommendation": "v290 exact Binder devnode or binderfs plan if user approves non-read-only primitive",
        "guardrails": [
            "no mknod",
            "no binderfs mount",
            "no Binder ioctl",
            "no service-manager execution",
            "no Wi-Fi daemon execution",
            "no QMI/QRTR packet",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill/ICNSS writes",
            "no Android partition write",
            "mountsystem ro allowed only for read-only binary visibility",
        ],
        "host_metadata": collect_host_metadata(),
    }


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_json("checks.json", {"checks": manifest["checks"]})
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {out_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
