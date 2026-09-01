#!/usr/bin/env python3
"""Build the P3.25 stock candidate, host-only and boot-only.

The exact P3.24 phase-2 builder and its deterministic packager are loaded by
stable bytes.  P3.25 rotates the run-bound Image/IKCONFIG, ``/init`` identity,
and Carrier/observer adapter labels, while retaining the P3.24 runtime and
source geometry.  The exact P3.24 candidate is the immediate predecessor;
the stock rollback remains unchanged and is validated before publication.
No device, ADB, USB, or Odin action is reachable here.
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
import s22plus_fyg8_p325_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p325_cdc_acm_guard_adapter as guard_adapter  # noqa: E402
import s22plus_fyg8_p325_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P324_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p324_stock_candidate_build.py"
P324_BUILDER_IDENTITY = {
    "size": 17_120,
    "sha256": "43bb5a63d46888d943b20b6f7253543b53b685d132ba8a85d0cd0fbccaeef96b",
}
P324_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p324/"
    "stock-candidate-build-v1-20260901-03"
)
P324_RESULT_IDENTITY = {
    "size": 39_893,
    "sha256": "16769c766acd329623781376893da40d465cb4e06c4614174f1ecbca820be779",
}
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p325/"
    "stock-candidate-build-v1-20260901-02"
)
P325_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p325_artifact_identity.py"
P324_ACM_SOURCE = REVALIDATION / "s22plus_fyg8_p324_acm_primary_runtime.py"
P325_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p325_stock_process_v2_adapter.py"
P325_GUARD_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p325_cdc_acm_guard_adapter.py"
P324_CARRIER_SOURCE = REVALIDATION / "s22plus_fyg8_p323_p322_carrier_reanalysis.py"

SCHEMA = "s22plus-fyg8-p325-stock-candidate-build-v1"
VERDICT = "PASS_P325_STOCK_CANDIDATE_BUILD_H0_FRESH_IDENTITY"
STATUS = "IMPLEMENTED_H0_FRESH_IDENTITY_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P325_RUN_ID = artifact.P325_RUN_ID
P325_RUN_ID_HEX = artifact.P325_RUN_ID_HEX
P324_PREDECESSOR_RUN_ID_HEX = artifact.P324_PREDECESSOR_RUN_ID_HEX


class AuditError(RuntimeError):
    """The P3.24 predecessor or P3.25 source/artifact identity differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise AuditError(f"{label} has duplicate key {key}")
            value[key] = item
        return value

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


