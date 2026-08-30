#!/usr/bin/env python3
"""Materialize the bounded P3.20 observer-integrated stock candidate, H0 only.

This builder starts from the exact stock runtime used to reproduce the
consumed P3.19 candidate (the ``-55`` output), applies the finalized P320
observer composition to both runtime seams, and reuses the pinned P319
userspace/package helpers for a private boot-only A/B build.  No device, ADB,
Odin, transfer, authority, or new Carrier/detail ABI is created here.
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
from collections.abc import Callable
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
AUDITOR = Path(__file__).resolve()

P319_ROOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p319/stock-witness-runtime-v1-20260821-55"
P319_RESULT = P319_ROOT / "result.json"
P319_SOURCE_ROOT = P319_ROOT / "stock-sources"
P319_MODULE_ROOT = P319_ROOT / "module-bytes"
P319_LIVE_CANDIDATE_AP = P319_ROOT / "candidate-a/odin4/AP.tar.md5"
P319_ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
P319_FIXED_IMAGE = P319_ROOT / "inputs/fixed-Image"
P319_CHILD_SOURCE = P319_ROOT / "inputs/child-source.c"
P319_BASE_BOOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p311/candidate-a/boot.img"
P319_STOCK_BUILDER = ROOT / "workspace/public/src/scripts/analysis/s22plus_fyg8_p319_stock_candidate_build.py"
P320_WIRING = ROOT / "workspace/public/src/scripts/analysis/s22plus_fyg8_p320_kmsg_witness_wiring.py"
P319_ENVELOPE = ROOT / "workspace/public/src/scripts/analysis/s22plus_fyg8_p319_kmsg_record_envelope.py"
P320_OBSERVER = ROOT / "workspace/public/src/scripts/analysis/s22plus_fyg8_p320_observer_contract.py"
O2_LOADER_CORE = ROOT / "workspace/public/src/native-init/s22plus_o2_loader_core.h"

DEFAULT_OUTPUT_ROOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p320/stock-candidate-build-v1-20260830-03"
HISTORICAL_OUTPUT_ROOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p320/stock-candidate-build-v1-20260830-01"
FAILED_ATTEMPT_OUTPUT_ROOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p320/stock-candidate-build-v1-20260830-02"
SCHEMA = "s22plus-fyg8-p320-stock-candidate-build-v2"
VERDICT = "PASS_P320_STOCK_CANDIDATE_BUILD_H0_OBSERVER_INTEGRATED"
STATUS = "IMPLEMENTED_H0_OBSERVER_INTEGRATED_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P319_RUNTIME_ABI = 2

# This is intentionally distinct from the consumed P319 stock run id.
P320_RUN_ID = bytes.fromhex("c320f1e0a90b5e6d7c8a9b0c1d2e3f40")
P319_RUN_ID = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")

P319_RESULT_IDENTITY = {
    "size": 392_886,
    "sha256": "21beec5d2010ecb5804c09055c93a24f83f0fc4be0c9125d24a831908efeaa4a",
}
P319_RUNTIME_IDENTITY = {
    "size": 435_334,
    "sha256": "0a12a9c0f148d58009ebc378b667733b5913d46ebf6466dff3f37bbb850c51a9",
}
P319_AP_IDENTITY = {
    "size": 27_279_401,
    "sha256": "db5666ac794dfbf6f64192d7ea341ed79ff330f03db74c57da5ef61f659032f6",
}
P319_ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}
P319_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8",
}
P319_CHILD_IDENTITY = {
    "size": 1_112,
    "sha256": "2af86dda0f6c93ee90996d89c9803bd84bab16b909d25b732b69144fe8760e14",
}
# The source result is authoritative for the complete 12-file closure.  The
# explicit map is repeated here so a missing/extra source cannot be silently
# accepted when the private result is regenerated.
P319_SOURCE_IDENTITIES = {
    "s22plus_fyg8_p260_e3_runtime.inc.c": {"size": 20_665, "sha256": "767bd359de56cb24be84c4479cd01d4f710a676490c23f966617b996fe5cc612"},
    "s22plus_fyg8_p282_classifier.inc.c": {"size": 14_317, "sha256": "e14a634ec39102d999f51e64b01b1350d9c000e465f01b639b106d51c36d483e"},
    "s22plus_fyg8_p286_classifier.inc.c": {"size": 3_701, "sha256": "14b82ca22e307708cc412b29fa2b7e4784dc791348298c376ab3d8bc4d66d09e"},
    "s22plus_fyg8_p286_e3_plan.h": {"size": 5_316, "sha256": "57d7467887797d2377186e46cafecd2efaa9e660a5c48f7b543441251102c9f1"},
    "s22plus_fyg8_p286_trace_descriptor.h": {"size": 27_172, "sha256": "3e233e3eeee6ac8c522f2ae7352bce1ed736de35c85d6869b0f3e68573b6f735"},
    "s22plus_fyg8_p288_classifier.inc.c": {"size": 1_873, "sha256": "7a15ae652d652a321e1291fd6fe4f6b400a219f22337f7886ec63f7f4e059025"},
    "s22plus_fyg8_p290_checkpoint.c": {"size": 40_903, "sha256": "ef1d2bfe327daa4c8d8010e880ceb7bb70ecbb254c23b1d23b94b580d21f40c4"},
    "s22plus_fyg8_p290_e3_runtime.c": {"size": 31_282, "sha256": "c55aae39ac4846e952e2d6c8672b93dd44f8a8d2388645aa8cd8dcd761f60064"},
    "s22plus_fyg8_p290_e3_runtime.inc.c": P319_RUNTIME_IDENTITY,
    "s22plus_fyg8_p290_positions.h": {"size": 2_674, "sha256": "33e880a6ab8ea887579add07212f063dbdd80dd27b1555485a71d1198c82d247"},
    "s22plus_r4w1e_checkpoint.h": {"size": 3_348, "sha256": "8584bd67d8c75c5db033cfb47cdbb6d300da4647fbf34bb4250a338792e309b3"},
    "s22plus_r4w1e_e1_runtime.c": {"size": 19_398, "sha256": "8fd76a904f72c02c8bb10c6b0505f8d3b01e4db4ad349dc4228b5609ac945284"},
}

P320_WIRING_IDENTITY = {
    "size": 11_181,
    "sha256": "dd396e1d0db584c7a6e9b3f7fe886a21d691c57c33f20e690d8402ae1a0cd5ee",
}
P319_ENVELOPE_IDENTITY = {
    "size": 6_367,
    "sha256": "a0f6f9d1dffd85cc5e6beaa838a8f57e229b54c50a7e169c7f91dfe86a074c24",
}
P320_OBSERVER_COMMIT = "1591df347f0173b5063bb355f0b683fe958a4467"
P320_OBSERVER_SOURCE_IDENTITY = {
    "size": 78_508,
    "sha256": "0ee66eb9ea774b54eb390d6eb869baa72587c812c830f98a040d89037ab6c395",
}
P319_STOCK_BUILDER_IDENTITY = {
    "size": 114_260,
    "sha256": "544b03e02ce5490bb2db03a4bbdbbda806ea2bb354026162efc54b0173610058",
}
O2_LOADER_CORE_IDENTITY = {
    "size": 10_420,
    "sha256": "c4f5dd0f1bac4e4d614ae683b1bab7f1908dd337f5c0e244cab424c4cea556e8",
}
P319_MODULE_LATCH_IDENTITY = {
    "size": 423_232,
    "sha256": "27be8abfe121867e50b0f8b2094fff1d615181e2e0168e5c37e9f8fab2364a2b",
}

RUNTIME_NAME = "s22plus_fyg8_p290_e3_runtime.c"
RUNTIME_INCLUDE_NAME = "s22plus_fyg8_p290_e3_runtime.inc.c"
PLAN_NAME = "s22plus_fyg8_p286_e3_plan.h"
CHECKPOINT_NAME = "s22plus_fyg8_p290_checkpoint.c"
CHILD_NAME = "child-source.c"


class AuditError(RuntimeError):
    """A source, transform, package, or publication invariant differs."""


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def stable_bytes(
    path: Path,
    label: str,
    maximum: int,
    expected: dict[str, Any] | None = None,
    *,
    required_mode: int | None = None,
    required_nlink: int | None = None,
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
        or before.st_nlink < 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or expected is not None and identity(payload) != expected
        or required_mode is not None and stat.S_IMODE(before.st_mode) != required_mode
        or required_nlink is not None and before.st_nlink != required_nlink
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _write_exclusive(path: Path, payload: bytes, mode: int = 0o400) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        mode,
    )
    try:
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise AuditError(f"short private publication: {path.name}")
            offset += written
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or state.st_nlink != 1
            or state.st_size != len(payload)
            or stat.S_IMODE(state.st_mode) != mode
        ):
            raise AuditError(f"private publication identity differs: {path.name}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _mkdir(path: Path) -> None:
    path.mkdir(mode=0o700)
    path.chmod(0o700)


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise AuditError(f"{label} has duplicate key {key}")
            value[key] = item
        return value

    def reject_constant(token: str) -> Any:
        raise AuditError(f"{label} has non-finite constant {token}")

    try:
        value = json.loads(
            payload.decode("ascii"),
            object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} root differs")
    return value


def _strict_children(path: Path, expected: set[str], label: str) -> None:
    try:
        state = path.lstat()
        children = {child.name for child in path.iterdir()}
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if (
        stat.S_ISLNK(state.st_mode)
        or not stat.S_ISDIR(state.st_mode)
        or stat.S_IMODE(state.st_mode) != 0o700
        or children != expected
    ):
        raise AuditError(f"{label} child set differs")


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def _load_bound_module(path: Path, expected: dict[str, Any], name: str) -> tuple[types.ModuleType, bytes]:
    source = stable_bytes(path, f"bound helper {path.name}", 2 * 1024 * 1024, expected)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    if name == "p320_wiring_bound":
        module.__dict__["_P320_WIRING_BOUND_SOURCE"] = source
    if name == "p319_stock_builder_bound":
        module.__dict__["_P319_STOCK_BOUND_SOURCE"] = source
    sys.modules[name] = module
    try:
        exec(compile(source.decode("utf-8"), str(path), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError(f"bound helper execution failed: {path.name}") from exc
    return module, source


def _bind_p320_helpers() -> tuple[types.ModuleType, types.ModuleType, dict[str, bytes]]:
    envelope, envelope_source = _load_bound_module(
        P319_ENVELOPE, P319_ENVELOPE_IDENTITY, "p319_envelope_bound"
    )
    wiring, wiring_source = _load_bound_module(
        P320_WIRING, P320_WIRING_IDENTITY, "p320_wiring_bound"
    )
    if wiring.P320_C_SOURCE != envelope.P320_C_SOURCE:
        raise AuditError("P320 envelope source is not the committed envelope")
    if wiring.RETAINED_RUNTIME_SHA256 != P319_RUNTIME_IDENTITY["sha256"]:
        raise AuditError("P320 wiring runtime lineage differs")
    if wiring.LIVE_CANDIDATE_AP_SHA256 != P319_AP_IDENTITY["sha256"]:
        raise AuditError("P320 wiring AP lineage differs")
    if wiring.LIVE_CANDIDATE_RESULT_SHA256 != P319_RESULT_IDENTITY["sha256"]:
        raise AuditError("P320 wiring result lineage differs")
    if wiring.P319_PARSER_ABI_VERSION != 2 or wiring.P319_PARSER_ENTRY != b"p319_witness_observe_v2":
        raise AuditError("P320 wiring parser binding differs")
    return wiring, envelope, {
        "p319_kmsg_record_envelope.py": envelope_source,
        "p320_kmsg_witness_wiring.py": wiring_source,
    }


def _bind_observer_contract() -> tuple[types.ModuleType, bytes]:
    """Load the finalized observer source at its immutable commit identity."""
    observer, source = _load_bound_module(
        P320_OBSERVER,
        P320_OBSERVER_SOURCE_IDENTITY,
        "p320_observer_contract_bound",
    )
    required = (
        "bind_exact_sources", "compose_runtime", "compose_wrapper",
        "P320_C_OBSERVER_SOURCE", "P320_C_RECORD_SOURCE",
        "P320_PAYLOAD_ABI", "OBSERVER_RECEIPT_OFFSET", "OBSERVER_RECEIPT_SIZE",
    )
    if any(not hasattr(observer, name) for name in required):
        raise AuditError("P320 observer contract API is incomplete")
    if observer.P320_PAYLOAD_ABI != 4 or observer.OBSERVER_RECEIPT_OFFSET != 61 \
            or observer.OBSERVER_RECEIPT_SIZE != 15:
        raise AuditError("P320 observer payload ABI differs")
    try:
        lineage = observer.bind_exact_sources()
    except Exception as exc:
        raise AuditError("P320 observer source lineage cannot be bound") from exc
    if (
        not isinstance(lineage, dict)
        or lineage.get("target") != TARGET
        or lineage.get("runtime_abi") != P319_RUNTIME_ABI
        or lineage.get("raw_checkpoint_source") != "/proc/last_kmsg"
        or lineage.get("exact_runtime_bound") is not True
        or lineage.get("envelope_source_bound") is not True
        or lineage.get("wiring_source_bound") is not True
    ):
        raise AuditError("P320 observer lineage differs")
    return observer, source


def _load_live_result() -> tuple[dict[str, Any], bytes]:
    payload = stable_bytes(P319_RESULT, "P319 -55 result", 2 * 1024 * 1024, P319_RESULT_IDENTITY)
    result = _strict_json(payload, "P319 -55 result")
    if (
        result.get("schema") != "s22plus-fyg8-p319-stock-witness-runtime-v1"
        or result.get("verdict") != "PASS_P319_STOCK_WITNESS_RUNTIME_H0"
    ):
        raise AuditError("P319 -55 result schema differs")
    sources = result.get("source", {}).get("materialized_stock_sources")
    if not isinstance(sources, dict) or sources != P319_SOURCE_IDENTITIES:
        raise AuditError("P319 -55 source closure differs")
    phase2 = result.get("phase2")
    candidate = phase2.get("candidate") if isinstance(phase2, dict) else None
    if not isinstance(candidate, dict) or candidate.get("byte_identical") is not True:
        raise AuditError("P319 -55 candidate A/B identity differs")
    for label in ("a", "b"):
        row = candidate.get(label)
        if not isinstance(row, dict):
            raise AuditError(f"P319 -55 candidate {label} is absent")
        if row.get("ap_tar_md5") != P319_AP_IDENTITY:
            raise AuditError(f"P319 -55 candidate {label} AP differs")
        package = row.get("package")
        if not isinstance(package, dict) or package.get("ap_tar_md5") != P319_AP_IDENTITY:
            raise AuditError(f"P319 -55 candidate {label} package AP differs")
    stable_bytes(P319_LIVE_CANDIDATE_AP, "P319 consumed candidate AP", 64 * 1024 * 1024, P319_AP_IDENTITY)
    stable_bytes(P319_ROLLBACK_AP, "P319 exact rollback AP", 64 * 1024 * 1024, P319_ROLLBACK_IDENTITY)
    stable_bytes(P319_FIXED_IMAGE, "P319 fixed Image", 64 * 1024 * 1024, P319_IMAGE_IDENTITY)
    stable_bytes(P319_CHILD_SOURCE, "P319 child source", 64 * 1024, P319_CHILD_IDENTITY)
    stable_bytes(P319_BASE_BOOT, "P319 clean base boot", 128 * 1024 * 1024, result["phase2"]["candidate"]["base"])
    return result, payload


def _function_bytes(source: bytes, signature: bytes, label: str) -> bytes:
    start = source.find(signature)
    if start < 0:
        raise AuditError(f"{label} signature is absent")
    brace = source.find(b"{", start)
    if brace < 0:
        raise AuditError(f"{label} body is absent")
    depth = 0
    for index in range(brace, len(source)):
        if source[index:index + 1] == b"{":
            depth += 1
        elif source[index:index + 1] == b"}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AuditError(f"{label} body is truncated")


def compose_runtime_transforms(
    runtime: bytes,
    transforms: tuple[Callable[[bytes], bytes], ...] = (),
) -> bytes:
    """Apply deterministic, independently reviewed post-composition transforms."""
    current = runtime
    for index, transform in enumerate(transforms):
        current = transform(current)
        if not isinstance(current, bytes):
            raise AuditError(f"P320 runtime transform {index} did not return bytes")
    return current


def transform_runtime(
    original: bytes,
    observer: types.ModuleType | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Apply the finalized observer composition directly to exact P319 bytes."""
    if not isinstance(original, bytes):
        raise AuditError("P319 runtime source must be bytes")
    if observer is None:
        observer, _ = _bind_observer_contract()
    try:
        transformed = observer.compose_runtime(original)
    except Exception as exc:
        raise AuditError("P320 observer runtime composition failed") from exc
    if not isinstance(transformed, bytes):
        raise AuditError("P320 observer runtime composition is not bytes")
    if b"return P319_DETAIL_WITNESS_BOUNDARY;" in transformed:
        raise AuditError("P320 observer path still escapes legacy boundary detail")
    if transformed == original:
        raise AuditError("P320 observer runtime was not transformed")
    observer_c = observer.P320_C_OBSERVER_SOURCE.encode("ascii")
    record_c = observer.P320_C_RECORD_SOURCE.encode("ascii")
    if observer_c not in transformed or record_c not in transformed:
        raise AuditError("P320 observer C composition is incomplete")
    if b"p320_observer_finalize_stock_payload_v4(payload)" not in transformed:
        raise AuditError("P320 ABI-v4 payload finalizer is absent")
    return transformed, {
        "original": identity(original),
        "transformed": identity(transformed),
        "composition": "observer.compose_runtime",
        "observer_contract_commit": P320_OBSERVER_COMMIT,
        "observer_source": P320_OBSERVER_SOURCE_IDENTITY,
        "payload_abi": 4,
        "receipt_offset": 61,
        "receipt_size": 15,
        "changed_only_in_observer_runtime_seams": True,
        "changed_only_injected_envelope_and_record_seam": False,
        "declared_runtime_seams": [
            "observer_source_insertion",
            "p303_kmsg_record",
            "p303_kmsg_begin",
            "p303_kmsg_drain",
            "p303_kmsg_finish",
            "p319_note_successful_module",
            "stock_payload_abi4",
            "stock_payload_v4_finalizer",
        ],
        "parser_entry": "p319_witness_observe_v2",
        "human_message_only": True,
        "dictionary_lines_excluded": True,
        "header_extensions_excluded": True,
        "fragment_flag_metadata_excluded": True,
        "fragment_reassembly": False,
        "existing_p319_detail_namespace_reused": False,
        "existing_stock_terminal_detail_reused": True,
        "new_observer_error_kind_namespace": True,
        "new_detail_namespace": False,
        "fail_closed_on_envelope_error": False,
        "observer_failure_fail_soft": True,
        "final_ambiguous_on_observer_error": True,
        "legacy_observer_detail_escape": False,
        "stock_payload_carrier_decoder_semantics_preserved": True,
    }


