#!/usr/bin/env python3
"""Materialize the P3.19 73-row module plan and identity-derived EUD hook.

Host-only.  This consumes the reviewed P3.19 V2 derivation, the exact frozen
P3.18 materialized sources, and the exact FYG8 vendor_boot/vendor_dlkm module
bytes.  It emits a no-clobber source bundle in which:

* only three plan rows are appended;
* the EUD index is rendered by the same plan materialization that renders the
  rows, rather than retained as a second runtime literal; and
* one post-load helper is called after successful loads in both the direct and
  folded loops.

The bundle is an H0 predecessor.  It does not build or package a candidate and
creates no connected or live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import sys
import types
from dataclasses import dataclass
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
AUDITOR = Path(__file__).resolve()
P318_ROOT = ROOT / "workspace/private/outputs/s22plus_fyg8_p318"
P318_SOURCES = P318_ROOT / "intent/materialized-sources"
P318_STATIC = P318_ROOT / "static-check-result.json"
V2_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "successor-module-plan-v2-20260820-02/result.json"
)
VENDOR_RAMDISK_MODULES = Path(
    "/mnt/android-lab-sd/extract/ap-fyg8/vboot/rd/lib/modules"
)
VENDOR_DLKM_MODULES = Path("/mnt/android-lab-logical/vendor_dlkm/lib/modules")
PRIOR_IRQ_INPUTS = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "max77705-irq-dt-audit-20260820-05/inputs"
)
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "successor-module-materialization-v1-20260820-04"
)

SCHEMA = "s22plus-fyg8-p319-successor-module-materialization-v1"
VERDICT = "PASS_P319_SUCCESSOR_MODULE_MATERIALIZATION_H0"
TARGET = {
    "model": "SM-S906N",
    "codename": "g0q",
    "build": "S906NKSS7FYG8",
}
RUN_ID = bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")
EUD_IDENTITY = ("eud.ko", "eud", "")
ADDITIONS = (
    ("spu_verify.ko", "spu_verify", ""),
    ("mfd_max77705.ko", "mfd_max77705", ""),
    ("pdic_max77705.ko", "pdic_max77705", ""),
)
VERMAGIC = (
    "5.10.226-android12-9-gki-30958166-abS906NKSS7FYG8 SMP preempt "
    "mod_unload modversions aarch64"
)


class AuditError(RuntimeError):
    """An exact source, module, transformation, or publication differs."""


_BOUND_AUDITOR_SOURCE = globals().get("_P319_MATERIALIZER_BOUND_SOURCE")


@dataclass(frozen=True)
class FileSpec:
    size: int
    sha256: str
    maximum: int


P318_SOURCE_SPECS: dict[str, FileSpec] = {
    "s22plus_fyg8_p260_e3_runtime.inc.c": FileSpec(
        20_665, "767bd359de56cb24be84c4479cd01d4f710a676490c23f966617b996fe5cc612", 64 << 10
    ),
    "s22plus_fyg8_p282_classifier.inc.c": FileSpec(
        14_317, "e14a634ec39102d999f51e64b01b1350d9c000e465f01b639b106d51c36d483e", 64 << 10
    ),
    "s22plus_fyg8_p286_classifier.inc.c": FileSpec(
        3_701, "14b82ca22e307708cc412b29fa2b7e4784dc791348298c376ab3d8bc4d66d09e", 32 << 10
    ),
    "s22plus_fyg8_p286_e3_plan.h": FileSpec(
        5_142, "682f18fb470b0e538eb463db5d2a865864b8aaa4681b41230e7c20cc134e70d7", 32 << 10
    ),
    "s22plus_fyg8_p286_trace_descriptor.h": FileSpec(
        27_172, "3e233e3eeee6ac8c522f2ae7352bce1ed736de35c85d6869b0f3e68573b6f735", 64 << 10
    ),
    "s22plus_fyg8_p288_classifier.inc.c": FileSpec(
        1_873, "7a15ae652d652a321e1291fd6fe4f6b400a219f22337f7886ec63f7f4e059025", 32 << 10
    ),
    "s22plus_fyg8_p290_checkpoint.c": FileSpec(
        40_341, "7d6fbc3925ff11c41818765d89a4ce9794dcc17c16929778bd1b029e5d583dce", 128 << 10
    ),
    "s22plus_fyg8_p290_e3_runtime.c": FileSpec(
        30_664, "8c0bf6a4765aa2a27bfe420de6c8599366267e546422378a21f586a8beeb9b7b", 128 << 10
    ),
    "s22plus_fyg8_p290_e3_runtime.inc.c": FileSpec(
        397_669, "050a8eb0deeb755540e9ca860b0ab50a6e9d69c02a644805f7cfd6eae644e42e", 512 << 10
    ),
    "s22plus_fyg8_p290_positions.h": FileSpec(
        2_674, "33e880a6ab8ea887579add07212f063dbdd80dd27b1555485a71d1198c82d247", 32 << 10
    ),
    "s22plus_r4w1e_checkpoint.h": FileSpec(
        3_348, "8584bd67d8c75c5db033cfb47cdbb6d300da4647fbf34bb4250a338792e309b3", 32 << 10
    ),
    "s22plus_r4w1e_e1_runtime.c": FileSpec(
        19_398, "8fd76a904f72c02c8bb10c6b0505f8d3b01e4db4ad349dc4228b5609ac945284", 64 << 10
    ),
}

V2_SPEC = FileSpec(
    14_833,
    "d8c12396e241e387fe342803eca4537b6728dcda7fb901aa8dc7e591d4745cb2",
    64 << 10,
)
P318_STATIC_SPEC = FileSpec(
    554_578,
    "2a4d639b55aa21cf8f52dba505e9bc2d9dfd33f20cd3b217a7c482906aeea4df",
    1 << 20,
)
MODULE_SPECS: dict[str, FileSpec] = {
    "spu_verify.ko": FileSpec(
        18_608, "d670a944288dffcc5fbf67a76550dc8a746665113f6ee4354521e482489f4b84", 64 << 10
    ),
    "mfd_max77705.ko": FileSpec(
        125_840, "26f238730604789293db237b2bcdc4d44c5f63c263e4298f6e8e28b85d0f6f94", 256 << 10
    ),
    "pdic_max77705.ko": FileSpec(
        423_456, "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db", 512 << 10
    ),
    "dwc3-msm.ko": FileSpec(
        308_624, "8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1", 512 << 10
    ),
}

PLAN_NAME = "s22plus_fyg8_p286_e3_plan.h"
WRAPPER_NAME = "s22plus_fyg8_p290_e3_runtime.c"
RUNTIME_NAME = "s22plus_fyg8_p290_e3_runtime.inc.c"
CHANGED_SOURCES = frozenset({PLAN_NAME, WRAPPER_NAME, RUNTIME_NAME})


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
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


def stable_bytes(
    path: Path,
    *,
    label: str,
    maximum: int,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
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
        or _stat_identity(before) != _stat_identity(inside)
        or _stat_identity(before) != _stat_identity(after)
        or (expected_size is not None and len(payload) != expected_size)
        or (expected_sha256 is not None and sha256(payload) != expected_sha256)
        or (required_mode is not None and stat.S_IMODE(before.st_mode) != required_mode)
        or (required_nlink is not None and before.st_nlink != required_nlink)
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
                raise AuditError(f"short write: {path.name}")
            offset += written
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or stat.S_IMODE(state.st_mode) != mode
            or state.st_nlink != 1
            or state.st_size != len(payload)
        ):
            raise AuditError(f"published file metadata differs: {path.name}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _mkdir(path: Path) -> None:
    os.mkdir(path, 0o700)
    os.chmod(path, 0o700)


def strict_json(payload: bytes, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise AuditError(f"{label} has duplicate JSON key {key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise AuditError(f"{label} has non-finite JSON value {value}")

    try:
        return json.loads(payload, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc


def _replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if payload.count(old) != 1:
        raise AuditError(f"{label} anchor differs")
    return payload.replace(old, new, 1)


PLAN_BEGIN = (
    b"static const struct s22plus_o2_module_plan_entry "
    b"s22plus_o2_module_plan[] = {\n"
)
PLAN_END = b"};\n\n#define S22PLUS_O2_MODULE_PLAN_COUNT"


def parse_plan(payload: bytes) -> list[tuple[str, str, str]]:
    if payload.count(PLAN_BEGIN) != 1 or payload.count(PLAN_END) != 1:
        raise AuditError("module plan array boundary differs")
    body = payload.split(PLAN_BEGIN, 1)[1].split(PLAN_END, 1)[0]
    pattern = re.compile(rb'^    \{"([^"\\]+)", "([^"\\]+)", "([^"\\]*)"\},$')
    rows: list[tuple[str, str, str]] = []
    for line in body.splitlines():
        match = pattern.fullmatch(line)
        if match is None:
            raise AuditError("module plan row grammar differs")
        rows.append(tuple(item.decode("ascii") for item in match.groups()))
    if (
        not rows
        or len({row[0] for row in rows}) != len(rows)
        or len({row[1] for row in rows}) != len(rows)
        or any(row[2] for row in rows)
    ):
        raise AuditError("module plan identity or uniqueness differs")
    return rows


def derive_eud_index(rows: list[tuple[str, str, str]]) -> int:
    matches = [index for index, row in enumerate(rows) if row == EUD_IDENTITY]
    if len(matches) != 1:
        raise AuditError("module plan must contain one exact EUD identity")
    return matches[0]


def transform_plan(base: bytes) -> bytes:
    rows = parse_plan(base)
    if len(rows) != 70 or rows[-1] != ("i2c-msm-geni.ko", "i2c_msm_geni", ""):
        raise AuditError("P3.18 plan shape differs")
    successor = rows + list(ADDITIONS)
    if len(successor) != 73 or len({row[0] for row in successor}) != 73:
        raise AuditError("successor plan count or uniqueness differs")
    eud_index = derive_eud_index(successor)
    addition_bytes = b"".join(
        f'    {{"{filename}", "{runtime}", "{params}"}},\n'.encode("ascii")
        for filename, runtime, params in ADDITIONS
    )
    value = _replace_once(base, PLAN_END, addition_bytes + PLAN_END, "plan append")
    count_anchor = (
        b"#define S22PLUS_O2_MODULE_PLAN_COUNT \\\n"
        b"    (sizeof(s22plus_o2_module_plan) / sizeof(s22plus_o2_module_plan[0]))\n"
    )
    derived = count_anchor + (
        f"\n#define S22PLUS_O2_EUD_MODULE_INDEX {eud_index}U\n".encode("ascii")
    )
    return _replace_once(value, count_anchor, derived, "plan-derived EUD index")


def transform_runtime(base: bytes) -> bytes:
    return _replace_once(
        base,
        b"#define P307_EUD_MODULE_INDEX 37U\n",
        b"",
        "stale EUD runtime literal",
    )


def transform_wrapper(base: bytes) -> bytes:
    value = _replace_once(
        base,
        b'_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 70U, "P3.18 early module count");',
        b'_Static_assert(S22PLUS_O2_MODULE_PLAN_COUNT == 73U, "P3.19 successor module count");',
        "module count assertion",
    )
    include = b'#include "s22plus_fyg8_p290_e3_runtime.inc.c"\n'
    helper = include + b"""

