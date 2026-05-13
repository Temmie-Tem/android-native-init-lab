#!/usr/bin/env python3
"""Apply and roll back A90 native firmware_class.path under strict guardrails."""

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


PROBE_PREFIX = "/tmp/a90-v212-"
EXPECTED_BLOCK = "sda29"
EXPECTED_MAJOR = "259"
EXPECTED_MINOR = "22"
VENDOR_MOUNTPOINT = "/mnt/vendor"
FIRMWARE_ROOT = "/mnt/vendor/firmware"
FIRMWARE_CLASS_PATH = "/sys/module/firmware_class/parameters/path"
V209_EXPECTED_DECISION = "vendor-assets-visible"
V210_EXPECTED_DECISION = "firmware-path-policy-needed"
V211_EXPECTED_DECISION = "sysfs-path-update-needed"
DEFAULT_V209_MANIFEST = Path("tmp/wifi/v209-vendor-ro-mount-probe/manifest.json")
DEFAULT_V210_MANIFEST = Path("tmp/wifi/v210-vendor-asset-classifier/manifest.json")
DEFAULT_V211_MANIFEST = Path("tmp/wifi/v211-firmware-path-policy/manifest.json")

DECISIONS = {
    "path-rollback-pass",
    "apply-required",
    "write-helper-unavailable",
    "path-readback-mismatch",
    "rollback-failed",
    "cleanup-failed",
    "request-name-unknown",
    "manual-review-required",
}

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 25.0),
    ("bootstatus", ["bootstatus"], 25.0),
    ("pre-proc-mounts", ["cat", "/proc/mounts"], 20.0),
    ("proc-filesystems", ["cat", "/proc/filesystems"], 20.0),
    ("firmware-class-path-before", ["cat", FIRMWARE_CLASS_PATH], 20.0),
    ("sys-sda29-dev", ["cat", "/sys/class/block/sda29/dev"], 20.0),
    ("sys-sda29-size", ["cat", "/sys/class/block/sda29/size"], 20.0),
    ("sys-sda29-ro", ["cat", "/sys/class/block/sda29/ro"], 20.0),
    ("sys-dev-block-sda29", ["ls", "/sys/dev/block/259:22"], 20.0),
    ("mnt-root-before", ["ls", "/mnt"], 20.0),
    ("tmp-root-before", ["ls", "/tmp"], 20.0),
)

LIKELY_REQUEST_NAMES = (
    "wlan/qca_cld/WCNSS_qcom_cfg.ini",
    "wlan/qca_cld/bdwlan.bin",
    "wlan/qca_cld/regdb.bin",
    "wlanmdsp.mbn",
)

UNCERTAIN_REQUEST_NAMES = (
    "WCNSS_qcom_cfg.ini",
    "bdwlan.bin",
    "regdb.bin",
)

REQUIRED_FIRMWARE_PATHS = tuple(f"{FIRMWARE_ROOT}/{name}" for name in LIKELY_REQUEST_NAMES)
UNCERTAIN_FIRMWARE_PATHS = tuple(f"{FIRMWARE_ROOT}/{name}" for name in UNCERTAIN_REQUEST_NAMES)

ACTIVE_WIFI_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\b", re.IGNORECASE),
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
    preflight_file: str


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v212-firmware-path-rollback"


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
    parser.add_argument("--run-id", default="", help="optional safe suffix for /tmp/a90-v212-<run-id>")
    parser.add_argument("--allow-non-v209-decision", action="store_true")
    parser.add_argument("--allow-non-v210-decision", action="store_true")
    parser.add_argument("--allow-non-v211-decision", action="store_true")
    parser.add_argument("--apply", action="store_true", help="actually write and roll back firmware_class.path")
    parser.add_argument("--native-bridge", action="store_true", help="document intent; native bridge is the current mode")
    return parser.parse_args()


def make_run_id(value: str = "") -> str:
    run_id = value or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.+-]{1,64}", run_id):
        raise RuntimeError(f"unsafe run id: {run_id!r}")
    return run_id


