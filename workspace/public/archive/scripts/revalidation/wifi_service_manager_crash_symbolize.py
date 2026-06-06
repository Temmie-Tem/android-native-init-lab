#!/usr/bin/env python3
"""Host-only parser/symbolizer for service-manager crash map-row evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/service-manager-crash-symbolize")


@dataclass
class SymbolTarget:
    name: str
    addr: str
    found: bool
    path: str
    relative_offset: str
    elf: str
    symbol: str
    source: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--run-log", type=Path, required=True)
    parser.add_argument("--elf-root", type=Path, action="append", default=[])
    parser.add_argument("--addr2line", default="aarch64-linux-gnu-addr2line")
    parser.add_argument("--readelf", default="aarch64-linux-gnu-readelf")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("analyze")
    return parser.parse_args()


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def normalize_hex(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if value.startswith(("0x", "0X")):
        return value
    return f"0x{value}"


def resolve_elf(path: str, roots: list[Path]) -> Path | None:
    if not path:
        return None
    raw = Path(path)
    candidates = []
    if raw.is_absolute():
        for root in roots:
            candidates.append(repo_path(root) / str(raw).lstrip("/"))
    else:
        candidates.extend(repo_path(root) / raw for root in roots)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def run_text(command: list[str]) -> tuple[str, str]:
    try:
        result = subprocess.run(
            command,
            cwd=repo_path(Path(".")),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001 - evidence should preserve host failures
        return "", str(exc)
    if result.returncode != 0:
        return "", result.stdout.strip() or f"rc={result.returncode}"
    return result.stdout.strip(), ""


def symbolize_target(args: argparse.Namespace, values: dict[str, str], name: str) -> SymbolTarget:
    prefix = f"capture.crash.maprow.{name}."
    found = values.get(prefix + "found") == "1"
    path = values.get(prefix + "path", "")
    relative_offset = normalize_hex(values.get(prefix + "relative_offset", ""))
    addr = normalize_hex(values.get(prefix + "addr", ""))
    elf = resolve_elf(path, args.elf_root)
    if not found:
        return SymbolTarget(name, addr, False, path, relative_offset, "", "", "", "maprow-not-found")
    if elf is None:
        return SymbolTarget(name, addr, True, path, relative_offset, "", "", "", "elf-not-available")
    if not relative_offset:
        return SymbolTarget(name, addr, True, path, relative_offset, str(elf), "", "", "relative-offset-missing")
    symbol_text, symbol_error = run_text([args.addr2line, "-f", "-C", "-e", str(elf), relative_offset])
    if symbol_error:
        return SymbolTarget(name, addr, True, path, relative_offset, str(elf), "", "", symbol_error)
    lines = symbol_text.splitlines()
    symbol = lines[0] if lines else ""
    source = lines[1] if len(lines) > 1 else ""
    return SymbolTarget(name, addr, True, path, relative_offset, str(elf), symbol, source, "")


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    run_log = repo_path(args.run_log)
    text = run_log.read_text(encoding="utf-8", errors="replace")
    values = parse_key_values(text)
    targets = [symbolize_target(args, values, "pc"), symbolize_target(args, values, "lr")]
    maprows_present = all(target.found for target in targets)
    symbols_present = any(target.symbol for target in targets)
    errors = [target.error for target in targets if target.error]
    if symbols_present:
        decision = "service-manager-crash-symbolization-pass"
        next_step = "inspect symbolized fatal path and plan targeted runtime repair"
        remaining = []
    elif maprows_present:
        decision = "service-manager-crash-symbolization-maprow-ready"
        next_step = "provide matching Android ELF root or use map offsets manually"
        remaining = ["elf-artifact"]
    else:
        decision = "service-manager-crash-symbolization-needs-maprow"
        next_step = "run V390 crash map capture live smoke"
        remaining = ["crash-maprow"]
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": True,
        "run_log": str(run_log),
        "host": collect_host_metadata(),
        "targets": [asdict(target) for target in targets],
        "maprows_present": maprows_present,
        "symbols_present": symbols_present,
        "remaining_blockers": remaining,
        "errors": errors,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# Service-Manager Crash Symbolize",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- run_log: `{manifest['run_log']}`",
        f"- maprows_present: `{manifest['maprows_present']}`",
        f"- symbols_present: `{manifest['symbols_present']}`",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Targets",
        "",
    ]
    for target in manifest["targets"]:
        lines.append(
            f"- `{target['name']}` found=`{target['found']}` addr=`{target['addr']}` "
            f"offset=`{target['relative_offset']}` path=`{target['path']}` "
            f"symbol=`{target['symbol']}` error=`{target['error']}`"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"maprows_present: {manifest['maprows_present']}")
    print(f"symbols_present: {manifest['symbols_present']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
