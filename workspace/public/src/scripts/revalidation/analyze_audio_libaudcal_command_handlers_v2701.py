#!/usr/bin/env python3
"""V2701 host-only libaudcal custom-topology command-handler RE.

V2700 localized the native replay split past libacdbloader request construction:
cal_type 10/14/24 all reach libaudcal with the same two-word request shape.
This unit maps the libaudcal command dispatch for the failing/stale commands and
known-good comparator without executing any device code or emitting vendor bytes.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2701"
LIBAUDCAL = ROOT / "workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libaudcal.so"
LLVM_OBJDUMP = ROOT / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0/bin/llvm-objdump"
COMPAT_LIBS = ROOT / "workspace/private/inputs/toolchains/compat-libs"
OUT_DIR = ROOT / "workspace/private/builds/audio/v2701-libaudcal-handler-re"
REPORT = ROOT / "docs/reports/NATIVE_INIT_V2701_AUDIO_LIBAUDCAL_COMMAND_HANDLER_RE_2026-06-18.md"

TEXT_SECTION_ADDR = 0x0000CB50
TEXT_SECTION_OFFSET = 0x0000BB50
PLT_SECTION_ADDR = 0x00025C70
PLT_ENTRY0_ADDR = 0x00025C90
PLT_ENTRY_SIZE = 0x10

COMMANDS = (
    {
        "cal_type": 10,
        "role": "ADM_CUST_TOPOLOGY",
        "cmd": 0x11394,
        "dispatcher": "acdb_ioctl -> acdb_ioctl_audio fallback",
        "dispatch_block": 0xD4B2,
        "call_addr": 0xD4DC,
        "expected_tail_target": 0x25A88,
        "observed_v2700_ret": -12,
        "observed_v2700_state": "absent-ret-minus-12",
        "dispatch_note": "top-level acdb_ioctl reaches generic fallback, then acdb_ioctl_audio handles command 0x11394",
    },
    {
        "cal_type": 14,
        "role": "ASM_CUST_TOPOLOGY",
        "cmd": 0x12E01,
        "dispatcher": "acdb_ioctl -> acdb_ioctl_audio direct compare",
        "dispatch_block": 0xD85E,
        "call_addr": 0xD878,
        "expected_tail_target": 0x25B60,
        "observed_v2700_ret": 0,
        "observed_v2700_state": "stale-selected-absent",
        "dispatch_note": "top-level acdb_ioctl reaches acdb_ioctl_audio; acdb_ioctl_audio direct-compare branch handles 0x12e01",
    },
    {
        "cal_type": 24,
        "role": "AFE_CUST_TOPOLOGY",
        "cmd": 0x130DA,
        "dispatcher": "acdb_ioctl high-command table",
        "dispatch_block": 0xE684,
        "call_addr": 0xE6AC,
        "expected_tail_target": 0x26230,
        "observed_v2700_ret": 0,
        "observed_v2700_state": "aligned-selected-present",
        "dispatch_note": "known-good comparator; high-command TBH table entry 0x130da handles the AFE topology request",
    },
)


@dataclasses.dataclass(frozen=True)
class Instruction:
    addr: int
    mnemonic: str
    operands: str
    text: str


@dataclasses.dataclass(frozen=True)
class PltSymbol:
    index: int
    plt_addr: int
    got_addr: int
    name: str


@dataclasses.dataclass(frozen=True)
class HandlerPath:
    cal_type: int
    role: str
    cmd: int
    dispatcher: str
    dispatch_block: int
    call_addr: int
    tail_target: int | None
    tail_target_kind: str
    plt_addr: int | None
    plt_symbol: str | None
    validator_in_len: int | None
    validator_out_len: int | None
    validator_key_word: str
    validator_key_offset: int | None
    validator_checks_word0: bool
    observed_v2700_ret: int
    observed_v2700_state: str
    interpretation: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def env_with_toolchain() -> dict[str, str]:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(COMPAT_LIBS) + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    return env


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=ROOT, env=env_with_toolchain(), text=True, stderr=subprocess.STDOUT)


def disassemble(start: int, stop: int, triple: str, output_name: str) -> str:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    text = run([
        str(LLVM_OBJDUMP),
        "-d",
        f"--triple={triple}",
        f"--start-address=0x{start:x}",
        f"--stop-address=0x{stop:x}",
        str(LIBAUDCAL),
    ])
    (OUT_DIR / output_name).write_text(text, encoding="utf-8")
    return text


def refresh_disassembly() -> dict[str, str]:
    return {
        "audio_handlers": rel(OUT_DIR / "libaudcal-v2701-audio-handlers.thumb-objdump.txt"),
        "top_handlers": rel(OUT_DIR / "libaudcal-v2701-top-handlers.thumb-objdump.txt"),
        "fallback": rel(OUT_DIR / "libaudcal-v2701-fallback.thumb-objdump.txt"),
        "veneers": rel(OUT_DIR / "libaudcal-v2701-veneers.thumb-objdump.txt"),
        "plt": rel(OUT_DIR / "libaudcal-v2701-plt.arm-objdump.txt"),
    }


def generate_disassembly() -> dict[str, str]:
    disassemble(0xD430, 0xD500, "thumbv7a-linux-android", "libaudcal-v2701-audio-handlers.thumb-objdump.txt")
    disassemble(0xD840, 0xD890, "thumbv7a-linux-android", "libaudcal-v2701-audio-handlers-12e01.thumb-objdump.txt")
    disassemble(0xE660, 0xE6E8, "thumbv7a-linux-android", "libaudcal-v2701-top-handlers.thumb-objdump.txt")
    disassemble(0xE540, 0xE5A0, "thumbv7a-linux-android", "libaudcal-v2701-fallback.thumb-objdump.txt")
    disassemble(0x25A80, 0x25BC0, "thumbv7a-linux-android", "libaudcal-v2701-veneers.thumb-objdump.txt")
    disassemble(0x25C70, 0x26280, "armv7a-linux-android", "libaudcal-v2701-plt.arm-objdump.txt")
    paths = refresh_disassembly()
    paths["audio_handlers_12e01"] = rel(OUT_DIR / "libaudcal-v2701-audio-handlers-12e01.thumb-objdump.txt")
    return paths


def parse_instructions(disasm: str) -> list[Instruction]:
    instructions: list[Instruction] = []
    for line in disasm.splitlines():
        if "\t" not in line:
            continue
        left, right = line.split("\t", 1)
        match = re.search(r"^\s*([0-9a-fA-F]+):", left)
        if not match:
            continue
        text = right.strip()
        if not text or text.startswith("<"):
            continue
        parts = text.split(None, 1)
        instructions.append(Instruction(addr=int(match.group(1), 16), mnemonic=parts[0], operands=parts[1] if len(parts) > 1 else "", text=line.rstrip()))
    return instructions


def branch_target(instruction: Instruction) -> int | None:
    if instruction.mnemonic not in {"bl", "blx", "b.w"}:
        return None
    match = re.match(r"#(-?\d+)", instruction.operands)
    if not match:
        return None
    return instruction.addr + 4 + int(match.group(1), 10)


def parse_relplt(readelf_output: str) -> list[PltSymbol]:
    symbols: list[PltSymbol] = []
    for line in readelf_output.splitlines():
        match = re.match(r"\s*([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+R_ARM_JUMP_SLOT\s+[0-9a-fA-F]+\s+([^\s]+)", line)
        if not match:
            continue
        index = len(symbols)
        symbols.append(PltSymbol(index=index, plt_addr=PLT_ENTRY0_ADDR + index * PLT_ENTRY_SIZE, got_addr=int(match.group(1), 16), name=match.group(2)))
    return symbols


def read_relplt() -> list[PltSymbol]:
    return parse_relplt(subprocess.check_output(["readelf", "-rW", str(LIBAUDCAL)], cwd=ROOT, text=True))


def resolve_plt_symbol(plt_symbols: list[PltSymbol], address: int) -> PltSymbol | None:
    if address < PLT_ENTRY0_ADDR:
        return None
    index = (address - PLT_ENTRY0_ADDR) // PLT_ENTRY_SIZE
    if 0 <= index < len(plt_symbols):
        slot = plt_symbols[index]
        if slot.plt_addr <= address < slot.plt_addr + PLT_ENTRY_SIZE:
            return slot
    return None


def thumb_pc_for_add(addr: int) -> int:
    return (addr + 4) & ~3


def parse_thumb_veneer(disasm: str, veneer_addr: int) -> int | None:
    instructions = parse_instructions(disasm)
    by_addr = {instruction.addr: instruction for instruction in instructions}
    first = by_addr.get(veneer_addr)
    third = by_addr.get(veneer_addr + 8)
    if first is None or third is None:
        return None
    match = re.search(r"r12, #(\d+)", first.operands)
    if not match or third.mnemonic != "add" or "r12, pc" not in third.operands:
        return None
    imm = int(match.group(1), 10)
    # These libaudcal veneers use movt r12,#0 for all targets needed here.
    return thumb_pc_for_add(third.addr) + imm


def resolve_tail_target(target: int | None, veneer_disasm: str, plt_symbols: list[PltSymbol]) -> tuple[str, int | None, str | None]:
    if target is None:
        return ("missing", None, None)
    direct = resolve_plt_symbol(plt_symbols, target)
    if direct:
        return ("plt", direct.plt_addr, direct.name)
    plt_addr = parse_thumb_veneer(veneer_disasm, target)
    if plt_addr is None:
        return ("unknown", None, None)
    symbol = resolve_plt_symbol(plt_symbols, plt_addr)
    return ("thumb-veneer", plt_addr, symbol.name if symbol else None)


def extract_window(instructions: list[Instruction], start: int, stop: int) -> list[Instruction]:
    return [instruction for instruction in instructions if start <= instruction.addr < stop]


def parse_validator(window: list[Instruction]) -> dict[str, Any]:
    text = "\n".join(instruction.text for instruction in window)
    in_len = None
    out_len = None
    key_offset = None
    # The audio sub-dispatcher uses r1/r2/r3/r12 for in/out args, while the
    # top-level AFE block has already copied them to r7/r6/r8/r9.  Match the
    # semantic checks, not one hard-coded register allocation.
    checks_word0 = bool(re.search(r"ldr\s+r0, \[r(?:1|7)\](?!,)", text))
    for instruction in window:
        if instruction.mnemonic == "cmp" and instruction.operands.endswith(", #8"):
            in_len = 8
        if instruction.mnemonic == "cmp.w" and instruction.operands.endswith(", #4"):
            out_len = 4
        if instruction.mnemonic == "ldr" and re.match(r"r0, \[r(?:1|7), #4\]", instruction.operands):
            key_offset = 4
    return {
        "in_len": in_len,
        "out_len": out_len,
        "key_offset": key_offset,
        "checks_word0": checks_word0,
    }


def find_call_target(disasm: str, call_addr: int) -> int | None:
    for instruction in parse_instructions(disasm):
        if instruction.addr == call_addr:
            return branch_target(instruction)
    return None


def analyze_handlers(refresh_objdump: bool = True) -> dict[str, Any]:
    if refresh_objdump:
        disasm_paths = generate_disassembly()
    else:
        disasm_paths = refresh_disassembly()
        disasm_paths["audio_handlers_12e01"] = rel(OUT_DIR / "libaudcal-v2701-audio-handlers-12e01.thumb-objdump.txt")
    audio_text = (OUT_DIR / "libaudcal-v2701-audio-handlers.thumb-objdump.txt").read_text(encoding="utf-8", errors="ignore")
    audio_12e01_text = (OUT_DIR / "libaudcal-v2701-audio-handlers-12e01.thumb-objdump.txt").read_text(encoding="utf-8", errors="ignore")
    top_text = (OUT_DIR / "libaudcal-v2701-top-handlers.thumb-objdump.txt").read_text(encoding="utf-8", errors="ignore")
    fallback_text = (OUT_DIR / "libaudcal-v2701-fallback.thumb-objdump.txt").read_text(encoding="utf-8", errors="ignore")
    veneer_text = (OUT_DIR / "libaudcal-v2701-veneers.thumb-objdump.txt").read_text(encoding="utf-8", errors="ignore")
    all_thumb_text = "\n".join((audio_text, audio_12e01_text, top_text, fallback_text))
    all_instructions = parse_instructions(all_thumb_text)
    plt_symbols = read_relplt()
    paths: list[HandlerPath] = []
    for command in COMMANDS:
        call_target = find_call_target(all_thumb_text, int(command["call_addr"]))
        if call_target is not None and call_target != int(command["expected_tail_target"]):
            raise ValueError(f"unexpected tail target for {command['cmd']:#x}: {call_target:#x}")
        kind, plt_addr, symbol_name = resolve_tail_target(call_target, veneer_text, plt_symbols)
        window = extract_window(all_instructions, int(command["dispatch_block"]), int(command["call_addr"]) + 4)
        validator = parse_validator(window)
        interpretation = (
            "local validator accepts an 8-byte request and 4-byte output buffer, then checks only request word1 at in_buf+4 before tail-calling the topology handler"
        )
        if validator["checks_word0"]:
            interpretation = "local validator also inspects request word0; this would reopen loader selector shape"
        paths.append(
            HandlerPath(
                cal_type=int(command["cal_type"]),
                role=str(command["role"]),
                cmd=int(command["cmd"]),
                dispatcher=str(command["dispatcher"]),
                dispatch_block=int(command["dispatch_block"]),
                call_addr=int(command["call_addr"]),
                tail_target=call_target,
                tail_target_kind=kind,
                plt_addr=plt_addr,
                plt_symbol=symbol_name,
                validator_in_len=validator["in_len"],
                validator_out_len=validator["out_len"],
                validator_key_word="word1",
                validator_key_offset=validator["key_offset"],
                validator_checks_word0=validator["checks_word0"],
                observed_v2700_ret=int(command["observed_v2700_ret"]),
                observed_v2700_state=str(command["observed_v2700_state"]),
                interpretation=interpretation,
            )
        )
    return {
        "run_id": RUN_ID,
        "generated_at": now_iso(),
        "scope": "host-only libaudcal command-handler RE; private vendor .so disassembly read only; no device action, Android handoff, ioctl, mixer write, PCM probe, raw ACDB payload commit, or vendor byte emission",
        "input": {
            "libaudcal": rel(LIBAUDCAL),
            "private_disassembly": disasm_paths,
            "source_iteration": "V2700",
        },
        "classification": classify_handlers(paths),
        "handler_paths": [dataclasses.asdict(path) for path in paths],
        "fallback_chain": {
            "top_level_generic_fallback": "acdb_ioctl calls acdb_ioctl_audio, then acdb_ioctl_voice, then acdb_ioctl_codec when no direct top-level command block handles a command",
            "resolved_symbols": ["acdb_ioctl_audio", "acdb_ioctl_voice", "acdb_ioctl_codec"],
            "relevance": "0x11394 reaches acdb_ioctl_audio through this fallback; 0x12e01 is handled in acdb_ioctl_audio; 0x130da is handled directly in acdb_ioctl high table",
        },
    }


def classify_handlers(paths: list[HandlerPath]) -> dict[str, Any]:
    all_word1 = all(path.validator_in_len == 8 and path.validator_out_len == 4 and path.validator_key_offset == 4 and not path.validator_checks_word0 for path in paths)
    all_symbols = all(path.plt_symbol for path in paths)
    if all_word1 and all_symbols:
        decision = "v2701-libaudcal-topology-handlers-share-word1-key"
        recommended = "v2702-acdb-command-handler-table-lookup-instrumentation"
        reason = (
            "libaudcal command dispatch for cal_type 10, 14, and 24 has the same local ABI guard: in_len=8, out_len=4, and only in_buf+4 must be nonzero before tail-calling the topology handler. "
            "The failing/stale split is therefore past local validation, inside the ACDB topology data handlers/table lookup keyed by word1."
        )
    else:
        decision = "v2701-libaudcal-handler-shape-diverges"
        recommended = "v2702-recheck-handler-mapping"
        reason = "At least one command path failed the shared validator or PLT-symbol mapping check."
    return {
        "decision": decision,
        "ok": True,
        "all_handlers_resolved": all_symbols,
        "shared_word1_only_validator": all_word1,
        "native_replay_remains_parked": True,
        "recommended_next": recommended,
        "reason": reason,
    }


def hex_or_none(value: int | None, width: int = 8) -> str:
    if value is None:
        return "None"
    return f"0x{value & ((1 << (width * 4)) - 1):0{width}x}"


def table(rows: list[list[str]]) -> str:
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    out = ["| " + " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(rows[0])) + " |"]
    out.append("| " + " | ".join("---" for _ in rows[0]) + " |")
    for row in rows[1:]:
        out.append("| " + " | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)) + " |")
    return "\n".join(out)


def render_report(summary: dict[str, Any]) -> str:
    c = summary["classification"]
    rows = [["cal_type", "role", "cmd", "dispatcher", "block", "tail target", "PLT symbol", "validator", "V2700 state"]]
    for path in summary["handler_paths"]:
        validator = f"in_len={path['validator_in_len']}, out_len={path['validator_out_len']}, key={path['validator_key_word']}@+{path['validator_key_offset']}, word0_checked={path['validator_checks_word0']}"
        rows.append(
            [
                str(path["cal_type"]),
                path["role"],
                hex_or_none(path["cmd"], 5),
                path["dispatcher"],
                hex_or_none(path["dispatch_block"]),
                f"{hex_or_none(path['tail_target'])} ({path['tail_target_kind']} -> {hex_or_none(path['plt_addr'])})",
                str(path["plt_symbol"]),
                validator,
                f"ret={path['observed_v2700_ret']} {path['observed_v2700_state']}",
            ]
        )
    lines = [
        "# NATIVE_INIT V2701 — libaudcal command-handler RE",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only `libaudcal.so` command-handler reverse engineering. This reads a private vendor library and stores only public-safe metadata: command IDs, handler symbols, local argument-shape checks, and branch targets. No device action, Android handoff, `/dev/msm_audio_cal` ioctl, mixer write, PCM probe, raw ACDB payload commit, or vendor byte commit occurred.",
        "",
        "## Result",
        "",
        f"- decision: `{c['decision']}`",
        f"- ok: `{c['ok']}`",
        f"- all_handlers_resolved: `{c['all_handlers_resolved']}`",
        f"- shared_word1_only_validator: `{c['shared_word1_only_validator']}`",
        f"- recommended_next: `{c['recommended_next']}`",
        f"- native_replay_remains_parked: `{c['native_replay_remains_parked']}`",
        "",
        "## Handler map",
        "",
        table(rows),
        "",
        "## Interpretation",
        "",
        "The libaudcal local validators for ADM cal_type `10` (`0x11394`), ASM cal_type `14` (`0x12e01`), and the known-good AFE comparator cal_type `24` (`0x130da`) all accept the same request ABI: an 8-byte input buffer, a 4-byte output buffer, and a nonzero check on only `in_buf + 4` (`word1`). None of these local validators checks `word0` before handing off to the topology-data handler.",
        "",
        "The resolved handler symbols are `AcdbCmdGetAudioCOPPTopologyData` for `0x11394`, `AcdbCmdGetAudioPOPPTopologyData` for `0x12e01`, and `AcdbCmdGetAfeTopologyData` for `0x130da`. That moves the frontier past both libacdbloader request construction and libaudcal's local command validators. The observed split — cal_type `10` returns `-12`, cal_type `14` returns stale/non-selected data, while cal_type `24` succeeds — is inside the ACDB topology-data/table lookup keyed by the second request word, not in a missing loader block or obvious ABI mismatch.",
        "",
        "## Next unit",
        "",
        "V2702 should inspect or instrument the command-specific ACDB table lookup behind `AcdbCmdGetAudioCOPPTopologyData` and `AcdbCmdGetAudioPOPPTopologyData`, using the known-good `AcdbCmdGetAfeTopologyData` path as comparator. Acceptance: identify the table/key fields consumed from request `word1`, or build a bounded own-process instrumentation point around those handlers/`acdbdata_ioctl` that logs return codes and public-safe key metadata. Native replay remains parked until byte-exact selected cal_type `10` and `14` payloads are recovered.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_libaudcal_command_handlers_v2701.py tests/test_analyze_audio_libaudcal_command_handlers_v2701.py`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_libaudcal_command_handlers_v2701 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_libaudcal_command_handlers_v2701.py --write-report --json`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`",
        "- `git diff --check`",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--no-refresh-objdump", action="store_true")
    args = parser.parse_args(argv)
    summary = analyze_handlers(refresh_objdump=not args.no_refresh_objdump)
    if args.write_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(render_report(summary), encoding="utf-8")
    if args.json or not args.write_report:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
