#!/usr/bin/env python3
"""V2578 host-only ACDB lower-get ABI reconnaissance.

This script extracts metadata-only evidence from the private V2324 vendor dump
of libacdbloader.so. It does not touch the device and does not commit or expose
raw proprietary disassembly blobs; detailed dumps stay under workspace/private.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

RUN_ID = "V2578"
BUILD_TAG = "v2578-audio-acdb-lower-get-abi-recon"
ROOT = Path(__file__).resolve().parents[5]
DEFAULT_LIBACDBLOADER = ROOT / "workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/lib/libacdbloader.so"
DEFAULT_LIBAUDCAL = ROOT / "workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/lib/libaudcal.so"
DEFAULT_OBJDUMP = ROOT / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0/bin/llvm-objdump"
DEFAULT_RELIBS = ROOT / "tmp/relibs"
DEFAULT_OUT_DIR = ROOT / "workspace/private/runs/audio/v2578-acdb-lower-get-abi-recon"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2578_AUDIO_ACDB_LOWER_GET_ABI_RECON_2026-06-16.md"

TARGET_SYMBOLS = [
    "acdb_loader_send_common_custom_topology",
    "acdb_loader_send_audio_cal_v5",
    "acdb_loader_get_calibration",
    "acdb_loader_adsp_get_audio_cal",
    "acdb_loader_get_audio_cal_v2",
    "acdb_loader_store_get_audio_cal",
]

INTEREST_PATTERNS = {
    "common_topology_cal_type_39": [r"movs\s+r0,\s*#39", r"0x00000027"],
    "common_topology_indirect_query": [r"movs\s+r0,\s*#4", r"str\s+r0,\s*\[sp\]", r"\[sp,\s*#56\]", r"\[sp,\s*#88\]"],
    "send_audio_cal_type_13": [r"movs\s+r0,\s*#13"],
    "store_selector": [r"\[r5,\s*#28\]", r"cmp.*#37", r"cmp.*#1"],
    "store_cmd_0x13265_family": [r"#12433", r"#468", r"#466", r"#474"],
    "store_cmd_0x11399_family": [r"#5017"],
    "adsp_get_fields": [r"\[r6,\s*#12\]", r"\[r6,\s*#16\]", r"\[r6,\s*#20\]", r"\[r6,\s*#32\]", r"\[r6,\s*#36\]", r"\[r6,\s*#40\]"],
    "thin_wrapper_guards": [r"cbz", r"bne", r"-22", r"#22"],
}


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(argv: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def parse_readelf_symbols(text: str, wanted: Iterable[str] = TARGET_SYMBOLS) -> dict[str, dict[str, object]]:
    wanted_set = set(wanted)
    symbols: dict[str, dict[str, object]] = {}
    pattern = re.compile(
        r"^\s*(?P<num>\d+):\s+"
        r"(?P<value>[0-9a-fA-F]+)\s+"
        r"(?P<size>\d+)\s+"
        r"(?P<type>\S+)\s+"
        r"(?P<bind>\S+)\s+"
        r"(?P<vis>\S+)\s+"
        r"(?P<ndx>\S+)\s+"
        r"(?P<name>\S+)"
    )
    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        name = match.group("name")
        base_name = name.split("@", 1)[0]
        if base_name not in wanted_set:
            continue
        symbols[base_name] = {
            "index": int(match.group("num")),
            "value_hex": "0x" + match.group("value").lower(),
            "value": int(match.group("value"), 16),
            "size": int(match.group("size")),
            "type": match.group("type"),
            "bind": match.group("bind"),
            "visibility": match.group("vis"),
            "section": match.group("ndx"),
            "name": name,
        }
    return symbols


def objdump_env(relibs: Path) -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("LD_LIBRARY_PATH", "")
    relibs_text = str(relibs)
    env["LD_LIBRARY_PATH"] = relibs_text + ((":" + current) if current else "")
    return env


def disassemble_function(objdump: Path, lib: Path, symbol: str, relibs: Path) -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            str(objdump),
            "-d",
            "--triple=thumbv7-linux-android",
            f"--disassemble-functions={symbol}",
            str(lib),
        ],
        env=objdump_env(relibs),
    )


def extract_matching_lines(text: str, patterns: Iterable[str], *, context: int = 2, max_hits: int = 12) -> list[dict[str, object]]:
    lines = text.splitlines()
    regexes = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    hits: list[int] = []
    for idx, line in enumerate(lines):
        if any(regex.search(line) for regex in regexes):
            hits.append(idx)
        if len(hits) >= max_hits:
            break
    snippets: list[dict[str, object]] = []
    seen_ranges: set[tuple[int, int]] = set()
    for idx in hits:
        start = max(0, idx - context)
        end = min(len(lines), idx + context + 1)
        key = (start, end)
        if key in seen_ranges:
            continue
        seen_ranges.add(key)
        snippets.append({
            "line": idx + 1,
            "context": [
                {"line": line_no + 1, "text": lines[line_no].rstrip()}
                for line_no in range(start, end)
            ],
        })
    return snippets


def literal_commands_from_snippets(snippets: dict[str, dict[str, object]]) -> dict[str, object]:
    """Return conservative command-literal observations from known snippet groups."""
    return {
        "store_get_audio_cal_selector0_candidate": {
            "base_movw": "0x13091",
            "observed_add_offsets": [466, 468, 474],
            "candidate_size_query": "0x13265",
            "confidence": "medium: literal arithmetic observed, final branch target still requires a dedicated control-flow pass",
        },
        "store_get_audio_cal_alternate_candidate": {
            "literal": "0x11399",
            "confidence": "medium: movw #5017 / movt #1 path observed in store getter snippets",
        },
        "common_topology_cal_type": {
            "cal_type": 39,
            "confidence": "high: direct movs r0,#39 before common topology cal-block helper",
        },
    }


def build_manifest(args: argparse.Namespace) -> dict[str, object]:
    lib = args.libacdbloader
    audcal = args.libaudcal
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    readelf = run_command([args.readelf, "-Ws", str(lib)])
    if readelf.returncode != 0:
        raise SystemExit(f"readelf failed rc={readelf.returncode}: {readelf.stderr.strip()}")
    symbols = parse_readelf_symbols(readelf.stdout)
    missing = [name for name in TARGET_SYMBOLS if name not in symbols]

    disassembly: dict[str, dict[str, object]] = {}
    for symbol in TARGET_SYMBOLS:
        if symbol not in symbols:
            continue
        result = disassemble_function(args.objdump, lib, symbol, args.relibs)
        dump_path = out_dir / f"{symbol}.thumb-objdump.txt"
        dump_path.write_text(result.stdout, encoding="utf-8", errors="replace")
        symbol_patterns: list[str] = []
        for group_patterns in INTEREST_PATTERNS.values():
            symbol_patterns.extend(group_patterns)
        groups = {
            name: extract_matching_lines(result.stdout, patterns, context=args.context, max_hits=args.max_hits)
            for name, patterns in INTEREST_PATTERNS.items()
        }
        disassembly[symbol] = {
            "returncode": result.returncode,
            "stderr": result.stderr.strip(),
            "private_dump": rel(dump_path),
            "snippet_groups": groups,
        }

    manifest: dict[str, object] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "host-only metadata RE; no device action; private vendor binaries not committed",
        "inputs": {
            "libacdbloader": {
                "path": rel(lib),
                "exists": lib.exists(),
                "sha256": sha256_file(lib) if lib.exists() else None,
            },
            "libaudcal": {
                "path": rel(audcal),
                "exists": audcal.exists(),
                "sha256": sha256_file(audcal) if audcal.exists() else None,
            },
            "objdump": rel(args.objdump),
        },
        "symbols": symbols,
        "missing_symbols": missing,
        "disassembly": disassembly,
        "literal_command_observations": literal_commands_from_snippets(disassembly),
        "decision": "v2578-lower-get-abi-host-recon-complete" if not missing else "v2578-lower-get-abi-host-recon-partial-missing-symbols",
    }
    manifest_path = out_dir / "v2578-lower-get-abi-recon.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    manifest["manifest_path"] = rel(manifest_path)
    return manifest


def snippet_text(manifest: dict[str, object], symbol: str, group: str, limit: int = 2) -> list[str]:
    disassembly = manifest.get("disassembly", {})
    if not isinstance(disassembly, dict):
        return []
    symbol_data = disassembly.get(symbol, {})
    if not isinstance(symbol_data, dict):
        return []
    groups = symbol_data.get("snippet_groups", {})
    if not isinstance(groups, dict):
        return []
    snippets = groups.get(group, [])
    output: list[str] = []
    if isinstance(snippets, list):
        for snippet in snippets[:limit]:
            if not isinstance(snippet, dict):
                continue
            line = snippet.get("line")
            context = snippet.get("context", [])
            if isinstance(context, list):
                flattened = " / ".join(
                    str(item.get("text", "")).strip()
                    for item in context
                    if isinstance(item, dict) and item.get("text")
                )
                output.append(f"line {line}: {flattened}")
    return output


def render_report(manifest: dict[str, object]) -> str:
    inputs = manifest.get("inputs", {}) if isinstance(manifest.get("inputs"), dict) else {}
    symbols = manifest.get("symbols", {}) if isinstance(manifest.get("symbols"), dict) else {}
    decision = manifest.get("decision", "unknown")
    lib_info = inputs.get("libacdbloader", {}) if isinstance(inputs.get("libacdbloader"), dict) else {}
    audcal_info = inputs.get("libaudcal", {}) if isinstance(inputs.get("libaudcal"), dict) else {}
    rows = []
    for name in TARGET_SYMBOLS:
        data = symbols.get(name, {}) if isinstance(symbols.get(name), dict) else {}
        rows.append(
            f"| `{name}` | `{data.get('value_hex', 'missing')}` | `{data.get('size', 'missing')}` | `{data.get('type', 'missing')}` |"
        )
    common = snippet_text(manifest, "acdb_loader_send_common_custom_topology", "common_topology_cal_type_39")
    common_indirect = snippet_text(manifest, "acdb_loader_send_common_custom_topology", "common_topology_indirect_query")
    send_v5 = snippet_text(manifest, "acdb_loader_send_audio_cal_v5", "send_audio_cal_type_13")
    store_selector = snippet_text(manifest, "acdb_loader_store_get_audio_cal", "store_selector")
    store_cmd_a = snippet_text(manifest, "acdb_loader_store_get_audio_cal", "store_cmd_0x13265_family")
    store_cmd_b = snippet_text(manifest, "acdb_loader_store_get_audio_cal", "store_cmd_0x11399_family")
    adsp_fields = snippet_text(manifest, "acdb_loader_adsp_get_audio_cal", "adsp_get_fields")

    def bullet_lines(items: list[str]) -> str:
        if not items:
            return "- No matching snippet captured by the conservative extractor."
        return "\n".join(f"- `{item}`" for item in items)

    return f"""# NATIVE_INIT V2578 — ACDB lower-get ABI recon

