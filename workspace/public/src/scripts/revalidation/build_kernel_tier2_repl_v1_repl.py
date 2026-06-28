#!/usr/bin/env python3
"""Tier-2 runtime kernel REPL v1: slide + small peek + poke + call.

This is the second build unit of the flash-once runtime kernel REPL. It reuses
the live-proven corrected `force_no_nap_store` patch target from the poke agent
and the v1-slide self-PC leak, then adds:

  op 0: slide - printk the runtime PC of the injected `adr x1,.`
  op 1: peek  - printk one qword at addr when 1 <= len <= 8 is supplied
  op 2: poke  - write val as 64-bit when width == 8, else 32-bit; printk val
  op 3: call  - call a real function entry with x0..x7; printk return x0

Command layout is a kernfs write buffer:

  +0x00 u64 magic  (0xA90C0DE5DEADBEEF)
  +0x08 u8  op
  +0x10 u64 arg0   (peek/poke addr, call target)
  +0x18 u64 arg1   (peek len, poke val, call x0)
  +0x20 u64 arg2   (poke width, call x1)
  +0x28 u64 arg3   (call x2)
  +0x30 u64 arg4   (call x3)
  +0x38 u64 arg5   (call x4)
  +0x40 u64 arg6   (call x5)
  +0x48 u64 arg7   (call x6)
  +0x50 u64 arg8   (call x7)

The store room is exactly 212 bytes, so v1 uses one compact printk format
(`A90R%llx\n`) and prints a single result word for each op. `call` is non-leaf:
the stub saves the ROPP eor value and x17 on the stack, restores x17 before the
ROPP epilogue, and uses `blr x9`. The call target must be a real function entry
whose entry-4 word is the JOPP magic (0x00BE7BAD); this v1 stub relies on the
kernel's JOPP gate and the host/live-validation contract rather than spending
store-room bytes on an in-stub precheck.
"""
from __future__ import annotations

import json
import os
import struct

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import (  # noqa: E402
    workspace_private_build_path,
    workspace_private_input_path,
    write_private_bytes,
    write_private_json,
)

import build_kernel_runtime_poke_agent as poke  # noqa: E402
import build_kernel_tier2_stage_c_direct_bl_printk as stage_c  # noqa: E402

CYCLE = "TIER2_REPL_V1_REPL"
DECISION = "tier2-repl-v1-repl-source-build-pass"
BASE_BOOT_SHA256 = stage_c.BASE_BOOT_SHA256
BASE_BOOT = stage_c.BASE_BOOT
OUT_BOOT = workspace_private_input_path(
    "boot_images", "boot_linux_tier2_repl_v1_repl.img", legacy_fallback=False
)
OUT_DIR = workspace_private_build_path("boot_images", "tier2-repl-v1-repl")

ENTRY_OFF = poke.ENTRY_OFF                # 0x8A73C8 force_no_nap_store
MAGIC_BEFORE_OFF = poke.MAGIC_BEFORE_OFF  # 0x8A73C4
NEXT_MAGIC_OFF = poke.NEXT_MAGIC_OFF      # 0x8A749C
SYSFS_NODE = poke.SYSFS_NODE
REPL_MAGIC = poke.POKE_MAGIC
JOPP_MAGIC = stage_c.U32_MAGIC
PRINTK_ENTRY_VADDR = 0xFFFFFF800813ADFC

OP_SLIDE = 0
OP_PEEK = 1
OP_POKE = 2
OP_CALL = 3
PEEK_MAX_LEN = 8

FORMAT = b"A90R%llx\n\x00"
ADR_SELF_WORD_INDEX = 15
CODE_WORD_COUNT = 48
MAGIC_LITERAL_WORD_INDEX = 48
FORMAT_WORD_INDEX = 50
EXPECTED_PATCH_LEN = 212


def _check_reg(value: int) -> None:
    if not 0 <= value <= 31:
        raise ValueError(f"bad register: {value}")


def _check_scaled_imm(imm: int, scale: int, bits: int, signed: bool = False) -> int:
    if imm % scale:
        raise ValueError(f"unaligned immediate {imm} for scale {scale}")
    value = imm // scale
    if signed:
        min_value = -(1 << (bits - 1))
        max_value = (1 << (bits - 1)) - 1
        if not min_value <= value <= max_value:
            raise ValueError(f"signed immediate out of range: {imm}")
        return value & ((1 << bits) - 1)
    if not 0 <= value < (1 << bits):
        raise ValueError(f"immediate out of range: {imm}")
    return value


