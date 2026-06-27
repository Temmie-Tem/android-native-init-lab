#!/usr/bin/env python3
"""Build the Tier-2 Stage C direct-BL printk kernel-patch candidate."""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import (
    workspace_private_build_path,
    workspace_private_input_path,
    write_private_bytes,
    write_private_json,
)

CYCLE = "TIER2_STAGE_C"
DECISION = "tier2-stage-c-direct-bl-printk-source-build-pass"
BASE_BOOT_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
BASE_BOOT = workspace_private_input_path(
    "boot_images",
    "boot_linux_v2321_usb_clean_identity_rodata.img",
    legacy_fallback=False,
)
OUT_BOOT = workspace_private_input_path(
    "boot_images",
    "boot_linux_tier2_stage_c_direct_bl_printk.img",
    legacy_fallback=False,
)
OUT_DIR = workspace_private_build_path("boot_images", "tier2-stage-c-direct-bl-printk")
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "KERNEL_SECURITY_TIER2_STAGE_C_DIRECT_BL_PRINTK_SOURCE_BUILD_2026-06-28.md"
)

BOOT_MAGIC = b"ANDROID!"
BOOT_PAGE_SIZE = 0x1000
BOOT_ID_OFFSET = 0x240
BOOT_ID_SIZE = 32
KERNEL_BOOT_OFFSET = 0x1000
KERNEL_WRAPPER_RAW_OFFSET = 20
KERNEL_TEXT_VADDR = 0xFFFFFF8008080000
KERNEL_FILE_VADDR_BASE = KERNEL_TEXT_VADDR - KERNEL_WRAPPER_RAW_OFFSET

U32_MAGIC = 0x00BE7BAD
U32_EOR_PROLOGUE = 0xCA1103D0  # eor x16, x30, x17
U32_EOR_EPILOGUE = 0xCA11021E  # eor x30, x16, x17
U32_RET = 0xD65F03C0
U32_NOP = 0xD503201F

KGSL_ANCHOR_OFF = 0x8A6334
KGSL_ANCHOR_WORD = 0x51000503  # sub w3, w8, #1
KGSL_EXPECTED_MAGIC_OFF = 0x8A62EC
KGSL_EXPECTED_ENTRY_OFF = 0x8A62F0
KGSL_EXPECTED_NEXT_MAGIC_OFF = 0x8A635C

PRINTK_REQUIRED_BODY_WORDS = {
    0xA9080BE1,  # stp x1, x2, [sp, #128]
    0xA90913E3,  # stp x3, x4, [sp, #144]
    0xA90A1BE5,  # stp x5, x6, [sp, #160]
    0xF9005BE7,  # str x7, [sp, #176]
    0xAD0007E0,  # stp q0, q1, [sp]
    0xAD010FE2,  # stp q2, q3, [sp, #32]
    0xAD0217E4,  # stp q4, q5, [sp, #64]
    0xAD031FE6,  # stp q6, q7, [sp, #96]
    0xD10123A1,  # sub x1, x29, #0x48 (va_list)
}
PRINTK_VA_HELPER_REQUIRED_BODY_WORDS = {
    0x12800001,  # mov w1, #-1
    0x2A1F03E0,  # mov w0, wzr
    0xAA1F03E2,  # mov x2, xzr
    0xAA1F03E3,  # mov x3, xzr
    0xAA1303E4,  # mov x4, x19 (fmt)
    0x9100A3E5,  # add x5, sp, #0x28 (copied va_list)
}
PRINTK_EXPECTED_ENTRY_OFF = 0xBD8E0
PRINTK_EXPECTED_VA_HELPER_OFF = 0xBD790
PRINTK_EXPECTED_EMIT_CORE_OFF = 0xBBD60

MARKER = b"A90TIER2C\n\x00"


@dataclass(frozen=True)
class BootLayout:
    kernel_size: int
    ramdisk_size: int
    second_size: int
    page_size: int
    kernel_off: int
    ramdisk_off: int
    second_off: int


@dataclass(frozen=True)
class PatchPlan:
    kgsl_magic_off: int
    kgsl_entry_off: int
    kgsl_next_magic_off: int
    printk_magic_off: int
    printk_entry_off: int
    printk_va_helper_off: int
    printk_emit_core_off: int
    marker_off: int
    patch_len: int
    patch_room: int


