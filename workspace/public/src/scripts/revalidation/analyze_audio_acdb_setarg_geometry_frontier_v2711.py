#!/usr/bin/env python3
"""V2711 host-only ACDB custom-topology SET-arg geometry frontier audit.

V2708 replayed V2704 custom-topology payloads through synthetic
`--basic-payload` SET arguments and still hit DSP-side ASM rejection. This audit
checks whether that failure can still be blamed on SET argument geometry.

It compares private exact lower SET arg captures for custom-topology cal_types
14/24 against the replay helper's generated 32-byte basic SET packet, and
compares their payload hashes against V2704. It emits only metadata: header
words, sizes, hashes, and decisions. It reads private payload files only to
compute SHA-256; it never emits raw payload bytes, runs a device, or issues any
ioctl.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2711"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2711_AUDIO_ACDB_SETARG_GEOMETRY_FRONTIER_2026-06-18.md"
DEFAULT_V2704_RESULT = ROOT / "workspace/private/runs/audio/v2704-acdb-large-buffer-topology-get-20260618-190151/v2704-result.json"
DEFAULT_LOWER_RUNS = (
    ROOT / "workspace/private/runs/audio/v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431/ownget-device-artifacts",
    ROOT / "workspace/private/runs/audio/v2693-acdb-lower-ptrtarget-capture-20260618-171518/ownget-device-artifacts",
)
TARGET_CAL_TYPES = (24, 10, 14)
TARGET_ROLES = {
    24: "AFE_CUST_TOPOLOGY",
    10: "ADM_CUST_TOPOLOGY",
    14: "ASM_CUST_TOPOLOGY",
}
TARGET_CMDS = {
    24: "0x000130da",
    10: "0x00011394",
    14: "0x00012e01",
}


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def words_from_file(path: Path) -> list[int]:
    raw = path.read_bytes()
    if len(raw) % 4 != 0:
        raise ValueError(f"arg length is not word-aligned: {path}")
    return list(struct.unpack("<" + "i" * (len(raw) // 4), raw))


def basic_set_words(cal_type: int, cal_size: int, mem_handle: int = 0, buffer_number: int = 0) -> list[int]:
    return [32, 0, int(cal_type), 16, 0, int(buffer_number), int(cal_size), int(mem_handle)]


def words_equivalent_mod_mem_handle(exact_words: list[int], basic_words: list[int]) -> bool:
    if len(exact_words) != len(basic_words):
        return False
    return exact_words[:7] == basic_words[:7]


def cal_type_from_name(path: Path) -> int | None:
    match = re.search(r"-cal([0-9a-fA-F]{8})-", path.name)
    if not match:
        return None
    return int(match.group(1), 16)


def load_v2704_rows(path: Path) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    payload = read_json(path)
    summary = payload.get("large_get_summary") if isinstance(payload.get("large_get_summary"), dict) else {}
    for row in summary.get("target_rows") or []:
        try:
            cal_type = int(row.get("target_cal_type"))
        except (TypeError, ValueError):
            continue
        if cal_type not in TARGET_CAL_TYPES:
            continue
        raw_status = row.get("raw_status") if isinstance(row.get("raw_status"), dict) else {}
        rows[cal_type] = {
            "cal_type": cal_type,
            "role": TARGET_ROLES[cal_type],
            "cmd": TARGET_CMDS[cal_type],
            "ret": row.get("ret"),
            "size": row.get("out_len"),
            "sha256": row.get("sha256"),
            "raw_ok": bool(raw_status.get("exists") and raw_status.get("nonzero") and raw_status.get("sha_ok") and raw_status.get("size_ok")),
        }
    return rows


def find_lower_records(lower_dirs: list[Path]) -> dict[int, list[dict[str, Any]]]:
    records: dict[int, list[dict[str, Any]]] = {cal_type: [] for cal_type in TARGET_CAL_TYPES}
    for directory in lower_dirs:
        if not directory.exists():
            continue
        args_by_cal: dict[int, Path] = {}
        payloads_by_cal: dict[int, Path] = {}
        for path in directory.glob("setcal-arg-*.bin"):
            cal_type = cal_type_from_name(path)
            if cal_type in TARGET_CAL_TYPES:
                args_by_cal[cal_type] = path
        for path in directory.glob("setcal-dmabuf-*.bin"):
            cal_type = cal_type_from_name(path)
            if cal_type in TARGET_CAL_TYPES:
                payloads_by_cal[cal_type] = path
        for cal_type, arg_path in sorted(args_by_cal.items()):
            words = words_from_file(arg_path)
            payload_path = payloads_by_cal.get(cal_type)
            payload_size = payload_path.stat().st_size if payload_path else None
            payload_sha = sha256_file(payload_path) if payload_path else None
            records[cal_type].append(
                {
                    "run_dir": rel(directory),
                    "arg_path": rel(arg_path),
                    "arg_len": arg_path.stat().st_size,
                    "arg_sha256": sha256_file(arg_path),
                    "arg_words": words,
                    "payload_path": rel(payload_path) if payload_path else None,
                    "payload_size": payload_size,
                    "payload_sha256": payload_sha,
                }
            )
    return records


def compare_records(v2704_rows: dict[int, dict[str, Any]], lower_records: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cal_type in TARGET_CAL_TYPES:
        v2704 = v2704_rows.get(cal_type, {})
        exact_records = lower_records.get(cal_type, [])
        basic_words = basic_set_words(cal_type, int(v2704.get("size") or 0), mem_handle=0, buffer_number=0)
        exact_equivalent = []
        payload_matches = []
        exact_words_public: list[list[int]] = []
        for record in exact_records:
            exact_words = list(record["arg_words"])
            exact_words_public.append(exact_words)
            exact_equivalent.append(words_equivalent_mod_mem_handle(exact_words, basic_words))
            payload_matches.append(bool(record.get("payload_sha256") and record.get("payload_sha256") == v2704.get("sha256")))
        rows.append(
            {
                "cal_type": cal_type,
                "role": TARGET_ROLES[cal_type],
                "cmd": TARGET_CMDS[cal_type],
                "v2704_size": v2704.get("size"),
                "v2704_sha256": v2704.get("sha256"),
                "v2704_raw_ok": bool(v2704.get("raw_ok")),
                "basic_words_without_runtime_mem_handle": basic_words,
                "lower_exact_record_count": len(exact_records),
                "lower_exact_arg_words": exact_words_public,
                "lower_exact_arg_equivalent_mod_mem_handle": bool(exact_records) and all(exact_equivalent),
                "lower_exact_payload_matches_v2704": bool(exact_records) and all(payload_matches),
                "lower_exact_payload_shas": sorted({record.get("payload_sha256") for record in exact_records if record.get("payload_sha256")}),
            }
        )
    return rows


def classify(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_cal = {row["cal_type"]: row for row in rows}
    cal24_closed = bool(by_cal[24]["lower_exact_arg_equivalent_mod_mem_handle"] and by_cal[24]["lower_exact_payload_matches_v2704"])
    cal14_closed = bool(by_cal[14]["lower_exact_arg_equivalent_mod_mem_handle"] and by_cal[14]["lower_exact_payload_matches_v2704"])
    cal10_has_exact = bool(by_cal[10]["lower_exact_record_count"])
    decision = "v2711-setarg-geometry-frontier-unknown"
    if cal24_closed and cal14_closed and not cal10_has_exact:
        decision = "v2711-setarg-geometry-exhausted-selector-payload-frontier"
    return {
        "decision": decision,
        "cal24_setarg_geometry_closed": cal24_closed,
        "cal14_setarg_geometry_closed": cal14_closed,
        "cal10_exact_setarg_absent": not cal10_has_exact,
        "v2708_failure_not_explained_by_cal14_setarg_geometry": cal14_closed,
        "fresh_setarg_only_capture_low_value": cal24_closed and cal14_closed,
        "native_replay_should_remain_parked": True,
        "recommended_next": "selected-payload-selector-re-or-route-specific-real-path-capture",
    }


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    lower_dirs = [Path(item) for item in args.lower_dir] if args.lower_dir else list(DEFAULT_LOWER_RUNS)
    v2704_rows = load_v2704_rows(args.v2704_result)
    lower_records = find_lower_records(lower_dirs)
    rows = compare_records(v2704_rows, lower_records)
    return {
        "run_id": RUN_ID,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": False,
        "raw_payload_read_for_hash_only": True,
        "inputs": {
            "v2704_result": rel(args.v2704_result),
            "lower_dirs": [rel(path) for path in lower_dirs],
        },
        "rows": rows,
        "classification": classify(rows),
        "next_requirements": [
            "Do not run another replay of the unchanged V2707 manifest.",
            "Do not spend a new live unit on SET-arg-only capture for cal_type 14 or 24; existing exact lower arg and payload metadata already match V2704/basic replay.",
            "Find or reconstruct selected ASM cal_type 14 payload/state, because V2708 failed exactly at send_asm_custom_topology with ADSP_EBADPARAM.",
            "Treat cal_type 10 as still lacking an exact lower SET record, but do not assume a non-32-byte SET arg format without new source evidence.",
        ],
    }


def write_report(summary: dict[str, Any], path: Path) -> None:
    c = summary["classification"]
    lines = [
        "# NATIVE_INIT V2711 — ACDB custom-topology SET-arg geometry frontier",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only audit of private metadata from V2704, V2675, and V2693. This unit compares exact lower custom-topology SET arg headers and payload hashes against the V2707/V2708 basic SET replay contract. It emits no raw ACDB bytes, runs no device step, and issues no ioctl.",
        "",
        "## Result",
        "",
        f"- Decision: `{c['decision']}`",
        f"- cal_type 24 SET-arg geometry closed: `{c['cal24_setarg_geometry_closed']}`",
        f"- cal_type 14 SET-arg geometry closed: `{c['cal14_setarg_geometry_closed']}`",
        f"- cal_type 10 exact SET arg absent: `{c['cal10_exact_setarg_absent']}`",
        f"- V2708 ASM failure explained by cal14 SET arg geometry: `{not c['v2708_failure_not_explained_by_cal14_setarg_geometry']}`",
        f"- Recommended next: `{c['recommended_next']}`",
        "",
        "## Comparison",
        "",
        "| cal_type | role | V2704 size | V2704 SHA-256 | basic arg words without runtime mem_handle | exact lower arg words | exact arg equivalent | payload SHA matches V2704 |",
        "| ---: | --- | ---: | --- | --- | --- | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| `{row['cal_type']}` | `{row['role']}` | `{row['v2704_size']}` | `{row['v2704_sha256']}` | `{row['basic_words_without_runtime_mem_handle']}` | `{row['lower_exact_arg_words']}` | `{row['lower_exact_arg_equivalent_mod_mem_handle']}` | `{row['lower_exact_payload_matches_v2704']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- For cal_type `24` and `14`, the existing exact lower SET arg captures are the same 32-byte packet shape that the replay helper generates for `--basic-payload`, modulo the runtime `mem_handle` value.",
            "- The V2704 payload SHA-256 values for cal_type `24` and `14` match the exact lower SET payloads from V2675/V2693.",
            "- Therefore V2708 did not merely replay an arbitrary or structurally generic cal_type `14` SET. It effectively replayed the same lower exact SET arg/payload family, and the DSP still rejected `send_asm_custom_topology` with `ADSP_EBADPARAM`.",
            "- The frontier moves from SET arg geometry to selector/payload semantics: the cal_type `14` payload appears stale/non-selected per V2696, and cal_type `10` still has no exact lower SET record even though V2704 recovered a large GET payload.",
            "- Native replay remains parked until selected cal_type `14` and cal_type `10` payload/state are recovered or source-backed reconstruction changes the payload contract.",
            "",
            "## Next Requirements",
            "",
        ]
    )
    for item in summary["next_requirements"]:
        lines.append(f"- {item}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2704-result", type=Path, default=DEFAULT_V2704_RESULT)
    parser.add_argument("--lower-dir", action="append")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(args)
    if args.write_report:
        write_report(summary, args.report)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
