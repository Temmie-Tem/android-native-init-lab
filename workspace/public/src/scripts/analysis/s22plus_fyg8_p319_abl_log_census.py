#!/usr/bin/env python3
"""Build a closed, deduplicated manifest of the retained bootloader captures.

The P3.19 report first stated its ABL census from three captures, then from
eighty, and an independent review objected that neither population was bounded:
no inclusion criterion, no path list, no hashes, and therefore no way to tell an
omitted capture from an absent one.  This builds the population explicitly.

Inclusion criterion, stated once and applied mechanically: every regular file
under `workspace/private` whose size is exactly 2097136 bytes, the `last_kmsg`
region size this campaign measured.  Nothing is selected by name or by run.

Captures are then deduplicated by SHA-256 before any counting.  That step is not
cosmetic: the retained tree copies the same capture into many run directories,
and counting files rather than contents inflates the population by more than a
factor of two.

SHA-256 identity is *file* identity, not *boot* identity, and an independent
review was right to say so.  A retained buffer can hold several boot rings, so
this also counts the bootloader's own per-boot MUIC banner inside each distinct
file and reports `boot_segments` alongside the file counts.  Where the two
differ, the segment count is the one that means anything about boots.

The same review found that normalising log lines before comparing them hid a
register-value difference, so the per-capture record now carries the raw
`BC_CTRL1_READ` values in file order and a census of the MUIC opcodes, both
uncollapsed.

Host-only.  Reads files already on this host, writes one JSON manifest under
`workspace/private/outputs/`, and contacts no device.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

LAST_KMSG_SIZE = 2097136
ABL_MARK = b"[ ABL ]"
ODIN_MARK = b"Launching odin"
MISSION_MARK = b"Booting Into Mission Mode"
SETPATH_RE = re.compile(rb"SetPath: (\d+)")
SEGMENT_RE = re.compile(rb"MUIC Device : Max77705! count: 0")
BC_CTRL1_RE = re.compile(rb"BC_CTRL1_READ\s*:\s*(0x[0-9A-Fa-f]+)")
OPCODE_RE = re.compile(rb"muic_command_polling: OP (0x[0-9A-Fa-f]{2})")

REPO = Path(__file__).resolve().parents[5]
PRIVATE = REPO / "workspace" / "private"
OUT = PRIVATE / "outputs" / "s22plus_fyg8_p319" / "abl-capture-manifest.json"


def classify(blob: bytes) -> dict:
    setpaths = [m.group(1).decode() for m in SETPATH_RE.finditer(blob)]
    opcodes: dict[str, int] = {}
    for m in OPCODE_RE.finditer(blob):
        key = m.group(1).decode()
        opcodes[key] = opcodes.get(key, 0) + 1
    return {
        "has_abl_stage": ABL_MARK in blob,
        "download_mode": ODIN_MARK in blob,
        "mission_mode": MISSION_MARK in blob,
        "setpath_values": sorted(set(setpaths)),
        "setpath_occurrences": len(setpaths),
        "boot_segments": len(SEGMENT_RE.findall(blob)),
        # In file order and uncollapsed: the difference between 0x00C5 and
        # 0x00E5 is BC_CTRL1 bit 5, BC_CTRL1_NoAutoIBUS, and normalising the
        # digits away is what hid it.
        "bc_ctrl1_reads": [m.group(1).decode() for m in BC_CTRL1_RE.finditer(blob)],
        "muic_opcodes": dict(sorted(opcodes.items())),
    }


def _tally(entries: list[dict], key: str) -> dict:
    out: dict[str, int] = {}
    for entry in entries:
        for value in entry[key]:
            out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items()))


def _opcode_tally(entries: list[dict]) -> dict:
    out: dict[str, int] = {}
    for entry in entries:
        for opcode, count in entry["muic_opcodes"].items():
            out[opcode] = out.get(opcode, 0) + count
    return dict(sorted(out.items()))


def build(private: Path = PRIVATE) -> dict:
    by_digest: dict[str, dict] = {}
    unreadable: list[str] = []
    file_count = 0
    for path in sorted(private.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            if path.stat().st_size != LAST_KMSG_SIZE:
                continue
            blob = path.read_bytes()
        except OSError:
            # Recorded rather than swallowed: an unreadable file of the right
            # size is an unknown, not an exclusion, and the manifest has to say
            # so for the population to be closed.
            unreadable.append(str(path))
            continue
        if len(blob) != LAST_KMSG_SIZE:
            # A sparse or truncated file can report the right st_size.
            unreadable.append(str(path))
            continue
        file_count += 1
        digest = hashlib.sha256(blob).hexdigest()
        rel = str(path.relative_to(REPO))
        if digest in by_digest:
            by_digest[digest]["paths"].append(rel)
            continue
        entry = classify(blob)
        entry["sha256"] = digest
        entry["paths"] = [rel]
        by_digest[digest] = entry

    captures = sorted(by_digest.values(), key=lambda e: e["sha256"])
    abl = [c for c in captures if c["has_abl_stage"]]
    download = [c for c in abl if c["download_mode"]]
    normal = [c for c in abl if not c["download_mode"]]
    return {
        "schema": "s22plus-fyg8-p319-abl-capture-manifest-v2",
        "inclusion_criterion": {
            "root": "workspace/private",
            "exact_size_bytes": LAST_KMSG_SIZE,
            "selected_by_name_or_run": False,
        },
        "matching_files": file_count,
        "unreadable_or_short_files": len(unreadable),
        "distinct_captures": len(captures),
        "duplicate_files_collapsed": file_count - len(captures),
        "counts": {
            "no_abl_stage": len(captures) - len(abl),
            "abl_stages": len(abl),
            "download_mode": len(download),
            "normal_handoff": len(normal),
            "download_with_setpath_1": sum(1 for c in download if c["setpath_values"] == ["1"]),
            "download_without_setpath": sum(1 for c in download if not c["setpath_values"]),
            "normal_with_any_setpath": sum(1 for c in normal if c["setpath_values"]),
            "normal_with_mission_mode": sum(1 for c in normal if c["mission_mode"]),
            "any_capture_with_setpath_0": sum(1 for c in captures if "0" in c["setpath_values"]),
            "abl_boot_segments": sum(c["boot_segments"] for c in abl),
            "download_boot_segments": sum(c["boot_segments"] for c in download),
            "normal_boot_segments": sum(c["boot_segments"] for c in normal),
            "setpath_occurrences_total": sum(c["setpath_occurrences"] for c in abl),
        },
        "bc_ctrl1_value_counts": _tally(abl, "bc_ctrl1_reads"),
        "bc_ctrl1_value_counts_download": _tally(download, "bc_ctrl1_reads"),
        "bc_ctrl1_value_counts_normal": _tally(normal, "bc_ctrl1_reads"),
        "muic_opcode_counts": _opcode_tally(abl),
        "setpath_values_observed": sorted({v for c in captures for v in c["setpath_values"]}),
        "captures": captures,
    }


def main() -> int:
    manifest = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    summary = {k: v for k, v in manifest.items() if k not in ("captures",)}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
