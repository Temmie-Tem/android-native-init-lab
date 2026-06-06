#!/usr/bin/env python3
"""Collect guarded native ICNSS firmware request evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


PROBE_PREFIX = "/tmp/a90-v213-"
EXPECTED_BLOCK = "sda29"
EXPECTED_MAJOR = "259"
EXPECTED_MINOR = "22"
VENDOR_MOUNTPOINT = "/mnt/vendor"
FIRMWARE_ROOT = "/mnt/vendor/firmware"
FIRMWARE_CLASS_PATH = "/sys/module/firmware_class/parameters/path"
FWPATH_HELPER = "/cache/bin/a90_fwpathctl"
ICNSS_HELPER = "/cache/bin/a90_icnssctl"
ICNSS_ID = "18800000.qcom,icnss"
ICNSS_NODE = "/sys/devices/platform/soc/18800000.qcom,icnss"
ICNSS_DRIVER = "/sys/bus/platform/drivers/icnss"
ICNSS_BIND = f"{ICNSS_DRIVER}/bind"
ICNSS_UNBIND = f"{ICNSS_DRIVER}/unbind"

V209_EXPECTED_DECISION = "vendor-assets-visible"
V210_EXPECTED_DECISION = "firmware-path-policy-needed"
V211_EXPECTED_DECISION = "sysfs-path-update-needed"
V212_EXPECTED_DECISION = "path-rollback-pass"
DEFAULT_V209_MANIFEST = Path("tmp/wifi/v209-vendor-ro-mount-probe/manifest.json")
DEFAULT_V210_MANIFEST = Path("tmp/wifi/v210-vendor-asset-classifier/manifest.json")
DEFAULT_V211_MANIFEST = Path("tmp/wifi/v211-firmware-path-policy/manifest.json")
DEFAULT_V212_MANIFEST = Path("tmp/wifi/v212-firmware-path-rollback/manifest.json")

LIKELY_REQUEST_NAMES = (
    "wlan/qca_cld/WCNSS_qcom_cfg.ini",
    "wlan/qca_cld/bdwlan.bin",
    "wlan/qca_cld/regdb.bin",
    "wlanmdsp.mbn",
)
REQUIRED_FIRMWARE_PATHS = tuple(f"{FIRMWARE_ROOT}/{name}" for name in LIKELY_REQUEST_NAMES)

DECISIONS = {
    "baseline-only",
    "path-only-pass",
    "request-evidence-captured",
    "request-evidence-missing",
    "reprobe-helper-unavailable",
    "icnss-rebind-failed",
    "path-rollback-failed",
    "cleanup-failed",
    "manual-review-required",
}

ACTIVE_WIFI_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bdumpsys\s+wifi\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\b(?:cnss-daemon|cnss_diag|wificond|hostapd|wpa_supplicant)\b", re.IGNORECASE),
)

FORBIDDEN_STORAGE_PATTERNS = (
    re.compile(r"\bmountfs\b", re.IGNORECASE),
    re.compile(r"\bmount\b.*\s--bind\b", re.IGNORECASE),
    re.compile(r"\bmount\b.*\s-o\s+bind\b", re.IGNORECASE),
    re.compile(r"\b(?:dd|mkfs|sgdisk|parted|fsck|e2fsck)\b", re.IGNORECASE),
    re.compile(r"\bblockdev\s+--set", re.IGNORECASE),
    re.compile(r"\bdmsetup\s+(?:create|remove|load|reload|suspend|resume)\b", re.IGNORECASE),
)

SAFE_PATH_RE = re.compile(r"^/[A-Za-z0-9_./+-]{0,255}$")
DMESG_FILTER_RE = re.compile(
    r"firmware|icnss|cnss|wlan|wifi|qca|wcn|bdwlan|regdb|wlanmdsp|WCNSS",
    re.IGNORECASE,
)


@dataclass
class CaptureRecord:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    text: str
    error: str


@dataclass(frozen=True)
class ProbePaths:
    run_id: str
    base: str
    node: str
    major: str
    minor: str
    dev_path: str


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v213-firmware-request-evidence"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v209-manifest", type=Path, default=DEFAULT_V209_MANIFEST)
    parser.add_argument("--v210-manifest", type=Path, default=DEFAULT_V210_MANIFEST)
    parser.add_argument("--v211-manifest", type=Path, default=DEFAULT_V211_MANIFEST)
    parser.add_argument("--v212-manifest", type=Path, default=DEFAULT_V212_MANIFEST)
    parser.add_argument("--run-id", default="", help="optional safe suffix for /tmp/a90-v213-<run-id>")
    parser.add_argument("--allow-non-v209-decision", action="store_true")
    parser.add_argument("--allow-non-v210-decision", action="store_true")
    parser.add_argument("--allow-non-v211-decision", action="store_true")
    parser.add_argument("--allow-non-v212-decision", action="store_true")
    parser.add_argument("--apply-path", action="store_true", help="temporarily apply firmware_class.path")
    parser.add_argument("--reprobe", action="store_true", help="opt-in ICNSS unbind/bind evidence probe")
    parser.add_argument("--i-understand-icnss-reprobe", action="store_true")
    parser.add_argument("--native-bridge", action="store_true", help="document intent; native bridge is the current mode")
    return parser.parse_args()


def make_run_id(value: str = "") -> str:
    run_id = value or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.+-]{1,64}", run_id):
        raise RuntimeError(f"unsafe run id: {run_id!r}")
    return run_id


def make_probe_paths(run_id: str, major: str = EXPECTED_MAJOR, minor: str = EXPECTED_MINOR) -> ProbePaths:
    base = f"{PROBE_PREFIX}{run_id}"
    return ProbePaths(
        run_id=run_id,
        base=base,
        node=f"{base}/{EXPECTED_BLOCK}",
        major=major,
        minor=minor,
        dev_path=f"/sys/dev/block/{major}:{minor}",
    )


def probe_from_sda29_dev(run_id: str, sda29_dev: str | None) -> ProbePaths:
    if sda29_dev is None or not re.fullmatch(r"\d+:\d+", sda29_dev):
        return make_probe_paths(run_id)
    major, minor = sda29_dev.split(":", 1)
    return make_probe_paths(run_id, major, minor)


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def command_text(command: list[str]) -> str:
    return " ".join(command)


def is_under_probe_path(path: str, probe: ProbePaths) -> bool:
    return path == probe.base or path.startswith(probe.base + "/")


def is_under_vendor_path(path: str) -> bool:
    return path == VENDOR_MOUNTPOINT or path.startswith(VENDOR_MOUNTPOINT + "/")


def firmware_write_command(value: str) -> list[str]:
    if not SAFE_PATH_RE.fullmatch(value):
        raise RuntimeError(f"unsafe firmware path value: {value!r}")
    return ["run", FWPATH_HELPER, "write", value]


def icnss_command(action: str) -> list[str]:
    if action not in {"status", "unbind", "bind"}:
        raise RuntimeError(f"unsupported ICNSS action: {action}")
    return ["run", ICNSS_HELPER, action]


def allowed_read_path(path: str, probe: ProbePaths) -> bool:
    exact_paths = {
        "/proc/mounts",
        "/proc/filesystems",
        "/proc/dynamic_debug/control",
        "/sys/kernel/tracing/events",
        "/sys/kernel/debug/tracing/events/firmware",
        FIRMWARE_CLASS_PATH,
        "/tmp",
        "/mnt",
        VENDOR_MOUNTPOINT,
        FWPATH_HELPER,
        ICNSS_HELPER,
        ICNSS_BIND,
        ICNSS_UNBIND,
        ICNSS_DRIVER,
        ICNSS_NODE,
        f"{ICNSS_NODE}/uevent",
        f"{ICNSS_NODE}/modalias",
        f"{ICNSS_NODE}/ramdump",
        f"{ICNSS_NODE}/wakeup",
        "/sys/class/net",
        "/sys/class/rfkill",
        "/sys/class/ieee80211",
        "/sys/class/block/sda29/dev",
        "/sys/class/block/sda29/size",
        "/sys/class/block/sda29/ro",
    }
    return (
        path in exact_paths
        or path == probe.dev_path
        or path.startswith(f"{ICNSS_NODE}/")
        or path.startswith("/sys/class/block/sda29/")
        or is_under_probe_path(path, probe)
        or is_under_vendor_path(path)
    )


def validate_no_active_wifi_commands() -> None:
    forbidden_samples = (
        ["run", "/cache/bin/toybox", "ip", "link", "set", "wlan0", "up"],
        ["run", "/cache/bin/toybox", "rfkill", "unblock", "wifi"],
        ["run", "/system/bin/cmd", "wifi", "set-wifi-enabled", "enabled"],
        ["run", "/vendor/bin/cnss-daemon"],
        ["run", "/system/bin/wpa_supplicant"],
    )
    probe = make_probe_paths("guard")
    for command in forbidden_samples:
        try:
            validate_command(command, probe, apply_path=False, reprobe=False, confirm_reprobe=False)
        except RuntimeError:
            continue
        raise RuntimeError(f"guard allowed active Wi-Fi command: {command_text(command)}")


def validate_command(
    command: list[str],
    probe: ProbePaths,
    *,
    apply_path: bool,
    reprobe: bool,
    confirm_reprobe: bool,
    original_path: str | None = None,
) -> None:
    if not command:
        raise RuntimeError("empty command")
    joined = command_text(command)
    if ">" in joined:
        raise RuntimeError(f"unexpected shell write command: {joined}")
    for pattern in ACTIVE_WIFI_PATTERNS + FORBIDDEN_STORAGE_PATTERNS:
        if pattern.search(joined):
            raise RuntimeError(f"forbidden command pattern {pattern.pattern!r}: {joined}")

    name = command[0]
    if name in {"version", "status", "bootstatus"}:
        return
    if name in {"cat", "ls", "stat"}:
        if len(command) != 2:
            raise RuntimeError(f"unexpected {name} arity: {joined}")
        if allowed_read_path(command[1], probe):
            return
        raise RuntimeError(f"{name} outside allowed paths: {joined}")
    if name == "mkdir":
        if len(command) == 2 and (command[1] == VENDOR_MOUNTPOINT or is_under_probe_path(command[1], probe)):
            return
        raise RuntimeError(f"mkdir outside allowed path: {joined}")
    if name == "mknodb":
        if command == ["mknodb", probe.node, probe.major, probe.minor]:
            return
        raise RuntimeError(f"unexpected mknodb command: {joined}")
    if name == "umount":
        if command == ["umount", VENDOR_MOUNTPOINT]:
            return
        raise RuntimeError(f"unexpected umount command: {joined}")
    if name == "run":
        expected_mount = ["run", "/cache/bin/toybox", "mount", "-t", "ext4", "-o", "ro,noload", probe.node, VENDOR_MOUNTPOINT]
        if command == expected_mount:
            return
        if command == ["run", "/cache/bin/toybox", "dmesg"]:
            return
        if command == ["run", FWPATH_HELPER, "read"]:
            return
        if apply_path and command == firmware_write_command(FIRMWARE_ROOT):
            return
        if apply_path and original_path is not None and command == firmware_write_command(original_path):
            return
        if command[1:2] == [ICNSS_HELPER]:
            if command == icnss_command("status"):
                return
            if reprobe and confirm_reprobe and (
                command == icnss_command("unbind") or command == icnss_command("bind")
            ):
                return
            raise RuntimeError(f"unexpected ICNSS helper command: {joined}")
        if len(command) >= 3 and command[1] == "/cache/bin/toybox" and command[2] == "mount":
            raise RuntimeError(f"mount command must be exact ro,noload probe mount: {joined}")
        raise RuntimeError(f"unexpected run command: {joined}")
    raise RuntimeError(f"unexpected command: {joined}")


def validate_command_guard() -> None:
    probe = make_probe_paths("guard")
    original = "/vendor/firmware_mnt/image"
    for _, command, _ in baseline_commands() + preflight_commands(probe) + asset_commands() + cleanup_commands(probe):
        validate_command(command, probe, apply_path=False, reprobe=False, confirm_reprobe=False, original_path=original)
    for _, command, _ in path_apply_commands(original):
        validate_command(command, probe, apply_path=True, reprobe=False, confirm_reprobe=False, original_path=original)
    for _, command, _ in reprobe_commands():
        validate_command(command, probe, apply_path=True, reprobe=True, confirm_reprobe=True, original_path=original)
    validate_no_active_wifi_commands()


def baseline_commands() -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("version", ["version"], 15.0),
        ("status", ["status"], 25.0),
        ("bootstatus", ["bootstatus"], 25.0),
        ("firmware-class-path-before", ["cat", FIRMWARE_CLASS_PATH], 20.0),
        ("pre-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        ("proc-filesystems", ["cat", "/proc/filesystems"], 20.0),
        ("sys-sda29-dev", ["cat", "/sys/class/block/sda29/dev"], 20.0),
        ("dynamic-debug-control", ["stat", "/proc/dynamic_debug/control"], 20.0),
        ("tracing-events", ["ls", "/sys/kernel/tracing/events"], 20.0),
        ("debug-tracing-firmware-events", ["ls", "/sys/kernel/debug/tracing/events/firmware"], 20.0),
        ("icnss-uevent", ["cat", f"{ICNSS_NODE}/uevent"], 20.0),
        ("icnss-modalias", ["cat", f"{ICNSS_NODE}/modalias"], 20.0),
        ("icnss-node", ["ls", ICNSS_NODE], 20.0),
        ("icnss-ramdump", ["ls", f"{ICNSS_NODE}/ramdump"], 20.0),
        ("icnss-wakeup", ["ls", f"{ICNSS_NODE}/wakeup"], 20.0),
        ("icnss-driver", ["ls", ICNSS_DRIVER], 20.0),
        ("icnss-bind-stat", ["stat", ICNSS_BIND], 20.0),
        ("icnss-unbind-stat", ["stat", ICNSS_UNBIND], 20.0),
        ("class-net-before", ["ls", "/sys/class/net"], 20.0),
        ("class-rfkill-before", ["ls", "/sys/class/rfkill"], 20.0),
        ("class-ieee80211-before", ["ls", "/sys/class/ieee80211"], 20.0),
        ("dmesg-before", ["run", "/cache/bin/toybox", "dmesg"], 45.0),
    )


def preflight_commands(probe: ProbePaths) -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("sys-sda29-size", ["cat", "/sys/class/block/sda29/size"], 20.0),
        ("sys-sda29-ro", ["cat", "/sys/class/block/sda29/ro"], 20.0),
        ("sys-dev-block-sda29", ["ls", probe.dev_path], 20.0),
        ("mkdir-probe-base", ["mkdir", probe.base], 20.0),
        ("mkdir-vendor-mountpoint", ["mkdir", VENDOR_MOUNTPOINT], 20.0),
        ("mknodb-sda29", ["mknodb", probe.node, probe.major, probe.minor], 20.0),
        ("temp-node-stat", ["stat", probe.node], 20.0),
        ("safe-ro-noload-mount", ["run", "/cache/bin/toybox", "mount", "-t", "ext4", "-o", "ro,noload", probe.node, VENDOR_MOUNTPOINT], 45.0),
        ("mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0),
    )


def asset_commands() -> tuple[tuple[str, list[str], float], ...]:
    commands: list[tuple[str, list[str], float]] = [
        ("mounted-vendor-root", ["ls", VENDOR_MOUNTPOINT], 20.0),
        ("mounted-firmware-root", ["ls", FIRMWARE_ROOT], 20.0),
        ("mounted-qca-cld", ["ls", f"{FIRMWARE_ROOT}/wlan/qca_cld"], 20.0),
    ]
    for path in REQUIRED_FIRMWARE_PATHS:
        commands.append((f"asset-{safe_name(path)}", ["stat", path], 20.0))
    return tuple(commands)


def path_apply_commands(original_path: str) -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("fwpath-helper-stat", ["stat", FWPATH_HELPER], 20.0),
        ("fwpath-helper-read-before", ["run", FWPATH_HELPER, "read"], 20.0),
        ("apply-firmware-class-path", firmware_write_command(FIRMWARE_ROOT), 20.0),
        ("firmware-class-path-applied", ["cat", FIRMWARE_CLASS_PATH], 20.0),
        ("post-apply-dmesg", ["run", "/cache/bin/toybox", "dmesg"], 45.0),
        ("rollback-firmware-class-path", firmware_write_command(original_path), 20.0),
        ("firmware-class-path-rolled-back", ["cat", FIRMWARE_CLASS_PATH], 20.0),
    )


def reprobe_commands() -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("icnss-helper-stat", ["stat", ICNSS_HELPER], 20.0),
        ("icnss-helper-status-before", icnss_command("status"), 20.0),
        ("icnss-unbind", icnss_command("unbind"), 30.0),
        ("icnss-driver-after-unbind", ["ls", ICNSS_DRIVER], 20.0),
        ("icnss-bind", icnss_command("bind"), 45.0),
        ("icnss-helper-status-after", icnss_command("status"), 20.0),
        ("icnss-node-after", ["ls", ICNSS_NODE], 20.0),
        ("class-net-after", ["ls", "/sys/class/net"], 20.0),
        ("class-rfkill-after", ["ls", "/sys/class/rfkill"], 20.0),
        ("class-ieee80211-after", ["ls", "/sys/class/ieee80211"], 20.0),
        ("dmesg-after-reprobe", ["run", "/cache/bin/toybox", "dmesg"], 45.0),
    )


def cleanup_commands(probe: ProbePaths) -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("cleanup-umount", ["umount", VENDOR_MOUNTPOINT], 25.0),
        ("post-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        ("post-firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 20.0),
        ("tmp-base-after", ["ls", probe.base], 20.0),
    )


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/commands/{safe_name(name)}.txt", redact_text(text).rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_device(
    store: EvidenceStore,
    args: argparse.Namespace,
    probe: ProbePaths,
    name: str,
    command: list[str],
    timeout: float,
    *,
    original_path: str | None = None,
) -> CaptureRecord:
    validate_command(
        command,
        probe,
        apply_path=args.apply_path,
        reprobe=args.reprobe,
        confirm_reprobe=args.i_understand_icnss_reprobe,
        original_path=original_path,
    )
    capture = run_capture(args, name, command, timeout=timeout)
    body = capture.text if capture.text else f"{capture.error}\n"
    relative = write_capture(store, name, body)
    data = capture_to_manifest(capture)
    return CaptureRecord(
        name=name,
        command=command_text(command),
        ok=bool(data["ok"]),
        rc=data.get("rc"),
        status=str(data.get("status", "missing")),
        duration_sec=float(data["duration_sec"]),
        file=relative,
        text=redact_text(body if capture.text else ""),
        error=str(data.get("error", "")),
    )


def run_sequence(
    store: EvidenceStore,
    args: argparse.Namespace,
    probe: ProbePaths,
    sequence: tuple[tuple[str, list[str], float], ...],
    captures: list[CaptureRecord],
    *,
    original_path: str | None = None,
) -> None:
    for name, command, timeout in sequence:
        captures.append(capture_device(store, args, probe, name, command, timeout, original_path=original_path))


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_decision(manifest: dict[str, Any] | None) -> str | None:
    if not manifest:
        return None
    return manifest.get("decision") or manifest.get("classification", {}).get("decision")


def capture_by_name(captures: list[CaptureRecord], name: str) -> CaptureRecord | None:
    for capture in captures:
        if capture.name == name:
            return capture
    return None


def capture_ok(captures: list[CaptureRecord], *names: str) -> bool:
    return any((capture := capture_by_name(captures, name)) is not None and capture.ok for name in names)


def capture_text(captures: list[CaptureRecord], *names: str) -> str:
    chunks: list[str] = []
    for name in names:
        capture = capture_by_name(captures, name)
        if capture is not None:
            chunks.append(strip_cmdv1_text(capture.text))
    return "\n".join(chunks)


def first_line_value(captures: list[CaptureRecord], name: str) -> str:
    raw = capture_text(captures, name).strip()
    return raw.splitlines()[0].strip() if raw.splitlines() else ""


def mountpoint_in_text(text: str, mountpoint: str) -> bool:
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == mountpoint:
            return True
    return False


def probe_mount_in_text(text: str, probe: ProbePaths) -> bool:
    return any(probe.base in line for line in text.splitlines())


def path_visible(captures: list[CaptureRecord], path: str) -> bool:
    capture = capture_by_name(captures, f"asset-{safe_name(path)}")
    return capture is not None and capture.ok


def filtered_dmesg_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in strip_cmdv1_text(text).splitlines():
        line = raw_line.strip()
        if line and DMESG_FILTER_RE.search(line):
            lines.append(line)
    return lines


def dmesg_lines(captures: list[CaptureRecord], name: str) -> list[str]:
    capture = capture_by_name(captures, name)
    return filtered_dmesg_lines(capture.text) if capture is not None else []


def contains_wifiish(text: str) -> bool:
    return bool(re.search(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|phy\d+)\b", text, re.IGNORECASE))


def icnss_bound(captures: list[CaptureRecord]) -> bool:
    return (
        "DRIVER=icnss" in capture_text(captures, "icnss-uevent")
        or ICNSS_ID in capture_text(captures, "icnss-driver")
    )


def icnss_bound_after_reprobe(captures: list[CaptureRecord]) -> bool:
    return (
        "DRIVER=icnss" in capture_text(captures, "icnss-helper-status-after")
        or ICNSS_ID in capture_text(captures, "icnss-node-after")
    )


def request_matrix(captures: list[CaptureRecord]) -> list[dict[str, Any]]:
    return [
        {"request": request, "path": path, "visible": path_visible(captures, path)}
        for request, path in zip(LIKELY_REQUEST_NAMES, REQUIRED_FIRMWARE_PATHS, strict=True)
    ]


def relevant_lines(captures: list[CaptureRecord], probe: ProbePaths, limit: int = 180) -> list[str]:
    lines: list[str] = []
    keywords = ("firmware", "icnss", "cnss", "wlan", "wifi", "qca", "wcn", "bdwlan", "regdb", "wlanmdsp", "WCNSS", probe.base, "/mnt/vendor")
    for capture in captures:
        for raw_line in strip_cmdv1_text(capture.text).splitlines():
            line = raw_line.strip()
            if line and any(token.lower() in line.lower() for token in keywords) and line not in lines:
                lines.append(line)
            if len(lines) >= limit:
                return lines
    return lines


def classify(
    captures: list[CaptureRecord],
    probe: ProbePaths,
    args: argparse.Namespace,
    v209: dict[str, Any] | None,
    v210: dict[str, Any] | None,
    v211: dict[str, Any] | None,
    v212: dict[str, Any] | None,
) -> dict[str, Any]:
    v209_decision = manifest_decision(v209)
    v210_decision = manifest_decision(v210)
    v211_decision = manifest_decision(v211)
    v212_decision = manifest_decision(v212)
    basic_control_ok = capture_ok(captures, "version", "status")
    original_path = first_line_value(captures, "firmware-class-path-before")
    pre_mounts = capture_text(captures, "pre-proc-mounts")
    post_mounts = capture_text(captures, "post-proc-mounts")
    pre_existing_vendor_mount = mountpoint_in_text(pre_mounts, VENDOR_MOUNTPOINT)
    leftover_vendor_mount = mountpoint_in_text(post_mounts, VENDOR_MOUNTPOINT)
    leftover_probe_mount = probe_mount_in_text(post_mounts, probe)
    ext4_available = "ext4" in capture_text(captures, "proc-filesystems").split()
    sda29_dev = first_line_value(captures, "sys-sda29-dev")
    expected_major_minor = bool(sda29_dev and re.fullmatch(r"\d+:\d+", sda29_dev))
    mount_ok = capture_ok(captures, "safe-ro-noload-mount")
    mounted_after_mount = mountpoint_in_text(capture_text(captures, "mounted-proc-mounts"), VENDOR_MOUNTPOINT)
    missing_likely = [row["request"] for row in request_matrix(captures) if not row["visible"]]
    helper_available = (not args.apply_path) or (capture_ok(captures, "fwpath-helper-stat") and capture_ok(captures, "fwpath-helper-read-before"))
    applied_path = first_line_value(captures, "firmware-class-path-applied")
    rolled_back_path = first_line_value(captures, "firmware-class-path-rolled-back")
    post_path = first_line_value(captures, "post-firmware-class-path")
    apply_ok = (not args.apply_path) or (capture_ok(captures, "apply-firmware-class-path") and applied_path == FIRMWARE_ROOT)
    rollback_ok = (not args.apply_path) or (capture_ok(captures, "rollback-firmware-class-path") and rolled_back_path == original_path and (not post_path or post_path == original_path))
    reprobe_helper_available = (not args.reprobe) or (capture_ok(captures, "icnss-helper-stat") and capture_ok(captures, "icnss-helper-status-before"))
    reprobe_attempted = capture_by_name(captures, "icnss-unbind") is not None or capture_by_name(captures, "icnss-bind") is not None
    icnss_bound_before = icnss_bound(captures)
    icnss_bound_after = icnss_bound_after_reprobe(captures)
    rebind_ok = (not args.reprobe) or (capture_ok(captures, "icnss-bind") and icnss_bound_after)
    dmesg_before = set(dmesg_lines(captures, "dmesg-before"))
    dmesg_after = set(dmesg_lines(captures, "dmesg-after-reprobe"))
    dmesg_delta = sorted(dmesg_after - dmesg_before)
    post_wifiish = contains_wifiish(capture_text(captures, "class-net-after", "class-rfkill-after", "class-ieee80211-after"))
    request_evidence = bool(dmesg_delta or post_wifiish)

    if not basic_control_ok:
        decision = "manual-review-required"
        reason = "native bridge/control commands did not return usable evidence"
    elif not args.allow_non_v209_decision and v209_decision != V209_EXPECTED_DECISION:
        decision = "manual-review-required"
        reason = f"v209 decision is {v209_decision!r}, expected {V209_EXPECTED_DECISION!r}"
    elif not args.allow_non_v210_decision and v210_decision != V210_EXPECTED_DECISION:
        decision = "manual-review-required"
        reason = f"v210 decision is {v210_decision!r}, expected {V210_EXPECTED_DECISION!r}"
    elif not args.allow_non_v211_decision and v211_decision != V211_EXPECTED_DECISION:
        decision = "manual-review-required"
        reason = f"v211 decision is {v211_decision!r}, expected {V211_EXPECTED_DECISION!r}"
    elif not args.allow_non_v212_decision and v212_decision != V212_EXPECTED_DECISION:
        decision = "manual-review-required"
        reason = f"v212 decision is {v212_decision!r}, expected {V212_EXPECTED_DECISION!r}"
    elif args.reprobe and not (args.apply_path and args.i_understand_icnss_reprobe):
        decision = "manual-review-required"
        reason = "ICNSS reprobe requires --apply-path and --i-understand-icnss-reprobe"
    elif args.apply_path and pre_existing_vendor_mount:
        decision = "manual-review-required"
        reason = f"{VENDOR_MOUNTPOINT} was already mounted before v213 probe"
    elif args.apply_path and (not expected_major_minor or not ext4_available):
        decision = "manual-review-required"
        reason = "sda29/ext4 prerequisites were not confirmed"
    elif args.apply_path and (not mount_ok or not mounted_after_mount):
        decision = "manual-review-required"
        reason = "temporary vendor ro,noload mount failed"
    elif args.apply_path and missing_likely:
        decision = "manual-review-required"
        reason = "candidate firmware root does not resolve all likely request names"
    elif args.apply_path and not helper_available:
        decision = "manual-review-required"
        reason = "a90_fwpathctl helper is missing or could not read firmware_class.path"
    elif args.apply_path and not apply_ok:
        decision = "manual-review-required"
        reason = "firmware_class.path did not read back as /mnt/vendor/firmware"
    elif args.reprobe and not reprobe_helper_available:
        decision = "reprobe-helper-unavailable"
        reason = "a90_icnssctl helper is missing or could not read ICNSS status"
    elif args.reprobe and reprobe_attempted and not rebind_ok:
        decision = "icnss-rebind-failed"
        reason = "ICNSS bind/rebind evidence did not return to bound state"
    elif args.apply_path and not rollback_ok:
        decision = "path-rollback-failed"
        reason = "firmware_class.path did not restore to original value"
    elif leftover_vendor_mount or leftover_probe_mount:
        decision = "cleanup-failed"
        reason = "temporary vendor/probe mount remained after cleanup"
    elif args.reprobe and request_evidence:
        decision = "request-evidence-captured"
        reason = "ICNSS reprobe produced dmesg or net/rfkill/wiphy delta evidence"
    elif args.reprobe:
        decision = "request-evidence-missing"
        reason = "ICNSS reprobe completed but did not expose firmware request or WLAN state evidence"
    elif args.apply_path:
        decision = "path-only-pass"
        reason = "firmware path apply/readback/rollback passed without ICNSS reprobe"
    else:
        decision = "baseline-only"
        reason = "read-only ICNSS firmware request baseline collected"

    return {
        "decision": decision,
        "reason": reason,
        "apply_path": bool(args.apply_path),
        "reprobe": bool(args.reprobe),
        "basic_control_ok": basic_control_ok,
        "v209_decision": v209_decision,
        "v210_decision": v210_decision,
        "v211_decision": v211_decision,
        "v212_decision": v212_decision,
        "original_firmware_class_path": original_path,
        "applied_firmware_class_path": applied_path,
        "rolled_back_firmware_class_path": rolled_back_path,
        "post_firmware_class_path": post_path,
        "pre_existing_vendor_mount": pre_existing_vendor_mount,
        "leftover_vendor_mount": leftover_vendor_mount,
        "leftover_probe_mount": leftover_probe_mount,
        "ext4_available": ext4_available,
        "sda29_dev": sda29_dev,
        "expected_major_minor": expected_major_minor,
        "mount_ok": mount_ok,
        "mounted_after_mount": mounted_after_mount,
        "missing_likely_requests": missing_likely,
        "request_matrix": request_matrix(captures),
        "fwpath_helper_available": helper_available,
        "icnss_helper_available": reprobe_helper_available,
        "icnss_bound": icnss_bound_after if args.reprobe else icnss_bound_before,
        "icnss_bound_before": icnss_bound_before,
        "icnss_bound_after_reprobe": icnss_bound_after,
        "reprobe_attempted": reprobe_attempted,
        "request_evidence": request_evidence,
        "dmesg_before_matches": len(dmesg_before),
        "dmesg_after_matches": len(dmesg_after),
        "dmesg_delta": dmesg_delta[:80],
        "post_wifiish": post_wifiish,
        "probe": asdict(probe),
        "recommended_next": recommended_next(decision),
        "evidence_lines": relevant_lines(captures, probe),
    }


def recommended_next(decision: str) -> str:
    if decision == "baseline-only":
        return "run --apply-path path-only validation before considering ICNSS reprobe"
    if decision == "path-only-pass":
        return "decide whether to deploy a90_icnssctl and run opt-in ICNSS reprobe"
    if decision == "request-evidence-captured":
        return "plan v214 controlled CNSS/ICNSS service preflight; still no scan/connect"
    if decision == "request-evidence-missing":
        return "improve observability before service bring-up"
    if decision == "reprobe-helper-unavailable":
        return "build/deploy /cache/bin/a90_icnssctl before reprobe"
    if decision == "icnss-rebind-failed":
        return "manual review ICNSS state before further Wi-Fi work"
    if decision == "path-rollback-failed":
        return "restore firmware_class.path manually before further Wi-Fi work"
    if decision == "cleanup-failed":
        return "unmount leftover vendor/probe mount before further Wi-Fi work"
    return "manual review before any firmware path mutation or Wi-Fi work"


def build_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    rows = [
        ["result", "PASS" if manifest["pass"] else "FAIL", c["reason"]],
        ["decision", c["decision"], c["recommended_next"]],
        ["apply_path", str(c["apply_path"]), ""],
        ["reprobe", str(c["reprobe"]), ""],
        ["v209", str(c["v209_decision"]), ""],
        ["v210", str(c["v210_decision"]), ""],
        ["v211", str(c["v211_decision"]), ""],
        ["v212", str(c["v212_decision"]), ""],
        ["sda29", str(c["sda29_dev"]), f"usable={c['expected_major_minor']} ext4={c['ext4_available']}"],
        ["mount", str(c["mount_ok"]), f"mounted={c['mounted_after_mount']}"],
        ["fwpath helper", str(c["fwpath_helper_available"]), FWPATH_HELPER],
        ["icnss helper", str(c["icnss_helper_available"]), ICNSS_HELPER],
        ["icnss bound", str(c["icnss_bound"]), ""],
        ["request evidence", str(c["request_evidence"]), f"dmesg_delta={len(c['dmesg_delta'])} post_wifiish={c['post_wifiish']}"],
        ["original path", c["original_firmware_class_path"] or "<empty>", ""],
        ["applied path", c["applied_firmware_class_path"] or "<not-run>", ""],
        ["rolled back path", c["rolled_back_firmware_class_path"] or "<not-run>", ""],
        ["post path", c["post_firmware_class_path"] or "<not-run>", ""],
        ["cleanup", str(not c["leftover_vendor_mount"] and not c["leftover_probe_mount"]), ""],
    ]
    request_rows = [[row["request"], row["path"], str(row["visible"])] for row in c["request_matrix"]]
    lines = [
        "# v213 Firmware Request Evidence Probe\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{c['decision']}`\n",
        f"- reason: `{c['reason']}`\n",
        f"- recommended next: `{c['recommended_next']}`\n\n",
        "## Summary Matrix\n\n",
        markdown_table(["area", "status", "detail"], rows),
        "\n\n## Request Path Matrix\n\n",
        markdown_table(["request", "path", "visible"], request_rows),
        "\n\n## Dmesg Delta\n\n",
    ]
    if c["dmesg_delta"]:
        lines.extend(f"- `{line}`\n" for line in c["dmesg_delta"])
    else:
        lines.append("- none\n")
    lines.append("\n## Evidence Lines\n\n")
    if c["evidence_lines"]:
        lines.extend(f"- `{line}`\n" for line in c["evidence_lines"])
    else:
        lines.append("- none\n")
    lines.append("\n## Captures\n\n")
    for item in manifest["captures"]:
        lines.append(f"- {'OK' if item['ok'] else 'FAIL'} `{item['name']}` rc={item['rc']} file=`{item['file']}`\n")
    lines.append("\n## Guardrails\n\n")
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def main() -> int:
    args = parse_args()
    if args.reprobe and not (args.apply_path and args.i_understand_icnss_reprobe):
        raise SystemExit("--reprobe requires --apply-path and --i-understand-icnss-reprobe")
    validate_command_guard()
    run_id = make_run_id(args.run_id)
    probe = make_probe_paths(run_id)
    store = EvidenceStore(args.out_dir)
    store.mkdir("native", "commands")
    captures: list[CaptureRecord] = []
    v209 = load_json(args.v209_manifest)
    v210 = load_json(args.v210_manifest)
    v211 = load_json(args.v211_manifest)
    v212 = load_json(args.v212_manifest)

    run_sequence(store, args, probe, baseline_commands(), captures)
    snapshot = classify(captures, probe, args, v209, v210, v211, v212)
    probe = probe_from_sda29_dev(run_id, snapshot["sda29_dev"])
    snapshot = classify(captures, probe, args, v209, v210, v211, v212)
    should_apply = (
        args.apply_path
        and snapshot["basic_control_ok"]
        and not snapshot["pre_existing_vendor_mount"]
        and (args.allow_non_v209_decision or snapshot["v209_decision"] == V209_EXPECTED_DECISION)
        and (args.allow_non_v210_decision or snapshot["v210_decision"] == V210_EXPECTED_DECISION)
        and (args.allow_non_v211_decision or snapshot["v211_decision"] == V211_EXPECTED_DECISION)
        and (args.allow_non_v212_decision or snapshot["v212_decision"] == V212_EXPECTED_DECISION)
    )
    original_path = snapshot["original_firmware_class_path"]

    if should_apply:
        try:
            run_sequence(store, args, probe, preflight_commands(probe), captures, original_path=original_path)
            mounted_snapshot = classify(captures, probe, args, v209, v210, v211, v212)
            if mounted_snapshot["mount_ok"] and mounted_snapshot["mounted_after_mount"]:
                run_sequence(store, args, probe, asset_commands(), captures, original_path=original_path)
                asset_snapshot = classify(captures, probe, args, v209, v210, v211, v212)
                if not asset_snapshot["missing_likely_requests"]:
                    for name, command, timeout in path_apply_commands(original_path):
                        captures.append(capture_device(store, args, probe, name, command, timeout, original_path=original_path))
                        if name in {"fwpath-helper-stat", "fwpath-helper-read-before"} and not capture_ok(captures, name):
                            break
                        if name == "apply-firmware-class-path" and not capture_ok(captures, "apply-firmware-class-path"):
                            break
                        if name == "firmware-class-path-applied" and first_line_value(captures, "firmware-class-path-applied") != FIRMWARE_ROOT:
                            break
                        if name == "post-apply-dmesg" and args.reprobe:
                            for reprobe_name, reprobe_command, reprobe_timeout in reprobe_commands():
                                captures.append(capture_device(store, args, probe, reprobe_name, reprobe_command, reprobe_timeout, original_path=original_path))
                                if reprobe_name in {"icnss-helper-stat", "icnss-helper-status-before"} and not capture_ok(captures, reprobe_name):
                                    break
                                if reprobe_name == "icnss-bind" and not capture_ok(captures, "icnss-bind"):
                                    break
        finally:
            if (
                capture_by_name(captures, "apply-firmware-class-path") is not None
                and capture_by_name(captures, "rollback-firmware-class-path") is None
                and original_path
            ):
                captures.append(capture_device(store, args, probe, "rollback-firmware-class-path", firmware_write_command(original_path), 20.0, original_path=original_path))
                captures.append(capture_device(store, args, probe, "firmware-class-path-rolled-back", ["cat", FIRMWARE_CLASS_PATH], 20.0, original_path=original_path))
            run_sequence(store, args, probe, cleanup_commands(probe), captures, original_path=original_path)
    else:
        run_sequence(store, args, probe, cleanup_commands(probe)[1:], captures, original_path=original_path)

    classification = classify(captures, probe, args, v209, v210, v211, v212)
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": classification["decision"] in DECISIONS and classification["decision"] not in {
            "manual-review-required",
            "reprobe-helper-unavailable",
            "icnss-rebind-failed",
            "path-rollback-failed",
            "cleanup-failed",
        },
        "decision": classification["decision"],
        "reason": classification["reason"],
        "mode": "native-firmware-request-evidence-probe",
        "classification": classification,
        "captures": [asdict(item) for item in captures],
        "v209_native": {"path": str(args.v209_manifest), "present": v209 is not None, "decision": manifest_decision(v209)},
        "v210_native": {"path": str(args.v210_manifest), "present": v210 is not None, "decision": manifest_decision(v210)},
        "v211_native": {"path": str(args.v211_manifest), "present": v211 is not None, "decision": manifest_decision(v211)},
        "v212_native": {"path": str(args.v212_manifest), "present": v212 is not None, "decision": manifest_decision(v212)},
        "guardrails": [
            "default mode is read-only",
            "firmware_class.path write requires --apply-path",
            "ICNSS reprobe requires --reprobe and --i-understand-icnss-reprobe",
            "plain echo and shell redirection forbidden",
            "a90_fwpathctl fixed-target firmware path writes only",
            "a90_icnssctl fixed-target ICNSS bind/unbind only",
            "mount requires ext4 ro,noload",
            "temporary block node only under /tmp/a90-v213-*",
            "vendor mountpoint limited to /mnt/vendor",
            "no bind mount",
            "no Wi-Fi enablement",
            "no rfkill write",
            "no WLAN link-up",
            "no scan/connect",
            "no module load/unload",
            "no cnss-daemon/cnss_diag/wificond/HAL/supplicant/hostapd start",
            "no firmware file copy",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(
        f"{'PASS' if manifest['pass'] else 'FAIL'} "
        f"out_dir={store.run_dir} "
        f"decision={classification['decision']} "
        f"reason={classification['reason']}"
    )
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
