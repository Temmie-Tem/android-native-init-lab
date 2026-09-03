#!/usr/bin/env python3
"""Build the fresh P3.32 boot-only logical-resident candidate.

P3.32 is a host-only successor of the consumed P3.31 candidate.  The exact
P3.31 packaging engine is loaded from pinned source bytes, while the final
source closure deliberately starts from the exact P3.30 runtime include and
applies the P3.32 same-tty logical-session transform.  P3.31 resident-loop
bytes are lineage evidence only and are never copied into the candidate.

The resulting A/B APs contain ``boot.img.lz4`` only and retain the exact
stock Magisk rollback.  This module never contacts a device or invokes Odin.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
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

import s22plus_fyg8_p332_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p332_logical_resident_acm_observer as resident_observer  # noqa: E402
import s22plus_fyg8_p332_logical_resident_exec_runtime as resident_runtime  # noqa: E402
import s22plus_fyg8_p332_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P331_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p331_stock_candidate_build.py"
P331_BUILDER_IDENTITY = {
    "size": 27_554,
    "sha256": "b91ffb3fd94dc31387f806df3e8992c365c47b983ad2c46ea9b8325c642992a2",
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
P330_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p330_stock_candidate_build.py"
P330_BUILDER_IDENTITY = {
    "size": 16_862,
    "sha256": "a1f56c5983d078df149be29937b343a63cf91a451fc1a71e5dfa977dacf68ce5",
}

P331_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p331/"
    "stock-candidate-build-v1-20260903-03"
)
P331_RESULT = P331_OUTPUT / "result.json"
P331_RESULT_IDENTITY = {
    "size": 46_253,
    "sha256": "39c4ae4d6c156f3cac1eed5037dd5172e5dafedf2f24238de431f4e32ceb35d4",
}
P331_RESIDENT_RUNTIME_SOURCE_IDENTITY = {
    "size": 18_203,
    "sha256": "b146a1b9c46fc5db520c20d8c250dcc565c9882723ba82398fb8d1cd60f69750",
}
P331_RESIDENT_OBSERVER_SOURCE_IDENTITY = {
    "size": 25_273,
    "sha256": "59d82f28dd50d8a1e39b4b267667bb4a56310acd71667b4df96499d43cdd558d",
}

P330_RUN_ID_HEX = "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b"
P330_RUN_ID = bytes.fromhex(P330_RUN_ID_HEX)
P331_RUN_ID_HEX = "c331f1e0a90b5e6d7c8a9b0c1d2e3f9b"
P331_RUN_ID = bytes.fromhex(P331_RUN_ID_HEX)
P332_RUN_ID_HEX = "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b"
P332_RUN_ID = bytes.fromhex(P332_RUN_ID_HEX)

P330_AP_IDENTITY = dict(artifact.P330_AP_IDENTITY)
P331_AP_IDENTITY = dict(artifact.P331_AP_IDENTITY)
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p332/"
    "stock-candidate-build-v1-20260903-10"
)
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
SCHEMA = "s22plus-fyg8-p332-stock-candidate-build-v1"
VERDICT = "PASS_P332_STOCK_CANDIDATE_BUILD_H0_LOGICAL_RESIDENT"
STATUS = "IMPLEMENTED_H0_LOGICAL_RESIDENT_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
AUTH_ALGORITHM = getattr(resident_runtime, "AUTH_ALGORITHM", "hmac-sha256")
PER_SESSION_RANDOM_NONCE = getattr(resident_runtime, "PER_SESSION_RANDOM_NONCE", True)


class AuditError(RuntimeError):
    """The exact P3.30/P3.31 lineage or fresh P3.32 closure differs."""


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


def _snapshot_legacy_modules() -> dict[str, dict[str, Any]]:
    """Capture imported predecessor modules before exact-source loading.

    The historical P331 builder's recursive compatibility rebind walks
    module-valued globals and can reach an already-imported P330 runtime.
    Keep that legacy process-global state isolated from callers that imported
    the P330/P331 helpers for independent tests or evidence decoding.
    """
    snapshot: dict[str, dict[str, Any]] = {}
    for name, module in tuple(sys.modules.items()):
        if not (
            name.startswith("s22plus_fyg8_p330_")
            or name.startswith("s22plus_fyg8_p331_")
        ) or not isinstance(module, types.ModuleType):
            continue
        values: dict[str, Any] = {}
        for key, value in vars(module).items():
            values[key] = value
            if callable(value) and hasattr(value, "__kwdefaults__"):
                values[f"__kwdefaults__:{key}"] = getattr(value, "__kwdefaults__", None)
        snapshot[name] = values
    return snapshot


def _restore_legacy_modules(snapshot: dict[str, dict[str, Any]]) -> None:
    for name, values in snapshot.items():
        module = sys.modules.get(name)
        if not isinstance(module, types.ModuleType):
            continue
        original_keys = {
            key for key in values if not key.startswith("__kwdefaults__:")
        }
        for key in tuple(vars(module)):
            if key not in original_keys:
                try:
                    delattr(module, key)
                except AttributeError:
                    pass
        for key, value in values.items():
            if key.startswith("__kwdefaults__:"):
                function = getattr(module, key.split(":", 1)[1], None)
                if callable(function):
                    function.__kwdefaults__ = value
            else:
                setattr(module, key, value)
    for name in tuple(sys.modules):
        if (
            name.startswith("s22plus_fyg8_p330_")
            or name.startswith("s22plus_fyg8_p331_")
        ) and name not in snapshot:
            sys.modules.pop(name, None)


def _load_p331_builder() -> types.ModuleType:
    payload = _stable(
        P331_BUILDER_SOURCE,
        "P3.31 builder",
        2 << 20,
        P331_BUILDER_IDENTITY,
        nlink=1,
    )
    module = types.ModuleType("s22plus_fyg8_p331_builder_bound_for_p332")
    module.__file__ = str(P331_BUILDER_SOURCE)
    module.__package__ = ""
    previous = sys.modules.get(module.__name__)
    sys.modules[module.__name__] = module
    try:
        exec(  # noqa: S102 - exact, hash-pinned predecessor source loading
            compile(payload, str(P331_BUILDER_SOURCE), "exec", dont_inherit=True),
            module.__dict__,
        )
    except Exception as exc:
        raise AuditError("P3.31 builder failed to load") from exc
    finally:
        if previous is None:
            sys.modules.pop(module.__name__, None)
        else:
            sys.modules[module.__name__] = previous
    if getattr(module, "P331_RUN_ID_HEX", None) != P331_RUN_ID_HEX:
        raise AuditError("P3.31 builder identity differs")
    return module


_LEGACY_MODULE_SNAPSHOT = _snapshot_legacy_modules()
try:
    _P331 = _load_p331_builder()
finally:
    _restore_legacy_modules(_LEGACY_MODULE_SNAPSHOT)
_P328 = _P331._P328
_ENGINE = _P331._ENGINE
_INHERITED_LOAD_PACKAGER = _P331._INHERITED_LOAD_PACKAGER


def _modules(root: types.ModuleType) -> list[types.ModuleType]:
    result: list[types.ModuleType] = []
    pending = [root]
    while pending:
        module = pending.pop()
        if module in result:
            continue
        result.append(module)
        for name, value in vars(module).items():
            if name.startswith("_P") and isinstance(value, types.ModuleType):
                pending.append(value)
    return result


def _rebind_engine() -> None:
    """Bind the exact-loaded P3.31 engine to the fresh P3.32 closure."""

    # The P331 builder itself is retained as a source receipt only.  Its
    # delegated P330/P328 engine receives the fresh artifact/adapter/runtime
    # objects for this build, while the P330 and P331 IDs remain explicit
    # lineage fields in this module and in the final result.
    for module in _modules(_P331):
        for name, value in tuple(vars(module).items()):
            if value == P331_RUN_ID:
                setattr(module, name, P332_RUN_ID)
            elif value == P331_RUN_ID_HEX:
                setattr(module, name, P332_RUN_ID_HEX)
            elif callable(value) and getattr(value, "__kwdefaults__", None):
                defaults = dict(value.__kwdefaults__)
                changed = False
                for key, current in tuple(defaults.items()):
                    if current == P331_RUN_ID:
                        defaults[key] = P332_RUN_ID
                        changed = True
                    elif current == P331_RUN_ID_HEX:
                        defaults[key] = P332_RUN_ID_HEX
                        changed = True
                if changed:
                    value.__kwdefaults__ = defaults

    for module in (_P331, _P328, _ENGINE):
        for name, value in {
            "artifact": artifact,
            "adapter": adapter,
            "framed_runtime": resident_runtime,
            "resident_runtime": resident_runtime,
            "framed_observer": resident_observer,
            "resident_observer": resident_observer,
            "P328_RUN_ID": P332_RUN_ID,
            "P328_RUN_ID_HEX": P332_RUN_ID_HEX,
            "P330_RUN_ID": P332_RUN_ID,
            "P330_RUN_ID_HEX": P332_RUN_ID_HEX,
            "P331_RUN_ID": P332_RUN_ID,
            "P331_RUN_ID_HEX": P332_RUN_ID_HEX,
            "DEFAULT_OUTPUT_ROOT": DEFAULT_OUTPUT_ROOT,
            "DEFAULT_AUTH_KEY_PATH": DEFAULT_AUTH_KEY_PATH,
            "SCHEMA": SCHEMA,
            "VERDICT": VERDICT,
            "STATUS": STATUS,
            "TARGET": TARGET,
        }.items():
            if hasattr(module, name):
                setattr(module, name, value)

    # _P328._require_runtime uses compatibility P328 names even though the
    # public runtime is P332.  The P332 runtime must expose those aliases; the
    # fallback keeps the adapter fail-closed if a source omits one.
    _P328.P328_RUN_ID = P332_RUN_ID
    _P328.P328_RUN_ID_HEX = P332_RUN_ID_HEX
    _P328.framed_runtime = resident_runtime
    _P328.framed_observer = resident_observer
    _P328.artifact = artifact
    _P328.adapter = adapter
    _P328.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
    _P328.DEFAULT_AUTH_KEY_PATH = DEFAULT_AUTH_KEY_PATH
    _P328.SCHEMA = SCHEMA
    _P328.VERDICT = VERDICT
    _P328.STATUS = STATUS

    _ENGINE.artifact = artifact
    _ENGINE.adapter = adapter
    _ENGINE.P321_OUTPUT = P330_OUTPUT
    _ENGINE.P322_RUN_ID = P332_RUN_ID
    _ENGINE.P322_RUN_ID_HEX = P332_RUN_ID_HEX
    _ENGINE.P322_ARTIFACT_SOURCE = artifact.P332_ARTIFACT_SOURCE
    _ENGINE.P322_REPAIR_SOURCE = RUNTIME_SOURCE
    _ENGINE.P322_ADAPTER_SOURCE = adapter.P332_ADAPTER_SOURCE
    _ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
    _ENGINE.SCHEMA = SCHEMA
    _ENGINE.VERDICT = VERDICT
    _ENGINE.STATUS = STATUS
    _ENGINE.TARGET = TARGET


RUNTIME_SOURCE = REVALIDATION / "s22plus_fyg8_p332_logical_resident_exec_runtime.py"
OBSERVER_SOURCE = REVALIDATION / "s22plus_fyg8_p332_logical_resident_acm_observer.py"


def _source_identity(path: Path, label: str) -> dict[str, Any]:
    return identity(_stable(path, label, 2 << 20, nlink=1))


# These reads intentionally happen after the paths are defined so importing
# the skeleton before the concurrent runtime/observer exists fails closed at
# the source seam rather than silently constructing an incomplete candidate.
RUNTIME_SOURCE_IDENTITY = _source_identity(RUNTIME_SOURCE, "P3.32 runtime source")
OBSERVER_SOURCE_IDENTITY = _source_identity(OBSERVER_SOURCE, "P3.32 observer source")
ADAPTER_SOURCE_IDENTITY = _source_identity(
    adapter.P332_ADAPTER_SOURCE, "P3.32 adapter source"
)
ARTIFACT_SOURCE_IDENTITY = _source_identity(
    artifact.P332_ARTIFACT_SOURCE, "P3.32 artifact source"
)

_rebind_engine()


def _read_result(path: Path, label: str, expected: Mapping[str, Any]) -> tuple[dict[str, Any], bytes]:
    payload = _stable(path, label, 4 << 20, expected, mode=0o400, nlink=1)
    return _strict_json(payload, label), payload


def _validate_lineage_result(
    value: Mapping[str, Any],
    *,
    run_id: str,
    schema: str,
    ap_identity: Mapping[str, Any],
    predecessor_run_id: str,
    predecessor_result: Mapping[str, Any],
) -> None:
    if (
        value.get("schema") != schema
        or value.get("run_id_hex") != run_id
        or value.get("target") != TARGET
        or value.get("scope", {}).get("host_only") is not True
        or value.get("scope", {}).get("device_contact") is not False
    ):
        raise AuditError("predecessor result header or scope differs")
    candidate = value.get("phase2", {}).get("candidate")
    if (
        not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("one_boot_img_lz4_member") is not True
        or candidate.get("a", {}).get("ap_tar_md5") != dict(ap_identity)
        or candidate.get("a", {}).get("package", {}).get("members") != ["boot.img.lz4"]
    ):
        raise AuditError("predecessor candidate differs")
    lineage = value.get("lineage")
    if not isinstance(lineage, dict):
        raise AuditError("predecessor lineage is absent")
    if lineage.get("predecessor_run_id") != predecessor_run_id:
        raise AuditError("predecessor chain run ID differs")
    if lineage.get("predecessor_result") != dict(predecessor_result):
        raise AuditError("predecessor chain result identity differs")
    if not isinstance(value.get("source_closure"), dict) or len(value["source_closure"]) != 12:
        raise AuditError("predecessor source closure differs")


def _predecessor_p330() -> tuple[dict[str, Any], bytes, bytes]:
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
        or candidate.get("a", {}).get("package", {}).get("members") != ["boot.img.lz4"]
    ):
        raise AuditError("P3.30 predecessor candidate differs")
    source = _stable(
        P330_BUILDER_SOURCE,
        "P3.30 builder source",
        2 << 20,
        P330_BUILDER_IDENTITY,
        nlink=1,
    )
    if not isinstance(value.get("source_closure"), dict) or len(value["source_closure"]) != 12:
        raise AuditError("P3.30 source closure differs")
    for name, expected in sorted(value["source_closure"].items()):
        _stable(
            P330_OUTPUT / "stock-sources" / name,
            f"P3.30 predecessor source {name}",
            2 << 20,
            expected,
            mode=0o400,
            nlink=1,
        )
    for label in ("a", "b"):
        candidate_path = P330_OUTPUT / f"candidate-{label}/odin4/AP.tar.md5"
        _stable(candidate_path, f"P3.30 candidate {label.upper()} AP", 128 << 20, P330_AP_IDENTITY, nlink=1)
    return value, payload, source


def _predecessor_p331() -> tuple[dict[str, Any], bytes]:
    payload = _stable(
        P331_RESULT,
        "P3.31 final result",
        4 << 20,
        P331_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    value = _strict_json(payload, "P3.31 final result")
    _validate_lineage_result(
        value,
        run_id=P331_RUN_ID_HEX,
        schema="s22plus-fyg8-p331-stock-candidate-build-v1",
        ap_identity=P331_AP_IDENTITY,
        predecessor_run_id=P330_RUN_ID_HEX,
        predecessor_result=P330_RESULT_IDENTITY,
    )
    lineage = value["lineage"]
    if lineage.get("predecessor_ap") != P330_AP_IDENTITY:
        raise AuditError("P3.31 predecessor AP identity differs")
    for name, expected in sorted(value["source_closure"].items()):
        _stable(
            P331_OUTPUT / "stock-sources" / name,
            f"P3.31 predecessor source {name}",
            2 << 20,
            expected,
            mode=0o400,
            nlink=1,
        )
    for label in ("a", "b"):
        candidate_path = P331_OUTPUT / f"candidate-{label}/odin4/AP.tar.md5"
        _stable(candidate_path, f"P3.31 candidate {label.upper()} AP", 128 << 20, P331_AP_IDENTITY, nlink=1)
    return value, payload


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    """Return P330's source base after proving both consumed lineages."""
    p330, payload, source = _predecessor_p330()
    _predecessor_p331()
    return p330, payload, source


