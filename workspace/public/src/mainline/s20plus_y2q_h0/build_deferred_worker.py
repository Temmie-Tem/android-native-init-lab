"""Build a fresh RAM-only y2q deferred-probe candidate; host operations only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import struct
import subprocess

import build_consolidated as prior

HERE = prior.HERE
PROFILE = "s20plus-g986n-deferred-worker-f1"
CONFIG = "b5da4669b6ceaeea03a1ab4b446645e4666e01a2d0bf923bb33286a25d5712db"
SOURCE = prior.loader.PRIVATE / "analysis/s20plus-y2q-deferred-static-20261127/kconfig-pc/.config"
EXP = prior.loader.PRIVATE / "analysis/s20plus-y2q-deferred-worker-f1"


def build_kernel():
    out = EXP / "candidate"
    out.mkdir(mode=0o700)
    nonce = secrets.token_hex(16)
    meta = prior.ram_inputs(out, nonce)
    archive = prior.loader.BENCH / "linux-6.18.tar.xz"
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != prior.previous.ARCHIVE:
            raise ValueError("Linux release digest differs")
    prior.run(["tar", "-xf", archive, "-C", out])
    src = out / "linux-6.18"
    prior.instrument(src, nonce, meta)
    with (HERE / "deferred-probe-hooks.patch").open("rb") as changes:
        prior.run(["patch", "-p1", "--batch", "--fuzz=0"], cwd=src, stdin=changes)
    shutil.copyfile(HERE / "deferred-witness.c", src / "init/y2q-progress.c")
    objects = out / "kernel-build"
    objects.mkdir()
    config = prior.loader.read_bound(SOURCE, CONFIG)
    (objects / ".config").write_bytes(config)
    env = dict(os.environ, KBUILD_BUILD_USER="lab", KBUILD_BUILD_HOST="y2q",
               KBUILD_BUILD_VERSION="1", KBUILD_BUILD_TIMESTAMP="2026-11-27 00:00:00 UTC")
    with (out / "kernel-build.log").open("xb") as log:
        for target in ("olddefconfig", "Image"):
            prior.run(["make", "-s", "-C", src, f"O={objects}", "ARCH=arm64",
                       "CROSS_COMPILE=aarch64-linux-gnu-", "-j16", target],
                      env=env, stdout=log, stderr=subprocess.STDOUT)
    if (objects / ".config").read_bytes() != config:
        raise ValueError("unexpected kernel configuration change")
    meta.update(nonce=nonce, config=CONFIG, release=prior.previous.ARCHIVE)
    (out / "kernel-inputs.json").write_text(json.dumps(meta, indent=2) + "\n")


def package():
    import deferred_reader as reader
    out = EXP / "candidate"
    meta = json.loads((out / "kernel-inputs.json").read_bytes())
    nonce = meta["nonce"]
    image = (out / "kernel-build/arch/arm64/boot/Image").read_bytes()
    symbols = {row[2]: int(row[0], 16) for line in (out / "kernel-build/System.map").read_text().splitlines()
               if len(row := line.split()) == 3}
    extent = symbols["_end"] - symbols["_text"]
    if extent != 0x490000 or extent != struct.unpack_from("<Q", image, 16)[0]:
        raise ValueError("unexpected arm64 runtime extent")
    start = symbols["__initcall0_start"]
    probe = start + 152 * 4
    if (symbols["__initcall_end"] - start != 159 * 4 or
            probe + struct.unpack_from("<i", image, probe - symbols["_text"])[0] != symbols["deferred_probe_initcall"]):
        raise ValueError("regular initcall table or deferred dispatch changed")
    loader = prior.loader
    firmware = loader.HERE / "compose.c"
    compose = out / "compose.c"
    compose.write_text(prior.sub(firmware.read_text(), '"rdinit=/init"', '"rdinit=/init cpuidle.off=1"'))
    call = "    cfg = layout(model, image, board, initrd)"
    trial = prior.local_adapter(Path(loader.__file__), "589a304798313ad4826c6370c5745d70bedbfcfac76e498d83dc82cfc6b413c9", [
        ("(0, 0x480000, 10)", "(0, 0x490000, 10)"),
        (call, "    board, initrd = trial_board, trial_ramdisk\n" + call),
        ('*extra, "-c", unit,', '*extra, "-I", HERE, "-c", (trial_compose if unit == HERE / "compose.c" else unit),')
    ], dict(trial_board=(out/"board.dtb").read_bytes(), trial_ramdisk=(out/"initrd.gz").read_bytes(), trial_compose=compose))
    trial.build(out / "handoff", stage_image=image)
    meta.update(kind="HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS", profile=PROFILE, image=prior.sha(image),
                raw=prior.sha((out/"handoff/handoff.bin").read_bytes()),
                stages={k:prior.sha(v) for k,v in reader.frames(nonce).items()})
    (out/"stage.json").write_text(json.dumps(meta, indent=2)+"\n")
    key_offset = symbols["y2q_nonce"] - symbols["_text"]
    pkg = prior.local_adapter(Path(prior.packager.__file__), "672ea2268c813ef009ee0c2d1fc00260d494819b5084f5840be0e662c6066f7d", [
        ('"46757f90128509a95836df46dbab0a1b66af21c10522e6497780f57c32280a46"', 'stage["initrd"]'),
        ('kernel.count(bytes(byte ^ 0xa5 for byte in frame)) != 1', 'kernel[key_offset:key_offset+16] != bytes.fromhex(stage["nonce"]) or any(tag + bytes.fromhex(stage["nonce"]) in blob for tag in (b"H0EPOCH3", b"H0UNATR3") for blob in (raw, ramdisk))')
    ], dict(key_offset=key_offset))
    pkg.return_stage = reader
    pkg.package(out, EXP/"packaged")
    f = EXP/"packaged/pair.json"
    pair = json.loads(f.read_bytes())
    pair["profile"] = PROFILE
    f.write_text(json.dumps(pair, indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("kernel", "package"))
    step = parser.parse_args().step
    if step == "kernel":
        build_kernel()
    else:
        package()
