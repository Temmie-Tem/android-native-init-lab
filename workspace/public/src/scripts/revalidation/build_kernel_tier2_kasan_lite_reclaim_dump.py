#!/usr/bin/env python3
"""Build the Tier-2 KASAN-lite PROCA/FIVE reclaim-dump kernel patch."""

from __future__ import annotations

import json
import os
from pathlib import Path

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import (
    workspace_private_build_path,
    workspace_private_input_path,
    write_private_bytes,
    write_private_json,
)

import build_kernel_tier2_stage_c_direct_bl_printk as stage_c

CYCLE = "TIER2_KASAN_LITE_RECLAIM_DUMP"
DECISION = "tier2-kasan-lite-reclaim-dump-source-build-pass"
BASE_BOOT_SHA256 = stage_c.BASE_BOOT_SHA256
BASE_BOOT = stage_c.BASE_BOOT
OUT_BOOT = workspace_private_input_path(
    "boot_images",
    "boot_linux_tier2_kasan_lite_reclaim_dump.img",
    legacy_fallback=False,
)
OUT_DIR = workspace_private_build_path("boot_images", "tier2-kasan-lite-reclaim-dump")

PROC_RESET_EXPECTED_MAGIC_OFF = 0x2AB0FC
PROC_RESET_EXPECTED_ENTRY_OFF = 0x2AB100
PROC_RESET_EXPECTED_NEXT_MAGIC_OFF = 0x2AB1BC
PROC_RESET_TASK_INTEGRITY_OFF = 0xB40
TASK_INTEGRITY_RESET_FILE_OFF = 0x58
TASK_INTEGRITY_DUMP_BYTES = 0x60

FORMAT = b"A90KAL%d %llx %llx %llx %llx %llx\n\x00"


def encode_ldr_x_imm(rt: int, rn: int, imm: int) -> int:
    if imm % 8:
        raise RuntimeError(f"unaligned 64-bit LDR offset: {imm}")
    imm12 = imm // 8
    if not 0 <= imm12 < (1 << 12):
        raise RuntimeError(f"64-bit LDR offset out of range: {imm}")
    return 0xF9400000 | (imm12 << 10) | (rn << 5) | rt


def encode_ldp_x(rt: int, rt2: int, rn: int, imm: int) -> int:
    if imm % 8:
        raise RuntimeError(f"unaligned 64-bit LDP offset: {imm}")
    imm7 = imm // 8
    if not -(1 << 6) <= imm7 < (1 << 6):
        raise RuntimeError(f"64-bit LDP offset out of range: {imm}")
    return 0xA9400000 | ((imm7 & 0x7F) << 15) | (rt2 << 10) | (rn << 5) | rt


def encode_mov_x(dst: int, src: int) -> int:
    return 0xAA0003E0 | (src << 16) | dst


def encode_mov_w_imm(dst: int, imm: int) -> int:
    if not 0 <= imm <= 0xFFFF:
        raise RuntimeError(f"MOVZ immediate out of range: {imm}")
    return 0x52800000 | (imm << 5) | dst


def find_proc_integrity_reset_file(kernel: bytes) -> tuple[int, int, int]:
    hits: list[tuple[int, int, int]] = []
    for magic_off in stage_c.iter_word_offsets(kernel, stage_c.U32_MAGIC):
        entry_off = stage_c.function_entry_after_magic(kernel, magic_off)
        if entry_off is None:
            continue
        try:
            next_magic_off = stage_c.find_next_magic(kernel, entry_off)
        except RuntimeError:
            continue
        if next_magic_off - entry_off < 0x80:
            continue
        body = {stage_c.u32_at(kernel, off) for off in range(entry_off, next_magic_off, 4)}
        required = {
            0xF945A068,  # ldr x8, [x3, #0xb40]       ; task->integrity
            0xF9402D08,  # ldr x8, [x8, #0x58]        ; tint->reset_file
            0x52820002,  # mov w2, #0x1000            ; PAGE_SIZE
            0x91004100,  # add x0, x8, #0x10          ; &reset_file->f_path
        }
        if required.issubset(body):
            hits.append((magic_off, entry_off, next_magic_off))
    if len(hits) != 1:
        raise RuntimeError(f"expected one proc_integrity_reset_file signature hit, found {len(hits)}")
    hit = hits[0]
    expected = (
        PROC_RESET_EXPECTED_MAGIC_OFF,
        PROC_RESET_EXPECTED_ENTRY_OFF,
        PROC_RESET_EXPECTED_NEXT_MAGIC_OFF,
    )
    if hit != expected:
        raise RuntimeError(f"unexpected proc_integrity_reset_file hit: actual={hit!r} expected={expected!r}")
    return hit


