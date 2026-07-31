#!/usr/bin/env python3
"""Exact one-shot cleanup for the retained A90 V3405 D3 work image.

This is a separately reviewed persistent-file cleanup contract.  Its default
mode is host-only inspection.  Live execution requires a final private
manifest, an exclusively prepared approval receipt, and the exact fresh
operator token.  It can unlink only the fixed retained work-image path after
revalidating its type, mode, size, SHA256, host preservation, target, health,
and adjacent-path absence.

The unlink dispatch is never retried.  A lost response permits read-only
reconciliation only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
if str(REVAL_DIR) not in sys.path:
    sys.path.insert(0, str(REVAL_DIR))

import a90ctl  # noqa: E402


SCHEMA = "a90_phase2d_retained_work_cleanup_manifest_v1"
STATUS = "ready-for-cleanup-approval"
APPROVAL_SCHEMA = "a90_phase2d_retained_work_cleanup_approval_v1"
APPROVAL_PREFIX = "A90-V3406-WORK-CLEANUP-APPROVE:"
RESULT_SCHEMA = "a90_phase2d_retained_work_cleanup_result_v1"
PRIVATE_RUN_BASE = (
    REPO_ROOT / "workspace" / "private" / "runs" / "server-distro"
).resolve()
PRIVATE_ROOT = (REPO_ROOT / "workspace" / "private").resolve()
CONNECTED_PREFLIGHT = (
    REPO_ROOT
    / "workspace"
    / "public"
    / "src"
    / "scripts"
    / "server-distro"
    / "a90_phase2d_connected_preflight.py"
)
A90CTL_SOURCE = (REVAL_DIR / "a90ctl.py").resolve()
WORK_PATH = "/mnt/sdext/a90/runtime/d3-handoff-work.img"
WORK_SIZE = 2147483648
WORK_MODE = "0600"
EXPECTED_VERSION = "0.9.285"
EXPECTED_BUILD = "v2321-usb-clean-identity-rodata"
EXPECTED_VENDOR_PRODUCT = "04e8:6861"
READ_TIMEOUT_SEC = 15.0
CLEANUP_TIMEOUT_SEC = 180.0
RUN_ID_RE = re.compile(r"^a90-v3406-work-cleanup-[0-9]{8}-[0-9]{2}$")
F1_RUN_ID_RE = re.compile(
    r"^a90-v3406-debian-display-f1-(?P<suffix>[0-9]{8}-[0-9]{2})$"
)
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(
    r"^version: 0\.9\.285 build=v2321-usb-clean-identity-rodata\r?$",
    re.MULTILINE,
)
SELFTEST_RE = re.compile(
    r"^selftest: pass=(?P<pass>[0-9]+) warn=(?P<warn>[0-9]+) "
    r"fail=0 duration=(?P<duration>[0-9]+)ms(?: entries=[0-9]+)?\r?$",
    re.MULTILINE,
)
PSTORE_ZERO_RE = re.compile(
    r"^pstore=fs=yes mounted=no dir=yes entries=0\b.*$",
    re.MULTILINE,
)


class ContractError(RuntimeError):
    """The exact cleanup contract was not satisfied."""


@dataclass(frozen=True)
class BoundFile:
    path: Path
    size: int
    sha256: str


@dataclass(frozen=True)
class CleanupSpec:
    manifest_path: Path
    manifest_sha256: str
    run_id: str
    f1_run_id: str
    runner: BoundFile
    transport: BoundFile
    connected_d0: BoundFile
    bridge_device: Path
    bridge_realpath_sha256: str
    usb_serial_sha256: str
    host_copy: BoundFile
    work_sha256: str
    source_path: str
    stage_path: str


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def json_sha256(value: Any) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_all(descriptor: int, body: bytes) -> None:
    offset = 0
    while offset < len(body):
        written = os.write(descriptor, body[offset:])
        if written <= 0:
            raise ContractError("short private JSON write")
        offset += written


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_private_json_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        _write_all(descriptor, _json_bytes(value))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path, follow_symlinks=False)
        _fsync_directory(path.parent)
    except FileExistsError as exc:
        raise ContractError(f"private evidence already exists: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise ContractError(f"{label} must be lowercase SHA256")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a non-empty string")
    return value


def validate_timeout(value: float, label: str, expected: float) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or float(value) != expected
    ):
        raise ContractError(
            f"{label} must be the exact finite value {expected:.0f} seconds"
        )
    return float(value)


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def require_private_regular(
    path: Path,
    *,
    exact_mode: int = 0o600,
) -> os.stat_result:
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(PRIVATE_ROOT):
        raise ContractError(f"private input is outside workspace/private: {path}")
    item = path.lstat()
    if not stat.S_ISREG(item.st_mode) or item.st_nlink != 1:
        raise ContractError(f"private input is not a single-link regular file: {path}")
    if stat.S_IMODE(item.st_mode) != exact_mode:
        raise ContractError(
            f"private input mode is not {exact_mode:04o}: {path}"
        )
    return item


def hash_open_regular(path: Path) -> tuple[str, os.stat_result]:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ContractError(f"bound file is not a single-link regular file: {path}")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    digest = hashlib.sha256()
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != before.st_dev
            or opened.st_ino != before.st_ino
            or opened.st_size != before.st_size
        ):
            raise ContractError(f"bound file changed during open: {path}")
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after_fd = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_path = path.lstat()
    identity = (opened.st_dev, opened.st_ino, opened.st_size)
    if (
        identity != (after_fd.st_dev, after_fd.st_ino, after_fd.st_size)
        or identity != (after_path.st_dev, after_path.st_ino, after_path.st_size)
    ):
        raise ContractError(f"bound file changed during hash: {path}")
    return digest.hexdigest(), after_fd


def load_bound(value: Any, label: str) -> BoundFile:
    item = require_dict(value, label)
    path = Path(require_string(item.get("path"), f"{label}.path"))
    if not path.is_absolute():
        path = (Path.cwd() / path).absolute()
    size = item.get("size")
    if type(size) is not int or size <= 0:
        raise ContractError(f"{label}.size must be a positive integer")
    expected = validate_sha256(item.get("sha256"), f"{label}.sha256")
    actual, opened = hash_open_regular(path)
    if opened.st_size != size or actual != expected:
        raise ContractError(f"{label} size/hash mismatch")
    return BoundFile(path=path.resolve(strict=True), size=size, sha256=expected)


def load_manifest(path: Path, expected_sha256: str) -> CleanupSpec:
    if not path.is_absolute():
        path = (Path.cwd() / path).absolute()
    require_private_regular(path)
    path = path.resolve(strict=True)
    actual_manifest_sha, _ = hash_open_regular(path)
    if actual_manifest_sha != validate_sha256(expected_sha256, "manifest SHA256"):
        raise ContractError("manifest SHA256 mismatch")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA or manifest.get("status") != STATUS:
        raise ContractError("manifest schema/status mismatch")
    run_id = require_string(manifest.get("run_id"), "run_id")
    f1_run_id = require_string(manifest.get("f1_run_id"), "f1_run_id")
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("cleanup run_id is not exact")
    f1_match = F1_RUN_ID_RE.fullmatch(f1_run_id)
    if f1_match is None:
        raise ContractError("F1 run_id is not exact V3406 display")
    run_root = (PRIVATE_RUN_BASE / run_id).resolve()
    if path.parent != run_root:
        raise ContractError("manifest must be directly inside its private run directory")

    runner = load_bound(manifest.get("runner"), "runner")
    if runner.path != Path(__file__).resolve():
        raise ContractError("manifest runner is not this exact helper")
    transport = load_bound(manifest.get("transport"), "transport")
    if transport.path != A90CTL_SOURCE.resolve(strict=True):
        raise ContractError("manifest transport is not the exact a90ctl source")
    connected_d0 = load_bound(manifest.get("connected_d0"), "connected_d0")
    require_private_regular(connected_d0.path)
    d0_value = json.loads(connected_d0.path.read_text(encoding="utf-8"))
    d0_target = require_dict(d0_value.get("target"), "connected_d0.target")
    health = require_dict(d0_value.get("health"), "connected_d0.health")
    d0_repository = require_dict(
        d0_value.get("repository"),
        "connected_d0.repository",
    )
    preflight_sha, preflight_stat = hash_open_regular(CONNECTED_PREFLIGHT)
    if (
        d0_value.get("schema") != "a90-v3403-connected-d0-v1"
        or d0_value.get("outcome")
        != (
            "PASS_A90_V3403_CONNECTED_READ_ONLY_"
            "AWAITING_STAGING_CONTRACT_AND_F1_MANIFEST"
        )
        or d0_value.get("run_id") != f"{f1_run_id}-connected-d0-01"
        or d0_target.get("profile") != "galaxy-a90-5g-native-init"
        or d0_target.get("matching_a90_usb_devices") != 1
        or health.get("version") != EXPECTED_VERSION
        or health.get("version_build") != EXPECTED_BUILD
        or require_dict(health.get("selftest"), "selftest").get("fail") != 0
        or health.get("pstore_entries") != 0
        or d0_repository.get("connected_preflight")
        != str(CONNECTED_PREFLIGHT.resolve(strict=True))
        or d0_repository.get("connected_preflight_size")
        != preflight_stat.st_size
        or d0_repository.get("connected_preflight_sha256") != preflight_sha
    ):
        raise ContractError("connected D0 does not bind the exact cleanup state")

    target = require_dict(manifest.get("target"), "target")
    if (
        target.get("profile") != "galaxy-a90-5g-native-init"
        or target.get("expected_vendor_product") != EXPECTED_VENDOR_PRODUCT
        or target.get("expected_version") != EXPECTED_VERSION
        or target.get("expected_build") != EXPECTED_BUILD
    ):
        raise ContractError("target contract mismatch")
    bridge_device = Path(
        require_string(target.get("bridge_device"), "target.bridge_device")
    )
    if (
        bridge_device.parent != Path("/dev/serial/by-id")
        or not bridge_device.name.startswith("usb-A90-LNX_")
    ):
        raise ContractError("target bridge is not the exact private A90 by-id form")
    bridge_realpath_sha256 = validate_sha256(
        target.get("bridge_realpath_sha256"),
        "target.bridge_realpath_sha256",
    )
    usb_serial_sha256 = validate_sha256(
        target.get("usb_serial_sha256"),
        "target.usb_serial_sha256",
    )
    d0_realpath = require_string(
        d0_target.get("bridge_selected_realpath"),
        "connected_d0 target realpath",
    )
    if (
        d0_target.get("bridge_device") != str(bridge_device)
        or hashlib.sha256(d0_realpath.encode("utf-8")).hexdigest()
        != bridge_realpath_sha256
        or d0_target.get("usb_serial_sha256") != usb_serial_sha256
    ):
        raise ContractError("connected D0 and cleanup target identity differ")

    work_item = require_dict(manifest.get("work_image"), "work_image")
    work_sha256 = validate_sha256(
        work_item.get("sha256"),
        "work_image.sha256",
    )
    if (
        work_item.get("device_path") != WORK_PATH
        or work_item.get("size") != WORK_SIZE
        or work_item.get("mode") != WORK_MODE
    ):
        raise ContractError("work-image contract is not exact")
    host_copy = load_bound(work_item.get("host_preservation"), "host_preservation")
    require_private_regular(host_copy.path)
    if host_copy.size != WORK_SIZE or host_copy.sha256 != work_sha256:
        raise ContractError("host preservation is not the exact work image")
    if host_copy.path.is_relative_to(run_root):
        raise ContractError("host preservation must remain outside cleanup run")

    adjacent = require_dict(manifest.get("adjacent_paths"), "adjacent_paths")
    source_path = require_string(adjacent.get("v3406_source"), "v3406_source")
    stage_path = require_string(adjacent.get("run_stage"), "run_stage")
    suffix = f1_match.group("suffix")
    expected_source = (
        "/mnt/sdext/a90/runtime/"
        f"debian-bookworm-arm64-phase2-display-v3406-keyed-{suffix}.img"
    )
    expected_stage = f"/mnt/sdext/a90/runtime/.a90-stage-{f1_run_id}"
    if source_path != expected_source or stage_path != expected_stage:
        raise ContractError("adjacent paths are not derived from the F1 run ID")

    authority = require_dict(manifest.get("authority"), "authority")
    if (
        authority.get("device_write_authorized") is not False
        or authority.get("fresh_exact_approval_required") is not True
        or authority.get("single_unlink_dispatch") is not True
        or authority.get("unlink_retry_forbidden") is not True
    ):
        raise ContractError("manifest authority contract mismatch")
    return CleanupSpec(
        manifest_path=path,
        manifest_sha256=actual_manifest_sha,
        run_id=run_id,
        f1_run_id=f1_run_id,
        runner=runner,
        transport=transport,
        connected_d0=connected_d0,
        bridge_device=bridge_device,
        bridge_realpath_sha256=bridge_realpath_sha256,
        usb_serial_sha256=usb_serial_sha256,
        host_copy=host_copy,
        work_sha256=work_sha256,
        source_path=source_path,
        stage_path=stage_path,
    )


def approval_binding(spec: CleanupSpec) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "f1_run_id": spec.f1_run_id,
        "manifest_sha256": spec.manifest_sha256,
        "runner_sha256": spec.runner.sha256,
        "transport_sha256": spec.transport.sha256,
        "connected_d0_sha256": spec.connected_d0.sha256,
        "bridge_realpath_sha256": spec.bridge_realpath_sha256,
        "usb_serial_sha256": spec.usb_serial_sha256,
        "device_path": WORK_PATH,
        "size": WORK_SIZE,
        "mode": WORK_MODE,
        "work_sha256": spec.work_sha256,
        "host_preservation_sha256": spec.host_copy.sha256,
        "read_timeout_sec": int(READ_TIMEOUT_SEC),
        "cleanup_timeout_sec": int(CLEANUP_TIMEOUT_SEC),
        "single_unlink_dispatch": True,
        "unlink_retry_forbidden": True,
    }


def approval_path(spec: CleanupSpec) -> Path:
    return (PRIVATE_RUN_BASE / spec.run_id / "approval-prepared.json").resolve()


def prepare_approval(spec: CleanupSpec) -> dict[str, Any]:
    host_sha, host_stat = hash_open_regular(spec.host_copy.path)
    if host_stat.st_size != WORK_SIZE or host_sha != spec.work_sha256:
        raise ContractError("host preservation changed before approval preparation")
    binding = approval_binding(spec)
    binding_sha = json_sha256(binding)
    value = {
        "schema": APPROVAL_SCHEMA,
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "approval_binding": binding,
        "approval_binding_sha256": binding_sha,
        "approval_token": APPROVAL_PREFIX + binding_sha,
        "device_contact": False,
        "device_write": False,
        "live_authorized": False,
    }
    write_private_json_exclusive(approval_path(spec), value)
    return value


def load_prepared_approval(spec: CleanupSpec, supplied: str) -> dict[str, Any]:
    path = approval_path(spec)
    require_private_regular(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    binding = approval_binding(spec)
    binding_sha = json_sha256(binding)
    expected_token = APPROVAL_PREFIX + binding_sha
    if (
        value.get("schema") != APPROVAL_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("manifest_sha256") != spec.manifest_sha256
        or value.get("approval_binding") != binding
        or value.get("approval_binding_sha256") != binding_sha
        or value.get("approval_token") != expected_token
        or supplied != expected_token
        or value.get("device_contact") is not False
        or value.get("device_write") is not False
    ):
        raise ContractError("fresh exact cleanup approval mismatch")
    return value


def find_usb_identity(bridge_device: Path) -> tuple[Path, str]:
    if not bridge_device.is_symlink():
        raise ContractError("A90 bridge path is not a symlink")
    resolved = bridge_device.resolve(strict=True)
    if not stat.S_ISCHR(resolved.stat().st_mode):
        raise ContractError("A90 bridge does not resolve to a character device")
    tty = resolved.name
    sys_device = (Path("/sys/class/tty") / tty / "device").resolve(strict=True)
    usb_root: Path | None = None
    for parent in (sys_device, *sys_device.parents):
        vendor = parent / "idVendor"
        product = parent / "idProduct"
        if vendor.is_file() and product.is_file():
            usb_root = parent
            break
    if usb_root is None:
        raise ContractError("A90 bridge USB parent is missing")
    vendor = (usb_root / "idVendor").read_text(encoding="utf-8").strip().lower()
    product = (usb_root / "idProduct").read_text(encoding="utf-8").strip().lower()
    serial_value = (usb_root / "serial").read_text(encoding="utf-8").strip()
    if f"{vendor}:{product}" != EXPECTED_VENDOR_PRODUCT or not serial_value:
        raise ContractError("A90 bridge USB identity mismatch")
    return resolved, hashlib.sha256(serial_value.encode("utf-8")).hexdigest()


def require_exact_target(spec: CleanupSpec) -> dict[str, Any]:
    matching = list(spec.bridge_device.parent.glob("usb-A90-LNX_*"))
    if len(matching) != 1 or matching[0] != spec.bridge_device:
        raise ContractError("exactly one private A90 bridge identity is required")
    resolved, serial_sha = find_usb_identity(spec.bridge_device)
    realpath_sha = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()
    if (
        realpath_sha != spec.bridge_realpath_sha256
        or serial_sha != spec.usb_serial_sha256
    ):
        raise ContractError("current A90 target differs from the manifest binding")
    return {
        "bridge_realpath_sha256": realpath_sha,
        "usb_serial_sha256": serial_sha,
        "matching_a90_bridges": 1,
        "resolved_bridge": str(resolved),
    }


def _argv_unique_value(argv: list[str], flag: str) -> str | None:
    indexes = [index for index, value in enumerate(argv) if value == flag]
    if len(indexes) != 1:
        return None
    index = indexes[0]
    if index + 1 >= len(argv):
        return None
    return argv[index + 1]


def require_exact_bridge_process(
    spec: CleanupSpec,
    resolved_bridge: str,
    host: str,
    port: int,
) -> dict[str, Any]:
    if host != "127.0.0.1" or port != a90ctl.DEFAULT_PORT:
        raise ContractError("cleanup transport must use the fixed local bridge endpoint")
    matches: list[int] = []
    for item in Path("/proc").iterdir():
        if not item.name.isdigit():
            continue
        try:
            raw = (item / "cmdline").read_bytes()
        except OSError:
            continue
        argv = [
            part.decode("utf-8", errors="surrogateescape")
            for part in raw.split(b"\0")
            if part
        ]
        if not argv or not any(
            value.endswith("/serial_tcp_bridge.py") for value in argv
        ):
            continue
        if (
            _argv_unique_value(argv, "--host") == host
            and _argv_unique_value(argv, "--port") == str(port)
            and _argv_unique_value(argv, "--device") == str(spec.bridge_device)
            and _argv_unique_value(argv, "--expect-realpath") == resolved_bridge
        ):
            matches.append(int(item.name))
    if len(matches) != 1:
        raise ContractError("exactly one manifest-bound local serial bridge is required")
    return {
        "local_endpoint": f"{host}:{port}",
        "matching_bridge_processes": 1,
    }


def remote_command(
    host: str,
    port: int,
    timeout: float,
    command: list[str],
) -> a90ctl.ProtocolResult:
    return a90ctl.run_cmdv1_command(
        host,
        port,
        timeout,
        command,
        retry_unsafe=False,
    )


def require_protocol_ok(result: a90ctl.ProtocolResult, label: str) -> str:
    if result.rc != 0 or result.status != "ok":
        raise ContractError(f"{label} did not return framed success")
    return result.text


def health_preflight(
    host: str,
    port: int,
    timeout: float,
) -> dict[str, Any]:
    version = require_protocol_ok(
        remote_command(host, port, timeout, ["version"]),
        "version",
    )
    selftest = require_protocol_ok(
        remote_command(host, port, timeout, ["selftest"]),
        "selftest",
    )
    status_text = require_protocol_ok(
        remote_command(host, port, timeout, ["status"]),
        "status",
    )
    match = SELFTEST_RE.search(selftest)
    if (
        VERSION_RE.search(version) is None
        or match is None
        or PSTORE_ZERO_RE.search(status_text) is None
    ):
        raise ContractError("A90 is not the exact healthy V2321 baseline")
    return {
        "proven": True,
        "version": EXPECTED_VERSION,
        "build": EXPECTED_BUILD,
        "selftest_pass": int(match.group("pass")),
        "selftest_warn": int(match.group("warn")),
        "selftest_fail": 0,
        "pstore_entries": 0,
    }


def preflight_script() -> str:
    return (
        'p="$1"; src="$2"; stage="$3"; expected="$4"; '
        '[ ! -L "$p" ] || exit 20; '
        '[ -f "$p" ] || exit 21; '
        'meta=$(/bin/busybox stat -c "%F|%s|%a|%h" "$p") || exit 22; '
        '[ "$meta" = "regular file|2147483648|600|1" ] || exit 23; '
        'actual=$(/bin/busybox sha256sum "$p") || exit 24; '
        'actual=${actual%% *}; [ "$actual" = "$expected" ] || exit 25; '
        '[ ! -e "$src" ] && [ ! -L "$src" ] || exit 26; '
        '[ ! -e "$stage" ] && [ ! -L "$stage" ] || exit 26; '
        '! /bin/busybox grep -F "$p" /proc/mounts >/dev/null 2>&1 || exit 27; '
        'for b in /sys/block/loop*/loop/backing_file; do '
        '[ -r "$b" ] || continue; '
        'v=$(/bin/busybox cat "$b") || exit 28; '
        '[ "$v" != "$p" ] || exit 29; '
        'done; '
        'printf "work=exact source=absent stage=absent in_use=no\\n"'
    )


def cleanup_script() -> str:
    return (
        'p="$1"; expected="$2"; src="$3"; stage="$4"; '
        '[ ! -L "$p" ] || exit 40; '
        '[ -f "$p" ] || exit 41; '
        'meta=$(/bin/busybox stat -c "%F|%s|%a|%h" "$p") || exit 42; '
        '[ "$meta" = "regular file|2147483648|600|1" ] || exit 43; '
        'actual=$(/bin/busybox sha256sum "$p") || exit 44; '
        'actual=${actual%% *}; [ "$actual" = "$expected" ] || exit 45; '
        '[ ! -e "$src" ] && [ ! -L "$src" ] || exit 46; '
        '[ ! -e "$stage" ] && [ ! -L "$stage" ] || exit 46; '
        '! /bin/busybox grep -F "$p" /proc/mounts >/dev/null 2>&1 || exit 47; '
        'for b in /sys/block/loop*/loop/backing_file; do '
        '[ -r "$b" ] || continue; '
        'v=$(/bin/busybox cat "$b") || exit 48; '
        '[ "$v" != "$p" ] || exit 49; '
        'done; '
        '/bin/busybox rm -- "$p" || exit 50; '
        '[ ! -e "$p" ] || exit 51; '
        'printf "work=unlinked\\n"'
    )


def presence_script() -> str:
    return (
        'p="$1"; src="$2"; stage="$3"; '
        'if [ -e "$p" ] || [ -L "$p" ]; then w=present; else w=absent; fi; '
        'if [ -e "$src" ] || [ -L "$src" ]; then s=present; else s=absent; fi; '
        'if [ -e "$stage" ] || [ -L "$stage" ]; then t=present; else t=absent; fi; '
        'printf "work=%s source=%s stage=%s\\n" "$w" "$s" "$t"'
    )


def run_read_preflight(
    spec: CleanupSpec,
    host: str,
    port: int,
    timeout: float,
) -> dict[str, Any]:
    result = remote_command(
        host,
        port,
        timeout,
        [
            "run",
            "/bin/busybox",
            "sh",
            "-c",
            preflight_script(),
            "sh",
            WORK_PATH,
            spec.source_path,
            spec.stage_path,
            spec.work_sha256,
        ],
    )
    text = require_protocol_ok(result, "work-image preflight")
    if text.count("work=exact source=absent stage=absent in_use=no") != 1:
        raise ContractError("work-image preflight output is not exact")
    return {"proof": True, "framed_rc": result.rc}


def read_presence(
    spec: CleanupSpec,
    host: str,
    port: int,
    timeout: float,
) -> dict[str, Any]:
    result = remote_command(
        host,
        port,
        timeout,
        [
            "run",
            "/bin/busybox",
            "sh",
            "-c",
            presence_script(),
            "sh",
            WORK_PATH,
            spec.source_path,
            spec.stage_path,
        ],
    )
    text = require_protocol_ok(result, "post-cleanup presence")
    states = re.findall(
        r"work=(absent|present) source=(absent|present) stage=(absent|present)",
        text,
    )
    if len(states) != 1:
        raise ContractError("post-cleanup presence output is not exact")
    work, source, stage = states[0]
    return {
        "work": work,
        "source": source,
        "stage": stage,
        "framed_rc": result.rc,
    }


def execute_cleanup(
    spec: CleanupSpec,
    approval: str,
    transaction_dir: Path,
    *,
    host: str,
    port: int,
    read_timeout: float,
    cleanup_timeout: float,
) -> dict[str, Any]:
    prepared = load_prepared_approval(spec, approval)
    read_timeout = validate_timeout(
        read_timeout,
        "read timeout",
        READ_TIMEOUT_SEC,
    )
    cleanup_timeout = validate_timeout(
        cleanup_timeout,
        "cleanup timeout",
        CLEANUP_TIMEOUT_SEC,
    )
    transaction_dir = transaction_dir.resolve()
    expected_transaction = (PRIVATE_RUN_BASE / spec.run_id / "live").resolve()
    if transaction_dir != expected_transaction or transaction_dir.exists():
        raise ContractError("transaction directory must be the new exact private live path")

    target = require_exact_target(spec)
    target["bridge_process"] = require_exact_bridge_process(
        spec,
        str(target.pop("resolved_bridge")),
        host,
        port,
    )
    before_health = health_preflight(host, port, read_timeout)
    before_remote = run_read_preflight(spec, host, port, cleanup_timeout)
    host_sha, host_stat = hash_open_regular(spec.host_copy.path)
    if host_stat.st_size != WORK_SIZE or host_sha != spec.work_sha256:
        raise ContractError("host preservation changed before dispatch")
    if transaction_dir.exists():
        raise ContractError("transaction directory appeared during preflight")
    transaction_dir.mkdir(mode=0o700)
    _fsync_directory(transaction_dir.parent)

    binding_sha = prepared["approval_binding_sha256"]
    intent = {
        "schema": "a90_v3405_retained_work_cleanup_intent_v1",
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "approval_binding_sha256": binding_sha,
        "approval_token_sha256": hashlib.sha256(
            approval.encode("utf-8")
        ).hexdigest(),
        "target": target,
        "before_health": before_health,
        "before_remote": before_remote,
        "host_preservation_sha256": host_sha,
        "transport_sha256": spec.transport.sha256,
        "device_path": WORK_PATH,
        "work_sha256": spec.work_sha256,
        "dispatch_limit": 1,
        "retry_forbidden": True,
    }
    write_private_json_exclusive(transaction_dir / "intent.json", intent)
    dispatch = {
        "schema": "a90_v3405_retained_work_cleanup_dispatch_v1",
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "dispatch_count": 1,
        "cleanup_command_sha256": hashlib.sha256(
            cleanup_script().encode("utf-8")
        ).hexdigest(),
        "retry_forbidden": True,
        "approval_consumed": True,
    }
    write_private_json_exclusive(transaction_dir / "dispatch.json", dispatch)

    dispatch_error: dict[str, str] | None = None
    response_proven = False
    try:
        result = remote_command(
            host,
            port,
            cleanup_timeout,
            [
                "run",
                "/bin/busybox",
                "sh",
                "-c",
                cleanup_script(),
                "sh",
                WORK_PATH,
                spec.work_sha256,
                spec.source_path,
                spec.stage_path,
            ],
        )
        text = require_protocol_ok(result, "cleanup dispatch")
        response_proven = text.count("work=unlinked") == 1
        if not response_proven:
            dispatch_error = {
                "type": "ContractError",
                "message": "cleanup response lacks exact unlink marker",
            }
    except Exception as exc:  # noqa: BLE001 - never retransmit after dispatch
        dispatch_error = {"type": type(exc).__name__, "message": str(exc)}
    if dispatch_error is not None:
        write_private_json_exclusive(
            transaction_dir / "dispatch-error.json",
            {
                "schema": "a90_v3405_retained_work_cleanup_dispatch_error_v1",
                "created_utc": utc_now(),
                "run_id": spec.run_id,
                "error": dispatch_error,
                "cleanup_retransmitted": False,
                "read_only_reconciliation_allowed": True,
            },
        )

    post_error: dict[str, str] | None = None
    try:
        presence = read_presence(spec, host, port, read_timeout)
    except Exception as exc:  # noqa: BLE001 - post-dispatch read, never unlink retry
        presence = {
            "work": "unknown",
            "source": "unknown",
            "stage": "unknown",
        }
        post_error = {"type": type(exc).__name__, "message": str(exc)}
    try:
        after_health = health_preflight(host, port, read_timeout)
    except Exception as exc:  # noqa: BLE001 - health failure cannot repeat unlink
        after_health = {"proven": False}
        if post_error is None:
            post_error = {"type": type(exc).__name__, "message": str(exc)}
        else:
            post_error["health_error_type"] = type(exc).__name__
            post_error["health_error_message"] = str(exc)
    effect_proven = (
        presence["work"] == "absent"
        and presence["source"] == "absent"
        and presence["stage"] == "absent"
    )
    post_health_proven = after_health.get("proven") is True
    complete = effect_proven and post_health_proven
    outcome = (
        "PASS_EXACT_RETAINED_WORK_COPY_UNLINKED"
        if complete and response_proven
        else "PASS_EFFECT_PROVEN_AFTER_AMBIGUOUS_RESPONSE"
        if complete
        else "STOP_NO_RETRY_POST_HEALTH_UNPROVEN"
        if effect_proven
        else "STOP_NO_RETRY_RETAINED_WORK_COPY_NOT_PROVEN_ABSENT"
    )
    result_value = {
        "schema": RESULT_SCHEMA,
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "approval_binding_sha256": binding_sha,
        "outcome": outcome,
        "dispatch_count": 1,
        "cleanup_retransmitted": False,
        "response_proven": response_proven,
        "post_presence": presence,
        "post_health": after_health,
        "post_error": post_error,
        "effect_proven": effect_proven,
        "post_health_proven": post_health_proven,
        "work_sha256": spec.work_sha256,
        "host_preservation_sha256": host_sha,
        "device_write": True,
        "deleted_path": WORK_PATH if effect_proven else None,
        "flash": False,
        "reboot_requested": False,
        "payload_sent": False,
        "other_device_commands": 0,
    }
    write_private_json_exclusive(transaction_dir / "result.json", result_value)
    return result_value


def inspect(spec: CleanupSpec) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "mode": "host-only-inspection",
        "run_id": spec.run_id,
        "f1_run_id": spec.f1_run_id,
        "manifest_sha256": spec.manifest_sha256,
        "runner_sha256": spec.runner.sha256,
        "transport_sha256": spec.transport.sha256,
        "connected_d0_sha256": spec.connected_d0.sha256,
        "work_sha256": spec.work_sha256,
        "host_preservation_sha256": spec.host_copy.sha256,
        "ready_for_approval_preparation": True,
        "device_contact": False,
        "device_write": False,
        "live_authorized": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expect-manifest-sha256", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--execute-approved-cleanup", action="store_true")
    parser.add_argument("--approval")
    parser.add_argument("--transaction-dir", type=Path)
    parser.add_argument("--bridge-host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--bridge-port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--read-timeout", type=float, default=READ_TIMEOUT_SEC)
    parser.add_argument(
        "--cleanup-timeout",
        type=float,
        default=CLEANUP_TIMEOUT_SEC,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec = load_manifest(args.manifest, args.expect_manifest_sha256)
    if args.prepare_approval:
        if args.approval is not None or args.transaction_dir is not None:
            raise ContractError("approval preparation accepts no live arguments")
        value = prepare_approval(spec)
    elif args.execute_approved_cleanup:
        if args.approval is None or args.transaction_dir is None:
            raise ContractError("live cleanup requires approval and transaction directory")
        value = execute_cleanup(
            spec,
            args.approval,
            args.transaction_dir,
            host=args.bridge_host,
            port=args.bridge_port,
            read_timeout=args.read_timeout,
            cleanup_timeout=args.cleanup_timeout,
        )
    else:
        if args.approval is not None or args.transaction_dir is not None:
            raise ContractError("host inspection accepts no live arguments")
        value = inspect(spec)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
