#!/usr/bin/env python3
"""Inactive H0 classic-seccomp candidate for the exact S20+ ADB child.

This module compiles and parses deterministic classic-BPF bytes for the exact
Ubuntu x86-64 host ABI.  It is not a connected executor and never runs ADB.
The public CLI only renders a static plan.  Internal helpers can install the
candidate in an isolated fork child and execute only a pinned harmless host
helper so hostile tests can observe the kernel's SIGSYS and execveat behavior.

Classic seccomp is deliberately not described as stateful.  It compares only
the numeric execveat pathname, argv, and envp pointer values; it cannot inspect
any bytes behind those pointers, remember that one execveat has already
succeeded, or prove that a CLOEXEC descriptor number and matching virtual
addresses can never be reused after the image transition.  The exact
pathname/argv/environment byte closure therefore belongs to a separately
reviewed executor and is not enforced here.  The filter qualifies no
production launch-prevention claim.  Those limitations, ADB compatibility,
production installation, executor integration, activation, and live authority
all remain false.
"""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import signal
import stat
import struct
import sys
import time
from types import MappingProxyType
from typing import Any, Final, Mapping, Protocol, Sequence


STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_SECCOMP_V1_PASS_GO_NOT_ACTIVE"
SCHEMA = "s20plus_g986n_autonomous_public_health_adb_seccomp_v1_h0"
EXPECTED_SELF_NORMALIZED_SHA256 = "cf041861841f79d9fe158f4c650b27d5b596aff9cea26acb68e66e5a3eabe3e6"

# These are operational/integration gates.  This artifact is permanently
# inactive and must not be activated by editing the booleans in place.
ADB_SECCOMP_V1_REVIEWED = False
EXACT_HOST_ABI_BOUND = False
RUNTIME_EXACT_BOUND = False
PROXY_EXACT_BOUND = False
ADB_EXACT_BOUND = False
BPF_BYTES_REVIEWED = False
ISOLATED_HELPER_PROBE_REVIEWED = False
PRODUCTION_FILTER_INSTALLER_IMPLEMENTED = False
ADB_CHILD_COMPATIBILITY_PROVED = False
EXECUTOR_IMPLEMENTED = False
SAME_PROCESS_HANDOFF_IMPLEMENTED = False
TARGET_COORDINATION_ACTIVE = False
CROSS_CODE_COORDINATION_ACTIVE = False
RECOVERY_INTEGRATION_ACTIVE = False
CONTRACT_ACTIVE = False
MECHANICAL_ACTIVATION = False
LIVE_AUTHORITY = False

NORMALIZED_GATE_NAMES = (
    "ADB_SECCOMP_V1_REVIEWED",
    "EXACT_HOST_ABI_BOUND",
    "RUNTIME_EXACT_BOUND",
    "PROXY_EXACT_BOUND",
    "ADB_EXACT_BOUND",
    "BPF_BYTES_REVIEWED",
    "ISOLATED_HELPER_PROBE_REVIEWED",
    "PRODUCTION_FILTER_INSTALLER_IMPLEMENTED",
    "ADB_CHILD_COMPATIBILITY_PROVED",
    "EXECUTOR_IMPLEMENTED",
    "SAME_PROCESS_HANDOFF_IMPLEMENTED",
    "TARGET_COORDINATION_ACTIVE",
    "CROSS_CODE_COORDINATION_ACTIVE",
    "RECOVERY_INTEGRATION_ACTIVE",
    "CONTRACT_ACTIVE",
    "MECHANICAL_ACTIVATION",
    "LIVE_AUTHORITY",
)

TARGET = MappingProxyType(
    {
        "model": "SM-G986N",
        "device": "y2q",
        "product": "y2qksx",
        "build": "G986NKSS8IYC2",
    }
)

RUNTIME_IDENTITY = MappingProxyType(
    {
        "path": (
            "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/"
            "revalidation/s20plus_g986n_autonomous_public_health_runtime_v1_h0.py"
        ),
        "size": 85_645,
        "sha256": (
            "f6644edc1f8eee80e6f9fc5e7623c96b8e58de23312e71607e51a4658d67652f"
        ),
        "normalized_sha256": (
            "12b993c199a104c2c0f1bdb9706c179005292971428ef26317442e600eb89ac2"
        ),
    }
)
PROXY_IDENTITY = MappingProxyType(
    {
        "path": (
            "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/"
            "revalidation/s20plus_g986n_autonomous_public_health_adb_proxy_v1_h0.py"
        ),
        "size": 46_477,
        "sha256": (
            "18993008de3c236211c11de2756dc9b05424d9704cfdcb9c02f3cf70e9e29d92"
        ),
        "normalized_sha256": (
            "8878c5e39f2d34ea90707bf81697aed119db1fdf3141807b56c81480fbe1c8c9"
        ),
    }
)
ADB_IDENTITY = MappingProxyType(
    {
        "path": "/usr/lib/android-sdk/platform-tools/adb",
        "canonical_realpath": "/usr/lib/android-sdk/platform-tools/adb",
        "size": 716_968,
        "sha256": (
            "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
        ),
        "elf": "ELF64-LSB-x86-64-PIE",
    }
)
HOST_IDENTITY = MappingProxyType(
    {
        "system": "Linux",
        "machine": "x86_64",
        "kernel_release": "7.0.0-30-generic",
        "byteorder": "little",
        "pointer_bits": 64,
        "libc_name": "glibc",
        "libc_version": "2.43",
        "os_release_path": "/usr/lib/os-release",
        "os_release_size": 410,
        "os_release_sha256": (
            "cf72627ff81aef345d0a9f3807eb80f1035e0f80fe2932d12d94efc02fd68104"
        ),
        "distribution_id": "ubuntu",
        "distribution_version_id": "26.04",
    }
)
HELPER_IDENTITY = MappingProxyType(
    {
        "path": "/usr/bin/gnutrue",
        "canonical_realpath": "/usr/bin/gnutrue",
        "size": 35_288,
        "sha256": (
            "7d659da07aad1d5d1ed79e9f2822d24d2dea47ceec4c7e2e71718a177dc20b4b"
        ),
        "purpose": "isolated-H0-execveat-probe-only",
    }
)

