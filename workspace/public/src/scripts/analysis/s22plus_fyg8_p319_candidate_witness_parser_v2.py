#!/usr/bin/env python3
"""Qualify the P3.19 source-bound kmsg witness/parser predecessor.

This is an H0-only successor of the exact 73-row P3.19 materialization.  It
binds the two driver translation units, the logging header that expands
``msg_maxim``, and the exact PDIC module before deriving the four witness
grammars (including both classification call sites).  It transforms a fresh
copy of the materialized runtime so every successful module load has one
bounded ``/dev/kmsg`` drain in both module-loop forms.

The structured result is an explicitly versioned host-qualified summary
state.  It has no canonical byte encoding yet: that is separate Carrier /
Envelope-v5 work.  It is deliberately not a Carrier publication and does not
reinterpret Envelope-v4.  The existing candidate-witness transport
obligation therefore remains review-pending.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import tempfile
import types
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[5]
AUDITOR = Path(__file__).resolve()
PRIVATE = ROOT / "workspace/private"
BASE_ROOT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/"
    "successor-module-materialization-v1-20260820-04"
)
BASE_SOURCES = BASE_ROOT / "materialized-sources"
BASE_RECEIPT = BASE_ROOT / "result.json"
BASE_MODULES = BASE_ROOT / "module-bytes"
DRIVER_ROOT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/max77705-irq-dt-audit-20260820-05/inputs"
)
KERNEL_SOURCE_ROOT = PRIVATE / (
    "work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel"
)
MUIC_GUARD_ROOT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/pdic-muic-guard-audit-20260820-02/inputs"
)
CORPUS_MANIFEST = DRIVER_ROOT / "abl-capture-manifest.json"
CORPUS_CAPTURE = ROOT / (
    "workspace/private/runs/s22plus_v3443_high_panic_20260711T014605Z/"
    "post_recovery_last_kmsg.bin"
)
OUTPUT_ROOT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/"
    "successor-witness-parser-v2-20260820-14"
)

SCHEMA = "s22plus-fyg8-p319-candidate-witness-parser-v2"
VERDICT = "PASS_P319_CANDIDATE_WITNESS_PARSER_PREDECESSOR_H0"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
SUMMARY_STATE = "s22plus-fyg8-p319-witness-summary-state-v1"

MAX_RECORD_BYTES = 4_096
MAX_DRAIN_RECORDS = 256
MAX_DRAIN_BYTES = 262_144
MAX_TOTAL_RECORDS = 4_096
# This is an execution-resource ceiling for the candidate observer.  It is
# independent of the stock sec_log FIFO (whose size was explicitly withdrawn
# as a transferable budget); it is four per-drain byte ceilings.
MAX_TOTAL_BYTES = 1_048_576
MAX_MODULES = 73

BASE_RECEIPT_SIZE = 10_658
BASE_RECEIPT_SHA256 = "8b8c1f5afd8c02693901d3552c221bcc73bafa2543c77dfff4954bdba188f6b5"
PDIC_MODULE_SIZE = 423_456
PDIC_MODULE_SHA256 = "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db"


class AuditError(RuntimeError):
    """An exact input, parser, transform, or publication property differs."""


_BOUND_AUDITOR_SOURCE = globals().get("_P319_WITNESS_PARSER_BOUND_SOURCE")


@dataclass(frozen=True)
class FileSpec:
    source: Path
    snapshot: str
    size: int
    sha256: str
    maximum: int


SOURCE_SPECS: dict[str, FileSpec] = {
    "max77705_usbc.c": FileSpec(
        DRIVER_ROOT / "max77705_usbc.c", "max77705_usbc.c", 124_569,
        "4dabc4b25e99e26c662748934a6a98775073683832f08652e15762f4689a3e3d", 256 << 10,
    ),
    "max77705-muic.c": FileSpec(
        DRIVER_ROOT / "max77705-muic.c", "max77705-muic.c", 76_141,
        "bfdb034d7571ca233202221cdc8cdfe68bab3e837afea9c4b5a37378ed7acbab", 128 << 10,
    ),
    "maxim-Makefile": FileSpec(
        KERNEL_SOURCE_ROOT / "drivers/usb/typec/maxim/Makefile", "maxim-Makefile", 450,
        "8055a9480971e835edccb441ce0554940a1d211be5bc1d1702ebc4587580c91d", 8 << 10,
    ),
    # The msg_maxim macro is in the USBC header.  The paired max77705.h is
    # also bound to retain the exact archive member named by the source audit.
    "max77705_usbc.h": FileSpec(
        MUIC_GUARD_ROOT / "max77705_usbc.h", "max77705_usbc.h", 10_072,
        "1cc7e211c50685c3eed3d1b4582869d0a65a559a2114c0087fac2646f4fc883e", 16 << 10,
    ),
    "max77705.h": FileSpec(
        KERNEL_SOURCE_ROOT / "include/linux/usb/typec/maxim/max77705.h", "max77705.h", 13_686,
        "ff2498061ddb20c1891cb9fe6611edde655c3e1cda8fa4446d0c876a476ff1c7", 16 << 10,
    ),
    "printk.c": FileSpec(
        KERNEL_SOURCE_ROOT / "kernel/printk/printk.c", "printk.c", 91_182,
        "eabf2acf23694f94b973981d684037556f62cbc74583907f087019d35d0acd3a", 128 << 10,
    ),
    "abl-capture-manifest.json": FileSpec(
        CORPUS_MANIFEST, "abl-capture-manifest.json", 107_997,
        "aa2d19ea09d3317dcff9961ee51eec579d7e912f4b98115fa5bf7994fff16f90", 128 << 10,
    ),
    "corpus-capture.bin": FileSpec(
        CORPUS_CAPTURE, "corpus-capture.bin", 2_097_136,
        "1ad451372ad5bf72fab681656249f07b4451df3255bd3a642759c4cbf5297df1", 2_097_136,
    ),
}


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns,
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
        direct != resolved or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode) or before.st_nlink < 1
        or len(payload) != before.st_size or len(payload) > maximum
        or _stat_identity(before) != _stat_identity(inside)
        or _stat_identity(before) != _stat_identity(after)
        or expected_size is not None and len(payload) != expected_size
        or expected_sha256 is not None and sha256(payload) != expected_sha256
        or required_mode is not None and stat.S_IMODE(before.st_mode) != required_mode
        or required_nlink is not None and before.st_nlink != required_nlink
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _mkdir(path: Path) -> None:
    os.mkdir(path, 0o700)
    os.chmod(path, 0o700)


def _write_exclusive(path: Path, payload: bytes, mode: int = 0o400) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode
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
            not stat.S_ISREG(state.st_mode) or stat.S_IMODE(state.st_mode) != mode
            or state.st_nlink != 1 or state.st_size != len(payload)
        ):
            raise AuditError(f"published file metadata differs: {path.name}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def strict_json(payload: bytes, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise AuditError(f"{label} has duplicate key {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise AuditError(f"{label} has non-finite JSON constant {value}")

    try:
        return json.loads(
            payload.decode("ascii"), object_pairs_hook=pairs,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc


def audit_capture_manifest(manifest: bytes) -> dict[str, Any]:
    """Bind the exact corpus index row used by the host qualification."""
    value = strict_json(manifest, "ABL capture manifest")
    if not isinstance(value, dict) or value.get("schema") != "s22plus-fyg8-p319-abl-capture-manifest-v3":
        raise AuditError("ABL capture manifest schema differs")
    captures = value.get("captures")
    if not isinstance(captures, list):
        raise AuditError("ABL capture manifest captures is not a list")
    selected_sha = "1ad451372ad5bf72fab681656249f07b4451df3255bd3a642759c4cbf5297df1"
    selected_path = (
        "workspace/private/runs/s22plus_v3443_high_panic_20260711T014605Z/"
        "post_recovery_last_kmsg.bin"
    )
    matches = [
        row for row in captures
        if isinstance(row, dict) and row.get("sha256") == selected_sha
    ]
    if len(matches) != 1 or matches[0].get("paths") != [selected_path]:
        raise AuditError("selected corpus capture binding differs")
    if any(
        isinstance(row, dict) and selected_path in row.get("paths", [])
        for row in captures if row is not matches[0]
    ):
        raise AuditError("selected corpus path is duplicated in manifest")
    return {
        "schema": value["schema"],
        "capture_rows": len(captures),
        "selected_sha256": selected_sha,
        "selected_relative_path": selected_path,
        "selected_row_count": 1,
        "selected_row_bound": True,
    }


def _c_function_body(source: bytes, name: str) -> bytes:
    token = name.encode("ascii") + b"("
    offset = 0
    while True:
        start = source.find(token, offset)
        if start < 0:
            raise AuditError(f"function absent: {name}")
        open_paren = start + len(name)
        depth = 0
        close_paren = -1
        for index in range(open_paren, len(source)):
            if source[index] == ord("("):
                depth += 1
            elif source[index] == ord(")"):
                depth -= 1
                if depth == 0:
                    close_paren = index
                    break
        if close_paren < 0:
            raise AuditError(f"function signature truncated: {name}")
        cursor = close_paren + 1
        while cursor < len(source) and chr(source[cursor]).isspace():
            cursor += 1
        if cursor < len(source) and source[cursor] == ord("{"):
            depth = 1
            end = cursor + 1
            while end < len(source) and depth:
                if source[end] == ord("{"):
                    depth += 1
                elif source[end] == ord("}"):
                    depth -= 1
                end += 1
            if depth:
                raise AuditError(f"function body truncated: {name}")
            return source[start:end]
        offset = close_paren + 1


def _replace_once(payload: bytes, old: bytes, new: bytes, label: str) -> bytes:
    if payload.count(old) != 1:
        raise AuditError(f"{label} anchor differs")
    return payload.replace(old, new, 1)


def _replace_function(source: bytes, name: str, new_body: bytes) -> bytes:
    old = _c_function_body(source, name)
    return _replace_once(source, old, new_body, f"{name} function")


def audit_bound_driver_sources(inputs: dict[str, bytes]) -> dict[str, Any]:
    usbc = inputs["max77705_usbc.c"]
    muic = inputs["max77705-muic.c"]
    makefile = inputs["maxim-Makefile"]
    usbc_h = inputs["max77705_usbc.h"]
    max_h = inputs["max77705.h"]
    printk = inputs["printk.c"]
    pdic = inputs["pdic_max77705.ko"]
    if b"#define msg_maxim(format, args...)" not in usbc_h:
        raise AuditError("msg_maxim macro is not bound")
    macro = b'pr_info("max77705: %s: " format "\\n", __func__, ## args)'
    if usbc_h.count(macro) != 1 or b"#define DEBUG_MAX77705" not in usbc_h:
        raise AuditError("msg_maxim expansion differs")
    if len(max_h) != 13_686 or sha256(max_h) != SOURCE_SPECS["max77705.h"].sha256:
        raise AuditError("paired max77705.h archive member differs")
    printk_header = _c_function_body(printk, "info_print_ext_header")
    if (
        len(printk_header) != 508 or sha256(printk_header) != "b2c68903ad264d7ea2f6f7de5d29704ca8cc3442dfb7842791acb8412b2e37a5"
        or printk_header.count(b'"%u,%llu,%llu,%c%s;"') != 1
        or b"id & 0x80000000 ? 'C' : 'T'" not in printk_header
    ):
        raise AuditError("printk ext-header grammar differs")
    required = {
        "probe": (usbc, b'msg_maxim("probing Complete..");', "max77705_usbc_probe"),
        "irq": (muic, b'uiadc(%d), chgtyp(%d), dcdtmo(%d), vbadc(%d), vbusdet(%d)', "max77705_muic_irq_init"),
        "initial": (muic, b'USBC1:0x%02x, USBC2:0x%02x, BC:0x%02x\\n', "max77705_muic_detect_dev"),
        "classification_form1": (muic, b'vps table match found at i(%lu), %s', "max77705_muic_check_new_dev"),
        "classification_form2": (muic, b'(%d) vps table match found at i(%d), %s', "muic_lookup_vps_table"),
        "deferred": (muic, b'USBC1:0x%02x, USBC2:0x%02x, BC:0x%02x, CC0:0x%x, CC1:0x%x, PD0:0x%x, PD1:0x%x attached_dev:%d', "max77705_muic_print_reg_log"),
    }
    sites: dict[str, Any] = {}
    for key, (source, token, function) in required.items():
        if source.count(token) != 1:
            raise AuditError(f"{key} format multiplicity differs")
        body = _c_function_body(source, function)
        if token not in body:
            raise AuditError(f"{key} format escaped its source function")
        sites[key] = {"function": function, "format_sha256": sha256(token), "source_offset": source.index(token)}
    if b"pdic_max77705" not in pdic:
        raise AuditError("bound PDIC module identity lacks module name")
    if muic.count(b'#define pr_fmt(fmt) KBUILD_MODNAME ": " fmt') != 1:
        raise AuditError("MUIC pr_fmt prefix binding differs")
    if (
        makefile.count(b"obj-$(CONFIG_CCIC_MAX77705)\t\t+= pdic_max77705.o") != 1
        or makefile.count(b"pdic_max77705-$(CONFIG_MUIC_MAX77705) += max77705-muic.o") != 1
        or pdic.count(b"name=pdic_max77705\0") != 1
    ):
        raise AuditError("PDIC source-to-module attribution differs")
    return {
        "source_bound_before_grammar": True,
        "msg_maxim_prefix": "max77705: ",
        "muic_module_prefix": "pdic_max77705: ",
        "probe_prefix": "max77705: max77705_usbc_probe: ",
        "muic_prefix": "pdic_max77705: ",
        "muic_prefix_derivation": "pr_fmt KBUILD_MODNAME + exact Makefile membership + .modinfo name",
        "sites": sites,
        "initial_status_bytes": 3,
        "deferred_status_bytes": 7,
        "deferred_status_is_auxiliary_only": True,
        "source_max77705_h": identity(max_h),
        "source_max77705_usbc_h": identity(usbc_h),
        "source_printk": identity(printk),
        "kmsg_header_grammar": {
            "facility_level": "unsigned-decimal",
            "sequence": "unsigned-decimal-llu",
            "timestamp": "unsigned-decimal-llu",
            "flags": ["c", "-"],
            "caller": "optional ,caller=[CT][0-9]+",
            "dictionary_lines": "fail-closed (not parsed by this predecessor)",
        },
        "pdic_module": identity(pdic),
    }


@dataclass
class WitnessState:
    probe_count: int = 0
    irq_count: int = 0
    initial_status_count: int = 0
    class_form1_count: int = 0
    class_form2_count: int = 0
    deferred_status_count: int = 0
    malformed_count: int = 0
    status: tuple[int, int, int] | None = None
    irq: tuple[int, int, int, int, int] | None = None
    class_form1_index: int | None = None
    class_form1_name: str | None = None
    class_form2_attached_dev: int | None = None
    class_form2_index: int | None = None
    class_form2_name: str | None = None


def _parse_dec(text: str, *, signed: bool, maximum: int) -> int:
    if not text or (not signed and text.startswith("-")):
        raise ValueError("decimal grammar")
    if text.startswith("+"):
        raise ValueError("explicit plus sign")
    negative = text.startswith("-")
    digits = text[1:] if negative else text
    if not digits or (len(digits) > 1 and digits[0] == "0") or (negative and digits == "0"):
        raise ValueError("decimal leading zero")
    if not digits.isascii() or not digits.isdigit():
        raise ValueError("decimal digits")
    value = int(text, 10)
    minimum = -maximum - 1 if signed else 0
    if value < minimum or value > maximum:
        raise ValueError("decimal range")
    return value


def _parse_hex(text: str, *, width: int | None = None) -> int:
    if width is not None and len(text) != width:
        raise ValueError("hex width")
    if not text or (width is None and len(text) > 1 and text[0] == "0") \
            or any(char not in "0123456789abcdef" for char in text):
        raise ValueError("hex grammar")
    value = int(text, 16)
    if value > 0xFF:
        raise ValueError("hex range")
    return value


def _class_name(text: str) -> str:
    if (
        not text or len(text) > 64 or text[0] == " " or text[-1] == " "
        or any(not (0x20 <= ord(char) <= 0x7E) for char in text)
    ):
        raise ValueError("%s grammar")
    return text


def parse_witness_message(message: str, state: WitnessState | None = None) -> dict[str, Any] | None:
    """Parse one printk message using the exact source-derived callsite forms."""
    state = state if state is not None else WitnessState()
    known = (
        "max77705: max77705_usbc_probe",
        "pdic_max77705: max77705_muic_irq_init",
        "pdic_max77705: max77705_muic_detect_dev",
        "pdic_max77705: max77705_muic_check_new_dev",
        "pdic_max77705: muic_lookup_vps_table",
        "pdic_max77705: max77705_muic_print_reg_log",
    )
    if not message.startswith(known):
        return None
    try:
        if message.startswith("max77705: max77705_usbc_probe"):
            expected = "max77705: max77705_usbc_probe: probing Complete.."
            if not message.startswith("max77705: max77705_usbc_probe: probing"):
                return None
            if message != expected:
                raise ValueError("probe grammar")
            state.probe_count += 1
            return {"kind": "probe"}
        prefix = "pdic_max77705: "
        body = message[len(prefix):]
        if body.startswith("max77705_muic_irq_init"):
            if not body.startswith("max77705_muic_irq_init uiadc("):
                return None
            match = re.fullmatch(
                r"max77705_muic_irq_init uiadc\((-?\d+)\), chgtyp\((-?\d+)\), "
                r"dcdtmo\((-?\d+)\), vbadc\((-?\d+)\), vbusdet\((-?\d+)\)", body
            )
            if match is None:
                raise ValueError("irq grammar")
            values = tuple(_parse_dec(x, signed=True, maximum=2_147_483_647) for x in match.groups())
            state.irq_count += 1
            state.irq = values  # type: ignore[assignment]
            return {"kind": "irq", "values": values}
        if body.startswith("max77705_muic_detect_dev"):
            if not body.startswith("max77705_muic_detect_dev USBC1:"):
                return None
            match = re.fullmatch(
                r"max77705_muic_detect_dev USBC1:0x([0-9a-f]{2}), "
                r"USBC2:0x([0-9a-f]{2}), BC:0x([0-9a-f]{2})", body
            )
            if match is None:
                raise ValueError("initial status grammar")
            values = tuple(_parse_hex(x, width=2) for x in match.groups())
            state.initial_status_count += 1
            state.status = values  # type: ignore[assignment]
            return {"kind": "initial_status", "values": values}
        if body.startswith("max77705_muic_check_new_dev"):
            if not body.startswith("max77705_muic_check_new_dev vps table"):
                return None
            match = re.fullmatch(
                r"max77705_muic_check_new_dev vps table match found at i\((\d+)\), (.+)", body
            )
            if match is None:
                raise ValueError("classification form1 grammar")
            index = _parse_dec(match.group(1), signed=False, maximum=(1 << 64) - 1)
            name = _class_name(match.group(2))
            state.class_form1_count += 1
            state.class_form1_index = index
            state.class_form1_name = name
            return {"kind": "classification", "form": 1, "index": index, "name": name}
        if body.startswith("muic_lookup_vps_table"):
            if not body.startswith("muic_lookup_vps_table ("):
                return None
            match = re.fullmatch(
                r"muic_lookup_vps_table \((-?\d+)\) vps table match found at i\((\d+)\), (.+)", body
            )
            if match is None:
                raise ValueError("classification form2 grammar")
            attached = _parse_dec(match.group(1), signed=True, maximum=2_147_483_647)
            index = _parse_dec(match.group(2), signed=False, maximum=2_147_483_647)
            name = _class_name(match.group(3))
            state.class_form2_count += 1
            state.class_form2_attached_dev = attached
            state.class_form2_index = index
            state.class_form2_name = name
            return {"kind": "classification", "form": 2, "attached_dev": attached, "index": index, "name": name}
        if body.startswith("max77705_muic_print_reg_log"):
            if not body.startswith("max77705_muic_print_reg_log USBC1:"):
                return None
            match = re.fullmatch(
                r"max77705_muic_print_reg_log USBC1:0x([0-9a-f]{1,2}), USBC2:0x([0-9a-f]{1,2}), "
                r"BC:0x([0-9a-f]{1,2}), CC0:0x([0-9a-f]{1,2}), CC1:0x([0-9a-f]{1,2}), "
                r"PD0:0x([0-9a-f]{1,2}), PD1:0x([0-9a-f]{1,2}) attached_dev:(-?\d+)", body
            )
            if match is None:
                raise ValueError("deferred status grammar")
            registers = tuple(
                _parse_hex(x, width=2 if index < 3 else None)
                for index, x in enumerate(match.groups()[:7])
            )
            attached = _parse_dec(match.group(8), signed=True, maximum=2_147_483_647)
            state.deferred_status_count += 1
            return {"kind": "deferred_status", "registers": registers, "attached_dev": attached}
    except ValueError as exc:
        state.malformed_count += 1
        raise AuditError(str(exc)) from exc
    raise AuditError("known witness prefix fell through grammar")


def parse_kmsg_record(record: bytes, state: WitnessState | None = None) -> dict[str, Any] | None:
    """Parse one /dev/kmsg record; accounting happens before message grammar."""
    if not record or len(record) > MAX_RECORD_BYTES:
        raise AuditError("record length is outside the bounded positive range")
    first = record.find(b",")
    second = record.find(b",", first + 1) if first >= 0 else -1
    semicolon = record.find(b";", second + 1) if second >= 0 else -1
    if first < 0 or second < 0 or semicolon < 0 or not first < second < semicolon:
        raise AuditError("kmsg framing grammar")
    try:
        header = record[:semicolon].decode("ascii", "strict")
        header_match = re.fullmatch(
            r"([0-9]+),([0-9]+),([0-9]+),([c-])(?:,caller=([CT])([0-9]+))?",
            header,
        )
        if header_match is None:
            raise ValueError("kmsg extended header grammar")
        _parse_dec(header_match.group(1), signed=False, maximum=(1 << 32) - 1)
        sequence_text = header_match.group(2)
        _parse_dec(header_match.group(3), signed=False, maximum=(1 << 64) - 1)
        if header_match.group(5) is not None:
            _parse_dec(header_match.group(6), signed=False, maximum=(1 << 32) - 1)
        sequence = _parse_dec(sequence_text, signed=False, maximum=(1 << 64) - 1)
        body = record[semicolon + 1:]
        if not body.endswith(b"\n") or body[:-1].find(b"\n") >= 0:
            raise ValueError("kmsg record requires one terminal newline")
        body = body[:-1]
        message = body.decode("utf-8", "strict")
    except (UnicodeDecodeError, ValueError) as exc:
        raise AuditError(str(exc)) from exc
    return {"sequence": sequence, "message": message, "length": len(record), "state": state}


class BoundedTransport:
    def __init__(self) -> None:
        self.state = WitnessState()
        self.drains = 0
        self.module_loads = 0
        self.module_drains = 0
        self.total_records = 0
        self.total_bytes = 0
        self.first_sequence: int | None = None
        self.last_sequence: int | None = None
        self._previous_sequence: int | None = None
        self._drain_records = 0
        self._drain_bytes = 0
        self.active_module_index: int | None = None
        self.initial_chain_stage = 0
        self.initial_chain_complete = False
        self.initial_chain_ambiguous = False
        self.module_results: dict[int, dict[str, Any]] = {}

    def begin_drain(self) -> None:
        if self.drains >= (1 << 32) - 1:
            raise AuditError("drain counter overflow")
        self.drains += 1
        self._drain_records = 0
        self._drain_bytes = 0

    def observe(self, record: bytes) -> None:
        if not record or len(record) > MAX_RECORD_BYTES:
            raise AuditError("record length is outside the bounded positive range")
        if self._drain_records >= MAX_DRAIN_RECORDS:
            raise AuditError("per-drain record limit")
        if len(record) > MAX_DRAIN_BYTES - self._drain_bytes:
            raise AuditError("per-drain byte limit")
        if self.total_records >= MAX_TOTAL_RECORDS:
            raise AuditError("cumulative record limit")
        if len(record) > MAX_TOTAL_BYTES - self.total_bytes:
            raise AuditError("cumulative byte limit")
        self._drain_records += 1
        self._drain_bytes += len(record)
        self.total_records += 1
        self.total_bytes += len(record)
        parsed = parse_kmsg_record(record, self.state)
        sequence = parsed["sequence"]
        message = parsed["message"]
        witness = parse_witness_message(message, self.state)
        if witness is not None and (
            witness["kind"] in {"probe", "irq", "initial_status"}
            or (witness["kind"] == "classification" and witness.get("form") == 1)
        ):
            if self.active_module_index != 72:
                self.initial_chain_ambiguous = True
            else:
                stage = {"irq": 1, "initial_status": 2, "classification": 3, "probe": 4}[witness["kind"]]
                if stage == self.initial_chain_stage + 1:
                    self.initial_chain_stage = stage
                    if stage == 4:
                        self.initial_chain_complete = True
                else:
                    self.initial_chain_ambiguous = True
        if self.first_sequence is None:
            self.first_sequence = sequence
        elif self._previous_sequence == (1 << 64) - 1 or sequence != self._previous_sequence + 1:
            raise AuditError("kmsg sequence gap")
        self._previous_sequence = sequence
        self.last_sequence = sequence

    def observe_drain(self, records: Iterable[bytes]) -> None:
        self.begin_drain()
        for record in records:
            self.observe(record)

    def successful_module(self, index: int, name: str, result: int, records: Iterable[bytes]) -> None:
        if self.module_loads >= MAX_MODULES:
            raise AuditError("module accounting limit")
        if result != 0 or index in self.module_results:
            raise AuditError("module result identity")
        if index in (69, 71, 72):
            self.module_results[index] = {"index": index, "name": name, "result": result}
        self.module_loads += 1
        self.active_module_index = index
        self.observe_drain(records)
        self.module_drains += 1
        self.active_module_index = None

    def summary(self) -> dict[str, Any]:
        return {
            "state": SUMMARY_STATE,
            "module_loads": self.module_loads,
            "module_drains": self.module_drains,
            "drains": self.drains,
            "record_count": self.total_records,
            "record_bytes": self.total_bytes,
            "first_sequence": self.first_sequence,
            "last_sequence": self.last_sequence,
            "witness": {
                "probe_count": self.state.probe_count,
                "irq_count": self.state.irq_count,
                "initial_status_count": self.state.initial_status_count,
                "classification_form1_count": self.state.class_form1_count,
                "classification_form2_count": self.state.class_form2_count,
                "classification_form1_index": self.state.class_form1_index,
                "classification_form1_name": self.state.class_form1_name,
                "classification_form2_attached_dev": self.state.class_form2_attached_dev,
                "classification_form2_index": self.state.class_form2_index,
                "classification_form2_name": self.state.class_form2_name,
                "deferred_status_count": self.state.deferred_status_count,
                "malformed_count": self.state.malformed_count,
                "initial_status": self.state.status,
                "irq": self.state.irq,
                "classification_form1_index": self.state.class_form1_index,
                "classification_form1_name": self.state.class_form1_name,
                "classification_form2_attached_dev": self.state.class_form2_attached_dev,
                "classification_form2_index": self.state.class_form2_index,
                "classification_form2_name": self.state.class_form2_name,
            },
            "module_results": [self.module_results[index] for index in sorted(self.module_results)],
            "initial_chain_stage": self.initial_chain_stage,
            "initial_chain_complete": self.initial_chain_complete,
            "initial_chain_ambiguous": self.initial_chain_ambiguous,
        }


# This is the exact parser core inserted into the generated runtime.  Tests
# compile and execute this same source on host fixtures; it is not a Python
# imitation of candidate behavior.
P319_C_PARSER_SOURCE = r'''
#define P319_WITNESS_ABI_VERSION 1U
#define P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION 0x6020L
#define P319_DETAIL_WITNESS_COUNTER_OVERFLOW 0x6021L
#define P319_DETAIL_WITNESS_BOUNDARY 0x6022L
#define P319_WITNESS_MASK_PROBE (1U << 0U)
#define P319_WITNESS_MASK_IRQ (1U << 1U)
#define P319_WITNESS_MASK_INITIAL (1U << 2U)
#define P319_WITNESS_MASK_CLASS1 (1U << 3U)
#define P319_WITNESS_MASK_CLASS2 (1U << 4U)
#define P319_WITNESS_MASK_DEFERRED (1U << 5U)

struct p319_module_result_state_v1 {
    uint32_t index;
    int32_t result;
    uint8_t name_length;
    uint8_t valid;
    char name[64];
};

struct p319_witness_summary_state_v1 {
    uint32_t abi_version;
    uint32_t witness_mask;
    uint32_t probe_count;
    uint32_t irq_count;
    uint32_t initial_status_count;
    uint32_t classification_form1_count;
    uint32_t classification_form2_count;
    uint32_t deferred_status_count;
    uint32_t malformed_count;
    uint64_t classification_form1_index;
    uint64_t classification_form2_index;
    int32_t classification_form2_attached_dev;
    uint8_t classification_form1_name_length;
    uint8_t classification_form2_name_length;
    char classification_form1_name[64];
    char classification_form2_name[64];
    uint32_t module_loads;
    uint32_t module_drains;
    uint32_t drains;
    uint32_t initial_status[3];
    int32_t irq[5];
    uint64_t record_count;
    uint64_t record_bytes;
    uint64_t first_sequence;
    uint64_t last_sequence;
    uint8_t first_sequence_valid;
    uint8_t last_sequence_valid;
    uint8_t active_module_valid;
    uint8_t initial_chain_stage;
    uint8_t initial_chain_complete;
    uint8_t initial_chain_ambiguous;
    uint32_t active_module_index;
    uint32_t initial_chain_module_index;
    struct p319_module_result_state_v1 target_modules[3];
};

static struct p319_witness_summary_state_v1 g_p319_witness = {
    .abi_version = P319_WITNESS_ABI_VERSION,
};

static int p319_eq(const char *s, size_t n, const char *literal) {
    size_t length = cstr_len(literal);
    return length == n && p260_bytes_equal(s, literal, n);
}

static int p319_has(const char *s, size_t n, const char *literal) {
    size_t length = cstr_len(literal);
    return n >= length && p260_bytes_equal(s, literal, length);
}

static long p319_dec(
    const char *s, size_t n, uint64_t maximum, uint64_t *value) {
    if (s == NULL || value == NULL || n == 0U
        || (n > 1U && s[0] == '0')) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    uint64_t result = 0;
    for (size_t i = 0; i < n; ++i) {
        if (s[i] < '0' || s[i] > '9') return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
        uint64_t digit = (uint64_t)(s[i] - '0');
        if (result > (maximum - digit) / 10U) return -P319_DETAIL_WITNESS_COUNTER_OVERFLOW;
        result = result * 10U + digit;
    }
    *value = result;
    return 0;
}

static long p319_sdec(
    const char *s, size_t n, int64_t minimum, int64_t maximum, int64_t *value) {
    if (s == NULL || value == NULL || n == 0U) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    int negative = s[0] == '-';
    size_t offset = negative ? 1U : 0U;
    if (offset == n || (n - offset > 1U && s[offset] == '0')) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    uint64_t magnitude = 0;
    long rc = p319_dec(s + offset, n - offset, UINT64_MAX, &magnitude);
    if (rc != 0) return rc;
    if (negative && magnitude == 0U) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    if (negative) {
        if (magnitude > (uint64_t)INT64_MAX + 1U) return -P319_DETAIL_WITNESS_COUNTER_OVERFLOW;
        int64_t result = magnitude == (uint64_t)INT64_MAX + 1U ? INT64_MIN : -(int64_t)magnitude;
        if (result < minimum || result > maximum) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
        *value = result;
    } else {
        if (magnitude > (uint64_t)INT64_MAX || (int64_t)magnitude < minimum || (int64_t)magnitude > maximum) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
        *value = (int64_t)magnitude;
    }
    return 0;
}

static long p319_hex_byte(
    const char *s, size_t n, uint32_t *value, int exact_two) {
    if (s == NULL || value == NULL || n == 0U || (exact_two && n != 2U) ||
        (!exact_two && n > 1U && s[0] == '0') || n > 2U)
        return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    uint32_t result = 0;
    for (size_t i = 0; i < n; ++i) {
        unsigned int digit;
        if (s[i] >= '0' && s[i] <= '9') digit = (unsigned int)(s[i] - '0');
        else if (s[i] >= 'a' && s[i] <= 'f') digit = 10U + (unsigned int)(s[i] - 'a');
        else return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
        result = result * 16U + digit;
    }
    *value = result;
    return 0;
}

static long p319_take_literal(
    const char **cursor, const char *end, const char *literal) {
    size_t length = cstr_len(literal);
    if (cursor == NULL || *cursor == NULL || end == NULL || *cursor > end
        || (size_t)(end - *cursor) < length
        || !p260_bytes_equal(*cursor, literal, length)) {
        return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    }
    *cursor += length;
    return 0;
}

static long p319_take_decimal(
    const char **cursor, const char *end, uint64_t maximum, uint64_t *value) {
    const char *start = *cursor;
    while (*cursor < end && **cursor >= '0' && **cursor <= '9') ++*cursor;
    return p319_dec(start, (size_t)(*cursor - start), maximum, value);
}

static long p319_take_signed(
    const char **cursor, const char *end, int64_t minimum, int64_t maximum, int64_t *value) {
    const char *start = *cursor;
    if (*cursor < end && **cursor == '-') ++*cursor;
    while (*cursor < end && **cursor >= '0' && **cursor <= '9') ++*cursor;
    return p319_sdec(start, (size_t)(*cursor - start), minimum, maximum, value);
}

static long p319_take_hex(
    const char **cursor, const char *end, int exact_two, uint32_t *value) {
    const char *start = *cursor;
    while (*cursor < end && ((**cursor >= '0' && **cursor <= '9') || (**cursor >= 'a' && **cursor <= 'f'))) ++*cursor;
    return p319_hex_byte(start, (size_t)(*cursor - start), value, exact_two);
}

static __attribute__((unused)) long p319_kmsg_header(
    const char *record, size_t length, uint64_t *sequence,
    const char **message) {
    if (record == NULL || sequence == NULL || message == NULL) {
        return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    }
    const char *cursor = record;
    const char *end = record + length;
    uint64_t facility_level = 0;
    uint64_t timestamp = 0;
    long rc = p319_take_decimal(&cursor, end, UINT32_MAX, &facility_level);
    if (rc == 0) rc = p319_take_literal(&cursor, end, ",");
    if (rc == 0) rc = p319_take_decimal(&cursor, end, UINT64_MAX, sequence);
    if (rc == 0) rc = p319_take_literal(&cursor, end, ",");
    if (rc == 0) rc = p319_take_decimal(&cursor, end, UINT64_MAX, &timestamp);
    if (rc == 0) rc = p319_take_literal(&cursor, end, ",");
    if (rc == 0 && cursor < end && (*cursor == 'c' || *cursor == '-')) {
        ++cursor;
    } else if (rc == 0) {
        rc = -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    }
    if (rc == 0 && p319_has(cursor, (size_t)(end - cursor), ",caller=")) {
        cursor += cstr_len(",caller=");
        if (cursor >= end || (*cursor != 'C' && *cursor != 'T')) {
            rc = -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
        } else {
            ++cursor;
            uint64_t caller_id = 0;
            rc = p319_take_decimal(&cursor, end, UINT32_MAX, &caller_id);
        }
    }
    if (rc == 0) rc = p319_take_literal(&cursor, end, ";");
    if (rc != 0) return rc;
    *message = cursor;
    return 0;
}

static long p319_count(uint32_t *value) {
    if (value == NULL || *value == UINT32_MAX) return -P319_DETAIL_WITNESS_COUNTER_OVERFLOW;
    ++*value;
    return 0;
}

static long p319_vps_name(const char *start, const char *end) {
    if (start >= end || (size_t)(end - start) > 64U
        || *start == ' ' || *(end - 1) == ' ') return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    for (const char *cursor = start; cursor < end; ++cursor) {
        if (*cursor < ' ' || *cursor > '~') return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    }
    return 0;
}

static long p319_copy_name(
    char *destination, uint8_t *length, const char *start, const char *end) {
    if (destination == NULL || length == NULL || p319_vps_name(start, end) != 0
        || (size_t)(end - start) > 64U) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    size_t count = (size_t)(end - start);
    for (size_t index = 0; index < count; ++index) destination[index] = start[index];
    *length = (uint8_t)count;
    return 0;
}

static __attribute__((unused)) long p319_note_successful_module(size_t index, long result, const char *name) {
    if (index > UINT32_MAX || result != 0 || name == NULL) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    g_p319_witness.active_module_index = (uint32_t)index;
    g_p319_witness.active_module_valid = 1U;
    if (index == 69U || index == 71U || index == 72U) {
        unsigned int slot = index == 69U ? 0U : (index == 71U ? 1U : 2U);
        if (g_p319_witness.target_modules[slot].valid) {
            g_p319_witness.initial_chain_ambiguous = 1U;
            return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
        }
        g_p319_witness.target_modules[slot].index = (uint32_t)index;
        g_p319_witness.target_modules[slot].result = (int32_t)result;
        const char *cursor = name;
        while (*cursor != '\0') ++cursor;
        long rc = p319_copy_name(g_p319_witness.target_modules[slot].name,
            &g_p319_witness.target_modules[slot].name_length, name, cursor);
        if (rc != 0) return rc;
        g_p319_witness.target_modules[slot].valid = 1U;
    }
    return 0;
}

static void p319_chain_event(unsigned int event) {
    if (!g_p319_witness.active_module_valid) return;
    if (g_p319_witness.active_module_index != 72U) {
        g_p319_witness.initial_chain_ambiguous = 1U;
        return;
    }
    if (event == 1U && g_p319_witness.initial_chain_stage == 0U) {
        g_p319_witness.initial_chain_stage = 1U;
    } else if (event == 2U && g_p319_witness.initial_chain_stage == 1U) {
        g_p319_witness.initial_chain_stage = 2U;
    } else if (event == 3U && g_p319_witness.initial_chain_stage == 2U) {
        g_p319_witness.initial_chain_stage = 3U;
    } else if (event == 4U && g_p319_witness.initial_chain_stage == 3U) {
        g_p319_witness.initial_chain_stage = 4U;
        g_p319_witness.initial_chain_complete = 1U;
        g_p319_witness.initial_chain_module_index = 72U;
    } else {
        g_p319_witness.initial_chain_ambiguous = 1U;
    }
}

static long p319_observe_probe(const char *message, size_t length) {
    const char *prefix = "max77705: max77705_usbc_probe: ";
    const char *tail = "probing Complete..";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix), "probing")) return 0;
    if (!p319_eq(message + cstr_len(prefix), length - cstr_len(prefix), tail)) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    long rc = p319_count(&g_p319_witness.probe_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_PROBE;
    if (rc == 0) p319_chain_event(4U);
    return rc;
}

static long p319_observe_irq(const char *message, size_t length) {
    const char *prefix = "pdic_max77705: max77705_muic_irq_init ";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix), "uiadc(")) return 0;
    const char *cursor = message + cstr_len(prefix);
    const char *end = message + length;
    const char *labels[5] = {"uiadc(", "), chgtyp(", "), dcdtmo(", "), vbadc(", "), vbusdet("};
    for (unsigned int i = 0; i < 5U; ++i) {
        long rc = p319_take_literal(&cursor, end, labels[i]);
        if (rc != 0) return rc;
        int64_t value = 0;
        rc = p319_take_signed(&cursor, end, INT32_MIN, INT32_MAX, &value);
        if (rc != 0) return rc;
        g_p319_witness.irq[i] = (int32_t)value;
    }
    long close_rc = p319_take_literal(&cursor, end, ")");
    if (close_rc != 0) return close_rc;
    if (cursor != end) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    long rc = p319_count(&g_p319_witness.irq_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_IRQ;
    if (rc == 0) p319_chain_event(1U);
    return rc;
}

static long p319_observe_initial(const char *message, size_t length) {
    const char *prefix = "pdic_max77705: max77705_muic_detect_dev ";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix), "USBC1:")) return 0;
    const char *cursor = message + cstr_len(prefix);
    const char *end = message + length;
    const char *labels[3] = {"USBC1:0x", ", USBC2:0x", ", BC:0x"};
    for (unsigned int i = 0; i < 3U; ++i) {
        long rc = p319_take_literal(&cursor, end, labels[i]);
        if (rc != 0) return rc;
        uint32_t value = 0;
        rc = p319_take_hex(&cursor, end, 1, &value);
        if (rc != 0) return rc;
        g_p319_witness.initial_status[i] = value;
    }
    if (cursor != end) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    long rc = p319_count(&g_p319_witness.initial_status_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_INITIAL;
    if (rc == 0) p319_chain_event(2U);
    return rc;
}

static long p319_observe_class1(const char *message, size_t length) {
    const char *prefix = "pdic_max77705: max77705_muic_check_new_dev ";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix), "vps table")) return 0;
    const char *cursor = message + cstr_len(prefix);
    const char *end = message + length;
    long rc = p319_take_literal(&cursor, end, "vps table match found at i(");
    uint64_t index = 0;
    if (rc == 0) rc = p319_take_decimal(&cursor, end, UINT64_MAX, &index);
    if (rc == 0) rc = p319_take_literal(&cursor, end, "), ");
    const char *name = cursor;
    while (cursor < end) ++cursor;
    if (rc == 0) rc = p319_copy_name(g_p319_witness.classification_form1_name,
        &g_p319_witness.classification_form1_name_length, name, end);
    if (rc == 0) g_p319_witness.classification_form1_index = index;
    if (rc == 0) rc = p319_count(&g_p319_witness.classification_form1_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_CLASS1;
    if (rc == 0) p319_chain_event(3U);
    return rc;
}

static long p319_observe_class2(const char *message, size_t length) {
    const char *prefix = "pdic_max77705: muic_lookup_vps_table ";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix), "(")) return 0;
    const char *cursor = message + cstr_len(prefix);
    const char *end = message + length;
    long rc = p319_take_literal(&cursor, end, "(");
    int64_t attached = 0;
    uint64_t index = 0;
    if (rc == 0) rc = p319_take_signed(&cursor, end, INT32_MIN, INT32_MAX, &attached);
    if (rc == 0) rc = p319_take_literal(&cursor, end, ") vps table match found at i(");
    if (rc == 0) rc = p319_take_decimal(&cursor, end, INT32_MAX, &index);
    if (rc == 0) rc = p319_take_literal(&cursor, end, "), ");
    const char *name = cursor;
    while (cursor < end) ++cursor;
    if (rc == 0) rc = p319_copy_name(g_p319_witness.classification_form2_name,
        &g_p319_witness.classification_form2_name_length, name, end);
    if (rc == 0) {
        g_p319_witness.classification_form2_attached_dev = (int32_t)attached;
        g_p319_witness.classification_form2_index = index;
    }
    if (rc == 0) rc = p319_count(&g_p319_witness.classification_form2_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_CLASS2;
    return rc;
}

static long p319_observe_deferred(const char *message, size_t length) {
    const char *prefix = "pdic_max77705: max77705_muic_print_reg_log ";
    if (!p319_has(message, length, prefix)) return 0;
    if (!p319_has(message + cstr_len(prefix), length - cstr_len(prefix), "USBC1:")) return 0;
    const char *cursor = message + cstr_len(prefix);
    const char *end = message + length;
    const char *labels[7] = {"USBC1:0x", ", USBC2:0x", ", BC:0x", ", CC0:0x", ", CC1:0x", ", PD0:0x", ", PD1:0x"};
    for (unsigned int i = 0; i < 7U; ++i) {
        long rc = p319_take_literal(&cursor, end, labels[i]);
        uint32_t value = 0;
        if (rc == 0) rc = p319_take_hex(&cursor, end, i < 3U, &value);
        if (rc != 0) return rc;
    }
    long rc = p319_take_literal(&cursor, end, " attached_dev:");
    int64_t attached = 0;
    if (rc == 0) rc = p319_take_signed(&cursor, end, INT32_MIN, INT32_MAX, &attached);
    if (rc == 0 && cursor != end) rc = -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    if (rc == 0) rc = p319_count(&g_p319_witness.deferred_status_count);
    if (rc == 0) g_p319_witness.witness_mask |= P319_WITNESS_MASK_DEFERRED;
    return rc;
}

static long p319_witness_observe_v1(const char *message, size_t length) {
    if (message == NULL) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    long rc = p319_observe_probe(message, length);
    if (rc == 0) rc = p319_observe_irq(message, length);
    if (rc == 0) rc = p319_observe_initial(message, length);
    if (rc == 0) rc = p319_observe_class1(message, length);
    if (rc == 0) rc = p319_observe_class2(message, length);
    if (rc == 0) rc = p319_observe_deferred(message, length);
    if (rc != 0 && g_p319_witness.malformed_count != UINT32_MAX) ++g_p319_witness.malformed_count;
    return rc;
}

static __attribute__((unused)) long p319_witness_summary_state_v1_copy(
    struct p319_witness_summary_state_v1 *destination) {
    if (destination == NULL) return -P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    *destination = g_p319_witness;
    destination->module_loads = g_p303_kmsg.module_count;
    destination->module_drains = g_p303_kmsg.module_drain_count;
    destination->drains = g_p303_kmsg.drain_count;
    destination->record_count = g_p303_kmsg.record_count;
    destination->record_bytes = g_p303_kmsg.record_bytes;
    destination->first_sequence = g_p303_kmsg.first_sequence;
    destination->last_sequence = g_p303_kmsg.previous_sequence;
    destination->first_sequence_valid = g_p303_kmsg.sequence_seen;
    destination->last_sequence_valid = g_p303_kmsg.sequence_seen;
    return 0;
}
'''


def _runtime_struct() -> bytes:
    return b'''struct p303_kmsg_capture {
    int fd;
    uint8_t started;
    uint8_t final;
    uint8_t path_seen;
    uint8_t reset_mask;
    uint8_t sequence_seen;
    uint32_t readback_count;
    uint32_t first_offset;
    uint64_t previous_sequence;
    uint64_t first_sequence;
    uint64_t record_count;
    uint64_t record_bytes;
    uint32_t drain_count;
    uint32_t module_count;
    uint32_t module_drain_count;
    uint32_t drain_record_count;
    uint32_t drain_bytes;
};
'''


def transform_runtime(base: bytes) -> bytes:
    value = _replace_once(
        base,
        b"#define P303_KMSG_RECORD_CAPACITY 4096U\n",
        b"""#define P303_KMSG_RECORD_CAPACITY 4096U
