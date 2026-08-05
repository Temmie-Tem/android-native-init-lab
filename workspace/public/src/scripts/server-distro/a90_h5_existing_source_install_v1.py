#!/usr/bin/env python3
"""Install H5 once from the exact run-12 source without staging it again.

This A90-only lane consumes the terminal zero-candidate run-12 journal as
predecessor evidence.  A fresh campaign reopens the already published source
read-only, proves work/stage/H5 state paths absent, and permits one boot-only
candidate.  It never resumes run-12 and never stages, copies, unlinks, mounts,
or hands off the rootfs.
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
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_phase2d_connected_preflight as connected  # noqa: E402
import a90_resident_existing_rootfs_install_v1 as legacy  # noqa: E402
import a90_resident_promotion_v1 as resident  # noqa: E402
import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


CAPABILITY = "A90_ATTENDED_H5_EXISTING_PUBLISHED_SOURCE_INSTALL_V1"
MODE = staging.PRESERVED_ROOTFS_INSTALL_MODE
MANIFEST_SCHEMA = staging.PRESERVED_ROOTFS_INSTALL_MANIFEST_SCHEMA
REVIEW_SCHEMA = "a90-h5-existing-published-source-install-independent-review-v1"
D0_SCHEMA = "a90-h5-existing-published-source-connected-d0-v1"
PROOF_SCHEMA = "a90-h5-existing-published-source-proof-v1"
DISPOSITION = "exact-existing-source-work-stage-markers-absent-no-stage"
RUN_RE = re.compile(r"^a90-v3406-debian-display-f1-[0-9]{8}-[0-9]{2}$")
SEQ_RE = re.compile(r"^[0-9]{2}$")
IDENTITY_RE = re.compile(r"^[0-9]+:[0-9]+$")
IMAGE_SIZE = 2147483648
FILE_MODE = "600"
FILE_NLINK = 1
MAX_WIRE_BYTES = 3800
D0_MAX_AGE_SEC = 900
MAX_CLOCK_SKEW_SEC = 5
WORK_PATH = str(staging.REMOTE_WORK)
H5_SOURCE_PATH = (
    "/mnt/sdext/a90/runtime/"
    "debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-12.img"
)
H5_SOURCE_SHA256 = (
    "874291801573d96bf7731b2cdc27deca066221450534365eddfa2acf41ab681e"
)
H5_CANDIDATE_SIZE = 58372096
H5_CANDIDATE_SHA256 = (
    "8ceda5ac0924c0fc1f8526bbd3632fd5e6f1a8cdd59b03c978efb09bbb1acd9b"
)
H5_VERSION = "0.11.173"
H5_BUILD = "phase3-minimal-h5-fresh-campaign-auto-benchmark"
H5_ENABLE = "/cache/a90-auto-handoff-phase3-minimal-h5.enable"
H5_LATCH = "/cache/a90-auto-handoff-phase3-minimal-h5.done"
H5_BINDING_SHA256 = (
    "243c65b770393e31c34048a4ec5ffea3032022b4de1d437e4e3ef1e7637d14f0"
)
ROLLBACK_SIZE = 60882944
ROLLBACK_SHA256 = (
    "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
)
ROLLBACK_VERSION = "0.9.285"
ROLLBACK_BUILD = "v2321-usb-clean-identity-rodata"
PREDECESSOR_STATUS = "ABORTED_F1_V2_BEFORE_CANDIDATE"
PREDECESSOR_ACTIONS = (
    "preflight",
    "approved",
    "staging-started",
    "rootfs-staged",
    "rootfs-candidate-preflight",
    "aborted-before-candidate",
)
SUCCESS_ACTIONS = (
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
SUCCESS_STATES = (
    "PREFLIGHT",
    "APPROVED",
    "APPROVED",
    "APPROVED",
    "APPROVED",
    "CANDIDATE_FLASHED",
    "CANDIDATE_FLASHED",
    "CANDIDATE_HEALTH_VERIFIED",
    "PROTECTED_PATHS_VERIFIED",
    resident.INSTALL_TERMINAL_STATE,
)
COMMON_JOURNAL_KEYS = {
    "schema", "sequence", "timestamp_utc", "run_id", "manifest_sha256",
    "state", "action",
}

ContractError = legacy.ContractError
Bound = legacy.Bound


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _dict(value: Any, label: str) -> dict[str, Any]:
    return legacy._dict(value, label)  # noqa: SLF001


def _string(value: Any, label: str) -> str:
    return legacy._string(value, label)  # noqa: SLF001


def _sha(value: Any, label: str) -> str:
    return legacy._sha(value, label)  # noqa: SLF001


def _bound(path: Path, *, private: bool = True, mode: int | None = None) -> Bound:
    return legacy._bound(path, private=private, mode=mode)  # noqa: SLF001


def _bound_dict(value: Bound) -> dict[str, Any]:
    return legacy._bound_dict(value)  # noqa: SLF001


def _load_bound(value: Any, label: str, *, private: bool = True) -> Bound:
    return legacy._load_bound(value, label, private=private)  # noqa: SLF001


def _load_embedded_bound(
    value: dict[str, Any],
    label: str,
    *,
    path_key: str = "path",
) -> Bound:
    return _load_bound(
        {
            "path": value.get(path_key),
            "size": value.get("size"),
            "sha256": value.get("sha256"),
        },
        label,
    )


def _read_json(bound: Bound, label: str) -> dict[str, Any]:
    return legacy._read_json(bound, label)  # noqa: SLF001


def _journal_keyset(
    record: dict[str, Any],
    payload: set[str],
    label: str,
) -> None:
    if set(record) != COMMON_JOURNAL_KEYS | payload:
        raise ContractError(f"{label} journal keyset changed")


def _wire_bytes(command: list[str]) -> int:
    return len(base.a90ctl.encode_cmdv1_line(command).encode("utf-8")) + 1


def _remote(
    args: argparse.Namespace,
    command: list[str],
    label: str,
) -> dict[str, Any]:
    wire = _wire_bytes(command)
    if wire > MAX_WIRE_BYTES:
        raise ContractError(f"{label} exceeds bounded cmdv1x frame")
    receipt = base.run_f1_cmd(args, command)
    receipt["wire_bytes"] = wire
    return receipt


def review_source_paths() -> dict[str, Path]:
    return {
        "runner": Path(__file__).resolve(),
        "orchestrator": Path(base.__file__).resolve(),
        "resident_promotion": Path(resident.__file__).resolve(),
        "preserved_recovery_helpers": Path(legacy.__file__).resolve(),
        "staging_contract": Path(staging.__file__).resolve(),
        "connected_preflight": Path(connected.__file__).resolve(),
        "flash_runner": base.NATIVE_FLASH_PATH.resolve(),
        "a90ctl": (REVAL_DIR / "a90ctl.py").resolve(),
        "serial_bridge": (REVAL_DIR / "serial_tcp_bridge.py").resolve(),
        "modemmanager_guard": (
            REVAL_DIR / "device_action_cdc_acm_observer_v1.py"
        ).resolve(),
        "tcpctl_host": (REVAL_DIR / "tcpctl_host.py").resolve(),
        "h5_flat_manifest": (
            REVAL_DIR
            / "a90_flat_builder/versions/phase3-minimal-h5/manifest.toml"
        ).resolve(),
    }


def review_source_records() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for label, path in review_source_paths().items():
        bound = _bound(path, private=False)
        result[label] = _bound_dict(bound)
    return result


def _execution_bounds(value: Any) -> dict[str, Bound]:
    closure = _dict(value, "execution_closure")
    expected = review_source_paths()
    if set(closure) != set(expected):
        raise ContractError("execution closure labels changed")
    result: dict[str, Bound] = {}
    for label, path in expected.items():
        bound = _load_bound(closure.get(label), f"execution {label}", private=False)
        if bound.path != path:
            raise ContractError(f"execution path changed: {label}")
        result[label] = bound
    return result


def _validate_review(value: Any) -> Bound:
    bound = _load_bound(value, "independent_review", private=False)
    if stat.S_IMODE(bound.path.stat().st_mode) != 0o644:
        raise ContractError("independent review mode is not 0644")
    report = _read_json(bound, "independent review")
    if (
        report.get("schema") != REVIEW_SCHEMA
        or report.get("status") != "PASS_GO"
        or report.get("named_execution_critical_closure")
        != review_source_records()
        or report.get("unresolved_findings") != []
        or report.get("permanent_boundaries_unchanged") is not True
        or report.get("device_authority_granted") is not False
    ):
        raise ContractError("independent review is not exact PASS_GO")
    return bound


def _predecessor_bindings(manifest_path: Path) -> dict[str, Bound]:
    run_dir = manifest_path.parent
    journal_dir = run_dir / "f1-live/journal"
    paths = tuple(sorted(journal_dir.glob("*.json")))
    if len(paths) != len(PREDECESSOR_ACTIONS):
        raise ContractError("predecessor journal record count changed")
    result = {
        "manifest": _bound(manifest_path),
        "approval": _bound(run_dir / "approval-prepared.json"),
        "result": _bound(run_dir / "f1-live/result.json"),
        "timeline": _bound(run_dir / "f1-live/timeline.json"),
        "staging_result": _bound(run_dir / "staging-live/result.json"),
        "keyed_summary": _bound(run_dir / "keyed-rootfs-summary.json"),
    }
    for index, path in enumerate(paths):
        result[f"journal_{index:02d}"] = _bound(path)
    return result


def _validate_predecessor(
    manifest_path: Path,
    expected_sha256: str,
) -> tuple[dict[str, Any], dict[str, Bound]]:
    manifest_bound = _bound(manifest_path)
    if manifest_bound.sha256 != _sha(expected_sha256, "predecessor SHA256"):
        raise ContractError("predecessor manifest SHA256 changed")
    manifest = _read_json(manifest_bound, "predecessor manifest")
    run_id = _string(manifest.get("run_id"), "predecessor run_id")
    if (
        manifest.get("schema") != staging.RESIDENT_INSTALL_MANIFEST_SCHEMA
        or manifest.get("status") != staging.FINAL_MANIFEST_STATUS
        or RUN_RE.fullmatch(run_id) is None
        or run_id != "a90-v3406-debian-display-f1-20260805-12"
    ):
        raise ContractError("predecessor manifest identity changed")
    bounds = _predecessor_bindings(manifest_bound.path)
    result = _read_json(bounds["result"], "predecessor result")
    staging_result = _read_json(bounds["staging_result"], "predecessor staging")
    records = [
        _read_json(bounds[f"journal_{index:02d}"], f"predecessor journal {index}")
        for index in range(len(PREDECESSOR_ACTIONS))
    ]
    actions = tuple(record.get("action") for record in records)
    if actions != PREDECESSOR_ACTIONS:
        raise ContractError("predecessor journal action sequence changed")
    for index, record in enumerate(records):
        if (
            record.get("sequence") != index
            or record.get("run_id") != run_id
            or record.get("manifest_sha256") != manifest_bound.sha256
        ):
            raise ContractError("predecessor journal binding changed")
    candidate = _dict(manifest.get("candidate_boot"), "predecessor candidate")
    rollback = _dict(manifest.get("rollback_boot"), "predecessor rollback")
    rootfs = _dict(manifest.get("debian_rootfs"), "predecessor Debian rootfs")
    keyed = _dict(rootfs.get("keyed_source"), "predecessor keyed source")
    first_boot = _dict(candidate.get("first_boot_contract"), "predecessor first boot")
    preflight = records[4]
    source_record = _dict(preflight.get("record"), "predecessor source preflight")
    marker_proof = _dict(
        preflight.get("candidate_first_boot_preflight"),
        "predecessor marker preflight",
    )
    if (
        candidate.get("size") != H5_CANDIDATE_SIZE
        or candidate.get("sha256") != H5_CANDIDATE_SHA256
        or candidate.get("expected_version") != H5_VERSION
        or candidate.get("expected_build") != H5_BUILD
        or candidate.get("partition") != "boot"
        or rollback.get("size") != ROLLBACK_SIZE
        or rollback.get("sha256") != ROLLBACK_SHA256
        or rollback.get("expected_version") != ROLLBACK_VERSION
        or rollback.get("expected_build") != ROLLBACK_BUILD
        or rollback.get("partition") != "boot"
        or keyed.get("device_path") != H5_SOURCE_PATH
        or keyed.get("size") != IMAGE_SIZE
        or keyed.get("sha256") != H5_SOURCE_SHA256
        or first_boot.get("enable_path") != H5_ENABLE
        or first_boot.get("latch_path") != H5_LATCH
        or _dict(first_boot.get("compiled_binding"), "compiled binding").get(
            "binding_sha256"
        )
        != H5_BINDING_SHA256
        or result.get("status") != PREDECESSOR_STATUS
        or result.get("candidate_transfer_count") != 0
        or result.get("candidate_replay") is not False
        or result.get("rollback_transfer_count") != 0
        or records[-1].get("status") != PREDECESSOR_STATUS
        or records[-1].get("candidate_transfer_count") != 0
        or records[-1].get("candidate_replay") is not False
        or staging_result.get("status") != "PASS_ABSENT_ONLY_ROOTFS_STAGED"
        or records[3].get("rootfs_sha256") != H5_SOURCE_SHA256
        or preflight.get("rootfs_sha256") != H5_SOURCE_SHA256
        or preflight.get("rootfs_size") != IMAGE_SIZE
        or preflight.get("work_absent") is not True
        or source_record.get("rc") != 0
        or str(source_record.get("text") or "").count(
            "A90F1_SOURCE_PRECHECK exact=1 work_absent=1"
        )
        != 1
        or marker_proof.get("proof") is not True
        or marker_proof.get("enable_path") != H5_ENABLE
        or marker_proof.get("latch_path") != H5_LATCH
    ):
        raise ContractError("predecessor zero-candidate source closure changed")
    candidate_bound = _bound(Path(_string(candidate.get("path"), "candidate path")))
    rollback_bound = _bound(Path(_string(rollback.get("path"), "rollback path")))
    source_bound = _bound(Path(_string(keyed.get("local_path"), "source local path")))
    if (
        candidate_bound.size != H5_CANDIDATE_SIZE
        or candidate_bound.sha256 != H5_CANDIDATE_SHA256
        or rollback_bound.size != ROLLBACK_SIZE
        or rollback_bound.sha256 != ROLLBACK_SHA256
        or source_bound.size != IMAGE_SIZE
        or source_bound.sha256 != H5_SOURCE_SHA256
    ):
        raise ContractError("predecessor private artifacts changed")
    bounds.update(
        candidate=candidate_bound,
        rollback=rollback_bound,
        source=source_bound,
        observer_key=_bound(Path(_string(
            _dict(rootfs.get("observer"), "predecessor observer").get(
                "private_key_path"
            ),
            "observer key",
        ))),
    )
    return manifest, bounds


def _source_binding(spec: base.F1Spec) -> tuple[dict[str, Any], str, str]:
    protected = _dict(spec.manifest.get("protected_rootfs"), "protected_rootfs")
    source = _dict(protected.get("source"), "protected source")
    stage_path = _string(protected.get("stage_path"), "protected stage")
    if (
        protected.get("disposition") != DISPOSITION
        or source.get("device_path") != H5_SOURCE_PATH
        or source.get("size") != IMAGE_SIZE
        or source.get("sha256") != H5_SOURCE_SHA256
        or source.get("mode") != FILE_MODE
        or source.get("nlink") != FILE_NLINK
        or protected.get("work_path") != WORK_PATH
        or protected.get("enable_path") != H5_ENABLE
        or protected.get("latch_path") != H5_LATCH
        or stage_path != spec.stage.remote_stage_dir
    ):
        raise ContractError("protected H5 source binding changed")
    return source, H5_SOURCE_PATH, stage_path


def _protected_commands(spec: base.F1Spec) -> dict[str, list[str]]:
    _source, source_path, stage_path = _source_binding(spec)
    stat_format = "%F|%s|%a|%h|%d:%i"
    absent_script = (
        'for p in "$1" "$2" "$3" "$4";do '
        '[ ! -e "$p" ]&&[ ! -L "$p" ]||exit 72;done;'
        'printf "work=absent stage=absent enable=absent latch=absent\\n"'
    )
    mount_script = (
        'for f in /proc/[0-9]*/mountinfo;do [ -r "$f" ]||continue;'
        '/bin/busybox grep -F "$1" "$f" >/dev/null 2>&1&&exit 74;done;'
        'printf "mount_namespace_use=none\\n"'
    )
    loop_script = (
        'for f in /sys/block/loop*/loop/backing_file;do [ -r "$f" ]||continue;'
        'v=$(/bin/busybox cat "$f")||exit 71;[ "$v" != "$1" ]||exit 72;done;'
        'printf "loop_use=none\\n"'
    )
    open_script = (
        'for f in /proc/[0-9]*/fd/* /proc/[0-9]*/root;do '
        '[ -e "$f" ]||continue;v=$(/bin/busybox readlink "$f")||continue;'
        'case "$v" in "$1"|"$1 (deleted)")exit 73;;esac;done;'
        'printf "open_fd_use=none current_root_use=none\\n"'
    )
    return {
        "source_stat": [
            "run", "/bin/busybox", "stat", "-c", stat_format, source_path
        ],
        "source_hash": ["run", "/bin/busybox", "sha256sum", source_path],
        "absences": [
            "run", "/bin/busybox", "sh", "-c", absent_script, "sh",
            WORK_PATH, stage_path, H5_ENABLE, H5_LATCH,
        ],
        "mounts": [
            "run", "/bin/busybox", "sh", "-c", mount_script, "sh", source_path,
        ],
        "loops": [
            "run", "/bin/busybox", "sh", "-c", loop_script, "sh", source_path,
        ],
        "opens": [
            "run", "/bin/busybox", "sh", "-c", open_script, "sh", source_path,
        ],
    }


def _validate_receipt(
    value: Any,
    command: list[str],
    expected_line: str,
    label: str,
) -> dict[str, Any]:
    return legacy._validate_protected_receipt(  # noqa: SLF001
        value,
        command,
        expected_line,
        label,
    )


def _validate_proof(
    spec: base.F1Spec,
    value: Any,
    *,
    phase: str,
    allow_unbound_identity: bool = False,
) -> dict[str, Any]:
    proof = _dict(value, f"{phase} proof")
    source, source_path, _stage_path = _source_binding(spec)
    identity = _string(proof.get("source_identity"), "source identity")
    if IDENTITY_RE.fullmatch(identity) is None:
        raise ContractError("source identity is not exact")
    if not allow_unbound_identity and identity != source.get("device_identity"):
        raise ContractError("source identity changed from fresh D0")
    expected_keys = {
        "schema", "phase", "source_sha256", "source_identity",
        "work_absent", "stage_absent", "enable_absent", "latch_absent",
        "mount_namespace_use", "loop_use", "open_fd_use", "current_root_use",
        "staging_attempt_count", "rootfs_copy_count", "cleanup_dispatch_count",
        "handoff_attempt_count", "candidate_first_boot_preflight", "receipts",
    }
    if (
        set(proof) != expected_keys
        or proof.get("schema") != PROOF_SCHEMA
        or proof.get("phase") != phase
        or proof.get("source_sha256") != H5_SOURCE_SHA256
        or any(proof.get(name) is not True for name in (
            "work_absent", "stage_absent", "enable_absent", "latch_absent"
        ))
        or any(proof.get(name) is not False for name in (
            "mount_namespace_use", "loop_use", "open_fd_use", "current_root_use"
        ))
        or any(proof.get(name) != 0 for name in (
            "staging_attempt_count", "rootfs_copy_count", "cleanup_dispatch_count",
            "handoff_attempt_count",
        ))
    ):
        raise ContractError(f"{phase} H5 source proof changed")
    commands = _protected_commands(spec)
    receipts = _dict(proof.get("receipts"), "protected receipts")
    if set(receipts) != set(commands):
        raise ContractError("protected receipt labels changed")
    lines = {
        "source_stat": f"regular file|{IMAGE_SIZE}|{FILE_MODE}|{FILE_NLINK}|{identity}",
        "source_hash": f"{H5_SOURCE_SHA256}  {source_path}",
        "absences": "work=absent stage=absent enable=absent latch=absent",
        "mounts": "mount_namespace_use=none",
        "loops": "loop_use=none",
        "opens": "open_fd_use=none current_root_use=none",
    }
    for label, command in commands.items():
        _validate_receipt(receipts.get(label), command, lines[label], f"{phase} {label}")
    first_boot = _dict(
        proof.get("candidate_first_boot_preflight"),
        "candidate first-boot preflight",
    )
    first_boot_record = _dict(
        first_boot.get("record"),
        "candidate first-boot preflight record",
    )
    first_boot_script = base.candidate_first_boot_state_absence_script(
        spec.candidate_first_boot
    )
    base.require_exact_f1_command_receipt(
        first_boot_record,
        ["run", "/bin/busybox", "sh", "-c", first_boot_script],
        "candidate first-boot preflight record",
    )
    if (
        set(first_boot) != {"proof", "enable_path", "latch_path", "record"}
        or first_boot.get("proof") is not True
        or first_boot.get("enable_path") != H5_ENABLE
        or first_boot.get("latch_path") != H5_LATCH
        or str(first_boot_record.get("text") or "").count(
            "A90AUTO_F1_PRE enable_absent=1 latch_absent=1"
        )
        != 1
    ):
        raise ContractError("candidate first-boot preflight changed")
    return proof


def protected_paths_preflight(
    spec: base.F1Spec,
    args: argparse.Namespace,
    *,
    phase: str,
) -> dict[str, Any]:
    if phase not in {"connected-d0", "pre-candidate", "post-candidate", "post-rollback"}:
        raise ContractError("protected proof phase is unsupported")
    commands = _protected_commands(spec)
    receipts = {
        label: _remote(args, command, f"{phase} {label}")
        for label, command in commands.items()
    }
    stat_text = str(receipts["source_stat"].get("text") or "")
    matches = re.findall(
        rf"regular file\|{IMAGE_SIZE}\|{FILE_MODE}\|{FILE_NLINK}\|([0-9]+:[0-9]+)",
        stat_text,
    )
    if len(matches) != 1:
        raise ContractError("source stat identity is not unique")
    first_boot_script = base.candidate_first_boot_state_absence_script(
        spec.candidate_first_boot
    )
    first_boot_command = [
        "run", "/bin/busybox", "sh", "-c", first_boot_script,
    ]
    if _wire_bytes(first_boot_command) > MAX_WIRE_BYTES:
        raise ContractError("candidate first-boot read exceeds bounded cmdv1x frame")
    first_boot = base.require_candidate_first_boot_state_absent(spec, args)
    if first_boot is None:
        raise ContractError("H5 first-boot preflight is absent")
    proof = {
        "schema": PROOF_SCHEMA,
        "phase": phase,
        "source_sha256": H5_SOURCE_SHA256,
        "source_identity": matches[0],
        "work_absent": True,
        "stage_absent": True,
        "enable_absent": True,
        "latch_absent": True,
        "mount_namespace_use": False,
        "loop_use": False,
        "open_fd_use": False,
        "current_root_use": False,
        "staging_attempt_count": 0,
        "rootfs_copy_count": 0,
        "cleanup_dispatch_count": 0,
        "handoff_attempt_count": 0,
        "candidate_first_boot_preflight": first_boot,
        "receipts": receipts,
    }
    return _validate_proof(
        spec,
        proof,
        phase=phase,
        allow_unbound_identity=phase == "connected-d0",
    )


def _validate_d0(
    bound: Bound,
    *,
    run_id: str,
    source_identity: str | None = None,
    require_fresh: bool,
) -> dict[str, Any]:
    value = _read_json(bound, "connected D0")
    target = _dict(value.get("target"), "D0 target")
    health = _dict(value.get("health"), "D0 health")
    proof = _dict(value.get("protected_source"), "D0 protected source")
    timestamp = _string(value.get("timestamp_utc"), "D0 timestamp")
    if not base.is_canonical_utc_timestamp(timestamp):
        raise ContractError("D0 timestamp is not canonical")
    observed = dt.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.UTC
    )
    age = (dt.datetime.now(dt.UTC) - observed).total_seconds()
    if require_fresh and not (-MAX_CLOCK_SKEW_SEC <= age <= D0_MAX_AGE_SEC):
        raise ContractError("D0 evidence is stale")
    if (
        value.get("schema") != D0_SCHEMA
        or value.get("run_id") != run_id
        or target.get("profile") != staging.TARGET_PROFILE
        or target.get("bridge_selected_exact") is not True
        or target.get("matching_a90_usb_devices") != 1
        or health.get("version") != ROLLBACK_VERSION
        or health.get("version_build") != ROLLBACK_BUILD
        or health.get("pstore_entries") != 0
        or _dict(health.get("selftest"), "D0 selftest").get("fail") != 0
        or value.get("global_f1_guard_absent") is not True
        or any(value.get("safety", {}).get(name) is not False for name in (
            "device_write", "flash", "payload_sent", "reboot_requested"
        ))
    ):
        raise ContractError("connected D0 is not exact healthy A90 V2321")
    if source_identity is not None and proof.get("source_identity") != source_identity:
        raise ContractError("D0 source identity differs from manifest")
    return value


def validate_promotion_manifest(
    spec: base.F1Spec,
    *,
    recovery: bool = False,
) -> dict[str, Any]:
    value = _dict(spec.manifest.get("resident_promotion"), "resident_promotion")
    runner = _dict(value.get("runner"), "resident promotion runner")
    expected_runner = _bound(Path(__file__).resolve(), private=False)
    if (
        set(value)
        != {
            "mode", "runner", "rootfs_preflight_disposition",
            "success_terminal", "candidate_health_checks",
            "rollback_on_post_attempt_failure", "handoff_eligible",
            "staging_attempt_count", "rootfs_copy_count", "cleanup_dispatch_count",
        }
        or value.get("mode") != MODE
        or runner != _bound_dict(expected_runner)
        or value.get("rootfs_preflight_disposition") != DISPOSITION
        or value.get("success_terminal") != resident.INSTALL_STATUS
        or value.get("candidate_health_checks") != 1
        or value.get("rollback_on_post_attempt_failure") is not True
        or value.get("handoff_eligible") is not True
        or any(value.get(name) != 0 for name in (
            "staging_attempt_count", "rootfs_copy_count", "cleanup_dispatch_count"
        ))
    ):
        raise ContractError("H5 existing-source promotion manifest changed")
    return {"mode": MODE, "runner": runner, "recovery": recovery}


def load_spec(
    manifest_path: Path,
    expected_manifest_sha256: str,
    *,
    recovery: bool = False,
) -> base.F1Spec:
    manifest_bound = _bound(manifest_path)
    if manifest_bound.sha256 != _sha(expected_manifest_sha256, "manifest SHA256"):
        raise ContractError("manifest SHA256 changed")
    manifest = _read_json(manifest_bound, "manifest")
    run_id = _string(manifest.get("run_id"), "run_id")
    expected_keys = {
        "schema", "status", "run_id", "capability", "target",
        "candidate_boot", "rollback_boot", "transport", "debian_rootfs",
        "protected_rootfs", "observation", "recovery", "predecessor_abort",
        "connected_d0", "execution_closure", "resident_promotion",
        "independent_review", "authority",
    }
    if (
        set(manifest) != expected_keys
        or manifest.get("schema") != MANIFEST_SCHEMA
        or manifest.get("status") != staging.FINAL_MANIFEST_STATUS
        or manifest.get("capability") != CAPABILITY
        or RUN_RE.fullmatch(run_id) is None
        or manifest_bound.path.parent
        != (staging.PRIVATE_RUN_BASE / run_id).resolve(strict=True)
    ):
        raise ContractError("H5 existing-source manifest root changed")
    candidate_value = _dict(manifest.get("candidate_boot"), "candidate_boot")
    rollback_value = _dict(manifest.get("rollback_boot"), "rollback_boot")
    if set(candidate_value) != {
        "path", "size", "sha256", "expected_version", "expected_build",
        "partition", "first_boot_contract",
    } or set(rollback_value) != {
        "path", "size", "sha256", "expected_version", "expected_build",
        "partition",
    }:
        raise ContractError("H5 candidate or V2321 rollback shape changed")
    candidate = _load_embedded_bound(candidate_value, "candidate_boot")
    rollback = _load_embedded_bound(rollback_value, "rollback_boot")
    if (
        candidate.size != H5_CANDIDATE_SIZE
        or candidate.sha256 != H5_CANDIDATE_SHA256
        or candidate_value.get("expected_version") != H5_VERSION
        or candidate_value.get("expected_build") != H5_BUILD
        or candidate_value.get("partition") != "boot"
        or rollback.size != ROLLBACK_SIZE
        or rollback.sha256 != ROLLBACK_SHA256
        or rollback_value.get("expected_version") != ROLLBACK_VERSION
        or rollback_value.get("expected_build") != ROLLBACK_BUILD
        or rollback_value.get("partition") != "boot"
    ):
        raise ContractError("H5 candidate or V2321 rollback changed")
    debian = _dict(manifest.get("debian_rootfs"), "debian_rootfs")
    keyed = _dict(debian.get("keyed_source"), "keyed source")
    if set(keyed) != {"path", "size", "sha256", "device_path", "profile"}:
        raise ContractError("keyed source shape changed")
    source = _load_embedded_bound(keyed, "keyed source")
    protected = _dict(manifest.get("protected_rootfs"), "protected_rootfs")
    source_value = _dict(protected.get("source"), "protected source")
    source_identity = _string(source_value.get("device_identity"), "source identity")
    if (
        source.size != IMAGE_SIZE
        or source.sha256 != H5_SOURCE_SHA256
        or keyed.get("device_path") != H5_SOURCE_PATH
        or source_value.get("host_path") != str(source.path)
        or source_value.get("device_path") != H5_SOURCE_PATH
        or source_value.get("sha256") != H5_SOURCE_SHA256
        or IDENTITY_RE.fullmatch(source_identity) is None
        or protected.get("stage_path") != str(staging.derive_stage_dir(run_id))
    ):
        raise ContractError("protected H5 source identity changed")
    target = _dict(manifest.get("target"), "target")
    d0_bound = _load_bound(manifest.get("connected_d0"), "connected D0")
    d0 = _validate_d0(
        d0_bound,
        run_id=run_id,
        source_identity=source_identity,
        require_fresh=not recovery,
    )
    d0_target = _dict(d0.get("target"), "D0 target")
    if (
        target.get("profile") != staging.TARGET_PROFILE
        or target.get("bridge_selected_exact") is not True
        or target.get("bridge_device") != d0_target.get("bridge_device")
        or target.get("bridge_selected_realpath")
        != d0_target.get("bridge_selected_realpath")
        or target.get("current_version") != ROLLBACK_VERSION
        or target.get("current_build") != ROLLBACK_BUILD
    ):
        raise ContractError("target differs from fresh D0")
    predecessor = _dict(manifest.get("predecessor_abort"), "predecessor_abort")
    predecessor_manifest = _load_bound(
        predecessor.get("manifest"), "predecessor manifest"
    )
    _predecessor, predecessor_bounds = _validate_predecessor(
        predecessor_manifest.path,
        predecessor_manifest.sha256,
    )
    expected_predecessor = {
        key: _bound_dict(value)
        for key, value in predecessor_bounds.items()
        if key in {
            "manifest", "approval", "result", "timeline", "staging_result",
            "keyed_summary", *{
                f"journal_{index:02d}"
                for index in range(len(PREDECESSOR_ACTIONS))
            },
        }
    }
    if predecessor != expected_predecessor:
        raise ContractError("predecessor abort closure changed")
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
        raise ContractError("transport is not exact boot-only")
    observer = _dict(debian.get("observer"), "observer")
    observer_key = _load_bound(observer.get("private_key"), "observer key")
    observation = _dict(manifest.get("observation"), "observation")
    recovery_value = _dict(manifest.get("recovery"), "recovery")
    evidence = recovery_value.get("identity_evidence")
    if not isinstance(evidence, list) or len(evidence) != 2:
        raise ContractError("recovery evidence count changed")
    recovery_evidence = tuple(
        _load_bound(item, f"recovery evidence {index}")
        for index, item in enumerate(evidence)
    )
    recovery_serial_sha = _sha(
        recovery_value.get("adb_serial_sha256"), "recovery serial SHA256"
    )
    recovery_serial = base.recovery_serial_from_evidence(
        tuple(
            staging.BoundFile(
                f"recovery[{index}]", item.path, item.size, item.sha256
            )
            for index, item in enumerate(recovery_evidence)
        ),
        recovery_serial_sha,
    )
    first_boot = _dict(candidate_value.get("first_boot_contract"), "first boot")
    base.validate_candidate_first_boot_contract(
        first_boot,
        candidate_version=H5_VERSION,
        candidate_build=H5_BUILD,
        remote_final=H5_SOURCE_PATH,
        rootfs_sha256=H5_SOURCE_SHA256,
    )
    authority = _dict(manifest.get("authority"), "authority")
    if authority != {
        "candidate_transfer_authorized": False,
        "live_authority": False,
        "manifest_grants_live_authority": False,
        "rollback_authority_activates_after_candidate_start": True,
        "operator_attendance_required": True,
    }:
        raise ContractError("authority changed")
    validate_promotion_manifest(SimpleNamespace(manifest=manifest), recovery=recovery)
    bound_files: list[staging.BoundFile] = []
    all_bounds = {
        "candidate": candidate,
        "rollback": rollback,
        "source": source,
        "target.connected_d0_result": d0_bound,
        "target.connected_path_preflight": d0_bound,
        "review": review,
        **{
            f"predecessor.{key}": value
            for key, value in predecessor_bounds.items()
            if key in expected_predecessor
        },
        **{f"execution.{key}": value for key, value in closure.items()},
        **{f"recovery.{index}": value for index, value in enumerate(recovery_evidence)},
    }
    for label, value in all_bounds.items():
        bound_files.append(
            staging.BoundFile(label, value.path, value.size, value.sha256)
        )
    stage_spec = staging.StageSpec(
        run_id=run_id,
        manifest_path=manifest_bound.path,
        manifest_sha256=manifest_bound.sha256,
        local_image=source.path,
        local_size=source.size,
        local_sha256=source.sha256,
        remote_final=H5_SOURCE_PATH,
        remote_work=WORK_PATH,
        remote_stage_dir=str(staging.derive_stage_dir(run_id)),
        remote_payload=str(
            staging.derive_stage_dir(run_id) / staging.STAGE_PAYLOAD_NAME
        ),
        bridge_device=_string(target.get("bridge_device"), "bridge device"),
        bridge_realpath=_string(
            target.get("bridge_selected_realpath"), "bridge realpath"
        ),
        observer_device=_string(observer.get("device_ip"), "observer device"),
        adapter_size=closure["staging_contract"].size,
        adapter_sha256=closure["staging_contract"].sha256,
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
        candidate=staging.BoundFile(
            "candidate_boot", candidate.path, candidate.size, candidate.sha256
        ),
        rollback=staging.BoundFile(
            "rollback_boot", rollback.path, rollback.size, rollback.sha256
        ),
        flash_runner=staging.BoundFile(
            "transport",
            closure["flash_runner"].path,
            closure["flash_runner"].size,
            closure["flash_runner"].sha256,
        ),
        candidate_version=H5_VERSION,
        candidate_build=H5_BUILD,
        rollback_version=ROLLBACK_VERSION,
        rollback_build=ROLLBACK_BUILD,
        handoff_command=(
            base.HANDOFF_COMMAND,
            base.HANDOFF_TOKEN,
            H5_SOURCE_PATH,
            H5_SOURCE_SHA256,
        ),
        observer_key=observer_key.path,
        observer_public_key_sha256=_sha(
            observer.get("public_key_sha256"), "observer public key SHA256"
        ),
        observer_device=_string(observer.get("device_ip"), "observer device"),
        observer_port=int(observer.get("device_port")),
        observer_host_ncm_profile=_string(
            observer.get("host_ncm_profile"), "host NCM profile"
        ),
        candidate_boot_timeout=int(observation["candidate_boot_timeout_sec"]),
        handoff_timeout=int(observation["handoff_timeout_sec"]),
        ssh_marker_timeout=int(observation["ssh_marker_timeout_sec"]),
        candidate_return_timeout=int(observation["candidate_return_timeout_sec"]),
        rollback_boot_timeout=int(observation["rollback_boot_timeout_sec"]),
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
            staging.BoundFile(
                f"recovery[{index}]", item.path, item.size, item.sha256
            )
            for index, item in enumerate(recovery_evidence)
        ),
        orchestrator_size=closure["orchestrator"].size,
        orchestrator_sha256=closure["orchestrator"].sha256,
        candidate_first_boot=first_boot,
    )


def _validate_installed_result(
    spec: base.F1Spec,
    value: Any,
) -> dict[str, Any]:
    result = _dict(value, "H5 installed result")
    if (
        set(result) != resident.INSTALLED_RESULT_KEYS
        or spec.manifest.get("schema") != MANIFEST_SCHEMA
        or _dict(
            spec.manifest.get("resident_promotion"),
            "resident_promotion",
        ).get("mode") != MODE
        or result.get("schema") != resident.INSTALL_RESULT_SCHEMA
        or result.get("run_id") != spec.stage.run_id
        or result.get("status") != resident.INSTALL_STATUS
        or result.get("manifest_sha256") != spec.stage.manifest_sha256
        or result.get("candidate_sha256") != spec.candidate.sha256
        or type(result.get("candidate_transfer_count")) is not int
        or result.get("candidate_transfer_count") != 1
        or result.get("candidate_replay") is not False
        or type(result.get("resident_reboot_count")) is not int
        or result.get("resident_reboot_count") != 0
        or type(result.get("candidate_health_check_count")) is not int
        or result.get("candidate_health_check_count") != 1
        or type(result.get("rollback_transfer_count")) is not int
        or result.get("rollback_transfer_count") != 0
        or result.get("rollback_required") is not False
        or result.get("device_safety_state") != "RESIDENT_HEALTHY"
        or not isinstance(result.get("first_health"), dict)
        or tuple(result.get("timeline_events") or ()) != resident.INSTALL_EVENTS
    ):
        raise ContractError("H5 installed result changed")
    resident._validate_installed_health(spec, result["first_health"])  # noqa: SLF001
    return result


def _installed_result_from_terminal(
    spec: base.F1Spec,
    record: dict[str, Any],
) -> dict[str, Any]:
    common = {
        "schema", "sequence", "timestamp_utc", "run_id", "manifest_sha256",
        "state", "action",
    }
    payload = resident.INSTALLED_RESULT_KEYS - {
        "schema", "run_id", "manifest_sha256",
    }
    if (
        set(record) != common | payload
        or record.get("schema") != base.JOURNAL_SCHEMA
        or record.get("state") != resident.INSTALL_TERMINAL_STATE
        or record.get("action") != "closed"
    ):
        raise ContractError("H5 installed terminal journal changed")
    result = {key: record.get(key) for key in resident.INSTALLED_RESULT_KEYS}
    result["schema"] = resident.INSTALL_RESULT_SCHEMA
    return _validate_installed_result(spec, result)


def _publish_exact_installed_result(
    spec: base.F1Spec,
    transaction_dir: Path,
    result: dict[str, Any],
) -> None:
    exact = _validate_installed_result(spec, result)
    path = transaction_dir / "result.json"
    if path.exists():
        existing = _read_json(_bound(path), "existing H5 installed result")
        if existing != exact:
            raise ContractError("existing H5 installed result changed")
        return
    base.write_private_json_exclusive(path, exact)


def _close_installed_transaction(
    spec: base.F1Spec,
    transaction_dir: Path,
    journal_dir: Path,
    events: list[dict[str, str]],
    *,
    first_health: dict[str, Any],
) -> dict[str, Any]:
    base.ensure_event(
        transaction_dir,
        events,
        "live_session_end",
        allow_promotion=True,
    )
    names = [event["name"] for event in events]
    if tuple(names) != resident.INSTALL_EVENTS:
        raise ContractError("H5 installed success timeline changed")
    result = {
        "schema": resident.INSTALL_RESULT_SCHEMA,
        "run_id": spec.stage.run_id,
        "status": resident.INSTALL_STATUS,
        "manifest_sha256": spec.stage.manifest_sha256,
        "candidate_sha256": spec.candidate.sha256,
        "candidate_transfer_count": 1,
        "candidate_replay": False,
        "resident_reboot_count": 0,
        "candidate_health_check_count": 1,
        "rollback_transfer_count": 0,
        "rollback_required": False,
        "device_safety_state": "RESIDENT_HEALTHY",
        "first_health": first_health,
        "timeline_events": names,
    }
    exact = _validate_installed_result(spec, result)
    base.append_record(
        journal_dir,
        resident.INSTALL_TERMINAL_STATE,
        "closed",
        exact,
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    _publish_exact_installed_result(spec, transaction_dir, exact)
    return exact


def _validate_success_journal(
    spec: base.F1Spec,
    transaction_dir: Path,
    *,
    repair_missing_result: bool = False,
) -> dict[str, Any]:
    records = base.read_journal(spec, transaction_dir)
    if (
        tuple(record.get("action") for record in records) != SUCCESS_ACTIONS
        or tuple(record.get("state") for record in records) != SUCCESS_STATES
    ):
        raise ContractError("H5 existing-source success journal sequence changed")
    payloads = {
        "preflight": {
            "device_write", "candidate_attempted", "candidate_sha256",
            "rollback_sha256", "rootfs_sha256",
        },
        "approved": {
            "approval_consumed", "candidate_attempted", "rollback_pre_authorized",
            "approval_token_sha256", "approval_binding_sha256",
            "orchestrator_sha256",
        },
        "protected-paths-pre-verified": {
            "candidate_attempted", "staging_attempt_count", "rootfs_copy_count",
            "cleanup_dispatch_count", "record",
        },
        "resident-promotion-guard-armed": {
            "candidate_attempted", "candidate_replay", "guard",
        },
        "candidate-transfer-started": {
            "candidate_attempted", "candidate_sha256",
            "candidate_transfer_count_max", "rollback_required",
            "candidate_replay",
        },
        "candidate-flashed": {
            "candidate_sha256", "candidate_transfer_count", "candidate_replay",
            "rollback_required", "record",
        },
        "candidate-boot-ready": {
            "candidate_version", "candidate_build", "selftest_fail_zero",
            "channel", "health", "candidate_first_boot_health",
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
    preflight = by_action["preflight"]
    approved = by_action["approved"]
    pre = records[2]
    guard_record = by_action["resident-promotion-guard-armed"]
    started = by_action["candidate-transfer-started"]
    flashed = by_action["candidate-flashed"]
    boot = records[6]
    health = records[7]
    post = records[8]
    terminal = records[9]
    _sha(approved.get("approval_token_sha256"), "approval token SHA256")
    _sha(approved.get("approval_binding_sha256"), "approval binding SHA256")
    if (
        preflight.get("device_write") is not False
        or preflight.get("candidate_attempted") is not False
        or preflight.get("candidate_sha256") != spec.candidate.sha256
        or preflight.get("rollback_sha256") != spec.rollback.sha256
        or preflight.get("rootfs_sha256") != H5_SOURCE_SHA256
        or approved.get("approval_consumed") is not True
        or approved.get("candidate_attempted") is not False
        or approved.get("rollback_pre_authorized") is not True
        or approved.get("orchestrator_sha256") != spec.orchestrator_sha256
        or guard_record.get("candidate_attempted") is not False
        or guard_record.get("candidate_replay") is not False
        or not isinstance(guard_record.get("guard"), dict)
        or started.get("candidate_attempted") is not True
        or started.get("candidate_sha256") != spec.candidate.sha256
        or type(started.get("candidate_transfer_count_max")) is not int
        or started.get("candidate_transfer_count_max") != 1
        or started.get("rollback_required") is not True
        or started.get("candidate_replay") is not False
        or flashed.get("candidate_sha256") != spec.candidate.sha256
        or type(flashed.get("candidate_transfer_count")) is not int
        or flashed.get("candidate_transfer_count") != 1
        or flashed.get("candidate_replay") is not False
        or flashed.get("rollback_required") is not True
        or pre.get("candidate_attempted") is not False
        or post.get("handoff_eligible") is not True
    ):
        raise ContractError("H5 existing-source journal payload changed")
    base.resident_promotion_guard_inputs(transaction_dir, records)
    pre_proof = _validate_proof(spec, pre.get("record"), phase="pre-candidate")
    post_proof = _validate_proof(spec, post.get("record"), phase="post-candidate")
    native_exact = resident._require_exact_native_health(  # noqa: SLF001
        spec,
        boot.get("health"),
    )
    first_health = resident._validate_installed_health(  # noqa: SLF001
        spec,
        health.get("health"),
    )
    terminal_result = _installed_result_from_terminal(
        spec,
        terminal,
    )
    resident._validate_candidate_first_boot_journal(  # noqa: SLF001
        spec,
        {
            "rootfs-candidate-preflight": {
                "candidate_first_boot_preflight": pre_proof[
                    "candidate_first_boot_preflight"
                ]
            },
            "candidate-boot-ready": boot,
        },
    )
    if (
        any(
            type(record.get(name)) is not int or record.get(name) != 0
            for record in (pre, post)
            for name in (
                "staging_attempt_count", "rootfs_copy_count",
                "cleanup_dispatch_count",
            )
        )
        or pre_proof.get("source_identity") != post_proof.get("source_identity")
        or boot.get("candidate_version") != H5_VERSION
        or boot.get("candidate_build") != H5_BUILD
        or boot.get("selftest_fail_zero") is not True
        or _dict(boot.get("candidate_first_boot_health"), "first boot health").get(
            "proof"
        )
        is not True
        or type(health.get("candidate_health_check_count")) is not int
        or health.get("candidate_health_check_count") != 1
        or health.get("native_exact") != native_exact
        or first_health.get("native") != boot.get("health")
        or terminal_result.get("first_health") != first_health
    ):
        raise ContractError("H5 existing-source terminal proof changed")
    result_path = transaction_dir / "result.json"
    if not result_path.exists():
        if not repair_missing_result:
            raise ContractError("H5 installed result is absent")
        _publish_exact_installed_result(spec, transaction_dir, terminal_result)
    result = _read_json(_bound(result_path), "installed result")
    if (
        result != terminal_result
        or result.get("status") != resident.INSTALL_STATUS
        or result.get("device_safety_state") != "RESIDENT_HEALTHY"
    ):
        raise ContractError("H5 existing-source installed result changed")
    return result


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
        native_exact = resident._require_exact_native_health(  # noqa: SLF001
            spec, candidate_health
        )
        first_health = resident._promotion_health(  # noqa: SLF001
            spec, args, candidate_health
        )
        base.append_record(
            journal_dir,
            "CANDIDATE_HEALTH_VERIFIED",
            "candidate-health-verified",
            {
                "candidate_health_check_count": 1,
                "native_exact": native_exact,
                "health": first_health,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        protected = protected_paths_preflight(spec, args, phase="post-candidate")
        base.append_record(
            journal_dir,
            "PROTECTED_PATHS_VERIFIED",
            "protected-paths-post-verified",
            {
                "handoff_eligible": True,
                "staging_attempt_count": 0,
                "rootfs_copy_count": 0,
                "cleanup_dispatch_count": 0,
                "record": protected,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        if not guard.healthy(recheck=True):
            raise ContractError("H5 existing-source guard was lost")
        release = base.release_candidate_return_modemmanager_guard(
            guard,
            transaction_dir,
            corridor="resident-promotion",
        )
        released = True
        if release.get("released") is not True:
            raise ContractError("H5 existing-source guard did not release")
        result = _close_installed_transaction(
            spec,
            transaction_dir,
            journal_dir,
            events,
            first_health=first_health,
        )
        if _validate_success_journal(spec, transaction_dir) != result:
            raise ContractError("H5 existing-source result differs from journal")
        return result
    finally:
        if not released:
            release = base.release_candidate_return_modemmanager_guard(
                guard,
                transaction_dir,
                corridor="resident-promotion",
            )
            if release.get("released") is not True:
                raise ContractError("H5 existing-source guard did not release")


def _validate_recovery_journal(
    spec: base.F1Spec,
    transaction_dir: Path,
    records: list[dict[str, Any]],
    *,
    closed: bool,
) -> dict[str, Any] | None:
    actions = [str(record.get("action")) for record in records]
    states = [str(record.get("state")) for record in records]
    if (
        len(records) < 5
        or actions[:5] != list(SUCCESS_ACTIONS[:5])
        or states[:5] != list(SUCCESS_STATES[:5])
    ):
        raise ContractError("H5 rollback recovery prefix changed")
    if actions.count("candidate-transfer-started") != 1:
        raise ContractError("H5 rollback candidate intent count changed")
    if any(
        forbidden in actions
        for forbidden in (
            "staging-started", "rootfs-staged", "rootfs-candidate-preflight",
        )
    ) or any("handoff" in action or "cleanup" in action for action in actions):
        raise ContractError("H5 rollback contains a forbidden action")

    rollback_positions = [
        index
        for index, action in enumerate(actions)
        if action.startswith("rollback-") or action == "health-verified"
    ]
    split = rollback_positions[0] if rollback_positions else len(actions)
    candidate_order = list(SUCCESS_ACTIONS[5:9])
    candidate_suffix = actions[5:split]
    if candidate_suffix not in (
        [],
        ["candidate-invocation-failed"],
        *[candidate_order[:count] for count in range(1, len(candidate_order) + 1)],
    ):
        raise ContractError("H5 rollback candidate prefix changed")
    if any(actions.count(action) > 1 for action in candidate_order):
        raise ContractError("H5 rollback contains candidate replay")
    by_action = {str(record.get("action")): record for record in records}
    candidate_states = {
        "candidate-invocation-failed": "APPROVED",
        "candidate-flashed": "CANDIDATE_FLASHED",
        "candidate-boot-ready": "CANDIDATE_FLASHED",
        "candidate-health-verified": "CANDIDATE_HEALTH_VERIFIED",
        "protected-paths-post-verified": "PROTECTED_PATHS_VERIFIED",
    }
    for action, expected_state in candidate_states.items():
        record = by_action.get(action)
        if record is not None and record.get("state") != expected_state:
            raise ContractError(f"{action} state changed")

    rollback_end = len(actions)
    protected_suffix = actions[-1:] == ["protected-paths-post-rollback-verified"]
    if closed:
        if actions[-2:] != ["protected-paths-post-rollback-verified", "closed"]:
            raise ContractError("H5 rollback closure suffix changed")
        rollback_end -= 2
    elif "closed" in actions:
        raise ContractError("open H5 rollback contains closed")
    elif protected_suffix:
        rollback_end -= 1
    elif "protected-paths-post-rollback-verified" in actions:
        raise ContractError("open H5 rollback proof is not the exact suffix")

    rollback_suffix = actions[split:rollback_end]
    pair_count = 0
    while rollback_suffix[:2] == [
        "rollback-transfer-started", "rollback-process-not-started",
    ]:
        exact, _mode = base.rollback_pre_spawn_pair_is_exact(
            spec,
            transaction_dir,
            records[split + pair_count * 2],
            records[split + pair_count * 2 + 1],
            prior_rejections=pair_count,
        )
        if not exact:
            raise ContractError("H5 rollback pre-spawn pair changed")
        pair_count += 1
        rollback_suffix = rollback_suffix[2:]
    allowed_tails = (
        [],
        ["rollback-transfer-started"],
        ["rollback-transfer-started", "rollback-invocation-failed"],
        ["rollback-transfer-started", "rollback-flashed"],
        ["rollback-transfer-started", "rollback-flashed", "rollback-boot-ready"],
        [
            "rollback-transfer-started", "rollback-flashed",
            "rollback-boot-ready", "health-verified",
        ],
        ["rollback-transfer-started", "rollback-completion-recovered-by-health"],
        [
            "rollback-transfer-started", "rollback-completion-recovered-by-health",
            "rollback-boot-ready",
        ],
        [
            "rollback-transfer-started", "rollback-completion-recovered-by-health",
            "rollback-boot-ready", "health-verified",
        ],
    )
    if rollback_suffix not in allowed_tails:
        raise ContractError("H5 rollback journal tail changed")
    if (closed or protected_suffix) and (
        not rollback_suffix or rollback_suffix[-1] != "health-verified"
    ):
        raise ContractError("H5 rollback lacks exact final health")

    started = records[4]
    prefix_payloads = (
        {
            "device_write", "candidate_attempted", "candidate_sha256",
            "rollback_sha256", "rootfs_sha256",
        },
        {
            "approval_consumed", "candidate_attempted", "rollback_pre_authorized",
            "approval_token_sha256", "approval_binding_sha256",
            "orchestrator_sha256",
        },
        {
            "candidate_attempted", "staging_attempt_count", "rootfs_copy_count",
            "cleanup_dispatch_count", "record",
        },
        {"candidate_attempted", "candidate_replay", "guard"},
        {
            "candidate_attempted", "candidate_sha256",
            "candidate_transfer_count_max", "rollback_required",
            "candidate_replay",
        },
    )
    for record, payload, label in zip(
        records[:5],
        prefix_payloads,
        SUCCESS_ACTIONS[:5],
        strict=True,
    ):
        _journal_keyset(record, payload, label)
    _sha(records[1].get("approval_token_sha256"), "approval token SHA256")
    _sha(records[1].get("approval_binding_sha256"), "approval binding SHA256")
    if (
        records[0].get("device_write") is not False
        or records[0].get("candidate_attempted") is not False
        or records[0].get("candidate_sha256") != spec.candidate.sha256
        or records[0].get("rollback_sha256") != spec.rollback.sha256
        or records[0].get("rootfs_sha256") != H5_SOURCE_SHA256
        or records[1].get("approval_consumed") is not True
        or records[1].get("candidate_attempted") is not False
        or records[1].get("rollback_pre_authorized") is not True
        or records[1].get("orchestrator_sha256") != spec.orchestrator_sha256
        or records[2].get("candidate_attempted") is not False
        or records[3].get("candidate_attempted") is not False
        or records[3].get("candidate_replay") is not False
        or not isinstance(records[3].get("guard"), dict)
        or started.get("candidate_attempted") is not True
        or started.get("candidate_sha256") != spec.candidate.sha256
        or type(started.get("candidate_transfer_count_max")) is not int
        or started.get("candidate_transfer_count_max") != 1
        or started.get("candidate_replay") is not False
        or started.get("rollback_required") is not True
    ):
        raise ContractError("H5 rollback pre-candidate closure changed")
    base.resident_promotion_guard_inputs(transaction_dir, records)
    pre = _validate_proof(
        spec,
        records[2].get("record"),
        phase="pre-candidate",
    )
    if (
        any(
            type(records[2].get(name)) is not int
            or records[2].get(name) != 0
            for name in (
                "staging_attempt_count", "rootfs_copy_count",
                "cleanup_dispatch_count",
            )
        )
    ):
        raise ContractError("H5 rollback pre-candidate counters changed")
    candidate_failed = by_action.get("candidate-invocation-failed")
    if candidate_failed is not None:
        _journal_keyset(
            candidate_failed,
            {"candidate_attempted", "candidate_replay", "rollback_required", "record"},
            "candidate-invocation-failed",
        )
        if (
            candidate_failed.get("candidate_attempted") is not True
            or candidate_failed.get("candidate_replay") is not False
            or candidate_failed.get("rollback_required") is not True
        ):
            raise ContractError("H5 candidate failure record changed")
    candidate_flashed = by_action.get("candidate-flashed")
    if candidate_flashed is not None:
        _journal_keyset(
            candidate_flashed,
            {
                "candidate_sha256", "candidate_transfer_count", "candidate_replay",
                "rollback_required", "record",
            },
            "candidate-flashed",
        )
        if (
            candidate_flashed.get("candidate_sha256") != spec.candidate.sha256
            or type(candidate_flashed.get("candidate_transfer_count")) is not int
            or candidate_flashed.get("candidate_transfer_count") != 1
            or candidate_flashed.get("candidate_replay") is not False
            or candidate_flashed.get("rollback_required") is not True
        ):
            raise ContractError("H5 candidate flash record changed")
    candidate_boot = by_action.get("candidate-boot-ready")
    if candidate_boot is not None:
        _journal_keyset(
            candidate_boot,
            {
                "candidate_version", "candidate_build", "selftest_fail_zero",
                "channel", "health", "candidate_first_boot_health",
            },
            "candidate-boot-ready",
        )
        resident._require_exact_native_health(  # noqa: SLF001
            spec,
            candidate_boot.get("health"),
        )
        if (
            candidate_boot.get("candidate_version") != H5_VERSION
            or candidate_boot.get("candidate_build") != H5_BUILD
            or candidate_boot.get("selftest_fail_zero") is not True
        ):
            raise ContractError("H5 candidate boot record changed")
        resident._validate_candidate_first_boot_journal(  # noqa: SLF001
            spec,
            {
                "rootfs-candidate-preflight": {
                    "candidate_first_boot_preflight": pre[
                        "candidate_first_boot_preflight"
                    ]
                },
                "candidate-boot-ready": candidate_boot,
            },
        )
    candidate_health = by_action.get("candidate-health-verified")
    if candidate_health is not None:
        _journal_keyset(
            candidate_health,
            {"candidate_health_check_count", "native_exact", "health"},
            "candidate-health-verified",
        )
        exact_health = resident._validate_installed_health(  # noqa: SLF001
            spec,
            candidate_health.get("health"),
        )
        native_exact = resident._require_exact_native_health(  # noqa: SLF001
            spec,
            exact_health.get("native"),
        )
        if (
            type(candidate_health.get("candidate_health_check_count")) is not int
            or candidate_health.get("candidate_health_check_count") != 1
            or candidate_health.get("native_exact") != native_exact
            or candidate_boot is None
            or exact_health.get("native") != candidate_boot.get("health")
        ):
            raise ContractError("H5 candidate health record changed")
    post_candidate = by_action.get("protected-paths-post-verified")
    if post_candidate is not None:
        _journal_keyset(
            post_candidate,
            {
                "handoff_eligible", "staging_attempt_count", "rootfs_copy_count",
                "cleanup_dispatch_count", "record",
            },
            "protected-paths-post-verified",
        )
        post = _validate_proof(
            spec,
            post_candidate.get("record"),
            phase="post-candidate",
        )
        if (
            post_candidate.get("handoff_eligible") is not True
            or any(
                type(post_candidate.get(name)) is not int
                or post_candidate.get(name) != 0
                for name in (
                    "staging_attempt_count", "rootfs_copy_count",
                    "cleanup_dispatch_count",
                )
            )
            or post.get("source_identity") != pre.get("source_identity")
        ):
            raise ContractError("H5 source identity changed after candidate")
    rollback_payloads = {
        "rollback-transfer-started": {
            "rollback_sha256", "rollback_attempt_limit", "rollback_process_started",
            "candidate_replay", "recovery_mode", "prior_pre_spawn_rejections",
        },
        "rollback-invocation-failed": {
            "candidate_replay", "rollback_retry_forbidden", "record",
        },
        "rollback-flashed": {
            "rollback_sha256", "rollback_transfer_count", "candidate_replay",
            "record",
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
        "protected-paths-post-rollback-verified": "HEALTH_VERIFIED",
    }
    for action, expected_state in expected_states.items():
        for record in (item for item in records if item.get("action") == action):
            if record.get("state") != expected_state:
                raise ContractError(f"{action} state changed")
            if action in rollback_payloads:
                _journal_keyset(record, rollback_payloads[action], action)
    for attempt_index, record in enumerate(
        item for item in records if item.get("action") == "rollback-transfer-started"
    ):
        if (
            record.get("rollback_sha256") != spec.rollback.sha256
            or type(record.get("rollback_attempt_limit")) is not int
            or record.get("rollback_attempt_limit") != 1
            or record.get("rollback_process_started") is not None
            or record.get("candidate_replay") is not False
            or record.get("recovery_mode") not in {"from-native", "adb-recovery"}
            or type(record.get("prior_pre_spawn_rejections")) is not int
            or record.get("prior_pre_spawn_rejections") != attempt_index
        ):
            raise ContractError("H5 rollback intent record changed")
    rollback_failed = by_action.get("rollback-invocation-failed")
    if rollback_failed is not None and (
        rollback_failed.get("candidate_replay") is not False
        or rollback_failed.get("rollback_retry_forbidden") is not True
    ):
        raise ContractError("H5 rollback failure record changed")
    rollback_flashed = by_action.get("rollback-flashed")
    if rollback_flashed is not None and (
        rollback_flashed.get("rollback_sha256") != spec.rollback.sha256
        or type(rollback_flashed.get("rollback_transfer_count")) is not int
        or rollback_flashed.get("rollback_transfer_count") != 1
        or rollback_flashed.get("candidate_replay") is not False
    ):
        raise ContractError("H5 rollback flashed record changed")
    recovered = by_action.get("rollback-completion-recovered-by-health")
    if recovered is not None and (
        recovered.get("rollback_reinvoked") is not False
        or recovered.get("exact_v2321_health") is not True
    ):
        raise ContractError("H5 rollback health recovery record changed")
    rollback_boot = by_action.get("rollback-boot-ready")
    if rollback_boot is not None:
        payload = {"rollback_version", "rollback_build", "selftest_fail_zero"}
        if "recovered_from_health" in rollback_boot:
            payload.add("recovered_from_health")
        _journal_keyset(rollback_boot, payload, "rollback-boot-ready")
        if (
            rollback_boot.get("rollback_version") != ROLLBACK_VERSION
            or rollback_boot.get("rollback_build") != ROLLBACK_BUILD
            or rollback_boot.get("selftest_fail_zero") is not True
            or (
                "recovered_from_health" in rollback_boot
                and rollback_boot.get("recovered_from_health") is not True
            )
        ):
            raise ContractError("H5 rollback boot record changed")
    final_health = by_action.get("health-verified")
    if final_health is not None:
        legacy._validate_final_health(  # noqa: SLF001
            spec,
            {
                key: value
                for key, value in final_health.items()
                if key not in COMMON_JOURNAL_KEYS
            },
        )
    post_rollback = by_action.get("protected-paths-post-rollback-verified")
    if post_rollback is not None:
        _journal_keyset(
            post_rollback,
            {
                "staging_attempt_count", "rootfs_copy_count",
                "cleanup_dispatch_count", "record",
            },
            "protected-paths-post-rollback-verified",
        )
        post = _validate_proof(
            spec,
            post_rollback.get("record"),
            phase="post-rollback",
        )
        if (
            post.get("source_identity") != pre.get("source_identity")
            or any(
                type(post_rollback.get(name)) is not int
                or post_rollback.get(name) != 0
                for name in (
                    "staging_attempt_count", "rootfs_copy_count",
                    "cleanup_dispatch_count",
                )
            )
        ):
            raise ContractError("H5 rollback protected closure changed")
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
    exact = legacy._validate_rollback_result(  # noqa: SLF001
        spec,
        transaction_dir,
        actions,
        result,
    )
    existing = _read_json(_bound(transaction_dir / "result.json"), "rollback result")
    if terminal.get("state") != "CLOSED" or existing != exact:
        raise ContractError("H5 rollback terminal record differs from result")
    return exact


def recover_or_repair(
    spec: base.F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    transaction_dir = base.exact_transaction_dir(spec, args.transaction_dir)
    records = base.read_journal(spec, transaction_dir)
    if records[-1].get("action") == "closed":
        approval = base.approved_bindings(spec, args, recovery=True)
        base.verify_local_closure(spec)
        base.require_consumed_approval(records, approval)
        if records[-1].get("state") == resident.INSTALL_TERMINAL_STATE:
            return _validate_success_journal(
                spec,
                transaction_dir,
                repair_missing_result=True,
            )
        exact = _validate_recovery_journal(
            spec,
            transaction_dir,
            records,
            closed=True,
        )
        assert exact is not None
        return exact
    actions = [str(record.get("action")) for record in records]
    if "candidate-transfer-started" not in actions:
        raise ContractError("H5 recovery lacks durable candidate intent")
    approval = base.approved_bindings(spec, args, recovery=True)
    base.verify_local_closure(spec)
    base.require_consumed_approval(records, approval)
    _validate_recovery_journal(spec, transaction_dir, records, closed=False)
    protected_already = actions[-1:] == ["protected-paths-post-rollback-verified"]
    result_path = transaction_dir / "result.json"
    if result_path.exists():
        if not protected_already:
            raise ContractError("open H5 rollback result precedes protected closure")
        existing = _read_json(_bound(result_path), "open rollback result")
        exact = legacy._validate_rollback_result(  # noqa: SLF001
            spec,
            transaction_dir,
            actions,
            existing,
        )
        base.append_record(
            transaction_dir / "journal",
            "CLOSED",
            "closed",
            exact,
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        closed = _validate_recovery_journal(
            spec,
            transaction_dir,
            base.read_journal(spec, transaction_dir),
            closed=True,
        )
        if closed != exact:
            raise ContractError("H5 rollback close-only repair changed result")
        return exact

    corridor = resident._next_rollback_guard_corridor(  # noqa: SLF001
        transaction_dir
    )
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
        if not protected_already:
            proof = protected_paths_preflight(spec, args, phase="post-rollback")
            base.append_record(
                transaction_dir / "journal",
                "HEALTH_VERIFIED",
                "protected-paths-post-rollback-verified",
                {
                    "staging_attempt_count": 0,
                    "rootfs_copy_count": 0,
                    "cleanup_dispatch_count": 0,
                    "record": proof,
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
            raise ContractError("H5 rollback guard did not release")

    try:
        result = base.recover_approved_rollback(
            spec,
            args,
            return_guard=guard,
            before_close=before_close,
        )
        exact = _validate_recovery_journal(
            spec,
            transaction_dir,
            base.read_journal(spec, transaction_dir),
            closed=True,
        )
        if exact != result:
            raise ContractError("H5 rollback result differs from journal")
        return result
    finally:
        if not released:
            release = base.release_candidate_return_modemmanager_guard(
                guard,
                transaction_dir,
                corridor=corridor,
            )
            if release.get("released") is not True:
                raise ContractError("H5 rollback guard did not release")


def _d0_spec(
    *,
    run_id: str,
    manifest: dict[str, Any],
    bounds: dict[str, Bound],
    bridge_device: str,
    bridge_realpath: str,
    observer_device: str,
) -> base.F1Spec:
    closure = review_source_records()
    stage_spec = staging.StageSpec(
        run_id=run_id,
        manifest_path=bounds["manifest"].path,
        manifest_sha256=bounds["manifest"].sha256,
        local_image=bounds["source"].path,
        local_size=IMAGE_SIZE,
        local_sha256=H5_SOURCE_SHA256,
        remote_final=H5_SOURCE_PATH,
        remote_work=WORK_PATH,
        remote_stage_dir=str(staging.derive_stage_dir(run_id)),
        remote_payload=str(
            staging.derive_stage_dir(run_id) / staging.STAGE_PAYLOAD_NAME
        ),
        bridge_device=bridge_device,
        bridge_realpath=bridge_realpath,
        observer_device=observer_device,
        adapter_size=closure["staging_contract"]["size"],
        adapter_sha256=closure["staging_contract"]["sha256"],
        tcpctl_host=Path(closure["tcpctl_host"]["path"]),
        tcpctl_host_size=closure["tcpctl_host"]["size"],
        tcpctl_host_sha256=closure["tcpctl_host"]["sha256"],
        bound_files=(),
        rootfs_profile=staging.PHASE3_PROFILE,
        starting_version=ROLLBACK_VERSION,
        starting_build=ROLLBACK_BUILD,
    )
    first_boot = _dict(
        _dict(manifest.get("candidate_boot"), "candidate").get(
            "first_boot_contract"
        ),
        "first boot",
    )
    synthetic = {
        "protected_rootfs": {
            "disposition": DISPOSITION,
            "source": {
                "device_path": H5_SOURCE_PATH,
                "size": IMAGE_SIZE,
                "sha256": H5_SOURCE_SHA256,
                "mode": FILE_MODE,
                "nlink": FILE_NLINK,
            },
            "work_path": WORK_PATH,
            "stage_path": str(staging.derive_stage_dir(run_id)),
            "enable_path": H5_ENABLE,
            "latch_path": H5_LATCH,
        }
    }
    return base.F1Spec(
        stage=stage_spec,
        manifest=synthetic,
        candidate=staging.BoundFile(
            "candidate", bounds["candidate"].path, H5_CANDIDATE_SIZE,
            H5_CANDIDATE_SHA256,
        ),
        rollback=staging.BoundFile(
            "rollback", bounds["rollback"].path, ROLLBACK_SIZE, ROLLBACK_SHA256,
        ),
        flash_runner=staging.BoundFile(
            "flash",
            Path(closure["flash_runner"]["path"]),
            closure["flash_runner"]["size"],
            closure["flash_runner"]["sha256"],
        ),
        candidate_version=H5_VERSION,
        candidate_build=H5_BUILD,
        rollback_version=ROLLBACK_VERSION,
        rollback_build=ROLLBACK_BUILD,
        handoff_command=(base.HANDOFF_COMMAND, base.HANDOFF_TOKEN, H5_SOURCE_PATH, H5_SOURCE_SHA256),
        observer_key=bounds["observer_key"].path,
        observer_public_key_sha256="0" * 64,
        observer_device=observer_device,
        observer_port=2222,
        observer_host_ncm_profile="a90-v3406-ncm",
        candidate_boot_timeout=180,
        handoff_timeout=905,
        ssh_marker_timeout=30,
        candidate_return_timeout=180,
        rollback_boot_timeout=180,
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
        recovery_serial_sha256="0" * 64,
        recovery_serial="unused-d0",
        recovery_evidence=(),
        orchestrator_size=Path(base.__file__).stat().st_size,
        orchestrator_sha256=legacy.sha256_file(Path(base.__file__)),
        candidate_first_boot=first_boot,
    )


def execute_connected_d0(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_RE.fullmatch(args.run_id) is None or SEQ_RE.fullmatch(args.evidence_sequence) is None:
        raise ContractError("run ID or evidence sequence is not exact")
    predecessor, bounds = _validate_predecessor(
        args.predecessor_manifest,
        args.expect_predecessor_manifest_sha256,
    )
    run_dir = staging.PRIVATE_RUN_BASE / args.run_id
    if run_dir.exists() or run_dir.is_symlink():
        raise ContractError("fresh campaign directory must be absent")
    run_dir.mkdir(mode=0o700)
    try:
        connected.require_exact_bridge(args.bridge_device, args.expect_realpath, args)
        usb = connected.exact_usb_identity(args.expect_realpath)
        ncm = staging.require_host_ncm_ready(args.device_ip, args.expect_realpath)
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
        spec = _d0_spec(
            run_id=args.run_id,
            manifest=predecessor,
            bounds=bounds,
            bridge_device=args.bridge_device,
            bridge_realpath=args.expect_realpath,
            observer_device=args.device_ip,
        )
        proof = protected_paths_preflight(spec, args, phase="connected-d0")
        guard_absent = not os.path.lexists(base.cdc_guard.GUARD_RUNTIME_RULE_PATH)
        if not guard_absent:
            raise ContractError("global F1 guard is already owned")
        result = {
            "schema": D0_SCHEMA,
            "timestamp_utc": utc_now(),
            "run_id": args.run_id,
            "target": {
                "profile": staging.TARGET_PROFILE,
                "matching_a90_usb_devices": 1,
                "bridge_device": args.bridge_device,
                "bridge_selected_realpath": args.expect_realpath,
                "bridge_selected_exact": True,
                **usb,
            },
            "host_ncm": ncm,
            "health": health,
            "protected_source": proof,
            "predecessor_manifest": _bound_dict(bounds["manifest"]),
            "candidate_boot": _bound_dict(bounds["candidate"]),
            "rollback_boot": _bound_dict(bounds["rollback"]),
            "source_host": _bound_dict(bounds["source"]),
            "global_f1_guard_absent": True,
            "safety": {
                "device_write": False,
                "flash": False,
                "payload_sent": False,
                "reboot_requested": False,
                "rootfs_staged": False,
            },
        }
        output = run_dir / f"connected-d0-{args.evidence_sequence}.json"
        staging.write_private_json_exclusive(output, result)
        return {
            "schema": D0_SCHEMA,
            "decision": "PASS_H5_EXISTING_SOURCE_CONNECTED_D0",
            "run_id": args.run_id,
            "connected_d0": _bound_dict(_bound(output)),
            "device_write": False,
            "flash": False,
            "payload_sent": False,
            "reboot_requested": False,
        }
    except Exception:
        if not any(run_dir.iterdir()):
            run_dir.rmdir()
        raise


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    if RUN_RE.fullmatch(args.run_id) is None:
        raise ContractError("run ID is not exact")
    run_dir = (staging.PRIVATE_RUN_BASE / args.run_id).resolve(strict=True)
    predecessor, bounds = _validate_predecessor(
        args.predecessor_manifest,
        args.expect_predecessor_manifest_sha256,
    )
    d0_bound = _bound(args.connected_d0)
    if d0_bound.sha256 != _sha(args.expect_connected_d0_sha256, "D0 SHA256"):
        raise ContractError("connected D0 SHA256 changed")
    d0 = _validate_d0(
        d0_bound,
        run_id=args.run_id,
        require_fresh=True,
    )
    proof = _dict(d0.get("protected_source"), "D0 protected source")
    review_bound = _bound(args.review_report, private=False, mode=0o644)
    if review_bound.sha256 != _sha(args.expect_review_report_sha256, "review SHA256"):
        raise ContractError("review report SHA256 changed")
    _validate_review(_bound_dict(review_bound))
    target = _dict(predecessor.get("target"), "predecessor target")
    debian = _dict(predecessor.get("debian_rootfs"), "predecessor Debian rootfs")
    observer = _dict(debian.get("observer"), "predecessor observer")
    recovery_source = _dict(
        target.get("recovery_adb_identity_evidence"),
        "recovery identity evidence",
    )
    recovery_labels = ("candidate_recovery_log", "rollback_recovery_log")
    if set(recovery_source) != set(recovery_labels):
        raise ContractError("predecessor recovery evidence labels changed")
    recovery_evidence = [
        _bound_dict(
            _bound(
                Path(
                    _string(
                        _dict(recovery_source[label], f"recovery {label}").get(
                            "path"
                        ),
                        f"recovery {label} path",
                    )
                )
            )
        )
        for label in recovery_labels
    ]
    closure = review_source_records()
    runner = closure["runner"]
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": staging.FINAL_MANIFEST_STATUS,
        "run_id": args.run_id,
        "capability": CAPABILITY,
        "target": {
            "profile": staging.TARGET_PROFILE,
            "current_version": ROLLBACK_VERSION,
            "current_build": ROLLBACK_BUILD,
            "bridge_device": d0["target"]["bridge_device"],
            "bridge_selected_realpath": d0["target"]["bridge_selected_realpath"],
            "bridge_selected_exact": True,
        },
        "candidate_boot": dict(predecessor["candidate_boot"]),
        "rollback_boot": dict(predecessor["rollback_boot"]),
        "transport": {
            "candidate_and_rollback_runner": closure["flash_runner"]["path"],
            "runner_size": closure["flash_runner"]["size"],
            "runner_sha256": closure["flash_runner"]["sha256"],
            "only_partition_payload": "boot",
            "forbidden_partition_writes": True,
        },
        "debian_rootfs": {
            "keyed_source": {
                "path": str(bounds["source"].path),
                "size": IMAGE_SIZE,
                "sha256": H5_SOURCE_SHA256,
                "device_path": H5_SOURCE_PATH,
                "profile": staging.PHASE3_PROFILE,
            },
            "work_copy": {
                "device_path": WORK_PATH,
                "must_be_absent_before_handoff": True,
            },
            "handoff_command": [
                base.HANDOFF_COMMAND, base.HANDOFF_TOKEN,
                H5_SOURCE_PATH, H5_SOURCE_SHA256,
            ],
            "observer": {
                "private_key": _bound_dict(bounds["observer_key"]),
                "public_key_sha256": observer["public_key_sha256"],
                "device_ip": observer["device_ip"],
                "device_port": observer["device_port"],
                "host_ncm_profile": observer["host_ncm_profile"],
                "transport_scope": base.OBSERVER_TRANSPORT_SCOPE,
                "wifi_or_external_network": False,
            },
        },
        "protected_rootfs": {
            "disposition": DISPOSITION,
            "source": {
                "host_path": str(bounds["source"].path),
                "device_path": H5_SOURCE_PATH,
                "size": IMAGE_SIZE,
                "sha256": H5_SOURCE_SHA256,
                "mode": FILE_MODE,
                "nlink": FILE_NLINK,
                "device_identity": proof["source_identity"],
            },
            "work_path": WORK_PATH,
            "stage_path": str(staging.derive_stage_dir(args.run_id)),
            "enable_path": H5_ENABLE,
            "latch_path": H5_LATCH,
        },
        "observation": {
            "mode": base.UNATTENDED_OBSERVATION_MODE,
            "candidate_boot_timeout_sec": 180,
            "handoff_timeout_sec": 905,
            "ssh_marker_timeout_sec": 30,
            "candidate_return_timeout_sec": 180,
            "rollback_boot_timeout_sec": 180,
            "display_required": False,
            "handoff_attempt_limit": 0,
        },
        "recovery": {
            "adb_serial_sha256": target["recovery_adb_serial_sha256"],
            "identity_evidence": recovery_evidence,
            "physical_path": "operator-attended Download or TWRP",
        },
        "predecessor_abort": {
            key: _bound_dict(value)
            for key, value in bounds.items()
            if key in {
                "manifest", "approval", "result", "timeline", "staging_result",
                "keyed_summary", *{
                    f"journal_{index:02d}" for index in range(len(PREDECESSOR_ACTIONS))
                },
            }
        },
        "connected_d0": _bound_dict(d0_bound),
        "execution_closure": closure,
        "resident_promotion": {
            "mode": MODE,
            "runner": runner,
            "rootfs_preflight_disposition": DISPOSITION,
            "success_terminal": resident.INSTALL_STATUS,
            "candidate_health_checks": 1,
            "rollback_on_post_attempt_failure": True,
            "handoff_eligible": True,
            "staging_attempt_count": 0,
            "rootfs_copy_count": 0,
            "cleanup_dispatch_count": 0,
        },
        "independent_review": _bound_dict(review_bound),
        "authority": {
            "candidate_transfer_authorized": False,
            "live_authority": False,
            "manifest_grants_live_authority": False,
            "rollback_authority_activates_after_candidate_start": True,
            "operator_attendance_required": True,
        },
    }
    output = run_dir / "h5-existing-source-manifest.json"
    if output.exists() or output.is_symlink():
        raise ContractError("manifest output must be absent")
    staging.write_private_json_exclusive(output, manifest)
    output_bound = _bound(output)
    load_spec(output, output_bound.sha256)
    return {
        "schema": MANIFEST_SCHEMA,
        "decision": "PASS_H5_EXISTING_SOURCE_MANIFEST",
        "run_id": args.run_id,
        "manifest": _bound_dict(output_bound),
        "candidate_authority": False,
        "live_authority": False,
        "device_contact": False,
        "device_write": False,
        "rootfs_staged": False,
    }


def audit() -> dict[str, Any]:
    audit_spec = SimpleNamespace(
            manifest={
                "protected_rootfs": {
                    "disposition": DISPOSITION,
                    "source": {
                        "device_path": H5_SOURCE_PATH,
                        "size": IMAGE_SIZE,
                        "sha256": H5_SOURCE_SHA256,
                        "mode": FILE_MODE,
                        "nlink": FILE_NLINK,
                    },
                    "work_path": WORK_PATH,
                    "stage_path": str(staging.derive_stage_dir(
                        "a90-v3406-debian-display-f1-20991231-99"
                    )),
                    "enable_path": H5_ENABLE,
                    "latch_path": H5_LATCH,
                }
            },
            stage=SimpleNamespace(
                remote_stage_dir=str(staging.derive_stage_dir(
                    "a90-v3406-debian-display-f1-20991231-99"
                ))
            ),
            candidate_first_boot={
                "enable_path": H5_ENABLE,
                "latch_path": H5_LATCH,
            },
    )
    commands = _protected_commands(audit_spec)
    first_boot_command = [
        "run", "/bin/busybox", "sh", "-c",
        base.candidate_first_boot_state_absence_script(
            audit_spec.candidate_first_boot
        ),
    ]
    read_frames = [*commands.values(), first_boot_command]
    issues: list[str] = []
    if any(_wire_bytes(command) > MAX_WIRE_BYTES for command in read_frames):
        issues.append("protected read command exceeds wire bound")
    source = Path(__file__).read_text(encoding="utf-8")
    subject = source[: source.index("\ndef audit(")]
    for forbidden in (
        "--execute-approved-stage",
        "stage_command(spec",
        "/bin/busybox rm",
        "/bin/busybox cp",
        "switch-root-to-distro\",",
    ):
        if forbidden in subject:
            issues.append(f"forbidden source route present: {forbidden}")
    return {
        "schema": MANIFEST_SCHEMA,
        "mode": "host-only-audit",
        "capability": CAPABILITY,
        "review_closure": review_source_records(),
        "protected_read_frame_count": len(read_frames),
        "max_protected_wire_bytes": max(_wire_bytes(value) for value in read_frames),
        "contract_issues": issues,
        "ready_for_review": not issues,
        "device_contact": False,
        "device_write": False,
        "rootfs_staged": False,
        "flash": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit-only", action="store_true")
    mode.add_argument("--execute-connected-d0", action="store_true")
    mode.add_argument("--build-manifest", action="store_true")
    mode.add_argument("--prepare-approval", action="store_true")
    mode.add_argument("--execute-approved-install", action="store_true")
    mode.add_argument("--recover-approved-rollback", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--evidence-sequence", default="01")
    parser.add_argument("--predecessor-manifest", type=Path)
    parser.add_argument("--expect-predecessor-manifest-sha256")
    parser.add_argument("--connected-d0", type=Path)
    parser.add_argument("--expect-connected-d0-sha256")
    parser.add_argument("--review-report", type=Path)
    parser.add_argument("--expect-review-report-sha256")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expect-manifest-sha256")
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


def _require(args: argparse.Namespace, names: tuple[str, ...]) -> None:
    missing = [name for name in names if getattr(args, name) is None]
    if missing:
        raise ContractError(f"required arguments missing: {missing}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.audit_only:
        result = audit()
    elif args.execute_connected_d0:
        _require(args, (
            "run_id", "predecessor_manifest",
            "expect_predecessor_manifest_sha256", "bridge_device",
            "expect_realpath", "device_ip",
        ))
        result = execute_connected_d0(args)
    elif args.build_manifest:
        _require(args, (
            "run_id", "predecessor_manifest",
            "expect_predecessor_manifest_sha256", "connected_d0",
            "expect_connected_d0_sha256", "review_report",
            "expect_review_report_sha256",
        ))
        result = build_manifest(args)
    else:
        _require(args, ("manifest", "expect_manifest_sha256"))
        spec = load_spec(
            args.manifest,
            args.expect_manifest_sha256,
            recovery=args.recover_approved_rollback,
        )
        if args.prepare_approval:
            if args.approval is not None or args.transaction_dir is not None:
                raise ContractError("approval preparation accepts no live inputs")
            result = base.prepare_approval(spec)
        elif args.execute_approved_install:
            if not args.operator_attended:
                raise ContractError("live H5 install requires awake attendance")
            _require(args, ("approval", "transaction_dir"))
            result = base.execute_approved_f1(
                spec,
                args,
                promotion_tail=promotion_tail,
            )
        else:
            if not args.operator_attended:
                raise ContractError("rollback recovery requires awake attendance")
            _require(args, ("transaction_dir",))
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
    except Exception as exc:  # noqa: BLE001
        print(
            f"a90-h5-existing-source-install-v1: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)
