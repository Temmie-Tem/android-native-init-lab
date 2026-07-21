#!/usr/bin/env python3
"""Independently qualify three host-only FYG8 R4W1-D candidate reproductions."""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import s22plus_fyg8_r4w1b_candidate_static_checker as engine  # noqa: E402
import s22plus_fyg8_r4w1d_witness_contract as contract  # noqa: E402


SCHEMA = "s22plus_fyg8_r4w1d_candidate_static_checker_v1"
VERDICT = "PASS_R4W1D_CANDIDATE_THREE_REPRO_STATIC_CONTRACT"
TARGET = contract.TARGET
CANDIDATE_SCHEMA = "s22plus_fyg8_r4w1d_candidate_build_v1"
CANDIDATE_VERDICT = "PASS_R4W1D_CANDIDATE_BUILT_HOST_ONLY"
RUNG = "R4W1-D"
CARRIER_SHA256 = contract.CARRIER_BOOT_SHA256
IMAGE_SHA256 = "bb768461a55a8ed4b36b4e5777e12e37953fa76fa3703b332b4273d653cbdcd9"
REPRO_RESULT_SIZE = 319_637
REPRO_RESULT_SHA256 = "6abde754a7411168bfd7bd42878efd9d743cd9cace86b113fbfb79294a6f5a60"
REPRO_SCHEMA = "s22plus_fyg8_r4w1d_repro_check_v1"
REPRO_VERDICT = "PASS_R4W1D_CLEAN_REPRODUCIBILITY"
INIT_SIZE = contract.CARRIER_INIT_SIZE
INIT_MODE = 0o750
INIT_SHA256 = contract.CARRIER_INIT_SHA256
MARKER = contract.PROOF.encode("ascii")
MARKER_FAMILY = contract.PROOF_FAMILY.encode("ascii")
HISTORICAL_FAMILY = b"[[S22R4W1"

DEFAULT_CARRIER = contract.DEFAULT_CARRIER_BOOT
DEFAULT_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1d_candidate_inputs/Image"
)
DEFAULT_REPRO_RESULT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1d_static_repro_20260721/"
    "repro/result.json"
)
DEFAULT_VENDOR_BOOT = engine.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = engine.DEFAULT_LZ4
DEFAULT_AVBTOOL = engine.DEFAULT_AVBTOOL
DEFAULT_ODIN = engine.DEFAULT_ODIN
DEFAULT_REPRO_A = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1d_candidate/reproduction-a"
)
DEFAULT_REPRO_B = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1d_candidate/reproduction-b"
)
DEFAULT_REPRO_C = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1d_candidate/reproduction-c"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_r4w1d_candidate/static-check-result.json"
)

CheckError = engine.CheckError


def inspect_watchdog_init(elf: bytes) -> dict[str, Any]:
    if len(elf) < 64 or elf[:6] != b"\x7fELF\x02\x01":
        raise CheckError("watchdog /init is not ELF64 little-endian")
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", elf, 0)
    elf_type, machine, entry, phoff = header[1], header[2], header[4], header[5]
    phentsize, phnum = header[9], header[10]
    if elf_type != 2 or machine != 183 or phentsize != 56 or not phnum:
        raise CheckError("watchdog /init ELF contract mismatch")
    mapped_entrypoint = False
    interpreter = False
    dynamic = False
    executable_stack = False
    for index in range(phnum):
        offset = phoff + index * phentsize
        if offset + phentsize > len(elf):
            raise CheckError("watchdog /init has truncated program headers")
        p_type, p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, _p_memsz, _p_align = (
            struct.unpack_from("<IIQQQQQQ", elf, offset)
        )
        interpreter |= p_type == 3
        dynamic |= p_type == 2
        executable_stack |= p_type == 0x6474E551 and bool(p_flags & 1)
        if p_type == 1 and p_flags & 1 and p_vaddr <= entry < p_vaddr + p_filesz:
            mapped_entrypoint = p_offset + entry - p_vaddr < len(elf)
    if interpreter or dynamic or executable_stack or not mapped_entrypoint:
        raise CheckError("watchdog /init is not a mapped static non-exec-stack ELF")
    required = (
        b"S22_NATIVE_INIT_R4W1C_WDT_CARRIER",
        b"exact_finit_rc=0",
        b"proc_modules_exact=1",
        b"phase=module_load_complete count=5",
        b"phase=proc_modules_verified count=5 exact=1",
        b"phase=park_enter",
        b"module_closure_visible=1",
        b"watchdog_ownership=not_directly_proven",
        b"functional_proof=bounded_live_survival",
    )
    missing = [token.decode("ascii") for token in required if token not in elf]
    forbidden = (
        b"/dev/block",
        b"/config",
        b"usb_gadget",
        b"ttyGS0",
        b"reboot_request=download",
        b"/system/bin/init",
    )
    hits = [token.decode("ascii") for token in forbidden if token in elf]
    if missing or hits:
        raise CheckError(
            f"watchdog /init runtime contract mismatch: missing={missing} forbidden={hits}"
        )
    return {
        "elf_class": 64,
        "machine": "AArch64",
        "type": "ET_EXEC",
        "entrypoint": entry,
        "program_header_count": phnum,
        "interpreter": False,
        "dynamic": False,
        "executable_stack": False,
        "runtime_contract_strings": len(required),
        "verified": True,
    }