def _audit_predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    """Use P330's source base with P331's result receipt during reopen.

    The inherited audit compares the stored ``predecessor_result`` receipt
    with the returned payload.  P332's immediate predecessor is P331, while
    its rebuild input/source closure is intentionally P330, so the audit
    needs this mixed but explicit projection.
    """
    p330, _p330_payload, source = _predecessor_p330()
    _p331, p331_payload = _predecessor_p331()
    return p330, p331_payload, source


def _current_sources() -> dict[str, bytes]:
    # Compatibility names are required by the inherited packager.  Their
    # values are exact P3.32 wrapper/runtime/observer bytes; no P331 resident
    # source is admitted here.
    paths = {
        "p328_stock_candidate_build.py": SELF_SOURCE,
        "p328_artifact_identity.py": artifact.P332_ARTIFACT_SOURCE,
        "p328_stock_process_v2_adapter.py": adapter.P332_ADAPTER_SOURCE,
        "p328_authenticated_exec_runtime.py": RUNTIME_SOURCE,
        "p328_authenticated_acm_observer.py": OBSERVER_SOURCE,
    }
    return {
        name: _stable(path, f"P3.32 source {name}", 2 << 20, nlink=1)
        for name, path in paths.items()
    }


def _active_auth_key() -> bytes:
    key = getattr(_P328, "_ACTIVE_AUTH_KEY", None)
    if type(key) is not bytes or len(key) != artifact.AUTH_KEY_SIZE:
        raise AuditError("P3.32 auth key is not bound before runtime transform")
    return key


