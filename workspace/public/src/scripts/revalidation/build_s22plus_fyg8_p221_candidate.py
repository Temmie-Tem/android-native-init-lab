#!/usr/bin/env python3
"""Construct the P2.21 boot-only AP without creating live authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_boot_slice as boot_slice  # noqa: E402
import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p219_same_ring_contract as p219  # noqa: E402
import s22plus_fyg8_p221_build_artifact_contract as artifact  # noqa: E402
import s22plus_fyg8_r4w1e_e1_candidate_static_checker as legacy  # noqa: E402


SCHEMA = "s22plus_fyg8_p221_candidate_artifact_result_v1"
VERDICT = "PASS_P221_CANDIDATE_ARTIFACTS_BUILT_HOST_ONLY"
BOOT_SIZE = legacy.BOOT_SIZE
KERNEL_START = legacy.KERNEL_START
KERNEL_END = legacy.KERNEL_END
E0_CARRIER_SIZE = BOOT_SIZE
E0_CARRIER_SHA256 = "6b8b7f07cdb0fd5802171df44378e098364555c09311c527ef26cf34fa41edaa"
DEFAULT_IMAGE = Path("workspace/private/outputs/s22plus_fyg8_p221_build/artifacts/Image")
DEFAULT_VMLINUX = Path(
    "workspace/private/outputs/s22plus_fyg8_p221_build/artifacts/vmlinux"
)
DEFAULT_CONFIG = Path("workspace/private/outputs/s22plus_fyg8_p221_build/artifacts/.config")
DEFAULT_BUILD_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p221_build/artifacts/build-result.json"
)
DEFAULT_CARRIER = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e0_candidate/reproduction-a/boot.img"
)
DEFAULT_LZ4 = legacy.DEFAULT_LZ4
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p221_candidate/artifacts")


class BuildError(ValueError):
    """A P2.21 offline construction invariant failed."""


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "GOAL.md").is_file():
            return parent
    raise BuildError("repository root not found")


def resolve(root: Path, value: Path) -> Path:
    if value.is_absolute():
        return value
    if ".." in value.parts:
        raise BuildError(f"relative path escapes repository root: {value}")
    return root / value


def _receipt(data: bytes) -> dict[str, Any]:
    return {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def replace_kernel(carrier: bytes, image: bytes) -> tuple[bytes, dict[str, Any]]:
    if len(carrier) != BOOT_SIZE or len(image) != KERNEL_END - KERNEL_START:
        raise BuildError("P2.21 fixed boot layout size mismatch")
    candidate = boot_slice.replace_fixed_interval(
        carrier, image, KERNEL_START, KERNEL_END
    )
    changes = boot_slice.diff_outside_interval(
        carrier, candidate, KERNEL_START, KERNEL_END
    )
    carrier_boot = boot_verify.parse_boot_v4(carrier)
    candidate_boot = boot_verify.parse_boot_v4(candidate)
    if carrier_boot.header != candidate_boot.header:
        raise BuildError("P2.21 kernel replacement changed the boot header")
    if carrier_boot.ramdisk != candidate_boot.ramdisk:
        raise BuildError("P2.21 kernel replacement changed the ramdisk")
    if candidate_boot.kernel != image:
        raise BuildError("P2.21 boot parser did not recover the exact Image")
    return candidate, {**changes, "header_preserved": True, "ramdisk_preserved": True}


def _run(command: list[Path | str], label: str) -> None:
    completed = subprocess.run(
        [str(value) for value in command],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", "replace")[-1000:]
        raise BuildError(f"{label} failed ({completed.returncode}): {error}")


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    output = resolve(root, args.out)
    if output.exists() or output.is_symlink():
        raise BuildError(f"output path already exists: {output}")
    inputs: dict[str, tuple[dict[str, Any], bytes]] = {}
    for name, path in {
        "Image": args.image,
        "vmlinux": args.vmlinux,
        ".config": args.config,
        "build_result": args.build_result,
    }.items():
        inputs[name] = boot_verify.read_stable(resolve(root, path), f"P2.21 {name}")
    build_closure = artifact.verify(
        image=inputs["Image"][1],
        vmlinux=inputs["vmlinux"][1],
        config=inputs[".config"][1],
        build_result=inputs["build_result"][1],
    )
    image = inputs["Image"][1]
    boot_verify.parse_arm64_header(image)
    p219.classify_compiled_blob(image, "P2.21 Image")
    carrier_receipt, carrier = boot_verify.read_pinned_stable(
        resolve(root, args.carrier),
        E0_CARRIER_SIZE,
        E0_CARRIER_SHA256,
        "pinned E0 ramdisk carrier",
    )
    lz4_receipt, lz4 = boot_verify.read_pinned_stable(
        resolve(root, args.lz4),
        legacy.base_static.LZ4_SIZE,
        legacy.base_static.LZ4_SHA256,
        "lz4",
    )
    candidate, construction = replace_kernel(carrier, image)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output.name}.", dir=output.parent) as temporary:
        staging = Path(temporary)
        boot_path = staging / "boot.img"
        frame_path = staging / "boot.img.lz4"
        lz4_path = staging / ".lz4"
        boot_path.write_bytes(candidate)
        lz4_path.write_bytes(lz4)
        lz4_path.chmod(0o700)
        _run(
            [lz4_path, "--content-size", "-B6", "-f", "-q", boot_path, frame_path],
            "compress P2.21 boot",
        )
        roundtrip = staging / ".roundtrip.img"
        _run(
            [lz4_path, "-d", "-f", "-q", frame_path, roundtrip],
            "decompress P2.21 boot",
        )
        if roundtrip.read_bytes() != candidate:
            raise BuildError("P2.21 LZ4 roundtrip mismatch")
        roundtrip.unlink()
        lz4_path.unlink()
        odin = staging / "odin4"
        odin.mkdir()
        ap_path = odin / "AP.tar.md5"
        frame = frame_path.read_bytes()
        ap_structure = boot_slice.write_deterministic_boot_ap(frame, ap_path)
        if ap_structure.get("members") != ["boot.img.lz4"]:
            raise BuildError("P2.21 AP is not exactly boot-only")
        result = {
            "schema": SCHEMA,
            "target": artifact.TARGET,
            "verdict": VERDICT,
            "build_closure": build_closure,
            "inputs": {
                name: value[0] for name, value in inputs.items()
            }
            | {"carrier": carrier_receipt, "lz4": lz4_receipt},
            "construction": construction,
            "outputs": {
                "boot_img": _receipt(candidate),
                "boot_img_lz4": _receipt(frame),
                "ap_tar_md5": _receipt(ap_path.read_bytes()),
                "ap_structure": ap_structure,
            },
            "manifest_created": False,
            "safety": {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
            },
        }
        (staging / "artifact-result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="ascii",
        )
        os.replace(staging, output)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--vmlinux", type=Path, default=DEFAULT_VMLINUX)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--build-result", type=Path, default=DEFAULT_BUILD_RESULT)
    parser.add_argument("--carrier", type=Path, default=DEFAULT_CARRIER)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        result = build(parse_args(argv))
    except (
        BuildError,
        artifact.ArtifactError,
        p219.CheckError,
        boot_slice.BootSliceError,
        boot_verify.BootVerifyError,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
