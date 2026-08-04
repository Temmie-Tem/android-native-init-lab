#!/usr/bin/env python3
"""Manifest-bound attended A90 resident switch-root session runner.

The default and preparation modes are host-only.  Live mode performs no
partition or payload transfer: it composes the already-reviewed resident
health, handoff, Debian observation, native-return, NCM, and framed command
primitives behind one durable attended-session approval.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_transition_engine_v2 as engine  # noqa: E402
import a90_phase3_d1_observer_v1 as phase3_observer  # noqa: E402
import a90_resident_preserved_d1_prep_v1 as preserved_prep  # noqa: E402
import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402
from a90_transition_contract_v2 import (  # noqa: E402
    AttendedSessionBinding,
    DISPLAY_SUCCESSOR,
    RiskTier,
    SessionAction,
    SessionPreflight,
    Workflow,
)


SCHEMA = "a90_d1_fast_loop_manifest_v2"
STATUS = "ready-for-d1-fast-loop-approval"
APPROVAL_SCHEMA = "a90_d1_fast_loop_approval_v2"
APPROVAL_PREFIX = "A90-D1-FAST-LOOP-V2-APPROVE:"
JOURNAL_SCHEMA = "a90_d1_fast_loop_journal_v2"
RESULT_SCHEMA = "a90_d1_fast_loop_action_v2"
OUTCOME_SCHEMA = "a90_d1_fast_loop_engine_outcome_v2"
VISIBLE_CONFIRMATION_SCHEMA = "a90_d1_display_visible_confirmation_v1"
RUN_ID_RE = re.compile(r"^a90-d1-attended-[0-9]{8}-[0-9]{2}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
RESIDENT_RUN_RE = re.compile(
    r"^a90-v3406-debian-display-f1-[0-9]{8}-[0-9]{2}$"
)
PRIVATE_ROOT = (REPO_ROOT / "workspace/private").resolve()
PRIVATE_RUN_BASE = (PRIVATE_ROOT / "runs/server-distro").resolve()
WORK_PATH = "/mnt/sdext/a90/runtime/d3-handoff-work.img"
WORK_MODE = "600"
MAX_DURATION_SEC = 8 * 60 * 60
MAX_ACTIONS = 32
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 54321
REMOTE_TIMEOUT_SEC = 180.0
BRIDGE_TIMEOUT_SEC = 180.0
FLASH_TIMEOUT_FOR_GUARD_BUDGET_SEC = 600.0
SSH_CONNECT_TIMEOUT_SEC = 8.0
POLL_INTERVAL_SEC = 3.0

RESIDENT_ACTIONS = (
    "preflight",
    "approved",
    "staging-started",
    "rootfs-staged",
    "rootfs-candidate-preflight",
    "resident-promotion-guard-armed",
    "candidate-transfer-started",
    "candidate-flashed",
    "candidate-boot-ready",
    "candidate-health-verified",
    "closed",
)

SOURCE_PATHS = {
    "runner": Path(__file__).resolve(),
    "transition_contract": REVAL_DIR / "a90_transition_contract_v2.py",
    "transition_engine": SCRIPT_DIR / "a90_transition_engine_v2.py",
    "f1_orchestrator": SCRIPT_DIR / "a90_v3403_f1_orchestrator.py",
    "staging_contract": SCRIPT_DIR / "a90_v3403_absent_only_staging.py",
    "observation_pipeline": REVAL_DIR / "a90_observation_pipeline.py",
    "display_observer": SCRIPT_DIR / "a90_phase2d_display_observer.py",
    "framed_transport": REVAL_DIR / "a90ctl.py",
    "cdc_acm_guard": REVAL_DIR / "device_action_cdc_acm_observer_v1.py",
    "cmdv1_shell_adapter": SCRIPT_DIR / "run_d1_chroot_mvp.py",
    "workspace_bootstrap": REVAL_DIR / "_workspace_bootstrap.py",
    "bridge_selector": REVAL_DIR / "a90_bridge.py",
    "serial_lock": REVAL_DIR / "a90_serial_lock.py",
    "serial_tcp_bridge": REVAL_DIR / "serial_tcp_bridge.py",
    "phase3_observer": SCRIPT_DIR / "a90_phase3_d1_observer_v1.py",
    "preserved_d1_prep": SCRIPT_DIR / "a90_resident_preserved_d1_prep_v1.py",
}
SESSION_DIR_NAME = "d1-live"
SESSION_LOCK_NAME = "d1-live.lock"


class ContractError(RuntimeError):
    """Raised before widening or repeating an A90 D1 effect."""


@dataclass(frozen=True)
class BoundFile:
    path: Path
    size: int
    sha256: str


@dataclass(frozen=True)
class SessionSpec:
    manifest_path: Path
    manifest_sha256: str
    run_id: str
    resident_run_id: str
    resident_manifest: BoundFile
    resident_journal: tuple[BoundFile, ...]
    candidate: BoundFile
    rollback: BoundFile
    rootfs: BoundFile
    rootfs_profile: str
    candidate_version: str
    candidate_build: str
    remote_final: str
    remote_work: str
    bridge_device: str
    bridge_realpath: str
    recovery_serial_sha256: str
    observer_key: Path
    observer_public_key_sha256: str
    observer_device: str
    observer_port: int
    observer_host_ncm_profile: str
    handoff_command: tuple[str, ...]
    handoff_timeout: int
    ssh_marker_timeout: int
    candidate_return_timeout: int
    source_closure: dict[str, BoundFile]
    transaction_dir: Path
    session_lock_path: Path
    session_duration_sec: int
    max_actions: int
    recovery_profile: str
    resident_evidence_kind: str = "ordinary-resident-install-v2"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _sample_epoch_sec(
    clock: Callable[[], float],
    *,
    floor_epoch_sec: int,
) -> int:
    if not callable(clock) or type(floor_epoch_sec) is not int or floor_epoch_sec < 0:
        raise ContractError("D1 session clock binding is not exact")
    try:
        observed = clock()
        if isinstance(observed, bool) or not isinstance(observed, (int, float)):
            raise TypeError("clock did not return a number")
        current = int(observed)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ContractError("D1 session clock is not exact") from exc
    if current < 0:
        raise ContractError("D1 session clock is not exact")
    return max(floor_epoch_sec, current)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _private_bytes(value: Any) -> bytes:
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


def _fsync_dir(path: Path) -> None:
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
        body = _private_bytes(value)
        offset = 0
        while offset < len(body):
            written = os.write(descriptor, body[offset:])
            if written <= 0:
                raise ContractError("short private JSON write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path, follow_symlinks=False)
        _fsync_dir(path.parent)
    except FileExistsError as exc:
        raise ContractError(f"private evidence already exists: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise ContractError(f"{label} is not lowercase SHA256")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} is not a nonempty string")
    return value


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} is not an object")
    return value


def _require_private_regular(path: Path) -> os.stat_result:
    try:
        resolved = path.resolve(strict=True)
        info = path.lstat()
    except OSError as exc:
        raise ContractError(f"private file is unavailable: {path}") from exc
    if (
        not resolved.is_relative_to(PRIVATE_ROOT)
        or not stat.S_ISREG(info.st_mode)
        or path.is_symlink()
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise ContractError(f"private file identity is not exact: {path}")
    return info


def _bound_file(path: Path, *, private: bool) -> BoundFile:
    if not path.is_absolute():
        path = (Path.cwd() / path).absolute()
    if private:
        info = _require_private_regular(path)
    else:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or path.is_symlink():
            raise ContractError(f"source is not a regular file: {path}")
    return BoundFile(path.resolve(strict=True), info.st_size, sha256_file(path))


def _bound_dict(value: Any, label: str, *, private: bool) -> BoundFile:
    item = _require_dict(value, label)
    if set(item) != {"path", "size", "sha256"}:
        raise ContractError(f"{label} key set is not exact")
    path = Path(_require_string(item.get("path"), f"{label}.path"))
    expected_size = item.get("size")
    expected_sha = _require_sha(item.get("sha256"), f"{label}.sha256")
    if type(expected_size) is not int or expected_size <= 0:
        raise ContractError(f"{label}.size is not positive")
    actual = _bound_file(path, private=private)
    if actual.size != expected_size or actual.sha256 != expected_sha:
        raise ContractError(f"{label} changed")
    return actual


def _as_dict(item: BoundFile) -> dict[str, Any]:
    return {"path": str(item.path), "size": item.size, "sha256": item.sha256}


def _read_private_json(path: Path) -> dict[str, Any]:
    _require_private_regular(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"private JSON is invalid: {path}") from exc
    return _require_dict(value, str(path))


def _validate_resident_native_health(
    value: Any,
    *,
    expected_version: str,
    expected_build: str,
    expected_bridge_realpath: str,
) -> dict[str, str]:
    native = _require_dict(value, "resident native health")
    version = _require_dict(native.get("version"), "resident version receipt")
    selftest = _require_dict(
        native.get("selftest"),
        "resident selftest receipt",
    )
    receipt_keys = {"command", "rc", "status", "trust", "begin", "end", "text"}
    if (
        native.get("exact_bridge") is not True
        or native.get("selected_realpath") != expected_bridge_realpath
        or set(version) != receipt_keys
        or version.get("command") != ["version"]
        or type(version.get("rc")) is not int
        or version.get("rc") != 0
        or version.get("status") != "ok"
        or type(version.get("text")) is not str
        or set(selftest) != receipt_keys
        or selftest.get("command") != ["selftest"]
        or type(selftest.get("rc")) is not int
        or selftest.get("rc") != 0
        or selftest.get("status") != "ok"
        or type(selftest.get("text")) is not str
    ):
        raise ContractError("resident native health receipts are not exact")
    expected_version_line = (
        f"version: {expected_version} build={expected_build}"
    )
    version_facts = [
        line
        for line in version["text"].splitlines()
        if line.startswith("version: ")
    ]
    selftest_facts = [
        line
        for line in selftest["text"].splitlines()
        if line.startswith("selftest: ")
    ]
    if (
        version_facts != [expected_version_line]
        or len(selftest_facts) != 1
        or re.fullmatch(
            r"selftest: pass=[0-9]+ warn=[0-9]+ fail=0 "
            r"duration=[0-9]+ms entries=[1-9][0-9]*",
            selftest_facts[0] if selftest_facts else "",
        )
        is None
    ):
        raise ContractError("resident native health facts are not exact")
    return {
        "version_line": expected_version_line,
        "selftest_line": selftest_facts[0],
    }


def _require_exact_command_receipt(
    value: Any,
    *,
    command: list[str],
    label: str,
) -> dict[str, Any]:
    receipt = _require_dict(value, label)
    if (
        set(receipt)
        != {"command", "rc", "status", "trust", "begin", "end", "text"}
        or receipt.get("command") != command
        or type(receipt.get("rc")) is not int
        or receipt.get("rc") != 0
        or receipt.get("status") != "ok"
        or type(receipt.get("text")) is not str
    ):
        raise ContractError(f"{label} is not an exact successful receipt")
    return receipt


def _validate_resident_pstore_health(value: Any) -> None:
    pstore = _require_dict(value, "resident pstore health")
    try:
        base.validate_pstore_before_handoff_receipt(
            pstore,
            allow_legacy_empty=True,
        )
    except base.ContractError as exc:
        raise ContractError("resident pstore health is not exact") from exc


def _validate_resident_ncm_health(
    value: Any,
    *,
    expected_profile: str,
) -> None:
    ncm = _require_dict(value, "resident NCM health")
    common_keys = {
        "same_current_acm_usb_parent",
        "exact_interface_count",
        "profile_bound",
        "mutated",
        "profile_check",
        "active_before",
        "ready",
    }
    if type(ncm.get("mutated")) is not bool:
        raise ContractError("resident NCM mutation fact is not exact")
    expected_keys = common_keys | (
        {"modify", "activate", "active_after"}
        if ncm["mutated"]
        else set()
    )
    ready = _require_dict(ncm.get("ready"), "resident NCM readiness")
    host_receipt_keys = {"command", "returncode", "stdout", "stderr"}
    profile_check = _require_dict(
        ncm.get("profile_check"),
        "resident NCM profile check",
    )
    active_before = _require_dict(
        ncm.get("active_before"),
        "resident NCM active-before check",
    )
    if (
        set(ncm) != expected_keys
        or ncm.get("same_current_acm_usb_parent") is not True
        or type(ncm.get("exact_interface_count")) is not int
        or ncm.get("exact_interface_count") != 1
        or ncm.get("profile_bound") is not True
        or ready
        != {
            "verified_a90_ncm": True,
            "direct_route": True,
            "host_cidr_present": True,
            "device_ping": True,
        }
        or set(profile_check) != host_receipt_keys
        or type(profile_check.get("returncode")) is not int
        or profile_check.get("returncode") != 0
        or str(profile_check.get("stdout") or "").strip()
        != base.HOST_NCM_CONNECTION_TYPE
        or set(active_before) != host_receipt_keys
    ):
        raise ContractError("resident NCM health is not exact")
    selected = active_before
    if ncm["mutated"]:
        for label in ("modify", "activate"):
            receipt = _require_dict(
                ncm.get(label),
                f"resident NCM {label}",
            )
            if (
                set(receipt) != host_receipt_keys
                or type(receipt.get("returncode")) is not int
                or receipt.get("returncode") != 0
            ):
                raise ContractError(f"resident NCM {label} failed")
        selected = _require_dict(
            ncm.get("active_after"),
            "resident NCM active-after check",
        )
        if set(selected) != host_receipt_keys:
            raise ContractError("resident NCM active-after check is not exact")
    if (
        type(selected.get("returncode")) is not int
        or selected.get("returncode") != 0
        or str(selected.get("stdout") or "").splitlines()[:1]
        != [expected_profile]
    ):
        raise ContractError("resident NCM selected profile is not exact")


def _validate_resident_journal(
    resident_manifest_sha256: str,
    resident_run_id: str,
    journal_dir: Path,
    *,
    expected_version: str,
    expected_build: str,
    expected_bridge_realpath: str,
    expected_ncm_profile: str,
    expected_source_script: str,
) -> tuple[tuple[BoundFile, ...], dict[str, Any]]:
    try:
        paths = tuple(sorted(journal_dir.glob("*.json")))
    except OSError as exc:
        raise ContractError("resident journal directory is unavailable") from exc
    if len(paths) != len(RESIDENT_ACTIONS):
        raise ContractError("resident journal record count is not exact")
    records = tuple(_read_private_json(path) for path in paths)
    if tuple(item.get("action") for item in records) != RESIDENT_ACTIONS:
        raise ContractError("resident journal action sequence is not exact")
    for index, item in enumerate(records):
        if (
            type(item.get("sequence")) is not int
            or item.get("sequence") != index
            or item.get("run_id") != resident_run_id
            or item.get("manifest_sha256") != resident_manifest_sha256
        ):
            raise ContractError("resident journal binding changed")
    terminal = records[-1]
    if (
        terminal.get("state") != "RESIDENT_INSTALLED_CLOSED"
        or terminal.get("status") != "PASS_A90_RESIDENT_INSTALLED"
        or terminal.get("device_safety_state") != "RESIDENT_HEALTHY"
        or type(terminal.get("candidate_transfer_count")) is not int
        or terminal.get("candidate_transfer_count") != 1
        or terminal.get("candidate_replay") is not False
        or type(terminal.get("candidate_health_check_count")) is not int
        or terminal.get("candidate_health_check_count") != 1
        or type(terminal.get("resident_reboot_count")) is not int
        or terminal.get("resident_reboot_count") != 0
        or type(terminal.get("rollback_transfer_count")) is not int
        or terminal.get("rollback_transfer_count") != 0
        or terminal.get("rollback_required") is not False
    ):
        raise ContractError("resident terminal is not exact")
    health_record = records[-2]
    health = _require_dict(health_record.get("health"), "resident health")
    if (
        set(health) != {"native", "pstore", "rootfs", "ncm"}
        or type(health_record.get("candidate_health_check_count")) is not int
        or health_record.get("candidate_health_check_count") != 1
    ):
        raise ContractError("resident health record is not exact")
    native = _require_dict(health.get("native"), "resident native health")
    rootfs = _require_dict(health.get("rootfs"), "resident rootfs health")
    ncm = _require_dict(health.get("ncm"), "resident NCM health")
    pstore = _require_dict(health.get("pstore"), "resident pstore health")
    try:
        native_exact = _validate_resident_native_health(
            native,
            expected_version=expected_version,
            expected_build=expected_build,
            expected_bridge_realpath=expected_bridge_realpath,
        )
        _require_exact_run_shell_receipt(
            rootfs,
            script=expected_source_script,
            marker_pattern=re.compile(
                r"A90F1_SOURCE_PRECHECK exact=1 work_absent=1"
            ),
            label="resident rootfs health",
        )
        _validate_resident_pstore_health(pstore)
        _validate_resident_ncm_health(
            ncm,
            expected_profile=expected_ncm_profile,
        )
    except ContractError as exc:
        raise ContractError("resident health proof is not exact") from exc
    if (
        health_record.get("native_exact") != native_exact
    ):
        raise ContractError("resident health proof is not exact")
    return tuple(_bound_file(path, private=True) for path in paths), terminal


def _crosscheck_resident_manifest(
    resident_manifest: BoundFile,
    resident_run_id: str,
    resident: dict[str, Any],
    candidate: BoundFile,
    rollback: BoundFile,
    rootfs: BoundFile,
    target: dict[str, Any],
    observer: dict[str, Any],
    observer_key: BoundFile,
    handoff: dict[str, Any],
) -> str:
    source = _read_private_json(resident_manifest.path)
    candidate_source = _require_dict(source.get("candidate_boot"), "resident candidate")
    rollback_source = _require_dict(source.get("rollback_boot"), "resident rollback")
    debian_source = _require_dict(source.get("debian_rootfs"), "resident Debian")
    rootfs_source = _require_dict(debian_source.get("keyed_source"), "resident rootfs")
    work_source = _require_dict(debian_source.get("work_copy"), "resident work")
    target_source = _require_dict(source.get("target"), "resident target")
    observer_source = _require_dict(debian_source.get("observer"), "resident observer")
    observation_source = _require_dict(source.get("observation"), "resident observation")
    if (
        source.get("schema") != staging.RESIDENT_INSTALL_MANIFEST_SCHEMA
        or source.get("status") != staging.FINAL_MANIFEST_STATUS
        or source.get("run_id") != resident_run_id
        or candidate_source.get("path") != str(candidate.path)
        or candidate_source.get("size") != candidate.size
        or candidate_source.get("sha256") != candidate.sha256
        or candidate_source.get("partition") != "boot"
        or candidate_source.get("expected_version")
        != resident.get("candidate_version")
        or candidate_source.get("expected_build") != resident.get("candidate_build")
        or rollback_source.get("path") != str(rollback.path)
        or rollback_source.get("size") != rollback.size
        or rollback_source.get("sha256") != rollback.sha256
        or rollback_source.get("partition") != "boot"
        or rootfs_source.get("local_path") != str(rootfs.path)
        or rootfs_source.get("size") != rootfs.size
        or rootfs_source.get("sha256") != rootfs.sha256
        or rootfs_source.get("profile") != phase3_observer.PROFILE
        or rootfs_source.get("device_path") != resident.get("remote_final")
        or work_source.get("device_path") != resident.get("remote_work")
        or debian_source.get("handoff_command") != handoff.get("command")
        or target_source.get("profile") != target.get("profile")
        or target_source.get("bridge_selected_exact") is not True
        or target_source.get("bridge_device") != target.get("bridge_device")
        or target_source.get("bridge_selected_realpath")
        != target.get("bridge_realpath")
        or target_source.get("recovery_adb_serial_sha256")
        != target.get("recovery_serial_sha256")
        or target_source.get("recovery") != target.get("recovery_profile")
        or observer_source.get("private_key_path") != str(observer_key.path)
        or observer_source.get("public_key_sha256")
        != observer.get("public_key_sha256")
        or observer_source.get("device_ip") != observer.get("device")
        or observer_source.get("device_port") != observer.get("port")
        or observer_source.get("host_ncm_profile")
        != observer.get("host_ncm_profile")
        or observer_source.get("transport_scope")
        != base.OBSERVER_TRANSPORT_SCOPE
        or observer_source.get("wifi_or_external_network") is not False
        or observation_source.get("handoff_attempt_limit") != 1
        or observation_source.get("handoff_timeout_sec")
        != handoff.get("handoff_timeout_sec")
        or observation_source.get("ssh_marker_timeout_sec")
        != handoff.get("ssh_marker_timeout_sec")
        or observation_source.get("candidate_return_timeout_sec")
        != handoff.get("candidate_return_timeout_sec")
    ):
        raise ContractError("D1 manifest reinterprets resident evidence")
    return phase3_observer.PROFILE


def _build_manifest_from_preserved_baseline(
    *,
    baseline: preserved_prep.BaselineSpec,
    run_id: str,
    session_duration_sec: int,
    max_actions: int,
) -> dict[str, Any]:
    """Map one reviewed immutable preserved baseline into the D1 schema."""

    resident_manifest = BoundFile(
        baseline.manifest.path,
        baseline.manifest.size,
        baseline.manifest.sha256,
    )
    candidate = BoundFile(
        baseline.candidate.path,
        baseline.candidate.size,
        baseline.candidate.sha256,
    )
    rollback = BoundFile(
        baseline.rollback.path,
        baseline.rollback.size,
        baseline.rollback.sha256,
    )
    rootfs = BoundFile(
        baseline.rootfs.path,
        baseline.rootfs.size,
        baseline.rootfs.sha256,
    )
    observer_key = BoundFile(
        baseline.observer_key.path,
        baseline.observer_key.size,
        baseline.observer_key.sha256,
    )
    journal = tuple(
        BoundFile(item.path, item.size, item.sha256)
        for item in baseline.resident_journal
    )
    source_closure = {
        role: _bound_file(path, private=False)
        for role, path in SOURCE_PATHS.items()
    }
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "created_utc": utc_now(),
        "run_id": run_id,
        "resident": {
            "evidence_kind": "preserved-install-cleanup-reduced-v1",
            "run_id": baseline.resident_run_id,
            "manifest": _as_dict(resident_manifest),
            "journal": [_as_dict(item) for item in journal],
            "terminal_journal_sha256": journal[-1].sha256,
            "terminal_status": preserved_prep.preserved.SUCCESS_STATUS,
            "candidate": _as_dict(candidate),
            "candidate_version": baseline.candidate_version,
            "candidate_build": baseline.candidate_build,
            "rollback": _as_dict(rollback),
            "rootfs": _as_dict(rootfs),
            "remote_final": baseline.remote_final,
            "remote_work": baseline.remote_work,
        },
        "target": {
            "profile": staging.TARGET_PROFILE,
            "bridge_device": baseline.bridge_device,
            "bridge_realpath": baseline.bridge_realpath,
            "recovery_serial_sha256": baseline.recovery_serial_sha256,
            "recovery_profile": baseline.recovery_profile,
        },
        "observer": {
            "key": _as_dict(observer_key),
            "public_key_sha256": baseline.observer_public_key_sha256,
            "device": baseline.observer_device,
            "port": baseline.observer_port,
            "host_ncm_profile": baseline.observer_host_ncm_profile,
        },
        "handoff": {
            "command": list(baseline.handoff_command),
            "handoff_timeout_sec": baseline.handoff_timeout,
            "ssh_marker_timeout_sec": baseline.ssh_marker_timeout,
            "candidate_return_timeout_sec": baseline.candidate_return_timeout,
        },
        "session": {
            "workflow": Workflow.ATTENDED_SESSION_D1.value,
            "risk_tier": RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL.value,
            "action_allowlist": [SessionAction.SWITCHROOT_EXPERIMENT.value],
            "session_duration_sec": session_duration_sec,
            "max_actions": max_actions,
            "operator_attended_each_action": True,
            "transaction_dir": str(PRIVATE_RUN_BASE / run_id / SESSION_DIR_NAME),
            "session_lock_path": str(PRIVATE_RUN_BASE / run_id / SESSION_LOCK_NAME),
        },
        "source_closure": {
            role: _as_dict(item) for role, item in source_closure.items()
        },
        "safety": {
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
            "candidate_replay": False,
            "fixed_work_path": WORK_PATH,
            "work_cleanup_requires_regular_mode_size": True,
            "other_targets_untouched": True,
        },
        "authority": {
            "live_authority": False,
            "manifest_grants_live_authority": False,
            "fresh_exact_session_approval_required": True,
            "one_approval_may_cover_bounded_actions": True,
        },
    }


def _crosscheck_preserved_baseline(
    resident_manifest: BoundFile,
    resident: dict[str, Any],
    candidate: BoundFile,
    rollback: BoundFile,
    rootfs: BoundFile,
    target: dict[str, Any],
    observer: dict[str, Any],
    observer_key: BoundFile,
    handoff: dict[str, Any],
) -> tuple[str, tuple[BoundFile, ...], str]:
    try:
        baseline = preserved_prep.load_baseline(
            resident_manifest.path,
            resident_manifest.sha256,
        )
    except preserved_prep.ContractError as exc:
        raise ContractError("preserved D1 baseline is not exact") from exc
    journal = tuple(
        BoundFile(item.path, item.size, item.sha256)
        for item in baseline.resident_journal
    )
    if (
        resident.get("run_id") != baseline.resident_run_id
        or candidate
        != BoundFile(
            baseline.candidate.path,
            baseline.candidate.size,
            baseline.candidate.sha256,
        )
        or rollback
        != BoundFile(
            baseline.rollback.path,
            baseline.rollback.size,
            baseline.rollback.sha256,
        )
        or rootfs
        != BoundFile(
            baseline.rootfs.path,
            baseline.rootfs.size,
            baseline.rootfs.sha256,
        )
        or resident.get("candidate_version") != baseline.candidate_version
        or resident.get("candidate_build") != baseline.candidate_build
        or resident.get("remote_final") != baseline.remote_final
        or resident.get("remote_work") != baseline.remote_work
        or target
        != {
            "profile": staging.TARGET_PROFILE,
            "bridge_device": baseline.bridge_device,
            "bridge_realpath": baseline.bridge_realpath,
            "recovery_serial_sha256": baseline.recovery_serial_sha256,
            "recovery_profile": baseline.recovery_profile,
        }
        or observer_key
        != BoundFile(
            baseline.observer_key.path,
            baseline.observer_key.size,
            baseline.observer_key.sha256,
        )
        or observer
        != {
            "key": _as_dict(observer_key),
            "public_key_sha256": baseline.observer_public_key_sha256,
            "device": baseline.observer_device,
            "port": baseline.observer_port,
            "host_ncm_profile": baseline.observer_host_ncm_profile,
        }
        or handoff
        != {
            "command": list(baseline.handoff_command),
            "handoff_timeout_sec": baseline.handoff_timeout,
            "ssh_marker_timeout_sec": baseline.ssh_marker_timeout,
            "candidate_return_timeout_sec": baseline.candidate_return_timeout,
        }
    ):
        raise ContractError("D1 manifest reinterprets preserved baseline")
    return phase3_observer.PROFILE, journal, preserved_prep.preserved.SUCCESS_STATUS


def build_manifest(
    *,
    resident_manifest_path: Path,
    resident_manifest_sha256: str,
    run_id: str,
    session_duration_sec: int,
    max_actions: int,
) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise ContractError("D1 run_id is not exact")
    if (
        type(session_duration_sec) is not int
        or not 1 <= session_duration_sec <= MAX_DURATION_SEC
        or type(max_actions) is not int
        or not 1 <= max_actions <= MAX_ACTIONS
    ):
        raise ContractError("D1 session window or action budget is invalid")
    resident_manifest = _bound_file(resident_manifest_path, private=True)
    if resident_manifest.sha256 != _require_sha(
        resident_manifest_sha256,
        "resident manifest SHA256",
    ):
        raise ContractError("resident manifest SHA256 mismatch")
    value = _read_private_json(resident_manifest.path)
    if value.get("schema") == preserved_prep.BASELINE_SCHEMA:
        try:
            baseline = preserved_prep.load_baseline(
                resident_manifest.path,
                resident_manifest.sha256,
            )
        except preserved_prep.ContractError as exc:
            raise ContractError("preserved D1 baseline is not exact") from exc
        return _build_manifest_from_preserved_baseline(
            baseline=baseline,
            run_id=run_id,
            session_duration_sec=session_duration_sec,
            max_actions=max_actions,
        )
    resident_run_id = _require_string(value.get("run_id"), "resident run_id")
    if (
        value.get("schema") != staging.RESIDENT_INSTALL_MANIFEST_SCHEMA
        or value.get("status") != staging.FINAL_MANIFEST_STATUS
        or RESIDENT_RUN_RE.fullmatch(resident_run_id) is None
    ):
        raise ContractError("resident manifest is not the exact install schema")
    candidate_item = _require_dict(value.get("candidate_boot"), "candidate boot")
    rollback_item = _require_dict(value.get("rollback_boot"), "rollback boot")
    candidate = _bound_file(
        Path(_require_string(candidate_item.get("path"), "candidate boot path")),
        private=True,
    )
    rollback = _bound_file(
        Path(_require_string(rollback_item.get("path"), "rollback boot path")),
        private=True,
    )
    if (
        candidate.size != candidate_item.get("size")
        or candidate.sha256 != candidate_item.get("sha256")
        or rollback.size != rollback_item.get("size")
        or rollback.sha256 != rollback_item.get("sha256")
    ):
        raise ContractError("resident boot artifact identity changed")
    if candidate_item.get("partition") != "boot" or rollback_item.get("partition") != "boot":
        raise ContractError("D1 resident and rollback artifacts are not boot-only")
    debian = _require_dict(value.get("debian_rootfs"), "debian rootfs")
    keyed = _require_dict(debian.get("keyed_source"), "keyed rootfs")
    rootfs = _bound_file(Path(_require_string(keyed.get("local_path"), "rootfs path")), private=True)
    if (
        rootfs.size != keyed.get("size")
        or rootfs.sha256 != keyed.get("sha256")
        or keyed.get("profile") != phase3_observer.PROFILE
        or keyed.get("device_path") is None
        or _require_dict(debian.get("work_copy"), "work copy").get("device_path")
        != WORK_PATH
    ):
        raise ContractError("resident rootfs identity changed")
    target = _require_dict(value.get("target"), "target")
    observer = _require_dict(debian.get("observer"), "observer")
    observer_key = _bound_file(
        Path(_require_string(observer.get("private_key_path"), "observer key")),
        private=True,
    )
    observation = _require_dict(value.get("observation"), "observation")
    if (
        target.get("profile") != staging.TARGET_PROFILE
        or target.get("bridge_selected_exact") is not True
        or debian.get("handoff_command")
        != [
            base.HANDOFF_COMMAND,
            base.HANDOFF_TOKEN,
            keyed.get("device_path"),
            keyed.get("sha256"),
        ]
        or observation.get("handoff_attempt_limit") != 1
        or observer.get("transport_scope") != base.OBSERVER_TRANSPORT_SCOPE
        or observer.get("wifi_or_external_network") is not False
    ):
        raise ContractError("resident target or observation contract changed")
    source_stage = argparse.Namespace(
        remote_final=_require_string(
            keyed.get("device_path"),
            "resident rootfs device path",
        ),
        remote_work=WORK_PATH,
        local_size=rootfs.size,
        local_sha256=rootfs.sha256,
    )
    journal, terminal = _validate_resident_journal(
        resident_manifest.sha256,
        resident_run_id,
        resident_manifest.path.parent / "f1-live" / "journal",
        expected_version=_require_string(
            candidate_item.get("expected_version"),
            "candidate version",
        ),
        expected_build=_require_string(
            candidate_item.get("expected_build"),
            "candidate build",
        ),
        expected_bridge_realpath=_require_string(
            target.get("bridge_selected_realpath"),
            "resident bridge realpath",
        ),
        expected_ncm_profile=_require_string(
            observer.get("host_ncm_profile"),
            "resident NCM profile",
        ),
        expected_source_script=base.remote_source_preflight_script(
            argparse.Namespace(stage=source_stage)
        ),
    )
    source_closure = {
        role: _bound_file(path, private=False)
        for role, path in SOURCE_PATHS.items()
    }
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "created_utc": utc_now(),
        "run_id": run_id,
        "resident": {
            "evidence_kind": "ordinary-resident-install-v2",
            "run_id": resident_run_id,
            "manifest": _as_dict(resident_manifest),
            "journal": [_as_dict(item) for item in journal],
            "terminal_journal_sha256": journal[-1].sha256,
            "terminal_status": terminal["status"],
            "candidate": _as_dict(candidate),
            "candidate_version": candidate_item["expected_version"],
            "candidate_build": candidate_item["expected_build"],
            "rollback": _as_dict(rollback),
            "rootfs": _as_dict(rootfs),
            "remote_final": keyed["device_path"],
            "remote_work": WORK_PATH,
        },
        "target": {
            "profile": target["profile"],
            "bridge_device": target["bridge_device"],
            "bridge_realpath": target["bridge_selected_realpath"],
            "recovery_serial_sha256": target["recovery_adb_serial_sha256"],
            "recovery_profile": target["recovery"],
        },
        "observer": {
            "key": _as_dict(observer_key),
            "public_key_sha256": observer["public_key_sha256"],
            "device": observer["device_ip"],
            "port": observer["device_port"],
            "host_ncm_profile": observer["host_ncm_profile"],
        },
        "handoff": {
            "command": debian["handoff_command"],
            "handoff_timeout_sec": observation["handoff_timeout_sec"],
            "ssh_marker_timeout_sec": observation["ssh_marker_timeout_sec"],
            "candidate_return_timeout_sec": observation[
                "candidate_return_timeout_sec"
            ],
        },
        "session": {
            "workflow": Workflow.ATTENDED_SESSION_D1.value,
            "risk_tier": RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL.value,
            "action_allowlist": [SessionAction.SWITCHROOT_EXPERIMENT.value],
            "session_duration_sec": session_duration_sec,
            "max_actions": max_actions,
            "operator_attended_each_action": True,
            "transaction_dir": str(
                PRIVATE_RUN_BASE / run_id / SESSION_DIR_NAME
            ),
            "session_lock_path": str(
                PRIVATE_RUN_BASE / run_id / SESSION_LOCK_NAME
            ),
        },
        "source_closure": {
            role: _as_dict(item) for role, item in source_closure.items()
        },
        "safety": {
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
            "candidate_replay": False,
            "fixed_work_path": WORK_PATH,
            "work_cleanup_requires_regular_mode_size": True,
            "other_targets_untouched": True,
        },
        "authority": {
            "live_authority": False,
            "manifest_grants_live_authority": False,
            "fresh_exact_session_approval_required": True,
            "one_approval_may_cover_bounded_actions": True,
        },
    }


def load_spec(path: Path, expected_sha256: str) -> SessionSpec:
    manifest = _bound_file(path, private=True)
    if manifest.sha256 != _require_sha(expected_sha256, "manifest SHA256"):
        raise ContractError("D1 manifest SHA256 mismatch")
    value = _read_private_json(manifest.path)
    if (
        set(value)
        != {
            "schema",
            "status",
            "created_utc",
            "run_id",
            "resident",
            "target",
            "observer",
            "handoff",
            "session",
            "source_closure",
            "safety",
            "authority",
        }
        or value.get("schema") != SCHEMA
        or value.get("status") != STATUS
    ):
        raise ContractError("D1 manifest schema or status changed")
    run_id = _require_string(value.get("run_id"), "run_id")
    if RUN_ID_RE.fullmatch(run_id) is None or manifest.path.parent != PRIVATE_RUN_BASE / run_id:
        raise ContractError("D1 manifest path and run_id differ")
    resident = _require_dict(value.get("resident"), "resident")
    evidence_kind = _require_string(
        resident.get("evidence_kind"),
        "resident evidence kind",
    )
    if evidence_kind not in {
        "ordinary-resident-install-v2",
        "preserved-install-cleanup-reduced-v1",
    }:
        raise ContractError("resident evidence kind is not allowlisted")
    resident_run_id = _require_string(resident.get("run_id"), "resident run_id")
    resident_manifest = _bound_dict(resident.get("manifest"), "resident manifest", private=True)
    journal_values = resident.get("journal")
    expected_journal_count = (
        len(RESIDENT_ACTIONS)
        if evidence_kind == "ordinary-resident-install-v2"
        else len(preserved_prep.preserved.INSTALL_SUCCESS_ACTIONS)
    )
    if not isinstance(journal_values, list) or len(journal_values) != expected_journal_count:
        raise ContractError("resident journal binding is not exact")
    resident_journal = tuple(
        _bound_dict(item, f"resident journal {index}", private=True)
        for index, item in enumerate(journal_values)
    )
    source_values = _require_dict(value.get("source_closure"), "source closure")
    if set(source_values) != set(SOURCE_PATHS):
        raise ContractError("D1 source closure role set changed")
    source_closure: dict[str, BoundFile] = {}
    for role, expected_path in SOURCE_PATHS.items():
        item = _bound_dict(source_values.get(role), role, private=False)
        if item.path != expected_path.resolve(strict=True):
            raise ContractError(f"D1 source role path changed: {role}")
        source_closure[role] = item
    candidate = _bound_dict(resident.get("candidate"), "candidate", private=True)
    rollback = _bound_dict(resident.get("rollback"), "rollback", private=True)
    rootfs = _bound_dict(resident.get("rootfs"), "rootfs", private=True)
    target = _require_dict(value.get("target"), "target")
    observer = _require_dict(value.get("observer"), "observer")
    handoff = _require_dict(value.get("handoff"), "handoff")
    session = _require_dict(value.get("session"), "session")
    safety = _require_dict(value.get("safety"), "safety")
    authority = _require_dict(value.get("authority"), "authority")
    source_stage = argparse.Namespace(
        remote_final=_require_string(
            resident.get("remote_final"),
            "resident rootfs device path",
        ),
        remote_work=_require_string(
            resident.get("remote_work"),
            "resident rootfs work path",
        ),
        local_size=rootfs.size,
        local_sha256=rootfs.sha256,
    )
    if evidence_kind == "ordinary-resident-install-v2":
        canonical_resident_journal, terminal = _validate_resident_journal(
            resident_manifest.sha256,
            resident_run_id,
            resident_manifest.path.parent / "f1-live" / "journal",
            expected_version=_require_string(
                resident.get("candidate_version"),
                "candidate version",
            ),
            expected_build=_require_string(
                resident.get("candidate_build"),
                "candidate build",
            ),
            expected_bridge_realpath=_require_string(
                target.get("bridge_realpath"),
                "resident bridge realpath",
            ),
            expected_ncm_profile=_require_string(
                observer.get("host_ncm_profile"),
                "resident NCM profile",
            ),
            expected_source_script=base.remote_source_preflight_script(
                argparse.Namespace(stage=source_stage)
            ),
        )
    else:
        (
            _baseline_profile,
            canonical_resident_journal,
            baseline_terminal_status,
        ) = _crosscheck_preserved_baseline(
            resident_manifest,
            resident,
            candidate,
            rollback,
            rootfs,
            target,
            observer,
            _bound_dict(observer.get("key"), "observer key", private=True),
            handoff,
        )
        terminal = {"status": baseline_terminal_status}
    if resident_journal != canonical_resident_journal:
        raise ContractError("resident journal path is not canonical")
    resident_journal = canonical_resident_journal
    if (
        resident.get("terminal_journal_sha256") != resident_journal[-1].sha256
        or resident.get("terminal_status") != terminal.get("status")
    ):
        raise ContractError("resident terminal binding changed")
    observer_port = observer.get("port")
    handoff_timeout = handoff.get("handoff_timeout_sec")
    ssh_marker_timeout = handoff.get("ssh_marker_timeout_sec")
    candidate_return_timeout = handoff.get("candidate_return_timeout_sec")
    if (
        set(resident)
        != {
            "evidence_kind",
            "run_id",
            "manifest",
            "journal",
            "terminal_journal_sha256",
            "terminal_status",
            "candidate",
            "candidate_version",
            "candidate_build",
            "rollback",
            "rootfs",
            "remote_final",
            "remote_work",
        }
        or set(target)
        != {
            "profile",
            "bridge_device",
            "bridge_realpath",
            "recovery_serial_sha256",
            "recovery_profile",
        }
        or set(observer)
        != {"key", "public_key_sha256", "device", "port", "host_ncm_profile"}
        or set(handoff)
        != {
            "command",
            "handoff_timeout_sec",
            "ssh_marker_timeout_sec",
            "candidate_return_timeout_sec",
        }
        or set(session)
        != {
            "workflow",
            "risk_tier",
            "action_allowlist",
            "session_duration_sec",
            "max_actions",
            "operator_attended_each_action",
            "transaction_dir",
            "session_lock_path",
        }
        or session.get("workflow") != Workflow.ATTENDED_SESSION_D1.value
        or session.get("risk_tier")
        != RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL.value
        or session.get("action_allowlist")
        != [SessionAction.SWITCHROOT_EXPERIMENT.value]
        or session.get("operator_attended_each_action") is not True
        or safety
        != {
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
            "candidate_replay": False,
            "fixed_work_path": WORK_PATH,
            "work_cleanup_requires_regular_mode_size": True,
            "other_targets_untouched": True,
        }
        or authority
        != {
            "live_authority": False,
            "manifest_grants_live_authority": False,
            "fresh_exact_session_approval_required": True,
            "one_approval_may_cover_bounded_actions": True,
        }
        or target.get("profile") != staging.TARGET_PROFILE
        or resident.get("remote_work") != WORK_PATH
        or handoff.get("command")
        != [
            base.HANDOFF_COMMAND,
            base.HANDOFF_TOKEN,
            resident.get("remote_final"),
            rootfs.sha256,
        ]
        or type(observer_port) is not int
        or not 1 <= observer_port <= 65535
        or any(
            type(item) is not int or item <= 0
            for item in (
                handoff_timeout,
                ssh_marker_timeout,
                candidate_return_timeout,
            )
        )
    ):
        raise ContractError("D1 safety or authority contract changed")
    duration = session.get("session_duration_sec")
    max_actions = session.get("max_actions")
    transaction_dir = Path(
        _require_string(session.get("transaction_dir"), "transaction dir")
    )
    session_lock_path = Path(
        _require_string(session.get("session_lock_path"), "session lock path")
    )
    if (
        transaction_dir != manifest.path.parent / SESSION_DIR_NAME
        or session_lock_path != manifest.path.parent / SESSION_LOCK_NAME
    ):
        raise ContractError("D1 session paths are not manifest-bound")
    binding = AttendedSessionBinding(
        approval_id=run_id,
        workflow=Workflow.ATTENDED_SESSION_D1,
        risk_tier=RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL,
        target_profile=_require_string(target.get("profile"), "target profile"),
        manifest_sha256=manifest.sha256,
        resident_boot_sha256=candidate.sha256,
        rollback_boot_sha256=rollback.sha256,
        recovery_profile="A90_ATTENDED_PHYSICAL_RECOVERY_V1",
        device_effect_runner_sha256=source_closure["runner"].sha256,
        observer_sha256=source_closure["observation_pipeline"].sha256,
        return_health_profile="A90_V3406_RESIDENT_HEALTH_V1",
        action_allowlist=(SessionAction.SWITCHROOT_EXPERIMENT,),
        not_before_epoch_sec=0,
        expires_at_epoch_sec=duration,
        max_actions=max_actions,
    )
    binding.validate()
    observer_key = _bound_dict(observer.get("key"), "observer key", private=True)
    if evidence_kind == "ordinary-resident-install-v2":
        rootfs_profile = _crosscheck_resident_manifest(
            resident_manifest,
            resident_run_id,
            resident,
            candidate,
            rollback,
            rootfs,
            target,
            observer,
            observer_key,
            handoff,
        )
    else:
        rootfs_profile, baseline_journal, baseline_status = _crosscheck_preserved_baseline(
            resident_manifest,
            resident,
            candidate,
            rollback,
            rootfs,
            target,
            observer,
            observer_key,
            handoff,
        )
        if (
            resident_journal != baseline_journal
            or resident.get("terminal_status") != baseline_status
        ):
            raise ContractError("preserved baseline journal binding changed")
    return SessionSpec(
        manifest_path=manifest.path,
        manifest_sha256=manifest.sha256,
        run_id=run_id,
        resident_run_id=resident_run_id,
        resident_manifest=resident_manifest,
        resident_journal=resident_journal,
        candidate=candidate,
        rollback=rollback,
        rootfs=rootfs,
        rootfs_profile=rootfs_profile,
        candidate_version=_require_string(resident.get("candidate_version"), "candidate version"),
        candidate_build=_require_string(resident.get("candidate_build"), "candidate build"),
        remote_final=_require_string(resident.get("remote_final"), "remote final"),
        remote_work=_require_string(resident.get("remote_work"), "remote work"),
        bridge_device=_require_string(target.get("bridge_device"), "bridge device"),
        bridge_realpath=_require_string(target.get("bridge_realpath"), "bridge realpath"),
        recovery_serial_sha256=_require_sha(
            target.get("recovery_serial_sha256"),
            "recovery serial SHA256",
        ),
        observer_key=observer_key.path,
        observer_public_key_sha256=_require_sha(observer.get("public_key_sha256"), "observer public key SHA256"),
        observer_device=_require_string(observer.get("device"), "observer device"),
        observer_port=observer_port,
        observer_host_ncm_profile=_require_string(observer.get("host_ncm_profile"), "NCM profile"),
        handoff_command=tuple(handoff.get("command") or ()),
        handoff_timeout=handoff_timeout,
        ssh_marker_timeout=ssh_marker_timeout,
        candidate_return_timeout=candidate_return_timeout,
        source_closure=source_closure,
        transaction_dir=transaction_dir,
        session_lock_path=session_lock_path,
        session_duration_sec=duration,
        max_actions=max_actions,
        recovery_profile=_require_string(target.get("recovery_profile"), "recovery profile"),
        resident_evidence_kind=evidence_kind,
    )


def approval_binding(spec: SessionSpec) -> dict[str, Any]:
    return {
        "run_id": spec.run_id,
        "workflow": Workflow.ATTENDED_SESSION_D1.value,
        "risk_tier": RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL.value,
        "manifest_sha256": spec.manifest_sha256,
        "resident_boot_sha256": spec.candidate.sha256,
        "rollback_boot_sha256": spec.rollback.sha256,
        "rootfs_sha256": spec.rootfs.sha256,
        "resident_terminal_journal_sha256": spec.resident_journal[-1].sha256,
        "device_effect_runner_sha256": spec.source_closure["runner"].sha256,
        "observer_sha256": spec.source_closure["observation_pipeline"].sha256,
        "action_allowlist": [SessionAction.SWITCHROOT_EXPERIMENT.value],
        "session_duration_sec": spec.session_duration_sec,
        "max_actions": spec.max_actions,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
    }


def approval_path(spec: SessionSpec) -> Path:
    return spec.manifest_path.parent / "approval-prepared.json"


def prepare_approval(spec: SessionSpec) -> dict[str, Any]:
    binding = approval_binding(spec)
    digest = json_sha256(binding)
    value = {
        "schema": APPROVAL_SCHEMA,
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "approval_binding": binding,
        "approval_binding_sha256": digest,
        "approval_token": APPROVAL_PREFIX + digest,
        "device_contact": False,
        "device_write": False,
        "live_authority": False,
    }
    write_private_json_exclusive(approval_path(spec), value)
    return value


def require_approval(spec: SessionSpec, supplied: str) -> dict[str, Any]:
    value = _read_private_json(approval_path(spec))
    binding = approval_binding(spec)
    digest = json_sha256(binding)
    if (
        value.get("schema") != APPROVAL_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("approval_binding") != binding
        or value.get("approval_binding_sha256") != digest
        or value.get("approval_token") != APPROVAL_PREFIX + digest
        or supplied != APPROVAL_PREFIX + digest
        or value.get("device_contact") is not False
        or value.get("device_write") is not False
    ):
        raise ContractError("fresh exact D1 session approval mismatch")
    return value


def _binding(
    spec: SessionSpec,
    opened_at_epoch_sec: int,
) -> AttendedSessionBinding:
    if type(opened_at_epoch_sec) is not int or opened_at_epoch_sec < 0:
        raise ContractError("D1 session opening time is not exact")
    value = AttendedSessionBinding(
        approval_id=spec.run_id,
        workflow=Workflow.ATTENDED_SESSION_D1,
        risk_tier=RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL,
        target_profile=staging.TARGET_PROFILE,
        manifest_sha256=spec.manifest_sha256,
        resident_boot_sha256=spec.candidate.sha256,
        rollback_boot_sha256=spec.rollback.sha256,
        recovery_profile="A90_ATTENDED_PHYSICAL_RECOVERY_V1",
        device_effect_runner_sha256=spec.source_closure["runner"].sha256,
        observer_sha256=spec.source_closure["observation_pipeline"].sha256,
        return_health_profile="A90_V3406_RESIDENT_HEALTH_V1",
        action_allowlist=(SessionAction.SWITCHROOT_EXPERIMENT,),
        not_before_epoch_sec=opened_at_epoch_sec,
        expires_at_epoch_sec=opened_at_epoch_sec + spec.session_duration_sec,
        max_actions=spec.max_actions,
    )
    value.validate()
    return value


def _binding_value(binding: AttendedSessionBinding) -> dict[str, Any]:
    binding.validate()
    return {
        "approval_id": binding.approval_id,
        "workflow": binding.workflow.value,
        "risk_tier": binding.risk_tier.value,
        "target_profile": binding.target_profile,
        "manifest_sha256": binding.manifest_sha256,
        "resident_boot_sha256": binding.resident_boot_sha256,
        "rollback_boot_sha256": binding.rollback_boot_sha256,
        "recovery_profile": binding.recovery_profile,
        "device_effect_runner_sha256": binding.device_effect_runner_sha256,
        "observer_sha256": binding.observer_sha256,
        "return_health_profile": binding.return_health_profile,
        "action_allowlist": [item.value for item in binding.action_allowlist],
        "not_before_epoch_sec": binding.not_before_epoch_sec,
        "expires_at_epoch_sec": binding.expires_at_epoch_sec,
        "max_actions": binding.max_actions,
    }


def _f1_spec(spec: SessionSpec) -> base.F1Spec:
    if spec.rootfs_profile != phase3_observer.PROFILE:
        raise ContractError("D1 rootfs profile is not exact Phase 3")
    adapter = spec.source_closure["staging_contract"]
    transport = spec.source_closure["framed_transport"]
    stage = staging.StageSpec(
        run_id=spec.run_id,
        manifest_path=spec.manifest_path,
        manifest_sha256=spec.manifest_sha256,
        local_image=spec.rootfs.path,
        local_size=spec.rootfs.size,
        local_sha256=spec.rootfs.sha256,
        remote_final=spec.remote_final,
        remote_work=spec.remote_work,
        remote_stage_dir=f"/mnt/sdext/a90/runtime/.a90-d1-stage-{spec.run_id}",
        remote_payload=f"/mnt/sdext/a90/runtime/.a90-d1-stage-{spec.run_id}/payload.img",
        bridge_device=spec.bridge_device,
        bridge_realpath=spec.bridge_realpath,
        observer_device=spec.observer_device,
        adapter_size=adapter.size,
        adapter_sha256=adapter.sha256,
        tcpctl_host=transport.path,
        tcpctl_host_size=transport.size,
        tcpctl_host_sha256=transport.sha256,
        bound_files=(),
    )
    candidate = staging.BoundFile("resident candidate", spec.candidate.path, spec.candidate.size, spec.candidate.sha256)
    rollback = staging.BoundFile("exact rollback", spec.rollback.path, spec.rollback.size, spec.rollback.sha256)
    orchestrator = spec.source_closure["f1_orchestrator"]
    return base.F1Spec(
        stage=stage,
        manifest={},
        candidate=candidate,
        rollback=rollback,
        flash_runner=candidate,
        candidate_version=spec.candidate_version,
        candidate_build=spec.candidate_build,
        rollback_version="0.9.285",
        rollback_build="v2321-usb-clean-identity-rodata",
        handoff_command=spec.handoff_command,
        observer_key=spec.observer_key,
        observer_public_key_sha256=spec.observer_public_key_sha256,
        observer_device=spec.observer_device,
        observer_port=spec.observer_port,
        observer_host_ncm_profile=spec.observer_host_ncm_profile,
        candidate_boot_timeout=180,
        handoff_timeout=spec.handoff_timeout,
        ssh_marker_timeout=spec.ssh_marker_timeout,
        candidate_return_timeout=spec.candidate_return_timeout,
        rollback_boot_timeout=180,
        observation_mode=base.ATTENDED_OBSERVATION_MODE,
        attended_window_sec=base.ATTENDED_WINDOW_SEC,
        pre_handoff_attempt_limit=1,
        handoff_attempt_limit=1,
        display_required=True,
        display_profile=base.PHASE2_DISPLAY_PROFILE,
        display_uid=base.PHASE2_DISPLAY_UID,
        display_gid=base.PHASE2_DISPLAY_GID,
        display_max_attempts=base.PHASE2_DISPLAY_MAX_ATTEMPTS,
        display_visible_text=base.PHASE2_DISPLAY_VISIBLE_TEXT,
        recovery_serial_sha256=spec.recovery_serial_sha256,
        recovery_serial="D1_NOT_USED",
        recovery_evidence=(),
        orchestrator_size=orchestrator.size,
        orchestrator_sha256=orchestrator.sha256,
    )


def _effect_args() -> argparse.Namespace:
    return argparse.Namespace(
        bridge_host=BRIDGE_HOST,
        bridge_port=BRIDGE_PORT,
        remote_timeout=REMOTE_TIMEOUT_SEC,
        bridge_timeout=BRIDGE_TIMEOUT_SEC,
        flash_command_timeout=FLASH_TIMEOUT_FOR_GUARD_BUDGET_SEC,
        ssh_connect_timeout=SSH_CONNECT_TIMEOUT_SEC,
        poll_interval=POLL_INTERVAL_SEC,
    )


def _require_exact_run_shell_receipt(
    value: Any,
    *,
    script: str,
    marker_pattern: re.Pattern[str],
    label: str,
) -> dict[str, Any]:
    receipt = _require_dict(value, label)
    marker_lines = (
        [
            line
            for line in receipt["text"].splitlines()
            if marker_pattern.fullmatch(line) is not None
        ]
        if type(receipt.get("text")) is str
        else []
    )
    if (
        set(receipt)
        != {"command", "rc", "status", "trust", "begin", "end", "text"}
        or receipt.get("command")
        != ["run", "/bin/busybox", "sh", "-c", script]
        or type(receipt.get("rc")) is not int
        or receipt.get("rc") != 0
        or receipt.get("status") != "ok"
        or type(receipt.get("text")) is not str
        or len(marker_lines) != 1
    ):
        raise ContractError(f"{label} is not an exact successful receipt")
    return receipt


def require_exact_source_preflight_receipt(
    f1_spec: base.F1Spec,
    value: Any,
) -> dict[str, Any]:
    return _require_exact_run_shell_receipt(
        value,
        script=base.remote_source_preflight_script(f1_spec),
        marker_pattern=re.compile(
            r"A90F1_SOURCE_PRECHECK exact=1 work_absent=1"
        ),
        label="D1 source preflight",
    )


def require_exact_cleanup_receipt(
    spec: SessionSpec,
    value: Any,
) -> dict[str, Any]:
    return _require_exact_run_shell_receipt(
        value,
        script=_cleanup_script(spec),
        marker_pattern=re.compile(
            r"A90D1_WORK_CLEANUP exact=1 work_absent=1 "
            r"disposition=(?:removed|already-absent)"
        ),
        label="D1 work cleanup",
    )


def verify_resident_health_exact(
    spec: SessionSpec,
    f1_spec: base.F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Require one exact framed resident identity, selftest, and pstore set."""

    expected_identity = (
        (
            preserved_prep.EXPECTED_VERSION,
            preserved_prep.EXPECTED_BUILD,
        )
        if spec.resident_evidence_kind == "preserved-install-cleanup-reduced-v1"
        else (
            staging.EXPECTED_RESIDENT_VERSION,
            staging.EXPECTED_RESIDENT_BUILD,
        )
    )
    if (spec.candidate_version, spec.candidate_build) != expected_identity:
        raise ContractError("D1 resident identity is not the exact V3406 baseline")
    bridge = staging.require_exact_bridge(f1_spec.stage, args)
    if spec.resident_evidence_kind == "preserved-install-cleanup-reduced-v1":
        receipts = {
            "version": base.run_f1_cmd(args, ["version"]),
            "status": base.run_f1_cmd(args, ["status"]),
            "selftest": base.run_f1_cmd(args, ["selftest"]),
        }
    else:
        receipts = staging.require_native_health(
            args,
            expected_version=spec.candidate_version,
            expected_build=spec.candidate_build,
            input_mode=base.F1_SERIAL_INPUT_MODE,
            input_char_delay_sec=base.F1_SERIAL_INPUT_CHAR_DELAY_SEC,
        )
    try:
        facts = staging.validate_native_health_receipts(
            receipts,
            expected_version=spec.candidate_version,
            expected_build=spec.candidate_build,
        )
    except staging.ContractError as exc:
        raise ContractError("D1 resident health framing is not exact") from exc
    if bridge.get("selected_realpath") != spec.bridge_realpath:
        raise ContractError("D1 resident health bridge changed")
    return {
        "exact_bridge": True,
        "selected_realpath": spec.bridge_realpath,
        "version": receipts["version"],
        "status": receipts["status"],
        "selftest": receipts["selftest"],
        "facts": facts,
    }


