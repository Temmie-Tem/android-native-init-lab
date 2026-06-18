#!/usr/bin/env python3
"""V2670 host-only analysis of the V2669 common-topology runtime path.

V2663 proved that the exported `acdb_loader_send_common_custom_topology()`
contains the lower ADM/ASM/AFE custom-topology SET blocks. V2669 then ran that
exported function in Android-good and captured only cal_type 39 at runtime. This
script turns that new live evidence into a repeatable host-only classification:
the public common export is not worth retrying unchanged because this runtime
takes the CORE_CUSTOM_TOPOLOGIES path and skips the lower 10/14/24 SET blocks.

The script reads metadata JSONL/logcat only. It never reads or prints raw
payload .bin files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parents[5]
DEFAULT_ARTIFACT_DIR = (
    REPO
    / "workspace/private/runs/audio/v2669-acdb-direct-real-common-setcal-capture-20260618-134245/ownget-device-artifacts"
)
DEFAULT_LIB = REPO / "workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libacdbloader.so"
DEFAULT_OBJDUMP = REPO / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0/bin/llvm-objdump"
DEFAULT_HOST_LIBS = REPO / "workspace/private/builds/audio/v2668-acdb-direct-real-common-setcal-capture-build-only/host-libs"
DEFAULT_REPORT = REPO / "docs/reports/NATIVE_INIT_V2670_AUDIO_ACDB_COMMON_RUNTIME_SKIP_HOST_RECON_2026-06-18.md"
COMPAT_DIR = Path("/tmp/a90-llvm-compat")

TARGET_CUSTOM_CALS = (10, 14, 24)
COMMON_SUPPLEMENTAL_CAL = 25
CORE_CUSTOM_TOPOLOGY_CAL = 39

LOWER_BLOCKS = {
    24: {"label": "AFE_CUST_TOPOLOGY", "entry": 0x90EA, "get": 0x9160, "set": 0x91C8},
    10: {"label": "ADM_CUST_TOPOLOGY", "entry": 0x924A, "get": 0x92C6, "set": 0x92FC},
    14: {"label": "ASM_CUST_TOPOLOGY", "entry": 0x93F6, "get": 0x946A, "set": 0x94A0},
    25: {"label": "supplemental/common custom topology", "entry": 0x9524, "get": 0x959A, "set": 0x95D0},
}


@dataclass(frozen=True)
class SetCalRecord:
    sequence: int
    cal_type: int
    data_size: int
    cal_size: int
    mem_handle: int
    arg_sha256: str
    dmabuf_status: str
    dmabuf_sha256: str


@dataclass(frozen=True)
class LowerBlockEvidence:
    cal_type: int
    label: str
    entry_site: str
    get_callsite: str
    set_callsite: str
    present_in_disassembly: bool


@dataclass(frozen=True)
class Analysis:
    decision: str
    ok: bool
    artifact_dir: str
    phase_stages: list[str]
    phase_common_return_codes: list[int]
    direct_real_common_returned_zero: bool
    log_reports_common_topology_in_use: bool
    set_cal_types_seen: list[int]
    setcal_records: list[SetCalRecord]
    allocate_cal_types_seen: list[int]
    target_allocate_cal_types_seen: list[int]
    missing_target_allocate_cal_types: list[int]
    missing_target_set_cal_types: list[int]
    lower_blocks_present: bool
    lower_blocks: list[LowerBlockEvidence]
    public_common_export_runtime_skips_lower_sets: bool
    corrected_previous_assumption: str
    next_unit: str


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="replace")


def parse_jsonl_with_stage_fallback(path: Path) -> list[dict]:
    records: list[dict] = []
    if not path.exists():
        return records
    stage_re = re.compile(r'"stage"\s*:\s*"([^"]+)"')
    code_re = re.compile(r'"code"\s*:\s*(-?\d+)')
    phase_re = re.compile(r'"phase"\s*:\s*(-?\d+)')
    for line_number, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            obj.setdefault("_line", line_number)
            records.append(obj)
            continue
        except json.JSONDecodeError:
            pass
        obj = {"_line": line_number, "_parse_error": True}
        stage = stage_re.search(line)
        code = code_re.search(line)
        phase = phase_re.search(line)
        if stage:
            obj["stage"] = stage.group(1)
        if code:
            obj["code"] = int(code.group(1))
        if phase:
            obj["phase"] = int(phase.group(1))
        records.append(obj)
    return records


def sorted_unique(values: Iterable[int]) -> list[int]:
    return sorted(set(values))


def parse_setcal_records(path: Path) -> list[SetCalRecord]:
    rows = []
    for row in parse_jsonl_with_stage_fallback(path):
        if row.get("event") != "setcal_capture":
            continue
        set_arg = row.get("set_arg") or {}
        dmabuf = row.get("dmabuf") or {}
        rows.append(
            SetCalRecord(
                sequence=int(row.get("sequence", 0)),
                cal_type=int(row.get("cal_type", -1)),
                data_size=int(row.get("data_size", 0)),
                cal_size=int(row.get("cal_size", 0)),
                mem_handle=int(row.get("mem_handle", -1)),
                arg_sha256=str(set_arg.get("sha256", "")),
                dmabuf_status=str(dmabuf.get("status", "")),
                dmabuf_sha256=str(dmabuf.get("sha256", "")),
            )
        )
    return rows


def parse_ioctl_cal_types(path: Path, request_name: str) -> list[int]:
    cal_types = []
    for row in parse_jsonl_with_stage_fallback(path):
        if row.get("name") != request_name:
            continue
        snapshot = row.get("arg_snapshot") or {}
        if snapshot.get("available") and "cal_type" in snapshot:
            cal_types.append(int(snapshot["cal_type"]))
    return sorted_unique(cal_types)


def ensure_llvm_compat() -> Path | None:
    COMPAT_DIR.mkdir(parents=True, exist_ok=True)
    link = COMPAT_DIR / "libtinfo.so.5"
    if link.exists():
        return COMPAT_DIR
    for candidate in (
        Path("/usr/lib/x86_64-linux-gnu/libtinfo.so.5"),
        Path("/usr/lib/x86_64-linux-gnu/libtinfo.so.6"),
    ):
        if candidate.exists():
            link.symlink_to(candidate)
            return COMPAT_DIR
    return None


def run_common_objdump(objdump: Path, lib: Path, host_libs: Path) -> str:
    if not objdump.exists() or not lib.exists():
        return ""
    env = os.environ.copy()
    ld_paths: list[str] = []
    if host_libs.exists():
        ld_paths.append(str(host_libs))
    compat = ensure_llvm_compat()
    if compat:
        ld_paths.append(str(compat))
    if env.get("LD_LIBRARY_PATH"):
        ld_paths.append(env["LD_LIBRARY_PATH"])
    if ld_paths:
        env["LD_LIBRARY_PATH"] = ":".join(ld_paths)
    cmd = [
        str(objdump),
        "-d",
        "--triple=thumbv7-linux-androideabi",
        "--no-show-raw-insn",
        "--start-address=0x9038",
        "--stop-address=0x95f0",
        str(lib),
    ]
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, env=env)
    except subprocess.CalledProcessError as exc:
        return exc.output


def disassembly_lower_blocks(text: str) -> list[LowerBlockEvidence]:
    rows: list[LowerBlockEvidence] = []
    lower_text = text.lower()
    for cal_type, meta in LOWER_BLOCKS.items():
        entry = int(meta["entry"])
        get = int(meta["get"])
        set_site = int(meta["set"])
        present = (
            f"{entry:04x}:" in lower_text
            and f"{get:04x}:" in lower_text
            and f"{set_site:04x}:" in lower_text
            and re.search(rf"^\s*{entry:04x}:\s+movs\s+r0,\s*#{cal_type}", lower_text, re.MULTILINE)
            is not None
        )
        rows.append(
            LowerBlockEvidence(
                cal_type=cal_type,
                label=str(meta["label"]),
                entry_site=f"0x{entry:04x}",
                get_callsite=f"0x{get:04x}",
                set_callsite=f"0x{set_site:04x}",
                present_in_disassembly=present,
            )
        )
    return rows


def analyze(artifact_dir: Path, objdump: Path = DEFAULT_OBJDUMP, lib: Path = DEFAULT_LIB, host_libs: Path = DEFAULT_HOST_LIBS, disassembly_text: str | None = None) -> Analysis:
    phase_rows = parse_jsonl_with_stage_fallback(artifact_dir / "acdb-v2668-direct-real-common-events.jsonl")
    phase_stages = [str(row["stage"]) for row in phase_rows if row.get("stage")]
    phase_common_return_codes = [
        int(row["code"])
        for row in phase_rows
        if row.get("stage") == "init_real_common_return" and "code" in row
    ]

    setcal_records = parse_setcal_records(artifact_dir / "setcal-events.jsonl")
    set_cal_types_seen = sorted_unique(record.cal_type for record in setcal_records)
    allocate_cal_types_seen = parse_ioctl_cal_types(artifact_dir / "ioctl-trace-events.jsonl", "AUDIO_ALLOCATE_CALIBRATION")
    target_allocate_cal_types_seen = [cal for cal in TARGET_CUSTOM_CALS if cal in allocate_cal_types_seen]
    missing_target_allocate_cal_types = [cal for cal in TARGET_CUSTOM_CALS if cal not in allocate_cal_types_seen]
    missing_target_set_cal_types = [cal for cal in TARGET_CUSTOM_CALS if cal not in set_cal_types_seen]

    logcat = read_text(artifact_dir / "logcat-acdb-loader.txt")
    log_reports_common_topology_in_use = "Common custom topology in use" in logcat
    if disassembly_text is None:
        disassembly_text = run_common_objdump(objdump, lib, host_libs)
    lower_blocks = disassembly_lower_blocks(disassembly_text)
    lower_blocks_present = all(row.present_in_disassembly for row in lower_blocks)

    direct_real_common_returned_zero = 0 in phase_common_return_codes
    public_common_export_runtime_skips_lower_sets = (
        direct_real_common_returned_zero
        and log_reports_common_topology_in_use
        and set_cal_types_seen == [CORE_CUSTOM_TOPOLOGY_CAL]
        and target_allocate_cal_types_seen == list(TARGET_CUSTOM_CALS)
        and missing_target_set_cal_types == list(TARGET_CUSTOM_CALS)
    )

    return Analysis(
        decision="v2670-common-export-runtime-skips-subsystem-custom-setcal-host-recon",
        ok=public_common_export_runtime_skips_lower_sets,
        artifact_dir=repo_relative(artifact_dir),
        phase_stages=phase_stages,
        phase_common_return_codes=phase_common_return_codes,
        direct_real_common_returned_zero=direct_real_common_returned_zero,
        log_reports_common_topology_in_use=log_reports_common_topology_in_use,
        set_cal_types_seen=set_cal_types_seen,
        setcal_records=setcal_records,
        allocate_cal_types_seen=allocate_cal_types_seen,
        target_allocate_cal_types_seen=target_allocate_cal_types_seen,
        missing_target_allocate_cal_types=missing_target_allocate_cal_types,
        missing_target_set_cal_types=missing_target_set_cal_types,
        lower_blocks_present=lower_blocks_present,
        lower_blocks=lower_blocks,
        public_common_export_runtime_skips_lower_sets=public_common_export_runtime_skips_lower_sets,
        corrected_previous_assumption=(
            "V2663's static claim remains true, but V2669 proves the exported common function's "
            "successful runtime CORE path does not emit subsystem custom topology SETs."
        ),
        next_unit=(
            "Stop rerunning acdb_loader_send_common_custom_topology() unchanged. Next host-only unit "
            "should recover hidden ADM/ASM/AFE custom-topology send routines and call them directly, "
            "or pin an "
            "exported lower SET-helper ABI for cal_types 10/14/24 before any further live capture."
        ),
    )


def markdown(analysis: Analysis) -> str:
    set_rows = []
    for record in analysis.setcal_records:
        set_rows.append(
            f"| {record.sequence} | {record.cal_type} | {record.data_size} | {record.cal_size} | "
            f"{record.mem_handle} | `{record.arg_sha256}` | {record.dmabuf_status} | `{record.dmabuf_sha256}` |"
        )
    if not set_rows:
        set_rows.append("| - | - | - | - | - | - | - | - |")

    lower_rows = []
    for block in analysis.lower_blocks:
        lower_rows.append(
            f"| {block.cal_type} | {block.label} | {block.entry_site} | {block.get_callsite} | "
            f"{block.set_callsite} | {block.present_in_disassembly} |"
        )

    return f"""# NATIVE_INIT V2670 — ACDB common runtime skip host recon

