#!/usr/bin/env python3
"""Run the exhaustive P2.82 production classifier in pinned arm64 QEMU."""

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

import s22plus_fyg8_p280_kprobe_qemu_control as p280_qemu
import s22plus_fyg8_p282_contract_spec as contract_spec


SCHEMA = "s22plus_fyg8_p282_classifier_qemu_v1"
VERDICT = "PASS_P282_CLASSIFIER_GENERIC_QEMU_HOST_ONLY"
FAIL_VERDICT = "FAIL_P282_CLASSIFIER_GENERIC_QEMU_HOST_ONLY"
TIMEOUT_VERDICT = "TIMEOUT_P282_CLASSIFIER_GENERIC_QEMU_HOST_ONLY"

KERNEL_VERSION = p280_qemu.KERNEL_VERSION
PINNED_KERNEL_SHA256 = p280_qemu.PINNED_KERNEL_SHA256
PINNED_CONFIG_SHA256 = p280_qemu.PINNED_CONFIG_SHA256
PINNED_QEMU_SHA256 = p280_qemu.PINNED_QEMU_SHA256
PINNED_QEMU_VERSION = p280_qemu.PINNED_QEMU_VERSION
HOST_COMMAND_TIMEOUT_SEC = 60
DETAILS_EXPECTED = 46
TUPLES_EXPECTED = 567

SPEC_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p282_contract_spec.py"
)
CLASSIFIER_RELATIVE = Path(
    "workspace/public/src/native-init/"
    "s22plus_fyg8_p282_classifier.inc.c"
)

PASS_PATTERN = re.compile(
    rb"P282_CLASSIFIER_QEMU result=PASS "
    rb"details_covered=46 tuple_count=567 "
    rb"classifier_sha=([0-9a-f]{64})"
)
FAIL_PATTERN = re.compile(
    rb"P282_CLASSIFIER_QEMU result=FAIL code=([0-9]+)"
)

DEFAULTS: dict[str, dict[str, int]] = {
    "p282_classify_stop": {
        "none_readback": 1,
        "trace_authoritative": 1,
        "worker_entered": 1,
        "worker_returned": 1,
        "worker_rc": 0,
    },
    "p282_classify_suspend": {
        "trace_authoritative": 1,
        "suspend_entered": 1,
        "suspend_returned": 1,
        "suspend_rc": 0,
        "status_suspended": 1,
        "power_off_entered": 1,
        "power_off_returned": 1,
        "power_off_rc": 0,
    },
    "p282_classify_restart": {
        "peripheral_readback": 1,
        "trace_authoritative": 1,
        "worker_entered": 1,
        "worker_returned": 1,
        "worker_rc": 0,
        "resume_entered": 1,
        "resume_returned": 1,
        "resume_rc": 0,
        "init_entered": 1,
        "init_returned": 1,
        "init_rc": 0,
        "power_on_entered": 1,
        "power_on_returned": 1,
        "power_on_rc": 0,
        "notify_connect": 1,
        "status_active": 1,
        "mode_peripheral": 1,
        "exact_udc": 1,
        "off_on_zero_pair": 1,
    },
    "p282_classify_bind": {
        "cleanup_verified": 1,
        "source_consistent": 1,
        "trace_authoritative": 1,
        "pullup_returned_zero": 1,
        "run_stop_seen": 1,
        "run_stop_rc": 0,
        "repair_class": 0,
        "bind_branch": 0,
    },
    "p282_classify_final_pair": {
        "first_state": 0,
        "first_speed": 0,
        "second_state": 0,
        "second_speed": 0,
        "repair_class": 0,
        "bind_branch": 0,
    },
}

STRUCTS = {
    "p282_classify_stop": "p282_stop_observation",
    "p282_classify_suspend": "p282_suspend_observation",
    "p282_classify_restart": "p282_restart_observation",
    "p282_classify_bind": "p282_bind_observation",
    "p282_classify_final_pair": "p282_final_pair_observation",
}


