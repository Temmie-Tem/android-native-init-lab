#!/usr/bin/env python3
"""Host-only parser/symbolizer for V392 service-manager frame-chain evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path
from a90harness.evidence import EvidenceStore
from wifi_service_manager_crash_symbolize import parse_key_values


DEFAULT_OUT_DIR = Path("tmp/wifi/service-manager-framechain-analyze")
FRAME_RETURN_RE = re.compile(r"^capture\.crash\.framechain\.(\d+)\.return_addr$")


@dataclass
class FrameTarget:
    index: int
    fp: str
    next_fp: str
    return_addr_raw: str
    return_addr: str
    maprow_found: bool
    maprow_path: str
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
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("analyze")
    return parser.parse_args()


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
    candidates: list[Path] = []
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


def frame_indexes(values: dict[str, str]) -> list[int]:
    indexes = set()
    for key in values:
        match = FRAME_RETURN_RE.match(key)
        if match:
            indexes.add(int(match.group(1)))
    return sorted(indexes)


def symbolize_frame(args: argparse.Namespace, values: dict[str, str], index: int) -> FrameTarget:
    frame_prefix = f"capture.crash.framechain.{index}."
    map_prefix = f"capture.crash.maprow.frame{index}_ra."
    maprow_found = values.get(map_prefix + "found") == "1"
    maprow_path = values.get(map_prefix + "path", "")
    relative_offset = normalize_hex(values.get(map_prefix + "relative_offset", ""))
    return_addr = normalize_hex(values.get(frame_prefix + "return_addr", ""))
    elf = resolve_elf(maprow_path, args.elf_root)
    symbol = ""
    source = ""
    error = ""
    if not maprow_found:
        error = "maprow-not-found"
    elif elf is None:
        error = "elf-not-available"
    elif not relative_offset:
        error = "relative-offset-missing"
    else:
        symbol_text, symbol_error = run_text([args.addr2line, "-f", "-C", "-e", str(elf), relative_offset])
        if symbol_error:
            error = symbol_error
        else:
            lines = symbol_text.splitlines()
            symbol = lines[0] if lines else ""
            source = lines[1] if len(lines) > 1 else ""
    return FrameTarget(
        index=index,
        fp=normalize_hex(values.get(frame_prefix + "fp", "")),
        next_fp=normalize_hex(values.get(frame_prefix + "next_fp", "")),
        return_addr_raw=normalize_hex(values.get(frame_prefix + "return_addr_raw", "")),
        return_addr=return_addr,
        maprow_found=maprow_found,
        maprow_path=maprow_path,
        relative_offset=relative_offset,
        elf=str(elf) if elf is not None else "",
        symbol=symbol,
        source=source,
        error=error,
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    run_log = repo_path(args.run_log)
    values = parse_key_values(run_log.read_text(encoding="utf-8", errors="replace"))
    indexes = frame_indexes(values)
    frames = [symbolize_frame(args, values, index) for index in indexes]
    frame_count_text = values.get("capture.crash.framechain.count", "")
    framechain_present = bool(indexes) or bool(frame_count_text)
    maprows_present = bool(frames) and any(frame.maprow_found for frame in frames)
    symbols_present = any(frame.symbol for frame in frames)
    if symbols_present:
        decision = "service-manager-framechain-symbolization-pass"
        next_step = "inspect symbolized caller and plan targeted runtime repair"
        remaining: list[str] = []
    elif maprows_present:
        decision = "service-manager-framechain-maprow-ready"
        next_step = "provide matching ELF roots or pull the mapped frame return-address libraries"
        remaining = ["frame-elf-artifact"]
    elif framechain_present:
        decision = "service-manager-framechain-no-maprow"
        next_step = "inspect framechain stop reason and raw return addresses"
        remaining = ["frame-return-maprow"]
    else:
        decision = "service-manager-framechain-needs-v392-live"
        next_step = "run V392 backchain capture live smoke"
        remaining = ["v392-framechain-evidence"]
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": True,
        "run_log": str(run_log),
        "host": collect_host_metadata(),
        "framechain_present": framechain_present,
        "frame_count_reported": frame_count_text,
        "frame_indexes": indexes,
        "frames": [asdict(frame) for frame in frames],
        "maprows_present": maprows_present,
        "symbols_present": symbols_present,
        "remaining_blockers": remaining,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# Service-Manager Framechain Analyze",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- run_log: `{manifest['run_log']}`",
        f"- framechain_present: `{manifest['framechain_present']}`",
        f"- frame_count_reported: `{manifest['frame_count_reported']}`",
        f"- maprows_present: `{manifest['maprows_present']}`",
        f"- symbols_present: `{manifest['symbols_present']}`",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Frames",
        "",
    ]
    for frame in manifest["frames"]:
        lines.append(
            f"- `frame{frame['index']}` fp=`{frame['fp']}` next_fp=`{frame['next_fp']}` "
            f"ra=`{frame['return_addr']}` offset=`{frame['relative_offset']}` "
            f"path=`{frame['maprow_path']}` symbol=`{frame['symbol']}` error=`{frame['error']}`"
        )
    if not manifest["frames"]:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"framechain_present: {manifest['framechain_present']}")
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