# Linux x86-64 syscall and seccomp ABI values from the UAPI.  This candidate
# intentionally has no multi-architecture fallback.
AUDIT_ARCH_X86_64 = 0xC000003E
X32_SYSCALL_BIT = 0x40000000
SYS_BIND = 49
SYS_LISTEN = 50
SYS_CLONE = 56
SYS_FORK = 57
SYS_VFORK = 58
SYS_EXECVE = 59
SYS_GETPID = 39
SYS_EXECVEAT = 322
SYS_CLONE3 = 435
AT_EMPTY_PATH = 0x1000

FORBIDDEN_SYSCALLS = MappingProxyType(
    {
        "bind": SYS_BIND,
        "listen": SYS_LISTEN,
        "clone": SYS_CLONE,
        "fork": SYS_FORK,
        "vfork": SYS_VFORK,
        "execve": SYS_EXECVE,
        "clone3": SYS_CLONE3,
    }
)
X32_REPRESENTATIVE_SYSCALLS = MappingProxyType(
    {
        "bind": X32_SYSCALL_BIT + 49,
        "listen": X32_SYSCALL_BIT + 50,
        "clone": X32_SYSCALL_BIT + 56,
        "fork": X32_SYSCALL_BIT + 57,
        "vfork": X32_SYSCALL_BIT + 58,
        "clone3": X32_SYSCALL_BIT + 435,
        "execve": X32_SYSCALL_BIT + 520,
        "execveat": X32_SYSCALL_BIT + 545,
    }
)

PR_SET_NO_NEW_PRIVS = 38
PR_SET_SECCOMP = 22
SECCOMP_MODE_FILTER = 2
SECCOMP_RET_KILL_PROCESS = 0x80000000
SECCOMP_RET_TRAP = 0x00030000
SECCOMP_RET_ALLOW = 0x7FFF0000

BPF_LD_W_ABS = 0x20
BPF_JMP_JEQ_K = 0x15
BPF_JMP_JSET_K = 0x45
BPF_RET_K = 0x06
SOCK_FILTER_STRUCT = struct.Struct("<HBBI")
SECCOMP_DATA_STRUCT = struct.Struct("<iIQQQQQQQ")
SECCOMP_DATA_NR_OFFSET = 0
SECCOMP_DATA_ARCH_OFFSET = 4
SECCOMP_DATA_ARGS_OFFSET = 16
SECCOMP_DATA_ARG_STRIDE = 8
MAX_CLASSIC_BPF_INSTRUCTIONS = 4_096
EXPECTED_FILTER_INSTRUCTION_COUNT = 53
EXPECTED_FILTER_BYTE_COUNT = EXPECTED_FILTER_INSTRUCTION_COUNT * SOCK_FILTER_STRUCT.size
EXPECTED_SAMPLE_FILTER_SHA256 = (
    "6f2e13a14ff7e17668fa6501535dc097960e5b1d02a83b7443d3ea86e103aaa5"
)
EXPECTED_EXEC_FD = 3
MAX_USER_POINTER = 0x00007FFFFFFFFFFF

# Stable sample values make the rendered candidate bytes and digest
# deterministic.  A real child would compile a separately validated program
# for its already-owned pointer values immediately before installation.
SAMPLE_EMPTY_PATH_POINTER = 0x00007F0011112222
SAMPLE_ARGV_POINTER = 0x00007F0033334444
SAMPLE_ENVP_POINTER = 0x00007F0055556666
SELF_MAX_BYTES = 128 * 1024
ISOLATED_CHILD_TIMEOUT_SEC = 3.0
MARKER_NO_NEW_PRIVS = b"N"
MARKER_FILTER_INSTALLED = b"F"
MODULE_IMPORT_PID = os.getpid()


class AdbSeccompV1Error(RuntimeError):
    """A candidate drift, ambiguity, or attempted activation stops."""


@dataclass(frozen=True)
class SockFilterInstruction:
    code: int
    jump_true: int
    jump_false: int
    value: int


@dataclass(frozen=True)
class FilterBinding:
    exec_fd: int
    empty_path_pointer: int
    argv_pointer: int
    envp_pointer: int
    flags: int = AT_EMPTY_PATH


@dataclass(frozen=True)
class ProgramValidation:
    instruction_count: int
    byte_count: int
    sha256: str
    architecture_action: int
    default_action: int
    forbidden_action: int
    exact_execveat_action: int


@dataclass(frozen=True)
class InstallTrace:
    events: tuple[str, ...]
    terminal: str
    exec_attempted: bool
    retry_permitted: bool


@dataclass(frozen=True)
class IsolatedProbeResult:
    name: str
    marker_bytes: bytes
    exited: bool
    exit_code: int | None
    signaled: bool
    signal_number: int | None
    timed_out: bool


class InstallOperations(Protocol):
    def set_no_new_privs(self) -> None: ...

    def install_filter(self, program: bytes) -> None: ...

    def execveat(self, binding: FilterBinding) -> None: ...


class _CSockFilter(ctypes.Structure):
    _fields_ = (
        ("code", ctypes.c_ushort),
        ("jt", ctypes.c_ubyte),
        ("jf", ctypes.c_ubyte),
        ("k", ctypes.c_uint32),
    )


class _CSockFprog(ctypes.Structure):
    _fields_ = (
        ("length", ctypes.c_ushort),
        ("filter", ctypes.POINTER(_CSockFilter)),
    )


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise AdbSeccompV1Error("hash input must be exact bytes")
    return hashlib.sha256(payload).hexdigest()


def _require_uint(value: object, bits: int, label: str) -> int:
    if type(value) is not int or value < 0 or value >= (1 << bits):
        raise AdbSeccompV1Error(f"{label} is not uint{bits}")
    return value