class HarnessError(RuntimeError):
    """A fail-closed classifier gate error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout_sec: int = HOST_COMMAND_TIMEOUT_SEC,
) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
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


def verify_classifier_source(data: bytes) -> None:
    required_definitions = (
        b"static int p282_classify_cycle_control(",
        b"static int p282_classify_stop(",
        b"static int p282_classify_suspend(",
        b"static int p282_classify_restart(",
        b"static int p282_classify_bind(",
        b"static int p282_encode_tuple(",
        b"static int p282_classify_final_pair(",
    )
    for token in required_definitions:
        if data.count(token) != 1:
            raise HarnessError(
                f"production classifier definition drifted: {token!r}"
            )
    required_semantics = (
        b"#ifndef P282_CLASSIFIER_CONTRACT_DEFINED",
        b"observation->first_state != observation->second_state",
        b"observation->first_speed != observation->second_speed",
        b"observation->second_state == P282_STATE_CONFIGURED",
        b"observation->second_speed == P282_SPEED_HIGH",
        b"*detail = P282_TUPLE_BASE +",
        b"repair_class * P282_BIND_COUNT",
        b"P282_STATE_COUNT + state",
        b"P282_SPEED_COUNT + speed",
    )
    for token in required_semantics:
        if token not in data:
            raise HarnessError(
                f"production classifier semantic token missing: {token!r}"
            )
    forbidden = (
        b"test_mode",
        b"fixture_mode",
        b"#ifdef TEST",
        b"CLASSIFIER_FIXTURES",
    )
    for token in forbidden:
        if token in data:
            raise HarnessError(
                f"production classifier contains a test hook: {token!r}"
            )


def verify_contract() -> None:
    contract_spec.validate()
    if len(contract_spec.CLASSIFIER_FIXTURES) != DETAILS_EXPECTED:
        raise HarnessError("P2.82 fixture count is not exactly 46")
    if set(
        fixture.detail for fixture in contract_spec.CLASSIFIER_FIXTURES
    ) != set(contract_spec.DETAIL_VALUES):
        raise HarnessError("P2.82 fixtures do not cover the exact detail domain")
    if (
        contract_spec.TUPLE_COUNT != TUPLES_EXPECTED
        or len(contract_spec.tuple_values()) != TUPLES_EXPECTED
    ):
        raise HarnessError("P2.82 tuple domain is not exactly 567")


def _initializer(values: dict[str, int]) -> str:
    return ", ".join(f".{name} = {value}" for name, value in values.items())


def _fixture_block(
    index: int,
    fixture: contract_spec.ClassifierFixture,
) -> str:
    if fixture.function == "p282_classify_cycle_control":
        condition = dict(fixture.fields)["condition"]
        declaration = ""
        invocation = (
            f"{fixture.function}(0x{fixture.stage:02x}U, "
            f"{condition}U, &result)"
        )
    else:
        try:
            values = dict(DEFAULTS[fixture.function])
            struct_name = STRUCTS[fixture.function]
        except KeyError as error:
            raise HarnessError(
                f"unknown classifier fixture function: {fixture.function}"
            ) from error
        values.update(dict(fixture.fields))
        declaration = (
            f"struct {struct_name} observation = "
            f"{{ {_initializer(values)} }};"
        )
        invocation = f"{fixture.function}(&observation, &result)"
    return f"""
    {{
        struct p282_classification result = {{0}};
        {declaration}
        int rc = {invocation};
        if (rc != 1 || result.detail != 0x{fixture.detail:03x}U ||
            result.stage != 0x{fixture.stage:02x}U ||
            result.outcome != {fixture.outcome}U)
            return {index + 1};
    }}
"""


def render_guest_source(classifier_sha256: str) -> str:
    verify_contract()
    if not re.fullmatch(r"[0-9a-f]{64}", classifier_sha256):
        raise HarnessError("classifier SHA256 is malformed")
    fixture_blocks = "".join(
        _fixture_block(index, fixture)
        for index, fixture in enumerate(contract_spec.CLASSIFIER_FIXTURES)
    )
    return f"""#include <stdio.h>
#include <unistd.h>

#include "p282_classifier_contract.h"
#include "s22plus_fyg8_p282_classifier.inc.c"

static int run_detail_fixtures(void)
{{
{fixture_blocks}
    return 0;
}}

