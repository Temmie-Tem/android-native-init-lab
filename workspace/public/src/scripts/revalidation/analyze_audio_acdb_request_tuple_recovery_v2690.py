#!/usr/bin/env python3
"""V2690 host-only ACDB custom-topology request-tuple audit.

This analyzer reconciles the last useful captured lower-call artifacts after
V2689 falsified the core-derived/defined-module topology guesses.  It does not
run a device step and never emits raw private payload bytes.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any, Iterable


REPO = Path(__file__).resolve().parents[5]
DEFAULT_V2675_RUN = REPO / (
    "workspace/private/runs/audio/"
    "v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431"
)
DEFAULT_V2689_REPORT = REPO / (
    "docs/reports/"
    "NATIVE_INIT_V2689_AUDIO_ACDB_DEFINED_MODULE_TOPOLOGY_LIVE_REPLAY_2026-06-18.md"
)
DEFAULT_REPORT = REPO / (
    "docs/reports/"
    "NATIVE_INIT_V2690_AUDIO_ACDB_REQUEST_TUPLE_RECOVERY_AUDIT_2026-06-18.md"
)

TARGETS: dict[int, dict[str, Any]] = {
    24: {"cmd": 0x130DA, "label": "AFE_CUSTOM_TOPOLOGY", "expected_topology": 0x1001025D},
    10: {"cmd": 0x11394, "label": "ADM_CUSTOM_TOPOLOGY", "expected_topology": 0x10004000},
    14: {"cmd": 0x12E01, "label": "ASM_CUSTOM_TOPOLOGY", "expected_topology": 0x10005000},
}
CMD_TO_CAL = {int(info["cmd"]): cal_type for cal_type, info in TARGETS.items()}
LOWER_EVENT_RE = re.compile(
    r'"stage":"(?P<stage>[^"]+)","code":(?P<code>-?\d+),'
    r'"cal_type":(?P<cal_type>\d+),"value":(?P<value>0x[0-9a-fA-F]+)'
)


@dataclasses.dataclass(frozen=True)
class LowerStage:
    stage: str
    code: int
    cal_type: int
    value: int


@dataclasses.dataclass(frozen=True)
class TapRecord:
    seq: int
    cal_type: int
    cmd: int
    cmd_hex: str
    input_words: list[int]
    input_sha256: str
    output_ret: int | None
    output_size: int | None
    output_sha256: str
    output_all_zero: bool | None


@dataclasses.dataclass(frozen=True)
class SetCalRecord:
    sequence: int
    cal_type: int
    data_size: int
    cal_size: int
    mem_handle: int
    arg_sha256: str
    dmabuf_sha256: str
    dmabuf_status: str


@dataclasses.dataclass(frozen=True)
class CalAudit:
    cal_type: int
    label: str
    cmd_hex: str
    create_ok: bool
    allocate_ok: bool
    get_ret: int | None
    get_size: int | None
    request_words_hex: list[str]
    request_sha256: str
    output_sha256: str
    output_all_zero: bool | None
    set_captured: bool
    set_cal_size: int | None
    set_mem_handle: int | None
    set_payload_sha256: str
    expected_topology_hex: str
    verdict: str


@dataclasses.dataclass(frozen=True)
class Analysis:
    decision: str
    ok: bool
    v2675_run: str
    v2689_report: str
    all_create_allocate_ok: bool
    captured_custom_cal_types: list[int]
    missing_custom_cal_types: list[int]
    failed_get_cal_types: list[int]
    successful_get_cal_types: list[int]
    tuple_audits: list[CalAudit]
    v2689_defined_module_rejected: bool
    conclusion: str
    next_unit: str


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text, 16) if text.lower().startswith("0x") else int(text)


def signed32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - 0x100000000 if value & 0x80000000 else value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_u32_le(path: Path) -> int | None:
    data = path.read_bytes()
    if len(data) < 4:
        return None
    return struct.unpack_from("<I", data, 0)[0]


def parse_lower_events(path: Path) -> list[LowerStage]:
    events: list[LowerStage] = []
    for line in path.read_text(errors="replace").splitlines():
        match = LOWER_EVENT_RE.search(line)
        if not match:
            continue
        events.append(
            LowerStage(
                stage=match.group("stage"),
                code=int(match.group("code")),
                cal_type=int(match.group("cal_type")),
                value=int(match.group("value"), 16),
            )
        )
    return events


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def parse_tap_records(acdbtap_dir: Path) -> list[TapRecord]:
    rows = parse_jsonl(acdbtap_dir / "acdbtap-events.jsonl")
    enters: dict[int, dict[str, Any]] = {}
    buffers: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("event") == "acdb_ioctl_call" and row.get("phase") == "enter":
            seq = parse_int(row.get("seq", 0))
            enters[seq] = row
        elif row.get("buffer") in {"in", "out"}:
            seq = parse_int(row.get("seq", 0))
            buffers[(seq, str(row.get("buffer")))] = row

    records: list[TapRecord] = []
    for seq, enter in sorted(enters.items()):
        cmd = parse_int(enter.get("cmd", 0))
        cal_type = CMD_TO_CAL.get(cmd, -1)
        if cal_type not in TARGETS:
            continue
        in_row = buffers.get((seq, "in"), {})
        out_row = buffers.get((seq, "out"), {})
        input_words = [parse_int(enter.get("in_word0", 0)), parse_int(enter.get("in_word1", 0))]
        out_file = acdbtap_dir / Path(str(out_row.get("raw_path", ""))).name if out_row.get("raw_path") else None
        out_size = read_u32_le(out_file) if out_file and out_file.exists() else None
        records.append(
            TapRecord(
                seq=seq,
                cal_type=cal_type,
                cmd=cmd,
                cmd_hex=f"0x{cmd:08x}",
                input_words=input_words,
                input_sha256=str(in_row.get("sha256", "")),
                output_ret=signed32(parse_int(out_row.get("ret", 0))) if out_row else None,
                output_size=out_size,
                output_sha256=str(out_row.get("sha256", "")),
                output_all_zero=bool(out_row.get("all_zero")) if out_row else None,
            )
        )
    return records


def parse_setcal_records(path: Path) -> list[SetCalRecord]:
    records: list[SetCalRecord] = []
    for row in parse_jsonl(path):
        if row.get("event") != "setcal_capture":
            continue
        records.append(
            SetCalRecord(
                sequence=parse_int(row.get("sequence", 0)),
                cal_type=parse_int(row.get("cal_type", -1)),
                data_size=parse_int(row.get("data_size", 0)),
                cal_size=parse_int(row.get("cal_size", 0)),
                mem_handle=parse_int(row.get("mem_handle", -1)),
                arg_sha256=str(row.get("set_arg", {}).get("sha256", "")),
                dmabuf_sha256=str(row.get("dmabuf", {}).get("sha256", "")),
                dmabuf_status=str(row.get("dmabuf", {}).get("status", "")),
            )
        )
    return records


def stage_ok(events: Iterable[LowerStage], stage: str, cal_type: int) -> bool:
    return any(event.stage == stage and event.cal_type == cal_type and event.code == 0 for event in events)


def get_code(events: Iterable[LowerStage], cal_type: int) -> int | None:
    for event in events:
        if event.stage == "acdb_ioctl_get_return" and event.cal_type == cal_type:
            return event.code
    return None


def build_cal_audit(
    cal_type: int,
    lower_events: list[LowerStage],
    taps: dict[int, TapRecord],
    sets: dict[int, SetCalRecord],
) -> CalAudit:
    info = TARGETS[cal_type]
    tap = taps.get(cal_type)
    set_record = sets.get(cal_type)
    create_ok = stage_ok(lower_events, "create_cal_node_return", cal_type)
    allocate_ok = stage_ok(lower_events, "allocate_cal_block_return", cal_type)
    ret = get_code(lower_events, cal_type)
    if ret is None and tap is not None:
        ret = tap.output_ret
    set_captured = set_record is not None
    if ret == 0 and set_captured:
        verdict = "captured-real-set-payload"
    elif ret == 0 and not set_captured:
        verdict = "get-succeeded-but-set-missing"
    elif ret is not None and ret < 0:
        verdict = "get-failed-before-set"
    else:
        verdict = "insufficient-evidence"
    return CalAudit(
        cal_type=cal_type,
        label=str(info["label"]),
        cmd_hex=f"0x{int(info['cmd']):08x}",
        create_ok=create_ok,
        allocate_ok=allocate_ok,
        get_ret=ret,
        get_size=tap.output_size if tap else None,
        request_words_hex=[f"0x{word:08x}" for word in (tap.input_words if tap else [])],
        request_sha256=tap.input_sha256 if tap else "",
        output_sha256=tap.output_sha256 if tap else "",
        output_all_zero=tap.output_all_zero if tap else None,
        set_captured=set_captured,
        set_cal_size=set_record.cal_size if set_record else None,
        set_mem_handle=set_record.mem_handle if set_record else None,
        set_payload_sha256=set_record.dmabuf_sha256 if set_record else "",
        expected_topology_hex=f"0x{int(info['expected_topology']):08x}",
        verdict=verdict,
    )


def analyze(run_dir: Path, v2689_report: Path) -> Analysis:
    artifacts = run_dir / "ownget-device-artifacts"
    lower_events = parse_lower_events(artifacts / "acdb-v2674-lower-hidden-inhook-events.jsonl")
    tap_records = {record.cal_type: record for record in parse_tap_records(artifacts / "acdbtap")}
    set_records = {record.cal_type: record for record in parse_setcal_records(artifacts / "setcal-events.jsonl")}
    tuple_audits = [build_cal_audit(cal_type, lower_events, tap_records, set_records) for cal_type in (24, 10, 14)]
    captured_custom = sorted(set_records)
    missing_custom = sorted(set(TARGETS) - set(captured_custom))
    failed_get = sorted(audit.cal_type for audit in tuple_audits if audit.get_ret is not None and audit.get_ret < 0)
    successful_get = sorted(audit.cal_type for audit in tuple_audits if audit.get_ret == 0)
    all_create_allocate_ok = all(audit.create_ok and audit.allocate_ok for audit in tuple_audits)
    report_text = v2689_report.read_text(errors="replace") if v2689_report.exists() else ""
    defined_rejected = "v2689-defined-module-topology-replay-still-adsp-ebadparam" in report_text and "ADSP_EBADPARAM" in report_text
    ok = (
        all_create_allocate_ok
        and captured_custom == [14, 24]
        and failed_get == [10]
        and successful_get == [14, 24]
        and defined_rejected
    )
    decision = (
        "v2690-request-tuple-recovery-needed-after-defined-module-rejection"
        if ok
        else "v2690-request-tuple-audit-incomplete"
    )
    conclusion = (
        "V2675 proves the lower hidden-node plumbing creates and allocates cal_types 24, 10, and 14, "
        "but the pinned ADM request tuple for cmd 0x11394 returns -12 with a zero size buffer while "
        "AFE/ASM return real payload sizes. V2689 then proves synthetic/core-derived replacements for "
        "the missing ADM and selected ASM topologies are still rejected by the DSP. Therefore the useful "
        "next branch is not another synthetic replay; it is recovery of the real ACDB request tuple or "
        "real SET record that produces the selected ADM/ASM topology definitions."
    )
    next_unit = (
        "Design a host-first capture/reconstruction unit that instruments the ACDB lower custom-topology "
        "send path by call site or argument tuple, preserving exact request words and SET records for the "
        "selected ADM 0x10004000 and ASM 0x10005000 topology definitions. Keep native replay parked until "
        "those byte-exact records are recovered."
    )
    return Analysis(
        decision=decision,
        ok=ok,
        v2675_run=rel(run_dir),
        v2689_report=rel(v2689_report),
        all_create_allocate_ok=all_create_allocate_ok,
        captured_custom_cal_types=captured_custom,
        missing_custom_cal_types=missing_custom,
        failed_get_cal_types=failed_get,
        successful_get_cal_types=successful_get,
        tuple_audits=tuple_audits,
        v2689_defined_module_rejected=defined_rejected,
        conclusion=conclusion,
        next_unit=next_unit,
    )


def render_report(analysis: Analysis) -> str:
    lines: list[str] = [
        "# NATIVE_INIT V2690 — ACDB request-tuple recovery audit",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only audit after V2689.  This reads only existing private metadata and",
        "tiny ACDB request/size-query artifacts from V2675.  No device step, flash,",
        "audio route write, PCM probe, or `/dev/msm_audio_cal` ioctl occurred.  Raw",
        "custom-topology payload bytes remain private and are not embedded here.",
        "",
        "## Result",
        "",
        f"- decision: `{analysis.decision}`",
        f"- ok: `{analysis.ok}`",
        f"- v2675_run: `{analysis.v2675_run}`",
        f"- v2689_report: `{analysis.v2689_report}`",
        f"- all_create_allocate_ok: `{analysis.all_create_allocate_ok}`",
        f"- captured_custom_cal_types: `{analysis.captured_custom_cal_types}`",
        f"- missing_custom_cal_types: `{analysis.missing_custom_cal_types}`",
        f"- failed_get_cal_types: `{analysis.failed_get_cal_types}`",
        f"- successful_get_cal_types: `{analysis.successful_get_cal_types}`",
        f"- v2689_defined_module_rejected: `{analysis.v2689_defined_module_rejected}`",
        "",
        "## Tuple Audit",
        "",
        "| cal_type | role | GET cmd | create | allocate | request words | ret | size | out_zero | SET captured | SET cal_size | SET mem_handle | expected selected topology | verdict |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for audit in analysis.tuple_audits:
        lines.append(
            "| {cal} | `{label}` | `{cmd}` | `{create}` | `{alloc}` | `{words}` | `{ret}` | `{size}` | `{zero}` | `{setcap}` | `{setsize}` | `{mem}` | `{topo}` | `{verdict}` |".format(
                cal=audit.cal_type,
                label=audit.label,
                cmd=audit.cmd_hex,
                create=audit.create_ok,
                alloc=audit.allocate_ok,
                words=", ".join(audit.request_words_hex),
                ret=audit.get_ret,
                size=audit.get_size,
                zero=audit.output_all_zero,
                setcap=audit.set_captured,
                setsize=audit.set_cal_size,
                mem=audit.set_mem_handle,
                topo=audit.expected_topology_hex,
                verdict=audit.verdict,
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            analysis.conclusion,
            "",
            "The key distinction is now explicit:",
            "",
            "- cal_type `24` and `14` have valid V2675 lower-path GET tuples and real SET payloads,",
            "  but cal_type `14` is not the selected `0x10005000` ASM definition needed by the",
            "  replayed stream header.",
            "- cal_type `10` is not missing because the helper skipped allocation: create and",
            "  allocate succeeded, but the captured/pinned `0x11394` request tuple returned `-12`,",
            "  so no ADM SET payload exists for that tuple.",
            "- V2689 already falsified the fallback of synthesizing cal_type `10`/`14` records from",
            "  core topology metadata.  More core-derived guessing is now low-value.",
            "",
            "## Next Unit",
            "",
            analysis.next_unit,
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_request_tuple_recovery_v2690.py tests/test_analyze_audio_acdb_request_tuple_recovery_v2690.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_request_tuple_recovery_v2690 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_request_tuple_recovery_v2690.py --write-report`",
            "- `git diff --check`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_V2675_RUN)
    parser.add_argument("--v2689-report", type=Path, default=DEFAULT_V2689_REPORT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    analysis = analyze(args.run_dir, args.v2689_report)
    print(json.dumps(dataclasses.asdict(analysis), indent=2, sort_keys=True))
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(analysis), encoding="utf-8")
    return 0 if analysis.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