Date: 2026-06-18

## Scope

Host-only analysis of the completed V2669 Android-good capture. No device boot,
flash, ACDB SET replay, `/dev/msm_audio_cal` ioctl, mixer write, PCM write, or
speaker playback occurred in this unit. The script reads metadata JSONL/logcat
only; raw captured `.bin` payloads stay private and are not read or emitted.

## Decision

- decision: `{analysis.decision}`
- ok: `{analysis.ok}`
- artifact_dir: `{analysis.artifact_dir}`
- direct_real_common_returned_zero: `{analysis.direct_real_common_returned_zero}`
- phase_common_return_codes: `{analysis.phase_common_return_codes}`
- log_reports_common_topology_in_use: `{analysis.log_reports_common_topology_in_use}`
- set_cal_types_seen: `{analysis.set_cal_types_seen}`
- allocate_cal_types_seen: `{analysis.allocate_cal_types_seen}`
- target_allocate_cal_types_seen: `{analysis.target_allocate_cal_types_seen}`
- missing_target_allocate_cal_types: `{analysis.missing_target_allocate_cal_types}`
- missing_target_set_cal_types: `{analysis.missing_target_set_cal_types}`
- lower_blocks_present: `{analysis.lower_blocks_present}`
- public_common_export_runtime_skips_lower_sets: `{analysis.public_common_export_runtime_skips_lower_sets}`

