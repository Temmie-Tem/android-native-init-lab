"""Build and package the single y2q Linux 6.18 device-tree and basic-setup diagnostic."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

import build_cstage_serial
import basic_setup_stage_reader as reader

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "mainline-handoff"))
import build as loader
import build_stage as previous
import package_stage

PROFILE = "s20plus-g986n-basic-setup-f1"
INIT_DIGEST = "f9b07dbca775cc81eba24a30fcfa31c05fee35efbe92da3a541bc7a03d324f61"


def substitute(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Linux source site differs")
    return text.replace(old, new)


def instrument(source, nonce):
    build_cstage_serial.select_serial(source)
    init = source / "init"
    setup = source / "arch/arm64/kernel/setup.c"
    code = loader.read_bound(setup, "d0572642224a071b14de5fdd61243d2086016faf3c29765817fd459b503110d6").decode()
    before = "\tif (acpi_disabled)\n\t\tunflatten_device_tree();"
    after = ("\tif (acpi_disabled) {\n\t\tunflatten_device_tree();\n"
             "\t\ty2q_dt_ready();\n\t}")
    setup.write_text('#include <linux/y2q-basic-stage.h>\n' + substitute(code, before, after))
    kernel_init = init / "main.c"
    code = loader.read_bound(kernel_init, "64a6b91514fb324ce41e874d7cc8312de9489c6df763873a09168bb222efa91d").decode()
    before = "\tdo_basic_setup();"
    after = "\ty2q_basic_enter();\n" + before + "\n\ty2q_basic_return();"
    kernel_init.write_text('#include <linux/y2q-basic-stage.h>\n' + substitute(code, before, after))
    prototypes = [f"void y2q_{name}(void);" for name in reader.STAGES]
    (source / "include/linux/y2q-basic-stage.h").write_text("\n".join(prototypes) + "\n")
    shutil.copyfile(HERE / "basic-setup-stage-witness.c", init / "y2q-basic-stage.c")
    frames = reader.frames(nonce)
    arrays = ["{" + ",".join(f"0x{b ^ 0xa5:02x}" for b in frame) + "}" for frame in frames.values()]
    (init / "y2q-basic-frames.h").write_text(
        "static const u8 y2q_frames[3][80] __initconst = {\n" + ",\n".join(arrays) + "\n};\n")
    with (init / "Makefile").open("a") as stream:
        stream.write("\nobj-y += y2q-basic-stage.o\n")
    return frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    exp = parser.parse_args().experiment
    if exp.resolve(strict=True) != exp or not exp.is_relative_to(loader.PRIVATE) or exp == loader.PRIVATE:
        raise ValueError("direct private experiment directory required")
    out = exp / "candidate"
    out.mkdir(mode=0o700)
    archive = loader.BENCH / "linux-6.18.tar.xz"
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != previous.ARCHIVE:
            raise ValueError("Linux source archive differs")
    loader.read_bound(loader.BENCH / "ramfs/init", INIT_DIGEST)
    subprocess.run(["tar","-xf",archive,"-C",out], check=True)
    source = out / "linux-6.18"
    objects = out / "kernel-build"
    objects.mkdir()
    config = loader.read_bound(loader.BENCH / "kernel-build/.config", previous.CONFIG)
    (objects / ".config").write_bytes(config)
    nonce = secrets.token_hex(16)
    (out / "nonce").write_text(nonce+"\n")
    frames = instrument(source,nonce)
    env = dict(os.environ, KBUILD_BUILD_USER="lab", KBUILD_BUILD_HOST="y2q",
               KBUILD_BUILD_TIMESTAMP="2026-11-23 00:00:00 UTC", KBUILD_BUILD_VERSION="1")
    with (out/"kernel-build.log").open("xb") as log:
        for target in ("olddefconfig","Image"):
            subprocess.run(["make","-C",source,f"O={objects}","ARCH=arm64","CROSS_COMPILE=aarch64-linux-gnu-",
                            "-j16",target],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    if (objects/".config").read_bytes()!=config:
        raise ValueError("Linux configuration differs")
    image = (objects/"arch/arm64/boot/Image").read_bytes()
    for frame in frames.values():
        if frame in image or image.count(bytes(b^0xa5 for b in frame)) != 1:
            raise ValueError("marker representation differs")
    loader.build(out/"handoff",stage_image=image)
    meta=dict(kind="HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS",profile=PROFILE,nonce=nonce,
              config=previous.CONFIG,release=previous.ARCHIVE,image=loader.digest(image),
              system_map=loader.digest((objects/"System.map").read_bytes()),
              raw=loader.digest((out/"handoff/handoff.bin").read_bytes()),
              stages={k:loader.digest(v) for k,v in frames.items()},init_elf=INIT_DIGEST)
    (out/"stage.json").write_text(json.dumps(meta,indent=2)+"\n")
    package_stage.return_stage=reader
    package_stage.package(out,exp/"packaged")
    receipt=exp/"packaged/pair.json"
    pair=json.loads(receipt.read_bytes())
    pair["profile"]=PROFILE
    receipt.write_text(json.dumps(pair,indent=2)+"\n")


if __name__ == "__main__":
    main()
