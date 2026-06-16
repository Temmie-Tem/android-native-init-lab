#!/usr/bin/env python3
"""V2599 host-only ACDB post-preGET downstream geometry recon.

This unit consumes the private stock libacdbloader.so and V2594/V2597 evidence,
then maps the downstream acdb_ioctl/ioctl rows after the first proven
`0x1122e -> 0x10005000` metadata query. It does not touch the device and does
not execute ACDB, audio, or calibration ioctls.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

import native_audio_acdb_send_audio_cal_preget_recon_v2594 as v2594

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2599"
BUILD_TAG = "v2599-audio-acdb-post-preget-geometry-re"
DEFAULT_LIB = v2594.DEFAULT_LIB
DEFAULT_OUT_DIR = ROOT / "workspace/private/runs/audio/v2599-acdb-post-preget-geometry-recon"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2599_AUDIO_ACDB_POST_PREGET_GEOMETRY_RE_2026-06-16.md"
DEFAULT_V2594_JSON = ROOT / "workspace/private/runs/audio/v2594-send-audio-cal-preget-recon/v2594-preget-recon.json"
DEFAULT_V2597_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2597_AUDIO_ACDB_DIRECT_PREGET_LIVE_RESULT_2026-06-16.md"
DEFAULT_LLVM_OBJDUMP = v2594.DEFAULT_LLVM_OBJDUMP
DEFAULT_LLVM_READELF = v2594.DEFAULT_LLVM_READELF

SEND_AUDIO_CAL_START = 0x9D30
POST_PREGET_STOP = 0xB550
AUDIO_SET_CALIBRATION = 0xC00461CB
EXPECTED_DIRECT_WORD = 0x10005000

INSTRUCTION_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+[0-9a-fA-F ]+\s+(.+?)\s*$")
MOV_RE = re.compile(r"\bmov([wt]|s)\s+([a-z0-9]+), #(\d+)")
STR_STACK_RE = re.compile(r"\bstr\s+([a-z0-9]+), \[sp\]")
STREQ_STACK_RE = re.compile(r"\bstrd\s+([a-z0-9]+),\s*([a-z0-9]+), \[sp\]")
LDR_TABLE_RE = re.compile(r"\bldr\.w\s+r0, \[r1, r0, lsl #2\]")
REPORT_VALUE_RE = re.compile(r"output word:\s*`(0x[0-9a-fA-F]+)`")
REPORT_DECISION_RE = re.compile(r"decision:\s*`([^`]+)`")

HELPER_RANGES = [
    ("send_audio_cal_v5_entry", 0x9D30, 0xA09C, "first metadata row and immediate fake-SET wrapper"),
    ("helper_a09c", 0xA09C, 0xA258, "called from 0x9f38; caller stack literal cal type 9"),
    ("helper_a258", 0xA258, 0xA638, "called from 0x9f50; caller cal type 11 or 49 branch"),
    ("helper_a638", 0xA638, 0xAA20, "called from 0x9f90; caller cal type 12 branch"),
    ("helper_aa20", 0xAA20, 0xADC8, "called from 0x9f98/0x9fc8; caller-side buffer helper"),
    ("helper_adc8", 0xADC8, 0xAF94, "called from 0x9fa4/0x9fd4; caller command type 23 branch"),
    ("helper_af94", 0xAF94, 0xB370, "called from 0x9fb4/0x9fea; caller cal type 16/17 branch"),
    ("helper_b370", 0xB370, 0xB550, "called from 0x9ff4; final helper before v4 wrapper area"),
]


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def tool_env() -> dict[str, str] | None:
    relib = ROOT / "tmp/relibs"
    if not relib.exists():
        return None
    env = dict(os.environ)
    existing = env.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = str(relib) if not existing else f"{relib}:{existing}"
    return env


def parse_instructions(disassembly: str) -> list[dict[str, Any]]:
    instructions: list[dict[str, Any]] = []
    for raw_line in disassembly.splitlines():
        match = INSTRUCTION_RE.match(raw_line)
        if not match:
            continue
        instructions.append(
            {
                "addr": int(match.group(1), 16),
                "instruction": match.group(2).strip(),
                "raw": raw_line.strip(),
            }
        )
    return instructions


def helper_range_for(addr: int) -> dict[str, Any]:
    for name, start, stop, description in HELPER_RANGES:
        if start <= addr < stop:
            return {"name": name, "start": start, "stop": stop, "description": description}
    return {"name": "unknown", "start": None, "stop": None, "description": "outside scanned helper ranges"}


def literal_registers(context: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    registers: dict[str, dict[str, int]] = {}
    for row in context:
        match = MOV_RE.search(row["instruction"])
        if not match:
            continue
        kind, register, value_text = match.groups()
        value = int(value_text)
        state = registers.setdefault(register, {})
        if kind == "w":
            state["movw"] = value
        elif kind == "t":
            state["movt"] = value
        else:
            state["movs"] = value
    return registers


def combined_literal(register_state: dict[str, int]) -> int | None:
    if "movw" in register_state:
        return int(register_state["movw"]) | (int(register_state.get("movt", 0)) << 16)
    if "movs" in register_state:
        return int(register_state["movs"])
    return None


def stack_out_len(context: list[dict[str, Any]], registers: dict[str, dict[str, int]]) -> int | None:
    del registers
    live_registers: dict[str, dict[str, int]] = {}
    last_value: int | None = None
    for row in context:
        mov_match = MOV_RE.search(row["instruction"])
        if mov_match:
            kind, register, value_text = mov_match.groups()
            state = live_registers.setdefault(register, {})
            value = int(value_text)
            if kind == "w":
                state["movw"] = value
                state.pop("movs", None)
            elif kind == "t":
                state["movt"] = value
                state.pop("movs", None)
            else:
                state.clear()
                state["movs"] = value
        str_match = STR_STACK_RE.search(row["instruction"])
        if str_match:
            last_value = combined_literal(live_registers.get(str_match.group(1), {}))
        strd_match = STREQ_STACK_RE.search(row["instruction"])
        if strd_match:
            last_value = combined_literal(live_registers.get(strd_match.group(1), {}))
    return last_value


def immediate_r2(context: list[dict[str, Any]], registers: dict[str, dict[str, int]]) -> int | None:
    return combined_literal(registers.get("r2", {}))


def command_source(context: list[dict[str, Any]], registers: dict[str, dict[str, int]], import_symbol: str) -> dict[str, Any]:
    if import_symbol == "ioctl":
        request = combined_literal(registers.get("r1", {}))
        return {
            "kind": "literal" if request is not None else "unknown",
            "value": request,
            "register": "r1",
            "meaning": "AUDIO_SET_CALIBRATION" if request == AUDIO_SET_CALIBRATION else None,
        }
    command = combined_literal(registers.get("r0", {}))
    if command is not None and command > 0x10000:
        return {"kind": "literal", "value": command, "register": "r0", "meaning": "acdb command literal"}
    if any(LDR_TABLE_RE.search(row["instruction"]) for row in context):
        return {"kind": "table_lookup", "value": None, "register": "r0", "meaning": "command loaded from r1[index] table"}
    return {"kind": "unknown", "value": None, "register": "r0", "meaning": None}


def summarize_call(call: dict[str, Any], instructions: list[dict[str, Any]]) -> dict[str, Any]:
    call_addr = int(str(call["call_addr"]), 16)
    context = [row for row in instructions if call_addr - 0x40 <= row["addr"] <= call_addr]
    registers = literal_registers(context)
    source = command_source(context, registers, str(call.get("import_symbol")))
    helper = helper_range_for(call_addr)
    return {
        "helper": helper["name"],
        "helper_description": helper["description"],
        "call_addr": call["call_addr"],
        "import_symbol": call.get("import_symbol"),
        "dest": call.get("dest"),
        "command_source": source["kind"],
        "command_hex": f"0x{source['value']:08x}" if source["value"] is not None else None,
        "command_meaning": source.get("meaning"),
        "in_len": immediate_r2(context, registers) if call.get("import_symbol") == "acdb_ioctl" else None,
        "out_len": stack_out_len(context, registers) if call.get("import_symbol") == "acdb_ioctl" else None,
        "ioctl_request_hex": f"0x{source['value']:08x}" if call.get("import_symbol") == "ioctl" and source["value"] is not None else None,
        "is_audio_set_calibration": bool(call.get("import_symbol") == "ioctl" and source["value"] == AUDIO_SET_CALIBRATION),
        "context_tail": [row["raw"] for row in context[-12:]],
    }


def load_v2597_result(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    word_match = REPORT_VALUE_RE.search(text)
    decision_match = REPORT_DECISION_RE.search(text)
    return {
        "report": rel(path),
        "exists": path.exists(),
        "decision": decision_match.group(1) if decision_match else None,
        "out_word_hex": word_match.group(1).lower() if word_match else None,
        "out_word_matches_expected": bool(word_match and int(word_match.group(1), 16) == EXPECTED_DIRECT_WORD),
    }


def make_payload(args: argparse.Namespace) -> dict[str, Any]:
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    env = tool_env()
    if not args.lib.exists():
        return {"ok": False, "error": f"missing private lib: {rel(args.lib)}"}

    reloc = v2594.run([str(args.readelf), "-r", str(args.lib)], env=env)
    symbols = v2594.run([str(args.readelf), "-Ws", str(args.lib)], env=env)
    plt_dis = v2594.run([str(args.objdump), "-d", "--section=.plt", str(args.lib)], env=env)
    func_dis = v2594.run(
        [
            str(args.objdump),
            "-d",
            "--triple=thumbv7-linux-android",
            f"--start-address=0x{SEND_AUDIO_CAL_START:x}",
            f"--stop-address=0x{POST_PREGET_STOP:x}",
            str(args.lib),
        ],
        env=env,
    )
    for name, result in {"relocations": reloc, "symbols": symbols, "plt": plt_dis, "post_preget_function": func_dis}.items():
        (out_dir / f"{name}.stdout.txt").write_text(result["stdout"], encoding="utf-8", errors="replace")
        (out_dir / f"{name}.stderr.txt").write_text(result["stderr"], encoding="utf-8", errors="replace")

    tool_ok = all(result["ok"] for result in (reloc, symbols, plt_dis, func_dis))
    if not tool_ok:
        return {
            "ok": False,
            "decision": "v2599-tool-failure",
            "tool_results": {"relocations": reloc["rc"], "symbols": symbols["rc"], "plt": plt_dis["rc"], "function": func_dis["rc"]},
        }

    plt = v2594.map_plt(reloc["stdout"], plt_dis["stdout"])
    parsed_symbols = v2594.parse_symbols(symbols["stdout"])
    calls = v2594.parse_calls(func_dis["stdout"], plt, parsed_symbols)
    instructions = parse_instructions(func_dis["stdout"])
    imported_rows = [
        summarize_call(call, instructions)
        for call in calls
        if call.get("import_symbol") in {"acdb_ioctl", "ioctl"}
    ]
    acdb_rows = [row for row in imported_rows if row["import_symbol"] == "acdb_ioctl"]
    set_rows = [row for row in imported_rows if row["is_audio_set_calibration"]]
    literal_acdb = [row for row in acdb_rows if row["command_source"] == "literal"]
    table_acdb = [row for row in acdb_rows if row["command_source"] == "table_lookup"]
    v2597_result = load_v2597_result(args.v2597_report)

    required_literals = {"0x0001122e", "0x0001122d", "0x000130d8", "0x00012eeb"}
    seen_literals = {str(row["command_hex"]) for row in literal_acdb}
    visible_acdb_out_lens = sorted({row.get("out_len") for row in acdb_rows if row.get("out_len") is not None})
    decision = "v2599-post-preget-downstream-map-extracted"
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": decision,
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "private_inputs": {
            "libacdbloader": rel(args.lib),
            "scratch": rel(out_dir),
            "v2594_json": rel(args.v2594_json),
        },
        "v2597_live_metadata": v2597_result,
        "scan_range": [f"0x{SEND_AUDIO_CAL_START:x}", f"0x{POST_PREGET_STOP:x}"],
        "acdb_ioctl_rows": acdb_rows,
        "audio_set_rows": set_rows,
        "summary": {
            "acdb_row_count": len(acdb_rows),
            "literal_acdb_commands": sorted(seen_literals),
            "table_backed_acdb_rows": len(table_acdb),
            "audio_set_calibration_rows": len(set_rows),
            "visible_acdb_out_lens": visible_acdb_out_lens,
            "required_literal_commands_present": sorted(required_literals & seen_literals),
            "required_literal_commands_missing": sorted(required_literals - seen_literals),
            "all_visible_acdb_rows_are_4byte_metadata": visible_acdb_out_lens == [4],
        },
        "interpretation": {
            "direct_metadata_word_usage": "V2597's 0x10005000 output is consumed as metadata and copied into the fake-guarded SET-side cal block, not itself a captured cal payload.",
            "send_path_payload_visibility": "The visible send_audio_cal_v5 downstream ACDB dispatcher rows in this range are 4-byte metadata/size rows; full per-device bytes are not exposed as direct out_buf payloads here.",
            "next_recommended_unit": "Build a direct lower-getter matrix or import-call tracer that logs request structs/indirect buffers for the table-backed and literal rows; do not rerun post-init topology arm or another send_audio_cal_v5 argument variant.",
        },
        "boundary": {
            "no_live": True,
            "no_acdb_execution": True,
            "no_audio_set_replay": True,
            "raw_disassembly_private_only": True,
        },
    }
    payload["ok"] = bool(
        v2597_result["out_word_matches_expected"]
        and not payload["summary"]["required_literal_commands_missing"]
        and len(set_rows) >= 1
        and payload["summary"]["all_visible_acdb_rows_are_4byte_metadata"]
    )
    (out_dir / "v2599-post-preget-geometry.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload.get("summary", {})
    rows = payload.get("acdb_ioctl_rows", [])
    set_rows = payload.get("audio_set_rows", [])
    lines = [
        "# NATIVE_INIT V2599 — ACDB post-preGET downstream geometry RE",
        "",
        "Date: 2026-06-16",
        "",
        "## Scope",
        "",
        "Host-only follow-up after V2597. No Android handoff, native replay `SET`, speaker write,",
        "ACDB command execution, or raw payload publication was performed. Proprietary disassembly",
        f"and JSON scratch stay private under `{payload.get('private_inputs', {}).get('scratch')}`.",
        "",
        "## Decision",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- ok: `{payload.get('ok')}`",
        f"- V2597 live metadata: `{payload.get('v2597_live_metadata', {}).get('out_word_hex')}`",
        f"- ACDB dispatcher rows scanned: `{summary.get('acdb_row_count')}`",
        f"- literal ACDB commands: `{summary.get('literal_acdb_commands')}`",
        f"- table-backed ACDB rows: `{summary.get('table_backed_acdb_rows')}`",
        f"- fake-guarded `AUDIO_SET_CALIBRATION` rows: `{summary.get('audio_set_calibration_rows')}`",
        "",
        "## Downstream ACDB Rows",
        "",
        "| helper | call | command | source | in_len | out_len | note |",
        "| --- | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        command = row.get("command_hex") or "table/unknown"
        note = row.get("helper_description") or ""
        lines.append(
            f"| `{row.get('helper')}` | `{row.get('call_addr')}` | `{command}` | "
            f"{row.get('command_source')} | `{row.get('in_len')}` | `{row.get('out_len')}` | {note} |"
        )
    lines.extend(
        [
            "",
            "## SET-Side Rows",
            "",
            "The success path after the first metadata row prepares fake-guarded `AUDIO_SET_CALIBRATION`",
            "ioctls. These are useful for understanding control flow, but they are not acceptable as",
            "native replay payload capture and remain guarded by the fake-allocation preload in live helpers.",
            "",
            "| helper | call | request |",
            "| --- | ---: | ---: |",
        ]
    )
    for row in set_rows:
        lines.append(f"| `{row.get('helper')}` | `{row.get('call_addr')}` | `{row.get('ioctl_request_hex')}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- V2597's `0x10005000` return from `acdb_ioctl(0x1122e, &0x11135, 4, out, 4)` is",
            "  consumed as metadata and copied into the SET-side cal-block structure. It is not a",
            "  per-device payload by itself.",
            "- Every visible downstream `acdb_ioctl` row in the scanned send path has `out_len=4`.",
            "  Therefore an `out_buf`-only ACDB tap will not recover full AFE/ASM/ADM/VOL bytes from",
            "  this send path; the bytes are behind indirect request/output structures or lower getter APIs.",
            "- The table-backed command rows are important: they prevent hard-coding a fixed command list",
            "  without also resolving the command table index selected at runtime.",
            "",
            "## Next Unit",
            "",
            "Do not repeat the post-init topology arm path or another `send_audio_cal_v5` argument variant.",
            "The next high-signal unit should be build-only: construct a bounded direct lower-getter matrix",
            "or import-call tracer that logs the request structs/indirect output pointers for the literal and",
            "table-backed rows above. Live execution remains blocked until that helper has a no-SET contract,",
            "zero-buffer checks, and a separate rollbackable Android handoff gate.",
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_post_preget_geometry_recon_v2599.py tests/test_native_audio_acdb_post_preget_geometry_recon_v2599.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_post_preget_geometry_recon_v2599`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_post_preget_geometry_recon_v2599.py --write-report`",
            "- `git diff --check`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lib", type=Path, default=DEFAULT_LIB)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--v2594-json", type=Path, default=DEFAULT_V2594_JSON)
    parser.add_argument("--v2597-report", type=Path, default=DEFAULT_V2597_REPORT)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_LLVM_OBJDUMP)
    parser.add_argument("--readelf", type=Path, default=DEFAULT_LLVM_READELF)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = make_payload(args)
    if args.write_report:
        write_report(args.report_path, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
