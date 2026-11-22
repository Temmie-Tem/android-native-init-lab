#!/usr/bin/env python3
"""Build the S20+ rooted-Android loader control in private host storage."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import shutil
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import build_s20plus_n3u0_magisk_overlay as resident

UPSTREAM = "7781b33c87ccde3e57bb744c5b8bccdbedfa4bc3"
TOOLCHAIN = "aarch64-linux-gnu-"
PAGE = 4096


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def split_boot(boot):
    header = boot[:PAGE]

    def field(offset):
        return struct.unpack_from("<I", header, offset)[0]

    require(header[:8] == b"ANDROID!" and field(36) == PAGE and field(40) == 2
            and field(1644) == 1660 and boot[-64:-60] == b"AVBf",
            "unexpected Android v2 header or footer")
    require(field(24) == 0 and field(1632) == 0, "unexpected second or recovery DTBO")
    offset, parts = PAGE, []
    for size in (field(8), field(16), field(1648)):
        require(size > 0 and offset + size < len(boot) - 64, "invalid member extent")
        parts.append(boot[offset:offset + size])
        offset += (size + PAGE - 1) & -PAGE
    return header, *parts


def audit_guard(elf, output):
    text = subprocess.check_output(
        [TOOLCHAIN + "objdump", "-d", "--disassemble=y2q_guard", elf], text=True
    )
    (output / "guard-disassembly.txt").write_text(text)
    instructions = re.findall(
        r"^[ \t]*[0-9a-f]+:[ \t]+[0-9a-f]{8}[ \t]+([^\s]+)[ \t]*(.*)$", text, re.M)
    symbols = subprocess.check_output([TOOLCHAIN + "nm", "-S", elf], text=True)
    symbol = re.search(r"^[0-9a-f]+ ([0-9a-f]+) T y2q_guard$", symbols, re.M)
    require(symbol and len(instructions) * 4 == int(symbol[1], 16)
            and any(op == "ret" for op, _ in instructions), "incomplete guard disassembly")
    forbidden = {"bl", "blr", "br", "dc", "ic", "msr", "mrs", "svc", "hvc", "smc", "eret"}
    require(all(not op.startswith(("st", "cas", "swp")) and op not in forbidden
                and not re.search(r"\b(?:sp|wsp|[xw]28|[xw]29|[xw]30)\b", args)
                for op, args in instructions), "pre-stack guard emitted a side effect")
    return len(instructions)


def compile_prefix(upstream, output):
    flags = [
        "-Os", "-ffreestanding", "-fno-builtin", "-fno-stack-protector",
        "-fomit-frame-pointer", "-fpie", "-mstrict-align", "-mgeneral-regs-only",
        "-ffunction-sections", "-fdata-sections", "-fno-asynchronous-unwind-tables",
        "-I", HERE, "-I", output, "-I", upstream / "include",
        "-I", upstream / "include/lib/libfdt", "-I", upstream / "lib/unic",
        "-I", upstream / "arch/aarch64",
    ]
    units = [
        HERE / "uniloader_entry.S", HERE / "uniloader_guard.c", HERE / "uniloader_fdt.c",
        upstream / "lib/unic/string.c", upstream / "arch/aarch64/memcpy.S",
        *(upstream / "lib/libfdt" / name for name in ("fdt.c", "fdt_ro.c", "fdt_rw.c")),
    ]
    objects = []
    with (output / "toolchain.log").open("xb") as log:
        for unit in units:
            obj = output / (unit.stem + ".o")
            extra = []
            if unit.name == "uniloader_guard.c":
                extra = ["-O2", "-fno-jump-tables", "-ffixed-x28", "-ffixed-x29",
                         "-ffixed-x30", *(f"-fcall-used-x{i}" for i in range(19, 28))]
            if unit.parent == HERE:
                extra += ["-Wall", "-Wextra", "-Werror"]
            subprocess.run([TOOLCHAIN + "gcc", *flags, *extra, "-c", unit, "-o", obj],
                           check=True, stdout=log, stderr=log)
            objects.append(obj)
        elf, binary = output / "prefix.elf", output / "prefix.bin"
        subprocess.run([TOOLCHAIN + "ld", "--gc-sections", "-T", HERE / "uniloader_prefix.lds",
                        "-o", elf, *objects], check=True, stdout=log, stderr=log)
        subprocess.run([TOOLCHAIN + "objcopy", "-O", "binary", elf, binary],
                       check=True, stdout=log, stderr=log)
    return binary.read_bytes(), audit_guard(elf, output)


def build(source, output):
    output = output.resolve()
    require(output.is_relative_to(ROOT / "workspace/private") and
            output != ROOT / "workspace/private", "private output required")
    original = resident.exact_receipt(
        resident.BASE_BOOT, "resident boot", size=resident.BASE_BOOT_SIZE,
        sha256=resident.BASE_BOOT_SHA256)
    magiskboot = resident.exact_receipt(
        resident.MAGISKBOOT, "magiskboot", size=resident.MAGISKBOOT_SIZE,
        sha256=resident.MAGISKBOOT_SHA256)
    output.mkdir(mode=0o700, parents=True)
    upstream = output / "upstream"
    upstream.mkdir()
    archive = output / "upstream.tar"
    with archive.open("xb") as stream:
        subprocess.run(["git", "-C", source, "archive", UPSTREAM], stdout=stream, check=True)
    shutil.unpack_archive(archive, upstream, filter="data")
    marker = secrets.token_hex(32)
    (output / "uniloader_marker.h").write_text(f'#define Y2Q_MARKER "{marker}"\n')

    original_bytes = resident.BASE_BOOT.read_bytes()
    require(hashlib.sha256(original_bytes).hexdigest() == original["sha256"],
            "resident input changed while reading")
    old_header, vendor, ramdisk, dtb = split_boot(original_bytes)
    text_offset, image_size, flags = struct.unpack_from("<QQQ", vendor, 8)
    require(vendor[56:60] == b"ARMd" and (text_offset, image_size, flags) == (0x80000, 70512640, 10)
            and hashlib.sha256(vendor).hexdigest() == resident.BASE_KERNEL_SHA256
            and hashlib.sha256(dtb).hexdigest() == resident.BASE_DTB_SHA256,
            "resident Image or DTB changed")

    prefix, instructions = compile_prefix(upstream, output)
    payload_offset = 0x200000
    require(prefix[56:60] == b"ARMd" and struct.unpack_from("<QQQ", prefix, 8) ==
            (text_offset, image_size + payload_offset, flags) and len(prefix) <= 0x20000,
            "wrapper Image header or prefix extent differs")
    image = prefix.ljust(payload_offset, b"\0") + vendor
    unpack = output / "unpack"
    unpack.mkdir()
    resident.run_command([resident.MAGISKBOOT, "unpack", "-h", resident.BASE_BOOT], cwd=unpack)
    require((unpack / "kernel").read_bytes() == vendor and (unpack / "dtb").read_bytes() == dtb,
            "unpacker disagrees with v2 layout")
    (unpack / "kernel").write_bytes(image)
    boot = output / "boot.img"
    (output / "repack.log").write_bytes(resident.run_command(
        [resident.MAGISKBOOT, "repack", resident.BASE_BOOT, boot], cwd=unpack))
    result = resident.exact_receipt(boot, "H0 boot", size=resident.BASE_BOOT_SIZE)
    new_header, new_kernel, new_ramdisk, new_dtb = split_boot(boot.read_bytes())
    require(new_header[:8] + new_header[12:576] + new_header[608:] ==
            old_header[:8] + old_header[12:576] + old_header[608:] and
            (new_kernel, new_ramdisk, new_dtb) == (image, ramdisk, dtb),
            "repack changed the Image or preserved boot members")
    resident.exact_receipt(resident.BASE_BOOT, "resident boot", size=resident.BASE_BOOT_SIZE,
                           sha256=resident.BASE_BOOT_SHA256)
    (output / "Image").write_bytes(image)
    (output / "result.json").write_text(json.dumps({
        "status": "H0_Y2Q_UNILOADER_ANDROID_BOOT_BUILT",
        "target": resident.TARGET,
        "upstream": UPSTREAM,
        "inputs": {
            "resident_boot": original,
            "magiskboot": magiskboot,
            "upstream_archive": resident.exact_receipt(archive, "upstream archive"),
            "sources": {name: resident.exact_receipt(HERE / name, name) for name in (
                "uniloader_entry.S", "uniloader_guard.c", "uniloader_fdt.c",
                "uniloader_prefix.lds", "uniloader_layout.h", Path(__file__).name)},
        },
        "boot": result,
        "image": resident.exact_receipt(output / "Image", "wrapped Image"),
        "marker": marker,
        "guard_instruction_count": instructions,
        "payload_offset": payload_offset,
        "device_commands": 0,
    }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    build(options.upstream, options.output)
