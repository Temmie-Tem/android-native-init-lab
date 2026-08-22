#!/usr/bin/env python3
"""Validate the A90 RTIC measurement-parameter/Image binding.

This is deliberately a host-only parser.  It accepts only the Samsung
``UNCOMPRESSED_IMG`` wrapper, walks the FDTs which begin exactly at the end of
the raw Image, and checks the one RTIC FDT against the bytes in that Image.
No external tools, subprocesses, USB transports, or device paths are used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import struct
import sys
from dataclasses import dataclass
from typing import Iterable


SCHEMA = "a90-rtic-mp-consistency-v1"
WRAPPER_MAGIC = b"UNCOMPRESSED_IMG"
WRAPPER_HEADER_SIZE = len(WRAPPER_MAGIC) + 4
FDT_MAGIC = 0xD00DFEED
FDT_HEADER_SIZE = 40
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9
MP_DATA_SIZE = struct.calcsize("<QQI32s")
RTIC_BASE_ADDRESS = 0xFFFFFF8008080000
RTIC_MARKER = b"--==!!!RTIC MP!!!==--\0\0\0"
RTIC_INTERFACE_SIZE = struct.calcsize("<HH")
RTIC_INTERFACE_MAJOR = 30
RTIC_INTERFACE_MINOR = 3


class ValidationError(ValueError):
    """A deterministic validation failure represented by a short reason code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class FdtBlob:
    index: int
    offset: int
    size: int
    root_properties: dict[str, tuple[bytes, ...]]


@dataclass(frozen=True)
class KernelParts:
    wrapper: bytes
    image: bytes
    image_offset: int
    image_size: int
    fdts: tuple[FdtBlob, ...]


def _align4(value: int) -> int:
    return (value + 3) & ~3


def _read_cstring(data: bytes, offset: int, end: int, reason: str) -> tuple[str, int]:
    if offset < 0 or offset >= end:
        raise ValidationError(reason)
    nul = data.find(b"\0", offset, end)
    if nul < 0:
        raise ValidationError(reason)
    try:
        value = data[offset:nul].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValidationError(reason) from exc
    return value, _align4(nul + 1)


