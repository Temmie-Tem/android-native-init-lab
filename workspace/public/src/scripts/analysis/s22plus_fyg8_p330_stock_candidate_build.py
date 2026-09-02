#!/usr/bin/env python3
"""Build the fresh P3.30 boot-only diagnostic candidate.

P3.30 is a thin host-only successor of the consumed P3.29 build.  The
reviewed P3.29 packaging engine is exact-loaded; only the fresh P3.30
artifact, adapter, runtime, and observer source bytes are supplied to it.
The resulting AP contains boot.img.lz4 only and keeps the exact stock
rollback.  No device or transfer tool is contacted by this module.
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

import s22plus_fyg8_p330_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p330_auth_acm_observer as framed_observer  # noqa: E402
import s22plus_fyg8_p330_auth_exec_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p330_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P329_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p329_stock_candidate_build.py"
P329_BUILDER_IDENTITY = {
    "size": 12_112,
    "sha256": "67d27540675dd594ae22f0c4d6a7e1cb508926f6d43b662abc0b2850a6b25691",
}
P329_RESULT_IDENTITY = {
    "size": 45_150,
    "sha256": "d8475c76d7fe31fa52fc78ed6f770eae73bd24520bf3ff4ab8b696a981503973",
}
P329_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "7a83b7c32e52f13fb88ec3cc6d81671baf70f13c343f2e02b03a6d712ab494bf",
}
P329_RUN_ID_HEX = "c329f1e0a90b5e6d7c8a9b0c1d2e3f1b"
P330_RUN_ID_HEX = artifact.P330_RUN_ID_HEX
P330_RUN_ID = artifact.P330_RUN_ID
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p330/"
    "stock-candidate-build-v1-20260903-07"
)
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
SCHEMA = "s22plus-fyg8-p330-stock-candidate-build-v1"
VERDICT = "PASS_P330_STOCK_CANDIDATE_BUILD_H0_DIAGNOSTIC"
STATUS = "IMPLEMENTED_H0_DIAGNOSTIC_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class AuditError(RuntimeError):
    """The exact P3.29 build engine or fresh P3.30 closure differs."""


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


def _load_p329_builder() -> types.ModuleType:
    payload = _stable(
        P329_BUILDER_SOURCE,
        "P3.29 builder",
        2 << 20,
        P329_BUILDER_IDENTITY,
        nlink=1,
    )
    module = types.ModuleType("s22plus_fyg8_p329_builder_bound_for_p330")
    module.__file__ = str(P329_BUILDER_SOURCE)
    module.__package__ = ""
    previous = sys.modules.get(module.__name__)
    sys.modules[module.__name__] = module
    try:
        exec(  # noqa: S102 - exact, hash-pinned predecessor source loading
            compile(payload, str(P329_BUILDER_SOURCE), "exec", dont_inherit=True),
            module.__dict__,
        )
    except Exception as exc:
        raise AuditError("P3.29 builder failed to load") from exc
    finally:
        if previous is None:
            sys.modules.pop(module.__name__, None)
        else:
            sys.modules[module.__name__] = previous
    if getattr(module, "P329_RUN_ID_HEX", None) != P329_RUN_ID_HEX:
        raise AuditError("P3.29 builder identity differs")
    return module


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


_P329 = _load_p329_builder()
_P328 = _P329._P328
_ENGINE = _P328._ENGINE
_P329_NORMALIZE = _P329._normalize_result


def _patch_identities() -> None:
    """Rotate inherited module globals without changing their source bytes."""

    for module in _modules(_P329):
        for name, value in tuple(vars(module).items()):
            if value == bytes.fromhex(P329_RUN_ID_HEX):
                setattr(module, name, P330_RUN_ID)
            elif value == P329_RUN_ID_HEX:
                setattr(module, name, P330_RUN_ID_HEX)
            elif callable(value) and isinstance(
                getattr(value, "__kwdefaults__", None), dict
            ):
                defaults = dict(value.__kwdefaults__)
                changed = False
                for key, current in tuple(defaults.items()):
                    if current == bytes.fromhex(P329_RUN_ID_HEX):
                        defaults[key] = P330_RUN_ID
                        changed = True
                    elif current == P329_RUN_ID_HEX:
                        defaults[key] = P330_RUN_ID_HEX
                        changed = True
                if changed:
                    value.__kwdefaults__ = defaults


_patch_identities()

# The P3.29 module and its exact-loaded P3.28 engine are now bound to P3.30
# source bytes.  Compatibility attribute names are retained only inside the
# private inherited engine; all emitted identities below are P3.30.
_P329.artifact = artifact
_P329.adapter = adapter
_P329.framed_runtime = framed_runtime
_P329.framed_observer = framed_observer
_P329.P329_RUN_ID = P330_RUN_ID
_P329.P329_RUN_ID_HEX = P330_RUN_ID_HEX
_P329.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT

_P328.artifact = artifact
_P328.adapter = adapter
_P328.framed_runtime = framed_runtime
_P328.framed_observer = framed_observer
_P328.P328_RUN_ID = P330_RUN_ID
_P328.P328_RUN_ID_HEX = P330_RUN_ID_HEX
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
_P328.P328_RUNTIME_IDENTITY = dict(framed_runtime.SOURCE_IDENTITY)

for module in _modules(_P328):
    if hasattr(module, "artifact"):
        module.artifact = artifact
    if hasattr(module, "adapter"):
        module.adapter = adapter
    if hasattr(module, "framed_runtime"):
        module.framed_runtime = framed_runtime
    if hasattr(module, "framed_observer"):
        module.framed_observer = framed_observer

_ENGINE.artifact = artifact
_ENGINE.adapter = adapter
_ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_ENGINE.P322_RUN_ID = P330_RUN_ID
_ENGINE.P322_RUN_ID_HEX = P330_RUN_ID_HEX
_ENGINE.P322_ARTIFACT_SOURCE = _P328.P328_ARTIFACT_SOURCE
_ENGINE.P322_REPAIR_SOURCE = _P328.P328_RUNTIME_SOURCE
_ENGINE.P322_ADAPTER_SOURCE = _P328.P328_ADAPTER_SOURCE
_ENGINE.SCHEMA = SCHEMA
_ENGINE.VERDICT = VERDICT
_ENGINE.STATUS = STATUS
_ENGINE.TARGET = TARGET
_P328._P328ConsoleCompat.CONTRACT_ID = framed_runtime.CONTRACT_ID
# P3.29 performs this second, recursive rebind after replacing the P3.28
# facade.  Keep the same seam: the inherited P3.24--P3.27 normalizers retain
# their own header/run globals and otherwise see a mixed P3.30/P3.29 view.
_P328._patch_delegate_modules()


def _current_sources() -> dict[str, bytes]:
    paths = {
        # Compatibility keys are required by the inherited packager, but each
        # value is an exact P3.30 wrapper/source byte stream.
        "p328_stock_candidate_build.py": SELF_SOURCE,
        "p328_artifact_identity.py": _P328.P328_ARTIFACT_SOURCE,
        "p328_stock_process_v2_adapter.py": _P328.P328_ADAPTER_SOURCE,
        "p328_authenticated_exec_runtime.py": _P328.P328_RUNTIME_SOURCE,
        "p328_authenticated_acm_observer.py": _P328.P328_OBSERVER_SOURCE,
    }
    return {
        name: _P328._stable(path, f"P330 source {name}", 2 << 20, nlink=1)
        for name, path in paths.items()
    }


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuditError("P330 result is not an object")
    normalization_input = copy.deepcopy(value)
    lineage = normalization_input.get("lineage")
    if isinstance(lineage, dict):
        if lineage.get("predecessor_run_id") == P329_RUN_ID_HEX:
            # A stored P3.30 result names P3.29 directly.  The exact P3.29
            # normalizer expects its own P3.28 predecessor at entry and then
            # restores P3.29 below, so project only this compatibility value.
            lineage["predecessor_run_id"] = _P329.P328_RUN_ID_HEX
        lineage.pop("construction_base_run_id", None)
    candidate_input = normalization_input.get("phase2", {}).get("candidate")
    if isinstance(candidate_input, dict):
        candidate_input.pop("differs_from_consumed_p329", None)
    try:
        result = _P329_NORMALIZE(normalization_input)
    except Exception as exc:
        raise AuditError(f"P330 inherited result normalization failed: {exc}") from exc
    candidate = result.get("phase2", {}).get("candidate")
    if not isinstance(candidate, dict):
        raise AuditError("P330 candidate projection is absent")
    ap = candidate.get("a", {}).get("ap_tar_md5")
    if not isinstance(ap, dict) or ap == P329_AP_IDENTITY:
        raise AuditError("P330 repeats the consumed P329 AP")
    candidate["differs_from_consumed_p329"] = True
    # Keep the inherited predecessor distinctions as provenance, but make the
    # current candidate's direct consumed-predecessor relation explicit.
    candidate["differs_from_consumed_p328"] = True
    for label in ("a", "b"):
        package = candidate.get(label, {}).get("package")
        if not isinstance(package, dict):
            raise AuditError("P330 package projection is absent")
        package["schema"] = "s22plus_fyg8_p330_boot_only_package_v1"
        package["verdict"] = "PASS_P330_DETERMINISTIC_BOOT_ONLY_DIAGNOSTIC_PACKAGE_H0"
    result["schema"] = SCHEMA
    result["verdict"] = VERDICT
    result["status"] = STATUS
    result["run_id_hex"] = P330_RUN_ID_HEX
    lineage = result.setdefault("lineage", {})
    lineage["construction_base_run_id"] = lineage.get("predecessor_run_id")
    lineage["predecessor_run_id"] = P329_RUN_ID_HEX
    lineage["fresh_run_id"] = P330_RUN_ID_HEX
    preservation = result.setdefault("preservation", {})
    preservation.update(
        {
            "p329_consumed_candidate_distinct": True,
            "p329_source_closure_reopened": True,
            "p329_authenticated_protocol_reused": True,
            "p329_auth_key_reused": True,
            "candidate_delta_diagnostic_and_identity_only": True,
            "observer_diagnostics_host_only": True,
            "diagnostic_provider_widening": False,
        }
    )
    result["compatibility_labels"] = {
        "engine": "P329 exact-loaded",
        "source_keys": "p328-prefixed compatibility keys contain P330 wrapper bytes",
        "wire_namespace": "S328/P328-NONCE retained",
        "presentation_only": True,
    }
    result["limitations"] = [
        "P330 reuses the P329 authenticated bounded command protocol and private key.",
        "Only bounded OPEN/RNG diagnostics and EAGAIN-only device retry are added.",
        "Diagnostics are non-authoritative and cannot establish authenticated execution.",
        "Only boot is transferred and exact Magisk rollback remains mandatory.",
        "No device contact, live authority, resident service, PTY, or USB causality is claimed by H0.",
    ]
    framed = result.get("framed_exec")
    if isinstance(framed, dict):
        framed["runtime_contract"] = framed_runtime.CONTRACT_ID
        framed["observer_contract"] = framed_observer.CONTRACT_ID
        framed["preauth_diagnostic_frame"] = framed_runtime.DIAGNOSTIC_FRAME_TYPE
        framed["rng_eagain_retry_limit"] = framed_runtime.RNG_EAGAIN_RETRY_LIMIT
        framed["diagnostics_non_authoritative"] = True
        framed["eagain_only_retry"] = True
    repair = result.get("lineage", {}).get("runtime_repair")
    if isinstance(repair, dict):
        repair.pop("auth_key_path", None)
        repair.pop("key_path", None)
        repair["run_id_hex"] = P330_RUN_ID_HEX
        repair["runtime_contract"] = framed_runtime.CONTRACT_ID
    return result


_P328._current_sources = _current_sources
_ENGINE._current_sources = _current_sources
_P328._normalize_result = _normalize_result
_ENGINE._json_bytes = lambda value: _P328._json_bytes(_normalize_result(value))


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