def validate_binding(binding: FilterBinding) -> None:
    if type(binding) is not FilterBinding:
        raise AdbSeccompV1Error("filter binding type differs")
    if binding.exec_fd != EXPECTED_EXEC_FD:
        raise AdbSeccompV1Error("initial execveat descriptor is not exact fd 3")
    pointers = (
        binding.empty_path_pointer,
        binding.argv_pointer,
        binding.envp_pointer,
    )
    for label, pointer in zip(("pathname", "argv", "envp"), pointers):
        _require_uint(pointer, 64, f"{label} pointer")
        if pointer == 0 or pointer > MAX_USER_POINTER:
            raise AdbSeccompV1Error(f"{label} pointer is outside x86-64 user range")
    if len(set(pointers)) != len(pointers):
        raise AdbSeccompV1Error("execveat pointer roles overlap")
    if binding.flags != AT_EMPTY_PATH:
        raise AdbSeccompV1Error("initial execveat flags differ from AT_EMPTY_PATH")


def sample_binding() -> FilterBinding:
    return FilterBinding(
        exec_fd=EXPECTED_EXEC_FD,
        empty_path_pointer=SAMPLE_EMPTY_PATH_POINTER,
        argv_pointer=SAMPLE_ARGV_POINTER,
        envp_pointer=SAMPLE_ENVP_POINTER,
    )


def _load_word(offset: int) -> SockFilterInstruction:
    return SockFilterInstruction(BPF_LD_W_ABS, 0, 0, _require_uint(offset, 32, "offset"))


def _jump_equal(value: int, jump_true: int, jump_false: int) -> SockFilterInstruction:
    return SockFilterInstruction(
        BPF_JMP_JEQ_K,
        _require_uint(jump_true, 8, "true jump"),
        _require_uint(jump_false, 8, "false jump"),
        _require_uint(value, 32, "comparison"),
    )


def _jump_bits_set(value: int, jump_true: int, jump_false: int) -> SockFilterInstruction:
    return SockFilterInstruction(
        BPF_JMP_JSET_K,
        _require_uint(jump_true, 8, "true jump"),
        _require_uint(jump_false, 8, "false jump"),
        _require_uint(value, 32, "bit comparison"),
    )


def _return_action(action: int) -> SockFilterInstruction:
    return SockFilterInstruction(BPF_RET_K, 0, 0, _require_uint(action, 32, "action"))


def _argument_halves(index: int, value: int) -> tuple[tuple[int, int], ...]:
    _require_uint(index, 3, "argument index")
    _require_uint(value, 64, "argument value")
    base = SECCOMP_DATA_ARGS_OFFSET + index * SECCOMP_DATA_ARG_STRIDE
    return ((base, value & 0xFFFFFFFF), (base + 4, value >> 32))


def build_filter_instructions(binding: FilterBinding) -> tuple[SockFilterInstruction, ...]:
    """Build the exact architecture-closed classic-BPF instruction tuple."""

    validate_binding(binding)
    instructions = [
        _load_word(SECCOMP_DATA_ARCH_OFFSET),
        _jump_equal(AUDIT_ARCH_X86_64, 1, 0),
        _return_action(SECCOMP_RET_KILL_PROCESS),
        _load_word(SECCOMP_DATA_NR_OFFSET),
        # x32 shares AUDIT_ARCH_X86_64 but marks its distinct syscall ABI in
        # nr.  Reject the complete x32 namespace before any default-ALLOW path.
        _jump_bits_set(X32_SYSCALL_BIT, 0, 1),
        _return_action(SECCOMP_RET_TRAP),
    ]
    for syscall_number in FORBIDDEN_SYSCALLS.values():
        instructions.extend(
            (
                _jump_equal(syscall_number, 0, 1),
                _return_action(SECCOMP_RET_TRAP),
            )
        )
    # Every syscall other than execveat and the unconditional deny set is
    # allowed by this narrow launch-prevention candidate.  It is not a general
    # syscall allowlist.
    instructions.extend(
        (
            _jump_equal(SYS_EXECVEAT, 1, 0),
            _return_action(SECCOMP_RET_ALLOW),
        )
    )
    raw_arguments = (
        binding.exec_fd,
        binding.empty_path_pointer,
        binding.argv_pointer,
        binding.envp_pointer,
        binding.flags,
    )
    for index, value in enumerate(raw_arguments):
        for offset, expected_word in _argument_halves(index, value):
            instructions.extend(
                (
                    _load_word(offset),
                    _jump_equal(expected_word, 1, 0),
                    _return_action(SECCOMP_RET_TRAP),
                )
            )
    instructions.append(_return_action(SECCOMP_RET_ALLOW))
    result = tuple(instructions)
    if len(result) != EXPECTED_FILTER_INSTRUCTION_COUNT:
        raise AdbSeccompV1Error("filter instruction closure differs")
    return result


def pack_filter_program(
    instructions: Sequence[SockFilterInstruction],
) -> bytes:
    if type(instructions) not in (tuple, list) or not instructions:
        raise AdbSeccompV1Error("filter instruction sequence is absent")
    if len(instructions) > MAX_CLASSIC_BPF_INSTRUCTIONS:
        raise AdbSeccompV1Error("classic-BPF instruction ceiling exceeded")
    payload = bytearray()
    for instruction in instructions:
        if type(instruction) is not SockFilterInstruction:
            raise AdbSeccompV1Error("filter instruction type differs")
        payload.extend(
            SOCK_FILTER_STRUCT.pack(
                _require_uint(instruction.code, 16, "instruction code"),
                _require_uint(instruction.jump_true, 8, "true jump"),
                _require_uint(instruction.jump_false, 8, "false jump"),
                _require_uint(instruction.value, 32, "instruction value"),
            )
        )
    return bytes(payload)


def build_filter_program(binding: FilterBinding) -> bytes:
    return pack_filter_program(build_filter_instructions(binding))


