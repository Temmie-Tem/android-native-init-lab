#!/usr/bin/env python3
"""Run the bounded P2.80 tracefs Kprobe control in generic-arm64 QEMU."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import select
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


KERNEL_VERSION = "6.12.94+deb13-arm64"
VERDICT = "PASS_P280_KPROBE_GENERIC_QEMU_HOST_ONLY"
PINNED_KERNEL_SHA256 = (
    "cbe59a02e7ea979a150661032440c94e2c4db0b735af2416e11ae5cac15a58e4"
)
PINNED_CONFIG_SHA256 = (
    "834fda1f695bb68263c61615fb6f3707ac1a54e6ba72a71376c7472d499f960a"
)
PINNED_QEMU_SHA256 = (
    "15d18809121fe6237c9170a5d820cc44196942d1df2df0dad0c5d8cd6154b35e"
)
PINNED_QEMU_VERSION = (
    "QEMU emulator version 10.2.1 (Debian 1:10.2.1+ds-1ubuntu3.1)"
)
HOST_COMMAND_TIMEOUT_SEC = 60
SOURCE_RELATIVE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_p280_kprobe_qemu_control.c"
)
REQUIRED_CONFIG = (
    "CONFIG_KALLSYMS_ALL=y",
    "CONFIG_KPROBES=y",
    "CONFIG_KRETPROBES=y",
    "CONFIG_KPROBE_EVENTS=y",
    "CONFIG_FTRACE=y",
    "CONFIG_TRACING=y",
)


class HarnessError(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_guest_config(data: bytes) -> None:
    lines = set(data.decode("ascii").splitlines())
    missing = [value for value in REQUIRED_CONFIG if value not in lines]
    if missing:
        raise HarnessError(
            "guest kernel lacks required Kprobe config: " + ", ".join(missing)
        )


def verify_source(data: bytes) -> None:
    cardinalities = (
        (b'#define P280_SYMBOL "__arm64_sys_close"', 1),
        (b'"p:" P280_GROUP "/" P280_ENTRY " " P280_SYMBOL "\\n"', 1),
        (b'"r:" P280_GROUP "/" P280_RETURN " " P280_SYMBOL', 1),
        (b'" rc=$retval:s32\\n"', 1),
        (b'"common_pid == 1\\n"', 4),
        (b'P280_INSTANCE_ROOT "/trace_clock"', 2),
        (b'P280_TRACE_ROOT "/kprobe_profile"', 1),
        (b'"-:" P280_GROUP "/" P280_ENTRY "\\n"', 1),
        (b'"-:" P280_GROUP "/" P280_RETURN "\\n"', 1),
        (b'"P280_KPROBE_QEMU result=PASS symbol=%s "', 1),
    )
    for token, expected in cardinalities:
        if data.count(token) != expected:
            raise HarnessError(
                f"Kprobe control token cardinality drifted: {token!r}"
            )
    required = (
        b'p280_write_fd_exact(tracing_on_fd, "tracing-disable", "0\\n")',
        b'p280_write_fd_exact(event_enable_fd, "event-disable", "0\\n")',
        b'P280_INSTANCE_ROOT "/events/" P280_GROUP "/enable", "0\\n"',
        b"O_WRONLY | O_TRUNC | O_CLOEXEC",
        b"syscall(SYS_close, -1)",
        b"long expected_result = -EBADF",
        b"p280_profile_has_exact(profile, P280_ENTRY, 1)",
        b"p280_profile_has_exact(profile, P280_RETURN, 1)",
        b"entry >= return_event",
        b"umount(P280_TRACE_ROOT)",
        b"(unsigned long)value.f_type == TRACEFS_MAGIC",
    )
    for token in required:
        if token not in data:
            raise HarnessError(f"Kprobe control is missing: {token!r}")
    if b"CONFIG_SHADOW_CALL_STACK" in data:
        raise HarnessError(
            "generic QEMU control must not claim target SCS validation"
        )


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=HOST_COMMAND_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as error:
        raise HarnessError(
            f"command timed out: {' '.join(command)}"
        ) from error
    if result.returncode != 0:
        raise HarnessError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}"
        )
    return result.stdout


def require_sha256(path: Path, expected: str, label: str) -> str:
    actual = sha256_path(path)
    if actual != expected:
        raise HarnessError(
            f"{label} SHA256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def _build_initramfs(
    *,
    repo: Path,
    guest_root: Path,
    output: Path,
) -> dict[str, Any]:
    source = repo / SOURCE_RELATIVE
    config = guest_root / "boot" / f"config-{KERNEL_VERSION}"
    kernel = guest_root / "boot" / f"vmlinuz-{KERNEL_VERSION}"
    if not source.is_file() or not config.is_file() or not kernel.is_file():
        raise HarnessError("source, guest config, or guest kernel is missing")
    verify_source(source.read_bytes())
    config_sha256 = require_sha256(
        config, PINNED_CONFIG_SHA256, "guest config"
    )
    kernel_sha256 = require_sha256(
        kernel, PINNED_KERNEL_SHA256, "guest kernel"
    )
    verify_guest_config(config.read_bytes())

    rootfs = output / "rootfs"
    if rootfs.exists():
        shutil.rmtree(rootfs)
    rootfs.mkdir(parents=True)
    compiler = shutil.which("aarch64-linux-gnu-gcc")
    if compiler is None:
        raise HarnessError("aarch64-linux-gnu-gcc is unavailable")
    init = rootfs / "init"
    compile_command = [
        compiler,
        "-static",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-o",
        str(init),
        str(source),
    ]
    compile_output = _run(compile_command)
    init.chmod(0o755)

    for path in rootfs.rglob("*"):
        os.utime(path, (0, 0), follow_symlinks=False)
    os.utime(rootfs, (0, 0), follow_symlinks=False)
    initramfs = output / "p280-kprobe-qemu-initramfs.cpio"
    shell = (
        "find . -print0 | LC_ALL=C sort -z | "
        "cpio --null --reproducible -o -H newc"
    )
    with initramfs.open("wb") as stream:
        try:
            result = subprocess.run(
                ["bash", "-c", shell],
                cwd=rootfs,
                check=False,
                stdout=stream,
                stderr=subprocess.PIPE,
                timeout=HOST_COMMAND_TIMEOUT_SEC,
            )
        except subprocess.TimeoutExpired as error:
            raise HarnessError("cpio timed out") from error
    if result.returncode != 0:
        raise HarnessError(
            f"cpio failed ({result.returncode}): "
            f"{result.stderr.decode('utf-8', 'replace')}"
        )
    file_output = _run(["file", str(init)]).strip()
    if "ARM aarch64" not in file_output or "statically linked" not in file_output:
        raise HarnessError(f"unexpected guest init type: {file_output}")
    return {
        "kernel": str(kernel),
        "kernel_sha256": kernel_sha256,
        "guest_config": str(config),
        "guest_config_sha256": config_sha256,
        "source": str(source),
        "source_sha256": sha256_path(source),
        "init": str(init),
        "init_sha256": sha256_path(init),
        "init_file": file_output,
        "initramfs": str(initramfs),
        "initramfs_sha256": sha256_path(initramfs),
        "compile_output": compile_output,
    }


def _qemu_command(
    *, qemu_root: Path, build: dict[str, Any]
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    binary = qemu_root / "usr/bin/qemu-system-aarch64"
    library_root = qemu_root / "usr/lib/x86_64-linux-gnu"
    if not binary.is_file():
        raise HarnessError(f"QEMU binary missing: {binary}")
    env = dict(os.environ)
    existing = env.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = (
        f"{library_root}:{existing}" if existing else str(library_root)
    )
    qemu_sha256 = require_sha256(
        binary, PINNED_QEMU_SHA256, "QEMU binary"
    )
    try:
        version_result = subprocess.run(
            [str(binary), "--version"],
            env=env,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
    except subprocess.TimeoutExpired as error:
        raise HarnessError("QEMU version query timed out") from error
    version_line = (
        version_result.stdout.splitlines()[0]
        if version_result.stdout
        else ""
    )
    if version_result.returncode != 0 or version_line != PINNED_QEMU_VERSION:
        raise HarnessError(
            "QEMU version mismatch: "
            f"expected {PINNED_QEMU_VERSION!r}, got {version_line!r}"
        )
    return (
        [
            str(binary),
            "-L",
            str(qemu_root / "usr/share/qemu"),
            "-M",
            "virt",
            "-cpu",
            "cortex-a57",
            "-smp",
            "2",
            "-m",
            "512M",
            "-nographic",
            "-no-reboot",
            "-nic",
            "none",
            "-kernel",
            build["kernel"],
            "-initrd",
            build["initramfs"],
            "-append",
            "console=ttyAMA0 rdinit=/init panic=-1 loglevel=6",
        ],
        env,
        {
            "binary": str(binary),
            "binary_sha256": qemu_sha256,
            "version": version_line,
        },
    )


def run_harness(
    *,
    repo: Path,
    guest_root: Path,
    qemu_root: Path,
    output: Path,
    timeout_sec: int,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    build = _build_initramfs(
        repo=repo,
        guest_root=guest_root,
        output=output,
    )
    command, env, qemu_identity = _qemu_command(
        qemu_root=qemu_root, build=build
    )
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert process.stdout is not None
    chunks: list[bytes] = []
    observed = b""
    deadline = started + timeout_sec
    verdict: str | None = None
    try:
        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            readable, _, _ = select.select(
                [process.stdout.fileno()], [], [], min(1.0, remaining)
            )
            if not readable:
                if process.poll() is not None:
                    break
                continue
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            chunks.append(chunk)
            observed += chunk
            print(chunk.decode("utf-8", "replace"), end="")
            if b"P280_KPROBE_QEMU result=PASS " in observed:
                verdict = VERDICT
                break
            if b"P280_KPROBE_QEMU result=FAIL " in observed:
                verdict = "FAIL_P280_KPROBE_GENERIC_QEMU_HOST_ONLY"
                break
    finally:
        process.terminate()
        try:
            tail, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            tail, _ = process.communicate(timeout=5)
        if tail:
            chunks.append(tail)
            print(tail.decode("utf-8", "replace"), end="")

    if verdict is None:
        if time.monotonic() >= deadline:
            verdict = "TIMEOUT_P280_KPROBE_GENERIC_QEMU_HOST_ONLY"
        else:
            verdict = "FAIL_P280_KPROBE_QEMU_GUEST_EXIT_HOST_ONLY"
    output_text = b"".join(chunks).decode("utf-8", "replace")
    passed = verdict == VERDICT
    report = {
        "schema": "s22plus_fyg8_p280_kprobe_qemu_control_v1",
        "verdict": verdict,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "command": command,
        "qemu_identity": qemu_identity,
        "build": build,
        "qemu_output_sha256": hashlib.sha256(
            output_text.encode("utf-8")
        ).hexdigest(),
        "scope": {
            "validated": [
                "tracefs mount and exact filesystem type",
                "isolated tracing instance and group ownership",
                "entry and return Kprobe-event registration",
                "PID1 filter and counter trace clock readback",
                "one entry and one exact signed s32 negative return value",
                "zero missed entry and return probes",
                "event, instance, and tracefs cleanup",
            ]
            if passed
            else [],
            "not_validated": [
                "S22+ Shadow Call Stack and pointer-authentication behavior",
                "S22+ DWC3-MSM target symbols and instruction sites",
                "Qualcomm USB runtime behavior",
                "physical USB enumeration",
            ],
        },
    }
    (output / "result.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "qemu-console.log").write_text(output_text, encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--guest-root", type=Path, required=True)
    parser.add_argument("--qemu-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=int, default=60)
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()
    if args.timeout_sec < 15 or args.timeout_sec > 180:
        raise HarnessError("--timeout-sec must be between 15 and 180")
    output = args.output.resolve()
    if args.build_only:
        output.mkdir(parents=True, exist_ok=True)
        result = _build_initramfs(
            repo=args.repo.resolve(),
            guest_root=args.guest_root.resolve(),
            output=output,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    result = run_harness(
        repo=args.repo.resolve(),
        guest_root=args.guest_root.resolve(),
        qemu_root=args.qemu_root.resolve(),
        output=output,
        timeout_sec=args.timeout_sec,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == VERDICT else 1


if __name__ == "__main__":
    raise SystemExit(main())
