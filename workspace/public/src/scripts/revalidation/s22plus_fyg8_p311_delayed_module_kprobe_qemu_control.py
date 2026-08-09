#!/usr/bin/env python3
"""Prove delayed module-local Kprobe arming in pinned generic-arm64 QEMU."""

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
VERDICT = "PASS_P311_DELAYED_MODULE_KPROBE_QEMU_HOST_ONLY"
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
    "s22plus_fyg8_p311_delayed_module_kprobe_qemu_control.c"
)
MODULES = ("usb-common", "usbcore", "udc-core", "dummy_hcd")
PINNED_MODULE_SHA256 = {
    "usb-common": (
        "160d74999d6f22d8ed951d6519b84f0875d55dfda0f1d754d1e94c9e345d9d28",
        "4dccd6b0e441beba62aa84aedbf40fbb67eedd01587e85637c2d4c77c1b37ce0",
    ),
    "usbcore": (
        "8d73ad01f8646f5ec37063d97c7d1577492093b4446bd75c2e5dc5893cb2d352",
        "666df6120bb5acfe4343c432bc606cfae628011356fa69ecd6c3fb1ecf9d4016",
    ),
    "udc-core": (
        "d79a67aff601ffe772658b7aae13230c4dd22214b8dc84920e141c2ed97a1a84",
        "22ffb43967f4de912ce693c5d6653f1ec380ed5474e0099fa6d7a06b39a88790",
    ),
    "dummy_hcd": (
        "914528c45313c90a908dce135a8411f6d16862f2e7044e7b1e01577f436cfee5",
        "bf79de0ae52f0df07af88530d5c09bf8e0e3831b370e9f6b332708fed3d8b057",
    ),
}
REQUIRED_CONFIG = (
    "CONFIG_KALLSYMS_ALL=y",
    "CONFIG_KPROBES=y",
    "CONFIG_KRETPROBES=y",
    "CONFIG_KPROBE_EVENTS=y",
    "CONFIG_FTRACE=y",
    "CONFIG_TRACING=y",
    "CONFIG_MODULES=y",
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
            "guest kernel lacks required delayed-Kprobe config: "
            + ", ".join(missing)
        )


def verify_source(data: bytes) -> None:
    cardinalities = (
        (b'#define P311_GROUP "p282"', 1),
        (b'#define P311_MODULE "dummy_hcd"', 1),
        (b'#define P311_SYMBOL "dummy_hcd_probe"', 1),
        (b'#define P311_SYMBOL_OFFSET "+0x4c"', 1),
        (b'#define P311_SYMBOL_OFFSET_READBACK "+76"', 1),
        (b'P311_MODULE ":" P311_SYMBOL "\\n"', 1),
        (b'P311_MODULE ":" P311_SYMBOL P311_SYMBOL_OFFSET "\\n"', 1),
        (b'"common_pid > 0\\n"', 4),
        (b'P311_TRACE_ROOT "/kprobe_profile"', 1),
        (b'"P311_DELAYED_MODULE_KPROBE result=PASS module=%s symbol=%s "', 1),
    )
    for token, expected in cardinalities:
        if data.count(token) != expected:
            raise HarnessError(
                f"delayed-Kprobe source token cardinality drifted: {token!r}"
            )
    required = (
        b'p311_load_module("usb-common")',
        b'p311_load_module("usbcore")',
        b'p311_load_module("udc-core")',
        b"p311_verify_pending_registration()",
        b'p311_write_exact(P311_INSTANCE_ROOT "/tracing_on", "1\\n")',
        b"p311_load_module(P311_MODULE)",
        b"entry_hits != entry_records",
        b"offset_hits != offset_records",
        b"entry_missed != 0U",
        b"offset_missed != 0U",
        b'"-:" P311_GROUP "/" P311_ENTRY "\\n"',
        b'"-:" P311_GROUP "/" P311_OFFSET "\\n"',
        b"umount(P311_TRACE_ROOT)",
    )
    for token in required:
        if token not in data:
            raise HarnessError(f"delayed-Kprobe source is missing: {token!r}")


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


def _find_module(module_root: Path, name: str) -> Path:
    matches = sorted(module_root.glob(f"**/{name}.ko.xz"))
    if len(matches) != 1:
        raise HarnessError(
            f"expected one {name}.ko.xz under {module_root}, found {len(matches)}"
        )
    return matches[0]


