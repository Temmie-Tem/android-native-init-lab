#!/usr/bin/env python3
"""Build the dormant S20+ P1 direct-PID1 exec-handoff witness candidate (V1).

H0-only deterministic builder with no connected or live execution surface.

It reuses the consumed candidates' proven materialisation inputs unchanged - the
same resident-Magisk base boot, the same magiskboot, the same no-change repack
proof, the same boot-only single-member AP - and preserves the resident kernel,
DTB and command line byte for byte, and preserves boot header settings and
partition geometry. Repacking regenerates the ramdisk size and image checksum.

Where it differs from the ACM and minimal builders is the ramdisk edit. Those
replaced ``/init`` and asserted that ramdisk membership was otherwise unchanged.
This candidate must hand control back to the resident magiskinit, so it makes
exactly two changes and proves both:

  * ``init``        - replaced with the compiled witness;
  * ``init.magisk`` - added, carrying the base ``init`` bytes unchanged.

Every other entry, its mode and its bytes must be identical, the added entry must
carry the base ``init`` mode, and no third entry may appear. On the device the
witness renames ``init.magisk`` back onto ``init`` before it execs, so the
ramdisk magiskinit actually runs in is byte- and membership-identical to the
resident one - which matters, because magiskinit copies ``/init`` to
``/data/magiskinit`` and renames ``/init`` to ``/sdcard`` to hijack second-stage
init, and both require its own bytes to be at ``/init``.

The disassembly checks are defence in depth against an accidental regression,
and their limits are the ones the minimal builder already recorded: the syscall
scan recognises only immediate ``mov x8, #constant`` forms, the expected set
proves presence rather than exclusivity, and string checks are literal byte
substrings. What binds a specific candidate is the artifact digest the owner
pins, not this scan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import build_s20plus_g986n_native_canary_n1 as common
import build_s20plus_n3u0_magisk_overlay as n3
import build_s20plus_g986n_p0_pid1_acm_h0 as acm


ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "workspace/public/src/native-init/s20plus_p1_pid1_witness_init.c"
DEFAULT_OUTPUT = ROOT / "workspace/private/outputs/s20plus_g986n/p1_pid1_witness_v1"

SCHEMA = "s20plus_g986n_p1_pid1_witness_build_v1"
VERDICT = "PASS_S20PLUS_G986N_P1_PID1_WITNESS_HOST_BUILT_NOT_LIVE_AUTHORIZED"
PROFILE = "s20plus-g986n-p1-pid1-witness-v1"

BASE_BOOT = acm.BASE_BOOT
MAGISKBOOT = acm.MAGISKBOOT
OBJDUMP = acm.OBJDUMP
INIT_NAME = "s20plus_p1_pid1_witness_init"
PUBLISHED_FILES = (INIT_NAME, "boot.img", "boot.img.lz4", "AP.tar.md5")

# The two ramdisk entries this candidate touches, and nothing else.
RAMDISK_INIT_ENTRY = "init"
RAMDISK_STAGED_ENTRY = "init.magisk"
RAMDISK_INIT_MODE = "-rwxr-x---"
RAMDISK_ADD_MODE = "750"

# Record grammar, shared with the evidence consumer through the manifest.
MAGIC = "S20PLUS_P1_PID1_WITNESS_V1"
CANDIDATE_ID = "6f3a1c7d0b45e29840d17ac6e5b93f21"
STAGE = "PRE_EXEC_HANDOFF"
UNAVAILABLE = "unavailable"
# include/linux/proc_ns.h in this target's own 4.19.113 source:
# PROC_PID_INIT_INO = 0xEFFFFFFC. Only the initial PID namespace presents it.
PID_NS_INIT_INO = 0xEFFFFFFC
EXPECTED_PIDNS = f"pid:[{PID_NS_INIT_INO}]"
FIELD_ORDER = ("cand", "pid", "procself", "pidns", "bootid", "stage")

# The complete runtime surface.
#   getpid                              - the PID1 gate and the emitted PID
#   mkdirat/mount/readlinkat/openat/read - the procfs-derived evidence values
#   mknodat/write/close/unlinkat        - the /dev/kmsg record and its cleanup
#   umount2                             - restoring the mount table magiskinit expects
#   renameat                            - restoring magiskinit to /init
#   execve                              - the handoff
#   nanosleep                           - the park
EXPECTED_RUNTIME_SYSCALLS = {
    "mknodat": 33,
    "mkdirat": 34,
    "unlinkat": 35,
    "renameat": 38,
    "umount2": 39,
    "mount": 40,
    "openat": 56,
    "close": 57,
    "read": 63,
    "write": 64,
    "readlinkat": 78,
    "nanosleep": 101,
    "getpid": 172,
    "execve": 221,
}

# exit_group would let PID1 terminate, which the kernel turns into a panic.
# clone would create the child this design exists to avoid; unshare/setns would
# move the witness out of the namespace it is trying to attest. reboot is the
# refuted V4 evidence channel and must not come back with the handoff.
FORBIDDEN_RUNTIME_SYSCALLS = {
    "exit_group": 94,
    "unshare": 97,
    "reboot": 142,
    "clone": 220,
    "setns": 268,
    "finit_module": 273,
    "pivot_root": 41,
    "symlinkat": 36,
    "clone3": 435,
}

# The host fault-injection seam. The device build must never define it, and the
# device link would fail if it did - the binary is -nostdlib -static, so
# p1w_harness_syscall would be an unresolved symbol - but the compile command is
# checked here too rather than relying on a link error to be the guard.
FAULT_HARNESS_MACRO = "S20PLUS_P1_WITNESS_FAULT_HARNESS"

REQUIRED_STRINGS = (
    MAGIC.encode(),
    CANDIDATE_ID.encode(),
    STAGE.encode(),
    UNAVAILABLE.encode(),
    b"/dev/kmsg",
    b"/proc/self/ns/pid",
    b"/proc/sys/kernel/random/boot_id",
    b"/init.magisk",
)

# Strings the consumed candidates carried. Their absence keeps this candidate
# free of the gadget chain and of the refuted download-request channel.
FORBIDDEN_STRINGS = (
    b"a600000.dwc3",
    b"/sys/class/udc",
    b"/config/usb_gadget",
    b"acm.usb0",
    b"/sys/class/tty/ttyGS0/dev",
    b"/dev/ttyGS0",
    b"S20Plus-P0-PID1",
    b"configfs",
    b"download",
)


class BuildError(RuntimeError):
    pass


def compiler_command(output: Path, *, selftest: bool) -> list[str | Path]:
    command: list[str | Path] = [common.TOOLS["cc"], *acm.COMPILE_FLAGS]
    if selftest:
        command.extend(["-Wno-unused-function", "-DS20PLUS_P1_WITNESS_SELFTEST_ONLY=1"])
    command.extend([SOURCE, "-o", output])
    if any(FAULT_HARNESS_MACRO in str(argument) for argument in command):
        raise BuildError("device compile command carries the host fault-injection macro")
    return command


def entry_first_syscall_is_getpid(objdump_text: str, symbol: str) -> bool:
    """The PID1 gate must be the first syscall the body executes.

    `_start` here is a two-instruction stack-pointer trampoline, so unlike the
    consumed candidates the gate lives in the branched-to body and that is what
    is checked. A body whose first syscall is anything else has an effect
    reachable before the gate.
    """
    match = re.search(
        rf"(?ms)^([0-9a-f]+) <{re.escape(symbol)}>:\n(?P<body>.*?)(?=^[0-9a-f]+ <|\Z)",
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


def start_is_stack_trampoline(objdump_text: str) -> bool:
    """`_start` must forward the untouched entry stack pointer and branch.

    The witness forwards the kernel's own argv and envp to magiskinit. That is
    only true if nothing has moved the stack pointer before it is captured, so
    the entry stub is required to be exactly `mov x0, sp` then a branch.
    """
    match = re.search(
        r"(?ms)^([0-9a-f]+) <_start>:\n(?P<body>.*?)(?=^[0-9a-f]+ <|\Z)",
        objdump_text,
    )
    if match is None:
        return False
    instructions = [
        line.split("\t", 2)[-1].strip()
        for line in match.group("body").splitlines()
        if line.strip()
    ]
    if len(instructions) != 2:
        return False
    return instructions[0].startswith("mov\tx0, sp") and instructions[1].startswith("b\t")


def compile_init(output: Path) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise BuildError("P1 witness init output already exists")
    selftest = output.with_name("p1-witness-selftest")
    n3.run_command(compiler_command(selftest, selftest=True), timeout=120)
    n3.run_command([common.TOOLS["qemu"], selftest], timeout=15)
    n3.run_command(compiler_command(output, selftest=False), timeout=120)
    unstripped = n3.run_command([OBJDUMP, "-d", output], timeout=30).decode("ascii", errors="strict")
    if not start_is_stack_trampoline(unstripped):
        raise BuildError("P1 witness _start is not an untouched stack-pointer trampoline")
    if not entry_first_syscall_is_getpid(unstripped, "p1w_main"):
        raise BuildError("P1 witness body's first syscall is not getpid")
    n3.run_command([common.TOOLS["strip"], "--strip-all", output])
    os.chmod(output, 0o700)
    audit = common.audit_elf(output)
    if audit["size"] > 4 * 1024:
        raise BuildError("P1 witness init exceeds 4 KiB")
    objdump = n3.run_command([OBJDUMP, "-d", output], timeout=30).decode("ascii", errors="strict")
    for name, number in EXPECTED_RUNTIME_SYSCALLS.items():
        if not acm.syscall_load_present(objdump, number):
            raise BuildError(f"P1 witness init lacks arm64 syscall {name}={number}")
    for name, number in FORBIDDEN_RUNTIME_SYSCALLS.items():
        if acm.syscall_load_present(objdump, number):
            raise BuildError(f"P1 witness init loads forbidden syscall {name}={number}")
    binary = common.read_regular_bytes(output, "compiled P1 witness init")
    if b"p1w_harness_syscall" in binary:
        raise BuildError("compiled P1 witness init carries the host fault-injection seam")
    for required in REQUIRED_STRINGS:
        if required not in binary:
            raise BuildError(f"compiled P1 witness init lacks {required!r}")
    for forbidden in FORBIDDEN_STRINGS:
        if forbidden in binary:
            raise BuildError(f"P1 witness init retains consumed-candidate string {forbidden!r}")
    return {
        **audit,
        **common.receipt(output, "P1 witness init binary"),
        "expected_syscalls": dict(EXPECTED_RUNTIME_SYSCALLS),
        "forbidden_syscalls_absent": sorted(FORBIDDEN_RUNTIME_SYSCALLS),
        "start_is_stack_trampoline": True,
        "first_syscall_is_getpid": True,
        "selftest_passed": True,
    }


def materialize(root: Path, init_binary: Path) -> dict[str, Any]:
    """Install the witness and stage the resident magiskinit beside it.

    Every assertion the ACM materialisation made is kept. The one relaxation is
    deliberate and bounded: exactly one new entry, with a declared name, a
    declared mode and the base ``init`` bytes.
    """
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
    nochange_receipt = n3.exact_receipt(
        nochange_boot,
        "P1 no-change repack",
        size=acm.BASE_BOOT_SIZE,
        sha256=acm.BASE_BOOT_SHA256,
    )

    n3.run_command([MAGISKBOOT, "unpack", "-h", BASE_BOOT], cwd=work)
    ramdisk = work / "ramdisk.cpio"
    kernel = work / "kernel"
    dtb = work / "dtb"
    header = work / "header"
    n3.exact_receipt(kernel, "P1 base kernel", sha256=acm.BASE_KERNEL_SHA256)
    n3.exact_receipt(dtb, "P1 base DTB", sha256=acm.BASE_DTB_SHA256)
    header_before = n3.exact_receipt(header, "P1 base header")

    resident_init = verify / "init.resident"
    n3.run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"extract {RAMDISK_INIT_ENTRY} {resident_init}"], cwd=work
    )
    n3.exact_receipt(resident_init, "P1 resident Magisk init", sha256=acm.BASE_INIT_SHA256)
    resident_bytes = common.read_regular_bytes(resident_init, "P1 resident Magisk init")

    before_rc, before_bytes = n3.cpio_result(ramdisk, "ls -r /", cwd=work)
    if before_rc != 0:
        raise BuildError("P1 base ramdisk listing failed")
    listing_before = n3.parse_cpio_listing(before_bytes)
    if listing_before.get(RAMDISK_INIT_ENTRY) != RAMDISK_INIT_MODE:
        raise BuildError("P1 base init metadata changed")
    if RAMDISK_STAGED_ENTRY in listing_before:
        raise BuildError("P1 base ramdisk already carries the staged entry")
    logical_before = acm.ramdisk_regular_receipts(
        ramdisk, listing_before, verify / "logical-before", cwd=work
    )

    # Stage the resident init first, so a failure between the two edits leaves a
    # ramdisk whose /init is still the resident one rather than an unreachable
    # witness. Nothing here is published, but the order is free and the weaker
    # intermediate state is the better one.
    n3.run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"add {RAMDISK_ADD_MODE} {RAMDISK_STAGED_ENTRY} {resident_init}"],
        cwd=work,
    )
    n3.run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"add {RAMDISK_ADD_MODE} {RAMDISK_INIT_ENTRY} {init_binary}"],
        cwd=work,
    )

    after_rc, after_bytes = n3.cpio_result(ramdisk, "ls -r /", cwd=work)
    if after_rc != 0:
        raise BuildError("P1 patched ramdisk listing failed")
    listing_after = n3.parse_cpio_listing(after_bytes)
    expected_listing = dict(listing_before)
    expected_listing[RAMDISK_STAGED_ENTRY] = RAMDISK_INIT_MODE
    if listing_after != expected_listing:
        raise BuildError("P1 ramdisk membership or metadata changed beyond the two declared entries")

    logical_after = acm.ramdisk_regular_receipts(
        ramdisk, listing_after, verify / "logical-after", cwd=work
    )
    retained_before = {
        entry: value for entry, value in logical_before.items() if entry != RAMDISK_INIT_ENTRY
    }
    retained_after = {
        entry: value
        for entry, value in logical_after.items()
        if entry not in (RAMDISK_INIT_ENTRY, RAMDISK_STAGED_ENTRY)
    }
    if retained_after != retained_before:
        raise BuildError("P1 non-init logical ramdisk bytes changed")
    if logical_before[RAMDISK_INIT_ENTRY] == logical_after[RAMDISK_INIT_ENTRY]:
        raise BuildError("P1 logical init bytes did not change")
    if logical_after[RAMDISK_STAGED_ENTRY]["sha256"] != logical_before[RAMDISK_INIT_ENTRY]["sha256"]:
        raise BuildError("P1 staged entry does not carry the resident init bytes")

    extracted_init = verify / "init.after"
    extracted_staged = verify / "init.magisk.after"
    n3.run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"extract {RAMDISK_INIT_ENTRY} {extracted_init}"], cwd=work
    )
    n3.run_command(
        [MAGISKBOOT, "cpio", ramdisk, f"extract {RAMDISK_STAGED_ENTRY} {extracted_staged}"], cwd=work
    )
    if common.read_regular_bytes(extracted_init, "P1 extracted init") != common.read_regular_bytes(
        init_binary, "P1 source init"
    ):
        raise BuildError("P1 ramdisk init bytes changed")
    if common.read_regular_bytes(extracted_staged, "P1 extracted staged init") != resident_bytes:
        raise BuildError("P1 ramdisk staged init bytes changed")

    boot_img = root / "boot.img"
    n3.run_command([MAGISKBOOT, "repack", BASE_BOOT, boot_img], cwd=work)
    n3.exact_receipt(boot_img, "P1 candidate boot", size=acm.BASE_BOOT_SIZE)
    patched = root / "patched"
    patched.mkdir(mode=0o700)
    n3.run_command([MAGISKBOOT, "unpack", "-h", boot_img], cwd=patched)
    n3.exact_receipt(patched / "kernel", "P1 patched kernel", sha256=acm.BASE_KERNEL_SHA256)
    n3.exact_receipt(patched / "dtb", "P1 patched DTB", sha256=acm.BASE_DTB_SHA256)
    if n3.exact_receipt(patched / "header", "P1 patched header") != header_before:
        raise BuildError("P1 patched boot header changed")
    patched_rc, patched_bytes = n3.cpio_result(patched / "ramdisk.cpio", "ls -r /", cwd=patched)
    if patched_rc != 0 or n3.parse_cpio_listing(patched_bytes) != expected_listing:
        raise BuildError("P1 repacked ramdisk membership changed")
    logical_patched = acm.ramdisk_regular_receipts(
        patched / "ramdisk.cpio", expected_listing, verify / "logical-patched", cwd=patched
    )
    if logical_patched != logical_after:
        raise BuildError("P1 repacked logical ramdisk bytes changed")

    boot_lz4 = odin / "boot.img.lz4"
    n3.boot_prep.lz4_roundtrip(boot_img, boot_lz4, odin / ".roundtrip.img")
    ap = odin / "AP.tar.md5"
    ap_state = n3.boot_prep.write_boot_ap(boot_lz4, ap)
    if ap_state["members"] != ["boot.img.lz4"]:
        raise BuildError("P1 AP is not boot-only")

    return {
        "paths": {
            "init": init_binary,
            "boot.img": boot_img,
            "boot.img.lz4": boot_lz4,
            "AP.tar.md5": ap,
        },
        "receipts": {
            "init": common.receipt(init_binary, "P1 materialized init"),
            "boot.img": common.receipt(boot_img, "P1 materialized boot"),
            "boot.img.lz4": common.receipt(boot_lz4, "P1 materialized lz4"),
            "AP.tar.md5": common.receipt(ap, "P1 materialized AP"),
        },
        "nochange": nochange_receipt,
        "ap": ap_state,
        "ramdisk": {
            "entries_before": listing_before,
            "entries_after": listing_after,
            "replaced_entry": RAMDISK_INIT_ENTRY,
            "added_entry": RAMDISK_STAGED_ENTRY,
            "added_entry_mode": RAMDISK_INIT_MODE,
            "added_entry_sha256": logical_after[RAMDISK_STAGED_ENTRY]["sha256"],
            "resident_init_sha256": acm.BASE_INIT_SHA256,
            "unrelated_entries_unchanged": True,
        },
    }


def source_contract() -> dict[str, Any]:
    """Bind the source-level invariants the disassembly cannot see.

    The exec must be unreachable unless the rename succeeded, or a failed rename
    would re-exec the witness as PID 1 forever. Evidence return values must not
    gate handoff; this does not establish that evidence syscalls cannot block.
    """
    text = common.read_regular_bytes(SOURCE, "P1 witness source").decode("ascii")
    required = (
        'p1w_syscall3(NR_EXECVE, (long)(uintptr_t)P1W_INIT_PATH',
        "if (p1w_restore_resident_init() != 0) {",
        "if (pid != 1) {",
        "p1w_emit_evidence_best_effort((uint64_t)pid);",
        # Only a node this witness created may be removed, or a pre-existing
        # /dev/kmsg would be unlinked out from under magiskinit.
        "if (created == 0) {",
    )
    for fragment in required:
        if fragment not in text:
            raise BuildError(f"P1 witness source lacks required fragment: {fragment}")
    # The seam the host fault tests use must exist exactly once and must be
    # unreachable without the macro, so the tests drive the device control flow
    # and the device build cannot pick the seam up.
    if text.count(f"#ifdef {FAULT_HARNESS_MACRO}") != 1:
        raise BuildError("P1 witness fault-injection seam is not guarded exactly once")
    guarded = text.split(f"#ifdef {FAULT_HARNESS_MACRO}", 1)[1].split("#else", 1)[0]
    if "p1w_harness_syscall" not in guarded:
        raise BuildError("P1 witness fault-injection seam is declared outside its guard")
    if text.count("p1w_harness_syscall") != guarded.count("p1w_harness_syscall"):
        raise BuildError("P1 witness references the host seam outside its guard")
    return {
        "sha256": hashlib.sha256(text.encode("ascii")).hexdigest(),
        "required_fragments": list(required),
        "fault_harness_macro": FAULT_HARNESS_MACRO,
        "fault_harness_seam_guarded": True,
    }


def build(out_dir: Path) -> dict[str, Any]:
    if out_dir.is_symlink():
        raise BuildError("P1 witness output directory is indirect")
    out_dir = out_dir.resolve(strict=False)
    if out_dir.exists() or out_dir.is_symlink():
        raise BuildError("P1 witness output directory exists; refusing to clobber it")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    contract = source_contract()
    base = n3.exact_receipt(
        BASE_BOOT, "P1 resident Magisk base boot", size=acm.BASE_BOOT_SIZE, sha256=acm.BASE_BOOT_SHA256
    )
    magiskboot = n3.exact_receipt(
        MAGISKBOOT, "P1 Magisk v30.7 magiskboot", size=acm.MAGISKBOOT_SIZE, sha256=acm.MAGISKBOOT_SHA256
    )
    sources = {
        "init": common.receipt(SOURCE, "P1 witness init source"),
        "builder": common.receipt(Path(__file__).resolve(), "P1 witness builder"),
        "acm_builder_reused": common.receipt(Path(acm.__file__).resolve(), "P1 ACM builder reused"),
        "common_h0_builder": common.receipt(Path(common.__file__).resolve(), "P1 common builder"),
        "n3_builder_helper": common.receipt(Path(n3.__file__).resolve(), "P1 N3 helper"),
    }
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        init_binary = work / INIT_NAME
        init_receipt = compile_init(init_binary)
        again = work / (INIT_NAME + ".again")
        n3.run_command(compiler_command(again, selftest=False), timeout=120)
        n3.run_command([common.TOOLS["strip"], "--strip-all", again])
        if common.read_regular_bytes(again, "P1 witness rebuild") != common.read_regular_bytes(
            init_binary, "P1 witness init"
        ):
            raise BuildError("P1 witness init is not reproducible")
        materialized = materialize(work / "materialize", init_binary)
        out_dir.mkdir(mode=0o700)
        for name in PUBLISHED_FILES:
            key = "init" if name == INIT_NAME else name
            acm.publish_file(materialized["paths"][key], out_dir / name, 0o700 if name == INIT_NAME else 0o600)
        common.fsync_directory(out_dir)
        published = {name: common.receipt(out_dir / name, f"P1 witness published {name}") for name in PUBLISHED_FILES}

    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "profile": PROFILE,
        "target": dict(acm.TARGET),
        "tier": "H0",
        "live_authority": False,
        "outputs": {
            name: {"size": published[name]["size"], "sha256": published[name]["sha256"]}
            for name in PUBLISHED_FILES
        },
        # The safety-declaration surface the owner validates. `evidence_contract`
        # replaces the ACM candidate's `observer_contract` and the minimal
        # candidate's `download_contract`.
        "evidence_contract": {
            "channel": "live-dev-kmsg",
            "magic": MAGIC,
            "candidate_id": CANDIDATE_ID,
            "stage": STAGE,
            "unavailable_token": UNAVAILABLE,
            "field_order": list(FIELD_ORDER),
            "expected_pid": 1,
            "expected_procself": "1",
            "expected_pidns": EXPECTED_PIDNS,
            "pid_ns_init_ino": PID_NS_INIT_INO,
            "kmsg_major": 1,
            "kmsg_minor": 11,
            "sysfs_lookup_required": False,
            "usb_gadget_configured": False,
            "configfs_mounted": False,
            # The kernel stamps the record, so the producer cannot choose its
            # ORDER. That is all the timestamp gives; it does not say who wrote
            # the record, and the first revision of this contract implied it did.
            "timestamp_is_kernel_assigned": True,
            # Facility and contiguous sequence constrain record ordering.
            # Writer attribution also depends on the reviewed boot path and
            # operational assumptions; ordering alone does not identify PID1.
            "kernel_facility_unforgeable_from_userspace": True,
            "consumer_requires_first_userspace_record": True,
            "consumer_requires_capture_from_sequence_zero": True,
            "consumer_requires_contiguous_sequence": True,
            "downstream_log_prefix_is_corroboration_only": True,
            "retention_across_reboot_required": False,
        },
        "safety": {
            "boot_only_output": True,
            "global_pid1_candidate": True,
            "ramdisk_init_replaced": True,
            "ramdisk_entries_added": [RAMDISK_STAGED_ENTRY],
            "kernel_preserved": True,
            "dtb_preserved": True,
            "header_preserved": True,
            "block_device_access": False,
            "persistent_write": False,
            "reboot_syscall": False,
            "dwell_before_handoff": False,
            # The deliberate difference from every consumed candidate: this one
            # returns control to the resident Magisk init and the same boot is
            # expected to reach Android.
            "execs_resident_init": True,
            "exec_target": "/init",
            "staged_resident_init": f"/{RAMDISK_STAGED_ENTRY}",
            "exec_requires_successful_rename": True,
            "creates_child_process": False,
            "creates_pid_namespace": False,
            "tar_members": ["boot.img.lz4"],
        },
        "base_boot": base,
        "magiskboot": magiskboot,
        "sources": sources,
        "source_contract": contract,
        "init": init_receipt,
        "materialized": materialized["receipts"],
        "nochange_repack": materialized["nochange"],
        "ap": materialized["ap"],
        "ramdisk": materialized["ramdisk"],
        "published": published,
        "successor_of": "s20plus-g986n-p0-pid1-min-v4",
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
    result["manifest"] = common.receipt(out_dir / "manifest.json", "P1 witness manifest")
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