## Runtime Evidence

V2669 successfully reached the real exported common custom-topology path:

- phase_stages: `{analysis.phase_stages}`
- `init_real_common_return` returned: `{analysis.phase_common_return_codes}`
- `logcat-acdb-loader.txt` contains `Common custom topology in use`.

However, the only captured `AUDIO_SET_CALIBRATION` row was cal_type `39`.

| seq | cal_type | data_size | cal_size | mem_handle | arg_sha256 | dmabuf_status | dmabuf_sha256 |
| ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
{chr(10).join(set_rows)}

The init-time allocation trace did include cal_types `10`, `14`, and `24`, but
those rows are `AUDIO_ALLOCATE_CALIBRATION` placeholders, not emitted SETs. That
distinction matters: allocation proves the loader has cal-node slots, while the
replay manifest needs byte-exact `AUDIO_SET_CALIBRATION` arg bytes + payloads.

## Static Cross-Check

The V2663 static finding remains valid: the stock common export contains lower
blocks for the per-subsystem custom topologies.

| cal_type | label | entry | GET callsite | SET callsite | present |
| ---: | --- | --- | --- | --- | --- |
{chr(10).join(lower_rows)}

V2670 changes the interpretation, not the static disassembly: the successful
runtime path exits after CORE_CUSTOM_TOPOLOGIES / cal_type `39` and does not
continue into the lower `24`, `10`, `14`, or supplemental `25` SET blocks in this
environment.

## Correction To Prior Plan

{analysis.corrected_previous_assumption}

Therefore another unchanged public-common capture run is low-information churn.
The next useful work is no longer another call to
`acdb_loader_send_common_custom_topology()`.

## Next Unit

{analysis.next_unit}

Hard boundaries remain unchanged: host-only RE until the lower target is pinned;
future live capture must keep fake `AUDIO_SET_CALIBRATION`, zero real kernel SET
pass-through, raw bytes private, checked Android handoff, and rollback to V2321.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_common_runtime_skip_v2670.py tests/test_analyze_audio_acdb_common_runtime_skip_v2670.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_common_runtime_skip_v2670 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_common_runtime_skip_v2670.py --write-report`
- `git diff --check`
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--lib", type=Path, default=DEFAULT_LIB)
    parser.add_argument("--host-libs", type=Path, default=DEFAULT_HOST_LIBS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    analysis = analyze(args.artifact_dir, args.objdump, args.lib, args.host_libs)
    payload = asdict(analysis)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown(analysis))
        print(f"wrote {repo_relative(args.report)}")
    return 0 if analysis.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
