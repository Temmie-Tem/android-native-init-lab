#!/usr/bin/env python3
"""Prove the platform driver_override match fence in pinned arm64 QEMU."""

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
import time
from pathlib import Path
from typing import Any


KERNEL_VERSION = "6.12.94+deb13-arm64"
VERDICT = "PASS_MAX77705_DRIVER_OVERRIDE_QEMU_HOST_ONLY"
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
PINNED_MODULE_SHA256 = (
    "7ced5d7abb0734d0bbae457e60ccae04893bc0d82313c8c568dd1933f00b2fc5",
    "e726b8eaacd2b97db92b86d867cfc88e3f6ec911d8609cfb25951ec541e8835b",
)
SOURCE_RELATIVE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_max77705_driver_override_qemu_control.c"
)
MODULE_RELATIVE = Path("kernel/drivers/virtio/virtio_mmio.ko.xz")
HOST_COMMAND_TIMEOUT_SEC = 60
REQUIRED_CONFIG = (
    "CONFIG_MODULES=y",
    "CONFIG_MODULE_UNLOAD=y",
    "CONFIG_OF=y",
    "CONFIG_SYSFS=y",
    "CONFIG_VIRTIO=y",
    "CONFIG_VIRTIO_MMIO=m",
)


class HarnessError(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_sha256(path: Path, expected: str, label: str) -> str:
    actual = sha256_path(path)
    if actual != expected:
        raise HarnessError(
            f"{label} SHA256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def verify_guest_config(data: bytes) -> None:
    lines = set(data.decode("ascii").splitlines())
    missing = [value for value in REQUIRED_CONFIG if value not in lines]
    if missing:
        raise HarnessError(
            "guest kernel lacks required platform-override config: "
            + ", ".join(missing)
        )


def verify_source(data: bytes) -> None:
    cardinalities = (
        (b'#define CONTROL_MODULE "virtio_mmio"', 1),
        (b'#define CONTROL_DRIVER "virtio-mmio"', 1),
        (b'#define CONTROL_OVERRIDE "s22plus-max77705-block"', 1),
        (b"#define CONTROL_ACTIVE_COUNT 3U", 1),
        (b'"/sys/bus/platform/drivers_probe"', 1),
        (b"SYS_finit_module", 1),
        (b"SYS_delete_module", 1),
        (b'"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS target=%s "', 1),
    )
    for token, expected in cardinalities:
        if data.count(token) != expected:
            raise HarnessError(
                f"driver-override source token cardinality drifted: {token!r}"
            )
    forbidden = (b'"/unbind"', b'"/bind"', b"platform_device_register")
    for token in forbidden:
        if token in data:
            raise HarnessError(
                f"driver-override control acquired a forbidden shortcut: {token!r}"
            )

    marker = b"int main(void)"
    start = data.find(marker)
    if start < 0:
        raise HarnessError("driver-override main is missing")
    body = data[start:]
    ordered = (
        b"control_load_module();",
        b"control_discover_active(&active);",
        b"control_unload_module();",
        b"control_set_override(active.names[1], CONTROL_OVERRIDE",
        b"control_set_override(active.names[2], CONTROL_OVERRIDE",
        b"control_load_module();",
        b"control_require_binding(active.names[0], true);",
        b"control_require_binding(active.names[1], false);",
        b"control_require_binding(active.names[2], false);",
        b'control_set_override(active.names[1], "\\n");',
        b'control_set_override(active.names[2], "\\n");',
        b"control_reprobe(active.names[1]);",
        b"control_reprobe(active.names[2]);",
        b"control_unload_module();",
    )
    cursor = 0
    for token in ordered:
        position = body.find(token, cursor)
        if position < 0:
            raise HarnessError(
                f"driver-override proof order missing {token!r}"
            )
        cursor = position + len(token)


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
        raise HarnessError(f"command timed out: {' '.join(command)}") from error
    if result.returncode != 0:
        raise HarnessError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}"
        )
    return result.stdout


def build_cpio(rootfs: Path, initramfs: Path) -> None:
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


def _build_initramfs(
    *, repo: Path, guest_root: Path, output: Path
) -> dict[str, Any]:
    source = repo / SOURCE_RELATIVE
    config = guest_root / "boot" / f"config-{KERNEL_VERSION}"
    kernel = guest_root / "boot" / f"vmlinuz-{KERNEL_VERSION}"
    compressed_module = (
        guest_root
        / "usr/lib/modules"
        / KERNEL_VERSION
        / MODULE_RELATIVE
    )
    for required in (source, config, kernel, compressed_module):
        if not required.is_file():
            raise HarnessError(f"required input is missing: {required}")
    verify_source(source.read_bytes())
    verify_guest_config(config.read_bytes())
    config_sha256 = require_sha256(
        config, PINNED_CONFIG_SHA256, "guest config"
    )
    kernel_sha256 = require_sha256(
        kernel, PINNED_KERNEL_SHA256, "guest kernel"
    )
    compressed_sha256 = require_sha256(
        compressed_module,
        PINNED_MODULE_SHA256[0],
        "virtio_mmio compressed module",
    )

    rootfs = output / "rootfs"
    if rootfs.exists():
        shutil.rmtree(rootfs)
    (rootfs / "modules").mkdir(parents=True)
    compiler = shutil.which("aarch64-linux-gnu-gcc")
    if compiler is None:
        raise HarnessError("aarch64-linux-gnu-gcc is unavailable")
    init = rootfs / "init"
    compile_output = _run(
        [
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
    )
    init.chmod(0o755)
    module = rootfs / "modules/virtio_mmio.ko"
    module.write_bytes(lzma.decompress(compressed_module.read_bytes()))
    module_sha256 = require_sha256(
        module, PINNED_MODULE_SHA256[1], "virtio_mmio module"
    )

    for path in rootfs.rglob("*"):
        os.utime(path, (0, 0), follow_symlinks=False)
    os.utime(rootfs, (0, 0), follow_symlinks=False)
    initramfs = output / "max77705-driver-override-qemu-initramfs.cpio"
    build_cpio(rootfs, initramfs)
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
        "module": str(module),
        "module_compressed_sha256": compressed_sha256,
        "module_sha256": module_sha256,
        "compile_output": compile_output,
    }


