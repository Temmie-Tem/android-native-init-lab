#!/usr/bin/env python3
"""Independently derive the P2.21 kernel, boot, AP, init and writer closure."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_p221_candidate as candidate  # noqa: E402
import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p219_same_ring_contract as p219  # noqa: E402
import s22plus_fyg8_p221_build_artifact_contract as artifact  # noqa: E402
import s22plus_fyg8_r4w1e0_pid1_userspace_proof as proof  # noqa: E402
import s22plus_fyg8_r4w1e_e1_candidate_static_checker as legacy  # noqa: E402
import s22plus_fyg8_r4w1e_e1_host_contract as e1  # noqa: E402


SCHEMA = "s22plus_fyg8_p221_candidate_static_checker_v1"
VERDICT = "PASS_P221_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_VMLINUX = candidate.DEFAULT_VMLINUX
DEFAULT_CONFIG = candidate.DEFAULT_CONFIG
DEFAULT_BUILD_RESULT = candidate.DEFAULT_BUILD_RESULT
DEFAULT_CARRIER = candidate.DEFAULT_CARRIER
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = legacy.DEFAULT_MAGISKBOOT
DEFAULT_VENDOR_BOOT = legacy.DEFAULT_VENDOR_BOOT
DEFAULT_INIT = proof.DEFAULT_INIT
DEFAULT_RUNTIME_RECEIPT = proof.DEFAULT_RUNTIME_RECEIPT
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p221_candidate/static-check-result.json"
)


class CheckError(ValueError):
    """An independently derived P2.21 artifact property failed."""


def repo_root() -> Path:
    return candidate.repo_root()


def resolve(root: Path, value: Path) -> Path:
    return candidate.resolve(root, value)


def _require_receipt(actual: dict[str, Any], expected: Any, label: str) -> None:
    if not isinstance(expected, dict) or any(
        expected.get(name) != actual[name] for name in ("size", "sha256")
    ):
        raise CheckError(f"{label} receipt mismatch")


def _run(command: list[Path | str], cwd: Path, label: str) -> None:
    completed = subprocess.run(
        [str(value) for value in command],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", "replace")[-1000:]
        raise CheckError(f"{label} failed ({completed.returncode}): {error}")


def verify_writer_exclusion(root: Path) -> dict[str, Any]:
    source_check = proof.check_runtime_sources(root)
    runtime_path = root / "workspace/public/src/native-init/s22plus_r4w1e_e1_runtime.c"
    runtime = runtime_path.read_text(encoding="ascii")
    match = re.search(
        r"static const struct module_spec k_modules\[MODULE_COUNT\] = \{(.*?)\n\};",
        runtime,
        flags=re.DOTALL,
    )
    if match is None:
        raise CheckError("pinned init module table missing")
    loaded = re.findall(r'\{"([^"]+\.ko)",\s*"[^"]+"\}', match.group(1))
    expected = [row[0] for row in e1.MODULE_SPECS]
    if loaded != expected:
        raise CheckError("pinned init module load set mismatch")
    forbidden = ("sec_log_buf.ko", "0x800200000", "/dev/mem", "/dev/block")
    hits = [value for value in forbidden if value in runtime]
    if hits:
        raise CheckError(f"pinned init contains forbidden ring-writer path: {hits}")
    return {
        "runtime_sources": source_check,
        "loaded_modules": loaded,
        "sec_log_buf_loaded": False,
        "direct_ring_writer_present": False,
        "verified": True,
    }


def _parse_result(data: bytes) -> dict[str, Any]:
    try:
        result = json.loads(data.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("candidate artifact result is not valid JSON") from exc
    if not isinstance(result, dict):
        raise CheckError("candidate artifact result is not an object")
    for name, expected in {
        "schema": candidate.SCHEMA,
        "target": artifact.TARGET,
        "verdict": candidate.VERDICT,
        "manifest_created": False,
    }.items():
        if result.get(name) != expected:
            raise CheckError(f"candidate artifact result {name} mismatch")
    safety = result.get("safety")
    if not isinstance(safety, dict) or any(
        safety.get(name) is not expected
        for name, expected in {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
        }.items()
    ):
        raise CheckError("candidate artifact safety contract mismatch")
    if not isinstance(result.get("outputs"), dict):
        raise CheckError("candidate artifact output receipts are malformed")
    return result


def verify_fixed_interval(
    carrier: bytes, image: bytes, submitted: bytes
) -> dict[str, Any]:
    if (
        len(carrier) != candidate.BOOT_SIZE
        or len(submitted) != candidate.BOOT_SIZE
        or len(image) != candidate.KERNEL_END - candidate.KERNEL_START
    ):
        raise CheckError("independent fixed boot layout size mismatch")
    expected = (
        carrier[: candidate.KERNEL_START]
        + image
        + carrier[candidate.KERNEL_END :]
    )
    if submitted != expected:
        raise CheckError("candidate differs from independent fixed-interval construction")
    carrier_boot = boot_verify.parse_boot_v4(carrier)
    submitted_boot = boot_verify.parse_boot_v4(submitted)
    if carrier_boot.header != submitted_boot.header:
        raise CheckError("candidate boot header differs from the carrier")
    if carrier_boot.ramdisk != submitted_boot.ramdisk:
        raise CheckError("candidate ramdisk differs from the carrier")
    if submitted_boot.kernel != image:
        raise CheckError("candidate boot kernel differs from the checked Image")
    return {
        "kernel_start": candidate.KERNEL_START,
        "kernel_end_exclusive": candidate.KERNEL_END,
        "header_preserved": True,
        "ramdisk_preserved": True,
        "outside_interval_changed_byte_count": 0,
        "verified": True,
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    directory = resolve(root, args.candidate)
    if directory.is_symlink() or not directory.is_dir():
        raise CheckError("candidate artifact directory missing or indirect")
    expected_entries = {"artifact-result.json", "boot.img", "boot.img.lz4", "odin4"}
    if {path.name for path in directory.iterdir()} != expected_entries:
        raise CheckError("candidate artifact directory inventory mismatch")
    odin_directory = directory / "odin4"
    if odin_directory.is_symlink() or not odin_directory.is_dir():
        raise CheckError("candidate Odin directory missing or indirect")
    if {path.name for path in odin_directory.iterdir()} != {"AP.tar.md5"}:
        raise CheckError("candidate Odin directory inventory mismatch")
    if any((directory / name).exists() for name in ("manifest.json", "run-manifest.json")):
        raise CheckError("P2.21 must not create a live/run manifest")
    paths = {
        "boot_img": directory / "boot.img",
        "boot_img_lz4": directory / "boot.img.lz4",
        "ap_tar_md5": directory / "odin4/AP.tar.md5",
        "artifact_result": directory / "artifact-result.json",
    }
    loaded = {name: boot_verify.read_stable(path, name) for name, path in paths.items()}
    receipts = {name: value[0] for name, value in loaded.items()}
    data = {name: value[1] for name, value in loaded.items()}
    artifact_result = _parse_result(data["artifact_result"])
    for name in ("boot_img", "boot_img_lz4", "ap_tar_md5"):
        _require_receipt(receipts[name], artifact_result.get("outputs", {}).get(name), name)

    build_inputs = {
        name: boot_verify.read_stable(resolve(root, path), f"P2.21 {name}")
        for name, path in {
            "Image": args.image,
            "vmlinux": args.vmlinux,
            ".config": args.config,
            "build_result": args.build_result,
        }.items()
    }
    build_closure = artifact.verify(
        image=build_inputs["Image"][1],
        vmlinux=build_inputs["vmlinux"][1],
        config=build_inputs[".config"][1],
        build_result=build_inputs["build_result"][1],
        vmlinux_path=resolve(root, args.vmlinux),
    )
    carrier_receipt, carrier = boot_verify.read_pinned_stable(
        resolve(root, args.carrier),
        candidate.E0_CARRIER_SIZE,
        candidate.E0_CARRIER_SHA256,
        "pinned E0 ramdisk carrier",
    )
    fixed_interval = verify_fixed_interval(
        carrier, build_inputs["Image"][1], data["boot_img"]
    )

    lz4_receipt, lz4 = boot_verify.read_pinned_stable(
        resolve(root, args.lz4),
        legacy.base_static.LZ4_SIZE,
        legacy.base_static.LZ4_SHA256,
        "lz4",
    )
    magiskboot_receipt, magiskboot = boot_verify.read_pinned_stable(
        resolve(root, args.magiskboot),
        legacy.carrier_inputs.MAGISKBOOT_SIZE,
        legacy.carrier_inputs.MAGISKBOOT_SHA256,
        "magiskboot",
    )
    vendor_receipt, vendor_boot = boot_verify.read_pinned_stable(
        resolve(root, args.vendor_boot),
        legacy.base_static.VENDOR_BOOT_SIZE,
        legacy.base_static.VENDOR_BOOT_SHA256,
        "stock vendor_boot",
    )
    runtime_receipt_path = resolve(root, args.runtime_receipt)
    runtime = proof.check_runtime_artifact(resolve(root, args.init), runtime_receipt_path)
    runtime_receipt, runtime_receipt_bytes = boot_verify.read_stable(
        runtime_receipt_path, "pinned runtime receipt"
    )
    if runtime_receipt["sha256"] != runtime["receipt_sha256"]:
        raise CheckError("runtime receipt changed between independent reads")
    try:
        runtime_contract = json.loads(runtime_receipt_bytes.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("pinned runtime receipt is not valid JSON") from exc
    expected_child = runtime_contract.get("child")
    if (
        not isinstance(expected_child, dict)
        or not isinstance(expected_child.get("size"), int)
        or expected_child["size"] <= 0
        or not isinstance(expected_child.get("sha256"), str)
        or len(expected_child["sha256"]) != 64
    ):
        raise CheckError("pinned runtime child receipt is malformed")
    writer_exclusion = verify_writer_exclusion(root)
    expected_init = {"size": runtime["size"], "sha256": runtime["sha256"]}

    ap_info, ap_frame = boot_verify.parse_ap_tar_md5(data["ap_tar_md5"])
    if ap_frame != data["boot_img_lz4"]:
        raise CheckError("AP member differs from submitted LZ4 frame")
    ap_members = [{"name": ap_info["member"]["name"], "type": "regular"}]
    with tempfile.TemporaryDirectory(prefix="s22-p221-static-") as temporary:
        work = Path(temporary)
        lz4_path = work / "lz4"
        magiskboot_path = work / "magiskboot"
        boot_path = work / "boot.img"
        frame_path = work / "boot.img.lz4"
        for path, contents in (
            (lz4_path, lz4),
            (magiskboot_path, magiskboot),
            (boot_path, data["boot_img"]),
            (frame_path, ap_frame),
        ):
            path.write_bytes(contents)
        lz4_path.chmod(0o700)
        magiskboot_path.chmod(0o700)
        roundtrip = work / "roundtrip.img"
        _run(
            [lz4_path, "-d", "-f", "-q", frame_path, roundtrip],
            work,
            "decompress AP member",
        )
        if roundtrip.read_bytes() != data["boot_img"]:
            raise CheckError("independent AP LZ4 roundtrip mismatch")
        unpack = work / "unpack"
        unpack.mkdir()
        _run(
            [magiskboot_path, "unpack", "-h", boot_path],
            unpack,
            "unpack candidate boot",
        )
        extracted_kernel = (unpack / "kernel").read_bytes()
        ramdisk = unpack / "ramdisk.cpio"
        extracted_init = work / "init"
        extracted_child = work / "s22-e1-child"
        _run(
            [magiskboot_path, "cpio", ramdisk, f"extract init {extracted_init}"],
            unpack,
            "extract /init",
        )
        _run(
            [magiskboot_path, "cpio", ramdisk, f"extract s22-e1-child {extracted_child}"],
            unpack,
            "extract child",
        )
        for path, expected, label in (
            (extracted_init, expected_init, "/init"),
            (extracted_child, expected_child, "/s22-e1-child"),
        ):
            receipt, _contents = boot_verify.read_stable(path, label)
            _require_receipt(receipt, expected, label)
        rootfs = legacy.rootfs_audit(
            data["boot_img"],
            vendor_boot,
            lz4_path,
            expected_init=expected_init,
            expected_child=expected_child,
            run_id=proof.PROBE_ID,
        )

    extracted_closure = p219.verify_extracted_artifact_closure(
        image=build_inputs["Image"][1],
        vmlinux=build_inputs["vmlinux"][1],
        boot_image=data["boot_img"],
        extracted_boot_kernel=extracted_kernel,
        ap_members=ap_members,
    )
    critical = [*paths.values()]
    inodes = []
    for path in critical:
        metadata = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode):
            raise CheckError(f"critical artifact is not regular: {path}")
        inodes.append((metadata.st_dev, metadata.st_ino))
    if len(inodes) != len(set(inodes)):
        raise CheckError("critical candidate artifacts are hardlinked")
    return {
        "schema": SCHEMA,
        "target": artifact.TARGET,
        "verdict": VERDICT,
        "build_closure": build_closure,
        "candidate": {
            "artifacts": receipts,
            "carrier": carrier_receipt,
            "fixed_interval": fixed_interval,
            "ap": ap_info,
            "independent_lz4_roundtrip": True,
            "independent_magiskboot_unpack": True,
            "extracted_artifact_closure": extracted_closure,
            "rootfs": rootfs,
            "runtime": runtime,
            "writer_exclusion": writer_exclusion,
            "manifest_absent": True,
            "verified": True,
        },
        "tools": {"lz4": lz4_receipt, "magiskboot": magiskboot_receipt},
        "vendor_boot": vendor_receipt,
        "limits": [
            "host-only artifact qualification grants no D0, D1, F1, or live authority",
            "cache-to-DRAM persistence remains a later live acceptance property",
        ],
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "flash": False,
            "partition_write": False,
            "manifest_created": False,
            "live_authorized": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--vmlinux", type=Path, default=DEFAULT_VMLINUX)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--build-result", type=Path, default=DEFAULT_BUILD_RESULT)
    parser.add_argument("--carrier", type=Path, default=DEFAULT_CARRIER)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--vendor-boot", type=Path, default=DEFAULT_VENDOR_BOOT)
    parser.add_argument("--init", type=Path, default=DEFAULT_INIT)
    parser.add_argument("--runtime-receipt", type=Path, default=DEFAULT_RUNTIME_RECEIPT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        result = audit(args)
        output = resolve(repo_root(), args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            encoded = (
                json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("ascii")
                + b"\n"
            )
            offset = 0
            while offset < len(encoded):
                written = os.write(descriptor, encoded[offset:])
                if written <= 0:
                    raise CheckError("short write while recording static result")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except (
        CheckError,
        candidate.BuildError,
        artifact.ArtifactError,
        p219.CheckError,
        proof.CheckError,
        legacy.CheckError,
        boot_verify.BootVerifyError,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
