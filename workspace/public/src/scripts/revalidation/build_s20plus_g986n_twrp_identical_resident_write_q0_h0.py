#!/usr/bin/env python3
"""Build the dormant S20+ TWRP identical-resident write backend.

This is host-only H0 construction.  It compiles and audits one fixed-input
static AArch64 executable, but never stages it, contacts a device, opens a
block node, prepares a live run, emits an approval, or grants execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any

import build_s20plus_g986n_native_canary_n1 as common


ROOT = Path(__file__).resolve().parents[5]
SOURCE = (
    ROOT
    / "workspace/public/src/native-init/"
    "s20plus_twrp_identical_resident_write_q0.c"
)
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s20plus_g986n/"
    "twrp_identical_resident_write_q0_h0"
)
PRIVATE_TMP = ROOT / "workspace/private/tmp"
SCHEMA = "s20plus_g986n_twrp_identical_resident_write_q0_build_v1"
VERDICT = "PASS_HOST_BUILT_IDENTICAL_RESIDENT_BACKEND_NOT_LIVE_AUTHORIZED"
TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}
TOOLS = {
    "cc": Path("/usr/bin/aarch64-linux-gnu-gcc-15"),
    "strip": Path("/usr/bin/aarch64-linux-gnu-strip"),
    "readelf": Path("/usr/bin/aarch64-linux-gnu-readelf"),
    "nm": Path("/usr/bin/aarch64-linux-gnu-nm"),
    "objdump": Path("/usr/bin/aarch64-linux-gnu-objdump"),
    "file": Path("/usr/bin/file"),
    "qemu": Path("/usr/bin/qemu-aarch64"),
}
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
EXPECTED_RESIDENT_SIZE = 67_108_864
EXPECTED_RESIDENT_SHA256 = (
    "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"
)
Q0_BACKEND_FILENAME = "s20plus_twrp_boot_write_q0"
EXPECTED_ARGUMENT_FAILURE = (
    "schema=s20plus_g986n_twrp_identical_resident_write_backend_v1\n"
    "verdict=STOP_IDENTICAL_RESIDENT_WRITE_QUALIFICATION\n"
    "stage=arguments\n"
    "errno=22\n"
    "write_started=0\n"
    "write_bytes=0\n"
    "fsync_attempted=0\n"
    "fsync_succeeded=0\n"
    "reboot_count=0\n"
    "other_partition_writes=0\n"
).encode("ascii")


class BuildError(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def read_regular(path: Path, label: str, maximum: int = 4 * 1024 * 1024) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise BuildError(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > maximum
        ):
            raise BuildError(f"{label} identity differs")
        chunks: list[bytes] = []
        total = 0
        while total < before.st_size:
            chunk = os.read(descriptor, min(1024 * 1024, before.st_size - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total != before.st_size or os.read(descriptor, 1):
            raise BuildError(f"{label} length differs")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        after.st_dev != before.st_dev
        or after.st_ino != before.st_ino
        or after.st_size != before.st_size
        or after.st_mtime_ns != before.st_mtime_ns
        or after.st_ctime_ns != before.st_ctime_ns
    ):
        raise BuildError(f"{label} changed while read")
    return b"".join(chunks)


def receipt(path: Path, label: str, maximum: int = 4 * 1024 * 1024) -> dict[str, Any]:
    payload = read_regular(path, label, maximum)
    return {"path": str(path), "size": len(payload), "sha256": sha256_bytes(payload)}


def clean_environment() -> dict[str, str]:
    return {
        "HOME": "/nonexistent/s20plus-q0-build",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
        "SOURCE_DATE_EPOCH": "0",
        "TZ": "UTC",
    }


def run(command: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=clean_environment(),
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BuildError("bounded host command failed") from exc
    if len(completed.stdout) > 2 * 1024 * 1024 or len(completed.stderr) > 2 * 1024 * 1024:
        raise BuildError("bounded host command output exceeded limit")
    return completed


def run_ok(command: list[str], *, timeout: int = 60) -> bytes:
    completed = run(command, timeout=timeout)
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr)[:4096].decode(
            "utf-8", errors="replace"
        )
        raise BuildError(f"host command returned {completed.returncode}: {detail}")
    return completed.stdout


def source_contract() -> dict[str, Any]:
    payload = read_regular(SOURCE, "Q0 backend source", 128 * 1024)
    text = payload.decode("ascii")
    required = (
        '#define Q0_STAGE_DIR "/tmp/s20plus-g986n-identical-resident-q0"',
        '#define Q0_BACKEND_NAME "s20plus_twrp_boot_write_q0"',
        '#define Q0_SOURCE_NAME "resident-boot.img"',
        '#define Q0_TARGET_PATH "/dev/block/sda23"',
        '#define Q0_SYSFS_UEVENT "/sys/dev/block/259:7/uevent"',
        "#define Q0_EXPECTED_MAJOR 259U",
        "#define Q0_EXPECTED_MINOR 7U",
        "#define Q0_EXPECTED_PARTITION 23U",
        "#define Q0_EXPECTED_SIZE 67108864ULL",
        EXPECTED_RESIDENT_SHA256,
        "main(int argc, char **argv)",
        "if (argc != 1)",
        "O_RDONLY | O_DIRECT | O_CLOEXEC | O_NOFOLLOW",
        "O_WRONLY | O_CLOEXEC | O_NOFOLLOW",
        "q0_guard_target_fd(target, &target_alignment)",
        "effect->write_started = 1;",
        "amount = pwrite(target, buffer + written",
        "int fsync_result = fsync(target);",
        "readback = open(Q0_TARGET_PATH",
        "PROVED_IDENTICAL_RESIDENT_WRITE_READBACK",
        "STOP_IDENTICAL_RESIDENT_WRITE_QUALIFICATION",
        "q0_block_host_signals();",
        "signal(SIGPIPE, SIG_IGN)",
    )
    forbidden = (
        '"/dev/block/sda24"',
        '"/dev/block/sda25"',
        '"/dev/block/by-name/',
        '"/dev/block/bootdevice/by-name/',
        "O_CREAT",
        "O_TRUNC",
        "system(",
        "execve(",
        "fork(",
        "mount(",
        "reboot(",
        "unlink(",
        "remove(",
        "BLKFLSBUF",
        "argv[1]",
    )
    missing = [token for token in required if token not in text]
    present = [token for token in forbidden if token in text]
    if missing or present:
        raise BuildError(f"Q0 source contract differs missing={missing} forbidden={present}")
    if text.count("pwrite(") != 1:
        raise BuildError("Q0 source must contain exactly one pwrite call site")
    main = text.split("int main(int argc, char **argv)", 1)[1]
    ordered = (
        "q0_open_stage(&stage_directory, &source, &source_identity)",
        "preimage = open(Q0_TARGET_PATH, O_RDONLY | O_DIRECT",
        "q0_guard_target_fd(preimage, &preimage_alignment)",
        "q0_hash_fd(source, Q0_EXPECTED_SIZE",
        "strcmp(source_before_sha, Q0_EXPECTED_SHA256)",
        "q0_hash_fd(preimage, Q0_EXPECTED_SIZE",
        "strcmp(preimage_sha, Q0_EXPECTED_SHA256)",
        "q0_same_source_identity(&source_after, &source_identity)",
        "target = open(Q0_TARGET_PATH, O_WRONLY",
        "q0_guard_target_fd(target, &target_alignment)",
        "q0_write_exact(source, target, buffer, &effect, source_during_sha)",
        "int fsync_result = fsync(target);",
        "readback = open(Q0_TARGET_PATH, O_RDONLY | O_DIRECT",
        "q0_guard_target_fd(readback, &readback_alignment)",
        "q0_hash_fd(readback, Q0_EXPECTED_SIZE",
        "strcmp(readback_sha, Q0_EXPECTED_SHA256)",
        'printf("verdict=PROVED_IDENTICAL_RESIDENT_WRITE_READBACK',
    )
    cursor = 0
    for token in ordered:
        found = main.find(token, cursor)
        if found < 0:
            raise BuildError(f"Q0 runtime order differs at {token}")
        cursor = found + len(token)
    return {
        "path": str(SOURCE),
        "size": len(payload),
        "sha256": sha256_bytes(payload),
        "required_tokens": list(required),
        "forbidden_tokens_absent": list(forbidden),
        "ordered_runtime": list(ordered),
        "pwrite_call_sites": 1,
        "caller_arguments": False,
    }


def compile_backend(output: Path) -> None:
    command = [str(TOOLS["cc"]), *COMPILE_FLAGS, "-o", str(output), str(SOURCE)]
    run_ok(command, timeout=120)
    run_ok([str(TOOLS["strip"]), "--strip-all", str(output)], timeout=30)
    os.chmod(output, 0o500)


def audit_elf(path: Path) -> dict[str, Any]:
    identity = receipt(path, "Q0 backend", 4 * 1024 * 1024)
    file_output = run_ok([str(TOOLS["file"]), "-b", str(path)]).decode("ascii")
    readelf = run_ok(
        [str(TOOLS["readelf"]), "-W", "-h", "-l", "-d", str(path)]
    ).decode("ascii")
    nm = run([str(TOOLS["nm"]), "-u", str(path)])
    if (
        "ELF 64-bit LSB executable, ARM aarch64" not in file_output
        or "statically linked" not in file_output
        or "INTERP" in readelf
        or "NEEDED" in readelf
        or "Dynamic section" in readelf
        or any(
            re.search(r"\bRWE\b", line)
            for line in readelf.splitlines()
            if line.lstrip().startswith("LOAD")
        )
        or nm.returncode != 0
        or nm.stdout.strip()
    ):
        raise BuildError("Q0 backend ELF audit failed")
    identity.update(
        {
            "file": file_output.strip(),
            "static": True,
            "pt_interp": False,
            "dt_needed": [],
            "undefined_symbols": [],
            "writable_executable_load": False,
            "mode": "0500",
        }
    )
    return identity


def qemu_argument_refusal(path: Path) -> dict[str, Any]:
    completed = run([str(TOOLS["qemu"]), str(path), "forbidden-argument"], timeout=10)
    if (
        completed.returncode != 70
        or completed.stdout != EXPECTED_ARGUMENT_FAILURE
        or completed.stderr != b""
    ):
        raise BuildError("Q0 backend argument refusal differs")
    return {
        "returncode": 70,
        "stdout_size": len(completed.stdout),
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_size": 0,
        "write_started": False,
    }


def tools_and_compiler() -> dict[str, Any]:
    receipts = {name: receipt(path, f"Q0 {name} tool", 64 * 1024 * 1024) for name, path in TOOLS.items()}
    queries = {
        "cc1": "-print-prog-name=cc1",
        "collect2": "-print-prog-name=collect2",
        "assembler": "-print-prog-name=as",
        "linker": "-print-prog-name=ld",
        "crt1": "-print-file-name=crt1.o",
        "crti": "-print-file-name=crti.o",
        "crtn": "-print-file-name=crtn.o",
        "crtbeginT": "-print-file-name=crtbeginT.o",
        "crtend": "-print-file-name=crtend.o",
        "libc": "-print-file-name=libc.a",
        "libc_nonshared": "-print-file-name=libc_nonshared.a",
        "libgcc": "-print-file-name=libgcc.a",
        "libgcc_eh": "-print-file-name=libgcc_eh.a",
    }
    closure: dict[str, Any] = {}
    for name, query in queries.items():
        output = run_ok([str(TOOLS["cc"]), query], timeout=10).decode("utf-8").strip()
        if not output or "\n" in output:
            raise BuildError(f"compiler closure query differs: {name}")
        path = Path(output).resolve(strict=True)
        closure[name] = {**receipt(path, f"Q0 compiler {name}", 128 * 1024 * 1024), "query": query}
    return {"tools": receipts, "compiler_closure": closure}


def publish(path: Path, payload: bytes, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise BuildError(f"refusing to clobber {path}") from exc
    try:
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(payload):
            amount = os.write(descriptor, payload[offset:])
            if amount <= 0:
                raise BuildError("short publish write")
            offset += amount
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build(output: Path) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise BuildError("output already exists")
    source = source_contract()
    toolchain = tools_and_compiler()
    PRIVATE_TMP.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="s20plus-q0-build-a-", dir=PRIVATE_TMP) as first_name, tempfile.TemporaryDirectory(prefix="s20plus-q0-build-b-", dir=PRIVATE_TMP) as second_name:
        first = Path(first_name) / Q0_BACKEND_FILENAME
        second = Path(second_name) / Q0_BACKEND_FILENAME
        compile_backend(first)
        compile_backend(second)
        first_bytes = read_regular(first, "first Q0 backend", 4 * 1024 * 1024)
        second_bytes = read_regular(second, "second Q0 backend", 4 * 1024 * 1024)
        if first_bytes != second_bytes:
            raise BuildError("independent Q0 builds differ")
        elf = audit_elf(first)
        elf["path"] = Q0_BACKEND_FILENAME
        refusal = qemu_argument_refusal(first)

    output.mkdir(parents=True, exist_ok=False)
    backend = output / Q0_BACKEND_FILENAME
    publish(backend, first_bytes, 0o500)
    manifest = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "tier": "H0",
        "live_authority": False,
        "target": TARGET,
        "source": source,
        "toolchain": toolchain,
        "backend": elf,
        "reproducible_builds": 2,
        "reproducible_binary_sha256": sha256_bytes(first_bytes),
        "qemu_argument_refusal": refusal,
        "runtime_binding": {
            "stage_dir": "/tmp/s20plus-g986n-identical-resident-q0",
            "backend_name": Q0_BACKEND_FILENAME,
            "source_name": "resident-boot.img",
            "target_path": "/dev/block/sda23",
            "rdev": "259:7",
            "partname": "boot",
            "partition_number": 23,
            "size_bytes": EXPECTED_RESIDENT_SIZE,
            "resident_sha256": EXPECTED_RESIDENT_SHA256,
        },
        "safety": {
            "fixed_input": True,
            "caller_arguments": False,
            "source_and_preimage_exact_before_write": True,
            "write_fd_identity_guarded": True,
            "write_fd_used_for_effect": True,
            "full_write_bytes": EXPECTED_RESIDENT_SIZE,
            "fsync_required": True,
            "fresh_odirect_readback_fd_independently_guarded": True,
            "signals_blocked_before_effect": True,
            "reboots": 0,
            "other_partition_paths": 0,
            "interrupted_write_recoverable_only_not_safe": True,
            "device_contact": False,
            "activation": False,
        },
    }
    manifest_payload = canonical(manifest)
    publish(output / "manifest.json", manifest_payload, 0o400)
    directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return {
        "output": str(output),
        "backend": {"size": len(first_bytes), "sha256": sha256_bytes(first_bytes)},
        "manifest": {"size": len(manifest_payload), "sha256": sha256_bytes(manifest_payload)},
        "verdict": VERDICT,
        "live_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve(strict=False)
    if output == ROOT or ROOT not in output.parents:
        raise BuildError("output must remain below the repository")
    print(json.dumps(build(output), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
