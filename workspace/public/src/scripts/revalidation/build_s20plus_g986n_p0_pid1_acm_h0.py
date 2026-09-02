#!/usr/bin/env python3
"""Build the dormant S20+ P0 direct-PID1 ACM first-light candidate.

This is an H0-only deterministic builder.  It preserves the exact known-good
resident kernel, DTB, boot header, command line, and partition geometry while
replacing only ramdisk ``/init`` with one freestanding AArch64 witness.  It has
no connected or live execution surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import build_s20plus_g986n_native_canary_n1 as common
import build_s20plus_n3u0_magisk_overlay as n3


ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "workspace/public/src/native-init/s20plus_p0_pid1_acm_init.c"
BASE_BOOT = n3.BASE_BOOT
MAGISKBOOT = n3.MAGISKBOOT
OBJDUMP = Path("/usr/bin/aarch64-linux-gnu-objdump")
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s20plus_g986n/p0_pid1_acm_v2"
)

SCHEMA = "s20plus_g986n_p0_pid1_acm_build_v2"
VERDICT = "PASS_S20PLUS_G986N_P0_PID1_ACM_HOST_BUILT_NOT_LIVE_AUTHORIZED"
TARGET = dict(n3.TARGET)
PROFILE = "s20plus-g986n-p0-pid1-acm-v2"
BANNER = b"S20PLUS_P0_PID1_ACM_V2;pid=00000001;stage=ACM_READY\n"
USB_PRODUCT_STRING = "S20Plus-P0-PID1"

BASE_BOOT_SIZE = n3.BASE_BOOT_SIZE
BASE_BOOT_SHA256 = n3.BASE_BOOT_SHA256
BASE_INIT_SHA256 = n3.BASE_INIT_SHA256
BASE_KERNEL_SHA256 = n3.BASE_KERNEL_SHA256
BASE_DTB_SHA256 = n3.BASE_DTB_SHA256
MAGISKBOOT_SIZE = n3.MAGISKBOOT_SIZE
MAGISKBOOT_SHA256 = n3.MAGISKBOOT_SHA256

PUBLISHED_FILES = (
    "s20plus_p0_pid1_init",
    "boot.img",
    "boot.img.lz4",
    "AP.tar.md5",
)

COMPILE_FLAGS = (
    "-std=gnu11",
    "-nostdlib",
    "-static",
    "-ffreestanding",
    "-fno-builtin",
    "-fno-tree-loop-distribute-patterns",
    "-fno-stack-protector",
    "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables",
    "-Os",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-fno-ident",
    f"-ffile-prefix-map={ROOT}=.",
    f"-fdebug-prefix-map={ROOT}=.",
    "-Wl,--build-id=none",
    "-Wl,-e,_start",
    "-Wl,-z,noexecstack",
)

EXPECTED_RUNTIME_SYSCALLS = {
    "mknodat": 33,
    "mkdirat": 34,
    "symlinkat": 36,
    "mount": 40,
    "openat": 56,
    "close": 57,
    "read": 63,
    "write": 64,
    "nanosleep": 101,
    "getpid": 172,
}

FORBIDDEN_RUNTIME_SYSCALLS = {
    "exit_group": 94,
    "reboot": 142,
    "clone": 220,
    "execve": 221,
    "finit_module": 273,
}


class BuildError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_contract() -> dict[str, Any]:
    text = common.read_regular_bytes(SOURCE, "P0 PID1 source").decode("ascii")
    required = (
        "S20+ G986N P0 direct-PID1 ACM first-light witness",
        "long pid = p0_getpid();",
        "if (pid != 1)",
        "p0_volatile_runtime()",
        "p0_mount_configfs()",
        "p0_create_gadget(&port)",
        "p0_open_acm(port)",
        "S20PLUS_P0_PID1_ACM_V2;pid=00000001;stage=ACM_READY",
        'P0_UDC "a600000.dwc3"',
        'P0_GADGET "/config/usb_gadget/s20plus_p0"',
        '"S20Plus-P0-PID1"',
        '"../../functions/acm.usb0"',
        '"/sys/class/tty/ttyGS0/dev"',
        '"/dev/ttyGS0"',
        "p0_mknod_char",
        "P0_STAGE_ACM",
        "S20PLUS_P0_SELFTEST_ONLY",
    )
    forbidden = (
        "/data/",
        "/metadata",
        "/cache",
        "/dev/block",
        "/system/",
        "/vendor/",
        "mass_storage",
        "rndis",
        "ncm.",
        "ffs.",
        '"peripheral"',
        '"/mode"',
        "system(",
        "execve(",
        "finit_module(",
        "socket(",
        "connect(",
        "fork(",
        "clone(",
        "reboot(",
    )
    missing = [token for token in required if token not in text]
    present = [token for token in forbidden if token in text]
    runtime = text.rsplit("#else", 1)[-1]
    ordered = (
        "long pid = p0_getpid();",
        "if (pid != 1)",
        "p0_volatile_runtime()",
        "p0_mount_configfs()",
        "p0_create_gadget(&port)",
        "p0_open_acm(port)",
        "p0_write_all(descriptor, P0_BANNER, P0_BANNER_SIZE)",
    )
    position = 0
    for token in ordered:
        found = runtime.find(token, position)
        if found < 0:
            missing.append(f"ordered:{token}")
            break
        position = found + len(token)
    if missing or present:
        raise BuildError(
            f"P0 source contract changed missing={missing} forbidden={present}"
        )
    return {
        "required": list(required),
        "forbidden_absent": list(forbidden),
        "runtime_order": list(ordered),
        "first_runtime_operation": "raw getpid syscall",
        "success": "exact ACM banner loop while PID1 remains resident",
        "failure": "quiet infinite park",
        "persistent_mounts": [],
        "block_devices": [],
        "caller_inputs": False,
    }


def compiler_command(output: Path, *, selftest: bool) -> list[str | Path]:
    command: list[str | Path] = [common.TOOLS["cc"], *COMPILE_FLAGS]
    if selftest:
        command.extend(
            ["-Wno-unused-function", "-DS20PLUS_P0_SELFTEST_ONLY=1"]
        )
    command.extend([SOURCE, "-o", output])
    return command


def syscall_load_present(objdump_text: str, number: int) -> bool:
    needle = f"#0x{number:x}"
    return any(
        "mov" in line
        and ("x8" in line or "w8" in line)
        and needle in line
        for line in objdump_text.splitlines()
    )


def start_first_syscall_is_getpid(objdump_text: str) -> bool:
    match = re.search(
        r"(?ms)^([0-9a-f]+) <_start>:\n(?P<body>.*?)(?=^[0-9a-f]+ <|\Z)",
        objdump_text,
    )
    if match is None:
        return False
    lines = match.group("body").splitlines()
    for index, line in enumerate(lines):
        if "svc" not in line:
            continue
        window = "\n".join(lines[max(0, index - 16) : index])
        return "x8, #0xac" in window or "w8, #0xac" in window
    return False


def compile_init(output: Path) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise BuildError("P0 init output already exists")
    selftest = output.with_name("p0-selftest")
    n3.run_command(compiler_command(selftest, selftest=True), timeout=120)
    n3.run_command([common.TOOLS["qemu"], selftest], timeout=15)
    n3.run_command(compiler_command(output, selftest=False), timeout=120)
    unstripped = n3.run_command(
        [OBJDUMP, "-d", output], timeout=30
    ).decode("ascii", errors="strict")
    if not start_first_syscall_is_getpid(unstripped):
        raise BuildError("P0 _start first syscall is not getpid")
    n3.run_command([common.TOOLS["strip"], "--strip-all", output])
    os.chmod(output, 0o700)
    audit = common.audit_elf(output)
    if audit["size"] > 16 * 1024:
        raise BuildError("P0 freestanding init exceeds 16 KiB")
    objdump = n3.run_command(
        [OBJDUMP, "-d", output], timeout=30
    ).decode("ascii", errors="strict")
    for name, number in EXPECTED_RUNTIME_SYSCALLS.items():
        if not syscall_load_present(objdump, number):
            raise BuildError(f"P0 init lacks arm64 syscall {name}={number}")
    for name, number in FORBIDDEN_RUNTIME_SYSCALLS.items():
        if syscall_load_present(objdump, number):
            raise BuildError(f"P0 runtime loads forbidden syscall {name}={number}")
    binary = common.read_regular_bytes(output, "compiled P0 init")
    for required in (
        BANNER,
        b"S20Plus-P0-PID1",
        b"a600000.dwc3",
        b"/config/usb_gadget/s20plus_p0",
        b"/functions/acm.usb0/port_num",
        b"/sys/class/tty/ttyGS0/dev",
        b"/dev/ttyGS0",
    ):
        if required not in binary:
            raise BuildError(f"compiled P0 init lacks {required!r}")
    for forbidden in (
        b"/data/",
        b"/metadata",
        b"/dev/block",
        b"/system/",
        b"peripheral",
        b"mass_storage",
        b"ffs.adb",
    ):
        if forbidden in binary:
            raise BuildError(f"compiled P0 init contains {forbidden!r}")
    return {
        **audit,
        "compile_command": [str(item) for item in compiler_command(output, selftest=False)],
        "qemu_selftest": True,
        "first_start_syscall": "getpid",
        "runtime_syscalls": dict(EXPECTED_RUNTIME_SYSCALLS),
        "forbidden_runtime_syscalls_absent": list(FORBIDDEN_RUNTIME_SYSCALLS),
    }


def ramdisk_regular_receipts(
    ramdisk: Path,
    listing: dict[str, str],
    output: Path,
    *,
    cwd: Path,
) -> dict[str, dict[str, Any]]:
    output.mkdir(mode=0o700)
    result: dict[str, dict[str, Any]] = {}
    for index, (entry, mode) in enumerate(sorted(listing.items())):
        if not mode.startswith("-"):
            continue
        extracted = output / f"entry-{index:03d}"
        n3.run_command(
            [MAGISKBOOT, "cpio", ramdisk, f"extract {entry} {extracted}"],
            cwd=cwd,
        )
        try:
            extracted_info = extracted.lstat()
        except OSError as exc:
            raise BuildError(f"P0 logical ramdisk entry is unavailable: {entry}") from exc
        if not stat.S_ISREG(extracted_info.st_mode) or extracted_info.st_nlink != 1:
            raise BuildError(f"P0 logical ramdisk entry is indirect: {entry}")
        os.chmod(extracted, 0o600, follow_symlinks=False)
        result[entry] = {
            "mode": mode,
            **common.receipt(extracted, f"P0 logical ramdisk entry {entry}"),
        }
    return result


def materialize(root: Path, init_binary: Path) -> dict[str, Any]:
    root.mkdir(mode=0o700)
    work = root / "work"
    nochange = root / "nochange"
    verify = root / "verify"
    odin = root / "odin"
    for directory in (work, nochange, verify, odin):
        directory.mkdir(mode=0o700)

    n3.run_command([MAGISKBOOT, "unpack", "-h", BASE_BOOT], cwd=nochange)
    nochange_boot = root / "boot.nochange.img"
    n3.run_command([MAGISKBOOT, "repack", BASE_BOOT, nochange_boot], cwd=nochange)
    nochange = n3.exact_receipt(
        nochange_boot,
        "P0 no-change repack",
        size=BASE_BOOT_SIZE,
        sha256=BASE_BOOT_SHA256,
    )

    unpack_output = n3.run_command([MAGISKBOOT, "unpack", "-h", BASE_BOOT], cwd=work)
    ramdisk = work / "ramdisk.cpio"
    kernel = work / "kernel"
    dtb = work / "dtb"
    header = work / "header"
    n3.exact_receipt(kernel, "P0 base kernel", sha256=BASE_KERNEL_SHA256)
    n3.exact_receipt(dtb, "P0 base DTB", sha256=BASE_DTB_SHA256)
    header_before = n3.exact_receipt(header, "P0 base header")

    original_init = verify / "init.before"
    n3.run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"extract init {original_init}"], cwd=work
    )
    n3.exact_receipt(original_init, "P0 original Magisk init", sha256=BASE_INIT_SHA256)
    before_rc, before_bytes = n3.cpio_result(ramdisk, "ls -r /", cwd=work)
    if before_rc != 0:
        raise BuildError("P0 base ramdisk listing failed")
    listing_before = n3.parse_cpio_listing(before_bytes)
    if listing_before.get("init") != "-rwxr-x---":
        raise BuildError("P0 base init metadata changed")
    ramdisk_before = verify / "ramdisk.before.cpio"
    shutil.copyfile(ramdisk, ramdisk_before)
    logical_before = ramdisk_regular_receipts(
        ramdisk, listing_before, verify / "logical-before", cwd=work
    )

    n3.run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"add 750 init {init_binary}"], cwd=work
    )
    after_rc, after_bytes = n3.cpio_result(ramdisk, "ls -r /", cwd=work)
    if after_rc != 0:
        raise BuildError("P0 patched ramdisk listing failed")
    listing_after = n3.parse_cpio_listing(after_bytes)
    if listing_after != listing_before:
        raise BuildError("P0 ramdisk membership or metadata changed beyond init bytes")
    logical_after = ramdisk_regular_receipts(
        ramdisk, listing_after, verify / "logical-after", cwd=work
    )
    retained_before = {
        entry: value for entry, value in logical_before.items() if entry != "init"
    }
    retained_after = {
        entry: value for entry, value in logical_after.items() if entry != "init"
    }
    if retained_after != retained_before:
        raise BuildError("P0 non-init logical ramdisk bytes changed")
    if logical_before["init"] == logical_after["init"]:
        raise BuildError("P0 logical init bytes did not change")
    extracted_init = verify / "init.after"
    n3.run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"extract init {extracted_init}"], cwd=work
    )
    if common.read_regular_bytes(extracted_init, "P0 extracted init") != common.read_regular_bytes(
        init_binary, "P0 source init"
    ):
        raise BuildError("P0 ramdisk init bytes changed")
    ramdisk_after = verify / "ramdisk.after.cpio"
    shutil.copyfile(ramdisk, ramdisk_after)

    boot_img = root / "boot.img"
    repack_output = n3.run_command([MAGISKBOOT, "repack", BASE_BOOT, boot_img], cwd=work)
    n3.exact_receipt(boot_img, "P0 candidate boot", size=BASE_BOOT_SIZE)
    patched = root / "patched"
    patched.mkdir(mode=0o700)
    n3.run_command([MAGISKBOOT, "unpack", "-h", boot_img], cwd=patched)
    n3.exact_receipt(patched / "kernel", "P0 patched kernel", sha256=BASE_KERNEL_SHA256)
    n3.exact_receipt(patched / "dtb", "P0 patched DTB", sha256=BASE_DTB_SHA256)
    if n3.exact_receipt(patched / "header", "P0 patched header") != header_before:
        raise BuildError("P0 patched boot header changed")
    patched_init = verify / "init.patched"
    n3.run_command(
        [
            MAGISKBOOT,
            "cpio",
            patched / "ramdisk.cpio",
            f"extract init {patched_init}",
        ],
        cwd=patched,
    )
    if common.read_regular_bytes(patched_init, "P0 repacked init") != common.read_regular_bytes(
        init_binary, "P0 expected init"
    ):
        raise BuildError("P0 repacked boot init differs")
    patched_rc, patched_bytes = n3.cpio_result(
        patched / "ramdisk.cpio", "ls -r /", cwd=patched
    )
    if patched_rc != 0 or n3.parse_cpio_listing(patched_bytes) != listing_before:
        raise BuildError("P0 repacked ramdisk membership changed")
    logical_patched = ramdisk_regular_receipts(
        patched / "ramdisk.cpio",
        listing_before,
        verify / "logical-patched",
        cwd=patched,
    )
    if logical_patched != logical_after:
        raise BuildError("P0 repacked logical ramdisk bytes changed")

    boot_lz4 = odin / "boot.img.lz4"
    n3.boot_prep.lz4_roundtrip(boot_img, boot_lz4, odin / ".roundtrip.img")
    ap = odin / "AP.tar.md5"
    ap_state = n3.boot_prep.write_boot_ap(boot_lz4, ap)
    if ap_state["members"] != ["boot.img.lz4"]:
        raise BuildError("P0 AP is not boot-only")
    return {
        "paths": {
            "init": init_binary,
            "boot.img": boot_img,
            "boot.img.lz4": boot_lz4,
            "AP.tar.md5": ap,
        },
        "receipts": {
            "init": common.receipt(init_binary, "P0 materialized init"),
            "boot.img": common.receipt(boot_img, "P0 materialized boot"),
            "boot.img.lz4": common.receipt(boot_lz4, "P0 materialized boot lz4"),
            "AP.tar.md5": common.receipt(ap, "P0 materialized AP"),
            "ramdisk_before": common.receipt(ramdisk_before, "P0 ramdisk before"),
            "ramdisk_after": common.receipt(ramdisk_after, "P0 ramdisk after"),
        },
        "nochange": nochange,
        "listing": listing_before,
        "retained_regular_entries": retained_before,
        "unpack_output_sha256": sha256_bytes(unpack_output),
        "repack_output_sha256": sha256_bytes(repack_output),
        "ap": ap_state,
    }


def publish_file(source: Path, destination: Path, mode: int) -> None:
    common.publish_bytes_no_clobber(
        destination,
        common.read_regular_bytes(source, f"P0 publish source {source.name}"),
        mode,
    )


def build(out_dir: Path) -> dict[str, Any]:
    if out_dir.is_symlink():
        raise BuildError("P0 output directory is indirect")
    out_dir = out_dir.resolve(strict=False)
    if out_dir.exists() or out_dir.is_symlink():
        raise BuildError("P0 output directory exists; refusing to clobber it")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    base = n3.exact_receipt(
        BASE_BOOT,
        "P0 resident Magisk base boot",
        size=BASE_BOOT_SIZE,
        sha256=BASE_BOOT_SHA256,
    )
    magiskboot = n3.exact_receipt(
        MAGISKBOOT,
        "P0 Magisk v30.7 magiskboot",
        size=MAGISKBOOT_SIZE,
        sha256=MAGISKBOOT_SHA256,
    )
    contract = source_contract()
    sources = {
        "init": common.receipt(SOURCE, "P0 init source"),
        "builder": common.receipt(Path(__file__).resolve(), "P0 builder"),
        "common_h0_builder": common.receipt(
            Path(common.__file__).resolve(), "P0 common builder"
        ),
        "n3_builder_helper": common.receipt(
            Path(n3.__file__).resolve(), "P0 N3 helper"
        ),
        "boot_prep_helper": common.receipt(
            Path(n3.boot_prep.__file__).resolve(), "P0 boot prep helper"
        ),
    }
    tools = common.tool_receipts()
    tools["objdump"] = common.receipt(OBJDUMP, "AArch64 objdump")
    compiler = common.compiler_closure()

    with tempfile.TemporaryDirectory(
        prefix=".s20plus-p0-a-", dir=out_dir.parent
    ) as first_name, tempfile.TemporaryDirectory(
        prefix=".s20plus-p0-b-", dir=out_dir.parent
    ) as second_name:
        first_root = Path(first_name)
        second_root = Path(second_name)
        first_init = first_root / "s20plus_p0_pid1_init"
        second_init = second_root / "s20plus_p0_pid1_init"
        first_audit = compile_init(first_init)
        second_audit = compile_init(second_init)
        if first_init.read_bytes() != second_init.read_bytes():
            raise BuildError("two P0 init builds are not byte-identical")
        first = materialize(first_root / "artifact", first_init)
        second = materialize(second_root / "artifact", second_init)
        if first["receipts"] != second["receipts"]:
            raise BuildError("two complete P0 builds differ")
        for name in PUBLISHED_FILES:
            key = "init" if name == "s20plus_p0_pid1_init" else name
            if first["paths"][key].read_bytes() != second["paths"][key].read_bytes():
                raise BuildError(f"two P0 outputs differ: {name}")

        out_dir.mkdir(mode=0o700)
        common.fsync_directory(out_dir.parent)
        publish_file(first_init, out_dir / "s20plus_p0_pid1_init", 0o700)
        publish_file(first["paths"]["boot.img"], out_dir / "boot.img", 0o600)
        publish_file(first["paths"]["boot.img.lz4"], out_dir / "boot.img.lz4", 0o600)
        publish_file(first["paths"]["AP.tar.md5"], out_dir / "AP.tar.md5", 0o600)

    outputs = {
        name: common.receipt(out_dir / name, f"published P0 {name}")
        for name in PUBLISHED_FILES
    }
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "tier": "H0",
        "review_state": "REVIEW_PENDING",
        "live_authority": False,
        "target": TARGET,
        "profile": PROFILE,
        "base_boot": base,
        "base_boot_role": "known-good resident Magisk boot; offline input only",
        "magiskboot": magiskboot,
        "tools": tools,
        "compiler_closure": compiler,
        "sources": sources,
        "source_contract": contract,
        "compile_flags": list(COMPILE_FLAGS),
        "binary_audit": first_audit,
        "reproduction_binary_audit": second_audit,
        "outputs": outputs,
        "observer_contract": {
            "usb_vendor": "04e8",
            "usb_product": "6861",
            "manufacturer": "Samsung",
            "product_string": USB_PRODUCT_STRING,
            "serial_descriptor": False,
            "banner_hex": BANNER.hex(),
            "banner_sha256": sha256_bytes(BANNER),
            "banner_size": len(BANNER),
            "pid_value_derived_from_first_getpid_gate": True,
        },
        "ramdisk": {
            "added_entries": [],
            "removed_entries": [],
            "replaced_entries": ["init"],
            "entry_metadata_changed": False,
            "original_magisk_init_sha256": BASE_INIT_SHA256,
            "other_base_entries_retained_but_not_executed": True,
            "logical_regular_entries_exact": True,
            "retained_regular_entries": sorted(first["retained_regular_entries"]),
            "retained_regular_entries_sha256": sha256_bytes(
                json.dumps(
                    first["retained_regular_entries"],
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            ),
        },
        "safety": {
            "host_only_build": True,
            "boot_only_output": True,
            "tar_members": ["boot.img.lz4"],
            "base_nochange_repack_byte_identical": True,
            "kernel_preserved": True,
            "dtb_preserved": True,
            "header_preserved": True,
            "ramdisk_init_replaced": True,
            "global_pid1_candidate": True,
            "android_started": False,
            "magisk_started": False,
            "persistent_partition_mount": False,
            "persistent_write": False,
            "block_device_access": False,
            "module_insertion": False,
            "network_function": False,
            "storage_function": False,
            "mode_peripheral_write": False,
            "reboot_syscall": False,
            "panic_or_watchdog": False,
            "odin_invoked": False,
            "device_contact": False,
        },
        "reproducibility": {
            "two_init_builds_byte_identical": True,
            "two_complete_artifact_builds_byte_identical": True,
        },
        "device_commands": 0,
        "adb_commands": 0,
        "su_commands": 0,
        "reboot_commands": 0,
        "odin_commands": 0,
        "partition_transfers": 0,
    }
    manifest_bytes = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    common.publish_bytes_no_clobber(out_dir / "manifest.json", manifest_bytes, 0o600)
    common.fsync_directory(out_dir)
    result["manifest"] = common.receipt(out_dir / "manifest.json", "P0 manifest")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = build(args.out_dir)
    except (
        BuildError,
        common.BuildError,
        n3.BuildError,
        OSError,
        subprocess.SubprocessError,
    ) as error:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "REJECTED", "error": str(error)},
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
