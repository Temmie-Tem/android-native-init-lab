#!/usr/bin/env python3
"""One-shot attended recovery of the exact H15 pre-latch armed state."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
for _path in (SCRIPT_DIR, REVAL_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import a90_h15_ufs_d1_runner_v1 as d1  # noqa: E402
import a90_h15_ufs_f1_runner_v1 as f1  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402
import run_d1_chroot_mvp as transport  # noqa: E402


SCHEMA = "a90-h15-armed-recovery-journal-v1"
RESULT_SCHEMA = "a90-h15-armed-recovery-result-v1"
QUALIFICATION_SCHEMA = "a90-h15-armed-recovery-qualification-v1"
APPROVAL_SCHEMA = "a90-h15-armed-recovery-approval-prepared-v1"
APPROVAL_BINDING_SCHEMA = "a90-h15-armed-recovery-approval-binding-v1"
APPROVAL_PREFIX = "A90-H15-ARMED-RECOVERY-APPROVE:"
APPROVAL_TTL_SEC = 1800
JOURNAL_MAX_BYTES = 16 * 1024 * 1024
CAPABILITY = "A90_H15_PRELATCH_ARMED_RECOVERY_V1"
RUN_ID = "a90-h15-ufs-f1-20260810-01"
MANIFEST_SHA256 = "bbc9ee91e8067eb07dd598c8aad9549c874cbec13a264fcfe899786826a74375"
INSTALL_RESULT_SHA256 = "ec5371c7734f7b78e54f81c124279238fcf86af32db457392c43635b7b5327d1"
PREDECESSOR_EXECUTION_SHA256 = (
    "1f4f5332e687ad783c9cf072ed3779918781c31079012565e61bb243c4e8dba4"
)
ENABLE_PATH = "/cache/a90-auto-handoff-phase3-minimal-h15.enable"
LATCH_PATH = "/cache/a90-auto-handoff-phase3-minimal-h15.done"
PRIVATE_RUN_BASE = (REPO_ROOT / "workspace/private/runs/server-distro").resolve()
EXPECTED_MANIFEST_PATH = (PRIVATE_RUN_BASE / RUN_ID / "manifest.json").resolve()
EXPECTED_INSTALL_RESULT_PATH = (
    PRIVATE_RUN_BASE / RUN_ID / "h15-f1-live" / "result.json"
).resolve()
EXPECTED_INCIDENT_DIR = (
    PRIVATE_RUN_BASE / RUN_ID / "h15-d1" / "run01"
).resolve()
EXPECTED_RECOVERY_DIR = (
    PRIVATE_RUN_BASE / RUN_ID / "h15-armed-recovery" / "run01"
).resolve()
QUALIFICATION_REL = (
    "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    "phase3-minimal-h15/armed-recovery-qualification.json"
)
REVIEW_REPORT_REL = (
    "docs/reports/A90_H15_ARMED_RECOVERY_INDEPENDENT_REVIEW_2026-08-10.json"
)
INCIDENT_REPORT_REL = (
    "docs/reports/A90_H15_PRELATCH_UFS_PREFLIGHT_EPERM_INCIDENT_2026-08-10.md"
)
TARGET_CONTRACT_REL = "docs/operations/targets/A90_TARGET_CONTRACT.md"
JOURNAL_NAMES = (
    "0000-open.json",
    "0001-unlink-intent.json",
    "0002-unlink-result.json",
    "0003-final-health.json",
    "0004-closed.json",
)
JOURNAL_ACTIONS = (
    "open-exact-armed-recovery",
    "unlink-intent",
    "unlink-result",
    "final-health",
    "closed",
)
EXECUTION_RELS = tuple(
    sorted(
        set(f1.EXECUTION_SOURCE_RELS)
        | {
            INCIDENT_REPORT_REL,
            "workspace/public/src/scripts/server-distro/"
            "a90_h15_armed_recovery_v1.py",
        }
    )
)


class ContractError(RuntimeError):
    """Raised before widening or replaying the exact armed recovery."""


def _effect_args() -> argparse.Namespace:
    return argparse.Namespace(
        bridge_host="127.0.0.1",
        bridge_port=54321,
        bridge_timeout=60.0,
        remote_timeout=60.0,
        flash_command_timeout=900.0,
        ssh_connect_timeout=8.0,
        poll_interval=3.0,
        transfer_timeout=1200.0,
    )


def execution_closure() -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    digest = hashlib.sha256()
    for relative in sorted(EXECUTION_RELS):
        path = (REPO_ROOT / relative).resolve(strict=True)
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise ContractError(f"recovery source is not regular: {relative}")
        sha = f1.sha256_file(path)
        files[relative] = {"size": info.st_size, "sha256": sha}
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(info.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(sha.encode("ascii"))
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "files": files}


def _require_regular(path: Path, expected_sha256: str, label: str) -> Path:
    lexical = path.absolute()
    if lexical.is_symlink():
        raise ContractError(f"{label} is a symlink")
    resolved = lexical.resolve(strict=True)
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode) or f1.sha256_file(resolved) != expected_sha256:
        raise ContractError(f"{label} changed")
    return resolved


def _load_json(path: Path, expected_sha256: str, label: str) -> dict[str, Any]:
    resolved = _require_regular(path, expected_sha256, label)
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is not exact JSON") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label} root is not an object")
    return value


def _load_qualification(closure: dict[str, Any]) -> dict[str, Any]:
    path = REPO_ROOT / QUALIFICATION_REL
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ContractError("armed recovery qualification is not regular")
    value = json.loads(path.read_text(encoding="utf-8"))
    report = REPO_ROOT / REVIEW_REPORT_REL
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schema",
            "capability",
            "verdict",
            "execution_closure_sha256",
            "execution_hashes",
            "incident_run_id",
            "predecessor_execution_closure_sha256",
            "review_scope",
            "new_hazard_or_incident",
            "review_report",
            "review_report_sha256",
            "live_authority",
        }
        or value.get("schema") != QUALIFICATION_SCHEMA
        or value.get("capability") != CAPABILITY
        or value.get("verdict") != "PASS_GO"
        or value.get("execution_closure_sha256") != closure["sha256"]
        or value.get("execution_hashes") != closure["files"]
        or value.get("incident_run_id") != RUN_ID
        or value.get("predecessor_execution_closure_sha256")
        != PREDECESSOR_EXECUTION_SHA256
        or value.get("review_scope")
        != "exact-h15-run01-prelatch-armed-marker-recovery"
        or value.get("new_hazard_or_incident") is not True
        or value.get("review_report") != REVIEW_REPORT_REL
        or not report.exists()
        or report.is_symlink()
        or not stat.S_ISREG(report.stat().st_mode)
        or value.get("review_report_sha256") != f1.sha256_file(report)
        or value.get("live_authority") is not False
    ):
        raise ContractError("armed recovery qualification is not current")
    return value


def _validate_manifest(value: dict[str, Any]) -> None:
    candidate = value.get("candidate_boot")
    binding = candidate.get("compiled_binding") if isinstance(candidate, dict) else None
    authority = value.get("authority")
    target = value.get("target")
    if (
        value.get("schema") != f1.SCHEMA
        or value.get("run_id") != RUN_ID
        or value.get("status") != "ready-for-attended-f1"
        or value.get("execution_closure", {}).get("sha256")
        != PREDECESSOR_EXECUTION_SHA256
        or not isinstance(authority, dict)
        or authority.get("candidate_replay") is not False
        or authority.get("rootfs_payload_count") != 0
        or authority.get("sd_stage_count") != 0
        or authority.get("userdata_write_count") != 0
        or not isinstance(candidate, dict)
        or candidate.get("expected_version") != f1.CANDIDATE_VERSION
        or candidate.get("expected_build") != f1.CANDIDATE_BUILD
        or candidate.get("sha256")
        != "b285d5f48402b88583adff55b2423870f481e0f0169ffca127b490a567d4d6cd"
        or not isinstance(binding, dict)
        or binding.get("enable_path") != ENABLE_PATH
        or binding.get("latch_path") != LATCH_PATH
        or not isinstance(target, dict)
        or target.get("profile") != "galaxy-a90-5g-native-init"
        or target.get("bridge_device") != f1.EXACT_BRIDGE_DEVICE
    ):
        raise ContractError("H15 incident manifest binding changed")


def _validate_install_result(value: dict[str, Any]) -> None:
    if (
        value.get("schema") != f1.RESULT_SCHEMA
        or value.get("status") != "PASS_A90_H15_UFS_RESIDENT_INSTALLED"
        or value.get("run_id") != RUN_ID
        or value.get("manifest_sha256") != MANIFEST_SHA256
        or value.get("device_safety_state") != "RESIDENT_HEALTHY"
        or value.get("candidate_transfer_count") != 1
        or value.get("rollback_transfer_count") != 0
        or value.get("candidate_replay") is not False
        or value.get("rootfs_payload_count") != 0
        or value.get("sd_stage_count") != 0
        or value.get("userdata_write_count") != 0
    ):
        raise ContractError("H15 install terminal changed")


def _incident_args(manifest_path: Path, install_result_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        manifest=manifest_path,
        expect_manifest_sha256=MANIFEST_SHA256,
        install_result=install_result_path,
        expect_install_result_sha256=INSTALL_RESULT_SHA256,
        expect_execution_closure_sha256=PREDECESSOR_EXECUTION_SHA256,
        transaction_dir=EXPECTED_INCIDENT_DIR,
    )


def _load_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], Any, str, dict[str, Any]]:
    if args.expect_manifest_sha256 != MANIFEST_SHA256:
        raise ContractError("manifest SHA binding changed")
    if args.expect_install_result_sha256 != INSTALL_RESULT_SHA256:
        raise ContractError("install-result SHA binding changed")
    if args.expect_predecessor_execution_closure_sha256 != PREDECESSOR_EXECUTION_SHA256:
        raise ContractError("predecessor execution closure changed")
    manifest_path = _require_regular(args.manifest, MANIFEST_SHA256, "manifest")
    result_path = _require_regular(
        args.install_result, INSTALL_RESULT_SHA256, "install result"
    )
    if manifest_path != EXPECTED_MANIFEST_PATH:
        raise ContractError("manifest path changed")
    if result_path != EXPECTED_INSTALL_RESULT_PATH:
        raise ContractError("install-result path changed")
    manifest = _load_json(manifest_path, MANIFEST_SHA256, "manifest")
    result = _load_json(result_path, INSTALL_RESULT_SHA256, "install result")
    _validate_manifest(manifest)
    _validate_install_result(result)
    incident_dir = args.incident_transaction_dir.resolve(strict=True)
    if incident_dir != EXPECTED_INCIDENT_DIR:
        raise ContractError("incident transaction directory changed")
    records = d1._read_records(incident_dir)  # noqa: SLF001
    if len(records) != 4:
        raise ContractError("incident journal is not the exact pending prefix")
    incident_args = _incident_args(manifest_path, result_path)
    intent_sha256 = d1._validate_records(  # noqa: SLF001
        records, incident_dir, incident_args, manifest
    )
    if intent_sha256 is None:
        raise ContractError("incident intent is absent")
    observation = records[3].get("observation")
    if (
        not isinstance(observation, dict)
        or observation.get("proof") is not False
        or observation.get("guard_release", {}).get("released") is not True
        or records[2].get("arm_reboot_command_dispatch_count") != 1
    ):
        raise ContractError("incident no-replay observation changed")
    closure = execution_closure()
    if args.expect_recovery_execution_closure_sha256 != closure["sha256"]:
        raise ContractError("recovery execution closure changed")
    _load_qualification(closure)
    spec = f1._spec(manifest, manifest_path, MANIFEST_SHA256)  # noqa: SLF001
    return manifest, spec, intent_sha256, closure


def _expected_enable(intent_sha256: str) -> bytes:
    if f1.HEX64_RE.fullmatch(intent_sha256) is None:
        raise ContractError("incident intent is not a SHA256")
    return (
        "schema=a90-auto-handoff-userdata-ro-v1\n"
        f"build={f1.CANDIDATE_BUILD}\n"
        "root_kind=userdata-ext4-ro-noload\n"
        "userdata_devname=sda33\n"
        "userdata_dev=259:17\n"
        "userdata_sectors=231577432\n"
        "userdata_label=A90D4ROOT\n"
        "userdata_marker=userdata=appliance-root\n"
        "userdata_uuid=300aaf21-412c-4238-9106-56414eaab105\n"
        "userdata_content_manifest_sha256="
        "e1950058627446d6bbd487d6a17b80f5766be4956b54cb56659b541dab09f8f6\n"
        f"intent_sha256={intent_sha256}\n"
        "state=armed-after-native-health\n"
    ).encode("utf-8")


def _read_enable(effect_args: argparse.Namespace, expected: bytes) -> tuple[dict[str, Any], bytes]:
    command = ["run", "/bin/busybox", "cat", ENABLE_PATH]
    record = base.run_f1_cmd(effect_args, command)
    exact = base.require_exact_f1_command_receipt(
        record, command, "H15 armed recovery enable capture"
    )
    text = str(exact.get("text") or "").replace("\r", "")
    start = text.find("schema=a90-auto-handoff-userdata-ro-v1\n")
    end = text.find("[exit 0]\n", start)
    if start < 0 or end < 0:
        raise ContractError("enable capture framing changed")
    body = text[start:end].encode("utf-8")
    if body != expected or text.count(expected.decode("utf-8")) != 1:
        raise ContractError("enable bytes differ from the incident intent")
    return record, body


def _write_preserved(path: Path, body: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}")
    fd = os.open(
        temporary,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_CLOEXEC
        | os.O_NOFOLLOW,
        0o600,
    )
    try:
        offset = 0
        while offset < len(body):
            written = os.write(fd, body[offset:])
            if written <= 0:
                raise ContractError("short host preservation write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.link(temporary, path, follow_symlinks=False)
        _fsync_directory(path.parent)
    except FileExistsError as exc:
        raise ContractError("refusing to replace preserved enable bytes") from exc
    finally:
        temporary.unlink(missing_ok=True)
        _fsync_directory(path.parent)
    return {
        "path": str(path.resolve(strict=True)),
        "size": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "mode": 0o600,
    }


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _canonicalize_exact_temp_hardlink(path: Path, info: os.stat_result) -> os.stat_result:
    if info.st_nlink == 1:
        return info
    if info.st_nlink != 2:
        raise ContractError("private evidence link count changed")
    prefix = f".{path.name}.tmp-"
    aliases: list[Path] = []
    for entry in path.parent.iterdir():
        if not entry.name.startswith(prefix):
            continue
        candidate = entry.lstat()
        if (
            not entry.is_symlink()
            and stat.S_ISREG(candidate.st_mode)
            and candidate.st_dev == info.st_dev
            and candidate.st_ino == info.st_ino
            and candidate.st_mode == info.st_mode
            and candidate.st_size == info.st_size
            and candidate.st_nlink == 2
        ):
            aliases.append(entry)
    if len(aliases) != 1:
        raise ContractError("private evidence hardlink is not the exact writer temp")
    aliases[0].unlink()
    _fsync_directory(path.parent)
    current = path.lstat()
    if (
        current.st_dev != info.st_dev
        or current.st_ino != info.st_ino
        or current.st_mode != info.st_mode
        or current.st_size != info.st_size
        or current.st_nlink != 1
    ):
        raise ContractError("private evidence temp-link retirement changed identity")
    return current


def _validate_preserved(
    directory: Path,
    preserved: dict[str, Any],
    expected: bytes,
) -> dict[str, Any]:
    expected_path = directory / "enable-before.bin"
    if (
        set(preserved) != {"path", "size", "sha256", "mode"}
        or preserved.get("path") != str(expected_path)
        or preserved.get("size") != len(expected)
        or preserved.get("sha256") != hashlib.sha256(expected).hexdigest()
        or preserved.get("mode") != 0o600
    ):
        raise ContractError("preserved enable binding changed")
    info = _canonicalize_exact_temp_hardlink(expected_path, expected_path.lstat())
    if (
        not stat.S_ISREG(info.st_mode)
        or expected_path.is_symlink()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
        or info.st_size != len(expected)
    ):
        raise ContractError("preserved enable file shape changed")
    descriptor = os.open(expected_path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        current = os.fstat(descriptor)
        if (
            current.st_dev != info.st_dev
            or current.st_ino != info.st_ino
            or not stat.S_ISREG(current.st_mode)
            or stat.S_IMODE(current.st_mode) != 0o600
            or current.st_nlink != 1
            or current.st_size != len(expected)
        ):
            raise ContractError("preserved enable identity changed while opening")
        body = b""
        while len(body) <= len(expected):
            chunk = os.read(descriptor, len(expected) + 1 - len(body))
            if not chunk:
                break
            body += chunk
    finally:
        os.close(descriptor)
    if body != expected:
        raise ContractError("preserved enable bytes changed")
    return preserved


def _recovery_dir(args: argparse.Namespace, *, absent: bool) -> Path:
    lexical = args.recovery_transaction_dir.absolute()
    path = lexical.resolve(strict=not absent)
    if lexical != EXPECTED_RECOVERY_DIR or path != EXPECTED_RECOVERY_DIR or path.exists() == absent:
        state = "absent" if absent else "existing"
        raise ContractError(f"recovery transaction directory is not exact and {state}")
    if not absent:
        info = lexical.lstat()
        if (
            lexical.is_symlink()
            or not stat.S_ISDIR(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise ContractError("recovery transaction directory shape changed")
    return path


def _approval_path() -> Path:
    return EXPECTED_RECOVERY_DIR.parent / "run01-approval-prepared.json"


def _cleanup_script(enable_sha256: str, enable_size: int) -> str:
    if f1.HEX64_RE.fullmatch(enable_sha256) is None:
        raise ContractError("enable SHA256 is malformed")
    if type(enable_size) is not int or enable_size <= 0 or enable_size > 4096:
        raise ContractError("enable size is outside the exact small-file bound")
    return "\n".join(
        (
            "set -eu",
            f"P='{ENABLE_PATH}'",
            f"L='{LATCH_PATH}'",
            f"E='{enable_sha256}'",
            '[ -f "$P" ]',
            '[ ! -L "$P" ]',
            f'M=$(/bin/busybox stat -c "%F|%s|%a|%h" "$P")',
            f'[ "$M" = "regular file|{enable_size}|600|1" ]',
            '[ ! -e "$L" ]',
            '[ ! -L "$L" ]',
            'A=$(/bin/busybox sha256sum "$P")',
            'A=${A%% *}',
            '[ "$A" = "$E" ]',
            '/bin/busybox rm -- "$P"',
            "/bin/busybox sync",
            '[ ! -e "$P" ]',
            '[ ! -L "$P" ]',
            '[ ! -e "$L" ]',
            '[ ! -L "$L" ]',
            "echo A90H15_ARMED_RECOVERY removed=1 synced=1 enable=absent latch=untouched",
        )
    )


def _approval_binding(
    intent_sha256: str,
    closure: dict[str, Any],
    *,
    created_utc: str,
    expires_utc: str,
) -> dict[str, Any]:
    expected = _expected_enable(intent_sha256)
    enable_sha = hashlib.sha256(expected).hexdigest()
    script = _cleanup_script(enable_sha, len(expected))
    return {
        "schema": APPROVAL_BINDING_SCHEMA,
        "capability": CAPABILITY,
        "run_id": RUN_ID,
        "incident_transaction_dir": str(EXPECTED_INCIDENT_DIR),
        "recovery_transaction_dir": str(EXPECTED_RECOVERY_DIR),
        "manifest_sha256": MANIFEST_SHA256,
        "install_result_sha256": INSTALL_RESULT_SHA256,
        "predecessor_execution_closure_sha256": PREDECESSOR_EXECUTION_SHA256,
        "recovery_execution_closure_sha256": closure["sha256"],
        "intent_sha256": intent_sha256,
        "enable_path": ENABLE_PATH,
        "latch_path": LATCH_PATH,
        "enable_size": len(expected),
        "enable_sha256": enable_sha,
        "cleanup_script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "action_budget": 1,
        "reboot_count": 0,
        "handoff_count": 0,
        "payload_transfer_count": 0,
        "partition_write_count": 0,
        "userdata_write_count": 0,
        "operator_attendance_required": True,
        "created_utc": created_utc,
        "expires_utc": expires_utc,
    }


def prepare_approval(args: argparse.Namespace) -> dict[str, Any]:
    _, _, intent_sha256, closure = _load_inputs(args)
    _recovery_dir(args, absent=True)
    created = dt.datetime.now(dt.UTC).replace(microsecond=0)
    expires = created + dt.timedelta(seconds=APPROVAL_TTL_SEC)
    binding = _approval_binding(
        intent_sha256,
        closure,
        created_utc=created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        expires_utc=expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    binding_sha = f1.json_sha256(binding)
    value = {
        "schema": APPROVAL_SCHEMA,
        "run_id": RUN_ID,
        "approval_binding": binding,
        "approval_binding_sha256": binding_sha,
        "approval_token": APPROVAL_PREFIX + binding_sha,
        "device_contact": False,
        "device_write": False,
        "live_authority_from_preparation": False,
    }
    f1.write_json_exclusive(_approval_path(), value)
    return value


def _validate_approval(
    args: argparse.Namespace,
    intent_sha256: str,
    closure: dict[str, Any],
) -> dict[str, Any]:
    path = _approval_path()
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_mode & 0o077:
        raise ContractError("recovery approval is not private regular mode")
    value = json.loads(path.read_text(encoding="utf-8"))
    binding = value.get("approval_binding") if isinstance(value, dict) else None
    if not isinstance(binding, dict):
        raise ContractError("recovery approval binding is absent")
    created = f1.parse_utc(binding.get("created_utc"), "recovery approval created")
    expires = f1.parse_utc(binding.get("expires_utc"), "recovery approval expires")
    expected = _approval_binding(
        intent_sha256,
        closure,
        created_utc=created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        expires_utc=expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    binding_sha = f1.json_sha256(binding)
    now = dt.datetime.now(dt.UTC)
    if (
        set(value)
        != {
            "schema",
            "run_id",
            "approval_binding",
            "approval_binding_sha256",
            "approval_token",
            "device_contact",
            "device_write",
            "live_authority_from_preparation",
        }
        or value.get("schema") != APPROVAL_SCHEMA
        or value.get("run_id") != RUN_ID
        or binding != expected
        or value.get("approval_binding_sha256") != binding_sha
        or value.get("approval_token") != APPROVAL_PREFIX + binding_sha
        or args.approval != value.get("approval_token")
        or value.get("device_contact") is not False
        or value.get("device_write") is not False
        or value.get("live_authority_from_preparation") is not False
        or expires - created != dt.timedelta(seconds=APPROVAL_TTL_SEC)
        or now < created
        or now > expires
    ):
        raise ContractError("recovery approval is not fresh and exact")
    return value


def _write_record(directory: Path, index: int, action: str, payload: dict[str, Any]) -> None:
    if action != JOURNAL_ACTIONS[index]:
        raise ContractError("recovery journal action/index mismatch")
    f1.write_json_exclusive(
        directory / JOURNAL_NAMES[index],
        {"schema": SCHEMA, "sequence": index, "action": action, **payload},
    )


def _read_records(directory: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, name in enumerate(JOURNAL_NAMES):
        path = directory / name
        try:
            info = path.lstat()
        except FileNotFoundError:
            if any(
                os.path.lexists(directory / later)
                for later in JOURNAL_NAMES[index + 1 :]
            ):
                raise ContractError("recovery journal has a gap")
            break
        info = _canonicalize_exact_temp_hardlink(path, info)
        if (
            path.is_symlink()
            or not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1
        ):
            raise ContractError("recovery journal file shape changed")
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            current = os.fstat(descriptor)
            if (
                current.st_dev != info.st_dev
                or current.st_ino != info.st_ino
                or not stat.S_ISREG(current.st_mode)
                or stat.S_IMODE(current.st_mode) != 0o600
                or current.st_nlink != 1
                or current.st_size != info.st_size
                or current.st_size <= 0
                or current.st_size > JOURNAL_MAX_BYTES
            ):
                raise ContractError("recovery journal identity changed while opening")
            payload = b""
            while len(payload) <= JOURNAL_MAX_BYTES:
                chunk = os.read(
                    descriptor,
                    min(1024 * 1024, JOURNAL_MAX_BYTES + 1 - len(payload)),
                )
                if not chunk:
                    break
                payload += chunk
        finally:
            os.close(descriptor)
        if len(payload) != info.st_size or len(payload) > JOURNAL_MAX_BYTES:
            raise ContractError("recovery journal bytes changed while reading")
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ContractError("recovery journal is not exact JSON") from exc
        if (
            not isinstance(value, dict)
            or value.get("schema") != SCHEMA
            or value.get("sequence") != index
            or value.get("action") != JOURNAL_ACTIONS[index]
        ):
            raise ContractError("recovery journal changed")
        records.append(value)
    return records


def _validate_recovery_records(
    directory: Path,
    records: list[dict[str, Any]],
    intent_sha256: str,
    closure: dict[str, Any],
) -> dict[str, Any] | None:
    if not records:
        return None
    open_record = records[0]
    expected = _expected_enable(intent_sha256)
    preserved = open_record.get("preserved_enable")
    approval_binding = open_record.get("approval_binding")
    opening_status = open_record.get("opening_status")
    if (
        set(open_record)
        != {
            "schema",
            "sequence",
            "action",
            "manifest_sha256",
            "install_result_sha256",
            "predecessor_execution_closure_sha256",
            "recovery_execution_closure_sha256",
            "incident_transaction_dir",
            "intent_sha256",
            "approval_binding",
            "approval_binding_sha256",
            "opening_status_record",
            "opening_status",
            "opening_health",
            "enable_capture_record",
            "preserved_enable",
            "action_budget",
            "reboot_count",
            "payload_transfer_count",
            "partition_write_count",
            "userdata_write_count",
        }
        or open_record.get("manifest_sha256") != MANIFEST_SHA256
        or open_record.get("install_result_sha256") != INSTALL_RESULT_SHA256
        or open_record.get("predecessor_execution_closure_sha256")
        != PREDECESSOR_EXECUTION_SHA256
        or open_record.get("recovery_execution_closure_sha256") != closure["sha256"]
        or open_record.get("incident_transaction_dir") != str(EXPECTED_INCIDENT_DIR)
        or open_record.get("intent_sha256") != intent_sha256
        or not isinstance(approval_binding, dict)
        or open_record.get("approval_binding_sha256")
        != f1.json_sha256(approval_binding)
        or not isinstance(open_record.get("opening_status_record"), dict)
        or not isinstance(opening_status, dict)
        or opening_status.get("binding") != 1
        or opening_status.get("enable") != 1
        or opening_status.get("latch") != 0
        or not isinstance(open_record.get("opening_health"), dict)
        or not isinstance(open_record.get("enable_capture_record"), dict)
        or open_record.get("action_budget") != 1
        or open_record.get("reboot_count") != 0
        or open_record.get("payload_transfer_count") != 0
        or open_record.get("partition_write_count") != 0
        or open_record.get("userdata_write_count") != 0
        or not isinstance(preserved, dict)
    ):
        raise ContractError("recovery open record changed")
    created = f1.parse_utc(approval_binding.get("created_utc"), "recovery open created")
    expires = f1.parse_utc(approval_binding.get("expires_utc"), "recovery open expires")
    if (
        expires - created != dt.timedelta(seconds=APPROVAL_TTL_SEC)
        or approval_binding
        != _approval_binding(
            intent_sha256,
            closure,
            created_utc=created.strftime("%Y-%m-%dT%H:%M:%SZ"),
            expires_utc=expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
    ):
        raise ContractError("recovery open approval binding changed")
    preserved = _validate_preserved(directory, preserved, expected)
    if len(records) >= 2:
        intent = records[1]
        script = _cleanup_script(preserved["sha256"], preserved["size"])
        if (
            set(intent)
            != {
                "schema",
                "sequence",
                "action",
                "intent_sha256",
                "selected_path",
                "selected_size",
                "selected_sha256",
                "cleanup_script_sha256",
                "unlink_dispatch_count_max",
                "unlink_replay",
            }
            or intent.get("intent_sha256") != intent_sha256
            or intent.get("selected_path") != ENABLE_PATH
            or intent.get("selected_size") != preserved["size"]
            or intent.get("selected_sha256") != preserved["sha256"]
            or intent.get("cleanup_script_sha256")
            != hashlib.sha256(script.encode("utf-8")).hexdigest()
            or intent.get("unlink_dispatch_count_max") != 1
            or intent.get("unlink_replay") is not False
        ):
            raise ContractError("recovery unlink intent changed")
    if len(records) >= 3:
        command_result = records[2].get("command_result")
        if (
            set(records[2])
            != {
                "schema",
                "sequence",
                "action",
                "intent_sha256",
                "unlink_dispatch_count",
                "unlink_dispatch_count_max",
                "unlink_dispatch_count_exact",
                "unlink_replay",
                "command_result",
            }
            or records[2].get("intent_sha256") != intent_sha256
            or records[2].get("unlink_dispatch_count") not in (None, 1)
            or records[2].get("unlink_dispatch_count_max") != 1
            or type(records[2].get("unlink_dispatch_count_exact")) is not bool
            or records[2].get("unlink_dispatch_count_exact")
            != (records[2].get("unlink_dispatch_count") == 1)
            or records[2].get("unlink_replay") is not False
            or not isinstance(command_result, dict)
        ):
            raise ContractError("recovery unlink result changed")
    if len(records) >= 4:
        result = records[3].get("result")
        final_status = result.get("auto_handoff_status") if isinstance(result, dict) else None
        if (
            set(records[3])
            != {"schema", "sequence", "action", "result_sha256", "result"}
            or not isinstance(result, dict)
            or records[3].get("result_sha256") != f1.json_sha256(result)
            or result.get("schema") != RESULT_SCHEMA
            or result.get("terminal") != "PASS_H15_ARMED_STATE_RECOVERED"
            or result.get("intent_sha256") != intent_sha256
            or result.get("resident_healthy") is not True
            or result.get("unlink_replay") is not False
            or result.get("selected_path") != ENABLE_PATH
            or result.get("latch_path_untouched") != LATCH_PATH
            or result.get("preserved_enable") != preserved
            or not isinstance(final_status, dict)
            or final_status.get("binding") != 1
            or final_status.get("enable") != 0
            or final_status.get("latch") != 0
            or result.get("unlink_dispatch_count") not in (None, 1)
            or result.get("unlink_dispatch_count_max") != 1
            or type(result.get("unlink_dispatch_count_exact")) is not bool
            or result.get("unlink_dispatch_count_exact")
            != (result.get("unlink_dispatch_count") == 1)
            or result.get("payload_transfer_count") != 0
            or result.get("partition_write_count") != 0
            or result.get("flash_count") != 0
            or result.get("userdata_write_count") != 0
        ):
            raise ContractError("recovery final-health record changed")
    if len(records) >= 5 and records[4] != {
        "schema": SCHEMA,
        "sequence": 4,
        "action": "closed",
        "result_sha256": records[3]["result_sha256"],
        "result": records[3]["result"],
    }:
        raise ContractError("recovery closed record changed")
    return preserved


def _status_and_health(spec: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    effect_args = _effect_args()
    status_record = base.run_f1_cmd(effect_args, ["auto-handoff-status"])
    status = d1.parse_status(status_record)
    health = base.verify_candidate_health(spec, effect_args)
    return status_record, status, health


def _run_cleanup_once(effect_args: argparse.Namespace, script: str) -> dict[str, Any]:
    command = ["run", "/bin/busybox", "sh", "-c", script]
    return transport.run_cmd(
        effect_args.bridge_host,
        effect_args.bridge_port,
        effect_args.remote_timeout,
        command,
        retry_unsafe=False,
        input_mode=base.F1_SERIAL_INPUT_MODE,
        input_char_delay_sec=base.F1_SERIAL_INPUT_CHAR_DELAY_SEC,
        allow_error=False,
    )


def _close_from_absence(
    directory: Path,
    spec: Any,
    intent_sha256: str,
    preserved: dict[str, Any],
    *,
    command_result: dict[str, Any],
    unlink_dispatch_count: int | None,
) -> dict[str, Any]:
    status_record, status, health = _status_and_health(spec)
    preserved = _validate_preserved(
        directory,
        preserved,
        _expected_enable(intent_sha256),
    )
    if (status.get("enable"), status.get("latch")) != (0, 0):
        return {
            "schema": RESULT_SCHEMA,
            "terminal": "RECOVERY_PENDING_ARMED_NO_REPLAY",
            "intent_sha256": intent_sha256,
            "candidate_replay": False,
            "unlink_replay": False,
            "status": status,
            "command_result": command_result,
            "resident_health": health,
            "auto_handoff_status_record": status_record,
        }
    result = {
        "schema": RESULT_SCHEMA,
        "terminal": "PASS_H15_ARMED_STATE_RECOVERED",
        "intent_sha256": intent_sha256,
        "resident_healthy": True,
        "candidate_replay": False,
        "arm_replay": False,
        "reboot_replay": False,
        "handoff_replay": False,
        "unlink_dispatch_count": unlink_dispatch_count,
        "unlink_dispatch_count_max": 1,
        "unlink_dispatch_count_exact": unlink_dispatch_count is not None,
        "unlink_replay": False,
        "payload_transfer_count": 0,
        "partition_write_count": 0,
        "flash_count": 0,
        "userdata_write_count": 0,
        "selected_path": ENABLE_PATH,
        "latch_path_untouched": LATCH_PATH,
        "preserved_enable": preserved,
        "auto_handoff_status": status,
        "auto_handoff_status_record": status_record,
        "native_health": health,
        "command_result": command_result,
    }
    result_sha = f1.json_sha256(result)
    _write_record(directory, 3, "final-health", {"result_sha256": result_sha, "result": result})
    _write_record(directory, 4, "closed", {"result_sha256": result_sha, "result": result})
    return result


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if args.operator_attended is not True:
        raise ContractError("armed recovery is attended-only")
    _, spec, intent_sha256, closure = _load_inputs(args)
    lexical_directory = args.recovery_transaction_dir.absolute()
    if lexical_directory != EXPECTED_RECOVERY_DIR:
        raise ContractError("recovery transaction directory path changed")
    if os.path.lexists(lexical_directory):
        directory = _recovery_dir(args, absent=False)
        existing_records = _read_records(directory)
        if len(existing_records) not in (0, 1):
            raise ContractError(
                "execute continuation is limited to a pre-intent journal prefix"
            )
    else:
        directory = _recovery_dir(args, absent=True)
        existing_records = []
    approval = _validate_approval(args, intent_sha256, closure)
    status_record, status, health = _status_and_health(spec)
    if (status.get("enable"), status.get("latch")) != (1, 0):
        raise ContractError("recovery opening state is not exact 1,0")
    expected = _expected_enable(intent_sha256)
    capture_record, body = _read_enable(_effect_args(), expected)
    if existing_records:
        preserved = _validate_recovery_records(
            directory,
            existing_records,
            intent_sha256,
            closure,
        )
        assert preserved is not None
        if (
            existing_records[0].get("approval_binding_sha256")
            != approval["approval_binding_sha256"]
        ):
            raise ContractError("pre-intent continuation approval changed")
    else:
        if not directory.exists():
            directory.mkdir(parents=True, mode=0o700)
            os.chmod(directory, 0o700)
        preserve_path = directory / "enable-before.bin"
        if os.path.lexists(preserve_path):
            preserved = {
                "path": str(preserve_path),
                "size": len(expected),
                "sha256": hashlib.sha256(expected).hexdigest(),
                "mode": 0o600,
            }
            preserved = _validate_preserved(directory, preserved, expected)
        else:
            preserved = _write_preserved(preserve_path, body)
            preserved = _validate_preserved(directory, preserved, expected)
        _write_record(
            directory,
            0,
            "open-exact-armed-recovery",
            {
                "manifest_sha256": MANIFEST_SHA256,
                "install_result_sha256": INSTALL_RESULT_SHA256,
                "predecessor_execution_closure_sha256": PREDECESSOR_EXECUTION_SHA256,
                "recovery_execution_closure_sha256": closure["sha256"],
                "incident_transaction_dir": str(EXPECTED_INCIDENT_DIR),
                "intent_sha256": intent_sha256,
                "approval_binding": approval["approval_binding"],
                "approval_binding_sha256": approval["approval_binding_sha256"],
                "opening_status_record": status_record,
                "opening_status": status,
                "opening_health": health,
                "enable_capture_record": capture_record,
                "preserved_enable": preserved,
                "action_budget": 1,
                "reboot_count": 0,
                "payload_transfer_count": 0,
                "partition_write_count": 0,
                "userdata_write_count": 0,
            },
        )
    script = _cleanup_script(preserved["sha256"], preserved["size"])
    _write_record(
        directory,
        1,
        "unlink-intent",
        {
            "intent_sha256": intent_sha256,
            "selected_path": ENABLE_PATH,
            "selected_size": preserved["size"],
            "selected_sha256": preserved["sha256"],
            "cleanup_script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
            "unlink_dispatch_count_max": 1,
            "unlink_replay": False,
        },
    )
    command_result: dict[str, Any] = {"response_proof": False}
    try:
        record = _run_cleanup_once(_effect_args(), script)
        marker = (
            "A90H15_ARMED_RECOVERY removed=1 synced=1 "
            "enable=absent latch=untouched"
        )
        if str(record.get("text") or "").count(marker) != 1:
            raise ContractError("recovery completion marker is not exact")
        command_result = {"response_proof": True, "record": record}
    except Exception as exc:
        command_result = {
            "response_proof": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
    _write_record(
        directory,
        2,
        "unlink-result",
        {
            "intent_sha256": intent_sha256,
            "unlink_dispatch_count": 1,
            "unlink_dispatch_count_max": 1,
            "unlink_dispatch_count_exact": True,
            "unlink_replay": False,
            "command_result": command_result,
        },
    )
    return _close_from_absence(
        directory,
        spec,
        intent_sha256,
        preserved,
        command_result=command_result,
        unlink_dispatch_count=1,
    )


def reconcile(args: argparse.Namespace) -> dict[str, Any]:
    if args.operator_attended is not True or args.approval is not None:
        raise ContractError("armed recovery reconciliation is attended and approval-free")
    _, spec, intent_sha256, closure = _load_inputs(args)
    directory = _recovery_dir(args, absent=False)
    records = _read_records(directory)
    if len(records) == 0:
        return {
            "schema": RESULT_SCHEMA,
            "terminal": "PRE_OPEN_READY_FOR_EXECUTE_CONTINUATION",
            "records_present": 0,
            "unlink_replay": False,
            "device_contact": True,
            "device_effect": False,
            "device_write": False,
        }
    preserved = _validate_recovery_records(
        directory,
        records,
        intent_sha256,
        closure,
    )
    assert preserved is not None
    if len(records) == 5:
        return records[4]["result"]
    if len(records) == 1:
        return {
            "schema": RESULT_SCHEMA,
            "terminal": "PRE_INTENT_READY_FOR_EXECUTE_CONTINUATION",
            "records_present": 1,
            "intent_sha256": intent_sha256,
            "preserved_enable": preserved,
            "unlink_replay": False,
            "device_contact": True,
            "device_effect": False,
            "device_write": False,
        }
    if len(records) == 4:
        _write_record(
            directory,
            4,
            "closed",
            {
                "result_sha256": records[3]["result_sha256"],
                "result": records[3]["result"],
            },
        )
        return records[3]["result"]
    if len(records) not in (2, 3):
        raise ContractError("recovery reconcile prefix is not supported")
    if len(records) == 2:
        status_record, status, health = _status_and_health(spec)
        if (status.get("enable"), status.get("latch")) != (0, 0):
            return {
                "schema": RESULT_SCHEMA,
                "terminal": "RECOVERY_PENDING_UNLINK_DISPATCH_UNKNOWN_NO_REPLAY",
                "records_present": 2,
                "intent_sha256": intent_sha256,
                "unlink_dispatch_count": None,
                "unlink_dispatch_count_max": 1,
                "unlink_replay": False,
                "auto_handoff_status": status,
                "auto_handoff_status_record": status_record,
                "resident_health": health,
            }
        command_result = {
            "response_proof": False,
            "reconciled_after_intent_only": True,
            "unlink_dispatch_count_unknown": True,
        }
        _write_record(
            directory,
            2,
            "unlink-result",
            {
                "intent_sha256": intent_sha256,
                "unlink_dispatch_count": None,
                "unlink_dispatch_count_max": 1,
                "unlink_dispatch_count_exact": False,
                "unlink_replay": False,
                "command_result": command_result,
            },
        )
        return _close_from_absence(
            directory,
            spec,
            intent_sha256,
            preserved,
            command_result=command_result,
            unlink_dispatch_count=None,
        )
    return _close_from_absence(
        directory,
        spec,
        intent_sha256,
        preserved,
        command_result=records[2].get("command_result", {}),
        unlink_dispatch_count=records[2].get("unlink_dispatch_count"),
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--manifest", type=Path, required=True)
    result.add_argument("--expect-manifest-sha256", required=True)
    result.add_argument("--install-result", type=Path, required=True)
    result.add_argument("--expect-install-result-sha256", required=True)
    result.add_argument("--expect-predecessor-execution-closure-sha256", required=True)
    result.add_argument("--expect-recovery-execution-closure-sha256", required=True)
    result.add_argument("--incident-transaction-dir", type=Path, required=True)
    result.add_argument("--recovery-transaction-dir", type=Path, required=True)
    modes = result.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare-approval", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--reconcile", action="store_true")
    result.add_argument("--operator-attended", action="store_true")
    result.add_argument("--approval")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.prepare_approval:
            if args.approval is not None or args.operator_attended:
                raise ContractError(
                    "approval preparation accepts no live authority inputs"
                )
            value = prepare_approval(args)
        elif args.execute:
            value = execute(args)
        else:
            value = reconcile(args)
    except (ContractError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"H15_ARMED_RECOVERY_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
