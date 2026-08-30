#!/usr/bin/env python3
"""Materialize the bounded P3.20 envelope-only stock candidate, H0 only.

This builder starts from the exact stock runtime used to reproduce the
consumed P3.19 candidate (the ``-55`` output), injects the already-reviewed
P320 kmsg envelope/wiring, and replaces only the reachable
``p303_kmsg_record`` seam.  It reuses the pinned P319 userspace/package
helpers for a private boot-only A/B build.  No device, ADB, Odin, transfer,
authority, or new Carrier/detail ABI is created here.
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
O2_LOADER_CORE = ROOT / "workspace/public/src/native-init/s22plus_o2_loader_core.h"

DEFAULT_OUTPUT_ROOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p320/stock-candidate-build-v1-20260830-01"
SCHEMA = "s22plus-fyg8-p320-stock-candidate-build-v1"
VERDICT = "PASS_P320_STOCK_CANDIDATE_BUILD_H0_ENVELOPE_ONLY"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}

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


P320_RECORD_REPLACEMENT = br'''static long p303_kmsg_record(const char *record, size_t length) {
    if (record == NULL || length == 0U || length > P303_KMSG_RECORD_CAPACITY
        || g_p303_kmsg.drain_record_count >= P319_KMSG_MAX_DRAIN_RECORDS
        || length > (size_t)(P319_KMSG_MAX_DRAIN_BYTES - g_p303_kmsg.drain_bytes)
        || g_p303_kmsg.record_count >= P319_KMSG_MAX_TOTAL_RECORDS
        || length > (size_t)(P319_KMSG_MAX_TOTAL_BYTES - g_p303_kmsg.record_bytes)) {
        return P319_DETAIL_WITNESS_BOUNDARY;
    }
    ++g_p303_kmsg.drain_record_count;
    g_p303_kmsg.drain_bytes += (uint32_t)length;
    ++g_p303_kmsg.record_count;
    g_p303_kmsg.record_bytes += (uint64_t)length;

    struct p320_kmsg_record_view view = {0};
    long envelope_rc = p320_kmsg_record_envelope(record, length, &view);
    if (envelope_rc == P320_KMSG_ENVELOPE_BOUNDARY_ERROR)
        return P319_DETAIL_WITNESS_BOUNDARY;
    if (envelope_rc != 0)
        return P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    if (g_p303_kmsg.sequence_seen
        && (g_p303_kmsg.previous_sequence == UINT64_MAX
            || view.sequence != g_p303_kmsg.previous_sequence + 1U)) {
        return P303_DETAIL_KMSG_SEQUENCE_CONTRADICTION;
    }
    if (!g_p303_kmsg.sequence_seen)
        g_p303_kmsg.first_sequence = view.sequence;
    g_p303_kmsg.sequence_seen = 1U;
    g_p303_kmsg.previous_sequence = view.sequence;

    long rc = p320_kmsg_witness_observe_v2(record, length);
    if (rc == 0)
        rc = p308_kmsg_observe(view.message, view.message_length);
    if (rc != 0)
        return rc;
    if (p282_find_bytes(
            view.message, view.message_length, "msm_hsphy_enable_clocks():") != NULL) {
        g_p303_kmsg.path_seen = 1U;
    }
    if (p282_find_bytes(
            view.message, view.message_length, "phy_reset assert failed") != NULL) {
        g_p303_kmsg.reset_mask |= 1U;
    }
    if (p282_find_bytes(
            view.message, view.message_length, "phy_reset deassert failed") != NULL) {
        g_p303_kmsg.reset_mask |= 2U;
    }
    const char *writeback = p282_find_bytes(
        view.message, view.message_length, "msm_usb_write_readback: write:");
    if (writeback == NULL) return 0;
    const char *offset = p282_find_bytes(
        view.message, view.message_length, "QSCRATCH:");
    const char *failed = p282_find_bytes(
        view.message, view.message_length, "FAILED");
    if (offset == NULL || failed == NULL || offset >= failed)
        return P303_DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION;
    offset += cstr_len("QSCRATCH:");
    while (offset < failed && p282_is_space(*offset)) ++offset;
    const char *offset_end = offset;
    while (offset_end < failed
        && ((*offset_end >= '0' && *offset_end <= '9')
            || (*offset_end >= 'a' && *offset_end <= 'f')
            || (*offset_end >= 'A' && *offset_end <= 'F'))) {
        ++offset_end;
    }
    uint32_t parsed_offset = 0;
    rc = p303_parse_hex(offset, offset_end, &parsed_offset);
    if (rc != 0 || parsed_offset > 0x1f8U || (parsed_offset & 3U) != 0U)
        return P303_DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION;
    if (g_p303_kmsg.readback_count == UINT32_MAX)
        return P303_DETAIL_KMSG_COUNT_OVERFLOW;
    if (g_p303_kmsg.readback_count == 0U)
        g_p303_kmsg.first_offset = parsed_offset;
    ++g_p303_kmsg.readback_count;
    return 0;
}'''


def compose_runtime_transforms(
    runtime: bytes,
    transforms: tuple[Callable[[bytes], bytes], ...] = (),
) -> bytes:
    """Apply optional post-envelope transforms before source compilation.

    The current H0 build supplies no observer-contract transform.  Keeping
    this seam explicit lets a separately reviewed P320 observer transform be
    composed before ``_copy_source_closure`` and the stock compiler without
    changing the envelope-only transform itself.
    """
    current = runtime
    for index, transform in enumerate(transforms):
        current = transform(current)
        if not isinstance(current, bytes):
            raise AuditError(f"P320 runtime transform {index} did not return bytes")
    return current


def transform_runtime(
    original: bytes, envelope_source: str, wiring_source: str,
) -> tuple[bytes, dict[str, Any]]:
    """Inject exact P320 code and replace only the reachable record seam."""
    if not isinstance(envelope_source, str) or not isinstance(wiring_source, str):
        raise AuditError("P320 C sources are not text")
    envelope = envelope_source.encode("ascii")
    wiring = wiring_source.encode("ascii")
    anchor = b"static long p303_kmsg_record("
    old_record = _function_bytes(original, anchor, "P319 p303_kmsg_record")
    if original.count(anchor) != 1 or original.count(b"P320_KMSG_ENVELOPE_MAX_RECORD") != 0:
        raise AuditError("P319 runtime transform anchors differ")
    injected = envelope + b"\n" + wiring + b"\n" + anchor
    transformed = original.replace(anchor, injected, 1)
    if transformed.count(old_record) != 1:
        raise AuditError("P319 p303 record replacement multiplicity differs")
    transformed = transformed.replace(old_record, P320_RECORD_REPLACEMENT, 1)

    # This exact reconstruction proves that no unrelated runtime byte moved.
    expected = original.replace(anchor, injected, 1).replace(old_record, P320_RECORD_REPLACEMENT, 1)
    if transformed != expected:
        raise AuditError("P320 runtime changed outside the declared seam")
    if transformed.count(envelope) != 1 or transformed.count(wiring) != 1:
        raise AuditError("P320 envelope/wiring insertion multiplicity differs")
    if transformed.count(b"p319_witness_observe_v2(view.message, view.message_length)") != 1:
        raise AuditError("P320 human-message parser seam is absent")
    if b"p319_witness_observe_v2(record" in transformed:
        raise AuditError("P320 record bytes reach the witness parser")
    if any(token in transformed for token in (
        b"view.dictionary_lines", b"view.extension_fields", b"view.flag",
    )):
        raise AuditError("P320 envelope metadata reaches the parser seam")
    for forbidden in (
        b"P320_DETAIL_", b"P320_WITNESS_ABI", b"P320_CARRIER_",
    ):
        if forbidden in transformed:
            raise AuditError("P320 transform invents a new detail/Carrier ABI")

    unchanged_functions: dict[str, dict[str, Any]] = {}
    for name in (
        b"static long p308_kmsg_observe(",
        b"static long p303_kmsg_drain(",
        b"static int s22plus_max77705_p318_encode_envelope(",
        b"static uint32_t s22plus_max77705_p319_stock_crc32(",
        b"static int s22plus_max77705_p319_stock_encode(",
        b"static __attribute__((noreturn)) void p319_stock_publish(",
    ):
        before = _function_bytes(original, name, name.decode("ascii"))
        after = _function_bytes(transformed, name, name.decode("ascii"))
        if before != after:
            raise AuditError(f"preserved P319 function changed: {name.decode()}")
        unchanged_functions[name.decode("ascii").removesuffix("(")] = identity(before)
    return transformed, {
        "original": identity(original),
        "transformed": identity(transformed),
        "injected_envelope": identity(envelope),
        "injected_wiring": identity(wiring),
        "record_function_original": identity(old_record),
        "record_function_replacement": identity(P320_RECORD_REPLACEMENT),
        "changed_only_injected_envelope_and_record_seam": True,
        "parser_entry": "p319_witness_observe_v2",
        "human_message_only": True,
        "dictionary_lines_excluded": True,
        "header_extensions_excluded": True,
        "fragment_flag_metadata_excluded": True,
        "fragment_reassembly": False,
        "existing_p319_detail_namespace_reused": True,
        "new_detail_namespace": False,
        "fail_closed_on_envelope_error": True,
        "preserved_p319_functions": unchanged_functions,
        "stock_payload_carrier_decoder_semantics_preserved": True,
    }


def _copy_input(path: Path, destination: Path, expected: dict[str, Any], label: str, maximum: int) -> dict[str, Any]:
    payload = stable_bytes(path, label, maximum, expected)
    _write_exclusive(destination, payload)
    return identity(payload)


def _copy_source_closure(output_root: Path, live_result: dict[str, Any], transformed_runtime: bytes) -> dict[str, dict[str, Any]]:
    source_root = output_root / "stock-sources"
    _mkdir(source_root)
    materialized: dict[str, dict[str, Any]] = {}
    for name, expected in P319_SOURCE_IDENTITIES.items():
        source = P319_SOURCE_ROOT / name
        payload = transformed_runtime if name == RUNTIME_INCLUDE_NAME else stable_bytes(
            source, f"P319 source {name}", 2 * 1024 * 1024, expected, required_mode=0o400, required_nlink=1
        )
        if name == RUNTIME_INCLUDE_NAME and identity(payload) == expected:
            raise AuditError("P320 runtime was not transformed")
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
        "status": "IMPLEMENTED_REVIEW_PENDING",
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
        "phase2": phase2,
        "limitations": [
            "P319 detail 0x6020 namespace collision remains unresolved and blocks live-ready promotion.",
            "This H0 unit does not create approval, D0/D1/F1/recovery/replay authority.",
            "The P320 envelope accepts ABI-valid dictionary/header-extension shapes, but c records are observed independently without fragment reassembly.",
            "No runtime USB, host attach, or physical MUX claim is made by this package.",
        ],
        "preservation": {
            "p319_run_id_unchanged_in_consumed_lineage": P319_RUN_ID.hex(),
            "stock_payload_carrier_decoder_semantics_preserved": True,
            "new_p320_carrier_or_detail_abi": False,
            "exact_rollback_untouched": True,
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
    transformed_runtime, transform = transform_runtime(
        original_runtime, wiring.P320_C_SOURCE, wiring.P320_C_WIRING_SOURCE,
    )
    transformed_runtime = compose_runtime_transforms(transformed_runtime)
    lineage = {
        "p319_result": P319_RESULT_IDENTITY,
        "p319_consumed_ap": P319_AP_IDENTITY,
        "p319_runtime": P319_RUNTIME_IDENTITY,
        "p319_rollback": P319_ROLLBACK_IDENTITY,
        "p319_result_schema": live_result["schema"],
        "p319_candidate_reproductions": 2,
        "runtime_transform": transform,
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
    source_identities = _copy_source_closure(output_root, live_result, transformed_runtime)
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


def _audit_source_output(output_root: Path, result: dict[str, Any], wiring: types.ModuleType) -> None:
    source_root = output_root / "stock-sources"
    names = sorted(path.name for path in source_root.iterdir())
    if names != sorted(P319_SOURCE_IDENTITIES):
        raise AuditError("P320 source output child set differs")
    for name, expected in result["source_closure"].items():
        stable_bytes(source_root / name, f"P320 output source {name}", 2 << 20, expected, required_mode=0o400, required_nlink=1)
    original = stable_bytes(P319_SOURCE_ROOT / RUNTIME_INCLUDE_NAME, "P319 original runtime", 2 << 20, P319_RUNTIME_IDENTITY, required_mode=0o400, required_nlink=1)
    transformed, transform = transform_runtime(original, wiring.P320_C_SOURCE, wiring.P320_C_WIRING_SOURCE)
    output_runtime = stable_bytes(source_root / RUNTIME_INCLUDE_NAME, "P320 transformed runtime", 2 << 20, result["runtime_transform"]["transformed"], required_mode=0o400, required_nlink=1)
    if transformed != output_runtime or transform != result["runtime_transform"]:
        raise AuditError("P320 runtime regeneration differs")


def audit_existing(output_root: Path) -> dict[str, Any]:
    result_payload = stable_bytes(output_root / "result.json", "P320 result", 2 << 20, required_mode=0o400, required_nlink=1)
    result = _strict_json(result_payload, "P320 result")
    if result.get("schema") != SCHEMA or result.get("verdict") != VERDICT:
        raise AuditError("P320 result schema/verdict differs")
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
    _audit_source_output(output_root, result, wiring)
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