static long p319_after_module_load(size_t index) {
    return index == S22PLUS_O2_EUD_MODULE_INDEX
        ? p307_read_eud_cache()
        : 0;
}
"""
    value = _replace_once(value, include, helper, "shared post-load helper")
    direct_old = b"""        E1_REQUIRE(
            S22_P241_MODULE_STAGE_BASE + (uint8_t)index,
            (uint8_t)index,
            p241_load_and_verify_module(index));
        if (index == P307_EUD_MODULE_INDEX) {
            long p307_eud_cache_rc = p307_read_eud_cache();
            if (p307_eud_cache_rc != 0) p290_fail_next(p307_eud_cache_rc);
        }
"""
    direct_new = b"""        E1_REQUIRE(
            S22_P241_MODULE_STAGE_BASE + (uint8_t)index,
            (uint8_t)index,
            p241_load_and_verify_module(index));
        long p319_post_load_rc = p319_after_module_load(index);
        if (p319_post_load_rc != 0) p290_fail_next(p319_post_load_rc);
"""
    value = _replace_once(value, direct_old, direct_new, "direct post-load hook")
    folded_anchor = b"""        if (p305_folded_load_rc != 0) {
            fail_at(
                S22_P241_MODULE_STAGE_BASE + P305_FOLDED_MODULE_INDEX,
                P305_FOLDED_MODULE_INDEX,
                (long)(P305_FOLDED_FAILURE_BASE + index));
        }
