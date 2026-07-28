#!/usr/bin/env python3
"""Verify the exact FYG8 sysfs text and P2.84 ingestion contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p284_contract_spec as spec


SCHEMA = "s22plus_fyg8_p284_sysfs_ingestion_oracle_v1"
VERDICT = "PASS_P284_SYSFS_INGESTION_ORACLE_HOST_ONLY"

DEFAULT_DWC3_SOURCE = Path(
    "workspace/private/inputs/kernel_source/s22plus-fyg8/"
    "dwc3-msm-core.c"
)
DEFAULT_POWER_SOURCE = Path(
    "workspace/private/inputs/kernel_source/s22plus-fyg8/"
    "power-sysfs.c"
)
DEFAULT_RUNTIME_SOURCE = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p260_e3_runtime.inc.c"
)
DEFAULT_P282_RUNTIME_SOURCE = Path(
    "workspace/public/src/native-init/s22plus_fyg8_p282_e3_runtime.inc.c"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p284_sysfs_ingestion/"
    "result.json"
)

PINNED_DWC3_SOURCE_SHA256 = (
    "1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021"
)
PINNED_POWER_SOURCE_SHA256 = (
    "8d1ef4c7799f79af6c4d59958157d30e793cac3b3e0748b57446cfaa37c19321"
)
PINNED_MODE_SHOW_SHA256 = (
    "71466affadfd34d31e1289ccfe3a1ba9af1473c416bb0f5f72b9de276f3ede10"
)
PINNED_RUNTIME_STATUS_SHOW_SHA256 = (
    "471b539d27780001de4b3c9faaf320717a3caa88fdaf511c4dd541cd29559cc0"
)
PINNED_P260_FUNCTION_SHA256 = {
    "p260_bytes_equal": (
        "a6eb61329ac45bf5152ad3797df82adf33d9d738d5a9a89e8937694aac67a254"
    ),
    "p260_read_value": (
        "9b84fb22c41416968e22dcfdbff2262e06fe6f486520b6dada20d06fe72eed87"
    ),
    "p260_expect_value": (
        "4ecc727ba0912c0fb20ad40b73ef4afe9c723fcc4ad2b75426f389071a349845"
    ),
}
PINNED_P282_WAIT_SHA256 = (
    "0572d88f05e6a265604a91eecadfcd7f9588532b8894f36d8b3523a86db37006"
)


class OracleError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": _sha256(data)}


def _stable_read(path: Path, label: str, maximum: int = 8 * 1024 * 1024) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise OracleError(f"{label} is unavailable: {path}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise OracleError(f"{label} is not a regular file")
        if not 1 <= before.st_size <= maximum:
            raise OracleError(f"{label} size is outside the bounded input")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                raise OracleError(f"{label} read was short")
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(before, field) != getattr(after, field)
        or getattr(after, field) != getattr(current, field)
        for field in fields
    ):
        raise OracleError(f"{label} changed while reading")
    return b"".join(chunks)


def extract_function(data: bytes, signature: bytes) -> bytes:
    if data.count(signature) != 1:
        raise OracleError(
            f"function signature cardinality drifted: {signature!r}"
        )
    start = data.index(signature)
    brace = data.find(b"{", start + len(signature))
    if brace < 0:
        raise OracleError(f"function body is missing: {signature!r}")
    depth = 0
    for index in range(brace, len(data)):
        byte = data[index]
        if byte == ord("{"):
            depth += 1
        elif byte == ord("}"):
            depth -= 1
            if depth == 0:
                end = index + 1
                while end < len(data) and data[end] in b" \t\r\n":
                    end += 1
                return data[start:end]
    raise OracleError(f"function body is unterminated: {signature!r}")


def _verify_source_contract(
    dwc3_source: bytes,
    power_source: bytes,
) -> dict[str, Any]:
    if _sha256(dwc3_source) != PINNED_DWC3_SOURCE_SHA256:
        raise OracleError("FYG8 dwc3-msm source hash mismatch")
    if _sha256(power_source) != PINNED_POWER_SOURCE_SHA256:
        raise OracleError("FYG8 power sysfs source hash mismatch")

    mode_show = extract_function(dwc3_source, b"static ssize_t mode_show(")
    runtime_status_show = extract_function(
        power_source, b"static ssize_t runtime_status_show("
    )
    if _sha256(mode_show) != PINNED_MODE_SHOW_SHA256:
        raise OracleError("FYG8 mode_show body hash mismatch")
    if _sha256(runtime_status_show) != PINNED_RUNTIME_STATUS_SHOW_SHA256:
        raise OracleError("FYG8 runtime_status_show body hash mismatch")

    mode_tokens = tuple(
        value.decode("ascii")
        for value in re.findall(
            rb'scnprintf\(buf, PAGE_SIZE, "([^"\\]+)\\n"\)',
            mode_show,
        )
    )
    status_tokens = tuple(
        value.decode("ascii")
        for value in re.findall(rb'output = "([^"]+)";', runtime_status_show)
    )
    if mode_tokens != spec.MODE_SHOW_TOKENS:
        raise OracleError("FYG8 mode_show token order differs")
    if status_tokens != spec.RUNTIME_STATUS_SHOW_TOKENS:
        raise OracleError("runtime_status_show token order differs")
    if (
        runtime_status_show.count(b'return sysfs_emit(buf, "%s\\n", output);')
        != 1
        or runtime_status_show.count(b"return -EIO;") != 1
    ):
        raise OracleError("runtime_status_show framing or error path differs")
    for token in spec.MODE_SHOW_TOKENS:
        expected = f'sysfs_streq(buf, "{token}")'.encode("ascii")
        count = dwc3_source.count(expected)
        if token == "none":
            if count != 0:
                raise OracleError("mode_store must derive none as its default")
        elif count != 1:
            raise OracleError(f"mode_store token differs: {token}")

    return {
        "dwc3_source": _receipt(dwc3_source),
        "power_source": _receipt(power_source),
        "mode_show": _receipt(mode_show),
        "runtime_status_show": _receipt(runtime_status_show),
        "mode_tokens": list(mode_tokens),
        "runtime_status_tokens": list(status_tokens),
        "newline_is_source_bound_not_global_sysfs_abi": True,
        "verified": True,
    }


def _verify_runtime_sources(
    p260_runtime: bytes,
    p282_runtime: bytes,
) -> dict[str, bytes]:
    functions = {
        "p260_bytes_equal": extract_function(
            p260_runtime, b"static int p260_bytes_equal("
        ),
        "p260_read_value": extract_function(
            p260_runtime, b"static long p260_read_value("
        ),
        "p260_expect_value": extract_function(
            p260_runtime, b"static long p260_expect_value("
        ),
        "p282_wait_exact_value": extract_function(
            p282_runtime, b"static long p282_wait_exact_value("
        ),
    }
    for name, expected in PINNED_P260_FUNCTION_SHA256.items():
        if _sha256(functions[name]) != expected:
            raise OracleError(f"exact {name} body hash mismatch")
    if _sha256(functions["p282_wait_exact_value"]) != PINNED_P282_WAIT_SHA256:
        raise OracleError("exact p282_wait_exact_value body hash mismatch")
    expected_retry = (
        b"        if (\n"
        b"            rc != -ENOENT\n"
        b"            && rc != -ENODEV\n"
        b"            && rc != -EIO\n"
        b"        ) {\n"
        b"            return rc;\n"
        b"        }\n"
    )
    if functions["p282_wait_exact_value"].count(expected_retry) != 1:
        raise OracleError("exact-value retry branch differs")
    return functions


def _harness_source(functions: dict[str, bytes]) -> bytes:
    joined = b"\n".join(
        functions[name]
        for name in (
            "p260_bytes_equal",
            "p260_read_value",
            "p260_expect_value",
        )
    )
    return b"""\
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define P260_EINTR 4
#define P260_EOVERFLOW 75
#define P260_EPROTO 71