def _runtime_transform(before: bytes, auth_key: bytes) -> tuple[bytes, dict[str, Any]]:
    runtime_key = getattr(
        resident_runtime, "RUNTIME_KEY", "s22plus_fyg8_p290_e3_runtime.inc.c"
    )
    try:
        transformed_bundle = resident_runtime.transform_artifacts(
            {runtime_key: before}, auth_key
        )
    except Exception as exc:
        raise AuditError(f"P3.32 runtime transform failed: {exc}") from exc
    if (
        not isinstance(transformed_bundle, Mapping)
        or set(transformed_bundle) != {runtime_key}
        or type(transformed_bundle[runtime_key]) is not bytes
        or transformed_bundle[runtime_key] == before
    ):
        raise AuditError("P3.32 runtime changed an unexpected source")
    after = transformed_bundle[runtime_key]
    receipt: dict[str, Any] = {}
    validator = getattr(resident_runtime, "validate_transform", None)
    if callable(validator):
        try:
            parameters = inspect.signature(validator).parameters
            if "auth_key" in parameters:
                value = validator(before, after, auth_key=auth_key)
            elif "auth_key_sha256" in parameters:
                value = validator(
                    before,
                    after,
                    auth_key_sha256=hashlib.sha256(auth_key).hexdigest(),
                )
            else:
                value = validator(before, after)
        except Exception as exc:
            raise AuditError(f"P3.32 runtime transform validation failed: {exc}") from exc
        if isinstance(value, Mapping):
            receipt.update(dict(value))
    receipt.update(
        {
            "authenticated": True,
            "authentication_required": True,
            "auth_key_schema": artifact.AUTH_KEY_SCHEMA,
            "auth_key": artifact.validate_auth_key(auth_key),
            "auth_key_path_published": False,
            "source_identity": identity(before),
            "target_identity": identity(after),
            "runtime_contract": getattr(resident_runtime, "CONTRACT_ID", ""),
            "run_id_hex": P332_RUN_ID_HEX,
            "input_lineage": "p330-runtime-include",
            "same_tty_logical_sessions": True,
        }
    )
    receipt.pop("auth_key_path", None)
    receipt.pop("key_path", None)
    return after, receipt


