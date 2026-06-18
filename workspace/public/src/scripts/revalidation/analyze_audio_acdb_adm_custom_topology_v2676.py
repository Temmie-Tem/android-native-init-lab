#!/usr/bin/env python3
"""V2676 host-only analysis of the missing ADM custom-topology SET.

V2675 captured real non-zero SET payloads for custom cal_types 24 and 14, but
cal_type 10 failed at the ACDB GET-size query with ret=-12.  This unit does not
run a device step.  It cross-checks that failure against:

* the V2675 private lower-runner events;
* the V2461 Android-good compat ioctl report; and
* the stock libacdbloader Thumb block that builds the ADM GET input.

Only metadata is emitted publicly.  Raw payloads remain private.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[5]

DEFAULT_V2675_RUN = REPO / (
    "workspace/private/runs/audio/"
    "v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431"
)
DEFAULT_V2461_REPORT = REPO / (
    "docs/reports/"
    "NATIVE_INIT_V2461_AUDIO_ACDB_COMPAT_IOCTL_LIVE_CAPTURE_2026-06-15.md"
)
DEFAULT_LIB = REPO / (
    "workspace/private/runs/audio/"
    "v2675-acdb-lower-hidden-node-inhook-setcal-capture-20260618-144431/"
    "ownget-device-artifacts/libacdbloader.so"
)
DEFAULT_OBJDUMP = REPO / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0/bin/llvm-objdump"
DEFAULT_REPORT = REPO / (
    "docs/reports/"
    "NATIVE_INIT_V2676_AUDIO_ACDB_ADM_CUSTOM_TOPOLOGY_GET_RECON_2026-06-18.md"
)

LOWER_EVENT_RE = re.compile(
    r'"stage":"(?P<stage>[^"]+)","code":(?P<code>-?\d+),'
    r'"cal_type":(?P<cal_type>\d+),"value":(?P<value>0x[0-9a-fA-F]+)'
)


@dataclasses.dataclass(frozen=True)
class LowerEvent:
    stage: str
    code: int
    cal_type: int
    value: int


@dataclasses.dataclass(frozen=True)
class SetCalRecord:
    sequence: int
    cal_type: int
    cal_size: int
    mem_handle: int
    arg_sha256: str
    dmabuf_sha256: str
    dmabuf_status: str


@dataclasses.dataclass(frozen=True)
class AdmGeometry:
    ok: bool
    has_entry: bool
    has_exact_get_input_pair: bool
    has_in_len_8: bool
    has_cmd_0x11394: bool
    has_acdb_ioctl_call: bool
    evidence: list[str]


@dataclasses.dataclass(frozen=True)
class Analysis:
    decision: str
    ok: bool
    v2675_run: str
    v2675_lower_get_codes: dict[int, list[int]]
    v2675_captured_custom_cal_types: list[int]
    v2675_missing_custom_cal_types: list[int]
    v2461_android_alloc_has_cal10: bool
    v2461_android_set_has_cal10: bool
    v2461_android_set_rows: int
    adm_geometry: AdmGeometry
    conclusion: str
    next_unit: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_lower_events(path: Path) -> list[LowerEvent]:
    events: list[LowerEvent] = []
    for line in path.read_text(errors="replace").splitlines():
        match = LOWER_EVENT_RE.search(line)
        if not match:
            continue
        events.append(
            LowerEvent(
                stage=match.group("stage"),
                code=int(match.group("code")),
                cal_type=int(match.group("cal_type")),
                value=int(match.group("value"), 16),
            )
        )
    return events


def parse_setcal_events(path: Path) -> list[SetCalRecord]:
    records: list[SetCalRecord] = []
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("event") != "setcal_capture":
            continue
        records.append(
            SetCalRecord(
                sequence=int(obj.get("sequence", 0)),
                cal_type=int(obj.get("cal_type", -1)),
                cal_size=int(obj.get("cal_size", 0)),
                mem_handle=int(obj.get("mem_handle", -1)),
                arg_sha256=str(obj.get("set_arg", {}).get("sha256", "")),
                dmabuf_sha256=str(obj.get("dmabuf", {}).get("sha256", "")),
                dmabuf_status=str(obj.get("dmabuf", {}).get("status", "")),
            )
        )
    return records


def ensure_llvm_compat() -> dict[str, str | bool]:
    compat_dir = REPO / "tmp/relibs"
    compat_dir.mkdir(parents=True, exist_ok=True)
    link = compat_dir / "libtinfo.so.5"
    candidates = [
        Path("/usr/lib/x86_64-linux-gnu/libtinfo.so.5"),
        Path("/usr/lib/x86_64-linux-gnu/libtinfo.so.6"),
    ]
    target = next((candidate for candidate in candidates if candidate.exists()), None)
    if target and not link.exists():
        link.symlink_to(target)
    return {
        "compat_dir": str(compat_dir),
        "libtinfo_link_exists": link.exists(),
        "target": str(target) if target else "",
    }


def run_thumb_objdump(objdump: Path, lib: Path, start: int = 0x9234, stop: int = 0x9304) -> str:
    env = os.environ.copy()
    compat = ensure_llvm_compat()
    if compat["libtinfo_link_exists"]:
        env["LD_LIBRARY_PATH"] = str(compat["compat_dir"]) + (
            ":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else ""
        )
    cmd = [
        str(objdump),
        "-d",
        "--triple=thumbv7-linux-androideabi",
        "--no-show-raw-insn",
        f"--start-address=0x{start:x}",
        f"--stop-address=0x{stop:x}",
        str(lib),
    ]
    return subprocess.check_output(cmd, text=True, env=env)


def has_line(text: str, addr: int, pattern: str) -> bool:
    return bool(re.search(rf"^\s*{addr:04x}:\s+{pattern}", text, re.MULTILINE))


def analyze_adm_geometry(text: str) -> AdmGeometry:
    checks = {
        "has_entry": has_line(text, 0x924A, r"movs\s+r0,\s*#10"),
        "has_load_arg0": has_line(text, 0x929E, r"ldr\s+r1,\s*\[r0\]"),
        "has_load_arg1": has_line(text, 0x92A0, r"ldr\s+r0,\s*\[r0,\s*#8\]"),
        "has_store_pair": has_line(text, 0x92A2, r"strd\s+r1,\s*r0,\s*\[sp,\s*#56\]"),
        "has_in_len_8": has_line(text, 0x92B6, r"movs\s+r2,\s*#8"),
        "has_cmd_low": has_line(text, 0x92BA, r"movw\s+r0,\s*#5012"),
        "has_cmd_high": has_line(text, 0x92C2, r"movt\s+r0,\s*#1"),
        "has_acdb_ioctl_call": has_line(text, 0x92C6, r"blx\s+#"),
    }
    evidence = [name for name, present in checks.items() if present]
    has_exact_get_input_pair = checks["has_load_arg0"] and checks["has_load_arg1"] and checks["has_store_pair"]
    has_cmd_0x11394 = checks["has_cmd_low"] and checks["has_cmd_high"]
    ok = (
        checks["has_entry"]
        and has_exact_get_input_pair
        and checks["has_in_len_8"]
        and has_cmd_0x11394
        and checks["has_acdb_ioctl_call"]
    )
    return AdmGeometry(
        ok=ok,
        has_entry=checks["has_entry"],
        has_exact_get_input_pair=has_exact_get_input_pair,
        has_in_len_8=checks["has_in_len_8"],
        has_cmd_0x11394=has_cmd_0x11394,
        has_acdb_ioctl_call=checks["has_acdb_ioctl_call"],
        evidence=evidence,
    )


def analyze_v2461_report(text: str) -> tuple[bool, bool, int]:
    alloc_has_cal10 = bool(
        re.search(r"AUDIO_ALLOCATE_CALIBRATION.*\|\s*10\s+`ADM_CUST_TOPOLOGY_CAL_TYPE`", text)
    )
    set_has_cal10 = bool(
        re.search(r"AUDIO_SET_CALIBRATION.*\|\s*10\s+`ADM_CUST_TOPOLOGY_CAL_TYPE`", text)
    )
    set_rows = len(re.findall(r"AUDIO_SET_CALIBRATION", text))
    return alloc_has_cal10, set_has_cal10, set_rows


def group_get_codes(events: Iterable[LowerEvent]) -> dict[int, list[int]]:
    grouped: dict[int, list[int]] = {}
    for event in events:
        if event.stage == "acdb_ioctl_get_return":
            grouped.setdefault(event.cal_type, []).append(event.code)
    return grouped


def analyze(run_dir: Path, v2461_report: Path, lib: Path, objdump: Path) -> Analysis:
    artifacts = run_dir / "ownget-device-artifacts"
    lower_events = parse_lower_events(artifacts / "acdb-v2674-lower-hidden-inhook-events.jsonl")
    set_records = parse_setcal_events(artifacts / "setcal-events.jsonl")
    get_codes = group_get_codes(lower_events)

    v2461_text = v2461_report.read_text(errors="replace")
    alloc_has_cal10, set_has_cal10, android_set_rows = analyze_v2461_report(v2461_text)

    thumb = run_thumb_objdump(objdump, lib)
    adm_geometry = analyze_adm_geometry(thumb)

    captured = sorted({record.cal_type for record in set_records if record.cal_type in {10, 14, 24}})
    missing = sorted({10, 14, 24} - set(captured))
    cal10_get_failed = get_codes.get(10) == [-12]
    cal14_24_succeeded = get_codes.get(14) == [0] and get_codes.get(24) == [0]
    ok = (
        adm_geometry.ok
        and alloc_has_cal10
        and not set_has_cal10
        and cal10_get_failed
        and cal14_24_succeeded
        and captured == [14, 24]
        and missing == [10]
    )
    conclusion = (
        "cal_type 10 is not a V2675 capture-plumbing miss: V2675 used the same "
        "ADM block GET geometry as libacdbloader, create/allocate succeeded, "
        "but cmd 0x11394 returned -12 while 14/24 returned real sizes.  V2461 "
        "Android-good likewise allocated cal_type 10 but did not emit an "
        "AUDIO_SET_CALIBRATION record for it.  Treat ADM custom topology as "
        "absent for this route until new operator RE identifies a different "
        "command/input."
    )
    next_unit = (
        "V2677 should stop re-running cal_type 10 capture variants and instead "
        "splice the captured 24+14 custom topology records into the native ACDB "
        "replay manifest before the bounded PCM probe, with dmesg deciding "
        "whether ADM still rejects and which remaining topology/calibration path "
        "is actually missing."
    )
    return Analysis(
        decision="v2676-adm-custom-topology-cal10-absent-not-capture-gap-host-recon",
        ok=ok,
        v2675_run=str(run_dir.relative_to(REPO) if run_dir.is_relative_to(REPO) else run_dir),
        v2675_lower_get_codes={key: value for key, value in sorted(get_codes.items()) if key in {10, 14, 24}},
        v2675_captured_custom_cal_types=captured,
        v2675_missing_custom_cal_types=missing,
        v2461_android_alloc_has_cal10=alloc_has_cal10,
        v2461_android_set_has_cal10=set_has_cal10,
        v2461_android_set_rows=android_set_rows,
        adm_geometry=adm_geometry,
        conclusion=conclusion,
        next_unit=next_unit,
    )


def render_report(analysis: Analysis, lib: Path, v2461_report: Path) -> str:
    lines: list[str] = [
        "# NATIVE_INIT V2676 — ACDB ADM custom-topology GET reconnaissance",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only reconciliation of the V2675 partial capture.  No device step,",
        "no ACDB replay, no `/dev/msm_audio_cal` ioctl, and no raw private payload",
        "bytes are included in this report.",
        "",
        "## Result",
        "",
        f"- decision: `{analysis.decision}`",
        f"- ok: `{analysis.ok}`",
        f"- v2675_run: `{analysis.v2675_run}`",
        f"- libacdbloader: `{lib.relative_to(REPO) if lib.is_relative_to(REPO) else lib}`",
        f"- libacdbloader_sha256: `{sha256_file(lib)}`",
        f"- v2461_report: `{v2461_report.relative_to(REPO) if v2461_report.is_relative_to(REPO) else v2461_report}`",
        "",
        "## Evidence",
        "",
        "| Check | Result |",
        "| --- | --- |",
        f"| V2675 lower GET return codes | `{analysis.v2675_lower_get_codes}` |",
        f"| V2675 captured custom SET cal_types | `{analysis.v2675_captured_custom_cal_types}` |",
        f"| V2675 missing custom SET cal_types | `{analysis.v2675_missing_custom_cal_types}` |",
        f"| V2461 Android-good allocated cal_type 10 | `{analysis.v2461_android_alloc_has_cal10}` |",
        f"| V2461 Android-good SET cal_type 10 | `{analysis.v2461_android_set_has_cal10}` |",
        f"| V2461 `AUDIO_SET_CALIBRATION` text mentions | `{analysis.v2461_android_set_rows}` |",
        f"| ADM Thumb geometry verified | `{analysis.adm_geometry.ok}` |",
        f"| ADM uses block[0]/block[8] as 8-byte input | `{analysis.adm_geometry.has_exact_get_input_pair}` |",
        f"| ADM command is 0x11394 | `{analysis.adm_geometry.has_cmd_0x11394}` |",
        "",
        "The ADM disassembly check verifies the same input geometry used by V2674:",
        "`block+0` and `block+8` are copied to the `acdb_ioctl` input buffer,",
        "`in_len` is 8, and the command ID is `0x11394`.  That removes the main",
        "V2675 helper-geometry suspicion.",
        "",
        "## Interpretation",
        "",
        analysis.conclusion,
        "",
        "This revises the previous working assumption that cal_type 10 was still a",
        "capture gap.  The stronger reading is that cal_type 10 exists in the",
        "allocation table but has no SET payload for this Android speaker route,",
        "whereas cal_types 24 and 14 do have real non-zero payloads.",
        "",
        "## Next Unit",
        "",
        analysis.next_unit,
        "",
        "If the next native replay still reports `adm_open 0x10004000 ADSP_EFAILED`,",
        "then the blocker should be reclassified away from 'missing ADM custom",
        "topology capture' and toward ADM topology 9/core topology/order or another",
        "DSP-side route dependency.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_adm_custom_topology_v2676.py tests/test_analyze_audio_acdb_adm_custom_topology_v2676.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_adm_custom_topology_v2676 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_adm_custom_topology_v2676.py --write-report`",
        "- `git diff --check`",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_V2675_RUN)
    parser.add_argument("--v2461-report", type=Path, default=DEFAULT_V2461_REPORT)
    parser.add_argument("--lib", type=Path, default=DEFAULT_LIB)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    analysis = analyze(args.run_dir, args.v2461_report, args.lib, args.objdump)
    payload = dataclasses.asdict(analysis)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(render_report(analysis, args.lib, args.v2461_report), encoding="utf-8")
    return 0 if analysis.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
