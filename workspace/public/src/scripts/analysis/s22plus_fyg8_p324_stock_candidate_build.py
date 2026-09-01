#!/usr/bin/env python3
"""Build the P3.24 stock candidate, host-only and boot-only.

This is a minimal fresh-identity successor to P3.23.  The reviewed P3.23
builder is loaded from an exact source identity and its real phase-2 engine is
reused.  P3.24 changes only the run-bound Image/IKCONFIG, compiled ``/init``
identity, adapter/source labels, and private output namespace; the ACM-primary
runtime source is required to remain byte-equivalent.  This builder never
contacts a device, runs ADB, or invokes Odin.
"""

from __future__ import annotations

import argparse
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

import s22plus_fyg8_p324_acm_primary_runtime as acm  # noqa: E402
import s22plus_fyg8_p324_stock_process_v2_adapter as adapter  # noqa: E402
import s22plus_fyg8_p324_artifact_identity as artifact  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P323_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p323_stock_candidate_build.py"
P323_BUILDER_IDENTITY = {
    "size": 15_689,
    "sha256": "cb768d0cbc5e1ba74d1c20d32d2200c927d1220d3fe4909c7a25a60a9152fcc2",
}
P323_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p323/"
    "stock-candidate-build-v1-20260831-03"
)
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p324/"
    "stock-candidate-build-v1-20260901-03"
)
P324_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p324_artifact_identity.py"
P324_ACM_SOURCE = REVALIDATION / "s22plus_fyg8_p324_acm_primary_runtime.py"
P324_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p324_stock_process_v2_adapter.py"
P323_CARRIER_SOURCE = REVALIDATION / "s22plus_fyg8_p323_p322_carrier_reanalysis.py"

SCHEMA = "s22plus-fyg8-p324-stock-candidate-build-v1"
VERDICT = "PASS_P324_STOCK_CANDIDATE_BUILD_H0_ACM_PRIMARY_IDENTITY"
STATUS = "IMPLEMENTED_H0_ACM_PRIMARY_IDENTITY_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P324_RUN_ID = artifact.P324_RUN_ID
P324_RUN_ID_HEX = artifact.P324_RUN_ID_HEX