def parse_filter_program(payload: bytes) -> tuple[SockFilterInstruction, ...]:
    if type(payload) is not bytes or not payload:
        raise AdbSeccompV1Error("filter bytes are absent")
    if len(payload) % SOCK_FILTER_STRUCT.size:
        raise AdbSeccompV1Error("filter bytes have a partial instruction")
    count = len(payload) // SOCK_FILTER_STRUCT.size
    if count > MAX_CLASSIC_BPF_INSTRUCTIONS:
        raise AdbSeccompV1Error("classic-BPF instruction ceiling exceeded")
    return tuple(
        SockFilterInstruction(*SOCK_FILTER_STRUCT.unpack_from(payload, offset))
        for offset in range(0, len(payload), SOCK_FILTER_STRUCT.size)
    )


def _seccomp_data(arch: int, syscall_number: int, arguments: Sequence[int]) -> bytes:
    _require_uint(arch, 32, "audit architecture")
    if type(syscall_number) is not int or not -(1 << 31) <= syscall_number < (1 << 31):
        raise AdbSeccompV1Error("syscall number is not int32")
    if type(arguments) not in (tuple, list) or len(arguments) != 6:
        raise AdbSeccompV1Error("seccomp argument vector differs")
    checked = tuple(_require_uint(item, 64, "seccomp argument") for item in arguments)
    return SECCOMP_DATA_STRUCT.pack(syscall_number, arch, 0, *checked)


def interpret_filter(
    instructions: Sequence[SockFilterInstruction],
    *,
    arch: int,
    syscall_number: int,
    arguments: Sequence[int] = (0, 0, 0, 0, 0, 0),
) -> int:
    """Interpret only the three instruction forms admitted by this candidate."""

    if type(instructions) not in (tuple, list) or not instructions:
        raise AdbSeccompV1Error("filter instruction sequence is absent")
    data = _seccomp_data(arch, syscall_number, arguments)
    accumulator = 0
    program_counter = 0
    steps = 0
    while program_counter < len(instructions):
        steps += 1
        if steps > len(instructions) + 1:
            raise AdbSeccompV1Error("filter interpreter failed to terminate")
        instruction = instructions[program_counter]
        if type(instruction) is not SockFilterInstruction:
            raise AdbSeccompV1Error("filter instruction type differs")
        if instruction.code == BPF_LD_W_ABS:
            if instruction.jump_true or instruction.jump_false:
                raise AdbSeccompV1Error("load instruction contains jumps")
            if instruction.value > len(data) - 4 or instruction.value % 4:
                raise AdbSeccompV1Error("load offset escapes seccomp_data")
            accumulator = struct.unpack_from("<I", data, instruction.value)[0]
            program_counter += 1
            continue
        if instruction.code in (BPF_JMP_JEQ_K, BPF_JMP_JSET_K):
            condition = (
                accumulator == instruction.value
                if instruction.code == BPF_JMP_JEQ_K
                else bool(accumulator & instruction.value)
            )
            destination = program_counter + 1 + (
                instruction.jump_true
                if condition else instruction.jump_false
            )
            if destination >= len(instructions):
                raise AdbSeccompV1Error("filter jump escapes program")
            program_counter = destination
            continue
        if instruction.code == BPF_RET_K:
            if instruction.jump_true or instruction.jump_false:
                raise AdbSeccompV1Error("return instruction contains jumps")
            return instruction.value
        raise AdbSeccompV1Error("filter opcode is outside the exact subset")
    raise AdbSeccompV1Error("filter program falls through")


def _exact_execveat_arguments(binding: FilterBinding) -> tuple[int, ...]:
    return (
        binding.exec_fd,
        binding.empty_path_pointer,
        binding.argv_pointer,
        binding.envp_pointer,
        binding.flags,
        0,
    )


def validate_filter_program(payload: bytes, binding: FilterBinding) -> ProgramValidation:
    """Strictly parse, byte-pin, and exercise the complete candidate policy."""

    validate_binding(binding)
    if len(payload) != EXPECTED_FILTER_BYTE_COUNT:
        raise AdbSeccompV1Error("filter byte count differs")
    instructions = parse_filter_program(payload)
    expected = build_filter_instructions(binding)
    if instructions != expected or payload != pack_filter_program(expected):
        raise AdbSeccompV1Error("filter bytes differ from the exact candidate")
    mismatch_arch_action = interpret_filter(
        instructions,
        arch=0x40000003,
        syscall_number=SYS_GETPID,
    )
    if mismatch_arch_action != SECCOMP_RET_KILL_PROCESS:
        raise AdbSeccompV1Error("architecture mismatch is not kill-process")
    default_action = interpret_filter(
        instructions,
        arch=AUDIT_ARCH_X86_64,
        syscall_number=SYS_GETPID,
    )
    if default_action != SECCOMP_RET_ALLOW:
        raise AdbSeccompV1Error("non-denied syscall action differs")
    for name, syscall_number in FORBIDDEN_SYSCALLS.items():
        action = interpret_filter(
            instructions,
            arch=AUDIT_ARCH_X86_64,
            syscall_number=syscall_number,
        )
        if action != SECCOMP_RET_TRAP:
            raise AdbSeccompV1Error(f"{name} is not an unconditional trap")
    for name, syscall_number in X32_REPRESENTATIVE_SYSCALLS.items():
        action = interpret_filter(
            instructions,
            arch=AUDIT_ARCH_X86_64,
            syscall_number=syscall_number,
        )
        if action != SECCOMP_RET_TRAP:
            raise AdbSeccompV1Error(f"x32 {name} bypasses the ABI trap")
    exact_arguments = _exact_execveat_arguments(binding)
    exact_action = interpret_filter(
        instructions,
        arch=AUDIT_ARCH_X86_64,
        syscall_number=SYS_EXECVEAT,
        arguments=exact_arguments,
    )
    if exact_action != SECCOMP_RET_ALLOW:
        raise AdbSeccompV1Error("exact initial execveat is not allowed")
    for index in range(5):
        changed = list(exact_arguments)
        changed[index] ^= 1
        action = interpret_filter(
            instructions,
            arch=AUDIT_ARCH_X86_64,
            syscall_number=SYS_EXECVEAT,
            arguments=changed,
        )
        if action != SECCOMP_RET_TRAP:
            raise AdbSeccompV1Error("execveat argument mismatch is not trapped")
    return ProgramValidation(
        instruction_count=len(instructions),
        byte_count=len(payload),
        sha256=sha256_bytes(payload),
        architecture_action=mismatch_arch_action,
        default_action=default_action,
        forbidden_action=SECCOMP_RET_TRAP,
        exact_execveat_action=exact_action,
    )


