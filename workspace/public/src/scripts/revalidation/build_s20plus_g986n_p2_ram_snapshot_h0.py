#!/usr/bin/env python3
"""H0-only P2 builder: exact resident handoff plus one fixed RAM-file reader.

The unchanged P1 materializer supplies its existing two-entry handoff checks.
An additional verified repack adds only the reader to existing overlay.d/sbin.
Snapshot/partial files are runtime RAM products and must be absent in the image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import build_s20plus_g986n_p1_pid1_witness_h0 as p1
import s20plus_g986n_p2_ram_snapshot as codec

ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "workspace/public/src/native-init/s20plus_p2_pid1_ram_snapshot.c"
HEADER = codec.HEADER
DEFAULT_OUTPUT = ROOT / "workspace/private/outputs/s20plus_g986n/p2_ram_snapshot_v1"
INIT_NAME = "s20plus_p2_pid1_ram_snapshot"
READER_NAME = codec.READER_NAME
READER_ENTRY = "overlay.d/sbin/" + READER_NAME
PUBLISHED_FILES = (INIT_NAME, READER_NAME, "boot.img", "boot.img.lz4", "AP.tar.md5")
SCHEMA = "s20plus_g986n_p2_ram_snapshot_build_v1"
PROFILE = "s20plus-g986n-p2-ram-snapshot-v1"
TARGET = dict(p1.acm.TARGET)
common, n3, acm = p1.common, p1.n3, p1.acm


class BuildError(ValueError):
    pass


def compiler_command(path: Path, *, reader: bool) -> list[str | Path]:
    command = [common.TOOLS["cc"], *acm.COMPILE_FLAGS, "-Wno-unused-function"]
    if reader:
        command.append("-DS20PLUS_P2_READER_ONLY=1")
    return [*command, SOURCE, "-o", path]


def compile_binary(path: Path, *, reader: bool) -> dict[str, Any]:
    if os.path.lexists(path):
        raise BuildError("compiled output already exists")
    n3.run_command(compiler_command(path, reader=reader), timeout=120)
    disassembly = n3.run_command([p1.OBJDUMP, "-d", path]).decode("ascii")
    if (not p1.start_is_stack_trampoline(disassembly)
            or not p1.entry_first_syscall_is_getpid(disassembly, "p2w_main")):
        raise BuildError("first-entry PID gate differs")
    forbidden = {"reboot": 142, "clone": 220, "clone3": 435, "unshare": 97,
                 "setns": 268, "finit_module": 273, "pivot_root": 41}
    if reader:
        forbidden.update(mount=40, mknodat=33, mkdirat=34, renameat=38, renameat2=276, execve=221)
    else:
        forbidden["exit_group"] = 94
    for name, number in forbidden.items():
        if acm.syscall_load_present(disassembly, number):
            raise BuildError("forbidden syscall load: " + name)
    required = {"getpid": 172, "read": 63, "write": 64, "openat": 56,
                "fstat": 80, "fstatfs": 44, "clock_gettime": 113}
    required.update({"exit_group": 94} if reader else {"execve": 221, "renameat2": 276, "fsync": 82})
    for name, number in required.items():
        if not acm.syscall_load_present(disassembly, number):
            raise BuildError("missing syscall load: " + name)
    n3.run_command([common.TOOLS["strip"], "--strip-all", path])
    path.chmod(0o700)
    result = common.audit_elf(path)
    if result["size"] > 32 * 1024:
        raise BuildError("P2 ELF exceeds 32 KiB")
    data = common.read_regular_bytes(path, "P2 ELF")
    required_strings = [codec.SNAPSHOT_NAME, codec.PARTIAL_NAME]
    required_strings += [READER_NAME] if reader else [codec.MAGIC, codec.CANDIDATE_ID, "/init.magisk"]
    if any(s.encode() not in data for s in required_strings):
        raise BuildError("P2 ELF missing its fixed identity/path")
    if b"p2w_harness_syscall" in data or b"/dev/block" in data or b"configfs" in data:
        raise BuildError("P2 ELF contains an unrelated execution surface")
    return {**result, "first_syscall_is_getpid": True, "start_is_stack_trampoline": True,
            "required_syscalls": required, "forbidden_syscall_loads_absent": forbidden,
            "syscall_scan_is_defense_in_depth_only": True, "reader": reader}


def materialize(root: Path, producer: Path, reader: Path) -> dict[str, Any]:
    root.mkdir(mode=0o700)
    handoff = p1.materialize(root / "handoff", producer)
    work, verify = root / "reader-work", root / "verify-reader"
    work.mkdir(mode=0o700); verify.mkdir(mode=0o700)
    n3.run_command([p1.MAGISKBOOT, "unpack", "-h", handoff["paths"]["boot.img"]], cwd=work)
    ramdisk = work / "ramdisk.cpio"
    rc, listing = n3.cpio_result(ramdisk, "ls -r /", cwd=work)
    if rc:
        raise BuildError("handoff ramdisk listing failed")
    before = n3.parse_cpio_listing(listing)
    if before != handoff["ramdisk"]["entries_after"]:
        raise BuildError("handoff ramdisk changed")
    for name in (READER_ENTRY, "overlay.d/sbin/" + codec.SNAPSHOT_NAME, "overlay.d/sbin/" + codec.PARTIAL_NAME):
        if name in before:
            raise BuildError("base ramdisk collides with a P2 output")
    if before.get("overlay.d/sbin", "")[0:1] != "d":
        raise BuildError("resident overlay directory is absent")
    logical_before = acm.ramdisk_regular_receipts(ramdisk, before, verify / "before", cwd=work)
    header_before = common.receipt(work / "header", "P2 header")
    n3.run_command([p1.MAGISKBOOT, "cpio", ramdisk, f"add 750 {READER_ENTRY} {reader}"], cwd=work)
    rc, listing = n3.cpio_result(ramdisk, "ls -r /", cwd=work)
    expected = {**before, READER_ENTRY: "-rwxr-x---"}
    if rc or n3.parse_cpio_listing(listing) != expected:
        raise BuildError("P2 ramdisk delta is not exactly the fixed reader")
    boot = root / "boot.img"
    n3.run_command([p1.MAGISKBOOT, "repack", handoff["paths"]["boot.img"], boot], cwd=work)
    n3.exact_receipt(boot, "P2 boot", size=acm.BASE_BOOT_SIZE)
    unpacked = root / "unpacked"
    unpacked.mkdir(mode=0o700)
    n3.run_command([p1.MAGISKBOOT, "unpack", "-h", boot], cwd=unpacked)
    n3.exact_receipt(unpacked / "kernel", "P2 kernel", sha256=acm.BASE_KERNEL_SHA256)
    n3.exact_receipt(unpacked / "dtb", "P2 DTB", sha256=acm.BASE_DTB_SHA256)
    if common.receipt(unpacked / "header", "P2 header") != header_before:
        raise BuildError("P2 boot header changed")
    rc, listing = n3.cpio_result(unpacked / "ramdisk.cpio", "ls -r /", cwd=unpacked)
    if rc or n3.parse_cpio_listing(listing) != expected:
        raise BuildError("P2 repacked ramdisk metadata changed")
    logical = acm.ramdisk_regular_receipts(unpacked / "ramdisk.cpio", expected, verify / "after", cwd=unpacked)
    if ({k: v for k, v in logical.items() if k != READER_ENTRY} != logical_before
            or logical[READER_ENTRY] != {"mode": "-rwxr-x---", **common.receipt(reader, "P2 reader")}):
        raise BuildError("P2 repacked entry bytes changed")
    lz4, ap = root / "boot.img.lz4", root / "AP.tar.md5"
    n3.boot_prep.lz4_roundtrip(boot, lz4, root / ".roundtrip.img")
    ap_receipt = n3.boot_prep.write_boot_ap(lz4, ap)
    if ap_receipt["members"] != ["boot.img.lz4"]:
        raise BuildError("P2 AP is not boot-only")
    paths = {INIT_NAME: producer, READER_NAME: reader, "boot.img": boot,
             "boot.img.lz4": lz4, "AP.tar.md5": ap}
    return {"paths": paths, "outputs": {k: common.receipt(v, k) for k, v in paths.items()},
            "ramdisk": {**handoff["ramdisk"], "entries_after": expected,
                        "added_entries": ["init.magisk", READER_ENTRY],
                        "runtime_snapshot_names_absent": True},
            "nochange_repack": handoff["nochange"], "ap": ap_receipt}


def build(out_dir: Path) -> dict[str, Any]:
    out_dir = out_dir.absolute()
    if not out_dir.resolve().is_relative_to(ROOT / "workspace/private/outputs/s20plus_g986n"):
        raise BuildError("P2 output must remain in the private S20+ output tree")
    if os.path.lexists(out_dir):
        raise BuildError("P2 output is no-clobber")
    n3.exact_receipt(acm.BASE_BOOT, "P2 resident base", size=acm.BASE_BOOT_SIZE, sha256=acm.BASE_BOOT_SHA256)
    n3.exact_receipt(p1.MAGISKBOOT, "P2 magiskboot", size=acm.MAGISKBOOT_SIZE, sha256=acm.MAGISKBOOT_SHA256)
    sources = {str(p.relative_to(ROOT)): common.receipt(p, "P2 source") for p in
               (SOURCE, HEADER, Path(__file__).resolve(), Path(codec.__file__), Path(p1.__file__),
                Path(acm.__file__), Path(common.__file__), Path(n3.__file__))}
    with tempfile.TemporaryDirectory(dir=out_dir.parent, prefix=".p2-build-") as temp:
        work = Path(temp)
        producer, reader = work / INIT_NAME, work / READER_NAME
        binaries = {INIT_NAME: compile_binary(producer, reader=False), READER_NAME: compile_binary(reader, reader=True)}
        first = materialize(work / "first", producer, reader)
        second = materialize(work / "second", producer, reader)
        if first["outputs"] != second["outputs"]:
            raise BuildError("P2 full artifact builds differ")
        if any(common.receipt(ROOT / p, "P2 source") != receipt for p, receipt in sources.items()):
            raise BuildError("P2 source changed during build")
        out_dir.mkdir(mode=0o700)
        for name, source in first["paths"].items():
            acm.publish_file(source, out_dir / name, 0o700 if name in (INIT_NAME, READER_NAME) else 0o600)
        outputs = {name: common.receipt(out_dir / name, name) for name in PUBLISHED_FILES}
        if outputs != first["outputs"]:
            raise BuildError("published P2 artifacts differ")
        manifest = {"schema": SCHEMA, "profile": PROFILE, "target": TARGET, "tier": "H0",
            "live_authority": False, "outputs": outputs, "sources": sources, "binaries": binaries,
            "base_boot": common.receipt(acm.BASE_BOOT, "resident base"),
            "ramdisk": first["ramdisk"], "nochange_repack": first["nochange_repack"], "ap": first["ap"],
            "evidence_contract": {"capture_source": codec.CAPTURE_SOURCE, "declaration": codec.CONSTANTS,
                "requires_sequence_zero": True, "requires_contiguous_prefix": True,
                "requires_first_userspace_witness": True, "relocation_live_proved": False},
            "safety": {"boot_only_output": True, "kernel_preserved": True, "dtb_preserved": True,
                "header_preserved": True, "block_device_access": False, "persistent_evidence_write": False,
                "reader_filesystems": sorted(codec.RAM_FILESYSTEMS), "execs_resident_init": True,
                "reboot_syscall": False, "creates_child_process": False,
                "reader_has_no_filesystem_write": True, "snapshot_is_not_hostile_root_attestation": True},
            "reproducibility": {"two_full_artifact_builds_byte_identical": True},
            "device_commands": 0, "partition_transfers": 0}
        common.publish_bytes_no_clobber(out_dir / "manifest.json",
            (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode(), 0o600)
        common.fsync_directory(out_dir)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = build(args.out_dir)
    except (ValueError, OSError, subprocess.SubprocessError, common.BuildError, n3.BuildError) as error:
        print(json.dumps({"status": "H0_BUILD_FAILED", "error": str(error)}))
        return 2
    print(json.dumps({"status": "H0_P2_ARTIFACT_BUILT", "outputs": result["outputs"],
                      "live_authority": False, "device_commands": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
