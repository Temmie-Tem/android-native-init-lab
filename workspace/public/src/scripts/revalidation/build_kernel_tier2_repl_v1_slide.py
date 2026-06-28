#!/usr/bin/env python3
"""Tier-2 runtime kernel REPL — v1-slide: leak the KASLR slide via an `adr` self-PC.

First build unit of the flash-once kernel REPL (design:
docs/reports/KERNEL_SECURITY_TIER2_RUNTIME_KERNEL_REPL_DESIGN_2026-06-28.md). It
proves the single biggest unverified assumption — that an injected `.text` stub can
read its OWN runtime address with `adr` and thereby reveal the per-boot KASLR slide
without the heavy V2216 perf/codeword method and without an exploit.

Hijacks the corrected `force_no_nap_store` target (file-off 0x8A73C8, vaddr
0xffffff80089273b4, room 212 B), the same disasm-verified store handler the poke
agent uses. On a magic-matched write the leaf-ish stub does:

    eor x16,x30,x17 ; stp x29,x16,[sp,#-16]! ; mov x29,sp      ; ROPP frame (bl below)
    movz/movk x7,<MAGIC> ; ldr x4,[x2] ; cmp x4,x7 ; b.ne out  ; magic guard
    adr x1,.                ; x1 = runtime PC of THIS instruction
    adr x0,fmt              ; x0 = "A90SLIDE %llx\n"
    bl printk               ; print runtime PC
  out:
    mov x0,x3              ; return count
    ldp x29,x16,[sp],#16 ; eor x30,x16,x17 ; ret               ; ROPP epilogue

The host knows the link-time address of the `adr x1,.` instruction
(entry_vaddr + 40), so slide = reported_runtime_pc - (entry_vaddr + 40). A direct
`bl printk` under RKP_CFP is already proven (Stage C); the magic guard means a stray
write to force_no_nap cannot fire it. RECON/operator tooling only — no memory write,
no call, no RKP-protected access.
"""
from __future__ import annotations

import json
import os

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import (  # noqa: E402
    workspace_private_build_path,
    workspace_private_input_path,
    write_private_bytes,
    write_private_json,
)

import build_kernel_tier2_stage_c_direct_bl_printk as stage_c  # noqa: E402
import build_kernel_runtime_poke_agent as poke  # noqa: E402

CYCLE = "TIER2_REPL_V1_SLIDE"
DECISION = "tier2-repl-v1-slide-source-build-pass"
BASE_BOOT_SHA256 = stage_c.BASE_BOOT_SHA256
BASE_BOOT = stage_c.BASE_BOOT
OUT_BOOT = workspace_private_input_path(
    "boot_images", "boot_linux_tier2_repl_v1_slide.img", legacy_fallback=False
)
OUT_DIR = workspace_private_build_path("boot_images", "tier2-repl-v1-slide")

ENTRY_OFF = poke.ENTRY_OFF                # 0x8A73C8 force_no_nap_store
MAGIC_BEFORE_OFF = poke.MAGIC_BEFORE_OFF  # 0x8A73C4
NEXT_MAGIC_OFF = poke.NEXT_MAGIC_OFF      # 0x8A749C
SYSFS_NODE = poke.SYSFS_NODE
POKE_MAGIC = poke.POKE_MAGIC

FORMAT = b"A90SLIDE %llx\n\x00"

# The `adr x1,.` instruction is at word index 10 of the stub (see build below);
# the host computes slide = runtime_pc - (entry_vaddr + ADR_SELF_WORD_INDEX*4).
ADR_SELF_WORD_INDEX = 10


def _movz_movk_magic() -> list[int]:
    return [
        poke._movz_x(7, (POKE_MAGIC >> 0) & 0xFFFF, 0),
        poke._movk_x(7, (POKE_MAGIC >> 16) & 0xFFFF, 16),
        poke._movk_x(7, (POKE_MAGIC >> 32) & 0xFFFF, 32),
        poke._movk_x(7, (POKE_MAGIC >> 48) & 0xFFFF, 48),
    ]


