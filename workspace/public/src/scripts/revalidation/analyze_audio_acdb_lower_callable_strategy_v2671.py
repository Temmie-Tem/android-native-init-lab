#!/usr/bin/env python3
"""V2671 host-only RE: ACDB lower custom-topology callable strategy.

V2670 closed the unchanged public-common path. This unit determines what is
actually callable next: direct entry into the hidden ADM/ASM/AFE blocks, or a
safer helper that recreates their create/allocate/GET/SET sequence using pinned
internal offsets and exported wrappers.

The script analyzes libacdbloader metadata and Thumb disassembly only. It does
not touch a device and does not read raw calibration payloads.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parents[5]
DEFAULT_LIB = REPO / "workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib/libacdbloader.so"
DEFAULT_OBJDUMP = REPO / "workspace/private/inputs/toolchains/llvm-arm-toolchain-ship-10.0/bin/llvm-objdump"
DEFAULT_HOST_LIBS = REPO / "workspace/private/builds/audio/v2668-acdb-direct-real-common-setcal-capture-build-only/host-libs"
DEFAULT_REPORT = REPO / "docs/reports/NATIVE_INIT_V2671_AUDIO_ACDB_LOWER_CALLABLE_STRATEGY_HOST_RECON_2026-06-18.md"
COMPAT_DIR = Path("/tmp/a90-llvm-compat")

SET_IOCTL = 0xC00461CB
CREATE_CAL_NODE = 0xFD44
ALLOCATE_CAL_BLOCK = 0xFBBC
ACDB_IOCTL_PLT = (0x15A70, 0x15A72)
IOCTL_PLT = 0x15BD0
TARGET_CUSTOM_CALS = (10, 14, 24)

COMMON_BLOCKS = {
    24: {
        "label": "AFE_CUST_TOPOLOGY",
        "list_anchor": "global+192",
        "entry": 0x90EA,
        "create_call": 0x90EC,
        "allocate_call": 0x910A,
        "acdb_ioctl_call": 0x9160,
        "set_ioctl_call": 0x91C8,
        "get_command": 0x130DA,
    },
    10: {
        "label": "ADM_CUST_TOPOLOGY",
        "list_anchor": "global+80",
        "entry": 0x924A,
        "create_call": 0x924C,
        "allocate_call": 0x926C,
        "acdb_ioctl_call": 0x92C6,
        "set_ioctl_call": 0x92FC,
        "get_command": 0x11394,
    },
    14: {
        "label": "ASM_CUST_TOPOLOGY",
        "list_anchor": "common-frame internal path",
        "entry": 0x93F6,
        "create_call": 0x93F8,
        "allocate_call": 0x9416,
        "acdb_ioctl_call": 0x946A,
        "set_ioctl_call": 0x94A0,
        "get_command": 0x12E01,
    },
    25: {
        "label": "supplemental/common custom topology",
        "list_anchor": "global+200",
        "entry": 0x9524,
        "create_call": 0x9526,
        "allocate_call": 0x9544,
        "acdb_ioctl_call": 0x959A,
        "set_ioctl_call": 0x95D0,
        "get_command": 0x130DC,
    },
}

EXPORTED_HELPERS = (
    "acdb_loader_send_common_custom_topology",
    "acdb_loader_adsp_set_audio_cal",
    "acdb_loader_store_set_audio_cal",
    "acdb_loader_set_audio_cal_v2",
)


@dataclass(frozen=True)
class DynamicSymbol:
    name: str
    value: str
    size: int
    present: bool


@dataclass(frozen=True)
class CommonBlockEvidence:
    cal_type: int
    label: str
    list_anchor: str
    entry_site: str
    create_cal_node_call: str
    allocate_cal_block_call: str
    acdb_ioctl_call: str
    set_ioctl_call: str
    get_command_id: str
    path_pinned: bool
    direct_entry_callable: bool
    direct_entry_rejection_reason: str


@dataclass(frozen=True)
class HelperAbiEvidence:
    set_audio_cal_v2_exported: bool
    set_audio_cal_v2_three_arg_wrapper: bool
    set_audio_cal_v2_tailcalls_store_and_adsp: bool
    store_set_audio_cal_expects_node_and_payload: bool
    adsp_set_audio_cal_expects_node_payload_len: bool
    standalone_helper_requires_cal_node_pointer: bool


@dataclass(frozen=True)
class Analysis:
    decision: str
    ok: bool
    lib_path: str
    dynamic_symbols: list[DynamicSymbol]
    common_prologue_sets_required_frame: bool
    set_ioctl_constant: str
    common_blocks: list[CommonBlockEvidence]
    helper_abi: HelperAbiEvidence
    direct_hidden_blocks_callable: bool
    hidden_node_sequence_ready: bool
    exported_lower_helper_standalone_ready: bool
    next_unit: str


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def ensure_llvm_compat() -> list[str]:
    paths: list[str] = []
    COMPAT_DIR.mkdir(parents=True, exist_ok=True)
    link = COMPAT_DIR / "libtinfo.so.5"
    if not link.exists():
        for candidate in (
            Path("/usr/lib/x86_64-linux-gnu/libtinfo.so.5"),
            Path("/usr/lib/x86_64-linux-gnu/libtinfo.so.6"),
        ):
            if candidate.exists():
                link.symlink_to(candidate)
                break
    if link.exists():
        paths.append(str(COMPAT_DIR))
    return paths


def run_checked(cmd: list[str], env_extra: dict[str, str] | None = None) -> str:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, env=env)


def objdump_range(objdump: Path, lib: Path, start: int, stop: int, host_libs: Path) -> str:
    ld_paths: list[str] = []
    if host_libs.exists():
        ld_paths.append(str(host_libs))
    ld_paths.extend(ensure_llvm_compat())
    if os.environ.get("LD_LIBRARY_PATH"):
        ld_paths.append(os.environ["LD_LIBRARY_PATH"])
    env_extra = {"LD_LIBRARY_PATH": ":".join(ld_paths)} if ld_paths else None
    return run_checked(
        [
            str(objdump),
            "-d",
            "--triple=thumbv7-linux-androideabi",
            "--no-show-raw-insn",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{stop:x}",
            str(lib),
        ],
        env_extra,
    )


def parse_dynamic_symbols(text: str, names: Iterable[str]) -> list[DynamicSymbol]:
    wanted = set(names)
    found: dict[str, DynamicSymbol] = {}
    pattern = re.compile(r"^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+)\s+FUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+(\S+)", re.MULTILINE)
    for match in pattern.finditer(text):
        value, size, name = match.groups()
        if name in wanted:
            found[name] = DynamicSymbol(name=name, value=f"0x{int(value, 16):08x}", size=int(size), present=True)
    return [found.get(name, DynamicSymbol(name=name, value="", size=0, present=False)) for name in names]


def parse_branch_target(text: str, address: int) -> int | None:
    match = re.search(rf"^\s*{address:04x}:\s+blx?\s+#(-?\d+)", text, re.MULTILINE)
    if not match:
        return None
    return address + 4 + int(match.group(1))


def has_line(text: str, address: int, pattern: str) -> bool:
    return re.search(rf"^\s*{address:04x}:\s+{pattern}", text, re.MULTILINE | re.IGNORECASE) is not None


def analyze_common_blocks(common_text: str) -> list[CommonBlockEvidence]:
    rows: list[CommonBlockEvidence] = []
    for cal_type, meta in COMMON_BLOCKS.items():
        entry = int(meta["entry"])
        create_target = parse_branch_target(common_text, int(meta["create_call"]))
        allocate_target = parse_branch_target(common_text, int(meta["allocate_call"]))
        acdb_target = parse_branch_target(common_text, int(meta["acdb_ioctl_call"]))
        set_target = parse_branch_target(common_text, int(meta["set_ioctl_call"]))
        path_pinned = (
            has_line(common_text, entry, rf"movs\s+r0,\s*#{cal_type}")
            and create_target == CREATE_CAL_NODE
            and allocate_target == ALLOCATE_CAL_BLOCK
            and acdb_target in ACDB_IOCTL_PLT
            and set_target == IOCTL_PLT
        )
        rows.append(
            CommonBlockEvidence(
                cal_type=cal_type,
                label=str(meta["label"]),
                list_anchor=str(meta["list_anchor"]),
                entry_site=f"0x{entry:04x}",
                create_cal_node_call=f"0x{int(meta['create_call']):04x}->0x{create_target:04x}" if create_target else "",
                allocate_cal_block_call=f"0x{int(meta['allocate_call']):04x}->0x{allocate_target:04x}" if allocate_target else "",
                acdb_ioctl_call=f"0x{int(meta['acdb_ioctl_call']):04x}->0x{acdb_target:04x}" if acdb_target else "",
                set_ioctl_call=f"0x{int(meta['set_ioctl_call']):04x}->0x{set_target:04x}" if set_target else "",
                get_command_id=f"0x{int(meta['get_command']):05x}",
                path_pinned=path_pinned,
                direct_entry_callable=False,
                direct_entry_rejection_reason=(
                    "interior block, not a function: it relies on common prologue state "
                    "(r7 global pointer, r8=0xc00461cb, r11=sp+24, zeroed stack slots, canary)."
                ),
            )
        )
    return rows


def analyze_helper_abi(symbols: list[DynamicSymbol], set_v2_text: str, store_text: str, adsp_text: str) -> HelperAbiEvidence:
    exported = {sym.name: sym.present for sym in symbols}
    set_v2_three_arg = all(
        re.search(pattern, set_v2_text, re.IGNORECASE)
        for pattern in (
            r"\bmov\s+r6,\s*r0\b",
            r"\bmov\s+r8,\s*r2\b",
            r"\bmov\s+r5,\s*r1\b",
        )
    )
    tailcalls_store_adsp = "e6c0:" in set_v2_text and "e6f2:" in set_v2_text
    store_expects = all(
        re.search(pattern, store_text, re.IGNORECASE)
        for pattern in (
            r"\bcmp\s+r0,\s*#0\b",
            r"\bcmpne\s+r1,\s*#0\b",
            r"\bldr\s+r3,\s*\[r0,\s*#28\]",
        )
    )
    adsp_expects = all(
        re.search(pattern, adsp_text, re.IGNORECASE)
        for pattern in (
            r"\bmov\s+r7,\s*r0\b",
            r"\bmov\s+r9,\s*r1\b",
            r"\bmov\s+r10,\s*r2\b",
            r"\bldr\s+r0,\s*\[r7,\s*#28\]",
        )
    )
    return HelperAbiEvidence(
        set_audio_cal_v2_exported=exported.get("acdb_loader_set_audio_cal_v2", False),
        set_audio_cal_v2_three_arg_wrapper=set_v2_three_arg,
        set_audio_cal_v2_tailcalls_store_and_adsp=tailcalls_store_adsp,
        store_set_audio_cal_expects_node_and_payload=store_expects,
        adsp_set_audio_cal_expects_node_payload_len=adsp_expects,
        standalone_helper_requires_cal_node_pointer=(set_v2_three_arg and store_expects and adsp_expects),
    )


def analyze(lib: Path = DEFAULT_LIB, objdump: Path = DEFAULT_OBJDUMP, host_libs: Path = DEFAULT_HOST_LIBS, *, dynsym_text: str | None = None, common_text: str | None = None, set_v2_text: str | None = None, store_text: str | None = None, adsp_text: str | None = None) -> Analysis:
    if dynsym_text is None:
        dynsym_text = run_checked(["readelf", "-Ws", str(lib)])
    if common_text is None:
        common_text = objdump_range(objdump, lib, 0x8CF0, 0x9738, host_libs)
    if set_v2_text is None:
        set_v2_text = objdump_range(objdump, lib, 0xE68C, 0xE6F6, host_libs)
    if store_text is None:
        store_text = objdump_range(objdump, lib, 0xE2D4, 0xE410, host_libs)
    if adsp_text is None:
        adsp_text = objdump_range(objdump, lib, 0xE43C, 0xE638, host_libs)

    symbols = parse_dynamic_symbols(dynsym_text, EXPORTED_HELPERS)
    blocks = analyze_common_blocks(common_text)
    common_prologue_sets_required_frame = all(
        re.search(pattern, common_text, re.IGNORECASE)
        for pattern in (
            r"\badd\.w\s+r11,\s*sp,\s*#24\b",
            r"\bmovw\s+r8,\s*#25035\b",
            r"\bmovt\s+r8,\s*#49156\b",
            r"\bstr\s+r0,\s*\[sp,\s*#92\]",
        )
    )
    helper_abi = analyze_helper_abi(symbols, set_v2_text, store_text, adsp_text)
    target_paths_pinned = all(block.path_pinned for block in blocks if block.cal_type in TARGET_CUSTOM_CALS)
    direct_hidden_blocks_callable = False
    hidden_node_sequence_ready = target_paths_pinned and common_prologue_sets_required_frame
    exported_lower_helper_standalone_ready = False
    ok = hidden_node_sequence_ready and helper_abi.standalone_helper_requires_cal_node_pointer

    return Analysis(
        decision="v2671-lower-blocks-not-direct-callable-hidden-node-sequence-ready-host-recon",
        ok=ok,
        lib_path=repo_relative(lib),
        dynamic_symbols=symbols,
        common_prologue_sets_required_frame=common_prologue_sets_required_frame,
        set_ioctl_constant=f"0x{SET_IOCTL:08x}",
        common_blocks=blocks,
        helper_abi=helper_abi,
        direct_hidden_blocks_callable=direct_hidden_blocks_callable,
        hidden_node_sequence_ready=hidden_node_sequence_ready,
        exported_lower_helper_standalone_ready=exported_lower_helper_standalone_ready,
        next_unit=(
            "V2672 build-only helper: resolve libacdbloader base, call hidden create_cal_node "
            "(base+0xfd45) and allocate_cal_block (base+0xfbbd) for cal_types 24/10/14, "
            "then run the pinned acdb_ioctl GET and fake AUDIO_SET_CALIBRATION capture path. "
            "Do not jump directly to interior common block entries."
        ),
    )


def markdown(analysis: Analysis) -> str:
    symbol_rows = [
        f"| `{sym.name}` | {sym.present} | `{sym.value or '-'}` | {sym.size} |" for sym in analysis.dynamic_symbols
    ]
    block_rows = [
        "| {cal} | {label} | {anchor} | {entry} | {create} | {alloc} | {get} | {acdb} | {setio} | {pinned} | {callable} |".format(
            cal=block.cal_type,
            label=block.label,
            anchor=block.list_anchor,
            entry=block.entry_site,
            create=block.create_cal_node_call,
            alloc=block.allocate_cal_block_call,
            get=block.get_command_id,
            acdb=block.acdb_ioctl_call,
            setio=block.set_ioctl_call,
            pinned=block.path_pinned,
            callable=block.direct_entry_callable,
        )
        for block in analysis.common_blocks
    ]
    return f"""# NATIVE_INIT V2671 — ACDB lower callable strategy host recon