def u32_at(data: bytes | bytearray, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def put_u32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pages(size: int, page_size: int) -> int:
    return (size + page_size - 1) // page_size


def parse_boot_layout(image: bytes) -> BootLayout:
    if image[:8] != BOOT_MAGIC:
        raise RuntimeError("not an Android boot image")
    (
        kernel_size,
        _kernel_addr,
        ramdisk_size,
        _ramdisk_addr,
        second_size,
        _second_addr,
        _tags_addr,
        page_size,
        _dt_size,
        _unused,
    ) = struct.unpack_from("<10I", image, 8)
    if page_size != BOOT_PAGE_SIZE:
        raise RuntimeError(f"unexpected boot page size: 0x{page_size:x}")
    kernel_off = page_size
    ramdisk_off = kernel_off + pages(kernel_size, page_size) * page_size
    second_off = ramdisk_off + pages(ramdisk_size, page_size) * page_size
    return BootLayout(
        kernel_size=kernel_size,
        ramdisk_size=ramdisk_size,
        second_size=second_size,
        page_size=page_size,
        kernel_off=kernel_off,
        ramdisk_off=ramdisk_off,
        second_off=second_off,
    )


def kernel_vaddr(kernel_file_off: int) -> int:
    return KERNEL_FILE_VADDR_BASE + kernel_file_off


def decode_bl_target(site_vaddr: int, word: int) -> int | None:
    if (word & 0xFC000000) != 0x94000000:
        return None
    imm26 = word & 0x03FFFFFF
    if imm26 & 0x02000000:
        imm26 -= 0x04000000
    return site_vaddr + imm26 * 4


def encode_bl(site_vaddr: int, target_vaddr: int) -> int:
    delta = target_vaddr - site_vaddr
    if delta % 4:
        raise RuntimeError(f"unaligned BL target delta: {delta}")
    imm26 = delta // 4
    if not -(1 << 25) <= imm26 < (1 << 25):
        raise RuntimeError(f"BL target out of range: {delta}")
    return 0x94000000 | (imm26 & 0x03FFFFFF)


def encode_adr_x0(site_vaddr: int, target_vaddr: int) -> int:
    delta = target_vaddr - site_vaddr
    if not -(1 << 20) <= delta < (1 << 20):
        raise RuntimeError(f"ADR target out of range: {delta}")
    imm = delta & 0x1FFFFF
    immlo = imm & 0x3
    immhi = (imm >> 2) & 0x7FFFF
    return 0x10000000 | (immlo << 29) | (immhi << 5)  # rd=x0


def iter_word_offsets(data: bytes, word: int) -> Iterable[int]:
    wanted = put_u32(word)
    start = 0
    while True:
        off = data.find(wanted, start)
        if off < 0:
            return
        if off % 4 == 0:
            yield off
        start = off + 1


def find_previous_ropp_entry(kernel: bytes, anchor_off: int) -> tuple[int, int]:
    for magic_off in range(anchor_off - 4, max(anchor_off - 0x200, 0), -4):
        if u32_at(kernel, magic_off) != U32_MAGIC:
            continue
        if u32_at(kernel, magic_off + 4) == U32_EOR_PROLOGUE:
            return magic_off, magic_off + 4
        if u32_at(kernel, magic_off + 8) == U32_EOR_PROLOGUE:
            return magic_off, magic_off + 8
    raise RuntimeError(f"no ROPP entry found before anchor 0x{anchor_off:x}")


def find_next_magic(kernel: bytes, entry_off: int) -> int:
    for off in range(entry_off + 4, min(entry_off + 0x200, len(kernel) - 4), 4):
        if u32_at(kernel, off) == U32_MAGIC:
            return off
    raise RuntimeError(f"no next RKP magic found after entry 0x{entry_off:x}")


def locate_kgsl_num_pwrlevels(kernel: bytes) -> tuple[int, int, int]:
    if u32_at(kernel, KGSL_ANCHOR_OFF) != KGSL_ANCHOR_WORD:
        raise RuntimeError("Stage-B KGSL anchor is missing at expected offset")
    magic_off, entry_off = find_previous_ropp_entry(kernel, KGSL_ANCHOR_OFF)
    next_magic_off = find_next_magic(kernel, entry_off)
    expected = (KGSL_EXPECTED_MAGIC_OFF, KGSL_EXPECTED_ENTRY_OFF, KGSL_EXPECTED_NEXT_MAGIC_OFF)
    actual = (magic_off, entry_off, next_magic_off)
    if actual != expected:
        raise RuntimeError(f"unexpected KGSL function bounds: actual={actual!r} expected={expected!r}")
    return actual


def function_entry_after_magic(kernel: bytes, magic_off: int) -> int | None:
    if magic_off < 0 or magic_off + 8 >= len(kernel) or u32_at(kernel, magic_off) != U32_MAGIC:
        return None
    if u32_at(kernel, magic_off + 4) == U32_EOR_PROLOGUE:
        return magic_off + 4
    if u32_at(kernel, magic_off + 8) == U32_EOR_PROLOGUE:
        return magic_off + 4
    return None


def function_body_words(kernel: bytes, entry_off: int, max_len: int = 0x400) -> set[int]:
    try:
        next_magic_off = find_next_magic(kernel, entry_off)
    except RuntimeError:
        return set()
    body_end = min(next_magic_off, entry_off + max_len)
    return {u32_at(kernel, off) for off in range(entry_off, body_end, 4)}


def direct_bl_targets(kernel: bytes, entry_off: int, max_len: int = 0x400) -> Iterable[tuple[int, int]]:
    try:
        next_magic_off = find_next_magic(kernel, entry_off)
    except RuntimeError:
        return
    body_end = min(next_magic_off, entry_off + max_len)
    for off in range(entry_off, body_end, 4):
        target = decode_bl_target(kernel_vaddr(off), u32_at(kernel, off))
        if target is not None:
            target_off = target - KERNEL_FILE_VADDR_BASE
            if 0 <= target_off < len(kernel):
                yield off, target_off


def locate_printk_variadic_wrapper(kernel: bytes) -> tuple[int, int, int, int]:
    """Locate the plain printk(fmt, ...) wrapper, not printk_emit(..., fmt, ...)."""

    hits: list[tuple[int, int, int, int]] = []
    for magic_off in iter_word_offsets(kernel, U32_MAGIC):
        entry_off = function_entry_after_magic(kernel, magic_off)
        if entry_off is None:
            continue
        if not PRINTK_REQUIRED_BODY_WORDS.issubset(function_body_words(kernel, entry_off)):
            continue
        for _call_off, helper_off in direct_bl_targets(kernel, entry_off):
            helper_magic_off = helper_off - 4
            helper_entry_off = function_entry_after_magic(kernel, helper_magic_off)
            if helper_entry_off != helper_off:
                continue
            helper_words = function_body_words(kernel, helper_entry_off)
            if not PRINTK_VA_HELPER_REQUIRED_BODY_WORDS.issubset(helper_words):
                continue
            emit_core_off = None
            for _helper_call_off, helper_target_off in direct_bl_targets(kernel, helper_entry_off):
                helper_target_magic_off = helper_target_off - 4
                if (
                    helper_target_off < helper_entry_off
                    and function_entry_after_magic(kernel, helper_target_magic_off) == helper_target_off
                ):
                    emit_core_off = helper_target_off
                    break
            if emit_core_off is not None:
                hits.append((magic_off, entry_off, helper_entry_off, emit_core_off))
    if len(hits) != 1:
        raise RuntimeError(f"expected one plain printk variadic-wrapper signature hit, found {len(hits)}")
    hit = hits[0]
    expected = (
        PRINTK_EXPECTED_ENTRY_OFF - 4,
        PRINTK_EXPECTED_ENTRY_OFF,
        PRINTK_EXPECTED_VA_HELPER_OFF,
        PRINTK_EXPECTED_EMIT_CORE_OFF,
    )
    if hit != expected:
        raise RuntimeError(f"unexpected printk signature hit: actual={hit!r} expected={expected!r}")
    return hit


def build_injection(entry_off: int, next_magic_off: int, printk_entry_off: int) -> tuple[bytes, int]:
    room = next_magic_off - entry_off
    code_words: list[int] = []
    entry_vaddr = kernel_vaddr(entry_off)
    marker_off = entry_off + 9 * 4
    marker_vaddr = kernel_vaddr(marker_off)
    code_words.extend([
        U32_EOR_PROLOGUE,
        0xA9BF43FD,  # stp x29, x16, [sp, #-16]!
        0x910003FD,  # mov x29, sp
        encode_adr_x0(entry_vaddr + 3 * 4, marker_vaddr),
        encode_bl(entry_vaddr + 4 * 4, kernel_vaddr(printk_entry_off)),
        0xA8C143FD,  # ldp x29, x16, [sp], #16
        U32_EOR_EPILOGUE,
        0x528000A0,  # mov w0, #5
        U32_RET,
    ])
    payload = b"".join(put_u32(word) for word in code_words) + MARKER
    while len(payload) % 4:
        payload += b"\x00"
    if len(payload) > room:
        raise RuntimeError(f"injection payload too large: {len(payload)} > {room}")
    payload += put_u32(U32_NOP) * ((room - len(payload)) // 4)
    return payload, marker_off


def recompute_boot_id(image: bytearray, layout: BootLayout) -> bytes:
    kernel = bytes(image[layout.kernel_off : layout.kernel_off + layout.kernel_size])
    ramdisk = bytes(image[layout.ramdisk_off : layout.ramdisk_off + layout.ramdisk_size])
    digest = hashlib.sha1()
    digest.update(kernel)
    digest.update(struct.pack("<I", layout.kernel_size))
    digest.update(ramdisk)
    digest.update(struct.pack("<I", layout.ramdisk_size))
    digest.update(b"")
    digest.update(struct.pack("<I", 0))
    digest.update(struct.pack("<I", 0))
    boot_id = digest.digest() + b"\x00" * (BOOT_ID_SIZE - digest.digest_size)
    image[BOOT_ID_OFFSET : BOOT_ID_OFFSET + BOOT_ID_SIZE] = boot_id
    return boot_id


def changed_offsets(before: bytes, after: bytes) -> list[int]:
    if len(before) != len(after):
        raise RuntimeError("image size changed")
    return [index for index, (left, right) in enumerate(zip(before, after)) if left != right]


def contiguous_ranges(values: list[int]) -> list[tuple[int, int]]:
    if not values:
        return []
    ranges: list[tuple[int, int]] = []
    start = prev = values[0]
    for value in values[1:]:
        if value == prev + 1:
            prev = value
            continue
        ranges.append((start, prev + 1))
        start = prev = value
    ranges.append((start, prev + 1))
    return ranges


def build_candidate() -> dict[str, object]:
    base_sha = sha256_file(BASE_BOOT)
    if base_sha != BASE_BOOT_SHA256:
        raise RuntimeError(f"unexpected v2321 SHA256: {base_sha}")
    original = BASE_BOOT.read_bytes()
    patched = bytearray(original)
    layout = parse_boot_layout(original)
    kernel = bytes(original[layout.kernel_off : layout.kernel_off + layout.kernel_size])
    if kernel[:16] != b"UNCOMPRESSED_IMG":
        raise RuntimeError("kernel wrapper is not UNCOMPRESSED_IMG")
    kgsl_magic_off, kgsl_entry_off, kgsl_next_magic_off = locate_kgsl_num_pwrlevels(kernel)
    printk_magic_off, printk_entry_off, printk_va_helper_off, printk_emit_core_off = (
        locate_printk_variadic_wrapper(kernel)
    )
    payload, marker_off = build_injection(kgsl_entry_off, kgsl_next_magic_off, printk_entry_off)
    patch_abs_off = layout.kernel_off + kgsl_entry_off
    patched[patch_abs_off : patch_abs_off + len(payload)] = payload
    boot_id = recompute_boot_id(patched, layout)
    diff_offsets = changed_offsets(original, bytes(patched))
    allowed_kernel = set(range(patch_abs_off, patch_abs_off + len(payload)))
    allowed_id = set(range(BOOT_ID_OFFSET, BOOT_ID_OFFSET + BOOT_ID_SIZE))
    unexpected = [off for off in diff_offsets if off not in allowed_kernel and off not in allowed_id]
    if unexpected:
        raise RuntimeError(f"unexpected patched offsets outside kernel/id contract: {unexpected[:8]}")
    write_private_bytes(OUT_BOOT, bytes(patched))
    out_sha = sha256_file(OUT_BOOT)
    diff_ranges = contiguous_ranges(diff_offsets)
    manifest = {
        "cycle": CYCLE,
        "decision": DECISION,
        "base_boot": str(BASE_BOOT.relative_to(REPO_ROOT)),
        "base_sha256": base_sha,
        "out_boot": str(OUT_BOOT.relative_to(REPO_ROOT)),
        "out_sha256": out_sha,
        "boot_id": boot_id[:20].hex(),
        "diff_byte_count": len(diff_offsets),
        "diff_ranges": [[hex(start), hex(stop)] for start, stop in diff_ranges],
        "kernel_boot_offset": hex(layout.kernel_off),
        "kernel_size": layout.kernel_size,
        "kgsl_magic_off": hex(kgsl_magic_off),
        "kgsl_entry_off": hex(kgsl_entry_off),
        "kgsl_entry_vaddr": hex(kernel_vaddr(kgsl_entry_off)),
        "kgsl_next_magic_off": hex(kgsl_next_magic_off),
        "kgsl_patch_room": kgsl_next_magic_off - kgsl_entry_off,
        "kgsl_patch_len": len(payload),
        "marker": MARKER.decode("ascii", errors="replace")
        .replace("\n", "\\n")
        .replace("\x00", "\\0"),
        "marker_off": hex(marker_off),
        "marker_vaddr": hex(kernel_vaddr(marker_off)),
        "printk_magic_off": hex(printk_magic_off),
        "printk_entry_off": hex(printk_entry_off),
        "printk_entry_vaddr": hex(kernel_vaddr(printk_entry_off)),
        "printk_va_helper_off": hex(printk_va_helper_off),
        "printk_va_helper_vaddr": hex(kernel_vaddr(printk_va_helper_off)),
        "printk_emit_core_off": hex(printk_emit_core_off),
        "printk_emit_core_vaddr": hex(kernel_vaddr(printk_emit_core_off)),
        "control_flow": {
            "new_direct_bl": True,
            "bl_target": "plain-printk-variadic-wrapper-signature",
            "no_blr": True,
            "preserves_x17": True,
            "ropp_prologue": "eor x16,x30,x17; stp x29,x16,[sp,#-16]!",
            "ropp_epilogue": "ldp x29,x16,[sp],#16; eor x30,x16,x17; ret",
        },
    }
    write_private_json(OUT_DIR / "manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    return manifest


def render_report(manifest: dict[str, object]) -> str:
    return "\n".join([
        "# Kernel Security Tier-2 Stage C Direct-BL Printk Source Build",
        "",
        f"- Cycle: `{CYCLE}`",
        f"- Decision: `{DECISION}`",
        f"- Base boot: `{manifest['base_boot']}`",
        f"- Base SHA256: `{manifest['base_sha256']}`",
        f"- Candidate boot: `{manifest['out_boot']}`",
        f"- Candidate SHA256: `{manifest['out_sha256']}`",
        "",
        "## What Changed",
        "",
        "- Direct-patched clean V2321 kernel `.text` only; no ramdisk/native-init changes.",
        "- Replaced the reachable `kgsl_pwrctrl_num_pwrlevels_show` body with a ROPP-correct stub.",
        "- The stub preserves `x17`, loads an in-function `A90TIER2C` marker, executes one new direct `bl` to the printk variadic-wrapper signature target, restores the ROPP return address, returns `5`, and leaves the following RKP magic word intact.",
        "- Recomputed only the Android boot header v1 `id` after the kernel patch.",
        "",
        "## Signature Evidence",
        "",
        f"- KGSL entry: `{manifest['kgsl_entry_vaddr']}` at kernel offset `{manifest['kgsl_entry_off']}`.",
        f"- KGSL patch room: `{manifest['kgsl_patch_room']}` bytes; payload length `{manifest['kgsl_patch_len']}` bytes.",
        f"- Marker: `{manifest['marker']}` at `{manifest['marker_vaddr']}`.",
        f"- Printk target: `{manifest['printk_entry_vaddr']}` at kernel offset `{manifest['printk_entry_off']}`.",
        f"- Printk target was located by the plain `printk(fmt, ...)` variadic-wrapper signature: RKP marker, stack frame, `x1..x7` and `q0..q7` vararg spills, va_list setup, and a direct call into the printk va_list helper at `{manifest['printk_va_helper_vaddr']}` / emit core at `{manifest['printk_emit_core_vaddr']}`.",
        "",
        "## Diff Contract",
        "",
        f"- Changed byte count: `{manifest['diff_byte_count']}`.",
        f"- Changed ranges: `{manifest['diff_ranges']}`.",
        "- Allowed ranges are the injected KGSL function body and the 32-byte boot header `id`; the builder fails if any other byte changes.",
        "",
        "## Live Gate",
        "",
        "- Not run by this source-build step.",
        "- Required next: flash only via `native_init_flash.py`, confirm boot/selftest, set `panic_on_oops=0`, read `/sys/class/kgsl/kgsl-3d0/num_pwrlevels`, grep dmesg for `A90TIER2C`, restore `panic_on_oops=1`, roll back to clean V2321, and confirm `selftest fail=0`.",
        "",
        "## Safety",
        "",
        "- RECON only: no UAF, grooming, EL1 exploit attempt, forbidden partition write, raw flash path, power write, or `blr`/indirect-branch patch.",
    ]) + "\n"


def main() -> int:
    manifest = build_candidate()
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
