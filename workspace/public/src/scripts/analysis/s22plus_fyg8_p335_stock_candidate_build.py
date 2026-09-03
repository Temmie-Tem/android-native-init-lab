#!/usr/bin/env python3
"""Build the P3.35 boot-only attended-resident candidate.

The exact P3.34 builder remains the packaging engine.  P3.35 reopens only the
P3.34 result/source closure, transforms its one runtime include through the
reviewed P3.35 runtime, and binds the new observer/runtime wrappers.  Build
and audit are host-only; no device, ADB, Odin, or live authority is created.
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
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p335_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p335_stock_process_v2_adapter as adapter  # noqa: E402

try:  # The parser worker may still be finalizing these two new sources.
    import s22plus_fyg8_p335_retained_listener_runtime as runtime  # noqa: E402
except ModuleNotFoundError:
    runtime = None
try:
    import s22plus_fyg8_p335_retained_listener_acm_observer as observer  # noqa: E402
except ModuleNotFoundError:
    observer = None


SELF_SOURCE = Path(__file__).resolve()
P334_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p334_stock_candidate_build.py"
P334_BUILDER_IDENTITY = {
    "size": 20_072,
    "sha256": "6a8b8c56ef5741889b9e53e9c23417e76c6b6cb01f1efab6452d64dcf9a93f55",
}
P334_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p334/"
    "stock-candidate-build-v1-20260904-01"
)
P334_RESULT = P334_OUTPUT / "result.json"
P334_RESULT_IDENTITY = {
    "size": 50_133,
    "sha256": "765b70a794503e9819940926af3e975334368f551c5c766f5fd754fa8ea2868a",
}
P334_RUN_ID_HEX = "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b"
P334_RUN_ID = bytes.fromhex(P334_RUN_ID_HEX)
P335_RUN_ID_HEX = "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"
P335_RUN_ID = bytes.fromhex(P335_RUN_ID_HEX)
# Compatibility names consumed by the exact-loaded P3.34 static seam.  They
# describe the current P3.35 candidate, not an invitation to reuse P3.33.
P333_RUN_ID_HEX = P335_RUN_ID_HEX
P333_RUN_ID = P335_RUN_ID
P332_RUN_ID_HEX = P335_RUN_ID_HEX
P332_RUN_ID = P335_RUN_ID
P331_RUN_ID_HEX = P335_RUN_ID_HEX
P331_RUN_ID = P335_RUN_ID
P330_RUN_ID_HEX = P335_RUN_ID_HEX
P330_RUN_ID = P335_RUN_ID
P328_RUN_ID_HEX = P335_RUN_ID_HEX
P328_RUN_ID = P335_RUN_ID
P334_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "d79ecf0721604dc30b32777e6a8bfdda54609198b09e3cf081d62446fcbaf7dc",
}
P335_RUNTIME_SOURCE = REVALIDATION / "s22plus_fyg8_p335_retained_listener_runtime.py"
P335_RUNTIME_SOURCE_IDENTITY = {
    "size": 32_035,
    "sha256": "d13ed7fe6fb40f5f68e829369ef75975f53a7796722bde566b2ce7f544ee05e7",
}
P335_OBSERVER_SOURCE = REVALIDATION / "s22plus_fyg8_p335_retained_listener_acm_observer.py"
P335_OBSERVER_SOURCE_IDENTITY = {
    "size": 47_411,
    "sha256": "26e2c98a7ba6a660f0c4c85b2432082303deb1b076304f20d1899ac125363281",
}
INITIAL_SESSION_COUNT = 3
INITIAL_RECONNECT_COUNT = 1

DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p335/"
    "stock-candidate-build-v1-20260904-03"
)
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
SCHEMA = "s22plus-fyg8-p335-stock-candidate-build-v1"
VERDICT = "PASS_P335_STOCK_CANDIDATE_BUILD_H0_ATTENDED_RESIDENT"
STATUS = "IMPLEMENTED_H0_ATTENDED_RESIDENT_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class AuditError(RuntimeError):
    """The exact P3.34 lineage or P3.35 closure differs."""


def _legacy_runtime_alias() -> types.ModuleType | None:
    """Provide legacy P3.34 presentation names while loading its engine."""
    if runtime is None:
        return None
    alias = types.ModuleType("s22plus_fyg8_p334_first_read_rc_runtime_for_p335")
    alias.__dict__.update(vars(runtime))
    alias.P334_DETAIL_PREFIX = getattr(runtime, "P334_DETAIL_PREFIX", 0xB000)
    alias.P334_DETAIL_SENTINEL = getattr(runtime, "P334_DETAIL_SENTINEL", 0xBFFF)
    return alias


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


def _load_p334_builder() -> types.ModuleType | None:
    if runtime is None or observer is None:
        return None
    payload = _stable(
        P334_BUILDER_SOURCE,
        "P3.34 builder source",
        2 << 20,
        P334_BUILDER_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p334_builder_bound_for_p335")
    module.__file__ = str(P334_BUILDER_SOURCE)
    module.__package__ = ""
    legacy_runtime = _legacy_runtime_alias()
    aliases = {
        "s22plus_fyg8_p334_artifact_identity": artifact,
        "s22plus_fyg8_p334_stock_process_v2_adapter": adapter,
        "s22plus_fyg8_p334_first_read_rc_runtime": legacy_runtime,
        "s22plus_fyg8_p334_first_read_rc_acm_observer": observer,
    }
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in aliases}
    try:
        sys.modules.update(aliases)
        exec(compile(payload, str(P334_BUILDER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P3.34 builder source failed to load") from exc
    finally:
        for name, old in previous.items():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
    if getattr(module, "P334_RUN_ID_HEX", None) != P334_RUN_ID_HEX:
        raise AuditError("P3.34 builder binding differs")
    return module


_P334 = _load_p334_builder()
if _P334 is not None:
    _P328 = _P334._P328
    _ENGINE = _P334._ENGINE
else:
    _P328 = None
    _ENGINE = None


def _all_modules() -> list[types.ModuleType]:
    if _P334 is None:
        return []
    result = [_P334]
    for module in _P334._all_modules():
        if module not in result:
            result.append(module)
    return result


def _rebind_engine() -> None:
    if _P334 is None:
        return
    for module in _all_modules():
        for name, value in tuple(vars(module).items()):
            if value == P334_RUN_ID:
                setattr(module, name, P335_RUN_ID)
            elif value == P334_RUN_ID_HEX:
                setattr(module, name, P335_RUN_ID_HEX)
            elif callable(value) and getattr(value, "__kwdefaults__", None):
                defaults = dict(value.__kwdefaults__)
                changed = False
                for key, current in tuple(defaults.items()):
                    if current == P334_RUN_ID:
                        defaults[key] = P335_RUN_ID
                        changed = True
                    elif current == P334_RUN_ID_HEX:
                        defaults[key] = P335_RUN_ID_HEX
                        changed = True
                if changed:
                    value.__kwdefaults__ = defaults
    for module in (*_all_modules(), _P328, _ENGINE):
        if module is None:
            continue
        for name, value in {
            "artifact": artifact,
            "adapter": adapter,
            "resident_runtime": runtime,
            "framed_runtime": runtime,
            "resident_observer": observer,
            "framed_observer": observer,
            "P328_RUN_ID": P335_RUN_ID,
            "P328_RUN_ID_HEX": P335_RUN_ID_HEX,
            "P330_RUN_ID": P335_RUN_ID,
            "P330_RUN_ID_HEX": P335_RUN_ID_HEX,
            "P331_RUN_ID": P335_RUN_ID,
            "P331_RUN_ID_HEX": P335_RUN_ID_HEX,
            "P332_RUN_ID": P335_RUN_ID,
            "P332_RUN_ID_HEX": P335_RUN_ID_HEX,
            "P333_RUN_ID": P335_RUN_ID,
            "P333_RUN_ID_HEX": P335_RUN_ID_HEX,
            "P334_RUN_ID": P335_RUN_ID,
            "P334_RUN_ID_HEX": P335_RUN_ID_HEX,
            "DEFAULT_OUTPUT_ROOT": DEFAULT_OUTPUT_ROOT,
            "DEFAULT_AUTH_KEY_PATH": DEFAULT_AUTH_KEY_PATH,
            "SCHEMA": SCHEMA,
            "VERDICT": VERDICT,
            "STATUS": STATUS,
            "TARGET": TARGET,
        }.items():
            if hasattr(module, name):
                setattr(module, name, value)
    _ENGINE.P321_OUTPUT = P334_OUTPUT
    _ENGINE.P322_RUN_ID = P335_RUN_ID
    _ENGINE.P322_RUN_ID_HEX = P335_RUN_ID_HEX
    _ENGINE.P322_ARTIFACT_SOURCE = artifact.P335_ARTIFACT_SOURCE
    _ENGINE.P322_REPAIR_SOURCE = Path(runtime.__file__).resolve()
    _ENGINE.P322_ADAPTER_SOURCE = adapter.P335_ADAPTER_SOURCE


_rebind_engine()


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    payload = _stable(
        P334_RESULT,
        "P3.34 result",
        4 << 20,
        P334_RESULT_IDENTITY,
        mode=0o400,
    )
    value = _strict_json(payload, "P3.34 result")
    candidate = value.get("phase2", {}).get("candidate")
    if (
        value.get("schema") != "s22plus-fyg8-p334-stock-candidate-build-v1"
        or value.get("run_id_hex") != P334_RUN_ID_HEX
        or value.get("target") != TARGET
        or not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("a", {}).get("ap_tar_md5") != P334_AP_IDENTITY
        or candidate.get("a", {}).get("package", {}).get("members") != ["boot.img.lz4"]
        or not isinstance(value.get("source_closure"), dict)
        or len(value["source_closure"]) != 12
    ):
        raise AuditError("P3.34 predecessor result differs")
    for name, expected in sorted(value["source_closure"].items()):
        _stable(
            P334_OUTPUT / "stock-sources" / name,
            f"P3.34 source {name}",
            2 << 20,
            expected,
            mode=0o400,
        )
    for label in ("a", "b"):
        _stable(
            P334_OUTPUT / f"candidate-{label}/odin4/AP.tar.md5",
            f"P3.34 candidate {label}",
            128 << 20,
            P334_AP_IDENTITY,
        )
    source = _stable(
        P334_BUILDER_SOURCE,
        "P3.34 builder source",
        2 << 20,
        P334_BUILDER_IDENTITY,
    )
    return value, payload, source


def _current_sources() -> dict[str, bytes]:
    paths = {
        "p328_stock_candidate_build.py": SELF_SOURCE,
        "p328_artifact_identity.py": artifact.P335_ARTIFACT_SOURCE,
        "p328_stock_process_v2_adapter.py": adapter.P335_ADAPTER_SOURCE,
        "p328_authenticated_exec_runtime.py": P335_RUNTIME_SOURCE,
        "p328_authenticated_acm_observer.py": P335_OBSERVER_SOURCE,
    }
    expected = {
        "p328_authenticated_exec_runtime.py": P335_RUNTIME_SOURCE_IDENTITY,
        "p328_authenticated_acm_observer.py": P335_OBSERVER_SOURCE_IDENTITY,
    }
    return {
        name: _stable(path, f"P3.35 source {name}", 2 << 20, expected.get(name))
        for name, path in paths.items()
    }


def _active_key() -> bytes:
    if _P328 is None:
        raise AuditError("P3.35 builder dependencies are unavailable")
    key = getattr(_P328, "_ACTIVE_AUTH_KEY", None)
    if type(key) is not bytes or len(key) != artifact.AUTH_KEY_SIZE:
        raise AuditError("P3.35 auth key is not bound")
    return key


def _runtime_transform(before: bytes, key: bytes) -> tuple[bytes, dict[str, Any]]:
    if runtime is None:
        raise AuditError("P3.35 runtime source is unavailable")
    _stable(
        P335_RUNTIME_SOURCE,
        "P3.35 runtime source",
        2 << 20,
        P335_RUNTIME_SOURCE_IDENTITY,
    )
    after = runtime.transform_runtime_include(before, key)
    validator = getattr(runtime, "validate_p335_transform", None)
    if validator is None:
        validator = runtime.validate_transform
    receipt = dict(
        validator(
            before,
            after,
            auth_key_sha256=hashlib.sha256(key).hexdigest(),
        )
    )
    for holder in (receipt, receipt.get("predecessor")):
        if isinstance(holder, dict) and isinstance(
            holder.get("default_commands"), (tuple, list)
        ):
            holder["default_commands"] = [
                identity(item) if type(item) is bytes else item
                for item in holder["default_commands"]
            ]
    receipt.update(
        {
            "authenticated": True,
            "auth_key": artifact.validate_auth_key(key),
            "auth_key_path_published": False,
            "runtime_contract": runtime.CONTRACT_ID,
            "run_id_hex": P335_RUN_ID_HEX,
            "input_lineage": "p334-runtime-include",
            "initial_session_count": getattr(runtime, "INITIAL_SESSION_COUNT", INITIAL_SESSION_COUNT),
            "initial_reconnect_count": getattr(runtime, "INITIAL_RECONNECT_COUNT", INITIAL_RECONNECT_COUNT),
            "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
            "resident_lease_duration_sec": 3_600,
            "resident_lease_action_cap": 16,
            "per_boot_identity_required": True,
            "console_body_changed": False,
        }
    )
    receipt.pop("auth_key_path", None)
    receipt.pop("key_path", None)
    return after, receipt


def _copy_source_closure(
    output_root: Path, predecessor: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if _ENGINE is None:
        raise AuditError("P3.35 packaging engine is unavailable")
    source_root = output_root / "stock-sources"
    _ENGINE.p321._mkdir(source_root)
    receipts: dict[str, dict[str, Any]] = {}
    repair: dict[str, Any] | None = None
    runtime_name = "s22plus_fyg8_p290_e3_runtime.inc.c"
    key = _active_key()
    for name, expected_identity in sorted(predecessor["source_closure"].items()):
        before = _stable(
            P334_OUTPUT / "stock-sources" / name,
            f"P3.34 source {name}",
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
        raise AuditError("P3.34 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, repair


def _load_packager() -> tuple[Any, Any, bytes]:
    module = _require_builder()
    helper, packager, source = module._load_packager()
    packager.RUN_ID = P335_RUN_ID
    packager._bind_tools()
    for name, value in {
        "artifact": artifact,
        "adapter": adapter,
        "resident_runtime": runtime,
        "framed_runtime": runtime,
        "resident_observer": observer,
        "framed_observer": observer,
        "RUN_ID": P335_RUN_ID,
        "P334_RUN_ID": P335_RUN_ID,
        "P334_RUN_ID_HEX": P335_RUN_ID_HEX,
    }.items():
        if hasattr(packager, name):
            setattr(packager, name, value)
    return helper, packager, source


def _require_builder() -> types.ModuleType:
    if _P334 is None or _P328 is None or _ENGINE is None:
        raise AuditError("P3.35 builder dependencies are unavailable")
    return _P334


class _RuntimeCompat:
    RuntimeRepairError = ValueError

    @staticmethod
    def transform_runtime_include(value: bytes) -> bytes:
        return _runtime_transform(value, _active_key())[0]

    @staticmethod
    def validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
        expected, receipt = _runtime_transform(before, _active_key())
        if expected != after:
            raise AuditError("P3.35 transformed runtime differs")
        return receipt


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    module = _require_builder()
    result = copy.deepcopy(module._normalize_result(value))
    candidate = result["phase2"]["candidate"]
    current_ap = candidate["a"]["ap_tar_md5"]
    if (
        candidate["a"] != candidate["b"]
        or current_ap == P334_AP_IDENTITY
        or current_ap == getattr(artifact, "P333_AP_IDENTITY", {})
    ):
        raise AuditError("P3.35 candidate repeats a consumed predecessor or differs A/B")
    for label in ("a", "b"):
        package = candidate[label]["package"]
        package.update(
            {
                "schema": "s22plus_fyg8_p335_boot_only_attended_resident_package_v1",
                "verdict": "PASS_P335_DETERMINISTIC_BOOT_ONLY_ATTENDED_RESIDENT_H0",
            }
        )
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "status": STATUS,
            "run_id_hex": P335_RUN_ID_HEX,
            "differs_from_consumed_p334": True,
        }
    )
    result["lineage"].update(
        {
            "construction_base_run_id": P334_RUN_ID_HEX,
            "construction_base_result": P334_RESULT_IDENTITY,
            "construction_base_ap": P334_AP_IDENTITY,
            "predecessor_run_id": P334_RUN_ID_HEX,
            "predecessor_result": P334_RESULT_IDENTITY,
            "predecessor_ap": P334_AP_IDENTITY,
            "fresh_run_id": P335_RUN_ID_HEX,
            "p334_source_closure_reopened": True,
        }
    )
    result["preservation"].update(
        {
            "p334_consumed_candidate_distinct": True,
            "p334_source_closure_reopened": True,
            "runtime_delta_attended_resident_only": True,
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "resident_sessions": INITIAL_SESSION_COUNT,
            "resident_reconnects": INITIAL_RECONNECT_COUNT,
            "logical_same_tty": True,
            "same_tty_fd_required": True,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "per_boot_identity_required": True,
            "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
            "resident_lease_duration_sec": 3_600,
            "resident_lease_action_cap": 16,
            "listener_wait_after_proof": True,
            "action_retry": False,
            "rollback_untouched": True,
            "interactive_pty": False,
            "arbitrary_file_transfer": False,
            "persistent_state": False,
        }
    )
    result["compatibility_labels"] = {
        "engine": "P334 exact-loaded",
        "runtime_input": "exact P334 runtime include",
        "wire_namespace": "unchanged P334 authenticated framing and fixed command ABI",
        "presentation_only": True,
    }
    for section in ("framed_exec", "resident"):
        if isinstance(result.get(section), dict):
            result[section].update(
                {
                    "runtime_contract": runtime.CONTRACT_ID,
                    "observer_contract": observer.CONTRACT_ID,
                    "initial_session_count": INITIAL_SESSION_COUNT,
                    "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
                    "resident_sessions": INITIAL_SESSION_COUNT,
                    "resident_reconnects": INITIAL_RECONNECT_COUNT,
                    "same_tty_fd_required": True,
                    "host_tty_close_reopen": True,
                    "transport_reconnect": True,
                    "fixed_heartbeat_only": False,
                    "fixed_p330_commands": True,
                    "per_boot_identity_required": True,
                    "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
                    "resident_lease_duration_sec": 3_600,
                    "resident_lease_action_cap": 16,
                    "listener_wait_after_proof": True,
                    "action_retry": False,
                }
            )
    result["limitations"] = [
        "P335 reuses the exact P3.34 packaging engine and transforms only its runtime include.",
        "Initial proof is two same-FD sessions followed by one exact host close/reopen session.",
        "All initial and later actions use the fixed three-command named catalog with no retry.",
        "The listener lease is current-boot, attended, bounded to one hour and 16 actions.",
        "Only boot is packaged; exact Magisk rollback remains mandatory.",
        "This host build creates no device, approval, F1, or live authority.",
    ]
    repair = result.get("lineage", {}).get("runtime_repair")
    if isinstance(repair, dict):
        repair.update(
            {
                "run_id_hex": P335_RUN_ID_HEX,
                "runtime_contract": runtime.CONTRACT_ID,
                "input_lineage": "p334-runtime-include",
                "initial_session_count": INITIAL_SESSION_COUNT,
                "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
                "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
                "resident_lease_duration_sec": 3_600,
                "resident_lease_action_cap": 16,
                "per_boot_identity_required": True,
            }
        )
    return result


if _P334 is not None:
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
    _require_builder()
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
                "live_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


__all__ = [name for name in globals() if not name.startswith("_")]


if __name__ == "__main__":
    raise SystemExit(main())
