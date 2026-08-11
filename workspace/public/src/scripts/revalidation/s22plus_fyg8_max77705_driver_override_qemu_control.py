#!/usr/bin/env python3
"""Prove the platform driver_override match fence in pinned arm64 QEMU."""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import math
import os
import re
import select
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, NamedTuple


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
RAW_CAPTURE_NAME = "qemu-console.raw"
CAPTURE_MANIFEST_NAME = "qemu-console-capture.json"
RENDERED_CONSOLE_NAME = "qemu-console.log"
RESULT_NAME = "result.json"
CAPTURE_SCHEMA = "s22plus_fyg8_max77705_qemu_console_capture_v1"
CAPTURE_SOURCE = "qemu-system-aarch64 PL011 stdio"
CAPTURE_CLOCK = "host time.monotonic relative to QEMU start"
CAPTURE_KEYS = frozenset(
    {
        "schema",
        "source",
        "clock",
        "raw_file",
        "raw_byte_count",
        "raw_sha256",
        "capture_started_monotonic",
        "chunks",
    }
)
CAPTURE_CHUNK_KEYS = frozenset(
    {
        "index",
        "source",
        "byte_start",
        "byte_end",
        "received_after_start_sec",
    }
)
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


class ConsoleRecord(NamedTuple):
    text: str
    byte_start: int
    byte_end: int
    line_ending: str


class DecodedConsole(NamedTuple):
    records: tuple[ConsoleRecord, ...]
    incomplete_suffix: str
    incomplete_suffix_start: int


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


def decode_pl011_console(raw: bytes) -> DecodedConsole:
    """Decode only LF/CRLF records while retaining their raw byte geometry."""

    if b"\x00" in raw:
        raise HarnessError("PL011 console contains NUL")
    records: list[ConsoleRecord] = []
    cursor = 0
    while True:
        newline = raw.find(b"\n", cursor)
        if newline < 0:
            break
        body = raw[cursor:newline]
        line_ending = "LF"
        if body.endswith(b"\r"):
            body = body[:-1]
            line_ending = "CRLF"
        if b"\r" in body:
            raise HarnessError("PL011 console contains bare CR")
        try:
            text = body.decode("utf-8", "strict")
        except UnicodeDecodeError as error:
            raise HarnessError("PL011 console is not valid UTF-8") from error
        records.append(
            ConsoleRecord(
                text=text,
                byte_start=cursor,
                byte_end=newline + 1,
                line_ending=line_ending,
            )
        )
        cursor = newline + 1

    suffix = raw[cursor:]
    if b"\r" in suffix:
        raise HarnessError("PL011 incomplete suffix contains bare CR")
    try:
        suffix_text = suffix.decode("utf-8", "strict")
    except UnicodeDecodeError as error:
        raise HarnessError("PL011 incomplete suffix is not valid UTF-8") from error
    return DecodedConsole(
        records=tuple(records),
        incomplete_suffix=suffix_text,
        incomplete_suffix_start=cursor,
    )


