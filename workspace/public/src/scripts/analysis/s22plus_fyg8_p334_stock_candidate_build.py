#!/usr/bin/env python3
"""Build the P3.34 boot-only first-console-return candidate.

The exact P3.33 builder is the packaging engine.  P3.34 starts from P3.33's
12-member source closure and changes only its runtime include through the
reviewed outer return-code transform.  The console body and wire protocol are
unchanged.  No kernel rebuild, device access, or Odin invocation occurs here.
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

import s22plus_fyg8_p334_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p334_first_read_rc_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p334_first_read_rc_runtime as runtime  # noqa: E402
import s22plus_fyg8_p334_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P333_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p333_stock_candidate_build.py"
P333_BUILDER_IDENTITY = {
    "size": 19_134,
    "sha256": "704032d3327f27d1a3c18834e5374e88de35071aa58f227e88d61fdb216be9e7",
}
P333_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p333/"
    "stock-candidate-build-v1-20260904-01"
)
P333_RESULT = P333_OUTPUT / "result.json"
P333_RESULT_IDENTITY = {
    "size": 48_548,
    "sha256": "9c3697ab3e9bba7a9d8e0ed038d0bbe69cf0e2c3da333cd433e338149398d03c",
}
P333_RUN_ID_HEX = "c333f1e0a90b5e6d7c8a9b0c1d2e3f7b"
P333_RUN_ID = bytes.fromhex(P333_RUN_ID_HEX)
P334_RUN_ID_HEX = "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b"
P334_RUN_ID = bytes.fromhex(P334_RUN_ID_HEX)
P333_AP_IDENTITY = dict(artifact.P333_AP_IDENTITY)

DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p334/"
    "stock-candidate-build-v1-20260904-01"
)
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
SCHEMA = "s22plus-fyg8-p334-stock-candidate-build-v1"
VERDICT = "PASS_P334_STOCK_CANDIDATE_BUILD_H0_FIRST_CONSOLE_RETURN"
STATUS = "IMPLEMENTED_H0_FIRST_CONSOLE_RETURN_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class AuditError(RuntimeError):
    """The exact P3.33 lineage or P3.34 closure differs."""


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


def _load_p333_builder() -> types.ModuleType:
    payload = _stable(
        P333_BUILDER_SOURCE,
        "P3.33 builder source",
        2 << 20,
        P333_BUILDER_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p333_builder_bound_for_p334")
    module.__file__ = str(P333_BUILDER_SOURCE)
    module.__package__ = ""
    previous = sys.modules.get(module.__name__)
    sys.modules[module.__name__] = module
    try:
        exec(compile(payload, str(P333_BUILDER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P3.33 builder source failed to load") from exc
    finally:
        if previous is None:
            sys.modules.pop(module.__name__, None)
        else:
            sys.modules[module.__name__] = previous
    if getattr(module, "P333_RUN_ID_HEX", None) != P333_RUN_ID_HEX:
        raise AuditError("P3.33 builder binding differs")
    return module


_P333 = _load_p333_builder()
_P328 = _P333._P328
_ENGINE = _P333._ENGINE


def _all_modules() -> list[types.ModuleType]:
    result = [_P333]
    for module in _P333._all_modules():
        if module not in result:
            result.append(module)
    return result


def _rebind_engine() -> None:
    for module in _all_modules():
        for name, value in tuple(vars(module).items()):
            if value == P333_RUN_ID:
                setattr(module, name, P334_RUN_ID)
            elif value == P333_RUN_ID_HEX:
                setattr(module, name, P334_RUN_ID_HEX)
            elif callable(value) and getattr(value, "__kwdefaults__", None):
                defaults = dict(value.__kwdefaults__)
                changed = False
                for key, current in tuple(defaults.items()):
                    if current == P333_RUN_ID:
                        defaults[key] = P334_RUN_ID
                        changed = True
                    elif current == P333_RUN_ID_HEX:
                        defaults[key] = P334_RUN_ID_HEX
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
            "P328_RUN_ID": P334_RUN_ID,
            "P328_RUN_ID_HEX": P334_RUN_ID_HEX,
            "P330_RUN_ID": P334_RUN_ID,
            "P330_RUN_ID_HEX": P334_RUN_ID_HEX,
            "P331_RUN_ID": P334_RUN_ID,
            "P331_RUN_ID_HEX": P334_RUN_ID_HEX,
            "P333_RUN_ID": P334_RUN_ID,
            "P333_RUN_ID_HEX": P334_RUN_ID_HEX,
            "DEFAULT_OUTPUT_ROOT": DEFAULT_OUTPUT_ROOT,
            "DEFAULT_AUTH_KEY_PATH": DEFAULT_AUTH_KEY_PATH,
            "SCHEMA": SCHEMA,
            "VERDICT": VERDICT,
            "STATUS": STATUS,
            "TARGET": TARGET,
        }.items():
            if hasattr(module, name):
                setattr(module, name, value)
    _ENGINE.P321_OUTPUT = P333_OUTPUT
    _ENGINE.P322_RUN_ID = P334_RUN_ID
    _ENGINE.P322_RUN_ID_HEX = P334_RUN_ID_HEX
    _ENGINE.P322_ARTIFACT_SOURCE = artifact.P334_ARTIFACT_SOURCE
    _ENGINE.P322_REPAIR_SOURCE = Path(runtime.__file__).resolve()
    _ENGINE.P322_ADAPTER_SOURCE = adapter.P334_ADAPTER_SOURCE


_rebind_engine()


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    payload = _stable(
        P333_RESULT,
        "P3.33 result",
        4 << 20,
        P333_RESULT_IDENTITY,
        mode=0o400,
    )
    value = _strict_json(payload, "P3.33 result")
    candidate = value.get("phase2", {}).get("candidate")
    if (
        value.get("schema") != "s22plus-fyg8-p333-stock-candidate-build-v1"
        or value.get("run_id_hex") != P333_RUN_ID_HEX
        or value.get("target") != TARGET
        or not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("a", {}).get("ap_tar_md5") != P333_AP_IDENTITY
        or candidate.get("a", {}).get("package", {}).get("members")
        != ["boot.img.lz4"]
        or not isinstance(value.get("source_closure"), dict)
        or len(value["source_closure"]) != 12
    ):
        raise AuditError("P3.33 predecessor result differs")
    for name, expected in sorted(value["source_closure"].items()):
        _stable(
            P333_OUTPUT / "stock-sources" / name,
            f"P3.33 source {name}",
            2 << 20,
            expected,
            mode=0o400,
        )
    for label in ("a", "b"):
        _stable(
            P333_OUTPUT / f"candidate-{label}/odin4/AP.tar.md5",
            f"P3.33 candidate {label}",
            128 << 20,
            P333_AP_IDENTITY,
        )
    source = _stable(
        P333_BUILDER_SOURCE,
        "P3.33 builder source",
        2 << 20,
        P333_BUILDER_IDENTITY,
    )
    return value, payload, source


def _current_sources() -> dict[str, bytes]:
    paths = {
        "p328_stock_candidate_build.py": SELF_SOURCE,
        "p328_artifact_identity.py": artifact.P334_ARTIFACT_SOURCE,
        "p328_stock_process_v2_adapter.py": adapter.P334_ADAPTER_SOURCE,
        "p328_authenticated_exec_runtime.py": Path(runtime.__file__).resolve(),
        "p328_authenticated_acm_observer.py": Path(observer.__file__).resolve(),
    }
    return {
        name: _stable(path, f"P3.34 source {name}", 2 << 20)
        for name, path in paths.items()
    }


def _active_key() -> bytes:
    key = getattr(_P328, "_ACTIVE_AUTH_KEY", None)
    if type(key) is not bytes or len(key) != artifact.AUTH_KEY_SIZE:
        raise AuditError("P3.34 auth key is not bound")
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
            "run_id_hex": P334_RUN_ID_HEX,
            "input_lineage": "p333-runtime-include",
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
            "first_console_return_checkpoint_only": True,
            "first_console_return_prefix": runtime.P334_DETAIL_PREFIX,
            "first_console_return_sentinel": runtime.P334_DETAIL_SENTINEL,
            "first_read_interpretation_requires_stage0_without_stage1": True,
            "console_body_changed": False,
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
            P333_OUTPUT / "stock-sources" / name,
            f"P3.33 source {name}",
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
        raise AuditError("P3.33 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, repair


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, packager, source = _P333._load_packager()
    packager.RUN_ID = P334_RUN_ID
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
            raise AuditError("P3.34 transformed runtime differs")
        if isinstance(receipt.get("default_commands"), (tuple, list)):
            receipt["default_commands"] = [
                identity(item) for item in receipt["default_commands"]
            ]
        return receipt


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(_P333._normalize_result(value))
    candidate = result["phase2"]["candidate"]
    current_ap = candidate["a"]["ap_tar_md5"]
    if candidate["a"] != candidate["b"] or current_ap == P333_AP_IDENTITY:
        raise AuditError("P3.34 candidate repeats P3.33 or differs A/B")
    for label in ("a", "b"):
        package = candidate[label]["package"]
        package.update(
            {
                "schema": "s22plus_fyg8_p334_boot_only_first_console_return_package_v1",
                "verdict": "PASS_P334_DETERMINISTIC_BOOT_ONLY_FIRST_CONSOLE_RETURN_H0",
            }
        )
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "status": STATUS,
            "run_id_hex": P334_RUN_ID_HEX,
            "differs_from_consumed_p333": True,
        }
    )
    result["lineage"].update(
        {
            "construction_base_run_id": P333_RUN_ID_HEX,
            "construction_base_result": P333_RESULT_IDENTITY,
            "construction_base_ap": P333_AP_IDENTITY,
            "predecessor_run_id": P333_RUN_ID_HEX,
            "predecessor_result": P333_RESULT_IDENTITY,
            "predecessor_ap": P333_AP_IDENTITY,
            "fresh_run_id": P334_RUN_ID_HEX,
            "p333_source_closure_reopened": True,
        }
    )
    result["preservation"].update(
        {
            "p333_consumed_candidate_distinct": True,
            "p333_source_closure_reopened": True,
            "runtime_delta_first_console_return_only": True,
            "entry_diagnostic_stage": 0,
            "entry_diagnostic_before_console": True,
            "first_console_return_checkpoint_only": True,
            "first_console_return_prefix": runtime.P334_DETAIL_PREFIX,
            "first_console_return_sentinel": runtime.P334_DETAIL_SENTINEL,
            "first_read_interpretation_requires_stage0_without_stage1": True,
            "console_body_changed": False,
            "resident_sessions": 2,
            "resident_reconnects": 0,
            "same_tty_fd_required": True,
            "fixed_p330_commands": True,
            "rollback_untouched": True,
        }
    )
    result["compatibility_labels"] = {
        "engine": "P333 exact-loaded",
        "runtime_input": "exact P333 runtime include",
        "wire_namespace": "unchanged P330 authenticated framing plus P333 stage-0 diagnostic",
        "presentation_only": True,
    }
    for section in ("framed_exec", "resident"):
        result[section].update(
            {
                "runtime_contract": runtime.CONTRACT_ID,
                "observer_contract": observer.CONTRACT_ID,
                "entry_diagnostic_stage": 0,
                "entry_diagnostic_before_console": True,
                "first_console_return_checkpoint_only": True,
                "first_read_interpretation_requires_stage0_without_stage1": True,
            }
        )
    result["limitations"] = [
        "P334 preserves both P333 stage-0 diagnostics and changes only the outer first-console return receipt.",
        "The checkpoint detail identifies the first read boundary only with stage 0 and no later diagnostic.",
        "The two sessions remain bounded to one tty FD with no reconnect.",
        "Only boot is packaged; exact Magisk rollback remains mandatory.",
        "This host build creates no device, approval, F1, or live authority.",
    ]
    repair = result["lineage"].get("runtime_repair")
    if isinstance(repair, dict):
        repair["run_id_hex"] = P334_RUN_ID_HEX
        repair["runtime_contract"] = runtime.CONTRACT_ID
        repair["input_lineage"] = "p333-runtime-include"
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