def _parse_fdt(blob: bytes, index: int, offset: int) -> FdtBlob:
    if len(blob) < FDT_HEADER_SIZE:
        raise ValidationError("fdt-header-truncated")
    header = struct.unpack_from(">10I", blob, 0)
    (
        magic,
        total_size,
        off_struct,
        off_strings,
        off_mem_rsvmap,
        _version,
        _last_comp_version,
        _boot_cpuid_phys,
        size_strings,
        size_struct,
    ) = header
    if magic != FDT_MAGIC:
        raise ValidationError("fdt-magic-invalid")
    if total_size != len(blob):
        raise ValidationError("fdt-total-size-mismatch")
    if off_mem_rsvmap % 8 or off_mem_rsvmap < FDT_HEADER_SIZE:
        raise ValidationError("fdt-reserve-map-offset-invalid")
    if off_mem_rsvmap + 16 > total_size:
        raise ValidationError("fdt-reserve-map-out-of-bounds")
    struct_end = off_struct + size_struct
    strings_end = off_strings + size_strings
    if off_struct % 4 or off_strings % 4:
        raise ValidationError("fdt-section-alignment-invalid")
    if off_struct < FDT_HEADER_SIZE or off_strings < FDT_HEADER_SIZE:
        raise ValidationError("fdt-section-offset-invalid")
    if struct_end > total_size or strings_end > total_size:
        raise ValidationError("fdt-section-out-of-bounds")
    if size_struct < 12:
        raise ValidationError("fdt-structure-too-short")
    if size_strings and not (struct_end <= off_strings or strings_end <= off_struct):
        raise ValidationError("fdt-sections-overlap")

    properties: dict[str, list[bytes]] = {}
    stack: list[str] = []
    cursor = off_struct
    depth = 0
    saw_root = False
    closed_root = False
    saw_end = False
    while cursor < struct_end:
        if cursor + 4 > struct_end:
            raise ValidationError("fdt-token-truncated")
        token = struct.unpack_from(">I", blob, cursor)[0]
        cursor += 4
        if saw_end:
            if token != FDT_NOP:
                raise ValidationError("fdt-token-after-end")
            continue
        if token == FDT_BEGIN_NODE:
            name, cursor = _read_cstring(blob, cursor, struct_end, "fdt-node-name-invalid")
            if depth == 0:
                if saw_root or name:
                    raise ValidationError("fdt-root-node-invalid")
                saw_root = True
            else:
                stack.append(name)
            depth += 1
        elif token == FDT_END_NODE:
            if depth == 0:
                raise ValidationError("fdt-end-node-underflow")
            depth -= 1
            if depth:
                stack.pop()
            else:
                if stack:
                    raise ValidationError("fdt-root-stack-invalid")
                closed_root = True
        elif token == FDT_PROP:
            if depth == 0:
                raise ValidationError("fdt-property-outside-node")
            if cursor + 8 > struct_end:
                raise ValidationError("fdt-property-header-truncated")
            length, name_offset = struct.unpack_from(">II", blob, cursor)
            cursor += 8
            value_end = cursor + length
            padded_end = _align4(value_end)
            if value_end > struct_end or padded_end > struct_end:
                raise ValidationError("fdt-property-out-of-bounds")
            if name_offset >= size_strings:
                raise ValidationError("fdt-property-name-out-of-bounds")
            name, _ = _read_cstring(
                blob,
                off_strings + name_offset,
                strings_end,
                "fdt-property-name-invalid",
            )
            path = "/" + "/".join(stack) if stack else "/"
            # Root properties are the only values consumed by this validator.
            if path == "/":
                properties.setdefault(name, []).append(blob[cursor:value_end])
            cursor = padded_end
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            if depth != 0 or not saw_root or not closed_root:
                raise ValidationError("fdt-end-before-root-close")
            saw_end = True
        else:
            raise ValidationError("fdt-token-invalid")

    if not saw_end or depth != 0 or not closed_root:
        raise ValidationError("fdt-end-missing")
    frozen = {name: tuple(values) for name, values in properties.items()}
    return FdtBlob(index=index, offset=offset, size=len(blob), root_properties=frozen)


def _enumerate_fdts(wrapper: bytes, image_end: int) -> tuple[FdtBlob, ...]:
    cursor = image_end
    blobs: list[FdtBlob] = []
    while cursor < len(wrapper):
        remaining = len(wrapper) - cursor
        if remaining < FDT_HEADER_SIZE:
            raise ValidationError("fdt-header-truncated")
        if struct.unpack_from(">I", wrapper, cursor)[0] != FDT_MAGIC:
            raise ValidationError("fdt-magic-missing-at-tail")
        total_size = struct.unpack_from(">I", wrapper, cursor + 4)[0]
        if total_size < FDT_HEADER_SIZE:
            raise ValidationError("fdt-total-size-too-small")
        if total_size > remaining:
            raise ValidationError("fdt-total-size-out-of-bounds")
        blob = wrapper[cursor : cursor + total_size]
        blobs.append(_parse_fdt(blob, len(blobs), cursor))
        cursor += total_size
    return tuple(blobs)


def _parse_wrapper(wrapper: bytes) -> KernelParts:
    if len(wrapper) < WRAPPER_HEADER_SIZE:
        raise ValidationError("wrapper-header-truncated")
    if wrapper[: len(WRAPPER_MAGIC)] != WRAPPER_MAGIC:
        raise ValidationError("wrapper-magic-invalid")
    image_size = struct.unpack_from("<I", wrapper, len(WRAPPER_MAGIC))[0]
    image_offset = WRAPPER_HEADER_SIZE
    image_end = image_offset + image_size
    if image_end > len(wrapper):
        raise ValidationError("wrapper-image-out-of-bounds")
    image = wrapper[image_offset:image_end]
    fdts = _enumerate_fdts(wrapper, image_end)
    return KernelParts(wrapper, image, image_offset, image_size, fdts)


