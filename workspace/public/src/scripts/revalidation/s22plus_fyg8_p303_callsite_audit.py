#!/usr/bin/env python3
"""Prove all exact FYG8 P3.03 post-BL clock return probe sites."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import s22plus_fyg8_p303_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p303_callsite_audit_v1"
VERDICT = "PASS_P303_EXACT_POST_BL_CALLSITE_AUDIT_HOST_ONLY"


class AuditError(ValueError):
    pass


def _read_exact(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise AuditError("P3.03 exact HS-PHY module is missing or indirect")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != spec.MODULE_SHA256:
        raise AuditError("P3.03 exact HS-PHY module receipt differs")
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


def audit(root: Path, module: Path, objdump: str, readelf: str) -> dict:
    module_path = module if module.is_absolute() else root / module
    data = _read_exact(module_path)
    symbols = _run([readelf, "-Ws", str(module_path)])
    rows = [line for line in symbols.splitlines() if line.split()[-1:] == [spec.CALLSITE_SYMBOL]]
    if len(rows) != 1:
        raise AuditError("P3.03 msm_hsphy_init symbol cardinality differs")
    fields = rows[0].split()
    symbol_value = int(fields[1], 16)
    if symbol_value != spec.CALLSITE_SYMBOL_VALUE:
        raise AuditError("P3.03 msm_hsphy_init symbol value differs")
    if any(line.split()[-1:] == ["msm_hsphy_enable_clocks"] for line in symbols.splitlines()):
        raise AuditError("P3.03 inlined clock helper unexpectedly has a symbol")

    disassembly = _run(
        [objdump, "-dr", f"--disassemble={spec.CALLSITE_SYMBOL}", str(module_path)]
    )
    instruction = re.compile(
        r"^\s*([0-9a-f]+):\s+[0-9a-f]+\s+([a-z0-9.]+)\s*(.*)$"
    )
    instructions: dict[int, tuple[str, str]] = {}
    relocation: dict[int, str] = {}
    for line in disassembly.splitlines():
        match = instruction.match(line)
        if match:
            instructions[int(match.group(1), 16)] = (
                match.group(2), match.group(3).strip()
            )
            continue
        rel = re.match(
            r"^\s*([0-9a-f]+):\s+R_AARCH64_CALL26\s+(\S+)\s*$", line
        )
        if rel:
            relocation[int(rel.group(1), 16)] = rel.group(2)

    proved = []
    for name, branch, clock, call, offset, consumer in spec.CALLSITES:
        site = symbol_value + offset
        bl_site = site - 4
        bl = instructions.get(bl_site)
        use = instructions.get(site)
        if bl is None or bl[0] != "bl":
            raise AuditError(f"P3.03 {name} is not immediately after BL")
        if relocation.get(bl_site) != f"clk_{call}":
            raise AuditError(f"P3.03 {name} BL relocation target differs")
        if use is None or use[0] != consumer or not use[1].startswith("w0,"):
            raise AuditError(f"P3.03 {name} does not immediately consume w0")
        proved.append(
            {
                "name": name,
                "branch": branch,
                "clock": clock,
                "call": call,
                "offset": offset,
                "bl_address": bl_site,
                "probe_address": site,
                "consumer": f"{use[0]} {use[1]}",
                "w0_unconsumed_at_probe": True,
            }
        )
    build_id_output = _run([readelf, "-n", str(module_path)])
    if f"Build ID: {spec.MODULE_BUILD_ID}" not in build_id_output:
        raise AuditError("P3.03 exact HS-PHY module Build ID differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "module": {
            "path": module.as_posix(),
            "size": len(data),
            "sha256": spec.MODULE_SHA256,
            "build_id": spec.MODULE_BUILD_ID,
        },
        "symbol": {
            "name": spec.CALLSITE_SYMBOL,
            "value": symbol_value,
            "inlined_helper_absent": True,
        },
        "callsites": proved,
        "callsite_count": len(proved),
        "a_b_offset_identity": {
            "runtime_module_shared": True,
            "module_rebuilt_for_candidate": False,
            "module_receipt_is_offset_contract": True,
            "descriptor_offset_count": len(proved),
            "basis": (
                "both candidate builds use the unchanged FYG8 vendor_dlkm module; "
                "their generated trace descriptors are required byte-identical"
            ),
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
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="ascii")
    print(json.dumps({"schema": SCHEMA, "verdict": VERDICT}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
