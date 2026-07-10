#!/usr/bin/env python3
"""Build the host-only S22+ V3432 direct-PID1 keystone candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import s22plus_v3427_transition_selection as transition
import s22plus_v3431_pid1_keystone_design as keystone
from build_s22plus_direct_p3_boot import (
    BOOT_PARTITION_SIZE,
    display_path,
    repo_root,
    require_ok,
    resolve,
    run,
    sha256_file,
    tar_members,
    write_ap_tar,
    write_boot_lz4,
)
from build_s22plus_inplace_m4t1_magiskboot import (
    DEFAULT_BASE_BOOT,
    DEFAULT_MAGISK_APK,
    DEFAULT_MAGISKBOOT,
    EXPECTED_BASE_BOOT_SHA256,
    EXPECTED_ORIGINAL_MAGISK_INIT_SHA256,
    diff_ranges,
    ensure_magiskboot,
    run_in_dir,
)


SCHEMA = "s22plus_v3432_pid1_keystone_build_v1"
CONTEXT_SCHEMA = "s22plus_v3432_pid1_keystone_context_v1"
PROFILE_REVISION = "v3432-pid1-keystone-v1"
TARGET = keystone.TARGET
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_native_init/v3432_pid1_keystone_v0_1"
)
DEFAULT_SOURCE = Path(
    "workspace/public/src/native-init/s22plus_init_v3432_pid1_keystone.c"
)
RUN_ID_RE = re.compile(r"^[0-9a-f]{32}$")
GENERATED_HEADER = "s22plus_v3432_pid1_keystone.generated.h"
MODULE_RAMDISK_PATH = "observer/sec_log_buf.ko"

EXPECTED_SYSCALLS = {
    "mknodat": 33,
    "mkdirat": 34,
    "mount": 40,
    "openat": 56,
    "close": 57,
    "write": 64,
    "nanosleep": 101,
    "getpid": 172,
    "finit_module": 273,
}

FORBIDDEN_RUNTIME_SYSCALLS = {
    "read": 63,
    "exit_group": 94,
    "reboot": 142,
    "clone": 220,
    "execve": 221,
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(keystone.canonical_json(value)).hexdigest()


def context_manifest(run_id: str) -> dict[str, Any]:
    return {
        "schema": CONTEXT_SCHEMA,
        "profile_revision": PROFILE_REVISION,
        "target": TARGET,
        "run_id": run_id,
        "expected_live_osrelease": keystone.EXPECTED_LIVE_OSRELEASE,
        "module": {
            "ramdisk_path": keystone.EMBEDDED_MODULE_PATH,
            "sha256": keystone.MODULE_SHA256,
            "size": keystone.MODULE_SIZE,
        },
        "keystone_contract_sha256": keystone.CONTRACT_SHA256,
    }


def make_expectation(run_id: str) -> keystone.MarkerExpectation:
    return keystone.make_expectation(
        run_id,
        canonical_sha256(context_manifest(run_id)),
    )


def marker_record(run_id: str) -> dict[str, Any]:
    context = context_manifest(run_id)
    expectation = make_expectation(run_id)
    frame = keystone.encode_marker(expectation)
    pid_token = b"pid=00000001"
    pid_token_offset = frame.find(pid_token)
    if pid_token_offset < 0:
        raise SystemExit("V3432 marker has no canonical PID token")
    pid_hex_offset = pid_token_offset + len(b"pid=")
    return {
        "schema": "s22plus_v3432_expected_marker_v1",
        "target": TARGET,
        "run_id": run_id,
        "context_manifest": context,
        "context_sha256": expectation.context_sha256,
        "module_sha256": expectation.module_sha256,
        "keystone_contract_sha256": expectation.contract_sha256,
        "transition_sha256": transition.TRANSITION_SHA256,
        "frame": frame.decode("ascii"),
        "frame_size": len(frame),
        "frame_sha256": hashlib.sha256(frame).hexdigest(),
        "pid_hex_offset": pid_hex_offset,
        "raw_run_token": f"run={run_id}",
    }


def render_generated_header(record: dict[str, Any]) -> str:
    return "\n".join(
        [
            "#ifndef S22PLUS_V3432_PID1_KEYSTONE_GENERATED_H",
            "#define S22PLUS_V3432_PID1_KEYSTONE_GENERATED_H",
            "",
            f'#define V3432_EXPECTED_FRAME "{record["frame"]}"',
            f'#define V3432_EXPECTED_FRAME_LEN {record["frame_size"]}U',
            f'#define V3432_PID_HEX_OFFSET {record["pid_hex_offset"]}U',
            "",
            "#endif",
            "",
        ]
    )


def _require_order(text: str, tokens: list[str], label: str) -> None:
    position = 0
    for token in tokens:
        found = text.find(token, position)
        if found < 0:
            raise SystemExit(f"{label} missing ordered token: {token}")
        position = found + len(token)


def verify_source_contract(source: Path) -> dict[str, Any]:
    text = source.read_text(encoding="ascii")
    required = [
        "__attribute__((noreturn)) void _start(void)",
        "long pid = v3432_getpid();",
        "pid == 1",
        "v3432_prepare_volatile_runtime()",
        "v3432_load_observer()",
        "v3432_observer_ready()",
        "v3432_emit_marker(pid)",
        "v3432_render_marker(output, sizeof(output), (uint32_t)pid)",
        "output[V3432_PID_HEX_OFFSET + 7U - index]",
        "V3432_SELFTEST_ONLY",
        "v3432_simulate(2, 1, 1, 1, 1) == V3432_STAGE_START",
        "v3432_simulate(1, 1, 0, 1, 1) == V3432_STAGE_VOLATILE_READY",
        "v3432_simulate(1, 1, 1, 0, 1) == V3432_STAGE_MODULE_LIVE",
        "v3432_simulate(1, 1, 1, 1, 0) == V3432_STAGE_OBSERVER_READY",
        'V3432_MODULE_PATH "/observer/sec_log_buf.ko"',
    ]
    forbidden = [
        "/proc/sys/kernel/osrelease",
        "/lib/modules/sec_log_buf.ko",
        "/proc/modules",
        "/sys/bus/platform/drivers",
        "PRECHECK",
        "FINAL",
        "FAIL ",
        "/config/",
        "usb_gadget",
        "a600000",
        "sec_debug",
        "sysrq",
        "watchdog",
        "NR_REBOOT",
        "NR_CLONE",
        "/dev/block",
        "/data/",
        "/system/",
        "execve",
    ]
    missing = [token for token in required if token not in text]
    present = [token for token in forbidden if token.lower() in text.lower()]
    if missing or present:
        raise SystemExit(
            f"V3432 source contract failed missing={missing} forbidden={present}"
        )
    runtime_start = text.rsplit("#else", 1)[-1]
    _require_order(
        runtime_start,
        [
            "long pid = v3432_getpid();",
            "V3432_STAGE_START, pid == 1",
            "v3432_prepare_volatile_runtime()",
            "v3432_load_observer()",
            "v3432_observer_ready()",
            "v3432_emit_marker(pid)",
            "v3432_quiet_park();",
        ],
        "V3432 runtime gate path",
    )
    if text.count("v3432_load_observer()") != 1:
        raise SystemExit("V3432 must call the observer loader exactly once")
    if text.count("v3432_emit_marker(pid)") != 1:
        raise SystemExit("V3432 must call the marker emitter exactly once")
    return {
        "required": required,
        "forbidden_absent": forbidden,
        "runtime_order": list(keystone.CANDIDATE_GATE_ORDER),
        "module_load_call_count": 1,
        "marker_emit_call_count": 1,
        "marker_pid_derived_from_getpid": True,
        "all_runtime_paths_park": True,
    }


def compiler_command(
    source: Path,
    generated_dir: Path,
    output: Path,
    *,
    selftest: bool,
) -> list[str | Path]:
    command: list[str | Path] = [
        "aarch64-linux-gnu-gcc",
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
        "-Wl,--build-id=none",
        "-Wl,-e,_start",
        "-Wl,-z,noexecstack",
        "-I",
        generated_dir,
    ]
    if selftest:
        command.extend(["-Wno-unused-function", "-DV3432_SELFTEST_ONLY=1"])
    command.extend([source, "-o", output])
    return command


def _syscall_load_present(objdump_text: str, number: int) -> bool:
    needle = f"#0x{number:x}"
    return any(
        "mov" in line
        and ("x8" in line or "x0" in line)
        and needle in line
        for line in objdump_text.splitlines()
    )


def _start_first_syscall_is_getpid(objdump_text: str) -> bool:
    match = re.search(
        r"(?ms)^([0-9a-f]+) <_start>:\n(?P<body>.*?)(?=^[0-9a-f]+ <|\Z)",
        objdump_text,
    )
    if not match:
        return False
    lines = match.group("body").splitlines()
    for index, line in enumerate(lines):
        if "svc" not in line:
            continue
        window = "\n".join(lines[max(0, index - 12) : index])
        return "x8, #0xac" in window
    return False


def compile_init(
    source: Path,
    generated_dir: Path,
    output: Path,
    build_dir: Path,
    record: dict[str, Any],
) -> dict[str, Any]:
    selftest = build_dir / "state-marker-selftest"
    require_ok(
        run(compiler_command(source, generated_dir, selftest, selftest=True)),
        "compile V3432 state/marker selftest",
    )
    require_ok(
        run(["qemu-aarch64", selftest]),
        "run V3432 state/marker selftest",
    )

    command = compiler_command(source, generated_dir, output, selftest=False)
    require_ok(run(command), "compile V3432 init")
    unstripped_objdump = run(["aarch64-linux-gnu-objdump", "-d", output])
    require_ok(unstripped_objdump, "objdump unstripped V3432 init")
    unstripped_text = unstripped_objdump.stdout.decode(
        "utf-8", errors="replace"
    )
    if not _start_first_syscall_is_getpid(unstripped_text):
        raise SystemExit("V3432 _start first syscall is not getpid")
    (build_dir / "v3432_init.unstripped.objdump.txt").write_text(
        unstripped_text, encoding="utf-8"
    )

    require_ok(run(["aarch64-linux-gnu-strip", "-s", output]), "strip V3432 init")
    file_result = run(["file", output])
    readelf_result = run(["aarch64-linux-gnu-readelf", "-h", "-l", output])
    objdump_result = run(["aarch64-linux-gnu-objdump", "-d", output])
    undefined_result = run(["aarch64-linux-gnu-nm", "-u", output])
    for result, label in (
        (file_result, "file V3432 init"),
        (readelf_result, "readelf V3432 init"),
        (objdump_result, "objdump V3432 init"),
        (undefined_result, "undefined V3432 init"),
    ):
        require_ok(result, label)
    file_text = (file_result.stdout + file_result.stderr).decode(
        "utf-8", errors="replace"
    )
    readelf_text = readelf_result.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump_result.stdout.decode("utf-8", errors="replace")
    undefined_text = undefined_result.stdout.decode("utf-8", errors="replace").strip()
    if "ARM aarch64" not in file_text or "statically linked" not in file_text:
        raise SystemExit(f"V3432 init is not static AArch64: {file_text.strip()}")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("V3432 init unexpectedly has PT_INTERP")
    if undefined_text:
        raise SystemExit(f"V3432 init has undefined symbols: {undefined_text}")
    if output.stat().st_size >= 65536:
        raise SystemExit(f"V3432 init unexpectedly large: {output.stat().st_size}")
    if "svc" not in objdump_text:
        raise SystemExit("V3432 init has no raw syscall instruction")
    for name, number in EXPECTED_SYSCALLS.items():
        if not _syscall_load_present(objdump_text, number):
            raise SystemExit(f"V3432 init lacks arm64 __NR_{name} ({number})")
    for name, number in FORBIDDEN_RUNTIME_SYSCALLS.items():
        if _syscall_load_present(objdump_text, number):
            raise SystemExit(
                f"V3432 runtime unexpectedly loads __NR_{name} ({number})"
            )

    binary = output.read_bytes()
    required_strings = [
        record["frame"],
        keystone.EMBEDDED_MODULE_PATH,
        "/proc/ap_klog",
        "/proc/last_kmsg",
    ]
    forbidden_strings = [
        b"/proc/sys/kernel/osrelease",
        b"/lib/modules/sec_log_buf.ko",
        b"/proc/modules",
        b"/sys/bus/platform/drivers",
        b"PRECHECK",
        b"FINAL",
        b"S22_V3432_FAIL",
        b"/config/",
        b"usb_gadget",
        b"sysrq",
        b"watchdog",
        b"/dev/block",
        b"/system/bin/init",
    ]
    for value in required_strings:
        if value.encode("ascii") not in binary:
            raise SystemExit(f"V3432 init required string missing: {value}")
    for value in forbidden_strings:
        if value in binary:
            raise SystemExit(f"V3432 init forbidden string present: {value!r}")

    (build_dir / "v3432_init.file.txt").write_text(file_text, encoding="utf-8")
    (build_dir / "v3432_init.readelf.txt").write_text(
        readelf_text, encoding="utf-8"
    )
    (build_dir / "v3432_init.objdump.txt").write_text(
        objdump_text, encoding="utf-8"
    )
    return {
        "command": [str(item) for item in command],
        "file": file_text.strip(),
        "sha256": sha256_file(output),
        "size": output.stat().st_size,
        "no_interp": True,
        "undefined_symbols": [],
        "runtime_syscalls": EXPECTED_SYSCALLS,
        "forbidden_syscalls_absent": list(FORBIDDEN_RUNTIME_SYSCALLS),
        "first_start_syscall": "getpid",
        "state_marker_qemu_selftest": True,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if not RUN_ID_RE.fullmatch(args.run_id):
        raise SystemExit("--run-id must be exactly 32 lowercase hex characters")

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    source = resolve(root, args.source)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)
    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    generated_dir = build_dir / "generated"
    work_dir = out_dir / "magiskboot-work"
    nochange_dir = out_dir / "nochange-probe"
    patched_unpack_dir = out_dir / "patched-unpack"
    odin_dir = out_dir / "odin4"
    for directory in (
        build_dir,
        generated_dir,
        work_dir,
        nochange_dir,
        patched_unpack_dir,
        odin_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    design = keystone.build_design(root)
    if design["contract_sha256"] != keystone.CONTRACT_SHA256:
        raise SystemExit("V3431 keystone contract mismatch")
    selection = transition.build_selection(root)
    if selection["transition_sha256"] != transition.TRANSITION_SHA256:
        raise SystemExit("V3427 transition contract mismatch")
    source_contract = verify_source_contract(source)
    source_sha = sha256_file(source)

    module = root / keystone.observer.MODULE_DIR / keystone.MODULE_NAME
    if module.stat().st_size != keystone.MODULE_SIZE:
        raise SystemExit("V3432 sec_log_buf.ko size mismatch")
    if sha256_file(module) != keystone.MODULE_SHA256:
        raise SystemExit("V3432 sec_log_buf.ko SHA256 mismatch")

    ensure_magiskboot(magiskboot, magisk_apk)
    base_sha = sha256_file(base_boot)
    if base_sha != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size}")

    expected = marker_record(args.run_id)
    expectation = make_expectation(args.run_id)
    classified = keystone.classify_snapshot(
        "retention",
        expected["frame"].encode("ascii"),
        expectation,
    )
    if classified["classification"] != "PASS_PID1_EXECUTION_AND_OBSERVER_LOAD":
        raise SystemExit(f"V3432 expected marker does not classify: {classified}")
    expected_path = out_dir / "expected_marker.json"
    expected_path.write_text(
        json.dumps(expected, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    generated_header = generated_dir / GENERATED_HEADER
    generated_header.write_text(render_generated_header(expected), encoding="ascii")

    init_out = build_dir / "init"
    init_info = compile_init(source, generated_dir, init_out, build_dir, expected)

    run_in_dir(
        [magiskboot, "unpack", "-h", base_boot],
        nochange_dir,
        "V3432 no-change unpack",
    )
    nochange_boot = out_dir / "boot_nochange_repack.img"
    run_in_dir(
        [magiskboot, "repack", base_boot, nochange_boot],
        nochange_dir,
        "V3432 no-change repack",
    )
    nochange_sha = sha256_file(nochange_boot)
    if nochange_sha != base_sha:
        raise SystemExit(f"V3432 no-change repack differs: {nochange_sha}")

    unpack_text = run_in_dir(
        [magiskboot, "unpack", "-h", base_boot],
        work_dir,
        "V3432 unpack",
    )
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    original_init = build_dir / "init.magisk.original"
    run_in_dir(
        [magiskboot, "cpio", ramdisk, f"extract init {original_init}"],
        work_dir,
        "V3432 extract original init",
    )
    if sha256_file(original_init) != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit("V3432 original Magisk init mismatch")
    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    cpio_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_before != 1:
        raise SystemExit(f"V3432 base ramdisk test rc mismatch: {cpio_before}")

    patch_commands = [
        f"add 750 init {init_out}",
        "mkdir 755 observer",
        f"add 600 {MODULE_RAMDISK_PATH} {module}",
    ]
    patch_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, *patch_commands],
        work_dir,
        "V3432 replace init and embed observer",
    )
    cpio_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_after not in (1, 2):
        raise SystemExit(f"V3432 patched ramdisk test rc mismatch: {cpio_after}")
    extracted_init = build_dir / "init.extracted"
    extracted_module = build_dir / "sec_log_buf.ko.extracted"
    run_in_dir(
        [magiskboot, "cpio", ramdisk, f"extract init {extracted_init}"],
        work_dir,
        "V3432 verify init",
    )
    run_in_dir(
        [
            magiskboot,
            "cpio",
            ramdisk,
            f"extract {MODULE_RAMDISK_PATH} {extracted_module}",
        ],
        work_dir,
        "V3432 verify embedded observer",
    )
    if sha256_file(extracted_init) != sha256_file(init_out):
        raise SystemExit("V3432 ramdisk init mismatch")
    if sha256_file(extracted_module) != keystone.MODULE_SHA256:
        raise SystemExit("V3432 embedded observer mismatch")
    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)

    boot_img = out_dir / "boot.img"
    repack_text = run_in_dir(
        [magiskboot, "repack", base_boot, boot_img],
        work_dir,
        "V3432 repack",
    )
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"V3432 boot size mismatch: {boot_img.stat().st_size}")
    run_in_dir(
        [magiskboot, "unpack", "-h", boot_img],
        patched_unpack_dir,
        "V3432 unpack patched",
    )
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit("V3432 patched boot kernel changed")
    patched_init = build_dir / "init.patched-boot"
    patched_module = build_dir / "sec_log_buf.ko.patched-boot"
    patched_ramdisk = patched_unpack_dir / "ramdisk.cpio"
    run_in_dir(
        [magiskboot, "cpio", patched_ramdisk, f"extract init {patched_init}"],
        patched_unpack_dir,
        "V3432 extract patched init",
    )
    run_in_dir(
        [
            magiskboot,
            "cpio",
            patched_ramdisk,
            f"extract {MODULE_RAMDISK_PATH} {patched_module}",
        ],
        patched_unpack_dir,
        "V3432 extract patched observer",
    )
    if sha256_file(patched_init) != sha256_file(init_out):
        raise SystemExit("V3432 patched boot init mismatch")
    if sha256_file(patched_module) != keystone.MODULE_SHA256:
        raise SystemExit("V3432 patched boot observer mismatch")

    boot_lz4 = odin_dir / "boot.img.lz4"
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_boot_lz4(boot_img, boot_lz4)
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"V3432 AP member mismatch: {members}")

    hashes = {
        "source": source_sha,
        "generated_header": sha256_file(generated_header),
        "expected_marker": sha256_file(expected_path),
        "sec_log_buf_ko": sha256_file(module),
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": sha256_file(original_init),
        "init": sha256_file(init_out),
        "ramdisk_before": sha256_file(ramdisk_before),
        "ramdisk_after": sha256_file(ramdisk_after),
        "kernel": sha256_file(kernel),
        "boot_img": sha256_file(boot_img),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    manifest = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "target": TARGET,
        "purpose": "direct-PID1 V3431 retained-marker keystone",
        "profile_revision": PROFILE_REVISION,
        "run_id": args.run_id,
        "paths": {
            "out_dir": display_path(root, out_dir),
            "source": display_path(root, source),
            "base_boot": display_path(root, base_boot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
            "expected_marker": display_path(root, expected_path),
        },
        "hashes": hashes,
        "sizes": {
            "init": init_out.stat().st_size,
            "embedded_module": module.stat().st_size,
            "boot_img": boot_img.stat().st_size,
            "boot_img_lz4": boot_lz4.stat().st_size,
            "ap_tar_md5": ap_md5.stat().st_size,
        },
        "contracts": {
            "keystone_sha256": keystone.CONTRACT_SHA256,
            "transition_sha256": transition.TRANSITION_SHA256,
        },
        "expected_marker": expected,
        "expected_marker_classification": classified,
        "source_contract": source_contract,
        "init": init_info,
        "ramdisk": {
            "cpio_test_before_rc": cpio_before,
            "cpio_test_after_rc": cpio_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_entries": ["observer", MODULE_RAMDISK_PATH],
            "embedded_module_mode": "600",
            "module_binary_injection": True,
            "module_sha256": keystone.MODULE_SHA256,
        },
        "magiskboot": {
            "nochange_repack_byte_identical": True,
            "unpack_output": unpack_text,
            "repack_output": repack_text,
            "patch_output": patch_text,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
        "tar_members": members,
        "safety": {
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "boot_only": True,
            "kernel_changed": False,
            "construction": (
                "magiskboot in-place repack; replace /init and add exact "
                "observer/sec_log_buf.ko"
            ),
            "runtime": "freestanding raw-syscall direct PID1",
            "pid1_never_exits": True,
            "success_state": "quiet park after exact PID1_ENTER full write",
            "failure_state": "quiet park without current-run token",
            "module_load_allowlist": [keystone.MODULE_NAME],
            "volatile_mounts": ["proc", "sysfs"],
            "kmsg_run_writes": [keystone.PHASE],
            "sysfs_write": False,
            "configfs_write": False,
            "usb_setup": False,
            "panic": False,
            "watchdog": False,
            "reboot_syscall": False,
            "block_device_write": False,
            "persistent_partition_mount": False,
            "android_or_magisk_handoff": False,
            "candidate_transition": False,
        },
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "sha256.txt").write_text(
        "".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())),
        encoding="ascii",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
