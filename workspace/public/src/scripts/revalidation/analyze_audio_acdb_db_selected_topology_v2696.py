#!/usr/bin/env python3
"""V2696 host-only ACDB DB / payload selected-topology audit.

This unit checks whether byte-exact selected custom-topology definitions for
ADM/ASM/AFE are present in staged ACDB DB files or in the already captured
payload corpus.  It performs no device action and never writes raw ACDB bytes
outside workspace/private.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import analyze_audio_acdb_core_topology_bridge_v2683 as v2683
except ModuleNotFoundError:  # pragma: no cover - package import path in unittest.
    from workspace.public.src.scripts.revalidation import analyze_audio_acdb_core_topology_bridge_v2683 as v2683

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2696"
REPORT = ROOT / "docs/reports/NATIVE_INIT_V2696_AUDIO_ACDB_DB_SELECTED_TOPOLOGY_AUDIT_2026-06-18.md"

DEFAULT_DB_ROOTS = (
    ROOT / "workspace/private/inputs/audio",
    ROOT / "workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump/etc",
)
DEFAULT_PAYLOAD_FILES = (
    ROOT / "workspace/private/inputs/audio/acdb_replay/payloads/core_custom_topologies_v2547.bin",
    ROOT / "workspace/private/runs/audio/v2693-acdb-lower-ptrtarget-capture-20260618-171518/ownget-device-artifacts/setcal-dmabuf-p00000f1c-s00000001-cal00000018-len0000049c.bin",
    ROOT / "workspace/private/runs/audio/v2693-acdb-lower-ptrtarget-capture-20260618-171518/ownget-device-artifacts/setcal-dmabuf-p00000f1c-s00000002-cal0000000e-len00000934.bin",
    ROOT / "workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431/ownget-device-artifacts/setcal-dmabuf-p00000f67-s00000001-cal00000018-len0000049c.bin",
    ROOT / "workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431/ownget-device-artifacts/setcal-dmabuf-p00000f67-s00000002-cal0000000e-len00000934.bin",
)

TARGETS = {
    10: {"role": "ADM_CUST_TOPOLOGY", "selected_topology": 0x10004000},
    14: {"role": "ASM_CUST_TOPOLOGY", "selected_topology": 0x10005000},
    24: {"role": "AFE_CUST_TOPOLOGY", "selected_topology": 0x1001025D},
}


@dataclasses.dataclass(frozen=True)
class EmbeddedRecord:
    parser: str
    topology_id: int
    word_offset: int
    module_count: int
    modules_preview: tuple[tuple[int, int], ...]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hex32(value: int) -> str:
    return f"0x{value & 0xFFFFFFFF:08x}"


def read_words(path: Path) -> tuple[int, ...]:
    data = path.read_bytes()
    if len(data) < 4:
        return ()
    aligned = len(data) - (len(data) % 4)
    return struct.unpack("<" + "I" * (aligned // 4), data[:aligned])


def pack_words(words: Iterable[int]) -> bytes:
    values = tuple(words)
    return struct.pack("<" + "I" * len(values), *values) if values else b""


def discover_acdb_files(roots: Iterable[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() == ".acdb":
                files.append(path)
    return sorted(set(files))


def existing_payloads(paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if path.exists() and path.is_file()]


def parse_whole_payload(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    out: dict[str, Any] = {
        "size": len(data),
        "sha256": sha256(data),
        "whole_core_ok": False,
        "whole_fixed_ok": False,
        "whole_core_topologies": [],
        "whole_fixed_topologies": [],
    }
    try:
        core = v2683.parse_core_payload(data)
        out["whole_core_ok"] = True
        out["whole_core_topologies"] = [
            {
                "topology_id": record.topology_id,
                "topology_hex": hex32(record.topology_id),
                "module_count": len(record.modules),
                "word_offset": record.word_offset,
            }
            for record in core
        ]
    except Exception as exc:  # noqa: BLE001 - parser failure is data.
        out["whole_core_error"] = str(exc)
    try:
        fixed = v2683.parse_fixed_payload(data)
        out["whole_fixed_ok"] = True
        out["whole_fixed_topologies"] = [
            {
                "topology_id": record.topology_id,
                "topology_hex": hex32(record.topology_id),
                "module_count": len(record.modules),
                "record_index": record.index,
            }
            for record in fixed
        ]
    except Exception as exc:  # noqa: BLE001 - parser failure is data.
        out["whole_fixed_error"] = str(exc)
    return out


def find_target_words(words: tuple[int, ...]) -> dict[int, list[int]]:
    targets = {int(meta["selected_topology"]) for meta in TARGETS.values()}
    hits = {target: [] for target in targets}
    for index, word in enumerate(words):
        if word in hits:
            hits[word].append(index)
    return hits


def embedded_fixed_candidate(words: tuple[int, ...], word_offset: int) -> EmbeddedRecord | None:
    end = word_offset + v2683.FIXED_RECORD_U32
    if end > len(words):
        return None
    rec = words[word_offset:end]
    module_count = rec[1]
    if module_count > v2683.FIXED_MODULE_SLOTS:
        return None
    modules: list[tuple[int, int]] = []
    for slot in range(module_count):
        slot_base = 2 + slot * v2683.FIXED_SLOT_U32
        module_id = rec[slot_base]
        instance_id = rec[slot_base + 1]
        if any(rec[slot_base + 2:slot_base + v2683.FIXED_SLOT_U32]):
            return None
        modules.append((module_id, instance_id))
    padding_start = 2 + module_count * v2683.FIXED_SLOT_U32
    if any(rec[padding_start:]):
        return None
    return EmbeddedRecord(
        parser="embedded_fixed_record",
        topology_id=rec[0],
        word_offset=word_offset,
        module_count=module_count,
        modules_preview=tuple(modules[:16]),
    )


def embedded_core_candidate(words: tuple[int, ...], topology_word_offset: int) -> EmbeddedRecord | None:
    start = topology_word_offset - 1
    if start < 0 or start + 4 > len(words):
        return None
    domain, topology_id, version, module_count = words[start:start + 4]
    _ = domain, version
    if module_count > 64:
        return None
    end = start + 4 + module_count * 2
    if end > len(words):
        return None
    modules = tuple((words[start + 4 + n * 2], words[start + 5 + n * 2]) for n in range(module_count))
    return EmbeddedRecord(
        parser="embedded_core_record",
        topology_id=topology_id,
        word_offset=start,
        module_count=module_count,
        modules_preview=modules[:16],
    )


def record_to_json(record: EmbeddedRecord) -> dict[str, Any]:
    return {
        "parser": record.parser,
        "topology_id": record.topology_id,
        "topology_hex": hex32(record.topology_id),
        "word_offset": record.word_offset,
        "module_count": record.module_count,
        "modules_preview": [
            {"module_id": module_id, "module_hex": hex32(module_id), "instance_id": instance_id, "instance_hex": hex32(instance_id)}
            for module_id, instance_id in record.modules_preview
        ],
    }


def scan_file(path: Path) -> dict[str, Any]:
    words = read_words(path)
    whole = parse_whole_payload(path)
    target_hits = find_target_words(words)
    embedded: dict[int, list[dict[str, Any]]] = {}
    for target, offsets in target_hits.items():
        records: list[dict[str, Any]] = []
        seen: set[tuple[str, int, int]] = set()
        for offset in offsets:
            for candidate in (
                embedded_fixed_candidate(words, offset),
                embedded_core_candidate(words, offset),
            ):
                if candidate is None:
                    continue
                key = (candidate.parser, candidate.word_offset, candidate.topology_id)
                if key in seen:
                    continue
                seen.add(key)
                records.append(record_to_json(candidate))
        embedded[target] = records
    return {
        "path": rel(path),
        "size": whole["size"],
        "sha256": whole["sha256"],
        "target_word_hits": {hex32(target): offsets for target, offsets in target_hits.items() if offsets},
        "embedded_records": {hex32(target): records for target, records in embedded.items() if records},
        "whole_core_ok": whole["whole_core_ok"],
        "whole_fixed_ok": whole["whole_fixed_ok"],
        "whole_core_topologies": whole["whole_core_topologies"],
        "whole_fixed_topologies": whole["whole_fixed_topologies"],
    }


def topology_present(scan: dict[str, Any], topology_id: int) -> bool:
    target = hex32(topology_id)
    if scan.get("target_word_hits", {}).get(target):
        return True
    for key in ("whole_core_topologies", "whole_fixed_topologies"):
        for item in scan.get(key) or []:
            if item["topology_id"] == topology_id:
                return True
    return False


def parseable_record_present(scan: dict[str, Any], topology_id: int, parser_prefix: str | None = None) -> bool:
    target = hex32(topology_id)
    records = scan.get("embedded_records", {}).get(target) or []
    for record in records:
        if parser_prefix is None or str(record["parser"]).startswith(parser_prefix):
            return True
    for key in ("whole_core_topologies", "whole_fixed_topologies"):
        for item in scan.get(key) or []:
            if item["topology_id"] == topology_id:
                return True
    return False


def analyze(db_roots: Iterable[Path] = DEFAULT_DB_ROOTS, payload_files: Iterable[Path] = DEFAULT_PAYLOAD_FILES) -> dict[str, Any]:
    db_files = discover_acdb_files(db_roots)
    payloads = existing_payloads(payload_files)
    db_scans = [scan_file(path) for path in db_files]
    payload_scans = [scan_file(path) for path in payloads]
    all_scans = db_scans + payload_scans

    target_summary: list[dict[str, Any]] = []
    for cal_type, meta in TARGETS.items():
        selected = int(meta["selected_topology"])
        scans_with_word = [scan["path"] for scan in all_scans if topology_present(scan, selected)]
        scans_with_parseable = [scan["path"] for scan in all_scans if parseable_record_present(scan, selected)]
        db_with_parseable = [scan["path"] for scan in db_scans if parseable_record_present(scan, selected)]
        payload_with_parseable = [scan["path"] for scan in payload_scans if parseable_record_present(scan, selected)]
        target_summary.append({
            "cal_type": cal_type,
            "role": meta["role"],
            "selected_topology": selected,
            "selected_topology_hex": hex32(selected),
            "word_hit_files": scans_with_word,
            "parseable_record_files": scans_with_parseable,
            "db_parseable_record_files": db_with_parseable,
            "payload_parseable_record_files": payload_with_parseable,
            "parseable_record_found": bool(scans_with_parseable),
            "db_parseable_record_found": bool(db_with_parseable),
            "payload_parseable_record_found": bool(payload_with_parseable),
        })

    db_staged = bool(db_files)
    lower_fixed_scans = [scan for scan in payload_scans if scan.get("whole_fixed_ok")]
    asm_in_exact_lower_payload = any(parseable_record_present(scan, 0x10005000) for scan in lower_fixed_scans)
    afe_in_exact_lower_payload = any(parseable_record_present(scan, 0x1001025D) for scan in lower_fixed_scans)
    core_payload_scans = [scan for scan in payload_scans if scan.get("whole_core_ok")]
    core_has_selected_all = all(
        any(parseable_record_present(scan, int(meta["selected_topology"])) for scan in core_payload_scans)
        for meta in TARGETS.values()
    )
    decision = "v2696-acdb-db-not-staged-core-has-selected-but-lower-selector-stale"
    if db_staged and all(row["db_parseable_record_found"] for row in target_summary):
        decision = "v2696-acdb-db-has-selected-records-selector-re-needed"
    elif db_staged:
        decision = "v2696-acdb-db-staged-selected-records-incomplete"

    return {
        "run_id": RUN_ID,
        "generated_at": now_iso(),
        "decision": decision,
        "ok": True,
        "db_roots": [rel(path) for path in db_roots],
        "payload_files_requested": [rel(path) for path in payload_files],
        "db_files_scanned": [rel(path) for path in db_files],
        "payload_files_scanned": [rel(path) for path in payloads],
        "db_staged": db_staged,
        "db_file_count": len(db_files),
        "payload_file_count": len(payloads),
        "core_has_selected_all": core_has_selected_all,
        "asm_selected_in_exact_lower_cal14": asm_in_exact_lower_payload,
        "afe_selected_in_exact_lower_cal24": afe_in_exact_lower_payload,
        "target_summary": target_summary,
        "db_scans": db_scans,
        "payload_scans": payload_scans,
    }


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def short_paths(paths: list[str], limit: int = 3) -> str:
    if not paths:
        return "none"
    shown = ", ".join(f"`{path}`" for path in paths[:limit])
    if len(paths) > limit:
        shown += f", ... (+{len(paths) - limit})"
    return shown


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# NATIVE_INIT V2696 — ACDB DB selected-topology audit",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only audit. This scans staged private ACDB DB files, if any, and the already captured private topology payload corpus for selected ADM/ASM/AFE custom topology IDs. No device action, flash, Android handoff, `/dev/msm_audio_cal` ioctl, mixer write, PCM probe, or raw payload commit occurred.",
        "",
        "## Result",
        "",
        f"- decision: `{summary['decision']}`",
        f"- ok: `{summary['ok']}`",
        f"- db_staged: `{summary['db_staged']}`",
        f"- db_file_count: `{summary['db_file_count']}`",
        f"- payload_file_count: `{summary['payload_file_count']}`",
        f"- core_has_selected_all: `{summary['core_has_selected_all']}`",
        f"- asm_selected_in_exact_lower_cal14: `{summary['asm_selected_in_exact_lower_cal14']}`",
        f"- afe_selected_in_exact_lower_cal24: `{summary['afe_selected_in_exact_lower_cal24']}`",
        "",
        "## Selected topology summary",
        "",
    ]
    rows: list[list[str]] = []
    for item in summary["target_summary"]:
        rows.append([
            str(item["cal_type"]),
            f"`{item['role']}`",
            f"`{item['selected_topology_hex']}`",
            str(item["db_parseable_record_found"]),
            str(item["payload_parseable_record_found"]),
            short_paths(item["payload_parseable_record_files"]),
        ])
    lines.append(render_table(
        ["cal_type", "role", "selected topology", "DB parseable", "payload parseable", "payload record files"],
        rows,
    ))
    lines.extend([
        "",
        "## Payload corpus scan",
        "",
    ])
    payload_rows: list[list[str]] = []
    for scan in summary["payload_scans"]:
        present = []
        parseable = []
        for cal_type, meta in TARGETS.items():
            selected = int(meta["selected_topology"])
            if topology_present(scan, selected):
                present.append(f"cal{cal_type}:{hex32(selected)}")
            if parseable_record_present(scan, selected):
                parseable.append(f"cal{cal_type}:{hex32(selected)}")
        payload_rows.append([
            f"`{scan['path']}`",
            str(scan["size"]),
            "core" if scan["whole_core_ok"] else ("fixed" if scan["whole_fixed_ok"] else "raw"),
            ", ".join(present) or "none",
            ", ".join(parseable) or "none",
        ])
    lines.append(render_table(["file", "size", "parser", "selected word hits", "parseable selected records"], payload_rows))
    lines.extend([
        "",
        "## Interpretation",
        "",
    ])
    if not summary["db_staged"]:
        lines.extend([
            "No `.acdb` DB corpus is currently staged under the checked private ACDB input roots. That means this unit cannot prove which on-disk DB table selector should be invoked; it can only classify the already captured payload corpus.",
            "",
        ])
    lines.extend([
        "The payload corpus still gives a useful split:",
        "",
        "- The CORE_CUSTOM_TOPOLOGIES blob contains parseable selected ADM `0x10004000`, ASM `0x10005000`, and AFE `0x1001025d` records.",
        "- The exact lower AFE cal_type 24 payload contains selected `0x1001025d`, so AFE custom topology selection is aligned.",
        "- The exact lower ASM cal_type 14 payload does not contain selected `0x10005000`; its selected record exists in core but not in the lower SET payload.",
        "- No byte-exact ADM cal_type 10 SET payload is present in the lower corpus; ADM selected `0x10004000` only appears in core/candidate material.",
        "",
        "Therefore V2695's pivot is reinforced: the next useful work is not another lower pointer-target capture. The missing piece is either staging/parsing the real `.acdb` DB corpus to identify the selector tuple for cal10/cal14, or a route-specific Android-good capture that observes the real HAL custom-topology SET path. Existing synthetic core-to-fixed candidates already failed to clear DSP semantics, so native replay remains parked until byte-exact selected cal10/cal14 payloads are recovered.",
        "",
        "## Next unit",
        "",
        "Stage the device `/vendor/etc/acdbdata` corpus privately and rerun this scanner against those `.acdb` files, or build the route-specific Android-good capture for the real custom-topology SET path. If the DB corpus is staged, this same script should classify whether selected ADM/ASM records exist in parseable on-disk tables before any new live audio run.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_db_selected_topology_v2696.py tests/test_analyze_audio_acdb_db_selected_topology_v2696.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_db_selected_topology_v2696 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_db_selected_topology_v2696.py --write-report`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v`",
        "- `git diff --check`",
        "",
    ])
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-root", action="append", type=Path, dest="db_roots")
    parser.add_argument("--payload", action="append", type=Path, dest="payload_files")
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    db_roots = tuple(args.db_roots) if args.db_roots else DEFAULT_DB_ROOTS
    payload_files = tuple(args.payload_files) if args.payload_files else DEFAULT_PAYLOAD_FILES
    summary = analyze(db_roots=db_roots, payload_files=payload_files)
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_markdown(summary), encoding="utf-8")
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(json.dumps({"decision": summary["decision"], "ok": summary["ok"], "report": rel(args.report) if args.write_report else None}, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
