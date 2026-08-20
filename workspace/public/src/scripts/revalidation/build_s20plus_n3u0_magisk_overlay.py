#!/usr/bin/env python3
"""Build the host-only S20+ N3-U0 temporary Magisk ACM overlay.

The builder has no device transport.  It accepts only an output directory,
pins the exact known-good resident Magisk boot and local tools, adds one rc and
one static binary, and emits a boot-only AP for offline inspection.  Its output
is not live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import build_s20plus_g986n_native_canary_n1 as common
import s20plus_g986n_boot_only_odin_prep as boot_prep


ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "workspace/public/src/native-init/s20plus_n3u0_acm_witness.c"
RC_SOURCE = ROOT / "workspace/public/src/android/s20plus_n3u0_acm.rc"
BASE_BOOT = (
    ROOT
    / "workspace/private/outputs/s20plus_g986n/"
    "magisk_boot_only_iyc2_v1/candidate/boot.img"
)
MAGISKBOOT = ROOT / "workspace/private/tools/magisk-v30.7/magiskboot"
DEFAULT_OUTPUT = (
    ROOT / "workspace/private/outputs/s20plus_g986n/n3u0_acm_overlay_v1"
)

SCHEMA = "s20plus_g986n_n3u0_magisk_overlay_build_v1"
VERDICT = "PASS_S20PLUS_G986N_N3U0_ACM_HOST_BUILT_NOT_LIVE_AUTHORIZED"
TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}
BASE_BOOT_SIZE = 67_108_864
BASE_BOOT_SHA256 = "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"
BASE_INIT_SHA256 = "383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468"
BASE_KERNEL_SHA256 = "f760f09e98eea9038b1fb0e62832e09daa5e5705530e36b1cf6d458d68a176a1"
BASE_DTB_SHA256 = "09ce85eab63208c985486bba8b450d17fd5907839361b53bf1971e0eeaceb883"
MAGISKBOOT_SIZE = 943_848
MAGISKBOOT_SHA256 = "a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e"
RC_ENTRY = "overlay.d/s20plus_n3u0_acm.rc"
BINARY_ENTRY = "overlay.d/sbin/s20plus_n3u0_acm"
ADDED_ENTRIES = (RC_ENTRY, BINARY_ENTRY)
ENTRY_MODES = {
    RC_ENTRY: "-rw-r--r--",
    BINARY_ENTRY: "-rwxr-x---",
}
PUBLISHED_FILES = (
    "s20plus_n3u0_acm",
    "boot.img",
    "boot.img.lz4",
    "AP.tar.md5",
)
COMPILE_FLAGS = (
    "-std=c11",
    "-static",
    "-Os",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-fno-ident",
    f"-ffile-prefix-map={ROOT}=.",
    f"-fdebug-prefix-map={ROOT}=.",
    "-Wl,--build-id=none",
    "-Wl,-z,noexecstack",
    "-Wl,-z,relro",
    "-Wl,-z,now",
)


class BuildError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_command(
    command: list[str | Path],
    *,
    cwd: Path | None = None,
    expected: tuple[int, ...] = (0,),
    timeout: int = 300,
) -> bytes:
    completed = subprocess.run(
        [str(item) for item in command],
        cwd=cwd,
        env=common.clean_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    if len(completed.stdout) > 2 * 1024 * 1024:
        raise BuildError("command output exceeded the H0 bound")
    if completed.returncode not in expected:
        text = completed.stdout[:4096].decode("utf-8", errors="replace")
        raise BuildError(
            f"command failed rc={completed.returncode} expected={expected}: {text}"
        )
    return completed.stdout


def exact_receipt(
    path: Path,
    label: str,
    *,
    size: int | None = None,
    sha256: str | None = None,
) -> dict[str, Any]:
    state = common.receipt(path, label)
    if size is not None and state["size"] != size:
        raise BuildError(f"{label} size changed")
    if sha256 is not None and state["sha256"] != sha256:
        raise BuildError(f"{label} SHA-256 changed")
    return state


def source_contract() -> dict[str, Any]:
    source = common.read_regular_bytes(SOURCE, "N3-U0 source").decode("ascii")
    rc = common.read_regular_bytes(RC_SOURCE, "N3-U0 rc").decode("ascii")
    source_required = (
        "S20PLUS_N3U0_ACM_WITNESS_V1",
        "S20PLUS_N3U0_ACM_V1\\n",
        '"a600000.dwc3"',
        '#define N3U0_STOCK_GADGET N3U0_GADGET_ROOT "/g1"',
        '#define N3U0_STOCK_UDC N3U0_STOCK_GADGET "/UDC"',
        '#define N3U0_OWN_GADGET N3U0_GADGET_ROOT "/s20plus_n3u0"',
        '"/functions/acm.usb0"',
        '"/port_num"',
        '"/dev/ttyGS%d"',
        "N3U0_BANNER_ATTEMPTS 40",
        "run_transaction",
        "real_owned_cleanup",
        "real_stock_restore",
    )
    source_forbidden = (
        "/data/",
        "/dev/block",
        "system(",
        "execve(",
        "execl(",
        "posix_spawn(",
        "fork(",
        "clone(",
        "socket(",
        "connect(",
        "mount(",
        "umount",
        "unshare(",
        "setns(",
        "reboot(",
        "ioctl(",
        "init_module(",
        "finit_module(",
        "setprop",
        "ctl.start",
        "ctl.stop",
        "mass_storage",
        "rndis",
        "ncm.",
        "ffs.",
        "/mode",
        '"peripheral"',
    )
    rc_required = (
        "on property:sys.boot_completed=1",
        "start s20plus_n3u0_acm",
        "service s20plus_n3u0_acm ${MAGISKTMP}/s20plus_n3u0_acm",
        "class late_start",
        "user root",
        "group root system shell",
        "disabled",
        "oneshot",
        "seclabel u:r:magisk:s0",
    )
    rc_forbidden = (
        "early-init",
        "on init",
        "critical",
        "restart_period",
        "setprop",
        "write /",
        "exec ",
        "/data/",
        "reboot",
    )
    missing_source = [token for token in source_required if token not in source]
    present_source = [token for token in source_forbidden if token in source]
    missing_rc = [token for token in rc_required if token not in rc]
    present_rc = [token for token in rc_forbidden if token in rc]
    if missing_source or present_source or missing_rc or present_rc:
        raise BuildError(
            "N3-U0 source contract changed: "
            f"missing_source={missing_source} forbidden_source={present_source} "
            f"missing_rc={missing_rc} forbidden_rc={present_rc}"
        )
    return {
        "source_required": list(source_required),
        "source_forbidden_absent": list(source_forbidden),
        "rc_required": list(rc_required),
        "rc_forbidden_absent": list(rc_forbidden),
        "single_owned_gadget": "/config/usb_gadget/s20plus_n3u0",
        "stock_mutation_surface": ["/config/usb_gadget/g1/UDC"],
        "mode_peripheral_write": False,
        "caller_inputs": False,
    }


def compile_witness(output: Path) -> dict[str, Any]:
    common.direct_regular(SOURCE, "N3-U0 source")
    if output.exists() or output.is_symlink():
        raise BuildError("witness output already exists")
    run_command(
        [str(common.TOOLS["cc"]), *COMPILE_FLAGS, "-o", output, SOURCE],
        timeout=120,
    )
    run_command([common.TOOLS["strip"], "--strip-all", output])
    os.chmod(output, 0o700)
    audit = common.audit_elf(output)
    if audit["size"] > 1024 * 1024:
        raise BuildError("N3-U0 witness exceeds the 1 MiB bound")
    return audit


def host_selftest() -> dict[str, Any]:
    cc = Path("/usr/bin/cc").resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="s20plus-n3u0-host-selftest-") as temp:
        binary = Path(temp) / "selftest"
        output = run_command(
            [
                cc,
                "-std=c11",
                "-Os",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-DS20PLUS_N3U0_HOST_TEST=1",
                SOURCE,
                "-o",
                binary,
            ],
            timeout=60,
        )
        if output:
            raise BuildError("host selftest compilation wrote unexpected output")
        result = run_command([binary], timeout=10)
    if result != b"s20plus_n3u0_host_selftest=PASS\n":
        raise BuildError("N3-U0 host state-machine selftest failed")
    return {
        "compiler": {"path": str(cc), **common.receipt(cc, "host C compiler")},
        "stdout_sha256": sha256_bytes(result),
        "stdout_size": len(result),
        "fault_routes": 7,
        "cleanup_after_owned_touch": True,
        "stock_restore_after_unbind": True,
    }


def cpio_result(ramdisk: Path, command: str, *, cwd: Path) -> tuple[int, bytes]:
    completed = subprocess.run(
        [str(MAGISKBOOT), "cpio", str(ramdisk), command],
        cwd=cwd,
        env=common.clean_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=120,
    )
    if len(completed.stdout) > 2 * 1024 * 1024:
        raise BuildError("magiskboot cpio output exceeded the H0 bound")
    return completed.returncode, completed.stdout


def parse_cpio_listing(data: bytes) -> dict[str, str]:
    entries: dict[str, str] = {}
    text = data.decode("utf-8", errors="strict")
    for line in text.splitlines():
        columns = line.split("\t")
        if len(columns) >= 2 and columns[0].startswith(("-", "d", "l")):
            entries[columns[-1]] = columns[0]
    return entries


def add_entry(
    ramdisk: Path,
    *,
    entry: str,
    mode: str,
    source: Path,
    verify: Path,
    cwd: Path,
) -> dict[str, Any]:
    run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"add {mode} {entry} {source}"], cwd=cwd
    )
    extracted = verify / entry.replace("/", "_")
    run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"extract {entry} {extracted}"], cwd=cwd
    )
    source_bytes = common.read_regular_bytes(source, f"source for {entry}")
    extracted_bytes = common.read_regular_bytes(extracted, f"extracted {entry}")
    if extracted_bytes != source_bytes:
        raise BuildError(f"cpio entry changed: {entry}")
    return {
        "entry": entry,
        "mode": mode,
        "size": len(source_bytes),
        "sha256": sha256_bytes(source_bytes),
    }


def materialize(root: Path, witness: Path) -> dict[str, Any]:
    root.mkdir(mode=0o700)
    work = root / "work"
    nochange = root / "nochange"
    verify = root / "verify"
    odin = root / "odin"
    for directory in (work, nochange, verify, odin):
        directory.mkdir(mode=0o700)

    run_command([MAGISKBOOT, "unpack", "-h", BASE_BOOT], cwd=nochange)
    nochange_boot = root / "boot.nochange.img"
    run_command([MAGISKBOOT, "repack", BASE_BOOT, nochange_boot], cwd=nochange)
    nochange_identity = exact_receipt(
        nochange_boot,
        "no-change repack",
        size=BASE_BOOT_SIZE,
        sha256=BASE_BOOT_SHA256,
    )

    unpack_output = run_command([MAGISKBOOT, "unpack", "-h", BASE_BOOT], cwd=work)
    ramdisk = work / "ramdisk.cpio"
    kernel = work / "kernel"
    dtb = work / "dtb"
    header = work / "header"
    exact_receipt(kernel, "base kernel", sha256=BASE_KERNEL_SHA256)
    exact_receipt(dtb, "base DTB", sha256=BASE_DTB_SHA256)
    header_before = exact_receipt(header, "base header")

    init_before = verify / "init.before"
    run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"extract init {init_before}"], cwd=work
    )
    exact_receipt(init_before, "Magisk init before", sha256=BASE_INIT_SHA256)
    test_rc, _ = cpio_result(ramdisk, "test", cwd=work)
    if test_rc != 1:
        raise BuildError(f"base ramdisk is not exact Magisk state rc=1: {test_rc}")
    list_rc, listing_before_bytes = cpio_result(ramdisk, "ls -r /", cwd=work)
    if list_rc != 0:
        raise BuildError("base ramdisk listing failed")
    listing_before = parse_cpio_listing(listing_before_bytes)
    for entry in ADDED_ENTRIES:
        exists_rc, _ = cpio_result(ramdisk, f"exists {entry}", cwd=work)
        if exists_rc == 0:
            raise BuildError(f"base already contains N3-U0 entry: {entry}")

    ramdisk_before = verify / "ramdisk.before.cpio"
    shutil.copyfile(ramdisk, ramdisk_before)
    entries = [
        add_entry(
            ramdisk,
            entry=RC_ENTRY,
            mode="644",
            source=RC_SOURCE,
            verify=verify,
            cwd=work,
        ),
        add_entry(
            ramdisk,
            entry=BINARY_ENTRY,
            mode="750",
            source=witness,
            verify=verify,
            cwd=work,
        ),
    ]
    test_rc, _ = cpio_result(ramdisk, "test", cwd=work)
    if test_rc != 1:
        raise BuildError(f"patched ramdisk lost exact Magisk state rc=1: {test_rc}")
    list_rc, listing_after_bytes = cpio_result(ramdisk, "ls -r /", cwd=work)
    if list_rc != 0:
        raise BuildError("patched ramdisk listing failed")
    listing_after = parse_cpio_listing(listing_after_bytes)
    listing_delta = {
        "added": sorted(set(listing_after) - set(listing_before)),
        "removed": sorted(set(listing_before) - set(listing_after)),
        "entry_modes": {entry: listing_after.get(entry) for entry in ADDED_ENTRIES},
    }
    expected_delta = {
        "added": sorted(ADDED_ENTRIES),
        "removed": [],
        "entry_modes": ENTRY_MODES,
    }
    if listing_delta != expected_delta:
        raise BuildError(f"ramdisk delta changed: {listing_delta}")
    init_after = verify / "init.after"
    run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"extract init {init_after}"], cwd=work
    )
    exact_receipt(init_after, "Magisk init after", sha256=BASE_INIT_SHA256)
    ramdisk_after = verify / "ramdisk.after.cpio"
    shutil.copyfile(ramdisk, ramdisk_after)

    boot_img = root / "boot.img"
    repack_output = run_command([MAGISKBOOT, "repack", BASE_BOOT, boot_img], cwd=work)
    exact_receipt(boot_img, "N3-U0 boot", size=BASE_BOOT_SIZE)
    patched = root / "patched"
    patched.mkdir(mode=0o700)
    run_command([MAGISKBOOT, "unpack", "-h", boot_img], cwd=patched)
    exact_receipt(patched / "kernel", "patched kernel", sha256=BASE_KERNEL_SHA256)
    exact_receipt(patched / "dtb", "patched DTB", sha256=BASE_DTB_SHA256)
    if exact_receipt(patched / "header", "patched header") != header_before:
        raise BuildError("patched boot header changed")
    patched_init = verify / "init.patched"
    run_command(
        [
            MAGISKBOOT,
            "cpio",
            patched / "ramdisk.cpio",
            f"extract init {patched_init}",
        ],
        cwd=patched,
    )
    exact_receipt(patched_init, "patched Magisk init", sha256=BASE_INIT_SHA256)
    patched_list_rc, patched_listing_bytes = cpio_result(
        patched / "ramdisk.cpio", "ls -r /", cwd=patched
    )
    if patched_list_rc != 0 or parse_cpio_listing(patched_listing_bytes) != listing_after:
        raise BuildError("repacked boot ramdisk listing changed")

    boot_lz4 = odin / "boot.img.lz4"
    boot_prep.lz4_roundtrip(boot_img, boot_lz4, odin / ".roundtrip.img")
    ap = odin / "AP.tar.md5"
    ap_state = boot_prep.write_boot_ap(boot_lz4, ap)
    if ap_state["members"] != ["boot.img.lz4"]:
        raise BuildError("N3-U0 AP is not boot-only")
    return {
        "paths": {
            "witness": witness,
            "boot.img": boot_img,
            "boot.img.lz4": boot_lz4,
            "AP.tar.md5": ap,
        },
        "receipts": {
            "witness": common.receipt(witness, "materialized witness"),
            "boot.img": common.receipt(boot_img, "materialized boot"),
            "boot.img.lz4": common.receipt(boot_lz4, "materialized boot lz4"),
            "AP.tar.md5": common.receipt(ap, "materialized boot-only AP"),
            "ramdisk_before": common.receipt(ramdisk_before, "ramdisk before"),
            "ramdisk_after": common.receipt(ramdisk_after, "ramdisk after"),
        },
        "nochange": nochange_identity,
        "entries": entries,
        "listing_delta": listing_delta,
        "unpack_output_sha256": sha256_bytes(unpack_output),
        "repack_output_sha256": sha256_bytes(repack_output),
        "ap": ap_state,
    }


def publish_file(source: Path, destination: Path, mode: int) -> None:
    data = common.read_regular_bytes(source, f"publish source {source.name}")
    common.publish_bytes_no_clobber(destination, data, mode)


def build(out_dir: Path) -> dict[str, Any]:
    out_dir = out_dir.resolve(strict=False)
    if out_dir.exists() or out_dir.is_symlink():
        raise BuildError("output directory exists; refusing to clobber it")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    base = exact_receipt(
        BASE_BOOT,
        "resident Magisk base boot",
        size=BASE_BOOT_SIZE,
        sha256=BASE_BOOT_SHA256,
    )
    magiskboot = exact_receipt(
        MAGISKBOOT,
        "Magisk v30.7 magiskboot",
        size=MAGISKBOOT_SIZE,
        sha256=MAGISKBOOT_SHA256,
    )
    exact_receipt(
        boot_prep.LZ4,
        "pinned lz4",
        size=boot_prep.LZ4_SIZE,
        sha256=boot_prep.LZ4_SHA256,
    )
    contract = source_contract()
    selftest = host_selftest()
    tools = common.tool_receipts()
    compiler = common.compiler_closure()
    sources = {
        "witness": common.receipt(SOURCE, "N3-U0 witness source"),
        "rc": common.receipt(RC_SOURCE, "N3-U0 rc source"),
        "builder": common.receipt(Path(__file__).resolve(), "N3-U0 builder"),
        "common_h0_builder": common.receipt(
            Path(common.__file__).resolve(), "common S20+ H0 builder"
        ),
        "boot_prep_helper": common.receipt(
            Path(boot_prep.__file__).resolve(), "S20+ boot preparation helper"
        ),
    }

    with tempfile.TemporaryDirectory(
        prefix=".s20plus-n3u0-a-", dir=out_dir.parent
    ) as first_name, tempfile.TemporaryDirectory(
        prefix=".s20plus-n3u0-b-", dir=out_dir.parent
    ) as second_name:
        first_root = Path(first_name)
        second_root = Path(second_name)
        first_witness = first_root / "s20plus_n3u0_acm"
        second_witness = second_root / "s20plus_n3u0_acm"
        first_audit = compile_witness(first_witness)
        second_audit = compile_witness(second_witness)
        if first_witness.read_bytes() != second_witness.read_bytes():
            raise BuildError("two witness builds are not byte-identical")
        first = materialize(first_root / "artifact", first_witness)
        second = materialize(second_root / "artifact", second_witness)
        if first["receipts"] != second["receipts"]:
            raise BuildError("two complete N3-U0 artifact builds differ")
        for name in PUBLISHED_FILES:
            first_path = first["paths"]["witness" if name == "s20plus_n3u0_acm" else name]
            second_path = second["paths"]["witness" if name == "s20plus_n3u0_acm" else name]
            if first_path.read_bytes() != second_path.read_bytes():
                raise BuildError(f"two N3-U0 outputs differ: {name}")

        out_dir.mkdir(mode=0o700)
        common.fsync_directory(out_dir.parent)
        publish_file(first_witness, out_dir / "s20plus_n3u0_acm", 0o700)
        publish_file(first["paths"]["boot.img"], out_dir / "boot.img", 0o600)
        publish_file(
            first["paths"]["boot.img.lz4"], out_dir / "boot.img.lz4", 0o600
        )
        publish_file(first["paths"]["AP.tar.md5"], out_dir / "AP.tar.md5", 0o600)

    outputs = {
        name: common.receipt(out_dir / name, f"published {name}")
        for name in PUBLISHED_FILES
    }
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "tier": "H0",
        "review_state": "REVIEW_PENDING",
        "live_authority": False,
        "target": TARGET,
        "base_boot": base,
        "base_boot_role": "known-good resident Magisk boot; offline input only",
        "magiskboot": magiskboot,
        "tools": tools,
        "compiler_closure": compiler,
        "sources": sources,
        "source_contract": contract,
        "host_selftest": selftest,
        "compile_flags": list(COMPILE_FLAGS),
        "binary_audit": first_audit,
        "reproduction_binary_audit": second_audit,
        "outputs": outputs,
        "ramdisk": {
            "added_entries": list(ADDED_ENTRIES),
            "replaced_entries": [],
            "entries": first["entries"],
            "listing_delta": first["listing_delta"],
            "magisk_cpio_test_before_rc": 1,
            "magisk_cpio_test_after_rc": 1,
            "original_magisk_init_preserved": True,
        },
        "safety": {
            "host_only_build": True,
            "boot_only_output": True,
            "tar_members": ["boot.img.lz4"],
            "base_nochange_repack_byte_identical": True,
            "kernel_preserved": True,
            "dtb_preserved": True,
            "header_preserved": True,
            "magisk_init_preserved": True,
            "one_rc_plus_one_binary": True,
            "mode_peripheral_write": False,
            "module_insertions": False,
            "network_functions": False,
            "storage_functions": False,
            "pid1_replacement": False,
            "persistent_promotion": False,
            "odin_invoked": False,
            "device_contact": False,
        },
        "reproducibility": {
            "two_witness_builds_byte_identical": True,
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
    result["manifest"] = common.receipt(out_dir / "manifest.json", "N3-U0 manifest")
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