def _copy_source_closure(
    output_root: Path, predecessor: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Copy P330's source closure and transform only its runtime include."""
    source_root = output_root / "stock-sources"
    _ENGINE.p321._mkdir(source_root)
    expected = predecessor.get("source_closure")
    if not isinstance(expected, dict) or len(expected) != 12:
        raise AuditError("P3.30 source closure differs")
    auth_key = _active_auth_key()
    receipts: dict[str, dict[str, Any]] = {}
    runtime_receipt: dict[str, Any] | None = None
    runtime_name = "s22plus_fyg8_p290_e3_runtime.inc.c"
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
            after, runtime_receipt = _runtime_transform(before, auth_key)
            runtime_receipt["before_identity"] = identity(before)
            runtime_receipt["after_identity"] = identity(after)
        _ENGINE.p321._write_exclusive(source_root / name, after)
        receipts[name] = identity(after)
    if runtime_receipt is None:
        raise AuditError("P3.30 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, runtime_receipt


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, packager, source = _INHERITED_LOAD_PACKAGER()
    packager.RUN_ID = P332_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    return helper, packager, source


class _RuntimeCompat:
    RuntimeRepairError = ValueError

    @staticmethod
    def transform_runtime_include(value: bytes) -> bytes:
        return _runtime_transform(value, _active_auth_key())[0]

    @staticmethod
    def validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
        transformed, receipt = _runtime_transform(before, _active_auth_key())
        if type(after) is not bytes or transformed != after:
            raise AuditError("P3.32 transformed runtime is not exact")
        if isinstance(receipt.get("default_commands"), (tuple, list)):
            commands_value = receipt["default_commands"]
            if all(type(item) is bytes for item in commands_value):
                receipt["default_commands"] = [identity(item) for item in commands_value]
        return receipt


def _auth_metadata(result: Mapping[str, Any]) -> dict[str, Any]:
    for location in (
        result.get("framed_exec", {}).get("auth_key")
        if isinstance(result.get("framed_exec"), Mapping)
        else None,
        result.get("authentication", {}).get("key")
        if isinstance(result.get("authentication"), Mapping)
        else None,
    ):
        if isinstance(location, Mapping) and location.get("size") == artifact.AUTH_KEY_SIZE:
            return {"size": location["size"], "sha256": location["sha256"]}
    return artifact.validate_auth_key(_active_auth_key())


def _runtime_commands() -> tuple[bytes, ...]:
    commands = getattr(resident_runtime, "DEFAULT_COMMANDS", ())
    if not isinstance(commands, tuple) or len(commands) != 3 or any(
        type(item) is not bytes for item in commands
    ):
        raise AuditError("P3.32 fixed P330 command set differs")
    return commands


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuditError("P3.32 result is not an object")
    result = copy.deepcopy(value)
    phase2 = result.get("phase2")
    candidate = phase2.get("candidate") if isinstance(phase2, dict) else None
    if not isinstance(candidate, dict) or candidate.get("a") != candidate.get("b"):
        raise AuditError("P3.32 A/B candidate differs")
    current_ap = candidate.get("a", {}).get("ap_tar_md5")
    if not isinstance(current_ap, dict) or current_ap in (P330_AP_IDENTITY, P331_AP_IDENTITY):
        raise AuditError("P3.32 candidate repeats a consumed P330/P331 AP")
    commands = _runtime_commands()
    source_closure = result.get("source_closure")
    if not isinstance(source_closure, dict):
        raise AuditError("P3.32 source closure is absent")
    runtime_identity = source_closure.get("s22plus_fyg8_p290_e3_runtime.inc.c")
    if runtime_identity == P331_RESIDENT_RUNTIME_SOURCE_IDENTITY:
        raise AuditError("P3.31 resident runtime bytes leaked into P3.32 candidate")
    helper_sources = result.get("helper_sources")
    if isinstance(helper_sources, dict):
        if helper_sources.get("p328_authenticated_exec_runtime.py") == P331_RESIDENT_RUNTIME_SOURCE_IDENTITY:
            raise AuditError("P3.31 resident runtime helper leaked into P3.32 candidate")
        if helper_sources.get("p328_authenticated_acm_observer.py") == P331_RESIDENT_OBSERVER_SOURCE_IDENTITY:
            raise AuditError("P3.31 resident observer helper leaked into P3.32 candidate")
    auth_meta = _auth_metadata(result)
    for label in ("a", "b"):
        package = candidate.get(label, {}).get("package")
        if not isinstance(package, dict) or package.get("members") != ["boot.img.lz4"]:
            raise AuditError("P3.32 package is not boot-only")
        package.update(
            {
                "schema": "s22plus_fyg8_p332_boot_only_logical_resident_package_v1",
                "verdict": "PASS_P332_DETERMINISTIC_BOOT_ONLY_LOGICAL_RESIDENT_PACKAGE_H0",
                "members": ["boot.img.lz4"],
                "host_only": True,
                "device_contact": False,
                "odin_invoked": False,
            }
        )
    candidate.update(
        {
            "differs_from_consumed_p330": True,
            "differs_from_consumed_p331": True,
            "one_boot_img_lz4_member": True,
            "ab_artifact_identity_equal": True,
        }
    )
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "status": STATUS,
            "target": TARGET,
            "run_id_hex": P332_RUN_ID_HEX,
            "fixed_image": True,
            "boot_only": True,
            "one_boot_img_lz4_member": True,
            "byte_identical": True,
            "differs_from_consumed_p330": True,
            "differs_from_consumed_p331": True,
            "p331_resident_runtime_absent": True,
        }
    )
    lineage = result.setdefault("lineage", {})
    lineage.update(
        {
            "construction_base_run_id": P330_RUN_ID_HEX,
            "construction_base_result": P330_RESULT_IDENTITY,
            "construction_base_ap": P330_AP_IDENTITY,
            "predecessor_run_id": P331_RUN_ID_HEX,
            "predecessor_result": P331_RESULT_IDENTITY,
            "predecessor_ap": P331_AP_IDENTITY,
            "fresh_run_id": P332_RUN_ID_HEX,
            "p330_source_closure_reopened": True,
            "p331_lineage_reopened": True,
        }
    )
    preservation = result.setdefault("preservation", {})
    preservation.update(
        {
            "p330_consumed_candidate_distinct": True,
            "p330_source_closure_reopened": True,
            "p330_authenticated_protocol_reused": True,
            "p330_auth_key_reused": True,
            "p331_consumed_candidate_distinct": True,
            "p331_result_reopened": True,
            "p331_resident_runtime_not_copied": True,
            "p330_runtime_include_input": True,
            "runtime_delta_same_tty_logical_resident_only": True,
            "logical_same_tty": True,
            "resident_loop_bounded": True,
            "resident_sessions": 2,
            "resident_reconnects": 0,
            "same_tty_fd_required": True,
            "host_tty_close_reopen": False,
            "transport_reconnect": False,
            "fixed_p330_commands": True,
            "command_count_per_session": 3,
            "interactive_pty": False,
            "arbitrary_file_transfer": False,
            "persistent_state": False,
            "rollback_untouched": True,
            "diagnostic_provider_widening": False,
        }
    )
    result["compatibility_labels"] = {
        "engine": "P331 exact-loaded",
        "source_keys": "p328-prefixed compatibility keys contain P332 wrapper bytes",
        "runtime_input": "exact P330 runtime include",
        "wire_namespace": "P330 authenticated framing retained",
        "presentation_only": True,
    }
    result["framed_exec"] = {
        "runtime_contract": getattr(resident_runtime, "CONTRACT_ID", ""),
        "observer_contract": getattr(resident_observer, "CONTRACT_ID", ""),
        "wire_magic": getattr(resident_runtime, "FRAME_MAGIC", b"S328").decode("ascii"),
        "frame_header_size": getattr(resident_runtime, "FRAME_HEADER_SIZE", 16),
        "commands": [identity(item) for item in commands],
        "proof_command_count": len(commands),
        "max_commands": getattr(resident_runtime, "MAX_COMMANDS", len(commands)),
        "caller_selected_command": False,
        "command_timeout_sec": getattr(resident_runtime, "COMMAND_TIMEOUT_SEC", 15),
        "max_output_bytes": getattr(resident_runtime, "MAX_OUTPUT_BYTES", 131072),
        "busybox_ash_child": True,
        "child_kill_and_reap": True,
        "interactive_pty": False,
        "authenticated": True,
        "authentication_required": True,
        "auth_algorithm": AUTH_ALGORITHM,
        "per_session_random_nonce": PER_SESSION_RANDOM_NONCE,
        "auth_tag_size": getattr(resident_runtime, "AUTH_TAG_SIZE", 32),
        "auth_key_schema": artifact.AUTH_KEY_SCHEMA,
        "auth_key": auth_meta,
        "auth_key_path_published": False,
        "preauth_diagnostic_frame": getattr(resident_runtime, "DIAGNOSTIC_FRAME_TYPE", 0x86),
        "rng_eagain_retry_limit": getattr(resident_runtime, "RNG_EAGAIN_RETRY_LIMIT", 64),
        "diagnostics_non_authoritative": True,
        "fixed_p330_commands": True,
        "fixed_heartbeat_only": False,
        "resident_session_cap": 2,
        "resident_reconnect_cap": 0,
        "logical_same_tty": True,
        "same_tty_fd_required": True,
        "host_tty_close_reopen": False,
        "transport_reconnect": False,
    }
    result["authentication"] = {
        "required": True,
        "scheme": "auth-key-v1",
        "key": auth_meta,
        "path_published": False,
    }
    result["resident"] = {
        "runtime_contract": getattr(resident_runtime, "CONTRACT_ID", ""),
        "observer_contract": getattr(resident_observer, "CONTRACT_ID", ""),
        "session_cap": 2,
        "reconnect_cap": 0,
        "command_count_per_session": 3,
        "commands": [identity(item) for item in commands],
        "fixed_p330_commands": True,
        "fixed_heartbeat_only": False,
        "logical_same_tty": True,
        "same_tty_fd_required": True,
        "host_tty_close_reopen": False,
        "transport_reconnect": False,
        "caller_selected_command": False,
        "interactive_pty": False,
        "persistent_state": False,
        "host_only_observer": True,
    }
    result["limitations"] = [
        "P332 runs exactly two authenticated P330 fixed-command sessions on one tty FD.",
        "The sessions are logical and same-tty; host close/reopen and transport reconnect are forbidden.",
        "The P330 runtime include is the only runtime transform input; P331 resident-loop bytes are not copied.",
        "Only the boot partition is transferred and exact Magisk rollback remains mandatory.",
        "No device contact, approval, D0, D1, F1, recovery, replay, or live authority is created by this host build.",
    ]
    repair = lineage.get("runtime_repair")
    if isinstance(repair, dict):
        if isinstance(repair.get("default_commands"), (tuple, list)):
            commands_value = repair["default_commands"]
            if all(type(item) is bytes for item in commands_value):
                repair["default_commands"] = [identity(item) for item in commands_value]
        repair.pop("auth_key_path", None)
        repair.pop("key_path", None)
        repair["auth_key"] = auth_meta
        repair["auth_key_path_published"] = False
        repair["run_id_hex"] = P332_RUN_ID_HEX
        repair["runtime_contract"] = getattr(resident_runtime, "CONTRACT_ID", "")
        repair["input_lineage"] = "p330-runtime-include"
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
    previous_predecessor = _ENGINE._predecessor
    previous_packager_predecessor = _P328._predecessor
    _ENGINE._predecessor = _audit_predecessor
    _P328._predecessor = _audit_predecessor
    try:
        return _P328.audit_existing(
            output_root,
            auth_key=DEFAULT_AUTH_KEY_PATH if auth_key is None else auth_key,
        )
    except Exception as exc:
        if isinstance(exc, AuditError):
            raise
        raise AuditError(str(exc)) from exc
    finally:
        _ENGINE._predecessor = previous_predecessor
        _P328._predecessor = previous_packager_predecessor


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
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
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


__all__ = [name for name in globals() if not name.startswith("_")]


if __name__ == "__main__":
    raise SystemExit(main())
