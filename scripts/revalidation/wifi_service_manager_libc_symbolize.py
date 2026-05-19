#!/usr/bin/env python3
"""V391 read-only libc pull and service-manager crash offset symbolization."""

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

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, ensure_private_dir, write_private_bytes
from wifi_service_manager_crash_symbolize import parse_key_values


DEFAULT_OUT_DIR = Path("tmp/wifi/v391-service-manager-libc-symbolize")
DEFAULT_RUN_LOG = Path("tmp/wifi/v390-approved-full-20260520-063910/live/native/run-system-servicemanager.txt")
DEFAULT_REMOTE_LIBC = "/mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so"
MAX_LIBC_BYTES = 4 * 1024 * 1024
BASE64_RE = re.compile(r"^[A-Za-z0-9+/=]*$")
STAT_SIZE_RE = re.compile(r"\bsize=(\d+)\b")
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
CMDV1_NOISE_PREFIXES = (
    "a90:/#",
    "A90P1 BEGIN ",
    "A90P1 END ",
    "[done] ",
    "[exit ",
    "run: pid=",
)
ALLOWED_REMOTE_LIBC = {
    "/mnt/system/system/apex/com.android.runtime/lib64/bionic/libc.so",
}


@dataclass
class ToolResult:
    command: list[str]
    rc: int
    stdout: str
    stderr: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-log", type=Path, default=DEFAULT_RUN_LOG)
    parser.add_argument("--libc-elf", type=Path, default=None)
    parser.add_argument("--remote-libc", default=DEFAULT_REMOTE_LIBC)
    parser.add_argument("--pull-from-device", action="store_true")
    parser.add_argument("--no-pull", action="store_true", help="explicitly skip device pull; this is the default")
    parser.add_argument("--max-file-bytes", type=int, default=MAX_LIBC_BYTES)
    parser.add_argument("--window", type=lambda value: int(value, 0), default=0x80)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("analyze")
    return parser.parse_args()


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def choose_tool(*names: str) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def run_tool(command: list[str], timeout: int = 30) -> ToolResult:
    result = subprocess.run(
        command,
        cwd=repo_path(Path(".")),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return ToolResult(command, result.returncode, result.stdout, result.stderr)


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


def validate_remote_libc(path: str) -> None:
    if path not in ALLOWED_REMOTE_LIBC:
        raise RuntimeError(f"refusing remote libc path outside allowlist: {path}")


def validate_device_command(command: list[str], remote_libc: str) -> None:
    if command in (["version"], ["status"], ["mountsystem", "ro"]):
        return
    if command == ["stat", remote_libc]:
        return
    if command == ["run", "/cache/bin/toybox", "base64", "-w", "0", remote_libc]:
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
    validate_device_command(command, args.remote_libc)
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


def pull_libc_from_device(store: EvidenceStore, args: argparse.Namespace) -> tuple[Path | None, list[dict[str, Any]], str | None]:
    validate_remote_libc(args.remote_libc)
    captures: list[dict[str, Any]] = []
    captures.append(capture_device(store, args, "version", ["version"], timeout=15.0))
    captures.append(capture_device(store, args, "status", ["status"], timeout=25.0))
    mount_record = capture_device(store, args, "mountsystem-ro", ["mountsystem", "ro"], timeout=35.0)
    captures.append(mount_record)
    if not mount_record["ok"]:
        return None, captures, "mountsystem ro failed"
    stat_record = capture_device(store, args, "stat-libc", ["stat", args.remote_libc], timeout=25.0)
    captures.append(stat_record)
    if not stat_record["ok"]:
        return None, captures, "remote libc stat failed"
    expected_size = parse_stat_size(stat_record["text"])
    if expected_size is None:
        return None, captures, "remote libc stat size missing"
    if expected_size > args.max_file_bytes:
        return None, captures, f"remote libc too large: {expected_size}"
    base64_record = capture_device(
        store,
        args,
        "base64-libc",
        ["run", "/cache/bin/toybox", "base64", "-w", "0", args.remote_libc],
        timeout=max(args.timeout, 180.0),
    )
    captures.append(base64_record)
    if not base64_record["ok"]:
        return None, captures, "remote libc base64 failed"
    try:
        base64_text = store.path(base64_record["file"]).read_text(encoding="utf-8", errors="replace")
        data = base64.b64decode(extract_base64_payload(base64_text), validate=True)
    except (binascii.Error, RuntimeError) as exc:
        return None, captures, f"remote libc base64 decode failed: {exc}"
    if len(data) != expected_size:
        return None, captures, f"remote libc size mismatch: {len(data)}!={expected_size}"
    path = store.path("files/libc.so")
    write_private_bytes(path, data)
    return path, captures, None


def parse_sections(text: str) -> list[dict[str, Any]]:
    sections = []
    for line in text.splitlines():
        match = SECTION_RE.match(line)
        if not match:
            continue
        sections.append({
            "index": int(match.group(1)),
            "name": match.group(2),
            "type": match.group(3),
            "address": int(match.group(4), 16),
            "offset": int(match.group(5), 16),
            "size": int(match.group(6), 16),
        })
    return sections


def parse_load_segments(text: str) -> list[dict[str, int]]:
    segments = []
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
    symbols = []
    for line in text.splitlines():
        match = SYMBOL_RE.match(line)
        if not match:
            continue
        name = match.group(6).strip()
        if not name:
            continue
        symbols.append({
            "value": int(match.group(1), 16),
            "size": int(match.group(2)),
            "type": match.group(3),
            "bind": match.group(4),
            "section": match.group(5),
            "name": name,
        })
    return symbols


def section_for_offset(sections: list[dict[str, Any]], offset: int) -> dict[str, Any] | None:
    for section in sections:
        start = int(section["offset"])
        end = start + int(section["size"])
        if start <= offset < end:
            item = dict(section)
            item["delta"] = offset - start
            return item
    return None


def vaddr_for_offset(segments: list[dict[str, int]], offset: int) -> int | None:
    for segment in segments:
        start = segment["offset"]
        end = start + segment["filesz"]
        if start <= offset < end:
            return segment["vaddr"] + (offset - start)
    return None


def nearest_symbols(symbols: list[dict[str, Any]], vaddr: int, limit: int = 8) -> list[dict[str, Any]]:
    candidates = []
    for symbol in symbols:
        value = int(symbol["value"])
        size = int(symbol["size"])
        if value == 0:
            continue
        contains = value <= vaddr < value + max(size, 1)
        if value <= vaddr or contains:
            item = dict(symbol)
            item["delta"] = vaddr - value
            item["contains"] = contains
            candidates.append(item)
    candidates.sort(key=lambda item: (not item["contains"], abs(int(item["delta"]))))
    return candidates[:limit]


def instruction_line(disasm: str, vaddr: int) -> str | None:
    needle = f"{vaddr:x}:"
    for line in disasm.splitlines():
        if needle in line.lower():
            return line.strip()
    return None


def maprow_offset(values: dict[str, str], name: str) -> int | None:
    raw = values.get(f"capture.crash.maprow.{name}.relative_offset", "")
    if not raw:
        return None
    return int(raw, 0)


def analyze_one_offset(store: EvidenceStore,
                       elf: Path,
                       name: str,
                       offset: int,
                       window: int,
                       tools: dict[str, str]) -> dict[str, Any]:
    headers_text = store.path("host/readelf-headers.txt").read_text(encoding="utf-8", errors="replace")
    sections_text = store.path("host/readelf-sections.txt").read_text(encoding="utf-8", errors="replace")
    symbols_text = store.path("host/readelf-symbols.txt").read_text(encoding="utf-8", errors="replace")
    sections = parse_sections(headers_text + "\n" + sections_text)
    segments = parse_load_segments(headers_text)
    symbols = parse_symbols(symbols_text)
    section = section_for_offset(sections, offset)
    vaddr = vaddr_for_offset(segments, offset)
    near = nearest_symbols(symbols, vaddr, limit=8) if vaddr is not None else []
    disasm_file = None
    selected_instruction = None
    addr2line_file = None
    addr2line_text = ""
    if vaddr is not None:
        start = max(0, vaddr - window)
        stop = vaddr + window
        disasm = run_tool([
            tools["objdump"],
            "-d",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{stop:x}",
            str(elf),
        ], timeout=30)
        disasm_file = write_tool_result(store, f"host/objdump-{name}-window.txt", disasm)
        selected_instruction = instruction_line(disasm.stdout, vaddr)
        addr2line = run_tool([tools["addr2line"], "-f", "-C", "-e", str(elf), f"0x{vaddr:x}"], timeout=10)
        addr2line_file = write_tool_result(store, f"host/addr2line-{name}.txt", addr2line)
        addr2line_text = addr2line.stdout.strip()
    return {
        "name": name,
        "offset": f"0x{offset:x}",
        "mapped_vaddr": f"0x{vaddr:x}" if vaddr is not None else None,
        "section": section,
        "nearest_symbols": near,
        "selected_instruction": selected_instruction,
        "addr2line": addr2line_text,
        "addr2line_file": addr2line_file,
        "disassembly_file": disasm_file,
    }


def analyze_elf(store: EvidenceStore, elf: Path, offsets: dict[str, int], window: int) -> dict[str, Any]:
    readelf = choose_tool("aarch64-linux-gnu-readelf", "readelf")
    objdump = choose_tool("aarch64-linux-gnu-objdump", "llvm-objdump", "objdump")
    addr2line = choose_tool("aarch64-linux-gnu-addr2line", "addr2line")
    file_tool = choose_tool("file")
    if readelf is None or objdump is None or addr2line is None:
        raise RuntimeError("readelf/objdump/addr2line tools are required")
    tools = {"readelf": readelf, "objdump": objdump, "addr2line": addr2line}
    elf = repo_path(elf)
    if not elf.exists():
        raise RuntimeError(f"libc ELF not found: {elf}")
    max_offset = max(offsets.values()) if offsets else 0
    if elf.stat().st_size <= max_offset:
        raise RuntimeError(f"offset 0x{max_offset:x} is beyond ELF size {elf.stat().st_size}")

    tool_outputs: dict[str, str] = {}
    if file_tool:
        tool_outputs["file"] = write_tool_result(store, "host/file-libc.txt", run_tool([file_tool, str(elf)], timeout=10))
    tool_outputs["readelf_headers"] = write_tool_result(store, "host/readelf-headers.txt", run_tool([readelf, "-W", "-h", "-l", "-n", str(elf)], timeout=20))
    tool_outputs["readelf_sections"] = write_tool_result(store, "host/readelf-sections.txt", run_tool([readelf, "-W", "-S", str(elf)], timeout=20))
    tool_outputs["readelf_symbols"] = write_tool_result(store, "host/readelf-symbols.txt", run_tool([readelf, "-W", "-s", str(elf)], timeout=30))
    return {
        "elf_path": str(elf),
        "elf_size": elf.stat().st_size,
        "elf_sha256": sha256_file(elf),
        "tool_outputs": tool_outputs,
        "offsets": [analyze_one_offset(store, elf, name, offset, window, tools) for name, offset in offsets.items()],
    }


def guardrails() -> list[str]:
    return [
        "read-only system mount through mountsystem ro only",
        "optional libc pull uses toybox base64 from an allowlisted path",
        "no Android daemon execution",
        "no Wi-Fi HAL/start/scan/connect",
        "no rfkill write",
        "no credential collection",
        "no system or vendor write",
        "host output directory/files are private",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# Native Init v391 Service-Manager Libc Symbolization",
        "",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- run_log: `{manifest.get('run_log', '')}`",
        f"- pull_from_device: `{manifest.get('pull_from_device', False)}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Offsets",
        "",
    ]
    for name, offset in manifest.get("offsets", {}).items():
        lines.append(f"- `{name}`: `{offset}`")
    analysis = manifest.get("elf_analysis") or {}
    if analysis:
        lines.extend([
            "",
            "## ELF",
            "",
            f"- path: `{analysis.get('elf_path')}`",
            f"- size: `{analysis.get('elf_size')}`",
            f"- sha256: `{analysis.get('elf_sha256')}`",
            "",
            "## Symbolization",
            "",
        ])
        for item in analysis.get("offsets", []):
            section = item.get("section") or {}
            lines.extend([
                f"### {item.get('name')}",
                "",
                f"- offset: `{item.get('offset')}`",
                f"- mapped_vaddr: `{item.get('mapped_vaddr')}`",
                f"- section: `{section.get('name') if isinstance(section, dict) else None}`",
                f"- selected_instruction: `{item.get('selected_instruction')}`",
                f"- addr2line: `{item.get('addr2line')}`",
                f"- disassembly: `{item.get('disassembly_file')}`",
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


def plan_command(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifest = {
        "generated_at": now_iso(),
        "command": "plan",
        "pass": True,
        "decision": "service-manager-libc-symbolization-plan-ready",
        "reason": "plan written; no device command or ELF access attempted",
        "host": collect_host_metadata(),
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "guardrails": guardrails(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"PASS out_dir={out_dir} decision={manifest['decision']}")
    return 0


def analyze_command(args: argparse.Namespace) -> int:
    if args.pull_from_device and args.no_pull:
        raise RuntimeError("--pull-from-device and --no-pull are mutually exclusive")
    out_dir = repo_path(args.out_dir)
    reset_private_dir(out_dir)
    store = EvidenceStore(out_dir)
    run_log = repo_path(args.run_log)
    values = parse_key_values(run_log.read_text(encoding="utf-8", errors="replace"))
    offsets_int = {name: offset for name in ("pc", "lr") if (offset := maprow_offset(values, name)) is not None}
    device_captures: list[dict[str, Any]] = []
    libc_elf = repo_path(args.libc_elf) if args.libc_elf else None
    pull_error = None
    if libc_elf is None and args.pull_from_device:
        libc_elf, device_captures, pull_error = pull_libc_from_device(store, args)

    elf_analysis = None
    analysis_error = None
    if libc_elf is not None:
        try:
            elf_analysis = analyze_elf(store, libc_elf, offsets_int, args.window)
        except Exception as exc:  # noqa: BLE001 - report keeps analysis failure reason
            analysis_error = str(exc)

    if len(offsets_int) < 2:
        decision = "service-manager-libc-symbolization-blocked-no-maprow"
        reason = "V390 PC/LR map-row offsets are missing"
        pass_ok = False
        remaining = ["crash-maprow"]
    elif elf_analysis is None:
        decision = "service-manager-libc-symbolization-blocked-no-elf"
        reason = analysis_error or pull_error or "matching libc ELF was not provided or pulled"
        pass_ok = False
        remaining = ["libc-elf"]
    else:
        has_disasm = all(item.get("selected_instruction") for item in elf_analysis.get("offsets", []))
        has_symbol = any(item.get("nearest_symbols") for item in elf_analysis.get("offsets", []))
        if has_disasm and has_symbol:
            decision = "service-manager-libc-symbolization-pass"
            reason = "PC/LR offsets mapped to libc sections, nearest symbols, and disassembly context"
        elif has_disasm:
            decision = "service-manager-libc-disassembled-no-symbol"
            reason = "PC/LR offsets mapped to libc disassembly, but symbols are stripped or unavailable"
        else:
            decision = "service-manager-libc-symbolization-partial"
            reason = "libc ELF was available but disassembly context is incomplete"
        pass_ok = True
        remaining = []

    manifest = {
        "generated_at": now_iso(),
        "command": "analyze",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "next_step": "use symbol/disassembly result to plan targeted servicemanager runtime repair",
        "run_log": str(run_log),
        "offsets": {name: f"0x{offset:x}" for name, offset in offsets_int.items()},
        "remote_libc": args.remote_libc,
        "pull_from_device": args.pull_from_device,
        "pull_error": pull_error,
        "analysis_error": analysis_error,
        "device_captures": device_captures,
        "elf_analysis": elf_analysis,
        "remaining_blockers": remaining,
        "guardrails": guardrails(),
        "host": collect_host_metadata(),
        "device_commands_executed": bool(device_captures),
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
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
