#!/usr/bin/env python3
"""Build one host-only FYG8 R4W1-E E1 offline candidate contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_r4w1b_candidate as slice_engine  # noqa: E402
import build_s22plus_fyg8_r4w1c_watchdog_carrier as carrier_engine  # noqa: E402
import s22plus_boot_slice as boot_slice  # noqa: E402
import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_r4w1e_build_artifact_contract as build_artifact  # noqa: E402
import s22plus_fyg8_r4w1e_checkpoint_contract as checkpoint  # noqa: E402
import s22plus_fyg8_r4w1e_e1_host_contract as e1  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1e_e1_candidate_build_v1"
RUN_MANIFEST_SCHEMA = "s22plus_fyg8_r4w1e_e1_run_manifest_v1"
VERDICT = "PASS_R4W1E_E1_CANDIDATE_BUILT_HOST_ONLY"
TARGET = checkpoint.TARGET
RUNG = "R4W1-E/E1"
BOOT_SIZE = slice_engine.BOOT_SIZE
KERNEL_START = slice_engine.KERNEL_START
KERNEL_END = slice_engine.KERNEL_END
KERNEL_SIZE = slice_engine.KERNEL_SIZE
HEADER_END = slice_engine.HEADER_END
GAP_START = slice_engine.GAP_START
GAP_END = slice_engine.GAP_END
SOURCE_CLANG_LINK = (
    "kernel_platform/prebuilts-master/clang/host/linux-x86/clang-r416183b"
)

DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e_e1_candidate/reproduction-a"
)
DEFAULT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e_candidate_inputs/Image"
)
DEFAULT_KERNEL_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e_candidate_inputs/"
    "kernel-build-result.json"
)
DEFAULT_VENDOR_RAMDISK = carrier_engine.DEFAULT_VENDOR_RAMDISK
DEFAULT_BASE_BOOT = carrier_engine.DEFAULT_BASE_BOOT
DEFAULT_LZ4 = carrier_engine.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = carrier_engine.DEFAULT_MAGISKBOOT


class BuildError(ValueError):
    """Fail-closed offline candidate construction error."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def exact_source_data(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    paths = {
        "runtime": root / e1.DEFAULT_RUNTIME,
        "child": root / e1.DEFAULT_CHILD,
        "client": root / e1.DEFAULT_CLIENT,
        "header": root / e1.DEFAULT_HEADER,
        "inventory": root / e1.DEFAULT_INVENTORY,
    }
    data: dict[str, bytes] = {}
    rows: dict[str, Any] = {}
    for name, path in paths.items():
        value = e1.read_direct(
            path,
            f"E1 {name}",
            16_777_216 if name == "inventory" else e1.SOURCE_MAX_SIZE,
        )
        actual = hashlib.sha256(value).hexdigest()
        if actual != e1.EXPECTED_SOURCE_SHA256[name]:
            raise BuildError(f"E1 {name} source identity mismatch: {actual}")
        data[name] = value
        rows[name] = receipt(value)
    return data, rows


