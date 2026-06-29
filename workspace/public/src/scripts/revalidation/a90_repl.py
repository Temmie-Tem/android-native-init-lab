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
import shutil
import struct
import subprocess
import sys
import tempfile
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
DEFAULT_KERNEL_SOURCE_ROOT = (
    REPO_ROOT
    / "workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel"
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
    "printk": 1000,
}
EXPORT_GROUND_TRUTH_SYMBOLS = frozenset((*ALLOCATOR_EXPORT_REQUIRED, "printk"))
LEAF_MAP_GROUND_TRUTH_SYMBOLS = {
    "strlen": {
        "min_direct_bl_xrefs": 1000,
        "expected_pointer_args": (0,),
        "note": "non-JOPP arm64 leaf string helper; identity rests on map label, high xref count, and leaf shape",
    },
    "strcmp": {
        "min_direct_bl_xrefs": 3000,
        "expected_pointer_args": (0, 1),
        "note": "non-JOPP arm64 leaf string compare helper; identity rests on map label, high xref count, and leaf shape",
    },
    "strnlen": {
        "min_direct_bl_xrefs": 100,
        "expected_pointer_args": (0,),
        "note": "non-JOPP arm64 leaf string helper; identity rests on map label, high xref count, and leaf shape",
    },
    "memcmp": {
        "min_direct_bl_xrefs": 500,
        "expected_pointer_args": (0, 1),
        "note": "non-JOPP arm64 leaf memory compare helper; identity rests on map label, high xref count, and leaf shape",
    },
    "strrchr": {
        "min_direct_bl_xrefs": 1000,
        "expected_pointer_args": (0,),
        "note": "non-JOPP arm64 leaf reverse string search helper; identity rests on map label, high xref count, and leaf shape",
    },
    "memset": {
        "min_direct_bl_xrefs": 5000,
        "expected_pointer_args": (0,),
        "note": "non-JOPP arm64 leaf memory fill helper; identity rests on map label, high xref count, and leaf shape",
    },
}
MIN_VERIFIED_DIRECT_BL_XREFS = 1
KNOWN_UNSAFE_CALL_TARGETS = {
    "kallsyms_lookup_name": (
        "faulted/rebooted during v2a1 live validation; resolve symbols from "
        "static evidence instead of calling this target"
    ),
}
CALL_SAFETY_ALLOW_UNVETTED_TOKEN = "A90_REPL_U2_ALLOW_UNVETTED_STATIC_ONLY"
CALL_SAFETY_SAFE_SCALAR = "SAFE-SCALAR"
CALL_SAFETY_SAFE_WITH_VALID_PTR = "SAFE-WITH-VALID-PTR"
CALL_SAFETY_CONTEXT_SENSITIVE = "CONTEXT-SENSITIVE"
CALL_SAFETY_BEHAVIOR_CHANGING = "BEHAVIOR-CHANGING"
CALL_SAFETY_DENY = "DENY"
CALL_SAFETY_SAFE_TIERS = frozenset((
    CALL_SAFETY_SAFE_SCALAR,
    CALL_SAFETY_SAFE_WITH_VALID_PTR,
))
CALL_SAFETY_CONTEXT_CALL_PATTERNS = (
    "spin_lock",
    "raw_spin",
    "mutex_lock",
    "lockdep_assert",
    "rcu_",
    "might_sleep",
    "local_irq",
    "preempt_",
    "_irqsave",
    "_irqrestore",
)
CALL_SAFETY_SWEEP_FAMILIES = {
    "allocator": {
        "symbols": (
            "__kmalloc",
            "__kmalloc_node",
            "kfree",
            "ksize",
            "kmem_cache_alloc",
            "kmem_cache_free",
            "kmem_cache_alloc_trace",
            "kmem_cache_alloc_node",
            "kmem_cache_free_bulk",
            "kmem_cache_alloc_bulk",
        ),
        "prefixes": ("kmalloc_", "kfree_", "kmem_cache_"),
    },
    "string": {
        "symbols": (
            "strlen",
            "strnlen",
            "strcmp",
            "strncmp",
            "strscpy",
            "strlcpy",
            "memcpy",
            "memset",
            "memmove",
            "memcmp",
        ),
        "prefixes": ("str", "mem"),
    },
    "read-io": {
        "symbols": ("kernel_read", "kernel_write", "filp_open", "filp_close"),
        "prefixes": ("kernel_read", "kernel_write", "filp_", "vfs_"),
    },
    "refcount": {
        "symbols": (),
        "prefixes": ("refcount_", "kref_", "get_", "put_"),
    },
    "sysfs-show": {
        "symbols": (),
        "prefixes": (),
        "regexes": (r"_show$",),
    },
}
CALL_SAFETY_SEEDS = {
    "printk": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "fmt"},
        "return_kind": "int",
        "reason": "live-proven printk target; x0 must be a verified format-string pointer",
    },
    "__kmalloc": {
        "tier": CALL_SAFETY_SAFE_SCALAR,
        "required_valid_pointer_args": {},
        "return_kind": "kernel-pointer-or-null",
        "reason": "live-proven allocator entry; scalar size/gfp ABI",
    },
    "kfree": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "kmalloc-object-or-NULL"},
        "return_kind": "void",
        "reason": "cleanup call; x0 must be a verified kmalloc object pointer or NULL",
    },
    "ksize": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "kmalloc-object"},
        "return_kind": "size_t",
        "reason": "allocator-family helper; x0 must be a verified kmalloc object pointer",
    },
    "strnlen": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "string-buffer"},
        "return_kind": "size_t",
        "reason": "bounded string helper; x0 must be a verified NUL-terminated kernel buffer",
    },
    "strlen": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "string-buffer"},
        "return_kind": "size_t",
        "reason": "string helper; x0 must be a verified NUL-terminated kernel buffer",
    },
    "strcmp": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "left-string-buffer", 1: "right-string-buffer"},
        "return_kind": "int-sign",
        "reason": "string compare helper; x0/x1 must be owned NUL-terminated kernel string buffers",
    },
    "strscpy": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "destination-buffer", 1: "source-string-buffer"},
        "return_kind": "ssize_t",
        "reason": "bounded string copy helper; x0/x1 must be owned buffers and size must stay inside destination",
    },
    "strlcpy": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "destination-buffer", 1: "source-string-buffer"},
        "return_kind": "size_t",
        "reason": "bounded string copy helper; x0/x1 must be owned buffers and size must stay inside destination",
    },
    "strncpy": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "destination-buffer", 1: "source-string-buffer"},
        "return_kind": "destination-pointer",
        "reason": "bounded string copy helper; x0/x1 must be owned buffers and count must stay inside destination",
    },
    "memcmp": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "left-buffer", 1: "right-buffer"},
        "return_kind": "int-sign",
        "reason": "bounded memory compare helper; x0/x1 must be owned buffers and size must stay inside both buffers",
    },
    "strrchr": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "string-buffer"},
        "return_kind": "string-pointer-or-null",
        "reason": "reverse string search helper; x0 must be an owned NUL-terminated kernel string buffer",
    },
    "memset": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "destination-buffer"},
        "return_kind": "destination-pointer",
        "reason": "bounded memory fill helper; x0 must be an owned buffer and size must stay inside destination",
    },
    "kmem_cache_alloc": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "kmem_cache"},
        "return_kind": "kernel-pointer-or-null",
        "reason": "allocator-family helper; cache pointer must be verified",
    },
    "kmem_cache_free": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "kmem_cache", 1: "cache-object"},
        "return_kind": "void",
        "reason": "allocator-family cleanup; cache and object pointers must be verified",
    },
    "kernel_read": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "struct-file", 1: "buffer", 3: "loff_t-pos"},
        "return_kind": "ssize_t",
        "reason": "bounded read helper; file, destination buffer, and pos pointer must be verified",
    },
    "filp_open": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "pathname"},
        "return_kind": "struct-file-or-errptr",
        "reason": "file-open helper; pathname pointer must be verified and caller must close",
    },
    "filp_close": {
        "tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "required_valid_pointer_args": {0: "struct-file"},
        "return_kind": "int",
        "reason": "file cleanup helper; file pointer must be verified",
    },
    "kallsyms_lookup_name": {
        "tier": CALL_SAFETY_DENY,
        "required_valid_pointer_args": {},
        "return_kind": "kernel-address",
        "reason": "known unsafe: live call rebooted the device",
    },
    "commit_creds": {
        "tier": CALL_SAFETY_BEHAVIOR_CHANGING,
        "required_valid_pointer_args": {0: "struct-cred"},
        "return_kind": "int",
        "reason": "credential mutation; recon only, never auto-call",
    },
    "prepare_kernel_cred": {
        "tier": CALL_SAFETY_BEHAVIOR_CHANGING,
        "required_valid_pointer_args": {0: "struct-task-or-null"},
        "return_kind": "struct-cred-or-null",
        "reason": "credential construction; recon only, never chained",
    },
    "set_memory_x": {
        "tier": CALL_SAFETY_BEHAVIOR_CHANGING,
        "required_valid_pointer_args": {},
        "return_kind": "int",
        "reason": "changes kernel memory permissions; never auto-call",
    },
    "call_usermodehelper_exec": {
        "tier": CALL_SAFETY_BEHAVIOR_CHANGING,
        "required_valid_pointer_args": {0: "subprocess-info"},
        "return_kind": "int",
        "reason": "starts usermode helper; never auto-call",
    },
}
EXPORT_NAME_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_\.]{0,127}\x00")
EXPORT_RECORD_NAME_DELTA = 24
FUNCTION_SYMBOL_KINDS = frozenset("TtWw")
MAP_AUDIT_ANCHORS = ("printk", "__kmalloc", "kfree")
PRINTK_LIVE_PROOF = (
    "v2a1 named call hit a callable printk twin; C2E/Gate-2 resolves real printk by relocated export "
    "row plus maximum direct-BL xrefs"
)
KSYMTAB_ABI_AUDIT_FOCUS = ("printk", "__kmalloc", "kfree")
KSYMTAB_GROUND_TRUTH_ANCHORS = (
    "printk",
    "kgsl_pwrctrl_force_no_nap_store",
    "__kmalloc",
    "kfree",
)
C2E_EXPECTED_ANCHORS = {
    "printk": 0xFFFFFF800813ADFC,
    "kgsl_pwrctrl_force_no_nap_store": 0xFFFFFF80089273B4,
    "__kmalloc": 0xFFFFFF800826AE34,
    "kfree": 0xFFFFFF800826B354,
}
KSYMTAB_RELOCATION_RECORD_SIZE = 24
KSYMTAB_RELOCATION_FLAGS = 0x403
KSYMTAB_ROW_SIZE = 16
KSYMTAB_MIN_EXPORT_ROWS = 12000
EXPORT_C_IDENTIFIER_RE = re.compile(rb"^[A-Za-z_][A-Za-z0-9_\.]{0,127}$")

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
_DIRECT_BL_XREF_INDEX_CACHE: dict[tuple[int, int], dict[int, tuple[int, list[str]]]] = {}
_EXPORT_CANDIDATE_CACHE: dict[tuple[int, str], list[dict[str, object]]] = {}
_EXPORT_STRING_INDEX_CACHE: dict[tuple[int, tuple[str, ...]], dict[int, tuple[str, ...]]] = {}
_EXPORT_REF_INDEX_CACHE: dict[tuple[int, tuple[str, ...]], dict[str, list[int]]] = {}
_KSYMTAB_RELOCATION_CACHE: dict[tuple[int, tuple[str, ...]], dict[str, object]] = {}


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


def _direct_bl_xref_index(raw: bytes) -> dict[int, tuple[int, list[str]]]:
    key = (id(raw), len(raw))
    cached = _DIRECT_BL_XREF_INDEX_CACHE.get(key)
    if cached is not None:
        return cached

    counts: dict[int, int] = {}
    samples: dict[int, list[str]] = {}
    for off in range(0, len(raw) - 4, 4):
        word = struct.unpack_from("<I", raw, off)[0]
        if not _is_a64_bl(word):
            continue
        target = _decode_a64_bl_target(_raw_off_to_vaddr(off), word)
        counts[target] = counts.get(target, 0) + 1
        sample_sites = samples.setdefault(target, [])
        if len(sample_sites) < 8:
            sample_sites.append(f"0x{_raw_off_to_vaddr(off):x}")

    result = {
        target: (count, samples.get(target, []))
        for target, count in counts.items()
    }
    _DIRECT_BL_XREF_INDEX_CACHE[key] = result
    return result