def _cleanup_script(spec: SessionSpec) -> str:
    final = staging.shlex.quote(spec.remote_final)
    work = staging.shlex.quote(spec.remote_work)
    return "\n".join(
        (
            "set -eu",
            f"FINAL={final}",
            f"WORK={work}",
            f"EXPECTED_SIZE={spec.rootfs.size}",
            f"EXPECTED_SHA={spec.rootfs.sha256}",
            '[ -f "$FINAL" ]',
            '[ ! -L "$FINAL" ]',
            '[ ! -L "$WORK" ]',
            'FINAL_SIZE=$(/bin/busybox stat -c %s "$FINAL")',
            '[ "$FINAL_SIZE" = "$EXPECTED_SIZE" ]',
            'FINAL_SHA=$(/bin/busybox sha256sum "$FINAL")',
            'FINAL_SHA=${FINAL_SHA%% *}',
            '[ "$FINAL_SHA" = "$EXPECTED_SHA" ]',
            'if [ -e "$WORK" ]; then',
            '  [ -f "$WORK" ]',
            '  WORK_SIZE=$(/bin/busybox stat -c %s "$WORK")',
            '  WORK_MODE=$(/bin/busybox stat -c %a "$WORK")',
            '  [ "$WORK_SIZE" = "$EXPECTED_SIZE" ]',
            f'  [ "$WORK_MODE" = "{WORK_MODE}" ]',
            '  /bin/busybox rm "$WORK"',
            '  DISPOSITION=removed',
            'else',
            '  DISPOSITION=already-absent',
            'fi',
            '[ ! -e "$WORK" ]',
            '[ ! -L "$WORK" ]',
            'echo A90D1_WORK_CLEANUP exact=1 work_absent=1 disposition=$DISPOSITION',
        )
    )


