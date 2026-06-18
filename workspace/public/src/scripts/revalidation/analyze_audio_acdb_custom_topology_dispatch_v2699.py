#!/usr/bin/env python3
"""V2699 host-only RE of libacdbloader custom-topology dispatch blocks.

This script disassembles the private stock 32-bit libacdbloader into
workspace/private, then extracts only public-safe metadata:
which ACDB GET command constants are assembled inside
acdb_loader_send_common_custom_topology(), which cal_type block each command
belongs to, and what that means after V2695-V2698.
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
RUN_ID = "V2699"
REPORT = ROOT / "docs/reports/NATIVE_INIT_V2699_AUDIO_ACDB_CUSTOM_TOPOLOGY_DISPATCH_RE_2026-06-18.md"

LIBACDBLOADER = ROOT / "workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libacdbloader.so"
OBJDUMP = ROOT / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0/bin/llvm-objdump"
COMPAT_LIBS = ROOT / "workspace/private/inputs/toolchains/compat-libs"
WORK_DIR = ROOT / "workspace/private/builds/audio/v2699-custom-topology-dispatch"
COMMON_DISASM = WORK_DIR / "libacdbloader-send-common-custom-topology.thumb-objdump.txt"

COMMON_TOPOLOGY_START = 0x8CF0
COMMON_TOPOLOGY_END = 0x9730

CUSTOM_BLOCKS = {
    24: {
        "role": "AFE_CUST_TOPOLOGY",
        "start": 0x90EA,
        "end": 0x924A,
        "expected_cmds": {0x130DA, 0x130DC},
        "selected_topology": 0x1001025D,
        "latest_payload_state": "aligned-selected-present",
    },
    10: {
        "role": "ADM_CUST_TOPOLOGY",
        "start": 0x924A,
        "end": 0x93F6,
        "expected_cmds": {0x11394},
        "selected_topology": 0x10004000,
        "latest_payload_state": "absent-ret-minus-12",
    },
    14: {
        "role": "ASM_CUST_TOPOLOGY",
        "start": 0x93F6,
        "end": 0x9524,
        "expected_cmds": {0x12E01},
        "selected_topology": 0x10005000,
        "latest_payload_state": "stale-selected-absent",
    },
    25: {
        "role": "LEGACY_OR_ALT_AFE_CUSTOM_TOPOLOGY",
        "start": 0x9524,
        "end": COMMON_TOPOLOGY_END,
        "expected_cmds": {0x130DA, 0x130DC},
        "selected_topology": None,
        "latest_payload_state": "not-targeted",
    },
}

CMD_NAMES = {
    0x11394: "ACDB_CMD_GET_ADM_CUSTOM_TOPOLOGY",
    0x12E01: "ACDB_CMD_GET_ASM_CUSTOM_TOPOLOGY",
    0x130DA: "ACDB_CMD_GET_AFE_CUSTOM_TOPOLOGY",
    0x130DC: "ACDB_CMD_GET_AFE_CUSTOM_TOPOLOGY_ALT",
    0x13296: "ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_V3",
}


@dataclasses.dataclass(frozen=True)
class MovPair:
    addr: int
    reg: str
    value: int
    low: int
    high: int


@dataclasses.dataclass(frozen=True)
class BlockCommand:
    cal_type: int
    role: str
    addr: int
    cmd: int
    cmd_name: str
    selected_topology: int | None
    latest_payload_state: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def run_objdump() -> None:
    if not LIBACDBLOADER.exists():
        raise FileNotFoundError(LIBACDBLOADER)
    if not OBJDUMP.exists():
        raise FileNotFoundError(OBJDUMP)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = f"{COMPAT_LIBS}:{env.get('LD_LIBRARY_PATH', '')}"
    proc = subprocess.run(
        [
            str(OBJDUMP),
            "-d",
            "--triple=thumbv7-none-linux-androideabi",
            f"--start-address=0x{COMMON_TOPOLOGY_START:x}",
            f"--stop-address=0x{COMMON_TOPOLOGY_END:x}",
            str(LIBACDBLOADER),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    COMMON_DISASM.write_text(proc.stdout, encoding="utf-8")
    COMMON_DISASM.chmod(0o600)


MOVW_RE = re.compile(r"^\s*([0-9a-fA-F]+):.*\bmovw(?:\.\w+)?\s+([a-z0-9]+),\s*#(\d+)")
MOVT_RE = re.compile(r"^\s*([0-9a-fA-F]+):.*\bmovt(?:\.\w+)?\s+([a-z0-9]+),\s*#(\d+)")


def parse_movw_movt_pairs(disasm: str) -> list[MovPair]:
    lines = disasm.splitlines()
    pairs: list[MovPair] = []
    for index, line in enumerate(lines):
        low_match = MOVW_RE.search(line)
        if not low_match:
            continue
        addr = int(low_match.group(1), 16)
        reg = low_match.group(2)
        low = int(low_match.group(3), 10)
        for lookahead in lines[index + 1 : index + 5]:
            high_match = MOVT_RE.search(lookahead)
            if not high_match or high_match.group(2) != reg:
                continue
            high = int(high_match.group(3), 10)
            pairs.append(MovPair(addr=addr, reg=reg, value=((high & 0xFFFF) << 16) | (low & 0xFFFF), low=low, high=high))
            break
    return pairs


def block_for_addr(addr: int) -> tuple[int, dict[str, Any]] | None:
    for cal_type, block in CUSTOM_BLOCKS.items():
        if int(block["start"]) <= addr < int(block["end"]):
            return cal_type, block
    return None


def extract_block_commands(disasm: str) -> list[BlockCommand]:
    commands: list[BlockCommand] = []
    for pair in parse_movw_movt_pairs(disasm):
        if pair.reg != "r0" or pair.value not in CMD_NAMES:
            continue
        block_match = block_for_addr(pair.addr)
        if block_match is None:
            continue
        cal_type, block = block_match
        commands.append(
            BlockCommand(
                cal_type=cal_type,
                role=str(block["role"]),
                addr=pair.addr,
                cmd=pair.value,
                cmd_name=CMD_NAMES[pair.value],
                selected_topology=block["selected_topology"],
                latest_payload_state=str(block["latest_payload_state"]),
            )
        )
    return commands


def classify_dispatch(commands: list[BlockCommand]) -> dict[str, Any]:
    by_cal: dict[int, set[int]] = {}
    for command in commands:
        by_cal.setdefault(command.cal_type, set()).add(command.cmd)
    target_coverage = {
        cal_type: bool(by_cal.get(cal_type, set()) & set(block["expected_cmds"]))
        for cal_type, block in CUSTOM_BLOCKS.items()
        if cal_type in {10, 14, 24}
    }
    all_target_commands_present = all(target_coverage.values())
    return {
        "decision": "v2699-custom-topology-dispatch-present-selector-state-missing"
        if all_target_commands_present
        else "v2699-custom-topology-dispatch-incomplete",
        "ok": all_target_commands_present,
        "target_command_coverage": target_coverage,
        "native_replay_remains_parked": True,
        "recommended_next": "v2700-lower-selector-state-re"
        if all_target_commands_present
        else "repair-dispatch-parser-before-next-unit",
        "reason": (
            "The cal_type 10/14/24 GET command blocks exist in acdb_loader_send_common_custom_topology, "
            "so the bug is not a missing loader block. Existing live results show ADM fails and ASM returns a stale payload; "
            "the next unit must recover the selector state/request model for those blocks, not replay existing payloads."
        ),
    }


def build_summary(refresh_objdump: bool = True) -> dict[str, Any]:
    if refresh_objdump or not COMMON_DISASM.exists():
        run_objdump()
    disasm = COMMON_DISASM.read_text(encoding="utf-8", errors="ignore")
    commands = extract_block_commands(disasm)
    return {
        "run_id": RUN_ID,
        "generated_at": now_iso(),
        "scope": "host-only private disassembly metadata; no device action, ioctl, mixer write, PCM probe, raw payload commit, or vendor byte emission",
        "input": {
            "libacdbloader": rel(LIBACDBLOADER),
            "disassembly": rel(COMMON_DISASM),
            "function": "acdb_loader_send_common_custom_topology",
            "range": f"0x{COMMON_TOPOLOGY_START:x}-0x{COMMON_TOPOLOGY_END:x}",
        },
        "classification": classify_dispatch(commands),
        "commands": [dataclasses.asdict(command) for command in commands],
    }


def table(rows: list[list[str]]) -> str:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    out = ["| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(rows[0])) + " |"]
    out.append("| " + " | ".join("---" for _ in rows[0]) + " |")
    for row in rows[1:]:
        out.append("| " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + " |")
    return "\n".join(out)


def render_report(summary: dict[str, Any]) -> str:
    c = summary["classification"]
    lines = [
        "# NATIVE_INIT V2699 — ACDB custom-topology dispatch RE",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only RE unit. This disassembles the private stock `libacdbloader.so` into `workspace/private` and commits only public-safe metadata about immediate command constants and block membership. No device action, Android handoff, `/dev/msm_audio_cal` ioctl, mixer write, PCM probe, raw ACDB payload commit, or vendor byte commit occurred.",
        "",
        "## Result",
        "",
        f"- decision: `{c['decision']}`",
        f"- ok: `{c['ok']}`",
        f"- recommended_next: `{c['recommended_next']}`",
        f"- native_replay_remains_parked: `{c['native_replay_remains_parked']}`",
        "",
        "## Extracted dispatch commands",
        "",
    ]
    rows = [["cal_type", "role", "block cmd addr", "GET cmd", "selected topology", "latest payload state"]]
    for command in summary["commands"]:
        selected = "None" if command["selected_topology"] is None else f"0x{command['selected_topology']:08x}"
        rows.append(
            [
                str(command["cal_type"]),
                command["role"],
                f"0x{command['addr']:x}",
                f"0x{command['cmd']:05x} ({command['cmd_name']})",
                selected,
                command["latest_payload_state"],
            ]
        )
    lines.extend([table(rows), ""])
    coverage_rows = [["cal_type", "command present"]]
    for cal_type, present in c["target_command_coverage"].items():
        coverage_rows.append([str(cal_type), str(present)])
    lines.extend(["## Target coverage", "", table(coverage_rows), ""])
    lines.extend(
        [
            "## Interpretation",
            "",
            "The missing cal_type `10` and stale cal_type `14` are not caused by absent loader dispatch blocks. `acdb_loader_send_common_custom_topology()` contains the ADM, ASM, and AFE custom-topology GET command constants in distinct block ranges. That narrows the real problem to the selector state and request buffer used by those blocks.",
            "",
            "This also explains why another same-route lower pointer-target run is low value: V2693/V2695 already showed the current lower request model reaches the blocks but produces `ret=-12` for ADM and a non-selected ASM payload. The next unit must change the request model or inspect the block-local selector state before the GET call.",
            "",
            "## Next unit",
            "",
            "V2700 should be a loader-selector-state RE unit, not a replay. It should decode or instrument the block-local request structure for the cal_type `10` and `14` calls inside `acdb_loader_send_common_custom_topology()`: the exact `in_buf` words, the object/table pointer provenance, and any preceding selector fields that differ from AFE cal_type `24`. Acceptance is either a new direct request tuple that returns byte-exact selected ADM/ASM payloads, or a documented close decision that no safe own-process selector remains.",
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_dispatch_v2699.py tests/test_analyze_audio_acdb_custom_topology_dispatch_v2699.py`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_custom_topology_dispatch_v2699 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_dispatch_v2699.py --write-report`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`",
            "- `git diff --check`",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--no-refresh-objdump", action="store_true")
    args = parser.parse_args(argv)
    summary = build_summary(refresh_objdump=not args.no_refresh_objdump)
    if args.write_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(render_report(summary), encoding="utf-8")
    if args.json or not args.write_report:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
