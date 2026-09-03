#!/usr/bin/env python3
"""Build the P3.33 boot-only pre-OPEN diagnostic candidate.

The exact P3.32 builder is the packaging engine.  P3.33 starts from P3.32's
12-member source closure and changes only its runtime include through the
stage-0 console-entry transform.  No kernel rebuild, device access, or Odin
invocation occurs here.
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
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p333_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p333_open_entry_diag_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p333_open_entry_diag_runtime as runtime  # noqa: E402
import s22plus_fyg8_p333_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P332_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p332_stock_candidate_build.py"
P332_BUILDER_IDENTITY = {
    "size": 38_993,
    "sha256": "bf17c88c7d326b98e8debce489ed08ae7137e6765870f83e9c963939dcb1dd84",
}
P332_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p332/"
    "stock-candidate-build-v1-20260903-10"
)
P332_RESULT = P332_OUTPUT / "result.json"
P332_RESULT_IDENTITY = {
    "size": 49_309,
    "sha256": "34b5c70bafc6eef854a95c88fb3ac6e3d1c2212de7604c76389c60f8ee0b2888",
}
P332_RUN_ID_HEX = "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b"
P332_RUN_ID = bytes.fromhex(P332_RUN_ID_HEX)
P333_RUN_ID_HEX = "c333f1e0a90b5e6d7c8a9b0c1d2e3f7b"
P333_RUN_ID = bytes.fromhex(P333_RUN_ID_HEX)
P332_AP_IDENTITY = dict(artifact.P332_AP_IDENTITY)

DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p333/"
    "stock-candidate-build-v1-20260904-01"
)
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
SCHEMA = "s22plus-fyg8-p333-stock-candidate-build-v1"
VERDICT = "PASS_P333_STOCK_CANDIDATE_BUILD_H0_OPEN_ENTRY_DIAG"
STATUS = "IMPLEMENTED_H0_OPEN_ENTRY_DIAG_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class AuditError(RuntimeError):
    """The exact P3.32 lineage or P3.33 closure differs."""


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
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise AuditError(f"{label} has duplicate key {key}")
            value[key] = item
        return value

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} is not an object")
    return value


def _load_p332_builder() -> types.ModuleType:
    payload = _stable(
        P332_BUILDER_SOURCE,
        "P3.32 builder source",
        2 << 20,
        P332_BUILDER_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p332_builder_bound_for_p333")
    module.__file__ = str(P332_BUILDER_SOURCE)
    module.__package__ = ""
    previous = sys.modules.get(module.__name__)
    sys.modules[module.__name__] = module
    try:
        exec(compile(payload, str(P332_BUILDER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P3.32 builder source failed to load") from exc
    finally:
        if previous is None:
            sys.modules.pop(module.__name__, None)
        else:
            sys.modules[module.__name__] = previous
    if getattr(module, "P332_RUN_ID_HEX", None) != P332_RUN_ID_HEX:
        raise AuditError("P3.32 builder binding differs")
    return module


_P332 = _load_p332_builder()
_P328 = _P332._P328
_ENGINE = _P332._ENGINE


def _all_modules() -> list[types.ModuleType]:
    result = [_P332]
    for module in _P332._modules(_P332._P331):
        if module not in result:
            result.append(module)
    return result


def _rebind_engine() -> None:
    for module in _all_modules():
        for name, value in tuple(vars(module).items()):
            if value == P332_RUN_ID:
                setattr(module, name, P333_RUN_ID)
            elif value == P332_RUN_ID_HEX:
                setattr(module, name, P333_RUN_ID_HEX)
            elif callable(value) and getattr(value, "__kwdefaults__", None):
                defaults = dict(value.__kwdefaults__)
                changed = False
                for key, current in tuple(defaults.items()):
                    if current == P332_RUN_ID:
                        defaults[key] = P333_RUN_ID
                        changed = True
                    elif current == P332_RUN_ID_HEX:
                        defaults[key] = P333_RUN_ID_HEX
                        changed = True
                if changed:
                    value.__kwdefaults__ = defaults
    for module in (*_all_modules(), _P328, _ENGINE):
        for name, value in {
            "artifact": artifact,
            "adapter": adapter,
            "resident_runtime": runtime,
            "framed_runtime": runtime,
            "resident_observer": observer,
            "framed_observer": observer,
            "P328_RUN_ID": P333_RUN_ID,
            "P328_RUN_ID_HEX": P333_RUN_ID_HEX,
            "P330_RUN_ID": P333_RUN_ID,
            "P330_RUN_ID_HEX": P333_RUN_ID_HEX,
            "P331_RUN_ID": P333_RUN_ID,
            "P331_RUN_ID_HEX": P333_RUN_ID_HEX,
            "P332_RUN_ID": P333_RUN_ID,
            "P332_RUN_ID_HEX": P333_RUN_ID_HEX,
            "DEFAULT_OUTPUT_ROOT": DEFAULT_OUTPUT_ROOT,
            "DEFAULT_AUTH_KEY_PATH": DEFAULT_AUTH_KEY_PATH,
            "SCHEMA": SCHEMA,
            "VERDICT": VERDICT,
            "STATUS": STATUS,
            "TARGET": TARGET,
        }.items():
            if hasattr(module, name):
                setattr(module, name, value)
    _ENGINE.P321_OUTPUT = P332_OUTPUT
    _ENGINE.P322_RUN_ID = P333_RUN_ID
    _ENGINE.P322_RUN_ID_HEX = P333_RUN_ID_HEX
    _ENGINE.P322_ARTIFACT_SOURCE = artifact.P333_ARTIFACT_SOURCE
    _ENGINE.P322_REPAIR_SOURCE = Path(runtime.__file__).resolve()
    _ENGINE.P322_ADAPTER_SOURCE = adapter.P333_ADAPTER_SOURCE


_rebind_engine()


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    payload = _stable(
        P332_RESULT,
        "P3.32 result",
        4 << 20,
        P332_RESULT_IDENTITY,
        mode=0o400,
    )
    value = _strict_json(payload, "P3.32 result")
    candidate = value.get("phase2", {}).get("candidate")
    if (
        value.get("schema") != "s22plus-fyg8-p332-stock-candidate-build-v1"
        or value.get("run_id_hex") != P332_RUN_ID_HEX
        or value.get("target") != TARGET
        or not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("a", {}).get("ap_tar_md5") != P332_AP_IDENTITY
        or candidate.get("a", {}).get("package", {}).get("members")
        != ["boot.img.lz4"]
        or not isinstance(value.get("source_closure"), dict)
        or len(value["source_closure"]) != 12
    ):
        raise AuditError("P3.32 predecessor result differs")
    for name, expected in sorted(value["source_closure"].items()):
        _stable(
            P332_OUTPUT / "stock-sources" / name,
            f"P3.32 source {name}",
            2 << 20,
            expected,
            mode=0o400,
        )
    for label in ("a", "b"):
        _stable(
            P332_OUTPUT / f"candidate-{label}/odin4/AP.tar.md5",
            f"P3.32 candidate {label}",
            128 << 20,
            P332_AP_IDENTITY,
        )
    source = _stable(
        P332_BUILDER_SOURCE,
        "P3.32 builder source",
        2 << 20,
        P332_BUILDER_IDENTITY,
    )
    return value, payload, source


def _current_sources() -> dict[str, bytes]:
    paths = {
        "p328_stock_candidate_build.py": SELF_SOURCE,
        "p328_artifact_identity.py": artifact.P333_ARTIFACT_SOURCE,
        "p328_stock_process_v2_adapter.py": adapter.P333_ADAPTER_SOURCE,
        "p328_authenticated_exec_runtime.py": Path(runtime.__file__).resolve(),
        "p328_authenticated_acm_observer.py": Path(observer.__file__).resolve(),
    }
    return {
        name: _stable(path, f"P3.33 source {name}", 2 << 20)
        for name, path in paths.items()
    }


def _active_key() -> bytes:
    key = getattr(_P328, "_ACTIVE_AUTH_KEY", None)
    if type(key) is not bytes or len(key) != artifact.AUTH_KEY_SIZE:
        raise AuditError("P3.33 auth key is not bound")
    return key


def _runtime_transform(before: bytes, key: bytes) -> tuple[bytes, dict[str, Any]]:
    after = runtime.transform_runtime_include(before, key)
    receipt = dict(
        runtime.validate_transform(
            before,
            after,
            auth_key_sha256=hashlib.sha256(key).hexdigest(),
        )
    )
    receipt.update(
        {
            "authenticated": True,
            "auth_key": artifact.validate_auth_key(key),
            "auth_key_path_published": False,
            "runtime_contract": runtime.CONTRACT_ID,
            "run_id_hex": P333_RUN_ID_HEX,
            "input_lineage": "p332-runtime-include",
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
        }
    )
    receipt.pop("auth_key_path", None)
    receipt.pop("key_path", None)
    return after, receipt


def _copy_source_closure(
    output_root: Path, predecessor: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    source_root = output_root / "stock-sources"
    _ENGINE.p321._mkdir(source_root)
    expected = predecessor["source_closure"]
    receipts: dict[str, dict[str, Any]] = {}
    repair: dict[str, Any] | None = None
    runtime_name = "s22plus_fyg8_p290_e3_runtime.inc.c"
    key = _active_key()
    for name, expected_identity in sorted(expected.items()):
        before = _stable(
            P332_OUTPUT / "stock-sources" / name,
            f"P3.32 source {name}",
            2 << 20,
            expected_identity,
            mode=0o400,
        )
        after = before
        if name == runtime_name:
            after, repair = _runtime_transform(before, key)
            repair["before_identity"] = identity(before)
            repair["after_identity"] = identity(after)
        _ENGINE.p321._write_exclusive(source_root / name, after)
        receipts[name] = identity(after)
    if repair is None:
        raise AuditError("P3.32 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, repair


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, packager, source = _P332._load_packager()
    packager.RUN_ID = P333_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    return helper, packager, source


class _RuntimeCompat:
    RuntimeRepairError = ValueError

    @staticmethod
    def transform_runtime_include(value: bytes) -> bytes:
        return _runtime_transform(value, _active_key())[0]

    @staticmethod
    def validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
        expected, receipt = _runtime_transform(before, _active_key())
        if expected != after:
            raise AuditError("P3.33 transformed runtime differs")
        if isinstance(receipt.get("default_commands"), (tuple, list)):
            receipt["default_commands"] = [
                identity(item) for item in receipt["default_commands"]
            ]
        return receipt


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(_P332._normalize_result(value))
    candidate = result["phase2"]["candidate"]
    current_ap = candidate["a"]["ap_tar_md5"]
    if candidate["a"] != candidate["b"] or current_ap == P332_AP_IDENTITY:
        raise AuditError("P3.33 candidate repeats P3.32 or differs A/B")
    for label in ("a", "b"):
        package = candidate[label]["package"]
        package.update(
            {
                "schema": "s22plus_fyg8_p333_boot_only_open_entry_diag_package_v1",
                "verdict": "PASS_P333_DETERMINISTIC_BOOT_ONLY_OPEN_ENTRY_DIAG_H0",
            }
        )
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "status": STATUS,
            "run_id_hex": P333_RUN_ID_HEX,
            "differs_from_consumed_p332": True,
        }
    )
    result["lineage"].update(
        {
            "construction_base_run_id": P332_RUN_ID_HEX,
            "construction_base_result": P332_RESULT_IDENTITY,
            "construction_base_ap": P332_AP_IDENTITY,
            "predecessor_run_id": P332_RUN_ID_HEX,
            "predecessor_result": P332_RESULT_IDENTITY,
            "predecessor_ap": P332_AP_IDENTITY,
            "fresh_run_id": P333_RUN_ID_HEX,
            "p332_source_closure_reopened": True,
        }
    )
    result["preservation"].update(
        {
            "p332_consumed_candidate_distinct": True,
            "p332_source_closure_reopened": True,
            "runtime_delta_open_entry_diagnostic_only": True,
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
            "resident_sessions": 2,
            "resident_reconnects": 0,
            "same_tty_fd_required": True,
            "fixed_p330_commands": True,
            "rollback_untouched": True,
        }
    )
    result["compatibility_labels"] = {
        "engine": "P332 exact-loaded",
        "runtime_input": "exact P332 runtime include",
        "wire_namespace": "P330 authenticated framing plus stage-0 diagnostic",
        "presentation_only": True,
    }
    for section in ("framed_exec", "resident"):
        result[section].update(
            {
                "runtime_contract": runtime.CONTRACT_ID,
                "observer_contract": observer.CONTRACT_ID,
                "entry_diagnostic_stage": 0,
                "entry_diagnostic_before_console": True,
            }
        )
    result["limitations"] = [
        "P333 adds only a stage-0 diagnostic before each P332 console call.",
        "The diagnostic localizes entry and does not itself prove OPEN parsing.",
        "The two sessions remain bounded to one tty FD with no reconnect.",
        "Only boot is packaged; exact Magisk rollback remains mandatory.",
        "This host build creates no device, approval, F1, or live authority.",
    ]
    repair = result["lineage"].get("runtime_repair")
    if isinstance(repair, dict):
        repair["run_id_hex"] = P333_RUN_ID_HEX
        repair["runtime_contract"] = runtime.CONTRACT_ID
        repair["input_lineage"] = "p332-runtime-include"
    return result


for module in (_ENGINE, _P328):
    module._predecessor = _predecessor
    module._current_sources = _current_sources
    module._copy_source_closure = _copy_source_closure
    module._load_packager = _load_packager
_ENGINE.repair = _RuntimeCompat
_ENGINE._json_bytes = lambda value: _P328._json_bytes(_normalize_result(value))
_P328._normalize_result = _normalize_result


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    auth_key: Path | str | None = None,
    audit_only: bool = False,
) -> dict[str, Any]:
    output_root = output_root.absolute()
    _predecessor()
    try:
        if audit_only:
            return _P328.audit_existing(
                output_root,
                auth_key=DEFAULT_AUTH_KEY_PATH if auth_key is None else auth_key,
            )
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
    return build_result(output_root, auth_key=auth_key, audit_only=True)


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
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
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
