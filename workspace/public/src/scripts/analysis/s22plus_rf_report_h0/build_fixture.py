"""Build a Linux-user Hexagon fixture around the unmodified FYG1 file reader."""
import argparse
import hashlib
from pathlib import Path
import subprocess

START = 0xD8B401A8
END = 0xD8B40730
IMAGE_BASE = 0xD8000000
DIGEST = "3874ddbc26973b86841b275cf2c3e95089b412de642edc52c9c9f4f86d0ed155"
# Filesystem/diag runtime imports supplied by efs_fixture.c. Every other target
# stays unmapped or traps. The guest cannot service another operation or file.
IMPORTS = {
    0xD8928464: "length", 0xD89A2B08: "compare", 0xD8AB3404: "denied",
    0xD8AD629C: "shorten", 0xD8B2ABB8: "error", 0xD8B2ACA8: "copy",
    0xD8B2AF9C: "access", 0xD8B2D37C: "open", 0xD8B2D5D0: "read",
    0xD8B2D8F0: "close", 0xD8B2DDA0: "stat", 0xD8B3FCE0: "allocate",
    0xD8B3FCE8: "error_code",
}


def build(source, out, llvm):
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name in ("highA", "highB"):
        with (source / name).open("rb") as stream:
            stream.seek(START - IMAGE_BASE)
            code = stream.read(END - START)
        if hashlib.sha256(code).hexdigest() != DIGEST:
            raise ValueError(f"{name}: incorrect FYG1 reader bytes")
    (out / "reader.bin").write_bytes(code)
    assembly = []
    sections = []
    for address, name in IMPORTS.items():
        assembly.extend([f'.section .leaf_{name},"ax",@progbits', f"jump ##fixture_{name}"])
        sections.append(f".leaf_{name} {address:#x} : {{ *(.leaf_{name}) }} :leaves")
    assembly.extend(['.section .reader,"ax",@progbits', '.global stock_reader',
                     'stock_reader:', '.incbin "reader.bin"'])
    (out / "imports.s").write_text("\n".join(assembly) + "\n")
    (out / "guest.ld").write_text("""
ENTRY(_start)
PHDRS { code PT_LOAD FLAGS(5); data PT_LOAD FLAGS(6); fd PT_LOAD FLAGS(6);
        state PT_LOAD FLAGS(6); leaves PT_LOAD FLAGS(5); }
SECTIONS {
  . = 0x100000; .text : { *(.text*) *(.rodata*) } :code
  . = ALIGN(0x10000); .data : { *(.data*) *(.bss*) *(COMMON) } :data
  .fd 0xc0cf6aa0 (NOLOAD) : { stock_fd = .; . += 4; } :fd
  .state 0xc53cd000 (NOLOAD) : { . += 0x9000; } :state
""" + "\n".join(sections) + f"\n.reader {START:#x} : {{ *(.reader) }} :leaves\n"
                                      "/DISCARD/ : { *(.comment*) *(.note*) }\n}\n")
    subprocess.run([llvm / "clang", "-target", "hexagon", "-mcpu=hexagonv68", "-G0", "-O1",
                    "-ffreestanding", "-fno-builtin", "-fno-stack-protector", "-Wall", "-Werror",
                    "-c", Path(__file__).with_name("efs_fixture.c").resolve(), "-o", "fixture.o"],
                   cwd=out, check=True)
    subprocess.run([llvm / "llvm-mc", "-triple=hexagon", "-mcpu=hexagonv68", "-filetype=obj",
                    "imports.s", "-o", "imports.o"], cwd=out, check=True)
    subprocess.run([llvm / "ld.lld", "-T", "guest.ld", "fixture.o", "imports.o",
                    "-o", "efs-fixture"], cwd=out, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code_copies", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("llvm_bin", type=Path)
    args = parser.parse_args()
    build(args.code_copies, args.output, args.llvm_bin.resolve())
