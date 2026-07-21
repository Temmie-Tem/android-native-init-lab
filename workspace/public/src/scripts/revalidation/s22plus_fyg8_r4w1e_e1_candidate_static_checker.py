#!/usr/bin/env python3
"""Independently audit one host-only FYG8 R4W1-E E1 offline candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_r4w1c_watchdog_carrier as carrier_inputs  # noqa: E402
import s22plus_boot_verify as verify  # noqa: E402
import s22plus_fyg8_r4w1b_candidate_static_checker as base_static  # noqa: E402
import s22plus_fyg8_r4w1e_build_artifact_contract as build_artifact  # noqa: E402
import s22plus_fyg8_r4w1e_checkpoint_contract as checkpoint  # noqa: E402
import s22plus_fyg8_r4w1e_e1_host_contract as e1  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1e_e1_candidate_static_checker_v1"
VERDICT = "PASS_R4W1E_E1_OFFLINE_CANDIDATE_STATIC_CONTRACT"
CANDIDATE_SCHEMA = "s22plus_fyg8_r4w1e_e1_candidate_build_v1"
RUN_MANIFEST_SCHEMA = "s22plus_fyg8_r4w1e_e1_run_manifest_v1"
CANDIDATE_VERDICT = "PASS_R4W1E_E1_CANDIDATE_BUILT_HOST_ONLY"
TARGET = checkpoint.TARGET
RUNG = "R4W1-E/E1"
BOOT_SIZE = base_static.BOOT_SIZE
KERNEL_START = base_static.KERNEL_START
KERNEL_END = base_static.KERNEL_END
KERNEL_SIZE = base_static.KERNEL_SIZE
HEADER_END = base_static.HEADER_END
GAP_START = base_static.GAP_START
GAP_END = base_static.GAP_END
SOURCE_CLANG_LINK = (
    "kernel_platform/prebuilts-master/clang/host/linux-x86/clang-r416183b"
)

DEFAULT_CANDIDATE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e_e1_candidate/reproduction-a"
)
DEFAULT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e_candidate_inputs/Image"
)
DEFAULT_KERNEL_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e_candidate_inputs/"
    "kernel-build-result.json"
)
DEFAULT_VENDOR_BOOT = base_static.DEFAULT_VENDOR_BOOT
DEFAULT_VENDOR_RAMDISK = carrier_inputs.DEFAULT_VENDOR_RAMDISK
DEFAULT_BASE_BOOT = carrier_inputs.DEFAULT_BASE_BOOT
DEFAULT_LZ4 = base_static.DEFAULT_LZ4
DEFAULT_MAGISKBOOT = carrier_inputs.DEFAULT_MAGISKBOOT
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1e_e1_candidate/"
    "static-check-result.json"
)


class CheckError(ValueError):
    """Fail-closed offline candidate audit error."""


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise CheckError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def file_receipt(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    return verify.read_stable(path, label)


def require_receipt(value: Any, expected: dict[str, Any], label: str) -> None:
    if not isinstance(value, dict):
        raise CheckError(f"{label} receipt missing")
    for name in ("size", "sha256"):
        if value.get(name) != expected[name]:
            raise CheckError(f"{label} {name} mismatch")


def exact_source_data(root: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    paths = {
        "runtime": root / e1.DEFAULT_RUNTIME,
        "child": root / e1.DEFAULT_CHILD,
        "client": root / e1.DEFAULT_CLIENT,
        "header": root / e1.DEFAULT_HEADER,
        "inventory": root / e1.DEFAULT_INVENTORY,
    }
    data: dict[str, bytes] = {}
    receipts: dict[str, Any] = {}
    for name, path in paths.items():
        value = e1.read_direct(
            path,
            f"E1 {name}",
            16_777_216 if name == "inventory" else e1.SOURCE_MAX_SIZE,
        )
        actual = hashlib.sha256(value).hexdigest()
        if actual != e1.EXPECTED_SOURCE_SHA256[name]:
            raise CheckError(f"E1 {name} source identity mismatch: {actual}")
        data[name] = value
        receipts[name] = {"size": len(value), "sha256": actual}
    return data, receipts


def tool_receipts(tools: dict[str, str]) -> dict[str, Any]:
    receipts: dict[str, Any] = {}
    for name, path_text in sorted(tools.items()):
        path = Path(path_text).resolve()
        data = e1.read_direct(path, f"resolved host tool {name}", 64 * 1024 * 1024)
        receipts[name] = {
            "resolved_name": path.name,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    return receipts


def inspect_static_elf(data: bytes, label: str) -> dict[str, Any]:
    if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
        raise CheckError(f"{label} is not ELF64 little-endian")
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", data, 0)
    machine, entry, phoff = header[2], header[4], header[5]
    phentsize, phnum = header[9], header[10]
    if machine != 183 or phentsize != 56 or not entry:
        raise CheckError(f"{label} AArch64 ELF header mismatch")
    interpreter = False
    dynamic = False
    executable_stack = False
    mapped_entry = False
    for index in range(phnum):
        offset = phoff + index * phentsize
        if offset + phentsize > len(data):
            raise CheckError(f"{label} truncated program headers")
        p_type, p_flags, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _align = struct.unpack_from(
            "<IIQQQQQQ", data, offset
        )
        interpreter |= p_type == 3
        dynamic |= p_type == 2
        executable_stack |= p_type == 0x6474E551 and bool(p_flags & 1)
        if p_type == 1 and p_vaddr <= entry < p_vaddr + p_filesz:
            mapped_entry = p_offset + (entry - p_vaddr) < len(data)
    if interpreter or dynamic or executable_stack or not mapped_entry:
        raise CheckError(f"{label} static/noexec-stack contract mismatch")
    return {
        "machine": "AArch64",
        "entrypoint": entry,
        "interpreter": False,
        "dynamic": False,
        "executable_stack": False,
        "entrypoint_mapped": True,
        "verified": True,
    }


def verify_kernel_result(data: bytes, image_receipt: dict[str, Any]) -> dict[str, Any]:
    result_receipt = {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if not build_artifact.matches(
        size=image_receipt.get("size"),
        sha256=image_receipt.get("sha256"),
        expected_size=build_artifact.IMAGE_SIZE,
        expected_sha256=build_artifact.IMAGE_SHA256,
    ):
        raise CheckError("R4W1-E Image does not match the immutable P2.9 build artifact")
    if not build_artifact.matches(
        size=result_receipt["size"],
        sha256=result_receipt["sha256"],
        expected_size=build_artifact.KERNEL_BUILD_RESULT_SIZE,
        expected_sha256=build_artifact.KERNEL_BUILD_RESULT_SHA256,
    ):
        raise CheckError(
            "R4W1-E kernel result does not match the immutable P2.9 build artifact"
        )
    try:
        result = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("invalid R4W1-E kernel result") from exc
    if not isinstance(result, dict):
        raise CheckError("R4W1-E kernel result is not an object")
    required = {
        "schema": "s22plus_fyg8_r4w1e_build_v1",
        "target": TARGET,
        "mode": "build",
        "returncode": 0,
        "r4w1e_build_pass": True,
    }
    for name, expected in required.items():
        if result.get(name) != expected:
            raise CheckError(f"kernel result {name} mismatch")
    gates = (
        "source_delta",
        "source_symlink_control_runtime",
        "output_gate",
        "module_gate",
        "kernel_banner_gate",
        "witness_output_gate",
        "sec_log_buf_timing_gate",
        "exclusive_output_root",
    )
    for name in gates:
        gate = result.get(name)
        if not isinstance(gate, dict) or gate.get("verified") is not True:
            raise CheckError("kernel result contains an unverified build gate")
    source_delta = result["source_delta"]
    if (
        source_delta.get("patch_sha256") != checkpoint.PATCH_SHA256
        or source_delta.get("restored") is not True
    ):
        raise CheckError("kernel result patch/restoration mismatch")
    source_links = result["source_symlink_control_runtime"]
    link_rows = source_links.get("links")
    if not isinstance(link_rows, list) or any(
        not isinstance(row, dict) for row in link_rows
    ):
        raise CheckError("kernel result source-link rows malformed")
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
        raise CheckError("kernel result clang-link runtime binding mismatch")
    output_rows = result.get("outputs")
    if not isinstance(output_rows, list) or any(
        not isinstance(row, dict) for row in output_rows
    ):
        raise CheckError("kernel result outputs malformed")
    outputs = [row for row in output_rows if row.get("name") == "Image"]
    if len(outputs) != 1:
        raise CheckError("kernel result Image cardinality mismatch")
    require_receipt(outputs[0], image_receipt, "kernel result Image")
    witness = result["witness_output_gate"]
    for name, expected in {
        "image_proof_count": 1,
        "vmlinux_proof_count": 1,
        "image_proof_family_count": 1,
        "vmlinux_proof_family_count": 1,
        "config_enable_count": 1,
        "fips_enable_count": 1,
    }.items():
        if witness.get(name) != expected:
            raise CheckError(f"kernel witness mismatch: {name}")
    historical_configs = witness.get("historical_config_enable_counts")
    if not isinstance(historical_configs, dict) or any(historical_configs.values()):
        raise CheckError("historical witness config enabled")
    safety = result.get("safety")
    if not isinstance(safety, dict):
        raise CheckError("kernel result safety contract malformed")
    if any(
        safety.get(name) is not expected
        for name, expected in {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "packaging_outputs_promoted": False,
        }.items()
    ):
        raise CheckError("kernel result safety mismatch")
    return {
        "schema": result["schema"],
        "patch_sha256": source_delta["patch_sha256"],
        "build_result": result_receipt,
        "artifact_contract_schema": build_artifact.SCHEMA,
        "clean_full_lto_build": True,
        "source_restored": True,
        "verified": True,
    }


def verify_run_manifest(
    data: bytes,
    *,
    image_receipt: dict[str, Any],
    kernel_result_receipt: dict[str, Any],
    fixed_receipts: dict[str, Any],
    source_receipts: dict[str, Any],
    actual_tool_receipts: dict[str, Any],
) -> tuple[dict[str, Any], bytes, bytes]:
    try:
        manifest = json.loads(data.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("invalid E1 run manifest") from exc
    if not isinstance(manifest, dict):
        raise CheckError("E1 run manifest is not an object")
    if manifest.get("schema") != RUN_MANIFEST_SCHEMA:
        raise CheckError("run manifest schema mismatch")
    if manifest.get("target") != TARGET or manifest.get("profile") != "E1":
        raise CheckError("run manifest target/profile mismatch")
    nonce = manifest.get("nonce")
    if not isinstance(nonce, str) or len(nonce) != 32:
        raise CheckError("run manifest nonce shape mismatch")
    try:
        bytes.fromhex(nonce)
    except ValueError as exc:
        raise CheckError("run manifest nonce is not hexadecimal") from exc
    if (
        manifest.get("checkpoint_patch_sha256") != checkpoint.PATCH_SHA256
        or manifest.get("checkpoint_carrier_sha256") != checkpoint.CARRIER_SHA256
    ):
        raise CheckError("run manifest checkpoint identity mismatch")
    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        raise CheckError("run manifest inputs are not an object")
    require_receipt(inputs.get("image"), image_receipt, "run manifest Image")
    require_receipt(
        inputs.get("kernel_build_result"),
        kernel_result_receipt,
        "run manifest kernel result",
    )
    expected_fixed = {
        "base_boot": {
            "size": BOOT_SIZE,
            "sha256": carrier_inputs.EXPECTED_BASE_BOOT_SHA256,
        },
        "vendor_ramdisk": {
            "size": carrier_inputs.VENDOR_RAMDISK_SIZE,
            "sha256": carrier_inputs.VENDOR_RAMDISK_SHA256,
        },
        "lz4": {"size": base_static.LZ4_SIZE, "sha256": base_static.LZ4_SHA256},
        "magiskboot": {
            "size": carrier_inputs.MAGISKBOOT_SIZE,
            "sha256": carrier_inputs.MAGISKBOOT_SHA256,
        },
    }
    for name, expected in expected_fixed.items():
        require_receipt(inputs.get(name), expected, f"run manifest {name}")
        require_receipt(fixed_receipts.get(name), expected, f"actual {name}")
        require_receipt(
            inputs.get(name), fixed_receipts[name], f"run manifest actual {name}"
        )
    sources = inputs.get("sources")
    if not isinstance(sources, dict):
        raise CheckError("run manifest sources are not an object")
    for name, digest in e1.EXPECTED_SOURCE_SHA256.items():
        value = sources.get(name, {})
        actual = source_receipts.get(name, {})
        if (
            not isinstance(value, dict)
            or not isinstance(actual, dict)
            or value.get("sha256") != digest
            or not isinstance(value.get("size"), int)
            or value != actual
        ):
            raise CheckError(f"run manifest source mismatch: {name}")
    expected_runtime_contract = {
        "schema": e1.SCHEMA,
        "compile_flags": list(e1.COMPILE_FLAGS),
        "child_token_hex": e1.CHILD_TOKEN.hex(),
        "child_exit": e1.CHILD_EXIT,
        "stage_values": dict(sorted(e1.STAGE_VALUES.items())),
        "runtime_syscalls": dict(sorted(e1.RUNTIME_SYSCALLS.items())),
        "client_syscalls": dict(sorted(e1.CLIENT_SYSCALLS.items())),
        "child_syscalls": dict(sorted(e1.CHILD_SYSCALLS.items())),
    }
    if inputs.get("runtime_contract") != expected_runtime_contract:
        raise CheckError("run manifest runtime contract mismatch")
    modules = inputs.get("modules")
    expected_modules = [
        {"file": name, "runtime": runtime, "size": size, "sha256": digest}
        for name, runtime, size, digest in e1.MODULE_SPECS
    ]
    if modules != expected_modules:
        raise CheckError("run manifest module closure mismatch")
    host_tools = inputs.get("host_tools")
    expected_tool_names = {
        "aarch64-linux-gnu-gcc",
        "aarch64-linux-gnu-strip",
        "aarch64-linux-gnu-readelf",
        "aarch64-linux-gnu-nm",
        "aarch64-linux-gnu-objdump",
        "gcc",
        "file",
        "qemu-aarch64",
    }
    if not isinstance(host_tools, dict) or set(host_tools) != expected_tool_names:
        raise CheckError("run manifest host-tool set mismatch")
    for name, value in host_tools.items():
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("size"), int)
            or value["size"] <= 0
            or not isinstance(value.get("sha256"), str)
            or len(value["sha256"]) != 64
            or not isinstance(value.get("resolved_name"), str)
        ):
            raise CheckError(f"run manifest host-tool receipt malformed: {name}")
        if value != actual_tool_receipts.get(name):
            raise CheckError(f"run manifest host-tool identity mismatch: {name}")
    encoded = canonical_json(manifest)
    digest = hashlib.sha256(encoded).digest()
    run_id = digest[:16]
    if run_id == bytes(16) or run_id == checkpoint.MODEL_RUN_IDS["E1"]:
        raise CheckError("run manifest derived an invalid/model run ID")
    return manifest, encoded, run_id


def run_checked(argv: list[str | Path], cwd: Path, label: str) -> None:
    result = subprocess.run(
        [str(value) for value in argv],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )
    if result.returncode != 0:
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise CheckError(f"{label} failed rc={result.returncode}: {output}")


def reconstruct_carrier(
    *,
    base_boot: bytes,
    magiskboot: bytes,
    source_data: dict[str, bytes],
    run_id: bytes,
    tools: dict[str, str],
) -> tuple[bytes, dict[str, Any]]:
    with tempfile.TemporaryDirectory(
        prefix="s22-r4w1e-e1-reconstruct-"
    ) as temporary:
        root = Path(temporary)
        build_dir = root / "build"
        nochange_dir = root / "nochange"
        work_dir = root / "carrier"
        for directory in (build_dir, nochange_dir, work_dir):
            directory.mkdir()
        base_path = root / "base.boot.img"
        magiskboot_path = root / "magiskboot"
        carrier_inputs.stage_file(base_path, base_boot)
        carrier_inputs.stage_file(magiskboot_path, magiskboot, executable=True)

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
        init_data = compiled["init"]["data"]
        child_data = compiled["child"]["data"]
        init_path = build_dir / "init"
        child_path = build_dir / "s22-e1-child"
        if init_path.read_bytes() != init_data or child_path.read_bytes() != child_data:
            raise CheckError("independent E1 binary changed after compilation")

        run_checked(
            [magiskboot_path, "unpack", "-h", base_path],
            nochange_dir,
            "independent no-change unpack",
        )
        nochange_boot = root / "boot.nochange.img"
        run_checked(
            [magiskboot_path, "repack", base_path, nochange_boot],
            nochange_dir,
            "independent no-change repack",
        )
        if nochange_boot.read_bytes() != base_boot:
            raise CheckError("independent magiskboot no-change repack changed base boot")

        run_checked(
            [magiskboot_path, "unpack", "-h", base_path],
            work_dir,
            "independent carrier unpack",
        )
        original_kernel = (work_dir / "kernel").read_bytes()
        original_init = build_dir / "init.magisk.original"
        run_checked(
            [
                magiskboot_path,
                "cpio",
                work_dir / "ramdisk.cpio",
                f"extract init {original_init}",
            ],
            work_dir,
            "independent original init extraction",
        )
        if (
            hashlib.sha256(original_init.read_bytes()).hexdigest()
            != carrier_inputs.EXPECTED_ORIGINAL_MAGISK_INIT_SHA256
        ):
            raise CheckError("independent base Magisk /init identity mismatch")
        run_checked(
            [
                magiskboot_path,
                "cpio",
                work_dir / "ramdisk.cpio",
                f"add 750 init {init_path}",
            ],
            work_dir,
            "independent /init replacement",
        )
        run_checked(
            [
                magiskboot_path,
                "cpio",
                work_dir / "ramdisk.cpio",
                f"add 750 s22-e1-child {child_path}",
            ],
            work_dir,
            "independent child addition",
        )
        carrier_path = root / "carrier.boot.img"
        run_checked(
            [magiskboot_path, "repack", base_path, carrier_path],
            work_dir,
            "independent E1 carrier repack",
        )
        carrier = carrier_path.read_bytes()
        if len(carrier) != BOOT_SIZE:
            raise CheckError("independent E1 carrier size mismatch")
        if carrier[KERNEL_START:KERNEL_END] != original_kernel:
            raise CheckError("independent ramdisk-only carrier changed its kernel")
        compiled_receipts = {
            name: {key: value for key, value in row.items() if key != "data"}
            for name, row in compiled.items()
        }
        return carrier, {
            "base_boot_exact": True,
            "source_compiled": True,
            "magiskboot_nochange_byte_identical": True,
            "carrier_size": len(carrier),
            "carrier_sha256": hashlib.sha256(carrier).hexdigest(),
            "compiled": compiled_receipts,
            "verified": True,
        }


def require_reconstructed_carrier(submitted: bytes, reconstructed: bytes) -> None:
    if submitted != reconstructed:
        raise CheckError("submitted carrier differs from independent reconstruction")


def verify_exact_boot_ap(ap_data: bytes, expected_frame: bytes) -> dict[str, Any]:
    ap_info, ap_frame = verify.parse_ap_tar_md5(ap_data)
    member = ap_info.get("member")
    if (
        not isinstance(member, dict)
        or member.get("name") != "boot.img.lz4"
        or ap_frame != expected_frame
    ):
        raise CheckError("candidate AP is not one exact boot.img.lz4 member")
    return ap_info


def rootfs_audit(
    candidate: bytes,
    vendor_boot: bytes,
    lz4_tool: Path,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    run_id: bytes,
) -> dict[str, Any]:
    boot = verify.parse_boot_v4(candidate)
    vendor = verify.parse_vendor_boot_v4(vendor_boot)
    generic = verify.decompress_lz4(lz4_tool, boot.ramdisk)
    layers: list[tuple[str, tuple[verify.CpioEntry, ...]]] = [
        ("generic", verify.parse_newc(generic))
    ]
    for index, fragment in enumerate(vendor.fragments):
        decoded = verify.decompress_lz4(lz4_tool, fragment.data)
        layers.append((f"vendor[{index}]/{fragment.name}", verify.parse_newc(decoded)))
    seen: dict[str, tuple[str, verify.CpioEntry]] = {}
    for label, entries in layers:
        for entry in entries:
            if entry.name in seen:
                raise CheckError(f"rootfs duplicate/override: {entry.name}")
            if entry.file_type == "symlink" or entry.nlink != 1:
                raise CheckError(f"rootfs alias forbidden: {label}:{entry.name}")
            seen[entry.name] = (label, entry)

    def exact_executable(name: str, expected: dict[str, Any]) -> tuple[str, verify.CpioEntry]:
        value = seen.get(name)
        if value is None:
            raise CheckError(f"effective rootfs missing {name}")
        label, entry = value
        actual = {"size": len(entry.data), "sha256": hashlib.sha256(entry.data).hexdigest()}
        if (
            label != "generic"
            or entry.file_type != "regular"
            or entry.uid != 0
            or entry.gid != 0
            or stat.S_IMODE(entry.mode) != 0o750
        ):
            raise CheckError(f"effective {name} metadata mismatch")
        require_receipt(actual, expected, f"effective {name}")
        return label, entry

    _, init = exact_executable("init", expected_init)
    _, child = exact_executable("s22-e1-child", expected_child)
    init_elf = inspect_static_elf(init.data, "/init")
    child_elf = inspect_static_elf(child.data, "/s22-e1-child")
    if init.data.count(run_id) != 1:
        raise CheckError("effective /init run ID cardinality mismatch")
    required_init = (
        b"/proc/s22_checkpoint",
        b"/proc/modules",
        b"/s22-e1-child",
        e1.CHILD_TOKEN,
        *(name.encode("ascii") for name, _runtime, _size, _digest in e1.MODULE_SPECS),
    )
    if any(value not in init.data for value in required_init):
        raise CheckError("effective /init required runtime strings missing")
    if e1.CHILD_TOKEN not in child.data:
        raise CheckError("effective child token missing")
    forbidden = (b"/dev/block", b"/config", b"ttyGS", b"/bin/sh", b"sec_log_buf.ko")
    if any(value in init.data for value in forbidden):
        raise CheckError("effective /init contains forbidden authority string")
    module_rows = []
    for name, runtime, size, digest in e1.MODULE_SPECS:
        value = seen.get(f"lib/modules/{name}")
        if value is None:
            raise CheckError(f"effective rootfs missing module: {name}")
        label, entry = value
        if (
            not label.startswith("vendor[")
            or entry.file_type != "regular"
            or len(entry.data) != size
            or hashlib.sha256(entry.data).hexdigest() != digest
        ):
            raise CheckError(f"effective module identity mismatch: {name}")
        module_rows.append({"file": name, "runtime": runtime, "layer": label})
    rdinit_sources = (
        boot.header["cmdline"].encode("ascii"),
        vendor.cmdline.encode("ascii"),
        vendor.bootconfig,
    )
    if any(b"rdinit=" in value for value in rdinit_sources):
        raise CheckError("rdinit override contaminates the effective entrypoint")
    return {
        "composition_order": [label for label, _entries in layers],
        "entry_count": len(seen),
        "no_duplicate_override_or_alias": True,
        "init": {**expected_init, "elf": init_elf, "run_id_count": 1},
        "child": {**expected_child, "elf": child_elf},
        "modules": module_rows,
        "module_count": len(module_rows),
        "rdinit_override_absent": True,
        "verified": True,
    }


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    directory = resolve(root, args.candidate)
    if directory.is_symlink() or not directory.is_dir():
        raise CheckError("candidate directory missing or indirect")
    paths = {
        "carrier": directory / "carrier.boot.img",
        "candidate": directory / "boot.img",
        "frame": directory / "boot.img.lz4",
        "ap": directory / "odin4/AP.tar.md5",
        "manifest": directory / "manifest.json",
        "run_manifest": directory / "run-manifest.json",
    }
    artifacts = {name: file_receipt(path, name) for name, path in paths.items()}
    receipts = {name: value[0] for name, value in artifacts.items()}
    data = {name: value[1] for name, value in artifacts.items()}
    if receipts["carrier"]["size"] != BOOT_SIZE or receipts["candidate"]["size"] != BOOT_SIZE:
        raise CheckError("carrier/candidate boot size mismatch")

    image_receipt, image = file_receipt(resolve(root, args.image), "R4W1-E Image")
    if image_receipt["size"] != KERNEL_SIZE:
        raise CheckError("R4W1-E Image size mismatch")
    verify.parse_arm64_header(image)
    if (
        image.count(checkpoint.ENTRY_PROOF) != 1
        or image.count(checkpoint.ENTRY_FAMILY) != 1
        or any(image.count(value) for value in (b"[[S22P1D|", b"[[S22R4W1B|", b"[[S22R4W1|"))
    ):
        raise CheckError("R4W1-E Image marker contract mismatch")
    kernel_result_receipt, kernel_result_data = file_receipt(
        resolve(root, args.kernel_result), "R4W1-E kernel result"
    )
    kernel_result = verify_kernel_result(kernel_result_data, image_receipt)

    base_receipt, base_boot = verify.read_pinned_stable(
        resolve(root, args.base_boot),
        BOOT_SIZE,
        carrier_inputs.EXPECTED_BASE_BOOT_SHA256,
        "known Magisk base boot",
    )
    vendor_ramdisk_receipt, _vendor_ramdisk = verify.read_pinned_stable(
        resolve(root, args.vendor_ramdisk),
        carrier_inputs.VENDOR_RAMDISK_SIZE,
        carrier_inputs.VENDOR_RAMDISK_SHA256,
        "FYG8 vendor ramdisk",
    )
    lz4_receipt, lz4_data = verify.read_pinned_stable(
        resolve(root, args.lz4), base_static.LZ4_SIZE, base_static.LZ4_SHA256, "lz4"
    )
    magiskboot_receipt, magiskboot = verify.read_pinned_stable(
        resolve(root, args.magiskboot),
        carrier_inputs.MAGISKBOOT_SIZE,
        carrier_inputs.MAGISKBOOT_SHA256,
        "magiskboot",
    )
    source_data, source_receipts = exact_source_data(root)
    host_contract = e1.run_check(
        root / e1.DEFAULT_RUNTIME,
        root / e1.DEFAULT_CHILD,
        root / e1.DEFAULT_CLIENT,
        root / e1.DEFAULT_HEADER,
        root / e1.DEFAULT_INVENTORY,
    )
    if host_contract.get("verdict") != e1.VERDICT:
        raise CheckError("independent E1 host contract did not pass")
    tools = e1.require_tools()
    actual_tool_receipts = tool_receipts(tools)
    fixed_receipts = {
        "base_boot": base_receipt,
        "vendor_ramdisk": vendor_ramdisk_receipt,
        "lz4": lz4_receipt,
        "magiskboot": magiskboot_receipt,
    }
    _, run_encoded, run_id = verify_run_manifest(
        data["run_manifest"],
        image_receipt=image_receipt,
        kernel_result_receipt=kernel_result_receipt,
        fixed_receipts=fixed_receipts,
        source_receipts=source_receipts,
        actual_tool_receipts=actual_tool_receipts,
    )
    reconstructed_carrier, reconstruction = reconstruct_carrier(
        base_boot=base_boot,
        magiskboot=magiskboot,
        source_data=source_data,
        run_id=run_id,
        tools=tools,
    )
    require_reconstructed_carrier(data["carrier"], reconstructed_carrier)

    try:
        manifest = json.loads(data["manifest"].decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError("invalid candidate manifest") from exc
    if not isinstance(manifest, dict):
        raise CheckError("candidate manifest is not an object")
    for name, expected in {
        "schema": CANDIDATE_SCHEMA,
        "target": TARGET,
        "rung": RUNG,
        "verdict": CANDIDATE_VERDICT,
    }.items():
        if manifest.get(name) != expected:
            raise CheckError(f"candidate manifest {name} mismatch")
    binding = manifest.get("run_binding")
    if not isinstance(binding, dict):
        raise CheckError("candidate run binding is not an object")
    if (
        binding.get("run_id") != run_id.hex()
        or binding.get("canonical_manifest_size") != len(run_encoded)
        or binding.get("canonical_manifest_sha256") != hashlib.sha256(run_encoded).hexdigest()
        or binding.get("derivation") != "sha256(canonical-run-manifest)[:16]"
        or binding.get("p2_7_model_id_reused") is not False
    ):
        raise CheckError("candidate run binding mismatch")
    if manifest.get("host_contract") != {"schema": e1.SCHEMA, "verdict": e1.VERDICT}:
        raise CheckError("candidate host-contract binding mismatch")
    expected_blockers = [
        "independent offline candidate checker not yet passed",
        "single clean kernel build is not a two-build reproducibility proof",
        "no F1 preflight, approval, or live authority exists",
    ]
    if manifest.get("blockers") != expected_blockers:
        raise CheckError("candidate blocker set mismatch")
    safety = manifest.get("safety")
    if not isinstance(safety, dict):
        raise CheckError("candidate safety contract is not an object")
    expected_safety = {
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
    }
    if safety != expected_safety:
        raise CheckError("candidate safety contract mismatch")

    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict):
        raise CheckError("candidate outputs are not an object")
    for name, artifact_name in {
        "carrier_boot": "carrier",
        "boot_img": "candidate",
        "boot_img_lz4": "frame",
        "ap_tar_md5": "ap",
    }.items():
        require_receipt(outputs.get(name), receipts[artifact_name], f"candidate output {name}")
    for name in ("init", "child"):
        require_receipt(
            outputs.get(name),
            reconstruction["compiled"][name],
            f"candidate independently compiled {name}",
        )
    expected = (
        reconstructed_carrier[:HEADER_END]
        + image
        + reconstructed_carrier[KERNEL_END:]
    )
    if data["candidate"] != expected:
        raise CheckError("candidate differs from independent fixed-interval construction")
    if data["carrier"][GAP_START:GAP_END] != data["candidate"][GAP_START:GAP_END]:
        raise CheckError("candidate alignment gap changed")
    carrier_boot = verify.parse_boot_v4(data["carrier"])
    candidate_boot = verify.parse_boot_v4(data["candidate"])
    if carrier_boot.header != candidate_boot.header or candidate_boot.kernel != image:
        raise CheckError("candidate boot-v4 header/kernel binding mismatch")
    if carrier_boot.ramdisk != candidate_boot.ramdisk:
        raise CheckError("kernel replacement changed the carrier ramdisk")

    vendor_receipt, vendor_boot = verify.read_pinned_stable(
        resolve(root, args.vendor_boot),
        base_static.VENDOR_BOOT_SIZE,
        base_static.VENDOR_BOOT_SHA256,
        "stock vendor_boot",
    )
    with tempfile.TemporaryDirectory(prefix="s22-r4w1e-e1-static-") as temporary:
        lz4_tool = Path(temporary) / "lz4"
        lz4_tool.write_bytes(lz4_data)
        lz4_tool.chmod(0o700)
        frame_info = verify.parse_lz4_frame(data["frame"])
        if frame_info.get("content_size") != BOOT_SIZE:
            raise CheckError("candidate LZ4 content-size mismatch")
        if verify.decompress_lz4(lz4_tool, data["frame"], BOOT_SIZE) != data["candidate"]:
            raise CheckError("candidate LZ4 roundtrip mismatch")
        verify_exact_boot_ap(data["ap"], data["frame"])
        rootfs = rootfs_audit(
            data["candidate"],
            vendor_boot,
            lz4_tool,
            expected_init=reconstruction["compiled"]["init"],
            expected_child=reconstruction["compiled"]["child"],
            run_id=run_id,
        )

    critical_inodes = []
    for path in paths.values():
        metadata = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode):
            raise CheckError(f"critical artifact is not regular: {path}")
        critical_inodes.append((metadata.st_dev, metadata.st_ino))
    if len(set(critical_inodes)) != len(critical_inodes):
        raise CheckError("critical candidate artifacts are hardlinked/aliased")
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "inputs": {
            "image": image_receipt,
            "kernel_result": {**kernel_result_receipt, **kernel_result},
            "base_boot": base_receipt,
            "vendor_ramdisk": vendor_ramdisk_receipt,
            "vendor_boot": vendor_receipt,
            "lz4": lz4_receipt,
            "magiskboot": magiskboot_receipt,
            "sources": source_receipts,
            "host_tools": actual_tool_receipts,
        },
        "run_binding": {
            "run_id": run_id.hex(),
            "canonical_manifest_size": len(run_encoded),
            "canonical_manifest_sha256": hashlib.sha256(run_encoded).hexdigest(),
            "fresh_non_model_id": True,
            "verified": True,
        },
        "candidate": {
            "artifacts": receipts,
            "independent_carrier_reconstruction": reconstruction,
            "carrier_matches_independent_reconstruction": True,
            "independent_fixed_interval_exact": True,
            "boot_header_preserved": True,
            "ramdisk_preserved_across_kernel_replacement": True,
            "lz4_roundtrip": True,
            "boot_only_ap": True,
        },
        "rootfs": rootfs,
        "blockers": [],
        "limits": [
            "one clean Full-LTO build is not two-build kernel reproducibility",
            "offline static qualification grants no D0, D1, F1, or live authority",
        ],
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--kernel-result", type=Path, default=DEFAULT_KERNEL_RESULT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument(
        "--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK
    )
    parser.add_argument("--vendor-boot", type=Path, default=DEFAULT_VENDOR_BOOT)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
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
            encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode("ascii") + b"\n"
            offset = 0
            while offset < len(encoded):
                written = os.write(descriptor, encoded[offset:])
                if written <= 0:
                    raise CheckError("short write while recording checker result")
                offset += written
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except (
        CheckError,
        e1.CheckError,
        verify.BootVerifyError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": result["verdict"],
                "run_id": result["run_binding"]["run_id"],
                "boot_sha256": result["candidate"]["artifacts"]["candidate"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