def build_dump_injection(entry_off: int, next_magic_off: int, printk_entry_off: int) -> tuple[bytes, int]:
    room = next_magic_off - entry_off
    code_words: list[int] = [
        stage_c.U32_EOR_PROLOGUE,
        0xA9BE43FD,  # stp x29, x16, [sp, #-32]!
        0xF9000BF3,  # str x19, [sp, #16]
        0x910003FD,  # mov x29, sp
        encode_ldr_x_imm(19, 3, PROC_RESET_TASK_INTEGRITY_OFF),  # x19 = task->integrity
    ]

    adr_placeholders: list[int] = []
    bl_placeholders: list[int] = []
    for line_index, offset in enumerate((0x00, 0x20, 0x40)):
        adr_placeholders.append(len(code_words))
        bl_placeholders.append(len(code_words) + 5)
        code_words.extend([
            0,  # patched to ADR x0, format
            encode_mov_w_imm(1, line_index),
            encode_mov_x(2, 19),
            encode_ldp_x(3, 4, 19, offset),
            encode_ldp_x(5, 6, 19, offset + 0x10),
            0,  # patched to BL printk
        ])

    code_words.extend([
        0x2A1F03E0,  # mov w0, wzr
        0xF9400BF3,  # ldr x19, [sp, #16]
        0xA8C243FD,  # ldp x29, x16, [sp], #32
        stage_c.U32_EOR_EPILOGUE,
        stage_c.U32_RET,
    ])

    code_len = len(code_words) * 4
    format_off = entry_off + code_len
    format_vaddr = stage_c.kernel_vaddr(format_off)
    entry_vaddr = stage_c.kernel_vaddr(entry_off)
    for word_index in adr_placeholders:
        site_vaddr = entry_vaddr + word_index * 4
        code_words[word_index] = stage_c.encode_adr_x0(site_vaddr, format_vaddr)
    for word_index in bl_placeholders:
        site_vaddr = entry_vaddr + word_index * 4
        code_words[word_index] = stage_c.encode_bl(site_vaddr, stage_c.kernel_vaddr(printk_entry_off))

    payload = b"".join(stage_c.put_u32(word) for word in code_words) + FORMAT
    while len(payload) % 4:
        payload += b"\x00"
    if len(payload) > room:
        raise RuntimeError(f"injection payload too large: {len(payload)} > {room}")
    payload += stage_c.put_u32(stage_c.U32_NOP) * ((room - len(payload)) // 4)
    return payload, format_off


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

    proc_magic_off, proc_entry_off, proc_next_magic_off = find_proc_integrity_reset_file(kernel)
    printk_magic_off, printk_entry_off, printk_va_helper_off, printk_emit_core_off = (
        stage_c.locate_printk_variadic_wrapper(kernel)
    )
    payload, format_off = build_dump_injection(proc_entry_off, proc_next_magic_off, printk_entry_off)

    patch_abs_off = layout.kernel_off + proc_entry_off
    patched[patch_abs_off : patch_abs_off + len(payload)] = payload
    boot_id = stage_c.recompute_boot_id(patched, layout)
    diff_offsets = stage_c.changed_offsets(original, bytes(patched))
    allowed_kernel = set(range(patch_abs_off, patch_abs_off + len(payload)))
    allowed_id = set(range(stage_c.BOOT_ID_OFFSET, stage_c.BOOT_ID_OFFSET + stage_c.BOOT_ID_SIZE))
    unexpected = [off for off in diff_offsets if off not in allowed_kernel and off not in allowed_id]
    if unexpected:
        raise RuntimeError(f"unexpected patched offsets outside kernel/id contract: {unexpected[:8]}")

    write_private_bytes(OUT_BOOT, bytes(patched))
    os.chmod(OUT_BOOT, 0o600)
    out_sha = stage_c.sha256_file(OUT_BOOT)
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
        "diff_ranges": [[hex(start), hex(stop)] for start, stop in stage_c.contiguous_ranges(diff_offsets)],
        "kernel_boot_offset": hex(layout.kernel_off),
        "kernel_size": layout.kernel_size,
        "proc_reset_magic_off": hex(proc_magic_off),
        "proc_reset_entry_off": hex(proc_entry_off),
        "proc_reset_entry_vaddr": hex(stage_c.kernel_vaddr(proc_entry_off)),
        "proc_reset_next_magic_off": hex(proc_next_magic_off),
        "proc_reset_patch_room": proc_next_magic_off - proc_entry_off,
        "proc_reset_patch_len": len(payload),
        "task_struct_integrity_off": hex(PROC_RESET_TASK_INTEGRITY_OFF),
        "task_integrity_layout": {
            "user_value": "0x0",
            "value": "0x4",
            "usage_count": "0x8",
            "value_lock": "0xc",
            "list_lock": "0x10",
            "label": "0x18",
            "events": "0x20",
            "reset_cause": "0x50",
            "reset_file": hex(TASK_INTEGRITY_RESET_FILE_OFF),
            "dump_bytes": hex(TASK_INTEGRITY_DUMP_BYTES),
        },
        "format": FORMAT.decode("ascii").replace("\n", "\\n").replace("\x00", "\\0"),
        "format_off": hex(format_off),
        "format_vaddr": hex(stage_c.kernel_vaddr(format_off)),
        "printk_magic_off": hex(printk_magic_off),
        "printk_entry_off": hex(printk_entry_off),
        "printk_entry_vaddr": hex(stage_c.kernel_vaddr(printk_entry_off)),
        "printk_va_helper_off": stage_c.optional_kernel_offset_text(printk_va_helper_off),
        "printk_va_helper_vaddr": stage_c.optional_kernel_vaddr_text(printk_va_helper_off),
        "printk_emit_core_off": stage_c.optional_kernel_offset_text(printk_emit_core_off),
        "printk_emit_core_vaddr": stage_c.optional_kernel_vaddr_text(printk_emit_core_off),
        "control_flow": {
            "new_direct_bl": True,
            "bl_target": "plain-printk-variadic-wrapper-signature",
            "no_blr": True,
            "preserves_x17": True,
            "ropp_prologue": "eor x16,x30,x17; stp x29,x16,[sp,#-32]!",
            "ropp_epilogue": "ldp x29,x16,[sp],#32; eor x30,x16,x17; ret",
            "max_args_per_printk_call": 6,
            "stack_varargs": False,
        },
    }
    write_private_json(OUT_DIR / "manifest.json", manifest)
    return manifest


def main() -> int:
    manifest = build_candidate()
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
