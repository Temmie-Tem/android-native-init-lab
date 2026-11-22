"""Build the y2q raw RAM handoff for host qualification."""

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
PRIVATE = HERE.parents[5] / "workspace/private"
BENCH = PRIVATE / "outputs/s20plus-y2q-mainline-h0-20261122.yy9l1A"
MODEL = PRIVATE / "analysis/s20plus-y2q-boot-map-20261123/fixture-inputs.json"
SOURCE = (
    PRIVATE / "outputs/s20plus-y2q-uniloader-proca-h0-20261123/control-3/upstream.tar"
)
TOOL = "aarch64-linux-gnu-"
ALIGN = 2 << 20


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_bound(path, sha):
    data = path.read_bytes()
    if digest(data) != sha:
        raise ValueError(f"changed input {path.name}")
    return data


def aligned(value, unit):
    return (value + unit - 1) & -unit


def disjoint(first, second):
    return first[1] <= second[0] or second[1] <= first[0]


def firmware_log_range():
    config = read_bound(
        MODEL.with_name("uefiplat.cfg"),
        "4baa30e661d8978b0258f1633bbce0e8ccee84aa7e3818db0e12298d1aa6eb60",
    )
    memory = config.decode("ascii").split("[MemoryMap]")[1].split("[RegisterMap]")[0]
    entries = csv.reader(
        (line for line in memory.splitlines() if line.lstrip().startswith("0x")),
        skipinitialspace=True,
    )
    rows = [row for row in entries if row[2].strip() == "SEC LOG"]
    if len(rows) != 1 or [cell.strip() for cell in rows[0][3:5]] != [
        "NoHob",
        "MMAP_IO",
    ]:
        raise ValueError("ambiguous firmware log mapping")
    first, length = (int(cell, 16) for cell in rows[0][:2])
    return first, first + length


def layout(model, image, board, initrd):
    text_offset, runtime, flags = struct.unpack_from("<3Q", image, 8)
    if image[56:60] != b"ARMd" or (text_offset, runtime, flags) != (0, 0x480000, 10):
        raise ValueError("mainline Image header differs")
    first, sweep_end = model["source_sweep"]
    last = first + 63 * 32768
    data_offset = ALIGN + 65536
    kernel_offset = aligned(data_offset + len(board) + len(initrd), 4096)
    file_size = kernel_offset + len(image)
    dt = aligned(last + file_size, ALIGN)
    stack_top = dt + ALIGN + 131072
    dest = model["destination"]
    rd, fp = model["ramdisk"], model["fdt"]
    page = 4096
    limit = model["region"] + model["span"]
    if (
        rd != limit - aligned(len(initrd), page) - page
        or fp != rd - ALIGN - page
        or first != model["region"] + 0x80000
        or last + file_size > fp
        or first + file_size + ALIGN > fp
    ):
        raise ValueError("input differs from firmware placement rules")
    if dest % ALIGN or not first <= dt < stack_top <= sweep_end:
        raise ValueError("layout exceeds measured envelope")
    writes = [(dt, stack_top), (dest, dest + runtime)]
    excluded = [*model["static_clipped"], (fp, model["region"] + model["span"])]
    if not disjoint(*writes) or any(
        not disjoint(w, r) for w in writes for r in excluded
    ):
        raise ValueError("reserved output")
    for slot in range(64):
        base = first + slot * 32768
        source = (base, base + file_size)
        body = (base + ALIGN, source[1])
        if source[1] > sweep_end or any(not disjoint(source, w) for w in writes):
            raise ValueError("source overlaps output")
        if any(not disjoint(body, r) for r in excluded):
            raise ValueError("post-branch input overlaps reservation")
    # The placement projection clips reservations at the Kernel region. Linux
    # can later use other banks, so carry the entire firmware log declaration.
    fw_lo, fw_hi = firmware_log_range()
    if not (
        fw_lo < fw_hi
        and all(fw_lo <= a < b <= fw_hi for a, b in model["static_clipped"])
    ):
        raise ValueError("new firmware exclusion requires qualification")
    return dict(
        IN_FDT=fp,
        IN_RD=rd,
        IN_RD_END=rd + len(initrd),
        FDT_CAP=ALIGN,
        SRC_MIN=first,
        SRC_MAX=last,
        DATA_OFF=data_offset,
        KERNEL_OFF=kernel_offset,
        IMG_SIZE=len(image),
        FILE_END=file_size,
        OUT_KERNEL=dest,
        KERNEL_RUNTIME=runtime,
        OUT_FDT=dt,
        STACK_TOP=stack_top,
        FW_LO=fw_lo,
        FW_LEN=fw_hi - fw_lo,
        RD_SIZE=len(initrd),
    )


def audit_leaf(elf, sym):
    asm = subprocess.check_output(
        [TOOL + "objdump", "-d", "--disassemble=" + sym, elf], text=True
    )
    rows = re.findall(
        r"^[ \t]*[0-9a-f]+:[ \t]+[0-9a-f]{8}[ \t]+(\S+)[ \t]*(.*)$", asm, re.M
    )
    sizes = subprocess.check_output([TOOL + "nm", "-S", elf], text=True)
    size = re.search(r"^[0-9a-f]+ ([0-9a-f]+) T " + sym + "$", sizes, re.M)
    if (
        not size
        or len(rows) * 4 != int(size[1], 16)
        or not any(op == "ret" for op, _ in rows)
    ):
        raise ValueError("incomplete leaf disassembly")
    for op, args in rows:
        if (
            op.startswith(("st", "cas", "swp", "ldadd", "ldclr", "ldset", "ldeor"))
            or op
            in {
                "bl",
                "blr",
                "br",
                "msr",
                "mrs",
                "dc",
                "ic",
                "svc",
                "smc",
                "hvc",
                "eret",
            }
            or re.search(r"\b(?:sp|wsp)\b", args)
        ):
            raise ValueError(f"pre-stack operation in {sym}: {op}")
    return len(rows)


