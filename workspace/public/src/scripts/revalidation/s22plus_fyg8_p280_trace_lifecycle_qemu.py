#!/usr/bin/env python3
"""Run the shared P2.80 four-plus-six trace lifecycle in arm64 QEMU."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import s22plus_fyg8_p280_kprobe_qemu_control as control
import s22plus_fyg8_p280_source_contract as p280


SCHEMA = "s22plus_fyg8_p280_trace_lifecycle_qemu_v1"
VERDICT = "PASS_P280_TRACE_LIFECYCLE_GENERIC_QEMU_HOST_ONLY"
SOURCE_RELATIVE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_p280_trace_lifecycle_qemu_harness.inc.c"
)
PASS_RE = re.compile(
    rb"P280_TRACE_LIFECYCLE result=PASS role_events=4 bind_events=6 "
    rb"role_ns=(?P<role>[0-9]+) bind_ns=(?P<bind>[0-9]+) "
    rb"parser=ok cleanup=ok nmissed=0"
)
FAIL_RE = re.compile(
    rb"P280_TRACE_LIFECYCLE result=FAIL stage=[A-Za-z0-9_-]+\r?\n"
)
SANITY_NS = 5_000_000_000
RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P280-TRACE-LIFECYCLE-QEMU-V1"
).digest()[:16]


class HarnessError(RuntimeError):
    pass


def _receipt(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "size": path.stat().st_size,
        "sha256": control.sha256_path(path),
    }


def verify_harness_source(data: bytes) -> None:
    required = (
        (b"p280_trace_setup(&control, events, event_count)", 1),
        (b"p280_trace_finish(&control, &quality)", 1),
        (b"p280_parse_trace_records(&control, records, &count)", 1),
        (b"p280_parse_bind_result(&bind_control, &bind_result)", 3),
        (b"p280_qemu_role_events[]", 1),
        (b"p280_qemu_bind_events[]", 1),
        (b"p280_trace_deadline_disable(&control)", 1),
        (b"P280_TRACE_LIFECYCLE result=PASS role_events=4 bind_events=6", 1),
    )
    for token, expected in required:
        if data.count(token) != expected:
            raise HarnessError(
                f"trace lifecycle token cardinality drifted: {token!r}"
            )
    for token in (
        b"unknown: on=1",
        b"pull_in: on=1junk",
        b"pull_in: on=1\"",
        b"P280_QEMU_SANITY_NS 5000000000ULL",
        b"common_pid == 1",
        b"on == 1",
    ):
        if token not in data:
            raise HarnessError(f"trace lifecycle fixture missing: {token!r}")
    if b"dwc3" in data or b"Qualcomm" in data:
        raise HarnessError("generic trace lifecycle must not emulate Qualcomm")


def _materialize_sources(repo: Path, directory: Path) -> tuple[Path, Path]:
    generated = p280.generate(repo)
    source = p280.source_bytes(repo)
    harness = repo / SOURCE_RELATIVE
    verify_harness_source(harness.read_bytes())

    for key in (
        "plan_header",
        "e3_runtime_include",
        "p260_e3_runtime_include",
        "trace_descriptor_header",
    ):
        (directory / p280.MATERIALIZED_FILENAMES[key]).write_bytes(source[key])
    checkpoint = directory / p280.MATERIALIZED_FILENAMES["checkpoint_client"]
    checkpoint.write_bytes(generated["checkpoint"])

    runtime = generated["runtime"]
    marker = b"__attribute__((noreturn)) void _start(void) {"
    if runtime.count(marker) != 1:
        raise HarnessError("generated P2.80 final entrypoint cardinality drifted")
    runtime = runtime.replace(
        marker,
        b"__attribute__((noreturn)) void p280_candidate_start(void) {",
        1,
    )
    runtime += (
        b'\n#include "'
        + SOURCE_RELATIVE.name.encode("ascii")
        + b'"\n'
    )
    runtime_path = directory / p280.MATERIALIZED_FILENAMES["runtime_wrapper"]
    runtime_path.write_bytes(runtime)
    shutil.copy2(harness, directory / SOURCE_RELATIVE.name)
    return runtime_path, checkpoint


def _build_initramfs(
    *,
    repo: Path,
    guest_root: Path,
    output: Path,
) -> dict[str, Any]:
    config = guest_root / "boot" / f"config-{control.KERNEL_VERSION}"
    kernel = guest_root / "boot" / f"vmlinuz-{control.KERNEL_VERSION}"
    if not config.is_file() or not kernel.is_file():
        raise HarnessError("pinned guest config or kernel is missing")
    config_sha256 = control.require_sha256(
        config, control.PINNED_CONFIG_SHA256, "guest config"
    )
    kernel_sha256 = control.require_sha256(
        kernel, control.PINNED_KERNEL_SHA256, "guest kernel"
    )
    control.verify_guest_config(config.read_bytes())

    rootfs = output / "rootfs"
    if rootfs.exists():
        shutil.rmtree(rootfs)
    source_dir = output / "source"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    rootfs.mkdir(parents=True)
    source_dir.mkdir(parents=True)
    runtime, checkpoint = _materialize_sources(repo, source_dir)

    compiler = shutil.which("aarch64-linux-gnu-gcc")
    if compiler is None:
        raise HarnessError("aarch64-linux-gnu-gcc is unavailable")
    init = rootfs / "init"
    define = p280.p252.p233._run_id_define(RUN_ID)
    compile_command = [
        compiler,
        *p280.p252.p233.legacy_e1.COMPILE_FLAGS,
        "-DS22PLUS_FYG8_P233_PROFILE=3",
        f"-DS22PLUS_FYG8_P233_RUN_ID_BYTES={define}",
        "-I",
        str(source_dir),
        "-I",
        str(repo / "workspace/public/src/native-init"),
        str(runtime),
        str(checkpoint),
        "-o",
        str(init),
    ]
    try:
        compile_output = control._run(compile_command)
    except control.HarnessError as error:
        raise HarnessError(str(error)) from error
    init.chmod(0o755)
    for path in rootfs.rglob("*"):
        os.utime(path, (0, 0), follow_symlinks=False)
    os.utime(rootfs, (0, 0), follow_symlinks=False)
    initramfs = output / "p280-trace-lifecycle-initramfs.cpio"
    try:
        control.build_cpio(rootfs, initramfs)
    except control.HarnessError as error:
        raise HarnessError(str(error)) from error
    file_output = control._run(["file", str(init)]).strip()
    if (
        "ARM aarch64" not in file_output
        or "statically linked" not in file_output
    ):
        raise HarnessError(f"unexpected guest init type: {file_output}")
    return {
        "kernel": str(kernel),
        "kernel_sha256": kernel_sha256,
        "guest_config": str(config),
        "guest_config_sha256": config_sha256,
        "runtime": _receipt(runtime),
        "checkpoint": _receipt(checkpoint),
        "harness": _receipt(repo / SOURCE_RELATIVE),
        "init": _receipt(init),
        "init_file": file_output,
        "initramfs": _receipt(initramfs),
        "compile_output": compile_output,
    }


def _run_sample(
    *,
    command: list[str],
    env: dict[str, str],
    timeout_sec: int,
) -> dict[str, Any]:
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert process.stdout is not None
    output = bytearray()
    deadline = started + timeout_sec
    match: re.Match[bytes] | None = None
    try:
        while time.monotonic() < deadline:
            readable, _, _ = select.select(
                [process.stdout.fileno()],
                [],
                [],
                min(1.0, max(0.0, deadline - time.monotonic())),
            )
            if not readable:
                if process.poll() is not None:
                    break
                continue
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            output.extend(chunk)
            if FAIL_RE.search(output) is not None:
                break
            match = PASS_RE.search(output)
            if match is not None:
                break
    finally:
        process.terminate()
        try:
            tail, _ = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            tail, _ = process.communicate(timeout=5)
        output.extend(tail)
    if match is None:
        match = PASS_RE.search(output)
    if match is None:
        text = bytes(output).decode("utf-8", "replace")
        raise HarnessError(f"QEMU trace lifecycle did not pass:\n{text}")
    role_ns = int(match.group("role"))
    bind_ns = int(match.group("bind"))
    if role_ns >= SANITY_NS or bind_ns >= SANITY_NS:
        raise HarnessError("QEMU trace phase exceeded the five-second sanity")
    return {
        "elapsed_sec": round(time.monotonic() - started, 3),
        "role_ns": role_ns,
        "bind_ns": bind_ns,
        "console_sha256": hashlib.sha256(output).hexdigest(),
        "verified": True,
    }


def run_harness(
    *,
    repo: Path,
    guest_root: Path,
    qemu_root: Path,
    output: Path,
    timeout_sec: int,
    samples: int,
) -> dict[str, Any]:
    if samples < 5 or samples > 10:
        raise HarnessError("cold sample count must be between 5 and 10")
    output.mkdir(parents=True, exist_ok=True)
    build = _build_initramfs(
        repo=repo,
        guest_root=guest_root,
        output=output,
    )
    try:
        command, env, qemu_identity = control._qemu_command(
            qemu_root=qemu_root,
            build={
                "kernel": build["kernel"],
                "initramfs": build["initramfs"]["path"],
            },
        )
    except control.HarnessError as error:
        raise HarnessError(str(error)) from error
    results = [
        _run_sample(command=command, env=env, timeout_sec=timeout_sec)
        for _index in range(samples)
    ]
    _source_data, source_receipts = p280.source_receipts(repo)
    report = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "source_contract_id": p280.CONTRACT_ID,
        "source_receipts": source_receipts,
        "cold_sample_count": len(results),
        "samples": results,
        "command": command,
        "qemu_identity": qemu_identity,
        "build": build,
        "scope": {
            "validated": [
                "shared P2.80 trace setup, exact readback, finish, and cleanup",
                "four-event then six-event isolated lifecycle",
                "runtime C parser malformed and nesting fixtures",
                "zero missed probes and one trace record per owned event",
                "each phase below the five-second control sanity threshold",
            ],
            "not_validated": [
                "Qualcomm DWC3-MSM targets or USB behavior",
                "S22+ SCS/PAC behavior",
                "physical enumeration",
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
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()
    try:
        if args.build_only:
            result = _build_initramfs(
                repo=args.repo.resolve(),
                guest_root=args.guest_root.resolve(),
                output=args.output.resolve(),
            )
        else:
            result = run_harness(
                repo=args.repo.resolve(),
                guest_root=args.guest_root.resolve(),
                qemu_root=args.qemu_root.resolve(),
                output=args.output.resolve(),
                timeout_sec=args.timeout_sec,
                samples=args.samples,
            )
    except (
        HarnessError,
        control.HarnessError,
        OSError,
        subprocess.TimeoutExpired,
    ) as error:
        print(json.dumps({"verdict": "FAIL_CLOSED", "error": str(error)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