static int run_tuple_fixtures(void)
{{
    unsigned int repair;
    unsigned int bind;
    unsigned int state;
    unsigned int speed;
    unsigned int count = 0;

    for (repair = 0; repair < P282_REPAIR_COUNT; ++repair)
        for (bind = 0; bind < P282_BIND_COUNT; ++bind)
            for (state = 0; state < P282_STATE_COUNT; ++state)
                for (speed = 0; speed < P282_SPEED_COUNT; ++speed) {{
                    struct p282_final_pair_observation observation = {{
                        .first_state = state,
                        .first_speed = speed,
                        .second_state = state,
                        .second_speed = speed,
                        .repair_class = repair,
                        .bind_branch = bind,
                    }};
                    struct p282_classification result = {{0}};
                    unsigned int encoded = 0;
                    unsigned int expected_outcome =
                        state == P282_STATE_CONFIGURED &&
                        speed == P282_SPEED_HIGH
                        ? P282_OUTCOME_PROGRESS
                        : P282_OUTCOME_FAILURE;
                    int rc = p282_classify_final_pair(
                        &observation, &result);

                    if (p282_encode_tuple(
                            repair, bind, state, speed, &encoded) != 0)
                        return 1001;
                    if (rc != 1 ||
                        result.stage != P282_STAGE_FINAL ||
                        result.outcome != expected_outcome ||
                        result.detail != P282_TUPLE_BASE + count ||
                        encoded != result.detail)
                        return 1002;
                    ++count;
                }}
    if (count != {TUPLES_EXPECTED}U ||
        P282_TUPLE_BASE + count - 1U != P282_TUPLE_MAX)
        return 1003;
    return 0;
}}