def build(output):
    output = output.resolve()
    if not output.is_relative_to(PRIVATE) or output == PRIVATE:
        raise ValueError("private build directory required")
    model = json.loads(
        read_bound(
            MODEL, "7866183bf68ba52b9268a8e88e24be5a3db04625f40208d9f9d3aa48326a309c"
        )
    )
    image = read_bound(
        BENCH / "kernel-build/arch/arm64/boot/Image",
        "907811f72a251c0e67647e2a8375143037188ce29a891d07411da1355a272fe8",
    )
    board = read_bound(
        BENCH / "sm8250-samsung-y2q-h0.dtb",
        "d84c08ac2d429637d0a381865d95de8a5a942f8baa554aa5f7473a9cd6934b14",
    )
    initrd = read_bound(
        BENCH / "initramfs.cpio.gz",
        "46757f90128509a95836df46dbab0a1b66af21c10522e6497780f57c32280a46",
    )
    cfg = layout(model, image, board, initrd)
    archive = read_bound(
        SOURCE, "ab91352dc1d189ab43dab4883248b8a4a87a77e09fe10e83dd1122674f1bc88e"
    )
    output.mkdir(mode=0o700, exist_ok=False)
    (output / "upstream.tar").write_bytes(archive)
    upstream = output / "upstream"
    with tarfile.open(output / "upstream.tar") as t:
        t.extractall(upstream, filter="data")
    for name, data in [
        ("bound-board.dtb", board),
        ("bound-initrd.gz", initrd),
        ("bound-Image", image),
    ]:
        (output / name).write_bytes(data)
    (output / "layout.h").write_text(
        "".join(f"#define {k} 0x{v:x}\n" for k, v in cfg.items())
    )
    flags = [
        "-Os",
        "-ffreestanding",
        "-fno-builtin",
        "-fno-stack-protector",
        "-fomit-frame-pointer",
        "-fpie",
        "-mstrict-align",
        "-mgeneral-regs-only",
        "-ffunction-sections",
        "-fdata-sections",
        "-fno-asynchronous-unwind-tables",
        "-I",
        output,
        "-I",
        upstream / "include",
        "-I",
        upstream / "include/lib/libfdt",
        "-I",
        upstream / "lib/unic",
        "-I",
        upstream / "arch/aarch64",
    ]
    units = [
        HERE / "entry.S",
        HERE / "guard.c",
        HERE / "compose.c",
        upstream / "lib/unic/string.c",
        HERE / "early-memory.c",
        *(upstream / "lib/libfdt" / f for f in ("fdt.c", "fdt_ro.c", "fdt_rw.c")),
    ]
    objects = []
    with (output / "toolchain.log").open("xb") as log:

        def run(args):
            subprocess.run(args, cwd=output, stdout=log, stderr=log, check=True)

        for unit in units:
            extra = []
            # The retained unic memset omits its final byte tail. Use the same
            # strictly byte-addressed operations for all libfdt mutations.
            if unit == upstream / "lib/unic/string.c":
                extra.append("-Dmemset=unused_unic_memset")
            if unit.parent == HERE:
                extra += ["-Wall", "-Wextra", "-Werror"]
            if unit.name == "guard.c":
                extra += [
                    "-O2",
                    "-fno-jump-tables",
                    "-ffixed-x28",
                    "-ffixed-x29",
                    "-ffixed-x30",
                    *[f"-fcall-used-x{i}" for i in range(19, 28)],
                ]
            obj = output / (unit.stem + ".o")
            run([TOOL + "gcc", *flags, *extra, "-c", unit, "-o", obj])
            objects.append(obj)
        run(
            [
                TOOL + "gcc",
                "-E",
                "-P",
                "-x",
                "assembler-with-cpp",
                "-I",
                output,
                HERE / "link.lds.S",
                "-o",
                "link.lds",
            ]
        )
        run(
            [
                TOOL + "ld",
                "--gc-sections",
                "-T",
                "link.lds",
                "-o",
                "handoff.elf",
                *objects,
            ]
        )
        run([TOOL + "objcopy", "-O", "binary", "handoff.elf", "handoff.bin"])
    elf = output / "handoff.elf"
    blob = (output / "handoff.bin").read_bytes()
    if (
        blob[cfg["KERNEL_OFF"] :] != image
        or blob[cfg["DATA_OFF"] : cfg["DATA_OFF"] + len(board) + len(initrd)]
        != board + initrd
    ):
        raise ValueError("linked input bytes differ")
    if struct.unpack_from("<I", blob)[0] != 0x14080000 or len(blob) != cfg["FILE_END"]:
        raise ValueError("unexpected first branch or extent")
    header = struct.unpack_from("<II6Q4sI", blob)
    if header != (0x14080000, 0, 0x80000, len(blob), 10, 0, 0, 0, b"ARMd", 0):
        raise ValueError("unexpected outer arm64 Image header")
    relocations = subprocess.check_output(
        [TOOL + "readelf", "-r", elf], text=True, env={**os.environ, "LC_ALL": "C"}
    )
    if "There are no relocations in this file." not in relocations:
        raise ValueError("runtime relocations in the early handoff")
    result = {
        "kind": "Y2Q_HOST_ONLY_MAINLINE_HANDOFF",
        "image_sha256": digest(blob),
        "elf_sha256": digest(elf.read_bytes()),
        "layout": cfg,
        "leaves": {k: audit_leaf(elf, k) for k in ("y2q_shape", "y2q_interval")},
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["kind"], result["image_sha256"], result["leaves"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
