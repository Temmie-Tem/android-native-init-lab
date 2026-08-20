#!/usr/bin/env python3
"""Dormant one-shot journal core for a future attended S20+ N3-U0 F1."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import re
import secrets
import stat
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCHEMA = "s20plus_g986n_n3u0_attended_f1_v1"
VERSION = 1
F1_ACTIVE = False
STATUS = "H0_EXECUTION_JOURNAL_PASS_GO_NOT_ACTIVE"
APPROVAL_PREFIX = "S20PLUS-G986N-N3U0-ATTENDED-F1-APPROVE:"
EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "74e2d7fc4effdaf25ee24a6b753919ebdde00b75a219f5ed2a6dee980fccbe7e"
MODEL_SOURCE = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_n3u0_attended_owner_h0.py"
)
MODEL_SOURCE_SIZE = 14_125
MODEL_SOURCE_SHA256 = (
    "db1b282e33218ea9f7a48b8b90b28b50a121dab3429b3f642ebf0e90ff940eca"
)
MODEL_BINDING_SHA256 = (
    "860d7970b0b841d1fccdaa27c59ec0d56060294f566c0d4844f484593f5fffbc"
)
TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

HEX64_RE = re.compile(r"[0-9a-f]{64}")
RUN_ID_RE = re.compile(r"[0-9a-f]{32}")
MAX_JOURNAL_BYTES = 1024 * 1024
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

JOURNAL_FILES = {
    "prepared.json",
    "initial-download-intent.json",
    "initial-download-result.json",
    "initial-download-observation.json",
    "candidate-intent.json",
    "candidate-result.json",
    "candidate-observation.json",
    "rollback-mode-intent.json",
    "rollback-mode-result.json",
    "rollback-mode-observation.json",
    "physical-rollback-intent.json",
    "physical-rollback-arrival.json",
    "rollback-intent.json",
    "rollback-result.json",
    "final-health.json",
    "terminal-result.json",
}


class N3U0F1Error(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise N3U0F1Error("journal value is not canonical JSON") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def exact_typed_equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and set(actual) == set(expected)
            and all(exact_typed_equal(actual[key], expected[key]) for key in expected)
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(
                exact_typed_equal(left, right)
                for left, right in zip(actual, expected)
            )
        )
    if expected is None:
        return actual is None
    return type(actual) is type(expected) and actual == expected


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def fsync_dir(path: Path) -> None:
    descriptor = os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_blob(path: Path, payload: bytes, mode: int = 0o400) -> None:
    if len(payload) > MAX_JOURNAL_BYTES:
        raise N3U0F1Error("journal payload is oversized")
    parent = os.open(
        path.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    descriptor = -1
    try:
        descriptor = os.open(
            ".",
            os.O_WRONLY | os.O_TMPFILE | os.O_CLOEXEC,
            mode,
            dir_fd=parent,
        )
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise N3U0F1Error("short journal write")
            offset += written
        os.fsync(descriptor)
        if _LINKAT(
            descriptor,
            b"",
            parent,
            os.fsencode(path.name),
            AT_EMPTY_PATH,
        ) != 0:
            number = ctypes.get_errno()
            raise OSError(number, os.strerror(number), path)
        os.fsync(parent)
    finally:
        try:
            if descriptor >= 0:
                os.close(descriptor)
        finally:
            os.close(parent)


def durable_create(path: Path, value: Any) -> None:
    durable_blob(path, canonical_bytes(value))


def read_exact_json(path: Path, label: str) -> Any:
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
    except (FileNotFoundError, OSError) as exc:
        raise N3U0F1Error(f"{label} is missing or indirect") from exc
    try:
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_size > MAX_JOURNAL_BYTES
        ):
            raise N3U0F1Error(f"{label} is not an exact bounded regular file")
        payload = bytearray()
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > MAX_JOURNAL_BYTES:
                raise N3U0F1Error(f"{label} is oversized")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    try:
        value = json.loads(
            bytes(payload).decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
        if bytes(payload) != canonical_bytes(value):
            raise ValueError("journal JSON is not canonical")
        return value
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise N3U0F1Error(f"{label} is malformed") from exc


def require_hex(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise N3U0F1Error(f"{label} is not lowercase SHA-256")
    return value


def require_run_id(value: Any) -> str:
    if not isinstance(value, str) or RUN_ID_RE.fullmatch(value) is None:
        raise N3U0F1Error("run ID is malformed")
    return value


def validate_identity(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {
        "serial_sha256",
        "topology_sha256",
        "boot_id_sha256",
    }:
        raise N3U0F1Error(f"{label} shape is malformed")
    return {
        key: require_hex(value[key], f"{label} {key}")
        for key in ("serial_sha256", "topology_sha256", "boot_id_sha256")
    }


def validate_endpoint(value: Any, label: str) -> dict[str, str]:
    keys = {
        "path_sha256",
        "identity_sha256",
        "topology_sha256",
        "profile_sha256",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise N3U0F1Error(f"{label} shape is malformed")
    return {key: require_hex(value[key], f"{label} {key}") for key in sorted(keys)}


def validate_raw_receipt(value: Any, label: str) -> dict[str, Any]:
    keys = {"stdout_sha256", "stderr_sha256", "stdout_size", "stderr_size"}
    if not isinstance(value, dict) or set(value) != keys:
        raise N3U0F1Error(f"{label} shape is malformed")
    for key in ("stdout_sha256", "stderr_sha256"):
        require_hex(value[key], f"{label} {key}")
    for key in ("stdout_size", "stderr_size"):
        if type(value[key]) is not int or not 0 <= value[key] <= MAX_JOURNAL_BYTES:
            raise N3U0F1Error(f"{label} {key} is malformed")
    return value


def validate_final_health_receipt(value: Any) -> dict[str, Any]:
    keys = {
        "identity",
        "android_health_sha256",
        "root_output_sha256",
        "root_attempts",
        "exact_target_healthy",
        "root_verified",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise N3U0F1Error("final health receipt shape is malformed")
    validate_identity(value["identity"], "final health receipt identity")
    require_hex(value["android_health_sha256"], "Android health receipt")
    require_hex(value["root_output_sha256"], "root output receipt")
    if (
        type(value["root_attempts"]) is not int
        or value["root_attempts"] < 1
        or value["exact_target_healthy"] is not True
        or value["root_verified"] is not True
    ):
        raise N3U0F1Error("final health receipt proof is malformed")
    return value


def _source_receipt() -> dict[str, Any]:
    descriptor = os.open(
        MODEL_SOURCE, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size != MODEL_SOURCE_SIZE
        ):
            raise N3U0F1Error("H0 owner model identity differs")
        payload = bytearray()
        while len(payload) < MODEL_SOURCE_SIZE:
            chunk = os.read(descriptor, MODEL_SOURCE_SIZE - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
    finally:
        os.close(descriptor)
    if (
        len(payload) != MODEL_SOURCE_SIZE
        or hashlib.sha256(payload).hexdigest() != MODEL_SOURCE_SHA256
    ):
        raise N3U0F1Error("H0 owner model hash differs")
    return {
        "path": str(MODEL_SOURCE),
        "size": MODEL_SOURCE_SIZE,
        "sha256": MODEL_SOURCE_SHA256,
    }


def self_receipt() -> dict[str, Any]:
    path = Path(__file__).resolve(strict=True)
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise N3U0F1Error("journal runner is not an exact regular file")
        payload = bytearray()
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > MAX_JOURNAL_BYTES:
                raise N3U0F1Error("journal runner is oversized")
    finally:
        os.close(descriptor)
    normalized, count = re.subn(
        rb'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "[0-9a-f]{64}"',
        b'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        bytes(payload),
    )
    normalized_sha256 = hashlib.sha256(normalized).hexdigest()
    if (
        count != 1
        or normalized_sha256 != EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256
    ):
        raise N3U0F1Error("journal runner normalized identity differs")
    return {
        "path": str(path),
        "size": metadata.st_size,
        "normalized_sha256": normalized_sha256,
    }


def load_model() -> Any:
    _source_receipt()
    specification = importlib.util.spec_from_file_location(
        "s20plus_n3u0_attended_owner_h0_bound", MODEL_SOURCE
    )
    if specification is None or specification.loader is None:
        raise N3U0F1Error("H0 owner model cannot be loaded")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    plan = module.render_plan()
    if (
        plan.get("binding_sha256") != MODEL_BINDING_SHA256
        or plan.get("active") is not False
        or plan.get("live_authority") is not False
    ):
        raise N3U0F1Error("H0 owner model binding differs")
    return module


def current_binding() -> dict[str, Any]:
    model = load_model()
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "status": STATUS,
        "target": dict(TARGET),
        "runner": self_receipt(),
        "model_source": _source_receipt(),
        "model_binding_sha256": MODEL_BINDING_SHA256,
        "candidate_ap_sha256": model.CANDIDATE_AP_SHA256,
        "candidate_boot_sha256": model.CANDIDATE_BOOT_SHA256,
        "rollback_ap_sha256": model.ROLLBACK_AP_SHA256,
        "rollback_boot_sha256": model.ROLLBACK_BOOT_SHA256,
        "candidate_attempts": 1,
        "rollback_attempts": 1,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
    }


def binding_sha256() -> str:
    return digest(current_binding())


def _base(schema: str, run_id: str, binding: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "version": VERSION,
        "run_id": require_run_id(run_id),
        "binding_sha256": require_hex(binding, "binding"),
    }


def _guard_path(runs_root: Path) -> Path:
    return runs_root / "active.json"


def _guard_value(prepared: dict[str, Any]) -> dict[str, Any]:
    return {
        **_base(
            "s20plus_g986n_n3u0_guard_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "unresolved": True,
        "prepared": prepared,
    }


def _require_direct_directory(path: Path, label: str) -> None:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise N3U0F1Error(f"{label} is not a direct directory")


def acquire_guard(runs_root: Path, prepared: dict[str, Any]) -> None:
    _require_direct_directory(runs_root, "N3-U0 runs root")
    expected = _guard_value(prepared)
    run_dir = runs_root / require_run_id(prepared["run_id"])
    _require_direct_directory(run_dir, "new N3-U0 run directory")
    if _run_files(run_dir):
        raise N3U0F1Error("new N3-U0 allocation directory is not empty")
    path = _guard_path(runs_root)
    if os.path.lexists(path):
        raise N3U0F1Error("an unresolved N3-U0 guard already exists")
    durable_create(path, expected)


def resume_guard_prepared(runs_root: Path, run_id: str) -> Path:
    require_run_id(run_id)
    _require_direct_directory(runs_root, "N3-U0 runs root")
    guard = read_exact_json(_guard_path(runs_root), "N3-U0 allocation guard")
    if (
        not isinstance(guard, dict)
        or set(guard)
        != {"schema", "version", "run_id", "binding_sha256", "unresolved", "prepared"}
        or guard.get("schema") != "s20plus_g986n_n3u0_guard_v1"
        or type(guard.get("version")) is not int
        or guard.get("version") != VERSION
        or guard.get("run_id") != run_id
        or guard.get("unresolved") is not True
    ):
        raise N3U0F1Error("allocation guard is malformed or belongs to another run")
    run_dir = runs_root / run_id
    names = _run_files(run_dir)
    if names not in (set(), {"prepared.json"}):
        raise N3U0F1Error("allocation-guard recovery found a later journal state")
    prepared = _validate_prepared_value(guard["prepared"], run_dir)
    if guard["binding_sha256"] != prepared["binding_sha256"]:
        raise N3U0F1Error("allocation guard binding differs from prepared state")
    if not names:
        durable_create(run_dir / "prepared.json", prepared)
    elif not exact_typed_equal(
        read_exact_json(run_dir / "prepared.json", "prepared journal"), prepared
    ):
        raise N3U0F1Error("prepared journal differs from allocation guard")
    require_guard(run_dir, prepared)
    return run_dir


def require_guard(run_dir: Path, prepared: dict[str, Any]) -> None:
    expected = _guard_value(prepared)
    actual = read_exact_json(_guard_path(run_dir.parent), "N3-U0 guard")
    if not exact_typed_equal(actual, expected):
        raise N3U0F1Error("N3-U0 guard is foreign or malformed")


def release_guard(run_dir: Path, prepared: dict[str, Any]) -> None:
    path = _guard_path(run_dir.parent)
    if not os.path.lexists(path):
        return
    require_guard(run_dir, prepared)
    path.unlink()
    fsync_dir(path.parent)


def _run_files(run_dir: Path) -> set[str]:
    _require_direct_directory(run_dir, "N3-U0 run directory")
    names: set[str] = set()
    for child in run_dir.iterdir():
        metadata = child.lstat()
        if child.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise N3U0F1Error("N3-U0 journal contains an indirect node")
        if metadata.st_nlink != 1:
            raise N3U0F1Error("N3-U0 journal contains a hardlinked node")
        if stat.S_IMODE(metadata.st_mode) != 0o400:
            raise N3U0F1Error("N3-U0 journal node mode differs")
        names.add(child.name)
    if not names.issubset(JOURNAL_FILES):
        raise N3U0F1Error("N3-U0 journal contains an unknown node")
    return names


def _record(run_dir: Path, name: str) -> dict[str, Any]:
    return read_exact_json(run_dir / name, f"N3-U0 {name}")


def create_prepared(
    runs_root: Path,
    prepared_identity: dict[str, str],
    empty_download_baseline_sha256: str,
) -> Path:
    _require_direct_directory(runs_root, "N3-U0 runs root")
    if os.path.lexists(_guard_path(runs_root)):
        raise N3U0F1Error("an unresolved N3-U0 run already exists")
    identity = validate_identity(prepared_identity, "prepared identity")
    baseline = require_hex(empty_download_baseline_sha256, "Download baseline")
    run_id = secrets.token_hex(16)
    run_dir = runs_root / run_id
    run_dir.mkdir(mode=0o700)
    fsync_dir(runs_root)
    binding = binding_sha256()
    prepared = {
        **_base("s20plus_g986n_n3u0_prepared_v1", run_id, binding),
        "target": dict(TARGET),
        "prepared_identity": identity,
        "empty_download_baseline_sha256": baseline,
        "candidate_attempts": 1,
        "rollback_attempts": 1,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
    }
    acquire_guard(runs_root, prepared)
    durable_create(run_dir / "prepared.json", prepared)
    return run_dir


def _validate_prepared_value(
    value: Any, run_dir: Path
) -> dict[str, Any]:
    keys = {
        "schema",
        "version",
        "run_id",
        "binding_sha256",
        "target",
        "prepared_identity",
        "empty_download_baseline_sha256",
        "candidate_attempts",
        "rollback_attempts",
        "candidate_replay_permitted",
        "rollback_replay_permitted",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise N3U0F1Error("prepared journal shape is malformed")
    run_id = require_run_id(value["run_id"])
    binding = binding_sha256()
    if (
        value["schema"] != "s20plus_g986n_n3u0_prepared_v1"
        or type(value["version"]) is not int
        or value["version"] != VERSION
        or value["binding_sha256"] != binding
        or not exact_typed_equal(value["target"], TARGET)
        or type(value["candidate_attempts"]) is not int
        or value["candidate_attempts"] != 1
        or type(value["rollback_attempts"]) is not int
        or value["rollback_attempts"] != 1
        or value["candidate_replay_permitted"] is not False
        or value["rollback_replay_permitted"] is not False
    ):
        raise N3U0F1Error("prepared journal binding is malformed")
    validate_identity(value["prepared_identity"], "prepared identity")
    require_hex(value["empty_download_baseline_sha256"], "Download baseline")
    if run_dir.name != run_id:
        raise N3U0F1Error("run directory does not match its run ID")
    return value


def read_prepared(run_dir: Path, *, require_active_guard: bool = True) -> dict[str, Any]:
    names = _run_files(run_dir)
    if "prepared.json" not in names:
        raise N3U0F1Error("prepared journal is absent")
    value = _validate_prepared_value(_record(run_dir, "prepared.json"), run_dir)
    if require_active_guard:
        require_guard(run_dir, value)
    return value


def _publish_effect_intent(
    run_dir: Path,
    prepared: dict[str, Any],
    name: str,
    action: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    if os.path.lexists(run_dir / name):
        raise N3U0F1Error(f"{action} intent already exists; replay forbidden")
    value = {
        **_base(
            f"s20plus_g986n_n3u0_{action.replace('-', '_')}_intent_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "action": action,
        "attempt": 1,
        "replay_permitted": False,
        **details,
    }
    durable_create(run_dir / name, value)
    return value


def begin_initial_download(run_dir: Path) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if os.path.lexists(run_dir / "initial-download-intent.json"):
        raise N3U0F1Error(
            "initial-download-reboot intent already exists; replay forbidden"
        )
    if _run_files(run_dir) != {"prepared.json"}:
        raise N3U0F1Error("initial Download is not eligible from this journal state")
    return _publish_effect_intent(
        run_dir,
        prepared,
        "initial-download-intent.json",
        "initial-download-reboot",
        {
            "source_identity": prepared["prepared_identity"],
            "empty_download_baseline_sha256": prepared[
                "empty_download_baseline_sha256"
            ],
        },
    )


def record_initial_download_result(
    run_dir: Path, outcome: str, raw_receipt: dict[str, Any]
) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if not os.path.lexists(run_dir / "initial-download-intent.json"):
        raise N3U0F1Error("initial Download result lacks intent")
    if os.path.lexists(run_dir / "initial-download-result.json"):
        raise N3U0F1Error("initial Download result already exists")
    if outcome not in ("dispatched", "uncertain"):
        raise N3U0F1Error("initial Download result is unknown")
    value = {
        **_base(
            "s20plus_g986n_n3u0_initial_download_result_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "outcome": outcome,
        "raw_receipt": validate_raw_receipt(raw_receipt, "initial Download raw"),
        "attempt": 1,
        "replay_permitted": False,
    }
    durable_create(run_dir / "initial-download-result.json", value)
    return value


def record_initial_download_observation(
    run_dir: Path,
    endpoint: dict[str, str],
    arrival_listing_sha256: str,
) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if not os.path.lexists(run_dir / "initial-download-intent.json"):
        raise N3U0F1Error("initial Download observation lacks intent")
    if os.path.lexists(run_dir / "initial-download-observation.json"):
        raise N3U0F1Error("initial Download observation already exists")
    value = {
        **_base(
            "s20plus_g986n_n3u0_initial_download_observation_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "endpoint": validate_endpoint(endpoint, "initial Download endpoint"),
        "arrival_listing_sha256": require_hex(
            arrival_listing_sha256, "initial Download arrival listing"
        ),
        "resolution": "download-observed",
    }
    durable_create(run_dir / "initial-download-observation.json", value)
    return value


def approval_token(run_dir: Path) -> str:
    prepared = validate_legal_prefix(run_dir)
    if not os.path.lexists(run_dir / "initial-download-observation.json"):
        raise N3U0F1Error("approval requires exact initial Download arrival")
    observation = _record(run_dir, "initial-download-observation.json")
    value = {
        "schema": "s20plus_g986n_n3u0_approval_v1",
        "run_id": prepared["run_id"],
        "binding_sha256": prepared["binding_sha256"],
        "prepared_boot_id_sha256": prepared["prepared_identity"][
            "boot_id_sha256"
        ],
        "endpoint": observation["endpoint"],
        "candidate_ap_sha256": current_binding()["candidate_ap_sha256"],
    }
    return APPROVAL_PREFIX + digest(value)


def begin_candidate(
    run_dir: Path, approval: str, endpoint: dict[str, str]
) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if os.path.lexists(run_dir / "candidate-intent.json"):
        raise N3U0F1Error("candidate-transfer intent already exists; replay forbidden")
    names = _run_files(run_dir)
    if "initial-download-observation.json" not in names:
        raise N3U0F1Error("candidate is not eligible from this journal state")
    if not isinstance(approval, str) or approval != approval_token(run_dir):
        raise N3U0F1Error("candidate approval is malformed or stale")
    observed = _record(run_dir, "initial-download-observation.json")["endpoint"]
    selected = validate_endpoint(endpoint, "candidate endpoint")
    if not exact_typed_equal(selected, observed):
        raise N3U0F1Error("candidate endpoint differs from approved arrival")
    return _publish_effect_intent(
        run_dir,
        prepared,
        "candidate-intent.json",
        "candidate-transfer",
        {
            "ap_sha256": current_binding()["candidate_ap_sha256"],
            "endpoint": selected,
        },
    )


def record_transfer_result(
    run_dir: Path,
    kind: str,
    classification: str,
    raw_receipt: dict[str, Any],
) -> dict[str, Any]:
    if kind not in ("candidate", "rollback"):
        raise N3U0F1Error("unknown transfer kind")
    prepared = validate_legal_prefix(run_dir)
    intent_name = f"{kind}-intent.json"
    result_name = f"{kind}-result.json"
    if not os.path.lexists(run_dir / intent_name):
        raise N3U0F1Error(f"{kind} result lacks its intent")
    if os.path.lexists(run_dir / result_name):
        raise N3U0F1Error(f"{kind} result already exists")
    if classification not in (
        "odin_transfer_completed",
        "odin_device_session_failure_or_unknown",
        "local_parse_failure",
    ):
        raise N3U0F1Error("transfer classification is unknown")
    value = {
        **_base(
            f"s20plus_g986n_n3u0_{kind}_result_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "kind": kind,
        "classification": classification,
        "raw_receipt": validate_raw_receipt(raw_receipt, f"{kind} raw receipt"),
        "attempt": 1,
        "replay_permitted": False,
    }
    durable_create(run_dir / result_name, value)
    return value


def record_candidate_observation(
    run_dir: Path,
    *,
    banner_accepted: bool,
    android_identity: dict[str, str] | None,
) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if not os.path.lexists(run_dir / "candidate-intent.json"):
        raise N3U0F1Error("candidate observation lacks consumed candidate intent")
    if os.path.lexists(run_dir / "candidate-observation.json"):
        raise N3U0F1Error("candidate observation already exists")
    if type(banner_accepted) is not bool:
        raise N3U0F1Error("candidate banner state is malformed")
    identity = (
        None
        if android_identity is None
        else validate_identity(android_identity, "candidate Android identity")
    )
    if identity is not None:
        prepared_identity = prepared["prepared_identity"]
        if (
            identity["serial_sha256"] != prepared_identity["serial_sha256"]
            or identity["topology_sha256"] != prepared_identity["topology_sha256"]
            or identity["boot_id_sha256"] == prepared_identity["boot_id_sha256"]
        ):
            raise N3U0F1Error("candidate Android identity lacks exact continuity")
    value = {
        **_base(
            "s20plus_g986n_n3u0_candidate_observation_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "banner_accepted": banner_accepted,
        "android_identity": identity,
        "terminal": False,
        "rollback_required": True,
    }
    durable_create(run_dir / "candidate-observation.json", value)
    return value


def begin_rollback_mode(run_dir: Path) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if os.path.lexists(run_dir / "physical-rollback-intent.json"):
        raise N3U0F1Error("physical rollback branch already owns recovery")
    if not os.path.lexists(run_dir / "candidate-observation.json"):
        raise N3U0F1Error("automatic rollback requires candidate observation")
    observation = _record(run_dir, "candidate-observation.json")
    identity = observation.get("android_identity")
    if identity is None:
        raise N3U0F1Error("automatic rollback requires exact Android return")
    return _publish_effect_intent(
        run_dir,
        prepared,
        "rollback-mode-intent.json",
        "rollback-mode-reboot",
        {"source_identity": validate_identity(identity, "rollback source")},
    )


def record_rollback_mode_result(
    run_dir: Path, outcome: str, raw_receipt: dict[str, Any]
) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if not os.path.lexists(run_dir / "rollback-mode-intent.json"):
        raise N3U0F1Error("rollback-mode result lacks intent")
    if os.path.lexists(run_dir / "rollback-mode-result.json"):
        raise N3U0F1Error("rollback-mode result already exists")
    if outcome not in ("dispatched", "uncertain"):
        raise N3U0F1Error("rollback-mode result is unknown")
    value = {
        **_base(
            "s20plus_g986n_n3u0_rollback_mode_result_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "outcome": outcome,
        "raw_receipt": validate_raw_receipt(raw_receipt, "rollback-mode raw"),
        "attempt": 1,
        "replay_permitted": False,
    }
    durable_create(run_dir / "rollback-mode-result.json", value)
    return value


def record_rollback_mode_observation(
    run_dir: Path, endpoint: dict[str, str]
) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if not os.path.lexists(run_dir / "rollback-mode-intent.json"):
        raise N3U0F1Error("rollback-mode observation lacks intent")
    if os.path.lexists(run_dir / "rollback-mode-observation.json"):
        raise N3U0F1Error("rollback-mode observation already exists")
    value = {
        **_base(
            "s20plus_g986n_n3u0_rollback_mode_observation_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "endpoint": validate_endpoint(endpoint, "rollback endpoint"),
        "resolution": "download-observed",
    }
    durable_create(run_dir / "rollback-mode-observation.json", value)
    return value


def begin_physical_rollback(run_dir: Path, empty_baseline_sha256: str) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if os.path.lexists(run_dir / "rollback-mode-intent.json"):
        raise N3U0F1Error("automatic rollback branch already owns recovery")
    if not os.path.lexists(run_dir / "candidate-intent.json"):
        raise N3U0F1Error("physical rollback requires consumed candidate intent")
    return _publish_effect_intent(
        run_dir,
        prepared,
        "physical-rollback-intent.json",
        "physical-rollback-entry",
        {
            "empty_download_baseline_sha256": require_hex(
                empty_baseline_sha256, "physical rollback baseline"
            ),
            "operator_attended": True,
        },
    )


def record_physical_arrival(
    run_dir: Path, endpoint: dict[str, str], arrival_listing_sha256: str
) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if not os.path.lexists(run_dir / "physical-rollback-intent.json"):
        raise N3U0F1Error("physical arrival lacks its intent")
    if os.path.lexists(run_dir / "physical-rollback-arrival.json"):
        raise N3U0F1Error("physical arrival already exists")
    value = {
        **_base(
            "s20plus_g986n_n3u0_physical_rollback_arrival_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "endpoint": validate_endpoint(endpoint, "physical rollback endpoint"),
        "arrival_listing_sha256": require_hex(
            arrival_listing_sha256, "physical arrival listing"
        ),
        "attempt": 1,
        "replay_permitted": False,
    }
    durable_create(run_dir / "physical-rollback-arrival.json", value)
    return value


def begin_rollback(run_dir: Path) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    automatic = os.path.lexists(run_dir / "rollback-mode-observation.json")
    physical = os.path.lexists(run_dir / "physical-rollback-arrival.json")
    if automatic == physical:
        raise N3U0F1Error("exactly one rollback arrival branch is required")
    source = (
        _record(run_dir, "rollback-mode-observation.json")
        if automatic
        else _record(run_dir, "physical-rollback-arrival.json")
    )
    return _publish_effect_intent(
        run_dir,
        prepared,
        "rollback-intent.json",
        "rollback-transfer",
        {
            "ap_sha256": current_binding()["rollback_ap_sha256"],
            "endpoint": validate_endpoint(source["endpoint"], "rollback endpoint"),
        },
    )


def _durable_boot_ids(run_dir: Path, prepared: dict[str, Any]) -> list[str]:
    boot_ids = [prepared["prepared_identity"]["boot_id_sha256"]]
    if os.path.lexists(run_dir / "candidate-observation.json"):
        candidate = _record(run_dir, "candidate-observation.json").get(
            "android_identity"
        )
        if candidate is not None:
            boot_ids.append(validate_identity(candidate, "candidate identity")["boot_id_sha256"])
    if os.path.lexists(run_dir / "rollback-mode-intent.json"):
        source = _record(run_dir, "rollback-mode-intent.json")["source_identity"]
        boot_ids.append(validate_identity(source, "rollback source")["boot_id_sha256"])
    return boot_ids


def record_final_health(run_dir: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir)
    if not os.path.lexists(run_dir / "rollback-result.json"):
        raise N3U0F1Error("final health lacks rollback result")
    result = _record(run_dir, "rollback-result.json")
    if result.get("classification") != "odin_transfer_completed":
        raise N3U0F1Error("final health requires completed resident rollback")
    proof = validate_final_health_receipt(receipt)
    final_identity = validate_identity(proof["identity"], "final resident identity")
    prepared_identity = prepared["prepared_identity"]
    if (
        final_identity["serial_sha256"] != prepared_identity["serial_sha256"]
        or final_identity["topology_sha256"] != prepared_identity["topology_sha256"]
        or final_identity["boot_id_sha256"] in _durable_boot_ids(run_dir, prepared)
    ):
        raise N3U0F1Error("final resident identity lacks fresh exact continuity")
    value = {
        **_base(
            "s20plus_g986n_n3u0_final_health_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "identity": final_identity,
        "health_receipt": proof,
        "rollback_transfer": "odin_transfer_completed",
        "resident_magisk_root_verified": True,
        "candidate_terminal": False,
        "healthy": True,
    }
    durable_create(run_dir / "final-health.json", value)
    return value


def finalize(run_dir: Path) -> dict[str, Any]:
    prepared = validate_legal_prefix(run_dir, require_active_guard=False)
    run_id = prepared["run_id"]
    binding = prepared["binding_sha256"]
    terminal_path = run_dir / "terminal-result.json"
    if os.path.lexists(terminal_path):
        terminal = read_exact_json(terminal_path, "N3-U0 terminal")
        if terminal.get("verdict") != "PASS_S20PLUS_G986N_N3U0_RESIDENT_RESTORED":
            raise N3U0F1Error("terminal result is malformed")
        release_guard(run_dir, prepared)
        return terminal
    require_guard(run_dir, prepared)
    if not os.path.lexists(run_dir / "final-health.json"):
        raise N3U0F1Error("terminal lacks final health")
    health = _record(run_dir, "final-health.json")
    if (
        health.get("healthy") is not True
        or health.get("resident_magisk_root_verified") is not True
        or health.get("rollback_transfer") != "odin_transfer_completed"
    ):
        raise N3U0F1Error("terminal health is not exact resident recovery")
    terminal = {
        **_base(
            "s20plus_g986n_n3u0_terminal_v1",
            run_id,
            binding,
        ),
        "verdict": "PASS_S20PLUS_G986N_N3U0_RESIDENT_RESTORED",
        "candidate_attempts": 1,
        "rollback_attempts": 1,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "final_identity": health["identity"],
        "resident_magisk_root_verified": True,
    }
    durable_create(terminal_path, terminal)
    release_guard(run_dir, prepared)
    return terminal


def _validate_base_record(
    value: Any,
    prepared: dict[str, Any],
    schema: str,
    extra_keys: set[str],
    label: str,
) -> dict[str, Any]:
    keys = {"schema", "version", "run_id", "binding_sha256"} | extra_keys
    if not isinstance(value, dict) or set(value) != keys:
        raise N3U0F1Error(f"{label} shape is malformed")
    if (
        value["schema"] != schema
        or type(value["version"]) is not int
        or value["version"] != VERSION
        or value["run_id"] != prepared["run_id"]
        or value["binding_sha256"] != prepared["binding_sha256"]
    ):
        raise N3U0F1Error(f"{label} binding is malformed")
    return value


def _validate_effect_intent(
    value: Any,
    prepared: dict[str, Any],
    *,
    schema: str,
    action: str,
    extra_keys: set[str],
    label: str,
) -> dict[str, Any]:
    record = _validate_base_record(
        value,
        prepared,
        schema,
        {"action", "attempt", "replay_permitted"} | extra_keys,
        label,
    )
    if (
        record["action"] != action
        or type(record["attempt"]) is not int
        or record["attempt"] != 1
        or record["replay_permitted"] is not False
    ):
        raise N3U0F1Error(f"{label} authority is malformed")
    return record


def _validate_transfer_result_record(
    value: Any,
    prepared: dict[str, Any],
    kind: str,
) -> dict[str, Any]:
    label = f"{kind} result"
    record = _validate_base_record(
        value,
        prepared,
        f"s20plus_g986n_n3u0_{kind}_result_v1",
        {"kind", "classification", "raw_receipt", "attempt", "replay_permitted"},
        label,
    )
    if (
        record["kind"] != kind
        or record["classification"]
        not in (
            "odin_transfer_completed",
            "odin_device_session_failure_or_unknown",
            "local_parse_failure",
        )
        or type(record["attempt"]) is not int
        or record["attempt"] != 1
        or record["replay_permitted"] is not False
    ):
        raise N3U0F1Error(f"{label} authority is malformed")
    validate_raw_receipt(record["raw_receipt"], f"{label} raw receipt")
    return record


def _validate_initial_download_intent_record(
    value: Any, prepared: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_effect_intent(
        value,
        prepared,
        schema="s20plus_g986n_n3u0_initial_download_reboot_intent_v1",
        action="initial-download-reboot",
        extra_keys={"source_identity", "empty_download_baseline_sha256"},
        label="initial Download intent",
    )
    if (
        not exact_typed_equal(record["source_identity"], prepared["prepared_identity"])
        or record["empty_download_baseline_sha256"]
        != prepared["empty_download_baseline_sha256"]
    ):
        raise N3U0F1Error("initial Download source binding differs")
    return record


def _validate_initial_download_result_record(
    value: Any, prepared: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_base_record(
        value,
        prepared,
        "s20plus_g986n_n3u0_initial_download_result_v1",
        {"outcome", "raw_receipt", "attempt", "replay_permitted"},
        "initial Download result",
    )
    if (
        record["outcome"] not in ("dispatched", "uncertain")
        or type(record["attempt"]) is not int
        or record["attempt"] != 1
        or record["replay_permitted"] is not False
    ):
        raise N3U0F1Error("initial Download result authority is malformed")
    validate_raw_receipt(record["raw_receipt"], "initial Download raw receipt")
    return record


def _validate_initial_download_observation_record(
    value: Any, prepared: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_base_record(
        value,
        prepared,
        "s20plus_g986n_n3u0_initial_download_observation_v1",
        {"endpoint", "arrival_listing_sha256", "resolution"},
        "initial Download observation",
    )
    validate_endpoint(record["endpoint"], "initial Download endpoint")
    require_hex(record["arrival_listing_sha256"], "initial Download arrival listing")
    if record["resolution"] != "download-observed":
        raise N3U0F1Error("initial Download observation resolution is malformed")
    return record


def _validate_candidate_intent_record(
    value: Any, prepared: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_effect_intent(
        value,
        prepared,
        schema="s20plus_g986n_n3u0_candidate_transfer_intent_v1",
        action="candidate-transfer",
        extra_keys={"ap_sha256", "endpoint"},
        label="candidate intent",
    )
    if record["ap_sha256"] != current_binding()["candidate_ap_sha256"]:
        raise N3U0F1Error("candidate intent artifact differs")
    validate_endpoint(record["endpoint"], "candidate intent endpoint")
    return record


def _validate_candidate_observation_record(
    value: Any, prepared: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_base_record(
        value,
        prepared,
        "s20plus_g986n_n3u0_candidate_observation_v1",
        {"banner_accepted", "android_identity", "terminal", "rollback_required"},
        "candidate observation",
    )
    if (
        type(record["banner_accepted"]) is not bool
        or record["terminal"] is not False
        or record["rollback_required"] is not True
    ):
        raise N3U0F1Error("candidate observation authority is malformed")
    identity = record["android_identity"]
    if identity is not None:
        identity = validate_identity(identity, "candidate observation identity")
        baseline = prepared["prepared_identity"]
        if (
            identity["serial_sha256"] != baseline["serial_sha256"]
            or identity["topology_sha256"] != baseline["topology_sha256"]
            or identity["boot_id_sha256"] == baseline["boot_id_sha256"]
        ):
            raise N3U0F1Error("candidate observation identity lacks continuity")
    return record


def _validate_rollback_mode_intent_record(
    value: Any, prepared: dict[str, Any], observation: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_effect_intent(
        value,
        prepared,
        schema="s20plus_g986n_n3u0_rollback_mode_reboot_intent_v1",
        action="rollback-mode-reboot",
        extra_keys={"source_identity"},
        label="rollback-mode intent",
    )
    source = validate_identity(record["source_identity"], "rollback-mode source")
    if observation["android_identity"] is None or not exact_typed_equal(
        source, observation["android_identity"]
    ):
        raise N3U0F1Error("rollback-mode source is not the candidate return")
    return record


def _validate_rollback_mode_result_record(
    value: Any, prepared: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_base_record(
        value,
        prepared,
        "s20plus_g986n_n3u0_rollback_mode_result_v1",
        {"outcome", "raw_receipt", "attempt", "replay_permitted"},
        "rollback-mode result",
    )
    if (
        record["outcome"] not in ("dispatched", "uncertain")
        or type(record["attempt"]) is not int
        or record["attempt"] != 1
        or record["replay_permitted"] is not False
    ):
        raise N3U0F1Error("rollback-mode result authority is malformed")
    validate_raw_receipt(record["raw_receipt"], "rollback-mode raw receipt")
    return record


def _validate_rollback_mode_observation_record(
    value: Any, prepared: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_base_record(
        value,
        prepared,
        "s20plus_g986n_n3u0_rollback_mode_observation_v1",
        {"endpoint", "resolution"},
        "rollback-mode observation",
    )
    if record["resolution"] != "download-observed":
        raise N3U0F1Error("rollback-mode observation resolution is malformed")
    validate_endpoint(record["endpoint"], "rollback-mode endpoint")
    return record


def _validate_physical_intent_record(
    value: Any, prepared: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_effect_intent(
        value,
        prepared,
        schema="s20plus_g986n_n3u0_physical_rollback_entry_intent_v1",
        action="physical-rollback-entry",
        extra_keys={"empty_download_baseline_sha256", "operator_attended"},
        label="physical rollback intent",
    )
    require_hex(record["empty_download_baseline_sha256"], "physical baseline")
    if record["operator_attended"] is not True:
        raise N3U0F1Error("physical rollback attendance is malformed")
    return record


def _validate_physical_arrival_record(
    value: Any, prepared: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_base_record(
        value,
        prepared,
        "s20plus_g986n_n3u0_physical_rollback_arrival_v1",
        {"endpoint", "arrival_listing_sha256", "attempt", "replay_permitted"},
        "physical rollback arrival",
    )
    validate_endpoint(record["endpoint"], "physical rollback endpoint")
    require_hex(record["arrival_listing_sha256"], "physical arrival listing")
    if (
        type(record["attempt"]) is not int
        or record["attempt"] != 1
        or record["replay_permitted"] is not False
    ):
        raise N3U0F1Error("physical rollback arrival authority is malformed")
    return record


def _validate_rollback_intent_record(
    value: Any, prepared: dict[str, Any], source_endpoint: dict[str, Any]
) -> dict[str, Any]:
    record = _validate_effect_intent(
        value,
        prepared,
        schema="s20plus_g986n_n3u0_rollback_transfer_intent_v1",
        action="rollback-transfer",
        extra_keys={"ap_sha256", "endpoint"},
        label="rollback intent",
    )
    if (
        record["ap_sha256"] != current_binding()["rollback_ap_sha256"]
        or not exact_typed_equal(record["endpoint"], source_endpoint)
    ):
        raise N3U0F1Error("rollback intent artifact or endpoint differs")
    validate_endpoint(record["endpoint"], "rollback intent endpoint")
    return record


def _validate_final_health_record(
    value: Any, prepared: dict[str, Any], run_dir: Path
) -> dict[str, Any]:
    record = _validate_base_record(
        value,
        prepared,
        "s20plus_g986n_n3u0_final_health_v1",
        {
            "identity",
            "health_receipt",
            "rollback_transfer",
            "resident_magisk_root_verified",
            "candidate_terminal",
            "healthy",
        },
        "final health",
    )
    identity = validate_identity(record["identity"], "final health identity")
    proof = validate_final_health_receipt(record["health_receipt"])
    baseline = prepared["prepared_identity"]
    if (
        record["rollback_transfer"] != "odin_transfer_completed"
        or record["resident_magisk_root_verified"] is not True
        or record["candidate_terminal"] is not False
        or record["healthy"] is not True
        or not exact_typed_equal(proof["identity"], identity)
        or identity["serial_sha256"] != baseline["serial_sha256"]
        or identity["topology_sha256"] != baseline["topology_sha256"]
        or identity["boot_id_sha256"] in _durable_boot_ids(run_dir, prepared)
    ):
        raise N3U0F1Error("final health is malformed or stale")
    return record


def _expected_terminal(
    prepared: dict[str, Any], health: dict[str, Any]
) -> dict[str, Any]:
    return {
        **_base(
            "s20plus_g986n_n3u0_terminal_v1",
            prepared["run_id"],
            prepared["binding_sha256"],
        ),
        "verdict": "PASS_S20PLUS_G986N_N3U0_RESIDENT_RESTORED",
        "candidate_attempts": 1,
        "rollback_attempts": 1,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "final_identity": health["identity"],
        "resident_magisk_root_verified": True,
    }


def validate_legal_prefix(
    run_dir: Path, *, require_active_guard: bool = True
) -> dict[str, Any]:
    prepared = read_prepared(run_dir, require_active_guard=False)
    if require_active_guard:
        require_guard(run_dir, prepared)
    names = _run_files(run_dir)
    dependencies = {
        "initial-download-result.json": {"initial-download-intent.json"},
        "initial-download-observation.json": {"initial-download-intent.json"},
        "candidate-intent.json": {"initial-download-observation.json"},
        "candidate-result.json": {"candidate-intent.json"},
        "candidate-observation.json": {"candidate-intent.json"},
        "rollback-mode-intent.json": {"candidate-observation.json"},
        "rollback-mode-result.json": {"rollback-mode-intent.json"},
        "rollback-mode-observation.json": {"rollback-mode-intent.json"},
        "physical-rollback-intent.json": {"candidate-intent.json"},
        "physical-rollback-arrival.json": {"physical-rollback-intent.json"},
        "rollback-intent.json": set(),
        "rollback-result.json": {"rollback-intent.json"},
        "final-health.json": {"rollback-result.json"},
        "terminal-result.json": {"final-health.json"},
    }
    for node, required in dependencies.items():
        if node in names and not required.issubset(names):
            raise N3U0F1Error(f"{node} lacks its predecessor")
    if "rollback-intent.json" in names:
        automatic = "rollback-mode-observation.json" in names
        physical = "physical-rollback-arrival.json" in names
        if automatic == physical:
            raise N3U0F1Error("rollback intent has an ambiguous source branch")
    if "rollback-mode-intent.json" in names and "physical-rollback-intent.json" in names:
        raise N3U0F1Error("rollback branches conflict")
    if "initial-download-intent.json" in names:
        _validate_initial_download_intent_record(
            _record(run_dir, "initial-download-intent.json"), prepared
        )
    if "initial-download-result.json" in names:
        _validate_initial_download_result_record(
            _record(run_dir, "initial-download-result.json"), prepared
        )
    initial_observation = None
    if "initial-download-observation.json" in names:
        initial_observation = _validate_initial_download_observation_record(
            _record(run_dir, "initial-download-observation.json"), prepared
        )
    candidate_observation = None
    if "candidate-intent.json" in names:
        candidate_intent = _validate_candidate_intent_record(
            _record(run_dir, "candidate-intent.json"), prepared
        )
        if initial_observation is None or not exact_typed_equal(
            candidate_intent["endpoint"], initial_observation["endpoint"]
        ):
            raise N3U0F1Error("candidate intent is not bound to initial arrival")
    if "candidate-result.json" in names:
        _validate_transfer_result_record(
            _record(run_dir, "candidate-result.json"), prepared, "candidate"
        )
    if "candidate-observation.json" in names:
        candidate_observation = _validate_candidate_observation_record(
            _record(run_dir, "candidate-observation.json"), prepared
        )
    if "rollback-mode-intent.json" in names:
        if candidate_observation is None:
            raise N3U0F1Error("rollback-mode intent lacks candidate observation")
        _validate_rollback_mode_intent_record(
            _record(run_dir, "rollback-mode-intent.json"),
            prepared,
            candidate_observation,
        )
    if "rollback-mode-result.json" in names:
        _validate_rollback_mode_result_record(
            _record(run_dir, "rollback-mode-result.json"), prepared
        )
    automatic_observation = None
    if "rollback-mode-observation.json" in names:
        automatic_observation = _validate_rollback_mode_observation_record(
            _record(run_dir, "rollback-mode-observation.json"), prepared
        )
    if "physical-rollback-intent.json" in names:
        _validate_physical_intent_record(
            _record(run_dir, "physical-rollback-intent.json"), prepared
        )
    physical_arrival = None
    if "physical-rollback-arrival.json" in names:
        physical_arrival = _validate_physical_arrival_record(
            _record(run_dir, "physical-rollback-arrival.json"), prepared
        )
    if "rollback-intent.json" in names:
        source = automatic_observation if automatic_observation is not None else physical_arrival
        if source is None:
            raise N3U0F1Error("rollback intent lacks an exact arrival source")
        _validate_rollback_intent_record(
            _record(run_dir, "rollback-intent.json"), prepared, source["endpoint"]
        )
    rollback_result = None
    if "rollback-result.json" in names:
        rollback_result = _validate_transfer_result_record(
            _record(run_dir, "rollback-result.json"), prepared, "rollback"
        )
    health = None
    if "final-health.json" in names:
        if rollback_result is None or rollback_result["classification"] != "odin_transfer_completed":
            raise N3U0F1Error("final health lacks completed rollback evidence")
        health = _validate_final_health_record(
            _record(run_dir, "final-health.json"), prepared, run_dir
        )
    if "terminal-result.json" in names:
        if health is None:
            raise N3U0F1Error("terminal result lacks final health")
        terminal = _record(run_dir, "terminal-result.json")
        if not exact_typed_equal(terminal, _expected_terminal(prepared, health)):
            raise N3U0F1Error("terminal result is malformed or mismatched")
    return prepared


def render_plan() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "active": F1_ACTIVE,
        "live_authority": False,
        "binding": current_binding(),
        "binding_sha256": binding_sha256(),
        "atomic_no_replace_journal": True,
        "strict_typed_json": True,
        "candidate_attempts": 1,
        "rollback_attempts": 1,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "candidate_terminal": False,
        "device_commands": [],
        "partition_transfers": [],
        "cli": ["--render-plan"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    arguments = parser.parse_args()
    if not arguments.render_plan:
        parser.error("the dormant H0 journal runner exposes only --render-plan")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