def _fdt_summary(fdts: Iterable[FdtBlob]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for fdt in fdts:
        qcom_values = fdt.root_properties.get("qcom,rtic-id", ())
        has_id_one = any(
            len(value) == 4 and struct.unpack(">I", value)[0] == 1
            for value in qcom_values
        )
        result.append(
            {
                "index": fdt.index,
                "offset": fdt.offset,
                "size": fdt.size,
                "has_qcom_rtic_id_1": has_id_one,
                "mp_data_count": len(fdt.root_properties.get("MP_DATA", ())),
            }
        )
    return result


def _rtic_candidate(fdts: Iterable[FdtBlob]) -> list[FdtBlob]:
    candidates: list[FdtBlob] = []
    for fdt in fdts:
        qcom_values = fdt.root_properties.get("qcom,rtic-id", ())
        mp_values = fdt.root_properties.get("MP_DATA", ())
        if (
            len(qcom_values) == 1
            and len(qcom_values[0]) == 4
            and struct.unpack(">I", qcom_values[0])[0] == 1
            and len(mp_values) == 1
        ):
            candidates.append(fdt)
    return candidates


def _has_rtic_id_one(fdt: FdtBlob) -> bool:
    return any(
        len(value) == 4 and struct.unpack(">I", value)[0] == 1
        for value in fdt.root_properties.get("qcom,rtic-id", ())
    )


def _has_additional_rtic_metadata(fdts: Iterable[FdtBlob], candidate: FdtBlob) -> bool:
    for fdt in fdts:
        if fdt is candidate:
            continue
        if _has_rtic_id_one(fdt) or "MP_DATA" in fdt.root_properties:
            return True
    return False


def _validate_rtic(parts: KernelParts, candidate: FdtBlob) -> tuple[list[str], dict[str, object]]:
    reasons: list[str] = []
    values = candidate.root_properties.get("MP_DATA", ())
    evidence: dict[str, object] = {
        "fdt_index": candidate.index,
        "fdt_offset": candidate.offset,
        "fdt_size": candidate.size,
        "mp_va_addr": None,
        "mp_offset": None,
        "mp_size": None,
        "marker_offset": None,
        "expected_sha256": None,
        "actual_sha256": None,
        "interface_major": None,
        "interface_minor": None,
        "base_relation": False,
    }
    if len(values) != 1:
        reasons.append("mp-data-cardinality-invalid")
        return reasons, evidence
    value = values[0]
    if len(value) != MP_DATA_SIZE:
        reasons.append("mp-data-size-invalid")
        return reasons, evidence

    mp_va_addr, mp_offset, mp_size, expected_sha = struct.unpack("<QQI32s", value)
    evidence.update(
        {
            "mp_va_addr": f"0x{mp_va_addr:016x}",
            "mp_offset": mp_offset,
            "mp_size": mp_size,
            "marker_offset": mp_offset,
            "expected_sha256": expected_sha.hex(),
            "base_relation": mp_va_addr - mp_offset == RTIC_BASE_ADDRESS,
        }
    )
    if not evidence["base_relation"]:
        reasons.append("mp-va-offset-relation-invalid")

    image_size = len(parts.image)
    in_bounds = 0 <= mp_offset <= image_size and 0 <= mp_size <= image_size - mp_offset
    if not in_bounds:
        reasons.append("mp-range-out-of-bounds")
        return reasons, evidence

    payload = parts.image[mp_offset : mp_offset + mp_size]
    actual_sha = hashlib.sha256(payload).hexdigest()
    evidence["actual_sha256"] = actual_sha
    if actual_sha != expected_sha.hex():
        reasons.append("mp-sha256-mismatch")

    measured_end = mp_offset + mp_size
    marker_end = mp_offset + len(RTIC_MARKER)
    if marker_end > measured_end:
        reasons.append("mp-range-too-small-for-marker")
    elif parts.image[mp_offset : mp_offset + len(RTIC_MARKER)] != RTIC_MARKER:
        reasons.append("rtic-marker-mismatch")

    interface_offset = mp_offset + len(RTIC_MARKER)
    interface_end = interface_offset + RTIC_INTERFACE_SIZE
    if interface_end > measured_end:
        reasons.append("mp-range-too-small-for-interface")
    elif interface_end > image_size:
        reasons.append("rtic-interface-out-of-bounds")
    else:
        major, minor = struct.unpack_from("<HH", parts.image, interface_offset)
        evidence["interface_major"] = major
        evidence["interface_minor"] = minor
        if (major, minor) != (RTIC_INTERFACE_MAJOR, RTIC_INTERFACE_MINOR):
            reasons.append("rtic-interface-version-mismatch")
    return reasons, evidence


def validate_kernel_bytes(wrapper: bytes) -> dict[str, object]:
    """Validate one wrapper and return the deterministic JSON-compatible result."""

    result: dict[str, object] = {
        "schema": SCHEMA,
        "decision": "FAIL",
        "reasons": [],
    }
    try:
        parts = _parse_wrapper(wrapper)
    except ValidationError as exc:
        result["reasons"] = [exc.reason]
        return result

    result["wrapper"] = {
        "file_size": len(parts.wrapper),
        "wrapper_sha256": hashlib.sha256(parts.wrapper).hexdigest(),
        "image_offset": parts.image_offset,
        "image_size": parts.image_size,
        "image_sha256": hashlib.sha256(parts.image).hexdigest(),
        "tail_size": len(parts.wrapper) - (parts.image_offset + parts.image_size),
    }
    fdt_summary = _fdt_summary(parts.fdts)
    result["fdts"] = fdt_summary

    candidates = _rtic_candidate(parts.fdts)
    if len(candidates) == 0:
        reasons = []
        has_id_one = any(entry["has_qcom_rtic_id_1"] for entry in fdt_summary)
        has_mp_data = any(entry["mp_data_count"] for entry in fdt_summary)
        if has_id_one:
            reasons.append("rtic-mp-data-missing-or-cardinality-invalid")
        elif has_mp_data:
            reasons.append("rtic-id-missing-or-invalid")
        else:
            reasons.append("rtic-dtb-absent")
        result["reasons"] = reasons
        return result
    if len(candidates) != 1:
        result["reasons"] = ["multiple-rtic-dtbs"]
        return result
    if _has_additional_rtic_metadata(parts.fdts, candidates[0]):
        result["reasons"] = ["additional-rtic-metadata"]
        return result

    reasons, evidence = _validate_rtic(parts, candidates[0])
    result["rtic"] = evidence
    result["reasons"] = reasons
    if not reasons:
        result["decision"] = "PASS"
    return result


def _read_regular_kernel(path: Path) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValidationError("kernel-path-unreadable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValidationError("kernel-not-regular-file")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValidationError("kernel-read-failed") from exc


def validate_kernel_path(path: Path) -> dict[str, object]:
    try:
        return validate_kernel_bytes(_read_regular_kernel(path))
    except ValidationError as exc:
        return {"schema": SCHEMA, "decision": "FAIL", "reasons": [exc.reason]}


def _parse_args(argv: list[str]) -> tuple[Path | None, str | None]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--kernel", dest="kernel_option")
    parser.add_argument("path", nargs="?")
    try:
        args, unknown = parser.parse_known_args(argv)
    except SystemExit:
        return None, "invalid-command-line"
    if unknown:
        return None, "unknown-command-line-option"
    if args.kernel_option and args.path and args.kernel_option != args.path:
        return None, "multiple-kernel-paths"
    selected = args.kernel_option or args.path
    if not selected:
        return None, "kernel-path-required"
    return Path(selected), None


def main(argv: list[str] | None = None) -> int:
    path, error = _parse_args(list(sys.argv[1:] if argv is None else argv))
    if error:
        result: dict[str, object] = {"schema": SCHEMA, "decision": "FAIL", "reasons": [error]}
    else:
        assert path is not None
        result = validate_kernel_path(path)
    sys.stdout.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return 0 if result.get("decision") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
