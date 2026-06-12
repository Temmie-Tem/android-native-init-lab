#!/usr/bin/env python3
"""V2242 user-ELF uprobe offset context audit.

V2241 proved runtime a90* probe IPs are load_bias + static helper offsets. This
host-only follow-up verifies those static offsets against the stripped user
ELFs: each offset must land in an executable LOAD segment, and bounded
instruction windows are written only to private evidence for future lookup.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_v2241_user_uprobe_offset_base_map import (
    DEFAULT_ELFS,
    DEFAULT_PARSER_SUMMARIES,
    HELPER_SOURCE,
    PRIVATE_RUNS,
    REPO_ROOT,
    RuntimeProbe,
    UprobeSpec,
    extract_runtime_probes,
    parse_uprobe_specs,
    read_json,
    rel,
)

DEFAULT_V2241 = PRIVATE_RUNS / "v2241-user-uprobe-offset-base-map-20260612-111447/summary.json"
DEFAULT_CONTEXT_ELFS = dict(DEFAULT_ELFS)
DEFAULT_CONTEXT_ELFS["a90periph"] = REPO_ROOT / "tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libperipheral_client.so"

KEY_EVENTS = {
    ("a90cnss", "wlfw_start"),
    ("a90cnss", "wlfw_service_request"),
    ("a90cnss", "wlfw_cap_qmi"),
    ("a90cnss", "wlfw_bdf_entry"),
    ("a90cnss", "wlfw_bdf_send_ret"),
    ("a90cnss", "wlfw_bdf_result_log"),
    ("a90cnss", "wlfw_worker_done_signal"),
    ("a90cnss", "wlfw_worker_post_done_wait"),
    ("a90libqmi", "libqmi_loop_client_init_ret"),
    ("a90pmsrv", "pm_service_main_supported_list_init"),
    ("a90pmsrv", "pm_server_register_entry"),
}


@dataclass(frozen=True)
class LoadSegment:
    index: int
    offset: int
    virt_addr: int
    file_size: int
    mem_size: int
    flags: str
    align: int

    @property
    def end_vaddr(self) -> int:
        return self.virt_addr + self.mem_size

    @property
    def end_file_vaddr(self) -> int:
        return self.virt_addr + self.file_size

    @property
    def executable(self) -> bool:
        return "E" in self.flags

    def contains_vaddr(self, value: int) -> bool:
        return self.virt_addr <= value < self.end_vaddr

    def file_offset_for_vaddr(self, value: int) -> int | None:
        if not self.contains_vaddr(value):
            return None
        file_delta = value - self.virt_addr
        if file_delta >= self.file_size:
            return None
        return self.offset + file_delta

    def public_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "offset": hex(self.offset),
            "virt_addr": hex(self.virt_addr),
            "file_size": hex(self.file_size),
            "mem_size": hex(self.mem_size),
            "flags": self.flags,
            "align": hex(self.align),
            "executable": self.executable,
        }


@dataclass(frozen=True)
class OffsetContext:
    group: str
    object: str
    event: str
    offset: int
    offset_hex: str
    source_line: int
    observed: bool
    key_event: bool
    elf_path: str | None
    elf_exists: bool
    segment_index: int | None
    segment_flags: str | None
    executable_segment: bool
    file_offset: int | None
    file_offset_hex: str | None
    in_file: bool
    issue: str | None


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def run_text(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_load_segments(path: Path) -> tuple[list[LoadSegment], dict[str, Any]]:
    if not path.exists():
        return [], {"path": rel(path), "exists": False}
    file_info = run_text(["file", str(path)])
    readelf = run_text(["readelf", "-lW", str(path)])
    segments: list[LoadSegment] = []
    for raw in readelf.stdout.splitlines():
        line = raw.strip()
        if not line.startswith("LOAD"):
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        hexes = re.findall(r"0x[0-9a-fA-F]+", line)
        if len(hexes) < 6:
            continue
        flags = "".join(parts[6:-1])
        segments.append(LoadSegment(
            index=len(segments),
            offset=int(hexes[0], 16),
            virt_addr=int(hexes[1], 16),
            file_size=int(hexes[3], 16),
            mem_size=int(hexes[4], 16),
            flags=flags,
            align=int(hexes[5], 16),
        ))
    return segments, {
        "path": rel(path),
        "exists": True,
        "file": file_info.stdout.strip(),
        "readelf_rc": readelf.returncode,
        "load_segments": [segment.public_dict() for segment in segments],
    }


def find_segment(segments: list[LoadSegment], offset: int) -> LoadSegment | None:
    for segment in segments:
        if segment.contains_vaddr(offset):
            return segment
    return None


def object_for_spec(spec: UprobeSpec) -> str:
    if spec.name.startswith("periph_"):
        return "a90periph"
    return spec.group


def observed_spec_keys(parser_summaries: list[Path], specs: dict[tuple[str, str], UprobeSpec]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for path in parser_summaries:
        for probe in extract_runtime_probes(path):
            key = (probe.group, probe.event)
            if key in specs:
                keys.add(key)
    return keys


def build_offset_contexts(
    specs: dict[tuple[str, str], UprobeSpec],
    observed_keys: set[tuple[str, str]],
    elf_paths: dict[str, Path],
    elf_segments: dict[str, list[LoadSegment]],
) -> list[OffsetContext]:
    rows: list[OffsetContext] = []
    for key, spec in sorted(specs.items(), key=lambda item: (object_for_spec(item[1]), item[1].offset, item[0][1])):
        obj = object_for_spec(spec)
        elf_path = elf_paths.get(obj)
        segments = elf_segments.get(obj, [])
        segment = find_segment(segments, spec.offset)
        file_offset = segment.file_offset_for_vaddr(spec.offset) if segment else None
        issue = None
        if elf_path is None:
            issue = "missing_elf_mapping"
        elif not elf_path.exists():
            issue = "missing_elf_file"
        elif segment is None:
            issue = "offset_outside_load_segments"
        elif not segment.executable:
            issue = "offset_not_executable"
        elif file_offset is None:
            issue = "offset_not_backed_by_file"
        rows.append(OffsetContext(
            group=spec.group,
            object=obj,
            event=spec.name,
            offset=spec.offset,
            offset_hex=hex(spec.offset),
            source_line=spec.source_line,
            observed=key in observed_keys,
            key_event=key in KEY_EVENTS,
            elf_path=rel(elf_path) if elf_path else None,
            elf_exists=bool(elf_path and elf_path.exists()),
            segment_index=segment.index if segment else None,
            segment_flags=segment.flags if segment else None,
            executable_segment=bool(segment and segment.executable),
            file_offset=file_offset,
            file_offset_hex=hex(file_offset) if file_offset is not None else None,
            in_file=file_offset is not None,
            issue=issue,
        ))
    return rows


def disassembler_command() -> list[str] | None:
    for tool in ("aarch64-linux-gnu-objdump", "llvm-objdump", "objdump"):
        path = shutil.which(tool)
        if path:
            return [path]
    return None


def read_bytes(path: Path, file_offset: int, size: int) -> str:
    with path.open("rb") as handle:
        handle.seek(file_offset)
        return handle.read(size).hex()


def disassemble_window(tool: list[str], elf_path: Path, offset: int, before: int, after: int) -> dict[str, Any]:
    start = max(0, (offset - before) & ~0x3)
    stop = (offset + after + 0x3) & ~0x3
    command = tool + ["-d", f"--start-address=0x{start:x}", f"--stop-address=0x{stop:x}", str(elf_path)]
    completed = run_text(command)
    return {
        "tool": tool[0],
        "command": [Path(item).name if item == tool[0] else item for item in command],
        "start": hex(start),
        "stop": hex(stop),
        "rc": completed.returncode,
        "stdout": completed.stdout.splitlines(),
        "stderr": completed.stderr.splitlines(),
    }


def write_private_context(
    out_dir: Path,
    rows: list[OffsetContext],
    elf_paths: dict[str, Path],
    before: int,
    after: int,
    include_all_observed: bool,
) -> tuple[Path, dict[str, Any]]:
    tool = disassembler_command()
    entries: list[dict[str, Any]] = []
    for row in rows:
        if row.issue is not None:
            continue
        if not row.key_event and not (include_all_observed and row.observed):
            continue
        elf_path = elf_paths[row.object]
        byte_start = max(0, row.file_offset - before) if row.file_offset is not None else None
        byte_size = before + after
        entry: dict[str, Any] = {
            "group": row.group,
            "object": row.object,
            "event": row.event,
            "offset": row.offset_hex,
            "source_line": row.source_line,
            "observed": row.observed,
            "key_event": row.key_event,
            "elf_path": row.elf_path,
            "segment_index": row.segment_index,
            "file_offset": row.file_offset_hex,
        }
        if row.file_offset is not None and byte_start is not None:
            entry["bytes_start_file_offset"] = hex(byte_start)
            entry["bytes_hex"] = read_bytes(elf_path, byte_start, byte_size)
        if tool is not None:
            entry["disassembly"] = disassemble_window(tool, elf_path, row.offset, before, after)
        entries.append(entry)
    context = {
        "warning": "Private evidence. Contains proprietary stripped-ELF byte/disassembly context; do not commit.",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "window_bytes_before": before,
        "window_bytes_after": after,
        "disassembler": Path(tool[0]).name if tool else None,
        "entries": entries,
    }
    path = out_dir / "private_instruction_context.json"
    path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path, {
        "path": rel(path),
        "entry_count": len(entries),
        "disassembler": context["disassembler"],
    }


def count_rows(rows: list[OffsetContext], predicate: Any) -> int:
    return sum(1 for row in rows if predicate(row))


def public_row(row: OffsetContext) -> dict[str, Any]:
    data = asdict(row)
    data.pop("file_offset", None)
    data.pop("offset", None)
    return data


def build_summary(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    specs = parse_uprobe_specs(args.helper_source)
    observed_keys = observed_spec_keys(args.parser_summaries, specs)
    elf_segments: dict[str, list[LoadSegment]] = {}
    elf_metadata: dict[str, Any] = {}
    for group, path in args.elf.items():
        segments, metadata = parse_load_segments(path)
        elf_segments[group] = segments
        elf_metadata[group] = metadata
    rows = build_offset_contexts(specs, observed_keys, args.elf, elf_segments)
    context_path, context_meta = write_private_context(
        out_dir,
        rows,
        args.elf,
        before=args.window_before,
        after=args.window_after,
        include_all_observed=args.include_all_observed_context,
    )
    observed_rows = [row for row in rows if row.observed]
    key_rows = [row for row in rows if row.key_event]
    bad_observed = [row for row in observed_rows if row.issue is not None]
    bad_static = [row for row in rows if row.issue is not None]
    bad_key = [row for row in key_rows if row.issue is not None]
    all_static_exec = not bad_static
    all_observed_exec = not bad_observed
    all_key_exec = not bad_key and len(key_rows) == len(KEY_EVENTS)
    decision = "v2242-user-elf-offset-context-pass"
    if not (all_static_exec and all_observed_exec and all_key_exec):
        decision = "v2242-user-elf-offset-context-incomplete"
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
            "helper_source": rel(args.helper_source),
            "parser_summaries": [rel(path) for path in args.parser_summaries],
            "v2241_summary": rel(args.v2241),
            "elfs": {group: rel(path) for group, path in args.elf.items()},
        },
        "v2241_decision": read_json(args.v2241).get("decision") if args.v2241.exists() else None,
        "static_spec_count": len(rows),
        "observed_spec_count": len(observed_rows),
        "key_event_count": len(key_rows),
        "expected_key_event_count": len(KEY_EVENTS),
        "static_exec_segment_hits": count_rows(rows, lambda row: row.issue is None),
        "observed_exec_segment_hits": count_rows(observed_rows, lambda row: row.issue is None),
        "key_exec_segment_hits": count_rows(key_rows, lambda row: row.issue is None),
        "static_issue_count": len(bad_static),
        "observed_issue_count": len(bad_observed),
        "key_issue_count": len(bad_key),
        "issues": {
            "static": [public_row(row) for row in bad_static[:30]],
            "observed": [public_row(row) for row in bad_observed[:30]],
            "key": [public_row(row) for row in bad_key[:30]],
        },
        "key_events": [public_row(row) for row in sorted(key_rows, key=lambda row: (row.object, row.offset))],
        "elf_metadata": elf_metadata,
        "private_instruction_context": context_meta,
        "identity_contract": {
            "static_offset_address_space": "ET_DYN user-ELF virtual address before load bias",
            "runtime_identity_formula": "runtime_probe_ip = per-run_load_bias + helper_static_uprobe_offset",
            "segment_check": "helper_static_uprobe_offset must fall in an executable LOAD segment of the matching stripped user ELF",
            "file_offset_formula": "file_offset = segment.p_offset + (helper_static_uprobe_offset - segment.p_vaddr)",
            "public_report_policy": "publish only metadata/counts; keep bytes and disassembly private",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2242-user-elf-offset-context")
    parser.add_argument("--helper-source", type=Path, default=HELPER_SOURCE)
    parser.add_argument("--parser-summary", action="append", type=Path, dest="parser_summaries")
    parser.add_argument("--v2241", type=Path, default=DEFAULT_V2241)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--window-before", type=int, default=32)
    parser.add_argument("--window-after", type=int, default=64)
    parser.add_argument("--include-all-observed-context", action="store_true", default=True)
    parser.add_argument("--elf", action="append", default=[], help="group=path override, e.g. a90cnss=/path/cnss-daemon")
    args = parser.parse_args()
    args.parser_summaries = args.parser_summaries or DEFAULT_PARSER_SUMMARIES
    elf_map = dict(DEFAULT_CONTEXT_ELFS)
    for item in args.elf:
        if "=" not in item:
            raise SystemExit(f"invalid --elf {item!r}; expected group=path")
        group, value = item.split("=", 1)
        elf_map[group] = Path(value)
    args.elf = elf_map
    return args


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
        "static_spec_count": summary["static_spec_count"],
        "observed_spec_count": summary["observed_spec_count"],
        "key_event_count": summary["key_event_count"],
        "static_issue_count": summary["static_issue_count"],
        "observed_issue_count": summary["observed_issue_count"],
        "key_issue_count": summary["key_issue_count"],
        "private_instruction_context": summary["private_instruction_context"],
    }, indent=2, sort_keys=True))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
