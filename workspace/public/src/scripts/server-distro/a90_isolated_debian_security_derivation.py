#!/usr/bin/env python3
"""Derive and reconcile the host-side A90 isolated-Debian security evidence.

This tool is deliberately H0-only.  It reads the already materialised private
AArch64 binaries, disassembles them with the cross objdump, and optionally runs
bounded ``qemu-aarch64 -strace`` observations.  It never opens USB, ADB,
Odin, a device transport, or a device-network endpoint.  QEMU user-mode
observations are records of exercised paths only: an observed set is a lower
bound and may be a strict subset of the service's real syscall set.

The output is written below ``workspace/private``.  It contains no authority,
candidate identity, installation permission, or tracked raw trace.  Missing
required scenarios are reported as incomplete evidence rather than filled with
guesses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[5]
PRIVATE_ROOT = (REPO_ROOT / "workspace/private").resolve()
MANIFEST_PATH = (
    REPO_ROOT
    / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/"
    / "isolated-debian-minimal-content-v2/userdata-content-manifest.json"
)
DEFAULT_BINARY_ROOT = PRIVATE_ROOT / "outputs/a90-isolated-debian-content-v2"
DEFAULT_OUTPUT = PRIVATE_ROOT / "outputs/a90-isolated-debian-security-derivation"
DEFAULT_DROPBEAR_SOURCE = PRIVATE_ROOT / "inputs/a90-isolated-debian/dropbear-source"
COMPONENT_SOURCE_ROOT = (
    REPO_ROOT / "workspace/public/src/scripts/server-distro/a90_isolated_debian_content_v2"
)
SYSCALL_HEADER = Path("/usr/aarch64-linux-gnu/include/asm/unistd_64.h")
SYSCALL_GENERIC_HEADER = SYSCALL_HEADER.parent.parent / "asm-generic/unistd.h"
SYSCALL_HEADERS = (SYSCALL_HEADER, SYSCALL_GENERIC_HEADER)

BINARY_RELATIVE_PATHS = {
    "dropbear": Path("dropbear-build/dropbear"),
    "pid1": Path("component-build/pid1"),
    "probe": Path("component-build/probe"),
    "workload": Path("component-build/workload"),
}

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
DISASSEMBLY_LINE_RE = re.compile(r"^\s*([0-9a-f]+):\s+(.*)$")
SYMBOL_LINE_RE = re.compile(r"^\s*([0-9a-f]+)\s+<([^>]+)>:$")
SVC_RE = re.compile(r"\bsvc\s+#0(?:x0)?\b", re.IGNORECASE)
MOV_IMMEDIATE_RE = re.compile(r"^mov\s+[xw]8,\s*#([^\s/]+)", re.IGNORECASE)
REGISTER_IMMEDIATE_RE = re.compile(
    r"^mov\s+[xw]([0-9]+),\s*#([^\s/]+)", re.IGNORECASE
)
MOV_REGISTER_RE = re.compile(
    r"^mov\s+[xw]8,\s*[xw][0-9]+\b", re.IGNORECASE
)
BRANCH_RE = re.compile(
    r"^(?:b(?:\.|\s|$)|bl\b|blr\b|br\b|ret\b|cbz\b|cbnz\b|tbz\b|tbnz\b)",
    re.IGNORECASE,
)
TRACE_LINE_RE = re.compile(r"^\s*\d+\s+([A-Za-z0-9_]+)\(")
PROC_PATH_RE = re.compile(r"\"(/proc/[^\"]*)\"")
SYSCALL_CANCEL_CALL_RE = re.compile(r"\bbl\s+[0-9a-f]+\s+<__syscall_cancel>")
SIGNAL_TRAMPOLINE_SYSCALLS = {
    "rt_sigreturn": "AArch64 signal-return trampoline supplied by the kernel/libc signal-delivery ABI, outside the private ELF text",
}

# These are the nine Dropbear sites left unresolved by the deliberately
# bounded 12-instruction walk.  The map does not make them disappear; it
# records the separate consumer/source decision for the report and residual
# risk section.
DROPBEAR_RESIDUALS = {
    0x40520: {
        "classification": "flow-carried-immediate",
        "decision": "contextually-167",
        "explanation": (
            "The fall-through path retains x8=167 from 0x404f8; the bounded "
            "walk stops at the preceding conditional branch."
        ),
        "residual_risk": "none-for-number-after-context-check; branch proof is outside the bounded walk",
    },
    0x4FAC4: {
        "classification": "register-sourced-generic-wrapper",
        "decision": "runtime-value",
        "explanation": (
            "__internal_syscall_cancel copies caller-supplied x6 into x8 "
            "before svc."
        ),
        "residual_risk": "a cancellation-point caller can select a runtime syscall number",
    },
    0x50DA8: {
        "classification": "register-sourced-generic-wrapper",
        "decision": "runtime-value",
        "explanation": (
            "__syscall_cancel_arch copies the caller-supplied x1 into x8 "
            "before svc."
        ),
        "residual_risk": "the cancellation wrapper is an unqualified runtime syscall-number escape hatch",
    },
    0x54EF0: {
        "classification": "bounded-window-limit",
        "decision": "contextually-278",
        "explanation": (
            "__ptmalloc_init sets x8=278 at 0x54ebc, just beyond the "
            "12-instruction backward window."
        ),
        "residual_risk": "none-for-number-after-function-context-check; the bounded result remains unresolved",
    },
    0x63940: {
        "classification": "bounded-window-limit",
        "decision": "contextually-29",
        "explanation": (
            "tcgetattr sets x8=29 at function entry, outside the bounded "
            "window; this is the ioctl call."
        ),
        "residual_risk": "ioctl request-argument filtering is still unproved",
    },
    0x63B44: {
        "classification": "flow-carried-immediate",
        "decision": "contextually-29",
        "explanation": (
            "tcsetattr carries x8=29 through the error/restore branch from "
            "0x63abc; the bounded walk stops at the branch."
        ),
        "residual_risk": "ioctl request-argument filtering is still unproved",
    },
    0x65164: {
        "classification": "register-sourced-generic-wrapper",
        "decision": "runtime-value",
        "explanation": "The exported syscall() wrapper copies its first argument w0 into w8.",
        "residual_risk": "a reachable syscall() caller can select a runtime syscall number",
    },
    0x9C604: {
        "classification": "register-sourced-setxid-descriptor",
        "decision": "runtime-setxid-family",
        "explanation": (
            "__nptl_setxid_sighandler loads a sign-extended syscall number "
            "from the glibc setxid descriptor."
        ),
        "residual_risk": "the exact CAP_SETUID/CAP_SETGID transition path must be exercised and negatively tested",
    },
    0x9C950: {
        "classification": "register-sourced-setxid-descriptor",
        "decision": "runtime-setxid-family",
        "explanation": (
            "__nptl_setxid loads a sign-extended syscall number from the "
            "glibc setxid descriptor."
        ),
        "residual_risk": "the exact CAP_SETUID/CAP_SETGID transition path must be exercised and negatively tested",
    },
}


class DerivationError(RuntimeError):
    """The host evidence cannot be derived without inventing a value."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path = path.resolve()
    try:
        path.relative_to(PRIVATE_ROOT)
    except ValueError as exc:
        raise DerivationError("derivation output must stay below workspace/private") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.resolve(strict=True).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DerivationError(f"cannot read manifest: {path}") from exc
    if not isinstance(value, dict):
        raise DerivationError("manifest is not an object")
    return value