def resident_d0_preflight(
    spec: SessionSpec,
    *,
    unattended_qualified: bool = False,
) -> tuple[SessionPreflight, dict[str, Any]]:
    if type(unattended_qualified) is not bool:
        raise ContractError("D1 presence qualification is not boolean")
    f1_spec = _f1_spec(spec)
    args = _effect_args()
    health = verify_resident_health_exact(spec, f1_spec, args)
    source = require_exact_source_preflight_receipt(
        f1_spec,
        base.remote_source_preflight(f1_spec, args),
    )
    preflight = SessionPreflight(
        not unattended_qualified,
        True,
        True,
        True,
        True,
        unattended_resident_d1_qualified=unattended_qualified,
    )
    preflight.validate()
    return (
        preflight,
        {
            "resident_health": health,
            "source_preflight": source,
            "rollback_sha256": spec.rollback.sha256,
            "recovery_profile": spec.recovery_profile,
        },
    )


def _preflight(
    spec: SessionSpec,
    *,
    operator_attended: bool,
) -> tuple[SessionPreflight, dict[str, Any]]:
    if operator_attended is not True:
        raise ContractError("operator attendance is required for every D1 action")
    return resident_d0_preflight(spec)


def _classify_return_observation(
    f1_spec: base.F1Spec,
    observation: dict[str, Any],
) -> tuple[bool, dict[str, str]]:
    candidate_return = observation.get("candidate_return")
    return_error = observation.get("candidate_return_error")
    retained_error = observation.get("retained_pmsg_error")
    release = observation.get("candidate_return_modemmanager_guard_release")
    retained = observation.get("retained_pmsg")
    if (
        isinstance(candidate_return, dict)
        and return_error is not None
        and retained_error is None
        and retained is None
    ):
        # Older observers recorded a retained-pmsg collection failure in the
        # candidate-return slot after exact return had already been captured.
        retained_error = return_error
        return_error = None
    errors: dict[str, str] = {}
    release_ok = isinstance(release, dict) and release.get("released") is True
    if not release_ok:
        errors["return_guard"] = "candidate-return guard release is not exact"
    returned = False
    if isinstance(candidate_return, dict) and return_error is None:
        try:
            return_epoch = _require_dict(
                candidate_return.get("return_epoch"),
                "candidate return epoch",
            )
            epoch_before = base._validated_return_epoch_key(  # noqa: SLF001
                f1_spec,
                return_epoch.get("pre_handoff"),
            )
            epoch_after = base._validated_return_epoch_key(  # noqa: SLF001
                f1_spec,
                return_epoch.get("returned"),
            )
            guard_proof = _require_dict(
                candidate_return.get("candidate_return_modemmanager_guard"),
                "candidate return guard",
            )
            if (
                set(candidate_return)
                != {
                    "exact_bridge",
                    "selected_realpath",
                    "return_epoch",
                    "native_epoch_version_proven",
                    "channel",
                    "version",
                    "selftest",
                    "device_command_sequences",
                    "candidate_return_modemmanager_guard",
                }
                or candidate_return.get("exact_bridge") is not True
                or candidate_return.get("selected_realpath")
                != f1_spec.stage.bridge_realpath
                or candidate_return.get("native_epoch_version_proven") is not True
                or type(candidate_return.get("device_command_sequences")) is not int
                or candidate_return.get("device_command_sequences") != 1
                or not isinstance(candidate_return.get("channel"), dict)
                or not isinstance(candidate_return.get("version"), dict)
                or not isinstance(candidate_return.get("selftest"), dict)
                or set(return_epoch)
                != {
                    "proof",
                    "pre_handoff",
                    "returned",
                    "usb_serial_epoch_changed",
                }
                or return_epoch.get("proof") is not True
                or return_epoch.get("usb_serial_epoch_changed") is not True
                or epoch_before[3:] == epoch_after[3:]
                or set(guard_proof)
                != {
                    "exact_a90_acm_identity",
                    "exact_guard_properties",
                    "identity_sha256",
                    "guard_spec_sha256",
                    "guard_topology_sha256",
                }
                or guard_proof.get("exact_a90_acm_identity") is not True
                or guard_proof.get("exact_guard_properties") is not True
                or any(
                    HEX64_RE.fullmatch(str(guard_proof.get(key) or "")) is None
                    for key in (
                        "identity_sha256",
                        "guard_spec_sha256",
                        "guard_topology_sha256",
                    )
                )
            ):
                raise ContractError("candidate return proof is not exact")
            returned = True
        except (ContractError, base.ContractError, staging.ContractError):
            errors["return_observation"] = "candidate return proof is not exact"
    if return_error is not None:
        errors["return_observation"] = "candidate return carries an error"
    if returned and not (
        isinstance(retained, dict)
        and retained.get("proof") is True
        and retained.get("armed_positive_control") is True
        and retained.get("capture_fsynced_before_cleanup") is True
        and retained.get("exact_cleanup") is True
        and retained.get("pstore_empty_after") is True
    ):
        errors["retained_pmsg"] = "retained pmsg capture or cleanup is not exact"
    if retained_error is not None:
        errors["retained_pmsg"] = "retained pmsg observer reported an error"
    return returned, errors