Date: 2026-06-18

## Scope

Host-only reverse-engineering follow-up to V2670. No Android boot, native boot,
device flash, `/dev/msm_audio_cal` ioctl, ACDB replay, mixer write, PCM write,
or speaker playback occurred. This unit reads the private stock
`libacdbloader.so` metadata/disassembly only and emits no proprietary payload
bytes.

## Decision

- decision: `{analysis.decision}`
- ok: `{analysis.ok}`
- lib_path: `{analysis.lib_path}`
- set_ioctl_constant: `{analysis.set_ioctl_constant}`
- common_prologue_sets_required_frame: `{analysis.common_prologue_sets_required_frame}`
- direct_hidden_blocks_callable: `{analysis.direct_hidden_blocks_callable}`
- hidden_node_sequence_ready: `{analysis.hidden_node_sequence_ready}`
- exported_lower_helper_standalone_ready: `{analysis.exported_lower_helper_standalone_ready}`

## Exported Surface

| symbol | present | value | size |
| --- | --- | --- | ---: |
{chr(10).join(symbol_rows)}

`acdb_loader_set_audio_cal_v2` is exported, but it is not a cal-type-only entry.
Its wrapper preserves `r0/r1/r2` and dispatches to store/adsp lower helpers; the
store/adsp helpers then dereference a loader-created cal-node pointer. Therefore
the exported lower helpers are useful only after a cal-node is created; they are
not standalone replacements for the hidden ADM/ASM/AFE send routines.