def transform_wrapper(
    original: bytes,
    observer: types.ModuleType | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Apply the finalized observer post-module seam to exact P319 wrapper bytes."""
    if not isinstance(original, bytes):
        raise AuditError("P319 runtime wrapper source must be bytes")
    if observer is None:
        observer, _ = _bind_observer_contract()
    try:
        transformed = observer.compose_wrapper(original)
    except Exception as exc:
        raise AuditError("P320 observer wrapper composition failed") from exc
    if not isinstance(transformed, bytes) or transformed == original:
        raise AuditError("P320 observer wrapper was not transformed")
    if b"return P319_DETAIL_WITNESS_BOUNDARY;" in transformed:
        raise AuditError("P320 wrapper still escapes legacy boundary detail")
    required = (
        b"p320_observer_transport_failure()",
        b"(void)p320_observer_set_active_module(0U, 0);",
        b"if (load_rc != 0L) return load_rc;",
    )
    if any(token not in transformed for token in required):
        raise AuditError("P320 observer wrapper composition is incomplete")
    return transformed, {
        "original": identity(original),
        "transformed": identity(transformed),
        "composition": "observer.compose_wrapper",
        "observer_contract_commit": P320_OBSERVER_COMMIT,
        "observer_source": P320_OBSERVER_SOURCE_IDENTITY,
        "changed_only_observer_post_module_seam": True,
        "legacy_observer_detail_escape": False,
        "module_load_fail_fast": True,
        "active_module_clear_after_drain": True,
    }


def _copy_input(path: Path, destination: Path, expected: dict[str, Any], label: str, maximum: int) -> dict[str, Any]:
    payload = stable_bytes(path, label, maximum, expected)
    _write_exclusive(destination, payload)
    return identity(payload)


def _copy_source_closure(
    output_root: Path,
    live_result: dict[str, Any],
    transformed_sources: dict[str, bytes],
) -> dict[str, dict[str, Any]]:
    source_root = output_root / "stock-sources"
    _mkdir(source_root)
    materialized: dict[str, dict[str, Any]] = {}
    for name, expected in P319_SOURCE_IDENTITIES.items():
        source = P319_SOURCE_ROOT / name
        payload = transformed_sources[name] if name in transformed_sources else stable_bytes(
            source, f"P319 source {name}", 2 * 1024 * 1024, expected, required_mode=0o400, required_nlink=1
        )
        if name in transformed_sources and identity(payload) == expected:
            raise AuditError(f"P320 source was not transformed: {name}")
        _write_exclusive(source_root / name, payload)
        materialized[name] = identity(payload)
    if set(materialized) != set(P319_SOURCE_IDENTITIES):
        raise AuditError("P320 source closure set differs")
    return materialized


def _audit_static_elf(helper: types.ModuleType, path: Path, label: str) -> dict[str, Any]:
    file_text = helper._run_bound_capture(
        "file", ["-b", path], cwd=ROOT, text=True, capture_output=True, check=True,
    ).stdout
    readelf = helper._run_bound_capture(
        "readelf", ["-W", "-h", "-l", path], cwd=ROOT, text=True, capture_output=True, check=True,
    ).stdout
    undefined = helper._run_bound_capture(
        "nm", ["-u", path], cwd=ROOT, text=True, capture_output=True, check=True,
    ).stdout
    if (
        "ELF 64-bit LSB executable, ARM aarch64" not in file_text
        or "statically linked" not in file_text
        or "INTERP" in readelf
        or "DYNAMIC" in readelf
        or undefined.strip()
    ):
        raise AuditError(f"{label} is not a static AArch64 ELF")
    return {"static_aarch64": True, "identity": identity(path.read_bytes())}


def _build_phase2(
    output_root: Path,
    helper: types.ModuleType,
    base_boot: bytes,
    image_bytes: bytes,
    rollback_before: bytes,
) -> dict[str, Any]:
    source_root = output_root / "stock-sources"
    userspace_a = helper._compile_userspace(source_root, output_root / "userspace-a", label="a")
    userspace_b = helper._compile_userspace(source_root, output_root / "userspace-b", label="b")
    if userspace_a != userspace_b:
        raise AuditError("P320 userspace A/B differs")
    for label in ("a", "b"):
        _audit_static_elf(helper, output_root / f"userspace-{label}/init", f"P320 userspace {label} init")
        _audit_static_elf(helper, output_root / f"userspace-{label}/s22-e1-child", f"P320 userspace {label} child")
    init_bytes = stable_bytes(output_root / "userspace-a/init", "P320 init", 1 << 20, userspace_a["init"], required_mode=0o400, required_nlink=1)
    child_bytes = stable_bytes(output_root / "userspace-a/s22-e1-child", "P320 child", 1 << 20, userspace_a["child"], required_mode=0o400, required_nlink=1)
    module_root = output_root / "module-bytes"
    module_payload = stable_bytes(module_root / "s22plus_dwc3_event_latch.ko", "P320 latch module", 8 << 20, P319_MODULE_LATCH_IDENTITY, required_mode=0o400, required_nlink=1)
    module_payloads = {"s22plus_dwc3_event_latch.ko": module_payload}
    overlay_names = ("s22plus_dwc3_event_latch.ko",)
    candidate_a = helper._package_candidate(
        base_boot, init_bytes, child_bytes, module_payloads,
        overlay_names, output_root / "candidate-a", "a",
    )
    candidate_b = helper._package_candidate(
        base_boot, init_bytes, child_bytes, module_payloads,
        overlay_names, output_root / "candidate-b", "b",
    )
    if candidate_a != candidate_b:
        raise AuditError("P320 candidate A/B differs")
    helper._verify_packaged_candidate(
        output_root / "candidate-a", candidate_a, init_bytes, child_bytes,
        module_payloads, image_bytes, overlay_names, "p320-candidate-a",
    )
    helper._verify_packaged_candidate(
        output_root / "candidate-b", candidate_b, init_bytes, child_bytes,
        module_payloads, image_bytes, overlay_names, "p320-candidate-b",
    )
    if candidate_a["ap_tar_md5"] == P319_AP_IDENTITY:
        raise AuditError("P320 candidate AP repeats consumed P319 AP")
    rollback_after = stable_bytes(P319_ROLLBACK_AP, "P319 rollback after P320 build", 64 << 20, P319_ROLLBACK_IDENTITY)
    if rollback_after != rollback_before:
        raise AuditError("P319 exact rollback changed during P320 build")
    return {
        "built": True,
        "userspace": {"a": userspace_a, "b": userspace_b, "byte_identical": True},
        "static_aarch64": True,
        "boot_builds": 2,
        "ap_builds": 2,
        "candidate": {
            "a": candidate_a,
            "b": candidate_b,
            "byte_identical": True,
            "fixed_image": True,
            "one_boot_img_lz4_member": True,
            "overlay_members": ["lib/modules/s22plus_dwc3_event_latch.ko"],
            "vendor_layer_stock_modules": 72,
            "inherited_modules_not_copied": True,
            "diagnostic_absent": True,
            "ap_differs_from_consumed_p319": True,
        },
        "rollback": {"identity": identity(rollback_after), "untouched": True},
    }


def _make_result(
    *,
    live_result: dict[str, Any],
    lineage: dict[str, Any],
    source_identities: dict[str, dict[str, Any]],
    helper_sources: dict[str, bytes],
    phase2: dict[str, Any],
    input_identities: dict[str, dict[str, Any]],
    tool_identities: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": STATUS,
        "target": TARGET,
        "run_id_hex": P320_RUN_ID.hex(),
        "scope": {
            "tier": "H0",
            "host_only": True,
            "device_contact": False,
            "adb_commands": 0,
            "odin_invocations": 0,
            "candidate_transfers": 0,
            "rollback_transfers": 0,
            "live_authority_created": False,
            "replay": False,
        },
        "lineage": lineage,
        "inputs": input_identities,
        "module_bytes": {
            "s22plus_dwc3_event_latch.ko": P319_MODULE_LATCH_IDENTITY,
        },
        "source_closure": source_identities,
        "helper_sources": {
            name: identity(payload) for name, payload in helper_sources.items()
        } | {"p319_stock_candidate_build.py": P319_STOCK_BUILDER_IDENTITY, "s22plus_o2_loader_core.h": O2_LOADER_CORE_IDENTITY},
        "tools": tool_identities,
        "runtime_transform": lineage["runtime_transform"],
        "wrapper_transform": lineage["wrapper_transform"],
        "phase2": phase2,
        "limitations": [
            "P320 observer failures are fail-soft: the first typed error is retained in the ABI-v4 15-byte receipt and the stock chain closes as AMBIGUOUS using existing detail 0x6726.",
            "The P320 observer path does not emit legacy 0x6020, 0x6021, or 0x6022; full raw records remain recoverable only from the mandatory /proc/last_kmsg retention.",
            "This H0 unit does not create approval, D0/D1/F1/recovery/replay authority.",
            "The P320 envelope accepts ABI-valid dictionary/header-extension shapes, but c records are observed independently without fragment reassembly; no USB, MUX, or causal result is claimed.",
            "No runtime USB, host attach, or physical MUX claim is made by this package.",
        ],
        "preservation": {
            "p319_run_id_unchanged_in_consumed_lineage": P319_RUN_ID.hex(),
            "stock_payload_carrier_decoder_semantics_preserved": True,
            "new_p320_carrier_or_detail_abi": False,
            "stock_payload_abi": 4,
            "observer_error_kind_namespace": "P320_OBSERVER_ERROR_KIND",
            "exact_rollback_untouched": True,
            "historical_p320_prototype_preserved": True,
        },
    }


def build_result(output_root: Path, *, audit_only: bool = False) -> dict[str, Any]:
    output_root = output_root.absolute()
    if audit_only:
        return audit_existing(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("P320 output already exists")
    if not output_root.parent.exists():
        output_root.parent.mkdir(mode=0o700, parents=True)
        output_root.parent.chmod(0o700)
    live_result, _ = _load_live_result()
    wiring, envelope, helper_sources = _bind_p320_helpers()
    observer, observer_source = _bind_observer_contract()
    helper_sources["p320_observer_contract.py"] = observer_source
    packager, packager_source = _load_bound_module(
        P319_STOCK_BUILDER, P319_STOCK_BUILDER_IDENTITY, "p319_stock_builder_bound"
    )
    packager.RUN_ID = P320_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    rollback_before = stable_bytes(P319_ROLLBACK_AP, "P319 rollback before P320 build", 64 << 20, P319_ROLLBACK_IDENTITY)
    original_runtime = stable_bytes(
        P319_SOURCE_ROOT / RUNTIME_INCLUDE_NAME,
        "P319 -55 runtime",
        2 * 1024 * 1024,
        P319_RUNTIME_IDENTITY,
        required_mode=0o400,
        required_nlink=1,
    )
    original_wrapper = stable_bytes(
        P319_SOURCE_ROOT / RUNTIME_NAME,
        "P319 -55 runtime wrapper",
        2 * 1024 * 1024,
        P319_SOURCE_IDENTITIES[RUNTIME_NAME],
        required_mode=0o400,
        required_nlink=1,
    )
    transformed_runtime, transform = transform_runtime(original_runtime, observer)
    transformed_wrapper, wrapper_transform = transform_wrapper(
        original_wrapper, observer
    )
    transformed_runtime = compose_runtime_transforms(transformed_runtime)
    lineage = {
        "p319_result": P319_RESULT_IDENTITY,
        "p319_consumed_ap": P319_AP_IDENTITY,
        "p319_runtime": P319_RUNTIME_IDENTITY,
        "p319_runtime_wrapper": P319_SOURCE_IDENTITIES[RUNTIME_NAME],
        "p319_rollback": P319_ROLLBACK_IDENTITY,
        "p319_result_schema": live_result["schema"],
        "p319_candidate_reproductions": 2,
        "runtime_transform": transform,
        "wrapper_transform": wrapper_transform,
        "p320_observer_contract": {
            "commit": P320_OBSERVER_COMMIT,
            **P320_OBSERVER_SOURCE_IDENTITY,
        },
    }
    _mkdir(output_root)
    input_root = output_root / "inputs"
    _mkdir(input_root)
    input_identities: dict[str, dict[str, Any]] = {}
    input_identities["p319-live-result.json"] = _copy_input(
        P319_RESULT, input_root / "p319-live-result.json", P319_RESULT_IDENTITY, "P319 live result", 2 << 20
    )
    input_identities["p319-stock-candidate-build.py"] = _copy_input(
        P319_STOCK_BUILDER, input_root / "p319-stock-candidate-build.py", P319_STOCK_BUILDER_IDENTITY, "P319 stock builder", 2 << 20
    )
    input_identities["p320-kmsg-witness-wiring.py"] = _copy_input(
        P320_WIRING, input_root / "p320-kmsg-witness-wiring.py", P320_WIRING_IDENTITY, "P320 wiring", 2 << 20
    )
    input_identities["p320-observer-contract.py"] = _copy_input(
        P320_OBSERVER,
        input_root / "p320-observer-contract.py",
        P320_OBSERVER_SOURCE_IDENTITY,
        "P320 observer contract",
        2 << 20,
    )
    input_identities["p319-kmsg-record-envelope.py"] = _copy_input(
        P319_ENVELOPE, input_root / "p319-kmsg-record-envelope.py", P319_ENVELOPE_IDENTITY, "P319 envelope", 2 << 20
    )
    input_identities["s22plus_o2_loader_core.h"] = _copy_input(
        O2_LOADER_CORE, input_root / "s22plus_o2_loader_core.h", O2_LOADER_CORE_IDENTITY, "O2 loader helper", 2 << 20
    )
    input_identities["fixed-Image"] = _copy_input(
        P319_FIXED_IMAGE, input_root / "fixed-Image", P319_IMAGE_IDENTITY, "fixed Image", 64 << 20
    )
    input_identities["p311-base-boot.img"] = _copy_input(
        P319_BASE_BOOT, input_root / "p311-base-boot.img", live_result["phase2"]["candidate"]["base"], "P311 base boot", 128 << 20
    )
    input_identities[CHILD_NAME] = _copy_input(
        P319_CHILD_SOURCE, input_root / CHILD_NAME, P319_CHILD_IDENTITY, "child source", 64 << 10
    )
    source_identities = _copy_source_closure(
        output_root,
        live_result,
        {
            RUNTIME_INCLUDE_NAME: transformed_runtime,
            RUNTIME_NAME: transformed_wrapper,
        },
    )
    module_root = output_root / "module-bytes"
    _mkdir(module_root)
    _copy_input(
        P319_MODULE_ROOT / "s22plus_dwc3_event_latch.ko",
        module_root / "s22plus_dwc3_event_latch.ko",
        P319_MODULE_LATCH_IDENTITY,
        "P319 latch module",
        8 << 20,
    )
    phase2 = _build_phase2(
        output_root, packager,
        stable_bytes(input_root / "p311-base-boot.img", "P320 base boot", 128 << 20, live_result["phase2"]["candidate"]["base"]),
        stable_bytes(input_root / "fixed-Image", "P320 fixed Image", 64 << 20, P319_IMAGE_IDENTITY),
        rollback_before,
    )
    lineage["runtime_transform"] = transform
    lineage["p319_helper_source"] = P319_STOCK_BUILDER_IDENTITY
    lineage["p320_wiring_source"] = P320_WIRING_IDENTITY
    lineage["p319_envelope_source"] = P319_ENVELOPE_IDENTITY
    lineage["o2_loader_helper"] = O2_LOADER_CORE_IDENTITY
    lineage["consumed_candidate_ap_actual"] = P319_AP_IDENTITY
    lineage["candidate_ap_actual"] = phase2["candidate"]["a"]["ap_tar_md5"]
    lineage["candidate_ap_differs_from_consumed"] = phase2["candidate"]["a"]["ap_tar_md5"] != P319_AP_IDENTITY
    lineage["rollback_untouched"] = phase2["rollback"]["untouched"]
    result = _make_result(
        live_result=live_result,
        lineage=lineage,
        source_identities=source_identities,
        helper_sources=helper_sources | {"p319-stock-candidate-build.py": packager_source},
        phase2=phase2,
        input_identities=input_identities,
        tool_identities={
            name: dict(packager.TOOL_IDENTITIES[name])
            for name in sorted(packager.TOOL_IDENTITIES)
        },
    )
    payload = _json_bytes(result)
    _write_exclusive(output_root / "result.json", payload)
    _fsync_directory(input_root)
    _fsync_directory(output_root / "stock-sources")
    _fsync_directory(module_root)
    _fsync_directory(output_root)
    return result


def _audit_source_output(
    output_root: Path,
    result: dict[str, Any],
    observer: types.ModuleType,
) -> None:
    source_root = output_root / "stock-sources"
    names = sorted(path.name for path in source_root.iterdir())
    if names != sorted(P319_SOURCE_IDENTITIES):
        raise AuditError("P320 source output child set differs")
    for name, expected in result["source_closure"].items():
        stable_bytes(source_root / name, f"P320 output source {name}", 2 << 20, expected, required_mode=0o400, required_nlink=1)
    original = stable_bytes(P319_SOURCE_ROOT / RUNTIME_INCLUDE_NAME, "P319 original runtime", 2 << 20, P319_RUNTIME_IDENTITY, required_mode=0o400, required_nlink=1)
    transformed, transform = transform_runtime(original, observer)
    output_runtime = stable_bytes(source_root / RUNTIME_INCLUDE_NAME, "P320 transformed runtime", 2 << 20, result["runtime_transform"]["transformed"], required_mode=0o400, required_nlink=1)
    if transformed != output_runtime or transform != result["runtime_transform"]:
        raise AuditError("P320 runtime regeneration differs")
    original_wrapper = stable_bytes(
        P319_SOURCE_ROOT / RUNTIME_NAME,
        "P319 original runtime wrapper",
        2 << 20,
        P319_SOURCE_IDENTITIES[RUNTIME_NAME],
        required_mode=0o400,
        required_nlink=1,
    )
    transformed_wrapper, wrapper_transform = transform_wrapper(
        original_wrapper, observer
    )
    output_wrapper = stable_bytes(
        source_root / RUNTIME_NAME,
        "P320 transformed runtime wrapper",
        2 << 20,
        result["wrapper_transform"]["transformed"],
        required_mode=0o400,
        required_nlink=1,
    )
    if transformed_wrapper != output_wrapper or wrapper_transform != result["wrapper_transform"]:
        raise AuditError("P320 runtime wrapper regeneration differs")


def audit_existing(output_root: Path) -> dict[str, Any]:
    result_payload = stable_bytes(output_root / "result.json", "P320 result", 2 << 20, required_mode=0o400, required_nlink=1)
    result = _strict_json(result_payload, "P320 result")
    if (
        result.get("schema") != SCHEMA
        or result.get("verdict") != VERDICT
        or result.get("status") != STATUS
    ):
        raise AuditError("P320 result schema/verdict/status differs")
    if result.get("run_id_hex") != P320_RUN_ID.hex() or result.get("scope", {}).get("device_contact") is not False:
        raise AuditError("P320 run/scope differs")
    live_result, _ = _load_live_result()
    _strict_children(
        output_root,
        {"inputs", "stock-sources", "module-bytes", "userspace-a", "userspace-b", "candidate-a", "candidate-b", "result.json"},
        "P320 output root",
    )
    _strict_children(output_root / "inputs", set(result.get("inputs", {})), "P320 input bundle")
    _strict_children(output_root / "module-bytes", {"s22plus_dwc3_event_latch.ko"}, "P320 module bundle")
    if result.get("module_bytes") != {
        "s22plus_dwc3_event_latch.ko": P319_MODULE_LATCH_IDENTITY,
    }:
        raise AuditError("P320 module byte identity differs")
    wiring, envelope, helper_sources = _bind_p320_helpers()
    observer, observer_source = _bind_observer_contract()
    if result.get("lineage", {}).get("p320_observer_contract") != {
        "commit": P320_OBSERVER_COMMIT,
        **P320_OBSERVER_SOURCE_IDENTITY,
    }:
        raise AuditError("P320 observer commit/source identity differs")
    packager, _ = _load_bound_module(P319_STOCK_BUILDER, P319_STOCK_BUILDER_IDENTITY, "p319_stock_builder_audit_bound")
    packager.RUN_ID = P320_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    expected_tools = {
        name: dict(packager.TOOL_IDENTITIES[name])
        for name in sorted(packager.TOOL_IDENTITIES)
    }
    if result.get("tools") != expected_tools:
        raise AuditError("P320 bound packaging tool identities differ")
    _audit_source_output(output_root, result, observer)
    for name, expected in result["inputs"].items():
        path = output_root / "inputs" / name
        stable_bytes(path, f"P320 input {name}", 128 << 20, expected, required_mode=0o400, required_nlink=1)
    image = stable_bytes(output_root / "inputs/fixed-Image", "P320 audit Image", 64 << 20, P319_IMAGE_IDENTITY)
    base = stable_bytes(output_root / "inputs/p311-base-boot.img", "P320 audit base boot", 128 << 20, live_result["phase2"]["candidate"]["base"])
    module = stable_bytes(output_root / "module-bytes/s22plus_dwc3_event_latch.ko", "P320 audit latch", 8 << 20, P319_MODULE_LATCH_IDENTITY)
    init = stable_bytes(output_root / "userspace-a/init", "P320 audit init", 1 << 20, result["phase2"]["userspace"]["a"]["init"], required_mode=0o400, required_nlink=1)
    child = stable_bytes(output_root / "userspace-a/s22-e1-child", "P320 audit child", 1 << 20, result["phase2"]["userspace"]["a"]["child"], required_mode=0o400, required_nlink=1)
    _audit_static_elf(packager, output_root / "userspace-a/init", "P320 audit init")
    _audit_static_elf(packager, output_root / "userspace-a/s22-e1-child", "P320 audit child")
    modules = {"s22plus_dwc3_event_latch.ko": module}
    overlay = ("s22plus_dwc3_event_latch.ko",)
    for label in ("a", "b"):
        candidate = result["phase2"]["candidate"][label]
        packager._verify_packaged_candidate(
            output_root / f"candidate-{label}", candidate, init, child,
            modules, image, overlay, f"p320-audit-candidate-{label}",
        )
    ap = result["phase2"]["candidate"]["a"]["ap_tar_md5"]
    if ap == P319_AP_IDENTITY or not result["lineage"]["candidate_ap_differs_from_consumed"]:
        raise AuditError("P320 audit candidate AP repeats consumed AP")
    rollback = stable_bytes(P319_ROLLBACK_AP, "P319 rollback audit", 64 << 20, P319_ROLLBACK_IDENTITY)
    if identity(rollback) != P319_ROLLBACK_IDENTITY:
        raise AuditError("P319 rollback identity changed")
    if not result["phase2"]["rollback"]["untouched"] or result["phase2"]["rollback"]["identity"] != P319_ROLLBACK_IDENTITY:
        raise AuditError("P320 rollback preservation receipt differs")
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


if __name__ == "__main__":
    raise SystemExit(main())
