#!/usr/bin/env python3
"""Durable global no-replay registry for the reusable Process-v2 F1 runner.

The registry is deliberately a small host-side authority.  Its location is
fixed below ``workspace/private``; callers can provide a repository root, but
cannot provide a registry path.  Candidate claims are keyed by the verified
target profile and candidate AP digest, never by a run directory alone.

This module does not contact a device and does not grant live authority.  A
claim is the durable candidate-consumption boundary; physical-target
serialization is a separate nonblocking session flock.  Only an exact,
independently classified ``odin_local_parse_failure`` with no device session
may append a release.  Every other interruption leaves the claim active for
recovery-only handling.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import tarfile
from typing import Any, Iterator, Mapping


REGISTRY_SCHEMA = "device_action_f1_consumed_candidate_registry_v1"
HEAD_SCHEMA = "device_action_f1_consumed_candidate_registry_head_v1"
RECORD_SCHEMA = "device_action_f1_consumed_candidate_record_v1"
IDENTITY_SCHEMA = "device_action_f1_verified_candidate_identity_v1"
QUALIFICATION_SCHEMA = "device_action_f1_consumed_candidate_registry_qualification_v1"
REPO_ROOT = Path(__file__).resolve().parents[5]
LEGACY_AUTHORITY_PATH = Path(__file__).resolve().with_name(
    "device_action_f1_legacy_consumed_candidate_authority_v1.json"
)
LEGACY_AUTHORITY_SHA256 = "db6bd3f0218e5e53b20bec18a6a747414477134ec5008af20c15ae098c88ca7a"
REGISTRY_DIR_NAME = "consumed-candidate-registry-v1"
HEAD_NAME = "head.json"
LOCK_NAME = "writer.lock"
SESSION_LOCK_NAME = "target-session.lock"
RECORDS_NAME = "records"
ACTIVATION_NAME = "activation.json"
ACTIVATION_SCHEMA = "device_action_f1_consumed_candidate_registry_activation_v1"
MAX_RECORDS = 4096
MAX_RECORD_BYTES = 64 * 1024
MAX_HEAD_BYTES = 16 * 1024
MAX_LOCK_BYTES = 256
LOCK_PAYLOAD = b"device-action-f1-consumed-candidate-registry-v1\n"
SESSION_LOCK_PAYLOAD = b"device-action-f1-target-session-lease-v1\n"
ZERO_SHA256 = "0" * 64
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,95}\Z")
HEAD_TEMP_RE = re.compile(r"\.head\.json\.next-[0-9]+-[0-9]+\Z")


class RegistryError(RuntimeError):
    """Malformed, replaced, unavailable, or otherwise unsafe registry."""


class DuplicateCandidateClaim(RegistryError):
    """The exact candidate identity is already actively claimed."""


class RegistryUnavailable(RegistryError):
    """The fixed authority is absent or cannot be safely opened."""


def _canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise RegistryError("registry value is not canonical JSON") from exc


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identity(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": _sha(data)}


def _strict_int(value: Any) -> bool:
    return type(value) is int


def _fixed_root(repo_root: Path) -> Path:
    root = Path(repo_root).resolve()
    private = root / "workspace/private"
    if private.is_symlink() or not private.is_dir() or private.resolve() != private:
        raise RegistryUnavailable("workspace/private is unavailable or indirect")
    path = private / REGISTRY_DIR_NAME
    if path.is_symlink():
        raise RegistryUnavailable("global registry is an indirect path")
    return path


def registry_root(repo_root: Path) -> Path:
    """Return the fixed registry path; no caller-supplied path is accepted."""

    return _fixed_root(repo_root)


def _direct_dir(path: Path, label: str, *, mode: int | None = None) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise RegistryUnavailable(f"{label} is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RegistryError(f"{label} is not a direct directory")
    if info.st_nlink < 2:
        raise RegistryError(f"{label} has an invalid link count")
    if mode is not None and stat.S_IMODE(info.st_mode) != mode:
        raise RegistryError(f"{label} mode differs")


def _read_regular(
    path: Path, label: str, *, mode: int | None = None, maximum: int
) -> bytes:
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise RegistryError(f"{label} is not a direct regular file")
        if before.st_nlink != 1:
            raise RegistryError(f"{label} link count differs")
        if mode is not None and stat.S_IMODE(before.st_mode) != mode:
            raise RegistryError(f"{label} mode differs")
        if before.st_size > maximum:
            raise RegistryError(f"{label} exceeds its size bound")
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            inside_before = os.fstat(fd)
            data = b""
            while True:
                chunk = os.read(fd, min(1024 * 1024, maximum + 1 - len(data)))
                if not chunk:
                    break
                data += chunk
                if len(data) > maximum:
                    raise RegistryError(f"{label} exceeds its size bound")
            inside_after = os.fstat(fd)
        finally:
            os.close(fd)
        after = path.lstat()
    except OSError as exc:
        raise RegistryUnavailable(f"{label} cannot be read") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    inside_before_id = (
        inside_before.st_dev,
        inside_before.st_ino,
        inside_before.st_size,
        inside_before.st_mtime_ns,
    )
    inside_after_id = (
        inside_after.st_dev,
        inside_after.st_ino,
        inside_after.st_size,
        inside_after.st_mtime_ns,
    )
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_id != inside_before_id or inside_before_id != inside_after_id or inside_after_id != after_id:
        raise RegistryError(f"{label} changed while reading")
    return data


def _read_legacy_private_regular(root: Path, path: Path, label: str, maximum: int) -> bytes:
    private_root = (root / "workspace/private").resolve(strict=True)
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(private_root) or path != resolved:
        raise RegistryError(f"{label} escaped private repository evidence")
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode) or not 1 <= before.st_nlink <= 2:
            raise RegistryError(f"{label} is not a bounded direct regular file")
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            inside_before = os.fstat(fd)
            data = bytearray()
            while chunk := os.read(fd, min(1024 * 1024, maximum + 1 - len(data))):
                data.extend(chunk)
                if len(data) > maximum:
                    raise RegistryError(f"{label} exceeds its size bound")
            inside_after = os.fstat(fd)
        finally:
            os.close(fd)
        after = path.lstat()
    except OSError as exc:
        raise RegistryUnavailable(f"{label} cannot be read") from exc
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_nlink)
    if identity(before) != identity(inside_before) or identity(inside_before) != identity(inside_after) or identity(inside_after) != identity(after):
        raise RegistryError(f"{label} changed while reading")
    return bytes(data)


def _parse_json(data: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise RegistryError(f"{label} has duplicate JSON key")
            value[key] = item
        return value

    def constant(value: str) -> Any:
        raise RegistryError(f"{label} has non-finite JSON constant {value}")

    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict) or data != _canonical(value):
        raise RegistryError(f"{label} is not canonical JSON")
    return value


def _legacy_authority() -> list[dict[str, Any]]:
    try:
        data = LEGACY_AUTHORITY_PATH.read_bytes()
    except OSError as exc:
        raise RegistryUnavailable("legacy activation authority is unavailable") from exc
    if _sha(data) != LEGACY_AUTHORITY_SHA256:
        raise RegistryError("legacy activation authority bytes differ")
    value = _parse_json(data, "legacy activation authority")
    if value.get("schema") != "device_action_f1_legacy_consumed_candidate_authority_v1" or value.get("count") != len(value.get("entries", [])):
        raise RegistryError("legacy activation authority schema differs")
    entries = value["entries"]
    if len({item.get("candidate_ap_sha256") for item in entries}) != len(entries):
        raise RegistryError("legacy activation authority is not unique")
    return entries


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise RegistryUnavailable(f"cannot fsync {path}") from exc


def _lock_path_identity(path: Path) -> dict[str, int]:
    try:
        info = path.lstat()
    except OSError as exc:
        raise RegistryUnavailable("registry lock identity is unavailable") from exc
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise RegistryError("registry lock identity is malformed")
    return {
        "st_dev": info.st_dev,
        "st_ino": info.st_ino,
        "st_size": info.st_size,
        "mode": stat.S_IMODE(info.st_mode),
        "nlink": info.st_nlink,
    }


def _write_no_replace(path: Path, data: bytes, *, mode: int) -> dict[str, Any]:
    if path.exists() or path.is_symlink():
        raise RegistryError(f"refusing to clobber {path.name}")
    try:
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            mode,
        )
        try:
            offset = 0
            while offset < len(data):
                count = os.write(fd, data[offset:])
                if count <= 0:
                    raise RegistryUnavailable("registry write did not progress")
                offset += count
            os.fchmod(fd, mode)
            os.fsync(fd)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != mode or info.st_size != len(data):
                raise RegistryError("published registry file metadata differs")
        finally:
            os.close(fd)
    except FileExistsError as exc:
        raise RegistryError(f"refusing to clobber {path.name}") from exc
    except OSError as exc:
        raise RegistryUnavailable(f"cannot publish {path.name}") from exc
    _fsync_dir(path.parent)
    reopened = _read_regular(path, f"published {path.name}", mode=mode, maximum=max(len(data), 1))
    if reopened != data:
        raise RegistryError(f"published {path.name} changed after reopen")
    return _identity(data)


def _write_head(path: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    # The head is replaceable state, but only while holding the fixed writer
    # lease.  Its contents are independently checked against every record.
    data = _canonical(dict(value))
    if len(data) > MAX_HEAD_BYTES:
        raise RegistryError("registry head exceeds its bound")
    temporary = path.with_name(f".{path.name}.next-{os.getpid()}-{id(value)}")
    if temporary.exists() or temporary.is_symlink():
        raise RegistryError("head staging path already exists")
    _write_no_replace(temporary, data, mode=0o400)
    try:
        os.replace(temporary, path)
        _fsync_dir(path.parent)
    except OSError as exc:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise RegistryUnavailable("cannot publish registry head") from exc
    reopened = _read_regular(path, "registry head", mode=0o400, maximum=MAX_HEAD_BYTES)
    if reopened != data:
        raise RegistryError("registry head changed after publication")
    return _identity(data)


def _paths(repo_root: Path) -> tuple[Path, Path, Path, Path]:
    root = _fixed_root(repo_root)
    return root, root / RECORDS_NAME, root / HEAD_NAME, root / LOCK_NAME


def _head_temp_paths(root: Path) -> list[Path]:
    try:
        return sorted(
            item for item in root.iterdir() if HEAD_TEMP_RE.fullmatch(item.name)
        )
    except OSError as exc:
        raise RegistryUnavailable("registry head namespace cannot be enumerated") from exc


def _validate_lock(path: Path, expected_payload: bytes = LOCK_PAYLOAD) -> None:
    data = _read_regular(path, "registry writer lock", mode=0o600, maximum=MAX_LOCK_BYTES)
    if data != expected_payload:
        raise RegistryError("registry writer lock identity differs")


def _validate_layout(repo_root: Path) -> tuple[Path, Path, Path, Path]:
    root, records, head, lock = _paths(repo_root)
    _direct_dir(root, "registry root", mode=0o700)
    _direct_dir(records, "registry records", mode=0o700)
    try:
        root_children = {item.name for item in root.iterdir()}
        record_children = {item.name for item in records.iterdir()}
    except OSError as exc:
        raise RegistryUnavailable("registry namespace cannot be enumerated") from exc
    temp_children = {item.name for item in _head_temp_paths(root)}
    base_children = root_children - temp_children
    if base_children != {RECORDS_NAME, HEAD_NAME, LOCK_NAME, SESSION_LOCK_NAME, ACTIVATION_NAME}:
        raise RegistryError("registry root contains an unexpected child")
    if len(temp_children) > 1:
        raise RegistryError("registry head has multiple staging files")
    for name in record_children:
        if re.fullmatch(r"[0-9]{8}-(?:claim|release)\.json", name) is None:
            raise RegistryError("registry records contains an unexpected child")
    _validate_lock(lock)
    _validate_lock(root / SESSION_LOCK_NAME, SESSION_LOCK_PAYLOAD)
    activation_data = _read_regular(root / ACTIVATION_NAME, "registry activation", mode=0o400, maximum=MAX_RECORD_BYTES)
    activation = _parse_json(activation_data, "registry activation")
    if set(activation) != {"schema", "legacy_candidates", "activation_boundary", "writer_lock_identity", "session_lock_identity"} or activation.get("schema") != ACTIVATION_SCHEMA or activation.get("activation_boundary") != "legacy-candidates-before-global-registry-v1" or not isinstance(activation.get("legacy_candidates"), list):
        raise RegistryError("registry activation identity differs")
    lock_paths = {
        "writer_lock_identity": lock,
        "session_lock_identity": root / SESSION_LOCK_NAME,
    }
    lock_fields = {"st_dev", "st_ino", "st_size", "mode", "nlink"}
    expected_locks: dict[str, dict[str, int]] = {}
    current_locks: dict[str, dict[str, int]] = {}
    for key, path in lock_paths.items():
        expected_identity = activation.get(key)
        if not isinstance(expected_identity, dict) or set(expected_identity) != lock_fields:
            raise RegistryError("registry activation lock identity differs")
        expected_locks[key] = expected_identity
        current_locks[key] = _lock_path_identity(path)
    if expected_locks != current_locks:
        stable_fields = lock_fields - {"st_dev"}
        synchronized_device_renumber = (
            len({value["st_dev"] for value in expected_locks.values()}) == 1
            and len({value["st_dev"] for value in current_locks.values()}) == 1
            and all(
                expected_locks[key][field] == current_locks[key][field]
                for key in lock_paths
                for field in stable_fields
            )
        )
        if not synchronized_device_renumber:
            raise RegistryError("registry lock was replaced after activation")
    for item in activation["legacy_candidates"]:
        if not isinstance(item, dict) or set(item) != {"candidate_ap_size", "candidate_ap_sha256", "boot_member_name", "boot_member_size", "boot_member_sha256", "source_result"} or not _strict_int(item.get("candidate_ap_size")) or not _strict_int(item.get("boot_member_size")) or not SHA256_RE.fullmatch(str(item.get("candidate_ap_sha256"))) or not SHA256_RE.fullmatch(str(item.get("boot_member_sha256"))) or item.get("boot_member_name") != "boot.img.lz4" or not isinstance(item.get("source_result"), dict) or set(item["source_result"]) != {"path", "size", "sha256"}:
            raise RegistryError("registry legacy activation entry differs")
    if Path(repo_root).resolve() == REPO_ROOT and activation["legacy_candidates"] != _legacy_authority():
        raise RegistryError("registry activation does not match pinned legacy authority")
    return root, records, head, lock


def initialize(repo_root: Path) -> dict[str, Any]:
    """Create the fixed empty authority, or validate an existing one."""

    root = _fixed_root(repo_root)
    private = root.parent
    if root.exists() or root.is_symlink():
        _validate_layout(repo_root)
        return validate(repo_root)
    try:
        root.mkdir(mode=0o700)
        records = root / RECORDS_NAME
        records.mkdir(mode=0o700)
        _write_no_replace(root / LOCK_NAME, LOCK_PAYLOAD, mode=0o600)
        _write_no_replace(root / SESSION_LOCK_NAME, SESSION_LOCK_PAYLOAD, mode=0o600)
        head = _head_value(0, -1, ZERO_SHA256)
        _write_no_replace(root / HEAD_NAME, _canonical(head), mode=0o400)
        legacy_entries = _legacy_candidate_entries(repo_root)
        if Path(repo_root).resolve() == REPO_ROOT:
            if legacy_entries != _legacy_authority():
                raise RegistryError("legacy candidate census differs from pinned authority")
            legacy_entries = _legacy_authority()
        activation = {
            "schema": ACTIVATION_SCHEMA,
            "activation_boundary": "legacy-candidates-before-global-registry-v1",
            "legacy_candidates": legacy_entries,
            "writer_lock_identity": _lock_path_identity(root / LOCK_NAME),
            "session_lock_identity": _lock_path_identity(root / SESSION_LOCK_NAME),
        }
        _write_no_replace(root / ACTIVATION_NAME, _canonical(activation), mode=0o400)
        _fsync_dir(root)
        _fsync_dir(private)
    except FileExistsError as exc:
        raise RegistryError("registry appeared during initialization") from exc
    return validate(repo_root)


def _head_value(record_count: int, last_sequence: int, last_record_sha256: str) -> dict[str, Any]:
    body = {
        "schema": HEAD_SCHEMA,
        "record_count": record_count,
        "last_sequence": last_sequence,
        "last_record_sha256": last_record_sha256,
    }
    body["head_sha256"] = _sha(_canonical(body))
    return body


def _legacy_candidate_entries(repo_root: Path) -> list[dict[str, Any]]:
    """Bind already-transferred APs at the activation boundary.

    This is intentionally a one-time deny list: the append-only registry
    begins empty, but a later run cannot silently replay a historical AP.
    """

    root = Path(repo_root).resolve()
    run_root = root / "workspace/private/runs/device-action-f1-live-v2"
    found: dict[str, dict[str, Any]] = {}
    if not run_root.is_dir() or run_root.is_symlink():
        return []
    run_dirs = [path for path in sorted(run_root.iterdir()) if path.is_dir() and not path.is_symlink()]
    for run_dir in run_dirs:
        start_path = run_dir / "candidate-attempt-01.start.json"
        result_path = run_dir / "candidate-attempt-01.result.json"
        live_path = run_dir / "live-result.json"
        prepared_path = run_dir / "prepared.json"
        attempt_two = list(run_dir.glob("candidate-attempt-02.*"))
        if not start_path.exists() and not result_path.exists():
            continue
        if any(path.is_symlink() or not path.is_file() for path in (start_path, result_path, live_path, prepared_path)) or attempt_two:
            raise RegistryError("legacy candidate run evidence is incomplete")
        try:
            start = json.loads(start_path.read_text(encoding="utf-8"))
            result = json.loads(result_path.read_text(encoding="utf-8"))
            live = json.loads(live_path.read_text(encoding="utf-8"))
            prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RegistryError("legacy candidate run evidence cannot be parsed") from exc
        if (
            start.get("schema") != "device_action_f1_transfer_attempt_start_v2"
            or start.get("kind") != "candidate"
            or start.get("attempt") != 1
            or start.get("prefix") != "candidate-attempt-01"
            or result.get("schema") != "device_action_f1_transfer_receipt_v2"
            or result.get("kind") != "candidate"
            or result.get("attempt") != 1
            or result.get("prefix") != "candidate-attempt-01"
            or result.get("classification") != "odin_transfer_completed"
            or live.get("current_state") != "CLOSED"
            or live.get("live_state", {}).get("candidate_completed") is not True
            or prepared.get("approval_binding_sha256") != start.get("approval_binding_sha256")
            or live.get("approval_binding_sha256") != start.get("approval_binding_sha256")
        ):
            raise RegistryError("legacy candidate run terminal evidence differs")
        transport = result.get("transport")
        ap = transport.get("ap") if isinstance(transport, dict) else None
        if not isinstance(ap, dict) or not isinstance(ap.get("path"), str) or not isinstance(ap.get("size"), int) or not SHA256_RE.fullmatch(str(ap.get("sha256"))):
            raise RegistryError("legacy candidate AP receipt is malformed")
        ap_path = Path(ap["path"])
        try:
            ap_data = _read_legacy_private_regular(
                root, ap_path, "legacy AP", 256 * 1024 * 1024
            )
            if len(ap_data) != ap["size"] or _sha(ap_data) != ap["sha256"]:
                raise RegistryError("legacy AP identity differs")
            with tarfile.open(fileobj=io.BytesIO(ap_data), mode="r:") as archive:
                members = archive.getmembers()
                boot_members = [item for item in members if item.name == "boot.img.lz4" and item.isreg()]
                if len(members) != 1 or len(boot_members) != 1:
                    raise RegistryError("legacy AP boot member is not unique")
                frame = archive.extractfile(boot_members[0]).read()
        except (OSError, tarfile.TarError, KeyError, TypeError, ValueError, RegistryError) as exc:
            raise RegistryError("legacy consumed candidate cannot be rebound") from exc
        result_data = _read_legacy_private_regular(
            root, result_path, "legacy result", MAX_RECORD_BYTES
        )
        try:
            source_result_path = result_path.resolve().relative_to(root).as_posix()
        except ValueError as exc:
            raise RegistryError("legacy result escaped repository root") from exc
        candidate_entry = {
            "candidate_ap_size": len(ap_data),
            "candidate_ap_sha256": ap["sha256"],
            "boot_member_name": "boot.img.lz4",
            "boot_member_size": len(frame),
            "boot_member_sha256": _sha(frame),
            "source_result": {
                "path": source_result_path,
                "size": len(result_data),
                "sha256": _sha(result_data),
            },
        }
        previous = found.get(ap["sha256"])
        if previous is not None and previous != candidate_entry:
            raise RegistryError("legacy candidate digest is not uniquely bound")
        found[ap["sha256"]] = candidate_entry
    if len(found) != len([path for path in run_dirs if (path / "candidate-attempt-01.start.json").exists()]):
        raise RegistryError("legacy candidate AP identities are not unique")
    return [found[key] for key in sorted(found)]


def _legacy_candidate_digests(repo_root: Path) -> list[str]:
    return [item["candidate_ap_sha256"] for item in _legacy_candidate_entries(repo_root)]


def _validate_head(value: Mapping[str, Any]) -> None:
    expected_keys = {"schema", "record_count", "last_sequence", "last_record_sha256", "head_sha256"}
    if set(value) != expected_keys or value.get("schema") != HEAD_SCHEMA:
        raise RegistryError("registry head schema differs")
    if not _strict_int(value.get("record_count")) or not 0 <= value["record_count"] <= MAX_RECORDS:
        raise RegistryError("registry head record count differs")
    if not _strict_int(value.get("last_sequence")) or value["last_sequence"] != value["record_count"] - 1:
        raise RegistryError("registry head sequence differs")
    if not isinstance(value.get("last_record_sha256"), str) or not SHA256_RE.fullmatch(value["last_record_sha256"]):
        raise RegistryError("registry head record digest differs")
    if not isinstance(value.get("head_sha256"), str) or not SHA256_RE.fullmatch(value["head_sha256"]):
        raise RegistryError("registry head digest is malformed")
    body = dict(value)
    digest = body.pop("head_sha256")
    if digest != _sha(_canonical(body)):
        raise RegistryError("registry head digest does not verify")
    if value["record_count"] == 0 and value["last_record_sha256"] != ZERO_SHA256:
        raise RegistryError("empty registry head has a nonempty digest")


def _record_digest(value: Mapping[str, Any]) -> str:
    body = dict(value)
    body.pop("record_sha256", None)
    return _sha(_canonical(body))


def _claim_id(candidate_key: str, run_id: str, approval_binding_sha256: str, sequence: int) -> str:
    return _sha(_canonical({
        "candidate_key": candidate_key,
        "run_id": run_id,
        "approval_binding_sha256": approval_binding_sha256,
        "sequence": sequence,
    }))


def _candidate_key_from_identity(value: Mapping[str, Any]) -> str:
    return _sha(_canonical({
        "schema": IDENTITY_SCHEMA,
        "target_key": value["target_key"],
        "candidate_ap_sha256": value["candidate_ap_sha256"],
        "candidate_ap_size": value["candidate_ap_size"],
        "boot_member_name": value["boot_member_name"],
        "boot_member_size": value["boot_member_size"],
        "boot_member_sha256": value["boot_member_sha256"],
        "allowed_member": "boot.img.lz4",
    }))


def _validate_identity_fields(value: Mapping[str, Any]) -> None:
    for key in ("candidate_key", "target_profile_sha256", "target_key", "candidate_ap_sha256", "approval_binding_sha256", "claim_id", "previous_record_sha256", "boot_member_sha256"):
        if not isinstance(value.get(key), str) or not SHA256_RE.fullmatch(value[key]):
            raise RegistryError(f"registry {key} is malformed")
    for key in ("manifest_id", "run_id", "boot_member_name"):
        if not isinstance(value.get(key), str) or not ID_RE.fullmatch(value[key]):
            raise RegistryError(f"registry {key} is malformed")
    if value.get("boot_member_name") != "boot.img.lz4":
        raise RegistryError("registry boot member differs")
    for key in ("candidate_ap_size", "boot_member_size"):
        if not _strict_int(value.get(key)) or value[key] <= 0 or value[key] > 256 * 1024 * 1024:
            raise RegistryError(f"registry {key} is malformed")


def _validate_record(value: Mapping[str, Any], *, sequence: int, previous: str) -> None:
    expected = {
        "schema", "sequence", "event", "candidate_key", "target_profile_sha256",
        "candidate_ap_sha256", "candidate_ap_size", "boot_member_name", "boot_member_size", "boot_member_sha256", "manifest_id", "run_id", "approval_binding_sha256", "target_key",
        "claim_id", "previous_record_sha256", "release_reason", "device_session_started",
        "partition_transfer", "record_sha256",
    }
    if set(value) != expected or value.get("schema") != RECORD_SCHEMA:
        raise RegistryError("registry record schema differs")
    if not _strict_int(value.get("sequence")) or value["sequence"] != sequence:
        raise RegistryError("registry record sequence differs")
    if value.get("event") not in {"claim", "release"}:
        raise RegistryError("registry record event differs")
    _validate_identity_fields(value)
    if value["candidate_key"] != _candidate_key_from_identity(value):
        raise RegistryError("registry record candidate key derivation differs")
    if value.get("previous_record_sha256") != previous:
        raise RegistryError("registry record chain predecessor differs")
    if value.get("event") == "claim":
        if value.get("release_reason") is not None or value.get("device_session_started") is not None or value.get("partition_transfer") is not None:
            raise RegistryError("claim record contains release fields")
    elif value.get("event") == "release":
        if value.get("release_reason") != "odin_local_parse_failure" or value.get("device_session_started") is not False or value.get("partition_transfer") is not False:
            raise RegistryError("release record is not the exact pre-session exception")
    else:
        if value.get("release_reason") != "odin_local_parse_failure" or value.get("device_session_started") is not False or value.get("partition_transfer") is not False:
            raise RegistryError("release record is not the exact pre-session exception")
    if value.get("record_sha256") != _record_digest(value):
        raise RegistryError("registry record digest differs")


def _record_paths(records: Path) -> list[Path]:
    paths = sorted(records.glob("[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-*.json"))
    if len(paths) > MAX_RECORDS:
        raise RegistryError("registry record count exceeds its bound")
    return paths


def _scan(repo_root: Path, *, repair_tail: bool = False) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    root, records_dir, head_path, _lock = _validate_layout(repo_root)
    data = _read_regular(head_path, "registry head", mode=0o400, maximum=MAX_HEAD_BYTES)
    head = _parse_json(data, "registry head")
    _validate_head(head)
    paths = _record_paths(records_dir)
    records: list[dict[str, Any]] = []
    previous = ZERO_SHA256
    active: dict[str, dict[str, Any]] = {}
    for sequence, path in enumerate(paths):
        payload = _read_regular(path, f"registry record {sequence}", mode=0o400, maximum=MAX_RECORD_BYTES)
        value = _parse_json(payload, f"registry record {sequence}")
        if path.name != f"{sequence:08d}-{value.get('event')}.json":
            raise RegistryError("registry record filename sequence/event differs")
        _validate_record(value, sequence=sequence, previous=previous)
        candidate_key = value["candidate_key"]
        if value["event"] == "claim":
            if candidate_key in active:
                raise RegistryError("candidate has multiple active claims")
            if value["claim_id"] != _claim_id(
                candidate_key,
                value["run_id"],
                value["approval_binding_sha256"],
                sequence,
            ):
                raise RegistryError("claim identifier derivation differs")
            active[candidate_key] = value
        else:
            prior = active.get(candidate_key)
            if prior is None:
                raise RegistryError("release has no active claim")
            for key in (
                "target_profile_sha256", "target_key", "candidate_ap_sha256",
                "candidate_ap_size", "boot_member_name", "boot_member_size",
                "boot_member_sha256", "manifest_id", "run_id",
                "approval_binding_sha256", "claim_id",
            ):
                if value.get(key) != prior.get(key):
                    raise RegistryError("release does not bind its active claim")
            del active[candidate_key]
        previous = value["record_sha256"]
        records.append(value)
    if head["record_count"] != len(records) or head["last_sequence"] != len(records) - 1 or head["last_record_sha256"] != (previous if records else ZERO_SHA256):
        expected = head["record_count"]
        if repair_tail and len(records) == expected + 1 and expected <= MAX_RECORDS:
            prefix = records[expected - 1]["record_sha256"] if expected else ZERO_SHA256
            tail = records[-1]
            if head["last_sequence"] == expected - 1 and head["last_record_sha256"] == prefix and tail["sequence"] == expected and tail["previous_record_sha256"] == prefix:
                head = _head_value(len(records), len(records) - 1, tail["record_sha256"])
                _write_head(head_path, head)
            else:
                raise RegistryError("registry head has an invalid tail")
        else:
            raise RegistryError("registry head does not match records")
    return head, records, {"path": str(root), "record_count": len(records), "last_record_sha256": previous if records else ZERO_SHA256}


@contextlib.contextmanager
def _writer(repo_root: Path) -> Iterator[None]:
    root, records, head, lock = _validate_layout(repo_root)
    fd: int | None = None
    try:
        fd = os.open(lock, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
        opened = os.fstat(fd)
        _validate_layout(repo_root)
        fcntl.flock(fd, fcntl.LOCK_EX)
    except BaseException as exc:
        if fd is not None:
            os.close(fd)
        if isinstance(exc, RegistryError):
            raise
        raise RegistryUnavailable("cannot acquire registry writer lease") from exc
    try:
        _assert_lock_identity(lock, fd, opened)
        temporary = _head_temp_paths(root)
        if len(temporary) > 1:
            raise RegistryError("registry head has multiple staging files")
        if temporary:
            if temporary[0].is_symlink() or not temporary[0].is_file() or temporary[0].stat().st_nlink != 1:
                raise RegistryError("registry head staging file is unsafe")
            temporary[0].unlink()
            _fsync_dir(root)
        _scan(repo_root, repair_tail=True)
        yield
    finally:
        try:
            _assert_lock_identity(lock, fd, opened)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


@contextlib.contextmanager
def _reader(repo_root: Path) -> Iterator[None]:
    _validate_layout(repo_root)
    if _head_temp_paths(_fixed_root(repo_root)):
        raise RegistryError("registry head staging file requires writer recovery")
    lock = _fixed_root(repo_root) / LOCK_NAME
    fd: int | None = None
    try:
        fd = os.open(lock, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        opened = os.fstat(fd)
        _validate_layout(repo_root)
        fcntl.flock(fd, fcntl.LOCK_SH)
    except BaseException as exc:
        if fd is not None:
            os.close(fd)
        if isinstance(exc, RegistryError):
            raise
        raise RegistryUnavailable("cannot acquire registry reader lease") from exc
    try:
        _assert_lock_identity(lock, fd, opened)
        _scan(repo_root)
        yield
    finally:
        try:
            _assert_lock_identity(lock, fd, opened)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _assert_lock_identity(
    path: Path, fd: int, opened: os.stat_result, expected_payload: bytes = LOCK_PAYLOAD
) -> None:
    try:
        current = os.fstat(fd)
        path_info = path.lstat()
        payload = os.pread(fd, len(expected_payload), 0)
    except OSError as exc:
        raise RegistryUnavailable("registry writer lock changed") from exc
    if (
        not stat.S_ISREG(current.st_mode)
        or current.st_nlink != 1
        or stat.S_IMODE(current.st_mode) != 0o600
        or (current.st_dev, current.st_ino, current.st_size)
        != (opened.st_dev, opened.st_ino, opened.st_size)
        or (path_info.st_dev, path_info.st_ino, path_info.st_size)
        != (opened.st_dev, opened.st_ino, opened.st_size)
        or path_info.st_nlink != 1
        or stat.S_IMODE(path_info.st_mode) != 0o600
        or payload != expected_payload
    ):
        raise RegistryError("registry writer lock identity changed")


@contextlib.contextmanager
def target_session_lease(repo_root: Path) -> Iterator[None]:
    """Hold the fixed target-session flock across recheck and Download use."""

    _validate_layout(repo_root)
    path = _fixed_root(repo_root) / SESSION_LOCK_NAME
    fd: int | None = None
    try:
        fd = os.open(path, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
        opened = os.fstat(fd)
        _validate_layout(repo_root)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _assert_lock_identity(path, fd, opened, SESSION_LOCK_PAYLOAD)
    except BaseException as exc:
        if fd is not None:
            os.close(fd)
        if isinstance(exc, RegistryError):
            raise
        raise RegistryUnavailable("cannot acquire target-session lease") from exc
    try:
        yield
    finally:
        try:
            _assert_lock_identity(path, fd, opened, SESSION_LOCK_PAYLOAD)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def validate(repo_root: Path) -> dict[str, Any]:
    with _reader(repo_root):
        head, records, details = _scan(repo_root)
    return {
        "schema": REGISTRY_SCHEMA,
        "scope": "global",
        "record_count": len(records),
        "head": head,
        "head_sha256": _sha(_canonical(head)),
        "last_record_sha256": details["last_record_sha256"],
        "replay_forbidden": True,
        "append_only": True,
        "hash_chained": True,
        "single_writer_flock": True,
        "restart_durable": True,
        "no_caller_supplied_path": True,
        "root": REGISTRY_DIR_NAME,
    }


def history(repo_root: Path) -> list[dict[str, Any]]:
    with _reader(repo_root):
        return list(_scan(repo_root)[1])


def _claims(records: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    active: dict[str, Mapping[str, Any]] = {}
    for record in records:
        key = str(record["candidate_key"])
        if record["event"] == "claim":
            active[key] = record
        elif record["event"] == "release":
            active.pop(key, None)
    return active


def active_claim(repo_root: Path, candidate_key: str) -> dict[str, Any] | None:
    if not isinstance(candidate_key, str) or not SHA256_RE.fullmatch(candidate_key):
        raise RegistryError("candidate key is malformed")
    with _reader(repo_root):
        record = _claims(_scan(repo_root)[1]).get(candidate_key)
    return dict(record) if record is not None else None


def preflight_candidate(repo_root: Path, identity: Mapping[str, Any]) -> None:
    """Fail closed before Download if the verified AP is already consumed.

    Physical target serialization is provided by ``target_session_lease``;
    this registry deliberately records only the candidate consumption boundary.
    """

    identity_value = _validate_identity(identity)
    with _writer(repo_root):
        _head, records, _details = _scan(repo_root)
        activation = _parse_json(
            _read_regular(
                registry_root(repo_root) / ACTIVATION_NAME,
                "registry activation",
                mode=0o400,
                maximum=MAX_RECORD_BYTES,
            ),
            "registry activation",
        )
        if any(
            item["candidate_ap_sha256"] == identity_value["candidate_ap_sha256"]
            for item in activation["legacy_candidates"]
        ):
            raise DuplicateCandidateClaim(
                "candidate AP was consumed before global registry activation"
            )
        if _claims(records).get(identity_value["candidate_key"]) is not None:
            raise DuplicateCandidateClaim("candidate identity was already consumed")


def _append(repo_root: Path, record: dict[str, Any]) -> dict[str, Any]:
    root, records_dir, head_path, _lock = _validate_layout(repo_root)
    head, records, _details = _scan(repo_root)
    sequence = len(records)
    if sequence >= MAX_RECORDS:
        raise RegistryError("registry record count bound exceeded")
    record["sequence"] = sequence
    record["previous_record_sha256"] = records[-1]["record_sha256"] if records else ZERO_SHA256
    record["record_sha256"] = _record_digest(record)
    _validate_record(record, sequence=sequence, previous=record["previous_record_sha256"])
    filename = records_dir / f"{sequence:08d}-{record['event']}.json"
    payload = _canonical(record)
    if len(payload) > MAX_RECORD_BYTES:
        raise RegistryError("registry record exceeds its size bound")
    receipt = _write_no_replace(filename, payload, mode=0o400)
    new_head = _head_value(sequence + 1, sequence, record["record_sha256"])
    _write_head(head_path, new_head)
    _fsync_dir(records_dir)
    _fsync_dir(root)
    # Reopen the whole chain after publication.  A bad head or replaced record
    # is therefore rejected before the caller can invoke a backend.
    _scan(repo_root)
    return {"record": dict(record), "record_receipt": receipt, "head": new_head}


def _validate_identity(identity: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "schema", "candidate_key", "target_profile_sha256", "target_key", "candidate_ap_sha256",
        "candidate_ap_size", "boot_member_name", "boot_member_size", "boot_member_sha256",
        "manifest_id", "run_id", "approval_binding_sha256",
    }
    if set(identity) != expected or identity.get("schema") != IDENTITY_SCHEMA:
        raise RegistryError("verified candidate identity schema differs")
    _validate_identity_fields({**identity, "claim_id": ZERO_SHA256, "previous_record_sha256": ZERO_SHA256})
    if identity["candidate_key"] != _candidate_key_from_identity(identity):
        raise RegistryError("verified candidate key derivation differs")
    return dict(identity)


def derive_candidate_identity(
    profile: Mapping[str, Any],
    manifest: Mapping[str, Any],
    candidate_ap_sha256: str,
    *,
    approval_binding_sha256: str,
    candidate_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive a key only from verified profile/manifest identity and AP bytes."""

    if not isinstance(profile, Mapping) or not isinstance(manifest, Mapping):
        raise RegistryError("verified profile/manifest are not objects")
    if not SHA256_RE.fullmatch(str(candidate_ap_sha256)) or not SHA256_RE.fullmatch(str(approval_binding_sha256)):
        raise RegistryError("verified candidate digest is malformed")
    candidate = manifest.get("candidate_ap")
    if not isinstance(candidate, Mapping) or candidate.get("sha256") != candidate_ap_sha256:
        raise RegistryError("candidate AP digest was not verified against manifest")
    if manifest.get("allowed_member") != "boot.img.lz4":
        raise RegistryError("candidate AP member is outside the boot-only contract")
    if not isinstance(candidate_receipt, Mapping):
        raise RegistryError("verified candidate AP receipt is required")
    member = candidate_receipt.get("member")
    if not isinstance(member, Mapping) or set(member) != {"name", "size", "sha256"}:
        raise RegistryError("verified candidate AP member receipt is malformed")
    if member.get("name") != "boot.img.lz4" or not _strict_int(member.get("size")) or not isinstance(member.get("sha256"), str) or not SHA256_RE.fullmatch(member["sha256"]):
        raise RegistryError("verified candidate AP member identity differs")
    if candidate_receipt.get("size") != candidate.get("size") or candidate_receipt.get("sha256") != candidate_ap_sha256:
        raise RegistryError("verified candidate AP receipt differs from manifest")
    if not _strict_int(candidate_receipt.get("size")) or candidate_receipt["size"] <= 0:
        raise RegistryError("verified candidate AP size is malformed")
    manifest_id = manifest.get("manifest_id")
    run_id = manifest.get("run_id")
    if not isinstance(manifest_id, str) or not ID_RE.fullmatch(manifest_id) or not isinstance(run_id, str) or not ID_RE.fullmatch(run_id):
        raise RegistryError("manifest identity is malformed")
    profile_sha = _sha(_canonical(dict(profile)))
    target = profile.get("target")
    if not isinstance(target, Mapping):
        raise RegistryError("physical target identity is not bound")
    physical_target = {
        "model": target.get("model"),
        "device": target.get("device"),
    }
    if any(not isinstance(value, str) or not value for value in physical_target.values()):
        raise RegistryError("physical target identity is malformed")
    target_key = _sha(_canonical(physical_target))
    key_body = {
        "schema": IDENTITY_SCHEMA,
        "target_key": target_key,
        "candidate_ap_sha256": candidate_ap_sha256,
        "candidate_ap_size": candidate_receipt["size"],
        "boot_member_name": member["name"],
        "boot_member_size": member["size"],
        "boot_member_sha256": member["sha256"],
        "allowed_member": "boot.img.lz4",
    }
    identity = {
        "schema": IDENTITY_SCHEMA,
        "candidate_key": _sha(_canonical(key_body)),
        "target_profile_sha256": profile_sha,
        "target_key": target_key,
        "candidate_ap_sha256": candidate_ap_sha256,
        "candidate_ap_size": candidate_receipt["size"],
        "boot_member_name": member["name"],
        "boot_member_size": member["size"],
        "boot_member_sha256": member["sha256"],
        "manifest_id": manifest_id,
        "run_id": run_id,
        "approval_binding_sha256": approval_binding_sha256,
    }
    return _validate_identity(identity)


