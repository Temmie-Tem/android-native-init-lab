#!/usr/bin/env python3
"""Symbolize the v236 Android linker crash file offset.

This host-side tool keeps v237 bounded to evidence handling: it can parse the
existing v236 ptrace-lite crash captures, optionally pull the matching linker64
ELF through the existing read-only native shell/base64 path, and run host
readelf/objdump to map the crash file offset to section/symbol/disassembly
context.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import hashlib
import json
import re
import shutil
import stat
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_bytes


DEFAULT_OUT_DIR = Path("tmp/wifi/v237-linker-offset-symbolize")
DEFAULT_V236_MANIFEST = Path("tmp/wifi/v236-linker-crash-capture-live/manifest.json")
DEFAULT_REMOTE_LINKER = "/mnt/system/system/apex/com.android.runtime/bin/linker64"
DEFAULT_OFFSET = 0x1002F4
MAX_LINKER_BYTES = 8 * 1024 * 1024
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=]*$")
STAT_SIZE_RE = re.compile(r"\bsize=(\d+)\b")
PC_RE = re.compile(r"^capture\.crash\.regset\.word32=(0x[0-9a-fA-F]+)$", re.MULTILINE)
FAULT_RE = re.compile(r"^capture\.crash\.siginfo\.addr=(0x[0-9a-fA-F]+)$", re.MULTILINE)
MAP_RE = re.compile(
    r"^([0-9a-fA-F]+)-([0-9a-fA-F]+)\s+"
    r"(\S+)\s+([0-9a-fA-F]+)\s+\S+\s+\S+\s*(.*)$"
)
SECTION_RE = re.compile(
    r"^\s*\[\s*(\d+)\]\s+(\S+)\s+(\S+)\s+"
    r"([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+"
)
SYMBOL_RE = re.compile(
    r"^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+)\s+(\S+)\s+(\S+)\s+\S+\s+(\S+)\s+(.*)$"
)
LOAD_RE = re.compile(
    r"^\s*LOAD\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+"
    r"0x[0-9a-fA-F]+\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+"
)

ALLOWED_REMOTE_LINKERS = {
    "/mnt/system/system/apex/com.android.runtime/bin/linker64",
    "/mnt/system/system/bin/linker64",
}
CMDV1_NOISE_PREFIXES = (
    "a90:/#",
    "A90P1 BEGIN ",
    "A90P1 END ",
    "[done] ",
    "[exit ",
    "run: pid=",
)


@dataclass
class CrashCase:
    output_file: str
    linker_profile: str
    target_profile: str
    linker_path: str
    pc: int
    fault_addr: int | None
    map_start: int
    map_end: int
    map_perms: str
    map_file_offset: int
    map_path: str
    computed_file_offset: int


@dataclass
class ToolResult:
    command: list[str]
    rc: int
    stdout: str
    stderr: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=repo_path(DEFAULT_OUT_DIR))
    parser.add_argument("--v236-manifest", type=Path, default=repo_path(DEFAULT_V236_MANIFEST))
    parser.add_argument("--linker-elf", type=Path, default=None, help="local linker64 ELF to analyze")
    parser.add_argument("--offset", default=hex(DEFAULT_OFFSET), help="expected linker64 file offset, default 0x1002f4")
    parser.add_argument("--window", type=lambda value: int(value, 0), default=0x80)
    parser.add_argument("--remote-linker", default=DEFAULT_REMOTE_LINKER)
    parser.add_argument("--pull-from-device", action="store_true")
    parser.add_argument("--no-pull", action="store_true", help="explicitly skip device pull; this is the default")
    parser.add_argument("--max-file-bytes", type=int, default=MAX_LINKER_BYTES)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan", help="write v237 plan-only evidence")
    subparsers.add_parser("analyze", help="parse v236 evidence and optionally symbolize a linker ELF")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_int(value: str) -> int:
    return int(value, 0)


def run_tool(command: list[str], timeout: int = 20) -> ToolResult:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return ToolResult(command, result.returncode, result.stdout, result.stderr)


def choose_tool(*names: str) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def reset_private_dir(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        ensure_private_dir(path)
        return
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing non-directory output path: {path}")
    shutil.rmtree(path)
    ensure_private_dir(path)


def write_tool_result(store: EvidenceStore, rel: str, result: ToolResult) -> str:
    text = (
        "$ " + " ".join(result.command) + "\n"
        f"# rc={result.rc}\n"
        "## stdout\n"
        + result.stdout
        + ("\n" if result.stdout and not result.stdout.endswith("\n") else "")
        + "## stderr\n"
        + result.stderr
    )
    path = store.write_text(rel, text)
    return str(path.relative_to(store.run_dir))


def load_v236_manifest(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def parse_maps_for_pc(text: str, pc: int) -> tuple[int, int, str, int, str] | None:
    for line in text.splitlines():
        match = MAP_RE.match(line)
        if not match:
            continue
        start = int(match.group(1), 16)
        end = int(match.group(2), 16)
        perms = match.group(3)
        file_offset = int(match.group(4), 16)
        path = match.group(5).strip()
        if start <= pc < end and "linker64" in path:
            return start, end, perms, file_offset, path
    return None


def parse_crash_case(v236_dir: Path, row: dict[str, Any]) -> CrashCase | None:
    output_rel = row.get("output_file")
    if not isinstance(output_rel, str):
        return None
    path = v236_dir / output_rel
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    pc_match = PC_RE.search(text)
    if not pc_match:
        return None
    pc = int(pc_match.group(1), 16)
    fault_match = FAULT_RE.search(text)
    fault_addr = int(fault_match.group(1), 16) if fault_match else None
    mapping = parse_maps_for_pc(text, pc)
    if mapping is None:
        return None
    map_start, map_end, perms, map_file_offset, map_path = mapping
    computed_offset = pc - map_start + map_file_offset
    return CrashCase(
        output_file=output_rel,
        linker_profile=str(row.get("linker_profile", "")),
        target_profile=str(row.get("profile", row.get("target_profile", ""))),
        linker_path=str(row.get("linker_path", "")),
        pc=pc,
        fault_addr=fault_addr,
        map_start=map_start,
        map_end=map_end,
        map_perms=perms,
        map_file_offset=map_file_offset,
        map_path=map_path,
        computed_file_offset=computed_offset,
    )


def parse_v236_cases(manifest: dict[str, Any]) -> list[CrashCase]:
    manifest_path = Path(manifest.get("_manifest_path", ""))
    v236_dir = manifest_path.parent if manifest_path else repo_path(DEFAULT_V236_MANIFEST).parent
    cases: list[CrashCase] = []
    for row in manifest.get("matrix", []):
        if not isinstance(row, dict):
            continue
        case = parse_crash_case(v236_dir, row)
        if case is not None:
            cases.append(case)
    return cases


def parse_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = SECTION_RE.match(line)
        if not match:
            continue
        sections.append({
            "index": int(match.group(1)),
            "name": match.group(2),
            "type": match.group(3),
            "addr": int(match.group(4), 16),
            "offset": int(match.group(5), 16),
            "size": int(match.group(6), 16),
        })
    return sections


def parse_load_segments(text: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = LOAD_RE.match(line)
        if not match:
            continue
        segments.append({
            "offset": int(match.group(1), 16),
            "vaddr": int(match.group(2), 16),
            "filesz": int(match.group(3), 16),
            "memsz": int(match.group(4), 16),
        })
    return segments


def parse_symbols(text: str) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = SYMBOL_RE.match(line)
        if not match:
            continue
        name = match.group(6).strip()
        if not name:
            continue
        ndx = match.group(5)
        if ndx in {"UND", "ABS"}:
            continue
        symbols.append({
            "value": int(match.group(1), 16),
            "size": int(match.group(2)),
            "type": match.group(3),
            "bind": match.group(4),
            "ndx": ndx,
            "name": name,
        })
    return symbols


def section_for_offset(sections: list[dict[str, Any]], offset: int) -> dict[str, Any] | None:
    for section in sections:
        start = section["offset"]
        end = start + section["size"]
        if section["size"] > 0 and start <= offset < end:
            item = dict(section)
            item["delta"] = offset - start
            return item
    return None


def vaddr_for_offset(segments: list[dict[str, Any]], offset: int) -> int | None:
    for segment in segments:
        start = segment["offset"]
        end = start + segment["filesz"]
        if segment["filesz"] > 0 and start <= offset < end:
            return segment["vaddr"] + (offset - start)
    return None


def nearest_symbols(symbols: list[dict[str, Any]], vaddr: int, limit: int = 8) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for symbol in symbols:
        value = symbol["value"]
        size = symbol["size"]
        if value > vaddr:
            continue
        item = dict(symbol)
        item["delta"] = vaddr - value
        item["contains"] = size > 0 and value <= vaddr < value + size
        candidates.append(item)
    candidates.sort(key=lambda item: (not item["contains"], item["delta"]))
    return candidates[:limit]


def instruction_line(disasm: str, vaddr: int) -> str | None:
    needle = f"{vaddr:x}:"
    for line in disasm.splitlines():
        if needle in line.lower():
            return line.strip()
    return None


def analyze_elf(store: EvidenceStore, elf: Path, offset: int, window: int) -> dict[str, Any]:
    readelf = choose_tool("aarch64-linux-gnu-readelf", "readelf")
    objdump = choose_tool("aarch64-linux-gnu-objdump", "llvm-objdump", "objdump")
    file_tool = choose_tool("file")
    if readelf is None or objdump is None:
        raise RuntimeError("readelf/objdump tools are required")
    elf = repo_path(elf)
    if not elf.exists():
        raise RuntimeError(f"linker ELF not found: {elf}")
    if elf.stat().st_size <= offset:
        raise RuntimeError(f"offset 0x{offset:x} is beyond ELF size {elf.stat().st_size}")

    tool_outputs: dict[str, str] = {}
    if file_tool:
        result = run_tool([file_tool, str(elf)], timeout=10)
        tool_outputs["file"] = write_tool_result(store, "host/file-linker64.txt", result)
    headers = run_tool([readelf, "-W", "-h", "-l", str(elf)], timeout=20)
    sections = run_tool([readelf, "-W", "-S", str(elf)], timeout=20)
    symbols = run_tool([readelf, "-W", "-s", str(elf)], timeout=30)
    tool_outputs["readelf_headers"] = write_tool_result(store, "host/readelf-headers.txt", headers)
    tool_outputs["readelf_sections"] = write_tool_result(store, "host/readelf-sections.txt", sections)
    tool_outputs["readelf_symbols"] = write_tool_result(store, "host/readelf-symbols.txt", symbols)

    parsed_sections = parse_sections(sections.stdout)
    parsed_segments = parse_load_segments(headers.stdout)
    parsed_symbols = parse_symbols(symbols.stdout)
    section = section_for_offset(parsed_sections, offset)
    vaddr = vaddr_for_offset(parsed_segments, offset)
    near = nearest_symbols(parsed_symbols, vaddr, limit=8) if vaddr is not None else []
    disasm_file = None
    selected_instruction = None
    if vaddr is not None:
        start = max(0, vaddr - window)
        stop = vaddr + window
        disasm = run_tool([
            objdump,
            "-d",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{stop:x}",
            str(elf),
        ], timeout=30)
        disasm_file = write_tool_result(store, "host/objdump-crash-window.txt", disasm)
        selected_instruction = instruction_line(disasm.stdout, vaddr)

    return {
        "elf_path": str(elf),
        "elf_size": elf.stat().st_size,
        "elf_sha256": sha256_file(elf),
        "offset": f"0x{offset:x}",
        "mapped_vaddr": f"0x{vaddr:x}" if vaddr is not None else None,
        "section": section,
        "nearest_symbols": near,
        "selected_instruction": selected_instruction,
        "tool_outputs": tool_outputs,
        "disassembly_file": disasm_file,
    }


def validate_remote_linker(path: str) -> None:
    if path not in ALLOWED_REMOTE_LINKERS:
        raise RuntimeError(f"refusing remote linker path outside allowlist: {path}")


def validate_device_command(command: list[str], remote_linker: str) -> None:
    if command in (["version"], ["status"], ["mountsystem", "ro"]):
        return
    if command == ["stat", remote_linker]:
        return
    if command == ["run", "/cache/bin/toybox", "base64", "-w", "0", remote_linker]:
        return
    raise RuntimeError(f"unexpected device command: {' '.join(command)}")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/commands/{name}.txt", text.rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_device(store: EvidenceStore,
                   args: argparse.Namespace,
                   name: str,
                   command: list[str],
                   timeout: float | None = None) -> dict[str, Any]:
    validate_device_command(command, args.remote_linker)
    capture = run_capture(args, name, command, timeout=timeout)
    file_path = write_capture(store, name, capture.text or capture.error)
    data = capture_to_manifest(capture)
    data["file"] = file_path
    return data


def cleaned_payload_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in strip_cmdv1_text(text).splitlines():
        line = raw_line.strip()
        for marker in ("[exit ", "[done] ", "A90P1 END "):
            marker_index = line.find(marker)
            if marker_index >= 0:
                line = line[:marker_index].strip()
        if not line:
            continue
        if line.startswith("cmdv1 ") or line.startswith("cmdv1x "):
            continue
        if any(line.startswith(prefix) for prefix in CMDV1_NOISE_PREFIXES):
            continue
        lines.append(line)
    return lines


def extract_base64_payload(text: str) -> str:
    payload = "".join(cleaned_payload_lines(text))
    payload = re.sub(r"\s+", "", payload)
    if not payload:
        raise RuntimeError("empty base64 payload")
    if not BASE64_RE.fullmatch(payload):
        raise RuntimeError("base64 payload contains unexpected characters")
    return payload


def parse_stat_size(text: str) -> int | None:
    match = STAT_SIZE_RE.search(strip_cmdv1_text(text))
    return int(match.group(1)) if match else None


def pull_linker_from_device(store: EvidenceStore, args: argparse.Namespace) -> tuple[Path | None, list[dict[str, Any]], str | None]:
    validate_remote_linker(args.remote_linker)
    captures: list[dict[str, Any]] = []
    captures.append(capture_device(store, args, "version", ["version"], timeout=15.0))
    captures.append(capture_device(store, args, "status", ["status"], timeout=25.0))
    mount_record = capture_device(store, args, "mountsystem-ro", ["mountsystem", "ro"], timeout=35.0)
    captures.append(mount_record)
    if not mount_record["ok"]:
        return None, captures, "mountsystem ro failed"
    stat_record = capture_device(store, args, "stat-linker64", ["stat", args.remote_linker], timeout=25.0)
    captures.append(stat_record)
    if not stat_record["ok"]:
        return None, captures, "remote linker stat failed"
    expected_size = parse_stat_size(stat_record["text"])
    if expected_size is None:
        return None, captures, "remote linker stat size missing"
    if expected_size > args.max_file_bytes:
        return None, captures, f"remote linker too large: {expected_size}"
    base64_record = capture_device(
        store,
        args,
        "base64-linker64",
        ["run", "/cache/bin/toybox", "base64", "-w", "0", args.remote_linker],
        timeout=max(args.timeout, 120.0),
    )
    captures.append(base64_record)
    if not base64_record["ok"]:
        return None, captures, "remote linker base64 failed"
    try:
        data = base64.b64decode(extract_base64_payload(base64_record["text"]), validate=True)
    except (binascii.Error, RuntimeError) as exc:
        return None, captures, f"remote linker base64 decode failed: {exc}"
    if len(data) != expected_size:
        return None, captures, f"remote linker size mismatch: {len(data)}!={expected_size}"
    path = store.path("files/linker64")
    write_private_bytes(path, data)
    return path, captures, None


def build_plan_summary() -> str:
    return "\n".join([
        "# v237 Linker Offset Symbolization Probe",
        "",
        "- purpose: map v236 linker64 crash offset 0x1002f4 to ELF section/symbol/disassembly context",
        "- default v236 evidence: `tmp/wifi/v236-linker-crash-capture-live/manifest.json`",
        "- optional device pull: `/mnt/system/system/apex/com.android.runtime/bin/linker64` through `mountsystem ro` + `toybox base64`",
        "- blocked actions: Wi-Fi daemon start, scan/connect, rfkill writes, Android partition writes",
        "",
        "## Commands",
        "",
        "```bash",
        "python3 scripts/revalidation/wifi_linker_offset_symbolize.py analyze --no-pull",
        "python3 scripts/revalidation/wifi_linker_offset_symbolize.py analyze --pull-from-device",
        "```",
        "",
    ])


def build_summary(manifest: dict[str, Any]) -> str:
    cases = manifest.get("crash_cases", [])
    case_rows = [
        [
            item["linker_profile"],
            item["target_profile"],
            item["fault_addr"],
            item["pc"],
            item["computed_file_offset"],
            item["map_perms"],
        ]
        for item in cases
    ]
    symbol_rows: list[list[str]] = []
    analysis = manifest.get("elf_analysis") or {}
    for item in analysis.get("nearest_symbols") or []:
        symbol_rows.append([
            item.get("name", ""),
            item.get("type", ""),
            hex(item.get("value", 0)) if isinstance(item.get("value"), int) else str(item.get("value")),
            str(item.get("size", "")),
            hex(item.get("delta", 0)) if isinstance(item.get("delta"), int) else str(item.get("delta")),
            str(item.get("contains", "")),
        ])
    lines = [
        "# Native Init v237 Linker Offset Symbolization",
        "",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- expected_offset: `{manifest['expected_offset']}`",
        f"- consistent_offset: `{manifest.get('consistent_offset')}`",
        "",
        "## Crash Cases",
        "",
        markdown_table(["linker", "target", "fault", "pc", "file offset", "perms"], case_rows or [["none", "none", "none", "none", "none", "none"]]),
        "",
        "## ELF Analysis",
        "",
    ]
    if analysis:
        section = analysis.get("section")
        lines.extend([
            f"- elf: `{analysis.get('elf_path')}`",
            f"- sha256: `{analysis.get('elf_sha256')}`",
            f"- mapped_vaddr: `{analysis.get('mapped_vaddr')}`",
            f"- section: `{section.get('name') if isinstance(section, dict) else None}`",
            f"- selected_instruction: `{analysis.get('selected_instruction')}`",
            f"- disassembly: `{analysis.get('disassembly_file')}`",
            "",
            "### Nearest Symbols",
            "",
            markdown_table(["name", "type", "value", "size", "delta", "contains"], symbol_rows or [["none", "", "", "", "", ""]]),
            "",
        ])
    else:
        lines.extend([
            "- ELF analysis was not available in this run.",
            "- Rerun with `--pull-from-device` when the serial bridge is connected, or pass `--linker-elf <path>`.",
            "",
        ])
    lines.extend([
        "## Guardrails",
        "",
    ])
    for item in manifest["guardrails"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def crash_cases_to_manifest(cases: list[CrashCase]) -> list[dict[str, str]]:
    rows = []
    for case in cases:
        rows.append({
            "output_file": case.output_file,
            "linker_profile": case.linker_profile,
            "target_profile": case.target_profile,
            "linker_path": case.linker_path,
            "pc": f"0x{case.pc:x}",
            "fault_addr": f"0x{case.fault_addr:x}" if case.fault_addr is not None else None,
            "map_start": f"0x{case.map_start:x}",
            "map_end": f"0x{case.map_end:x}",
            "map_perms": case.map_perms,
            "map_file_offset": f"0x{case.map_file_offset:x}",
            "map_path": case.map_path,
            "computed_file_offset": f"0x{case.computed_file_offset:x}",
        })
    return rows


def plan_command(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "v237-plan",
        "pass": True,
        "decision": "linker-offset-symbolization-plan-ready",
        "reason": "plan written; no device or ELF access attempted",
        "host_metadata": collect_host_metadata(),
        "guardrails": guardrails(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_plan_summary())
    print(f"PASS out_dir={out_dir} decision={manifest['decision']}")
    return 0


def guardrails() -> list[str]:
    return [
        "read-only system mount through mountsystem ro only",
        "optional linker64 pull uses toybox base64 from an allowlisted path",
        "no Android daemon execution",
        "no Wi-Fi scan/connect",
        "no rfkill write",
        "no credential collection",
        "no system or vendor write",
        "host output directory/files are private",
    ]


def analyze_command(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    reset_private_dir(out_dir)
    store = EvidenceStore(out_dir)
    expected_offset = safe_int(args.offset)
    v236 = load_v236_manifest(args.v236_manifest)
    cases = parse_v236_cases(v236) if not v236.get("missing") else []
    offsets = sorted({case.computed_file_offset for case in cases})
    consistent_offset = len(offsets) == 1
    selected_offset = offsets[0] if consistent_offset else expected_offset
    if args.offset:
        selected_offset = expected_offset

    device_captures: list[dict[str, Any]] = []
    linker_elf = repo_path(args.linker_elf) if args.linker_elf else None
    pull_error = None
    if args.pull_from_device and args.no_pull:
        raise RuntimeError("--pull-from-device and --no-pull are mutually exclusive")
    if linker_elf is None and args.pull_from_device:
        linker_elf, device_captures, pull_error = pull_linker_from_device(store, args)

    elf_analysis = None
    analysis_error = None
    if linker_elf is not None:
        try:
            elf_analysis = analyze_elf(store, linker_elf, selected_offset, args.window)
        except Exception as exc:  # noqa: BLE001 - report keeps analysis failure reason
            analysis_error = str(exc)

    if not cases:
        decision = "linker-offset-symbolization-blocked-no-v236-evidence"
        reason = "v236 crash case evidence could not be parsed"
        pass_ok = False
    elif not consistent_offset:
        decision = "linker-offset-inconsistent"
        reason = "v236 crash cases do not agree on one linker64 file offset"
        pass_ok = False
    elif selected_offset != expected_offset:
        decision = "linker-offset-unexpected"
        reason = f"v236 offset 0x{selected_offset:x} did not match expected 0x{expected_offset:x}"
        pass_ok = False
    elif elf_analysis is None:
        decision = "linker-offset-symbolization-blocked-no-elf"
        reason = analysis_error or pull_error or "matching linker64 ELF was not provided or pulled"
        pass_ok = False
    else:
        section = elf_analysis.get("section")
        selected_instruction = elf_analysis.get("selected_instruction")
        if section and selected_instruction:
            nearest = elf_analysis.get("nearest_symbols") or []
            if nearest:
                decision = "linker-offset-symbolized"
                reason = "crash offset mapped to linker64 section, nearest symbol list, and disassembly context"
            else:
                decision = "linker-offset-disassembled-no-symbol"
                reason = "crash offset mapped to linker64 section and disassembly, but symbols are stripped or unavailable"
            pass_ok = True
        else:
            decision = "linker-offset-symbolization-partial"
            reason = "ELF was available but section/disassembly context was incomplete"
            pass_ok = False

    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "v237-linker-offset-symbolization",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "expected_offset": f"0x{expected_offset:x}",
        "selected_offset": f"0x{selected_offset:x}",
        "consistent_offset": consistent_offset,
        "offsets": [f"0x{offset:x}" for offset in offsets],
        "v236_manifest": str(repo_path(args.v236_manifest)),
        "v236_decision": v236.get("decision"),
        "crash_cases": crash_cases_to_manifest(cases),
        "device_captures": device_captures,
        "pull_from_device": args.pull_from_device,
        "pull_error": pull_error,
        "analysis_error": analysis_error,
        "elf_analysis": elf_analysis,
        "guardrails": guardrails(),
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


def main() -> int:
    args = parse_args()
    if args.command == "plan":
        return plan_command(args)
    if args.command == "analyze":
        return analyze_command(args)
    raise RuntimeError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
