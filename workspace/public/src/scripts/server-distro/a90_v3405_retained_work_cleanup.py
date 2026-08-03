#!/usr/bin/env python3
"""Exact one-shot cleanup for the retained A90 V3405 D3 work image.

This is a separately reviewed persistent-file cleanup contract.  Its default
mode is host-only inspection.  Live execution requires a final private
manifest, an exclusively prepared approval receipt, and the exact fresh
operator token.  It can unlink only the fixed retained work-image path after
revalidating its type, mode, size, SHA256, host preservation, target, health,
and the selected adjacent-path disposition.  The separately reviewed
source-preserved recovery profile additionally proves the adjacent source is
an exact distinct copy before and after the unlink.

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
REVIEW_SCHEMA = (
    "a90-retained-work-source-preserved-cleanup-independent-review-v1"
)
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
SOURCE_ABSENT = "absent"
SOURCE_EXACT_PRESERVED = "exact-preserved"
EXPECTED_VERSION = "0.9.285"
EXPECTED_BUILD = "v2321-usb-clean-identity-rodata"
EXPECTED_VENDOR_PRODUCT = "04e8:6861"
EXPECTED_ROLLBACK_SIZE = 60882944
EXPECTED_ROLLBACK_SHA256 = (
    "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
)
F1_MANIFEST_SCHEMA = "a90_native_init_f1_prepared_v3"
F1_MANIFEST_STATUS = "ready-for-f1-approval"
F1_RESULT_SCHEMA = "a90_v3403_f1_orchestrator_v1"
F1_JOURNAL_SCHEMA = "a90_v3403_f1_journal_v1"
F1_TIMELINE_EVENTS = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)
READ_TIMEOUT_SEC = 15.0
CLEANUP_TIMEOUT_SEC = 180.0
RUN_ID_RE = re.compile(r"^a90-v3406-work-cleanup-[0-9]{8}-[0-9]{2}$")
F1_RUN_ID_RE = re.compile(
    r"^a90-v3406-debian-display-f1-(?P<suffix>[0-9]{8}-[0-9]{2})$"
)
JOURNAL_NAME_RE = re.compile(
    r"^(?P<sequence>[0-9]{4})-(?P<action>[a-z0-9-]+)\.json$"
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
REVIEW_SOURCES = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "docs" / "operations" / "targets" / "A90_TARGET_CONTRACT.md",
    Path(__file__).resolve(),
    CONNECTED_PREFLIGHT,
    A90CTL_SOURCE,
    REVAL_DIR / "serial_tcp_bridge.py",
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
    source_disposition: str
    stage_path: str
    independent_review: BoundFile | None
    closed_f1_manifest: BoundFile | None
    closed_f1_result: BoundFile | None
    closed_f1_journal: tuple[BoundFile, ...]


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def parse_utc(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str):
        raise ContractError(f"{label} is not an exact UTC timestamp")
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.UTC
        )
    except ValueError as exc:
        raise ContractError(f"{label} is not an exact UTC timestamp") from exc
    return parsed


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


def current_bound(path: Path) -> BoundFile:
    resolved = path.resolve(strict=True)
    actual, opened = hash_open_regular(resolved)
    return BoundFile(path=resolved, size=opened.st_size, sha256=actual)


def required_review_source_records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in REVIEW_SOURCES:
        bound = current_bound(path)
        relative = str(bound.path.relative_to(REPO_ROOT.resolve(strict=True)))
        records[relative] = {"bytes": bound.size, "sha256": bound.sha256}
    return records


def validate_independent_review_binding(value: Any) -> BoundFile:
    bound = load_bound(value, "independent_review")
    reports = (REPO_ROOT / "docs" / "reports").resolve(strict=True)
    try:
        bound.path.relative_to(reports)
    except ValueError as exc:
        raise ContractError("independent review is outside docs/reports") from exc
    if bound.path.stat().st_mode & 0o022:
        raise ContractError("independent review is writable by group or other")
    try:
        report = json.loads(bound.path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("independent review is not valid JSON") from exc
    if (
        not isinstance(report, dict)
        or report.get("schema") != REVIEW_SCHEMA
        or report.get("status") != "PASS_GO"
        or report.get("unresolved_findings") != []
        or report.get("permanent_boundaries_unchanged") is not True
        or report.get("device_authority_granted") is not False
        or report.get("named_execution_critical_closure")
        != required_review_source_records()
    ):
        raise ContractError("independent review is not exact PASS_GO")
    return bound


def protocol_text(value: Any, command: str, label: str) -> str:
    item = require_dict(value, label)
    begin = require_dict(item.get("begin"), f"{label}.begin")
    end = require_dict(item.get("end"), f"{label}.end")
    text = require_string(item.get("text"), f"{label}.text")
    if (
        item.get("command") != [command]
        or item.get("rc") != 0
        or item.get("status") != "ok"
        or item.get("trust") != "A90P1_V1_STRUCTURAL_ONLY"
        or begin.get("cmd") != command
        or end.get("cmd") != command
        or end.get("rc") != "0"
        or end.get("status") != "ok"
    ):
        raise ContractError(f"{label} is not an exact framed observation")
    return text


def validate_closed_f1_binding(
    value: Any,
    f1_run_id: str,
) -> tuple[BoundFile, BoundFile, tuple[BoundFile, ...]]:
    item = require_dict(value, "closed_f1")
    if set(item) != {"manifest", "result", "journal"}:
        raise ContractError("closed F1 binding keys are not exact")
    manifest_bound = load_bound(item.get("manifest"), "closed_f1.manifest")
    result_bound = load_bound(item.get("result"), "closed_f1.result")
    expected_root = (PRIVATE_RUN_BASE / f1_run_id).resolve(strict=True)
    if (
        manifest_bound.path != expected_root / "prepared-manifest.json"
        or result_bound.path != expected_root / "f1-live" / "result.json"
    ):
        raise ContractError("closed F1 paths are not exact")
    try:
        manifest = json.loads(manifest_bound.path.read_text(encoding="utf-8"))
        result = json.loads(result_bound.path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("closed F1 JSON is invalid") from exc
    if not isinstance(manifest, dict):
        raise ContractError("closed F1 manifest is not an object")
    candidate = require_dict(manifest.get("candidate_boot"), "candidate_boot")
    rollback = require_dict(manifest.get("rollback_boot"), "rollback_boot")
    target = require_dict(manifest.get("target"), "target")
    candidate_sha = validate_sha256(candidate.get("sha256"), "candidate sha256")
    candidate_size = candidate.get("size")
    candidate_version = require_string(
        candidate.get("expected_version"),
        "candidate expected version",
    )
    candidate_build = require_string(
        candidate.get("expected_build"),
        "candidate expected build",
    )
    selected_realpath = require_string(
        target.get("bridge_selected_realpath"),
        "closed F1 selected realpath",
    )
    if (
        manifest.get("schema") != F1_MANIFEST_SCHEMA
        or manifest.get("status") != F1_MANIFEST_STATUS
        or manifest.get("run_id") != f1_run_id
        or candidate.get("partition") != "boot"
        or type(candidate_size) is not int
        or candidate_size <= 0
        or rollback.get("partition") != "boot"
        or rollback.get("size") != EXPECTED_ROLLBACK_SIZE
        or rollback.get("sha256") != EXPECTED_ROLLBACK_SHA256
        or rollback.get("expected_version") != EXPECTED_VERSION
        or rollback.get("expected_build") != EXPECTED_BUILD
        or target.get("profile") != "galaxy-a90-5g-native-init"
        or target.get("bridge_selected_exact") is not True
    ):
        raise ContractError("closed F1 manifest is not exact boot-only A90")
    journal_value = item.get("journal")
    if not isinstance(journal_value, list) or not 1 <= len(journal_value) <= 64:
        raise ContractError("closed F1 journal count is not bounded")
    journal: list[BoundFile] = []
    records: list[dict[str, Any]] = []
    actions: list[str] = []
    timestamps: list[dt.datetime] = []
    allowed_states = {
        "preflight": "PREFLIGHT",
        "approved": "APPROVED",
        "staging-started": "APPROVED",
        "rootfs-staged": "APPROVED",
        "rootfs-candidate-preflight": "APPROVED",
        "candidate-transfer-started": "APPROVED",
        "candidate-flashed": "CANDIDATE_FLASHED",
        "attended-window-open": "CANDIDATE_FLASHED",
        "attended-pre-handoff-attempt": "CANDIDATE_FLASHED",
        "attended-pre-handoff-failed": "CANDIDATE_FLASHED",
        "candidate-boot-ready": "CANDIDATE_FLASHED",
        "attended-pre-handoff-ready": "CANDIDATE_FLASHED",
        "attended-handoff-started": "CANDIDATE_FLASHED",
        "observation-proven": "OBSERVED",
        "observation-no-proof": "OBSERVED",
        "display-visible-confirmed": "OBSERVED",
        "rollback-transfer-started": "RECOVERY_ROLLBACK",
        "rollback-flashed": "ROLLBACK_FLASHED",
        "rollback-boot-ready": "ROLLBACK_FLASHED",
        "health-verified": "HEALTH_VERIFIED",
        "closed": "CLOSED",
    }
    for sequence, raw in enumerate(journal_value):
        bound = load_bound(raw, f"closed_f1.journal[{sequence}]")
        match = JOURNAL_NAME_RE.fullmatch(bound.path.name)
        expected_parent = expected_root / "f1-live" / "journal"
        try:
            record = json.loads(bound.path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContractError("closed F1 journal JSON is invalid") from exc
        action = record.get("action") if isinstance(record, dict) else None
        if (
            bound.path.parent != expected_parent
            or match is None
            or int(match.group("sequence")) != sequence
            or action != match.group("action")
            or record.get("schema") != F1_JOURNAL_SCHEMA
            or record.get("sequence") != sequence
            or record.get("run_id") != f1_run_id
            or record.get("manifest_sha256") != manifest_bound.sha256
            or action not in allowed_states
            or record.get("state") != allowed_states[action]
        ):
            raise ContractError("closed F1 journal is not contiguous and exact")
        timestamps.append(
            parse_utc(record.get("timestamp_utc"), f"journal[{sequence}] timestamp")
        )
        if record.get("candidate_replay") not in (None, False):
            raise ContractError("closed F1 journal permits candidate replay")
        journal.append(bound)
        records.append(record)
        actions.append(action)
    if timestamps != sorted(timestamps):
        raise ContractError("closed F1 journal timestamps are not monotonic")

    prefix = (
        "preflight",
        "approved",
        "staging-started",
        "rootfs-staged",
        "rootfs-candidate-preflight",
        "candidate-transfer-started",
        "candidate-flashed",
        "attended-window-open",
    )
    if tuple(actions[: len(prefix)]) != prefix:
        raise ContractError("closed F1 journal prefix order is not exact")
    cursor = len(prefix)
    attempt_count = 0
    failure_count = 0
    while cursor < len(actions) and actions[cursor] == "attended-pre-handoff-attempt":
        attempt_count += 1
        cursor += 1
        if cursor < len(actions) and actions[cursor] == "attended-pre-handoff-failed":
            failure_count += 1
            cursor += 1
            continue
        break
    if not (1 <= attempt_count <= 3) or failure_count != attempt_count - 1:
        raise ContractError("closed F1 attended attempts are not exact")
    expected_tail_prefix = (
        "candidate-boot-ready",
        "attended-pre-handoff-ready",
        "attended-handoff-started",
    )
    if tuple(actions[cursor : cursor + len(expected_tail_prefix)]) != (
        expected_tail_prefix
    ):
        raise ContractError("closed F1 attended handoff order is not exact")
    cursor += len(expected_tail_prefix)
    if cursor >= len(actions) or actions[cursor] not in {
        "observation-proven",
        "observation-no-proof",
    }:
        raise ContractError("closed F1 observation order is not exact")
    cursor += 1
    if cursor < len(actions) and actions[cursor] == "display-visible-confirmed":
        cursor += 1
    suffix = (
        "rollback-transfer-started",
        "rollback-flashed",
        "rollback-boot-ready",
        "health-verified",
        "closed",
    )
    if tuple(actions[cursor:]) != suffix:
        raise ContractError("closed F1 rollback/health order is not exact")

    required_counts = {
        "preflight": 1,
        "approved": 1,
        "candidate-transfer-started": 1,
        "candidate-flashed": 1,
        "candidate-boot-ready": 1,
        "rollback-transfer-started": 1,
        "rollback-flashed": 1,
        "rollback-boot-ready": 1,
        "health-verified": 1,
        "closed": 1,
    }
    if any(actions.count(name) != count for name, count in required_counts.items()):
        raise ContractError("closed F1 required journal actions are not exact")
    required_order = tuple(required_counts)
    allowed_status = {
        "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
        "PASS_F1_V2_DEBIAN_PID1_PROVEN_AND_ROLLED_BACK",
        "PASS_F1_V2_DISPLAY_ACQUISITION_PROVEN_AND_ROLLED_BACK",
    }
    status_facts = {
        "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK": (False, False),
        "PASS_F1_V2_DEBIAN_PID1_PROVEN_AND_ROLLED_BACK": (True, False),
        "PASS_F1_V2_DISPLAY_ACQUISITION_PROVEN_AND_ROLLED_BACK": (True, True),
    }
    result_keys = {
        "schema",
        "run_id",
        "status",
        "manifest_sha256",
        "candidate_transfer_count",
        "candidate_transfer_uncertain",
        "candidate_replay",
        "debian_pid1_proven",
        "display_acquisition_proven",
        "rollback_transfer_count",
        "final_health_restored",
        "timeline_events",
    }
    if (
        not isinstance(result, dict)
        or set(result) != result_keys
        or result.get("schema") != F1_RESULT_SCHEMA
        or result.get("run_id") != f1_run_id
        or result.get("manifest_sha256") != manifest_bound.sha256
        or result.get("status") not in allowed_status
        or type(result.get("candidate_transfer_count")) is not int
        or result.get("candidate_transfer_count") != 1
        or result.get("candidate_transfer_uncertain") is not False
        or result.get("candidate_replay") is not False
        or type(result.get("rollback_transfer_count")) is not int
        or result.get("rollback_transfer_count") != 1
        or result.get("final_health_restored") is not True
        or (
            result.get("debian_pid1_proven"),
            result.get("display_acquisition_proven"),
        )
        != status_facts.get(result.get("status"))
        or result.get("timeline_events") != list(F1_TIMELINE_EVENTS)
    ):
        raise ContractError("closed F1 does not prove one candidate and rollback")

    by_action = {name: records[actions.index(name)] for name in required_order}
    if (
        by_action["preflight"].get("candidate_sha256") != candidate_sha
        or by_action["preflight"].get("rollback_sha256")
        != EXPECTED_ROLLBACK_SHA256
        or by_action["candidate-transfer-started"].get("candidate_sha256")
        != candidate_sha
        or by_action["candidate-transfer-started"].get("candidate_replay")
        is not False
        or by_action["candidate-flashed"].get("candidate_sha256")
        != candidate_sha
        or type(
            by_action["candidate-flashed"].get("candidate_transfer_count")
        )
        is not int
        or by_action["candidate-flashed"].get("candidate_transfer_count") != 1
        or by_action["candidate-flashed"].get("candidate_replay") is not False
        or by_action["rollback-transfer-started"].get("rollback_sha256")
        != EXPECTED_ROLLBACK_SHA256
        or by_action["rollback-transfer-started"].get("candidate_replay")
        is not False
        or by_action["rollback-flashed"].get("rollback_sha256")
        != EXPECTED_ROLLBACK_SHA256
        or type(by_action["rollback-flashed"].get("rollback_transfer_count"))
        is not int
        or by_action["rollback-flashed"].get("rollback_transfer_count") != 1
        or by_action["rollback-flashed"].get("candidate_replay") is not False
        or by_action["rollback-boot-ready"].get("rollback_version")
        != EXPECTED_VERSION
        or by_action["rollback-boot-ready"].get("rollback_build")
        != EXPECTED_BUILD
        or by_action["rollback-boot-ready"].get("selftest_fail_zero") is not True
    ):
        raise ContractError("closed F1 transfer identities are not exact")

    candidate_ready = by_action["candidate-boot-ready"]
    candidate_health = require_dict(
        candidate_ready.get("health"),
        "candidate health",
    )
    candidate_version_text = protocol_text(
        candidate_health.get("version"),
        "version",
        "candidate version",
    )
    candidate_selftest_text = protocol_text(
        candidate_health.get("selftest"),
        "selftest",
        "candidate selftest",
    )
    candidate_version_re = re.compile(
        rf"^version: {re.escape(candidate_version)} "
        rf"build={re.escape(candidate_build)}\r?$",
        re.MULTILINE,
    )
    if (
        candidate_ready.get("candidate_version") != candidate_version
        or candidate_ready.get("candidate_build") != candidate_build
        or candidate_ready.get("selftest_fail_zero") is not True
        or candidate_health.get("exact_bridge") is not True
        or candidate_health.get("selected_realpath") != selected_realpath
        or len(candidate_version_re.findall(candidate_version_text)) != 1
        or len(SELFTEST_RE.findall(candidate_selftest_text)) != 1
    ):
        raise ContractError("closed F1 candidate health is not exact")

    final_health = by_action["health-verified"]
    baseline = require_dict(final_health.get("baseline"), "final baseline")
    version_text = protocol_text(
        baseline.get("version"),
        "version",
        "final version",
    )
    selftest_text = protocol_text(
        baseline.get("selftest"),
        "selftest",
        "final selftest",
    )
    status_text = protocol_text(
        baseline.get("status"),
        "status",
        "final status",
    )
    if (
        final_health.get("version") != EXPECTED_VERSION
        or final_health.get("build") != EXPECTED_BUILD
        or final_health.get("exact_bridge") is not True
        or final_health.get("selected_realpath") != selected_realpath
        or final_health.get("selftest_fail_zero") is not True
        or final_health.get("pstore_entries_zero") is not True
        or len(VERSION_RE.findall(version_text)) != 1
        or len(SELFTEST_RE.findall(selftest_text)) != 1
        or len(PSTORE_ZERO_RE.findall(status_text)) != 1
    ):
        raise ContractError("closed F1 final V2321 health is not exact")

    closed = by_action["closed"]
    closed_payload = {
        key: item
        for key, item in closed.items()
        if key not in {"action", "sequence", "state", "timestamp_utc"}
    }
    closed_payload["schema"] = F1_RESULT_SCHEMA
    if closed_payload != result:
        raise ContractError("closed F1 journal payload and result differ")
    return manifest_bound, result_bound, tuple(journal)


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
    d0_run_id = require_string(d0_value.get("run_id"), "connected_d0.run_id")
    d0_match = re.fullmatch(
        rf"{re.escape(f1_run_id)}-connected-d0-(?P<sequence>[0-9]{{2}})",
        d0_run_id,
    )
    expected_f1_root = (PRIVATE_RUN_BASE / f1_run_id).resolve()
    expected_d0_path = (
        expected_f1_root / f"connected-d0-{d0_match.group('sequence')}.json"
        if d0_match is not None
        else None
    )
    preflight_sha, preflight_stat = hash_open_regular(CONNECTED_PREFLIGHT)
    if (
        d0_value.get("schema") != "a90-v3403-connected-d0-v1"
        or d0_value.get("outcome")
        != (
            "PASS_A90_V3403_CONNECTED_READ_ONLY_"
            "AWAITING_STAGING_CONTRACT_AND_F1_MANIFEST"
        )
        or d0_match is None
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
    source_disposition = adjacent.get("source_disposition", SOURCE_ABSENT)
    if source_disposition not in {SOURCE_ABSENT, SOURCE_EXACT_PRESERVED}:
        raise ContractError("adjacent source disposition is not exact")
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
        or (
            source_disposition == SOURCE_EXACT_PRESERVED
            and authority.get("source_preservation_required") is not True
        )
    ):
        raise ContractError("manifest authority contract mismatch")
    independent_review = (
        validate_independent_review_binding(manifest.get("independent_review"))
        if source_disposition == SOURCE_EXACT_PRESERVED
        else None
    )
    if source_disposition == SOURCE_EXACT_PRESERVED:
        if connected_d0.path != expected_d0_path:
            raise ContractError("source-preserved D0 path is not exact")
        closed_manifest, closed_result, closed_journal = (
            validate_closed_f1_binding(manifest.get("closed_f1"), f1_run_id)
        )
        closed_value = json.loads(
            closed_journal[-1].path.read_text(encoding="utf-8")
        )
        if parse_utc(
            d0_value.get("timestamp_utc"),
            "connected D0 timestamp",
        ) <= parse_utc(
            closed_value.get("timestamp_utc"),
            "closed F1 timestamp",
        ):
            raise ContractError("connected D0 is not fresh after the closed F1")
    else:
        closed_manifest = None
        closed_result = None
        closed_journal = ()
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
        source_disposition=source_disposition,
        stage_path=stage_path,
        independent_review=independent_review,
        closed_f1_manifest=closed_manifest,
        closed_f1_result=closed_result,
        closed_f1_journal=closed_journal,
    )


def approval_binding(spec: CleanupSpec) -> dict[str, Any]:
    binding = {
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
        "source_disposition": spec.source_disposition,
        "host_preservation_sha256": spec.host_copy.sha256,
        "independent_review_sha256": (
            spec.independent_review.sha256
            if spec.independent_review is not None
            else None
        ),
        "read_timeout_sec": int(READ_TIMEOUT_SEC),
        "cleanup_timeout_sec": int(CLEANUP_TIMEOUT_SEC),
        "single_unlink_dispatch": True,
        "unlink_retry_forbidden": True,
    }
    if spec.source_disposition == SOURCE_EXACT_PRESERVED:
        if (
            spec.independent_review is None
            or spec.closed_f1_manifest is None
            or spec.closed_f1_result is None
            or not spec.closed_f1_journal
        ):
            raise ContractError("source-preserved cleanup evidence is absent")
        binding.update(
            {
                "source_disposition": SOURCE_EXACT_PRESERVED,
                "protected_source_path": spec.source_path,
                "independent_review_sha256": spec.independent_review.sha256,
                "closed_f1_manifest_sha256": spec.closed_f1_manifest.sha256,
                "closed_f1_result_sha256": spec.closed_f1_result.sha256,
                "closed_f1_journal_sha256": [
                    item.sha256 for item in spec.closed_f1_journal
                ],
            }
        )
    return binding


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
        'p="$1"; src="$2"; stage="$3"; expected="$4"; disposition="$5"; '
        '[ ! -L "$p" ] || exit 20; '
        '[ -f "$p" ] || exit 21; '
        'meta=$(/bin/busybox stat -c "%F|%s|%a|%h" "$p") || exit 22; '
        '[ "$meta" = "regular file|2147483648|600|1" ] || exit 23; '
        'actual=$(/bin/busybox sha256sum "$p") || exit 24; '
        'actual=${actual%% *}; [ "$actual" = "$expected" ] || exit 25; '
        'case "$disposition" in '
        'absent) [ ! -e "$src" ] && [ ! -L "$src" ] || exit 26; '
        'source_state=absent ;; '
        'exact-preserved) '
        '[ ! -L "$src" ] && [ -f "$src" ] || exit 30; '
        'srcmeta=$(/bin/busybox stat -c "%F|%s|%a|%h" "$src") || exit 31; '
        '[ "$srcmeta" = "regular file|2147483648|600|1" ] || exit 32; '
        'srcactual=$(/bin/busybox sha256sum "$src") || exit 33; '
        'srcactual=${srcactual%% *}; [ "$srcactual" = "$expected" ] || exit 34; '
        '[ "$(/bin/busybox stat -c %d:%i "$src")" != '
        '"$(/bin/busybox stat -c %d:%i "$p")" ] || exit 35; '
        'source_state=exact ;; '
        '*) exit 36 ;; esac; '
        '[ ! -e "$stage" ] && [ ! -L "$stage" ] || exit 26; '
        '! /bin/busybox grep -F "$p" /proc/mounts >/dev/null 2>&1 || exit 27; '
        '! /bin/busybox grep -F "$src" /proc/mounts >/dev/null 2>&1 || exit 37; '
        'for b in /sys/block/loop*/loop/backing_file; do '
        '[ -r "$b" ] || continue; '
        'v=$(/bin/busybox cat "$b") || exit 28; '
        '[ "$v" != "$p" ] && [ "$v" != "$src" ] || exit 29; '
        'done; '
        'printf "work=exact source=%s stage=absent in_use=no\\n" "$source_state"'
    )


def cleanup_script() -> str:
    return (
        'p="$1"; expected="$2"; src="$3"; stage="$4"; disposition="$5"; '
        '[ ! -L "$p" ] || exit 40; '
        '[ -f "$p" ] || exit 41; '
        'meta=$(/bin/busybox stat -c "%F|%s|%a|%h" "$p") || exit 42; '
        '[ "$meta" = "regular file|2147483648|600|1" ] || exit 43; '
        'actual=$(/bin/busybox sha256sum "$p") || exit 44; '
        'actual=${actual%% *}; [ "$actual" = "$expected" ] || exit 45; '
        'case "$disposition" in '
        'absent) [ ! -e "$src" ] && [ ! -L "$src" ] || exit 46; '
        'source_state=absent ;; '
        'exact-preserved) '
        '[ ! -L "$src" ] && [ -f "$src" ] || exit 60; '
        'srcmeta=$(/bin/busybox stat -c "%F|%s|%a|%h" "$src") || exit 61; '
        '[ "$srcmeta" = "regular file|2147483648|600|1" ] || exit 62; '
        'srcactual=$(/bin/busybox sha256sum "$src") || exit 63; '
        'srcactual=${srcactual%% *}; [ "$srcactual" = "$expected" ] || exit 64; '
        '[ "$(/bin/busybox stat -c %d:%i "$src")" != '
        '"$(/bin/busybox stat -c %d:%i "$p")" ] || exit 65; '
        'source_state=exact ;; '
        '*) exit 66 ;; esac; '
        '[ ! -e "$stage" ] && [ ! -L "$stage" ] || exit 46; '
        '! /bin/busybox grep -F "$p" /proc/mounts >/dev/null 2>&1 || exit 47; '
        '! /bin/busybox grep -F "$src" /proc/mounts >/dev/null 2>&1 || exit 67; '
        'for b in /sys/block/loop*/loop/backing_file; do '
        '[ -r "$b" ] || continue; '
        'v=$(/bin/busybox cat "$b") || exit 48; '
        '[ "$v" != "$p" ] && [ "$v" != "$src" ] || exit 49; '
        'done; '
        '/bin/busybox rm -- "$p" || exit 50; '
        '[ ! -e "$p" ] || exit 51; '
        'if [ "$disposition" = exact-preserved ]; then '
        'srcactual=$(/bin/busybox sha256sum "$src") || exit 68; '
        'srcactual=${srcactual%% *}; [ "$srcactual" = "$expected" ] || exit 69; '
        'fi; '
        'printf "work=unlinked source=%s\\n" "$source_state"'
    )


def presence_script() -> str:
    return (
        'p="$1"; src="$2"; stage="$3"; expected="$4"; disposition="$5"; '
        'if [ -e "$p" ] || [ -L "$p" ]; then w=present; else w=absent; fi; '
        'if [ "$disposition" = exact-preserved ]; then '
        'if [ ! -L "$src" ] && [ -f "$src" ] && '
        '[ "$(/bin/busybox stat -c "%F|%s|%a|%h" "$src")" = '
        '"regular file|2147483648|600|1" ] && '
        '[ "$(/bin/busybox sha256sum "$src" | /bin/busybox cut -d" " -f1)" '
        '= "$expected" ]; then s=exact; else s=invalid; fi; '
        'elif [ -e "$src" ] || [ -L "$src" ]; then s=present; else s=absent; fi; '
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
            spec.source_disposition,
        ],
    )
    text = require_protocol_ok(result, "work-image preflight")
    expected_source = (
        "exact"
        if spec.source_disposition == SOURCE_EXACT_PRESERVED
        else "absent"
    )
    if text.count(
        f"work=exact source={expected_source} stage=absent in_use=no"
    ) != 1:
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
            spec.work_sha256,
            spec.source_disposition,
        ],
    )
    text = require_protocol_ok(result, "post-cleanup presence")
    states = re.findall(
        r"work=(absent|present) source=(absent|exact|invalid|present) "
        r"stage=(absent|present)",
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
    operator_attended: bool,
    host: str,
    port: int,
    read_timeout: float,
    cleanup_timeout: float,
) -> dict[str, Any]:
    if operator_attended is not True:
        raise ContractError("live cleanup requires awake attended operator presence")
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
        "source_disposition": spec.source_disposition,
        "protected_source_path": (
            spec.source_path
            if spec.source_disposition == SOURCE_EXACT_PRESERVED
            else None
        ),
        "operator_attended": True,
        "physical_recovery_available": True,
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
                spec.source_disposition,
            ],
        )
        text = require_protocol_ok(result, "cleanup dispatch")
        expected_source = (
            "exact"
            if spec.source_disposition == SOURCE_EXACT_PRESERVED
            else "absent"
        )
        response_proven = (
            text.count(f"work=unlinked source={expected_source}") == 1
        )
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
    expected_source = (
        "exact"
        if spec.source_disposition == SOURCE_EXACT_PRESERVED
        else "absent"
    )
    effect_proven = (
        presence["work"] == "absent"
        and presence["source"] == expected_source
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
        "source_disposition": spec.source_disposition,
        "protected_source_preserved": (
            presence["source"] == "exact"
            if spec.source_disposition == SOURCE_EXACT_PRESERVED
            else None
        ),
        "operator_attended": True,
        "physical_recovery_available": True,
        "device_write": True,
        "deleted_path": WORK_PATH if effect_proven else None,
        "flash": False,
        "reboot_requested": False,
        "payload_sent": False,
        "other_device_commands": 0,
    }
    write_private_json_exclusive(transaction_dir / "result.json", result_value)
    return result_value


def bound_dict(bound: BoundFile) -> dict[str, Any]:
    return {
        "path": str(bound.path),
        "size": bound.size,
        "sha256": bound.sha256,
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_ID_RE.fullmatch(args.run_id) is None:
        raise ContractError("cleanup run_id is not exact")
    match = F1_RUN_ID_RE.fullmatch(args.f1_run_id)
    if match is None:
        raise ContractError("F1 run_id is not exact")
    if args.source_disposition != SOURCE_EXACT_PRESERVED:
        raise ContractError("builder supports only source-preserved recovery")
    run_dir = (PRIVATE_RUN_BASE / args.run_id).resolve()
    if run_dir.exists() or run_dir.is_symlink():
        raise ContractError("cleanup run directory must be absent")

    connected = load_bound(
        {
            "path": str(args.connected_d0),
            "size": args.connected_d0.resolve(strict=True).stat().st_size,
            "sha256": validate_sha256(
                args.expect_connected_d0_sha256,
                "connected D0 sha256",
            ),
        },
        "connected_d0",
    )
    require_private_regular(connected.path)
    connected_value = json.loads(connected.path.read_text(encoding="utf-8"))
    target_value = require_dict(connected_value.get("target"), "connected target")
    connected_run_id = connected_value.get("run_id")
    connected_match = re.fullmatch(
        rf"{re.escape(args.f1_run_id)}-connected-d0-(?P<sequence>[0-9]{{2}})",
        connected_run_id if isinstance(connected_run_id, str) else "",
    )
    if (
        connected_match is None
        or connected.path
        != (
            PRIVATE_RUN_BASE
            / args.f1_run_id
            / f"connected-d0-{connected_match.group('sequence')}.json"
        ).resolve(strict=True)
    ):
        raise ContractError("connected D0 does not select the F1 run")

    host_path = args.host_preservation.resolve(strict=True)
    host_sha = validate_sha256(args.expect_work_sha256, "work sha256")
    host_copy = load_bound(
        {
            "path": str(host_path),
            "size": host_path.stat().st_size,
            "sha256": host_sha,
        },
        "host_preservation",
    )
    require_private_regular(host_copy.path)
    if host_copy.size != WORK_SIZE:
        raise ContractError("host preservation size is not exact")

    review_path = args.review_report.resolve(strict=True)
    review_bound = validate_independent_review_binding(
        {
            "path": str(review_path),
            "size": review_path.stat().st_size,
            "sha256": validate_sha256(
                args.expect_review_report_sha256,
                "review report sha256",
            ),
        }
    )
    f1_root = (PRIVATE_RUN_BASE / args.f1_run_id).resolve(strict=True)
    f1_live = f1_root / "f1-live"
    journal_paths = sorted((f1_live / "journal").glob("*.json"))
    closed_f1 = {
        "manifest": bound_dict(current_bound(f1_root / "prepared-manifest.json")),
        "result": bound_dict(current_bound(f1_live / "result.json")),
        "journal": [bound_dict(current_bound(path)) for path in journal_paths],
    }
    runner = current_bound(Path(__file__).resolve())
    transport = current_bound(A90CTL_SOURCE)
    suffix = match.group("suffix")
    source_path = (
        "/mnt/sdext/a90/runtime/"
        f"debian-bookworm-arm64-phase2-display-v3406-keyed-{suffix}.img"
    )
    stage_path = f"/mnt/sdext/a90/runtime/.a90-stage-{args.f1_run_id}"
    bridge_realpath = require_string(
        target_value.get("bridge_selected_realpath"),
        "connected bridge realpath",
    )
    manifest = {
        "schema": SCHEMA,
        "status": STATUS,
        "run_id": args.run_id,
        "f1_run_id": args.f1_run_id,
        "runner": bound_dict(runner),
        "transport": bound_dict(transport),
        "connected_d0": bound_dict(connected),
        "independent_review": bound_dict(review_bound),
        "closed_f1": closed_f1,
        "target": {
            "profile": "galaxy-a90-5g-native-init",
            "bridge_device": target_value.get("bridge_device"),
            "bridge_realpath_sha256": hashlib.sha256(
                bridge_realpath.encode("utf-8")
            ).hexdigest(),
            "usb_serial_sha256": target_value.get("usb_serial_sha256"),
            "expected_vendor_product": EXPECTED_VENDOR_PRODUCT,
            "expected_version": EXPECTED_VERSION,
            "expected_build": EXPECTED_BUILD,
        },
        "work_image": {
            "device_path": WORK_PATH,
            "size": WORK_SIZE,
            "mode": WORK_MODE,
            "sha256": host_sha,
            "host_preservation": bound_dict(host_copy),
        },
        "adjacent_paths": {
            "v3406_source": source_path,
            "source_disposition": SOURCE_EXACT_PRESERVED,
            "run_stage": stage_path,
        },
        "authority": {
            "device_write_authorized": False,
            "fresh_exact_approval_required": True,
            "single_unlink_dispatch": True,
            "unlink_retry_forbidden": True,
            "source_preservation_required": True,
        },
    }
    output = run_dir / "manifest.json"
    write_private_json_exclusive(output, manifest)
    manifest_sha = hashlib.sha256(output.read_bytes()).hexdigest()
    spec = load_manifest(output, manifest_sha)
    return {
        **inspect(spec),
        "mode": "host-only-manifest-build",
        "manifest": {
            "path": str(output),
            "size": output.stat().st_size,
            "sha256": manifest_sha,
        },
    }


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
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--build-manifest", action="store_true")
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--execute-approved-cleanup", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--f1-run-id")
    parser.add_argument("--connected-d0", type=Path)
    parser.add_argument("--expect-connected-d0-sha256")
    parser.add_argument("--host-preservation", type=Path)
    parser.add_argument("--expect-work-sha256")
    parser.add_argument(
        "--source-disposition",
        choices=(SOURCE_EXACT_PRESERVED,),
    )
    parser.add_argument("--review-report", type=Path)
    parser.add_argument("--expect-review-report-sha256")
    parser.add_argument("--approval")
    parser.add_argument("--transaction-dir", type=Path)
    parser.add_argument(
        "--operator-attended",
        action="store_true",
        help=(
            "assert that the operator is awake at the A90 and can enter "
            "Download or TWRP now"
        ),
    )
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
    build_inputs = (
        "run_id",
        "f1_run_id",
        "connected_d0",
        "expect_connected_d0_sha256",
        "host_preservation",
        "expect_work_sha256",
        "source_disposition",
        "review_report",
        "expect_review_report_sha256",
    )
    if args.build_manifest:
        if args.manifest is not None or args.expect_manifest_sha256 is not None:
            raise ContractError("manifest build accepts no existing manifest")
        missing = [name for name in build_inputs if getattr(args, name) is None]
        if missing:
            raise ContractError(f"manifest build inputs are missing: {missing}")
        if (
            args.approval is not None
            or args.transaction_dir is not None
            or args.operator_attended
        ):
            raise ContractError("manifest build accepts no live arguments")
        value = build_manifest(args)
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    if any(getattr(args, name) is not None for name in build_inputs):
        raise ContractError("non-build mode accepts no manifest-build inputs")
    if args.manifest is None or args.expect_manifest_sha256 is None:
        raise ContractError("manifest and exact hash are required")
    spec = load_manifest(args.manifest, args.expect_manifest_sha256)
    if args.prepare_approval:
        if (
            args.approval is not None
            or args.transaction_dir is not None
            or args.operator_attended
        ):
            raise ContractError("approval preparation accepts no live arguments")
        value = prepare_approval(spec)
    elif args.execute_approved_cleanup:
        if args.approval is None or args.transaction_dir is None:
            raise ContractError("live cleanup requires approval and transaction directory")
        if not args.operator_attended:
            raise ContractError("live cleanup requires --operator-attended")
        value = execute_cleanup(
            spec,
            args.approval,
            args.transaction_dir,
            operator_attended=args.operator_attended,
            host=args.bridge_host,
            port=args.bridge_port,
            read_timeout=args.read_timeout,
            cleanup_timeout=args.cleanup_timeout,
        )
    else:
        if (
            args.approval is not None
            or args.transaction_dir is not None
            or args.operator_attended
        ):
            raise ContractError("host inspection accepts no live arguments")
        value = inspect(spec)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