static size_t cstr_len(const char *text) {
    return strlen(text);
}

static long sys_openat(const char *path, int flags, unsigned int mode) {
    int fd = openat(AT_FDCWD, path, flags, mode);
    return fd < 0 ? -errno : fd;
}

static long sys_read(int fd, void *buffer, size_t size) {
    ssize_t amount = read(fd, buffer, size);
    return amount < 0 ? -errno : amount;
}

static long sys_close(int fd) {
    return close(fd) == 0 ? 0 : -errno;
}

""" + joined + b"""\
static int p284_exact_value_retryable(long rc) {
    return rc == -ENOENT || rc == -ENODEV || rc == -EIO;
}

static int replace_file(const char *path, const void *data, size_t size) {
    int fd = open(path, O_WRONLY | O_TRUNC | O_CLOEXEC);
    if (fd < 0)
        return -1;
    ssize_t amount = write(fd, data, size);
    int close_rc = close(fd);
    return amount == (ssize_t)size && close_rc == 0 ? 0 : -1;
}

static int expect_rc(const char *name, long actual, long expected) {
    if (actual == expected)
        return 0;
    dprintf(
        STDOUT_FILENO,
        "P284_INGEST fail=%s actual=%ld expected=%ld\\n",
        name,
        actual,
        expected);
    return -1;
}

