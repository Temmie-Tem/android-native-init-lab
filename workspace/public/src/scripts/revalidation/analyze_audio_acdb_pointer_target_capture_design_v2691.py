#!/usr/bin/env python3
"""V2691 host-only ACDB pointer-target capture design audit.

V2690 stopped synthetic topology guessing and identified the next useful edge:
the lower hidden-node GET calls pass a two-word request where word1 is a
same-process pointer-like value. Existing V2675 artifacts captured only the
8-byte request buffer and the 4-byte size output, not the memory addressed by
that pointer. This analyzer makes that gap explicit and renders the V2692
build-only capture requirements.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[5]
DEFAULT_V2675_RUN = REPO / (
    "workspace/private/runs/audio/"
    "v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431"
)
DEFAULT_V2690_REPORT = REPO / (
    "docs/reports/"
    "NATIVE_INIT_V2690_AUDIO_ACDB_REQUEST_TUPLE_RECOVERY_AUDIT_2026-06-18.md"
)
DEFAULT_REPORT = REPO / (
    "docs/reports/"
    "NATIVE_INIT_V2691_AUDIO_ACDB_POINTER_TARGET_CAPTURE_DESIGN_2026-06-18.md"
)
LOWER_SOURCE = REPO / "workspace/public/src/android/acdb_payload_capture/libacdb_lower_hidden_node_inhook_v2674.c"
TAP_SOURCE = REPO / "workspace/public/src/android/acdb_payload_capture/libacdbtap_v2572.c"
INDIRECT_TAP_SOURCE = REPO / "workspace/public/src/android/acdb_payload_capture/libacdbtap_indirect_layout_v2613.c"

TARGETS: dict[int, dict[str, Any]] = {
    24: {"role": "AFE_CUSTOM_TOPOLOGY", "cmd": 0x130DA, "expected_topology": 0x1001025D},
    10: {"role": "ADM_CUSTOM_TOPOLOGY", "cmd": 0x11394, "expected_topology": 0x10004000},
    14: {"role": "ASM_CUSTOM_TOPOLOGY", "cmd": 0x12E01, "expected_topology": 0x10005000},
}
MARKERS = [0x1001025D, 0x10004000, 0x10005000, 0x00011135]
TUPLE_RE = re.compile(
    r"\|\s*(?P<cal>24|10|14)\s*\|.*?\|\s*`(?P<cmd>0x[0-9a-fA-F]+)`\s*\|"
    r".*?\|\s*`(?P<words>0x[0-9a-fA-F]+,\s*0x[0-9a-fA-F]+)`\s*\|\s*`(?P<ret>-?\d+)`",
)


@dataclasses.dataclass(frozen=True)
class TupleEvidence:
    cal_type: int
    role: str
    cmd_hex: str
    request_words_hex: list[str]
    ret: int
    word1_pointer_like: bool
    expected_topology_hex: str


@dataclasses.dataclass(frozen=True)
class SourceEvidence:
    lower_builds_get_from_block: bool
    lower_exposes_block_struct: bool
    tap_logs_in_word1: bool
    tap_has_generic_indirect_capture: bool
    indirect_tap_has_generic_indirect_capture: bool
    indirect_tap_has_maps_verified_pointer_target_capture: bool


@dataclasses.dataclass(frozen=True)
class ArtifactEvidence:
    v2675_run: str
    acdbtap_file_count: int
    inbuf_file_count: int
    outbuf_file_count: int
    pointer_target_file_count: int
    indirect_file_count: int
    has_pointer_target_artifact: bool
    event_logs_in_word1: bool


@dataclasses.dataclass(frozen=True)
class DesignStep:
    name: str
    requirement: str
    reason: str


@dataclasses.dataclass(frozen=True)
class Analysis:
    decision: str
    ok: bool
    v2690_report: str
    tuple_evidence: list[TupleEvidence]
    source_evidence: SourceEvidence
    artifact_evidence: ArtifactEvidence
    same_process_pointer_capture_required: bool
    raw_bytes_private_only: bool
    native_replay_parked: bool
    v2692_acceptance: list[str]
    v2692_design_steps: list[DesignStep]
    branch_after_v2692: list[str]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(errors="replace") if path.exists() else ""


def parse_tuple_evidence(report_text: str) -> list[TupleEvidence]:
    tuples: list[TupleEvidence] = []
    for match in TUPLE_RE.finditer(report_text):
        cal_type = int(match.group("cal"))
        info = TARGETS[cal_type]
        words = [word.strip() for word in match.group("words").split(",")]
        word1 = int(words[1], 16)
        tuples.append(
            TupleEvidence(
                cal_type=cal_type,
                role=str(info["role"]),
                cmd_hex=match.group("cmd").lower(),
                request_words_hex=[word.lower() for word in words],
                ret=int(match.group("ret")),
                word1_pointer_like=0x10000 <= word1 < 0xFFFF0000,
                expected_topology_hex=f"0x{int(info['expected_topology']):08x}",
            )
        )
    return sorted(tuples, key=lambda row: (0 if row.cal_type == 24 else 1 if row.cal_type == 10 else 2))


def inspect_sources(lower_source: Path, tap_source: Path, indirect_tap_source: Path) -> SourceEvidence:
    lower = read_text(lower_source)
    tap = read_text(tap_source)
    indirect = read_text(indirect_tap_source)
    return SourceEvidence(
        lower_builds_get_from_block="get_in[0] = block->get_arg0" in lower
        and "get_in[1] = block->get_arg1" in lower,
        lower_exposes_block_struct="struct a90_cal_block" in lower and "mem_handle" in lower,
        tap_logs_in_word1="in_word1" in tap,
        tap_has_generic_indirect_capture="a90_log_generic_indirect_capture" in tap or "a90_log_indirect_candidate_captures" in tap,
        indirect_tap_has_generic_indirect_capture="a90_log_indirect_candidate_captures" in indirect,
        indirect_tap_has_maps_verified_pointer_target_capture="/proc/self/maps" in indirect
        and "ptrtarget" in indirect,
    )


def inspect_artifacts(run_dir: Path) -> ArtifactEvidence:
    acdbtap_dir = run_dir / "ownget-device-artifacts" / "acdbtap"
    files = [path for path in acdbtap_dir.glob("*") if path.is_file()] if acdbtap_dir.exists() else []
    names = [path.name for path in files]
    events_text = read_text(acdbtap_dir / "acdbtap-events.jsonl")
    ptr_names = [name for name in names if "ptrtarget" in name or "pointee" in name or "blocktarget" in name]
    indirect_names = [name for name in names if "indirect" in name or "ind-" in name]
    return ArtifactEvidence(
        v2675_run=rel(run_dir),
        acdbtap_file_count=len(files),
        inbuf_file_count=sum(1 for name in names if "-in-len-" in name),
        outbuf_file_count=sum(1 for name in names if "-in-len-" not in name and name.endswith(".bin")),
        pointer_target_file_count=len(ptr_names),
        indirect_file_count=len(indirect_names),
        has_pointer_target_artifact=bool(ptr_names),
        event_logs_in_word1="in_word1" in events_text,
    )


def build_design_steps() -> list[DesignStep]:
    return [
        DesignStep(
            name="same-process pointer safety",
            requirement=(
                "Extend the V2674 own-process hidden-node hook, not a cross-process procfs reader. "
                "Before copying any pointer target, verify the requested range is fully covered by a readable "
                "entry from /proc/self/maps; otherwise log ptrtarget_unmapped and skip the copy."
            ),
            reason=(
                "V2473-class cross-process reads are opaque, but the lower hook owns the pointer and can inspect "
                "its own address space without dmabuf/procfs reopen tricks."
            ),
        ),
        DesignStep(
            name="block and request snapshot",
            requirement=(
                "For each cal_type 24/10/14, dump metadata for node->word0, node->word4, block address, "
                "block get_arg0/get_arg1/mem_handle/word4/word16/word20, plus the exact 8-byte GET input."
            ),
            reason="The current V2675 public tuple only has get_arg0/get_arg1 after construction; the block is the missing selector object.",
        ),
        DesignStep(
            name="pointer-target raw capture",
            requirement=(
                "For custom topology cmds 0x130da/0x11394/0x12e01/0x130dc with in_len==8, dump a private raw "
                "window from in_word1.  Default window is min(in_word0, 0x1000) bytes; record SHA-256, length, "
                "maps segment, and marker offsets in the public event log."
            ),
            reason="V2690 shows in_word1 is pointer-like for all three lower tuples, but no existing V2675 artifact contains its pointee bytes.",
        ),
        DesignStep(
            name="marker-only public report",
            requirement=(
                "Scan private pointer-target windows for 0x1001025d, 0x10004000, 0x10005000, and 0x11135. "
                "Commit only counts, offsets, sizes, and hashes; never commit the raw pointer-target files."
            ),
            reason="The selected ADM/ASM topology IDs are the only public discriminator needed to choose the next branch.",
        ),
        DesignStep(
            name="measurement-only guardrails",
            requirement=(
                "Keep fake AUDIO_SET_CALIBRATION, no real SET ioctl, no PCM probe, no route write, no speaker playback. "
                "Exit after the lower hidden-node sequence and roll back to V2321 if a live Android handoff is used."
            ),
            reason="V2692 is a capture unit, not a native replay or audio-output test.",
        ),
    ]


def analyze(run_dir: Path, v2690_report: Path, lower_source: Path, tap_source: Path, indirect_tap_source: Path) -> Analysis:
    report_text = read_text(v2690_report)
    tuples = parse_tuple_evidence(report_text)
    source = inspect_sources(lower_source, tap_source, indirect_tap_source)
    artifacts = inspect_artifacts(run_dir)
    tuple_gap = len(tuples) == 3 and all(row.word1_pointer_like for row in tuples)
    source_gap = source.lower_builds_get_from_block and source.lower_exposes_block_struct
    artifact_gap = artifacts.event_logs_in_word1 and not artifacts.has_pointer_target_artifact
    ok = tuple_gap and source_gap and artifact_gap
    decision = "v2691-same-process-pointer-target-capture-required" if ok else "v2691-pointer-target-design-incomplete"
    return Analysis(
        decision=decision,
        ok=ok,
        v2690_report=rel(v2690_report),
        tuple_evidence=tuples,
        source_evidence=source,
        artifact_evidence=artifacts,
        same_process_pointer_capture_required=ok,
        raw_bytes_private_only=True,
        native_replay_parked=True,
        v2692_acceptance=[
            "captured block/request metadata for cal_types 24, 10, and 14",
            "captured or explicitly classified maps-unreadable in_word1 pointer targets for cmds 0x130da, 0x11394, and 0x12e01",
            "public report contains only sizes, SHA-256, marker counts/offsets, ret codes, and branch decision",
            "no real AUDIO_SET_CALIBRATION, no PCM probe, no speaker write, and no native replay in the same unit",
        ],
        v2692_design_steps=build_design_steps(),
        branch_after_v2692=[
            "If a pointer target or block snapshot identifies a request selector for ADM 0x10004000 or ASM 0x10005000, build the next direct exact-capture unit around that selector.",
            "If cal_type 10 remains ret=-12 and no pointer-target data references 0x10004000, treat lower-hidden cal10 as the wrong route and pivot to Android-good in-HAL/real-path capture for the selected ADM SET record.",
            "If cal_type 14 pointer-target data explains why V2675 selected the stale 2356-byte payload, replace the V2684/V2689 forged candidate only after capturing byte-exact selected payload evidence.",
        ],
    )


def render_report(analysis: Analysis) -> str:
    lines = [
        "# NATIVE_INIT V2691 — ACDB pointer-target capture design",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only design unit after V2690.  This unit does not run the device, flash,",
        "touch `/dev/msm_audio_cal`, issue PCM, change audio route, or replay any ACDB",
        "payload.  It audits public metadata plus existing private file names only; raw",
        "ACDB bytes remain private and are not embedded here.",
        "",
        "## Result",
        "",
        f"- decision: `{analysis.decision}`",
        f"- ok: `{analysis.ok}`",
        f"- v2690_report: `{analysis.v2690_report}`",
        f"- same_process_pointer_capture_required: `{analysis.same_process_pointer_capture_required}`",
        f"- raw_bytes_private_only: `{analysis.raw_bytes_private_only}`",
        f"- native_replay_parked: `{analysis.native_replay_parked}`",
        "",
        "## Evidence",
        "",
        "### Tuple Evidence",
        "",
        "| cal_type | role | GET cmd | request words | ret | word1 pointer-like | expected selected topology |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in analysis.tuple_evidence:
        lines.append(
            f"| {row.cal_type} | `{row.role}` | `{row.cmd_hex}` | `{', '.join(row.request_words_hex)}` | `{row.ret}` | `{row.word1_pointer_like}` | `{row.expected_topology_hex}` |"
        )
    src = analysis.source_evidence
    art = analysis.artifact_evidence
    lines.extend(
        [
            "",
            "### Source Evidence",
            "",
            f"- lower_builds_get_from_block: `{src.lower_builds_get_from_block}`",
            f"- lower_exposes_block_struct: `{src.lower_exposes_block_struct}`",
            f"- default_v2572_source_logs_in_word1: `{src.tap_logs_in_word1}`",
            f"- tap_has_generic_indirect_capture: `{src.tap_has_generic_indirect_capture}`",
            f"- indirect_tap_has_generic_indirect_capture: `{src.indirect_tap_has_generic_indirect_capture}`",
            f"- indirect_tap_has_maps_verified_pointer_target_capture: `{src.indirect_tap_has_maps_verified_pointer_target_capture}`",
            "",
            "### Artifact Evidence",
            "",
            f"- v2675_run: `{art.v2675_run}`",
            f"- acdbtap_file_count: `{art.acdbtap_file_count}`",
            f"- inbuf_file_count: `{art.inbuf_file_count}`",
            f"- outbuf_file_count: `{art.outbuf_file_count}`",
            f"- pointer_target_file_count: `{art.pointer_target_file_count}`",
            f"- indirect_file_count: `{art.indirect_file_count}`",
            f"- has_pointer_target_artifact: `{art.has_pointer_target_artifact}`",
            f"- event_logs_in_word1: `{art.event_logs_in_word1}`",
            "",
            "## Interpretation",
            "",
            "V2690 captured only the visible two-word GET tuple.  For cal_types `24`, `10`,",
            "and `14`, the second word is pointer-like, and V2674 constructs that tuple from",
            "`block->get_arg0` and `block->get_arg1`.  The V2675 artifacts contain the 8-byte",
            "input buffers and 4-byte size outputs, but no pointer-target/pointee dump.  That",
            "means the next useful measurement is not another replay or synthetic payload; it is",
            "a same-process dump of the lower ACDB block and the memory addressed by `get_arg1`.",
            "",
            "The existing V2572/V2613 indirect taps prove the project already has useful indirect",
            "capture scaffolding, but the V2692 requirement is stricter: custom-topology",
            "pointer targets must be captured from the actual V2674 lower-node context,",
            "maps-verified before copy, and the block fields must be captured at the",
            "lower hidden-node call site.  Raw bytes remain private; public",
            "reports should expose only hashes, lengths, ret codes, and marker offsets/counts.",
            "",
            "## V2692 Build Requirements",
            "",
        ]
    )
    for step in analysis.v2692_design_steps:
        lines.extend(
            [
                f"### {step.name}",
                "",
                f"- requirement: {step.requirement}",
                f"- reason: {step.reason}",
                "",
            ]
        )
    lines.extend(
        [
            "## Acceptance",
            "",
        ]
    )
    for item in analysis.v2692_acceptance:
        lines.append(f"- {item}")
    lines.extend(["", "## Branch After V2692", ""])
    for item in analysis.branch_after_v2692:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_pointer_target_capture_design_v2691.py tests/test_analyze_audio_acdb_pointer_target_capture_design_v2691.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_pointer_target_capture_design_v2691 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_pointer_target_capture_design_v2691.py --write-report`",
            "- `git diff --check`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_V2675_RUN)
    parser.add_argument("--v2690-report", type=Path, default=DEFAULT_V2690_REPORT)
    parser.add_argument("--lower-source", type=Path, default=LOWER_SOURCE)
    parser.add_argument("--tap-source", type=Path, default=TAP_SOURCE)
    parser.add_argument("--indirect-tap-source", type=Path, default=INDIRECT_TAP_SOURCE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    analysis = analyze(args.run_dir, args.v2690_report, args.lower_source, args.tap_source, args.indirect_tap_source)
    print(json.dumps(dataclasses.asdict(analysis), indent=2, sort_keys=True))
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(analysis), encoding="utf-8")
    return 0 if analysis.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
