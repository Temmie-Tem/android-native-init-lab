#!/usr/bin/env python3
"""Build the dormant S20+ P0 direct-PID1 minimal download-request candidate (V4).

H0-only deterministic builder with no connected or live execution surface.

It reuses the ACM candidate builder's proven materialisation path unchanged -
same stock base boot, same magiskboot, same no-change repack proof, same
boot-only AP - and replaces only the freestanding ``/init`` it installs.

The candidate is a *reduction* of the consumed ACM candidate, so this builder
proves the reduction mechanically: the compiled binary must contain the download
request and must NOT contain any configfs, gadget, UDC or ttyGS0 string that the
ACM candidate depended on. A candidate that quietly regained that chain would
fail the build rather than reach the device.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import build_s20plus_g986n_native_canary_n1 as common
import build_s20plus_n3u0_magisk_overlay as n3
import build_s20plus_g986n_p0_pid1_acm_h0 as acm


ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "workspace/public/src/native-init/s20plus_p0_pid1_min_init.c"
DEFAULT_OUTPUT = ROOT / "workspace/private/outputs/s20plus_g986n/p0_pid1_min_v4"

SCHEMA = "s20plus_g986n_p0_pid1_min_build_v4"
VERDICT = "PASS_S20PLUS_G986N_P0_PID1_MIN_HOST_BUILT_NOT_LIVE_AUTHORIZED"
PROFILE = "s20plus-g986n-p0-pid1-min-v4"
BANNER = b"S20PLUS_P0_PID1_MIN_V4;pid=00000001;stage=DOWNLOAD_REQUEST\n"

BASE_BOOT = acm.BASE_BOOT
MAGISKBOOT = acm.MAGISKBOOT
OBJDUMP = acm.OBJDUMP
INIT_NAME = "s20plus_p0_pid1_min_init"
PUBLISHED_FILES = (INIT_NAME, "boot.img", "boot.img.lz4", "AP.tar.md5")

# The complete runtime surface. getpid gates on PID1; mkdirat/mknodat/openat/
# write/close are the best-effort banner; nanosleep is the park; reboot is the
# evidence. Nothing else may appear.
EXPECTED_RUNTIME_SYSCALLS = {
    "mknodat": 33,
    "mkdirat": 34,
    "openat": 56,
    "close": 57,
    "write": 64,
    "nanosleep": 101,
    "reboot": 142,
    "getpid": 172,
}

# exit_group would let PID1 terminate, which the kernel turns into a panic.
# The ACM candidate's syscalls are forbidden here because their absence is what
# makes this the minimal probe.
FORBIDDEN_RUNTIME_SYSCALLS = {
    "exit_group": 94,
    "mount": 40,
    "symlinkat": 36,
    "read": 63,
}

REQUIRED_STRINGS = (BANNER.rstrip(b"\n"), b"/dev/kmsg", b"download")

# Every one of these is a string the consumed ACM candidate carried. Their
# absence is the mechanical proof that the gadget chain is gone.
FORBIDDEN_STRINGS = (
    b"a600000.dwc3",
    b"/sys/class/udc",
    b"/config/usb_gadget",
    b"acm.usb0",
    b"port_num",
    b"/sys/class/tty/ttyGS0/dev",
    b"/dev/ttyGS0",
    b"S20Plus-P0-PID1",
    b"configfs",
)


class BuildError(RuntimeError):
    pass


def compiler_command(output: Path, *, selftest: bool) -> list[str | Path]:
    command: list[str | Path] = [common.TOOLS["cc"], *acm.COMPILE_FLAGS]
    if selftest:
        command.extend(["-Wno-unused-function", "-DS20PLUS_P0_MIN_SELFTEST_ONLY=1"])
    command.extend([SOURCE, "-o", output])
    return command


def compile_init(output: Path) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise BuildError("P0 minimal init output already exists")
    selftest = output.with_name("p0-min-selftest")
    n3.run_command(compiler_command(selftest, selftest=True), timeout=120)
    n3.run_command([common.TOOLS["qemu"], selftest], timeout=15)
    n3.run_command(compiler_command(output, selftest=False), timeout=120)
    unstripped = n3.run_command([OBJDUMP, "-d", output], timeout=30).decode("ascii", errors="strict")
    if not acm.start_first_syscall_is_getpid(unstripped):
        raise BuildError("P0 minimal _start first syscall is not getpid")
    n3.run_command([common.TOOLS["strip"], "--strip-all", output])
    os.chmod(output, 0o700)
    audit = common.audit_elf(output)
    if audit["size"] > 4 * 1024:
        raise BuildError("P0 minimal init exceeds 4 KiB")
    objdump = n3.run_command([OBJDUMP, "-d", output], timeout=30).decode("ascii", errors="strict")
    for name, number in EXPECTED_RUNTIME_SYSCALLS.items():
        if not acm.syscall_load_present(objdump, number):
            raise BuildError(f"P0 minimal init lacks arm64 syscall {name}={number}")
    for name, number in FORBIDDEN_RUNTIME_SYSCALLS.items():
        if acm.syscall_load_present(objdump, number):
            raise BuildError(f"P0 minimal init loads forbidden syscall {name}={number}")
    binary = common.read_regular_bytes(output, "compiled P0 minimal init")
    for required in REQUIRED_STRINGS:
        if required not in binary:
            raise BuildError(f"compiled P0 minimal init lacks {required!r}")
    for forbidden in FORBIDDEN_STRINGS:
        if forbidden in binary:
            raise BuildError(f"P0 minimal init retains ACM-chain string {forbidden!r}")
    return {
        **audit,
        **common.receipt(output, "P0 minimal init binary"),
        "expected_syscalls": dict(EXPECTED_RUNTIME_SYSCALLS),
        "forbidden_syscalls_absent": sorted(FORBIDDEN_RUNTIME_SYSCALLS),
        "acm_chain_strings_absent": True,
        "selftest_passed": True,
    }


def build(out_dir: Path) -> dict[str, Any]:
    if out_dir.is_symlink():
        raise BuildError("P0 minimal output directory is indirect")
    out_dir = out_dir.resolve(strict=False)
    if out_dir.exists() or out_dir.is_symlink():
        raise BuildError("P0 minimal output directory exists; refusing to clobber it")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    base = n3.exact_receipt(BASE_BOOT, "P0 resident Magisk base boot", size=acm.BASE_BOOT_SIZE, sha256=acm.BASE_BOOT_SHA256)
    magiskboot = n3.exact_receipt(MAGISKBOOT, "P0 Magisk v30.7 magiskboot", size=acm.MAGISKBOOT_SIZE, sha256=acm.MAGISKBOOT_SHA256)
    sources = {
        "init": common.receipt(SOURCE, "P0 minimal init source"),
        "builder": common.receipt(Path(__file__).resolve(), "P0 minimal builder"),
        "acm_builder_reused": common.receipt(Path(acm.__file__).resolve(), "P0 ACM builder reused for materialisation"),
        "common_h0_builder": common.receipt(Path(common.__file__).resolve(), "P0 common builder"),
        "n3_builder_helper": common.receipt(Path(n3.__file__).resolve(), "P0 N3 helper"),
    }
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        init_binary = work / INIT_NAME
        init_receipt = compile_init(init_binary)
        # Byte-identical rebuild, as the ACM builder requires of itself.
        again = work / (INIT_NAME + ".again")
        n3.run_command(compiler_command(again, selftest=False), timeout=120)
        n3.run_command([common.TOOLS["strip"], "--strip-all", again])
        if common.read_regular_bytes(again, "P0 minimal init rebuild") != common.read_regular_bytes(init_binary, "P0 minimal init"):
            raise BuildError("P0 minimal init is not reproducible")
        materialized = acm.materialize(work / "materialize", init_binary)
        out_dir.mkdir(mode=0o700)
        for name in PUBLISHED_FILES:
            key = "init" if name == INIT_NAME else name
            acm.publish_file(materialized["paths"][key], out_dir / name, 0o700 if name == INIT_NAME else 0o600)
        common.fsync_directory(out_dir)
        published = {name: common.receipt(out_dir / name, f"P0 minimal published {name}") for name in PUBLISHED_FILES}
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "profile": PROFILE,
        "target": dict(acm.TARGET),
        "banner": BANNER.decode("ascii"),
        "base_boot": base,
        "magiskboot": magiskboot,
        "sources": sources,
        "init": init_receipt,
        "materialized": materialized["receipts"],
        "nochange_repack": materialized["nochange"],
        "ap": materialized["ap"],
        "published": published,
        "reduction_of": "s20plus-g986n-p0-pid1-acm-v3",
        "properties": {
            "boot_only": True,
            "kernel_unchanged": True,
            "dtb_unchanged": True,
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
            "usb_gadget_configured": False,
            "configfs_mounted": False,
            # The one deliberate difference from the ACM candidate: this probe
            # requests download mode, and that request is its whole evidence.
            "reboot_syscall": True,
            "reboot_target": "download",
            "dwell_before_reboot": False,
            "kmsg_banner_best_effort": True,
            "odin_invoked": False,
            "device_contact": False,
        },
        "reproducibility": {"two_init_builds_byte_identical": True},
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
    result["manifest"] = common.receipt(out_dir / "manifest.json", "P0 minimal manifest")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = build(args.out_dir)
    except (BuildError, common.BuildError, n3.BuildError, acm.BuildError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"schema": SCHEMA, "verdict": "REJECTED", "error": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