int main(void) {
    char path[] = "/tmp/p284-sysfs-XXXXXX";
    int fd = mkstemp(path);
    if (fd < 0 || close(fd) != 0)
        return 10;

    static const struct {
        const char *wire;
        const char *token;
    } valid[] = {
        {"peripheral\\n", "peripheral"},
        {"host\\n", "host"},
        {"none\\n", "none"},
        {"error\\n", "error"},
        {"unsupported\\n", "unsupported"},
        {"suspended\\n", "suspended"},
        {"suspending\\n", "suspending"},
        {"resuming\\n", "resuming"},
        {"active\\n", "active"},
    };
    for (size_t index = 0; index < sizeof(valid) / sizeof(valid[0]); ++index) {
        if (
            replace_file(path, valid[index].wire, strlen(valid[index].wire)) != 0
            || expect_rc(
                "source-token-roundtrip",
                p260_expect_value(path, valid[index].token),
                0) != 0
        )
            return 20;
    }

    if (
        replace_file(path, "none\\n", 5) != 0
        || expect_rc(
            "valid-mismatch-retry",
            p260_expect_value(path, "peripheral"),
            -EIO) != 0
    )
        return 21;
    if (
        replace_file(path, "", 0) != 0
        || expect_rc("empty-retry", p260_expect_value(path, "none"), -EIO) != 0
    )
        return 22;
    if (
        replace_file(path, "none", 4) != 0
        || expect_rc(
            "missing-newline-hard",
            p260_expect_value(path, "none"),
            -P260_EPROTO) != 0
    )
        return 23;

    char overflow[128];
    memset(overflow, 'x', sizeof(overflow));
    if (
        replace_file(path, overflow, sizeof(overflow)) != 0
        || expect_rc(
            "overflow-hard",
            p260_expect_value(path, "none"),
            -P260_EOVERFLOW) != 0
    )
        return 24;

    static const long retryable[] = {-ENOENT, -ENODEV, -EIO};
    for (size_t index = 0;
         index < sizeof(retryable) / sizeof(retryable[0]);
         ++index) {
        if (!p284_exact_value_retryable(retryable[index]))
            return 30;
    }
    static const long hard[] = {
        -P260_EPROTO,
        -P260_EOVERFLOW,
        -EACCES,
        -EPERM,
        -EINVAL,
        -ENOMEM,
        -ENXIO,
        -EBUSY,
    };
    for (size_t index = 0; index < sizeof(hard) / sizeof(hard[0]); ++index) {
        if (p284_exact_value_retryable(hard[index]))
            return 31;
    }
    if (unlink(path) != 0)
        return 40;
    dprintf(STDOUT_FILENO, "P284_INGEST result=PASS\\n");
    return 0;
}
"""


def _run_harness(
    functions: dict[str, bytes],
    *,
    compiler: str,
    qemu: str,
) -> dict[str, Any]:
    source = _harness_source(functions)
    with tempfile.TemporaryDirectory(prefix="s22-p284-ingest-") as raw:
        directory = Path(raw)
        source_path = directory / "harness.c"
        binary_path = directory / "harness"
        source_path.write_bytes(source)
        compile_command = [
            compiler,
            "-static",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-o",
            str(binary_path),
            str(source_path),
        ]
        compiled = subprocess.run(
            compile_command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        if compiled.returncode != 0:
            raise OracleError(
                "P2.84 AArch64 ingestion harness did not compile:\n"
                f"{compiled.stdout}"
            )
        file_result = subprocess.run(
            ["file", str(binary_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
        if (
            file_result.returncode != 0
            or "ARM aarch64" not in file_result.stdout
            or "statically linked" not in file_result.stdout
        ):
            raise OracleError("P2.84 ingestion harness is not static AArch64")
        executed = subprocess.run(
            [qemu, str(binary_path)],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        if (
            executed.returncode != 0
            or executed.stdout.count("P284_INGEST result=PASS\n") != 1
        ):
            raise OracleError(
                "P2.84 ingestion harness failed:\n"
                f"{executed.stdout}"
            )
        compiler_path = Path(compiler).resolve()
        qemu_path = Path(qemu).resolve()
        compiler_version = subprocess.run(
            [str(compiler_path), "--version"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        ).stdout
        qemu_version = subprocess.run(
            [str(qemu_path), "--version"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        ).stdout
        return {
            "source": _receipt(source),
            "binary": _receipt(binary_path.read_bytes()),
            "file": file_result.stdout.strip(),
            "output_sha256": _sha256(executed.stdout.encode("utf-8")),
            "substrate": {
                "compiler": {
                    "path": str(compiler_path),
                    **_receipt(_stable_read(compiler_path, "AArch64 compiler")),
                    "version_sha256": _sha256(
                        compiler_version.encode("utf-8")
                    ),
                },
                "qemu": {
                    "path": str(qemu_path),
                    **_receipt(_stable_read(qemu_path, "qemu-aarch64")),
                    "version_sha256": _sha256(qemu_version.encode("utf-8")),
                },
            },
            "cases": {
                "source_tokens": 9,
                "valid_mismatch_retry": True,
                "empty_read_retry": True,
                "missing_newline_hard": True,
                "overflow_hard": True,
                "retry_errno_count": 3,
                "representative_hard_errno_count": 8,
            },
            "verified": True,
        }


def run_oracle(
    *,
    dwc3_source_path: Path,
    power_source_path: Path,
    p260_runtime_path: Path,
    p282_runtime_path: Path,
    compiler: str,
    qemu: str,
) -> dict[str, Any]:
    spec.validate()
    source_contract = _verify_source_contract(
        _stable_read(dwc3_source_path, "FYG8 dwc3-msm source"),
        _stable_read(power_source_path, "FYG8 power sysfs source"),
    )
    p260_runtime = _stable_read(
        p260_runtime_path, "P2.60 runtime source"
    )
    p282_runtime = _stable_read(
        p282_runtime_path, "P2.82 runtime source"
    )
    functions = _verify_runtime_sources(p260_runtime, p282_runtime)
    harness = _run_harness(functions, compiler=compiler, qemu=qemu)
    payload = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "source_contract": source_contract,
        "runtime_sources": {
            "p260": _receipt(p260_runtime),
            "p282": _receipt(p282_runtime),
            "functions": {
                name: _receipt(body) for name, body in sorted(functions.items())
            },
            "verified": True,
        },
        "harness": harness,
        "policy": {
            "readback_tokens_are_normalized": True,
            "write_wire_has_one_trailing_newline": True,
            "source_specific_show_framing": True,
            "unknown_kernel_errno_is_not_silently_retried": True,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "kernel_built": False,
            "image_built": False,
            "live_authorized": False,
        },
        "verified": True,
    }
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dwc3-source", type=Path, default=DEFAULT_DWC3_SOURCE)
    parser.add_argument("--power-source", type=Path, default=DEFAULT_POWER_SOURCE)
    parser.add_argument(
        "--p260-runtime", type=Path, default=DEFAULT_RUNTIME_SOURCE
    )
    parser.add_argument(
        "--p282-runtime", type=Path, default=DEFAULT_P282_RUNTIME_SOURCE
    )
    parser.add_argument("--compiler", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--qemu", default="qemu-aarch64")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    compiler = shutil.which(args.compiler)
    qemu = shutil.which(args.qemu)
    if compiler is None or qemu is None:
        raise SystemExit("AArch64 compiler or qemu-aarch64 is unavailable")
    result = run_oracle(
        dwc3_source_path=args.dwc3_source,
        power_source_path=args.power_source,
        p260_runtime_path=args.p260_runtime,
        p282_runtime_path=args.p282_runtime,
        compiler=compiler,
        qemu=qemu,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "verdict": result["verdict"],
                "out": str(args.out),
                "verified": result["verified"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
