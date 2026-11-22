"""Build the y2q Linux stage witness in a new private host directory."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess

import build as loader
from return_stage import frames

CONFIG = "77079802e6165cd86cfbabad3fbf2fc001258b675d797392cdf18e36d3d5eb89"
ARCHIVE = "9106a4605da9e31ff17659d958782b815f9591ab308d03b0ee21aad6c7dced4b"


def build_stage(output):
    output = output.resolve()
    if not output.is_relative_to(loader.PRIVATE) or output == loader.PRIVATE:
        raise ValueError("private output required")
    output.mkdir(mode=0o700, exist_ok=False)
    artifact = loader.BENCH / "linux-6.18.tar.xz"
    with artifact.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != ARCHIVE:
            raise ValueError("release archive changed")
    subprocess.run(["tar", "-xf", artifact, "-C", output], check=True)
    source = output / "linux-6.18"
    objects = output / "kernel-build"
    objects.mkdir()
    config = loader.read_bound(loader.BENCH / "kernel-build/.config", CONFIG)
    (objects / ".config").write_bytes(config)
    nonce = secrets.token_hex(16)
    stage_frames = frames(nonce)
    kernel = source / "arch/arm64/kernel"
    setup = kernel / "setup.c"
    code = loader.read_bound(
        setup, "d0572642224a071b14de5fdd61243d2086016faf3c29765817fd459b503110d6"
    ).decode()
    substitutions = [
        (
            "void __init __no_sanitize_address setup_arch(",
            '#include "y2q-stage-kernel.h"\n\nvoid __init __no_sanitize_address setup_arch(',
        ),
        (
            "\tsetup_machine_fdt(__fdt_pointer);",
            "\tsetup_machine_fdt(__fdt_pointer);\n\ty2q_record_stage(0);",
        ),
        (
            "\tif (acpi_disabled)\n\t\tunflatten_device_tree();",
            '\tif (acpi_disabled) {\n\t\tunflatten_device_tree();\n\t\tif (of_machine_is_compatible("samsung,y2q"))\n\t\t\ty2q_record_stage(1);\n\t}',
        ),
    ]
    for old, new in substitutions:
        if code.count(old) != 1:
            raise ValueError("unexpected Linux call site")
        code = code.replace(old, new)
    setup.write_text(code)
    shutil.copyfile(loader.HERE / "stage-kernel.h", kernel / "y2q-stage-kernel.h")
    arrays = []
    for frame in stage_frames.values():
        if len(frame) != 128:
            raise ValueError("unexpected stage frame length")
        arrays.append("{" + ",".join(f"0x{byte ^ 0xA5:02x}" for byte in frame) + "}")
    (kernel / "y2q-stage-frames.h").write_text(
        "static const u8 y2q_frames[2][128] __initconst = {\n"
        + ",\n".join(arrays)
        + "\n};\n"
    )
    (output / "nonce").write_text(nonce + "\n")
    command = [
        "make",
        "-C",
        str(source),
        f"O={objects}",
        "ARCH=arm64",
        "CROSS_COMPILE=aarch64-linux-gnu-",
    ]
    env = dict(
        os.environ,
        KBUILD_BUILD_TIMESTAMP="2026-11-23 00:00:00 UTC",
        KBUILD_BUILD_USER="lab",
        KBUILD_BUILD_HOST="y2q",
        KBUILD_BUILD_VERSION="1",
    )
    with (output / "kernel-build.log").open("xb") as log:
        for goal in ("olddefconfig", "Image"):
            subprocess.run(
                [*command, "-j16", goal], stdout=log, stderr=log, check=True, env=env
            )
    if (objects / ".config").read_bytes() != config:
        raise ValueError("kernel configuration differs")
    image = (objects / "arch/arm64/boot/Image").read_bytes()
    for frame in stage_frames.values():
        if frame in image or bytes(b ^ 0xA5 for b in frame) not in image:
            raise ValueError("unexpected frame representation in Linux Image")
    handoff = output / "handoff"
    loader.build(handoff, stage_image=image)
    raw = (handoff / "handoff.bin").read_bytes()
    if any(frame in raw for frame in stage_frames.values()):
        raise ValueError("complete witness present in transport")
    meta = dict(
        kind="HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS",
        nonce=nonce,
        config=CONFIG,
        release=ARCHIVE,
        setup=loader.digest(setup.read_bytes()),
        image=loader.digest(image),
        system_map=loader.digest((objects / "System.map").read_bytes()),
        raw=loader.digest(raw),
        stages={s: loader.digest(f) for s, f in stage_frames.items()},
    )
    (output / "stage.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(meta["kind"], meta["raw"])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    build_stage(p.parse_args().output)