def model_install_then_execveat(
    operations: InstallOperations,
    binding: FilterBinding,
) -> InstallTrace:
    """Injected H0 ordering model; it never retries a failed transition."""

    if operations is None:
        raise AdbSeccompV1Error("install operations are absent")
    program = build_filter_program(binding)
    validate_filter_program(program, binding)
    events: list[str] = []
    try:
        operations.set_no_new_privs()
        events.append("no_new_privs-set")
    except BaseException:
        return InstallTrace(tuple(events), "no-new-privs-failed", False, False)
    try:
        operations.install_filter(program)
        events.append("filter-installed")
    except BaseException:
        return InstallTrace(tuple(events), "filter-install-failed", False, False)
    try:
        events.append("execveat-attempted")
        operations.execveat(binding)
    except BaseException:
        return InstallTrace(tuple(events), "execveat-failed", True, False)
    return InstallTrace(tuple(events), "execveat-returned-unexpectedly", True, False)


def _install_filter_current_process(
    program: bytes,
    binding: FilterBinding,
    marker_fd: int | None = None,
) -> None:
    """H0-test-only kernel installer.  It must be called in a disposable child."""

    if os.getpid() == MODULE_IMPORT_PID:
        raise AdbSeccompV1Error("kernel filter probe requires a fork child")
    validation = validate_filter_program(program, binding)
    if validation.byte_count != EXPECTED_FILTER_BYTE_COUNT:
        raise AdbSeccompV1Error("kernel filter byte count differs")
    instructions = parse_filter_program(program)
    array_type = _CSockFilter * len(instructions)
    c_instructions = array_type(
        *(
            _CSockFilter(item.code, item.jump_true, item.jump_false, item.value)
            for item in instructions
        )
    )
    filter_program = _CSockFprog(
        len(instructions),
        ctypes.cast(c_instructions, ctypes.POINTER(_CSockFilter)),
    )
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.restype = ctypes.c_int
    ctypes.set_errno(0)
    if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), "PR_SET_NO_NEW_PRIVS")
    if marker_fd is not None:
        os.write(marker_fd, MARKER_NO_NEW_PRIVS)
    ctypes.set_errno(0)
    if libc.prctl(
        PR_SET_SECCOMP,
        SECCOMP_MODE_FILTER,
        ctypes.byref(filter_program),
    ) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), "PR_SET_SECCOMP")
    if marker_fd is not None:
        os.write(marker_fd, MARKER_FILTER_INSTALLED)


def _prepare_execveat_arguments(
    *, nonempty_path: bool = False
) -> tuple[Any, Any, Any, Any, Any, FilterBinding]:
    pathname = ctypes.create_string_buffer(b"x" if nonempty_path else b"", 2 if nonempty_path else 1)
    argv0 = ctypes.create_string_buffer(b"gnutrue")
    env0 = ctypes.create_string_buffer(b"LANG=C")
    argv = (ctypes.c_char_p * 2)(ctypes.cast(argv0, ctypes.c_char_p), None)
    envp = (ctypes.c_char_p * 2)(ctypes.cast(env0, ctypes.c_char_p), None)
    binding = FilterBinding(
        exec_fd=EXPECTED_EXEC_FD,
        empty_path_pointer=ctypes.addressof(pathname),
        argv_pointer=ctypes.addressof(argv),
        envp_pointer=ctypes.addressof(envp),
    )
    validate_binding(binding)
    expected_path = b"x\x00" if nonempty_path else b"\x00"
    if bytes(pathname) != expected_path:
        raise AdbSeccompV1Error("helper pathname buffer differs")
    return pathname, argv0, env0, argv, envp, binding


def _raw_execveat(binding: FilterBinding, *, path_pointer: int | None = None) -> int:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = libc.syscall(
        ctypes.c_long(SYS_EXECVEAT),
        ctypes.c_int(binding.exec_fd),
        ctypes.c_void_p(
            binding.empty_path_pointer if path_pointer is None else path_pointer
        ),
        ctypes.c_void_p(binding.argv_pointer),
        ctypes.c_void_p(binding.envp_pointer),
        ctypes.c_int(binding.flags),
    )
    if result == -1:
        return ctypes.get_errno()
    return 0


def _wait_isolated_child(
    pid: int,
    name: str,
    marker_read_fd: int | None = None,
) -> IsolatedProbeResult:
    if type(pid) is not int or pid <= 0:
        raise AdbSeccompV1Error("isolated child pid differs")
    deadline = time.monotonic() + ISOLATED_CHILD_TIMEOUT_SEC
    status_value: int | None = None
    timed_out = False
    while status_value is None:
        waited, candidate = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            status_value = candidate
            break
        if waited != 0:
            raise AdbSeccompV1Error("isolated child wait identity differs")
        if time.monotonic() >= deadline:
            timed_out = True
            os.kill(pid, signal.SIGKILL)
            waited, status_value = os.waitpid(pid, 0)
            if waited != pid:
                raise AdbSeccompV1Error("isolated child timeout reap differs")
            break
        time.sleep(0.005)
    markers = b""
    if marker_read_fd is not None:
        try:
            while True:
                chunk = os.read(marker_read_fd, 32)
                if not chunk:
                    break
                markers += chunk
                if len(markers) > 32:
                    raise AdbSeccompV1Error("isolated marker stream is oversized")
        finally:
            os.close(marker_read_fd)
    assert status_value is not None
    return IsolatedProbeResult(
        name=name,
        marker_bytes=markers,
        exited=os.WIFEXITED(status_value),
        exit_code=os.WEXITSTATUS(status_value) if os.WIFEXITED(status_value) else None,
        signaled=os.WIFSIGNALED(status_value),
        signal_number=(
            os.WTERMSIG(status_value) if os.WIFSIGNALED(status_value) else None
        ),
        timed_out=timed_out,
    )