def claim(repo_root: Path, identity: Mapping[str, Any]) -> dict[str, Any]:
    identity_value = _validate_identity(identity)
    with _writer(repo_root):
        head, records, _details = _scan(repo_root)
        activation = _parse_json(
            _read_regular(
                registry_root(repo_root) / ACTIVATION_NAME,
                "registry activation",
                mode=0o400,
                maximum=MAX_RECORD_BYTES,
            ),
            "registry activation",
        )
        if any(
            item["candidate_ap_sha256"] == identity_value["candidate_ap_sha256"]
            for item in activation["legacy_candidates"]
        ):
            raise DuplicateCandidateClaim(
                "candidate AP was consumed before global registry activation"
            )
        existing = _claims(records).get(identity_value["candidate_key"])
        if existing is not None:
            raise DuplicateCandidateClaim("candidate identity is already globally claimed")
        claim_id = _claim_id(
            identity_value["candidate_key"],
            identity_value["run_id"],
            identity_value["approval_binding_sha256"],
            len(records),
        )
        record = {
            "sequence": len(records),
            "event": "claim",
            **{key: value for key, value in identity_value.items() if key != "schema"},
            "schema": RECORD_SCHEMA,
            "claim_id": claim_id,
            "previous_record_sha256": ZERO_SHA256,
            "release_reason": None,
            "device_session_started": None,
            "partition_transfer": None,
            "record_sha256": ZERO_SHA256,
        }
        result = _append(repo_root, record)
    return {
        "schema": REGISTRY_SCHEMA,
        "event": "claim",
        "candidate_key": identity_value["candidate_key"],
        "claim_id": claim_id,
        "record": result["record"],
        "record_receipt": result["record_receipt"],
        "head": result["head"],
    }


