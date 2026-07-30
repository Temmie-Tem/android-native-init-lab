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
import json
import os
import re
import stat
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90ctl  # noqa: E402
import run_d1_chroot_mvp as d1  # noqa: E402


ORCHESTRATOR_SCHEMA = "a90_v3403_f1_orchestrator_v1"
JOURNAL_SCHEMA = "a90_v3403_f1_journal_v1"
APPROVAL_PREPARED_SCHEMA = "a90_v3403_f1_approval_prepared_v1"
APPROVAL_PREFIX = "A90-F1-V2-APPROVE:"
ATTENDED_WINDOW_SCHEMA = "a90_v3403_f1_attended_window_v1"
ATTENDED_CONTINUE_PREFIX = "A90-F1-ATTENDED-CONTINUE:"
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
HANDOFF_COMMAND = "switch-root-to-distro"
HANDOFF_TOKEN = "SERVER-DISTRO-D3B-SWITCHROOT"
OBSERVER_TRANSPORT_SCOPE = "USB-local NCM only"
PSTORE_ZERO_RE = staging.PSTORE_ZERO_RE
HEX64_RE = staging.HEX64_RE
NATIVE_FLASH_PATH = (REVAL_DIR / "native_init_flash.py").resolve()
STAGING_PATH = (SCRIPT_DIR / "a90_v3403_absent_only_staging.py").resolve()
OBSERVATION_OUTPUT_MARKERS = (
    "source_sha phase=initial",
    "source_sha phase=post-display-cleanup",
    "source_sha phase=work-copy",
    "source_sha phase=post-copy-source",
    "work_copy=ready",
    "exec_switch_root_now",
)
F1_SERIAL_INPUT_MODE = "slow"
F1_SERIAL_INPUT_CHAR_DELAY_SEC = 0.02
F1_HANDOFF_MAX_PRE_READ_SEC = 5.0
F1_HANDOFF_COPY_BOUND_SEC = 300
F1_HANDOFF_SHA_PASS_COUNT = 4
F1_HANDOFF_SHA_ALLOWANCE_PER_PASS_SEC = 90
F1_HANDOFF_SWITCH_HELPER_BOUND_COUNT = 2
F1_HANDOFF_SWITCH_HELPER_BOUND_SEC = 30
F1_HANDOFF_MISC_ALLOWANCE_SEC = 180
F1_HANDOFF_MIN_READ_BUDGET_SEC = (
    F1_HANDOFF_COPY_BOUND_SEC
    + F1_HANDOFF_SHA_PASS_COUNT * F1_HANDOFF_SHA_ALLOWANCE_PER_PASS_SEC
    + F1_HANDOFF_SWITCH_HELPER_BOUND_COUNT
    * F1_HANDOFF_SWITCH_HELPER_BOUND_SEC
    + F1_HANDOFF_MISC_ALLOWANCE_SEC
)
F1_HANDOFF_MIN_TIMEOUT_SEC = (
    F1_HANDOFF_MIN_READ_BUDGET_SEC + int(F1_HANDOFF_MAX_PRE_READ_SEC)
)
OBSERVATION_MENU_SETTLE_SEC = 3.0
OBSERVATION_CHANNEL_CANARY = ("run", "/bin/busybox", "true")
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
    candidate_boot_timeout: int
    handoff_timeout: int
    ssh_marker_timeout: int
    candidate_return_timeout: int
    rollback_boot_timeout: int
    observation_mode: str
    attended_window_sec: int
    pre_handoff_attempt_limit: int
    handoff_attempt_limit: int
    recovery_serial_sha256: str
    recovery_serial: str
    recovery_evidence: tuple[staging.BoundFile, ...]
    orchestrator_size: int
    orchestrator_sha256: str


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

    candidate_version, candidate_build = validate_expected_boot(
        manifest.get("candidate_boot"),
        "candidate_boot",
        candidate,
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
            candidate_boot_timeout=candidate_boot_timeout,
            handoff_timeout=handoff_timeout,
            ssh_marker_timeout=ssh_marker_timeout,
            candidate_return_timeout=candidate_return_timeout,
            rollback_boot_timeout=rollback_boot_timeout,
            observation_mode=observation_mode,
            attended_window_sec=attended_window_sec,
            pre_handoff_attempt_limit=pre_handoff_attempt_limit,
            handoff_attempt_limit=handoff_attempt_limit,
            recovery_serial_sha256=recovery_serial_sha256,
            recovery_serial=recovery_serial,
            recovery_evidence=recovery_evidence,
            orchestrator_size=orchestrator_size,
            orchestrator_sha256=orchestrator_sha256,
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


def load_timeline(transaction_dir: Path) -> list[dict[str, str]]:
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
    try:
        positions = [CANONICAL_EVENTS.index(str(name)) for name in names]
    except ValueError as exc:
        raise ContractError("timeline contains a non-canonical event") from exc
    if positions != sorted(set(positions)):
        raise ContractError("timeline is not in canonical order")
    return events


def add_event(
    transaction_dir: Path,
    events: list[dict[str, str]],
    name: str,
) -> None:
    if name not in CANONICAL_EVENTS:
        raise ContractError(f"non-canonical timeline event: {name!r}")
    names = [event.get("name") for event in events]
    if name in names:
        raise ContractError(f"duplicate timeline event: {name!r}")
    if names and CANONICAL_EVENTS.index(name) <= CANONICAL_EVENTS.index(str(names[-1])):
        raise ContractError(f"timeline event out of order: {name!r}")
    events.append({"name": name, "timestamp_utc": utc_now()})
    write_private_json(transaction_dir / "timeline.json", {"events": events})


def ensure_event(
    transaction_dir: Path,
    events: list[dict[str, str]],
    name: str,
) -> None:
    if name in [event.get("name") for event in events]:
        return
    add_event(transaction_dir, events, name)


JOURNAL_EVENT_ACTIONS = {
    "live_session_start": ("preflight",),
    "candidate_flash_start": ("candidate-transfer-started",),
    "candidate_flash_done": ("candidate-flashed",),
    "candidate_boot_ready": ("candidate-boot-ready",),
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
) -> list[dict[str, str]]:
    existing = load_timeline(transaction_dir)
    existing_by_name = {event["name"]: event["timestamp_utc"] for event in existing}
    timestamps: dict[str, str] = {}
    for event_name, actions in JOURNAL_EVENT_ACTIONS.items():
        for record in records:
            if record.get("action") in actions:
                timestamps[event_name] = str(record["timestamp_utc"])
                break
    repaired: list[dict[str, str]] = []
    for name in CANONICAL_EVENTS:
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
    return {
        "schema": "a90_v3403_f1_approval_binding_v1",
        "run_id": spec.stage.run_id,
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
        "observation_mode": spec.observation_mode,
        "attended_window_sec": spec.attended_window_sec,
        "pre_handoff_attempt_limit": spec.pre_handoff_attempt_limit,
        "handoff_attempt_limit": spec.handoff_attempt_limit,
        "candidate_attempt_limit": 1,
        "mandatory_rollback_preapproved_after_candidate_start": True,
        "candidate_replay": False,
        "only_partition_payload": "boot",
    }


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
    if spec.manifest.get("schema") != FINAL_MANIFEST_SCHEMA:
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


def require_f1_baseline(args: argparse.Namespace) -> dict[str, Any]:
    return staging.require_baseline(
        args,
        input_mode=F1_SERIAL_INPUT_MODE,
        input_char_delay_sec=F1_SERIAL_INPUT_CHAR_DELAY_SEC,
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


def remote_source_preflight(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    final = staging.shlex.quote(spec.stage.remote_final)
    work = staging.shlex.quote(spec.stage.remote_work)
    script = "\n".join(
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
    return run_f1_shell(args, script)


def verify_candidate_health(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    bridge = staging.require_exact_bridge(spec.stage, args)
    version = run_f1_cmd(args, ["version"])
    selftest = run_f1_cmd(args, ["selftest"])
    version_text = str(version.get("text") or "")
    if (
        spec.candidate_version not in version_text
        or spec.candidate_build not in version_text
    ):
        raise ContractError("candidate boot identity lacks exact version/build")
    if "fail=0" not in str(selftest.get("text") or ""):
        raise ContractError("candidate boot selftest is not fail=0")
    return {
        "exact_bridge": True,
        "selected_realpath": bridge.get("selected_realpath"),
        "version": version,
        "selftest": selftest,
    }


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
    for phase in ("initial", "post-display-cleanup", "work-copy", "post-copy-source"):
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


def observe_ssh(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    deadline = time.monotonic() + spec.ssh_marker_timeout
    attempts = 0
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        attempts += 1
        completed = subprocess.run(
            ssh_command(spec, args),
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=args.ssh_connect_timeout + 10.0,
            check=False,
        )
        text = completed.stdout + completed.stderr
        last = {"returncode": completed.returncode, "text": text}
        proc1_init = re.search(r"^pid1_comm=init$", text, re.MULTILINE) is not None
        proc1_exe = re.search(r"^proc1_exe=\S*/init$", text, re.MULTILINE) is not None
        if (
            completed.returncode == 0
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
    raise RuntimeError(f"Debian PID1 marker timeout after {attempts} attempts; last={last}")


def wait_for_candidate_return(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    deadline = time.monotonic() + spec.candidate_return_timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            version = run_f1_cmd(args, ["version"], allow_error=True)
            text = str(version.get("text") or "")
            if spec.candidate_version in text and spec.candidate_build in text:
                selftest = run_f1_cmd(args, ["selftest"], allow_error=True)
                if "fail=0" in str(selftest.get("text") or ""):
                    return {"version": version, "selftest": selftest}
            last = text
        except Exception as exc:  # noqa: BLE001 - bounded reboot polling
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(args.poll_interval)
    raise RuntimeError(f"candidate did not return before rollback deadline; last={last!r}")


def observe_candidate(spec: F1Spec, args: argparse.Namespace, transaction_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"proof": False}
    try:
        result["channel_before_source"] = settle_observation_channel(
            args,
            phase="before-source-preflight",
        )
        result["source_preflight"] = remote_source_preflight(spec, args)
        result["channel_before_handoff"] = settle_observation_channel(
            args,
            phase="before-handoff",
        )
        result["handoff"] = run_handoff(spec, args)
        result["ssh"] = observe_ssh(spec, args)
        result["proof"] = True
    except Exception as exc:  # noqa: BLE001 - rollback remains mandatory
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        try:
            result["candidate_return"] = wait_for_candidate_return(spec, args)
        except Exception as exc:  # noqa: BLE001 - recovery must resume later
            result["candidate_return_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
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
) -> dict[str, Any]:
    deadline = time.monotonic() + spec.candidate_return_timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            bridge = staging.require_exact_bridge(spec.stage, args)
        except Exception as exc:  # noqa: BLE001 - bounded host-only enumeration
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(args.poll_interval)
            continue
        time.sleep(OBSERVATION_MENU_SETTLE_SEC)
        channel = settle_observation_channel(
            args,
            phase="attended-candidate-return",
        )
        version = run_f1_cmd(args, ["version"])
        selftest = run_f1_cmd(args, ["selftest"])
        version_text = str(version.get("text") or "")
        if (
            spec.candidate_version not in version_text
            or spec.candidate_build not in version_text
            or "fail=0" not in str(selftest.get("text") or "")
        ):
            raise ContractError(
                "attended candidate return is not the exact healthy candidate"
            )
        return {
            "exact_bridge": True,
            "selected_realpath": bridge.get("selected_realpath"),
            "channel": channel,
            "version": version,
            "selftest": selftest,
            "device_command_attempts": 1,
        }
    raise RuntimeError(
        "attended candidate did not re-enumerate before rollback deadline; "
        f"last={last!r}"
    )


def observe_attended_after_handoff(
    spec: F1Spec,
    args: argparse.Namespace,
    transaction_dir: Path,
    pre_handoff: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "proof": False,
        "pre_handoff": pre_handoff,
        "handoff_attempt_limit": spec.handoff_attempt_limit,
    }
    try:
        result["handoff"] = run_handoff(spec, args)
        result["ssh"] = observe_ssh(spec, args)
        result["proof"] = True
    except Exception as exc:  # noqa: BLE001 - rollback remains mandatory
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        try:
            result["candidate_return"] = (
                wait_for_candidate_return_attended_once(spec, args)
            )
        except Exception as exc:  # noqa: BLE001 - recovery must resume later
            result["candidate_return_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
    write_private_json_exclusive(transaction_dir / "observation.json", result)
    return result


def verify_final_health(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    bridge = staging.require_exact_bridge(spec.stage, args)
    channel = settle_observation_channel(
        args,
        phase="before-final-health",
    )
    baseline = require_f1_baseline(args)
    return {
        "exact_bridge": True,
        "selected_realpath": bridge.get("selected_realpath"),
        "channel": channel,
        "version": spec.rollback_version,
        "build": spec.rollback_build,
        "selftest_fail_zero": True,
        "pstore_entries_zero": True,
        "baseline": baseline,
    }


def require_rollback_source_native(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    staging.require_exact_bridge(spec.stage, args)
    version = run_f1_cmd(args, ["version"], allow_error=True)
    selftest = run_f1_cmd(args, ["selftest"], allow_error=True)
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
) -> dict[str, Any]:
    ensure_event(transaction_dir, events, "rollback_flash_start")
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
    ensure_event(transaction_dir, events, "rollback_flash_done")
    health = verify_final_health(spec, args)
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
    ensure_event(transaction_dir, events, "rollback_boot_ready")
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
    events[:] = repair_timeline_from_journal(
        transaction_dir,
        read_journal(spec, transaction_dir),
    )
    ensure_event(transaction_dir, events, "live_session_end")
    names = [event["name"] for event in events]
    if candidate_complete and names != list(CANONICAL_EVENTS):
        raise ContractError("completed candidate transaction lacks the canonical timeline")
    if not candidate_complete:
        status = "ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK"
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


def execute_approved_f1(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
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
        require_f1_baseline(args)
        verify_local_closure(spec)
        source_preflight = remote_source_preflight(spec, args)
        append_record(
            journal_dir,
            "APPROVED",
            "rootfs-candidate-preflight",
            {
                "candidate_attempted": False,
                "final_regular": True,
                "work_absent": True,
                "rootfs_size": spec.stage.local_size,
                "rootfs_sha256": spec.stage.local_sha256,
                "record": source_preflight,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
    except Exception as exc:
        abort_before_candidate(spec, transaction_dir, journal_dir, events, exc)
        raise

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
            require_rollback_source_native(spec, args)
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
        )
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
    candidate_health_channel = settle_observation_channel(
        args,
        phase="before-candidate-health",
    )
    candidate_health = verify_candidate_health(spec, args)
    append_record(
        journal_dir,
        "CANDIDATE_FLASHED",
        "candidate-boot-ready",
        {
            "candidate_version": spec.candidate_version,
            "candidate_build": spec.candidate_build,
            "selftest_fail_zero": True,
            "channel": candidate_health_channel,
            "health": candidate_health,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    ensure_event(transaction_dir, events, "candidate_boot_ready")

    observation = observe_candidate(spec, args, transaction_dir)
    append_record(
        journal_dir,
        "OBSERVED",
        "observation-proven" if observation.get("proof") else "observation-no-proof",
        {
            "debian_pid1_proven": observation.get("proof") is True,
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
        source_preflight = remote_source_preflight(spec, args)
        channel_before_handoff = settle_observation_channel(
            args,
            phase=f"attended-attempt-{attempt}-before-handoff",
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
        "source_preflight": source_preflight,
        "channel_before_handoff": channel_before_handoff,
    }
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
    observation = observe_attended_after_handoff(
        spec,
        args,
        transaction_dir,
        pre_handoff,
    )
    append_record(
        journal_dir,
        "OBSERVED",
        "observation-proven" if observation.get("proof") else "observation-no-proof",
        {
            "debian_pid1_proven": observation.get("proof") is True,
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


def action_names(records: list[dict[str, Any]]) -> list[str]:
    return [str(record.get("action")) for record in records]


def recover_approved_rollback(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
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
    events = repair_timeline_from_journal(transaction_dir, records)
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
            require_rollback_source_native(spec, args)
        health = invoke_rollback(
            spec,
            args,
            transaction_dir,
            journal_dir,
            events,
            from_native=from_native,
            pre_spawn_retry_index=rejection_count,
        )
    elif rollback_started and not rollback_flashed:
        health = verify_final_health(spec, args)
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
        health = verify_final_health(spec, args)
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
            require_rollback_source_native(spec, args)
        health = invoke_rollback(
            spec,
            args,
            transaction_dir,
            journal_dir,
            events,
            from_native=from_native,
        )

    observation_proven = "observation-proven" in actions
    candidate_complete = (
        "candidate-flashed" in actions and "candidate-boot-ready" in actions
    )
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
        "def prepare_approval(",
        "def load_approval_prepared(",
        "def candidate_failure_is_definite_pre_session(",
        "def rollback_pre_spawn_retry(",
        "def validate_handoff_timeout(",
        "def settle_observation_channel(",
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
        "F1_HANDOFF_COPY_BOUND_SEC = 300",
        "F1_HANDOFF_SHA_PASS_COUNT = 4",
        "F1_HANDOFF_SHA_ALLOWANCE_PER_PASS_SEC = 90",
        "F1_HANDOFF_SWITCH_HELPER_BOUND_COUNT = 2",
        "F1_HANDOFF_SWITCH_HELPER_BOUND_SEC = 30",
        "F1_HANDOFF_MISC_ALLOWANCE_SEC = 180",
        "F1_HANDOFF_MIN_READ_BUDGET_SEC = (",
        "F1_HANDOFF_MIN_TIMEOUT_SEC = (",
        "OBSERVATION_MENU_SETTLE_SEC = 3.0",
        'OBSERVATION_CHANNEL_CANARY = ("run", "/bin/busybox", "true")',
        'ATTENDED_OBSERVATION_MODE = "operator-attended-v1"',
        "ATTENDED_WINDOW_SEC = 900",
        "ATTENDED_PRE_HANDOFF_ATTEMPT_LIMIT = 3",
        "ATTENDED_HANDOFF_ATTEMPT_LIMIT = 1",
    ):
        if token not in observation_constants:
            issues.append(f"missing observation channel contract: {token}")
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
            "F1_HANDOFF_MISC_ALLOWANCE_SEC",
        ):
            if read_budget.count(operand) != 1:
                issues.append(
                    f"handoff 900-second read budget lacks exact operand: {operand}"
                )
        compact_timeout_budget = "".join(
            observation_constants[timeout_budget_start:menu_start].split()
        )
        if (
            "F1_HANDOFF_MIN_READ_BUDGET_SEC"
            "+int(F1_HANDOFF_MAX_PRE_READ_SEC)"
            not in compact_timeout_budget
        ):
            issues.append("handoff 905-second timeout formula is not exact")
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
        "require_f1_baseline(args)",
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
            "remote_source_preflight(spec, args)",
            'phase="before-handoff"',
            "run_handoff(spec, args)",
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
            or observe.count("remote_source_preflight(spec, args)") != 1
            or observe.count("run_handoff(spec, args)") != 1
            or re.search(r"^\s+(?:for|while)\b", observe, re.MULTILINE)
            is not None
        ):
            issues.append("observation corridor is not exact single-shot order")
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
            "remote_source_preflight(spec, args)",
            'phase=f"attended-attempt-{attempt}-before-handoff"',
            '"attended observation window expired before handoff"',
            '"attended-pre-handoff-failed"',
            '"candidate-boot-ready"',
            '"attended-pre-handoff-ready"',
            "intent_timestamp = current_utc()",
            '"attended window expired before durable handoff intent; "',
            '"attended-handoff-started"',
            "observe_attended_after_handoff(",
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
    if "repair_timeline_from_journal(transaction_dir, records)" not in recover:
        issues.append("recovery does not rebuild timeline from durable journal")
    if "approved_bindings(spec, args, recovery=True)" not in recover:
        issues.append("recovery does not reopen the consumed approval binding")
    if "rollback_pre_spawn_retry(" not in recover:
        issues.append("recovery cannot distinguish a definite rollback pre-spawn failure")
    if "pre_spawn_retry_index=rejection_count" not in recover:
        issues.append("recovery does not preserve the exact rollback after pre-spawn failure")
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
    mode.add_argument("--recover-approved-rollback", action="store_true")
    parser.add_argument("--approval")
    parser.add_argument("--attended-approval")
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
        if args.approval is not None or args.attended_approval is not None:
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
        if args.approval is None:
            raise ContractError("initial execution requires --approval")
        result = execute_approved_f1(spec, args)
    elif args.continue_attended_f1:
        if args.approval is not None or args.recovery_path is not None:
            raise ContractError(
                "attended continuation accepts no F1 approval or recovery path"
            )
        if args.attended_approval is None:
            raise ContractError(
                "attended continuation requires --attended-approval"
            )
        result = continue_attended_f1(spec, args)
    else:
        if args.approval is not None or args.attended_approval is not None:
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