@contextmanager
def _bind_engine_contract() -> Iterator[None]:
    replacements: dict[str, Any] = {
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "TARGET": TARGET,
        "CANDIDATE_SCHEMA": CANDIDATE_SCHEMA,
        "CANDIDATE_VERDICT": CANDIDATE_VERDICT,
        "RUNG": RUNG,
        "CARRIER_SHA256": CARRIER_SHA256,
        "IMAGE_SHA256": IMAGE_SHA256,
        "REPRO_RESULT_SIZE": REPRO_RESULT_SIZE,
        "REPRO_RESULT_SHA256": REPRO_RESULT_SHA256,
        "REPRO_SCHEMA": REPRO_SCHEMA,
        "REPRO_VERDICT": REPRO_VERDICT,
        "CARRIER_LABEL": "R4W1-C watchdog carrier",
        "IMAGE_LABEL": "R4W1-D Image",
        "REPRO_LABEL": "R4W1-D reproduction result",
        "CARRIER_INPUT_KEY": "r4w1c_watchdog_carrier",
        "IMAGE_INPUT_KEY": "r4w1d_image",
        "REPRO_INPUT_KEY": "r4w1d_reproduction_result",
        "RESULT_REPRO_INPUT_KEY": "r4w1d_reproduction_result",
        "INIT_SIZE": INIT_SIZE,
        "INIT_MODE": INIT_MODE,
        "INIT_SHA256": INIT_SHA256,
        "INIT_INSPECTOR": inspect_watchdog_init,
        "MARKER": MARKER,
        "MARKER_FAMILY": MARKER_FAMILY,
        "HISTORICAL_FAMILY": HISTORICAL_FAMILY,
    }
    previous = {name: getattr(engine, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(engine, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(engine, name, value)


def verify_reproduction_result(encoded: bytes) -> dict[str, Any]:
    with _bind_engine_contract():
        return engine.verify_reproduction_result(encoded)


def classify_marker(data: bytes) -> dict[str, Any]:
    with _bind_engine_contract():
        return engine.classify_marker(data)


def audit_rootfs(carrier: bytes, vendor_boot: bytes, lz4_tool: Path) -> dict[str, Any]:
    with _bind_engine_contract():
        return engine.audit_rootfs(carrier, vendor_boot, lz4_tool)


def audit(args: argparse.Namespace) -> dict[str, Any]:
    with _bind_engine_contract():
        return engine.audit(args)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrier", type=Path, default=DEFAULT_CARRIER)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--repro-result", type=Path, default=DEFAULT_REPRO_RESULT)
    parser.add_argument("--vendor-boot", type=Path, default=DEFAULT_VENDOR_BOOT)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--avbtool", type=Path, default=DEFAULT_AVBTOOL)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--reproduction-a", type=Path, default=DEFAULT_REPRO_A)
    parser.add_argument("--reproduction-b", type=Path, default=DEFAULT_REPRO_B)
    parser.add_argument("--reproduction-c", type=Path, default=DEFAULT_REPRO_C)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = audit(args)
        output = engine.resolve(engine.repo_root(), args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, encoded.encode("ascii"))
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except (CheckError, engine.verify.BootVerifyError, OSError) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": VERDICT,
                "candidate_sha256": result["independent_construction"][
                    "candidate_sha256"
                ],
                "blockers": [],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
