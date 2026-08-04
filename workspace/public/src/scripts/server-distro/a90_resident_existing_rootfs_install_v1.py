#!/usr/bin/env python3
"""Install the exact A90 resident boot while preserving existing SD rootfs files.

This incident-recovery lane never stages, copies, unlinks, mounts, or hands off a
rootfs.  It proves one exact pre-existing source and one exact pre-existing work
copy with bounded read-only frames, transfers one manifest-bound boot candidate,
and closes only after resident health and the same protected bytes are proved.
The successful terminal is deliberately ineligible for switch_root.
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
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_phase2d_connected_preflight as connected  # noqa: E402
import a90_resident_promotion_v1 as resident  # noqa: E402
import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402
import a90_v3405_retained_work_cleanup as cleanup  # noqa: E402


CAPABILITY = "A90_ATTENDED_RESIDENT_INSTALL_EXISTING_SOURCE_WORK_PRESERVED_V1"
MODE = staging.PRESERVED_ROOTFS_INSTALL_MODE
MANIFEST_SCHEMA = staging.PRESERVED_ROOTFS_INSTALL_MANIFEST_SCHEMA
RESULT_SCHEMA = "a90_resident_install_existing_source_work_preserved_v1_result"
SUCCESS_STATUS = "PASS_A90_RESIDENT_INSTALLED_WORK_RETAINED"
TERMINAL_STATE = "RESIDENT_INSTALLED_WORK_RETAINED_CLOSED"
CONNECTED_D0_SCHEMA = "a90_resident_existing_rootfs_connected_d0_v1"
PATH_PREFLIGHT_SCHEMA = "a90_resident_existing_rootfs_path_preflight_v1"
REVIEW_SCHEMA = "a90-resident-existing-rootfs-install-independent-review-v1"
ROOTFS_DISPOSITION = "exact-source-work-preserved-no-stage"
PRIVATE_RUN_BASE = staging.PRIVATE_RUN_BASE
PRIVATE_ROOT = staging.PRIVATE_ROOT
WORK_PATH = str(staging.REMOTE_WORK)
IMAGE_SIZE = 2147483648
FILE_MODE = "600"
FILE_NLINK = 1
MAX_CMDV1X_WIRE_BYTES = 3800
D0_MAX_AGE_SEC = 900
MAX_CLOCK_SKEW_SEC = 5
RUN_RE = re.compile(r"^a90-v3406-debian-display-f1-[0-9]{8}-[0-9]{2}$")
SEQ_RE = re.compile(r"^[0-9]{2}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
SOURCE_RE = re.compile(
    r"^/mnt/sdext/a90/runtime/"
    r"debian-bookworm-arm64-phase2-display-v3406-keyed-"
    r"(?P<suffix>[0-9]{8}-[0-9]{2})\.img$"
)
CANDIDATE_SIZE = 61440000
CANDIDATE_SHA256 = "93ac207f6008959f663ec3df60e9bfd43ee855f72e57a4967c93bd0aa49d2d6f"
CANDIDATE_VERSION = "0.11.167"
CANDIDATE_BUILD = "phase3-minimal-f-power-recovery-ui"
ROLLBACK_SIZE = cleanup.EXPECTED_ROLLBACK_SIZE
ROLLBACK_SHA256 = cleanup.EXPECTED_ROLLBACK_SHA256
ROLLBACK_VERSION = cleanup.EXPECTED_VERSION
ROLLBACK_BUILD = cleanup.EXPECTED_BUILD
EXPECTED_CLEANUP_OUTCOME = "STOP_NO_RETRY_RETAINED_WORK_COPY_NOT_PROVEN_ABSENT"
EXPECTED_CLEANUP_ERROR = "A90P1 strict framing rejected output: A90P1 END lacks BEGIN"
INSTALL_EVENTS = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "live_session_end",
)
INSTALL_SUCCESS_ACTIONS = (
    "preflight",
    "approved",
    "protected-paths-pre-verified",
    "resident-promotion-guard-armed",
    "candidate-transfer-started",
    "candidate-flashed",
    "candidate-boot-ready",
    "candidate-health-verified",
    "protected-paths-post-verified",
    "closed",
)
INSTALL_SUCCESS_STATES = (
    "PREFLIGHT",
    "APPROVED",
    "APPROVED",
    "APPROVED",
    "APPROVED",
    "CANDIDATE_FLASHED",
    "CANDIDATE_FLASHED",
    "CANDIDATE_HEALTH_VERIFIED",
    "PROTECTED_PATHS_VERIFIED",
    TERMINAL_STATE,
)
CLEANUP_RUN_RE = re.compile(r"^a90-v3406-work-cleanup-(?P<suffix>[0-9]{8}-[0-9]{2})$")
PROTECTED_PROOF_SCHEMA = "a90_resident_existing_rootfs_protected_paths_v1"
COMMON_JOURNAL_KEYS = {
    "schema",
    "sequence",
    "timestamp_utc",
    "run_id",
    "manifest_sha256",
    "state",
    "action",
}


class ContractError(RuntimeError):
    """Raised when the preserved-rootfs install contract is not exact."""


@dataclass(frozen=True)
class Bound:
    path: Path
    size: int
    sha256: str


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_file(path: Path) -> str:
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


def _utc(value: Any, label: str) -> dt.datetime:
    if not base.is_canonical_utc_timestamp(value):
        raise ContractError(f"{label} is not canonical UTC")
    return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.UTC)


def _bound(path: Path, *, private: bool = True, mode: int | None = None) -> Bound:
    if path.is_symlink():
        raise ContractError(f"bound path is a symlink: {path}")
    resolved = path.resolve(strict=True)
    info = resolved.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ContractError(f"bound path is not regular: {resolved}")
    if mode is not None and stat.S_IMODE(info.st_mode) != mode:
        raise ContractError(f"bound path mode changed: {resolved}")
    if private:
        staging.require_below(resolved, PRIVATE_ROOT, "private bound file")
    else:
        staging.require_below(resolved, REPO_ROOT, "repository bound file")
    return Bound(resolved, info.st_size, sha256_file(resolved))


def _bound_dict(item: Bound) -> dict[str, Any]:
    return {"path": str(item.path), "size": item.size, "sha256": item.sha256}


def _load_bound(value: Any, label: str, *, private: bool = True) -> Bound:
    item = _dict(value, label)
    if set(item) != {"path", "size", "sha256"}:
        raise ContractError(f"{label} binding shape changed")
    actual = _bound(Path(_string(item.get("path"), f"{label}.path")), private=private)
    if actual.size != item.get("size") or actual.sha256 != _sha(
        item.get("sha256"), f"{label}.sha256"
    ):
        raise ContractError(f"{label} size/hash changed")
    return actual


def _read_json(bound: Bound, label: str) -> dict[str, Any]:
    try:
        value = json.loads(bound.path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} JSON is invalid") from exc
    return _dict(value, label)


def _write_private(path: Path, value: dict[str, Any]) -> None:
    staging.write_private_json_exclusive(path, value)


def _wire_bytes(command: list[str]) -> int:
    return len(base.a90ctl.encode_cmdv1_line(command).encode("utf-8")) + 1


def _remote(
    args: argparse.Namespace,
    command: list[str],
    label: str,
    *,
    allow_error: bool = False,
) -> dict[str, Any]:
    wire = _wire_bytes(command)
    if wire > MAX_CMDV1X_WIRE_BYTES:
        raise ContractError(
            f"{label} exceeds bounded cmdv1x frame: {wire} > {MAX_CMDV1X_WIRE_BYTES}"
        )
    receipt = base.run_f1_cmd(args, command, allow_error=allow_error)
    receipt["wire_bytes"] = wire
    return receipt


def _exact_line(text: Any, expected: str, label: str) -> None:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if lines.count(expected) != 1:
        raise ContractError(f"{label} output is not exact")


def _protected(value: dict[str, Any]) -> dict[str, Any]:
    return _dict(value.get("protected_rootfs"), "protected_rootfs")


def _protected_binding(
    spec: base.F1Spec,
    *,
    phase: str,
) -> tuple[dict[str, Any], dict[str, Any], str, str, str, str, str]:
    protected = _protected(spec.manifest)
    source = _dict(protected.get("source"), "protected source")
    work = _dict(protected.get("work"), "protected work")
    stage_path = _string(protected.get("stage_path"), "protected stage_path")
    source_path = _string(source.get("device_path"), "protected source path")
    work_path = _string(work.get("device_path"), "protected work path")
    source_sha = _sha(source.get("sha256"), "protected source sha256")
    work_sha = _sha(work.get("sha256"), "protected work sha256")
    if (
        SOURCE_RE.fullmatch(source_path) is None
        or work_path != WORK_PATH
        or source.get("size") != IMAGE_SIZE
        or work.get("size") != IMAGE_SIZE
        or source.get("mode") != FILE_MODE
        or work.get("mode") != FILE_MODE
        or source.get("nlink") != FILE_NLINK
        or work.get("nlink") != FILE_NLINK
        or stage_path != spec.stage.remote_stage_dir
    ):
        raise ContractError("protected path binding is not exact")
    if phase != "connected-d0":
        source_identity = _string(
            source.get("device_identity"), "protected source device identity"
        )
        work_identity = _string(
            work.get("device_identity"), "protected work device identity"
        )
        if (
            re.fullmatch(r"[0-9]+:[0-9]+", source_identity) is None
            or re.fullmatch(r"[0-9]+:[0-9]+", work_identity) is None
            or source_identity == work_identity
        ):
            raise ContractError("manifest-bound protected identities are not exact/distinct")
    return source, work, stage_path, source_path, work_path, source_sha, work_sha


def _protected_commands(spec: base.F1Spec, *, phase: str) -> dict[str, list[str]]:
    (
        _source,
        _work,
        stage_path,
        source_path,
        work_path,
        _source_sha,
        _work_sha,
    ) = _protected_binding(spec, phase=phase)
    stat_format = "%F|%s|%a|%h|%d:%i"
    stage_script = '[ ! -e "$1" ]&&[ ! -L "$1" ]&&printf "stage=absent\\n"'
    mount_script = (
        'for f in /proc/[0-9]*/mountinfo;do [ -r "$f" ]||continue;'
        '/bin/busybox grep -F "$1" "$f" >/dev/null 2>&1&&exit 74;'
        '/bin/busybox grep -F "$2" "$f" >/dev/null 2>&1&&exit 74;done;'
        'printf "mount_namespace_use=none\\n"'
    )
    loop_script = (
        'for f in /sys/block/loop*/loop/backing_file;do [ -r "$f" ]||continue;'
        'v=$(/bin/busybox cat "$f")||exit 71;'
        '[ "$v" != "$1" ]&&[ "$v" != "$2" ]||exit 72;done;'
        'printf "loop_use=none\\n"'
    )
    open_script = (
        'for f in /proc/[0-9]*/fd/*;do [ -e "$f" ]||continue;'
        'v=$(/bin/busybox readlink "$f")||continue;case "$v" in '
        '"$1"|"$2"|"$1 (deleted)"|"$2 (deleted)")exit 73;;esac;done;'
        'for f in /proc/[0-9]*/root;do [ -e "$f" ]||continue;'
        'v=$(/bin/busybox readlink "$f")||continue;case "$v" in '
        '"$1"|"$2"|"$1 (deleted)"|"$2 (deleted)")exit 73;;esac;done;'
        'printf "open_fd_use=none current_root_use=none\\n"'
    )
    return {
        "source_stat": [
            "run", "/bin/busybox", "stat", "-c", stat_format, source_path
        ],
        "work_stat": [
            "run", "/bin/busybox", "stat", "-c", stat_format, work_path
        ],
        "source_hash": ["run", "/bin/busybox", "sha256sum", source_path],
        "work_hash": ["run", "/bin/busybox", "sha256sum", work_path],
        "stage": [
            "run", "/bin/busybox", "sh", "-c", stage_script, "sh", stage_path
        ],
        "mounts": [
            "run", "/bin/busybox", "sh", "-c", mount_script, "sh",
            source_path, work_path,
        ],
        "loops": [
            "run", "/bin/busybox", "sh", "-c", loop_script, "sh",
            source_path, work_path,
        ],
        "opens": [
            "run", "/bin/busybox", "sh", "-c", open_script, "sh",
            source_path, work_path,
        ],
    }


def _validate_protected_receipt(
    value: Any,
    command: list[str],
    expected_line: str,
    label: str,
) -> dict[str, Any]:
    receipt = _dict(value, label)
    begin = _dict(receipt.get("begin"), f"{label} begin")
    end = _dict(receipt.get("end"), f"{label} end")
    if (
        set(receipt)
        != {"command", "rc", "status", "trust", "begin", "end", "text", "wire_bytes"}
        or receipt.get("command") != command
        or type(receipt.get("rc")) is not int
        or receipt.get("rc") != 0
        or receipt.get("status") != "ok"
        or receipt.get("trust") != "A90P1_V1_STRUCTURAL_ONLY"
        or set(begin) != {"argc", "cmd", "flags", "seq"}
        or set(end)
        != {"cmd", "duration_ms", "errno", "flags", "rc", "seq", "status"}
        or begin.get("cmd") != command[0]
        or end.get("cmd") != command[0]
        or begin.get("argc") != str(len(command))
        or re.fullmatch(r"[1-9][0-9]*", str(begin.get("seq") or "")) is None
        or begin.get("seq") != end.get("seq")
        or begin.get("flags") != ("0x2" if command[0] == "run" else "0x0")
        or end.get("flags") != begin.get("flags")
        or re.fullmatch(r"[0-9]+", str(end.get("duration_ms") or "")) is None
        or end.get("rc") != "0"
        or end.get("errno") != "0"
        or end.get("status") != "ok"
        or type(receipt.get("wire_bytes")) is not int
        or receipt.get("wire_bytes") != _wire_bytes(command)
        or receipt["wire_bytes"] > MAX_CMDV1X_WIRE_BYTES
    ):
        raise ContractError(f"{label} receipt is not exact")
    _exact_line(receipt.get("text"), expected_line, label)
    return receipt


def _validate_protected_proof(
    spec: base.F1Spec,
    value: Any,
    *,
    phase: str,
    allow_unbound_identity: bool = False,
) -> dict[str, Any]:
    proof = _dict(value, f"{phase} protected proof")
    (
        source,
        work,
        _stage_path,
        source_path,
        work_path,
        source_sha,
        work_sha,
    ) = _protected_binding(
        spec,
        phase="connected-d0" if allow_unbound_identity else phase,
    )
    source_identity = _string(proof.get("source_identity"), "source identity")
    work_identity = _string(proof.get("work_identity"), "work identity")
    if (
        re.fullmatch(r"[0-9]+:[0-9]+", source_identity) is None
        or re.fullmatch(r"[0-9]+:[0-9]+", work_identity) is None
        or source_identity == work_identity
    ):
        raise ContractError(f"{phase} protected identities are not exact/distinct")
    if not allow_unbound_identity and (
        source_identity != source.get("device_identity")
        or work_identity != work.get("device_identity")
    ):
        raise ContractError(f"{phase} protected identities changed from fresh D0")
    expected_keys = {
        "schema", "phase", "source_sha256", "work_sha256",
        "source_identity", "work_identity", "source_work_distinct",
        "stage_absent", "mount_namespace_use", "loop_use", "open_fd_use",
        "current_root_use", "staging_attempt_count", "rootfs_copy_count",
        "cleanup_dispatch_count", "handoff_attempt_count", "receipts",
    }
    if (
        set(proof) != expected_keys
        or proof.get("schema") != PROTECTED_PROOF_SCHEMA
        or proof.get("phase") != phase
        or proof.get("source_sha256") != source_sha
        or proof.get("work_sha256") != work_sha
        or proof.get("source_work_distinct") is not True
        or proof.get("stage_absent") is not True
        or proof.get("mount_namespace_use") is not False
        or proof.get("loop_use") is not False
        or proof.get("open_fd_use") is not False
        or proof.get("current_root_use") is not False
        or any(
            proof.get(name) != 0
            for name in (
                "staging_attempt_count", "rootfs_copy_count",
                "cleanup_dispatch_count", "handoff_attempt_count",
            )
        )
    ):
        raise ContractError(f"{phase} protected proof is not exact")
    commands = _protected_commands(spec, phase=phase)
    receipts = _dict(proof.get("receipts"), f"{phase} receipts")
    if set(receipts) != set(commands):
        raise ContractError(f"{phase} protected receipt set changed")
    expected_lines = {
        "source_stat": f"regular file|{IMAGE_SIZE}|{FILE_MODE}|{FILE_NLINK}|{source_identity}",
        "work_stat": f"regular file|{IMAGE_SIZE}|{FILE_MODE}|{FILE_NLINK}|{work_identity}",
        "source_hash": f"{source_sha}  {source_path}",
        "work_hash": f"{work_sha}  {work_path}",
        "stage": "stage=absent",
        "mounts": "mount_namespace_use=none",
        "loops": "loop_use=none",
        "opens": "open_fd_use=none current_root_use=none",
    }
    for label, command in commands.items():
        _validate_protected_receipt(
            receipts.get(label), command, expected_lines[label], f"{phase} {label}"
        )
    return proof


def protected_paths_preflight(
    spec: base.F1Spec,
    args: argparse.Namespace,
    *,
    phase: str,
) -> dict[str, Any]:
    if phase not in {"connected-d0", "pre-candidate", "post-candidate", "post-rollback"}:
        raise ContractError("protected-path phase is not allowlisted")
    (
        source,
        work,
        _stage_path,
        source_path,
        work_path,
        source_sha,
        work_sha,
    ) = _protected_binding(spec, phase=phase)
    commands = _protected_commands(spec, phase=phase)
    source_stat = _remote(
        args,
        commands["source_stat"],
        f"{phase} source stat",
    )
    work_stat = _remote(
        args,
        commands["work_stat"],
        f"{phase} work stat",
    )
    stat_re = re.compile(
        r"regular file\|2147483648\|600\|1\|(?P<identity>[0-9]+:[0-9]+)"
    )
    source_stats = stat_re.findall(str(source_stat.get("text") or ""))
    work_stats = stat_re.findall(str(work_stat.get("text") or ""))
    if len(source_stats) != 1 or len(work_stats) != 1 or source_stats[0] == work_stats[0]:
        raise ContractError(f"{phase} protected stat identity is not exact/distinct")
    if phase != "connected-d0" and (
        source_stats[0] != source.get("device_identity")
        or work_stats[0] != work.get("device_identity")
    ):
        raise ContractError(f"{phase} protected stat identity changed from fresh D0")

    source_hash = _remote(
        args,
        commands["source_hash"],
        f"{phase} source hash",
    )
    work_hash = _remote(
        args,
        commands["work_hash"],
        f"{phase} work hash",
    )
    _exact_line(source_hash.get("text"), f"{source_sha}  {source_path}", f"{phase} source hash")
    _exact_line(work_hash.get("text"), f"{work_sha}  {work_path}", f"{phase} work hash")

    stage = _remote(
        args,
        commands["stage"],
        f"{phase} stage absence",
    )
    _exact_line(stage.get("text"), "stage=absent", f"{phase} stage absence")

    mounts = _remote(
        args,
        commands["mounts"],
        f"{phase} mount use",
    )
    _exact_line(mounts.get("text"), "mount_namespace_use=none", f"{phase} mount use")

    loops = _remote(
        args,
        commands["loops"],
        f"{phase} loop use",
    )
    _exact_line(loops.get("text"), "loop_use=none", f"{phase} loop use")

    opens = _remote(
        args,
        commands["opens"],
        f"{phase} open use",
    )
    _exact_line(
        opens.get("text"),
        "open_fd_use=none current_root_use=none",
        f"{phase} open/current-root use",
    )
    receipts = {
        "source_stat": source_stat,
        "work_stat": work_stat,
        "source_hash": source_hash,
        "work_hash": work_hash,
        "stage": stage,
        "mounts": mounts,
        "loops": loops,
        "opens": opens,
    }
    if any(item["wire_bytes"] > MAX_CMDV1X_WIRE_BYTES for item in receipts.values()):
        raise ContractError("protected read exceeded the static wire budget")
    result = {
        "schema": PROTECTED_PROOF_SCHEMA,
        "phase": phase,
        "source_sha256": source_sha,
        "work_sha256": work_sha,
        "source_identity": source_stats[0],
        "work_identity": work_stats[0],
        "source_work_distinct": True,
        "stage_absent": True,
        "mount_namespace_use": False,
        "loop_use": False,
        "open_fd_use": False,
        "current_root_use": False,
        "staging_attempt_count": 0,
        "rootfs_copy_count": 0,
        "cleanup_dispatch_count": 0,
        "handoff_attempt_count": 0,
        "receipts": receipts,
    }
    return _validate_protected_proof(
        spec,
        result,
        phase=phase,
        allow_unbound_identity=phase == "connected-d0",
    )


CANONICAL_SUPPORT_SOURCES = {
    "support_run_d1_chroot_mvp": SCRIPT_DIR / "run_d1_chroot_mvp.py",
    "support_transition_contract": REVAL_DIR / "a90_transition_contract_v2.py",
    "support_workspace_bootstrap": REVAL_DIR / "_workspace_bootstrap.py",
    "support_a90_bridge": REVAL_DIR / "a90_bridge.py",
    "support_observation_pipeline": REVAL_DIR / "a90_observation_pipeline.py",
    "support_serial_lock": REVAL_DIR / "a90_serial_lock.py",
    "support_display_observer": SCRIPT_DIR / "a90_phase2d_display_observer.py",
    "support_harness_evidence": (
        REPO_ROOT
        / "workspace" / "public" / "src" / "harness" / "a90harness" / "evidence.py"
    ),
}
if set(path.resolve() for path in staging.COMMON_SUPPORT_FILES) != {
    path.resolve()
    for path in (
        *CANONICAL_SUPPORT_SOURCES.values(),
        REVAL_DIR / "a90ctl.py",
        REVAL_DIR / "serial_tcp_bridge.py",
    )
}:
    raise RuntimeError("canonical preserved-install support closure drifted")


REVIEW_SOURCES = {
    "repository_contract": REPO_ROOT / "AGENTS.md",
    "target_contract": REPO_ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md",
    "preserved_install_runner": Path(__file__).resolve(),
    "f1_orchestrator": SCRIPT_DIR / "a90_v3403_f1_orchestrator.py",
    "absent_only_staging": SCRIPT_DIR / "a90_v3403_absent_only_staging.py",
    "resident_promotion": SCRIPT_DIR / "a90_resident_promotion_v1.py",
    "connected_preflight": SCRIPT_DIR / "a90_phase2d_connected_preflight.py",
    "cleanup_incident_runner": SCRIPT_DIR / "a90_v3405_retained_work_cleanup.py",
    "flash_runner": REVAL_DIR / "native_init_flash.py",
    "a90ctl": REVAL_DIR / "a90ctl.py",
    "serial_bridge": REVAL_DIR / "serial_tcp_bridge.py",
    "modemmanager_guard": REVAL_DIR / "device_action_cdc_acm_observer_v1.py",
    "tcpctl_host": REVAL_DIR / "tcpctl_host.py",
    **CANONICAL_SUPPORT_SOURCES,
}


def review_source_records() -> dict[str, dict[str, Any]]:
    return {
        label: _bound_dict(_bound(path, private=False))
        for label, path in REVIEW_SOURCES.items()
    }


def _validate_review(value: Any) -> Bound:
    bound = _load_bound(value, "independent review", private=False)
    review = _read_json(bound, "independent review")
    if (
        review.get("schema") != REVIEW_SCHEMA
        or review.get("status") != "PASS_GO"
        or review.get("capability") != CAPABILITY
        or review.get("unresolved_findings") != []
        or review.get("permanent_boundaries_unchanged") is not True
        or review.get("device_authority_granted") is not False
        or review.get("named_execution_critical_closure")
        != review_source_records()
    ):
        raise ContractError("independent review is not exact PASS_GO")
    return bound


def _validate_prior_closed(value: Any, predecessor_run_id: str) -> tuple[Bound, Bound, tuple[Bound, ...]]:
    item = _dict(value, "prior_closed_f1")
    if set(item) != {"manifest", "result", "journal"}:
        raise ContractError("prior closed F1 binding shape changed")
    manifest = _load_bound(item.get("manifest"), "prior F1 manifest")
    result = _load_bound(item.get("result"), "prior F1 result")
    journal_value = item.get("journal")
    if not isinstance(journal_value, list) or not journal_value:
        raise ContractError("prior F1 journal binding is absent")
    journal = tuple(
        _load_bound(entry, f"prior F1 journal[{index}]")
        for index, entry in enumerate(journal_value)
    )
    binding = {
        "manifest": _bound_dict(manifest),
        "result": _bound_dict(result),
        "journal": [_bound_dict(entry) for entry in journal],
    }
    try:
        cleanup.validate_closed_f1_binding(binding, predecessor_run_id)
    except cleanup.ContractError as exc:
        raise ContractError("prior ordinary F1 closure is not exact") from exc
    return manifest, result, journal


def _validate_cleanup_incident(value: Any, predecessor_run_id: str) -> tuple[Bound, ...]:
    item = _dict(value, "cleanup_incident")
    names = ("manifest", "intent", "dispatch", "dispatch_error", "result")
    if set(item) != set(names):
        raise ContractError("cleanup incident binding shape changed")
    bounds = tuple(
        _load_bound(item.get(name), f"cleanup incident {name}") for name in names
    )
    manifest, intent, dispatch, dispatch_error, result = (
        _read_json(bound, f"cleanup incident {name}")
        for bound, name in zip(bounds, names, strict=True)
    )
    cleanup_run_id = _string(result.get("run_id"), "cleanup run_id")
    cleanup_match = CLEANUP_RUN_RE.fullmatch(cleanup_run_id)
    predecessor_suffix = predecessor_run_id.removeprefix(
        "a90-v3406-debian-display-f1-"
    )
    expected_paths = (
        PRIVATE_RUN_BASE / cleanup_run_id / "manifest.json",
        PRIVATE_RUN_BASE / cleanup_run_id / "live" / "intent.json",
        PRIVATE_RUN_BASE / cleanup_run_id / "live" / "dispatch.json",
        PRIVATE_RUN_BASE / cleanup_run_id / "live" / "dispatch-error.json",
        PRIVATE_RUN_BASE / cleanup_run_id / "live" / "result.json",
    )
    if cleanup_match is None or cleanup_match.group("suffix") != predecessor_suffix:
        raise ContractError("cleanup incident run identity is not canonical")
    if tuple(bound.path for bound in bounds) != tuple(
        path.resolve(strict=True) for path in expected_paths
    ):
        raise ContractError("cleanup incident files are outside the canonical run")

    manifest_keys = {
        "schema", "status", "run_id", "f1_run_id", "runner", "transport",
        "connected_d0", "independent_review", "closed_f1", "target",
        "work_image", "adjacent_paths", "authority",
    }
    intent_keys = {
        "schema", "created_utc", "run_id", "manifest_sha256",
        "approval_binding_sha256", "approval_token_sha256", "target",
        "before_health", "before_remote", "host_preservation_sha256",
        "transport_sha256", "device_path", "work_sha256",
        "source_disposition", "protected_source_sha256",
        "protected_source_path", "operator_attended",
        "physical_recovery_available", "dispatch_limit", "retry_forbidden",
    }
    dispatch_keys = {
        "schema", "created_utc", "run_id", "dispatch_count",
        "cleanup_command_sha256", "retry_forbidden", "approval_consumed",
    }
    dispatch_error_keys = {
        "schema", "created_utc", "run_id", "error",
        "cleanup_retransmitted", "read_only_reconciliation_allowed",
    }
    result_keys = {
        "schema", "created_utc", "run_id", "manifest_sha256",
        "approval_binding_sha256", "outcome", "dispatch_count",
        "cleanup_retransmitted", "response_proven", "post_presence",
        "post_health", "post_error", "effect_proven", "post_health_proven",
        "work_sha256", "host_preservation_sha256", "source_disposition",
        "protected_source_sha256", "protected_source_preserved",
        "operator_attended", "physical_recovery_available", "device_write",
        "deleted_path", "flash", "reboot_requested", "payload_sent",
        "other_device_commands",
    }
    work_image = _dict(manifest.get("work_image"), "cleanup work image")
    adjacent = _dict(manifest.get("adjacent_paths"), "cleanup adjacent paths")
    target = _dict(manifest.get("target"), "cleanup target")
    authority = _dict(manifest.get("authority"), "cleanup authority")
    cleanup_runner = _dict(manifest.get("runner"), "cleanup runner binding")
    cleanup_transport = _dict(manifest.get("transport"), "cleanup transport binding")
    intent_target = _dict(intent.get("target"), "cleanup intent target")
    bridge_process = _dict(
        intent_target.get("bridge_process"), "cleanup bridge process"
    )
    work_host = _load_bound(
        work_image.get("host_preservation"), "cleanup host preservation"
    )
    intent_health = _dict(intent.get("before_health"), "cleanup pre health")
    result_health = _dict(result.get("post_health"), "cleanup post health")
    exact_health = {
        "build": ROLLBACK_BUILD,
        "proven": True,
        "pstore_entries": 0,
        "selftest_fail": 0,
        "selftest_pass": 11,
        "selftest_warn": 1,
        "version": ROLLBACK_VERSION,
    }
    intent_created = _utc(intent.get("created_utc"), "cleanup intent timestamp")
    dispatch_created = _utc(dispatch.get("created_utc"), "cleanup dispatch timestamp")
    error_created = _utc(
        dispatch_error.get("created_utc"), "cleanup dispatch error timestamp"
    )
    result_created = _utc(result.get("created_utc"), "cleanup result timestamp")
    if (
        set(manifest) != manifest_keys
        or set(intent) != intent_keys
        or set(dispatch) != dispatch_keys
        or set(dispatch_error) != dispatch_error_keys
        or set(result) != result_keys
        or manifest.get("schema") != cleanup.SCHEMA
        or manifest.get("status") != cleanup.STATUS
        or manifest.get("f1_run_id") != predecessor_run_id
        or manifest.get("run_id") != cleanup_run_id
        or intent.get("run_id") != cleanup_run_id
        or intent.get("schema") != "a90_v3405_retained_work_cleanup_intent_v1"
        or intent.get("manifest_sha256") != bounds[0].sha256
        or intent_health != exact_health
        or _dict(intent.get("before_remote"), "cleanup pre remote")
        != {"framed_rc": 0, "proof": True}
        or intent.get("device_path") != WORK_PATH
        or intent.get("work_sha256") != work_image.get("sha256")
        or intent.get("host_preservation_sha256") != work_image.get("sha256")
        or intent.get("transport_sha256") != cleanup_transport.get("sha256")
        or intent.get("source_disposition") != adjacent.get("source_disposition")
        or intent.get("protected_source_sha256") != adjacent.get("source_sha256")
        or intent.get("protected_source_path") != adjacent.get("v3406_source")
        or intent.get("operator_attended") is not True
        or intent.get("physical_recovery_available") is not True
        or intent.get("dispatch_limit") != 1
        or intent.get("retry_forbidden") is not True
        or _sha(intent.get("approval_binding_sha256"), "cleanup approval binding")
        != result.get("approval_binding_sha256")
        or HEX64_RE.fullmatch(str(intent.get("approval_token_sha256") or "")) is None
        or dispatch.get("run_id") != cleanup_run_id
        or dispatch.get("schema") != "a90_v3405_retained_work_cleanup_dispatch_v1"
        or dispatch_error.get("run_id") != cleanup_run_id
        or dispatch.get("dispatch_count") != 1
        or dispatch.get("retry_forbidden") is not True
        or dispatch.get("approval_consumed") is not True
        or HEX64_RE.fullmatch(str(dispatch.get("cleanup_command_sha256") or "")) is None
        or dispatch_error.get("schema")
        != "a90_v3405_retained_work_cleanup_dispatch_error_v1"
        or dispatch_error.get("cleanup_retransmitted") is not False
        or dispatch_error.get("read_only_reconciliation_allowed") is not True
        or _dict(dispatch_error.get("error"), "cleanup dispatch error").get("message")
        != EXPECTED_CLEANUP_ERROR
        or _dict(dispatch_error.get("error"), "cleanup dispatch error")
        != {"message": EXPECTED_CLEANUP_ERROR, "type": "RuntimeError"}
        or result.get("schema") != cleanup.RESULT_SCHEMA
        or result.get("outcome") != EXPECTED_CLEANUP_OUTCOME
        or result.get("manifest_sha256") != bounds[0].sha256
        or result.get("approval_binding_sha256")
        != intent.get("approval_binding_sha256")
        or result.get("dispatch_count") != 1
        or result.get("cleanup_retransmitted") is not False
        or result.get("effect_proven") is not False
        or result.get("response_proven") is not False
        or result.get("post_health_proven") is not True
        or result_health != exact_health
        or result.get("post_error") is not None
        or _dict(result.get("post_presence"), "cleanup post presence")
        != {"framed_rc": 0, "source": "exact", "stage": "absent", "work": "present"}
        or result.get("protected_source_preserved") is not True
        or result.get("source_disposition") != adjacent.get("source_disposition")
        or result.get("protected_source_sha256") != adjacent.get("source_sha256")
        or result.get("work_sha256") != work_image.get("sha256")
        or result.get("host_preservation_sha256") != work_image.get("sha256")
        or result.get("operator_attended") is not True
        or result.get("physical_recovery_available") is not True
        or result.get("device_write") is not True
        or result.get("deleted_path") is not None
        or result.get("reboot_requested") is not False
        or result.get("payload_sent") is not False
        or result.get("flash") is not False
        or result.get("other_device_commands") != 0
        or set(work_image) != {"device_path", "size", "mode", "sha256", "host_preservation"}
        or work_image.get("device_path") != WORK_PATH
        or work_image.get("size") != IMAGE_SIZE
        or work_image.get("mode") != "0600"
        or work_host.size != IMAGE_SIZE
        or work_host.sha256 != work_image.get("sha256")
        or set(adjacent) != {"v3406_source", "source_disposition", "source_sha256", "run_stage"}
        or SOURCE_RE.fullmatch(str(adjacent.get("v3406_source") or "")) is None
        or adjacent.get("run_stage")
        != str(staging.derive_stage_dir(predecessor_run_id))
        or adjacent.get("source_disposition") != "exact-distinct-preserved"
        or _sha(adjacent.get("source_sha256"), "cleanup protected source")
        == _sha(work_image.get("sha256"), "cleanup work sha256")
        or target.get("profile") != staging.TARGET_PROFILE
        or target.get("expected_vendor_product") != "04e8:6861"
        or target.get("expected_version") != ROLLBACK_VERSION
        or target.get("expected_build") != ROLLBACK_BUILD
        or set(target)
        != {
            "bridge_device", "bridge_realpath_sha256", "expected_build",
            "expected_vendor_product", "expected_version", "profile",
            "usb_serial_sha256",
        }
        or set(intent_target)
        != {
            "bridge_process", "bridge_realpath_sha256", "matching_a90_bridges",
            "usb_serial_sha256",
        }
        or intent_target.get("matching_a90_bridges") != 1
        or intent_target.get("bridge_realpath_sha256")
        != target.get("bridge_realpath_sha256")
        or intent_target.get("usb_serial_sha256") != target.get("usb_serial_sha256")
        or bridge_process
        != {"local_endpoint": "127.0.0.1:54321", "matching_bridge_processes": 1}
        or set(cleanup_runner) != {"path", "size", "sha256"}
        or cleanup_runner.get("path") != str(Path(cleanup.__file__).resolve())
        or type(cleanup_runner.get("size")) is not int
        or cleanup_runner.get("size") <= 0
        or HEX64_RE.fullmatch(str(cleanup_runner.get("sha256") or "")) is None
        or set(cleanup_transport) != {"path", "size", "sha256"}
        or cleanup_transport.get("path") != str((REVAL_DIR / "a90ctl.py").resolve())
        or type(cleanup_transport.get("size")) is not int
        or cleanup_transport.get("size") <= 0
        or HEX64_RE.fullmatch(str(cleanup_transport.get("sha256") or "")) is None
        or authority
        != {
            "device_write_authorized": False,
            "fresh_exact_approval_required": True,
            "single_unlink_dispatch": True,
            "source_preservation_required": True,
            "unlink_retry_forbidden": True,
        }
        or not (intent_created <= dispatch_created <= error_created <= result_created)
    ):
        raise ContractError("cleanup incident is not the exact non-retransmitted terminal")
    return bounds


def _validate_connected_evidence(
    value: Any,
    *,
    run_id: str,
    candidate: Bound,
    rollback: Bound,
    proof_spec: base.F1Spec,
    cleanup_result: Bound,
    require_fresh: bool,
) -> tuple[Bound, Bound, dict[str, Any], dict[str, Any]]:
    target = _dict(value, "target")
    connected_bound = _load_bound(target.get("connected_d0_result"), "connected D0")
    paths_bound = _load_bound(
        target.get("connected_path_preflight"), "protected path D0"
    )
    connected_value = _read_json(connected_bound, "connected D0")
    paths_value = _read_json(paths_bound, "protected path D0")
    connected_time = _utc(connected_value.get("timestamp_utc"), "connected D0 timestamp")
    paths_time = _utc(paths_value.get("timestamp_utc"), "path D0 timestamp")
    cleanup_value = _read_json(cleanup_result, "cleanup result")
    cleanup_time = _utc(cleanup_value.get("created_utc"), "cleanup result timestamp")
    now = dt.datetime.now(dt.UTC).replace(microsecond=0)
    connected_target = _dict(connected_value.get("target"), "connected D0 target")
    health = _dict(connected_value.get("health"), "connected D0 health")
    artifacts = _dict(connected_value.get("artifacts"), "connected D0 artifacts")
    connected_keys = {
        "schema", "timestamp_utc", "run_id", "predecessor_run_id",
        "device_ip", "target", "host_ncm", "health", "artifacts",
        "predecessor_manifest", "cleanup_result", "safety",
    }
    paths_keys = {
        "schema", "timestamp_utc", "run_id", "connected_d0_sha256",
        "cleanup_result_sha256", "proof", "safety",
    }
    age = (now - paths_time).total_seconds()
    if (
        set(connected_value) != connected_keys
        or set(paths_value) != paths_keys
        or connected_value.get("schema") != CONNECTED_D0_SCHEMA
        or connected_value.get("run_id") != run_id
        or connected_time <= cleanup_time
        or paths_time < connected_time
        or paths_time > now + dt.timedelta(seconds=MAX_CLOCK_SKEW_SEC)
        or (require_fresh and (age < -MAX_CLOCK_SKEW_SEC or age > D0_MAX_AGE_SEC))
        or connected_target.get("profile") != staging.TARGET_PROFILE
        or connected_target.get("matching_a90_usb_devices") != 1
        or connected_target.get("bridge_device") != target.get("bridge_device")
        or connected_target.get("bridge_selected_realpath")
        != target.get("bridge_selected_realpath")
        or health.get("version") != ROLLBACK_VERSION
        or health.get("version_build") != ROLLBACK_BUILD
        or _dict(health.get("selftest"), "connected selftest").get("fail") != 0
        or health.get("pstore_entries") != 0
        or _dict(artifacts.get("candidate_boot"), "connected candidate").get("sha256")
        != candidate.sha256
        or _dict(artifacts.get("rollback_boot"), "connected rollback").get("sha256")
        != rollback.sha256
        or connected_value.get("safety")
        != {
            "device_write": False,
            "flash": False,
            "payload_sent": False,
            "reboot_requested": False,
            "rootfs_staged": False,
            "userdata_touched": False,
        }
    ):
        raise ContractError("connected D0 is not fresh exact V2321 evidence")
    proof = _validate_protected_proof(
        proof_spec,
        paths_value.get("proof"),
        phase="connected-d0",
    )
    path_safety = _dict(paths_value.get("safety"), "protected path safety")
    if (
        paths_value.get("schema") != PATH_PREFLIGHT_SCHEMA
        or paths_value.get("run_id") != run_id
        or paths_value.get("connected_d0_sha256") != connected_bound.sha256
        or paths_value.get("cleanup_result_sha256") != cleanup_result.sha256
        or path_safety
        != {
            "device_write": False,
            "flash": False,
            "payload_sent": False,
            "reboot_requested": False,
            "rootfs_staged": False,
            "rootfs_copied": False,
            "cleanup_dispatched": False,
            "handoff_dispatched": False,
        }
    ):
        raise ContractError("protected path D0 is not exact")
    return connected_bound, paths_bound, connected_value, paths_value


def _execution_bounds(value: Any) -> dict[str, Bound]:
    closure = _dict(value, "execution_closure")
    expected = {
        "runner": Path(__file__).resolve(),
        "orchestrator": Path(base.__file__).resolve(),
        "staging_adapter": Path(staging.__file__).resolve(),
        "resident_helpers": Path(resident.__file__).resolve(),
        "connected_helpers": Path(connected.__file__).resolve(),
        "cleanup_helpers": Path(cleanup.__file__).resolve(),
        "flash_runner": base.NATIVE_FLASH_PATH,
        "a90ctl": REVAL_DIR / "a90ctl.py",
        "serial_bridge": REVAL_DIR / "serial_tcp_bridge.py",
        "modemmanager_guard": REVAL_DIR / "device_action_cdc_acm_observer_v1.py",
        "tcpctl_host": REVAL_DIR / "tcpctl_host.py",
        **CANONICAL_SUPPORT_SOURCES,
    }
    if set(closure) != set(expected):
        raise ContractError("execution closure labels changed")
    result: dict[str, Bound] = {}
    for label, expected_path in expected.items():
        bound = _load_bound(closure.get(label), f"execution closure {label}", private=False)
        if bound.path != expected_path.resolve(strict=True):
            raise ContractError(f"execution closure {label} path changed")
        result[label] = bound
    return result


def validate_promotion_manifest(
    spec: base.F1Spec,
    *,
    recovery: bool = False,
) -> dict[str, Any]:
    value = _dict(spec.manifest.get("resident_promotion"), "resident_promotion")
    runner = _dict(value.get("runner"), "resident_promotion.runner")
    expected_runner = _bound(Path(__file__).resolve(), private=False)
    if (
        set(value)
        != {
            "mode",
            "runner",
            "rootfs_preflight_disposition",
            "success_terminal",
            "terminal_state",
            "candidate_health_checks",
            "rollback_on_post_attempt_failure",
            "handoff_eligible",
            "staging_attempt_count",
            "rootfs_copy_count",
            "cleanup_dispatch_count",
        }
        or value.get("mode") != MODE
        or runner != _bound_dict(expected_runner)
        or value.get("rootfs_preflight_disposition") != ROOTFS_DISPOSITION
        or value.get("success_terminal") != SUCCESS_STATUS
        or value.get("terminal_state") != TERMINAL_STATE
        or value.get("candidate_health_checks") != 1
        or value.get("rollback_on_post_attempt_failure") is not True
        or value.get("handoff_eligible") is not False
        or any(
            value.get(name) != 0
            for name in (
                "staging_attempt_count",
                "rootfs_copy_count",
                "cleanup_dispatch_count",
            )
        )
    ):
        raise ContractError("preserved-rootfs promotion manifest changed")
    return {"mode": MODE, "runner": runner, "recovery": recovery}


def load_spec(
    manifest_path: Path,
    expected_manifest_sha256: str,
    *,
    recovery: bool = False,
) -> base.F1Spec:
    manifest_bound = _bound(manifest_path)
    if manifest_bound.sha256 != _sha(expected_manifest_sha256, "manifest sha256"):
        raise ContractError("manifest SHA256 mismatch")
    manifest = _read_json(manifest_bound, "manifest")
    run_id = _string(manifest.get("run_id"), "run_id")
    if (
        set(manifest)
        != {
            "schema",
            "status",
            "run_id",
            "capability",
            "target",
            "candidate_boot",
            "rollback_boot",
            "transport",
            "protected_rootfs",
            "observer",
            "observation",
            "recovery",
            "prior_closed_f1",
            "cleanup_incident",
            "execution_closure",
            "resident_promotion",
            "independent_review",
            "authority",
        }
        or manifest.get("schema") != MANIFEST_SCHEMA
        or manifest.get("status") != staging.FINAL_MANIFEST_STATUS
        or manifest.get("capability") != CAPABILITY
        or RUN_RE.fullmatch(run_id) is None
        or manifest_bound.path.parent != (PRIVATE_RUN_BASE / run_id).resolve(strict=True)
    ):
        raise ContractError("preserved-rootfs manifest root is not exact")
    target = _dict(manifest.get("target"), "target")
    if (
        target.get("profile") != staging.TARGET_PROFILE
        or target.get("current_version") != ROLLBACK_VERSION
        or target.get("current_build") != ROLLBACK_BUILD
        or target.get("bridge_selected_exact") is not True
        or not _string(target.get("bridge_device"), "bridge_device").startswith(
            "/dev/serial/by-id/usb-A90-LNX_"
        )
        or staging.BRIDGE_REALPATH_RE.fullmatch(
            _string(target.get("bridge_selected_realpath"), "bridge realpath")
        )
        is None
    ):
        raise ContractError("target binding is not exact A90 V2321")

    candidate_value = _dict(manifest.get("candidate_boot"), "candidate_boot")
    rollback_value = _dict(manifest.get("rollback_boot"), "rollback_boot")
    candidate = _load_bound(
        {name: candidate_value.get(name) for name in ("path", "size", "sha256")},
        "candidate_boot",
    )
    rollback = _load_bound(
        {name: rollback_value.get(name) for name in ("path", "size", "sha256")},
        "rollback_boot",
    )
    if (
        candidate_value.get("partition") != "boot"
        or candidate.size != CANDIDATE_SIZE
        or candidate.sha256 != CANDIDATE_SHA256
        or candidate_value.get("expected_version") != CANDIDATE_VERSION
        or candidate_value.get("expected_build") != CANDIDATE_BUILD
        or rollback_value.get("partition") != "boot"
        or rollback.size != ROLLBACK_SIZE
        or rollback.sha256 != ROLLBACK_SHA256
        or rollback_value.get("expected_version") != ROLLBACK_VERSION
        or rollback_value.get("expected_build") != ROLLBACK_BUILD
    ):
        raise ContractError("boot-only candidate/rollback identity changed")

    protected = _protected(manifest)
    predecessor_run_id = _string(protected.get("predecessor_run_id"), "predecessor_run_id")
    source = _dict(protected.get("source"), "protected source")
    work = _dict(protected.get("work"), "protected work")
    source_path = _string(source.get("device_path"), "protected source path")
    source_match = SOURCE_RE.fullmatch(source_path)
    if (
        RUN_RE.fullmatch(predecessor_run_id) is None
        or predecessor_run_id == run_id
        or source_match is None
        or predecessor_run_id.rsplit("-", 2)[-2:] != source_match.group("suffix").rsplit("-", 1)
    ):
        raise ContractError("protected source is not derived from predecessor run")
    source_host = _load_bound(source.get("host_preservation"), "source host preservation")
    work_host = _load_bound(work.get("host_preservation"), "work host preservation",)
    source_sha = _sha(source.get("sha256"), "source sha256")
    work_sha = _sha(work.get("sha256"), "work sha256")
    source_identity = _string(source.get("device_identity"), "source device identity")
    work_identity = _string(work.get("device_identity"), "work device identity")
    stage_path = _string(protected.get("stage_path"), "stage_path")
    if (
        source.get("size") != IMAGE_SIZE
        or source.get("mode") != FILE_MODE
        or source.get("nlink") != FILE_NLINK
        or source_host.size != IMAGE_SIZE
        or source_host.sha256 != source_sha
        or work.get("device_path") != WORK_PATH
        or work.get("size") != IMAGE_SIZE
        or work.get("mode") != FILE_MODE
        or work.get("nlink") != FILE_NLINK
        or work_host.size != IMAGE_SIZE
        or work_host.sha256 != work_sha
        or source_sha == work_sha
        or re.fullmatch(r"[0-9]+:[0-9]+", source_identity) is None
        or re.fullmatch(r"[0-9]+:[0-9]+", work_identity) is None
        or source_identity == work_identity
        or stage_path != str(staging.derive_stage_dir(run_id))
        or protected.get("disposition") != ROOTFS_DISPOSITION
        or protected.get("handoff_eligible") is not False
    ):
        raise ContractError("protected source/work identity is not exact and distinct")

    prior_manifest, prior_result, prior_journal = _validate_prior_closed(
        manifest.get("prior_closed_f1"), predecessor_run_id
    )
    cleanup_bounds = _validate_cleanup_incident(
        manifest.get("cleanup_incident"), predecessor_run_id
    )
    if _read_json(cleanup_bounds[0], "cleanup manifest").get("closed_f1") != manifest.get(
        "prior_closed_f1"
    ):
        raise ContractError("cleanup incident and predecessor closure bindings differ")
    cleanup_result = cleanup_bounds[-1]
    prior_close = _utc(
        _read_json(prior_journal[-1], "prior terminal journal").get("timestamp_utc"),
        "prior terminal timestamp",
    )
    cleanup_created = _utc(
        _read_json(cleanup_result, "cleanup result").get("created_utc"),
        "cleanup result timestamp",
    )
    if cleanup_created <= prior_close:
        raise ContractError("cleanup incident does not follow the closed ordinary F1")
    proof_spec = SimpleNamespace(
        manifest=manifest,
        stage=SimpleNamespace(remote_stage_dir=stage_path),
    )
    connected_d0, connected_paths, connected_value, _ = _validate_connected_evidence(
        target,
        run_id=run_id,
        candidate=candidate,
        rollback=rollback,
        proof_spec=proof_spec,
        cleanup_result=cleanup_result,
        require_fresh=not recovery,
    )
    if (
        _dict(connected_value.get("target"), "connected target").get("usb_serial_sha256")
        != target.get("usb_serial_sha256")
    ):
        raise ContractError("manifest USB serial binding differs from fresh D0")

    closure = _execution_bounds(manifest.get("execution_closure"))
    review = _validate_review(manifest.get("independent_review"))
    transport = _dict(manifest.get("transport"), "transport")
    if (
        transport.get("candidate_and_rollback_runner")
        != str(closure["flash_runner"].path)
        or transport.get("runner_size") != closure["flash_runner"].size
        or transport.get("runner_sha256") != closure["flash_runner"].sha256
        or transport.get("only_partition_payload") != "boot"
        or transport.get("forbidden_partition_writes") is not True
    ):
        raise ContractError("flash transport binding is not boot-only exact")

    observer = _dict(manifest.get("observer"), "observer")
    observer_key = _load_bound(observer.get("private_key"), "observer private key")
    observer_public = _load_bound(observer.get("public_key"), "observer public key")
    if (
        observer.get("transport_scope") != base.OBSERVER_TRANSPORT_SCOPE
        or observer.get("wifi_or_external_network") is not False
        or observer.get("device_ip") != connected_value.get("device_ip")
        or sha256_file(observer_public.path) != observer_public.sha256
    ):
        raise ContractError("observer binding is not exact USB-local NCM")
    observation = _dict(manifest.get("observation"), "observation")
    for name in (
        "candidate_boot_timeout_sec",
        "handoff_timeout_sec",
        "ssh_marker_timeout_sec",
        "candidate_return_timeout_sec",
        "rollback_boot_timeout_sec",
    ):
        if type(observation.get(name)) is not int or observation[name] <= 0:
            raise ContractError(f"observation {name} is not positive")
    if (
        observation.get("mode") != base.UNATTENDED_OBSERVATION_MODE
        or observation.get("display_required") is not False
        or observation.get("handoff_attempt_limit") != 0
    ):
        raise ContractError("preserved install observation must have no handoff/display")

    recovery_value = _dict(manifest.get("recovery"), "recovery")
    recovery_serial_sha = _sha(recovery_value.get("adb_serial_sha256"), "recovery serial")
    recovery_evidence_value = recovery_value.get("identity_evidence")
    if not isinstance(recovery_evidence_value, list) or len(recovery_evidence_value) != 2:
        raise ContractError("recovery identity evidence must contain two records")
    recovery_evidence = tuple(
        _load_bound(entry, f"recovery identity[{index}]")
        for index, entry in enumerate(recovery_evidence_value)
    )
    recovery_serial = base.recovery_serial_from_evidence(
        tuple(
            staging.BoundFile(f"recovery[{index}]", item.path, item.size, item.sha256)
            for index, item in enumerate(recovery_evidence)
        ),
        recovery_serial_sha,
    )
    authority = _dict(manifest.get("authority"), "authority")
    if authority != {
        "candidate_transfer_authorized": False,
        "live_authority": False,
        "manifest_grants_live_authority": False,
        "fresh_operator_approval_required": True,
        "rollback_authority_activates_after_candidate_start": True,
        "operator_attendance_required": True,
    }:
        raise ContractError("manifest authority changed")

    promotion = validate_promotion_manifest(
        SimpleNamespace(manifest=manifest), recovery=recovery
    )
    if promotion.get("mode") != MODE:
        raise ContractError("preserved promotion mode failed validation")
    bound_files: list[staging.BoundFile] = []
    for label, item in (
        ("target.connected_d0_result", connected_d0),
        ("target.connected_path_preflight", connected_paths),
        ("candidate_boot", candidate),
        ("rollback_boot", rollback),
        ("transport", closure["flash_runner"]),
        ("host_preparation", connected_paths),
        ("protected_source_host", source_host),
        ("protected_work_host", work_host),
        ("prior_manifest", prior_manifest),
        ("prior_result", prior_result),
        *[(f"prior_journal[{i}]", item) for i, item in enumerate(prior_journal)],
        *[(f"cleanup_incident[{i}]", item) for i, item in enumerate(cleanup_bounds)],
        ("independent_review", review),
        *[(f"execution.{label}", item) for label, item in closure.items()],
        *[(f"recovery[{i}]", item) for i, item in enumerate(recovery_evidence)],
        ("observer_key", observer_key),
        ("observer_public", observer_public),
    ):
        bound_files.append(staging.BoundFile(label, item.path, item.size, item.sha256))

    stage_spec = staging.StageSpec(
        run_id=run_id,
        manifest_path=manifest_bound.path,
        manifest_sha256=manifest_bound.sha256,
        local_image=source_host.path,
        local_size=source_host.size,
        local_sha256=source_host.sha256,
        remote_final=source_path,
        remote_work=WORK_PATH,
        remote_stage_dir=stage_path,
        remote_payload=f"{stage_path}/{staging.STAGE_PAYLOAD_NAME}",
        bridge_device=_string(target.get("bridge_device"), "bridge_device"),
        bridge_realpath=_string(target.get("bridge_selected_realpath"), "bridge realpath"),
        observer_device=_string(observer.get("device_ip"), "observer device"),
        adapter_size=closure["staging_adapter"].size,
        adapter_sha256=closure["staging_adapter"].sha256,
        tcpctl_host=closure["tcpctl_host"].path,
        tcpctl_host_size=closure["tcpctl_host"].size,
        tcpctl_host_sha256=closure["tcpctl_host"].sha256,
        bound_files=tuple(bound_files),
        rootfs_profile=staging.PHASE3_PROFILE,
        starting_version=ROLLBACK_VERSION,
        starting_build=ROLLBACK_BUILD,
    )
    return base.F1Spec(
        stage=stage_spec,
        manifest=manifest,
        candidate=staging.BoundFile("candidate_boot", candidate.path, candidate.size, candidate.sha256),
        rollback=staging.BoundFile("rollback_boot", rollback.path, rollback.size, rollback.sha256),
        flash_runner=staging.BoundFile(
            "transport", closure["flash_runner"].path, closure["flash_runner"].size, closure["flash_runner"].sha256
        ),
        candidate_version=CANDIDATE_VERSION,
        candidate_build=CANDIDATE_BUILD,
        rollback_version=ROLLBACK_VERSION,
        rollback_build=ROLLBACK_BUILD,
        handoff_command=(base.HANDOFF_COMMAND, base.HANDOFF_TOKEN, source_path, source_sha),
        observer_key=observer_key.path,
        observer_public_key_sha256=observer_public.sha256,
        observer_device=_string(observer.get("device_ip"), "observer device"),
        observer_port=int(observer.get("device_port")),
        observer_host_ncm_profile=_string(observer.get("host_ncm_profile"), "host NCM profile"),
        candidate_boot_timeout=observation["candidate_boot_timeout_sec"],
        handoff_timeout=observation["handoff_timeout_sec"],
        ssh_marker_timeout=observation["ssh_marker_timeout_sec"],
        candidate_return_timeout=observation["candidate_return_timeout_sec"],
        rollback_boot_timeout=observation["rollback_boot_timeout_sec"],
        observation_mode=base.UNATTENDED_OBSERVATION_MODE,
        attended_window_sec=0,
        pre_handoff_attempt_limit=0,
        handoff_attempt_limit=0,
        display_required=False,
        display_profile="none",
        display_uid=0,
        display_gid=0,
        display_max_attempts=0,
        display_visible_text=(),
        recovery_serial_sha256=recovery_serial_sha,
        recovery_serial=recovery_serial,
        recovery_evidence=tuple(
            staging.BoundFile(f"recovery[{i}]", item.path, item.size, item.sha256)
            for i, item in enumerate(recovery_evidence)
        ),
        orchestrator_size=closure["orchestrator"].size,
        orchestrator_sha256=closure["orchestrator"].sha256,
    )


def _validate_candidate_health(spec: base.F1Spec, value: Any) -> dict[str, Any]:
    health = _dict(value, "preserved install candidate health")
    if set(health) != {"native", "pstore", "ncm"}:
        raise ContractError("preserved install health keys are not exact")
    resident._require_exact_native_health(  # noqa: SLF001
        spec,
        _dict(health.get("native"), "preserved candidate native health"),
    )
    try:
        base.validate_pstore_before_handoff_receipt(
            health.get("pstore"),
            allow_legacy_empty=True,
        )
    except base.ContractError as exc:
        raise ContractError("preserved install pstore health is not exact") from exc

    ncm = _dict(health.get("ncm"), "preserved install NCM health")
    common_ncm = {
        "same_current_acm_usb_parent", "exact_interface_count", "profile_bound",
        "mutated", "profile_check", "active_before", "ready",
    }
    expected_ncm = common_ncm | (
        {"modify", "activate", "active_after"}
        if ncm.get("mutated") is True
        else set()
    )
    host_receipt_keys = {"command", "returncode", "stdout", "stderr"}
    profile_check = _dict(ncm.get("profile_check"), "preserved NCM profile check")
    active_before = _dict(ncm.get("active_before"), "preserved NCM active check")
    ready = _dict(ncm.get("ready"), "preserved NCM readiness")
    profile_name = spec.observer_host_ncm_profile
    if (
        set(ncm) != expected_ncm
        or ncm.get("same_current_acm_usb_parent") is not True
        or ncm.get("exact_interface_count") != 1
        or ncm.get("profile_bound") is not True
        or type(ncm.get("mutated")) is not bool
        or set(profile_check) != host_receipt_keys
        or profile_check.get("returncode") != 0
        or str(profile_check.get("stdout") or "").strip()
        != base.HOST_NCM_CONNECTION_TYPE
        or set(active_before) != host_receipt_keys
        or ready
        != {
            "verified_a90_ncm": True,
            "direct_route": True,
            "host_cidr_present": True,
            "device_ping": True,
        }
    ):
        raise ContractError("preserved install NCM health is not exact")
    selected = active_before
    if ncm["mutated"]:
        for label in ("modify", "activate"):
            receipt = _dict(ncm.get(label), f"preserved NCM {label}")
            if set(receipt) != host_receipt_keys or receipt.get("returncode") != 0:
                raise ContractError(f"preserved NCM {label} failed")
        selected = _dict(ncm.get("active_after"), "preserved NCM active-after")
        if set(selected) != host_receipt_keys:
            raise ContractError("preserved NCM active-after keys changed")
    if (
        selected.get("returncode") != 0
        or str(selected.get("stdout") or "").splitlines()[:1] != [profile_name]
    ):
        raise ContractError("preserved NCM selected profile is not exact")
    return health


def _validate_final_health(spec: base.F1Spec, value: Any) -> dict[str, Any]:
    health = _dict(value, "preserved rollback final health")
    required = {
        "exact_bridge", "selected_realpath", "channel", "version", "build",
        "selftest_fail_zero", "pstore_entries_zero", "baseline",
    }
    allowed = required | {"rollback_boot_modemmanager_guard"}
    baseline = _dict(health.get("baseline"), "preserved rollback baseline")
    if (
        set(health) not in (required, allowed)
        or health.get("exact_bridge") is not True
        or health.get("selected_realpath") != spec.stage.bridge_realpath
        or health.get("version") != spec.rollback_version
        or health.get("build") != spec.rollback_build
        or health.get("selftest_fail_zero") is not True
        or health.get("pstore_entries_zero") is not True
        or not isinstance(health.get("channel"), dict)
    ):
        raise ContractError("preserved rollback final health is not exact")
    resident._require_exact_native_health(  # noqa: SLF001
        SimpleNamespace(
            candidate_version=spec.rollback_version,
            candidate_build=spec.rollback_build,
            stage=spec.stage,
        ),
        {
            "exact_bridge": health["exact_bridge"],
            "selected_realpath": health["selected_realpath"],
            "version": baseline.get("version"),
            "selftest": baseline.get("selftest"),
        },
    )
    return health


def _validate_success_result(spec: base.F1Spec, value: Any) -> dict[str, Any]:
    result = _dict(value, "preserved install result")
    expected_keys = {
        "schema",
        "run_id",
        "status",
        "manifest_sha256",
        "candidate_sha256",
        "candidate_transfer_count",
        "candidate_replay",
        "rollback_transfer_count",
        "rollback_required",
        "device_safety_state",
        "handoff_eligible",
        "staging_attempt_count",
        "rootfs_copy_count",
        "cleanup_dispatch_count",
        "candidate_health_check_count",
        "health",
        "protected_paths",
        "timeline_events",
    }
    protected = _dict(result.get("protected_paths"), "result protected_paths")
    if (
        set(result) != expected_keys
        or result.get("schema") != RESULT_SCHEMA
        or result.get("run_id") != spec.stage.run_id
        or result.get("status") != SUCCESS_STATUS
        or result.get("manifest_sha256") != spec.stage.manifest_sha256
        or result.get("candidate_sha256") != CANDIDATE_SHA256
        or result.get("candidate_transfer_count") != 1
        or result.get("candidate_replay") is not False
        or result.get("rollback_transfer_count") != 0
        or result.get("rollback_required") is not False
        or result.get("device_safety_state") != "RESIDENT_HEALTHY"
        or result.get("handoff_eligible") is not False
        or result.get("candidate_health_check_count") != 1
        or any(
            result.get(name) != 0
            for name in (
                "staging_attempt_count",
                "rootfs_copy_count",
                "cleanup_dispatch_count",
            )
        )
        or tuple(result.get("timeline_events") or ()) != INSTALL_EVENTS
    ):
        raise ContractError("preserved install success result is not exact")
    _validate_candidate_health(spec, result.get("health"))
    _validate_protected_proof(
        spec,
        protected,
        phase="post-candidate",
    )
    return result


def _publish_result(spec: base.F1Spec, transaction_dir: Path, result: dict[str, Any]) -> None:
    exact = _validate_success_result(spec, result)
    path = transaction_dir / "result.json"
    if path.exists():
        base.require_private_regular(path)
        if json.loads(path.read_text(encoding="utf-8")) != exact:
            raise ContractError("existing preserved install result changed")
        return
    base.write_private_json_exclusive(path, exact)


def _result_from_terminal(spec: base.F1Spec, record: dict[str, Any]) -> dict[str, Any]:
    common = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
    }
    result_keys = {
        "schema",
        "run_id",
        "status",
        "manifest_sha256",
        "candidate_sha256",
        "candidate_transfer_count",
        "candidate_replay",
        "rollback_transfer_count",
        "rollback_required",
        "device_safety_state",
        "handoff_eligible",
        "staging_attempt_count",
        "rootfs_copy_count",
        "cleanup_dispatch_count",
        "candidate_health_check_count",
        "health",
        "protected_paths",
        "timeline_events",
    }
    if (
        set(record) != common | (result_keys - {"schema", "run_id", "manifest_sha256"})
        or record.get("state") != TERMINAL_STATE
        or record.get("action") != "closed"
    ):
        raise ContractError("preserved install terminal journal changed")
    result = {key: record.get(key) for key in result_keys}
    result["schema"] = RESULT_SCHEMA
    result["run_id"] = spec.stage.run_id
    result["manifest_sha256"] = spec.stage.manifest_sha256
    return _validate_success_result(spec, result)


def _journal_keyset(record: dict[str, Any], payload: set[str], label: str) -> None:
    if set(record) != COMMON_JOURNAL_KEYS | payload:
        raise ContractError(f"{label} journal keyset changed")


def _validate_success_journal(
    spec: base.F1Spec,
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    actions = tuple(str(record.get("action")) for record in records)
    states = tuple(str(record.get("state")) for record in records)
    if actions != INSTALL_SUCCESS_ACTIONS or states != INSTALL_SUCCESS_STATES:
        raise ContractError("preserved install journal success sequence is not exact")
    payloads = {
        "preflight": {
            "device_write", "candidate_attempted", "candidate_sha256",
            "rollback_sha256", "rootfs_sha256",
        },
        "approved": {
            "approval_consumed", "candidate_attempted", "rollback_pre_authorized",
            "approval_token_sha256", "approval_binding_sha256", "orchestrator_sha256",
        },
        "protected-paths-pre-verified": {
            "candidate_attempted", "staging_attempt_count", "rootfs_copy_count",
            "cleanup_dispatch_count", "record",
        },
        "resident-promotion-guard-armed": {
            "candidate_attempted", "candidate_replay", "guard",
        },
        "candidate-transfer-started": {
            "candidate_attempted", "candidate_sha256", "candidate_transfer_count_max",
            "rollback_required", "candidate_replay",
        },
        "candidate-flashed": {
            "candidate_sha256", "candidate_transfer_count", "candidate_replay",
            "rollback_required", "record",
        },
        "candidate-boot-ready": {
            "candidate_version", "candidate_build", "selftest_fail_zero",
            "channel", "health",
        },
        "candidate-health-verified": {
            "candidate_health_check_count", "native_exact", "health",
        },
        "protected-paths-post-verified": {
            "handoff_eligible", "staging_attempt_count", "rootfs_copy_count",
            "cleanup_dispatch_count", "record",
        },
    }
    by_action = {str(record["action"]): record for record in records}
    for action, payload in payloads.items():
        _journal_keyset(by_action[action], payload, action)
    terminal_result = _result_from_terminal(spec, records[-1])

    preflight = by_action["preflight"]
    approved = by_action["approved"]
    protected_pre = by_action["protected-paths-pre-verified"]
    started = by_action["candidate-transfer-started"]
    flashed = by_action["candidate-flashed"]
    boot_ready = by_action["candidate-boot-ready"]
    health_verified = by_action["candidate-health-verified"]
    protected_post = by_action["protected-paths-post-verified"]
    if (
        preflight.get("device_write") is not False
        or preflight.get("candidate_attempted") is not False
        or preflight.get("candidate_sha256") != spec.candidate.sha256
        or preflight.get("rollback_sha256") != spec.rollback.sha256
        or approved.get("approval_consumed") is not True
        or approved.get("candidate_attempted") is not False
        or approved.get("rollback_pre_authorized") is not True
        or approved.get("orchestrator_sha256") != spec.orchestrator_sha256
        or protected_pre.get("candidate_attempted") is not False
        or started.get("candidate_attempted") is not True
        or started.get("candidate_sha256") != spec.candidate.sha256
        or started.get("candidate_transfer_count_max") != 1
        or started.get("rollback_required") is not True
        or started.get("candidate_replay") is not False
        or flashed.get("candidate_sha256") != spec.candidate.sha256
        or flashed.get("candidate_transfer_count") != 1
        or flashed.get("candidate_replay") is not False
        or flashed.get("rollback_required") is not True
        or boot_ready.get("candidate_version") != spec.candidate_version
        or boot_ready.get("candidate_build") != spec.candidate_build
        or boot_ready.get("selftest_fail_zero") is not True
        or health_verified.get("candidate_health_check_count") != 1
        or protected_post.get("handoff_eligible") is not False
        or any(
            record.get(name) != 0
            for record in (protected_pre, protected_post)
            for name in (
                "staging_attempt_count", "rootfs_copy_count",
                "cleanup_dispatch_count",
            )
        )
    ):
        raise ContractError("preserved install journal candidate closure changed")
    pre_proof = _validate_protected_proof(
        spec, protected_pre.get("record"), phase="pre-candidate"
    )
    post_proof = _validate_protected_proof(
        spec, protected_post.get("record"), phase="post-candidate"
    )
    native_exact = resident._require_exact_native_health(  # noqa: SLF001
        spec,
        boot_ready.get("health"),
    )
    exact_health = _validate_candidate_health(spec, health_verified.get("health"))
    if (
        health_verified.get("native_exact") != native_exact
        or exact_health.get("native") != boot_ready.get("health")
        or terminal_result.get("health") != exact_health
        or terminal_result.get("protected_paths") != post_proof
        or pre_proof.get("source_identity") != post_proof.get("source_identity")
        or pre_proof.get("work_identity") != post_proof.get("work_identity")
    ):
        raise ContractError("preserved install terminal proof differs from journal")
    timeline = base.load_timeline(transaction_dir, allow_promotion=True)
    if tuple(event.get("name") for event in timeline) != INSTALL_EVENTS:
        raise ContractError("preserved install durable timeline is not exact")
    return terminal_result


def _validate_rollback_result(
    spec: base.F1Spec,
    transaction_dir: Path,
    actions: list[str],
    value: Any,
) -> dict[str, Any]:
    result = _dict(value, "preserved rollback result")
    result_keys = {
        "schema", "run_id", "status", "manifest_sha256",
        "candidate_transfer_count", "candidate_transfer_uncertain",
        "candidate_replay", "debian_pid1_proven", "display_acquisition_proven",
        "rollback_transfer_count", "final_health_restored", "timeline_events",
    }
    candidate_complete = (
        "candidate-flashed" in actions and "candidate-boot-ready" in actions
    )
    expected_status = (
        "NO_PROOF_A90_F1_RP_CANDIDATE_ROLLED_BACK"
        if candidate_complete
        else "ABORTED_F1_V2_CANDIDATE_UNCERTAIN_ROLLED_BACK"
    )
    timeline = base.load_timeline(transaction_dir, allow_promotion=True)
    timeline_names = [str(event.get("name")) for event in timeline]
    expected_timeline = ["live_session_start", "candidate_flash_start"]
    if "candidate-flashed" in actions:
        expected_timeline.append("candidate_flash_done")
    if "candidate-boot-ready" in actions:
        expected_timeline.append("candidate_boot_ready")
    if "rollback-transfer-started" in actions:
        expected_timeline.append("rollback_flash_start")
    if any(
        action in actions
        for action in ("rollback-flashed", "rollback-completion-recovered-by-health")
    ):
        expected_timeline.append("rollback_flash_done")
    if "rollback-boot-ready" in actions:
        expected_timeline.append("rollback_boot_ready")
    expected_timeline.append("live_session_end")
    if (
        set(result) != result_keys
        or result.get("schema") != base.ORCHESTRATOR_SCHEMA
        or result.get("run_id") != spec.stage.run_id
        or result.get("manifest_sha256") != spec.stage.manifest_sha256
        or result.get("status") != expected_status
        or result.get("candidate_transfer_count")
        != (1 if candidate_complete else None)
        or result.get("candidate_transfer_uncertain") is not (not candidate_complete)
        or result.get("candidate_replay") is not False
        or result.get("debian_pid1_proven") is not False
        or result.get("display_acquisition_proven") is not False
        or result.get("rollback_transfer_count") != 1
        or result.get("final_health_restored") is not True
        or result.get("timeline_events") != timeline_names
        or timeline_names != expected_timeline
    ):
        raise ContractError("preserved rollback result is not exact")
    return result


def _validate_recovery_journal(
    spec: base.F1Spec,
    transaction_dir: Path,
    records: list[dict[str, Any]],
    *,
    closed: bool,
) -> dict[str, Any] | None:
    actions = [str(record.get("action")) for record in records]
    prefix = list(INSTALL_SUCCESS_ACTIONS[:5])
    if actions[:5] != prefix or len(records) < 5:
        raise ContractError("preserved rollback recovery prefix is not exact")
    if actions.count("candidate-transfer-started") != 1:
        raise ContractError("preserved rollback recovery candidate intent count changed")
    for forbidden in ("staging-started", "rootfs-staged", "rootfs-candidate-preflight"):
        if forbidden in actions:
            raise ContractError("preserved rollback recovery contains staging")
    if any("handoff" in action or "cleanup" in action for action in actions):
        raise ContractError("preserved rollback recovery contains a forbidden action")

    candidate_order = [
        "candidate-flashed", "candidate-boot-ready", "candidate-health-verified",
        "protected-paths-post-verified",
    ]
    rollback_positions = [
        index for index, action in enumerate(actions)
        if action.startswith("rollback-") or action == "health-verified"
    ]
    split = rollback_positions[0] if rollback_positions else len(actions)
    candidate_suffix = actions[5:split]
    if candidate_suffix not in (
        [],
        ["candidate-invocation-failed"],
        *[candidate_order[:count] for count in range(1, len(candidate_order) + 1)],
    ):
        raise ContractError("preserved rollback recovery candidate prefix changed")
    if actions.count("candidate-flashed") > 1 or actions.count("candidate-boot-ready") > 1:
        raise ContractError("preserved rollback recovery contains candidate replay")
    if actions.count("candidate-health-verified") > 1:
        raise ContractError("preserved rollback recovery health count changed")

    rollback_end = len(actions)
    open_protected_suffix = False
    if closed:
        if len(actions) < 2 or actions[-2:] != [
            "protected-paths-post-rollback-verified", "closed"
        ]:
            raise ContractError("preserved rollback closure suffix is not exact")
        rollback_end -= 2
    elif "closed" in actions:
        raise ContractError("open preserved rollback journal contains closed")
    elif actions[-1:] == ["protected-paths-post-rollback-verified"]:
        open_protected_suffix = True
        rollback_end -= 1
    elif "protected-paths-post-rollback-verified" in actions:
        raise ContractError("open preserved rollback proof is not the exact suffix")
    rollback_suffix = actions[split:rollback_end]
    pair_count = 0
    while rollback_suffix[:2] == [
        "rollback-transfer-started", "rollback-process-not-started"
    ]:
        pair_start = split + pair_count * 2
        exact, _mode = base.rollback_pre_spawn_pair_is_exact(
            spec,
            transaction_dir,
            records[pair_start],
            records[pair_start + 1],
            prior_rejections=pair_count,
        )
        if not exact:
            raise ContractError("preserved rollback pre-spawn pair is not exact")
        pair_count += 1
        rollback_suffix = rollback_suffix[2:]
    allowed_rollback_tails = (
        [],
        ["rollback-transfer-started"],
        ["rollback-transfer-started", "rollback-invocation-failed"],
        ["rollback-transfer-started", "rollback-flashed"],
        ["rollback-transfer-started", "rollback-flashed", "rollback-boot-ready"],
        ["rollback-transfer-started", "rollback-flashed", "rollback-boot-ready", "health-verified"],
        ["rollback-transfer-started", "rollback-completion-recovered-by-health"],
        ["rollback-transfer-started", "rollback-completion-recovered-by-health", "rollback-boot-ready"],
        ["rollback-transfer-started", "rollback-completion-recovered-by-health", "rollback-boot-ready", "health-verified"],
    )
    if rollback_suffix not in allowed_rollback_tails:
        raise ContractError("preserved rollback journal tail is not allowlisted")
    if (closed or open_protected_suffix) and (
        not rollback_suffix or rollback_suffix[-1] != "health-verified"
    ):
        raise ContractError("preserved rollback closed without exact final health")

    # Critical record shapes and values are revalidated before any recovery effect.
    started = records[4]
    _journal_keyset(
        started,
        {"candidate_attempted", "candidate_sha256", "candidate_transfer_count_max",
         "rollback_required", "candidate_replay"},
        "candidate-transfer-started",
    )
    if (
        started.get("candidate_sha256") != spec.candidate.sha256
        or started.get("candidate_transfer_count_max") != 1
        or started.get("candidate_replay") is not False
        or started.get("rollback_required") is not True
    ):
        raise ContractError("preserved rollback candidate intent changed")
    protected_pre = records[2]
    _journal_keyset(
        protected_pre,
        {"candidate_attempted", "staging_attempt_count", "rootfs_copy_count",
         "cleanup_dispatch_count", "record"},
        "protected-paths-pre-verified",
    )
    _validate_protected_proof(
        spec, protected_pre.get("record"), phase="pre-candidate"
    )
    _journal_keyset(
        records[0],
        {"device_write", "candidate_attempted", "candidate_sha256",
         "rollback_sha256", "rootfs_sha256"},
        "preflight",
    )
    _journal_keyset(
        records[1],
        {"approval_consumed", "candidate_attempted", "rollback_pre_authorized",
         "approval_token_sha256", "approval_binding_sha256", "orchestrator_sha256"},
        "approved",
    )
    _journal_keyset(
        records[3],
        {"candidate_attempted", "candidate_replay", "guard"},
        "resident-promotion-guard-armed",
    )
    if (
        records[0].get("device_write") is not False
        or records[0].get("candidate_attempted") is not False
        or records[1].get("approval_consumed") is not True
        or records[1].get("rollback_pre_authorized") is not True
        or records[3].get("candidate_attempted") is not False
        or records[3].get("candidate_replay") is not False
    ):
        raise ContractError("preserved rollback pre-candidate closure changed")
    if "candidate-flashed" in actions:
        flashed = records[actions.index("candidate-flashed")]
        _journal_keyset(
            flashed,
            {"candidate_sha256", "candidate_transfer_count", "candidate_replay",
             "rollback_required", "record"},
            "candidate-flashed",
        )
        if (
            flashed.get("candidate_sha256") != spec.candidate.sha256
            or flashed.get("candidate_transfer_count") != 1
            or flashed.get("candidate_replay") is not False
        ):
            raise ContractError("preserved rollback candidate flash changed")
    if "candidate-invocation-failed" in actions:
        failed = records[actions.index("candidate-invocation-failed")]
        _journal_keyset(
            failed,
            {"candidate_attempted", "candidate_replay", "rollback_required", "record"},
            "candidate-invocation-failed",
        )
        if (
            failed.get("candidate_attempted") is not True
            or failed.get("candidate_replay") is not False
            or failed.get("rollback_required") is not True
        ):
            raise ContractError("preserved rollback candidate failure changed")
    if "candidate-boot-ready" in actions:
        boot = records[actions.index("candidate-boot-ready")]
        _journal_keyset(
            boot,
            {"candidate_version", "candidate_build", "selftest_fail_zero",
             "channel", "health"},
            "candidate-boot-ready",
        )
        resident._require_exact_native_health(spec, boot.get("health"))  # noqa: SLF001
        if (
            boot.get("candidate_version") != spec.candidate_version
            or boot.get("candidate_build") != spec.candidate_build
            or boot.get("selftest_fail_zero") is not True
        ):
            raise ContractError("preserved rollback candidate boot health changed")
    if "candidate-health-verified" in actions:
        candidate_health = records[actions.index("candidate-health-verified")]
        _journal_keyset(
            candidate_health,
            {"candidate_health_check_count", "native_exact", "health"},
            "candidate-health-verified",
        )
        if candidate_health.get("candidate_health_check_count") != 1:
            raise ContractError("preserved rollback candidate health count changed")
        exact_candidate_health = _validate_candidate_health(
            spec, candidate_health.get("health")
        )
        native_exact = resident._require_exact_native_health(  # noqa: SLF001
            spec, exact_candidate_health.get("native")
        )
        if (
            candidate_health.get("native_exact") != native_exact
            or exact_candidate_health.get("native")
            != records[actions.index("candidate-boot-ready")].get("health")
        ):
            raise ContractError("preserved rollback candidate health proof changed")
    if "protected-paths-post-verified" in actions:
        protected_post = records[actions.index("protected-paths-post-verified")]
        _journal_keyset(
            protected_post,
            {"handoff_eligible", "staging_attempt_count", "rootfs_copy_count",
             "cleanup_dispatch_count", "record"},
            "protected-paths-post-verified",
        )
        if (
            protected_post.get("handoff_eligible") is not False
            or any(
                protected_post.get(name) != 0
                for name in (
                    "staging_attempt_count", "rootfs_copy_count",
                    "cleanup_dispatch_count",
                )
            )
        ):
            raise ContractError("preserved rollback protected post proof changed")
        _validate_protected_proof(
            spec, protected_post.get("record"), phase="post-candidate"
        )
    if "health-verified" in actions:
        final_record = records[actions.index("health-verified")]
        _validate_final_health(
            spec,
            {key: value for key, value in final_record.items() if key not in COMMON_JOURNAL_KEYS},
        )

    rollback_payloads = {
        "rollback-transfer-started": {
            "rollback_sha256", "rollback_attempt_limit", "rollback_process_started",
            "candidate_replay", "recovery_mode", "prior_pre_spawn_rejections",
        },
        "rollback-invocation-failed": {
            "candidate_replay", "rollback_retry_forbidden", "record",
        },
        "rollback-flashed": {
            "rollback_sha256", "rollback_transfer_count", "candidate_replay", "record",
        },
        "rollback-completion-recovered-by-health": {
            "rollback_reinvoked", "exact_v2321_health",
        },
    }
    expected_states = {
        "rollback-transfer-started": "RECOVERY_ROLLBACK",
        "rollback-invocation-failed": "RECOVERY_ROLLBACK",
        "rollback-flashed": "ROLLBACK_FLASHED",
        "rollback-completion-recovered-by-health": "ROLLBACK_FLASHED",
        "rollback-boot-ready": "ROLLBACK_FLASHED",
        "health-verified": "HEALTH_VERIFIED",
    }
    for action, expected_state in expected_states.items():
        for record in (item for item in records if item.get("action") == action):
            if record.get("state") != expected_state:
                raise ContractError(f"{action} rollback state changed")
            if action in rollback_payloads:
                _journal_keyset(record, rollback_payloads[action], action)
    if "rollback-invocation-failed" in actions:
        failed_rollback = records[actions.index("rollback-invocation-failed")]
        if (
            failed_rollback.get("candidate_replay") is not False
            or failed_rollback.get("rollback_retry_forbidden") is not True
        ):
            raise ContractError("preserved rollback invocation failure changed")
    for record in (item for item in records if item.get("action") == "rollback-transfer-started"):
        if (
            record.get("rollback_sha256") != spec.rollback.sha256
            or record.get("rollback_attempt_limit") != 1
            or record.get("rollback_process_started") is not None
            or record.get("candidate_replay") is not False
            or record.get("recovery_mode") not in {"from-native", "adb-recovery"}
        ):
            raise ContractError("preserved rollback intent changed")
    if "rollback-flashed" in actions:
        flashed_rollback = records[actions.index("rollback-flashed")]
        if (
            flashed_rollback.get("rollback_sha256") != spec.rollback.sha256
            or flashed_rollback.get("rollback_transfer_count") != 1
            or flashed_rollback.get("candidate_replay") is not False
        ):
            raise ContractError("preserved rollback completion changed")
    if "rollback-completion-recovered-by-health" in actions:
        recovered = records[actions.index("rollback-completion-recovered-by-health")]
        if (
            recovered.get("rollback_reinvoked") is not False
            or recovered.get("exact_v2321_health") is not True
        ):
            raise ContractError("preserved rollback health recovery changed")
    if "rollback-boot-ready" in actions:
        ready = records[actions.index("rollback-boot-ready")]
        payload = {"rollback_version", "rollback_build", "selftest_fail_zero"}
        if "recovered_from_health" in ready:
            payload.add("recovered_from_health")
        _journal_keyset(ready, payload, "rollback-boot-ready")
        if (
            ready.get("rollback_version") != spec.rollback_version
            or ready.get("rollback_build") != spec.rollback_build
            or ready.get("selftest_fail_zero") is not True
            or (
                "recovered_from_health" in ready
                and ready.get("recovered_from_health") is not True
            )
        ):
            raise ContractError("preserved rollback boot-ready changed")

    if not closed and not open_protected_suffix:
        return None
    protected_rollback = records[-2] if closed else records[-1]
    _journal_keyset(
        protected_rollback,
        {"staging_attempt_count", "rootfs_copy_count", "cleanup_dispatch_count", "record"},
        "protected-paths-post-rollback-verified",
    )
    _validate_protected_proof(
        spec, protected_rollback.get("record"), phase="post-rollback"
    )
    if any(
        protected_rollback.get(name) != 0
        for name in (
            "staging_attempt_count", "rootfs_copy_count", "cleanup_dispatch_count"
        )
    ):
        raise ContractError("preserved rollback protected counters changed")
    if not closed:
        return None
    terminal = records[-1]
    result_keys = {
        "schema", "run_id", "status", "manifest_sha256",
        "candidate_transfer_count", "candidate_transfer_uncertain",
        "candidate_replay", "debian_pid1_proven", "display_acquisition_proven",
        "rollback_transfer_count", "final_health_restored", "timeline_events",
    }
    _journal_keyset(
        terminal,
        result_keys - {"schema", "run_id", "manifest_sha256"},
        "rollback closed",
    )
    result = {key: terminal.get(key) for key in result_keys}
    result["schema"] = base.ORCHESTRATOR_SCHEMA
    result["run_id"] = spec.stage.run_id
    result["manifest_sha256"] = spec.stage.manifest_sha256
    if (
        terminal.get("state") != "CLOSED"
        or terminal.get("action") != "closed"
    ):
        raise ContractError("preserved rollback terminal result is not exact")
    return _validate_rollback_result(spec, transaction_dir, actions, result)


def promotion_tail(
    spec: base.F1Spec,
    args: argparse.Namespace,
    transaction_dir: Path,
    journal_dir: Path,
    events: list[dict[str, str]],
    candidate_health: dict[str, Any],
    guard: base.cdc_guard.ModemManagerGuard,
) -> dict[str, Any]:
    released = False
    try:
        native_exact = resident._require_exact_native_health(spec, candidate_health)  # noqa: SLF001
        pstore = base.require_clean_pstore_before_handoff(args)
        ncm = base.rebind_host_ncm_after_reenumeration(spec, args)
        health = {"native": candidate_health, "pstore": pstore, "ncm": ncm}
        base.append_record(
            journal_dir,
            "CANDIDATE_HEALTH_VERIFIED",
            "candidate-health-verified",
            {
                "candidate_health_check_count": 1,
                "native_exact": native_exact,
                "health": health,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        protected = protected_paths_preflight(
            spec,
            args,
            phase="post-candidate",
        )
        base.append_record(
            journal_dir,
            "PROTECTED_PATHS_VERIFIED",
            "protected-paths-post-verified",
            {
                "handoff_eligible": False,
                "staging_attempt_count": 0,
                "rootfs_copy_count": 0,
                "cleanup_dispatch_count": 0,
                "record": protected,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        if not guard.healthy(recheck=True):
            raise ContractError("preserved install ModemManager guard was lost")
        release = base.release_candidate_return_modemmanager_guard(
            guard,
            transaction_dir,
            corridor="resident-promotion",
        )
        released = True
        if release.get("released") is not True:
            raise ContractError("preserved install guard did not release")
        base.ensure_event(
            transaction_dir,
            events,
            "live_session_end",
            allow_promotion=True,
        )
        if tuple(event["name"] for event in events) != INSTALL_EVENTS:
            raise ContractError("preserved install timeline is not canonical")
        result = {
            "schema": RESULT_SCHEMA,
            "run_id": spec.stage.run_id,
            "status": SUCCESS_STATUS,
            "manifest_sha256": spec.stage.manifest_sha256,
            "candidate_sha256": CANDIDATE_SHA256,
            "candidate_transfer_count": 1,
            "candidate_replay": False,
            "rollback_transfer_count": 0,
            "rollback_required": False,
            "device_safety_state": "RESIDENT_HEALTHY",
            "handoff_eligible": False,
            "staging_attempt_count": 0,
            "rootfs_copy_count": 0,
            "cleanup_dispatch_count": 0,
            "candidate_health_check_count": 1,
            "health": health,
            "protected_paths": protected,
            "timeline_events": [event["name"] for event in events],
        }
        base.append_record(
            journal_dir,
            TERMINAL_STATE,
            "closed",
            result,
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        if _validate_success_journal(
            spec,
            transaction_dir,
            base.read_journal(spec, transaction_dir),
        ) != result:
            raise ContractError("preserved install live result differs from exact journal")
        _publish_result(spec, transaction_dir, result)
        return result
    finally:
        if not released:
            release = base.release_candidate_return_modemmanager_guard(
                guard,
                transaction_dir,
                corridor="resident-promotion",
            )
            if release.get("released") is not True:
                raise ContractError("preserved install guard did not release")


def recover_or_repair(spec: base.F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    transaction_dir = base.exact_transaction_dir(spec, args.transaction_dir)
    records = base.read_journal(spec, transaction_dir)
    if (
        records[-1].get("state") == TERMINAL_STATE
        and records[-1].get("action") == "closed"
    ):
        approval = base.approved_bindings(spec, args, recovery=True)
        base.verify_local_closure(spec)
        base.require_consumed_approval(records, approval)
        result = _validate_success_journal(spec, transaction_dir, records)
        _publish_result(spec, transaction_dir, result)
        return result
    if records[-1].get("state") == "CLOSED" and records[-1].get("action") == "closed":
        approval = base.approved_bindings(spec, args, recovery=True)
        base.verify_local_closure(spec)
        base.require_consumed_approval(records, approval)
        result = _validate_recovery_journal(
            spec,
            transaction_dir,
            records,
            closed=True,
        )
        assert result is not None
        result_path = transaction_dir / "result.json"
        base.require_private_regular(result_path)
        if json.loads(result_path.read_text(encoding="utf-8")) != result:
            raise ContractError("preserved rollback result differs from terminal journal")
        return result
    actions = [record.get("action") for record in records]
    if "candidate-transfer-started" not in actions or "closed" in actions:
        raise ContractError("preserved install recovery lacks open candidate intent")
    approval = base.approved_bindings(spec, args, recovery=True)
    base.verify_local_closure(spec)
    base.require_consumed_approval(records, approval)
    _validate_recovery_journal(
        spec,
        transaction_dir,
        records,
        closed=False,
    )
    protected_rollback_already_verified = (
        records[-1].get("action") == "protected-paths-post-rollback-verified"
    )
    result_path = transaction_dir / "result.json"
    if result_path.exists():
        if not protected_rollback_already_verified:
            raise ContractError("open preserved rollback result precedes protected closure")
        base.require_private_regular(result_path)
        try:
            existing_result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ContractError("open preserved rollback result is invalid") from exc
        exact_result = _validate_rollback_result(
            spec,
            transaction_dir,
            [str(record.get("action")) for record in records],
            existing_result,
        )
        base.append_record(
            transaction_dir / "journal",
            "CLOSED",
            "closed",
            exact_result,
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        repaired_records = base.read_journal(spec, transaction_dir)
        repaired = _validate_recovery_journal(
            spec,
            transaction_dir,
            repaired_records,
            closed=True,
        )
        if repaired != exact_result:
            raise ContractError("preserved rollback close-only repair changed result")
        return exact_result
    corridor = resident._next_rollback_guard_corridor(transaction_dir)  # noqa: SLF001
    prepared_inputs = base.resident_promotion_guard_inputs(transaction_dir, records)
    guard = base.arm_candidate_return_modemmanager_guard(
        spec,
        args,
        transaction_dir,
        corridor=corridor,
        prepared_inputs=prepared_inputs,
    )
    base.modemmanager_guard_arm_evidence(transaction_dir, corridor, guard)
    released = False

    def before_close() -> None:
        nonlocal released
        if not protected_rollback_already_verified:
            protected = protected_paths_preflight(spec, args, phase="post-rollback")
            base.append_record(
                transaction_dir / "journal",
                "HEALTH_VERIFIED",
                "protected-paths-post-rollback-verified",
                {
                    "staging_attempt_count": 0,
                    "rootfs_copy_count": 0,
                    "cleanup_dispatch_count": 0,
                    "record": protected,
                },
                manifest_sha256=spec.stage.manifest_sha256,
                run_id=spec.stage.run_id,
            )
        release = base.release_candidate_return_modemmanager_guard(
            guard,
            transaction_dir,
            corridor=corridor,
        )
        released = True
        if release.get("released") is not True:
            raise ContractError("rollback guard did not release")

    try:
        result = base.recover_approved_rollback(
            spec,
            args,
            return_guard=guard,
            before_close=before_close,
        )
        closed_records = base.read_journal(spec, transaction_dir)
        exact = _validate_recovery_journal(
            spec,
            transaction_dir,
            closed_records,
            closed=True,
        )
        if exact != result:
            raise ContractError("preserved rollback result differs from exact journal")
        return result
    finally:
        if not released:
            release = base.release_candidate_return_modemmanager_guard(
                guard,
                transaction_dir,
                corridor=corridor,
            )
            if release.get("released") is not True:
                raise ContractError("rollback guard did not release")


def _prior_inputs(
    manifest_path: Path,
    expected_sha256: str,
) -> tuple[Bound, dict[str, Any], str]:
    bound = _bound(manifest_path)
    if bound.sha256 != _sha(expected_sha256, "predecessor manifest sha256"):
        raise ContractError("predecessor manifest SHA256 mismatch")
    value = _read_json(bound, "predecessor manifest")
    run_id = _string(value.get("run_id"), "predecessor run_id")
    if (
        value.get("schema") != staging.PHASE2_DISPLAY_MANIFEST_SCHEMA
        or value.get("status") != staging.FINAL_MANIFEST_STATUS
        or RUN_RE.fullmatch(run_id) is None
        or bound.path.parent != (PRIVATE_RUN_BASE / run_id).resolve(strict=True)
    ):
        raise ContractError("predecessor manifest is not exact ordinary V3406 F1")
    return bound, value, run_id


def execute_connected_d0(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_RE.fullmatch(args.run_id or "") is None or SEQ_RE.fullmatch(
        args.evidence_sequence or ""
    ) is None:
        raise ContractError("connected D0 run/sequence is not exact")
    run_dir = (PRIVATE_RUN_BASE / args.run_id).resolve(strict=True)
    if not run_dir.is_dir() or run_dir.is_symlink():
        raise ContractError("connected D0 run directory is not exact")
    prior_bound, prior, predecessor_run_id = _prior_inputs(
        args.predecessor_manifest,
        args.expect_predecessor_manifest_sha256,
    )
    if predecessor_run_id == args.run_id:
        raise ContractError("connected D0 requires a distinct predecessor run")
    rootfs = _dict(prior.get("debian_rootfs"), "predecessor rootfs")
    keyed = _dict(rootfs.get("keyed_source"), "predecessor keyed source")
    source_host = _bound(Path(_string(keyed.get("local_path"), "source host path")), mode=0o600)
    source_sha = _sha(keyed.get("sha256"), "source sha256")
    if (
        source_host.size != IMAGE_SIZE
        or source_host.sha256 != source_sha
        or keyed.get("size") != IMAGE_SIZE
        or SOURCE_RE.fullmatch(_string(keyed.get("device_path"), "source device path"))
        is None
    ):
        raise ContractError("predecessor source identity changed")
    work_host = _bound(args.work_host_preservation, mode=0o600)
    work_sha = _sha(args.expect_work_sha256, "work SHA256")
    if work_host.size != IMAGE_SIZE or work_host.sha256 != work_sha or work_sha == source_sha:
        raise ContractError("host-preserved work identity changed")
    candidate_value = _dict(prior.get("candidate_boot"), "predecessor candidate")
    rollback_value = _dict(prior.get("rollback_boot"), "predecessor rollback")
    candidate = _bound(Path(_string(candidate_value.get("path"), "candidate path")))
    rollback = _bound(Path(_string(rollback_value.get("path"), "rollback path")))
    if (
        candidate.size != CANDIDATE_SIZE
        or candidate.sha256 != CANDIDATE_SHA256
        or rollback.size != ROLLBACK_SIZE
        or rollback.sha256 != ROLLBACK_SHA256
    ):
        raise ContractError("connected D0 boot artifacts changed")
    cleanup_result = _bound(args.cleanup_result)
    if cleanup_result.sha256 != _sha(
        args.expect_cleanup_result_sha256, "cleanup result SHA256"
    ):
        raise ContractError("cleanup result binding changed")
    cleanup_value = _read_json(cleanup_result, "cleanup result")
    if (
        cleanup_value.get("outcome") != EXPECTED_CLEANUP_OUTCOME
        or cleanup_value.get("effect_proven") is not False
        or cleanup_value.get("post_health_proven") is not True
    ):
        raise ContractError("cleanup result is not the exact no-effect terminal")

    connected.require_exact_bridge(args.bridge_device, args.expect_realpath, args)
    usb_identity = connected.exact_usb_identity(args.expect_realpath)
    host_ncm = staging.require_host_ncm_ready(args.device_ip, args.expect_realpath)
    baseline = staging.require_native_health(
        args,
        expected_version=ROLLBACK_VERSION,
        expected_build=ROLLBACK_BUILD,
        input_mode="slow",
        input_char_delay_sec=0.02,
    )
    health = connected.parse_health(
        baseline,
        expected_version=ROLLBACK_VERSION,
        expected_build=ROLLBACK_BUILD,
    )
    stage_path = str(staging.derive_stage_dir(args.run_id))
    protected_value = {
        "disposition": ROOTFS_DISPOSITION,
        "predecessor_run_id": predecessor_run_id,
        "source": {
            "device_path": keyed["device_path"],
            "size": IMAGE_SIZE,
            "mode": FILE_MODE,
            "nlink": FILE_NLINK,
            "sha256": source_sha,
            "host_preservation": _bound_dict(source_host),
        },
        "work": {
            "device_path": WORK_PATH,
            "size": IMAGE_SIZE,
            "mode": FILE_MODE,
            "nlink": FILE_NLINK,
            "sha256": work_sha,
            "host_preservation": _bound_dict(work_host),
        },
        "stage_path": stage_path,
        "handoff_eligible": False,
    }
    spec = SimpleNamespace(
        manifest={"protected_rootfs": protected_value},
        stage=SimpleNamespace(remote_stage_dir=stage_path),
    )
    proof = protected_paths_preflight(spec, args, phase="connected-d0")
    connected_value = {
        "schema": CONNECTED_D0_SCHEMA,
        "timestamp_utc": utc_now(),
        "run_id": args.run_id,
        "predecessor_run_id": predecessor_run_id,
        "device_ip": args.device_ip,
        "target": {
            "profile": staging.TARGET_PROFILE,
            "matching_a90_usb_devices": 1,
            "bridge_device": args.bridge_device,
            **usb_identity,
        },
        "host_ncm": host_ncm,
        "health": health,
        "artifacts": {
            "candidate_boot": _bound_dict(candidate),
            "rollback_boot": _bound_dict(rollback),
            "source_host": _bound_dict(source_host),
            "work_host": _bound_dict(work_host),
        },
        "predecessor_manifest": _bound_dict(prior_bound),
        "cleanup_result": _bound_dict(cleanup_result),
        "safety": {
            "device_write": False,
            "flash": False,
            "payload_sent": False,
            "reboot_requested": False,
            "rootfs_staged": False,
            "userdata_touched": False,
        },
    }
    connected_path = run_dir / f"preserved-connected-d0-{args.evidence_sequence}.json"
    _write_private(connected_path, connected_value)
    connected_bound = _bound(connected_path)
    paths_value = {
        "schema": PATH_PREFLIGHT_SCHEMA,
        "timestamp_utc": utc_now(),
        "run_id": args.run_id,
        "connected_d0_sha256": connected_bound.sha256,
        "cleanup_result_sha256": cleanup_result.sha256,
        "proof": proof,
        "safety": {
            "device_write": False,
            "flash": False,
            "payload_sent": False,
            "reboot_requested": False,
            "rootfs_staged": False,
            "rootfs_copied": False,
            "cleanup_dispatched": False,
            "handoff_dispatched": False,
        },
    }
    paths_path = run_dir / f"preserved-path-preflight-{args.evidence_sequence}.json"
    _write_private(paths_path, paths_value)
    return {
        "schema": CONNECTED_D0_SCHEMA,
        "status": "PASS_EXACT_A90_V2321_SOURCE_WORK_PRESERVED",
        "run_id": args.run_id,
        "connected_d0": _bound_dict(connected_bound),
        "connected_path_preflight": _bound_dict(_bound(paths_path)),
        "device_contact": True,
        "device_write": False,
        "flash": False,
        "payload_sent": False,
        "other_device_commands": 0,
    }


def _journal_bindings(run_id: str) -> list[dict[str, Any]]:
    root = PRIVATE_RUN_BASE / run_id / "f1-live" / "journal"
    paths = sorted(root.glob("*.json"))
    if not paths:
        raise ContractError("predecessor journal is absent")
    return [_bound_dict(_bound(path)) for path in paths]


def _cleanup_bindings(run_dir: Path) -> dict[str, dict[str, Any]]:
    paths = {
        "manifest": run_dir / "manifest.json",
        "intent": run_dir / "live" / "intent.json",
        "dispatch": run_dir / "live" / "dispatch.json",
        "dispatch_error": run_dir / "live" / "dispatch-error.json",
        "result": run_dir / "live" / "result.json",
    }
    return {label: _bound_dict(_bound(path)) for label, path in paths.items()}


def _current_execution_closure() -> dict[str, dict[str, Any]]:
    paths = {
        "runner": Path(__file__).resolve(),
        "orchestrator": Path(base.__file__).resolve(),
        "staging_adapter": Path(staging.__file__).resolve(),
        "resident_helpers": Path(resident.__file__).resolve(),
        "connected_helpers": Path(connected.__file__).resolve(),
        "cleanup_helpers": Path(cleanup.__file__).resolve(),
        "flash_runner": base.NATIVE_FLASH_PATH,
        "a90ctl": REVAL_DIR / "a90ctl.py",
        "serial_bridge": REVAL_DIR / "serial_tcp_bridge.py",
        "modemmanager_guard": REVAL_DIR / "device_action_cdc_acm_observer_v1.py",
        "tcpctl_host": REVAL_DIR / "tcpctl_host.py",
        **CANONICAL_SUPPORT_SOURCES,
    }
    return {label: _bound_dict(_bound(path, private=False)) for label, path in paths.items()}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_RE.fullmatch(args.run_id or "") is None:
        raise ContractError("manifest run_id is not exact")
    run_dir = (PRIVATE_RUN_BASE / args.run_id).resolve(strict=True)
    prior_bound, prior, predecessor_run_id = _prior_inputs(
        args.predecessor_manifest,
        args.expect_predecessor_manifest_sha256,
    )
    connected_bound = _bound(args.connected_d0)
    if connected_bound.sha256 != _sha(args.expect_connected_d0_sha256, "connected D0 SHA256"):
        raise ContractError("connected D0 SHA256 mismatch")
    paths_bound = _bound(args.connected_path_preflight)
    if paths_bound.sha256 != _sha(
        args.expect_connected_path_preflight_sha256, "path preflight SHA256"
    ):
        raise ContractError("path preflight SHA256 mismatch")
    connected_value = _read_json(connected_bound, "connected D0")
    if connected_value.get("run_id") != args.run_id:
        raise ContractError("connected D0 belongs to another run")
    cleanup_dir = args.cleanup_run_dir.resolve(strict=True)
    cleanup_bindings = _cleanup_bindings(cleanup_dir)
    cleanup_result = _load_bound(cleanup_bindings["result"], "cleanup result")
    if _dict(connected_value.get("cleanup_result"), "connected cleanup result").get(
        "sha256"
    ) != cleanup_result.sha256:
        raise ContractError("connected D0 cleanup result binding differs")
    prior_rootfs = _dict(prior.get("debian_rootfs"), "predecessor rootfs")
    keyed = _dict(prior_rootfs.get("keyed_source"), "predecessor keyed source")
    source_host = _bound(Path(_string(keyed.get("local_path"), "source local path")), mode=0o600)
    work_host = _bound(args.work_host_preservation, mode=0o600)
    work_sha = _sha(args.expect_work_sha256, "work SHA256")
    if source_host.sha256 != keyed.get("sha256") or work_host.sha256 != work_sha:
        raise ContractError("host source/work bytes changed before manifest build")
    candidate_value = _dict(prior.get("candidate_boot"), "predecessor candidate")
    rollback_value = _dict(prior.get("rollback_boot"), "predecessor rollback")
    candidate = _bound(Path(_string(candidate_value.get("path"), "candidate path")))
    rollback = _bound(Path(_string(rollback_value.get("path"), "rollback path")))
    if candidate.sha256 != CANDIDATE_SHA256 or rollback.sha256 != ROLLBACK_SHA256:
        raise ContractError("predecessor boot artifacts changed")
    review = _bound(args.review_report, private=False)
    if review.sha256 != _sha(args.expect_review_report_sha256, "review SHA256"):
        raise ContractError("review report SHA256 mismatch")
    observer_value = _dict(prior_rootfs.get("observer"), "predecessor observer")
    observer_key = _bound(Path(_string(observer_value.get("private_key_path"), "observer key")))
    observer_public = _bound(observer_key.path.with_suffix(observer_key.path.suffix + ".pub"))
    prior_target = _dict(prior.get("target"), "predecessor target")
    recovery_evidence = _dict(
        prior_target.get("recovery_adb_identity_evidence"), "predecessor recovery evidence"
    )
    recovery_records = [
        recovery_evidence.get("candidate_recovery_log"),
        recovery_evidence.get("rollback_recovery_log"),
    ]
    if not all(isinstance(item, dict) for item in recovery_records):
        raise ContractError("predecessor recovery evidence is incomplete")
    execution = _current_execution_closure()
    target_value = _dict(connected_value.get("target"), "connected target")
    stage_path = str(staging.derive_stage_dir(args.run_id))
    proof_protected = {
        "source": {
            "device_path": keyed["device_path"],
            "size": IMAGE_SIZE,
            "mode": FILE_MODE,
            "nlink": FILE_NLINK,
            "sha256": keyed["sha256"],
        },
        "work": {
            "device_path": WORK_PATH,
            "size": IMAGE_SIZE,
            "mode": FILE_MODE,
            "nlink": FILE_NLINK,
            "sha256": work_sha,
        },
        "stage_path": stage_path,
    }
    connected_paths_value = _read_json(paths_bound, "protected path D0")
    connected_proof = _validate_protected_proof(
        SimpleNamespace(
            manifest={"protected_rootfs": proof_protected},
            stage=SimpleNamespace(remote_stage_dir=stage_path),
        ),
        connected_paths_value.get("proof"),
        phase="connected-d0",
        allow_unbound_identity=True,
    )
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": staging.FINAL_MANIFEST_STATUS,
        "run_id": args.run_id,
        "capability": CAPABILITY,
        "target": {
            "profile": staging.TARGET_PROFILE,
            "current_version": ROLLBACK_VERSION,
            "current_build": ROLLBACK_BUILD,
            "bridge_device": target_value["bridge_device"],
            "bridge_selected_realpath": target_value["bridge_selected_realpath"],
            "bridge_selected_exact": True,
            "usb_serial_sha256": target_value["usb_serial_sha256"],
            "connected_d0_result": _bound_dict(connected_bound),
            "connected_path_preflight": _bound_dict(paths_bound),
        },
        "candidate_boot": {
            **_bound_dict(candidate),
            "partition": "boot",
            "expected_version": CANDIDATE_VERSION,
            "expected_build": CANDIDATE_BUILD,
        },
        "rollback_boot": {
            **_bound_dict(rollback),
            "partition": "boot",
            "expected_version": ROLLBACK_VERSION,
            "expected_build": ROLLBACK_BUILD,
        },
        "transport": {
            "candidate_and_rollback_runner": execution["flash_runner"]["path"],
            "runner_size": execution["flash_runner"]["size"],
            "runner_sha256": execution["flash_runner"]["sha256"],
            "only_partition_payload": "boot",
            "forbidden_partition_writes": True,
        },
        "protected_rootfs": {
            "disposition": ROOTFS_DISPOSITION,
            "predecessor_run_id": predecessor_run_id,
            "source": {
                "device_path": keyed["device_path"],
                "size": IMAGE_SIZE,
                "mode": FILE_MODE,
                "nlink": FILE_NLINK,
                "sha256": keyed["sha256"],
                "device_identity": connected_proof["source_identity"],
                "host_preservation": _bound_dict(source_host),
            },
            "work": {
                "device_path": WORK_PATH,
                "size": IMAGE_SIZE,
                "mode": FILE_MODE,
                "nlink": FILE_NLINK,
                "sha256": work_sha,
                "device_identity": connected_proof["work_identity"],
                "host_preservation": _bound_dict(work_host),
            },
            "stage_path": stage_path,
            "handoff_eligible": False,
        },
        "observer": {
            "private_key": _bound_dict(observer_key),
            "public_key": _bound_dict(observer_public),
            "device_ip": observer_value["device_ip"],
            "device_port": observer_value["device_port"],
            "host_ncm_profile": observer_value["host_ncm_profile"],
            "transport_scope": base.OBSERVER_TRANSPORT_SCOPE,
            "wifi_or_external_network": False,
        },
        "observation": {
            "mode": base.UNATTENDED_OBSERVATION_MODE,
            "candidate_boot_timeout_sec": 180,
            "handoff_timeout_sec": 180,
            "ssh_marker_timeout_sec": 30,
            "candidate_return_timeout_sec": 180,
            "rollback_boot_timeout_sec": 180,
            "display_required": False,
            "handoff_attempt_limit": 0,
        },
        "recovery": {
            "adb_serial_sha256": prior_target["recovery_adb_serial_sha256"],
            "identity_evidence": recovery_records,
            "physical_path": "operator-attended Download or TWRP",
        },
        "prior_closed_f1": {
            "manifest": _bound_dict(prior_bound),
            "result": _bound_dict(_bound(PRIVATE_RUN_BASE / predecessor_run_id / "f1-live" / "result.json")),
            "journal": _journal_bindings(predecessor_run_id),
        },
        "cleanup_incident": cleanup_bindings,
        "execution_closure": execution,
        "resident_promotion": {
            "mode": MODE,
            "runner": execution["runner"],
            "rootfs_preflight_disposition": ROOTFS_DISPOSITION,
            "success_terminal": SUCCESS_STATUS,
            "terminal_state": TERMINAL_STATE,
            "candidate_health_checks": 1,
            "rollback_on_post_attempt_failure": True,
            "handoff_eligible": False,
            "staging_attempt_count": 0,
            "rootfs_copy_count": 0,
            "cleanup_dispatch_count": 0,
        },
        "independent_review": _bound_dict(review),
        "authority": {
            "candidate_transfer_authorized": False,
            "live_authority": False,
            "manifest_grants_live_authority": False,
            "fresh_operator_approval_required": True,
            "rollback_authority_activates_after_candidate_start": True,
            "operator_attendance_required": True,
        },
    }
    output = run_dir / "resident-existing-rootfs-preserved-manifest.json"
    if output.exists():
        raise ContractError("preserved-rootfs manifest output already exists")
    _write_private(output, manifest)
    output_bound = _bound(output)
    load_spec(output, output_bound.sha256)
    return {
        "schema": MANIFEST_SCHEMA,
        "status": "READY_FOR_FRESH_EXACT_APPROVAL",
        "run_id": args.run_id,
        "manifest": _bound_dict(output_bound),
        "candidate_sha256": candidate.sha256,
        "rollback_sha256": rollback.sha256,
        "source_sha256": source_host.sha256,
        "work_sha256": work_host.sha256,
        "handoff_eligible": False,
        "device_contact": False,
        "device_write": False,
        "live_authority": False,
    }


def audit() -> dict[str, Any]:
    audit_run_id = "a90-v3406-debian-display-f1-20991231-99"
    audit_stage = str(staging.derive_stage_dir(audit_run_id))
    audit_spec = SimpleNamespace(
        manifest={
            "protected_rootfs": {
                "source": {
                    "device_path": (
                        "/mnt/sdext/a90/runtime/"
                        "debian-bookworm-arm64-phase2-display-v3406-keyed-"
                        "20991231-98.img"
                    ),
                    "size": IMAGE_SIZE,
                    "mode": FILE_MODE,
                    "nlink": FILE_NLINK,
                    "sha256": "1" * 64,
                },
                "work": {
                    "device_path": WORK_PATH,
                    "size": IMAGE_SIZE,
                    "mode": FILE_MODE,
                    "nlink": FILE_NLINK,
                    "sha256": "2" * 64,
                },
                "stage_path": audit_stage,
            }
        },
        stage=SimpleNamespace(remote_stage_dir=audit_stage),
    )
    commands = list(
        _protected_commands(audit_spec, phase="connected-d0").values()
    )
    issues: list[str] = []
    if any(_wire_bytes(command) > MAX_CMDV1X_WIRE_BYTES for command in commands):
        issues.append("static protected command exceeds wire bound")
    source = Path(__file__).read_text(encoding="utf-8")
    subject = source[: source.index("\ndef audit(")]
    for token in (
        "staging_attempt_count\": 0",
        "rootfs_copy_count\": 0",
        "cleanup_dispatch_count\": 0",
        "handoff_eligible\": False",
        "candidate_transfer_count_max\": 1",
        "base.recover_approved_rollback(",
        "protected-paths-pre-verified",
        "protected-paths-post-verified",
    ):
        if token not in source and token not in Path(base.__file__).read_text(encoding="utf-8"):
            issues.append(f"source contract missing {token!r}")
    for forbidden in (
        "--execute-approved-stage",
        "stage_command(spec",
        "cleanup.execute_cleanup(",
        "switch-root-to-distro\",",
    ):
        if forbidden in subject:
            issues.append(f"preserved runner contains forbidden route {forbidden!r}")
    return {
        "schema": MANIFEST_SCHEMA,
        "mode": "host-only-audit",
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "orchestrator_sha256": sha256_file(Path(base.__file__).resolve()),
        "review_closure": review_source_records(),
        "protected_read_frame_count": len(commands),
        "max_protected_wire_bytes": max(_wire_bytes(command) for command in commands),
        "contract_issues": issues,
        "ready_for_review": not issues,
        "device_contact": False,
        "device_write": False,
        "flash": False,
        "payload_sent": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit-only", action="store_true")
    mode.add_argument("--execute-connected-d0", action="store_true")
    mode.add_argument("--build-manifest", action="store_true")
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--execute-approved-preserved-install", action="store_true")
    mode.add_argument("--recover-approved-rollback", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-manifest-sha256")
    parser.add_argument("--run-id")
    parser.add_argument("--evidence-sequence", default="01")
    parser.add_argument("--predecessor-manifest", type=Path)
    parser.add_argument("--expect-predecessor-manifest-sha256")
    parser.add_argument("--cleanup-result", type=Path)
    parser.add_argument("--expect-cleanup-result-sha256")
    parser.add_argument("--cleanup-run-dir", type=Path)
    parser.add_argument("--work-host-preservation", type=Path)
    parser.add_argument("--expect-work-sha256")
    parser.add_argument("--connected-d0", type=Path)
    parser.add_argument("--expect-connected-d0-sha256")
    parser.add_argument("--connected-path-preflight", type=Path)
    parser.add_argument("--expect-connected-path-preflight-sha256")
    parser.add_argument("--review-report", type=Path)
    parser.add_argument("--expect-review-report-sha256")
    parser.add_argument("--approval")
    parser.add_argument("--transaction-dir", type=Path)
    parser.add_argument("--operator-attended", action="store_true")
    parser.add_argument("--recovery-path", choices=("from-native", "adb-recovery"))
    parser.add_argument("--bridge-device")
    parser.add_argument("--expect-realpath")
    parser.add_argument("--device-ip")
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


def _require_args(args: argparse.Namespace, names: tuple[str, ...], label: str) -> None:
    missing = [name for name in names if getattr(args, name) is None]
    if missing:
        rendered = ", ".join("--" + name.replace("_", "-") for name in missing)
        raise ContractError(f"{label} requires {rendered}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.audit_only:
        result = audit()
    elif args.execute_connected_d0:
        _require_args(
            args,
            (
                "run_id",
                "predecessor_manifest",
                "expect_predecessor_manifest_sha256",
                "cleanup_result",
                "expect_cleanup_result_sha256",
                "work_host_preservation",
                "expect_work_sha256",
                "bridge_device",
                "expect_realpath",
                "device_ip",
            ),
            "connected D0",
        )
        result = execute_connected_d0(args)
    elif args.build_manifest:
        _require_args(
            args,
            (
                "run_id",
                "predecessor_manifest",
                "expect_predecessor_manifest_sha256",
                "cleanup_run_dir",
                "work_host_preservation",
                "expect_work_sha256",
                "connected_d0",
                "expect_connected_d0_sha256",
                "connected_path_preflight",
                "expect_connected_path_preflight_sha256",
                "review_report",
                "expect_review_report_sha256",
            ),
            "manifest build",
        )
        result = build_manifest(args)
    else:
        _require_args(args, ("manifest", "expect_manifest_sha256"), "manifest mode")
        spec = load_spec(
            args.manifest,
            args.expect_manifest_sha256,
            recovery=args.recover_approved_rollback,
        )
        if args.prepare_approval:
            if args.approval is not None or args.transaction_dir is not None:
                raise ContractError("approval preparation accepts no live inputs")
            result = base.prepare_approval(spec)
        elif args.execute_approved_preserved_install:
            if not args.operator_attended:
                raise ContractError("live preserved install requires awake operator attendance")
            _require_args(args, ("approval", "transaction_dir"), "live install")
            if args.recovery_path is not None:
                raise ContractError("fresh install accepts no recovery path")
            result = base.execute_approved_f1(
                spec,
                args,
                promotion_tail=promotion_tail,
            )
        else:
            if not args.operator_attended:
                raise ContractError("rollback recovery requires awake operator attendance")
            _require_args(args, ("transaction_dir",), "rollback recovery")
            if args.approval is not None:
                raise ContractError("rollback recovery accepts no new approval")
            result = recover_or_repair(spec, args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(
            f"a90-resident-existing-rootfs-install-v1: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
