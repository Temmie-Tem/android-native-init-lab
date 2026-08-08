#!/usr/bin/env python3
"""Minimal manifest-driven A90 V3403 F1 transaction orchestrator.

This file does not implement a new transfer primitive.  It composes the
manifest-bound absent-only rootfs staging adapter and native_init_flash.py,
records candidate intent before the one candidate invocation, observes the
bounded Debian handoff, and owns the mandatory exact rollback.

The default mode is host-only inspection.  Live execution requires a final
prepared manifest, exact approval bindings, and an independently reviewed
orchestrator binding.  Recovery never invokes the candidate and never repeats
an already-recorded rollback invocation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_phase2d_display_observer as display  # noqa: E402
import a90ctl  # noqa: E402
import device_action_cdc_acm_observer_v1 as cdc_guard  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402


ORCHESTRATOR_SCHEMA = "a90_v3403_f1_orchestrator_v1"
JOURNAL_SCHEMA = "a90_v3403_f1_journal_v1"
APPROVAL_PREPARED_SCHEMA = "a90_v3403_f1_approval_prepared_v1"
APPROVAL_PREFIX = "A90-F1-V2-APPROVE:"
ATTENDED_WINDOW_SCHEMA = "a90_v3403_f1_attended_window_v1"
ATTENDED_CONTINUE_PREFIX = "A90-F1-ATTENDED-CONTINUE:"
DISPLAY_VISIBLE_SCHEMA = "a90_v3406_f1_display_visible_v1"
DISPLAY_VISIBLE_PREFIX = "A90-F1-DISPLAY-VISIBLE:"
FINAL_MANIFEST_SCHEMA = staging.FINAL_MANIFEST_SCHEMA
FINAL_MANIFEST_STATUS = staging.FINAL_MANIFEST_STATUS
PRIVATE_RUN_BASE = staging.PRIVATE_RUN_BASE
CANONICAL_EVENTS = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)
PROMOTION_EVENTS = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "resident_reboot_start",
    "resident_reboot_ready",
    "promotion_health_verified",
    "live_session_end",
)
TIMELINE_EVENT_ORDER = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "resident_reboot_start",
    "resident_reboot_ready",
    "promotion_health_verified",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)
HANDOFF_COMMAND = "switch-root-to-distro"
HANDOFF_TOKEN = "SERVER-DISTRO-D3B-SWITCHROOT"
OBSERVER_TRANSPORT_SCOPE = "USB-local NCM only"
PSTORE_ZERO_RE = staging.PSTORE_ZERO_RE
HEX64_RE = staging.HEX64_RE
NATIVE_FLASH_PATH = (REVAL_DIR / "native_init_flash.py").resolve()
CDC_GUARD_PATH = (
    REVAL_DIR / "device_action_cdc_acm_observer_v1.py"
).resolve()
CDC_GUARD_SIZE = 51402
CDC_GUARD_SHA256 = "6c8a6d2151928d2e098ca41b3c9dc24cdbbfabe9be10df19969be274744ef9a9"
STAGING_PATH = (SCRIPT_DIR / "a90_v3403_absent_only_staging.py").resolve()
OBSERVATION_OUTPUT_MARKERS = (
    "source_sha phase=initial",
    "source_sha phase=post-display-cleanup",
    # The work copy is gone: the source is mounted read-only and a fixed
    # writable set is mounted over it, so there is no copy to hash and no
    # copy to announce. These markers replace work-copy/post-copy-source and
    # work_copy=ready, and they assert more than those did -- the probe has
    # proved the root read-only and every writable path writable before the
    # switch.
    "writable_set=mounted",
    "writable_set=verified root=read-only",
    "evidence_bind=ok",
    "exec_switch_root_now",
)
F1_SERIAL_INPUT_MODE = "slow"
F1_SERIAL_INPUT_CHAR_DELAY_SEC = 0.02
F1_HANDOFF_MAX_PRE_READ_SEC = 5.0
F1_HANDOFF_SOURCE_SHA_PHASES = (
    "initial",
    "post-display-cleanup",
)
# The 2 GiB copy no longer happens, so its 300 s allowance would be pure
# slack, and slack is not free: an over-provisioned budget cannot detect the
# regression it exists to bound. Two full source hashes remain -- initial and
# post-display -- instead of four passes.
F1_HANDOFF_COPY_BOUND_SEC = 0
F1_HANDOFF_SHA_PASS_COUNT = len(F1_HANDOFF_SOURCE_SHA_PHASES)
F1_HANDOFF_SHA_ALLOWANCE_PER_PASS_SEC = 90
F1_HANDOFF_SWITCH_HELPER_BOUND_COUNT = 2
F1_HANDOFF_SWITCH_HELPER_BOUND_SEC = 30
# Native display cleanup stops autohud once, the dpublic presenter once, then
# at most 16 additional native DRM owners. Each DRM owner gets one bounded
# TERM wait and one bounded KILL wait. These values are mirrored by
# A90_D_HANDOFF_* in a90_server_distro.c and source-closure tests bind them.
F1_HANDOFF_DISPLAY_HUD_STOP_BOUND_SEC = 3
F1_HANDOFF_DISPLAY_DPRESENT_OWNER_BOUND_COUNT = 1
F1_HANDOFF_DISPLAY_OWNER_BOUND_COUNT = 16
F1_HANDOFF_DISPLAY_OWNER_WAIT_COUNT = 2
F1_HANDOFF_DISPLAY_OWNER_WAIT_SEC = 1
F1_HANDOFF_DISPLAY_PROC_SCAN_COUNT = 3
F1_HANDOFF_DISPLAY_PROC_ENTRY_BOUND_COUNT = 8192
# Native enforces this total with one monotonic deadline threaded through every
# /proc and per-fd scan as well as both bounded owner waits. The host budget is
# therefore the code-enforced ceiling, not an estimated per-scan allowance.
F1_HANDOFF_DISPLAY_TOTAL_BOUND_SEC = 127
F1_HANDOFF_DISPLAY_BOUND_SEC = F1_HANDOFF_DISPLAY_TOTAL_BOUND_SEC
F1_HANDOFF_MISC_ALLOWANCE_SEC = 90
F1_HANDOFF_MIN_READ_BUDGET_SEC = (
    F1_HANDOFF_COPY_BOUND_SEC
    + F1_HANDOFF_SHA_PASS_COUNT * F1_HANDOFF_SHA_ALLOWANCE_PER_PASS_SEC
    + F1_HANDOFF_SWITCH_HELPER_BOUND_COUNT
    * F1_HANDOFF_SWITCH_HELPER_BOUND_SEC
    + F1_HANDOFF_DISPLAY_BOUND_SEC
    + F1_HANDOFF_MISC_ALLOWANCE_SEC
)
F1_HANDOFF_MIN_TIMEOUT_SEC = (
    F1_HANDOFF_MIN_READ_BUDGET_SEC + int(F1_HANDOFF_MAX_PRE_READ_SEC)
)
OBSERVATION_MENU_SETTLE_SEC = 3.0
OBSERVATION_CHANNEL_CANARY = ("run", "/bin/busybox", "true")
RETURN_EPOCH_SCHEMA = "a90_host_usb_serial_epoch_v1"
HOST_NCM_PROFILE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
HOST_NCM_REBIND_TIMEOUT_SEC = 30
HOST_NCM_REBIND_POLL_SEC = 1.0
HOST_NCM_CONNECTION_TYPE = "802-3-ethernet"
HOST_NCM_REBIND_WORST_CASE_SEC = 155.0
MODEMMANAGER_GUARD_POST_RETURN_COMMAND_COUNT = 4
MODEMMANAGER_GUARD_PROMOTION_REMOTE_COMMAND_COUNT = 20
MODEMMANAGER_GUARD_PROMOTION_BRIDGE_COMMAND_COUNT = 6
MODEMMANAGER_GUARD_ROLLBACK_SOURCE_COMMAND_COUNT = 2
MODEMMANAGER_GUARD_ROLLBACK_HEALTH_COMMAND_COUNT = 5
MODEMMANAGER_GUARD_MARGIN_SEC = 60
EXACT_BRIDGE_PREFLIGHT_BUDGET_SEC = 30.0
MODEMMANAGER_GUARD_ARM_SCHEMA = "a90_modemmanager_guard_arm_v2"
MODEMMANAGER_GUARD_RECEIPT_KEYS = frozenset(
    {
        "schema",
        "status",
        "spec_sha256",
        "topology_sha256",
        "rule_sha256",
        "instance_sha256",
        "output_sha256",
        "child_alive",
    }
)
MODEMMANAGER_GUARD_CORRIDORS = frozenset(
    {
        "candidate-return",
        "resident-promotion",
        "rollback-recovery-1",
        "rollback-recovery-2",
    }
)
PSTORE_MOUNT_PATH = "/sys/fs/pstore"
PSTORE_ENTRY_RE = re.compile(
    r"^[dlcb?\-]\s+\S+\s+([A-Za-z0-9_.-]+)$"
)
PSTORE_PMSG_ENTRY_RE = re.compile(r"^pmsg-ramoops(?:-[0-9]+)?$")
PSTORE_EXPECTED_BOOT_ENTRY_RE = re.compile(
    r"^(?:console|pmsg)-ramoops(?:-[0-9]+)?$"
)
PSTORE_LISTING_CONTROL_RES = (
    re.compile(r"^cmdv1 ls /sys/fs/pstore$"),
    re.compile(
        r"^A90P1 BEGIN seq=[0-9]+ cmd=ls argc=2 flags=0x[0-9a-f]+$"
    ),
    re.compile(r"^\[done\] ls \([0-9]+ms\)$"),
    re.compile(
        r"^A90P1 END seq=[0-9]+ cmd=ls rc=0 errno=0 "
        r"duration_ms=[0-9]+ flags=0x[0-9a-f]+ status=ok$"
    ),
    re.compile(r"^a90:/# ?$"),
)
RETAINED_PMSG_MARKER = "A90D3RET_V3405"
RETAINED_PMSG_REQUIRED_PHASE = "phase=armed"
RETAINED_PMSG_OBSERVER_CONTRACT = "mount-read-fsync-exact-unlink-unmount-v1"
NCM_REBIND_IDENTITY = "same-current-acm-usb-parent-v1"
UNATTENDED_OBSERVATION_MODE = "unattended-single-shot-v1"
ATTENDED_OBSERVATION_MODE = "operator-attended-v1"
ATTENDED_WINDOW_SEC = 900
ATTENDED_PRE_HANDOFF_ATTEMPT_LIMIT = 3
ATTENDED_HANDOFF_ATTEMPT_LIMIT = 1
ATTENDED_RETRYABLE_CHANNEL_ERRORS = (
    "A90P1 END marker not found",
    "observation menu hide did not complete",
    "observation channel did not settle",
)
PHASE2_DISPLAY_PROFILE = "phase2-display-v1"
PHASE2_DISPLAY_VISIBLE_TEXT = (
    "A90 DEBIAN",
    "DIRECT DRM SESSION",
    "PID 1: SYSVINIT / VT: NONE",
    "DISPLAY OWNER: DEBIAN",
)
PHASE2_DISPLAY_UID = 3904
PHASE2_DISPLAY_GID = 3904
PHASE2_DISPLAY_MAX_ATTEMPTS = 3
DISPLAY_D3_BEGIN = "A90OBS_D3_BEGIN"
DISPLAY_D3_END = "A90OBS_D3_END"
DISPLAY_RELEASE_BEGIN = "A90OBS_RELEASE_BEGIN"
DISPLAY_RELEASE_END = "A90OBS_RELEASE_END"
DISPLAY_READY_BEGIN = "A90OBS_READY_BEGIN"
DISPLAY_READY_END = "A90OBS_READY_END"
DISPLAY_FAILURE_BEGIN = "A90OBS_FAILURE_BEGIN"
DISPLAY_FAILURE_END = "A90OBS_FAILURE_END"
DISPLAY_PRESENTER_LOG_BEGIN = "A90OBS_PRESENTER_LOG_BEGIN"
DISPLAY_PRESENTER_LOG_END = "A90OBS_PRESENTER_LOG_END"
DISPLAY_DIAGNOSTICS_BEGIN = "A90OBS_DISPLAY_DIAGNOSTICS_BEGIN"
DISPLAY_DIAGNOSTICS_END = "A90OBS_DISPLAY_DIAGNOSTICS_END"
RECOVERY_ADB_MARKER_RE = re.compile(
    r"(?:^|\] )ADB ready: ([^\s]+) recovery\r?$",
    re.MULTILINE,
)
UTC_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
SUCCESSFUL_STAGE_STATES = (
    "approval-binding-reopened",
    "connected-preflight",
    "stage-reserve-start",
    "stage-reserved",
    "payload-transfer-start",
    "payload-transfer-complete",
    "payload-verified",
    "publish-start",
    "published",
    "closed",
)


class ContractError(RuntimeError):
    """Raised when the immutable F1 transaction contract is not satisfied."""


@dataclass(frozen=True)
class F1Spec:
    stage: staging.StageSpec
    manifest: dict[str, Any]
    candidate: staging.BoundFile
    rollback: staging.BoundFile
    flash_runner: staging.BoundFile
    candidate_version: str
    candidate_build: str
    rollback_version: str
    rollback_build: str
    handoff_command: tuple[str, ...]
    observer_key: Path
    observer_public_key_sha256: str
    observer_device: str
    observer_port: int
    observer_host_ncm_profile: str
    candidate_boot_timeout: int
    handoff_timeout: int
    ssh_marker_timeout: int
    candidate_return_timeout: int
    rollback_boot_timeout: int
    observation_mode: str
    attended_window_sec: int
    pre_handoff_attempt_limit: int
    handoff_attempt_limit: int
    display_required: bool
    display_profile: str
    display_uid: int
    display_gid: int
    display_max_attempts: int
    display_visible_text: tuple[str, ...]
    recovery_serial_sha256: str
    recovery_serial: str
    recovery_evidence: tuple[staging.BoundFile, ...]
    orchestrator_size: int
    orchestrator_sha256: str
    candidate_first_boot: dict[str, Any] | None = None


@dataclass
class F1Model:
    history: list[str] = field(default_factory=list)
    candidate_attempts: int = 0
    rollback_attempts: int = 0
    rollback_required: bool = False
    observation_proven: bool = False
    final_health: bool = False
    closed: bool = False
    blocked: str | None = None


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def is_canonical_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or UTC_TIMESTAMP_RE.fullmatch(value) is None:
        return False
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value


def parse_utc_timestamp(value: Any, label: str) -> dt.datetime:
    if not is_canonical_utc_timestamp(value):
        raise ContractError(f"{label} is not canonical UTC")
    return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.UTC
    )


def current_utc() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


def _private_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise ContractError("short private JSON write")
        offset += written


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_private_json_exclusive(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}"
    )
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        _write_all(descriptor, _private_json_bytes(payload))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path, follow_symlinks=False)
        _fsync_directory(path.parent)
    except FileExistsError as exc:
        raise ContractError(f"private JSON already exists: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def write_private_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ContractError(f"private JSON destination is a symlink: {path}")
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}"
    )
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        _write_all(descriptor, _private_json_bytes(payload))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def sha256_file(path: Path) -> str:
    return staging.sha256_file(path)


def validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise ContractError(f"{label} must be a lowercase sha256")
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a non-empty string")
    return value


def require_positive_int(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ContractError(f"{label} must be a positive integer")
    return value


def validate_handoff_timeout(value: Any) -> int:
    timeout = require_positive_int(value, "observation.handoff_timeout_sec")
    if timeout < F1_HANDOFF_MIN_TIMEOUT_SEC:
        raise ContractError(
            "observation.handoff_timeout_sec must reserve the complete "
            f"V3403 handoff corridor (minimum {F1_HANDOFF_MIN_TIMEOUT_SEC}s)"
        )
    return timeout


def validate_observation_policy(
    observation: dict[str, Any],
) -> tuple[str, int, int, int]:
    mode = require_string(observation.get("mode"), "observation.mode")
    window = observation.get("attended_window_sec")
    attempts = observation.get("pre_handoff_attempt_limit")
    handoffs = observation.get("handoff_attempt_limit")
    if mode == ATTENDED_OBSERVATION_MODE:
        if type(window) is not int or window != ATTENDED_WINDOW_SEC:
            raise ContractError("attended window must be exactly 900 seconds")
        if (
            type(attempts) is not int
            or attempts != ATTENDED_PRE_HANDOFF_ATTEMPT_LIMIT
        ):
            raise ContractError("attended pre-handoff limit must be exactly 3")
        if (
            type(handoffs) is not int
            or handoffs != ATTENDED_HANDOFF_ATTEMPT_LIMIT
        ):
            raise ContractError("attended handoff limit must be exactly 1")
    elif mode == UNATTENDED_OBSERVATION_MODE:
        if (
            type(window) is not int
            or type(attempts) is not int
            or type(handoffs) is not int
            or window != 0
            or attempts != 1
            or handoffs != 1
        ):
            raise ContractError(
                "unattended observation must bind window=0 attempts=1 handoff=1"
            )
    else:
        raise ContractError("observation.mode is not a reviewed exact mode")
    return mode, window, attempts, handoffs


def validate_display_observation(
    manifest: dict[str, Any],
    observation: dict[str, Any],
    observation_mode: str,
) -> tuple[bool, str, int, int, int, tuple[str, ...]]:
    required = (
        manifest.get("schema") == staging.PHASE2_DISPLAY_MANIFEST_SCHEMA
    )
    value = observation.get("display")
    if not required:
        if value is not None:
            raise ContractError(
                "legacy manifest must not add the Phase 2 display contract"
            )
        return False, "", 0, 0, 0, ()
    if observation_mode != ATTENDED_OBSERVATION_MODE:
        raise ContractError(
            "Phase 2 display proof requires operator-attended observation"
        )
    item = _dict(value, "observation.display")
    expected_keys = {
        "profile",
        "native_release_schema",
        "native_release_marker_path",
        "ready_schema",
        "ready_marker_path",
        "failure_schema",
        "failure_marker_path",
        "display_uid",
        "display_gid",
        "max_attempts",
        "visible_text",
        "operator_visible_confirmation_required",
    }
    if set(item) != expected_keys:
        raise ContractError("Phase 2 display contract key set is not exact")
    visible = item.get("visible_text")
    if (
        item.get("profile") != PHASE2_DISPLAY_PROFILE
        or item.get("native_release_schema")
        != "a90-native-display-release-v1"
        or item.get("native_release_marker_path")
        != "/run/a90-native-display-release"
        or item.get("ready_schema") != "a90-debian-display-v1"
        or item.get("ready_marker_path") != "/run/a90-display/ready"
        or item.get("failure_schema")
        != "a90-debian-display-v1-failure"
        or item.get("failure_marker_path") != "/run/a90-display/failure"
        or type(item.get("display_uid")) is not int
        or item.get("display_uid") != PHASE2_DISPLAY_UID
        or type(item.get("display_gid")) is not int
        or item.get("display_gid") != PHASE2_DISPLAY_GID
        or type(item.get("max_attempts")) is not int
        or item.get("max_attempts") != PHASE2_DISPLAY_MAX_ATTEMPTS
        or not isinstance(visible, list)
        or tuple(visible) != PHASE2_DISPLAY_VISIBLE_TEXT
        or item.get("operator_visible_confirmation_required") is not True
    ):
        raise ContractError("Phase 2 display contract is not exact")
    return (
        True,
        PHASE2_DISPLAY_PROFILE,
        PHASE2_DISPLAY_UID,
        PHASE2_DISPLAY_GID,
        PHASE2_DISPLAY_MAX_ATTEMPTS,
        PHASE2_DISPLAY_VISIBLE_TEXT,
    )


def require_private_regular(path: Path, *, mode_mask: int = 0o077) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise ContractError(f"not a non-symlink regular file: {path}")
    if info.st_mode & mode_mask:
        raise ContractError(f"private input has excessive permissions: {path}")
    staging.require_below(path, staging.PRIVATE_ROOT, "private input")


def bound_by_label(stage_spec: staging.StageSpec, label: str) -> staging.BoundFile:
    matches = [item for item in stage_spec.bound_files if item.label == label]
    if len(matches) != 1:
        raise ContractError(f"bound closure must contain one {label}")
    return matches[0]


def private_bound_file(value: Any, label: str) -> staging.BoundFile:
    item = _dict(value, label)
    path_value = item.get("path")
    size_value = item.get("size")
    if not isinstance(path_value, str):
        raise ContractError(f"{label}.path is missing")
    if type(size_value) is not int or size_value <= 0:
        raise ContractError(f"{label}.size must be positive")
    bound = staging.BoundFile(
        label=label,
        path=Path(path_value).resolve(strict=True),
        size=size_value,
        sha256=validate_sha256(item.get("sha256"), f"{label}.sha256"),
    )
    staging.require_below(bound.path, staging.PRIVATE_ROOT, label)
    return bound


def recovery_serial_from_evidence(
    evidence: tuple[staging.BoundFile, ...],
    expected_sha256: str,
) -> str:
    if len(evidence) != 2:
        raise ContractError("recovery ADB identity requires exactly two evidence logs")
    serials: list[str] = []
    for bound in evidence:
        staging.require_regular_file(
            bound.path,
            expected_size=bound.size,
            expected_sha256=bound.sha256,
        )
        try:
            text = bound.path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ContractError(f"{bound.label} is not UTF-8 text") from exc
        matches = RECOVERY_ADB_MARKER_RE.findall(text)
        if len(matches) != 1:
            raise ContractError(
                f"{bound.label} must contain exactly one recovery ADB marker"
            )
        serials.append(matches[0])
    if serials[0] != serials[1]:
        raise ContractError("recovery ADB evidence logs select different targets")
    actual = hashlib.sha256(serials[0].encode("utf-8")).hexdigest()
    if actual != expected_sha256:
        raise ContractError("recovery ADB serial does not match the manifest digest")
    return serials[0]


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def validate_expected_boot(
    value: Any,
    label: str,
    bound: staging.BoundFile,
) -> tuple[str, str]:
    item = _dict(value, label)
    if item.get("partition") != "boot":
        raise ContractError(f"{label} partition must be boot")
    if Path(require_string(item.get("path"), f"{label}.path")).resolve() != bound.path:
        raise ContractError(f"{label} path does not match bound closure")
    if item.get("size") != bound.size or item.get("sha256") != bound.sha256:
        raise ContractError(f"{label} size/hash does not match bound closure")
    version = require_string(item.get("expected_version"), f"{label}.expected_version")
    build = require_string(item.get("expected_build"), f"{label}.expected_build")
    return version, build


def validate_candidate_first_boot_contract(
    value: Any,
    *,
    candidate_version: str,
    candidate_build: str,
    remote_final: str,
    rootfs_sha256: str,
) -> dict[str, Any] | None:
    h2_identity = (
        "0.11.170",
        "phase3-minimal-h2-two-phase-auto-benchmark",
    )
    h2_expected = {
        "schema": "a90-auto-handoff-first-boot-v1",
        "enable_path": "/cache/a90-auto-handoff-phase3-minimal-h2.enable",
        "latch_path": "/cache/a90-auto-handoff-phase3-minimal-h2.done",
        "pre_transfer_state": "both-absent",
        "post_boot_status": "binding=1-enable=0-latch=0",
        "post_boot_log": "A90AUTO state=unarmed-stay-native",
    }
    identity = (candidate_version, candidate_build)
    if identity == h2_identity:
        if value != h2_expected:
            raise ContractError("H2 candidate first-boot contract is not exact")
        return dict(h2_expected)
    compiled_identity_markers = {
        (
            "0.11.171",
            "phase3-minimal-h3-exact-binding-auto-benchmark",
        ): (
            "/cache/a90-auto-handoff-phase3-minimal-h3.enable",
            "/cache/a90-auto-handoff-phase3-minimal-h3.done",
        ),
        (
            "0.11.172",
            "phase3-minimal-h4-observer-complete-auto-benchmark",
        ): (
            "/cache/a90-auto-handoff-phase3-minimal-h4.enable",
            "/cache/a90-auto-handoff-phase3-minimal-h4.done",
        ),
        (
            "0.11.173",
            "phase3-minimal-h5-fresh-campaign-auto-benchmark",
        ): (
            "/cache/a90-auto-handoff-phase3-minimal-h5.enable",
            "/cache/a90-auto-handoff-phase3-minimal-h5.done",
        ),
        (
            "0.11.174",
            "phase3-minimal-h6-observer-complete-baseline-auto-benchmark",
        ): (
            "/cache/a90-auto-handoff-phase3-minimal-h6.enable",
            "/cache/a90-auto-handoff-phase3-minimal-h6.done",
        ),
        (
            "0.11.175",
            "phase3-minimal-h7-readonly-source-ondevice-evidence-auto-benchmark",
        ): (
            "/cache/a90-auto-handoff-phase3-minimal-h7.enable",
            "/cache/a90-auto-handoff-phase3-minimal-h7.done",
        ),
    }
    if identity in compiled_identity_markers:
        enable_path, latch_path = compiled_identity_markers[identity]
        binding = {
            "schema": "a90-compiled-auto-handoff-binding-v1",
            "candidate_version": candidate_version,
            "candidate_build": candidate_build,
            "image_path": remote_final,
            "image_sha256": rootfs_sha256,
            "enable_path": enable_path,
            "latch_path": latch_path,
        }
        binding["binding_sha256"] = json_sha256(binding)
        expected = {
            "schema": "a90-auto-handoff-first-boot-v2",
            "enable_path": binding["enable_path"],
            "latch_path": binding["latch_path"],
            "compiled_binding": binding,
            "pre_transfer_state": "both-absent",
            "post_boot_status": "binding=1-enable=0-latch=0",
            "post_boot_log": "A90AUTO state=unarmed-stay-native",
        }
        if value != expected:
            raise ContractError("compiled candidate/rootfs binding is not exact")
        return expected
    if value is not None:
        raise ContractError("non-auto candidate has an unexpected first-boot contract")
    return None


def load_spec(
    manifest_path: Path,
    expected_manifest_sha256: str,
    *,
    allow_draft: bool,
) -> tuple[F1Spec, list[str]]:
    stage_spec, manifest, issues = staging.stage_spec_from_manifest(
        manifest_path,
        expected_manifest_sha256,
        allow_draft=allow_draft,
    )
    candidate = bound_by_label(stage_spec, "candidate_boot")
    rollback = bound_by_label(stage_spec, "rollback_boot")
    flash_runner = bound_by_label(stage_spec, "transport")
    if flash_runner.path != NATIVE_FLASH_PATH:
        raise ContractError("flash runner is not native_init_flash.py")

    candidate_value = _dict(manifest.get("candidate_boot"), "candidate_boot")
    candidate_version, candidate_build = validate_expected_boot(
        candidate_value,
        "candidate_boot",
        candidate,
    )
    candidate_first_boot = validate_candidate_first_boot_contract(
        candidate_value.get("first_boot_contract"),
        candidate_version=candidate_version,
        candidate_build=candidate_build,
        remote_final=stage_spec.remote_final,
        rootfs_sha256=stage_spec.local_sha256,
    )
    rollback_version, rollback_build = validate_expected_boot(
        manifest.get("rollback_boot"),
        "rollback_boot",
        rollback,
    )
    if (
        rollback_version != staging.EXPECTED_BASELINE_VERSION
        or rollback_build != staging.EXPECTED_BASELINE_BUILD
    ):
        raise ContractError("rollback is not the exact V2321 baseline")

    rootfs = _dict(manifest.get("debian_rootfs"), "debian_rootfs")
    handoff_value = rootfs.get("handoff_command")
    if not isinstance(handoff_value, list) or not all(
        isinstance(item, str) for item in handoff_value
    ):
        raise ContractError("debian_rootfs.handoff_command must be a string array")
    handoff = tuple(handoff_value)
    expected_handoff = (
        HANDOFF_COMMAND,
        HANDOFF_TOKEN,
        stage_spec.remote_final,
        stage_spec.local_sha256,
    )
    if handoff != expected_handoff:
        raise ContractError("handoff command is not the exact V3403 immutable contract")

    run_root = (PRIVATE_RUN_BASE / stage_spec.run_id).resolve()
    observer = _dict(rootfs.get("observer"), "debian_rootfs.observer")
    observer_key = Path(
        require_string(observer.get("private_key_path"), "observer.private_key_path")
    ).resolve(strict=True)
    if observer_key.parent != run_root:
        raise ContractError("observer private key must be directly inside the run directory")
    require_private_regular(observer_key)
    observer_public_key_sha256 = validate_sha256(
        observer.get("public_key_sha256"),
        "observer.public_key_sha256",
    )
    public_key = observer_key.with_suffix(observer_key.suffix + ".pub")
    require_private_regular(public_key, mode_mask=0o022)
    if sha256_file(public_key) != observer_public_key_sha256:
        raise ContractError("observer public key sha256 mismatch")
    if observer.get("transport_scope") != OBSERVER_TRANSPORT_SCOPE:
        raise ContractError("observer transport must be USB-local NCM")
    if observer.get("wifi_or_external_network") is not False:
        raise ContractError("observer must not use Wi-Fi or an external network")
    observer_device = require_string(observer.get("device_ip"), "observer.device_ip")
    observer_port = require_positive_int(observer.get("device_port"), "observer.device_port")
    observer_host_ncm_profile = require_string(
        observer.get("host_ncm_profile"),
        "observer.host_ncm_profile",
    )
    if HOST_NCM_PROFILE_RE.fullmatch(observer_host_ncm_profile) is None:
        raise ContractError("observer.host_ncm_profile is not an exact safe name")
    if observer.get("ncm_rebind_identity") != NCM_REBIND_IDENTITY:
        raise ContractError("observer NCM rebind identity is not the reviewed contract")
    if (
        observer.get("retained_pmsg_marker") != RETAINED_PMSG_MARKER
        or observer.get("retained_pmsg_required_phase")
        != RETAINED_PMSG_REQUIRED_PHASE
        or observer.get("retained_pmsg_observer_contract")
        != RETAINED_PMSG_OBSERVER_CONTRACT
        or observer.get("retained_pmsg_cleanup_after_private_fsync") is not True
    ):
        raise ContractError("observer retained pmsg contract is not exact")

    observation = _dict(manifest.get("observation"), "observation")
    candidate_boot_timeout = require_positive_int(
        observation.get("candidate_boot_timeout_sec"),
        "observation.candidate_boot_timeout_sec",
    )
    handoff_timeout = validate_handoff_timeout(
        observation.get("handoff_timeout_sec")
    )
    ssh_marker_timeout = require_positive_int(
        observation.get("ssh_marker_timeout_sec"),
        "observation.ssh_marker_timeout_sec",
    )
    candidate_return_timeout = require_positive_int(
        observation.get("candidate_return_timeout_sec"),
        "observation.candidate_return_timeout_sec",
    )
    rollback_boot_timeout = require_positive_int(
        observation.get("rollback_boot_timeout_sec"),
        "observation.rollback_boot_timeout_sec",
    )
    (
        observation_mode,
        attended_window_sec,
        pre_handoff_attempt_limit,
        handoff_attempt_limit,
    ) = validate_observation_policy(observation)
    (
        display_required,
        display_profile,
        display_uid,
        display_gid,
        display_max_attempts,
        display_visible_text,
    ) = validate_display_observation(
        manifest,
        observation,
        observation_mode,
    )

    target = _dict(manifest.get("target"), "target")
    recovery_serial_sha256_value = target.get("recovery_adb_serial_sha256")
    recovery_evidence: tuple[staging.BoundFile, ...] = ()
    recovery_serial = ""
    if recovery_serial_sha256_value is None and allow_draft:
        recovery_serial_sha256 = ""
        issues.append("final manifest lacks recovery_adb_serial_sha256")
    else:
        recovery_serial_sha256 = validate_sha256(
            recovery_serial_sha256_value,
            "target.recovery_adb_serial_sha256",
        )
    evidence_value = target.get("recovery_adb_identity_evidence")
    if not isinstance(evidence_value, dict):
        issues.append("final manifest lacks bound recovery ADB identity evidence")
    elif recovery_serial_sha256:
        try:
            recovery_evidence = (
                private_bound_file(
                    evidence_value.get("candidate_recovery_log"),
                    "target.recovery_adb_identity_evidence.candidate_recovery_log",
                ),
                private_bound_file(
                    evidence_value.get("rollback_recovery_log"),
                    "target.recovery_adb_identity_evidence.rollback_recovery_log",
                ),
            )
            recovery_serial = recovery_serial_from_evidence(
                recovery_evidence,
                recovery_serial_sha256,
            )
        except (ContractError, FileNotFoundError) as exc:
            if not allow_draft:
                raise
            issues.append(f"recovery ADB identity evidence is not final: {exc}")
            recovery_evidence = ()
            recovery_serial = ""

    rootfs_staging = _dict(manifest.get("rootfs_staging"), "rootfs_staging")
    if rootfs_staging.get("independent_review_passed") is not True:
        issues.append("staging independent safety review is not passed")

    authority = _dict(manifest.get("authority"), "authority")
    for name in (
        "candidate_transfer_authorized",
        "live_authority",
        "rootfs_staging_authorized",
    ):
        if authority.get(name) is not False:
            issues.append(f"authority.{name} must remain false before approval")
    for name in (
        "fresh_operator_approval_required",
        "rollback_authority_activates_after_candidate_start",
    ):
        if authority.get(name) is not True:
            issues.append(f"authority.{name} is not true")
    if authority.get("manifest_grants_live_authority") is not False:
        issues.append("authority.manifest_grants_live_authority must be false")

    orchestrator = manifest.get("f1_orchestrator")
    orchestrator_size = 0
    orchestrator_sha256 = ""
    if not isinstance(orchestrator, dict):
        issues.append("final manifest lacks f1_orchestrator binding")
    else:
        orchestrator_path = orchestrator.get("path")
        if not isinstance(orchestrator_path, str):
            issues.append("f1_orchestrator.path is missing")
        else:
            try:
                selected_path = Path(orchestrator_path).resolve(strict=True)
            except FileNotFoundError:
                issues.append("f1_orchestrator.path is absent")
            else:
                if selected_path != Path(__file__).resolve():
                    issues.append("f1_orchestrator.path does not select this source")
        size_value = orchestrator.get("size")
        sha_value = orchestrator.get("sha256")
        if type(size_value) is not int or size_value <= 0:
            issues.append("f1_orchestrator.size is not bound")
        else:
            orchestrator_size = size_value
        if not isinstance(sha_value, str) or HEX64_RE.fullmatch(sha_value) is None:
            issues.append("f1_orchestrator.sha256 is not bound")
        else:
            orchestrator_sha256 = sha_value
            if sha_value != sha256_file(Path(__file__).resolve()):
                issues.append("f1_orchestrator.sha256 does not match this source")
        if orchestrator.get("independent_review_passed") is not True:
            issues.append("orchestrator independent safety review is not passed")
        if orchestrator.get("status") != "reviewed-ready":
            issues.append("f1_orchestrator.status is not reviewed-ready")

    if manifest.get("readiness_blockers") not in ([], None):
        issues.append("final manifest still declares readiness blockers")
    if not allow_draft and issues:
        raise ContractError("; ".join(issues))

    return (
        F1Spec(
            stage=stage_spec,
            manifest=manifest,
            candidate=candidate,
            rollback=rollback,
            flash_runner=flash_runner,
            candidate_version=candidate_version,
            candidate_build=candidate_build,
            rollback_version=rollback_version,
            rollback_build=rollback_build,
            handoff_command=handoff,
            observer_key=observer_key,
            observer_public_key_sha256=observer_public_key_sha256,
            observer_device=observer_device,
            observer_port=observer_port,
            observer_host_ncm_profile=observer_host_ncm_profile,
            candidate_boot_timeout=candidate_boot_timeout,
            handoff_timeout=handoff_timeout,
            ssh_marker_timeout=ssh_marker_timeout,
            candidate_return_timeout=candidate_return_timeout,
            rollback_boot_timeout=rollback_boot_timeout,
            observation_mode=observation_mode,
            attended_window_sec=attended_window_sec,
            pre_handoff_attempt_limit=pre_handoff_attempt_limit,
            handoff_attempt_limit=handoff_attempt_limit,
            display_required=display_required,
            display_profile=display_profile,
            display_uid=display_uid,
            display_gid=display_gid,
            display_max_attempts=display_max_attempts,
            display_visible_text=display_visible_text,
            recovery_serial_sha256=recovery_serial_sha256,
            recovery_serial=recovery_serial,
            recovery_evidence=recovery_evidence,
            orchestrator_size=orchestrator_size,
            orchestrator_sha256=orchestrator_sha256,
            candidate_first_boot=candidate_first_boot,
        ),
        issues,
    )


def verify_local_closure(spec: F1Spec) -> None:
    staging.verify_local_closure(spec.stage)
    staging.require_regular_file(
        spec.candidate.path,
        expected_size=spec.candidate.size,
        expected_sha256=spec.candidate.sha256,
    )
    staging.require_regular_file(
        spec.rollback.path,
        expected_size=spec.rollback.size,
        expected_sha256=spec.rollback.sha256,
    )
    staging.require_regular_file(
        spec.flash_runner.path,
        expected_size=spec.flash_runner.size,
        expected_sha256=spec.flash_runner.sha256,
    )
    for item in spec.recovery_evidence:
        staging.require_regular_file(
            item.path,
            expected_size=item.size,
            expected_sha256=item.sha256,
        )
    if not spec.recovery_serial:
        raise ContractError("exact recovery ADB target is not available")
    if (
        hashlib.sha256(spec.recovery_serial.encode("utf-8")).hexdigest()
        != spec.recovery_serial_sha256
    ):
        raise ContractError("in-memory recovery ADB target lost its manifest binding")
    staging.require_regular_file(
        Path(__file__).resolve(),
        expected_size=spec.orchestrator_size,
        expected_sha256=spec.orchestrator_sha256,
    )
    if Path(cdc_guard.__file__).resolve() != CDC_GUARD_PATH:
        raise ContractError("ModemManager guard import path lost its binding")
    staging.require_regular_file(
        CDC_GUARD_PATH,
        expected_size=CDC_GUARD_SIZE,
        expected_sha256=CDC_GUARD_SHA256,
    )
    require_private_regular(spec.observer_key)


def exact_transaction_dir(spec: F1Spec, requested: Path) -> Path:
    expected = (PRIVATE_RUN_BASE / spec.stage.run_id / "f1-live").resolve()
    actual = requested.resolve()
    if actual != expected:
        raise ContractError(f"transaction_dir must be the exact private path: {expected}")
    staging.require_below(actual, PRIVATE_RUN_BASE, "transaction_dir")
    return actual


def append_record(
    journal_dir: Path,
    state: str,
    action: str,
    payload: dict[str, Any],
    *,
    manifest_sha256: str,
    run_id: str,
    timestamp_utc: str | None = None,
) -> Path:
    journal_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    existing = sorted(journal_dir.glob("*.json"))
    sequence = len(existing)
    path = journal_dir / f"{sequence:04d}-{action}.json"
    record_timestamp = timestamp_utc or utc_now()
    if not is_canonical_utc_timestamp(record_timestamp):
        raise ContractError("journal timestamp is not canonical UTC")
    body = {
        **payload,
        "schema": JOURNAL_SCHEMA,
        "sequence": sequence,
        "timestamp_utc": record_timestamp,
        "run_id": run_id,
        "manifest_sha256": manifest_sha256,
        "state": state,
        "action": action,
    }
    write_private_json_exclusive(path, body)
    return path


def read_journal(spec: F1Spec, transaction_dir: Path) -> list[dict[str, Any]]:
    journal_dir = transaction_dir / "journal"
    paths = sorted(journal_dir.glob("*.json"))
    if not paths:
        raise ContractError("transaction journal is absent")
    records: list[dict[str, Any]] = []
    for sequence, path in enumerate(paths):
        expected_prefix = f"{sequence:04d}-"
        if not path.name.startswith(expected_prefix):
            raise ContractError("transaction journal sequence is not contiguous")
        require_private_regular(path)
        value = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("schema") != JOURNAL_SCHEMA
            or type(value.get("sequence")) is not int
            or value.get("sequence") != sequence
            or value.get("run_id") != spec.stage.run_id
            or value.get("manifest_sha256") != spec.stage.manifest_sha256
            or not is_canonical_utc_timestamp(value.get("timestamp_utc"))
            or not isinstance(value.get("state"), str)
            or not value.get("state")
            or not isinstance(value.get("action"), str)
            or not value.get("action")
        ):
            raise ContractError(f"invalid journal record: {path}")
        if path.name != f"{sequence:04d}-{value.get('action')}.json":
            raise ContractError(f"journal filename/action mismatch: {path}")
        records.append(value)
    return records


def write_private_json(path: Path, payload: Any) -> None:
    write_private_json_atomic(path, payload)


def load_timeline(
    transaction_dir: Path,
    *,
    allow_promotion: bool = False,
) -> list[dict[str, str]]:
    path = transaction_dir / "timeline.json"
    if not path.exists():
        return []
    value = json.loads(path.read_text(encoding="utf-8"))
    events = value.get("events") if isinstance(value, dict) else None
    if not isinstance(events, list):
        raise ContractError("timeline events are invalid")
    if any(
        not isinstance(event, dict)
        or set(event) != {"name", "timestamp_utc"}
        or not isinstance(event.get("name"), str)
        or not isinstance(event.get("timestamp_utc"), str)
        for event in events
    ):
        raise ContractError("timeline contains an invalid event")
    names = [event["name"] for event in events]
    order = TIMELINE_EVENT_ORDER if allow_promotion else CANONICAL_EVENTS
    try:
        positions = [order.index(str(name)) for name in names]
    except ValueError as exc:
        raise ContractError("timeline contains a non-canonical event") from exc
    if positions != sorted(set(positions)):
        raise ContractError("timeline is not in canonical order")
    return events


def add_event(
    transaction_dir: Path,
    events: list[dict[str, str]],
    name: str,
    *,
    allow_promotion: bool = False,
) -> None:
    order = TIMELINE_EVENT_ORDER if allow_promotion else CANONICAL_EVENTS
    if name not in order:
        raise ContractError(f"non-canonical timeline event: {name!r}")
    names = [event.get("name") for event in events]
    if name in names:
        raise ContractError(f"duplicate timeline event: {name!r}")
    if names and order.index(name) <= order.index(str(names[-1])):
        raise ContractError(f"timeline event out of order: {name!r}")
    events.append({"name": name, "timestamp_utc": utc_now()})
    write_private_json(transaction_dir / "timeline.json", {"events": events})


def ensure_event(
    transaction_dir: Path,
    events: list[dict[str, str]],
    name: str,
    *,
    allow_promotion: bool = False,
) -> None:
    if name in [event.get("name") for event in events]:
        return
    add_event(
        transaction_dir,
        events,
        name,
        allow_promotion=allow_promotion,
    )


JOURNAL_EVENT_ACTIONS = {
    "live_session_start": ("preflight",),
    "candidate_flash_start": ("candidate-transfer-started",),
    "candidate_flash_done": ("candidate-flashed",),
    "candidate_boot_ready": ("candidate-boot-ready",),
    "resident_reboot_start": ("resident-reboot-intent",),
    "resident_reboot_ready": ("resident-rebooted",),
    "promotion_health_verified": ("resident-health-verified",),
    "rollback_flash_start": ("rollback-transfer-started",),
    "rollback_flash_done": (
        "rollback-flashed",
        "rollback-completion-recovered-by-health",
    ),
    "rollback_boot_ready": ("rollback-boot-ready",),
    "live_session_end": ("closed", "aborted-before-candidate"),
}


def repair_timeline_from_journal(
    transaction_dir: Path,
    records: list[dict[str, Any]],
    *,
    allow_promotion: bool = False,
) -> list[dict[str, str]]:
    existing = load_timeline(
        transaction_dir,
        allow_promotion=allow_promotion,
    )
    existing_by_name = {event["name"]: event["timestamp_utc"] for event in existing}
    timestamps: dict[str, str] = {}
    for event_name, actions in JOURNAL_EVENT_ACTIONS.items():
        for record in records:
            if record.get("action") in actions:
                timestamps[event_name] = str(record["timestamp_utc"])
                break
    repaired: list[dict[str, str]] = []
    order = TIMELINE_EVENT_ORDER if allow_promotion else CANONICAL_EVENTS
    for name in order:
        if name not in timestamps:
            continue
        repaired.append(
            {
                "name": name,
                "timestamp_utc": existing_by_name.get(name, timestamps[name]),
            }
        )
    if repaired != existing:
        write_private_json(transaction_dir / "timeline.json", {"events": repaired})
    return repaired


def command_record(path: Path, returncode: int) -> dict[str, Any]:
    return {
        "returncode": returncode,
        "raw_log": str(path),
        "raw_log_size": path.stat().st_size,
        "raw_log_sha256": sha256_file(path),
    }


def classify_flash_log(path: Path) -> dict[str, bool]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "local_image_validated": (
            "phase.native_init_flash.inspect_local_image." in text
            and "phase.native_init_flash.inspect_local_image.elapsed_sec=" in text
            and "ok=1" in text.split(
                "phase.native_init_flash.inspect_local_image.elapsed_sec=",
                1,
            )[1].splitlines()[0]
        ),
        "native_recovery_requested": (
            "phase.native_init_flash.native_to_recovery.elapsed_sec=" in text
        ),
        "recovery_endpoint_selected": RECOVERY_ADB_MARKER_RE.search(text) is not None,
        "payload_transfer_started": "phase.native_init_flash.adb_push.elapsed_sec=" in text,
        "boot_write_started": "phase.native_init_flash.boot_dd_write.elapsed_sec=" in text,
        "boot_write_completed": (
            "phase.native_init_flash.boot_dd_write.elapsed_sec=" in text
            and "ok=1" in text.split(
                "phase.native_init_flash.boot_dd_write.elapsed_sec=",
                1,
            )[1].splitlines()[0]
        ),
        "readback_completed": (
            "phase.native_init_flash.boot_readback_sha256.elapsed_sec=" in text
            and "ok=1" in text.split(
                "phase.native_init_flash.boot_readback_sha256.elapsed_sec=",
                1,
            )[1].splitlines()[0]
        ),
    }


def run_logged(
    command: list[str],
    *,
    log_path: Path,
    timeout: float,
) -> dict[str, Any]:
    descriptor = os.open(
        log_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    execution_error: dict[str, Any] | None = None
    process_started = False
    returncode: int
    with os.fdopen(descriptor, "wb") as output:
        try:
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                stdout=output,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
            process_started = True
            returncode = completed.returncode
        except subprocess.TimeoutExpired:
            process_started = True
            returncode = 124
            execution_error = {
                "type": "TimeoutExpired",
                "stage": "process-wait",
                "timeout_sec": timeout,
            }
        except OSError as exc:
            returncode = 125
            execution_error = {
                "type": "OSError",
                "stage": "process-spawn",
                "errno": exc.errno,
            }
        finally:
            output.flush()
            os.fsync(output.fileno())
    record = command_record(log_path, returncode)
    record["process_started"] = process_started
    if execution_error is not None:
        record["execution_error"] = execution_error
    return record


def candidate_failure_is_definite_pre_session(record: dict[str, Any]) -> bool:
    classification = record.get("phase_classification")
    if not isinstance(classification, dict):
        raise ContractError("candidate failure lacks phase classification")
    if any(
        classification.get(name) is True
        for name in (
            "native_recovery_requested",
            "recovery_endpoint_selected",
            "payload_transfer_started",
            "boot_write_started",
        )
    ):
        return False
    execution_error = record.get("execution_error")
    if (
        isinstance(execution_error, dict)
        and execution_error.get("type") == "TimeoutExpired"
    ):
        return False
    if record.get("process_started") is False:
        return (
            isinstance(execution_error, dict)
            and execution_error.get("stage") == "process-spawn"
        )
    return execution_error is None


def json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def approval_binding(spec: F1Spec) -> dict[str, Any]:
    connected_d0 = bound_by_label(spec.stage, "target.connected_d0_result")
    connected_paths = bound_by_label(
        spec.stage,
        "target.connected_path_preflight",
    )
    hashes = {
        "manifest_sha256": spec.stage.manifest_sha256,
        "orchestrator_sha256": sha256_file(Path(__file__).resolve()),
        "staging_adapter_sha256": spec.stage.adapter_sha256,
        "flash_runner_sha256": spec.flash_runner.sha256,
        "candidate_boot_sha256": spec.candidate.sha256,
        "rollback_boot_sha256": spec.rollback.sha256,
        "rootfs_sha256": spec.stage.local_sha256,
        "connected_d0_sha256": connected_d0.sha256,
        "connected_path_preflight_sha256": connected_paths.sha256,
        "recovery_adb_serial_sha256": spec.recovery_serial_sha256,
    }
    if staging.RUN_ID_RE.fullmatch(spec.stage.run_id) is None:
        raise ContractError("approval binding run_id is not exact")
    for label, value in hashes.items():
        staging.validate_sha256(value, f"approval binding {label}")
    if (
        spec.manifest.get("schema")
        == staging.PRESERVED_ROOTFS_INSTALL_MANIFEST_SCHEMA
    ):
        policy = (
            spec.attended_window_sec,
            spec.pre_handoff_attempt_limit,
            spec.handoff_attempt_limit,
        )
        if (
            spec.observation_mode != UNATTENDED_OBSERVATION_MODE
            or any(type(value) is not int for value in policy)
            or policy != (0, 0, 0)
        ):
            raise ContractError("preserved-rootfs approval requires zero handoff authority")
        return {
            "schema": "a90_resident_existing_rootfs_approval_binding_v1",
            "run_id": spec.stage.run_id,
            **hashes,
            "observation_mode": spec.observation_mode,
            "attended_window_sec": 0,
            "pre_handoff_attempt_limit": 0,
            "handoff_attempt_limit": 0,
            "candidate_attempt_limit": 1,
            "mandatory_rollback_preapproved_after_candidate_start": True,
            "candidate_replay": False,
            "only_partition_payload": "boot",
            "rootfs_payload_forbidden": True,
            "handoff_forbidden": True,
        }
    return staging.canonical_f1_approval_binding(
        run_id=spec.stage.run_id,
        **hashes,
        observation_mode=spec.observation_mode,
        attended_window_sec=spec.attended_window_sec,
        pre_handoff_attempt_limit=spec.pre_handoff_attempt_limit,
        handoff_attempt_limit=spec.handoff_attempt_limit,
    )


def approval_prepared_path(spec: F1Spec) -> Path:
    return (
        PRIVATE_RUN_BASE
        / spec.stage.run_id
        / "approval-prepared.json"
    ).resolve()


def prepare_approval(spec: F1Spec) -> dict[str, Any]:
    verify_local_closure(spec)
    binding = approval_binding(spec)
    binding_sha256 = json_sha256(binding)
    prepared = {
        "schema": APPROVAL_PREPARED_SCHEMA,
        "created_utc": utc_now(),
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "approval_binding": binding,
        "approval_binding_sha256": binding_sha256,
        "approval_token": APPROVAL_PREFIX + binding_sha256,
        "device_contact": False,
        "device_write": False,
        "f1_authorized": False,
        "live_authorized": False,
    }
    write_private_json_exclusive(approval_prepared_path(spec), prepared)
    return prepared


def load_approval_prepared(spec: F1Spec) -> dict[str, Any]:
    path = approval_prepared_path(spec)
    require_private_regular(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    expected_keys = {
        "schema",
        "created_utc",
        "run_id",
        "manifest_sha256",
        "approval_binding",
        "approval_binding_sha256",
        "approval_token",
        "device_contact",
        "device_write",
        "f1_authorized",
        "live_authorized",
    }
    binding = approval_binding(spec)
    binding_sha256 = json_sha256(binding)
    if (
        not isinstance(value, dict)
        or set(value) != expected_keys
        or value.get("schema") != APPROVAL_PREPARED_SCHEMA
        or value.get("run_id") != spec.stage.run_id
        or value.get("manifest_sha256") != spec.stage.manifest_sha256
        or value.get("approval_binding") != binding
        or value.get("approval_binding_sha256") != binding_sha256
        or value.get("approval_token") != APPROVAL_PREFIX + binding_sha256
        or any(
            value.get(name) is not False
            for name in (
                "device_contact",
                "device_write",
                "f1_authorized",
                "live_authorized",
            )
        )
    ):
        raise ContractError("prepared approval binding does not match exact closure")
    return value


def approved_bindings(
    spec: F1Spec,
    args: argparse.Namespace,
    *,
    recovery: bool,
) -> dict[str, Any]:
    if (
        spec.manifest.get("schema")
        != staging.selected_manifest_schema(
            spec.manifest,
            spec.stage.run_id,
        )
    ):
        raise ContractError("live F1 refuses a non-final manifest schema")
    if spec.manifest.get("status") != FINAL_MANIFEST_STATUS:
        raise ContractError("live F1 refuses a non-ready manifest status")
    prepared = load_approval_prepared(spec)
    if recovery:
        if args.approval is not None:
            raise ContractError("rollback recovery must not require a second approval")
    elif args.approval != prepared["approval_token"]:
        raise ContractError("fresh exact F1 approval token mismatch")
    return prepared


def require_consumed_approval(
    records: list[dict[str, Any]],
    approval_prepared: dict[str, Any],
) -> None:
    approved_records = [
        record for record in records if record.get("action") == "approved"
    ]
    if (
        len(approved_records) != 1
        or approved_records[0].get("approval_binding_sha256")
        != approval_prepared["approval_binding_sha256"]
        or approved_records[0].get("approval_token_sha256")
        != hashlib.sha256(
            str(approval_prepared["approval_token"]).encode("utf-8")
        ).hexdigest()
    ):
        raise ContractError("transaction lacks the exact consumed approval binding")


def validate_attended_candidate_closure(
    spec: F1Spec,
    approval_prepared: dict[str, Any],
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> None:
    actions = action_names(records)
    expected_prefix = [
        "preflight",
        "approved",
        "staging-started",
        "rootfs-staged",
        "rootfs-candidate-preflight",
        "candidate-transfer-started",
        "candidate-flashed",
        "attended-window-open",
    ]
    if actions[:len(expected_prefix)] != expected_prefix:
        raise ContractError("attended candidate journal prefix is not exact")
    common_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
    }
    approved = records[1]
    candidate_start = records[5]
    candidate_flashed = records[6]
    window = records[7]
    approved_keys = common_keys | {
        "approval_consumed",
        "candidate_attempted",
        "rollback_pre_authorized",
        "approval_token_sha256",
        "approval_binding_sha256",
        "orchestrator_sha256",
    }
    start_keys = common_keys | {
        "candidate_attempted",
        "candidate_sha256",
        "candidate_transfer_count_max",
        "rollback_required",
        "candidate_replay",
    }
    flashed_keys = common_keys | {
        "candidate_sha256",
        "candidate_transfer_count",
        "candidate_replay",
        "rollback_required",
        "record",
    }
    approval_token_sha256 = hashlib.sha256(
        str(approval_prepared["approval_token"]).encode("utf-8")
    ).hexdigest()
    if (
        set(approved) != approved_keys
        or approved.get("state") != "APPROVED"
        or approved.get("approval_consumed") is not True
        or approved.get("candidate_attempted") is not False
        or approved.get("rollback_pre_authorized") is not True
        or approved.get("approval_token_sha256") != approval_token_sha256
        or approved.get("approval_binding_sha256")
        != approval_prepared["approval_binding_sha256"]
        or approved.get("orchestrator_sha256") != spec.orchestrator_sha256
        or set(candidate_start) != start_keys
        or candidate_start.get("state") != "APPROVED"
        or candidate_start.get("candidate_attempted") is not True
        or candidate_start.get("candidate_sha256") != spec.candidate.sha256
        or type(candidate_start.get("candidate_transfer_count_max")) is not int
        or candidate_start.get("candidate_transfer_count_max") != 1
        or candidate_start.get("candidate_replay") is not False
        or candidate_start.get("rollback_required") is not True
        or set(candidate_flashed) != flashed_keys
        or candidate_flashed.get("state") != "CANDIDATE_FLASHED"
        or candidate_flashed.get("candidate_sha256") != spec.candidate.sha256
        or type(candidate_flashed.get("candidate_transfer_count")) is not int
        or candidate_flashed.get("candidate_transfer_count") != 1
        or candidate_flashed.get("candidate_replay") is not False
        or candidate_flashed.get("rollback_required") is not True
    ):
        raise ContractError("attended candidate transfer evidence is not exact")
    approved_timestamp = parse_utc_timestamp(
        approved.get("timestamp_utc"),
        "attended approval",
    )
    start_timestamp = parse_utc_timestamp(
        candidate_start.get("timestamp_utc"),
        "attended candidate intent",
    )
    flashed_timestamp = parse_utc_timestamp(
        candidate_flashed.get("timestamp_utc"),
        "attended candidate completion",
    )
    window_timestamp = parse_utc_timestamp(
        window.get("timestamp_utc"),
        "attended window opened",
    )
    if not (
        approved_timestamp
        <= start_timestamp
        <= flashed_timestamp
        <= window_timestamp
    ):
        raise ContractError("attended candidate timestamps are out of order")

    execution = candidate_flashed.get("record")
    phase_keys = {
        "local_image_validated",
        "native_recovery_requested",
        "recovery_endpoint_selected",
        "payload_transfer_started",
        "boot_write_started",
        "boot_write_completed",
        "readback_completed",
    }
    execution_keys = {
        "returncode",
        "raw_log",
        "raw_log_size",
        "raw_log_sha256",
        "process_started",
        "phase_classification",
    }
    expected_log = transaction_dir / "candidate-flash.raw.log"
    if (
        not isinstance(execution, dict)
        or set(execution) != execution_keys
        or type(execution.get("returncode")) is not int
        or execution.get("returncode") != 0
        or execution.get("process_started") is not True
        or type(execution.get("raw_log_size")) is not int
        or execution.get("raw_log_size") < 0
        or not isinstance(execution.get("raw_log_sha256"), str)
        or execution.get("raw_log") != str(expected_log)
        or not isinstance(execution.get("phase_classification"), dict)
        or set(execution["phase_classification"]) != phase_keys
        or any(
            value is not True
            for value in execution["phase_classification"].values()
        )
    ):
        raise ContractError("attended candidate execution record is not exact")
    try:
        require_private_regular(expected_log)
        log_stat = os.lstat(expected_log)
        resolved_log = expected_log.resolve(strict=True)
    except (FileNotFoundError, ContractError) as exc:
        raise ContractError("attended candidate raw log is unavailable") from exc
    if (
        log_stat.st_nlink != 1
        or resolved_log != expected_log
        or resolved_log.stat().st_size != execution["raw_log_size"]
        or sha256_file(resolved_log) != execution["raw_log_sha256"]
        or classify_flash_log(resolved_log) != execution["phase_classification"]
    ):
        raise ContractError("attended candidate raw log lost its exact binding")


def attended_window_path(transaction_dir: Path) -> Path:
    return transaction_dir / "attended-window.json"


def attended_window_binding(
    spec: F1Spec,
    approval_prepared: dict[str, Any],
    window_record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "a90_v3403_f1_attended_continue_binding_v1",
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "approval_binding_sha256": approval_prepared[
            "approval_binding_sha256"
        ],
        "candidate_boot_sha256": spec.candidate.sha256,
        "rollback_boot_sha256": spec.rollback.sha256,
        "window_sequence": window_record.get("sequence"),
        "window_opened_utc": window_record.get("timestamp_utc"),
        "window_deadline_utc": window_record.get("window_deadline_utc"),
        "attended_window_sec": spec.attended_window_sec,
        "pre_handoff_attempt_limit": spec.pre_handoff_attempt_limit,
        "handoff_attempt_limit": spec.handoff_attempt_limit,
        "handoff_argv_sha256": json_sha256(list(spec.handoff_command)),
        "candidate_replay": False,
        "only_partition_payload": "boot",
    }


def open_attended_window(
    spec: F1Spec,
    approval_prepared: dict[str, Any],
    transaction_dir: Path,
    journal_dir: Path,
) -> dict[str, Any]:
    if spec.observation_mode != ATTENDED_OBSERVATION_MODE:
        raise ContractError("attended window requires exact attended observation mode")
    opened = utc_now()
    deadline = (
        parse_utc_timestamp(opened, "attended window opened")
        + dt.timedelta(seconds=spec.attended_window_sec)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    record_path = append_record(
        journal_dir,
        "CANDIDATE_FLASHED",
        "attended-window-open",
        {
            "window_deadline_utc": deadline,
            "attended_window_sec": spec.attended_window_sec,
            "pre_handoff_attempt_limit": spec.pre_handoff_attempt_limit,
            "handoff_attempt_limit": spec.handoff_attempt_limit,
            "candidate_replay": False,
            "rollback_required": True,
            "handoff_intent": False,
            "handoff_sent": False,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
        timestamp_utc=opened,
    )
    window_record = json.loads(record_path.read_text(encoding="utf-8"))
    binding = attended_window_binding(
        spec,
        approval_prepared,
        window_record,
    )
    binding_sha256 = json_sha256(binding)
    receipt = {
        "schema": ATTENDED_WINDOW_SCHEMA,
        "created_utc": utc_now(),
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "continue_binding": binding,
        "continue_binding_sha256": binding_sha256,
        "continue_token": ATTENDED_CONTINUE_PREFIX + binding_sha256,
        "candidate_already_started": True,
        "additional_partition_authority": False,
        "candidate_replay": False,
        "rollback_pre_authorized": True,
    }
    write_private_json_exclusive(
        attended_window_path(transaction_dir),
        receipt,
    )
    return {
        "schema": ORCHESTRATOR_SCHEMA,
        "status": "PAUSED_F1_V2_ATTENDED_WINDOW",
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "continue_token": receipt["continue_token"],
        "window_deadline_utc": deadline,
        "pre_handoff_attempt_limit": spec.pre_handoff_attempt_limit,
        "handoff_attempt_limit": spec.handoff_attempt_limit,
        "candidate_transfer_count": 1,
        "candidate_replay": False,
        "rollback_required": True,
        "additional_partition_authority": False,
    }


def load_attended_window(
    spec: F1Spec,
    approval_prepared: dict[str, Any],
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    path = attended_window_path(transaction_dir)
    require_private_regular(path)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    window_records = [
        record
        for record in records
        if record.get("action") == "attended-window-open"
    ]
    expected_keys = {
        "schema",
        "created_utc",
        "run_id",
        "manifest_sha256",
        "continue_binding",
        "continue_binding_sha256",
        "continue_token",
        "candidate_already_started",
        "additional_partition_authority",
        "candidate_replay",
        "rollback_pre_authorized",
    }
    if len(window_records) != 1:
        raise ContractError("attended continuation requires one exact window record")
    window_record = window_records[0]
    window_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
        "window_deadline_utc",
        "attended_window_sec",
        "pre_handoff_attempt_limit",
        "handoff_attempt_limit",
        "candidate_replay",
        "rollback_required",
        "handoff_intent",
        "handoff_sent",
    }
    opened = parse_utc_timestamp(
        window_record.get("timestamp_utc"),
        "attended window opened",
    )
    deadline = parse_utc_timestamp(
        window_record.get("window_deadline_utc"),
        "attended window deadline",
    )
    if (
        set(window_record) != window_keys
        or window_record.get("state") != "CANDIDATE_FLASHED"
        or type(window_record.get("attended_window_sec")) is not int
        or window_record.get("attended_window_sec") != ATTENDED_WINDOW_SEC
        or type(window_record.get("pre_handoff_attempt_limit")) is not int
        or window_record.get("pre_handoff_attempt_limit")
        != ATTENDED_PRE_HANDOFF_ATTEMPT_LIMIT
        or type(window_record.get("handoff_attempt_limit")) is not int
        or window_record.get("handoff_attempt_limit")
        != ATTENDED_HANDOFF_ATTEMPT_LIMIT
        or deadline
        != opened + dt.timedelta(seconds=ATTENDED_WINDOW_SEC)
        or window_record.get("candidate_replay") is not False
        or window_record.get("rollback_required") is not True
        or window_record.get("handoff_intent") is not False
        or window_record.get("handoff_sent") is not False
    ):
        raise ContractError("attended window journal record is not exact")
    binding = attended_window_binding(
        spec,
        approval_prepared,
        window_record,
    )
    binding_sha256 = json_sha256(binding)
    if (
        not isinstance(receipt, dict)
        or set(receipt) != expected_keys
        or receipt.get("schema") != ATTENDED_WINDOW_SCHEMA
        or not is_canonical_utc_timestamp(receipt.get("created_utc"))
        or receipt.get("run_id") != spec.stage.run_id
        or receipt.get("manifest_sha256") != spec.stage.manifest_sha256
        or receipt.get("continue_binding") != binding
        or receipt.get("continue_binding_sha256") != binding_sha256
        or receipt.get("continue_token")
        != ATTENDED_CONTINUE_PREFIX + binding_sha256
        or receipt.get("candidate_already_started") is not True
        or receipt.get("additional_partition_authority") is not False
        or receipt.get("candidate_replay") is not False
        or receipt.get("rollback_pre_authorized") is not True
    ):
        raise ContractError("attended continuation receipt lost its exact binding")
    return receipt


def stage_command(spec: F1Spec, args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(STAGING_PATH),
        "--manifest",
        str(spec.stage.manifest_path),
        "--expect-manifest-sha256",
        spec.stage.manifest_sha256,
        "--execute-approved-stage",
        "--approved-manifest-sha256",
        spec.stage.manifest_sha256,
        "--approved-adapter-sha256",
        spec.stage.adapter_sha256,
        "--approved-run-id",
        spec.stage.run_id,
        "--approval",
        args.approval,
        "--run-dir",
        str(PRIVATE_RUN_BASE / spec.stage.run_id / "staging-live"),
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--device-ip",
        spec.observer_device,
        "--remote-timeout",
        str(args.remote_timeout),
        "--bridge-timeout",
        str(args.bridge_timeout),
        "--transfer-timeout",
        str(args.transfer_timeout),
    ]


def flash_command(
    spec: F1Spec,
    args: argparse.Namespace,
    *,
    rollback: bool,
    from_native: bool,
) -> list[str]:
    bound = spec.rollback if rollback else spec.candidate
    version = spec.rollback_version if rollback else spec.candidate_version
    timeout = spec.rollback_boot_timeout if rollback else spec.candidate_boot_timeout
    command = [
        sys.executable,
        str(spec.flash_runner.path),
        str(bound.path),
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--bridge-timeout",
        str(args.bridge_timeout),
        "--reboot-timeout",
        str(timeout),
        "--expect-sha256",
        bound.sha256,
        "--expect-version",
        version,
        "--verify-protocol",
        "selftest",
        "--serial",
        spec.recovery_serial,
    ]
    if from_native:
        command.append("--from-native")
    return command


def validate_stage_result(spec: F1Spec) -> dict[str, Any]:
    stage_dir = PRIVATE_RUN_BASE / spec.stage.run_id / "staging-live"
    path = stage_dir / "result.json"
    require_private_regular(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    rootfs = value.get("rootfs") if isinstance(value, dict) else None
    publication = value.get("publication") if isinstance(value, dict) else None
    if (
        value.get("schema") != staging.ADAPTER_SCHEMA
        or value.get("run_id") != spec.stage.run_id
        or value.get("status") != "PASS_ABSENT_ONLY_ROOTFS_STAGED"
        or value.get("manifest_sha256") != spec.stage.manifest_sha256
        or value.get("adapter_sha256") != spec.stage.adapter_sha256
        or not isinstance(rootfs, dict)
        or rootfs.get("device_path") != spec.stage.remote_final
        or rootfs.get("size") != spec.stage.local_size
        or rootfs.get("sha256") != spec.stage.local_sha256
        or not isinstance(publication, dict)
        or publication.get("candidate_allowed") is not True
    ):
        raise ContractError("staging result does not authorize this exact candidate")
    journal_paths = sorted((stage_dir / "journal").glob("*.json"))
    if len(journal_paths) != len(SUCCESSFUL_STAGE_STATES):
        raise ContractError("staging journal does not have the exact success closure")
    records: list[dict[str, Any]] = []
    for sequence, journal_path in enumerate(journal_paths):
        require_private_regular(journal_path)
        if not journal_path.name.startswith(f"{sequence:04d}-"):
            raise ContractError("staging journal sequence is not contiguous")
        record = json.loads(journal_path.read_text(encoding="utf-8"))
        if (
            not isinstance(record, dict)
            or record.get("schema") != "a90_v3403_absent_only_stage_journal_v1"
            or record.get("sequence") != sequence
            or record.get("run_id") != spec.stage.run_id
            or record.get("manifest_sha256") != spec.stage.manifest_sha256
            or record.get("state") != SUCCESSFUL_STAGE_STATES[sequence]
        ):
            raise ContractError("staging journal is not the exact bound success sequence")
        if journal_path.name != f"{sequence:04d}-{record.get('state')}.json":
            raise ContractError("staging journal filename/state mismatch")
        records.append(record)
    if records[-1].get("result") != value:
        raise ContractError("staging journal is not durably closed on the exact result")
    return value


def run_f1_cmd(
    args: argparse.Namespace,
    command: list[str],
    *,
    allow_error: bool = False,
) -> dict[str, Any]:
    return d1.run_cmd(
        args.bridge_host,
        args.bridge_port,
        args.remote_timeout,
        command,
        input_mode=F1_SERIAL_INPUT_MODE,
        input_char_delay_sec=F1_SERIAL_INPUT_CHAR_DELAY_SEC,
        allow_error=allow_error,
    )


def run_f1_shell(
    args: argparse.Namespace,
    script: str,
    *,
    allow_error: bool = False,
) -> dict[str, Any]:
    return d1.run_shell(
        args.bridge_host,
        args.bridge_port,
        args.remote_timeout,
        script,
        input_mode=F1_SERIAL_INPUT_MODE,
        input_char_delay_sec=F1_SERIAL_INPUT_CHAR_DELAY_SEC,
        allow_error=allow_error,
    )


def require_exact_f1_command_receipt(
    value: Any,
    command: list[str],
    label: str,
) -> dict[str, Any]:
    record = _dict(value, label)
    begin = _dict(record.get("begin"), f"{label}.begin")
    end = _dict(record.get("end"), f"{label}.end")
    if (
        set(record) != {"command", "rc", "status", "trust", "begin", "end", "text"}
        or record.get("command") != command
        or type(record.get("rc")) is not int
        or record.get("rc") != 0
        or record.get("status") != "ok"
        or record.get("trust") != "A90P1_V1_STRUCTURAL_ONLY"
        or type(record.get("text")) is not str
        or set(begin) != {"argc", "cmd", "flags", "seq"}
        or begin.get("cmd") != command[0]
        or begin.get("argc") != str(len(command))
        or re.fullmatch(r"0x[0-9a-f]+", str(begin.get("flags") or "")) is None
        or not str(begin.get("seq") or "").isdigit()
        or set(end)
        != {"cmd", "duration_ms", "errno", "flags", "rc", "seq", "status"}
        or end.get("cmd") != command[0]
        or end.get("seq") != begin.get("seq")
        or end.get("flags") != begin.get("flags")
        or end.get("rc") != "0"
        or end.get("errno") != "0"
        or end.get("status") != "ok"
        or not str(end.get("duration_ms") or "").isdigit()
    ):
        raise ContractError(f"{label} is not one exact successful framed receipt")
    return record


def candidate_first_boot_state_absence_script(contract: dict[str, Any]) -> str:
    enable_path = contract["enable_path"]
    latch_path = contract["latch_path"]
    return "\n".join(
        (
            "set -eu",
            f"ENABLE={enable_path}",
            f"LATCH={latch_path}",
            'for STATE_PATH in "$ENABLE" "$LATCH"; do',
            '  if [ -e "$STATE_PATH" ] || [ -L "$STATE_PATH" ]; then',
            '    echo A90AUTO_F1_PRE state_path_absent=0 path="$STATE_PATH"',
            "    exit 41",
            "  fi",
            "done",
            "echo A90AUTO_F1_PRE enable_absent=1 latch_absent=1",
        )
    )


def require_candidate_first_boot_state_absent(
    spec: F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any] | None:
    contract = getattr(spec, "candidate_first_boot", None)
    if contract is None:
        return None
    enable_path = contract["enable_path"]
    latch_path = contract["latch_path"]
    script = candidate_first_boot_state_absence_script(contract)
    record = require_exact_f1_command_receipt(
        run_f1_shell(args, script),
        ["run", "/bin/busybox", "sh", "-c", script],
        "auto-handoff pre-transfer state receipt",
    )
    marker = "A90AUTO_F1_PRE enable_absent=1 latch_absent=1"
    if str(record.get("text") or "").count(marker) != 1:
        raise ContractError("auto-handoff pre-transfer enable/latch absence is not exact")
    return {
        "proof": True,
        "enable_path": enable_path,
        "latch_path": latch_path,
        "record": record,
    }


def require_auto_handoff_log_exclusively_unarmed(
    log_text: str,
    label: str,
) -> None:
    state_lines: list[str] = []
    for line in log_text.replace("\r", "\n").splitlines():
        marker = line.find("A90AUTO state=")
        if marker >= 0:
            state_lines.append(line[marker:].strip())
    if not state_lines or any(
        line != "A90AUTO state=unarmed-stay-native" for line in state_lines
    ):
        raise ContractError(f"{label} is not exclusively unarmed")


def require_candidate_first_boot_unarmed(
    spec: F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any] | None:
    if getattr(spec, "candidate_first_boot", None) is None:
        return None
    status_record = require_exact_f1_command_receipt(
        run_f1_cmd(args, ["auto-handoff-status"]),
        ["auto-handoff-status"],
        "auto-handoff first-boot status receipt",
    )
    status_text = str(status_record.get("text") or "")
    expected_status = (
        "A90AUTO_STATUS binding=1 enable=0 latch=0 "
        f"build={spec.candidate_build}"
    )
    if status_text.count(expected_status) != 1:
        raise ContractError(
            "auto-handoff first resident boot status is not exact unarmed 0,0"
        )
    log_record = require_exact_f1_command_receipt(
        run_f1_cmd(args, ["logcat"]),
        ["logcat"],
        "auto-handoff first-boot log receipt",
    )
    log_text = str(log_record.get("text") or "")
    require_auto_handoff_log_exclusively_unarmed(
        log_text,
        "auto-handoff first resident boot log",
    )
    return {
        "proof": True,
        "status": status_record,
        "log": log_record,
        "enable": 0,
        "latch": 0,
        # Legacy journal field name: True means every observed state was the
        # exact safe unarmed state, not that the cumulative log had one line.
        "unarmed_log_unique": True,
    }


def require_f1_baseline(args: argparse.Namespace) -> dict[str, Any]:
    return staging.require_baseline(
        args,
        input_mode=F1_SERIAL_INPUT_MODE,
        input_char_delay_sec=F1_SERIAL_INPUT_CHAR_DELAY_SEC,
    )


def require_f1_starting_health(
    spec: F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    expected_version = getattr(
        spec.stage,
        "starting_version",
        staging.EXPECTED_BASELINE_VERSION,
    )
    expected_build = getattr(
        spec.stage,
        "starting_build",
        staging.EXPECTED_BASELINE_BUILD,
    )
    if (
        expected_version == staging.EXPECTED_BASELINE_VERSION
        and expected_build == staging.EXPECTED_BASELINE_BUILD
    ):
        return require_f1_baseline(args)
    return staging.require_native_health(
        args,
        expected_version=expected_version,
        expected_build=expected_build,
        input_mode=F1_SERIAL_INPUT_MODE,
        input_char_delay_sec=F1_SERIAL_INPUT_CHAR_DELAY_SEC,
    )


def _candidate_return_modemmanager_guard_inputs(
    spec: F1Spec,
) -> tuple[dict[str, str], str]:
    try:
        resolved = Path(spec.stage.bridge_realpath).resolve(strict=True)
        info = resolved.stat()
        identity, endpoint = cdc_guard._resolve_endpoint(  # noqa: SLF001
            staging.SYS_CLASS_TTY / resolved.name
        )
    except (OSError, ValueError, cdc_guard.ObserverError) as exc:
        raise ContractError(
            "ModemManager guard A90 ACM identity is unavailable"
        ) from exc
    if not stat.S_ISCHR(info.st_mode):
        raise ContractError(
            "ModemManager guard bridge is not a character device"
        )
    if (
        os.major(info.st_rdev) != endpoint.major
        or os.minor(info.st_rdev) != endpoint.minor
        or identity.get("vendor") != staging.HOST_NCM_VENDOR_ID
        or identity.get("product") != staging.HOST_NCM_PRODUCT_ID
        or identity.get("driver") != "cdc_acm"
        or not identity.get("serial")
    ):
        raise ContractError("ModemManager guard identity is not exact A90 ACM")
    guard_spec = {
        "kind": cdc_guard.KIND,
        "usb_vendor_id": identity["vendor"],
        "usb_product_id": identity["product"],
        "usb_serial": identity["serial"],
        "usb_driver": identity["driver"],
        "usb_interface_number": identity["interface"],
        "banner_hex": "00",
    }
    cdc_guard.validate_spec(guard_spec)
    return guard_spec, f"usb:{endpoint.topology}"


def arm_candidate_return_modemmanager_guard(
    spec: F1Spec,
    args: argparse.Namespace,
    transaction_dir: Path,
    *,
    corridor: str = "candidate-return",
    prepared_inputs: tuple[dict[str, str], str] | None = None,
) -> cdc_guard.ModemManagerGuard:
    if corridor not in MODEMMANAGER_GUARD_CORRIDORS:
        raise ContractError("ModemManager guard corridor is not exact")
    if prepared_inputs is None:
        guard_spec, topology = _candidate_return_modemmanager_guard_inputs(spec)
    else:
        if not corridor.startswith("rollback-recovery-"):
            raise ContractError("prepared ModemManager guard inputs are recovery-only")
        guard_spec, topology = prepared_inputs
        try:
            cdc_guard.validate_spec(guard_spec)
        except cdc_guard.ObserverError as exc:
            raise ContractError("prepared ModemManager guard spec is invalid") from exc
        if cdc_guard.TOPOLOGY_RE.fullmatch(topology) is None:
            raise ContractError("prepared ModemManager guard topology is invalid")
    numeric = (
        spec.handoff_timeout,
        spec.ssh_marker_timeout,
        spec.candidate_return_timeout,
        args.ssh_connect_timeout,
        args.bridge_timeout,
        args.flash_command_timeout,
        args.poll_interval,
        args.remote_timeout,
    )
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
        for value in numeric
    ):
        raise ContractError("ModemManager guard timeout input is invalid")
    if corridor == "candidate-return":
        budget = (
            spec.handoff_timeout
            + spec.ssh_marker_timeout
            + args.ssh_connect_timeout
            + 10.0
            + 2 * args.poll_interval
            + spec.candidate_return_timeout
            + MODEMMANAGER_GUARD_POST_RETURN_COMMAND_COUNT
            * args.remote_timeout
            + OBSERVATION_MENU_SETTLE_SEC
            + MODEMMANAGER_GUARD_MARGIN_SEC
        )
    elif corridor == "resident-promotion":
        promotion_budget = (
            args.flash_command_timeout
            + MODEMMANAGER_GUARD_PROMOTION_BRIDGE_COMMAND_COUNT
            * max(args.bridge_timeout, EXACT_BRIDGE_PREFLIGHT_BUDGET_SEC)
            + MODEMMANAGER_GUARD_PROMOTION_REMOTE_COMMAND_COUNT
            * args.remote_timeout
            + 3 * OBSERVATION_MENU_SETTLE_SEC
            + min(spec.candidate_return_timeout, 30.0)
            + spec.candidate_return_timeout
            + 2 * HOST_NCM_REBIND_WORST_CASE_SEC
            + MODEMMANAGER_GUARD_MARGIN_SEC
        )
        inline_rollback_budget = (
            2 * args.flash_command_timeout
            + max(args.bridge_timeout, EXACT_BRIDGE_PREFLIGHT_BUDGET_SEC)
            + (
                MODEMMANAGER_GUARD_ROLLBACK_SOURCE_COMMAND_COUNT
                + MODEMMANAGER_GUARD_ROLLBACK_HEALTH_COMMAND_COUNT
            )
            * args.remote_timeout
            + OBSERVATION_MENU_SETTLE_SEC
            + MODEMMANAGER_GUARD_MARGIN_SEC
        )
        budget = max(promotion_budget, inline_rollback_budget)
    else:
        budget = (
            args.flash_command_timeout
            + max(args.bridge_timeout, EXACT_BRIDGE_PREFLIGHT_BUDGET_SEC)
            + (
                MODEMMANAGER_GUARD_ROLLBACK_SOURCE_COMMAND_COUNT
                + MODEMMANAGER_GUARD_ROLLBACK_HEALTH_COMMAND_COUNT
            )
            * args.remote_timeout
            + OBSERVATION_MENU_SETTLE_SEC
            + MODEMMANAGER_GUARD_MARGIN_SEC
        )
    max_sec = max(cdc_guard.GUARD_DEFAULT_MAX_SEC, math.ceil(budget))
    if max_sec > cdc_guard.GUARD_MAX_SEC_LIMIT:
        raise ContractError(
            f"{corridor} corridor exceeds the reviewed ModemManager "
            "guard lifetime"
        )
    try:
        guard = cdc_guard.ModemManagerGuard.arm(
            guard_spec,
            topology,
            transaction_dir,
            max_sec=max_sec,
        )
    except cdc_guard.ObserverError as exc:
        raise ContractError(
            f"{corridor} ModemManager guard did not arm"
        ) from exc
    if (
        guard.arm_receipt is None
        or guard.arm_receipt.get("child_alive") is not True
        or guard.process is None
        or guard.process.pid <= 0
        or guard.process.poll() is not None
        or guard.max_sec != max_sec
    ):
        guard.release()
        raise ContractError(f"{corridor} ModemManager guard lacks live receipt")
    try:
        write_private_json_exclusive(
            transaction_dir / f"{corridor}-modemmanager-guard-arm.json",
            {
                "schema": MODEMMANAGER_GUARD_ARM_SCHEMA,
                "corridor": corridor,
                "max_sec": max_sec,
                "child_pid": guard.process.pid,
                "guard_spec": guard_spec,
                "topology": topology,
                "receipt": guard.arm_receipt,
            },
        )
    except Exception:
        guard.release()
        raise
    return guard


def release_candidate_return_modemmanager_guard(
    guard: cdc_guard.ModemManagerGuard,
    transaction_dir: Path,
    *,
    corridor: str = "candidate-return",
) -> dict[str, Any]:
    if corridor not in MODEMMANAGER_GUARD_CORRIDORS:
        raise ContractError("ModemManager guard release corridor is not exact")
    release = guard.release()
    suffix = "release" if release.get("released") is True else "release-failed"
    write_private_json_exclusive(
        transaction_dir / f"{corridor}-modemmanager-guard-{suffix}.json",
        release,
    )
    return release


def modemmanager_guard_arm_evidence(
    transaction_dir: Path,
    corridor: str,
    guard: cdc_guard.ModemManagerGuard,
) -> dict[str, Any]:
    if corridor not in MODEMMANAGER_GUARD_CORRIDORS:
        raise ContractError("ModemManager guard evidence corridor is not exact")
    path = transaction_dir / f"{corridor}-modemmanager-guard-arm.json"
    require_private_regular(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("ModemManager guard arm evidence is invalid") from exc
    receipt = require_exact_modemmanager_guard_receipt(
        guard.arm_receipt,
        guard.spec,
        guard.topology,
    )
    receipt_hashes = (
        receipt.get("instance_sha256") if isinstance(receipt, dict) else None,
        receipt.get("spec_sha256") if isinstance(receipt, dict) else None,
        receipt.get("topology_sha256") if isinstance(receipt, dict) else None,
    )
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schema",
            "corridor",
            "max_sec",
            "child_pid",
            "guard_spec",
            "topology",
            "receipt",
        }
        or value.get("schema") != MODEMMANAGER_GUARD_ARM_SCHEMA
        or value.get("corridor") != corridor
        or value.get("max_sec") != guard.max_sec
        or guard.process is None
        or value.get("child_pid") != guard.process.pid
        or value.get("guard_spec") != guard.spec
        or value.get("topology") != guard.topology
        or value.get("receipt") != receipt
        or any(
            not isinstance(item, str) or HEX64_RE.fullmatch(item) is None
            for item in receipt_hashes
        )
    ):
        raise ContractError("ModemManager guard arm evidence lost its binding")
    return {
        "corridor": corridor,
        "arm_evidence_sha256": sha256_file(path),
        "guard_instance_sha256": receipt_hashes[0],
        "guard_spec_sha256": receipt_hashes[1],
        "guard_topology_sha256": receipt_hashes[2],
        "max_sec": guard.max_sec,
    }


def require_exact_modemmanager_guard_receipt(
    receipt: Any,
    guard_spec: Any,
    topology: Any,
) -> dict[str, Any]:
    try:
        if isinstance(guard_spec, dict):
            cdc_guard.validate_spec(guard_spec)
    except cdc_guard.ObserverError as exc:
        raise ContractError("ModemManager guard receipt spec is invalid") from exc
    topology_match = (
        cdc_guard.TOPOLOGY_RE.fullmatch(topology)
        if isinstance(topology, str)
        else None
    )
    digest_fields = (
        receipt.get("spec_sha256") if isinstance(receipt, dict) else None,
        receipt.get("topology_sha256") if isinstance(receipt, dict) else None,
        receipt.get("rule_sha256") if isinstance(receipt, dict) else None,
        receipt.get("instance_sha256") if isinstance(receipt, dict) else None,
        receipt.get("output_sha256") if isinstance(receipt, dict) else None,
    )
    if (
        not isinstance(guard_spec, dict)
        or topology_match is None
        or not isinstance(receipt, dict)
        or set(receipt) != MODEMMANAGER_GUARD_RECEIPT_KEYS
        or receipt.get("schema") != cdc_guard.GUARD_SCHEMA
        or receipt.get("status") != "armed"
        or receipt.get("child_alive") is not True
        or receipt.get("spec_sha256") != cdc_guard.digest(guard_spec)
        or receipt.get("topology_sha256")
        != hashlib.sha256(topology_match.group(1).encode("ascii")).hexdigest()
        or any(
            not isinstance(item, str) or HEX64_RE.fullmatch(item) is None
            for item in digest_fields
        )
    ):
        raise ContractError("ModemManager guard receipt is not exact")
    return receipt


def resident_promotion_guard_inputs(
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> tuple[dict[str, str], str]:
    path = transaction_dir / "resident-promotion-modemmanager-guard-arm.json"
    require_private_regular(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("resident promotion guard evidence is invalid") from exc
    guard_spec = value.get("guard_spec") if isinstance(value, dict) else None
    topology = value.get("topology") if isinstance(value, dict) else None
    receipt = value.get("receipt") if isinstance(value, dict) else None
    try:
        receipt = require_exact_modemmanager_guard_receipt(
            receipt,
            guard_spec,
            topology,
        )
    except ContractError as exc:
        raise ContractError("resident promotion guard receipt is invalid") from exc
    journal_records = [
        record
        for record in records
        if record.get("action") == "resident-promotion-guard-armed"
    ]
    journal_guard = (
        journal_records[0].get("guard")
        if len(journal_records) == 1
        and isinstance(journal_records[0], dict)
        else None
    )
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schema",
            "corridor",
            "max_sec",
            "child_pid",
            "guard_spec",
            "topology",
            "receipt",
        }
        or value.get("schema") != MODEMMANAGER_GUARD_ARM_SCHEMA
        or value.get("corridor") != "resident-promotion"
        or type(value.get("child_pid")) is not int
        or value.get("child_pid") <= 0
        or not isinstance(journal_guard, dict)
        or set(journal_guard)
        != {
            "corridor",
            "arm_evidence_sha256",
            "guard_instance_sha256",
            "guard_spec_sha256",
            "guard_topology_sha256",
            "max_sec",
        }
        or journal_guard.get("corridor") != "resident-promotion"
        or journal_guard.get("arm_evidence_sha256") != sha256_file(path)
        or journal_guard.get("guard_instance_sha256")
        != receipt.get("instance_sha256")
        or journal_guard.get("guard_spec_sha256")
        != receipt.get("spec_sha256")
        or journal_guard.get("guard_topology_sha256")
        != receipt.get("topology_sha256")
        or journal_guard.get("max_sec") != value.get("max_sec")
    ):
        raise ContractError("resident promotion guard evidence lost its binding")
    return dict(guard_spec), topology


def require_returned_modemmanager_guard(
    spec: F1Spec,
    epoch: dict[str, Any],
    guard: cdc_guard.ModemManagerGuard,
) -> dict[str, Any]:
    selected = Path(epoch["returned"]["selected_realpath"])
    try:
        resolved = selected.resolve(strict=True)
        info = resolved.stat()
        identity, endpoint = cdc_guard._resolve_endpoint(  # noqa: SLF001
            staging.SYS_CLASS_TTY / selected.name
        )
        cdc_guard.validate_spec(guard.spec)
    except (OSError, ValueError, cdc_guard.ObserverError) as exc:
        raise ContractError(
            "returned A90 ACM guard identity is unavailable"
        ) from exc
    expected_topology = f"usb:{endpoint.topology}"
    if (
        str(selected) != spec.stage.bridge_realpath
        or not stat.S_ISCHR(info.st_mode)
        or os.major(info.st_rdev) != endpoint.major
        or os.minor(info.st_rdev) != endpoint.minor
        or endpoint.tty_name != selected.name
        or guard.topology != expected_topology
        or identity.get("vendor") != guard.spec["usb_vendor_id"]
        or identity.get("product") != guard.spec["usb_product_id"]
        or identity.get("serial") != guard.spec["usb_serial"]
        or identity.get("driver") != guard.spec["usb_driver"]
        or identity.get("interface")
        != guard.spec["usb_interface_number"]
        or identity.get("vendor") != staging.HOST_NCM_VENDOR_ID
        or identity.get("product") != staging.HOST_NCM_PRODUCT_ID
        or identity.get("driver") != "cdc_acm"
        or not guard.matches_node(endpoint.tty_class)
    ):
        raise ContractError(
            "returned A90 ACM lacks the exact ModemManager ignore guard"
        )
    return {
        "exact_a90_acm_identity": True,
        "exact_guard_properties": True,
        "identity_sha256": endpoint.identity_sha256,
        "guard_spec_sha256": cdc_guard.digest(guard.spec),
        "guard_topology_sha256": hashlib.sha256(
            endpoint.topology.encode("ascii")
        ).hexdigest(),
    }


def _bound_bridge_serial_epoch(
    spec: F1Spec,
    bridge: dict[str, Any],
) -> dict[str, Any]:
    selected_realpath = bridge.get("selected_realpath")
    if selected_realpath != spec.stage.bridge_realpath:
        raise ContractError("return epoch bridge realpath is not exact")
    device = Path(spec.stage.bridge_device)
    try:
        if not device.is_symlink():
            raise ContractError("return epoch bridge device is not a symlink")
        resolved = device.resolve(strict=True)
        expected = Path(spec.stage.bridge_realpath).resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        raise ContractError("return epoch bridge device is unavailable") from exc
    if resolved != expected or not stat.S_ISCHR(info.st_mode):
        raise ContractError("return epoch bridge character device is not exact")

    usb_parent = staging._usb_device_parent(  # noqa: SLF001 - same bound adapter
        staging.SYS_CLASS_TTY / resolved.name
    )
    if usb_parent is None:
        raise ContractError("return epoch USB parent is unavailable")
    vendor = staging._read_sysfs_text(usb_parent / "idVendor").lower()  # noqa: SLF001
    product = staging._read_sysfs_text(usb_parent / "idProduct").lower()  # noqa: SLF001
    busnum = staging._read_sysfs_text(usb_parent / "busnum")  # noqa: SLF001
    devnum = staging._read_sysfs_text(usb_parent / "devnum")  # noqa: SLF001
    if (
        vendor != staging.HOST_NCM_VENDOR_ID
        or product != staging.HOST_NCM_PRODUCT_ID
        or not busnum.isdecimal()
        or not devnum.isdecimal()
    ):
        raise ContractError("return epoch USB identity is not exact A90")
    return {
        "schema": RETURN_EPOCH_SCHEMA,
        "selected_realpath": selected_realpath,
        "tty_st_dev": info.st_dev,
        "tty_st_ino": info.st_ino,
        "tty_st_rdev": info.st_rdev,
        "usb_busnum": int(busnum, 10),
        "usb_devnum": int(devnum, 10),
    }


def capture_bridge_serial_epoch(
    spec: F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    bridge = staging.require_exact_bridge(spec.stage, args)
    return _bound_bridge_serial_epoch(spec, bridge)


def _validated_return_epoch_key(
    spec: F1Spec,
    value: Any,
) -> tuple[int, int, int, int, int]:
    keys = {
        "schema",
        "selected_realpath",
        "tty_st_dev",
        "tty_st_ino",
        "tty_st_rdev",
        "usb_busnum",
        "usb_devnum",
    }
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or value.get("schema") != RETURN_EPOCH_SCHEMA
        or value.get("selected_realpath") != spec.stage.bridge_realpath
    ):
        raise ContractError("return epoch record is not exact")
    numeric = tuple(
        value[name]
        for name in (
            "tty_st_dev",
            "tty_st_ino",
            "tty_st_rdev",
            "usb_busnum",
            "usb_devnum",
        )
    )
    if any(type(item) is not int or item < 0 for item in numeric):
        raise ContractError("return epoch record has invalid numeric identity")
    return numeric


def wait_for_new_bridge_serial_epoch(
    spec: F1Spec,
    args: argparse.Namespace,
    before_handoff: dict[str, Any],
) -> dict[str, Any]:
    before_key = _validated_return_epoch_key(spec, before_handoff)
    deadline = time.monotonic() + spec.candidate_return_timeout
    last = "same pre-handoff USB serial epoch"
    while time.monotonic() < deadline:
        try:
            bridge = staging.require_exact_bridge(spec.stage, args)
            current = _bound_bridge_serial_epoch(spec, bridge)
            current_key = _validated_return_epoch_key(spec, current)
        except Exception as exc:  # noqa: BLE001 - bounded host enumeration
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(args.poll_interval)
            continue
        if time.monotonic() >= deadline:
            last = "return USB serial epoch appeared after deadline"
            break
        if current_key[3:] == before_key[3:]:
            time.sleep(args.poll_interval)
            continue
        if deadline - time.monotonic() <= OBSERVATION_MENU_SETTLE_SEC:
            last = "return USB serial epoch lacks bounded settle budget"
            break
        time.sleep(OBSERVATION_MENU_SETTLE_SEC)
        if time.monotonic() >= deadline:
            last = "return USB serial epoch settle crossed deadline"
            break
        try:
            bridge = staging.require_exact_bridge(spec.stage, args)
            confirmed = _bound_bridge_serial_epoch(spec, bridge)
            confirmed_key = _validated_return_epoch_key(spec, confirmed)
        except Exception as exc:  # noqa: BLE001 - bounded host enumeration
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(args.poll_interval)
            continue
        if time.monotonic() >= deadline:
            last = "return USB serial epoch confirmation crossed deadline"
            break
        if confirmed_key != current_key:
            last = "return USB serial epoch changed while settling"
            time.sleep(args.poll_interval)
            continue
        return {
            "proof": True,
            "pre_handoff": before_handoff,
            "returned": confirmed,
            "usb_serial_epoch_changed": True,
        }
    raise RuntimeError(
        "candidate USB serial epoch did not change before rollback deadline; "
        f"last={last!r}"
    )


def settle_observation_channel(
    args: argparse.Namespace,
    *,
    phase: str,
) -> dict[str, Any]:
    hide = run_f1_cmd(args, ["hide"], allow_error=True)
    hide_end = hide.get("end") if isinstance(hide.get("end"), dict) else {}
    if (
        hide.get("rc") != 0
        or hide.get("status") != "ok"
        or hide_end.get("cmd") != "hide"
        or "menu: hide requested" not in str(hide.get("text") or "")
    ):
        raise ContractError(f"{phase} observation menu hide did not complete")

    time.sleep(OBSERVATION_MENU_SETTLE_SEC)
    canary = run_f1_cmd(
        args,
        list(OBSERVATION_CHANNEL_CANARY),
        allow_error=True,
    )
    canary_end = (
        canary.get("end") if isinstance(canary.get("end"), dict) else {}
    )
    if (
        canary.get("rc") != 0
        or canary.get("status") != "ok"
        or canary_end.get("cmd") != OBSERVATION_CHANNEL_CANARY[0]
    ):
        raise ContractError(f"{phase} observation channel did not settle")
    return {
        "phase": phase,
        "framed_hide": True,
        "menu_settle_sec": OBSERVATION_MENU_SETTLE_SEC,
        "canary_command": list(OBSERVATION_CHANNEL_CANARY),
        "hide": hide,
        "canary": canary,
    }


def _host_command(command: list[str], *, timeout: float) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ContractError("bounded host NCM command failed") from exc
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _host_ncm_peer_cidr(device_ip: str) -> str:
    device = ipaddress.IPv4Address(staging.validate_observer_device(device_ip))
    network = ipaddress.IPv4Network(
        f"{device}/{staging.HOST_NCM_PREFIX}",
        strict=False,
    )
    peer = ipaddress.IPv4Address(int(device) - 1)
    if peer not in network or peer == network.network_address:
        raise ContractError("observer address has no exact USB-local host peer")
    return f"{peer}/{staging.HOST_NCM_PREFIX}"


def _nmcli_active_connection(interface: str) -> tuple[str, dict[str, Any]]:
    receipt = _host_command(
        [
            "nmcli",
            "-g",
            "GENERAL.CONNECTION",
            "device",
            "show",
            interface,
        ],
        timeout=10.0,
    )
    lines = str(receipt["stdout"]).splitlines()
    active = lines[0].strip() if receipt["returncode"] == 0 and lines else ""
    return active, receipt


def rebind_host_ncm_after_reenumeration(
    spec: F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    if shutil.which("nmcli") is None:
        raise ContractError("nmcli is unavailable for exact host NCM rebind")
    bridge = staging.require_exact_bridge(spec.stage, args)
    bridge_realpath = bridge.get("selected_realpath")
    if not isinstance(bridge_realpath, str):
        raise ContractError("exact bridge lacks a selected realpath")

    deadline = time.monotonic() + HOST_NCM_REBIND_TIMEOUT_SEC
    interfaces: tuple[str, ...] = ()
    while time.monotonic() < deadline:
        interfaces = staging.exact_a90_ncm_interfaces(bridge_realpath)
        if len(interfaces) == 1:
            break
        if len(interfaces) > 1:
            raise ContractError("multiple NCM interfaces share the exact A90 USB parent")
        time.sleep(HOST_NCM_REBIND_POLL_SEC)
    if len(interfaces) != 1:
        raise ContractError("exact A90 USB parent did not expose one NCM interface")
    interface = interfaces[0]

    profile = _host_command(
        [
            "nmcli",
            "-g",
            "connection.type",
            "connection",
            "show",
            spec.observer_host_ncm_profile,
        ],
        timeout=10.0,
    )
    if (
        profile["returncode"] != 0
        or str(profile["stdout"]).strip() != HOST_NCM_CONNECTION_TYPE
    ):
        raise ContractError("manifest-bound host NCM profile is absent or not Ethernet")

    active_before, active_before_receipt = _nmcli_active_connection(interface)
    try:
        ready_before = staging.require_host_ncm_ready(
            spec.observer_device,
            bridge_realpath,
        )
    except (ContractError, staging.ContractError):
        ready_before = None
    if (
        ready_before is not None
        and active_before == spec.observer_host_ncm_profile
    ):
        return {
            "same_current_acm_usb_parent": True,
            "exact_interface_count": 1,
            "profile_bound": True,
            "mutated": False,
            "profile_check": profile,
            "active_before": active_before_receipt,
            "ready": ready_before,
        }

    host_cidr = _host_ncm_peer_cidr(spec.observer_device)
    modify = _host_command(
        [
            "nmcli",
            "--wait",
            "10",
            "connection",
            "modify",
            spec.observer_host_ncm_profile,
            "connection.interface-name",
            interface,
            "ipv4.method",
            "manual",
            "ipv4.addresses",
            host_cidr,
            "ipv4.gateway",
            "",
            "ipv4.never-default",
            "yes",
            "ipv4.dns",
            "",
            "ipv6.method",
            "disabled",
            "connection.autoconnect",
            "no",
        ],
        timeout=15.0,
    )
    if modify["returncode"] != 0:
        raise ContractError("manifest-bound host NCM profile modification failed")
    activate = _host_command(
        [
            "nmcli",
            "--wait",
            "15",
            "connection",
            "up",
            spec.observer_host_ncm_profile,
            "ifname",
            interface,
        ],
        timeout=20.0,
    )
    if activate["returncode"] != 0:
        raise ContractError("manifest-bound host NCM profile activation failed")

    active_after, active_after_receipt = _nmcli_active_connection(interface)
    if active_after != spec.observer_host_ncm_profile:
        raise ContractError("exact A90 NCM interface did not select the bound profile")
    ready: dict[str, bool] | None = None
    deadline = time.monotonic() + HOST_NCM_REBIND_TIMEOUT_SEC
    while time.monotonic() < deadline:
        try:
            ready = staging.require_host_ncm_ready(
                spec.observer_device,
                bridge_realpath,
            )
            break
        except (ContractError, staging.ContractError):
            time.sleep(HOST_NCM_REBIND_POLL_SEC)
    if ready is None:
        raise ContractError("rebound exact A90 NCM path did not become USB-local ready")
    return {
        "same_current_acm_usb_parent": True,
        "exact_interface_count": 1,
        "profile_bound": True,
        "mutated": True,
        "profile_check": profile,
        "active_before": active_before_receipt,
        "modify": modify,
        "activate": activate,
        "active_after": active_after_receipt,
        "ready": ready,
    }


def _pstore_entry_names(text: str) -> tuple[str, ...]:
    names: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if not line:
            continue
        entry = PSTORE_ENTRY_RE.fullmatch(line)
        if entry is not None:
            names.append(entry.group(1))
            continue
        if any(pattern.fullmatch(line) for pattern in PSTORE_LISTING_CONTROL_RES):
            continue
        raise ContractError("pstore listing contains a malformed line")
    if len(names) != len(set(names)):
        raise ContractError("pstore listing contains duplicate entry names")
    return tuple(names)


def _require_exact_pstore_command_receipt(
    value: Any,
    command: list[str],
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} is not an exact successful receipt")
    if (
        set(value) != {"command", "rc", "status", "trust", "begin", "end", "text"}
        or value.get("command") != command
        or type(value.get("rc")) is not int
        or value.get("rc") != 0
        or value.get("status") != "ok"
        or type(value.get("text")) is not str
    ):
        raise ContractError(f"{label} is not an exact successful receipt")
    return value


def validate_pstore_before_handoff_receipt(
    value: Any,
    *,
    allow_legacy_empty: bool = False,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("pre-handoff pstore receipt is not exact")
    legacy_keys = {
        "mounted_read_only",
        "entries",
        "mount",
        "listing",
        "summary",
        "unmount",
    }
    exact_keys = {
        "mounted_read_only",
        "entries",
        "classification",
        "warning",
        "unexpected_entries",
        "mount",
        "listing",
        "summary",
        "unmount",
    }
    entries = value.get("entries")
    legacy = allow_legacy_empty and set(value) == legacy_keys
    if (
        (set(value) != exact_keys and not legacy)
        or value.get("mounted_read_only") is not True
        or not isinstance(entries, list)
        or any(type(entry) is not str for entry in entries)
        or (not legacy and value.get("unexpected_entries") != [])
    ):
        raise ContractError("pre-handoff pstore receipt is not exact")
    _require_exact_pstore_command_receipt(
        value.get("mount"),
        ["mountfs", "pstore", PSTORE_MOUNT_PATH, "pstore", "ro"],
        "pre-handoff pstore mount",
    )
    listing = _require_exact_pstore_command_receipt(
        value.get("listing"),
        ["ls", PSTORE_MOUNT_PATH],
        "pre-handoff pstore listing",
    )
    listing_entries = _pstore_entry_names(listing["text"])
    if legacy:
        if entries != [] or listing_entries != ():
            raise ContractError("legacy pre-handoff pstore receipt is not empty")
        _require_exact_pstore_command_receipt(
            value.get("summary"),
            ["pstore", "full"],
            "pre-handoff pstore summary",
        )
        _require_exact_pstore_command_receipt(
            value.get("unmount"),
            ["umount", PSTORE_MOUNT_PATH],
            "pre-handoff pstore unmount",
        )
        return value
    expected_boot_records = bool(listing_entries)
    if (
        entries != list(listing_entries)
        or any(
            PSTORE_EXPECTED_BOOT_ENTRY_RE.fullmatch(entry) is None
            for entry in listing_entries
        )
        or value.get("classification")
        != ("expected-boot-records" if expected_boot_records else "empty")
        or value.get("warning") is not expected_boot_records
    ):
        raise ContractError("pre-handoff pstore receipt is not exact")
    _require_exact_pstore_command_receipt(
        value.get("summary"),
        ["pstore", "full"],
        "pre-handoff pstore summary",
    )
    _require_exact_pstore_command_receipt(
        value.get("unmount"),
        ["umount", PSTORE_MOUNT_PATH],
        "pre-handoff pstore unmount",
    )
    return value


def require_clean_pstore_before_handoff(
    args: argparse.Namespace,
) -> dict[str, Any]:
    mount = run_f1_cmd(
        args,
        ["mountfs", "pstore", PSTORE_MOUNT_PATH, "pstore", "ro"],
    )
    mounted = True
    try:
        listing = run_f1_cmd(args, ["ls", PSTORE_MOUNT_PATH])
        summary = run_f1_cmd(args, ["pstore", "full"])
        entries = _pstore_entry_names(str(listing.get("text") or ""))
        unexpected_entries = tuple(
            entry
            for entry in entries
            if PSTORE_EXPECTED_BOOT_ENTRY_RE.fullmatch(entry) is None
        )
        if unexpected_entries:
            raise ContractError(
                "pre-handoff pstore contains crash-class or unknown entries"
            )
        unmount = run_f1_cmd(args, ["umount", PSTORE_MOUNT_PATH])
        mounted = False
    finally:
        if mounted:
            run_f1_cmd(
                args,
                ["umount", PSTORE_MOUNT_PATH],
                allow_error=True,
            )
    return {
        "mounted_read_only": True,
        "entries": list(entries),
        "classification": (
            "expected-boot-records" if entries else "empty"
        ),
        "warning": bool(entries),
        "unexpected_entries": [],
        "mount": mount,
        "listing": listing,
        "summary": summary,
        "unmount": unmount,
    }


def _retained_pmsg_classification(text: str) -> str:
    if "A90D3RET_V3405 phase=sync-timeout " in text:
        return "sync-timeout-observed"
    if (
        "A90D3RET_V3405 phase=sync-return" in text
        and "A90D3RET_V3405 phase=reboot-enter" in text
    ):
        return "sync-returned-reboot-entered"
    if "A90D3RET_V3405 phase=sync-enter" in text:
        return "sync-enter-no-terminal-marker"
    return "armed-before-sync"


def collect_and_clear_retained_pmsg(
    spec: F1Spec,
    args: argparse.Namespace,
    transaction_dir: Path,
) -> dict[str, Any]:
    mount = run_f1_cmd(
        args,
        ["mountfs", "pstore", PSTORE_MOUNT_PATH, "pstore"],
    )
    mounted = True
    try:
        listing = run_f1_cmd(args, ["ls", PSTORE_MOUNT_PATH])
        summary = run_f1_cmd(args, ["pstore", "full"])
        entries = _pstore_entry_names(str(listing.get("text") or ""))
        if (
            len(entries) != 1
            or PSTORE_PMSG_ENTRY_RE.fullmatch(entries[0]) is None
        ):
            raise ContractError("candidate return lacks one exact retained pmsg entry")
        entry = entries[0]
        path = f"{PSTORE_MOUNT_PATH}/{entry}"
        digest_record = run_f1_cmd(
            args,
            [
                "run",
                "/bin/busybox",
                "sh",
                "-c",
                f"/bin/busybox sha256sum {staging.shlex.quote(path)}",
            ],
        )
        digests = re.findall(
            r"\b[0-9a-f]{64}\b",
            str(digest_record.get("text") or ""),
        )
        if len(digests) != 1:
            raise ContractError("retained pmsg digest is not exact")
        digest = digests[0]
        content = run_f1_cmd(args, ["cat", path])
        content_text = str(content.get("text") or "")
        armed_token = f"{RETAINED_PMSG_MARKER} {RETAINED_PMSG_REQUIRED_PHASE} "
        armed_count = content_text.count(armed_token)
        classification = _retained_pmsg_classification(content_text)
        capture = {
            "schema": "a90_v3405_retained_pmsg_capture_v1",
            "run_id": spec.stage.run_id,
            "manifest_sha256": spec.stage.manifest_sha256,
            "rootfs_sha256": spec.stage.local_sha256,
            "marker": RETAINED_PMSG_MARKER,
            "required_phase": RETAINED_PMSG_REQUIRED_PHASE,
            "armed_count": armed_count,
            "classification": classification,
            "entry": entry,
            "sha256": digest,
            "mount": mount,
            "listing": listing,
            "summary": summary,
            "digest": digest_record,
            "content": content,
            "private_fsync_before_cleanup": True,
        }
        write_private_json_exclusive(
            transaction_dir / "retained-pmsg-capture.json",
            capture,
        )
        if armed_count != 1:
            raise ContractError("retained pmsg lacks one exact armed positive control")

        cleanup_intent = {
            "schema": "a90_v3405_retained_pmsg_cleanup_intent_v1",
            "run_id": spec.stage.run_id,
            "manifest_sha256": spec.stage.manifest_sha256,
            "entry": entry,
            "sha256": digest,
            "capture_fsynced": True,
            "exact_unlink_pending": True,
        }
        write_private_json_exclusive(
            transaction_dir / "retained-pmsg-cleanup-intent.json",
            cleanup_intent,
        )
        cleanup_script = "\n".join(
            (
                "set -eu",
                f"P={staging.shlex.quote(path)}",
                f"EXPECTED={staging.shlex.quote(digest)}",
                'ACTUAL=$(/bin/busybox sha256sum "$P")',
                'ACTUAL=${ACTUAL%% *}',
                '[ "$ACTUAL" = "$EXPECTED" ]',
                '/bin/busybox rm "$P"',
                "echo A90D3RET_PMSG_CLEANUP exact=1",
            )
        )
        cleanup = run_f1_cmd(
            args,
            ["run", "/bin/busybox", "sh", "-c", cleanup_script],
        )
        listing_after = run_f1_cmd(args, ["ls", PSTORE_MOUNT_PATH])
        if _pstore_entry_names(str(listing_after.get("text") or "")):
            raise ContractError("retained pmsg cleanup did not leave pstore empty")
        unmount = run_f1_cmd(args, ["umount", PSTORE_MOUNT_PATH])
        mounted = False
    finally:
        if mounted:
            run_f1_cmd(
                args,
                ["umount", PSTORE_MOUNT_PATH],
                allow_error=True,
            )

    cleanup_receipt = {
        "schema": "a90_v3405_retained_pmsg_cleanup_v1",
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "entry": entry,
        "sha256": digest,
        "capture_fsynced_before_unlink": True,
        "exact_unlink": True,
        "pstore_empty_after": True,
        "unmounted": True,
        "cleanup": cleanup,
        "listing_after": listing_after,
        "unmount": unmount,
    }
    write_private_json_exclusive(
        transaction_dir / "retained-pmsg-cleanup.json",
        cleanup_receipt,
    )
    return {
        "proof": True,
        "armed_positive_control": True,
        "classification": classification,
        "entry_sha256": digest,
        "capture_fsynced_before_cleanup": True,
        "exact_cleanup": True,
        "pstore_empty_after": True,
    }


def remote_source_preflight_script(spec: F1Spec) -> str:
    final = staging.shlex.quote(spec.stage.remote_final)
    work = staging.shlex.quote(spec.stage.remote_work)
    return "\n".join(
        (
            "set -eu",
            f"FINAL={final}",
            f"WORK={work}",
            f'EXPECTED_SIZE={staging.shlex.quote(str(spec.stage.local_size))}',
            f'EXPECTED_SHA={staging.shlex.quote(spec.stage.local_sha256)}',
            '[ -f "$FINAL" ]',
            '[ ! -L "$FINAL" ]',
            '[ ! -e "$WORK" ]',
            '[ ! -L "$WORK" ]',
            'ACTUAL_SIZE=$(/bin/busybox stat -c %s "$FINAL")',
            '[ "$ACTUAL_SIZE" = "$EXPECTED_SIZE" ]',
            'ACTUAL_SHA=$(/bin/busybox sha256sum "$FINAL")',
            'ACTUAL_SHA=${ACTUAL_SHA%% *}',
            '[ "$ACTUAL_SHA" = "$EXPECTED_SHA" ]',
            'echo A90F1_SOURCE_PRECHECK exact=1 work_absent=1',
        )
    )


def remote_source_preflight(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    return run_f1_shell(args, remote_source_preflight_script(spec))


def verify_candidate_health(
    spec: F1Spec,
    args: argparse.Namespace,
    *,
    return_guard: cdc_guard.ModemManagerGuard | None = None,
) -> dict[str, Any]:
    bridge = staging.require_exact_bridge(spec.stage, args)
    guard_proof = None
    if return_guard is not None:
        if not return_guard.healthy(recheck=True):
            raise ContractError("resident promotion guard was lost before first health")
        guard_proof = require_returned_modemmanager_guard(
            spec,
            {"returned": {"selected_realpath": spec.stage.bridge_realpath}},
            return_guard,
        )
    version = run_f1_cmd(args, ["version"])
    selftest = run_f1_cmd(args, ["selftest"])
    if return_guard is not None and not return_guard.healthy(recheck=True):
        raise ContractError("resident promotion guard was lost during first health")
    version_text = str(version.get("text") or "")
    if (
        spec.candidate_version not in version_text
        or spec.candidate_build not in version_text
    ):
        raise ContractError("candidate boot identity lacks exact version/build")
    if "fail=0" not in str(selftest.get("text") or ""):
        raise ContractError("candidate boot selftest is not fail=0")
    result = {
        "exact_bridge": True,
        "selected_realpath": bridge.get("selected_realpath"),
        "version": version,
        "selftest": selftest,
    }
    if guard_proof is not None:
        result["candidate_boot_modemmanager_guard"] = guard_proof
    return result


def run_handoff(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    validate_handoff_timeout(spec.handoff_timeout)
    line = a90ctl.encode_cmdv1_line(list(spec.handoff_command))
    minimum_read_budget = (
        float(spec.handoff_timeout) - F1_HANDOFF_MAX_PRE_READ_SEC
    )
    if minimum_read_budget <= 0.0:
        raise ContractError("handoff timeout cannot reserve its read budget")
    text = a90ctl.bridge_exchange(
        args.bridge_host,
        args.bridge_port,
        line,
        spec.handoff_timeout,
        markers=(b"exec_switch_root_now", b"A90P1 END "),
        input_mode=F1_SERIAL_INPUT_MODE,
        input_char_delay_sec=F1_SERIAL_INPUT_CHAR_DELAY_SEC,
        minimum_read_budget_sec=minimum_read_budget,
        require_prompt_after_end=False,
        post_marker_drain_sec=0.3,
    )
    missing = [marker for marker in OBSERVATION_OUTPUT_MARKERS if marker not in text]
    for phase in F1_HANDOFF_SOURCE_SHA_PHASES:
        exact = (
            f"source_sha phase={phase} sha={spec.stage.local_sha256} "
            "expected_sha_match=1"
        )
        if exact not in text:
            missing.append(exact)
    if "A90P1 END " in text and "exec_switch_root_now" not in text:
        missing.append("handoff returned before exec")
    if missing:
        raise RuntimeError(f"handoff proof missing: {missing}")
    return {"proof": True, "text": text}


def ssh_command(spec: F1Spec, args: argparse.Namespace) -> list[str]:
    if spec.display_required:
        remote_script = (
            f"echo {DISPLAY_D3_BEGIN}; "
            "cat /run/a90-d3-marker 2>/dev/null; "
            f"echo {DISPLAY_D3_END}; "
            f"echo {DISPLAY_RELEASE_BEGIN}; "
            "cat /run/a90-native-display-release 2>/dev/null; "
            f"echo {DISPLAY_RELEASE_END}; "
            f"echo {DISPLAY_READY_BEGIN}; "
            "cat /run/a90-display/ready 2>/dev/null; "
            f"echo {DISPLAY_READY_END}; "
            f"echo {DISPLAY_FAILURE_BEGIN}; "
            "cat /run/a90-display/failure 2>/dev/null; "
            f"echo {DISPLAY_FAILURE_END}; "
            f"echo {DISPLAY_PRESENTER_LOG_BEGIN}; "
            "cat /run/a90-display/presenter.log 2>/dev/null; "
            f"echo {DISPLAY_PRESENTER_LOG_END}; "
            f"echo {DISPLAY_DIAGNOSTICS_BEGIN}; "
            "if [ -c /dev/dri/card0 ]; then echo drm.card0=char; "
            "else echo drm.card0=absent; fi; "
            "for p in /sys/class/drm/card0-*/status; do "
            "[ -r \"$p\" ] || continue; d=${p%/status}; "
            "n=${d##*/}; printf 'drm.%s.status=' \"$n\"; cat \"$p\"; done; "
            "for p in /sys/class/drm/card0-*/dpms; do "
            "[ -r \"$p\" ] || continue; d=${p%/dpms}; "
            "n=${d##*/}; printf 'drm.%s.dpms=' \"$n\"; cat \"$p\"; done; "
            "for d in /sys/class/backlight/*; do [ -d \"$d\" ] || continue; "
            "n=${d##*/}; for f in bl_power brightness actual_brightness "
            "max_brightness; do [ -r \"$d/$f\" ] || continue; "
            "printf 'backlight.%s.%s=' \"$n\" \"$f\"; cat \"$d/$f\"; "
            "done; done; "
            f"echo {DISPLAY_DIAGNOSTICS_END}; "
            "echo pid1_comm=$(cat /proc/1/comm 2>/dev/null); "
            "echo proc1_exe=$(readlink /proc/1/exe 2>/dev/null); true"
        )
    else:
        remote_script = (
            "cat /run/a90-d3-marker 2>/dev/null; "
            "echo pid1_comm=$(cat /proc/1/comm 2>/dev/null); "
            "echo proc1_exe=$(readlink /proc/1/exe 2>/dev/null)"
        )
    return [
        "ssh",
        "-i",
        str(spec.observer_key),
        "-p",
        str(spec.observer_port),
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        f"ConnectTimeout={int(args.ssh_connect_timeout)}",
        "-o",
        "BatchMode=yes",
        f"root@{spec.observer_device}",
        remote_script,
    ]


def exact_ssh_section(text: str, begin: str, end: str) -> str:
    begin_line = begin + "\n"
    end_line = end + "\n"
    if text.count(begin_line) != 1 or text.count(end_line) != 1:
        raise ContractError(f"SSH observation section is not exact: {begin}")
    prefix, suffix = text.split(begin_line, 1)
    content, tail = suffix.split(end_line, 1)
    if prefix and not prefix.endswith("\n"):
        raise ContractError(f"SSH observation section prefix is malformed: {begin}")
    if tail and not tail.endswith("\n"):
        raise ContractError(f"SSH observation section suffix is malformed: {end}")
    return content


def _phase2_line_state(text: str, key: str, expected: str) -> bool | None:
    matches = re.findall(rf"^{re.escape(key)}=(.*)$", text, re.MULTILINE)
    if len(matches) != 1:
        return None
    return matches[0] == expected


def classify_phase2_ssh_attempt(
    spec: F1Spec,
    *,
    returncode: int,
    text: str,
) -> tuple[dict[str, Any], bool]:
    sections: dict[str, str | None] = {}
    errors: dict[str, str] = {}
    for name, begin, end in (
        ("d3", DISPLAY_D3_BEGIN, DISPLAY_D3_END),
        ("release", DISPLAY_RELEASE_BEGIN, DISPLAY_RELEASE_END),
        ("ready", DISPLAY_READY_BEGIN, DISPLAY_READY_END),
        ("failure", DISPLAY_FAILURE_BEGIN, DISPLAY_FAILURE_END),
        (
            "presenter_log",
            DISPLAY_PRESENTER_LOG_BEGIN,
            DISPLAY_PRESENTER_LOG_END,
        ),
        (
            "display_diagnostics",
            DISPLAY_DIAGNOSTICS_BEGIN,
            DISPLAY_DIAGNOSTICS_END,
        ),
    ):
        try:
            sections[name] = exact_ssh_section(text, begin, end)
        except ContractError as exc:
            sections[name] = None
            errors[name] = str(exc)

    d3_marker = sections["d3"]
    if d3_marker is None:
        dropbear_started: bool | None = None
    else:
        d3_lines = d3_marker.splitlines()
        schema_lines = [
            line for line in d3_lines if line.startswith("A90D3_MARKER")
        ]
        dropbear_lines = [
            line for line in d3_lines if line.startswith("dropbear_started=")
        ]
        dropbear_started = (
            schema_lines == ["A90D3_MARKER"]
            and dropbear_lines == ["dropbear_started=1"]
        )
    pid1_comm_init = (
        None
        if d3_marker is None
        else _phase2_line_state(d3_marker, "pid1_comm", "init")
    )
    proc1_exe_init = (
        None
        if d3_marker is None
        else _phase2_line_state(d3_marker, "proc1_exe", "/usr/sbin/init")
    )
    ready_marker = sections["ready"] or ""
    failure_marker = sections["failure"] or ""
    terminal_signal = bool(ready_marker or failure_marker) or (
        "schema=a90-debian-display-v1\n" in text
        or "schema=a90-debian-display-v1-failure\n" in text
    )
    display_status = "unknown"
    display_marker: dict[str, str] = {}
    if returncode == 0 and sections["ready"] is not None and sections["failure"] is not None:
        if bool(ready_marker) != bool(failure_marker):
            try:
                if ready_marker:
                    display_marker = display.validate_debian_ready_marker(
                        ready_marker,
                        display_uid=spec.display_uid,
                        display_gid=spec.display_gid,
                    )
                    display_status = "ready"
                else:
                    display_marker = display.validate_bounded_failure_marker(
                        failure_marker,
                        max_attempts=spec.display_max_attempts,
                        ready_absent=True,
                    )
                    display_status = "bounded-failure"
            except display.ContractError as exc:
                errors["display_marker"] = str(exc)
        elif ready_marker or failure_marker:
            errors["display_marker"] = (
                "Phase 2 ready/failure markers are ambiguous"
            )
    result = {
        "proof": display_status == "ready",
        "pid1_comm_init": pid1_comm_init,
        "proc1_exe_init": proc1_exe_init,
        "dropbear_started": dropbear_started,
        "display_status": display_status,
        "display_marker": display_marker,
        "display_marker_text": (
            ready_marker if ready_marker else failure_marker
        ),
        "native_release_marker_text": sections["release"] or "",
        "presenter_log_text": sections["presenter_log"] or "",
        "display_diagnostics_text": sections["display_diagnostics"] or "",
        "observation_errors": errors,
        "text": text,
    }
    terminal = display_status in {"ready", "bounded-failure"} or terminal_signal
    return result, terminal


def observe_ssh(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    deadline = time.monotonic() + spec.ssh_marker_timeout
    attempts = 0
    last: dict[str, Any] | None = None
    last_partial: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        attempts += 1
        try:
            completed = subprocess.run(
                ssh_command(spec, args),
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                timeout=args.ssh_connect_timeout + 10.0,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            last = {
                "returncode": None,
                "error": f"TimeoutExpired: {exc}",
                "text": "",
            }
            time.sleep(args.poll_interval)
            continue
        text = completed.stdout + completed.stderr
        last = {"returncode": completed.returncode, "text": text}
        proc1_init = re.search(r"^pid1_comm=init$", text, re.MULTILINE) is not None
        proc1_exe = re.search(r"^proc1_exe=\S*/init$", text, re.MULTILINE) is not None
        if spec.display_required:
            partial, terminal = classify_phase2_ssh_attempt(
                spec,
                returncode=completed.returncode,
                text=text,
            )
            partial["attempts"] = attempts
            last_partial = partial
            if terminal:
                return partial
        if (
            not spec.display_required
            and completed.returncode == 0
            and "A90D3_MARKER" in text
            and proc1_init
            and proc1_exe
            and "dropbear_started=1" in text
        ):
            return {
                "proof": True,
                "attempts": attempts,
                "pid1_comm_init": True,
                "proc1_exe_init": True,
                "dropbear_started": True,
                "text": text,
            }
        time.sleep(args.poll_interval)
    if spec.display_required:
        if last_partial is None:
            last_partial = {
                "proof": False,
                "attempts": attempts,
                "pid1_comm_init": None,
                "proc1_exe_init": None,
                "dropbear_started": None,
                "display_status": "unknown",
                "display_marker": {},
                "display_marker_text": "",
                "native_release_marker_text": "",
                "presenter_log_text": "",
                "display_diagnostics_text": "",
                "observation_errors": {"timeout": str(last)},
                "text": "",
            }
        last_partial["timed_out"] = True
        return last_partial
    raise RuntimeError(f"Debian PID1 marker timeout after {attempts} attempts; last={last}")


def _verify_candidate_after_return_epoch_once(
    spec: F1Spec,
    args: argparse.Namespace,
    before_handoff: dict[str, Any],
    *,
    phase: str,
    return_guard: cdc_guard.ModemManagerGuard | None = None,
) -> dict[str, Any]:
    epoch = wait_for_new_bridge_serial_epoch(spec, args, before_handoff)
    guard_evidence: dict[str, Any] | None = None
    if return_guard is not None:
        if not return_guard.healthy(recheck=True):
            raise ContractError("candidate-return ModemManager guard was lost")
        guard_evidence = require_returned_modemmanager_guard(
            spec,
            epoch,
            return_guard,
        )
        if not return_guard.healthy(recheck=True):
            raise ContractError(
                "candidate-return ModemManager guard was lost before command"
            )
    version = run_f1_cmd(args, ["version"])
    version_text = str(version.get("text") or "")
    expected_version_line = (
        f"version: {spec.candidate_version} build={spec.candidate_build}"
    )
    version_lines = [
        line for line in version_text.splitlines() if line.startswith("version: ")
    ]
    if version_lines != [expected_version_line]:
        raise ContractError("candidate return native epoch identity is not exact")
    channel = settle_observation_channel(args, phase=phase)
    selftest = run_f1_cmd(args, ["selftest"])
    selftest_lines = [
        line
        for line in str(selftest.get("text") or "").splitlines()
        if line.startswith("selftest: ")
    ]
    if (
        len(selftest_lines) != 1
        or re.fullmatch(
            r"selftest: pass=[0-9]+ warn=[0-9]+ fail=0 "
            r"duration=[0-9]+ms entries=[1-9][0-9]*",
            selftest_lines[0],
        )
        is None
    ):
        raise ContractError("candidate return selftest is not fail=0")
    result = {
        "exact_bridge": True,
        "selected_realpath": epoch["returned"]["selected_realpath"],
        "return_epoch": epoch,
        "native_epoch_version_proven": True,
        "channel": channel,
        "version": version,
        "selftest": selftest,
        "device_command_sequences": 1,
    }
    if guard_evidence is not None:
        result["candidate_return_modemmanager_guard"] = guard_evidence
    return result


def wait_for_candidate_return(
    spec: F1Spec,
    args: argparse.Namespace,
    before_handoff: dict[str, Any],
) -> dict[str, Any]:
    return _verify_candidate_after_return_epoch_once(
        spec,
        args,
        before_handoff,
        phase="candidate-return",
    )


def observe_candidate(spec: F1Spec, args: argparse.Namespace, transaction_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "proof": False,
        "handoff_dispatch_started": False,
    }
    try:
        result["channel_before_source"] = settle_observation_channel(
            args,
            phase="before-source-preflight",
        )
        result["host_ncm_rebind"] = rebind_host_ncm_after_reenumeration(
            spec,
            args,
        )
        result["pstore_before_handoff"] = require_clean_pstore_before_handoff(
            args,
        )
        result["source_preflight"] = remote_source_preflight(spec, args)
        result["channel_before_handoff"] = settle_observation_channel(
            args,
            phase="before-handoff",
        )
        result["return_epoch_before_handoff"] = capture_bridge_serial_epoch(
            spec,
            args,
        )
        result["handoff_dispatch_started"] = True
        result["handoff"] = run_handoff(spec, args)
        result["ssh"] = observe_ssh(spec, args)
        result["proof"] = True
    except Exception as exc:  # noqa: BLE001 - rollback remains mandatory
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        try:
            if result["handoff_dispatch_started"]:
                result["candidate_return"] = wait_for_candidate_return(
                    spec,
                    args,
                    result["return_epoch_before_handoff"],
                )
            else:
                result["candidate_return"] = {
                    "no_handoff_dispatched": True,
                    "health": verify_candidate_health(spec, args),
                }
            if result["handoff_dispatch_started"]:
                result["retained_pmsg"] = collect_and_clear_retained_pmsg(
                    spec,
                    args,
                    transaction_dir,
                )
            else:
                result["retained_pmsg"] = {
                    "proof": False,
                    "not_expected_without_handoff": True,
                }
        except Exception as exc:  # noqa: BLE001 - recovery must resume later
            result["candidate_return_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
            result["proof"] = False
    write_private_json_exclusive(transaction_dir / "observation.json", result)
    return result


def attended_retryable_error_identity(
    error_type: str,
    message: str,
    *,
    attempt: int,
) -> bool:
    phases = (
        f"attended-attempt-{attempt}-before-health",
        f"attended-attempt-{attempt}-before-handoff",
    )
    if error_type == "ContractError":
        return message in {
            f"{phase} {suffix}"
            for phase in phases
            for suffix in ATTENDED_RETRYABLE_CHANNEL_ERRORS[1:]
        }
    if error_type == "RuntimeError":
        marker = ATTENDED_RETRYABLE_CHANNEL_ERRORS[0]
        return message == marker or message.startswith(marker + "\n")
    return False


def attended_pre_handoff_retryable(
    exc: Exception,
    *,
    attempt: int,
) -> bool:
    if type(exc) not in (ContractError, RuntimeError):
        return False
    return attended_retryable_error_identity(
        type(exc).__name__,
        str(exc),
        attempt=attempt,
    )


def attended_stored_failure_retryable(
    error: Any,
    *,
    attempt: int,
) -> bool:
    return (
        isinstance(error, dict)
        and set(error) == {"type", "message"}
        and isinstance(error.get("type"), str)
        and isinstance(error.get("message"), str)
        and attended_retryable_error_identity(
            error["type"],
            error["message"],
            attempt=attempt,
        )
    )


def wait_for_candidate_return_attended_once(
    spec: F1Spec,
    args: argparse.Namespace,
    before_handoff: dict[str, Any],
    return_guard: cdc_guard.ModemManagerGuard | None = None,
) -> dict[str, Any]:
    return _verify_candidate_after_return_epoch_once(
        spec,
        args,
        before_handoff,
        phase="attended-candidate-return",
        return_guard=return_guard,
    )


def observe_attended_after_handoff(
    spec: F1Spec,
    args: argparse.Namespace,
    transaction_dir: Path,
    pre_handoff: dict[str, Any],
    return_guard: cdc_guard.ModemManagerGuard | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "proof": False,
        "pre_handoff": pre_handoff,
        "handoff_attempt_limit": spec.handoff_attempt_limit,
    }
    try:
        result["handoff"] = run_handoff(spec, args)
        result["ssh"] = observe_ssh(spec, args)
        if spec.display_required:
            facts = display.classify_phase2_display_facts(
                handoff_log=result["handoff"]["text"],
                native_release_marker=result["ssh"][
                    "native_release_marker_text"
                ],
                pid1_comm_init=result["ssh"].get("pid1_comm_init"),
                proc1_exe_init=result["ssh"].get("proc1_exe_init"),
                dropbear_started=result["ssh"].get("dropbear_started"),
                display_status=str(result["ssh"].get("display_status")),
            )
            result["facts"] = display.facts_to_dict(facts)
            result["native_release_proven"] = (
                facts["native_release"].state is display.FactState.PROVEN
            )
            result["debian_pid1_proven"] = (
                facts["debian_pid1"].state is display.FactState.PROVEN
            )
            result["dropbear_proven"] = (
                facts["dropbear"].state is display.FactState.PROVEN
            )
            result["display_status"] = result["ssh"]["display_status"]
            result["display_mechanical_proof"] = (
                result["native_release_proven"]
                and result["debian_pid1_proven"]
                and result["dropbear_proven"]
                and facts["display_acquisition"].state
                is display.FactState.PROVEN
            )
            result["bounded_display_failure"] = (
                facts["display_acquisition"].state
                is display.FactState.REFUTED
            )
            result["visible_confirmation_required"] = (
                result["display_mechanical_proof"]
            )
            result["proof"] = False
        else:
            result["proof"] = True
    except Exception as exc:  # noqa: BLE001 - rollback remains mandatory
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        try:
            result["candidate_return"] = (
                wait_for_candidate_return_attended_once(
                    spec,
                    args,
                    pre_handoff["return_epoch_before_handoff"],
                    return_guard=return_guard,
                )
            )
        except Exception as exc:  # noqa: BLE001 - recovery must resume later
            result["candidate_return_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
            result["proof"] = False
        finally:
            if return_guard is not None:
                try:
                    release = release_candidate_return_modemmanager_guard(
                        return_guard,
                        transaction_dir,
                    )
                except Exception as exc:  # noqa: BLE001 - preserve evidence
                    release = {
                        "schema": cdc_guard.GUARD_SCHEMA,
                        "status": "release-evidence-failed",
                        "released": False,
                        "error_type": type(exc).__name__,
                    }
                result["candidate_return_modemmanager_guard_release"] = release
                if release.get("released") is not True:
                    result.pop("candidate_return", None)
                    result["candidate_return_error"] = {
                        "type": "ContractError",
                        "message": (
                            "candidate-return ModemManager guard did not "
                            "release exactly"
                        ),
                    }
                    result["proof"] = False
        if "candidate_return" in result:
            try:
                result["retained_pmsg"] = collect_and_clear_retained_pmsg(
                    spec,
                    args,
                    transaction_dir,
                )
            except Exception as exc:  # noqa: BLE001 - recovery resumes later
                result["retained_pmsg_error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
                result["proof"] = False
    write_private_json_exclusive(transaction_dir / "observation.json", result)
    return result


def display_visible_path(transaction_dir: Path) -> Path:
    return transaction_dir / "display-visible-confirmation.json"


def display_visible_binding(
    spec: F1Spec,
    approval_prepared: dict[str, Any],
    attended_receipt: dict[str, Any],
    open_record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "a90_v3406_f1_display_visible_binding_v1",
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "approval_binding_sha256": approval_prepared[
            "approval_binding_sha256"
        ],
        "candidate_boot_sha256": spec.candidate.sha256,
        "rollback_boot_sha256": spec.rollback.sha256,
        "final_keyed_rootfs_sha256": spec.stage.local_sha256,
        "display_profile": spec.display_profile,
        "display_ready_marker_sha256": open_record.get(
            "display_ready_marker_sha256"
        ),
        "visible_text_sha256": json_sha256(list(spec.display_visible_text)),
        "confirmation_open_sequence": open_record.get("sequence"),
        "confirmation_opened_utc": open_record.get("timestamp_utc"),
        "observation_deadline_utc": attended_receipt[
            "continue_binding"
        ]["window_deadline_utc"],
        "candidate_returned": True,
        "retained_pmsg_captured_and_cleaned": True,
        "candidate_replay": False,
        "rollback_pre_authorized": True,
        "only_partition_payload": "boot",
    }


def open_display_visible_confirmation(
    spec: F1Spec,
    approval_prepared: dict[str, Any],
    attended_receipt: dict[str, Any],
    transaction_dir: Path,
    journal_dir: Path,
    observation: dict[str, Any],
) -> dict[str, Any]:
    if (
        not spec.display_required
        or observation.get("display_mechanical_proof") is not True
        or observation.get("visible_confirmation_required") is not True
        or "candidate_return" not in observation
        or observation.get("retained_pmsg", {}).get("proof") is not True
    ):
        raise ContractError(
            "display visible confirmation requires complete mechanical proof and return"
        )
    deadline = parse_utc_timestamp(
        attended_receipt["continue_binding"]["window_deadline_utc"],
        "display visible observation deadline",
    )
    if current_utc() > deadline:
        raise ContractError(
            "display visible observation window expired; rollback only"
        )
    marker_text = observation["ssh"].get("display_marker_text")
    if not isinstance(marker_text, str):
        raise ContractError("display ready marker text is absent")
    display.validate_debian_ready_marker(
        marker_text,
        display_uid=spec.display_uid,
        display_gid=spec.display_gid,
    )
    marker_sha256 = hashlib.sha256(marker_text.encode("utf-8")).hexdigest()
    path = append_record(
        journal_dir,
        "OBSERVED",
        "display-visible-confirmation-open",
        {
            "display_ready_marker_sha256": marker_sha256,
            "observation_deadline_utc": deadline.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "candidate_returned": True,
            "retained_pmsg_captured_and_cleaned": True,
            "candidate_replay": False,
            "rollback_required": True,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    open_record = json.loads(path.read_text(encoding="utf-8"))
    binding = display_visible_binding(
        spec,
        approval_prepared,
        attended_receipt,
        open_record,
    )
    binding_sha256 = json_sha256(binding)
    receipt = {
        "schema": DISPLAY_VISIBLE_SCHEMA,
        "created_utc": utc_now(),
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "visible_binding": binding,
        "visible_binding_sha256": binding_sha256,
        "visible_token": DISPLAY_VISIBLE_PREFIX + binding_sha256,
        "expected_visible_text": list(spec.display_visible_text),
        "operator_attestation_required": True,
        "candidate_already_returned": True,
        "additional_partition_authority": False,
        "candidate_replay": False,
        "rollback_pre_authorized": True,
    }
    write_private_json_exclusive(
        display_visible_path(transaction_dir),
        receipt,
    )
    return {
        "schema": ORCHESTRATOR_SCHEMA,
        "status": "PAUSED_F1_V2_DISPLAY_VISIBLE_CONFIRMATION",
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "visible_token": receipt["visible_token"],
        "observation_deadline_utc": binding["observation_deadline_utc"],
        "expected_visible_text": list(spec.display_visible_text),
        "candidate_transfer_count": 1,
        "candidate_returned": True,
        "retained_pmsg_captured_and_cleaned": True,
        "candidate_replay": False,
        "rollback_required": True,
        "additional_partition_authority": False,
    }


def load_display_visible_confirmation(
    spec: F1Spec,
    approval_prepared: dict[str, Any],
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    if not spec.display_required:
        raise ContractError("manifest does not require display confirmation")
    path = display_visible_path(transaction_dir)
    require_private_regular(path)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    opens = [
        record
        for record in records
        if record.get("action") == "display-visible-confirmation-open"
    ]
    if len(opens) != 1:
        raise ContractError("display confirmation requires one exact open record")
    open_record = opens[0]
    expected_record_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
        "display_ready_marker_sha256",
        "observation_deadline_utc",
        "candidate_returned",
        "retained_pmsg_captured_and_cleaned",
        "candidate_replay",
        "rollback_required",
    }
    attended = load_attended_window(
        spec,
        approval_prepared,
        transaction_dir,
        records,
    )
    binding = display_visible_binding(
        spec,
        approval_prepared,
        attended,
        open_record,
    )
    binding_sha256 = json_sha256(binding)
    expected_receipt_keys = {
        "schema",
        "created_utc",
        "run_id",
        "manifest_sha256",
        "visible_binding",
        "visible_binding_sha256",
        "visible_token",
        "expected_visible_text",
        "operator_attestation_required",
        "candidate_already_returned",
        "additional_partition_authority",
        "candidate_replay",
        "rollback_pre_authorized",
    }
    if (
        set(open_record) != expected_record_keys
        or open_record.get("state") != "OBSERVED"
        or open_record.get("candidate_returned") is not True
        or open_record.get("retained_pmsg_captured_and_cleaned") is not True
        or open_record.get("candidate_replay") is not False
        or open_record.get("rollback_required") is not True
        or not isinstance(receipt, dict)
        or set(receipt) != expected_receipt_keys
        or receipt.get("schema") != DISPLAY_VISIBLE_SCHEMA
        or not is_canonical_utc_timestamp(receipt.get("created_utc"))
        or receipt.get("run_id") != spec.stage.run_id
        or receipt.get("manifest_sha256") != spec.stage.manifest_sha256
        or receipt.get("visible_binding") != binding
        or receipt.get("visible_binding_sha256") != binding_sha256
        or receipt.get("visible_token")
        != DISPLAY_VISIBLE_PREFIX + binding_sha256
        or receipt.get("expected_visible_text")
        != list(spec.display_visible_text)
        or receipt.get("operator_attestation_required") is not True
        or receipt.get("candidate_already_returned") is not True
        or receipt.get("additional_partition_authority") is not False
        or receipt.get("candidate_replay") is not False
        or receipt.get("rollback_pre_authorized") is not True
    ):
        raise ContractError("display confirmation receipt lost its exact binding")
    return receipt


def validate_confirmed_display_proof(
    spec: F1Spec,
    approval_prepared: dict[str, Any],
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    receipt = load_display_visible_confirmation(
        spec,
        approval_prepared,
        transaction_dir,
        records,
    )
    confirmations = [
        record
        for record in records
        if record.get("action") == "display-visible-confirmed"
    ]
    observations = [
        record
        for record in records
        if record.get("action") == "observation-no-proof"
    ]
    if len(confirmations) != 1 or len(observations) != 1:
        raise ContractError(
            "display proof requires one exact observation and confirmation"
        )
    confirmation = confirmations[0]
    observation_record = observations[0]
    confirmation_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
        "visible_binding_sha256",
        "operator_attested_exact_visible_text",
        "display_ready_marker_sha256",
        "visible_text_sha256",
        "within_observation_deadline",
        "candidate_returned",
        "candidate_replay",
        "rollback_required",
    }
    observation_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
        "debian_pid1_proven",
        "native_release_proven",
        "display_mechanical_proven",
        "bounded_display_failure",
        "visible_confirmation_required",
        "retained_pmsg_armed_proven",
        "retained_pmsg_cleaned",
        "candidate_replay",
        "rollback_required",
        "candidate_returned",
        "handoff_attempt_count",
    }
    binding = receipt["visible_binding"]
    deadline = parse_utc_timestamp(
        binding["observation_deadline_utc"],
        "display visible observation deadline",
    )
    opened = parse_utc_timestamp(
        binding["confirmation_opened_utc"],
        "display visible confirmation opened",
    )
    confirmed = parse_utc_timestamp(
        confirmation.get("timestamp_utc"),
        "display visible confirmation",
    )
    if (
        set(observation_record) != observation_keys
        or observation_record.get("state") != "OBSERVED"
        or observation_record.get("debian_pid1_proven") is not True
        or observation_record.get("native_release_proven") is not True
        or observation_record.get("display_mechanical_proven") is not True
        or observation_record.get("bounded_display_failure") is not False
        or observation_record.get("visible_confirmation_required") is not True
        or observation_record.get("retained_pmsg_armed_proven") is not True
        or observation_record.get("retained_pmsg_cleaned") is not True
        or observation_record.get("candidate_replay") is not False
        or observation_record.get("rollback_required") is not True
        or observation_record.get("candidate_returned") is not True
        or observation_record.get("handoff_attempt_count") != 1
        or set(confirmation) != confirmation_keys
        or confirmation.get("state") != "OBSERVED"
        or confirmation.get("visible_binding_sha256")
        != receipt["visible_binding_sha256"]
        or confirmation.get("operator_attested_exact_visible_text") is not True
        or confirmation.get("display_ready_marker_sha256")
        != binding["display_ready_marker_sha256"]
        or confirmation.get("visible_text_sha256")
        != binding["visible_text_sha256"]
        or confirmation.get("within_observation_deadline") is not True
        or confirmation.get("candidate_returned") is not True
        or confirmation.get("candidate_replay") is not False
        or confirmation.get("rollback_required") is not True
        or not (
            observation_record["sequence"]
            < binding["confirmation_open_sequence"]
            < confirmation["sequence"]
        )
        or not opened <= confirmed <= deadline
    ):
        raise ContractError("display confirmation journal proof is not exact")

    observation_path = transaction_dir / "observation.json"
    require_private_regular(observation_path)
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    marker_text = (
        observation.get("ssh", {}).get("display_marker_text")
        if isinstance(observation, dict)
        else None
    )
    if (
        not isinstance(observation, dict)
        or observation.get("native_release_proven") is not True
        or observation.get("debian_pid1_proven") is not True
        or observation.get("display_status") != "ready"
        or observation.get("display_mechanical_proof") is not True
        or observation.get("bounded_display_failure") is not False
        or observation.get("visible_confirmation_required") is not True
        or "candidate_return" not in observation
        or observation.get("retained_pmsg", {}).get("proof") is not True
        or not isinstance(marker_text, str)
    ):
        raise ContractError(
            "display confirmation lost its exact observation evidence"
        )
    display.validate_debian_ready_marker(
        marker_text,
        display_uid=spec.display_uid,
        display_gid=spec.display_gid,
    )
    if (
        hashlib.sha256(marker_text.encode("utf-8")).hexdigest()
        != binding["display_ready_marker_sha256"]
    ):
        raise ContractError("display ready marker does not match confirmation")

    result_path = transaction_dir / "display-visible-confirmation-result.json"
    require_private_regular(result_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    expected_result = {
        "schema": "a90_v3406_f1_display_visible_result_v1",
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "visible_binding_sha256": receipt["visible_binding_sha256"],
        "confirmation_sequence": confirmation["sequence"],
        "confirmation_timestamp_utc": confirmation["timestamp_utc"],
        "operator_attested_exact_visible_text": True,
        "candidate_replay": False,
        "rollback_required": True,
    }
    if result != expected_result:
        raise ContractError("display confirmation result lost its exact binding")
    return {
        "proof": True,
        "receipt": receipt,
        "confirmation": confirmation,
        "observation_sha256": sha256_file(observation_path),
        "result_sha256": sha256_file(result_path),
    }


def verify_final_health(
    spec: F1Spec,
    args: argparse.Namespace,
    *,
    return_guard: cdc_guard.ModemManagerGuard | None = None,
) -> dict[str, Any]:
    bridge = staging.require_exact_bridge(spec.stage, args)
    if return_guard is not None and not return_guard.healthy(recheck=True):
        raise ContractError("rollback recovery guard was lost before final health")
    guard_proof = None
    if return_guard is not None:
        guard_proof = require_returned_modemmanager_guard(
            spec,
            {"returned": {"selected_realpath": spec.stage.bridge_realpath}},
            return_guard,
        )
    channel = settle_observation_channel(
        args,
        phase="before-final-health",
    )
    baseline = require_f1_baseline(args)
    if return_guard is not None and not return_guard.healthy(recheck=True):
        raise ContractError("rollback recovery guard was lost during final health")
    result = {
        "exact_bridge": True,
        "selected_realpath": bridge.get("selected_realpath"),
        "channel": channel,
        "version": spec.rollback_version,
        "build": spec.rollback_build,
        "selftest_fail_zero": True,
        "pstore_entries_zero": True,
        "baseline": baseline,
    }
    if guard_proof is not None:
        result["rollback_boot_modemmanager_guard"] = guard_proof
    return result


def require_rollback_source_native(
    spec: F1Spec,
    args: argparse.Namespace,
    *,
    return_guard: cdc_guard.ModemManagerGuard | None = None,
) -> dict[str, Any]:
    staging.require_exact_bridge(spec.stage, args)
    if return_guard is not None:
        if not return_guard.healthy(recheck=True):
            raise ContractError("rollback source guard is not live")
        require_returned_modemmanager_guard(
            spec,
            {"returned": {"selected_realpath": spec.stage.bridge_realpath}},
            return_guard,
        )
    version = run_f1_cmd(args, ["version"], allow_error=True)
    selftest = run_f1_cmd(args, ["selftest"], allow_error=True)
    if return_guard is not None and not return_guard.healthy(recheck=True):
        raise ContractError("rollback source guard was lost during health check")
    version_text = str(version.get("text") or "")
    known = (
        spec.candidate_version in version_text and spec.candidate_build in version_text
    ) or (
        spec.rollback_version in version_text and spec.rollback_build in version_text
    )
    if not known or "fail=0" not in str(selftest.get("text") or ""):
        raise ContractError("native rollback source is not the exact candidate or baseline")
    return {"version": version, "selftest": selftest}


def invoke_rollback(
    spec: F1Spec,
    args: argparse.Namespace,
    transaction_dir: Path,
    journal_dir: Path,
    events: list[dict[str, str]],
    *,
    from_native: bool,
    pre_spawn_retry_index: int = 0,
    allow_promotion: bool = False,
    return_guard: cdc_guard.ModemManagerGuard | None = None,
) -> dict[str, Any]:
    ensure_event(
        transaction_dir,
        events,
        "rollback_flash_start",
        allow_promotion=allow_promotion,
    )
    append_record(
        journal_dir,
        "RECOVERY_ROLLBACK",
        "rollback-transfer-started",
        {
            "rollback_sha256": spec.rollback.sha256,
            "rollback_attempt_limit": 1,
            "rollback_process_started": None,
            "candidate_replay": False,
            "recovery_mode": "from-native" if from_native else "adb-recovery",
            "prior_pre_spawn_rejections": pre_spawn_retry_index,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    if pre_spawn_retry_index:
        log_name = (
            f"rollback-flash-pre-spawn-retry-{pre_spawn_retry_index:04d}.raw.log"
        )
    else:
        log_name = "rollback-flash.raw.log"
    record = run_logged(
        flash_command(
            spec,
            args,
            rollback=True,
            from_native=from_native,
        ),
        log_path=transaction_dir / log_name,
        timeout=args.flash_command_timeout,
    )
    if record["returncode"] != 0:
        record["phase_classification"] = classify_flash_log(
            Path(str(record["raw_log"]))
        )
        execution_error = record.get("execution_error")
        if (
            record.get("process_started") is False
            and isinstance(execution_error, dict)
            and execution_error.get("stage") == "process-spawn"
        ):
            append_record(
                journal_dir,
                "RECOVERY_ROLLBACK",
                "rollback-process-not-started",
                {
                    "candidate_replay": False,
                    "rollback_process_started": False,
                    "rollback_transfer_count": 0,
                    "rollback_retry_preserved": True,
                    "record": record,
                },
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
            raise RuntimeError(
                "rollback helper did not start; recover rollback only"
            )
        append_record(
            journal_dir,
            "RECOVERY_ROLLBACK",
            "rollback-invocation-failed",
            {
                "candidate_replay": False,
                "rollback_retry_forbidden": True,
                "record": record,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        raise RuntimeError("rollback invocation failed; do not repeat it automatically")
    record["phase_classification"] = classify_flash_log(Path(str(record["raw_log"])))
    append_record(
        journal_dir,
        "ROLLBACK_FLASHED",
        "rollback-flashed",
        {
            "rollback_sha256": spec.rollback.sha256,
            "rollback_transfer_count": 1,
            "candidate_replay": False,
            "record": record,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    ensure_event(
        transaction_dir,
        events,
        "rollback_flash_done",
        allow_promotion=allow_promotion,
    )
    if allow_promotion and return_guard is None:
        raise ContractError(
            "rollback flashed; guarded final health requires recovery"
        )
    health = verify_final_health(
        spec,
        args,
        return_guard=return_guard,
    )
    append_record(
        journal_dir,
        "ROLLBACK_FLASHED",
        "rollback-boot-ready",
        {
            "rollback_version": spec.rollback_version,
            "rollback_build": spec.rollback_build,
            "selftest_fail_zero": True,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    ensure_event(
        transaction_dir,
        events,
        "rollback_boot_ready",
        allow_promotion=allow_promotion,
    )
    append_record(
        journal_dir,
        "HEALTH_VERIFIED",
        "health-verified",
        health,
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    return health


def rollback_pre_spawn_pair_is_exact(
    spec: F1Spec,
    transaction_dir: Path,
    intent: dict[str, Any],
    rejection: dict[str, Any],
    *,
    prior_rejections: int,
) -> tuple[bool, str | None]:
    common_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
    }
    intent_keys = common_keys | {
        "rollback_sha256",
        "rollback_attempt_limit",
        "rollback_process_started",
        "candidate_replay",
        "recovery_mode",
        "prior_pre_spawn_rejections",
    }
    rejection_keys = common_keys | {
        "candidate_replay",
        "rollback_process_started",
        "rollback_transfer_count",
        "rollback_retry_preserved",
        "record",
    }
    recovery_mode = intent.get("recovery_mode")
    if (
        set(intent) != intent_keys
        or set(rejection) != rejection_keys
        or intent.get("action") != "rollback-transfer-started"
        or rejection.get("action") != "rollback-process-not-started"
        or intent.get("state") != "RECOVERY_ROLLBACK"
        or rejection.get("state") != "RECOVERY_ROLLBACK"
        or type(intent.get("sequence")) is not int
        or type(rejection.get("sequence")) is not int
        or rejection.get("sequence") != intent.get("sequence", -2) + 1
        or not is_canonical_utc_timestamp(intent.get("timestamp_utc"))
        or not is_canonical_utc_timestamp(rejection.get("timestamp_utc"))
        or intent.get("rollback_sha256") != spec.rollback.sha256
        or type(intent.get("rollback_attempt_limit")) is not int
        or intent.get("rollback_attempt_limit") != 1
        or intent.get("rollback_process_started") is not None
        or intent.get("candidate_replay") is not False
        or recovery_mode not in ("from-native", "adb-recovery")
        or type(intent.get("prior_pre_spawn_rejections")) is not int
        or intent.get("prior_pre_spawn_rejections") != prior_rejections
        or rejection.get("candidate_replay") is not False
        or rejection.get("rollback_process_started") is not False
        or type(rejection.get("rollback_transfer_count")) is not int
        or rejection.get("rollback_transfer_count") != 0
        or rejection.get("rollback_retry_preserved") is not True
    ):
        return False, recovery_mode if isinstance(recovery_mode, str) else None

    execution = rejection.get("record")
    if not isinstance(execution, dict):
        return False, recovery_mode
    execution_keys = {
        "returncode",
        "raw_log",
        "raw_log_size",
        "raw_log_sha256",
        "process_started",
        "execution_error",
        "phase_classification",
    }
    execution_error = execution.get("execution_error")
    phase_classification = execution.get("phase_classification")
    phase_keys = {
        "local_image_validated",
        "native_recovery_requested",
        "recovery_endpoint_selected",
        "payload_transfer_started",
        "boot_write_started",
        "boot_write_completed",
        "readback_completed",
    }
    error_type = (
        execution_error.get("type")
        if isinstance(execution_error, dict)
        else None
    )
    if (
        set(execution) != execution_keys
        or type(execution.get("returncode")) is not int
        or execution.get("returncode") != 125
        or execution.get("process_started") is not False
        or not isinstance(execution_error, dict)
        or set(execution_error) != {"type", "stage", "errno"}
        or error_type != "OSError"
        or execution_error.get("stage") != "process-spawn"
        or type(execution_error.get("errno")) is not int
        or execution_error.get("errno") <= 0
        or not isinstance(phase_classification, dict)
        or set(phase_classification) != phase_keys
        or any(value is not False for value in phase_classification.values())
        or type(execution.get("raw_log_size")) is not int
        or execution.get("raw_log_size") != 0
        or execution.get("raw_log_sha256") != hashlib.sha256(b"").hexdigest()
    ):
        return False, recovery_mode

    if prior_rejections:
        log_name = (
            f"rollback-flash-pre-spawn-retry-{prior_rejections:04d}.raw.log"
        )
    else:
        log_name = "rollback-flash.raw.log"
    # Keep the exact canonical-parent/lexical-leaf pathname. Resolving this
    # before comparing and lstat-checking the leaf would let a symlink replace
    # the expected name and redefine the journal's accepted raw-log pathname.
    expected_log = transaction_dir / log_name
    raw_log_value = execution.get("raw_log")
    if (
        not isinstance(raw_log_value, str)
        or raw_log_value != str(expected_log)
    ):
        return False, recovery_mode
    raw_log_path = Path(raw_log_value)
    try:
        require_private_regular(raw_log_path)
        raw_log_stat = os.lstat(raw_log_path)
        actual_log = raw_log_path.resolve(strict=True)
    except (FileNotFoundError, ContractError):
        return False, recovery_mode
    if (
        raw_log_stat.st_nlink != 1
        or actual_log != expected_log
        or actual_log.stat().st_size != execution["raw_log_size"]
        or sha256_file(actual_log) != execution["raw_log_sha256"]
    ):
        return False, recovery_mode
    return True, recovery_mode


def rollback_pre_spawn_retry(
    spec: F1Spec,
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> tuple[bool, str | None, int]:
    rollback_states = {
        "RECOVERY_ROLLBACK",
        "ROLLBACK_FLASHED",
        "HEALTH_VERIFIED",
        "CLOSED",
    }
    rollback_marker_keys = {
        "rollback_attempt_limit",
        "rollback_process_started",
        "prior_pre_spawn_rejections",
        "rollback_retry_forbidden",
        "rollback_transfer_count",
        "rollback_retry_preserved",
    }
    common_record_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
    }
    known_nonrollback_process_shapes = {
        "staging-failed": common_record_keys
        | {"candidate_attempted", "rollback_required", "record"},
        "rootfs-staged": common_record_keys
        | {"candidate_attempted", "rootfs_sha256", "record"},
        "candidate-host-rejected": common_record_keys
        | {
            "candidate_transfer_count",
            "candidate_replay",
            "rollback_required",
            "record",
        },
        "candidate-invocation-failed": common_record_keys
        | {
            "candidate_attempted",
            "candidate_replay",
            "rollback_required",
            "record",
        },
        "candidate-flashed": common_record_keys
        | {
            "candidate_sha256",
            "candidate_transfer_count",
            "candidate_replay",
            "rollback_required",
            "record",
        },
    }
    known_nonrollback_process_states = {
        "staging-failed": "ABORTED",
        "rootfs-staged": "APPROVED",
        "candidate-host-rejected": "ABORTED",
        "candidate-invocation-failed": "APPROVED",
        "candidate-flashed": "CANDIDATE_FLASHED",
    }
    related_positions: list[int] = []
    for index, record in enumerate(records):
        action = record.get("action")
        nested_record = record.get("record")
        nested_process_marker = (
            isinstance(nested_record, dict)
            and "process_started" in nested_record
        )
        known_nonrollback_shape = (
            isinstance(action, str)
            and action in known_nonrollback_process_shapes
            and set(record) == known_nonrollback_process_shapes[action]
            and record.get("state")
            == known_nonrollback_process_states[action]
        )
        if (
            action in {"health-verified", "closed"}
            or (
                isinstance(action, str)
                and action.startswith("rollback-")
            )
            or record.get("state") in rollback_states
            or rollback_marker_keys.intersection(record)
            or (
                nested_process_marker
                and not known_nonrollback_shape
            )
        ):
            related_positions.append(index)
    if not related_positions:
        return False, None, 0

    # A retryable history is one complete suffix made only of exact adjacent
    # intent/process-not-started pairs. This rules out any earlier possibly
    # started invocation, completion, health closure, malformed pair, or
    # unrelated record before a later otherwise-valid pair.
    retry_suffix = records[related_positions[0] :]
    if len(retry_suffix) < 2 or len(retry_suffix) % 2:
        return False, None, 0

    recovery_modes: list[str] = []
    for pair_index in range(0, len(retry_suffix), 2):
        intent = retry_suffix[pair_index]
        rejection = retry_suffix[pair_index + 1]
        exact, recovery_mode = rollback_pre_spawn_pair_is_exact(
            spec,
            transaction_dir,
            intent,
            rejection,
            prior_rejections=pair_index // 2,
        )
        if not exact or recovery_mode is None:
            return False, recovery_mode, 0
        recovery_modes.append(recovery_mode)

    if len(set(recovery_modes)) != 1:
        return False, recovery_modes[-1], 0
    return True, recovery_modes[-1], len(recovery_modes)


def close_transaction(
    spec: F1Spec,
    transaction_dir: Path,
    journal_dir: Path,
    events: list[dict[str, str]],
    *,
    observation_proven: bool,
    final_health: dict[str, Any],
    candidate_complete: bool,
) -> dict[str, Any]:
    resident_promotion = isinstance(
        spec.manifest.get("resident_promotion"),
        dict,
    )
    events[:] = repair_timeline_from_journal(
        transaction_dir,
        read_journal(spec, transaction_dir),
        allow_promotion=resident_promotion,
    )
    ensure_event(
        transaction_dir,
        events,
        "live_session_end",
        allow_promotion=resident_promotion,
    )
    names = [event["name"] for event in events]
    if candidate_complete:
        allowed = {CANONICAL_EVENTS}
        if resident_promotion:
            promotion_prefixes = (
                (),
                ("resident_reboot_start",),
                ("resident_reboot_start", "resident_reboot_ready"),
                (
                    "resident_reboot_start",
                    "resident_reboot_ready",
                    "promotion_health_verified",
                ),
            )
            allowed = {
                (
                    "live_session_start",
                    "candidate_flash_start",
                    "candidate_flash_done",
                    "candidate_boot_ready",
                    *prefix,
                    "rollback_flash_start",
                    "rollback_flash_done",
                    "rollback_boot_ready",
                    "live_session_end",
                )
                for prefix in promotion_prefixes
            }
        if tuple(names) not in allowed:
            raise ContractError(
                "completed candidate transaction lacks the canonical timeline"
            )
    if not candidate_complete:
        status = "ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK"
    elif resident_promotion:
        status = "NO_PROOF_A90_F1_RP_CANDIDATE_ROLLED_BACK"
    elif observation_proven and spec.display_required:
        status = "PASS_F1_V2_DISPLAY_ACQUISITION_PROVEN_AND_ROLLED_BACK"
    elif observation_proven:
        status = "PASS_F1_V2_DEBIAN_PID1_PROVEN_AND_ROLLED_BACK"
    else:
        status = "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
    result = {
        "schema": ORCHESTRATOR_SCHEMA,
        "run_id": spec.stage.run_id,
        "status": status,
        "manifest_sha256": spec.stage.manifest_sha256,
        "candidate_transfer_count": 1 if candidate_complete else None,
        "candidate_transfer_uncertain": not candidate_complete,
        "candidate_replay": False,
        "debian_pid1_proven": observation_proven,
        "display_acquisition_proven": (
            observation_proven and spec.display_required
        ),
        "rollback_transfer_count": 1,
        "final_health_restored": bool(final_health),
        "timeline_events": names,
    }
    write_private_json_exclusive(transaction_dir / "result.json", result)
    append_record(
        journal_dir,
        "CLOSED",
        "closed",
        result,
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    return result


def abort_before_candidate(
    spec: F1Spec,
    transaction_dir: Path,
    journal_dir: Path,
    events: list[dict[str, str]],
    exc: Exception,
) -> None:
    if "live_session_end" not in [event.get("name") for event in events]:
        ensure_event(transaction_dir, events, "live_session_end")
    result = {
        "schema": ORCHESTRATOR_SCHEMA,
        "run_id": spec.stage.run_id,
        "status": "ABORTED_F1_V2_BEFORE_CANDIDATE",
        "manifest_sha256": spec.stage.manifest_sha256,
        "candidate_transfer_count": 0,
        "candidate_replay": False,
        "rollback_transfer_count": 0,
        "rollback_required": False,
        "final_health_restored": False,
        "error": {"type": type(exc).__name__, "message": str(exc)},
        "timeline_events": [event["name"] for event in events],
    }
    write_private_json_exclusive(transaction_dir / "result.json", result)
    append_record(
        journal_dir,
        "ABORTED",
        "aborted-before-candidate",
        result,
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )


def require_exact_promotion_tail(
    spec: F1Spec,
    promotion_tail: Any,
) -> None:
    promotion = _dict(
        spec.manifest.get("resident_promotion"),
        "resident_promotion",
    )
    runner = _dict(
        promotion.get("runner"),
        "resident_promotion.runner",
    )
    if set(runner) != {"path", "size", "sha256"}:
        raise ContractError("resident promotion runner binding keys are not exact")
    path_value = runner.get("path")
    size_value = runner.get("size")
    sha_value = runner.get("sha256")
    code = getattr(promotion_tail, "__code__", None)
    module = sys.modules.get(getattr(promotion_tail, "__module__", ""))
    validator = getattr(module, "validate_promotion_manifest", None)
    validator_code = getattr(validator, "__code__", None)
    preserved_mode = (
        spec.manifest.get("schema")
        == staging.PRESERVED_ROOTFS_INSTALL_MANIFEST_SCHEMA
    )
    protected_preflight = getattr(module, "protected_paths_preflight", None)
    protected_preflight_code = getattr(protected_preflight, "__code__", None)
    if (
        not isinstance(path_value, str)
        or type(size_value) is not int
        or not isinstance(sha_value, str)
        or code is None
        or module is None
        or validator_code is None
        or getattr(promotion_tail, "__name__", None) != "promotion_tail"
        or getattr(promotion_tail, "__qualname__", None) != "promotion_tail"
        or getattr(validator, "__name__", None) != "validate_promotion_manifest"
        or getattr(validator, "__qualname__", None)
        != "validate_promotion_manifest"
        or (
            preserved_mode
            and (
                protected_preflight_code is None
                or getattr(protected_preflight, "__name__", None)
                != "protected_paths_preflight"
                or getattr(protected_preflight, "__qualname__", None)
                != "protected_paths_preflight"
            )
        )
    ):
        raise ContractError("resident promotion callback identity is not exact")
    try:
        runner_path = Path(path_value).resolve(strict=True)
        code_path = Path(code.co_filename).resolve(strict=True)
        validator_path = Path(validator_code.co_filename).resolve(strict=True)
        protected_preflight_path = (
            Path(protected_preflight_code.co_filename).resolve(strict=True)
            if preserved_mode
            else runner_path
        )
        module_path = Path(str(getattr(module, "__file__", ""))).resolve(
            strict=True
        )
        info = runner_path.lstat()
    except (FileNotFoundError, OSError) as exc:
        raise ContractError("resident promotion runner is unavailable") from exc
    if (
        runner_path != code_path
        or runner_path != validator_path
        or runner_path != module_path
        or runner_path != protected_preflight_path
        or not stat.S_ISREG(info.st_mode)
        or runner_path.is_symlink()
        or info.st_size != size_value
        or sha256_file(runner_path) != sha_value
    ):
        raise ContractError("resident promotion callback lost its manifest binding")
    validated = validator(spec, recovery=False)
    if (
        not isinstance(validated, dict)
        or validated.get("mode") != promotion.get("mode")
        or validated.get("runner") != runner
    ):
        raise ContractError("resident promotion validator did not close the manifest")


def execute_approved_f1(
    spec: F1Spec,
    args: argparse.Namespace,
    *,
    promotion_tail: Any = None,
) -> dict[str, Any]:
    preserved_rootfs = (
        spec.manifest.get("schema")
        == staging.PRESERVED_ROOTFS_INSTALL_MANIFEST_SCHEMA
    )
    promotion_manifest = isinstance(
        spec.manifest.get("resident_promotion"),
        dict,
    )
    if promotion_manifest != (promotion_tail is not None):
        raise ContractError(
            "resident promotion manifest requires its exact promotion runner"
        )
    if promotion_manifest:
        require_exact_promotion_tail(spec, promotion_tail)
    promotion_module = (
        sys.modules.get(getattr(promotion_tail, "__module__", ""))
        if promotion_tail is not None
        else None
    )
    protected_preflight = (
        getattr(promotion_module, "protected_paths_preflight", None)
        if preserved_rootfs
        else None
    )
    if preserved_rootfs and not callable(protected_preflight):
        raise ContractError("preserved-rootfs preflight callback is unavailable")
    approval_prepared = approved_bindings(spec, args, recovery=False)
    verify_local_closure(spec)
    transaction_dir = exact_transaction_dir(spec, args.transaction_dir)
    transaction_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    journal_dir = transaction_dir / "journal"
    events: list[dict[str, str]] = []
    add_event(transaction_dir, events, "live_session_start")
    append_record(
        journal_dir,
        "PREFLIGHT",
        "preflight",
        {
            "device_write": False,
            "candidate_attempted": False,
            "candidate_sha256": spec.candidate.sha256,
            "rollback_sha256": spec.rollback.sha256,
            "rootfs_sha256": spec.stage.local_sha256,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    append_record(
        journal_dir,
        "APPROVED",
        "approved",
        {
            "approval_consumed": True,
            "candidate_attempted": False,
            "rollback_pre_authorized": True,
            "approval_token_sha256": hashlib.sha256(
                args.approval.encode("utf-8")
            ).hexdigest(),
            "approval_binding_sha256": approval_prepared[
                "approval_binding_sha256"
            ],
            "orchestrator_sha256": spec.orchestrator_sha256,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )

    if preserved_rootfs:
        try:
            staging.require_exact_bridge(spec.stage, args)
            require_f1_starting_health(spec, args)
            verify_local_closure(spec)
            protected_record = protected_preflight(
                spec,
                args,
                phase="pre-candidate",
            )
            append_record(
                journal_dir,
                "APPROVED",
                "protected-paths-pre-verified",
                {
                    "candidate_attempted": False,
                    "staging_attempt_count": 0,
                    "rootfs_copy_count": 0,
                    "cleanup_dispatch_count": 0,
                    "record": protected_record,
                },
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
        except Exception as exc:
            abort_before_candidate(spec, transaction_dir, journal_dir, events, exc)
            raise
    else:
        append_record(
            journal_dir,
            "APPROVED",
            "staging-started",
            {"candidate_attempted": False},
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        stage_live_dir = PRIVATE_RUN_BASE / spec.stage.run_id / "staging-live"
        if stage_live_dir.exists():
            exc = ContractError("preexisting staging-live state is never reusable")
            abort_before_candidate(spec, transaction_dir, journal_dir, events, exc)
            raise exc
        try:
            stage_record = run_logged(
                stage_command(spec, args),
                log_path=transaction_dir / "staging.raw.log",
                timeout=args.staging_command_timeout,
            )
        except Exception as exc:
            abort_before_candidate(spec, transaction_dir, journal_dir, events, exc)
            raise
        if stage_record["returncode"] != 0:
            append_record(
                journal_dir,
                "ABORTED",
                "staging-failed",
                {
                    "candidate_attempted": False,
                    "rollback_required": False,
                    "record": stage_record,
                },
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
            exc = RuntimeError("rootfs staging failed before candidate attempt")
            abort_before_candidate(spec, transaction_dir, journal_dir, events, exc)
            raise exc
        try:
            validate_stage_result(spec)
            append_record(
                journal_dir,
                "APPROVED",
                "rootfs-staged",
                {
                    "candidate_attempted": False,
                    "rootfs_sha256": spec.stage.local_sha256,
                    "record": stage_record,
                },
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
            staging.require_exact_bridge(spec.stage, args)
            require_f1_starting_health(spec, args)
            verify_local_closure(spec)
            source_preflight = remote_source_preflight(spec, args)
            candidate_first_boot_preflight = (
                require_candidate_first_boot_state_absent(spec, args)
            )
            candidate_preflight_payload: dict[str, Any] = {
                "candidate_attempted": False,
                "final_regular": True,
                "work_absent": True,
                "rootfs_size": spec.stage.local_size,
                "rootfs_sha256": spec.stage.local_sha256,
                "record": source_preflight,
            }
            if candidate_first_boot_preflight is not None:
                candidate_preflight_payload["candidate_first_boot_preflight"] = (
                    candidate_first_boot_preflight
                )
            append_record(
                journal_dir,
                "APPROVED",
                "rootfs-candidate-preflight",
                candidate_preflight_payload,
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
        except Exception as exc:
            abort_before_candidate(spec, transaction_dir, journal_dir, events, exc)
            raise

    promotion_guard: cdc_guard.ModemManagerGuard | None = None
    promotion_guard_transferred = False

    def release_owned_promotion_guard() -> None:
        nonlocal promotion_guard
        if promotion_guard is None:
            return
        release = release_candidate_return_modemmanager_guard(
            promotion_guard,
            transaction_dir,
            corridor="resident-promotion",
        )
        promotion_guard = None
        if release.get("released") is not True:
            raise ContractError("resident promotion guard did not release")

    if promotion_manifest:
        try:
            promotion_guard = arm_candidate_return_modemmanager_guard(
                spec,
                args,
                transaction_dir,
                corridor="resident-promotion",
            )
            guard_evidence = modemmanager_guard_arm_evidence(
                transaction_dir,
                "resident-promotion",
                promotion_guard,
            )
            append_record(
                journal_dir,
                "APPROVED",
                "resident-promotion-guard-armed",
                {
                    "candidate_attempted": False,
                    "candidate_replay": False,
                    "guard": guard_evidence,
                },
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
        except Exception as exc:
            release_owned_promotion_guard()
            abort_before_candidate(
                spec,
                transaction_dir,
                journal_dir,
                events,
                exc,
            )
            raise
    try:
        add_event(transaction_dir, events, "candidate_flash_start")
        append_record(
            journal_dir,
            "APPROVED",
            "candidate-transfer-started",
            {
                "candidate_attempted": True,
                "candidate_sha256": spec.candidate.sha256,
                "candidate_transfer_count_max": 1,
                "rollback_required": True,
                "candidate_replay": False,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        candidate_record = run_logged(
            flash_command(spec, args, rollback=False, from_native=True),
            log_path=transaction_dir / "candidate-flash.raw.log",
            timeout=args.flash_command_timeout,
        )
        candidate_record["phase_classification"] = classify_flash_log(
            Path(str(candidate_record["raw_log"]))
        )
        if candidate_record["returncode"] != 0:
            if candidate_failure_is_definite_pre_session(candidate_record):
                append_record(
                    journal_dir,
                    "ABORTED",
                    "candidate-host-rejected",
                    {
                        "candidate_transfer_count": 0,
                        "candidate_replay": False,
                        "rollback_required": False,
                        "record": candidate_record,
                    },
                    manifest_sha256=spec.stage.manifest_sha256,
                    run_id=spec.stage.run_id,
                )
                exc = RuntimeError(
                    "candidate was definitively rejected before a device session; "
                    "fresh approval required"
                )
                release_owned_promotion_guard()
                abort_before_candidate(spec, transaction_dir, journal_dir, events, exc)
                raise exc
            append_record(
                journal_dir,
                "APPROVED",
                "candidate-invocation-failed",
                {
                    "candidate_attempted": True,
                    "candidate_replay": False,
                    "rollback_required": True,
                    "record": candidate_record,
                },
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
            try:
                require_rollback_source_native(
                    spec,
                    args,
                    return_guard=promotion_guard,
                )
            except Exception as exc:  # noqa: BLE001 - physical recovery may be required
                raise RuntimeError(
                    "candidate invocation failed after durable intent; recover rollback only"
                ) from exc
            health = invoke_rollback(
                spec,
                args,
                transaction_dir,
                journal_dir,
                events,
                from_native=True,
                return_guard=promotion_guard,
            )
            if preserved_rootfs:
                protected_after_rollback = protected_preflight(
                    spec,
                    args,
                    phase="post-rollback",
                )
                append_record(
                    journal_dir,
                    "HEALTH_VERIFIED",
                    "protected-paths-post-rollback-verified",
                    {
                        "staging_attempt_count": 0,
                        "rootfs_copy_count": 0,
                        "cleanup_dispatch_count": 0,
                        "record": protected_after_rollback,
                    },
                    manifest_sha256=spec.stage.manifest_sha256,
                    run_id=spec.stage.run_id,
                )
            release_owned_promotion_guard()
            return close_transaction(
                spec,
                transaction_dir,
                journal_dir,
                events,
                observation_proven=False,
                final_health=health,
                candidate_complete=False,
            )
        append_record(
            journal_dir,
            "CANDIDATE_FLASHED",
            "candidate-flashed",
            {
                "candidate_sha256": spec.candidate.sha256,
                "candidate_transfer_count": 1,
                "candidate_replay": False,
                "rollback_required": True,
                "record": candidate_record,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        ensure_event(transaction_dir, events, "candidate_flash_done")
        if promotion_guard is not None and not promotion_guard.healthy(recheck=True):
            raise ContractError("resident promotion guard was lost after candidate flash")
        if spec.observation_mode == ATTENDED_OBSERVATION_MODE:
            attended_result = open_attended_window(
                spec,
                approval_prepared,
                transaction_dir,
                journal_dir,
            )
            validate_attended_candidate_closure(
                spec,
                approval_prepared,
                transaction_dir,
                read_journal(spec, transaction_dir),
            )
            return attended_result
        if promotion_guard is not None:
            staging.require_exact_bridge(spec.stage, args)
            if not promotion_guard.healthy(recheck=True):
                raise ContractError(
                    "resident promotion guard was lost before channel settle"
                )
            require_returned_modemmanager_guard(
                spec,
                {"returned": {"selected_realpath": spec.stage.bridge_realpath}},
                promotion_guard,
            )
        candidate_health_channel = settle_observation_channel(
            args,
            phase="before-candidate-health",
        )
        candidate_health = verify_candidate_health(
            spec,
            args,
            return_guard=promotion_guard,
        )
        candidate_first_boot_health = require_candidate_first_boot_unarmed(
            spec,
            args,
        )
        candidate_boot_payload: dict[str, Any] = {
            "candidate_version": spec.candidate_version,
            "candidate_build": spec.candidate_build,
            "selftest_fail_zero": True,
            "channel": candidate_health_channel,
            "health": candidate_health,
        }
        if candidate_first_boot_health is not None:
            candidate_boot_payload["candidate_first_boot_health"] = (
                candidate_first_boot_health
            )
        append_record(
            journal_dir,
            "CANDIDATE_FLASHED",
            "candidate-boot-ready",
            candidate_boot_payload,
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        ensure_event(transaction_dir, events, "candidate_boot_ready")

        if promotion_tail is not None:
            assert promotion_guard is not None
            promotion_guard_transferred = True
            return promotion_tail(
                spec,
                args,
                transaction_dir,
                journal_dir,
                events,
                candidate_health,
                promotion_guard,
            )
    finally:
        if promotion_guard is not None and not promotion_guard_transferred:
            release_owned_promotion_guard()

    observation = observe_candidate(spec, args, transaction_dir)
    append_record(
        journal_dir,
        "OBSERVED",
        "observation-proven" if observation.get("proof") else "observation-no-proof",
        {
            "debian_pid1_proven": observation.get("proof") is True,
            "retained_pmsg_armed_proven": observation.get("proof") is True,
            "retained_pmsg_cleaned": observation.get("proof") is True,
            "candidate_replay": False,
            "rollback_required": True,
            "candidate_returned": "candidate_return" in observation,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    if "candidate_return" not in observation:
        raise RuntimeError("candidate did not return; recover rollback only")

    health = invoke_rollback(
        spec,
        args,
        transaction_dir,
        journal_dir,
        events,
        from_native=True,
    )
    return close_transaction(
        spec,
        transaction_dir,
        journal_dir,
        events,
        observation_proven=observation.get("proof") is True,
        final_health=health,
        candidate_complete=True,
    )


def validate_attended_continuation(
    spec: F1Spec,
    args: argparse.Namespace,
    approval_prepared: dict[str, Any],
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    if spec.observation_mode != ATTENDED_OBSERVATION_MODE:
        raise ContractError("manifest does not select attended observation")
    require_consumed_approval(records, approval_prepared)
    actions = action_names(records)
    if (
        actions.count("candidate-transfer-started") != 1
        or actions.count("candidate-flashed") != 1
        or actions.count("attended-window-open") != 1
    ):
        raise ContractError("attended continuation lacks exact candidate/window state")
    for forbidden in (
        "candidate-host-rejected",
        "attended-pre-handoff-ready",
        "attended-handoff-started",
        "observation-proven",
        "observation-no-proof",
        "rollback-transfer-started",
        "rollback-flashed",
        "rollback-completion-recovered-by-health",
        "closed",
    ):
        if forbidden in actions:
            raise ContractError(
                f"attended continuation is closed by durable action: {forbidden}"
            )
    validate_attended_candidate_closure(
        spec,
        approval_prepared,
        transaction_dir,
        records,
    )
    window_index = actions.index("attended-window-open")
    suffix = records[window_index + 1:]
    if len(suffix) % 2 != 0:
        raise ContractError("attended pre-handoff journal has an incomplete pair")
    receipt = load_attended_window(
        spec,
        approval_prepared,
        transaction_dir,
        records,
    )
    if args.attended_approval != receipt["continue_token"]:
        raise ContractError("fresh exact attended continuation token mismatch")
    window_opened = parse_utc_timestamp(
        records[window_index]["timestamp_utc"],
        "attended window opened",
    )
    deadline = parse_utc_timestamp(
        receipt["continue_binding"]["window_deadline_utc"],
        "attended window deadline",
    )
    journal_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
    }
    attempt_keys = journal_keys | {
        "attempt",
        "attempt_limit",
        "handoff_intent",
        "handoff_sent",
        "candidate_replay",
        "rollback_required",
    }
    failure_keys = journal_keys | {
        "attempt",
        "attempt_limit",
        "retryable_channel_failure",
        "continuation_allowed",
        "within_deadline",
        "handoff_intent",
        "handoff_sent",
        "candidate_replay",
        "rollback_required",
        "error",
    }
    for index in range(0, len(suffix), 2):
        attempt = suffix[index]
        failure = suffix[index + 1]
        expected_attempt = index // 2 + 1
        attempt_timestamp = parse_utc_timestamp(
            attempt.get("timestamp_utc"),
            "attended pre-handoff attempt",
        )
        failure_timestamp = parse_utc_timestamp(
            failure.get("timestamp_utc"),
            "attended pre-handoff failure",
        )
        if (
            set(attempt) != attempt_keys
            or attempt.get("state") != "CANDIDATE_FLASHED"
            or attempt.get("action") != "attended-pre-handoff-attempt"
            or type(attempt.get("attempt")) is not int
            or attempt.get("attempt") != expected_attempt
            or type(attempt.get("attempt_limit")) is not int
            or attempt.get("attempt_limit") != spec.pre_handoff_attempt_limit
            or attempt.get("handoff_intent") is not False
            or attempt.get("handoff_sent") is not False
            or attempt.get("candidate_replay") is not False
            or attempt.get("rollback_required") is not True
            or set(failure) != failure_keys
            or failure.get("state") != "CANDIDATE_FLASHED"
            or failure.get("action") != "attended-pre-handoff-failed"
            or type(failure.get("attempt")) is not int
            or failure.get("attempt") != expected_attempt
            or type(failure.get("attempt_limit")) is not int
            or failure.get("attempt_limit") != spec.pre_handoff_attempt_limit
            or failure.get("retryable_channel_failure") is not True
            or failure.get("continuation_allowed") is not True
            or failure.get("within_deadline") is not True
            or failure.get("handoff_intent") is not False
            or failure.get("handoff_sent") is not False
            or failure.get("candidate_replay") is not False
            or failure.get("rollback_required") is not True
            or not attended_stored_failure_retryable(
                failure.get("error"),
                attempt=expected_attempt,
            )
            or not (
                window_opened
                <= attempt_timestamp
                <= failure_timestamp
                <= deadline
            )
        ):
            raise ContractError(
                "attended pre-handoff retry lacks exact no-intent/no-send proof"
            )
    attempts = len(suffix) // 2
    if attempts >= spec.pre_handoff_attempt_limit:
        raise ContractError("attended pre-handoff attempt budget is exhausted")
    if current_utc() > deadline:
        raise ContractError("attended observation window expired; rollback only")
    return receipt, attempts + 1


def continue_attended_f1(
    spec: F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    approval_prepared = approved_bindings(spec, args, recovery=True)
    verify_local_closure(spec)
    transaction_dir = exact_transaction_dir(spec, args.transaction_dir)
    records = read_journal(spec, transaction_dir)
    receipt, attempt = validate_attended_continuation(
        spec,
        args,
        approval_prepared,
        transaction_dir,
        records,
    )
    events = repair_timeline_from_journal(transaction_dir, records)
    journal_dir = transaction_dir / "journal"
    append_record(
        journal_dir,
        "CANDIDATE_FLASHED",
        "attended-pre-handoff-attempt",
        {
            "attempt": attempt,
            "attempt_limit": spec.pre_handoff_attempt_limit,
            "handoff_intent": False,
            "handoff_sent": False,
            "candidate_replay": False,
            "rollback_required": True,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    try:
        channel_before_health = settle_observation_channel(
            args,
            phase=f"attended-attempt-{attempt}-before-health",
        )
        candidate_health = verify_candidate_health(spec, args)
        host_ncm_rebind = rebind_host_ncm_after_reenumeration(spec, args)
        pstore_before_handoff = require_clean_pstore_before_handoff(args)
        source_preflight = remote_source_preflight(spec, args)
        channel_before_handoff = settle_observation_channel(
            args,
            phase=f"attended-attempt-{attempt}-before-handoff",
        )
        return_epoch_before_handoff = capture_bridge_serial_epoch(
            spec,
            args,
        )
        handoff_deadline = parse_utc_timestamp(
            receipt["continue_binding"]["window_deadline_utc"],
            "attended window deadline",
        )
        if current_utc() > handoff_deadline:
            raise ContractError(
                "attended observation window expired before handoff"
            )
    except Exception as exc:
        retryable = attended_pre_handoff_retryable(
            exc,
            attempt=attempt,
        )
        deadline = parse_utc_timestamp(
            receipt["continue_binding"]["window_deadline_utc"],
            "attended window deadline",
        )
        failure_observed = current_utc()
        within_deadline = failure_observed <= deadline
        continuation_allowed = (
            retryable
            and attempt < spec.pre_handoff_attempt_limit
            and within_deadline
        )
        append_record(
            journal_dir,
            "CANDIDATE_FLASHED",
            "attended-pre-handoff-failed",
            {
                "attempt": attempt,
                "attempt_limit": spec.pre_handoff_attempt_limit,
                "retryable_channel_failure": retryable,
                "continuation_allowed": continuation_allowed,
                "within_deadline": within_deadline,
                "handoff_intent": False,
                "handoff_sent": False,
                "candidate_replay": False,
                "rollback_required": True,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
            timestamp_utc=failure_observed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        if not continuation_allowed:
            raise RuntimeError(
                "attended pre-handoff continuation ended; rollback only"
            ) from exc
        return {
            "schema": ORCHESTRATOR_SCHEMA,
            "status": "PAUSED_F1_V2_ATTENDED_RETRY_AVAILABLE",
            "run_id": spec.stage.run_id,
            "manifest_sha256": spec.stage.manifest_sha256,
            "continue_token": receipt["continue_token"],
            "attempt": attempt,
            "attempts_remaining": (
                spec.pre_handoff_attempt_limit - attempt
            ),
            "handoff_attempted": False,
            "candidate_replay": False,
            "rollback_required": True,
        }
    append_record(
        journal_dir,
        "CANDIDATE_FLASHED",
        "candidate-boot-ready",
        {
            "candidate_version": spec.candidate_version,
            "candidate_build": spec.candidate_build,
            "selftest_fail_zero": True,
            "attended_attempt": attempt,
            "channel": channel_before_health,
            "health": candidate_health,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    ensure_event(transaction_dir, events, "candidate_boot_ready")
    pre_handoff = {
        "attempt": attempt,
        "host_ncm_rebind": host_ncm_rebind,
        "pstore_before_handoff": pstore_before_handoff,
        "source_preflight": source_preflight,
        "channel_before_handoff": channel_before_handoff,
        "return_epoch_before_handoff": return_epoch_before_handoff,
    }
    return_guard: cdc_guard.ModemManagerGuard | None = None
    if spec.display_required:
        return_guard = arm_candidate_return_modemmanager_guard(
            spec,
            args,
            transaction_dir,
        )
        pre_handoff["candidate_return_modemmanager_guard_arm"] = (
            {
                "max_sec": return_guard.max_sec,
                "receipt": return_guard.arm_receipt,
            }
        )
    try:
        append_record(
            journal_dir,
            "CANDIDATE_FLASHED",
            "attended-pre-handoff-ready",
            {
                "attempt": attempt,
                "handoff_intent": False,
                "handoff_sent": False,
                "source_exact": True,
                "candidate_health_exact": True,
                "host_ncm_rebound": True,
                "pstore_clean_before_handoff": True,
                "return_epoch_captured": True,
                "candidate_return_modemmanager_guard_armed": (
                    return_guard is not None
                ),
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        intent_timestamp = current_utc()
        if intent_timestamp > handoff_deadline:
            raise RuntimeError(
                "attended window expired before durable handoff intent; "
                "rollback only"
            )
        if return_guard is not None and not return_guard.healthy(recheck=True):
            raise ContractError(
                "candidate-return ModemManager guard was lost before intent"
            )
        append_record(
            journal_dir,
            "CANDIDATE_FLASHED",
            "attended-handoff-started",
            {
                "handoff_attempt": 1,
                "handoff_attempt_limit": spec.handoff_attempt_limit,
                "handoff_argv_sha256": json_sha256(list(spec.handoff_command)),
                "journal_fsync_completed_before_dispatch": True,
                "candidate_replay": False,
                "rollback_required": True,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
            timestamp_utc=intent_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        if return_guard is not None and not return_guard.healthy(recheck=True):
            raise ContractError(
                "candidate-return ModemManager guard was lost before dispatch"
            )
    except Exception:
        if return_guard is not None:
            try:
                release_candidate_return_modemmanager_guard(
                    return_guard,
                    transaction_dir,
                )
            except Exception:  # noqa: BLE001 - preserve original failure
                pass
        raise
    observe_kwargs = (
        {} if return_guard is None else {"return_guard": return_guard}
    )
    observation = observe_attended_after_handoff(
        spec,
        args,
        transaction_dir,
        pre_handoff,
        **observe_kwargs,
    )
    mechanical_display_proof = (
        spec.display_required
        and observation.get("display_mechanical_proof") is True
    )
    bounded_display_failure = (
        spec.display_required
        and observation.get("bounded_display_failure") is True
    )
    append_record(
        journal_dir,
        "OBSERVED",
        "observation-proven" if observation.get("proof") else "observation-no-proof",
        {
            "debian_pid1_proven": (
                observation.get("proof") is True
                or observation.get("debian_pid1_proven") is True
            ),
            "native_release_proven": (
                observation.get("native_release_proven") is True
            ),
            "display_mechanical_proven": mechanical_display_proof,
            "bounded_display_failure": bounded_display_failure,
            "visible_confirmation_required": (
                mechanical_display_proof
                and observation.get("visible_confirmation_required") is True
            ),
            "retained_pmsg_armed_proven": (
                observation.get("retained_pmsg", {}).get("proof") is True
            ),
            "retained_pmsg_cleaned": (
                observation.get("retained_pmsg", {}).get("proof") is True
            ),
            "candidate_replay": False,
            "rollback_required": True,
            "candidate_returned": "candidate_return" in observation,
            "handoff_attempt_count": 1,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    if "candidate_return" not in observation:
        raise RuntimeError("attended candidate did not return; recover rollback only")
    if spec.display_required and mechanical_display_proof:
        return open_display_visible_confirmation(
            spec,
            approval_prepared,
            receipt,
            transaction_dir,
            journal_dir,
            observation,
        )
    health = invoke_rollback(
        spec,
        args,
        transaction_dir,
        journal_dir,
        events,
        from_native=True,
    )
    return close_transaction(
        spec,
        transaction_dir,
        journal_dir,
        events,
        observation_proven=observation.get("proof") is True,
        final_health=health,
        candidate_complete=True,
    )


def confirm_visible_display(
    spec: F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    approval_prepared = approved_bindings(spec, args, recovery=True)
    verify_local_closure(spec)
    transaction_dir = exact_transaction_dir(spec, args.transaction_dir)
    records = read_journal(spec, transaction_dir)
    actions = action_names(records)
    if "closed" in actions:
        raise ContractError("transaction is already closed")
    require_consumed_approval(records, approval_prepared)
    if (
        actions.count("display-visible-confirmation-open") != 1
        or "display-visible-confirmed" in actions
        or "rollback-transfer-started" in actions
    ):
        raise ContractError(
            "display confirmation requires one open, unconfirmed window before rollback"
        )
    receipt = load_display_visible_confirmation(
        spec,
        approval_prepared,
        transaction_dir,
        records,
    )
    if args.visible_approval != receipt["visible_token"]:
        raise ContractError("exact display visible confirmation token mismatch")
    deadline = parse_utc_timestamp(
        receipt["visible_binding"]["observation_deadline_utc"],
        "display visible observation deadline",
    )
    confirmed = current_utc()
    if confirmed > deadline:
        raise ContractError(
            "display visible observation window expired; rollback only"
        )
    observation_path = transaction_dir / "observation.json"
    require_private_regular(observation_path)
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    if (
        not isinstance(observation, dict)
        or observation.get("display_mechanical_proof") is not True
        or observation.get("visible_confirmation_required") is not True
        or "candidate_return" not in observation
        or observation.get("retained_pmsg", {}).get("proof") is not True
        or observation.get("ssh", {}).get("display_marker_text") is None
    ):
        raise ContractError(
            "display confirmation lost its mechanical observation closure"
        )
    marker_text = observation["ssh"]["display_marker_text"]
    display.validate_debian_ready_marker(
        marker_text,
        display_uid=spec.display_uid,
        display_gid=spec.display_gid,
    )
    marker_sha256 = hashlib.sha256(marker_text.encode("utf-8")).hexdigest()
    if (
        marker_sha256
        != receipt["visible_binding"]["display_ready_marker_sha256"]
    ):
        raise ContractError("display ready marker changed after confirmation opened")
    journal_dir = transaction_dir / "journal"
    confirmation_path = append_record(
        journal_dir,
        "OBSERVED",
        "display-visible-confirmed",
        {
            "visible_binding_sha256": receipt["visible_binding_sha256"],
            "operator_attested_exact_visible_text": True,
            "display_ready_marker_sha256": marker_sha256,
            "visible_text_sha256": json_sha256(
                list(spec.display_visible_text)
            ),
            "within_observation_deadline": True,
            "candidate_returned": True,
            "candidate_replay": False,
            "rollback_required": True,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
        timestamp_utc=confirmed.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    confirmation_record = json.loads(
        confirmation_path.read_text(encoding="utf-8")
    )
    write_private_json_exclusive(
        transaction_dir / "display-visible-confirmation-result.json",
        {
            "schema": "a90_v3406_f1_display_visible_result_v1",
            "run_id": spec.stage.run_id,
            "manifest_sha256": spec.stage.manifest_sha256,
            "visible_binding_sha256": receipt["visible_binding_sha256"],
            "confirmation_sequence": confirmation_record["sequence"],
            "confirmation_timestamp_utc": confirmation_record[
                "timestamp_utc"
            ],
            "operator_attested_exact_visible_text": True,
            "candidate_replay": False,
            "rollback_required": True,
        },
    )
    validate_confirmed_display_proof(
        spec,
        approval_prepared,
        transaction_dir,
        read_journal(spec, transaction_dir),
    )
    events = repair_timeline_from_journal(
        transaction_dir,
        read_journal(spec, transaction_dir),
    )
    health = invoke_rollback(
        spec,
        args,
        transaction_dir,
        journal_dir,
        events,
        from_native=True,
    )
    return close_transaction(
        spec,
        transaction_dir,
        journal_dir,
        events,
        observation_proven=True,
        final_health=health,
        candidate_complete=True,
    )


def action_names(records: list[dict[str, Any]]) -> list[str]:
    return [str(record.get("action")) for record in records]


def recover_approved_rollback(
    spec: F1Spec,
    args: argparse.Namespace,
    *,
    return_guard: cdc_guard.ModemManagerGuard | None = None,
    before_close: Callable[[], None] | None = None,
) -> dict[str, Any]:
    resident_promotion = isinstance(
        spec.manifest.get("resident_promotion"),
        dict,
    )
    approval_prepared = approved_bindings(spec, args, recovery=True)
    verify_local_closure(spec)
    transaction_dir = exact_transaction_dir(spec, args.transaction_dir)
    records = read_journal(spec, transaction_dir)
    actions = action_names(records)
    if "candidate-transfer-started" not in actions:
        raise ContractError("rollback recovery requires durable candidate intent")
    if (
        "candidate-host-rejected" in actions
        or "aborted-before-candidate" in actions
    ):
        raise ContractError("pre-session abort has no rollback authority to exercise")
    if "closed" in actions:
        raise ContractError("transaction is already closed")
    require_consumed_approval(records, approval_prepared)
    display_observation_proven = False
    if spec.display_required and "display-visible-confirmed" in actions:
        try:
            validate_confirmed_display_proof(
                spec,
                approval_prepared,
                transaction_dir,
                records,
            )
        # Recovery must never let an evidence-parser exception preempt the
        # already-authorized exact rollback.  In particular, the display
        # observer owns a distinct ContractError type.
        except Exception:  # noqa: BLE001 - evidence failure is NO_PROOF
            display_observation_proven = False
        else:
            display_observation_proven = True
    events = repair_timeline_from_journal(
        transaction_dir,
        records,
        allow_promotion=isinstance(
            spec.manifest.get("resident_promotion"),
            dict,
        ),
    )
    journal_dir = transaction_dir / "journal"

    rollback_started = "rollback-transfer-started" in actions
    rollback_flashed = any(
        action in actions
        for action in (
            "rollback-flashed",
            "rollback-completion-recovered-by-health",
        )
    )
    retry_allowed, retry_mode, rejection_count = rollback_pre_spawn_retry(
        spec,
        transaction_dir,
        records,
    )
    if retry_allowed and not rollback_flashed:
        if args.recovery_path is not None and args.recovery_path != retry_mode:
            raise ContractError(
                "recovery path conflicts with durable pre-spawn rollback mode"
            )
        from_native = retry_mode == "from-native"
        if from_native:
            if resident_promotion and return_guard is None:
                raise ContractError(
                    "resident from-native rollback requires its exact guard"
                )
            require_rollback_source_native(
                spec,
                args,
                return_guard=return_guard,
            )
        health = invoke_rollback(
            spec,
            args,
            transaction_dir,
            journal_dir,
            events,
            from_native=from_native,
            pre_spawn_retry_index=rejection_count,
            allow_promotion=resident_promotion,
            return_guard=return_guard,
        )
    elif rollback_started and not rollback_flashed:
        if resident_promotion and return_guard is None:
            raise ContractError(
                "rollback completion needs guarded final-health recovery"
            )
        health = verify_final_health(
            spec,
            args,
            return_guard=return_guard,
        )
        append_record(
            journal_dir,
            "ROLLBACK_FLASHED",
            "rollback-completion-recovered-by-health",
            {
                "rollback_reinvoked": False,
                "exact_v2321_health": True,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        append_record(
            journal_dir,
            "ROLLBACK_FLASHED",
            "rollback-boot-ready",
            {
                "rollback_version": spec.rollback_version,
                "rollback_build": spec.rollback_build,
                "selftest_fail_zero": True,
                "recovered_from_health": True,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        append_record(
            journal_dir,
            "HEALTH_VERIFIED",
            "health-verified",
            health,
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
    elif rollback_flashed:
        if resident_promotion and return_guard is None:
            raise ContractError(
                "rollback is flashed; guarded final-health recovery is pending"
            )
        health = verify_final_health(
            spec,
            args,
            return_guard=return_guard,
        )
        if "rollback-boot-ready" not in actions:
            append_record(
                journal_dir,
                "ROLLBACK_FLASHED",
                "rollback-boot-ready",
                {
                    "rollback_version": spec.rollback_version,
                    "rollback_build": spec.rollback_build,
                    "selftest_fail_zero": True,
                    "recovered_from_health": True,
                },
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
        if "health-verified" not in actions:
            append_record(
                journal_dir,
                "HEALTH_VERIFIED",
                "health-verified",
                health,
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
    else:
        if args.recovery_path not in ("from-native", "adb-recovery"):
            raise ContractError(
                "rollback recovery requires --recovery-path from-native|adb-recovery"
            )
        from_native = args.recovery_path == "from-native"
        if from_native:
            if resident_promotion and return_guard is None:
                raise ContractError(
                    "resident from-native rollback requires its exact guard"
                )
            require_rollback_source_native(
                spec,
                args,
                return_guard=return_guard,
            )
        health = invoke_rollback(
            spec,
            args,
            transaction_dir,
            journal_dir,
            events,
            from_native=from_native,
            allow_promotion=resident_promotion,
            return_guard=return_guard,
        )

    observation_proven = (
        display_observation_proven
        if spec.display_required
        else "observation-proven" in actions
    )
    candidate_complete = (
        "candidate-flashed" in actions and "candidate-boot-ready" in actions
    )
    if before_close is not None:
        before_close()
    return close_transaction(
        spec,
        transaction_dir,
        journal_dir,
        events,
        observation_proven=observation_proven,
        final_health=health,
        candidate_complete=candidate_complete,
    )


def simulate_transaction(
    *,
    fail_at: str | None = None,
    recover: bool = False,
) -> F1Model:
    model = F1Model()
    steps = (
        "validate",
        "approve",
        "stage",
        "candidate-intent",
        "candidate-complete",
        "candidate-boot-ready",
        "observe",
        "rollback-intent",
        "rollback-complete",
        "final-health",
        "close",
    )
    for step in steps:
        model.history.append(step)
        if step == "candidate-intent":
            model.candidate_attempts += 1
            model.rollback_required = True
        elif step == "observe":
            model.observation_proven = fail_at != step
        elif step == "rollback-intent":
            model.rollback_attempts += 1
        elif step == "rollback-complete":
            model.rollback_required = False
        elif step == "final-health":
            model.final_health = True
        elif step == "close":
            model.closed = True
        if fail_at == step:
            model.blocked = step
            break
    if recover and model.rollback_required:
        model.history.append("recover-rollback-only")
        if model.rollback_attempts == 0:
            model.rollback_attempts = 1
            model.rollback_required = False
            model.final_health = True
            model.closed = True
        else:
            model.history.append("rollback-retry-refused")
    return model


def source_contract_issues(source: str) -> tuple[str, ...]:
    issues: list[str] = []
    required_functions = (
        "def approval_binding(",
        "def prepare_approval(",
        "def load_approval_prepared(",
        "def candidate_failure_is_definite_pre_session(",
        "def rollback_pre_spawn_retry(",
        "def validate_handoff_timeout(",
        "def require_returned_modemmanager_guard(",
        "def capture_bridge_serial_epoch(",
        "def wait_for_new_bridge_serial_epoch(",
        "def settle_observation_channel(",
        "def rebind_host_ncm_after_reenumeration(",
        "def require_clean_pstore_before_handoff(",
        "def validate_pstore_before_handoff_receipt(",
        "def collect_and_clear_retained_pmsg(",
        "def validate_display_observation(",
        "def open_display_visible_confirmation(",
        "def load_display_visible_confirmation(",
        "def validate_confirmed_display_proof(",
        "def confirm_visible_display(",
        "def validate_attended_candidate_closure(",
        "def open_attended_window(",
        "def load_attended_window(",
        "def validate_attended_continuation(",
        "def continue_attended_f1(",
        "def execute_approved_f1(",
        "def recover_approved_rollback(",
        "def invoke_rollback(",
        "def validate_stage_result(",
        "def approved_bindings(",
    )
    for token in required_functions:
        if token not in source:
            issues.append(f"missing function: {token}")
    for token in (
        "CDC_GUARD_SIZE = 51402",
        'CDC_GUARD_SHA256 = "6c8a6d2151928d2e098ca41b3c9dc24cdbbfabe9be10df19969be274744ef9a9"',
    ):
        if token not in source:
            issues.append(f"ModemManager guard transitive binding missing: {token}")
    local_closure_start = source.find("def verify_local_closure(")
    local_closure_end = source.find(
        "def exact_transaction_dir(",
        local_closure_start + 1,
    )
    if local_closure_start < 0 or local_closure_end < 0:
        issues.append("local closure source boundary is missing")
    else:
        local_closure = source[local_closure_start:local_closure_end]
        for token in (
            "Path(cdc_guard.__file__).resolve() != CDC_GUARD_PATH",
            "expected_size=CDC_GUARD_SIZE",
            "expected_sha256=CDC_GUARD_SHA256",
        ):
            if token not in local_closure:
                issues.append(
                    f"ModemManager guard local closure missing: {token}"
                )
    approval_start = source.find("def approval_binding(")
    approval_end = source.find("\ndef approval_prepared_path(", approval_start + 1)
    if approval_start < 0 or approval_end < 0:
        issues.append("approval binding source boundary is missing")
    else:
        approval = source[approval_start:approval_end]
        for token in (
            "return staging.canonical_f1_approval_binding(",
            "observation_mode=spec.observation_mode",
            "attended_window_sec=spec.attended_window_sec",
            "pre_handoff_attempt_limit=spec.pre_handoff_attempt_limit",
            "handoff_attempt_limit=spec.handoff_attempt_limit",
        ):
            if approval.count(token) != 1:
                issues.append(
                    f"approval binding lacks canonical observation gate: {token}"
                )
    constants_start = source.find('F1_SERIAL_INPUT_MODE = "slow"')
    constants_end = source.find("RECOVERY_ADB_MARKER_RE", constants_start + 1)
    if constants_start < 0 or constants_end < 0:
        observation_constants = ""
        issues.append("observation constant boundary is missing")
    else:
        observation_constants = source[constants_start:constants_end]
    for token in (
        'F1_SERIAL_INPUT_MODE = "slow"',
        "F1_SERIAL_INPUT_CHAR_DELAY_SEC = 0.02",
        "F1_HANDOFF_MAX_PRE_READ_SEC = 5.0",
        "F1_HANDOFF_SOURCE_SHA_PHASES = (",
        '    "initial",',
        '    "post-display-cleanup",',
        "F1_HANDOFF_COPY_BOUND_SEC = 0",
        "F1_HANDOFF_SHA_PASS_COUNT = len(F1_HANDOFF_SOURCE_SHA_PHASES)",
        "F1_HANDOFF_SHA_ALLOWANCE_PER_PASS_SEC = 90",
        "F1_HANDOFF_SWITCH_HELPER_BOUND_COUNT = 2",
        "F1_HANDOFF_SWITCH_HELPER_BOUND_SEC = 30",
        "F1_HANDOFF_DISPLAY_HUD_STOP_BOUND_SEC = 3",
        "F1_HANDOFF_DISPLAY_DPRESENT_OWNER_BOUND_COUNT = 1",
        "F1_HANDOFF_DISPLAY_OWNER_BOUND_COUNT = 16",
        "F1_HANDOFF_DISPLAY_OWNER_WAIT_COUNT = 2",
        "F1_HANDOFF_DISPLAY_OWNER_WAIT_SEC = 1",
        "F1_HANDOFF_DISPLAY_PROC_SCAN_COUNT = 3",
        "F1_HANDOFF_DISPLAY_PROC_ENTRY_BOUND_COUNT = 8192",
        "F1_HANDOFF_DISPLAY_TOTAL_BOUND_SEC = 127",
        "F1_HANDOFF_DISPLAY_BOUND_SEC = F1_HANDOFF_DISPLAY_TOTAL_BOUND_SEC",
        "F1_HANDOFF_MISC_ALLOWANCE_SEC = 90",
        "F1_HANDOFF_MIN_READ_BUDGET_SEC = (",
        "F1_HANDOFF_MIN_TIMEOUT_SEC = (",
        "OBSERVATION_MENU_SETTLE_SEC = 3.0",
        'OBSERVATION_CHANNEL_CANARY = ("run", "/bin/busybox", "true")',
        'RETURN_EPOCH_SCHEMA = "a90_host_usb_serial_epoch_v1"',
        "HOST_NCM_REBIND_TIMEOUT_SEC = 30",
        "HOST_NCM_REBIND_WORST_CASE_SEC = 155.0",
        'PSTORE_MOUNT_PATH = "/sys/fs/pstore"',
        'RETAINED_PMSG_MARKER = "A90D3RET_V3405"',
        'RETAINED_PMSG_REQUIRED_PHASE = "phase=armed"',
        (
            'RETAINED_PMSG_OBSERVER_CONTRACT = '
            '"mount-read-fsync-exact-unlink-unmount-v1"'
        ),
        'NCM_REBIND_IDENTITY = "same-current-acm-usb-parent-v1"',
        'ATTENDED_OBSERVATION_MODE = "operator-attended-v1"',
        "ATTENDED_WINDOW_SEC = 900",
        "ATTENDED_PRE_HANDOFF_ATTEMPT_LIMIT = 3",
        "ATTENDED_HANDOFF_ATTEMPT_LIMIT = 1",
        "PHASE2_DISPLAY_UID = 3904",
        "PHASE2_DISPLAY_GID = 3904",
        "PHASE2_DISPLAY_MAX_ATTEMPTS = 3",
    ):
        if token not in observation_constants:
            issues.append(f"missing observation channel contract: {token}")
    display_constants = source[:source.find("def source_contract_issues(")]
    for token in (
        'DISPLAY_VISIBLE_SCHEMA = "a90_v3406_f1_display_visible_v1"',
        'DISPLAY_VISIBLE_PREFIX = "A90-F1-DISPLAY-VISIBLE:"',
        'PHASE2_DISPLAY_PROFILE = "phase2-display-v1"',
        'DISPLAY_PRESENTER_LOG_BEGIN = "A90OBS_PRESENTER_LOG_BEGIN"',
        'DISPLAY_PRESENTER_LOG_END = "A90OBS_PRESENTER_LOG_END"',
        'DISPLAY_DIAGNOSTICS_BEGIN = "A90OBS_DISPLAY_DIAGNOSTICS_BEGIN"',
        'DISPLAY_DIAGNOSTICS_END = "A90OBS_DISPLAY_DIAGNOSTICS_END"',
    ):
        if display_constants.count(token) != 1:
            issues.append(f"missing display confirmation contract: {token}")
    exact_retryable_errors = (
        "ATTENDED_RETRYABLE_CHANNEL_ERRORS = (\n"
        '    "A90P1 END marker not found",\n'
        '    "observation menu hide did not complete",\n'
        '    "observation channel did not settle",\n'
        ")\n"
    )
    if observation_constants.count(exact_retryable_errors) != 1:
        issues.append("attended retryable channel errors are not exact")
    read_budget_start = observation_constants.find(
        "F1_HANDOFF_MIN_READ_BUDGET_SEC = ("
    )
    timeout_budget_start = observation_constants.find(
        "F1_HANDOFF_MIN_TIMEOUT_SEC = ("
    )
    menu_start = observation_constants.find("OBSERVATION_MENU_SETTLE_SEC =")
    if (
        read_budget_start < 0
        or timeout_budget_start <= read_budget_start
        or menu_start <= timeout_budget_start
    ):
        issues.append("handoff timeout budget boundary is missing")
    else:
        read_budget = observation_constants[
            read_budget_start:timeout_budget_start
        ]
        for operand in (
            "F1_HANDOFF_COPY_BOUND_SEC",
            "F1_HANDOFF_SHA_PASS_COUNT",
            "F1_HANDOFF_SHA_ALLOWANCE_PER_PASS_SEC",
            "F1_HANDOFF_SWITCH_HELPER_BOUND_COUNT",
            "F1_HANDOFF_SWITCH_HELPER_BOUND_SEC",
            "F1_HANDOFF_DISPLAY_BOUND_SEC",
            "F1_HANDOFF_MISC_ALLOWANCE_SEC",
        ):
            if read_budget.count(operand) != 1:
                issues.append(
                    f"handoff read budget lacks exact operand: {operand}"
                )
        compact_timeout_budget = "".join(
            observation_constants[timeout_budget_start:menu_start].split()
        )
        if (
            "F1_HANDOFF_MIN_READ_BUDGET_SEC"
            "+int(F1_HANDOFF_MAX_PRE_READ_SEC)"
            not in compact_timeout_budget
        ):
            issues.append("handoff timeout formula is not exact")
    epoch_wait_start = source.find("def _bound_bridge_serial_epoch(")
    settle_start = source.find(
        "def settle_observation_channel(",
        epoch_wait_start + 1,
    )
    if epoch_wait_start < 0 or settle_start < 0:
        issues.append("return epoch source boundary is missing")
    else:
        epoch_wait = source[epoch_wait_start:settle_start]
        for token in (
            "before_key = _validated_return_epoch_key(",
            "current_key[3:] == before_key[3:]",
            "deadline - time.monotonic() <= OBSERVATION_MENU_SETTLE_SEC",
            "time.sleep(OBSERVATION_MENU_SETTLE_SEC)",
            'last = "return USB serial epoch confirmation crossed deadline"',
            "confirmed_key != current_key",
            '"usb_serial_epoch_changed": True',
        ):
            if token not in epoch_wait:
                issues.append(f"return epoch gate missing: {token}")
        for forbidden in (
            "run_f1_cmd(",
            "run_f1_shell(",
            "settle_observation_channel(",
            "a90ctl.",
            "d1.",
            "subprocess.",
            "socket.",
        ):
            if forbidden in epoch_wait:
                issues.append(
                    f"return epoch gate issues a device command: {forbidden}"
                )
    timeout_validator_start = source.find("def validate_handoff_timeout(")
    timeout_validator_end = source.find(
        "def require_private_regular(",
        timeout_validator_start + 1,
    )
    if timeout_validator_start < 0 or timeout_validator_end < 0:
        issues.append("handoff timeout validator boundary is missing")
    else:
        timeout_validator = source[
            timeout_validator_start:timeout_validator_end
        ]
        for token in (
            'require_positive_int(value, "observation.handoff_timeout_sec")',
            "if timeout < F1_HANDOFF_MIN_TIMEOUT_SEC:",
            "return timeout",
        ):
            if timeout_validator.count(token) != 1:
                issues.append(
                    f"handoff timeout validator lacks exact gate: {token}"
                )
    load_start = source.find("def load_spec(")
    load_end = source.find("\ndef ", load_start + len("def load_spec("))
    if load_start < 0 or load_end < 0:
        issues.append("manifest load source boundary is missing")
    else:
        load = source[load_start:load_end]
        load_gate = (
            "handoff_timeout = validate_handoff_timeout(\n"
            '        observation.get("handoff_timeout_sec")\n'
            "    )"
        )
        if load.count(load_gate) != 1:
            issues.append("manifest load lacks exact handoff timeout gate")
        if load.count(") = validate_observation_policy(observation)") != 1:
            issues.append("manifest load lacks exact attended policy gate")
        if load.count(
            ") = validate_display_observation(\n"
            "        manifest,\n"
            "        observation,\n"
            "        observation_mode,\n"
            "    )"
        ) != 1:
            issues.append("manifest load lacks exact Phase 2 display gate")
        for token in (
            'observer.get("host_ncm_profile")',
            "HOST_NCM_PROFILE_RE.fullmatch(observer_host_ncm_profile)",
            'observer.get("ncm_rebind_identity") != NCM_REBIND_IDENTITY',
            'observer.get("retained_pmsg_marker") != RETAINED_PMSG_MARKER',
            "retained_pmsg_cleanup_after_private_fsync",
        ):
            if token not in load:
                issues.append(f"manifest load lacks V3405 observer gate: {token}")
    policy_start = source.find("def validate_observation_policy(")
    policy_end = source.find("def require_private_regular(", policy_start + 1)
    if policy_start < 0 or policy_end < 0:
        issues.append("attended policy validator boundary is missing")
    else:
        policy = source[policy_start:policy_end]
        for token in (
            "if mode == ATTENDED_OBSERVATION_MODE:",
            "type(window) is not int or window != ATTENDED_WINDOW_SEC",
            "type(attempts) is not int",
            "attempts != ATTENDED_PRE_HANDOFF_ATTEMPT_LIMIT",
            "type(handoffs) is not int",
            "handoffs != ATTENDED_HANDOFF_ATTEMPT_LIMIT",
            "elif mode == UNATTENDED_OBSERVATION_MODE:",
            "return mode, window, attempts, handoffs",
        ):
            if token not in policy:
                issues.append(f"attended policy validator missing: {token}")
    display_policy_start = source.find("def validate_display_observation(")
    display_policy_end = source.find(
        "def require_private_regular(",
        display_policy_start + 1,
    )
    if display_policy_start < 0 or display_policy_end < 0:
        issues.append("Phase 2 display policy boundary is missing")
    else:
        display_policy = source[
            display_policy_start:display_policy_end
        ]
        for token in (
            "manifest.get(\"schema\") "
            "== staging.PHASE2_DISPLAY_MANIFEST_SCHEMA",
            "if observation_mode != ATTENDED_OBSERVATION_MODE:",
            "if set(item) != expected_keys:",
            "tuple(visible) != PHASE2_DISPLAY_VISIBLE_TEXT",
            'item.get("operator_visible_confirmation_required") is not True',
        ):
            if token not in display_policy:
                issues.append(
                    f"Phase 2 display policy is not exact: {token}"
                )
    candidate_closure_start = source.find(
        "def validate_attended_candidate_closure("
    )
    attended_window_path_start = source.find(
        "def attended_window_path(",
        candidate_closure_start + 1,
    )
    if candidate_closure_start < 0 or attended_window_path_start < 0:
        issues.append("attended candidate closure boundary is missing")
    else:
        candidate_closure = source[
            candidate_closure_start:attended_window_path_start
        ]
        for token in (
            "actions[:len(expected_prefix)] != expected_prefix",
            "set(approved) != approved_keys",
            "set(candidate_start) != start_keys",
            "set(candidate_flashed) != flashed_keys",
            'candidate_start.get("candidate_sha256") != spec.candidate.sha256',
            'type(candidate_start.get("candidate_transfer_count_max")) is not int',
            'candidate_start.get("candidate_transfer_count_max") != 1',
            'type(candidate_flashed.get("candidate_transfer_count")) is not int',
            'candidate_flashed.get("candidate_transfer_count") != 1',
            'candidate_flashed.get("candidate_replay") is not False',
            'candidate_flashed.get("rollback_required") is not True',
            "set(execution) != execution_keys",
            'execution.get("process_started") is not True',
            "value is not True",
            "classify_flash_log(resolved_log)",
        ):
            if token not in candidate_closure:
                issues.append(
                    f"attended candidate closure is not exact: {token}"
                )
    execute_start = source.find("def execute_approved_f1(")
    recover_start = source.find("def recover_approved_rollback(")
    simulate_start = source.find("def simulate_transaction(")
    if min(execute_start, recover_start, simulate_start) < 0:
        return tuple(issues)
    execute = source[execute_start:recover_start]
    ordered = (
        "approved_bindings(spec, args, recovery=False)",
        "verify_local_closure(spec)",
        "validate_stage_result(spec)",
        "require_f1_starting_health(spec, args)",
        "remote_source_preflight(spec, args)",
        '"candidate-transfer-started"',
        "flash_command(spec, args, rollback=False, from_native=True)",
        '"candidate-flashed"',
        "observe_candidate(spec, args, transaction_dir)",
        "invoke_rollback(",
        "close_transaction(",
    )
    cursor = -1
    for token in ordered:
        position = execute.find(token, cursor + 1)
        if position < 0:
            issues.append(f"execute contract missing or out of order: {token}")
        else:
            cursor = position
    guard_start = source.find(
        "def _candidate_return_modemmanager_guard_inputs("
    )
    guard_end = source.find("def _bound_bridge_serial_epoch(", guard_start + 1)
    if guard_start < 0 or guard_end < 0:
        issues.append("candidate-return ModemManager guard boundary is missing")
    else:
        guard_source = source[guard_start:guard_end]
        for token in (
            "Path(spec.stage.bridge_realpath).resolve(strict=True)",
            "stat.S_ISCHR(info.st_mode)",
            "cdc_guard._resolve_endpoint(",
            "os.major(info.st_rdev) != endpoint.major",
            "os.minor(info.st_rdev) != endpoint.minor",
            "identity.get(\"vendor\") != staging.HOST_NCM_VENDOR_ID",
            "identity.get(\"product\") != staging.HOST_NCM_PRODUCT_ID",
            'identity.get("driver") != "cdc_acm"',
            "max_sec = max(",
            "MODEMMANAGER_GUARD_POST_RETURN_COMMAND_COUNT",
            "+ 2 * args.poll_interval",
            "max_sec > cdc_guard.GUARD_MAX_SEC_LIMIT",
            "cdc_guard.ModemManagerGuard.arm(",
            "max_sec=max_sec",
            'f"{corridor}-modemmanager-guard-arm.json"',
            'f"{corridor}-modemmanager-guard-{suffix}.json"',
            "def require_returned_modemmanager_guard(",
            'identity.get("serial") != guard.spec["usb_serial"]',
            'identity.get("driver") != guard.spec["usb_driver"]',
            "guard.topology != expected_topology",
            "guard.matches_node(endpoint.tty_class)",
        ):
            if token not in guard_source:
                issues.append(
                    f"candidate-return ModemManager guard missing: {token}"
                )
        for forbidden in (
            "systemctl",
            "/etc/udev",
            '"04e8"',
            '"6860"',
        ):
            if forbidden in guard_source:
                issues.append(
                    "candidate-return ModemManager guard contains "
                    f"unbound or persistent action: {forbidden}"
                )
    ncm_start = source.find("def rebind_host_ncm_after_reenumeration(")
    pstore_constants_start = source.find("PSTORE_ENTRY_RE = re.compile(")
    pstore_parser_start = source.find("def _pstore_entry_names(", ncm_start + 1)
    if ncm_start < 0 or pstore_parser_start < 0:
        issues.append("host NCM rebind source boundary is missing")
    else:
        ncm = source[ncm_start:pstore_parser_start]
        for token in (
            "staging.require_exact_bridge(spec.stage, args)",
            "staging.exact_a90_ncm_interfaces(bridge_realpath)",
            "if len(interfaces) > 1:",
            "spec.observer_host_ncm_profile",
            '"connection.interface-name"',
            "interface",
            '"ipv4.never-default"',
            '"connection.autoconnect"',
            "staging.require_host_ncm_ready(",
        ):
            if token not in ncm:
                issues.append(f"host NCM rebind contract missing: {token}")
        for forbidden in (
            '"delete"',
            "host_ncm_candidates(",
            "usb_serial",
            "mac",
        ):
            if forbidden in ncm:
                issues.append(
                    f"host NCM rebind contains unbound identity/action: {forbidden}"
                )
    clean_start = source.find("def require_clean_pstore_before_handoff(")
    if min(pstore_constants_start, pstore_parser_start, clean_start) < 0:
        issues.append("pre-handoff pstore parser boundary is missing")
    else:
        pstore_constants = source[pstore_constants_start:pstore_parser_start]
        pstore_parser = source[pstore_parser_start:clean_start]
        if (
            'r"^(?:console|pmsg)-ramoops(?:-[0-9]+)?$"'
            not in pstore_constants
        ):
            issues.append("pre-handoff pstore parser allowlist is not exact")
        for token in (
            'r"^cmdv1 ls /sys/fs/pstore$"',
            'r"^A90P1 BEGIN seq=[0-9]+ cmd=ls argc=2 flags=0x[0-9a-f]+$"',
            'r"^\\[done\\] ls \\([0-9]+ms\\)$"',
            'r"^A90P1 END seq=[0-9]+ cmd=ls rc=0 errno=0 "',
            'r"^a90:/# ?$"',
        ):
            if token not in pstore_constants:
                issues.append(
                    f"pre-handoff pstore control grammar is not exact: {token}"
                )
        for token in (
            "for raw_line in text.splitlines():",
            "entry = PSTORE_ENTRY_RE.fullmatch(line)",
            "pattern.fullmatch(line)",
            'raise ContractError("pstore listing contains a malformed line")',
            "len(names) != len(set(names))",
            "def validate_pstore_before_handoff_receipt(",
            "allow_legacy_empty: bool = False",
            "legacy = allow_legacy_empty and set(value) == legacy_keys",
            "if entries != [] or listing_entries != ():",
            '["mountfs", "pstore", PSTORE_MOUNT_PATH, "pstore", "ro"]',
            '"unexpected_entries",',
            "entries != list(listing_entries)",
            "PSTORE_EXPECTED_BOOT_ENTRY_RE.fullmatch(entry) is None",
            '"expected-boot-records" if expected_boot_records else "empty"',
            'value.get("warning") is not expected_boot_records',
        ):
            if token not in pstore_parser:
                issues.append(
                    f"pre-handoff pstore parser is not exact: {token}"
                )
    classify_start = source.find(
        "def _retained_pmsg_classification(",
        clean_start + 1,
    )
    if clean_start < 0 or classify_start < 0:
        issues.append("pre-handoff pstore gate source boundary is missing")
    else:
        clean = source[clean_start:classify_start]
        for token in (
            "PSTORE_EXPECTED_BOOT_ENTRY_RE.fullmatch(entry) is None",
        ):
            if token not in clean:
                issues.append(
                    f"pre-handoff pstore classifier is not exact: {token}"
                )
        clean_ordered = (
            '["mountfs", "pstore", PSTORE_MOUNT_PATH, "pstore", "ro"]',
            '["ls", PSTORE_MOUNT_PATH]',
            "unexpected_entries = tuple(",
            "if unexpected_entries:",
            '["umount", PSTORE_MOUNT_PATH]',
            '"entries": list(entries)',
            '"classification": (',
            '"warning": bool(entries)',
            '"unexpected_entries": []',
        )
        clean_cursor = -1
        for token in clean_ordered:
            position = clean.find(token, clean_cursor + 1)
            if position < 0:
                issues.append(
                    f"pre-handoff pstore gate missing or out of order: {token}"
                )
            else:
                clean_cursor = position
        for forbidden in (
            '["run",',
            '/bin/busybox rm',
            "unlink(",
            '"pstore"]',
        ):
            if forbidden in clean:
                issues.append(
                    "pre-handoff pstore gate contains write or cleanup: "
                    f"{forbidden}"
                )
    collect_start = source.find("def collect_and_clear_retained_pmsg(")
    remote_source_start = source.find(
        "def remote_source_preflight(",
        collect_start + 1,
    )
    if collect_start < 0 or remote_source_start < 0:
        issues.append("retained pmsg collector source boundary is missing")
    else:
        collect = source[collect_start:remote_source_start]
        collect_ordered = (
            '["mountfs", "pstore", PSTORE_MOUNT_PATH, "pstore"]',
            "PSTORE_PMSG_ENTRY_RE.fullmatch(entries[0])",
            "digest_record = run_f1_cmd(",
            "content = run_f1_cmd(args, [\"cat\", path])",
            "write_private_json_exclusive(",
            '"retained-pmsg-capture.json"',
            "if armed_count != 1:",
            '"retained-pmsg-cleanup-intent.json"',
            'ACTUAL=$(/bin/busybox sha256sum "$P")',
            '[ "$ACTUAL" = "$EXPECTED" ]',
            '/bin/busybox rm "$P"',
            "if _pstore_entry_names(",
            '["umount", PSTORE_MOUNT_PATH]',
            '"retained-pmsg-cleanup.json"',
        )
        collect_cursor = -1
        for token in collect_ordered:
            position = collect.find(token, collect_cursor + 1)
            if position < 0:
                issues.append(
                    f"retained pmsg collector missing or out of order: {token}"
                )
            else:
                collect_cursor = position
        for forbidden in (
            "run_f1_shell(",
            "rm -rf",
            '/bin/busybox rm *',
            '"s\\n"',
            "\nsync\n",
        ):
            if forbidden in collect:
                issues.append(
                    f"retained pmsg collector contains forbidden action: {forbidden!r}"
                )
    observe_start = source.find("def observe_candidate(")
    attended_start = source.find(
        "def attended_retryable_error_identity(",
        observe_start + 1,
    )
    if observe_start < 0 or attended_start < 0:
        issues.append("observation source boundary is missing")
    else:
        observe = source[observe_start:attended_start]
        observe_ordered = (
            'phase="before-source-preflight"',
            "rebind_host_ncm_after_reenumeration(",
            "require_clean_pstore_before_handoff(",
            "remote_source_preflight(spec, args)",
            'phase="before-handoff"',
            "capture_bridge_serial_epoch(",
            "run_handoff(spec, args)",
            "wait_for_candidate_return(",
            "collect_and_clear_retained_pmsg(",
        )
        observe_cursor = -1
        for token in observe_ordered:
            position = observe.find(token, observe_cursor + 1)
            if position < 0:
                issues.append(
                    f"observation contract missing or out of order: {token}"
                )
            else:
                observe_cursor = position
        if (
            observe.count("settle_observation_channel(") != 2
            or observe.count("rebind_host_ncm_after_reenumeration(") != 1
            or observe.count("require_clean_pstore_before_handoff(") != 1
            or observe.count("remote_source_preflight(spec, args)") != 1
            or observe.count("capture_bridge_serial_epoch(") != 1
            or observe.count("run_handoff(spec, args)") != 1
            or observe.count("collect_and_clear_retained_pmsg(") != 1
            or re.search(r"^\s+(?:for|while)\b", observe, re.MULTILINE)
            is not None
        ):
            issues.append("observation corridor is not exact single-shot order")
    return_verify_start = source.find(
        "def _verify_candidate_after_return_epoch_once("
    )
    return_verify_end = source.find(
        "def observe_candidate(",
        return_verify_start + 1,
    )
    if return_verify_start < 0 or return_verify_end < 0:
        issues.append("candidate return verifier boundary is missing")
    else:
        return_verify = source[return_verify_start:return_verify_end]
        return_ordered = (
            "wait_for_new_bridge_serial_epoch(",
            "if return_guard is not None:",
            "not return_guard.healthy(recheck=True)",
            "require_returned_modemmanager_guard(",
            'run_f1_cmd(args, ["version"])',
            "version_lines != [expected_version_line]",
            'raise ContractError("candidate return native epoch identity is not exact")',
            "settle_observation_channel(args, phase=phase)",
            'run_f1_cmd(args, ["selftest"])',
            "len(selftest_lines) != 1",
            'r"selftest: pass=[0-9]+ warn=[0-9]+ fail=0 "',
            'r"duration=[0-9]+ms entries=[1-9][0-9]*"',
            '"native_epoch_version_proven": True',
        )
        return_cursor = -1
        for token in return_ordered:
            position = return_verify.find(token, return_cursor + 1)
            if position < 0:
                issues.append(
                    f"candidate return verifier missing or out of order: {token}"
                )
            else:
                return_cursor = position
        if (
            return_verify.count('run_f1_cmd(args, ["version"])') != 1
            or return_verify.count('run_f1_cmd(args, ["selftest"])') != 1
            or return_verify.count(
                "not return_guard.healthy(recheck=True)"
            )
            != 2
            or "allow_error=True" in return_verify
            or re.search(r"^\s+while\b", return_verify, re.MULTILINE)
            is not None
        ):
            issues.append("candidate return verifier is not exact single-shot order")
    retry_classifier_start = source.find(
        "def attended_retryable_error_identity("
    )
    retry_runtime_start = source.find(
        "def attended_pre_handoff_retryable(",
        retry_classifier_start + 1,
    )
    retry_stored_start = source.find(
        "def attended_stored_failure_retryable(",
        retry_runtime_start + 1,
    )
    candidate_return_start = source.find(
        "def wait_for_candidate_return_attended_once(",
        retry_stored_start + 1,
    )
    if (
        retry_classifier_start < 0
        or retry_runtime_start < 0
        or retry_stored_start < 0
        or candidate_return_start < 0
    ):
        issues.append("attended retry classifier boundary is missing")
    else:
        retry_identity = source[
            retry_classifier_start:retry_runtime_start
        ]
        for token in (
            'if error_type == "ContractError":',
            "for suffix in ATTENDED_RETRYABLE_CHANNEL_ERRORS[1:]",
            'if error_type == "RuntimeError":',
            "message == marker or message.startswith(marker +",
            "return False",
        ):
            if token not in retry_identity:
                issues.append(
                    f"attended retry classifier is not exact: {token}"
                )
        retry_runtime = source[retry_runtime_start:retry_stored_start]
        for token in (
            "if type(exc) not in (ContractError, RuntimeError):",
            "return False",
            "return attended_retryable_error_identity(",
            "type(exc).__name__",
            "attempt=attempt",
        ):
            if token not in retry_runtime:
                issues.append(
                    f"attended runtime retry classifier is not exact: {token}"
                )
        retry_stored = source[retry_stored_start:candidate_return_start]
        for token in (
            'set(error) == {"type", "message"}',
            'isinstance(error.get("type"), str)',
            'isinstance(error.get("message"), str)',
            "and attended_retryable_error_identity(",
            "attempt=attempt",
        ):
            if token not in retry_stored:
                issues.append(
                    f"attended stored retry classifier is not exact: {token}"
                )
    attended_observe_start = source.find("def observe_attended_after_handoff(")
    final_health_start = source.find(
        "def verify_final_health(",
        attended_observe_start + 1,
    )
    if attended_observe_start < 0 or final_health_start < 0:
        issues.append("attended post-handoff observer boundary is missing")
    else:
        attended_observe = source[attended_observe_start:final_health_start]
        attended_observe_ordered = (
            "run_handoff(spec, args)",
            "observe_ssh(spec, args)",
            "wait_for_candidate_return_attended_once(",
            "release_candidate_return_modemmanager_guard(",
            "collect_and_clear_retained_pmsg(",
        )
        attended_observe_cursor = -1
        for token in attended_observe_ordered:
            position = attended_observe.find(
                token,
                attended_observe_cursor + 1,
            )
            if position < 0:
                issues.append(
                    "attended post-handoff observer missing or out of order: "
                    f"{token}"
                )
            else:
                attended_observe_cursor = position
    validation_start = source.find("def validate_attended_continuation(")
    continue_start = source.find(
        "def continue_attended_f1(",
        validation_start + 1,
    )
    if validation_start < 0 or continue_start < 0:
        issues.append("attended continuation validator boundary is missing")
    else:
        validation = source[validation_start:continue_start]
        for token in (
            "validate_attended_candidate_closure(",
            "set(attempt) != attempt_keys",
            "set(failure) != failure_keys",
            'failure.get("within_deadline") is not True',
            'failure.get("candidate_replay") is not False',
            'failure.get("rollback_required") is not True',
            "attended_stored_failure_retryable(",
            "<= failure_timestamp",
            "<= deadline",
        ):
            if token not in validation:
                issues.append(
                    f"attended resume validation is not exact: {token}"
                )
    action_names_start = source.find("def action_names(", continue_start + 1)
    if continue_start < 0 or action_names_start < 0:
        issues.append("attended continuation source boundary is missing")
    else:
        attended = source[continue_start:action_names_start]
        attended_ordered = (
            "validate_attended_continuation(",
            '"attended-pre-handoff-attempt"',
            'phase=f"attended-attempt-{attempt}-before-health"',
            "verify_candidate_health(spec, args)",
            "rebind_host_ncm_after_reenumeration(spec, args)",
            "require_clean_pstore_before_handoff(args)",
            "remote_source_preflight(spec, args)",
            'phase=f"attended-attempt-{attempt}-before-handoff"',
            "capture_bridge_serial_epoch(",
            '"attended observation window expired before handoff"',
            '"attended-pre-handoff-failed"',
            '"candidate-boot-ready"',
            "arm_candidate_return_modemmanager_guard(",
            '"attended-pre-handoff-ready"',
            "intent_timestamp = current_utc()",
            '"attended window expired before durable handoff intent; "',
            '"candidate-return ModemManager guard was lost before intent"',
            '"attended-handoff-started"',
            '"candidate-return ModemManager guard was lost before dispatch"',
            'observe_kwargs = (',
            "observe_attended_after_handoff(",
            "open_display_visible_confirmation(",
            "invoke_rollback(",
            "close_transaction(",
        )
        attended_cursor = -1
        for token in attended_ordered:
            position = attended.find(token, attended_cursor + 1)
            if position < 0:
                issues.append(
                    f"attended contract missing or out of order: {token}"
                )
            else:
                attended_cursor = position
        intent_position = attended.find('"attended-handoff-started"')
        dispatch_position = attended.find(
            "observe_attended_after_handoff(",
            intent_position + 1,
        )
        if (
            intent_position < 0
            or dispatch_position <= intent_position
            or attended.count('"attended-handoff-started"') != 1
            or attended.count("observe_attended_after_handoff(") != 1
            or attended.count(
                "if return_guard is not None and not "
                "return_guard.healthy(recheck=True):"
            )
            != 2
            or '"journal_fsync_completed_before_dispatch": True'
            not in attended[intent_position:dispatch_position]
        ):
            issues.append(
                "attended handoff intent is not durably ordered before dispatch"
            )
        for token in (
            '"handoff_intent": False',
            '"handoff_sent": False',
            '"retryable_channel_failure": retryable',
            '"continuation_allowed": continuation_allowed',
            '"within_deadline": within_deadline',
            'timestamp_utc=failure_observed.strftime("%Y-%m-%dT%H:%M:%SZ")',
            "attempt < spec.pre_handoff_attempt_limit",
            "current_utc() > handoff_deadline",
            'timestamp_utc=intent_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")',
            "within_deadline",
        ):
            if token not in attended:
                issues.append(f"attended retry contract missing: {token}")
        for token in (
            "if spec.display_required and mechanical_display_proof:",
            "return open_display_visible_confirmation(",
            '"visible_confirmation_required": (',
            '"display_mechanical_proven": mechanical_display_proof',
        ):
            if token not in attended:
                issues.append(
                    f"attended display confirmation gate missing: {token}"
                )
    confirm_start = source.find("def confirm_visible_display(")
    action_names_start = source.find("def action_names(", confirm_start + 1)
    if confirm_start < 0 or action_names_start < 0:
        issues.append("display visible confirmation boundary is missing")
    else:
        confirm = source[confirm_start:action_names_start]
        confirm_ordered = (
            "approved_bindings(spec, args, recovery=True)",
            "require_consumed_approval(records, approval_prepared)",
            "load_display_visible_confirmation(",
            'args.visible_approval != receipt["visible_token"]',
            "confirmed > deadline",
            '"display-visible-confirmed"',
            "validate_confirmed_display_proof(",
            "invoke_rollback(",
            "close_transaction(",
        )
        confirm_cursor = -1
        for token in confirm_ordered:
            position = confirm.find(token, confirm_cursor + 1)
            if position < 0:
                issues.append(
                    "display visible confirmation missing or out of order: "
                    f"{token}"
                )
            else:
                confirm_cursor = position
        for forbidden in (
            "rollback=False",
            "candidate-transfer-started",
            "candidate-flashed",
        ):
            if forbidden in confirm:
                issues.append(
                    "display visible confirmation contains candidate route: "
                    f"{forbidden}"
                )
    handoff_start = source.find("def run_handoff(")
    ssh_start = source.find("def ssh_command(", handoff_start + 1)
    if handoff_start < 0 or ssh_start < 0:
        issues.append("handoff source boundary is missing")
    else:
        handoff = source[handoff_start:ssh_start]
        if handoff.count("a90ctl.bridge_exchange(") != 1:
            issues.append("handoff must contain one direct bridge exchange")
        bridge_position = handoff.find("a90ctl.bridge_exchange(")
        bridge_prefix = handoff[:bridge_position]
        if (
            handoff.count(
                "validate_handoff_timeout(spec.handoff_timeout)"
            )
            != 1
            or bridge_prefix.count(
                "validate_handoff_timeout(spec.handoff_timeout)"
            )
            != 1
        ):
            issues.append("handoff runtime lacks exact timeout gate before transport")
        if (
            handoff.count("run_handoff(") != 1
            or re.search(
                r"^\s+(?:for|while)\b",
                bridge_prefix,
                re.MULTILINE,
            )
            is not None
            or "retry_unsafe" in handoff
        ):
            issues.append("handoff bridge exchange is not direct single-shot")
        for token in (
            "input_mode=F1_SERIAL_INPUT_MODE",
            "input_char_delay_sec=F1_SERIAL_INPUT_CHAR_DELAY_SEC",
            "minimum_read_budget_sec=minimum_read_budget",
            "require_prompt_after_end=False",
        ):
            if token not in handoff:
                issues.append(f"handoff transport contract missing: {token}")
    ssh_end = source.find("def exact_ssh_section(", ssh_start + 1)
    if ssh_start < 0 or ssh_end < 0:
        issues.append("SSH diagnostic observer source boundary is missing")
    else:
        ssh = source[ssh_start:ssh_end]
        for token in (
            'cat /run/a90-display/presenter.log 2>/dev/null',
            'if [ -c /dev/dri/card0 ]',
            '/sys/class/drm/card0-*/status',
            '/sys/class/drm/card0-*/dpms',
            '/sys/class/backlight/*',
            'DISPLAY_PRESENTER_LOG_BEGIN',
            'DISPLAY_PRESENTER_LOG_END',
            'DISPLAY_DIAGNOSTICS_BEGIN',
            'DISPLAY_DIAGNOSTICS_END',
        ):
            if token not in ssh:
                issues.append(f"SSH diagnostic observer missing: {token}")
        ssh_without_stderr_null = ssh.replace("2>/dev/null", "")
        if re.search(
            r"(?<![-=])>{1,2}",
            ssh_without_stderr_null,
        ) is not None:
            issues.append("SSH diagnostic observer contains output redirection")
        for forbidden in (
            "tee ",
            "dd ",
            "touch ",
            "mkdir ",
            "rmdir ",
            "ln ",
            "install ",
            "mknod ",
            "chmod ",
            "chown ",
            "rm ",
            "mv ",
            "cp ",
            "mount ",
            "umount ",
            "truncate ",
            "sed -i",
            "sysctl ",
            "reboot ",
            "poweroff ",
            "sync ",
        ):
            if forbidden in ssh:
                issues.append(
                    "SSH diagnostic observer contains write-capable command: "
                    f"{forbidden.strip()}"
                )
    recover = source[recover_start:simulate_start]
    if "rollback=False" in recover or "spec.candidate" in recover:
        issues.append("recovery contains a candidate execution route")
    if "rollback_retry_forbidden" not in source:
        issues.append("rollback ambiguity stop is missing")
    flash_start = source.find("def flash_command(")
    stage_result_start = source.find("def validate_stage_result(", flash_start + 1)
    if flash_start < 0 or stage_result_start < 0:
        issues.append("flash-command source boundary is missing")
    else:
        flash = source[flash_start:stage_result_start]
        for token in (
            '"--serial"',
            "spec.recovery_serial",
            '"--expect-version"',
            "if from_native:",
        ):
            if token not in flash:
                issues.append(f"flash command lacks exact target/version gate: {token}")
        if 'f"{version} build=' in flash:
            issues.append("flash command uses a nonexistent combined image marker")
    if "preexisting staging-live state is never reusable" not in execute:
        issues.append("execute path may reuse preexisting staging output")
    if (
        "events = repair_timeline_from_journal(" not in recover
        or "allow_promotion=resident_promotion" not in recover
    ):
        issues.append("recovery does not rebuild timeline from durable journal")
    if "approved_bindings(spec, args, recovery=True)" not in recover:
        issues.append("recovery does not reopen the consumed approval binding")
    if (
        '"display-visible-confirmed" in actions'
        not in recover
        or "if spec.display_required" not in recover
        or "validate_confirmed_display_proof(" not in recover
        or "display_observation_proven = False" not in recover
    ):
        issues.append(
            "display recovery can promote mechanical proof without operator confirmation"
        )
    if "rollback_pre_spawn_retry(" not in recover:
        issues.append("recovery cannot distinguish a definite rollback pre-spawn failure")
    if "pre_spawn_retry_index=rejection_count" not in recover:
        issues.append("recovery does not preserve the exact rollback after pre-spawn failure")
    parser_start = source.find("def build_parser(")
    main_start = source.find("def main(", parser_start + 1)
    if parser_start < 0 or main_start < 0:
        issues.append("CLI source boundary is missing")
    else:
        cli = source[parser_start:]
        for token in (
            'mode.add_argument("--confirm-visible-display", action="store_true")',
            'parser.add_argument("--visible-approval")',
            "result = confirm_visible_display(spec, args)",
            '"display confirmation accepts only --visible-approval"',
        ):
            if token not in cli:
                issues.append(
                    f"display visible confirmation CLI gate missing: {token}"
                )
    append_start = source.find("def append_record(")
    read_start = source.find("def read_journal(", append_start + 1)
    if append_start < 0 or read_start < 0:
        issues.append("journal source boundary is missing")
    elif "write_private_json_exclusive(path, body)" not in source[
        append_start:read_start
    ]:
        issues.append("journal does not use atomic exclusive publication")
    if "fresh exact F1 approval token mismatch" not in source:
        issues.append("fresh exact approval token gate is missing")
    if "candidate_failure_is_definite_pre_session(candidate_record)" not in execute:
        issues.append("candidate timeout uncertainty does not preserve rollback")
    if 'mode.add_argument("--prepare-approval"' not in source:
        issues.append("separate approval preparation mode is missing")
    return tuple(issues)


def inspect_manifest(spec: F1Spec, issues: list[str]) -> dict[str, Any]:
    source_issues = source_contract_issues(Path(__file__).read_text(encoding="utf-8"))
    all_issues = [*issues, *source_issues]
    return {
        "schema": ORCHESTRATOR_SCHEMA,
        "mode": "host-only-inspection",
        "run_id": spec.stage.run_id,
        "manifest_sha256": spec.stage.manifest_sha256,
        "orchestrator_sha256": sha256_file(Path(__file__).resolve()),
        "staging_adapter_sha256": spec.stage.adapter_sha256,
        "flash_runner_sha256": spec.flash_runner.sha256,
        "candidate_sha256": spec.candidate.sha256,
        "rollback_sha256": spec.rollback.sha256,
        "rootfs_sha256": spec.stage.local_sha256,
        "contract_issues": all_issues,
        "ready_for_approval_preparation": not all_issues,
        "ready_for_live_f1": False,
        "fresh_operator_approval_required": True,
        "manifest_grants_live_authority": False,
        "device_contact": False,
        "device_write": False,
        "candidate_route_in_recovery": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expect-manifest-sha256", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--execute-approved-f1", action="store_true")
    mode.add_argument("--continue-attended-f1", action="store_true")
    mode.add_argument("--confirm-visible-display", action="store_true")
    mode.add_argument("--recover-approved-rollback", action="store_true")
    parser.add_argument("--approval")
    parser.add_argument("--attended-approval")
    parser.add_argument("--visible-approval")
    parser.add_argument("--transaction-dir", type=Path)
    parser.add_argument(
        "--recovery-path",
        choices=("from-native", "adb-recovery"),
        help=(
            "rollback-only recovery origin; the exact recovery ADB target is always "
            "loaded from manifest-bound private evidence"
        ),
    )
    parser.add_argument("--bridge-host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--remote-timeout", type=float, default=180.0)
    parser.add_argument("--bridge-timeout", type=float, default=180.0)
    parser.add_argument("--transfer-timeout", type=float, default=1200.0)
    parser.add_argument("--staging-command-timeout", type=float, default=1800.0)
    parser.add_argument("--flash-command-timeout", type=float, default=600.0)
    parser.add_argument("--ssh-connect-timeout", type=float, default=8.0)
    parser.add_argument("--poll-interval", type=float, default=3.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    live = (
        args.execute_approved_f1
        or args.continue_attended_f1
        or args.confirm_visible_display
        or args.recover_approved_rollback
    )
    final_only = live or args.prepare_approval
    spec, issues = load_spec(
        args.manifest,
        args.expect_manifest_sha256,
        allow_draft=not final_only,
    )
    if not final_only:
        result = inspect_manifest(spec, issues)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if not result["contract_issues"] else 2
    if args.prepare_approval:
        if (
            args.approval is not None
            or args.attended_approval is not None
            or args.visible_approval is not None
        ):
            raise ContractError("approval preparation does not accept live approval")
        result = prepare_approval(spec)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.transaction_dir is None:
        raise ContractError("--transaction-dir is required for live F1")
    if args.execute_approved_f1:
        if args.recovery_path is not None:
            raise ContractError("initial execution does not accept --recovery-path")
        if args.attended_approval is not None:
            raise ContractError("initial execution does not accept attended approval")
        if args.visible_approval is not None:
            raise ContractError("initial execution does not accept display approval")
        if args.approval is None:
            raise ContractError("initial execution requires --approval")
        result = execute_approved_f1(spec, args)
    elif args.continue_attended_f1:
        if (
            args.approval is not None
            or args.visible_approval is not None
            or args.recovery_path is not None
        ):
            raise ContractError(
                "attended continuation accepts no F1 approval or recovery path"
            )
        if args.attended_approval is None:
            raise ContractError(
                "attended continuation requires --attended-approval"
            )
        result = continue_attended_f1(spec, args)
    elif args.confirm_visible_display:
        if (
            args.approval is not None
            or args.attended_approval is not None
            or args.recovery_path is not None
        ):
            raise ContractError(
                "display confirmation accepts only --visible-approval"
            )
        if args.visible_approval is None:
            raise ContractError(
                "display confirmation requires --visible-approval"
            )
        result = confirm_visible_display(spec, args)
    else:
        if (
            args.approval is not None
            or args.attended_approval is not None
            or args.visible_approval is not None
        ):
            raise ContractError("rollback recovery does not accept live approval")
        result = recover_approved_rollback(spec, args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(f"a90-v3403-f1: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