def verify_qemu_version_result(returncode: int, output: str) -> str:
    version_line = output.splitlines()[0] if output else ""
    if returncode != 0 or version_line != PINNED_QEMU_VERSION:
        raise HarnessError(
            "QEMU version mismatch: "
            f"expected {PINNED_QEMU_VERSION!r}, got {version_line!r}"
        )
    return version_line


def query_qemu_version(binary: Path, env: dict[str, str]) -> str:
    try:
        result = subprocess.run(
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
    return verify_qemu_version_result(result.returncode, result.stdout)


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
    qemu_sha256 = require_sha256(binary, PINNED_QEMU_SHA256, "QEMU binary")
    version_line = query_qemu_version(binary, env)
    command = [
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
    ]
    for index in range(3):
        command.extend(
            [
                "-object",
                f"rng-builtin,id=rng{index}",
                "-device",
                f"virtio-rng-device,rng=rng{index}",
            ]
        )
    return command, env, {
        "binary": str(binary),
        "binary_sha256": qemu_sha256,
        "version": version_line,
    }


def parse_pass_line(output: str) -> dict[str, Any]:
    pattern = re.compile(
        r"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
        r"target=([^ ]+) blocked=([^,]+),([^ ]+) active=(\d+)"
    )
    matches = [
        match.groups()
        for line in output.splitlines()
        if (match := pattern.fullmatch(line)) is not None
    ]
    if len(matches) != 1:
        raise HarnessError(f"expected one PASS line, found {len(matches)}")
    target, blocker1, blocker2, count = matches[0]
    if int(count) != 3 or len({target, blocker1, blocker2}) != 3:
        raise HarnessError("PASS line has invalid device cardinality")
    if any(not value.endswith(".virtio_mmio") for value in matches[0][:3]):
        raise HarnessError("PASS line contains a non-platform control device")
    return {
        "target": target,
        "blocked": [blocker1, blocker2],
        "active_count": int(count),
    }


def complete_record_seen(observed: bytes, marker: bytes) -> bool:
    start = observed.find(marker)
    return start >= 0 and b"\n" in observed[start:]


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
        repo=repo, guest_root=guest_root, output=output
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
    pass_marker = b"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
    fail_marker = b"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL "
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
            if complete_record_seen(observed, pass_marker):
                verdict = VERDICT
                break
            if complete_record_seen(observed, fail_marker):
                verdict = "FAIL_MAX77705_DRIVER_OVERRIDE_QEMU_HOST_ONLY"
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

    output_text = b"".join(chunks).decode("utf-8", "replace")
    (output / "qemu-console.log").write_text(output_text, encoding="utf-8")
    if verdict is None:
        verdict = (
            "TIMEOUT_MAX77705_DRIVER_OVERRIDE_QEMU_HOST_ONLY"
            if time.monotonic() >= deadline
            else "FAIL_MAX77705_DRIVER_OVERRIDE_QEMU_GUEST_EXIT_HOST_ONLY"
        )
    proof = None
    observer_error = None
    if verdict == VERDICT:
        try:
            proof = parse_pass_line(output_text)
        except HarnessError as error:
            observer_error = str(error)
            verdict = "FAIL_MAX77705_DRIVER_OVERRIDE_TERMINAL_PARSE_HOST_ONLY"
    report = {
        "schema": "s22plus_fyg8_max77705_driver_override_qemu_control_v1",
        "verdict": verdict,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "command": command,
        "qemu_identity": qemu_identity,
        "build": build,
        "proof": proof,
        "observer_error": observer_error,
        "qemu_output_sha256": hashlib.sha256(
            output_text.encode("utf-8")
        ).hexdigest(),
        "scope": {
            "validated": [
                "three real QEMU virtio-mmio platform devices bind without overrides",
                "two pre-registration blocking overrides preserve only one target bind",
                "override readback matches before driver registration",
                "clearing each override plus normal drivers_probe binds both controls",
                "module unload returns all three devices to an unbound state",
            ]
            if verdict == VERDICT
            else [],
            "not_validated": [
                "S22+ sysfs path implementation",
                "Qualcomm QUPv3, GPI, or GENI binding",
                "Max77705 I2C transfer or physical MUX behavior",
                "candidate packaging or any device authority",
            ],
        },
    }
    (output / "result.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--guest-root", type=Path, required=True)
    parser.add_argument("--qemu-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=int, default=90)
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()
    if args.timeout_sec < 30 or args.timeout_sec > 180:
        raise HarnessError("--timeout-sec must be between 30 and 180")
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
