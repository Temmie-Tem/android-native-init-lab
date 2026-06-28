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
`__kmalloc` buffer it owns, verifies via `peek`, then calls `kfree`. Per-boot
raw runtime pointers and the slide are kept out of stdout and committed
artifacts; only symbolic PASS/FAIL and link-relative facts are surfaced.
Private evidence (with raw values) is written under workspace/private when
--evidence-dir is given.
"""
from __future__ import annotations

import argparse
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
KERNEL_LOWMEM_MIN = 0xFFFFFFC000000000
KERNEL_LOWMEM_MAX = 0xFFFFFFFFFFFFFFFF

A64_BL_MASK = 0xFC000000
A64_BL = 0x94000000
A64_LDR64_UNSIGNED_BASE = 0xF9400000
A64_LDR32_UNSIGNED_BASE = 0xB9400000
A64_LDRB_UNSIGNED_BASE = 0x39400000
A64_LDRH_UNSIGNED_BASE = 0x79400000
A64_LDR_UNSIGNED_MASK = 0xFFC003E0

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


# ----------------------------------------------------------------------------
# Live REPL transport
# ----------------------------------------------------------------------------
class ReplError(RuntimeError):
    pass


@dataclass
class ReplConfig:
    host: str = a90ctl.DEFAULT_HOST
    port: int = a90ctl.DEFAULT_PORT
    busybox: str = DEFAULT_BUSYBOX
    timeout: float = 25.0
    dmesg_tail: int = DEFAULT_DMESG_TAIL
    settle_sec: float = 0.4


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

    def _op_values(self, op: int, args: tuple[int, ...] = ()) -> list[int]:
        buf = build_cmd_buffer(op, args)
        # Write + read in a single shell so the kernel-log ring cannot drain
        # between the two; the newest A90R line is this op's result.
        text = self._run_sh(op_sh(buf, self.config.busybox), allow_error=True)
        values = parse_a90r_values(text)
        if not values:
            raise ReplError(f"no A90R output captured for op={op} args={args}")
        return values

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
                            xargs: tuple[int, ...] = ()) -> list[int]:
        if len(xargs) > 8:
            raise ValueError(f"too many call args (max x0..x7): {len(xargs)}")
        args = (target_runtime & MASK64, *(value & MASK64 for value in xargs))
        return self._op_values(OP_CALL, args)

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


def _is_a64_unsigned_load_from_x0(word: int) -> bool:
    # LDR/LD(R)B/H unsigned-immediate with Rn == x0/w0. This intentionally
    # covers only the simple scalar-allocator hazard seen live: the candidate
    # treats x0 as a context pointer before any helper call can sanitize it.
    if (word & A64_LDR_UNSIGNED_MASK) not in {
        A64_LDR64_UNSIGNED_BASE,
        A64_LDR32_UNSIGNED_BASE,
        A64_LDRB_UNSIGNED_BASE,
        A64_LDRH_UNSIGNED_BASE,
    }:
        return False
    rn = (word >> 5) & 0x1F
    return rn == 0


def assert_no_precall_x0_pointer_deref(image: StaticImage, link_vaddr: int,
                                       name: str) -> None:
    """Reject scalar-call candidates whose entry dereferences x0 before the
    first BL. v2a2 live proved this matters: the recovered `__kmalloc` entry
    reads `[x0,#72]`, so calling it as `__kmalloc(size, flags)` faults at
    `size + 0x48` before any owned buffer exists.
    """
    words = image.u32_words_at_vaddr(link_vaddr, 0x80 // 4)
    for index, word in enumerate(words):
        if _is_a64_bl(word):
            return
        if _is_a64_unsigned_load_from_x0(word):
            raise ReplError(
                f"{name} is not safe for scalar direct-call ABI: "
                f"entry+0x{index * 4:x} dereferences x0 before first BL "
                f"(word={word:#x})"
            )


CALL_SENTINEL = 0xA90CA11  # recognizable arg echoed by the called printk


def run_selftest(session: ReplSession,
                 symbols: dict[str, Symbol],
                 image: StaticImage,
                 *,
                 peek_symbols: tuple[str, ...],
                 call_symbol: str = "printk") -> dict[str, object]:
    checks: list[dict[str, object]] = []
    session.hide()
    session.set_panic_on_oops(0)
    try:
        slide = session.slide()
        # The slide is a single page-granular value; never surfaced raw.
        if slide & 0xFFF:
            raise ReplError("slide is not page-aligned; refusing to proceed")

        # 1) named peek vs static image ground truth -----------------------
        for name in peek_symbols:
            link = resolve_link(symbols, name)
            want = image.u64_at_vaddr(link)
            got = session.peek_runtime(link + slide, 8)
            ok = got == want
            checks.append({
                "check": "named-peek",
                "symbol": name,
                "ok": ok,
                "match_static_qword": ok,
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
        call_link = resolve_link(symbols, call_symbol)
        assert_jopp_entry(image, call_link, call_symbol)
        format_runtime = (FORMAT_LINK_VADDR + slide) & MASK64
        values = session.call_runtime_values(
            call_link + slide,
            (format_runtime, CALL_SENTINEL),
        )
        sentinel_echoed = CALL_SENTINEL in values
        checks.append({
            "check": "named-call-printk",
            "call_symbol": call_symbol,
            "ok": sentinel_echoed,
            "sentinel_echoed": sentinel_echoed,
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
                       check_allocator_abi: bool = True) -> tuple[dict[str, object], dict[str, object]]:
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

    kmalloc_link = resolve_link(symbols, "__kmalloc")
    kfree_link = resolve_link(symbols, "kfree")
    assert_jopp_entry(image, kmalloc_link, "__kmalloc")
    assert_jopp_entry(image, kfree_link, "kfree")
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
        "raw_runtime_values_redacted": True,
        "checks": checks,
    }
    private.update({
        "slide": f"0x{slide:x}",
        "alloc_ptr": f"0x{ptr:x}",
        "gfp_components": {key: f"0x{value:x}" for key, value in gfp_components.items()},
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
    parser.add_argument("--evidence-dir", type=Path, default=None,
                        help="private dir for raw evidence (kept out of git)")


def make_session(args: argparse.Namespace) -> ReplSession:
    return ReplSession(ReplConfig(
        host=args.host,
        port=args.port,
        busybox=args.busybox,
        timeout=args.timeout,
        dmesg_tail=args.dmesg_tail,
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
    link = resolve_link(symbols, args.symbol)
    print(json.dumps({"symbol": args.symbol, "link_vaddr": f"0x{link:x}"}, indent=2))
    return 0


def cmd_peek(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    session = make_session(args)
    link = resolve_link(symbols, args.symbol)
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
        "matches_static_qword": (want is not None and got == want),
    }
    write_evidence(args, {**summary, "_raw_qword": f"0x{got:x}"})
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def cmd_poke_roundtrip(args: argparse.Namespace) -> int:
    symbols = load_system_map(args.map)
    image = load_static_image(args.image)
    session = make_session(args)
    summary, private = run_poke_roundtrip(
        session,
        symbols,
        image,
        alloc_size=args.alloc_size,
        gfp_header=args.gfp_header,
        gfp_value=args.gfp,
        include_width32=not args.skip_width32,
    )
    write_evidence(args, {**summary, "_private": private})
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
    p_res.add_argument("symbol")
    p_res.set_defaults(func=cmd_resolve)

    p_peek = sub.add_parser("peek", help="named runtime peek of one symbol")
    add_common(p_peek)
    p_peek.add_argument("symbol")
    p_peek.add_argument("--len", type=int, default=8)
    p_peek.set_defaults(func=cmd_peek)

    p_round = sub.add_parser("poke-roundtrip", help="v2a2 kmalloc-backed poke/peek/kfree proof")
    add_common(p_round)
    p_round.add_argument("--alloc-size", type=lambda value: int(value, 0), default=KMALLOC_ROUNDTRIP_SIZE)
    p_round.add_argument("--gfp-header", type=Path, default=DEFAULT_GFP_HEADER)
    p_round.add_argument("--gfp", type=lambda value: int(value, 0), default=None,
                         help="override GFP value; default derives GFP_KERNEL from --gfp-header")
    p_round.add_argument("--skip-width32", action="store_true",
                         help="skip the optional 32-bit poke path")
    p_round.set_defaults(func=cmd_poke_roundtrip)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