def verify_dummy_callsite(module: Path) -> dict[str, Any]:
    readelf = _run(["aarch64-linux-gnu-readelf", "-Ws", str(module)])
    matches = re.findall(
        r"^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+)\s+FUNC\s+LOCAL\s+"
        r"DEFAULT\s+\d+\s+dummy_hcd_probe$",
        readelf,
        re.MULTILINE,
    )
    if matches != [("0000000000000008", "332")]:
        raise HarnessError(
            f"unexpected dummy_hcd_probe symbol identity: {matches!r}"
        )
    objdump = _run(["aarch64-linux-gnu-objdump", "-d", str(module)])
    start = objdump.find("<dummy_hcd_probe>:")
    end = objdump.find("\n\n", start)
    if start < 0 or end < 0:
        raise HarnessError("dummy_hcd_probe disassembly boundary is missing")
    body = objdump[start:end]
    prior = re.search(r"^\s*50:\s+([0-9a-f]+)\s+bl\s+", body, re.MULTILINE)
    site = re.search(r"^\s*54:\s+([0-9a-f]+)\s+(\S+)", body, re.MULTILINE)
    if prior is None or site is None:
        raise HarnessError(
            "dummy_hcd_probe+0x4c is not the instruction immediately after BL"
        )
    return {
        "symbol": "dummy_hcd_probe",
        "symbol_value": "0x8",
        "symbol_size": 332,
        "probe_offset": "0x4c",
        "prior_address": "0x50",
        "prior_mnemonic": "bl",
        "site_address": "0x54",
        "site_mnemonic": site.group(2),
        "module_sha256": sha256_path(module),
    }


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
    module_root = guest_root / "usr" / "lib" / "modules" / KERNEL_VERSION
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
        "-Werror",
        "-o",
        str(init),
        str(source),
    ]
    compile_output = _run(compile_command)
    init.chmod(0o755)

    module_receipts: dict[str, dict[str, str]] = {}
    for name in MODULES:
        compressed_expected, decompressed_expected = PINNED_MODULE_SHA256[name]
        compressed = _find_module(module_root, name)
        require_sha256(compressed, compressed_expected, f"{name} compressed module")
        target = rootfs / "modules" / f"{name}.ko"
        target.write_bytes(lzma.decompress(compressed.read_bytes()))
        require_sha256(target, decompressed_expected, f"{name} module")
        module_receipts[name] = {
            "source": str(compressed),
            "source_sha256": compressed_expected,
            "decompressed_sha256": decompressed_expected,
        }
    callsite = verify_dummy_callsite(rootfs / "modules" / "dummy_hcd.ko")

    for path in rootfs.rglob("*"):
        os.utime(path, (0, 0), follow_symlinks=False)
    os.utime(rootfs, (0, 0), follow_symlinks=False)
    initramfs = output / "p311-delayed-module-kprobe-initramfs.cpio"
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
        "modules": module_receipts,
        "callsite": callsite,
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
    qemu_sha256 = require_sha256(
        binary, PINNED_QEMU_SHA256, "QEMU binary"
    )
    version_line = query_qemu_version(binary, env)
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
            if b"P311_DELAYED_MODULE_KPROBE result=PASS " in observed:
                verdict = VERDICT
                break
            if b"P311_DELAYED_MODULE_KPROBE result=FAIL " in observed:
                verdict = "FAIL_P311_DELAYED_MODULE_KPROBE_QEMU_HOST_ONLY"
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
            verdict = "TIMEOUT_P311_DELAYED_MODULE_KPROBE_QEMU_HOST_ONLY"
        else:
            verdict = "FAIL_P311_DELAYED_MODULE_KPROBE_GUEST_EXIT_HOST_ONLY"
    output_text = b"".join(chunks).decode("utf-8", "replace")
    passed = verdict == VERDICT
    report = {
        "schema": "s22plus_fyg8_p311_delayed_module_kprobe_qemu_control_v1",
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
                "absent module-local symbol and offset registration",
                "pending event enable before target module load",
                "MODULE_STATE_COMING arm before synchronous module probe",
                "equal nonzero symbol and post-BL offset records",
                "profile hits equal records with zero missed probes",
                "event, instance, and tracefs cleanup",
            ]
            if passed
            else [],
            "not_validated": [
                "S22+ module loader implementation",
                "S22+ Shadow Call Stack and pointer authentication",
                "Qualcomm PHY callsite offsets and return registers",
                "physical USB behavior",
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
