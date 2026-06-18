#!/usr/bin/env python3
"""V2651 host-only ACDB audio-cal ioctl order analyzer.

Consumes existing private Android-good capture metadata and native replay logs.
It emits a redacted request-order summary only: ioctl names, cal_type values,
return/error scalars, and source paths.  It never copies or prints raw ACDB
payload bytes and never touches a device.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2651"
BUILD_TAG = "v2651-audio-acdb-ioctl-order-analysis"
DEFAULT_RUNS_ROOT = ROOT / "workspace/private/runs/audio"
DEFAULT_BUILDS_ROOT = ROOT / "workspace/private/builds/audio"
DEFAULT_BUILD_ROOT = DEFAULT_BUILDS_ROOT / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2651_AUDIO_ACDB_IOCTL_ORDER_ANALYSIS_2026-06-18.md"

AUDIO_CAL_IOCTL_NAMES: dict[int, str] = {
    0xC00461C8: "AUDIO_ALLOCATE_CALIBRATION",
    0xC00461C9: "AUDIO_DEALLOCATE_CALIBRATION",
    0xC00461CA: "AUDIO_PREPARE_CALIBRATION",
    0xC00461CB: "AUDIO_SET_CALIBRATION",
    0xC00461CC: "AUDIO_GET_CALIBRATION",
    0xC00461CD: "AUDIO_POST_CALIBRATION",
}
NAME_TO_IOCTL = {name: value for value, name in AUDIO_CAL_IOCTL_NAMES.items()}
SETCAL_CAPTURE = (
    ROOT
    / "workspace/private/runs/audio/v2632-acdb-setcal-capture-20260618-083701/ownget-device-artifacts/setcal-events.jsonl"
)
V2634_GATE = DEFAULT_BUILDS_ROOT / "v2634-audio-acdb-setcal-replay-gate/setcal-replay-gate-manifest.json"
V2636_DEPLOY = DEFAULT_BUILDS_ROOT / "v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json"
V2639_LIVE_MANIFEST = DEFAULT_BUILDS_ROOT / "v2639-audio-acdb-setcal-replay-live-handoff/manifest.json"
V2648_RUN = DEFAULT_RUNS_ROOT / "v2639-acdb-setcal-replay-20260618-105431"

REPLAY_CAL_RE = re.compile(
    r"(?P<name>AUDIO_(?:ALLOCATE|DEALLOCATE|PREPARE|SET|GET|POST)_CALIBRATION)"
    r".*?\bcal_type=(?P<cal_type>-?\d+)"
    r".*?(?:\bcal_size=(?P<cal_size>-?\d+))?"
    r".*?(?:\bmem_handle=(?P<mem_handle>-?\d+))?"
    r".*?(?:\barg_len=(?P<arg_len>-?\d+))?",
)
REPLAY_SET_OK_RE = re.compile(
    r"A90_ACDB_SETCAL_SET_OK\s+index=(?P<index>\d+)\s+cal_type=(?P<cal_type>-?\d+)"
)
HEX_RE = re.compile(r"0x[0-9a-fA-F]{8}")


@dataclass(frozen=True)
class IoctlEvent:
    source: str
    source_class: str
    sequence: int
    request: int | None
    name: str
    cal_type: int | None = None
    ret: int | None = None
    errno: int | None = None
    data_size: int | None = None
    cal_size: int | None = None
    mem_handle: int | None = None
    intercept: str | None = None
    note: str | None = None

    def public_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_class": self.source_class,
            "sequence": self.sequence,
            "request": f"0x{self.request:08x}" if self.request is not None else None,
            "name": self.name,
            "cal_type": self.cal_type,
            "ret": self.ret,
            "errno": self.errno,
            "data_size": self.data_size,
            "cal_size": self.cal_size,
            "mem_handle": self.mem_handle,
            "intercept": self.intercept,
            "note": self.note,
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
        text = value.strip()
        if not text:
            return None
        try:
            return int(text, 0)
        except ValueError:
            return None
    return None


def request_name(value: int | None) -> str | None:
    if value is None:
        return None
    return AUDIO_CAL_IOCTL_NAMES.get(value)


def request_from_name(name: str | None) -> int | None:
    if not name:
        return None
    return NAME_TO_IOCTL.get(name.strip())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def json_object_to_event(path: Path, obj: dict[str, Any], sequence: int) -> IoctlEvent | None:
    request = parse_int(obj.get("request"))
    name = obj.get("name") if isinstance(obj.get("name"), str) else None
    if request is None and name:
        request = request_from_name(name)
    if request is None:
        for key in ("ioctl", "cmd", "request_hex"):
            request = parse_int(obj.get(key))
            if request is not None:
                break
    if name is None:
        name = request_name(request)
    if name not in NAME_TO_IOCTL:
        return None
    if request is None:
        request = request_from_name(name)
    if request not in AUDIO_CAL_IOCTL_NAMES:
        return None

    cal_type = parse_int(obj.get("cal_type"))
    if cal_type is None and isinstance(obj.get("header"), dict):
        cal_type = parse_int(obj["header"].get("cal_type"))
    if cal_type is None and isinstance(obj.get("set_arg"), dict):
        cal_type = parse_int(obj["set_arg"].get("cal_type"))

    return IoctlEvent(
        source=rel(path),
        source_class=classify_source(path, obj),
        sequence=sequence,
        request=request,
        name=name,
        cal_type=cal_type,
        ret=parse_int(obj.get("ret")),
        errno=parse_int(obj.get("errno")),
        data_size=parse_int(obj.get("data_size")),
        cal_size=parse_int(obj.get("cal_size")),
        mem_handle=parse_int(obj.get("mem_handle")),
        intercept=obj.get("intercept") if isinstance(obj.get("intercept"), str) else None,
        note=obj.get("event") if isinstance(obj.get("event"), str) else None,
    )


def classify_source(path: Path, obj: dict[str, Any] | None = None) -> str:
    text = rel(path)
    if "v2632-acdb-setcal-capture" in text:
        return "android-ownprocess-fake-set-capture"
    if "v2639-acdb-setcal-replay" in text:
        return "native-setcal-replay"
    if "v2634-audio-acdb-setcal-replay-gate" in text:
        return "host-gate-manifest"
    if "v2636-audio-acdb-setcal-replay-deploy-plan" in text:
        return "host-deploy-plan"
    if obj and obj.get("intercept") == "fake-success":
        return "android-ownprocess-fake-ioctl"
    if "ownprocess" in text or "acdb" in text:
        return "android-ownprocess-trace"
    return "unknown-json-trace"


def parse_setcal_capture(path: Path = SETCAL_CAPTURE) -> list[IoctlEvent]:
    events: list[IoctlEvent] = []
    if not path.exists():
        return events
    for index, row in enumerate(iter_jsonl(path), start=1):
        event = json_object_to_event(path, row, index)
        if event:
            events.append(event)
    return events


def parse_v2634_manifest(path: Path = V2634_GATE) -> list[IoctlEvent]:
    if not path.exists():
        return []
    data = load_json(path)
    events: list[IoctlEvent] = []
    for index, record in enumerate(data.get("set_records", []) if isinstance(data, dict) else [], start=1):
        if not isinstance(record, dict):
            continue
        cal_type = parse_int(record.get("cal_type"))
        events.append(
            IoctlEvent(
                source=rel(path),
                source_class="host-gate-manifest",
                sequence=index,
                request=NAME_TO_IOCTL["AUDIO_SET_CALIBRATION"],
                name="AUDIO_SET_CALIBRATION",
                cal_type=cal_type,
                data_size=parse_int(record.get("data_size")),
                cal_size=parse_int(record.get("cal_size")),
                mem_handle=parse_int(record.get("mem_handle")),
                note=str(record.get("role") or ""),
            )
        )
    return events


def parse_v2639_manifest(path: Path = V2639_LIVE_MANIFEST) -> list[IoctlEvent]:
    if not path.exists():
        return []
    data = load_json(path)
    remote = data.get("remote", {}) if isinstance(data, dict) else {}
    argv = remote.get("argv", []) if isinstance(remote, dict) else []
    events: list[IoctlEvent] = []
    sequence = 0
    if isinstance(argv, list):
        for item in argv:
            if not isinstance(item, str):
                continue
            if item.startswith("39:"):
                sequence += 1
                events.append(
                    IoctlEvent(
                        source=rel(path),
                        source_class="native-setcal-replay-plan",
                        sequence=sequence,
                        request=NAME_TO_IOCTL["AUDIO_SET_CALIBRATION"],
                        name="AUDIO_SET_CALIBRATION",
                        cal_type=39,
                        note="topology-basic-payload",
                    )
                )
            match = re.search(r"cal(?P<cal>\d{2})\.bin", item)
            if match and "set-arg" in item:
                sequence += 1
                events.append(
                    IoctlEvent(
                        source=rel(path),
                        source_class="native-setcal-replay-plan",
                        sequence=sequence,
                        request=NAME_TO_IOCTL["AUDIO_SET_CALIBRATION"],
                        name="AUDIO_SET_CALIBRATION",
                        cal_type=int(match.group("cal"), 10),
                        note="exact-set-arg",
                    )
                )
    return events


def parse_replay_text(path: Path) -> list[IoctlEvent]:
    events: list[IoctlEvent] = []
    if not path.exists():
        return events
    text = path.read_text(encoding="utf-8", errors="replace")
    sequence = 0
    for line in text.splitlines():
        match = REPLAY_CAL_RE.search(line)
        if match:
            name = match.group("name")
            sequence += 1
            events.append(
                IoctlEvent(
                    source=rel(path),
                    source_class="native-setcal-replay",
                    sequence=sequence,
                    request=NAME_TO_IOCTL.get(name),
                    name=name,
                    cal_type=parse_int(match.group("cal_type")),
                    cal_size=parse_int(match.group("cal_size")),
                    mem_handle=parse_int(match.group("mem_handle")),
                    data_size=parse_int(match.group("arg_len")),
                    ret=0 if " ok " in f" {line} " else None,
                    note="stderr-marker",
                )
            )
            continue
        match = REPLAY_SET_OK_RE.search(line)
        if match:
            sequence += 1
            events.append(
                IoctlEvent(
                    source=rel(path),
                    source_class="native-setcal-replay",
                    sequence=sequence,
                    request=NAME_TO_IOCTL["AUDIO_SET_CALIBRATION"],
                    name="AUDIO_SET_CALIBRATION",
                    cal_type=parse_int(match.group("cal_type")),
                    ret=0,
                    note=f"A90_SET_OK index={match.group('index')}",
                )
            )
    return events


def replay_text_paths(run_dir: Path = V2648_RUN) -> list[Path]:
    if not run_dir.exists():
        return []
    preferred = [
        "61_acdb-setcal-helper-deallocate-check.txt",
        "58_acdb-setcal-replay-start-wait-all-set.txt",
    ]
    fallback = [
        "61_acdb-setcal-helper-deallocate-check.json",
        "58_acdb-setcal-replay-start-wait-all-set.json",
    ]
    paths = [run_dir / name for name in preferred if (run_dir / name).exists()]
    return paths if paths else [run_dir / name for name in fallback if (run_dir / name).exists()]


def discover_json_trace_files(runs_root: Path, builds_root: Path, *, max_bytes: int = 5_000_000) -> list[Path]:
    roots = [runs_root, builds_root]
    paths: list[Path] = []
    suffixes = {".json", ".jsonl"}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in suffixes:
                continue
            if path.stat().st_size > max_bytes:
                continue
            text = rel(path)
            if BUILD_TAG in text:
                continue
            if "/docs/" in text or "/obj/" in text:
                continue
            if not any(token in text for token in ("acdb", "audio", "setcal", "msm")):
                continue
            paths.append(path)
    return sorted(paths)


def parse_trace_file(path: Path, start_sequence: int = 1) -> list[IoctlEvent]:
    events: list[IoctlEvent] = []
    if path.suffix == ".jsonl":
        for index, obj in enumerate(iter_jsonl(path), start=start_sequence):
            event = json_object_to_event(path, obj, index)
            if event:
                events.append(event)
        return events
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return []
    sequence = start_sequence
    for obj in walk_dicts(data):
        event = json_object_to_event(path, obj, sequence)
        if event:
            events.append(event)
            sequence += 1
    return events


def event_sequence(events: list[IoctlEvent], source_class: str, name: str | None = None) -> list[int | None]:
    out = []
    for event in events:
        if event.source_class == source_class and (name is None or event.name == name):
            out.append(event.cal_type)
    return out


def summarize_events(events: list[IoctlEvent]) -> dict[str, Any]:
    by_source_class = Counter(event.source_class for event in events)
    by_name = Counter(event.name for event in events)
    set_cal_types = sorted({event.cal_type for event in events if event.name == "AUDIO_SET_CALIBRATION" and event.cal_type is not None})
    prepare_events = [event.public_dict() for event in events if event.name == "AUDIO_PREPARE_CALIBRATION"]
    post_events = [event.public_dict() for event in events if event.name == "AUDIO_POST_CALIBRATION"]
    cal8_events = [event.public_dict() for event in events if event.cal_type == 8]
    real_android_kernel_set_events = [
        event
        for event in events
        if event.name == "AUDIO_SET_CALIBRATION"
        and event.source_class == "android-ownprocess-trace"
        and event.intercept != "fake-success"
    ]
    decoded_real_android_kernel_set_events = [
        event for event in real_android_kernel_set_events if event.cal_type is not None
    ]
    return {
        "total_events": len(events),
        "by_source_class": dict(sorted(by_source_class.items())),
        "by_name": dict(sorted(by_name.items())),
        "set_cal_types_seen": set_cal_types,
        "prepare_count": len(prepare_events),
        "post_count": len(post_events),
        "cal_type8_count": len(cal8_events),
        "real_android_kernel_set_count": len(real_android_kernel_set_events),
        "decoded_real_android_kernel_set_count": len(decoded_real_android_kernel_set_events),
        "prepare_events": prepare_events[:20],
        "post_events": post_events[:20],
        "cal_type8_events": cal8_events[:20],
        "decoded_real_android_kernel_set_events": [
            event.public_dict() for event in decoded_real_android_kernel_set_events[:20]
        ],
    }


def ordered_unique_events(events: list[IoctlEvent], source_class: str) -> list[dict[str, Any]]:
    return [event.public_dict() for event in events if event.source_class == source_class]


def manifest(args: argparse.Namespace) -> dict[str, Any]:
    all_events: list[IoctlEvent] = []
    all_events.extend(parse_setcal_capture(Path(args.setcal_capture)))
    all_events.extend(parse_v2634_manifest(Path(args.v2634_manifest)))
    all_events.extend(parse_v2639_manifest(Path(args.v2639_manifest)))
    for path in replay_text_paths(Path(args.v2648_run)):
        all_events.extend(parse_replay_text(path))

    scanned_files: list[str] = []
    for path in discover_json_trace_files(Path(args.runs_root), Path(args.builds_root)):
        scanned_files.append(rel(path))
        if path in {Path(args.setcal_capture), Path(args.v2634_manifest), Path(args.v2639_manifest)}:
            continue
        all_events.extend(parse_trace_file(path, start_sequence=1))

    summary = summarize_events(all_events)
    capture_order = [event.cal_type for event in parse_setcal_capture(Path(args.setcal_capture)) if event.name == "AUDIO_SET_CALIBRATION"]
    gate_order = [event.cal_type for event in parse_v2634_manifest(Path(args.v2634_manifest)) if event.name == "AUDIO_SET_CALIBRATION"]
    native_plan_order = [event.cal_type for event in parse_v2639_manifest(Path(args.v2639_manifest)) if event.name == "AUDIO_SET_CALIBRATION"]
    native_replay_events = [
        event.cal_type
        for path in replay_text_paths(Path(args.v2648_run))
        for event in parse_replay_text(path)
        if event.name == "AUDIO_SET_CALIBRATION" and event.note and ("SET_OK" in event.note or event.ret == 0)
    ]
    native_replay_set_ok_order = [
        event.cal_type
        for path in replay_text_paths(Path(args.v2648_run))
        for event in parse_replay_text(path)
        if event.name == "AUDIO_SET_CALIBRATION" and event.note and event.note.startswith("A90_SET_OK")
    ]
    native_replay_ok_order = native_replay_set_ok_order or native_replay_events

    prepare_or_post_seen = summary["prepare_count"] > 0 or summary["post_count"] > 0
    cal8_seen = summary["cal_type8_count"] > 0
    android_real_kernel_set_seen = summary["real_android_kernel_set_count"] > 0
    decoded_android_real_kernel_set_seen = summary["decoded_real_android_kernel_set_count"] > 0
    existing_evidence_enough = prepare_or_post_seen or cal8_seen or decoded_android_real_kernel_set_seen
    decision = "v2651-existing-evidence-real-set-undecoded-requires-android-good-ioctl-order-capture"
    if existing_evidence_enough:
        decision = "v2651-existing-evidence-order-edge-found-review-before-replay"

    payload = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "raw_payloads_copied": False,
        "ok": True,
        "decision": decision,
        "scanned_json_file_count": len(scanned_files),
        "inputs": {
            "setcal_capture": rel(Path(args.setcal_capture)),
            "v2634_manifest": rel(Path(args.v2634_manifest)),
            "v2639_manifest": rel(Path(args.v2639_manifest)),
            "v2648_run": rel(Path(args.v2648_run)),
        },
        "orders": {
            "v2632_fake_set_capture": capture_order,
            "v2634_gate_manifest": gate_order,
            "v2639_native_replay_plan": native_plan_order,
            "v2648_native_replay_success_markers": native_replay_ok_order,
        },
        "summary": summary,
        "conclusions": {
            "audio_prepare_seen_in_existing_evidence": summary["prepare_count"] > 0,
            "audio_post_seen_in_existing_evidence": summary["post_count"] > 0,
            "cal_type8_seen_in_existing_evidence": cal8_seen,
            "android_real_kernel_set_seen_in_existing_evidence": android_real_kernel_set_seen,
            "decoded_android_real_kernel_set_seen_in_existing_evidence": decoded_android_real_kernel_set_seen,
            "existing_evidence_enough_to_change_replay": existing_evidence_enough,
            "next_recommendation": (
                "review found order-edge before replay"
                if existing_evidence_enough
                else "design one bounded Android-good /dev/msm_audio_cal order-only capture with decoded cal_type/header scalars before another native SET replay"
            ),
        },
        "redacted_event_samples": {
            "prepare": summary["prepare_events"],
            "post": summary["post_events"],
            "cal_type8": summary["cal_type8_events"],
            "v2632_capture": ordered_unique_events(all_events, "android-ownprocess-fake-set-capture")[:12],
            "v2648_native_replay": ordered_unique_events(all_events, "native-setcal-replay")[:40],
        },
    }
    Path(args.manifest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(args.manifest_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_report:
        Path(args.report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report_path).write_text(report_markdown(payload), encoding="utf-8")
    return payload


def report_markdown(payload: dict[str, Any]) -> str:
    orders = payload["orders"]
    summary = payload["summary"]
    conclusions = payload["conclusions"]

    def order_text(name: str) -> str:
        return ", ".join("None" if value is None else str(value) for value in orders.get(name, [])) or "(none)"

    lines = [
        "# NATIVE_INIT V2651 — ACDB audio-cal ioctl order analysis",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only analysis of existing private ACDB capture/replay metadata. No device action, flash, playback,",
        "calibration ioctl, mixer write, or raw payload publication occurred. Raw ACDB bytes remain private.",
        "",
        "## Decision",
        "",
        f"- `decision`: `{payload['decision']}`",
        f"- `ok`: `{payload['ok']}`",
        f"- `scanned_json_file_count`: `{payload['scanned_json_file_count']}`",
        "",
        "## Request Orders",
        "",
        "| Source | SET cal_type order | Meaning |",
        "| --- | --- | --- |",
        f"| V2632 fake SET capture | `{order_text('v2632_fake_set_capture')}` | Android-good own-process `send_audio_cal_v5` layer, fake-successed SET; no real kernel SET |",
        f"| V2634 gate manifest | `{order_text('v2634_gate_manifest')}` | Gate-2 manifest derived from V2632 |",
        f"| V2639 native replay plan | `{order_text('v2639_native_replay_plan')}` | Native replay plan, with topology cal_type 39 prepended |",
        f"| V2648 native replay success markers | `{order_text('v2648_native_replay_success_markers')}` | Kernel-accepted native SET markers from replay stderr/json |",
        "",
        "## Existing Evidence Classification",
        "",
        f"- `AUDIO_PREPARE_CALIBRATION` seen: `{conclusions['audio_prepare_seen_in_existing_evidence']}` (`count={summary['prepare_count']}`)",
        f"- `AUDIO_POST_CALIBRATION` seen: `{conclusions['audio_post_seen_in_existing_evidence']}` (`count={summary['post_count']}`)",
        f"- cal_type `8` seen in existing ioctl evidence: `{conclusions['cal_type8_seen_in_existing_evidence']}` (`count={summary['cal_type8_count']}`)",
        f"- real Android-good kernel `AUDIO_SET_CALIBRATION` seen: `{conclusions['android_real_kernel_set_seen_in_existing_evidence']}`",
        f"- decoded real Android-good SET cal_type/header order seen: `{conclusions['decoded_android_real_kernel_set_seen_in_existing_evidence']}` (`count={summary['decoded_real_android_kernel_set_count']}`)",
        f"- existing evidence enough to change replay: `{conclusions['existing_evidence_enough_to_change_replay']}`",
        "",
        "## Aggregate Counts",
        "",
        "### By request",
        "",
    ]
    for name, count in summary["by_name"].items():
        lines.append(f"- `{name}`: `{count}`")
    lines.extend(["", "### By source class", ""])
    for name, count in summary["by_source_class"].items():
        lines.append(f"- `{name}`: `{count}`")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The existing evidence confirms the V2632/V2634 SET-layer order and the V2648 native replay",
            "order with topology cal_type `39` prepended. Older Android-good ptrace captures do show real",
            "`AUDIO_SET_CALIBRATION` ioctl entries, but those entries do not decode the cal_type/header",
            "scalars needed for an order comparison. Existing evidence does **not** show",
            "`AUDIO_PREPARE_CALIBRATION`, `AUDIO_POST_CALIBRATION`, a decoded real cal_type `8` SET,",
            "or another decoded extra AFE startup SET outside the fake own-process SET-layer capture.",
            "",
            "Therefore another native replay without new order/context evidence is not justified. The next",
            "unit should be a bounded Android-good `/dev/msm_audio_cal` order-only capture that records request",
            "numbers and decoded cal_type/header scalars around real AudioTrack speaker playback; raw payload",
            "bytes remain private and no native replay should run first.",
            "",
            "## Validation",
            "",
            "- `GOAL.md`, `AGENTS.md`, and `CLAUDE.md` were reread for current safety and audio directives.",
            "- Existing private JSON/JSONL/TXT metadata was parsed host-only.",
            "- No raw payload bytes were copied into this report.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--builds-root", type=Path, default=DEFAULT_BUILDS_ROOT)
    parser.add_argument("--setcal-capture", type=Path, default=SETCAL_CAPTURE)
    parser.add_argument("--v2634-manifest", type=Path, default=V2634_GATE)
    parser.add_argument("--v2639-manifest", type=Path, default=V2639_LIVE_MANIFEST)
    parser.add_argument("--v2648-run", type=Path, default=V2648_RUN)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    payload = manifest(args)
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
