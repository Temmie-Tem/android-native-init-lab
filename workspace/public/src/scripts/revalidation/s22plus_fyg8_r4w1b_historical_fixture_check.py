#!/usr/bin/env python3
"""Qualify new builder mechanics against frozen R4W1-A private artifacts."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import s22plus_boot_slice as boot_slice


SCHEMA = "s22plus_fyg8_r4w1b_historical_fixture_check_v1"
VERDICT = "PASS_R4W1B_BUILD_PRIMITIVES_R4W1A_FIXTURE"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
BOOT_SIZE = 100_663_296
KERNEL_START = 4_096
KERNEL_END = 41_495_040
KERNEL_SIZE = KERNEL_END - KERNEL_START

R3C0_BOOT_SHA256 = "384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f"
R4W1_IMAGE_SHA256 = "9552653de86dbdc2f1abd919b4d7b0d3f365fc878a56ed5ae09c82d0d81d844c"
R4W1A_BOOT_SHA256 = "a2bba0ef907af14e57508ca55d247d571c3f89936dd7020293e51ebfa8f8d133"
R4W1A_LZ4_SIZE = 27_716_775
R4W1A_LZ4_SHA256 = "0bf83af2bb7167aae4a57be1686599aa99fe9e75ccd7aa89128da799a4c14a99"
R4W1A_AP_SIZE = 27_719_721
R4W1A_AP_SHA256 = "cb2c078f001af6e263dc3f533a2efe3294a5c80201f50952a45bb88254e4d895"
R4W1_MARKER = (
    b"\n[[S22R4W1|id=9ed5923b08c5eedbbdb0aaa6f6a5200c|"
    b"phase=RAMDISK_EXEC_ACCEPTED|pid=1|path=/init]]\n"
)

DEFAULT_R3C0_BOOT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate_inputs/r3c0-carrier.img"
)
DEFAULT_R4W1_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1/remote-g-artifacts-final/Image"
)
DEFAULT_R4W1A_BOOT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1a_candidate/reproduction-a/boot.img"
)
DEFAULT_R4W1A_LZ4 = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1a_candidate/reproduction-a/odin4/boot.img.lz4"
)
DEFAULT_R4W1A_AP = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1a_candidate/reproduction-a/odin4/AP.tar.md5"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate/historical-fixture-result.json"
)


class FixtureError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise FixtureError("repository root not found")


def resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else (root / value).resolve()


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    carrier_pin, carrier = boot_slice.read_pinned_stable(
        resolve(root, args.r3c0_boot), BOOT_SIZE, R3C0_BOOT_SHA256, "R3C0 carrier"
    )
    image_pin, image = boot_slice.read_pinned_stable(
        resolve(root, args.r4w1_image), KERNEL_SIZE, R4W1_IMAGE_SHA256, "R4W1 Image"
    )
    historical_pin, historical = boot_slice.read_pinned_stable(
        resolve(root, args.r4w1a_boot), BOOT_SIZE, R4W1A_BOOT_SHA256, "R4W1-A boot"
    )
    frame_pin, frame = boot_slice.read_pinned_stable(
        resolve(root, args.r4w1a_lz4), R4W1A_LZ4_SIZE, R4W1A_LZ4_SHA256, "R4W1-A LZ4"
    )
    ap_pin, ap = boot_slice.read_pinned_stable(
        resolve(root, args.r4w1a_ap), R4W1A_AP_SIZE, R4W1A_AP_SHA256, "R4W1-A AP"
    )
    reconstructed = boot_slice.replace_fixed_interval(
        carrier, image, KERNEL_START, KERNEL_END
    )
    if reconstructed != historical:
        raise FixtureError(
            f"new fixed-slice primitive did not reproduce R4W1-A: "
            f"{boot_slice.sha256_bytes(reconstructed)}"
        )
    difference = boot_slice.diff_outside_interval(
        carrier, reconstructed, KERNEL_START, KERNEL_END
    )
    marker = boot_slice.classify_marker_family(
        image, R4W1_MARKER, b"[[S22R4W1|"
    )
    if not marker["valid_single_exact"]:
        raise FixtureError(f"R4W1 fixture marker classification failed: {marker}")
    with tempfile.TemporaryDirectory(prefix="s22plus-r4w1a-fixture-") as temporary:
        generated_path = Path(temporary) / "AP.tar.md5"
        structure = boot_slice.write_deterministic_boot_ap(frame, generated_path)
        generated = generated_path.read_bytes()
    if generated != ap:
        raise FixtureError(
            f"new AP primitive did not reproduce R4W1-A: {boot_slice.sha256_bytes(generated)}"
        )
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "inputs": {
            "carrier": carrier_pin,
            "image": image_pin,
            "historical_boot": historical_pin,
            "historical_lz4": frame_pin,
            "historical_ap": ap_pin,
        },
        "checks": {
            "fixed_slice_exact_historical_boot": True,
            "outside_interval_equal": True,
            "difference": difference,
            "marker": marker,
            "deterministic_ap_exact_historical_ap": True,
            "ap_structure": structure,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "flash": False,
            "live_authorized": False,
        },
        "blockers": [],
        "verdict": VERDICT,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r3c0-boot", type=Path, default=DEFAULT_R3C0_BOOT)
    parser.add_argument("--r4w1-image", type=Path, default=DEFAULT_R4W1_IMAGE)
    parser.add_argument("--r4w1a-boot", type=Path, default=DEFAULT_R4W1A_BOOT)
    parser.add_argument("--r4w1a-lz4", type=Path, default=DEFAULT_R4W1A_LZ4)
    parser.add_argument("--r4w1a-ap", type=Path, default=DEFAULT_R4W1A_AP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = audit(args)
        root = repo_root()
        output = resolve(root, args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, encoded.encode("ascii"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except (FixtureError, boot_slice.BootSliceError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": VERDICT}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