def make_probe_paths(run_id: str) -> ProbePaths:
    base = f"{PROBE_PREFIX}{run_id}"
    return ProbePaths(
        run_id=run_id,
        base=base,
        node=f"{base}/{EXPECTED_BLOCK}",
        preflight_file=f"{base}/fwpath-preflight",
    )


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def shell_quote_path(value: str) -> str:
    if value == "":
        return "''"
    if not SAFE_PATH_RE.fullmatch(value):
        raise RuntimeError(f"unsafe firmware path value: {value!r}")
    return "'" + value + "'"


def write_command(value: str, target: str) -> list[str]:
    if target != FIRMWARE_CLASS_PATH and not target.startswith(PROBE_PREFIX):
        raise RuntimeError(f"unsafe write target: {target!r}")
    quoted_value = shell_quote_path(value)
    quoted_target = shell_quote_path(target)
    return ["run", "/cache/bin/toybox", "sh", "-c", f"printf %s {quoted_value} > {quoted_target}"]


def command_text(command: list[str]) -> str:
    return " ".join(command)


def is_under_probe_path(path: str, probe: ProbePaths) -> bool:
    return path == probe.base or path.startswith(probe.base + "/")


def is_under_vendor_path(path: str) -> bool:
    return path == VENDOR_MOUNTPOINT or path.startswith(VENDOR_MOUNTPOINT + "/")


def allowed_global_read_path(path: str, probe: ProbePaths) -> bool:
    return (
        path in {"/proc/mounts", "/proc/filesystems", FIRMWARE_CLASS_PATH, "/tmp", "/mnt", VENDOR_MOUNTPOINT}
        or path.startswith("/sys/class/block/sda29/")
        or path == "/sys/dev/block/259:22"
        or is_under_probe_path(path, probe)
        or is_under_vendor_path(path)
    )


def is_exact_write_command(command: list[str], value: str, target: str) -> bool:
    try:
        return command == write_command(value, target)
    except RuntimeError:
        return False


def validate_apply_command(
    command: list[str],
    probe: ProbePaths,
    *,
    apply_enabled: bool = False,
    original_path: str | None = None,
) -> None:
    if not command:
        raise RuntimeError("empty apply command")
    joined = command_text(command)

    if is_exact_write_command(command, FIRMWARE_ROOT, probe.preflight_file):
        return
    if apply_enabled and is_exact_write_command(command, FIRMWARE_ROOT, FIRMWARE_CLASS_PATH):
        return
    if apply_enabled and original_path is not None and is_exact_write_command(command, original_path, FIRMWARE_CLASS_PATH):
        return
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
        if allowed_global_read_path(command[1], probe):
            return
        raise RuntimeError(f"{name} outside allowed read paths: {joined}")
    if name == "mkdir":
        if len(command) == 2 and (command[1] == VENDOR_MOUNTPOINT or is_under_probe_path(command[1], probe)):
            return
        raise RuntimeError(f"mkdir outside allowed path: {joined}")
    if name == "mknodb":
        if command == ["mknodb", probe.node, EXPECTED_MAJOR, EXPECTED_MINOR]:
            return
        raise RuntimeError(f"unexpected mknodb command: {joined}")
    if name == "umount":
        if command == ["umount", VENDOR_MOUNTPOINT]:
            return
        raise RuntimeError(f"unexpected umount command: {joined}")
    if name == "run":
        expected_mount = [
            "run",
            "/cache/bin/toybox",
            "mount",
            "-t",
            "ext4",
            "-o",
            "ro,noload",
            probe.node,
            VENDOR_MOUNTPOINT,
        ]
        if command == expected_mount:
            return
        if len(command) >= 3 and command[1] == "/cache/bin/toybox" and command[2] == "mount":
            raise RuntimeError(f"mount command must be exact ro,noload probe mount: {joined}")
        raise RuntimeError(f"unexpected run command: {joined}")
    raise RuntimeError(f"unexpected command: {joined}")