#define P319_KMSG_MAX_DRAIN_RECORDS 256U
#define P319_KMSG_MAX_DRAIN_BYTES 262144U
#define P319_KMSG_MAX_TOTAL_RECORDS 4096U
#define P319_KMSG_MAX_TOTAL_BYTES 1048576ULL
#define P319_KMSG_MAX_MODULES 73U
""",
        "bounded kmsg limits",
    )
    # Replace the old struct with the extended version while keeping one exact anchor.
    old_struct = re.search(rb"struct p303_kmsg_capture \{.*?\n\};\n", value, re.S)
    if old_struct is None:
        raise AuditError("runtime capture struct absent")
    value = value[:old_struct.start()] + _runtime_struct() + value[old_struct.end():]
    parser_anchor = b"static long p303_kmsg_record(const char *record, size_t length) {\n"
    if value.count(parser_anchor) != 1:
        raise AuditError("kmsg record parser anchor differs")
    value = value.replace(parser_anchor, P319_C_PARSER_SOURCE.encode("ascii") + b"\n" + parser_anchor, 1)
    record_start = value.index(parser_anchor)
    record_end = value.index(b"\n}\n\nstatic long p303_kmsg_drain", record_start) + 3
    old_record = value[record_start:record_end]
    old_record = old_record.replace(
        b"static long p303_kmsg_record(const char *record, size_t length) {\n",
        b"""static long p303_kmsg_record(const char *record, size_t length) {
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
""", 1)
    header_start = old_record.index(b"    const char *end = record + length;")
    message_length_start = old_record.index(b"    size_t message_length", header_start)
    header_prefix = old_record[:header_start]
    header_suffix = old_record[message_length_start:]
    old_record = header_prefix + b"""    const char *end = record + length;
    uint64_t sequence = 0;
    const char *message = NULL;
    long rc = p319_kmsg_header(record, length, &sequence, &message);
    if (rc != 0
        || (g_p303_kmsg.sequence_seen
            && (g_p303_kmsg.previous_sequence == UINT64_MAX
                || sequence != g_p303_kmsg.previous_sequence + 1U))) {
        return P303_DETAIL_KMSG_SEQUENCE_CONTRADICTION;
    }
    if (!g_p303_kmsg.sequence_seen) g_p303_kmsg.first_sequence = sequence;
    g_p303_kmsg.sequence_seen = 1U;
    g_p303_kmsg.previous_sequence = sequence;
""" + header_suffix
    old_record = old_record.replace(
        b"if (rc != 0\n        || (g_p303_kmsg.sequence_seen\n            && sequence != g_p303_kmsg.previous_sequence + 1U)) {",
        b"if (rc != 0 || (g_p303_kmsg.sequence_seen\n            && (g_p303_kmsg.previous_sequence == UINT64_MAX\n                || sequence != g_p303_kmsg.previous_sequence + 1U))) {",
        1,
    )
    old_record = old_record.replace(
        b"g_p303_kmsg.sequence_seen = 1U;\n    g_p303_kmsg.previous_sequence = sequence;",
        b"if (!g_p303_kmsg.sequence_seen) g_p303_kmsg.first_sequence = sequence;\n    g_p303_kmsg.sequence_seen = 1U;\n    g_p303_kmsg.previous_sequence = sequence;",
        1,
    )
    old_record = old_record.replace(
        b"    if (body_end == NULL) {\n        p308_latch_failure(P308_FAILURE_SITE_LINE);\n    } else {\n        rc = p308_kmsg_observe(\n            message, (size_t)(body_end - message));\n        if (rc != 0) return rc;\n    }",
        b"""    if (body_end == NULL || body_end + 1 != end) {
        return P319_DETAIL_WITNESS_GRAMMAR_CONTRADICTION;
    }
    size_t body_length = (size_t)(body_end - message);
    rc = p319_witness_observe_v1(message, body_length);
    if (rc == 0) rc = p308_kmsg_observe(message, body_length);
    if (rc != 0) return rc;""",
        1,
    )
    value = value[:record_start] + old_record + value[record_end:]
    # _c_function_body begins at the function name, leaving the existing
    # ``static long `` declaration prefix in place.
    drain_body = b'''p303_kmsg_drain(void) {
    if (!g_p303_kmsg.started || g_p303_kmsg.fd < 0 || g_p303_kmsg.final) {
        return P303_DETAIL_KMSG_READ_FAILED;
    }
    if (g_p303_kmsg.drain_count == UINT32_MAX) {
        return P319_DETAIL_WITNESS_COUNTER_OVERFLOW;
    }
    ++g_p303_kmsg.drain_count;
    g_p303_kmsg.drain_record_count = 0U;
    g_p303_kmsg.drain_bytes = 0U;
    char record[P303_KMSG_RECORD_CAPACITY];
    for (;;) {
        long amount = sys_read(g_p303_kmsg.fd, record, sizeof(record));
        if (amount == -EAGAIN) return 0;
        if (amount == -P303_EPIPE) return P303_DETAIL_KMSG_RING_LOSS;
        if (amount <= 0 || amount > (long)sizeof(record)) {
            return P303_DETAIL_KMSG_READ_FAILED;
        }
        long rc = p303_kmsg_record(record, (size_t)amount);
        if (rc != 0) return rc;
    }
}
'''
    value = _replace_function(value, "p303_kmsg_drain", drain_body)
    return value


def transform_wrapper(base: bytes) -> bytes:
    old = b'''static long p319_after_module_load(size_t index) {
    return index == S22PLUS_O2_EUD_MODULE_INDEX
        ? p307_read_eud_cache()
        : 0;
}
'''
    new = b'''static long p319_after_module_load(size_t index, long load_rc) {
    if (g_p303_kmsg.module_count >= P319_KMSG_MAX_MODULES) {
        return P319_DETAIL_WITNESS_COUNTER_OVERFLOW;
    }
    long note_rc = p319_note_successful_module(
        index, load_rc, s22plus_o2_module_plan[index].filename);
    if (note_rc != 0) return note_rc;
    ++g_p303_kmsg.module_count;
    long drain_rc = p303_kmsg_drain();
    g_p319_witness.active_module_valid = 0U;
    if (drain_rc != 0) return drain_rc;
    if (g_p303_kmsg.module_drain_count == UINT32_MAX) {
        return P319_DETAIL_WITNESS_COUNTER_OVERFLOW;
    }
    ++g_p303_kmsg.module_drain_count;
    return index == S22PLUS_O2_EUD_MODULE_INDEX
        ? p307_read_eud_cache() : 0;
}
'''
    # Keep a distinct compile-time name for the module-count guard.
    value = _replace_once(base, old, new, "shared post-load witness path")
    value = _replace_once(
        value,
        b"#include \"s22plus_fyg8_p290_e3_runtime.inc.c\"\n",
        b"#include \"s22plus_fyg8_p290_e3_runtime.inc.c\"\n",
        "runtime include binding",
    )
    if value.count(b"p319_after_module_load(index);") != 2:
        raise AuditError("direct/folded post-load calls are not both present")
    value = value.replace(b"p319_after_module_load(index);", b"p319_after_module_load(index, 0L);", 1)
    value = value.replace(b"p319_after_module_load(index);", b"p319_after_module_load(index, p305_folded_load_rc);", 1)
    return value


def _base_source_identities(receipt: bytes) -> dict[str, tuple[int, str]]:
    value = strict_json(receipt, "base materialization receipt")
    if value.get("schema") != "s22plus-fyg8-p319-successor-module-materialization-v1":
        raise AuditError("base materialization schema differs")
    materialized = value.get("materialization", {}).get("materialized_sources")
    if not isinstance(materialized, dict) or len(materialized) != 12:
        raise AuditError("base materialized source identities differ")
    result = {}
    for name, item in materialized.items():
        if not isinstance(item, dict) or set(item) != {"size", "sha256"}:
            raise AuditError("base source identity shape differs")
        result[name] = (int(item["size"]), str(item["sha256"]))
    return result


def _paths(root: Path) -> dict[str, Path]:
    return {
        "root": root, "inputs": root / "inputs", "base_sources": root / "base-sources",
        "sources": root / "materialized-sources",
        "result": root / "result.json",
    }


def load_inputs(materialize: bool, output_root: Path | None = None) -> dict[str, bytes]:
    root = (output_root or OUTPUT_ROOT).absolute()
    base_receipt = stable_bytes(BASE_RECEIPT, label="base materialization receipt", maximum=256 << 10,
                                expected_size=BASE_RECEIPT_SIZE, expected_sha256=BASE_RECEIPT_SHA256,
                                required_mode=0o400, required_nlink=1)
    identities = _base_source_identities(base_receipt)
    base: dict[str, bytes] = {}
    for name, (size, digest) in identities.items():
        base[name] = stable_bytes(BASE_SOURCES / name, label=f"base source {name}", maximum=max(size, 1 << 20),
                                   expected_size=size, expected_sha256=digest, required_mode=0o400, required_nlink=1)
    added = {
        "base-result.json": (BASE_RECEIPT, base_receipt, 256 << 10),
        "pdic_max77705.ko": (BASE_MODULES / "pdic_max77705.ko", stable_bytes(
            BASE_MODULES / "pdic_max77705.ko", label="bound PDIC module", maximum=512 << 10,
            expected_size=PDIC_MODULE_SIZE, expected_sha256=PDIC_MODULE_SHA256, required_mode=0o400, required_nlink=1), 512 << 10),
    }
    for key, spec in SOURCE_SPECS.items():
        added[key] = (spec.source, stable_bytes(spec.source, label=f"source {key}", maximum=spec.maximum,
                                               expected_size=spec.size, expected_sha256=spec.sha256), spec.maximum)
    if materialize:
        paths = _paths(root)
        if root.exists() or root.is_symlink():
            raise AuditError("successor parser output already exists")
        _mkdir(root); _mkdir(paths["inputs"]); _mkdir(paths["base_sources"]); _mkdir(paths["sources"])
        for key, (_, payload, _) in added.items():
            _write_exclusive(paths["inputs"] / key, payload)
        for name, payload in base.items():
            _write_exclusive(paths["base_sources"] / name, payload)
        generated = materialized_bytes(base)
        for name, payload in generated.items():
            _write_exclusive(paths["sources"] / name, payload)
        _fsync_directory(paths["inputs"]); _fsync_directory(paths["base_sources"]); _fsync_directory(paths["sources"])
        _fsync_directory(root); _fsync_directory(root.parent)
    if materialize:
        input_root = _paths(root)["inputs"]
        source_root = _paths(root)["base_sources"]
        generated_root = _paths(root)["sources"]
    else:
        input_root = root / "inputs"
        source_root = root / "base-sources"
        generated_root = root / "materialized-sources"
    result: dict[str, bytes] = {"base-result.json": stable_bytes(input_root / "base-result.json", label="preserved base receipt", maximum=256 << 10,
                                                                  expected_size=BASE_RECEIPT_SIZE, expected_sha256=BASE_RECEIPT_SHA256, required_mode=0o400, required_nlink=1)}
    for name in identities:
        result[f"base:{name}"] = stable_bytes(source_root / name, label=f"preserved base source {name}", maximum=max(identities[name][0], 1 << 20),
                                               expected_size=identities[name][0], expected_sha256=identities[name][1], required_mode=0o400, required_nlink=1)
    generated = materialized_bytes({
        key: result[f"base:{key}"] for key in identities
    })
    for name, payload in generated.items():
        result[f"generated:{name}"] = stable_bytes(
            generated_root / name, label=f"preserved generated source {name}",
            maximum=max(len(payload), 1 << 20), expected_size=len(payload),
            expected_sha256=sha256(payload), required_mode=0o400, required_nlink=1,
        )
    for key, spec in SOURCE_SPECS.items():
        result[key] = stable_bytes(input_root / spec.snapshot, label=f"preserved {key}", maximum=spec.maximum,
                                   expected_size=spec.size, expected_sha256=spec.sha256, required_mode=0o400, required_nlink=1)
    result["pdic_max77705.ko"] = stable_bytes(input_root / "pdic_max77705.ko", label="preserved PDIC module", maximum=512 << 10,
                                               expected_size=PDIC_MODULE_SIZE, expected_sha256=PDIC_MODULE_SHA256,
                                               required_mode=0o400, required_nlink=1)
    return result


def _base_sources(inputs: dict[str, bytes]) -> dict[str, bytes]:
    return {key[5:]: payload for key, payload in inputs.items() if key.startswith("base:")}


def _generated_sources(inputs: dict[str, bytes]) -> dict[str, bytes]:
    return {key[10:]: payload for key, payload in inputs.items() if key.startswith("generated:")}


def materialized_bytes(base: dict[str, bytes]) -> dict[str, bytes]:
    result = dict(base)
    wrapper = "s22plus_fyg8_p290_e3_runtime.c"
    runtime = "s22plus_fyg8_p290_e3_runtime.inc.c"
    result[runtime] = transform_runtime(base[runtime])
    result[wrapper] = transform_wrapper(base[wrapper])
    changed = {name for name in result if result[name] != base[name]}
    if changed != {runtime, wrapper}:
        raise AuditError(f"unexpected source delta: {sorted(changed)}")
    return result


def audit_envelope_v4_unchanged(base: dict[str, bytes], generated: dict[str, bytes]) -> dict[str, Any]:
    """Prove the parser/transport transform did not rewrite the P3.18 ABI."""
    name = "s22plus_fyg8_p290_e3_runtime.inc.c"
    base_runtime = base[name]
    generated_runtime = generated[name]
    constants = (
        b"#define S22PLUS_MAX77705_ENVELOPE_SIZE 128U\n",
        b"#define S22PLUS_MAX77705_ENVELOPE_CRC_OFFSET 124U\n",
        b"#define S22PLUS_MAX77705_P318_ENVELOPE_VERSION 4U\n",
        b"#define S22PLUS_MAX77705_P318_TIMING_SIZE 26U\n",
        b"#define S22PLUS_MAX77705_P318_LOSSLESS_CAPACITY 47U\n",
        b"#define S22PLUS_MAX77705_P318_TIME_MASK 0xffU\n",
    )
    crc_domain = b'"S22PLUS-FYG8-MAX77705-DIAG-V4\\0"'
    for payload in (base_runtime, generated_runtime):
        for token in constants:
            if payload.count(token) != 1:
                raise AuditError(f"Envelope-v4 constant multiplicity differs: {token!r}")
        if payload.count(crc_domain) != 1:
            raise AuditError("Envelope-v4 CRC domain differs")
    functions = (
        "s22plus_max77705_p318_envelope_crc32",
        "s22plus_max77705_p318_encode_envelope",
        "p317_publish",
    )
    identities: dict[str, dict[str, Any]] = {}
    for function in functions:
        base_body = _c_function_body(base_runtime, function)
        generated_body = _c_function_body(generated_runtime, function)
        if base_body != generated_body:
            raise AuditError(f"Envelope-v4 function changed: {function}")
        identities[function] = identity(base_body)
    return {
        "base_generated_function_bytes_identical": True,
        "functions": identities,
        "envelope_size": 128,
        "crc_offset": 124,
        "version": 4,
        "timing_size": 26,
        "lossless_capacity": 47,
        "time_mask": "0xffU",
        "crc_domain": "S22PLUS-FYG8-MAX77705-DIAG-V4\\0",
    }


def audit_materialization(base: dict[str, bytes], generated: dict[str, bytes]) -> dict[str, Any]:
    if generated.keys() != base.keys():
        raise AuditError("successor source set differs")
    changed = [name for name in generated if generated[name] != base[name]]
    if set(changed) != {"s22plus_fyg8_p290_e3_runtime.c", "s22plus_fyg8_p290_e3_runtime.inc.c"}:
        raise AuditError("successor changed source set differs")
    wrapper = generated["s22plus_fyg8_p290_e3_runtime.c"]
    runtime = generated["s22plus_fyg8_p290_e3_runtime.inc.c"]
    envelope_v4 = audit_envelope_v4_unchanged(base, generated)
    for token in (b"p319_after_module_load(index,", b"P319_KMSG_MAX_DRAIN_RECORDS", b"P319_WITNESS_ABI_VERSION"):
        if token not in wrapper + runtime:
            raise AuditError(f"successor token absent: {token!r}")
    if wrapper.count(b"p319_after_module_load(index,") != 2:
        raise AuditError("direct/folded shared drain coverage differs")
    if wrapper.count(b"p319_after_module_load(index, 0L);") != 1 or wrapper.count(b"p319_after_module_load(index, p305_folded_load_rc);") != 1:
        raise AuditError("module result binding differs between loops")
    helper = wrapper[wrapper.index(b"static long p319_after_module_load"):]
    if helper.find(b"p303_kmsg_drain()") > helper.find(b"p307_read_eud_cache()"):
        raise AuditError("EUD fallible action precedes the post-load drain")
    if runtime.count(b"if (amount == -P303_EPIPE) return P303_DETAIL_KMSG_RING_LOSS;") != 1:
        raise AuditError("EPIPE gate absent")
    if runtime.count(b"sequence != g_p303_kmsg.previous_sequence + 1U") != 1:
        raise AuditError("sequence gap gate absent")
    if b"P319_WITNESS_MASK_INITIAL" not in runtime or b"max77705_muic_print_reg_log" not in runtime:
        raise AuditError("source-derived parser forms absent")
    return {
        "base_source_count": len(base), "changed_source_count": len(changed),
        "changed_sources": sorted(changed), "unchanged_source_count": len(base) - len(changed),
        "direct_post_load_drain_calls": 1, "folded_post_load_drain_calls": 1,
        "per_module_drain_is_shared": True, "eud_hook_follows_shared_drain": True,
        "successful_module_result_bound": True,
        "target_module_indices": [69, 71, 72],
        "epipe_fail_closed": True, "sequence_gap_fail_closed": True,
        "fixed_record_capacity": MAX_RECORD_BYTES, "fixed_per_drain_record_limit": MAX_DRAIN_RECORDS,
        "fixed_per_drain_byte_limit": MAX_DRAIN_BYTES, "fixed_cumulative_record_limit": MAX_TOTAL_RECORDS,
        "fixed_cumulative_byte_limit": MAX_TOTAL_BYTES,
        "structured_summary_state": SUMMARY_STATE,
        "carrier_publication": False,
        "envelope_v4_unchanged": envelope_v4,
    }


def _message_from_last_kmsg(line: bytes) -> str | None:
    marker = b"] "
    # last_kmsg has both a timestamp bracket and a task bracket; the printk
    # body begins after the latter, not the first one.
    pos = line.rfind(marker)
    if pos < 0:
        return None
    body = line[pos + len(marker):].rstrip(b"\r\n")
    try:
        return body.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return None


def qualify_corpus(capture: bytes) -> dict[str, Any]:
    parser = BoundedTransport()
    messages: list[dict[str, Any]] = []
    for line in capture.splitlines():
        message = _message_from_last_kmsg(line)
        if message is None:
            continue
        try:
            parsed = parse_witness_message(message, parser.state)
        except AuditError:
            raise
        if parsed is not None:
            messages.append(parsed)
    kinds = {item["kind"] for item in messages}
    required = {"probe", "irq", "initial_status", "classification", "deferred_status"}
    if not {"probe", "irq", "initial_status", "deferred_status"}.issubset(kinds):
        raise AuditError("corpus lacks required positive witness forms")
    if parser.state.class_form1_count == 0 or parser.state.class_form2_count == 0:
        raise AuditError("corpus lacks both classification forms")
    return {
        "capture_identity": identity(capture),
        "messages_qualified": len(messages),
        "kinds": sorted(kinds),
        "probe_count": parser.state.probe_count,
        "irq_count": parser.state.irq_count,
        "initial_status_count": parser.state.initial_status_count,
        "classification_form1_count": parser.state.class_form1_count,
        "classification_form2_count": parser.state.class_form2_count,
        "deferred_status_count": parser.state.deferred_status_count,
        "deferred_is_not_initial": parser.state.initial_status_count > 0,
        "source_grammar_not_derived_from_corpus": True,
    }


def syntax_compile(source_root: Path) -> dict[str, Any]:
    compiler = shutil_which("aarch64-linux-gnu-gcc")
    if compiler is None:
        raise AuditError("AArch64 compiler unavailable")
    run_id_define = "{" + ",".join("0x%02x" % item for item in bytes.fromhex("b9cc424d0d184f5accbce94a844e817d")) + "}"
    command = [compiler, "-nostdlib", "-ffreestanding", "-fno-builtin", "-fno-stack-protector",
               "-Wall", "-Wextra", "-Werror", "-fsyntax-only", "-DS22PLUS_FYG8_P233_PROFILE=3",
               f"-DS22PLUS_FYG8_P233_RUN_ID_BYTES={run_id_define}",
               "-I", str(source_root), "-I", str(ROOT / "workspace/public/src/native-init"),
               str(source_root / "s22plus_fyg8_p290_e3_runtime.c")]
    completed = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=180, check=False)
    if completed.returncode != 0 or completed.stdout or completed.stderr:
        detail = (completed.stdout + completed.stderr).decode("utf-8", "replace")
        raise AuditError(f"generated runtime syntax check failed: {detail[-4000:]}")
    return {"compiler": Path(compiler).name, "syntax_only": True, "returncode": 0}


def _generated_parser_source(runtime: bytes) -> bytes:
    parser_start = runtime.find(b"#define P319_WITNESS_ABI_VERSION")
    record_start = runtime.find(b"static long p303_kmsg_record", parser_start)
    if parser_start < 0 or record_start < 0 or parser_start >= record_start:
        raise AuditError("generated parser/record boundaries are absent")
    return runtime[parser_start:record_start]


def qualify_c_parser_native(runtime: bytes) -> dict[str, Any]:
    """Compile and execute parser bytes extracted from the generated runtime."""
    compiler = shutil_which("gcc")
    if compiler is None:
        raise AuditError("host C compiler unavailable for parser qualification")
    with tempfile.TemporaryDirectory(prefix="p319-witness-c-qualify-") as directory:
        root = Path(directory)
        source = root / "fixture.c"
        source.write_text(
            "#include <stdint.h>\n#include <stddef.h>\n#include <limits.h>\n"
            "#include <string.h>\n#include <stdio.h>\n"
            "static size_t cstr_len(const char *s) { return strlen(s); }\n"
            "static int p260_bytes_equal(const char *a, const char *b, size_t n) { return memcmp(a, b, n) == 0; }\n"
            "struct p303_kmsg_capture { int fd; uint8_t started; uint8_t final; uint8_t path_seen; uint8_t reset_mask; uint8_t sequence_seen; uint32_t readback_count; uint32_t first_offset; uint64_t previous_sequence; uint64_t first_sequence; uint64_t record_count; uint64_t record_bytes; uint32_t drain_count; uint32_t module_count; uint32_t module_drain_count; uint32_t drain_record_count; uint32_t drain_bytes; };\n"
            "static struct p303_kmsg_capture g_p303_kmsg;\n"
            + _generated_parser_source(runtime).decode("ascii")
            + """
int main(int argc, char **argv) {
    int start = 1;
    const char *mode = argc > 1 ? argv[1] : "";
    if (strcmp(mode, "chain") == 0 || strcmp(mode, "wrong-row") == 0
        || strcmp(mode, "wrong-order") == 0 || strcmp(mode, "aux") == 0) {
        start = 2;
        unsigned int module_index = strcmp(mode, "wrong-row") == 0 ? 71U : 72U;
        if (p319_note_successful_module(module_index, 0L,
                module_index == 72U ? "pdic_max77705.ko" : "mfd_max77705.ko") != 0)
            return 8;
    }
    for (int i = start; i < argc; ++i) {
        long rc = p319_witness_observe_v1(argv[i], strlen(argv[i]));
        if (rc != 0) { printf("ERR %ld\\n", rc); return 2; }
    }
    struct p319_witness_summary_state_v1 summary;
    if (p319_witness_summary_state_v1_copy(&summary) != 0) return 3;
    if (strcmp(mode, "chain") == 0) {
        printf("CHAIN %u %u %u TARGET %u %u %d %u %.*s\\n",
            summary.initial_chain_stage, summary.initial_chain_complete,
            summary.initial_chain_ambiguous, summary.target_modules[2].index,
            summary.target_modules[2].valid, summary.target_modules[2].result,
            summary.target_modules[2].name_length, summary.target_modules[2].name_length,
            summary.target_modules[2].name);
        if (summary.initial_chain_stage != 4U ||
            summary.initial_chain_complete != 1U ||
            summary.initial_chain_ambiguous != 0U ||
            summary.target_modules[2].valid != 1U ||
            summary.target_modules[2].index != 72U ||
            summary.target_modules[2].result != 0 ||
            summary.target_modules[2].name_length != 16U ||
            memcmp(summary.target_modules[2].name, "pdic_max77705.ko", 16U) != 0)
            return 9;
        return 0;
    }
    if (strcmp(mode, "wrong-row") == 0 || strcmp(mode, "wrong-order") == 0) {
        printf("CHAIN %u %u %u\\n", summary.initial_chain_stage,
            summary.initial_chain_complete, summary.initial_chain_ambiguous);
        if (summary.initial_chain_complete != 0U ||
            summary.initial_chain_ambiguous != 1U)
            return 10;
        return 0;
    }
    if (strcmp(mode, "aux") == 0) {
        printf("CHAIN %u %u %u\\n", summary.initial_chain_stage,
            summary.initial_chain_complete, summary.initial_chain_ambiguous);
        if (summary.initial_chain_stage != 0U ||
            summary.initial_chain_complete != 0U ||
            summary.initial_chain_ambiguous != 0U)
            return 11;
        return 0;
    }
    printf("MASK %u\\n", summary.witness_mask);
    printf("IRQ %d %d %d %d %d\\n", summary.irq[0], summary.irq[1],
        summary.irq[2], summary.irq[3], summary.irq[4]);
    printf("STATUS %u %u %u\\n", summary.initial_status[0],
        summary.initial_status[1], summary.initial_status[2]);
    printf("COUNTS %u %u %u %u %u %u\\n", summary.probe_count,
        summary.irq_count, summary.initial_status_count,
        summary.classification_form1_count, summary.classification_form2_count,
        summary.deferred_status_count);
    printf("C1 %llu %u %.*s\\n", (unsigned long long)summary.classification_form1_index,
        summary.classification_form1_name_length, summary.classification_form1_name_length,
        summary.classification_form1_name);
    printf("C2 %d %llu %u %.*s\\n", summary.classification_form2_attached_dev,
        (unsigned long long)summary.classification_form2_index,
        summary.classification_form2_name_length, summary.classification_form2_name_length,
        summary.classification_form2_name);
    printf("CHAIN %u %u %u\\n", summary.initial_chain_stage,
        summary.initial_chain_complete, summary.initial_chain_ambiguous);
    return 0;
}
""",
            encoding="ascii",
        )
        binary = root / "fixture"
        completed = subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-o", str(binary), str(source)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if completed.returncode != 0:
            detail = (completed.stdout + completed.stderr).decode("utf-8", "replace")
            raise AuditError(f"native parser fixture compile failed: {detail[-4000:]}")
        positive = [
            "max77705: max77705_usbc_probe: probing Complete..",
            "pdic_max77705: max77705_muic_irq_init uiadc(355), chgtyp(354), dcdtmo(352), vbadc(351), vbusdet(350)",
            "pdic_max77705: max77705_muic_detect_dev USBC1:0x27, USBC2:0x05, BC:0x82",
            "pdic_max77705: max77705_muic_check_new_dev vps table match found at i(9), DCD Timeout",
            "pdic_max77705: muic_lookup_vps_table (2) vps table match found at i(9), CDP",
            "pdic_max77705: max77705_muic_print_reg_log USBC1:0x27, USBC2:0x05, BC:0x82, CC0:0xa1, CC1:0x8, PD0:0x19, PD1:0x47 attached_dev:2",
        ]
        run = subprocess.run([str(binary), *positive], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        expected_lines = (
            "MASK 63\n", "IRQ 355 354 352 351 350\n", "STATUS 39 5 130\n",
            "COUNTS 1 1 1 1 1 1\n", "C1 9 11 DCD Timeout\n", "C2 2 9 3 CDP\n",
        )
        if run.returncode != 0 or any(line not in run.stdout for line in expected_lines):
            raise AuditError(f"native parser positive fixture failed: {run.stdout}{run.stderr}")
        numeric_positive = subprocess.run(
            [str(binary),
             "pdic_max77705: max77705_muic_irq_init uiadc(-2147483648), chgtyp(2147483647), dcdtmo(0), vbadc(-1), vbusdet(1)",
             "pdic_max77705: muic_lookup_vps_table (-2147483648) vps table match found at i(2147483647), USB"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
        )
        if numeric_positive.returncode != 0:
            raise AuditError(f"native printf signed range positive failed: {numeric_positive.stdout}{numeric_positive.stderr}")
        chain_messages = [positive[1], positive[2], positive[3], positive[0]]
        chain = subprocess.run([str(binary), "chain", *chain_messages], stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, check=False)
        if chain.returncode != 0 or "CHAIN 4 1 0 TARGET 72 1 0 16 pdic_max77705.ko\n" not in chain.stdout:
            raise AuditError(f"native row-72 initial chain fixture failed: {chain.stdout}{chain.stderr}")
        wrong_row = subprocess.run([str(binary), "wrong-row", *chain_messages], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, check=False)
        if wrong_row.returncode != 0 or "CHAIN 0 0 1\n" not in wrong_row.stdout:
            raise AuditError(f"native wrong-row context fixture failed: {wrong_row.stdout}{wrong_row.stderr}")
        wrong_order = subprocess.run([str(binary), "wrong-order", *chain_messages[1:]], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, check=False)
        if wrong_order.returncode != 0 or "CHAIN 0 0 1\n" not in wrong_order.stdout:
            raise AuditError(f"native wrong-order fixture failed: {wrong_order.stdout}{wrong_order.stderr}")
        auxiliary = subprocess.run([str(binary), "aux", positive[4], positive[5]], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, check=False)
        if auxiliary.returncode != 0 or "CHAIN 0 0 0\n" not in auxiliary.stdout:
            raise AuditError(f"native auxiliary-context fixture failed: {auxiliary.stdout}{auxiliary.stderr}")
        deferred_only = subprocess.run([str(binary), positive[-1]], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if deferred_only.returncode != 0 or "COUNTS 0 0 0 0 0 1\n" not in deferred_only.stdout:
            raise AuditError(f"deferred witness was promoted to initial: {deferred_only.stdout}{deferred_only.stderr}")
        negatives = (
            "pdic_max77705: max77705_muic_detect_dev USBC1:0X27, USBC2:0x05, BC:0x82",
            "pdic_max77705: max77705_muic_irq_init uiadc(1), chgtyp(2), dcdtmo(3), vbadc(4)",
            "pdic_max77705: max77705_muic_check_new_dev vps table match found at i(01), USB",
            "pdic_max77705: muic_lookup_vps_table (2) vps table match found at i(9), DCD Timeout ",
            "pdic_max77705: max77705_muic_irq_init uiadc(+1), chgtyp(2), dcdtmo(3), vbadc(4), vbusdet(5)",
            "pdic_max77705: max77705_muic_irq_init uiadc(-0), chgtyp(2), dcdtmo(3), vbadc(4), vbusdet(5)",
            "pdic_max77705: muic_lookup_vps_table (2) vps table match found at i(2147483648), USB",
            "pdic_max77705: muic_lookup_vps_table (2) vps table match found at i(4294967295), USB",
            "pdic_max77705: max77705_muic_print_reg_log USBC1:0x27, USBC2:0x05, BC:0x82, CC0:0x01, CC1:0x8, PD0:0x19, PD1:0x47 attached_dev:2",
        )
        for malformed in negatives:
            negative = subprocess.run([str(binary), malformed], stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True, check=False)
            if negative.returncode == 0:
                raise AuditError(f"native parser accepted malformed witness: {malformed}")
    return {"compiler": Path(compiler).name, "compiled": True, "executed": True,
            "parser_source_extracted_from_generated_runtime": True,
            "positive_forms": 6, "numeric_printf_range_qualified": True,
            "malformed_negative_count": len(negatives), "mask": 63,
            "row72_chain_qualified": True, "wrong_contexts_fail_closed": True,
            "auxiliary_does_not_advance_initial_chain": True}


def _extract_function(source: bytes, name: str) -> bytes:
    body = _c_function_body(source, name)
    token = name.encode("ascii") + b"("
    position = source.find(token)
    start = source.rfind(b"\n", 0, position) + 1
    return source[start:position] + body


def qualify_c_record_transport(runtime: bytes) -> dict[str, Any]:
    """Execute transformed framing, sequence, EPIPE, and byte-boundary code."""
    compiler = shutil_which("gcc")
    if compiler is None:
        raise AuditError("host C compiler unavailable for transport qualification")
    parser_start = runtime.find(b"#define P319_WITNESS_ABI_VERSION")
    record_start = runtime.find(b"static long p303_kmsg_record", parser_start)
    if parser_start < 0 or record_start < 0:
        raise AuditError("generated parser/record boundaries are absent")
    parser = _generated_parser_source(runtime).decode("ascii")
    record = _extract_function(runtime, "p303_kmsg_record").decode("ascii")
    drain = _extract_function(runtime, "p303_kmsg_drain").decode("ascii")
    with tempfile.TemporaryDirectory(prefix="p319-record-c-qualify-") as directory:
        root = Path(directory)
        source = root / "fixture.c"
        source.write_text(
            "#include <stdint.h>\n#include <stddef.h>\n#include <limits.h>\n#include <string.h>\n#include <stdio.h>\n#include <stdlib.h>\n"
            "static size_t cstr_len(const char *s) { return strlen(s); }\n"
            "static int p260_bytes_equal(const char *a, const char *b, size_t n) { return memcmp(a, b, n) == 0; }\n"
            "#define P303_DETAIL_KMSG_SEQUENCE_CONTRADICTION 0x6010L\n#define P303_DETAIL_KMSG_RING_LOSS 0x6011L\n#define P303_DETAIL_KMSG_READ_FAILED 0x6012L\n#define P303_DETAIL_KMSG_COUNT_OVERFLOW 0x6013L\n#define P303_DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION 0x6014L\n#define P303_EPIPE 32\n#define EAGAIN 11\n#define P303_KMSG_RECORD_CAPACITY 4096U\n#define P319_KMSG_MAX_DRAIN_RECORDS 256U\n#define P319_KMSG_MAX_DRAIN_BYTES 262144U\n#define P319_KMSG_MAX_TOTAL_RECORDS 4096U\n#define P319_KMSG_MAX_TOTAL_BYTES 1048576ULL\n"
            "static const char *p282_find_bytes(const char *s, size_t n, const char *needle) { size_t m = strlen(needle); if (m == 0 || m > n) return NULL; for (size_t i=0;i+m<=n;++i) if (memcmp(s+i,needle,m)==0) return s+i; return NULL; }\n"
            "static int p282_is_space(char value) { return value == ' ' || value == '\\t'; }\n"
            "static long p303_parse_hex(const char *s, const char *e, uint32_t *out) { (void)s;(void)e;(void)out; return -1; }\n"
            "static long p308_kmsg_observe(const char *s, size_t n) { (void)s;(void)n; return 0; }\n"
            "struct p303_kmsg_capture { int fd; uint8_t started; uint8_t final; uint8_t path_seen; uint8_t reset_mask; uint8_t sequence_seen; uint32_t readback_count; uint32_t first_offset; uint64_t previous_sequence; uint64_t first_sequence; uint64_t record_count; uint64_t record_bytes; uint32_t drain_count; uint32_t module_count; uint32_t module_drain_count; uint32_t drain_record_count; uint32_t drain_bytes; };\nstatic struct p303_kmsg_capture g_p303_kmsg = {.fd = 1};\n"
            + parser
            + record + "\n"
            "static int g_mode; static int g_stop_after; static char **g_records; static int g_record_count; static int g_record_index; static int g_batch_count;\n"
            "static long sys_read(int fd, char *buffer, size_t size) { (void)fd; if (g_mode == 2) return -P303_EPIPE; if (g_stop_after > 0 && g_batch_count >= g_stop_after) { g_batch_count = 0; return -EAGAIN; } if (g_record_index >= g_record_count) return -EAGAIN; size_t length = strlen(g_records[g_record_index++]); if (length > size) return -1; memcpy(buffer, g_records[g_record_index-1], length); ++g_batch_count; return (long)length; }\n"
            + drain
            + """
int main(int argc, char **argv) {
    if (argc < 2) return 3;
    if (strcmp(argv[1], "record") == 0) {
        for (int i = 2; i < argc; ++i) {
            long rc = p303_kmsg_record(argv[i], strlen(argv[i]));
            if (rc != 0) return 2;
        }
        return 0;
    }
    if (strcmp(argv[1], "epipe") == 0) {
        g_p303_kmsg.started = 1;
        g_mode = 2;
        long rc = p303_kmsg_drain();
        printf("RC %ld\\n", rc);
        return 0;
    }
    if (strcmp(argv[1], "drain-overflow") == 0) {
        g_p303_kmsg.started = 1;
        g_p303_kmsg.drain_count = UINT32_MAX;
        long rc = p303_kmsg_drain();
        printf("RC %ld DRAINS %u\\n", rc, g_p303_kmsg.drain_count);
        return 0;
    }
    if (strcmp(argv[1], "per-drain-bytes") == 0 ||
        strcmp(argv[1], "per-drain-records") == 0 ||
        strcmp(argv[1], "cumulative-bytes") == 0 ||
        strcmp(argv[1], "cumulative-records") == 0) {
        int repeats = 1;
        if (strcmp(argv[1], "cumulative-bytes") == 0) {
            g_stop_after = 64;
            repeats = 20;
        } else if (strcmp(argv[1], "cumulative-records") == 0) {
            g_stop_after = 128;
            repeats = 40;
        }
        g_p303_kmsg.started = 1;
        g_records = argv + 2;
        g_record_count = argc - 2;
        for (int i = 0; i < repeats; ++i) {
            long rc = p303_kmsg_drain();
            if (rc != 0) {
                printf("RC %ld RECORDS %llu BYTES %llu DRAINS %u\\n", rc,
                    (unsigned long long)g_p303_kmsg.record_count,
                    (unsigned long long)g_p303_kmsg.record_bytes,
                    g_p303_kmsg.drain_count);
                return 0;
            }
        }
        printf("RC 0 RECORDS %llu BYTES %llu DRAINS %u\\n",
            (unsigned long long)g_p303_kmsg.record_count,
            (unsigned long long)g_p303_kmsg.record_bytes,
            g_p303_kmsg.drain_count);
        return 0;
    }
    return 3;
}
""",
            encoding="ascii",
        )
        binary = root / "fixture"
        compiled = subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-o", str(binary), str(source)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if compiled.returncode != 0:
            detail = (compiled.stdout + compiled.stderr).decode("utf-8", "replace")
            raise AuditError(f"native record fixture compile failed: {detail[-4000:]}")
        good = ["6,10,1,-;x\n", "6,11,2,-;x\n"]
        if subprocess.run([str(binary), "record", *good], check=False).returncode != 0:
            raise AuditError("native record fixture rejected exact framing")
        for malformed in (b"6,10,1,-;x", b"6,10,1,-;x\ntrailing", b"6,010,1,-;x\n", b"6,10,1,;x\n", b"6,10,1,-,caller=Q2;x\n"):
            if subprocess.run([str(binary), "record", malformed.decode()], check=False).returncode == 0:
                raise AuditError("native record fixture accepted malformed framing")
        gap = subprocess.run([str(binary), "record", "6,10,1,-;x\n", "6,12,2,-;x\n"], check=False)
        if gap.returncode == 0:
            raise AuditError("native record fixture accepted sequence gap")
        epipe = subprocess.run([str(binary), "epipe"], stdout=subprocess.PIPE, text=True, check=False)
        if "RC 24593" not in epipe.stdout:
            raise AuditError(f"native EPIPE gate differs: {epipe.stdout}")
        def stats(output: str) -> dict[str, int]:
            parts = output.split()
            if len(parts) != 8 or parts[0] != "RC" or parts[2] != "RECORDS" \
                    or parts[4] != "BYTES" or parts[6] != "DRAINS":
                raise AuditError(f"native transport stats shape differs: {output}")
            return {
                "rc": int(parts[1]), "records": int(parts[3]),
                "bytes": int(parts[5]), "drains": int(parts[7]),
            }
        large_records = [f"6,{10 + index},1,-;" + "x" * 4080 + "\n" for index in range(270)]
        per_drain_bytes = subprocess.run(
            [str(binary), "per-drain-bytes", *large_records[:65]],
            stdout=subprocess.PIPE, text=True, check=False,
        )
        if not per_drain_bytes.stdout.startswith("RC 24610 RECORDS 64 "):
            raise AuditError(f"native per-drain byte gate differs: {per_drain_bytes.stdout}")
        per_drain_byte_stats = stats(per_drain_bytes.stdout)
        small_records = [f"6,{10 + index},1,-;x\n" for index in range(257)]
        per_drain_records = subprocess.run(
            [str(binary), "per-drain-records", *small_records],
            stdout=subprocess.PIPE, text=True, check=False,
        )
        if not per_drain_records.stdout.startswith("RC 24610 RECORDS 256 "):
            raise AuditError(f"native per-drain record gate differs: {per_drain_records.stdout}")
        per_drain_record_stats = stats(per_drain_records.stdout)
        cumulative_bytes = subprocess.run(
            [str(binary), "cumulative-bytes", *large_records],
            stdout=subprocess.PIPE, text=True, check=False,
        )
        byte_parts = cumulative_bytes.stdout.split()
        if (
            not cumulative_bytes.stdout.startswith("RC 24610")
            or int(byte_parts[3]) != 256
            or int(byte_parts[5]) < 1_040_000
            or int(byte_parts[7]) < 5
        ):
            raise AuditError(f"native cumulative byte gate differs: {cumulative_bytes.stdout}")
        cumulative_byte_stats = stats(cumulative_bytes.stdout)
        cumulative_records = subprocess.run(
            [str(binary), "cumulative-records", *[
                f"6,{10 + index},1,-;x\n" for index in range(5140)
            ]],
            stdout=subprocess.PIPE, text=True, check=False,
        )
        record_parts = cumulative_records.stdout.split()
        if (
            not cumulative_records.stdout.startswith("RC 24610")
            or int(record_parts[3]) != 4096
            or int(record_parts[5]) >= 1_048_576
            or int(record_parts[7]) < 33
        ):
            raise AuditError(f"native cumulative record gate differs: {cumulative_records.stdout}")
        cumulative_record_stats = stats(cumulative_records.stdout)
        overflow = subprocess.run(
            [str(binary), "drain-overflow"], stdout=subprocess.PIPE, text=True, check=False,
        )
        if overflow.stdout != "RC 24609 DRAINS 4294967295\n":
            raise AuditError(f"native drain counter overflow gate differs: {overflow.stdout}")
        overflow_stats = {"rc": 24609, "drains": 4294967295}
    return {"compiler": Path(compiler).name, "compiled": True, "executed": True,
            "exact_framing_positive": True, "newline_and_trailing_negative": True,
            "sequence_gap_negative": True, "epipe_negative": True,
            "per_drain_byte_limit_negative": True,
            "per_drain_record_limit_negative": True,
            "cumulative_byte_limit_negative": True,
            "cumulative_record_limit_negative": True,
            "drain_counter_overflow_negative": True,
            "limit_case_stats": {
                "per_drain_bytes": per_drain_byte_stats,
                "per_drain_records": per_drain_record_stats,
                "cumulative_bytes": cumulative_byte_stats,
                "cumulative_records": cumulative_record_stats,
                "drain_overflow": overflow_stats,
            },
            "parser_source_extracted_from_generated_runtime": True}


def shutil_which(name: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def build_result(inputs: dict[str, bytes]) -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise AuditError("unbound parser cannot build authoritative result")
    base_receipt = inputs["base-result.json"]
    base = _base_sources(inputs)
    generated = materialized_bytes(base)
    preserved_generated = _generated_sources(inputs)
    if preserved_generated != generated:
        raise AuditError("preserved generated source differs from deterministic transform")
    source_audit = audit_bound_driver_sources(inputs)
    materialization = audit_materialization(base, generated)
    manifest_binding = audit_capture_manifest(inputs["abl-capture-manifest.json"])
    corpus = qualify_corpus(inputs["corpus-capture.bin"])
    with tempfile.TemporaryDirectory(prefix="p319-witness-syntax-") as directory:
        syntax_root = Path(directory)
        for name, payload in generated.items():
            (syntax_root / name).write_bytes(payload)
        syntax = syntax_compile(syntax_root)
    native_parser = qualify_c_parser_native(generated["s22plus_fyg8_p290_e3_runtime.inc.c"])
    native_transport = qualify_c_record_transport(generated["s22plus_fyg8_p290_e3_runtime.inc.c"])
    result = {
        "schema": SCHEMA, "verdict": VERDICT, "status": "IMPLEMENTED_REVIEW_PENDING", "target": TARGET,
        "scope": {"tier": "H0", "host_only": True, "device_contact": False, "adb_commands": 0,
                   "usb_actions": 0, "odin_invocations": 0, "candidate_transfers": 0,
                   "rollback_transfers": 0, "recovery_actions": 0, "replay": False,
                   "live_authority_created": False},
        "inputs": {key: identity(value) for key, value in sorted(inputs.items())},
        "implementation": {"auditor": identity(_BOUND_AUDITOR_SOURCE)},
        "source_bound_grammar": source_audit,
        "corpus_manifest_binding": manifest_binding,
        "materialization": materialization,
        "corpus_qualification": corpus,
        "static_validation": syntax,
        "native_parser_qualification": native_parser,
        "native_transport_qualification": native_transport,
        "transport_limits": {"record_capacity_bytes": MAX_RECORD_BYTES,
                             "per_drain_record_limit": MAX_DRAIN_RECORDS,
                             "per_drain_byte_limit": MAX_DRAIN_BYTES,
                             "cumulative_record_limit": MAX_TOTAL_RECORDS,
                             "cumulative_byte_limit": MAX_TOTAL_BYTES,
                             "positive_amount_accounted_before_parse": True,
                             "first_and_last_sequence_retained": True,
                             "epipe_fail_closed": True, "sequence_gap_fail_closed": True},
        "structured_summary_state": {"name": SUMMARY_STATE, "version": 1,
                                      "host_qualified": True, "candidate_source_compiled": True,
                                      "canonical_encoding_defined": False,
                                      "successful_module_indices_bound": [69, 71, 72],
                                      "initial_chain_context": "only active module index 72 drain",
                                      "initial_chain_order": ["irq", "initial_status", "classification_form1", "probe"],
                                      "initial_chain_is_no_proof_until_runtime_summary": True,
                                      "carrier_published": False, "envelope_v4_reinterpreted": False,
                                      "envelope_v5_defined": False},
        "conclusion": {
            "source_derived_grammar": True,
            "both_classification_forms_bound": True,
            "deferred_seven_byte_line_auxiliary_only": True,
            "deferred_line_can_satisfy_initial_witness": False,
            "direct_and_folded_loops_share_post_load_drain": True,
            "initial_chain_requires_pdic_row72_context": True,
            "initial_chain_ambiguous_without_runtime_context": True,
            "raw_printk_is_not_authority": True,
            "carrier_publication": False,
            "envelope_v4_unchanged": materialization["envelope_v4_unchanged"][
                "base_generated_function_bytes_identical"
            ],
            "envelope_v4_audit": materialization["envelope_v4_unchanged"],
            "existing_candidate_witness_transport_obligation_resolved": False,
            "independent_review_required": True,
            "next_step": "independent changed-closure review, then decide explicit Carrier/Envelope-v5 ABI separately",
        },
    }
    if stable_bytes(AUDITOR, label="post-run parser auditor", maximum=2 << 20) != _BOUND_AUDITOR_SOURCE:
        raise AuditError("parser auditor changed during execution")
    return result


def encode(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def publish_result(root: Path, payload: bytes) -> None:
    path = _paths(root)["result"]
    _write_exclusive(path, payload)
    _fsync_directory(root)
    stable_bytes(path, label="successor parser receipt", maximum=512 << 10,
                 expected_size=len(payload), expected_sha256=sha256(payload),
                 required_mode=0o400, required_nlink=1)


def run(materialize: bool, output_root: Path = OUTPUT_ROOT) -> tuple[dict[str, Any], bytes]:
    global OUTPUT_ROOT
    previous = OUTPUT_ROOT
    OUTPUT_ROOT = output_root.absolute()
    try:
        inputs = load_inputs(materialize, output_root)
        result = build_result(inputs)
        return result, encode(result)
    finally:
        OUTPUT_ROOT = previous


def load_bound_auditor() -> Any:
    payload = stable_bytes(AUDITOR, label="parser auditor bootstrap", maximum=2 << 20)
    module = types.ModuleType("s22plus_fyg8_p319_candidate_witness_parser_v2_bound")
    module.__file__ = str(AUDITOR); module.__package__ = ""
    module.__dict__["_P319_WITNESS_PARSER_BOUND_SOURCE"] = payload
    sys.modules[module.__name__] = module
    try:
        exec(compile(payload.decode("utf-8"), str(AUDITOR), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError("parser auditor bound execution failed") from exc
    return module


def main() -> int:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        return load_bound_auditor().main()
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--audit-only", action="store_true")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    root = args.output_root.absolute()
    _, payload = run(args.write, root)
    if args.write:
        publish_result(root, payload)
    else:
        existing = stable_bytes(_paths(root)["result"], label="successor parser receipt", maximum=512 << 10,
                                expected_size=len(payload), expected_sha256=sha256(payload),
                                required_mode=0o400, required_nlink=1)
        if existing != payload:
            raise AuditError("successor parser receipt differs")
    print(f"{VERDICT} {len(payload)} {sha256(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
