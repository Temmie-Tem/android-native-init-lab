#!/usr/bin/env python3
"""Dormant durable evidence owner for the future S20+ N3-U0 attended F1."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import stat
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "s20plus_g986n_n3u0_attended_f1_evidence_h0_v1"
STATUS = "H0_DURABLE_EVIDENCE_PASS_GO_NOT_ACTIVE"
EVIDENCE_ACTIVE = False
EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "459c579cbefcb7916ccce7a00c595a772f3c0b23f679016a98be49ec85af9dbb"
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_RAW_BYTES = 8 * 1024 * 1024
MAX_COMMAND_ITEMS = 64
MAX_COMMAND_TEXT = 4096

JOURNAL_RUNS_ROOT = ROOT / "workspace/private/runs/s20plus-n3u0-attended-f1"
EVIDENCE_ROOT = ROOT / "workspace/private/runs/s20plus-n3u0-attended-f1-evidence"
JOURNAL_BINDING_SHA256 = (
    "4695acca5c8d618eee7e16aaf665cbf66235a5a76aadc0a4322f490113cc2945"
)
BACKEND_BINDING_SHA256 = (
    "5561aabc35f20752702b8ef12ec6f8d4669bbef8b022ff5557c7925c34b9704b"
)
INTEGRATION_BINDING_SHA256 = (
    "2a037eb3cab5f068b0d534d034fcadce51b26c3ee9f5874ec583b90905a6d6a6"
)

SOURCES = {
    "journal": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/s20plus_n3u0_attended_f1.py",
        "size": 55_803,
        "sha256": "2c4d7335211ade6c25540782148f44c309da6373d8ad495a5904d43714a01e86",
    },
    "backend": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_attended_f1_backend_h0.py",
        "size": 30_896,
        "sha256": "0d8a752e94ea34f5130a53fe2747c7e949561db54ba661d55c4af2db0a19e27b",
    },
    "integration": {
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_n3u0_attended_f1_integration_h0.py",
        "size": 18_516,
        "sha256": "4b5234f818306ffc8d361ee8b14b15c74702b23b05f752c5acef5171071bc3a0",
    },
}

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

OPERATIONS = {
    "initial-download-reboot": "initial-download-intent.json",
    "initial-download-observation": "initial-download-intent.json",
    "candidate-transfer": "candidate-intent.json",
    "candidate-observation": "candidate-intent.json",
    "rollback-download-reboot": "rollback-mode-intent.json",
    "rollback-download-observation": "rollback-mode-intent.json",
    "physical-download-entry": "physical-rollback-intent.json",
    "physical-download-observation": "physical-rollback-intent.json",
    "rollback-transfer": "rollback-intent.json",
    "final-resident-health": "rollback-result.json",
}

RUN_ID_RE = re.compile(r"[0-9a-f]{32}")
FILE_RE = re.compile(
    r"(initial-download-reboot|initial-download-observation|candidate-transfer|"
    r"candidate-observation|rollback-download-reboot|rollback-download-observation|"
    r"physical-download-entry|physical-download-observation|rollback-transfer|"
    r"final-resident-health)-([0-9]{2})\.(stdout|stderr|result\.json)"
)
HEX64_RE = re.compile(r"[0-9a-f]{64}")
AT_EMPTY_PATH = 0x1000
_LIBC = ctypes.CDLL(None, use_errno=True)
_LINKAT = _LIBC.linkat
_LINKAT.argtypes = (
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
)
_LINKAT.restype = ctypes.c_int


class EvidenceError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EvidenceError("evidence value is not canonical JSON") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _read_source(expected: dict[str, Any], label: str) -> bytes:
    path = expected["path"]
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise EvidenceError(f"{label} is unavailable") from exc
    try:
        metadata = os.fstat(descriptor)
        size = expected["size"]
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or type(size) is not int
            or not 0 < size <= MAX_SOURCE_BYTES
            or metadata.st_size != size
        ):
            raise EvidenceError(f"{label} identity differs")
        payload = bytearray()
        while len(payload) < size:
            chunk = os.read(descriptor, min(1024 * 1024, size - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != size or os.read(descriptor, 1):
            raise EvidenceError(f"{label} length differs")
    finally:
        os.close(descriptor)
    result = bytes(payload)
    if hashlib.sha256(result).hexdigest() != expected["sha256"]:
        raise EvidenceError(f"{label} hash differs")
    return result


def _load_journal() -> Any:
    expected = SOURCES["journal"]
    payload = _read_source(expected, "N3-U0 evidence journal")
    module = types.ModuleType("s20plus_n3u0_evidence_journal_bound")
    module.__file__ = str(expected["path"])
    exec(compile(payload, str(expected["path"]), "exec"), module.__dict__)
    if module.binding_sha256() != JOURNAL_BINDING_SHA256:
        raise EvidenceError("journal binding differs")
    if module.F1_ACTIVE is not False:
        raise EvidenceError("journal unexpectedly exposes authority")
    return module


def source_receipts() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, expected in SOURCES.items():
        _read_source(expected, f"N3-U0 evidence {name}")
        result[name] = {
            "path": str(expected["path"]),
            "size": expected["size"],
            "sha256": expected["sha256"],
        }
    return result


def self_receipt() -> dict[str, Any]:
    path = Path(__file__).resolve()
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise EvidenceError("evidence owner is unavailable") from exc
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or not 0 < metadata.st_size <= MAX_SOURCE_BYTES
        ):
            raise EvidenceError("evidence owner identity differs")
        data = bytearray()
        while len(data) < metadata.st_size:
            chunk = os.read(
                descriptor, min(1024 * 1024, metadata.st_size - len(data))
            )
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != metadata.st_size or os.read(descriptor, 1):
            raise EvidenceError("evidence owner length differs")
    finally:
        os.close(descriptor)
    payload = bytes(data)
    normalized = re.sub(
        rb'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "[0-9a-f]{64}"',
        b'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        payload,
        count=1,
    )
    normalized_sha256 = hashlib.sha256(normalized).hexdigest()
    if normalized_sha256 != EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256:
        raise EvidenceError("evidence owner normalized identity differs")
    return {
        "path": str(path),
        "size": len(payload),
        "normalized_sha256": normalized_sha256,
    }


def current_binding() -> dict[str, Any]:
    _load_journal()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "runner": self_receipt(),
        "journal_binding_sha256": JOURNAL_BINDING_SHA256,
        "backend_binding_sha256": BACKEND_BINDING_SHA256,
        "integration_binding_sha256": INTEGRATION_BINDING_SHA256,
        "sources": source_receipts(),
        "operations": dict(OPERATIONS),
        "publication": "atomic-no-replace-file-fsync-directory-fsync",
    }


def binding_sha256() -> str:
    return digest(current_binding())


def require_active() -> None:
    if EVIDENCE_ACTIVE is not True:
        raise EvidenceError("N3-U0 evidence owner is not active")


def _require_directory(
    path: Path, label: str, *, mode: int = 0o700
) -> os.stat_result:
    require_active()
    if path != EVIDENCE_ROOT and not (
        path.parent == EVIDENCE_ROOT and RUN_ID_RE.fullmatch(path.name) is not None
    ):
        raise EvidenceError(f"{label} path is outside the fixed evidence root")
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise EvidenceError(f"{label} is unavailable") from exc
    if (
        path.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != mode
    ):
        raise EvidenceError(f"{label} is not an exact direct directory")
    return metadata


def _fsync_dir(path: Path) -> None:
    require_active()
    if path != EVIDENCE_ROOT and not (
        path.parent == EVIDENCE_ROOT and RUN_ID_RE.fullmatch(path.name) is not None
    ):
        raise EvidenceError("fsync path is outside the fixed evidence root")
    descriptor = os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_evidence_run(run_id: str) -> Path:
    require_active()
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        raise EvidenceError("evidence run ID is malformed")
    _require_directory(EVIDENCE_ROOT, "N3-U0 evidence root")
    path = EVIDENCE_ROOT / run_id
    if not os.path.lexists(path):
        path.mkdir(mode=0o700)
        path.chmod(0o700)
        _fsync_dir(EVIDENCE_ROOT)
    _require_evidence_run_directory(run_id)
    return path


def _require_evidence_run_directory(run_id: str) -> tuple[Path, os.stat_result]:
    require_active()
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        raise EvidenceError("evidence run ID is malformed")
    root_metadata = _require_directory(EVIDENCE_ROOT, "N3-U0 evidence root")
    path = EVIDENCE_ROOT / run_id
    run_metadata = _require_directory(path, "N3-U0 evidence run")
    if (run_metadata.st_uid, run_metadata.st_gid) != (
        root_metadata.st_uid,
        root_metadata.st_gid,
    ):
        raise EvidenceError("N3-U0 evidence run owner differs")
    return path, run_metadata


def _require_evidence_file_path(path: Path) -> None:
    require_active()
    if (
        path.parent.parent != EVIDENCE_ROOT
        or RUN_ID_RE.fullmatch(path.parent.name) is None
        or FILE_RE.fullmatch(path.name) is None
    ):
        raise EvidenceError("evidence file path is outside the fixed namespace")


def _durable_blob(path: Path, payload: bytes) -> None:
    require_active()
    _require_evidence_file_path(path)
    if len(payload) > MAX_RAW_BYTES:
        raise EvidenceError("evidence payload is oversized")
    _require_evidence_run_directory(path.parent.name)
    parent = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    descriptor = -1
    try:
        descriptor = os.open(
            ".", os.O_WRONLY | os.O_TMPFILE | os.O_CLOEXEC, 0o400, dir_fd=parent
        )
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise EvidenceError("short evidence write")
            offset += written
        os.fsync(descriptor)
        if _LINKAT(descriptor, b"", parent, os.fsencode(path.name), AT_EMPTY_PATH) != 0:
            number = ctypes.get_errno()
            raise OSError(number, os.strerror(number), path)
        os.fsync(parent)
    finally:
        try:
            if descriptor >= 0:
                os.close(descriptor)
        finally:
            os.close(parent)


def _read_blob(path: Path, label: str) -> bytes:
    require_active()
    _require_evidence_file_path(path)
    _parent, parent_metadata = _require_evidence_run_directory(path.parent.name)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise EvidenceError(f"{label} is missing or indirect") from exc
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_uid != parent_metadata.st_uid
            or metadata.st_gid != parent_metadata.st_gid
            or metadata.st_size > MAX_RAW_BYTES
        ):
            raise EvidenceError(f"{label} is not an exact bounded regular file")
        payload = bytearray()
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > MAX_RAW_BYTES:
                raise EvidenceError(f"{label} is oversized")
    finally:
        os.close(descriptor)
    return bytes(payload)


def _read_json(path: Path, label: str) -> Any:
    payload = _read_blob(path, label)
    try:
        value = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
        if payload != canonical_bytes(value):
            raise ValueError("noncanonical evidence JSON")
        return value
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} is malformed") from exc


def _run_context(run_dir: Path, operation: str) -> tuple[Any, dict[str, Any], Any]:
    if operation not in OPERATIONS:
        raise EvidenceError("unknown evidence operation")
    if run_dir.parent != JOURNAL_RUNS_ROOT or RUN_ID_RE.fullmatch(run_dir.name) is None:
        raise EvidenceError("evidence run path is not fixed")
    journal = _load_journal()
    prepared = journal.validate_legal_prefix(run_dir)
    prerequisite = run_dir / OPERATIONS[operation]
    if not os.path.lexists(prerequisite):
        raise EvidenceError("evidence operation lacks its durable predecessor")
    record = journal.read_exact_json(prerequisite, f"{operation} predecessor")
    return journal, prepared, record


def _command_digest(argv: Any) -> str:
    if (
        not isinstance(argv, list)
        or not 1 <= len(argv) <= MAX_COMMAND_ITEMS
        or any(
            not isinstance(item, str)
            or not 0 < len(item) <= MAX_COMMAND_TEXT
            or "\x00" in item
            or "\n" in item
            or "\r" in item
            for item in argv
        )
    ):
        raise EvidenceError("command shape is malformed")
    return digest(argv)


def publish_command_result(
    run_dir: Path,
    operation: str,
    ordinal: int,
    argv: list[str],
    timeout_seconds: int,
    output_limit: int,
    returncode: int,
    stdout: bytes,
    stderr: bytes,
) -> dict[str, Any]:
    require_active()
    evidence_binding = binding_sha256()
    journal, prepared, predecessor = _run_context(run_dir, operation)
    if (
        type(ordinal) is not int
        or not 1 <= ordinal <= 99
        or type(timeout_seconds) is not int
        or not 1 <= timeout_seconds <= 900
        or type(output_limit) is not int
        or not 1 <= output_limit <= MAX_RAW_BYTES
        or type(returncode) is not int
        or not isinstance(stdout, bytes)
        or not isinstance(stderr, bytes)
        or len(stdout) > output_limit
        or len(stderr) > output_limit
        or len(stdout) + len(stderr) > MAX_RAW_BYTES
    ):
        raise EvidenceError("command result is malformed or oversized")
    command_sha256 = _command_digest(argv)
    evidence_run = _ensure_evidence_run(prepared["run_id"])
    stem = f"{operation}-{ordinal:02d}"
    stdout_path = evidence_run / f"{stem}.stdout"
    stderr_path = evidence_run / f"{stem}.stderr"
    result_path = evidence_run / f"{stem}.result.json"
    if any(os.path.lexists(path) for path in (stdout_path, stderr_path, result_path)):
        raise EvidenceError("command evidence already exists; replay is forbidden")
    raw_receipt = {
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "stdout_size": len(stdout),
        "stderr_size": len(stderr),
    }
    journal.validate_raw_receipt(raw_receipt, f"{operation} evidence raw")
    value = {
        "schema": "s20plus_g986n_n3u0_command_evidence_v1",
        "run_id": prepared["run_id"],
        "journal_binding_sha256": prepared["binding_sha256"],
        "evidence_binding_sha256": evidence_binding,
        "operation": operation,
        "ordinal": ordinal,
        "predecessor_sha256": digest(predecessor),
        "command_sha256": command_sha256,
        "timeout_seconds": timeout_seconds,
        "output_limit": output_limit,
        "returncode": returncode,
        "raw_receipt": raw_receipt,
        "replay_permitted": False,
    }
    _durable_blob(stdout_path, stdout)
    _durable_blob(stderr_path, stderr)
    _durable_blob(result_path, canonical_bytes(value))
    return value


def _evidence_names(run_id: str) -> set[str]:
    require_active()
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        raise EvidenceError("evidence run ID is malformed")
    path = EVIDENCE_ROOT / run_id
    if not os.path.lexists(path):
        return set()
    path, run_metadata = _require_evidence_run_directory(run_id)
    names: set[str] = set()
    for child in path.iterdir():
        if FILE_RE.fullmatch(child.name) is None:
            raise EvidenceError("evidence run contains an unknown node")
        metadata = child.lstat()
        if (
            child.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_uid != run_metadata.st_uid
            or metadata.st_gid != run_metadata.st_gid
            or metadata.st_size > MAX_RAW_BYTES
        ):
            raise EvidenceError("evidence run contains an indirect node")
        names.add(child.name)
    return names


def inspect_operation(run_dir: Path, operation: str, ordinal: int) -> dict[str, Any]:
    require_active()
    evidence_binding = binding_sha256()
    journal, prepared, predecessor = _run_context(run_dir, operation)
    if type(ordinal) is not int or not 1 <= ordinal <= 99:
        raise EvidenceError("evidence ordinal is malformed")
    names = _evidence_names(prepared["run_id"])
    stem = f"{operation}-{ordinal:02d}"
    expected = {
        f"{stem}.stdout",
        f"{stem}.stderr",
        f"{stem}.result.json",
    }
    present = names & expected
    if not present:
        return {
            "state": "intent-consumed-evidence-absent",
            "operation": operation,
            "ordinal": ordinal,
            "replay_permitted": False,
        }
    if present not in ({f"{stem}.stdout"}, {f"{stem}.stdout", f"{stem}.stderr"}, expected):
        raise EvidenceError("command evidence publication order is impossible")
    if present != expected:
        return {
            "state": "uncertain-consumed",
            "operation": operation,
            "ordinal": ordinal,
            "published": sorted(present),
            "replay_permitted": False,
        }
    path = EVIDENCE_ROOT / prepared["run_id"]
    stdout = _read_blob(path / f"{stem}.stdout", f"{operation} stdout")
    stderr = _read_blob(path / f"{stem}.stderr", f"{operation} stderr")
    result = _read_json(path / f"{stem}.result.json", f"{operation} result")
    keys = {
        "schema",
        "run_id",
        "journal_binding_sha256",
        "evidence_binding_sha256",
        "operation",
        "ordinal",
        "predecessor_sha256",
        "command_sha256",
        "timeout_seconds",
        "output_limit",
        "returncode",
        "raw_receipt",
        "replay_permitted",
    }
    if (
        not isinstance(result, dict)
        or set(result) != keys
        or result.get("schema") != "s20plus_g986n_n3u0_command_evidence_v1"
        or result.get("run_id") != prepared["run_id"]
        or result.get("journal_binding_sha256") != prepared["binding_sha256"]
        or result.get("evidence_binding_sha256") != evidence_binding
        or result.get("operation") != operation
        or type(result.get("ordinal")) is not int
        or result["ordinal"] != ordinal
        or result.get("predecessor_sha256") != digest(predecessor)
        or not isinstance(result.get("command_sha256"), str)
        or HEX64_RE.fullmatch(result["command_sha256"]) is None
        or type(result.get("timeout_seconds")) is not int
        or not 1 <= result["timeout_seconds"] <= 900
        or type(result.get("output_limit")) is not int
        or not 1 <= result["output_limit"] <= MAX_RAW_BYTES
        or type(result.get("returncode")) is not int
        or result.get("replay_permitted") is not False
    ):
        raise EvidenceError("command evidence result is malformed")
    raw = journal.validate_raw_receipt(result.get("raw_receipt"), f"{operation} raw")
    if (
        raw["stdout_size"] != len(stdout)
        or raw["stderr_size"] != len(stderr)
        or raw["stdout_sha256"] != hashlib.sha256(stdout).hexdigest()
        or raw["stderr_sha256"] != hashlib.sha256(stderr).hexdigest()
    ):
        raise EvidenceError("command evidence raw bytes differ")
    return {
        "state": "complete",
        "operation": operation,
        "ordinal": ordinal,
        "result": result,
        "replay_permitted": False,
    }


def read_complete_operation(
    run_dir: Path, operation: str, ordinal: int
) -> dict[str, Any]:
    require_active()
    inspection = inspect_operation(run_dir, operation, ordinal)
    if inspection.get("state") != "complete":
        raise EvidenceError("command evidence is not complete")
    prepared = _load_journal().validate_legal_prefix(run_dir)
    stem = f"{operation}-{ordinal:02d}"
    evidence_run = EVIDENCE_ROOT / prepared["run_id"]
    return {
        "inspection": inspection,
        "stdout": _read_blob(evidence_run / f"{stem}.stdout", f"{operation} stdout"),
        "stderr": _read_blob(evidence_run / f"{stem}.stderr", f"{operation} stderr"),
    }


def render_plan() -> dict[str, Any]:
    binding = current_binding()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": EVIDENCE_ACTIVE,
        "live_authority": False,
        "binding_sha256": digest(binding),
        "binding": binding,
        "cli": ["--render-plan"],
        "device_commands": [],
        "partition_transfers": [],
        "backend_exposed": False,
        "raw_evidence_durable": True,
        "integrated_live_consumer": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-plan", action="store_true")
    arguments = parser.parse_args()
    if not arguments.render_plan:
        parser.error("only --render-plan is available")
    print(json.dumps(render_plan(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