def _prepare_disposable_child() -> None:
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    signal.signal(signal.SIGSYS, signal.SIG_DFL)


def exact_probe_host_matches() -> bool:
    """Return whether the current host matches the complete reviewed H0 tuple."""

    try:
        os_release = Path(HOST_IDENTITY["os_release_path"]).read_bytes()
    except OSError:
        return False
    return (
        platform.system() == HOST_IDENTITY["system"]
        and platform.machine() == HOST_IDENTITY["machine"]
        and platform.release() == HOST_IDENTITY["kernel_release"]
        and sys.byteorder == HOST_IDENTITY["byteorder"]
        and struct.calcsize("P") * 8 == HOST_IDENTITY["pointer_bits"]
        and platform.libc_ver()
        == (HOST_IDENTITY["libc_name"], HOST_IDENTITY["libc_version"])
        and len(os_release) == HOST_IDENTITY["os_release_size"]
        and sha256_bytes(os_release) == HOST_IDENTITY["os_release_sha256"]
    )


def _require_exact_probe_host() -> None:
    if not exact_probe_host_matches():
        raise AdbSeccompV1Error("isolated probe host identity differs")


def _open_pinned_helper() -> int:
    descriptor = os.open(
        HELPER_IDENTITY["path"],
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid != 0
            or before.st_gid != 0
            or stat.S_IMODE(before.st_mode) != 0o755
            or before.st_size != HELPER_IDENTITY["size"]
        ):
            raise AdbSeccompV1Error("isolated helper metadata differs")
        payload = os.pread(descriptor, before.st_size + 1, 0)
        if (
            len(payload) != before.st_size
            or sha256_bytes(payload) != HELPER_IDENTITY["sha256"]
            or _metadata(before) != _metadata(os.fstat(descriptor))
        ):
            raise AdbSeccompV1Error("isolated helper held-file identity differs")
        if os.get_inheritable(descriptor):
            raise AdbSeccompV1Error("isolated helper descriptor lacks CLOEXEC")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def run_isolated_forbidden_syscall_probe(name: str) -> IsolatedProbeResult:
    """Install in a fork child and make one forbidden raw syscall."""

    if type(name) is not str or name not in FORBIDDEN_SYSCALLS:
        raise AdbSeccompV1Error("forbidden syscall probe name differs")
    _require_exact_probe_host()
    binding = sample_binding()
    program = build_filter_program(binding)
    validate_filter_program(program, binding)
    pid = os.fork()
    if pid == 0:
        try:
            _prepare_disposable_child()
            _install_filter_current_process(program, binding)
            libc = ctypes.CDLL(None, use_errno=True)
            libc.syscall.restype = ctypes.c_long
            libc.syscall(ctypes.c_long(FORBIDDEN_SYSCALLS[name]), 0, 0, 0, 0, 0, 0)
        except BaseException:
            os._exit(125)
        os._exit(124)
    return _wait_isolated_child(pid, name)


def run_isolated_x32_syscall_probe(name: str) -> IsolatedProbeResult:
    """Install in a fork child and make one x32-ABI raw syscall."""

    if type(name) is not str or name not in X32_REPRESENTATIVE_SYSCALLS:
        raise AdbSeccompV1Error("x32 syscall probe name differs")
    _require_exact_probe_host()
    binding = sample_binding()
    program = build_filter_program(binding)
    validate_filter_program(program, binding)
    pid = os.fork()
    if pid == 0:
        try:
            _prepare_disposable_child()
            _install_filter_current_process(program, binding)
            libc = ctypes.CDLL(None, use_errno=True)
            libc.syscall.restype = ctypes.c_long
            libc.syscall(
                ctypes.c_long(X32_REPRESENTATIVE_SYSCALLS[name]),
                0,
                0,
                0,
                0,
                0,
                0,
            )
        except BaseException:
            os._exit(125)
        os._exit(124)
    return _wait_isolated_child(pid, f"x32-{name}")


def run_isolated_exact_execveat_probe() -> IsolatedProbeResult:
    """Use the candidate only with held /usr/bin/gnutrue in a fork child."""

    _require_exact_probe_host()
    helper_fd = _open_pinned_helper()
    marker_read_fd, marker_write_fd = os.pipe2(os.O_CLOEXEC)
    try:
        pid = os.fork()
        if pid == 0:
            try:
                os.close(marker_read_fd)
                _prepare_disposable_child()
                if helper_fd != EXPECTED_EXEC_FD:
                    os.dup2(helper_fd, EXPECTED_EXEC_FD, inheritable=False)
                    os.close(helper_fd)
                else:
                    os.set_inheritable(helper_fd, False)
                if os.get_inheritable(EXPECTED_EXEC_FD):
                    os._exit(122)
                pathname, argv0, env0, argv, envp, binding = _prepare_execveat_arguments()
                # Keep every ctypes owner live across the raw syscall.
                if not all((pathname, argv0, env0, argv, envp)):
                    os._exit(123)
                program = build_filter_program(binding)
                validate_filter_program(program, binding)
                _install_filter_current_process(program, binding, marker_write_fd)
                error = _raw_execveat(binding)
                os._exit(120 if error == 0 else 121)
            except BaseException:
                os._exit(125)
        os.close(marker_write_fd)
        marker_write_fd = -1
        return _wait_isolated_child(pid, "exact-execveat", marker_read_fd)
    finally:
        os.close(helper_fd)
        if marker_write_fd >= 0:
            os.close(marker_write_fd)