def _load_bound_p324() -> types.ModuleType:
    payload = _stable(
        P324_BUILDER_SOURCE,
        "P3.24 builder source",
        2 << 20,
        P324_BUILDER_IDENTITY,
        nlink=1,
    )
    module = types.ModuleType("s22plus_fyg8_p324_builder_bound_for_p325")
    module.__file__ = str(P324_BUILDER_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P324_BUILDER_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("P3.24 builder failed to load") from exc
    for name in ("build_result", "audit_existing", "_ENGINE", "_ORIGINAL_BUILD_ONCE"):
        if not hasattr(module, name):
            raise AuditError(f"P3.24 builder lacks {name}")
    if getattr(module, "P324_RUN_ID_HEX", None) != artifact.P324_RUN_ID_HEX:
        raise AuditError("P3.24 builder run identity differs")
    return module


_P324 = _load_bound_p324()
try:
    _P324_PREDECESSOR_PAYLOAD = _stable(
        P324_OUTPUT / "result.json",
        "P3.24 predecessor result",
        4 << 20,
        P324_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    _P324_PREDECESSOR = _strict_json(
        _P324_PREDECESSOR_PAYLOAD, "P3.24 predecessor result"
    )
except Exception as exc:
    raise AuditError("P3.24 predecessor result is unavailable") from exc
if (
    _P324_PREDECESSOR.get("run_id_hex") != artifact.P324_RUN_ID_HEX
    or _P324_PREDECESSOR.get("schema")
    != "s22plus-fyg8-p324-stock-candidate-build-v1"
    or _P324_PREDECESSOR.get("scope", {}).get("device_contact") is not False
    or _P324_PREDECESSOR.get("scope", {}).get("live_authority_created") is not False
):
    raise AuditError("P3.24 predecessor is not the expected host-only result")

_ENGINE = _P324._ENGINE
_ORIGINAL_BUILD_ONCE = _ENGINE._build_once
_ORIGINAL_AUDIT_EXISTING = _ENGINE.audit_existing
_BASE_NORMALIZE = _P324._normalize_result


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    payload = _stable(
        P324_OUTPUT / "result.json",
        "P3.24 predecessor result",
        4 << 20,
        P324_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    value = _strict_json(payload, "P3.24 predecessor result")
    if value != _P324_PREDECESSOR:
        raise AuditError("P3.24 predecessor result changed after binding")
    source = _stable(
        P324_BUILDER_SOURCE,
        "P3.24 predecessor builder source",
        2 << 20,
        P324_BUILDER_IDENTITY,
        nlink=1,
    )
    return value, payload, source


def _current_sources() -> dict[str, bytes]:
    paths = {
        "p325_stock_candidate_build.py": SELF_SOURCE,
        "p325_artifact_identity.py": P325_ARTIFACT_SOURCE,
        "p324_acm_primary_runtime.py": P324_ACM_SOURCE,
        "p325_stock_process_v2_adapter.py": P325_ADAPTER_SOURCE,
        "p325_cdc_acm_guard_adapter.py": P325_GUARD_ADAPTER_SOURCE,
        "p323_p322_carrier_reanalysis.py": P324_CARRIER_SOURCE,
    }
    return {
        name: _stable(path, f"P325 source {name}", 2 << 20, nlink=1)
        for name, path in paths.items()
    }


def _copy(path: Path, destination: Path, expected: Mapping[str, Any], label: str) -> dict[str, Any]:
    payload = _stable(path, label, 128 << 20, expected)
    _ENGINE.p321._write_exclusive(destination, payload)
    return identity(payload)


def _copy_source_closure(
    output_root: Path, predecessor: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    source_root = output_root / "stock-sources"
    _ENGINE.p321._mkdir(source_root)
    receipts: dict[str, dict[str, Any]] = {}
    runtime_receipt: dict[str, Any] | None = None
    expected_closure = predecessor.get("source_closure")
    if not isinstance(expected_closure, dict) or len(expected_closure) != 12:
        raise AuditError("P3.24 source closure is invalid")
    for name, expected in sorted(expected_closure.items()):
        before = _stable(
            P324_OUTPUT / "stock-sources" / name,
            f"P3.24 source {name}",
            2 << 20,
            expected,
            mode=0o400,
            nlink=1,
        )
        after = before
        if name == "s22plus_fyg8_p290_e3_runtime.inc.c":
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
        raise AuditError("P3.25 runtime source is absent")
    _ENGINE.p321._fsync_directory(source_root)
    return receipts, runtime_receipt


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, packager, packager_source = _P324._load_packager()
    packager.RUN_ID = P325_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    return helper, packager, packager_source


class _RuntimeCompat:
    RuntimeRepairError = acm.AcmPrimaryError

    @staticmethod
    def transform_runtime_include(value: bytes) -> bytes:
        return acm.transform_runtime_include(value)

    @staticmethod
    def validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
        return acm.validate_transform(before, after)


# Redirect only the phase-2 engine's narrow bindings.  The packager, boot-only
# join, and rollback parser remain delegated to the exact P3.24 implementation.
_ENGINE._current_sources = _current_sources
_ENGINE._predecessor = _predecessor
_ENGINE._copy_source_closure = _copy_source_closure
_ENGINE._load_packager = _load_packager
_ENGINE.artifact = artifact
_ENGINE.adapter = adapter
_ENGINE.repair = _RuntimeCompat
_ENGINE.P321_OUTPUT = P324_OUTPUT
_ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_ENGINE.P322_ARTIFACT_SOURCE = P325_ARTIFACT_SOURCE
_ENGINE.P322_REPAIR_SOURCE = P324_ACM_SOURCE
_ENGINE.P322_ADAPTER_SOURCE = P325_ADAPTER_SOURCE
_ENGINE.P322_RUN_ID = P325_RUN_ID
_ENGINE.P322_RUN_ID_HEX = P325_RUN_ID_HEX
_ENGINE.SCHEMA = SCHEMA
_ENGINE.VERDICT = VERDICT
_ENGINE.STATUS = STATUS
_ENGINE.TARGET = TARGET

for name, value in {
    "artifact": artifact,
    "adapter": adapter,
    "P324_RUN_ID": P325_RUN_ID,
    "P324_RUN_ID_HEX": P325_RUN_ID_HEX,
    "SCHEMA": SCHEMA,
    "VERDICT": VERDICT,
    "STATUS": STATUS,
    "TARGET": TARGET,
}.items():
    setattr(_P324, name, value)


def _normalize_result(value: dict[str, Any]) -> dict[str, Any]:
    result = _BASE_NORMALIZE(value)
    if (
        result.get("schema") != SCHEMA
        or result.get("run_id_hex") != P325_RUN_ID_HEX
        or result.get("lineage", {}).get("predecessor_run_id")
        != P324_PREDECESSOR_RUN_ID_HEX
    ):
        raise AuditError("P325 result projection header differs")
    candidate = result.get("phase2", {}).get("candidate")
    if not isinstance(candidate, dict):
        raise AuditError("P325 candidate projection is absent")
    candidate["differs_from_consumed_p324"] = candidate.get(
        "differs_from_consumed_p323", False
    )
    candidate.pop("differs_from_consumed_p323", None)
    if candidate["differs_from_consumed_p324"] is not True:
        raise AuditError("P325 candidate repeats the consumed P3.24 AP")
    preservation = result.get("preservation")
    if not isinstance(preservation, dict):
        raise AuditError("P325 preservation projection is absent")
    for key in (
        "p323_consumed_candidate_unchanged",
        "p323_source_closure_reopened",
        "p321_consumed_candidate_unchanged",
        "p321_source_closure_reopened",
        "p322_consumed_candidate_unchanged",
        "p322_source_closure_reopened",
    ):
        preservation.pop(key, None)
    preservation["p324_consumed_candidate_unchanged"] = True
    preservation["p324_source_closure_reopened"] = True
    preservation["runtime_byte_equivalent_to_p324"] = True
    preservation["runtime_byte_equivalent_to_p323"] = True
    helpers = result.get("helper_sources")
    if not isinstance(helpers, dict):
        raise AuditError("P325 helper source receipts are absent")
    helpers["p324_stock_candidate_build.py"] = identity(
        _stable(P324_BUILDER_SOURCE, "P324 builder source", 2 << 20, P324_BUILDER_IDENTITY)
    )
    guard_receipt = identity(
        _stable(
            P325_GUARD_ADAPTER_SOURCE,
            "P325 CDC ACM guard adapter source",
            2 << 20,
            {"size": 6_295, "sha256": "13d4ba6ee935d5b7a73d06f0e4e7ef34b5ac567fbed89813113205f87f34a648"},
        )
    )
    result["guard_adapter"] = {
        "schema": guard_adapter.SCHEMA,
        "contract_id": guard_adapter.CONTRACT_ID,
        "base_contract_id": guard_adapter.BASE_CONTRACT_ID,
        "required_modem_manager_properties": list(
            guard_adapter.REQUIRED_MODEM_MANAGER_PROPERTIES
        ),
        "source": {
            "path": str(P325_GUARD_ADAPTER_SOURCE.relative_to(ROOT)),
            **guard_receipt,
        },
        "host_only": True,
        "device_contact": False,
        "observer_taxonomy_unchanged": True,
    }
    result["helper_sources"]["p325_cdc_acm_guard_adapter.py"] = guard_receipt
    result["limitations"] = [
        "P325 changes only the run-bound Image/IKCONFIG, /init identity, and Carrier/observer adapter labels.",
        "The P3.24 ACM-primary runtime is retained byte-for-byte; the new CDC ACM guard seam does not rewrite receipts or classifications.",
        "No kernel Full-LTO, device contact, approval, D0, D1, F1, recovery, replay, or live authority is created.",
    ]
    result["compatibility_labels"] = {
        "inherited_input_names": ["p321-result.json", "p321-stock-candidate-build.py"],
        "actual_predecessor": "P324",
        "presentation_only": True,
        "baseline_reanalysis": "not required for artifact-only H0; required before any P325 live-result comparison",
    }
    result["schema"] = SCHEMA
    result["verdict"] = VERDICT
    result["status"] = STATUS
    result["target"] = TARGET
    result["run_id_hex"] = P325_RUN_ID_HEX
    return result


def _p325_json_bytes(value: dict[str, Any]) -> bytes:
    return _json_bytes(_normalize_result(value))


_P324._normalize_result = _normalize_result
_ENGINE._json_bytes = _p325_json_bytes


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    audit_only: bool = False,
) -> dict[str, Any]:
    output_root = output_root.absolute()
    if audit_only:
        return audit_existing(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("P325 output already exists")
    output_root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.parent.chmod(0o700)
    _ORIGINAL_BUILD_ONCE(output_root)
    return _strict_json(
        _stable(
            output_root / "result.json",
            "P325 result after build",
            4 << 20,
            mode=0o400,
            nlink=1,
        ),
        "P325 result after build",
    )


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.absolute()
    raw = _stable(
        output_root / "result.json",
        "P325 result",
        4 << 20,
        mode=0o400,
        nlink=1,
    )
    stored = _strict_json(raw, "P325 result")
    try:
        audited = _ORIGINAL_AUDIT_EXISTING(output_root)
    except Exception as exc:
        raise AuditError("P325 phase-2 output did not reopen") from exc
    normalized = _normalize_result(audited)
    if stored != normalized:
        raise AuditError("P325 normalized result differs from stored bytes")
    return stored


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        result = build_result(output, audit_only=args.audit_only)
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
                "identity": identity(_stable(output / "result.json", "P325 result", 4 << 20)),
                "created": not args.audit_only,
                "device_contact": False,
                "live_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


__all__ = [
    "AuditError",
    "DEFAULT_OUTPUT_ROOT",
    "P324_BUILDER_IDENTITY",
    "P324_BUILDER_SOURCE",
    "P324_OUTPUT",
    "P324_PREDECESSOR_RUN_ID_HEX",
    "P325_ARTIFACT_SOURCE",
    "P325_GUARD_ADAPTER_SOURCE",
    "P325_RUN_ID",
    "P325_RUN_ID_HEX",
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
