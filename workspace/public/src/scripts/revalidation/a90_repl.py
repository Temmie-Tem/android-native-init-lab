#!/usr/bin/env python3
"""Host-side driver for the flash-once Tier-2 runtime kernel REPL (v1-repl image).

This started as the v2a1 unit and now also carries the v2a2 host driver. It
does *not* build a new boot image. It drives the
already-live-proven `boot_linux_tier2_repl_v1_repl.img` (SHA256
b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65) over the
existing serial bridge, resolving kernel symbols *by name* from the
fixed `a90_stock_kallsyms_extract.py` System.map and turning the per-boot KASLR
slide (op 0) into named `peek`/`call`/owned-buffer `poke`:

    runtime_vaddr(symbol) = link_vaddr(symbol, System.map) + slide

The REPL stub hijacks `kgsl_pwrctrl_force_no_nap_store`
(`/sys/class/kgsl/kgsl-3d0/force_no_nap`). A write to that node carries a binary
command buffer; the stub printk's one `A90R%llx` line per op, read back via
`dmesg`. Both the write and the dmesg read go through the native-init `run`
builtin, whose child stdout is captured into the A90P1 console block.

Command buffer layout (matches build_kernel_tier2_repl_v1_repl.py):

    +0x00 u64 magic  (0xA90C0DE5DEADBEEF)
    +0x08 u8  op     (0 slide, 1 peek, 2 poke, 3 call)
    +0x10 u64 arg0   (peek/poke addr, call target)
    +0x18 u64 arg1   (peek len, poke val, call x0)
    +0x20 u64 arg2   (poke width, call x1)
    +0x28..+0x50     (call x2..x7)

Safety: normal selftest only *reads* with `peek` and calls real function
entries (JOPP-gated, verified `u32(entry-4)==0x00BE7BAD` against the static
image). The v2a2 `poke-roundtrip` command issues `poke` only into a fresh
`__kmalloc` buffer it owns, verifies via `peek`, then calls `kfree`. If the
recovered kallsyms map mislabels the slab region, `--use-recovered-allocator-
exports` first recovers ground-truth `__kmalloc`/`kfree` link addresses from
static export string references. Per-boot raw runtime pointers and the slide
are kept out of stdout and committed artifacts; only symbolic PASS/FAIL and
link-relative facts are surfaced. Private evidence (with raw values) is written
under workspace/private when --evidence-dir is given.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import a90ctl  # noqa: E402
import a90_transport as transport  # noqa: E402
import build_kernel_tier2_stage_c_direct_bl_printk as stage_c  # noqa: E402
import build_kernel_tier2_repl_v1_repl as v1repl  # noqa: E402

NODE = v1repl.SYSFS_NODE
REPL_MAGIC = v1repl.REPL_MAGIC
JOPP_MAGIC = stage_c.U32_MAGIC
ENTRY_OFF = v1repl.ENTRY_OFF
ENTRY_VADDR = stage_c.kernel_vaddr(ENTRY_OFF)
ADR_SELF_LINK_VADDR = ENTRY_VADDR + v1repl.ADR_SELF_WORD_INDEX * 4
FORMAT_LINK_VADDR = ENTRY_VADDR + v1repl.FORMAT_WORD_INDEX * 4

OP_SLIDE = v1repl.OP_SLIDE
OP_PEEK = v1repl.OP_PEEK
OP_POKE = v1repl.OP_POKE
OP_CALL = v1repl.OP_CALL
PEEK_MAX_LEN = v1repl.PEEK_MAX_LEN
REPLAY_SAFE_OPS = frozenset((OP_SLIDE, OP_PEEK))

CMD_BUF_LEN = 0x58  # magic + op + arg0..arg8
ARG_BASE = 0x10
MASK64 = (1 << 64) - 1

DEFAULT_BUSYBOX = "/bin/busybox"
DEFAULT_IMAGE = "workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img"
DEFAULT_DMESG_TAIL = 16
DEFAULT_GFP_HEADER = (
    REPO_ROOT
    / "workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource"
    / "Kernel/include/linux/gfp.h"
)

KMALLOC_ROUNDTRIP_SIZE = 0x1000
POKE_SENTINEL_A = 0xA90F00D1CAFE0001
POKE_SENTINEL_B = 0x1122334455667788
POKE_SENTINEL_32 = 0xC001D00D
DEFAULT_READ_CHUNK = PEEK_MAX_LEN
KERNEL_LOWMEM_MIN = 0xFFFFFFC000000000
KERNEL_LOWMEM_MAX = 0xFFFFFFFFFFFFFFFF
ALLOCATOR_EXPORT_REQUIRED = ("__kmalloc", "kfree")
ALLOCATOR_EXPORT_OPTIONAL = ("kmalloc_order", "kmalloc_order_trace")
MIN_ALLOCATOR_EXPORT_BL_XREFS = {
    "__kmalloc": 100,
    "kfree": 100,
}
EXPORT_GROUND_TRUTH_SYMBOLS = frozenset(ALLOCATOR_EXPORT_REQUIRED)
MIN_VERIFIED_DIRECT_BL_XREFS = 1
KNOWN_UNSAFE_CALL_TARGETS = {
    "kallsyms_lookup_name": (
        "faulted/rebooted during v2a1 live validation; resolve symbols from "
        "static evidence instead of calling this target"
    ),
}
EXPORT_NAME_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_\.]{0,127}\x00")
EXPORT_RECORD_NAME_DELTA = 24
FUNCTION_SYMBOL_KINDS = frozenset("TtWw")
MAP_AUDIT_ANCHORS = ("printk", "__kmalloc", "kfree")
PRINTK_LIVE_PROOF = "v2a1 named call printk(format,sentinel) echoed the sentinel"

A64_BL_MASK = 0xFC000000
A64_BL = 0x94000000
A64_LDR64_UNSIGNED_BASE = 0xF9400000
A64_LDR32_UNSIGNED_BASE = 0xB9400000
A64_LDRB_UNSIGNED_BASE = 0x39400000
A64_LDRH_UNSIGNED_BASE = 0x79400000
A64_LDR_UNSIGNED_MASK = 0xFFC003E0
A64_RET = 0xD65F03C0
A64_MOV_W0_WZR = 0x2A1F03E0
A64_MOV_X0_XZR = 0xAA1F03E0

ALLOCATOR_ABI_CANDIDATES: tuple[dict[str, str | None], ...] = (
    {
        "symbol": "__kmalloc",
        "free_symbol": "kfree",
        "expected_abi": "size,gfp",
        "note": "original v2a2 plan",
    },
    {
        "symbol": "__get_free_pages",
        "free_symbol": "free_pages",
        "expected_abi": "gfp,order",
        "note": "page allocator direct pointer candidate",
    },
    {
        "symbol": "get_zeroed_page",
        "free_symbol": "free_pages",
        "expected_abi": "gfp",
        "note": "single-page direct pointer candidate",
    },
    {
        "symbol": "alloc_pages_exact",
        "free_symbol": "free_pages_exact",
        "expected_abi": "size,gfp",
        "note": "exact-size page allocator candidate",
    },
    {
        "symbol": "__alloc_pages_nodemask",
        "free_symbol": "__free_pages",
        "expected_abi": "gfp,order,nid,nodemask",
        "note": "returns struct page, not directly pokable unless converted",
    },
    {
        "symbol": "kmalloc_order",
        "free_symbol": "kfree",
        "expected_abi": "size,gfp,order",
        "note": "large kmalloc fallback candidate",
    },
    {
        "symbol": "kmalloc_order_trace",
        "free_symbol": "kfree",
        "expected_abi": "size,gfp,order",
        "note": "large kmalloc trace candidate",
    },
    {
        "symbol": "vmalloc",
        "free_symbol": "vfree",
        "expected_abi": "size",
        "note": "vmalloc candidate",
    },
    {
        "symbol": "__vmalloc",
        "free_symbol": "vfree",
        "expected_abi": "size,gfp,prot",
        "note": "internal vmalloc candidate",
    },
    {
        "symbol": "kvmalloc_node",
        "free_symbol": "kvfree",
        "expected_abi": "size,gfp,node",
        "note": "kvmalloc candidate",
    },
    {
        "symbol": "kmem_cache_alloc",
        "free_symbol": "kmem_cache_free",
        "expected_abi": "cache,gfp",
        "note": "requires existing cache pointer, not size-only",
    },
    {
        "symbol": "kmem_cache_alloc_trace",
        "free_symbol": "kmem_cache_free",
        "expected_abi": "cache,gfp,size",
        "note": "requires existing cache pointer",
    },
    {
        "symbol": "mempool_kmalloc",
        "free_symbol": "mempool_kfree",
        "expected_abi": "gfp,pool_data",
        "note": "mempool helper candidate",
    },
)

ALLOCATOR_KNOWN_NON_SCALAR: dict[str, str] = {
    "__alloc_pages_nodemask": "returns struct page, not a writable kernel virtual pointer",
    "kmalloc_order": "this recovered path is not accepted as a pointer-return scalar allocator",
    "kmalloc_order_trace": "this recovered path is trace/bookkeeping shaped, not live-ready",
    "kmem_cache_alloc": "x0 is a kmem_cache pointer, not an allocation size",
    "kmem_cache_alloc_trace": "x0 is a kmem_cache pointer, not an allocation size",
    "mempool_kmalloc": "mempool helper ABI needs pool data, not a standalone size/gfp call",
    "mempool_kfree": "mempool helper ABI needs pool data, not standalone free",
    "vmalloc": "leaf thunk in this image returns allocator metadata/global, not vmalloc(size)",
    "__vmalloc": "this image treats x0 as a descriptor pointer before validating scalar args",
    "kvmalloc_node": "this image treats x0 as a descriptor/context pointer",
}

A90R_RE = re.compile(r"A90R([0-9a-fA-F]+)")


# ----------------------------------------------------------------------------
# Pure command-buffer + parsing helpers (no device, unit-tested)
# ----------------------------------------------------------------------------
def build_cmd_buffer(op: int, args: tuple[int, ...] = ()) -> bytes:
    if not 0 <= op <= 0xFF:
        raise ValueError(f"op out of range: {op}")
    if len(args) > 9:
        raise ValueError(f"too many args: {len(args)} (max 9: arg0..arg8)")
    buf = bytearray(CMD_BUF_LEN)
    struct.pack_into("<Q", buf, 0x00, REPL_MAGIC)
    buf[0x08] = op
    for index, value in enumerate(args):
        struct.pack_into("<Q", buf, ARG_BASE + 8 * index, value & MASK64)
    return bytes(buf)


def printf_octal(buf: bytes) -> str:
    """busybox-printf octal escape for an arbitrary binary buffer (no NULs lost)."""
    return "".join("\\%03o" % byte for byte in buf)


def write_node_sh(buf: bytes, node: str = NODE) -> str:
    return f"printf '{printf_octal(buf)}' > {node}"


def dmesg_tail_sh(lines: int) -> str:
    return f"dmesg | tail -n {int(lines)}"


def op_sh(buf: bytes, busybox: str = DEFAULT_BUSYBOX, *, tail_lines: int = 60,
          node: str = NODE) -> str:
    """Single on-device invocation: write the command buffer, then read back the
    op's `A90R` line *in the same shell* so the kernel-log ring cannot drain
    between the write and the read.

    Notes pinned from live A90 behaviour:
    - busybox `dmesg` here is read-and-CLEAR (consuming), so each op reads a
      fresh ring that already contains the record our write just produced.
    - the read is bounded with `tail -n N` because the native-init `run` console
      capture truncates long output; a raw unbounded `dmesg` loses the trailing
      `A90R` line in the boot-log flood.
    The newest `A90R` line is ours: the write we just issued is the most recent
    producer."""
    write = f"printf '{printf_octal(buf)}' > {node}"
    # No trailing `tail -1`: a `call` prints two A90R lines (the called function's
    # output and the stub's return value), and the call proof must see both.
    # Single-output ops just take the newest value host-side.
    read = f"dmesg | tail -n {int(tail_lines)} | grep -a A90R"
    return f"{write}; {read}"


def parse_a90r_values(text: str) -> list[int]:
    return [int(hexval, 16) for hexval in A90R_RE.findall(text)]


def parse_define_u32(text: str, name: str) -> int:
    match = re.search(
        rf"^#define\s+{re.escape(name)}\s+(0x[0-9a-fA-F]+|\d+)u?\b",
        text,
        re.MULTILINE,
    )
    if not match:
        raise RuntimeError(f"missing {name} in GFP header")
    return int(match.group(1), 0)


def parse_int_auto(text: str) -> int:
    try:
        value = int(text, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer/address: {text!r}") from exc
    if value < 0:
        raise argparse.ArgumentTypeError(f"value must be non-negative: {text!r}")
    return value


def derive_gfp_kernel_value(header: Path = DEFAULT_GFP_HEADER) -> tuple[int, dict[str, int]]:
    """Derive GFP_KERNEL from this kernel tree's include/linux/gfp.h.

    The public source currently uses widened reclaim bits, so deriving beats
    copying an expected value from notes.
    """
    text = header.read_text()
    components = {
        "___GFP_IO": parse_define_u32(text, "___GFP_IO"),
        "___GFP_FS": parse_define_u32(text, "___GFP_FS"),
        "___GFP_DIRECT_RECLAIM": parse_define_u32(text, "___GFP_DIRECT_RECLAIM"),
        "___GFP_KSWAPD_RECLAIM": parse_define_u32(text, "___GFP_KSWAPD_RECLAIM"),
    }
    value = 0
    for component in components.values():
        value |= component
    return value, components


def is_kernel_lowmem_pointer(value: int) -> bool:
    return (
        value != 0
        and KERNEL_LOWMEM_MIN <= value <= KERNEL_LOWMEM_MAX
        and (value & 0x7) == 0
    )


# ----------------------------------------------------------------------------
# System.map + static-image resolution (no device, unit-tested)
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Symbol:
    vaddr: int
    kind: str
    name: str


def load_system_map(path: Path) -> dict[str, Symbol]:
    symbols: dict[str, Symbol] = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        vaddr_text, kind, name = parts
        try:
            vaddr = int(vaddr_text, 16)
        except ValueError:
            continue
        # First definition wins; map is address-sorted so this is the lowest.
        symbols.setdefault(name, Symbol(vaddr, kind, name))
    if not symbols:
        raise RuntimeError(f"no symbols parsed from System.map: {path}")
    return symbols


def resolve_link(symbols: dict[str, Symbol], name: str) -> int:
    symbol = symbols.get(name)
    if symbol is None:
        raise RuntimeError(f"symbol not in System.map: {name}")
    return symbol.vaddr


@dataclass(frozen=True)
class VerifiedResolution:
    symbol: str
    link_vaddr: int | None
    verified: bool
    method: str
    evidence: dict[str, object]

    def public_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "link_vaddr": f"0x{self.link_vaddr:x}" if self.link_vaddr is not None else None,
            "verified": self.verified,
            "method": self.method,
            "evidence": self.evidence,
        }


def require_verified_resolution(resolution: VerifiedResolution, action: str) -> int:
    if resolution.verified and resolution.link_vaddr is not None:
        return resolution.link_vaddr
    blocked = resolution.evidence.get("blocked_reasons", [])
    raise ReplError(
        f"{action} target {resolution.symbol!r} is not verified "
        f"(method={resolution.method}, blocked={blocked})"
    )


@dataclass(frozen=True)
class StaticImage:
    kernel_off: int
    data: bytes  # whole boot image bytes

    def file_off(self, vaddr: int) -> int:
        off = vaddr - stage_c.KERNEL_FILE_VADDR_BASE
        if off < 0:
            raise RuntimeError(f"vaddr below kernel base: {vaddr:#x}")
        return off

    def u64_at_vaddr(self, vaddr: int) -> int:
        abs_off = self.kernel_off + self.file_off(vaddr)
        return struct.unpack_from("<Q", self.data, abs_off)[0]

    def u32_at_vaddr(self, vaddr: int) -> int:
        abs_off = self.kernel_off + self.file_off(vaddr)
        return struct.unpack_from("<I", self.data, abs_off)[0]

    def u32_words_at_vaddr(self, vaddr: int, count: int) -> list[int]:
        abs_off = self.kernel_off + self.file_off(vaddr)
        return [
            struct.unpack_from("<I", self.data, abs_off + index * 4)[0]
            for index in range(count)
        ]

    def bytes_at_vaddr(self, vaddr: int, length: int) -> bytes:
        if length < 0:
            raise RuntimeError(f"negative byte length: {length}")
        abs_off = self.kernel_off + self.file_off(vaddr)
        end = abs_off + length
        if end > len(self.data):
            raise RuntimeError(f"vaddr byte range outside image: {vaddr:#x}+{length:#x}")
        return self.data[abs_off:end]

    def find_symbol_string_vaddr(self, name: str) -> int:
        """Find a clean NUL-bounded ASCII occurrence of `name` and return its
        link vaddr. Used to hand kallsyms_lookup_name an existing kernel string
        pointer without any poke."""
        needle = b"\x00" + name.encode("ascii") + b"\x00"
        kernel = self.data[self.kernel_off :]
        hit = kernel.find(needle)
        if hit < 0:
            raise RuntimeError(f"no NUL-bounded kernel string for: {name!r}")
        string_off = hit + 1  # skip the leading NUL
        return stage_c.kernel_vaddr(string_off)


def load_static_image(path: Path) -> StaticImage:
    data = path.read_bytes()
    layout = stage_c.parse_boot_layout(data)
    return StaticImage(kernel_off=layout.kernel_off, data=data)


def static_raw_image(image: StaticImage) -> bytes:
    """Return the loaded arm64 Image bytes, excluding the 20-byte wrapper."""
    layout = stage_c.parse_boot_layout(image.data)
    kernel = image.data[layout.kernel_off : layout.kernel_off + layout.kernel_size]
    if kernel.startswith(b"UNCOMPRESSED_IMG"):
        size = struct.unpack_from("<I", kernel, stage_c.KERNEL_WRAPPER_RAW_OFFSET - 4)[0]
        start = stage_c.KERNEL_WRAPPER_RAW_OFFSET
        return kernel[start : start + size]
    return kernel


_STATIC_RAW_CACHE: dict[tuple[int, int], bytes] = {}
_DIRECT_BL_XREF_CACHE: dict[tuple[int, int], tuple[int, list[str]]] = {}
_EXPORT_CANDIDATE_CACHE: dict[tuple[int, str], list[dict[str, object]]] = {}
_EXPORT_STRING_INDEX_CACHE: dict[tuple[int, tuple[str, ...]], dict[int, tuple[str, ...]]] = {}
_EXPORT_REF_INDEX_CACHE: dict[tuple[int, tuple[str, ...]], dict[str, list[int]]] = {}


def cached_static_raw_image(image: StaticImage) -> bytes:
    key = (id(image.data), image.kernel_off)
    raw = _STATIC_RAW_CACHE.get(key)
    if raw is None:
        raw = static_raw_image(image)
        _STATIC_RAW_CACHE[key] = raw
    return raw


def _raw_off_to_vaddr(raw_off: int) -> int:
    return stage_c.KERNEL_TEXT_VADDR + raw_off


def _vaddr_to_raw_off(vaddr: int) -> int:
    return vaddr - stage_c.KERNEL_TEXT_VADDR


def _iter_exact_c_string_offsets(raw: bytes, text: str) -> list[int]:
    needle = text.encode("ascii") + b"\x00"
    hits: list[int] = []
    start = 0
    while True:
        off = raw.find(needle, start)
        if off < 0:
            return hits
        before = raw[off - 1] if off else 0
        if not (0x30 <= before <= 0x39 or 0x41 <= before <= 0x5A or before == 0x5F or 0x61 <= before <= 0x7A):
            hits.append(off)
        start = off + 1


def _iter_aligned_qword_hits(raw: bytes, value: int) -> list[int]:
    encoded = struct.pack("<Q", value & MASK64)
    hits: list[int] = []
    start = 0
    while True:
        off = raw.find(encoded, start)
        if off < 0:
            return hits
        if off % 8 == 0:
            hits.append(off)
        start = off + 1


def _is_static_jopp_text_entry(raw: bytes, vaddr: int) -> bool:
    raw_off = _vaddr_to_raw_off(vaddr)
    if raw_off < 4 or raw_off + 4 > len(raw):
        return False
    return struct.unpack_from("<I", raw, raw_off - 4)[0] == JOPP_MAGIC


def _count_direct_bl_xrefs(raw: bytes, target_vaddr: int) -> tuple[int, list[str]]:
    count = 0
    sample_sites: list[str] = []
    for off in range(0, len(raw) - 4, 4):
        word = struct.unpack_from("<I", raw, off)[0]
        if not _is_a64_bl(word):
            continue
        if _decode_a64_bl_target(_raw_off_to_vaddr(off), word) != target_vaddr:
            continue
        count += 1
        if len(sample_sites) < 8:
            sample_sites.append(f"0x{_raw_off_to_vaddr(off):x}")
    return count, sample_sites


def _count_direct_bl_xrefs_cached(raw: bytes, target_vaddr: int) -> tuple[int, list[str]]:
    key = (id(raw), target_vaddr)
    cached = _DIRECT_BL_XREF_CACHE.get(key)
    if cached is None:
        cached = _count_direct_bl_xrefs(raw, target_vaddr)
        _DIRECT_BL_XREF_CACHE[key] = cached
    return cached


def _function_words_from_raw(raw: bytes, link_vaddr: int, byte_count: int = 0x80) -> list[int]:
    raw_off = _vaddr_to_raw_off(link_vaddr)
    if raw_off < 0 or raw_off + byte_count > len(raw):
        raise RuntimeError(f"function address outside raw image: 0x{link_vaddr:x}")
    return [
        struct.unpack_from("<I", raw, raw_off + index * 4)[0]
        for index in range(byte_count // 4)
    ]


def _recover_export_candidates(raw: bytes, symbol: str) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for string_off in _iter_exact_c_string_offsets(raw, symbol):
        string_vaddr = _raw_off_to_vaddr(string_off)
        for name_ref_off in _iter_aligned_qword_hits(raw, string_vaddr):
            for value_off in range(max(0, name_ref_off - 0x40), name_ref_off, 8):
                value = struct.unpack_from("<Q", raw, value_off)[0]
                if not _is_static_jopp_text_entry(raw, value):
                    continue
                words = _function_words_from_raw(raw, value)
                deref = _first_precall_x0_deref(words)
                bl_count, sample_sites = _count_direct_bl_xrefs_cached(raw, value)
                candidates.append({
                    "symbol": symbol,
                    "link_vaddr": f"0x{value:x}",
                    "string_vaddr": f"0x{string_vaddr:x}",
                    "string_raw_off": f"0x{string_off:x}",
                    "name_ref_vaddr": f"0x{_raw_off_to_vaddr(name_ref_off):x}",
                    "name_ref_raw_off": f"0x{name_ref_off:x}",
                    "value_ref_vaddr": f"0x{_raw_off_to_vaddr(value_off):x}",
                    "value_ref_raw_off": f"0x{value_off:x}",
                    "name_ref_minus_value_ref": name_ref_off - value_off,
                    "jopp_entry": True,
                    "precall_x0_deref": deref,
                    "direct_bl_xref_count": bl_count,
                    "direct_bl_xref_sample_sites": sample_sites,
                })
    candidates.sort(
        key=lambda row: (
            row["precall_x0_deref"] is not None,
            -int(row["direct_bl_xref_count"]),
            int(str(row["link_vaddr"]), 16),
        )
    )
    return candidates


def _recover_export_candidates_cached(raw: bytes, symbol: str) -> list[dict[str, object]]:
    key = (id(raw), symbol)
    cached = _EXPORT_CANDIDATE_CACHE.get(key)
    if cached is None:
        cached = _recover_export_candidates(raw, symbol)
        _EXPORT_CANDIDATE_CACHE[key] = cached
    return cached


def exported_symbol_names(symbols: dict[str, Symbol]) -> tuple[str, ...]:
    return tuple(sorted(
        name[len("__ksymtab_"):]
        for name in symbols
        if name.startswith("__ksymtab_") and len(name) > len("__ksymtab_")
    ))


def _is_vaddr_inside_raw(raw: bytes, value: int) -> bool:
    raw_off = _vaddr_to_raw_off(value)
    return 0 <= raw_off < len(raw)


def _build_export_string_index(raw: bytes, names: tuple[str, ...]) -> dict[int, tuple[str, ...]]:
    key = (id(raw), names)
    cached = _EXPORT_STRING_INDEX_CACHE.get(key)
    if cached is not None:
        return cached
    wanted = set(names)
    by_vaddr: dict[int, set[str]] = {}
    for match in EXPORT_NAME_RE.finditer(raw):
        text = match.group()[:-1].decode("ascii", errors="ignore")
        if text in wanted:
            by_vaddr.setdefault(_raw_off_to_vaddr(match.start()), set()).add(text)
    built = {vaddr: tuple(sorted(values)) for vaddr, values in by_vaddr.items()}
    _EXPORT_STRING_INDEX_CACHE[key] = built
    return built


def _build_export_name_ref_index(raw: bytes, names: tuple[str, ...]) -> dict[str, list[int]]:
    key = (id(raw), names)
    cached = _EXPORT_REF_INDEX_CACHE.get(key)
    if cached is not None:
        return cached
    string_index = _build_export_string_index(raw, names)
    string_vaddrs = set(string_index)
    refs: dict[str, list[int]] = {name: [] for name in names}
    for off in range(0, len(raw) - 8, 8):
        value = struct.unpack_from("<Q", raw, off)[0]
        if value not in string_vaddrs:
            continue
        for name in string_index[value]:
            refs.setdefault(name, []).append(off)
    _EXPORT_REF_INDEX_CACHE[key] = refs
    return refs


def _map_kind_is_function(kind: str | None) -> bool:
    return kind in FUNCTION_SYMBOL_KINDS if kind else False


def _audit_export_candidates_for_name(raw: bytes,
                                      symbols: dict[str, Symbol],
                                      name: str,
                                      name_ref_offsets: list[int]) -> list[dict[str, object]]:
    map_symbol = symbols.get(name)
    require_jopp = _map_kind_is_function(map_symbol.kind if map_symbol else None)
    seen: set[int] = set()
    candidates: list[dict[str, object]] = []
    for name_ref_off in name_ref_offsets:
        value_ref_off = name_ref_off - EXPORT_RECORD_NAME_DELTA
        if value_ref_off < 0:
            continue
        value = struct.unpack_from("<Q", raw, value_ref_off)[0]
        if value in seen or not _is_vaddr_inside_raw(raw, value):
            continue
        seen.add(value)
        jopp = _is_static_jopp_text_entry(raw, value)
        if require_jopp and not jopp:
            continue
        candidates.append({
            "symbol": name,
            "link_vaddr": f"0x{value:x}",
            "name_ref_vaddr": f"0x{_raw_off_to_vaddr(name_ref_off):x}",
            "name_ref_raw_off": f"0x{name_ref_off:x}",
            "value_ref_vaddr": f"0x{_raw_off_to_vaddr(value_ref_off):x}",
            "value_ref_raw_off": f"0x{value_ref_off:x}",
            "name_ref_minus_value_ref": EXPORT_RECORD_NAME_DELTA,
            "jopp_entry": jopp,
        })
    candidates.sort(key=lambda row: int(str(row["link_vaddr"]), 16))
    return candidates


def run_string_ref_map_audit(symbols: dict[str, Symbol],
                             image: StaticImage,
                             *,
                             row_limit: int = 80,
                             focus_symbols: tuple[str, ...] = ("__kmalloc", "kfree", "printk")) -> dict[str, object]:
    """Historical C2A audit.

    This is intentionally retained as a noisy diagnostic, not as an oracle:
    string-reference scanning can find unrelated qword tables that happen to
    mention an exported name. The high-confidence `run_map_audit` below is the
    default C2 oracle.
    """
    raw = cached_static_raw_image(image)
    names = exported_symbol_names(symbols)
    refs = _build_export_name_ref_index(raw, names)

    counts = {
        "map_match": 0,
        "map_mismatch": 0,
        "ambiguous": 0,
        "missing_recovery": 0,
        "missing_map_symbol": 0,
    }
    rows: list[dict[str, object]] = []
    focus_rows: dict[str, dict[str, object]] = {}
    mismatch_buckets: dict[str, int] = {}

    for name in names:
        map_symbol = symbols.get(name)
        map_link = map_symbol.vaddr if map_symbol else None
        candidates = _audit_export_candidates_for_name(raw, symbols, name, refs.get(name, []))
        row: dict[str, object] = {
            "symbol": name,
            "map_link_vaddr": f"0x{map_link:x}" if map_link is not None else None,
            "map_kind": map_symbol.kind if map_symbol else None,
            "candidate_count": len(candidates),
            "status": "missing-recovery",
            "selected_link_vaddr": None,
        }
        if map_link is None:
            counts["missing_map_symbol"] += 1
            row["status"] = "missing-map-symbol"
        elif not candidates:
            counts["missing_recovery"] += 1
        elif len(candidates) > 1:
            candidate_values = [int(str(candidate["link_vaddr"]), 16) for candidate in candidates]
            row["candidate_link_vaddrs"] = [candidate["link_vaddr"] for candidate in candidates[:8]]
            if map_link in candidate_values:
                counts["map_match"] += 1
                row["status"] = "map-match-ambiguous"
                row["selected_link_vaddr"] = f"0x{map_link:x}"
            else:
                counts["ambiguous"] += 1
                row["status"] = "ambiguous"
        else:
            selected = candidates[0]
            selected_link = int(str(selected["link_vaddr"]), 16)
            row["selected_link_vaddr"] = selected["link_vaddr"]
            row["jopp_entry"] = selected["jopp_entry"]
            if selected_link == map_link:
                counts["map_match"] += 1
                row["status"] = "map-match"
            else:
                counts["map_mismatch"] += 1
                row["status"] = "map-mismatch"
                bucket = f"0x{map_link & ~0xfffff:x}"
                mismatch_buckets[bucket] = mismatch_buckets.get(bucket, 0) + 1
                row["map_minus_recovered"] = map_link - selected_link

        if name in focus_symbols:
            row["candidates"] = candidates[:8]
            focus_rows[name] = row
        if len(rows) < row_limit and row["status"] not in ("map-match",):
            row_for_sample = dict(row)
            row_for_sample["candidates"] = candidates[:4]
            rows.append(row_for_sample)

    top_buckets = [
        {"map_region_base": bucket, "mismatch_count": count}
        for bucket, count in sorted(mismatch_buckets.items(), key=lambda item: (-item[1], item[0]))[:20]
    ]
    audited = len(names)
    return {
        "decision": "a90-repl-v2c-c2-map-audit-host-pass",
        "ok": True,
        "raw_runtime_values_redacted": True,
        "export_symbol_count": audited,
        "recovered_candidate_symbol_count": (
            audited - counts["missing_recovery"] - counts["missing_map_symbol"]
        ),
        "counts": counts,
        "map_match_rate": (counts["map_match"] / audited) if audited else 0,
        "focus_rows": focus_rows,
        "mismatch_region_buckets": top_buckets,
        "sample_rows": rows,
        "row_limit": row_limit,
        "next_required": (
            "use the drift report to fix or fence the kallsyms decoder; "
            "do not treat System.map as globally trustworthy"
        ),
    }


def _kernel_image_with_wrapper(image: StaticImage) -> bytes:
    layout = stage_c.parse_boot_layout(image.data)
    return image.data[layout.kernel_off : layout.kernel_off + layout.kernel_size]


def _stage_c_printk_link_vaddr(image: StaticImage) -> int:
    _magic_off, entry_off, _helper_off, _emit_off = (
        stage_c.locate_printk_variadic_wrapper(_kernel_image_with_wrapper(image))
    )
    return stage_c.kernel_vaddr(entry_off)


def _format_precall_x0_deref(deref: object) -> str | None:
    if not isinstance(deref, dict):
        return None
    return (
        f"+0x{int(deref['offset']):x}/imm=0x{int(deref['imm']):x}/"
        f"word=0x{int(deref['word']):08x}"
    )


def _map_function_evidence(symbols: dict[str, Symbol],
                           image: StaticImage,
                           raw: bytes,
                           link_vaddr: int) -> dict[str, object]:
    magic = image.u32_at_vaddr(link_vaddr - 4)
    bl_count, sample_sites = _count_direct_bl_xrefs_cached(raw, link_vaddr)
    shape = _scan_function_shape(symbols, image, link_vaddr)
    return {
        "entry_minus_4": f"0x{magic:08x}",
        "jopp_entry": magic == JOPP_MAGIC,
        "direct_bl_xref_count": bl_count,
        "direct_bl_xref_sample_sites": sample_sites,
        "shape": shape,
        "precall_x0_deref": shape["precall_x0_deref"],
    }


def _allocator_map_audit_row(symbols: dict[str, Symbol],
                             image: StaticImage,
                             raw: bytes,
                             name: str) -> dict[str, object]:
    map_symbol = symbols.get(name)
    map_link = map_symbol.vaddr if map_symbol else None
    candidates = _recover_export_candidates_cached(raw, name)
    min_xrefs = MIN_ALLOCATOR_EXPORT_BL_XREFS[name]
    passing = [
        candidate for candidate in candidates
        if (
            candidate.get("jopp_entry")
            and candidate.get("precall_x0_deref") is None
            and int(candidate["direct_bl_xref_count"]) >= min_xrefs
        )
    ]
    row: dict[str, object] = {
        "symbol": name,
        "status": "unknown",
        "truth_link_vaddr": None,
        "map_link_vaddr": f"0x{map_link:x}" if map_link is not None else None,
        "method": "high-confidence-export-candidate-plus-map-shape",
        "candidate_count": len(candidates),
        "passing_candidate_count": len(passing),
        "candidate_link_vaddrs": [candidate["link_vaddr"] for candidate in candidates[:8]],
        "high_confidence_reasons": [],
        "blocked_reasons": [],
    }
    high_confidence = row["high_confidence_reasons"]
    blocked = row["blocked_reasons"]
    assert isinstance(high_confidence, list)
    assert isinstance(blocked, list)

    if map_link is None:
        blocked.append("missing-map-symbol")
        return row
    if len(passing) != 1:
        blocked.append(f"expected-one-high-confidence-export-candidate:{len(passing)}")
        return row

    selected = passing[0]
    selected_link = int(str(selected["link_vaddr"]), 16)
    row["truth_link_vaddr"] = f"0x{selected_link:x}"
    row["selected_direct_bl_xref_count"] = selected["direct_bl_xref_count"]
    row["selected_precall_x0_deref"] = selected["precall_x0_deref"]
    high_confidence.extend([
        "single-passing-export-candidate",
        "candidate-is-jopp-entry",
        "candidate-has-no-precall-x0-deref",
        f"candidate-direct-bl-xrefs>={min_xrefs}",
    ])

    map_evidence = _map_function_evidence(symbols, image, raw, map_link)
    row.update({
        "map_jopp_entry": map_evidence["jopp_entry"],
        "map_entry_minus_4": map_evidence["entry_minus_4"],
        "map_direct_bl_xref_count": map_evidence["direct_bl_xref_count"],
        "map_precall_x0_deref": map_evidence["precall_x0_deref"],
        "map_precall_x0_deref_summary": _format_precall_x0_deref(map_evidence["precall_x0_deref"]),
    })

    if selected_link == map_link:
        row["status"] = "map-match"
        high_confidence.append("map-agrees-with-high-confidence-candidate")
        return row

    map_reject_reasons: list[str] = []
    if int(map_evidence["direct_bl_xref_count"]) < min_xrefs:
        map_reject_reasons.append(
            f"map-target-low-direct-bl-xrefs:{map_evidence['direct_bl_xref_count']}<{min_xrefs}"
        )
    if map_evidence["precall_x0_deref"] is not None:
        map_reject_reasons.append(
            "map-target-precall-x0-deref:"
            f"{_format_precall_x0_deref(map_evidence['precall_x0_deref'])}"
        )
    if not map_reject_reasons:
        blocked.append("map-disagrees-but-map-address-not-independently-refuted")
        return row

    row["status"] = "map-mismatch"
    row["map_wrong_evidence"] = map_reject_reasons
    row["map_minus_truth"] = map_link - selected_link
    high_confidence.append("map-address-independently-refuted")
    return row


def _printk_map_audit_row(symbols: dict[str, Symbol],
                          image: StaticImage,
                          raw: bytes) -> dict[str, object]:
    name = "printk"
    map_symbol = symbols.get(name)
    map_link = map_symbol.vaddr if map_symbol else None
    signature_link = _stage_c_printk_link_vaddr(image)
    resolution = resolve_verified(symbols, image, name, purpose="call")
    noisy_candidates = _recover_export_candidates_cached(raw, name)
    row: dict[str, object] = {
        "symbol": name,
        "status": "unknown",
        "truth_link_vaddr": f"0x{signature_link:x}",
        "map_link_vaddr": f"0x{map_link:x}" if map_link is not None else None,
        "method": "stage-c-printk-signature+disasm-signature+xref+map",
        "live_proof": PRINTK_LIVE_PROOF,
        "string_ref_candidate_count": len(noisy_candidates),
        "string_ref_candidate_link_vaddrs": [
            candidate["link_vaddr"] for candidate in noisy_candidates[:8]
        ],
        "string_ref_candidates_promoted": False,
        "resolution": resolution.public_dict(),
        "high_confidence_reasons": [],
        "blocked_reasons": [],
    }
    high_confidence = row["high_confidence_reasons"]
    blocked = row["blocked_reasons"]
    assert isinstance(high_confidence, list)
    assert isinstance(blocked, list)

    if map_link is None:
        blocked.append("missing-map-symbol")
        return row
    if signature_link != map_link:
        row["status"] = "map-mismatch"
        row["map_wrong_evidence"] = ["stage-c-printk-signature-disagrees-with-map"]
        return row
    if not resolution.verified or resolution.link_vaddr != map_link:
        blocked.append("map-printk-failed-resolve_verified")
        return row

    map_evidence = _map_function_evidence(symbols, image, raw, map_link)
    row.update({
        "map_jopp_entry": map_evidence["jopp_entry"],
        "map_entry_minus_4": map_evidence["entry_minus_4"],
        "map_direct_bl_xref_count": map_evidence["direct_bl_xref_count"],
        "map_precall_x0_deref": map_evidence["precall_x0_deref"],
    })
    row["status"] = "map-match"
    high_confidence.extend([
        "stage-c-printk-signature-matches-map",
        "resolve_verified-accepts-map-target",
        "v2a1-live-call-proof",
        "noisy-string-ref-candidates-not-promoted",
    ])
    return row


def run_map_audit(symbols: dict[str, Symbol],
                  image: StaticImage,
                  *,
                  row_limit: int = 80,
                  focus_symbols: tuple[str, ...] = MAP_AUDIT_ANCHORS) -> dict[str, object]:
    """Sound C2 audit over high-confidence anchors.

    This deliberately does not claim a whole-map drift count from the C2A
    string-ref heuristic. A row becomes `map-mismatch` only when there is a
    single high-confidence alternative and the map address is independently
    refuted, or `map-match` when an independent semantic locator agrees with the
    map.
    """
    raw = cached_static_raw_image(image)
    rows: dict[str, dict[str, object]] = {}
    for name in focus_symbols:
        if name == "printk":
            rows[name] = _printk_map_audit_row(symbols, image, raw)
        elif name in ALLOCATOR_EXPORT_REQUIRED:
            rows[name] = _allocator_map_audit_row(symbols, image, raw, name)
        else:
            resolution = resolve_verified(symbols, image, name, purpose="call")
            status = "map-match" if resolution.verified else "unknown"
            rows[name] = {
                "symbol": name,
                "status": status,
                "truth_link_vaddr": (
                    f"0x{resolution.link_vaddr:x}" if resolution.link_vaddr is not None else None
                ),
                "map_link_vaddr": (
                    f"0x{symbols[name].vaddr:x}" if name in symbols else None
                ),
                "method": resolution.method,
                "resolution": resolution.public_dict(),
                "blocked_reasons": [] if resolution.verified else ["no-high-confidence-audit-rule"],
            }

    counts = {
        "map_match": sum(1 for row in rows.values() if row["status"] == "map-match"),
        "map_mismatch": sum(1 for row in rows.values() if row["status"] == "map-mismatch"),
        "unknown": sum(1 for row in rows.values() if row["status"] == "unknown"),
    }
    expected = {
        "printk": "map-match",
        "__kmalloc": "map-mismatch",
        "kfree": "map-mismatch",
    }
    anchor_failures = [
        f"{name}:{rows.get(name, {}).get('status')}!=expected:{status}"
        for name, status in expected.items()
        if name in rows and rows[name].get("status") != status
    ]
    ordered_rows = [rows[name] for name in focus_symbols if name in rows]
    return {
        "decision": (
            "a90-repl-v2c-c2c-high-confidence-map-audit-host-pass"
            if not anchor_failures else
            "a90-repl-v2c-c2c-high-confidence-map-audit-host-fail"
        ),
        "ok": not anchor_failures,
        "raw_runtime_values_redacted": True,
        "scope": "high-confidence anchors only; no whole-map drift count claimed",
        "method": (
            "semantic printk signature plus C1 resolve verification; allocator rows require "
            "a single JOPP/no-x0-deref/high-xref export candidate and independent map refutation"
        ),
        "audited_symbol_count": len(rows),
        "counts": counts,
        "focus_rows": rows,
        "sample_rows": ordered_rows[:row_limit],
        "anchor_failures": anchor_failures,
        "c2a_status": (
            "string-ref whole-map audit is retained as run_string_ref_map_audit() but is noisy "
            "and not a decoder-rewrite oracle"
        ),
        "next_required": (
            "locate the real __ksymtab/__ksymtab_strings section bounds for any broad drift map; "
            "until then, trust only verified call/poke resolutions and high-confidence rows"
        ),
    }


def recover_allocator_export_addresses(
    symbols: dict[str, Symbol],
    image: StaticImage,
    *,
    required: tuple[str, ...] = ALLOCATOR_EXPORT_REQUIRED,
    optional: tuple[str, ...] = ALLOCATOR_EXPORT_OPTIONAL,
) -> dict[str, object]:
    raw = cached_static_raw_image(image)
    rows: list[dict[str, object]] = []
    recovered: dict[str, int] = {}
    ok = True

    for symbol in (*required, *optional):
        candidates = _recover_export_candidates_cached(raw, symbol)
        selected = candidates[0] if candidates else None
        map_symbol = symbols.get(symbol)
        map_link = map_symbol.vaddr if map_symbol else None
        map_ksymtab = symbols.get(f"__ksymtab_{symbol}")
        map_ksymtab_first_qword = None
        if map_ksymtab is not None:
            try:
                map_ksymtab_first_qword = image.u64_at_vaddr(map_ksymtab.vaddr)
            except Exception:  # noqa: BLE001 - report unavailable as null
                map_ksymtab_first_qword = None

        row: dict[str, object] = {
            "symbol": symbol,
            "required": symbol in required,
            "map_link_vaddr": f"0x{map_link:x}" if map_link is not None else None,
            "map_ksymtab_vaddr": f"0x{map_ksymtab.vaddr:x}" if map_ksymtab is not None else None,
            "map_ksymtab_first_qword": (
                f"0x{map_ksymtab_first_qword:x}" if map_ksymtab_first_qword is not None else None
            ),
            "candidate_count": len(candidates),
            "candidates": candidates[:4],
            "status": "missing",
            "selected_link_vaddr": None,
            "blocked_reasons": [],
        }
        blocked = row["blocked_reasons"]
        assert isinstance(blocked, list)
        if selected is None:
            blocked.append("no-export-string-ref-candidate")
        else:
            selected_vaddr = int(str(selected["link_vaddr"]), 16)
            min_xrefs = MIN_ALLOCATOR_EXPORT_BL_XREFS.get(symbol, 0)
            row["selected_link_vaddr"] = selected["link_vaddr"]
            row["map_mismatch"] = map_link is not None and selected_vaddr != map_link
            row["selected_direct_bl_xref_count"] = selected["direct_bl_xref_count"]
            row["selected_precall_x0_deref"] = selected["precall_x0_deref"]
            if selected["precall_x0_deref"] is not None:
                blocked.append("selected-entry-dereferences-x0-before-first-bl")
            if int(selected["direct_bl_xref_count"]) < min_xrefs:
                blocked.append(f"selected-entry-low-bl-xrefs:{selected['direct_bl_xref_count']}<{min_xrefs}")
            if not blocked:
                row["status"] = "recovered"
                recovered[symbol] = selected_vaddr
        if symbol in required and row["status"] != "recovered":
            ok = False
        rows.append(row)

    return {
        "decision": (
            "a90-repl-v2a2rp-allocator-export-recovery-pass"
            if ok else "a90-repl-v2a2rp-allocator-export-recovery-fail"
        ),
        "ok": ok,
        "raw_runtime_values_redacted": True,
        "method": "absolute export string-reference recovery from static boot image",
        "note": (
            "System.map __ksymtab labels are drifted/zero in the raw image; "
            "ground truth is recovered from exact symbol strings and nearby JOPP text values"
        ),
        "recovered": {name: f"0x{value:x}" for name, value in sorted(recovered.items())},
        "rows": rows,
    }


# ----------------------------------------------------------------------------
# Live REPL transport
# ----------------------------------------------------------------------------
class ReplError(RuntimeError):
    pass


class ReplTransientNoiseError(ReplError):
    pass


@dataclass
class ReplConfig:
    host: str = a90ctl.DEFAULT_HOST
    port: int = a90ctl.DEFAULT_PORT
    busybox: str = DEFAULT_BUSYBOX
    timeout: float = 25.0
    dmesg_tail: int = DEFAULT_DMESG_TAIL
    settle_sec: float = 0.4
    safe_op_retries: int = 2
    retry_delay_sec: float = 0.2


class ReplSession:
    """Live driver over the serial bridge. Raw values stay in memory; callers
    decide what to surface."""

    def __init__(self, config: ReplConfig):
        self.config = config

    def _run_sh(self, sh_str: str, *, allow_error: bool = False) -> str:
        argv = ["run", self.config.busybox, "sh", "-c", sh_str]
        result = transport.run_serial_command(
            argv,
            host=self.config.host,
            port=self.config.port,
            timeout=self.config.timeout,
        )
        if not result.get("ok") and not allow_error:
            raise ReplError(
                f"serial run failed: rc={result.get('rc')} "
                f"stderr={result.get('stderr')!r}"
            )
        return str(result.get("stdout") or "")

    def hide(self) -> None:
        """Best-effort: drop the HUD menu so `run` is not [busy]."""
        try:
            a90ctl.bridge_exchange(
                self.config.host,
                self.config.port,
                "hide",
                min(self.config.timeout, 8.0),
                markers=(b"[busy]", b"[done]", b"[err]"),
            )
        except OSError:
            pass

    def set_panic_on_oops(self, value: int) -> None:
        self._run_sh(f"echo {int(value)} > /proc/sys/kernel/panic_on_oops")

    def _op(self, op: int, args: tuple[int, ...] = (), *, expect_output: bool = True):
        buf = build_cmd_buffer(op, args)
        if not expect_output:
            self._run_sh(write_node_sh(buf), allow_error=True)
            return None
        return self._op_values(op, args)[-1]

    def _op_values(self, op: int, args: tuple[int, ...] = (), *,
                   replay_safe: bool | None = None) -> list[int]:
        buf = build_cmd_buffer(op, args)
        replay_safe = (op in REPLAY_SAFE_OPS) if replay_safe is None else replay_safe
        attempts = 1 + (max(0, self.config.safe_op_retries) if replay_safe else 0)
        samples: list[str] = []
        for attempt in range(attempts):
            # Write + read in a single shell so the kernel-log ring cannot drain
            # between the two; the newest A90R line is this op's result.
            text = self._run_sh(
                op_sh(
                    buf,
                    self.config.busybox,
                    tail_lines=self.config.dmesg_tail,
                ),
                allow_error=True,
            )
            values = parse_a90r_values(text)
            if values:
                return values
            samples.append(text[-160:].replace("\n", "\\n"))
            if attempt + 1 < attempts:
                self.hide()
                if self.config.retry_delay_sec > 0:
                    time.sleep(self.config.retry_delay_sec)
        raise ReplTransientNoiseError(
            f"no A90R output captured for op={op} after {attempts} attempt(s); "
            f"replay_safe={replay_safe}; classify=transient-serial-or-ring-noise; "
            f"stdout_tail_samples={samples!r}"
        )

    # --- public ops --------------------------------------------------------
    def slide(self) -> int:
        runtime_pc = self._op(OP_SLIDE, ())
        return (runtime_pc - ADR_SELF_LINK_VADDR) & MASK64

    def peek_runtime(self, runtime_vaddr: int, length: int = 8) -> int:
        if not 1 <= length <= PEEK_MAX_LEN:
            raise ValueError(f"peek length out of range 1..{PEEK_MAX_LEN}: {length}")
        return self._op(OP_PEEK, (runtime_vaddr & MASK64, length))

    def call_runtime(self, target_runtime: int, xargs: tuple[int, ...] = ()) -> int:
        return self.call_runtime_values(target_runtime, xargs)[-1]

    def call_runtime_values(self, target_runtime: int,
                            xargs: tuple[int, ...] = (),
                            *,
                            replay_safe: bool = False) -> list[int]:
        if len(xargs) > 8:
            raise ValueError(f"too many call args (max x0..x7): {len(xargs)}")
        args = (target_runtime & MASK64, *(value & MASK64 for value in xargs))
        return self._op_values(OP_CALL, args, replay_safe=replay_safe)

    def poke_runtime(self, runtime_vaddr: int, value: int, width: int = 8) -> int:
        # Present for completeness; the v2a1 selftest never calls this.
        if width not in (4, 8):
            raise ValueError("poke width must be 4 or 8")
        return self._op(OP_POKE, (runtime_vaddr & MASK64, value & MASK64, width))


# ----------------------------------------------------------------------------
# v2a1 selftest: named peek/call proofs over the live image, cross-checked
# against the static image. Raw values never reach stdout.
# ----------------------------------------------------------------------------
def assert_jopp_entry(image: StaticImage, link_vaddr: int, name: str) -> None:
    magic = image.u32_at_vaddr(link_vaddr - 4)
    if magic != JOPP_MAGIC:
        raise ReplError(
            f"call target {name} is not a JOPP function entry "
            f"(u32(entry-4)={magic:#x}, want {JOPP_MAGIC:#x})"
        )


def _is_a64_bl(word: int) -> bool:
    return (word & A64_BL_MASK) == A64_BL


def _is_a64_ret(word: int) -> bool:
    return word == A64_RET


def _is_a64_zero_return_move(word: int) -> bool:
    return word in (A64_MOV_W0_WZR, A64_MOV_X0_XZR)


def _decode_a64_bl_target(pc: int, word: int) -> int:
    imm26 = word & 0x03FFFFFF
    if imm26 & (1 << 25):
        imm26 -= 1 << 26
    return (pc + (imm26 << 2)) & MASK64


def _decode_a64_unsigned_load(word: int) -> dict[str, int] | None:
    # LDR/LD(R)B/H unsigned-immediate. This intentionally covers only the
    # simple scalar-allocator hazard seen live: the candidate treats x0 as a
    # context pointer before any helper call can sanitize it.
    shape = word & A64_LDR_UNSIGNED_MASK
    if shape == A64_LDR64_UNSIGNED_BASE:
        width = 8
    elif shape == A64_LDR32_UNSIGNED_BASE:
        width = 4
    elif shape == A64_LDRH_UNSIGNED_BASE:
        width = 2
    elif shape == A64_LDRB_UNSIGNED_BASE:
        width = 1
    else:
        return None
    return {
        "rt": word & 0x1F,
        "rn": (word >> 5) & 0x1F,
        "width": width,
        "imm": ((word >> 10) & 0xFFF) * width,
    }


def _first_precall_x0_deref(words: list[int]) -> dict[str, int] | None:
    for index, word in enumerate(words):
        if _is_a64_bl(word) or _is_a64_ret(word):
            return None
        load = _decode_a64_unsigned_load(word)
        if load and load["rn"] == 0:
            return {"offset": index * 4, "word": word, **load}
    return None


def _nearest_symbol(symbols: dict[str, Symbol], addr: int) -> dict[str, str | int] | None:
    nearest: Symbol | None = None
    for symbol in symbols.values():
        if symbol.vaddr <= addr and (nearest is None or nearest.vaddr < symbol.vaddr):
            nearest = symbol
    if nearest is None:
        return None
    return {
        "symbol": nearest.name,
        "link_vaddr": f"0x{nearest.vaddr:x}",
        "delta": addr - nearest.vaddr,
    }


def _scan_function_shape(symbols: dict[str, Symbol],
                         image: StaticImage,
                         link_vaddr: int,
                         *,
                         scan_bytes: int = 0x100) -> dict[str, object]:
    words = image.u32_words_at_vaddr(link_vaddr, scan_bytes // 4)
    first_bl: dict[str, object] | None = None
    first_ret_offset: int | None = None
    zero_return_before_ret = False

    for index, word in enumerate(words):
        pc = link_vaddr + index * 4
        if _is_a64_bl(word):
            target = _decode_a64_bl_target(pc, word)
            first_bl = {
                "offset": index * 4,
                "word": f"0x{word:08x}",
                "target": f"0x{target:x}",
                "nearest_symbol": _nearest_symbol(symbols, target),
            }
            break
        if _is_a64_ret(word):
            first_ret_offset = index * 4
            break
        if _is_a64_zero_return_move(word):
            zero_return_before_ret = True

    return {
        "first_bl": first_bl,
        "first_ret_offset": first_ret_offset,
        "zero_return_before_first_ret_or_bl": zero_return_before_ret,
        "precall_x0_deref": _first_precall_x0_deref(words),
    }


def resolve_verified(symbols: dict[str, Symbol],
                     image: StaticImage,
                     name: str,
                     *,
                     purpose: str = "call") -> VerifiedResolution:
    """Resolve a symbol for a potentially dangerous target and attach proof.

    System.map is intentionally treated as untrusted for executable/write
    targets. The only automatic map-bypass ground truth currently accepted is
    the v2a2R' export recovery for symbols whose recovered addresses were
    independently live-proven. Other call/poke targets must pass static
    signature sanity at their map address. Read-only peeks may still use the
    map, but they are surfaced as unverified.
    """
    if purpose not in ("call", "poke", "peek"):
        raise ValueError(f"unknown resolution purpose: {purpose}")

    map_symbol = symbols.get(name)
    map_link = map_symbol.vaddr if map_symbol is not None else None
    blocked: list[str] = []
    evidence: dict[str, object] = {
        "purpose": purpose,
        "map_link_vaddr": f"0x{map_link:x}" if map_link is not None else None,
        "blocked_reasons": blocked,
    }

    if map_link is None:
        blocked.append("missing-symbol-in-System.map")
        return VerifiedResolution(name, None, False, "missing", evidence)

    if purpose == "peek":
        evidence["note"] = "read-only peek may use System.map but is not a verified call/poke target"
        return VerifiedResolution(name, map_link, False, "System.map-read-only-unverified", evidence)

    unsafe_reason = KNOWN_UNSAFE_CALL_TARGETS.get(name)
    if unsafe_reason:
        blocked.append(f"known-unsafe-live-call:{unsafe_reason}")
        return VerifiedResolution(name, map_link, False, "blocked-known-unsafe", evidence)

    raw = cached_static_raw_image(image)
    export_candidates = _recover_export_candidates_cached(raw, name)
    passing_exports: list[dict[str, object]] = []
    for candidate in export_candidates:
        bl_count = int(candidate["direct_bl_xref_count"])
        min_xrefs = MIN_ALLOCATOR_EXPORT_BL_XREFS.get(name, MIN_VERIFIED_DIRECT_BL_XREFS)
        if (
            candidate.get("jopp_entry")
            and candidate.get("precall_x0_deref") is None
            and bl_count >= min_xrefs
        ):
            passing_exports.append(candidate)

    evidence["export_candidate_count"] = len(export_candidates)
    evidence["export_passing_candidate_count"] = len(passing_exports)
    if export_candidates:
        evidence["export_candidate_sample"] = export_candidates[:3]

    if len(passing_exports) == 1:
        selected = passing_exports[0]
        selected_link = int(str(selected["link_vaddr"]), 16)
        evidence["export_selected_link_vaddr"] = selected["link_vaddr"]
        evidence["export_selected_direct_bl_xref_count"] = selected["direct_bl_xref_count"]
        evidence["map_agrees_with_export"] = selected_link == map_link
        if name in EXPORT_GROUND_TRUTH_SYMBOLS or selected_link == map_link:
            return VerifiedResolution(name, selected_link, True, "export-recovery", evidence)
        evidence["export_recovery_rejected_reason"] = (
            "disagrees-with-map-and-symbol-not-ground-truth-allowlisted"
        )
    elif len(passing_exports) > 1:
        evidence["export_recovery_rejected_reason"] = "ambiguous-export-recovery-candidates"

    try:
        magic = image.u32_at_vaddr(map_link - 4)
        shape = _scan_function_shape(symbols, image, map_link)
        bl_count, sample_sites = _count_direct_bl_xrefs_cached(raw, map_link)
    except Exception as exc:  # noqa: BLE001 - malformed map/image pairing is unverified
        blocked.append(f"static-verification-failed:{exc}")
        return VerifiedResolution(name, map_link, False, "unverified", evidence)

    evidence.update({
        "map_entry_minus_4": f"0x{magic:08x}",
        "map_jopp_entry": magic == JOPP_MAGIC,
        "map_direct_bl_xref_count": bl_count,
        "map_direct_bl_xref_sample_sites": sample_sites,
        "map_shape": shape,
    })
    if magic != JOPP_MAGIC:
        blocked.append("map-target-not-jopp-entry")
    deref = shape["precall_x0_deref"]
    if deref:
        assert isinstance(deref, dict)
        blocked.append(
            "map-target-precall-x0-deref:"
            f"+0x{deref['offset']:x}/imm=0x{deref['imm']:x}/word=0x{deref['word']:08x}"
        )
    if bl_count < MIN_VERIFIED_DIRECT_BL_XREFS:
        blocked.append(f"map-target-low-direct-bl-xrefs:{bl_count}<{MIN_VERIFIED_DIRECT_BL_XREFS}")
    if shape["first_bl"] is None:
        blocked.append("map-target-no-helper-call-before-return-or-scan-limit")
    if shape["zero_return_before_first_ret_or_bl"]:
        blocked.append("map-target-zero-return-pattern-before-first-ret-or-bl")

    if blocked:
        return VerifiedResolution(name, map_link, False, "unverified", evidence)
    return VerifiedResolution(name, map_link, True, "disasm-signature+xref+map", evidence)


def assert_no_precall_x0_pointer_deref(image: StaticImage, link_vaddr: int,
                                       name: str) -> None:
    """Reject scalar-call candidates whose entry dereferences x0 before the
    first BL. v2a2 live proved this matters: the recovered `__kmalloc` entry
    reads `[x0,#72]`, so calling it as `__kmalloc(size, flags)` faults at
    `size + 0x48` before any owned buffer exists.
    """
    deref = _first_precall_x0_deref(image.u32_words_at_vaddr(link_vaddr, 0x80 // 4))
    if deref:
        raise ReplError(
            f"{name} is not safe for scalar direct-call ABI: "
            f"entry+0x{deref['offset']:x} dereferences x0 before first BL "
            f"(word={deref['word']:#x})"
        )


def analyze_allocator_candidate(symbols: dict[str, Symbol],
                                image: StaticImage,
                                candidate: dict[str, str | None]) -> dict[str, object]:
    name = str(candidate["symbol"])
    free_symbol = candidate.get("free_symbol")
    row: dict[str, object] = {
        "symbol": name,
        "free_symbol": free_symbol,
        "expected_abi": candidate.get("expected_abi"),
        "note": candidate.get("note"),
        "status": "rejected",
        "live_ready": False,
        "blocked_reasons": [],
    }
    blocked = row["blocked_reasons"]
    assert isinstance(blocked, list)

    symbol = symbols.get(name)
    if symbol is None:
        blocked.append("missing-symbol")
        return row

    row["link_vaddr"] = f"0x{symbol.vaddr:x}"
    try:
        magic = image.u32_at_vaddr(symbol.vaddr - 4)
    except Exception as exc:  # noqa: BLE001 - report malformed image/map pairing
        blocked.append(f"static-image-read-failed:{exc}")
        return row

    row["jopp_entry"] = magic == JOPP_MAGIC
    row["entry_minus_4"] = f"0x{magic:08x}"
    if magic != JOPP_MAGIC:
        blocked.append("not-jopp-entry")

    shape = _scan_function_shape(symbols, image, symbol.vaddr)
    row.update(shape)

    deref = shape["precall_x0_deref"]
    if deref:
        assert isinstance(deref, dict)
        blocked.append(
            "precall-x0-deref:"
            f"+0x{deref['offset']:x}/imm=0x{deref['imm']:x}/word=0x{deref['word']:08x}"
        )

    if shape["first_bl"] is None:
        blocked.append("no-helper-call-before-return-or-scan-limit")

    if shape["zero_return_before_first_ret_or_bl"]:
        blocked.append("zero-return-pattern-before-first-ret-or-bl")

    manual = ALLOCATOR_KNOWN_NON_SCALAR.get(name)
    if manual:
        blocked.append(f"known-non-scalar:{manual}")

    if not blocked:
        row["status"] = "needs-manual-abi-proof"
        row["blocked_reasons"] = ["no-hard-static-blocker-but-not-auto-live-ready"]
    return row


def run_allocator_abi_audit(symbols: dict[str, Symbol],
                            image: StaticImage,
                            candidates: tuple[dict[str, str | None], ...] = ALLOCATOR_ABI_CANDIDATES
                            ) -> dict[str, object]:
    rows = [analyze_allocator_candidate(symbols, image, candidate) for candidate in candidates]
    live_ready = [row["symbol"] for row in rows if row.get("live_ready")]
    return {
        "decision": (
            "a90-repl-v2a2r-allocator-abi-audit-live-ready-candidate"
            if live_ready else "a90-repl-v2a2r-allocator-abi-audit-no-live-ready-scalar"
        ),
        "ok": True,
        "raw_runtime_values_redacted": True,
        "candidate_count": len(rows),
        "live_ready_candidates": live_ready,
        "rows": rows,
        "next_required": (
            "run bounded live poke-roundtrip only for a live_ready candidate"
            if live_ready else (
                "run allocator-export-recovery; map-labeled allocator entries may be mislabeled"
            )
        ),
    }


CALL_SENTINEL = 0xA90CA11  # recognizable arg echoed by the called printk


def run_selftest(session: ReplSession,
                 symbols: dict[str, Symbol],
                 image: StaticImage,
                 *,
                 peek_symbols: tuple[str, ...],
                 call_symbol: str = "printk") -> dict[str, object]:
    checks: list[dict[str, object]] = []
    peek_resolutions = {
        name: resolve_verified(symbols, image, name, purpose="peek")
        for name in peek_symbols
    }
    call_resolution = resolve_verified(symbols, image, call_symbol, purpose="call")
    call_link = require_verified_resolution(call_resolution, "call")
    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        # The slide is a single page-granular value; never surfaced raw.
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")

        # 1) named peek vs static image ground truth -----------------------
        for name in peek_symbols:
            peek_resolution = peek_resolutions[name]
            if peek_resolution.link_vaddr is None:
                raise ReplError(f"peek symbol {name!r} did not resolve")
            link = peek_resolution.link_vaddr
            want = image.u64_at_vaddr(link)
            got = session.peek_runtime(link + slide, 8)
            ok = got == want
            checks.append({
                "check": "named-peek",
                "symbol": name,
                "ok": ok,
                "match_static_qword": ok,
                "resolution_verified": peek_resolution.verified,
                "resolution_method": peek_resolution.method,
            })
            if not ok:
                raise ReplError(
                    f"named-peek mismatch for {name}: live qword != static image"
                )

        # 2) named call: resolve `call_symbol` (printk) from the map and call
        #    it with the stub's own "A90R%llx" format string and a sentinel.
        #    The called printk must echo the sentinel; this proves
        #    name -> map -> slide -> call dispatch with attacker-controlled args.
        #    (printk is the call target proven safe by v1-repl; kallsyms_lookup_name
        #    is deliberately *not* called here -- it faulted live.)
        format_runtime = (FORMAT_LINK_VADDR + slide) & MASK64
        values = session.call_runtime_values(
            call_link + slide,
            (format_runtime, CALL_SENTINEL),
            replay_safe=True,
        )
        sentinel_echoed = CALL_SENTINEL in values
        checks.append({
            "check": "named-call-printk",
            "call_symbol": call_symbol,
            "ok": sentinel_echoed,
            "sentinel_echoed": sentinel_echoed,
            "resolution_verified": call_resolution.verified,
            "resolution_method": call_resolution.method,
        })
        if not sentinel_echoed:
            raise ReplError(
                f"named call {call_symbol}(format, sentinel) did not echo the sentinel"
            )
    finally:
        session.set_panic_on_oops(1)

    passed = all(check["ok"] for check in checks)
    return {
        "decision": "a90-repl-v2a1-selftest-pass" if passed else "a90-repl-v2a1-selftest-fail",
        "ok": passed,
        "peek_symbols": list(peek_symbols),
        "call_symbol": call_symbol,
        "call_resolution": call_resolution.public_dict(),
        "checks": checks,
        # slide deliberately omitted from the public summary
    }


def run_poke_roundtrip(session: ReplSession,
                       symbols: dict[str, Symbol],
                       image: StaticImage,
                       *,
                       alloc_size: int = KMALLOC_ROUNDTRIP_SIZE,
                       gfp_header: Path = DEFAULT_GFP_HEADER,
                       gfp_value: int | None = None,
                       include_width32: bool = True,
                       check_allocator_abi: bool = True,
                       allocator_links: dict[str, int] | None = None,
                       allocator_source: str = "verified-resolution") -> tuple[dict[str, object], dict[str, object]]:
    """v2a2 proof: allocate owned kernel memory, poke it, peek it, free it.

    Returns `(public_summary, private_evidence)`. The public half deliberately
    omits raw slide/runtime pointer values.
    """
    checks: list[dict[str, object]] = []
    private: dict[str, object] = {}
    ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted = False
    free_ok = False
    free_error = ""

    gfp, gfp_components = (
        (gfp_value, {}) if gfp_value is not None else derive_gfp_kernel_value(gfp_header)
    )
    if gfp is None:
        raise ReplError("GFP_KERNEL derivation returned no value")

    allocator_links = allocator_links or {}
    kmalloc_resolution = resolve_verified(symbols, image, "__kmalloc", purpose="call")
    kfree_resolution = resolve_verified(symbols, image, "kfree", purpose="call")
    kmalloc_link = require_verified_resolution(kmalloc_resolution, "allocator call")
    kfree_link = require_verified_resolution(kfree_resolution, "allocator free call")
    for symbol_name, verified_link in (("__kmalloc", kmalloc_link), ("kfree", kfree_link)):
        override_link = allocator_links.get(symbol_name)
        if override_link is not None and override_link != verified_link:
            raise ReplError(
                f"allocator override for {symbol_name} does not match verified resolution "
                f"(override=0x{override_link:x}, verified=0x{verified_link:x})"
            )
    if check_allocator_abi:
        assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")

        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        ptr_ok = is_kernel_lowmem_pointer(ptr)
        checks.append({
            "check": "kmalloc-owned-buffer",
            "ok": ptr_ok,
            "non_null": ptr != 0,
            "kernel_lowmem": ptr_ok,
            "alloc_size": alloc_size,
        })
        if not ptr_ok:
            raise ReplError("__kmalloc did not return a sane kernel lowmem pointer")

        for label, sentinel in (
            ("sentinel-a", POKE_SENTINEL_A),
            ("sentinel-b", POKE_SENTINEL_B),
        ):
            session.poke_runtime(ptr, sentinel, 8)
            got = session.peek_runtime(ptr, 8)
            ok = got == sentinel
            checks.append({
                "check": "poke-peek-qword",
                "label": label,
                "ok": ok,
                "width": 8,
                "matches_written_value": ok,
            })
            if not ok:
                raise ReplError(f"{label} poke/peek mismatch")

        if include_width32:
            session.poke_runtime(ptr, POKE_SENTINEL_32, 4)
            got32 = session.peek_runtime(ptr, 8)
            expected32 = (POKE_SENTINEL_B & ~0xFFFFFFFF) | POKE_SENTINEL_32
            ok32 = got32 == expected32
            checks.append({
                "check": "poke-peek-low32",
                "ok": ok32,
                "width": 4,
                "preserved_high32": ok32,
                "matches_written_low32": ok32,
            })
            if not ok32:
                raise ReplError("32-bit poke/peek mismatch")
    finally:
        if ptr and is_kernel_lowmem_pointer(ptr) and kfree_runtime:
            free_attempted = True
            try:
                session.call_runtime(kfree_runtime, (ptr,))
                free_ok = True
            except Exception as exc:  # noqa: BLE001 - keep cleanup failure visible
                free_error = str(exc)
        session.set_panic_on_oops(1)

    if free_attempted:
        checks.append({
            "check": "kfree-owned-buffer",
            "ok": free_ok,
            "free_attempted": True,
        })
    if free_error:
        raise ReplError(f"kfree failed after round-trip: {free_error}")

    passed = all(check["ok"] for check in checks)
    summary = {
        "decision": (
            "a90-repl-v2a2-poke-roundtrip-pass"
            if passed else "a90-repl-v2a2-poke-roundtrip-fail"
        ),
        "ok": passed,
        "alloc_size": alloc_size,
        "gfp_kernel": f"0x{gfp:x}",
        "gfp_source": str(gfp_header.relative_to(REPO_ROOT)) if gfp_header.is_relative_to(REPO_ROOT) else str(gfp_header),
        "allocator_address_source": allocator_source,
        "allocator_link_vaddrs": {
            "__kmalloc": f"0x{kmalloc_link:x}",
            "kfree": f"0x{kfree_link:x}",
        },
        "allocator_resolutions": {
            "__kmalloc": kmalloc_resolution.public_dict(),
            "kfree": kfree_resolution.public_dict(),
        },
        "raw_runtime_values_redacted": True,
        "checks": checks,
    }
    private.update({
        "slide": f"0x{slide:x}",
        "alloc_ptr": f"0x{ptr:x}",
        "gfp_components": {key: f"0x{value:x}" for key, value in gfp_components.items()},
    })
    return summary, private


def _parse_read_target(symbols: dict[str, Symbol],
                       image: StaticImage,
                       target: str,
                       *,
                       runtime_addr: bool = False) -> tuple[int, dict[str, object]]:
    if runtime_addr:
        link = parse_int_auto(target)
        return link, {
            "target": target,
            "target_kind": "runtime-vaddr",
            "link_vaddr": None,
            "resolution_verified": False,
            "resolution_method": "raw-runtime-address",
        }
    try:
        link = parse_int_auto(target)
        return link, {
            "target": target,
            "target_kind": "link-vaddr",
            "link_vaddr": f"0x{link:x}",
            "resolution_verified": False,
            "resolution_method": "raw-link-address",
        }
    except argparse.ArgumentTypeError:
        resolution = resolve_verified(symbols, image, target, purpose="peek")
        if resolution.link_vaddr is None:
            raise ReplError(f"read target {target!r} did not resolve")
        return resolution.link_vaddr, {
            "target": target,
            "target_kind": "symbol",
            "link_vaddr": f"0x{resolution.link_vaddr:x}",
            "resolution_verified": resolution.verified,
            "resolution_method": resolution.method,
            "resolution": resolution.public_dict(),
        }


def read_runtime_bytes(session: ReplSession,
                       runtime_vaddr: int,
                       length: int,
                       *,
                       chunk_size: int = DEFAULT_READ_CHUNK) -> bytes:
    if length < 0:
        raise ValueError(f"read length must be non-negative: {length}")
    if not 1 <= chunk_size <= PEEK_MAX_LEN:
        raise ValueError(f"read chunk size must be 1..{PEEK_MAX_LEN}: {chunk_size}")
    out = bytearray()
    offset = 0
    while offset < length:
        this_len = min(chunk_size, length - offset)
        value = session.peek_runtime((runtime_vaddr + offset) & MASK64, this_len)
        out.extend(struct.pack("<Q", value & MASK64)[:this_len])
        offset += this_len
    return bytes(out)


def run_read(session: ReplSession,
             symbols: dict[str, Symbol],
             image: StaticImage,
             target: str,
             *,
             length: int,
             runtime_addr: bool = False,
             chunk_size: int = DEFAULT_READ_CHUNK) -> tuple[dict[str, object], dict[str, object]]:
    if length <= 0:
        raise ReplError(f"read length must be positive: {length}")
    link, target_info = _parse_read_target(symbols, image, target, runtime_addr=runtime_addr)
    private: dict[str, object] = {}
    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = 0 if runtime_addr else session.slide()
        if not runtime_addr and slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        runtime_vaddr = link if runtime_addr else (link + slide) & MASK64
        data = read_runtime_bytes(session, runtime_vaddr, length, chunk_size=chunk_size)
    finally:
        session.set_panic_on_oops(1)

    static_match = None
    if not runtime_addr:
        try:
            static_match = data == image.bytes_at_vaddr(link, length)
        except Exception:  # noqa: BLE001 - raw link may be outside the static image
            static_match = None

    chunks = (length + chunk_size - 1) // chunk_size
    summary = {
        "decision": "a90-repl-v2c-u1-read-pass",
        "ok": True,
        **target_info,
        "len": length,
        "chunk_size": chunk_size,
        "chunk_count": chunks,
        "static_image_match": static_match,
        "data_sha256": hashlib.sha256(data).hexdigest(),
        "raw_runtime_values_redacted": True,
        "data_hex_redacted": True,
    }
    private.update({
        "slide": None if runtime_addr else f"0x{slide:x}",
        "runtime_vaddr": f"0x{runtime_vaddr:x}",
        "data_hex": data.hex(),
    })
    return summary, private


def run_call(session: ReplSession,
             symbols: dict[str, Symbol],
             image: StaticImage,
             symbol: str,
             xargs: tuple[int, ...],
             *,
             replay_safe: bool = False) -> tuple[dict[str, object], dict[str, object]]:
    resolution = resolve_verified(symbols, image, symbol, purpose="call")
    link = require_verified_resolution(resolution, "call")
    private: dict[str, object] = {}
    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        values = session.call_runtime_values((link + slide) & MASK64, xargs, replay_safe=replay_safe)
    finally:
        session.set_panic_on_oops(1)

    summary = {
        "decision": "a90-repl-v2c-u1-call-pass",
        "ok": True,
        "symbol": symbol,
        "arg_count": len(xargs),
        "return_value_count": len(values),
        "resolution": resolution.public_dict(),
        "raw_runtime_values_redacted": True,
        "argument_values_redacted": True,
        "return_values_redacted": True,
        "replay_safe": replay_safe,
    }
    private.update({
        "slide": f"0x{slide:x}",
        "target_runtime": f"0x{((link + slide) & MASK64):x}",
        "args": [f"0x{value:x}" for value in xargs],
        "return_values": [f"0x{value:x}" for value in values],
    })
    return summary, private


def run_owned_poke(session: ReplSession,
                   symbols: dict[str, Symbol],
                   image: StaticImage,
                   *,
                   value: int,
                   width: int = 8,
                   alloc_size: int = KMALLOC_ROUNDTRIP_SIZE,
                   gfp_header: Path = DEFAULT_GFP_HEADER,
                   gfp_value: int | None = None) -> tuple[dict[str, object], dict[str, object]]:
    if width not in (4, 8):
        raise ReplError("poke width must be 4 or 8")
    if alloc_size < width:
        raise ReplError(f"alloc_size must be >= width ({width}): {alloc_size}")

    gfp, gfp_components = (
        (gfp_value, {}) if gfp_value is not None else derive_gfp_kernel_value(gfp_header)
    )
    if gfp is None:
        raise ReplError("GFP_KERNEL derivation returned no value")

    kmalloc_resolution = resolve_verified(symbols, image, "__kmalloc", purpose="call")
    kfree_resolution = resolve_verified(symbols, image, "kfree", purpose="call")
    kmalloc_link = require_verified_resolution(kmalloc_resolution, "allocator call")
    kfree_link = require_verified_resolution(kfree_resolution, "allocator free call")

    private: dict[str, object] = {}
    checks: list[dict[str, object]] = []
    ptr = 0
    slide = 0
    kfree_runtime = 0
    free_ok = False
    free_error = ""

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64
        ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        ptr_ok = is_kernel_lowmem_pointer(ptr)
        checks.append({
            "check": "kmalloc-owned-buffer",
            "ok": ptr_ok,
            "alloc_size": alloc_size,
            "kernel_lowmem": ptr_ok,
        })
        if not ptr_ok:
            raise ReplError("__kmalloc did not return a sane kernel lowmem pointer")

        session.poke_runtime(ptr, value, width)
        got = session.peek_runtime(ptr, width)
        expected = value & ((1 << (width * 8)) - 1)
        value_ok = got == expected
        checks.append({
            "check": "owned-buffer-poke-peek",
            "ok": value_ok,
            "width": width,
            "matches_written_value": value_ok,
        })
        if not value_ok:
            raise ReplError("owned-buffer poke/peek mismatch")
    finally:
        if ptr and is_kernel_lowmem_pointer(ptr) and kfree_runtime:
            try:
                session.call_runtime(kfree_runtime, (ptr,))
                free_ok = True
            except Exception as exc:  # noqa: BLE001 - keep cleanup failure visible
                free_error = str(exc)
        session.set_panic_on_oops(1)

    checks.append({
        "check": "kfree-owned-buffer",
        "ok": free_ok,
        "free_attempted": bool(ptr and is_kernel_lowmem_pointer(ptr) and kfree_runtime),
    })
    if free_error:
        raise ReplError(f"kfree failed after owned-buffer poke: {free_error}")

    passed = all(check["ok"] for check in checks)
    summary = {
        "decision": "a90-repl-v2c-u1-owned-poke-pass" if passed else "a90-repl-v2c-u1-owned-poke-fail",
        "ok": passed,
        "width": width,
        "alloc_size": alloc_size,
        "gfp_kernel": f"0x{gfp:x}",
        "allocator_resolutions": {
            "__kmalloc": kmalloc_resolution.public_dict(),
            "kfree": kfree_resolution.public_dict(),
        },
        "raw_runtime_values_redacted": True,
        "value_redacted": True,
        "checks": checks,
    }
    private.update({
        "slide": f"0x{slide:x}",
        "alloc_ptr": f"0x{ptr:x}",
        "value": f"0x{value:x}",
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--map", type=Path, required=True, help="System.map from a90_stock_kallsyms_extract.py")
    parser.add_argument("--image", type=Path, default=REPO_ROOT / DEFAULT_IMAGE,
                        help="static boot image matching what is flashed (v1-repl)")
    parser.add_argument("--host", default=a90ctl.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=a90ctl.DEFAULT_PORT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--dmesg-tail", type=int, default=DEFAULT_DMESG_TAIL)
    parser.add_argument("--safe-op-retries", type=int, default=2,
                        help="bounded replay count for idempotent slide/peek ops when A90R capture is noisy")
    parser.add_argument("--retry-delay-sec", type=float, default=0.2)
    parser.add_argument("--evidence-dir", type=Path, default=None,
                        help="private dir for raw evidence (kept out of git)")


def make_session(args: argparse.Namespace) -> ReplSession:
    return ReplSession(ReplConfig(
        host=args.host,
        port=args.port,
        busybox=args.busybox,
        timeout=args.timeout,
        dmesg_tail=args.dmesg_tail,
        safe_op_retries=args.safe_op_retries,
        retry_delay_sec=args.retry_delay_sec,
    ))


def write_evidence(args: argparse.Namespace, payload: dict[str, object]) -> None:
    if not args.evidence_dir:
        return
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    out = args.evidence_dir / "a90_repl_evidence.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def cmd_selftest(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    session = make_session(args)
    summary = run_selftest(
        session,
        symbols,
        image,
        peek_symbols=tuple(args.peek_symbols),
        call_symbol=args.call_symbol,
    )
    write_evidence(args, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def cmd_resolve(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    resolution = resolve_verified(symbols, image, args.symbol, purpose=args.purpose)
    print(json.dumps(resolution.public_dict(), indent=2, sort_keys=True))
    return 0


def cmd_peek(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    session = make_session(args)
    resolution = resolve_verified(symbols, image, args.symbol, purpose="peek")
    if resolution.link_vaddr is None:
        raise ReplError(f"peek symbol {args.symbol!r} did not resolve")
    link = resolution.link_vaddr
    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        got = session.peek_runtime(link + slide, args.len)
        want = image.u64_at_vaddr(link) if args.len == 8 else None
    finally:
        session.set_panic_on_oops(1)
    summary = {
        "symbol": args.symbol,
        "len": args.len,
        "resolution_verified": resolution.verified,
        "resolution_method": resolution.method,
        "matches_static_qword": (want is not None and got == want),
    }
    write_evidence(args, {**summary, "_raw_qword": f"0x{got:x}"})
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    session = make_session(args)
    summary, private = run_read(
        session,
        symbols,
        image,
        args.target,
        length=args.len,
        runtime_addr=args.runtime_addr,
        chunk_size=args.chunk_size,
    )
    write_evidence(args, {**summary, "_private": private})
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def cmd_call(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    session = make_session(args)
    summary, private = run_call(
        session,
        symbols,
        image,
        args.symbol,
        tuple(args.xargs),
        replay_safe=args.replay_safe,
    )
    write_evidence(args, {**summary, "_private": private})
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def cmd_poke(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    session = make_session(args)
    summary, private = run_owned_poke(
        session,
        symbols,
        image,
        value=args.value,
        width=args.width,
        alloc_size=args.alloc_size,
        gfp_header=args.gfp_header,
        gfp_value=args.gfp,
    )
    write_evidence(args, {**summary, "_private": private})
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def cmd_poke_roundtrip(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    session = make_session(args)
    recovery = None
    allocator_links = None
    allocator_source = "System.map"
    if args.use_recovered_allocator_exports:
        recovery = recover_allocator_export_addresses(symbols, image)
        if not recovery["ok"]:
            raise ReplError("allocator export recovery failed; refusing live poke-roundtrip")
        recovered = recovery["recovered"]
        assert isinstance(recovered, dict)
        allocator_links = {
            "__kmalloc": int(str(recovered["__kmalloc"]), 16),
            "kfree": int(str(recovered["kfree"]), 16),
        }
        allocator_source = "allocator-export-recovery"
    summary, private = run_poke_roundtrip(
        session,
        symbols,
        image,
        alloc_size=args.alloc_size,
        gfp_header=args.gfp_header,
        gfp_value=args.gfp,
        include_width32=not args.skip_width32,
        allocator_links=allocator_links,
        allocator_source=allocator_source,
    )
    payload = {**summary, "_private": private}
    if recovery is not None:
        payload["_allocator_export_recovery"] = recovery
    write_evidence(args, payload)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def cmd_allocator_audit(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    summary = run_allocator_abi_audit(symbols, image)
    write_evidence(args, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def cmd_allocator_export_recovery(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    summary = recover_allocator_export_addresses(symbols, image)
    write_evidence(args, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def cmd_map_audit(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    summary = run_map_audit(symbols, image, row_limit=args.row_limit)
    write_evidence(args, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_self = sub.add_parser("selftest", help="run the v2a1 named peek/call proof sequence")
    add_common(p_self)
    p_self.add_argument("--peek-symbols", nargs="+",
                        default=["kgsl_pwrctrl_force_no_nap_store", "__kmalloc"])
    p_self.add_argument("--call-symbol", default="printk")
    p_self.set_defaults(func=cmd_selftest)

    p_res = sub.add_parser("resolve", help="print link vaddr for a symbol (host-only)")
    p_res.add_argument("--map", type=Path, required=True)
    p_res.add_argument("--image", type=Path, default=REPO_ROOT / DEFAULT_IMAGE,
                       help="static boot image matching the map; required for verification evidence")
    p_res.add_argument("--purpose", choices=("call", "poke", "peek"), default="call")
    p_res.add_argument("symbol")
    p_res.set_defaults(func=cmd_resolve)

    p_peek = sub.add_parser("peek", help="named runtime peek of one symbol")
    add_common(p_peek)
    p_peek.add_argument("symbol")
    p_peek.add_argument("--len", type=int, default=8)
    p_peek.set_defaults(func=cmd_peek)

    p_read = sub.add_parser(
        "read",
        help="v2c U1 arbitrary-length runtime read via looped 8-byte peek ops",
    )
    add_common(p_read)
    p_read.add_argument("target", help="symbol name or link vaddr; use --runtime-addr for a runtime vaddr")
    p_read.add_argument("--len", type=int, required=True)
    p_read.add_argument("--chunk-size", type=int, default=DEFAULT_READ_CHUNK)
    p_read.add_argument("--runtime-addr", action="store_true",
                        help="interpret target as a runtime vaddr and do not apply KASLR slide")
    p_read.set_defaults(func=cmd_read)

    p_call = sub.add_parser(
        "call",
        help="v2c U1 verified named call; raw return values are private evidence only",
    )
    add_common(p_call)
    p_call.add_argument("symbol")
    p_call.add_argument("xargs", nargs="*", type=parse_int_auto, help="x0..x7 integer arguments")
    p_call.add_argument("--replay-safe", action="store_true",
                        help="allow retry on transient capture loss only for idempotent calls")
    p_call.set_defaults(func=cmd_call)

    p_poke = sub.add_parser(
        "poke",
        help="v2c U1 owned-buffer-only poke proof; never pokes an arbitrary address",
    )
    add_common(p_poke)
    p_poke.add_argument("value", type=parse_int_auto)
    p_poke.add_argument("--width", type=int, choices=(4, 8), default=8)
    p_poke.add_argument("--alloc-size", type=parse_int_auto, default=KMALLOC_ROUNDTRIP_SIZE)
    p_poke.add_argument("--gfp-header", type=Path, default=DEFAULT_GFP_HEADER)
    p_poke.add_argument("--gfp", type=parse_int_auto, default=None,
                        help="override GFP value; default derives GFP_KERNEL from --gfp-header")
    p_poke.set_defaults(func=cmd_poke)

    p_round = sub.add_parser("poke-roundtrip", help="v2a2 kmalloc-backed poke/peek/kfree proof")
    add_common(p_round)
    p_round.add_argument("--alloc-size", type=parse_int_auto, default=KMALLOC_ROUNDTRIP_SIZE)
    p_round.add_argument("--gfp-header", type=Path, default=DEFAULT_GFP_HEADER)
    p_round.add_argument("--gfp", type=parse_int_auto, default=None,
                         help="override GFP value; default derives GFP_KERNEL from --gfp-header")
    p_round.add_argument("--skip-width32", action="store_true",
                         help="skip the optional 32-bit poke path")
    p_round.add_argument("--use-recovered-allocator-exports", action="store_true",
                         help="recover ground-truth __kmalloc/kfree addresses from export string refs before live")
    p_round.set_defaults(func=cmd_poke_roundtrip)

    p_audit = sub.add_parser(
        "allocator-audit",
        help="host-only v2a2R static ABI audit for owned-buffer candidates",
    )
    add_common(p_audit)
    p_audit.set_defaults(func=cmd_allocator_audit)

    p_export = sub.add_parser(
        "allocator-export-recovery",
        help="host-only v2a2R' recovery of ground-truth __kmalloc/kfree addresses",
    )
    add_common(p_export)
    p_export.set_defaults(func=cmd_allocator_export_recovery)

    p_map_audit = sub.add_parser(
        "map-audit",
        help="host-only v2c C2 high-confidence audit of System.map trust anchors",
    )
    add_common(p_map_audit)
    p_map_audit.add_argument("--row-limit", type=int, default=80)
    p_map_audit.set_defaults(func=cmd_map_audit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
