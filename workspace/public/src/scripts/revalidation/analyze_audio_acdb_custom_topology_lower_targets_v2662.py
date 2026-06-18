#!/usr/bin/env python3
"""V2662 host-only libacdbloader lower-target reconnaissance.

V2661 proved existing traces do not already contain SET records for cal_types
10/14/24.  This unit inspects the stock libacdbloader.so metadata to decide
whether the missing per-subsystem custom topology send paths are callable by
symbol, or require direct internal-offset RE before another live capture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import re
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2662"
BUILD_TAG = "v2662-audio-acdb-custom-topology-lower-targets"
DEFAULT_LIB = ROOT / "workspace/private/runs/audio/v2660-acdb-custom-topology-phase-common-setcal-capture-20260618-123009/ownget-device-artifacts/libacdbloader.so"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2662_AUDIO_ACDB_CUSTOM_TOPOLOGY_LOWER_TARGETS_2026-06-18.md"

EXPORTED_REQUIRED = [
    "acdb_loader_init_v3",
    "acdb_loader_send_common_custom_topology",
    "acdb_loader_send_audio_cal_v5",
    "acdb_loader_adsp_set_audio_cal",
    "acdb_loader_store_set_audio_cal",
    "acdb_loader_set_audio_cal_v2",
]
CUSTOM_SEND_NAMES = [
    "send_adm_custom_topology",
    "send_asm_custom_topology",
    "send_afe_custom_topology",
]
CUSTOM_LOG_STRINGS = [
    "ACDB -> send_adm_custom_topology",
    "ACDB -> send_asm_custom_topology",
    "ACDB -> send_afe_custom_topology",
    "ACDB -> AUDIO_SET_ADM_CUSTOM_TOPOLOGY",
    "ACDB -> AUDIO_SET_ASM_CUSTOM_TOPOLOGY",
    "ACDB -> AUDIO_SET_AFE_CUSTOM_TOPOLOGY",
]
DEBUG_SYMBOLS_OF_INTEREST = [
    "allocate_cal_block",
    "create_cal_node",
    "deallocate_cal_block",
    "send_adm_topology",
    "send_afe_topology",
    "send_afe_cal",
]


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_text(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.stdout


def parse_symbol_table(text: str) -> dict[str, dict[str, Any]]:
    symbols: dict[str, dict[str, Any]] = {}
    # Example: 145:   141: 00008cf1  2620 FUNC    GLOBAL DEFAULT   14 name
    pattern = re.compile(
        r"^\s*(?:\d+:)?\s*(?P<num>\d+):\s+"
        r"(?P<value>[0-9a-fA-F]+)\s+(?P<size>\d+)\s+"
        r"(?P<type>\S+)\s+(?P<bind>\S+)\s+(?P<vis>\S+)\s+"
        r"(?P<ndx>\S+)\s+(?P<name>\S+)"
    )
    for line in text.splitlines():
        m = pattern.match(line)
        if not m:
            continue
        name = m.group("name")
        # Drop version suffix for lookups, keep raw too.
        base = name.split("@", 1)[0]
        entry = {
            "name": name,
            "value": int(m.group("value"), 16),
            "value_hex": f"0x{int(m.group('value'), 16):08x}",
            "size": int(m.group("size")),
            "type": m.group("type"),
            "bind": m.group("bind"),
            "visibility": m.group("vis"),
            "section": m.group("ndx"),
        }
        symbols[name] = entry
        symbols.setdefault(base, entry)
    return symbols


def elf32_sections(data: bytes) -> dict[str, dict[str, int]]:
    if data[:4] != b"\x7fELF" or data[4] != 1 or data[5] != 1:
        raise ValueError("expected little-endian ELF32")
    e_shoff = struct.unpack_from("<I", data, 0x20)[0]
    e_shentsize = struct.unpack_from("<H", data, 0x2E)[0]
    e_shnum = struct.unpack_from("<H", data, 0x30)[0]
    e_shstrndx = struct.unpack_from("<H", data, 0x32)[0]
    headers = []
    for idx in range(e_shnum):
        off = e_shoff + idx * e_shentsize
        sh = struct.unpack_from("<IIIIIIIIII", data, off)
        headers.append({
            "name_off": sh[0],
            "type": sh[1],
            "flags": sh[2],
            "addr": sh[3],
            "offset": sh[4],
            "size": sh[5],
            "link": sh[6],
            "info": sh[7],
            "align": sh[8],
            "entsize": sh[9],
        })
    shstr = headers[e_shstrndx]
    names = data[shstr["offset"]:shstr["offset"] + shstr["size"]]
    sections: dict[str, dict[str, int]] = {}
    for sh in headers:
        start = sh["name_off"]
        end = names.find(b"\0", start)
        name = names[start:end].decode("ascii", errors="replace") if end >= start else ""
        sections[name] = {k: int(v) for k, v in sh.items() if k != "name_off"}
    return sections


def extract_gnu_debugdata_symbols(lib_path: Path, readelf: str) -> dict[str, dict[str, Any]]:
    data = lib_path.read_bytes()
    sections = elf32_sections(data)
    sec = sections.get(".gnu_debugdata")
    if not sec:
        return {}
    blob = data[sec["offset"]:sec["offset"] + sec["size"]]
    debug_elf = lzma.decompress(blob)
    with tempfile.NamedTemporaryFile(prefix="a90-libacdbloader-debugdata-", suffix=".elf") as tmp:
        tmp.write(debug_elf)
        tmp.flush()
        return parse_symbol_table(run_text([readelf, "-Ws", tmp.name]))


def string_presence(lib_path: Path, strings_cmd: str) -> dict[str, bool]:
    text = run_text([strings_cmd, "-a", str(lib_path)])
    needles = EXPORTED_REQUIRED + CUSTOM_SEND_NAMES + CUSTOM_LOG_STRINGS + DEBUG_SYMBOLS_OF_INTEREST
    return {needle: needle in text for needle in needles}


def analyze(lib_path: Path, *, readelf: str, strings_cmd: str) -> dict[str, Any]:
    dyn_symbols = parse_symbol_table(run_text([readelf, "-Ws", str(lib_path)]))
    debug_symbols = extract_gnu_debugdata_symbols(lib_path, readelf)
    strings = string_presence(lib_path, strings_cmd)
    exported = {name: dyn_symbols.get(name) for name in EXPORTED_REQUIRED}
    custom_dyn = {name: dyn_symbols.get(name) for name in CUSTOM_SEND_NAMES}
    custom_debug = {name: debug_symbols.get(name) for name in CUSTOM_SEND_NAMES}
    debug_interest = {name: debug_symbols.get(name) for name in DEBUG_SYMBOLS_OF_INTEREST}
    custom_strings = {name: strings.get(name, False) for name in CUSTOM_SEND_NAMES + CUSTOM_LOG_STRINGS}
    lower_set_exports_ready = all(exported.get(name) for name in ["acdb_loader_adsp_set_audio_cal", "acdb_loader_store_set_audio_cal", "acdb_loader_set_audio_cal_v2"])
    direct_custom_symbols_ready = any(custom_dyn.values()) or any(custom_debug.values())
    if direct_custom_symbols_ready:
        decision = "v2662-custom-topology-direct-symbols-present-host-recon"
        next_action = "build direct-symbol helper for ADM/ASM/AFE custom topology sends"
    elif lower_set_exports_ready:
        decision = "v2662-lower-set-exports-present-custom-symbols-hidden-host-recon"
        next_action = "pin lower SET helper argument layout or recover hidden custom function offsets before live capture"
    else:
        decision = "v2662-custom-topology-lower-targets-blocked-no-callable-surface-host-recon"
        next_action = "external disassembly/import of libacdbloader required before another live run"
    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": decision,
        "ok": True,
        "lib_path": rel(lib_path),
        "lib_sha256": sha256_file(lib_path),
        "exported_required": exported,
        "custom_topology_dynamic_symbols": custom_dyn,
        "custom_topology_debug_symbols": custom_debug,
        "custom_topology_strings": custom_strings,
        "debug_symbols_of_interest": debug_interest,
        "lower_set_exports_ready": lower_set_exports_ready,
        "direct_custom_symbols_ready": direct_custom_symbols_ready,
        "operator_value": {
            "custom_send_code_exists_by_strings": all(custom_strings.get(name) for name in CUSTOM_SEND_NAMES),
            "custom_send_functions_are_not_dlsym_callables": not direct_custom_symbols_ready,
            "lower_set_exports_ready": lower_set_exports_ready,
            "next_action": next_action,
        },
        "safety": {
            "host_only": True,
            "device_touched": False,
            "native_replay": False,
            "audio_set_issued": False,
            "raw_bytes_committed": False,
        },
    }


def render_report(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# NATIVE_INIT V2662 — ACDB custom-topology lower-target recon")
    lines.append("")
    lines.append("Date: 2026-06-18")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("Host-only inspection of the stock 32-bit `libacdbloader.so` captured from")
    lines.append("the V2660 Android-good run. No Android boot, device flash, native replay,")
    lines.append("`/dev/msm_audio_cal` ioctl, mixer write, PCM write, or speaker playback occurred.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append(f"- decision: `{summary['decision']}`")
    lines.append(f"- ok: `{summary['ok']}`")
    lines.append(f"- lib_path: `{summary['lib_path']}`")
    lines.append(f"- lib_sha256: `{summary['lib_sha256']}`")
    lines.append(f"- lower_set_exports_ready: `{summary['lower_set_exports_ready']}`")
    lines.append(f"- direct_custom_symbols_ready: `{summary['direct_custom_symbols_ready']}`")
    lines.append("")
    lines.append("## Exported Lower SET Surface")
    lines.append("")
    lines.append("| symbol | present | value | size |")
    lines.append("| --- | --- | --- | ---: |")
    for name, entry in summary["exported_required"].items():
        lines.append(f"| `{name}` | `{bool(entry)}` | `{entry.get('value_hex') if entry else None}` | `{entry.get('size') if entry else None}` |")
    lines.append("")
    lines.append("## Custom Topology Direct Symbols")
    lines.append("")
    lines.append("| function | string present | dynamic symbol | mini-debug symbol |")
    lines.append("| --- | --- | --- | --- |")
    for name in CUSTOM_SEND_NAMES:
        lines.append(
            f"| `{name}` | `{summary['custom_topology_strings'].get(name)}` | "
            f"`{bool(summary['custom_topology_dynamic_symbols'].get(name))}` | "
            f"`{bool(summary['custom_topology_debug_symbols'].get(name))}` |"
        )
    lines.append("")
    lines.append("## Supporting Strings")
    lines.append("")
    for name in CUSTOM_LOG_STRINGS:
        lines.append(f"- `{name}`: `{summary['custom_topology_strings'].get(name)}`")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("The stock loader clearly contains the ADM/ASM/AFE custom-topology code paths:")
    lines.append("all three `send_*_custom_topology` names and their `AUDIO_SET_*_CUSTOM_TOPOLOGY`")
    lines.append("log strings are present. They are not exported dynamic symbols and are not")
    lines.append("named in `.gnu_debugdata`, so a future helper cannot simply `dlsym()` those")
    lines.append("functions. Repeating the V2659/V2660 public common-topology strategy is therefore")
    lines.append("not justified.")
    lines.append("")
    lines.append("The exported lower SET helpers are present (`acdb_loader_adsp_set_audio_cal`,")
    lines.append("`acdb_loader_store_set_audio_cal`, `acdb_loader_set_audio_cal_v2`). The next")
    lines.append("host-only unit should either pin one of those argument layouts for cal_types")
    lines.append("`10/14/24`, or recover hidden custom-function offsets from disassembly before")
    lines.append("any further live capture.")
    lines.append("")
    lines.append("## Validation")
    lines.append("")
    lines.append("- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_lower_targets_v2662.py tests/test_analyze_audio_acdb_custom_topology_lower_targets_v2662.py`")
    lines.append("- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests/test_analyze_audio_acdb_custom_topology_lower_targets_v2662.py -v`")
    lines.append("- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_lower_targets_v2662.py --write-report`")
    lines.append("- `git diff --check`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lib", type=Path, default=DEFAULT_LIB)
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--strings", default="strings")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = analyze(args.lib, readelf=args.readelf, strings_cmd=args.strings)
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
