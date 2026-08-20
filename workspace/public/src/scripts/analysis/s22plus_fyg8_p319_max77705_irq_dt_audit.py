#!/usr/bin/env python3
"""Bind the FYG8 MAX77705 DT, parent IRQ, nested MUIC IRQ, and live attach.

This is a host-only P3.19 analysis.  It reads the exact stock DTBO and shipped
MFD/PDIC modules, their exact source counterparts, and the closed
manifest-defined retained stock corpus.  It never contacts a device and grants
no D0/D1/F1 or live authority.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import stat
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[5]
PRIVATE = REPO / "workspace/private"
OUTPUT_V1 = PRIVATE / (
    "outputs/s22plus_fyg8_p319/"
    "max77705-irq-dt-audit-20260820-01/result.json"
)
OUTPUT_V2 = PRIVATE / (
    "outputs/s22plus_fyg8_p319/"
    "max77705-irq-dt-audit-20260820-02/result.json"
)
OUTPUT_V3 = PRIVATE / (
    "outputs/s22plus_fyg8_p319/"
    "max77705-irq-dt-audit-20260820-03/result.json"
)
OUTPUT_V4 = PRIVATE / (
    "outputs/s22plus_fyg8_p319/"
    "max77705-irq-dt-audit-20260820-04/result.json"
)
OUTPUT_ROOT = PRIVATE / "outputs/s22plus_fyg8_p319/max77705-irq-dt-audit-20260820-05"
OUTPUT = OUTPUT_ROOT / "result.json"
SNAPSHOT_ROOT = OUTPUT_ROOT / "inputs"

SCHEMA = "s22plus-fyg8-p319-max77705-irq-dt-audit-v2"
VERDICT = "PASS_P319_MAX77705_IRQ_DT_CORPUS_CHAIN_H0"

KERNEL = (
    PRIVATE
    / "work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel"
)
OSRC = (
    PRIVATE
    / "inputs/s22plus_kernel_source/S906NKSS7FYG8_osrc/Kernel/kernel_platform/"
    "msm-kernel"
)
DTBO = (
    PRIVATE
    / "inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/dtbo.img"
)
CORPUS_MANIFEST = (
    PRIVATE / "outputs/s22plus_fyg8_p319/abl-capture-manifest.json"
)


class AuditError(RuntimeError):
    pass


@dataclass(frozen=True)
class InputSpec:
    size: int
    sha256: str
    source: Path
    snapshot_name: str | None
    limit: int = 2 * 1024 * 1024


INPUTS: dict[str, InputSpec] = {
    "stock_dtbo": InputSpec(
        8_388_608,
        "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c",
        DTBO,
        None,
        9 * 1024 * 1024,
    ),
    "active_r12_dts": InputSpec(
        1_086_127,
        "aff997ab764b7be8ff66d57b0633fa11c881a108f8fabea186cf5a4216844822",
        OSRC / "arch/arm64/boot/dts/samsung/rainbow/g0q/g0q_kor_singlex_w00_r12.dts",
        "g0q_kor_singlex_w00_r12.dts",
    ),
    "mfd_max77705_module": InputSpec(
        125_840,
        "26f238730604789293db237b2bcdc4d44c5f63c263e4298f6e8e28b85d0f6f94",
        Path("/mnt/android-lab-logical/vendor_dlkm/lib/modules/mfd_max77705.ko"),
        "mfd_max77705.ko",
    ),
    "pdic_max77705_module": InputSpec(
        423_456,
        "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db",
        Path("/mnt/android-lab-logical/vendor_dlkm/lib/modules/pdic_max77705.ko"),
        "pdic_max77705.ko",
    ),
    "max77705_mfd_source": InputSpec(
        40_632,
        "523fe8b765f53b775efc9f51a9cc1ddfc67088e8375894fe43d273bbde23db46",
        KERNEL / "drivers/mfd/maxim/max77705.c",
        "max77705.c",
    ),
    "max77705_irq_source": InputSpec(
        16_518,
        "5ddbe1dee81c5756fc86c8c47264d77b4049c1ca7063647abbdc5c1cbc5cfabc",
        KERNEL / "drivers/mfd/maxim/max77705-irq.c",
        "max77705-irq.c",
    ),
    "max77705_muic_source": InputSpec(
        76_141,
        "bfdb034d7571ca233202221cdc8cdfe68bab3e837afea9c4b5a37378ed7acbab",
        KERNEL / "drivers/usb/typec/maxim/max77705-muic.c",
        "max77705-muic.c",
    ),
    "max77705_usbc_source": InputSpec(
        124_569,
        "4dabc4b25e99e26c662748934a6a98775073683832f08652e15762f4689a3e3d",
        KERNEL / "drivers/usb/typec/maxim/max77705_usbc.c",
        "max77705_usbc.c",
    ),
    "max77705_private_header": InputSpec(
        13_063,
        "a205dfc0743d38f7684a046f5aef26d466f5feef3713fe0d19bc58134a7c441e",
        KERNEL / "include/linux/mfd/max77705-private.h",
        "max77705-private.h",
    ),
    "max77705_mfd_header": InputSpec(
        2_354,
        "99da4c06b2e635fd497ff4af4daed6af06f566a7f48b55b9695c5134f42d794f",
        KERNEL / "include/linux/mfd/max77705.h",
        "max77705.h",
    ),
    "irq_manage_source": InputSpec(
        75_513,
        "9edc980d13f5b06f0311cf341a77806e9ea15191e4dcef6fa09d1504e621a7aa",
        KERNEL / "kernel/irq/manage.c",
        "irq-manage.c",
    ),
    "sched_header": InputSpec(
        60_368,
        "06da1d46f1aff24e2e090ab2ac9dac59a9da70db3022f12cba22b87d53c2ecca",
        KERNEL / "include/linux/sched.h",
        "sched.h",
    ),
    "abl_capture_manifest": InputSpec(
        107_997,
        "aa2d19ea09d3317dcff9961ee51eec579d7e912f4b98115fa5bf7994fff16f90",
        CORPUS_MANIFEST,
        "abl-capture-manifest.json",
        128 * 1024,
    ),
}


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _stable_read(path: Path, label: str, limit: int) -> bytes:
    try:
        before_l = path.lstat()
        before = path.stat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable: {path}") from exc
    if stat.S_ISLNK(before_l.st_mode) or not stat.S_ISREG(before.st_mode):
        raise AuditError(f"{label} is not a direct regular file")
    if before.st_nlink < 1 or not 0 < before.st_size <= limit:
        raise AuditError(f"{label} size/link contract differs")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
        inside = os.fstat(stream.fileno())
    after = path.stat()
    identity = lambda item: (  # noqa: E731
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
    )
    if identity(before) != identity(inside) or identity(inside) != identity(after):
        raise AuditError(f"{label} changed while read")
    if len(data) != before.st_size or len(data) > limit:
        raise AuditError(f"{label} read length differs")
    return data


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    current = path
    while current != PRIVATE.parent:
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise AuditError(f"private output parent is indirect: {current}")
        if current == OUTPUT_ROOT or OUTPUT_ROOT in current.parents:
            if stat.S_IMODE(info.st_mode) != 0o700:
                os.chmod(current, 0o700, follow_symlinks=False)
                info = current.lstat()
                if stat.S_IMODE(info.st_mode) != 0o700:
                    raise AuditError(f"private output directory mode differs: {current}")
        if current == PRIVATE:
            break
        current = current.parent


def _write_exclusive(path: Path, data: bytes, mode: int = 0o400) -> None:
    _ensure_private_dir(path.parent)
    if path.exists():
        existing = _stable_read(path, f"existing {path.name}", max(len(data), 1) + 1)
        info = path.stat()
        if existing != data or stat.S_IMODE(info.st_mode) != mode or info.st_nlink != 1:
            raise AuditError(f"existing private output differs: {path}")
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        os.fchmod(fd, mode)
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise AuditError(f"short private output write: {path}")
            view = view[written:]
        os.fsync(fd)
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != mode
            or info.st_nlink != 1
            or info.st_size != len(data)
        ):
            raise AuditError(f"private output metadata differs: {path}")
    finally:
        os.close(fd)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def load_inputs(*, materialize: bool = True) -> dict[str, bytes]:
    loaded: dict[str, bytes] = {}
    for name, spec in INPUTS.items():
        snapshot = SNAPSHOT_ROOT / spec.snapshot_name if spec.snapshot_name else None
        if snapshot is not None and snapshot.exists():
            data = _stable_read(snapshot, f"P3.19 snapshot {name}", spec.limit)
            info = snapshot.stat()
            if stat.S_IMODE(info.st_mode) != 0o400 or info.st_nlink != 1:
                raise AuditError(f"P3.19 snapshot mode differs: {name}")
            if spec.source.exists():
                source = _stable_read(spec.source, f"P3.19 source {name}", spec.limit)
                if source != data:
                    raise AuditError(f"P3.19 source/snapshot bytes differ: {name}")
        else:
            data = _stable_read(spec.source, f"P3.19 source {name}", spec.limit)
            if snapshot is not None and materialize:
                _write_exclusive(snapshot, data)
        if receipt(data) != {"size": spec.size, "sha256": spec.sha256}:
            raise AuditError(f"P3.19 exact input identity differs: {name}")
        loaded[name] = data
    return loaded


MANIFEST_KEYS = {
    "bc_ctrl1_value_counts",
    "bc_ctrl1_value_counts_download",
    "bc_ctrl1_value_counts_normal",
    "captures",
    "counts",
    "distinct_captures",
    "duplicate_files_collapsed",
    "inclusion_criterion",
    "kernel_side",
    "matching_files",
    "muic_opcode_counts",
    "schema",
    "setpath_values_observed",
    "unreadable_or_short_files",
}
CAPTURE_KEYS = {
    "bc_ctrl1_reads",
    "boot_segments",
    "candidate_markers",
    "download_mode",
    "has_abl_stage",
    "has_max7770x_irq_thread",
    "mission_mode",
    "muic_notifier_tags",
    "muic_opcodes",
    "paths",
    "setpath_occurrences",
    "setpath_values",
    "sha256",
    "stock_daemons",
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_corpus_manifest(data: bytes) -> dict[str, Any]:
    try:
        manifest = json.loads(
            data,
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(
                AuditError(f"non-finite JSON number: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError("capture manifest JSON is malformed") from exc
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_KEYS:
        raise AuditError("capture manifest key set differs")
    if manifest.get("schema") != "s22plus-fyg8-p319-abl-capture-manifest-v3":
        raise AuditError("capture manifest schema differs")
    for key in (
        "matching_files",
        "unreadable_or_short_files",
        "distinct_captures",
        "duplicate_files_collapsed",
    ):
        if type(manifest.get(key)) is not int or manifest[key] < 0:
            raise AuditError(f"capture manifest scalar differs: {key}")
    if (
        manifest["unreadable_or_short_files"] != 0
        or manifest["matching_files"] < manifest["distinct_captures"]
        or manifest["duplicate_files_collapsed"]
        != manifest["matching_files"] - manifest["distinct_captures"]
    ):
        raise AuditError("capture manifest population arithmetic differs")
    if manifest.get("inclusion_criterion") != {
        "root": "workspace/private",
        "exact_size_bytes": 2_097_136,
        "selected_by_name_or_run": False,
    }:
        raise AuditError("capture manifest inclusion criterion differs")
    kernel_side = manifest.get("kernel_side")
    if (
        not isinstance(kernel_side, dict)
        or set(kernel_side)
        != {
            "captures_with_notifier_lines",
            "captures_with_irq_thread",
            "captures_with_any_candidate_marker",
            "captures_with_all_stock_daemons",
        }
        or any(type(value) is not int or value < 0 for value in kernel_side.values())
    ):
        raise AuditError("capture manifest kernel-side census differs")
    captures = manifest.get("captures")
    if (
        not isinstance(captures, list)
        or len(captures) != manifest["distinct_captures"]
        or not captures
    ):
        raise AuditError("capture manifest population differs")
    seen_hashes: set[str] = set()
    for index, capture in enumerate(captures):
        if not isinstance(capture, dict) or set(capture) != CAPTURE_KEYS:
            raise AuditError(f"capture manifest entry keys differ: {index}")
        digest = capture.get("sha256")
        paths = capture.get("paths")
        tags = capture.get("muic_notifier_tags")
        if (
            not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or digest in seen_hashes
        ):
            raise AuditError(f"capture manifest digest differs: {index}")
        if (
            not isinstance(paths, list)
            or not paths
            or any(not isinstance(path, str) or not path for path in paths)
        ):
            raise AuditError(f"capture manifest paths differ: {index}")
        if type(capture.get("has_max7770x_irq_thread")) is not bool:
            raise AuditError(f"capture manifest IRQ boolean differs: {index}")
        if not isinstance(tags, dict) or any(
            not isinstance(key, str) or type(value) is not int or value < 0
            for key, value in tags.items()
        ):
            raise AuditError(f"capture manifest notifier tags differ: {index}")
        seen_hashes.add(digest)
    return manifest


def load_corpus(manifest: dict[str, Any]) -> dict[str, bytes]:
    expected = {capture["sha256"]: capture for capture in manifest["captures"]}
    corpus: dict[str, bytes] = {}
    observed_paths: dict[str, list[str]] = collections.defaultdict(list)
    matching_files = 0
    for path in sorted(PRIVATE.rglob("*")):
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size != 2_097_136:
                continue
        except OSError as exc:
            raise AuditError(f"capture population stat failed: {path}") from exc
        body = _stable_read(path, "P3.19 current corpus capture", 3 * 1024 * 1024)
        digest = hashlib.sha256(body).hexdigest()
        relative = str(path.relative_to(REPO))
        matching_files += 1
        observed_paths[digest].append(relative)
        corpus.setdefault(digest, body)
    if (
        matching_files != manifest["matching_files"]
        or set(corpus) != set(expected)
        or len(corpus) != manifest["distinct_captures"]
    ):
        raise AuditError("current capture population differs from manifest")
    for digest, capture in expected.items():
        if observed_paths[digest] != capture["paths"]:
            raise AuditError(f"capture duplicate-path inventory differs: {digest}")
    return corpus


@dataclass(frozen=True)
class FdtBlob:
    index: int
    offset: int
    totalsize: int
    data: bytes


@dataclass(frozen=True)
class FdtProp:
    path: str
    name: str
    value: bytes


def _align4(value: int) -> int:
    return (value + 3) & ~3


def _fdt_blobs(image: bytes) -> list[FdtBlob]:
    magic = struct.pack(">I", 0xD00DFEED)
    blobs: list[FdtBlob] = []
    cursor = 0
    while True:
        found = image.find(magic, cursor)
        if found < 0:
            break
        if found + 8 <= len(image):
            size = struct.unpack_from(">I", image, found + 4)[0]
            if 40 <= size <= len(image) - found:
                blobs.append(FdtBlob(len(blobs), found, size, image[found : found + size]))
        cursor = found + 4
    return blobs


def _fdt_cstring(data: bytes, offset: int) -> tuple[str, int]:
    end = data.find(b"\0", offset)
    if end < 0:
        raise AuditError("FDT string is unterminated")
    try:
        value = data[offset:end].decode("ascii")
    except UnicodeError as exc:
        raise AuditError("FDT string is not ASCII") from exc
    return value, _align4(end + 1)


def _fdt_props(blob: FdtBlob) -> list[FdtProp]:
    header = struct.unpack_from(">10I", blob.data, 0)
    magic, total, off_struct, off_strings = header[:4]
    size_strings, size_struct = header[8:10]
    if magic != 0xD00DFEED or total != blob.totalsize:
        raise AuditError("FDT header differs")
    struct_end = off_struct + size_struct
    strings_end = off_strings + size_strings
    if struct_end > len(blob.data) or strings_end > len(blob.data):
        raise AuditError("FDT section exceeds blob")
    result: list[FdtProp] = []
    stack: list[str] = []
    cursor = off_struct
    while cursor + 4 <= struct_end:
        token = struct.unpack_from(">I", blob.data, cursor)[0]
        cursor += 4
        if token == 1:
            name, cursor = _fdt_cstring(blob.data, cursor)
            if name:
                stack.append(name)
        elif token == 2:
            # The root BEGIN_NODE carries an empty name and therefore is not
            # represented in ``stack``.  Its matching END_NODE is valid.
            if stack:
                stack.pop()
        elif token == 3:
            if cursor + 8 > struct_end:
                raise AuditError("FDT property header is truncated")
            length, nameoff = struct.unpack_from(">II", blob.data, cursor)
            cursor += 8
            if off_strings + nameoff >= strings_end or cursor + length > struct_end:
                raise AuditError("FDT property exceeds section")
            name, _ = _fdt_cstring(blob.data, off_strings + nameoff)
            path = "/" + "/".join(stack) if stack else "/"
            result.append(FdtProp(path, name, blob.data[cursor : cursor + length]))
            cursor = _align4(cursor + length)
        elif token == 4:
            continue
        elif token == 9:
            break
        else:
            raise AuditError(f"unknown FDT token {token}")
    return result


def _one_prop(props: list[FdtProp], path: str, name: str) -> bytes:
    matches = [item.value for item in props if item.path == path and item.name == name]
    if len(matches) != 1:
        raise AuditError(f"FDT property cardinality differs: {path}/{name}={len(matches)}")
    return matches[0]


def _strings(value: bytes) -> tuple[str, ...]:
    try:
        return tuple(part.decode("ascii") for part in value.split(b"\0") if part)
    except UnicodeError as exc:
        raise AuditError("FDT string-list differs") from exc


def audit_dtbo(image: bytes, source: bytes) -> dict[str, Any]:
    blobs = _fdt_blobs(image)
    if len(blobs) != 11:
        raise AuditError(f"stock DTBO blob count differs: {len(blobs)}")
    selected: list[tuple[FdtBlob, list[FdtProp]]] = []
    for blob in blobs:
        props = _fdt_props(blob)
        model = _strings(_one_prop(props, "/", "model"))
        if model == ("Samsung G0Q PROJECT (board-id,12)",):
            selected.append((blob, props))
    if len(selected) != 1:
        raise AuditError(f"FYG8 board-id 12 overlay cardinality differs: {len(selected)}")
    blob, props = selected[0]
    if (blob.index, blob.offset, blob.totalsize) != (10, 0x6BDCE4, 708_337):
        raise AuditError("FYG8 board-id 12 blob geometry differs")
    if _one_prop(props, "/", "qcom,board-id") != bytes.fromhex("000100080000000c"):
        raise AuditError("FYG8 board-id cells differ")

    node = "/fragment@63/__overlay__/max77705@66"
    child = node + "/max77705_pdic"
    expected = {
        "status": b"okay\0",
        "compatible": b"maxim,max77705\0",
        "reg": struct.pack(">I", 0x66),
        "pinctrl-0": struct.pack(">I", 0x7B),
        "max77705,irq-gpio": struct.pack(">III", 0x11, 5, 1),
    }
    for name, value in expected.items():
        if _one_prop(props, node, name) != value:
            raise AuditError(f"MAX77705 DT property differs: {name}")
    if _one_prop(props, child, "status") != b"okay\0" or _one_prop(
        props, child, "compatible"
    ) != b"maxim,max77705_pdic\0":
        raise AuditError("MAX77705 PDIC child differs")
    target_fixups = _strings(_one_prop(props, "/__fixups__", "qupv3_se5_i2c"))
    if target_fixups != ("/fragment@41:target:0", "/fragment@63:target:0"):
        raise AuditError("MAX77705 I2C target fixup differs")

    def phandle_path(value: int) -> str:
        matches = [
            item.path
            for item in props
            if item.name in ("phandle", "linux,phandle")
            and item.value == struct.pack(">I", value)
        ]
        if len(matches) != 1:
            raise AuditError(f"FDT phandle cardinality differs: {value:#x}={matches}")
        return matches[0]

    controller_path = phandle_path(0x11)
    pinctrl_path = phandle_path(0x7B)
    if _one_prop(props, controller_path, "compatible") != b"qcom,pm8350c-gpio\0":
        raise AuditError("MAX77705 parent GPIO controller differs")
    pinctrl_expected = {
        "pins": b"gpio5\0",
        "function": b"normal\0",
        "input-enable": b"",
        "bias-disable": b"",
    }
    for name, value in pinctrl_expected.items():
        if _one_prop(props, pinctrl_path, name) != value:
            raise AuditError(f"MAX77705 parent pinctrl property differs: {name}")

    # The source counterpart names the local phandles which binary FDT keeps as
    # cells: PM8350C GPIO controller 0x11 and its gpio5 input state 0x7b.
    required_source = (
        b'model = "Samsung G0Q PROJECT (board-id,12)";',
        b'compatible = "qcom,pm8350c-gpio";',
        b'phandle = <0x11>;',
        b'if_pmic_irq {',
        b'pins = "gpio5";',
        b'phandle = <0x7b>;',
        b'max77705@66 {',
        b'compatible = "maxim,max77705";',
        b'reg = <0x66>;',
        b'pinctrl-0 = <0x7b>;',
        b'max77705,irq-gpio = <0x11 0x05 0x01>;',
        b'compatible = "maxim,max77705_pdic";',
        b'qupv3_se5_i2c = "/fragment@41:target:0\\0/fragment@63:target:0";',
    )
    missing = [token for token in required_source if token not in source]
    if missing:
        raise AuditError(f"MAX77705 DTS semantic seam differs: {missing!r}")
    return {
        "stock_dtbo_blob_count": len(blobs),
        "selected_blob": {
            "index": blob.index,
            "offset": blob.offset,
            "totalsize": blob.totalsize,
            **receipt(blob.data),
        },
        "model": "Samsung G0Q PROJECT (board-id,12)",
        "board_id_cells": [0x10008, 12],
        "i2c_controller_fixup": "qupv3_se5_i2c",
        "i2c_address": 0x66,
        "parent_gpio_controller": "qcom,pm8350c-gpio",
        "parent_gpio_controller_path": controller_path,
        "parent_gpio_phandle": 0x11,
        "parent_gpio_pin": 5,
        "parent_gpio_flags": 1,
        "parent_gpio_active_low": True,
        "pinctrl_state_phandle": 0x7B,
        "pinctrl_state_path": pinctrl_path,
        "pdic_child_enabled": True,
    }


@dataclass(frozen=True)
class Section:
    index: int
    name: str
    kind: int
    flags: int
    address: int
    offset: int
    size: int
    link: int
    info: int
    align: int
    entry_size: int


@dataclass(frozen=True)
class Symbol:
    index: int
    name: str
    section_index: int
    value: int
    size: int


@dataclass(frozen=True)
class Relocation:
    target_section: str
    offset: int
    kind: int
    symbol: str
    addend: int


class Elf64:
    def __init__(self, data: bytes, label: str):
        self.data = data
        self.label = label
        if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
            raise AuditError(f"{label} is not ELF64 little-endian")
        header = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
        if header[0] != 1 or header[1] != 183 or header[7] != 64:
            raise AuditError(f"{label} is not an AArch64 relocatable object")
        shoff, shentsize, shnum, shstrndx = header[5], header[10], header[11], header[12]
        if shentsize != 64 or not shnum or shstrndx >= shnum:
            raise AuditError(f"{label} section header contract differs")
        if shoff < 64 or shoff + shentsize * shnum > len(data):
            raise AuditError(f"{label} section headers exceed file")
        raw = [
            struct.unpack_from("<IIQQQQIIQQ", data, shoff + index * 64)
            for index in range(shnum)
        ]
        names_raw = raw[shstrndx]
        names = self._slice(names_raw[4], names_raw[5], "section names")
        self.sections = tuple(
            Section(index, self._cstring(names, row[0]), *row[1:])
            for index, row in enumerate(raw)
        )
        self.by_name = {item.name: item for item in self.sections}
        if len(self.by_name) != len(self.sections):
            raise AuditError(f"{label} section names are not unique")
        self.symbols = self._symbols()
        self.relocations = self._relocations()

    def _slice(self, offset: int, size: int, what: str) -> bytes:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise AuditError(f"{self.label} {what} exceeds file")
        return self.data[offset : offset + size]

    @staticmethod
    def _cstring(table: bytes, offset: int) -> str:
        if not 0 <= offset < len(table):
            raise AuditError("ELF string offset differs")
        end = table.find(b"\0", offset)
        if end < 0:
            raise AuditError("ELF string is unterminated")
        try:
            return table[offset:end].decode("ascii")
        except UnicodeError as exc:
            raise AuditError("ELF string is not ASCII") from exc

    def section(self, name: str) -> Section:
        try:
            return self.by_name[name]
        except KeyError as exc:
            raise AuditError(f"{self.label} lacks section {name}") from exc

    def section_bytes(self, name: str) -> bytes:
        item = self.section(name)
        return self._slice(item.offset, item.size, f"section {name}")

    def cstring(self, section: str, offset: int) -> str:
        return self._cstring(self.section_bytes(section), offset)

    def _symbols(self) -> tuple[Symbol, ...]:
        table = self.section(".symtab")
        if table.kind != 2 or table.entry_size != 24 or table.link >= len(self.sections):
            raise AuditError(f"{self.label} symbol table contract differs")
        strings_section = self.sections[table.link]
        strings = self._slice(strings_section.offset, strings_section.size, "symbol strings")
        body = self.section_bytes(".symtab")
        if len(body) % 24:
            raise AuditError(f"{self.label} symbol table is truncated")
        result = []
        for index, cursor in enumerate(range(0, len(body), 24)):
            nameoff, info, _other, section_index, value, size = struct.unpack_from(
                "<IBBHQQ", body, cursor
            )
            name = self._cstring(strings, nameoff)
            if not name and info & 0xF == 3 and section_index < len(self.sections):
                name = self.sections[section_index].name
            result.append(Symbol(index, name, section_index, value, size))
        return tuple(result)

    def symbol(self, name: str) -> Symbol:
        matches = [item for item in self.symbols if item.name == name]
        if len(matches) != 1:
            raise AuditError(f"{self.label} symbol cardinality differs: {name}={len(matches)}")
        item = matches[0]
        if item.section_index == 0 or item.section_index >= len(self.sections):
            raise AuditError(f"{self.label} symbol is undefined: {name}")
        return item

    def symbol_bytes(self, name: str) -> bytes:
        item = self.symbol(name)
        section = self.sections[item.section_index]
        relative = item.value - section.address
        if relative < 0 or relative + item.size > section.size or not item.size:
            raise AuditError(f"{self.label} symbol bounds differ: {name}")
        return self._slice(section.offset + relative, item.size, f"symbol {name}")

    def _relocations(self) -> tuple[Relocation, ...]:
        result = []
        for section in self.sections:
            if section.kind != 4:
                continue
            if section.entry_size != 24 or section.info >= len(self.sections):
                raise AuditError(f"{self.label} relocation section differs: {section.name}")
            body = self._slice(section.offset, section.size, f"relocations {section.name}")
            if len(body) % 24:
                raise AuditError(f"{self.label} relocations are truncated")
            target = self.sections[section.info].name
            for cursor in range(0, len(body), 24):
                offset, info, addend = struct.unpack_from("<QQq", body, cursor)
                symbol_index = info >> 32
                if symbol_index >= len(self.symbols):
                    raise AuditError(f"{self.label} relocation symbol differs")
                result.append(
                    Relocation(
                        target,
                        offset,
                        info & 0xFFFFFFFF,
                        self.symbols[symbol_index].name,
                        addend,
                    )
                )
        return tuple(result)

    def relocation(self, target: str, offset: int) -> Relocation:
        matches = [
            item
            for item in self.relocations
            if item.target_section == target and item.offset == offset
        ]
        if len(matches) != 1:
            raise AuditError(
                f"{self.label} relocation cardinality differs: {target}+{offset:#x}={len(matches)}"
            )
        return matches[0]

    def word(self, address: int) -> int:
        text = self.section(".text")
        relative = address - text.address
        if relative < 0 or relative + 4 > text.size or relative % 4:
            raise AuditError(f"{self.label} text address differs: {address:#x}")
        return struct.unpack_from("<I", self.data, text.offset + relative)[0]


def _require_word(elf: Elf64, address: int, expected: int, label: str) -> None:
    actual = elf.word(address)
    if actual != expected:
        raise AuditError(f"{label} instruction differs at {address:#x}: {actual:#x}")


def _require_relocation(
    elf: Elf64,
    target: str,
    offset: int,
    kind: int,
    symbol: str,
    addend: int,
    label: str,
) -> None:
    expected = Relocation(target, offset, kind, symbol, addend)
    actual = elf.relocation(target, offset)
    if actual != expected:
        raise AuditError(f"{label} relocation differs: {actual}")


def _require_symbol(
    elf: Elf64, name: str, address: int, size: int, digest: str
) -> dict[str, Any]:
    item = elf.symbol(name)
    body = elf.symbol_bytes(name)
    if (item.value, item.size) != (address, size) or receipt(body) != {
        "size": size,
        "sha256": digest,
    }:
        raise AuditError(f"binary symbol identity differs: {name}")
    return {"address": address, **receipt(body)}


def audit_mfd_binary(data: bytes) -> dict[str, Any]:
    elf = Elf64(data, "mfd_max77705.ko")
    symbols = {
        "max77705_i2c_probe": _require_symbol(
            elf,
            "max77705_i2c_probe",
            0x2058,
            1_568,
            "fd684ee76f6489735ebfd65ace8384a3ce20d913a1496ab599f8ba1a7d579a6c",
        ),
        "max77705_irq_init": _require_symbol(
            elf,
            "max77705_irq_init",
            0x2988,
            876,
            "9194bb4104a0eb83ba3f618bdfa037da7aff348afd407c9391c61fe69af92bc3",
        ),
        "max77705_irq_thread": _require_symbol(
            elf,
            "max77705_irq_thread",
            0x2CF4,
            1_672,
            "97bf7eeeaea53746d160a42e00787ec6e045d49bc1fab44d636d8fe88946afe6",
        ),
        "max77705_devs": _require_symbol(
            elf,
            "max77705_devs",
            0x110,
            432,
            "1fe2373734955e60c172999142934b52e69ba7ab9039b3c18ea54082ba32afcd",
        ),
    }
    modinfo = elf.section_bytes(".modinfo")
    for token in (
        b"alias=of:N*T*Cmaxim,max77705\0",
        b"name=mfd_max77705\0",
    ):
        if modinfo.count(token) != 1:
            raise AuditError(f"MFD modinfo differs: {token!r}")
    _require_relocation(elf, ".data", 0x110, 257, ".rodata", 0xE6E, "USBC MFD cell")
    if elf.cstring(".rodata", 0xE6E) != "max77705-usbc":
        raise AuditError("MFD USBC child name differs")
    for address, word, label in (
        (0x2140, 0x52800542, "42 nested descriptor count"),
        (0x2610, 0x52800063, "three MFD child count"),
        (0x2BBC, 0x7100AB1F, "42 nested setup bound"),
        (0x2C04, 0x52840103, "parent low oneshot flags"),
        (0x32A0, 0xF100AA9F, "42 nested dispatch bound"),
        (0x32BC, 0xB9406A68, "nested base load"),
        (0x32C0, 0x0B080280, "nested base plus index"),
    ):
        _require_word(elf, address, word, label)
    for offset, symbol, addend, label in (
        (0x2154, "__irq_alloc_descs", 0, "nested descriptor allocation"),
        (0x219C, "of_get_named_gpio_flags", 0, "DT GPIO consumer"),
        (0x25F8, "max77705_irq_init", 0, "IRQ init call"),
        (0x2620, "mfd_add_devices", 0, "MFD child publication"),
        (0x2A28, "gpio_to_desc", 0, "GPIO descriptor lookup"),
        (0x2A2C, "gpiod_to_irq", 0, "parent Linux IRQ lookup"),
        (0x2C10, "request_threaded_irq", 0, "parent IRQ registration"),
        (0x32C4, "handle_nested_irq", 0, "nested IRQ dispatch"),
    ):
        _require_relocation(elf, ".text", offset, 283, symbol, addend, label)
    if elf.cstring(".rodata", 0x50B) != "max77705-irq":
        raise AuditError("MAX77705 parent IRQ action name differs")
    return {
        "build_id": "1d5c6c64132316f45a4be929a5e288829006182a",
        "symbols": symbols,
        "of_alias": "maxim,max77705",
        "mfd_usbc_child": "max77705-usbc",
        "mfd_child_count": 3,
        "nested_irq_count": 42,
        "parent_irq_action_name": "max77705-irq",
        "parent_irq_flags": ["IRQF_TRIGGER_LOW", "IRQF_ONESHOT"],
        "dispatch": "handle_nested_irq(irq_base + i)",
    }


def audit_pdic_binary(data: bytes) -> dict[str, Any]:
    elf = Elf64(data, "pdic_max77705.ko")
    symbols = {
        "max77705_usbc_probe": _require_symbol(
            elf,
            "max77705_usbc_probe",
            0xCF0C,
            2_676,
            "f13b266d1fc5225417003df568775ff0c1b2612128dfe93ebc083e53b91c26d6",
        ),
        "max77705_muic_probe": _require_symbol(
            elf,
            "max77705_muic_probe",
            0x16264,
            3_076,
            "06c944761850866f80ecf5f9d4732b84f0566a87bc53de3880c4dbd098ebc525",
        ),
        "max77705_muic_irq": _require_symbol(
            elf,
            "max77705_muic_irq",
            0x16E68,
            220,
            "1df88f707ff267748ae23ad8c0e203f03f3b77d57d4866376e947a36d6d80050",
        ),
    }
    modinfo = elf.section_bytes(".modinfo")
    if modinfo.count(b"name=pdic_max77705\0") != 1:
        raise AuditError("PDIC module name differs")
    depends = [item for item in modinfo.split(b"\0") if item.startswith(b"depends=")]
    if len(depends) != 1 or b"mfd_max77705" not in depends[0]:
        raise AuditError("PDIC MFD dependency differs")
    _require_relocation(
        elf, ".data", 0x30, 257, ".rodata", 0x963D, "PDIC platform driver name"
    )
    if elf.cstring(".rodata", 0x963D) != "max77705-usbc":
        raise AuditError("PDIC platform match name differs")
    for offset, symbol, addend, label in (
        (0xD4E8, "max77705_init_irq_handler", 0, "USBC nested IRQ registration"),
        (0xD4F0, "max77705_muic_probe", 0, "MUIC probe call"),
        (0xD890, "max77705_read_reg", 0, "parent mask read"),
        (0xD8AC, "max77705_write_reg", 0, "parent mask write"),
        (0x167C4, "request_threaded_irq", 0, "UIDADC nested registration"),
        (0x1680C, "request_threaded_irq", 0, "CHGT nested registration"),
        (0x16858, "request_threaded_irq", 0, "DCD nested registration"),
        (0x168A0, "request_threaded_irq", 0, "VBADC nested registration"),
        (0x168E8, "request_threaded_irq", 0, "VBUS nested registration"),
        (0x16F04, ".text", 0x177C4, "MUIC detect dispatch"),
    ):
        _require_relocation(elf, ".text", offset, 283, symbol, addend, label)
    for address, word, label in (
        (0xD878, 0x52800028, "cc_booting_complete value"),
        (0xD87C, 0x39054B28, "cc_booting_complete store"),
        (0xD8A4, 0x121C7902, "USBC parent-mask bit clear"),
        (0x167A8, 0x11006EC0, "UIDADC offset 27"),
        (0x167F0, 0x11006AC0, "CHGT offset 26"),
        (0x1683C, 0x110062C0, "DCD offset 24"),
        (0x16884, 0x11005EC0, "VBADC offset 23"),
        (0x168CC, 0x11005AC0, "VBUS offset 22"),
    ):
        _require_word(elf, address, word, label)
    names = {
        "uidadc": elf.cstring(".rodata", 0x2D9C),
        "chgtyp": elf.cstring(".rodata", 0x6443),
        "dcdtmo": elf.cstring(".rodata", 0x9925),
        "vbadc": elf.cstring(".rodata", 0x8DA1),
        "vbusdet": elf.cstring(".rodata", 0x537F),
    }
    if names != {
        "uidadc": "muic-uiadc",
        "chgtyp": "muic-chgtyp",
        "dcdtmo": "muic-dcdtmo",
        "vbadc": "muic-vbadc",
        "vbusdet": "muic-vbusdet",
    }:
        raise AuditError(f"MUIC nested IRQ names differ: {names}")
    return {
        "build_id": "a59ccb842e0d521ec636b01ed54a65b6c0121d07",
        "symbols": symbols,
        "platform_driver_name": "max77705-usbc",
        "mfd_dependency": True,
        "nested_irqs": {
            "vbusdet": 22,
            "vbadc": 23,
            "dcdtmo": 24,
            "chgtyp": 26,
            "uidadc": 27,
        },
        "nested_irq_names": names,
        "probe_terminal_gate": {
            "cc_booting_complete": 1,
            "parent_intsrc_mask_bit_cleared": 3,
        },
    }


def _ordered(body: bytes, *tokens: bytes) -> None:
    cursor = -1
    for token in tokens:
        found = body.find(token, cursor + 1)
        if found < 0:
            raise AuditError(f"source order seam differs: {token!r}")
        cursor = found


def audit_sources(inputs: dict[str, bytes]) -> dict[str, Any]:
    mfd = inputs["max77705_mfd_source"]
    irq = inputs["max77705_irq_source"]
    muic = inputs["max77705_muic_source"]
    usbc = inputs["max77705_usbc_source"]
    private = inputs["max77705_private_header"]
    public = inputs["max77705_mfd_header"]
    manage = inputs["irq_manage_source"]
    sched = inputs["sched_header"]

    required = {
        "mfd": (
            b'{ .name = "max77705-usbc", },',
            b'pdata->irq_gpio = of_get_named_gpio(np_max77705, "max77705,irq-gpio", 0);',
            b'pdata->irq_base = irq_alloc_descs(-1, 0, MAX77705_IRQ_NR, -1);',
            b'ret = max77705_irq_init(max77705);',
            b'ret = mfd_add_devices(max77705->dev, -1, max77705_devs,',
            b'{ .compatible = "maxim,max77705" },',
        ),
        "irq": (
            b'[MAX77705_USBC_IRQ_VBUS_INT] = { .group = USBC_INT, .mask = 1 << 5 },',
            b'[MAX77705_USBC_IRQ_CHGT_INT] = { .group = USBC_INT, .mask = 1 << 1 },',
            b'[MAX77705_USBC_IRQ_UIDADC_INT] = { .group = USBC_INT, .mask = 1 << 0 },',
            b'max77705->irq = gpio_to_irq(max77705->irq_gpio);',
            b'irq_set_nested_thread(cur_irq, 1);',
            b'"max77705-irq", max77705);',
            b'if ((irq_src & MAX77705_IRQSRC_USBC) && max77705->cc_booting_complete)',
            b'handle_nested_irq(max77705->irq_base + i);',
        ),
        "muic": (
            b'muic_data->irq_uiadc = irq_base + MAX77705_USBC_IRQ_UIDADC_INT;',
            b'muic_data->irq_chgtyp = irq_base + MAX77705_USBC_IRQ_CHGT_INT;',
            b'muic_data->irq_dcdtmo = irq_base + MAX77705_USBC_IRQ_DCD_INT;',
            b'muic_data->irq_vbadc = irq_base + MAX77705_USBC_IRQ_VBADC_INT;',
            b'muic_data->irq_vbusdet = irq_base + MAX77705_USBC_IRQ_VBUS_INT;',
            b'if (muic_data->is_muic_ready == true)\n\t\tmax77705_muic_detect_dev(muic_data, irq);',
            b'muic_data->is_muic_ready = true;',
            b'max77705_muic_detect_dev(muic_data, MUIC_IRQ_INIT_DETECT);',
        ),
        "usbc": (
            b'.name = "max77705-usbc",',
            b'max77705_init_irq_handler(usbc_data);',
            b'max77705_muic_probe(usbc_data);',
            b'max77705->cc_booting_complete = 1;',
            b'max77705_usbc_umask_irq(usbc_data);',
            b'i2c_data &= ~((1 << 3));',
            b'print_hex_dump(KERN_INFO, "max77705: opcode_write: ",',
            b'ret = max77705_bulk_write(usbc_data->muic, OPCODE_WRITE,',
            b'ret = max77705_i2c_opcode_write(usbc_data, cmd_data.opcode,',
            b'msg_maxim("i2c write fail. dequeue opcode");',
        ),
        "private": (
            b'MAX77705_USBC_IRQ_VBUS_INT,',
            b'MAX77705_USBC_IRQ_CHGT_INT,',
            b'MAX77705_USBC_IRQ_UIDADC_INT,',
            b'MAX77705_IRQ_NR,',
        ),
        "public": (b'int irq_base;', b'int irq_gpio;'),
        "manage": (b'kthread_create(irq_thread, new, "irq/%d-%s", irq,',),
        "sched": (b'#define TASK_COMM_LEN\t\t\t16',),
    }
    bodies = {
        "mfd": mfd,
        "irq": irq,
        "muic": muic,
        "usbc": usbc,
        "private": private,
        "public": public,
        "manage": manage,
        "sched": sched,
    }
    for name, tokens in required.items():
        missing = [token for token in tokens if token not in bodies[name]]
        if missing:
            raise AuditError(f"source semantic seam differs: {name} {missing!r}")
    _ordered(
        mfd,
        b'pdata->irq_base = irq_alloc_descs(-1, 0, MAX77705_IRQ_NR, -1);',
        b'ret = max77705_irq_init(max77705);',
        b'ret = mfd_add_devices(max77705->dev, -1, max77705_devs,',
    )
    _ordered(
        usbc,
        b'max77705_init_irq_handler(usbc_data);',
        b'max77705_muic_probe(usbc_data);',
        b'max77705->cc_booting_complete = 1;',
        b'max77705_usbc_umask_irq(usbc_data);',
    )
    _ordered(
        usbc,
        b'print_hex_dump(KERN_INFO, "max77705: opcode_write: ",',
        b'ret = max77705_bulk_write(usbc_data->muic, OPCODE_WRITE,',
        b'ret = max77705_i2c_opcode_write(usbc_data, cmd_data.opcode,',
        b'if (ret < 0) {',
        b'msg_maxim("i2c write fail. dequeue opcode");',
    )
    _ordered(
        muic,
        b'muic_data->irq_uiadc = irq_base + MAX77705_USBC_IRQ_UIDADC_INT;',
        b'muic_data->irq_chgtyp = irq_base + MAX77705_USBC_IRQ_CHGT_INT;',
        b'muic_data->irq_dcdtmo = irq_base + MAX77705_USBC_IRQ_DCD_INT;',
        b'muic_data->irq_vbadc = irq_base + MAX77705_USBC_IRQ_VBADC_INT;',
        b'muic_data->irq_vbusdet = irq_base + MAX77705_USBC_IRQ_VBUS_INT;',
    )
    return {name: receipt(body) for name, body in sorted(bodies.items())}


PARENT_RE = re.compile(
    rb"max77705_irq_thread: irq\[(\d+)\] (\d+)/(\d+)/(\d+) "
    rb"irq_src=0x([0-9a-fA-F]+) pmic_rev=0x([0-9a-fA-F]+)"
)
NESTED_RE = re.compile(rb"max77705_muic_irq irq:(\d+) \(([^)]+)\)")
THREAD_RE = re.compile(rb"irq/(\d+)-max7770(?![A-Za-z0-9_])")
NOTIFIER_RE = re.compile(rb"\[MUIC\] (muic_notifier_[a-z_]+)")
ATTACH_RE = re.compile(rb"muic_notifier_attach_attached_dev: \((\d+)\)")
DETACH_RE = re.compile(rb"muic_notifier_detach_attached_dev: \((\d+)\)")
VPS_RE = re.compile(rb"vps table match found at i\((\d+)\), ([^\r\n]+)")
AP_RE = re.compile(rb"pdic_max77705: com_to_usb_ap")
DUMP_0609_RE = re.compile(rb"opcode_write: 00000000: 06 09")

NESTED_OFFSETS = {
    b"muic-vbusdet": 22,
    b"muic-vbadc": 23,
    b"muic-chgtyp": 26,
}


def derive_thread_comm(parent_irq: int) -> str:
    if not 0 <= parent_irq <= 999_999:
        raise AuditError("parent IRQ value is out of derivation range")
    return f"irq/{parent_irq}-max77705-irq"[:15]


def audit_nested_offsets(data: bytes) -> dict[str, Any]:
    parents = PARENT_RE.findall(data)
    nested = NESTED_RE.findall(data)
    if not parents or not nested:
        raise AuditError("nested-offset evidence is incomplete")
    bases = {int(item[2]) for item in parents}
    if len(bases) != 1:
        raise AuditError(f"nested-offset capture has multiple bases: {bases}")
    base = next(iter(bases))
    counts: collections.Counter[tuple[int, str]] = collections.Counter()
    absolute: dict[str, set[int]] = {
        name.removeprefix(b"muic-").decode(): set() for name in NESTED_OFFSETS
    }
    for raw_irq, raw_name in nested:
        if raw_name not in NESTED_OFFSETS:
            raise AuditError(f"unexpected nested MUIC IRQ name: {raw_name!r}")
        irq = int(raw_irq)
        if irq - base != NESTED_OFFSETS[raw_name]:
            raise AuditError(
                f"nested IRQ offset differs: {raw_name!r} {irq}-{base}"
            )
        name = raw_name.removeprefix(b"muic-").decode()
        counts[(irq, name)] += 1
        absolute[name].add(irq)
    if any(len(values) != 1 for values in absolute.values()):
        raise AuditError(f"nested IRQ absolute inventory differs: {absolute}")
    return {
        "nested_irq_base": base,
        "nested_irq_base_source": "direct parent max77705_irq_thread log field",
        "absolute_irqs": {
            name: next(iter(values)) for name, values in sorted(absolute.items())
        },
        "derived_offsets": {
            name.removeprefix(b"muic-").decode(): offset
            for name, offset in NESTED_OFFSETS.items()
        },
        "base_free_pairwise_differences": {
            "vbadc_minus_vbusdet": next(iter(absolute["vbadc"]))
            - next(iter(absolute["vbusdet"])),
            "chgtyp_minus_vbusdet": next(iter(absolute["chgtyp"]))
            - next(iter(absolute["vbusdet"])),
        },
        "counts": {
            f"{name}@{irq}": count
            for (irq, name), count in sorted(counts.items())
        },
    }


def _line_at(data: bytes, offset: int) -> bytes:
    start = data.rfind(b"\n", 0, offset) + 1
    end = data.find(b"\n", offset)
    return data[start : len(data) if end < 0 else end]


def audit_stock_corpus(
    manifest: dict[str, Any],
    corpus: dict[str, bytes],
    *,
    enforce_identity: bool = True,
) -> dict[str, Any]:
    captures = manifest["captures"]
    expected_hashes = {capture["sha256"] for capture in captures}
    if set(corpus) != expected_hashes:
        raise AuditError("loaded corpus identity set differs")

    parent_numbers: set[int] = set()
    thread_capture_count = 0
    parent_367_capture_count = 0
    notifier_hashes: list[str] = []
    nested_evidence: dict[str, dict[str, Any]] = {}
    notifier_summaries: dict[str, dict[str, Any]] = {}
    dump_before_attach = 0
    attach_before_dump = 0
    irq_context_ap = 0
    non_irq_context_ap = 0
    attach_values: collections.Counter[int] = collections.Counter()
    detach_values: collections.Counter[int] = collections.Counter()
    vps_matches: collections.Counter[str] = collections.Counter()
    total_ap = 0
    total_dump = 0
    total_attach = 0
    total_i2c_failures = 0

    for capture in captures:
        digest = capture["sha256"]
        data = corpus[digest]
        if enforce_identity and receipt(data) != {
            "size": 2_097_136,
            "sha256": digest,
        }:
            raise AuditError(f"corpus capture identity differs: {digest}")
        actual_tags = collections.Counter(
            match.group(1).decode() for match in NOTIFIER_RE.finditer(data)
        )
        if dict(sorted(actual_tags.items())) != capture["muic_notifier_tags"]:
            raise AuditError(f"manifest notifier classification differs: {digest}")

        thread_matches = list(THREAD_RE.finditer(data))
        has_thread = bool(thread_matches)
        if has_thread is not capture["has_max7770x_irq_thread"]:
            raise AuditError(f"manifest IRQ-thread classification differs: {digest}")
        capture_parent_numbers = {int(match.group(1)) for match in thread_matches}
        for match in thread_matches:
            irq = int(match.group(1))
            if match.group(0).decode() != derive_thread_comm(irq):
                raise AuditError(f"parent IRQ thread-name derivation differs: {digest}")
        if has_thread:
            thread_capture_count += 1
            parent_numbers.update(capture_parent_numbers)
            if 367 in capture_parent_numbers:
                parent_367_capture_count += 1

        parents = PARENT_RE.findall(data)
        for irq_arg, linux_irq, _base, gpio, _source, pmic_revision in parents:
            if irq_arg != linux_irq or gpio != b"282" or pmic_revision != b"05":
                raise AuditError(f"parent IRQ semantic tuple differs: {digest}")

        nested = NESTED_RE.findall(data)
        if nested:
            nested_evidence[digest] = audit_nested_offsets(data)

        if actual_tags:
            notifier_hashes.append(digest)
            ap = list(AP_RE.finditer(data))
            dumps = list(DUMP_0609_RE.finditer(data))
            attaches = list(ATTACH_RE.finditer(data))
            failures = data.count(b"i2c write fail. dequeue opcode")
            if not ap or len(ap) != len(dumps) or len(ap) != len(attaches):
                raise AuditError(f"AP/dump/attach multiplicity differs: {digest}")
            before = 0
            after = 0
            irq_events = 0
            non_irq_events = 0
            for index, ap_match in enumerate(ap):
                end = ap[index + 1].start() if index + 1 < len(ap) else len(data)
                segment_dumps = [item for item in dumps if ap_match.end() <= item.start() < end]
                segment_attaches = [
                    item for item in attaches if ap_match.end() <= item.start() < end
                ]
                if len(segment_dumps) != 1 or len(segment_attaches) != 1:
                    raise AuditError(f"AP event association differs: {digest}:{index}")
                if segment_dumps[0].start() < segment_attaches[0].start():
                    before += 1
                else:
                    after += 1
                if b"irq/" in _line_at(data, ap_match.start()):
                    irq_events += 1
                else:
                    non_irq_events += 1
            dump_before_attach += before
            attach_before_dump += after
            irq_context_ap += irq_events
            non_irq_context_ap += non_irq_events
            total_ap += len(ap)
            total_dump += len(dumps)
            total_attach += len(attaches)
            total_i2c_failures += failures
            attach_values.update(int(item.group(1)) for item in attaches)
            detach_values.update(int(item.group(1)) for item in DETACH_RE.finditer(data))
            vps_matches.update(
                f"i({item.group(1).decode()}) {item.group(2).decode()}"
                for item in VPS_RE.finditer(data)
            )
            notifier_summaries[digest] = {
                "com_to_usb_ap": len(ap),
                "opcode_0609": len(dumps),
                "notifier_attach": len(attaches),
                "dump_before_attach": before,
                "attach_before_dump": after,
                "irq_context_ap": irq_events,
                "non_irq_context_ap": non_irq_events,
                "i2c_write_failure_logs": failures,
            }

    if (
        thread_capture_count != manifest["kernel_side"]["captures_with_irq_thread"]
        or len(parent_numbers) < 2
    ):
        raise AuditError("dynamic parent IRQ census differs")
    if not nested_evidence:
        raise AuditError("corpus lacks nested-offset evidence")
    for digest, actual in nested_evidence.items():
        if actual["base_free_pairwise_differences"] != {
            "vbadc_minus_vbusdet": 1,
            "chgtyp_minus_vbusdet": 4,
        }:
            raise AuditError(f"base-free nested IRQ differences differ: {digest}")

    if (
        len(notifier_hashes)
        != manifest["kernel_side"]["captures_with_notifier_lines"]
        or not notifier_hashes
        or total_ap == 0
        or total_ap != total_dump
        or total_ap != total_attach
        or dump_before_attach + attach_before_dump != total_ap
        or irq_context_ap + non_irq_context_ap != total_ap
        or total_i2c_failures != 0
    ):
        raise AuditError("stock AP/notifier corpus invariant differs")

    return {
        "corpus": {
            "distinct_captures": len(corpus),
            "identity_set_sha256": hashlib.sha256(
                ("\n".join(sorted(corpus)) + "\n").encode()
            ).hexdigest(),
            "notifier_capture_count": len(notifier_hashes),
            "notifier_capture_sha256": sorted(notifier_hashes),
        },
        "parent_irq": {
            "dynamic_linux_irq_numbers": sorted(parent_numbers),
            "distinct_number_count": len(parent_numbers),
            "captures_with_thread": thread_capture_count,
            "captures_with_parent_367": parent_367_capture_count,
            "absolute_number_is_stock_invariant": False,
            "thread_name_example": {
                "full": "irq/367-max77705-irq",
                "task_comm": derive_thread_comm(367),
            },
            "linux_gpio_values_in_parent_records": [282],
        },
        "nested_irq": {
            "captures_with_absolute_nested_numbers": len(nested_evidence),
            "bases_observed": sorted(
                item["nested_irq_base"] for item in nested_evidence.values()
            ),
            "derived_offsets": {
                name.removeprefix(b"muic-").decode(): offset
                for name, offset in NESTED_OFFSETS.items()
            },
            "absolute_numbers_are_stock_invariants": False,
            "evidence": dict(sorted(nested_evidence.items())),
        },
        "ap_path": {
            "notifier_captures": len(notifier_hashes),
            "com_to_usb_ap": total_ap,
            "opcode_0609": total_dump,
            "notifier_attach_all_values": total_attach,
            "dump_before_attach": dump_before_attach,
            "attach_before_dump": attach_before_dump,
            "irq_context_ap": irq_context_ap,
            "non_irq_context_ap": non_irq_context_ap,
            "captures_with_any_chgtyp_irq": len(nested_evidence),
            "captures_without_chgtyp_irq": len(notifier_hashes) - len(nested_evidence),
            "attach_values": {str(key): value for key, value in sorted(attach_values.items())},
            "detach_values": {str(key): value for key, value in sorted(detach_values.items())},
            "vps_match_counts": dict(sorted(vps_matches.items())),
            "i2c_write_failure_logs": total_i2c_failures,
            "opcode_0609_dump_precedes_bulk_write_in_source": True,
            "bulk_write_negative_return_would_log_failure": True,
            "per_capture": dict(sorted(notifier_summaries.items())),
        },
    }


def build_result(
    inputs: dict[str, bytes],
    manifest: dict[str, Any],
    corpus: dict[str, bytes],
    *,
    enforce_identity: bool = True,
) -> dict[str, Any]:
    if set(inputs) != set(INPUTS):
        raise AuditError("P3.19 input key set differs")
    if manifest != parse_corpus_manifest(inputs["abl_capture_manifest"]):
        raise AuditError("P3.19 parsed corpus manifest differs")
    identities = {}
    for name, data in sorted(inputs.items()):
        identities[name] = receipt(data)
        spec = INPUTS[name]
        if enforce_identity and identities[name] != {
            "size": spec.size,
            "sha256": spec.sha256,
        }:
            raise AuditError(f"P3.19 input identity differs: {name}")
    dt = audit_dtbo(inputs["stock_dtbo"], inputs["active_r12_dts"])
    sources = audit_sources(inputs)
    mfd = audit_mfd_binary(inputs["mfd_max77705_module"])
    pdic = audit_pdic_binary(inputs["pdic_max77705_module"])
    observed = audit_stock_corpus(manifest, corpus, enforce_identity=enforce_identity)
    if observed["nested_irq"]["derived_offsets"] != {
        name: pdic["nested_irqs"][name] for name in ("vbusdet", "vbadc", "chgtyp")
    }:
        raise AuditError("static/observed nested IRQ offsets differ")
    implementation = receipt(Path(__file__).read_bytes())
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": {
            "model": "SM-S906N",
            "codename": "g0q",
            "build": "S906NKSS7FYG8",
        },
        "scope": {
            "tier": "H0",
            "host_only": True,
            "device_contact": False,
            "device_writes": False,
            "d0_authorized": False,
            "d1_authorized": False,
            "f1_authorized": False,
            "live_authorized": False,
        },
        "inputs": identities,
        "dtbo": dt,
        "source_semantics": sources,
        "binary_semantics": {
            "mfd_max77705": mfd,
            "pdic_max77705": pdic,
        },
        "stock_observation": observed,
        "conclusion": {
            "stock_dt_max77705_node_enabled": True,
            "stock_dt_targets_qupv3_se5_i2c_at_0x66": True,
            "stock_parent_gpio_is_pm8350c_gpio5_active_low": True,
            "mfd_publishes_max77705_usbc_child": True,
            "pdic_platform_driver_matches_mfd_child": True,
            "pdic_probe_registers_five_muic_nested_irqs": True,
            "pdic_probe_completion_unmasks_parent_usbc_source": True,
            "observed_parent_irq_gpio_matches_static_route": True,
            "observed_nested_irq_offsets_match_static_dispatch": True,
            "absolute_parent_and_nested_irq_numbers_are_dynamic": (
                observed["parent_irq"]["distinct_number_count"] > 1
            ),
            "observed_stock_ap_paths_attempt_i2c_06_09_without_negative_return": True,
            "interrupt_is_one_ap_route_not_the_only_route": (
                observed["ap_path"]["irq_context_ap"] > 0
                and observed["ap_path"]["non_irq_context_ap"] > 0
            ),
            "notifier_captures": observed["ap_path"]["notifier_captures"],
            "ap_path_events": observed["ap_path"]["com_to_usb_ap"],
            "dump_before_attach_events": observed["ap_path"]["dump_before_attach"],
            "attach_before_dump_events": observed["ap_path"]["attach_before_dump"],
            "stock_irq_dt_or_shipped_demux_defect_explains_candidate_silence": False,
            "candidate_reached_pdic_probe_completion_and_unmask": False,
            "candidate_reached_pdic_probe_completion_and_unmask_proven": False,
            "remaining_boundary": (
                "candidate-side i2c-msm-geni/mfd_max77705/pdic_max77705 load, "
                "platform bind, cc_booting_complete publication, and parent USBC unmask"
            ),
        },
        "implementation": implementation,
    }


def encode(result: dict[str, Any]) -> bytes:
    return (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    inputs = load_inputs(materialize=not args.audit_only)
    manifest = parse_corpus_manifest(inputs["abl_capture_manifest"])
    corpus = load_corpus(manifest)
    data = encode(build_result(inputs, manifest, corpus))
    if args.audit_only:
        sys.stdout.buffer.write(data)
        return 0
    _write_exclusive(OUTPUT, data)
    sys.stdout.write(f"{VERDICT} {len(data)} {hashlib.sha256(data).hexdigest()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
