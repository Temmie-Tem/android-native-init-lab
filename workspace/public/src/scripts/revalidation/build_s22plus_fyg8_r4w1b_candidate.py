#!/usr/bin/env python3
"""Build the host-only FYG8 R4W1-B direct-PID1 witness candidate."""

from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import s22plus_boot_slice as boot_slice


SCHEMA = "s22plus_fyg8_r4w1b_candidate_build_v1"
VERDICT = "PASS_R4W1B_CANDIDATE_BUILT_HOST_ONLY"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
RUNG = "R4W1-B"
BOOT_SIZE = 100_663_296
HEADER_START = 0
HEADER_END = 4_096
KERNEL_START = 4_096
KERNEL_END = 41_495_040
KERNEL_SIZE = KERNEL_END - KERNEL_START
GAP_START = KERNEL_END
GAP_END = 41_496_576
GAP_SIZE = GAP_END - GAP_START

M4T2_BOOT_SHA256 = "8103bce76fb3e41d71b64735a64d2f2f29431a44ea1c9a85dc0bc151d71afd15"
R4W1B_IMAGE_SHA256 = "350bc71815a7dbf22caf5d42434e4f99ace846329fd11e599b3be2d9c5e080d3"
REPRO_RESULT_SIZE = 314_695
REPRO_RESULT_SHA256 = "1b1124c828243772cb48cf8aa7f6667e88cd9ac5443164e2042243510d833eb1"
LZ4_SIZE = 218_696
LZ4_SHA256 = "91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8"
ODIN_SIZE = 3_746_744
ODIN_SHA256 = "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
MARKER_ID = "36dc5462adedcf136176f2ddcfee08a8"
MARKER = (
    b"\n[[S22R4W1B|id=36dc5462adedcf136176f2ddcfee08a8|"
    b"phase=DIRECT_INIT_EXEC_ACCEPTED|pid=1|path=/init]]\n"
)
MARKER_FAMILY = b"[[S22R4W1B|"

DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate/reproduction-a"
)
DEFAULT_CARRIER = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate_inputs/m4t2-carrier/boot.img"
)
DEFAULT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate_inputs/Image"
)
DEFAULT_REPRO_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1b_clean_repro_20260719/repro/result.json"
)
DEFAULT_LZ4 = Path(
    "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/"
    "prebuilts/kernel-build-tools/linux-x86/bin/lz4"
)
DEFAULT_ODIN = Path("/home/temmie/다운로드/odin4")


class BuildError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise BuildError("repository root not found")


def resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else (root / value).resolve()


def validate_patch_vbmeta_flag(environment: dict[str, str] | None = None) -> None:
    value = (os.environ if environment is None else environment).get("PATCHVBMETAFLAG")
    if value not in (None, "false"):
        raise BuildError("PATCHVBMETAFLAG must be absent or exactly 'false'")


