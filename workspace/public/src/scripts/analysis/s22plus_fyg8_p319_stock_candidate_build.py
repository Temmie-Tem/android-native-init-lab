#!/usr/bin/env python3
"""Materialize the P3.19 stock-emitter runtime closure, host-only.

This successor deliberately does not consume the P3.19 driver-source patches.
It binds the exact 73-row plan to the shipped FYG8 module bytes and audits the
fixed Image's kernel ABI and load-order CRC closure.  It then materializes a
diagnostic-free runtime source bundle for the *stock* witness profile.  This
The default Phase-1 unit deliberately does not compile userspace, build a
boot/AP, or invoke a transfer tool; those are optional Phase 2 inputs and
actions.  The stock
witness profile is a distinct payload ABI: it records exactly three
synchronous status bytes, uses the four-stage IRQ -> status -> class -> probe
chain, and cannot claim the two extended bytes or the register-0x23 readback.

No device, ADB, USB, Odin, transfer, recovery, replay, or live authority is
created here.  Compiled/private outputs stay under workspace/private.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import tempfile
import tarfile
import types
from typing import Any
import zlib


ROOT = Path(__file__).resolve().parents[5]
AUDITOR = Path(__file__).resolve()
_BOUND_AUDITOR_SOURCE = globals().get("_P319_STOCK_BOUND_SOURCE")
V5_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "successor-witness-carrier-v5-20260820-13"
)
V5_SOURCES = V5_ROOT / "materialized-sources"
V5_RECEIPT = V5_ROOT / "result.json"
P318_INPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "candidate-witness-transport-20260820-02/inputs"
)
P318_STATIC_RESULT = P318_INPUT_ROOT / "p318-static-check-result.json"
P318_CANDIDATE_PATCH = P318_INPUT_ROOT / "p318-candidate.patch"
P319_MATERIALIZATION_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "successor-module-materialization-v1-20260820-04/result.json"
)
PACKAGER_SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "build_s22plus_fyg8_p318_candidate.py"
)
CHILD_SOURCE = ROOT / "workspace/public/src/native-init/s22plus_r4w1e_e1_child.c"
V5_AUDITOR = ROOT / "workspace/public/src/scripts/analysis/s22plus_fyg8_p319_candidate_witness_carrier_v5.py"
PARSER_AUDITOR = ROOT / "workspace/public/src/scripts/analysis/s22plus_fyg8_p319_candidate_witness_parser_v2.py"
IMAGE = ROOT / "workspace/private/outputs/s22plus_fyg8_p311/fixed-p310-ready-1/Image"
P311_BASE_BOOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p311/candidate-a/boot.img"
KERNEL_MODULE_SOURCE = ROOT / (
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common/kernel/module.c"
)
PINNED_MODULE_SNAPSHOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-06/module-bytes"
)
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-28"
)

SCHEMA = "s22plus-fyg8-p319-stock-witness-runtime-v1"
VERDICT = "PASS_P319_STOCK_WITNESS_RUNTIME_H0"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
RUN_ID = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")
PLAN_NAME = "s22plus_fyg8_p286_e3_plan.h"
RUNTIME_NAME = "s22plus_fyg8_p290_e3_runtime.c"
RUNTIME_INCLUDE_NAME = "s22plus_fyg8_p290_e3_runtime.inc.c"
CHECKPOINT_NAME = "s22plus_fyg8_p290_checkpoint.c"
E1_RUNTIME_NAME = "s22plus_r4w1e_e1_runtime.c"
IMAGE_IDENTITY = {"size": 41_490_944, "sha256": "71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8"}
P311_BASE_BOOT_IDENTITY = {"size": 100_663_296, "sha256": "58b38211d19ead1b0fe54e9fde463aef2c6dbf248be8d669e1b5415f244af17d"}
P318_STATIC_RESULT_IDENTITY = {"size": 554_578, "sha256": "2a4d639b55aa21cf8f52dba505e9bc2d9dfd33f20cd3b217a7c482906aeea4df"}
P318_CANDIDATE_PATCH_IDENTITY = {"size": 42_020, "sha256": "d839850e6e95cea4b199e3bb8217a3112012bf845279d7557d6792aa745662a5"}
P319_MATERIALIZATION_RECEIPT_IDENTITY = {"size": 10_658, "sha256": "8b8c1f5afd8c02693901d3552c221bcc73bafa2543c77dfff4954bdba188f6b5"}
PACKAGER_SOURCE_IDENTITY = {"size": 15_896, "sha256": "dfd6db60d32f1b4dd827e2c3a9ce4fe2b3a06619a2dc12335344200215f99a59"}
TOOL_PATHS = {
    "gcc": Path("/usr/bin/aarch64-linux-gnu-gcc"),
    "modprobe": Path("/usr/sbin/modprobe"),
    "nm": Path("/usr/bin/aarch64-linux-gnu-nm"),
    "readelf": Path("/usr/bin/aarch64-linux-gnu-readelf"),
    "file": Path("/usr/bin/file"),
    "magiskboot": ROOT / "workspace/private/tools/magisk-v30.7/magiskboot",
    "lz4": ROOT / "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/prebuilts/kernel-build-tools/linux-x86/bin/lz4",
}
TOOL_IDENTITIES = {
    "gcc": {"size": 2_137_240, "sha256": "50d0961827e521a7c06d7794d4b15282559a117d365a149aaca5726917ab1603"},
    "modprobe": {"size": 174_472, "sha256": "6edf62330978627d75d8de7e903f243b6ba765f8b54baa914ec83e21cd85bdc7"},
    "nm": {"size": 60_976, "sha256": "29467ca5f9dc5bfdefdb1ef911eda82c5ec99c425c8add4a2ffec3a5c8c4e443"},
    "readelf": {"size": 875_624, "sha256": "b4bb1bf2d6b2d3a309a281a920f0203d68e512e610a4f075cf0ed23e8976b795"},
    "file": {"size": 27_352, "sha256": "4b6e9eb1da3575a8b2ba143b9a84db578b83550791aa198dfb9a3c91cf145b88"},
    "magiskboot": {"size": 943_848, "sha256": "a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e"},
    "lz4": {"size": 218_696, "sha256": "91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8"},
}
_ACTIVE_TOOLS: dict[str, Path] | None = None
COMPILER_ENVIRONMENT_KEYS = (
    "AS", "BFD_PLUGIN", "C_INCLUDE_PATH", "COMPILER_PATH", "CPATH",
    "CPLUS_INCLUDE_PATH", "DEPENDENCIES_OUTPUT", "GCC_COMPARE_DEBUG",
    "GCC_EXEC_PREFIX", "LD", "LDEMULATION", "LD_LIBRARY_PATH",
    "LD_PRELOAD", "LIBRARY_PATH", "OBJC_INCLUDE_PATH", "SUNPRO_DEPENDENCIES",
)
COMPILE_FLAGS = (
    "-nostdlib", "-static", "-ffreestanding", "-fno-builtin",
    "-fno-stack-protector", "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables", "-ffunction-sections", "-fdata-sections", "-Os",
    "-Wall", "-Wextra", "-Werror", "-Wl,--build-id=none",
    "-Wl,--gc-sections", "-Wl,-e,_start", "-Wl,-z,noexecstack",
)
MODULE_SOURCE_IDENTITY = {"size": 129_236, "sha256": "c5f3fccfe692101e37d102567584526210e17c94d6372a998685771cea5effef"}
SAME_MAGIC_BODY_IDENTITY = {"size": 292, "sha256": "217445c73317d49486485b785f64377cc475e02539da52b90277079ceeccccf3"}
SAME_MAGIC_FUNCTION_IDENTITY = {"size": 220, "sha256": "e6bf1e5989a21294656716c6e3bd2df3112693407eea302ae90fdfbbc2f0171f"}
CHECK_MODINFO_FUNCTION_IDENTITY = {"size": 1_200, "sha256": "c6836fd76329f7312a564ef5e733298446dceea486c9e8cc2250b82d49211e00"}
V5_RECEIPT_IDENTITY = {"size": 11_647, "sha256": "05ee3385c8c8001039a329316c65f9bee9d5d3181e8673f7ddf9dea420532917"}
V5_AUDITOR_IDENTITY = {"size": 87_577, "sha256": "a6c0c410f5c5157da4e9b2044dfc9eb710c7f39460f44e41a4deb9034c3bdcc8"}
PARSER_AUDITOR_IDENTITY = {"size": 101_509, "sha256": "7078ef471ffb5a1291d40274201b1f71db93f0465348bb9f1135215d65e659e5"}
PARSER_RECEIPT_IDENTITY = {"size": 15_478, "sha256": "14ca869c411a5940ecffbc24cd2231bc1d10e0bc410ad379d6914809b0debaf0"}
CHILD_SOURCE_IDENTITY = {"size": 1_112, "sha256": "2af86dda0f6c93ee90996d89c9803bd84bab16b909d25b732b69144fe8760e14"}
IKCONFIG_ST = b"IKCFG_ST"
IKCONFIG_ED = b"IKCFG_ED"
IMAGE_EXPECTED_RUN_ID_HEX = RUN_ID.hex()
IMAGE_EXPECTED_UNSAT_TAG_HEX = "ecbfff41d2c5ed22383db45dedfb622d"
IMAGE_SECTION_LAYOUT = {
    "__ksymtab": {
        "image_offset": 35_693_760, "size": 34_212, "entry_size": 12,
        "sha256": "a5ff1f5fb15683862f0dbf8d4132ba43a78250ecc5d51a0d718be2298878be3a",
    },
    "__ksymtab_gpl": {
        "image_offset": 35_727_972, "size": 52_452, "entry_size": 12,
        "sha256": "11de1b664019175d2b43b32211e62f007aab7dad201daefe58a3224021ac8b7d",
    },
    "__kcrctab": {
        "image_offset": 35_780_424, "size": 11_404, "entry_size": 4,
        "sha256": "551a646cdcc3d066b43e01187e448b83c6d712d3067a2e87354cc79cb3688543",
    },
    "__kcrctab_gpl": {
        "image_offset": 35_791_828, "size": 17_484, "entry_size": 4,
        "sha256": "018b0f33ceeee6e438a6c3c6054844c14124833f79acdeabb066e1a7664b1bcb",
    },
    "__ksymtab_strings": {
        "image_offset": 35_809_312, "size": 170_032, "entry_size": 1,
        "sha256": "4c0d4ae1f1a69aaef35b5adcb17e15aace1c68847b7a5a17069f157dbe81e854",
    },
}
STOCK_DOMAIN = b"S22PLUS-FYG8-MAX77705-STOCK-V1\0"
STOCK_ENCODING = 4
STOCK_PAYLOAD_ABI = 3
STOCK_STATUS_WIDTH = 3
STOCK_CHAIN_STAGES = ("irq", "initial_status", "classification", "probe")
MODULE_SOURCE_FILES = (
    PLAN_NAME, RUNTIME_NAME, RUNTIME_INCLUDE_NAME, CHECKPOINT_NAME,
    "s22plus_fyg8_p260_e3_runtime.inc.c", "s22plus_fyg8_p282_classifier.inc.c",
    "s22plus_fyg8_p286_classifier.inc.c", "s22plus_fyg8_p286_trace_descriptor.h",
    "s22plus_fyg8_p288_classifier.inc.c", "s22plus_fyg8_p290_positions.h",
    "s22plus_r4w1e_checkpoint.h", E1_RUNTIME_NAME,
)


class AuditError(RuntimeError):
    """A source, ABI, module, package, or publication invariant differs."""


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def stable_bytes(
    path: Path, label: str, maximum: int,
    expected: dict[str, Any] | None = None,
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
        direct != resolved or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode) or before.st_nlink < 1
        or len(payload) != before.st_size or len(payload) > maximum
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
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open(path, flags, mode)
    try:
        os.fchmod(fd, mode)
        offset = 0
        while offset < len(payload):
            count = os.write(fd, payload[offset:])
            if count <= 0:
                raise AuditError(f"short private publication: {path.name}")
            offset += count
        state = os.fstat(fd)
        if not stat.S_ISREG(state.st_mode) or state.st_nlink != 1 or state.st_size != len(payload):
            raise AuditError(f"private publication identity differs: {path.name}")
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _strict_directory(path: Path, label: str, expected: set[str] | None = None) -> list[str]:
    direct = path.absolute()
    try:
        state = direct.lstat()
        children = list(direct.iterdir())
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if (
        stat.S_ISLNK(state.st_mode) or not stat.S_ISDIR(state.st_mode)
        or stat.S_IMODE(state.st_mode) != 0o700
    ):
        raise AuditError(f"{label} directory identity differs")
    names = [child.name for child in children]
    if len(names) != len(set(names)) or expected is not None and set(names) != expected:
        raise AuditError(f"{label} child set differs")
    return sorted(names)


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def _json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} root differs")
    return value


def _bind_tools() -> dict[str, Path]:
    global _ACTIVE_TOOLS
    bound: dict[str, Path] = {}
    for name, path in TOOL_PATHS.items():
        try:
            state = path.lstat()
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise AuditError(f"bound tool {name} is unavailable") from exc
        if stat.S_ISLNK(state.st_mode):
            stable_bytes(resolved, f"bound tool target {name}", 16 * 1024 * 1024, TOOL_IDENTITIES[name], required_nlink=1)
        else:
            stable_bytes(path, f"bound tool {name}", 16 * 1024 * 1024, TOOL_IDENTITIES[name])
        if not os.access(path, os.X_OK):
            raise AuditError(f"bound tool is not executable: {name}")
        bound[name] = path
    _ACTIVE_TOOLS = bound
    return bound


def _tools() -> dict[str, Path]:
    return _ACTIVE_TOOLS if _ACTIVE_TOOLS is not None else _bind_tools()


def _tool_receipt() -> dict[str, Any]:
    _tools()
    return {
        name: {"logical": f"p319-tool/{name}", **TOOL_IDENTITIES[name]}
        for name in sorted(TOOL_PATHS)
    } | {"reviewed_lineage_source": {"logical": "p319-lineage/build_s22plus_fyg8_p318_candidate.py", **PACKAGER_SOURCE_IDENTITY}}


def _run_bound_capture(name: str, args: list[str | Path], **kwargs: Any) -> subprocess.CompletedProcess[Any]:
    tools = _bind_tools()
    result = subprocess.run([str(tools[name]), *[str(value) for value in args]], **kwargs)
    _bind_tools()
    return result


def _bound_auditor_module() -> types.ModuleType:
    source = stable_bytes(AUDITOR, "stock auditor source", 512 * 1024)
    module = types.ModuleType("p319_stock_bound_auditor")
    module.__file__ = str(AUDITOR)
    module.__package__ = ""
    module.__dict__["_P319_STOCK_BOUND_SOURCE"] = source
    try:
        exec(compile(source.decode("utf-8"), str(AUDITOR), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("bound stock auditor bootstrap failed") from exc
    bound = module.__dict__.get("_BOUND_AUDITOR_SOURCE")
    if type(bound) is not bytes or bound != source:
        raise AuditError("bound stock auditor source identity differs")
    return module


def _load_bound_auditor_source() -> bytes:
    current = stable_bytes(AUDITOR, "stock auditor source", 512 * 1024)
    if type(_BOUND_AUDITOR_SOURCE) is bytes:
        if current != _BOUND_AUDITOR_SOURCE:
            raise AuditError("stock auditor source changed after binding")
        return _BOUND_AUDITOR_SOURCE
    module = _bound_auditor_module()
    source = module.__dict__.get("_BOUND_AUDITOR_SOURCE")
    if type(source) is not bytes:
        raise AuditError("bound stock auditor source is not bytes")
    return source


def _require_bound_authority() -> None:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise AuditError("unbound stock auditor cannot build an authoritative result")


def _v5_materialized_source_identities(
    receipt_payload: bytes, source_root: Path = V5_SOURCES,
) -> dict[str, dict[str, Any]]:
    receipt = _json_object(receipt_payload, "V5 receipt")
    sources = receipt.get("implementation", {}).get("materialized_sources")
    if not isinstance(sources, dict) or set(sources) != set(MODULE_SOURCE_FILES):
        raise AuditError("V5 materialized source set differs")
    identities: dict[str, dict[str, Any]] = {}
    for name in MODULE_SOURCE_FILES:
        expected = sources.get(name)
        if not isinstance(expected, dict) or set(expected) != {"size", "sha256"}:
            raise AuditError(f"V5 source identity shape differs: {name}")
        identities[name] = dict(expected)
        stable_bytes(
            source_root / name, f"V5 materialized source {name}",
            2 * 1024 * 1024, expected, required_mode=0o400,
            required_nlink=1,
        )
    return identities


def _reviewed_module_inputs() -> tuple[bytes, dict[str, Any], dict[str, Any], bytes]:
    static_payload = stable_bytes(
        P318_STATIC_RESULT, "P318 static-check result", 2 * 1024 * 1024,
        P318_STATIC_RESULT_IDENTITY, required_mode=0o400, required_nlink=1,
    )
    patch_payload = stable_bytes(
        P318_CANDIDATE_PATCH, "P318 candidate kernel patch", 128 * 1024,
        P318_CANDIDATE_PATCH_IDENTITY, required_mode=0o400, required_nlink=1,
    )
    materialization_payload = stable_bytes(
        P319_MATERIALIZATION_RECEIPT, "P319 module materialization receipt",
        128 * 1024, P319_MATERIALIZATION_RECEIPT_IDENTITY,
        required_mode=0o400, required_nlink=1,
    )
    static_result = _json_object(static_payload, "P318 static-check result")
    materialization = _json_object(
        materialization_payload, "P319 module materialization receipt",
    )
    if b"CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE=y" not in patch_payload:
        raise AuditError("P318 candidate patch stage gate is absent")
    if b"CONFIG_S22PLUS_FYG8_E1_PROFILE=3" not in patch_payload:
        raise AuditError("P318 candidate patch profile gate is absent")
    if b"S22PLUS_FYG8_E1_RUN_ID_HEX" not in patch_payload:
        raise AuditError("P318 candidate patch run binding is absent")
    for token in (
        b"s22_fyg8_e1_request_allowed",
        b"s22_fyg8_e1_detail_allowed",
        b"S22_FYG8_E1_PROFILE_E2",
    ):
        if token not in patch_payload:
            raise AuditError(f"P318 candidate request gate anchor is absent: {token.decode()}")
    return patch_payload, static_result, materialization, materialization_payload


def _derive_exact_module_rows(
    rows: list[dict[str, Any]], static_result: dict[str, Any],
    materialization: dict[str, Any], latch_payload: bytes,
) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    closure = static_result.get("candidate", {}).get("module_closure", {})
    static_rows = closure.get("modules")
    latch_meta = static_result.get("candidate", {}).get("latch_module")
    added = materialization.get("materialization", {}).get("added_entries")
    added_meta = materialization.get("module_bytes", {}).get("modules")
    if not isinstance(static_rows, list) or len(static_rows) != 69:
        raise AuditError("P318 exact 69-row closure is absent")
    if not isinstance(latch_meta, dict) or not isinstance(added, list) or len(added) != 3:
        raise AuditError("reviewed module delta shape differs")
    if not isinstance(added_meta, dict):
        raise AuditError("reviewed module-byte metadata is absent")
    expected: list[dict[str, Any]] = [{
        "index": 0, "file": "s22plus_dwc3_event_latch.ko",
        "runtime_name": "s22plus_dwc3_event_latch",
        "size": len(latch_payload), "sha256": sha256(latch_payload),
    }]
    if expected[0]["size"] != latch_meta.get("size") or expected[0]["sha256"] != latch_meta.get("sha256"):
        raise AuditError("latch bytes differ from P318 static closure")
    for item in static_rows:
        if not isinstance(item, dict) or set(item) != {"file", "index", "runtime_name", "sha256", "size"}:
            raise AuditError("P318 module row shape differs")
        expected.append({
            "index": int(item["index"]) + 1, "file": item["file"],
            "runtime_name": item["runtime_name"], "size": item["size"],
            "sha256": item["sha256"],
        })
    for item in added:
        if not isinstance(item, dict) or set(item) != {"filename", "index", "params", "runtime_name"}:
            raise AuditError("P319 added module row shape differs")
        if item["params"] != "":
            raise AuditError("P319 added module params differ")
        meta = added_meta.get(item["filename"])
        if not isinstance(meta, dict):
            raise AuditError(f"P319 added module byte metadata absent: {item['filename']}")
        expected.append({
            "index": int(item["index"]), "file": item["filename"],
            "runtime_name": item["runtime_name"], "size": meta.get("size"),
            "sha256": meta.get("sha256"),
        })
    if len(expected) != 73 or [item["index"] for item in expected] != list(range(73)):
        raise AuditError("exact effective module indices differ")
    if len(rows) != 73:
        raise AuditError("current plan row count differs")
    for actual, wanted in zip(rows, expected):
        for key in ("index", "file", "runtime_name"):
            if actual[key] != wanted[key]:
                raise AuditError(f"module plan identity differs at {wanted['index']}: {key}")
    overlay = tuple(["s22plus_dwc3_event_latch.ko"] + [item["filename"] for item in added])
    return expected, overlay


def _load_parser_helpers() -> Any:
    source = stable_bytes(
        PARSER_AUDITOR, "reviewed parser predecessor auditor", 256 * 1024,
        PARSER_AUDITOR_IDENTITY,
    )
    module = types.ModuleType("p319_stock_parser_helpers")
    module.__file__ = str(PARSER_AUDITOR)
    module.__package__ = ""
    module.__dict__["_P319_WITNESS_PARSER_BOUND_SOURCE"] = source
    sys.modules[module.__name__] = module
    try:
        exec(compile(source.decode("utf-8"), str(PARSER_AUDITOR), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("reviewed parser predecessor bound execution failed") from exc
    return module


def _replace_function(source: bytes, helper: Any, name: str, body: bytes) -> bytes:
    old = helper._c_function_body(source, name)
    if source.count(old) != 1:
        raise AuditError(f"stock source function multiplicity differs: {name}")
    return source.replace(old, body, 1)


def _augment_function(source: bytes, helper: Any, name: str, insertion: bytes) -> bytes:
    old = helper._c_function_body(source, name)
    brace = old.find(b"{")
    if brace < 0 or source.count(old) != 1:
        raise AuditError(f"stock source function multiplicity differs: {name}")
    new = old[:brace + 1] + insertion + old[brace + 1:]
    return source.replace(old, new, 1)


STOCK_CHECKPOINT_ALLOWLIST_MACROS = b'''\
#define S22_MAX77705_STOCK_DETAIL_FIRST 0x6724U
#define S22_MAX77705_STOCK_DETAIL_LAST 0x6726U
'''
STOCK_CHECKPOINT_ALLOWLIST_INSERTION = b'''\
    if (position_ordinal == S22_MAX77705_TERMINAL_POSITION
        && outcome == S22_P233_OUTCOME_FAILURE
        && detail >= S22_MAX77705_STOCK_DETAIL_FIRST
        && detail <= S22_MAX77705_STOCK_DETAIL_LAST) {
        return 1;
    }
'''
STOCK_P288_ALLOWLIST_INSERTION = b'''\
    if (ordinal == S22_MAX77705_TERMINAL_POSITION
        && outcome == S22_P233_OUTCOME_FAILURE
        && detail >= S22_MAX77705_STOCK_DETAIL_FIRST
        && detail <= S22_MAX77705_STOCK_DETAIL_LAST) {
        return 1;
    }
'''


def parse_plan(payload: bytes) -> list[dict[str, Any]]:
    rows = []
    pattern = re.compile(rb'^\s+\{"([^"]+\.ko)",\s+"([^"]+)",\s+"([^"\n]*)"\},$', re.MULTILINE)
    for index, match in enumerate(pattern.finditer(payload)):
        rows.append({"index": index, "file": match.group(1).decode(), "runtime_name": match.group(2).decode(), "params": match.group(3).decode()})
    if len(rows) != 73 or len({row["file"] for row in rows}) != 73:
        raise AuditError("exact 73-row plan differs")
    if rows[38] != {"index": 38, "file": "eud.ko", "runtime_name": "eud", "params": ""}:
        raise AuditError("row-38 EUD identity differs")
    if rows[72]["file"] != "pdic_max77705.ko":
        raise AuditError("row-72 stock PDIC identity differs")
    return rows


def _module_paths(name: str, module_root: Path | None = None) -> list[Path]:
    if module_root is not None:
        candidate = module_root / name
        return [candidate] if candidate.is_file() else []
    candidate = PINNED_MODULE_SNAPSHOT / name
    if not candidate.is_file():
        raise AuditError(f"pinned stock module snapshot unavailable: {name}")
    return [candidate]


def _module_payloads(name: str, module_root: Path | None = None) -> tuple[bytes, list[str]]:
    paths = _module_paths(name, module_root)
    if not paths:
        raise AuditError(f"module source unavailable: {name}")
    payloads = [stable_bytes(
        path, f"module {name}", 8 * 1024 * 1024,
        required_mode=0o400 if module_root is not None else None,
        required_nlink=1,
    ) for path in paths]
    if any(value != payloads[0] for value in payloads[1:]):
        raise AuditError(f"vendor_boot/vendor_dlkm module bytes differ: {name}")
    return payloads[0], [str(path) for path in paths]


def _load_exact_module_payloads(
    rows: list[dict[str, Any]], static_result: dict[str, Any],
    materialization: dict[str, Any],
) -> tuple[dict[str, bytes], list[dict[str, Any]], tuple[str, ...]]:
    latch_name = "s22plus_dwc3_event_latch.ko"
    latch_meta = static_result.get("candidate", {}).get("latch_module")
    if not isinstance(latch_meta, dict):
        raise AuditError("reviewed latch metadata is absent")
    latch_expected = {"size": latch_meta.get("size"), "sha256": latch_meta.get("sha256")}
    latch_payload = stable_bytes(
        PINNED_MODULE_SNAPSHOT / latch_name, "private latch snapshot", 8 * 1024 * 1024,
        latch_expected, required_mode=0o400, required_nlink=1,
    )
    expected, overlay = _derive_exact_module_rows(
        rows, static_result, materialization, latch_payload,
    )
    pinned_entries = _strict_directory(
        PINNED_MODULE_SNAPSHOT, "reviewed module snapshot",
        {item["file"] for item in expected},
    )
    payloads: dict[str, bytes] = {}
    for item in expected:
        name = item["file"]
        payload = stable_bytes(
            PINNED_MODULE_SNAPSHOT / name, f"reviewed module {name}",
            8 * 1024 * 1024, {"size": item["size"], "sha256": item["sha256"]},
            required_mode=0o400, required_nlink=1,
        )
        if identity(payload) != {"size": item["size"], "sha256": item["sha256"]}:
            raise AuditError(f"reviewed module bytes differ: {name}")
        payloads[name] = payload
    if set(payloads) != set(pinned_entries):
        raise AuditError("reviewed module snapshot names differ")
    return payloads, expected, overlay


def _norm_crc(value: str) -> str:
    value = value.lower().removeprefix("0x").lstrip("0")
    return value or "0"


def _imports(path: Path) -> dict[str, str]:
    tools = _bind_tools()
    result = subprocess.run([tools["modprobe"], "--dump-modversions", str(path)], text=True, capture_output=True, check=False)
    _bind_tools()
    if result.returncode != 0:
        raise AuditError(f"modprobe --dump-modversions failed: {path.name}")
    values: dict[str, str] = {}
    for raw in result.stdout.splitlines():
        fields = raw.split()
        if len(fields) != 2 or fields[1] in values:
            raise AuditError(f"module import row malformed/duplicated: {path.name}")
        values[fields[1]] = _norm_crc(fields[0])
    if not values:
        raise AuditError(f"module has no __versions imports: {path.name}")
    return values


def _exports(path: Path) -> dict[str, str]:
    tools = _bind_tools()
    result = subprocess.run([tools["nm"], "-g", "--defined-only", str(path)], text=True, capture_output=True, check=False)
    _bind_tools()
    if result.returncode != 0:
        raise AuditError(f"nm export scan failed: {path.name}")
    values: dict[str, str] = {}
    for raw in result.stdout.splitlines():
        fields = raw.split()
        if len(fields) < 3 or not fields[-1].startswith("__crc_"):
            continue
        symbol = fields[-1][6:]
        if symbol in values:
            raise AuditError(f"duplicate module export CRC: {path.name}:{symbol}")
        values[symbol] = _norm_crc(fields[0])
    return values


def _image_provider_map(
    image: bytes, sections: dict[str, dict[str, Any]],
) -> dict[str, str]:
    """Decode the fixed Image's PREL32 export tables.

    The Image is the authority used by the module loader.  PREL32 offsets are
    relative to the field containing each offset, so the common file-to-load
    displacement cancels and the decoded target is an Image file offset.
    """
    strings = sections["__ksymtab_strings"]
    strings_start = int(strings["image_offset"])
    strings_end = strings_start + int(strings["size"])
    providers: dict[str, str] = {}
    if len(image) != IMAGE_IDENTITY["size"]:
        raise AuditError("fixed Image size differs during provider decode")
    if strings.get("entry_size") != 1:
        raise AuditError("Image ksymtab strings entry size differs")
    for table_name, crc_name in (
        ("__ksymtab", "__kcrctab"),
        ("__ksymtab_gpl", "__kcrctab_gpl"),
    ):
        table = sections[table_name]
        crc_table = sections[crc_name]
        if table.get("entry_size") != 12 or crc_table.get("entry_size") != 4:
            raise AuditError(f"Image PREL32 table entry size differs: {table_name}")
        table_start = int(table["image_offset"])
        table_end = table_start + int(table["size"])
        crc_start = int(crc_table["image_offset"])
        crc_end = crc_start + int(crc_table["size"])
        if not (0 <= table_start < table_end <= len(image)) or not (
            0 <= crc_start < crc_end <= len(image)
        ):
            raise AuditError(f"Image export/CRC table escapes Image: {table_name}")
        count = int(table["size"]) // int(table["entry_size"])
        if count != int(crc_table["size"]) // int(crc_table["entry_size"]):
            raise AuditError(f"Image export/CRC table count differs: {table_name}")
        for index in range(count):
            entry = table_start + index * int(table["entry_size"])
            name_delta = struct.unpack_from("<i", image, entry + 4)[0]
            name_offset = entry + 4 + name_delta
            if not strings_start <= name_offset < strings_end:
                raise AuditError(f"Image PREL32 symbol name escapes strings: {table_name}")
            end = image.find(b"\0", name_offset, strings_end)
            if end < 0:
                raise AuditError(f"Image symbol string is unterminated: {table_name}")
            try:
                name = image[name_offset:end].decode("ascii")
            except UnicodeDecodeError as exc:
                raise AuditError(f"Image symbol string is non-ASCII: {table_name}") from exc
            if not name or name in providers:
                raise AuditError(f"Image provider name is empty/duplicated: {name}")
            namespace_delta = struct.unpack_from("<i", image, entry + 8)[0]
            if namespace_delta:
                namespace_offset = entry + 8 + namespace_delta
                if not strings_start <= namespace_offset < strings_end:
                    raise AuditError(
                        f"Image PREL32 namespace escapes strings: {table_name}"
                    )
                namespace_end = image.find(b"\0", namespace_offset, strings_end)
                if namespace_end < 0:
                    raise AuditError(
                        f"Image namespace string is unterminated: {table_name}"
                    )
                try:
                    image[namespace_offset:namespace_end].decode("ascii")
                except UnicodeDecodeError as exc:
                    raise AuditError(
                        f"Image namespace string is non-ASCII: {table_name}"
                    ) from exc
            crc_offset = crc_start + index * int(crc_table["entry_size"])
            crc = _norm_crc(f"{struct.unpack_from('<I', image, crc_offset)[0]:08x}")
            providers[name] = crc
    if len(providers) != 7222:
        raise AuditError("fixed Image provider count differs")
    return providers


def _extract_image_ikconfig(image: bytes) -> dict[str, Any]:
    starts: list[int] = []
    ends: list[int] = []
    cursor = 0
    while True:
        offset = image.find(IKCONFIG_ST, cursor)
        if offset < 0:
            break
        starts.append(offset)
        cursor = offset + 1
    cursor = 0
    while True:
        offset = image.find(IKCONFIG_ED, cursor)
        if offset < 0:
            break
        ends.append(offset)
        cursor = offset + 1
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise AuditError("Image IKCONFIG markers are not unique")
    compressed_start = starts[0] + len(IKCONFIG_ST)
    compressed = image[compressed_start:ends[0]]
    if not compressed or len(compressed) > 2 * 1024 * 1024:
        raise AuditError("Image IKCONFIG compressed payload is out of bounds")
    if not compressed.startswith(b"\x1f\x8b"):
        raise AuditError("Image IKCONFIG compression is not strict gzip")
    decompressor = zlib.decompressobj(16 + 15)
    try:
        config_bytes = decompressor.decompress(compressed, 2 * 1024 * 1024 + 1)
        config_bytes += decompressor.flush()
    except zlib.error as exc:
        raise AuditError("Image IKCONFIG gzip payload is corrupt") from exc
    if (
        not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
        or len(config_bytes) > 2 * 1024 * 1024
        or not config_bytes.endswith(b"\n")
    ):
        raise AuditError("Image IKCONFIG payload has trailing or truncated data")
    try:
        config_text = config_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise AuditError("Image IKCONFIG text is not strict ASCII") from exc
    values: dict[str, str] = {}
    config_line = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
    unset_line = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")
    for line in config_text.splitlines():
        if not line or line.startswith("#") and not unset_line.fullmatch(line):
            continue
        match = config_line.fullmatch(line)
        unset = unset_line.fullmatch(line)
        if match is None and unset is None:
            raise AuditError("Image IKCONFIG line schema differs")
        key = match.group(1) if match is not None else unset.group(1)
        if key in values:
            raise AuditError(f"Image IKCONFIG key is duplicated: {key}")
        values[key] = match.group(2) if match is not None else "unset"
    required = (
        "CONFIG_MODVERSIONS", "CONFIG_MODULE_SIG", "CONFIG_MODULE_FORCE_LOAD",
        "CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE",
        "CONFIG_S22PLUS_FYG8_E1_PROFILE", "CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX",
        "CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX",
    )
    if any(key not in values for key in required):
        raise AuditError("Image IKCONFIG required key is absent")
    if (
        values["CONFIG_MODVERSIONS"] != "y"
        or values["CONFIG_MODULE_SIG"] != "unset"
        or values["CONFIG_MODULE_FORCE_LOAD"] != "unset"
        or values.get("CONFIG_MODULE_REL_CRCS", "unset") != "unset"
        or values["CONFIG_S22PLUS_FYG8_E1_LATEST_STAGE"] != "y"
        or values["CONFIG_S22PLUS_FYG8_E1_PROFILE"] != "3"
    ):
        raise AuditError("Image IKCONFIG module lane differs")
    run_match = re.fullmatch(
        r'"([0-9a-f]{32})"', values["CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX"]
    )
    unsat_match = re.fullmatch(
        r'"([0-9a-f]{32})"', values["CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX"]
    )
    if run_match is None or unsat_match is None:
        raise AuditError("Image IKCONFIG run/UNSAT tags are malformed")
    if run_match.group(1) != IMAGE_EXPECTED_RUN_ID_HEX:
        raise AuditError("Image IKCONFIG run id differs")
    if unsat_match.group(1) != IMAGE_EXPECTED_UNSAT_TAG_HEX:
        raise AuditError("Image IKCONFIG UNSAT tag differs")
    return {
        "start_offset": starts[0], "end_offset": ends[0],
        "compressed": identity(compressed), "decompressed": identity(config_bytes),
        "compression": "gzip", "marker_counts": {"IKCFG_ST": 1, "IKCFG_ED": 1},
        "config_values": {
            key: values.get(key, "unset") for key in (
                *required, "CONFIG_MODULE_REL_CRCS",
            )
        },
        "config_key_presence": {
            key: key in values for key in (
                *required, "CONFIG_MODULE_REL_CRCS",
            )
        },
        "run_id_hex": run_match.group(1), "unsat_tag_hex": unsat_match.group(1),
        "config_bytes": config_bytes,
    }


def _derive_image_vermagic(image: bytes) -> dict[str, Any]:
    marker = b" SMP preempt mod_unload modversions aarch64\0"
    release_pattern = rb"(?<![0-9A-Za-z._+-])([0-9][0-9A-Za-z._+-]+)"
    matches = list(re.finditer(release_pattern + re.escape(marker), image))
    if len(matches) != 1:
        raise AuditError("fixed Image kernel vermagic is not unique")
    match = matches[0]
    release = match.group(1)
    payload = image[match.start(1):match.end() - 1]
    try:
        vermagic = payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise AuditError("fixed Image kernel vermagic is not ASCII") from exc
    suffix = vermagic.split(" ", 1)[1]
    return {
        "offset": match.start(1), "identity": identity(payload),
        "release_token": release.decode("ascii"), "suffix": suffix,
    }


def _c_function_bytes(source: bytes, signature: bytes, label: str) -> bytes:
    start = source.find(signature)
    if start < 0:
        raise AuditError(f"{label} source anchor absent")
    brace = source.find(b"{", start)
    if brace < 0:
        raise AuditError(f"{label} body absent")
    depth = 0
    for index in range(brace, len(source)):
        if source[index:index + 1] == b"{":
            depth += 1
        elif source[index:index + 1] == b"}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AuditError(f"{label} body truncated")


def audit_same_magic_and_image() -> dict[str, Any]:
    """Bind loader semantics and ABI facts to the exact fixed Image only.

    The previous implementation treated a different-run vmlinux, symvers, and
    .config as if they were provenance for this Image. That lane is retired:
    section bytes, IKCONFIG, vermagic, and the provider map all come from the
    pinned Image itself. A separately reconstructed build provenance is not
    implied when no exact Image build bundle is present.
    """
    image = stable_bytes(
        IMAGE, "fixed P3.10 Image", 64 * 1024 * 1024, IMAGE_IDENTITY,
    )
    image_ikconfig = _extract_image_ikconfig(image)
    image_vermagic = _derive_image_vermagic(image)
    module_source = stable_bytes(
        KERNEL_MODULE_SOURCE, "common/kernel/module.c",
        2 * 1024 * 1024, MODULE_SOURCE_IDENTITY,
    )
    start = module_source.find(b"/* First part is kernel version")
    end = module_source.find(b"\n#else", start)
    if start < 0 or end < 0 or end <= start:
        raise AuditError("same_magic source boundary is absent")
    body = module_source[start:end]
    if identity(body) != SAME_MAGIC_BODY_IDENTITY or (
        b"amagic += strcspn(amagic, \" \")" not in body
    ):
        raise AuditError("same_magic source semantics differ")
    same_magic = _c_function_bytes(
        module_source, b"static inline int same_magic(", "same_magic",
    )
    check_modinfo = _c_function_bytes(
        module_source,
        b"static int check_modinfo(struct module *mod, struct load_info *info, int flags)",
        "check_modinfo",
    )
    finit_module = _c_function_bytes(
        module_source, b"SYSCALL_DEFINE3(finit_module", "finit_module",
    )
    if identity(same_magic) != SAME_MAGIC_FUNCTION_IDENTITY or not all(
        token in same_magic for token in (
            b"if (has_crcs)", b"strcspn(amagic, \" \")",
            b"strcmp(amagic, bmagic)",
        )
    ):
        raise AuditError("same_magic loader function differs")
    if identity(check_modinfo) != CHECK_MODINFO_FUNCTION_IDENTITY or not all(
        token in check_modinfo for token in (
            b"MODULE_INIT_IGNORE_VERMAGIC",
            b"same_magic(modmagic, vermagic, info->index.vers)",
        )
    ):
        raise AuditError("check_modinfo loader function differs")
    if b"load_module(&info, uargs, flags)" not in finit_module:
        raise AuditError("finit_module loader flags path differs")

    section_result: dict[str, dict[str, Any]] = {}
    for name, spec in IMAGE_SECTION_LAYOUT.items():
        image_offset = int(spec["image_offset"])
        size = int(spec["size"])
        entry_size = int(spec["entry_size"])
        if (
            image_offset < 0 or size <= 0 or entry_size <= 0
            or size % entry_size != 0 or image_offset + size > len(image)
        ):
            raise AuditError(f"fixed Image section layout differs: {name}")
        target = image[image_offset:image_offset + size]
        if identity(target) != {"size": size, "sha256": spec["sha256"]}:
            raise AuditError(f"fixed Image section bytes differ: {name}")
        section_result[name] = {
            "image_offset": image_offset, "size": size,
            "entry_size": entry_size, "sha256_image": sha256(target),
            "raw_bounds_checked": True,
        }
    image_provider_map = _image_provider_map(image, section_result)
    return {
        "image": identity(image),
        "image_ikconfig": {
            key: value for key, value in image_ikconfig.items()
            if key != "config_bytes"
        },
        "image_vermagic": image_vermagic,
        "same_magic": {
            "source": identity(module_source), "body": identity(body),
            "function": identity(same_magic),
            "has_crcs_ignores_release_prefix": True,
            "derived_image_vermagic_suffix": image_vermagic["suffix"],
            "full_release_token_equality_required": False,
        },
        "check_modinfo": {
            "function": identity(check_modinfo),
            "finit_module": identity(finit_module), "flags_zero_path": True,
        },
        "config": image_ikconfig["config_values"],
        "sections": section_result,
        "image_provider_count": len(image_provider_map),
        "image_provider_map": image_provider_map,
        "provider_authority": (
            "fixed Image raw section offsets, PREL32 names, and parallel CRC "
            "tables; external vmlinux.symvers is not provider authority"
        ),
        "external_build_provenance": {
            "status": "not_bound",
            "reason": (
                "no exact fixed-Image vmlinux/symvers/config bundle was "
                "available; wrong-run inputs are rejected as authority"
            ),
        },
    }


def audit_modules(
    rows: list[dict[str, Any]], image_provider_map: dict[str, str],
    image_vermagic_suffix: str,
    module_root: Path | None = None,
) -> dict[str, Any]:
    if module_root is None:
        raise AuditError("module audit requires a concrete module snapshot root")
    providers: dict[str, list[tuple[str, str]]] = {symbol: [("fixed-image", crc)] for symbol, crc in image_provider_map.items()}
    modules = []
    total_imports = 0
    fixed_image_imports = 0
    earlier_module_imports = 0
    missing_providers = 0
    ambiguous_providers = 0
    duplicate_providers = 0
    source_payloads: dict[str, bytes] = {}
    for row in rows:
        payload, paths = _module_payloads(row["file"], module_root)
        source_payloads[row["file"]] = payload
        match = re.search(rb"vermagic=([^\0]+)", payload)
        if match is None:
            raise AuditError(f"module vermagic absent: {row['file']}")
        vermagic = match.group(1).decode("ascii")
        if vermagic.split(" ", 1)[-1] != image_vermagic_suffix:
            raise AuditError(f"module vermagic suffix differs from Image: {row['file']}")
        module_path = Path(paths[0])
        imports = _imports(module_path)
        exports = _exports(module_path)
        mismatches = []
        for symbol, required in imports.items():
            candidates = providers.get(symbol, [])
            if not candidates:
                missing_providers += 1
                mismatches.append({"symbol": symbol, "required_crc": required, "providers": candidates})
            elif len(candidates) != 1:
                ambiguous_providers += 1
                mismatches.append({"symbol": symbol, "required_crc": required, "providers": candidates})
            elif candidates[0][1] != required:
                mismatches.append({"symbol": symbol, "required_crc": required, "providers": candidates})
            elif candidates[0][0] == "fixed-image":
                fixed_image_imports += 1
            else:
                earlier_module_imports += 1
        if mismatches:
            raise AuditError(f"module load-order CRC closure differs: {row['file']}")
        duplicate_exports = [symbol for symbol in exports if symbol in providers]
        if duplicate_exports:
            duplicate_providers += len(duplicate_exports)
            raise AuditError(f"module export duplicates an earlier provider: {row['file']}")
        for symbol, crc in exports.items():
            providers[symbol] = [(row["file"], crc)]
        total_imports += len(imports)
        logical_paths = [
            f"private-module-snapshot/{row['file']}" if module_root is not None
            else f"vendor-tree/{Path(path).parent.name}/{row['file']}"
            for path in paths
        ]
        modules.append({"index": row["index"], "file": row["file"], "runtime_name": row["runtime_name"], "size": len(payload), "sha256": sha256(payload), "vermagic": vermagic, "source_paths": logical_paths, "import_count": len(imports), "export_count": len(exports)})
    if (total_imports, fixed_image_imports, earlier_module_imports) != (3566, 3238, 328):
        raise AuditError("load-order CRC resolution counts differ")
    return {
        "module_count": len(modules), "modules": modules,
        "total_imports": total_imports,
        "provider_resolution": {
            "fixed_image_imports": fixed_image_imports,
            "earlier_module_imports": earlier_module_imports,
            "total_resolved_imports": fixed_image_imports + earlier_module_imports,
        },
        "duplicate_provider_count": duplicate_providers,
        "ambiguous_provider_count": ambiguous_providers,
        "missing_provider_count": missing_providers,
        "ordered_crc_closed": True,
        "image_derived_vermagic_suffix": image_vermagic_suffix,
        "source_payloads": source_payloads,
    }


STOCK_INITIAL = b'''p319_observe_initial(const char *message, size_t length) {
    const char *prefix = "pdic_max77705: max77705_muic_detect_dev ";
    if (!p319_has(message, length, prefix)) return 0;
    const char *cursor = message + cstr_len(prefix);
    const char *end = message + length;
    const char *labels[S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH] = {
        "USBC1:0x", ", USBC2:0x", ", BC:0x"};
    uint32_t values[S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH] = {0};
    for (unsigned int i = 0; i < S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH; ++i) {
        long rc = p319_take_literal(&cursor, end, labels[i]);
        if (rc != 0) return rc;
        rc = p319_take_hex(&cursor, end, 1, &values[i]);
        if (rc != 0) return rc;
    }
    if (cursor != end) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    if (p319_primary_witness_frozen()) return 0;
    for (unsigned int i = 0; i < S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH; ++i)
        g_p319_witness.initial_status[i] = values[i];
    long rc = p319_count(&g_p319_witness.initial_status_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_INITIAL;
    if (rc == 0) p319_chain_event(2U);
    return rc;
}
'''
STOCK_PARENT = b'''p319_observe_parent_mask(const char *message, size_t length) {
    const char *prefix = "max77705: max77705_usbc_umask_irq: ";
    if (!p319_has(message, length, prefix)) return 0;
    return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
}
'''
STOCK_OBSERVE = b'''p319_witness_observe_v2(const char *message, size_t length) {
    if (message == NULL) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    /* The stock profile is four-stage.  Form-2 classification and the
     * deferred seven-register line are valid auxiliary observations; only
     * parent/W5 and a five-byte initial claim are outside this domain. */
    if (p319_has(message, length, "max77705: max77705_usbc_umask_irq "))
        return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    long rc = p319_observe_irq(message, length);
    if (rc == 0) rc = p319_observe_initial(message, length);
    if (rc == 0) rc = p319_observe_class1(message, length);
    if (rc == 0) rc = p319_observe_probe(message, length);
    if (rc == 0) rc = p319_observe_class2(message, length);
    if (rc == 0) rc = p319_observe_deferred(message, length);
    if (rc != 0 && g_p319_witness.malformed_count != UINT32_MAX)
        ++g_p319_witness.malformed_count;
    return rc;
}
'''
STOCK_CHAIN = b'''p319_chain_event(unsigned int event) {
    if (!g_p319_witness.active_module_valid) {
        if (g_p319_witness.initial_chain_stage != 0U)
            g_p319_witness.initial_chain_ambiguous = 1U;
        return;
    }
    if (g_p319_witness.active_module_index != 72U) {
        g_p319_witness.initial_chain_ambiguous = 1U;
        return;
    }
    if (event == 1U && g_p319_witness.initial_chain_stage == 0U)
        g_p319_witness.initial_chain_stage = 1U;
    else if (event == 2U && g_p319_witness.initial_chain_stage == 1U)
        g_p319_witness.initial_chain_stage = 2U;
    else if (event == 3U && g_p319_witness.initial_chain_stage == 2U)
        g_p319_witness.initial_chain_stage = 3U;
    else if (event == 5U && g_p319_witness.initial_chain_stage == 3U) {
        g_p319_witness.initial_chain_stage = 4U;
        g_p319_witness.initial_chain_complete = 1U;
        g_p319_witness.initial_chain_module_index = 72U;
    } else
        g_p319_witness.initial_chain_ambiguous = 1U;
}
'''

STOCK_ENCODER_SOURCE = br'''/* P3.19 stock-emitter envelope: no diagnostic binding/result ABI. */
#define S22PLUS_MAX77705_P319_STOCK_DETAIL_COMPLETE 0x6724U
#define S22PLUS_MAX77705_P319_STOCK_DETAIL_INCOMPLETE 0x6725U
#define S22PLUS_MAX77705_P319_STOCK_DETAIL_AMBIGUOUS 0x6726U
#define S22PLUS_MAX77705_P319_STOCK_PARENT_UNAVAILABLE 1U
#define S22PLUS_MAX77705_P319_STOCK_W5_UNAVAILABLE 1U

static uint32_t s22plus_max77705_p319_stock_crc32(
        const uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE])
{
    static const uint8_t domain[] =
        "S22PLUS-FYG8-MAX77705-STOCK-V1\0";
    uint32_t crc = ~0U;

    crc = s22plus_max77705_envelope_crc_update(
        crc, domain, sizeof(domain) - 1U);
    crc = s22plus_max77705_envelope_crc_update(
        crc, envelope, S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET);
    return crc ^ ~0U;
}

static int s22plus_max77705_p319_stock_module_exact(
        const struct p319_module_result_state_v1 *module,
        uint32_t index, const char *name)
{
    size_t length = cstr_len(name);
    return module != NULL && module->valid == 1U && module->index == index &&
        module->name_length == length &&
        p260_bytes_equal(module->name, name, length);
}

static void p319_stock_bypass_to_pair(void) {
    if (g_checkpoint.terminal || g_checkpoint.generation > 105U)
        p290_fail_next(P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION);
    while (g_checkpoint.generation < 105U)
        p290_progress_position((uint8_t)g_checkpoint.generation, 0U);
}

static int s22plus_max77705_p319_stock_encode(
        const struct p319_witness_summary_state_v2 *witness,
        uint8_t terminal_state,
        uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE],
        uint16_t *terminal_detail)
{
    uint8_t *payload;
    uint8_t expected_mask = 0U;
    uint8_t validity = 0U;
    uint32_t crc;

    if (witness == NULL || envelope == NULL || terminal_detail == NULL ||
        witness->abi_version != P319_WITNESS_ABI_VERSION ||
        witness->module_loads != P319_KMSG_MAX_MODULES ||
        witness->module_drains != P319_KMSG_MAX_MODULES ||
        witness->malformed_count != 0U ||
        witness->initial_chain_stage > 4U ||
        witness->initial_chain_complete > 1U ||
        witness->initial_chain_ambiguous > 1U ||
        witness->active_module_valid != 0U ||
        witness->parent_mask_count != 0U ||
        witness->parent_mask_readback != 0U ||
        witness->initial_status_count > UINT8_MAX ||
        witness->probe_count > UINT8_MAX ||
        witness->irq_count > UINT8_MAX ||
        witness->classification_form1_count > UINT8_MAX ||
        witness->classification_form2_count > UINT8_MAX ||
        witness->deferred_status_count > UINT8_MAX ||
        witness->record_count > UINT16_MAX ||
        witness->record_bytes > 0xFFFFFFU ||
        terminal_state > 2U ||
        !s22plus_max77705_p319_stock_module_exact(
            &witness->target_modules[0], 69U, "i2c-msm-geni.ko") ||
        !s22plus_max77705_p319_stock_module_exact(
            &witness->target_modules[1], 71U, "mfd_max77705.ko") ||
        !s22plus_max77705_p319_stock_module_exact(
            &witness->target_modules[2], 72U, "pdic_max77705.ko"))
        return -1;
    if (witness->initial_chain_complete != 0U &&
        witness->initial_chain_stage != 4U)
        return -1;
    if (witness->initial_chain_complete == 0U &&
        witness->initial_chain_module_index != 0U)
        return -1;
    if (witness->initial_chain_complete != 0U &&
        witness->initial_chain_module_index != 72U)
        return -1;
    if ((witness->initial_chain_stage >= 1U && witness->irq_count == 0U) ||
        (witness->initial_chain_stage >= 2U &&
            witness->initial_status_count == 0U) ||
        (witness->initial_chain_stage >= 3U &&
            witness->classification_form1_count == 0U) ||
        (witness->initial_chain_stage >= 4U && witness->probe_count == 0U))
        return -1;
    if (witness->initial_status_count == 0U) {
        for (unsigned int index = 0U;
             index < S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH; ++index)
            if (witness->initial_status[index] != 0U) return -1;
    }
    for (unsigned int index = 0U;
         index < S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH; ++index)
        if (witness->initial_status[index] > UINT8_MAX) return -1;
    for (unsigned int index = 3U; index < 5U; ++index)
        if (witness->initial_status[index] != 0U) return -1;
    if (witness->witness_mask & P319_WITNESS_MASK_PARENT)
        return -1;
    if (witness->probe_count != 0U) expected_mask |= P319_WITNESS_MASK_PROBE;
    if (witness->irq_count != 0U) expected_mask |= P319_WITNESS_MASK_IRQ;
    if (witness->initial_status_count != 0U)
        expected_mask |= P319_WITNESS_MASK_INITIAL;
    if (witness->classification_form1_count != 0U)
        expected_mask |= P319_WITNESS_MASK_CLASS1;
    if (witness->classification_form2_count != 0U)
        expected_mask |= P319_WITNESS_MASK_CLASS2;
    if (witness->deferred_status_count != 0U)
        expected_mask |= P319_WITNESS_MASK_DEFERRED;
    if (witness->witness_mask != expected_mask) return -1;
    if ((terminal_state == 0U) !=
        (witness->initial_chain_complete != 0U)) return -1;
    if (terminal_state == 2U && witness->initial_chain_ambiguous == 0U)
        return -1;

    memset(envelope, 0, S22PLUS_MAX77705_ENVELOPE_SIZE);
    envelope[0] = 'M'; envelope[1] = 'X'; envelope[2] = 'D';
    envelope[3] = '5'; envelope[4] = 5U;
    envelope[7] = S22PLUS_MAX77705_P319_WITNESS_FLAG;
    envelope[43] = S22PLUS_MAX77705_P319_STOCK_ENCODING;
    envelope[46] = S22PLUS_MAX77705_P319_PAYLOAD_USED;
    payload = envelope + S22PLUS_MAX77705_ENVELOPE_PAYLOAD_OFFSET;
    payload[0] = S22PLUS_MAX77705_P319_STOCK_PAYLOAD_ABI;
    payload[1] = witness->witness_mask;
    validity = S22PLUS_MAX77705_P319_VALID_MODULE69 |
        S22PLUS_MAX77705_P319_VALID_MODULE71 |
        S22PLUS_MAX77705_P319_VALID_MODULE72;
    if (witness->initial_status_count != 0U)
        validity |= S22PLUS_MAX77705_P319_VALID_INITIAL;
    if (witness->classification_form1_count != 0U)
        validity |= S22PLUS_MAX77705_P319_VALID_CLASS1;
    payload[2] = validity;
    payload[3] = (uint8_t)(witness->initial_chain_stage |
        (witness->initial_chain_complete << 3U) |
        (witness->initial_chain_ambiguous << 4U) |
        (1U << 5U));
    for (unsigned int index = 0U; index < 3U; ++index)
        s22plus_max77705_store_le16(
            payload + 4U + index * 2U,
            (uint16_t)(int16_t)witness->target_modules[index].result);
    payload[10] = (uint8_t)witness->probe_count;
    payload[11] = (uint8_t)witness->irq_count;
    payload[12] = (uint8_t)witness->initial_status_count;
    payload[13] = (uint8_t)witness->classification_form1_count;
    for (unsigned int index = 0U;
         index < S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH; ++index)
        payload[14U + index] = (uint8_t)witness->initial_status[index];
    for (unsigned int index = 0U; index < 5U; ++index)
        s22plus_max77705_store_le16(
            payload + 17U + index * 2U,
            (uint16_t)witness->irq[index]);
    s22plus_max77705_p319_store_le64(
        payload + 27U, witness->classification_form1_index);
        s22plus_max77705_store_le16(payload + 35U,
        (uint16_t)witness->record_count);
    s22plus_max77705_p319_store_le24(payload + 37U,
        (uint32_t)witness->record_bytes);
    s22plus_max77705_p319_store_le64(payload + 40U,
        witness->first_sequence);
    s22plus_max77705_p319_store_le64(payload + 48U,
        witness->last_sequence);
    payload[56] = S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH;
    payload[57] = S22PLUS_MAX77705_P319_STOCK_PARENT_UNAVAILABLE;
    payload[58] = S22PLUS_MAX77705_P319_STOCK_W5_UNAVAILABLE;
    payload[59] = (uint8_t)witness->classification_form2_count;
    payload[60] = (uint8_t)witness->deferred_status_count;
    if (terminal_state == 0U) {
        *terminal_detail = S22PLUS_MAX77705_P319_STOCK_DETAIL_COMPLETE;
    } else if (terminal_state == 1U) {
        *terminal_detail = S22PLUS_MAX77705_P319_STOCK_DETAIL_INCOMPLETE;
    } else {
        *terminal_detail = S22PLUS_MAX77705_P319_STOCK_DETAIL_AMBIGUOUS;
    }
    crc = s22plus_max77705_p319_stock_crc32(envelope);
    s22plus_max77705_store_le32(
        envelope + S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET, crc);
    return 0;
}

static __attribute__((noreturn)) void p319_stock_publish(int tty_fd) {
    struct p319_witness_summary_state_v2 witness = {0};
    uint8_t envelope[S22PLUS_MAX77705_ENVELOPE_SIZE];
    uint16_t detail = 0U;
    uint8_t terminal_state;
    long publish_rc;

    (void)tty_fd;
    if (p319_witness_summary_state_v2_copy(&witness) != 0)
        p290_fail_next(S22PLUS_MAX77705_P319_STOCK_DETAIL_AMBIGUOUS);
    terminal_state = witness.initial_chain_ambiguous != 0U ? 2U
        : (witness.initial_chain_complete != 0U ? 0U : 1U);
    if (s22plus_max77705_p319_stock_encode(
            &witness, terminal_state, envelope, &detail) != 0)
        p290_fail_next(S22PLUS_MAX77705_P319_STOCK_DETAIL_AMBIGUOUS);
    p319_stock_bypass_to_pair();
    publish_rc = s22_max77705_checkpoint_payload_progress_position(
        &g_checkpoint, 105U, S22PLUS_MAX77705_A_DETAIL, envelope);
    if (publish_rc == 0)
        publish_rc = s22_max77705_checkpoint_payload_terminal_position(
            &g_checkpoint, 106U, detail, envelope + 64U);
    if (publish_rc != 0) p292_park_after_checkpoint_error(publish_rc);
    p290_park_after_confirmed_publication();
}
'''

STOCK_DEAD_PUBLISH = b'''p317_publish(
    int tty_fd, const struct p316_diag_observation *input) {
    (void)tty_fd;
    (void)input;
    p290_fail_next(S22PLUS_MAX77705_P319_STOCK_DETAIL_AMBIGUOUS);
}
'''


def materialize_stock_sources(output: Path) -> dict[str, bytes]:
    helper = _load_parser_helpers()
    v5_receipt = stable_bytes(
        V5_RECEIPT, "historical V5 receipt", 64 * 1024,
        V5_RECEIPT_IDENTITY, required_mode=0o400, required_nlink=1,
    )
    v5_source_identities = _v5_materialized_source_identities(v5_receipt)
    originals = {
        name: stable_bytes(
            V5_SOURCES / name, f"V5 source {name}", 2 * 1024 * 1024,
            v5_source_identities[name],
            required_mode=0o400, required_nlink=1,
        ) for name in MODULE_SOURCE_FILES
    }
    checkpoint = originals[CHECKPOINT_NAME]
    checkpoint_anchor = b"#define S22_MAX77705_FIRST_DETAIL 0xda3U\n"
    if checkpoint.count(checkpoint_anchor) != 1:
        raise AuditError("checkpoint allowlist anchor differs")
    checkpoint = checkpoint.replace(
        checkpoint_anchor, STOCK_CHECKPOINT_ALLOWLIST_MACROS + checkpoint_anchor, 1,
    )
    checkpoint = _augment_function(
        checkpoint, helper, "p288_detail_allowed", STOCK_P288_ALLOWLIST_INSERTION,
    )
    checkpoint = _augment_function(
        checkpoint, helper, "s22_max77705_detail_allowed",
        STOCK_CHECKPOINT_ALLOWLIST_INSERTION,
    )
    runtime = _replace_function(originals[RUNTIME_INCLUDE_NAME], helper, "p319_observe_initial", STOCK_INITIAL)
    runtime = _replace_function(runtime, helper, "p319_observe_parent_mask", STOCK_PARENT)
    runtime = _replace_function(
        runtime, helper, "p319_observe_class2",
        helper._c_function_body(originals[RUNTIME_INCLUDE_NAME], "p319_observe_class2"),
    )
    runtime = _replace_function(
        runtime, helper, "p319_observe_deferred",
        helper._c_function_body(originals[RUNTIME_INCLUDE_NAME], "p319_observe_deferred"),
    )
    runtime = _replace_function(runtime, helper, "p319_witness_observe_v2", STOCK_OBSERVE)
    runtime = _replace_function(runtime, helper, "p319_chain_event", STOCK_CHAIN)
    runtime = _replace_function(runtime, helper, "p317_publish", STOCK_DEAD_PUBLISH)
    substitutions = (
        (b"#define P319_WITNESS_ABI_VERSION 2U", b"#define S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH 3U\n#define P319_WITNESS_ABI_VERSION 2U"),
        (b"#define S22PLUS_MAX77705_P319_PAYLOAD_ABI 2U", b"#define S22PLUS_MAX77705_P319_PAYLOAD_ABI 3U\n#define S22PLUS_MAX77705_P319_STOCK_PAYLOAD_ABI 3U\n#define S22PLUS_MAX77705_P319_STOCK_ENCODING 4U\n#define S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH 3U"),
        (b"#define S22PLUS_MAX77705_P319_WITNESS_ENCODING 3U", b"#define S22PLUS_MAX77705_P319_WITNESS_ENCODING 4U"),
        (b"witness->initial_chain_stage > 5U ||", b"witness->initial_chain_stage > 4U ||\n        witness->parent_mask_count != 0U ||\n        witness->parent_mask_readback != 0U ||\n        witness->initial_status[3] != 0U ||\n        witness->initial_status[4] != 0U ||"),
        (b"(witness->initial_chain_complete != 0U) !=\n            (witness->initial_chain_stage == 5U)", b"(witness->initial_chain_complete != 0U) !=\n            (witness->initial_chain_stage == 4U)"),
        (b"(witness->initial_chain_stage >= 4U &&\n            witness->parent_mask_count == 0U) ||\n        (witness->initial_chain_stage >= 5U && witness->probe_count == 0U)", b"(witness->initial_chain_stage >= 4U &&\n            witness->probe_count == 0U)"),
        (b"payload[3] = (uint8_t)(witness->initial_chain_stage |\n        (witness->initial_chain_complete << 3U) |\n        (witness->initial_chain_ambiguous << 4U));", b"payload[3] = (uint8_t)(witness->initial_chain_stage |\n        (witness->initial_chain_complete << 3U) |\n        (witness->initial_chain_ambiguous << 4U) | (1U << 5U));"),
    )
    for old, new in substitutions:
        if runtime.count(old) != 1:
            raise AuditError("stock ABI source transform anchor differs")
        runtime = runtime.replace(old, new, 1)
    encoder_anchor = b"/* P3.17 boot-specific executability witness. */"
    if runtime.count(encoder_anchor) != 1:
        raise AuditError("stock encoder insertion anchor differs")
    runtime = runtime.replace(encoder_anchor, STOCK_ENCODER_SOURCE + b"\n" + encoder_anchor, 1)
    wrapper = originals[RUNTIME_NAME]
    override = b'''    long p316_override_rc = p316_prepare_overrides();
    if (p316_override_rc != 0) {
        p317_fail_observer(
            -1, S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE,
            p316_override_rc, NULL);
    }

'''
    if wrapper.count(override) != 1:
        raise AuditError("stock override removal anchor differs")
    wrapper = wrapper.replace(override, b"", 1)
    p318_original = helper._c_function_body(runtime, "p318_run")
    cut = b"    rc = p317_capture_policy();"
    if p318_original.count(cut) != 1:
        raise AuditError("p318 diagnostic-tail cut anchor differs")
    prefix = p318_original[:p318_original.index(cut)]
    prefix = prefix.replace(
        b"    (void)p316_run;\n", b"", 1)
    gate_failure = b'''    if (rc != 0) p317_fail_observer(
        tty_fd, S22PLUS_MAX77705_P318_OBSERVER_SITE_EXPOSURE_GATE,
        rc, NULL);
'''
    if prefix.count(gate_failure) != 1:
        raise AuditError("stock latch failure anchor differs")
    prefix = prefix.replace(gate_failure, b"    if (rc != 0) p290_fail_next(rc);\n", 1)
    policy_line = b"    g_p317_exec.policy |= S22PLUS_MAX77705_P317_POLICY_GADGET_READY;\n"
    if prefix.count(policy_line) != 1:
        raise AuditError("stock P317 policy anchor differs")
    prefix = prefix.replace(policy_line, b"", 1)
    p318_body = prefix + b"    p319_stock_publish(tty_fd);\n}\n"
    runtime = runtime.replace(p318_original, p318_body, 1)
    for name in (
        b"p319_observe_parent_mask", b"p319_observe_class2",
        b"p319_observe_deferred", b"p316_prepare_overrides",
        b"p316_run", b"p317_capture_policy", b"p317_capture_waiting",
        b"p317_capture_supplier", b"p317_capture_post_provider",
    ):
        prefix_token = b"static long " + name + b"("
        replacement = b"static __attribute__((unused)) long " + name + b"("
        if prefix_token in runtime:
            runtime = runtime.replace(prefix_token, replacement, 1)
        else:
            noreturn_token = b"static __attribute__((noreturn)) void " + name + b"("
            if noreturn_token in runtime:
                runtime = runtime.replace(
                    noreturn_token,
                    b"static __attribute__((unused,noreturn)) void " + name + b"(",
                    1,
                )
    if any(token in p318_body for token in (
        b"p316_", b"p317_", b"p241_finit_module", b"P316_DIAG",
        b"i2c", b"I2C")):
        raise AuditError("stock reachable p318 prefix retains diagnostic/provider path")
    if b"p319_stock_publish(tty_fd);" not in p318_body:
        raise AuditError("stock publisher is not reachable from p318")
    for old, new in (
        (
            b"static long p318_capture_terminal_latch(",
            b"static __attribute__((unused)) long p318_capture_terminal_latch(",
        ),
        (
            b"static struct s22plus_p318_banner_result p318_terminal_banner(",
            b"static __attribute__((unused)) struct s22plus_p318_banner_result p318_terminal_banner(",
        ),
        (
            b"static int s22plus_max77705_p319_encode_envelope_v5(",
            b"static __attribute__((unused)) int s22plus_max77705_p319_encode_envelope_v5(",
        ),
    ):
        if runtime.count(old) != 1:
            raise AuditError("stock dead diagnostic helper anchor differs")
        runtime = runtime.replace(old, new, 1)
    result = dict(originals)
    result[CHECKPOINT_NAME] = checkpoint
    result[RUNTIME_INCLUDE_NAME] = runtime
    result[RUNTIME_NAME] = wrapper
    output.mkdir(mode=0o700)
    output.chmod(0o700)
    for name, payload in result.items():
        _write_exclusive(output / name, payload)
    _fsync_directory(output)
    return result


def _compile_userspace(source_dir: Path, output: Path, *, label: str) -> dict[str, Any]:
    tools = _tools()
    child_source = source_dir.parent / "inputs/child-source.c"
    stable_bytes(child_source, "preserved child source", 64 * 1024, CHILD_SOURCE_IDENTITY, required_mode=0o400, required_nlink=1)
    with tempfile.TemporaryDirectory(prefix=f"p319-stock-userspace-{label}-") as name:
        work = Path(name)
        init = work / "init"
        child = work / "s22-e1-child"
        define = "{" + ",".join(f"0x{value:02x}" for value in RUN_ID) + "}"
        environment = os.environ.copy()
        for key in COMPILER_ENVIRONMENT_KEYS:
            environment.pop(key, None)
        environment.update({"LANG": "C", "LC_ALL": "C", "SOURCE_DATE_EPOCH": "0"})
        common = [tools["gcc"], *COMPILE_FLAGS, "-DS22PLUS_FYG8_P233_PROFILE=3", f"-DS22PLUS_FYG8_P233_RUN_ID_BYTES={define}", "-I", str(source_dir), "-I", str(ROOT / "workspace/public/src/native-init")]
        for command, target, title in ((common + [source_dir / RUNTIME_NAME, source_dir / CHECKPOINT_NAME, "-o", init], init, "stock init"), ([tools["gcc"], *COMPILE_FLAGS, child_source, "-o", child], child, "stock child")):
            completed = subprocess.run(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=180)
            if completed.returncode != 0:
                detail = (completed.stdout + completed.stderr).decode("utf-8", "replace")
                raise AuditError(f"{title} compile failed: {detail[-4000:]}")
            _bind_tools()
        init_bytes, child_bytes = init.read_bytes(), child.read_bytes()
        file_text = _run_bound_capture("file", ["-b", init], text=True, capture_output=True, check=True).stdout
        readelf = _run_bound_capture("readelf", ["-W", "-h", "-l", init], text=True, capture_output=True, check=True).stdout
        undefined = _run_bound_capture("nm", ["-u", init], text=True, capture_output=True, check=True).stdout
        if "ELF 64-bit LSB executable, ARM aarch64" not in file_text or "statically linked" not in file_text or "INTERP" in readelf or "DYNAMIC" in readelf or undefined.strip():
            raise AuditError("stock init static ELF contract differs")
        module_names = [row["file"] for row in parse_plan((source_dir / PLAN_NAME).read_bytes())]
        counts = {name: init_bytes.count(name.encode("ascii")) for name in module_names}
        if any(value != 1 for value in counts.values()) or init_bytes.count(RUN_ID) != 1 or b"P319_INTSRC_MASK" in init_bytes or b"CC0:0x%02x" in init_bytes:
            raise AuditError("stock init producer/profile identity differs")
        output.mkdir(mode=0o700, parents=True)
        output.chmod(0o700)
        _write_exclusive(output / "init", init_bytes)
        _write_exclusive(output / "s22-e1-child", child_bytes)
        _fsync_directory(output)
        return {"init": identity(init_bytes), "child": identity(child_bytes), "module_string_counts": counts, "static_aarch64": True, "enhanced_witness_claimable": False, "artifacts": {"init": "init", "child": "s22-e1-child"}}


def _run_tool(command: list[Path | str], cwd: Path, label: str) -> None:
    _bind_tools()
    result = subprocess.run([str(value) for value in command], cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=180)
    if result.returncode != 0:
        raise AuditError(f"{label} failed: {(result.stdout + result.stderr).decode('utf-8', 'replace')[-4000:]}")
    _bind_tools()


def _cpio_entries(tool: Path, ramdisk: Path, cwd: Path, label: str) -> list[str]:
    result = subprocess.run(
        [str(tool), "cpio", str(ramdisk), "ls -r"], cwd=cwd,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=30,
    )
    if result.returncode != 0:
        raise AuditError(f"{label} cpio listing failed")
    entries = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        fields = line.split("\t")
        if len(fields) >= 6 and fields[-1]:
            entries.append(fields[-1])
    if len(entries) != len(set(entries)):
        raise AuditError(f"{label} cpio listing is not unique")
    return entries


def _write_deterministic_boot_ap(frame: bytes, output: Path) -> dict[str, Any]:
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with output.open("xb") as handle:
        with tarfile.open(fileobj=handle, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            info = tarfile.TarInfo("boot.img.lz4")
            info.size = len(frame)
            info.mode = 0o644
            info.uid = 0
            info.gid = 0
            info.mtime = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(frame))
    prefix = output.read_bytes()
    digest = hashlib.md5(prefix).hexdigest()
    with output.open("ab") as handle:
        handle.write(f"{digest}  AP.tar\n".encode("ascii"))
    return {
        "tar_prefix_size": len(prefix), "tar_md5": digest,
        "trailer": f"{digest}  AP.tar\\n", "members": ["boot.img.lz4"],
    }


def _package_candidate(
    base_boot: bytes, init_bytes: bytes, child_bytes: bytes,
    module_payloads: dict[str, bytes],
    overlay_names: tuple[str, ...], output: Path, label: str,
) -> dict[str, Any]:
    magiskboot = _tools()["magiskboot"]
    lz4 = _tools()["lz4"]
    magiskboot_bytes = stable_bytes(magiskboot, "magiskboot", 4 * 1024 * 1024)
    lz4_bytes = stable_bytes(lz4, "lz4", 4 * 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix=f"p319-stock-package-{label}-") as name:
        work = Path(name); unpack = work / "unpack"; final = work / "final"; audit = work / "audit"
        unpack.mkdir(); final.mkdir(); audit.mkdir()
        base_path = work / "base.boot.img"; base_path.write_bytes(base_boot)
        init_path = work / "init"; init_path.write_bytes(init_bytes)
        tool_magisk = audit / "magiskboot"; tool_magisk.write_bytes(magiskboot_bytes); tool_magisk.chmod(0o700)
        tool_lz4 = audit / "lz4"; tool_lz4.write_bytes(lz4_bytes); tool_lz4.chmod(0o700)
        _run_tool([tool_magisk, "unpack", "-h", base_path], unpack, "P311 base unpack")
        ramdisk = unpack / "ramdisk.cpio"
        base_entries = _cpio_entries(tool_magisk, ramdisk, unpack, "P311 base")
        base_module_entries = sorted(
            entry for entry in base_entries if entry.startswith("lib/modules/")
        )
        if base_module_entries:
            raise AuditError("P311 clean base unexpectedly contains generic modules")
        if "s22-e1-child" not in base_entries:
            raise AuditError("P311 clean base child is absent")
        for member in (
            "lib/modules/s22plus_dwc3_event_latch.ko",
            "lib/modules/s22plus_max77705_mux_diag_p318.ko",
            "lib/modules/s22plus_max77705_mux_diag.ko",
        ):
            probe = subprocess.run(
                [str(tool_magisk), "cpio", str(ramdisk), f"exists {member}"],
                cwd=unpack, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, check=False, timeout=30,
            )
            if probe.returncode != 1:
                raise AuditError(f"P311 clean base unexpectedly contains {member}")
        overlay_set = set(overlay_names)
        if set(module_payloads).issuperset(overlay_set) is not True:
            raise AuditError("stock overlay module inputs are incomplete")
        overlay_payloads = {
            name: module_payloads[name] for name in overlay_names
        }
        stage_modules = work / "modules"
        stage_modules.mkdir()
        child_path = work / "s22-e1-child"
        child_path.write_bytes(child_bytes)
        add_commands = [
            f"add 750 init {init_path}",
            f"add 750 s22-e1-child {child_path}",
        ]
        for name, payload in sorted(overlay_payloads.items()):
            module_path = stage_modules / name
            module_path.write_bytes(payload)
            add_commands.append(f"add 640 lib/modules/{name} {module_path}")
        _run_tool(
            [tool_magisk, "cpio", str(ramdisk), *add_commands], unpack,
            "P311 ramdisk init/latch/module overlay",
        )
        boot = work / "boot.img"
        _run_tool([tool_magisk, "repack", base_path, boot], unpack, "stock boot repack")
        candidate = boot.read_bytes()
        _run_tool([tool_magisk, "unpack", "-h", boot], final, "stock final unpack")
        final_ramdisk = final / "ramdisk.cpio"
        extracted_init = final / "init.final"
        _run_tool([tool_magisk, "cpio", str(final_ramdisk), f"extract init {extracted_init}"], final, "stock final init extract")
        if extracted_init.read_bytes() != init_bytes:
            raise AuditError("stock final ramdisk identity differs")
        extracted_child = final / "child.final"
        _run_tool([tool_magisk, "cpio", str(final_ramdisk), f"extract s22-e1-child {extracted_child}"], final, "stock final child extract")
        if extracted_child.read_bytes() != child_bytes:
            raise AuditError("stock final child identity differs")
        final_module_entries = sorted(
            entry for entry in _cpio_entries(tool_magisk, final_ramdisk, final, "stock final")
            if entry.startswith("lib/modules/")
        )
        expected_module_entries = sorted(f"lib/modules/{name}" for name in overlay_names)
        if final_module_entries != expected_module_entries:
            raise AuditError("stock final generic module overlay differs")
        for name, payload in overlay_payloads.items():
            extracted = final / f"{name}.final"
            _run_tool(
                [tool_magisk, "cpio", str(final_ramdisk),
                 f"extract lib/modules/{name} {extracted}"],
                final, f"extract final {name}",
            )
            if extracted.read_bytes() != payload:
                raise AuditError(f"stock final module identity differs: {name}")
        probe_diag = subprocess.run(
            [str(tool_magisk), "cpio", str(final_ramdisk),
             "exists lib/modules/s22plus_max77705_mux_diag_p318.ko"],
            cwd=final, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, timeout=30,
        )
        if probe_diag.returncode != 1:
            raise AuditError("P311 final ramdisk contains diagnostic module")
        probe_old_diag = subprocess.run(
            [str(tool_magisk), "cpio", str(final_ramdisk),
             "exists lib/modules/s22plus_max77705_mux_diag.ko"],
            cwd=final, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, timeout=30,
        )
        if probe_old_diag.returncode != 1:
            raise AuditError("P311 final ramdisk contains predecessor diagnostic module")
        frame_path = work / "boot.img.lz4"
        _run_tool(
            [tool_lz4, "--content-size", "-B6", "-f", "-q", boot, frame_path],
            work, "stock boot LZ4 compression",
        )
        roundtrip = audit / "p319-package-roundtrip.img"
        _run_tool(
            [tool_lz4, "-d", "-f", "-q", frame_path, roundtrip],
            work, "stock boot LZ4 roundtrip",
        )
        if roundtrip.read_bytes() != candidate:
            raise AuditError("stock boot LZ4 roundtrip differs")
        ap_dir = work / "odin4"
        ap_dir.mkdir(mode=0o700)
        ap_path = ap_dir / "AP.tar.md5"
        ap_structure = _write_deterministic_boot_ap(frame_path.read_bytes(), ap_path)
        package = {
            "schema": "s22plus_fyg8_p303_boot_only_package_v1",
            "verdict": "PASS_P303_DETERMINISTIC_BOOT_ONLY_PACKAGE_HOST_ONLY",
            "boot_img": identity(candidate),
            "boot_img_lz4": identity(frame_path.read_bytes()),
            "ap_tar_md5": identity(ap_path.read_bytes()),
            "ap_structure": ap_structure,
            "paths": {"boot_img_lz4": "boot.img.lz4", "ap_tar_md5": "odin4/AP.tar.md5"},
            "verified": True,
            "safety": {"host_only": True, "boot_only": True, "device_contact": False,
                       "device_write": False, "odin_invoked": False, "live_authorized": False},
        }
        output.mkdir(mode=0o700)
        output.chmod(0o700)
        for source, target in ((boot, output / "boot.img"), (frame_path, output / "boot.img.lz4"), (ap_path, output / "odin4/AP.tar.md5")):
            target.parent.mkdir(mode=0o700, exist_ok=True)
            target.parent.chmod(0o700)
            _write_exclusive(target, source.read_bytes())
        _fsync_directory(output / "odin4"); _fsync_directory(output); _fsync_directory(output.parent)
        return {"boot_img": identity(candidate), "boot_img_lz4": identity((output / "boot.img.lz4").read_bytes()), "ap_tar_md5": identity((output / "odin4/AP.tar.md5").read_bytes()), "diagnostic_absent": True, "fixed_image": True, "exact_four_member_overlay": True, "overlay_members": expected_module_entries, "inherited_modules_not_copied": True, "package": package}


def _verify_packaged_candidate(
    candidate_root: Path, expected: dict[str, Any], init_bytes: bytes,
    child_bytes: bytes, module_payloads: dict[str, bytes], image_bytes: bytes,
    overlay_names: tuple[str, ...], label: str,
) -> dict[str, Any]:
    _strict_directory(
        candidate_root, f"{label} candidate root",
        {"boot.img", "boot.img.lz4", "odin4"},
    )
    _strict_directory(
        candidate_root / "odin4", f"{label} candidate AP directory",
        {"AP.tar.md5"},
    )
    magiskboot = _tools()["magiskboot"]
    lz4 = _tools()["lz4"]
    boot = stable_bytes(
        candidate_root / "boot.img", f"{label} boot", 128 * 1024 * 1024,
        expected["boot_img"], required_mode=0o400, required_nlink=1,
    )
    frame = stable_bytes(
        candidate_root / "boot.img.lz4", f"{label} boot.lz4", 128 * 1024 * 1024,
        expected["boot_img_lz4"], required_mode=0o400, required_nlink=1,
    )
    ap_path = candidate_root / "odin4/AP.tar.md5"
    ap = stable_bytes(ap_path, f"{label} AP.tar.md5", 128 * 1024 * 1024,
                       expected["ap_tar_md5"], required_mode=0o400,
                       required_nlink=1)
    trailer_marker = b"  AP.tar\n"
    trailer_start = ap.rfind(trailer_marker)
    if trailer_start < 32:
        raise AuditError(f"{label} AP trailer is malformed")
    tar_start = trailer_start - 32
    tar_payload = ap[:tar_start]
    tar_md5 = ap[tar_start:trailer_start].decode("ascii")
    if hashlib.md5(tar_payload).hexdigest() != tar_md5:
        raise AuditError(f"{label} AP tar digest differs")
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_payload), mode="r:") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            if names != ["boot.img.lz4"]:
                raise AuditError(f"{label} AP member set differs")
            member_bytes = archive.extractfile(members[0]).read()  # type: ignore[union-attr]
            if member_bytes != frame:
                raise AuditError(f"{label} AP boot frame differs")
    except (OSError, tarfile.TarError) as exc:
        raise AuditError(f"{label} AP tar cannot be audited") from exc
    with tempfile.TemporaryDirectory(prefix=f"p319-stock-audit-{label}-") as name:
        work = Path(name); unpack = work / "unpack"; final = work / "final"
        tools = work / "tools"
        for directory in (unpack, final, tools):
            directory.mkdir()
        tool_magisk = tools / "magiskboot"; tool_magisk.write_bytes(stable_bytes(magiskboot, "magiskboot", 4 * 1024 * 1024)); tool_magisk.chmod(0o700)
        tool_lz4 = tools / "lz4"; tool_lz4.write_bytes(stable_bytes(lz4, "lz4", 4 * 1024 * 1024)); tool_lz4.chmod(0o700)
        boot_path = work / "boot.img"; boot_path.write_bytes(boot)
        frame_path = work / "boot.img.lz4"; frame_path.write_bytes(frame)
        roundtrip = work / "roundtrip.boot.img"
        _run_tool([tool_lz4, "-d", "-f", "-q", frame_path, roundtrip], work, f"{label} lz4 roundtrip")
        if roundtrip.read_bytes() != boot:
            raise AuditError(f"{label} lz4 roundtrip differs")
        _run_tool([tool_magisk, "unpack", "-h", boot_path], unpack, f"{label} unpack")
        final_ramdisk = unpack / "ramdisk.cpio"
        entries = _cpio_entries(tool_magisk, final_ramdisk, unpack, label)
        overlay_entries = sorted(entry for entry in entries if entry.startswith("lib/modules/"))
        expected_entries = sorted(f"lib/modules/{name}" for name in overlay_names)
        if overlay_entries != expected_entries:
            raise AuditError(f"{label} generic module overlay differs")
        if (unpack / "kernel").read_bytes() != image_bytes:
            raise AuditError(f"{label} fixed Image differs")
        init_extract = final / "init"; child_extract = final / "child"
        _run_tool([tool_magisk, "cpio", str(final_ramdisk), f"extract init {init_extract}"], unpack, f"{label} init extract")
        _run_tool([tool_magisk, "cpio", str(final_ramdisk), f"extract s22-e1-child {child_extract}"], unpack, f"{label} child extract")
        if init_extract.read_bytes() != init_bytes or child_extract.read_bytes() != child_bytes:
            raise AuditError(f"{label} userspace payload differs")
        for name in overlay_names:
            extracted = final / name
            _run_tool([tool_magisk, "cpio", str(final_ramdisk), f"extract lib/modules/{name} {extracted}"], unpack, f"{label} {name} extract")
            if extracted.read_bytes() != module_payloads[name]:
                raise AuditError(f"{label} overlay module differs: {name}")
        diag = "lib/modules/s22plus_max77705_mux_diag_p318.ko"
        if diag in entries:
            raise AuditError(f"{label} diagnostic module is present")
        old_diag = "lib/modules/s22plus_max77705_mux_diag.ko"
        if old_diag in entries:
            raise AuditError(f"{label} predecessor diagnostic module is present")
    package = {
        "schema": "s22plus_fyg8_p303_boot_only_package_v1",
        "verdict": "PASS_P303_DETERMINISTIC_BOOT_ONLY_PACKAGE_HOST_ONLY",
        "verified": True,
        "safety": {
            "boot_only": True, "device_contact": False,
            "device_write": False, "host_only": True,
            "live_authorized": False, "odin_invoked": False,
        },
        "boot_img": identity(boot),
        "boot_img_lz4": identity(frame),
        "ap_tar_md5": identity(ap),
        "paths": {"boot_img_lz4": "boot.img.lz4", "ap_tar_md5": "odin4/AP.tar.md5"},
        "ap_structure": {
            "members": ["boot.img.lz4"], "tar_md5": tar_md5,
            "tar_prefix_size": len(tar_payload),
            "trailer": tar_md5 + "  AP.tar\\n",
        },
    }
    return {
        "boot_img": identity(boot), "boot_img_lz4": identity(frame),
        "ap_tar_md5": identity(ap), "diagnostic_absent": True,
        "fixed_image": True, "exact_four_member_overlay": True,
        "overlay_members": sorted(f"lib/modules/{name}" for name in overlay_names),
        "inherited_modules_not_copied": True, "package": package,
    }


def _audit_phase2_existing(
    output_root: Path, existing: dict[str, Any], source_root: Path,
    module_audit: dict[str, Any], image_bytes: bytes,
    overlay_names: tuple[str, ...],
) -> dict[str, Any]:
    phase2 = existing.get("phase2")
    if not isinstance(phase2, dict) or phase2.get("built") is not True:
        raise AuditError("existing Phase-2 result is not marked built")
    userspace = phase2.get("userspace")
    candidate = phase2.get("candidate")
    if not isinstance(userspace, dict) or not isinstance(candidate, dict):
        raise AuditError("existing Phase-2 result shape differs")
    if phase2.get("userspace_compiles") != 3:
        raise AuditError("existing Phase-2 compile count differs")
    a, b = userspace.get("a"), userspace.get("b")
    if not isinstance(a, dict) or not isinstance(b, dict) or a != b:
        raise AuditError("existing Phase-2 A/B userspace metadata differs")
    _strict_directory(output_root / "userspace-a", "existing userspace A", {"init", "s22-e1-child"})
    _strict_directory(output_root / "userspace-b", "existing userspace B", {"init", "s22-e1-child"})
    for label in ("candidate-a", "candidate-b"):
        _strict_directory(output_root / label, f"existing {label}", {"boot.img", "boot.img.lz4", "odin4"})
        _strict_directory(output_root / label / "odin4", f"existing {label} AP directory", {"AP.tar.md5"})
    a_init = stable_bytes(output_root / "userspace-a/init", "existing userspace A init", 1 * 1024 * 1024, a["init"], required_mode=0o400, required_nlink=1)
    a_child = stable_bytes(output_root / "userspace-a/s22-e1-child", "existing userspace A child", 1 * 1024 * 1024, a["child"], required_mode=0o400, required_nlink=1)
    b_init = stable_bytes(output_root / "userspace-b/init", "existing userspace B init", 1 * 1024 * 1024, b["init"], required_mode=0o400, required_nlink=1)
    b_child = stable_bytes(output_root / "userspace-b/s22-e1-child", "existing userspace B child", 1 * 1024 * 1024, b["child"], required_mode=0o400, required_nlink=1)
    if (a_init, a_child) != (b_init, b_child):
        raise AuditError("existing Phase-2 A/B userspace bytes differ")
    with tempfile.TemporaryDirectory(prefix="p319-stock-audit-third-") as name:
        init = Path(name) / "init"; child = Path(name) / "s22-e1-child"
        _compile_userspace_to_path(source_root, init, child)
        third = userspace.get("third_compile")
        if third != {"init": identity(init.read_bytes()), "child": identity(child.read_bytes())}:
            raise AuditError("existing Phase-2 third compile differs")
    expected_module_payloads = module_audit["source_payloads"]
    expected_a = candidate.get("a"); expected_b = candidate.get("b")
    if not isinstance(expected_a, dict) or not isinstance(expected_b, dict) or expected_a != expected_b:
        raise AuditError("existing Phase-2 A/B candidate metadata differs")
    verified_a = _verify_packaged_candidate(output_root / "candidate-a", expected_a, a_init, a_child, expected_module_payloads, image_bytes, overlay_names, "candidate-a")
    verified_b = _verify_packaged_candidate(output_root / "candidate-b", expected_b, a_init, a_child, expected_module_payloads, image_bytes, overlay_names, "candidate-b")
    if verified_a != expected_a or verified_b != expected_b:
        raise AuditError("existing Phase-2 package receipt differs")
    if candidate.get("byte_identical") is not True or candidate.get("base") != P311_BASE_BOOT_IDENTITY:
        raise AuditError("existing Phase-2 base or A/B binding differs")
    return phase2


def _assemble_result(
    *, auditor: bytes, v5_auditor: bytes, parser_auditor: bytes,
    v5_receipt: bytes, parser_receipt: bytes, plan: bytes,
    rows: list[dict[str, Any]], abi: dict[str, Any],
    module_audit: dict[str, Any], sources: dict[str, bytes],
    p311_base: bytes, phase2: dict[str, Any] | None = None,
) -> dict[str, Any]:
    userspace_compiles = int(phase2.get("userspace_compiles", 0)) if phase2 else 0
    boot_builds = int(phase2.get("boot_builds", 0)) if phase2 else 0
    ap_builds = int(phase2.get("ap_builds", 0)) if phase2 else 0
    return {
        "schema": SCHEMA, "verdict": VERDICT,
        "status": "IMPLEMENTED_REVIEW_PENDING", "target": TARGET,
        "auditor": identity(auditor),
        "profile": {
            "name": "STOCK_EMITTERS_V1", "payload_abi": STOCK_PAYLOAD_ABI,
            "encoding": STOCK_ENCODING, "domain": STOCK_DOMAIN.decode("ascii").rstrip("\0"),
            "status_width": STOCK_STATUS_WIDTH,
            "chain": list(STOCK_CHAIN_STAGES),
            "parent_unavailable": True, "w5_unavailable": True,
            "enhanced_witness_claimable": False,
            "enhanced_markers_rejected": False,
            "unsupported_parent_w5_markers_rejected": True,
            "auxiliary_form2_deferred_accepted": True,
            "late_diagnostic_reachable": False,
            "i2c_transactions_added": 0,
        },
        "reviewed_predecessors": {
            "carrier_v5_auditor": identity(v5_auditor),
            "carrier_v5_receipt": identity(v5_receipt),
            "parser_v2_auditor": identity(parser_auditor),
            "parser_v2_receipt": identity(parser_receipt),
            "v5_reinterpreted": False,
        },
        "inputs": {
            "p318_static_check_result": P318_STATIC_RESULT_IDENTITY,
            "p318_candidate_patch": P318_CANDIDATE_PATCH_IDENTITY,
            "p319_module_materialization_receipt": P319_MATERIALIZATION_RECEIPT_IDENTITY,
            "v5_receipt": V5_RECEIPT_IDENTITY,
            "parser_receipt": PARSER_RECEIPT_IDENTITY,
            "image": IMAGE_IDENTITY,
            "p311_base_boot": P311_BASE_BOOT_IDENTITY,
            "child_source": CHILD_SOURCE_IDENTITY,
        },
        "tools": _tool_receipt(),
        "plan": {"identity": identity(plan), "rows": rows,
            "eud_index": 38, "module_count": 73},
        "fixed_image_abi": {key: value for key, value in abi.items()
            if key != "image_bytes"},
        "module_crc_closure": {
            key: value for key, value in module_audit.items() if key != "source_payloads"
        },
        "source": {
            "predecessor_v5_sources": _v5_materialized_source_identities(v5_receipt),
            "materialized_stock_sources": {name: identity(payload) for name, payload in sources.items()},
            "driver_patches_consumed": False,
            "enhanced_driver_sources_consumed": False,
            "stock_runtime_transform": {
                "three_byte_initial_status": True,
                "status_padding_fabricated": False,
                "four_stage_chain": list(STOCK_CHAIN_STAGES),
                "enhanced_markers_rejected": False,
                "unsupported_parent_w5_markers_rejected": True,
                "auxiliary_form2_deferred_accepted": True,
                "p318_gadget_role_udc_direct_prefix_preserved": True,
                "p316_p317_provider_and_late_diagnostic_tail_reachable": False,
                "no_i2c_terminal_publisher": True,
                "terminal_details": [0x6724, 0x6725, 0x6726],
                "checkpoint_allowlist": {
                    "detail_first": 0x6724,
                    "detail_last": 0x6726,
                    "transformed_functions": ["p288_detail_allowed", "s22_max77705_detail_allowed"],
                    "candidate_patch_bound": P318_CANDIDATE_PATCH_IDENTITY,
                    "positive_and_adjacent_negative_fixture": True,
                },
                "auxiliary_form2_and_deferred": {
                    "accepted_as_auxiliary": True,
                    "primary_chain_stage": False,
                    "payload_count_offsets": {"form2": 59, "deferred": 60},
                },
            },
        },
        "phase2_inputs": {
            "fixed_image": identity(abi["image_bytes"]),
            "p311_clean_base_boot": identity(p311_base),
            "source_bundle_ready": True,
            "boot_build": bool(phase2 and phase2.get("built")),
            "ap_build": bool(phase2 and phase2.get("built")),
        },
        "phase2": phase2 or {
            "built": False, "userspace_compiles": 0,
            "boot_builds": 0, "ap_builds": 0,
        },
        "scope": {
            "tier": "H0", "host_only": True, "device_contact": False,
            "adb_commands": 0, "usb_actions": 0, "odin_invocations": 0,
            "userspace_compiles": userspace_compiles,
            "boot_builds": boot_builds, "ap_builds": ap_builds,
            "candidate_transfers": 0, "rollback_transfers": 0,
            "recovery_actions": 0, "live_authority_created": False,
            "replay": False,
        },
        "limits": [
            "Phase 1 materializes source and private ABI inputs only; optional Phase 2 is host-only and remains unqualified until independent review.",
            "W5 and extended W4 bytes are structurally absent from STOCK_EMITTERS_V1.",
        ],
    }


def _publish_input_bundle(output_root: Path, inputs: dict[str, bytes]) -> None:
    input_root = output_root / "inputs"
    input_root.mkdir(mode=0o700)
    input_root.chmod(0o700)
    for name, payload in inputs.items():
        _write_exclusive(input_root / name, payload)
    _fsync_directory(input_root)


def _audit_input_bundle(input_root: Path) -> dict[str, bytes]:
    expected = {
        "fixed-Image": (IMAGE, IMAGE_IDENTITY, 64 * 1024 * 1024),
        "module.c": (KERNEL_MODULE_SOURCE, MODULE_SOURCE_IDENTITY, 2 * 1024 * 1024),
        "carrier-v5-result.json": (V5_RECEIPT, V5_RECEIPT_IDENTITY, 64 * 1024),
        "carrier-v5-auditor.py": (V5_AUDITOR, V5_AUDITOR_IDENTITY, 256 * 1024),
        "parser-v2-result.json": (
            V5_ROOT.parent / "successor-witness-parser-v2-20260820-14/result.json",
            PARSER_RECEIPT_IDENTITY, 64 * 1024,
        ),
        "parser-v2-auditor.py": (PARSER_AUDITOR, PARSER_AUDITOR_IDENTITY, 256 * 1024),
        "reviewed-lineage-source.py": (PACKAGER_SOURCE, PACKAGER_SOURCE_IDENTITY, 256 * 1024),
        "child-source.c": (CHILD_SOURCE, CHILD_SOURCE_IDENTITY, 64 * 1024),
        "p318-static-check-result.json": (P318_STATIC_RESULT, P318_STATIC_RESULT_IDENTITY, 2 * 1024 * 1024),
        "p318-candidate.patch": (P318_CANDIDATE_PATCH, P318_CANDIDATE_PATCH_IDENTITY, 128 * 1024),
        "p319-module-materialization-result.json": (
            P319_MATERIALIZATION_RECEIPT, P319_MATERIALIZATION_RECEIPT_IDENTITY, 128 * 1024,
        ),
    }
    _strict_directory(input_root, "stock input bundle", set(expected))
    payloads: dict[str, bytes] = {}
    for name, (source, expected_identity, maximum) in expected.items():
        payloads[name] = stable_bytes(
            input_root / name, f"stock input {name}", maximum,
            expected_identity, required_mode=0o400, required_nlink=1,
        )
        source_payload = stable_bytes(source, f"bound input {name}", maximum, expected_identity)
        if payloads[name] != source_payload:
            raise AuditError(f"stock input bundle differs from bound input: {name}")
    return payloads


def _publish_module_snapshot(output_root: Path, payloads: dict[str, bytes]) -> Path:
    module_root = output_root / "module-bytes"
    module_root.mkdir(mode=0o700)
    module_root.chmod(0o700)
    for name, payload in payloads.items():
        _write_exclusive(module_root / name, payload)
    _fsync_directory(module_root)
    return module_root


def _audit_existing(output_root: Path) -> dict[str, Any]:
    _require_bound_authority()
    _bind_tools()
    result_path = output_root / "result.json"
    existing_payload = result_path.read_bytes()
    result_bytes = stable_bytes(
        result_path, "existing stock result", 2 * 1024 * 1024,
        expected=identity(existing_payload), required_mode=0o400,
        required_nlink=1,
    )
    try:
        existing_result = json.loads(result_bytes.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError("existing stock result is not canonical JSON") from exc
    if not isinstance(existing_result, dict):
        raise AuditError("existing stock result root differs")
    input_root = output_root / "inputs"
    source_root = output_root / "stock-sources"
    module_root = output_root / "module-bytes"
    phase2_marker = existing_result.get("phase2")
    root_children = {"result.json", "inputs", "stock-sources", "module-bytes"}
    if isinstance(phase2_marker, dict) and phase2_marker.get("built") is True:
        root_children |= {"userspace-a", "userspace-b", "candidate-a", "candidate-b"}
    _strict_directory(output_root, "existing stock output root", root_children)
    if not input_root.is_dir() or not source_root.is_dir() or not module_root.is_dir():
        raise AuditError("existing stock output bundle is incomplete")
    _strict_directory(source_root, "existing stock source bundle", set(MODULE_SOURCE_FILES))
    _audit_input_bundle(input_root)
    auditor = _load_bound_auditor_source()
    v5_auditor = stable_bytes(V5_AUDITOR, "V5 auditor", 256 * 1024, V5_AUDITOR_IDENTITY)
    parser_auditor = stable_bytes(PARSER_AUDITOR, "parser auditor", 256 * 1024, PARSER_AUDITOR_IDENTITY)
    v5_receipt = stable_bytes(V5_RECEIPT, "V5 receipt", 64 * 1024, V5_RECEIPT_IDENTITY)
    parser_receipt = stable_bytes(
        V5_ROOT.parent / "successor-witness-parser-v2-20260820-14/result.json",
        "parser receipt", 64 * 1024, PARSER_RECEIPT_IDENTITY,
    )
    plan = stable_bytes(V5_SOURCES / PLAN_NAME, "73-row plan", 64 * 1024)
    rows = parse_plan(plan)
    abi = audit_same_magic_and_image()
    p311_base = stable_bytes(P311_BASE_BOOT, "P311 clean base boot", 128 * 1024 * 1024, P311_BASE_BOOT_IDENTITY)
    _, static_result, materialization, materialization_payload = _reviewed_module_inputs()
    _reviewed_payloads, _expected_module_rows, overlay_names = _load_exact_module_payloads(
        rows, static_result, materialization,
    )
    expected_module_names = set(_reviewed_payloads)
    _strict_directory(module_root, "existing module snapshot", expected_module_names)
    for name, expected_payload in _reviewed_payloads.items():
        stable_bytes(
            module_root / name, f"existing module snapshot {name}",
            8 * 1024 * 1024, identity(expected_payload),
            required_mode=0o400, required_nlink=1,
        )
    module_audit = audit_modules(
        rows, abi["image_provider_map"], abi["image_vermagic"]["suffix"], module_root,
    )
    with tempfile.TemporaryDirectory(prefix="p319-stock-source-audit-") as name:
        regenerated = materialize_stock_sources(Path(name) / "stock-sources")
        source_payloads: dict[str, bytes] = {}
        for filename, payload in regenerated.items():
            source_payloads[filename] = stable_bytes(
                source_root / filename, f"existing stock source {filename}",
                2 * 1024 * 1024, identity(payload), required_mode=0o400,
                required_nlink=1,
            )
            if payload != source_payloads[filename]:
                raise AuditError(f"stock source regeneration differs: {filename}")
    abi_for_result = dict(abi)
    image_bytes = stable_bytes(IMAGE, "fixed Image", 64 * 1024 * 1024, IMAGE_IDENTITY)
    abi_for_result["image_bytes"] = image_bytes
    phase2_result = None
    phase2_existing = existing_result.get("phase2")
    if isinstance(phase2_existing, dict) and phase2_existing.get("built") is True:
        phase2_result = _audit_phase2_existing(
            output_root, existing_result, source_root, module_audit, image_bytes,
            overlay_names,
        )
    expected = _assemble_result(
        auditor=auditor, v5_auditor=v5_auditor, parser_auditor=parser_auditor,
        v5_receipt=v5_receipt, parser_receipt=parser_receipt, plan=plan,
        rows=rows, abi=abi_for_result, module_audit=module_audit,
        sources=source_payloads,
        p311_base=p311_base, phase2=phase2_result,
    )
    if _json_bytes(expected) != result_bytes:
        raise AuditError("existing stock result is not deterministic")
    return expected


def build_result(
    output_root: Path, *, audit_only: bool = False, phase2: bool = False,
) -> dict[str, Any]:
    _require_bound_authority()
    _bind_tools()
    output_root = output_root.absolute()
    if audit_only:
        return _audit_existing(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("stock witness output already exists")
    output_root.mkdir(mode=0o700)
    output_root.chmod(0o700)
    auditor = _load_bound_auditor_source()
    v5_auditor = stable_bytes(V5_AUDITOR, "V5 auditor", 256 * 1024, V5_AUDITOR_IDENTITY)
    parser_auditor = stable_bytes(PARSER_AUDITOR, "parser auditor", 256 * 1024, PARSER_AUDITOR_IDENTITY)
    v5_receipt = stable_bytes(V5_RECEIPT, "historical V5 receipt", 64 * 1024, V5_RECEIPT_IDENTITY)
    parser_receipt = stable_bytes(
        V5_ROOT.parent / "successor-witness-parser-v2-20260820-14/result.json",
        "parser receipt", 64 * 1024, PARSER_RECEIPT_IDENTITY,
    )
    plan = stable_bytes(V5_SOURCES / PLAN_NAME, "73-row plan", 64 * 1024)
    rows = parse_plan(plan)
    abi = audit_same_magic_and_image()
    p311_base = stable_bytes(P311_BASE_BOOT, "P311 clean base boot", 128 * 1024 * 1024, P311_BASE_BOOT_IDENTITY)
    _, static_result, materialization, materialization_payload = _reviewed_module_inputs()
    reviewed_payloads, expected_module_rows, overlay_names = _load_exact_module_payloads(
        rows, static_result, materialization,
    )
    source_dir = output_root / "stock-sources"
    sources = materialize_stock_sources(source_dir)
    module_root = _publish_module_snapshot(output_root, reviewed_payloads)
    module_audit = audit_modules(
        rows, abi["image_provider_map"], abi["image_vermagic"]["suffix"], module_root,
    )
    _publish_input_bundle(output_root, {
        "fixed-Image": stable_bytes(IMAGE, "fixed Image", 64 * 1024 * 1024, IMAGE_IDENTITY),
        "module.c": stable_bytes(KERNEL_MODULE_SOURCE, "loader module.c", 2 * 1024 * 1024, MODULE_SOURCE_IDENTITY),
        "carrier-v5-result.json": v5_receipt,
        "carrier-v5-auditor.py": v5_auditor,
        "parser-v2-result.json": parser_receipt,
        "parser-v2-auditor.py": parser_auditor,
        "reviewed-lineage-source.py": stable_bytes(
            PACKAGER_SOURCE, "reviewed package lineage source", 256 * 1024,
            PACKAGER_SOURCE_IDENTITY,
        ),
        "p318-static-check-result.json": stable_bytes(
            P318_STATIC_RESULT, "P318 static-check result", 2 * 1024 * 1024,
            P318_STATIC_RESULT_IDENTITY, required_mode=0o400, required_nlink=1,
        ),
        "p318-candidate.patch": stable_bytes(
            P318_CANDIDATE_PATCH, "P318 candidate patch", 128 * 1024,
            P318_CANDIDATE_PATCH_IDENTITY, required_mode=0o400, required_nlink=1,
        ),
        "p319-module-materialization-result.json": materialization_payload,
        "child-source.c": stable_bytes(
            CHILD_SOURCE, "child source", 64 * 1024, CHILD_SOURCE_IDENTITY,
        ),
    })
    abi_for_result = dict(abi)
    abi_for_result["image_bytes"] = stable_bytes(IMAGE, "fixed Image", 64 * 1024 * 1024, IMAGE_IDENTITY)
    phase2_result: dict[str, Any] | None = None
    if phase2:
        userspace_a = _compile_userspace(source_dir, output_root / "userspace-a", label="a")
        userspace_b = _compile_userspace(source_dir, output_root / "userspace-b", label="b")
        if userspace_a != userspace_b:
            raise AuditError("stock userspace A/B differs")
        userspace_a_init = stable_bytes(
            output_root / "userspace-a/init", "stock userspace A init",
            1 * 1024 * 1024, userspace_a["init"], required_mode=0o400,
            required_nlink=1,
        )
        userspace_a_child = stable_bytes(
            output_root / "userspace-a/s22-e1-child", "stock userspace A child",
            1 * 1024 * 1024, userspace_a["child"], required_mode=0o400,
            required_nlink=1,
        )
        userspace_b_init = stable_bytes(
            output_root / "userspace-b/init", "stock userspace B init",
            1 * 1024 * 1024, userspace_b["init"], required_mode=0o400,
            required_nlink=1,
        )
        userspace_b_child = stable_bytes(
            output_root / "userspace-b/s22-e1-child", "stock userspace B child",
            1 * 1024 * 1024, userspace_b["child"], required_mode=0o400,
            required_nlink=1,
        )
        if (userspace_a_init, userspace_a_child) != (userspace_b_init, userspace_b_child):
            raise AuditError("stock userspace A/B artifacts differ")
        with tempfile.TemporaryDirectory(prefix="p319-stock-phase2-init-") as name:
            init_path = Path(name) / "init"
            child_path = Path(name) / "s22-e1-child"
            _compile_userspace_to_path(source_dir, init_path, child_path)
            init_bytes = init_path.read_bytes()
            child_bytes = child_path.read_bytes()
            if identity(init_bytes) != userspace_a["init"] or identity(child_bytes) != userspace_a["child"]:
                raise AuditError("third stock userspace compile differs from A/B")
            candidate_a = _package_candidate(
                p311_base, init_bytes, child_bytes, module_audit["source_payloads"],
                overlay_names, output_root / "candidate-a", "a",
            )
            candidate_b = _package_candidate(
                p311_base, init_bytes, child_bytes, module_audit["source_payloads"],
                overlay_names, output_root / "candidate-b", "b",
            )
        if candidate_a != candidate_b:
            raise AuditError("stock candidate A/B differs")
        phase2_result = {
            "built": True, "userspace_compiles": 3,
            "boot_builds": 2, "ap_builds": 2,
            "userspace": {"a": userspace_a, "b": userspace_b,
                           "third_compile": {"init": identity(init_bytes), "child": identity(child_bytes)},
                           "byte_identical": True},
            "candidate": {"a": candidate_a, "b": candidate_b,
                           "byte_identical": True,
                           "base": P311_BASE_BOOT_IDENTITY,
                           "exact_four_member_overlay": True,
                           "overlay_members": list(sorted(
                               f"lib/modules/{name}" for name in overlay_names
                           )),
                           "inherited_modules_not_copied": True,
                           "diagnostic_absent": True},
        }
    result = _assemble_result(
        auditor=auditor, v5_auditor=v5_auditor, parser_auditor=parser_auditor,
        v5_receipt=v5_receipt, parser_receipt=parser_receipt, plan=plan,
        rows=rows, abi=abi_for_result, module_audit=module_audit,
        sources=sources, p311_base=p311_base, phase2=phase2_result,
    )
    payload = _json_bytes(result)
    _write_exclusive(output_root / "result.json", payload)
    _fsync_directory(output_root)
    return result


def _compile_userspace_to_path(
    source_dir: Path, output: Path, child_output: Path | None = None,
) -> None:
    tools = _tools(); output.parent.mkdir(parents=True, exist_ok=True)
    define = "{" + ",".join(f"0x{value:02x}" for value in RUN_ID) + "}"
    environment = os.environ.copy()
    for key in COMPILER_ENVIRONMENT_KEYS:
        environment.pop(key, None)
    environment.update({"LANG": "C", "LC_ALL": "C", "SOURCE_DATE_EPOCH": "0"})
    command = [tools["gcc"], *COMPILE_FLAGS, "-DS22PLUS_FYG8_P233_PROFILE=3", f"-DS22PLUS_FYG8_P233_RUN_ID_BYTES={define}", "-I", str(source_dir), "-I", str(ROOT / "workspace/public/src/native-init"), source_dir / RUNTIME_NAME, source_dir / CHECKPOINT_NAME, "-o", output]
    result = subprocess.run([str(value) for value in command], cwd=ROOT, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=180)
    if result.returncode != 0:
        raise AuditError(f"stock init compile for packaging failed: {(result.stdout + result.stderr).decode('utf-8', 'replace')[-4000:]}")
    _bind_tools()
    if child_output is not None:
        child_output.parent.mkdir(parents=True, exist_ok=True)
        child_source = source_dir.parent / "inputs/child-source.c"
        stable_bytes(child_source, "preserved child source", 64 * 1024, CHILD_SOURCE_IDENTITY, required_mode=0o400, required_nlink=1)
        child_command = [tools["gcc"], *COMPILE_FLAGS, child_source, "-o", child_output]
        child_result = subprocess.run([str(value) for value in child_command], cwd=ROOT, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=180)
        if child_result.returncode != 0:
            raise AuditError(f"stock child compile for packaging failed: {(child_result.stdout + child_result.stderr).decode('utf-8', 'replace')[-4000:]}")
        _bind_tools()


def main(argv: list[str] | None = None) -> int:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        return _bound_auditor_module().main(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--audit-only", action="store_true",
        help="verify an existing no-clobber Phase-1 output without writing",
    )
    parser.add_argument(
        "--phase2", action="store_true",
        help="build the private A/B boot/AP successor from the Phase-1 bundle",
    )
    args = parser.parse_args(argv)
    try:
        result = build_result(
            (args.out if args.out.is_absolute() else ROOT / args.out).absolute(),
            audit_only=args.audit_only,
            phase2=args.phase2,
        )
    except (AuditError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"], "output": str(args.out)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
