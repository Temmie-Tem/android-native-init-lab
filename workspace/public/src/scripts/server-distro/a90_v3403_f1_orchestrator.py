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
    recovery_serial_sha256: str
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
    if not isinstance(value, int) or value <= 0:
        raise ContractError(f"{label} must be a positive integer")
    return value


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
    handoff_timeout = require_positive_int(
        observation.get("handoff_timeout_sec"),
        "observation.handoff_timeout_sec",
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

    target = _dict(manifest.get("target"), "target")
    recovery_serial_sha256_value = target.get("recovery_adb_serial_sha256")
    if recovery_serial_sha256_value is None and allow_draft:
        recovery_serial_sha256 = ""
        issues.append("final manifest lacks recovery_adb_serial_sha256")
    else:
        recovery_serial_sha256 = validate_sha256(
            recovery_serial_sha256_value,
            "target.recovery_adb_serial_sha256",
        )

    rootfs_staging = _dict(manifest.get("rootfs_staging"), "rootfs_staging")
    if rootfs_staging.get("independent_review_passed") is not True:
        issues.append("staging independent safety review is not passed")

    authority = _dict(manifest.get("authority"), "authority")
    for name in (
        "candidate_transfer_authorized",
        "live_authority",
        "rootfs_staging_authorized",
        "rollback_authority_activates_after_candidate_start",
    ):
        if authority.get(name) is not True:
            issues.append(f"authority.{name} is not true")

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
        if not isinstance(size_value, int) or size_value <= 0:
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
            recovery_serial_sha256=recovery_serial_sha256,
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
) -> Path:
    journal_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    existing = sorted(journal_dir.glob("*.json"))
    sequence = len(existing)
    path = journal_dir / f"{sequence:04d}-{action}.json"
    body = {
        "schema": JOURNAL_SCHEMA,
        "sequence": sequence,
        "timestamp_utc": utc_now(),
        "run_id": run_id,
        "manifest_sha256": manifest_sha256,
        "state": state,
        "action": action,
        **payload,
    }
    encoded = (json.dumps(body, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)
    dir_fd = os.open(journal_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
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
        value = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or value.get("schema") != JOURNAL_SCHEMA
            or value.get("sequence") != sequence
            or value.get("run_id") != spec.stage.run_id
            or value.get("manifest_sha256") != spec.stage.manifest_sha256
        ):
            raise ContractError(f"invalid journal record: {path}")
        records.append(value)
    return records


def write_private_json(path: Path, payload: Any) -> None:
    d1.write_json(path, payload)
    path.chmod(0o600)


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


def command_record(path: Path, returncode: int) -> dict[str, Any]:
    return {
        "returncode": returncode,
        "raw_log": str(path),
        "raw_log_size": path.stat().st_size,
        "raw_log_sha256": sha256_file(path),
    }


def run_logged(
    command: list[str],
    *,
    log_path: Path,
    timeout: float,
) -> dict[str, Any]:
    with log_path.open("xb") as output:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output.flush()
        os.fsync(output.fileno())
    log_path.chmod(0o600)
    return command_record(log_path, completed.returncode)


def approved_bindings(spec: F1Spec, args: argparse.Namespace) -> None:
    if spec.manifest.get("schema") != FINAL_MANIFEST_SCHEMA:
        raise ContractError("live F1 refuses a non-final manifest schema")
    if spec.manifest.get("status") != FINAL_MANIFEST_STATUS:
        raise ContractError("live F1 refuses a non-ready manifest status")
    if args.approved_manifest_sha256 != spec.stage.manifest_sha256:
        raise ContractError("approved manifest sha256 does not match")
    current_sha = sha256_file(Path(__file__).resolve())
    if args.approved_orchestrator_sha256 != current_sha:
        raise ContractError("approved orchestrator sha256 does not match")
    if args.approved_run_id != spec.stage.run_id:
        raise ContractError("approved run_id does not match")


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
    recovery_serial: str | None = None,
) -> list[str]:
    bound = spec.rollback if rollback else spec.candidate
    version = spec.rollback_version if rollback else spec.candidate_version
    build = spec.rollback_build if rollback else spec.candidate_build
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
        f"{version} build={build}",
        "--verify-protocol",
        "selftest",
    ]
    if recovery_serial is None:
        command.append("--from-native")
    else:
        command.extend(["--serial", recovery_serial])
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
    if not journal_paths:
        raise ContractError("staging journal is absent")
    require_private_regular(journal_paths[-1])
    last = json.loads(journal_paths[-1].read_text(encoding="utf-8"))
    if (
        not isinstance(last, dict)
        or last.get("schema") != "a90_v3403_absent_only_stage_journal_v1"
        or last.get("state") != "closed"
        or last.get("result") != value
    ):
        raise ContractError("staging journal is not durably closed on the exact result")
    return value


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
    return d1.run_shell(
        args.bridge_host,
        args.bridge_port,
        args.remote_timeout,
        script,
    )