## Common Internal Blocks

| cal_type | label | list anchor | entry | create_cal_node | allocate_cal_block | GET cmd | acdb_ioctl | SET ioctl | path pinned | direct callable |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(block_rows)}

The `10`, `14`, and `24` paths are pinned, but their entries are **interior
blocks** inside `acdb_loader_send_common_custom_topology()`, not callable hidden
functions. They rely on the common prologue setting `r7` to the loader global,
`r8` to `0xc00461cb`, `r11` to the local SET-arg frame, and multiple zeroed stack
slots. Jumping to `0x90ea`, `0x924a`, or `0x93f6` from a standalone helper would
skip that state and is unsafe.

## Helper ABI Evidence

- set_audio_cal_v2_exported: `{analysis.helper_abi.set_audio_cal_v2_exported}`
- set_audio_cal_v2_three_arg_wrapper: `{analysis.helper_abi.set_audio_cal_v2_three_arg_wrapper}`
- set_audio_cal_v2_tailcalls_store_and_adsp: `{analysis.helper_abi.set_audio_cal_v2_tailcalls_store_and_adsp}`
- store_set_audio_cal_expects_node_and_payload: `{analysis.helper_abi.store_set_audio_cal_expects_node_and_payload}`
- adsp_set_audio_cal_expects_node_payload_len: `{analysis.helper_abi.adsp_set_audio_cal_expects_node_payload_len}`
- standalone_helper_requires_cal_node_pointer: `{analysis.helper_abi.standalone_helper_requires_cal_node_pointer}`

