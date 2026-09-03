#!/usr/bin/env python3
"""Build the fresh P3.31 boot-only resident candidate.

P3.31 reopens the consumed P3.30 host build, keeps its stock Process-v2
packaging engine, and changes only the exact resident runtime/observer source
closure plus the run/Image identity.  The resulting AP contains
``boot.img.lz4`` only and keeps the exact unchanged Magisk rollback.  This
module performs host-only validation/build work and never contacts a device or
invokes Odin.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types
from collections.abc import Mapping
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p331_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p331_resident_acm_observer as resident_observer  # noqa: E402
import s22plus_fyg8_p331_resident_exec_runtime as resident_runtime  # noqa: E402
import s22plus_fyg8_p331_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P330_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p330_stock_candidate_build.py"
P330_BUILDER_IDENTITY = {
    "size": 16_862,
    "sha256": "a1f56c5983d078df149be29937b343a63cf91a451fc1a71e5dfa977dacf68ce5",
}
P330_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p330/"
    "stock-candidate-build-v1-20260903-07"
)
P330_RESULT = P330_OUTPUT / "result.json"
P330_RESULT_IDENTITY = {
    "size": 45_820,
    "sha256": "d2186404aaab0c1472d41d93a241c0ab32119561fe0a07ca231eb0b0ca3bacf1",
}
P330_RUN_ID_HEX = "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P330_RUN_ID = bytes.fromhex(P330_RUN_ID_HEX)
P330_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b",
}
P330_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "7a730473a60cf454ba5a3df9dd992444196299b0397369531f3e171982ee8456",
}
P330_INIT_IDENTITY = {
    "size": 82_032,
    "sha256": "4d744d3def07a000d0d31f5abfa323372709d4cac0d6493d8696cb0a0e70a7a7",
}
P331_RUN_ID_HEX = resident_runtime.P331_RUN_ID_HEX
P331_RUN_ID = resident_runtime.P331_RUN_ID
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p331/"
    "stock-candidate-build-v1-20260903-03"
)
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
SCHEMA = "s22plus-fyg8-p331-stock-candidate-build-v1"
VERDICT = "PASS_P331_STOCK_CANDIDATE_BUILD_H0_RESIDENT"
STATUS = "IMPLEMENTED_H0_RESIDENT_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
AUTH_ALGORITHM = getattr(resident_runtime, "AUTH_ALGORITHM", "hmac-sha256")
PER_SESSION_RANDOM_NONCE = getattr(
    resident_runtime, "PER_SESSION_RANDOM_NONCE", True
)


class AuditError(RuntimeError):
    """The exact P3.30 predecessor or fresh P3.31 closure differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _stable(
    path: Path,
    label: str,
    maximum: int,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (expected is not None and identity(payload) != dict(expected))
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise AuditError(f"{label} has duplicate key {key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} is not an object")
    return value


def _load_p330_builder() -> types.ModuleType:
    payload = _stable(
        P330_BUILDER_SOURCE,
        "P3.30 builder",
        2 << 20,
        P330_BUILDER_IDENTITY,
        nlink=1,
    )
    module = types.ModuleType("s22plus_fyg8_p330_builder_bound_for_p331")
    module.__file__ = str(P330_BUILDER_SOURCE)
    module.__package__ = ""
    previous = sys.modules.get(module.__name__)
    sys.modules[module.__name__] = module
    try:
        exec(  # noqa: S102 - exact, hash-pinned predecessor source loading
            compile(payload, str(P330_BUILDER_SOURCE), "exec", dont_inherit=True),
            module.__dict__,
        )
    except Exception as exc:
        raise AuditError("P3.30 builder failed to load") from exc
    finally:
        if previous is None:
            sys.modules.pop(module.__name__, None)
        else:
            sys.modules[module.__name__] = previous
    if getattr(module, "P330_RUN_ID_HEX", None) != P330_RUN_ID_HEX:
        raise AuditError("P3.30 builder identity differs")
    return module


def _source_identity(path: Path, label: str) -> dict[str, Any]:
    return identity(_stable(path, label, 2 << 20, nlink=1))


RUNTIME_SOURCE = REVALIDATION / "s22plus_fyg8_p331_resident_exec_runtime.py"
OBSERVER_SOURCE = REVALIDATION / "s22plus_fyg8_p331_resident_acm_observer.py"
# These are derived from the source bytes at import time.  They are not
# guessed constants: a changed concurrent runtime/observer fails the stable
# source read and requires a fresh packaging process.
RUNTIME_SOURCE_IDENTITY = _source_identity(RUNTIME_SOURCE, "P3.31 runtime source")
OBSERVER_SOURCE_IDENTITY = _source_identity(OBSERVER_SOURCE, "P3.31 observer source")
ADAPTER_SOURCE_IDENTITY = _source_identity(
    adapter.P331_ADAPTER_SOURCE, "P3.31 adapter source"
)
ARTIFACT_SOURCE_IDENTITY = _source_identity(
    artifact.P331_ARTIFACT_SOURCE, "P3.31 artifact source"
)


_P330 = _load_p330_builder()
_P328 = _P330._P328
_ENGINE = _P330._ENGINE
_INHERITED_LOAD_PACKAGER = _P328._load_packager


def _modules(root: types.ModuleType) -> list[types.ModuleType]:
    result: list[types.ModuleType] = []
    pending = [root]
    while pending:
        module = pending.pop()
        if module in result:
            continue
        result.append(module)
        for value in vars(module).values():
            if isinstance(value, types.ModuleType) and value not in result:
                pending.append(value)
    return result


def _rebind_modules() -> None:
    """Bind the inherited engine to P3.31 without changing predecessor bytes."""

    for module in _modules(_P330):
        for name in (
            "P322_RUN_ID",
            "P323_RUN_ID",
            "P324_RUN_ID",
            "P325_RUN_ID",
            "P326_RUN_ID",
            "P327_RUN_ID",
            "P328_RUN_ID",
            "P329_RUN_ID",
            "P330_RUN_ID",
        ):
            if hasattr(module, name):
                setattr(module, name, P331_RUN_ID)
        for name in (
            "P322_RUN_ID_HEX",
            "P323_RUN_ID_HEX",
            "P324_RUN_ID_HEX",
            "P325_RUN_ID_HEX",
            "P326_RUN_ID_HEX",
            "P327_RUN_ID_HEX",
            "P328_RUN_ID_HEX",
            "P329_RUN_ID_HEX",
            "P330_RUN_ID_HEX",
        ):
            if hasattr(module, name):
                setattr(module, name, P331_RUN_ID_HEX)
        for name, value in (
            ("artifact", artifact),
            ("adapter", adapter),
            ("framed_runtime", resident_runtime),
            ("resident_runtime", resident_runtime),
            ("framed_observer", resident_observer),
            ("resident_observer", resident_observer),
        ):
            if hasattr(module, name):
                setattr(module, name, value)

    # The top-level predecessor module is retained only as an exact-loaded
    # engine.  Its public identities are rebound to the fresh P3.31 lane.
    _P330.artifact = artifact
    _P330.adapter = adapter
    _P330.framed_runtime = resident_runtime
    _P330.framed_observer = resident_observer
    _P330.P330_RUN_ID = P331_RUN_ID
    _P330.P330_RUN_ID_HEX = P331_RUN_ID_HEX
    _P330.P329_RUN_ID = P331_RUN_ID
    _P330.P329_RUN_ID_HEX = P331_RUN_ID_HEX
    _P330.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
    _P330.DEFAULT_AUTH_KEY_PATH = DEFAULT_AUTH_KEY_PATH
    _P330.SCHEMA = SCHEMA
    _P330.VERDICT = VERDICT
    _P330.STATUS = STATUS

    _P328.artifact = artifact
    _P328.adapter = adapter
    _P328.framed_runtime = resident_runtime
    _P328.framed_observer = resident_observer
    _P328.P328_RUN_ID = P331_RUN_ID
    _P328.P328_RUN_ID_HEX = P331_RUN_ID_HEX
    _P328.P328_ARTIFACT_SOURCE = artifact.P331_ARTIFACT_SOURCE
    _P328.P328_ADAPTER_SOURCE = adapter.P331_ADAPTER_SOURCE
    _P328.P328_RUNTIME_SOURCE = RUNTIME_SOURCE
    _P328.P328_RUNTIME_IDENTITY = dict(RUNTIME_SOURCE_IDENTITY)
    _P328.P328_OBSERVER_SOURCE = OBSERVER_SOURCE
    _P328.P328_OBSERVER_IDENTITY = dict(OBSERVER_SOURCE_IDENTITY)
    _P328.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
    _P328.DEFAULT_AUTH_KEY_PATH = DEFAULT_AUTH_KEY_PATH
    _P328.SCHEMA = SCHEMA
    _P328.VERDICT = VERDICT
    _P328.STATUS = STATUS
    _P328._RUNTIME_LOAD_ERROR = None
    _P328._OBSERVER_LOAD_ERROR = None

    _ENGINE.artifact = artifact
    _ENGINE.adapter = adapter
    _ENGINE.P321_OUTPUT = P330_OUTPUT
    _ENGINE.P322_RUN_ID = P331_RUN_ID
    _ENGINE.P322_RUN_ID_HEX = P331_RUN_ID_HEX
    _ENGINE.P322_ARTIFACT_SOURCE = artifact.P331_ARTIFACT_SOURCE
    _ENGINE.P322_REPAIR_SOURCE = RUNTIME_SOURCE
    _ENGINE.P322_ADAPTER_SOURCE = adapter.P331_ADAPTER_SOURCE
    _ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
    _ENGINE.SCHEMA = SCHEMA
    _ENGINE.VERDICT = VERDICT
    _ENGINE.STATUS = STATUS
    _ENGINE.TARGET = TARGET


_rebind_modules()


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    """Read the final P3.30 result once and treat it as consumed input."""

    payload = _stable(
        P330_RESULT,
        "P3.30 final result",
        4 << 20,
        P330_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    value = _strict_json(payload, "P3.30 final result")
    if (
        value.get("schema") != "s22plus-fyg8-p330-stock-candidate-build-v1"
        or value.get("run_id_hex") != P330_RUN_ID_HEX
        or value.get("target") != TARGET
        or value.get("scope", {}).get("host_only") is not True
        or value.get("scope", {}).get("device_contact") is not False
    ):
        raise AuditError("P3.30 predecessor header or scope differs")
    candidate = value.get("phase2", {}).get("candidate")
    if (
        not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("one_boot_img_lz4_member") is not True
        or candidate.get("a", {}).get("ap_tar_md5") != P330_AP_IDENTITY
        or candidate.get("a", {}).get("package", {}).get("members")
        != ["boot.img.lz4"]
    ):
        raise AuditError("P3.30 predecessor candidate differs")
    source_closure = value.get("source_closure")
    if not isinstance(source_closure, dict) or len(source_closure) != 12:
        raise AuditError("P3.30 predecessor source closure differs")
    builder_source = _stable(
        P330_BUILDER_SOURCE,
        "P3.30 builder source",
        2 << 20,
        P330_BUILDER_IDENTITY,
        nlink=1,
    )
    return value, payload, builder_source


def _current_sources() -> dict[str, bytes]:
    paths = {
        # The inherited packager names these keys p328-prefixed.  The values
        # are exact P3.31 wrappers, so the compatibility spelling does not
        # hide the new runtime/observer source closure.
        "p328_stock_candidate_build.py": SELF_SOURCE,
        "p328_artifact_identity.py": artifact.P331_ARTIFACT_SOURCE,
        "p328_stock_process_v2_adapter.py": adapter.P331_ADAPTER_SOURCE,
        "p328_authenticated_exec_runtime.py": RUNTIME_SOURCE,
        "p328_authenticated_acm_observer.py": OBSERVER_SOURCE,
    }
    return {
        name: _stable(path, f"P3.31 source {name}", 2 << 20, nlink=1)
        for name, path in paths.items()
    }


def _active_auth_key() -> bytes:
    key = getattr(_P328, "_ACTIVE_AUTH_KEY", None)
    if type(key) is not bytes or len(key) != artifact.AUTH_KEY_SIZE:
        raise AuditError("P3.31 auth key is not bound before runtime transform")
    return key


def _copy_source_closure(
    output_root: Path, predecessor: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    source_root = output_root / "stock-sources"
    _ENGINE.p321._mkdir(source_root)
    expected = predecessor.get("source_closure")
    if not isinstance(expected, dict) or len(expected) != 12:
        raise AuditError("P3.30 source closure differs")
    receipts: dict[str, dict[str, Any]] = {}
    runtime_receipt: dict[str, Any] | None = None
    runtime_name = "s22plus_fyg8_p290_e3_runtime.inc.c"
    auth_key = _active_auth_key()
    for name, expected_identity in sorted(expected.items()):
        before = _stable(
            P330_OUTPUT / "stock-sources" / name,
            f"P3.30 source {name}",
            2 << 20,
            expected_identity,
            mode=0o400,
            nlink=1,
        )
        after = before
        if name == runtime_name:
            try:
                transformed = resident_runtime.transform_artifacts(
                    {resident_runtime.RUNTIME_KEY: before}, auth_key
                )
                after = transformed[resident_runtime.RUNTIME_KEY]
                runtime_receipt = resident_runtime.validate_transform(
                    before,
                    after,
                    auth_key_sha256=hashlib.sha256(auth_key).hexdigest(),
                )
            except Exception as exc:
                raise AuditError(f"P3.31 resident runtime transform failed: {exc}") from exc
            runtime_receipt.update(
                {
                    "before_identity": identity(before),
                    "after_identity": identity(after),
                    "auth_key": artifact.validate_auth_key(auth_key),
                    "auth_key_path_published": False,
                }
            )
            runtime_receipt.pop("auth_key_path", None)
            runtime_receipt.pop("key_path", None)
        _ENGINE.p321._write_exclusive(source_root / name, after)
        receipts[name] = identity(after)
    if runtime_receipt is None:
        raise AuditError("P3.30 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, runtime_receipt


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, packager, source = _INHERITED_LOAD_PACKAGER()
    packager.RUN_ID = P331_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    return helper, packager, source


class _RuntimeCompat:
    RuntimeRepairError = ValueError

    @staticmethod
    def transform_runtime_include(value: bytes) -> bytes:
        return resident_runtime.transform_runtime_include(value, _active_auth_key())

    @staticmethod
    def validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
        key = _active_auth_key()
        transformed = resident_runtime.transform_runtime_include(before, key)
        if type(after) is not bytes or transformed != after:
            raise AuditError("P3.31 transformed runtime is not exact")
        receipt = resident_runtime.validate_transform(
            before,
            after,
            auth_key_sha256=hashlib.sha256(key).hexdigest(),
        )
        receipt.update(
            {
                "auth_key": artifact.validate_auth_key(key),
                "auth_key_path_published": False,
                "runtime_contract": resident_runtime.CONTRACT_ID,
            }
        )
        receipt.pop("auth_key_path", None)
        receipt.pop("key_path", None)
        return receipt


def _auth_metadata(result: Mapping[str, Any]) -> dict[str, Any]:
    for value in (
        result.get("framed_exec", {}).get("auth_key")
        if isinstance(result.get("framed_exec"), Mapping)
        else None,
        result.get("authentication", {}).get("key")
        if isinstance(result.get("authentication"), Mapping)
        else None,
    ):
        if isinstance(value, Mapping) and value.get("size") == artifact.AUTH_KEY_SIZE:
            return {"size": value["size"], "sha256": value["sha256"]}
    try:
        return artifact.validate_auth_key(_active_auth_key())
    except AuditError:
        raise
    except Exception as exc:
        raise AuditError("P3.31 auth metadata is unavailable") from exc


def _validate_published_source_receipts(output_root: Path) -> None:
    """Reject a result produced before any wrapper source drifted."""

    raw = _stable(
        output_root / "result.json",
        "P3.31 published result",
        4 << 20,
        mode=0o400,
        nlink=1,
    )
    stored = _strict_json(raw, "P3.31 published result")
    receipts = stored.get("helper_sources")
    if not isinstance(receipts, dict):
        raise AuditError("P3.31 published helper source receipts are absent")
    for name, payload in _current_sources().items():
        if receipts.get(name) != identity(payload):
            raise AuditError(f"P3.31 output source identity differs: {name}")


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuditError("P3.31 result is not an object")
    result = copy.deepcopy(value)
    phase2 = result.get("phase2")
    candidate = phase2.get("candidate") if isinstance(phase2, dict) else None
    if not isinstance(candidate, dict):
        raise AuditError("P3.31 candidate projection is absent")
    if candidate.get("a") != candidate.get("b"):
        raise AuditError("P3.31 A/B candidate differs")
    ap = candidate.get("a", {}).get("ap_tar_md5")
    if not isinstance(ap, dict) or ap == P330_AP_IDENTITY:
        raise AuditError("P3.31 candidate repeats the consumed P3.30 AP")
    candidate["differs_from_consumed_p330"] = True
    candidate["differs_from_consumed_p329"] = True
    for label in ("a", "b"):
        package = candidate.get(label, {}).get("package")
        if not isinstance(package, dict):
            raise AuditError("P3.31 package projection is absent")
        package["schema"] = "s22plus_fyg8_p331_boot_only_resident_package_v1"
        package["verdict"] = "PASS_P331_DETERMINISTIC_BOOT_ONLY_RESIDENT_PACKAGE_H0"

    result["schema"] = SCHEMA
    result["verdict"] = VERDICT
    result["status"] = STATUS
    result["target"] = TARGET
    result["run_id_hex"] = P331_RUN_ID_HEX
    lineage = result.setdefault("lineage", {})
    lineage.update(
        {
            "construction_base_run_id": P330_RUN_ID_HEX,
            "predecessor_run_id": P330_RUN_ID_HEX,
            "predecessor_result": P330_RESULT_IDENTITY,
            "predecessor_ap": P330_AP_IDENTITY,
            "fresh_run_id": P331_RUN_ID_HEX,
        }
    )
    preservation = result.setdefault("preservation", {})
    preservation.update(
        {
            "p330_consumed_candidate_distinct": True,
            "p330_source_closure_reopened": True,
            "p330_authenticated_protocol_reused": True,
            "p330_auth_key_reused": True,
            "p330_resident_runtime_replaced": True,
            "resident_loop_bounded": True,
            "resident_sessions": resident_runtime.MAX_SESSIONS,
            "resident_reconnects": resident_runtime.MAX_RECONNECTS,
            "fixed_heartbeat_only": True,
            "observer_resident_host_only": True,
            "diagnostic_provider_widening": False,
            "rollback_untouched": True,
        }
    )
    result["compatibility_labels"] = {
        "engine": "P330 exact-loaded",
        "source_keys": "p328-prefixed compatibility keys contain P331 wrapper bytes",
        "wire_namespace": "S328/P331 resident framing retained",
        "presentation_only": True,
    }

    auth_meta = _auth_metadata(result)
    commands = tuple(resident_runtime.DEFAULT_COMMANDS)
    result["framed_exec"] = {
        "runtime_contract": resident_runtime.CONTRACT_ID,
        "observer_contract": resident_observer.CONTRACT_ID,
        "wire_magic": resident_runtime.FRAME_MAGIC.decode("ascii"),
        "frame_header_size": resident_runtime.FRAME_HEADER_SIZE,
        "commands": [identity(item) for item in commands],
        "proof_command_count": len(commands),
        "max_commands": resident_runtime.MAX_COMMANDS,
        "caller_selected_command": False,
        "command_timeout_sec": resident_runtime.COMMAND_TIMEOUT_SEC,
        "max_output_bytes": resident_runtime.MAX_OUTPUT_BYTES,
        "busybox_ash_child": True,
        "child_kill_and_reap": True,
        "interactive_pty": False,
        "authenticated": True,
        "authentication_required": True,
        "auth_algorithm": AUTH_ALGORITHM,
        "per_session_random_nonce": PER_SESSION_RANDOM_NONCE,
        "auth_tag_size": resident_runtime.AUTH_TAG_SIZE,
        "auth_key_schema": artifact.AUTH_KEY_SCHEMA,
        "auth_key": auth_meta,
        "auth_key_path_published": False,
        "preauth_diagnostic_frame": resident_runtime.DIAGNOSTIC_FRAME_TYPE,
        "rng_eagain_retry_limit": resident_runtime.RNG_EAGAIN_RETRY_LIMIT,
        "diagnostics_non_authoritative": True,
        "fixed_heartbeat_only": True,
        "resident_session_cap": resident_runtime.MAX_SESSIONS,
        "resident_reconnect_cap": resident_runtime.MAX_RECONNECTS,
    }
    result["authentication"] = {
        "required": True,
        "scheme": "auth-key-v1",
        "key": auth_meta,
        "path_published": False,
    }
    result["resident"] = {
        "runtime_contract": resident_runtime.CONTRACT_ID,
        "observer_contract": resident_observer.CONTRACT_ID,
        "session_cap": resident_runtime.MAX_SESSIONS,
        "reconnect_cap": resident_runtime.MAX_RECONNECTS,
        "session_timeout_sec": resident_runtime.RESIDENT_SESSION_TIMEOUT_SEC,
        "command": identity(resident_runtime.HEARTBEAT_COMMAND),
        "output": identity(resident_runtime.HEARTBEAT_OUTPUT),
        "fixed_heartbeat_only": True,
        "caller_selected_command": False,
        "interactive_pty": False,
        "persistent_state": False,
        "host_only_observer": True,
    }
    result["limitations"] = [
        "P331 packages a bounded two-session resident loop with one fixed heartbeat command.",
        "The P330 authenticated framing, HMAC domains, diagnostics, and private key are reused.",
        "A reconnect is bounded to one fresh session; no failed session is replayed.",
        "Only the boot partition is transferred and exact Magisk rollback remains mandatory.",
        "No device contact, approval, D0, D1, F1, recovery, replay, or live authority is created by this host build.",
    ]
    repair = result.get("lineage", {}).get("runtime_repair")
    if isinstance(repair, dict):
        repair.pop("auth_key_path", None)
        repair.pop("key_path", None)
        repair["auth_key"] = auth_meta
        repair["auth_key_path_published"] = False
        repair["run_id_hex"] = P331_RUN_ID_HEX
        repair["runtime_contract"] = resident_runtime.CONTRACT_ID
    return result


_ENGINE._predecessor = _predecessor
_ENGINE._current_sources = _current_sources
_ENGINE._copy_source_closure = _copy_source_closure
_ENGINE._load_packager = _load_packager
_ENGINE.repair = _RuntimeCompat
_ENGINE._json_bytes = lambda value: _P328._json_bytes(_normalize_result(value))
_P328._predecessor = _predecessor
_P328._current_sources = _current_sources
_P328._copy_source_closure = _copy_source_closure
_P328._load_packager = _load_packager
_P328._normalize_result = _normalize_result


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    auth_key: Path | str | None = None,
    audit_only: bool = False,
) -> dict[str, Any]:
    output_root = output_root.absolute()
    _predecessor()
    if audit_only:
        return audit_existing(output_root, auth_key=auth_key)
    try:
        return _P328.build_result(
            output_root,
            auth_key=DEFAULT_AUTH_KEY_PATH if auth_key is None else auth_key,
            audit_only=False,
        )
    except Exception as exc:
        if isinstance(exc, AuditError):
            raise
        raise AuditError(str(exc)) from exc


def audit_existing(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    auth_key: Path | str | None = None,
) -> dict[str, Any]:
    _predecessor()
    _validate_published_source_receipts(output_root)
    try:
        return _P328.audit_existing(
            output_root,
            auth_key=DEFAULT_AUTH_KEY_PATH if auth_key is None else auth_key,
        )
    except Exception as exc:
        if isinstance(exc, AuditError):
            raise
        raise AuditError(str(exc)) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--auth-key", type=Path, default=DEFAULT_AUTH_KEY_PATH)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    key = args.auth_key if args.auth_key.is_absolute() else ROOT / args.auth_key
    try:
        result = build_result(output, auth_key=key, audit_only=args.audit_only)
    except (AuditError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": result["verdict"],
                "output": str(output),
                "result": identity((output / "result.json").read_bytes()),
                "created": not args.audit_only,
                "device_contact": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