def verify_reproduction_result(encoded: bytes) -> dict[str, Any]:
    try:
        data = json.loads(encoded.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError("invalid R4W1-B reproduction result JSON") from exc
    expected = {
        "schema": "s22plus_fyg8_r4w1b_repro_check_v1",
        "target": TARGET,
        "verdict": "PASS_R4W1B_CLEAN_REPRODUCIBILITY",
        "blockers": [],
        "reproducible": True,
        "image_byte_identical": True,
    }
    for key, value in expected.items():
        if data.get(key) != value:
            raise BuildError(f"R4W1-B reproduction result {key} mismatch")
    safety = data.get("safety", {})
    required_safety = {
        "host_only": True,
        "device_contact": False,
        "flash": False,
        "image_packaging": False,
        "live_authorized": False,
    }
    if any(safety.get(key) != value for key, value in required_safety.items()):
        raise BuildError("R4W1-B reproduction result safety mismatch")
    images = data.get("images")
    if not isinstance(images, list) or len(images) != 2:
        raise BuildError("R4W1-B reproduction result requires two Image records")
    for index, image in enumerate(images):
        required = {
            "size": KERNEL_SIZE,
            "sha256": R4W1B_IMAGE_SHA256,
            "marker_count": 1,
            "family_count": 1,
            "historical_family_count": 0,
            "verified": True,
        }
        if any(image.get(key) != value for key, value in required.items()):
            raise BuildError(f"R4W1-B reproduction Image {index} mismatch")
        if image.get("arm64_header", {}).get("verified") is not True:
            raise BuildError(f"R4W1-B reproduction Image {index} header not verified")
    return {
        "size": len(encoded),
        "sha256": boot_slice.sha256_bytes(encoded),
        "schema": data["schema"],
        "verdict": data["verdict"],
        "two_clean_images_verified": True,
    }


def validate_carrier_header(carrier: bytes) -> dict[str, Any]:
    if len(carrier) != BOOT_SIZE or carrier[:8] != b"ANDROID!":
        raise BuildError("M4T2 carrier is not the pinned-size Android boot image")
    kernel_size, ramdisk_size, _os_version, header_size = struct.unpack_from("<4I", carrier, 8)
    header_version = struct.unpack_from("<I", carrier, 40)[0]
    if header_version != 4 or header_size != 1584 or kernel_size != KERNEL_SIZE:
        raise BuildError("M4T2 carrier boot-v4 geometry mismatch")
    return {
        "header_version": header_version,
        "header_size": header_size,
        "kernel_size": kernel_size,
        "ramdisk_size": ramdisk_size,
    }


def build_candidate_bytes(carrier: bytes, image: bytes) -> tuple[bytes, dict[str, Any]]:
    carrier_header = validate_carrier_header(carrier)
    if len(image) != KERNEL_SIZE:
        raise BuildError(f"R4W1-B Image size mismatch: {len(image)} != {KERNEL_SIZE}")
    image_header = boot_slice.parse_arm64_header(image)
    marker = boot_slice.classify_marker_family(image, MARKER, MARKER_FAMILY)
    if not marker["valid_single_exact"]:
        raise BuildError(f"R4W1-B marker contract mismatch: {marker}")
    candidate = boot_slice.replace_fixed_interval(carrier, image, KERNEL_START, KERNEL_END)
    difference = boot_slice.diff_outside_interval(carrier, candidate, KERNEL_START, KERNEL_END)
    if candidate[:HEADER_END] != carrier[:HEADER_END]:
        raise BuildError("candidate changed the M4T2 Android header")
    if candidate[GAP_START:GAP_END] != carrier[GAP_START:GAP_END]:
        raise BuildError("candidate changed the explicit M4T2 alignment gap")
    if candidate[KERNEL_END:] != carrier[KERNEL_END:]:
        raise BuildError("candidate changed opaque M4T2 post-kernel bytes")
    if candidate[KERNEL_START:KERNEL_END] != image:
        raise BuildError("candidate kernel interval differs from qualified Image")
    if boot_slice.parse_arm64_header(candidate[KERNEL_START:KERNEL_END]) != image_header:
        raise BuildError("candidate kernel ARM64 header differs from qualified Image")
    return candidate, {
        "carrier_header": carrier_header,
        "image_header": image_header,
        "marker": marker,
        "difference": difference,
    }


def run(
    argv: list[str | Path], *, timeout: int = 120
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(part) for part in argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def require_ok(result: subprocess.CompletedProcess[bytes], label: str) -> None:
    if result.returncode != 0:
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise BuildError(f"{label} failed rc={result.returncode}: {output}")


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    output = resolve(root, args.out)
    if output.exists():
        raise BuildError(f"output path already exists: {output}")
    validate_patch_vbmeta_flag()
    carrier_pin, carrier = boot_slice.read_pinned_stable(
        resolve(root, args.carrier), BOOT_SIZE, M4T2_BOOT_SHA256, "M4T2 carrier"
    )
    image_pin, image = boot_slice.read_pinned_stable(
        resolve(root, args.image), KERNEL_SIZE, R4W1B_IMAGE_SHA256, "R4W1-B Image"
    )
    repro_pin, repro_bytes = boot_slice.read_pinned_stable(
        resolve(root, args.repro_result),
        REPRO_RESULT_SIZE,
        REPRO_RESULT_SHA256,
        "R4W1-B reproduction result",
    )
    repro = verify_reproduction_result(repro_bytes)
    lz4_pin, lz4_bytes = boot_slice.read_pinned_stable(
        resolve(root, args.lz4), LZ4_SIZE, LZ4_SHA256, "lz4"
    )
    odin_pin, odin_bytes = boot_slice.read_pinned_stable(
        resolve(root, args.odin), ODIN_SIZE, ODIN_SHA256, "odin4"
    )
    candidate, construction = build_candidate_bytes(carrier, image)
    candidate_sha256 = boot_slice.sha256_bytes(candidate)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output.name}.", dir=output.parent) as temporary:
        staging = Path(temporary)
        tools = staging / ".pinned-tools"
        tools.mkdir()
        pinned_lz4 = tools / "lz4"
        pinned_odin = tools / "odin4"
        pinned_lz4.write_bytes(lz4_bytes)
        pinned_odin.write_bytes(odin_bytes)
        pinned_lz4.chmod(0o700)
        pinned_odin.chmod(0o700)
        boot_slice.read_pinned_stable(pinned_lz4, LZ4_SIZE, LZ4_SHA256, "staged lz4")
        boot_slice.read_pinned_stable(pinned_odin, ODIN_SIZE, ODIN_SHA256, "staged odin4")

        boot_path = staging / "boot.img"
        with boot_path.open("xb") as handle:
            handle.write(candidate)
        if boot_path.read_bytes() != candidate:
            raise BuildError("staged candidate bytes changed after write")
        frame_path = staging / "boot.img.lz4"
        require_ok(
            run([pinned_lz4, "--content-size", "-B6", "-f", "-q", boot_path, frame_path]),
            "LZ4 compression",
        )
        roundtrip = staging / ".roundtrip.img"
        require_ok(run([pinned_lz4, "-d", "-f", "-q", frame_path, roundtrip]), "LZ4 roundtrip")
        if roundtrip.read_bytes() != candidate:
            raise BuildError("LZ4 roundtrip differs from candidate")
        roundtrip.unlink()

        odin_dir = staging / "odin4"
        odin_dir.mkdir()
        ap_path = odin_dir / "AP.tar.md5"
        frame = frame_path.read_bytes()
        ap_structure = boot_slice.write_deterministic_boot_ap(frame, ap_path)
        odin_gate = boot_slice.run_odin_invalid_device_gate(pinned_odin, ap_path)
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(
            json.dumps(odin_gate, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )

        outputs = {
            "boot_img": {"size": len(candidate), "sha256": candidate_sha256},
            "boot_img_lz4": {
                "size": frame_path.stat().st_size,
                "sha256": boot_slice.sha256_path(frame_path),
            },
            "ap_tar_md5": {
                "size": ap_path.stat().st_size,
                "sha256": boot_slice.sha256_path(ap_path),
            },
        }
        manifest = {
            "schema": SCHEMA,
            "target": TARGET,
            "rung": RUNG,
            "inputs": {
                "m4t2_carrier": carrier_pin,
                "r4w1b_image": image_pin,
                "r4w1b_reproduction_result": {**repro_pin, **repro},
                "lz4": lz4_pin,
                "odin4": odin_pin,
            },
            "geometry": {
                "carrier_size": BOOT_SIZE,
                "android_header": [HEADER_START, HEADER_END],
                "kernel_interval": [KERNEL_START, KERNEL_END],
                "kernel_size": KERNEL_SIZE,
                "alignment_gap": [GAP_START, GAP_END],
                "alignment_gap_size": GAP_SIZE,
                "preserved_tail": [KERNEL_END, BOOT_SIZE],
            },
            "construction": {
                "method": "fixed-interval replacement",
                "patch_vbmeta_flag": False,
                "carrier_header_preserved": candidate[:HEADER_END] == carrier[:HEADER_END],
                "kernel_equals_qualified_image": candidate[KERNEL_START:KERNEL_END] == image,
                "alignment_gap_preserved": candidate[GAP_START:GAP_END]
                == carrier[GAP_START:GAP_END],
                "opaque_post_kernel_bytes_preserved": candidate[KERNEL_END:]
                == carrier[KERNEL_END:],
                **construction,
            },
            "outputs": {**outputs, "ap_structure": ap_structure},
            "odin_invalid_device_gate": odin_gate,
            "safety": {
                "host_only": True,
                "boot_only_ap": True,
                "ap_members": ["boot.img.lz4"],
                "device_contact": False,
                "device_write": False,
                "usb_enumeration": False,
                "odin_transfer": False,
                "flash": False,
                "live_authorized": False,
                "stale_carrier_avb_preserved": True,
            },
            "blockers": [],
            "verdict": VERDICT,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )
        pinned_lz4.unlink()
        pinned_odin.unlink()
        tools.rmdir()
        os.replace(staging, output)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--carrier", type=Path, default=DEFAULT_CARRIER)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--repro-result", type=Path, default=DEFAULT_REPRO_RESULT)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        manifest = build(parse_args(argv))
    except (BuildError, boot_slice.BootSliceError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": manifest["verdict"],
                "boot_sha256": manifest["outputs"]["boot_img"]["sha256"],
                "ap_sha256": manifest["outputs"]["ap_tar_md5"]["sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