class AuditError(RuntimeError):
    """The P3.23 predecessor or P3.24 source/artifact identity differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise AuditError(f"{label} has duplicate key {key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=pairs)
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

    def inode(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns,
            value.st_ctime_ns,
        )

    actual = identity(payload)
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or inode(before) != inode(inside)
        or inode(before) != inode(after)
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
        or (expected is not None and actual != dict(expected))
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _load_bound_p323() -> types.ModuleType:
    payload = _stable(
        P323_BUILDER_SOURCE,
        "P3.23 builder source",
        2 << 20,
        P323_BUILDER_IDENTITY,
        nlink=1,
    )
    module = types.ModuleType("s22plus_fyg8_p323_builder_bound_for_p324")
    module.__file__ = str(P323_BUILDER_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P323_BUILDER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P3.23 builder failed to load") from exc
    for name in ("build_result", "audit_existing", "_P322", "_ORIGINAL_BUILD_ONCE"):
        if not hasattr(module, name):
            raise AuditError(f"P3.23 builder lacks {name}")
    if getattr(module, "P323_RUN_ID_HEX", None) != artifact.P323_RUN_ID_HEX:
        raise AuditError("P3.23 builder run identity differs")
    return module


_P323 = _load_bound_p323()
try:
    _P323_PREDECESSOR = _P323.audit_existing(P323_OUTPUT)
    _P323_PREDECESSOR_PAYLOAD = _stable(
        P323_OUTPUT / "result.json",
        "P3.23 predecessor result",
        4 << 20,
        mode=0o400,
        nlink=1,
    )
except Exception as exc:
    raise AuditError("P3.23 predecessor audit failed") from exc
if _strict_json(_P323_PREDECESSOR_PAYLOAD, "P3.23 predecessor result") != _P323_PREDECESSOR:
    raise AuditError("P3.23 predecessor result changed after audit")
if (
    _P323_PREDECESSOR.get("run_id_hex") != artifact.P323_RUN_ID_HEX
    or _P323_PREDECESSOR.get("scope", {}).get("device_contact") is not False
    or _P323_PREDECESSOR.get("scope", {}).get("live_authority_created") is not False
):
    raise AuditError("P3.23 predecessor is not the expected host-only result")

_ENGINE = _P323._P322


def _current_sources() -> dict[str, bytes]:
    paths = {
        "p324_stock_candidate_build.py": SELF_SOURCE,
        "p324_artifact_identity.py": P324_ARTIFACT_SOURCE,
        "p324_acm_primary_runtime.py": P324_ACM_SOURCE,
        "p324_stock_process_v2_adapter.py": P324_ADAPTER_SOURCE,
        # This is a stable diagnostic dependency only.  P324 does not
        # reinterpret a new live baseline in its H0 artifact unit.
        "p323_p322_carrier_reanalysis.py": P323_CARRIER_SOURCE,
    }
    return {
        name: _stable(path, f"P324 source {name}", 2 << 20, nlink=1)
        for name, path in paths.items()
    }


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    payload = _stable(
        P323_OUTPUT / "result.json",
        "P3.23 predecessor result",
        4 << 20,
        identity(_P323_PREDECESSOR_PAYLOAD),
        mode=0o400,
        nlink=1,
    )
    value = _strict_json(payload, "P3.23 predecessor result")
    if value != _P323_PREDECESSOR:
        raise AuditError("P3.23 predecessor result changed after audit")
    source = _stable(
        P323_BUILDER_SOURCE,
        "P3.23 predecessor builder source",
        2 << 20,
        P323_BUILDER_IDENTITY,
        nlink=1,
    )
    return value, payload, source


def _copy(path: Path, destination: Path, expected: Mapping[str, Any], label: str) -> dict[str, Any]:
    payload = _stable(path, label, 128 << 20, expected)
    _ENGINE.p321._write_exclusive(destination, payload)
    return identity(payload)


def _copy_bytes(destination: Path, payload: bytes) -> dict[str, Any]:
    _ENGINE.p321._write_exclusive(destination, payload)
    return identity(payload)


class _RuntimeCompat:
    RuntimeRepairError = acm.AcmPrimaryError

    @staticmethod
    def transform_runtime_include(value: bytes) -> bytes:
        return acm.transform_runtime_include(value)

    @staticmethod
    def validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
        return acm.validate_transform(before, after)


def _copy_source_closure(
    output_root: Path, predecessor: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    source_root = output_root / "stock-sources"
    _ENGINE.p321._mkdir(source_root)
    receipts: dict[str, dict[str, Any]] = {}
    runtime_receipt: dict[str, Any] | None = None
    expected_closure = predecessor.get("source_closure")
    if not isinstance(expected_closure, dict) or len(expected_closure) != 12:
        raise AuditError("P3.23 source closure is invalid")
    runtime_name = "s22plus_fyg8_p290_e3_runtime.inc.c"
    for name, expected in sorted(expected_closure.items()):
        before = _stable(
            P323_OUTPUT / "stock-sources" / name,
            f"P3.23 source {name}",
            2 << 20,
            expected,
            mode=0o400,
            nlink=1,
        )
        after = before
        if name == runtime_name:
            try:
                after = acm.transform_runtime_include(before)
                runtime_receipt = acm.validate_transform(before, after) | {
                    "before_identity": identity(before),
                    "after_identity": identity(after),
                }
            except acm.AcmPrimaryError as exc:
                raise AuditError(str(exc)) from exc
        _ENGINE.p321._write_exclusive(source_root / name, after)
        receipts[name] = identity(after)
    if runtime_receipt is None:
        raise AuditError("P3.23 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, runtime_receipt


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, packager, packager_source = _P323._load_packager()
    packager.RUN_ID = P324_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    return helper, packager, packager_source


# Redirect only the P3.23 engine's narrow seams.  The real phase-2 compiler,
# deterministic AP packager, and exact rollback parser remain unchanged.
_ENGINE._current_sources = _current_sources
_ENGINE._predecessor = _predecessor
_ENGINE._copy_source_closure = _copy_source_closure
_ENGINE._load_packager = _load_packager
_ENGINE.artifact = artifact
_ENGINE.adapter = adapter
_ENGINE.repair = _RuntimeCompat
_ENGINE.P321_OUTPUT = P323_OUTPUT
_ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_ENGINE.P322_ARTIFACT_SOURCE = P324_ARTIFACT_SOURCE
_ENGINE.P322_REPAIR_SOURCE = P324_ACM_SOURCE
_ENGINE.P322_ADAPTER_SOURCE = P324_ADAPTER_SOURCE
_ENGINE.P322_RUN_ID = P324_RUN_ID
_ENGINE.P322_RUN_ID_HEX = P324_RUN_ID_HEX
_ENGINE.SCHEMA = SCHEMA
_ENGINE.VERDICT = VERDICT
_ENGINE.STATUS = STATUS
_ENGINE.TARGET = TARGET

_ORIGINAL_BUILD_ONCE = _ENGINE._build_once
_ORIGINAL_AUDIT_EXISTING = _ENGINE.audit_existing


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    result = _strict_json(_json_bytes(value), "P324 result projection")
    if (
        result.get("schema") != SCHEMA
        or result.get("run_id_hex") != P324_RUN_ID_HEX
        or result.get("lineage", {}).get("predecessor_run_id")
        != artifact.P323_PREDECESSOR_RUN_ID_HEX
    ):
        raise AuditError("P324 result projection header differs")
    candidate = result.get("phase2", {}).get("candidate")
    if not isinstance(candidate, dict):
        raise AuditError("P324 result projection lacks candidate")
    candidate["differs_from_consumed_p323"] = (
        candidate.get("a", {}).get("ap_tar_md5")
        != result["lineage"].get("predecessor_ap")
    )
    if candidate["differs_from_consumed_p323"] is not True:
        raise AuditError("P324 candidate repeats consumed P323 AP")
    candidate.pop("differs_from_consumed_p321", None)
    candidate.pop("differs_from_consumed_p322", None)
    preservation = result.get("preservation")
    if not isinstance(preservation, dict):
        raise AuditError("P324 preservation projection is absent")
    preservation["p323_consumed_candidate_unchanged"] = True
    preservation["p323_source_closure_reopened"] = True
    preservation["runtime_byte_equivalent_to_p323"] = True
    for key in (
        "p321_consumed_candidate_unchanged",
        "p321_source_closure_reopened",
        "p322_consumed_candidate_unchanged",
        "p322_source_closure_reopened",
    ):
        preservation.pop(key, None)
    helpers = result.get("helper_sources")
    if not isinstance(helpers, dict):
        raise AuditError("P324 helper source receipts are absent")
    # The inherited engine's audit still expects its historical p321-named
    # slot.  Preserve it as compatibility metadata and add the truthful
    # immediate-predecessor alias; no input bytes are renamed in place.
    helpers["p323_stock_candidate_build.py"] = helpers.get(
        "p321_stock_candidate_build.py",
        identity(_stable(P323_BUILDER_SOURCE, "P323 builder", 2 << 20, P323_BUILDER_IDENTITY)),
    )
    result["limitations"] = [
        "P324 changes only the run-bound Image/IKCONFIG, compiled /init identity, and adapter/source labels.",
        "The P3.23 ACM-primary runtime is retained byte-for-byte; its exact 49-byte banner remains the primary native PID-1/USB arrival witness and Carrier remains supplemental.",
        "No kernel Full-LTO, device contact, approval, D0, D1, F1, recovery, replay, or live authority is created.",
    ]
    result["compatibility_labels"] = {
        "inherited_input_names": ["p321-result.json", "p321-stock-candidate-build.py"],
        "actual_predecessor": "P323",
        "presentation_only": True,
        "baseline_reanalysis": "not required for artifact-only H0; required before any P324 live-result comparison",
    }
    return result


def _p324_json_bytes(value: dict[str, Any]) -> bytes:
    return _json_bytes(_normalize_result(value))


_ENGINE._json_bytes = _p324_json_bytes


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    audit_only: bool = False,
) -> dict[str, Any]:
    output_root = output_root.absolute()
    if audit_only:
        return audit_existing(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("P324 output already exists")
    output_root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.parent.chmod(0o700)
    _ORIGINAL_BUILD_ONCE(output_root)
    return _strict_json(
        _stable(
            output_root / "result.json",
            "P324 result after build",
            4 << 20,
            mode=0o400,
            nlink=1,
        ),
        "P324 result after build",
    )


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.absolute()
    result = _ORIGINAL_AUDIT_EXISTING(output_root)
    normalized = _normalize_result(result)
    if result != normalized:
        raise AuditError("P324 normalized result projection differs")
    candidate = result.get("phase2", {}).get("candidate", {})
    preservation = result.get("preservation", {})
    if (
        candidate.get("differs_from_consumed_p323") is not True
        or preservation.get("p323_consumed_candidate_unchanged") is not True
        or preservation.get("p323_source_closure_reopened") is not True
        or "P323" not in result.get("compatibility_labels", {}).get("actual_predecessor", "")
    ):
        raise AuditError("P324 normalized lineage differs")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        result = build_result(output, audit_only=args.audit_only)
    except (AuditError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"], "output": str(output)}, sort_keys=True))
    return 0


__all__ = [
    "AuditError",
    "DEFAULT_OUTPUT_ROOT",
    "P323_BUILDER_IDENTITY",
    "P323_BUILDER_SOURCE",
    "P323_OUTPUT",
    "P324_RUN_ID",
    "P324_RUN_ID_HEX",
    "SCHEMA",
    "STATUS",
    "TARGET",
    "VERDICT",
    "adapter",
    "artifact",
    "audit_existing",
    "build_result",
    "identity",
]


if __name__ == "__main__":
    raise SystemExit(main())