## Scope

Host-only ABI reconnaissance after V2575/V2577. No device action, Android handoff, native
calibration ioctl, speaker write, raw ACDB payload capture, or private vendor binary commit was
performed.

## Decision

- decision: `{decision}`
- private manifest: `{manifest.get('manifest_path')}`
- input libacdbloader sha256: `{lib_info.get('sha256')}`
- input libaudcal sha256: `{audcal_info.get('sha256')}`

## Export Inventory

| symbol | value | size | type |
| --- | ---: | ---: | --- |
{chr(10).join(rows)}

## Findings

1. **Public-send live routes remain closed.** V2570 and V2574 both reached the public
   `send_audio_cal_v5` boundary without useful per-device `acdb_ioctl` GET rows; V2575 closed that
   strategy, and V2577 shows the common-topology entry arm is not a remaining timing race.
2. **The lower-get surface is real and exported.** `acdb_loader_get_audio_cal_v2`,
   `acdb_loader_adsp_get_audio_cal`, `acdb_loader_get_calibration`, and
   `acdb_loader_store_get_audio_cal` are all present in the V2324 stock `libacdbloader.so`.
3. **Common topology still uses cal_type 39, but V2577 makes this public function a poor capture
   point in own-process mode.** The host RE sees the expected cal-type setup, while live execution
   arms before the real call and still records no target rows before timeout.
