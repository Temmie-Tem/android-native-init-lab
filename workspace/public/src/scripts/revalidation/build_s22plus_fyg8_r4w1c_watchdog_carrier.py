#!/usr/bin/env python3
"""Build the host-only FYG8 R4W1-C watchdog-managed PID1 carrier.

This builder never contacts a device and never invokes Odin. It replaces only
the ramdisk /init in a known Magisk boot carrier, then inserts the independently
qualified R4W1-B kernel Image into the fixed boot-v4 kernel interval.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import build_s22plus_fyg8_r4w1b_candidate as r4w1b
import build_s22plus_inplace_m23_dts_exact_qmp_park as m23
import build_s22plus_m31b_wdt_managed_park as m31b
import s22plus_boot_slice as boot_slice
from build_s22plus_direct_p3_boot import BOOT_PARTITION_SIZE, sha256_file
from build_s22plus_inplace_m4t1_magiskboot import (
    DEFAULT_BASE_BOOT,
    DEFAULT_MAGISKBOOT,
    EXPECTED_BASE_BOOT_SHA256,
    EXPECTED_ORIGINAL_MAGISK_INIT_SHA256,
    diff_ranges,
    run_in_dir,
)


SCHEMA = "s22plus_fyg8_r4w1c_watchdog_carrier_build_v1"
VERDICT = "PASS_R4W1C_WATCHDOG_CARRIER_BUILT_HOST_ONLY"
TARGET = r4w1b.TARGET
RUNG = "R4W1-C"
MARKER = "S22_NATIVE_INIT_R4W1C_WDT_CARRIER"

DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/reproduction-a"
)
DEFAULT_SOURCE = Path(
    "workspace/public/src/native-init/s22plus_init_r4w1c_wdt_carrier.c"
)
DEFAULT_VENDOR_RAMDISK = m23.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = r4w1b.DEFAULT_LZ4
DEFAULT_IMAGE = r4w1b.DEFAULT_IMAGE
DEFAULT_REPRO_RESULT = r4w1b.DEFAULT_REPRO_RESULT

VENDOR_RAMDISK_SIZE = 21_813_545
VENDOR_RAMDISK_SHA256 = (
    "41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193"
)
MAGISKBOOT_SIZE = 943_848
MAGISKBOOT_SHA256 = (
    "a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e"
)
SOURCE_MAX_SIZE = 1_048_576

MODULE_SPECS = [
    {
        "file": "smem.ko",
        "runtime": "smem",
        "size": 28_704,
        "sha256": "27a80d5598329d6a526384d09806de63983204988748ea4e7d3fccfafc24a524",
    },
    {
        "file": "minidump.ko",
        "runtime": "minidump",
        "size": 37_312,
        "sha256": "e5e6f4dfe1ddac2cd4f8d15c11a50d4d32b6e9de278fedbed44747630a5c554d",
    },
    {
        "file": "qcom-scm.ko",
        "runtime": "qcom_scm",
        "size": 218_384,
        "sha256": "e12ba8661808c2c47acf42c9939157e509fcdb5b98f6e650f79b92dba18a1af3",
    },
    {
        "file": "qcom_wdt_core.ko",
        "runtime": "qcom_wdt_core",
        "size": 48_640,
        "sha256": "ef484fb4f1f17586ff63852e0ea9579d07f275f7966ad117d20039055c2d7599",
    },
    {
        "file": "gh_virt_wdt.ko",
        "runtime": "gh_virt_wdt",
        "size": 18_944,
        "sha256": "f030c5486a41b1fbe4b0ea3aa85a401dd16daa1f1a551a626f6ea424ee90dd39",
    },
]


class BuildError(ValueError):
    """A fail-closed host build error."""


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise BuildError("repository root not found")


def resolve(root: Path, value: Path) -> Path:
    candidate = value if value.is_absolute() else root / value
    return Path(os.path.abspath(candidate))


def run(
    argv: list[str | Path],
    *,
    cwd: Path | None = None,
    input_bytes: bytes | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(part) for part in argv],
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def require_ok(result: subprocess.CompletedProcess[bytes], label: str) -> None:
    if result.returncode != 0:
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise BuildError(f"{label} failed rc={result.returncode}: {output}")


def _identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def read_stable_file(
    path: Path, label: str, max_size: int
) -> tuple[dict[str, Any], bytes]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BuildError(f"{label} cannot be opened directly: {path}") from exc
    try:
        first = os.fstat(descriptor)
        if not stat.S_ISREG(first.st_mode):
            raise BuildError(f"{label} is not a direct regular file: {path}")
        if first.st_size < 0 or first.st_size > max_size:
            raise BuildError(f"{label} size outside bound: {first.st_size}")
        chunks: list[bytes] = []
        remaining = first.st_size
        while remaining:
            chunk = os.read(descriptor, min(1_048_576, remaining))
            if not chunk:
                raise BuildError(f"{label} ended before its pinned size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise BuildError(f"{label} exceeded its pinned size")
        second = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        path_after = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise BuildError(f"{label} path disappeared after reading") from exc
    if _identity(first) != _identity(second) or _identity(second) != _identity(
        path_after
    ):
        raise BuildError(f"{label} identity changed while reading")
    data = b"".join(chunks)
    digest = boot_slice.sha256_bytes(data)
    return {"size": len(data), "sha256": digest}, data


def read_exact_file(
    path: Path, expected_size: int, expected_sha256: str, label: str
) -> bytes:
    receipt, data = read_stable_file(path, label, expected_size)
    if len(data) != expected_size or receipt["sha256"] != expected_sha256:
        raise BuildError(
            f"{label} pin mismatch size={len(data)} sha256={receipt['sha256']}"
        )
    return data


def stage_file(path: Path, data: bytes, *, executable: bool = False) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags, 0o700 if executable else 0o400)
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise BuildError(f"short write while staging {path.name}")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def derive_and_verify_module_closure(
    vendor_ramdisk: Path, lz4_tool: Path, build_dir: Path
) -> dict[str, Any]:
    read_exact_file(
        vendor_ramdisk,
        VENDOR_RAMDISK_SIZE,
        VENDOR_RAMDISK_SHA256,
        "FYG8 vendor ramdisk",
    )
    metadata = m23.extract_vendor_metadata(vendor_ramdisk, lz4_tool, build_dir)
    closure = m31b.watchdog_closure(
        dep_map=metadata["dep_map"],
        recovery_basenames=metadata["recovery_basenames"],
    )
    expected_files = [spec["file"] for spec in MODULE_SPECS]
    if closure["modules"] != expected_files:
        raise BuildError("derived watchdog closure does not match the pinned order")

    decompressed = run([lz4_tool, "-dc", vendor_ramdisk])
    require_ok(decompressed, "decompress FYG8 vendor ramdisk for module audit")
    extract_dir = build_dir / "watchdog-modules"
    extract_dir.mkdir()
    relative_paths = [f"lib/modules/{name}" for name in expected_files]
    extracted = run(
        ["cpio", "-id", "--no-absolute-filenames", *relative_paths],
        cwd=extract_dir,
        input_bytes=decompressed.stdout,
    )
    require_ok(extracted, "extract exact watchdog modules")

    receipts: list[dict[str, Any]] = []
    for spec in MODULE_SPECS:
        path = extract_dir / "lib/modules" / str(spec["file"])
        read_exact_file(
            path,
            int(spec["size"]),
            str(spec["sha256"]),
            f"watchdog module {spec['file']}",
        )
        modinfo = run(["modinfo", "-F", "name", path])
        require_ok(modinfo, f"modinfo name for {spec['file']}")
        runtime_name = modinfo.stdout.decode("ascii", errors="strict").strip()
        if runtime_name != spec["runtime"]:
            raise BuildError(
                f"runtime module name mismatch for {spec['file']}: {runtime_name}"
            )
        receipts.append(dict(spec))
    return {
        "files": expected_files,
        "runtime_names": [spec["runtime"] for spec in MODULE_SPECS],
        "count": len(MODULE_SPECS),
        "modules": receipts,
        "order_model": closure["order_model"],
        "stock_recovery_positions": closure["stock_recovery_positions"],
        "vendor_metadata_hashes": metadata["metadata_hashes"],
    }


def compile_init(source: Path, output: Path, build_dir: Path) -> dict[str, Any]:
    compile_result = run(
        [
            "aarch64-linux-gnu-gcc",
            "-nostdlib",
            "-static",
            "-ffreestanding",
            "-fno-builtin",
            "-fno-stack-protector",
            "-fno-asynchronous-unwind-tables",
            "-fno-unwind-tables",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wl,--build-id=none",
            "-Wl,-e,_start",
            "-Wl,-z,noexecstack",
            "-o",
            output,
            source,
        ]
    )
    require_ok(compile_result, "compile R4W1-C watchdog carrier init")
    strip_result = run(["aarch64-linux-gnu-strip", "-s", output])
    require_ok(strip_result, "strip R4W1-C watchdog carrier init")
    file_result = run(["file", output])
    require_ok(file_result, "inspect R4W1-C init file")
    readelf_result = run(["aarch64-linux-gnu-readelf", "-h", "-l", output])
    require_ok(readelf_result, "inspect R4W1-C init ELF")
    objdump_result = run(
        ["aarch64-linux-gnu-objdump", "-d", output.name], cwd=output.parent
    )
    require_ok(objdump_result, "disassemble R4W1-C init")
    readelf_text = readelf_result.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump_result.stdout.decode("utf-8", errors="replace")
    if "AArch64" not in readelf_text or "INTERP" in readelf_text:
        raise BuildError("R4W1-C init is not a static AArch64 executable")
    binary = output.read_bytes()
    required = [
        MARKER,
        "exact_finit_rc=0",
        "proc_modules_exact=1",
        "phase=module_load_complete count=5",
        "phase=proc_modules_verified count=5 exact=1",
        "phase=park_enter",
        "module_closure_visible=1",
        "watchdog_ownership=not_directly_proven",
        "functional_proof=bounded_live_survival",
        "/proc/modules",
        "/lib/modules/",
    ]
    for value in required:
        if value.encode("ascii") not in binary:
            raise BuildError(f"required init marker missing: {value}")
    forbidden = [
        b"/dev/block",
        b"/config",
        b"usb_gadget",
        b"ttyGS0",
        b"ss_acm.0",
        b"reboot_request=download",
        b"/system/bin/init",
        b"ld-linux",
        b"libc.so",
    ]
    for value in forbidden:
        if value in binary:
            raise BuildError(f"forbidden init string present: {value!r}")
    for spec in MODULE_SPECS:
        for key in ("file", "runtime"):
            if str(spec[key]).encode("ascii") not in binary:
                raise BuildError(f"compiled init missing {key}: {spec[key]}")
    (build_dir / "r4w1c_init_readelf.txt").write_text(
        readelf_text, encoding="utf-8"
    )
    (build_dir / "r4w1c_init_objdump.txt").write_text(
        objdump_text, encoding="utf-8"
    )
    file_text = file_result.stdout.decode("utf-8", errors="replace").strip()
    file_description = file_text.partition(":")[2].strip()
    if not file_description:
        raise BuildError("file(1) returned no normalized ELF description")
    return {
        "size": output.stat().st_size,
        "sha256": sha256_file(output),
        "file": file_description,
        "required_strings": required,
        "forbidden_strings_absent": [value.decode("ascii") for value in forbidden],
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    output = resolve(root, args.out)
    if output.exists():
        raise BuildError(f"output path already exists: {output}")
    r4w1b.validate_patch_vbmeta_flag()

    base_boot = resolve(root, args.base_boot)
    source = resolve(root, args.source)
    vendor_ramdisk = resolve(root, args.vendor_ramdisk)
    lz4_tool = resolve(root, args.lz4)
    magiskboot = resolve(root, args.magiskboot)
    image_path = resolve(root, args.image)
    repro_path = resolve(root, args.repro_result)

    base_data = read_exact_file(
        base_boot,
        BOOT_PARTITION_SIZE,
        EXPECTED_BASE_BOOT_SHA256,
        "known Magisk base boot",
    )
    image_pin, image = boot_slice.read_pinned_stable(
        image_path,
        r4w1b.KERNEL_SIZE,
        r4w1b.R4W1B_IMAGE_SHA256,
        "qualified R4W1-B Image",
    )
    repro_pin, repro_bytes = boot_slice.read_pinned_stable(
        repro_path,
        r4w1b.REPRO_RESULT_SIZE,
        r4w1b.REPRO_RESULT_SHA256,
        "R4W1-B reproduction result",
    )
    repro_receipt = r4w1b.verify_reproduction_result(repro_bytes)
    lz4_data = read_exact_file(
        lz4_tool, r4w1b.LZ4_SIZE, r4w1b.LZ4_SHA256, "pinned lz4"
    )
    magiskboot_data = read_exact_file(
        magiskboot, MAGISKBOOT_SIZE, MAGISKBOOT_SHA256, "pinned magiskboot"
    )
    vendor_ramdisk_data = read_exact_file(
        vendor_ramdisk,
        VENDOR_RAMDISK_SIZE,
        VENDOR_RAMDISK_SHA256,
        "FYG8 vendor ramdisk",
    )
    source_receipt, source_data = read_stable_file(
        source, "R4W1-C PID1 source", SOURCE_MAX_SIZE
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output.name}.", dir=output.parent
    ) as temporary, tempfile.TemporaryDirectory(
        prefix="s22-r4w1c-pinned-inputs-"
    ) as input_temporary:
        staging = Path(temporary)
        pinned_inputs = Path(input_temporary)
        build_dir = staging / "build"
        work_dir = staging / "magiskboot-work"
        nochange_dir = staging / "nochange-probe"
        unpack_dir = staging / "candidate-unpack"
        for directory in (build_dir, work_dir, nochange_dir, unpack_dir):
            directory.mkdir()

        pinned_base_boot = pinned_inputs / "base.boot.img"
        pinned_vendor_ramdisk = pinned_inputs / "vendor_ramdisk00"
        pinned_source = pinned_inputs / "s22plus_init_r4w1c_wdt_carrier.c"
        pinned_lz4 = pinned_inputs / "lz4"
        pinned_magiskboot = pinned_inputs / "magiskboot"
        stage_file(pinned_base_boot, base_data)
        stage_file(pinned_vendor_ramdisk, vendor_ramdisk_data)
        stage_file(pinned_source, source_data)
        stage_file(pinned_lz4, lz4_data, executable=True)
        stage_file(pinned_magiskboot, magiskboot_data, executable=True)

        closure = derive_and_verify_module_closure(
            pinned_vendor_ramdisk, pinned_lz4, build_dir
        )
        init_path = build_dir / "s22plus_init_r4w1c_wdt_carrier"
        init_receipt = compile_init(pinned_source, init_path, build_dir)

        run_in_dir(
            [pinned_magiskboot, "unpack", "-h", pinned_base_boot],
            nochange_dir,
            "R4W1-C no-change unpack",
        )
        nochange_boot = build_dir / "boot.nochange.img"
        run_in_dir(
            [pinned_magiskboot, "repack", pinned_base_boot, nochange_boot],
            nochange_dir,
            "R4W1-C no-change repack",
        )
        if nochange_boot.read_bytes() != base_data:
            raise BuildError("magiskboot no-change repack is not byte-identical")

        run_in_dir(
            [pinned_magiskboot, "unpack", "-h", pinned_base_boot],
            work_dir,
            "R4W1-C unpack base boot",
        )
        ramdisk = work_dir / "ramdisk.cpio"
        original_kernel = work_dir / "kernel"
        original_init = build_dir / "init.magisk.original"
        run_in_dir(
            [pinned_magiskboot, "cpio", ramdisk, f"extract init {original_init}"],
            work_dir,
            "R4W1-C extract original init",
        )
        if sha256_file(original_init) != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
            raise BuildError("original Magisk /init pin mismatch")
        ramdisk_before = build_dir / "ramdisk.before.cpio"
        shutil.copy2(ramdisk, ramdisk_before)
        cpio_before = run(
            [pinned_magiskboot, "cpio", ramdisk, "test"], cwd=work_dir
        )
        if cpio_before.returncode != 1:
            raise BuildError(
                f"unexpected base Magisk cpio test rc={cpio_before.returncode}"
            )
        run_in_dir(
            [pinned_magiskboot, "cpio", ramdisk, f"add 750 init {init_path}"],
            work_dir,
            "R4W1-C replace /init",
        )
        cpio_after = run(
            [pinned_magiskboot, "cpio", ramdisk, "test"], cwd=work_dir
        )
        if cpio_after.returncode not in (1, 2):
            raise BuildError(
                f"unexpected patched Magisk cpio test rc={cpio_after.returncode}"
            )
        extracted_init = build_dir / "init.replaced"
        run_in_dir(
            [pinned_magiskboot, "cpio", ramdisk, f"extract init {extracted_init}"],
            work_dir,
            "R4W1-C verify replaced /init",
        )
        if extracted_init.read_bytes() != init_path.read_bytes():
            raise BuildError("ramdisk /init differs from compiled R4W1-C init")
        ramdisk_after = build_dir / "ramdisk.after.cpio"
        shutil.copy2(ramdisk, ramdisk_after)

        carrier_path = staging / "carrier.boot.img"
        run_in_dir(
            [pinned_magiskboot, "repack", pinned_base_boot, carrier_path],
            work_dir,
            "R4W1-C repack watchdog carrier",
        )
        carrier = carrier_path.read_bytes()
        if len(carrier) != BOOT_PARTITION_SIZE:
            raise BuildError("R4W1-C carrier boot size mismatch")
        if carrier[r4w1b.KERNEL_START : r4w1b.KERNEL_END] != (
            original_kernel.read_bytes()
        ):
            raise BuildError("ramdisk-only carrier unexpectedly changed its kernel")

        candidate, construction = r4w1b.build_candidate_bytes(carrier, image)
        candidate_path = staging / "boot.img"
        candidate_path.write_bytes(candidate)
        if candidate_path.read_bytes() != candidate:
            raise BuildError("staged R4W1-C candidate changed after write")
        run_in_dir(
            [pinned_magiskboot, "unpack", "-h", candidate_path],
            unpack_dir,
            "R4W1-C unpack final candidate",
        )
        final_init = build_dir / "init.final-candidate"
        run_in_dir(
            [
                pinned_magiskboot,
                "cpio",
                unpack_dir / "ramdisk.cpio",
                f"extract init {final_init}",
            ],
            unpack_dir,
            "R4W1-C extract final candidate init",
        )
        if final_init.read_bytes() != init_path.read_bytes():
            raise BuildError("final candidate /init differs from compiled carrier")
        if (unpack_dir / "kernel").read_bytes() != image:
            raise BuildError("final candidate kernel differs from qualified Image")

        frame_path = staging / "boot.img.lz4"
        require_ok(
            run(
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
            "compress R4W1-C boot",
        )
        roundtrip_path = staging / ".roundtrip.img"
        require_ok(
            run(
                [
                    pinned_lz4,
                    "-d",
                    "-f",
                    "-q",
                    frame_path,
                    roundtrip_path,
                ]
            ),
            "decompress R4W1-C boot roundtrip",
        )
        if roundtrip_path.read_bytes() != candidate:
            raise BuildError("R4W1-C LZ4 roundtrip mismatch")
        roundtrip_path.unlink()

        odin_dir = staging / "odin4"
        odin_dir.mkdir()
        ap_path = odin_dir / "AP.tar.md5"
        ap_structure = boot_slice.write_deterministic_boot_ap(
            frame_path.read_bytes(), ap_path
        )
        if ap_structure.get("members") != ["boot.img.lz4"]:
            raise BuildError("R4W1-C AP is not an exact boot-only archive")

        outputs = {
            "carrier_boot": {
                "size": len(carrier),
                "sha256": boot_slice.sha256_bytes(carrier),
            },
            "boot_img": {
                "size": len(candidate),
                "sha256": boot_slice.sha256_bytes(candidate),
            },
            "boot_img_lz4": {
                "size": frame_path.stat().st_size,
                "sha256": sha256_file(frame_path),
            },
            "ap_tar_md5": {
                "size": ap_path.stat().st_size,
                "sha256": sha256_file(ap_path),
            },
            "init": init_receipt,
        }
        manifest: dict[str, Any] = {
            "schema": SCHEMA,
            "target": TARGET,
            "rung": RUNG,
            "inputs": {
                "base_magisk_boot": {
                    "size": len(base_data),
                    "sha256": EXPECTED_BASE_BOOT_SHA256,
                },
                "vendor_ramdisk": {
                    "size": VENDOR_RAMDISK_SIZE,
                    "sha256": VENDOR_RAMDISK_SHA256,
                },
                "qualified_r4w1b_image": image_pin,
                "r4w1b_reproduction_result": {
                    **repro_pin,
                    **repro_receipt,
                },
                "lz4": {
                    "size": len(lz4_data),
                    "sha256": r4w1b.LZ4_SHA256,
                },
                "magiskboot": {
                    "size": len(magiskboot_data),
                    "sha256": MAGISKBOOT_SHA256,
                },
                "source": source_receipt,
            },
            "module_closure": closure,
            "construction": {
                "carrier": "known Magisk boot with ramdisk /init replaced only",
                "kernel": "fixed-interval qualified R4W1-B Image replacement",
                "kernel_interval": [r4w1b.KERNEL_START, r4w1b.KERNEL_END],
                "patch_vbmeta_flag": False,
                "kernel_witness_preserved": construction["marker"][
                    "valid_single_exact"
                ],
                "android_header_preserved": (
                    candidate[: r4w1b.HEADER_END]
                    == carrier[: r4w1b.HEADER_END]
                ),
                "post_kernel_carrier_preserved": (
                    candidate[r4w1b.KERNEL_END :]
                    == carrier[r4w1b.KERNEL_END :]
                ),
                "ramdisk_init_mode": "0750",
                "module_binaries_injected": 0,
                "module_list_file_injected": False,
                "r4w1b_slice_checks": construction,
                "magiskboot_nochange_byte_identical": True,
                "cpio_test_before_rc": cpio_before.returncode,
                "cpio_test_after_rc": cpio_after.returncode,
                "magiskboot_unpack_pass": True,
                "magiskboot_init_replace_pass": True,
                "magiskboot_repack_pass": True,
                "boot_diff_vs_base": diff_ranges(pinned_base_boot, carrier_path),
            },
            "outputs": {**outputs, "ap_structure": ap_structure},
            "runtime_contract": {
                "finit_module_success_required": True,
                "proc_modules_eof_complete": True,
                "proc_modules_exact_set_required": True,
                "park_only_after_module_visibility_verification": True,
                "module_closure_load_and_visibility_only": True,
                "watchdog_functional_ownership_directly_proven": False,
                "watchdog_functional_proof_required": "bounded live survival",
                "failure_mode": "emit fail_closed marker and park without reboot",
                "observation_target_sec": 120,
            },
            "safety": {
                "host_only": True,
                "device_contact": False,
                "device_write": False,
                "odin_invoked": False,
                "odin_transfer": False,
                "flash": False,
                "live_authorized": False,
                "boot_only_ap": True,
                "ap_members": ["boot.img.lz4"],
                "no_android_handoff": True,
                "no_usb_or_configfs": True,
                "no_persistent_mount": True,
                "no_block_write": True,
                "no_reboot_syscall": True,
                "stale_carrier_avb_preserved": True,
                "requires_independent_static_checker": True,
                "requires_new_committed_live_policy": True,
            },
            "blockers": [
                "independent static checker not yet passed",
                "no connected read-only gate or live policy exists",
            ],
            "verdict": VERDICT,
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
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK
    )
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--repro-result", type=Path, default=DEFAULT_REPRO_RESULT)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        manifest = build(parse_args(argv))
    except (
        BuildError,
        boot_slice.BootSliceError,
        OSError,
        subprocess.SubprocessError,
        UnicodeError,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": manifest["verdict"],
                "boot_sha256": manifest["outputs"]["boot_img"]["sha256"],
                "ap_sha256": manifest["outputs"]["ap_tar_md5"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