def _append_record(
    spec: SessionSpec,
    transaction_dir: Path,
    action: str,
    payload: dict[str, Any],
    *,
    expected_sequence: int,
) -> Path:
    bound_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "action",
        "run_id",
        "manifest_sha256",
    }
    if bound_keys.intersection(payload):
        raise ContractError("D1 journal payload overrides a bound field")
    journal_dir = transaction_dir / "journal"
    existing = tuple(sorted(journal_dir.glob("*.json"))) if journal_dir.exists() else ()
    sequence = len(existing)
    if sequence != expected_sequence:
        raise ContractError("D1 journal expected sequence changed")
    path = journal_dir / f"{sequence:04d}-{action}.json"
    write_private_json_exclusive(
        path,
        {
            "schema": JOURNAL_SCHEMA,
            "sequence": sequence,
            "timestamp_utc": utc_now(),
            "action": action,
            "run_id": spec.run_id,
            "manifest_sha256": spec.manifest_sha256,
            **payload,
        },
    )
    return path


def _preflight_value(value: SessionPreflight | None) -> dict[str, bool] | None:
    if value is None:
        return None
    result = {
        "operator_attended": value.operator_attended,
        "target_identity_matches": value.target_identity_matches,
        "resident_identity_matches": value.resident_identity_matches,
        "rollback_ready": value.rollback_ready,
        "recovery_available": value.recovery_available,
    }
    if value.unattended_resident_d1_qualified:
        result["unattended_resident_d1_qualified"] = True
    return result