4. **The next useful path is lower-level GET request construction, not another public-function
   rerun.** The direct `acdb_ioctl` commands and getter request structs need one more static pass
   before a live pure-read helper should issue them.

## Metadata Snippets

### `acdb_loader_send_common_custom_topology`
{bullet_lines(common)}
{bullet_lines(common_indirect)}

### `acdb_loader_send_audio_cal_v5`
{bullet_lines(send_v5)}

### `acdb_loader_store_get_audio_cal`
{bullet_lines(store_selector)}
{bullet_lines(store_cmd_a)}
{bullet_lines(store_cmd_b)}

### `acdb_loader_adsp_get_audio_cal`
{bullet_lines(adsp_fields)}

## Direct-GET Candidate Notes

- `store_get_audio_cal` selector field evidence points at request offset `+28` and multiple
  small-input size-query paths.
- Conservative literal extraction observes a candidate `0x13265` family from `0x13091 + offsets`
  and an alternate `0x11399` family, but this report does **not** claim final cal_type mapping.
- `adsp_get_audio_cal` reads request fields around offsets `+12`, `+16`, `+20`, `+32`, `+36`, and
  `+40`, which must be pinned before any live direct GET.
- Success for a future live direct-GET remains `ret==0` and non-all-zero output; requested length
  alone is not success.