def release(
    repo_root: Path,
    claim_value: Mapping[str, Any],
    *,
    release_reason: str = "odin_local_parse_failure",
    device_session_started: bool = False,
    partition_transfer: bool = False,
) -> dict[str, Any]:
    if not isinstance(claim_value, Mapping):
        raise RegistryError("claim receipt is not an object")
    candidate_key = claim_value.get("candidate_key")
    claim_id = claim_value.get("claim_id")
    if not isinstance(candidate_key, str) or not SHA256_RE.fullmatch(candidate_key) or not isinstance(claim_id, str) or not SHA256_RE.fullmatch(claim_id):
        raise RegistryError("claim receipt identity is malformed")
    if release_reason != "odin_local_parse_failure" or device_session_started is not False or partition_transfer is not False:
        raise RegistryError("only exact pre-session parse failure may release a claim")
    with _writer(repo_root):
        _head, records, _details = _scan(repo_root)
        existing = _claims(records).get(candidate_key)
        supplied_record = claim_value.get("record")
        recorded_claim = next(
            (
                item
                for item in records
                if item["event"] == "claim"
                and item["candidate_key"] == candidate_key
                and item["claim_id"] == claim_id
            ),
            None,
        )
        if not isinstance(supplied_record, dict) or recorded_claim is None:
            raise RegistryError("claim receipt lacks its recorded owner")
        if supplied_record != recorded_claim:
            raise RegistryError("claim receipt owner differs from active claim")
        if existing is None or existing.get("claim_id") != claim_id:
            for item in reversed(records):
                if (
                    item["event"] == "release"
                    and item["candidate_key"] == candidate_key
                    and item["claim_id"] == claim_id
                ):
                    return {
                        "schema": REGISTRY_SCHEMA,
                        "event": "release",
                        "candidate_key": candidate_key,
                        "claim_id": claim_id,
                        "record": dict(item),
                    }
            raise RegistryError("active candidate claim is absent or differs")
        record = {
            "schema": RECORD_SCHEMA,
            "sequence": len(records),
            "event": "release",
            "candidate_key": candidate_key,
            "target_profile_sha256": existing["target_profile_sha256"],
            "target_key": existing["target_key"],
            "candidate_ap_sha256": existing["candidate_ap_sha256"],
            "candidate_ap_size": existing["candidate_ap_size"],
            "boot_member_name": existing["boot_member_name"],
            "boot_member_size": existing["boot_member_size"],
            "boot_member_sha256": existing["boot_member_sha256"],
            "manifest_id": existing["manifest_id"],
            "run_id": existing["run_id"],
            "approval_binding_sha256": existing["approval_binding_sha256"],
            "claim_id": claim_id,
            "previous_record_sha256": ZERO_SHA256,
            "release_reason": release_reason,
            "device_session_started": False,
            "partition_transfer": False,
            "record_sha256": ZERO_SHA256,
        }
        result = _append(repo_root, record)
    return {
        "schema": REGISTRY_SCHEMA,
        "event": "release",
        "candidate_key": candidate_key,
        "claim_id": claim_id,
        "record": result["record"],
        "record_receipt": result["record_receipt"],
        "head": result["head"],
    }


