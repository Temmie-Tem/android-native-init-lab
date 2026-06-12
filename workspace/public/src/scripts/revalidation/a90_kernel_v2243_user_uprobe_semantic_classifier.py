#!/usr/bin/env python3
"""V2243 user-uprobe semantic classifier.

V2242 banked private stripped-ELF instruction windows for observed a90* helper
uprobes. This host-only classifier converts those private windows into public
metadata: event-role classes, target instruction classes, and alignment counts.
It deliberately keeps raw bytes and disassembly private.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_v2241_user_uprobe_offset_base_map import PRIVATE_RUNS, REPO_ROOT, rel

DEFAULT_V2242_SUMMARY = PRIVATE_RUNS / "v2242-user-elf-offset-context-20260612-112444/summary.json"
DEFAULT_V2242_CONTEXT = PRIVATE_RUNS / "v2242-user-elf-offset-context-20260612-112444/private_instruction_context.json"

INSTRUCTION_RE = re.compile(r"^\s*(?P<addr>[0-9a-fA-F]+):\s+(?P<bytes>(?:[0-9a-fA-F]{2,8}\s+)+)\s*(?P<mnemonic>[a-zA-Z0-9_.]+)?(?P<operands>.*)$")

KEY_EVENTS = {
    "wlfw_start",
    "wlfw_service_request",
    "wlfw_cap_qmi",
    "wlfw_bdf_entry",
    "wlfw_bdf_send_ret",
    "wlfw_bdf_result_log",
    "wlfw_worker_done_signal",
    "wlfw_worker_post_done_wait",
    "libqmi_loop_client_init_ret",
    "pm_server_register_entry",
    "pm_service_main_supported_list_init",
}


@dataclass(frozen=True)
class Instruction:
    address: int
    mnemonic: str
    operands: str
    raw_line: str


@dataclass(frozen=True)
class SemanticRow:
    group: str
    object: str
    event: str
    offset: str
    observed: bool
    key_event: bool
    event_role: str
    instruction_class: str
    previous_instruction_class: str | None
    next_instruction_class: str | None
    target_found: bool
    alignment: str
    confidence: str


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def parse_instructions(lines: list[str]) -> list[Instruction]:
    instructions: list[Instruction] = []
    for line in lines:
        match = INSTRUCTION_RE.match(line)
        if not match:
            continue
        mnemonic = (match.group("mnemonic") or "").strip().lower()
        if not mnemonic:
            continue
        instructions.append(Instruction(
            address=int(match.group("addr"), 16),
            mnemonic=mnemonic,
            operands=(match.group("operands") or "").strip(),
            raw_line=line,
        ))
    return instructions


def find_target(instructions: list[Instruction], offset: int) -> tuple[Instruction | None, Instruction | None, Instruction | None]:
    for index, instruction in enumerate(instructions):
        if instruction.address == offset:
            previous = instructions[index - 1] if index > 0 else None
            next_instruction = instructions[index + 1] if index + 1 < len(instructions) else None
            return previous, instruction, next_instruction
    return None, None, None


def instruction_class(instruction: Instruction | None) -> str | None:
    if instruction is None:
        return None
    mnemonic = instruction.mnemonic
    operands = instruction.operands
    if mnemonic == "stp" and "x29" in operands and "x30" in operands and "[sp" in operands:
        return "frame_prologue"
    if mnemonic in {"ret", "eret"}:
        return "return"
    if mnemonic in {"bl", "blr"}:
        return "call"
    if mnemonic == "b" or mnemonic.startswith("b."):
        return "branch"
    if mnemonic in {"cbz", "cbnz", "tbz", "tbnz"}:
        return "conditional_branch"
    if mnemonic in {"cmp", "cmn", "tst"} or mnemonic.startswith("ccmp"):
        return "compare"
    if mnemonic.startswith("ldr") or mnemonic.startswith("ldp"):
        return "load"
    if mnemonic.startswith("str") or mnemonic.startswith("stp"):
        return "store"
    if mnemonic in {"adr", "adrp", "add", "sub", "mov", "movz", "movk", "orr", "and", "eor"}:
        return "address_or_alu"
    if mnemonic.startswith("svc"):
        return "syscall"
    return "other"


def event_role(event: str) -> str:
    if event == "pm_service_main_supported_list_init":
        return "state_edge"
    if event.endswith("_entry") or event in {"wlfw_start", "pm_server_register_entry"}:
        return "entry"
    if "send_ret" in event or event.endswith("_return") or event.endswith("_ret"):
        return "return_or_result"
    if event.endswith("_retcheck") or "retcheck" in event:
        return "return_check"
    if event.endswith("_call") or "_call_" in event:
        return "call_edge"
    if "branch" in event:
        return "branch"
    if "success" in event:
        return "success_path"
    if "fail" in event or "error" in event or "not_found" in event:
        return "failure_path"
    if "wait" in event:
        return "wait_edge"
    if "signal" in event:
        return "signal_edge"
    if "log" in event:
        return "log_edge"
    if "qmi" in event or "service_request" in event or "bdf" in event or "cap" in event:
        return "protocol_edge"
    return "state_edge"


def role_alignment(role: str, current_class: str | None, previous_class: str | None, next_class: str | None) -> tuple[str, str]:
    if current_class is None:
        return "missing_target", "none"
    if role == "entry" and current_class == "frame_prologue":
        return "aligned_entry_prologue", "high"
    if role == "call_edge" and current_class == "call":
        return "aligned_call_site", "high"
    if role in {"return_check", "return_or_result"} and previous_class == "call":
        return "aligned_post_call", "high"
    if role == "branch" and current_class in {"branch", "conditional_branch", "compare"}:
        return "aligned_branch_or_compare", "high"
    if role in {"success_path", "failure_path"} and current_class in {"branch", "conditional_branch", "compare", "address_or_alu"}:
        return "plausible_path_marker", "medium"
    if role in {"protocol_edge", "state_edge", "log_edge", "wait_edge", "signal_edge"}:
        return "marker_edge", "medium"
    if next_class == "call" and role in {"log_edge", "signal_edge", "wait_edge"}:
        return "pre_call_marker", "medium"
    return "needs_manual_context", "low"


def public_row(row: SemanticRow) -> dict[str, Any]:
    return asdict(row)


def private_row(row: SemanticRow, previous: Instruction | None, current: Instruction | None, next_instruction: Instruction | None) -> dict[str, Any]:
    data = asdict(row)
    data["private_instruction_lines"] = {
        "previous": previous.raw_line if previous else None,
        "current": current.raw_line if current else None,
        "next": next_instruction.raw_line if next_instruction else None,
    }
    return data


def classify_context(context: dict[str, Any]) -> tuple[list[SemanticRow], list[dict[str, Any]]]:
    rows: list[SemanticRow] = []
    private_rows: list[dict[str, Any]] = []
    for entry in context.get("entries", []):
        disassembly = entry.get("disassembly") or {}
        instructions = parse_instructions(disassembly.get("stdout") or [])
        offset = int(str(entry["offset"]), 16)
        previous, current, next_instruction = find_target(instructions, offset)
        current_class = instruction_class(current)
        previous_class = instruction_class(previous)
        next_class = instruction_class(next_instruction)
        role = event_role(str(entry["event"]))
        alignment, confidence = role_alignment(role, current_class, previous_class, next_class)
        row = SemanticRow(
            group=str(entry["group"]),
            object=str(entry.get("object") or entry["group"]),
            event=str(entry["event"]),
            offset=str(entry["offset"]),
            observed=bool(entry.get("observed")),
            key_event=bool(entry.get("key_event") or entry.get("event") in KEY_EVENTS),
            event_role=role,
            instruction_class=current_class or "missing",
            previous_instruction_class=previous_class,
            next_instruction_class=next_class,
            target_found=current is not None,
            alignment=alignment,
            confidence=confidence,
        )
        rows.append(row)
        private_rows.append(private_row(row, previous, current, next_instruction))
    return rows, private_rows


def counter_dict(rows: list[SemanticRow], field: str) -> dict[str, int]:
    return dict(sorted(Counter(getattr(row, field) for row in rows).items()))


def build_summary(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    v2242_summary = read_json(args.v2242_summary)
    context = read_json(args.v2242_context)
    rows, private_rows = classify_context(context)
    key_rows = [row for row in rows if row.key_event]
    bad_targets = [row for row in rows if not row.target_found]
    low_key_rows = [row for row in key_rows if row.confidence == "low"]
    private_path = out_dir / "private_semantic_instruction_lines.json"
    private_path.write_text(json.dumps({
        "warning": "Private evidence. Contains raw stripped-ELF disassembly lines; do not commit or publish.",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_context": rel(args.v2242_context),
        "rows": private_rows,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decision = "v2243-user-uprobe-semantic-classifier-pass"
    if bad_targets or low_key_rows:
        decision = "v2243-user-uprobe-semantic-classifier-review-needed"
    return {
        "label": args.label,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "decision": decision,
        "pass": decision.endswith("-pass"),
        "out_dir": rel(out_dir),
        "safety": {
            "host_only": True,
            "device_io": False,
            "bpf_attach": False,
            "tracefs_control_write": False,
            "probe_write_user_executed": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
            "private_raw_log_copied_to_public": False,
        },
        "inputs": {
            "v2242_summary": rel(args.v2242_summary),
            "v2242_context": rel(args.v2242_context),
        },
        "v2242_decision": v2242_summary.get("decision"),
        "classified_entry_count": len(rows),
        "key_event_count": len(key_rows),
        "target_found_count": sum(1 for row in rows if row.target_found),
        "missing_target_count": len(bad_targets),
        "key_low_confidence_count": len(low_key_rows),
        "event_role_counts": counter_dict(rows, "event_role"),
        "instruction_class_counts": counter_dict(rows, "instruction_class"),
        "alignment_counts": counter_dict(rows, "alignment"),
        "confidence_counts": counter_dict(rows, "confidence"),
        "key_events": [public_row(row) for row in sorted(key_rows, key=lambda row: (row.object, row.offset, row.event))],
        "review_needed": [public_row(row) for row in sorted(low_key_rows, key=lambda row: (row.object, row.offset, row.event))],
        "private_semantic_instruction_lines": {
            "path": rel(private_path),
            "entry_count": len(private_rows),
        },
        "public_policy": {
            "raw_bytes_published": False,
            "raw_disassembly_published": False,
            "published_fields": "event role, instruction class, neighboring instruction classes, alignment/confidence only",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2243-user-uprobe-semantic-classifier")
    parser.add_argument("--v2242-summary", type=Path, default=DEFAULT_V2242_SUMMARY)
    parser.add_argument("--v2242-context", type=Path, default=DEFAULT_V2242_CONTEXT)
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(args, out_dir)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": summary["decision"],
        "pass": summary["pass"],
        "out_dir": summary["out_dir"],
        "summary": rel(summary_path),
        "classified_entry_count": summary["classified_entry_count"],
        "key_event_count": summary["key_event_count"],
        "missing_target_count": summary["missing_target_count"],
        "key_low_confidence_count": summary["key_low_confidence_count"],
        "confidence_counts": summary["confidence_counts"],
    }, indent=2, sort_keys=True))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
