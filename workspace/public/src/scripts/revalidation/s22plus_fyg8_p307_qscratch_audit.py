#!/usr/bin/env python3
"""Prove the exact FYG8 DWC3 MSM QSCRATCH post-readback probe site."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import s22plus_fyg8_p307_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p307_qscratch_callsite_audit_v1"
VERDICT = "PASS_P307_EXACT_QSCRATCH_CALLSITE_AUDIT_HOST_ONLY"


class AuditError(ValueError):
    pass


def _run(command: list[str]) -> str:
    return subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    ).stdout


def audit(root: Path, module: Path, objdump: str, readelf: str) -> dict:
    path = module if module.is_absolute() else root / module
    if path.is_symlink() or not path.is_file():
        raise AuditError("P3.07 exact DWC3 MSM module is missing or indirect")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != spec.DWC3_MODULE_SHA256:
        raise AuditError("P3.07 exact DWC3 MSM module receipt differs")

    symbols = _run([readelf, "-Ws", str(path)])
    rows = [
        line for line in symbols.splitlines()
        if line.split()[-1:] == [spec.QSCRATCH_SYMBOL]
    ]
    if len(rows) != 1:
        raise AuditError("P3.07 start-peripheral symbol cardinality differs")
    symbol_value = int(rows[0].split()[1], 16)
    if symbol_value != spec.QSCRATCH_SYMBOL_VALUE:
        raise AuditError("P3.07 start-peripheral symbol value differs")

    disassembly = _run(
        [objdump, "-dr", f"--disassemble={spec.QSCRATCH_SYMBOL}", str(path)]
    )
    instruction = re.compile(
        r"^\s*([0-9a-f]+):\s+[0-9a-f]+\s+([a-z0-9.]+)\s*(.*)$"
    )
    instructions: dict[int, tuple[str, str]] = {}
    for line in disassembly.splitlines():
        match = instruction.match(line)
        if match:
            instructions[int(match.group(1), 16)] = (
                match.group(2), match.group(3).strip()
            )

    # Prove the linked write/readback/barrier stream actually used by kprobes.
    expected = {
        0x4A0: ("dmb", "oshst"),
        0x4A4: ("orr", "w22, w22, #0x100000"),
        0x4A8: ("nop", ""),
        0x4AC: ("str", "w22, [x2]"),
        0x4B0: ("nop", ""),
        0x4B4: ("ldr", "w21, [x2]"),
        0x4B8: ("nop", ""),
        0x4BC: ("dmb", "oshld"),
        0x4C0: ("mov", "w8, w21"),
        0x4C4: ("eor", "x8, x8, x8"),
        0x4C8: ("cbnz", "x8,"),
        0x4CC: ("ldr", "x8, [x19, #32]"),
    }

    proved = []
    for offset, (mnemonic, operand_prefix) in sorted(expected.items()):
        actual = instructions.get(symbol_value + offset)
        if actual is None or actual[0] != mnemonic:
            raise AuditError(f"P3.07 instruction differs at +0x{offset:x}")
        if operand_prefix and not actual[1].startswith(operand_prefix):
            raise AuditError(f"P3.07 operands differ at +0x{offset:x}")
        proved.append({
            "offset": offset,
            "address": symbol_value + offset,
            "instruction": f"{actual[0]} {actual[1]}".rstrip(),
        })

    build_id = _run([readelf, "-n", str(path)])
    if f"Build ID: {spec.DWC3_MODULE_BUILD_ID}" not in build_id:
        raise AuditError("P3.07 exact DWC3 MSM Build ID differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "module": {
            "path": module.as_posix(),
            "size": len(data),
            "sha256": spec.DWC3_MODULE_SHA256,
            "build_id": spec.DWC3_MODULE_BUILD_ID,
        },
        "symbol": {"name": spec.QSCRATCH_SYMBOL, "value": symbol_value},
        "probe": {
            "offset": spec.QSCRATCH_PROBE_OFFSET,
            "address": symbol_value + spec.QSCRATCH_PROBE_OFFSET,
            "register": "w21",
            "readback_load_offset": spec.QSCRATCH_READBACK_OFFSET,
            "vbus_valid_bit": spec.QSCRATCH_VBUS_VALID_BIT,
            "sw_session_valid_select_bit": spec.QSCRATCH_SW_SESSVLD_SEL_BIT,
            "w21_unmodified_from_readback_to_probe": True,
            "instructions": proved,
        },
        "a_b_offset_identity": {
            "runtime_module_shared": True,
            "module_rebuilt_for_candidate": False,
            "module_receipt_is_offset_contract": True,
            "verified": True,
        },
        "verified": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--module", type=Path, default=Path(spec.DWC3_MODULE_PATH))
    parser.add_argument("--objdump", default="aarch64-linux-gnu-objdump")
    parser.add_argument("--readelf", default="readelf")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = audit(args.root.resolve(), args.module, args.objdump, args.readelf)
    except (AuditError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": VERDICT}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