def encode_adr(rd: int, site_vaddr: int, target_vaddr: int) -> int:
    _check_reg(rd)
    delta = target_vaddr - site_vaddr
    if not -(1 << 20) <= delta < (1 << 20):
        raise RuntimeError(f"ADR target out of range: {delta}")
    imm = delta & 0x1FFFFF
    immlo = imm & 0x3
    immhi = (imm >> 2) & 0x7FFFF
    return 0x10000000 | (immlo << 29) | (immhi << 5) | rd


def encode_ldr_literal_x(rt: int, site_vaddr: int, target_vaddr: int) -> int:
    _check_reg(rt)
    delta = target_vaddr - site_vaddr
    if delta % 4:
        raise RuntimeError(f"unaligned LDR literal delta: {delta}")
    imm19 = delta // 4
    if not -(1 << 18) <= imm19 < (1 << 18):
        raise RuntimeError(f"LDR literal target out of range: {delta}")
    return 0x58000000 | ((imm19 & 0x7FFFF) << 5) | rt


def encode_b_index(site_index: int, target_index: int) -> int:
    imm26 = target_index - site_index
    if not -(1 << 25) <= imm26 < (1 << 25):
        raise RuntimeError(f"B target out of range: {site_index}->{target_index}")
    return 0x14000000 | (imm26 & 0x03FFFFFF)


def encode_b_cond_index(site_index: int, target_index: int, cond: int) -> int:
    if not 0 <= cond <= 0xF:
        raise ValueError(f"bad condition: {cond}")
    imm19 = target_index - site_index
    if not -(1 << 18) <= imm19 < (1 << 18):
        raise RuntimeError(f"B.cond target out of range: {site_index}->{target_index}")
    return 0x54000000 | ((imm19 & 0x7FFFF) << 5) | cond


def encode_tbz_index(rt: int, bit: int, site_index: int, target_index: int) -> int:
    _check_reg(rt)
    if not 0 <= bit < 64:
        raise ValueError(f"bad TBZ bit: {bit}")
    imm14 = target_index - site_index
    if not -(1 << 13) <= imm14 < (1 << 13):
        raise RuntimeError(f"TBZ target out of range: {site_index}->{target_index}")
    b5 = (bit >> 5) & 1
    b40 = bit & 0x1F
    return 0x36000000 | (b5 << 31) | (b40 << 19) | ((imm14 & 0x3FFF) << 5) | rt


def encode_cmp_w_imm(rn: int, imm: int) -> int:
    _check_reg(rn)
    if not 0 <= imm < 0x1000:
        raise ValueError(f"bad cmp immediate: {imm}")
    return 0x7100001F | (imm << 10) | (rn << 5)


def encode_cmp_x_imm(rn: int, imm: int) -> int:
    _check_reg(rn)
    if not 0 <= imm < 0x1000:
        raise ValueError(f"bad cmp immediate: {imm}")
    return 0xF100001F | (imm << 10) | (rn << 5)


def encode_ldr_x_imm(rt: int, rn: int, imm: int) -> int:
    _check_reg(rt)
    _check_reg(rn)
    imm12 = _check_scaled_imm(imm, 8, 12)
    return 0xF9400000 | (imm12 << 10) | (rn << 5) | rt


def encode_ldrb_w_imm(rt: int, rn: int, imm: int) -> int:
    _check_reg(rt)
    _check_reg(rn)
    if not 0 <= imm < 0x1000:
        raise ValueError(f"bad ldrb immediate: {imm}")
    return 0x39400000 | (imm << 10) | (rn << 5) | rt


def encode_str_x_imm(rt: int, rn: int, imm: int) -> int:
    _check_reg(rt)
    _check_reg(rn)
    imm12 = _check_scaled_imm(imm, 8, 12)
    return 0xF9000000 | (imm12 << 10) | (rn << 5) | rt


def encode_str_w_imm(rt: int, rn: int, imm: int) -> int:
    _check_reg(rt)
    _check_reg(rn)
    imm12 = _check_scaled_imm(imm, 4, 12)
    return 0xB9000000 | (imm12 << 10) | (rn << 5) | rt


def encode_stp_pre_x(rt: int, rt2: int, rn: int, imm: int) -> int:
    _check_reg(rt)
    _check_reg(rt2)
    _check_reg(rn)
    imm7 = _check_scaled_imm(imm, 8, 7, signed=True)
    return 0xA9800000 | (imm7 << 15) | (rt2 << 10) | (rn << 5) | rt