"""
    folded_new = folded_anchor + b"""        long p319_post_load_rc = p319_after_module_load(index);
        if (p319_post_load_rc != 0) p290_fail_next(p319_post_load_rc);
"""
    return _replace_once(value, folded_anchor, folded_new, "folded post-load hook")


def materialized_bytes(base: dict[str, bytes]) -> dict[str, bytes]:
    result = dict(base)
    result[PLAN_NAME] = transform_plan(base[PLAN_NAME])
    result[WRAPPER_NAME] = transform_wrapper(base[WRAPPER_NAME])
    result[RUNTIME_NAME] = transform_runtime(base[RUNTIME_NAME])
    changed = {name for name in result if result[name] != base[name]}
    if changed != CHANGED_SOURCES:
        raise AuditError(f"materialized source delta differs: {sorted(changed)}")
    return result


@dataclass(frozen=True)
class Section:
    name: str
    offset: int
    size: int
    link: int
    entry_size: int


@dataclass(frozen=True)
class Symbol:
    name: str
    info: int
    section_index: int
    value: int
    size: int


class Elf64:
    """Minimal little-endian ELF64 symbol/RELA reader for the four modules."""

    def __init__(self, payload: bytes, label: str):
        if (
            len(payload) < 64
            or payload[:6] != b"\x7fELF\x02\x01"
            or struct.unpack_from("<H", payload, 18)[0] != 183
        ):
            raise AuditError(f"{label} is not AArch64 ELF64")
        self.payload = payload
        self.label = label
        shoff = struct.unpack_from("<Q", payload, 0x28)[0]
        shentsize, shnum, shstrndx = struct.unpack_from("<HHH", payload, 0x3A)
        if shentsize != 64 or shnum == 0 or shstrndx >= shnum:
            raise AuditError(f"{label} section table differs")
        raw = []
        for index in range(shnum):
            start = shoff + index * shentsize
            if start + shentsize > len(payload):
                raise AuditError(f"{label} section table is truncated")
            raw.append(struct.unpack_from("<IIQQQQIIQQ", payload, start))
        string_row = raw[shstrndx]
        strings = payload[string_row[4] : string_row[4] + string_row[5]]

        def cstring(data: bytes, offset: int) -> str:
            end = data.find(b"\0", offset)
            if offset >= len(data) or end < 0:
                raise AuditError(f"{label} string table differs")
            return data[offset:end].decode("ascii")

        self.sections = [
            Section(cstring(strings, row[0]), row[4], row[5], row[6], row[9])
            for row in raw
        ]
        self._cstring = cstring

    def section(self, name: str) -> bytes:
        matches = [row for row in self.sections if row.name == name]
        if len(matches) != 1:
            raise AuditError(f"{self.label} section {name} differs")
        row = matches[0]
        if row.offset + row.size > len(self.payload):
            raise AuditError(f"{self.label} section {name} is truncated")
        return self.payload[row.offset : row.offset + row.size]

    def symbols(self) -> list[Symbol]:
        matches = [(index, row) for index, row in enumerate(self.sections) if row.name == ".symtab"]
        if len(matches) != 1:
            raise AuditError(f"{self.label} symbol table differs")
        _index, row = matches[0]
        if row.entry_size != 24 or row.link >= len(self.sections):
            raise AuditError(f"{self.label} symbol metadata differs")
        string_row = self.sections[row.link]
        strings = self.payload[string_row.offset : string_row.offset + string_row.size]
        data = self.payload[row.offset : row.offset + row.size]
        result = []
        for offset in range(0, len(data), 24):
            name, info, _other, section_index, value, size = struct.unpack_from(
                "<IBBHQQ", data, offset
            )
            result.append(
                Symbol(self._cstring(strings, name), info, section_index, value, size)
            )
        return result

    def relocations(self, section_name: str) -> list[tuple[int, int, str]]:
        rows = [row for row in self.sections if row.name == section_name]
        if len(rows) != 1 or rows[0].entry_size != 24:
            raise AuditError(f"{self.label} relocation section differs")
        symbols = self.symbols()
        data = self.payload[rows[0].offset : rows[0].offset + rows[0].size]
        result = []
        for offset in range(0, len(data), 24):
            address, info, _addend = struct.unpack_from("<QQq", data, offset)
            symbol_index = info >> 32
            if symbol_index >= len(symbols):
                raise AuditError(f"{self.label} relocation symbol differs")
            result.append((address, info & 0xFFFFFFFF, symbols[symbol_index].name))
        return result


def modinfo(payload: bytes, label: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for item in Elf64(payload, label).section(".modinfo").split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        name = key.decode("ascii")
        values.setdefault(name, []).append(value.decode("ascii"))
    return values


def audit_provider_elf(modules: dict[str, bytes]) -> dict[str, Any]:
    dwc3 = Elf64(modules["dwc3-msm.ko"], "dwc3-msm.ko")
    pdic = Elf64(modules["pdic_max77705.ko"], "pdic_max77705.ko")
    dwc3_symbols = dwc3.symbols()
    pdic_symbols = pdic.symbols()

    provider = [row for row in dwc3_symbols if row.name == "dwc3_restart_usb_host_mode"]
    ksym = [row for row in dwc3_symbols if row.name == "__ksymtab_dwc3_restart_usb_host_mode"]
    if (
        len(provider) != 1
        or provider[0].section_index == 0
        or provider[0].info >> 4 != 1
        or provider[0].info & 0xF != 2
        or len(ksym) != 1
        or ksym[0].section_index == 0
        or b"dwc3_restart_usb_host_mode\0" not in dwc3.section("__ksymtab_strings")
    ):
        raise AuditError("exact dwc3-msm provider export differs")

    imports = [row for row in pdic_symbols if row.name == "dwc3_restart_usb_host_mode"]
    enclosing = [row for row in pdic_symbols if row.name == "max77705_vdm_dp_select_pin"]
    relocs = [
        row
        for row in pdic.relocations(".rela.text.max77705_ccic_event_work")
        if row[2] == "dwc3_restart_usb_host_mode"
    ]
    if (
        len(imports) != 1
        or imports[0].section_index != 0
        or len(enclosing) != 1
        or len(relocs) != 1
        or relocs[0][:2] != (0x12318, 283)
        or not enclosing[0].value <= relocs[0][0] < enclosing[0].value + enclosing[0].size
    ):
        raise AuditError("exact pdic/DWC3 import relocation differs")
    return {
        "exported_symbol": "dwc3_restart_usb_host_mode",
        "provider_module": "dwc3-msm.ko",
        "consumer_module": "pdic_max77705.ko",
        "relocation_type": "R_AARCH64_CALL26",
        "relocation_offset": "0x12318",
        "enclosing_function": "max77705_vdm_dp_select_pin",
        "provider_export_present": True,
        "consumer_import_count": 1,
        "consumer_relocation_count": 1,
    }


def audit_module_metadata(
    modules: dict[str, bytes], rows: list[tuple[str, str, str]]
) -> dict[str, Any]:
    positions = {runtime: index for index, (_file, runtime, _params) in enumerate(rows)}
    result: dict[str, Any] = {}
    for filename, payload in sorted(modules.items()):
        info = modinfo(payload, filename)
        runtime = filename[:-3].replace("-", "_")
        expected_runtime = "dwc3_msm" if filename == "dwc3-msm.ko" else runtime
        names = info.get("name", [])
        vermagics = info.get("vermagic", [])
        depends_rows = info.get("depends", [])
        if (
            names != [expected_runtime]
            or vermagics != [VERMAGIC]
            or len(depends_rows) != 1
        ):
            raise AuditError(f"{filename} name or vermagic differs")
        dependencies = tuple(item for item in depends_rows[0].split(",") if item)
        if expected_runtime not in positions:
            raise AuditError(f"{filename} is absent from materialized plan")
        normalized_dependencies = tuple(item.replace("-", "_") for item in dependencies)
        missing_or_late = [
            item
            for item in normalized_dependencies
            if item not in positions or positions[item] >= positions[expected_runtime]
        ]
        if missing_or_late:
            raise AuditError(f"{filename} has absent or late dependencies")
        result[filename] = {
            **identity(payload),
            "runtime_name": expected_runtime,
            "plan_index": positions[expected_runtime],
            "depends": list(dependencies),
            "dependencies_precede_module": True,
            "vermagic": vermagics[0],
        }
    return result


def audit_v2(value: Any) -> dict[str, Any]:
    try:
        plan = value["successor_plan"]
        eud = plan["eud_trigger"]
        additions = plan["incremental_entries"]
    except (KeyError, TypeError) as exc:
        raise AuditError("V2 receipt shape differs") from exc
    if (
        value.get("schema") != "s22plus-fyg8-p319-successor-module-plan-v2"
        or value.get("verdict") != "PASS_P319_SUCCESSOR_MODULE_PLAN_V2_H0"
        or value.get("status") != "IMPLEMENTED_REVIEW_PENDING"
        or plan.get("successor_plan_count") != 73
        or [item.get("filename") for item in additions]
        != [item[0] for item in ADDITIONS]
        or eud.get("derived_index") != 38
        or eud.get("inherited_literal_index") != 37
        or eud.get("independent_runtime_index_literal_allowed") is not False
    ):
        raise AuditError("V2 derivation receipt differs")
    return {
        "receipt": identity(encode(value)),
        "successor_plan_count": 73,
        "incremental_count": 3,
        "derived_eud_index": 38,
        "review_commit": "f88b1cbdbf",
        "independent_review_confirmed_delta_and_index": True,
    }


def audit_p318_static(value: Any, dwc3_payload: bytes) -> dict[str, Any]:
    try:
        closure = value["candidate"]["module_closure"]
        matches = [row for row in closure["modules"] if row.get("file") == "dwc3-msm.ko"]
    except (KeyError, TypeError) as exc:
        raise AuditError("P3.18 static closure shape differs") from exc
    expected = {"file": "dwc3-msm.ko", "index": 58, **identity(dwc3_payload)}
    if (
        closure.get("count") != 69
        or len(matches) != 1
        or any(matches[0].get(key) != value for key, value in expected.items())
    ):
        raise AuditError("P3.18 dwc3-msm provider identity differs")
    return {
        "p318_stock_closure_count": 69,
        "p318_stock_closure_index": 58,
        "p318_effective_plan_index_after_latch": 59,
        "same_exact_dwc3_msm_bytes": True,
        **identity(dwc3_payload),
    }


def audit_materialized(
    base: dict[str, bytes], generated: dict[str, bytes]
) -> dict[str, Any]:
    expected = materialized_bytes(base)
    if generated != expected:
        raise AuditError("preserved successor materialization differs")
    rows = parse_plan(generated[PLAN_NAME])
    if len(rows) != 73 or tuple(rows[-3:]) != ADDITIONS:
        raise AuditError("materialized successor plan differs")
    eud_index = derive_eud_index(rows)
    plan = generated[PLAN_NAME]
    wrapper = generated[WRAPPER_NAME]
    runtime = generated[RUNTIME_NAME]
    index_match = re.findall(rb"^#define S22PLUS_O2_EUD_MODULE_INDEX ([0-9]+)U$", plan, re.MULTILINE)
    if index_match != [str(eud_index).encode("ascii")]:
        raise AuditError("materialized plan-derived EUD index differs")
    if b"P307_EUD_MODULE_INDEX" in runtime or b"P307_EUD_MODULE_INDEX" in wrapper:
        raise AuditError("stale EUD runtime literal survived materialization")
    helper = b"""static long p319_after_module_load(size_t index) {
    return index == S22PLUS_O2_EUD_MODULE_INDEX
        ? p307_read_eud_cache()
        : 0;
}
"""
    if wrapper.count(helper) != 1 or wrapper.count(b"p319_after_module_load(index);") != 2:
        raise AuditError("shared post-load helper or consumers differ")
    direct = wrapper.find(
        b"for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {"
    )
    folded = wrapper.find(b"for (size_t index = P305_FOLDED_MODULE_INDEX;")
    direct_load = wrapper.find(b"p241_load_and_verify_module(index));", direct)
    direct_hook = wrapper.find(b"p319_after_module_load(index);", direct)
    folded_load = wrapper.find(b"p241_load_and_verify_module(index);", folded)
    folded_failure = wrapper.find(b"if (p305_folded_load_rc != 0) {", folded)
    folded_hook = wrapper.find(b"p319_after_module_load(index);", folded)
    if not (
        0 <= direct < direct_load < direct_hook < folded
        and 0 <= folded < folded_load < folded_failure < folded_hook
    ):
        raise AuditError("direct or folded successful post-load order differs")
    return {
        "base_plan_count": 70,
        "successor_plan_count": 73,
        "changed_source_count": 3,
        "changed_sources": sorted(CHANGED_SOURCES),
        "unchanged_source_count": len(base) - len(CHANGED_SOURCES),
        "added_entries": [
            {"index": 70 + index, "filename": row[0], "runtime_name": row[1], "params": row[2]}
            for index, row in enumerate(ADDITIONS)
        ],
        "eud_identity": {
            "filename": EUD_IDENTITY[0],
            "runtime_name": EUD_IDENTITY[1],
            "params": EUD_IDENTITY[2],
            "derived_index": eud_index,
            "independent_runtime_literal_present": False,
        },
        "shared_post_load_helper_count": 1,
        "direct_loop_consumer_count": 1,
        "folded_loop_consumer_count": 1,
        "both_consumers_follow_successful_load": True,
        "materialized_sources": {
            name: identity(payload) for name, payload in sorted(generated.items())
        },
    }


def syntax_compile(source_root: Path) -> dict[str, Any]:
    compiler = shutil.which("aarch64-linux-gnu-gcc")
    if compiler is None:
        raise AuditError("AArch64 compiler is unavailable")
    compiler_path = Path(compiler).resolve(strict=True)
    define = "{" + ",".join(f"0x{value:02x}" for value in RUN_ID) + "}"
    environment = {
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", ""),
        "SOURCE_DATE_EPOCH": "0",
    }
    command = [
        str(compiler_path),
        "-nostdlib",
        "-ffreestanding",
        "-fno-builtin",
        "-fno-stack-protector",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-fsyntax-only",
        "-DS22PLUS_FYG8_P233_PROFILE=3",
        f"-DS22PLUS_FYG8_P233_RUN_ID_BYTES={define}",
        "-I",
        str(source_root),
        "-I",
        str(ROOT / "workspace/public/src/native-init"),
        str(source_root / WRAPPER_NAME),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0 or completed.stdout or completed.stderr:
        detail = (completed.stdout + completed.stderr).decode("utf-8", "replace")
        raise AuditError(f"materialized runtime syntax check failed: {detail[-2000:]}")
    compiler_payload = stable_bytes(
        compiler_path, label="AArch64 compiler", maximum=16 << 20
    )
    return {
        "compiler": {"basename": compiler_path.name, **identity(compiler_payload)},
        "profile": 3,
        "run_id": RUN_ID.hex(),
        "syntax_only": True,
        "returncode": 0,
    }


def _paths(output_root: Path) -> dict[str, Path]:
    return {
        "root": output_root,
        "inputs": output_root / "inputs",
        "sources": output_root / "materialized-sources",
        "modules": output_root / "module-bytes",
        "stock": output_root / "stock-comparison",
        "result": output_root / "result.json",
    }


def _create_output(output_root: Path) -> dict[str, Path]:
    paths = _paths(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("successor materialization output already exists")
    _mkdir(output_root)
    for key in ("inputs", "sources", "modules", "stock"):
        _mkdir(paths[key])
    for key in ("inputs", "sources", "modules", "stock", "root"):
        _fsync_directory(paths[key])
    _fsync_directory(output_root.parent)
    return paths


def _load_base_sources() -> dict[str, bytes]:
    return {
        name: stable_bytes(
            P318_SOURCES / name,
            label=f"P3.18 materialized source {name}",
            maximum=spec.maximum,
            expected_size=spec.size,
            expected_sha256=spec.sha256,
            required_mode=0o400,
            required_nlink=1,
        )
        for name, spec in P318_SOURCE_SPECS.items()
    }


def write_bundle(output_root: Path) -> None:
    base = _load_base_sources()
    generated = materialized_bytes(base)
    v2 = stable_bytes(
        V2_RECEIPT,
        label="V2 derivation receipt",
        maximum=V2_SPEC.maximum,
        expected_size=V2_SPEC.size,
        expected_sha256=V2_SPEC.sha256,
        required_mode=0o400,
        required_nlink=1,
    )
    p318_static = stable_bytes(
        P318_STATIC,
        label="P3.18 static closure",
        maximum=P318_STATIC_SPEC.maximum,
        expected_size=P318_STATIC_SPEC.size,
        expected_sha256=P318_STATIC_SPEC.sha256,
        required_mode=0o400,
        required_nlink=1,
    )
    ramdisk: dict[str, bytes] = {}
    stock: dict[str, bytes] = {}
    for name, spec in MODULE_SPECS.items():
        ramdisk[name] = stable_bytes(
            VENDOR_RAMDISK_MODULES / name,
            label=f"vendor_boot ramdisk {name}",
            maximum=spec.maximum,
            expected_size=spec.size,
            expected_sha256=spec.sha256,
        )
        stock[name] = stable_bytes(
            VENDOR_DLKM_MODULES / name,
            label=f"vendor_dlkm {name}",
            maximum=spec.maximum,
            expected_size=spec.size,
            expected_sha256=spec.sha256,
        )
        if ramdisk[name] != stock[name]:
            raise AuditError(f"vendor_boot/vendor_dlkm module bytes differ: {name}")
    for name in ("mfd_max77705.ko", "pdic_max77705.ko"):
        prior = stable_bytes(
            PRIOR_IRQ_INPUTS / name,
            label=f"prior symbol-analysis {name}",
            maximum=MODULE_SPECS[name].maximum,
            expected_size=MODULE_SPECS[name].size,
            expected_sha256=MODULE_SPECS[name].sha256,
            required_mode=0o400,
            required_nlink=1,
        )
        if prior != ramdisk[name]:
            raise AuditError(f"prior symbol-analysis bytes differ: {name}")
    paths = _create_output(output_root)
    _write_exclusive(paths["inputs"] / "successor-module-plan-v2.json", v2)
    _write_exclusive(paths["inputs"] / "p318-static-check-result.json", p318_static)
    for name, payload in generated.items():
        _write_exclusive(paths["sources"] / name, payload)
    for name, payload in ramdisk.items():
        _write_exclusive(paths["modules"] / name, payload)
    for name, payload in stock.items():
        _write_exclusive(paths["stock"] / name, payload)
    for key in ("inputs", "sources", "modules", "stock", "root"):
        _fsync_directory(paths[key])


def load_bundle(output_root: Path) -> dict[str, Any]:
    paths = _paths(output_root)
    base = _load_base_sources()
    expected = materialized_bytes(base)
    generated = {
        name: stable_bytes(
            paths["sources"] / name,
            label=f"preserved materialized source {name}",
            maximum=max(P318_SOURCE_SPECS[name].maximum, len(expected[name])),
            required_mode=0o400,
            required_nlink=1,
        )
        for name in P318_SOURCE_SPECS
    }
    v2 = stable_bytes(
        paths["inputs"] / "successor-module-plan-v2.json",
        label="preserved V2 receipt",
        maximum=V2_SPEC.maximum,
        expected_size=V2_SPEC.size,
        expected_sha256=V2_SPEC.sha256,
        required_mode=0o400,
        required_nlink=1,
    )
    p318_static = stable_bytes(
        paths["inputs"] / "p318-static-check-result.json",
        label="preserved P3.18 static closure",
        maximum=P318_STATIC_SPEC.maximum,
        expected_size=P318_STATIC_SPEC.size,
        expected_sha256=P318_STATIC_SPEC.sha256,
        required_mode=0o400,
        required_nlink=1,
    )
    modules: dict[str, bytes] = {}
    stock: dict[str, bytes] = {}
    for name, spec in MODULE_SPECS.items():
        modules[name] = stable_bytes(
            paths["modules"] / name,
            label=f"preserved candidate module {name}",
            maximum=spec.maximum,
            expected_size=spec.size,
            expected_sha256=spec.sha256,
            required_mode=0o400,
            required_nlink=1,
        )
        stock[name] = stable_bytes(
            paths["stock"] / name,
            label=f"preserved stock comparison {name}",
            maximum=spec.maximum,
            expected_size=spec.size,
            expected_sha256=spec.sha256,
            required_mode=0o400,
            required_nlink=1,
        )
        if modules[name] != stock[name]:
            raise AuditError(f"preserved module copies differ: {name}")
    return {
        "paths": paths,
        "base": base,
        "generated": generated,
        "v2": v2,
        "p318_static": p318_static,
        "modules": modules,
        "stock": stock,
    }


def build_result(bundle: dict[str, Any]) -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise AuditError("unbound materializer cannot build an authoritative result")
    materialization = audit_materialized(bundle["base"], bundle["generated"])
    rows = parse_plan(bundle["generated"][PLAN_NAME])
    module_metadata = audit_module_metadata(bundle["modules"], rows)
    provider = audit_provider_elf(bundle["modules"])
    v2 = audit_v2(strict_json(bundle["v2"], "V2 receipt"))
    p318 = audit_p318_static(
        strict_json(bundle["p318_static"], "P3.18 static closure"),
        bundle["modules"]["dwc3-msm.ko"],
    )
    syntax = syntax_compile(bundle["paths"]["sources"])
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": "IMPLEMENTED_REVIEW_PENDING",
        "target": TARGET,
        "scope": {
            "host_only": True,
            "device_contact": False,
            "adb_commands": 0,
            "usb_actions": 0,
            "odin_invocations": 0,
            "candidate_transfers": 0,
            "rollback_transfers": 0,
            "recovery_actions": 0,
            "replay": False,
            "live_authority_created": False,
        },
        "inputs": {
            "v2_derivation_receipt": identity(bundle["v2"]),
            "p318_static_closure": identity(bundle["p318_static"]),
            "p318_materialized_sources": {
                name: identity(payload) for name, payload in sorted(bundle["base"].items())
            },
        },
        "implementation": {"auditor": identity(_BOUND_AUDITOR_SOURCE)},
        "v2_derivation": v2,
        "materialization": materialization,
        "module_bytes": {
            "candidate_source": "FYG8 vendor_boot ramdisk lib/modules",
            "stock_comparison_source": "FYG8 vendor_dlkm lib/modules",
            "candidate_and_stock_copies_byte_identical": True,
            "modules": module_metadata,
            "prior_mfd_pdic_symbol_analysis_snapshots_match": True,
        },
        "p318_dwc3_provider_binding": p318,
        "pdic_dwc3_symbol_edge": provider,
        "static_validation": syntax,
        "conclusion": {
            "successor_plan_header_materialized": True,
            "successor_runtime_hook_materialized": True,
            "added_module_binary_identities_frozen": True,
            "existing_dwc3_provider_binary_identity_frozen": True,
            "dwc3_restart_usb_host_mode_export_present_in_bound_provider": True,
            "independent_eud_runtime_index_literal_removed": True,
            "shared_post_load_hook_covers_direct_and_folded_loops": True,
            "candidate_userspace_built": False,
            "candidate_boot_built": False,
            "candidate_packaged": False,
            "parser_qualified": False,
            "candidate_build_qualified": False,
            "symbol_stub_authorized": False,
            "independent_review_required": True,
            "next_step": (
                "independently review this exact materialization, then derive a new "
                "candidate intent/build closure and qualify the bounded live-kmsg parser"
            ),
        },
    }
    if stable_bytes(AUDITOR, label="post-run auditor", maximum=1 << 20) != _BOUND_AUDITOR_SOURCE:
        raise AuditError("materializer changed during execution")
    return result


def encode(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def publish_result(output_root: Path, payload: bytes) -> None:
    paths = _paths(output_root)
    _write_exclusive(paths["result"], payload)
    _fsync_directory(output_root)
    existing = stable_bytes(
        paths["result"],
        label="successor materialization receipt",
        maximum=256 << 10,
        expected_size=len(payload),
        expected_sha256=sha256(payload),
        required_mode=0o400,
        required_nlink=1,
    )
    if existing != payload:
        raise AuditError("successor materialization receipt differs")


def run(output_root: Path, materialize: bool) -> tuple[dict[str, Any], bytes]:
    if materialize:
        write_bundle(output_root)
    bundle = load_bundle(output_root)
    result = build_result(bundle)
    return result, encode(result)


def load_bound_auditor() -> Any:
    payload = stable_bytes(AUDITOR, label="materializer bootstrap", maximum=1 << 20)
    module = types.ModuleType("s22plus_fyg8_p319_successor_module_materialization_bound")
    module.__file__ = str(AUDITOR)
    module.__package__ = ""
    module.__dict__["_P319_MATERIALIZER_BOUND_SOURCE"] = payload
    sys.modules[module.__name__] = module
    try:
        code = compile(payload.decode("utf-8"), str(AUDITOR), "exec", dont_inherit=True)
        exec(code, module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("materializer bound execution failed") from exc
    return module


def main() -> int:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        return load_bound_auditor().main()
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--audit-only", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    output_root = args.output_root.absolute()
    _, payload = run(output_root, materialize=args.write)
    if args.write:
        publish_result(output_root, payload)
    else:
        existing = stable_bytes(
            _paths(output_root)["result"],
            label="successor materialization receipt",
            maximum=256 << 10,
            expected_size=len(payload),
            expected_sha256=sha256(payload),
            required_mode=0o400,
            required_nlink=1,
        )
        if existing != payload:
            raise AuditError("successor materialization receipt differs")
    print(f"{VERDICT} {len(payload)} {sha256(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
