#!/usr/bin/env python3
"""One-shot A90 retained-work cleanup and immutable D1 baseline reducer.

The original preserved resident-install terminal is intentionally not a D1
baseline.  This runner first records a fresh read-only proof of that exact
terminal and its protected source/work files, then permits one attended unlink
of only the fixed work path.  A second read-only proof must establish exact
resident health, exact source bytes, and absent work before the host-only
reducer can emit the sole D1 baseline.

An unlink dispatch is never repeated.  A missing or malformed response is
reconciled only with bounded reads.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_phase3_d1_observer_v1 as phase3_observer  # noqa: E402
import a90_resident_existing_rootfs_install_v1 as preserved  # noqa: E402
import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402
import a90_v3405_retained_work_cleanup as cleanup  # noqa: E402


CAPABILITY = "A90_RESIDENT_PRESERVED_WORK_CLEANUP_AND_D1_BASELINE_V1"
CLEANUP_SCHEMA = "a90_resident_preserved_work_cleanup_manifest_v1"
CLEANUP_STATUS = "ready-for-attended-cleanup"
PRE_D0_SCHEMA = "a90_resident_preserved_work_pre_cleanup_d0_v1"
POST_D0_SCHEMA = "a90_resident_preserved_work_post_cleanup_d0_v1"
RESULT_SCHEMA = "a90_resident_preserved_work_cleanup_result_v1"
BASELINE_SCHEMA = "a90_resident_preserved_d1_baseline_v1"
BASELINE_STATUS = "ready-for-d1-manifest-reduction"
REVIEW_SCHEMA = "a90-resident-preserved-d1-prep-independent-review-v1"
APPROVAL_SCHEMA = "a90_resident_preserved_work_cleanup_approval_v1"
APPROVAL_PREFIX = "A90-RESIDENT-WORK-CLEANUP-V1-APPROVE:"
RUN_RE = re.compile(r"^a90-resident-work-cleanup-[0-9]{8}-[0-9]{2}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
PRIVATE_ROOT = (REPO_ROOT / "workspace/private").resolve()
PRIVATE_RUN_BASE = (PRIVATE_ROOT / "runs/server-distro").resolve()
WORK_PATH = str(staging.REMOTE_WORK)
IMAGE_SIZE = preserved.IMAGE_SIZE
FILE_MODE = preserved.FILE_MODE
FILE_NLINK = preserved.FILE_NLINK
EXPECTED_VERSION = preserved.CANDIDATE_VERSION
EXPECTED_BUILD = preserved.CANDIDATE_BUILD
HANDOFF_TIMEOUT_SEC = 1200
SSH_MARKER_TIMEOUT_SEC = 120
CANDIDATE_RETURN_TIMEOUT_SEC = 240
MAX_CMDV1X_WIRE_BYTES = preserved.MAX_CMDV1X_WIRE_BYTES
HISTORICAL_CLEANUP_RUN_ID = "a90-resident-work-cleanup-20260804-01"
HISTORICAL_CLEANUP_MANIFEST_SHA256 = (
    "aea5afb0c8de8dd52e5fe31e8c99c4625860ee0f6ac8d716e7dda86f7855ac6c"
)
HISTORICAL_BASELINE_SHA256 = (
    "492226307a39990b6cc9be5fae05f1c8e07e399343b8428d6dc7f8223aade396"
)
HISTORICAL_REVIEW_PATH = (
    REPO_ROOT
    / "docs/reports/"
    "A90_RESIDENT_PRESERVED_D1_PREP_INDEPENDENT_REVIEW_2026-08-04.json"
).resolve()
HISTORICAL_REVIEW_SHA256 = (
    "02682119e036df24f0fe463eeeec1d3ec83f2dbf626406d35ab5c1ff27ce5221"
)

SOURCE_PATHS = {
    "repository_contract": REPO_ROOT / "AGENTS.md",
    "target_contract": REPO_ROOT
    / "docs/operations/targets/A90_TARGET_CONTRACT.md",
    "prep_runner": Path(__file__).resolve(),
    "d1_runner": SCRIPT_DIR / "a90_transition_d1_session_v1.py",
    "preserved_install_runner": Path(preserved.__file__).resolve(),
    "retained_work_cleanup_helper": Path(cleanup.__file__).resolve(),
    "f1_orchestrator": Path(base.__file__).resolve(),
    "staging_contract": Path(staging.__file__).resolve(),
    "resident_health_validator": Path(preserved.resident.__file__).resolve(),
    "phase3_observer": Path(phase3_observer.__file__).resolve(),
    "transition_engine": SCRIPT_DIR / "a90_transition_engine_v2.py",
    "transition_contract": REVAL_DIR / "a90_transition_contract_v2.py",
    "observation_pipeline": REVAL_DIR / "a90_observation_pipeline.py",
    "display_observer": SCRIPT_DIR / "a90_phase2d_display_observer.py",
    "cmdv1_shell_adapter": SCRIPT_DIR / "run_d1_chroot_mvp.py",
    "cdc_acm_guard": REVAL_DIR / "device_action_cdc_acm_observer_v1.py",
    "workspace_bootstrap": REVAL_DIR / "_workspace_bootstrap.py",
    "a90ctl": REVAL_DIR / "a90ctl.py",
    "bridge_selector": REVAL_DIR / "a90_bridge.py",
    "serial_lock": REVAL_DIR / "a90_serial_lock.py",
    "serial_bridge": REVAL_DIR / "serial_tcp_bridge.py",
}


class ContractError(RuntimeError):
    """Raised before widening or repeating the fixed cleanup effect."""


@dataclass(frozen=True)
class Bound:
    path: Path
    size: int
    sha256: str


@dataclass(frozen=True)
class ResidentEvidence:
    run_id: str
    manifest: Bound
    result: Bound
    journal: tuple[Bound, ...]
    value: dict[str, Any]
    result_value: dict[str, Any]
    spec: Any
    candidate: Bound
    rollback: Bound
    source_host: Bound
    work_host: Bound
    observer_key: Bound
    observer_public_key: Bound


@dataclass(frozen=True)
class CleanupSpec:
    manifest: Bound
    run_id: str
    resident: ResidentEvidence
    pre_d0: Bound
    review: Bound
    closure: dict[str, Bound]


@dataclass(frozen=True)
class BaselineSpec:
    manifest: Bound
    run_id: str
    resident_run_id: str
    resident_manifest: Bound
    resident_result: Bound
    resident_journal: tuple[Bound, ...]
    cleanup_manifest: Bound
    cleanup_result: Bound
    post_cleanup_d0: Bound
    candidate: Bound
    rollback: Bound
    rootfs: Bound
    remote_final: str
    remote_work: str
    candidate_version: str
    candidate_build: str
    bridge_device: str
    bridge_realpath: str
    recovery_serial_sha256: str
    recovery_profile: str
    observer_key: Bound
    observer_public_key_sha256: str
    observer_device: str
    observer_port: int
    observer_host_ncm_profile: str
    handoff_command: tuple[str, ...]
    handoff_timeout: int
    ssh_marker_timeout: int
    candidate_return_timeout: int
    review: Bound
    closure: dict[str, Bound]


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _utc(value: Any, label: str) -> dt.datetime:
    if not base.is_canonical_utc_timestamp(value):
        raise ContractError(f"{label} is not canonical UTC")
    return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.UTC
    )


def _sha256(path: Path) -> str:
    return staging.sha256_file(path)


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a nonempty string")
    return value


def _sha(value: Any, label: str) -> str:
    value = _string(value, label)
    if HEX64_RE.fullmatch(value) is None:
        raise ContractError(f"{label} must be lowercase SHA256")
    return value


def _bound(path: Path, *, private: bool) -> Bound:
    if path.is_symlink():
        raise ContractError(f"bound path is a symlink: {path}")
    resolved = path.resolve(strict=True)
    info = resolved.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ContractError(f"bound path is not regular: {resolved}")
    root = PRIVATE_ROOT if private else REPO_ROOT.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ContractError(f"bound path is outside its allowed root: {resolved}")
    return Bound(resolved, info.st_size, _sha256(resolved))


def _bound_value(item: Bound) -> dict[str, Any]:
    return {"path": str(item.path), "size": item.size, "sha256": item.sha256}


def _load_bound(value: Any, label: str, *, private: bool) -> Bound:
    item = _dict(value, label)
    if set(item) != {"path", "size", "sha256"}:
        raise ContractError(f"{label} binding shape changed")
    actual = _bound(Path(_string(item.get("path"), f"{label}.path")), private=private)
    if actual.size != item.get("size") or actual.sha256 != _sha(
        item.get("sha256"), f"{label}.sha256"
    ):
        raise ContractError(f"{label} size/hash changed")
    return actual


def _read(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} JSON is invalid") from exc
    return _dict(value, label)


def _write(path: Path, value: dict[str, Any]) -> None:
    staging.write_private_json_exclusive(path, value)


def _closure() -> dict[str, Bound]:
    return {role: _bound(path, private=False) for role, path in SOURCE_PATHS.items()}


def review_source_records() -> dict[str, dict[str, Any]]:
    return {role: _bound_value(item) for role, item in _closure().items()}


def _load_review(value: Any) -> Bound:
    bound = _load_bound(value, "independent review", private=False)
    reports = (REPO_ROOT / "docs/reports").resolve(strict=True)
    if not bound.path.is_relative_to(reports) or bound.path.stat().st_mode & 0o022:
        raise ContractError("independent review path or permissions changed")
    report = _read(bound.path, "independent review")
    if (
        report.get("schema") != REVIEW_SCHEMA
        or report.get("status") != "PASS_GO"
        or report.get("capabilities")
        != [
            "attended-fixed-work-unlink-one-shot",
            "preserved-terminal-to-d1-baseline-reducer",
        ]
        or report.get("unresolved_findings") != []
        or report.get("permanent_boundaries_unchanged") is not True
        or report.get("device_authority_granted") is not False
        or report.get("named_execution_critical_closure")
        != review_source_records()
    ):
        raise ContractError("independent review is not exact PASS_GO")
    return bound


def _recorded_closure(value: Any) -> dict[str, Bound]:
    records = _dict(value, "recorded execution closure")
    if set(records) != set(SOURCE_PATHS):
        raise ContractError("recorded execution closure roles changed")
    result: dict[str, Bound] = {}
    for role, expected_path in SOURCE_PATHS.items():
        item = _dict(records.get(role), f"recorded closure {role}")
        path = Path(_string(item.get("path"), f"recorded closure {role}.path"))
        size = item.get("size")
        digest = _sha(item.get("sha256"), f"recorded closure {role}.sha256")
        if (
            set(item) != {"path", "size", "sha256"}
            or path != expected_path.resolve(strict=True)
            or type(size) is not int
            or size <= 0
        ):
            raise ContractError(f"recorded execution closure role changed: {role}")
        result[role] = Bound(path, size, digest)
    return result


def _load_historical_review(value: Any, closure_value: Any) -> tuple[Bound, dict[str, Bound]]:
    """Validate a closed action against its immutable reviewed-time closure."""

    closure = _recorded_closure(closure_value)
    bound = _load_bound(value, "historical independent review", private=False)
    reports = (REPO_ROOT / "docs/reports").resolve(strict=True)
    if (
        not bound.path.is_relative_to(reports)
        or bound.path.stat().st_mode & 0o022
        or bound.path != HISTORICAL_REVIEW_PATH
        or bound.sha256 != HISTORICAL_REVIEW_SHA256
    ):
        raise ContractError("historical independent review path changed")
    report = _read(bound.path, "historical independent review")
    if (
        report.get("schema") != REVIEW_SCHEMA
        or report.get("status") != "PASS_GO"
        or report.get("capabilities")
        != [
            "attended-fixed-work-unlink-one-shot",
            "preserved-terminal-to-d1-baseline-reducer",
        ]
        or report.get("unresolved_findings") != []
        or report.get("permanent_boundaries_unchanged") is not True
        or report.get("device_authority_granted") is not False
        or report.get("named_execution_critical_closure") != closure_value
    ):
        raise ContractError("historical independent review is not exact PASS_GO")
    return bound, closure


def _make_live_spec(
    manifest: dict[str, Any],
    manifest_bound: Bound,
    candidate: Bound,
    rollback: Bound,
) -> Any:
    target = _dict(manifest.get("target"), "resident target")
    protected = _dict(manifest.get("protected_rootfs"), "protected rootfs")
    source = _dict(protected.get("source"), "protected source")
    observer = _dict(manifest.get("observer"), "resident observer")
    execution = _dict(manifest.get("execution_closure"), "resident execution closure")
    orchestrator = _dict(execution.get("orchestrator"), "resident orchestrator")
    return SimpleNamespace(
        manifest=manifest,
        candidate=SimpleNamespace(sha256=candidate.sha256),
        rollback=SimpleNamespace(sha256=rollback.sha256),
        candidate_version=EXPECTED_VERSION,
        candidate_build=EXPECTED_BUILD,
        rollback_version=preserved.ROLLBACK_VERSION,
        rollback_build=preserved.ROLLBACK_BUILD,
        observer_host_ncm_profile=_string(
            observer.get("host_ncm_profile"), "observer host NCM profile"
        ),
        orchestrator_sha256=_sha(orchestrator.get("sha256"), "orchestrator SHA256"),
        stage=SimpleNamespace(
            run_id=_string(manifest.get("run_id"), "resident run_id"),
            manifest_sha256=manifest_bound.sha256,
            remote_stage_dir=_string(protected.get("stage_path"), "stage path"),
            bridge_device=_string(target.get("bridge_device"), "bridge device"),
            bridge_realpath=_string(
                target.get("bridge_selected_realpath"), "bridge realpath"
            ),
            local_size=source.get("size"),
            local_sha256=_sha(source.get("sha256"), "source SHA256"),
            remote_final=_string(source.get("device_path"), "source path"),
            remote_work=WORK_PATH,
        ),
    )


def load_resident_evidence(path: Path, expected_sha256: str) -> ResidentEvidence:
    manifest = _bound(path, private=True)
    if manifest.sha256 != _sha(expected_sha256, "resident manifest SHA256"):
        raise ContractError("resident manifest SHA256 mismatch")
    value = _read(manifest.path, "resident manifest")
    run_id = _string(value.get("run_id"), "resident run_id")
    if (
        value.get("schema") != preserved.MANIFEST_SCHEMA
        or value.get("status") != staging.FINAL_MANIFEST_STATUS
        or value.get("capability") != preserved.CAPABILITY
        or preserved.RUN_RE.fullmatch(run_id) is None
        or manifest.path
        != (PRIVATE_RUN_BASE / run_id / "resident-existing-rootfs-preserved-manifest.json").resolve(strict=True)
    ):
        raise ContractError("resident manifest is not the exact preserved terminal source")

    candidate_value = _dict(value.get("candidate_boot"), "candidate boot")
    rollback_value = _dict(value.get("rollback_boot"), "rollback boot")
    candidate = _load_bound(
        {key: candidate_value.get(key) for key in ("path", "size", "sha256")},
        "candidate boot",
        private=True,
    )
    rollback = _load_bound(
        {key: rollback_value.get(key) for key in ("path", "size", "sha256")},
        "rollback boot",
        private=True,
    )
    protected = _dict(value.get("protected_rootfs"), "protected rootfs")
    source = _dict(protected.get("source"), "protected source")
    work = _dict(protected.get("work"), "protected work")
    source_host = _load_bound(source.get("host_preservation"), "source host", private=True)
    work_host = _load_bound(work.get("host_preservation"), "work host", private=True)
    target = _dict(value.get("target"), "resident target")
    observer = _dict(value.get("observer"), "resident observer")
    observer_key = _load_bound(observer.get("private_key"), "observer key", private=True)
    observer_public_key = _load_bound(
        observer.get("public_key"),
        "observer public key",
        private=True,
    )
    if (
        candidate_value.get("partition") != "boot"
        or candidate.size != preserved.CANDIDATE_SIZE
        or candidate.sha256 != preserved.CANDIDATE_SHA256
        or candidate_value.get("expected_version") != EXPECTED_VERSION
        or candidate_value.get("expected_build") != EXPECTED_BUILD
        or rollback_value.get("partition") != "boot"
        or rollback.size != preserved.ROLLBACK_SIZE
        or rollback.sha256 != preserved.ROLLBACK_SHA256
        or target.get("profile") != staging.TARGET_PROFILE
        or target.get("bridge_selected_exact") is not True
        or protected.get("disposition") != preserved.ROOTFS_DISPOSITION
        or protected.get("handoff_eligible") is not False
        or source.get("size") != IMAGE_SIZE
        or source.get("mode") != FILE_MODE
        or source.get("nlink") != FILE_NLINK
        or source_host.sha256 != source.get("sha256")
        or work.get("device_path") != WORK_PATH
        or work.get("size") != IMAGE_SIZE
        or work.get("mode") != FILE_MODE
        or work.get("nlink") != FILE_NLINK
        or work_host.sha256 != work.get("sha256")
        or source_host.sha256 == work_host.sha256
        or observer.get("transport_scope") != base.OBSERVER_TRANSPORT_SCOPE
        or observer.get("wifi_or_external_network") is not False
    ):
        raise ContractError("preserved resident artifact or rootfs identity changed")
    spec = _make_live_spec(value, manifest, candidate, rollback)
    result = _bound(manifest.path.parent / "f1-live/result.json", private=True)
    result_value = _read(result.path, "resident result")
    try:
        exact_result = preserved._validate_success_result(spec, result_value)  # noqa: SLF001
        records = base.read_journal(spec, manifest.path.parent / "f1-live")
        exact_journal_result = preserved._validate_success_journal(  # noqa: SLF001
            spec,
            manifest.path.parent / "f1-live",
            records,
        )
    except (preserved.ContractError, base.ContractError) as exc:
        raise ContractError("preserved resident success terminal is not exact") from exc
    if exact_result != exact_journal_result:
        raise ContractError("resident result and canonical journal differ")
    journal_paths = tuple(sorted((manifest.path.parent / "f1-live/journal").glob("*.json")))
    if len(journal_paths) != len(preserved.INSTALL_SUCCESS_ACTIONS):
        raise ContractError("resident journal count changed")
    journal = tuple(_bound(item, private=True) for item in journal_paths)
    return ResidentEvidence(
        run_id,
        manifest,
        result,
        journal,
        value,
        result_value,
        spec,
        candidate,
        rollback,
        source_host,
        work_host,
        observer_key,
        observer_public_key,
    )


def _health(spec: Any, args: argparse.Namespace) -> dict[str, Any]:
    native = base.verify_candidate_health(spec, args)
    try:
        native_exact = preserved.resident._require_exact_native_health(  # noqa: SLF001
            spec, native
        )
        pstore = base.require_clean_pstore_before_handoff(args)
        base.validate_pstore_before_handoff_receipt(pstore, allow_legacy_empty=True)
    except (preserved.resident.ContractError, base.ContractError) as exc:
        raise ContractError("installed resident health is not exact") from exc
    return {"native": native, "native_exact": native_exact, "pstore": pstore}


def _validate_health_value(resident: ResidentEvidence, value: Any) -> dict[str, Any]:
    health = _dict(value, "resident health")
    if set(health) != {"native", "native_exact", "pstore"}:
        raise ContractError("resident health keyset changed")
    try:
        native_exact = preserved.resident._require_exact_native_health(  # noqa: SLF001
            resident.spec,
            health.get("native"),
        )
        base.validate_pstore_before_handoff_receipt(
            health.get("pstore"),
            allow_legacy_empty=True,
        )
    except (preserved.resident.ContractError, base.ContractError) as exc:
        raise ContractError("resident health evidence is not exact") from exc
    if health.get("native_exact") != native_exact:
        raise ContractError("resident native health reduction changed")
    return health


def _validate_pre_d0(
    resident: ResidentEvidence,
    run_id: str,
    bound: Bound,
) -> dict[str, Any]:
    value = _read(bound.path, "pre-cleanup D0")
    target = _dict(value.get("target"), "pre-cleanup D0 target")
    if (
        set(value)
        != {
            "schema", "created_utc", "run_id", "resident_run_id",
            "resident_manifest", "resident_result", "resident_terminal_journal",
            "target", "health", "protected_paths", "device_contact",
            "device_write", "flash", "payload_sent",
        }
        or value.get("schema") != PRE_D0_SCHEMA
        or value.get("run_id") != run_id
        or value.get("resident_run_id") != resident.run_id
        or value.get("resident_manifest") != _bound_value(resident.manifest)
        or value.get("resident_result") != _bound_value(resident.result)
        or value.get("resident_terminal_journal") != _bound_value(resident.journal[-1])
        or target
        != {
            "profile": staging.TARGET_PROFILE,
            "bridge_device": resident.spec.stage.bridge_device,
            "bridge_realpath": resident.spec.stage.bridge_realpath,
        }
        or value.get("device_contact") is not True
        or value.get("device_write") is not False
        or value.get("flash") is not False
        or value.get("payload_sent") is not False
    ):
        raise ContractError("pre-cleanup D0 root binding changed")
    _validate_health_value(resident, value.get("health"))
    try:
        preserved._validate_protected_proof(  # noqa: SLF001
            resident.spec,
            value.get("protected_paths"),
            phase="post-candidate",
        )
    except preserved.ContractError as exc:
        raise ContractError("pre-cleanup protected proof is not exact") from exc
    return value


def _validate_post_d0(
    spec: CleanupSpec,
    result: Bound,
    bound: Bound,
) -> dict[str, Any]:
    value = _read(bound.path, "post-cleanup D0")
    target = _dict(value.get("target"), "post-cleanup D0 target")
    if (
        set(value)
        != {
            "schema", "created_utc", "run_id", "manifest", "cleanup_result",
            "target", "source_absent_work_proof", "health", "source_exact",
            "work_absent", "device_contact", "device_write", "flash",
            "payload_sent",
        }
        or value.get("schema") != POST_D0_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("manifest") != _bound_value(spec.manifest)
        or value.get("cleanup_result") != _bound_value(result)
        or target
        != {
            "profile": staging.TARGET_PROFILE,
            "bridge_device": spec.resident.spec.stage.bridge_device,
            "bridge_realpath": spec.resident.spec.stage.bridge_realpath,
        }
        or value.get("source_exact") is not True
        or value.get("work_absent") is not True
        or value.get("device_contact") is not True
        or value.get("device_write") is not False
        or value.get("flash") is not False
        or value.get("payload_sent") is not False
    ):
        raise ContractError("post-cleanup D0 root binding changed")
    command = ["run", "/bin/busybox", "sh", "-c", _post_source_script(spec.resident)]
    marker = "A90_PRESERVED_D1_POST source=exact work=absent stage=absent in_use=no"
    try:
        preserved._validate_protected_receipt(  # noqa: SLF001
            value.get("source_absent_work_proof"),
            command,
            marker,
            "post-cleanup D0 source proof",
        )
    except preserved.ContractError as exc:
        raise ContractError("post-cleanup D0 source proof is not exact") from exc
    _validate_health_value(spec.resident, value.get("health"))
    return value


def _require_live_target(resident: ResidentEvidence, args: argparse.Namespace) -> None:
    if (
        args.bridge_device != resident.spec.stage.bridge_device
        or args.expect_realpath != resident.spec.stage.bridge_realpath
    ):
        raise ContractError("live target arguments differ from the exact resident")
    staging.require_exact_bridge(resident.spec.stage, args)


def _post_source_script(resident: ResidentEvidence) -> str:
    source = staging.shlex.quote(resident.spec.stage.remote_final)
    work = staging.shlex.quote(WORK_PATH)
    stage_path = staging.shlex.quote(resident.spec.stage.remote_stage_dir)
    source_sha = staging.shlex.quote(resident.source_host.sha256)
    return "\n".join(
        (
            "set -eu",
            f"SOURCE={source}",
            f"WORK={work}",
            f"STAGE={stage_path}",
            f"EXPECTED_SHA={source_sha}",
            f"EXPECTED_SIZE={IMAGE_SIZE}",
            '[ ! -L "$SOURCE" ] && [ -f "$SOURCE" ]',
            '[ ! -e "$WORK" ] && [ ! -L "$WORK" ]',
            '[ ! -e "$STAGE" ] && [ ! -L "$STAGE" ]',
            'META=$(/bin/busybox stat -c "%F|%s|%a|%h" "$SOURCE")',
            '[ "$META" = "regular file|2147483648|600|1" ]',
            'ACTUAL=$(/bin/busybox sha256sum "$SOURCE")',
            'ACTUAL=${ACTUAL%% *}',
            '[ "$ACTUAL" = "$EXPECTED_SHA" ]',
            '! /bin/busybox grep -F "$SOURCE" /proc/mounts >/dev/null 2>&1',
            'for P in /proc/[0-9]*/mountinfo; do [ -r "$P" ] || continue; '
            '! /bin/busybox grep -F "$SOURCE" "$P" >/dev/null 2>&1; done',
            'for B in /sys/block/loop*/loop/backing_file; do [ -r "$B" ] || continue; '
            'V=$(/bin/busybox cat "$B"); [ "$V" != "$SOURCE" ]; done',
            'for F in /proc/[0-9]*/fd/*; do [ -e "$F" ] || continue; '
            'V=$(/bin/busybox readlink "$F") || continue; case "$V" in '
            '"$SOURCE"|"$SOURCE (deleted)") exit 73;; esac; done',
            'for F in /proc/[0-9]*/root; do [ -e "$F" ] || continue; '
            'V=$(/bin/busybox readlink "$F") || continue; case "$V" in '
            '"$SOURCE"|"$SOURCE (deleted)") exit 73;; esac; done',
            'echo A90_PRESERVED_D1_POST source=exact work=absent stage=absent in_use=no',
        )
    )


def _exact_remote(
    args: argparse.Namespace,
    command: list[str],
    marker: str,
    label: str,
) -> dict[str, Any]:
    receipt = preserved._remote(args, command, label)  # noqa: SLF001
    try:
        preserved._validate_protected_receipt(  # noqa: SLF001
            receipt,
            command,
            marker,
            label,
        )
    except preserved.ContractError as exc:
        raise ContractError(f"{label} receipt is not exact") from exc
    return receipt


def _post_source_proof(resident: ResidentEvidence, args: argparse.Namespace) -> dict[str, Any]:
    script = _post_source_script(resident)
    marker = "A90_PRESERVED_D1_POST source=exact work=absent stage=absent in_use=no"
    command = ["run", "/bin/busybox", "sh", "-c", script]
    return _exact_remote(args, command, marker, "post-cleanup source proof")


def execute_pre_cleanup_d0(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_RE.fullmatch(args.run_id or "") is None:
        raise ContractError("cleanup run_id is not exact")
    resident = load_resident_evidence(
        args.resident_manifest, args.expect_resident_manifest_sha256
    )
    run_dir = PRIVATE_RUN_BASE / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    output = run_dir / "pre-cleanup-d0.json"
    if output.exists() or output.is_symlink():
        raise ContractError("pre-cleanup D0 already exists")
    _require_live_target(resident, args)
    health = _health(resident.spec, args)
    protected = preserved.protected_paths_preflight(
        resident.spec, args, phase="post-candidate"
    )
    value = {
        "schema": PRE_D0_SCHEMA,
        "created_utc": utc_now(),
        "run_id": args.run_id,
        "resident_run_id": resident.run_id,
        "resident_manifest": _bound_value(resident.manifest),
        "resident_result": _bound_value(resident.result),
        "resident_terminal_journal": _bound_value(resident.journal[-1]),
        "target": {
            "profile": staging.TARGET_PROFILE,
            "bridge_device": resident.spec.stage.bridge_device,
            "bridge_realpath": resident.spec.stage.bridge_realpath,
        },
        "health": health,
        "protected_paths": protected,
        "device_contact": True,
        "device_write": False,
        "flash": False,
        "payload_sent": False,
    }
    _write(output, value)
    return {"status": "PASS_PRE_CLEANUP_D0", "evidence": _bound_value(_bound(output, private=True))}


def build_cleanup_manifest(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_RE.fullmatch(args.run_id or "") is None:
        raise ContractError("cleanup run_id is not exact")
    resident = load_resident_evidence(
        args.resident_manifest, args.expect_resident_manifest_sha256
    )
    run_dir = (PRIVATE_RUN_BASE / args.run_id).resolve(strict=True)
    pre_d0 = _bound(args.pre_cleanup_d0, private=True)
    if pre_d0.sha256 != _sha(args.expect_pre_cleanup_d0_sha256, "pre-cleanup D0 SHA256"):
        raise ContractError("pre-cleanup D0 SHA256 mismatch")
    pre = _validate_pre_d0(resident, args.run_id, pre_d0)
    if (
        pre_d0.path != run_dir / "pre-cleanup-d0.json"
        or pre.get("schema") != PRE_D0_SCHEMA
    ):
        raise ContractError("pre-cleanup D0 is not exact")
    review_input = _bound(args.review_report, private=False)
    if review_input.sha256 != _sha(args.expect_review_report_sha256, "review SHA256"):
        raise ContractError("review SHA256 mismatch")
    review = _load_review(_bound_value(review_input))
    closure = _closure()
    protected = _dict(resident.value.get("protected_rootfs"), "protected rootfs")
    source = _dict(protected.get("source"), "protected source")
    work = _dict(protected.get("work"), "protected work")
    manifest_value = {
        "schema": CLEANUP_SCHEMA,
        "status": CLEANUP_STATUS,
        "created_utc": utc_now(),
        "run_id": args.run_id,
        "capability": CAPABILITY,
        "resident": {
            "run_id": resident.run_id,
            "manifest": _bound_value(resident.manifest),
            "result": _bound_value(resident.result),
            "journal": [_bound_value(item) for item in resident.journal],
        },
        "pre_cleanup_d0": _bound_value(pre_d0),
        "target": {
            "profile": staging.TARGET_PROFILE,
            "bridge_device": resident.spec.stage.bridge_device,
            "bridge_realpath": resident.spec.stage.bridge_realpath,
            "recovery_serial_sha256": _dict(resident.value.get("recovery"), "recovery").get("adb_serial_sha256"),
            "recovery_profile": "operator-attended Download or TWRP",
        },
        "candidate_boot": _bound_value(resident.candidate),
        "rollback_boot": _bound_value(resident.rollback),
        "protected_rootfs": {
            "source_path": source["device_path"],
            "source_size": source["size"],
            "source_sha256": source["sha256"],
            "source_host": _bound_value(resident.source_host),
            "work_path": WORK_PATH,
            "work_size": work["size"],
            "work_sha256": work["sha256"],
            "work_host": _bound_value(resident.work_host),
            "stage_path": protected["stage_path"],
            "source_work_distinct": True,
        },
        "execution_closure": {role: _bound_value(item) for role, item in closure.items()},
        "independent_review": _bound_value(review),
        "authority": {
            "live_authority": False,
            "operator_attendance_required": True,
            "fresh_exact_approval_required": True,
            "single_fixed_unlink_dispatch": True,
            "unlink_replay_forbidden": True,
            "flash": False,
            "payload_transfer": False,
        },
    }
    output = run_dir / "cleanup-manifest.json"
    _write(output, manifest_value)
    bound = _bound(output, private=True)
    load_cleanup_spec(output, bound.sha256)
    return {"status": "READY_FOR_ATTENDED_CLEANUP", "manifest": _bound_value(bound), "live_authority": False}


def load_cleanup_spec(
    path: Path,
    expected_sha256: str,
    *,
    historical_closure: bool = False,
) -> CleanupSpec:
    manifest = _bound(path, private=True)
    if manifest.sha256 != _sha(expected_sha256, "cleanup manifest SHA256"):
        raise ContractError("cleanup manifest SHA256 mismatch")
    value = _read(manifest.path, "cleanup manifest")
    run_id = _string(value.get("run_id"), "cleanup run_id")
    if (
        set(value)
        != {
            "schema", "status", "created_utc", "run_id", "capability",
            "resident", "pre_cleanup_d0", "target", "candidate_boot",
            "rollback_boot", "protected_rootfs", "execution_closure",
            "independent_review", "authority",
        }
        or value.get("schema") != CLEANUP_SCHEMA
        or value.get("status") != CLEANUP_STATUS
        or value.get("capability") != CAPABILITY
        or RUN_RE.fullmatch(run_id) is None
        or manifest.path != (PRIVATE_RUN_BASE / run_id / "cleanup-manifest.json").resolve(strict=True)
    ):
        raise ContractError("cleanup manifest root changed")
    if historical_closure and (
        run_id != HISTORICAL_CLEANUP_RUN_ID
        or manifest.path
        != (
            PRIVATE_RUN_BASE
            / HISTORICAL_CLEANUP_RUN_ID
            / "cleanup-manifest.json"
        ).resolve(strict=True)
        or manifest.sha256 != HISTORICAL_CLEANUP_MANIFEST_SHA256
    ):
        raise ContractError("historical cleanup manifest is not the exact closed artifact")
    resident_value = _dict(value.get("resident"), "cleanup resident")
    resident_manifest = _load_bound(resident_value.get("manifest"), "resident manifest", private=True)
    resident = load_resident_evidence(resident_manifest.path, resident_manifest.sha256)
    if (
        resident_value.get("run_id") != resident.run_id
        or _load_bound(resident_value.get("result"), "resident result", private=True) != resident.result
        or resident_value.get("journal") != [_bound_value(item) for item in resident.journal]
    ):
        raise ContractError("cleanup resident binding changed")
    pre_d0 = _load_bound(value.get("pre_cleanup_d0"), "pre-cleanup D0", private=True)
    _validate_pre_d0(resident, run_id, pre_d0)
    closure_value = _dict(value.get("execution_closure"), "execution closure")
    if set(closure_value) != set(SOURCE_PATHS):
        raise ContractError("cleanup source closure roles changed")
    if historical_closure:
        review, closure = _load_historical_review(
            value.get("independent_review"),
            closure_value,
        )
    else:
        closure = _closure()
        if closure_value != {role: _bound_value(item) for role, item in closure.items()}:
            raise ContractError("cleanup source closure changed")
        review = _load_review(value.get("independent_review"))
    protected = _dict(value.get("protected_rootfs"), "cleanup protected rootfs")
    source = _dict(resident.value.get("protected_rootfs"), "resident protected rootfs")
    source_item = _dict(source.get("source"), "resident source")
    work_item = _dict(source.get("work"), "resident work")
    target = _dict(value.get("target"), "cleanup target")
    authority = _dict(value.get("authority"), "cleanup authority")
    if (
        target
        != {
            "profile": staging.TARGET_PROFILE,
            "bridge_device": resident.spec.stage.bridge_device,
            "bridge_realpath": resident.spec.stage.bridge_realpath,
            "recovery_serial_sha256": _dict(resident.value.get("recovery"), "recovery").get("adb_serial_sha256"),
            "recovery_profile": "operator-attended Download or TWRP",
        }
        or value.get("candidate_boot") != _bound_value(resident.candidate)
        or value.get("rollback_boot") != _bound_value(resident.rollback)
        or protected
        != {
            "source_path": source_item["device_path"],
            "source_size": IMAGE_SIZE,
            "source_sha256": source_item["sha256"],
            "source_host": _bound_value(resident.source_host),
            "work_path": WORK_PATH,
            "work_size": IMAGE_SIZE,
            "work_sha256": work_item["sha256"],
            "work_host": _bound_value(resident.work_host),
            "stage_path": source["stage_path"],
            "source_work_distinct": True,
        }
        or authority
        != {
            "live_authority": False,
            "operator_attendance_required": True,
            "fresh_exact_approval_required": True,
            "single_fixed_unlink_dispatch": True,
            "unlink_replay_forbidden": True,
            "flash": False,
            "payload_transfer": False,
        }
    ):
        raise ContractError("cleanup safety binding changed")
    return CleanupSpec(manifest, run_id, resident, pre_d0, review, closure)


def approval_binding(spec: CleanupSpec) -> dict[str, Any]:
    protected = _dict(_read(spec.manifest.path, "cleanup manifest").get("protected_rootfs"), "protected rootfs")
    return {
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest.sha256,
        "resident_manifest_sha256": spec.resident.manifest.sha256,
        "candidate_sha256": spec.resident.candidate.sha256,
        "rollback_sha256": spec.resident.rollback.sha256,
        "source_sha256": protected["source_sha256"],
        "work_sha256": protected["work_sha256"],
        "work_path": WORK_PATH,
        "bridge_device": spec.resident.spec.stage.bridge_device,
        "bridge_realpath": spec.resident.spec.stage.bridge_realpath,
        "review_sha256": spec.review.sha256,
        "dispatch_limit": 1,
        "unlink_replay_forbidden": True,
    }


def prepare_approval(spec: CleanupSpec) -> dict[str, Any]:
    binding = approval_binding(spec)
    binding_sha = preserved.base.json_sha256(binding)
    value = {
        "schema": APPROVAL_SCHEMA,
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "approval_binding": binding,
        "approval_binding_sha256": binding_sha,
        "approval_token": APPROVAL_PREFIX + binding_sha,
        "live_authority": False,
        "device_contact": False,
        "device_write": False,
    }
    output = spec.manifest.path.parent / "cleanup-approval-prepared.json"
    _write(output, value)
    return value


def _load_approval(spec: CleanupSpec, token: str) -> dict[str, Any]:
    value = _read(spec.manifest.path.parent / "cleanup-approval-prepared.json", "cleanup approval")
    binding = approval_binding(spec)
    binding_sha = preserved.base.json_sha256(binding)
    expected = APPROVAL_PREFIX + binding_sha
    if (
        value.get("schema") != APPROVAL_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("approval_binding") != binding
        or value.get("approval_binding_sha256") != binding_sha
        or value.get("approval_token") != expected
        or token != expected
        or value.get("live_authority") is not False
    ):
        raise ContractError("cleanup approval is not exact")
    return value


def _cleanup_command(spec: CleanupSpec) -> list[str]:
    protected = _dict(_read(spec.manifest.path, "cleanup manifest").get("protected_rootfs"), "protected rootfs")
    return [
        "run", "/bin/busybox", "sh", "-c", cleanup.cleanup_script(), "sh",
        WORK_PATH, protected["work_sha256"], protected["source_path"],
        protected["stage_path"], protected["source_sha256"],
        cleanup.SOURCE_EXACT_DISTINCT,
    ]


def _presence_command(spec: CleanupSpec) -> list[str]:
    protected = _dict(_read(spec.manifest.path, "cleanup manifest").get("protected_rootfs"), "protected rootfs")
    return [
        "run", "/bin/busybox", "sh", "-c", cleanup.presence_script(), "sh",
        WORK_PATH, protected["source_path"], protected["stage_path"],
        protected["work_sha256"], protected["source_sha256"],
        cleanup.SOURCE_EXACT_DISTINCT,
    ]


def _presence(spec: CleanupSpec, args: argparse.Namespace) -> dict[str, Any]:
    command = _presence_command(spec)
    receipt = preserved._remote(args, command, "cleanup presence")  # noqa: SLF001
    matches = re.findall(
        r"^work=(absent|present) source=(exact|invalid|present|absent) stage=(absent|present)\r?$",
        str(receipt.get("text") or ""),
        re.MULTILINE,
    )
    if len(matches) != 1:
        raise ContractError("cleanup presence receipt is not exact")
    work, source, stage = matches[0]
    marker = f"work={work} source={source} stage={stage}"
    try:
        preserved._validate_protected_receipt(  # noqa: SLF001
            receipt,
            command,
            marker,
            "cleanup presence",
        )
    except preserved.ContractError as exc:
        raise ContractError("cleanup presence receipt is not exact") from exc
    return {"work": work, "source": source, "stage": stage, "receipt": receipt}


def execute_cleanup(
    spec: CleanupSpec,
    args: argparse.Namespace,
    *,
    approval: str,
    transaction_dir: Path,
) -> dict[str, Any]:
    if args.operator_attended is not True:
        raise ContractError("cleanup requires awake attended operator")
    _load_approval(spec, approval)
    expected_dir = spec.manifest.path.parent / "cleanup-live"
    if transaction_dir.resolve() != expected_dir.resolve() or expected_dir.exists():
        raise ContractError("cleanup transaction path must be new and exact")
    _require_live_target(spec.resident, args)
    before_health = _health(spec.resident.spec, args)
    before_paths = preserved.protected_paths_preflight(
        spec.resident.spec, args, phase="post-candidate"
    )
    if (
        _sha256(spec.resident.work_host.path) != spec.resident.work_host.sha256
        or _sha256(spec.resident.source_host.path) != spec.resident.source_host.sha256
    ):
        raise ContractError("host-preserved source/work changed before unlink")
    expected_dir.mkdir(mode=0o700)
    intent = {
        "schema": "a90_resident_preserved_work_cleanup_intent_v1",
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest.sha256,
        "approval_binding_sha256": preserved.base.json_sha256(approval_binding(spec)),
        "before_health": before_health,
        "before_paths": before_paths,
        "work_path": WORK_PATH,
        "operator_attended": True,
        "physical_recovery_available": True,
        "dispatch_limit": 1,
        "unlink_replay_forbidden": True,
    }
    _write(expected_dir / "intent.json", intent)
    command = _cleanup_command(spec)
    dispatch = {
        "schema": "a90_resident_preserved_work_cleanup_dispatch_v1",
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "dispatch_count": 1,
        "command_sha256": preserved.base.json_sha256(command),
        "approval_consumed": True,
        "unlink_replay_forbidden": True,
    }
    _write(expected_dir / "dispatch.json", dispatch)
    response_proven = False
    dispatch_error: dict[str, str] | None = None
    try:
        receipt = preserved._remote(args, command, "cleanup unlink dispatch")  # noqa: SLF001
        marker = "work=unlinked source=exact"
        preserved._validate_protected_receipt(  # noqa: SLF001
            receipt,
            command,
            marker,
            "cleanup unlink dispatch",
        )
        response_proven = True
    except Exception as exc:  # noqa: BLE001 - dispatch is never retransmitted
        receipt = None
        dispatch_error = {"type": type(exc).__name__, "message": str(exc)}
    if dispatch_error is not None:
        _write(
            expected_dir / "dispatch-error.json",
            {
                "schema": "a90_resident_preserved_work_cleanup_dispatch_error_v1",
                "created_utc": utc_now(),
                "run_id": spec.run_id,
                "error": dispatch_error,
                "cleanup_retransmitted": False,
                "read_only_reconciliation_allowed": True,
            },
        )
    errors: dict[str, dict[str, str]] = {}
    try:
        presence = _presence(spec, args)
    except Exception as exc:  # noqa: BLE001 - passive reconciliation only
        presence = {"work": "unknown", "source": "unknown", "stage": "unknown"}
        errors["presence"] = {"type": type(exc).__name__, "message": str(exc)}
    try:
        post_source = _post_source_proof(spec.resident, args)
    except Exception as exc:  # noqa: BLE001
        post_source = None
        errors["source"] = {"type": type(exc).__name__, "message": str(exc)}
    try:
        post_health = _health(spec.resident.spec, args)
    except Exception as exc:  # noqa: BLE001
        post_health = None
        errors["health"] = {"type": type(exc).__name__, "message": str(exc)}
    effect_proven = (
        presence.get("work") == "absent"
        and presence.get("source") == "exact"
        and presence.get("stage") == "absent"
        and post_source is not None
    )
    healthy = post_health is not None
    complete = effect_proven and healthy
    outcome = (
        "PASS_EXACT_FIXED_WORK_UNLINKED"
        if complete and response_proven
        else "PASS_EFFECT_PROVEN_AFTER_AMBIGUOUS_RESPONSE"
        if complete
        else "RECOVERY_PENDING_PARKED"
        if effect_proven
        else "STOP_NO_RETRY_WORK_ABSENCE_UNPROVEN"
    )
    value = {
        "schema": RESULT_SCHEMA,
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "manifest_sha256": spec.manifest.sha256,
        "outcome": outcome,
        "dispatch_count": 1,
        "cleanup_retransmitted": False,
        "response_proven": response_proven,
        "dispatch_receipt": receipt,
        "post_presence": presence,
        "post_source": post_source,
        "post_health": post_health,
        "post_errors": errors,
        "effect_proven": effect_proven,
        "post_health_proven": healthy,
        "operator_attended": True,
        "physical_recovery_available": True,
        "device_write": True,
        "deleted_path": WORK_PATH if effect_proven else None,
        "flash": False,
        "payload_sent": False,
        "other_device_commands": 0,
    }
    _write(expected_dir / "result.json", value)
    return value


def _load_success_result(spec: CleanupSpec) -> tuple[Bound, dict[str, Any]]:
    live_dir = spec.manifest.path.parent / "cleanup-live"
    intent_bound = _bound(live_dir / "intent.json", private=True)
    dispatch_bound = _bound(live_dir / "dispatch.json", private=True)
    bound = _bound(live_dir / "result.json", private=True)
    intent = _read(intent_bound.path, "cleanup intent")
    dispatch = _read(dispatch_bound.path, "cleanup dispatch")
    value = _read(bound.path, "cleanup result")
    presence = _dict(value.get("post_presence"), "cleanup post presence")
    outcome = value.get("outcome")
    response_proven = value.get("response_proven")
    binding = approval_binding(spec)
    binding_sha = preserved.base.json_sha256(binding)
    expected_token = APPROVAL_PREFIX + binding_sha
    _load_approval(spec, expected_token)
    command = _cleanup_command(spec)
    protected = _dict(
        _read(spec.manifest.path, "cleanup manifest").get("protected_rootfs"),
        "protected rootfs",
    )
    if (
        set(intent)
        != {
            "schema", "created_utc", "run_id", "manifest_sha256",
            "approval_binding_sha256", "before_health", "before_paths",
            "work_path", "operator_attended", "physical_recovery_available",
            "dispatch_limit", "unlink_replay_forbidden",
        }
        or intent.get("schema")
        != "a90_resident_preserved_work_cleanup_intent_v1"
        or intent.get("run_id") != spec.run_id
        or intent.get("manifest_sha256") != spec.manifest.sha256
        or intent.get("approval_binding_sha256") != binding_sha
        or intent.get("work_path") != WORK_PATH
        or intent.get("operator_attended") is not True
        or intent.get("physical_recovery_available") is not True
        or type(intent.get("dispatch_limit")) is not int
        or intent.get("dispatch_limit") != 1
        or intent.get("unlink_replay_forbidden") is not True
    ):
        raise ContractError("cleanup durable intent is not exact")
    _validate_health_value(spec.resident, intent.get("before_health"))
    try:
        preserved._validate_protected_proof(  # noqa: SLF001
            spec.resident.spec,
            intent.get("before_paths"),
            phase="post-candidate",
        )
    except preserved.ContractError as exc:
        raise ContractError("cleanup intent protected proof is not exact") from exc
    if (
        _sha256(spec.resident.work_host.path) != spec.resident.work_host.sha256
        or _sha256(spec.resident.source_host.path) != spec.resident.source_host.sha256
    ):
        raise ContractError("cleanup host preservation changed")
    if (
        set(dispatch)
        != {
            "schema", "created_utc", "run_id", "dispatch_count",
            "command_sha256", "approval_consumed", "unlink_replay_forbidden",
        }
        or dispatch.get("schema")
        != "a90_resident_preserved_work_cleanup_dispatch_v1"
        or dispatch.get("run_id") != spec.run_id
        or type(dispatch.get("dispatch_count")) is not int
        or dispatch.get("dispatch_count") != 1
        or dispatch.get("command_sha256")
        != preserved.base.json_sha256(command)
        or dispatch.get("approval_consumed") is not True
        or dispatch.get("unlink_replay_forbidden") is not True
    ):
        raise ContractError("cleanup durable dispatch is not exact")
    if (
        set(value)
        != {
            "schema", "created_utc", "run_id", "manifest_sha256", "outcome",
            "dispatch_count", "cleanup_retransmitted", "response_proven",
            "dispatch_receipt", "post_presence", "post_source", "post_health",
            "post_errors", "effect_proven", "post_health_proven",
            "operator_attended", "physical_recovery_available", "device_write",
            "deleted_path", "flash", "payload_sent", "other_device_commands",
        }
        or value.get("schema") != RESULT_SCHEMA
        or value.get("run_id") != spec.run_id
        or value.get("manifest_sha256") != spec.manifest.sha256
        or outcome
        not in {"PASS_EXACT_FIXED_WORK_UNLINKED", "PASS_EFFECT_PROVEN_AFTER_AMBIGUOUS_RESPONSE"}
        or type(value.get("dispatch_count")) is not int
        or value.get("dispatch_count") != 1
        or value.get("cleanup_retransmitted") is not False
        or type(response_proven) is not bool
        or (outcome == "PASS_EXACT_FIXED_WORK_UNLINKED") is not response_proven
        or presence.get("work") != "absent"
        or presence.get("source") != "exact"
        or presence.get("stage") != "absent"
        or not isinstance(value.get("post_source"), dict)
        or not isinstance(value.get("post_health"), dict)
        or value.get("post_errors") != {}
        or value.get("effect_proven") is not True
        or value.get("post_health_proven") is not True
        or value.get("operator_attended") is not True
        or value.get("physical_recovery_available") is not True
        or value.get("device_write") is not True
        or value.get("deleted_path") != WORK_PATH
        or value.get("flash") is not False
        or value.get("payload_sent") is not False
        or value.get("other_device_commands") != 0
    ):
        raise ContractError("cleanup result is not an exact successful terminal")
    intent_time = _utc(intent.get("created_utc"), "cleanup intent time")
    dispatch_time = _utc(dispatch.get("created_utc"), "cleanup dispatch time")
    result_time = _utc(value.get("created_utc"), "cleanup result time")
    if not intent_time <= dispatch_time <= result_time:
        raise ContractError("cleanup evidence time order changed")
    presence_command = _presence_command(spec)
    presence_marker = "work=absent source=exact stage=absent"
    try:
        preserved._validate_protected_receipt(  # noqa: SLF001
            presence.get("receipt"),
            presence_command,
            presence_marker,
            "cleanup result presence",
        )
        source_command = [
            "run", "/bin/busybox", "sh", "-c", _post_source_script(spec.resident)
        ]
        preserved._validate_protected_receipt(  # noqa: SLF001
            value.get("post_source"),
            source_command,
            "A90_PRESERVED_D1_POST source=exact work=absent stage=absent in_use=no",
            "cleanup result source proof",
        )
    except preserved.ContractError as exc:
        raise ContractError("cleanup PASS readback receipt is not exact") from exc
    _validate_health_value(spec.resident, value.get("post_health"))
    if response_proven:
        try:
            preserved._validate_protected_receipt(  # noqa: SLF001
                value.get("dispatch_receipt"),
                command,
                "work=unlinked source=exact",
                "cleanup result dispatch receipt",
            )
        except preserved.ContractError as exc:
            raise ContractError("cleanup dispatch receipt is not exact") from exc
        if (live_dir / "dispatch-error.json").exists():
            raise ContractError("cleanup exact response has a conflicting error record")
    else:
        error_bound = _bound(live_dir / "dispatch-error.json", private=True)
        error_value = _read(error_bound.path, "cleanup dispatch error")
        error = _dict(error_value.get("error"), "cleanup dispatch error detail")
        if (
            set(error_value)
            != {
                "schema", "created_utc", "run_id", "error",
                "cleanup_retransmitted", "read_only_reconciliation_allowed",
            }
            or error_value.get("schema")
            != "a90_resident_preserved_work_cleanup_dispatch_error_v1"
            or error_value.get("run_id") != spec.run_id
            or set(error) != {"type", "message"}
            or not all(isinstance(error.get(key), str) and error.get(key) for key in error)
            or error_value.get("cleanup_retransmitted") is not False
            or error_value.get("read_only_reconciliation_allowed") is not True
            or not dispatch_time
            <= _utc(error_value.get("created_utc"), "cleanup dispatch error time")
            <= result_time
        ):
            raise ContractError("cleanup ambiguous-response record is not exact")
    if protected.get("work_path") != WORK_PATH:
        raise ContractError("cleanup result work path binding changed")
    return bound, value


def execute_post_cleanup_d0(spec: CleanupSpec, args: argparse.Namespace) -> dict[str, Any]:
    result, _ = _load_success_result(spec)
    output = spec.manifest.path.parent / "post-cleanup-d0.json"
    if output.exists() or output.is_symlink():
        raise ContractError("post-cleanup D0 already exists")
    _require_live_target(spec.resident, args)
    source = _post_source_proof(spec.resident, args)
    health = _health(spec.resident.spec, args)
    value = {
        "schema": POST_D0_SCHEMA,
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "manifest": _bound_value(spec.manifest),
        "cleanup_result": _bound_value(result),
        "target": {
            "profile": staging.TARGET_PROFILE,
            "bridge_device": spec.resident.spec.stage.bridge_device,
            "bridge_realpath": spec.resident.spec.stage.bridge_realpath,
        },
        "source_absent_work_proof": source,
        "health": health,
        "source_exact": True,
        "work_absent": True,
        "device_contact": True,
        "device_write": False,
        "flash": False,
        "payload_sent": False,
    }
    _write(output, value)
    return {"status": "PASS_POST_CLEANUP_D0", "evidence": _bound_value(_bound(output, private=True))}


def build_baseline(spec: CleanupSpec, args: argparse.Namespace) -> dict[str, Any]:
    result, _ = _load_success_result(spec)
    post_d0 = _bound(args.post_cleanup_d0, private=True)
    if post_d0.sha256 != _sha(args.expect_post_cleanup_d0_sha256, "post-cleanup D0 SHA256"):
        raise ContractError("post-cleanup D0 SHA256 mismatch")
    post = _validate_post_d0(spec, result, post_d0)
    if (
        post_d0.path != spec.manifest.path.parent / "post-cleanup-d0.json"
        or post.get("schema") != POST_D0_SCHEMA
    ):
        raise ContractError("post-cleanup D0 is not exact")
    output = spec.manifest.path.parent / "d1-baseline.json"
    if output.exists() or output.is_symlink():
        raise ContractError("D1 baseline already exists; reduction is one-time")
    resident = spec.resident
    value = resident.value
    protected = _dict(value.get("protected_rootfs"), "protected rootfs")
    source = _dict(protected.get("source"), "protected source")
    observer = _dict(value.get("observer"), "resident observer")
    recovery = _dict(value.get("recovery"), "resident recovery")
    baseline = {
        "schema": BASELINE_SCHEMA,
        "status": BASELINE_STATUS,
        "created_utc": utc_now(),
        "run_id": spec.run_id,
        "resident": {
            "run_id": resident.run_id,
            "manifest": _bound_value(resident.manifest),
            "result": _bound_value(resident.result),
            "journal": [_bound_value(item) for item in resident.journal],
        },
        "cleanup": {
            "manifest": _bound_value(spec.manifest),
            "result": _bound_value(result),
            "post_cleanup_d0": _bound_value(post_d0),
        },
        "target": {
            "profile": staging.TARGET_PROFILE,
            "bridge_device": resident.spec.stage.bridge_device,
            "bridge_realpath": resident.spec.stage.bridge_realpath,
            "recovery_serial_sha256": recovery["adb_serial_sha256"],
            "recovery_profile": "operator-attended Download or TWRP",
        },
        "candidate_boot": {
            **_bound_value(resident.candidate),
            "partition": "boot",
            "expected_version": EXPECTED_VERSION,
            "expected_build": EXPECTED_BUILD,
        },
        "rollback_boot": {
            **_bound_value(resident.rollback),
            "partition": "boot",
            "expected_version": preserved.ROLLBACK_VERSION,
            "expected_build": preserved.ROLLBACK_BUILD,
        },
        "debian_rootfs": {
            "keyed_source": {
                "local_path": str(resident.source_host.path),
                "device_path": source["device_path"],
                "size": IMAGE_SIZE,
                "sha256": source["sha256"],
                "profile": phase3_observer.PROFILE,
            },
            "work_copy": {"device_path": WORK_PATH, "required_initial_state": "absent"},
            "observer": {
                "private_key_path": str(resident.observer_key.path),
                "public_key_sha256": resident.observer_public_key.sha256,
                "device_ip": observer["device_ip"],
                "device_port": observer["device_port"],
                "host_ncm_profile": observer["host_ncm_profile"],
                "transport_scope": base.OBSERVER_TRANSPORT_SCOPE,
                "wifi_or_external_network": False,
            },
            "handoff_command": [
                base.HANDOFF_COMMAND,
                base.HANDOFF_TOKEN,
                source["device_path"],
                source["sha256"],
            ],
        },
        "observation": {
            "handoff_attempt_limit": 1,
            "handoff_timeout_sec": HANDOFF_TIMEOUT_SEC,
            "ssh_marker_timeout_sec": SSH_MARKER_TIMEOUT_SEC,
            "candidate_return_timeout_sec": CANDIDATE_RETURN_TIMEOUT_SEC,
        },
        "execution_closure": {role: _bound_value(item) for role, item in spec.closure.items()},
        "independent_review": _bound_value(spec.review),
        "authority": {
            "live_authority": False,
            "baseline_grants_device_authority": False,
            "fresh_d1_opening_d0_required": True,
            "original_preserved_terminal_directly_ineligible": True,
            "reduction_count": 1,
        },
    }
    _write(output, baseline)
    bound = _bound(output, private=True)
    load_baseline(output, bound.sha256)
    return {"status": "PASS_IMMUTABLE_D1_BASELINE_REDUCED", "baseline": _bound_value(bound), "live_authority": False}


def load_baseline(path: Path, expected_sha256: str) -> BaselineSpec:
    manifest = _bound(path, private=True)
    if manifest.sha256 != _sha(expected_sha256, "baseline SHA256"):
        raise ContractError("baseline SHA256 mismatch")
    value = _read(manifest.path, "D1 baseline")
    run_id = _string(value.get("run_id"), "baseline run_id")
    if (
        set(value)
        != {
            "schema", "status", "created_utc", "run_id", "resident", "cleanup",
            "target", "candidate_boot", "rollback_boot", "debian_rootfs",
            "observation", "execution_closure", "independent_review", "authority",
        }
        or value.get("schema") != BASELINE_SCHEMA
        or value.get("status") != BASELINE_STATUS
        or RUN_RE.fullmatch(run_id) is None
        or manifest.path != (PRIVATE_RUN_BASE / run_id / "d1-baseline.json").resolve(strict=True)
    ):
        raise ContractError("D1 baseline root changed")
    if (
        run_id != HISTORICAL_CLEANUP_RUN_ID
        or manifest.path
        != (
            PRIVATE_RUN_BASE
            / HISTORICAL_CLEANUP_RUN_ID
            / "d1-baseline.json"
        ).resolve(strict=True)
        or manifest.sha256 != HISTORICAL_BASELINE_SHA256
    ):
        raise ContractError("D1 baseline is not the exact immutable historical artifact")
    cleanup_value = _dict(value.get("cleanup"), "baseline cleanup")
    cleanup_manifest = _load_bound(cleanup_value.get("manifest"), "cleanup manifest", private=True)
    spec = load_cleanup_spec(
        cleanup_manifest.path,
        cleanup_manifest.sha256,
        historical_closure=True,
    )
    cleanup_result, _ = _load_success_result(spec)
    post_d0 = _load_bound(cleanup_value.get("post_cleanup_d0"), "post-cleanup D0", private=True)
    if (
        cleanup_value.get("result") != _bound_value(cleanup_result)
        or post_d0.path != spec.manifest.path.parent / "post-cleanup-d0.json"
    ):
        raise ContractError("baseline cleanup proof changed")
    _validate_post_d0(spec, cleanup_result, post_d0)
    resident_value = _dict(value.get("resident"), "baseline resident")
    resident = spec.resident
    if resident_value != {
        "run_id": resident.run_id,
        "manifest": _bound_value(resident.manifest),
        "result": _bound_value(resident.result),
        "journal": [_bound_value(item) for item in resident.journal],
    }:
        raise ContractError("baseline resident proof changed")
    closure_value = _dict(value.get("execution_closure"), "baseline closure")
    if closure_value != {role: _bound_value(item) for role, item in spec.closure.items()}:
        raise ContractError("baseline execution closure changed")
    review = _load_bound(
        value.get("independent_review"),
        "baseline independent review",
        private=False,
    )
    if review != spec.review:
        raise ContractError("baseline independent review changed")
    candidate_value = _dict(value.get("candidate_boot"), "baseline candidate")
    rollback_value = _dict(value.get("rollback_boot"), "baseline rollback")
    candidate = _load_bound(
        {key: candidate_value.get(key) for key in ("path", "size", "sha256")},
        "baseline candidate", private=True,
    )
    rollback = _load_bound(
        {key: rollback_value.get(key) for key in ("path", "size", "sha256")},
        "baseline rollback", private=True,
    )
    debian = _dict(value.get("debian_rootfs"), "baseline rootfs")
    keyed = _dict(debian.get("keyed_source"), "baseline keyed source")
    rootfs = _bound(Path(_string(keyed.get("local_path"), "rootfs local path")), private=True)
    observer = _dict(debian.get("observer"), "baseline observer")
    observer_key = _bound(Path(_string(observer.get("private_key_path"), "observer key")), private=True)
    target = _dict(value.get("target"), "baseline target")
    observation = _dict(value.get("observation"), "baseline observation")
    authority = _dict(value.get("authority"), "baseline authority")
    source = _dict(resident.value.get("protected_rootfs"), "resident protected rootfs")
    source_item = _dict(source.get("source"), "resident source")
    resident_target = _dict(resident.value.get("target"), "resident target")
    resident_observer = _dict(resident.value.get("observer"), "resident observer")
    resident_recovery = _dict(resident.value.get("recovery"), "resident recovery")
    expected_target = {
        "profile": staging.TARGET_PROFILE,
        "bridge_device": resident_target.get("bridge_device"),
        "bridge_realpath": resident_target.get("bridge_selected_realpath"),
        "recovery_serial_sha256": resident_recovery.get("adb_serial_sha256"),
        "recovery_profile": "operator-attended Download or TWRP",
    }
    expected_observer = {
        "private_key_path": str(resident.observer_key.path),
        "public_key_sha256": resident.observer_public_key.sha256,
        "device_ip": resident_observer.get("device_ip"),
        "device_port": resident_observer.get("device_port"),
        "host_ncm_profile": resident_observer.get("host_ncm_profile"),
        "transport_scope": base.OBSERVER_TRANSPORT_SCOPE,
        "wifi_or_external_network": False,
    }
    if (
        set(candidate_value)
        != {"path", "size", "sha256", "partition", "expected_version", "expected_build"}
        or candidate != resident.candidate
        or candidate_value.get("partition") != "boot"
        or candidate_value.get("expected_version") != EXPECTED_VERSION
        or candidate_value.get("expected_build") != EXPECTED_BUILD
        or set(rollback_value)
        != {"path", "size", "sha256", "partition", "expected_version", "expected_build"}
        or rollback != resident.rollback
        or rollback_value.get("partition") != "boot"
        or rollback_value.get("expected_version") != preserved.ROLLBACK_VERSION
        or rollback_value.get("expected_build") != preserved.ROLLBACK_BUILD
        or set(debian) != {"keyed_source", "work_copy", "observer", "handoff_command"}
        or rootfs != resident.source_host
        or keyed
        != {
            "local_path": str(resident.source_host.path),
            "device_path": source_item.get("device_path"),
            "size": IMAGE_SIZE,
            "sha256": source_item.get("sha256"),
            "profile": phase3_observer.PROFILE,
        }
        or _dict(debian.get("work_copy"), "baseline work")
        != {"device_path": WORK_PATH, "required_initial_state": "absent"}
        or debian.get("handoff_command")
        != [base.HANDOFF_COMMAND, base.HANDOFF_TOKEN, keyed["device_path"], keyed["sha256"]]
        or observer_key != resident.observer_key
        or observer != expected_observer
        or target != expected_target
        or observation
        != {
            "handoff_attempt_limit": 1,
            "handoff_timeout_sec": HANDOFF_TIMEOUT_SEC,
            "ssh_marker_timeout_sec": SSH_MARKER_TIMEOUT_SEC,
            "candidate_return_timeout_sec": CANDIDATE_RETURN_TIMEOUT_SEC,
        }
        or authority
        != {
            "live_authority": False,
            "baseline_grants_device_authority": False,
            "fresh_d1_opening_d0_required": True,
            "original_preserved_terminal_directly_ineligible": True,
            "reduction_count": 1,
        }
    ):
        raise ContractError("D1 baseline interpretation changed")
    return BaselineSpec(
        manifest, run_id, resident.run_id, resident.manifest, resident.result,
        resident.journal, spec.manifest, cleanup_result, post_d0, candidate,
        rollback, rootfs, keyed["device_path"], WORK_PATH, EXPECTED_VERSION,
        EXPECTED_BUILD, target["bridge_device"], target["bridge_realpath"],
        target["recovery_serial_sha256"], target["recovery_profile"], observer_key,
        observer["public_key_sha256"], observer["device_ip"], observer["device_port"],
        observer["host_ncm_profile"], tuple(debian["handoff_command"]),
        observation["handoff_timeout_sec"], observation["ssh_marker_timeout_sec"],
        observation["candidate_return_timeout_sec"], review, spec.closure,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--print-review-closure", action="store_true")
    mode.add_argument("--execute-pre-cleanup-d0", action="store_true")
    mode.add_argument("--build-cleanup-manifest", action="store_true")
    mode.add_argument("--prepare-cleanup-approval", action="store_true")
    mode.add_argument("--execute-cleanup", action="store_true")
    mode.add_argument("--execute-post-cleanup-d0", action="store_true")
    mode.add_argument("--build-baseline", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--resident-manifest", type=Path)
    parser.add_argument("--expect-resident-manifest-sha256")
    parser.add_argument("--pre-cleanup-d0", type=Path)
    parser.add_argument("--expect-pre-cleanup-d0-sha256")
    parser.add_argument("--review-report", type=Path)
    parser.add_argument("--expect-review-report-sha256")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    parser.add_argument("--approval")
    parser.add_argument("--transaction-dir", type=Path)
    parser.add_argument("--post-cleanup-d0", type=Path)
    parser.add_argument("--expect-post-cleanup-d0-sha256")
    parser.add_argument("--operator-attended", action="store_true")
    parser.add_argument("--bridge-device")
    parser.add_argument("--expect-realpath")
    parser.add_argument("--bridge-host", default=base.a90ctl.DEFAULT_HOST)
    parser.add_argument("--bridge-port", type=int, default=base.a90ctl.DEFAULT_PORT)
    parser.add_argument("--remote-timeout", type=float, default=180.0)
    parser.add_argument("--bridge-timeout", type=float, default=180.0)
    parser.add_argument("--transfer-timeout", type=float, default=1200.0)
    parser.add_argument("--staging-command-timeout", type=float, default=1800.0)
    parser.add_argument("--flash-command-timeout", type=float, default=600.0)
    parser.add_argument("--ssh-connect-timeout", type=float, default=8.0)
    parser.add_argument("--poll-interval", type=float, default=3.0)
    parser.set_defaults(attended_approval=None, visible_approval=None)
    return parser


def _need(args: argparse.Namespace, names: tuple[str, ...], label: str) -> None:
    missing = [name for name in names if getattr(args, name) is None]
    if missing:
        raise ContractError(f"{label} arguments are incomplete: {missing}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.print_review_closure:
        result = {
            "schema": REVIEW_SCHEMA,
            "capabilities": [
                "attended-fixed-work-unlink-one-shot",
                "preserved-terminal-to-d1-baseline-reducer",
            ],
            "named_execution_critical_closure": review_source_records(),
            "device_contact": False,
            "device_write": False,
        }
    elif args.execute_pre_cleanup_d0:
        _need(args, ("run_id", "resident_manifest", "expect_resident_manifest_sha256", "bridge_device", "expect_realpath"), "pre-cleanup D0")
        result = execute_pre_cleanup_d0(args)
    elif args.build_cleanup_manifest:
        _need(args, ("run_id", "resident_manifest", "expect_resident_manifest_sha256", "pre_cleanup_d0", "expect_pre_cleanup_d0_sha256", "review_report", "expect_review_report_sha256"), "cleanup manifest")
        result = build_cleanup_manifest(args)
    else:
        _need(args, ("manifest", "expect_manifest_sha256"), "cleanup manifest")
        spec = load_cleanup_spec(args.manifest, args.expect_manifest_sha256)
        if args.prepare_cleanup_approval:
            result = prepare_approval(spec)
        elif args.execute_cleanup:
            _need(args, ("approval", "transaction_dir", "bridge_device", "expect_realpath"), "live cleanup")
            result = execute_cleanup(spec, args, approval=args.approval, transaction_dir=args.transaction_dir)
        elif args.execute_post_cleanup_d0:
            _need(args, ("bridge_device", "expect_realpath"), "post-cleanup D0")
            result = execute_post_cleanup_d0(spec, args)
        elif args.build_baseline:
            _need(args, ("post_cleanup_d0", "expect_post_cleanup_d0_sha256"), "baseline build")
            result = build_baseline(spec, args)
        else:
            raise ContractError("unsupported mode")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(f"a90-resident-preserved-d1-prep-v1: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