def encode_ldp_x_imm(rt: int, rt2: int, rn: int, imm: int) -> int:
    _check_reg(rt)
    _check_reg(rt2)
    _check_reg(rn)
    imm7 = _check_scaled_imm(imm, 8, 7, signed=True)
    return 0xA9400000 | (imm7 << 15) | (rt2 << 10) | (rn << 5) | rt


def encode_ldp_post_x(rt: int, rt2: int, rn: int, imm: int) -> int:
    _check_reg(rt)
    _check_reg(rt2)
    _check_reg(rn)
    imm7 = _check_scaled_imm(imm, 8, 7, signed=True)
    return 0xA8C00000 | (imm7 << 15) | (rt2 << 10) | (rn << 5) | rt


def encode_mov_x(rd: int, rn: int) -> int:
    _check_reg(rd)
    _check_reg(rn)
    return 0xAA0003E0 | (rn << 16) | rd


def encode_blr(rn: int) -> int:
    _check_reg(rn)
    return 0xD63F0000 | (rn << 5)


def _site(entry_vaddr: int, word_index: int) -> int:
    return entry_vaddr + word_index * 4


def build_repl_injection(entry_off: int, next_magic_off: int, printk_entry_off: int) -> bytes:
    room = next_magic_off - entry_off
    entry_vaddr = stage_c.kernel_vaddr(entry_off)
    labels = {
        "low_ops": 13,
        "slide": 15,
        "peek": 17,
        "poke": 23,
        "poke32": 30,
        "poke_done": 31,
        "call": 33,
        "print": 42,
        "out": 44,
        "magic": MAGIC_LITERAL_WORD_INDEX,
        "fmt": FORMAT_WORD_INDEX,
    }
    words = [
        stage_c.U32_EOR_PROLOGUE,                                # 00 eor x16,x30,x17
        encode_stp_pre_x(16, 17, 31, -32),                       # 01 stp x16,x17,[sp,#-32]!
        encode_str_x_imm(3, 31, 16),                             # 02 str x3,[sp,#16]
        encode_ldr_literal_x(7, _site(entry_vaddr, 3), _site(entry_vaddr, labels["magic"])),
        encode_ldr_x_imm(4, 2, 0),                               # 04 ldr x4,[x2]
        0xEB07009F,                                              # 05 cmp x4,x7
        encode_b_cond_index(6, labels["out"], 0x1),              # 06 b.ne out
        encode_ldrb_w_imm(4, 2, 8),                              # 07 ldrb w4,[x2,#8]
        encode_cmp_w_imm(4, OP_CALL),                            # 08 cmp w4,#3
        encode_b_cond_index(9, labels["out"], 0x8),              # 09 b.hi out
        encode_tbz_index(4, 1, 10, labels["low_ops"]),           # 10 tbz w4,#1,low_ops
        encode_tbz_index(4, 0, 11, labels["poke"]),              # 11 tbz w4,#0,poke
        encode_b_index(12, labels["call"]),                      # 12 b call
        encode_tbz_index(4, 0, 13, labels["slide"]),             # 13 low_ops: tbz w4,#0,slide
        encode_b_index(14, labels["peek"]),                      # 14 b peek
        encode_adr(1, _site(entry_vaddr, 15), _site(entry_vaddr, 15)),
        encode_b_index(16, labels["print"]),                     # 16 b print
        encode_ldr_x_imm(5, 2, 16),                              # 17 peek: ldr x5,[x2,#16]
        encode_ldr_x_imm(6, 2, 24),                              # 18 ldr x6,[x2,#24]
        encode_cmp_x_imm(6, PEEK_MAX_LEN),                       # 19 cmp x6,#8
        encode_b_cond_index(20, labels["out"], 0x8),             # 20 b.hi out
        encode_ldr_x_imm(1, 5, 0),                               # 21 ldr x1,[x5]
        encode_b_index(22, labels["print"]),                     # 22 b print
        encode_ldr_x_imm(5, 2, 16),                              # 23 poke: ldr x5,[x2,#16]
        encode_ldr_x_imm(6, 2, 24),                              # 24 ldr x6,[x2,#24]
        encode_ldr_x_imm(7, 2, 32),                              # 25 ldr x7,[x2,#32]
        encode_cmp_x_imm(7, 8),                                  # 26 cmp x7,#8
        encode_b_cond_index(27, labels["poke32"], 0x1),          # 27 b.ne poke32
        encode_str_x_imm(6, 5, 0),                               # 28 str x6,[x5]
        encode_b_index(29, labels["poke_done"]),                 # 29 b poke_done
        encode_str_w_imm(6, 5, 0),                               # 30 poke32: str w6,[x5]
        encode_mov_x(1, 6),                                      # 31 poke_done: mov x1,x6
        encode_b_index(32, labels["print"]),                     # 32 b print
        encode_mov_x(11, 2),                                     # 33 call: mov x11,x2
        encode_ldr_x_imm(9, 11, 16),                             # 34 ldr x9,[x11,#16]
        encode_ldp_x_imm(0, 1, 11, 24),                          # 35 ldp x0,x1,[x11,#24]
        encode_ldp_x_imm(2, 3, 11, 40),                          # 36 ldp x2,x3,[x11,#40]
        encode_ldp_x_imm(4, 5, 11, 56),                          # 37 ldp x4,x5,[x11,#56]
        encode_ldp_x_imm(6, 7, 11, 72),                          # 38 ldp x6,x7,[x11,#72]
        encode_blr(9),                                           # 39 blr x9
        encode_mov_x(1, 0),                                      # 40 mov x1,x0
        encode_b_index(41, labels["print"]),                     # 41 b print
        encode_adr(0, _site(entry_vaddr, 42), _site(entry_vaddr, labels["fmt"])),
        stage_c.encode_bl(_site(entry_vaddr, 43), stage_c.kernel_vaddr(printk_entry_off)),
        encode_ldr_x_imm(0, 31, 16),                             # 44 out: ldr x0,[sp,#16]
        encode_ldp_post_x(16, 17, 31, 32),                       # 45 ldp x16,x17,[sp],#32
        stage_c.U32_EOR_EPILOGUE,                                # 46 eor x30,x16,x17
        stage_c.U32_RET,                                         # 47 ret
    ]
    if len(words) != CODE_WORD_COUNT:
        raise RuntimeError(f"stub word count drifted: {len(words)}")
    payload = b"".join(stage_c.put_u32(word) for word in words)
    payload += struct.pack("<Q", REPL_MAGIC)
    payload += FORMAT
    while len(payload) % 4:
        payload += b"\x00"
    if len(payload) != EXPECTED_PATCH_LEN:
        raise RuntimeError(f"unexpected v1-repl payload length: {len(payload)}")
    if len(payload) > room:
        raise RuntimeError(f"v1-repl payload too large: {len(payload)} > {room}")
    payload += stage_c.put_u32(stage_c.U32_NOP) * ((room - len(payload)) // 4)
    return payload


def _assert_force_no_nap_store_fingerprint(kernel: bytes | bytearray) -> None:
    if stage_c.u32_at(kernel, MAGIC_BEFORE_OFF) != JOPP_MAGIC:
        raise RuntimeError("RKP magic before force_no_nap_store not found")
    if stage_c.u32_at(kernel, ENTRY_OFF) != poke.U32_FNN_STORE_FIRST:
        raise RuntimeError("entry is not force_no_nap_store `sub sp,#0x40`")
    if stage_c.u32_at(kernel, ENTRY_OFF + 4) != poke.U32_EOR_PROLOGUE:
        raise RuntimeError("second word is not force_no_nap_store ROPP eor")
    if stage_c.u32_at(kernel, NEXT_MAGIC_OFF) != JOPP_MAGIC:
        raise RuntimeError("next RKP magic after force_no_nap_store not found")


def build_candidate() -> dict[str, object]:
    base_sha = stage_c.sha256_file(BASE_BOOT)
    if base_sha != BASE_BOOT_SHA256:
        raise RuntimeError(f"unexpected v2321 SHA256: {base_sha}")
    original = BASE_BOOT.read_bytes()
    patched = bytearray(original)
    layout = stage_c.parse_boot_layout(original)
    kernel = bytes(original[layout.kernel_off : layout.kernel_off + layout.kernel_size])
    if kernel[:16] != b"UNCOMPRESSED_IMG":
        raise RuntimeError("kernel wrapper is not UNCOMPRESSED_IMG")
    _assert_force_no_nap_store_fingerprint(kernel)

    _printk_magic_off, printk_entry_off, _va_helper_off, _emit_core_off = (
        stage_c.locate_printk_variadic_wrapper(kernel)
    )
    printk_vaddr = stage_c.kernel_vaddr(printk_entry_off)
    if printk_vaddr != PRINTK_ENTRY_VADDR:
        raise RuntimeError(f"plain printk target drifted: 0x{printk_vaddr:x}")
    payload = build_repl_injection(ENTRY_OFF, NEXT_MAGIC_OFF, printk_entry_off)

    patch_abs_off = layout.kernel_off + ENTRY_OFF
    patched[patch_abs_off : patch_abs_off + len(payload)] = payload
    patched_kernel = bytes(patched[layout.kernel_off : layout.kernel_off + layout.kernel_size])
    if stage_c.u32_at(patched_kernel, MAGIC_BEFORE_OFF) != JOPP_MAGIC:
        raise RuntimeError("patched image clobbered previous RKP magic")
    if stage_c.u32_at(patched_kernel, NEXT_MAGIC_OFF) != JOPP_MAGIC:
        raise RuntimeError("patched image clobbered next RKP magic")

    boot_id = stage_c.recompute_boot_id(patched, layout)
    diff_offsets = stage_c.changed_offsets(original, bytes(patched))
    allowed_kernel = set(range(patch_abs_off, patch_abs_off + len(payload)))
    allowed_id = set(range(stage_c.BOOT_ID_OFFSET, stage_c.BOOT_ID_OFFSET + stage_c.BOOT_ID_SIZE))
    unexpected = [off for off in diff_offsets if off not in allowed_kernel and off not in allowed_id]
    if unexpected:
        raise RuntimeError(f"unexpected patched offsets outside contract: {unexpected[:8]}")

    write_private_bytes(OUT_BOOT, bytes(patched))
    os.chmod(OUT_BOOT, 0o600)
    write_private_bytes(OUT_DIR / "force_no_nap_store_v1_repl_body.bin", payload)
    out_sha = stage_c.sha256_file(OUT_BOOT)
    entry_vaddr = stage_c.kernel_vaddr(ENTRY_OFF)
    manifest = {
        "cycle": CYCLE,
        "decision": DECISION,
        "base_boot": str(BASE_BOOT.relative_to(REPO_ROOT)),
        "base_sha256": base_sha,
        "out_boot": str(OUT_BOOT.relative_to(REPO_ROOT)),
        "out_sha256": out_sha,
        "out_mode": oct(OUT_BOOT.stat().st_mode & 0o777),
        "boot_id": boot_id[:20].hex(),
        "diff_byte_count": len(diff_offsets),
        "diff_ranges": [[hex(a), hex(b)] for a, b in stage_c.contiguous_ranges(diff_offsets)],
        "hijacked_handler": "kgsl_pwrctrl_force_no_nap_store",
        "sysfs_node": SYSFS_NODE,
        "entry_off": hex(ENTRY_OFF),
        "entry_vaddr": hex(entry_vaddr),
        "magic_before_off": hex(MAGIC_BEFORE_OFF),
        "next_magic_off": hex(NEXT_MAGIC_OFF),
        "patch_room": NEXT_MAGIC_OFF - ENTRY_OFF,
        "patch_len": len(payload),
        "body_bin": str((OUT_DIR / "force_no_nap_store_v1_repl_body.bin").relative_to(REPO_ROOT)),
        "repl_magic": hex(REPL_MAGIC),
        "jopp_magic": hex(JOPP_MAGIC),
        "printk_entry_vaddr": hex(printk_vaddr),
        "format": FORMAT.decode("ascii").replace("\n", "\\n").replace("\x00", "\\0"),
        "adr_self_word_index": ADR_SELF_WORD_INDEX,
        "adr_self_link_vaddr": hex(entry_vaddr + ADR_SELF_WORD_INDEX * 4),
        "slide_formula": "slide = reported_runtime_pc - adr_self_link_vaddr",
        "peek_max_len": PEEK_MAX_LEN,
        "protocol": {
            "magic_offset": "0x00:u64",
            "op_offset": "0x08:u8",
            "arg0_offset": "0x10:u64",
            "arg1_offset": "0x18:u64",
            "arg2_offset": "0x20:u64",
            "call_args": "target@0x10, x0..x7@0x18..0x50",
            "outputs": "printk line A90R%llx for slide pc, peek qword, poke val, or call return",
            "call_target_contract": "target must be a real function entry with u32(entry-4)==0x00BE7BAD",
        },
        "ops": {
            "0": "slide: printk runtime PC of adr_self instruction",
            "1": "peek: if len <= 8, printk u64 at addr",
            "2": "poke: width == 8 stores u64 else stores u32, then printk val",
            "3": "call: blr target with x0..x7, then printk return x0",
        },
        "control_flow": {
            "ropp_eor_frame": True,
            "preserves_x17": True,
            "new_direct_bl_printk": True,
            "has_blr_for_call": True,
            "call_target_jopp_gated": True,
            "in_stub_jopp_precheck": False,
            "magic_guard": True,
            "no_ret_site_patch": True,
            "no_cfp_site_patch": True,
            "no_rwx": True,
        },
    }
    write_private_json(OUT_DIR / "manifest.json", manifest)
    return manifest


def main() -> int:
    print(json.dumps(build_candidate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
