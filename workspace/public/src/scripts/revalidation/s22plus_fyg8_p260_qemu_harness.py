#!/usr/bin/env python3
"""Build and run the bounded P2.60 E3 generic-arm64 QEMU harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
import re
import select
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


VERDICT = "PASS_P260_E3_GENERIC_QEMU_HOST_ONLY"
KERNEL_VERSION = "6.12.94+deb13-arm64"
MODULES = (
    "usb-common",
    "usbcore",
    "configfs",
    "udc-core",
    "libcomposite",
    "dummy_hcd",
    "u_serial",
    "usb_f_acm",
    "cdc-acm",
)
EXPECTED_HELPER_ORDER = (
    b"p260_mount_configfs(",
    b"p260_create_gadget(",
    b"p260_wait_tty_dev(",
    b"p260_prepare_tty_node(",
    b"p260_open_raw_tty(",
    b"p260_write_all(",
    b"p260_wait_role_and_udc(",
    b"p260_bind_udc(",
    b"p260_wait_configured(",
)
RUNTIME_RELATIVE = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p260_e3_runtime.inc.c"
)
HARNESS_RELATIVE = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p260_qemu_harness.c"
)


class HarnessError(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_runtime_source(data: bytes) -> None:
    definitions = re.findall(
        rb"^#define[ \t]+P260_CONFIGFS_MAGIC[ \t]+"
        rb"(0[xX][0-9a-fA-F]+)[lL]?[ \t]*$",
        data,
        re.MULTILINE,
    )
    if definitions != [b"0x62656570"]:
        raise HarnessError("P2.60 configfs magic is not exact 0x62656570")

    marker = b"static __attribute__((noreturn)) void p260_e3_run(void)"
    start = data.find(marker)
    if start < 0:
        raise HarnessError("P2.60 E3 entrypoint is missing")
    body = data[start:]
    cursor = 0
    for helper in EXPECTED_HELPER_ORDER:
        next_cursor = body.find(helper, cursor)
        if next_cursor < 0:
            raise HarnessError(
                f"P2.60 helper order missing {helper.decode('ascii')}"
            )
        cursor = next_cursor + len(helper)


def verify_harness_source(data: bytes) -> None:
    required = (
        b'#include "s22plus_fyg8_p260_e3_runtime.inc.c"',
        b'static const char k_qemu_udc_name[] = "dummy_udc.0";',
        b"p260_mount_configfs();",
        b"p260_create_gadget();",
        b"p260_wait_tty_dev(&major_number, &minor_number);",
        b"p260_prepare_tty_node(major_number, minor_number);",
        b"p260_open_raw_tty(&tty_fd);",
        b"p260_write_all(",
        b"p260_write_and_verify(",
        VERDICT.encode("ascii"),
    )
    for token in required:
        if data.count(token) != 1:
            raise HarnessError(
                f"QEMU harness token cardinality drifted: {token!r}"
            )
    if b"p260_wait_role_and_udc();" in data or b"p260_bind_udc();" in data:
        raise HarnessError("QEMU harness must adapt the Qualcomm role/UDC boundary")

    banner = data.find(b"p260_write_all(")
    bind = data.find(b'"/config/usb_gadget/g1/UDC"')
    if banner < 0 or bind < 0 or banner >= bind:
        raise HarnessError("QEMU harness no longer writes the banner before UDC bind")


def _find_module(module_root: Path, name: str) -> Path:
    matches = sorted(module_root.glob(f"**/{name}.ko.xz"))
    if len(matches) != 1:
        raise HarnessError(
            f"expected one {name}.ko.xz under {module_root}, found {len(matches)}"
        )
    return matches[0]


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise HarnessError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}"
        )
    return result


def _build_initramfs(
    *,
    repo: Path,
    guest_root: Path,
    output: Path,
) -> dict[str, Any]:
    runtime = repo / RUNTIME_RELATIVE
    harness = repo / HARNESS_RELATIVE
    verify_runtime_source(runtime.read_bytes())
    verify_harness_source(harness.read_bytes())

    kernel = guest_root / "boot" / f"vmlinuz-{KERNEL_VERSION}"
    module_root = guest_root / "usr" / "lib" / "modules" / KERNEL_VERSION
    if not kernel.is_file():
        raise HarnessError(f"guest kernel missing: {kernel}")

    rootfs = output / "rootfs"
    if rootfs.exists():
        shutil.rmtree(rootfs)
    (rootfs / "modules").mkdir(parents=True)

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
        "-Wno-unused-function",
        "-fno-strict-aliasing",
        "-I",
        str(harness.parent),
        "-o",
        str(init),
        str(harness),
    ]
    compile_result = _run(compile_command)
    init.chmod(0o755)

    module_receipts: dict[str, dict[str, str]] = {}
    for name in MODULES:
        source = _find_module(module_root, name)
        target = rootfs / "modules" / f"{name}.ko"
        target.write_bytes(lzma.decompress(source.read_bytes()))
        module_receipts[name] = {
            "source": str(source),
            "source_sha256": sha256_path(source),
            "decompressed_sha256": sha256_path(target),
        }

    for path in rootfs.rglob("*"):
        os.utime(path, (0, 0), follow_symlinks=False)
    os.utime(rootfs, (0, 0), follow_symlinks=False)
    initramfs = output / "p260-e3-qemu-initramfs.cpio"
    shell = (
        "find . -print0 | LC_ALL=C sort -z | "
        "cpio --null --reproducible -o -H newc"
    )
    with initramfs.open("wb") as stream:
        result = subprocess.run(
            ["bash", "-c", shell],
            cwd=rootfs,
            check=False,
            stdout=stream,
            stderr=subprocess.PIPE,
        )
    if result.returncode != 0:
        raise HarnessError(
            f"cpio failed ({result.returncode}): "
            f"{result.stderr.decode('utf-8', 'replace')}"
        )

    file_result = _run(["file", str(init)])
    if "ARM aarch64" not in file_result.stdout or "statically linked" not in file_result.stdout:
        raise HarnessError(f"unexpected guest init type: {file_result.stdout}")

    return {
        "kernel": str(kernel),
        "kernel_sha256": sha256_path(kernel),
        "runtime_sha256": sha256_path(runtime),
        "harness_sha256": sha256_path(harness),
        "init": str(init),
        "init_sha256": sha256_path(init),
        "init_file": file_result.stdout.strip(),
        "initramfs": str(initramfs),
        "initramfs_sha256": sha256_path(initramfs),
        "modules": module_receipts,
        "compile_output": compile_result.stdout,
    }


def _qemu_command(qemu_root: Path, build: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    binary = qemu_root / "usr" / "bin" / "qemu-system-aarch64"
    library_root = qemu_root / "usr" / "lib" / "x86_64-linux-gnu"
    if not binary.is_file():
        raise HarnessError(f"QEMU binary missing: {binary}")
    env = dict(os.environ)
    old_library_path = env.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = (
        f"{library_root}:{old_library_path}"
        if old_library_path
        else str(library_root)
    )
    command = [
        str(binary),
        "-L",
        str(qemu_root / "usr" / "share" / "qemu"),
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
    ]
    return command, env


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
    command, env = _qemu_command(qemu_root, build)
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
            if b"P260_QEMU result=PASS " in observed:
                verdict = VERDICT
                break
            if b"P260_QEMU result=FAIL " in observed:
                verdict = "FAIL_P260_E3_GENERIC_QEMU_HOST_ONLY"
                break
    finally:
        process.terminate()
        try:
            tail, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            tail, _ = process.communicate(timeout=5)
        if tail:
            print(tail.decode("utf-8", "replace"), end="")
            chunks.append(tail)
    if verdict is None:
        if process.returncode not in (0, -15):
            verdict = "FAIL_P260_E3_QEMU_PROCESS_HOST_ONLY"
        elif time.monotonic() >= deadline:
            verdict = "TIMEOUT_P260_E3_GENERIC_QEMU_HOST_ONLY"
        else:
            verdict = "FAIL_P260_E3_QEMU_GUEST_EXIT_HOST_ONLY"

    passed = verdict == VERDICT
    output_text = b"".join(chunks).decode("utf-8", "replace")
    report = {
        "schema": "s22plus_fyg8_p260_generic_qemu_harness_v1",
        "verdict": verdict,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "command": command,
        "build": build,
        "qemu_output_sha256": hashlib.sha256(
            output_text.encode("utf-8")
        ).hexdigest(),
        "scope": {
            "validated": [
                "generic configfs mount and statfs",
                "generic ACM gadget construction",
                "ttyGS0 materialization and raw mode",
                "pre-bind banner queue",
                "dummy_hcd UDC bind and configured state",
                "exact banner arrival through ttyACM0",
            ] if passed else [],
            "intended_validation": [
                "generic configfs mount and statfs",
                "generic ACM gadget construction",
                "ttyGS0 materialization and raw mode",
                "pre-bind banner queue",
                "dummy_hcd UDC bind and configured state",
                "exact banner arrival through ttyACM0",
            ],
            "not_validated": [
                "Qualcomm DWC3-MSM and peripheral role",
                "S22+ PHY, VBUS, Type-C, and Samsung notifier behavior",
                "physical host enumeration",
            ],
        },
    }
    (output / "result.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "qemu-console.log").write_text(
        output_text,
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--guest-root", type=Path, required=True)
    parser.add_argument("--qemu-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = args.output.resolve()
    if args.timeout_sec < 30 or args.timeout_sec > 600:
        raise HarnessError("--timeout-sec must be between 30 and 600")
    if args.build_only:
        output.mkdir(parents=True, exist_ok=True)
        result = _build_initramfs(
            repo=repo,
            guest_root=args.guest_root.resolve(),
            output=output,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    result = run_harness(
        repo=repo,
        guest_root=args.guest_root.resolve(),
        qemu_root=args.qemu_root.resolve(),
        output=output,
        timeout_sec=args.timeout_sec,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == VERDICT else 1


if __name__ == "__main__":
    raise SystemExit(main())