def run_isolated_execveat_mismatch_probe(field: str) -> IsolatedProbeResult:
    """Prove each raw execveat argument mismatch reaches SIGSYS."""

    allowed = {"fd", "pathname-pointer", "argv-pointer", "envp-pointer", "flags"}
    if type(field) is not str or field not in allowed:
        raise AdbSeccompV1Error("execveat mismatch field differs")
    _require_exact_probe_host()
    pid = os.fork()
    if pid == 0:
        try:
            _prepare_disposable_child()
            pathname, argv0, env0, argv, envp, binding = _prepare_execveat_arguments()
            if not all((pathname, argv0, env0, argv, envp)):
                os._exit(123)
            program = build_filter_program(binding)
            _install_filter_current_process(program, binding)
            values = {
                "fd": binding.exec_fd,
                "pathname-pointer": binding.empty_path_pointer,
                "argv-pointer": binding.argv_pointer,
                "envp-pointer": binding.envp_pointer,
                "flags": binding.flags,
            }
            values[field] ^= 1
            changed = FilterBinding(
                exec_fd=values["fd"],
                empty_path_pointer=values["pathname-pointer"],
                argv_pointer=values["argv-pointer"],
                envp_pointer=values["envp-pointer"],
                flags=values["flags"],
            )
            _raw_execveat(changed)
        except BaseException:
            os._exit(125)
        os._exit(124)
    return _wait_isolated_child(pid, f"execveat-mismatch-{field}")


def run_isolated_nonempty_same_pointer_probe() -> IsolatedProbeResult:
    """Demonstrate that classic BPF cannot inspect pathname pointed-to bytes."""

    _require_exact_probe_host()
    helper_fd = _open_pinned_helper()
    try:
        pid = os.fork()
        if pid == 0:
            try:
                _prepare_disposable_child()
                if helper_fd != EXPECTED_EXEC_FD:
                    os.dup2(helper_fd, EXPECTED_EXEC_FD, inheritable=False)
                    os.close(helper_fd)
                else:
                    os.set_inheritable(helper_fd, False)
                if os.get_inheritable(EXPECTED_EXEC_FD):
                    os._exit(122)
                pathname, argv0, env0, argv, envp, binding = _prepare_execveat_arguments(
                    nonempty_path=True
                )
                if not all((pathname, argv0, env0, argv, envp)):
                    os._exit(123)
                program = build_filter_program(binding)
                _install_filter_current_process(program, binding)
                error = _raw_execveat(binding)
                # The filter allowed the raw pointer.  The kernel then rejects
                # the nonempty relative path against regular-file fd 3.
                # ENOTDIR is proof of this limitation; it is not SIGSYS.
                os._exit(42 if error == errno.ENOTDIR else 43)
            except BaseException:
                os._exit(125)
        return _wait_isolated_child(pid, "nonempty-same-pointer")
    finally:
        os.close(helper_fd)


def _operational_gates() -> dict[str, bool]:
    return {
        "adb_seccomp_v1_reviewed": ADB_SECCOMP_V1_REVIEWED,
        "exact_host_abi_bound": EXACT_HOST_ABI_BOUND,
        "runtime_exact_bound": RUNTIME_EXACT_BOUND,
        "proxy_exact_bound": PROXY_EXACT_BOUND,
        "adb_exact_bound": ADB_EXACT_BOUND,
        "bpf_bytes_reviewed": BPF_BYTES_REVIEWED,
        "isolated_helper_probe_reviewed": ISOLATED_HELPER_PROBE_REVIEWED,
        "production_filter_installer_implemented": PRODUCTION_FILTER_INSTALLER_IMPLEMENTED,
        "adb_child_compatibility_proved": ADB_CHILD_COMPATIBILITY_PROVED,
        "executor_implemented": EXECUTOR_IMPLEMENTED,
        "same_process_handoff_implemented": SAME_PROCESS_HANDOFF_IMPLEMENTED,
        "target_coordination_active": TARGET_COORDINATION_ACTIVE,
        "cross_code_coordination_active": CROSS_CODE_COORDINATION_ACTIVE,
        "recovery_integration_active": RECOVERY_INTEGRATION_ACTIVE,
        "contract_active": CONTRACT_ACTIVE,
        "mechanical_activation": MECHANICAL_ACTIVATION,
        "live_authority": LIVE_AUTHORITY,
    }


def _require_operational_gate() -> None:
    if not all(value is True for value in _operational_gates().values()):
        raise AdbSeccompV1Error("ADB seccomp candidate is inactive")


def attended_open_and_read() -> None:
    _require_operational_gate()
    raise AdbSeccompV1Error("ADB seccomp executor is not implemented")