## Interpretation

V2671 resolves the post-V2670 branch: do **not** call the common function's lower
block offsets directly. The viable build-only path is a small helper that
recreates the pinned lower sequence using internal offsets from the same loaded
library base:

1. create the cal node with `base+0xfd45` (`create_cal_node(cal_type)`);
2. allocate the cal block with `base+0xfbbd` using the same 32-byte SET header
   layout the common function builds;
3. issue the pinned ACDB GET command for the target cal_type; and
4. let the existing fake-SET interposer dump the generated SET arg/dma-buf.

This keeps the next live capture measurement-only: `AUDIO_SET_CALIBRATION` must
remain fake-success, raw bytes stay private, and rollback remains to V2321.

## Next Unit

{analysis.next_unit}

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_lower_callable_strategy_v2671.py tests/test_analyze_audio_acdb_lower_callable_strategy_v2671.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_lower_callable_strategy_v2671 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_lower_callable_strategy_v2671.py --write-report`
- `git diff --check`
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lib", type=Path, default=DEFAULT_LIB)
    parser.add_argument("--objdump", type=Path, default=DEFAULT_OBJDUMP)
    parser.add_argument("--host-libs", type=Path, default=DEFAULT_HOST_LIBS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    analysis = analyze(args.lib, args.objdump, args.host_libs)
    print(json.dumps(asdict(analysis), indent=2, sort_keys=True))
    if args.write_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown(analysis))
        print(f"wrote {repo_relative(args.report)}")
    return 0 if analysis.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