int main(void)
{{
    int rc = run_detail_fixtures();

    if (rc == 0)
        rc = run_tuple_fixtures();
    if (rc == 0)
        printf(
            "P282_CLASSIFIER_QEMU result=PASS "
            "details_covered={DETAILS_EXPECTED} "
            "tuple_count={TUPLES_EXPECTED} "
            "classifier_sha={classifier_sha256}\\n");
    else
        printf("P282_CLASSIFIER_QEMU result=FAIL code=%d\\n", rc);
    fflush(stdout);
    for (;;)
        pause();
}}
"""


def compiler_identity(compiler: Path) -> dict[str, str]:
    resolved = compiler.resolve()
    version_output = _run([str(resolved), "--version"], timeout_sec=10)
    version = version_output.splitlines()[0] if version_output else ""
    if not version:
        raise HarnessError("cross-compiler version is empty")
    return {
        "path": str(resolved),
        "sha256": sha256_path(resolved),
        "version": version,
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
    *,
    repo: Path,
    guest_root: Path,
    output: Path,
) -> dict[str, Any]:
    spec_path = repo / SPEC_RELATIVE
    classifier_path = repo / CLASSIFIER_RELATIVE
    config = guest_root / "boot" / f"config-{KERNEL_VERSION}"
    kernel = guest_root / "boot" / f"vmlinuz-{KERNEL_VERSION}"
    for label, path in (
        ("contract spec", spec_path),
        ("production classifier", classifier_path),
        ("guest config", config),
        ("guest kernel", kernel),
    ):
        if not path.is_file():
            raise HarnessError(f"{label} is missing: {path}")

    classifier_data = classifier_path.read_bytes()
    verify_classifier_source(classifier_data)
    verify_contract()
    kernel_sha256 = require_sha256(
        kernel, PINNED_KERNEL_SHA256, "guest kernel"
    )
    config_sha256 = require_sha256(
        config, PINNED_CONFIG_SHA256, "guest config"
    )

    rootfs = output / "rootfs"
    if rootfs.exists():
        shutil.rmtree(rootfs)
    rootfs.mkdir(parents=True)
    contract_header = rootfs / "p282_classifier_contract.h"
    classifier_copy = rootfs / CLASSIFIER_RELATIVE.name
    guest_source = rootfs / "p282_classifier_qemu.c"
    init = rootfs / "init"
    contract_text = contract_spec.render_classifier_contract_c()
    classifier_sha256 = sha256_bytes(classifier_data)
    source_text = render_guest_source(classifier_sha256)
    contract_header.write_text(contract_text, encoding="ascii")
    classifier_copy.write_bytes(classifier_data)
    guest_source.write_text(source_text, encoding="ascii")

    compiler_name = shutil.which("aarch64-linux-gnu-gcc")
    if compiler_name is None:
        raise HarnessError("aarch64-linux-gnu-gcc is unavailable")
    compiler = Path(compiler_name)
    compiler_receipt = compiler_identity(compiler)
    compile_command = [
        str(compiler.resolve()),
        "-std=c11",
        "-static",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-o",
        str(init),
        str(guest_source),
    ]
    compile_output = _run(compile_command, cwd=rootfs)
    init.chmod(0o755)
    file_output = _run(["file", str(init)]).strip()
    if "ARM aarch64" not in file_output or "statically linked" not in file_output:
        raise HarnessError(f"unexpected guest init type: {file_output}")

    for path in rootfs.rglob("*"):
        os.utime(path, (0, 0), follow_symlinks=False)
    os.utime(rootfs, (0, 0), follow_symlinks=False)
    initramfs = output / "p282-classifier-qemu-initramfs.cpio"
    build_cpio(rootfs, initramfs)
    return {
        "kernel": str(kernel),
        "kernel_sha256": kernel_sha256,
        "guest_config": str(config),
        "guest_config_sha256": config_sha256,
        "contract_spec": str(spec_path),
        "contract_spec_sha256": sha256_path(spec_path),
        "generated_contract_sha256": sha256_bytes(
            contract_text.encode("ascii")
        ),
        "production_classifier": str(classifier_path),
        "production_classifier_sha256": classifier_sha256,
        "guest_source_sha256": sha256_bytes(source_text.encode("ascii")),
        "compiler": compiler_receipt,
        "compile_command": compile_command,
        "compile_output": compile_output,
        "init": str(init),
        "init_sha256": sha256_path(init),
        "init_file": file_output,
        "initramfs": str(initramfs),
        "initramfs_sha256": sha256_path(initramfs),
    }


def verify_qemu_version_result(returncode: int, output: str) -> str:
    version = output.splitlines()[0] if output else ""
    if returncode != 0 or version != PINNED_QEMU_VERSION:
        raise HarnessError(
            "QEMU version mismatch: "
            f"expected {PINNED_QEMU_VERSION!r}, got {version!r}"
        )
    return version


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
    *,
    qemu_root: Path,
    build: dict[str, Any],
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
    version = query_qemu_version(binary, env)
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
    return (
        command,
        env,
        {
            "path": str(binary),
            "sha256": qemu_sha256,
            "version": version,
        },
    )


def parse_guest_result(
    output: bytes,
    expected_classifier_sha256: str,
) -> tuple[str, int, int]:
    passes = PASS_PATTERN.findall(output)
    failures = FAIL_PATTERN.findall(output)
    if failures:
        return FAIL_VERDICT, 0, 0
    if len(passes) != 1:
        raise HarnessError(
            f"expected one exact guest PASS marker, found {len(passes)}"
        )
    observed_sha = passes[0].decode("ascii")
    if observed_sha != expected_classifier_sha256:
        raise HarnessError(
            "guest classifier SHA does not match the production source"
        )
    return VERDICT, DETAILS_EXPECTED, TUPLES_EXPECTED


def validate_result_schema(report: dict[str, Any]) -> None:
    required = {
        "schema",
        "verdict",
        "details_covered",
        "tuple_count",
        "elapsed_sec",
        "command",
        "substrate",
        "production_classifier_sha256",
        "contract_spec_sha256",
        "generated_contract_sha256",
        "guest_source_sha256",
        "init_sha256",
        "initramfs_sha256",
        "qemu_output_sha256",
        "scope",
    }
    if set(report) != required:
        raise HarnessError("result JSON keys do not match the exact schema")
    if report["schema"] != SCHEMA:
        raise HarnessError("result JSON schema identifier drifted")
    if report["verdict"] == VERDICT:
        if (
            report["details_covered"] != DETAILS_EXPECTED
            or report["tuple_count"] != TUPLES_EXPECTED
        ):
            raise HarnessError("PASS result has incomplete classifier coverage")
    elif report["details_covered"] != 0 or report["tuple_count"] != 0:
        raise HarnessError("non-PASS result claims classifier coverage")
    substrate = report["substrate"]
    if set(substrate) != {"kernel", "config", "qemu", "compiler"}:
        raise HarnessError("substrate receipt keys drifted")
    for label in ("kernel", "config", "qemu", "compiler"):
        receipt = substrate[label]
        if set(receipt) != {"path", "sha256", "version"}:
            raise HarnessError(f"{label} substrate receipt keys drifted")
        if not re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"]):
            raise HarnessError(f"{label} substrate SHA256 is malformed")
        if not receipt["version"]:
            raise HarnessError(f"{label} substrate version is empty")
    for key in (
        "production_classifier_sha256",
        "contract_spec_sha256",
        "generated_contract_sha256",
        "guest_source_sha256",
        "init_sha256",
        "initramfs_sha256",
        "qemu_output_sha256",
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", report[key]):
            raise HarnessError(f"{key} is malformed")


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
        qemu_root=qemu_root,
        build=build,
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
    saw_terminal_marker = False
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
            if PASS_PATTERN.search(observed) or FAIL_PATTERN.search(observed):
                saw_terminal_marker = True
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

    output_bytes = b"".join(chunks)
    if saw_terminal_marker:
        verdict, details_covered, tuple_count = parse_guest_result(
            output_bytes,
            build["production_classifier_sha256"],
        )
    elif time.monotonic() >= deadline:
        verdict, details_covered, tuple_count = TIMEOUT_VERDICT, 0, 0
    else:
        verdict, details_covered, tuple_count = FAIL_VERDICT, 0, 0

    compiler = build["compiler"]
    report = {
        "schema": SCHEMA,
        "verdict": verdict,
        "details_covered": details_covered,
        "tuple_count": tuple_count,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "command": command,
        "substrate": {
            "kernel": {
                "path": build["kernel"],
                "sha256": build["kernel_sha256"],
                "version": KERNEL_VERSION,
            },
            "config": {
                "path": build["guest_config"],
                "sha256": build["guest_config_sha256"],
                "version": KERNEL_VERSION,
            },
            "qemu": qemu_identity,
            "compiler": compiler,
        },
        "production_classifier_sha256": (
            build["production_classifier_sha256"]
        ),
        "contract_spec_sha256": build["contract_spec_sha256"],
        "generated_contract_sha256": (
            build["generated_contract_sha256"]
        ),
        "guest_source_sha256": build["guest_source_sha256"],
        "init_sha256": build["init_sha256"],
        "initramfs_sha256": build["initramfs_sha256"],
        "qemu_output_sha256": sha256_bytes(output_bytes),
        "scope": {
            "validated": [
                "production P2.82 classifier compiled for AArch64",
                "exact 46-of-46 C-band classifier fixtures executed",
                "all 567 final tuple combinations classified and encoded",
                "pinned generic-arm64 kernel, config, and QEMU substrate",
            ]
            if verdict == VERDICT
            else [],
            "not_validated": [
                "S22+ vendor-kernel execution",
                "S22+ runtime trace acquisition and ordering",
                "physical USB enumeration",
                "device flashing",
            ],
        },
    }
    validate_result_schema(report)
    (output / "result.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "qemu-console.log").write_bytes(output_bytes)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--guest-root", type=Path, required=True)
    parser.add_argument("--qemu-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=int, default=60)
    args = parser.parse_args()
    if args.timeout_sec < 15 or args.timeout_sec > 180:
        raise HarnessError("--timeout-sec must be between 15 and 180")
    report = run_harness(
        repo=args.repo.resolve(),
        guest_root=args.guest_root.resolve(),
        qemu_root=args.qemu_root.resolve(),
        output=args.output.resolve(),
        timeout_sec=args.timeout_sec,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == VERDICT else 1


if __name__ == "__main__":
    raise SystemExit(main())
