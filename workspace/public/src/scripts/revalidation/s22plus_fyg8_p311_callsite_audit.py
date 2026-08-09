#!/usr/bin/env python3
"""Prove all 24 exact P3.11 module-local post-BL clock return sites."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import s22plus_fyg8_p311_callsite_spec as spec


SCHEMA = "s22plus_fyg8_p311_callsite_audit_v1"
VERDICT = "PASS_P311_24_EXACT_POST_BL_CALLSITES_HOST_ONLY"


class AuditError(ValueError):
    pass


def _read_exact(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise AuditError("P3.11 exact HS-PHY module is missing or indirect")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != spec.MODULE_SHA256:
        raise AuditError("P3.11 exact HS-PHY module receipt differs")
    return data


def _run(command: list[str]) -> str:
    result = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    return result.stdout


def _symbol_rows(symbols: str, name: str) -> list[list[str]]:
    return [
        line.split()
        for line in symbols.splitlines()
        if line.split()[-1:] == [name]
    ]


def _instructions_and_relocations(
    *, objdump: str, module: Path, symbol: str
) -> tuple[dict[int, tuple[str, str]], dict[int, str]]:
    disassembly = _run(
        [objdump, "-dr", f"--disassemble={symbol}", str(module)]
    )
    instruction = re.compile(
        r"^\s*([0-9a-f]+):\s+[0-9a-f]+\s+([a-z0-9.]+)\s*(.*)$"
    )
    instructions: dict[int, tuple[str, str]] = {}
    relocations: dict[int, str] = {}
    for line in disassembly.splitlines():
        match = instruction.match(line)
        if match:
            instructions[int(match.group(1), 16)] = (
                match.group(2),
                match.group(3).strip(),
            )
            continue
        relocation = re.match(
            r"^\s*([0-9a-f]+):\s+R_AARCH64_CALL26\s+(\S+)\s*$", line
        )
        if relocation:
            relocations[int(relocation.group(1), 16)] = relocation.group(2)
    return instructions, relocations


def audit(root: Path, module: Path, objdump: str, readelf: str) -> dict:
    module_path = module if module.is_absolute() else root / module
    data = _read_exact(module_path)
    symbols = _run([readelf, "-Ws", str(module_path)])
    if _symbol_rows(symbols, "msm_hsphy_enable_clocks"):
        raise AuditError("P3.11 clock helper unexpectedly has an out-of-line symbol")

    proved_callers = []
    all_pairs: set[tuple[str, int]] = set()
    all_names: set[str] = set()
    for (
        phase,
        symbol,
        expected_value,
        expected_size,
        cfi_symbol,
        expected_cfi_value,
        callsites,
    ) in spec.CALLER_SPECS:
        rows = _symbol_rows(symbols, symbol)
        if len(rows) != 1:
            raise AuditError(f"P3.11 {symbol} symbol cardinality differs")
        fields = rows[0]
        value = int(fields[1], 16)
        size = int(fields[2], 10)
        if (
            value != expected_value
            or size != expected_size
            or fields[3] != "FUNC"
            or fields[4] != "LOCAL"
        ):
            raise AuditError(f"P3.11 {symbol} identity differs")
        cfi_rows = _symbol_rows(symbols, cfi_symbol)
        if len(cfi_rows) != 1 or int(cfi_rows[0][1], 16) != expected_cfi_value:
            raise AuditError(f"P3.11 {symbol} CFI jump-table identity differs")
        instructions, relocations = _instructions_and_relocations(
            objdump=objdump, module=module_path, symbol=symbol
        )
        proved_sites = []
        for name, clock, operation, offset, consumer in callsites:
            if name in all_names or (symbol, offset) in all_pairs:
                raise AuditError("P3.11 callsite name or address is duplicated")
            all_names.add(name)
            all_pairs.add((symbol, offset))
            if offset % 4 != 0 or offset <= 0 or offset >= size:
                raise AuditError(f"P3.11 {name} offset is outside its symbol")
            probe_address = value + offset
            bl_address = probe_address - 4
            bl = instructions.get(bl_address)
            use = instructions.get(probe_address)
            if bl is None or bl[0] != "bl":
                raise AuditError(f"P3.11 {name} is not immediately after BL")
            if relocations.get(bl_address) != f"clk_{operation}":
                raise AuditError(f"P3.11 {name} BL relocation target differs")
            if use is None or use[0] != consumer or not use[1].startswith("w0,"):
                raise AuditError(f"P3.11 {name} does not immediately consume w0")
            proved_sites.append(
                {
                    "name": name,
                    "phase": phase,
                    "clock": clock,
                    "operation": operation,
                    "symbol": symbol,
                    "offset": offset,
                    "bl_address": bl_address,
                    "probe_address": probe_address,
                    "consumer": f"{use[0]} {use[1]}",
                    "w0_unconsumed_at_probe": True,
                    "module_local_callsite_attribution": True,
                }
            )
        proved_callers.append(
            {
                "phase": phase,
                "symbol": symbol,
                "symbol_value": value,
                "symbol_size": size,
                "cfi_jump_table": cfi_symbol,
                "cfi_jump_table_value": expected_cfi_value,
                "callsites": proved_sites,
                "callsite_count": len(proved_sites),
            }
        )

    if len(all_pairs) != spec.CALLSITE_COUNT:
        raise AuditError("P3.11 exact callsite count differs")
    build_id_output = _run([readelf, "-n", str(module_path)])
    if f"Build ID: {spec.MODULE_BUILD_ID}" not in build_id_output:
        raise AuditError("P3.11 exact HS-PHY module Build ID differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "module": {
            "path": module.as_posix(),
            "size": len(data),
            "sha256": spec.MODULE_SHA256,
            "build_id": spec.MODULE_BUILD_ID,
            "out_of_line_helper_symbol_absent": True,
        },
        "callers": proved_callers,
        "callsite_count": len(all_pairs),
        "a_b_offset_identity": {
            "runtime_module_shared": True,
            "module_rebuilt_for_candidate": False,
            "fixed_module_receipt_is_offset_contract": True,
            "descriptor_offset_count": len(all_pairs),
        },
        "verified": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--module", type=Path, default=Path(spec.MODULE_PATH))
    parser.add_argument("--objdump", default="aarch64-linux-gnu-objdump")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = audit(args.root.resolve(), args.module, args.objdump, args.readelf)
    except (AuditError, OSError, subprocess.SubprocessError) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
        return 1
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="ascii")
    print(json.dumps({"schema": SCHEMA, "verdict": VERDICT}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
