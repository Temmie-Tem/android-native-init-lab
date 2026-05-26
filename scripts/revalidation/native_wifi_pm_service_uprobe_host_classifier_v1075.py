#!/usr/bin/env python3
"""V1075 host-only pm-service uprobe candidate classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v1075-pm-service-uprobe-host-classifier")
DEFAULT_EXTRACT_DIR = Path("tmp/wifi/v1073-host-only/vendor-extract/files")
DEFAULT_KERNEL_CONFIG = Path("tmp/kernel-config/v202-kernel-config.json")
DEFAULT_KERNEL_CONFIG_TEXTS = (
    Path("tmp/wifi/v770-instrumented-diagnostic-boot-staging/base-ikconfig.txt"),
    Path("tmp/wifi/v281-icnss-probe-expectation/captures/run-zcat-proc-config.txt"),
    Path("tmp/wifi/v282-icnss-wlfw-readiness-surface/captures/run-zcat-proc-config.txt"),
)

ENTRY_RE = re.compile(r"Entry point address:\s+0x([0-9a-fA-F]+)")
NEEDED_RE = re.compile(r"Shared library: \[([^\]]+)\]")
DYNSYM_RE = re.compile(r"^\s*\d+:\s+([0-9a-fA-F]+)\s+\d+\s+FUNC\s+\S+\s+\S+\s+(\S+)\s+(.+)$")
PLT_RE = re.compile(r"^([0-9a-fA-F]+)\s+<(.+?)@plt>:")
RELATIVE_RE = re.compile(r"^\s*([0-9a-fA-F]+)\s+\S+\s+R_AARCH64_RELATIVE\s+([0-9a-fA-F]+)\b")
ADRP_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+[0-9a-fA-F]+\s+adrp\s+x2,\s*([0-9a-fA-F]+)")
LDR_X2_RE = re.compile(r"^\s*([0-9a-fA-F]+):\s+[0-9a-fA-F]+\s+ldr\s+x2,\s*\[x2,\s*#(\d+)\]")

CRITICAL_IMPORT_PATTERNS = {
    "android_log": "__android_log_print",
    "binder_driver": "_ZN7android12ProcessState14initWithDriverEPKc",
    "binder_service_manager": "_ZN7android21defaultServiceManagerEv",
    "mdmdetect_system_info": "get_system_info",
    "qmi_csi_register": "qmi_csi_register_with_options",
    "qmi_csi_event_loop": "qmi_csi_handle_event",
    "property_set": "property_set",
    "pipe": "pipe",
    "access": "access",
    "open": "__open_2",
    "select": "select",
    "write": "write",
    "close": "close",
}

IMPORTANT_STRINGS = [
    "Failed to get system information",
    "Failed to init peripheral",
    "Adding Peripheral Manager service fail",
    "QMI service start",
    "QMI service select error",
    "QMI service process event error",
    "/dev/vndbinder",
    "vendor.qcom.PeripheralManager",
    "vendor.peripheral.",
]

KERNEL_KEYS = (
    "CONFIG_UPROBES",
    "CONFIG_UPROBE_EVENTS",
    "CONFIG_BPF_EVENTS",
    "CONFIG_BPF_SYSCALL",
    "CONFIG_BPF_JIT",
    "CONFIG_KPROBES",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def repo_path(path: Path | str) -> Path:
    return Path(path).resolve() if Path(path).is_absolute() else Path.cwd() / path


def run_command(command: list[str], *, timeout: float = 20.0) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + "\n[TIMEOUT]\n"
        return -1, output


def symbol_base(name: str) -> str:
    return name.split("@", 1)[0].strip()


def parse_entry(readelf_header: str) -> int | None:
    match = ENTRY_RE.search(readelf_header)
    return int(match.group(1), 16) if match else None


def parse_needed(readelf_dynamic: str) -> list[str]:
    return NEEDED_RE.findall(readelf_dynamic)


def parse_imports(readelf_symbols: str) -> list[str]:
    imports: list[str] = []
    for line in readelf_symbols.splitlines():
        match = DYNSYM_RE.match(line)
        if not match:
            continue
        ndx = match.group(2)
        name = symbol_base(match.group(3))
        if ndx == "UND" and name not in imports:
            imports.append(name)
    return imports


def parse_plt(objdump_plt: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for line in objdump_plt.splitlines():
        match = PLT_RE.match(line.strip())
        if match:
            out[symbol_base(match.group(2))] = int(match.group(1), 16)
    return out


def parse_relative_relocations(readelf_relocs: str) -> dict[int, int]:
    out: dict[int, int] = {}
    for line in readelf_relocs.splitlines():
        match = RELATIVE_RE.match(line)
        if match:
            out[int(match.group(1), 16)] = int(match.group(2), 16)
    return out


def infer_libc_init_target(entry_disasm: str, relocs: dict[int, int]) -> dict[str, Any]:
    adrp_base: int | None = None
    ldr_offset: int | None = None
    ldr_pc: int | None = None
    for line in entry_disasm.splitlines():
        adrp = ADRP_RE.match(line)
        if adrp:
            adrp_base = int(adrp.group(2), 16)
            continue
        ldr = LDR_X2_RE.match(line)
        if ldr and adrp_base is not None:
            ldr_pc = int(ldr.group(1), 16)
            ldr_offset = int(ldr.group(2), 10)
            break
    if adrp_base is None or ldr_offset is None:
        return {"found": False, "reason": "entry-x2-ldr-not-found"}
    relocation_addr = adrp_base + ldr_offset
    target = relocs.get(relocation_addr)
    return {
        "found": target is not None,
        "entry_ldr_pc": f"0x{ldr_pc:x}" if ldr_pc is not None else None,
        "relocation_addr": f"0x{relocation_addr:x}",
        "target_offset": f"0x{target:x}" if target is not None else None,
        "aligned4": bool(target is not None and target % 4 == 0),
    }


def collect_strings(binary: Path) -> dict[str, dict[str, Any]]:
    rc, output = run_command(["strings", "-a", "-tx", str(binary)])
    results: dict[str, dict[str, Any]] = {}
    for needle in IMPORTANT_STRINGS:
        rows = []
        for line in output.splitlines():
            if needle.lower() in line.lower():
                rows.append(line.strip())
        results[needle] = {"present": bool(rows), "matches": rows[:8]}
    return {"rc": rc, "needles": results}


def parse_kernel_config_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        for key in KERNEL_KEYS:
            if stripped == f"{key}=y":
                values[key] = "y"
            elif stripped == f"# {key} is not set":
                values[key] = "n"
    return values


def load_kernel_config(path: Path, text_paths: list[Path]) -> dict[str, str]:
    merged: dict[str, str] = {}
    if path.exists():
        data = json.loads(path.read_text())
        for category in data.get("categories", []):
            opts = category.get("options") or {}
            for key in KERNEL_KEYS:
                if key in opts:
                    merged[key] = opts[key]
        for capture in data.get("captures", []):
            text_values = parse_kernel_config_text(capture.get("text") or "")
            for key, value in text_values.items():
                merged.setdefault(key, value)
    for text_path in text_paths:
        if not text_path.exists():
            continue
        text_values = parse_kernel_config_text(text_path.read_text())
        for key, value in text_values.items():
            merged.setdefault(key, value)
    return merged


def classify(args: argparse.Namespace) -> dict[str, Any]:
    extract_dir = repo_path(args.extract_dir)
    binary = repo_path(args.binary) if args.binary else extract_dir / "pm-service"
    kernel_config_path = repo_path(args.kernel_config)
    kernel_config_text_paths = [repo_path(path) for path in args.kernel_config_text]
    if not binary.exists():
        return {
            "decision": "v1075-pm-service-binary-missing",
            "pass": False,
            "reason": f"missing binary: {binary}",
            "next_step": "provide vendor pm-service extract before uprobe planning",
        }

    commands: dict[str, dict[str, Any]] = {}
    for name, command in {
        "file": ["file", str(binary)],
        "readelf_header": ["readelf", "-h", str(binary)],
        "readelf_dynamic": ["readelf", "-d", str(binary)],
        "readelf_symbols": ["readelf", "-sW", str(binary)],
        "readelf_relocs": ["readelf", "-rW", str(binary)],
        "objdump_plt": ["aarch64-linux-gnu-objdump", "-d", "-j", ".plt", str(binary)],
    }.items():
        rc, output = run_command(command)
        commands[name] = {"command": command, "rc": rc, "output": output}

    header = commands["readelf_header"]["output"]
    dynamic = commands["readelf_dynamic"]["output"]
    symbols = commands["readelf_symbols"]["output"]
    relocs_text = commands["readelf_relocs"]["output"]
    objdump_plt = commands["objdump_plt"]["output"]
    entry = parse_entry(header)
    relocs = parse_relative_relocations(relocs_text)
    entry_start = max(0, (entry or 0) - 0x40)
    entry_stop = (entry or 0) + 0x80
    _, entry_disasm = run_command([
        "aarch64-linux-gnu-objdump",
        "-d",
        str(binary),
        f"--start-address=0x{entry_start:x}",
        f"--stop-address=0x{entry_stop:x}",
    ])
    commands["entry_disasm"] = {"command": ["aarch64-linux-gnu-objdump", "-d", str(binary), f"--start-address=0x{entry_start:x}", f"--stop-address=0x{entry_stop:x}"], "rc": 0, "output": entry_disasm}

    needed = parse_needed(dynamic)
    imports = parse_imports(symbols)
    plt = parse_plt(objdump_plt)
    libc_init_target = infer_libc_init_target(entry_disasm, relocs)
    string_hits = collect_strings(binary)
    kernel_config = load_kernel_config(kernel_config_path, kernel_config_text_paths)

    candidates: list[dict[str, Any]] = []
    if entry is not None:
        candidates.append({"label": "elf_entry", "offset": f"0x{entry:x}", "aligned4": entry % 4 == 0, "kind": "entry"})
    if libc_init_target.get("found"):
        candidates.append({
            "label": "libc_init_main_candidate",
            "offset": libc_init_target["target_offset"],
            "aligned4": libc_init_target["aligned4"],
            "kind": "function-entry",
        })
    for label, symbol in CRITICAL_IMPORT_PATTERNS.items():
        offset = plt.get(symbol)
        candidates.append({
            "label": label,
            "symbol": symbol,
            "offset": f"0x{offset:x}" if offset is not None else None,
            "aligned4": bool(offset is not None and offset % 4 == 0),
            "kind": "plt-call",
            "present": offset is not None,
        })

    missing_critical = [c["label"] for c in candidates if c.get("kind") == "plt-call" and not c.get("present")]
    unaligned = [c for c in candidates if c.get("offset") and not c.get("aligned4")]
    config_ready = all(kernel_config.get(key) == "y" for key in ("CONFIG_UPROBES", "CONFIG_UPROBE_EVENTS", "CONFIG_BPF_EVENTS", "CONFIG_BPF_SYSCALL"))
    kprobes_disabled = kernel_config.get("CONFIG_KPROBES") == "n"
    decisive_strings = all(string_hits["needles"][needle]["present"] for needle in (
        "Failed to get system information",
        "Failed to init peripheral",
        "Adding Peripheral Manager service fail",
        "/dev/vndbinder",
        "vendor.qcom.PeripheralManager",
    ))

    passed = bool(binary.exists() and entry is not None and not unaligned and config_ready and decisive_strings)
    decision = "v1075-pm-service-uprobe-host-classified" if passed else "v1075-pm-service-uprobe-host-review"
    reason = (
        "pm-service is stripped PIE but has aligned entry/main and critical PLT uprobe candidates; "
        "kernel config supports uprobes/BPF events while kprobes remain unavailable"
        if passed else
        f"missing_critical={missing_critical} unaligned={len(unaligned)} config_ready={config_ready} decisive_strings={decisive_strings}"
    )
    next_step = (
        "V1076 implement bounded uprobe/BPF helper for pm-service entry/main/get_system_info/qmi/binder/log callsites"
        if passed else
        "repair missing binary/config/candidate data before building uprobe helper"
    )

    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "binary": str(binary),
        "binary_size": binary.stat().st_size,
        "file": commands["file"]["output"].strip(),
        "entry_offset": f"0x{entry:x}" if entry is not None else None,
        "libc_init_target": libc_init_target,
        "needed": needed,
        "imports_interesting": [name for name in imports if any(token in name for token in ("qmi", "ProcessState", "defaultServiceManager", "property", "open", "access", "select", "write", "close", "log", "get_system_info"))],
        "candidate_uprobes": candidates,
        "missing_critical": missing_critical,
        "unaligned_candidates": unaligned,
        "string_hits": string_hits,
        "kernel_config_path": str(kernel_config_path),
        "kernel_config_text_paths": [str(path) for path in kernel_config_text_paths],
        "kernel_config": kernel_config,
        "config_ready": config_ready,
        "kprobes_disabled": kprobes_disabled,
        "commands": {name: {"command": value["command"], "rc": value["rc"]} for name, value in commands.items()},
        "raw_outputs": commands,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = []
    for candidate in manifest.get("candidate_uprobes", []):
        rows.append(
            f"| {candidate.get('label')} | {candidate.get('kind')} | {candidate.get('symbol', '')} | {candidate.get('offset')} | {candidate.get('aligned4')} |"
        )
    return "\n".join([
        "# V1075 PM Service Uprobe Host Classifier",
        "",
        f"- generated: `{manifest.get('generated_at')}`",
        f"- decision: `{manifest.get('decision')}`",
        f"- pass: `{manifest.get('pass')}`",
        f"- reason: {manifest.get('reason')}",
        f"- next_step: `{manifest.get('next_step')}`",
        f"- binary: `{manifest.get('binary')}`",
        f"- entry_offset: `{manifest.get('entry_offset')}`",
        f"- libc_init_target: `{manifest.get('libc_init_target')}`",
        "",
        "## Candidate Uprobes",
        "",
        "| label | kind | symbol | offset | aligned4 |",
        "| --- | --- | --- | --- | --- |",
        *rows,
        "",
        "## Kernel Config",
        "",
        f"- config_ready: `{manifest.get('config_ready')}`",
        f"- values: `{manifest.get('kernel_config')}`",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--extract-dir", type=Path, default=DEFAULT_EXTRACT_DIR)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--kernel-config", type=Path, default=DEFAULT_KERNEL_CONFIG)
    parser.add_argument(
        "--kernel-config-text",
        type=Path,
        action="append",
        default=None,
        help="Additional raw /proc/config.gz text capture to fill truncated JSON keys.",
    )
    args = parser.parse_args()
    if args.kernel_config_text is None:
        args.kernel_config_text = list(DEFAULT_KERNEL_CONFIG_TEXTS)

    store = EvidenceStore(repo_path(args.out_dir))
    manifest = classify(args)
    raw_outputs = manifest.pop("raw_outputs", {})
    for name, payload in raw_outputs.items():
        store.write_text(f"host/{name}.txt", payload.get("output", ""))
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.path('manifest.json')}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