def qualification_summary(repo_root: Path) -> dict[str, Any]:
    """Return the structural authority summary for the real empty registry."""

    state = initialize(repo_root)
    root = registry_root(repo_root)
    head = root / HEAD_NAME
    lock = root / LOCK_NAME
    session_lock = root / SESSION_LOCK_NAME
    activation = root / ACTIVATION_NAME
    head_data = _read_regular(head, "qualification head", mode=0o400, maximum=MAX_HEAD_BYTES)
    lock_data = _read_regular(lock, "qualification lock", mode=0o600, maximum=MAX_LOCK_BYTES)
    session_lock_data = _read_regular(session_lock, "qualification target-session lock", mode=0o600, maximum=MAX_LOCK_BYTES)
    activation_data = _read_regular(activation, "qualification activation", mode=0o400, maximum=MAX_RECORD_BYTES)
    activation_value = _parse_json(activation_data, "qualification activation")
    return {
        "schema": QUALIFICATION_SCHEMA,
        "scope": "global",
        "registry_root": REGISTRY_DIR_NAME,
        "head": {"name": HEAD_NAME, **_identity(head_data), "mode": "0400", "nlink": 1},
        "lock": {"name": LOCK_NAME, **_identity(lock_data), "mode": "0600", "nlink": 1},
        "session_lock": {"name": SESSION_LOCK_NAME, **_identity(session_lock_data), "mode": "0600", "nlink": 1},
        "activation": {"name": ACTIVATION_NAME, **_identity(activation_data), "mode": "0400", "nlink": 1, "legacy_candidate_count": len(activation_value["legacy_candidates"])},
        "records": {"name": RECORDS_NAME, "count": 0, "max_count": MAX_RECORDS, "max_record_bytes": MAX_RECORD_BYTES},
        "record_count": state["record_count"],
        "empty_at_initialization": state["record_count"] == 0,
        "replay_forbidden": True,
        "append_only": True,
        "hash_chained": True,
        "strict_typed_canonical_json": True,
        "file_and_directory_fsync": True,
        "single_writer_flock": True,
        "process_restart_durable": True,
        "replacement_fail_closed": True,
        "no_caller_supplied_path": True,
        "runner_consumption_boundary": "candidate claim precedes candidate backend transfer",
        "device_contact": False,
        "live_authorized": False,
    }
