#!/usr/bin/env python3
"""V2663 host-only RE of libacdbloader common custom-topology SET paths.

This script does not touch a device and does not emit proprietary bytes. It uses
llvm-objdump against the private stock 32-bit libacdbloader.so captured in V2660
and records only metadata: which cal_type blocks exist, which ACDB GET command
IDs they use, and whether the blocks reach acdb_ioctl + ioctl(SET) callsites.
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
DEFAULT_LIB = REPO / "workspace/private/runs/audio/v2660-acdb-custom-topology-phase-common-setcal-capture-20260618-123009/ownget-device-artifacts/libacdbloader.so"
DEFAULT_OBJDUMP = REPO / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0/bin/llvm-objdump"
DEFAULT_REPORT = REPO / "docs/reports/NATIVE_INIT_V2663_AUDIO_ACDB_COMMON_CUSTOM_TOPOLOGY_PATH_RECON_2026-06-18.md"
COMPAT_DIR = Path("/tmp/a90-llvm-compat")

SEND_COMMON_START = 0x8CF0
SEND_COMMON_STOP = 0x9738
LOWER_SET_START = 0xE2D4
LOWER_SET_STOP = 0xE714

PLT_TARGETS = {
    0x15A70: "acdb_ioctl",
    0x15A72: "acdb_ioctl",
    0x15BD0: "ioctl",
}

CAL_LABELS = {
    10: "ADM_CUST_TOPOLOGY",
    14: "ASM_CUST_TOPOLOGY",
    24: "AFE_CUST_TOPOLOGY",
    25: "supplemental/common custom topology",
    39: "CORE_CUSTOM_TOPOLOGIES",
}

TARGET_CALS = (10, 14, 24)

# Exact Thumb sites observed in the V2660 stock libacdbloader.so.
COMMON_BLOCK_SITES = {
    24: {
        "entry": 0x90EA,
        "create_call": 0x90EC,
        "allocate_call": 0x910A,
        "get_cmd_site": 0x9154,
        "get_cmd": 0x130DA,
        "acdb_ioctl_call": 0x9160,
        "set_ioctl_call": 0x91C8,
    },
    10: {
        "entry": 0x924A,
        "create_call": 0x924C,
        "allocate_call": 0x926C,
        "get_cmd_site": 0x92BA,
        "get_cmd": 0x11394,
        "acdb_ioctl_call": 0x92C6,
        "set_ioctl_call": 0x92FC,
    },
    14: {
        "entry": 0x93F6,
        "create_call": 0x93F8,
        "allocate_call": 0x9416,
        "get_cmd_site": 0x945E,
        "get_cmd": 0x12E01,
        "acdb_ioctl_call": 0x946A,
        "set_ioctl_call": 0x94A0,
    },
    25: {
        "entry": 0x9524,
        "create_call": 0x9526,
        "allocate_call": 0x9544,
        "get_cmd_site": 0x958C,
        "get_cmd": 0x130DC,
        "acdb_ioctl_call": 0x959A,
        "set_ioctl_call": 0x95D0,
    },
}


@dataclass(frozen=True)
class CalPath:
    cal_type: int
    label: str
    entry_site: str
    create_cal_node: bool
    allocate_cal_block: bool
    get_command_id: str | None
    acdb_ioctl_callsite: str | None
    set_ioctl_callsite: str | None
    reaches_target_set_path: bool


@dataclass(frozen=True)
class Analysis:
    decision: str
    ok: bool
    lib_path: str
    lib_sha256: str
    thumb_disassembly_ok: bool
    target_custom_cals_complete: bool
    common_export_contains_targets: bool
    lower_set_helper_not_required: bool
    cal_paths: list[CalPath]
    next_unit: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_llvm_compat() -> dict[str, str | bool]:
    COMPAT_DIR.mkdir(parents=True, exist_ok=True)
    link = COMPAT_DIR / "libtinfo.so.5"
    candidates = [
        Path("/usr/lib/x86_64-linux-gnu/libtinfo.so.5"),
        Path("/usr/lib/x86_64-linux-gnu/libtinfo.so.6"),
    ]
    target = next((p for p in candidates if p.exists()), None)
    if target and not link.exists():
        link.symlink_to(target)
    return {"compat_dir": str(COMPAT_DIR), "libtinfo_link_exists": link.exists(), "target": str(target) if target else ""}


def run_objdump(objdump: Path, lib: Path, start: int, stop: int) -> str:
    env = os.environ.copy()
    compat = ensure_llvm_compat()
    if compat["libtinfo_link_exists"]:
        env["LD_LIBRARY_PATH"] = str(COMPAT_DIR) + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
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


def has_line(text: str, address: int, pattern: str) -> bool:
    line_re = re.compile(rf"^\s*{address:04x}:\s+{pattern}", re.MULTILINE)
    return bool(line_re.search(text))


def parse_branch_target(text: str, address: int) -> int | None:
    match = re.search(rf"^\s*{address:04x}:\s+blx?\s+#(-?\d+)", text, re.MULTILINE)
    if not match:
        return None
    return address + 4 + int(match.group(1))


def analyze_common_text(text: str) -> list[CalPath]:
    paths: list[CalPath] = []
    for cal_type, sites in COMMON_BLOCK_SITES.items():
        entry = sites["entry"]
        create_target = parse_branch_target(text, sites["create_call"])
        alloc_target = parse_branch_target(text, sites["allocate_call"])
        acdb_target = parse_branch_target(text, sites["acdb_ioctl_call"])
        set_target = parse_branch_target(text, sites["set_ioctl_call"])
        cmd = sites["get_cmd"]
        path = CalPath(
            cal_type=cal_type,
            label=CAL_LABELS.get(cal_type, "unknown"),
            entry_site=f"0x{entry:04x}",
            create_cal_node=create_target == 0xFD44,
            allocate_cal_block=alloc_target == 0xFBBC,
            get_command_id=f"0x{cmd:05x}",
            acdb_ioctl_callsite=f"0x{sites['acdb_ioctl_call']:04x}" if PLT_TARGETS.get(acdb_target) == "acdb_ioctl" else None,
            set_ioctl_callsite=f"0x{sites['set_ioctl_call']:04x}" if PLT_TARGETS.get(set_target) == "ioctl" else None,
            reaches_target_set_path=(
                has_line(text, entry, rf"movs\s+r0,\s*#{cal_type}")
                and create_target == 0xFD44
                and alloc_target == 0xFBBC
                and PLT_TARGETS.get(acdb_target) == "acdb_ioctl"
                and PLT_TARGETS.get(set_target) == "ioctl"
            ),
        )
        paths.append(path)
    return paths


def analyze(lib: Path, objdump: Path) -> tuple[Analysis, dict[str, str]]:
    common = run_objdump(objdump, lib, SEND_COMMON_START, SEND_COMMON_STOP)
    lower = run_objdump(objdump, lib, LOWER_SET_START, LOWER_SET_STOP)
    cal_paths = analyze_common_text(common)
    target_complete = all(p.reaches_target_set_path for p in cal_paths if p.cal_type in TARGET_CALS)
    analysis = Analysis(
        decision="v2663-common-export-contains-missing-custom-setcal-paths-host-recon",
        ok=target_complete,
        lib_path=str(lib.relative_to(REPO) if lib.is_relative_to(REPO) else lib),
        lib_sha256=sha256_file(lib),
        thumb_disassembly_ok="push.w" in common and "acdb_loader_send_common_custom_topology" in common,
        target_custom_cals_complete=target_complete,
        common_export_contains_targets=target_complete,
        lower_set_helper_not_required=target_complete,
        cal_paths=cal_paths,
        next_unit=(
            "V2664 build-only common-only post-init SET-capture helper: after init_v3 success, "
            "call exported acdb_loader_send_common_custom_topology() only, fake AUDIO_SET_CALIBRATION, "
            "dump byte-exact SET args/dmabufs for cal_types 10/14/24, and skip send_audio_cal_v5."
        ),
    )
    return analysis, {"send_common_custom_topology": common, "lower_set_helpers": lower}


def markdown(analysis: Analysis) -> str:
    rows = []
    for path in analysis.cal_paths:
        rows.append(
            "| {cal_type} | {label} | {entry_site} | {get_command_id} | {create} | {alloc} | {acdb} | {setio} | {ok} |".format(
                cal_type=path.cal_type,
                label=path.label,
                entry_site=path.entry_site,
                get_command_id=path.get_command_id or "-",
                create=path.create_cal_node,
                alloc=path.allocate_cal_block,
                acdb=path.acdb_ioctl_callsite or "-",
                setio=path.set_ioctl_callsite or "-",
                ok=path.reaches_target_set_path,
            )
        )
    return f"""# NATIVE_INIT V2663 — ACDB common custom-topology path recon

