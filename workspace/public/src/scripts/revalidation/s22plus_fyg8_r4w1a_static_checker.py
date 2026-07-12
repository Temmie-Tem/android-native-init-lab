#!/usr/bin/env python3
"""Independently audit three host-only FYG8 R4W1-A candidate reproductions.

The checker reconstructs each boot image from pinned R3C0 and R4W1 inputs. It
does not import the R4W1-A builder, construct artifacts, invoke Odin, enumerate
USB, contact a device, or authorize a live run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_r4w1a_static_checker_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
BOOT_SIZE = 100_663_296
KERNEL_START = 4_096
KERNEL_END = 41_495_040
KERNEL_SIZE = KERNEL_END - KERNEL_START
R4W1_MARKER = b"[[S22R4W1|id=9ed5923b08c5eedbbdb0aaa6f6a5200c|"

EXPECTED_R3C0_BOOT_SHA256 = "384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f"
EXPECTED_R3C0_AP_SHA256 = "8f2b16d3ee8932ff927e06fee8956f975ec3f9e5cc0ef16337e00ad5108d3c00"
EXPECTED_R4W1_IMAGE_SHA256 = "9552653de86dbdc2f1abd919b4d7b0d3f365fc878a56ed5ae09c82d0d81d844c"
EXPECTED_PATCH_SHA256 = "e66962c9e8cc503f9c5e94265816fdc2e96f4920a2d47387c6f1a4d9bbc6b787"

R4W1_EVIDENCE = (
    ("G static audit", 8_904, "2d2653f00044da98470e93dc993d6c11be078d1df713d8220e42e85c3a692ce5",
     "s22plus_fyg8_r4w1_static_audit_v2", "PASS_R4W1_STATIC_COMPATIBILITY"),
    ("H static audit", 8_904, "5e4b93d427758ba4e178b3d77ee3f3b858caecb0a26f0062d3986b9b526394cb",
     "s22plus_fyg8_r4w1_static_audit_v2", "PASS_R4W1_STATIC_COMPATIBILITY"),
    ("G/H reproducibility", 17_810, "71ab56b4c56010225145b82899535fbb9680c455e78aec19cebb39f39ad2cbd8",
     "s22plus_fyg8_r4w1_repro_check_v2", "PASS_R4W1_CLEAN_REPRODUCIBILITY"),
    ("patch contract", 6_439, "67582699a706a68b5b988e7334a56b4858de63e4e8a49ca6b00c1e77a9a2e973",
     "s22plus_fyg8_r4w1_patch_check_v1", "PASS_R4W1_HOST_PATCH_CONTRACT"),
)

DEFAULT_R3C0_BOOT = Path("workspace/private/outputs/s22plus_fyg8_r3c0_control/reproduction-a/boot.img")
DEFAULT_R3C0_AP = Path("workspace/private/outputs/s22plus_fyg8_r3c0_control/reproduction-a/odin4/AP.tar.md5")
DEFAULT_R4W1_IMAGE = Path("workspace/private/outputs/s22plus_fyg8_r4w1/remote-g-artifacts-final/Image")
DEFAULT_PATCH = Path("workspace/public/src/patches/s22plus_fyg8_r4w1_retained_init_witness.patch")
DEFAULT_EVIDENCE = (
    Path("workspace/private/outputs/s22plus_fyg8_r4w1/remote-g-static-final/result.json"),
    Path("workspace/private/outputs/s22plus_fyg8_r4w1/remote-h-static-final/result.json"),
    Path("workspace/private/outputs/s22plus_fyg8_r4w1/remote-gh-repro-final/result.json"),
    Path("workspace/private/outputs/s22plus_fyg8_r4w1/patch-check-final-v2.json"),
)
DEFAULT_REPRODUCTIONS = tuple(
    Path(f"workspace/private/outputs/s22plus_fyg8_r4w1a_candidate/reproduction-{name}")
    for name in ("a", "b", "c")
)


class CheckError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise CheckError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def load_r3_checker() -> Any:
    path = Path(__file__).with_name("s22plus_fyg8_r3_static_checker.py")
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r3_shared_audit", path)
    if spec is None or spec.loader is None:
        raise CheckError("cannot load R3 common static audit")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_stable(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CheckError(f"{label} missing or not a direct regular file: {path}")
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise CheckError(f"{label} is not a regular file: {path}")
        payload = handle.read()
        after = os.fstat(handle.fileno())
    current = path.stat(follow_symlinks=False)
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise CheckError(f"{label} changed while being read: {path}")
    return payload


def read_pinned(path: Path, size: int, sha256: str, label: str) -> tuple[dict[str, Any], bytes]:
    payload = read_stable(path, label)
    if len(payload) != size:
        raise CheckError(f"{label} size mismatch: {len(payload)} != {size}")
    actual = sha256_bytes(payload)
    if actual != sha256:
        raise CheckError(f"{label} SHA256 mismatch: {actual}")
    return {"path": str(path), "size": len(payload), "sha256": actual}, payload


def read_json_pinned(path: Path, size: int, sha256: str, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    pin, payload = read_pinned(path, size, sha256, label)
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError(f"{label} is not valid JSON") from exc
    if not isinstance(data, dict):
        raise CheckError(f"{label} top level must be an object")
    return pin, data


def parse_arm64_header(kernel: bytes) -> tuple[int, ...]:
    if len(kernel) < 64:
        raise CheckError("kernel is too short for ARM64 header")
    fields = struct.unpack_from("<IIQQQQQQII", kernel, 0)
    if fields[8] != 0x644D5241:
        raise CheckError("kernel ARM64 magic mismatch")
    return fields


def reconstruct_candidate(control: bytes, image: bytes) -> bytes:
    if len(control) != BOOT_SIZE or len(image) != KERNEL_SIZE:
        raise CheckError("candidate reconstruction input size mismatch")
    if parse_arm64_header(image) != parse_arm64_header(control[KERNEL_START:KERNEL_END]):
        raise CheckError("R4W1 ARM64 header differs from R3C0")
    if image.count(R4W1_MARKER) != 1:
        raise CheckError("R4W1 Image marker count is not exactly one")
    return control[:KERNEL_START] + image + control[KERNEL_END:]


def validate_candidate_bytes(candidate: bytes, expected: bytes, control: bytes, image: bytes) -> None:
    if len(candidate) != BOOT_SIZE:
        raise CheckError("candidate boot size mismatch")
    if candidate != expected:
        outside = sum(
            left != right
            for offset, (left, right) in enumerate(zip(control, candidate))
            if offset < KERNEL_START or offset >= KERNEL_END
        )
        raise CheckError(f"candidate differs from independent reconstruction; outside delta={outside}")
    if candidate[:KERNEL_START] != control[:KERNEL_START] or candidate[KERNEL_END:] != control[KERNEL_END:]:
        raise CheckError("candidate changed bytes outside the kernel interval")
    if candidate[KERNEL_START:KERNEL_END] != image:
        raise CheckError("candidate does not contain the exact R4W1 Image")


def audit_r4w1_evidence(root: Path, paths: tuple[Path, ...], patch_path: Path, image_path: Path) -> dict[str, Any]:
    if len(paths) != len(R4W1_EVIDENCE):
        raise CheckError("exactly four R4W1 evidence paths are required")
    records = []
    for path, expected in zip(paths, R4W1_EVIDENCE):
        label, size, digest, schema, verdict = expected
        pin, data = read_json_pinned(resolve(root, path), size, digest, label)
        if data.get("schema") != schema or data.get("verdict") != verdict:
            raise CheckError(f"{label} schema or verdict mismatch")
        if data.get("target") != TARGET or data.get("blockers", []) != []:
            raise CheckError(f"{label} target or blockers mismatch")
        records.append({**pin, "schema": schema, "verdict": verdict})

    repro = json.loads(read_pinned(resolve(root, paths[2]), R4W1_EVIDENCE[2][1], R4W1_EVIDENCE[2][2], "G/H reproducibility")[1])
    if repro.get("image_byte_identical") is not True or repro.get("reproducible") is not True:
        raise CheckError("R4W1 G/H reproducibility flags are not closed")
    images = repro.get("images", [])
    if len(images) != 2 or any(item.get("sha256") != EXPECTED_R4W1_IMAGE_SHA256 for item in images):
        raise CheckError("R4W1 G/H Image pins mismatch")

    patch_pin, patch = read_pinned(resolve(root, patch_path), resolve(root, patch_path).stat().st_size,
                                   EXPECTED_PATCH_SHA256, "R4W1 witness patch")
    image_pin, image = read_pinned(resolve(root, image_path), KERNEL_SIZE, EXPECTED_R4W1_IMAGE_SHA256,
                                   "R4W1 Image")
    if image.count(R4W1_MARKER) != 1:
        raise CheckError("R4W1 Image marker count is not exactly one")
    text = patch.decode("utf-8")
    call = "s22plus_fyg8_record_init_exec(ramdisk_execute_command);"
    success = "ret = run_init_process(ramdisk_execute_command);\n \t\tif (!ret) {"
    if text.count('return kernel_execve(init_filename, argv_init, envp_init);') != 1:
        raise CheckError("patch does not bind the witness to one kernel_execve path")
    if text.count('strcmp(init_filename, "/init") || task_pid_nr(current) != 1') != 1:
        raise CheckError("patch does not enforce exact /init and PID 1")
    if text.count(call) != 1 or success not in text or text.index(call) < text.index(success):
        raise CheckError("witness call is not exactly once after successful ramdisk init exec")
    return {
        "records": records,
        "patch": patch_pin,
        "image": image_pin,
        "marker_count": 1,
        "witness_gate": {
            "kernel_execve_path_count": 1,
            "exact_path": "/init",
            "exact_pid": 1,
            "record_call_after_success_count": 1,
            "verified": True,
        },
    }


def audit_manifest(path: Path, expected_hashes: dict[str, str]) -> dict[str, Any]:
    payload = read_stable(path, "candidate manifest")
    try:
        data = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError(f"invalid candidate manifest: {path}") from exc
    if data.get("schema") != "s22plus_fyg8_r4w1a_candidate_build_v1":
        raise CheckError("candidate manifest schema mismatch")
    if data.get("verdict") != "PASS_R4W1A_ARTIFACT_BUILT_HOST_ONLY":
        raise CheckError("candidate manifest verdict mismatch")
    if data.get("target") != TARGET:
        raise CheckError("candidate manifest target mismatch")
    inputs = data.get("inputs", {})
    if inputs.get("r3c0_boot", {}).get("sha256") != EXPECTED_R3C0_BOOT_SHA256:
        raise CheckError("candidate manifest R3C0 input mismatch")
    if inputs.get("r4w1_image", {}).get("sha256") != EXPECTED_R4W1_IMAGE_SHA256:
        raise CheckError("candidate manifest R4W1 input mismatch")
    hashes = data.get("artifacts", {}).get("hashes", {})
    for key, value in expected_hashes.items():
        if hashes.get(key) != value:
            raise CheckError(f"candidate manifest {key} mismatch")
    construction = data.get("construction", {})
    if construction.get("r4w1_marker_count") != 1:
        raise CheckError("candidate manifest marker count mismatch")
    if construction.get("patch_vbmeta_flag") is not False:
        raise CheckError("candidate manifest PATCHVBMETAFLAG mismatch")
    for key in (
        "kernel_equals_exact_r4w1_image", "r3c0_boot_header_preserved",
        "r3c0_post_kernel_bytes_preserved", "r3c0_ramdisk_preserved",
        "r3c0_signer_preserved", "r3c0_vbmeta_preserved",
        "r3c0_avb_footer_preserved", "arm64_header_exact_r3c0_match",
    ):
        if construction.get(key) is not True:
            raise CheckError(f"candidate manifest construction.{key} is not true")
    if construction.get("difference", {}).get("outside_kernel_changed_byte_count") != 0:
        raise CheckError("candidate manifest permits an outside-kernel delta")
    safety = data.get("safety", {})
    for key in ("device_contact", "usb_enumeration", "odin_transfer", "flash", "live_authorized", "r4w1a_live_authorized"):
        if safety.get(key) is not False:
            raise CheckError(f"candidate manifest safety.{key} is not false")
    if safety.get("boot_only_ap") is not True or safety.get("ap_members") != ["boot.img.lz4"]:
        raise CheckError("candidate manifest boot-only scope mismatch")
    if safety.get("stale_avb_descriptor_semantics_retained") is not True:
        raise CheckError("candidate manifest stale AVB semantics not explicit")
    return {"path": str(path), "size": len(payload), "sha256": sha256_bytes(payload), "verified": True}


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    r3 = load_r3_checker()
    common_args = r3.parse_args([])
    common, blobs, paths = r3.build_common_audit(common_args, root)

    control_path = resolve(root, args.r3c0_boot)
    control_pin, control = read_pinned(control_path, BOOT_SIZE, EXPECTED_R3C0_BOOT_SHA256, "R3C0 boot")
    control_contract = r3.validate_control_boot(blobs["stock"], control)
    control_avb = r3.run_avbtool(paths["avbtool"], control)
    r3.require_stale_avb(control_avb, "R3C0")
    control_ap = r3.validate_ap(resolve(root, args.r3c0_ap), None, EXPECTED_R3C0_AP_SHA256,
                                control, paths["lz4"], "R3C0 AP", True)

    evidence_args = tuple(args.r4w1_evidence or DEFAULT_EVIDENCE)
    reproduction_args = tuple(args.reproduction or DEFAULT_REPRODUCTIONS)
    r4w1 = audit_r4w1_evidence(root, evidence_args, args.patch, args.r4w1_image)
    _, image = read_pinned(resolve(root, args.r4w1_image), KERNEL_SIZE, EXPECTED_R4W1_IMAGE_SHA256, "R4W1 Image")
    expected = reconstruct_candidate(control, image)

    reproductions = []
    identity: tuple[str, str, str] | None = None
    for index, directory_arg in enumerate(reproduction_args, start=1):
        directory = resolve(root, directory_arg)
        boot_path = directory / "boot.img"
        boot = read_stable(boot_path, f"reproduction {index} boot")
        validate_candidate_bytes(boot, expected, control, image)
        avb = r3.run_avbtool(paths["avbtool"], boot)
        r3.require_stale_avb(avb, f"R4W1-A reproduction {index}")
        ap_path = directory / "odin4/AP.tar.md5"
        ap_bytes = read_stable(ap_path, f"reproduction {index} AP")
        ap = r3.validate_ap(ap_path, None, sha256_bytes(ap_bytes), boot, paths["lz4"],
                            f"R4W1-A reproduction {index} AP", True)
        lz4_bytes = read_stable(directory / "odin4/boot.img.lz4", f"reproduction {index} LZ4")
        if sha256_bytes(lz4_bytes) != ap["member_sha256"]:
            raise CheckError(f"reproduction {index} standalone LZ4 differs from AP member")
        hashes = {
            "boot_img": sha256_bytes(boot),
            "boot_img_lz4": sha256_bytes(lz4_bytes),
            "ap_tar_md5": sha256_bytes(ap_bytes),
            "kernel": EXPECTED_R4W1_IMAGE_SHA256,
        }
        manifest = audit_manifest(directory / "manifest.json", hashes)
        current = (hashes["boot_img"], hashes["boot_img_lz4"], hashes["ap_tar_md5"])
        if identity is None:
            identity = current
        elif current != identity:
            raise CheckError("three candidate reproductions are not byte-identical")
        reproductions.append({"index": index, "directory": str(directory), "hashes": hashes,
                              "manifest": manifest, "ap": ap, "avb_verify": avb})

    if len(reproductions) != 3:
        raise CheckError("exactly three candidate reproductions are required")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "inputs": {
            "r3_common_audit": common,
            "r3c0": {"boot": {**control_pin, **control_contract, "avb_verify": control_avb}, "ap": control_ap},
            "r4w1": r4w1,
        },
        "candidate": {
            "kernel_region": {"start": KERNEL_START, "end_exclusive": KERNEL_END},
            "independently_reconstructed": True,
            "outside_kernel_changed_byte_count": 0,
            "reproductions": reproductions,
            "byte_identical_count": 3,
        },
        "scope": {
            "host_only": True,
            "inputs_read_only": True,
            "artifact_construction": False,
            "device_contact": False,
            "usb_enumeration": False,
            "odin_invocation": False,
            "flash_authorized": False,
            "live_authorized": False,
        },
        "verdict": "PASS_R4W1A_THREE_REPRO_STATIC_CONTRACT",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r3c0-boot", type=Path, default=DEFAULT_R3C0_BOOT)
    parser.add_argument("--r3c0-ap", type=Path, default=DEFAULT_R3C0_AP)
    parser.add_argument("--r4w1-image", type=Path, default=DEFAULT_R4W1_IMAGE)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--r4w1-evidence", type=Path, action="append")
    parser.add_argument("--reproduction", type=Path, action="append")
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = audit(args)
    except (CheckError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        out = resolve(repo_root(), args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(encoded, encoding="ascii")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