def run_handoff(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    line = a90ctl.encode_cmdv1_line(list(spec.handoff_command))
    text = a90ctl.bridge_exchange(
        args.bridge_host,
        args.bridge_port,
        line,
        spec.handoff_timeout,
        markers=(b"exec_switch_root_now", b"A90P1 END "),
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
            version = d1.run_cmd(
                args.bridge_host,
                args.bridge_port,
                args.remote_timeout,
                ["version"],
                allow_error=True,
            )
            text = str(version.get("text") or "")
            if spec.candidate_version in text and spec.candidate_build in text:
                selftest = d1.run_cmd(
                    args.bridge_host,
                    args.bridge_port,
                    args.remote_timeout,
                    ["selftest"],
                    allow_error=True,
                )
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
        result["source_preflight"] = remote_source_preflight(spec, args)
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
    write_private_json(transaction_dir / "observation.json", result)
    return result


def verify_final_health(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    bridge = staging.require_exact_bridge(spec.stage, args)
    baseline = staging.require_baseline(args)
    return {
        "exact_bridge": True,
        "selected_realpath": bridge.get("selected_realpath"),
        "version": spec.rollback_version,
        "build": spec.rollback_build,
        "selftest_fail_zero": True,
        "pstore_entries_zero": True,
        "baseline": baseline,
    }


def require_rollback_source_native(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    staging.require_exact_bridge(spec.stage, args)
    version = d1.run_cmd(
        args.bridge_host,
        args.bridge_port,
        args.remote_timeout,
        ["version"],
        allow_error=True,
    )
    selftest = d1.run_cmd(
        args.bridge_host,
        args.bridge_port,
        args.remote_timeout,
        ["selftest"],
        allow_error=True,
    )
    version_text = str(version.get("text") or "")
    known = (
        spec.candidate_version in version_text and spec.candidate_build in version_text
    ) or (
        spec.rollback_version in version_text and spec.rollback_build in version_text
    )
    if not known or "fail=0" not in str(selftest.get("text") or ""):
        raise ContractError("native rollback source is not the exact candidate or baseline")
    return {"version": version, "selftest": selftest}


def validate_recovery_serial(spec: F1Spec, serial: str | None) -> str | None:
    if serial is None:
        return None
    if not spec.recovery_serial_sha256:
        raise ContractError("manifest does not bind a recovery ADB serial digest")
    actual = hashlib.sha256(serial.encode("utf-8")).hexdigest()
    if actual != spec.recovery_serial_sha256:
        raise ContractError("recovery ADB serial does not match the manifest binding")
    return serial


def invoke_rollback(
    spec: F1Spec,
    args: argparse.Namespace,
    transaction_dir: Path,
    journal_dir: Path,
    events: list[dict[str, str]],
    *,
    recovery_serial: str | None,
) -> dict[str, Any]:
    add_event(transaction_dir, events, "rollback_flash_start")
    append_record(
        journal_dir,
        "RECOVERY_ROLLBACK",
        "rollback-transfer-started",
        {
            "rollback_sha256": spec.rollback.sha256,
            "rollback_attempt_count": 1,
            "candidate_replay": False,
            "recovery_mode": "adb-recovery" if recovery_serial else "from-native",
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    record = run_logged(
        flash_command(
            spec,
            args,
            rollback=True,
            recovery_serial=recovery_serial,
        ),
        log_path=transaction_dir / "rollback-flash.raw.log",
        timeout=args.flash_command_timeout,
    )
    if record["returncode"] != 0:
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
    add_event(transaction_dir, events, "rollback_flash_done")
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
    add_event(transaction_dir, events, "rollback_boot_ready")
    append_record(
        journal_dir,
        "HEALTH_VERIFIED",
        "health-verified",
        health,
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    return health


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
    add_event(transaction_dir, events, "live_session_end")
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
    write_private_json(transaction_dir / "result.json", result)
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
        add_event(transaction_dir, events, "live_session_end")
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
    write_private_json(transaction_dir / "result.json", result)
    append_record(
        journal_dir,
        "ABORTED",
        "aborted-before-candidate",
        result,
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )


def execute_approved_f1(spec: F1Spec, args: argparse.Namespace) -> dict[str, Any]:
    approved_bindings(spec, args)
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
    stage_result_path = PRIVATE_RUN_BASE / spec.stage.run_id / "staging-live" / "result.json"
    if stage_result_path.exists():
        stage_record = {"reused_exact_closed_result": True}
    else:
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
        staging.require_baseline(args)
        verify_local_closure(spec)
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
        flash_command(spec, args, rollback=False),
        log_path=transaction_dir / "candidate-flash.raw.log",
        timeout=args.flash_command_timeout,
    )
    if candidate_record["returncode"] != 0:
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
            recovery_serial=None,
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
    add_event(transaction_dir, events, "candidate_flash_done")
    append_record(
        journal_dir,
        "CANDIDATE_FLASHED",
        "candidate-boot-ready",
        {
            "candidate_version": spec.candidate_version,
            "candidate_build": spec.candidate_build,
            "selftest_fail_zero": True,
        },
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    add_event(transaction_dir, events, "candidate_boot_ready")

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
        recovery_serial=None,
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
    approved_bindings(spec, args)
    verify_local_closure(spec)
    transaction_dir = exact_transaction_dir(spec, args.transaction_dir)
    records = read_journal(spec, transaction_dir)
    actions = action_names(records)
    if "candidate-transfer-started" not in actions:
        raise ContractError("rollback recovery requires durable candidate intent")
    if "closed" in actions:
        raise ContractError("transaction is already closed")
    events = load_timeline(transaction_dir)
    journal_dir = transaction_dir / "journal"

    rollback_started = "rollback-transfer-started" in actions
    rollback_flashed = "rollback-flashed" in actions
    if rollback_started and not rollback_flashed:
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
        if "rollback_flash_done" not in [event.get("name") for event in events]:
            add_event(transaction_dir, events, "rollback_flash_done")
        if "rollback_boot_ready" not in [event.get("name") for event in events]:
            add_event(transaction_dir, events, "rollback_boot_ready")
    elif rollback_flashed:
        health = verify_final_health(spec, args)
        if "rollback_boot_ready" not in [event.get("name") for event in events]:
            add_event(transaction_dir, events, "rollback_boot_ready")
    else:
        recovery_serial = validate_recovery_serial(spec, args.recovery_serial)
        if recovery_serial is None:
            require_rollback_source_native(spec, args)
        health = invoke_rollback(
            spec,
            args,
            transaction_dir,
            journal_dir,
            events,
            recovery_serial=recovery_serial,
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
        "def execute_approved_f1(",
        "def recover_approved_rollback(",
        "def invoke_rollback(",
        "def validate_stage_result(",
        "def approved_bindings(",
    )
    for token in required_functions:
        if token not in source:
            issues.append(f"missing function: {token}")
    execute_start = source.find("def execute_approved_f1(")
    recover_start = source.find("def recover_approved_rollback(")
    simulate_start = source.find("def simulate_transaction(")
    if min(execute_start, recover_start, simulate_start) < 0:
        return tuple(issues)
    execute = source[execute_start:recover_start]
    ordered = (
        "approved_bindings(spec, args)",
        "verify_local_closure(spec)",
        "validate_stage_result(spec)",
        "staging.require_baseline(args)",
        '"candidate-transfer-started"',
        "flash_command(spec, args, rollback=False)",
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
    recover = source[recover_start:simulate_start]
    if "rollback=False" in recover or "spec.candidate" in recover:
        issues.append("recovery contains a candidate execution route")
    if "rollback_retry_forbidden" not in source:
        issues.append("rollback ambiguity stop is missing")
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
        "ready_for_live_f1": not all_issues,
        "device_contact": False,
        "device_write": False,
        "candidate_route_in_recovery": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expect-manifest-sha256", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute-approved-f1", action="store_true")
    mode.add_argument("--recover-approved-rollback", action="store_true")
    parser.add_argument("--approved-manifest-sha256", default="")
    parser.add_argument("--approved-orchestrator-sha256", default="")
    parser.add_argument("--approved-run-id", default="")
    parser.add_argument("--transaction-dir", type=Path)
    parser.add_argument("--recovery-serial")
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
    live = args.execute_approved_f1 or args.recover_approved_rollback
    spec, issues = load_spec(
        args.manifest,
        args.expect_manifest_sha256,
        allow_draft=not live,
    )
    if not live:
        result = inspect_manifest(spec, issues)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if not result["contract_issues"] else 2
    if args.transaction_dir is None:
        raise ContractError("--transaction-dir is required for live F1")
    if args.execute_approved_f1:
        if args.recovery_serial is not None:
            raise ContractError("initial execution does not accept --recovery-serial")
        result = execute_approved_f1(spec, args)
    else:
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
