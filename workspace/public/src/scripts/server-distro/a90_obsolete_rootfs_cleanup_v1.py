#!/usr/bin/env python3
"""Exact attended garbage collection of host-recoverable A90 SD rootfs images.

The default mode is host-only inspection. Inventory capture is bounded D0.
Live D1 execution requires a fresh exact inventory, immutable execution
binding, attended presence, a new durable transaction, one nonrecursive unlink
dispatch, read-only reconciliation, and final V3406 health. Selection is
derived only from successful absent-only staging receipts whose exact bytes
remain privately preserved on the host. The unlink is never retransmitted.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SERVER_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for directory in (SERVER_DIR, REVAL_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import a90_v3405_retained_work_cleanup as legacy  # noqa: E402
import a90_transition_d1_session_v1 as resident_d1  # noqa: E402
import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90ctl  # noqa: E402


SCHEMA = "a90_attended_sd_rootfs_gc_manifest_v2"
STATUS = "ready-for-attended-rootfs-gc"
INVENTORY_SCHEMA = "a90_attended_sd_rootfs_gc_inventory_v2"
APPROVAL_SCHEMA = "a90_attended_sd_rootfs_gc_compatibility_binding_v2"
APPROVAL_PREFIX = "A90-SD-ROOTFS-GC-V2-COMPAT:"
RESULT_SCHEMA = "a90_attended_sd_rootfs_gc_result_v2"
CAPABILITY = "A90_ATTENDED_SD_ROOTFS_GC_V2"
PRIVATE_BASE = (
    REPO_ROOT / "workspace" / "private" / "runs" / "server-distro"
).resolve()
PRIVATE_ROOT = (REPO_ROOT / "workspace" / "private").resolve()
RUNNER = Path(__file__).resolve()
A90CTL = (REVAL_DIR / "a90ctl.py").resolve()
LEGACY_RUNNER = (SERVER_DIR / "a90_v3405_retained_work_cleanup.py").resolve()
D1_RUNNER = (SERVER_DIR / "a90_transition_d1_session_v1.py").resolve()
SERIAL_TCP_BRIDGE = (REVAL_DIR / "serial_tcp_bridge.py").resolve()
OBSERVATION_PIPELINE = (REVAL_DIR / "a90_observation_pipeline.py").resolve()
SERIAL_LOCK = (REVAL_DIR / "a90_serial_lock.py").resolve()
TRANSITION_CONTRACT = (REVAL_DIR / "a90_transition_contract_v2.py").resolve()
WORKSPACE_BOOTSTRAP = (REVAL_DIR / "_workspace_bootstrap.py").resolve()
TCPCTL_HOST = (REVAL_DIR / "tcpctl_host.py").resolve()
EVIDENCE_HELPER = (
    REPO_ROOT
    / "workspace"
    / "public"
    / "src"
    / "harness"
    / "a90harness"
    / "evidence.py"
).resolve()
STAGING_RUNNER = (SERVER_DIR / "a90_v3403_absent_only_staging.py").resolve()
COMMON_CONTRACT = (REPO_ROOT / "AGENTS.md").resolve()
TARGET_CONTRACT = (
    REPO_ROOT / "docs" / "operations" / "targets" / "A90_TARGET_CONTRACT.md"
).resolve()
RISK_TIERS = (
    REPO_ROOT / "docs" / "operations" / "DEVICE_ACTION_RISK_TIERS.md"
).resolve()
F1_RESULT = (
    PRIVATE_BASE
    / "a90-v3406-debian-display-f1-20260803-04"
    / "f1-live"
    / "result.json"
)
D1_RESULT = (
    PRIVATE_BASE
    / "a90-d1-attended-20260803-07"
    / "d1-live"
    / "action-001"
    / "result.json"
)
DISPLAY_CONFIRMATION = (
    PRIVATE_BASE
    / "a90-d1-attended-20260803-07"
    / "d1-live"
    / "action-001"
    / "display-visible-confirmation.json"
)
D1_MANIFEST = (
    PRIVATE_BASE / "a90-d1-attended-20260803-07" / "manifest.json"
)
D1_MANIFEST_SHA256 = (
    "34edbed80112811910784b07e2308b90ec121defd97847251671e4cd5354f5cc"
)
BRIDGE_DEVICE = Path(
    "/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00"
)
USB_SERIAL_SHA256 = (
    "21e7dfcb89397f16cf8f58f366d5fa91aeddb523b9507077786bb94fff697ee2"
)
EXPECTED_VERSION = "0.11.161"
EXPECTED_BUILD = "phase2-display-v1-native-handoff"
EXPECTED_VENDOR_PRODUCT = "04e8:6861"
RECOVERY_PROFILE = (
    "attended physical Download or TWRP path followed by the exact checked "
    "V2321 rollback"
)
IMAGE_SIZE = 2147483648
IMAGE_MODE = "600"
WORK_PATH = "/mnt/sdext/a90/runtime/d3-handoff-work.img"
READ_TIMEOUT_SEC = 20.0
HASH_TIMEOUT_SEC = 240.0
CLEANUP_TIMEOUT_SEC = 300.0
MAX_INVENTORY_AGE_SEC = 900
FREE_GAIN_TOLERANCE_KIB = 65536
MAX_SELECTED = 32
MAX_INVENTORY_FRAME_SCRIPT_BYTES = 1024
MAX_CMDV1X_WIRE_BYTES = 3800
RUN_ID_RE = re.compile(r"^a90-sd-cleanup-[0-9]{8}-[0-9]{2}$")
SELECTION_RUN_ID_RE = re.compile(
    r"^a90-v(?:3403-debian-f1|3404-debian-f1|3405-debian-f1|"
    r"3406-debian-display-f1)-[0-9]{8}-[0-9]{2}$"
)
SELECTABLE_DEVICE_PATH_RE = re.compile(
    r"^/mnt/sdext/a90/runtime/debian-bookworm-arm64-(?:"
    r"d3-sysvinit-(?:v3403|v3404|v3405)-keyed(?:-[0-9]{8}-[0-9]{2})?"
    r"|phase2-display-v3406-keyed-[0-9]{8}-[0-9]{2})\.img$"
)
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
VERSION_RE = re.compile(
    r"^version: 0\.11\.161 build=phase2-display-v1-native-handoff\r?$",
    re.MULTILINE,
)
SELFTEST_RE = re.compile(
    r"^selftest: pass=(?P<pass>[0-9]+) warn=(?P<warn>[0-9]+) "
    r"fail=0 duration=(?P<duration>[0-9]+)ms entries=(?P<entries>[0-9]+)\r?$",
    re.MULTILINE,
)
PSTORE_RE = re.compile(
    r"^pstore=fs=yes mounted=no dir=yes entries=0\b",
    re.MULTILINE,
)
RUNTIME_RE = re.compile(
    r"^runtime: backend=sd root=/mnt/sdext/a90 fallback=no writable=yes\r?$",
    re.MULTILINE,
)
IMAGE_LINE_RE = re.compile(
    r"^A90CLEAN_IMG\|(?P<path>/mnt/sdext/a90/runtime/[A-Za-z0-9._-]+\.img)"
    r"\|(?P<size>[0-9]+)\|(?P<blocks>[0-9]+)\|(?P<mode>[0-9]+)"
    r"\|(?P<nlink>[0-9]+)\|(?P<dev>[0-9]+)\|(?P<ino>[0-9]+)"
    r"\|(?P<sha>[0-9a-f]{64})\r?$",
    re.MULTILINE,
)
DF_LINE_RE = re.compile(
    r"^A90CLEAN_DF\|(?P<blocks>[0-9]+)\|(?P<used>[0-9]+)"
    r"\|(?P<available>[0-9]+)\r?$",
    re.MULTILINE,
)


class ContractError(RuntimeError):
    """The exact cleanup contract is not satisfied."""


@dataclass(frozen=True)
class FixedImage:
    role: str
    device_path: str
    sha256: str
    host_preservation: Path | None


@dataclass(frozen=True)
class SelectionSource:
    run_id: str
    fixed: FixedImage
    host_path: Path
    prepared_manifest: legacy.BoundFile
    staging_result: legacy.BoundFile


@dataclass(frozen=True)
class ImageRecord:
    role: str
    device_path: str
    size: int
    blocks: int
    mode: str
    nlink: int
    st_dev: int
    st_ino: int
    sha256: str
    host_preservation: legacy.BoundFile | None


@dataclass(frozen=True)
class CleanupSpec:
    manifest_path: Path
    manifest_sha256: str
    run_id: str
    selected_run_ids: tuple[str, ...]
    inventory: legacy.BoundFile
    bridge_realpath: str
    bridge_process: dict[str, Any]
    selected: tuple[ImageRecord, ...]
    protected: tuple[ImageRecord, ImageRecord]
    source_closure: dict[str, legacy.BoundFile]
    f1_result: legacy.BoundFile
    d1_result: legacy.BoundFile
    display_confirmation: legacy.BoundFile
    recovery_manifest: legacy.BoundFile
    recovery_rollback: legacy.BoundFile
    recovery_profile: str
    recovery_serial_sha256: str
    recovery_observer_device: str
    restoration_evidence: tuple[
        tuple[legacy.BoundFile, legacy.BoundFile], ...
    ]


FIXED_PROTECTED = (
    FixedImage(
        "incident-preserve-20260803-03",
        "/mnt/sdext/a90/runtime/"
        "debian-bookworm-arm64-phase2-display-v3406-keyed-20260803-03.img",
        "787986ddb9be0cd3b4109b5059b32423525e8803251e5f1e64f1e223e9f9266c",
        None,
    ),
    FixedImage(
        "current-resident-20260803-04",
        "/mnt/sdext/a90/runtime/"
        "debian-bookworm-arm64-phase2-display-v3406-keyed-20260803-04.img",
        "9f169b6b7008168e172fb4abda446440fbbbe443daa2a1c991d25c5ceeabc847",
        None,
    ),
)


def _expected_source_paths() -> dict[str, Path]:
    paths = {
        "runner": RUNNER,
        "transport": A90CTL,
        "legacy_cleanup_primitives": LEGACY_RUNNER,
        "resident_health_parser": D1_RUNNER,
        "serial_tcp_bridge": SERIAL_TCP_BRIDGE,
        "observation_pipeline": OBSERVATION_PIPELINE,
        "serial_lock": SERIAL_LOCK,
        "transition_contract": TRANSITION_CONTRACT,
        "workspace_bootstrap": WORKSPACE_BOOTSTRAP,
        "restoration_staging": STAGING_RUNNER,
        "restoration_tcpctl_host": TCPCTL_HOST,
        "restoration_evidence_helper": EVIDENCE_HELPER,
        "common_contract": COMMON_CONTRACT,
        "target_contract": TARGET_CONTRACT,
        "risk_tiers": RISK_TIERS,
    }
    for role, path in resident_d1.SOURCE_PATHS.items():
        paths[f"d1_recovery_{role}"] = path.resolve()
    return paths


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a non-empty string")
    return value


def _require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ContractError(f"{label} must be an exact integer")
    return value


def _require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise ContractError(f"{label} must be lowercase SHA256")
    return value


def _require_private(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(PRIVATE_ROOT):
        raise ContractError("private input is outside workspace/private")
    item = path.lstat()
    if (
        not stat.S_ISREG(item.st_mode)
        or stat.S_IMODE(item.st_mode) != 0o600
        or item.st_nlink != 1
    ):
        raise ContractError("private input is not an exact mode-0600 regular file")
    return resolved


def _bound(path: Path, *, private: bool) -> legacy.BoundFile:
    if private:
        path = _require_private(path)
    digest, item = legacy.hash_open_regular(path)
    return legacy.BoundFile(
        path=path.resolve(strict=True),
        size=item.st_size,
        sha256=digest,
    )


def _selection_sources(run_ids: list[str]) -> tuple[SelectionSource, ...]:
    if (
        not run_ids
        or len(run_ids) > MAX_SELECTED
        or run_ids != sorted(run_ids)
        or len(run_ids) != len(set(run_ids))
        or any(SELECTION_RUN_ID_RE.fullmatch(item) is None for item in run_ids)
    ):
        raise ContractError("selected staging run IDs are not canonical")
    loaded: list[SelectionSource] = []
    seen_paths: set[str] = set()
    seen_hosts: set[Path] = set()
    protected_paths = {item.device_path for item in FIXED_PROTECTED}
    for run_id in run_ids:
        run_dir = (PRIVATE_BASE / run_id).resolve()
        prepared = _bound(run_dir / "prepared-manifest.json", private=True)
        result = _bound(run_dir / "staging-live" / "result.json", private=True)
        manifest_value = _require_dict(
            json.loads(prepared.path.read_text(encoding="utf-8")),
            f"{run_id} prepared manifest",
        )
        result_value = _require_dict(
            json.loads(result.path.read_text(encoding="utf-8")),
            f"{run_id} staging result",
        )
        rootfs = _require_dict(result_value.get("rootfs"), f"{run_id} rootfs")
        publication = _require_dict(
            result_value.get("publication"),
            f"{run_id} publication",
        )
        safety = _require_dict(result_value.get("safety"), f"{run_id} safety")
        debian_rootfs = _require_dict(
            manifest_value.get("debian_rootfs"),
            f"{run_id} Debian rootfs",
        )
        keyed = _require_dict(
            debian_rootfs.get("keyed_source"),
            f"{run_id} keyed source",
        )
        device_path = _require_string(
            rootfs.get("device_path"),
            f"{run_id} device path",
        )
        sha256 = _require_sha(rootfs.get("sha256"), f"{run_id} rootfs SHA256")
        local_path = Path(
            _require_string(keyed.get("local_path"), f"{run_id} local path")
        )
        host_path = _require_private(local_path)
        host_state = host_path.lstat()
        if (
            result_value.get("schema")
            != "a90_v3403_absent_only_staging_adapter_v1"
            or result_value.get("status") != "PASS_ABSENT_ONLY_ROOTFS_STAGED"
            or result_value.get("run_id") != run_id
            or result_value.get("manifest_sha256") != prepared.sha256
            or manifest_value.get("run_id") != run_id
            or set(rootfs) != {"device_path", "size", "sha256"}
            or type(rootfs.get("size")) is not int
            or rootfs.get("size") != IMAGE_SIZE
            or SELECTABLE_DEVICE_PATH_RE.fullmatch(device_path) is None
            or device_path in protected_paths
            or keyed.get("device_path") != device_path
            or type(keyed.get("size")) is not int
            or keyed.get("size") != IMAGE_SIZE
            or keyed.get("sha256") != sha256
            or host_path.parent != run_dir
            or host_state.st_size != IMAGE_SIZE
            or set(publication)
            != {"primitive", "stage_dir_removed", "candidate_allowed"}
            or publication.get("primitive") != "hardlink-no-clobber"
            or publication.get("stage_dir_removed") is not True
            or publication.get("candidate_allowed") is not True
            or set(safety)
            != {"flash", "mount", "reboot", "switch_root", "userdata_touched"}
            or any(safety.get(key) is not False for key in safety)
            or device_path in seen_paths
            or host_path in seen_hosts
        ):
            raise ContractError(f"{run_id} is not an exact selectable staging run")
        seen_paths.add(device_path)
        seen_hosts.add(host_path)
        loaded.append(
            SelectionSource(
                run_id=run_id,
                fixed=FixedImage(
                    role=f"obsolete-{run_id}",
                    device_path=device_path,
                    sha256=sha256,
                    host_preservation=host_path,
                ),
                host_path=host_path,
                prepared_manifest=prepared,
                staging_result=result,
            )
        )
    return tuple(loaded)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _as_bound(value: legacy.BoundFile) -> dict[str, Any]:
    return {"path": str(value.path), "size": value.size, "sha256": value.sha256}


def _load_bound(value: Any, label: str, *, private: bool) -> legacy.BoundFile:
    item = _require_dict(value, label)
    if set(item) != {"path", "size", "sha256"}:
        raise ContractError(f"{label} binding shape is not exact")
    path = Path(_require_string(item.get("path"), f"{label}.path"))
    if not path.is_absolute():
        path = (Path.cwd() / path).absolute()
    bound = _bound(path, private=private)
    if (
        bound.size != _require_int(item.get("size"), f"{label}.size", minimum=1)
        or bound.sha256 != _require_sha(item.get("sha256"), f"{label}.sha256")
    ):
        raise ContractError(f"{label} size/hash changed")
    return bound


def _remote(command: list[str], timeout: float) -> a90ctl.ProtocolResult:
    return a90ctl.run_cmdv1_command(
        a90ctl.DEFAULT_HOST,
        a90ctl.DEFAULT_PORT,
        timeout,
        command,
        retry_unsafe=False,
    )


def _protocol_text(result: a90ctl.ProtocolResult, label: str) -> str:
    if type(result.rc) is not int or result.rc != 0 or result.status != "ok":
        raise ContractError(f"{label} did not return exact framed success")
    return result.text


def _script_command(script: str, args: tuple[str, ...] = ()) -> list[str]:
    if not script:
        raise ContractError("empty device script")
    command = ["run", "/bin/busybox", "sh", "-c", script]
    if args:
        command += ["a90-rootfs-gc", *args]
    return command


def _command_wire_bytes(command: list[str]) -> int:
    return len(a90ctl.encode_cmdv1_line(command).encode("utf-8")) + 1


def _require_bounded_command(command: list[str], label: str) -> None:
    wire_bytes = _command_wire_bytes(command)
    if wire_bytes > MAX_CMDV1X_WIRE_BYTES:
        raise ContractError(
            f"{label} exceeds bounded cmdv1x frame: "
            f"{wire_bytes} > {MAX_CMDV1X_WIRE_BYTES}"
        )


def _run_script(
    script: str,
    timeout: float,
    label: str,
    *,
    args: tuple[str, ...] = (),
) -> str:
    command = _script_command(script, args)
    _require_bounded_command(command, label)
    return _protocol_text(_remote(command, timeout), label)


def _find_target() -> tuple[str, str]:
    matches = list(BRIDGE_DEVICE.parent.glob("usb-A90-LNX_*"))
    if len(matches) != 1 or matches[0] != BRIDGE_DEVICE:
        raise ContractError("exactly one A90 by-id target is required")
    resolved, serial_sha = legacy.find_usb_identity(BRIDGE_DEVICE)
    if serial_sha != USB_SERIAL_SHA256:
        raise ContractError("A90 USB serial binding changed")
    return str(resolved), serial_sha


def _argv_value(argv: list[str], flag: str) -> str | None:
    indexes = [index for index, value in enumerate(argv) if value == flag]
    if len(indexes) != 1 or indexes[0] + 1 >= len(argv):
        return None
    return argv[indexes[0] + 1]


def _process_start_epoch_sec(pid: int, proc_root: Path = Path("/proc")) -> int:
    stat_text = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    close = stat_text.rfind(")")
    if close < 0:
        raise ContractError("bridge process stat is malformed")
    fields = stat_text[close + 2 :].split()
    if len(fields) <= 19:
        raise ContractError("bridge process stat is incomplete")
    start_ticks = int(fields[19])
    clock_ticks = int(os.sysconf("SC_CLK_TCK"))
    boot_values = [
        line.split()[1]
        for line in (proc_root / "stat").read_text(encoding="utf-8").splitlines()
        if line.startswith("btime ")
    ]
    if len(boot_values) != 1 or clock_ticks <= 0:
        raise ContractError("bridge process boot clock is unavailable")
    return int(boot_values[0]) + start_ticks // clock_ticks


def _require_bridge(
    realpath: str,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    required = {
        "--host": a90ctl.DEFAULT_HOST,
        "--port": str(a90ctl.DEFAULT_PORT),
        "--device": str(BRIDGE_DEVICE),
        "--device-glob": (
            str(BRIDGE_DEVICE)
            + ",/dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_*"
        ),
        "--capture": None,
        "--expect-realpath": realpath,
    }
    bridge_digest, bridge_state = legacy.hash_open_regular(SERIAL_TCP_BRIDGE)
    if bridge_digest != _bound(SERIAL_TCP_BRIDGE, private=False).sha256:
        raise ContractError("serial bridge source changed during validation")
    for item in proc_root.iterdir():
        if not item.name.isdigit():
            continue
        try:
            argv = [
                part.decode("utf-8", errors="surrogateescape")
                for part in (item / "cmdline").read_bytes().split(b"\0")
                if part
            ]
        except OSError:
            continue
        if len(argv) != 2 + 2 * len(required):
            continue
        try:
            interpreter = Path(argv[0]).resolve(strict=True)
            script = Path(argv[1]).resolve(strict=True)
        except OSError:
            continue
        if interpreter != Path(sys.executable).resolve(strict=True):
            continue
        if argv[1] != str(SERIAL_TCP_BRIDGE) or script != SERIAL_TCP_BRIDGE:
            continue
        flags = argv[2::2]
        if len(flags) != len(set(flags)) or set(flags) != set(required):
            continue
        values = {flag: _argv_value(argv, flag) for flag in required}
        if any(
            values[flag] != expected
            for flag, expected in required.items()
            if expected is not None
        ):
            continue
        capture_value = values["--capture"]
        if not isinstance(capture_value, str):
            continue
        capture = Path(capture_value)
        if (
            not capture.is_absolute()
            or not capture.resolve().is_relative_to(PRIVATE_ROOT / "logs" / "bridge")
        ):
            continue
        pid = int(item.name)
        start_epoch_sec = _process_start_epoch_sec(pid, proc_root)
        source_mtime_ceiling = (
            bridge_state.st_mtime_ns + 999_999_999
        ) // 1_000_000_000
        if source_mtime_ceiling > start_epoch_sec:
            continue
        matches.append(
            {
                "pid": pid,
                "start_epoch_sec": start_epoch_sec,
                "script_path": str(SERIAL_TCP_BRIDGE),
                "script_sha256": bridge_digest,
                "script_mtime_ns": bridge_state.st_mtime_ns,
                "argv_sha256": legacy.json_sha256(argv),
                "forbidden_options_absent": True,
                "matching_processes": 1,
                "local_endpoint": "127.0.0.1:54321",
            }
        )
    if len(matches) != 1:
        raise ContractError("exactly one realpath-pinned A90 bridge is required")
    return matches[0]


def _validated_bridge_process(value: Any) -> dict[str, Any]:
    item = _require_dict(value, "bridge process")
    current_digest, current_state = legacy.hash_open_regular(SERIAL_TCP_BRIDGE)
    if (
        set(item)
        != {
            "pid",
            "start_epoch_sec",
            "script_path",
            "script_sha256",
            "script_mtime_ns",
            "argv_sha256",
            "forbidden_options_absent",
            "matching_processes",
            "local_endpoint",
        }
        or type(item.get("pid")) is not int
        or item["pid"] <= 0
        or type(item.get("start_epoch_sec")) is not int
        or item["start_epoch_sec"] <= 0
        or type(item.get("script_mtime_ns")) is not int
        or item["script_mtime_ns"] <= 0
        or item.get("script_path") != str(SERIAL_TCP_BRIDGE)
        or item.get("script_sha256") != current_digest
        or item.get("script_mtime_ns") != current_state.st_mtime_ns
        or _require_sha(item.get("argv_sha256"), "bridge argv SHA256")
        != item.get("argv_sha256")
        or item.get("forbidden_options_absent") is not True
        or type(item.get("matching_processes")) is not int
        or item.get("matching_processes") != 1
        or item.get("local_endpoint") != "127.0.0.1:54321"
        or (item["script_mtime_ns"] + 999_999_999) // 1_000_000_000
        > item["start_epoch_sec"]
    ):
        raise ContractError("bridge process binding is not exact")
    return item


def _health() -> dict[str, Any]:
    version = _protocol_text(_remote(["version"], READ_TIMEOUT_SEC), "version")
    selftest = _protocol_text(_remote(["selftest"], READ_TIMEOUT_SEC), "selftest")
    status_text = _protocol_text(_remote(["status"], READ_TIMEOUT_SEC), "status")
    match = SELFTEST_RE.search(selftest)
    if (
        VERSION_RE.search(version) is None
        or match is None
        or PSTORE_RE.search(status_text) is None
        or RUNTIME_RE.search(status_text) is None
    ):
        raise ContractError("A90 is not exact healthy resident V3406")
    return {
        "proven": True,
        "version": EXPECTED_VERSION,
        "build": EXPECTED_BUILD,
        "selftest_pass": int(match.group("pass")),
        "selftest_warn": int(match.group("warn")),
        "selftest_fail": 0,
        "pstore_entries": 0,
        "runtime_root": "/mnt/sdext/a90",
    }


def _inventory_work_script() -> str:
    return "\n".join(
        [
            "set -eu",
            f"WORK={shlex.quote(WORK_PATH)}",
        'if [ -e "$WORK" ] || [ -L "$WORK" ]; then '
        "echo WORK_PRESENT=1; exit 20; fi",
        "echo WORK_ABSENT=1",
        ]
    )


def _inventory_image_script(index: int, fixed: FixedImage) -> str:
    if type(index) is not int or index < 0:
        raise ContractError("inventory image index is not exact")
    return "\n".join(
        [
            "set -eu",
            f"P={shlex.quote(fixed.device_path)}",
            '[ ! -L "$P" ]',
            '[ -f "$P" ]',
            'META=$(/bin/busybox stat -c "%n|%s|%b|%a|%h|%d|%i" "$P")',
            'SHA=$(/bin/busybox sha256sum "$P")',
            'SHA=${SHA%% *}',
            f'echo "A90CLEAN_INDEX|{index}"',
            'echo "A90CLEAN_IMG|$META|$SHA"',
        ]
    )


def _inventory_df_script() -> str:
    return "\n".join(
        [
            "set -eu",
            'set -- $(/bin/busybox df -k /mnt/sdext | /bin/busybox tail -n 1)',
            'echo "A90CLEAN_DF|$2|$3|$4"',
        ]
    )


def _bounded_inventory_read(script: str, timeout: float, label: str) -> str:
    if not script or len(script.encode("utf-8")) > MAX_INVENTORY_FRAME_SCRIPT_BYTES:
        raise ContractError("inventory frame script exceeds the reviewed bound")
    return _run_script(script, timeout, label)


def _parse_inventory(
    text: str,
    fixed_images: tuple[FixedImage, ...],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    matches = list(IMAGE_LINE_RE.finditer(text))
    if len(matches) != len(fixed_images) or text.count("WORK_ABSENT=1") != 1:
        raise ContractError("inventory output shape is not exact")
    records: list[dict[str, Any]] = []
    for match, fixed in zip(matches, fixed_images, strict=True):
        item = match.groupdict()
        if (
            item["path"] != fixed.device_path
            or int(item["size"]) != IMAGE_SIZE
            or item["mode"] != IMAGE_MODE
            or int(item["nlink"]) != 1
            or item["sha"] != fixed.sha256
        ):
            raise ContractError(f"inventory identity mismatch for {fixed.role}")
        records.append(
            {
                "role": fixed.role,
                "device_path": fixed.device_path,
                "size": int(item["size"]),
                "blocks": int(item["blocks"]),
                "mode": item["mode"],
                "nlink": int(item["nlink"]),
                "st_dev": int(item["dev"]),
                "st_ino": int(item["ino"]),
                "sha256": item["sha"],
            }
        )
    df_matches = list(DF_LINE_RE.finditer(text))
    if len(df_matches) != 1:
        raise ContractError("inventory df output is not exact")
    df = {
        key: int(df_matches[0].group(key))
        for key in ("blocks", "used", "available")
    }
    return records, df


def capture_inventory(
    run_id: str,
    output: Path,
    selected_run_ids: list[str],
) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("cleanup run_id is not exact")
    expected_parent = (PRIVATE_BASE / run_id).resolve()
    expected_output = expected_parent / "inventory.json"
    if output.resolve() != expected_output or output.exists():
        raise ContractError("inventory output is not the new exact private run path")
    selection_sources = _selection_sources(selected_run_ids)
    fixed_images = tuple(item.fixed for item in selection_sources) + FIXED_PROTECTED
    realpath, serial_sha = _find_target()
    bridge = _require_bridge(realpath)
    health = _health()
    transcripts = [
        _bounded_inventory_read(
            _inventory_work_script(),
            READ_TIMEOUT_SEC,
            "SD work-path inventory",
        )
    ]
    for index, fixed in enumerate(fixed_images):
        item_text = _bounded_inventory_read(
            _inventory_image_script(index, fixed),
            HASH_TIMEOUT_SEC,
            f"SD image inventory {index}",
        )
        if item_text.count(f"A90CLEAN_INDEX|{index}") != 1:
            raise ContractError("inventory frame index is not exact")
        transcripts.append(item_text)
    transcripts.append(
        _bounded_inventory_read(
            _inventory_df_script(),
            READ_TIMEOUT_SEC,
            "SD filesystem inventory",
        )
    )
    text = "\n".join(transcripts)
    records, df = _parse_inventory(text, fixed_images)
    output.parent.mkdir(mode=0o700, parents=False, exist_ok=False)
    value = {
        "schema": INVENTORY_SCHEMA,
        "captured_utc": legacy.utc_now(),
        "captured_epoch_sec": int(time.time()),
        "run_id": run_id,
        "selected_run_ids": selected_run_ids,
        "target": {
            "profile": "galaxy-a90-5g-native-init",
            "bridge_device": str(BRIDGE_DEVICE),
            "bridge_realpath": realpath,
            "usb_serial_sha256": serial_sha,
            "bridge_process": bridge,
        },
        "health": health,
        "work_path": WORK_PATH,
        "work_absent": True,
        "images": records,
        "filesystem_kib": df,
        "device_contact": True,
        "device_write": False,
        "other_target_commands": 0,
    }
    legacy.write_private_json_exclusive(output, value)
    return value


def _load_inventory(
    path: Path,
    expected_sha256: str,
) -> tuple[legacy.BoundFile, dict[str, Any]]:
    bound = _bound(path, private=True)
    if bound.sha256 != _require_sha(expected_sha256, "inventory SHA256"):
        raise ContractError("inventory SHA256 mismatch")
    value = _require_dict(
        json.loads(bound.path.read_text(encoding="utf-8")),
        "inventory",
    )
    expected_keys = {
        "schema",
        "captured_utc",
        "captured_epoch_sec",
        "run_id",
        "selected_run_ids",
        "target",
        "health",
        "work_path",
        "work_absent",
        "images",
        "filesystem_kib",
        "device_contact",
        "device_write",
        "other_target_commands",
    }
    if (
        set(value) != expected_keys
        or value.get("schema") != INVENTORY_SCHEMA
        or value.get("run_id") is None
        or value.get("work_path") != WORK_PATH
        or value.get("work_absent") is not True
        or value.get("device_contact") is not True
        or value.get("device_write") is not False
        or type(value.get("other_target_commands")) is not int
        or value.get("other_target_commands") != 0
    ):
        raise ContractError("inventory contract is not exact")
    target = _require_dict(value.get("target"), "inventory target")
    health = _require_dict(value.get("health"), "inventory health")
    bridge_process = _validated_bridge_process(target.get("bridge_process"))
    if (
        set(target)
        != {
            "profile",
            "bridge_device",
            "bridge_realpath",
            "usb_serial_sha256",
            "bridge_process",
        }
        or set(health)
        != {
            "proven",
            "version",
            "build",
            "selftest_pass",
            "selftest_warn",
            "selftest_fail",
            "pstore_entries",
            "runtime_root",
        }
        or target.get("profile") != "galaxy-a90-5g-native-init"
        or target.get("bridge_device") != str(BRIDGE_DEVICE)
        or not isinstance(target.get("bridge_realpath"), str)
        or re.fullmatch(r"/dev/ttyACM[0-9]+", target["bridge_realpath"]) is None
        or target.get("bridge_process") != bridge_process
        or target.get("usb_serial_sha256") != USB_SERIAL_SHA256
        or health.get("proven") is not True
        or health.get("version") != EXPECTED_VERSION
        or health.get("build") != EXPECTED_BUILD
        or any(
            type(health.get(key)) is not int or health[key] < 0
            for key in (
                "selftest_pass",
                "selftest_warn",
                "selftest_fail",
                "pstore_entries",
            )
        )
        or health.get("selftest_fail") != 0
        or health.get("pstore_entries") != 0
    ):
        raise ContractError("inventory target or health is not exact")
    records = value.get("images")
    selected_run_ids = value.get("selected_run_ids")
    if not isinstance(selected_run_ids, list) or any(
        not isinstance(item, str) for item in selected_run_ids
    ):
        raise ContractError("inventory selected run IDs are not exact")
    selection_sources = _selection_sources(selected_run_ids)
    fixed_images = tuple(item.fixed for item in selection_sources) + FIXED_PROTECTED
    if not isinstance(records, list) or len(records) != len(fixed_images):
        raise ContractError("inventory images are not exact")
    for item, fixed in zip(records, fixed_images, strict=True):
        record = _require_dict(item, fixed.role)
        if (
            record.get("role") != fixed.role
            or record.get("device_path") != fixed.device_path
            or type(record.get("size")) is not int
            or record.get("size") != IMAGE_SIZE
            or record.get("mode") != IMAGE_MODE
            or type(record.get("nlink")) is not int
            or record.get("nlink") != 1
            or record.get("sha256") != fixed.sha256
            or type(record.get("blocks")) is not int
            or type(record.get("st_dev")) is not int
            or type(record.get("st_ino")) is not int
        ):
            raise ContractError(f"inventory record changed for {fixed.role}")
    filesystem = _require_dict(value.get("filesystem_kib"), "filesystem_kib")
    if set(filesystem) != {"blocks", "used", "available"} or any(
        type(filesystem.get(key)) is not int or filesystem[key] < 0
        for key in ("blocks", "used", "available")
    ):
        raise ContractError("inventory filesystem shape is not exact")
    return bound, value


def _load_recovery_spec() -> tuple[legacy.BoundFile, resident_d1.SessionSpec]:
    manifest = _bound(D1_MANIFEST, private=True)
    if manifest.sha256 != D1_MANIFEST_SHA256:
        raise ContractError("canonical D1 recovery manifest changed")
    recovery = resident_d1.load_spec(manifest.path, manifest.sha256)
    if (
        recovery.bridge_device != str(BRIDGE_DEVICE)
        or recovery.candidate_version != EXPECTED_VERSION
        or recovery.candidate_build != EXPECTED_BUILD
        or recovery.remote_final != FIXED_PROTECTED[-1].device_path
        or recovery.rootfs.sha256 != FIXED_PROTECTED[-1].sha256
        or recovery.recovery_profile != RECOVERY_PROFILE
        or recovery.rollback.size <= 0
        or not recovery.rollback.path.is_relative_to(PRIVATE_ROOT)
    ):
        raise ContractError("canonical D1 physical recovery binding changed")
    return manifest, recovery


def _load_restoration_evidence(
    selection_sources: tuple[SelectionSource, ...],
) -> tuple[tuple[legacy.BoundFile, legacy.BoundFile], ...]:
    return tuple(
        (item.prepared_manifest, item.staging_result)
        for item in selection_sources
    )


def build_manifest(
    *,
    run_id: str,
    inventory_path: Path,
    inventory_sha256: str,
    output: Path,
) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("cleanup run_id is not exact")
    inventory, value = _load_inventory(inventory_path, inventory_sha256)
    if value.get("run_id") != run_id:
        raise ContractError("inventory run_id differs")
    expected_parent = (PRIVATE_BASE / run_id).resolve()
    expected_output = expected_parent / "manifest.json"
    if output.resolve() != expected_output or output.exists():
        raise ContractError("manifest output is not the exact private run path")
    source_closure = {
        role: _bound(path, private=False)
        for role, path in _expected_source_paths().items()
    }
    selection_sources = _selection_sources(value["selected_run_ids"])
    recovery_manifest, recovery = _load_recovery_spec()
    restoration_evidence = _load_restoration_evidence(selection_sources)
    if recovery.bridge_realpath != value["target"]["bridge_realpath"]:
        raise ContractError("fresh target differs from canonical recovery binding")
    f1_result = _bound(F1_RESULT, private=True)
    d1_result = _bound(D1_RESULT, private=True)
    display = _bound(DISPLAY_CONFIRMATION, private=True)
    f1_value = json.loads(f1_result.path.read_text(encoding="utf-8"))
    d1_value = json.loads(d1_result.path.read_text(encoding="utf-8"))
    display_value = json.loads(display.path.read_text(encoding="utf-8"))
    if (
        f1_value.get("status") != "PASS_A90_RESIDENT_INSTALLED"
        or f1_value.get("device_safety_state") != "RESIDENT_HEALTHY"
        or type(f1_value.get("candidate_transfer_count")) is not int
        or f1_value.get("candidate_transfer_count") != 1
        or type(f1_value.get("rollback_transfer_count")) is not int
        or f1_value.get("rollback_transfer_count") != 0
        or type(d1_value.get("handoff_dispatch_count")) is not int
        or d1_value.get("handoff_dispatch_count") != 1
        or d1_value.get("resident_healthy") is not True
        or d1_value.get("payload_transfer") is not False
        or d1_value.get("partition_write") is not False
        or d1_value.get("flash") is not False
        or display_value.get("visible_confirmed") != "yes"
        or display_value.get("display_visibility_proved") is not True
    ):
        raise ContractError("resident health provenance is not exact")
    inventory_records = value["images"]
    images: list[dict[str, Any]] = []
    selected_count = len(selection_sources)
    fixed_images = tuple(item.fixed for item in selection_sources) + FIXED_PROTECTED
    for index, (item, fixed) in enumerate(
        zip(inventory_records, fixed_images, strict=True)
    ):
        record = dict(item)
        if index < selected_count:
            host = _bound(selection_sources[index].host_path, private=True)
            if host.size != IMAGE_SIZE or host.sha256 != fixed.sha256:
                raise ContractError(f"host preservation changed for {fixed.role}")
            record["host_preservation"] = _as_bound(host)
        images.append(record)
    manifest = {
        "schema": SCHEMA,
        "status": STATUS,
        "created_utc": legacy.utc_now(),
        "run_id": run_id,
        "selected_run_ids": value["selected_run_ids"],
        "capability": CAPABILITY,
        "inventory": _as_bound(inventory),
        "target": {
            "profile": "galaxy-a90-5g-native-init",
            "bridge_device": str(BRIDGE_DEVICE),
            "bridge_realpath": value["target"]["bridge_realpath"],
            "bridge_process": value["target"]["bridge_process"],
            "usb_serial_sha256": USB_SERIAL_SHA256,
            "expected_version": EXPECTED_VERSION,
            "expected_build": EXPECTED_BUILD,
        },
        "selected": images[:selected_count],
        "protected": images[selected_count:],
        "work_path": WORK_PATH,
        "source_closure": {
            role: _as_bound(bound) for role, bound in source_closure.items()
        },
        "resident_evidence": {
            "f1_result": _as_bound(f1_result),
            "d1_result": _as_bound(d1_result),
            "display_confirmation": _as_bound(display),
        },
        "recovery": {
            "resident_d1_manifest": _as_bound(recovery_manifest),
            "rollback_boot": _as_bound(
                legacy.BoundFile(
                    recovery.rollback.path,
                    recovery.rollback.size,
                    recovery.rollback.sha256,
                )
            ),
            "profile": recovery.recovery_profile,
            "recovery_serial_sha256": recovery.recovery_serial_sha256,
            "observer_device": recovery.observer_device,
            "restoration_evidence": [
                {
                    "prepared_manifest": _as_bound(manifest_bound),
                    "staging_result": _as_bound(result_bound),
                }
                for manifest_bound, result_bound in restoration_evidence
            ],
            "restore_transaction": {
                "separate_after_cleanup_dispatch": True,
                "automatic_restore": False,
                "restore_retry_forbidden": True,
                "publication": "hardlink-no-clobber",
                "exact_destinations": [
                    item.fixed.device_path for item in selection_sources
                ],
            },
        },
        "authority": {
            "risk_tier": "TIER_D1_ATTENDED_EXACT_STORAGE_ARTIFACT_CLEANUP",
            "operator_attended_required": True,
            "selected_count": selected_count,
            "unlink_dispatch_count_max": 1,
            "unlink_retry_forbidden": True,
            "exact_restore_preauthorized_after_unlink_dispatch": True,
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
        },
    }
    legacy.write_private_json_exclusive(output, manifest)
    return manifest


def _record_from_manifest(
    value: Any,
    fixed: FixedImage,
    *,
    selected: bool,
) -> ImageRecord:
    item = _require_dict(value, fixed.role)
    expected_keys = {
        "role",
        "device_path",
        "size",
        "blocks",
        "mode",
        "nlink",
        "st_dev",
        "st_ino",
        "sha256",
    } | ({"host_preservation"} if selected else set())
    if set(item) != expected_keys:
        raise ContractError(f"{fixed.role} manifest shape is not exact")
    if (
        item.get("role") != fixed.role
        or item.get("device_path") != fixed.device_path
        or type(item.get("size")) is not int
        or item.get("size") != IMAGE_SIZE
        or item.get("mode") != IMAGE_MODE
        or type(item.get("nlink")) is not int
        or item.get("nlink") != 1
        or item.get("sha256") != fixed.sha256
    ):
        raise ContractError(f"{fixed.role} identity is not exact")
    blocks = _require_int(item.get("blocks"), f"{fixed.role}.blocks", minimum=1)
    st_dev = _require_int(item.get("st_dev"), f"{fixed.role}.st_dev", minimum=1)
    st_ino = _require_int(item.get("st_ino"), f"{fixed.role}.st_ino", minimum=1)
    host = (
        _load_bound(item.get("host_preservation"), fixed.role, private=True)
        if selected
        else None
    )
    if host is not None and (host.size != IMAGE_SIZE or host.sha256 != fixed.sha256):
        raise ContractError(f"{fixed.role} host preservation changed")
    return ImageRecord(
        role=fixed.role,
        device_path=fixed.device_path,
        size=IMAGE_SIZE,
        blocks=blocks,
        mode=IMAGE_MODE,
        nlink=1,
        st_dev=st_dev,
        st_ino=st_ino,
        sha256=fixed.sha256,
        host_preservation=host,
    )


def load_manifest(path: Path, expected_sha256: str) -> CleanupSpec:
    manifest = _bound(path, private=True)
    if manifest.sha256 != _require_sha(expected_sha256, "manifest SHA256"):
        raise ContractError("manifest SHA256 mismatch")
    value = _require_dict(
        json.loads(manifest.path.read_text(encoding="utf-8")),
        "manifest",
    )
    run_id = _require_string(value.get("run_id"), "run_id")
    if (
        set(value)
        != {
            "schema",
            "status",
            "created_utc",
            "run_id",
            "selected_run_ids",
            "capability",
            "inventory",
            "target",
            "selected",
            "protected",
            "work_path",
            "source_closure",
            "resident_evidence",
            "recovery",
            "authority",
        }
        or value.get("schema") != SCHEMA
        or value.get("status") != STATUS
        or value.get("capability") != CAPABILITY
        or RUN_ID_RE.fullmatch(run_id) is None
        or manifest.path != (PRIVATE_BASE / run_id / "manifest.json").resolve()
        or value.get("work_path") != WORK_PATH
    ):
        raise ContractError("manifest header is not exact")
    inventory = _load_bound(value.get("inventory"), "inventory", private=True)
    if inventory.path != (PRIVATE_BASE / run_id / "inventory.json").resolve():
        raise ContractError("manifest inventory path changed")
    inventory, inventory_value = _load_inventory(
        inventory.path,
        inventory.sha256,
    )
    captured = _require_int(
        inventory_value.get("captured_epoch_sec"),
        "inventory captured_epoch_sec",
        minimum=1,
    )
    if inventory_value.get("run_id") != run_id:
        raise ContractError("manifest inventory run_id changed")
    if captured > int(time.time()) + 5:
        raise ContractError("inventory timestamp is from the future")
    target = _require_dict(value.get("target"), "target")
    if (
        set(target)
        != {
            "profile",
            "bridge_device",
            "bridge_realpath",
            "bridge_process",
            "usb_serial_sha256",
            "expected_version",
            "expected_build",
        }
        or target.get("profile") != "galaxy-a90-5g-native-init"
        or target.get("bridge_device") != str(BRIDGE_DEVICE)
        or target.get("bridge_realpath")
        != inventory_value["target"]["bridge_realpath"]
        or target.get("bridge_process")
        != inventory_value["target"]["bridge_process"]
        or target.get("usb_serial_sha256") != USB_SERIAL_SHA256
        or target.get("expected_version") != EXPECTED_VERSION
        or target.get("expected_build") != EXPECTED_BUILD
    ):
        raise ContractError("manifest target changed")
    selected_values = value.get("selected")
    protected_values = value.get("protected")
    selected_run_ids_value = value.get("selected_run_ids")
    if (
        not isinstance(selected_run_ids_value, list)
        or any(not isinstance(item, str) for item in selected_run_ids_value)
        or selected_run_ids_value != inventory_value.get("selected_run_ids")
        or not isinstance(selected_values, list)
        or not isinstance(protected_values, list)
        or len(selected_values) != len(selected_run_ids_value)
        or len(protected_values) != 2
    ):
        raise ContractError("manifest selected/protected set is not exact")
    selection_sources = _selection_sources(selected_run_ids_value)
    selected = tuple(
        _record_from_manifest(item, fixed, selected=True)
        for item, fixed in zip(
            selected_values,
            (source.fixed for source in selection_sources),
            strict=True,
        )
    )
    protected = tuple(
        _record_from_manifest(item, fixed, selected=False)
        for item, fixed in zip(protected_values, FIXED_PROTECTED, strict=True)
    )
    if len({(item.st_dev, item.st_ino) for item in selected + protected}) != (
        len(selected) + len(protected)
    ):
        raise ContractError("selected/protected inode identities overlap")
    inventory_images = inventory_value.get("images")
    manifest_inventory_projection = [
        {key: item[key] for key in item if key != "host_preservation"}
        for item in selected_values + protected_values
    ]
    if (
        not isinstance(inventory_images, list)
        or inventory_images != manifest_inventory_projection
    ):
        raise ContractError("manifest images differ from the exact inventory")
    source_values = _require_dict(value.get("source_closure"), "source_closure")
    expected_sources = _expected_source_paths()
    if set(source_values) != set(expected_sources):
        raise ContractError("source closure roles are not exact")
    source_closure = {
        role: _load_bound(source_values[role], role, private=False)
        for role in sorted(expected_sources)
    }
    if any(
        source_closure[role].path != expected_sources[role]
        for role in expected_sources
    ):
        raise ContractError("source closure path changed")
    evidence = _require_dict(value.get("resident_evidence"), "resident_evidence")
    if set(evidence) != {"f1_result", "d1_result", "display_confirmation"}:
        raise ContractError("resident evidence roles are not exact")
    f1_result = _load_bound(evidence["f1_result"], "f1_result", private=True)
    d1_result = _load_bound(evidence["d1_result"], "d1_result", private=True)
    display = _load_bound(
        evidence["display_confirmation"],
        "display_confirmation",
        private=True,
    )
    if (
        f1_result.path != F1_RESULT.resolve(strict=True)
        or d1_result.path != D1_RESULT.resolve(strict=True)
        or display.path != DISPLAY_CONFIRMATION.resolve(strict=True)
    ):
        raise ContractError("resident evidence path changed")
    f1_value = json.loads(f1_result.path.read_text(encoding="utf-8"))
    d1_value = json.loads(d1_result.path.read_text(encoding="utf-8"))
    display_value = json.loads(display.path.read_text(encoding="utf-8"))
    if (
        f1_value.get("status") != "PASS_A90_RESIDENT_INSTALLED"
        or f1_value.get("device_safety_state") != "RESIDENT_HEALTHY"
        or type(f1_value.get("candidate_transfer_count")) is not int
        or f1_value.get("candidate_transfer_count") != 1
        or type(f1_value.get("rollback_transfer_count")) is not int
        or f1_value.get("rollback_transfer_count") != 0
        or type(d1_value.get("handoff_dispatch_count")) is not int
        or d1_value.get("handoff_dispatch_count") != 1
        or d1_value.get("resident_healthy") is not True
        or d1_value.get("payload_transfer") is not False
        or d1_value.get("partition_write") is not False
        or d1_value.get("flash") is not False
        or display_value.get("visible_confirmed") != "yes"
        or display_value.get("display_visibility_proved") is not True
    ):
        raise ContractError("resident evidence semantics changed")
    recovery_value = _require_dict(value.get("recovery"), "recovery")
    if set(recovery_value) != {
        "resident_d1_manifest",
        "rollback_boot",
        "profile",
        "recovery_serial_sha256",
        "observer_device",
        "restoration_evidence",
        "restore_transaction",
    }:
        raise ContractError("recovery binding shape changed")
    recovery_manifest = _load_bound(
        recovery_value.get("resident_d1_manifest"),
        "resident D1 recovery manifest",
        private=True,
    )
    recovery_rollback = _load_bound(
        recovery_value.get("rollback_boot"),
        "recovery rollback boot",
        private=True,
    )
    canonical_recovery_manifest, canonical_recovery = _load_recovery_spec()
    if (
        recovery_manifest != canonical_recovery_manifest
        or recovery_rollback.path != canonical_recovery.rollback.path
        or recovery_rollback.size != canonical_recovery.rollback.size
        or recovery_rollback.sha256 != canonical_recovery.rollback.sha256
        or recovery_value.get("profile") != canonical_recovery.recovery_profile
        or recovery_value.get("recovery_serial_sha256")
        != canonical_recovery.recovery_serial_sha256
        or recovery_value.get("observer_device")
        != canonical_recovery.observer_device
        or canonical_recovery.bridge_realpath != target["bridge_realpath"]
    ):
        raise ContractError("physical recovery binding changed")
    restoration_values = recovery_value.get("restoration_evidence")
    canonical_restoration = _load_restoration_evidence(selection_sources)
    if (
        not isinstance(restoration_values, list)
        or len(restoration_values) != len(selection_sources)
    ):
        raise ContractError("restoration evidence set changed")
    restoration_loaded: list[tuple[legacy.BoundFile, legacy.BoundFile]] = []
    for index, (item, canonical) in enumerate(
        zip(restoration_values, canonical_restoration, strict=True)
    ):
        record = _require_dict(item, f"restoration evidence {index}")
        if set(record) != {"prepared_manifest", "staging_result"}:
            raise ContractError("restoration evidence shape changed")
        pair = (
            _load_bound(
                record["prepared_manifest"],
                f"restoration manifest {index}",
                private=True,
            ),
            _load_bound(
                record["staging_result"],
                f"restoration result {index}",
                private=True,
            ),
        )
        if pair != canonical:
            raise ContractError("restoration evidence identity changed")
        restoration_loaded.append(pair)
    restore_transaction = _require_dict(
        recovery_value.get("restore_transaction"),
        "restore transaction",
    )
    if (
        set(restore_transaction)
        != {
            "separate_after_cleanup_dispatch",
            "automatic_restore",
            "restore_retry_forbidden",
            "publication",
            "exact_destinations",
        }
        or restore_transaction.get("separate_after_cleanup_dispatch") is not True
        or restore_transaction.get("automatic_restore") is not False
        or restore_transaction.get("restore_retry_forbidden") is not True
        or restore_transaction.get("publication") != "hardlink-no-clobber"
        or restore_transaction.get("exact_destinations")
        != [item.device_path for item in selected]
    ):
        raise ContractError("restore transaction contract changed")
    authority = _require_dict(value.get("authority"), "authority")
    if (
        set(authority)
        != {
            "risk_tier",
            "operator_attended_required",
            "selected_count",
            "unlink_dispatch_count_max",
            "unlink_retry_forbidden",
            "exact_restore_preauthorized_after_unlink_dispatch",
            "payload_transfer",
            "partition_write",
            "flash",
        }
        or authority.get("risk_tier")
        != "TIER_D1_ATTENDED_EXACT_STORAGE_ARTIFACT_CLEANUP"
        or authority.get("operator_attended_required") is not True
        or type(authority.get("selected_count")) is not int
        or authority.get("selected_count") != len(selected)
        or type(authority.get("unlink_dispatch_count_max")) is not int
        or authority.get("unlink_dispatch_count_max") != 1
        or authority.get("unlink_retry_forbidden") is not True
        or authority.get("exact_restore_preauthorized_after_unlink_dispatch")
        is not True
        or authority.get("payload_transfer") is not False
        or authority.get("partition_write") is not False
        or authority.get("flash") is not False
    ):
        raise ContractError("manifest authority changed")
    return CleanupSpec(
        manifest_path=manifest.path,
        manifest_sha256=manifest.sha256,
        run_id=run_id,
        selected_run_ids=tuple(selected_run_ids_value),
        inventory=inventory,
        bridge_realpath=target["bridge_realpath"],
        bridge_process=_validated_bridge_process(target["bridge_process"]),
        selected=selected,  # type: ignore[arg-type]
        protected=protected,  # type: ignore[arg-type]
        source_closure=source_closure,
        f1_result=f1_result,
        d1_result=d1_result,
        display_confirmation=display,
        recovery_manifest=recovery_manifest,
        recovery_rollback=recovery_rollback,
        recovery_profile=canonical_recovery.recovery_profile,
        recovery_serial_sha256=canonical_recovery.recovery_serial_sha256,
        recovery_observer_device=canonical_recovery.observer_device,
        restoration_evidence=tuple(restoration_loaded),  # type: ignore[arg-type]
    )


def _approval_binding(spec: CleanupSpec) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "selected_run_ids": list(spec.selected_run_ids),
        "capability": CAPABILITY,
        "manifest_sha256": spec.manifest_sha256,
        "inventory_sha256": spec.inventory.sha256,
        "bridge_process": spec.bridge_process,
        "runner_sha256": spec.source_closure["runner"].sha256,
        "transport_sha256": spec.source_closure["transport"].sha256,
        "source_closure": {
            role: item.sha256
            for role, item in sorted(spec.source_closure.items())
        },
        "resident_evidence": {
            "f1_result_sha256": spec.f1_result.sha256,
            "d1_result_sha256": spec.d1_result.sha256,
            "display_confirmation_sha256": spec.display_confirmation.sha256,
        },
        "recovery": {
            "resident_d1_manifest_sha256": spec.recovery_manifest.sha256,
            "rollback_boot_sha256": spec.recovery_rollback.sha256,
            "recovery_profile": spec.recovery_profile,
            "recovery_serial_sha256": spec.recovery_serial_sha256,
            "restoration_evidence_sha256": [
                [manifest.sha256, result.sha256]
                for manifest, result in spec.restoration_evidence
            ],
            "exact_restore_preauthorized_after_unlink_dispatch": True,
        },
        "selected": [
            {
                "role": item.role,
                "device_path": item.device_path,
                "sha256": item.sha256,
                "st_dev": item.st_dev,
                "st_ino": item.st_ino,
                "host_preservation_sha256": item.host_preservation.sha256,
            }
            for item in spec.selected
            if item.host_preservation is not None
        ],
        "protected": [
            {
                "role": item.role,
                "device_path": item.device_path,
                "sha256": item.sha256,
                "st_dev": item.st_dev,
                "st_ino": item.st_ino,
            }
            for item in spec.protected
        ],
        "single_unlink_dispatch": True,
        "unlink_retry_forbidden": True,
        "operator_attended": True,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
    }


def approval_path(spec: CleanupSpec) -> Path:
    return (PRIVATE_BASE / spec.run_id / "approval-prepared.json").resolve()


def prepare_approval(spec: CleanupSpec) -> dict[str, Any]:
    for item in spec.selected:
        if item.host_preservation is None:
            raise ContractError("selected image lacks host preservation")
        digest, state = legacy.hash_open_regular(item.host_preservation.path)
        if state.st_size != IMAGE_SIZE or digest != item.sha256:
            raise ContractError("host preservation changed before approval")
    binding = _approval_binding(spec)
    binding_sha = legacy.json_sha256(binding)
    value = {
        "schema": APPROVAL_SCHEMA,
        "created_utc": legacy.utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "approval_binding": binding,
        "approval_binding_sha256": binding_sha,
        "approval_token": APPROVAL_PREFIX + binding_sha,
        "device_contact": False,
        "device_write": False,
        "live_authority": False,
    }
    legacy.write_private_json_exclusive(approval_path(spec), value)
    return value


def _consume_approval(spec: CleanupSpec, supplied: str) -> dict[str, Any]:
    path = approval_path(spec)
    value = json.loads(_require_private(path).read_text(encoding="utf-8"))
    binding = _approval_binding(spec)
    binding_sha = legacy.json_sha256(binding)
    if (
        value.get("schema") != APPROVAL_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("manifest_sha256") != spec.manifest_sha256
        or value.get("approval_binding") != binding
        or value.get("approval_binding_sha256") != binding_sha
        or value.get("approval_token") != APPROVAL_PREFIX + binding_sha
        or supplied != APPROVAL_PREFIX + binding_sha
        or value.get("device_contact") is not False
        or value.get("device_write") is not False
    ):
        raise ContractError("exact cleanup approval mismatch")
    return value


def _revalidate_source_closure(spec: CleanupSpec) -> None:
    expected = _expected_source_paths()
    if set(spec.source_closure) != set(expected):
        raise ContractError("live source closure roles changed")
    for role, path in expected.items():
        current = _bound(path, private=False)
        if current != spec.source_closure[role]:
            raise ContractError(f"live source closure changed: {role}")


def _restore_stage_spec(spec: CleanupSpec, index: int) -> staging.StageSpec:
    if type(index) is not int or not 0 <= index < len(spec.selected):
        raise ContractError("restore index is not exact")
    selected = spec.selected[index]
    if selected.host_preservation is None:
        raise ContractError("restore source is not preserved")
    stage_dir = (
        f"/mnt/sdext/a90/runtime/.a90-cleanup-restore-{spec.run_id}-{index}"
    )
    return staging.StageSpec(
        run_id=spec.run_id,
        manifest_path=spec.manifest_path,
        manifest_sha256=spec.manifest_sha256,
        local_image=selected.host_preservation.path,
        local_size=selected.size,
        local_sha256=selected.sha256,
        remote_final=selected.device_path,
        remote_work=WORK_PATH,
        remote_stage_dir=stage_dir,
        remote_payload=f"{stage_dir}/payload.img",
        bridge_device=str(BRIDGE_DEVICE),
        bridge_realpath=spec.bridge_realpath,
        observer_device=spec.recovery_observer_device,
        adapter_size=spec.source_closure["restoration_staging"].size,
        adapter_sha256=spec.source_closure["restoration_staging"].sha256,
        tcpctl_host=spec.source_closure["restoration_tcpctl_host"].path,
        tcpctl_host_size=spec.source_closure["restoration_tcpctl_host"].size,
        tcpctl_host_sha256=spec.source_closure["restoration_tcpctl_host"].sha256,
        bound_files=(),
        rootfs_profile="A90_EXACT_OBSOLETE_ROOTFS_RESTORE_V1",
        starting_version=EXPECTED_VERSION,
        starting_build=EXPECTED_BUILD,
    )


def _revalidate_recovery_availability(
    spec: CleanupSpec,
) -> dict[str, Any]:
    _revalidate_recovery_binding(spec)
    selection_sources = _selection_sources(list(spec.selected_run_ids))
    if _load_restoration_evidence(selection_sources) != spec.restoration_evidence:
        raise ContractError("live restoration demonstration changed")
    for index, selected in enumerate(spec.selected):
        if selected.host_preservation is None:
            raise ContractError("live restoration source is absent")
        digest, state = legacy.hash_open_regular(selected.host_preservation.path)
        if state.st_size != IMAGE_SIZE or digest != selected.sha256:
            raise ContractError("live restoration source changed")
        restore = _restore_stage_spec(spec, index)
        for script in (
            staging.remote_readonly_preflight_script(restore),
            staging.remote_reserve_script(restore),
            staging.remote_verify_payload_script(restore),
            staging.remote_publish_script(restore),
        ):
            if selected.device_path not in script or selected.sha256 not in script:
                raise ContractError("exact restoration script binding changed")
            _require_bounded_command(
                _script_command(script),
                f"restore {index} command",
            )
    host_ncm = staging.require_host_ncm_ready(
        spec.recovery_observer_device,
        spec.bridge_realpath,
    )
    if host_ncm != {
        "verified_a90_ncm": True,
        "direct_route": True,
        "host_cidr_present": True,
        "device_ping": True,
    }:
        raise ContractError("exact A90 restoration NCM is unavailable")
    return {
        "physical_recovery_profile": spec.recovery_profile,
        "rollback_boot_sha256": spec.recovery_rollback.sha256,
        "restoration_demonstrations": len(spec.selected),
        "host_ncm": host_ncm,
        "automatic_restore": False,
        "separate_restore_transaction": True,
    }


def _revalidate_recovery_binding(spec: CleanupSpec) -> None:
    manifest, recovery = _load_recovery_spec()
    if (
        manifest != spec.recovery_manifest
        or recovery.rollback.path != spec.recovery_rollback.path
        or recovery.rollback.size != spec.recovery_rollback.size
        or recovery.rollback.sha256 != spec.recovery_rollback.sha256
        or recovery.recovery_profile != spec.recovery_profile
        or recovery.recovery_serial_sha256 != spec.recovery_serial_sha256
        or recovery.observer_device != spec.recovery_observer_device
        or recovery.bridge_realpath != spec.bridge_realpath
    ):
        raise ContractError("live physical recovery binding changed")


def _inventory_age(spec: CleanupSpec) -> int:
    value = json.loads(spec.inventory.path.read_text(encoding="utf-8"))
    age = int(time.time()) - value["captured_epoch_sec"]
    if age < -5 or age > MAX_INVENTORY_AGE_SEC:
        raise ContractError("cleanup inventory is stale")
    return age


def _revalidate_dispatch_window(
    spec: CleanupSpec,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    _inventory_age(spec)
    realpath, serial_sha = _find_target()
    if realpath != spec.bridge_realpath or serial_sha != USB_SERIAL_SHA256:
        raise ContractError("dispatch target differs from the manifest")
    bridge = _require_bridge(realpath)
    if bridge != spec.bridge_process:
        raise ContractError("dispatch bridge generation differs")
    _revalidate_source_closure(spec)
    _revalidate_recovery_binding(spec)
    health = _health()
    return realpath, bridge, health


def _preflight_filesystem_script(spec: CleanupSpec) -> str:
    return "\n".join(
        (
            "set -eu",
            f"W={shlex.quote(WORK_PATH)}",
            '[ ! -e "$W" ]',
            '[ ! -L "$W" ]',
            "for x in /mnt/sdext/a90/runtime/.a90-stage-* "
            "/mnt/sdext/a90/runtime/.a90-d1-stage-* "
            "/mnt/sdext/a90/runtime/.a90-cleanup-restore-*; do "
            '[ ! -e "$x" ] && [ ! -L "$x" ] || exit 60; done',
            "set -- $(/bin/busybox df -k /mnt/sdext | "
            "/bin/busybox tail -n 1)",
            f'echo "A90CLEAN_PREFLIGHT exact=1 selected={len(spec.selected)} '
            f'protected={len(spec.protected)} work_absent=1 blocks=$2 used=$3 '
            'available=$4"',
        )
    )


def _image_exact_script() -> str:
    return "\n".join(
        (
            "set -eu",
            "p=$1; e=$2; h=$3; t=$4",
            '[ ! -L "$p" ]',
            '[ -f "$p" ]',
            '[ "$(/bin/busybox stat -c "%F|%s|%a|%h|%d|%i" "$p")" = "$e" ]',
            's=$(/bin/busybox sha256sum "$p")',
            's=${s%% *}',
            '[ "$s" = "$h" ]',
            'echo "A90CLEAN_IMAGE_EXACT tag=$t"',
        )
    )


def _image_exact_args(item: ImageRecord, tag: str) -> tuple[str, ...]:
    return (
        item.device_path,
        (
            f"regular file|{IMAGE_SIZE}|{IMAGE_MODE}|1|"
            f"{item.st_dev}|{item.st_ino}"
        ),
        item.sha256,
        tag,
    )


def _read_exact_image(item: ImageRecord, tag: str) -> None:
    text = _run_script(
        _image_exact_script(),
        HASH_TIMEOUT_SEC,
        f"{tag} exact image",
        args=_image_exact_args(item, tag),
    )
    if text.count(f"A90CLEAN_IMAGE_EXACT tag={tag}") != 1:
        raise ContractError(f"{tag} exact image marker is not exact")


def _selected_use_guard_scripts(
    item: ImageRecord,
    tag: str,
    *,
    proc_root: str = "/proc",
    sys_root: str = "/sys",
    sd_mount: str = "/mnt/sdext",
) -> tuple[str, ...]:
    path = shlex.quote(item.device_path)
    proc = shlex.quote(proc_root)
    sys_block = shlex.quote(sys_root)
    mount = shlex.quote(sd_mount)
    mount_script = "\n".join(
        (
            "set -eu",
            f"PROC={proc}; SDMOUNT={mount}; P={path}; DEV={item.st_dev}",
            "SDROOT=$(/bin/busybox awk -v m=\"$SDMOUNT\" "
            "'$5==m{n++;r=$4}END{if(n!=1)exit 1;print r}' "
            '"$PROC/self/mountinfo")',
            '[ -n "$SDROOT" ]',
            "A=$(( (DEV >> 8) & 4095 )); "
            "B=$(( (DEV & 255) | ((DEV >> 12) & 1048320) ))",
            'D="$A:$B"; R=${P#"$SDMOUNT"}; [ "$R" != "$P" ]; R="${SDROOT%/}$R"',
            'for F in "$PROC"/[0-9]*/mountinfo; do [ -r "$F" ] || continue',
            "  /bin/busybox awk -v d=\"$D\" -v r=\"$R\" -v b=\"$SDROOT\" "
            "-v m=\"$SDMOUNT\" -v p=\"$P\" '",
            "  $3==d{c=($4==r||($4==\"/\"?substr(r,1,1)==\"/\":"
            "index(r,$4\"/\")==1));k=($4==b&&$5==m);"
            "if(($5==p||c)&&!k)x=1}END{exit(x?1:0)}' \"$F\" || exit 62",
            "done",
            f'echo "A90CLEAN_USE_MOUNT tag={tag} exact=1"',
        )
    )
    fd_script = "\n".join(
        (
            "set -eu",
            f"PROC={proc}; DEV={item.st_dev}; INO={item.st_ino}",
            'for F in "$PROC"/[0-9]*/fd/*; do',
            '  [ -e "$F" ] || [ -L "$F" ] || continue',
            '  M=$(/bin/busybox stat -L -c "%d|%i" "$F" 2>/dev/null) || continue',
            '  [ "$M" != "$DEV|$INO" ] || exit 63',
            "done",
            f'echo "A90CLEAN_USE_FD tag={tag} exact=1"',
        )
    )
    loop_script = "\n".join(
        (
            "set -eu",
            f"SYS={sys_block}; P={path}; DEV={item.st_dev}; INO={item.st_ino}",
            'for F in "$SYS"/block/loop*/loop/backing_file; do',
            '  [ -r "$F" ] || continue; B=$(/bin/busybox cat "$F")',
            '  case "$B" in /*) ;; *) B="/$B";; esac',
            '  [ "$B" != "$P" ] || exit 64',
            '  if [ -e "$B" ] || [ -L "$B" ]; then',
            '    M=$(/bin/busybox stat -L -c "%d|%i" "$B" 2>/dev/null) || true',
            '    [ "$M" != "$DEV|$INO" ] || exit 64',
            "  fi",
            "done",
            f'echo "A90CLEAN_USE_LOOP tag={tag} exact=1"',
        )
    )
    root_script = "\n".join(
        (
            "set -eu",
            f"PROC={proc}; SYS={sys_block}; P={path}",
            'for R in "$PROC"/[0-9]*/root; do',
            '  [ -e "$R" ] || [ -L "$R" ] || continue',
            '  D=$(/bin/busybox stat -L -c "%d" "$R" 2>/dev/null) || continue',
            '  A=$(( (D >> 8) & 4095 )); B=$(( (D & 255) | ((D >> 12) & 1048320) ))',
            '  N="$A:$B"; for L in "$SYS"/block/loop*/dev; do',
            '    [ -r "$L" ] || continue',
            '    [ "$(/bin/busybox cat "$L")" != "$N" ] || {',
            '      F=${L%/dev}/loop/backing_file; [ -r "$F" ] || exit 65',
            '      Q=$(/bin/busybox cat "$F"); case "$Q" in /*) ;; *) Q="/$Q";; esac',
            '      [ "$Q" != "$P" ] || exit 65',
            "    }",
            "  done",
            "done",
            f'echo "A90CLEAN_USE_ROOT tag={tag} exact=1"',
        )
    )
    return mount_script, fd_script, loop_script, root_script


def _read_cleanup_preflight(spec: CleanupSpec) -> dict[str, int]:
    text = _run_script(
        _preflight_filesystem_script(spec),
        READ_TIMEOUT_SEC,
        "cleanup filesystem preflight",
    )
    before = _parse_preflight(text, spec)
    for prefix, records in (("selected", spec.selected), ("protected", spec.protected)):
        for index, item in enumerate(records):
            _read_exact_image(item, f"{prefix}-{index}")
    for index, item in enumerate(spec.selected):
        tag = f"selected-{index}"
        for kind, script in zip(
            ("MOUNT", "FD", "LOOP", "ROOT"),
            _selected_use_guard_scripts(item, tag),
            strict=True,
        ):
            output = _run_script(
                script,
                READ_TIMEOUT_SEC,
                f"{tag} {kind.lower()} use guard",
            )
            if output.count(f"A90CLEAN_USE_{kind} tag={tag} exact=1") != 1:
                raise ContractError(f"{tag} {kind.lower()} use marker is not exact")
    return before


def _parse_preflight(text: str, spec: CleanupSpec) -> dict[str, int]:
    matches = re.findall(
        r"^A90CLEAN_PREFLIGHT exact=1 selected=([0-9]+) "
        r"protected=([0-9]+) work_absent=1 blocks=([0-9]+) "
        r"used=([0-9]+) available=([0-9]+)\r?$",
        text,
        re.MULTILINE,
    )
    if len(matches) != 1:
        raise ContractError("cleanup preflight marker is not exact")
    selected_count, protected_count, blocks, used, available = matches[0]
    if (
        int(selected_count) != len(spec.selected)
        or int(protected_count) != len(spec.protected)
    ):
        raise ContractError("cleanup preflight counts are not exact")
    return {
        "blocks": int(blocks),
        "used": int(used),
        "available": int(available),
    }


def _free_gain_bounds(spec: CleanupSpec) -> tuple[int, int]:
    allocated_kib = sum(item.blocks for item in spec.selected) // 2
    return (
        max(1, allocated_kib - FREE_GAIN_TOLERANCE_KIB),
        allocated_kib + FREE_GAIN_TOLERANCE_KIB,
    )


def _cleanup_script(spec: CleanupSpec) -> str:
    return "\n".join(
        (
            "set -eu",
            f"W={shlex.quote(WORK_PATH)}; D=$1; X=$2; shift 2",
            '[ ! -e "$W" ]; [ ! -L "$W" ]',
            "for x in /mnt/sdext/a90/runtime/.a90-stage-* "
            "/mnt/sdext/a90/runtime/.a90-d1-stage-* "
            "/mnt/sdext/a90/runtime/.a90-cleanup-restore-*; do "
            '[ ! -e "$x" ] && [ ! -L "$x" ] || exit 60; done',
            'while [ -n "$X" ]; do',
            '  case "$X" in *,*) R=${X%%,*}; X=${X#*,};; *) R=$X; X=;; esac',
            '  K=${R%%:*}; R=${R#*:}; S=${R%%:*}; I=${R#*:}',
            '  case "$K" in 3|4|5) '
            'B=debian-bookworm-arm64-d3-sysvinit-v340$K-keyed;; '
            '6) B=debian-bookworm-arm64-phase2-display-v3406-keyed;; '
            '*) exit 66;; esac',
            '  [ -z "$S" ] || B=$B-$S; '
            'p=/mnt/sdext/a90/runtime/$B.img',
            '  [ ! -L "$p" ]; [ -f "$p" ]',
            f'  [ "$(/bin/busybox stat -c "%s|%a|%h|%d|%i" "$p")" = '
            f'"{IMAGE_SIZE}|{IMAGE_MODE}|1|$D|$I" ]',
            '  set -- "$@" "$p"',
            "done",
            f'[ "$#" -gt 0 ]; [ "$#" -le {MAX_SELECTED} ]',
            '/bin/busybox rm -- "$@"',
            "/bin/busybox sync",
            'for p do [ ! -e "$p" ] && [ ! -L "$p" ]; done',
            'echo "A90CLEAN_UNLINKED exact=1 selected_absent=$#"',
        )
    )


def _cleanup_selector(item: ImageRecord) -> str:
    prefix = "/mnt/sdext/a90/runtime/"
    if not item.device_path.startswith(prefix) or item.st_ino > 4294967295:
        raise ContractError("cleanup selector input is outside exact ext4 bounds")
    name = item.device_path.removeprefix(prefix)
    legacy_match = re.fullmatch(
        r"debian-bookworm-arm64-d3-sysvinit-v340([345])-keyed"
        r"(?:-([0-9]{8}-[0-9]{2}))?\.img",
        name,
    )
    display_match = re.fullmatch(
        r"debian-bookworm-arm64-phase2-display-v3406-keyed-"
        r"([0-9]{8}-[0-9]{2})\.img",
        name,
    )
    if legacy_match is not None:
        kind = legacy_match.group(1)
        suffix = legacy_match.group(2) or ""
    elif display_match is not None:
        kind = "6"
        suffix = display_match.group(1)
    else:
        raise ContractError("cleanup path cannot be represented exactly")
    selector = f"{kind}:{suffix}:{item.st_ino}"
    if not re.fullmatch(r"[3-6]:(?:[0-9]{8}-[0-9]{2})?:[1-9][0-9]{0,9}", selector):
        raise ContractError("cleanup selector is not canonical")
    if _cleanup_selector_path(selector) != item.device_path:
        raise ContractError("cleanup selector does not round-trip exactly")
    return selector


def _cleanup_selector_path(selector: str) -> str:
    match = re.fullmatch(
        r"([3-6]):((?:[0-9]{8}-[0-9]{2})?):([1-9][0-9]{0,9})",
        selector,
    )
    if match is None:
        raise ContractError("cleanup selector is not canonical")
    kind, suffix, _ = match.groups()
    if kind == "6" and not suffix:
        raise ContractError("display cleanup selector requires an exact suffix")
    if kind in {"3", "4", "5"}:
        name = f"debian-bookworm-arm64-d3-sysvinit-v340{kind}-keyed"
    else:
        name = "debian-bookworm-arm64-phase2-display-v3406-keyed"
    if suffix:
        name += f"-{suffix}"
    return f"/mnt/sdext/a90/runtime/{name}.img"


def _cleanup_args(spec: CleanupSpec) -> tuple[str, ...]:
    devices = {item.st_dev for item in spec.selected}
    if len(devices) != 1:
        raise ContractError("cleanup selection is not on one exact filesystem")
    return str(next(iter(devices))), ",".join(
        _cleanup_selector(item) for item in spec.selected
    )


def _cleanup_command(spec: CleanupSpec) -> list[str]:
    command = _script_command(_cleanup_script(spec), _cleanup_args(spec))
    _require_bounded_command(command, "cleanup effect")
    return command


def _selected_state_script() -> str:
    return "\n".join(
        (
            "set -eu",
            "p=$1; e=$2; h=$3; t=$4",
            'if [ ! -e "$p" ] && [ ! -L "$p" ]; then x=absent',
            "else",
            '  [ ! -L "$p" ]; [ -f "$p" ]',
            '  [ "$(/bin/busybox stat -c "%F|%s|%a|%h|%d|%i" "$p")" = "$e" ]',
            '  s=$(/bin/busybox sha256sum "$p"); s=${s%% *}; [ "$s" = "$h" ]',
            "  x=present",
            "fi",
            'echo "A90CLEAN_SELECTED_STATE tag=$t state=$x"',
        )
    )


def _read_selected_state(item: ImageRecord, tag: str) -> str:
    text = _run_script(
        _selected_state_script(),
        HASH_TIMEOUT_SEC,
        f"{tag} cleanup reconciliation",
        args=_image_exact_args(item, tag),
    )
    matches = re.findall(
        rf"^A90CLEAN_SELECTED_STATE tag={re.escape(tag)} "
        r"state=(absent|present)\r?$",
        text,
        re.MULTILINE,
    )
    if len(matches) != 1:
        raise ContractError(f"{tag} cleanup state marker is not exact")
    return matches[0]


def _filesystem_state_script() -> str:
    return "\n".join(
        (
            "set -eu",
            f"W={shlex.quote(WORK_PATH)}",
            'if [ -e "$W" ] || [ -L "$W" ]; then X=present; else X=absent; fi',
            "set -- $(/bin/busybox df -k /mnt/sdext | "
            "/bin/busybox tail -n 1)",
            'echo "A90CLEAN_FS_STATE work=$X blocks=$2 used=$3 available=$4"',
        )
    )


def _read_reconciliation(spec: CleanupSpec) -> dict[str, Any]:
    selected = [
        _read_selected_state(item, f"selected-{index}")
        for index, item in enumerate(spec.selected)
    ]
    for index, item in enumerate(spec.protected):
        _read_exact_image(item, f"protected-{index}")
    text = _run_script(
        _filesystem_state_script(),
        READ_TIMEOUT_SEC,
        "cleanup filesystem reconciliation",
    )
    matches = re.findall(
        r"^A90CLEAN_FS_STATE work=(absent|present) blocks=([0-9]+) "
        r"used=([0-9]+) available=([0-9]+)\r?$",
        text,
        re.MULTILINE,
    )
    if len(matches) != 1:
        raise ContractError("cleanup reconciliation output is not exact")
    work, blocks, used, available = matches[0]
    return {
        "selected": selected,
        "protected": "exact",
        "work": work,
        "filesystem_kib": {
            "blocks": int(blocks),
            "used": int(used),
            "available": int(available),
        },
    }


def _cleanup_result_value(
    spec: CleanupSpec,
    *,
    approval_binding_sha256: str,
    before_filesystem: dict[str, int],
    response_proven: bool,
    dispatch_error: dict[str, str] | None,
    reconciliation: dict[str, Any],
    reconciliation_error: dict[str, str] | None,
    final_health: dict[str, Any],
    health_error: dict[str, str] | None,
    resumed_from_durable_dispatch: bool,
    observation_bridge_process: dict[str, Any],
) -> dict[str, Any]:
    selected_state = reconciliation.get("selected")
    all_absent = selected_state == ["absent"] * len(spec.selected)
    protected_exact = reconciliation.get("protected") == "exact"
    work_absent = reconciliation.get("work") == "absent"
    final_healthy = final_health.get("proven") is True
    after_filesystem = reconciliation.get("filesystem_kib")
    free_gain_kib: int | None = None
    free_gain_bounds_kib = _free_gain_bounds(spec)
    if (
        isinstance(after_filesystem, dict)
        and type(after_filesystem.get("available")) is int
    ):
        free_gain_kib = (
            after_filesystem["available"] - before_filesystem["available"]
        )
    free_space_proven = (
        free_gain_kib is not None
        and free_gain_bounds_kib[0] <= free_gain_kib <= free_gain_bounds_kib[1]
    )
    if (
        all_absent
        and protected_exact
        and work_absent
        and final_healthy
        and free_space_proven
    ):
        outcome = (
            "PASS_EXACT_HOST_RECOVERABLE_ROOTFS_SET_UNLINKED"
            if response_proven
            else "PASS_EFFECT_PROVEN_AFTER_AMBIGUOUS_RESPONSE"
        )
    elif (
        isinstance(selected_state, list)
        and len(selected_state) == len(spec.selected)
        and "absent" in selected_state
        and "present" in selected_state
    ):
        outcome = "RECOVERY_PENDING_PARKED_PARTIAL_NO_RETRY"
    else:
        outcome = "RECOVERY_PENDING_PARKED_NO_RETRY"
    return {
        "schema": RESULT_SCHEMA,
        "created_utc": legacy.utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "approval_binding_sha256": approval_binding_sha256,
        "outcome": outcome,
        "dispatch_count": 1,
        "cleanup_retransmitted": False,
        "response_proven": response_proven,
        "dispatch_error": dispatch_error,
        "reconciliation": reconciliation,
        "reconciliation_error": reconciliation_error,
        "final_health": final_health,
        "final_health_error": health_error,
        "before_filesystem_kib": before_filesystem,
        "free_gain_kib": free_gain_kib,
        "free_gain_bounds_kib": list(free_gain_bounds_kib),
        "free_space_proven": free_space_proven,
        "selected_paths": [item.device_path for item in spec.selected],
        "protected_paths": [item.device_path for item in spec.protected],
        "resumed_from_durable_dispatch": resumed_from_durable_dispatch,
        "observation_bridge_process": observation_bridge_process,
        "device_write": True,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
        "other_target_commands": 0,
    }


def execute_cleanup(
    spec: CleanupSpec,
    *,
    approval: str | None,
    transaction_dir: Path,
    operator_attended: bool,
) -> dict[str, Any]:
    if operator_attended is not True:
        raise ContractError("exact SD cleanup is attended-only")
    if approval is None:
        compatibility_path = approval_path(spec)
        if compatibility_path.exists():
            compatibility = _require_dict(
                json.loads(_require_private(compatibility_path).read_text(encoding="utf-8")),
                "compatibility binding",
            )
        else:
            compatibility = prepare_approval(spec)
        approval = _require_string(
            compatibility.get("approval_token"),
            "compatibility token",
        )
    prepared = _consume_approval(spec, approval)
    transaction_dir = transaction_dir.resolve()
    expected = (PRIVATE_BASE / spec.run_id / "live").resolve()
    if transaction_dir != expected or transaction_dir.exists():
        raise ContractError("cleanup transaction must be a new exact private path")
    _inventory_age(spec)
    realpath, serial_sha = _find_target()
    if realpath != spec.bridge_realpath or serial_sha != USB_SERIAL_SHA256:
        raise ContractError("current A90 target differs from the manifest")
    bridge = _require_bridge(realpath)
    if bridge != spec.bridge_process:
        raise ContractError("current bridge process generation differs")
    _revalidate_source_closure(spec)
    recovery_availability = _revalidate_recovery_availability(spec)
    before_health = _health()
    for item in spec.selected:
        if item.host_preservation is None:
            raise ContractError("host preservation is absent")
        digest, state = legacy.hash_open_regular(item.host_preservation.path)
        if state.st_size != IMAGE_SIZE or digest != item.sha256:
            raise ContractError("host preservation changed before dispatch")
    before_filesystem = _read_cleanup_preflight(spec)
    cleanup_command = _cleanup_command(spec)
    realpath, bridge, before_health = _revalidate_dispatch_window(spec)
    transaction_dir.mkdir(mode=0o700)
    _fsync_directory(transaction_dir.parent)
    binding_sha = prepared["approval_binding_sha256"]
    legacy.write_private_json_exclusive(
        transaction_dir / "intent.json",
        {
            "schema": "a90_attended_sd_exact_rootfs_cleanup_intent_v1",
            "created_utc": legacy.utc_now(),
            "run_id": spec.run_id,
            "manifest_sha256": spec.manifest_sha256,
            "approval_binding_sha256": binding_sha,
            "target": {
                "bridge_realpath": realpath,
                "usb_serial_sha256": serial_sha,
                "bridge": bridge,
            },
            "before_health": before_health,
            "before_filesystem_kib": before_filesystem,
            "recovery_available": recovery_availability,
            "selected_paths": [item.device_path for item in spec.selected],
            "protected_paths": [item.device_path for item in spec.protected],
            "unlink_dispatch_count_max": 1,
            "unlink_retry_forbidden": True,
        },
    )
    legacy.write_private_json_exclusive(
        transaction_dir / "dispatch-started.json",
        {
            "schema": "a90_attended_sd_exact_rootfs_cleanup_dispatch_v1",
            "created_utc": legacy.utc_now(),
            "run_id": spec.run_id,
            "dispatch_count": 1,
            "cleanup_command_sha256": legacy.json_sha256(
                {"argv": cleanup_command}
            ),
            "approval_consumed": True,
            "retry_forbidden": True,
        },
    )
    response_proven = False
    dispatch_error: dict[str, str] | None = None
    try:
        text = _run_script(
            _cleanup_script(spec),
            CLEANUP_TIMEOUT_SEC,
            "cleanup dispatch",
            args=_cleanup_args(spec),
        )
        response_proven = text.count(
            "A90CLEAN_UNLINKED exact=1 "
            f"selected_absent={len(spec.selected)}"
        ) == 1
        if not response_proven:
            dispatch_error = {
                "type": "ContractError",
                "message": "cleanup response marker is not exact",
            }
    except Exception as exc:  # noqa: BLE001 - unlink is never retransmitted
        dispatch_error = {"type": type(exc).__name__, "message": str(exc)}
    if dispatch_error is not None:
        legacy.write_private_json_exclusive(
            transaction_dir / "dispatch-error.json",
            {
                "schema": (
                    "a90_attended_sd_exact_rootfs_cleanup_dispatch_error_v1"
                ),
                "created_utc": legacy.utc_now(),
                "error": dispatch_error,
                "cleanup_retransmitted": False,
                "read_only_reconciliation_allowed": True,
            },
        )
    reconciliation_error: dict[str, str] | None = None
    try:
        reconciliation = _read_reconciliation(spec)
    except Exception as exc:  # noqa: BLE001 - never causes another unlink
        reconciliation = {
            "selected": ["unknown"] * len(spec.selected),
            "protected": "unknown",
            "work": "unknown",
        }
        reconciliation_error = {"type": type(exc).__name__, "message": str(exc)}
    legacy.write_private_json_exclusive(
        transaction_dir / "reconciliation.json",
        {
            "schema": (
                "a90_attended_sd_exact_rootfs_cleanup_reconciliation_v1"
            ),
            "created_utc": legacy.utc_now(),
            "result": reconciliation,
            "error": reconciliation_error,
            "cleanup_retransmitted": False,
        },
    )
    health_error: dict[str, str] | None = None
    try:
        final_health = _health()
    except Exception as exc:  # noqa: BLE001 - never causes another unlink
        final_health = {"proven": False}
        health_error = {"type": type(exc).__name__, "message": str(exc)}
    result = _cleanup_result_value(
        spec,
        approval_binding_sha256=binding_sha,
        before_filesystem=before_filesystem,
        response_proven=response_proven,
        dispatch_error=dispatch_error,
        reconciliation=reconciliation,
        reconciliation_error=reconciliation_error,
        final_health=final_health,
        health_error=health_error,
        resumed_from_durable_dispatch=False,
        observation_bridge_process=bridge,
    )
    legacy.write_private_json_exclusive(transaction_dir / "result.json", result)
    return result


def _load_private_record(path: Path, label: str) -> tuple[legacy.BoundFile, dict[str, Any]]:
    bound = _bound(path, private=True)
    return bound, _require_dict(
        json.loads(bound.path.read_text(encoding="utf-8")),
        label,
    )


def _validated_existing_cleanup_result(
    spec: CleanupSpec,
    path: Path,
) -> dict[str, Any]:
    _, value = _load_private_record(path, "cleanup result")
    before_filesystem = _require_dict(
        value.get("before_filesystem_kib"),
        "cleanup result before filesystem",
    )
    reconciliation = _require_dict(
        value.get("reconciliation"),
        "cleanup result reconciliation",
    )
    final_health = _require_dict(
        value.get("final_health"),
        "cleanup result final health",
    )
    observation_bridge = _validated_bridge_process(
        value.get("observation_bridge_process")
    )
    resumed = value.get("resumed_from_durable_dispatch")
    if (
        value.get("schema") != RESULT_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("manifest_sha256") != spec.manifest_sha256
        or value.get("approval_binding_sha256")
        != legacy.json_sha256(_approval_binding(spec))
        or type(value.get("dispatch_count")) is not int
        or value.get("dispatch_count") != 1
        or value.get("cleanup_retransmitted") is not False
        or type(value.get("response_proven")) is not bool
        or type(resumed) is not bool
        or type(value.get("free_space_proven")) is not bool
        or value.get("free_gain_kib") is not None
        and type(value.get("free_gain_kib")) is not int
        or not isinstance(value.get("free_gain_bounds_kib"), list)
        or len(value["free_gain_bounds_kib"]) != 2
        or any(
            type(item) is not int or item < 0
            for item in value["free_gain_bounds_kib"]
        )
        or value.get("selected_paths")
        != [item.device_path for item in spec.selected]
        or value.get("protected_paths")
        != [item.device_path for item in spec.protected]
        or value.get("device_write") is not True
        or value.get("payload_transfer") is not False
        or value.get("partition_write") is not False
        or value.get("flash") is not False
        or type(value.get("other_target_commands")) is not int
        or value.get("other_target_commands") != 0
        or not isinstance(value.get("created_utc"), str)
        or not value["created_utc"]
        or set(before_filesystem) != {"blocks", "used", "available"}
        or any(
            type(before_filesystem.get(key)) is not int
            or before_filesystem[key] < 0
            for key in ("blocks", "used", "available")
        )
        or value.get("dispatch_error") is not None
        and not isinstance(value.get("dispatch_error"), dict)
        or value.get("reconciliation_error") is not None
        and not isinstance(value.get("reconciliation_error"), dict)
        or value.get("final_health_error") is not None
        and not isinstance(value.get("final_health_error"), dict)
    ):
        raise ContractError("existing cleanup result is not exact")
    expected = _cleanup_result_value(
        spec,
        approval_binding_sha256=value["approval_binding_sha256"],
        before_filesystem=before_filesystem,
        response_proven=value["response_proven"],
        dispatch_error=value.get("dispatch_error"),
        reconciliation=reconciliation,
        reconciliation_error=value.get("reconciliation_error"),
        final_health=final_health,
        health_error=value.get("final_health_error"),
        resumed_from_durable_dispatch=resumed,
        observation_bridge_process=observation_bridge,
    )
    expected["created_utc"] = value["created_utc"]
    if resumed:
        recovery_available = _require_dict(
            value.get("recovery_available"),
            "cleanup result recovery availability",
        )
        if (
            type(recovery_available.get("proven")) is not bool
            or value.get("resume_device_write") is not False
        ):
            raise ContractError("cleanup resume result flags are not exact")
        expected["resume_device_write"] = False
        expected["recovery_available"] = recovery_available
    if value != expected:
        raise ContractError("existing cleanup result semantics changed")
    return value


def _load_dispatched_cleanup_journal(
    spec: CleanupSpec,
    transaction_dir: Path,
) -> tuple[legacy.BoundFile, dict[str, Any], legacy.BoundFile, dict[str, Any]]:
    intent_bound, intent = _load_private_record(
        transaction_dir / "intent.json",
        "cleanup intent",
    )
    dispatch_bound, dispatch = _load_private_record(
        transaction_dir / "dispatch-started.json",
        "cleanup dispatch",
    )
    target = _require_dict(intent.get("target"), "cleanup intent target")
    before_filesystem = _require_dict(
        intent.get("before_filesystem_kib"),
        "cleanup intent filesystem",
    )
    approval_binding_sha256 = legacy.json_sha256(_approval_binding(spec))
    if (
        set(intent)
        != {
            "schema",
            "created_utc",
            "run_id",
            "manifest_sha256",
            "approval_binding_sha256",
            "target",
            "before_health",
            "before_filesystem_kib",
            "recovery_available",
            "selected_paths",
            "protected_paths",
            "unlink_dispatch_count_max",
            "unlink_retry_forbidden",
        }
        or intent.get("schema")
        != "a90_attended_sd_exact_rootfs_cleanup_intent_v1"
        or intent.get("run_id") != spec.run_id
        or intent.get("manifest_sha256") != spec.manifest_sha256
        or intent.get("approval_binding_sha256") != approval_binding_sha256
        or set(target)
        != {"bridge_realpath", "usb_serial_sha256", "bridge"}
        or target.get("bridge_realpath") != spec.bridge_realpath
        or target.get("usb_serial_sha256") != USB_SERIAL_SHA256
        or target.get("bridge") != spec.bridge_process
        or not isinstance(intent.get("before_health"), dict)
        or set(before_filesystem) != {"blocks", "used", "available"}
        or any(
            type(before_filesystem.get(key)) is not int
            or before_filesystem[key] < 0
            for key in ("blocks", "used", "available")
        )
        or not isinstance(intent.get("recovery_available"), dict)
        or intent.get("selected_paths")
        != [item.device_path for item in spec.selected]
        or intent.get("protected_paths")
        != [item.device_path for item in spec.protected]
        or type(intent.get("unlink_dispatch_count_max")) is not int
        or intent.get("unlink_dispatch_count_max") != 1
        or intent.get("unlink_retry_forbidden") is not True
    ):
        raise ContractError("durable cleanup intent is not exact")
    if (
        set(dispatch)
        != {
            "schema",
            "created_utc",
            "run_id",
            "dispatch_count",
            "cleanup_command_sha256",
            "approval_consumed",
            "retry_forbidden",
        }
        or dispatch.get("schema")
        != "a90_attended_sd_exact_rootfs_cleanup_dispatch_v1"
        or dispatch.get("run_id") != spec.run_id
        or type(dispatch.get("dispatch_count")) is not int
        or dispatch.get("dispatch_count") != 1
        or dispatch.get("cleanup_command_sha256")
        != legacy.json_sha256({"argv": _cleanup_command(spec)})
        or dispatch.get("approval_consumed") is not True
        or dispatch.get("retry_forbidden") is not True
    ):
        raise ContractError("durable cleanup dispatch is not exact")
    return intent_bound, intent, dispatch_bound, dispatch


def resume_dispatched_cleanup(
    spec: CleanupSpec,
    *,
    transaction_dir: Path,
) -> dict[str, Any]:
    transaction_dir = transaction_dir.resolve()
    expected = (PRIVATE_BASE / spec.run_id / "live").resolve()
    if transaction_dir != expected:
        raise ContractError("cleanup resume transaction path is not canonical")
    state = transaction_dir.lstat()
    if (
        not stat.S_ISDIR(state.st_mode)
        or stat.S_IMODE(state.st_mode) != 0o700
    ):
        raise ContractError("cleanup resume transaction directory is not exact")
    result_path = transaction_dir / "result.json"
    if result_path.exists():
        return _validated_existing_cleanup_result(spec, result_path)
    intent_bound, intent, dispatch_bound, _ = _load_dispatched_cleanup_journal(
        spec,
        transaction_dir,
    )
    realpath, serial_sha = _find_target()
    if realpath != spec.bridge_realpath or serial_sha != USB_SERIAL_SHA256:
        raise ContractError("cleanup resume target differs from the manifest")
    current_bridge = _require_bridge(realpath)
    _revalidate_source_closure(spec)
    try:
        recovery_available = {
            "proven": True,
            "receipt": _revalidate_recovery_availability(spec),
        }
    except Exception as exc:  # noqa: BLE001 - does not block passive reconciliation
        recovery_available = {
            "proven": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
    resume_intent_path = transaction_dir / "resume-intent.json"
    resume_binding = {
        "schema": "a90_attended_sd_exact_rootfs_cleanup_resume_intent_v1",
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "approval_binding_sha256": intent["approval_binding_sha256"],
        "intent_sha256": intent_bound.sha256,
        "dispatch_sha256": dispatch_bound.sha256,
        "cleanup_dispatch_count": 1,
        "cleanup_retransmitted": False,
        "read_only_reconciliation": True,
        "resume_device_write": False,
    }
    if resume_intent_path.exists():
        _, existing_resume = _load_private_record(
            resume_intent_path,
            "cleanup resume intent",
        )
        if existing_resume != resume_binding:
            raise ContractError("cleanup resume intent changed")
    else:
        legacy.write_private_json_exclusive(resume_intent_path, resume_binding)

    reconciliation_path = transaction_dir / "resume-reconciliation.json"
    if reconciliation_path.exists():
        _, reconciliation_record = _load_private_record(
            reconciliation_path,
            "cleanup resume reconciliation",
        )
        if (
            set(reconciliation_record)
            != {
                "schema",
                "run_id",
                "result",
                "error",
                "cleanup_retransmitted",
                "device_write",
            }
            or reconciliation_record.get("schema")
            != "a90_attended_sd_exact_rootfs_cleanup_resume_reconciliation_v1"
            or reconciliation_record.get("run_id") != spec.run_id
            or reconciliation_record.get("cleanup_retransmitted") is not False
            or reconciliation_record.get("device_write") is not False
        ):
            raise ContractError("cleanup resume reconciliation changed")
        reconciliation = _require_dict(
            reconciliation_record.get("result"),
            "cleanup resume reconciliation result",
        )
        reconciliation_error = reconciliation_record.get("error")
    else:
        try:
            reconciliation = _read_reconciliation(spec)
            reconciliation_error = None
        except Exception as exc:  # noqa: BLE001 - read-only, unlink never replays
            reconciliation = {
                "selected": ["unknown"] * len(spec.selected),
                "protected": "unknown",
                "work": "unknown",
            }
            reconciliation_error = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
        legacy.write_private_json_exclusive(
            reconciliation_path,
            {
                "schema": (
                    "a90_attended_sd_exact_rootfs_cleanup_"
                    "resume_reconciliation_v1"
                ),
                "run_id": spec.run_id,
                "result": reconciliation,
                "error": reconciliation_error,
                "cleanup_retransmitted": False,
                "device_write": False,
            },
        )

    health_path = transaction_dir / "resume-health.json"
    if health_path.exists():
        _, health_record = _load_private_record(
            health_path,
            "cleanup resume health",
        )
        if (
            set(health_record)
            != {"schema", "run_id", "result", "error", "device_write"}
            or health_record.get("schema")
            != "a90_attended_sd_exact_rootfs_cleanup_resume_health_v1"
            or health_record.get("run_id") != spec.run_id
            or health_record.get("device_write") is not False
        ):
            raise ContractError("cleanup resume health changed")
        final_health = _require_dict(
            health_record.get("result"),
            "cleanup resume health result",
        )
        health_error = health_record.get("error")
    else:
        try:
            final_health = _health()
            health_error = None
        except Exception as exc:  # noqa: BLE001 - observation never replays unlink
            final_health = {"proven": False}
            health_error = {"type": type(exc).__name__, "message": str(exc)}
        legacy.write_private_json_exclusive(
            health_path,
            {
                "schema": "a90_attended_sd_exact_rootfs_cleanup_resume_health_v1",
                "run_id": spec.run_id,
                "result": final_health,
                "error": health_error,
                "device_write": False,
            },
        )
    result = _cleanup_result_value(
        spec,
        approval_binding_sha256=intent["approval_binding_sha256"],
        before_filesystem=intent["before_filesystem_kib"],
        response_proven=False,
        dispatch_error={
            "type": "HOST_PROCESS_TERMINATED_POST_DISPATCH",
            "message": (
                "result was absent after durable dispatch; effect was not "
                "replayed and was classified by read-only reconciliation"
            ),
        },
        reconciliation=reconciliation,
        reconciliation_error=reconciliation_error,
        final_health=final_health,
        health_error=health_error,
        resumed_from_durable_dispatch=True,
        observation_bridge_process=current_bridge,
    )
    result["resume_device_write"] = False
    result["recovery_available"] = recovery_available
    legacy.write_private_json_exclusive(result_path, result)
    return result


def _restore_args(spec: CleanupSpec) -> argparse.Namespace:
    return argparse.Namespace(
        bridge_host=a90ctl.DEFAULT_HOST,
        bridge_port=a90ctl.DEFAULT_PORT,
        device_ip=spec.recovery_observer_device,
        bridge_timeout=120.0,
        connect_timeout=10.0,
        tcp_timeout=60.0,
        toybox="/bin/toybox",
        transfer_timeout=1200.0,
        transfer_delay=2.0,
    )


def _recovery_health() -> dict[str, Any]:
    version = _protocol_text(_remote(["version"], READ_TIMEOUT_SEC), "version")
    selftest = _protocol_text(_remote(["selftest"], READ_TIMEOUT_SEC), "selftest")
    status_text = _protocol_text(_remote(["status"], READ_TIMEOUT_SEC), "status")
    version_lines = [
        line.rstrip("\r")
        for line in version.splitlines()
        if line.startswith("version: ")
    ]
    allowed = {
        f"version: {EXPECTED_VERSION} build={EXPECTED_BUILD}": "RESIDENT_HEALTHY",
        "version: 0.9.285 build=v2321-usb-clean-identity-rodata": "BASELINE_HEALTHY",
    }
    match = SELFTEST_RE.search(selftest)
    if (
        len(version_lines) != 1
        or version_lines[0] not in allowed
        or match is None
        or PSTORE_RE.search(status_text) is None
        or RUNTIME_RE.search(status_text) is None
    ):
        raise ContractError("A90 recovery health is not exact")
    return {
        "proven": True,
        "state": allowed[version_lines[0]],
        "version_line": version_lines[0],
        "selftest_fail": 0,
        "pstore_entries": 0,
    }


def _restore_selected_state_script() -> str:
    return "\n".join(
        (
            "set -eu",
            "p=$1; e=$2; h=$3; t=$4; g=$5",
            'if [ -e "$g" ] || [ -L "$g" ]; then y=present; else y=absent; fi',
            'if [ ! -e "$p" ] && [ ! -L "$p" ]; then x=absent; i=0',
            "else",
            '  [ ! -L "$p" ]; [ -f "$p" ]',
            '  [ "$(/bin/busybox stat -c "%F|%s|%a|%h|%d" "$p")" = "$e" ]',
            '  s=$(/bin/busybox sha256sum "$p"); s=${s%% *}; [ "$s" = "$h" ]',
            '  i=$(/bin/busybox stat -c "%i" "$p"); [ "$i" -gt 0 ]; x=exact',
            "fi",
            'echo "A90CLEAN_RESTORE_STATE tag=$t selected=$x stage=$y ino=$i"',
        )
    )


def _read_restore_selected_state(
    item: ImageRecord,
    tag: str,
    stage_dir: str,
) -> tuple[str, str, int]:
    args = (
        item.device_path,
        f"regular file|{IMAGE_SIZE}|{IMAGE_MODE}|1|{item.st_dev}",
        item.sha256,
        tag,
        stage_dir,
    )
    text = _run_script(
        _restore_selected_state_script(),
        HASH_TIMEOUT_SEC,
        f"{tag} restore reconciliation",
        args=args,
    )
    matches = re.findall(
        rf"^A90CLEAN_RESTORE_STATE tag={re.escape(tag)} "
        r"selected=(absent|exact) stage=(absent|present) ino=([0-9]+)\r?$",
        text,
        re.MULTILINE,
    )
    if len(matches) != 1:
        raise ContractError(f"{tag} restore state marker is not exact")
    selected, stage, inode = matches[0]
    if (selected == "absent") is not (inode == "0"):
        raise ContractError(f"{tag} restore inode state is not exact")
    return selected, stage, int(inode)


def _restore_reconciled(spec: CleanupSpec) -> dict[str, Any]:
    selected: list[str] = []
    stages: list[str] = []
    inodes: list[int] = []
    for index, item in enumerate(spec.selected):
        state, stage, inode = _read_restore_selected_state(
            item,
            f"selected-{index}",
            _restore_stage_spec(spec, index).remote_stage_dir,
        )
        selected.append(state)
        stages.append(stage)
        inodes.append(inode)
    for index, item in enumerate(spec.protected):
        _read_exact_image(item, f"protected-{index}")
    text = _run_script(
        _filesystem_state_script(),
        READ_TIMEOUT_SEC,
        "restore filesystem reconciliation",
    )
    matches = re.findall(
        r"^A90CLEAN_FS_STATE work=(absent|present) blocks=[0-9]+ "
        r"used=[0-9]+ available=[0-9]+\r?$",
        text,
        re.MULTILINE,
    )
    if len(matches) != 1:
        raise ContractError("restore filesystem state is not exact")
    return {
        "selected": selected,
        "stages": stages,
        "protected": "exact",
        "work": matches[0],
        "restored_inodes": inodes,
    }


def _restore_result_value(
    spec: CleanupSpec,
    *,
    cleanup_result_sha256: str,
    restore_indexes: list[int],
    reserve_count: int,
    transfer_count: int,
    publish_count: int,
    response_proven: bool,
    error: dict[str, str] | None,
    reconciliation: dict[str, Any],
    reconciliation_error: dict[str, str] | None,
    final_health: dict[str, Any],
    health_error: dict[str, str] | None,
    resumed_from_durable_restore: bool,
    observation_bridge_process: dict[str, Any],
) -> dict[str, Any]:
    exact = (
        reconciliation.get("selected") == ["exact"] * len(spec.selected)
        and reconciliation.get("stages") == ["absent"] * len(spec.selected)
        and reconciliation.get("protected") == "exact"
        and reconciliation.get("work") == "absent"
        and final_health.get("proven") is True
        and final_health.get("state") == "RESIDENT_HEALTHY"
    )
    if exact:
        outcome = (
            "PASS_EXACT_OBSOLETE_ROOTFS_RESTORED"
            if response_proven
            else "PASS_EXACT_OBSOLETE_ROOTFS_RESTORED_AFTER_AMBIGUOUS_RESPONSE"
        )
    else:
        outcome = "RECOVERY_PENDING_PARKED_RESTORE_NO_RETRY"
    return {
        "schema": "a90_attended_sd_exact_rootfs_restore_result_v1",
        "created_utc": legacy.utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "cleanup_result_sha256": cleanup_result_sha256,
        "outcome": outcome,
        "restore_indexes": restore_indexes,
        "reserve_count": reserve_count,
        "transfer_count": transfer_count,
        "publish_count": publish_count,
        "response_proven": response_proven,
        "transfer_retransmitted": False,
        "publish_retransmitted": False,
        "error": error,
        "reconciliation": reconciliation,
        "reconciliation_error": reconciliation_error,
        "final_health": final_health,
        "final_health_error": health_error,
        "resumed_from_durable_restore": resumed_from_durable_restore,
        "observation_bridge_process": observation_bridge_process,
        "payload_transfer": transfer_count > 0,
        "partition_write": False,
        "flash": False,
        "other_target_commands": 0,
    }


def execute_restore(
    spec: CleanupSpec,
    *,
    cleanup_result_path: Path,
    transaction_dir: Path,
    operator_attended: bool,
) -> dict[str, Any]:
    if operator_attended is not True:
        raise ContractError("exact SD restoration is attended-only")
    cleanup_result = _bound(cleanup_result_path, private=True)
    expected_result = (PRIVATE_BASE / spec.run_id / "live" / "result.json").resolve()
    if cleanup_result.path != expected_result:
        raise ContractError("restore input is not the canonical cleanup result")
    cleanup_value = _validated_existing_cleanup_result(
        spec,
        cleanup_result.path,
    )
    if cleanup_value.get("outcome") not in {
        "RECOVERY_PENDING_PARKED_PARTIAL_NO_RETRY",
        "RECOVERY_PENDING_PARKED_NO_RETRY",
    }:
        raise ContractError("cleanup result does not authorize exact restoration")
    transaction_dir = transaction_dir.resolve()
    expected_dir = (PRIVATE_BASE / spec.run_id / "live" / "restore").resolve()
    if transaction_dir != expected_dir or transaction_dir.exists():
        raise ContractError("restore transaction must be a new canonical path")
    realpath, serial_sha = _find_target()
    if realpath != spec.bridge_realpath or serial_sha != USB_SERIAL_SHA256:
        raise ContractError("restore target differs from cleanup manifest")
    bridge = _require_bridge(realpath)
    _revalidate_source_closure(spec)
    recovery_available = _revalidate_recovery_availability(spec)
    before_health = _recovery_health()
    state = _read_reconciliation(spec)
    if state.get("protected") != "exact" or state.get("work") != "absent":
        raise ContractError("restore opening protected state is not exact")
    selected_state = state.get("selected")
    if not isinstance(selected_state, list) or any(
        value not in {"absent", "present"} for value in selected_state
    ):
        raise ContractError("restore opening selection state is not exact")
    restore_indexes = [
        index for index, value in enumerate(selected_state) if value == "absent"
    ]
    if not restore_indexes:
        raise ContractError("restore has no absent selected image")
    transaction_dir.mkdir(mode=0o700)
    _fsync_directory(transaction_dir.parent)
    legacy.write_private_json_exclusive(
        transaction_dir / "0000-intent.json",
        {
            "schema": "a90_attended_sd_exact_rootfs_restore_intent_v1",
            "created_utc": legacy.utc_now(),
            "run_id": spec.run_id,
            "cleanup_result_sha256": cleanup_result.sha256,
            "approval_binding_sha256": cleanup_value.get(
                "approval_binding_sha256"
            ),
            "restore_indexes": restore_indexes,
            "destinations": [spec.selected[index].device_path for index in restore_indexes],
            "recovery_available": recovery_available,
            "manifest_bridge_process": spec.bridge_process,
            "recovery_bridge_process": bridge,
            "before_health": before_health,
            "automatic": False,
            "publish_retry_forbidden": True,
        },
    )
    sequence = 1

    def record(state: str, payload: dict[str, Any]) -> None:
        nonlocal sequence
        legacy.write_private_json_exclusive(
            transaction_dir / f"{sequence:04d}-{state}.json",
            {"created_utc": legacy.utc_now(), **payload},
        )
        sequence += 1

    args = _restore_args(spec)
    error: dict[str, str] | None = None
    reserve_count = 0
    publish_count = 0
    transfer_count = 0
    for index in restore_indexes:
        restore = _restore_stage_spec(spec, index)
        try:
            readonly = _run_script(
                staging.remote_readonly_preflight_script(restore),
                HASH_TIMEOUT_SEC,
                f"restore {index} preflight",
            )
            record(
                "preflight",
                {"index": index, "record": readonly, "device_write": False},
            )
            reserve_count += 1
            record(
                "reserve-start",
                {
                    "index": index,
                    "reserve_count": reserve_count,
                    "device_write_may_follow": True,
                    "retry_forbidden": True,
                },
            )
            reserve = _run_script(
                staging.remote_reserve_script(restore),
                HASH_TIMEOUT_SEC,
                f"restore {index} reserve",
            )
            transfer_count += 1
            record(
                "transfer-start",
                {
                    "index": index,
                    "path": restore.remote_payload,
                    "size": restore.local_size,
                    "sha256": restore.local_sha256,
                    "reserve": reserve,
                    "transfer_count": transfer_count,
                    "retry_forbidden": True,
                },
            )
            command = staging.transfer_command(restore, args)
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                timeout=args.transfer_timeout + args.bridge_timeout + 120.0,
                check=False,
            )
            if completed.returncode != 0:
                raise ContractError(
                    f"restore {index} transfer failed rc={completed.returncode}"
                )
            record(
                "transfer-complete",
                {
                    "index": index,
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                },
            )
            verified = _run_script(
                staging.remote_verify_payload_script(restore),
                HASH_TIMEOUT_SEC,
                f"restore {index} verify",
            )
            record(
                "publish-start",
                {
                    "index": index,
                    "verified": verified,
                    "publication": "hardlink-no-clobber",
                    "publish_count": publish_count + 1,
                    "retry_forbidden": True,
                },
            )
            publish_count += 1
            _run_script(
                staging.remote_publish_script(restore),
                HASH_TIMEOUT_SEC,
                f"restore {index} publish",
            )
        except Exception as exc:  # noqa: BLE001 - never replay restoration publish
            error = {"type": type(exc).__name__, "message": str(exc)}
            break
    reconciliation_error: dict[str, str] | None = None
    try:
        reconciliation = _restore_reconciled(spec)
    except Exception as exc:  # noqa: BLE001 - read-only after uncertain restore
        reconciliation = {
            "selected": ["unknown"] * len(spec.selected),
            "stages": ["unknown"] * len(spec.selected),
            "protected": "unknown",
            "work": "unknown",
        }
        reconciliation_error = {"type": type(exc).__name__, "message": str(exc)}
    try:
        final_health = _recovery_health()
        health_error = None
    except Exception as exc:  # noqa: BLE001 - never causes replay
        final_health = {"proven": False}
        health_error = {"type": type(exc).__name__, "message": str(exc)}
    result = _restore_result_value(
        spec,
        cleanup_result_sha256=cleanup_result.sha256,
        restore_indexes=restore_indexes,
        reserve_count=reserve_count,
        transfer_count=transfer_count,
        publish_count=publish_count,
        response_proven=error is None,
        error=error,
        reconciliation=reconciliation,
        reconciliation_error=reconciliation_error,
        final_health=final_health,
        health_error=health_error,
        resumed_from_durable_restore=False,
        observation_bridge_process=bridge,
    )
    legacy.write_private_json_exclusive(transaction_dir / "result.json", result)
    return result


def _validated_existing_restore_result(
    spec: CleanupSpec,
    path: Path,
    cleanup_result_sha256: str,
) -> dict[str, Any]:
    _, value = _load_private_record(path, "restore result")
    restore_indexes = value.get("restore_indexes")
    reserve_count = value.get("reserve_count")
    transfer_count = value.get("transfer_count")
    publish_count = value.get("publish_count")
    response_proven = value.get("response_proven")
    resumed = value.get("resumed_from_durable_restore")
    reconciliation = _require_dict(
        value.get("reconciliation"),
        "restore result reconciliation",
    )
    final_health = _require_dict(
        value.get("final_health"),
        "restore result health",
    )
    observation_bridge = _validated_bridge_process(
        value.get("observation_bridge_process")
    )
    if (
        value.get("schema")
        != "a90_attended_sd_exact_rootfs_restore_result_v1"
        or value.get("run_id") != spec.run_id
        or value.get("manifest_sha256") != spec.manifest_sha256
        or value.get("cleanup_result_sha256") != cleanup_result_sha256
        or not isinstance(restore_indexes, list)
        or not restore_indexes
        or len(restore_indexes) != len(set(restore_indexes))
        or any(
            type(index) is not int or not 0 <= index < len(spec.selected)
            for index in restore_indexes
        )
        or type(reserve_count) is not int
        or not 0 <= reserve_count <= len(restore_indexes)
        or type(transfer_count) is not int
        or not 0 <= transfer_count <= reserve_count
        or type(publish_count) is not int
        or not 0 <= publish_count <= transfer_count
        or type(response_proven) is not bool
        or type(resumed) is not bool
        or value.get("transfer_retransmitted") is not False
        or value.get("publish_retransmitted") is not False
        or value.get("payload_transfer") is not (transfer_count > 0)
        or value.get("partition_write") is not False
        or value.get("flash") is not False
        or type(value.get("other_target_commands")) is not int
        or value.get("other_target_commands") != 0
        or value.get("error") is not None
        and not isinstance(value.get("error"), dict)
        or value.get("reconciliation_error") is not None
        and not isinstance(value.get("reconciliation_error"), dict)
        or value.get("final_health_error") is not None
        and not isinstance(value.get("final_health_error"), dict)
        or not isinstance(value.get("created_utc"), str)
        or not value["created_utc"]
    ):
        raise ContractError("existing restore result is not exact")
    expected = _restore_result_value(
        spec,
        cleanup_result_sha256=cleanup_result_sha256,
        restore_indexes=restore_indexes,
        reserve_count=reserve_count,
        transfer_count=transfer_count,
        publish_count=publish_count,
        response_proven=response_proven,
        error=value.get("error"),
        reconciliation=reconciliation,
        reconciliation_error=value.get("reconciliation_error"),
        final_health=final_health,
        health_error=value.get("final_health_error"),
        resumed_from_durable_restore=resumed,
        observation_bridge_process=observation_bridge,
    )
    expected["created_utc"] = value["created_utc"]
    if resumed:
        recovery_available = _require_dict(
            value.get("recovery_available"),
            "restore result recovery availability",
        )
        if (
            type(recovery_available.get("proven")) is not bool
            or value.get("resume_device_write") is not False
        ):
            raise ContractError("restore resume result flags are not exact")
        expected["resume_device_write"] = False
        expected["recovery_available"] = recovery_available
    if value != expected:
        raise ContractError("existing restore result semantics changed")
    return value


def _load_restore_intent(
    spec: CleanupSpec,
    cleanup_result: legacy.BoundFile,
    transaction_dir: Path,
) -> tuple[legacy.BoundFile, dict[str, Any], list[int]]:
    intent_bound, intent = _load_private_record(
        transaction_dir / "0000-intent.json",
        "restore intent",
    )
    restore_indexes = intent.get("restore_indexes")
    manifest_bridge = intent.get("manifest_bridge_process")
    recovery_bridge = intent.get("recovery_bridge_process")
    if (
        set(intent)
        != {
            "schema",
            "created_utc",
            "run_id",
            "cleanup_result_sha256",
            "approval_binding_sha256",
            "restore_indexes",
            "destinations",
            "recovery_available",
            "manifest_bridge_process",
            "recovery_bridge_process",
            "before_health",
            "automatic",
            "publish_retry_forbidden",
        }
        or intent.get("schema")
        != "a90_attended_sd_exact_rootfs_restore_intent_v1"
        or intent.get("run_id") != spec.run_id
        or intent.get("cleanup_result_sha256") != cleanup_result.sha256
        or intent.get("approval_binding_sha256")
        != legacy.json_sha256(_approval_binding(spec))
        or not isinstance(restore_indexes, list)
        or not restore_indexes
        or len(restore_indexes) != len(set(restore_indexes))
        or any(
            type(index) is not int or not 0 <= index < len(spec.selected)
            for index in restore_indexes
        )
        or intent.get("destinations")
        != [spec.selected[index].device_path for index in restore_indexes]
        or not isinstance(intent.get("recovery_available"), dict)
        or manifest_bridge != spec.bridge_process
        or _validated_bridge_process(recovery_bridge) != recovery_bridge
        or not isinstance(intent.get("before_health"), dict)
        or intent.get("automatic") is not False
        or intent.get("publish_retry_forbidden") is not True
    ):
        raise ContractError("durable restore intent is not exact")
    return intent_bound, intent, restore_indexes


def _restore_started_counts(
    spec: CleanupSpec,
    transaction_dir: Path,
    restore_indexes: list[int],
) -> tuple[int, int, int]:
    reserves = sorted(transaction_dir.glob("*-reserve-start.json"))
    transfers = sorted(transaction_dir.glob("*-transfer-start.json"))
    publishes = sorted(transaction_dir.glob("*-publish-start.json"))
    reserve_indexes: list[int] = []
    for count, path in enumerate(reserves, 1):
        if re.fullmatch(r"[0-9]{4}-reserve-start\.json", path.name) is None:
            raise ContractError("restore reserve journal name is not exact")
        _, value = _load_private_record(path, "restore reserve start")
        index = value.get("index")
        if (
            set(value)
            != {
                "created_utc",
                "index",
                "reserve_count",
                "device_write_may_follow",
                "retry_forbidden",
            }
            or type(index) is not int
            or index not in restore_indexes
            or index in reserve_indexes
            or type(value.get("reserve_count")) is not int
            or value.get("reserve_count") != count
            or value.get("device_write_may_follow") is not True
            or value.get("retry_forbidden") is not True
        ):
            raise ContractError("restore reserve journal is not exact")
        reserve_indexes.append(index)
    transfer_indexes: list[int] = []
    for count, path in enumerate(transfers, 1):
        if re.fullmatch(r"[0-9]{4}-transfer-start\.json", path.name) is None:
            raise ContractError("restore transfer journal name is not exact")
        _, value = _load_private_record(path, "restore transfer start")
        index = value.get("index")
        if (
            set(value)
            != {
                "created_utc",
                "index",
                "path",
                "size",
                "sha256",
                "reserve",
                "transfer_count",
                "retry_forbidden",
            }
            or type(index) is not int
            or index not in reserve_indexes
            or index in transfer_indexes
            or value.get("path") != _restore_stage_spec(spec, index).remote_payload
            or value.get("size") != spec.selected[index].size
            or value.get("sha256") != spec.selected[index].sha256
            or not isinstance(value.get("reserve"), str)
            or type(value.get("transfer_count")) is not int
            or value.get("transfer_count") != count
            or value.get("retry_forbidden") is not True
        ):
            raise ContractError("restore transfer journal is not exact")
        transfer_indexes.append(index)
    publish_indexes: list[int] = []
    for count, path in enumerate(publishes, 1):
        if re.fullmatch(r"[0-9]{4}-publish-start\.json", path.name) is None:
            raise ContractError("restore publish journal name is not exact")
        _, value = _load_private_record(path, "restore publish start")
        index = value.get("index")
        if (
            set(value)
            != {
                "created_utc",
                "index",
                "verified",
                "publication",
                "publish_count",
                "retry_forbidden",
            }
            or type(index) is not int
            or index not in transfer_indexes
            or index in publish_indexes
            or not isinstance(value.get("verified"), str)
            or value.get("publication") != "hardlink-no-clobber"
            or type(value.get("publish_count")) is not int
            or value.get("publish_count") != count
            or value.get("retry_forbidden") is not True
        ):
            raise ContractError("restore publish journal is not exact")
        publish_indexes.append(index)
    return len(reserve_indexes), len(transfer_indexes), len(publish_indexes)


def resume_started_restore(
    spec: CleanupSpec,
    *,
    cleanup_result_path: Path,
    transaction_dir: Path,
) -> dict[str, Any]:
    cleanup_result = _bound(cleanup_result_path, private=True)
    expected_cleanup = (PRIVATE_BASE / spec.run_id / "live" / "result.json").resolve()
    if cleanup_result.path != expected_cleanup:
        raise ContractError("restore resume cleanup result is not canonical")
    cleanup_value = _validated_existing_cleanup_result(
        spec,
        cleanup_result.path,
    )
    if cleanup_value.get("outcome") not in {
        "RECOVERY_PENDING_PARKED_PARTIAL_NO_RETRY",
        "RECOVERY_PENDING_PARKED_NO_RETRY",
    }:
        raise ContractError("cleanup result does not authorize restore resume")
    transaction_dir = transaction_dir.resolve()
    expected_dir = (PRIVATE_BASE / spec.run_id / "live" / "restore").resolve()
    if transaction_dir != expected_dir:
        raise ContractError("restore resume transaction path is not canonical")
    state = transaction_dir.lstat()
    if (
        not stat.S_ISDIR(state.st_mode)
        or stat.S_IMODE(state.st_mode) != 0o700
    ):
        raise ContractError("restore resume transaction directory is not exact")
    result_path = transaction_dir / "result.json"
    if result_path.exists():
        return _validated_existing_restore_result(
            spec,
            result_path,
            cleanup_result.sha256,
        )
    intent_bound, intent, restore_indexes = _load_restore_intent(
        spec,
        cleanup_result,
        transaction_dir,
    )
    reserve_count, transfer_count, publish_count = _restore_started_counts(
        spec,
        transaction_dir,
        restore_indexes,
    )
    realpath, serial_sha = _find_target()
    if realpath != spec.bridge_realpath or serial_sha != USB_SERIAL_SHA256:
        raise ContractError("restore resume target differs from cleanup manifest")
    current_bridge = _require_bridge(realpath)
    _revalidate_source_closure(spec)
    try:
        recovery_available = {
            "proven": True,
            "receipt": _revalidate_recovery_availability(spec),
        }
    except Exception as exc:  # noqa: BLE001 - passive reconciliation continues
        recovery_available = {
            "proven": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
    resume_intent_path = transaction_dir / "resume-intent.json"
    resume_binding = {
        "schema": "a90_attended_sd_exact_rootfs_restore_resume_intent_v1",
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "cleanup_result_sha256": cleanup_result.sha256,
        "restore_intent_sha256": intent_bound.sha256,
        "restore_indexes": restore_indexes,
        "reserve_count": reserve_count,
        "transfer_count": transfer_count,
        "publish_count": publish_count,
        "transfer_retransmitted": False,
        "publish_retransmitted": False,
        "read_only_reconciliation": True,
        "resume_device_write": False,
    }
    if resume_intent_path.exists():
        _, existing = _load_private_record(
            resume_intent_path,
            "restore resume intent",
        )
        if existing != resume_binding:
            raise ContractError("restore resume intent changed")
    else:
        legacy.write_private_json_exclusive(resume_intent_path, resume_binding)
    reconciliation_path = transaction_dir / "resume-reconciliation.json"
    if reconciliation_path.exists():
        _, record = _load_private_record(
            reconciliation_path,
            "restore resume reconciliation",
        )
        if (
            set(record) != {"schema", "run_id", "result", "error", "device_write"}
            or record.get("schema")
            != "a90_attended_sd_exact_rootfs_restore_resume_reconciliation_v1"
            or record.get("run_id") != spec.run_id
            or record.get("device_write") is not False
        ):
            raise ContractError("restore resume reconciliation changed")
        reconciliation = _require_dict(
            record.get("result"),
            "restore resume reconciliation result",
        )
        reconciliation_error = record.get("error")
    else:
        try:
            reconciliation = _restore_reconciled(spec)
            reconciliation_error = None
        except Exception as exc:  # noqa: BLE001 - no restoration effect replays
            reconciliation = {
                "selected": ["unknown"] * len(spec.selected),
                "stages": ["unknown"] * len(spec.selected),
                "protected": "unknown",
                "work": "unknown",
            }
            reconciliation_error = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
        legacy.write_private_json_exclusive(
            reconciliation_path,
            {
                "schema": (
                    "a90_attended_sd_exact_rootfs_restore_"
                    "resume_reconciliation_v1"
                ),
                "run_id": spec.run_id,
                "result": reconciliation,
                "error": reconciliation_error,
                "device_write": False,
            },
        )
    health_path = transaction_dir / "resume-health.json"
    if health_path.exists():
        _, record = _load_private_record(health_path, "restore resume health")
        if (
            set(record) != {"schema", "run_id", "result", "error", "device_write"}
            or record.get("schema")
            != "a90_attended_sd_exact_rootfs_restore_resume_health_v1"
            or record.get("run_id") != spec.run_id
            or record.get("device_write") is not False
        ):
            raise ContractError("restore resume health changed")
        final_health = _require_dict(
            record.get("result"),
            "restore resume health result",
        )
        health_error = record.get("error")
    else:
        try:
            final_health = _recovery_health()
            health_error = None
        except Exception as exc:  # noqa: BLE001 - observation never replays recovery
            final_health = {"proven": False}
            health_error = {"type": type(exc).__name__, "message": str(exc)}
        legacy.write_private_json_exclusive(
            health_path,
            {
                "schema": "a90_attended_sd_exact_rootfs_restore_resume_health_v1",
                "run_id": spec.run_id,
                "result": final_health,
                "error": health_error,
                "device_write": False,
            },
        )
    result = _restore_result_value(
        spec,
        cleanup_result_sha256=cleanup_result.sha256,
        restore_indexes=restore_indexes,
        reserve_count=reserve_count,
        transfer_count=transfer_count,
        publish_count=publish_count,
        response_proven=False,
        error={
            "type": "HOST_PROCESS_TERMINATED_DURING_RESTORE",
            "message": (
                "restore result was absent; transfer and publish were not "
                "replayed and current state was classified read-only"
            ),
        },
        reconciliation=reconciliation,
        reconciliation_error=reconciliation_error,
        final_health=final_health,
        health_error=health_error,
        resumed_from_durable_restore=True,
        observation_bridge_process=current_bridge,
    )
    result["resume_device_write"] = False
    result["recovery_available"] = recovery_available
    legacy.write_private_json_exclusive(result_path, result)
    return result


def source_contract_issues() -> list[str]:
    issues: list[str] = []
    if MAX_SELECTED != 32 or SELECTION_RUN_ID_RE.fullmatch(
        "a90-v3406-debian-display-f1-20260801-10"
    ) is None:
        issues.append("dynamic selection contract changed")
    if (
        len(FIXED_PROTECTED) != 2
        or FIXED_PROTECTED[-1].sha256
        != "9f169b6b7008168e172fb4abda446440fbbbe443daa2a1c991d25c5ceeabc847"
    ):
        issues.append("protected set changed")
    fake = CleanupSpec(
        manifest_path=Path("/tmp/manifest"),
        manifest_sha256="0" * 64,
        run_id="a90-sd-cleanup-20260803-01",
        selected_run_ids=tuple(
            f"a90-v340{3 + index % 4}-"
            f"{'debian-display' if index % 4 == 3 else 'debian'}-f1-"
            f"20260801-{index + 1:02d}"
            for index in range(MAX_SELECTED)
        ),
        inventory=legacy.BoundFile(Path("/tmp/inventory"), 1, "0" * 64),
        bridge_realpath="/dev/ttyACM0",
        bridge_process={
            "pid": 1,
            "start_epoch_sec": 2,
            "script_path": str(SERIAL_TCP_BRIDGE),
            "script_sha256": "0" * 64,
            "script_mtime_ns": 1_000_000_000,
            "argv_sha256": "0" * 64,
            "forbidden_options_absent": True,
            "matching_processes": 1,
            "local_endpoint": "127.0.0.1:54321",
        },
        selected=tuple(
            ImageRecord(
                f"obsolete-fake-{index}",
                (
                    "/mnt/sdext/a90/runtime/debian-bookworm-arm64-"
                    + (
                        "phase2-display-v3406-keyed"
                        if index % 4 == 3
                        else f"d3-sysvinit-v340{3 + index % 4}-keyed"
                    )
                    + f"-20260801-{index + 1:02d}.img"
                ),
                IMAGE_SIZE,
                1,
                IMAGE_MODE,
                1,
                1,
                1000000 + index,
                hashlib.sha256(str(index).encode("ascii")).hexdigest(),
                legacy.BoundFile(
                    Path(f"/tmp/host-{index}"),
                    IMAGE_SIZE,
                    hashlib.sha256(str(index).encode("ascii")).hexdigest(),
                ),
            )
            for index in range(MAX_SELECTED)
        ),  # type: ignore[arg-type]
        protected=tuple(
            ImageRecord(
                item.role,
                item.device_path,
                IMAGE_SIZE,
                1,
                IMAGE_MODE,
                1,
                1,
                2000000 + index,
                item.sha256,
                None,
            )
            for index, item in enumerate(FIXED_PROTECTED)
        ),  # type: ignore[arg-type]
        source_closure={
            "restoration_staging": legacy.BoundFile(
                STAGING_RUNNER, 1, "0" * 64
            ),
            "restoration_tcpctl_host": legacy.BoundFile(
                TCPCTL_HOST, 1, "0" * 64
            ),
        },
        f1_result=legacy.BoundFile(Path("/tmp/f1"), 1, "0" * 64),
        d1_result=legacy.BoundFile(Path("/tmp/d1"), 1, "0" * 64),
        display_confirmation=legacy.BoundFile(
            Path("/tmp/display"),
            1,
            "0" * 64,
        ),
        recovery_manifest=legacy.BoundFile(Path("/tmp/recovery"), 1, "0" * 64),
        recovery_rollback=legacy.BoundFile(Path("/tmp/rollback"), 1, "0" * 64),
        recovery_profile=RECOVERY_PROFILE,
        recovery_serial_sha256="0" * 64,
        recovery_observer_device="192.0.2.2",
        restoration_evidence=tuple(
            (
                legacy.BoundFile(Path(f"/tmp/m{index}"), 1, "0" * 64),
                legacy.BoundFile(Path(f"/tmp/r{index}"), 1, "0" * 64),
            )
            for index in range(MAX_SELECTED)
        ),
    )
    cleanup = _cleanup_script(fake)
    cleanup_command = _cleanup_command(fake)
    if cleanup.count("/bin/busybox rm --") != 1:
        issues.append("cleanup does not contain exactly one unlink dispatch")
    for token in ("rm -r", "rm -f", " dd ", "fastboot", "odin", "format", "mkfs"):
        if token in cleanup:
            issues.append(f"forbidden cleanup token: {token}")
    if (
        _command_wire_bytes(cleanup_command) > MAX_CMDV1X_WIRE_BYTES
        or len(cleanup_command) != 8
    ):
        issues.append("MAX_SELECTED cleanup command is not one bounded frame")
    validation = "\n".join(
        (
            _preflight_filesystem_script(fake),
            _image_exact_script(),
            *_selected_use_guard_scripts(fake.selected[0], "selected-0"),
        )
    )
    for token in (
        "sha256sum",
        "[0-9]*/mountinfo",
        "block/loop*/loop/backing_file",
        "[0-9]*/fd/*",
        "[0-9]*/root",
        "stat -c",
    ):
        if token not in validation:
            issues.append(f"missing validation token: {token}")
    frame_commands = [
        _script_command(_preflight_filesystem_script(fake)),
        _script_command(
            _image_exact_script(),
            _image_exact_args(fake.selected[0], "selected-0"),
        ),
        *(
            _script_command(script)
            for script in _selected_use_guard_scripts(
                fake.selected[0], "selected-0"
            )
        ),
        _script_command(
            _selected_state_script(),
            _image_exact_args(fake.selected[0], "selected-0"),
        ),
        _script_command(
            _restore_selected_state_script(),
            (
                fake.selected[0].device_path,
                f"regular file|{IMAGE_SIZE}|{IMAGE_MODE}|1|"
                f"{fake.selected[0].st_dev}",
                fake.selected[0].sha256,
                "selected-0",
                "/mnt/sdext/a90/runtime/.a90-cleanup-restore-fake-0",
            ),
        ),
        _script_command(_filesystem_state_script()),
    ]
    for command in frame_commands:
        if _command_wire_bytes(command) > MAX_CMDV1X_WIRE_BYTES:
            issues.append("live read-only command exceeds bounded frame")
            break
    result_source = inspect.getsource(_cleanup_result_value)
    for token in ("free_space_proven", "_free_gain_bounds"):
        if token not in result_source:
            issues.append(f"missing final capacity proof: {token}")
    if "retry_unsafe=False" not in inspect.getsource(_remote):
        issues.append("transport no-retry binding changed")
    resume_source = inspect.getsource(resume_dispatched_cleanup)
    for token in (
        "_load_dispatched_cleanup_journal",
        "_read_reconciliation",
        "resumed_from_durable_dispatch=True",
        "resume_device_write",
    ):
        if token not in resume_source:
            issues.append(f"missing journal-only cleanup resume: {token}")
    if "execute_cleanup(" in resume_source or "_cleanup_script(" in resume_source:
        issues.append("cleanup resume can reach cleanup execution")
    bridge_source = inspect.getsource(_require_bridge)
    for token in (
        "SERIAL_TCP_BRIDGE",
        "forbidden_options_absent",
        "start_epoch_sec",
        "argv_sha256",
    ):
        if token not in bridge_source:
            issues.append(f"missing exact bridge generation proof: {token}")
    restore_source = inspect.getsource(execute_restore)
    restore_result_source = inspect.getsource(_restore_result_value)
    for token in (
        "cleanup result does not authorize exact restoration",
        "publish_retransmitted",
        "staging.remote_publish_script",
        "RECOVERY_PENDING_PARKED_RESTORE_NO_RETRY",
    ):
        if token not in restore_source and token not in restore_result_source:
            issues.append(f"missing restoration contract: {token}")
    if 'final_health.get("state") == "RESIDENT_HEALTHY"' not in restore_result_source:
        issues.append("restore PASS can accept nonresident final health")
    restore_resume_source = inspect.getsource(resume_started_restore)
    for token in (
        "_load_restore_intent",
        "_restore_started_counts",
        "_restore_reconciled",
        "resumed_from_durable_restore=True",
        "resume_device_write",
    ):
        if token not in restore_resume_source:
            issues.append(f"missing journal-only restore resume: {token}")
    for token in (
        "subprocess.run",
        "staging.transfer_command",
        "staging.remote_publish_script",
        "execute_restore(",
    ):
        if token in restore_resume_source:
            issues.append(f"restore resume can reach recovery effect: {token}")
    return issues


def inspect_spec(spec: CleanupSpec) -> dict[str, Any]:
    issues = source_contract_issues()
    return {
        "schema": SCHEMA,
        "mode": "host-only-inspection",
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "selected_paths": [item.device_path for item in spec.selected],
        "protected_paths": [item.device_path for item in spec.protected],
        "contract_issues": issues,
        "ready_for_attended_execution_binding": not issues,
        "device_contact": False,
        "device_write": False,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--capture-inventory", action="store_true")
    mode.add_argument("--build-manifest", action="store_true")
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--execute-cleanup", action="store_true")
    mode.add_argument("--execute-approved-cleanup", action="store_true")
    mode.add_argument("--resume-dispatched-cleanup", action="store_true")
    mode.add_argument("--execute-authorized-restore", action="store_true")
    mode.add_argument("--resume-started-restore", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--selected-run-id", action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--expect-inventory-sha256")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    parser.add_argument("--approval")
    parser.add_argument("--transaction-dir", type=Path)
    parser.add_argument("--cleanup-result", type=Path)
    parser.add_argument("--operator-attended", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.capture_inventory:
        if args.run_id is None or args.output is None:
            raise ContractError("inventory capture arguments are incomplete")
        value = capture_inventory(
            args.run_id,
            args.output,
            sorted(args.selected_run_id),
        )
    elif args.build_manifest:
        if (
            args.run_id is None
            or args.output is None
            or args.inventory is None
            or args.expect_inventory_sha256 is None
        ):
            raise ContractError("manifest build arguments are incomplete")
        value = build_manifest(
            run_id=args.run_id,
            inventory_path=args.inventory,
            inventory_sha256=args.expect_inventory_sha256,
            output=args.output,
        )
    else:
        if args.manifest is None or args.expect_manifest_sha256 is None:
            raise ContractError("manifest and expected SHA256 are required")
        spec = load_manifest(args.manifest, args.expect_manifest_sha256)
        if args.prepare_approval:
            value = prepare_approval(spec)
        elif args.resume_dispatched_cleanup:
            if args.transaction_dir is None:
                raise ContractError("cleanup resume arguments are incomplete")
            value = resume_dispatched_cleanup(
                spec,
                transaction_dir=args.transaction_dir,
            )
        elif args.execute_authorized_restore:
            if args.cleanup_result is None or args.transaction_dir is None:
                raise ContractError("restore arguments are incomplete")
            value = execute_restore(
                spec,
                cleanup_result_path=args.cleanup_result,
                transaction_dir=args.transaction_dir,
                operator_attended=args.operator_attended,
            )
        elif args.resume_started_restore:
            if args.cleanup_result is None or args.transaction_dir is None:
                raise ContractError("restore resume arguments are incomplete")
            value = resume_started_restore(
                spec,
                cleanup_result_path=args.cleanup_result,
                transaction_dir=args.transaction_dir,
            )
        elif args.execute_cleanup or args.execute_approved_cleanup:
            if args.transaction_dir is None:
                raise ContractError("live cleanup arguments are incomplete")
            value = execute_cleanup(
                spec,
                approval=args.approval,
                transaction_dir=args.transaction_dir,
                operator_attended=args.operator_attended,
            )
        else:
            value = inspect_spec(spec)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        ContractError,
        legacy.ContractError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(
            f"a90-obsolete-rootfs-cleanup-v1: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
