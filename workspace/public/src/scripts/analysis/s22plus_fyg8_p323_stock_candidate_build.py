#!/usr/bin/env python3
"""Build the P3.23 stock candidate, host-only and boot-only.

P3.23 reopens the exact P3.22 host result and changes two deliberately small
things: a fresh same-length Image identity and the P323 ACM-primary publisher
transform.  The existing P3.22 retained Carrier path remains in the runtime
as supplemental evidence.  This builder never contacts a device, runs ADB,
or invokes Odin.
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

import s22plus_fyg8_p323_acm_primary_runtime as acm  # noqa: E402
import s22plus_fyg8_p323_stock_process_v2_adapter as adapter  # noqa: E402
import s22plus_fyg8_p323_artifact_identity as artifact  # noqa: E402


P322_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p322_stock_candidate_build.py"
P322_BUILDER_IDENTITY = {
    "size": 21_976,
    "sha256": "ef6e5b5d4a75e0251348a8ce5d21f09189c92c11e1a07883d567b8ffca722ae1",
}
P322_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p322/"
    "stock-candidate-build-v1-20260831-02"
)
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p323/"
    "stock-candidate-build-v1-20260831-03"
)
P323_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p323_artifact_identity.py"
P323_ACM_SOURCE = REVALIDATION / "s22plus_fyg8_p323_acm_primary_runtime.py"
P323_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p323_stock_process_v2_adapter.py"
P323_CARRIER_SOURCE = REVALIDATION / "s22plus_fyg8_p323_p322_carrier_reanalysis.py"

SCHEMA = "s22plus-fyg8-p323-stock-candidate-build-v1"
VERDICT = "PASS_P323_STOCK_CANDIDATE_BUILD_H0_ACM_PRIMARY"
STATUS = "IMPLEMENTED_H0_ACM_PRIMARY_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P323_RUN_ID = artifact.P323_RUN_ID
P323_RUN_ID_HEX = artifact.P323_RUN_ID_HEX


class AuditError(RuntimeError):
    """The P3.22 predecessor or P3.23 source/artifact identity differs."""


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


def _load_bound_p322() -> types.ModuleType:
    """Load the predecessor builder by exact bytes and no implicit import."""
    direct = P322_BUILDER_SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(P322_BUILDER_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError("P322 builder source is unavailable") from exc
    def inode(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns,
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
        or identity(payload) != P322_BUILDER_IDENTITY
    ):
        raise AuditError("P322 builder source identity differs")
    module = types.ModuleType("s22plus_fyg8_p322_builder_bound_for_p323")
    module.__file__ = str(P322_BUILDER_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P322_BUILDER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P322 builder failed to load") from exc
    return module


_P322 = _load_bound_p322()
try:
    _P322_PREDECESSOR = _P322.audit_existing(P322_OUTPUT)
except Exception as exc:
    raise AuditError("P322 predecessor audit failed") from exc


def _stable(path: Path, label: str, maximum: int, expected: Mapping[str, Any] | None = None, *, mode: int | None = None, nlink: int | None = None) -> bytes:
    try:
        return _P322._stable(path, label, maximum, expected, mode=mode, nlink=nlink)
    except Exception as exc:
        raise AuditError(str(exc)) from exc


def _current_sources() -> dict[str, bytes]:
    paths = {
        "p323_stock_candidate_build.py": SELF_SOURCE,
        "p323_artifact_identity.py": P323_ARTIFACT_SOURCE,
        "p323_acm_primary_runtime.py": P323_ACM_SOURCE,
        "p323_stock_process_v2_adapter.py": P323_ADAPTER_SOURCE,
        "p323_p322_carrier_reanalysis.py": P323_CARRIER_SOURCE,
    }
    return {
        name: _stable(path, f"P323 source {name}", 2 << 20)
        for name, path in paths.items()
    }


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    payload = _stable(
        P322_OUTPUT / "result.json",
        "P322 predecessor result",
        4 << 20,
        mode=0o400,
        nlink=1,
    )
    value = _strict_json(payload, "P322 predecessor result")
    if value != _P322_PREDECESSOR:
        raise AuditError("P322 predecessor result changed after audit")
    if (
        value.get("run_id_hex") != artifact.P322_RUN_ID_HEX
        or value.get("scope", {}).get("device_contact") is not False
        or value.get("scope", {}).get("live_authority_created") is not False
    ):
        raise AuditError("P322 predecessor is not the expected host-only result")
    p322_source = _stable(
        P322_BUILDER_SOURCE,
        "P322 predecessor builder source",
        2 << 20,
        P322_BUILDER_IDENTITY,
    )
    return value, payload, p322_source


def _copy(path: Path, destination: Path, expected: Mapping[str, Any], label: str) -> dict[str, Any]:
    payload = _stable(path, label, 128 << 20, expected)
    _P322.p321._write_exclusive(destination, payload)
    return identity(payload)


def _copy_bytes(destination: Path, payload: bytes) -> dict[str, Any]:
    _P322.p321._write_exclusive(destination, payload)
    return identity(payload)


class _RepairCompat:
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
    _P322.p321._mkdir(source_root)
    receipts: dict[str, dict[str, Any]] = {}
    transform_receipt: dict[str, Any] | None = None
    expected_closure = predecessor.get("source_closure")
    if not isinstance(expected_closure, dict) or len(expected_closure) != 12:
        raise AuditError("P322 source closure is invalid")
    runtime_name = "s22plus_fyg8_p290_e3_runtime.inc.c"
    for name, expected in sorted(expected_closure.items()):
        before = _stable(
            P322_OUTPUT / "stock-sources" / name,
            f"P322 source {name}",
            2 << 20,
            expected,
            mode=0o400,
            nlink=1,
        )
        after = before
        if name == runtime_name:
            try:
                after = acm.transform_runtime_include(before)
                transform_receipt = acm.validate_transform(before, after) | {
                    "before_identity": identity(before),
                    "after_identity": identity(after),
                }
            except acm.AcmPrimaryError as exc:
                raise AuditError(str(exc)) from exc
        _P322.p321._write_exclusive(source_root / name, after)
        receipts[name] = identity(after)
    if transform_receipt is None:
        raise AuditError("P322 runtime source is absent")
    _P322.p321._fsync_directory(source_root)
    return receipts, transform_receipt


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, _p320_source = _P322.p321._load_p320()
    packager, packager_source = helper._load_bound_module(
        helper.P319_STOCK_BUILDER,
        helper.P319_STOCK_BUILDER_IDENTITY,
        "p319_stock_builder_bound_for_p323",
    )
    packager.RUN_ID = P323_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    return helper, packager, packager_source


# Redirect only the P322 builder's narrow seams.  Its phase-2 machinery and
# real AP packaging remain untouched, while all current identity values are
# explicitly rebound to P323.
_P322._current_sources = _current_sources
_P322._predecessor = _predecessor
_P322._copy_source_closure = _copy_source_closure
_P322._load_packager = _load_packager
_P322.artifact = artifact
_P322.adapter = adapter
_P322.repair = _RepairCompat
_P322.P321_OUTPUT = P322_OUTPUT
_P322.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_P322.P322_ARTIFACT_SOURCE = P323_ARTIFACT_SOURCE
_P322.P322_REPAIR_SOURCE = P323_ACM_SOURCE
_P322.P322_ADAPTER_SOURCE = P323_ADAPTER_SOURCE
_P322.P322_RUN_ID = P323_RUN_ID
_P322.P322_RUN_ID_HEX = P323_RUN_ID_HEX
_P322.SCHEMA = SCHEMA
_P322.VERDICT = VERDICT
_P322.STATUS = STATUS
_P322.TARGET = TARGET

_ORIGINAL_BUILD_ONCE = _P322._build_once
_ORIGINAL_AUDIT_EXISTING = _P322.audit_existing


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    """Replace inherited P322 presentation labels with truthful P323 lineage."""
    result = _strict_json(_json_bytes(value), "P323 result projection")
    if (
        result.get("schema") != SCHEMA
        or result.get("run_id_hex") != P323_RUN_ID_HEX
        or result.get("lineage", {}).get("predecessor_run_id")
        != artifact.P322_PREDECESSOR_RUN_ID_HEX
    ):
        raise AuditError("P323 result projection header differs")
    candidate = result.get("phase2", {}).get("candidate")
    if not isinstance(candidate, dict):
        raise AuditError("P323 result projection lacks candidate")
    candidate["differs_from_consumed_p322"] = (
        candidate.get("a", {}).get("ap_tar_md5")
        != result["lineage"].get("predecessor_ap")
    )
    if candidate["differs_from_consumed_p322"] is not True:
        raise AuditError("P323 candidate repeats consumed P322 AP")
    preservation = result.get("preservation")
    if not isinstance(preservation, dict):
        raise AuditError("P323 preservation projection is absent")
    preservation["p322_consumed_candidate_unchanged"] = True
    preservation["p322_source_closure_reopened"] = True
    preservation.pop("p321_consumed_candidate_unchanged", None)
    preservation.pop("p321_source_closure_reopened", None)
    helpers = result.get("helper_sources")
    if not isinstance(helpers, dict) or "p321_stock_candidate_build.py" not in helpers:
        raise AuditError("P323 inherited builder receipt is absent")
    helpers["p322_stock_candidate_build.py"] = helpers[
        "p321_stock_candidate_build.py"
    ]
    result["limitations"] = [
        "P323 changes only the Image run identity and one userspace ACM publisher entry.",
        "The exact 49-byte ACM banner proves native PID-1/USB arrival only; Carrier remains supplemental experiment evidence.",
        "No kernel Full-LTO, device contact, approval, D0, D1, F1, recovery, replay, or live authority is created.",
    ]
    result["compatibility_labels"] = {
        "inherited_input_names": [
            "p321-result.json",
            "p321-stock-candidate-build.py",
        ],
        "actual_predecessor": "P322",
        "presentation_only": True,
    }
    return result


def _p323_json_bytes(value: dict[str, Any]) -> bytes:
    return _json_bytes(_normalize_result(value))


# The exact-loaded builder owns publication.  Normalize its final object before
# that one no-clobber result write rather than rewriting a published receipt.
_P322._json_bytes = _p323_json_bytes


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    audit_only: bool = False,
) -> dict[str, Any]:
    output_root = output_root.absolute()
    if audit_only:
        return audit_existing(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("P323 output already exists")
    output_root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.parent.chmod(0o700)
    _ORIGINAL_BUILD_ONCE(output_root)
    return _strict_json(
        _stable(
            output_root / "result.json",
            "P323 result after build",
            4 << 20,
            mode=0o400,
            nlink=1,
        ),
        "P323 result after build",
    )


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.absolute()
    result = _ORIGINAL_AUDIT_EXISTING(output_root)
    if result != _normalize_result(result):
        raise AuditError("P323 normalized result projection differs")
    candidate = result.get("phase2", {}).get("candidate", {})
    preservation = result.get("preservation", {})
    if (
        candidate.get("differs_from_consumed_p322") is not True
        or preservation.get("p322_consumed_candidate_unchanged") is not True
        or preservation.get("p322_source_closure_reopened") is not True
        or "P322" not in result.get("compatibility_labels", {}).get(
            "actual_predecessor", ""
        )
    ):
        raise AuditError("P323 normalized lineage differs")
    return result


SELF_SOURCE = Path(__file__).resolve()


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
    "P322_BUILDER_IDENTITY",
    "P322_BUILDER_SOURCE",
    "P322_OUTPUT",
    "P323_RUN_ID",
    "P323_RUN_ID_HEX",
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
