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

REPO = Path(__file__).resolve().parents[5]
PRIVATE = REPO / "workspace" / "private"
OUT = PRIVATE / "outputs" / "s22plus_fyg8_p319" / "abl-capture-manifest.json"


def classify(blob: bytes) -> dict:
    return {
        "has_abl_stage": ABL_MARK in blob,
        "download_mode": ODIN_MARK in blob,
        "mission_mode": MISSION_MARK in blob,
        "setpath_values": sorted({m.group(1).decode() for m in SETPATH_RE.finditer(blob)}),
    }


def build(private: Path = PRIVATE) -> dict:
    by_digest: dict[str, dict] = {}
    file_count = 0
    for path in sorted(private.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            if path.stat().st_size != LAST_KMSG_SIZE:
                continue
            blob = path.read_bytes()
        except OSError:
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
        "schema": "s22plus-fyg8-p319-abl-capture-manifest-v1",
        "inclusion_criterion": {
            "root": "workspace/private",
            "exact_size_bytes": LAST_KMSG_SIZE,
            "selected_by_name_or_run": False,
        },
        "matching_files": file_count,
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
        },
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
