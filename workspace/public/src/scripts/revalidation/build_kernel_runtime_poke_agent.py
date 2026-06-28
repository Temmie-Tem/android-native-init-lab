#!/usr/bin/env python3
"""Flash-once runtime kernel POKE agent (Tier-2, operator tool) — corrected build.

Goal: stop re-flashing for every EL1 experiment. Flash ONCE a kernel that turns a
benign write-only sysfs node into a runtime "poke" channel; thereafter write
kernel memory at runtime over the bridge with NO reflash/reboot.

Mechanism: hijack `kgsl_pwrctrl_force_no_nap_store(dev, attr, buf, count)` — a
benign GPU debug-flag sysfs *store* handler (`/sys/class/kgsl/kgsl-3d0/force_no_nap`).
Store signature is `ssize_t store(struct device*, struct device_attribute*, const
char *buf, size_t count)` => x0=dev, x1=attr, x2=buf, x3=count. `buf` is a kernfs
page (NUL-terminated, zero-padded), so reading 32 bytes is safe.

BRICK ROOT CAUSE (2026-06-28, the previous build) and the two fixes here:
  * The previous build targeted file offset 0x8A7920, which the eor+RKP-magic
    "safety" asserts ACCEPTED because *every* ROPP function begins that way. But
    0x8A7920 is `gpu_busy_percentage_show` (a *read* handler that snprintf()s into
    a 4096 buffer) — NOT force_no_nap_store. native-init reads
    `/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage` during boot (a90_metrics.c /
    a90_monitor.c), so at boot the hijacked code ran with x2 = output buffer ->
    `str x5,[x4]` to a garbage address -> panic_on_oops=1 -> bootloop.
  * FIX 1 (correct target, semantically verified): the real force_no_nap_store is
    at file offset 0x8A73C8 (vaddr 0xffffff80089273b4), verified by disassembly to
    be a real store (frame, kstrtobool(buf), mutex, set/clear flag, return count).
    The asserts below pin its EXACT first instructions (`sub sp,sp,#0x40` then
    `eor x16,x30,x17`) — a function fingerprint, not just the generic ROPP shape.
    native-init never reads OR writes force_no_nap (verified), and the periodic
    monitor reads gpu_model/gpu_busy_percentage/cur_freq/max_freq/max_gpuclk/temp
    only — NOT force_no_nap — so nothing triggers this handler at boot.
  * FIX 2 (magic guard, defence in depth): the first 8 bytes of `buf` must equal
    MAGIC (0xA90C0DE5DEADBEEF) or the handler does nothing and just returns count.
    So any stray/short write (e.g. an ASCII "0\n") can never trigger a store.

Body (leaf, CFP-safe — no bl/blr, no x30 spill, only direct branches; the blr that
DISPATCHES to us still hits the preserved RKP magic at 0x8A73C4 so JOPP is satisfied;
a leaf `ret` returns the plain x30 so no ROPP eor dance is needed):

    movz x7,#..; movk x7,#..,16; movk x7,#..,32; movk x7,#..,48   ; x7 = MAGIC
    ldr  x4,[x2]            ; candidate magic
    cmp  x4,x7
    b.ne ret_path          ; mismatch -> no store
    ldr  x4,[x2,#8]        ; addr
    ldr  x5,[x2,#16]       ; val
    ldr  x6,[x2,#24]       ; width
    cmp  x6,#8
    b.ne store32
    str  x5,[x4]           ; 64-bit store
    b    ret_path
  store32:
    str  w5,[x4]           ; 32-bit store
  ret_path:
    mov  x0,x3             ; return count
    ret

Protocol (runtime): write 32 LE bytes {u64 magic, u64 addr, u64 val, u64 width};
width==8 -> 64-bit store, else 32-bit. Poke benign DATA only; a poke to an
RKP-protected region (cred/page-tables/.text) still faults under RKP (expected,
out of scope). panic_on_oops should be 0 during runtime poking so a bad poke kills
the writer task, not the device.

OPERATOR research/debug tool on an owned, bootloader-unlocked device (we already
run our own EL1 code by flashing). Grants no new privilege; only removes the
per-experiment flash/reboot cost. Pinned to v2321.
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

import build_kernel_tier2_stage_c_direct_bl_printk as stage_c  # noqa: E402

CYCLE = "TIER2_RUNTIME_POKE_AGENT"
DECISION = "tier2-runtime-poke-agent-corrected-source-build-pass"
BASE_BOOT_SHA256 = stage_c.BASE_BOOT_SHA256
BASE_BOOT = stage_c.BASE_BOOT
OUT_BOOT = workspace_private_input_path(
    "boot_images", "boot_linux_tier2_runtime_poke_agent.img", legacy_fallback=False
)
OUT_DIR = workspace_private_build_path("boot_images", "tier2-runtime-poke-agent")

# CORRECTED target: kgsl_pwrctrl_force_no_nap_store, verified by disassembly of
# clean v2321 (frame + kstrtobool(buf) + mutex + set/clear flag + return count).
ENTRY_OFF = 0x8A73C8          # sub sp,sp,#0x40 (function entry, after RKP magic)
MAGIC_BEFORE_OFF = 0x8A73C4   # 0x00be7bad (RKP/JOPP magic — preserved)
NEXT_MAGIC_OFF = 0x8A749C     # 0x00be7bad (next function — room boundary)
SYSFS_NODE = "/sys/class/kgsl/kgsl-3d0/force_no_nap"

U32_MAGIC = 0x00BE7BAD
U32_FNN_STORE_FIRST = 0xD10103FF   # sub sp, sp, #0x40   (force_no_nap_store fingerprint)
U32_EOR_PROLOGUE = 0xCA1103D0      # eor x16, x30, x17

# Defence-in-depth magic guard value (first qword of the written command).
POKE_MAGIC = 0xA90C0DE5DEADBEEF


def _movz_x(rd: int, imm16: int, shift: int) -> int:
    return 0xD2800000 | ((shift // 16) << 21) | ((imm16 & 0xFFFF) << 5) | rd


def _movk_x(rd: int, imm16: int, shift: int) -> int:
    return 0xF2800000 | ((shift // 16) << 21) | ((imm16 & 0xFFFF) << 5) | rd


def poke_words() -> list[int]:
    """Magic-guarded leaf poke body. Verified independently via objdump."""
    m = POKE_MAGIC
    return [
        _movz_x(7, (m >> 0) & 0xFFFF, 0),
        _movk_x(7, (m >> 16) & 0xFFFF, 16),
        _movk_x(7, (m >> 32) & 0xFFFF, 32),
        _movk_x(7, (m >> 48) & 0xFFFF, 48),
        0xF9400044,  # ldr x4,[x2]     candidate magic
        0xEB07009F,  # cmp x4,x7
        0x54000121,  # b.ne ret_path (+9 -> mov x0,x3)
        0xF9400444,  # ldr x4,[x2,#8]  addr
        0xF9400845,  # ldr x5,[x2,#16] val
        0xF9400C46,  # ldr x6,[x2,#24] width
        0xF10020DF,  # cmp x6,#8
        0x54000061,  # b.ne store32 (+3 -> str w5)
        0xF9000085,  # str x5,[x4]     64-bit
        0x14000002,  # b ret_path (+2)
        0xB9000085,  # store32: str w5,[x4]  32-bit
        0xAA0303E0,  # ret_path: mov x0,x3   return count
        0xD65F03C0,  # ret
    ]


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

    # Semantic asserts: pin the EXACT force_no_nap_store fingerprint (not the generic
    # ROPP shape that fooled the previous build into hijacking a *show* handler).
    if stage_c.u32_at(kernel, MAGIC_BEFORE_OFF) != U32_MAGIC:
        raise RuntimeError("RKP magic before entry not found — offsets stale")
    if stage_c.u32_at(kernel, ENTRY_OFF) != U32_FNN_STORE_FIRST:
        raise RuntimeError("entry is not force_no_nap_store `sub sp,#0x40` — wrong target")
    if stage_c.u32_at(kernel, ENTRY_OFF + 4) != U32_EOR_PROLOGUE:
        raise RuntimeError("second word is not the ROPP eor prologue — wrong target")
    if stage_c.u32_at(kernel, NEXT_MAGIC_OFF) != U32_MAGIC:
        raise RuntimeError("next RKP magic not found — offsets stale")

    room = NEXT_MAGIC_OFF - ENTRY_OFF
    words = poke_words()
    payload = b"".join(stage_c.put_u32(w) for w in words)
    if len(payload) > room:
        raise RuntimeError(f"poke payload too large: {len(payload)} > {room}")
    payload += stage_c.put_u32(stage_c.U32_NOP) * ((room - len(payload)) // 4)

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
        "entry_vaddr": hex(stage_c.kernel_vaddr(ENTRY_OFF)),
        "patch_room": room,
        "patch_len": len(payload),
        "poke_magic": hex(POKE_MAGIC),
        "protocol": (
            "write 32 LE bytes {u64 magic, u64 addr, u64 val, u64 width}; "
            "magic must equal poke_magic or no store; width==8 -> 64-bit store else 32-bit; returns count"
        ),
        "control_flow": {
            "leaf_body": True,
            "no_bl": True,
            "no_blr": True,
            "direct_branches_only": True,
            "no_x30_spill": True,
            "ropp_dance_needed": False,
            "cfp_safe": True,
            "magic_guard": True,
        },
        "brick_root_cause_fixed": (
            "previous build hijacked gpu_busy_percentage_show @0x8A7920 (read at boot); "
            "now correctly targets force_no_nap_store @0x8A73C8 with exact-fingerprint asserts + magic guard"
        ),
    }
    write_private_json(OUT_DIR / "manifest.json", manifest)
    return manifest


def main() -> int:
    print(json.dumps(build_candidate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
