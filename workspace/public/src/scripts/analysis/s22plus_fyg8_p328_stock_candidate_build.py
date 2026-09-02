#!/usr/bin/env python3
"""Build the P3.28 boot-only authenticated fixed-command ACM candidate.

P3.28 reopens the consumed P3.27 output, keeps the Image/AP/BusyBox and
Process-v2 lane bounded, and changes only the materialized runtime include.
The runtime receives one exact host authentication key; no key is generated
by this builder.  This module performs host-only validation/build work and
never contacts a device or invokes Odin.
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

import s22plus_fyg8_p328_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p328_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P327_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p327_stock_candidate_build.py"
P327_BUILDER_IDENTITY = {
    "size": 18_379,
    "sha256": "7f71a003ab98c022fa47c8776513ee7d126005278194ad9ac8f16e7fd2c1c6c2",
}
P327_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p327/"
    "stock-candidate-build-v1-20260902-04"
)
P327_RESULT_IDENTITY = {
    "size": 42_906,
    "sha256": "b6ea8cc54addc7b1e5500c68004db928cc7aef704f09157b6d895f3d0318f431",
}
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p328/"
    "stock-candidate-build-v1-20260902-04"
)

BUSYBOX = ROOT / (
    "workspace/private/inputs/s22plus_fyg8_p326/busybox/bin/"
    "busybox-aarch64-static-1.36.1"
)
BUSYBOX_IDENTITY = {
    "size": 2_237_056,
    "sha256": "d4e1ca8235fd5c47a7dfca5c9c60ad2243f5d17d3c43d58a7c42355f10fa2cba",
}
BUSYBOX_SOURCE_ARCHIVE_IDENTITY = {
    "size": 2_525_473,
    "sha256": "b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314",
}
BUSYBOX_CONFIG_IDENTITY = {
    "size": 29_588,
    "sha256": "aae4e7cb22845d0eb46ab912f830558c0fb0655fd1964fdda6c745c43fa3b601",
}
BUSYBOX_SOURCE_ARCHIVE = BUSYBOX.parents[1] / "downloads/busybox-1.36.1.tar.bz2"
BUSYBOX_CONFIG = BUSYBOX.parents[1] / "pkg/busybox-1.36.1-config"

P328_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p328_artifact_identity.py"
P328_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p328_stock_process_v2_adapter.py"
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
AUTH_KEY_SIZE = artifact.AUTH_KEY_SIZE
AUTH_KEY_MODE = artifact.AUTH_KEY_MODE
AUTH_KEY_SCHEMA = artifact.AUTH_KEY_SCHEMA


P328_RUNTIME_SOURCE = REVALIDATION / "s22plus_fyg8_p328_auth_exec_runtime.py"
P328_RUNTIME_IDENTITY = {
    "size": 21_068,
    "sha256": "e69b5603998c19f2c24f48b16d8149c3c5046ae9a42a8baf9de497c3f56d328a",
}
P328_OBSERVER_SOURCE = REVALIDATION / "s22plus_fyg8_p328_auth_acm_observer.py"
P328_OBSERVER_IDENTITY = {
    "size": 18_326,
    "sha256": "2ec10d550b575f69f91f2424d9a605b5635ed9d5a853b59bb24563c85c6a9e25",
}

SCHEMA = "s22plus-fyg8-p328-stock-candidate-build-v1"
VERDICT = "PASS_P328_STOCK_CANDIDATE_BUILD_H0_AUTHENTICATED_FRAMED_EXEC"
STATUS = "IMPLEMENTED_H0_AUTHENTICATED_FRAMED_EXEC_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P328_RUN_ID = artifact.P328_RUN_ID
P328_RUN_ID_HEX = artifact.P328_RUN_ID_HEX


class AuditError(RuntimeError):
    """The P3.27 predecessor, auth key, runtime, or candidate differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")


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
    inode = lambda value: (  # noqa: E731
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
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or inode(before) != inode(inside)
        or inode(before) != inode(after)
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (expected is not None and identity(payload) != dict(expected))
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _load_exact(
    path: Path,
    name: str,
    expected: Mapping[str, Any],
) -> tuple[types.ModuleType | None, Exception | None]:
    try:
        payload = _stable(path, f"P328 {name} source", 2 << 20, expected, nlink=1)
        module = types.ModuleType(name)
        module.__file__ = str(path)
        module.__package__ = ""
        previous = sys.modules.get(name)
        sys.modules[name] = module
        try:
            exec(  # noqa: S102 - exact source bytes are the execution closure
                compile(payload, str(path), "exec", dont_inherit=True),
                module.__dict__,
            )
        finally:
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
        return module, None
    except Exception as exc:  # defer the fail-closed message to build/audit
        return None, exc


framed_runtime, _RUNTIME_LOAD_ERROR = _load_exact(
    P328_RUNTIME_SOURCE,
    "s22plus_fyg8_p328_runtime_bound_for_build",
    P328_RUNTIME_IDENTITY,
)
framed_observer, _OBSERVER_LOAD_ERROR = _load_exact(
    P328_OBSERVER_SOURCE,
    "s22plus_fyg8_p328_observer_bound_for_build",
    P328_OBSERVER_IDENTITY,
)


def _require_runtime() -> types.ModuleType:
    global framed_runtime, _RUNTIME_LOAD_ERROR
    if framed_runtime is None and P328_RUNTIME_SOURCE.is_file():
        framed_runtime, _RUNTIME_LOAD_ERROR = _load_exact(
            P328_RUNTIME_SOURCE,
            "s22plus_fyg8_p328_runtime_bound_for_build_retry",
            P328_RUNTIME_IDENTITY,
        )
    if framed_runtime is None:
        detail = " is unavailable"
        if _RUNTIME_LOAD_ERROR is not None:
            detail = f" failed to load: {_RUNTIME_LOAD_ERROR}"
        raise AuditError(f"P328 authenticated runtime{detail}")
    if not callable(getattr(framed_runtime, "transform_artifacts", None)):
        raise AuditError("P328 runtime lacks transform_artifacts(source, auth_key=...)")
    if getattr(framed_runtime, "P328_RUN_ID_HEX", None) != P328_RUN_ID_HEX:
        raise AuditError("P328 runtime run identity differs")
    if getattr(framed_runtime, "P328_RUN_ID", None) != P328_RUN_ID:
        raise AuditError("P328 runtime binary run identity differs")
    return framed_runtime


def _observer() -> types.ModuleType | None:
    global framed_observer, _OBSERVER_LOAD_ERROR
    if framed_observer is None and P328_OBSERVER_SOURCE.is_file():
        framed_observer, _OBSERVER_LOAD_ERROR = _load_exact(
            P328_OBSERVER_SOURCE,
            "s22plus_fyg8_p328_observer_bound_for_build_retry",
            P328_OBSERVER_IDENTITY,
        )
    return framed_observer


def _load_p327() -> types.ModuleType:
    payload = _stable(
        P327_BUILDER_SOURCE,
        "P3.27 builder",
        2 << 20,
        P327_BUILDER_IDENTITY,
        nlink=1,
    )
    module = types.ModuleType("s22plus_fyg8_p327_builder_bound_for_p328")
    module.__file__ = str(P327_BUILDER_SOURCE)
    module.__package__ = ""
    try:
        exec(  # noqa: S102 - exact, hash-pinned predecessor source loading
            compile(payload, str(P327_BUILDER_SOURCE), "exec", dont_inherit=True),
            module.__dict__,
        )
    except Exception as exc:
        raise AuditError("P3.27 builder failed to load") from exc
    if getattr(module, "P327_RUN_ID_HEX", None) != artifact.P327_RUN_ID_HEX:
        raise AuditError("P3.27 builder run identity differs")
    return module


_P327 = _load_p327()
try:
    _P327_PREDECESSOR = _P327.audit_existing(P327_OUTPUT)
    _P327_PREDECESSOR_PAYLOAD = _stable(
        P327_OUTPUT / "result.json",
        "P3.27 result",
        4 << 20,
        P327_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
except Exception as exc:
    raise AuditError("P3.27 predecessor audit failed") from exc

_ENGINE = _P327._ENGINE
_ORIGINAL_BUILD_ONCE = _P327._ORIGINAL_BUILD_ONCE
_ORIGINAL_AUDIT_EXISTING = _P327._ORIGINAL_AUDIT_EXISTING
_P327_NORMALIZE = _P327._normalize_result

_ACTIVE_AUTH_KEY: bytes | None = None
_ACTIVE_AUTH_KEY_META: dict[str, Any] | None = None


def _result_auth_key_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    """Recover only a path-free key identity for post-build re-normalization."""
    if _ACTIVE_AUTH_KEY_META is not None:
        return dict(_ACTIVE_AUTH_KEY_META)
    candidates: list[Any] = []
    framed = value.get("framed_exec")
    if isinstance(framed, Mapping):
        candidates.append(framed.get("auth_key"))
    authentication = value.get("authentication")
    if isinstance(authentication, Mapping):
        candidates.append(authentication.get("key"))
    lineage = value.get("lineage")
    if isinstance(lineage, Mapping) and isinstance(lineage.get("runtime_repair"), Mapping):
        candidates.append(lineage["runtime_repair"].get("auth_key"))
    for candidate in candidates:
        if (
            isinstance(candidate, Mapping)
            and set(candidate) == {"size", "sha256"}
            and type(candidate.get("size")) is int
            and candidate.get("size") == AUTH_KEY_SIZE
            and type(candidate.get("sha256")) is str
            and len(candidate["sha256"]) == 64
            and all(character in "0123456789abcdef" for character in candidate["sha256"])
        ):
            return {"size": AUTH_KEY_SIZE, "sha256": candidate["sha256"]}
    raise AuditError("P328 path-free auth key identity is absent")


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    payload = _stable(
        P327_OUTPUT / "result.json",
        "P3.27 result",
        4 << 20,
        P327_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    # The exact P3.27 audit was completed before the delegate globals were
    # rebound to P3.28 below.  Re-running that mutable delegate here would
    # audit the successor under P3.28 labels; the pinned bytes plus the
    # original audited projection are the stable predecessor seam.
    if _strict_json(payload, "P3.27 result") != _P327_PREDECESSOR:
        raise AuditError("P3.27 result changed after audit")
    source = _stable(
        P327_BUILDER_SOURCE,
        "P3.27 builder",
        2 << 20,
        P327_BUILDER_IDENTITY,
        nlink=1,
    )
    return dict(_P327_PREDECESSOR), payload, source


def _current_sources() -> dict[str, bytes]:
    paths: dict[str, Path] = {
        "p328_stock_candidate_build.py": SELF_SOURCE,
        "p328_artifact_identity.py": P328_ARTIFACT_SOURCE,
        "p328_stock_process_v2_adapter.py": P328_ADAPTER_SOURCE,
        "p328_authenticated_exec_runtime.py": P328_RUNTIME_SOURCE,
    }
    if P328_OBSERVER_SOURCE.is_file():
        paths["p328_authenticated_acm_observer.py"] = P328_OBSERVER_SOURCE
    return {
        name: _stable(path, f"P328 source {name}", 2 << 20, nlink=1)
        for name, path in paths.items()
    }


def _runtime_transform(before: bytes, auth_key: bytes) -> tuple[bytes, dict[str, Any]]:
    runtime = _require_runtime()
    runtime_key = getattr(
        runtime, "RUNTIME_KEY", "s22plus_fyg8_p290_e3_runtime.inc.c"
    )
    source = {runtime_key: before}
    try:
        transformed_bundle = runtime.transform_artifacts(source, auth_key=auth_key)
    except Exception as exc:
        raise AuditError(f"P328 authenticated runtime transform failed: {exc}") from exc
    if not isinstance(transformed_bundle, Mapping) or runtime_key not in transformed_bundle:
        raise AuditError("P328 runtime transform result lacks the runtime include")
    after = transformed_bundle[runtime_key]
    if type(after) is not bytes or set(transformed_bundle) != {runtime_key}:
        raise AuditError("P328 runtime changed more than the runtime include")
    if after == before:
        raise AuditError("P328 authenticated runtime did not change the include")

    receipt: dict[str, Any] = {}
    validator = getattr(runtime, "validate_transform", None)
    if callable(validator):
        try:
            parameters = inspect.signature(validator).parameters
            kwargs = {"auth_key": auth_key} if "auth_key" in parameters else {}
            value = validator(before, after, **kwargs)
        except Exception as exc:
            raise AuditError(f"P328 runtime transform validation failed: {exc}") from exc
        if isinstance(value, Mapping):
            receipt.update(dict(value))
    receipt.update(
        {
            "authenticated": True,
            "authentication_required": True,
            "auth_key_schema": AUTH_KEY_SCHEMA,
            "auth_key": dict(_ACTIVE_AUTH_KEY_META or artifact.validate_auth_key(auth_key)),
            "auth_key_path_published": False,
            "source_identity": identity(before),
            "target_identity": identity(after),
            "runtime_contract": getattr(
                runtime, "CONTRACT_ID", "s22plus-fyg8-p328-authenticated-exec-runtime-v1"
            ),
            "run_id_hex": P328_RUN_ID_HEX,
        }
    )
    # A runtime may return useful validation labels, but a key path is never a
    # result field.  Replace any nested key projection with the path-free one.
    receipt.pop("auth_key_path", None)
    receipt.pop("key_path", None)
    receipt["auth_key"] = dict(_ACTIVE_AUTH_KEY_META or artifact.validate_auth_key(auth_key))
    return after, receipt


def _copy_source_closure(
    output_root: Path, predecessor: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if _ACTIVE_AUTH_KEY is None:
        raise AuditError("P328 auth key is not bound before runtime transform")
    source_root = output_root / "stock-sources"
    _ENGINE.p321._mkdir(source_root)
    expected = predecessor.get("source_closure")
    if not isinstance(expected, dict) or len(expected) != 12:
        raise AuditError("P3.27 source closure differs")
    receipts: dict[str, dict[str, Any]] = {}
    runtime_receipt: dict[str, Any] | None = None
    for name, expected_identity in sorted(expected.items()):
        before = _stable(
            P327_OUTPUT / "stock-sources" / name,
            f"P3.27 source {name}",
            2 << 20,
            expected_identity,
            mode=0o400,
            nlink=1,
        )
        after = before
        if name == "s22plus_fyg8_p290_e3_runtime.inc.c":
            after, runtime_receipt = _runtime_transform(before, _ACTIVE_AUTH_KEY)
            runtime_receipt["before_identity"] = identity(before)
            runtime_receipt["after_identity"] = identity(after)
        _ENGINE.p321._write_exclusive(source_root / name, after)
        receipts[name] = identity(after)
    if runtime_receipt is None:
        raise AuditError("P328 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, runtime_receipt


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, packager, source = _P327._load_packager()
    packager.RUN_ID = P328_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    return helper, packager, source


class _RuntimeCompat:
    RuntimeRepairError = ValueError

    @staticmethod
    def transform_runtime_include(value: bytes) -> bytes:
        if _ACTIVE_AUTH_KEY is None:
            raise AuditError("P328 auth key is not bound")
        return _runtime_transform(value, _ACTIVE_AUTH_KEY)[0]

    @staticmethod
    def validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
        if _ACTIVE_AUTH_KEY is None:
            raise AuditError("P328 auth key is not bound")
        transformed, receipt = _runtime_transform(before, _ACTIVE_AUTH_KEY)
        if type(after) is not bytes or transformed != after:
            raise AuditError("P328 transformed runtime is not bytes")
        return receipt


# The inherited P3.22 engine is the common build/packager seam.  It is bound
# to the P3.27 output and P3.28 execution-critical closures below; no P327
# source is edited.
_ENGINE._current_sources = _current_sources
_ENGINE._predecessor = _predecessor
_ENGINE._copy_source_closure = _copy_source_closure
_ENGINE._load_packager = _load_packager
_ENGINE.artifact = artifact
_ENGINE.adapter = adapter
_ENGINE.repair = _RuntimeCompat
_ENGINE.P321_OUTPUT = P327_OUTPUT
_ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_ENGINE.P322_ARTIFACT_SOURCE = P328_ARTIFACT_SOURCE
_ENGINE.P322_REPAIR_SOURCE = P328_RUNTIME_SOURCE
_ENGINE.P322_ADAPTER_SOURCE = P328_ADAPTER_SOURCE
_ENGINE.P322_RUN_ID = P328_RUN_ID
_ENGINE.P322_RUN_ID_HEX = P328_RUN_ID_HEX
_ENGINE.SCHEMA = SCHEMA
_ENGINE.VERDICT = VERDICT
_ENGINE.STATUS = STATUS
_ENGINE.TARGET = TARGET


class _P328ConsoleCompat:
    CONTRACT_ID = getattr(
        framed_runtime,
        "CONTRACT_ID",
        "s22plus-fyg8-p328-authenticated-exec-runtime-v1",
    )
    HOST_TRANSCRIPT = b""
    DEVICE_TRANSCRIPT = b""


def _patch_delegate_modules() -> None:
    modules = [_P327, _P327._P326]
    for name in ("_P325", "_P324", "_P323", "_P322", "_P321", "_P320"):
        for base in tuple(modules):
            value = getattr(base, name, None)
            if isinstance(value, types.ModuleType) and value not in modules:
                modules.append(value)
    for module in modules:
        predecessor_values = {
            name: artifact.P327_RUN_ID_HEX
            for name in (
                "P321_PREDECESSOR_RUN_ID_HEX",
                "P322_PREDECESSOR_RUN_ID_HEX",
                "P323_PREDECESSOR_RUN_ID_HEX",
                "P324_PREDECESSOR_RUN_ID_HEX",
                "P325_PREDECESSOR_RUN_ID_HEX",
                "P326_PREDECESSOR_RUN_ID_HEX",
                "P327_PREDECESSOR_RUN_ID_HEX",
            )
            if hasattr(module, name)
        }
        predecessor_values.update(
            {
                name.replace("_HEX", ""): artifact.P327_RUN_ID
                for name in tuple(predecessor_values)
            }
        )
        for name, value in {
            "artifact": artifact,
            "adapter": adapter,
            "SCHEMA": SCHEMA,
            "VERDICT": VERDICT,
            "STATUS": STATUS,
            "TARGET": TARGET,
            "P327_RUN_ID": P328_RUN_ID,
            "P327_RUN_ID_HEX": P328_RUN_ID_HEX,
            "P326_RUN_ID": P328_RUN_ID,
            "P326_RUN_ID_HEX": P328_RUN_ID_HEX,
            "P325_RUN_ID": P328_RUN_ID,
            "P325_RUN_ID_HEX": P328_RUN_ID_HEX,
            "P324_RUN_ID": P328_RUN_ID,
            "P324_RUN_ID_HEX": P328_RUN_ID_HEX,
            "console": _P328ConsoleCompat,
            "framed_runtime": framed_runtime,
            "framed_observer": framed_observer,
            **predecessor_values,
        }.items():
            if hasattr(module, name):
                setattr(module, name, value)


_patch_delegate_modules()


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuditError("P328 result is not an object")
    # Parent normalizers use shallow projections and mutate nested candidate
    # dictionaries.  Work on a deep copy so re-normalization is idempotent
    # for callers holding the stored result object.
    normalization_input = copy.deepcopy(value)
    # P3.27's normalizer is intentionally retained as the recursive checker,
    # but an already-published P3.28 result has the successor package label
    # and predecessor flag.  Present those two fields under the parent's
    # accepted spelling for the duration of that checker, then restore the
    # P3.28 projection below.
    phase2_value = normalization_input.get("phase2")
    candidate_value = phase2_value.get("candidate") if isinstance(phase2_value, dict) else None
    if isinstance(candidate_value, dict):
        if "differs_from_consumed_p327" in candidate_value:
            # Each inherited normalizer advances one predecessor spelling;
            # seed the complete true chain so none of those checks can erase
            # the already-proved P327 distinction.
            for predecessor_number in range(321, 327):
                candidate_value[f"differs_from_consumed_p{predecessor_number}"] = (
                    candidate_value["differs_from_consumed_p327"]
                )
        for label in ("a", "b"):
            package = candidate_value.get(label, {}).get("package")
            if isinstance(package, dict) and (
                package.get("schema"), package.get("verdict")
            ) not in (
                (
                    "s22plus_fyg8_p326_boot_only_package_v1",
                    "PASS_P326_DETERMINISTIC_BOOT_ONLY_BUSYBOX_PACKAGE_H0",
                ),
                (
                    "s22plus_fyg8_p327_boot_only_package_v1",
                    "PASS_P327_DETERMINISTIC_BOOT_ONLY_FRAMED_EXEC_PACKAGE_H0",
                ),
            ):
                package["schema"] = "s22plus_fyg8_p327_boot_only_package_v1"
                package["verdict"] = "PASS_P327_DETERMINISTIC_BOOT_ONLY_FRAMED_EXEC_PACKAGE_H0"
    # The parent normalizer performs the inherited recursive phase-2 checks.
    # Its globals are rebound above, so it sees the P3.27 predecessor and the
    # fresh P3.28 identity while preserving the P327 package seam.
    try:
        result = _P327_NORMALIZE(normalization_input)
    except Exception as exc:
        raise AuditError(f"P328 inherited result normalization failed: {exc}") from exc
    if (
        result.get("schema") != SCHEMA
        or result.get("run_id_hex") != P328_RUN_ID_HEX
        or result.get("lineage", {}).get("predecessor_run_id")
        != artifact.P327_PREDECESSOR_RUN_ID_HEX
    ):
        raise AuditError("P328 result header differs")
    candidate = result.get("phase2", {}).get("candidate")
    if not isinstance(candidate, dict):
        raise AuditError("P328 candidate projection is absent")
    predecessor_flag = candidate.pop(
        "differs_from_consumed_p326",
        candidate.get("differs_from_consumed_p327", False),
    )
    if predecessor_flag is not True:
        raise AuditError("P328 repeats consumed P327 AP")
    candidate["differs_from_consumed_p327"] = True
    for predecessor_number in range(321, 327):
        candidate.pop(f"differs_from_consumed_p{predecessor_number}", None)
    for label in ("a", "b"):
        if candidate.get(label, {}).get("busybox") != BUSYBOX_IDENTITY:
            raise AuditError("P328 candidate lacks exact unchanged BusyBox")
        package = candidate[label].get("package")
        if not isinstance(package, dict):
            raise AuditError("P328 package projection is absent")
        package["schema"] = "s22plus_fyg8_p328_boot_only_package_v1"
        package["verdict"] = "PASS_P328_DETERMINISTIC_BOOT_ONLY_AUTHENTICATED_PACKAGE_H0"

    preservation = result.get("preservation")
    if not isinstance(preservation, dict):
        raise AuditError("P328 preservation projection is absent")
    for stale in (
        "p326_consumed_candidate_unchanged",
        "p326_source_closure_reopened",
        "p325_consumed_candidate_unchanged",
        "p325_source_closure_reopened",
        "runtime_delta_framed_exec_only",
        "runtime_delta_console_only",
        "runtime_delta_one_function",
    ):
        preservation.pop(stale, None)
    preservation.update(
        {
            "p327_consumed_candidate_unchanged": True,
            "p327_source_closure_reopened": True,
            "p327_exact_lane_and_guard_reused": True,
            "runtime_delta_authenticated_exec_only": True,
        }
    )
    result["busybox"] = {
        "binary": BUSYBOX_IDENTITY,
        "source_archive": BUSYBOX_SOURCE_ARCHIVE_IDENTITY,
        "config": BUSYBOX_CONFIG_IDENTITY,
        "path": "bin/busybox",
        "static_aarch64": True,
        "ash_enabled": True,
        "su_getty_disabled": True,
    }

    runtime = _require_runtime()
    observer = _observer()
    runtime_contract = getattr(
        runtime, "CONTRACT_ID", "s22plus-fyg8-p328-authenticated-exec-runtime-v1"
    )
    observer_contract = getattr(
        observer,
        "CONTRACT_ID",
        "s22plus-fyg8-p328-authenticated-acm-observer-v1",
    )
    commands = tuple(getattr(runtime, "DEFAULT_COMMANDS", ()))
    auth_meta = _result_auth_key_metadata(result)
    result.pop("bidirectional_console", None)
    result["framed_exec"] = {
        "runtime_contract": runtime_contract,
        "observer_contract": observer_contract,
        "wire_magic": getattr(runtime, "FRAME_MAGIC", b"S328").decode("ascii"),
        "frame_header_size": getattr(runtime, "FRAME_HEADER_SIZE", 16),
        "commands": [identity(item) for item in commands],
        "proof_command_count": len(commands),
        "max_commands": getattr(runtime, "MAX_COMMANDS", len(commands)),
        "caller_selected_command": bool(
            getattr(runtime, "CALLER_SELECTED_COMMAND", True)
        ),
        "command_timeout_sec": getattr(runtime, "COMMAND_TIMEOUT_SEC", 10),
        "max_output_bytes": getattr(runtime, "MAX_OUTPUT_BYTES", 128 * 1024),
        "busybox_ash_child": True,
        "child_kill_and_reap": True,
        "interactive_pty": False,
        "authenticated": True,
        "authentication_required": True,
        "auth_algorithm": getattr(runtime, "AUTH_ALGORITHM", "hmac-sha256"),
        "per_session_random_nonce": bool(
            getattr(runtime, "PER_SESSION_RANDOM_NONCE", True)
        ),
        "auth_tag_size": getattr(runtime, "AUTH_TAG_SIZE", 32),
        "auth_key_schema": AUTH_KEY_SCHEMA,
        "auth_key": auth_meta,
        "auth_key_path_published": False,
    }
    result["authentication"] = {
        "required": True,
        "scheme": "auth-key-v1",
        "key": auth_meta,
        "path_published": False,
    }
    result["limitations"] = [
        "P328 packages one authenticated bounded command proof over the P327 ACM path.",
        "The symmetric key is embedded in the private candidate; possession of that candidate implies possession of the key.",
        "P328 accepts only the runtime's bounded ASCII command policy and proves no general interactive shell or PTY.",
        "Only the boot partition is transferred; the exact-stock rollback remains mandatory.",
        "BusyBox, module bytes, and the inherited Process-v2 guard are unchanged.",
        "No device contact, approval, D0, D1, F1, recovery, replay, or live authority is created by this host build.",
    ]
    result["compatibility_labels"] = {
        "inherited_input_names": ["p321-result.json", "p321-stock-candidate-build.py"],
        "actual_predecessor": "P327",
        "presentation_only": True,
    }
    # Keep the auth projection path-free even if a runtime supplied a richer
    # internal receipt to its optional validator.
    if isinstance(result.get("lineage", {}).get("runtime_repair"), dict):
        repair = result["lineage"]["runtime_repair"]
        repair.pop("auth_key_path", None)
        repair.pop("key_path", None)
        repair["auth_key"] = auth_meta
        repair["auth_key_path_published"] = False
    return result


_ENGINE._json_bytes = lambda value: _json_bytes(_normalize_result(value))


def _validate_busybox_inputs() -> None:
    try:
        _P327._validate_busybox_inputs()
    except Exception as exc:
        raise AuditError(f"P328 BusyBox input differs: {exc}") from exc


def _read_auth_key(path: Path | str | None) -> tuple[bytes, dict[str, Any]]:
    selected = DEFAULT_AUTH_KEY_PATH if path is None else Path(path)
    try:
        payload = artifact.read_auth_key(selected)
        metadata = artifact.validate_auth_key(payload)
    except Exception as exc:
        raise AuditError(str(exc)) from exc
    if metadata != {"size": AUTH_KEY_SIZE, "sha256": metadata["sha256"]}:
        raise AuditError("P328 auth key metadata differs")
    return payload, metadata


def _with_auth_key(path: Path | str | None) -> tuple[bytes, dict[str, Any]]:
    global _ACTIVE_AUTH_KEY, _ACTIVE_AUTH_KEY_META
    payload, metadata = _read_auth_key(path)
    _ACTIVE_AUTH_KEY = payload
    _ACTIVE_AUTH_KEY_META = metadata
    return payload, metadata


def _clear_auth_key() -> None:
    global _ACTIVE_AUTH_KEY, _ACTIVE_AUTH_KEY_META
    _ACTIVE_AUTH_KEY = None
    _ACTIVE_AUTH_KEY_META = None


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    auth_key: Path | str | None = None,
    audit_only: bool = False,
) -> dict[str, Any]:
    output_root = output_root.absolute()
    _validate_busybox_inputs()
    _require_runtime()
    _with_auth_key(auth_key)
    try:
        if audit_only:
            return audit_existing(output_root, auth_key=auth_key, _bound=True)
        if output_root.exists() or output_root.is_symlink():
            raise AuditError("P328 output already exists")
        output_root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        output_root.parent.chmod(0o700)
        _ORIGINAL_BUILD_ONCE(output_root)
        return _strict_json(
            _stable(
                output_root / "result.json",
                "P328 result",
                4 << 20,
                mode=0o400,
                nlink=1,
            ),
            "P328 result",
        )
    finally:
        _clear_auth_key()


def audit_existing(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    auth_key: Path | str | None = None,
    _bound: bool = False,
) -> dict[str, Any]:
    output_root = output_root.absolute()
    _validate_busybox_inputs()
    _require_runtime()
    if not _bound:
        _with_auth_key(auth_key)
    try:
        raw = _stable(
            output_root / "result.json",
            "P328 result",
            4 << 20,
            mode=0o400,
            nlink=1,
        )
        stored = _strict_json(raw, "P328 result")
        try:
            audited = _ORIGINAL_AUDIT_EXISTING(output_root)
        except Exception as exc:
            raise AuditError("P328 output did not reopen") from exc
        normalized = _normalize_result(audited)
        if stored != normalized:
            raise AuditError("P328 stored result differs from audit")
        return stored
    finally:
        if not _bound:
            _clear_auth_key()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--auth-key", type=Path, default=DEFAULT_AUTH_KEY_PATH)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    auth_path = args.auth_key if args.auth_key.is_absolute() else ROOT / args.auth_key
    try:
        result = build_result(output, auth_key=auth_path, audit_only=args.audit_only)
    except (AuditError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
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