def _require_private(path: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PRIVATE_ROOT)
    except ValueError as exc:
        raise DerivationError(f"{label} must stay below workspace/private") from exc
    return resolved


def binary_paths(binary_root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for name, relative in BINARY_RELATIVE_PATHS.items():
        path = (binary_root / relative).resolve(strict=True)
        if not path.is_file() or path.is_symlink():
            raise DerivationError(f"{name} is not a regular private binary: {path}")
        result[name] = path
    return result


def verify_binary_pins(manifest: dict[str, Any], binaries: dict[str, Path]) -> None:
    records = {
        item.get("path"): item
        for item in manifest.get("files", [])
        if isinstance(item, dict)
    }
    expected_paths = {
        "dropbear": "/usr/sbin/dropbear",
        "pid1": "/usr/local/libexec/a90-pid1",
        "probe": "/usr/local/libexec/a90-probe",
        "workload": "/usr/local/libexec/a90-workload",
    }
    for name, binary in binaries.items():
        record = records.get(expected_paths[name])
        if not isinstance(record, dict):
            raise DerivationError(f"manifest has no pin for {name}")
        digest = sha256_file(binary)
        if record.get("sha256") != digest or record.get("size") != binary.stat().st_size:
            raise DerivationError(f"private {name} binary does not match the manifest pin")


def _parse_immediate(token: str) -> int:
    token = token.lower().replace("_", "")
    sign = -1 if token.startswith("-") else 1
    token = token.lstrip("-")
    if token.startswith("0x"):
        return sign * int(token, 16)
    return sign * int(token, 10)


def _parse_disassembly(binary: Path) -> tuple[list[dict[str, Any]], str]:
    objdump = shutil.which("aarch64-linux-gnu-objdump")
    if objdump is None:
        raise DerivationError("aarch64-linux-gnu-objdump is unavailable")
    try:
        text = subprocess.check_output(
            [objdump, "-d", "--no-show-raw-insn", str(binary)],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DerivationError(f"objdump failed for {binary}") from exc
    instructions: list[dict[str, Any]] = []
    current_function = "<unknown>"
    for line in text.splitlines():
        symbol = SYMBOL_LINE_RE.match(line)
        if symbol:
            current_function = symbol.group(2)
            continue
        match = DISASSEMBLY_LINE_RE.match(line)
        if match:
            instructions.append(
                {
                    "address": int(match.group(1), 16),
                    "assembly": match.group(2).strip(),
                    "function": current_function,
                }
            )
    return instructions, text


def _backward_resolution(instructions: list[dict[str, Any]]) -> dict[str, Any]:
    svc_indexes = [
        index
        for index, instruction in enumerate(instructions)
        if SVC_RE.search(instruction["assembly"])
    ]
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for index in svc_indexes:
        syscall_number: int | None = None
        stop_reason = "window-exhausted"
        evidence: list[str] = []
        for previous in range(index - 1, max(-1, index - 13), -1):
            assembly = instructions[previous]["assembly"]
            evidence.append(assembly)
            if BRANCH_RE.match(assembly):
                stop_reason = "branch"
                break
            register_source = MOV_REGISTER_RE.match(assembly)
            if register_source:
                stop_reason = "register-sourced"
                break
            immediate = MOV_IMMEDIATE_RE.match(assembly)
            if immediate:
                try:
                    syscall_number = _parse_immediate(immediate.group(1))
                except ValueError:
                    stop_reason = "unparseable-immediate"
                break
        record = {
            "address": instructions[index]["address"],
            "address_hex": f"0x{instructions[index]['address']:x}",
            "function": instructions[index]["function"],
        }
        if syscall_number is None:
            record.update({"reason": stop_reason, "backward_evidence": evidence})
            unresolved.append(record)
        else:
            record["syscall_number"] = syscall_number
            resolved.append(record)
    return {
        "svc_site_count": len(svc_indexes),
        "resolved_site_count": len(resolved),
        "unresolved_site_count": len(unresolved),
        "resolved_sites": resolved,
        "unresolved_sites": unresolved,
        "resolved_syscall_numbers": sorted({item["syscall_number"] for item in resolved}),
    }


def _register_syscall_callers(
    instructions: list[dict[str, Any]], syscall_numbers: dict[str, int]
) -> list[dict[str, Any]]:
    """Find libc wrappers that pass a syscall number through x6 to cancellation.

    The bounded svc walk intentionally stops at the generic cancellation
    wrapper's register move.  Recording the caller-side immediate is the
    repeatable evidence that explains the observed accept/connect/select/wait4
    numbers without treating the generic wrapper as a constant site.
    """

    interesting_numbers = set(syscall_numbers.values())
    records: list[dict[str, Any]] = []
    for index, instruction in enumerate(instructions):
        immediate = REGISTER_IMMEDIATE_RE.match(instruction["assembly"])
        if immediate is None or immediate.group(1) != "6":
            continue
        try:
            number = _parse_immediate(immediate.group(2))
        except ValueError:
            continue
        if number not in interesting_numbers:
            continue
        for following in instructions[index + 1 : index + 13]:
            if following["function"] != instruction["function"]:
                break
            if SYSCALL_CANCEL_CALL_RE.search(following["assembly"]):
                records.append(
                    {
                        "syscall_number": number,
                        "immediate_address": f"0x{instruction['address']:x}",
                        "call_address": f"0x{following['address']:x}",
                        "function": instruction["function"],
                        "cause": "caller loads the number into x6 before __syscall_cancel; the bounded walk later sees only a register-sourced x8 move",
                    }
                )
                break
            if BRANCH_RE.match(following["assembly"]):
                break
    return records


def derive_static(manifest: dict[str, Any], binaries: dict[str, Path]) -> dict[str, Any]:
    verify_binary_pins(manifest, binaries)
    syscall_numbers = parse_syscall_header()
    records: dict[str, Any] = {}
    for name, binary in binaries.items():
        instructions, _ = _parse_disassembly(binary)
        result = _backward_resolution(instructions)
        if name == "dropbear":
            result["register_syscall_callers"] = _register_syscall_callers(
                instructions, syscall_numbers
            )
        result["binary_sha256"] = sha256_file(binary)
        result["binary_size"] = binary.stat().st_size
        records[name] = result
    union = sorted(
        {
            number
            for value in records.values()
            for number in value["resolved_syscall_numbers"]
        }
    )
    dropbear_unresolved = {
        int(item["address"]): item for item in records["dropbear"]["unresolved_sites"]
    }
    if set(dropbear_unresolved) != set(DROPBEAR_RESIDUALS):
        raise DerivationError(
            "Dropbear unresolved svc addresses drifted: "
            f"{sorted(hex(value) for value in dropbear_unresolved)}"
        )
    for address, residual in DROPBEAR_RESIDUALS.items():
        dropbear_unresolved[address]["consumer_decision"] = residual
    return {
        "abi": "AArch64 Linux LP64 syscall ABI (asm/unistd_64.h); compat/arm32 is not supported by this rootfs",
        "method": "aarch64-linux-gnu-objdump -d --no-show-raw-insn; inspect every svc #0; walk at most 12 prior instructions; stop at branches and register-sourced mov x8/w8; separately bind caller immediates that enter __syscall_cancel",
        "binaries": records,
        "resolved_svc_union_numbers": union,
        "resolved_svc_union_count": len(union),
        "union_resolved_syscall_numbers": union,
        "union_resolved_syscall_count": len(union),
        "dropbear_expected_reproduction": {
            "svc_sites": 194,
            "resolved_sites": 185,
            "unresolved_sites": 9,
            "distinct_syscalls": 83,
            "matches": (
                records["dropbear"]["svc_site_count"] == 194
                and records["dropbear"]["resolved_site_count"] == 185
                and records["dropbear"]["unresolved_site_count"] == 9
                and len(records["dropbear"]["resolved_syscall_numbers"]) == 83
            ),
        },
    }


def _syscall_header_paths(path: Path | None) -> tuple[Path, ...]:
    if path is None:
        return tuple(candidate for candidate in SYSCALL_HEADERS if candidate.is_file())
    primary = path
    candidates = [primary]
    generic = primary.parent.parent / "asm-generic/unistd.h"
    if generic not in candidates:
        candidates.append(generic)
    return tuple(candidate for candidate in candidates if candidate.is_file())


def parse_syscall_header(path: Path | None = None) -> dict[str, int]:
    """Return one authoritative AArch64 syscall-name-to-number mapping.

    The architecture header is primary.  The generic header is parsed as
    well so ``__NR3264_*`` definitions and their LP64 aliases (including
    fcntl/fstat/fstatat/lseek/mmap) are resolved from kernel header source
    rather than from a hand-maintained alias table.
    """

    definitions: dict[str, str] = {}
    pattern = re.compile(
        r"^#define\s+(__NR(?:3264)?_[A-Za-z0-9_]+)\s+"
        r"([0-9]+|__NR(?:3264)?_[A-Za-z0-9_]+)\s*$"
    )
    for header in _syscall_header_paths(path):
        try:
            lines = header.read_text(encoding="ascii").splitlines()
        except (OSError, UnicodeError):
            continue
        for line in lines:
            match = pattern.match(line)
            if match:
                definitions.setdefault(match.group(1), match.group(2))

    resolved_macros: dict[str, int] = {}

    def resolve(macro: str, stack: tuple[str, ...] = ()) -> int | None:
        if macro in resolved_macros:
            return resolved_macros[macro]
        if macro in stack:
            return None
        value = definitions.get(macro)
        if value is None:
            return None
        if value.isdigit():
            number = int(value)
        else:
            number = resolve(value, stack + (macro,))
            if number is None:
                return None
        resolved_macros[macro] = number
        return number

    result: dict[str, int] = {}
    for macro in sorted(definitions):
        number = resolve(macro)
        if number is None or macro == "__NR_syscalls":
            continue
        if macro.startswith("__NR3264_"):
            name = macro[len("__NR3264_") :]
            result.setdefault(name, number)
        elif macro.startswith("__NR_"):
            name = macro[len("__NR_") :]
            result.setdefault(name, number)
    return result


def _trace_names(text: str) -> tuple[list[str], list[str]]:
    names: list[str] = []
    proc_paths: list[str] = []
    for line in text.splitlines():
        match = TRACE_LINE_RE.match(line)
        if match:
            names.append(match.group(1))
        proc_paths.extend(PROC_PATH_RE.findall(line))
    return names, sorted(set(proc_paths))


def _trace_syscall_numbers(
    syscall_names: Iterable[str], syscall_numbers_by_name: dict[str, int]
) -> tuple[list[int], list[str], dict[str, int]]:
    names = sorted(set(syscall_names))
    unmapped = sorted(name for name in names if name not in syscall_numbers_by_name)
    if unmapped:
        raise DerivationError(
            "trace contains syscall names absent from the authoritative AArch64 headers: "
            + ", ".join(unmapped)
        )
    mapping = {name: syscall_numbers_by_name[name] for name in names}
    return sorted(set(mapping.values())), unmapped, mapping


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def ingest_trace(trace_path: Path) -> dict[str, Any]:
    """Ingest one preserved QEMU ``-strace`` file without executing anything."""

    trace_path = _require_private(trace_path, "trace input")
    if not trace_path.is_file() or trace_path.is_symlink():
        raise DerivationError(f"trace input is not a private regular file: {trace_path}")
    try:
        raw = trace_path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise DerivationError(f"cannot read trace input: {trace_path}") from exc
    names, proc_paths = _trace_names(raw)
    if not names:
        raise DerivationError(f"trace contains no syscall lines: {trace_path}")
    syscall_numbers_by_name = parse_syscall_header()
    numbers, unmapped, mapping = _trace_syscall_numbers(
        names, syscall_numbers_by_name
    )
    signal_trampoline_entries = sorted(
        name for name in set(names) if name in SIGNAL_TRAMPOLINE_SYSCALLS
    )
    return {
        "method": "ingested preserved QEMU -strace; no host/device execution performed by this invocation",
        "interpretation": "two-sided exercised-path lower bound: the trace may be a strict subset of the real syscall set, so a missing syscall can kill the service, while every observed syscall must be in the candidate allowlist",
        "trace_input": {
            "path": _repo_relative(trace_path),
            "sha256": sha256_file(trace_path),
            "line_count": len(raw.splitlines()),
        },
        "runs": [
            {
                "name": "preserved-operator-session",
                "trace_line_count": len(names),
                "syscall_names": sorted(set(names)),
                "proc_paths": proc_paths,
                "signal_trampoline_entries": signal_trampoline_entries,
            }
        ],
        "observed_syscall_names": sorted(set(names)),
        "observed_syscall_numbers": numbers,
        "syscall_name_to_number": mapping,
        "unmapped_syscall_names": unmapped,
        "observed_signal_trampoline_entries": signal_trampoline_entries,
        "observed_proc_paths": proc_paths,
        "observed_global_proc_scalars": [],
        "host_network_contact": "preserved evidence only; this invocation opened no socket and contacted no device or device network",
        "completeness": "preserved-session-lower-bound-required-scenarios-recorded-separately-in-trace-readme",
    }


def _run_qemu_trace(
    name: str,
    binary: Path,
    argv: list[str],
    trace_dir: Path,
    *,
    timeout_seconds: float = 3.0,
) -> dict[str, Any]:
    qemu = shutil.which("qemu-aarch64")
    if qemu is None:
        raise DerivationError("qemu-aarch64 is unavailable")
    trace_dir.mkdir(parents=True, exist_ok=True)
    command = [qemu, "-strace", str(binary), *argv]
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        raw = completed.stderr
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stderr = exc.stderr or ""
        raw = stderr if isinstance(stderr, str) else stderr.decode("utf-8", "replace")
        returncode = None
    (trace_dir / f"{name}.strace").write_text(raw, encoding="utf-8")
    names, proc_paths = _trace_names(raw)
    syscall_numbers_by_name = parse_syscall_header()
    syscall_numbers, unmapped, mapping = _trace_syscall_numbers(
        names, syscall_numbers_by_name
    )
    socket_permission_denied = any(
        "socket(" in line and "errno=1" in line for line in raw.splitlines()
    )
    return {
        "name": name,
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "trace_line_count": len(names),
        "syscall_names": sorted(set(names)),
        "syscall_numbers": syscall_numbers,
        "syscall_name_to_number": mapping,
        "unmapped_syscall_names": unmapped,
        "proc_paths": proc_paths,
        "socket_permission_denied": socket_permission_denied,
    }


def _safe_extract(source: Path, destination: Path) -> Path:
    if source.is_dir():
        return source
    if not source.is_file() or not tarfile.is_tarfile(source):
        raise DerivationError("Dropbear source must be a local directory or tar archive")
    with tarfile.open(source, "r:*") as archive:
        members = archive.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            try:
                target.relative_to(destination.resolve())
            except ValueError as exc:
                raise DerivationError("Dropbear source archive escapes staging") from exc
            if member.issym() or member.islnk() or not (member.isdir() or member.isfile()):
                raise DerivationError("Dropbear source archive contains a forbidden member")
        archive.extractall(destination)
    roots = sorted(destination.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise DerivationError("Dropbear source archive must contain one source directory")
    return roots[0]


def _read_source_member(source: Path, suffix: str) -> str:
    source = _require_private(source, "Dropbear source")
    if source.is_dir():
        matches = sorted(path for path in source.rglob(Path(suffix).name) if path.as_posix().endswith(suffix))
        if len(matches) != 1:
            raise DerivationError(f"expected one Dropbear source consumer: {suffix}")
        return matches[0].read_text(encoding="utf-8", errors="strict")
    if not source.is_file() or not tarfile.is_tarfile(source):
        raise DerivationError("Dropbear source must be a local directory or tar archive")
    with tarfile.open(source, "r:*") as archive:
        matches = [
            member
            for member in archive.getmembers()
            if member.isfile() and (member.name == suffix or member.name.endswith("/" + suffix))
        ]
        if len(matches) != 1:
            raise DerivationError(f"expected one Dropbear source consumer: {suffix}")
        stream = archive.extractfile(matches[0])
        if stream is None:
            raise DerivationError(f"cannot read Dropbear source consumer: {suffix}")
        return stream.read().decode("utf-8", errors="strict")


def _prepare_dropbearkey(source: Path, material_dir: Path) -> Path:
    source = _require_private(source, "Dropbear source")
    if not source.exists():
        raise DerivationError("pinned private Dropbear source is absent")
    material_dir.mkdir(parents=True, exist_ok=True)
    keygen = material_dir / "dropbearkey"
    receipt = material_dir / "dropbearkey-receipt.json"
    source_file_hash = sha256_file(source) if source.is_file() else None
    if keygen.is_file() and receipt.is_file():
        stored = json.loads(receipt.read_text(encoding="utf-8"))
        if stored.get("source_file_sha256") == source_file_hash:
            return keygen
    compiler = shutil.which("cc")
    make = shutil.which("make")
    if compiler is None or make is None:
        raise DerivationError("native cc and make are required to build dropbearkey")
    with tempfile.TemporaryDirectory(prefix="a90-dropbearkey-", dir=PRIVATE_ROOT) as temporary:
        staging_parent = Path(temporary) / "source"
        staging_parent.mkdir()
        if source.is_dir():
            staging = Path(temporary) / "dropbear-source"
            shutil.copytree(source, staging)
        else:
            staging = _safe_extract(source, staging_parent)
        env = os.environ.copy()
        env.update(
            {
                "CC": compiler,
                "AR": shutil.which("ar") or "ar",
                "RANLIB": shutil.which("ranlib") or "ranlib",
                "CFLAGS": "-O2 -fPIE -fno-ident",
                "LDFLAGS": "",
                "LC_ALL": "C",
                "TZ": "UTC",
                "SOURCE_DATE_EPOCH": "0",
            }
        )
        configure = staging / "configure"
        if configure.is_file():
            subprocess.run(
                [str(configure), "--disable-pam", "--disable-zlib"],
                cwd=staging,
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        subprocess.run(
            [make, "-j1", "dropbearkey"],
            cwd=staging,
            env=env,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        built = staging / "dropbearkey"
        if not built.is_file():
            raise DerivationError("same-source dropbearkey build produced no binary")
        temporary_output = keygen.with_name(keygen.name + ".tmp")
        shutil.copyfile(built, temporary_output)
        temporary_output.chmod(0o700)
        temporary_output.replace(keygen)
    write_json(
        receipt,
        {
            "source_file_sha256": source_file_hash,
            "dropbearkey_sha256": sha256_file(keygen),
            "host_only": True,
            "installation_authorized": False,
        },
    )
    return keygen


def _prepare_trace_host_key(source: Path, material_dir: Path) -> Path:
    keygen = _prepare_dropbearkey(source, material_dir)
    host_key = material_dir / "host_ed25519_key"
    if not host_key.exists():
        subprocess.run(
            [str(keygen), "-t", "ed25519", "-f", str(host_key)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        host_key.chmod(stat.S_IRUSR | stat.S_IWUSR)
    if not host_key.is_file() or host_key.is_symlink():
        raise DerivationError("trace-only host key was not materialized as a regular file")
    return host_key


def derive_dynamic(
    manifest: dict[str, Any],
    binaries: dict[str, Path],
    output: Path,
    source: Path,
) -> dict[str, Any]:
    trace_dir = _require_private(output / "traces", "trace output")
    material_dir = _require_private(output / "trace-material", "trace material")
    host_key = _prepare_trace_host_key(source, material_dir)
    dropbear_argv = list(manifest["dropbear"]["argv"][1:])
    dropbear_argv[dropbear_argv.index("-r") + 1] = str(host_key)
    runs = [
        _run_qemu_trace(
            "dropbear-startup", binaries["dropbear"], dropbear_argv, trace_dir
        ),
        _run_qemu_trace(
            "pid1-identity-gate", binaries["pid1"], [], trace_dir
        ),
        _run_qemu_trace(
            "probe-forced-request-identity-gate",
            binaries["probe"],
            ["--request=readiness"],
            trace_dir,
        ),
        _run_qemu_trace(
            "probe-malformed-request-identity-gate",
            binaries["probe"],
            ["--request=malformed"],
            trace_dir,
        ),
        _run_qemu_trace(
            "workload-normal-identity-gate",
            binaries["workload"],
            ["--serve"],
            trace_dir,
        ),
    ]
    syscall_names = sorted({name for run in runs for name in run["syscall_names"]})
    syscall_numbers_by_name = parse_syscall_header()
    syscall_numbers, unmapped, name_mapping = _trace_syscall_numbers(
        syscall_names, syscall_numbers_by_name
    )
    proc_paths = sorted({path for run in runs for path in run["proc_paths"]})
    startup_blocked = runs[0]["socket_permission_denied"]
    scenarios = [
        {
            "name": "full-authenticated-public-key-ssh",
            "status": "not-exercised",
            "reason": "The host cannot create the exact 3301:3301/3302:3302 execution identities or a private absolute root, and the QEMU socket path is denied before a listener exists.",
            "successor_method": "Run the same harness in a host environment that provides exact UID/GID and root-path isolation, then repeat on-device negative tests before release.",
        },
        {
            "name": "forced-dispatcher-returning-bounded-output",
            "status": "not-exercised",
            "reason": "The direct probe run stopped at its exact-identity gate; no authenticated Dropbear session reached the forced command.",
            "successor_method": "Exercise the exact a90svc shell and forced command in the authenticated session with the manifest-fixed /run/a90 record.",
        },
        {
            "name": "pid1-reap-child-and-shutdown",
            "status": "not-exercised",
            "reason": "The exact pid1 exits at its PID/identity precondition before fork, wait, or shutdown.",
            "successor_method": "Run the exact binary as PID 1 with the manifest service identity in an isolated PID namespace and capture fork, wait, signal, and exit traces.",
        },
        {
            "name": "workload-normal-work",
            "status": "not-exercised",
            "reason": "The exact workload exits at its service-identity precondition before creating /run/a90/workload.ready.",
            "successor_method": "Run it as a90svc with the native-created writable tmpfs and observe create, write, fsync, pause, signal, unlink, and exit.",
        },
        {
            "name": "bad-public-key-rejected",
            "status": "not-exercised",
            "reason": "Dropbear could not create its listening socket on this host, so no SSH authentication exchange occurred.",
            "successor_method": "Use a local isolated trace host or the attended A90 proof to send a wrong key and capture rejection without retrying a candidate.",
        },
        {
            "name": "connection-dropped-mid-handshake",
            "status": "not-exercised",
            "reason": "No listener existed after the host socket denial.",
            "successor_method": "Connect to the exact local listener, send a bounded partial SSH handshake, close, and verify the child is reaped without restart.",
        },
        {
            "name": "malformed-probe-request",
            "status": "identity-gate-only",
            "reason": "The exact binary was invoked with --request=malformed, but identity validation precedes request parsing and stopped first.",
            "successor_method": "Invoke the exact dispatcher after establishing the service identity and record the bounded malformed-request rejection.",
        },
    ]
    if startup_blocked:
        scenarios.append(
            {
                "name": "host-network-precondition",
                "status": "blocked-before-listener",
                "reason": "QEMU's Dropbear startup attempted local socket creation and the current host returned EPERM; this was not device-network contact.",
            }
        )
    return {
        "method": "qemu-aarch64 -strace on the exact private AArch64 binaries; only lines for exercised paths are counted",
        "trace_interpretation": "two-sided lower-bound: a trace may contain only exercised syscalls and may be a strict subset; missing a syscall can mean the filter would kill the service, while every observed syscall must be in the candidate allowlist",
        "runs": runs,
        "scenarios": scenarios,
        "observed_syscall_names": syscall_names,
        "observed_syscall_numbers": syscall_numbers,
        "syscall_name_to_number": name_mapping,
        "unmapped_syscall_names": unmapped,
        "observed_proc_paths": proc_paths,
        "observed_global_proc_scalars": [],
        "host_key_source": "same pinned Dropbear source; generated private and trace-only",
        "host_network_contact": "local QEMU socket creation only; no device or device-network endpoint",
        "completeness": "partial-lower-bound-required-scenarios-unexercised",
    }


def _static_gap_records(
    static: dict[str, Any],
    dynamic: dict[str, Any] | None,
    static_numbers: set[int],
) -> list[dict[str, Any]]:
    if not dynamic:
        return []
    mapping = dynamic.get("syscall_name_to_number", {})
    if not mapping:
        names = dynamic.get("observed_syscall_names", [])
        mapping = {
            name: number
            for name, number in zip(
                names, dynamic.get("observed_syscall_numbers", [])
            )
        }
    register_callers: dict[int, list[dict[str, Any]]] = {}
    for item in (
        static.get("binaries", {})
        .get("dropbear", {})
        .get("register_syscall_callers", [])
    ):
        if isinstance(item, dict) and "syscall_number" in item:
            register_callers.setdefault(int(item["syscall_number"]), []).append(item)
    generic_sites = [
        {
            "binary": "dropbear",
            "address": item.get("address_hex"),
            "consumer": item.get("function"),
            "walk_reason": item.get("reason"),
            "evidence": item.get("backward_evidence", []),
        }
        for item in static.get("binaries", {})
        .get("dropbear", {})
        .get("unresolved_sites", [])
        if item.get("consumer_decision", {}).get("classification")
        == "register-sourced-generic-wrapper"
    ]
    gaps: list[dict[str, Any]] = []
    for name, number in sorted(mapping.items()):
        if number in static_numbers:
            continue
        if name in SIGNAL_TRAMPOLINE_SYSCALLS:
            gaps.append(
                {
                    "syscall_name": name,
                    "syscall_number": number,
                    "classification": "signal-trampoline-entry",
                    "cause": SIGNAL_TRAMPOLINE_SYSCALLS[name],
                    "static_walk_result": "no private-ELF svc site exists to walk",
                    "evidence": {
                        "trace_entries": dynamic.get(
                            "observed_signal_trampoline_entries", [name]
                        )
                    },
                }
            )
            continue
        callers = register_callers.get(number, [])
        if callers and generic_sites:
            gaps.append(
                {
                    "syscall_name": name,
                    "syscall_number": number,
                    "classification": "unresolved-register-sourced-site",
                    "cause": callers[0]["cause"],
                    "static_walk_result": "stopped at generic register-sourced x8 move",
                    "evidence": {
                        "callers": callers,
                        "unresolved_generic_sites": generic_sites,
                    },
                }
            )
            continue
        gaps.append(
            {
                "syscall_name": name,
                "syscall_number": number,
                "classification": "genuine-walk-gap",
                "cause": "observed number has no resolved static site or classified register/trampoline explanation",
                "static_walk_result": "not resolved by the current backward walk",
                "evidence": {},
            }
        )
    return gaps


def reconcile(
    static: dict[str, Any],
    dynamic: dict[str, Any] | None,
    allowlist: list[int],
) -> dict[str, Any]:
    raw_static_numbers = static.get("resolved_svc_union_numbers")
    if raw_static_numbers is None:
        raw_static_numbers = static.get("union_resolved_syscall_numbers", [])
    static_numbers = set(raw_static_numbers)
    dynamic_numbers = set(dynamic["observed_syscall_numbers"]) if dynamic else set()
    allow = set(allowlist)
    missing = sorted(dynamic_numbers - allow)
    outside_static = sorted(dynamic_numbers - static_numbers)
    static_not_traced = sorted(static_numbers - dynamic_numbers)
    decisions = {
        str(number): {
            "decision": "include",
            "reason": "Deliberate conservative inclusion of every resolved static syscall; dynamic omission is not reachability proof.",
        }
        for number in static_not_traced
    }
    return {
        "resolved_svc_static_count": len(static_numbers),
        "static_syscall_count": len(static_numbers),
        "dynamic_syscall_count": len(dynamic_numbers),
        "candidate_allowlist_count": len(allow),
        "candidate_allowlist": sorted(allow),
        "traced_missing_from_allowlist": missing,
        "traced_outside_static_set": outside_static,
        "static_not_traced": static_not_traced,
        "static_not_traced_decisions": decisions,
        "static_analysis_gaps": _static_gap_records(static, dynamic, static_numbers),
        "static_upper_bound_claim": {
            "survives": not outside_static,
            "status": "survives"
            if not outside_static
            else "does-not-survive-observed-outside-resolved-svc-union",
            "corrected_claim": "The resolved svc-site union is a partial known set, not an upper bound; the evidence-derived candidate numeric allowlist is the resolved union plus every mapped observed syscall, with signal-trampoline and register-sourced gaps explicitly recorded.",
        },
        "corrected_candidate_allowlist": sorted(static_numbers | dynamic_numbers),
        "regression_pass": not missing,
        "static_analysis_defect": bool(outside_static),
        "deliberate_conservative_static_choice": True,
    }


def derive_capabilities(
    dropbear_source: Path = DEFAULT_DROPBEAR_SOURCE,
    dynamic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    forbidden_component_fragments = [
        "setuid(",
        "setgid(",
        "setgroups(",
        "capset(",
        "mount(",
        "chown(",
        "mknod(",
    ]
    component_requirements = {
        "pid1": ["getpid() != 1", "fork()", "waitpid", "execve", "kill"],
        "dispatcher": ["getuid()", "open(\"/run/a90/workload.ready\"", "read(fd", "write(STDOUT_FILENO"],
        "workload": ["open(\"/run/a90/workload.ready\"", "write(fd", "fsync(fd)", "unlink(\"/run/a90/workload.ready\""],
    }
    component_checks: dict[str, Any] = {}
    for name, required in component_requirements.items():
        source_path = COMPONENT_SOURCE_ROOT / f"a90_{'probe' if name == 'dispatcher' else name}.c"
        text = source_path.read_text(encoding="utf-8", errors="strict")
        missing = [fragment for fragment in required if fragment not in text]
        if missing:
            raise DerivationError(f"{name} capability consumer check missing: {missing}")
        forbidden = [fragment for fragment in forbidden_component_fragments if fragment in text]
        if forbidden:
            raise DerivationError(f"{name} has a direct privileged consumer: {forbidden}")
        component_checks[name] = {
            "source": str(source_path.relative_to(REPO_ROOT)),
            "required_fragments": required,
            "forbidden_direct_privileged_fragments": forbidden_component_fragments,
            "missing_fragments": [],
        }
    auth_source = _read_source_member(dropbear_source, "src/svr-auth.c")
    authpubkey_source = _read_source_member(dropbear_source, "src/svr-authpubkey.c")
    auth_fragments = ["setgid", "initgroups", "setresgid", "setuid", "setegid"]
    authpubkey_fragments = ["setegid", "seteuid"]
    for fragment in auth_fragments:
        if fragment not in auth_source:
            raise DerivationError(f"svr-auth.c capability consumer check missing: {fragment}")
    for fragment in authpubkey_fragments:
        if fragment not in authpubkey_source:
            raise DerivationError(
                f"svr-authpubkey.c capability consumer check missing: {fragment}"
            )
    transition_observed = bool(
        dynamic
        and {"setresgid", "setresuid"}.issubset(
            set(dynamic.get("observed_syscall_names", []))
        )
    )
    transition_status = (
        "observed-borrowed-identity-exact-3302-to-3301-transition-unproved"
        if transition_observed
        else "deferred-unexercised"
    )
    return {
        "basis": "tracked component source plus pinned Dropbear source consumers; no capability is inferred from a manifest declaration alone",
        "source_checks": {
            "components": component_checks,
            "dropbear": {
                "svr_auth": ["setgid", "initgroups", "setresgid", "setuid", "setegid"],
                "svr_authpubkey": ["setegid", "seteuid"],
                "source_verified": True,
            },
        },
        "profiles": {
            "pid1": {
                "minimum": [],
                "exact": True,
                "reason": "The tracked pid1 only checks identity, installs signal handlers, sets dumpability, forks, waits, signals its child, and execs the workload; it owns its service paths and performs no privileged transition.",
            },
            "dispatcher": {
                "minimum": [],
                "exact": True,
                "reason": "The tracked probe only checks identity, reads the bounded readiness file, closes it, and writes bounded stdout; ownership supplies DAC access.",
            },
            "workload": {
                "minimum": [],
                "exact": True,
                "reason": "The tracked workload creates/writes/fsyncs/unlinks its service-owned readiness file and handles signals; it needs no privileged operation.",
            },
            "key_daemon": {
                "minimum": ["CAP_SETGID", "CAP_SETUID"],
                "exact": True,
                "reason": "Pinned Dropbear src/svr-auth.c changes gid/groups and uid after authentication, and src/svr-authpubkey.c changes euid/egid while checking the service-owned key file. The listener is port 2222, so CAP_NET_BIND_SERVICE is not required; the key tree is key-daemon-owned, so DAC override is not required.",
                "dynamic_auth_transition_proof": transition_status,
                "observed_transition_syscalls": ["setresgid", "setresuid"]
                if transition_observed
                else [],
                "observed_identity_deviation": "The preserved trace used the invoking uid/gid for a90svc, so the calls kept the same borrowed identity; it did not exercise the distinct 3302-to-3301 privileged transition."
                if transition_observed
                else None,
            },
        },
        "all_other_capabilities": "absent",
    }


def derive_proc(static: dict[str, Any], dynamic: dict[str, Any] | None) -> dict[str, Any]:
    observed_paths = sorted(dynamic["observed_proc_paths"] if dynamic else [])
    non_scalar = ["/proc/self/exe"] if "/proc/self/exe" in observed_paths else []
    global_paths = [
        path
        for path in observed_paths
        if path not in non_scalar and path.startswith("/proc/")
    ]
    return {
        "observed_paths": observed_paths,
        "observed_global_read_only_paths": global_paths,
        "observed_global_read_only_scalars": [],
        "finite_global_scalar_allowlist": [],
        "non_scalar_per_task_paths": non_scalar,
        "status": "observed-global-paths-but-finite-scalar-closure-remains-deferred",
        "unexercised_literal_candidates": [
            "/proc/interrupts",
            "/proc/loadavg",
            "/proc/meminfo",
            "/proc/net/dev",
            "/proc/net/netstat",
            "/proc/net/rt_cache",
            "/proc/net/tcp",
            "/proc/stat",
            "/proc/sys/kernel/ngroups_max",
            "/proc/sys/kernel/random/entropy_avail",
            "/proc/sys/kernel/rtsig-max",
            "/proc/sys/vm/overcommit_memory",
            "/proc/vmstat",
        ],
        "reason": "The trace observed /proc/interrupts as a global non-scalar path and /proc/self/exe as a per-task link; no finite scalar value was derived. Static path literals are not proof of reads, and the exact PID-1/workload namespace path remains unexercised.",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--binary-root", type=Path, default=DEFAULT_BINARY_ROOT)
    parser.add_argument("--dropbear-source", type=Path, default=DEFAULT_DROPBEAR_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="run bounded qemu-aarch64 traces in addition to the static derivation",
    )
    parser.add_argument(
        "--trace",
        type=Path,
        help="ingest one preserved private qemu-aarch64 -strace file instead of running QEMU",
    )
    parser.add_argument(
        "--allowlist",
        type=int,
        nargs="*",
        help="candidate syscall numbers to check; defaults to the raw static union plus ingested observations",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        if args.dynamic and args.trace is not None:
            raise DerivationError("--dynamic and --trace are mutually exclusive")
        manifest = load_manifest(args.manifest)
        binaries = binary_paths(args.binary_root)
        static = derive_static(manifest, binaries)
        dynamic = (
            ingest_trace(args.trace)
            if args.trace is not None
            else derive_dynamic(manifest, binaries, args.output, args.dropbear_source)
            if args.dynamic
            else None
        )
        allowlist = (
            sorted(set(args.allowlist))
            if args.allowlist is not None
            else sorted(
                set(static["resolved_svc_union_numbers"])
                | set(dynamic["observed_syscall_numbers"] if dynamic else [])
            )
        )
        result = {
            "schema": "a90-isolated-debian-security-derivation",
            "authority": {
                "candidate_eligible": False,
                "device_install_authorized": False,
                "device_contact": False,
                "device_network_contact": False,
            },
            "static": static,
            "dynamic": dynamic,
            "reconciliation": reconcile(static, dynamic, allowlist),
            "capabilities": derive_capabilities(args.dropbear_source, dynamic),
            "proc": derive_proc(static, dynamic),
        }
        output = _require_private(args.output / "derivation.json", "derivation output")
        write_json(output, result)
        print(json.dumps(result, sort_keys=True))
    except (DerivationError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