def _count_direct_bl_xrefs_cached(raw: bytes, target_vaddr: int) -> tuple[int, list[str]]:
    key = (id(raw), target_vaddr)
    cached = _DIRECT_BL_XREF_CACHE.get(key)
    if cached is None:
        cached = _direct_bl_xref_index(raw).get(target_vaddr, (0, []))
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
    anchor_failures = [
        f"{name}:{rows.get(name, {}).get('status')} not-classified"
        for name in focus_symbols
        if name in rows and rows[name].get("status") not in ("map-match", "map-mismatch")
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


def _find_403_record_runs(raw: bytes, *, min_records: int = 20) -> list[dict[str, object]]:
    runs: list[dict[str, object]] = []
    for align in range(0, 24, 8):
        start: int | None = None
        count = 0
        for off in range(align, len(raw) - 8, 24):
            if struct.unpack_from("<Q", raw, off)[0] == 0x403:
                if start is None:
                    start = off
                    count = 1
                else:
                    count += 1
                continue
            if start is not None and count >= min_records:
                runs.append({
                    "raw_off": f"0x{start:x}",
                    "link_vaddr": f"0x{_raw_off_to_vaddr(start):x}",
                    "record_count": count,
                    "record_size": 24,
                    "flags_qword": "0x403",
                    "alignment": align,
                })
            start = None
            count = 0
        if start is not None and count >= min_records:
            runs.append({
                "raw_off": f"0x{start:x}",
                "link_vaddr": f"0x{_raw_off_to_vaddr(start):x}",
                "record_count": count,
                "record_size": 24,
                "flags_qword": "0x403",
                "alignment": align,
            })
    runs.sort(key=lambda row: (-int(row["record_count"]), int(str(row["raw_off"]), 16)))
    return runs


def _is_off_in_403_run(off: int, runs: list[dict[str, object]]) -> bool:
    for run in runs:
        start = int(str(run["raw_off"]), 16)
        end = start + int(run["record_count"]) * int(run["record_size"])
        if start <= off < end:
            return True
    return False


def _kernel_symbol_abs_pair_candidates(raw: bytes, symbol: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for string_off in _iter_exact_c_string_offsets(raw, symbol):
        string_vaddr = _raw_off_to_vaddr(string_off)
        for name_ref_off in _iter_aligned_qword_hits(raw, string_vaddr):
            if name_ref_off < 8:
                continue
            value = struct.unpack_from("<Q", raw, name_ref_off - 8)[0]
            if not _is_vaddr_inside_raw(raw, value):
                continue
            bl_count, sample_sites = _count_direct_bl_xrefs_cached(raw, value)
            rows.append({
                "record_raw_off": f"0x{name_ref_off - 8:x}",
                "record_link_vaddr": f"0x{_raw_off_to_vaddr(name_ref_off - 8):x}",
                "string_raw_off": f"0x{string_off:x}",
                "string_link_vaddr": f"0x{string_vaddr:x}",
                "name_ref_raw_off": f"0x{name_ref_off:x}",
                "value_link_vaddr": f"0x{value:x}",
                "jopp_entry": _is_static_jopp_text_entry(raw, value),
                "direct_bl_xref_count": bl_count,
                "direct_bl_xref_sample_sites": sample_sites,
            })
    return rows


def _noisy_403_symbol_candidates(raw: bytes,
                                 symbol: str,
                                 runs_403: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for string_off in _iter_exact_c_string_offsets(raw, symbol):
        string_vaddr = _raw_off_to_vaddr(string_off)
        for name_ref_off in _iter_aligned_qword_hits(raw, string_vaddr):
            if name_ref_off < 24:
                continue
            name_record_flags = struct.unpack_from("<Q", raw, name_ref_off - 8)[0]
            previous_record_value = struct.unpack_from("<Q", raw, name_ref_off - 24)[0]
            if name_record_flags != 0x403 or not _is_vaddr_inside_raw(raw, previous_record_value):
                continue
            bl_count, sample_sites = _count_direct_bl_xrefs_cached(raw, previous_record_value)
            rows.append({
                "string_raw_off": f"0x{string_off:x}",
                "string_link_vaddr": f"0x{string_vaddr:x}",
                "name_ref_raw_off": f"0x{name_ref_off:x}",
                "name_record_raw_off": f"0x{name_ref_off - 8:x}",
                "value_record_raw_off": f"0x{name_ref_off - 32:x}",
                "candidate_link_vaddr": f"0x{previous_record_value:x}",
                "candidate_jopp_entry": _is_static_jopp_text_entry(raw, previous_record_value),
                "candidate_direct_bl_xref_count": bl_count,
                "candidate_direct_bl_xref_sample_sites": sample_sites,
                "inside_403_run": (
                    _is_off_in_403_run(name_ref_off - 8, runs_403)
                    and _is_off_in_403_run(name_ref_off - 32, runs_403)
                ),
                "classification": "noisy-24-byte-0x403-record-table-not-kernel_symbol-pair",
            })
    return rows


def run_ksymtab_abi_audit(symbols: dict[str, Symbol],
                          image: StaticImage,
                          *,
                          focus_symbols: tuple[str, ...] = KSYMTAB_ABI_AUDIT_FOCUS
                          ) -> dict[str, object]:
    """Audit whether the image contains source-ABI `struct kernel_symbol` rows.

    The available kernel source defines `struct kernel_symbol` as a 16-byte
    absolute pair `{ unsigned long value; const char *name; }`. C2A's noisy
    string-ref recovery instead follows a 24-byte `0x403, pointer, aux` table.
    This audit separates those two cases so the 24-byte table is not promoted
    to broad `__ksymtab` truth.
    """
    raw = cached_static_raw_image(image)
    runs_403 = _find_403_record_runs(raw)
    rows: dict[str, dict[str, object]] = {}
    for symbol in focus_symbols:
        map_symbol = symbols.get(symbol)
        abs_pairs = _kernel_symbol_abs_pair_candidates(raw, symbol)
        noisy = _noisy_403_symbol_candidates(raw, symbol, runs_403)
        rows[symbol] = {
            "symbol": symbol,
            "map_link_vaddr": f"0x{map_symbol.vaddr:x}" if map_symbol else None,
            "absolute_kernel_symbol_pair_candidate_count": len(abs_pairs),
            "absolute_kernel_symbol_pair_candidates": abs_pairs[:8],
            "noisy_403_candidate_count": len(noisy),
            "noisy_403_candidates": noisy[:8],
            "status": (
                "no-parseable-source-abi-ksymtab-row"
                if not abs_pairs else "source-abi-ksymtab-row-present"
            ),
        }

    bad_abs_rows = [
        name for name, row in rows.items()
        if int(row["absolute_kernel_symbol_pair_candidate_count"]) != 0
    ]
    return {
        "decision": (
            "a90-repl-v2c-c2d-ksymtab-abi-audit-fenced"
            if not bad_abs_rows else "a90-repl-v2c-c2d-ksymtab-abi-audit-review"
        ),
        "ok": not bad_abs_rows,
        "raw_runtime_values_redacted": True,
        "source_abi": "struct kernel_symbol { unsigned long value; const char *name; }",
        "source_abi_record_size": 16,
        "source_reference": (
            "workspace/private/inputs/kernel_source/"
            "SM-A908N_KOR_12_Opensource/Kernel/include/linux/export.h"
        ),
        "focus_rows": rows,
        "noisy_403_table_runs": runs_403[:8],
        "noisy_403_table_total_run_count": len(runs_403),
        "conclusion": (
            "No focus anchor has a parseable 16-byte source-ABI kernel_symbol pair in the raw image. "
            "The string-ref candidates come from a large 24-byte 0x403 record table, so they remain "
            "noisy evidence unless independently verified per symbol."
        ),
        "next_required": (
            "Do not claim a broad export drift count from the 0x403 table. Keep call/poke on C1 "
            "verified resolution and high-confidence C2C rows; use semantic/independent proof for "
            "any additional symbol."
        ),
    }


def _strict_c_identifier_at_vaddr(raw: bytes, vaddr: int) -> str | None:
    raw_off = _vaddr_to_raw_off(vaddr)
    if not (0 <= raw_off < len(raw)):
        return None
    end = raw.find(b"\x00", raw_off, min(len(raw), raw_off + 160))
    if end < 0:
        return None
    text = raw[raw_off:end]
    if not text or not EXPORT_C_IDENTIFIER_RE.match(text):
        return None
    return text.decode("ascii", errors="strict")


def _zeroed_qword_pair_at_vaddr(raw: bytes, vaddr: int) -> bool:
    raw_off = _vaddr_to_raw_off(vaddr)
    if raw_off < 0 or raw_off + KSYMTAB_ROW_SIZE > len(raw):
        return False
    return (
        struct.unpack_from("<Q", raw, raw_off)[0] == 0
        and struct.unpack_from("<Q", raw, raw_off + 8)[0] == 0
    )


def _build_403_relocation_target_index(raw: bytes) -> dict[int, dict[str, object]]:
    records: dict[int, dict[str, object]] = {}
    for run in _find_403_record_runs(raw):
        start = int(str(run["raw_off"]), 16)
        count = int(run["record_count"])
        for index in range(count):
            raw_off = start + index * KSYMTAB_RELOCATION_RECORD_SIZE
            flags, value, target = struct.unpack_from("<QQQ", raw, raw_off)
            if flags != KSYMTAB_RELOCATION_FLAGS:
                continue
            records.setdefault(target, {
                "record_raw_off": raw_off,
                "value": value,
                "target": target,
            })
    return records


def _candidate_relocated_ksymtab_rows(raw: bytes,
                                      export_names: set[str]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    records = _build_403_relocation_target_index(raw)
    rows: list[dict[str, object]] = []
    for target, record in records.items():
        name_record = records.get(target + 8)
        if name_record is None:
            continue
        if not _zeroed_qword_pair_at_vaddr(raw, target):
            continue
        value = int(record["value"])
        name_vaddr = int(name_record["value"])
        if not _is_vaddr_inside_raw(raw, value):
            continue
        name = _strict_c_identifier_at_vaddr(raw, name_vaddr)
        if name is None:
            continue
        rows.append({
            "target_vaddr": target,
            "value_vaddr": value,
            "name_vaddr": name_vaddr,
            "name": name,
            "value_record_raw_off": int(record["record_raw_off"]),
            "name_record_raw_off": int(name_record["record_raw_off"]),
            "jopp_entry": _is_static_jopp_text_entry(raw, value),
            "has_export_label": name in export_names,
        })
    rows.sort(key=lambda row: (int(row["target_vaddr"]), str(row["name"])))

    runs: list[dict[str, object]] = []
    current: list[dict[str, object]] = []
    last_target: int | None = None
    for row in rows:
        target = int(row["target_vaddr"])
        if last_target is None or target == last_target + KSYMTAB_ROW_SIZE:
            current.append(row)
        else:
            if current:
                runs.append(_summarize_ksymtab_candidate_run(current))
            current = [row]
        last_target = target
    if current:
        runs.append(_summarize_ksymtab_candidate_run(current))
    return rows, runs


def _summarize_ksymtab_candidate_run(rows: list[dict[str, object]]) -> dict[str, object]:
    export_count = sum(1 for row in rows if row["has_export_label"])
    jopp_count = sum(1 for row in rows if row["jopp_entry"])
    name_raw_offsets = [
        _vaddr_to_raw_off(int(row["name_vaddr"]))
        for row in rows
    ]
    return {
        "start_vaddr": int(rows[0]["target_vaddr"]),
        "end_vaddr": int(rows[-1]["target_vaddr"]),
        "row_count": len(rows),
        "export_label_count": export_count,
        "export_label_density": export_count / len(rows),
        "jopp_entry_count": jopp_count,
        "name_raw_min": min(name_raw_offsets),
        "name_raw_max": max(name_raw_offsets),
        "first_name": rows[0]["name"],
        "last_name": rows[-1]["name"],
    }


def _locate_relocated_ksymtab_rows(raw: bytes,
                                   export_names: set[str]) -> dict[str, object]:
    cache_key = (id(raw), tuple(sorted(export_names)))
    cached = _KSYMTAB_RELOCATION_CACHE.get(cache_key)
    if cached is not None:
        return cached

    candidates, runs = _candidate_relocated_ksymtab_rows(raw, export_names)
    selected_runs = [
        run for run in runs
        if (
            int(run["row_count"]) >= 10
            and float(run["export_label_density"]) >= 0.95
        )
    ]
    if not selected_runs:
        result = {
            "ok": False,
            "rows": [],
            "runs": runs,
            "selected_runs": [],
            "blocked_reasons": ["no-high-density-export-label-relocation-runs"],
        }
        _KSYMTAB_RELOCATION_CACHE[cache_key] = result
        return result

    start_vaddr = min(int(run["start_vaddr"]) for run in selected_runs)
    end_vaddr = max(int(run["end_vaddr"]) for run in selected_runs)
    selected_rows = [
        row for row in candidates
        if (
            start_vaddr <= int(row["target_vaddr"]) <= end_vaddr
            and bool(row["has_export_label"])
        )
    ]
    selected_rows.sort(key=lambda row: (int(row["target_vaddr"]), str(row["name"])))
    by_name: dict[str, dict[str, object]] = {}
    duplicate_names: dict[str, int] = {}
    for row in selected_rows:
        name = str(row["name"])
        if name in by_name:
            duplicate_names[name] = duplicate_names.get(name, 1) + 1
            continue
        by_name[name] = row

    name_raw_offsets = [
        _vaddr_to_raw_off(int(row["name_vaddr"]))
        for row in selected_rows
    ]
    result = {
        "ok": len(selected_rows) >= KSYMTAB_MIN_EXPORT_ROWS and not duplicate_names,
        "rows": selected_rows,
        "by_name": by_name,
        "runs": runs,
        "selected_runs": selected_runs,
        "target_start_vaddr": start_vaddr,
        "target_end_vaddr": end_vaddr,
        "name_raw_min": min(name_raw_offsets) if name_raw_offsets else None,
        "name_raw_max": max(name_raw_offsets) if name_raw_offsets else None,
        "duplicate_names": duplicate_names,
        "blocked_reasons": [] if len(selected_rows) >= KSYMTAB_MIN_EXPORT_ROWS else [
            f"selected-export-row-count:{len(selected_rows)}<{KSYMTAB_MIN_EXPORT_ROWS}"
        ],
    }
    _KSYMTAB_RELOCATION_CACHE[cache_key] = result
    return result


def _public_relocated_ksymtab_row(row: dict[str, object] | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {
        "name": row["name"],
        "target_vaddr": f"0x{int(row['target_vaddr']):x}",
        "value_vaddr": f"0x{int(row['value_vaddr']):x}",
        "name_vaddr": f"0x{int(row['name_vaddr']):x}",
        "value_record_raw_off": f"0x{int(row['value_record_raw_off']):x}",
        "name_record_raw_off": f"0x{int(row['name_record_raw_off']):x}",
        "jopp_entry": row["jopp_entry"],
    }


def _public_ksymtab_run(run: dict[str, object]) -> dict[str, object]:
    return {
        "start_vaddr": f"0x{int(run['start_vaddr']):x}",
        "end_vaddr": f"0x{int(run['end_vaddr']):x}",
        "row_count": run["row_count"],
        "export_label_count": run["export_label_count"],
        "export_label_density": run["export_label_density"],
        "jopp_entry_count": run["jopp_entry_count"],
        "name_raw_min": f"0x{int(run['name_raw_min']):x}",
        "name_raw_max": f"0x{int(run['name_raw_max']):x}",
        "first_name": run["first_name"],
        "last_name": run["last_name"],
    }


def _summarize_ksymtab_drift(rows: list[dict[str, object]],
                             symbols: dict[str, Symbol],
                             *,
                             sample_limit: int = 12) -> dict[str, object]:
    counts = {
        "map_match": 0,
        "map_mismatch": 0,
        "missing_map_symbol": 0,
    }
    samples: list[dict[str, object]] = []
    mismatch_buckets: dict[str, int] = {}
    for row in rows:
        name = str(row["name"])
        truth = int(row["value_vaddr"])
        symbol = symbols.get(name)
        if symbol is None:
            counts["missing_map_symbol"] += 1
            if len(samples) < sample_limit:
                samples.append({
                    "symbol": name,
                    "status": "missing-map-symbol",
                    "truth_link_vaddr": f"0x{truth:x}",
                })
            continue
        if symbol.vaddr == truth:
            counts["map_match"] += 1
            continue
        counts["map_mismatch"] += 1
        bucket = f"0x{symbol.vaddr & ~0xfffff:x}"
        mismatch_buckets[bucket] = mismatch_buckets.get(bucket, 0) + 1
        if len(samples) < sample_limit:
            samples.append({
                "symbol": name,
                "status": "map-mismatch",
                "truth_link_vaddr": f"0x{truth:x}",
                "map_link_vaddr": f"0x{symbol.vaddr:x}",
                "map_minus_truth": symbol.vaddr - truth,
                "kind": symbol.kind,
            })
    total = len(rows)
    return {
        "audited_symbol_count": total,
        "counts": counts,
        "map_match_rate": counts["map_match"] / total if total else 0,
        "mismatch_region_buckets": [
            {"map_region_base": bucket, "mismatch_count": count}
            for bucket, count in sorted(
                mismatch_buckets.items(), key=lambda item: (-item[1], item[0])
            )[:20]
        ],
        "sample_rows": samples,
    }


def _ksymtab_anchor_results(symbols: dict[str, Symbol],
                            image: StaticImage,
                            by_name: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    results: dict[str, dict[str, object]] = {}
    for name in KSYMTAB_GROUND_TRUTH_ANCHORS:
        expected = C2E_EXPECTED_ANCHORS[name]
        map_symbol = symbols.get(name)
        row = by_name.get(name)
        result: dict[str, object] = {
            "symbol": name,
            "expected_link_vaddr": f"0x{expected:x}",
            "map_link_vaddr": f"0x{map_symbol.vaddr:x}" if map_symbol else None,
            "ksymtab_row": _public_relocated_ksymtab_row(row),
            "status": "unknown",
            "method": "relocated-ksymtab",
        }
        if name in ("__kmalloc", "kfree"):
            truth = int(row["value_vaddr"]) if row else None
            result["truth_link_vaddr"] = f"0x{truth:x}" if truth is not None else None
            result["status"] = "anchor-match" if truth == expected else "anchor-fail"
        elif name == "printk":
            semantic = _stage_c_printk_link_vaddr(image)
            export_truth = int(row["value_vaddr"]) if row else None
            status = "anchor-match" if semantic == expected and export_truth == semantic else "anchor-fail"
            if semantic == expected and export_truth is not None and export_truth != semantic:
                status = "anchor-match-export-conflict"
            result.update({
                "method": "semantic-xref-anchor-plus-relocated-ksymtab",
                "truth_link_vaddr": f"0x{semantic:x}",
                "semantic_link_vaddr": f"0x{semantic:x}",
                "export_row_link_vaddr": f"0x{export_truth:x}" if export_truth is not None else None,
                "export_row_conflicts_with_semantic_anchor": export_truth != semantic,
                "status": status,
            })
        elif name == "kgsl_pwrctrl_force_no_nap_store":
            result.update({
                "method": "non-exported-semantic-map-anchor",
                "truth_link_vaddr": f"0x{map_symbol.vaddr:x}" if map_symbol else None,
                "ksymtab_scope": "not-exported",
                "status": "anchor-match" if map_symbol and map_symbol.vaddr == expected else "anchor-fail",
            })
        results[name] = result
    return results


def run_ksymtab_ground_truth_audit(
    symbols: dict[str, Symbol],
    image: StaticImage,
    *,
    compare_symbol_maps: dict[str, dict[str, Symbol]] | None = None,
) -> dict[str, object]:
    raw = cached_static_raw_image(image)
    export_names = set(exported_symbol_names(symbols))
    located = _locate_relocated_ksymtab_rows(raw, export_names)
    rows = list(located.get("rows", []))
    by_name = dict(located.get("by_name", {}))
    anchor_results = _ksymtab_anchor_results(symbols, image, by_name)
    anchor_failures = [
        f"{name}:{row['status']}"
        for name, row in anchor_results.items()
        if not str(row["status"]).startswith("anchor-match")
    ]
    current_drift = _summarize_ksymtab_drift(rows, symbols)
    compare_maps: dict[str, object] = {}
    for label, compare_symbols in (compare_symbol_maps or {}).items():
        compare_maps[label] = _summarize_ksymtab_drift(rows, compare_symbols)

    selected_runs = list(located.get("selected_runs", []))
    ok = bool(located.get("ok")) and not anchor_failures
    return {
        "decision": (
            "a90-repl-v2c-c2e-ksymtab-ground-truth-oracle-host-pass"
            if ok else "a90-repl-v2c-c2e-ksymtab-ground-truth-oracle-review"
        ),
        "ok": ok,
        "raw_runtime_values_redacted": True,
        "oracle": {
            "layout": "24-byte-0x403-relocation-records-reconstruct-zeroed-16-byte-ksymtab-pairs",
            "source_row_abi": "struct kernel_symbol { unsigned long value; const char *name; }",
            "relocation_record_size": KSYMTAB_RELOCATION_RECORD_SIZE,
            "relocation_flags": f"0x{KSYMTAB_RELOCATION_FLAGS:x}",
            "selected_export_row_count": len(rows),
            "selected_unique_name_count": len(by_name),
            "target_start_vaddr": (
                f"0x{int(located['target_start_vaddr']):x}" if located.get("target_start_vaddr") else None
            ),
            "target_end_vaddr": (
                f"0x{int(located['target_end_vaddr']):x}" if located.get("target_end_vaddr") else None
            ),
            "name_raw_min": (
                f"0x{int(located['name_raw_min']):x}" if located.get("name_raw_min") is not None else None
            ),
            "name_raw_max": (
                f"0x{int(located['name_raw_max']):x}" if located.get("name_raw_max") is not None else None
            ),
            "selected_run_count": len(selected_runs),
            "selected_run_samples": [_public_ksymtab_run(run) for run in selected_runs[:8]],
            "blocked_reasons": located.get("blocked_reasons", []),
        },
        "anchor_results": anchor_results,
        "anchor_failures": anchor_failures,
        "current_map_drift": current_drift,
        "compare_map_drift": compare_maps,
        "decoder_divergence": {
            "current_map": (
                "current v2a1 System.map is index-drifted for the relocated ksymtab export scope; "
                "the audited export rows have zero direct matches"
            ),
            "localized_root_cause": (
                "the previously generated C2B padding-fix map is validated by this structural oracle "
                "when supplied as a compare map: it corrects the 95-entry offsets drift for nearly all "
                "relocated export rows"
            ),
            "semantic_conflicts": (
                "Gate-2 fixes the printk twin bug by selecting the relocated export row / highest direct-BL "
                "xref candidate; older v2a1 live proof hit a callable lower-xref twin"
            ),
        },
        "decoder_root_fix_decision": (
            "promote the C2B padding fix plus printk-xref disambiguation; keep C1 fail-closed and fence "
            "remaining residuals until operator-disasm-verified"
        ),
        "trust_policy": (
            "exported symbols inside the relocated ksymtab scope may use this oracle for drift reports; "
            "live call/poke targets still require C1 verified resolution; non-exported symbols remain "
            "map-only and verified=false unless separately proven"
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
                     purpose: str = "call",
                     allow_pre_arg_deref: bool = False) -> VerifiedResolution:
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
        "allow_pre_arg_deref": allow_pre_arg_deref,
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
            and (allow_pre_arg_deref or candidate.get("precall_x0_deref") is None)
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
    leaf_truth = LEAF_MAP_GROUND_TRUTH_SYMBOLS.get(name)
    if purpose == "call" and leaf_truth is not None:
        leaf_blocked: list[str] = []
        min_leaf_xrefs = int(leaf_truth["min_direct_bl_xrefs"])
        if not _map_kind_is_function(map_symbol.kind if map_symbol else None):
            leaf_blocked.append("leaf-map-target-not-function-kind")
        if shape["first_bl"] is not None:
            leaf_blocked.append("leaf-map-target-has-helper-call")
        if shape["first_ret_offset"] is None:
            leaf_blocked.append("leaf-map-target-no-ret-in-scan")
        if shape["zero_return_before_first_ret_or_bl"]:
            leaf_blocked.append("leaf-map-target-zero-return-pattern-before-ret")
        if bl_count < min_leaf_xrefs:
            leaf_blocked.append(f"leaf-map-target-low-direct-bl-xrefs:{bl_count}<{min_leaf_xrefs}")
        if not leaf_blocked:
            evidence["leaf_map_ground_truth"] = {
                "accepted": True,
                "min_direct_bl_xrefs": min_leaf_xrefs,
                "note": leaf_truth["note"],
            }
            return VerifiedResolution(name, map_link, True, "leaf-map-disasm+xref", evidence)
        evidence["leaf_map_rejected_reasons"] = leaf_blocked

    if magic != JOPP_MAGIC:
        blocked.append("map-target-not-jopp-entry")
    deref = shape["precall_x0_deref"]
    if deref and not allow_pre_arg_deref:
        assert isinstance(deref, dict)
        blocked.append(
            "map-target-precall-x0-deref:"
            f"+0x{deref['offset']:x}/imm=0x{deref['imm']:x}/word=0x{deref['word']:08x}"
        )
    elif deref:
        evidence["map_target_pre_arg_deref_allowed"] = True
    if bl_count < MIN_VERIFIED_DIRECT_BL_XREFS:
        blocked.append(f"map-target-low-direct-bl-xrefs:{bl_count}<{MIN_VERIFIED_DIRECT_BL_XREFS}")
    if shape["first_bl"] is None:
        blocked.append("map-target-no-helper-call-before-return-or-scan-limit")
    if shape["zero_return_before_first_ret_or_bl"]:
        blocked.append("map-target-zero-return-pattern-before-first-ret-or-bl")

    if blocked:
        return VerifiedResolution(name, map_link, False, "unverified", evidence)
    return VerifiedResolution(name, map_link, True, "disasm-signature+xref+map", evidence)


def _first_precall_arg_derefs(words: list[int]) -> list[dict[str, int]]:
    derefs: list[dict[str, int]] = []
    for index, word in enumerate(words):
        if _is_a64_bl(word) or _is_a64_ret(word):
            return derefs
        load = _decode_a64_unsigned_load(word)
        if load and 0 <= load["rn"] <= 7:
            derefs.append({"offset": index * 4, "word": word, "arg_reg": load["rn"], **load})
    return derefs


def _objdump_function_excerpt(image: StaticImage,
                              link_vaddr: int,
                              *,
                              byte_count: int = 0x100,
                              max_lines: int = 40) -> dict[str, object]:
    tool = shutil.which("aarch64-linux-gnu-objdump")
    if tool is None:
        return {
            "available": False,
            "tool": "aarch64-linux-gnu-objdump",
            "reason": "tool-not-found",
        }
    try:
        code = image.bytes_at_vaddr(link_vaddr, byte_count)
    except Exception as exc:  # noqa: BLE001 - classify should keep going with word evidence
        return {
            "available": False,
            "tool": tool,
            "reason": f"bytes-unavailable:{exc}",
        }
    with tempfile.NamedTemporaryFile(prefix="a90-repl-disasm-", suffix=".bin") as tmp:
        tmp.write(code)
        tmp.flush()
        result = subprocess.run(
            [
                tool,
                "-D",
                "-b",
                "binary",
                "-m",
                "aarch64",
                f"--adjust-vma=0x{link_vaddr:x}",
                tmp.name,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
    if result.returncode != 0:
        return {
            "available": False,
            "tool": tool,
            "returncode": result.returncode,
            "stderr_tail": result.stderr[-400:],
        }
    lines = [
        line.rstrip()
        for line in result.stdout.splitlines()
        if line.strip() and "file format binary" not in line
    ]
    return {
        "available": True,
        "tool": tool,
        "adjust_vma": f"0x{link_vaddr:x}",
        "line_count": len(lines),
        "lines": lines[:max_lines],
        "truncated": len(lines) > max_lines,
    }


def _function_scan_byte_count(symbols: dict[str, Symbol],
                              link_vaddr: int,
                              *,
                              max_scan_bytes: int = 0x1000) -> int:
    next_vaddr = min(
        (
            symbol.vaddr
            for symbol in symbols.values()
            if symbol.vaddr > link_vaddr and _map_kind_is_function(symbol.kind)
        ),
        default=None,
    )
    if next_vaddr is None:
        return max_scan_bytes
    return max(0x40, min(max_scan_bytes, next_vaddr - link_vaddr))


def _reg_num(text: str) -> int | None:
    text = text.strip().lower()
    if text in ("sp", "xzr", "wzr"):
        return None
    match = re.fullmatch(r"[xw]([0-2]?\d|3[01])", text)
    if not match:
        return None
    value = int(match.group(1))
    return value if 0 <= value <= 30 else None


def _regs_in_text(text: str) -> list[int]:
    regs: list[int] = []
    for match in re.finditer(r"\b([xw](?:[0-2]?\d|3[01])|sp|xzr|wzr)\b", text.lower()):
        reg = _reg_num(match.group(1))
        if reg is not None:
            regs.append(reg)
    return regs


def _split_first_operand(operands: str) -> tuple[str, str]:
    if "," not in operands:
        return operands.strip(), ""
    first, rest = operands.split(",", 1)
    return first.strip(), rest.strip()


def _parse_objdump_instruction(line: str) -> dict[str, object] | None:
    match = re.match(
        r"^\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{8})\s+([A-Za-z0-9_.]+)\s*(.*)$",
        line,
    )
    if not match:
        return None
    operands = match.group(4).split("//", 1)[0].strip()
    return {
        "pc": int(match.group(1), 16),
        "word": match.group(2).lower(),
        "mnemonic": match.group(3).lower(),
        "operands": operands,
        "line": line,
    }


def _is_load_mnemonic(mnemonic: str) -> bool:
    return mnemonic.startswith(("ldr", "ldur", "ldp", "ldxp", "ldax", "ldar"))


def _dest_regs_before_memory_operand(operands: str) -> list[int]:
    before_mem = operands.split("[", 1)[0]
    return _regs_in_text(before_mem)


def _call_safety_arg_taint_flow(symbols: dict[str, Symbol],
                                image: StaticImage,
                                link_vaddr: int,
                                *,
                                scan_bytes: int) -> dict[str, object]:
    disasm = _objdump_function_excerpt(
        image,
        link_vaddr,
        byte_count=scan_bytes,
        max_lines=900,
    )
    if not disasm.get("available"):
        return {
            "available": False,
            "safe_scalar_positive_no_arg_memory_base_flow": False,
            "reason": disasm,
        }

    taint: dict[int, set[int]] = {index: {index} for index in range(8)}
    memory_base_uses: list[dict[str, object]] = []
    tainted_arg_calls: list[dict[str, object]] = []
    propagation_sample: list[dict[str, object]] = []

    for line in disasm.get("lines", []):
        parsed = _parse_objdump_instruction(str(line))
        if parsed is None:
            continue
        mnemonic = str(parsed["mnemonic"])
        operands = str(parsed["operands"])

        for base_text in re.findall(r"\[([xw](?:[0-2]?\d|3[01])|sp)\b", operands.lower()):
            base = _reg_num(base_text)
            if base is not None and base in taint:
                memory_base_uses.append({
                    "pc": f"0x{int(parsed['pc']):x}",
                    "word": f"0x{parsed['word']}",
                    "mnemonic": mnemonic,
                    "base_reg": f"x{base}",
                    "source_args": [f"x{arg}" for arg in sorted(taint[base])],
                    "line": line,
                })

        if mnemonic == "bl":
            tainted_args = {
                f"x{index}": [f"x{arg}" for arg in sorted(taint[index])]
                for index in range(8)
                if index in taint
            }
            if tainted_args and len(tainted_arg_calls) < 16:
                tainted_arg_calls.append({
                    "pc": f"0x{int(parsed['pc']):x}",
                    "line": line,
                    "tainted_args": tainted_args,
                })
            # A direct call overwrites caller-clobbered registers. Keep
            # callee-saved aliases such as kfree's x22 <- x0.
            for reg in range(19):
                taint.pop(reg, None)
            continue

        if "[" in operands:
            if _is_load_mnemonic(mnemonic):
                base_match = re.search(r"\[([xw](?:[0-2]?\d|3[01])|sp)\b", operands.lower())
                base = _reg_num(base_match.group(1)) if base_match else None
                base_taint = set(taint.get(base, set())) if base is not None else set()
                for dest in _dest_regs_before_memory_operand(operands):
                    if dest == 31:
                        continue
                    if base_taint:
                        taint[dest] = set(base_taint)
                    else:
                        taint.pop(dest, None)
            continue

        dest_text, rest = _split_first_operand(operands)
        dest = _reg_num(dest_text)
        if dest is None:
            continue

        source_regs = _regs_in_text(rest)
        source_taint: set[int] = set()
        for reg in source_regs:
            source_taint.update(taint.get(reg, set()))

        if mnemonic in {
            "mov",
            "add",
            "sub",
            "orr",
            "and",
            "eor",
            "bic",
            "lsl",
            "lsr",
            "asr",
            "sxtw",
            "uxtw",
            "ubfx",
            "sbfx",
            "csel",
            "csinc",
            "csinv",
            "csneg",
        }:
            if source_taint:
                taint[dest] = source_taint
                if len(propagation_sample) < 24:
                    propagation_sample.append({
                        "pc": f"0x{int(parsed['pc']):x}",
                        "dest": f"x{dest}",
                        "source_args": [f"x{arg}" for arg in sorted(source_taint)],
                        "line": line,
                    })
            else:
                taint.pop(dest, None)
        elif mnemonic in {"adr", "adrp", "mrs", "movz", "movn"}:
            taint.pop(dest, None)

    final_taint = {
        f"x{reg}": [f"x{arg}" for arg in sorted(args)]
        for reg, args in sorted(taint.items())
    }
    return {
        "available": True,
        "scan_bytes": scan_bytes,
        "safe_scalar_positive_no_arg_memory_base_flow": not memory_base_uses,
        "arg_memory_base_use_count": len(memory_base_uses),
        "arg_memory_base_uses": memory_base_uses[:16],
        "tainted_arg_call_count": len(tainted_arg_calls),
        "tainted_arg_calls_sample": tainted_arg_calls,
        "propagation_sample": propagation_sample,
        "final_tainted_regs": final_taint,
    }


def _call_safety_static_signals(symbols: dict[str, Symbol],
                                image: StaticImage,
                                link_vaddr: int,
                                *,
                                scan_bytes: int | None = None,
                                include_objdump: bool = True) -> dict[str, object]:
    raw = cached_static_raw_image(image)
    scan_bytes = scan_bytes or _function_scan_byte_count(symbols, link_vaddr)
    words = image.u32_words_at_vaddr(link_vaddr, scan_bytes // 4)
    bl_targets: list[dict[str, object]] = []
    ret_offsets: list[int] = []
    for index, word in enumerate(words):
        pc = link_vaddr + index * 4
        if _is_a64_bl(word):
            target = _decode_a64_bl_target(pc, word)
            bl_targets.append({
                "offset": index * 4,
                "word": f"0x{word:08x}",
                "target": f"0x{target:x}",
                "nearest_symbol": _nearest_symbol(symbols, target),
            })
        elif _is_a64_ret(word):
            ret_offsets.append(index * 4)

    context_calls: list[dict[str, object]] = []
    for call in bl_targets:
        nearest = call.get("nearest_symbol")
        nearest_name = str(nearest.get("symbol")) if isinstance(nearest, dict) else ""
        if any(pattern in nearest_name for pattern in CALL_SAFETY_CONTEXT_CALL_PATTERNS):
            context_calls.append(call)

    try:
        printk_resolution = resolve_verified(symbols, image, "printk", purpose="call")
        printk_link = require_verified_resolution(printk_resolution, "call-safety-printk-prologue")
        printk_words = image.u32_words_at_vaddr(printk_link, 0x20 // 4)
        variadic_prologue = words[: len(printk_words)] == printk_words
    except Exception:
        printk_link = None
        variadic_prologue = False

    bl_count, sample_sites = _count_direct_bl_xrefs_cached(raw, link_vaddr)
    signals: dict[str, object] = {
        "scan_bytes": scan_bytes,
        "first_words": [f"0x{word:08x}" for word in words[:12]],
        "jopp_entry": image.u32_at_vaddr(link_vaddr - 4) == JOPP_MAGIC,
        "direct_bl_xref_count": bl_count,
        "direct_bl_xref_sample_sites": sample_sites,
        "arg_pointer_derefs_before_first_bl_or_ret": [
            {
                **{key: value for key, value in row.items() if key != "word"},
                "word": f"0x{row['word']:08x}",
                "arg": f"x{row['arg_reg']}",
            }
            for row in _first_precall_arg_derefs(words)
        ],
        "bl_count_in_scan": len(bl_targets),
        "leaf": len(bl_targets) == 0,
        "bl_targets_sample": bl_targets[:12],
        "context_call_count": len(context_calls),
        "context_calls_sample": context_calls[:8],
        "ret_offsets_sample": [f"0x{offset:x}" for offset in ret_offsets[:8]],
        "variadic_prologue_matches_printk": variadic_prologue,
        "printk_prologue_link_vaddr": f"0x{printk_link:x}" if printk_link is not None else None,
        "arg_taint_flow": _call_safety_arg_taint_flow(
            symbols,
            image,
            link_vaddr,
            scan_bytes=scan_bytes,
        ),
    }
    if include_objdump:
        signals["objdump"] = _objdump_function_excerpt(image, link_vaddr, byte_count=scan_bytes)
    return signals


def classify_call_safety(symbols: dict[str, Symbol],
                         image: StaticImage,
                         name: str,
                         *,
                         include_objdump: bool = True) -> dict[str, object]:
    seed = CALL_SAFETY_SEEDS.get(name)
    seed_required_ptrs = dict(seed.get("required_valid_pointer_args", {})) if seed else {}
    resolution = resolve_verified(
        symbols,
        image,
        name,
        purpose="call",
        allow_pre_arg_deref=bool(seed_required_ptrs),
    )
    link = resolution.link_vaddr
    tier = CALL_SAFETY_DENY
    reasons: list[str] = []
    warnings: list[str] = []

    if seed:
        tier = str(seed["tier"])
        reasons.append(f"seed:{seed['reason']}")
    else:
        reasons.append("deny-by-default:not-in-vetted-seed-whitelist")

    if name in KNOWN_UNSAFE_CALL_TARGETS:
        tier = CALL_SAFETY_DENY
        reasons.append(f"known-unsafe-live-call:{KNOWN_UNSAFE_CALL_TARGETS[name]}")

    behavior_prefixes = (
        "commit_creds",
        "prepare_kernel_cred",
        "set_memory_",
        "call_usermodehelper",
    )
    if name.startswith(behavior_prefixes):
        tier = CALL_SAFETY_BEHAVIOR_CHANGING
        reasons.append("behavior-changing-name-family")

    signals: dict[str, object] = {}
    if link is not None:
        try:
            signals = _call_safety_static_signals(
                symbols,
                image,
                link,
                include_objdump=include_objdump,
            )
        except Exception as exc:  # noqa: BLE001 - evidence-backed deny beats crashing classification
            warnings.append(f"static-signal-scan-failed:{exc}")
            if tier in CALL_SAFETY_SAFE_TIERS:
                tier = CALL_SAFETY_DENY
                reasons.append("static-signal-scan-failed-for-safe-seed")

    if not resolution.verified and tier in CALL_SAFETY_SAFE_TIERS:
        tier = CALL_SAFETY_DENY
        reasons.append("identity-not-c1-verified")

    arg_derefs = signals.get("arg_pointer_derefs_before_first_bl_or_ret", [])
    required_ptrs = seed_required_ptrs
    if tier == CALL_SAFETY_SAFE_SCALAR and required_ptrs:
        tier = CALL_SAFETY_DENY
        reasons.append("pointer-typed-args-never-safe-scalar")
    if tier == CALL_SAFETY_SAFE_SCALAR and arg_derefs:
        tier = CALL_SAFETY_DENY
        reasons.append("safe-scalar-contradicted-by-early-arg-pointer-deref")
    arg_taint_flow = signals.get("arg_taint_flow", {})
    if tier == CALL_SAFETY_SAFE_SCALAR:
        if not isinstance(arg_taint_flow, dict) or not arg_taint_flow.get("available"):
            tier = CALL_SAFETY_DENY
            reasons.append("safe-scalar-missing-positive-arg-taint-flow-proof")
        elif not arg_taint_flow.get("safe_scalar_positive_no_arg_memory_base_flow"):
            tier = CALL_SAFETY_DENY
            reasons.append("safe-scalar-contradicted-by-arg-taint-memory-base-flow")
    if tier == CALL_SAFETY_SAFE_WITH_VALID_PTR and arg_derefs:
        deref_regs = {
            int(str(row["arg"])[1:])
            for row in arg_derefs
            if isinstance(row, dict) and str(row.get("arg", "")).startswith("x")
        }
        missing = sorted(deref_regs - set(required_ptrs))
        if missing:
            tier = CALL_SAFETY_DENY
            reasons.append(
                "valid-pointer-seed-missing-required-deref-args:"
                + ",".join(f"x{reg}" for reg in missing)
            )

    context_count = int(signals.get("context_call_count", 0) or 0)
    if tier in CALL_SAFETY_SAFE_TIERS and context_count:
        warnings.append("context-sensitive-locking-or-sleep-call-in-scan")
        if seed is None:
            tier = CALL_SAFETY_CONTEXT_SENSITIVE
            reasons.append("context-sensitive-locking-or-sleep-call-in-scan")

    if signals.get("variadic_prologue_matches_printk") and name != "printk":
        warnings.append("variadic-prologue-matches-printk-twin-shape")
        if tier in CALL_SAFETY_SAFE_TIERS:
            tier = CALL_SAFETY_DENY
            reasons.append("printk-twin-variadic-prologue-risk")

    auto_call_allowed = tier == CALL_SAFETY_SAFE_SCALAR
    if tier == CALL_SAFETY_SAFE_WITH_VALID_PTR:
        auto_call_allowed = bool(required_ptrs)

    return {
        "symbol": name,
        "tier": tier,
        "safe_group": tier in CALL_SAFETY_SAFE_TIERS,
        "auto_call_allowed": auto_call_allowed,
        "seeded": seed is not None,
        "vetted_seed_whitelist": seed is not None,
        "required_valid_pointer_args": {str(key): value for key, value in required_ptrs.items()},
        "return_kind": str(seed.get("return_kind", "unknown")) if seed else "unknown",
        "reasons": reasons,
        "warnings": warnings,
        "resolution": resolution.public_dict(),
        "signals": signals,
    }


def run_call_safety_classify(symbols: dict[str, Symbol],
                             image: StaticImage,
                             names: tuple[str, ...],
                             *,
                             include_objdump: bool = True) -> dict[str, object]:
    classify_names = names or tuple(CALL_SAFETY_SEEDS)
    rows = [
        classify_call_safety(symbols, image, name, include_objdump=include_objdump)
        for name in classify_names
    ]
    counts: dict[str, int] = {}
    for row in rows:
        tier = str(row["tier"])
        counts[tier] = counts.get(tier, 0) + 1
    return {
        "decision": "a90-repl-u2-call-safety-classify-host-pass",
        "ok": True,
        "host_only": True,
        "device_action": False,
        "boot_image_changed": False,
        "deny_by_default": True,
        "allow_unvetted_token": CALL_SAFETY_ALLOW_UNVETTED_TOKEN,
        "seed_whitelist_count": len(CALL_SAFETY_SEEDS),
        "requested_symbol_count": len(classify_names),
        "counts": counts,
        "rows": rows,
    }


_SOURCE_SIGNATURE_CACHE: dict[tuple[str, str], dict[str, object]] = {}
_SOURCE_CANDIDATE_FILE_CACHE: dict[tuple[str, str], tuple[Path, ...]] = {}
_SOURCE_HINT_FILE_CACHE: dict[tuple[str, str], tuple[Path, ...]] = {}
_SOURCE_FILE_TEXT_CACHE: dict[Path, str | None] = {}
_SOURCE_C_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SOURCE_HEADER_HINTS_BY_EXACT_SYMBOL = {
    "filp_clone_open": ("fs/internal.h", "include/linux/fs.h"),
    "filp_close": ("include/linux/fs.h",),
    "filp_open": ("include/linux/fs.h",),
    "kfree_call_rcu": ("include/linux/rcutree.h",),
    "kfree_const": ("include/linux/string.h",),
    "kfree_link": ("include/linux/fs.h",),
    "kernel_read": ("include/linux/fs.h",),
    "kernel_read_file": ("include/linux/fs.h",),
    "kernel_read_file_from_fd": ("include/linux/fs.h",),
    "kernel_read_file_from_path": ("include/linux/fs.h",),
    "kernel_write": ("include/linux/fs.h",),
    "kfree": ("include/linux/slab.h",),
    "ksize": ("include/linux/slab.h",),
    "vfs_getxattr": ("include/linux/xattr.h",),
    "vfs_getxattr_alloc": ("include/linux/xattr.h",),
    "vfs_ioctl": ("fs/internal.h", "include/linux/fs.h"),
    "vfs_kern_mount": ("include/linux/mount.h",),
    "vfs_listxattr": ("include/linux/xattr.h",),
    "vfs_load_quota_inode": ("fs/quota/dquot.c",),
}
_SOURCE_HEADER_HINTS_BY_PREFIX = (
    ("__kmalloc", ("include/linux/slab.h",)),
    ("filp_", ("include/linux/fs.h", "fs/internal.h")),
    ("kernel_read", ("include/linux/fs.h",)),
    ("kernel_write", ("include/linux/fs.h",)),
    ("kfree_skb", ("include/linux/skbuff.h",)),
    ("kfree", ("include/linux/slab.h",)),
    ("kmalloc", ("include/linux/slab.h",)),
    ("kmem_cache", ("include/linux/slab.h",)),
    ("kref_", ("include/linux/kref.h",)),
    ("memcmp", ("include/linux/string.h", "arch/arm64/include/asm/string.h")),
    ("memcpy", ("include/linux/string.h", "arch/arm64/include/asm/string.h")),
    ("memmove", ("include/linux/string.h", "arch/arm64/include/asm/string.h")),
    ("memset", ("include/linux/string.h", "arch/arm64/include/asm/string.h")),
    ("refcount_", ("include/linux/refcount.h",)),
    ("str", ("include/linux/string.h", "arch/arm64/include/asm/string.h")),
    ("sysfs_", ("include/linux/sysfs.h",)),
    ("vfs_", (
        "include/linux/fs.h",
        "include/linux/xattr.h",
        "include/linux/mount.h",
        "fs/internal.h",
        "fs/quota/dquot.c",
    )),
)


def _public_repo_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _source_symbol_header_hints(symbol: str) -> tuple[str, ...]:
    exact = _SOURCE_HEADER_HINTS_BY_EXACT_SYMBOL.get(symbol)
    if exact:
        return exact
    for prefix, hints in _SOURCE_HEADER_HINTS_BY_PREFIX:
        if symbol.startswith(prefix):
            return hints
    return ()


def _source_file_priority(root: Path, path: Path, symbol: str) -> tuple[int, int, str]:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = path.as_posix()
    hints = _source_symbol_header_hints(symbol)
    for index, hint in enumerate(hints):
        if rel == hint:
            return (-10, index, rel)
    if rel.startswith("include/linux/") and path.suffix == ".h":
        return (0, 0, rel)
    if rel.startswith("include/") and path.suffix == ".h":
        return (1, 0, rel)
    if rel.startswith("arch/arm64/include/") and path.suffix == ".h":
        return (2, 0, rel)
    if path.suffix == ".h":
        return (3, 0, rel)
    if rel.startswith("fs/"):
        return (4, 0, rel)
    if rel.startswith("drivers/"):
        return (5, 0, rel)
    if rel.startswith("arch/"):
        return (6, 0, rel)
    return (7, 0, rel)


def _strip_c_comments_preserve_newlines(text: str) -> str:
    def block_repl(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    text = re.sub(r"/\*.*?\*/", block_repl, text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def _split_c_args(args_text: str) -> list[str]:
    args: list[str] = []
    start = 0
    depth = 0
    for index, ch in enumerate(args_text):
        if ch in "([<":
            depth += 1
        elif ch in ")]>" and depth:
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(args_text[start:index].strip())
            start = index + 1
    tail = args_text[start:].strip()
    if tail:
        args.append(tail)
    return args


_SOURCE_ARG_TYPE_WORDS = frozenset((
    "bool",
    "char",
    "const",
    "enum",
    "gfp_t",
    "int",
    "loff_t",
    "long",
    "mode_t",
    "pid_t",
    "short",
    "signed",
    "size_t",
    "ssize_t",
    "struct",
    "u8",
    "u16",
    "u32",
    "u64",
    "uint8_t",
    "uint16_t",
    "uint32_t",
    "uint64_t",
    "union",
    "unsigned",
    "void",
))
_SOURCE_NON_SIGNATURE_PREFIXES = (
    "#",
    "case ",
    "default:",
    "do ",
    "else ",
    "for ",
    "if ",
    "return ",
    "sizeof",
    "switch ",
    "while ",
)


def _source_argument_looks_typed(arg: str) -> bool:
    arg = arg.strip()
    if not arg or arg == "...":
        return True
    if arg == "void":
        return True
    if "*" in arg or "[" in arg or "__user" in arg:
        return True
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", arg)
    if any(word in _SOURCE_ARG_TYPE_WORDS for word in words):
        return True
    if any(word.endswith("_t") for word in words):
        return True
    return False


def _source_prefix_looks_like_function_decl(prefix: str) -> bool:
    if any(ch in prefix for ch in "{}:"):
        return False
    if re.search(r"\b(if|while|for|return|switch|case|goto)\b", prefix):
        return False
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", prefix)
    if any(word in _SOURCE_ARG_TYPE_WORDS for word in words):
        return True
    if any(word.endswith("_t") for word in words):
        return True
    return "*" in prefix


def _source_signature_annotation_flags(signature: str, args: list[str]) -> list[str]:
    haystack = " ".join([signature, *args])
    flags: list[str] = []
    if re.search(r"\b__init\b", haystack):
        flags.append("source-__init-annotation")
    if re.search(r"\b__exit\b", haystack):
        flags.append("source-__exit-annotation")
    if "__user" in haystack:
        flags.append("source-__user-pointer")
    if "__must_hold" in haystack:
        flags.append("source-__must_hold-annotation")
    if "might_sleep" in haystack:
        flags.append("source-might_sleep")
    if re.search(r"\b(raw_spin|spin_lock|mutex_lock|rcu_|lockdep_assert|preempt_)", haystack):
        flags.append("source-locking-or-rcu-annotation")
    return flags


def _parse_source_signature_statement(root: Path,
                                      file_path: Path,
                                      statement: str,
                                      start_line: int,
                                      symbol: str) -> dict[str, object] | None:
    stripped = statement.lstrip()
    if stripped.startswith(_SOURCE_NON_SIGNATURE_PREFIXES):
        return None
    if re.search(r"\btypedef\b", statement):
        return None
    flat = re.sub(r"\s+", " ", statement).strip()
    if symbol not in flat:
        return None

    pattern = re.compile(r"\b" + re.escape(symbol) + r"\s*\((?P<args>[^;{}]*)\)")
    for match in pattern.finditer(flat):
        prefix = flat[:match.start()].strip()
        if not prefix or prefix.endswith(_SOURCE_NON_SIGNATURE_PREFIXES):
            continue
        prefix_tail = prefix[-180:]
        if re.search(r"\b(return|if|while|for|switch|sizeof)\s*$", prefix_tail):
            continue
        if not _source_prefix_looks_like_function_decl(prefix_tail):
            continue
        if "=" in prefix_tail and prefix_tail.rfind("=") > prefix_tail.rfind(";"):
            continue
        args_text = match.group("args").strip()
        args = [] if not args_text else _split_c_args(args_text)
        if args == ["void"]:
            args = []
        if not all(_source_argument_looks_typed(arg) for arg in args):
            continue
        suffix = flat[match.end():]
        suffix = re.split(r"[;{]", suffix, maxsplit=1)[0].strip()
        signature = " ".join(part for part in (prefix_tail, f"{symbol}({args_text})", suffix) if part)
        parsed_args: list[dict[str, object]] = []
        pointer_indices: list[int] = []
        user_pointer_indices: list[int] = []
        variadic = False
        for index, arg in enumerate(args):
            arg_clean = arg.strip()
            is_variadic = arg_clean == "..."
            variadic = variadic or is_variadic
            is_pointer = (
                "*" in arg_clean
                or "[" in arg_clean
                or "__user" in arg_clean
                or "(*" in arg_clean
            )
            if is_pointer:
                pointer_indices.append(index)
            if "__user" in arg_clean:
                user_pointer_indices.append(index)
            parsed_args.append({
                "index": index,
                "text": arg_clean,
                "is_pointer": is_pointer,
                "is_user_pointer": "__user" in arg_clean,
                "is_variadic": is_variadic,
            })
        return {
            "path": _public_repo_path(file_path),
            "line": start_line,
            "signature": signature,
            "arg_count": len(args),
            "args": parsed_args,
            "pointer_arg_indices": pointer_indices,
            "user_pointer_arg_indices": user_pointer_indices,
            "variadic": variadic,
            "annotation_flags": _source_signature_annotation_flags(signature, args),
        }
    return None


def _source_candidate_files(root: Path, symbol: str) -> tuple[Path, ...]:
    key = (str(root.resolve()), symbol)
    cached = _SOURCE_CANDIDATE_FILE_CACHE.get(key)
    if cached is not None:
        return cached

    candidates: list[Path] = []
    rg = shutil.which("rg")
    if rg:
        try:
            proc = subprocess.run(
                [
                    rg,
                    "--fixed-strings",
                    "--files-with-matches",
                    "--glob",
                    "*.c",
                    "--glob",
                    "*.h",
                    symbol,
                    str(root),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15,
                check=False,
            )
            if proc.returncode in (0, 1):
                candidates = [Path(line) for line in proc.stdout.splitlines() if line.strip()]
        except (OSError, subprocess.TimeoutExpired):
            candidates = []

    if not candidates:
        for suffix in ("*.h", "*.c"):
            for path in root.rglob(suffix):
                try:
                    if symbol in path.read_text(errors="ignore"):
                        candidates.append(path)
                except OSError:
                    continue

    result = tuple(sorted(set(candidates), key=lambda path: _source_file_priority(root, path, symbol)))
    _SOURCE_CANDIDATE_FILE_CACHE[key] = result
    return result


def _extract_source_signatures_from_file(root: Path,
                                         file_path: Path,
                                         symbol: str) -> list[dict[str, object]]:
    original = _source_file_text(file_path)
    if original is None:
        return []
    text = _strip_c_comments_preserve_newlines(original)
    matches: list[dict[str, object]] = []
    statement_lines: list[str] = []
    statement_start = 1
    paren_depth = 0
    for lineno, line in enumerate(text.splitlines(), start=1):
        if paren_depth == 0 and not line.strip():
            statement_lines = []
            continue
        if paren_depth == 0 and line.lstrip().startswith("#"):
            statement_lines = []
            continue
        if not statement_lines:
            statement_start = lineno
        statement_lines.append(line)
        paren_depth += line.count("(") - line.count(")")
        too_long = sum(len(part) for part in statement_lines) > 5000
        terminates = (";" in line or "{" in line) and paren_depth <= 0
        if terminates or too_long:
            statement = "\n".join(statement_lines)
            if symbol in statement:
                parsed = _parse_source_signature_statement(root, file_path, statement, statement_start, symbol)
                if parsed is not None:
                    matches.append(parsed)
            statement_lines = []
            paren_depth = 0
    return matches


def _source_match_sort_key(row: dict[str, object], symbol: str = "") -> tuple[int, int, int, str]:
    path = str(row.get("path", ""))
    for index, hint in enumerate(_source_symbol_header_hints(symbol)):
        if path.endswith(hint):
            return (-10, index, int(row.get("line", 0) or 0), path)
    if "/include/linux/" in f"/{path}":
        bucket = 0
    elif "/arch/arm64/" in f"/{path}":
        bucket = 1
    elif "/fs/" in f"/{path}":
        bucket = 2
    elif "/drivers/" in f"/{path}":
        bucket = 3
    else:
        bucket = 4
    signature = str(row.get("signature", ""))
    if signature.startswith("extern "):
        bucket -= 1
    return (bucket, 0, int(row.get("line", 0) or 0), path)


def _source_hint_files(root: Path, symbol: str) -> tuple[Path, ...]:
    key = (str(root.resolve()), symbol)
    cached = _SOURCE_HINT_FILE_CACHE.get(key)
    if cached is not None:
        return cached

    files: list[Path] = []
    for rel in _source_symbol_header_hints(symbol):
        path = root / rel
        if path.is_file():
            files.append(path)
    result = tuple(sorted(set(files), key=lambda path: _source_file_priority(root, path, symbol)))
    _SOURCE_HINT_FILE_CACHE[key] = result
    return result


def _source_file_text(path: Path) -> str | None:
    cached = _SOURCE_FILE_TEXT_CACHE.get(path)
    if cached is not None or path in _SOURCE_FILE_TEXT_CACHE:
        return cached
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        text = None
    _SOURCE_FILE_TEXT_CACHE[path] = text
    return text


def _dedupe_source_matches(matches: list[dict[str, object]],
                           symbol: str) -> list[dict[str, object]]:
    deduped: dict[tuple[str, int], dict[str, object]] = {}
    for row in matches:
        deduped[(str(row.get("signature")), int(row.get("line", 0) or 0))] = row
    return sorted(deduped.values(), key=lambda row: _source_match_sort_key(row, symbol))


def _source_lookup_result_from_matches(symbol: str,
                                       root: Path,
                                       candidate_files: tuple[Path, ...],
                                       matches: list[dict[str, object]],
                                       *,
                                       strategy: str,
                                       missing_reason: str) -> dict[str, object]:
    candidate_file_sample = [_public_repo_path(path) for path in candidate_files[:12]]
    matches = _dedupe_source_matches(matches, symbol)

    if not matches:
        return {
            "symbol": symbol,
            "found": False,
            "has_pointer_arg": False,
            "pointer_arg_indices": [],
            "status": "missing",
            "reason": missing_reason,
            "source_root": _public_repo_path(root),
            "candidate_file_count": len(candidate_files),
            "candidate_files_sample": candidate_file_sample,
            "candidate_scan_strategy": strategy,
            "match_count": 0,
            "selected": None,
            "matches_sample": [],
        }

    shapes = {
        (
            int(row.get("arg_count", 0) or 0),
            tuple(row.get("pointer_arg_indices", [])),
            tuple(row.get("user_pointer_arg_indices", [])),
            bool(row.get("variadic")),
        )
        for row in matches
    }
    if len(shapes) > 1:
        return {
            "symbol": symbol,
            "found": False,
            "has_pointer_arg": False,
            "pointer_arg_indices": [],
            "status": "ambiguous",
            "reason": "source-signatures-have-incompatible-arg-shapes",
            "source_root": _public_repo_path(root),
            "candidate_file_count": len(candidate_files),
            "candidate_files_sample": candidate_file_sample,
            "candidate_scan_strategy": strategy,
            "match_count": len(matches),
            "selected": None,
            "matches_sample": matches[:8],
        }

    selected = matches[0]
    pointer_arg_indices = [int(index) for index in selected.get("pointer_arg_indices", [])]
    return {
        "symbol": symbol,
        "found": True,
        "has_pointer_arg": bool(pointer_arg_indices),
        "pointer_arg_indices": pointer_arg_indices,
        "status": "found",
        "reason": "source-signature-found",
        "source_root": _public_repo_path(root),
        "candidate_file_count": len(candidate_files),
        "candidate_files_sample": candidate_file_sample,
        "candidate_scan_strategy": strategy,
        "match_count": len(matches),
        "selected": selected,
        "matches_sample": matches[:8],
    }


def lookup_source_signature(symbol: str,
                            *,
                            source_root: Path = DEFAULT_KERNEL_SOURCE_ROOT) -> dict[str, object]:
    root = source_root.resolve()
    key = (str(root), symbol)
    cached = _SOURCE_SIGNATURE_CACHE.get(key)
    if cached is not None:
        return cached

    if not root.is_dir():
        result = {
            "symbol": symbol,
            "found": False,
            "has_pointer_arg": False,
            "pointer_arg_indices": [],
            "status": "missing",
            "reason": "source-root-missing",
            "source_root": str(source_root),
            "candidate_file_count": 0,
            "candidate_files_sample": [],
            "match_count": 0,
            "selected": None,
            "matches_sample": [],
        }
        _SOURCE_SIGNATURE_CACHE[key] = result
        return result

    if not _SOURCE_C_IDENTIFIER_RE.fullmatch(symbol):
        result = {
            "symbol": symbol,
            "found": False,
            "has_pointer_arg": False,
            "pointer_arg_indices": [],
            "status": "missing",
            "reason": "source-symbol-not-c-identifier",
            "source_root": _public_repo_path(root),
            "candidate_file_count": 0,
            "candidate_files_sample": [],
            "candidate_scan_strategy": "identifier-reject",
            "match_count": 0,
            "selected": None,
            "matches_sample": [],
        }
        _SOURCE_SIGNATURE_CACHE[key] = result
        return result

    hint_files = _source_hint_files(root, symbol)
    if hint_files:
        hint_matches: list[dict[str, object]] = []
        for path in hint_files:
            hint_matches.extend(_extract_source_signatures_from_file(root, path, symbol))
        if hint_matches:
            result = _source_lookup_result_from_matches(
                symbol,
                root,
                hint_files,
                hint_matches,
                strategy="hint",
                missing_reason="signature-not-found-in-source-hints",
            )
            _SOURCE_SIGNATURE_CACHE[key] = result
            return result

    candidate_files = _source_candidate_files(root, symbol)
    matches: list[dict[str, object]] = []
    for path in candidate_files:
        if path.suffix not in (".c", ".h"):
            continue
        matches.extend(_extract_source_signatures_from_file(root, path, symbol))

    result = _source_lookup_result_from_matches(
        symbol,
        root,
        candidate_files,
        matches,
        strategy="rg-fallback",
        missing_reason="signature-not-found-in-source",
    )
    _SOURCE_SIGNATURE_CACHE[key] = result
    return result


def _source_pointer_arg_indices(source: dict[str, object]) -> set[int]:
    selected = source.get("selected")
    if not isinstance(selected, dict):
        return set()
    return {
        int(index)
        for index in selected.get("pointer_arg_indices", [])
    }


def _source_pointer_arg_requirements(source: dict[str, object]) -> dict[str, str]:
    selected = source.get("selected")
    if not isinstance(selected, dict):
        return {}
    req: dict[str, str] = {}
    for arg in selected.get("args", []):
        if not isinstance(arg, dict) or not arg.get("is_pointer"):
            continue
        req[str(arg["index"])] = str(arg.get("text", "source-pointer-arg"))
    return req


def _source_row_evidence(source: dict[str, object]) -> dict[str, object]:
    selected = source.get("selected")
    if not isinstance(selected, dict):
        return {
            "status": source.get("status"),
            "found": bool(source.get("found")),
            "has_pointer_arg": bool(source.get("has_pointer_arg")),
            "pointer_arg_indices": list(source.get("pointer_arg_indices", [])),
            "signature": None,
            "path": None,
            "line": None,
            "annotation_flags": [],
        }
    return {
        "status": source.get("status"),
        "found": bool(source.get("found")),
        "has_pointer_arg": bool(source.get("has_pointer_arg")),
        "pointer_arg_indices": list(source.get("pointer_arg_indices", [])),
        "signature": selected.get("signature"),
        "path": selected.get("path"),
        "line": selected.get("line"),
        "annotation_flags": list(selected.get("annotation_flags", [])),
    }


def _arg_source_index_from_text(text: str) -> int | None:
    match = re.fullmatch(r"x([0-7])", text.strip())
    return int(match.group(1)) if match else None


def _signal_arg_memory_source_indices(signals: dict[str, object]) -> set[int]:
    indices: set[int] = set()
    for row in signals.get("arg_pointer_derefs_before_first_bl_or_ret", []) or []:
        if isinstance(row, dict):
            arg = _arg_source_index_from_text(str(row.get("arg", "")))
            if arg is not None:
                indices.add(arg)
    taint_flow = signals.get("arg_taint_flow", {})
    if isinstance(taint_flow, dict):
        for row in taint_flow.get("arg_memory_base_uses", []) or []:
            if not isinstance(row, dict):
                continue
            for source_arg in row.get("source_args", []) or []:
                arg = _arg_source_index_from_text(str(source_arg))
                if arg is not None:
                    indices.add(arg)
    return indices


def _name_is_behavior_changing(name: str) -> bool:
    return name.startswith((
        "commit_creds",
        "prepare_kernel_cred",
        "set_memory_",
        "call_usermodehelper",
    ))


def _call_safety_advisory_from_source(row: dict[str, object],
                                      source: dict[str, object]) -> dict[str, object]:
    symbol = str(row.get("symbol"))
    signals = row.get("signals", {})
    if not isinstance(signals, dict):
        signals = {}
    resolution = row.get("resolution", {})
    verified = bool(isinstance(resolution, dict) and resolution.get("verified"))
    pointer_args = _source_pointer_arg_indices(source)
    memory_source_args = _signal_arg_memory_source_indices(signals)
    taint_flow = signals.get("arg_taint_flow", {})
    taint_available = isinstance(taint_flow, dict) and bool(taint_flow.get("available"))

    danger_flags: list[str] = []
    reasons: list[str] = []
    advisory_tier = CALL_SAFETY_DENY

    if not verified:
        danger_flags.append("identity-not-c1-verified")
        reasons.append("C1 identity verification failed or is unavailable")
    if symbol in KNOWN_UNSAFE_CALL_TARGETS:
        danger_flags.append("known-unsafe-live-call")
        reasons.append("known unsafe live-call target")
    if _name_is_behavior_changing(symbol):
        danger_flags.append("behavior-changing-name-family")
        reasons.append("behavior-changing name family")

    source_status = str(source.get("status"))
    if source_status == "missing":
        danger_flags.append("source-missing")
        reasons.append("source signature missing; fail-closed downgrade")
    elif source_status == "ambiguous":
        danger_flags.append("source-ambiguous")
        reasons.append("source signatures ambiguous; fail-closed downgrade")
    elif source_status != "found":
        danger_flags.append(f"source-{source_status}")
        reasons.append("source signature not usable")

    selected = source.get("selected")
    annotation_flags: list[str] = []
    if isinstance(selected, dict):
        annotation_flags = [str(flag) for flag in selected.get("annotation_flags", [])]
    for flag in annotation_flags:
        danger_flags.append(flag)
    if any(flag.startswith("source-__user") for flag in annotation_flags):
        reasons.append("__user pointer in source signature")
    if any(flag in annotation_flags for flag in (
        "source-__exit-annotation",
        "source-__init-annotation",
        "source-__must_hold-annotation",
        "source-might_sleep",
        "source-locking-or-rcu-annotation",
    )):
        reasons.append("source context annotation requires manual gate")

    context_count = int(signals.get("context_call_count", 0) or 0)
    if context_count:
        danger_flags.append("context-sensitive-disasm-call")
        reasons.append("disasm reaches lock/sleep/preempt/irq-sensitive call")
    if signals.get("variadic_prologue_matches_printk") and symbol != "printk":
        danger_flags.append("variadic-prologue-printk-twin")
        reasons.append("printk-like variadic prologue shape")

    if source_status == "found" and pointer_args and row.get("tier") == CALL_SAFETY_SAFE_SCALAR:
        danger_flags.append("source-overrides-safe-scalar-pointer-arg")
        reasons.append("source declares pointer args; never SAFE-SCALAR")

    uncovered = sorted(memory_source_args - pointer_args)
    gate_required_ptrs = {
        int(index)
        for index in row.get("required_valid_pointer_args", {})
        if str(index).isdigit()
    }
    source_or_memory_args = pointer_args | memory_source_args
    unseeded_gate_uncovered = sorted(source_or_memory_args - gate_required_ptrs)
    if source_or_memory_args and not row.get("seeded") and unseeded_gate_uncovered:
        danger_flags.append("unseeded-arg-memory-flow-without-gate-pointer-contract")
        reasons.append(
            "non-seeded target has source/disasm pointer-arg evidence without a vetted gate pointer contract:"
            + ",".join(f"x{arg}" for arg in unseeded_gate_uncovered)
        )
    context_blocked = bool(annotation_flags or context_count)
    if source_status == "found":
        if pointer_args:
            if uncovered:
                danger_flags.append("arg-memory-base-flow-uncovered-by-source-pointer-args")
                reasons.append(
                    "taint flow uses non-pointer source args as memory-base contributors:"
                    + ",".join(f"x{arg}" for arg in uncovered)
                )
            elif verified and context_blocked:
                advisory_tier = CALL_SAFETY_CONTEXT_SENSITIVE
                reasons.append("source pointer args covered, but context danger requires manual gate")
            elif verified:
                advisory_tier = CALL_SAFETY_SAFE_WITH_VALID_PTR
                reasons.append("source pointer args cover observed arg-derived memory bases")
        else:
            if memory_source_args:
                danger_flags.append("arg-memory-base-flow-without-source-pointer-args")
                reasons.append("source says scalar-only but disasm uses arg-derived memory base")
            elif not taint_available:
                danger_flags.append("arg-taint-flow-unavailable")
                reasons.append("missing positive taint proof for scalar-only candidate")
            elif verified and context_blocked:
                advisory_tier = CALL_SAFETY_CONTEXT_SENSITIVE
                reasons.append("source scalar-only signature, but context danger requires manual gate")
            elif verified and taint_flow.get("safe_scalar_positive_no_arg_memory_base_flow"):
                advisory_tier = CALL_SAFETY_SAFE_SCALAR
                reasons.append("source scalar-only signature plus clean arg-taint memory-base proof")

    blocking_flags = [
        flag for flag in danger_flags
        if flag not in ("source-overrides-safe-scalar-pointer-arg",)
    ]
    candidate_safe = advisory_tier in CALL_SAFETY_SAFE_TIERS and not blocking_flags
    if candidate_safe:
        reasons.append("advisory candidate only; does not alter call gate")

    return {
        "tier": advisory_tier,
        "safe_group": advisory_tier in CALL_SAFETY_SAFE_TIERS,
        "candidate_safe": candidate_safe,
        "candidate_tag": "advisory-not-auto-callable" if candidate_safe else None,
        "required_valid_pointer_args_from_source": _source_pointer_arg_requirements(source),
        "source_pointer_arg_indices": sorted(pointer_args),
        "arg_memory_source_indices": sorted(memory_source_args),
        "source_or_arg_memory_indices": sorted(source_or_memory_args),
        "danger_flags": sorted(set(danger_flags)),
        "blocking_danger_flags": sorted(set(blocking_flags)),
        "reasons": reasons,
    }


def _select_call_safety_sweep_symbols(symbols: dict[str, Symbol],
                                      *,
                                      families: tuple[str, ...],
                                      prefixes: tuple[str, ...],
                                      regexes: tuple[str, ...],
                                      explicit_symbols: tuple[str, ...],
                                      limit: int) -> tuple[str, ...]:
    selected: set[str] = set(explicit_symbols)
    function_names = sorted(
        name for name, symbol in symbols.items()
        if _map_kind_is_function(symbol.kind)
    )

    family_prefixes: list[str] = []
    family_regexes: list[str] = []
    for family in families:
        spec = CALL_SAFETY_SWEEP_FAMILIES.get(family)
        if spec is None:
            raise ReplError(f"unknown call-safety sweep family: {family}")
        for name in spec.get("symbols", ()):
            if name in symbols:
                selected.add(str(name))
        family_prefixes.extend(str(prefix) for prefix in spec.get("prefixes", ()))
        family_regexes.extend(str(regex) for regex in spec.get("regexes", ()))

    all_prefixes = tuple(prefixes) + tuple(family_prefixes)
    for prefix in all_prefixes:
        selected.update(name for name in function_names if name.startswith(prefix))

    compiled_regexes = [re.compile(pattern) for pattern in tuple(regexes) + tuple(family_regexes)]
    for regex in compiled_regexes:
        selected.update(name for name in function_names if regex.search(name))

    ordered = tuple(sorted(selected))
    if limit > 0:
        ordered = ordered[:limit]
    return ordered


def run_call_safety_sweep(symbols: dict[str, Symbol],
                          image: StaticImage,
                          *,
                          families: tuple[str, ...] = (),
                          prefixes: tuple[str, ...] = (),
                          regexes: tuple[str, ...] = (),
                          explicit_symbols: tuple[str, ...] = (),
                          limit: int = 60,
                          source_root: Path = DEFAULT_KERNEL_SOURCE_ROOT,
                          include_objdump: bool = False) -> dict[str, object]:
    if not (families or prefixes or regexes or explicit_symbols):
        families = ("allocator", "string", "read-io")

    names = _select_call_safety_sweep_symbols(
        symbols,
        families=families,
        prefixes=prefixes,
        regexes=regexes,
        explicit_symbols=explicit_symbols,
        limit=limit,
    )

    rows: list[dict[str, object]] = []
    gate_counts: dict[str, int] = {}
    advisory_counts: dict[str, int] = {}
    danger_counts: dict[str, int] = {}
    for name in names:
        gate_row = classify_call_safety(
            symbols,
            image,
            name,
            include_objdump=include_objdump,
        )
        source = lookup_source_signature(name, source_root=source_root)
        advisory = _call_safety_advisory_from_source(gate_row, source)
        gate_tier = str(gate_row.get("tier"))
        advisory_tier = str(advisory.get("tier"))
        gate_counts[gate_tier] = gate_counts.get(gate_tier, 0) + 1
        advisory_counts[advisory_tier] = advisory_counts.get(advisory_tier, 0) + 1
        for flag in advisory.get("danger_flags", []) or []:
            danger_counts[str(flag)] = danger_counts.get(str(flag), 0) + 1
        source_evidence = _source_row_evidence(source)
        rows.append({
            "symbol": name,
            "gate_tier": gate_tier,
            "gate_auto_call_allowed": bool(gate_row.get("auto_call_allowed")),
            "gate_seeded": bool(gate_row.get("seeded")),
            "gate_required_valid_pointer_args": gate_row.get("required_valid_pointer_args", {}),
            "advisory": advisory,
            "source": source,
            "source_evidence": source_evidence,
            "source_signature": source_evidence["signature"],
            "source_annotation_flags": source_evidence["annotation_flags"],
            "resolution": gate_row.get("resolution", {}),
            "signals": gate_row.get("signals", {}),
            "gate_reasons": gate_row.get("reasons", []),
            "gate_warnings": gate_row.get("warnings", []),
        })

    tier_order = {
        CALL_SAFETY_SAFE_SCALAR: 0,
        CALL_SAFETY_SAFE_WITH_VALID_PTR: 1,
        CALL_SAFETY_CONTEXT_SENSITIVE: 2,
        CALL_SAFETY_BEHAVIOR_CHANGING: 3,
        CALL_SAFETY_DENY: 4,
    }
    candidates = [
        {
            "symbol": row["symbol"],
            "advisory_tier": row["advisory"]["tier"],
            "candidate_tag": row["advisory"]["candidate_tag"],
            "required_valid_pointer_args_from_source": row["advisory"][
                "required_valid_pointer_args_from_source"
            ],
            "source": row["source"].get("selected"),
            "source_signature": row.get("source_signature"),
            "source_annotation_flags": row.get("source_annotation_flags", []),
            "gate_seeded": row["gate_seeded"],
            "gate_auto_call_allowed": row["gate_auto_call_allowed"],
            "note": "advisory candidate; not inserted into CALL_SAFETY_SEEDS",
        }
        for row in rows
        if row["advisory"].get("candidate_safe")
    ]
    candidates.sort(
        key=lambda row: (
            bool(row["gate_seeded"]),
            tier_order.get(str(row["advisory_tier"]), 99),
            str(row["symbol"]),
        )
    )

    return {
        "decision": "a90-repl-u3-call-safety-sweep-host-pass",
        "ok": True,
        "host_only": True,
        "device_action": False,
        "boot_image_changed": False,
        "network_dependency": False,
        "offline_source_oracle": True,
        "source_root": _public_repo_path(source_root),
        "families": list(families),
        "prefixes": list(prefixes),
        "regexes": list(regexes),
        "explicit_symbols": list(explicit_symbols),
        "limit": limit,
        "seed_whitelist_count": len(CALL_SAFETY_SEEDS),
        "auto_call_firewall": "sweep-results-do-not-mutate-CALL_SAFETY_SEEDS-or-call-gate",
        "swept_symbol_count": len(rows),
        "gate_counts": gate_counts,
        "advisory_counts": advisory_counts,
        "danger_counts": dict(sorted(danger_counts.items())),
        "candidate_safe_count": len(candidates),
        "candidate_safe_ranked": candidates,
        "rows": rows,
    }


def _call_arg_is_verified_pointer_token(arg: int | str) -> bool:
    return isinstance(arg, str) and arg.startswith("@") and len(arg) > 1


def _call_arg_satisfies_required_pointer(arg: int | str, kind: str) -> bool:
    if _call_arg_is_verified_pointer_token(arg):
        return True
    if kind.endswith("-or-NULL"):
        try:
            return parse_int_auto(str(arg)) == 0
        except argparse.ArgumentTypeError:
            return False
    return False


def require_call_safety_for_call(symbols: dict[str, Symbol],
                                 image: StaticImage,
                                 symbol: str,
                                 xargs: tuple[int | str, ...],
                                 *,
                                 allow_unvetted_token: str | None = None) -> dict[str, object]:
    row = classify_call_safety(symbols, image, symbol, include_objdump=False)
    tier = str(row["tier"])
    if allow_unvetted_token is not None:
        if allow_unvetted_token != CALL_SAFETY_ALLOW_UNVETTED_TOKEN:
            raise ReplError(
                "invalid --allow-unvetted token; expected "
                f"{CALL_SAFETY_ALLOW_UNVETTED_TOKEN!r}"
            )
        if tier == CALL_SAFETY_DENY:
            raise ReplError(
                f"call-safety gate refused {symbol!r}: DENY cannot be overridden "
                f"(reasons={row['reasons']})"
            )
        override_row = dict(row)
        override_row["override_used"] = True
        return override_row

    if tier == CALL_SAFETY_SAFE_SCALAR:
        return row

    if tier == CALL_SAFETY_SAFE_WITH_VALID_PTR:
        required = {
            int(index): kind
            for index, kind in dict(row["required_valid_pointer_args"]).items()
        }
        missing = [
            f"x{index}:{kind}"
            for index, kind in sorted(required.items())
            if index >= len(xargs) or not _call_arg_satisfies_required_pointer(xargs[index], kind)
        ]
        if not missing:
            return row
        raise ReplError(
            f"call-safety gate refused {symbol!r}: SAFE-WITH-VALID-PTR requires "
            f"verified @pointer args {missing}"
        )

    raise ReplError(
        f"call-safety gate refused {symbol!r}: tier={tier} reasons={row['reasons']}"
    )


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


def _resolve_call_arg(arg: int | str,
                      symbols: dict[str, Symbol],
                      image: StaticImage,
                      slide: int) -> tuple[int, str]:
    if isinstance(arg, int):
        return arg & MASK64, "integer"
    try:
        return parse_int_auto(arg) & MASK64, "integer"
    except argparse.ArgumentTypeError:
        pass
    if not arg.startswith("@"):
        raise ReplError(f"call arg must be an integer or @symbol token: {arg!r}")

    name = arg[1:]
    if name in ("repl_format", "format"):
        return (FORMAT_LINK_VADDR + slide) & MASK64, "pseudo:@repl_format"
    resolution = resolve_verified(symbols, image, name, purpose="peek")
    if resolution.link_vaddr is None:
        raise ReplError(f"call arg symbol {name!r} did not resolve")
    return (resolution.link_vaddr + slide) & MASK64, f"symbol:@{name}:{resolution.method}"


def run_call(session: ReplSession,
             symbols: dict[str, Symbol],
             image: StaticImage,
             symbol: str,
             xargs: tuple[int | str, ...],
             *,
             replay_safe: bool = False,
             allow_unvetted_token: str | None = None) -> tuple[dict[str, object], dict[str, object]]:
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        symbol,
        xargs,
        allow_unvetted_token=allow_unvetted_token,
    )
    resolution = call_safety["resolution"]
    if not isinstance(resolution, dict) or not resolution.get("verified") or resolution.get("link_vaddr") is None:
        raise ReplError(f"call target {symbol!r} is not verified by call-safety identity gate")
    link = int(str(resolution["link_vaddr"]), 16)
    private: dict[str, object] = {}
    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        resolved_arg_rows = [
            _resolve_call_arg(arg, symbols, image, slide)
            for arg in xargs
        ]
        resolved_args = tuple(row[0] for row in resolved_arg_rows)
        arg_sources = [row[1] for row in resolved_arg_rows]
        values = session.call_runtime_values(
            (link + slide) & MASK64,
            resolved_args,
            replay_safe=replay_safe,
        )
    finally:
        session.set_panic_on_oops(1)

    summary = {
        "decision": "a90-repl-v2c-u1-call-pass",
        "ok": True,
        "symbol": symbol,
        "arg_count": len(xargs),
        "return_value_count": len(values),
        "resolution": resolution,
        "call_safety": call_safety,
        "raw_runtime_values_redacted": True,
        "argument_values_redacted": True,
        "return_values_redacted": True,
        "replay_safe": replay_safe,
        "allow_unvetted_override_used": bool(call_safety.get("override_used")),
    }
    private.update({
        "slide": f"0x{slide:x}",
        "target_runtime": f"0x{((link + slide) & MASK64):x}",
        "arg_sources": arg_sources,
        "args": [f"0x{value:x}" for value in resolved_args],
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


CALL_PROOF_TARGETS = {
    "ksize": {
        "input_contract": "owned-__kmalloc-pointer",
        "return_contract": "size_t >= alloc_size and <= max_expected_return",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "size_t ksize(const void *)",
    },
    "filp_open": {
        "input_contract": "owned-kernel-pathname:/init",
        "return_contract": "struct file pointer, not NULL and not ERR_PTR",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "extern struct file * filp_open(const char *, int, umode_t)",
    },
    "kernel_read": {
        "input_contract": "filp_open(/init) file pointer + owned read buffer + owned loff_t pos",
        "return_contract": "ssize_t == read_len, buffer starts with ELF magic, pos advances by read_len",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "extern ssize_t kernel_read(struct file *, void *, size_t, loff_t *)",
    },
    "strnlen": {
        "input_contract": "owned NUL-terminated kernel string buffer + scalar maxlen",
        "return_contract": "size_t == expected string length and <= maxlen",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "extern __kernel_size_t strnlen(const char *,__kernel_size_t)",
    },
    "strlen": {
        "input_contract": "owned NUL-terminated kernel string buffer",
        "return_contract": "size_t == expected string length",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "extern __kernel_size_t strlen(const char *)",
    },
    "strcmp": {
        "input_contract": "two owned NUL-terminated kernel string buffers",
        "return_contract": "int == 0 for equal strings and positive sign when left first-difference byte is greater",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "extern int strcmp(const char *,const char *)",
    },
    "strscpy": {
        "input_contract": "owned destination buffer plus owned NUL-terminated source string buffer plus bounded size",
        "return_contract": "ssize_t == copied source length and destination prefix matches source",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "ssize_t strscpy(char *, const char *, size_t)",
    },
    "strlcpy": {
        "input_contract": "owned destination buffer plus owned NUL-terminated source string buffer plus bounded size",
        "return_contract": "size_t == source string length and destination prefix matches source",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "size_t strlcpy(char *, const char *, size_t)",
    },
    "strncpy": {
        "input_contract": "owned destination buffer plus owned NUL-terminated source string buffer plus bounded count",
        "return_contract": "char * == owned destination pointer and destination bytes match source plus NUL padding",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "extern char * strncpy(char *,const char *, __kernel_size_t)",
    },
    "memcmp": {
        "input_contract": "two owned initialized buffers plus bounded size inside both buffers",
        "return_contract": "int == 0 for equal bytes and positive sign when left first-difference byte is greater",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "extern int memcmp(const void *,const void *,__kernel_size_t)",
    },
    "strrchr": {
        "input_contract": "owned NUL-terminated kernel string buffer plus scalar search byte",
        "return_contract": "char * == owned string buffer plus expected last-occurrence offset; missing byte returns NULL",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "extern char * strrchr(const char *,int)",
    },
    "memset": {
        "input_contract": "owned destination buffer plus scalar fill byte plus bounded size",
        "return_contract": "void * == owned destination pointer; first size bytes equal fill byte; post-size canary preserved",
        "expected_tier": CALL_SAFETY_SAFE_WITH_VALID_PTR,
        "source_signature": "extern void * memset(void *,int,__kernel_size_t)",
    },
}
FILP_OPEN_PROOF_PATH = b"/init\x00"
FILP_OPEN_PROOF_FLAGS = 0
FILP_OPEN_PROOF_MODE = 0
KERNEL_READ_PROOF_LEN = 16
KERNEL_READ_EXPECTED_PREFIX = b"\x7fELF"
STRNLEN_PROOF_BYTES = b"A90STRNLEN\x00"
STRNLEN_PROOF_EXPECTED = len(STRNLEN_PROOF_BYTES) - 1
STRNLEN_PROOF_MAXLEN = 64
STRLEN_PROOF_BYTES = b"A90STRLEN\x00"
STRLEN_PROOF_EXPECTED = len(STRLEN_PROOF_BYTES) - 1
STRLEN_ZERO_FILL_LEN = 64
STRCMP_PROOF_BYTES = b"A90STRCMP-PROOF-ZZ\x00"
STRCMP_PROOF_LABEL = STRCMP_PROOF_BYTES[:-1].decode("ascii")
STRCMP_CANARY_LEN = 8
STRCMP_MISMATCH_OFFSET = len(b"A90STRCMP-PROOF-")
STRCMP_MISMATCH_RIGHT_BYTE = ord("@")
STRSCPY_PROOF_SRC_BYTES = b"A90STRSCPY\x00"
STRSCPY_PROOF_EXPECTED = len(STRSCPY_PROOF_SRC_BYTES) - 1
STRSCPY_PROOF_SIZE = 32
STRSCPY_SRC_ZERO_FILL_LEN = 64
STRSCPY_DST_CANARY_LEN = 8
STRLCPY_PROOF_SRC_BYTES = b"A90STRLCPY\x00"
STRLCPY_PROOF_EXPECTED = len(STRLCPY_PROOF_SRC_BYTES) - 1
STRLCPY_PROOF_SIZE = 32
STRLCPY_SRC_ZERO_FILL_LEN = 64
STRLCPY_DST_CANARY_LEN = 8
STRNCPY_PROOF_SRC_BYTES = b"A90STRNCPY\x00"
STRNCPY_PROOF_SIZE = 32
STRNCPY_SRC_ZERO_FILL_LEN = 64
STRNCPY_DST_CANARY_LEN = 8
MEMCMP_PROOF_BYTES = b"A90MEMCMP-PROOF-0123456789ABCDEF"
MEMCMP_PROOF_SIZE = len(MEMCMP_PROOF_BYTES)
MEMCMP_CANARY_LEN = 8
MEMCMP_MISMATCH_OFFSET = 10
MEMCMP_MISMATCH_RIGHT_BYTE = ord("@")
STRRCHR_PROOF_BYTES = b"A90STRRCHR-A-B-A-Z\x00"
STRRCHR_PROOF_LABEL = STRRCHR_PROOF_BYTES[:-1].decode("ascii")
STRRCHR_SEARCH_BYTE = ord("A")
STRRCHR_EXPECTED_OFFSET = STRRCHR_PROOF_BYTES[:-1].rfind(bytes([STRRCHR_SEARCH_BYTE]))
STRRCHR_MISSING_BYTE = ord("@")
STRRCHR_CANARY_LEN = 8
MEMSET_PROOF_SIZE = 32
MEMSET_PROOF_BYTE = 0x5A
MEMSET_INITIAL_BYTE = 0x11
MEMSET_CANARY_LEN = 8
LINUX_MAX_ERRNO = 4095
LINUX_ERR_PTR_MIN = ((-LINUX_MAX_ERRNO) & MASK64)


def _redacted_resolution_set(rows: dict[str, VerifiedResolution]) -> dict[str, dict[str, object]]:
    return {name: row.public_dict() for name, row in rows.items()}


def _is_kernel_err_ptr(value: int) -> bool:
    return (value & MASK64) >= LINUX_ERR_PTR_MIN


def _poke_bytes(session: ReplSession, runtime_vaddr: int, data: bytes) -> None:
    for offset in range(0, len(data), 8):
        chunk = data[offset:offset + 8]
        value = int.from_bytes(chunk.ljust(8, b"\x00"), "little")
        session.poke_runtime((runtime_vaddr + offset) & MASK64, value, 8)


def _peek_bytes(session: ReplSession, runtime_vaddr: int, length: int) -> bytes:
    out = bytearray()
    for offset in range(0, length, 8):
        value = session.peek_runtime((runtime_vaddr + offset) & MASK64, 8)
        out.extend(value.to_bytes(8, "little"))
    return bytes(out[:length])


def _run_call_proof_memcmp(session: ReplSession,
                           symbols: dict[str, Symbol],
                           image: StaticImage,
                           *,
                           alloc_size: int,
                           source_root: Path,
                           gfp: int,
                           gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    scan_len = MEMCMP_PROOF_SIZE + MEMCMP_CANARY_LEN
    if alloc_size < scan_len:
        raise ReplError(f"memcmp call-proof alloc_size must be at least {scan_len} bytes")

    if MEMCMP_MISMATCH_OFFSET >= MEMCMP_PROOF_SIZE:
        raise ReplError("memcmp mismatch offset must be inside proof size")
    if MEMCMP_PROOF_BYTES[MEMCMP_MISMATCH_OFFSET] <= MEMCMP_MISMATCH_RIGHT_BYTE:
        raise ReplError("memcmp mismatch right byte must be less than left byte for positive sign proof")

    source = lookup_source_signature("memcmp", source_root=source_root)
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        "memcmp",
        ("@owned_left_buffer", "@owned_right_buffer", MEMCMP_PROOF_SIZE),
    )
    if call_safety.get("tier") != CALL_PROOF_TARGETS["memcmp"]["expected_tier"]:
        raise ReplError("memcmp call-safety tier is not the expected vetted pointer tier")
    if not source.get("found") or source.get("pointer_arg_indices") != [0, 1]:
        raise ReplError("memcmp source signature does not declare x0/x1 as pointer arguments")

    resolutions = {
        "memcmp": resolve_verified(symbols, image, "memcmp", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    memcmp_link = require_verified_resolution(resolutions["memcmp"], "call-proof target")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof buffer allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof buffer cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    right_mismatch = bytearray(MEMCMP_PROOF_BYTES)
    right_mismatch[MEMCMP_MISMATCH_OFFSET] = MEMCMP_MISMATCH_RIGHT_BYTE
    right_mismatch_bytes = bytes(right_mismatch)
    expected_left_scan = MEMCMP_PROOF_BYTES + (b"\xcc" * MEMCMP_CANARY_LEN)
    expected_right_equal_scan = expected_left_scan
    expected_right_mismatch_scan = right_mismatch_bytes + (b"\xcc" * MEMCMP_CANARY_LEN)

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "memcmp",
            "resolution_method": resolutions["memcmp"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source.get("selected", {}).get("signature")
            if isinstance(source.get("selected"), dict) else None,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
            "bounded_size": MEMCMP_PROOF_SIZE,
        },
    ]
    private: dict[str, object] = {}
    left_ptr = 0
    right_ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted: list[str] = []
    free_ok: dict[str, bool] = {"left": False, "right": False}
    free_errors: list[str] = []
    equal_return = 0
    mismatch_return = 0
    observed_left = b""
    observed_right_equal = b""
    observed_right_mismatch = b""

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        memcmp_runtime = (memcmp_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        left_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        right_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        left_ok = is_kernel_lowmem_pointer(left_ptr)
        right_ok = is_kernel_lowmem_pointer(right_ptr)
        distinct_ok = left_ptr != right_ptr
        checks.append({
            "check": "kmalloc-owned-memcmp-buffers",
            "ok": left_ok and right_ok and distinct_ok,
            "alloc_size": alloc_size,
            "left_kernel_lowmem": left_ok,
            "right_kernel_lowmem": right_ok,
            "distinct_buffers": distinct_ok,
        })
        if not (left_ok and right_ok and distinct_ok):
            raise ReplError("__kmalloc did not return sane distinct memcmp buffers")

        _poke_bytes(session, left_ptr, expected_left_scan)
        _poke_bytes(session, right_ptr, expected_right_equal_scan)
        observed_left = _peek_bytes(session, left_ptr, scan_len)
        observed_right_equal = _peek_bytes(session, right_ptr, scan_len)
        setup_ok = observed_left == expected_left_scan and observed_right_equal == expected_right_equal_scan
        checks.append({
            "check": "owned-memcmp-buffer-poke-peek",
            "ok": setup_ok,
            "proof_bytes_label": MEMCMP_PROOF_BYTES.decode("ascii"),
            "size_arg": MEMCMP_PROOF_SIZE,
            "canary_len": MEMCMP_CANARY_LEN,
        })
        if not setup_ok:
            raise ReplError("owned memcmp buffer poke/peek mismatch")

        equal_return = session.call_runtime(memcmp_runtime, (left_ptr, right_ptr, MEMCMP_PROOF_SIZE))
        equal_ok = equal_return == 0
        checks.append({
            "check": "memcmp-equal-return-contract",
            "ok": equal_ok,
            "expected_return": "0x0",
            "observed_return": f"0x{equal_return:x}",
            "size_arg": MEMCMP_PROOF_SIZE,
        })
        if not equal_ok:
            raise ReplError(f"memcmp equal case returned 0x{equal_return:x}, expected 0")

        observed_left = _peek_bytes(session, left_ptr, scan_len)
        observed_right_equal = _peek_bytes(session, right_ptr, scan_len)
        equal_buffers_unchanged = observed_left == expected_left_scan and observed_right_equal == expected_right_equal_scan
        checks.append({
            "check": "memcmp-equal-buffer-immutability",
            "ok": equal_buffers_unchanged,
            "left_unchanged": observed_left == expected_left_scan,
            "right_unchanged": observed_right_equal == expected_right_equal_scan,
        })
        if not equal_buffers_unchanged:
            raise ReplError("memcmp equal case modified an owned buffer")

        _poke_bytes(session, right_ptr, expected_right_mismatch_scan)
        observed_right_mismatch = _peek_bytes(session, right_ptr, scan_len)
        mismatch_setup_ok = observed_right_mismatch == expected_right_mismatch_scan
        checks.append({
            "check": "owned-memcmp-mismatch-poke-peek",
            "ok": mismatch_setup_ok,
            "mismatch_offset": MEMCMP_MISMATCH_OFFSET,
            "left_byte": f"0x{MEMCMP_PROOF_BYTES[MEMCMP_MISMATCH_OFFSET]:02x}",
            "right_byte": f"0x{MEMCMP_MISMATCH_RIGHT_BYTE:02x}",
        })
        if not mismatch_setup_ok:
            raise ReplError("owned memcmp mismatch buffer poke/peek mismatch")

        mismatch_return = session.call_runtime(memcmp_runtime, (left_ptr, right_ptr, MEMCMP_PROOF_SIZE))
        mismatch_positive = 0 < mismatch_return < 0x80000000
        checks.append({
            "check": "memcmp-mismatch-return-contract",
            "ok": mismatch_positive,
            "expected_return_sign": "positive",
            "observed_return": f"0x{mismatch_return:x}",
            "mismatch_offset": MEMCMP_MISMATCH_OFFSET,
            "left_byte": f"0x{MEMCMP_PROOF_BYTES[MEMCMP_MISMATCH_OFFSET]:02x}",
            "right_byte": f"0x{MEMCMP_MISMATCH_RIGHT_BYTE:02x}",
        })
        if not mismatch_positive:
            raise ReplError(f"memcmp mismatch case returned 0x{mismatch_return:x}, expected positive int")

        observed_left = _peek_bytes(session, left_ptr, scan_len)
        observed_right_mismatch = _peek_bytes(session, right_ptr, scan_len)
        mismatch_buffers_unchanged = (
            observed_left == expected_left_scan
            and observed_right_mismatch == expected_right_mismatch_scan
        )
        checks.append({
            "check": "memcmp-mismatch-buffer-immutability",
            "ok": mismatch_buffers_unchanged,
            "left_unchanged": observed_left == expected_left_scan,
            "right_unchanged": observed_right_mismatch == expected_right_mismatch_scan,
        })
        if not mismatch_buffers_unchanged:
            raise ReplError("memcmp mismatch case modified an owned buffer")
    finally:
        if kfree_runtime:
            for label, ptr in (("left", left_ptr), ("right", right_ptr)):
                if ptr and is_kernel_lowmem_pointer(ptr):
                    free_attempted.append(label)
                    try:
                        session.call_runtime(kfree_runtime, (ptr,))
                        free_ok[label] = True
                    except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                        free_errors.append(f"{label}:{exc}")
        session.set_panic_on_oops(1)

    cleanup_ok = bool(free_ok["left"] and free_ok["right"])
    checks.append({
        "check": "kfree-owned-memcmp-buffers",
        "ok": cleanup_ok,
        "free_attempted": free_attempted,
        "left_free_ok": free_ok["left"],
        "right_free_ok": free_ok["right"],
    })
    if free_errors:
        raise ReplError(f"kfree failed after memcmp proof: {free_errors}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-memcmp-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "memcmp",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["memcmp"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["memcmp"]["return_contract"],
        "alloc_size": alloc_size,
        "proof_bytes_label": MEMCMP_PROOF_BYTES.decode("ascii"),
        "size_arg": MEMCMP_PROOF_SIZE,
        "equal_expected_return_value": "0x0",
        "equal_observed_return_value": f"0x{equal_return:x}",
        "mismatch_expected_return_sign": "positive",
        "mismatch_observed_return_value": f"0x{mismatch_return:x}",
        "mismatch_offset": MEMCMP_MISMATCH_OFFSET,
        "mismatch_left_byte": f"0x{MEMCMP_PROOF_BYTES[MEMCMP_MISMATCH_OFFSET]:02x}",
        "mismatch_right_byte": f"0x{MEMCMP_MISMATCH_RIGHT_BYTE:02x}",
        "buffers_unchanged_after_calls": True,
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source),
        "call_safety": call_safety,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "observed_bytes_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "memcmp",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["memcmp"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["memcmp"]["return_contract"],
            "observed_return_value": "equal=0x0,mismatch=positive",
            "cleanup": "kfree-owned-memcmp-buffers-ok" if cleanup_ok else "cleanup-failed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "memcmp_runtime": f"0x{((memcmp_link + slide) & MASK64):x}",
        "left_ptr": f"0x{left_ptr:x}",
        "right_ptr": f"0x{right_ptr:x}",
        "left_bytes_hex": observed_left.hex(),
        "right_equal_bytes_hex": observed_right_equal.hex(),
        "right_mismatch_bytes_hex": observed_right_mismatch.hex(),
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def _run_call_proof_strcmp(session: ReplSession,
                           symbols: dict[str, Symbol],
                           image: StaticImage,
                           *,
                           alloc_size: int,
                           source_root: Path,
                           gfp: int,
                           gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    scan_len = len(STRCMP_PROOF_BYTES) + STRCMP_CANARY_LEN
    if alloc_size < scan_len:
        raise ReplError(f"strcmp call-proof alloc_size must be at least {scan_len} bytes")

    if STRCMP_MISMATCH_OFFSET >= len(STRCMP_PROOF_BYTES) - 1:
        raise ReplError("strcmp mismatch offset must be inside the non-NUL string body")
    if STRCMP_MISMATCH_RIGHT_BYTE == 0:
        raise ReplError("strcmp mismatch right byte must not terminate the proof string")
    if STRCMP_PROOF_BYTES[STRCMP_MISMATCH_OFFSET] <= STRCMP_MISMATCH_RIGHT_BYTE:
        raise ReplError("strcmp mismatch right byte must be less than left byte for positive sign proof")

    source = lookup_source_signature("strcmp", source_root=source_root)
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        "strcmp",
        ("@owned_left_string_buffer", "@owned_right_string_buffer"),
    )
    if call_safety.get("tier") != CALL_PROOF_TARGETS["strcmp"]["expected_tier"]:
        raise ReplError("strcmp call-safety tier is not the expected vetted pointer tier")
    if not source.get("found") or source.get("pointer_arg_indices") != [0, 1]:
        raise ReplError("strcmp source signature does not declare x0/x1 as pointer arguments")

    resolutions = {
        "strcmp": resolve_verified(symbols, image, "strcmp", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    strcmp_link = require_verified_resolution(resolutions["strcmp"], "call-proof target")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof string allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof string cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    right_mismatch = bytearray(STRCMP_PROOF_BYTES)
    right_mismatch[STRCMP_MISMATCH_OFFSET] = STRCMP_MISMATCH_RIGHT_BYTE
    right_mismatch_bytes = bytes(right_mismatch)
    expected_left_scan = STRCMP_PROOF_BYTES + (b"\xcc" * STRCMP_CANARY_LEN)
    expected_right_equal_scan = expected_left_scan
    expected_right_mismatch_scan = right_mismatch_bytes + (b"\xcc" * STRCMP_CANARY_LEN)

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "strcmp",
            "resolution_method": resolutions["strcmp"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source.get("selected", {}).get("signature")
            if isinstance(source.get("selected"), dict) else None,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
        },
    ]
    private: dict[str, object] = {}
    left_ptr = 0
    right_ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted: list[str] = []
    free_ok: dict[str, bool] = {"left": False, "right": False}
    free_errors: list[str] = []
    equal_return = 0
    mismatch_return = 0
    observed_left = b""
    observed_right_equal = b""
    observed_right_mismatch = b""

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        strcmp_runtime = (strcmp_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        left_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        right_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        left_ok = is_kernel_lowmem_pointer(left_ptr)
        right_ok = is_kernel_lowmem_pointer(right_ptr)
        distinct_ok = left_ptr != right_ptr
        checks.append({
            "check": "kmalloc-owned-strcmp-strings",
            "ok": left_ok and right_ok and distinct_ok,
            "alloc_size": alloc_size,
            "left_kernel_lowmem": left_ok,
            "right_kernel_lowmem": right_ok,
            "distinct_strings": distinct_ok,
        })
        if not (left_ok and right_ok and distinct_ok):
            raise ReplError("__kmalloc did not return sane distinct strcmp strings")

        _poke_bytes(session, left_ptr, expected_left_scan)
        _poke_bytes(session, right_ptr, expected_right_equal_scan)
        observed_left = _peek_bytes(session, left_ptr, scan_len)
        observed_right_equal = _peek_bytes(session, right_ptr, scan_len)
        setup_ok = observed_left == expected_left_scan and observed_right_equal == expected_right_equal_scan
        checks.append({
            "check": "owned-strcmp-string-poke-peek",
            "ok": setup_ok,
            "proof_string": STRCMP_PROOF_LABEL,
            "canary_len": STRCMP_CANARY_LEN,
        })
        if not setup_ok:
            raise ReplError("owned strcmp string poke/peek mismatch")

        equal_return = session.call_runtime(strcmp_runtime, (left_ptr, right_ptr))
        equal_ok = equal_return == 0
        checks.append({
            "check": "strcmp-equal-return-contract",
            "ok": equal_ok,
            "expected_return": "0x0",
            "observed_return": f"0x{equal_return:x}",
        })
        if not equal_ok:
            raise ReplError(f"strcmp equal case returned 0x{equal_return:x}, expected 0")

        observed_left = _peek_bytes(session, left_ptr, scan_len)
        observed_right_equal = _peek_bytes(session, right_ptr, scan_len)
        equal_strings_unchanged = (
            observed_left == expected_left_scan
            and observed_right_equal == expected_right_equal_scan
        )
        checks.append({
            "check": "strcmp-equal-string-immutability",
            "ok": equal_strings_unchanged,
            "left_unchanged": observed_left == expected_left_scan,
            "right_unchanged": observed_right_equal == expected_right_equal_scan,
        })
        if not equal_strings_unchanged:
            raise ReplError("strcmp equal case modified an owned string")

        _poke_bytes(session, right_ptr, expected_right_mismatch_scan)
        observed_right_mismatch = _peek_bytes(session, right_ptr, scan_len)
        mismatch_setup_ok = observed_right_mismatch == expected_right_mismatch_scan
        checks.append({
            "check": "owned-strcmp-mismatch-poke-peek",
            "ok": mismatch_setup_ok,
            "mismatch_offset": STRCMP_MISMATCH_OFFSET,
            "left_byte": f"0x{STRCMP_PROOF_BYTES[STRCMP_MISMATCH_OFFSET]:02x}",
            "right_byte": f"0x{STRCMP_MISMATCH_RIGHT_BYTE:02x}",
        })
        if not mismatch_setup_ok:
            raise ReplError("owned strcmp mismatch string poke/peek mismatch")

        mismatch_return = session.call_runtime(strcmp_runtime, (left_ptr, right_ptr))
        mismatch_positive = 0 < mismatch_return < 0x80000000
        checks.append({
            "check": "strcmp-mismatch-return-contract",
            "ok": mismatch_positive,
            "expected_return_sign": "positive",
            "observed_return": f"0x{mismatch_return:x}",
            "mismatch_offset": STRCMP_MISMATCH_OFFSET,
            "left_byte": f"0x{STRCMP_PROOF_BYTES[STRCMP_MISMATCH_OFFSET]:02x}",
            "right_byte": f"0x{STRCMP_MISMATCH_RIGHT_BYTE:02x}",
        })
        if not mismatch_positive:
            raise ReplError(f"strcmp mismatch case returned 0x{mismatch_return:x}, expected positive int")

        observed_left = _peek_bytes(session, left_ptr, scan_len)
        observed_right_mismatch = _peek_bytes(session, right_ptr, scan_len)
        mismatch_strings_unchanged = (
            observed_left == expected_left_scan
            and observed_right_mismatch == expected_right_mismatch_scan
        )
        checks.append({
            "check": "strcmp-mismatch-string-immutability",
            "ok": mismatch_strings_unchanged,
            "left_unchanged": observed_left == expected_left_scan,
            "right_unchanged": observed_right_mismatch == expected_right_mismatch_scan,
        })
        if not mismatch_strings_unchanged:
            raise ReplError("strcmp mismatch case modified an owned string")
    finally:
        if kfree_runtime:
            for label, ptr in (("left", left_ptr), ("right", right_ptr)):
                if ptr and is_kernel_lowmem_pointer(ptr):
                    free_attempted.append(label)
                    try:
                        session.call_runtime(kfree_runtime, (ptr,))
                        free_ok[label] = True
                    except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                        free_errors.append(f"{label}:{exc}")
        session.set_panic_on_oops(1)

    cleanup_ok = bool(free_ok["left"] and free_ok["right"])
    checks.append({
        "check": "kfree-owned-strcmp-strings",
        "ok": cleanup_ok,
        "free_attempted": free_attempted,
        "left_free_ok": free_ok["left"],
        "right_free_ok": free_ok["right"],
    })
    if free_errors:
        raise ReplError(f"kfree failed after strcmp proof: {free_errors}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-strcmp-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "strcmp",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["strcmp"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["strcmp"]["return_contract"],
        "alloc_size": alloc_size,
        "proof_string": STRCMP_PROOF_LABEL,
        "equal_expected_return_value": "0x0",
        "equal_observed_return_value": f"0x{equal_return:x}",
        "mismatch_expected_return_sign": "positive",
        "mismatch_observed_return_value": f"0x{mismatch_return:x}",
        "mismatch_offset": STRCMP_MISMATCH_OFFSET,
        "mismatch_left_byte": f"0x{STRCMP_PROOF_BYTES[STRCMP_MISMATCH_OFFSET]:02x}",
        "mismatch_right_byte": f"0x{STRCMP_MISMATCH_RIGHT_BYTE:02x}",
        "strings_unchanged_after_calls": True,
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source),
        "call_safety": call_safety,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "observed_bytes_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "strcmp",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["strcmp"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["strcmp"]["return_contract"],
            "observed_return_value": "equal=0x0,mismatch=positive",
            "cleanup": "kfree-owned-strcmp-strings-ok" if cleanup_ok else "cleanup-failed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "strcmp_runtime": f"0x{((strcmp_link + slide) & MASK64):x}",
        "left_ptr": f"0x{left_ptr:x}",
        "right_ptr": f"0x{right_ptr:x}",
        "left_bytes_hex": observed_left.hex(),
        "right_equal_bytes_hex": observed_right_equal.hex(),
        "right_mismatch_bytes_hex": observed_right_mismatch.hex(),
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def _run_call_proof_strrchr(session: ReplSession,
                            symbols: dict[str, Symbol],
                            image: StaticImage,
                            *,
                            alloc_size: int,
                            source_root: Path,
                            gfp: int,
                            gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    scan_len = len(STRRCHR_PROOF_BYTES) + STRRCHR_CANARY_LEN
    if alloc_size < scan_len:
        raise ReplError(f"strrchr call-proof alloc_size must be at least {scan_len} bytes")
    if STRRCHR_EXPECTED_OFFSET < 0:
        raise ReplError("strrchr proof search byte is not present in the proof string")
    if STRRCHR_MISSING_BYTE in STRRCHR_PROOF_BYTES:
        raise ReplError("strrchr missing-byte proof value is present in the proof string")

    source = lookup_source_signature("strrchr", source_root=source_root)
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        "strrchr",
        ("@owned_string_buffer", STRRCHR_SEARCH_BYTE),
    )
    if call_safety.get("tier") != CALL_PROOF_TARGETS["strrchr"]["expected_tier"]:
        raise ReplError("strrchr call-safety tier is not the expected vetted pointer tier")
    if not source.get("found") or source.get("pointer_arg_indices") != [0]:
        raise ReplError("strrchr source signature does not declare x0 as the string pointer argument")

    resolutions = {
        "strrchr": resolve_verified(symbols, image, "strrchr", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    strrchr_link = require_verified_resolution(resolutions["strrchr"], "call-proof target")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof string allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof string cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    expected_scan = STRRCHR_PROOF_BYTES + (b"\xcc" * STRRCHR_CANARY_LEN)
    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "strrchr",
            "resolution_method": resolutions["strrchr"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source.get("selected", {}).get("signature")
            if isinstance(source.get("selected"), dict) else None,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
            "search_byte": f"0x{STRRCHR_SEARCH_BYTE:02x}",
        },
    ]
    private: dict[str, object] = {}
    ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted = False
    free_ok = False
    free_error = ""
    hit_return = 0
    miss_return = 0
    observed = b""

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        strrchr_runtime = (strrchr_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        ptr_ok = is_kernel_lowmem_pointer(ptr)
        checks.append({
            "check": "kmalloc-owned-strrchr-string-buffer",
            "ok": ptr_ok,
            "alloc_size": alloc_size,
            "kernel_lowmem": ptr_ok,
        })
        if not ptr_ok:
            raise ReplError("__kmalloc did not return a sane strrchr string buffer")

        _poke_bytes(session, ptr, expected_scan)
        observed = _peek_bytes(session, ptr, scan_len)
        setup_ok = observed == expected_scan
        checks.append({
            "check": "owned-strrchr-string-poke-peek",
            "ok": setup_ok,
            "proof_string": STRRCHR_PROOF_LABEL,
            "canary_len": STRRCHR_CANARY_LEN,
        })
        if not setup_ok:
            raise ReplError("owned strrchr string poke/peek mismatch")

        hit_return = session.call_runtime(strrchr_runtime, (ptr, STRRCHR_SEARCH_BYTE))
        expected_hit_return = (ptr + STRRCHR_EXPECTED_OFFSET) & MASK64
        hit_ok = hit_return == expected_hit_return
        checks.append({
            "check": "strrchr-hit-return-contract",
            "ok": hit_ok,
            "search_byte": f"0x{STRRCHR_SEARCH_BYTE:02x}",
            "expected_offset": STRRCHR_EXPECTED_OFFSET,
            "return_matches_expected_offset": hit_ok,
        })
        if not hit_ok:
            raise ReplError(
                "strrchr hit case returned an unexpected pointer "
                f"(expected offset {STRRCHR_EXPECTED_OFFSET})"
            )

        observed = _peek_bytes(session, ptr, scan_len)
        hit_unchanged = observed == expected_scan
        checks.append({
            "check": "strrchr-hit-string-immutability",
            "ok": hit_unchanged,
            "string_unchanged": hit_unchanged,
        })
        if not hit_unchanged:
            raise ReplError("strrchr hit case modified the owned string buffer")

        miss_return = session.call_runtime(strrchr_runtime, (ptr, STRRCHR_MISSING_BYTE))
        miss_ok = miss_return == 0
        checks.append({
            "check": "strrchr-miss-return-contract",
            "ok": miss_ok,
            "missing_byte": f"0x{STRRCHR_MISSING_BYTE:02x}",
            "expected_return": "0x0",
            "observed_return": f"0x{miss_return:x}",
        })
        if not miss_ok:
            raise ReplError(f"strrchr miss case returned 0x{miss_return:x}, expected 0")

        observed = _peek_bytes(session, ptr, scan_len)
        miss_unchanged = observed == expected_scan
        checks.append({
            "check": "strrchr-miss-string-immutability",
            "ok": miss_unchanged,
            "string_unchanged": miss_unchanged,
        })
        if not miss_unchanged:
            raise ReplError("strrchr miss case modified the owned string buffer")
    finally:
        if ptr and is_kernel_lowmem_pointer(ptr) and kfree_runtime:
            free_attempted = True
            try:
                session.call_runtime(kfree_runtime, (ptr,))
                free_ok = True
            except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                free_error = str(exc)
        session.set_panic_on_oops(1)

    checks.append({
        "check": "kfree-owned-strrchr-string-buffer",
        "ok": free_ok,
        "free_attempted": free_attempted,
    })
    if free_error:
        raise ReplError(f"kfree failed after strrchr proof: {free_error}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-strrchr-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "strrchr",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["strrchr"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["strrchr"]["return_contract"],
        "alloc_size": alloc_size,
        "proof_string": STRRCHR_PROOF_LABEL,
        "search_byte": f"0x{STRRCHR_SEARCH_BYTE:02x}",
        "expected_hit_offset": STRRCHR_EXPECTED_OFFSET,
        "hit_expected_return_value": "owned-string-pointer-plus-offset-redacted",
        "hit_observed_return_value": "owned-string-pointer-plus-offset-redacted",
        "return_matches_expected_offset": hit_return == ((ptr + STRRCHR_EXPECTED_OFFSET) & MASK64),
        "missing_byte": f"0x{STRRCHR_MISSING_BYTE:02x}",
        "missing_expected_return_value": "0x0",
        "missing_observed_return_value": f"0x{miss_return:x}",
        "string_unchanged_after_calls": True,
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source),
        "call_safety": call_safety,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "observed_bytes_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "strrchr",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["strrchr"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["strrchr"]["return_contract"],
            "observed_return_value": f"hit-offset={STRRCHR_EXPECTED_OFFSET},miss=0x0",
            "cleanup": "kfree-owned-strrchr-string-buffer-ok" if free_ok else "cleanup-failed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "strrchr_runtime": f"0x{((strrchr_link + slide) & MASK64):x}",
        "alloc_ptr": f"0x{ptr:x}",
        "hit_return_ptr": f"0x{hit_return:x}",
        "observed_bytes_hex": observed.hex(),
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def _run_call_proof_memset(session: ReplSession,
                           symbols: dict[str, Symbol],
                           image: StaticImage,
                           *,
                           alloc_size: int,
                           source_root: Path,
                           gfp: int,
                           gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    scan_len = MEMSET_PROOF_SIZE + MEMSET_CANARY_LEN
    if alloc_size < scan_len:
        raise ReplError(f"memset call-proof alloc_size must be at least {scan_len} bytes")

    source = lookup_source_signature("memset", source_root=source_root)
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        "memset",
        ("@owned_destination_buffer", MEMSET_PROOF_BYTE, MEMSET_PROOF_SIZE),
    )
    if call_safety.get("tier") != CALL_PROOF_TARGETS["memset"]["expected_tier"]:
        raise ReplError("memset call-safety tier is not the expected vetted pointer tier")
    if not source.get("found") or source.get("pointer_arg_indices") != [0]:
        raise ReplError("memset source signature does not declare x0 as the destination pointer argument")

    resolutions = {
        "memset": resolve_verified(symbols, image, "memset", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    memset_link = require_verified_resolution(resolutions["memset"], "call-proof target")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof buffer allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof buffer cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    initial_scan = (bytes([MEMSET_INITIAL_BYTE]) * MEMSET_PROOF_SIZE) + (b"\xcc" * MEMSET_CANARY_LEN)
    expected_scan = (bytes([MEMSET_PROOF_BYTE]) * MEMSET_PROOF_SIZE) + (b"\xcc" * MEMSET_CANARY_LEN)
    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "memset",
            "resolution_method": resolutions["memset"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source.get("selected", {}).get("signature")
            if isinstance(source.get("selected"), dict) else None,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
            "fill_byte": f"0x{MEMSET_PROOF_BYTE:02x}",
            "bounded_size": MEMSET_PROOF_SIZE,
        },
    ]
    private: dict[str, object] = {}
    ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted = False
    free_ok = False
    free_error = ""
    return_ptr = 0
    observed_before = b""
    observed_after = b""

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        memset_runtime = (memset_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        ptr_ok = is_kernel_lowmem_pointer(ptr)
        checks.append({
            "check": "kmalloc-owned-memset-destination-buffer",
            "ok": ptr_ok,
            "alloc_size": alloc_size,
            "kernel_lowmem": ptr_ok,
        })
        if not ptr_ok:
            raise ReplError("__kmalloc did not return a sane memset destination buffer")

        _poke_bytes(session, ptr, initial_scan)
        observed_before = _peek_bytes(session, ptr, scan_len)
        setup_ok = observed_before == initial_scan
        checks.append({
            "check": "owned-memset-destination-poke-peek",
            "ok": setup_ok,
            "initial_byte": f"0x{MEMSET_INITIAL_BYTE:02x}",
            "fill_byte": f"0x{MEMSET_PROOF_BYTE:02x}",
            "size_arg": MEMSET_PROOF_SIZE,
            "canary_len": MEMSET_CANARY_LEN,
        })
        if not setup_ok:
            raise ReplError("owned memset destination poke/peek mismatch")

        return_ptr = session.call_runtime(memset_runtime, (ptr, MEMSET_PROOF_BYTE, MEMSET_PROOF_SIZE))
        return_ok = return_ptr == ptr
        checks.append({
            "check": "memset-return-contract",
            "ok": return_ok,
            "return_matches_destination": return_ok,
        })
        if not return_ok:
            raise ReplError("memset did not return the owned destination pointer")

        observed_after = _peek_bytes(session, ptr, scan_len)
        fill_ok = observed_after[:MEMSET_PROOF_SIZE] == bytes([MEMSET_PROOF_BYTE]) * MEMSET_PROOF_SIZE
        canary_ok = observed_after[MEMSET_PROOF_SIZE:] == b"\xcc" * MEMSET_CANARY_LEN
        checks.append({
            "check": "memset-fill-and-canary-contract",
            "ok": fill_ok and canary_ok,
            "filled_size": MEMSET_PROOF_SIZE,
            "fill_byte": f"0x{MEMSET_PROOF_BYTE:02x}",
            "prefix_filled": fill_ok,
            "post_size_canary_preserved": canary_ok,
        })
        if not (fill_ok and canary_ok):
            raise ReplError("memset fill bytes or post-size canary did not match contract")
    finally:
        if ptr and is_kernel_lowmem_pointer(ptr) and kfree_runtime:
            free_attempted = True
            try:
                session.call_runtime(kfree_runtime, (ptr,))
                free_ok = True
            except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                free_error = str(exc)
        session.set_panic_on_oops(1)

    checks.append({
        "check": "kfree-owned-memset-destination-buffer",
        "ok": free_ok,
        "free_attempted": free_attempted,
    })
    if free_error:
        raise ReplError(f"kfree failed after memset proof: {free_error}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-memset-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "memset",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["memset"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["memset"]["return_contract"],
        "alloc_size": alloc_size,
        "size_arg": MEMSET_PROOF_SIZE,
        "fill_byte": f"0x{MEMSET_PROOF_BYTE:02x}",
        "initial_byte": f"0x{MEMSET_INITIAL_BYTE:02x}",
        "expected_return_value": "owned-destination-pointer-redacted",
        "observed_return_value": "owned-destination-pointer-redacted",
        "return_matches_destination": return_ptr == ptr,
        "filled_size": MEMSET_PROOF_SIZE,
        "post_size_canary_preserved": True,
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source),
        "call_safety": call_safety,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "observed_bytes_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "memset",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["memset"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["memset"]["return_contract"],
            "observed_return_value": "owned-destination-pointer-redacted,filled-size=32",
            "cleanup": "kfree-owned-memset-destination-buffer-ok" if free_ok else "cleanup-failed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "memset_runtime": f"0x{((memset_link + slide) & MASK64):x}",
        "dst_ptr": f"0x{ptr:x}",
        "return_ptr": f"0x{return_ptr:x}",
        "observed_before_hex": observed_before.hex(),
        "observed_after_hex": observed_after.hex(),
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def _run_call_proof_strlen(session: ReplSession,
                           symbols: dict[str, Symbol],
                           image: StaticImage,
                           *,
                           alloc_size: int,
                           source_root: Path,
                           gfp: int,
                           gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    if alloc_size < STRLEN_ZERO_FILL_LEN:
        raise ReplError(
            f"strlen call-proof alloc_size must be at least {STRLEN_ZERO_FILL_LEN} bytes"
        )

    source = lookup_source_signature("strlen", source_root=source_root)
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        "strlen",
        ("@owned_string_buffer",),
    )
    if call_safety.get("tier") != CALL_PROOF_TARGETS["strlen"]["expected_tier"]:
        raise ReplError("strlen call-safety tier is not the expected vetted pointer tier")
    if not source.get("found") or source.get("pointer_arg_indices") != [0]:
        raise ReplError("strlen source signature does not declare x0 as string pointer")

    resolutions = {
        "strlen": resolve_verified(symbols, image, "strlen", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    strlen_link = require_verified_resolution(resolutions["strlen"], "call-proof target")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof string allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof string cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "strlen",
            "resolution_method": resolutions["strlen"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source.get("selected", {}).get("signature")
            if isinstance(source.get("selected"), dict) else None,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
        },
    ]
    private: dict[str, object] = {}
    ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted = False
    free_ok = False
    free_error = ""
    proof_return = 0
    observed_bytes = b""

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        strlen_runtime = (strlen_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        ptr_ok = is_kernel_lowmem_pointer(ptr)
        checks.append({
            "check": "kmalloc-owned-string-buffer",
            "ok": ptr_ok,
            "alloc_size": alloc_size,
            "kernel_lowmem": ptr_ok,
        })
        if not ptr_ok:
            raise ReplError("__kmalloc did not return a sane string buffer pointer")

        _poke_bytes(session, ptr, b"\x00" * STRLEN_ZERO_FILL_LEN)
        _poke_bytes(session, ptr, STRLEN_PROOF_BYTES)
        observed_bytes = _peek_bytes(session, ptr, len(STRLEN_PROOF_BYTES))
        payload_ok = observed_bytes == STRLEN_PROOF_BYTES
        checks.append({
            "check": "owned-string-poke-peek",
            "ok": payload_ok,
            "string": STRLEN_PROOF_BYTES[:-1].decode("ascii"),
            "nul_terminated": observed_bytes.endswith(b"\x00"),
            "zero_fill_len": STRLEN_ZERO_FILL_LEN,
        })
        if not payload_ok:
            raise ReplError("owned strlen string poke/peek mismatch")

        proof_return = session.call_runtime(strlen_runtime, (ptr,))
        return_ok = proof_return == STRLEN_PROOF_EXPECTED
        checks.append({
            "check": "strlen-return-contract",
            "ok": return_ok,
            "return_kind": "size_t",
            "return_value": f"0x{proof_return:x}",
            "expected_return": f"0x{STRLEN_PROOF_EXPECTED:x}",
        })
        if not return_ok:
            raise ReplError(
                f"strlen returned 0x{proof_return:x}, expected 0x{STRLEN_PROOF_EXPECTED:x}"
            )
    finally:
        if ptr and is_kernel_lowmem_pointer(ptr) and kfree_runtime:
            free_attempted = True
            try:
                session.call_runtime(kfree_runtime, (ptr,))
                free_ok = True
            except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                free_error = str(exc)
        session.set_panic_on_oops(1)

    checks.append({
        "check": "kfree-owned-string-buffer",
        "ok": free_ok,
        "free_attempted": free_attempted,
    })
    if free_error:
        raise ReplError(f"kfree failed after strlen proof: {free_error}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-strlen-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "strlen",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["strlen"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["strlen"]["return_contract"],
        "alloc_size": alloc_size,
        "proof_string": STRLEN_PROOF_BYTES[:-1].decode("ascii"),
        "expected_return_value": f"0x{STRLEN_PROOF_EXPECTED:x}",
        "observed_return_value": f"0x{proof_return:x}",
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source),
        "call_safety": call_safety,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "strlen",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["strlen"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["strlen"]["return_contract"],
            "observed_return_value": f"0x{proof_return:x}",
            "cleanup": "kfree-owned-string-buffer-ok" if free_ok else "cleanup-failed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "strlen_runtime": f"0x{((strlen_link + slide) & MASK64):x}",
        "alloc_ptr": f"0x{ptr:x}",
        "observed_bytes_hex": observed_bytes.hex(),
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def _run_call_proof_strscpy(session: ReplSession,
                            symbols: dict[str, Symbol],
                            image: StaticImage,
                            *,
                            alloc_size: int,
                            source_root: Path,
                            gfp: int,
                            gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    required_alloc = max(STRSCPY_SRC_ZERO_FILL_LEN, STRSCPY_PROOF_SIZE + STRSCPY_DST_CANARY_LEN)
    if alloc_size < required_alloc:
        raise ReplError(
            f"strscpy call-proof alloc_size must be at least {required_alloc} bytes"
        )

    source = lookup_source_signature("strscpy", source_root=source_root)
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        "strscpy",
        ("@owned_destination_buffer", "@owned_source_string_buffer", STRSCPY_PROOF_SIZE),
    )
    if call_safety.get("tier") != CALL_PROOF_TARGETS["strscpy"]["expected_tier"]:
        raise ReplError("strscpy call-safety tier is not the expected vetted pointer tier")
    if not source.get("found") or source.get("pointer_arg_indices") != [0, 1]:
        raise ReplError("strscpy source signature does not declare x0/x1 as pointer arguments")

    resolutions = {
        "strscpy": resolve_verified(symbols, image, "strscpy", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    strscpy_link = require_verified_resolution(resolutions["strscpy"], "call-proof target")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof string allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof string cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "strscpy",
            "resolution_method": resolutions["strscpy"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source.get("selected", {}).get("signature")
            if isinstance(source.get("selected"), dict) else None,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
            "bounded_size": STRSCPY_PROOF_SIZE,
        },
    ]
    private: dict[str, object] = {}
    dst_ptr = 0
    src_ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted: list[str] = []
    free_ok: dict[str, bool] = {"dst": False, "src": False}
    free_errors: list[str] = []
    proof_return = 0
    observed_src = b""
    observed_dst = b""
    dst_scan_len = STRSCPY_PROOF_SIZE + STRSCPY_DST_CANARY_LEN

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        strscpy_runtime = (strscpy_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        dst_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        src_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        dst_ok = is_kernel_lowmem_pointer(dst_ptr)
        src_ok = is_kernel_lowmem_pointer(src_ptr)
        distinct_ok = dst_ptr != src_ptr
        checks.append({
            "check": "kmalloc-owned-strscpy-buffers",
            "ok": dst_ok and src_ok and distinct_ok,
            "alloc_size": alloc_size,
            "dst_kernel_lowmem": dst_ok,
            "src_kernel_lowmem": src_ok,
            "distinct_buffers": distinct_ok,
        })
        if not (dst_ok and src_ok and distinct_ok):
            raise ReplError("__kmalloc did not return sane distinct strscpy buffers")

        _poke_bytes(session, dst_ptr, b"\xcc" * dst_scan_len)
        _poke_bytes(session, src_ptr, b"\x00" * STRSCPY_SRC_ZERO_FILL_LEN)
        _poke_bytes(session, src_ptr, STRSCPY_PROOF_SRC_BYTES)
        observed_src = _peek_bytes(session, src_ptr, len(STRSCPY_PROOF_SRC_BYTES))
        src_payload_ok = observed_src == STRSCPY_PROOF_SRC_BYTES
        checks.append({
            "check": "owned-strscpy-source-poke-peek",
            "ok": src_payload_ok,
            "string": STRSCPY_PROOF_SRC_BYTES[:-1].decode("ascii"),
            "nul_terminated": observed_src.endswith(b"\x00"),
            "size_arg": STRSCPY_PROOF_SIZE,
        })
        if not src_payload_ok:
            raise ReplError("owned strscpy source poke/peek mismatch")

        proof_return = session.call_runtime(strscpy_runtime, (dst_ptr, src_ptr, STRSCPY_PROOF_SIZE))
        return_ok = proof_return == STRSCPY_PROOF_EXPECTED
        checks.append({
            "check": "strscpy-return-contract",
            "ok": return_ok,
            "return_kind": "ssize_t",
            "return_value": f"0x{proof_return:x}",
            "expected_return": f"0x{STRSCPY_PROOF_EXPECTED:x}",
            "size_arg": STRSCPY_PROOF_SIZE,
        })
        if not return_ok:
            raise ReplError(
                f"strscpy returned 0x{proof_return:x}, expected 0x{STRSCPY_PROOF_EXPECTED:x}"
            )

        observed_dst = _peek_bytes(session, dst_ptr, dst_scan_len)
        prefix_ok = observed_dst[:len(STRSCPY_PROOF_SRC_BYTES)] == STRSCPY_PROOF_SRC_BYTES
        canary_ok = observed_dst[STRSCPY_PROOF_SIZE:dst_scan_len] == (b"\xcc" * STRSCPY_DST_CANARY_LEN)
        checks.append({
            "check": "strscpy-destination-contract",
            "ok": prefix_ok and canary_ok,
            "copied_prefix": STRSCPY_PROOF_SRC_BYTES[:-1].decode("ascii"),
            "prefix_ok": prefix_ok,
            "canary_after_size_ok": canary_ok,
        })
        if not (prefix_ok and canary_ok):
            raise ReplError("strscpy destination prefix/canary contract failed")
    finally:
        if kfree_runtime:
            for label, ptr in (("dst", dst_ptr), ("src", src_ptr)):
                if ptr and is_kernel_lowmem_pointer(ptr):
                    free_attempted.append(label)
                    try:
                        session.call_runtime(kfree_runtime, (ptr,))
                        free_ok[label] = True
                    except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                        free_errors.append(f"{label}:{exc}")
        session.set_panic_on_oops(1)

    cleanup_ok = bool(free_ok["dst"] and free_ok["src"])
    checks.append({
        "check": "kfree-owned-strscpy-buffers",
        "ok": cleanup_ok,
        "free_attempted": free_attempted,
        "dst_free_ok": free_ok["dst"],
        "src_free_ok": free_ok["src"],
    })
    if free_errors:
        raise ReplError(f"kfree failed after strscpy proof: {free_errors}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-strscpy-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "strscpy",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["strscpy"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["strscpy"]["return_contract"],
        "alloc_size": alloc_size,
        "proof_string": STRSCPY_PROOF_SRC_BYTES[:-1].decode("ascii"),
        "size_arg": STRSCPY_PROOF_SIZE,
        "expected_return_value": f"0x{STRSCPY_PROOF_EXPECTED:x}",
        "observed_return_value": f"0x{proof_return:x}",
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source),
        "call_safety": call_safety,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "strscpy",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["strscpy"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["strscpy"]["return_contract"],
            "observed_return_value": f"0x{proof_return:x}",
            "cleanup": "kfree-owned-strscpy-buffers-ok" if cleanup_ok else "cleanup-failed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "strscpy_runtime": f"0x{((strscpy_link + slide) & MASK64):x}",
        "dst_ptr": f"0x{dst_ptr:x}",
        "src_ptr": f"0x{src_ptr:x}",
        "observed_src_hex": observed_src.hex(),
        "observed_dst_hex": observed_dst.hex(),
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def _run_call_proof_strlcpy(session: ReplSession,
                            symbols: dict[str, Symbol],
                            image: StaticImage,
                            *,
                            alloc_size: int,
                            source_root: Path,
                            gfp: int,
                            gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    required_alloc = max(STRLCPY_SRC_ZERO_FILL_LEN, STRLCPY_PROOF_SIZE + STRLCPY_DST_CANARY_LEN)
    if alloc_size < required_alloc:
        raise ReplError(
            f"strlcpy call-proof alloc_size must be at least {required_alloc} bytes"
        )

    source = lookup_source_signature("strlcpy", source_root=source_root)
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        "strlcpy",
        ("@owned_destination_buffer", "@owned_source_string_buffer", STRLCPY_PROOF_SIZE),
    )
    if call_safety.get("tier") != CALL_PROOF_TARGETS["strlcpy"]["expected_tier"]:
        raise ReplError("strlcpy call-safety tier is not the expected vetted pointer tier")
    if not source.get("found") or source.get("pointer_arg_indices") != [0, 1]:
        raise ReplError("strlcpy source signature does not declare x0/x1 as pointer arguments")

    resolutions = {
        "strlcpy": resolve_verified(symbols, image, "strlcpy", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    strlcpy_link = require_verified_resolution(resolutions["strlcpy"], "call-proof target")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof string allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof string cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "strlcpy",
            "resolution_method": resolutions["strlcpy"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source.get("selected", {}).get("signature")
            if isinstance(source.get("selected"), dict) else None,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
            "bounded_size": STRLCPY_PROOF_SIZE,
        },
    ]
    private: dict[str, object] = {}
    dst_ptr = 0
    src_ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted: list[str] = []
    free_ok: dict[str, bool] = {"dst": False, "src": False}
    free_errors: list[str] = []
    proof_return = 0
    observed_src = b""
    observed_dst = b""
    dst_scan_len = STRLCPY_PROOF_SIZE + STRLCPY_DST_CANARY_LEN

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        strlcpy_runtime = (strlcpy_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        dst_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        src_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        dst_ok = is_kernel_lowmem_pointer(dst_ptr)
        src_ok = is_kernel_lowmem_pointer(src_ptr)
        distinct_ok = dst_ptr != src_ptr
        checks.append({
            "check": "kmalloc-owned-strlcpy-buffers",
            "ok": dst_ok and src_ok and distinct_ok,
            "alloc_size": alloc_size,
            "dst_kernel_lowmem": dst_ok,
            "src_kernel_lowmem": src_ok,
            "distinct_buffers": distinct_ok,
        })
        if not (dst_ok and src_ok and distinct_ok):
            raise ReplError("__kmalloc did not return sane distinct strlcpy buffers")

        _poke_bytes(session, dst_ptr, b"\xcc" * dst_scan_len)
        _poke_bytes(session, src_ptr, b"\x00" * STRLCPY_SRC_ZERO_FILL_LEN)
        _poke_bytes(session, src_ptr, STRLCPY_PROOF_SRC_BYTES)
        observed_src = _peek_bytes(session, src_ptr, len(STRLCPY_PROOF_SRC_BYTES))
        src_payload_ok = observed_src == STRLCPY_PROOF_SRC_BYTES
        checks.append({
            "check": "owned-strlcpy-source-poke-peek",
            "ok": src_payload_ok,
            "string": STRLCPY_PROOF_SRC_BYTES[:-1].decode("ascii"),
            "nul_terminated": observed_src.endswith(b"\x00"),
            "size_arg": STRLCPY_PROOF_SIZE,
        })
        if not src_payload_ok:
            raise ReplError("owned strlcpy source poke/peek mismatch")

        proof_return = session.call_runtime(strlcpy_runtime, (dst_ptr, src_ptr, STRLCPY_PROOF_SIZE))
        return_ok = proof_return == STRLCPY_PROOF_EXPECTED
        checks.append({
            "check": "strlcpy-return-contract",
            "ok": return_ok,
            "return_kind": "size_t",
            "return_value": f"0x{proof_return:x}",
            "expected_return": f"0x{STRLCPY_PROOF_EXPECTED:x}",
            "size_arg": STRLCPY_PROOF_SIZE,
        })
        if not return_ok:
            raise ReplError(
                f"strlcpy returned 0x{proof_return:x}, expected 0x{STRLCPY_PROOF_EXPECTED:x}"
            )

        observed_dst = _peek_bytes(session, dst_ptr, dst_scan_len)
        prefix_ok = observed_dst[:len(STRLCPY_PROOF_SRC_BYTES)] == STRLCPY_PROOF_SRC_BYTES
        canary_ok = observed_dst[STRLCPY_PROOF_SIZE:dst_scan_len] == (b"\xcc" * STRLCPY_DST_CANARY_LEN)
        checks.append({
            "check": "strlcpy-destination-contract",
            "ok": prefix_ok and canary_ok,
            "copied_prefix": STRLCPY_PROOF_SRC_BYTES[:-1].decode("ascii"),
            "prefix_ok": prefix_ok,
            "canary_after_size_ok": canary_ok,
        })
        if not (prefix_ok and canary_ok):
            raise ReplError("strlcpy destination prefix/canary contract failed")
    finally:
        if kfree_runtime:
            for label, ptr in (("dst", dst_ptr), ("src", src_ptr)):
                if ptr and is_kernel_lowmem_pointer(ptr):
                    free_attempted.append(label)
                    try:
                        session.call_runtime(kfree_runtime, (ptr,))
                        free_ok[label] = True
                    except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                        free_errors.append(f"{label}:{exc}")
        session.set_panic_on_oops(1)

    cleanup_ok = bool(free_ok["dst"] and free_ok["src"])
    checks.append({
        "check": "kfree-owned-strlcpy-buffers",
        "ok": cleanup_ok,
        "free_attempted": free_attempted,
        "dst_free_ok": free_ok["dst"],
        "src_free_ok": free_ok["src"],
    })
    if free_errors:
        raise ReplError(f"kfree failed after strlcpy proof: {free_errors}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-strlcpy-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "strlcpy",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["strlcpy"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["strlcpy"]["return_contract"],
        "alloc_size": alloc_size,
        "proof_string": STRLCPY_PROOF_SRC_BYTES[:-1].decode("ascii"),
        "size_arg": STRLCPY_PROOF_SIZE,
        "expected_return_value": f"0x{STRLCPY_PROOF_EXPECTED:x}",
        "observed_return_value": f"0x{proof_return:x}",
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source),
        "call_safety": call_safety,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "strlcpy",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["strlcpy"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["strlcpy"]["return_contract"],
            "observed_return_value": f"0x{proof_return:x}",
            "cleanup": "kfree-owned-strlcpy-buffers-ok" if cleanup_ok else "cleanup-failed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "strlcpy_runtime": f"0x{((strlcpy_link + slide) & MASK64):x}",
        "dst_ptr": f"0x{dst_ptr:x}",
        "src_ptr": f"0x{src_ptr:x}",
        "observed_src_hex": observed_src.hex(),
        "observed_dst_hex": observed_dst.hex(),
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def _run_call_proof_strncpy(session: ReplSession,
                            symbols: dict[str, Symbol],
                            image: StaticImage,
                            *,
                            alloc_size: int,
                            source_root: Path,
                            gfp: int,
                            gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    required_alloc = max(STRNCPY_SRC_ZERO_FILL_LEN, STRNCPY_PROOF_SIZE + STRNCPY_DST_CANARY_LEN)
    if alloc_size < required_alloc:
        raise ReplError(
            f"strncpy call-proof alloc_size must be at least {required_alloc} bytes"
        )

    source = lookup_source_signature("strncpy", source_root=source_root)
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        "strncpy",
        ("@owned_destination_buffer", "@owned_source_string_buffer", STRNCPY_PROOF_SIZE),
    )
    if call_safety.get("tier") != CALL_PROOF_TARGETS["strncpy"]["expected_tier"]:
        raise ReplError("strncpy call-safety tier is not the expected vetted pointer tier")
    if not source.get("found") or source.get("pointer_arg_indices") != [0, 1]:
        raise ReplError("strncpy source signature does not declare x0/x1 as pointer arguments")

    resolutions = {
        "strncpy": resolve_verified(symbols, image, "strncpy", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    strncpy_link = require_verified_resolution(resolutions["strncpy"], "call-proof target")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof string allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof string cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "strncpy",
            "resolution_method": resolutions["strncpy"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source.get("selected", {}).get("signature")
            if isinstance(source.get("selected"), dict) else None,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
            "bounded_count": STRNCPY_PROOF_SIZE,
        },
    ]
    private: dict[str, object] = {}
    dst_ptr = 0
    src_ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted: list[str] = []
    free_ok: dict[str, bool] = {"dst": False, "src": False}
    free_errors: list[str] = []
    proof_return = 0
    observed_src = b""
    observed_dst = b""
    dst_scan_len = STRNCPY_PROOF_SIZE + STRNCPY_DST_CANARY_LEN

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        strncpy_runtime = (strncpy_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        dst_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        src_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        dst_ok = is_kernel_lowmem_pointer(dst_ptr)
        src_ok = is_kernel_lowmem_pointer(src_ptr)
        distinct_ok = dst_ptr != src_ptr
        checks.append({
            "check": "kmalloc-owned-strncpy-buffers",
            "ok": dst_ok and src_ok and distinct_ok,
            "alloc_size": alloc_size,
            "dst_kernel_lowmem": dst_ok,
            "src_kernel_lowmem": src_ok,
            "distinct_buffers": distinct_ok,
        })
        if not (dst_ok and src_ok and distinct_ok):
            raise ReplError("__kmalloc did not return sane distinct strncpy buffers")

        _poke_bytes(session, dst_ptr, b"\xcc" * dst_scan_len)
        _poke_bytes(session, src_ptr, b"\x00" * STRNCPY_SRC_ZERO_FILL_LEN)
        _poke_bytes(session, src_ptr, STRNCPY_PROOF_SRC_BYTES)
        observed_src = _peek_bytes(session, src_ptr, len(STRNCPY_PROOF_SRC_BYTES))
        src_payload_ok = observed_src == STRNCPY_PROOF_SRC_BYTES
        checks.append({
            "check": "owned-strncpy-source-poke-peek",
            "ok": src_payload_ok,
            "string": STRNCPY_PROOF_SRC_BYTES[:-1].decode("ascii"),
            "nul_terminated": observed_src.endswith(b"\x00"),
            "count_arg": STRNCPY_PROOF_SIZE,
        })
        if not src_payload_ok:
            raise ReplError("owned strncpy source poke/peek mismatch")

        proof_return = session.call_runtime(strncpy_runtime, (dst_ptr, src_ptr, STRNCPY_PROOF_SIZE))
        return_ok = proof_return == dst_ptr
        checks.append({
            "check": "strncpy-return-contract",
            "ok": return_ok,
            "return_kind": "char-pointer",
            "return_matches_destination": return_ok,
            "return_value_redacted": True,
            "expected_return": "owned-destination-pointer-redacted",
            "count_arg": STRNCPY_PROOF_SIZE,
        })
        if not return_ok:
            raise ReplError("strncpy did not return the owned destination pointer")

        observed_dst = _peek_bytes(session, dst_ptr, dst_scan_len)
        prefix_ok = observed_dst[:len(STRNCPY_PROOF_SRC_BYTES)] == STRNCPY_PROOF_SRC_BYTES
        padding_start = len(STRNCPY_PROOF_SRC_BYTES)
        padding_ok = observed_dst[padding_start:STRNCPY_PROOF_SIZE] == (
            b"\x00" * (STRNCPY_PROOF_SIZE - padding_start)
        )
        canary_ok = observed_dst[STRNCPY_PROOF_SIZE:dst_scan_len] == (b"\xcc" * STRNCPY_DST_CANARY_LEN)
        checks.append({
            "check": "strncpy-destination-contract",
            "ok": prefix_ok and padding_ok and canary_ok,
            "copied_prefix": STRNCPY_PROOF_SRC_BYTES[:-1].decode("ascii"),
            "prefix_ok": prefix_ok,
            "nul_padding_to_count_ok": padding_ok,
            "canary_after_count_ok": canary_ok,
        })
        if not (prefix_ok and padding_ok and canary_ok):
            raise ReplError("strncpy destination prefix/padding/canary contract failed")
    finally:
        if kfree_runtime:
            for label, ptr in (("dst", dst_ptr), ("src", src_ptr)):
                if ptr and is_kernel_lowmem_pointer(ptr):
                    free_attempted.append(label)
                    try:
                        session.call_runtime(kfree_runtime, (ptr,))
                        free_ok[label] = True
                    except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                        free_errors.append(f"{label}:{exc}")
        session.set_panic_on_oops(1)

    cleanup_ok = bool(free_ok["dst"] and free_ok["src"])
    checks.append({
        "check": "kfree-owned-strncpy-buffers",
        "ok": cleanup_ok,
        "free_attempted": free_attempted,
        "dst_free_ok": free_ok["dst"],
        "src_free_ok": free_ok["src"],
    })
    if free_errors:
        raise ReplError(f"kfree failed after strncpy proof: {free_errors}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-strncpy-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "strncpy",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["strncpy"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["strncpy"]["return_contract"],
        "alloc_size": alloc_size,
        "proof_string": STRNCPY_PROOF_SRC_BYTES[:-1].decode("ascii"),
        "count_arg": STRNCPY_PROOF_SIZE,
        "return_matches_destination": proof_return == dst_ptr,
        "expected_return_value": "owned-destination-pointer-redacted",
        "observed_return_value": "owned-destination-pointer-redacted" if proof_return == dst_ptr else "unexpected-pointer-redacted",
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source),
        "call_safety": call_safety,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "strncpy",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["strncpy"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["strncpy"]["return_contract"],
            "observed_return_value": "owned-destination-pointer-redacted",
            "cleanup": "kfree-owned-strncpy-buffers-ok" if cleanup_ok else "cleanup-failed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "strncpy_runtime": f"0x{((strncpy_link + slide) & MASK64):x}",
        "dst_ptr": f"0x{dst_ptr:x}",
        "src_ptr": f"0x{src_ptr:x}",
        "return_ptr": f"0x{proof_return:x}",
        "observed_src_hex": observed_src.hex(),
        "observed_dst_hex": observed_dst.hex(),
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def _run_call_proof_strnlen(session: ReplSession,
                            symbols: dict[str, Symbol],
                            image: StaticImage,
                            *,
                            alloc_size: int,
                            source_root: Path,
                            gfp: int,
                            gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    if alloc_size < STRNLEN_PROOF_MAXLEN:
        raise ReplError(
            f"strnlen call-proof alloc_size must be at least {STRNLEN_PROOF_MAXLEN} bytes"
        )

    source = lookup_source_signature("strnlen", source_root=source_root)
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        "strnlen",
        ("@owned_string_buffer", STRNLEN_PROOF_MAXLEN),
    )
    if call_safety.get("tier") != CALL_PROOF_TARGETS["strnlen"]["expected_tier"]:
        raise ReplError("strnlen call-safety tier is not the expected vetted pointer tier")
    if not source.get("found") or source.get("pointer_arg_indices") != [0]:
        raise ReplError("strnlen source signature does not declare x0 as string pointer")

    resolutions = {
        "strnlen": resolve_verified(symbols, image, "strnlen", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    strnlen_link = require_verified_resolution(resolutions["strnlen"], "call-proof target")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof string allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof string cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "strnlen",
            "resolution_method": resolutions["strnlen"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source.get("selected", {}).get("signature")
            if isinstance(source.get("selected"), dict) else None,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
        },
    ]
    private: dict[str, object] = {}
    ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted = False
    free_ok = False
    free_error = ""
    proof_return = 0
    observed_bytes = b""

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        strnlen_runtime = (strnlen_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        ptr_ok = is_kernel_lowmem_pointer(ptr)
        checks.append({
            "check": "kmalloc-owned-string-buffer",
            "ok": ptr_ok,
            "alloc_size": alloc_size,
            "kernel_lowmem": ptr_ok,
        })
        if not ptr_ok:
            raise ReplError("__kmalloc did not return a sane string buffer pointer")

        _poke_bytes(session, ptr, b"\x00" * STRNLEN_PROOF_MAXLEN)
        _poke_bytes(session, ptr, STRNLEN_PROOF_BYTES)
        observed_bytes = _peek_bytes(session, ptr, len(STRNLEN_PROOF_BYTES))
        payload_ok = observed_bytes == STRNLEN_PROOF_BYTES
        checks.append({
            "check": "owned-string-poke-peek",
            "ok": payload_ok,
            "string": STRNLEN_PROOF_BYTES[:-1].decode("ascii"),
            "nul_terminated": observed_bytes.endswith(b"\x00"),
        })
        if not payload_ok:
            raise ReplError("owned strnlen string poke/peek mismatch")

        proof_return = session.call_runtime(strnlen_runtime, (ptr, STRNLEN_PROOF_MAXLEN))
        return_ok = proof_return == STRNLEN_PROOF_EXPECTED
        checks.append({
            "check": "strnlen-return-contract",
            "ok": return_ok,
            "return_kind": "size_t",
            "return_value": f"0x{proof_return:x}",
            "expected_return": f"0x{STRNLEN_PROOF_EXPECTED:x}",
            "maxlen": f"0x{STRNLEN_PROOF_MAXLEN:x}",
        })
        if not return_ok:
            raise ReplError(
                f"strnlen returned 0x{proof_return:x}, expected 0x{STRNLEN_PROOF_EXPECTED:x}"
            )
    finally:
        if ptr and is_kernel_lowmem_pointer(ptr) and kfree_runtime:
            free_attempted = True
            try:
                session.call_runtime(kfree_runtime, (ptr,))
                free_ok = True
            except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                free_error = str(exc)
        session.set_panic_on_oops(1)

    checks.append({
        "check": "kfree-owned-string-buffer",
        "ok": free_ok,
        "free_attempted": free_attempted,
    })
    if free_error:
        raise ReplError(f"kfree failed after strnlen proof: {free_error}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-strnlen-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "strnlen",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["strnlen"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["strnlen"]["return_contract"],
        "alloc_size": alloc_size,
        "proof_string": STRNLEN_PROOF_BYTES[:-1].decode("ascii"),
        "maxlen": STRNLEN_PROOF_MAXLEN,
        "expected_return_value": f"0x{STRNLEN_PROOF_EXPECTED:x}",
        "observed_return_value": f"0x{proof_return:x}",
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source),
        "call_safety": call_safety,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "strnlen",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["strnlen"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["strnlen"]["return_contract"],
            "observed_return_value": f"0x{proof_return:x}",
            "cleanup": "kfree-owned-string-buffer-ok" if free_ok else "cleanup-failed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "strnlen_runtime": f"0x{((strnlen_link + slide) & MASK64):x}",
        "alloc_ptr": f"0x{ptr:x}",
        "observed_bytes_hex": observed_bytes.hex(),
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def _run_call_proof_filp_open(session: ReplSession,
                              symbols: dict[str, Symbol],
                              image: StaticImage,
                              *,
                              alloc_size: int,
                              source_root: Path,
                              gfp: int,
                              gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    if alloc_size < 64:
        raise ReplError("filp_open call-proof alloc_size must be at least 64 bytes")

    source_open = lookup_source_signature("filp_open", source_root=source_root)
    source_close = lookup_source_signature("filp_close", source_root=source_root)
    call_safety_open = require_call_safety_for_call(
        symbols,
        image,
        "filp_open",
        ("@owned_pathname_ptr", FILP_OPEN_PROOF_FLAGS, FILP_OPEN_PROOF_MODE),
    )
    call_safety_close = require_call_safety_for_call(
        symbols,
        image,
        "filp_close",
        ("@filp_open_result", 0),
    )
    if call_safety_open.get("tier") != CALL_PROOF_TARGETS["filp_open"]["expected_tier"]:
        raise ReplError("filp_open call-safety tier is not the expected vetted pointer tier")
    if call_safety_close.get("tier") != CALL_SAFETY_SAFE_WITH_VALID_PTR:
        raise ReplError("filp_close cleanup tier is not the expected vetted pointer tier")
    if not source_open.get("found") or source_open.get("pointer_arg_indices") != [0]:
        raise ReplError("filp_open source signature does not declare x0 as pathname pointer")
    if not source_close.get("found") or source_close.get("pointer_arg_indices") != [0]:
        raise ReplError("filp_close source signature does not declare x0 as struct file pointer")

    resolutions = {
        "filp_open": resolve_verified(symbols, image, "filp_open", purpose="call", allow_pre_arg_deref=True),
        "filp_close": resolve_verified(symbols, image, "filp_close", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    filp_open_link = require_verified_resolution(resolutions["filp_open"], "call-proof target")
    filp_close_link = require_verified_resolution(resolutions["filp_close"], "call-proof cleanup")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof pathname allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof pathname cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "filp_open",
            "resolution_method": resolutions["filp_open"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source_open.get("selected", {}).get("signature")
            if isinstance(source_open.get("selected"), dict) else None,
            "pointer_arg_indices": source_open.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety_open.get("tier"),
            "required_valid_pointer_args": call_safety_open.get("required_valid_pointer_args", {}),
        },
        {
            "check": "static-cleanup-contract",
            "ok": True,
            "cleanup_symbol": "filp_close",
            "tier": call_safety_close.get("tier"),
            "source_signature": source_close.get("selected", {}).get("signature")
            if isinstance(source_close.get("selected"), dict) else None,
        },
    ]
    private: dict[str, object] = {}
    path_ptr = 0
    file_ptr = 0
    slide = 0
    kfree_runtime = 0
    filp_close_runtime = 0
    close_attempted = False
    close_ok = False
    close_return = 0
    close_error = ""
    free_attempted = False
    free_ok = False
    free_error = ""

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        filp_open_runtime = (filp_open_link + slide) & MASK64
        filp_close_runtime = (filp_close_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        path_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        path_ok = is_kernel_lowmem_pointer(path_ptr)
        checks.append({
            "check": "kmalloc-owned-pathname-buffer",
            "ok": path_ok,
            "alloc_size": alloc_size,
            "kernel_lowmem": path_ok,
        })
        if not path_ok:
            raise ReplError("__kmalloc did not return a sane pathname buffer pointer")

        path_payload = FILP_OPEN_PROOF_PATH.ljust(16, b"\x00")
        _poke_bytes(session, path_ptr, path_payload)
        first_qword = session.peek_runtime(path_ptr, 8)
        first_expected = int.from_bytes(path_payload[:8], "little")
        path_written = first_qword == first_expected
        checks.append({
            "check": "owned-pathname-poke-peek",
            "ok": path_written,
            "path_redacted": False,
            "path": FILP_OPEN_PROOF_PATH[:-1].decode("ascii"),
        })
        if not path_written:
            raise ReplError("owned pathname poke/peek mismatch")

        file_ptr = session.call_runtime(
            filp_open_runtime,
            (path_ptr, FILP_OPEN_PROOF_FLAGS, FILP_OPEN_PROOF_MODE),
        )
        file_ok = is_kernel_lowmem_pointer(file_ptr) and not _is_kernel_err_ptr(file_ptr)
        checks.append({
            "check": "filp-open-return-contract",
            "ok": file_ok,
            "return_kind": "struct-file-or-errptr",
            "not_null": file_ptr != 0,
            "not_err_ptr": not _is_kernel_err_ptr(file_ptr),
            "kernel_lowmem": is_kernel_lowmem_pointer(file_ptr),
        })
        if not file_ok:
            raise ReplError("filp_open did not return a sane struct file pointer")

        close_attempted = True
        close_return = session.call_runtime(filp_close_runtime, (file_ptr, 0))
        close_ok = close_return == 0
        checks.append({
            "check": "filp-close-opened-file",
            "ok": close_ok,
            "return_kind": "int",
            "return_value": f"0x{close_return:x}",
        })
        if not close_ok:
            raise ReplError(f"filp_close returned 0x{close_return:x}, expected 0")
    finally:
        if file_ptr and is_kernel_lowmem_pointer(file_ptr) and not _is_kernel_err_ptr(file_ptr) and not close_ok and filp_close_runtime:
            close_attempted = True
            try:
                close_return = session.call_runtime(filp_close_runtime, (file_ptr, 0))
                close_ok = close_return == 0
            except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                close_error = str(exc)
        if path_ptr and is_kernel_lowmem_pointer(path_ptr) and kfree_runtime:
            free_attempted = True
            try:
                session.call_runtime(kfree_runtime, (path_ptr,))
                free_ok = True
            except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                free_error = str(exc)
        session.set_panic_on_oops(1)

    checks.append({
        "check": "kfree-owned-pathname-buffer",
        "ok": free_ok,
        "free_attempted": free_attempted,
    })
    if close_error:
        raise ReplError(f"filp_close cleanup failed after filp_open proof: {close_error}")
    if free_error:
        raise ReplError(f"kfree failed after filp_open proof: {free_error}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-filp_open-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "filp_open",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["filp_open"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["filp_open"]["return_contract"],
        "alloc_size": alloc_size,
        "pathname": FILP_OPEN_PROOF_PATH[:-1].decode("ascii"),
        "open_flags": FILP_OPEN_PROOF_FLAGS,
        "open_mode": FILP_OPEN_PROOF_MODE,
        "close_return_value": f"0x{close_return:x}",
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source_open),
        "cleanup_source_evidence": _source_row_evidence(source_close),
        "call_safety": call_safety_open,
        "cleanup_call_safety": call_safety_close,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "filp_open",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["filp_open"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["filp_open"]["return_contract"],
            "observed_return": "sane-struct-file-pointer",
            "cleanup": "filp_close-returned-0",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
        "paired_cleanup_function_map_entry": {
            "symbol": "filp_close",
            "status": "cleanup-live-proven",
            "trusted_input_contract": "struct file pointer returned by filp_open proof",
            "return_contract": "int == 0",
            "observed_return_value": f"0x{close_return:x}",
            "auto_call_policy": "cleanup-only-not-general-file-close-allowlist",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "filp_open_runtime": f"0x{((filp_open_link + slide) & MASK64):x}",
        "filp_close_runtime": f"0x{((filp_close_link + slide) & MASK64):x}",
        "path_ptr": f"0x{path_ptr:x}",
        "file_ptr": f"0x{file_ptr:x}",
        "close_attempted": close_attempted,
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def _run_call_proof_kernel_read(session: ReplSession,
                                symbols: dict[str, Symbol],
                                image: StaticImage,
                                *,
                                alloc_size: int,
                                source_root: Path,
                                gfp: int,
                                gfp_components: dict[str, int]) -> tuple[dict[str, object], dict[str, object]]:
    if alloc_size < 64:
        raise ReplError("kernel_read call-proof alloc_size must be at least 64 bytes")

    source_read = lookup_source_signature("kernel_read", source_root=source_root)
    source_open = lookup_source_signature("filp_open", source_root=source_root)
    source_close = lookup_source_signature("filp_close", source_root=source_root)
    call_safety_read = require_call_safety_for_call(
        symbols,
        image,
        "kernel_read",
        ("@filp_open_result", "@owned_read_buffer", KERNEL_READ_PROOF_LEN, "@owned_loff_t_pos"),
    )
    call_safety_open = require_call_safety_for_call(
        symbols,
        image,
        "filp_open",
        ("@owned_pathname_ptr", FILP_OPEN_PROOF_FLAGS, FILP_OPEN_PROOF_MODE),
    )
    call_safety_close = require_call_safety_for_call(
        symbols,
        image,
        "filp_close",
        ("@filp_open_result", 0),
    )
    if call_safety_read.get("tier") != CALL_PROOF_TARGETS["kernel_read"]["expected_tier"]:
        raise ReplError("kernel_read call-safety tier is not the expected vetted pointer tier")
    if call_safety_open.get("tier") != CALL_SAFETY_SAFE_WITH_VALID_PTR:
        raise ReplError("filp_open setup tier is not the expected vetted pointer tier")
    if call_safety_close.get("tier") != CALL_SAFETY_SAFE_WITH_VALID_PTR:
        raise ReplError("filp_close cleanup tier is not the expected vetted pointer tier")
    if not source_read.get("found") or source_read.get("pointer_arg_indices") != [0, 1, 3]:
        raise ReplError("kernel_read source signature does not declare x0/x1/x3 as pointer arguments")
    if not source_open.get("found") or source_open.get("pointer_arg_indices") != [0]:
        raise ReplError("filp_open source signature does not declare x0 as pathname pointer")
    if not source_close.get("found") or source_close.get("pointer_arg_indices") != [0]:
        raise ReplError("filp_close source signature does not declare x0 as struct file pointer")

    resolutions = {
        "kernel_read": resolve_verified(symbols, image, "kernel_read", purpose="call", allow_pre_arg_deref=True),
        "filp_open": resolve_verified(symbols, image, "filp_open", purpose="call", allow_pre_arg_deref=True),
        "filp_close": resolve_verified(symbols, image, "filp_close", purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    kernel_read_link = require_verified_resolution(resolutions["kernel_read"], "call-proof target")
    filp_open_link = require_verified_resolution(resolutions["filp_open"], "call-proof file open")
    filp_close_link = require_verified_resolution(resolutions["filp_close"], "call-proof file close")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof allocator cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": "kernel_read",
            "resolution_method": resolutions["kernel_read"].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source_read.get("selected", {}).get("signature")
            if isinstance(source_read.get("selected"), dict) else None,
            "pointer_arg_indices": source_read.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety_read.get("tier"),
            "required_valid_pointer_args": call_safety_read.get("required_valid_pointer_args", {}),
        },
    ]
    private: dict[str, object] = {}
    slide = 0
    path_ptr = 0
    read_ptr = 0
    pos_ptr = 0
    file_ptr = 0
    kfree_runtime = 0
    filp_close_runtime = 0
    close_attempted = False
    close_ok = False
    close_return = 0
    close_error = ""
    freed: list[str] = []
    free_errors: list[str] = []
    read_return = 0
    read_data = b""
    pos_after = 0

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        kernel_read_runtime = (kernel_read_link + slide) & MASK64
        filp_open_runtime = (filp_open_link + slide) & MASK64
        filp_close_runtime = (filp_close_link + slide) & MASK64
        kmalloc_runtime = (kmalloc_link + slide) & MASK64
        kfree_runtime = (kfree_link + slide) & MASK64

        path_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        read_ptr = session.call_runtime(kmalloc_runtime, (alloc_size, gfp))
        pos_ptr = session.call_runtime(kmalloc_runtime, (64, gfp))
        allocated_ok = all(is_kernel_lowmem_pointer(ptr) for ptr in (path_ptr, read_ptr, pos_ptr))
        checks.append({
            "check": "kmalloc-owned-read-contract-buffers",
            "ok": allocated_ok,
            "path_kernel_lowmem": is_kernel_lowmem_pointer(path_ptr),
            "read_kernel_lowmem": is_kernel_lowmem_pointer(read_ptr),
            "pos_kernel_lowmem": is_kernel_lowmem_pointer(pos_ptr),
        })
        if not allocated_ok:
            raise ReplError("__kmalloc did not return sane kernel lowmem pointers for read proof")

        path_payload = FILP_OPEN_PROOF_PATH.ljust(16, b"\x00")
        _poke_bytes(session, path_ptr, path_payload)
        _poke_bytes(session, read_ptr, b"\x00" * KERNEL_READ_PROOF_LEN)
        session.poke_runtime(pos_ptr, 0, 8)
        path_written = session.peek_runtime(path_ptr, 8) == int.from_bytes(path_payload[:8], "little")
        pos_zero = session.peek_runtime(pos_ptr, 8) == 0
        checks.append({
            "check": "owned-inputs-initialized",
            "ok": path_written and pos_zero,
            "path": FILP_OPEN_PROOF_PATH[:-1].decode("ascii"),
            "pos_zero": pos_zero,
        })
        if not path_written or not pos_zero:
            raise ReplError("owned kernel_read inputs were not initialized correctly")

        file_ptr = session.call_runtime(
            filp_open_runtime,
            (path_ptr, FILP_OPEN_PROOF_FLAGS, FILP_OPEN_PROOF_MODE),
        )
        file_ok = is_kernel_lowmem_pointer(file_ptr) and not _is_kernel_err_ptr(file_ptr)
        checks.append({
            "check": "filp-open-return-contract",
            "ok": file_ok,
            "return_kind": "struct-file-or-errptr",
            "not_null": file_ptr != 0,
            "not_err_ptr": not _is_kernel_err_ptr(file_ptr),
            "kernel_lowmem": is_kernel_lowmem_pointer(file_ptr),
        })
        if not file_ok:
            raise ReplError("filp_open did not return a sane struct file pointer")

        read_return = session.call_runtime(
            kernel_read_runtime,
            (file_ptr, read_ptr, KERNEL_READ_PROOF_LEN, pos_ptr),
        )
        read_data = _peek_bytes(session, read_ptr, KERNEL_READ_PROOF_LEN)
        pos_after = session.peek_runtime(pos_ptr, 8)
        expected_read = KERNEL_READ_PROOF_LEN
        read_ok = read_return == expected_read
        prefix_ok = read_data.startswith(KERNEL_READ_EXPECTED_PREFIX)
        pos_ok = pos_after == expected_read
        checks.append({
            "check": "kernel-read-return-buffer-pos-contract",
            "ok": read_ok and prefix_ok and pos_ok,
            "return_kind": "ssize_t",
            "return_value": f"0x{read_return:x}",
            "expected_return": f"0x{expected_read:x}",
            "buffer_prefix": read_data[:4].hex(),
            "expected_prefix": KERNEL_READ_EXPECTED_PREFIX.hex(),
            "pos_after": f"0x{pos_after:x}",
        })
        if not read_ok or not prefix_ok or not pos_ok:
            raise ReplError(
                "kernel_read contract failed: "
                f"return=0x{read_return:x} prefix={read_data[:4].hex()} pos=0x{pos_after:x}"
            )

        close_attempted = True
        close_return = session.call_runtime(filp_close_runtime, (file_ptr, 0))
        close_ok = close_return == 0
        checks.append({
            "check": "filp-close-opened-file",
            "ok": close_ok,
            "return_kind": "int",
            "return_value": f"0x{close_return:x}",
        })
        if not close_ok:
            raise ReplError(f"filp_close returned 0x{close_return:x}, expected 0")
    finally:
        if file_ptr and is_kernel_lowmem_pointer(file_ptr) and not _is_kernel_err_ptr(file_ptr) and not close_ok and filp_close_runtime:
            close_attempted = True
            try:
                close_return = session.call_runtime(filp_close_runtime, (file_ptr, 0))
                close_ok = close_return == 0
            except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                close_error = str(exc)
        for name, ptr in (("path", path_ptr), ("read", read_ptr), ("pos", pos_ptr)):
            if ptr and is_kernel_lowmem_pointer(ptr) and kfree_runtime:
                try:
                    session.call_runtime(kfree_runtime, (ptr,))
                    freed.append(name)
                except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                    free_errors.append(f"{name}:{exc}")
        session.set_panic_on_oops(1)

    checks.append({
        "check": "kfree-owned-kernel-read-buffers",
        "ok": sorted(freed) == ["path", "pos", "read"],
        "freed": sorted(freed),
    })
    if close_error:
        raise ReplError(f"filp_close cleanup failed after kernel_read proof: {close_error}")
    if free_errors:
        raise ReplError(f"kfree failed after kernel_read proof: {free_errors}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-kernel_read-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": "kernel_read",
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS["kernel_read"]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS["kernel_read"]["return_contract"],
        "pathname": FILP_OPEN_PROOF_PATH[:-1].decode("ascii"),
        "read_len": KERNEL_READ_PROOF_LEN,
        "observed_return_value": f"0x{read_return:x}",
        "observed_prefix": read_data[:4].hex(),
        "observed_pos_after": f"0x{pos_after:x}",
        "close_return_value": f"0x{close_return:x}",
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source_read),
        "setup_source_evidence": _source_row_evidence(source_open),
        "cleanup_source_evidence": _source_row_evidence(source_close),
        "call_safety": call_safety_read,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "read_data_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": "kernel_read",
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS["kernel_read"]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS["kernel_read"]["return_contract"],
            "observed_return_value": f"0x{read_return:x}",
            "observed_prefix": read_data[:4].hex(),
            "cleanup": "filp_close-returned-0-and-owned-buffers-freed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "kernel_read_runtime": f"0x{((kernel_read_link + slide) & MASK64):x}",
        "filp_open_runtime": f"0x{((filp_open_link + slide) & MASK64):x}",
        "filp_close_runtime": f"0x{((filp_close_link + slide) & MASK64):x}",
        "path_ptr": f"0x{path_ptr:x}",
        "read_ptr": f"0x{read_ptr:x}",
        "pos_ptr": f"0x{pos_ptr:x}",
        "file_ptr": f"0x{file_ptr:x}",
        "read_data_hex": read_data.hex(),
        "close_attempted": close_attempted,
        "gfp_components": {key: f"0x{component:x}" for key, component in gfp_components.items()},
    })
    return summary, private


def run_call_proof(session: ReplSession,
                   symbols: dict[str, Symbol],
                   image: StaticImage,
                   target: str,
                   *,
                   alloc_size: int = KMALLOC_ROUNDTRIP_SIZE,
                   max_expected_return: int | None = None,
                   source_root: Path = DEFAULT_KERNEL_SOURCE_ROOT,
                   gfp_header: Path = DEFAULT_GFP_HEADER,
                   gfp_value: int | None = None) -> tuple[dict[str, object], dict[str, object]]:
    if target not in CALL_PROOF_TARGETS:
        raise ReplError(f"unsupported call-proof target {target!r}; supported={sorted(CALL_PROOF_TARGETS)}")
    if alloc_size <= 0:
        raise ReplError(f"alloc_size must be positive: {alloc_size}")
    max_return = max_expected_return if max_expected_return is not None else max(alloc_size * 2, alloc_size)
    if max_return < alloc_size:
        raise ReplError("max_expected_return must be >= alloc_size")

    gfp, gfp_components = (
        (gfp_value, {}) if gfp_value is not None else derive_gfp_kernel_value(gfp_header)
    )
    if gfp is None:
        raise ReplError("GFP_KERNEL derivation returned no value")

    if target == "filp_open":
        return _run_call_proof_filp_open(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )
    if target == "kernel_read":
        return _run_call_proof_kernel_read(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )
    if target == "strnlen":
        return _run_call_proof_strnlen(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )
    if target == "strlen":
        return _run_call_proof_strlen(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )
    if target == "strscpy":
        return _run_call_proof_strscpy(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )
    if target == "strlcpy":
        return _run_call_proof_strlcpy(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )
    if target == "strncpy":
        return _run_call_proof_strncpy(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )
    if target == "strcmp":
        return _run_call_proof_strcmp(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )
    if target == "memcmp":
        return _run_call_proof_memcmp(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )
    if target == "strrchr":
        return _run_call_proof_strrchr(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )
    if target == "memset":
        return _run_call_proof_memset(
            session,
            symbols,
            image,
            alloc_size=alloc_size,
            source_root=source_root,
            gfp=gfp,
            gfp_components=gfp_components,
        )

    source = lookup_source_signature(target, source_root=source_root)
    call_safety = require_call_safety_for_call(
        symbols,
        image,
        target,
        ("@owned_kmalloc_ptr",),
    )
    if call_safety.get("tier") != CALL_PROOF_TARGETS[target]["expected_tier"]:
        raise ReplError(f"{target} call-safety tier is not the expected vetted pointer tier")
    target_resolution_dict = call_safety.get("resolution")
    if (
        not isinstance(target_resolution_dict, dict)
        or not target_resolution_dict.get("verified")
        or target_resolution_dict.get("link_vaddr") is None
    ):
        raise ReplError(f"{target} is not verified by the C1 identity gate")
    if not source.get("found") or source.get("pointer_arg_indices") != [0]:
        raise ReplError(f"{target} source signature does not declare x0 as the owned pointer argument")

    resolutions = {
        target: resolve_verified(symbols, image, target, purpose="call", allow_pre_arg_deref=True),
        "__kmalloc": resolve_verified(symbols, image, "__kmalloc", purpose="call"),
        "kfree": resolve_verified(symbols, image, "kfree", purpose="call"),
    }
    target_link = require_verified_resolution(resolutions[target], "call-proof target")
    kmalloc_link = require_verified_resolution(resolutions["__kmalloc"], "call-proof allocator")
    kfree_link = require_verified_resolution(resolutions["kfree"], "call-proof cleanup")
    assert_no_precall_x0_pointer_deref(image, kmalloc_link, "__kmalloc")

    checks: list[dict[str, object]] = [
        {
            "check": "static-c1-identity",
            "ok": True,
            "target": target,
            "resolution_method": resolutions[target].method,
        },
        {
            "check": "static-source-contract",
            "ok": True,
            "signature": source.get("selected", {}).get("signature")
            if isinstance(source.get("selected"), dict) else None,
            "pointer_arg_indices": source.get("pointer_arg_indices", []),
        },
        {
            "check": "static-call-safety-contract",
            "ok": True,
            "tier": call_safety.get("tier"),
            "required_valid_pointer_args": call_safety.get("required_valid_pointer_args", {}),
        },
    ]
    private: dict[str, object] = {}
    ptr = 0
    slide = 0
    kfree_runtime = 0
    free_attempted = False
    free_ok = False
    free_error = ""
    proof_return = 0

    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")
        target_runtime = (target_link + slide) & MASK64
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

        proof_return = session.call_runtime(target_runtime, (ptr,))
        return_ok = alloc_size <= proof_return <= max_return
        checks.append({
            "check": "ksize-return-contract",
            "ok": return_ok,
            "return_kind": "size_t",
            "return_value": f"0x{proof_return:x}",
            "expected_min": f"0x{alloc_size:x}",
            "expected_max": f"0x{max_return:x}",
            "gte_alloc_size": proof_return >= alloc_size,
            "lte_expected_max": proof_return <= max_return,
        })
        if not return_ok:
            raise ReplError(
                f"{target} returned 0x{proof_return:x}, outside expected "
                f"[0x{alloc_size:x}, 0x{max_return:x}]"
            )
    finally:
        if ptr and is_kernel_lowmem_pointer(ptr) and kfree_runtime:
            free_attempted = True
            try:
                session.call_runtime(kfree_runtime, (ptr,))
                free_ok = True
            except Exception as exc:  # noqa: BLE001 - cleanup failures must be visible
                free_error = str(exc)
        session.set_panic_on_oops(1)

    checks.append({
        "check": "kfree-owned-buffer",
        "ok": free_ok,
        "free_attempted": free_attempted,
    })
    if free_error:
        raise ReplError(f"kfree failed after {target} proof: {free_error}")

    passed = all(bool(check.get("ok")) for check in checks)
    summary = {
        "decision": f"a90-repl-live-call-proof-{target}-{'pass' if passed else 'fail'}",
        "ok": passed,
        "target": target,
        "proof_status": "trusted-under-owned-input-contract" if passed else "failed",
        "input_contract": CALL_PROOF_TARGETS[target]["input_contract"],
        "return_contract": CALL_PROOF_TARGETS[target]["return_contract"],
        "alloc_size": alloc_size,
        "max_expected_return": f"0x{max_return:x}",
        "observed_return_value": f"0x{proof_return:x}",
        "gfp_kernel": f"0x{gfp:x}",
        "source_evidence": _source_row_evidence(source),
        "call_safety": call_safety,
        "resolutions": _redacted_resolution_set(resolutions),
        "raw_runtime_values_redacted": True,
        "owned_pointer_redacted": True,
        "checks": checks,
        "function_map_entry": {
            "symbol": target,
            "status": "live-proven",
            "trusted_input_contract": CALL_PROOF_TARGETS[target]["input_contract"],
            "return_contract": CALL_PROOF_TARGETS[target]["return_contract"],
            "observed_return_value": f"0x{proof_return:x}",
            "cleanup": "kfree-owned-buffer-ok" if free_ok else "cleanup-failed",
            "auto_call_policy": "one-target-proof-only-not-mass-call",
        },
    }
    private.update({
        "slide": f"0x{slide:x}",
        "target_runtime": f"0x{((target_link + slide) & MASK64):x}",
        "alloc_ptr": f"0x{ptr:x}",
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
        allow_unvetted_token=args.allow_unvetted,
    )
    write_evidence(args, {**summary, "_private": private})
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def cmd_call_safety_classify(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    summary = run_call_safety_classify(
        symbols,
        image,
        tuple(args.symbols),
        include_objdump=not args.no_objdump,
    )
    write_evidence(args, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def cmd_call_safety_sweep(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    summary = run_call_safety_sweep(
        symbols,
        image,
        families=tuple(args.family),
        prefixes=tuple(args.prefix),
        regexes=tuple(args.regex),
        explicit_symbols=tuple(args.symbols),
        limit=args.limit,
        source_root=args.source_root,
        include_objdump=not args.no_objdump,
    )
    write_evidence(args, summary)
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


def cmd_call_proof(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    session = make_session(args)
    summary, private = run_call_proof(
        session,
        symbols,
        image,
        args.target,
        alloc_size=args.alloc_size,
        max_expected_return=args.max_expected_return,
        source_root=args.source_root,
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


def cmd_ksymtab_audit(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    summary = run_ksymtab_abi_audit(symbols, image, focus_symbols=tuple(args.focus_symbols))
    write_evidence(args, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def parse_compare_map_arg(text: str) -> tuple[str, Path]:
    if "=" not in text:
        raise argparse.ArgumentTypeError("compare map must be LABEL=PATH")
    label, path_text = text.split("=", 1)
    if not label:
        raise argparse.ArgumentTypeError("compare map label must not be empty")
    if not path_text:
        raise argparse.ArgumentTypeError("compare map path must not be empty")
    return label, Path(path_text)


def cmd_ksymtab_ground_truth(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    compare_maps = {
        label: load_system_map(path)
        for label, path in (args.compare_map or [])
    }
    summary = run_ksymtab_ground_truth_audit(
        symbols,
        image,
        compare_symbol_maps=compare_maps,
    )
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
    p_call.add_argument(
        "xargs",
        nargs="*",
        help="x0..x7 integer args; @repl_format or @symbol tokens resolve to runtime pointers privately",
    )
    p_call.add_argument("--replay-safe", action="store_true",
                        help="allow retry on transient capture loss only for idempotent calls")
    p_call.add_argument("--allow-unvetted", default=None, metavar="TOKEN",
                        help="override non-DENY call-safety refusal with the exact U2 token")
    p_call.set_defaults(func=cmd_call)

    p_call_safety = sub.add_parser(
        "call-safety-classify",
        help="host-only U2 disasm-backed call-safety classifier",
    )
    p_call_safety.add_argument("--map", type=Path, required=True)
    p_call_safety.add_argument("--image", type=Path, default=REPO_ROOT / DEFAULT_IMAGE,
                               help="static boot image matching the verified map")
    p_call_safety.add_argument("--evidence-dir", type=Path, default=None,
                               help="private dir for raw evidence (kept out of git)")
    p_call_safety.add_argument("--no-objdump", action="store_true",
                               help="omit aarch64-linux-gnu-objdump excerpts from output")
    p_call_safety.add_argument("symbols", nargs="*",
                               help="symbols to classify; defaults to the vetted seed inventory")
    p_call_safety.set_defaults(func=cmd_call_safety_classify)

    p_call_safety_sweep = sub.add_parser(
        "call-safety-sweep",
        help="host-only U3 advisory source+disasm call-safety family sweep",
    )
    p_call_safety_sweep.add_argument("--map", type=Path, required=True)
    p_call_safety_sweep.add_argument("--image", type=Path, default=REPO_ROOT / DEFAULT_IMAGE,
                                     help="static boot image matching the verified map")
    p_call_safety_sweep.add_argument("--source-root", type=Path, default=DEFAULT_KERNEL_SOURCE_ROOT,
                                     help="offline kernel source tree for signature xref")
    p_call_safety_sweep.add_argument("--evidence-dir", type=Path, default=None,
                                     help="private dir for raw evidence (kept out of git)")
    p_call_safety_sweep.add_argument("--family", action="append", default=[],
                                     choices=sorted(CALL_SAFETY_SWEEP_FAMILIES),
                                     help="bounded built-in family selector")
    p_call_safety_sweep.add_argument("--prefix", action="append", default=[],
                                     help="add function-name prefix selector")
    p_call_safety_sweep.add_argument("--regex", action="append", default=[],
                                     help="add function-name regex selector")
    p_call_safety_sweep.add_argument("--limit", type=int, default=60,
                                     help="cap swept symbol count after stable sorting; 0 means no cap")
    p_call_safety_sweep.add_argument("--no-objdump", action="store_true",
                                     help="omit full objdump excerpts from output")
    p_call_safety_sweep.add_argument("symbols", nargs="*",
                                     help="explicit symbols to include in the advisory sweep")
    p_call_safety_sweep.set_defaults(func=cmd_call_safety_sweep)

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

    p_call_proof = sub.add_parser(
        "call-proof",
        help="one-target live-call proof with an internally-owned input contract",
    )
    add_common(p_call_proof)
    p_call_proof.add_argument("target", choices=sorted(CALL_PROOF_TARGETS))
    p_call_proof.add_argument("--alloc-size", type=parse_int_auto, default=KMALLOC_ROUNDTRIP_SIZE)
    p_call_proof.add_argument("--max-expected-return", type=parse_int_auto, default=None,
                              help="upper bound for target return contract; default is alloc_size*2")
    p_call_proof.add_argument("--source-root", type=Path, default=DEFAULT_KERNEL_SOURCE_ROOT,
                              help="offline kernel source tree for signature xref")
    p_call_proof.add_argument("--gfp-header", type=Path, default=DEFAULT_GFP_HEADER)
    p_call_proof.add_argument("--gfp", type=parse_int_auto, default=None,
                              help="override GFP value; default derives GFP_KERNEL from --gfp-header")
    p_call_proof.set_defaults(func=cmd_call_proof)

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

    p_ksymtab = sub.add_parser(
        "ksymtab-audit",
        help="host-only v2c C2D audit for source-ABI kernel_symbol rows vs noisy 0x403 table",
    )
    add_common(p_ksymtab)
    p_ksymtab.add_argument("--focus-symbols", nargs="+", default=list(KSYMTAB_ABI_AUDIT_FOCUS))
    p_ksymtab.set_defaults(func=cmd_ksymtab_audit)

    p_ksymtab_gt = sub.add_parser(
        "ksymtab-ground-truth",
        help="host-only v2c C2E relocated __ksymtab oracle and authoritative drift report",
    )
    add_common(p_ksymtab_gt)
    p_ksymtab_gt.add_argument(
        "--compare-map",
        action="append",
        type=parse_compare_map_arg,
        default=[],
        metavar="LABEL=PATH",
        help="optional extra System.map to compare against the relocated ksymtab oracle",
    )
    p_ksymtab_gt.set_defaults(func=cmd_ksymtab_ground_truth)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
