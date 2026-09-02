#!/usr/bin/env python3
"""Build the fresh P3.29 boot-only candidate from the reviewed P3.28 engine.

The P3.28 authenticated runtime, private key, BusyBox, and boot packaging stay
unchanged.  This wrapper rotates the run identity and records that the new AP
differs from the consumed P3.28 AP.  It is host-only.
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
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p329_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p329_auth_acm_observer as framed_observer  # noqa: E402
import s22plus_fyg8_p329_auth_exec_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p329_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P328_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p328_stock_candidate_build.py"
P328_BUILDER_IDENTITY = {
    "size": 33_410,
    "sha256": "2d55eb45eca5d5094a6369e9fc82e337a66dba20d1ad5d1f2e3cce8bd5ebbfff",
}
P328_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "4ff89343a35a3bd0081ac8ed09ef0a872921b2ace5e9be266ce0c4d5a2bffbdb",
}
P328_RUN_ID_HEX = artifact.P328_PREDECESSOR_RUN_ID_HEX
P329_RUN_ID_HEX = artifact.P329_RUN_ID_HEX
P329_RUN_ID = artifact.P329_RUN_ID
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p329/"
    "stock-candidate-build-v1-20260903-01"
)
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
SCHEMA = "s22plus-fyg8-p329-stock-candidate-build-v1"
VERDICT = "PASS_P329_STOCK_CANDIDATE_BUILD_H0_UDEV_SETTLE"
STATUS = "IMPLEMENTED_H0_UDEV_SETTLE_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class AuditError(RuntimeError):
    """The exact P3.28 engine or P3.29 candidate closure differs."""


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


def _load_engine() -> types.ModuleType:
    direct = P328_BUILDER_SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(P328_BUILDER_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError("P3.28 builder source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != P328_BUILDER_IDENTITY
    ):
        raise AuditError("P3.28 builder source identity differs")
    module = types.ModuleType("s22plus_fyg8_p328_builder_bound_for_p329")
    module.__file__ = str(P328_BUILDER_SOURCE)
    module.__package__ = ""
    previous = sys.modules.get(module.__name__)
    sys.modules[module.__name__] = module
    try:
        exec(compile(payload, str(P328_BUILDER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P3.28 builder source failed to load") from exc
    finally:
        if previous is None:
            sys.modules.pop(module.__name__, None)
        else:
            sys.modules[module.__name__] = previous
    return module


def _patch_identity(module: types.ModuleType) -> None:
    for name, value in tuple(vars(module).items()):
        if value == artifact.P328_PREDECESSOR_RUN_ID:
            setattr(module, name, P329_RUN_ID)
        elif value == artifact.P328_PREDECESSOR_RUN_ID_HEX:
            setattr(module, name, P329_RUN_ID_HEX)
        elif callable(value) and getattr(value, "__kwdefaults__", None):
            defaults = dict(value.__kwdefaults__)
            for key, current in tuple(defaults.items()):
                if current == artifact.P328_PREDECESSOR_RUN_ID:
                    defaults[key] = P329_RUN_ID
                elif current == artifact.P328_PREDECESSOR_RUN_ID_HEX:
                    defaults[key] = P329_RUN_ID_HEX
            value.__kwdefaults__ = defaults


_P328 = _load_engine()
_P328_NORMALIZE = _P328._normalize_result
_P328.artifact = artifact
_P328.adapter = adapter
_P328.framed_runtime = framed_runtime
_P328.framed_observer = framed_observer
_P328.P328_RUN_ID = P329_RUN_ID
_P328.P328_RUN_ID_HEX = P329_RUN_ID_HEX
_P328.SCHEMA = SCHEMA
_P328.VERDICT = VERDICT
_P328.STATUS = STATUS
_P328.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_P328.DEFAULT_AUTH_KEY_PATH = DEFAULT_AUTH_KEY_PATH
_P328.SELF_SOURCE = SELF_SOURCE
_P328.P328_ARTIFACT_SOURCE = Path(artifact.__file__).resolve()
_P328.P328_ADAPTER_SOURCE = Path(adapter.__file__).resolve()
_P328.P328_RUNTIME_SOURCE = Path(framed_runtime.__file__).resolve()
_P328.P328_OBSERVER_SOURCE = Path(framed_observer.__file__).resolve()
for _module in (_P328, _P328._ENGINE, _P328._P327):
    _patch_identity(_module)
_P328._ENGINE.artifact = artifact
_P328._ENGINE.adapter = adapter
_P328._ENGINE.P322_RUN_ID = P329_RUN_ID
_P328._ENGINE.P322_RUN_ID_HEX = P329_RUN_ID_HEX
_P328._ENGINE.SCHEMA = SCHEMA
_P328._ENGINE.VERDICT = VERDICT
_P328._ENGINE.STATUS = STATUS
_P328._ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_P328._ENGINE.P322_ARTIFACT_SOURCE = _P328.P328_ARTIFACT_SOURCE
_P328._ENGINE.P322_REPAIR_SOURCE = _P328.P328_RUNTIME_SOURCE
_P328._ENGINE.P322_ADAPTER_SOURCE = _P328.P328_ADAPTER_SOURCE
_P328._P328ConsoleCompat.CONTRACT_ID = framed_runtime.CONTRACT_ID
_P328._patch_delegate_modules()


def _current_sources() -> dict[str, bytes]:
    paths = {
        # Compatibility keys keep the proven P3.28 engine's generic copier;
        # each value is the exact P3.29 wrapper source named below.
        "p328_stock_candidate_build.py": SELF_SOURCE,
        "p328_artifact_identity.py": _P328.P328_ARTIFACT_SOURCE,
        "p328_stock_process_v2_adapter.py": _P328.P328_ADAPTER_SOURCE,
        "p328_authenticated_exec_runtime.py": _P328.P328_RUNTIME_SOURCE,
        "p328_authenticated_acm_observer.py": _P328.P328_OBSERVER_SOURCE,
    }
    return {
        name: _P328._stable(path, f"P329 source {name}", 2 << 20, nlink=1)
        for name, path in paths.items()
    }


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    normalization_input = copy.deepcopy(value)
    lineage_input = normalization_input.get("lineage")
    if isinstance(lineage_input, dict):
        if lineage_input.get("predecessor_run_id") == P328_RUN_ID_HEX:
            lineage_input["predecessor_run_id"] = artifact.P327_PREDECESSOR_RUN_ID_HEX
        lineage_input.pop("construction_base_run_id", None)
    candidate_input = normalization_input.get("phase2", {}).get("candidate")
    if isinstance(candidate_input, dict):
        candidate_input.pop("differs_from_consumed_p328", None)
    try:
        result = _P328_NORMALIZE(normalization_input)
    except Exception as exc:
        raise AuditError(f"P329 inherited result normalization failed: {exc}") from exc
    candidate = result.get("phase2", {}).get("candidate")
    if not isinstance(candidate, dict):
        raise AuditError("P329 candidate projection is absent")
    ap = candidate.get("a", {}).get("ap_tar_md5")
    if not isinstance(ap, dict) or ap == P328_AP_IDENTITY:
        raise AuditError("P329 repeats the consumed P328 AP")
    candidate["differs_from_consumed_p328"] = True
    for label in ("a", "b"):
        package = candidate.get(label, {}).get("package")
        if not isinstance(package, dict):
            raise AuditError("P329 package projection is absent")
        package["schema"] = "s22plus_fyg8_p329_boot_only_package_v1"
        package["verdict"] = "PASS_P329_DETERMINISTIC_BOOT_ONLY_UDEV_SETTLE_PACKAGE_H0"
    result["schema"] = SCHEMA
    result["verdict"] = VERDICT
    result["status"] = STATUS
    result["run_id_hex"] = P329_RUN_ID_HEX
    lineage = result.setdefault("lineage", {})
    lineage["construction_base_run_id"] = lineage.get("predecessor_run_id")
    lineage["predecessor_run_id"] = P328_RUN_ID_HEX
    lineage["fresh_run_id"] = P329_RUN_ID_HEX
    preservation = result.setdefault("preservation", {})
    preservation.update(
        {
            "p328_consumed_candidate_distinct": True,
            "p328_authenticated_protocol_reused": True,
            "p328_auth_key_reused": True,
            "candidate_delta_identity_only": True,
            "observer_udev_settle_host_only": True,
        }
    )
    result["compatibility_labels"] = {
        "engine": "P328 exact-loaded",
        "source_keys": "p328-prefixed compatibility keys contain P329 wrapper bytes",
        "wire_namespace": "S328/P328-NONCE retained",
        "presentation_only": True,
    }
    result["limitations"] = [
        "P329 reuses the P328 authenticated bounded command protocol and private key.",
        "Only the fresh run identity changes candidate bytes; udev settle is host-only.",
        "The symmetric key is not hardware-backed and candidate possession exposes it.",
        "Only boot is transferred and exact Magisk rollback remains mandatory.",
        "No device contact, live authority, resident service, PTY, or USB causality is claimed by H0.",
    ]
    return result


_P328._current_sources = _current_sources
_P328._ENGINE._current_sources = _current_sources
_P328._normalize_result = _normalize_result
_P328._ENGINE._json_bytes = lambda value: _P328._json_bytes(_normalize_result(value))


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    auth_key: Path | str | None = None,
    audit_only: bool = False,
) -> dict[str, Any]:
    try:
        return _P328.build_result(
            output_root,
            auth_key=DEFAULT_AUTH_KEY_PATH if auth_key is None else auth_key,
            audit_only=audit_only,
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


if __name__ == "__main__":
    raise SystemExit(main())
