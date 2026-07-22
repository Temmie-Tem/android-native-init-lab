#!/usr/bin/env python3
"""Build and linked-audit the FYG8 P2.25 kernel host-only."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p225_guard_poc_flush_contract as contract  # noqa: E402
import s22plus_fyg8_r4w1d_build as engine  # noqa: E402


SCHEMA = "s22plus_fyg8_p225_build_v1"
DEFAULT_RESULT_DIR = Path(
    "workspace/private/outputs/s22plus_fyg8_p225_build/build"
)
DEFAULT_LLVM_BIN = Path(
    "workspace/private/inputs/toolchains/aosp-clang-android12-release/"
    "clang-r416183b/bin"
)


def _default_linked_tool(gnu_name: str, llvm_name: str) -> Path:
    gnu_path = Path("/usr/bin") / gnu_name
    if gnu_path.is_file():
        return gnu_path
    root = contract.p219.shared.repo_root()
    return (root / DEFAULT_LLVM_BIN / llvm_name).resolve()


DEFAULT_OBJDUMP = _default_linked_tool("aarch64-linux-gnu-objdump", "llvm-objdump")
DEFAULT_NM = _default_linked_tool("aarch64-linux-gnu-nm", "llvm-nm")
BASE_OUTPUT_GATE = engine.witness_output_gate
EXPECTED_IMAGE_SHA256 = (
    "242909cf62c6ee1642f81da6c8d0cece3041d619a13f01e6f4ded5ee7957352a"
)
EXPECTED_VMLINUX_SHA256 = (
    "be763ff7ea70c3c3c59b6305fc514f9a1ae75b42a464b252fba519829eb9496f"
)
EXPECTED_FUNCTION_CODE_SHA256 = {
    "__pi___flush_dcache_area": (
        "92f72446764c8641ba8f966400b3622c51c951e75679b44ed1483285fdd9b886"
    ),
    "s22plus_fyg8_p1s_write": (
        "19ad2fc98978b0e26ed102e2485b357890db0943133636e3b9f1a33d5d2f41eb"
    ),
    "s22plus_fyg8_p1s_head": (
        "ac393f9f7a02829d4971e9d4eae76cacbb47268047126733cf2a9cf0ce52d919"
    ),
    "kernel_init": (
        "c0810cf558d4e6cfa278d7d577d40fc6bcf3c1c81edf25a9a2043485d787b1c1"
    ),
}


class BuildAuditError(ValueError):
    pass


def _run_tool(command: list[str], label: str) -> str:
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=45,
        check=False,
    )
    if completed.returncode != 0:
        raise BuildAuditError(
            f"{label} failed rc={completed.returncode}: {completed.stdout[-2000:]}"
        )
    return completed.stdout


def _symbol_ranges(symbols: str) -> dict[str, tuple[int, int]]:
    entries: list[tuple[int, str]] = []
    for line in symbols.splitlines():
        match = re.match(r"^([0-9a-fA-F]+)\s+\S\s+(\S+)$", line)
        if match:
            entries.append((int(match.group(1), 16), match.group(2)))
    addresses = sorted({address for address, _name in entries})
    next_address = dict(zip(addresses, addresses[1:]))
    ranges: dict[str, tuple[int, int]] = {}
    for address, name in entries:
        stop = next_address.get(address)
        if stop is not None:
            ranges[name] = (address, stop)
    return ranges


def _disassemble_range(
    objdump: Path,
    vmlinux: Path,
    symbol: str,
    symbol_ranges: dict[str, tuple[int, int]],
) -> str:
    if symbol not in symbol_ranges:
        raise BuildAuditError(f"linked symbol range missing: {symbol}")
    start, stop = symbol_ranges[symbol]
    output = _run_tool(
        [
            str(objdump),
            "-d",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{stop:x}",
            str(vmlinux),
        ],
        f"objdump range {symbol}",
    )
    if not re.search(rf"\b{start:x}:\s", output):
        raise BuildAuditError(f"linked symbol range was not disassembled: {symbol}")
    return output


def _instruction_bytes(disassembly: str) -> bytes:
    code = bytearray()
    for line in disassembly.splitlines():
        match = re.match(r"^\s*[0-9a-fA-F]+:\s+(.+)$", line)
        if match is None:
            continue
        fields = match.group(1).split()
        if len(fields) >= 4 and all(
            re.fullmatch(r"[0-9a-fA-F]{2}", field) for field in fields[:4]
        ):
            code.extend(int(field, 16) for field in fields[:4])
        elif fields and re.fullmatch(r"[0-9a-fA-F]{8}", fields[0]):
            code.extend(int(fields[0], 16).to_bytes(4, "little"))
    if not code:
        raise BuildAuditError("disassembly contained no AArch64 instructions")
    return bytes(code)


def _canonical_call_targets(disassembly: str) -> list[str]:
    targets = re.findall(
        r"\bbl\s+(?:0x)?[0-9a-fA-F]+\s+<([^>]+)>", disassembly
    )
    canonical: list[str] = []
    for target in targets:
        target = target.split("+", 1)[0]
        if target.startswith("__pi_"):
            target = target[5:]
        if target == "__memcpy":
            target = "memcpy"
        canonical.append(target)
    return canonical


def _require_call_subsequence(
    actual: list[str], expected: tuple[str, ...], label: str
) -> None:
    cursor = 0
    for target in actual:
        if cursor < len(expected) and target == expected[cursor]:
            cursor += 1
    if cursor != len(expected):
        raise BuildAuditError(
            f"{label} call chain incomplete: expected={expected} actual={actual}"
        )


def audit_linked_vmlinux(
    vmlinux: Path,
    objdump: Path = DEFAULT_OBJDUMP,
    nm: Path = DEFAULT_NM,
) -> dict[str, Any]:
    for label, path in (("vmlinux", vmlinux), ("objdump", objdump), ("nm", nm)):
        if path.is_symlink() or not path.is_file():
            raise BuildAuditError(f"{label} missing or indirect: {path}")
    vmlinux_sha256 = contract.p219.shared.sha256_file(vmlinux)
    if vmlinux_sha256 != EXPECTED_VMLINUX_SHA256:
        raise BuildAuditError(f"P2.25 vmlinux SHA256 mismatch: {vmlinux_sha256}")
    symbols = _run_tool([str(nm), "-n", str(vmlinux)], "nm")
    ranges = _symbol_ranges(symbols)
    required_symbols = (
        "__pi___flush_dcache_area",
        "kernel_init",
        "s22plus_fyg8_p1s_head",
        "s22plus_fyg8_p1s_write",
    )
    for symbol in required_symbols:
        if symbol not in ranges:
            raise BuildAuditError(f"required linked symbol missing: {symbol}")

    disassembly = {
        symbol: _disassemble_range(objdump, vmlinux, symbol, ranges)
        for symbol in required_symbols
    }
    code_hashes = {
        symbol: hashlib.sha256(_instruction_bytes(text)).hexdigest()
        for symbol, text in disassembly.items()
    }
    if code_hashes != EXPECTED_FUNCTION_CODE_SHA256:
        raise BuildAuditError(f"reviewed function code identities changed: {code_hashes}")

    flush = disassembly["__pi___flush_dcache_area"]
    head = disassembly["s22plus_fyg8_p1s_head"]
    writer = disassembly["s22plus_fyg8_p1s_write"]
    kernel_init = disassembly["kernel_init"]
    if "<of_address_to_resource>" in head or "<of_get_address>" in head:
        raise BuildAuditError("generic OF resource helper remains in linked target guard")
    calls = {
        "head": _canonical_call_targets(head),
        "kernel_init": _canonical_call_targets(kernel_init),
        "userspace_writer": _canonical_call_targets(writer),
    }
    _require_call_subsequence(
        calls["head"],
        (
            "of_find_node_opts_by_path",
            "of_find_property",
            "strnlen",
            "strcmp",
            "of_find_compatible_node",
            "of_device_is_available",
            "of_find_property",
            "of_find_property",
            "of_find_property",
            "of_get_property",
        ),
        "target guard",
    )
    _require_call_subsequence(
        calls["kernel_init"],
        (
            "run_init_process",
            "strcmp",
            "s22plus_fyg8_p1s_head",
            "memcpy",
            "__flush_dcache_area",
            "bcmp",
        ),
        "entry store",
    )
    _require_call_subsequence(
        calls["userspace_writer"],
        ("_copy_from_user", "s22plus_fyg8_p1s_head", "__flush_dcache_area"),
        "userspace store",
    )
    flush_counts = {
        "kernel_init": calls["kernel_init"].count("__flush_dcache_area"),
        "userspace_writer": calls["userspace_writer"].count(
            "__flush_dcache_area"
        ),
    }
    if flush_counts != {"kernel_init": 1, "userspace_writer": 1}:
        raise BuildAuditError(
            f"linked cache-flush callsite cardinality mismatch: {flush_counts}"
        )
    if not re.search(r"\bdc\s+civac\b", flush):
        raise BuildAuditError("linked flush helper lacks dc civac")
    if not re.search(r"\bdsb\s+sy\b", flush):
        raise BuildAuditError("linked flush helper lacks final dsb sy")
    return {
        "vmlinux": {
            "size": vmlinux.stat().st_size,
            "sha256": vmlinux_sha256,
            "exact_identity": True,
        },
        "required_symbols": list(required_symbols),
        "reviewed_function_code_sha256": code_hashes,
        "call_chains": calls,
        "generic_of_resource_helper_absent_from_head": True,
        "flush_calls": flush_counts,
        "entry_copy_poc_flush_readback_linked": True,
        "userspace_copy_poc_flush_readback_linked": True,
        "flush_helper_dc_civac_dsb_sy": True,
        "reset_retention_proven": False,
        "verified": True,
    }


class _ContractAdapter:
    CONFIG = contract.CONFIG
    VERDICT = contract.VERDICT
    DEFAULT_PATCH = contract.DEFAULT_PATCH
    PATCH_SHA256 = contract.PATCH_SHA256
    BASE_FILES = contract.p219.shared.BASE_FILES
    PATCHED_FILES = contract.PATCHED_FILES
    CheckError = contract.CheckError

    @staticmethod
    def run_check(
        work_tree: Path,
        patch: Path,
        _unused_inherited: Path,
        _unused_carrier_boot: Path,
        _unused_carrier_init: Path,
    ) -> dict[str, Any]:
        root = contract.p219.shared.repo_root()
        return contract.run(
            work_tree,
            patch,
            root,
            contract._resolve(root, contract.DEFAULT_DTBO),
            contract._resolve(root, contract.DEFAULT_VENDOR_DTB),
            contract._resolve(root, contract.DEFAULT_FDTOVERLAY),
            contract._resolve(root, contract.DEFAULT_LIBFDT),
        )


def output_gate(work_tree: Path) -> dict[str, Any]:
    result = BASE_OUTPUT_GATE(work_tree)
    if not result.get("image_path") or not result.get("vmlinux_path"):
        return result
    image_path = Path(result["image_path"])
    image = image_path.read_bytes()
    image_sha256 = hashlib.sha256(image).hexdigest()
    vmlinux_path = Path(result["vmlinux_path"])
    vmlinux = vmlinux_path.read_bytes()
    counts = {
        "image_userspace_count": image.count(contract.USERSPACE_PROOF),
        "vmlinux_userspace_count": vmlinux.count(contract.USERSPACE_PROOF),
        "image_unsat_count": image.count(contract.UNSAT_PROOF),
        "vmlinux_unsat_count": vmlinux.count(contract.UNSAT_PROOF),
        "image_long_family_count": image.count(contract.p219.design.ENTRY_FAMILY),
        "vmlinux_long_family_count": vmlinux.count(contract.p219.design.ENTRY_FAMILY),
        "image_unsat_family_count": image.count(contract.p219.design.UNSAT_FAMILY),
        "vmlinux_unsat_family_count": vmlinux.count(contract.p219.design.UNSAT_FAMILY),
        "image_old_e0_entry_count": image.count(contract.p219.OLD_E0_ENTRY_PROOF),
        "vmlinux_old_e0_entry_count": vmlinux.count(contract.p219.OLD_E0_ENTRY_PROOF),
        "image_old_e0_userspace_count": image.count(
            contract.p219.OLD_E0_USERSPACE_PROOF
        ),
        "vmlinux_old_e0_userspace_count": vmlinux.count(
            contract.p219.OLD_E0_USERSPACE_PROOF
        ),
    }
    expected = {
        "image_userspace_count": 1,
        "vmlinux_userspace_count": 1,
        "image_unsat_count": 1,
        "vmlinux_unsat_count": 1,
        "image_long_family_count": 2,
        "vmlinux_long_family_count": 2,
        "image_unsat_family_count": 1,
        "vmlinux_unsat_family_count": 1,
        "image_old_e0_entry_count": 0,
        "vmlinux_old_e0_entry_count": 0,
        "image_old_e0_userspace_count": 0,
        "vmlinux_old_e0_userspace_count": 0,
    }
    result.update(counts)
    result["p225_image_identity"] = {
        "size": len(image),
        "sha256": image_sha256,
        "exact_identity": image_sha256 == EXPECTED_IMAGE_SHA256,
    }
    try:
        linked = audit_linked_vmlinux(vmlinux_path)
    except BuildAuditError as exc:
        linked = {"verified": False, "error": str(exc)}
    result["p225_linked_audit"] = linked
    result["verified"] = (
        result.get("verified") is True
        and image_sha256 == EXPECTED_IMAGE_SHA256
        and counts == expected
        and linked.get("verified") is True
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "build"), default="preflight")
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    parser.add_argument("--work-tree", type=Path, default=engine.base.DEFAULT_WORK_TREE)
    parser.add_argument("--clang-repo", type=Path, default=engine.base.DEFAULT_CLANG_REPO)
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULT_DIR)
    parser.add_argument("--base-archive", type=Path, default=engine.base.DEFAULT_BASE_ARCHIVE)
    parser.add_argument("--delta-archive", type=Path, default=engine.base.DEFAULT_DELTA_ARCHIVE)
    parser.add_argument("--overlay-audit", type=Path, default=engine.base.DEFAULT_OVERLAY_AUDIT)
    parser.add_argument("--stock-baseline", type=Path, default=engine.base.DEFAULT_STOCK_BASELINE)
    parser.add_argument("--patch", type=Path, default=contract.DEFAULT_PATCH)
    args = parser.parse_args()
    args.inherited_result = args.patch
    args.carrier_boot = args.patch
    args.carrier_init = args.patch
    return args


@contextmanager
def bind_engine() -> Iterator[None]:
    replacements = {
        "SCHEMA": SCHEMA,
        "EXECUTION_SCRIPT": Path(__file__),
        "DEFAULT_RESULT_DIR": DEFAULT_RESULT_DIR,
        "contract": _ContractAdapter,
        "PROOF_BYTES": contract.ENTRY_PROOF,
        "PROOF_FAMILY": contract.ENTRY_PROOF,
        "HISTORICAL_FAMILIES": (
            b"[[S22P1E|",
            b"[[S22P1D|",
            b"[[S22R4W1B|",
            b"[[S22R4W1|",
            contract.p219.OLD_E0_ENTRY_PROOF,
            contract.p219.OLD_E0_USERSPACE_PROOF,
        ),
        "HISTORICAL_CONFIGS": (
            "CONFIG_S22PLUS_FYG8_PID1_USERSPACE_PROOF",
            "CONFIG_S22PLUS_FYG8_RUNTIME_CHECKPOINT",
            "CONFIG_S22PLUS_FYG8_COMPACT_RETAINED_WITNESS",
            "CONFIG_S22PLUS_FYG8_RETAINED_WITNESS",
        ),
        "CONTRACT_RESULT_KEY": "p225_guard_poc_flush_contract",
        "BUILD_PASS_KEY": "p225_build_pass",
        "witness_output_gate": output_gate,
        "parse_args": parse_args,
    }
    previous = {name: getattr(engine, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(engine, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(engine, name, value)


def main() -> int:
    with bind_engine():
        return engine.main()


if __name__ == "__main__":
    raise SystemExit(main())
