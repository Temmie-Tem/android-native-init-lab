#!/usr/bin/env python3
"""V2652 host-only decoder for existing real Android-good ACDB SET arg bytes.

This consumes prior private ptrace JSONL captures for /dev/msm_audio_cal and
decodes only the public-safe AUDIO_SET_CALIBRATION header scalars from captured
ioctl argument bytes.  It never emits raw arg bytes or payload bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2652"
BUILD_TAG = "v2652-audio-acdb-real-set-arg-decode"
DEFAULT_RUNS_ROOT = ROOT / "workspace/private/runs/audio"
DEFAULT_BUILDS_ROOT = ROOT / "workspace/private/builds/audio"
DEFAULT_BUILD_ROOT = DEFAULT_BUILDS_ROOT / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2652_AUDIO_ACDB_REAL_SET_ARG_DECODE_2026-06-18.md"
DEFAULT_SETCAL_CAPTURE = (
    ROOT
    / "workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701/ownget-device-artifacts/setcal-events.jsonl"
)

AUDIO_SET_CALIBRATION = 0xC00461CB
V2639_NATIVE_REPLAY_ORDER = [39, 13, 9, 11, 12, 15, 23, 16, 21]


@dataclass(frozen=True)
class SetArgRecord:
    source: str
    run_dir: str
    sequence: int | None
    tid: int | None
    fd_pid: int | None
    ts_ms: int | None
    read_len: int
    data_size: int
    version: int
    cal_type: int
    cal_type_size: int
    cal_hdr_version: int
    buffer_number: int
    cal_size: int
    mem_handle: int
    arg_sha256: str
    scalar_words: list[int]

    def public_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "run_dir": self.run_dir,
            "sequence": self.sequence,
            "tid": self.tid,
            "fd_pid": self.fd_pid,
            "ts_ms": self.ts_ms,
            "read_len": self.read_len,
            "data_size": self.data_size,
            "version": self.version,
            "cal_type": self.cal_type,
            "cal_type_size": self.cal_type_size,
            "cal_hdr_version": self.cal_hdr_version,
            "buffer_number": self.buffer_number,
            "cal_size": self.cal_size,
            "mem_handle": self.mem_handle,
            "arg_sha256": self.arg_sha256,
            "scalar_words": self.scalar_words,
        }


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip(), 0)
        except ValueError:
            return None
    return None


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                yield item


def run_dir_from_path(path: Path, runs_root: Path) -> str:
    try:
        return path.resolve().relative_to(runs_root.resolve()).parts[0]
    except (ValueError, IndexError):
        return "unknown"


def decode_set_arg_bytes(bytes_hex: str) -> dict[str, Any]:
    blob = bytes.fromhex(bytes_hex)
    if len(blob) < 32:
        raise ValueError("SET arg buffer shorter than 32-byte msm_audio_cal header")
    words = list(struct.unpack(f"<{len(blob) // 4}I", blob[: len(blob) - (len(blob) % 4)]))
    mem_handle = struct.unpack("<i", blob[28:32])[0]
    data_size = words[0]
    digest_len = min(max(data_size, 0), len(blob))
    declared_len = min(max(data_size, 32), len(blob))
    declared_word_count = declared_len // 4
    return {
        "read_len": len(blob),
        "data_size": data_size,
        "version": words[1],
        "cal_type": words[2],
        "cal_type_size": words[3],
        "cal_hdr_version": words[4],
        "buffer_number": words[5],
        "cal_size": words[6],
        "mem_handle": mem_handle,
        "arg_sha256": hashlib.sha256(blob[:digest_len]).hexdigest(),
        "scalar_words": words[8:declared_word_count],
    }


def row_to_set_record(path: Path, row: dict[str, Any], runs_root: Path) -> SetArgRecord | None:
    if parse_int(row.get("request")) != AUDIO_SET_CALIBRATION:
        return None
    bytes_hex = row.get("bytes_hex")
    if not isinstance(bytes_hex, str) or not bytes_hex:
        return None
    try:
        decoded = decode_set_arg_bytes(bytes_hex)
    except (ValueError, struct.error):
        return None
    return SetArgRecord(
        source=rel(path),
        run_dir=run_dir_from_path(path, runs_root),
        sequence=parse_int(row.get("seq")),
        tid=parse_int(row.get("tid")),
        fd_pid=parse_int(row.get("fd_pid")),
        ts_ms=parse_int(row.get("ts_ms")),
        **decoded,
    )


def iter_trace_paths(runs_root: Path) -> list[Path]:
    return sorted(runs_root.glob("v24*/**/msm-audio-cal-*.jsonl"))


def load_real_set_records(runs_root: Path) -> list[SetArgRecord]:
    records: list[SetArgRecord] = []
    for path in iter_trace_paths(runs_root):
        for row in iter_jsonl(path):
            record = row_to_set_record(path, row, runs_root)
            if record is not None:
                records.append(record)
    return records


def load_v2632_fake_set_order(path: Path) -> list[int]:
    order: list[int] = []
    if not path.exists():
        return order
    for row in iter_jsonl(path):
        if parse_int(row.get("request")) != AUDIO_SET_CALIBRATION and row.get("event") not in {
            "setcal_capture",
            "setcal_exact_arg",
        }:
            continue
        cal_type = parse_int(row.get("cal_type"))
        if cal_type is not None:
            order.append(cal_type)
    return order


def count_request_numbers(runs_root: Path) -> Counter[int]:
    counts: Counter[int] = Counter()
    for path in iter_trace_paths(runs_root):
        for row in iter_jsonl(path):
            request = parse_int(row.get("request"))
            if request is not None:
                counts[request] += 1
    return counts


def summarize_records(records: list[SetArgRecord]) -> dict[str, Any]:
    by_type: Counter[int] = Counter(record.cal_type for record in records)
    by_run: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sorted(records, key=lambda item: (item.run_dir, item.source, item.sequence or -1)):
        by_run[record.run_dir].append(record.public_dict())

    per_type_shapes: dict[str, list[dict[str, Any]]] = {}
    for cal_type in sorted(by_type):
        shapes = {
            (
                record.data_size,
                record.cal_type_size,
                record.buffer_number,
                record.cal_size,
                record.mem_handle,
                tuple(record.scalar_words),
            )
            for record in records
            if record.cal_type == cal_type
        }
        per_type_shapes[str(cal_type)] = [
            {
                "data_size": shape[0],
                "cal_type_size": shape[1],
                "buffer_number": shape[2],
                "cal_size": shape[3],
                "mem_handle": shape[4],
                "scalar_words": list(shape[5]),
            }
            for shape in sorted(shapes)
        ]
    return {
        "count": len(records),
        "cal_type_counts": dict(sorted(by_type.items())),
        "per_run_order": {
            run_dir: [record["cal_type"] for record in rows]
            for run_dir, rows in sorted(by_run.items())
        },
        "per_type_shapes": per_type_shapes,
        "records": [record.public_dict() for record in records],
    }


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    runs_root = Path(args.runs_root)
    records = load_real_set_records(runs_root)
    request_counts = count_request_numbers(runs_root)
    fake_order = load_v2632_fake_set_order(Path(args.setcal_capture))
    real_types = sorted({record.cal_type for record in records})
    native_types = set(V2639_NATIVE_REPLAY_ORDER)
    extra_types = sorted(set(real_types) - native_types)

    decision = "v2652-no-real-set-arg-bytes-found"
    if records and extra_types:
        decision = "v2652-extra-real-set-cal20-found-host-only" if extra_types == [20] else "v2652-extra-real-set-found-host-only"
    elif records:
        decision = "v2652-real-set-bytes-decode-no-extra-type"

    payload = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "generated_at": now_iso(),
        "ok": True,
        "decision": decision,
        "scope": "host-only existing private ptrace byte decode; no device action",
        "inputs": {
            "runs_root": rel(runs_root),
            "trace_file_count": len(iter_trace_paths(runs_root)),
            "setcal_capture": rel(Path(args.setcal_capture)),
        },
        "request_counts": {f"0x{request:08x}": count for request, count in sorted(request_counts.items())},
        "orders": {
            "v2632_fake_set_capture": fake_order,
            "v2639_native_replay": V2639_NATIVE_REPLAY_ORDER,
        },
        "real_set_decode": summarize_records(records),
        "conclusions": {
            "real_set_arg_bytes_present": bool(records),
            "decoded_real_cal_types": real_types,
            "extra_real_cal_types_not_in_native_replay": extra_types,
            "cal_type8_seen": 8 in real_types,
            "cal_type20_seen": 20 in real_types,
            "prepare_post_seen": any(request in request_counts for request in (0xC00461CA, 0xC00461CD)),
            "raw_bytes_publicly_emitted": False,
            "new_live_capture_needed_before_this_decode": False,
            "native_replay_should_not_rerun_unchanged": bool(extra_types),
        },
    }
    return payload


def write_manifest(path: Path, payload: dict[str, Any], *, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def format_order(order: list[int]) -> str:
    return ", ".join(str(value) for value in order) if order else "(none)"


def write_report(path: Path, payload: dict[str, Any]) -> None:
    real = payload["real_set_decode"]
    conclusions = payload["conclusions"]
    lines = [
        "# NATIVE_INIT V2652 — ACDB real Android-good SET arg decode",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only decode of existing private ptrace `bytes_hex` for real Android-good",
        "`AUDIO_SET_CALIBRATION` calls. No device action, flash, playback, mixer write,",
        "calibration ioctl, or raw payload publication occurred. Raw ioctl argument bytes",
        "remain private under `workspace/private/`.",
        "",
        "## Decision",
        "",
        f"- `decision`: `{payload['decision']}`",
        f"- `ok`: `{payload['ok']}`",
        f"- decoded real SET records: `{real['count']}`",
        f"- decoded real cal_types: `{format_order(conclusions['decoded_real_cal_types'])}`",
        f"- extra cal_types absent from V2639 native replay: `{format_order(conclusions['extra_real_cal_types_not_in_native_replay'])}`",
        "",
        "## Order Comparison",
        "",
        "| Source | SET cal_type order | Notes |",
        "| --- | --- | --- |",
        f"| V2632 fake SET capture | `{format_order(payload['orders']['v2632_fake_set_capture'])}` | own-process HAL-layer fake SET capture |",
        f"| V2639/V2648 native replay | `{format_order(payload['orders']['v2639_native_replay'])}` | topology 39 prepended, all kernel-accepted in native replay |",
        "| Existing real Android-good ptrace bytes | see per-run table below | real kernel ioctl arg bytes from older captures |",
        "",
        "## Real Android-good Decoded SET Types",
        "",
    ]
    for cal_type, count in real["cal_type_counts"].items():
        lines.append(f"- cal_type `{cal_type}`: `{count}` records")
    lines.extend(
        [
            "",
            "### Distinct decoded shapes",
            "",
            "| cal_type | data_size | cal_type_size | buffer | cal_size | mem_handle | scalar words after header |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for cal_type, shapes in real["per_type_shapes"].items():
        for shape in shapes:
            lines.append(
                f"| `{cal_type}` | `{shape['data_size']}` | `{shape['cal_type_size']}` | "
                f"`{shape['buffer_number']}` | `{shape['cal_size']}` | `{shape['mem_handle']}` | "
                f"`{shape['scalar_words']}` |"
            )
    lines.extend(["", "### Per-run order", "", "| Run | Decoded real SET order |", "| --- | --- |"])
    for run_dir, order in sorted(real["per_run_order"].items()):
        lines.append(f"| `{run_dir}` | `{format_order(order)}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "V2651 correctly identified that a decoded real Android-good SET order was missing,",
            "but the older ptrace JSONL already carried enough private `bytes_hex` to decode",
            "the ioctl argument headers host-only. That decode finds real kernel",
            "`AUDIO_SET_CALIBRATION` calls for cal_type `39` and cal_type `20`.",
            "",
            "The cal_type `39` entries are the expected 4916-byte topology SET. The cal_type",
            "`20` entries are header-only (`cal_size=0`, `mem_handle=-1`) and were not present",
            "in the V2632 fake SET-layer manifest or in the V2639/V2648 native replay order.",
            "This is a concrete extra Android-good SET edge and another unchanged native replay",
            "is not justified until cal_type `20` placement/semantics are handled.",
            "",
            "This decode does **not** show a real cal_type `8` SET and does **not** show",
            "`AUDIO_PREPARE_CALIBRATION` or `AUDIO_POST_CALIBRATION` in the existing ptrace",
            "evidence. Raw arg bytes and hashes are omitted from this public report.",
            "",
            "## Validation",
            "",
            "- `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec were reread.",
            "- Existing private JSONL ptrace bytes were parsed host-only.",
            "- The public report includes only scalar decoded headers, not raw arg bytes.",
            "- `py_compile`, focused unittest, and `git diff --check` were run.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--setcal-capture", type=Path, default=DEFAULT_SETCAL_CAPTURE)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = manifest(args)
    write_manifest(Path(args.manifest_path), payload, pretty=args.pretty)
    if args.write_report:
        write_report(Path(args.report_path), payload)
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