def build_preflight_commands(probe: ProbePaths) -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("mkdir-probe-base", ["mkdir", probe.base], 20.0),
        ("mkdir-vendor-mountpoint", ["mkdir", VENDOR_MOUNTPOINT], 20.0),
        ("mknodb-sda29", ["mknodb", probe.node, EXPECTED_MAJOR, EXPECTED_MINOR], 20.0),
        ("temp-node-stat", ["stat", probe.node], 20.0),
        ("safe-ro-noload-mount", ["run", "/cache/bin/toybox", "mount", "-t", "ext4", "-o", "ro,noload", probe.node, VENDOR_MOUNTPOINT], 45.0),
        ("mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0),
    )


def build_asset_commands() -> tuple[tuple[str, list[str], float], ...]:
    commands: list[tuple[str, list[str], float]] = [
        ("mounted-vendor-root", ["ls", VENDOR_MOUNTPOINT], 20.0),
        ("mounted-firmware-root", ["ls", FIRMWARE_ROOT], 20.0),
        ("mounted-qca-cld", ["ls", f"{FIRMWARE_ROOT}/wlan/qca_cld"], 20.0),
    ]
    for path in REQUIRED_FIRMWARE_PATHS:
        commands.append((f"asset-{safe_name(path)}", ["stat", path], 20.0))
    for path in UNCERTAIN_FIRMWARE_PATHS:
        commands.append((f"uncertain-{safe_name(path)}", ["stat", path], 20.0))
    return tuple(commands)


def build_apply_commands(probe: ProbePaths, original_path: str) -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("write-preflight-temp", write_command(FIRMWARE_ROOT, probe.preflight_file), 20.0),
        ("read-preflight-temp", ["cat", probe.preflight_file], 20.0),
        ("apply-firmware-class-path", write_command(FIRMWARE_ROOT, FIRMWARE_CLASS_PATH), 20.0),
        ("firmware-class-path-applied", ["cat", FIRMWARE_CLASS_PATH], 20.0),
        ("rollback-firmware-class-path", write_command(original_path, FIRMWARE_CLASS_PATH), 20.0),
        ("firmware-class-path-rolled-back", ["cat", FIRMWARE_CLASS_PATH], 20.0),
    )


def build_cleanup_commands(probe: ProbePaths) -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("cleanup-umount", ["umount", VENDOR_MOUNTPOINT], 25.0),
        ("post-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        ("post-firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 20.0),
        ("tmp-base-after", ["ls", probe.base], 20.0),
    )