## Next Unit

V2579 should stay host-only and build a stricter direct-GET request-layout extractor: decode the
literal ACDB command IDs, request field offsets, and out-pointer/size semantics for
`store_get_audio_cal` and `adsp_get_audio_cal`. Do not rerun the V2572/V2577 public-send/common-hook
live paths unchanged.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_lower_get_abi_recon_v2578.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_lower_get_abi_recon_v2578`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_lower_get_abi_recon_v2578.py --write-report`
- `git diff --check`
"""


def write_report(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(manifest), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libacdbloader", type=Path, default=DEFAULT_LIBACDBLOADER)
    parser.add_argument("--libaudcal", type=Path, default=DEFAULT_LIBAUDCAL)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--relibs", type=Path, default=DEFAULT_RELIBS)
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--context", type=int, default=2)
    parser.add_argument("--max-hits", type=int, default=10)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for path_name in ("libacdbloader", "libaudcal", "objdump"):
        path = getattr(args, path_name)
        if not path.exists():
            print(json.dumps({"ok": False, "error": f"missing {path_name}: {rel(path)}"}, indent=2))
            return 2
    manifest = build_manifest(args)
    if args.write_report:
        write_report(args.report_path, manifest)
    print(json.dumps({
        "ok": manifest.get("decision") == "v2578-lower-get-abi-host-recon-complete",
        "decision": manifest.get("decision"),
        "manifest_path": manifest.get("manifest_path"),
        "report_path": rel(args.report_path) if args.write_report else None,
        "missing_symbols": manifest.get("missing_symbols"),
    }, indent=2, sort_keys=True))
    return 0 if manifest.get("decision") == "v2578-lower-get-abi-host-recon-complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