Date: 2026-06-18

## Scope

Host-only Thumb disassembly of the stock 32-bit `libacdbloader.so` captured from
V2660. No Android boot, native boot, device flash, `/dev/msm_audio_cal` ioctl,
ACDB SET replay, mixer write, PCM write, or speaker playback occurred. Raw vendor
library bytes stay private; this report records metadata only.

## Decision

- decision: `{analysis.decision}`
- ok: `{analysis.ok}`
- lib_path: `{analysis.lib_path}`
- lib_sha256: `{analysis.lib_sha256}`
- thumb_disassembly_ok: `{analysis.thumb_disassembly_ok}`
- target_custom_cals_complete: `{analysis.target_custom_cals_complete}`
- common_export_contains_targets: `{analysis.common_export_contains_targets}`
- lower_set_helper_not_required: `{analysis.lower_set_helper_not_required}`

## Common Custom-Topology SET Paths

| cal_type | label | entry | GET command | create_cal_node | allocate_cal_block | acdb_ioctl call | ioctl SET call | reaches SET path |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(rows)}

## Interpretation

V2662 correctly found that direct `send_adm_custom_topology`,
`send_asm_custom_topology`, and `send_afe_custom_topology` symbols are hidden.
V2663 resolves the resulting ambiguity: the exported
`acdb_loader_send_common_custom_topology()` already contains the missing
per-subsystem custom topology SET paths. Its Thumb code builds blocks for
cal_types `24`, `10`, and `14`; each target block calls `create_cal_node`,
`allocate_cal_block`, an `acdb_ioctl` GET-size query, and then reaches the
`ioctl()` SET callsite.

