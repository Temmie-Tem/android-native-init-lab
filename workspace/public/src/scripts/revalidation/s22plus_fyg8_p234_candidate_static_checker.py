#!/usr/bin/env python3
"""Independently audit one deterministic P2.34 E1A boot-only candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_p234_candidate as candidate  # noqa: E402
import build_s22plus_fyg8_r4w1c_watchdog_carrier as carrier  # noqa: E402
import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p234_build_repro_check as repro  # noqa: E402
import s22plus_fyg8_p234_candidate_contract as contract  # noqa: E402
import s22plus_fyg8_p234_userspace_build as userspace  # noqa: E402


SCHEMA = "s22plus_fyg8_p234_candidate_static_checker_v1"
VERDICT = "PASS_P234_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY"
TARGET = contract.TARGET
DEFAULT_CANDIDATE = candidate.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p234/candidate-b")
DEFAULT_IMAGE = candidate.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = candidate.DEFAULT_REPRO_RESULT
DEFAULT_USERSPACE = candidate.DEFAULT_USERSPACE
DEFAULT_BASE_BOOT = candidate.DEFAULT_BASE_BOOT
DEFAULT_LZ4 = candidate.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = candidate.DEFAULT_MAGISKBOOT
DEFAULT_BUILD_A = repro.DEFAULT_BUILD_A
DEFAULT_BUILD_B = repro.DEFAULT_BUILD_B
DEFAULT_SOURCE = contract.DEFAULT_SOURCE
DEFAULT_INTENT = contract.DEFAULT_INTENT
DEFAULT_PATCH = contract.DEFAULT_PATCH
DEFAULT_NM = repro.DEFAULT_NM
DEFAULT_OBJDUMP = repro.DEFAULT_OBJDUMP
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p234/static-check-result.json"
)

ARTIFACT_LIMITS = {
    "artifact_result": 16 * 1024 * 1024,
    "boot_img": candidate.BOOT_SIZE,
    "boot_img_lz4": candidate.BOOT_SIZE,
    "ap_tar_md5": candidate.BOOT_SIZE,
}


class CheckError(ValueError):
    pass


def repo_root() -> Path:
    return contract.intent.repo_root()


def resolve(root: Path, value: Path) -> Path:
    return contract.intent.resolve(root, value)


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def stable_read(path: Path, label: str, maximum: int) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= maximum:
            raise CheckError(f"{label} is not a bounded regular file")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise CheckError(f"{label} read was short")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(before, name) != getattr(after, name)
        or getattr(after, name) != getattr(current, name)
        for name in fields
    ):
        raise CheckError(f"{label} changed while reading")
    return b"".join(chunks)


def require_unique_regular_storage(paths: list[Path]) -> None:
    identities = []
    for path in paths:
        metadata = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise CheckError(
                f"P2.34 critical artifact is not unique regular storage: {path}"
            )
        identities.append((metadata.st_dev, metadata.st_ino))
    if len(identities) != len(set(identities)):
        raise CheckError("P2.34 critical candidate artifacts are hardlinked")


def read_json(path: Path, label: str, maximum: int) -> tuple[dict[str, Any], bytes]:
    payload = stable_read(path, label, maximum)
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError(f"{label} is not valid ASCII JSON") from exc
    if not isinstance(value, dict):
        raise CheckError(f"{label} root is not an object")
    return value, payload


def require_receipt(actual: dict[str, Any], expected: Any, label: str) -> None:
    if not isinstance(expected, dict) or any(
        expected.get(name) != actual[name] for name in ("size", "sha256")
    ):
        raise CheckError(f"{label} receipt mismatch")


def run(command: list[str | Path], cwd: Path, label: str) -> bytes:
    completed = subprocess.run(
        [str(value) for value in command],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).decode("utf-8", "replace")
        raise CheckError(f"{label} failed rc={completed.returncode}: {detail[-2000:]}")
    return completed.stdout


def verify_artifact_result(
    value: dict[str, Any],
    *,
    exact_contract: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
    image_receipt: dict[str, Any],
    repro_receipt: dict[str, Any],
    userspace_closure: dict[str, Any],
) -> dict[str, Any]:
    for name, expected in {
        "schema": candidate.SCHEMA,
        "target": TARGET,
        "verdict": candidate.VERDICT,
        "candidate_contract": exact_contract,
        "manifest_created": False,
    }.items():
        if value.get(name) != expected:
            raise CheckError(f"candidate artifact result mismatch: {name}")
    if value.get("outputs", {}).get("ap_structure", {}).get("members") != [
        "boot.img.lz4"
    ]:
        raise CheckError("candidate result is not exactly boot-only")
    for name in ("boot_img", "boot_img_lz4", "ap_tar_md5"):
        require_receipt(outputs[name], value.get("outputs", {}).get(name), name)
    kernel = value.get("kernel_closure")
    if (
        not isinstance(kernel, dict)
        or kernel.get("result") != repro_receipt
        or kernel.get("image") != image_receipt
        or kernel.get("two_clean_builds_byte_identical") is not True
        or kernel.get("linked_audit_verified") is not True
    ):
        raise CheckError("candidate kernel closure mismatch")
    if value.get("userspace_closure") != userspace_closure:
        raise CheckError("candidate userspace closure mismatch")
    construction = value.get("construction")
    if not isinstance(construction, dict) or any(
        construction.get(name) is not expected
        for name, expected in {
            "header_preserved": True,
            "ramdisk_preserved": True,
            "kernel_exact_image": True,
            "magiskboot_nochange_byte_identical": True,
            "base_child_absent": True,
            "patch_vbmeta_flag": False,
        }.items()
    ):
        raise CheckError("candidate construction contract mismatch")
    if construction.get("outside_interval_changed_byte_count") != 0 or construction.get(
        "kernel_interval"
    ) != [candidate.KERNEL_START, candidate.KERNEL_END]:
        raise CheckError("candidate fixed kernel interval contract mismatch")
    safety = value.get("safety")
    expected_safety = {
        "host_only": True,
        "device_contact": False,
        "device_write": False,
        "odin_invoked": False,
        "flash": False,
        "partition_write": False,
        "live_authorized": False,
        "boot_only_ap": True,
        "ap_members": ["boot.img.lz4"],
        "no_shell": True,
        "no_usb_or_configfs": True,
        "no_block_write": True,
        "no_reboot_syscall": True,
    }
    if safety != expected_safety:
        raise CheckError("candidate artifact safety contract mismatch")
    return {"verified": True}


def verify_userspace(
    root: Path, directory: Path, exact_contract: dict[str, Any]
) -> tuple[dict[str, bytes], dict[str, Any], dict[str, Any]]:
    if directory.is_symlink() or not directory.is_dir():
        raise CheckError("P2.34 userspace directory missing or indirect")
    if {path.name for path in directory.iterdir()} != {
        "init",
        "s22-e1-child",
        "userspace-result.json",
    }:
        raise CheckError("P2.34 userspace inventory mismatch")
    result, result_payload = read_json(
        directory / "userspace-result.json", "P2.34 userspace result", 8 * 1024 * 1024
    )
    if (
        result.get("schema") != userspace.SCHEMA
        or result.get("target") != TARGET
        or result.get("verdict") != userspace.VERDICT
        or result.get("candidate_contract") != exact_contract
        or result.get("run_id") != exact_contract["run_id"]
        or result.get("profile") != "E1A"
        or result.get("two_build_byte_identical") is not True
    ):
        raise CheckError("P2.34 userspace result identity mismatch")
    paths = {"init": directory / "init", "child": directory / "s22-e1-child"}
    payloads = {
        name: stable_read(path, f"P2.34 {name}", 1024 * 1024)
        for name, path in paths.items()
    }
    for name, path in paths.items():
        require_receipt(receipt(payloads[name]), result.get("outputs", {}).get(name), name)
        if path.stat(follow_symlinks=False).st_mode & 0o777 != 0o755:
            raise CheckError(f"P2.34 {name} host mode mismatch")
    run_id = bytes.fromhex(exact_contract["run_id"])
    init = payloads["init"]
    child = payloads["child"]
    module_counts = {
        name: init.count(name.encode("ascii"))
        for name in userspace.FORBIDDEN_MODULE_NAMES
    }
    forbidden = (b"sec_log_buf.ko", b"/dev/mem", b"/dev/block", b"/bin/sh")
    if (
        init.count(run_id) != 1
        or any(module_counts.values())
        or any(token in init for token in forbidden)
        or init.count(b"/proc/s22_checkpoint") != 1
        or init.count(b"/s22-e1-child") != 1
        or init.count(userspace.CHILD_TOKEN) != 1
        or child.count(userspace.CHILD_TOKEN) != 1
    ):
        raise CheckError("P2.34 E1A binary closure mismatch")
    source = result.get("source_contract")
    fresh_source = userspace.p233.audit_sources(
        userspace.p233.read_direct(
            root / userspace.p233.DEFAULT_CLIENT, "P2.34 checkpoint client"
        ),
        userspace.p233.read_direct(
            root / userspace.p233.DEFAULT_RUNTIME, "P2.34 runtime wrapper"
        ),
        userspace.p233.read_direct(
            root / userspace.p233.DEFAULT_LEGACY_RUNTIME, "P2.34 legacy runtime"
        ),
        userspace.p233.read_direct(
            root / userspace.p233.DEFAULT_HEADER, "P2.34 checkpoint header"
        ),
        userspace.p233.read_direct(
            root / userspace.p233.DEFAULT_CHILD, "P2.34 child source"
        ),
    )
    if (
        not isinstance(source, dict)
        or source != fresh_source
        or source.get("verified") is not True
        or source.get("sec_log_buf_absent") is not True
        or source.get("terminal_dominance_verified") is not True
    ):
        raise CheckError("P2.34 E1A source closure mismatch")
    qemu_path = Path(userspace.require_tools()["qemu-aarch64"])
    qemu = stable_read(qemu_path, "P2.34 qemu-aarch64", 32 * 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="s22-p234-child-audit-") as temporary:
        staged_qemu = Path(temporary) / "qemu-aarch64"
        staged_child = Path(temporary) / "s22-e1-child"
        staged_qemu.write_bytes(qemu)
        staged_child.write_bytes(payloads["child"])
        staged_qemu.chmod(0o700)
        staged_child.chmod(0o700)
        child_run = subprocess.run(
            [staged_qemu, staged_child],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    if (
        child_run.returncode != userspace.CHILD_EXIT
        or child_run.stdout != userspace.CHILD_TOKEN
        or child_run.stderr
    ):
        raise CheckError("P2.34 independent child token/exit check failed")
    safety = result.get("safety")
    if not isinstance(safety, dict) or safety.get("host_only") is not True or any(
        safety.get(name) is not False for name in safety if name != "host_only"
    ):
        raise CheckError("P2.34 userspace safety contract mismatch")
    closure = {
        "result": receipt(result_payload),
        "init": receipt(init),
        "child": receipt(child),
        "two_build_byte_identical": True,
        "verified": True,
    }
    return payloads, closure, receipt(qemu)


def verify_repro(
    root: Path, args: argparse.Namespace, exact_contract: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, payload = read_json(
        resolve(root, args.repro_result),
        "P2.34 build reproducibility result",
        16 * 1024 * 1024,
    )
    fresh = repro.check(
        argparse.Namespace(
            build_a=args.build_a,
            build_b=args.build_b,
            source=args.source,
            intent=args.intent,
            patch=args.patch,
            nm=args.nm,
            objdump=args.objdump,
        )
    )
    if result != fresh or result.get("candidate_contract") != exact_contract:
        raise CheckError("P2.34 reproducibility result differs from fresh verification")
    return result, receipt(payload)


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    exact_contract = contract.verify(
        root,
        resolve(root, args.source),
        resolve(root, args.intent),
        resolve(root, args.patch),
    )
    repro_result, repro_receipt = verify_repro(root, args, exact_contract)
    image = stable_read(
        resolve(root, args.image), "P2.34 Image", candidate.KERNEL_END - candidate.KERNEL_START
    )
    image_receipt = receipt(image)
    if image_receipt != repro_result.get("build_a", {}).get("artifacts", {}).get("Image"):
        raise CheckError("P2.34 Image differs from reproducibility result")
    boot_verify.parse_arm64_header(image)
    userspace_payloads, userspace_closure, qemu_receipt = verify_userspace(
        root, resolve(root, args.userspace), exact_contract
    )

    directory = resolve(root, args.candidate)
    if directory.is_symlink() or not directory.is_dir():
        raise CheckError("P2.34 candidate directory missing or indirect")
    if {path.name for path in directory.iterdir()} != {
        "artifact-result.json",
        "boot.img",
        "boot.img.lz4",
        "odin4",
    }:
        raise CheckError("P2.34 candidate inventory mismatch")
    odin = directory / "odin4"
    if odin.is_symlink() or not odin.is_dir() or {
        path.name for path in odin.iterdir()
    } != {"AP.tar.md5"}:
        raise CheckError("P2.34 Odin inventory mismatch")
    if any((directory / name).exists() for name in ("manifest.json", "run-manifest.json")):
        raise CheckError("P2.34 candidate unexpectedly created a live manifest")

    paths = {
        "artifact_result": directory / "artifact-result.json",
        "boot_img": directory / "boot.img",
        "boot_img_lz4": directory / "boot.img.lz4",
        "ap_tar_md5": odin / "AP.tar.md5",
    }
    payloads = {
        name: stable_read(path, f"P2.34 {name}", ARTIFACT_LIMITS[name])
        for name, path in paths.items()
    }
    output_receipts = {
        name: receipt(payloads[name])
        for name in ("boot_img", "boot_img_lz4", "ap_tar_md5")
    }
    artifact_result, _artifact_payload = read_json(
        paths["artifact_result"], "P2.34 artifact result", ARTIFACT_LIMITS["artifact_result"]
    )
    if _artifact_payload != payloads["artifact_result"]:
        raise CheckError("P2.34 artifact result changed between independent reads")
    verify_artifact_result(
        artifact_result,
        exact_contract=exact_contract,
        outputs=output_receipts,
        image_receipt=image_receipt,
        repro_receipt=repro_receipt,
        userspace_closure=userspace_closure,
    )

    directory_b = resolve(root, args.candidate_b)
    if directory_b.resolve() == directory.resolve():
        raise CheckError("P2.34 package reproducibility inputs must be distinct")
    if directory_b.is_symlink() or not directory_b.is_dir():
        raise CheckError("P2.34 candidate-b directory missing or indirect")
    if {path.name for path in directory_b.iterdir()} != {
        "artifact-result.json",
        "boot.img",
        "boot.img.lz4",
        "odin4",
    }:
        raise CheckError("P2.34 candidate-b inventory mismatch")
    odin_b = directory_b / "odin4"
    if odin_b.is_symlink() or not odin_b.is_dir() or {
        path.name for path in odin_b.iterdir()
    } != {"AP.tar.md5"}:
        raise CheckError("P2.34 candidate-b Odin inventory mismatch")
    if any((directory_b / name).exists() for name in ("manifest.json", "run-manifest.json")):
        raise CheckError("P2.34 candidate-b unexpectedly created a live manifest")
    paths_b = {
        "artifact_result": directory_b / "artifact-result.json",
        "boot_img": directory_b / "boot.img",
        "boot_img_lz4": directory_b / "boot.img.lz4",
        "ap_tar_md5": odin_b / "AP.tar.md5",
    }
    require_unique_regular_storage([*paths.values(), *paths_b.values()])
    payloads_b = {
        name: stable_read(path, f"P2.34 candidate-b {name}", ARTIFACT_LIMITS[name])
        for name, path in paths_b.items()
    }
    if payloads_b != payloads:
        changed = [name for name in payloads if payloads_b[name] != payloads[name]]
        raise CheckError(f"P2.34 package reproducibility mismatch: {changed}")
    artifact_result_b, artifact_payload_b = read_json(
        paths_b["artifact_result"],
        "P2.34 candidate-b artifact result",
        ARTIFACT_LIMITS["artifact_result"],
    )
    if artifact_payload_b != payloads_b["artifact_result"]:
        raise CheckError("P2.34 candidate-b result changed between independent reads")
    verify_artifact_result(
        artifact_result_b,
        exact_contract=exact_contract,
        outputs={
            name: receipt(payloads_b[name])
            for name in ("boot_img", "boot_img_lz4", "ap_tar_md5")
        },
        image_receipt=image_receipt,
        repro_receipt=repro_receipt,
        userspace_closure=userspace_closure,
    )

    base_boot = carrier.read_exact_file(
        resolve(root, args.base_boot),
        candidate.BOOT_SIZE,
        carrier.EXPECTED_BASE_BOOT_SHA256,
        "known Magisk base boot",
    )
    lz4 = carrier.read_exact_file(
        resolve(root, args.lz4),
        carrier.r4w1b.LZ4_SIZE,
        carrier.r4w1b.LZ4_SHA256,
        "pinned lz4",
    )
    magiskboot = carrier.read_exact_file(
        resolve(root, args.magiskboot),
        carrier.MAGISKBOOT_SIZE,
        carrier.MAGISKBOOT_SHA256,
        "pinned magiskboot",
    )
    ap_info, ap_frame = boot_verify.parse_ap_tar_md5(payloads["ap_tar_md5"])
    if ap_frame != payloads["boot_img_lz4"] or ap_info["member"]["name"] != "boot.img.lz4":
        raise CheckError("P2.34 AP member mismatch")

    with tempfile.TemporaryDirectory(prefix="s22-p234-static-") as name:
        work = Path(name)
        tools = work / "tools"
        base_unpack = work / "base-unpack"
        candidate_unpack = work / "candidate-unpack"
        tools.mkdir()
        base_unpack.mkdir()
        candidate_unpack.mkdir()
        lz4_path = tools / "lz4"
        magiskboot_path = tools / "magiskboot"
        base_path = tools / "base.boot.img"
        init_path = tools / "init"
        child_path = tools / "s22-e1-child"
        frame_path = tools / "boot.img.lz4"
        candidate_path = tools / "candidate.boot.img"
        for path, data, executable in (
            (lz4_path, lz4, True),
            (magiskboot_path, magiskboot, True),
            (base_path, base_boot, False),
            (init_path, userspace_payloads["init"], True),
            (child_path, userspace_payloads["child"], True),
            (frame_path, ap_frame, False),
            (candidate_path, payloads["boot_img"], False),
        ):
            path.write_bytes(data)
            path.chmod(0o700 if executable else 0o600)
        roundtrip = tools / "roundtrip.boot.img"
        run([lz4_path, "-d", "-f", "-q", frame_path, roundtrip], work, "decompress AP")
        if roundtrip.read_bytes() != payloads["boot_img"]:
            raise CheckError("P2.34 independent LZ4 roundtrip mismatch")

        run([magiskboot_path, "unpack", "-h", base_path], base_unpack, "unpack base boot")
        base_ramdisk = base_unpack / "ramdisk.cpio"
        child_exists = subprocess.run(
            [magiskboot_path, "cpio", base_ramdisk, "exists s22-e1-child"],
            cwd=base_unpack,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        if child_exists.returncode != 1:
            raise CheckError(
                "P2.34 independent base child absence check failed "
                f"rc={child_exists.returncode}"
            )
        run(
            [magiskboot_path, "cpio", base_ramdisk, f"add 750 init {init_path}"],
            base_unpack,
            "replace E1A init independently",
        )
        run(
            [
                magiskboot_path,
                "cpio",
                base_ramdisk,
                f"add 750 s22-e1-child {child_path}",
            ],
            base_unpack,
            "add E1A child independently",
        )
        reconstructed = tools / "reconstructed.carrier.img"
        run(
            [magiskboot_path, "repack", base_path, reconstructed],
            base_unpack,
            "repack E1A carrier independently",
        )
        carrier_boot = reconstructed.read_bytes()
        expected = (
            carrier_boot[: candidate.KERNEL_START]
            + image
            + carrier_boot[candidate.KERNEL_END :]
        )
        if payloads["boot_img"] != expected:
            raise CheckError("P2.34 candidate differs from independent reconstruction")
        carrier_parsed = boot_verify.parse_boot_v4(carrier_boot)
        submitted = boot_verify.parse_boot_v4(payloads["boot_img"])
        if (
            carrier_parsed.header != submitted.header
            or carrier_parsed.ramdisk != submitted.ramdisk
            or submitted.kernel != image
        ):
            raise CheckError("P2.34 fixed-interval boot semantics mismatch")

        run(
            [magiskboot_path, "unpack", "-h", candidate_path],
            candidate_unpack,
            "unpack P2.34 candidate",
        )
        extracted_init = tools / "extracted.init"
        extracted_child = tools / "extracted.child"
        final_ramdisk = candidate_unpack / "ramdisk.cpio"
        run(
            [magiskboot_path, "cpio", final_ramdisk, f"extract init {extracted_init}"],
            candidate_unpack,
            "extract P2.34 init",
        )
        run(
            [
                magiskboot_path,
                "cpio",
                final_ramdisk,
                f"extract s22-e1-child {extracted_child}",
            ],
            candidate_unpack,
            "extract P2.34 child",
        )
        if (
            extracted_init.read_bytes() != userspace_payloads["init"]
            or extracted_child.read_bytes() != userspace_payloads["child"]
            or (candidate_unpack / "kernel").read_bytes() != image
        ):
            raise CheckError("P2.34 extracted candidate closure mismatch")

    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "candidate_contract": exact_contract,
        "build_repro": {
            "result": repro_receipt,
            "image": image_receipt,
            "fresh_reverification": True,
            "two_clean_builds_byte_identical": True,
            "linked_audit_verified": True,
        },
        "candidate": {
            "artifacts": {name: receipt(data) for name, data in payloads.items()},
            "candidate_b_artifacts": {
                name: receipt(data) for name, data in payloads_b.items()
            },
            "base_boot": receipt(base_boot),
            "ap": ap_info,
            "fixed_interval": {
                "kernel_start": candidate.KERNEL_START,
                "kernel_end_exclusive": candidate.KERNEL_END,
                "header_preserved": True,
                "ramdisk_preserved": True,
                "outside_interval_changed_byte_count": 0,
                "verified": True,
            },
            "userspace": userspace_closure,
            "independent_reconstruction": True,
            "independent_lz4_roundtrip": True,
            "independent_magiskboot_unpack": True,
            "writer_exclusion_verified": True,
            "two_package_builds_byte_identical": True,
            "manifest_absent": True,
            "boot_only_ap": True,
            "verified": True,
        },
        "tools": {
            "lz4": receipt(lz4),
            "magiskboot": receipt(magiskboot),
            "qemu_aarch64": qemu_receipt,
        },
        "limits": [
            "host-only artifact qualification grants no D0, D1, F1, or live authority",
            "candidate execution and retained observation remain unproved",
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
    parser.add_argument("--candidate-b", type=Path, default=DEFAULT_CANDIDATE_B)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--repro-result", type=Path, default=DEFAULT_REPRO_RESULT)
    parser.add_argument("--userspace", type=Path, default=DEFAULT_USERSPACE)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--build-a", type=Path, default=DEFAULT_BUILD_A)
    parser.add_argument("--build-b", type=Path, default=DEFAULT_BUILD_B)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--nm", type=Path, default=DEFAULT_NM)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def durable_create(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise CheckError(f"short output write: {path}")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        result = audit(args)
        encoded = (
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("ascii")
            + b"\n"
        )
        durable_create(resolve(repo_root(), args.out), encoded)
    except (
        CheckError,
        candidate.BuildError,
        carrier.BuildError,
        boot_verify.BootVerifyError,
        repro.CheckError,
        contract.ContractError,
        contract.intent.IntentError,
        userspace.p233.CheckError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