def normalized_source_sha256(source: bytes) -> str:
    if type(source) is not bytes or not source:
        raise AdbSeccompV1Error("source bytes are absent")
    normalized, status_count = re.subn(
        rb'^STATUS = "[A-Z0-9_]+"$',
        b'STATUS = "<REVIEWED_STATUS>"',
        source,
        flags=re.MULTILINE,
    )
    normalized, anchor_count = re.subn(
        rb'^EXPECTED_SELF_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_SELF_NORMALIZED_SHA256 = "<REVIEWED_SELF_ANCHOR>"',
        normalized,
        flags=re.MULTILINE,
    )
    if status_count != 1 or anchor_count != 1:
        raise AdbSeccompV1Error("source identity normalization is ambiguous")
    for name in NORMALIZED_GATE_NAMES:
        normalized, count = re.subn(
            rf"^{name} = (?:False|True)$".encode("ascii"),
            f"{name} = <REVIEWED_BOOLEAN>".encode("ascii"),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise AdbSeccompV1Error("source gate normalization is ambiguous")
    return sha256_bytes(normalized)


def _metadata(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_self_bytes() -> bytes:
    descriptor = os.open(Path(__file__), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size <= 0
            or before.st_size > SELF_MAX_BYTES
        ):
            raise AdbSeccompV1Error("seccomp source identity differs")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, before.st_size - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != before.st_size or os.read(descriptor, 1):
            raise AdbSeccompV1Error("seccomp source length differs")
        if _metadata(before) != _metadata(os.fstat(descriptor)):
            raise AdbSeccompV1Error("seccomp source changed while read")
        return bytes(payload)
    finally:
        os.close(descriptor)


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def render_plan() -> dict[str, Any]:
    source = _read_self_bytes()
    normalized_sha256 = normalized_source_sha256(source)
    if normalized_sha256 != EXPECTED_SELF_NORMALIZED_SHA256:
        raise AdbSeccompV1Error("seccomp normalized source identity differs")
    gates = _operational_gates()
    if any(gates.values()):
        raise AdbSeccompV1Error("H0 render found an active gate")
    binding = sample_binding()
    program = build_filter_program(binding)
    validation = validate_filter_program(program, binding)
    if validation.sha256 != EXPECTED_SAMPLE_FILTER_SHA256:
        raise AdbSeccompV1Error("sample filter identity differs")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "self": {
            "size": len(source),
            "sha256": sha256_bytes(source),
            "normalized_sha256": normalized_sha256,
            "normalized_sha256_expected": EXPECTED_SELF_NORMALIZED_SHA256,
        },
        "target": dict(TARGET),
        "authority": {
            "tier": "H0",
            "device_contact": False,
            "adb_executed": False,
            "socket_or_network_used": False,
            "su_used": False,
            "odin_used": False,
            "production_filter_installed": False,
            "connected_executor": False,
            "live_authority": False,
        },
        "gates": gates,
        "pinned_identities": {
            "runtime": _plain(RUNTIME_IDENTITY),
            "restricted_proxy": _plain(PROXY_IDENTITY),
            "adb": _plain(ADB_IDENTITY),
            "host": _plain(HOST_IDENTITY),
            "isolated_helper": _plain(HELPER_IDENTITY),
        },
        "classic_bpf": {
            "encoding": "little-endian-struct-sock_filter-HBBI",
            "audit_arch": f"0x{AUDIT_ARCH_X86_64:08x}",
            "x32_syscall_bit": f"0x{X32_SYSCALL_BIT:08x}",
            "x32_abi_action": "SECCOMP_RET_TRAP-SIGSYS-before-default-allow",
            "x32_representative_syscalls": dict(X32_REPRESENTATIVE_SYSCALLS),
            "arch_mismatch_action": "SECCOMP_RET_KILL_PROCESS",
            "forbidden_action": "SECCOMP_RET_TRAP-SIGSYS",
            "default_action": "SECCOMP_RET_ALLOW",
            "instruction_count": validation.instruction_count,
            "byte_count": validation.byte_count,
            "sample_sha256": validation.sha256,
            "sample_program_hex": program.hex(),
            "sample_binding": {
                "exec_fd": binding.exec_fd,
                "pathname_pointer_hex": f"0x{binding.empty_path_pointer:016x}",
                "argv_pointer_hex": f"0x{binding.argv_pointer:016x}",
                "envp_pointer_hex": f"0x{binding.envp_pointer:016x}",
                "flags_hex": f"0x{binding.flags:08x}",
            },
            "unconditionally_trapped": list(FORBIDDEN_SYSCALLS),
            "deterministic_generator": True,
            "strict_parser_and_interpreter": True,
            "general_syscall_allowlist": False,
        },
        "initial_transition": {
            "required_order": [
                "PR_SET_NO_NEW_PRIVS",
                "PR_SET_SECCOMP-filter",
                "execveat-held-fd",
            ],
            "execveat_raw_arguments_compared": [
                "fd-low-high",
                "pathname-pointer-low-high",
                "argv-pointer-low-high",
                "envp-pointer-low-high",
                "flags-low-high",
            ],
            "expected_fd": EXPECTED_EXEC_FD,
            "expected_flags": "AT_EMPTY_PATH",
            "filter_can_dereference_pathname": False,
            "filter_can_dereference_argv": False,
            "filter_can_dereference_envp": False,
            "empty_path_contents_enforced_by_filter": False,
            "argv_contents_enforced_by_filter": False,
            "envp_contents_enforced_by_filter": False,
            "exact_executor_owned_pointer_referents_required": True,
            "exact_executor_owned_pointer_referents_proved": False,
            "filter_is_stateful": False,
            "maximum_execveat_successes_proved": False,
            "held_fd_cloexec_required": True,
            "held_fd_cloexec_transition_proved_for_adb": False,
            "fd_number_reuse_bypass_closed": False,
            "pointer_address_reuse_bypass_closed": False,
        },
        "failure_model": {
            "no_new_privs_failure_exec_attempted": False,
            "filter_install_failure_exec_attempted": False,
            "forbidden_syscall_terminal": "SIGSYS",
            "terminal_means_controller_must_stop_without_retry": True,
            "pinned_adb_sigsys_disposition_and_process_death_proved": False,
            "retry_permitted_after_install_or_exec_uncertainty": False,
            "candidate_replay_permitted": False,
        },
        "isolated_h0_probe": {
            "available_only_by_import": True,
            "public_cli_exposes_probe": False,
            "fork_before_filter": True,
            "executes_pinned_helper_only": HELPER_IDENTITY["path"],
            "executes_adb": False,
            "kernel_filter_installation_is_production_integration": False,
            "probe_results_are_embedded_authority": False,
        },
        "cli": ["--render-plan"],
        "caller_inputs": [],
        "callbacks": [],
        "connected_backends": [],
        "device_commands": [],
        "root_commands": [],
        "odin_commands": [],
        "partition_transfers": [],
        "private_writes": [],
        "unresolved_gates": [
            "classic-BPF-cannot-dereference-execveat-pointer-referents",
            "exact-executor-owned-pathname-argv-env-byte-closure",
            "classic-BPF-has-no-one-shot-state",
            "held-ADB-fd-CLOEXEC-post-exec-proof",
            "fd-number-and-pointer-address-reuse-closure",
            "exact-pinned-ADB-child-compatibility-under-filter",
            "exact-pinned-ADB-SIGSYS-disposition-and-process-death",
            "production-child-filter-installation",
            "closed-no-input-executor-call-graph",
            "same-process-runtime-proxy-campaign-handoff",
            "cross-code-interlock-and-recovery-integration",
            "combined-independent-review",
            "target-contract-and-mechanical-activation",
            "fresh-attended-opening-request",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.render_plan:
        raise AdbSeccompV1Error("only the H0 render mode exists")
    print(json.dumps(render_plan(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
