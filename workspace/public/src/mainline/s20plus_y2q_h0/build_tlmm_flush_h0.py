"""Build and audit the host-only TLMM/first flush candidate using the retained y2q inputs."""
import argparse
import gzip
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import shutil
import struct

import build_deferred_worker as old
import tlmm_flush_h0 as reader

base = old.prior
EXP = base.loader.PRIVATE / "analysis/s20plus-y2q-tlmm-flush-h0-20261128"
OUT = EXP / "candidate"


def match_initrd_extent(meta):
    # Preserve even /chosen/linux,initrd-end with the new build-bound /init.
    # The initramfs format accepts zero padding after a compressed member.
    path = OUT/"initrd.gz"
    archive = gzip.decompress(path.read_bytes())
    member = gzip.compress(archive, compresslevel=9, mtime=0)
    size = (old.EXP/"candidate/initrd.gz").stat().st_size
    if len(member) > size:
        raise ValueError("compressed initramfs exceeds predecessor extent")
    data = member.ljust(size, bytes(1))
    if gzip.decompress(data) != archive:
        raise ValueError("padded initramfs differs")
    path.write_bytes(data)
    meta["initrd"] = base.sha(data)


def build_kernel():
    OUT.mkdir(parents=True, exist_ok=False)
    nonce = secrets.token_hex(16)
    meta = base.ram_inputs(OUT, nonce)
    match_initrd_extent(meta)
    archive = base.loader.BENCH / "linux-6.18.tar.xz"
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != base.previous.ARCHIVE:
            raise ValueError("release changed")
    base.run(["tar", "-xf", archive, "-C", OUT])
    src = OUT/"linux-6.18"
    base.instrument(src, nonce, meta)
    def apply(name):
        with (base.HERE/name).open("rb") as patch:
            base.run(["patch", "--batch", "--fuzz=0", "-p1"], cwd=src, stdin=patch)
    apply("deferred-probe-hooks.patch")
    shutil.copyfile(base.HERE/"deferred-witness.c", src/"init/y2q-progress.c")
    apply("tlmm-flush-hooks.patch")
    obj = OUT/"kernel-build"
    obj.mkdir()
    config = base.loader.read_bound(old.SOURCE, old.CONFIG)
    (obj/".config").write_bytes(config)
    env = dict(os.environ, KBUILD_BUILD_USER="lab", KBUILD_BUILD_HOST="y2q",
               KBUILD_BUILD_VERSION="1", KBUILD_BUILD_TIMESTAMP="2026-11-27 00:00:00 UTC")
    with (OUT/"build.log").open("xb") as log:
        for target in ("olddefconfig", "Image"):
            base.run(["make", "-s", "-C", src, f"O={obj}", "ARCH=arm64", "CROSS_COMPILE=aarch64-linux-gnu-",
                      "-j16", target], env=env, stdout=log, stderr=log.fileno())
    (OUT/"kernel-inputs.json").write_text(json.dumps(dict(meta, nonce=nonce), indent=2)+"\n")


def table(obj, image):
    rows = [line.split() for line in (obj/"System.map").read_text().splitlines()]
    syms = {name: int(addr, 16) for addr, _, name in rows}
    names = {int(addr, 16): name for addr, _, name in rows}
    slots = []
    for addr in range(syms["__initcall_start"], syms["__initcall_end"], 4):
        fn = addr + struct.unpack_from("<i", image, addr-syms["_text"])[0]
        slots.append(names[fn])
    return slots, syms


def package():
    def inputs(path):
        obj = path/"kernel-build"
        image = (obj/"arch/arm64/boot/Image").read_bytes()
        return image, *table(obj, image)
    image, order, syms = inputs(OUT)
    previous = old.EXP/"candidate"
    old_image, old_order, old_syms = inputs(previous)
    def boundaries(symbols):
        return {name: address-symbols["__initcall_start"] for name, address in symbols.items()
                if re.fullmatch(r"__initcall([0-7]_start|_end)", name)}
    if boundaries(syms) != boundaries(old_syms):
        raise ValueError("initcall level boundaries changed")
    if (order != old_order or base.sha(old_image) != "1219c5ab080ae32a1ec820777609b4eb53a1f5d822cc85ddfeda6fc2df61f73b"
            or base.sha((OUT/"kernel-build/.config").read_bytes()) != old.CONFIG
            or base.sha((OUT/"board.dtb").read_bytes()) != "541e220217f8bf0b65d4c18743a4ae6f8e7c35d6e5d9bc4497cda99655b433b8"):
        raise ValueError("candidate configuration, DT or initcall order differs")
    meta = json.loads((OUT/"kernel-inputs.json").read_bytes())
    nonce = meta["nonce"]
    offset = syms["y2q_nonce"] - syms["_text"]
    if image[offset:offset+16] != bytes.fromhex(nonce):
        raise ValueError("Image nonce mismatch")
    compose = OUT/"compose.c"
    compose.write_bytes(base.loader.read_bound(previous/"compose.c",
                        "1446b9f5f640d61fbeeddfc527d47e4088256b5d9cf024a9ca76f31c0a8e0b2a"))
    loader = base.loader
    call = "    cfg = layout(model, image, board, initrd)"
    trial = base.local_adapter(Path(loader.__file__), "589a304798313ad4826c6370c5745d70bedbfcfac76e498d83dc82cfc6b413c9", [
        ("(0, 0x480000, 10)", "(0, 0x490000, 10)"),
        (call, "    board, initrd = trial_board, trial_ramdisk\n" + call),
        ('*extra, "-c", unit,', '*extra, "-I", HERE, "-c", (trial_compose if unit == HERE / "compose.c" else unit),')
    ], dict(trial_board=(OUT/"board.dtb").read_bytes(), trial_ramdisk=(OUT/"initrd.gz").read_bytes(), trial_compose=compose))
    trial.build(OUT/"handoff", stage_image=image)
    meta.update(kind="HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS", profile="tlmm-flush-h0", image=base.sha(image),
                raw=base.sha((OUT/"handoff/handoff.bin").read_bytes()),
                stages={k:base.sha(v) for k,v in reader.frames(nonce).items()}, initcalls=order)
    (OUT/"stage.json").write_text(json.dumps(meta, indent=2)+"\n")
    # Bind to the new offline decoder; this package has no device return-reader scope.
    pkg = base.local_adapter(Path(base.packager.__file__), "672ea2268c813ef009ee0c2d1fc00260d494819b5084f5840be0e662c6066f7d", [
        ('"46757f90128509a95836df46dbab0a1b66af21c10522e6497780f57c32280a46"', 'stage["initrd"]'),
        ('kernel.count(bytes(byte ^ 0xa5 for byte in frame)) != 1',
         'kernel[key_offset:key_offset+16] != bytes.fromhex(stage["nonce"])'),
        ('return_template=build.digest(\n            return_stage.shell(stage["nonce"], "0" * 64).encode()\n        )',
         'offline_reader_sha256=reader_sha'),
    ], dict(key_offset=offset, reader_sha=base.sha(Path(reader.__file__).read_bytes())))
    pkg.return_stage = reader
    pkg.package(OUT, EXP/"packaged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("kernel", "package"))
    if parser.parse_args().step == "kernel":
        build_kernel()
    else:
        package()
