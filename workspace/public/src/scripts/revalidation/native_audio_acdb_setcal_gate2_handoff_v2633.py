#!/usr/bin/env python3
"""Build a Gate-2 handoff package from the V2632 SET-calibration capture.

Host-only. Reads the private V2632 run, verifies the dumped SET ioctl argument
bytes and same-process dma-buf payloads, writes a private raw-path manifest for
operator Gate-2 review, and writes a redacted public report. This is not a native
replay manifest and never copies raw bytes into tracked paths.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2633"
BUILD_TAG = "v2633-audio-acdb-setcal-gate2-handoff"
DEFAULT_RUN_GLOB = "v2632-acdb-setcal-capture-*"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2633_AUDIO_ACDB_SETCAL_GATE2_HANDOFF_2026-06-18.md"
DEFAULT_PRIVATE_NAME = "v2633-acdb-setcal-gate2-handoff-manifest.json"
DEFAULT_PREVIOUS_GATE2_MANIFEST = (
    ROOT
    / "workspace/private/runs/audio/v2618-acdb-direct-matrix-20260616-203644"
    / "v2619-acdb-gate2-handoff-manifest.json"
)
EXPECTED_ORDER = [13, 9, 11, 12, 15, 23, 16, 21]
PAYLOAD_CAL_TYPES = {11, 15, 16}
PREVIOUS_CATEGORY_TO_CAL_TYPE = {
    "AUDPROC_COMMON_CANDIDATE": 11,
    "AUDPROC_STREAM_CANDIDATE": 15,
    "AFE_COMMON_CANDIDATE": 16,
}
ROLE_BY_CAL_TYPE = {
    9: "AFE_TOPOLOGY_HEADER",
    11: "AUDPROC_COMMON_PAYLOAD",
    12: "VOL_HEADER_NO_PAYLOAD",
    13: "APP_META_HEADER",
    15: "ASM_STREAM_PAYLOAD",
    16: "AFE_COMMON_PAYLOAD",
    21: "SPEAKER_VI_HEADER",
    23: "AFE_TOPOLOGY_ID_HEADER",
}


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict[str, Any], mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text, 0)
    except ValueError:
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def all_zero(path: Path) -> bool:
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            if any(chunk):
                return False
    return True


def latest_v2632_run(base: Path) -> Path:
    candidates = sorted(
        run_dir
        for run_dir in base.glob(DEFAULT_RUN_GLOB)
        if run_dir.is_dir() and (run_dir / "v2631-result.json").exists()
    )
    if not candidates:
        raise FileNotFoundError(f"no V2632 SET-cal runs with v2631-result.json under {rel(base)}")
    return candidates[-1]


def local_artifact_from_remote(run_dir: Path, remote_path: str | None) -> Path | None:
    if not remote_path:
        return None
    return run_dir / "ownget-device-artifacts" / Path(remote_path).name


def file_summary(path: Path | None, expected_len: int | None, expected_sha256: str | None) -> dict[str, Any]:
    if path is None:
        return {
            "exists": False,
            "verified": False,
            "raw_path_private": None,
            "size": None,
            "sha256": None,
            "nonzero": False,
            "size_matches_event": False,
            "hash_matches_event": False,
        }
    if not path.exists():
        return {
            "exists": False,
            "verified": False,
            "raw_path_private": rel(path),
            "size": None,
            "sha256": None,
            "nonzero": False,
            "size_matches_event": False,
            "hash_matches_event": False,
        }
    size = path.stat().st_size
    sha256 = sha256_file(path)
    nonzero = not all_zero(path)
    size_matches = expected_len is None or size == expected_len
    hash_matches = expected_sha256 in (None, sha256)
    return {
        "exists": True,
        "verified": bool(size_matches and hash_matches and nonzero),
        "raw_path_private": rel(path),
        "size": size,
        "sha256": sha256,
        "nonzero": nonzero,
        "size_matches_event": size_matches,
        "hash_matches_event": hash_matches,
    }


def previous_payloads(previous_manifest_path: Path | None) -> dict[int, dict[str, Any]]:
    if previous_manifest_path is None or not previous_manifest_path.exists():
        return {}
    manifest = read_json(previous_manifest_path)
    output: dict[int, dict[str, Any]] = {}
    for item in manifest.get("payload_candidates", []):
        cal_type = PREVIOUS_CATEGORY_TO_CAL_TYPE.get(str(item.get("category") or ""))
        raw_path = item.get("raw_path_private")
        if cal_type is None or not raw_path:
            continue
        local_path = ROOT / str(raw_path)
        if not local_path.exists():
            continue
        data = local_path.read_bytes()
        output[cal_type] = {
            "source_manifest": rel(previous_manifest_path),
            "source_raw_path_private": rel(local_path),
            "sha256": sha256_bytes(data),
            "size": len(data),
            "first_word_hex": data[:4].hex(),
            "tail_sha256": sha256_bytes(data[4:]) if len(data) >= 4 else None,
        }
    return output


def compare_previous(cal_type: int, raw_path: Path | None, previous: dict[int, dict[str, Any]]) -> dict[str, Any]:
    previous_item = previous.get(cal_type)
    if previous_item is None or raw_path is None or not raw_path.exists():
        return {
            "available": False,
            "tail_bytes_match": None,
            "previous_first_word_hex": None,
            "current_first_word_hex": None,
            "current_tail_sha256": None,
            "previous_tail_sha256": None,
        }
    current_data = raw_path.read_bytes()
    current_tail_sha256 = sha256_bytes(current_data[4:]) if len(current_data) >= 4 else None
    tail_match = (
        previous_item.get("size") == len(current_data)
        and previous_item.get("tail_sha256") == current_tail_sha256
    )
    return {
        "available": True,
        "tail_bytes_match": bool(tail_match),
        "previous_source_manifest": previous_item.get("source_manifest"),
        "previous_raw_path_private": previous_item.get("source_raw_path_private"),
        "previous_first_word_hex": previous_item.get("first_word_hex"),
        "current_first_word_hex": current_data[:4].hex(),
        "current_tail_sha256": current_tail_sha256,
        "previous_tail_sha256": previous_item.get("tail_sha256"),
    }


def collect_setcal_records(run_dir: Path, previous_manifest_path: Path | None) -> list[dict[str, Any]]:
    events_path = run_dir / "ownget-device-artifacts/setcal-events.jsonl"
    events = [event for event in read_jsonl(events_path) if event.get("event") == "setcal_capture"]
    previous = previous_payloads(previous_manifest_path)
    records: list[dict[str, Any]] = []
    for event in events:
        sequence = parse_int(event.get("sequence"))
        cal_type = parse_int(event.get("cal_type"))
        data_size = parse_int(event.get("data_size"))
        cal_size = parse_int(event.get("cal_size"))
        mem_handle = parse_int(event.get("mem_handle"))
        set_arg = event.get("set_arg") if isinstance(event.get("set_arg"), dict) else {}
        dmabuf = event.get("dmabuf") if isinstance(event.get("dmabuf"), dict) else {}
        arg_path = local_artifact_from_remote(run_dir, set_arg.get("path"))
        dmabuf_path = local_artifact_from_remote(run_dir, dmabuf.get("path"))
        arg_summary = file_summary(arg_path, parse_int(set_arg.get("len")), set_arg.get("sha256"))
        dmabuf_expected = bool(cal_size and cal_size > 0 and mem_handle is not None and mem_handle >= 0)
        dmabuf_summary = file_summary(
            dmabuf_path if dmabuf_expected else None,
            parse_int(dmabuf.get("len")) if dmabuf_expected else None,
            dmabuf.get("sha256") if dmabuf_expected else None,
        )
        previous_comparison = compare_previous(cal_type or -1, dmabuf_path, previous) if dmabuf_expected else {
            "available": False,
            "tail_bytes_match": None,
            "previous_first_word_hex": None,
            "current_first_word_hex": None,
            "current_tail_sha256": None,
            "previous_tail_sha256": None,
        }
        verified_for_gate2 = bool(
            event.get("header_valid")
            and arg_summary.get("verified")
            and (not dmabuf_expected or dmabuf_summary.get("verified"))
        )
        records.append({
            "sequence": sequence,
            "cal_type": cal_type,
            "role": ROLE_BY_CAL_TYPE.get(cal_type, "UNMAPPED_SET_RECORD"),
            "data_size": data_size,
            "cal_type_size": parse_int(event.get("cal_type_size")),
            "cal_size": cal_size,
            "mem_handle": mem_handle,
            "header_valid": bool(event.get("header_valid")),
            "dmabuf_expected": dmabuf_expected,
            "dmabuf_status": dmabuf.get("status"),
            "arg": arg_summary,
            "dmabuf": dmabuf_summary,
            "previous_gate2_compare": previous_comparison,
            "verified_for_gate2": verified_for_gate2,
        })
    return records


def redacted_record(record: dict[str, Any]) -> dict[str, Any]:
    def redact_file(summary: dict[str, Any]) -> dict[str, Any]:
        return {
            key: summary.get(key)
            for key in [
                "exists",
                "verified",
                "size",
                "sha256",
                "nonzero",
                "size_matches_event",
                "hash_matches_event",
            ]
        }

    previous = record.get("previous_gate2_compare", {})
    return {
        "sequence": record.get("sequence"),
        "cal_type": record.get("cal_type"),
        "role": record.get("role"),
        "data_size": record.get("data_size"),
        "cal_type_size": record.get("cal_type_size"),
        "cal_size": record.get("cal_size"),
        "mem_handle": record.get("mem_handle"),
        "header_valid": record.get("header_valid"),
        "dmabuf_expected": record.get("dmabuf_expected"),
        "dmabuf_status": record.get("dmabuf_status"),
        "arg": redact_file(record.get("arg", {})),
        "dmabuf": redact_file(record.get("dmabuf", {})),
        "previous_gate2_compare": {
            "available": previous.get("available"),
            "tail_bytes_match": previous.get("tail_bytes_match"),
            "previous_first_word_hex": previous.get("previous_first_word_hex"),
            "current_first_word_hex": previous.get("current_first_word_hex"),
            "current_tail_sha256": previous.get("current_tail_sha256"),
            "previous_tail_sha256": previous.get("previous_tail_sha256"),
        },
        "verified_for_gate2": record.get("verified_for_gate2"),
    }


def build_manifest(run_dir: Path, previous_manifest_path: Path | None) -> dict[str, Any]:
    result_path = run_dir / "v2631-result.json"
    if not result_path.exists():
        raise FileNotFoundError(f"missing {rel(result_path)}")
    result = read_json(result_path)
    summary = result.get("setcal_summary", {})
    records = collect_setcal_records(run_dir, previous_manifest_path)
    ordered_cal_types = [record.get("cal_type") for record in records]
    payload_records = [record for record in records if record.get("dmabuf_expected")]
    header_records = [record for record in records if not record.get("dmabuf_expected")]
    previous_comparisons = [
        record.get("previous_gate2_compare", {})
        for record in payload_records
        if record.get("cal_type") in PAYLOAD_CAL_TYPES
    ]
    manifest = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_run_id": "V2632",
        "source_run_dir": rel(run_dir),
        "source_result": rel(result_path),
        "source_decision": result.get("decision"),
        "source_ok": result.get("ok"),
        "source_rolled_back": result.get("rolled_back"),
        "source_operator_valuable": result.get("operator_valuable"),
        "previous_gate2_manifest": rel(previous_manifest_path) if previous_manifest_path else None,
        "gate": "operator-gate2-pending",
        "native_replay_ready": False,
        "replay_blockers": [
            "operator must accept the SET-layer arg bytes and dma-buf payloads before replay",
            "this package is a handoff manifest, not a native replay manifest",
            "topology cal_type 39 must still be combined from the already verified topology capture",
        ],
        "summary": {
            "source_classification": summary.get("classification"),
            "source_counts_toward_fails_twice": result.get("counts_toward_fails_twice"),
            "record_count": len(records),
            "verified_record_count": sum(1 for record in records if record.get("verified_for_gate2")),
            "ordered_cal_types": ordered_cal_types,
            "expected_order": EXPECTED_ORDER,
            "order_matches_expected": ordered_cal_types == EXPECTED_ORDER,
            "payload_record_count": len(payload_records),
            "header_record_count": len(header_records),
            "payload_cal_types": sorted(record.get("cal_type") for record in payload_records),
            "header_cal_types": sorted(record.get("cal_type") for record in header_records),
            "previous_payload_tail_match_count": sum(
                1 for item in previous_comparisons if item.get("tail_bytes_match") is True
            ),
            "previous_payload_compare_count": len(previous_comparisons),
            "real_audio_set_pass_through_count": summary.get("real_audio_set_pass_through_count"),
            "fake_audio_set_count": summary.get("fake_audio_set_count"),
            "rolled_back": result.get("rolled_back"),
        },
        "records": records,
        "records_redacted": [redacted_record(record) for record in records],
        "operator_note": (
            "Use raw_path_private only from workspace/private. Public report contains SHA/length only. "
            "Do not update native replay until Gate-2 accepts this SET-layer manifest."
        ),
    }
    manifest["ok"] = bool(
        result.get("ok")
        and result.get("rolled_back")
        and manifest["summary"]["order_matches_expected"]
        and manifest["summary"]["record_count"] == manifest["summary"]["verified_record_count"]
        and manifest["summary"].get("real_audio_set_pass_through_count") == 0
        and manifest["summary"]["previous_payload_compare_count"] == len(PAYLOAD_CAL_TYPES)
        and manifest["summary"]["previous_payload_tail_match_count"] == len(PAYLOAD_CAL_TYPES)
    )
    return manifest


def write_report(path: Path, manifest: dict[str, Any], private_manifest_path: Path) -> None:
    summary = manifest.get("summary", {})
    lines = [
        "# NATIVE_INIT V2633 — ACDB SET-cal Gate-2 handoff package",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only handoff of the V2632 SET-layer ACDB capture. This unit verifies",
        "private raw SET-argument and dma-buf artifacts, writes a private manifest for",
        "operator Gate-2, and publishes only metadata, sizes, and SHA-256 hashes.",
        "",
        "It does **not** build or modify a native replay manifest, does not issue audio",
        "ioctls, does not boot or flash the device, and does not copy raw bytes into",
        "tracked paths.",
        "",
        "## Result",
        "",
        f"- decision: `v2633-setcal-gate2-handoff-{'ready' if manifest.get('ok') else 'needs-review'}`",
        f"- ok: `{manifest.get('ok')}`",
        f"- source_run_dir: `{manifest.get('source_run_dir')}`",
        f"- source_decision: `{manifest.get('source_decision')}`",
        f"- source_rolled_back: `{manifest.get('source_rolled_back')}`",
        f"- private_manifest: `{rel(private_manifest_path)}`",
        f"- record_count: `{summary.get('record_count')}`",
        f"- verified_record_count: `{summary.get('verified_record_count')}`",
        f"- ordered_cal_types: `{summary.get('ordered_cal_types')}`",
        f"- order_matches_expected: `{summary.get('order_matches_expected')}`",
        f"- payload_cal_types: `{summary.get('payload_cal_types')}`",
        f"- header_cal_types: `{summary.get('header_cal_types')}`",
        f"- previous_payload_tail_match_count: `{summary.get('previous_payload_tail_match_count')}`",
        f"- real_audio_set_pass_through_count: `{summary.get('real_audio_set_pass_through_count')}`",
        "",
        "## Redacted SET Records",
        "",
        "| seq | cal_type | role | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 | prev_tail_match |",
        "| ---: | ---: | --- | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for record in manifest.get("records_redacted", []):
        previous = record.get("previous_gate2_compare", {})
        lines.append(
            f"| {record.get('sequence')} | {record.get('cal_type')} | `{record.get('role')}` | "
            f"{record.get('data_size')} | {record.get('cal_size')} | {record.get('mem_handle')} | "
            f"`{record.get('arg', {}).get('sha256')}` | `{record.get('dmabuf_status')}` | "
            f"`{record.get('dmabuf', {}).get('sha256')}` | `{previous.get('tail_bytes_match')}` |"
        )
    lines.extend([
        "",
        "## Gate-2 Boundary",
        "",
        "- This is a handoff package, not a native replay manifest.",
        "- Private manifest rows include `raw_path_private`; public rows intentionally do not.",
        "- cal_type `11`, `15`, and `16` dma-buf payloads match previous Gate-2 payloads",
        "  from byte offset 4 onward; the first word differs as expected between capture methods.",
        "- Header-only SET records (`9`, `12`, `13`, `21`, `23`) are preserved via full SET arg dumps.",
        "- Native ACDB replay remains blocked until operator Gate-2 accepts this package.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_gate2_handoff_v2633.py tests/test_native_audio_acdb_setcal_gate2_handoff_v2633.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_gate2_handoff_v2633 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_gate2_handoff_v2633.py --write-report`",
        "- `git diff --check`",
        "",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-dir", type=Path)
    parser.add_argument("--runs-base", type=Path, default=ROOT / "workspace/private/runs/audio")
    parser.add_argument("--previous-gate2-manifest", type=Path, default=DEFAULT_PREVIOUS_GATE2_MANIFEST)
    parser.add_argument("--private-manifest", type=Path)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_dir = args.source_run_dir or latest_v2632_run(args.runs_base)
    private_manifest = args.private_manifest or (run_dir / DEFAULT_PRIVATE_NAME)
    manifest = build_manifest(run_dir, args.previous_gate2_manifest)
    write_json(private_manifest, manifest, 0o600)
    payload = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": f"v2633-setcal-gate2-handoff-{'ready' if manifest.get('ok') else 'needs-review'}",
        "ok": bool(manifest.get("ok")),
        "source_run_dir": rel(run_dir),
        "private_manifest": rel(private_manifest),
        "summary": manifest.get("summary", {}),
        "native_replay_ready": False,
    }
    if args.write_report:
        write_report(args.report_path, manifest, private_manifest)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
