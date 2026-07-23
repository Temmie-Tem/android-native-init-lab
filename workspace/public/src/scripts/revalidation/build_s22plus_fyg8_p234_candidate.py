#!/usr/bin/env python3
"""Build one deterministic boot-only FYG8 E1 candidate host-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_p221_candidate as layout  # noqa: E402
import build_s22plus_fyg8_r4w1c_watchdog_carrier as carrier  # noqa: E402
import s22plus_boot_slice as boot_slice  # noqa: E402
import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p234_build_repro_check as repro  # noqa: E402
import s22plus_fyg8_p234_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_p234_userspace_build as userspace  # noqa: E402
import s22plus_fyg8_p242_e2_stock_closure as e2_closure  # noqa: E402
import s22plus_fyg8_p245_e2_stock_closure as p245_e2_closure  # noqa: E402


SCHEMA = "s22plus_fyg8_p234_candidate_artifact_result_v1"
VERDICT = "PASS_P234_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
TARGET = candidate_contract.TARGET
DEFAULT_IMAGE = repro.DEFAULT_BUILD_A / "Image"
DEFAULT_REPRO_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_p234/build-repro-result.json"
)
DEFAULT_USERSPACE = userspace.DEFAULT_OUT
DEFAULT_BASE_BOOT = carrier.DEFAULT_BASE_BOOT
DEFAULT_VENDOR_RAMDISK = carrier.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = carrier.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = carrier.DEFAULT_MAGISKBOOT
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p234/candidate-a")

BOOT_SIZE = layout.BOOT_SIZE
KERNEL_START = layout.KERNEL_START
KERNEL_END = layout.KERNEL_END


class BuildError(ValueError):
    pass


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _read_json(path: Path, label: str, maximum: int = 16 * 1024 * 1024):
    data = candidate_contract.stable_read(path, label, maximum)
    try:
        value = json.loads(data.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"{label} is not valid ASCII JSON") from exc
    if not isinstance(value, dict):
        raise BuildError(f"{label} root is not an object")
    return value, receipt(data)


def verify_repro_result(
    result_path: Path,
    image_receipt: dict[str, Any],
    exact_contract: dict[str, Any],
) -> dict[str, Any]:
    value, result_receipt = _read_json(result_path, "P2.34 build reproducibility result")
    if (
        value.get("schema") != repro.SCHEMA
        or value.get("target") != TARGET
        or value.get("verdict") != repro.VERDICT
        or value.get("candidate_contract") != exact_contract
        or value.get("linked_audit", {}).get("verified") is not True
        or not isinstance(value.get("byte_identical_artifacts"), dict)
        or set(value["byte_identical_artifacts"])
        != set(repro.ARTIFACT_LIMITS) - {"build-result.json"}
        or any(item is not True for item in value["byte_identical_artifacts"].values())
    ):
        raise BuildError("P2.34 build reproducibility result is not accepted")
    expected_image = value.get("build_a", {}).get("artifacts", {}).get("Image")
    if expected_image != image_receipt:
        raise BuildError("P2.34 supplied Image differs from reproducibility closure")
    return {
        "result": result_receipt,
        "verdict": value["verdict"],
        "image": image_receipt,
        "two_clean_builds_byte_identical": True,
        "linked_audit_verified": True,
    }


def verify_userspace(
    directory: Path, exact_contract: dict[str, Any]
) -> tuple[dict[str, bytes], dict[str, Any]]:
    if directory.is_symlink() or not directory.is_dir():
        raise BuildError("P2.34 userspace directory missing or indirect")
    expected = {"init", "s22-e1-child", "userspace-result.json"}
    if {path.name for path in directory.iterdir()} != expected:
        raise BuildError("P2.34 userspace inventory mismatch")
    value, result_receipt = _read_json(
        directory / "userspace-result.json", "P2.34 userspace result"
    )
    if (
        value.get("schema") != userspace.SCHEMA
        or value.get("target") != TARGET
        or value.get("verdict")
        != userspace.verdict_for_profile(
            exact_contract["profile"],
            exact_contract.get("source_contract_id"),
        )
        or value.get("candidate_contract") != exact_contract
        or value.get("run_id") != exact_contract["run_id"]
        or value.get("profile") != exact_contract["profile"]
        or value.get("two_build_byte_identical") is not True
    ):
        raise BuildError("P2.34 userspace result does not bind the candidate")
    paths = {"init": directory / "init", "child": directory / "s22-e1-child"}
    data = {
        name: candidate_contract.stable_read(path, f"P2.34 {name}", 1024 * 1024)
        for name, path in paths.items()
    }
    for name in ("init", "child"):
        if value.get("outputs", {}).get(name, {}).get("size") != len(data[name]) or value.get(
            "outputs", {}
        ).get(name, {}).get("sha256") != hashlib.sha256(data[name]).hexdigest():
            raise BuildError(f"P2.34 userspace receipt mismatch: {name}")
    if any((path.stat().st_mode & 0o777) != 0o755 for path in paths.values()):
        raise BuildError("P2.34 userspace host mode mismatch")
    return data, {
        "result": result_receipt,
        "init": receipt(data["init"]),
        "child": receipt(data["child"]),
        "two_build_byte_identical": True,
        "verified": True,
    }


def replace_kernel(carrier_boot: bytes, image: bytes) -> tuple[bytes, dict[str, Any]]:
    if len(carrier_boot) != BOOT_SIZE or len(image) != KERNEL_END - KERNEL_START:
        raise BuildError("P2.34 fixed boot layout size mismatch")
    candidate = boot_slice.replace_fixed_interval(
        carrier_boot, image, KERNEL_START, KERNEL_END
    )
    parsed_carrier = boot_verify.parse_boot_v4(carrier_boot)
    parsed_candidate = boot_verify.parse_boot_v4(candidate)
    if parsed_carrier.header != parsed_candidate.header:
        raise BuildError("P2.34 kernel replacement changed the boot header")
    if parsed_carrier.ramdisk != parsed_candidate.ramdisk:
        raise BuildError("P2.34 kernel replacement changed the ramdisk")
    if parsed_candidate.kernel != image:
        raise BuildError("P2.34 candidate parser did not recover the exact Image")
    changes = boot_slice.diff_outside_interval(
        carrier_boot, candidate, KERNEL_START, KERNEL_END
    )
    return candidate, {
        **changes,
        "kernel_interval": [KERNEL_START, KERNEL_END],
        "header_preserved": True,
        "ramdisk_preserved": True,
        "kernel_exact_image": True,
    }


def build_candidate(args: argparse.Namespace) -> dict[str, Any]:
    root = candidate_contract.intent.repo_root()
    output = candidate_contract.intent.resolve(root, args.out)
    if output.exists() or output.is_symlink():
        raise BuildError(f"P2.34 candidate output already exists: {output}")
    exact_contract = candidate_contract.verify(
        root,
        candidate_contract.intent.resolve(root, args.source),
        candidate_contract.intent.resolve(root, args.intent),
        candidate_contract.intent.resolve(root, args.patch),
    )
    carrier.r4w1b.validate_patch_vbmeta_flag()
    base_boot = carrier.read_exact_file(
        candidate_contract.intent.resolve(root, args.base_boot),
        BOOT_SIZE,
        carrier.EXPECTED_BASE_BOOT_SHA256,
        "known Magisk base boot",
    )
    lz4 = carrier.read_exact_file(
        candidate_contract.intent.resolve(root, args.lz4),
        carrier.r4w1b.LZ4_SIZE,
        carrier.r4w1b.LZ4_SHA256,
        "pinned lz4",
    )
    magiskboot = carrier.read_exact_file(
        candidate_contract.intent.resolve(root, args.magiskboot),
        carrier.MAGISKBOOT_SIZE,
        carrier.MAGISKBOOT_SHA256,
        "pinned magiskboot",
    )
    image_receipt, image = carrier.read_stable_file(
        candidate_contract.intent.resolve(root, args.image),
        "P2.34 Image",
        KERNEL_END - KERNEL_START,
    )
    if image_receipt["size"] != KERNEL_END - KERNEL_START:
        raise BuildError("P2.34 Image has the wrong fixed-slot size")
    boot_verify.parse_arm64_header(image)
    kernel_closure = verify_repro_result(
        candidate_contract.intent.resolve(root, args.repro_result),
        image_receipt,
        exact_contract,
    )
    userspace_data, userspace_closure = verify_userspace(
        candidate_contract.intent.resolve(root, args.userspace), exact_contract
    )
    module_closure = None
    if exact_contract["profile"] == "E1B":
        with tempfile.TemporaryDirectory(prefix="s22-p239-module-closure-") as name:
            module_closure = carrier.derive_and_verify_module_closure(
                candidate_contract.intent.resolve(
                    root, getattr(args, "vendor_ramdisk", DEFAULT_VENDOR_RAMDISK)
                ),
                candidate_contract.intent.resolve(root, args.lz4),
                Path(name),
            )
    elif exact_contract["profile"] == "E2":
        closure_api = p245_e2_closure.select(
            exact_contract.get("source_contract_id")
        )
        plan_header = None
        if exact_contract.get("source_contract_id") is not None:
            plan_header = (
                candidate_contract.intent.resolve(root, args.intent).parent
                / "materialized-sources"
                / candidate_contract.intent.p245.MATERIALIZED_FILENAMES[
                    "plan_header"
                ]
            )
        module_closure = closure_api.derive_module_closure(
            root,
            candidate_contract.intent.resolve(
                root, getattr(args, "vendor_ramdisk", DEFAULT_VENDOR_RAMDISK)
            ),
            candidate_contract.intent.resolve(root, args.lz4),
            plan_header=plan_header,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output.name}.", dir=output.parent
    ) as temporary:
        staging = Path(temporary)
        work = staging / "work"
        nochange = staging / "nochange"
        final_unpack = staging / "final-unpack"
        audit = staging / "audit"
        for directory in (work, nochange, final_unpack, audit):
            directory.mkdir()
        pinned_base = audit / "base.boot.img"
        pinned_lz4 = audit / "lz4"
        pinned_magiskboot = audit / "magiskboot"
        init_path = audit / "init"
        child_path = audit / "s22-e1-child"
        carrier.stage_file(pinned_base, base_boot)
        carrier.stage_file(pinned_lz4, lz4, executable=True)
        carrier.stage_file(pinned_magiskboot, magiskboot, executable=True)
        carrier.stage_file(init_path, userspace_data["init"], executable=True)
        carrier.stage_file(child_path, userspace_data["child"], executable=True)

        carrier.run_in_dir(
            [pinned_magiskboot, "unpack", "-h", pinned_base],
            nochange,
            "P2.34 no-change unpack",
        )
        nochange_boot = audit / "boot.nochange.img"
        carrier.run_in_dir(
            [pinned_magiskboot, "repack", pinned_base, nochange_boot],
            nochange,
            "P2.34 no-change repack",
        )
        if nochange_boot.read_bytes() != base_boot:
            raise BuildError("P2.34 magiskboot no-change repack differs")

        carrier.run_in_dir(
            [pinned_magiskboot, "unpack", "-h", pinned_base],
            work,
            "P2.34 unpack base boot",
        )
        ramdisk = work / "ramdisk.cpio"
        original_kernel = (work / "kernel").read_bytes()
        original_init = audit / "init.original"
        carrier.run_in_dir(
            [pinned_magiskboot, "cpio", ramdisk, f"extract init {original_init}"],
            work,
            "P2.34 extract original init",
        )
        if carrier.sha256_file(original_init) != carrier.EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
            raise BuildError("P2.34 original Magisk init pin mismatch")
        child_exists = carrier.run(
            [pinned_magiskboot, "cpio", ramdisk, "exists s22-e1-child"],
            cwd=work,
        )
        if child_exists.returncode != 1:
            raise BuildError(
                f"P2.34 base child absence check failed rc={child_exists.returncode}"
            )
        carrier.run_in_dir(
            [pinned_magiskboot, "cpio", ramdisk, f"add 750 init {init_path}"],
            work,
            "P2.34 replace init",
        )
        carrier.run_in_dir(
            [
                pinned_magiskboot,
                "cpio",
                ramdisk,
                f"add 750 s22-e1-child {child_path}",
            ],
            work,
            "P2.34 add child",
        )
        carrier_path = audit / "carrier.boot.img"
        carrier.run_in_dir(
            [pinned_magiskboot, "repack", pinned_base, carrier_path],
            work,
            "P2.34 repack E1 carrier",
        )
        carrier_boot = carrier_path.read_bytes()
        if len(carrier_boot) != BOOT_SIZE:
            raise BuildError("P2.34 E1 carrier size mismatch")
        if carrier_boot[KERNEL_START:KERNEL_END] != original_kernel:
            raise BuildError("P2.34 ramdisk repack changed the carrier kernel")
        candidate, construction = replace_kernel(carrier_boot, image)
        boot_path = staging / "boot.img"
        carrier.stage_file(boot_path, candidate)

        carrier.run_in_dir(
            [pinned_magiskboot, "unpack", "-h", boot_path],
            final_unpack,
            "P2.34 unpack final candidate",
        )
        final_init = audit / "init.final"
        final_child = audit / "child.final"
        final_ramdisk = final_unpack / "ramdisk.cpio"
        carrier.run_in_dir(
            [pinned_magiskboot, "cpio", final_ramdisk, f"extract init {final_init}"],
            final_unpack,
            "P2.34 extract final init",
        )
        carrier.run_in_dir(
            [
                pinned_magiskboot,
                "cpio",
                final_ramdisk,
                f"extract s22-e1-child {final_child}",
            ],
            final_unpack,
            "P2.34 extract final child",
        )
        if (
            final_init.read_bytes() != userspace_data["init"]
            or final_child.read_bytes() != userspace_data["child"]
            or (final_unpack / "kernel").read_bytes() != image
        ):
            raise BuildError("P2.34 final candidate content mismatch")

        frame_path = staging / "boot.img.lz4"
        carrier.require_ok(
            carrier.run(
                [
                    pinned_lz4,
                    "--content-size",
                    "-B6",
                    "-f",
                    "-q",
                    boot_path,
                    frame_path,
                ]
            ),
            "compress P2.34 boot",
        )
        roundtrip = audit / "roundtrip.img"
        carrier.require_ok(
            carrier.run([pinned_lz4, "-d", "-f", "-q", frame_path, roundtrip]),
            "decompress P2.34 boot",
        )
        if roundtrip.read_bytes() != candidate:
            raise BuildError("P2.34 LZ4 roundtrip mismatch")
        odin = staging / "odin4"
        odin.mkdir()
        ap_path = odin / "AP.tar.md5"
        ap_structure = boot_slice.write_deterministic_boot_ap(
            frame_path.read_bytes(), ap_path
        )
        if ap_structure.get("members") != ["boot.img.lz4"]:
            raise BuildError("P2.34 AP is not exactly boot-only")
        shutil.rmtree(work)
        shutil.rmtree(nochange)
        shutil.rmtree(final_unpack)
        shutil.rmtree(audit)
        safety = {
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
            "no_block_write": True,
            "no_reboot_syscall": True,
        }
        if exact_contract["profile"] == "E2":
            safety.update(
                {
                    "no_userspace_sysfs_or_configfs_write": True,
                    "usb_scope": "active-module-init-probe-and-read-only-bind-gates",
                    "module_init_probe_authority": "active-live-unproved",
                }
            )
        else:
            safety["no_usb_or_configfs"] = True
        result = {
            "schema": SCHEMA,
            "target": TARGET,
            "verdict": VERDICT,
            "candidate_contract": exact_contract,
            "kernel_closure": kernel_closure,
            "userspace_closure": userspace_closure,
            "construction": {
                **construction,
                "magiskboot_nochange_byte_identical": True,
                "base_child_absent": True,
                "ramdisk_init_mode": "0750",
                "ramdisk_child_mode": "0750",
                "patch_vbmeta_flag": False,
            },
            "outputs": {
                "boot_img": receipt(candidate),
                "boot_img_lz4": receipt(frame_path.read_bytes()),
                "ap_tar_md5": receipt(ap_path.read_bytes()),
                "ap_structure": ap_structure,
            },
            "manifest_created": False,
            "safety": safety,
        }
        if module_closure is not None:
            result["module_closure"] = module_closure
            result["construction"].update(
                {
                    "module_binaries_injected": 0,
                    "vendor_ramdisk_modules_reused": True,
                }
            )
        (staging / "artifact-result.json").write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="ascii",
        )
        os.replace(staging, output)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=candidate_contract.DEFAULT_SOURCE)
    parser.add_argument("--intent", type=Path, default=candidate_contract.DEFAULT_INTENT)
    parser.add_argument("--patch", type=Path, default=candidate_contract.DEFAULT_PATCH)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--repro-result", type=Path, default=DEFAULT_REPRO_RESULT)
    parser.add_argument("--userspace", type=Path, default=DEFAULT_USERSPACE)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument(
        "--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK
    )
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        result = build_candidate(parse_args(argv))
    except (
        BuildError,
        candidate_contract.ContractError,
        candidate_contract.intent.IntentError,
        e2_closure.ClosureError,
        carrier.BuildError,
        boot_slice.BootSliceError,
        boot_verify.BootVerifyError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": result["verdict"],
                "boot_sha256": result["outputs"]["boot_img"]["sha256"],
                "ap_sha256": result["outputs"]["ap_tar_md5"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