This corrects the next-step emphasis: recovering hidden custom-function offsets
or calling lower SET helpers directly is not the shortest route. The safer next
unit is to stabilize the exported common path after `acdb_loader_init_v3` has
returned successfully, and to avoid unrelated per-device `send_audio_cal_v5`
work in the same helper.

Prior live evidence is consistent with this:

- V2657 called the real common path too early and returned `-92` before SET rows;
- V2660 proved init-short success and fake allocations for `10/14/24`, but the
  helper SIGSEGV'd before the post-init common call, so it did not disprove the
  exported common path.

## Next Unit

{analysis.next_unit}

Hard boundaries for that future live unit remain unchanged: measurement-only,
fake `AUDIO_SET_CALIBRATION`, zero real kernel SET pass-through, raw bytes private,
checked Android handoff and rollback to V2321.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_common_path_v2663.py tests/test_analyze_audio_acdb_custom_topology_common_path_v2663.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_custom_topology_common_path_v2663 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_common_path_v2663.py --write-report`
- `git diff --check`
"""


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lib", type=Path, default=DEFAULT_LIB)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    analysis, _ = analyze(args.lib, args.objdump)
    payload = asdict(analysis)
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown(analysis), encoding="utf-8")
    if args.json or not args.write_report:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if analysis.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