def validate_apply_commands() -> None:
    probe = make_probe_paths("guard")
    original = "/vendor/firmware_mnt/image"
    for _, command, _ in READ_ONLY_COMMANDS + build_preflight_commands(probe) + build_asset_commands() + build_cleanup_commands(probe):
        validate_apply_command(command, probe)
    for _, command, _ in build_apply_commands(probe, original):
        validate_apply_command(command, probe, apply_enabled=True, original_path=original)
    try:
        validate_apply_command(write_command(FIRMWARE_ROOT, FIRMWARE_CLASS_PATH), probe, apply_enabled=False)
    except RuntimeError:
        pass
    else:
        raise RuntimeError("guard allowed sysfs write without apply_enabled")


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
    validate_apply_command(command, probe, apply_enabled=args.apply, original_path=original_path)
    capture = run_capture(args, name, command, timeout=timeout)
    body = capture.text if capture.text else f"{capture.error}\n"
    relative = write_capture(store, name, body)
    data = capture_to_manifest(capture)
    full_text = redact_text(body if capture.text else "")
    return CaptureRecord(
        name=name,
        command=command_text(command),
        ok=bool(data["ok"]),
        rc=data.get("rc"),
        status=str(data.get("status", "missing")),
        duration_sec=float(data["duration_sec"]),
        file=relative,
        text=full_text,
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


def parse_major_minor(text: str) -> tuple[str, str] | None:
    match = re.search(r"\b(\d+):(\d+)\b", text)
    if not match:
        return None
    return match.group(1), match.group(2)


def mountpoint_in_text(text: str, mountpoint: str) -> bool:
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == mountpoint:
            return True
    return False


def probe_mount_in_text(text: str, probe: ProbePaths) -> bool:
    for line in text.splitlines():
        if probe.base in line:
            return True
    return False


def path_visible(captures: list[CaptureRecord], path: str, prefix: str = "asset") -> bool:
    capture = capture_by_name(captures, f"{prefix}-{safe_name(path)}")
    return capture is not None and capture.ok


def request_matrix(captures: list[CaptureRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for request, path in zip(LIKELY_REQUEST_NAMES, REQUIRED_FIRMWARE_PATHS, strict=True):
        rows.append({"request": request, "path": path, "kind": "likely", "visible": path_visible(captures, path)})
    for request, path in zip(UNCERTAIN_REQUEST_NAMES, UNCERTAIN_FIRMWARE_PATHS, strict=True):
        rows.append({"request": request, "path": path, "kind": "uncertain", "visible": path_visible(captures, path, prefix="uncertain")})
    return rows


def relevant_lines(captures: list[CaptureRecord], probe: ProbePaths, limit: int = 160) -> list[str]:
    keywords = (
        "firmware_class",
        "firmware_mnt",
        "/mnt/vendor",
        "bdwlan",
        "regdb",
        "wlanmdsp",
        "WCNSS",
        "sda29",
        probe.base,
        "ro,noload",
    )
    lines: list[str] = []
    for capture in captures:
        text = strip_cmdv1_text(capture.text)
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if any(token.lower() in line.lower() for token in keywords) and line not in lines:
                lines.append(line)
            if len(lines) >= limit:
                return lines
    return lines


def classify(
    captures: list[CaptureRecord],
    probe: ProbePaths,
    v209: dict[str, Any] | None,
    v210: dict[str, Any] | None,
    v211: dict[str, Any] | None,
    args: argparse.Namespace,
) -> dict[str, Any]:
    v209_decision = manifest_decision(v209)
    v210_decision = manifest_decision(v210)
    v211_decision = manifest_decision(v211)
    basic_control_ok = capture_ok(captures, "version", "status")
    pre_mount_text = capture_text(captures, "pre-proc-mounts")
    pre_existing_vendor_mount = mountpoint_in_text(pre_mount_text, VENDOR_MOUNTPOINT)
    sys_dev_text = capture_text(captures, "sys-sda29-dev")
    major_minor = parse_major_minor(sys_dev_text)
    expected_major_minor = major_minor == (EXPECTED_MAJOR, EXPECTED_MINOR)
    ext4_available = "ext4" in capture_text(captures, "proc-filesystems").split()
    original_path = first_line_value(captures, "firmware-class-path-before")
    mounted_text = capture_text(captures, "mounted-proc-mounts")
    mount_capture = capture_by_name(captures, "safe-ro-noload-mount")
    mount_attempted = mount_capture is not None
    mount_ok = mount_capture.ok if mount_capture is not None else False
    mounted_after_mount = mountpoint_in_text(mounted_text, VENDOR_MOUNTPOINT)
    cleanup_capture = capture_by_name(captures, "cleanup-umount")
    cleanup_attempted = cleanup_capture is not None
    cleanup_rc = cleanup_capture.rc if cleanup_capture is not None else None
    post_mounts = capture_text(captures, "post-proc-mounts")
    leftover_vendor_mount = mountpoint_in_text(post_mounts, VENDOR_MOUNTPOINT)
    leftover_probe_mount = probe_mount_in_text(post_mounts, probe)
    applied_path = first_line_value(captures, "firmware-class-path-applied")
    rolled_back_path = first_line_value(captures, "firmware-class-path-rolled-back")
    post_path = first_line_value(captures, "post-firmware-class-path")
    preflight_value = first_line_value(captures, "read-preflight-temp")
    likely_rows = [row for row in request_matrix(captures) if row["kind"] == "likely"]
    uncertain_rows = [row for row in request_matrix(captures) if row["kind"] == "uncertain"]
    missing_likely = [row["request"] for row in likely_rows if not row["visible"]]
    missing_uncertain = [row["request"] for row in uncertain_rows if not row["visible"]]
    write_preflight_ok = capture_ok(captures, "write-preflight-temp", "read-preflight-temp") and preflight_value == FIRMWARE_ROOT
    apply_attempted = capture_by_name(captures, "apply-firmware-class-path") is not None
    apply_ok = capture_ok(captures, "apply-firmware-class-path") and applied_path == FIRMWARE_ROOT
    rollback_attempted = capture_by_name(captures, "rollback-firmware-class-path") is not None
    rollback_ok = capture_ok(captures, "rollback-firmware-class-path") and rolled_back_path == original_path
    post_rollback_ok = not post_path or post_path == original_path

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
    elif pre_existing_vendor_mount:
        decision = "manual-review-required"
        reason = f"{VENDOR_MOUNTPOINT} was already mounted before v212 probe"
    elif not original_path and args.apply:
        decision = "manual-review-required"
        reason = "original firmware_class.path is empty; apply rollback policy needs manual review"
    elif original_path and not SAFE_PATH_RE.fullmatch(original_path):
        decision = "manual-review-required"
        reason = "original firmware_class.path contains characters outside the guarded write allowlist"
    elif not expected_major_minor:
        decision = "manual-review-required"
        reason = "sda29 major/minor could not be confirmed as 259:22"
    elif not ext4_available:
        decision = "manual-review-required"
        reason = "ext4 is not listed in /proc/filesystems"
    elif mount_attempted and not mount_ok:
        decision = "manual-review-required"
        reason = "temporary vendor ro,noload mount failed"
    elif mount_attempted and not mounted_after_mount:
        decision = "manual-review-required"
        reason = "temporary vendor ro,noload mount did not appear in /proc/mounts"
    elif missing_likely:
        decision = "request-name-unknown"
        reason = "candidate firmware root does not resolve all likely request names"
    elif leftover_vendor_mount or leftover_probe_mount:
        decision = "cleanup-failed"
        reason = "temporary vendor mount remained after cleanup"
    elif args.apply and not write_preflight_ok:
        decision = "write-helper-unavailable"
        reason = "toybox sh printf no-newline preflight did not round-trip under /tmp"
    elif args.apply and not apply_attempted:
        decision = "manual-review-required"
        reason = "apply mode requested but apply command was not attempted"
    elif args.apply and not apply_ok:
        decision = "path-readback-mismatch"
        reason = "firmware_class.path readback did not match /mnt/vendor/firmware after apply"
    elif args.apply and (not rollback_attempted or not rollback_ok or not post_rollback_ok):
        decision = "rollback-failed"
        reason = "firmware_class.path did not restore to the original value"
    elif args.apply:
        decision = "path-rollback-pass"
        reason = "firmware_class.path apply, readback, request resolution, rollback, and cleanup passed"
    else:
        decision = "apply-required"
        reason = "dry-run mount and request resolution passed; rerun with --apply to test sysfs write rollback"

    return {
        "decision": decision,
        "reason": reason,
        "apply_mode": bool(args.apply),
        "basic_control_ok": basic_control_ok,
        "v209_decision": v209_decision,
        "v210_decision": v210_decision,
        "v211_decision": v211_decision,
        "pre_existing_vendor_mount": pre_existing_vendor_mount,
        "major_minor": ":".join(major_minor) if major_minor else None,
        "expected_major_minor": expected_major_minor,
        "ext4_available": ext4_available,
        "original_firmware_class_path": original_path,
        "applied_firmware_class_path": applied_path,
        "rolled_back_firmware_class_path": rolled_back_path,
        "post_firmware_class_path": post_path,
        "preflight_value": preflight_value,
        "write_preflight_ok": write_preflight_ok,
        "mount_attempted": mount_attempted,
        "mount_ok": mount_ok,
        "mounted_after_mount": mounted_after_mount,
        "cleanup_attempted": cleanup_attempted,
        "cleanup_rc": cleanup_rc,
        "leftover_vendor_mount": leftover_vendor_mount,
        "leftover_probe_mount": leftover_probe_mount,
        "missing_likely_requests": missing_likely,
        "missing_uncertain_requests": missing_uncertain,
        "request_matrix": request_matrix(captures),
        "probe": asdict(probe),
        "recommended_next": recommended_next(decision),
        "evidence_lines": relevant_lines(captures, probe),
    }


def recommended_next(decision: str) -> str:
    if decision == "apply-required":
        return "operator can run v212 again with --apply when ready for reversible sysfs write"
    if decision == "path-rollback-pass":
        return "plan v213 firmware request evidence or controlled ICNSS/CNSS preflight; do not jump to Wi-Fi connect"
    if decision == "write-helper-unavailable":
        return "build a tiny static a90_fwpathctl helper instead of shell-based sysfs writes"
    if decision == "rollback-failed":
        return "restore firmware_class.path manually before any further Wi-Fi work"
    if decision == "cleanup-failed":
        return "unmount leftover vendor/probe mount before any further Wi-Fi work"
    return "manual review before firmware path mutation or Wi-Fi work"


def build_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    rows = [
        ["result", "PASS" if manifest["pass"] else "FAIL", c["reason"]],
        ["decision", c["decision"], c["recommended_next"]],
        ["apply_mode", str(c["apply_mode"]), ""],
        ["v209", str(c["v209_decision"]), ""],
        ["v210", str(c["v210_decision"]), ""],
        ["v211", str(c["v211_decision"]), ""],
        ["major_minor", str(c["major_minor"]), f"expected={c['expected_major_minor']}"],
        ["ext4", str(c["ext4_available"]), ""],
        ["mount", str(c["mount_ok"]), f"attempted={c['mount_attempted']} mounted={c['mounted_after_mount']}"],
        ["cleanup", str(not c["leftover_vendor_mount"] and not c["leftover_probe_mount"]), f"attempted={c['cleanup_attempted']} rc={c['cleanup_rc']}"],
        ["original path", c["original_firmware_class_path"] or "<empty>", ""],
        ["applied path", c["applied_firmware_class_path"] or "<not-run>", ""],
        ["rolled back path", c["rolled_back_firmware_class_path"] or "<not-run>", ""],
        ["post path", c["post_firmware_class_path"] or "<not-run>", ""],
        ["missing likely", str(len(c["missing_likely_requests"])), ", ".join(c["missing_likely_requests"])],
    ]
    request_rows = [
        [row["request"], row["kind"], row["path"], str(row["visible"])]
        for row in c["request_matrix"]
    ]
    lines = [
        "# v212 Firmware Path Apply / Rollback Probe\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{c['decision']}`\n",
        f"- reason: `{c['reason']}`\n",
        f"- recommended next: `{c['recommended_next']}`\n\n",
        "## Summary Matrix\n\n",
        markdown_table(["area", "status", "detail"], rows),
        "\n\n## Request Resolution\n\n",
        markdown_table(["request", "kind", "path", "visible"], request_rows),
        "\n\n## Evidence Lines\n\n",
    ]
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
    validate_apply_commands()
    run_id = make_run_id(args.run_id)
    probe = make_probe_paths(run_id)
    store = EvidenceStore(args.out_dir)
    store.mkdir("native", "commands")
    captures: list[CaptureRecord] = []
    v209 = load_json(args.v209_manifest)
    v210 = load_json(args.v210_manifest)
    v211 = load_json(args.v211_manifest)

    run_sequence(store, args, probe, READ_ONLY_COMMANDS, captures)
    snapshot = classify(captures, probe, v209, v210, v211, args)
    should_mount = (
        snapshot["basic_control_ok"]
        and not snapshot["pre_existing_vendor_mount"]
        and (args.allow_non_v209_decision or snapshot["v209_decision"] == V209_EXPECTED_DECISION)
        and (args.allow_non_v210_decision or snapshot["v210_decision"] == V210_EXPECTED_DECISION)
        and (args.allow_non_v211_decision or snapshot["v211_decision"] == V211_EXPECTED_DECISION)
        and snapshot["expected_major_minor"]
        and snapshot["ext4_available"]
    )
    original_path = snapshot["original_firmware_class_path"]

    if should_mount:
        run_sequence(store, args, probe, build_preflight_commands(probe), captures, original_path=original_path)
        mounted_snapshot = classify(captures, probe, v209, v210, v211, args)
        if mounted_snapshot["mount_ok"] and mounted_snapshot["mounted_after_mount"]:
            run_sequence(store, args, probe, build_asset_commands(), captures, original_path=original_path)
            asset_snapshot = classify(captures, probe, v209, v210, v211, args)
            if args.apply and not asset_snapshot["missing_likely_requests"]:
                apply_commands = build_apply_commands(probe, original_path)
                try:
                    for name, command, timeout in apply_commands:
                        captures.append(
                            capture_device(
                                store,
                                args,
                                probe,
                                name,
                                command,
                                timeout,
                                original_path=original_path,
                            )
                        )
                        if name == "apply-firmware-class-path" and not capture_ok(captures, "apply-firmware-class-path"):
                            break
                        if name == "firmware-class-path-applied" and first_line_value(captures, "firmware-class-path-applied") != FIRMWARE_ROOT:
                            break
                finally:
                    if capture_by_name(captures, "rollback-firmware-class-path") is None and original_path:
                        rollback = ("rollback-firmware-class-path", write_command(original_path, FIRMWARE_CLASS_PATH), 20.0)
                        captures.append(
                            capture_device(
                                store,
                                args,
                                probe,
                                rollback[0],
                                rollback[1],
                                rollback[2],
                                original_path=original_path,
                            )
                        )
                        captures.append(
                            capture_device(
                                store,
                                args,
                                probe,
                                "firmware-class-path-rolled-back",
                                ["cat", FIRMWARE_CLASS_PATH],
                                20.0,
                                original_path=original_path,
                            )
                        )
        run_sequence(store, args, probe, build_cleanup_commands(probe), captures, original_path=original_path)
    elif snapshot["basic_control_ok"]:
        run_sequence(store, args, probe, build_cleanup_commands(probe)[1:], captures, original_path=original_path)

    classification = classify(captures, probe, v209, v210, v211, args)
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": classification["decision"] in DECISIONS and classification["decision"] not in {
            "manual-review-required",
            "path-readback-mismatch",
            "rollback-failed",
            "cleanup-failed",
            "request-name-unknown",
            "write-helper-unavailable",
        },
        "decision": classification["decision"],
        "reason": classification["reason"],
        "mode": "native-firmware-path-apply-rollback-probe",
        "classification": classification,
        "captures": [asdict(item) for item in captures],
        "v209_native": {"path": str(args.v209_manifest), "present": v209 is not None, "decision": manifest_decision(v209)},
        "v210_native": {"path": str(args.v210_manifest), "present": v210 is not None, "decision": manifest_decision(v210)},
        "v211_native": {"path": str(args.v211_manifest), "present": v211 is not None, "decision": manifest_decision(v211)},
        "guardrails": [
            "dry-run never writes firmware_class.path",
            "sysfs write requires --apply",
            "plain echo forbidden; only exact printf no-newline write command is allowed",
            "original firmware_class.path is saved and restored",
            "mount requires ext4 ro,noload",
            "temporary block node only under /tmp/a90-v212-*",
            "vendor mountpoint limited to /mnt/vendor",
            "no bind mount",
            "no /vendor or /lib/firmware mutation",
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