def _action_outcome_value(
    ordinal: int,
    result: engine.SessionActionResult,
) -> dict[str, Any]:
    result.validate()
    return {
        "schema": OUTCOME_SCHEMA,
        "ordinal": ordinal,
        "action": SessionAction.SWITCHROOT_EXPERIMENT.value,
        "status": result.status.value,
        "action_started": result.action_started,
        "failure_class": result.failure_class,
        "postflight": _preflight_value(result.postflight),
        "independent_safety_check": result.independent_safety_check,
    }


class LiveSessionEffects:
    mode = "A90_D1_LIVE_NO_PAYLOAD_V1"

    def __init__(
        self,
        spec: SessionSpec,
        transaction_dir: Path,
        *,
        binding: AttendedSessionBinding,
        opening_preflight_evidence: dict[str, Any],
        visible_confirmed: str,
        clock: Callable[[], float] | None = None,
        presence_mode: str = "attended",
        enforce_session_window: bool = True,
        pre_dispatch_revalidate: Callable[[], None] | None = None,
    ) -> None:
        self.spec = spec
        self.transaction_dir = transaction_dir
        self.binding = binding
        self.opening_preflight_evidence = opening_preflight_evidence
        self.visible_confirmed = visible_confirmed
        self.clock = time.time if clock is None else clock
        self.presence_mode = presence_mode
        self.enforce_session_window = enforce_session_window
        self.pre_dispatch_revalidate = pre_dispatch_revalidate
        if not callable(self.clock):
            raise ContractError("D1 session clock is not callable")
        if presence_mode not in {
            "attended",
            "A90_UNATTENDED_RESIDENT_D1_V1",
        }:
            raise ContractError("D1 presence mode is not exact")
        if type(enforce_session_window) is not bool:
            raise ContractError("D1 session-window mode is not boolean")
        if pre_dispatch_revalidate is not None and not callable(
            pre_dispatch_revalidate
        ):
            raise ContractError("D1 pre-dispatch revalidator is not callable")
        if presence_mode == "attended" and enforce_session_window is not True:
            raise ContractError("attended D1 cannot disable its session window")
        if (
            presence_mode == "A90_UNATTENDED_RESIDENT_D1_V1"
            and enforce_session_window is not False
        ):
            raise ContractError("unattended one-ordinal D1 cannot inherit a session window")

    def _healthy_postflight(self) -> SessionPreflight:
        unattended = self.presence_mode == "A90_UNATTENDED_RESIDENT_D1_V1"
        value = SessionPreflight(
            operator_attended=not unattended,
            target_identity_matches=True,
            resident_identity_matches=True,
            rollback_ready=True,
            recovery_available=True,
            unattended_resident_d1_qualified=unattended,
        )
        value.validate()
        return value

    def _finish_action(
        self,
        action_dir: Path,
        ordinal: int,
        result: engine.SessionActionResult,
    ) -> engine.SessionActionResult:
        write_private_json_exclusive(
            action_dir / "engine-outcome.json",
            _action_outcome_value(ordinal, result),
        )
        return result

    def _expired_before_dispatch(
        self,
        action_dir: Path,
        ordinal: int,
        binding: AttendedSessionBinding,
    ) -> engine.SessionActionResult | None:
        if not self.enforce_session_window:
            return None
        checked_at_epoch_sec = _sample_epoch_sec(
            self.clock,
            floor_epoch_sec=binding.not_before_epoch_sec,
        )
        if checked_at_epoch_sec < binding.expires_at_epoch_sec:
            return None
        write_private_json_exclusive(
            action_dir / "expiry-before-dispatch.json",
            {
                "schema": RESULT_SCHEMA,
                "ordinal": ordinal,
                "checked_at_epoch_sec": checked_at_epoch_sec,
                "expires_at_epoch_sec": binding.expires_at_epoch_sec,
                "action_started": False,
                "handoff_dispatch_count": 0,
            },
        )
        return self._finish_action(
            action_dir,
            ordinal,
            engine.SessionActionResult(
                engine.SessionActionStatus.WINDOW_EXPIRED_NO_EFFECT,
                False,
                failure_class="SESSION_WINDOW_EXPIRED",
            ),
        )

    def consume_session_approval_once(self, binding: AttendedSessionBinding) -> bool:
        if binding != self.binding:
            raise ContractError("session approval binding changed")
        _append_record(
            self.spec,
            self.transaction_dir,
            "session-open",
            {
                "approval_binding_sha256": json_sha256(approval_binding(self.spec)),
                "session_binding_sha256": json_sha256(_binding_value(binding)),
                "opened_at_epoch_sec": binding.not_before_epoch_sec,
                "expires_at_epoch_sec": binding.expires_at_epoch_sec,
                "approval_consumed": True,
                "payload_transfer": False,
                "partition_write": False,
                "flash": False,
            },
            expected_sequence=0,
        )
        return True

    def record_action_intent(
        self,
        binding: AttendedSessionBinding,
        ordinal: int,
        action: SessionAction,
        observer_sha256: str,
        observer_no_proof_acknowledged: bool,
    ) -> None:
        if (
            binding != self.binding
            or action is not SessionAction.SWITCHROOT_EXPERIMENT
            or observer_sha256 != binding.observer_sha256
            or type(observer_no_proof_acknowledged) is not bool
        ):
            raise ContractError("D1 action intent binding changed")
        _append_record(
            self.spec,
            self.transaction_dir,
            f"action-{ordinal:03d}-intent",
            {
                "ordinal": ordinal,
                "session_action": action.value,
                "observer_sha256": observer_sha256,
                "observer_no_proof_acknowledged": (
                    observer_no_proof_acknowledged
                ),
                "handoff_dispatch_count_max": 1,
                "action_replay": False,
                "payload_transfer": False,
                "partition_write": False,
                "flash": False,
            },
            expected_sequence=2 * ordinal - 1,
        )

    def invoke_action(
        self,
        binding: AttendedSessionBinding,
        ordinal: int,
        action: SessionAction,
        observer_sha256: str,
    ) -> engine.SessionActionResult:
        if (
            binding != self.binding
            or action is not SessionAction.SWITCHROOT_EXPERIMENT
            or observer_sha256 != binding.observer_sha256
        ):
            raise ContractError("D1 action binding changed")
        action_dir = self.transaction_dir / f"action-{ordinal:03d}"
        action_dir.mkdir(parents=False, exist_ok=False, mode=0o700)
        expired = self._expired_before_dispatch(action_dir, ordinal, binding)
        if expired is not None:
            return expired
        f1_spec = _f1_spec(self.spec)
        args = _effect_args()
        guard = None
        resident_health_proven = False
        handoff_intent_written = False
        try:
            opening = self.opening_preflight_evidence
            self.opening_preflight_evidence = {}
            if set(opening) != {
                "resident_health",
                "source_preflight",
                "rollback_sha256",
                "recovery_profile",
            }:
                raise ContractError("D1 opening preflight evidence is not exact")
            health = opening["resident_health"]
            source = opening["source_preflight"]
            resident_health_proven = True
            ncm = base.rebind_host_ncm_after_reenumeration(f1_spec, args)
            pstore = base.require_clean_pstore_before_handoff(args)
            channel = base.settle_observation_channel(args, phase=f"d1-action-{ordinal}-before-handoff")
            epoch = base.capture_bridge_serial_epoch(f1_spec, args)
            pre_handoff = {
                "resident_health": health,
                "host_ncm_rebind": ncm,
                "pstore_before_handoff": pstore,
                "source_preflight": source,
                "channel_before_handoff": channel,
                "return_epoch_before_handoff": epoch,
            }
            write_private_json_exclusive(action_dir / "preflight.json", pre_handoff)
            guard = base.arm_candidate_return_modemmanager_guard(
                f1_spec,
                args,
                action_dir,
            )
            write_private_json_exclusive(
                action_dir / "handoff-intent.json",
                {
                    "schema": RESULT_SCHEMA,
                    "ordinal": ordinal,
                    "handoff_command": list(f1_spec.handoff_command),
                    "handoff_dispatch_count_max": 1,
                    "journal_fsync_completed_before_dispatch": True,
                },
            )
            handoff_intent_written = True
            if self.pre_dispatch_revalidate is not None:
                try:
                    self.pre_dispatch_revalidate()
                except Exception as exc:  # noqa: BLE001 - still before dispatch
                    write_private_json_exclusive(
                        action_dir / "pre-dispatch-revalidation-error.json",
                        {"type": type(exc).__name__, "message": str(exc)},
                    )
                    return self._finish_action(
                        action_dir,
                        ordinal,
                        engine.SessionActionResult(
                            engine.SessionActionStatus.EXPERIMENT_BLOCKED,
                            action_started=True,
                            failure_class="PRE_DISPATCH_INTEGRITY_BLOCKED",
                            postflight=self._healthy_postflight(),
                        ),
                    )
            expired = self._expired_before_dispatch(action_dir, ordinal, binding)
            if expired is not None:
                return expired
            try:
                observation = phase3_observer.observe_attended_after_handoff(
                    f1_spec,
                    args,
                    action_dir,
                    pre_handoff,
                    return_guard=guard,
                )
            except Exception as exc:  # noqa: BLE001 - reporting can fail after return
                observation = {
                    "proof": False,
                    "observer_exception": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                }
            if not isinstance(observation, dict):
                observation = {
                    "proof": False,
                    "observer_exception": {
                        "type": "ContractError",
                        "message": "observer returned a non-object result",
                    },
                }
            release = observation.get(
                "candidate_return_modemmanager_guard_release"
            )
            if isinstance(release, dict) and release.get("released") is True:
                guard = None
            returned, observation_errors = _classify_return_observation(
                f1_spec,
                observation,
            )
            postflight_errors: dict[str, dict[str, str]] = {}
            observation_warnings: dict[str, dict[str, str]] = {}
            for label, message in observation_errors.items():
                destination = (
                    observation_warnings
                    if label == "retained_pmsg"
                    else postflight_errors
                )
                destination[label] = {
                    "type": "ContractError",
                    "message": message,
                }
            returned_ncm: dict[str, Any] | None = None
            cleanup: dict[str, Any] | None = None
            final_source: dict[str, Any] | None = None
            try:
                returned_ncm = base.rebind_host_ncm_after_reenumeration(f1_spec, args)
            except Exception as exc:  # noqa: BLE001 - serial health still decides safety
                postflight_errors["ncm"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            try:
                cleanup = require_exact_cleanup_receipt(
                    self.spec,
                    base.run_f1_shell(args, _cleanup_script(self.spec)),
                )
            except Exception as exc:  # noqa: BLE001 - resident health remains separable
                postflight_errors["cleanup"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            try:
                final_health = verify_resident_health_exact(
                    self.spec,
                    f1_spec,
                    args,
                )
            except Exception as exc:  # noqa: BLE001 - current resident safety is unknown
                write_private_json_exclusive(
                    action_dir / "postflight-error.json",
                    {"type": type(exc).__name__, "message": str(exc)},
                )
                return self._finish_action(
                    action_dir,
                    ordinal,
                    engine.SessionActionResult(
                        engine.SessionActionStatus.DEVICE_SAFETY_FAILURE,
                        action_started=True,
                        failure_class="POSTFLIGHT_DEVICE_SAFETY_FAILURE",
                    ),
                )
            try:
                final_source = require_exact_source_preflight_receipt(
                    f1_spec,
                    base.remote_source_preflight(f1_spec, args),
                )
            except Exception as exc:  # noqa: BLE001 - blocks reuse but not resident safety
                postflight_errors["source"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            detail = {
                "schema": RESULT_SCHEMA,
                "ordinal": ordinal,
                "handoff_dispatch_count": 1,
                "candidate_return_observed": returned,
                "observation": observation,
                "returned_ncm": returned_ncm,
                "cleanup": cleanup,
                "final_health": final_health,
                "final_source": final_source,
                "postflight_errors": postflight_errors,
                "observation_warnings": observation_warnings,
                "resident_healthy": True,
                "payload_transfer": False,
                "partition_write": False,
                "flash": False,
            }
            if postflight_errors:
                detail["proof_terminal"] = "SESSION_BLOCKED_RESIDENT_HEALTHY"
                write_private_json_exclusive(action_dir / "result.json", detail)
                return self._finish_action(
                    action_dir,
                    ordinal,
                    engine.SessionActionResult(
                        engine.SessionActionStatus.EXPERIMENT_BLOCKED,
                        action_started=True,
                        failure_class="POSTFLIGHT_EXPERIMENT_BLOCKED",
                        postflight=self._healthy_postflight(),
                    ),
                )
            if not returned:
                detail["proof_terminal"] = "NO_PROOF_RETURN_OBSERVER"
                write_private_json_exclusive(action_dir / "result.json", detail)
                return self._finish_action(
                    action_dir,
                    ordinal,
                    engine.SessionActionResult(
                        engine.SessionActionStatus.NO_PROOF_OBSERVER,
                        action_started=True,
                        failure_class="RETURN_CHANNEL_OBSERVER",
                        postflight=self._healthy_postflight(),
                        independent_safety_check=True,
                    ),
                )
            if observation.get("bounded_display_failure") is True:
                detail["proof_terminal"] = "REFUTED_DISPLAY_ACQUISITION"
                write_private_json_exclusive(action_dir / "result.json", detail)
                return self._finish_action(
                    action_dir,
                    ordinal,
                    engine.SessionActionResult(
                        engine.SessionActionStatus.REFUTED,
                        action_started=True,
                        failure_class="DISPLAY_ACQUISITION_REFUTED",
                        postflight=self._healthy_postflight(),
                    ),
                )
            if observation.get("display_mechanical_proof") is not True:
                detail["proof_terminal"] = "NO_PROOF_DISPLAY_OBSERVER"
                write_private_json_exclusive(action_dir / "result.json", detail)
                return self._finish_action(
                    action_dir,
                    ordinal,
                    engine.SessionActionResult(
                        engine.SessionActionStatus.NO_PROOF_OBSERVER,
                        action_started=True,
                        failure_class="DISPLAY_EVIDENCE_OBSERVER",
                        postflight=self._healthy_postflight(),
                        independent_safety_check=True,
                    ),
                )
            if observation.get("phase3_service_proven") is not True:
                detail["proof_terminal"] = "NO_PROOF_PHASE3_SERVICE_OBSERVER"
                write_private_json_exclusive(action_dir / "result.json", detail)
                return self._finish_action(
                    action_dir,
                    ordinal,
                    engine.SessionActionResult(
                        engine.SessionActionStatus.NO_PROOF_OBSERVER,
                        action_started=True,
                        failure_class="PHASE3_SERVICE_EVIDENCE_OBSERVER",
                        postflight=self._healthy_postflight(),
                        independent_safety_check=True,
                    ),
                )
            if self.visible_confirmed == "no":
                detail["proof_terminal"] = "REFUTED_DISPLAY_VISIBILITY"
                write_private_json_exclusive(action_dir / "result.json", detail)
                return self._finish_action(
                    action_dir,
                    ordinal,
                    engine.SessionActionResult(
                        engine.SessionActionStatus.REFUTED,
                        action_started=True,
                        failure_class="DISPLAY_VISIBILITY_REFUTED",
                        postflight=self._healthy_postflight(),
                    ),
                )
            detail["proof_terminal"] = (
                "PASS_SWITCHROOT_RETURN_VISIBLE"
                if self.visible_confirmed == "yes"
                else "PASS_SWITCHROOT_RETURN_NO_PROOF_DISPLAY_VISIBILITY"
            )
            write_private_json_exclusive(action_dir / "result.json", detail)
            return self._finish_action(
                action_dir,
                ordinal,
                engine.SessionActionResult(
                    engine.SessionActionStatus.PROVED,
                    action_started=True,
                    postflight=self._healthy_postflight(),
                ),
            )
        except Exception as exc:  # noqa: BLE001 - classify only before dispatch
            write_private_json_exclusive(
                action_dir / "pre-handoff-error.json",
                {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "resident_health_proven": resident_health_proven,
                    "handoff_intent_written": handoff_intent_written,
                },
            )
            if resident_health_proven and not handoff_intent_written:
                return self._finish_action(
                    action_dir,
                    ordinal,
                    engine.SessionActionResult(
                        engine.SessionActionStatus.EXPERIMENT_BLOCKED,
                        action_started=True,
                        failure_class="PRE_HANDOFF_EXPERIMENT_BLOCKED",
                        postflight=self._healthy_postflight(),
                    ),
                )
            return self._finish_action(
                action_dir,
                ordinal,
                engine.SessionActionResult(
                    engine.SessionActionStatus.CONTROL_AMBIGUOUS,
                    action_started=True,
                    failure_class="HANDOFF_CONTROL_AMBIGUOUS",
                ),
            )
        finally:
            if guard is not None:
                try:
                    base.release_candidate_return_modemmanager_guard(
                        guard,
                        action_dir,
                    )
                except Exception:  # noqa: BLE001 - original result remains primary
                    pass

    def record_observer_repair(self, binding, repair) -> None:  # noqa: ANN001
        del binding, repair
        raise ContractError("live observer repair requires a new reviewed closure")


def _session_records(
    spec: SessionSpec,
    transaction_dir: Path,
) -> tuple[dict[str, Any], ...]:
    journal = transaction_dir / "journal"
    paths = tuple(sorted(journal.glob("*.json"))) if journal.exists() else ()
    records = tuple(_read_private_json(path) for path in paths)
    for index, (path, item) in enumerate(zip(paths, records, strict=True)):
        action = item.get("action")
        if (
            item.get("schema") != JOURNAL_SCHEMA
            or item.get("sequence") != index
            or item.get("run_id") != spec.run_id
            or item.get("manifest_sha256") != spec.manifest_sha256
            or not isinstance(action, str)
            or path.name != f"{index:04d}-{action}.json"
        ):
            raise ContractError("D1 session journal sequence is not exact")
    return records


def _binding_from_session_open(
    spec: SessionSpec,
    records: tuple[dict[str, Any], ...],
) -> AttendedSessionBinding:
    if not records or records[0].get("action") != "session-open":
        raise ContractError("D1 session lacks exact open record")
    opened_at = records[0].get("opened_at_epoch_sec")
    expires_at = records[0].get("expires_at_epoch_sec")
    if type(opened_at) is not int or type(expires_at) is not int:
        raise ContractError("D1 session open window is absent")
    binding = _binding(spec, opened_at)
    if expires_at != binding.expires_at_epoch_sec:
        raise ContractError("D1 session open window changed")
    return binding


def _validate_snapshot(
    spec: SessionSpec,
    binding: AttendedSessionBinding,
    snapshot: dict[str, Any],
    expected_actions_used: int,
) -> None:
    expected_keys = {
        "schema",
        "workflow",
        "risk_tier",
        "effects_mode",
        "terminal",
        "session_open",
        "session_active",
        "observer_repair_required",
        "observer_no_proof_acknowledgements",
        "active_observer_sha256",
        "actions_used",
        "actions_remaining",
        "opened_at_epoch_sec",
        "expires_at_epoch_sec",
        "last_now_epoch_sec",
        "device_safety_state",
        "candidate_transfer",
        "rollback_transfer",
        "payload_transfer",
        "action_replay",
        "history",
        "action_results",
    }
    terminal = snapshot.get("terminal")
    session_open = snapshot.get("session_open")
    session_active = snapshot.get("session_active")
    repair_required = snapshot.get("observer_repair_required")
    no_proof_acknowledgements = snapshot.get(
        "observer_no_proof_acknowledgements"
    )
    opened_at = snapshot.get("opened_at_epoch_sec")
    last_now = snapshot.get("last_now_epoch_sec")
    history = snapshot.get("history")
    action_results = snapshot.get("action_results")
    if (
        set(snapshot) != expected_keys
        or snapshot.get("schema") != engine.ENGINE_SCHEMA
        or snapshot.get("workflow") != Workflow.ATTENDED_SESSION_D1.value
        or snapshot.get("risk_tier")
        != RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL.value
        or snapshot.get("effects_mode") != LiveSessionEffects.mode
        or snapshot.get("active_observer_sha256")
        != spec.source_closure["observation_pipeline"].sha256
        or snapshot.get("actions_used") != expected_actions_used
        or snapshot.get("actions_remaining")
        != spec.max_actions - expected_actions_used
        or type(opened_at) is not int
        or type(last_now) is not int
        or not binding.not_before_epoch_sec <= opened_at <= last_now
        or opened_at != binding.not_before_epoch_sec
        or snapshot.get("expires_at_epoch_sec") != binding.expires_at_epoch_sec
        or type(no_proof_acknowledgements) is not int
        or not 0 <= no_proof_acknowledgements <= 1
        or snapshot.get("device_safety_state")
        not in {"RESIDENT_HEALTHY", "RECOVERY_REQUIRED"}
        or any(
            snapshot.get(key) is not False
            for key in (
                "candidate_transfer",
                "rollback_transfer",
                "payload_transfer",
                "action_replay",
            )
        )
        or not isinstance(history, list)
        or not history
        or not all(isinstance(item, str) and item for item in history)
        or not isinstance(action_results, list)
        or len(action_results) != expected_actions_used
    ):
        raise ContractError("D1 session snapshot is not exact")
    if terminal == "SESSION_ACTIVE":
        if (session_open, session_active, repair_required) != (True, True, False):
            raise ContractError("D1 active-session snapshot is inconsistent")
    elif terminal == "SESSION_PAUSED_OBSERVER_REPAIR_REQUIRED":
        if (session_open, session_active, repair_required) != (True, False, True):
            raise ContractError("D1 paused-session snapshot is inconsistent")
    elif not (
        isinstance(terminal, str)
        and terminal.startswith(("SESSION_CLOSED_", "RECOVERY_REQUIRED"))
        and session_open is False
        and session_active is False
    ):
        raise ContractError("D1 session terminal is not exact")
    for ordinal, item in enumerate(action_results, start=1):
        if (
            not isinstance(item, dict)
            or set(item) != {"ordinal", "action", "status", "failure_class"}
            or item.get("ordinal") != ordinal
            or item.get("action") != SessionAction.SWITCHROOT_EXPERIMENT.value
        ):
            raise ContractError("D1 action result snapshot is not exact")
        try:
            engine.SessionActionStatus(item.get("status"))
        except (TypeError, ValueError) as exc:
            raise ContractError("D1 action result status is not exact") from exc
        failure_class = item.get("failure_class")
        if failure_class is not None and (
            not isinstance(failure_class, str) or not failure_class
        ):
            raise ContractError("D1 action failure class is not exact")


def _result_from_outcome(value: dict[str, Any]) -> engine.SessionActionResult:
    if (
        set(value) != {"ordinal", "action", "status", "failure_class"}
        or value.get("action") != SessionAction.SWITCHROOT_EXPERIMENT.value
    ):
        raise ContractError("D1 replay outcome is not exact")
    try:
        status = engine.SessionActionStatus(value.get("status"))
    except (TypeError, ValueError) as exc:
        raise ContractError("D1 replay outcome status is not exact") from exc
    safe_statuses = {
        engine.SessionActionStatus.PROVED,
        engine.SessionActionStatus.REFUTED,
        engine.SessionActionStatus.NO_PROOF_OBSERVER,
        engine.SessionActionStatus.EXPERIMENT_BLOCKED,
    }
    action_started = status is not engine.SessionActionStatus.WINDOW_EXPIRED_NO_EFFECT
    result = engine.SessionActionResult(
        status=status,
        action_started=action_started,
        failure_class=value.get("failure_class"),
        postflight=(
            SessionPreflight(True, True, True, True, True)
            if status in safe_statuses
            else None
        ),
        independent_safety_check=(
            status is engine.SessionActionStatus.NO_PROOF_OBSERVER
        ),
    )
    result.validate()
    return result


def _compact_outcome_evidence(
    value: dict[str, Any],
    ordinal: int,
) -> dict[str, Any]:
    compact = {
        "ordinal": value.get("ordinal"),
        "action": value.get("action"),
        "status": value.get("status"),
        "failure_class": value.get("failure_class"),
    }
    result = _result_from_outcome(compact)
    if value != _action_outcome_value(ordinal, result):
        raise ContractError("D1 engine outcome evidence is not exact")
    return compact


class _ReplaySessionEffects:
    mode = LiveSessionEffects.mode

    def __init__(
        self,
        outcomes: tuple[dict[str, Any], ...],
        acknowledgements: tuple[bool, ...],
    ) -> None:
        self.results = tuple(_result_from_outcome(item) for item in outcomes)
        self.acknowledgements = acknowledgements
        self.index = 0

    def consume_session_approval_once(self, binding: AttendedSessionBinding) -> bool:
        del binding
        return True

    def record_action_intent(
        self,
        binding: AttendedSessionBinding,
        ordinal: int,
        action: SessionAction,
        observer_sha256: str,
        observer_no_proof_acknowledged: bool,
    ) -> None:
        del binding, action, observer_sha256
        if (
            ordinal != self.index + 1
            or ordinal > len(self.acknowledgements)
            or observer_no_proof_acknowledged
            is not self.acknowledgements[ordinal - 1]
        ):
            raise ContractError("D1 replay ordinal changed")

    def invoke_action(
        self,
        binding: AttendedSessionBinding,
        ordinal: int,
        action: SessionAction,
        observer_sha256: str,
    ) -> engine.SessionActionResult:
        del binding, action, observer_sha256
        if ordinal != self.index + 1 or self.index >= len(self.results):
            raise ContractError("D1 replay result order changed")
        result = self.results[self.index]
        self.index += 1
        return result

    def record_observer_repair(self, binding, repair) -> None:  # noqa: ANN001
        del binding, repair
        raise ContractError("D1 replay does not cross an observer-repair boundary")


def _restore_session(
    spec: SessionSpec,
    binding: AttendedSessionBinding,
    records: tuple[dict[str, Any], ...],
) -> engine.AttendedSession:
    if not records or records[0].get("action") != "session-open":
        raise ContractError("D1 session lacks exact open record")
    common_keys = {
        "schema",
        "sequence",
        "timestamp_utc",
        "action",
        "run_id",
        "manifest_sha256",
    }
    session_open = records[0]
    if (
        set(session_open)
        != common_keys
        | {
            "approval_binding_sha256",
            "session_binding_sha256",
            "opened_at_epoch_sec",
            "expires_at_epoch_sec",
            "approval_consumed",
            "payload_transfer",
            "partition_write",
            "flash",
        }
        or session_open.get("approval_binding_sha256")
        != json_sha256(approval_binding(spec))
        or session_open.get("session_binding_sha256")
        != json_sha256(_binding_value(binding))
        or session_open.get("opened_at_epoch_sec")
        != binding.not_before_epoch_sec
        or session_open.get("expires_at_epoch_sec")
        != binding.expires_at_epoch_sec
        or binding.expires_at_epoch_sec - binding.not_before_epoch_sec
        != spec.session_duration_sec
        or session_open.get("approval_consumed") is not True
        or any(
            session_open.get(key) is not False
            for key in ("payload_transfer", "partition_write", "flash")
        )
    ):
        raise ContractError("D1 session open record is not exact")
    action_names = [str(item.get("action")) for item in records[1:]]
    if len(action_names) % 2 != 0:
        raise ContractError("D1 action intent has no durable result; no retry permitted")
    snapshots: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    action_times: list[int] = []
    acknowledgements: list[bool] = []
    for index in range(0, len(action_names), 2):
        ordinal = index // 2 + 1
        if action_names[index] != f"action-{ordinal:03d}-intent" or action_names[index + 1] != f"action-{ordinal:03d}-result":
            raise ContractError("D1 session action journal order changed")
        intent = records[index + 1]
        result_record = records[index + 2]
        if (
            set(intent)
            != common_keys
            | {
                "ordinal",
                "session_action",
                "observer_sha256",
                "observer_no_proof_acknowledged",
                "handoff_dispatch_count_max",
                "action_replay",
                "payload_transfer",
                "partition_write",
                "flash",
            }
            or type(intent.get("ordinal")) is not int
            or intent.get("ordinal") != ordinal
            or intent.get("session_action")
            != SessionAction.SWITCHROOT_EXPERIMENT.value
            or intent.get("observer_sha256")
            != spec.source_closure["observation_pipeline"].sha256
            or type(intent.get("handoff_dispatch_count_max")) is not int
            or intent.get("handoff_dispatch_count_max") != 1
            or type(intent.get("observer_no_proof_acknowledged")) is not bool
            or any(
                intent.get(key) is not False
                for key in (
                    "action_replay",
                    "payload_transfer",
                    "partition_write",
                    "flash",
                )
            )
            or set(result_record)
            != common_keys
            | {"snapshot", "outcome", "outcome_evidence", "now_epoch_sec"}
        ):
            raise ContractError("D1 action journal binding is not exact")
        snapshot = result_record.get("snapshot")
        outcome = result_record.get("outcome")
        outcome_evidence = _bound_dict(
            result_record.get("outcome_evidence"),
            f"D1 action {ordinal} outcome evidence",
            private=True,
        )
        action_time = result_record.get("now_epoch_sec")
        if not isinstance(snapshot, dict):
            raise ContractError("D1 action result snapshot is absent")
        snapshot_results = snapshot.get("action_results")
        if (
            not isinstance(outcome, dict)
            or not isinstance(snapshot_results, list)
            or not snapshot_results
            or outcome != snapshot_results[-1]
            or outcome.get("ordinal") != ordinal
            or type(action_time) is not int
            or action_time != snapshot.get("last_now_epoch_sec")
        ):
            raise ContractError("D1 action outcome binding is not exact")
        expected_outcome_path = (
            spec.transaction_dir
            / f"action-{ordinal:03d}"
            / "engine-outcome.json"
        )
        if (
            outcome_evidence.path != expected_outcome_path
            or _compact_outcome_evidence(
                _read_private_json(outcome_evidence.path),
                ordinal,
            )
            != outcome
        ):
            raise ContractError("D1 action outcome evidence binding changed")
        _validate_snapshot(spec, binding, snapshot, ordinal)
        snapshots.append(snapshot)
        outcomes.append(outcome)
        action_times.append(action_time)
        acknowledgements.append(intent["observer_no_proof_acknowledged"])
    last = snapshots[-1] if snapshots else None
    if last is None:
        raise ContractError("opened D1 session has no completed action")
    contract = engine.AttendedSessionContract(
        binding=binding,
        successors=(DISPLAY_SUCCESSOR,),
    )
    replay_effects = _ReplaySessionEffects(
        tuple(outcomes),
        tuple(acknowledgements),
    )
    try:
        replay = engine.open_attended_session(
            contract,
            replay_effects,
            now_epoch_sec=binding.not_before_epoch_sec,
            preflight=SessionPreflight(True, True, True, True, True),
        )
        for action_time, snapshot, acknowledged in zip(
            action_times,
            snapshots,
            acknowledgements,
            strict=True,
        ):
            reproduced = replay.run_action(
                SessionAction.SWITCHROOT_EXPERIMENT,
                now_epoch_sec=action_time,
                preflight=SessionPreflight(True, True, True, True, True),
                acknowledge_observer_no_proof=acknowledged,
            )
            if reproduced != snapshot:
                raise ContractError("D1 session snapshot replay differs")
    except engine.ContractError as exc:
        raise ContractError("D1 session transition replay failed") from exc
    if replay_effects.index != len(outcomes):
        raise ContractError("D1 session replay did not consume every outcome")
    return replay


def _execute_switchroot_locked(
    spec: SessionSpec,
    *,
    transaction_dir: Path,
    approval: str | None,
    resume: bool,
    operator_attended: bool,
    acknowledge_observer_no_proof: bool,
    visible_confirmed: str,
    now_epoch_sec: int,
    clock: Callable[[], float],
) -> dict[str, Any]:
    if visible_confirmed not in {"yes", "no", "unavailable"}:
        raise ContractError("visible confirmation value is not exact")
    if type(now_epoch_sec) is not int or now_epoch_sec < 0:
        raise ContractError("D1 session time is not exact")
    if type(acknowledge_observer_no_proof) is not bool:
        raise ContractError("observer no-proof acknowledgement is not boolean")
    session: engine.AttendedSession | None = None
    binding: AttendedSessionBinding | None = None
    if resume:
        if approval is not None:
            raise ContractError("resumed D1 session must not consume approval again")
        if not transaction_dir.is_dir():
            raise ContractError("resumed D1 session directory is absent")
        records = _session_records(spec, transaction_dir)
        binding = _binding_from_session_open(spec, records)
        if now_epoch_sec >= binding.expires_at_epoch_sec:
            raise ContractError("D1 session approval window is not active")
        session = _restore_session(spec, binding, records)
        if session.closed_terminal is not None:
            raise ContractError("D1 session is already closed")
        if now_epoch_sec < session.last_now_epoch_sec:
            raise ContractError("session time is not monotonic")
        paused = session.observer_repair_required
        if paused and not acknowledge_observer_no_proof:
            raise ContractError(
                "D1 session requires explicit observer no-proof acknowledgement"
            )
        if not paused and acknowledge_observer_no_proof:
            raise ContractError("observer no-proof acknowledgement is unexpected")
    else:
        if transaction_dir.exists():
            raise ContractError("fresh D1 session directory already exists")
        if approval is None:
            raise ContractError("fresh D1 session approval is absent")
        if acknowledge_observer_no_proof:
            raise ContractError("fresh D1 session cannot acknowledge prior no-proof")
        require_approval(spec, approval)
    preflight, preflight_evidence = _preflight(
        spec,
        operator_attended=operator_attended,
    )
    action_now_epoch_sec = _sample_epoch_sec(
        clock,
        floor_epoch_sec=now_epoch_sec,
    )
    if resume:
        if binding is None or action_now_epoch_sec >= binding.expires_at_epoch_sec:
            raise ContractError("D1 session approval window is not active")
    else:
        binding = _binding(spec, action_now_epoch_sec)
    if binding is None:
        raise ContractError("D1 session binding is absent")
    effects = LiveSessionEffects(
        spec,
        transaction_dir,
        binding=binding,
        opening_preflight_evidence=preflight_evidence,
        visible_confirmed=visible_confirmed,
        clock=clock,
    )
    if resume:
        if session is None or effects.binding != session.contract.binding:
            raise ContractError("D1 restored session binding changed")
        session.effects = effects
    else:
        transaction_dir.mkdir(parents=True, mode=0o700)
        write_private_json_exclusive(
            transaction_dir / "opening-preflight.json",
            preflight_evidence,
        )
        session = engine.open_attended_session(
            engine.AttendedSessionContract(
                binding=binding,
                successors=(DISPLAY_SUCCESSOR,),
            ),
            effects,
            now_epoch_sec=action_now_epoch_sec,
            preflight=preflight,
        )
    if session is None:
        raise ContractError("D1 session initialization failed")
    previous_actions = session.actions_used
    snapshot = session.run_action(
        SessionAction.SWITCHROOT_EXPERIMENT,
        now_epoch_sec=action_now_epoch_sec,
        preflight=preflight,
        acknowledge_observer_no_proof=acknowledge_observer_no_proof,
    )
    if snapshot["actions_used"] == previous_actions:
        _append_record(
            spec,
            transaction_dir,
            "session-closed",
            {"snapshot": snapshot},
            expected_sequence=2 * previous_actions + 1,
        )
        return snapshot
    outcome_path = (
        transaction_dir
        / f"action-{snapshot['actions_used']:03d}"
        / "engine-outcome.json"
    )
    outcome_evidence = _bound_file(outcome_path, private=True)
    anchored_outcome = _compact_outcome_evidence(
        _read_private_json(outcome_evidence.path),
        snapshot["actions_used"],
    )
    if anchored_outcome != snapshot["action_results"][-1]:
        raise ContractError("D1 engine outcome and session snapshot differ")
    _append_record(
        spec,
        transaction_dir,
        f"action-{snapshot['actions_used']:03d}-result",
        {
            "snapshot": snapshot,
            "outcome": anchored_outcome,
            "outcome_evidence": _as_dict(outcome_evidence),
            "now_epoch_sec": action_now_epoch_sec,
        },
        expected_sequence=2 * snapshot["actions_used"],
    )
    return snapshot


def execute_switchroot(
    spec: SessionSpec,
    *,
    transaction_dir: Path,
    approval: str | None,
    resume: bool,
    operator_attended: bool,
    acknowledge_observer_no_proof: bool = False,
    visible_confirmed: str,
    now_epoch_sec: int,
    clock: Callable[[], float] | None = None,
) -> dict[str, Any]:
    if transaction_dir != spec.transaction_dir:
        raise ContractError("D1 transaction path is not manifest-bound")
    descriptor = os.open(
        spec.session_lock_path,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise ContractError("D1 session lock identity is not exact")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContractError("D1 session is already owned by another process") from exc
        return _execute_switchroot_locked(
            spec,
            transaction_dir=transaction_dir,
            approval=approval,
            resume=resume,
            operator_attended=operator_attended,
            acknowledge_observer_no_proof=acknowledge_observer_no_proof,
            visible_confirmed=visible_confirmed,
            now_epoch_sec=now_epoch_sec,
            clock=time.time if clock is None else clock,
        )
    finally:
        os.close(descriptor)


def _record_visible_confirmation_locked(
    spec: SessionSpec,
    *,
    transaction_dir: Path,
    ordinal: int,
    visible_confirmed: str,
    operator_attended: bool,
) -> dict[str, Any]:
    if not transaction_dir.is_dir():
        raise ContractError("D1 visibility transaction directory is absent")
    if type(ordinal) is not int or ordinal <= 0:
        raise ContractError("D1 visibility ordinal is not exact")
    if visible_confirmed not in {"yes", "no"}:
        raise ContractError("D1 post-action visibility must be yes or no")
    if operator_attended is not True:
        raise ContractError("D1 visibility requires attended operator observation")

    records = _session_records(spec, transaction_dir)
    sequence = 2 * ordinal
    if sequence >= len(records):
        raise ContractError("D1 visibility action result is absent")
    record = records[sequence]
    expected_action = f"action-{ordinal:03d}-result"
    snapshot = record.get("snapshot")
    if record.get("action") != expected_action or not isinstance(snapshot, dict):
        raise ContractError("D1 visibility journal result is not exact")
    binding = _binding_from_session_open(spec, records)
    _validate_snapshot(spec, binding, snapshot, ordinal)
    action_results = snapshot.get("action_results")
    if (
        not isinstance(action_results, list)
        or len(action_results) != ordinal
        or type(action_results[-1].get("ordinal")) is not int
        or action_results[-1].get("ordinal") != ordinal
        or action_results[-1].get("action")
        != SessionAction.SWITCHROOT_EXPERIMENT.value
    ):
        raise ContractError("D1 visibility snapshot action is not exact")

    action_dir = transaction_dir / f"action-{ordinal:03d}"
    intent = _bound_file(action_dir / "handoff-intent.json", private=True)
    observation = _bound_file(action_dir / "observation.json", private=True)
    result = _bound_file(action_dir / "result.json", private=True)
    outcome = _bound_file(action_dir / "engine-outcome.json", private=True)
    journal_path = transaction_dir / "journal" / f"{sequence:04d}-{expected_action}.json"
    journal_result = _bound_file(journal_path, private=True)
    anchored_outcome = _bound_dict(
        record.get("outcome_evidence"),
        "D1 visibility outcome evidence",
        private=True,
    )
    if anchored_outcome != outcome:
        raise ContractError("D1 visibility outcome binding changed")

    intent_value = _read_private_json(intent.path)
    observation_value = _read_private_json(observation.path)
    result_value = _read_private_json(result.path)
    ssh = observation_value.get("ssh")
    if (
        intent_value.get("schema") != RESULT_SCHEMA
        or type(intent_value.get("ordinal")) is not int
        or intent_value.get("ordinal") != ordinal
        or type(intent_value.get("handoff_dispatch_count_max")) is not int
        or intent_value.get("handoff_dispatch_count_max") != 1
        or result_value.get("schema") != RESULT_SCHEMA
        or type(result_value.get("ordinal")) is not int
        or result_value.get("ordinal") != ordinal
        or type(result_value.get("handoff_dispatch_count")) is not int
        or result_value.get("handoff_dispatch_count") != 1
        or result_value.get("resident_healthy") is not True
        or result_value.get("observation") != observation_value
        or observation_value.get("native_release_proven") is not True
        or observation_value.get("debian_pid1_proven") is not True
        or observation_value.get("dropbear_proven") is not True
        or observation_value.get("display_mechanical_proof") is not True
        or observation_value.get("phase3_service_proven") is not True
        or not isinstance(ssh, dict)
        or ssh.get("proof") is not True
    ):
        raise ContractError("D1 display mechanical proof is not exact")

    proof = visible_confirmed == "yes"
    value = {
        "schema": VISIBLE_CONFIRMATION_SCHEMA,
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "ordinal": ordinal,
        "action": SessionAction.SWITCHROOT_EXPERIMENT.value,
        "operator_attended_at_observation": True,
        "visible_confirmed": visible_confirmed,
        "display_visibility_proved": proof,
        "display_visibility_refuted": not proof,
        "mechanical_display_proof": True,
        "evidence": {
            "handoff_intent": _as_dict(intent),
            "observation": _as_dict(observation),
            "action_result": _as_dict(result),
            "engine_outcome": _as_dict(outcome),
            "journal_result": _as_dict(journal_result),
        },
        "device_contact": False,
        "device_effect": False,
        "payload_transfer": False,
        "partition_write": False,
        "flash": False,
    }
    write_private_json_exclusive(
        action_dir / "display-visible-confirmation.json",
        value,
    )
    return value


def record_visible_confirmation(
    spec: SessionSpec,
    *,
    transaction_dir: Path,
    ordinal: int,
    visible_confirmed: str,
    operator_attended: bool,
) -> dict[str, Any]:
    if transaction_dir != spec.transaction_dir:
        raise ContractError("D1 transaction path is not manifest-bound")
    descriptor = os.open(
        spec.session_lock_path,
        os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
        0o600,
    )
    try:
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise ContractError("D1 session lock identity is not exact")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ContractError("D1 session is already owned by another process") from exc
        return _record_visible_confirmation_locked(
            spec,
            transaction_dir=transaction_dir,
            ordinal=ordinal,
            visible_confirmed=visible_confirmed,
            operator_attended=operator_attended,
        )
    finally:
        os.close(descriptor)


def inspect(spec: SessionSpec) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "mode": "host-only-inspection",
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest_sha256,
        "resident_terminal": (
            preserved_prep.preserved.SUCCESS_STATUS
            if spec.resident_evidence_kind
            == "preserved-install-cleanup-reduced-v1"
            else "PASS_A90_RESIDENT_INSTALLED"
        ),
        "resident_boot_sha256": spec.candidate.sha256,
        "rollback_boot_sha256": spec.rollback.sha256,
        "rootfs_sha256": spec.rootfs.sha256,
        "source_closure": {role: item.sha256 for role, item in spec.source_closure.items()},
        "ready_for_approval_preparation": True,
        "live_authority": False,
        "device_contact": False,
        "device_write": False,
        "payload_transfer": False,
        "flash": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    parser.add_argument("--build-manifest", action="store_true")
    parser.add_argument("--resident-manifest", type=Path)
    parser.add_argument("--expect-resident-manifest-sha256")
    parser.add_argument("--run-id")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--session-duration-sec", type=int, default=MAX_DURATION_SEC)
    parser.add_argument("--max-actions", type=int, default=8)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--prepare-approval", action="store_true")
    modes.add_argument("--execute-switchroot", action="store_true")
    modes.add_argument("--record-visible-confirmation", action="store_true")
    parser.add_argument("--transaction-dir", type=Path)
    parser.add_argument("--ordinal", type=int)
    parser.add_argument("--approval")
    parser.add_argument("--resume-session", action="store_true")
    parser.add_argument("--operator-attended", action="store_true")
    parser.add_argument("--acknowledge-observer-no-proof", action="store_true")
    parser.add_argument(
        "--visible-confirmed",
        choices=("yes", "no", "unavailable"),
        default="unavailable",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.build_manifest:
        required = (
            args.resident_manifest,
            args.expect_resident_manifest_sha256,
            args.run_id,
            args.output,
            args.session_duration_sec,
        )
        if any(item is None for item in required):
            raise ContractError("manifest-build arguments are incomplete")
        value = build_manifest(
            resident_manifest_path=args.resident_manifest,
            resident_manifest_sha256=args.expect_resident_manifest_sha256,
            run_id=args.run_id,
            session_duration_sec=args.session_duration_sec,
            max_actions=args.max_actions,
        )
        write_private_json_exclusive(args.output, value)
        print(json.dumps({"manifest_sha256": sha256_file(args.output), "host_only": True}, sort_keys=True))
        return 0
    if args.manifest is None or args.expect_manifest_sha256 is None:
        raise ContractError("manifest and expected SHA256 are required")
    spec = load_spec(args.manifest, args.expect_manifest_sha256)
    if args.prepare_approval:
        print(json.dumps(prepare_approval(spec), indent=2, sort_keys=True))
        return 0
    if args.execute_switchroot:
        if args.transaction_dir is None:
            raise ContractError("D1 transaction directory is required")
        result = execute_switchroot(
            spec,
            transaction_dir=args.transaction_dir,
            approval=args.approval,
            resume=args.resume_session,
            operator_attended=args.operator_attended,
            acknowledge_observer_no_proof=(
                args.acknowledge_observer_no_proof
            ),
            visible_confirmed=args.visible_confirmed,
            now_epoch_sec=int(time.time()),
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.record_visible_confirmation:
        if args.transaction_dir is None or args.ordinal is None:
            raise ContractError(
                "D1 visibility transaction directory and ordinal are required"
            )
        result = record_visible_confirmation(
            spec,
            transaction_dir=args.transaction_dir,
            ordinal=args.ordinal,
            visible_confirmed=args.visible_confirmed,
            operator_attended=args.operator_attended,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    print(json.dumps(inspect(spec), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"a90-transition-d1-session-v1: ContractError: {exc}", file=sys.stderr)
        raise SystemExit(1)
