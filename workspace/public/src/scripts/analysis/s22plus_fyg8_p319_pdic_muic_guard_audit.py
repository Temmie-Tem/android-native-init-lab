#!/usr/bin/env python3
"""Direct-ELF audit of the FYG8 MAX77705 MUIC attach guards.

This is a host-only P3.19 analysis.  It snapshots exact private module/source
inputs, reads AArch64 ELF bytes directly, and proves the control flow from a
CDP attach through ``max77705_muic_attach_usb_path`` to the CONTROL1 write.
It never contacts a device and grants no D0/D1/F1 or live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[5]
PRIVATE = REPO / "workspace/private"
OUTPUT_ROOT = PRIVATE / "outputs/s22plus_fyg8_p319/pdic-muic-guard-audit-20260820-02"
OUTPUT = OUTPUT_ROOT / "result.json"
SNAPSHOT_ROOT = OUTPUT_ROOT / "inputs"
PREDECESSOR_OUTPUT = (
    PRIVATE
    / "outputs/s22plus_fyg8_p319/"
    "pdic-muic-guard-audit-20260820-01/result.json"
)

SCHEMA = "s22plus-fyg8-p319-pdic-muic-guard-audit-v1"
VERDICT = "PASS_P319_PDIC_MUIC_ATTACH_GUARDS_H0"


class AuditError(RuntimeError):
    pass


@dataclass(frozen=True)
class InputSpec:
    size: int
    sha256: str
    source: Path
    snapshot_name: str


KERNEL = (
    PRIVATE
    / "work/s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform/msm-kernel"
)
INPUTS: dict[str, InputSpec] = {
    "pdic_max77705_module": InputSpec(
        423_456,
        "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db",
        Path("/mnt/android-lab-logical/vendor_dlkm/lib/modules/pdic_max77705.ko"),
        "pdic_max77705.ko",
    ),
    "common_muic_module": InputSpec(
        62_344,
        "f373e8ddbba77d4b80027ed9485bc0b38b5f9961227d32f5baa0cfbdaa2f2c16",
        Path("/mnt/android-lab-logical/vendor_dlkm/lib/modules/common_muic.ko"),
        "common_muic.ko",
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
    "muic_core_source": InputSpec(
        16_794,
        "962d841eb2e8097eefc79a0769b844c168f4d21c37f7fc3d0365ae72b224eec1",
        KERNEL / "drivers/muic/common/muic-core.c",
        "muic-core.c",
    ),
    "muic_param_source": InputSpec(
        4_713,
        "c03677edf35e5d51e980fc4b1feabb57555c4b03c155241155af6b84bb211159",
        KERNEL / "drivers/muic/common/muic_param.c",
        "muic_param.c",
    ),
    "muic_header": InputSpec(
        18_609,
        "421c69aea93560473d01b412448ca50395c096346709375720fe7c839b44fd57",
        KERNEL / "include/linux/muic/common/muic.h",
        "muic.h",
    ),
    "max77705_muic_header": InputSpec(
        13_948,
        "3f7f2b9790940d61ec6bb636f87fd750f7971f1c609c06e6380d11907f701cb1",
        KERNEL / "include/linux/usb/typec/maxim/max77705-muic.h",
        "max77705-muic.h",
    ),
    "max77705_usbc_header": InputSpec(
        10_072,
        "1cc7e211c50685c3eed3d1b4582869d0a65a559a2114c0087fac2646f4fc883e",
        KERNEL / "include/linux/usb/typec/maxim/max77705_usbc.h",
        "max77705_usbc.h",
    ),
}


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _stable_read(path: Path, label: str, limit: int = 2 * 1024 * 1024) -> bytes:
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
    identity = lambda value: (  # noqa: E731
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
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
        existing = _stable_read(path, f"existing {path.name}")
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
        snapshot = SNAPSHOT_ROOT / spec.snapshot_name
        if snapshot.exists():
            data = _stable_read(snapshot, f"P3.19 snapshot {name}")
            info = snapshot.stat()
            if stat.S_IMODE(info.st_mode) != 0o400 or info.st_nlink != 1:
                raise AuditError(f"P3.19 snapshot mode differs: {name}")
            if spec.source.exists():
                source = _stable_read(spec.source, f"P3.19 source {name}")
                if source != data:
                    raise AuditError(f"P3.19 source/snapshot bytes differ: {name}")
        else:
            data = _stable_read(spec.source, f"P3.19 source {name}")
            if materialize:
                _write_exclusive(snapshot, data)
        if receipt(data) != {"size": spec.size, "sha256": spec.sha256}:
            raise AuditError(f"P3.19 exact input identity differs: {name}")
        loaded[name] = data
    return loaded


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
            raise AuditError(f"{label} section headers exceed the file")
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
        self.by_name = {section.name: section for section in self.sections}
        if len(self.by_name) != len(self.sections):
            raise AuditError(f"{label} section names are not unique")
        self.symbols = self._symbols()
        self.relocations = self._relocations()

    def _slice(self, offset: int, size: int, what: str) -> bytes:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise AuditError(f"{self.label} {what} exceeds the file")
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
        section = self.section(name)
        return self._slice(section.offset, section.size, f"section {name}")

    def _symbols(self) -> tuple[Symbol, ...]:
        table = self.section(".symtab")
        if table.kind != 2 or table.entry_size != 24 or table.link >= len(self.sections):
            raise AuditError(f"{self.label} symbol table contract differs")
        strings_section = self.sections[table.link]
        strings = self._slice(strings_section.offset, strings_section.size, "symbol strings")
        body = self.section_bytes(".symtab")
        if len(body) % 24:
            raise AuditError(f"{self.label} symbol table is truncated")
        out = []
        for index, cursor in enumerate(range(0, len(body), 24)):
            name_off, info, _other, section_index, value, size = struct.unpack_from(
                "<IBBHQQ", body, cursor
            )
            name = self._cstring(strings, name_off)
            if not name and info & 0xF == 3 and section_index < len(self.sections):
                name = self.sections[section_index].name
            out.append(Symbol(index, name, section_index, value, size))
        return tuple(out)

    def symbol(self, name: str) -> Symbol:
        matches = [symbol for symbol in self.symbols if symbol.name == name]
        if len(matches) != 1:
            raise AuditError(f"{self.label} symbol cardinality differs: {name}={len(matches)}")
        symbol = matches[0]
        if symbol.section_index == 0 or symbol.section_index >= len(self.sections):
            raise AuditError(f"{self.label} symbol is not defined: {name}")
        return symbol

    def symbol_bytes(self, name: str) -> bytes:
        symbol = self.symbol(name)
        section = self.sections[symbol.section_index]
        relative = symbol.value - section.address
        if relative < 0 or relative + symbol.size > section.size or not symbol.size:
            raise AuditError(f"{self.label} symbol bounds differ: {name}")
        return self._slice(section.offset + relative, symbol.size, f"symbol {name}")

    def _relocations(self) -> tuple[Relocation, ...]:
        out = []
        text_index = self.section(".text").index
        for section in self.sections:
            if section.kind != 4 or section.info != text_index:
                continue
            if section.entry_size != 24 or section.link >= len(self.sections):
                raise AuditError(f"{self.label} text relocation contract differs")
            body = self._slice(section.offset, section.size, f"relocations {section.name}")
            if len(body) % 24:
                raise AuditError(f"{self.label} text relocations are truncated")
            for cursor in range(0, len(body), 24):
                offset, info, addend = struct.unpack_from("<QQq", body, cursor)
                symbol_index = info >> 32
                if symbol_index >= len(self.symbols):
                    raise AuditError(f"{self.label} relocation symbol differs")
                out.append(
                    Relocation(offset, info & 0xFFFFFFFF, self.symbols[symbol_index].name, addend)
                )
        return tuple(out)

    def relocation(self, offset: int) -> Relocation:
        matches = [item for item in self.relocations if item.offset == offset]
        if len(matches) != 1:
            raise AuditError(f"{self.label} relocation cardinality differs at {offset:#x}")
        return matches[0]

    def word(self, address: int) -> int:
        text = self.section(".text")
        relative = address - text.address
        if relative < 0 or relative + 4 > text.size or relative % 4:
            raise AuditError(f"{self.label} text address differs: {address:#x}")
        return struct.unpack_from("<I", self.data, text.offset + relative)[0]


def _sign_extend(value: int, bits: int) -> int:
    top = 1 << (bits - 1)
    return (value ^ top) - top


def _branch19_target(word: int, address: int) -> int:
    return address + (_sign_extend((word >> 5) & 0x7FFFF, 19) << 2)


def _branch26_target(word: int, address: int) -> int:
    return address + (_sign_extend(word & 0x3FFFFFF, 26) << 2)


def _require_word(elf: Elf64, address: int, expected: int, label: str) -> None:
    actual = elf.word(address)
    if actual != expected:
        raise AuditError(f"{label} instruction differs at {address:#x}: {actual:#x}")


def _require_relocation(
    elf: Elf64, address: int, kind: int, symbol: str, addend: int, label: str
) -> None:
    actual = elf.relocation(address)
    if actual != Relocation(address, kind, symbol, addend):
        raise AuditError(f"{label} relocation differs at {address:#x}: {actual}")


def _stores_to_word_offset(elf: Elf64, byte_offset: int) -> list[int]:
    text = elf.section(".text")
    found = []
    for address in range(text.address, text.address + text.size, 4):
        word = elf.word(address)
        if word & 0xFFC00000 != 0xB9000000:
            continue
        if ((word >> 10) & 0xFFF) * 4 == byte_offset:
            found.append(address)
    return found


def _jump_target(elf: Elf64, table_offset: int, base: int, value: int) -> int:
    rodata = elf.section_bytes(".rodata")
    index = value - 1
    if index < 0 or table_offset + (index + 1) * 2 > len(rodata):
        raise AuditError("MUIC attach jump-table index differs")
    entry = struct.unpack_from("<H", rodata, table_offset + index * 2)[0]
    return base + entry * 4


def audit_pdic_semantics(data: bytes) -> dict[str, Any]:
    elf = Elf64(data, "pdic_max77705.ko")
    detect = elf.symbol("max77705_muic_detect_dev")
    if (detect.value, detect.size) != (0x177C4, 4_024):
        raise AuditError("MAX77705 detect symbol bounds differ")
    # The handle-attach jump table is indexed by new_dev - 1.  USB=1, CDP=2,
    # JIG_USB_OFF=23 and JIG_USB_ON=24 all enter the same inlined USB block.
    _require_relocation(elf, 0x18180, 275, ".rodata", 0x5DE, "attach jump table")
    attach_targets = {
        str(value): _jump_target(elf, 0x5DE, 0x17C64, value)
        for value in (1, 2, 23, 24)
    }
    if set(attach_targets.values()) != {0x18198}:
        raise AuditError(f"USB/CDP attach dispatch differs: {attach_targets}")

    # pdata is at muic_data+120 and usb_path at pdata+12.  Zero selects AP,
    # one selects CP, and every other value reaches only the invalid log.
    expected_words = {
        0x1819C: 0xF9403E76,
        0x181AC: 0xB9400EC2,
        0x181B8: 0xB9400EC8,
        0x181BC: 0x7100051F,
        0x181C0: 0x54001340,
        0x181C4: 0x34FFD508,
        0x181D8: 0x140000C3,
    }
    for address, word in expected_words.items():
        _require_word(elf, address, word, "usb_path guard")
    if _branch19_target(elf.word(0x181C0), 0x181C0) != 0x18428:
        raise AuditError("usb_path CP branch target differs")
    if _branch19_target(elf.word(0x181C4), 0x181C4) != 0x17C64:
        raise AuditError("usb_path AP branch target differs")
    if _branch26_target(elf.word(0x181D8), 0x181D8) != 0x184E4:
        raise AuditError("usb_path invalid branch target differs")
    _require_relocation(elf, 0x181A4, 275, ".rodata", 0x7450, "attach function name")
    _require_relocation(elf, 0x17C6C, 275, ".rodata", 0x215D, "AP function name")

    # The inlined AP block has no conditional branch before COM_USB is formed.
    # The only later suppression is max77705_switch_path's fac_water_enable.
    _require_word(elf, 0x17C90, 0x52800122, "COM_USB log value")
    _require_word(elf, 0x17C94, 0x52800137, "COM_USB command value")
    _require_word(elf, 0x17CB8, 0xB9445502, "fac_water_enable load")
    _require_word(elf, 0x17CBC, 0x35001702, "fac_water_enable guard")
    if _branch19_target(elf.word(0x17CBC), 0x17CBC) != 0x17F9C:
        raise AuditError("fac_water_enable skip target differs")
    _require_word(elf, 0x17CF8, 0x529FE0C8, "CONTROL1 opcode")
    _require_word(elf, 0x17D0C, 0x3901D3FF, "CONTROL1 read length")
    _require_word(elf, 0x17D10, 0x39010FF7, "CONTROL1 data byte")
    _require_relocation(
        elf, 0x17D18, 283, "max77705_usbc_opcode_write", 0, "CONTROL1 write call"
    )
    conditional_masks = (
        (0xFF000010, 0x54000000),  # b.cond
        (0x7E000000, 0x34000000),  # cbz/cbnz
        (0x7E000000, 0x36000000),  # tbz/tbnz
    )
    early_conditionals = []
    for address in range(0x17C64, 0x17CB4, 4):
        word = elf.word(address)
        if any(word & mask == value for mask, value in conditional_masks):
            early_conditionals.append(address)
    if early_conditionals:
        raise AuditError(f"com_to_usb_ap gained an early guard: {early_conditionals}")

    # fac_water_enable is zeroed with the kzalloc'd usbc_data.  Its only two
    # stores in this module are cmd 3 -> 1 and cmd 4 -> 0, in the control-option
    # function, whose only call site is the PDIC sysfs setter.
    stores = _stores_to_word_offset(elf, 1_108)
    if stores != [0x9D70, 0x9DA0]:
        raise AuditError(f"fac_water_enable store set differs: {stores}")
    _require_word(elf, 0x9D70, 0xB9045668, "fac_water_enable set")
    _require_word(elf, 0x9DA0, 0xB904567F, "fac_water_enable clear")
    control_calls = [
        relocation.offset
        for relocation in elf.relocations
        if relocation.kind == 283
        and relocation.symbol == "max77705_control_option_command"
    ]
    sysfs = elf.symbol("max77705_sysfs_set_prop")
    if control_calls != [0xEBEC] or not sysfs.value <= control_calls[0] < sysfs.value + sysfs.size:
        raise AuditError("fac_water_enable producer is not sysfs-only")
    if b"max77705_control_option_command\0" in elf.section_bytes("__ksymtab_strings"):
        raise AuditError("control-option setter unexpectedly became a kernel export")

    # A fresh MUIC probe publishes NONE before the initial detect call.  Thus a
    # first CDP=2 observation is not rejected as a duplicate attach.
    _require_word(elf, 0x16650, 0xB900827F, "initial attached_dev NONE")
    _require_relocation(elf, 0x16C94, 283, ".text", 0x177C4, "initial detect call")
    detect_bytes = elf.symbol_bytes("max77705_muic_detect_dev")
    if receipt(detect_bytes) != {
        "size": 4_024,
        "sha256": "7677a9e3227ec22d17ded3ae6994f8095e18bd778fbabbac12bbc6d500add3b3",
    }:
        raise AuditError("MAX77705 detect symbol bytes differ")

    return {
        "detect_symbol": {"address": detect.value, **receipt(detect_bytes)},
        "attached_dev_dispatch": {
            "usb": attach_targets["1"],
            "cdp": attach_targets["2"],
            "jig_usb_off": attach_targets["23"],
            "jig_usb_on": attach_targets["24"],
            "shared_usb_block": 0x18198,
        },
        "usb_path_guard": {
            "field_offset": 12,
            "ap_value": 0,
            "ap_target": 0x17C64,
            "cp_value": 1,
            "cp_target": 0x18428,
            "other_values_write": False,
        },
        "com_to_usb_ap": {
            "early_conditional_branches": [],
            "control1_value": 0x09,
            "opcode": 0x06,
            "opcode_write_call": 0x17D18,
        },
        "fac_water_guard": {
            "field_offset": 1_108,
            "skip_branch": 0x17CBC,
            "skip_target": 0x17F9C,
            "write_sites": stores,
            "producer": "max77705_control_option_command",
            "sole_call_site": control_calls[0],
            "sole_caller": "max77705_sysfs_set_prop",
            "kernel_exported": False,
        },
        "fresh_probe": {
            "attached_dev_initial": 0,
            "initial_detect_irq": -1,
            "initial_detect_call": 0x16C94,
        },
    }


def audit_common_semantics(data: bytes) -> dict[str, Any]:
    elf = Elf64(data, "common_muic.ko")
    parameter = elf.symbol_bytes("muic_param_pmic_info")
    if parameter != b"\xff\xff\xff\xff":
        raise AuditError("muic_param_pmic_info default differs")
    _require_relocation(elf, 0x1CCC, 275, ".data", 0x11C, "switch_sel parameter")
    _require_word(elf, 0x1CE0, 0x12002D13, "switch_sel mask")
    _require_relocation(elf, 0x5C4, 275, "muic_pdata", 12, "usb_path address")
    for address, word in {
        0x5D0: 0x12000276,
        0x5D4: 0x520002C8,
        0x5D8: 0xB90002A8,
    }.items():
        _require_word(elf, address, word, "usb_path initializer")
    no_parameter_switch_sel = 0xFFFFFFFF & 0xFFF
    no_parameter_usb_path = ((no_parameter_switch_sel & 1) ^ 1)
    stock_parameter_usb_path = ((3 & 1) ^ 1)
    if no_parameter_usb_path != 0 or stock_parameter_usb_path != 0:
        raise AuditError("AP path arithmetic differs")
    return {
        "muic_param_pmic_info_default": -1,
        "switch_sel_mask": 0xFFF,
        "usb_path_formula": "(switch_sel & 1) ^ 1",
        "no_parameter_switch_sel": no_parameter_switch_sel,
        "no_parameter_usb_path": no_parameter_usb_path,
        "stock_parameter_3_usb_path": stock_parameter_usb_path,
        "muic_path_usb_ap": 0,
        "muic_path_usb_cp": 1,
    }


def audit_sources(inputs: dict[str, bytes]) -> dict[str, Any]:
    muic = inputs["max77705_muic_source"]
    usbc = inputs["max77705_usbc_source"]
    param = inputs["muic_param_source"]
    core = inputs["muic_core_source"]
    header = inputs["muic_header"]
    muic_header = inputs["max77705_muic_header"]
    usbc_header = inputs["max77705_usbc_header"]
    required = {
        "max77705_muic_source": (
            b"if (pdata->usb_path == MUIC_PATH_USB_AP)",
            b"ret = com_to_usb_ap(muic_data);",
            b"else if (pdata->usb_path == MUIC_PATH_USB_CP)",
            b"if (muic_data->usbc_pdata->fac_water_enable)",
            b"write_data.opcode = COMMAND_CONTROL1_WRITE;",
            b"write_data.write_data[0] = reg_val;",
        ),
        "max77705_usbc_source": (
            b"usbpd_data->fac_water_enable = 1;",
            b"usbpd_data->fac_water_enable = 0;",
            b"max77705_control_option_command(usbpd_data, mode);",
            b"usbc_data =  kzalloc(sizeof(struct max77705_usbc_platform_data), GFP_KERNEL);",
        ),
        "muic_param_source": (
            b"static int muic_param_pmic_info = -1;",
            b"local_switch_sel = local_pmic_info & 0xfff;",
        ),
        "muic_core_source": (
            b"pdata->usb_path = MUIC_PATH_USB_AP;",
            b"if (switch_sel & SWITCH_SEL_USB_MASK)",
            b"pdata->usb_path = MUIC_PATH_USB_CP;",
        ),
        "muic_header": (
            b"MUIC_PATH_USB_AP\t= 0,",
            b"ATTACHED_DEV_USB_MUIC = 1,",
            b"ATTACHED_DEV_CDP_MUIC,",
        ),
        "max77705_muic_header": (
            b"COM_USB\t\t= (MAX77705_MUIC_NOBCCOMP_DIS",
            b"COM_USB_CP\t= (MAX77705_MUIC_NOBCCOMP_EN",
        ),
        "max77705_usbc_header": (b"int fac_water_enable;",),
    }
    bodies = {
        "max77705_muic_source": muic,
        "max77705_usbc_source": usbc,
        "muic_param_source": param,
        "muic_core_source": core,
        "muic_header": header,
        "max77705_muic_header": muic_header,
        "max77705_usbc_header": usbc_header,
    }
    for name, tokens in required.items():
        body = bodies[name]
        missing = [token for token in tokens if token not in body]
        if missing:
            raise AuditError(f"source semantic seam differs: {name} {missing!r}")
    if usbc.count(b"fac_water_enable = 1;") != 1 or usbc.count(b"fac_water_enable = 0;") != 1:
        raise AuditError("fac_water_enable source writer count differs")
    if usbc.count(b"max77705_control_option_command(usbpd_data, mode);") != 1:
        raise AuditError("control-option source caller count differs")
    return {
        name: receipt(body)
        for name, body in sorted(bodies.items())
    }


def build_result(inputs: dict[str, bytes], *, enforce_identity: bool = True) -> dict[str, Any]:
    if set(inputs) != set(INPUTS):
        raise AuditError("P3.19 input key set differs")
    identities = {}
    for name, data in sorted(inputs.items()):
        identities[name] = receipt(data)
        spec = INPUTS[name]
        if enforce_identity and identities[name] != {"size": spec.size, "sha256": spec.sha256}:
            raise AuditError(f"P3.19 input identity differs: {name}")
    pdic = audit_pdic_semantics(inputs["pdic_max77705_module"])
    common = audit_common_semantics(inputs["common_muic_module"])
    source = audit_sources(inputs)
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
        "source_semantics": source,
        "binary_semantics": {
            "pdic_max77705": pdic,
            "common_muic": common,
        },
        "conclusion": {
            "observed_stock_attach_type": "ATTACHED_DEV_CDP_MUIC",
            "observed_stock_attach_value": 2,
            "cdp_dispatches_to_usb_path_guard": True,
            "no_parameter_load_selects_ap": True,
            "stock_parameter_3_selects_ap": True,
            "com_to_usb_ap_has_pogo_guard_in_this_binary": False,
            "fac_water_is_the_only_post_ap_write_suppression": True,
            "fac_water_initially_zero": True,
            "fac_water_can_be_set_only_by_pdic_sysfs_control_option": True,
            "guard_result_for_no_parameter_no_sysfs_load": "COM_USB_0x09_ENQUEUED",
            "these_guards_explain_prior_candidate_silence": False,
            "remaining_boundary": (
                "module probe/bind, initial status classification, IRQ/DT wiring, "
                "and opcode queue-to-I2C delivery"
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
    data = encode(build_result(inputs))
    if args.audit_only:
        sys.stdout.buffer.write(data)
        return 0
    _write_exclusive(OUTPUT, data)
    sys.stdout.write(f"{VERDICT} {len(data)} {hashlib.sha256(data).hexdigest()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