def build_slide_injection(entry_off: int, next_magic_off: int, printk_entry_off: int) -> bytes:
    room = next_magic_off - entry_off
    entry_vaddr = stage_c.kernel_vaddr(entry_off)
    # 17 code words, then the format string.
    fmt_off = entry_off + 17 * 4
    fmt_vaddr = stage_c.kernel_vaddr(fmt_off)
    words = [
        stage_c.U32_EOR_PROLOGUE,            # 0  eor x16,x30,x17
        0xA9BF43FD,                          # 1  stp x29,x16,[sp,#-16]!
        0x910003FD,                          # 2  mov x29,sp
        *_movz_movk_magic(),                 # 3-6 movz/movk x7,<MAGIC>
        0xF9400044,                          # 7  ldr x4,[x2]   candidate magic
        0xEB07009F,                          # 8  cmp x4,x7
        0x54000081,                          # 9  b.ne out (+4 -> idx 13)
        0x10000001,                          # 10 adr x1,.   runtime PC (self)
        stage_c.encode_adr_x0(entry_vaddr + 11 * 4, fmt_vaddr),  # 11 adr x0,fmt
        stage_c.encode_bl(entry_vaddr + 12 * 4, stage_c.kernel_vaddr(printk_entry_off)),  # 12 bl printk
        0xAA0303E0,                          # 13 out: mov x0,x3   return count
        0xA8C143FD,                          # 14 ldp x29,x16,[sp],#16
        stage_c.U32_EOR_EPILOGUE,            # 15 eor x30,x16,x17
        stage_c.U32_RET,                     # 16 ret
    ]
    if len(words) != 17:
        raise RuntimeError(f"stub word count drifted: {len(words)} (ADR_SELF_WORD_INDEX stale)")
    payload = b"".join(stage_c.put_u32(w) for w in words) + FORMAT
    while len(payload) % 4:
        payload += b"\x00"
    if len(payload) > room:
        raise RuntimeError(f"slide injection too large: {len(payload)} > {room}")
    payload += stage_c.put_u32(stage_c.U32_NOP) * ((room - len(payload)) // 4)
    return payload


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

    # Same exact-fingerprint asserts as the poke agent (force_no_nap_store, not the
    # generic ROPP shape that fooled the original brick build).
    if stage_c.u32_at(kernel, MAGIC_BEFORE_OFF) != poke.U32_MAGIC:
        raise RuntimeError("RKP magic before entry not found — offsets stale")
    if stage_c.u32_at(kernel, ENTRY_OFF) != poke.U32_FNN_STORE_FIRST:
        raise RuntimeError("entry is not force_no_nap_store `sub sp,#0x40` — wrong target")
    if stage_c.u32_at(kernel, ENTRY_OFF + 4) != poke.U32_EOR_PROLOGUE:
        raise RuntimeError("second word is not the ROPP eor prologue — wrong target")
    if stage_c.u32_at(kernel, NEXT_MAGIC_OFF) != poke.U32_MAGIC:
        raise RuntimeError("next RKP magic not found — offsets stale")

    _printk_magic_off, printk_entry_off, _va_helper_off, _emit_core_off = (
        stage_c.locate_printk_variadic_wrapper(kernel)
    )
    payload = build_slide_injection(ENTRY_OFF, NEXT_MAGIC_OFF, printk_entry_off)

    patch_abs_off = layout.kernel_off + ENTRY_OFF
    patched[patch_abs_off : patch_abs_off + len(payload)] = payload
    boot_id = stage_c.recompute_boot_id(patched, layout)
    diff_offsets = stage_c.changed_offsets(original, bytes(patched))
    allowed_kernel = set(range(patch_abs_off, patch_abs_off + len(payload)))
    allowed_id = set(range(stage_c.BOOT_ID_OFFSET, stage_c.BOOT_ID_OFFSET + stage_c.BOOT_ID_SIZE))
    unexpected = [off for off in diff_offsets if off not in allowed_kernel and off not in allowed_id]
    if unexpected:
        raise RuntimeError(f"unexpected patched offsets outside contract: {unexpected[:8]}")

    write_private_bytes(OUT_BOOT, bytes(patched))
    os.chmod(OUT_BOOT, 0o600)
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
        "patch_room": NEXT_MAGIC_OFF - ENTRY_OFF,
        "patch_len": len(payload),
        "poke_magic": hex(POKE_MAGIC),
        "adr_self_word_index": ADR_SELF_WORD_INDEX,
        "adr_self_link_vaddr": hex(entry_vaddr + ADR_SELF_WORD_INDEX * 4),
        "slide_formula": "slide = reported_runtime_pc - adr_self_link_vaddr",
        "printk_entry_vaddr": hex(stage_c.kernel_vaddr(printk_entry_off)),
        "format": FORMAT.decode("ascii").replace("\n", "\\n").replace("\x00", "\\0"),
        "protocol": "write 8+ LE bytes with first qword == poke_magic; stub printk's its runtime PC as 'A90SLIDE <hex>'",
        "control_flow": {
            "ropp_frame": True,
            "new_direct_bl_printk": True,
            "adr_self_pc_leak": True,
            "magic_guard": True,
            "no_blr": True,
            "no_memory_write": True,
            "cfp_safe": True,
        },
    }
    write_private_json(OUT_DIR / "manifest.json", manifest)
    return manifest


def main() -> int:
    print(json.dumps(build_candidate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
