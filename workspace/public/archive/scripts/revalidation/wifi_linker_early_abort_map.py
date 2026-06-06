#!/usr/bin/env python3
"""Map Android linker __early_abort call sites and abort codes.

v237 proved that the v236 linker crash lands in bionic's intentional
``__early_abort`` trap.  This host-side tool expands that result: it scans the
matching linker64 ELF for every call into ``__early_abort``, recovers the
constant loaded into ``w0`` before the call, and matches the captured fault
address/abort code to the exact caller.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import stat
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, ensure_private_dir


DEFAULT_OUT_DIR = Path("tmp/wifi/v238-linker-early-abort-map")
DEFAULT_V237_MANIFEST = Path("tmp/wifi/v237-linker-offset-symbolize-live/manifest.json")
DEFAULT_LINKER_ELF = Path("tmp/wifi/v237-linker-offset-symbolize-live/files/linker64")
EARLY_ABORT_SYMBOL = "__dl__ZL13__early_aborti"
INSTRUCTION_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{8})\s+(.+?)\s*$")
FUNCTION_RE = re.compile(r"^([0-9a-fA-F]+)\s+<([^>]+)>:$")
MOV_W0_RE = re.compile(r"\bmov\s+w0,\s*#(0x[0-9a-fA-F]+|\d+)\b")
BL_RE = re.compile(r"\bbl\s+[0-9a-fA-Fx]+\s+<([^>]+)>")


@dataclass
class Instruction:
    address: int
    bytes_text: str
    text: str
    function: str
    function_start: int
    raw: str


@dataclass
class AbortCall:
    call_site: int
    function: str
    function_start: int
    function_delta: int
    abort_code: int | None
    mov_site: int | None
    call_instruction: str
    context_file: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=repo_path(DEFAULT_OUT_DIR))
    parser.add_argument("--v237-manifest", type=Path, default=repo_path(DEFAULT_V237_MANIFEST))
    parser.add_argument("--linker-elf", type=Path, default=repo_path(DEFAULT_LINKER_ELF))
    parser.add_argument("--fault-addr", default=None, help="override captured fault addr, e.g. 0xa1")
    parser.add_argument("--context", type=int, default=14, help="instruction lines before/after each call site")
    parser.add_argument("--tool-timeout", type=int, default=45)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan", help="write v238 plan-only evidence")
    subparsers.add_parser("analyze", help="map __early_abort callers from a local linker64 ELF")
    return parser.parse_args()


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


def run_tool(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def write_tool_result(store: EvidenceStore, rel: str, result: subprocess.CompletedProcess[str]) -> str:
    text = (
        "$ " + " ".join(result.args if isinstance(result.args, list) else [str(result.args)]) + "\n"
        f"# rc={result.returncode}\n"
        "## stdout\n"
        + result.stdout
        + ("\n" if result.stdout and not result.stdout.endswith("\n") else "")
        + "## stderr\n"
        + result.stderr
    )
    path = store.write_text(rel, text)
    return str(path.relative_to(store.run_dir))


def load_manifest(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def parse_hex_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value), 0)
    except ValueError:
        return None


def infer_fault_addr(args: argparse.Namespace, v237: dict[str, Any]) -> int | None:
    override = parse_hex_or_none(args.fault_addr)
    if override is not None:
        return override
    for case in v237.get("crash_cases", []):
        if not isinstance(case, dict):
            continue
        fault_addr = parse_hex_or_none(case.get("fault_addr"))
        if fault_addr is not None:
            return fault_addr
    return None


def parse_disassembly(text: str) -> list[Instruction]:
    instructions: list[Instruction] = []
    current_function = "<unknown>"
    current_function_start = 0
    for line in text.splitlines():
        stripped = line.strip()
        function_match = FUNCTION_RE.match(stripped)
        if function_match:
            current_function_start = int(function_match.group(1), 16)
            current_function = function_match.group(2)
            continue
        instruction_match = INSTRUCTION_RE.match(line)
        if not instruction_match:
            continue
        instructions.append(
            Instruction(
                address=int(instruction_match.group(1), 16),
                bytes_text=instruction_match.group(2),
                text=instruction_match.group(3).strip(),
                function=current_function,
                function_start=current_function_start,
                raw=line.rstrip(),
            )
        )
    return instructions


def find_abort_mov(instructions: list[Instruction], index: int) -> tuple[int | None, int | None]:
    call_function = instructions[index].function
    for prev in reversed(instructions[max(0, index - 20):index]):
        if prev.function != call_function:
            continue
        match = MOV_W0_RE.search(prev.text)
        if match:
            return int(match.group(1), 0), prev.address
    return None, None


def write_context(store: EvidenceStore, instructions: list[Instruction], index: int, context: int) -> str:
    start = max(0, index - context)
    stop = min(len(instructions), index + context + 1)
    call_addr = instructions[index].address
    lines: list[str] = []
    for item in instructions[start:stop]:
        marker = "=> " if item.address == call_addr else "   "
        lines.append(f"{marker}{item.raw}")
    path = store.write_text(f"host/callsite-0x{call_addr:x}.txt", "\n".join(lines) + "\n")
    return str(path.relative_to(store.run_dir))


def extract_calls(store: EvidenceStore, disasm: str, context: int) -> list[AbortCall]:
    instructions = parse_disassembly(disasm)
    calls: list[AbortCall] = []
    for index, instruction in enumerate(instructions):
        match = BL_RE.search(instruction.text)
        if not match:
            continue
        if match.group(1) != EARLY_ABORT_SYMBOL:
            continue
        abort_code, mov_site = find_abort_mov(instructions, index)
        calls.append(
            AbortCall(
                call_site=instruction.address,
                function=instruction.function,
                function_start=instruction.function_start,
                function_delta=instruction.address - instruction.function_start,
                abort_code=abort_code,
                mov_site=mov_site,
                call_instruction=instruction.raw.strip(),
                context_file=write_context(store, instructions, index, context),
            )
        )
    return calls


def parse_strings_for_context(strings_text: str) -> dict[str, Any]:
    needles = (
        "/dev/null",
        "/sys/fs/selinux/null",
        "expected /dev/null fd",
        "__dl_libc_init_common.cpp",
        "__dl__Z21__libc_init_AT_SECUREPPc",
    )
    hits: dict[str, list[str]] = {}
    for line in strings_text.splitlines():
        for needle in needles:
            if needle in line:
                hits.setdefault(needle, []).append(line.strip())
    return {
        "hits": hits,
        "has_dev_null": "/dev/null" in hits,
        "has_selinux_null": "/sys/fs/selinux/null" in hits,
        "has_libc_init_source": "__dl_libc_init_common.cpp" in hits,
        "has_at_secure_symbol": "__dl__Z21__libc_init_AT_SECUREPPc" in hits,
    }


def calls_to_manifest(calls: list[AbortCall]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call in calls:
        rows.append({
            **asdict(call),
            "call_site": f"0x{call.call_site:x}",
            "function_start": f"0x{call.function_start:x}",
            "function_delta": f"0x{call.function_delta:x}",
            "abort_code": f"0x{call.abort_code:x}" if call.abort_code is not None else None,
            "abort_code_dec": call.abort_code,
            "mov_site": f"0x{call.mov_site:x}" if call.mov_site is not None else None,
        })
    return rows


def classify(
    calls: list[AbortCall],
    fault_addr: int | None,
    strings_context: dict[str, Any],
) -> tuple[bool, str, str, AbortCall | None]:
    if not calls:
        return False, "linker-early-abort-map-blocked-no-calls", "no __early_abort call sites found", None
    if fault_addr is None:
        return False, "linker-early-abort-map-blocked-no-fault-code", "no captured fault address/abort code was available", None
    selected = next((call for call in calls if call.abort_code == fault_addr), None)
    if selected is None:
        return False, "linker-early-abort-code-unmapped", f"no call site passed abort code 0x{fault_addr:x}", None
    if (
        selected.function == "__dl__Z21__libc_init_AT_SECUREPPc"
        and fault_addr == 0xA1
        and strings_context.get("has_dev_null")
        and strings_context.get("has_selinux_null")
    ):
        return (
            True,
            "linker-early-abort-dev-null-open-failed",
            "abort code 0xa1 maps to __libc_init_AT_SECURE stdio nullification path; linker strings contain /dev/null and /sys/fs/selinux/null",
            selected,
        )
    return True, "linker-early-abort-code-mapped", f"abort code 0x{fault_addr:x} mapped to one __early_abort caller", selected


def build_plan_summary() -> str:
    return "\n".join([
        "# v238 Linker Early-Abort Call-Site Map",
        "",
        "- purpose: map v236 fault address `0xa1` to the exact `__early_abort` caller in the v237 linker64 ELF",
        "- input: `tmp/wifi/v237-linker-offset-symbolize-live/files/linker64`",
        "- no device access is required when v237 ELF evidence is present",
        "- blocked actions: Android daemon start, Wi-Fi scan/connect, rfkill writes, Android partition writes",
        "",
        "## Commands",
        "",
        "```bash",
        "python3 scripts/revalidation/wifi_linker_early_abort_map.py analyze",
        "```",
        "",
    ])


def build_summary(manifest: dict[str, Any]) -> str:
    calls = manifest.get("calls", [])
    selected = manifest.get("selected_call")
    rows = [
        [
            item["call_site"],
            item["function"],
            item["function_delta"],
            item["abort_code"],
            str(item["abort_code_dec"]),
            item.get("mov_site"),
        ]
        for item in calls
    ]
    lines = [
        "# Native Init v238 Linker Early-Abort Map",
        "",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- fault_addr: `{manifest.get('fault_addr')}`",
        f"- linker_elf: `{manifest.get('linker_elf')}`",
        "",
        "## Call Sites",
        "",
        markdown_table(
            ["call", "function", "delta", "abort code", "decimal", "mov site"],
            rows or [["none", "none", "none", "none", "none", "none"]],
        ),
        "",
        "## Selected Caller",
        "",
    ]
    if isinstance(selected, dict):
        lines.extend([
            f"- call_site: `{selected['call_site']}`",
            f"- function: `{selected['function']}`",
            f"- function_delta: `{selected['function_delta']}`",
            f"- abort_code: `{selected['abort_code']}` / `{selected['abort_code_dec']}`",
            f"- mov_site: `{selected.get('mov_site')}`",
            f"- context: `{selected['context_file']}`",
            "",
        ])
    else:
        lines.extend(["- no selected caller", ""])

    string_hits = manifest.get("strings_context", {}).get("hits", {})
    lines.extend([
        "## String Context",
        "",
    ])
    for key in sorted(string_hits):
        for value in string_hits[key]:
            lines.append(f"- `{value}`")
    if not string_hits:
        lines.append("- no matching strings")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- v237 mapped the crash instruction to `__early_abort+0x14`, where the linker writes through the abort-code address.",
        "- v238 maps captured fault address `0xa1` to the caller that passes `0xa1` to `__early_abort`.",
        "- The selected caller sits in `__libc_init_AT_SECURE`; AOSP bionic uses this path to ensure stdio fds are backed by `/dev/null` or `/sys/fs/selinux/null` before normal output is safe.",
        "- Next validation should materialize or bind minimal `/dev/null` inside the private Android execution namespace, then rerun the linker `--list` probe.",
        "",
        "## Guardrails",
        "",
    ])
    for item in manifest["guardrails"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def guardrails() -> list[str]:
    return [
        "host-side ELF/disassembly analysis only",
        "no device command execution",
        "no Android daemon execution",
        "no Wi-Fi scan/connect",
        "no rfkill write",
        "no credential collection",
        "no system/vendor write",
        "host output directory/files are private",
    ]


def plan_command(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "v238-plan",
        "pass": True,
        "decision": "linker-early-abort-map-plan-ready",
        "reason": "plan written; no device or ELF access attempted",
        "host_metadata": collect_host_metadata(),
        "guardrails": guardrails(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_plan_summary())
    print(f"PASS out_dir={out_dir} decision={manifest['decision']}")
    return 0


def analyze_command(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    reset_private_dir(out_dir)
    store = EvidenceStore(out_dir)
    objdump = choose_tool("aarch64-linux-gnu-objdump", "llvm-objdump", "objdump")
    strings_tool = choose_tool("strings")
    if objdump is None or strings_tool is None:
        raise RuntimeError("objdump and strings are required")

    linker_elf = repo_path(args.linker_elf)
    if not linker_elf.exists():
        raise RuntimeError(f"linker ELF not found: {linker_elf}")
    v237 = load_manifest(args.v237_manifest)
    fault_addr = infer_fault_addr(args, v237)

    disasm_result = run_tool([objdump, "-d", str(linker_elf)], timeout=args.tool_timeout)
    disasm_file = write_tool_result(store, "host/objdump-linker64.txt", disasm_result)
    if disasm_result.returncode != 0:
        raise RuntimeError(f"objdump failed rc={disasm_result.returncode}")
    strings_result = run_tool([strings_tool, "-a", "-tx", str(linker_elf)], timeout=args.tool_timeout)
    strings_file = write_tool_result(store, "host/strings-linker64.txt", strings_result)
    if strings_result.returncode != 0:
        raise RuntimeError(f"strings failed rc={strings_result.returncode}")

    calls = extract_calls(store, disasm_result.stdout, args.context)
    strings_context = parse_strings_for_context(strings_result.stdout)
    pass_ok, decision, reason, selected = classify(calls, fault_addr, strings_context)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": "v238-linker-early-abort-map",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "linker_elf": str(linker_elf),
        "v237_manifest": str(repo_path(args.v237_manifest)),
        "v237_decision": v237.get("decision"),
        "fault_addr": f"0x{fault_addr:x}" if fault_addr is not None else None,
        "fault_addr_dec": fault_addr,
        "calls": calls_to_manifest(calls),
        "selected_call": calls_to_manifest([selected])[0] if selected is not None else None,
        "strings_context": strings_context,
        "tool_outputs": {
            "objdump": disasm_file,
            "strings": strings_file,
        },
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
