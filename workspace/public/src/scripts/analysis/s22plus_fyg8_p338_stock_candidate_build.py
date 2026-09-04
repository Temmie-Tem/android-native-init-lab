#!/usr/bin/env python3
"""Build the P3.38 boot-only first-OPEN branch candidate (host-only).

The exact P3.37 builder is loaded into a private module graph and retained as
the packaging engine.  P3.38 reopens only the verified P3.37 result/source
closure, transforms its one runtime include through the P3.38 runtime, and
binds the P3.38 observer.  The package remains A/B-equal and boot-only; this
module performs no device, ADB, Odin, or live-authority action.
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

import s22plus_fyg8_p338_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p338_stock_process_v2_adapter as adapter  # noqa: E402
import s22plus_fyg8_p338_open_read_branch_runtime as runtime  # noqa: E402
import s22plus_fyg8_p338_open_read_branch_acm_observer as observer  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P337_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p337_stock_candidate_build.py"
P337_BUILDER_IDENTITY = {
    "size": 28_499,
    "sha256": "3ad070a5bd93d1bc74a82d6dde528410b1b25a2ca30650a582d99ba47ef42dfc",
}
P337_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p337/"
    "stock-candidate-build-v1-20260904-06"
)
P337_RESULT = P337_OUTPUT / "result.json"
P337_RESULT_IDENTITY = {
    "size": 58_673,
    "sha256": "8a034575ba71eff0234f28e688c3f9c7c46270407134678b4791ee13603ed0f8",
}
P337_RUN_ID_HEX = "c337f1e0a90b5e6d7c8a9b0c1d2e3f3b"
P337_RUN_ID = bytes.fromhex(P337_RUN_ID_HEX)
P338_RUN_ID_HEX = "c338f1e0a90b5e6d7c8a9b0c1d2e3f2b"
P338_RUN_ID = bytes.fromhex(P338_RUN_ID_HEX)
# Compatibility names required while the exact-loaded predecessor static
# seam recursively imports its historical builder labels.
P334_RUN_ID_HEX = P338_RUN_ID_HEX
P334_RUN_ID = P338_RUN_ID
P333_RUN_ID_HEX = P338_RUN_ID_HEX
P333_RUN_ID = P338_RUN_ID
P332_RUN_ID_HEX = P338_RUN_ID_HEX
P332_RUN_ID = P338_RUN_ID
P331_RUN_ID_HEX = P338_RUN_ID_HEX
P331_RUN_ID = P338_RUN_ID
P330_RUN_ID_HEX = P338_RUN_ID_HEX
P330_RUN_ID = P338_RUN_ID
P328_RUN_ID_HEX = P338_RUN_ID_HEX
P328_RUN_ID = P338_RUN_ID
P337_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "0c1f6f231180f27376cf4b3e0ed8a84b7347cc2e5d066cf87db53d91cc239466",
}
P334_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "d79ecf0721604dc30b32777e6a8bfdda54609198b09e3cf081d62446fcbaf7dc",
}
P333_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "1a6036b688ae92c94f459aee66e06a817e767aa615c6a7a9cb2a22b7d13487b3",
}
P332_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "e1309080879700445b88cef08eb3becb4e57e524f5467979857fc79ee36a9a9d",
}
P331_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "729b33c3bad602e1d5863fa8cfa6a4bdf22f194a74d378f7417879897bf4d08d",
}
P330_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b",
}
P338_RUNTIME_SOURCE = REVALIDATION / "s22plus_fyg8_p338_open_read_branch_runtime.py"
P338_OBSERVER_SOURCE = REVALIDATION / "s22plus_fyg8_p338_open_read_branch_acm_observer.py"
P338_ACTION_SOURCE = REVALIDATION / "s22plus_fyg8_p336_long_idle_action.py"
P338_RUNTIME_SOURCE_IDENTITY = dict(runtime.identity(P338_RUNTIME_SOURCE.read_bytes()))
P338_OBSERVER_SOURCE_IDENTITY = dict(observer.identity(P338_OBSERVER_SOURCE.read_bytes()))
P338_ACTION_SOURCE_IDENTITY = {
    "size": P338_ACTION_SOURCE.stat().st_size,
    "sha256": hashlib.sha256(P338_ACTION_SOURCE.read_bytes()).hexdigest(),
}
# Compatibility labels consumed by the exact-loaded P3.37 static seam.
P337_RUNTIME_SOURCE_IDENTITY = dict(P338_RUNTIME_SOURCE_IDENTITY)
P337_OBSERVER_SOURCE_IDENTITY = dict(P338_OBSERVER_SOURCE_IDENTITY)
P335_RUNTIME_SOURCE_IDENTITY = dict(P338_RUNTIME_SOURCE_IDENTITY)
P335_OBSERVER_SOURCE_IDENTITY = dict(P338_OBSERVER_SOURCE_IDENTITY)

INITIAL_SESSION_COUNT = 3
INITIAL_RECONNECT_COUNT = 1
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p338/"
    "stock-candidate-build-v1-20260904-07"
)
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
SCHEMA = "s22plus-fyg8-p338-stock-candidate-build-v1"
VERDICT = "PASS_P338_STOCK_CANDIDATE_BUILD_H0_OPEN_READ_BRANCH"
STATUS = "IMPLEMENTED_H0_OPEN_READ_BRANCH_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class AuditError(RuntimeError):
    """The exact P3.37 lineage or P3.38 closure differs."""


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


def _legacy_runtime_alias() -> types.ModuleType:
    alias = types.ModuleType("s22plus_fyg8_p334_first_read_rc_runtime_for_p338")
    alias.__dict__.update(vars(runtime))
    alias.P334_DETAIL_PREFIX = getattr(runtime, "P334_DETAIL_PREFIX", 0xB000)
    alias.P334_DETAIL_SENTINEL = getattr(runtime, "P334_DETAIL_SENTINEL", 0xBFFF)
    return alias


def _load_p337_builder() -> types.ModuleType:
    payload = _stable(
        P337_BUILDER_SOURCE,
        "P3.37 builder source",
        2 << 20,
        P337_BUILDER_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p337_builder_bound_for_p338")
    module.__file__ = str(P337_BUILDER_SOURCE)
    module.__package__ = ""
    aliases = {
        "s22plus_fyg8_p337_artifact_identity": artifact,
        "s22plus_fyg8_p337_stock_process_v2_adapter": adapter,
        "s22plus_fyg8_p337_open_read_diag_runtime": runtime,
        "s22plus_fyg8_p337_open_read_diag_acm_observer": observer,
        "s22plus_fyg8_p337_long_idle_runtime": runtime,
        "s22plus_fyg8_p337_long_idle_acm_observer": observer,
        "s22plus_fyg8_p337_retained_listener_runtime": runtime,
        "s22plus_fyg8_p337_retained_listener_acm_observer": observer,
        "s22plus_fyg8_p334_first_read_rc_runtime": _legacy_runtime_alias(),
    }
    # A test process may already have imported the consumed P337 graph.  Hide
    # historical module names while loading the exact predecessor so its
    # nested P322..P337 seams cannot reuse stale globals from that graph.
    hidden: dict[str, types.ModuleType] = {}
    for name in list(sys.modules):
        if name.startswith("s22plus_fyg8_p") and not name.startswith(
            "s22plus_fyg8_p338_"
        ):
            hidden[name] = sys.modules.pop(name)
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in aliases}
    try:
        sys.modules.update(aliases)
        exec(compile(payload, str(P337_BUILDER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P3.37 builder source failed to load") from exc
    finally:
        for name, old in previous.items():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
        for name, old in hidden.items():
            if name not in sys.modules:
                sys.modules[name] = old
    if getattr(module, "P337_RUN_ID_HEX", None) != P337_RUN_ID_HEX:
        raise AuditError("P3.37 builder binding differs")
    return module


_P337 = _load_p337_builder()
_P328 = _P337._P328
_ENGINE = _P337._ENGINE
_P337_LOAD_PACKAGER = _P337._load_packager


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
    modules = [_P337, *_modules(_P337)]
    for module in modules:
        for name, value in tuple(vars(module).items()):
            if value == P337_RUN_ID:
                setattr(module, name, P338_RUN_ID)
            elif value == P337_RUN_ID_HEX:
                setattr(module, name, P338_RUN_ID_HEX)
            elif callable(value) and getattr(value, "__kwdefaults__", None):
                defaults = dict(value.__kwdefaults__)
                changed = False
                for key, current in tuple(defaults.items()):
                    if current == P337_RUN_ID:
                        defaults[key] = P338_RUN_ID
                        changed = True
                    elif current == P337_RUN_ID_HEX:
                        defaults[key] = P338_RUN_ID_HEX
                        changed = True
                if changed:
                    value.__kwdefaults__ = defaults
        for name, value in {
            "artifact": artifact,
            "adapter": adapter,
            "resident_runtime": runtime,
            "framed_runtime": runtime,
            "resident_observer": observer,
            "framed_observer": observer,
            "P328_RUN_ID": P338_RUN_ID,
            "P328_RUN_ID_HEX": P338_RUN_ID_HEX,
            "P330_RUN_ID": P338_RUN_ID,
            "P330_RUN_ID_HEX": P338_RUN_ID_HEX,
            "P331_RUN_ID": P338_RUN_ID,
            "P331_RUN_ID_HEX": P338_RUN_ID_HEX,
            "P332_RUN_ID": P338_RUN_ID,
            "P332_RUN_ID_HEX": P338_RUN_ID_HEX,
            "P333_RUN_ID": P338_RUN_ID,
            "P333_RUN_ID_HEX": P338_RUN_ID_HEX,
            "P334_RUN_ID": P338_RUN_ID,
            "P334_RUN_ID_HEX": P338_RUN_ID_HEX,
            "P337_RUN_ID": P338_RUN_ID,
            "P337_RUN_ID_HEX": P338_RUN_ID_HEX,
            "DEFAULT_OUTPUT_ROOT": DEFAULT_OUTPUT_ROOT,
            "DEFAULT_AUTH_KEY_PATH": DEFAULT_AUTH_KEY_PATH,
            "SCHEMA": SCHEMA,
            "VERDICT": VERDICT,
            "STATUS": STATUS,
            "TARGET": TARGET,
        }.items():
            if hasattr(module, name):
                setattr(module, name, value)
    _ENGINE.P321_OUTPUT = P337_OUTPUT
    _ENGINE.P322_RUN_ID = P338_RUN_ID
    _ENGINE.P322_RUN_ID_HEX = P338_RUN_ID_HEX
    _ENGINE.P322_ARTIFACT_SOURCE = artifact.P338_ARTIFACT_SOURCE
    _ENGINE.P322_REPAIR_SOURCE = P338_RUNTIME_SOURCE
    _ENGINE.P322_ADAPTER_SOURCE = adapter.P338_ADAPTER_SOURCE


_rebind_engine()


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    payload = _stable(
        P337_RESULT,
        "P3.37 result",
        4 << 20,
        P337_RESULT_IDENTITY,
        mode=0o400,
    )
    value = _strict_json(payload, "P3.37 result")
    candidate = value.get("phase2", {}).get("candidate")
    if (
        value.get("schema") != "s22plus-fyg8-p337-stock-candidate-build-v1"
        or value.get("run_id_hex") != P337_RUN_ID_HEX
        or value.get("target") != TARGET
        or not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("a", {}).get("ap_tar_md5") != P337_AP_IDENTITY
        or candidate.get("a", {}).get("package", {}).get("members") != ["boot.img.lz4"]
        or not isinstance(value.get("source_closure"), dict)
        or len(value["source_closure"]) != 12
    ):
        raise AuditError("P3.37 predecessor result differs")
    for name, expected in sorted(value["source_closure"].items()):
        _stable(
            P337_OUTPUT / "stock-sources" / name,
            f"P3.37 source {name}",
            2 << 20,
            expected,
            mode=0o400,
        )
    for label in ("a", "b"):
        _stable(
            P337_OUTPUT / f"candidate-{label}/odin4/AP.tar.md5",
            f"P3.37 candidate {label}",
            128 << 20,
            P337_AP_IDENTITY,
        )
    source = _stable(
        P337_BUILDER_SOURCE,
        "P3.37 builder source",
        2 << 20,
        P337_BUILDER_IDENTITY,
    )
    return value, payload, source


def _current_sources() -> dict[str, bytes]:
    paths = {
        "p328_stock_candidate_build.py": SELF_SOURCE,
        "p328_artifact_identity.py": artifact.P338_ARTIFACT_SOURCE,
        "p328_stock_process_v2_adapter.py": adapter.P338_ADAPTER_SOURCE,
        "p328_authenticated_exec_runtime.py": P338_RUNTIME_SOURCE,
        "p328_authenticated_acm_observer.py": P338_OBSERVER_SOURCE,
    }
    expected = {
        "p328_authenticated_exec_runtime.py": P338_RUNTIME_SOURCE_IDENTITY,
        "p328_authenticated_acm_observer.py": P338_OBSERVER_SOURCE_IDENTITY,
    }
    return {
        name: _stable(path, f"P3.38 source {name}", 2 << 20, expected.get(name))
        for name, path in paths.items()
    }


def _active_key() -> bytes:
    key = getattr(_P328, "_ACTIVE_AUTH_KEY", None)
    if type(key) is not bytes or len(key) != artifact.AUTH_KEY_SIZE:
        raise AuditError("P3.38 auth key is not bound")
    return key


def _runtime_transform(before: bytes, key: bytes) -> tuple[bytes, dict[str, Any]]:
    _stable(
        P338_RUNTIME_SOURCE,
        "P3.38 runtime source",
        2 << 20,
        P338_RUNTIME_SOURCE_IDENTITY,
    )
    after = runtime.transform_runtime_include(before, key)
    receipt = dict(
        runtime.validate_transform(
            before,
            after,
            auth_key_sha256=hashlib.sha256(key).hexdigest(),
        )
    )
    for holder in (receipt, receipt.get("predecessor")):
        if isinstance(holder, dict) and isinstance(holder.get("default_commands"), (tuple, list)):
            holder["default_commands"] = [
                identity(item) if type(item) is bytes else item
                for item in holder["default_commands"]
            ]
        if isinstance(holder, dict) and isinstance(holder.get("open_read_branch_ordinals"), dict):
            holder["open_read_branch_ordinals"] = {
                str(key): value
                for key, value in holder["open_read_branch_ordinals"].items()
            }
    receipt.update(
        {
            "authenticated": True,
            "auth_key": artifact.validate_auth_key(key),
            "auth_key_path_published": False,
            "runtime_contract": runtime.CONTRACT_ID,
            "run_id_hex": P338_RUN_ID_HEX,
            "input_lineage": "p337-runtime-include",
            "initial_session_count": INITIAL_SESSION_COUNT,
            "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
            "fixed_p330_commands": True,
            "command_count_per_session": len(runtime.DEFAULT_COMMANDS),
            "first_open_failure_diagnostic": True,
            "later_action_open_before_resync": True,
            "later_action_max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
            "later_action_max_resync_bytes": observer.MAX_RESYNC_BYTES,
            "per_boot_identity_required": True,
            "resident_lease_schema": adapter.LEASE_SCHEMA,
            "resident_lease_duration_sec": 3_600,
            "resident_lease_action_cap": 16,
            "console_body_changed": True,
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
    receipts: dict[str, dict[str, Any]] = {}
    repair: dict[str, Any] | None = None
    key = _active_key()
    for name, expected_identity in sorted(predecessor["source_closure"].items()):
        before = _stable(
            P337_OUTPUT / "stock-sources" / name,
            f"P3.37 source {name}",
            2 << 20,
            expected_identity,
            mode=0o400,
        )
        after = before
        if name == "s22plus_fyg8_p290_e3_runtime.inc.c":
            after, repair = _runtime_transform(before, key)
            repair["before_identity"] = identity(before)
            repair["after_identity"] = identity(after)
        _ENGINE.p321._write_exclusive(source_root / name, after)
        receipts[name] = identity(after)
    if repair is None:
        raise AuditError("P3.37 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, repair


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, packager, source = _P337_LOAD_PACKAGER()
    packager.RUN_ID = P338_RUN_ID
    packager._bind_tools()
    for name, value in {
        "artifact": artifact,
        "adapter": adapter,
        "resident_runtime": runtime,
        "framed_runtime": runtime,
        "resident_observer": observer,
        "framed_observer": observer,
        "RUN_ID": P338_RUN_ID,
        "P334_RUN_ID": P338_RUN_ID,
        "P334_RUN_ID_HEX": P338_RUN_ID_HEX,
        "P337_RUN_ID": P338_RUN_ID,
        "P337_RUN_ID_HEX": P338_RUN_ID_HEX,
    }.items():
        if hasattr(packager, name):
            setattr(packager, name, value)
    return helper, packager, source


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    try:
        result = copy.deepcopy(_P337._normalize_result(value))
    except Exception as exc:
        raise AuditError(f"P3.37 inherited result normalization failed: {exc}") from exc
    candidate = result.get("phase2", {}).get("candidate")
    if not isinstance(candidate, dict):
        raise AuditError("P3.38 candidate projection is absent")
    current_ap = candidate.get("a", {}).get("ap_tar_md5")
    if (
        candidate.get("a") != candidate.get("b")
        or current_ap in (
            P337_AP_IDENTITY,
            P334_AP_IDENTITY,
            P333_AP_IDENTITY,
            P332_AP_IDENTITY,
            P331_AP_IDENTITY,
            P330_AP_IDENTITY,
        )
    ):
        raise AuditError("P3.38 candidate repeats a consumed predecessor or differs A/B")
    for label in ("a", "b"):
        package = candidate[label]["package"]
        package.update(
            {
                "schema": "s22plus_fyg8_p338_boot_only_open_read_branch_package_v1",
                "verdict": "PASS_P338_DETERMINISTIC_BOOT_ONLY_OPEN_READ_BRANCH_H0",
            }
        )
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "status": STATUS,
            "run_id_hex": P338_RUN_ID_HEX,
            "differs_from_consumed_p337": True,
        }
    )
    lineage = result.setdefault("lineage", {})
    lineage.update(
        {
            "construction_base_run_id": P337_RUN_ID_HEX,
            "construction_base_result": P337_RESULT_IDENTITY,
            "construction_base_ap": P337_AP_IDENTITY,
            "predecessor_run_id": P337_RUN_ID_HEX,
            "predecessor_result": P337_RESULT_IDENTITY,
            "predecessor_ap": P337_AP_IDENTITY,
            "fresh_run_id": P338_RUN_ID_HEX,
            "p337_source_closure_reopened": True,
        }
    )
    preservation = result.setdefault("preservation", {})
    preservation.update(
        {
            "p337_consumed_candidate_distinct": True,
            "p337_source_closure_reopened": True,
            "runtime_delta_first_open_failure_diagnostic_only": True,
            "first_open_failure_diagnostic": True,
            "later_action_open_before_resync": True,
            "later_action_max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
            "later_action_max_resync_bytes": observer.MAX_RESYNC_BYTES,
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
            "command_count_per_session": len(runtime.DEFAULT_COMMANDS),
            "per_boot_identity_required": True,
            "resident_lease_schema": adapter.LEASE_SCHEMA,
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
        "engine": "P337 exact-loaded",
        "runtime_input": "exact P337 runtime include",
        "wire_namespace": "unchanged P337 authenticated framing and fixed command ABI",
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
                    "command_count_per_session": len(runtime.DEFAULT_COMMANDS),
                    "first_open_failure_diagnostic": True,
                    "later_action_open_before_resync": True,
                    "later_action_max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
                    "later_action_max_resync_bytes": observer.MAX_RESYNC_BYTES,
                    "per_boot_identity_required": True,
                    "resident_lease_schema": adapter.LEASE_SCHEMA,
                    "resident_lease_duration_sec": 3_600,
                    "resident_lease_action_cap": 16,
                    "listener_wait_after_proof": True,
                    "action_retry": False,
                }
            )
    result["limitations"] = [
        "P338 reuses the exact P337 packaging engine and changes only the runtime include.",
        "Initial proof retains the P337 three-session same-FD lease and one host close/reopen.",
        "Successful P337 framing is unchanged; only first-OPEN failures emit one best-effort stage-3 diagnostic.",
        "All sessions use the fixed three-command named catalog with no retry or replay.",
        "Only boot is packaged; exact Magisk rollback remains mandatory.",
        "This host build creates no device, approval, F1, or live authority.",
    ]
    repair = lineage.get("runtime_repair")
    if isinstance(repair, dict):
        repair.update(
            {
                "run_id_hex": P338_RUN_ID_HEX,
                "runtime_contract": runtime.CONTRACT_ID,
                "input_lineage": "p337-runtime-include",
                "initial_session_count": INITIAL_SESSION_COUNT,
                "initial_reconnect_count": INITIAL_RECONNECT_COUNT,
                "fixed_p330_commands": True,
                "command_count_per_session": len(runtime.DEFAULT_COMMANDS),
                "first_open_failure_diagnostic": True,
                "later_action_open_before_resync": True,
                "per_boot_identity_required": True,
                "resident_lease_schema": adapter.LEASE_SCHEMA,
                "resident_lease_duration_sec": 3_600,
                "resident_lease_action_cap": 16,
            }
        )
    return result


# The inherited P3.36 engine resolves these callbacks through its own module
# globals.  Rebinding only the isolated graph keeps P3.36 imports untouched.
for module in (_P337, _P328, _ENGINE):
    if hasattr(module, "_predecessor"):
        module._predecessor = _predecessor
    if hasattr(module, "_current_sources"):
        module._current_sources = _current_sources
    if hasattr(module, "_copy_source_closure"):
        module._copy_source_closure = _copy_source_closure
    if hasattr(module, "_load_packager"):
        module._load_packager = _load_packager
_ENGINE.repair = types.SimpleNamespace(
    RuntimeRepairError=ValueError,
    transform_runtime_include=lambda value: _runtime_transform(value, _active_key())[0],
    validate_repair=lambda before, after: _validate_repair(before, after),
)
_ENGINE._json_bytes = lambda value: _P328._json_bytes(_normalize_result(value))
_P328._normalize_result = _normalize_result


def _validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
    expected, receipt = _runtime_transform(before, _active_key())
    if expected != after:
        raise AuditError("P3.38 transformed runtime differs")
    return receipt


def _require_builder() -> None:
    if _P337 is None or _P328 is None or _ENGINE is None:
        raise AuditError("P3.38 builder dependencies are unavailable")
    adapter.audit()
    observer.audit_binding()


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
