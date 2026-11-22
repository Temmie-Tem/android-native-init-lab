#!/usr/bin/env python3
"""Build a host-only y2q UniLoader with recoverable boot-stage witnesses."""

import argparse
import json
from pathlib import Path
import re
import shutil

import build_uniloader_android as control

HERE = Path(__file__).resolve().parent
PRIVATE = control.ROOT / "workspace/private"
STAGES = ("guard-passed", "fdt-marked", "handoff-ready")
PMSG_LIMIT = 1024
CONSOLE_LIMIT = 0x40000


def build(upstream, output):
    output = output.resolve()
    control.require(output.is_relative_to(PRIVATE.resolve()) and
                    output != PRIVATE.resolve(), "private output required")
    output.mkdir(mode=0o700)
    sources = output / "sources"
    sources.mkdir()
    for name in ("uniloader_entry.S", "uniloader_guard.c", "uniloader_prefix.lds",
                 "uniloader_layout.h", control.__name__ + ".py", Path(__file__).name):
        shutil.copyfile(HERE / name, sources / name)
    shutil.copyfile(HERE / "uniloader_stage_fdt.c", sources / "uniloader_fdt.c")

    # Use the unchanged control's build and exact image-member verification
    # against a private source snapshot, with just the FDT helper substituted.
    original_sources, control.HERE = control.HERE, sources
    try:
        control.build(upstream, output / "candidate")
    finally:
        control.HERE = original_sources
    result = {
        "status": "H0_Y2Q_UNILOADER_STAGE_BOOT_BUILT",
        "control_builder": control.resident.exact_receipt(
            sources / Path(control.__file__).name, "control builder"),
        "stage_builder": control.resident.exact_receipt(
            sources / Path(__file__).name, "stage builder"),
        "build": control.resident.exact_receipt(
            output / "candidate/result.json", "candidate build"),
        "device_commands": 0,
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def read_bounded(path, maximum):
    if path is None:
        return None
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("retained record exceeds its expected size")
    return data


def decode(tag, pmsg, console):
    """Decode only the matching build tag and the canonical stage order."""
    control.require(re.fullmatch(r"[0-9a-f]{64}", tag), "invalid build marker")
    label = tag.encode("ascii")
    stages = []
    if pmsg is not None:
        expected = [b"Y2Q-STAGE-V1 " + label + b" " + name.encode() + b"\n" for name in STAGES]
        for count in range(1, len(expected) + 1):
            if pmsg == b"".join(expected[:count]):
                stages = list(STAGES[:count])
                break

    vendor_printk = False
    if console is not None:
        line = (rb"(?:<\d+>)?(?:\[ *\d+\.\d+\] *)?"
                rb"(?:[ I]\[\d:[^\r\n:\]]{15}: *\d{1,5}\] )?"
                rb"Kernel command line: codex\.y2q_trace=" + label + rb"(?: |$)")
        vendor_printk = sum(bool(re.match(line, value)) for value in console.splitlines()) == 1
    return {
        "pmsg": "matched" if stages else "unavailable" if pmsg is None else "unmatched",
        "loader_stages": stages,
        "vendor_kernel_command_line": vendor_printk,
        "console": "matched" if vendor_printk else "unavailable" if console is None else "unmatched",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    builder = commands.add_parser("build")
    builder.add_argument("--upstream", required=True, type=Path)
    builder.add_argument("--output", required=True, type=Path)
    decoder = commands.add_parser("decode")
    decoder.add_argument("--build-receipt", required=True, type=Path)
    decoder.add_argument("--pmsg", type=Path)
    decoder.add_argument("--console", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        result = build(args.upstream, args.output)
    else:
        if args.pmsg is None and args.console is None:
            parser.error("provide an already collected pmsg or console file")
        receipt = json.loads(args.build_receipt.read_text())
        control.require(receipt["status"] == "H0_Y2Q_UNILOADER_ANDROID_BOOT_BUILT",
                        "unexpected candidate build receipt")
        tag = receipt["marker"]
        result = decode(tag, read_bounded(args.pmsg, PMSG_LIMIT),
                        read_bounded(args.console, CONSOLE_LIMIT))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
