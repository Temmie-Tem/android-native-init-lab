#!/usr/bin/env python3
"""Tier-2 runtime kernel REPL v1 call-pair variant.

This is a deliberately narrow companion image for the one remaining ABI gap:
small aggregate returns on arm64.  The normal v1-repl image prints only the
post-call x0 register, so it can prove only the first lane of a two-register
struct return.  This variant keeps the same magic/op layout and patch target,
but changes the call printout to:

    R%llx:%llx\n

where the two fields are post-call x0 and x1.  It is not a replacement for the
normal v1-repl resident image and should only be used for bounded return-pair
proofs such as current_kernel_time64().
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

import build_kernel_tier2_repl_v1_repl as v1repl  # noqa: E402


CYCLE = "TIER2_REPL_V1_CALL_PAIR"
DECISION = "tier2-repl-v1-call-pair-source-build-pass"
OUT_BOOT = workspace_private_input_path(
    "boot_images", "boot_linux_tier2_repl_v1_call_pair.img", legacy_fallback=False
)
OUT_DIR = workspace_private_build_path("boot_images", "tier2-repl-v1-call-pair")

FORMAT = b"R%llx:%llx\n\x00"
CALL_MOV_X2_X1_WORD_INDEX = 40
CALL_MOV_X1_X0_WORD_INDEX = 41


def build_call_pair_injection(entry_off: int,
                              next_magic_off: int,
                              printk_entry_off: int) -> bytes:
    payload = bytearray(v1repl.build_repl_injection(entry_off, next_magic_off, printk_entry_off))

    struct.pack_into(
        "<I",
        payload,
        CALL_MOV_X2_X1_WORD_INDEX * 4,
        v1repl.encode_mov_x(2, 1),
    )
    struct.pack_into(
        "<I",
        payload,
        CALL_MOV_X1_X0_WORD_INDEX * 4,
        v1repl.encode_mov_x(1, 0),
    )
    if len(FORMAT) != v1repl.EXPECTED_PATCH_LEN - v1repl.FORMAT_WORD_INDEX * 4:
        raise RuntimeError(f"call-pair format must exactly fill the literal tail: {len(FORMAT)}")
    payload[v1repl.FORMAT_WORD_INDEX * 4:] = FORMAT
    if len(payload) != v1repl.EXPECTED_PATCH_LEN:
        raise RuntimeError(f"unexpected call-pair payload length: {len(payload)}")
    return bytes(payload)


def build_candidate() -> dict[str, object]:
    base_sha = v1repl.stage_c.sha256_file(v1repl.BASE_BOOT)
    if base_sha != v1repl.BASE_BOOT_SHA256:
        raise RuntimeError(f"unexpected v2321 SHA256: {base_sha}")
    original = v1repl.BASE_BOOT.read_bytes()
    patched = bytearray(original)
    layout = v1repl.stage_c.parse_boot_layout(original)
    kernel = bytes(original[layout.kernel_off : layout.kernel_off + layout.kernel_size])
    if kernel[:16] != b"UNCOMPRESSED_IMG":
        raise RuntimeError("kernel wrapper is not UNCOMPRESSED_IMG")
    v1repl._assert_force_no_nap_store_fingerprint(kernel)

    _printk_magic_off, printk_entry_off, _va_helper_off, _emit_core_off = (
        v1repl.stage_c.locate_printk_variadic_wrapper(kernel)
    )
    printk_vaddr = v1repl.stage_c.kernel_vaddr(printk_entry_off)
    if printk_vaddr != v1repl.PRINTK_ENTRY_VADDR:
        raise RuntimeError(f"plain printk target drifted: 0x{printk_vaddr:x}")
    payload = build_call_pair_injection(v1repl.ENTRY_OFF, v1repl.NEXT_MAGIC_OFF, printk_entry_off)

    patch_abs_off = layout.kernel_off + v1repl.ENTRY_OFF
    patched[patch_abs_off : patch_abs_off + len(payload)] = payload
    patched_kernel = bytes(patched[layout.kernel_off : layout.kernel_off + layout.kernel_size])
    if v1repl.stage_c.u32_at(patched_kernel, v1repl.MAGIC_BEFORE_OFF) != v1repl.JOPP_MAGIC:
        raise RuntimeError("patched image clobbered previous RKP magic")
    if v1repl.stage_c.u32_at(patched_kernel, v1repl.NEXT_MAGIC_OFF) != v1repl.JOPP_MAGIC:
        raise RuntimeError("patched image clobbered next RKP magic")

    boot_id = v1repl.stage_c.recompute_boot_id(patched, layout)
    diff_offsets = v1repl.stage_c.changed_offsets(original, bytes(patched))
    allowed_kernel = set(range(patch_abs_off, patch_abs_off + len(payload)))
    allowed_id = set(
        range(v1repl.stage_c.BOOT_ID_OFFSET, v1repl.stage_c.BOOT_ID_OFFSET + v1repl.stage_c.BOOT_ID_SIZE)
    )
    unexpected = [off for off in diff_offsets if off not in allowed_kernel and off not in allowed_id]
    if unexpected:
        raise RuntimeError(f"unexpected patched offsets outside contract: {unexpected[:8]}")

    write_private_bytes(OUT_BOOT, bytes(patched))
    os.chmod(OUT_BOOT, 0o600)
    body_path = OUT_DIR / "force_no_nap_store_v1_call_pair_body.bin"
    write_private_bytes(body_path, payload)
    out_sha = v1repl.stage_c.sha256_file(OUT_BOOT)
    entry_vaddr = v1repl.stage_c.kernel_vaddr(v1repl.ENTRY_OFF)
    manifest = {
        "cycle": CYCLE,
        "decision": DECISION,
        "base_boot": str(v1repl.BASE_BOOT.relative_to(REPO_ROOT)),
        "base_sha256": base_sha,
        "out_boot": str(OUT_BOOT.relative_to(REPO_ROOT)),
        "out_sha256": out_sha,
        "out_mode": oct(OUT_BOOT.stat().st_mode & 0o777),
        "boot_id": boot_id[:20].hex(),
        "diff_byte_count": len(diff_offsets),
        "diff_ranges": [[hex(a), hex(b)] for a, b in v1repl.stage_c.contiguous_ranges(diff_offsets)],
        "hijacked_handler": "kgsl_pwrctrl_force_no_nap_store",
        "sysfs_node": v1repl.SYSFS_NODE,
        "entry_off": hex(v1repl.ENTRY_OFF),
        "entry_vaddr": hex(entry_vaddr),
        "patch_room": v1repl.NEXT_MAGIC_OFF - v1repl.ENTRY_OFF,
        "patch_len": len(payload),
        "body_bin": str(body_path.relative_to(REPO_ROOT)),
        "repl_magic": hex(v1repl.REPL_MAGIC),
        "jopp_magic": hex(v1repl.JOPP_MAGIC),
        "printk_entry_vaddr": hex(printk_vaddr),
        "format": FORMAT.decode("ascii").replace("\n", "\\n").replace("\x00", "\\0"),
        "adr_self_word_index": v1repl.ADR_SELF_WORD_INDEX,
        "adr_self_link_vaddr": hex(entry_vaddr + v1repl.ADR_SELF_WORD_INDEX * 4),
        "slide_formula": "slide = first_pair_field - adr_self_link_vaddr",
        "protocol_delta": {
            "base": "v1-repl magic/op layout",
            "call_output": "printk line R%llx:%llx with post-call x0:x1",
            "word40": "mov x2,x1",
            "word41": "mov x1,x0",
            "format_tail": FORMAT.decode("ascii").replace("\n", "\\n").replace("\x00", "\\0"),
        },
        "ops": {
            "0": "slide: first pair field is runtime PC of adr_self instruction",
            "1": "peek: first pair field is qword at addr; second pair field is ignored",
            "2": "poke: first pair field is stored value; second pair field is ignored",
            "3": "call: blr target with x0..x7, then printk return x0:x1",
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