def verify_kernel_build(encoded: bytes, image: bytes) -> dict[str, Any]:
    image_receipt = receipt(image)
    result_receipt = receipt(encoded)
    if not build_artifact.matches(
        size=image_receipt["size"],
        sha256=image_receipt["sha256"],
        expected_size=build_artifact.IMAGE_SIZE,
        expected_sha256=build_artifact.IMAGE_SHA256,
    ):
        raise BuildError("R4W1-E Image does not match the immutable P2.9 build artifact")
    if not build_artifact.matches(
        size=result_receipt["size"],
        sha256=result_receipt["sha256"],
        expected_size=build_artifact.KERNEL_BUILD_RESULT_SIZE,
        expected_sha256=build_artifact.KERNEL_BUILD_RESULT_SHA256,
    ):
        raise BuildError(
            "R4W1-E kernel result does not match the immutable P2.9 build artifact"
        )
    try:
        result = json.loads(encoded.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BuildError("invalid R4W1-E kernel build result") from exc
    if not isinstance(result, dict):
        raise BuildError("R4W1-E kernel build result is not an object")
    required = {
        "schema": "s22plus_fyg8_r4w1e_build_v1",
        "target": TARGET,
        "mode": "build",
        "returncode": 0,
        "r4w1e_build_pass": True,
    }
    for name, expected in required.items():
        if result.get(name) != expected:
            raise BuildError(f"kernel build result {name} mismatch")
    gate_names = (
        "source_delta",
        "source_symlink_control_runtime",
        "output_gate",
        "module_gate",
        "kernel_banner_gate",
        "witness_output_gate",
        "sec_log_buf_timing_gate",
        "exclusive_output_root",
    )
    for name in gate_names:
        gate = result.get(name)
        if not isinstance(gate, dict) or gate.get("verified") is not True:
            raise BuildError(f"kernel build gate not verified: {name}")
    source_delta = result["source_delta"]
    if (
        source_delta.get("restored") is not True
        or source_delta.get("patch_sha256") != checkpoint.PATCH_SHA256
    ):
        raise BuildError("kernel build patch/restoration binding mismatch")
    source_links = result["source_symlink_control_runtime"]
    link_rows = source_links.get("links")
    if not isinstance(link_rows, list) or any(
        not isinstance(row, dict) for row in link_rows
    ):
        raise BuildError("kernel build source-link rows malformed")
    clang_rows = [
        row
        for row in link_rows
        if row.get("relative_path") == SOURCE_CLANG_LINK
    ]
    if (
        source_links.get("runtime_override_count") != 1
        or source_links.get("qualified_external_symlink_count") != 1
        or len(clang_rows) != 1
        or clang_rows[0].get("provenance")
        != "separately-pinned-toolchain-link"
        or clang_rows[0].get("runtime_override_applied") is not True
        or clang_rows[0].get("target_mutated_by_build") is not False
        or clang_rows[0].get("post_build_target")
        != clang_rows[0].get("runtime_target")
        or clang_rows[0].get("restored") is not True
        or clang_rows[0].get("path_identity_verified") is not True
    ):
        raise BuildError("kernel build clang-link runtime binding mismatch")
    contract = result.get("r4w1e_checkpoint_contract")
    if not isinstance(contract, dict):
        raise BuildError("kernel build checkpoint contract malformed")
    if contract.get("verdict") != checkpoint.VERDICT:
        raise BuildError("kernel build checkpoint contract mismatch")
    witness = result["witness_output_gate"]
    expected_witness = {
        "image_size": KERNEL_SIZE,
        "image_proof_count": 1,
        "vmlinux_proof_count": 1,
        "image_proof_family_count": 1,
        "vmlinux_proof_family_count": 1,
        "config_enable_count": 1,
        "fips_enable_count": 1,
    }
    for name, expected in expected_witness.items():
        if witness.get(name) != expected:
            raise BuildError(f"kernel witness output mismatch: {name}")
    historical_configs = witness.get("historical_config_enable_counts")
    if not isinstance(historical_configs, dict) or any(historical_configs.values()):
        raise BuildError("historical kernel witness config remains enabled")
    output_rows = result.get("outputs")
    if not isinstance(output_rows, list) or any(
        not isinstance(row, dict) for row in output_rows
    ):
        raise BuildError("kernel build outputs malformed")
    image_rows = [row for row in output_rows if row.get("name") == "Image"]
    if len(image_rows) != 1 or any(
        image_rows[0].get(name) != image_receipt[name] for name in ("size", "sha256")
    ):
        raise BuildError("kernel build result does not bind the supplied Image")
    safety = result.get("safety")
    if not isinstance(safety, dict):
        raise BuildError("kernel build safety contract malformed")
    for name, expected in {
        "host_only": True,
        "device_contact": False,
        "flash": False,
        "partition_write": False,
        "live_authorized": False,
        "packaging_outputs_promoted": False,
    }.items():
        if safety.get(name) is not expected:
            raise BuildError(f"kernel build safety mismatch: {name}")
    return {
        "schema": result["schema"],
        "returncode": result["returncode"],
        "patch_sha256": source_delta["patch_sha256"],
        "image": image_receipt,
        "build_result": result_receipt,
        "artifact_contract_schema": build_artifact.SCHEMA,
        "clean_full_lto_build": True,
        "source_restored": True,
        "verified": True,
    }


def classify_image(image: bytes) -> dict[str, Any]:
    if len(image) != KERNEL_SIZE:
        raise BuildError(f"R4W1-E Image size mismatch: {len(image)}")
    boot_verify.parse_arm64_header(image)
    exact = image.count(checkpoint.ENTRY_PROOF)
    family = image.count(checkpoint.ENTRY_FAMILY)
    historical = {
        marker.decode("ascii"): image.count(marker)
        for marker in (b"[[S22P1D|", b"[[S22R4W1B|", b"[[S22R4W1|")
    }
    if exact != 1 or family != 1 or any(historical.values()):
        raise BuildError("R4W1-E Image marker cardinality mismatch")
    return {
        "size": len(image),
        "sha256": hashlib.sha256(image).hexdigest(),
        "entry_proof_count": exact,
        "entry_family_count": family,
        "historical_family_counts": historical,
        "verified": True,
    }


def tool_receipts(tools: dict[str, str]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for name, path_text in sorted(tools.items()):
        path = Path(path_text).resolve()
        data = e1.read_direct(path, f"resolved host tool {name}", 64 * 1024 * 1024)
        rows[name] = {"resolved_name": path.name, **receipt(data)}
    return rows


def derive_run_manifest(
    *,
    nonce: bytes,
    image: dict[str, Any],
    kernel_result: dict[str, Any],
    base_boot: dict[str, Any],
    vendor_ramdisk: dict[str, Any],
    lz4: dict[str, Any],
    magiskboot: dict[str, Any],
    sources: dict[str, Any],
    tools: dict[str, Any],
) -> tuple[dict[str, Any], bytes, bytes]:
    if len(nonce) != 16:
        raise BuildError("run manifest nonce must be exactly 16 bytes")
    manifest = {
        "schema": RUN_MANIFEST_SCHEMA,
        "target": TARGET,
        "profile": "E1",
        "nonce": nonce.hex(),
        "checkpoint_patch_sha256": checkpoint.PATCH_SHA256,
        "checkpoint_carrier_sha256": checkpoint.CARRIER_SHA256,
        "inputs": {
            "image": image,
            "kernel_build_result": kernel_result,
            "base_boot": base_boot,
            "vendor_ramdisk": vendor_ramdisk,
            "lz4": lz4,
            "magiskboot": magiskboot,
            "sources": sources,
            "host_tools": tools,
            "runtime_contract": {
                "schema": e1.SCHEMA,
                "compile_flags": list(e1.COMPILE_FLAGS),
                "child_token_hex": e1.CHILD_TOKEN.hex(),
                "child_exit": e1.CHILD_EXIT,
                "stage_values": dict(sorted(e1.STAGE_VALUES.items())),
                "runtime_syscalls": dict(sorted(e1.RUNTIME_SYSCALLS.items())),
                "client_syscalls": dict(sorted(e1.CLIENT_SYSCALLS.items())),
                "child_syscalls": dict(sorted(e1.CHILD_SYSCALLS.items())),
            },
            "modules": [
                {
                    "file": file_name,
                    "runtime": runtime,
                    "size": size,
                    "sha256": digest,
                }
                for file_name, runtime, size, digest in e1.MODULE_SPECS
            ],
        },
    }
    encoded = canonical_json(manifest)
    digest = hashlib.sha256(encoded).digest()
    run_id = digest[:16]
    if run_id == bytes(16) or run_id == checkpoint.MODEL_RUN_IDS["E1"]:
        raise BuildError("derived run ID is zero or the P2.7 host-model ID")
    return manifest, encoded, run_id


def replace_kernel(carrier: bytes, image: bytes) -> tuple[bytes, dict[str, Any]]:
    candidate = boot_slice.replace_fixed_interval(
        carrier, image, KERNEL_START, KERNEL_END
    )
    if candidate[:HEADER_END] != carrier[:HEADER_END]:
        raise BuildError("candidate changed the Android boot header")
    if candidate[GAP_START:GAP_END] != carrier[GAP_START:GAP_END]:
        raise BuildError("candidate changed the fixed alignment gap")
    if candidate[KERNEL_END:] != carrier[KERNEL_END:]:
        raise BuildError("candidate changed opaque post-kernel bytes")
    parsed = boot_verify.parse_boot_v4(candidate)
    if parsed.kernel != image:
        raise BuildError("candidate parser did not recover the exact Image")
    return candidate, {
        "kernel_interval": [KERNEL_START, KERNEL_END],
        "android_header_preserved": True,
        "alignment_gap_preserved": True,
        "opaque_post_kernel_preserved": True,
        "kernel_exact_image": True,
    }


def parse_nonce(value: str | None) -> bytes:
    if value is None:
        return secrets.token_bytes(16)
    if len(value) != 32:
        raise BuildError("--nonce-hex must contain exactly 32 hexadecimal digits")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise BuildError("--nonce-hex is not hexadecimal") from exc


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = carrier_engine.repo_root()
    output = carrier_engine.resolve(root, args.out)
    if output.exists():
        raise BuildError(f"output path already exists: {output}")
    slice_engine.validate_patch_vbmeta_flag()

    base_boot = carrier_engine.read_exact_file(
        carrier_engine.resolve(root, args.base_boot),
        BOOT_SIZE,
        carrier_engine.EXPECTED_BASE_BOOT_SHA256,
        "known Magisk base boot",
    )
    vendor_ramdisk = carrier_engine.read_exact_file(
        carrier_engine.resolve(root, args.vendor_ramdisk),
        carrier_engine.VENDOR_RAMDISK_SIZE,
        carrier_engine.VENDOR_RAMDISK_SHA256,
        "FYG8 vendor ramdisk",
    )
    lz4 = carrier_engine.read_exact_file(
        carrier_engine.resolve(root, args.lz4),
        slice_engine.LZ4_SIZE,
        slice_engine.LZ4_SHA256,
        "pinned lz4",
    )
    magiskboot = carrier_engine.read_exact_file(
        carrier_engine.resolve(root, args.magiskboot),
        carrier_engine.MAGISKBOOT_SIZE,
        carrier_engine.MAGISKBOOT_SHA256,
        "pinned magiskboot",
    )
    _, image = carrier_engine.read_stable_file(
        carrier_engine.resolve(root, args.image),
        "R4W1-E Image",
        KERNEL_SIZE,
    )
    image_info = classify_image(image)
    _, kernel_result_bytes = carrier_engine.read_stable_file(
        carrier_engine.resolve(root, args.kernel_result),
        "R4W1-E kernel build result",
        16 * 1024 * 1024,
    )
    kernel_result = verify_kernel_build(kernel_result_bytes, image)

    source_data, source_rows = exact_source_data(root)
    host_contract = e1.run_check(
        root / e1.DEFAULT_RUNTIME,
        root / e1.DEFAULT_CHILD,
        root / e1.DEFAULT_CLIENT,
        root / e1.DEFAULT_HEADER,
        root / e1.DEFAULT_INVENTORY,
    )
    if host_contract.get("verdict") != e1.VERDICT:
        raise BuildError("E1 host contract did not pass")
    tools = e1.require_tools()
    tool_rows = tool_receipts(tools)
    run_manifest, run_manifest_bytes, run_id = derive_run_manifest(
        nonce=parse_nonce(args.nonce_hex),
        image=image_info,
        kernel_result={**receipt(kernel_result_bytes), **kernel_result},
        base_boot=receipt(base_boot),
        vendor_ramdisk=receipt(vendor_ramdisk),
        lz4=receipt(lz4),
        magiskboot=receipt(magiskboot),
        sources=source_rows,
        tools=tool_rows,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output.name}.", dir=output.parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="s22-r4w1e-e1-pinned-"
    ) as input_temporary:
        staging = Path(temporary)
        pinned = Path(input_temporary)
        build_dir = staging / "build"
        work_dir = staging / "magiskboot-work"
        nochange_dir = staging / "nochange-probe"
        unpack_dir = staging / "candidate-unpack"
        for directory in (build_dir, work_dir, nochange_dir, unpack_dir):
            directory.mkdir()
        pinned_base = pinned / "base.boot.img"
        pinned_vendor = pinned / "vendor_ramdisk00"
        pinned_lz4 = pinned / "lz4"
        pinned_magiskboot = pinned / "magiskboot"
        carrier_engine.stage_file(pinned_base, base_boot)
        carrier_engine.stage_file(pinned_vendor, vendor_ramdisk)
        carrier_engine.stage_file(pinned_lz4, lz4, executable=True)
        carrier_engine.stage_file(pinned_magiskboot, magiskboot, executable=True)

        closure = carrier_engine.derive_and_verify_module_closure(
            pinned_vendor, pinned_lz4, build_dir
        )
        with e1.without_compiler_environment():
            compiled = e1.compile_one(
                build_dir,
                source_data["runtime"],
                source_data["child"],
                source_data["client"],
                source_data["header"],
                run_id,
                tools,
            )
        init_data = compiled["init"].pop("data")
        child_data = compiled["child"].pop("data")
        init_path = build_dir / "init"
        child_path = build_dir / "s22-e1-child"
        if init_path.read_bytes() != init_data or child_path.read_bytes() != child_data:
            raise BuildError("compiled E1 artifact changed after audit")

        carrier_engine.run_in_dir(
            [pinned_magiskboot, "unpack", "-h", pinned_base],
            nochange_dir,
            "R4W1-E no-change unpack",
        )
        nochange_boot = build_dir / "boot.nochange.img"
        carrier_engine.run_in_dir(
            [pinned_magiskboot, "repack", pinned_base, nochange_boot],
            nochange_dir,
            "R4W1-E no-change repack",
        )
        if nochange_boot.read_bytes() != base_boot:
            raise BuildError("magiskboot no-change repack is not byte-identical")

        carrier_engine.run_in_dir(
            [pinned_magiskboot, "unpack", "-h", pinned_base],
            work_dir,
            "R4W1-E unpack base boot",
        )
        ramdisk = work_dir / "ramdisk.cpio"
        original_kernel = (work_dir / "kernel").read_bytes()
        original_init = build_dir / "init.magisk.original"
        carrier_engine.run_in_dir(
            [pinned_magiskboot, "cpio", ramdisk, f"extract init {original_init}"],
            work_dir,
            "R4W1-E extract original init",
        )
        if carrier_engine.sha256_file(original_init) != carrier_engine.EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
            raise BuildError("original Magisk /init pin mismatch")
        shutil.copy2(ramdisk, build_dir / "ramdisk.before.cpio")
        carrier_engine.run_in_dir(
            [pinned_magiskboot, "cpio", ramdisk, f"add 750 init {init_path}"],
            work_dir,
            "R4W1-E replace /init",
        )
        carrier_engine.run_in_dir(
            [
                pinned_magiskboot,
                "cpio",
                ramdisk,
                f"add 750 s22-e1-child {child_path}",
            ],
            work_dir,
            "R4W1-E add child",
        )
        replaced_init = build_dir / "init.replaced"
        replaced_child = build_dir / "s22-e1-child.replaced"
        carrier_engine.run_in_dir(
            [pinned_magiskboot, "cpio", ramdisk, f"extract init {replaced_init}"],
            work_dir,
            "R4W1-E extract replaced init",
        )
        carrier_engine.run_in_dir(
            [
                pinned_magiskboot,
                "cpio",
                ramdisk,
                f"extract s22-e1-child {replaced_child}",
            ],
            work_dir,
            "R4W1-E extract replaced child",
        )
        if replaced_init.read_bytes() != init_data or replaced_child.read_bytes() != child_data:
            raise BuildError("ramdisk E1 executables differ from audited binaries")
        shutil.copy2(ramdisk, build_dir / "ramdisk.after.cpio")

        carrier_path = staging / "carrier.boot.img"
        carrier_engine.run_in_dir(
            [pinned_magiskboot, "repack", pinned_base, carrier_path],
            work_dir,
            "R4W1-E repack E1 carrier",
        )
        carrier = carrier_path.read_bytes()
        if len(carrier) != BOOT_SIZE:
            raise BuildError("R4W1-E carrier size mismatch")
        if carrier[KERNEL_START:KERNEL_END] != original_kernel:
            raise BuildError("ramdisk-only carrier changed its kernel")

        candidate, construction = replace_kernel(carrier, image)
        candidate_path = staging / "boot.img"
        carrier_engine.stage_file(candidate_path, candidate)
        carrier_engine.run_in_dir(
            [pinned_magiskboot, "unpack", "-h", candidate_path],
            unpack_dir,
            "R4W1-E unpack final candidate",
        )
        final_init = build_dir / "init.final-candidate"
        final_child = build_dir / "s22-e1-child.final-candidate"
        final_ramdisk = unpack_dir / "ramdisk.cpio"
        carrier_engine.run_in_dir(
            [pinned_magiskboot, "cpio", final_ramdisk, f"extract init {final_init}"],
            unpack_dir,
            "R4W1-E extract final init",
        )
        carrier_engine.run_in_dir(
            [
                pinned_magiskboot,
                "cpio",
                final_ramdisk,
                f"extract s22-e1-child {final_child}",
            ],
            unpack_dir,
            "R4W1-E extract final child",
        )
        if final_init.read_bytes() != init_data or final_child.read_bytes() != child_data:
            raise BuildError("final candidate E1 executables changed")
        if (unpack_dir / "kernel").read_bytes() != image:
            raise BuildError("final candidate kernel differs from R4W1-E Image")

        frame_path = staging / "boot.img.lz4"
        carrier_engine.require_ok(
            carrier_engine.run(
                [
                    pinned_lz4,
                    "--content-size",
                    "-B6",
                    "-f",
                    "-q",
                    candidate_path,
                    frame_path,
                ]
            ),
            "compress R4W1-E E1 boot",
        )
        roundtrip = staging / ".roundtrip.img"
        carrier_engine.require_ok(
            carrier_engine.run([pinned_lz4, "-d", "-f", "-q", frame_path, roundtrip]),
            "decompress R4W1-E E1 boot",
        )
        if roundtrip.read_bytes() != candidate:
            raise BuildError("R4W1-E E1 LZ4 roundtrip mismatch")
        roundtrip.unlink()
        odin_dir = staging / "odin4"
        odin_dir.mkdir()
        ap_path = odin_dir / "AP.tar.md5"
        ap_structure = boot_slice.write_deterministic_boot_ap(
            frame_path.read_bytes(), ap_path
        )
        if ap_structure.get("members") != ["boot.img.lz4"]:
            raise BuildError("R4W1-E E1 AP is not exactly boot-only")

        run_manifest_path = staging / "run-manifest.json"
        run_manifest_path.write_bytes(
            json.dumps(run_manifest, indent=2, sort_keys=True, allow_nan=False).encode("ascii")
            + b"\n"
        )
        outputs = {
            "carrier_boot": receipt(carrier),
            "boot_img": receipt(candidate),
            "boot_img_lz4": receipt(frame_path.read_bytes()),
            "ap_tar_md5": receipt(ap_path.read_bytes()),
            "init": compiled["init"],
            "child": compiled["child"],
        }
        manifest = {
            "schema": SCHEMA,
            "target": TARGET,
            "rung": RUNG,
            "verdict": VERDICT,
            "run_binding": {
                "run_id": run_id.hex(),
                "canonical_manifest_size": len(run_manifest_bytes),
                "canonical_manifest_sha256": hashlib.sha256(run_manifest_bytes).hexdigest(),
                "derivation": "sha256(canonical-run-manifest)[:16]",
                "p2_7_model_id_reused": False,
            },
            "kernel_build": kernel_result,
            "host_contract": {
                "schema": host_contract["schema"],
                "verdict": host_contract["verdict"],
            },
            "module_closure": closure,
            "construction": {
                **construction,
                "magiskboot_nochange_byte_identical": True,
                "ramdisk_init_mode": "0750",
                "ramdisk_child_mode": "0750",
                "module_binaries_injected": 0,
                "vendor_ramdisk_modules_reused": True,
                "patch_vbmeta_flag": False,
            },
            "outputs": {**outputs, "ap_structure": ap_structure},
            "safety": {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "odin_transfer": False,
                "flash": False,
                "partition_write": False,
                "live_authorized": False,
                "boot_only_ap": True,
                "ap_members": ["boot.img.lz4"],
                "no_shell": True,
                "no_usb_or_configfs": True,
                "no_block_write": True,
                "no_reboot_syscall": True,
            },
            "blockers": [
                "independent offline candidate checker not yet passed",
                "single clean kernel build is not a two-build reproducibility proof",
                "no F1 preflight, approval, or live authority exists",
            ],
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="ascii",
        )
        os.replace(staging, output)
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--kernel-result", type=Path, default=DEFAULT_KERNEL_RESULT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--nonce-hex")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        manifest = build(parse_args(argv))
    except (
        BuildError,
        carrier_engine.BuildError,
        e1.CheckError,
        boot_slice.BootSliceError,
        boot_verify.BootVerifyError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": manifest["verdict"],
                "run_id": manifest["run_binding"]["run_id"],
                "boot_sha256": manifest["outputs"]["boot_img"]["sha256"],
                "ap_sha256": manifest["outputs"]["ap_tar_md5"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
