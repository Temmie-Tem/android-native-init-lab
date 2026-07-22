#!/usr/bin/env python3
"""Independently validate the P2.41 E2 profile-3 host implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPT_DIR))

import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p232_e1_latest_stage_design as model  # noqa: E402
import s22plus_fyg8_p233_e1_static_checker as p233  # noqa: E402
import s22plus_fyg8_p241_dtbo_role_contract as dtbo  # noqa: E402
import s22plus_fyg8_r4w1b_candidate_static_checker as base_static  # noqa: E402
import s22plus_o2_module_plan as planner  # noqa: E402


SCHEMA = "s22plus_fyg8_p241_e2_static_checker_v1"
VERDICT = "PASS_P241_E2_SOURCE_IMPLEMENTATION_HOST_ONLY"
TARGET = model.TARGET
PROFILE = "E2"
PROFILE_NUMBER = 3
RUN_ID = hashlib.sha256(b"S22PLUS-FYG8-P241-E2-SOURCE-CHECK-V1").digest()[:16]

DEFAULT_SOURCE = p233.DEFAULT_SOURCE
DEFAULT_PATCH = Path(
    "workspace/public/src/patches/s22plus_fyg8_p241_e2_latest_stage.patch"
)
DEFAULT_CLIENT = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p241_checkpoint.c"
)
DEFAULT_RUNTIME = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p241_e2_runtime.c"
)
DEFAULT_PLAN_HEADER = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p241_e2_plan.h"
)
DEFAULT_CHILD = p233.DEFAULT_CHILD
DEFAULT_VENDOR_RAMDISK = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/vendor_ramdisk00"
)
DEFAULT_LZ4 = base_static.DEFAULT_LZ4
EXPECTED_VENDOR_RAMDISK_SIZE = 21_813_545
EXPECTED_VENDOR_RAMDISK_SHA256 = (
    "41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193"
)
EXPECTED_VENDOR_NEWC_SIZE = 63_974_144
EXPECTED_VENDOR_ENTRY_COUNT = 452


class CheckError(ValueError):
    pass


def repo_root() -> Path:
    return p233.repo_root()


def resolve(root: Path, path: Path) -> Path:
    return p233.resolve(root, path)


def receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def stable_read(path: Path, label: str, limit: int) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise CheckError(f"{label} unavailable: {path}") from exc
    if path.is_symlink() or not path.is_file() or not 0 < before.st_size <= limit:
        raise CheckError(f"{label} is indirect, empty, or outside bound")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
    )
    if identity(before) != identity(after) or len(data) != before.st_size:
        raise CheckError(f"{label} changed while reading")
    return data


def ascii_text(data: bytes, label: str) -> str:
    try:
        return data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise CheckError(f"{label} is not ASCII") from exc


def audit_plan(
    metadata_dir: Path, header_data: bytes
) -> tuple[planner.ModuleMetadata, planner.ModulePlan, dict[str, Any]]:
    metadata = planner.load_metadata(metadata_dir)
    planner.verify_fyg8_pins(metadata)
    plan = planner.build_e2_profile_plan(metadata)
    planner.validate_plan_contract(metadata, plan)
    planner.verify_e2_profile_plan_identity(metadata, plan)
    expected_header = planner.render_plan_header(metadata, plan).replace(
        "S22PLUS_O2_MODULE_PLAN_GENERATED_H",
        "S22PLUS_FYG8_P241_E2_PLAN_H",
    )
    if header_data != expected_header.encode("ascii"):
        raise CheckError("tracked E2 plan header differs from fresh metadata derivation")
    positions = {module: index for index, module in enumerate(plan.modules)}
    violations = [
        row
        for row in plan.constraints
        if positions[row["before"]] >= positions[row["after"]]
    ]
    if violations:
        raise CheckError(f"E2 dependency order violation: {violations}")
    return metadata, plan, {
        "module_count": len(plan.modules),
        "constraint_count": len(plan.constraints),
        "tsv_sha256": planner.sha256_text(planner.render_plan_tsv(metadata, plan)),
        "header": receipt(header_data),
        "foundation": list(planner.E2_PROVEN_E1B_FOUNDATION),
        "options_file_present": metadata.options_file_present,
        "orphan_options": list(metadata.orphan_options),
        "verified": True,
    }


def audit_patch(source: Path, patch: Path, data: bytes) -> dict[str, Any]:
    text = ascii_text(data, "P2.41 kernel patch")
    p233.run_checked(
        ["git", "apply", "--check", "--unsafe-paths", str(patch)],
        cwd=source,
        label="P2.41 clean-apply check",
    )
    required = (
        "range 1 3",
        "S22_FYG8_E1_PROFILE_E2",
        "s22_fyg8_e2_sequence",
        "0x78, 0x79, 0x7a, 0x7b",
        "0x80, 0x81, 0x82, 0x8f",
        "request->stage >= 0x40 && request->stage <= 0x7a",
        "request->stage >= 0x7b && request->stage <= 0x82",
        "CONFIG_S22PLUS_FYG8_E1_PROFILE != S22_FYG8_E1_PROFILE_E2",
        "proc_create(\"s22_checkpoint\", 0200",
        "__flush_dcache_area",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise CheckError(f"P2.41 patch contract missing: {missing}")
    forbidden = (
        "kernel_restart(",
        "emergency_restart(",
        "panic(",
        "call_usermodehelper(",
        "sec_log_buf.ko",
        "head->idx =",
        "head->magic =",
        "head->boot_cnt =",
    )
    present = [token for token in forbidden if token in text]
    if present:
        raise CheckError(f"P2.41 patch contains forbidden behavior: {present}")
    sequence_match = re.search(
        r"s22_fyg8_e2_sequence\[\]\s*=\s*\{(?P<body>.*?)\};",
        text,
        re.DOTALL,
    )
    if sequence_match is None:
        raise CheckError("P2.41 kernel E2 sequence is absent")
    values = tuple(
        int(value, 16)
        for value in re.findall(r"0x([0-9a-fA-F]+)", sequence_match.group("body"))
    )
    if values != model.PROFILE_STAGE_SEQUENCES[PROFILE]:
        raise CheckError("P2.41 kernel E2 sequence differs from the host model")
    return {
        **receipt(data),
        "clean_apply": True,
        "sequence_count": len(values),
        "terminal": values[-1],
        "default_disabled": True,
        "verified": True,
    }


def audit_sources(client_data: bytes, runtime_data: bytes) -> dict[str, Any]:
    client = ascii_text(client_data, "P2.41 checkpoint client")
    runtime = ascii_text(runtime_data, "P2.41 E2 runtime")
    required_client = (
        "S22PLUS_FYG8_P233_PROFILE < 1 || S22PLUS_FYG8_P233_PROFILE > 3",
        "S22_P241_STAGE_E2_MODULE_0 0x40U",
        "S22_P241_STAGE_E2_GATE_7 0x82U",
        "S22_P241_STAGE_E2_SUCCESS 0x8fU",
        'sys_openat("/proc/s22_checkpoint"',
    )
    required_runtime = (
        '#include "s22plus_r4w1e_e1_runtime.c"',
        '#include "s22plus_fyg8_p241_e2_plan.h"',
        '#include "s22plus_o2_loader_core.h"',
        "S22PLUS_O2_MODULE_PLAN_COUNT == 59U",
        "p241_finit_module",
        "p241_verify_module_prefix(index + 1U)",
        "scan.lines_seen != count",
        "AT_SYMLINK_NOFOLLOW",
        "p241_readlinkat",
        "p241_check_udc",
        "S22_P241_GATE_TIMEOUT_SEC 20LL",
        "S22_P241_GATE_POLL_NS 100000000LL",
        "s22_r4w1e_checkpoint_success(&g_checkpoint)",
    )
    missing = [token for token in required_client if token not in client]
    missing += [token for token in required_runtime if token not in runtime]
    if missing:
        raise CheckError(f"P2.41 source contract missing: {missing}")
    forbidden = (
        "sec_log_buf.ko",
        "/dev/block",
        "/config/usb_gadget",
        "kernel_restart",
        "emergency_restart",
        "SYS_reboot",
    )
    present = [token for token in forbidden if token in client + runtime]
    if present:
        raise CheckError(f"P2.41 source contains forbidden authority: {present}")
    operations = (
        "mount_proc()",
        "mount_sys()",
        "mount_dev()",
        "mount_run()",
        "setup_and_verify_dev_null()",
        "child_start(&child)",
        "child_verify_token(&child)",
        "child_reap(&child)",
        "p241_load_and_verify_module(index)",
        "p241_check_gate(index)",
        "s22_r4w1e_checkpoint_success(&g_checkpoint)",
    )
    positions = [runtime.find(value) for value in operations]
    if any(value < 0 for value in positions) or positions != sorted(positions):
        raise CheckError("P2.41 terminal is not dominated by the required operations")
    return {
        "client": receipt(client_data),
        "runtime": receipt(runtime_data),
        "operation_count": len(operations),
        "module_prefix_checked_after_each_load": True,
        "eexist_rejected": True,
        "read_only_gate_phase": True,
        "terminal_dominance_verified": True,
        "verified": True,
    }


def audit_vendor_modules(
    root: Path,
    vendor_ramdisk_path: Path,
    lz4_path: Path,
    plan: planner.ModulePlan,
) -> dict[str, Any]:
    compressed = stable_read(
        vendor_ramdisk_path, "FYG8 vendor ramdisk", 128 * 1024 * 1024
    )
    if (
        len(compressed) != EXPECTED_VENDOR_RAMDISK_SIZE
        or hashlib.sha256(compressed).hexdigest() != EXPECTED_VENDOR_RAMDISK_SHA256
    ):
        raise CheckError("FYG8 vendor ramdisk identity mismatch")
    lz4 = stable_read(lz4_path, "pinned lz4", 1024 * 1024)
    if (
        len(lz4) != base_static.LZ4_SIZE
        or hashlib.sha256(lz4).hexdigest() != base_static.LZ4_SHA256
    ):
        raise CheckError("pinned lz4 identity mismatch")
    cpio = boot_verify.decompress_lz4(lz4_path, compressed)
    if len(cpio) != EXPECTED_VENDOR_NEWC_SIZE:
        raise CheckError(f"vendor newc size mismatch: {len(cpio)}")
    entries = boot_verify.parse_newc(cpio)
    if len(entries) != EXPECTED_VENDOR_ENTRY_COUNT:
        raise CheckError(f"vendor newc entry count mismatch: {len(entries)}")
    by_name: dict[str, boot_verify.CpioEntry] = {}
    for entry in entries:
        if entry.name in by_name:
            raise CheckError(f"duplicate vendor newc entry: {entry.name}")
        by_name[entry.name] = entry
    rows: list[dict[str, Any]] = []
    for index, module in enumerate(plan.modules):
        path = f"lib/modules/{module}"
        entry = by_name.get(path)
        if entry is None or entry.file_type != "regular":
            raise CheckError(f"exact E2 vendor module missing or non-regular: {module}")
        if b"request_firmware" in entry.data:
            raise CheckError(f"E2 module has firmware-class string: {module}")
        rows.append(
            {
                "index": index,
                "file": module,
                "runtime_name": planner.normalize_module_name(module),
                **receipt(entry.data),
            }
        )
    if any(row["file"] == "sec_log_buf.ko" for row in rows):
        raise CheckError("forbidden sec_log_buf entered the E2 module closure")
    return {
        "vendor_ramdisk": receipt(compressed),
        "decompressed_newc_size": len(cpio),
        "entry_count": len(entries),
        "modules": rows,
        "module_count": len(rows),
        "request_firmware_string_hits": 0,
        "sec_log_buf_absent": True,
        "verified": True,
    }


def compile_runtime(
    root: Path, runtime: Path, client: Path, child: Path
) -> dict[str, Any]:
    tools = {
        name: shutil.which(name)
        for name in (
            "aarch64-linux-gnu-gcc",
            "aarch64-linux-gnu-readelf",
            "aarch64-linux-gnu-nm",
            "aarch64-linux-gnu-objdump",
            "file",
            "qemu-aarch64",
        )
    }
    missing = [name for name, path in tools.items() if path is None]
    if missing:
        raise CheckError(f"P2.41 required host tools missing: {missing}")
    include = root / "workspace/public/src/native-init"
    flags = list(p233.legacy_e1.COMPILE_FLAGS)
    with tempfile.TemporaryDirectory(prefix="s22-p241-e2-static-") as name:
        directory = Path(name)
        init = directory / "init"
        child_output = directory / "s22-e1-child"
        define = p233._run_id_define(RUN_ID)
        p233.run_checked(
            [
                str(tools["aarch64-linux-gnu-gcc"]),
                *flags,
                f"-DS22PLUS_FYG8_P233_PROFILE={PROFILE_NUMBER}",
                f"-DS22PLUS_FYG8_P233_RUN_ID_BYTES={define}",
                "-I",
                str(include),
                str(runtime),
                str(client),
                "-o",
                str(init),
            ],
            cwd=root,
            label="P2.41 E2 cross-link",
        )
        p233.run_checked(
            [
                str(tools["aarch64-linux-gnu-gcc"]),
                *flags,
                str(child),
                "-o",
                str(child_output),
            ],
            cwd=root,
            label="P2.41 child cross-link",
        )
        init_data = init.read_bytes()
        child_data = child_output.read_bytes()
        file_text = p233.run_checked(
            [str(tools["file"]), "-b", str(init)],
            cwd=root,
            label="P2.41 file inspection",
        ).stdout.decode("ascii", "replace").strip()
        readelf = p233.run_checked(
            [str(tools["aarch64-linux-gnu-readelf"]), "-W", "-h", "-l", str(init)],
            cwd=root,
            label="P2.41 readelf inspection",
        ).stdout.decode("ascii", "replace")
        symbols = p233.run_checked(
            [str(tools["aarch64-linux-gnu-nm"]), "-n", str(init)],
            cwd=root,
            label="P2.41 symbol inspection",
        ).stdout.decode("ascii", "replace")
        undefined = p233.run_checked(
            [str(tools["aarch64-linux-gnu-nm"]), "-u", str(init)],
            cwd=root,
            label="P2.41 undefined-symbol inspection",
        ).stdout
        disassembly = p233.run_checked(
            [str(tools["aarch64-linux-gnu-objdump"]), "-d", str(init)],
            cwd=root,
            label="P2.41 disassembly inspection",
        ).stdout.decode("ascii", "replace")
        stack = [line for line in readelf.splitlines() if "GNU_STACK" in line]
        if (
            "ELF 64-bit LSB executable, ARM aarch64" not in file_text
            or "statically linked" not in file_text
            or "INTERP" in readelf
            or "DYNAMIC" in readelf
            or len(stack) != 1
            or " RWE " in stack[0]
            or undefined.strip()
            or len(re.findall(r"\bT _start$", symbols, re.MULTILINE)) != 1
            or "svc" not in disassembly
            or init_data.count(RUN_ID) != 1
        ):
            raise CheckError("P2.41 E2 linked ELF contract mismatch")
        required_binary = (
            b"/proc/s22_checkpoint",
            b"/proc/modules",
            b"/sys/class/udc",
            b"a600000.dwc3",
            b"/s22-e1-child",
            p233.legacy_e1.CHILD_TOKEN,
        )
        if any(value not in init_data for value in required_binary):
            raise CheckError("P2.41 E2 linked runtime string closure mismatch")
        child_run = subprocess.run(
            [str(tools["qemu-aarch64"]), str(child_output)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        if (
            child_run.returncode != 23
            or child_run.stdout != p233.legacy_e1.CHILD_TOKEN
            or child_run.stderr
        ):
            raise CheckError("P2.41 child token/exit behavior mismatch")
        result = {
            "init": {
                **receipt(init_data),
                "file": file_text,
                "static_aarch64": True,
                "undefined_symbols": 0,
                "svc_present": True,
                "run_id_count": 1,
            },
            "child": {
                **receipt(child_data),
                "qemu_exit": child_run.returncode,
                "token_exact": True,
            },
        }
    return result


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    paths = {
        "source": resolve(root, args.source),
        "patch": resolve(root, args.patch),
        "client": resolve(root, args.client),
        "runtime": resolve(root, args.runtime),
        "plan_header": resolve(root, args.plan_header),
        "child": resolve(root, args.child),
        "vendor_ramdisk": resolve(root, args.vendor_ramdisk),
        "lz4": resolve(root, args.lz4),
    }
    tracked = {
        name: stable_read(path, name, 2 * 1024 * 1024)
        for name, path in paths.items()
        if name in {"patch", "client", "runtime", "plan_header", "child"}
    }
    metadata, plan, plan_audit = audit_plan(
        resolve(root, planner.DEFAULT_METADATA_DIR), tracked["plan_header"]
    )
    if metadata.options_file_present or metadata.orphan_options:
        raise CheckError("E2 module options state is not empty")
    reachable = p233.validate_reachable_records({PROFILE: RUN_ID})
    if reachable["reachable_slot_variants"] != 307_201:
        raise CheckError("E2 reachable slot count mismatch")
    e1_regression = p233.validate_reachable_records(p233.SOURCE_CHECK_RUN_IDS)
    if e1_regression["reachable_slot_variants"] != 90_114:
        raise CheckError("E1A/E1B reachable identity regression")
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "profile": PROFILE,
        "profile_number": PROFILE_NUMBER,
        "run_id": RUN_ID.hex(),
        "plan": plan_audit,
        "patch": audit_patch(paths["source"], paths["patch"], tracked["patch"]),
        "sources": audit_sources(tracked["client"], tracked["runtime"]),
        "vendor_rootfs": audit_vendor_modules(
            root, paths["vendor_ramdisk"], paths["lz4"], plan
        ),
        "linked_userspace": compile_runtime(
            root, paths["runtime"], paths["client"], paths["child"]
        ),
        "reachable_record_contract": reachable,
        "e1a_e1b_regression": e1_regression,
        "dtbo_role_contract": dtbo.build_result(),
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "image_built": False,
            "candidate_created": False,
            "manifest_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
            "sysfs_write": False,
            "configfs_write": False,
        },
        "next": "separate reproducible Full-LTO candidate build and offline closure",
    }
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--client", type=Path, default=DEFAULT_CLIENT)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--plan-header", type=Path, default=DEFAULT_PLAN_HEADER)
    parser.add_argument("--child", type=Path, default=DEFAULT_CHILD)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        result = build_result(parse_args(argv))
    except (
        CheckError,
        model.DesignError,
        planner.PlanError,
        dtbo.ContractError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