def parse_pass_records(records: tuple[ConsoleRecord, ...]) -> dict[str, Any]:
    pattern = re.compile(
        r"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
        r"target=([^ ]+) blocked=([^,]+),([^ ]+) active=(\d+)"
    )
    matches = [
        match.groups()
        for record in records
        if (match := pattern.fullmatch(record.text)) is not None
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


def parse_pass_line(output: str) -> dict[str, Any]:
    """Compatibility entry point used by focused tests and older callers."""

    return parse_pass_records(decode_pl011_console(output.encode("utf-8")).records)


def parse_fail_records(records: tuple[ConsoleRecord, ...]) -> dict[str, Any]:
    pattern = re.compile(
        r"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL "
        r"stage=([^ ]+) detail=([1-9][0-9]*)"
    )
    matches = [
        match.groups()
        for record in records
        if (match := pattern.fullmatch(record.text)) is not None
    ]
    if len(matches) != 1:
        raise HarnessError(f"expected one exact FAIL line, found {len(matches)}")
    stage, detail_text = matches[0]
    detail = int(detail_text)
    if detail > 2_147_483_647:
        raise HarnessError("FAIL line detail exceeds signed int range")
    return {"stage": stage, "detail": detail}


def evaluate_console_bytes(raw: bytes) -> dict[str, Any]:
    decoded = decode_pl011_console(raw)
    pass_prefix = "MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
    fail_prefix = "MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL "
    pass_records = tuple(
        record for record in decoded.records if record.text.startswith(pass_prefix)
    )
    fail_records = tuple(
        record for record in decoded.records if record.text.startswith(fail_prefix)
    )
    if pass_prefix in decoded.incomplete_suffix or fail_prefix in decoded.incomplete_suffix:
        raise HarnessError("terminal record is incomplete")
    if len(pass_records) + len(fail_records) != 1:
        raise HarnessError(
            "expected exactly one complete terminal record, found "
            f"{len(pass_records) + len(fail_records)}"
        )
    if fail_records:
        return {
            "verdict": "FAIL_MAX77705_DRIVER_OVERRIDE_QEMU_HOST_ONLY",
            "proof": None,
            "failure": parse_fail_records(fail_records),
            "terminal_line_ending": fail_records[0].line_ending,
        }
    return {
        "verdict": VERDICT,
        "proof": parse_pass_records(pass_records),
        "failure": None,
        "terminal_line_ending": pass_records[0].line_ending,
    }


def replay_console_bytes(raw: bytes, *, expected_sha256: str | None = None) -> dict[str, Any]:
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise HarnessError(
            "replay console SHA256 mismatch: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    evaluated = evaluate_console_bytes(raw)
    return {
        "schema": "s22plus_fyg8_max77705_driver_override_qemu_replay_v1",
        "raw_byte_count": len(raw),
        "raw_sha256": actual_sha256,
        **evaluated,
    }


def complete_record_seen(observed: bytes, marker: bytes) -> bool:
    start = observed.find(marker)
    return start >= 0 and b"\n" in observed[start:]


def _write_all(stream: Any, data: bytes) -> None:
    view = memoryview(data)
    written = 0
    while written < len(view):
        amount = stream.write(view[written:])
        if amount is None or amount <= 0:
            raise HarnessError("immutable evidence write made no progress")
        written += amount


def _write_exclusive_bytes(path: Path, data: bytes) -> None:
    try:
        with path.open("xb", buffering=0) as stream:
            _write_all(stream, data)
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise HarnessError(f"immutable evidence path already exists: {path}") from error


def _write_exclusive_json(path: Path, value: dict[str, Any]) -> None:
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _write_exclusive_bytes(path, data)


def _require_capture_paths_absent(output: Path) -> None:
    for name in (
        RAW_CAPTURE_NAME,
        CAPTURE_MANIFEST_NAME,
        RENDERED_CONSOLE_NAME,
        RESULT_NAME,
    ):
        path = output / name
        if path.exists():
            raise HarnessError(f"immutable evidence path already exists: {path}")


def _capture_manifest(
    *, raw: bytes, chunks: list[dict[str, Any]], started: float
) -> dict[str, Any]:
    manifest = {
        "schema": CAPTURE_SCHEMA,
        "source": CAPTURE_SOURCE,
        "clock": CAPTURE_CLOCK,
        "raw_file": RAW_CAPTURE_NAME,
        "raw_byte_count": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "capture_started_monotonic": started,
        "chunks": chunks,
    }
    verify_capture_manifest(raw, manifest)
    return manifest


def _is_finite_nonnegative_number(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(float(value)) and value >= 0
    except (OverflowError, TypeError, ValueError):
        return False


def verify_capture_manifest(raw: bytes, manifest: dict[str, Any]) -> None:
    if frozenset(manifest) != CAPTURE_KEYS:
        raise HarnessError("console capture top-level keys mismatch")
    if manifest.get("schema") != CAPTURE_SCHEMA:
        raise HarnessError("console capture schema mismatch")
    if manifest.get("source") != CAPTURE_SOURCE:
        raise HarnessError("console capture source mismatch")
    if manifest.get("clock") != CAPTURE_CLOCK:
        raise HarnessError("console capture clock mismatch")
    if manifest.get("raw_file") != RAW_CAPTURE_NAME:
        raise HarnessError("console capture raw filename mismatch")
    if (
        not isinstance(manifest.get("raw_byte_count"), int)
        or isinstance(manifest.get("raw_byte_count"), bool)
        or manifest["raw_byte_count"] != len(raw)
    ):
        raise HarnessError("console capture byte count mismatch")
    if not _is_finite_nonnegative_number(
        manifest.get("capture_started_monotonic")
    ):
        raise HarnessError("console capture start clock is invalid")
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if manifest.get("raw_sha256") != actual_sha256:
        raise HarnessError("console capture SHA256 mismatch")
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list):
        raise HarnessError("console capture chunks are missing")
    expected_start = 0
    previous_timestamp = 0.0
    tail_seen = False
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            raise HarnessError("console capture chunk is malformed")
        if frozenset(chunk) != CAPTURE_CHUNK_KEYS:
            raise HarnessError("console capture chunk keys mismatch")
        byte_start = chunk.get("byte_start")
        byte_end = chunk.get("byte_end")
        if (
            not isinstance(chunk.get("index"), int)
            or isinstance(chunk.get("index"), bool)
            or chunk["index"] != index
            or not isinstance(byte_start, int)
            or isinstance(byte_start, bool)
            or byte_start != expected_start
            or not isinstance(byte_end, int)
            or isinstance(byte_end, bool)
            or byte_end <= expected_start
        ):
            raise HarnessError("console capture chunk geometry mismatch")
        source = chunk.get("source")
        if source == "select-read":
            if tail_seen:
                raise HarnessError("console capture source order mismatch")
        elif source == "communicate-tail":
            if tail_seen or index != len(chunks) - 1:
                raise HarnessError("console capture source order mismatch")
            tail_seen = True
        else:
            raise HarnessError("console capture chunk source mismatch")
        timestamp = chunk.get("received_after_start_sec")
        if (
            not _is_finite_nonnegative_number(timestamp)
            or timestamp < previous_timestamp
        ):
            raise HarnessError("console capture chunk clock mismatch")
        previous_timestamp = float(timestamp)
        expected_start = byte_end
    if expected_start != len(raw):
        raise HarnessError("console capture chunks do not cover raw bytes")


def replay_console_capture(
    raw_path: Path,
    manifest_path: Path,
    *,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256) is None:
        raise HarnessError("expected capture manifest SHA256 is not canonical")
    manifest_sha256 = require_sha256(
        manifest_path,
        expected_manifest_sha256,
        "QEMU console capture manifest",
    )
    raw = raw_path.read_bytes()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HarnessError("console capture manifest is unreadable") from error
    if not isinstance(manifest, dict):
        raise HarnessError("console capture manifest is not an object")
    verify_capture_manifest(raw, manifest)
    result = replay_console_bytes(raw, expected_sha256=manifest["raw_sha256"])
    result["capture_manifest_sha256"] = manifest_sha256
    return result


def run_harness(
    *,
    repo: Path,
    guest_root: Path,
    qemu_root: Path,
    output: Path,
    timeout_sec: int,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    _require_capture_paths_absent(output)
    raw_path = output / RAW_CAPTURE_NAME
    try:
        raw_stream = raw_path.open("xb", buffering=0)
    except FileExistsError as error:
        raise HarnessError(
            f"immutable evidence path already exists: {raw_path}"
        ) from error
    with raw_stream:
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
        chunk_receipts: list[dict[str, Any]] = []
        observed = b""
        deadline = started + timeout_sec
        verdict: str | None = None
        pass_marker = b"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
        fail_marker = b"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL "

        def preserve_chunk(chunk: bytes, source: str) -> None:
            byte_start = sum(len(value) for value in chunks)
            _write_all(raw_stream, chunk)
            os.fsync(raw_stream.fileno())
            chunks.append(chunk)
            chunk_receipts.append(
                {
                    "index": len(chunk_receipts),
                    "source": source,
                    "byte_start": byte_start,
                    "byte_end": byte_start + len(chunk),
                    "received_after_start_sec": round(
                        time.monotonic() - started, 6
                    ),
                }
            )

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
                preserve_chunk(chunk, "select-read")
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
                preserve_chunk(tail, "communicate-tail")
                print(tail.decode("utf-8", "replace"), end="")

    raw_output = b"".join(chunks)
    capture = _capture_manifest(raw=raw_output, chunks=chunk_receipts, started=started)
    require_sha256(raw_path, capture["raw_sha256"], "QEMU raw console capture")
    _write_exclusive_json(output / CAPTURE_MANIFEST_NAME, capture)
    _write_exclusive_bytes(output / RENDERED_CONSOLE_NAME, raw_output)
    if verdict is None:
        verdict = (
            "TIMEOUT_MAX77705_DRIVER_OVERRIDE_QEMU_HOST_ONLY"
            if time.monotonic() >= deadline
            else "FAIL_MAX77705_DRIVER_OVERRIDE_QEMU_GUEST_EXIT_HOST_ONLY"
        )
    proof = None
    failure = None
    observer_error = None
    terminal_line_ending = None
    if verdict in (
        VERDICT,
        "FAIL_MAX77705_DRIVER_OVERRIDE_QEMU_HOST_ONLY",
    ):
        try:
            evaluated = evaluate_console_bytes(raw_output)
            verdict = evaluated["verdict"]
            proof = evaluated["proof"]
            failure = evaluated["failure"]
            terminal_line_ending = evaluated["terminal_line_ending"]
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
        "failure": failure,
        "observer_error": observer_error,
        "terminal_line_ending": terminal_line_ending,
        "capture": capture,
        "qemu_output_sha256": capture["raw_sha256"],
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
    _write_exclusive_json(output / RESULT_NAME, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--guest-root", type=Path)
    parser.add_argument("--qemu-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=int, default=90)
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--replay-console", type=Path)
    parser.add_argument("--replay-capture-manifest", type=Path)
    parser.add_argument("--expected-capture-manifest-sha256")
    args = parser.parse_args()
    if args.timeout_sec < 30 or args.timeout_sec > 180:
        raise HarnessError("--timeout-sec must be between 30 and 180")
    output = args.output.resolve()
    replay_values = (
        args.replay_console,
        args.replay_capture_manifest,
        args.expected_capture_manifest_sha256,
    )
    if any(value is not None for value in replay_values) and not all(
        value is not None for value in replay_values
    ):
        raise HarnessError(
            "replay console, manifest, and expected manifest SHA256 are required together"
        )
    if args.replay_console is not None:
        if args.build_only or args.guest_root is not None or args.qemu_root is not None:
            raise HarnessError("replay mode cannot build or run QEMU")
        output.mkdir(parents=True, exist_ok=True)
        replay_path = output / "replay-result.json"
        if replay_path.exists():
            raise HarnessError(f"immutable evidence path already exists: {replay_path}")
        result = replay_console_capture(
            args.replay_console.resolve(),
            args.replay_capture_manifest.resolve(),
            expected_manifest_sha256=args.expected_capture_manifest_sha256,
        )
        _write_exclusive_json(replay_path, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["verdict"] == VERDICT else 1
    if args.guest_root is None:
        raise HarnessError("--guest-root is required outside replay mode")
    if args.build_only:
        output.mkdir(parents=True, exist_ok=True)
        result = _build_initramfs(
            repo=args.repo.resolve(),
            guest_root=args.guest_root.resolve(),
            output=output,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.qemu_root is None:
        raise HarnessError("--qemu-root is required for QEMU execution")
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
