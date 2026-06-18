#!/usr/bin/env python3
"""V2683 host-only bridge analysis for ACDB core vs subsystem topology payloads.

Parses the captured CORE_CUSTOM_TOPOLOGIES payload (cal_type 39) and the
subsystem fixed-record payloads (cal_types 14/24) to determine whether the
missing selected ASM/ADM topology IDs exist in the core graph and can be
represented in the fixed subsystem topology payload grammar.

Raw generated candidate payloads are written only under workspace/private when
--write-candidates is passed; public output is metadata-only.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import struct
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parents[5]

CORE_PAYLOAD = REPO / "workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin"
CAL14_PAYLOAD = REPO / "workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431/ownget-device-artifacts/setcal-dmabuf-p00000f67-s00000002-cal0000000e-len00000934.bin"
CAL24_PAYLOAD = REPO / "workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431/ownget-device-artifacts/setcal-dmabuf-p00000f67-s00000001-cal00000018-len0000049c.bin"
REPORT = REPO / "docs/reports/NATIVE_INIT_V2683_AUDIO_ACDB_CORE_TO_FIXED_TOPOLOGY_BRIDGE_2026-06-18.md"
CANDIDATE_DIR = REPO / "workspace/private/builds/audio/v2683-acdb-core-topology-candidates"
MODULE_HEADER = REPO / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/4.0/include/dsp/apr_audio-v2.h"

FIXED_RECORD_U32 = 98
FIXED_MODULE_SLOTS = 16
FIXED_SLOT_U32 = 6
TARGETS = {
    0x10005000: {"role": "selected ASM topology from cal13", "candidate_cal_type": 14},
    0x10004000: {"role": "selected ADM topology from cal9", "candidate_cal_type": 10},
    0x1001025D: {"role": "selected AFE topology from cal23", "candidate_cal_type": 24},
}


@dataclasses.dataclass(frozen=True)
class CoreRecord:
    index: int
    word_offset: int
    domain: int
    topology_id: int
    version: int
    modules: tuple[tuple[int, int], ...]


@dataclasses.dataclass(frozen=True)
class FixedRecord:
    index: int
    topology_id: int
    modules: tuple[tuple[int, int], ...]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def u32_words(data: bytes) -> tuple[int, ...]:
    if len(data) % 4 != 0:
        raise ValueError(f"payload length is not u32-aligned: {len(data)}")
    return struct.unpack("<" + "I" * (len(data) // 4), data)


def pack_words(words: Iterable[int]) -> bytes:
    values = tuple(words)
    return struct.pack("<" + "I" * len(values), *values)


def parse_core_payload(data: bytes) -> list[CoreRecord]:
    words = u32_words(data)
    if not words:
        raise ValueError("empty core payload")
    count = words[0]
    pos = 1
    records: list[CoreRecord] = []
    for index in range(count):
        if pos + 4 > len(words):
            raise ValueError(f"truncated core record header at index {index}")
        domain, topology_id, version, module_count = words[pos:pos + 4]
        if module_count > 64:
            raise ValueError(f"implausible core module count {module_count} at index {index}")
        end = pos + 4 + module_count * 2
        if end > len(words):
            raise ValueError(f"truncated core modules at index {index}")
        modules = tuple((words[pos + 4 + n * 2], words[pos + 5 + n * 2]) for n in range(module_count))
        records.append(CoreRecord(index, pos, domain, topology_id, version, modules))
        pos = end
    if pos != len(words):
        raise ValueError(f"core payload trailing words: parsed={pos} total={len(words)}")
    return records


def parse_fixed_payload(data: bytes) -> list[FixedRecord]:
    words = u32_words(data)
    if not words:
        raise ValueError("empty fixed payload")
    count = words[0]
    expected = 1 + count * FIXED_RECORD_U32
    if expected != len(words):
        raise ValueError(f"fixed payload length mismatch: count={count} expected_words={expected} actual_words={len(words)}")
    records: list[FixedRecord] = []
    for index in range(count):
        base = 1 + index * FIXED_RECORD_U32
        rec = words[base:base + FIXED_RECORD_U32]
        topology_id = rec[0]
        module_count = rec[1]
        if module_count > FIXED_MODULE_SLOTS:
            raise ValueError(f"fixed record {index} module_count={module_count} exceeds slots")
        modules: list[tuple[int, int]] = []
        for slot in range(module_count):
            slot_base = 2 + slot * FIXED_SLOT_U32
            module_id = rec[slot_base]
            instance_id = rec[slot_base + 1]
            rest = rec[slot_base + 2:slot_base + FIXED_SLOT_U32]
            if any(rest):
                raise ValueError(f"fixed record {index} slot {slot} has non-zero reserved words")
            modules.append((module_id, instance_id))
        padding_start = 2 + module_count * FIXED_SLOT_U32
        if any(rec[padding_start:]):
            raise ValueError(f"fixed record {index} has non-zero padding")
        records.append(FixedRecord(index, topology_id, tuple(modules)))
    return records


def fixed_payload_from_core(records: Iterable[CoreRecord]) -> bytes:
    selected = list(records)
    words: list[int] = [len(selected)]
    for record in selected:
        if len(record.modules) > FIXED_MODULE_SLOTS:
            raise ValueError(f"topology 0x{record.topology_id:08x} has {len(record.modules)} modules, exceeds fixed slots")
        rec = [0] * FIXED_RECORD_U32
        rec[0] = record.topology_id
        rec[1] = len(record.modules)
        for slot, (module_id, instance_id) in enumerate(record.modules):
            slot_base = 2 + slot * FIXED_SLOT_U32
            rec[slot_base] = module_id
            rec[slot_base + 1] = instance_id
        words.extend(rec)
    return pack_words(words)


def load_module_names(header: Path) -> dict[int, str]:
    names: dict[int, str] = {}
    if not header.exists():
        return names
    import re
    pattern = re.compile(r"^\s*#define\s+([A-Za-z0-9_]*MODULE[A-Za-z0-9_]*)\s+(0x[0-9A-Fa-f]+|[0-9]+)\b")
    for line in header.read_text(errors="ignore").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        name, raw = match.groups()
        try:
            value = int(raw, 0)
        except ValueError:
            continue
        old = names.get(value)
        if old is None or ("_MODULE_ID_" in name and "_MODULE_ID_" not in old) or len(name) < len(old):
            names[value] = name
    return names


def module_list(modules: Iterable[tuple[int, int]], names: dict[int, str]) -> str:
    parts = []
    for module_id, instance_id in modules:
        label = names.get(module_id, "unknown")
        parts.append(f"`0x{module_id:08x}`/`0x{instance_id:08x}` ({label})")
    return ", ".join(parts) if parts else "none"


def summarize(args: argparse.Namespace) -> dict:
    core_data = args.core_payload.read_bytes()
    cal14_data = args.cal14_payload.read_bytes()
    cal24_data = args.cal24_payload.read_bytes()
    core_records = parse_core_payload(core_data)
    fixed14 = parse_fixed_payload(cal14_data)
    fixed24 = parse_fixed_payload(cal24_data)
    core_by_topology = {record.topology_id: record for record in core_records}
    fixed_by_cal = {
        14: fixed14,
        24: fixed24,
    }
    fixed_topologies = {cal: [record.topology_id for record in records] for cal, records in fixed_by_cal.items()}
    fixed_module_matches = []
    for cal, records in fixed_by_cal.items():
        for fixed in records:
            core = core_by_topology.get(fixed.topology_id)
            fixed_module_matches.append({
                "cal_type": cal,
                "topology_id": fixed.topology_id,
                "core_present": core is not None,
                "module_pairs_match_core": core.modules == fixed.modules if core else False,
                "duplicate_in_fixed": sum(1 for other in records if other.topology_id == fixed.topology_id) > 1,
            })
    candidates = []
    candidate_dir = args.candidate_dir
    if args.write_candidates:
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate_dir.chmod(0o700)
    for topology_id, meta in TARGETS.items():
        core = core_by_topology.get(topology_id)
        if not core:
            candidates.append({
                "topology_id": topology_id,
                "candidate_cal_type": meta["candidate_cal_type"],
                "role": meta["role"],
                "core_present": False,
            })
            continue
        payload = fixed_payload_from_core([core])
        candidate_name = f"cal{meta['candidate_cal_type']:02d}-topology-0x{topology_id:08x}-from-core-fixed.bin"
        candidate_path = candidate_dir / candidate_name
        if args.write_candidates:
            candidate_path.write_bytes(payload)
            candidate_path.chmod(0o600)
        candidates.append({
            "topology_id": topology_id,
            "candidate_cal_type": meta["candidate_cal_type"],
            "role": meta["role"],
            "core_present": True,
            "core_index": core.index,
            "core_word_offset": core.word_offset,
            "module_count": len(core.modules),
            "payload_len": len(payload),
            "payload_sha256": sha256(payload),
            "private_candidate_path": str(candidate_path.relative_to(REPO)) if args.write_candidates else None,
        })
    current_plus = []
    if 0x10005000 in core_by_topology:
        existing_unique: list[CoreRecord] = []
        seen = set()
        for fixed in fixed14:
            if fixed.topology_id in core_by_topology and fixed.topology_id not in seen:
                existing_unique.append(core_by_topology[fixed.topology_id])
                seen.add(fixed.topology_id)
        if 0x10005000 not in seen:
            existing_unique.append(core_by_topology[0x10005000])
        payload = fixed_payload_from_core(existing_unique)
        candidate_path = candidate_dir / "cal14-current-unique-plus-0x10005000-from-core-fixed.bin"
        if args.write_candidates:
            candidate_path.write_bytes(payload)
            candidate_path.chmod(0o600)
        current_plus.append({
            "name": "cal14-current-unique-plus-0x10005000",
            "topologies": [record.topology_id for record in existing_unique],
            "payload_len": len(payload),
            "payload_sha256": sha256(payload),
            "private_candidate_path": str(candidate_path.relative_to(REPO)) if args.write_candidates else None,
        })
    return {
        "decision": "v2683-core-to-fixed-topology-bridge-candidates",
        "core_payload": {
            "path": str(args.core_payload.relative_to(REPO)),
            "len": len(core_data),
            "sha256": sha256(core_data),
            "record_count": len(core_records),
        },
        "subsystem_payloads": {
            "cal14": {"path": str(args.cal14_payload.relative_to(REPO)), "len": len(cal14_data), "sha256": sha256(cal14_data), "topologies": fixed_topologies[14]},
            "cal24": {"path": str(args.cal24_payload.relative_to(REPO)), "len": len(cal24_data), "sha256": sha256(cal24_data), "topologies": fixed_topologies[24]},
        },
        "core_records": core_records,
        "fixed14": fixed14,
        "fixed24": fixed24,
        "fixed_module_matches": fixed_module_matches,
        "candidates": candidates,
        "current_plus_candidates": current_plus,
        "candidate_dir": str(candidate_dir.relative_to(REPO)) if args.write_candidates else None,
        "module_names": load_module_names(args.module_header),
        "write_candidates": args.write_candidates,
    }


def table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    header = rows[0]
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out.extend("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |" for row in rows[1:])
    return "\n".join(out)


def markdown(summary: dict) -> str:
    names = summary["module_names"]
    core_by_topology = {record.topology_id: record for record in summary["core_records"]}
    lines = [
        "# NATIVE_INIT V2683 — ACDB core-to-fixed topology bridge",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only analysis. No device action, flash, audio ioctl, PCM probe, or raw committed payload occurred.",
        "Generated candidate payload bytes, when requested, are written only under `workspace/private/`.",
        "",
        "## Result",
        "",
        f"- decision: `{summary['decision']}`",
        f"- core payload records parsed: `{summary['core_payload']['record_count']}`",
        f"- core payload SHA-256: `{summary['core_payload']['sha256']}`",
        f"- write_candidates: `{summary['write_candidates']}`",
    ]
    if summary["candidate_dir"]:
        lines.append(f"- private candidate dir: `{summary['candidate_dir']}`")
    lines.extend(["", "## Target topology records in core payload", ""])
    rows = [["topology", "role", "candidate cal_type", "core offset", "modules", "module list"]]
    for cand in summary["candidates"]:
        tid = cand["topology_id"]
        if not cand.get("core_present"):
            rows.append([f"`0x{tid:08x}`", cand["role"], str(cand["candidate_cal_type"]), "missing", "0", "missing"])
            continue
        core = core_by_topology[tid]
        rows.append([
            f"`0x{tid:08x}`",
            cand["role"],
            str(cand["candidate_cal_type"]),
            f"word `{core.word_offset}`",
            str(len(core.modules)),
            module_list(core.modules, names),
        ])
    lines.append(table(rows))
    lines.extend(["", "## Existing subsystem payload alignment", ""])
    rows = [["cal_type", "topology", "core present", "module pairs match core", "duplicate in fixed payload"]]
    for item in summary["fixed_module_matches"]:
        rows.append([
            str(item["cal_type"]),
            f"`0x{item['topology_id']:08x}`",
            f"`{item['core_present']}`",
            f"`{item['module_pairs_match_core']}`",
            f"`{item['duplicate_in_fixed']}`",
        ])
    lines.append(table(rows))
    lines.extend(["", "## Generated fixed-payload candidates", ""])
    rows = [["candidate", "cal_type", "topology set", "bytes", "sha256", "private path"]]
    for cand in summary["candidates"]:
        if not cand.get("core_present"):
            continue
        rows.append([
            f"minimal-0x{cand['topology_id']:08x}",
            str(cand["candidate_cal_type"]),
            f"`0x{cand['topology_id']:08x}`",
            str(cand["payload_len"]),
            f"`{cand['payload_sha256']}`",
            f"`{cand['private_candidate_path']}`" if cand.get("private_candidate_path") else "not written",
        ])
    for cand in summary["current_plus_candidates"]:
        rows.append([
            cand["name"],
            "14",
            ", ".join(f"`0x{x:08x}`" for x in cand["topologies"]),
            str(cand["payload_len"]),
            f"`{cand['payload_sha256']}`",
            f"`{cand['private_candidate_path']}`" if cand.get("private_candidate_path") else "not written",
        ])
    lines.append(table(rows))
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The missing selected topology IDs are not absent from the ACDB-derived data. They are present in the core `4916`-byte custom topology graph:",
        "",
        "- ASM selected topology `0x10005000` is present in core but absent from the replayed cal_type `14` payload.",
        "- ADM selected topology `0x10004000` is present in core, while no cal_type `10` payload was replayed.",
        "- AFE selected topology `0x1001025d` is present in both core and the replayed cal_type `24` payload, and the module pairs match.",
        "",
        "The current cal_type `14` payload is therefore best classified as a structurally valid lower-hidden subset, not as the selected ASM topology table for app type `0x11135`. The core-to-fixed conversion is mechanically validated by the AFE match: core records and fixed subsystem records share the same `(module_id, instance_id)` pairs, with fixed records adding four zero reserved words per module slot and padding to sixteen slots.",
        "",
        "## Next unit",
        "",
        "Build a V2684 deploy plan that prepends generated cal_type `10` and corrected cal_type `14` fixed-topology candidates before the existing per-device SET sequence, then run the normal V2639 replay path once. Prefer the conservative candidate set first: cal10 minimal `0x10004000` plus cal14 minimal `0x10005000`, leaving cal24 as the captured payload because it already matches `0x1001025d`. If DSP still rejects ASM, try the cal14 current-unique-plus-`0x10005000` candidate as the second bounded branch; do not rerun V2679 unchanged.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_core_topology_bridge_v2683.py tests/test_analyze_audio_acdb_core_topology_bridge_v2683.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_core_topology_bridge_v2683 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_core_topology_bridge_v2683.py --write-candidates --write-report`",
        "- `git diff --check`",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-payload", type=Path, default=CORE_PAYLOAD)
    parser.add_argument("--cal14-payload", type=Path, default=CAL14_PAYLOAD)
    parser.add_argument("--cal24-payload", type=Path, default=CAL24_PAYLOAD)
    parser.add_argument("--candidate-dir", type=Path, default=CANDIDATE_DIR)
    parser.add_argument("--module-header", type=Path, default=MODULE_HEADER)
    parser.add_argument("--write-candidates", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize(args)
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown(summary))
    public = {
        "decision": summary["decision"],
        "core_record_count": summary["core_payload"]["record_count"],
        "candidates": [
            {k: v for k, v in cand.items() if k != "private_candidate_path"}
            for cand in summary["candidates"]
        ],
        "current_plus_candidates": [
            {k: v for k, v in cand.items() if k != "private_candidate_path"}
            for cand in summary["current_plus_candidates"]
        ],
        "write_candidates": summary["write_candidates"],
    }
    if args.json:
        print(json.dumps(public, indent=2, sort_keys=True))
    else:
        print(json.dumps(public, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
