"""Package a y2q stage experiment and check both boot-only archives on the host."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import build
import return_stage

sys.path.insert(0, str(build.HERE.parent))
import prepare_uniloader_android as transport
from build_uniloader_android import resident, split_boot


def package(stage_build, output):
    stage_build = stage_build.resolve(strict=True)
    output = output.resolve()
    if not all(
        path.is_relative_to(build.PRIVATE) and path != build.PRIVATE
        for path in (stage_build, output)
    ):
        raise ValueError("private paths required")
    stage = json.loads((stage_build / "stage.json").read_text())
    if stage["kind"] != "HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS":
        raise ValueError("expected a stage build")
    handoff = stage_build / "handoff"
    note = json.loads((handoff / "result.json").read_text())
    if (
        note["kind"] != "Y2Q_HOST_ONLY_STAGE_HANDOFF"
        or note["image_sha256"] != stage["raw"]
    ):
        raise ValueError("stage and loader identities differ")
    raw = build.read_bound(handoff / "handoff.bin", stage["raw"])
    kernel = build.read_bound(handoff / "bound-Image", stage["image"])
    ramdisk = build.read_bound(
        handoff / "bound-initrd.gz",
        "46757f90128509a95836df46dbab0a1b66af21c10522e6497780f57c32280a46",
    )
    frame_bytes = return_stage.frames(stage["nonce"])
    if stage["stages"] != {
        k: build.digest(v) for k, v in frame_bytes.items()
    } or not raw.endswith(kernel):
        raise ValueError("stage frame or kernel identity differs")
    for frame in frame_bytes.values():
        if kernel.count(bytes(byte ^ 0xa5 for byte in frame)) != 1:
            raise ValueError("reader does not match the frames encoded in the kernel")

    original = build.read_bound(resident.BASE_BOOT, resident.BASE_BOOT_SHA256)
    original_header, _, _, dtb = split_boot(original)
    if (
        len(original) != resident.BASE_BOOT_SIZE
        or build.digest(dtb) != resident.BASE_DTB_SHA256
    ):
        raise ValueError("resident image size or stock DTB differs")
    resident.exact_receipt(
        resident.MAGISKBOOT,
        "magiskboot",
        size=resident.MAGISKBOOT_SIZE,
        sha256=resident.MAGISKBOOT_SHA256,
    )
    rollback = transport.retained.ROLLBACK_AP
    rollback_pin = resident.exact_receipt(
        rollback,
        "original Magisk AP",
        size=transport.retained.ROLLBACK_AP_SIZE,
        sha256=transport.retained.ROLLBACK_AP_SHA256,
    )
    output.mkdir(mode=0o700, exist_ok=False)
    boot = output / "boot.img"
    ap = output / "AP.tar.md5"
    with tempfile.TemporaryDirectory(dir=output) as temp:
        scratch = Path(temp)
        parts = scratch / "components"
        parts.mkdir()
        with (output / "container.log").open("xb") as log:

            def tool(*args):
                subprocess.run(
                    [resident.MAGISKBOOT, *args],
                    cwd=parts,
                    check=True,
                    stdout=log,
                    stderr=log,
                )

            tool("unpack", "-n", "-h", resident.BASE_BOOT)
            if {f.name for f in parts.iterdir()} != {
                "header",
                "kernel",
                "ramdisk.cpio",
                "dtb",
            }:
                raise ValueError("unexpected Android v2 components")
            (parts / "kernel").write_bytes(raw)
            (parts / "ramdisk.cpio").write_bytes(ramdisk)
            tool("repack", "-n", resident.BASE_BOOT, boot)
        new = boot.read_bytes()
        header, payload, initrd, tree = split_boot(new)
        mutable = set(range(8, 12)) | set(range(16, 20)) | set(range(576, 608))
        if (
            len(new) != len(original)
            or (payload, initrd, tree) != (raw, ramdisk, dtb)
            or any(
                a != b and i not in mutable
                for i, (a, b) in enumerate(zip(original_header, header))
            )
        ):
            raise ValueError("repacked Android components or header differ")
        if any(
            frame in blob for frame in frame_bytes.values() for blob in (new, original)
        ):
            raise ValueError("clear witness already present in a transport payload")
        boot.chmod(0o400)
        lz4 = scratch / "stage.lz4"
        transport.prep.lz4_roundtrip(boot, lz4, scratch / "roundtrip.img")
        written = transport.prep.write_boot_ap(lz4, ap)
        ap.chmod(0o400)
        audit = {}
        for key, path, pin, decoded in (
            ("candidate", ap, written, {"size": len(new), "sha256": build.digest(new)}),
            (
                "rollback",
                rollback,
                rollback_pin,
                {"size": len(original), "sha256": resident.BASE_BOOT_SHA256},
            ),
        ):
            work = scratch / key
            work.mkdir()
            audit[key] = transport.audit_ap(path, pin, decoded, work, key)
    receipt = dict(
        kind="HOST_ONLY_S20PLUS_Y2Q_STAGE_AP_PAIR",
        target="SM-G986N/y2q/G986NKSS8IYC2",
        raw=stage["raw"],
        nonce=stage["nonce"],
        clear_frames_absent_from_both_boots=True,
        return_template=build.digest(
            return_stage.shell(stage["nonce"], "0" * 64).encode()
        ),
        archives=audit,
        device_commands=0,
    )
    (output / "pair.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["kind"], audit["candidate"]["ap"]["sha256"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage_build", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    package(args.stage_build, args.output)
