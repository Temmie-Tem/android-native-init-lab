#!/usr/bin/env python3
"""Build and independently audit the host-only FYG8 R4W1-E E1 runtime."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_r4w1e_checkpoint_contract as carrier


SCHEMA = "s22plus_fyg8_r4w1e_e1_host_contract_v1"
VERDICT = "PASS_R4W1E_E1_RUNTIME_HOST_CONTRACT"
TARGET = carrier.TARGET

DEFAULT_RUNTIME = Path(
    "workspace/public/src/native-init/s22plus_r4w1e_e1_runtime.c"
)
DEFAULT_CHILD = Path(
    "workspace/public/src/native-init/s22plus_r4w1e_e1_child.c"
)
DEFAULT_CLIENT = Path(
    "workspace/public/src/native-init/s22plus_r4w1e_checkpoint.c"
)
DEFAULT_HEADER = Path(
    "workspace/public/src/native-init/s22plus_r4w1e_checkpoint.h"
)
DEFAULT_INVENTORY = Path("docs/module-map/s22plus-fyg8/inventory.tsv")

SOURCE_MAX_SIZE = 1_048_576
CHILD_TOKEN = b"S22PLUS_R4W1E_E1_CHILD_OK:4c3e58c0785b\n"
CHILD_EXIT = 23

COMPILER_ENVIRONMENT_KEYS = (
    "AS",
    "BFD_PLUGIN",
    "C_INCLUDE_PATH",
    "COMPILER_PATH",
    "CPATH",
    "CPLUS_INCLUDE_PATH",
    "DEPENDENCIES_OUTPUT",
    "GCC_COMPARE_DEBUG",
    "GCC_EXEC_PREFIX",
    "LD",
    "LDEMULATION",
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "LIBRARY_PATH",
    "OBJC_INCLUDE_PATH",
    "SUNPRO_DEPENDENCIES",
)

MODULE_SPECS = (
    (
        "smem.ko",
        "smem",
        28_704,
        "27a80d5598329d6a526384d09806de63983204988748ea4e7d3fccfafc24a524",
    ),
    (
        "minidump.ko",
        "minidump",
        37_312,
        "e5e6f4dfe1ddac2cd4f8d15c11a50d4d32b6e9de278fedbed44747630a5c554d",
    ),
    (
        "qcom-scm.ko",
        "qcom_scm",
        218_384,
        "e12ba8661808c2c47acf42c9939157e509fcdb5b98f6e650f79b92dba18a1af3",
    ),
    (
        "qcom_wdt_core.ko",
        "qcom_wdt_core",
        48_640,
        "ef484fb4f1f17586ff63852e0ea9579d07f275f7966ad117d20039055c2d7599",
    ),
    (
        "gh_virt_wdt.ko",
        "gh_virt_wdt",
        18_944,
        "f030c5486a41b1fbe4b0ea3aa85a401dd16daa1f1a551a626f6ea424ee90dd39",
    ),
)

E1_STEPS = (
    ("S22_R4W1E_STAGE_PROC_MOUNTED", 0, "mount_proc()"),
    ("S22_R4W1E_STAGE_SYS_MOUNTED", 0, "mount_sys()"),
    ("S22_R4W1E_STAGE_DEV_TMPFS_MOUNTED", 0, "mount_dev()"),
    ("S22_R4W1E_STAGE_RUN_TMPFS_MOUNTED", 0, "mount_run()"),
    (
        "S22_R4W1E_STAGE_DEV_NODES_VERIFIED",
        0,
        "setup_and_verify_dev_null()",
    ),
    ("S22_R4W1E_STAGE_CHILD_EXEC_STARTED", 0, "child_start(&child)"),
    (
        "S22_R4W1E_STAGE_CHILD_TOKEN_VERIFIED",
        0,
        "child_verify_token(&child)",
    ),
    ("S22_R4W1E_STAGE_CHILD_REAPED", 0, "child_reap(&child)"),
    ("S22_R4W1E_STAGE_WDT_MODULE_0", 0, "load_and_verify_module(0U)"),
    ("S22_R4W1E_STAGE_WDT_MODULE_1", 1, "load_and_verify_module(1U)"),
    ("S22_R4W1E_STAGE_WDT_MODULE_2", 2, "load_and_verify_module(2U)"),
    ("S22_R4W1E_STAGE_WDT_MODULE_3", 3, "load_and_verify_module(3U)"),
    ("S22_R4W1E_STAGE_WDT_MODULE_4", 4, "load_and_verify_module(4U)"),
    (
        "S22_R4W1E_STAGE_WDT_MODULES_VERIFIED",
        0,
        "verify_exact_modules()",
    ),
)

STAGE_VALUES = {
    "S22_R4W1E_STAGE_PROC_MOUNTED": 0x10,
    "S22_R4W1E_STAGE_SYS_MOUNTED": 0x11,
    "S22_R4W1E_STAGE_DEV_TMPFS_MOUNTED": 0x12,
    "S22_R4W1E_STAGE_RUN_TMPFS_MOUNTED": 0x13,
    "S22_R4W1E_STAGE_DEV_NODES_VERIFIED": 0x14,
    "S22_R4W1E_STAGE_CHILD_EXEC_STARTED": 0x20,
    "S22_R4W1E_STAGE_CHILD_TOKEN_VERIFIED": 0x21,
    "S22_R4W1E_STAGE_CHILD_REAPED": 0x22,
    "S22_R4W1E_STAGE_WDT_MODULE_0": 0x30,
    "S22_R4W1E_STAGE_WDT_MODULE_1": 0x31,
    "S22_R4W1E_STAGE_WDT_MODULE_2": 0x32,
    "S22_R4W1E_STAGE_WDT_MODULE_3": 0x33,
    "S22_R4W1E_STAGE_WDT_MODULE_4": 0x34,
    "S22_R4W1E_STAGE_WDT_MODULES_VERIFIED": 0x35,
    "S22_R4W1E_STAGE_E1_SUCCESS": 0x3F,
}

RUNTIME_SYSCALLS = {
    "NR_DUP3": 24,
    "NR_MKNODAT": 33,
    "NR_MKDIRAT": 34,
    "NR_MOUNT": 40,
    "NR_STATFS": 43,
    "NR_OPENAT": 56,
    "NR_CLOSE": 57,
    "NR_PIPE2": 59,
    "NR_READ": 63,
    "NR_WRITE": 64,
    "NR_EXIT": 93,
    "NR_NANOSLEEP": 101,
    "NR_KILL": 129,
    "NR_GETPID": 172,
    "NR_CLONE": 220,
    "NR_EXECVE": 221,
    "NR_WAIT4": 260,
    "NR_FINIT_MODULE": 273,
}
CLIENT_SYSCALLS = {"NR_OPENAT": 56, "NR_CLOSE": 57, "NR_WRITE": 64}
CHILD_SYSCALLS = {"NR_WRITE": 64, "NR_EXIT": 93}

EXPECTED_SOURCE_SHA256 = {
    "runtime": "d0767ebd1b10a9631c4306fe9d02e21faa3e49afcdb82e66fa77aeb1872e48cf",
    "child": "2af86dda0f6c93ee90996d89c9803bd84bab16b909d25b732b69144fe8760e14",
    "client": "9012a764887e3e37436d1396bacf53e63a70a0143941b7f3b8b2bb6255884703",
    "header": "1a720dca985c159266a8dc281131de3c916ea223efec831a132a6d7217b44712",
    "inventory": "35f1a7b903fc3582d3d51c4f119b993d154874e632465b2e212e0bf56a37ab7b",
}

COMPILE_FLAGS = (
    "-nostdlib",
    "-static",
    "-ffreestanding",
    "-fno-builtin",
    "-fno-stack-protector",
    "-fno-asynchronous-unwind-tables",
    "-fno-unwind-tables",
    "-ffunction-sections",
    "-fdata-sections",
    "-Os",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-Wl,--build-id=none",
    "-Wl,--gc-sections",
    "-Wl,-e,_start",
    "-Wl,-z,noexecstack",
)


class CheckError(ValueError):
    """A fail-closed E1 host-contract error."""


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise CheckError("repository root not found")


def resolve(root: Path, value: Path) -> Path:
    candidate = value if value.is_absolute() else root / value
    return Path(os.path.abspath(candidate))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_direct(path: Path, label: str, max_size: int = SOURCE_MAX_SIZE) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise CheckError(f"{label} is unavailable: {path}") from exc
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise CheckError(f"{label} is not a direct regular file: {path}")
    if before.st_size <= 0 or before.st_size > max_size:
        raise CheckError(f"{label} size outside bound: {before.st_size}")
    data = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if identity_before != identity_after or len(data) != before.st_size:
        raise CheckError(f"{label} changed while reading")
    return data


def decode_ascii(data: bytes, label: str) -> str:
    try:
        return data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise CheckError(f"{label} is not ASCII") from exc


def extract_function(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise CheckError(f"function signature missing: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise CheckError(f"function body missing: {signature}")
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise CheckError(f"unterminated function: {signature}")


def normalize_c(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def expected_raw_wrapper(wrapper: str) -> str:
    if wrapper == "syscall6":
        return '''static inline long syscall6(
    long nr,
    long a0,
    long a1,
    long a2,
    long a3,
    long a4,
    long a5) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x3 asm("x3") = a3;
    register long x4 asm("x4") = a4;
    register long x5 asm("x5") = a5;
    register long x8 asm("x8") = nr;
    asm volatile(
        "svc #0"
        : "+r"(x0)
        : "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5), "r"(x8)
        : "memory");
    return x0;
}'''
    if wrapper == "syscall3":
        return '''static inline long syscall3(long nr, long a0, long a1, long a2) {
    register long x0 asm("x0") = a0;
    register long x1 asm("x1") = a1;
    register long x2 asm("x2") = a2;
    register long x8 asm("x8") = nr;
    asm volatile(
        "svc #0"
        : "+r"(x0)
        : "r"(x1), "r"(x2), "r"(x8)
        : "memory");
    return x0;
}'''
    raise CheckError(f"unknown raw syscall wrapper: {wrapper}")


def check_syscall_source(
    text: str,
    wrapper: str,
    expected_definitions: dict[str, int],
    expected_calls: tuple[str, ...],
    label: str,
) -> dict[str, Any]:
    definitions = {
        name: int(value)
        for name, value in re.findall(
            r"^#define (NR_[A-Z0-9_]+) ([0-9]+)$", text, flags=re.MULTILINE
        )
    }
    if definitions != expected_definitions:
        raise CheckError(f"{label} syscall definition mismatch: {definitions}")
    if text.count('"svc #0"') != 1 or len(re.findall(r"\bsvc\b", text)) != 1:
        raise CheckError(f"{label} raw supervisor-call cardinality mismatch")
    wrapper_body = extract_function(text, f"static inline long {wrapper}(")
    if normalize_c(wrapper_body) != normalize_c(expected_raw_wrapper(wrapper)):
        raise CheckError(f"{label} raw syscall ABI wrapper mismatch")
    call_text = text.replace(wrapper_body, "", 1)
    raw_arguments = tuple(
        argument.strip()
        for argument in re.findall(
            rf"\b{re.escape(wrapper)}\(\s*([^,\n]+)\s*,", call_text
        )
    )
    if any(not re.fullmatch(r"NR_[A-Z0-9_]+", value) for value in raw_arguments):
        raise CheckError(f"{label} has a non-symbolic syscall number: {raw_arguments}")
    calls = raw_arguments
    if Counter(calls) != Counter(expected_calls):
        raise CheckError(f"{label} syscall wrapper call mismatch: {calls}")
    if text.count(wrapper) != len(expected_calls) + 1:
        raise CheckError(f"{label} syscall wrapper reference cardinality mismatch")
    return {
        "definitions": definitions,
        "wrapper_calls": list(calls),
        "raw_svc_count": 1,
        "verified": True,
    }


def audit_disassembly_syscalls(
    text: str, expected_numbers: set[int], label: str
) -> dict[str, Any]:
    current_x8: int | None = None
    observed: list[int] = []
    for line in text.splitlines():
        if re.search(r"^[0-9a-f]+ <[^>]+>:$", line.strip()):
            current_x8 = None
            continue
        if re.search(r"\b[a-z0-9.]+\s+[wx]8,", line):
            immediate = re.search(r"\bmov\s+[wx]8,\s+#(0x[0-9a-f]+|[0-9]+)\b", line)
            current_x8 = int(immediate.group(1), 0) if immediate else None
        if re.search(r"\bsvc\s+#0x0\b", line):
            if current_x8 is None:
                raise CheckError(f"{label} has svc without a static x8 syscall number")
            observed.append(current_x8)
    if not observed or set(observed) != expected_numbers:
        raise CheckError(
            f"{label} compiled syscall set mismatch: {sorted(set(observed))}"
        )
    return {
        "numbers": sorted(set(observed)),
        "svc_count": len(observed),
        "verified": True,
    }


def check_header(text: str) -> dict[str, Any]:
    definitions = {
        name: int(value, 16)
        for name, value in re.findall(
            r"^#define (S22_R4W1E_STAGE_[A-Z0-9_]+) 0x([0-9a-f]+)U$",
            text,
            flags=re.MULTILINE,
        )
    }
    if definitions != STAGE_VALUES:
        raise CheckError(f"E1 header stage map mismatch: {definitions}")
    required = (
        "struct s22_r4w1e_checkpoint_client",
        "s22_r4w1e_checkpoint_client_init",
        "s22_r4w1e_checkpoint_progress",
        "s22_r4w1e_checkpoint_failure",
        "s22_r4w1e_checkpoint_success",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise CheckError(f"checkpoint header tokens missing: {missing}")
    return {"stages": definitions, "verified": True}


def check_client(text: str) -> dict[str, Any]:
    required = (
        'sys_openat("/proc/s22_checkpoint", O_WRONLY | O_CLOEXEC)',
        "written != (long)sizeof(request)",
        "client->stage = stage;",
        "client->terminal = outcome != S22_R4W1E_OUTCOME_PROGRESS;",
        "0xedb88320U",
        "#define S22_R4W1E_PROFILE_E1 1U",
        "uint32_t crc = ~0U;",
        "return crc ^ ~0U;",
        "request.profile = S22_R4W1E_PROFILE_E1;",
        "#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__",
        "offsetof(struct s22_r4w1e_checkpoint_request, detail) == 8U",
        "offsetof(struct s22_r4w1e_checkpoint_request, run_id) == 12U",
        "offsetof(struct s22_r4w1e_checkpoint_request, crc32) == 28U",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise CheckError(f"checkpoint client contract missing: {missing}")
    publish = extract_function(text, "static long publish(")
    ordering = (
        "e1_next_stage(client->stage) != stage",
        "request.crc32 = checkpoint_crc32",
        'sys_openat("/proc/s22_checkpoint"',
        "sys_write((int)fd, &request, sizeof(request))",
        "sys_close((int)fd)",
        "client->stage = stage;",
    )
    positions = [publish.find(token) for token in ordering]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise CheckError("checkpoint publish ordering is not fail-closed")
    if text.count('sys_openat("/proc/s22_checkpoint"') != 1:
        raise CheckError("checkpoint node open cardinality mismatch")
    openat_body = extract_function(text, "static long sys_openat(")
    expected_openat = '''static long sys_openat(const char *path, int flags) {
    return syscall6(
        NR_OPENAT, AT_FDCWD, (long)(uintptr_t)path, flags, 0, 0, 0);
}'''
    if normalize_c(openat_body) != normalize_c(expected_openat):
        raise CheckError("checkpoint client openat argument routing mismatch")
    syscall_contract = check_syscall_source(
        text,
        "syscall6",
        CLIENT_SYSCALLS,
        ("NR_OPENAT", "NR_WRITE", "NR_CLOSE"),
        "checkpoint client",
    )
    return {
        "request_size": 32,
        "profile": 1,
        "crc32": "IEEE seed=~0 xorout=~0 polynomial=0xedb88320",
        "byte_order": "little-endian",
        "reopen_per_checkpoint": True,
        "syscalls": syscall_contract,
        "verified": True,
    }


def parse_runtime_steps(e1_body: str) -> tuple[tuple[str, int, str], ...]:
    matches = re.findall(
        r"E1_REQUIRE\((S22_R4W1E_STAGE_[A-Z0-9_]+),\s*"
        r"([0-9]+)U,\s*([^;]+)\);",
        e1_body,
    )
    return tuple((stage, int(item), operation.strip()) for stage, item, operation in matches)


def check_runtime(text: str) -> dict[str, Any]:
    module_pairs = tuple(
        re.findall(r'\{"([A-Za-z0-9_.-]+\.ko)", "([A-Za-z0-9_]+)"\}', text)
    )
    expected_pairs = tuple((file_name, runtime) for file_name, runtime, _, _ in MODULE_SPECS)
    if module_pairs != expected_pairs:
        raise CheckError(f"E1 runtime module order mismatch: {module_pairs}")
    e1_body = extract_function(text, "static void e1_run(void)")
    steps = parse_runtime_steps(e1_body)
    if steps != E1_STEPS:
        raise CheckError(f"E1 stage-to-operation mismatch: {steps}")

    macro_start = text.find("#define E1_REQUIRE")
    e1_start = text.find("static void e1_run(void)")
    if macro_start < 0 or e1_start < 0 or macro_start > e1_start:
        raise CheckError("E1_REQUIRE definition placement mismatch")
    macro = text[macro_start:e1_start]
    macro_order = (
        "long e1_operation_result = (operation);",
        "if (e1_operation_result != 0)",
        "fail_at((stage), (item_index), e1_operation_result);",
        "s22_r4w1e_checkpoint_progress(",
        "if (e1_checkpoint_result != 0)",
        "quiet_park();",
    )
    positions = [macro.find(token) for token in macro_order]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise CheckError("E1 operation/checkpoint dominance weakened")

    fail_body = extract_function(text, "static void fail_at(")
    checkpoint_calls = {
        "progress": text.count("s22_r4w1e_checkpoint_progress"),
        "failure": text.count("s22_r4w1e_checkpoint_failure"),
        "success": text.count("s22_r4w1e_checkpoint_success"),
    }
    if checkpoint_calls != {"progress": 1, "failure": 1, "success": 1}:
        raise CheckError(f"E1 checkpoint call cardinality mismatch: {checkpoint_calls}")
    if (
        macro.count("s22_r4w1e_checkpoint_progress(") != 1
        or fail_body.count("s22_r4w1e_checkpoint_failure(") != 1
        or e1_body.count("s22_r4w1e_checkpoint_success(") != 1
    ):
        raise CheckError("E1 checkpoint call escaped its authorized control site")
    if text.count("E1_REQUIRE(") != len(E1_STEPS) + 1:
        raise CheckError("E1_REQUIRE call cardinality mismatch")

    if fail_body.find("s22_r4w1e_checkpoint_failure(") > fail_body.find(
        "quiet_park();"
    ):
        raise CheckError("E1 failure checkpoint follows park")
    terminal_order = (
        e1_body.find("verify_exact_modules()"),
        e1_body.find("s22_r4w1e_checkpoint_success(&g_checkpoint)"),
        e1_body.rfind("quiet_park();"),
    )
    if any(position < 0 for position in terminal_order) or terminal_order != tuple(
        sorted(terminal_order)
    ):
        raise CheckError("E1 terminal success ordering mismatch")

    required = (
        "if (sys_getpid() != 1)",
        "S22_R4W1E_E1_RUN_ID_BYTES",
        '"proc", "/proc", "proc"',
        '"sysfs", "/sys", "sysfs"',
        '"tmpfs", "/dev", "tmpfs"',
        '"tmpfs", "/run", "tmpfs"',
        '"/dev/null", S_IFCHR | 0600U',
        "sys_statfs(target, &probe)",
        "wait_for_exec_result(child)",
        "child_abort(child, -EIO)",
        "child_abort(child, -ETIMEDOUT)",
        "token_equals(token, used, k_child_token)",
        "status == (23 << 8)",
        "verify_module_prefix(index)",
        "while (sys_wait4(-1, &status, WNOHANG) > 0)",
        "sys_nanosleep(10000000000LL)",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise CheckError(f"E1 runtime contract missing: {missing}")
    forbidden = (
        "/dev/block",
        "/config",
        "configfs",
        "ttyGS",
        "/sys/class/udc",
        "switch_root",
        "/bin/sh",
        "system(",
        "popen(",
        "sec_log_buf.ko",
    )
    hits = [token for token in forbidden if token in text]
    if hits:
        raise CheckError(f"forbidden E1 runtime scope: {hits}")
    syscall_contract = check_syscall_source(
        text,
        "syscall6",
        RUNTIME_SYSCALLS,
        tuple(RUNTIME_SYSCALLS),
        "E1 runtime",
    )
    return {
        "module_order": [pair[0] for pair in module_pairs],
        "steps": [
            {"stage": STAGE_VALUES[stage], "item_index": item, "operation": operation}
            for stage, item, operation in steps
        ],
        "terminal_stage": STAGE_VALUES["S22_R4W1E_STAGE_E1_SUCCESS"],
        "checkpoint_calls": checkpoint_calls,
        "syscalls": syscall_contract,
        "verified": True,
    }


def check_child(text: str) -> dict[str, Any]:
    required = (
        CHILD_TOKEN.decode("ascii").rstrip("\n"),
        "NR_WRITE 64",
        "NR_EXIT 93",
        "sys_exit(111);",
        "sys_exit(23);",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise CheckError(f"E1 child contract missing: {missing}")
    if "NR_OPEN" in text or "NR_EXEC" in text or "NR_CLONE" in text:
        raise CheckError("E1 child gained filesystem or process authority")
    syscall_contract = check_syscall_source(
        text,
        "syscall3",
        CHILD_SYSCALLS,
        ("NR_EXIT", "NR_WRITE"),
        "E1 child",
    )
    return {
        "token": CHILD_TOKEN.decode("ascii"),
        "exit_status": CHILD_EXIT,
        "syscalls": syscall_contract,
        "verified": True,
    }


def check_inventory(text: str) -> dict[str, Any]:
    rows: dict[str, tuple[str, int, str]] = {}
    for line in text.splitlines()[1:]:
        fields = line.split("\t")
        if len(fields) < 4:
            continue
        try:
            size = int(fields[3])
        except ValueError:
            continue
        rows[fields[0]] = (fields[1], size, fields[2])
    for file_name, runtime, size, digest in MODULE_SPECS:
        if rows.get(file_name) != (runtime, size, digest):
            raise CheckError(f"tracked module inventory mismatch: {file_name}")
    if "sec_log_buf.ko" not in rows:
        raise CheckError("tracked inventory lacks the excluded sec_log_buf module")
    return {
        "modules": [
            {"file": file_name, "runtime": runtime, "size": size, "sha256": digest}
            for file_name, runtime, size, digest in MODULE_SPECS
        ],
        "sec_log_buf_excluded": True,
        "verified": True,
    }


def run_command(
    argv: list[str | Path],
    *,
    cwd: Path | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    for key in COMPILER_ENVIRONMENT_KEYS:
        environment.pop(key, None)
    environment.update({"LC_ALL": "C", "LANG": "C", "SOURCE_DATE_EPOCH": "0"})
    return subprocess.run(
        [str(value) for value in argv],
        cwd=cwd,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def require_ok(result: subprocess.CompletedProcess[bytes], label: str) -> None:
    if result.returncode != 0:
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        raise CheckError(f"{label} failed rc={result.returncode}: {output}")


@contextmanager
def without_compiler_environment():
    saved = {
        key: os.environ[key]
        for key in COMPILER_ENVIRONMENT_KEYS
        if key in os.environ
    }
    for key in saved:
        del os.environ[key]
    try:
        yield
    finally:
        for key in COMPILER_ENVIRONMENT_KEYS:
            os.environ.pop(key, None)
        os.environ.update(saved)


def require_tools() -> dict[str, str]:
    names = (
        "aarch64-linux-gnu-gcc",
        "aarch64-linux-gnu-strip",
        "aarch64-linux-gnu-readelf",
        "aarch64-linux-gnu-nm",
        "aarch64-linux-gnu-objdump",
        "gcc",
        "file",
        "qemu-aarch64",
    )
    resolved = {name: shutil.which(name) for name in names}
    missing = [name for name, path in resolved.items() if path is None]
    if missing:
        raise CheckError(f"required E1 host tools missing: {missing}")
    return {name: str(path) for name, path in resolved.items()}


def write_run_header(path: Path, run_id: bytes) -> None:
    values = ",".join(f"0x{value:02x}" for value in run_id)
    path.write_text(
        f"#define S22_R4W1E_E1_RUN_ID_BYTES {{{values}}}\n",
        encoding="ascii",
    )


def probe_client_request(
    build_dir: Path,
    client_text: str,
    header_data: bytes,
    run_id: bytes,
    tools: dict[str, str],
) -> dict[str, Any]:
    syscall_body = extract_function(client_text, "static inline long syscall6(")
    probe_syscall = r'''static uint8_t g_probe_request[32];
static size_t g_probe_request_size;
static int g_probe_fd_open;

static int probe_text_equal(const char *left, const char *right) {
    size_t index = 0;
    while (left[index] != '\0' && left[index] == right[index]) {
        ++index;
    }
    return left[index] == right[index];
}

static inline long syscall6(
    long nr,
    long a0,
    long a1,
    long a2,
    long a3,
    long a4,
    long a5) {
    if (nr == NR_OPENAT && a0 == AT_FDCWD &&
        probe_text_equal((const char *)(uintptr_t)a1, "/proc/s22_checkpoint") &&
        a2 == (O_WRONLY | O_CLOEXEC) && a3 == 0 && a4 == 0 && a5 == 0) {
        g_probe_fd_open = 1;
        return 7;
    }
    if (nr == NR_WRITE && g_probe_fd_open && a0 == 7 && a2 == 32 &&
        a3 == 0 && a4 == 0 && a5 == 0) {
        const uint8_t *source = (const uint8_t *)(uintptr_t)a1;
        for (size_t index = 0; index < 32U; ++index) {
            g_probe_request[index] = source[index];
        }
        g_probe_request_size = 32U;
        return 32;
    }
    if (nr == NR_CLOSE && g_probe_fd_open && a0 == 7 &&
        a1 == 0 && a2 == 0 && a3 == 0 && a4 == 0 && a5 == 0) {
        g_probe_fd_open = 0;
        return 0;
    }
    return -38;
}'''
    probe_main = r'''

#include <stdio.h>

int main(void) {
    static const uint8_t run_id[16] = S22_R4W1E_PROBE_RUN_ID_BYTES;
    struct s22_r4w1e_checkpoint_client client;
    if (s22_r4w1e_checkpoint_client_init(&client, run_id) != 0) {
        return 10;
    }
    if (s22_r4w1e_checkpoint_progress(
            &client, S22_R4W1E_STAGE_PROC_MOUNTED, 0U) != 0) {
        return 11;
    }
    if (g_probe_fd_open || g_probe_request_size != 32U) {
        return 12;
    }
    return fwrite(g_probe_request, 1U, g_probe_request_size, stdout) == 32U
        ? 0
        : 13;
}
'''
    run_values = ",".join(f"0x{value:02x}" for value in run_id)
    instrumented = client_text.replace(syscall_body, probe_syscall, 1) + probe_main
    source = build_dir / "checkpoint_probe.c"
    header = build_dir / "s22plus_r4w1e_checkpoint.h"
    output = build_dir / "checkpoint_probe"
    source.write_text(instrumented, encoding="ascii")
    header.write_bytes(header_data)
    compiled = run_command(
        [
            tools["gcc"],
            "-std=c11",
            "-O0",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            build_dir,
            f"-DS22_R4W1E_PROBE_RUN_ID_BYTES={{{run_values}}}",
            "-o",
            output,
            source,
        ]
    )
    require_ok(compiled, "compile checkpoint request probe")
    executed = run_command([output], timeout=10)
    if executed.returncode != 0 or executed.stderr:
        raise CheckError(
            "checkpoint request probe failed "
            f"rc={executed.returncode} stderr={executed.stderr!r}"
        )
    expected = carrier.encode_request(
        "E1", carrier.STAGES["PROC_MOUNTED"], run_id=run_id
    )
    if executed.stdout != expected:
        raise CheckError(
            "checkpoint client request bytes differ from the P2.7 carrier oracle"
        )
    decoded = carrier.decode_request(executed.stdout)
    return {
        "size": len(executed.stdout),
        "sha256": sha256_bytes(executed.stdout),
        "profile": decoded.profile,
        "stage": decoded.stage,
        "outcome": decoded.outcome,
        "item_index": decoded.item_index,
        "detail": decoded.detail,
        "run_id": decoded.run_id,
        "p2_7_oracle_exact": True,
        "verified": True,
    }


def compile_one(
    build_dir: Path,
    runtime_data: bytes,
    child_data: bytes,
    client_data: bytes,
    header_data: bytes,
    run_id: bytes,
    tools: dict[str, str],
) -> dict[str, Any]:
    run_header = build_dir / "run_id.h"
    runtime = build_dir / "s22plus_r4w1e_e1_runtime.c"
    child = build_dir / "s22plus_r4w1e_e1_child.c"
    client = build_dir / "s22plus_r4w1e_checkpoint.c"
    header = build_dir / "s22plus_r4w1e_checkpoint.h"
    init_output = build_dir / "init"
    child_output = build_dir / "s22-e1-child"
    write_run_header(run_header, run_id)
    runtime.write_bytes(runtime_data)
    child.write_bytes(child_data)
    client.write_bytes(client_data)
    header.write_bytes(header_data)
    init_compile = run_command(
        [
            tools["aarch64-linux-gnu-gcc"],
            *COMPILE_FLAGS,
            "-I",
            build_dir,
            "-include",
            run_header,
            "-o",
            init_output,
            runtime,
            client,
        ]
    )
    require_ok(init_compile, "compile E1 init")
    child_compile = run_command(
        [tools["aarch64-linux-gnu-gcc"], *COMPILE_FLAGS, "-o", child_output, child]
    )
    require_ok(child_compile, "compile E1 child")

    audits: dict[str, dict[str, Any]] = {}
    for label, output in (("init", init_output), ("child", child_output)):
        file_result = run_command([tools["file"], output])
        require_ok(file_result, f"file audit {label}")
        readelf = run_command(
            [tools["aarch64-linux-gnu-readelf"], "-W", "-h", "-l", output]
        )
        require_ok(readelf, f"readelf audit {label}")
        nm_undefined = run_command([tools["aarch64-linux-gnu-nm"], "-u", output])
        require_ok(nm_undefined, f"undefined-symbol audit {label}")
        nm_symbols = run_command([tools["aarch64-linux-gnu-nm"], output])
        require_ok(nm_symbols, f"symbol audit {label}")
        objdump = run_command([tools["aarch64-linux-gnu-objdump"], "-d", output])
        require_ok(objdump, f"disassembly audit {label}")
        file_text = file_result.stdout.decode("utf-8", errors="replace")
        elf_text = readelf.stdout.decode("utf-8", errors="replace")
        symbol_text = nm_symbols.stdout.decode("utf-8", errors="replace")
        objdump_text = objdump.stdout.decode("utf-8", errors="replace")
        if "ARM aarch64" not in file_text or "statically linked" not in file_text:
            raise CheckError(f"{label} is not a static AArch64 executable")
        if "INTERP" in elf_text or "DYNAMIC" in elf_text:
            raise CheckError(f"{label} contains a dynamic program header")
        stack_lines = [line for line in elf_text.splitlines() if "GNU_STACK" in line]
        if len(stack_lines) != 1 or " RWE " in stack_lines[0]:
            raise CheckError(f"{label} executable-stack contract mismatch")
        if nm_undefined.stdout.strip():
            raise CheckError(f"{label} has undefined symbols")
        if not re.search(r"\bT _start$", symbol_text, flags=re.MULTILINE):
            raise CheckError(f"{label} lacks the exact _start symbol")
        expected_syscalls = (
            set(RUNTIME_SYSCALLS.values()) | set(CLIENT_SYSCALLS.values())
            if label == "init"
            else set(CHILD_SYSCALLS.values())
        )
        syscall_audit = audit_disassembly_syscalls(
            objdump_text, expected_syscalls, label
        )
        audits[label] = {
            "static_aarch64": True,
            "pt_interp": False,
            "undefined_symbols": False,
            "executable_stack": False,
            "syscalls": syscall_audit,
        }

    for output in (init_output, child_output):
        stripped = run_command([tools["aarch64-linux-gnu-strip"], "-s", output])
        require_ok(stripped, f"strip {output.name}")

    init_data = init_output.read_bytes()
    child_data = child_output.read_bytes()
    required_init = (
        b"/proc/s22_checkpoint",
        b"/proc/modules",
        b"/s22-e1-child",
        b"/dev/null",
        b"/lib/modules/",
        CHILD_TOKEN,
        run_id,
        *(spec[0].encode("ascii") for spec in MODULE_SPECS),
        *(spec[1].encode("ascii") for spec in MODULE_SPECS),
    )
    missing_init = [value for value in required_init if value not in init_data]
    if missing_init:
        raise CheckError(f"E1 init binary strings missing: {missing_init}")
    if CHILD_TOKEN not in child_data:
        raise CheckError("E1 child binary lacks the exact token")
    forbidden_binary = (
        b"/dev/block",
        b"/config",
        b"ttyGS",
        b"/sys/class/udc",
        b"/bin/sh",
        b"sec_log_buf.ko",
    )
    hits = [value.decode("ascii") for value in forbidden_binary if value in init_data]
    if hits:
        raise CheckError(f"forbidden E1 init binary strings: {hits}")

    child_run = run_command([tools["qemu-aarch64"], child_output], timeout=10)
    if (
        child_run.returncode != CHILD_EXIT
        or child_run.stdout != CHILD_TOKEN
        or child_run.stderr
    ):
        raise CheckError(
            "E1 child dynamic contract mismatch "
            f"rc={child_run.returncode} stdout={child_run.stdout!r} "
            f"stderr={child_run.stderr!r}"
        )
    return {
        "init": {
            "size": len(init_data),
            "sha256": sha256_bytes(init_data),
            "data": init_data,
            **audits["init"],
        },
        "child": {
            "size": len(child_data),
            "sha256": sha256_bytes(child_data),
            "data": child_data,
            **audits["child"],
            "qemu_exit": child_run.returncode,
            "qemu_stdout": child_run.stdout.decode("ascii"),
            "qemu_stderr_empty": True,
        },
    }


def source_receipt(path: Path, data: bytes) -> dict[str, Any]:
    return {"path": str(path), "size": len(data), "sha256": sha256_bytes(data)}


def run_check(
    runtime: Path,
    child: Path,
    client: Path,
    header: Path,
    inventory: Path,
) -> dict[str, Any]:
    tools = require_tools()
    runtime_data = read_direct(runtime, "E1 runtime")
    child_data = read_direct(child, "E1 child")
    client_data = read_direct(client, "E1 checkpoint client")
    header_data = read_direct(header, "E1 checkpoint header")
    inventory_data = read_direct(inventory, "FYG8 module inventory", 16_777_216)
    runtime_text = decode_ascii(runtime_data, "E1 runtime")
    child_text = decode_ascii(child_data, "E1 child")
    client_text = decode_ascii(client_data, "E1 checkpoint client")
    header_text = decode_ascii(header_data, "E1 checkpoint header")
    inventory_text = decode_ascii(inventory_data, "FYG8 module inventory")

    source_data = {
        "runtime": runtime_data,
        "child": child_data,
        "client": client_data,
        "header": header_data,
        "inventory": inventory_data,
    }
    for label, data in source_data.items():
        digest = sha256_bytes(data)
        if digest != EXPECTED_SOURCE_SHA256[label]:
            raise CheckError(
                f"{label} source identity mismatch: {digest}"
            )

    root = repo_root()
    with without_compiler_environment():
        carrier_result = carrier.run_check(
            resolve(root, carrier.DEFAULT_SOURCE),
            resolve(root, carrier.DEFAULT_PATCH),
        )
    if carrier_result["verdict"] != carrier.VERDICT:
        raise CheckError("P2.7 checkpoint carrier prerequisite did not pass")
    source_contract = {
        "header": check_header(header_text),
        "client": check_client(client_text),
        "runtime": check_runtime(runtime_text),
        "child": check_child(child_text),
        "inventory": check_inventory(inventory_text),
    }
    run_id = carrier.MODEL_RUN_IDS["E1"]
    with tempfile.TemporaryDirectory(prefix="s22-r4w1e-e1-probe-") as probe_dir:
        source_contract["client"]["request_probe"] = probe_client_request(
            Path(probe_dir), client_text, header_data, run_id, tools
        )
    with tempfile.TemporaryDirectory(prefix="s22-r4w1e-e1-a-") as first_dir:
        first = compile_one(
            Path(first_dir),
            runtime_data,
            child_data,
            client_data,
            header_data,
            run_id,
            tools,
        )
    with tempfile.TemporaryDirectory(prefix="s22-r4w1e-e1-b-") as second_dir:
        second = compile_one(
            Path(second_dir),
            runtime_data,
            child_data,
            client_data,
            header_data,
            run_id,
            tools,
        )
    for label in ("init", "child"):
        if first[label]["data"] != second[label]["data"]:
            raise CheckError(f"E1 {label} two-build reproducibility mismatch")
        first[label].pop("data")
        second[label].pop("data")

    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": VERDICT,
        "carrier_prerequisite": {
            "schema": carrier_result["schema"],
            "verdict": carrier_result["verdict"],
            "carrier_sha256": carrier_result["carrier"]["sha256"],
        },
        "sources": {
            "runtime": source_receipt(runtime, runtime_data),
            "child": source_receipt(child, child_data),
            "client": source_receipt(client, client_data),
            "header": source_receipt(header, header_data),
            "inventory": source_receipt(inventory, inventory_data),
        },
        "source_contract": source_contract,
        "build": {
            "run_id": run_id.hex(),
            "run_id_kind": "P2.7 host model only; never live evidence",
            "compile_flags": list(COMPILE_FLAGS),
            "tools": tools,
            "reproduction_a": first,
            "reproduction_b": second,
            "byte_identical": True,
        },
        "safety": {
            "host_only": True,
            "kernel_build": False,
            "boot_image_created": False,
            "vendor_ramdisk_created": False,
            "candidate_packaged": False,
            "device_contact": False,
            "flash": False,
            "live_authorized": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--child", type=Path, default=DEFAULT_CHILD)
    parser.add_argument("--client", type=Path, default=DEFAULT_CLIENT)
    parser.add_argument("--header", type=Path, default=DEFAULT_HEADER)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    result = run_check(
        resolve(root, args.runtime),
        resolve(root, args.child),
        resolve(root, args.client),
        resolve(root, args.header),
        resolve(root, args.inventory),
    )
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        output = resolve(root, args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="ascii")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckError as exc:
        print(json.dumps({"verdict": "BLOCKED_R4W1E_E1_HOST_CONTRACT", "error": str(exc)}))
        raise SystemExit(2) from exc
