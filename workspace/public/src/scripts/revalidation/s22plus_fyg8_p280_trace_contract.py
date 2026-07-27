#!/usr/bin/env python3
"""Derive and parse the exact P2.80 trace contract."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import s22plus_fyg8_p280_contract_spec as spec


class TraceContractError(ValueError):
    pass


_NM_LINE = re.compile(
    r"^(?P<address>[0-9a-fA-F]+)\s+(?P<kind>[A-Za-z])\s+(?P<name>\S+)$"
)
_INSTRUCTION = re.compile(
    r"^\s*(?P<address>[0-9a-fA-F]+):\s+"
    r"(?P<opcode>[0-9a-fA-F]{8})\s+(?P<text>.*)$"
)
_RELOCATION = re.compile(
    r"^\s*(?P<address>[0-9a-fA-F]+):\s+R_AARCH64_CALL26\s+(?P<name>\S+)$"
)
_TRACE_LINE = re.compile(
    r"^(?P<prefix>.*?)-(?P<pid>[0-9]+)\s+\[[^\]]+\]\s+\S+\s+"
    r"(?P<counter>[0-9]+):\s+"
    r"(?P<event>p280_[a-z0-9_]+):\s*(?P<fields>.*)$"
)
_FIELD = re.compile(r"(?:^|\s)(?P<name>[a-z_]+)=(?P<value>-?[0-9]+)")


@dataclass(frozen=True)
class Symbol:
    address: int
    kind: str
    name: str


@dataclass(frozen=True)
class TraceRecord:
    pid: int
    counter: int
    event: str
    fields: dict[str, int]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def parse_nm(text: str) -> tuple[Symbol, ...]:
    result = []
    for line in text.splitlines():
        match = _NM_LINE.fullmatch(line.strip())
        if match is None:
            continue
        result.append(
            Symbol(
                address=int(match.group("address"), 16),
                kind=match.group("kind"),
                name=match.group("name"),
            )
        )
    return tuple(result)


def require_exact_symbol(
    symbols: tuple[Symbol, ...],
    name: str,
    *,
    kinds: frozenset[str],
) -> Symbol:
    matches = tuple(symbol for symbol in symbols if symbol.name == name)
    if len(matches) != 1:
        raise TraceContractError(
            f"expected one exact symbol {name!r}, found {len(matches)}"
        )
    selected = matches[0]
    if selected.kind not in kinds or selected.name.endswith(".cfi_jt"):
        raise TraceContractError(f"symbol {name!r} is not an exact text body")
    if any(
        symbol.address == selected.address and symbol.name != selected.name
        for symbol in symbols
    ):
        raise TraceContractError(f"symbol {name!r} aliases another symbol")
    return selected


def derive_parent_post_call_offsets(
    *,
    nm_text: str,
    disassembly: str,
) -> tuple[int, int]:
    symbols = parse_nm(nm_text)
    parent = require_exact_symbol(
        symbols, spec.PARENT_SYMBOL, kinds=frozenset(("t", "T"))
    )
    if any(symbol.name == spec.PARENT_SYMBOL + ".cfi_jt" for symbol in symbols):
        raise TraceContractError("parent symbol has a same-name CFI thunk")

    instructions: dict[int, str] = {}
    relocations: list[int] = []
    inside = False
    header = re.compile(
        rf"^[0-9a-fA-F]+ <{re.escape(spec.PARENT_SYMBOL)}>:$"
    )
    next_symbol = re.compile(r"^[0-9a-fA-F]+ <[^>]+>:$")
    for line in disassembly.splitlines():
        stripped = line.strip()
        if header.fullmatch(stripped):
            inside = True
            continue
        if inside and next_symbol.fullmatch(stripped):
            break
        if not inside:
            continue
        instruction = _INSTRUCTION.match(line)
        if instruction is not None:
            address = int(instruction.group("address"), 16)
            instructions[address] = instruction.group("text").strip()
            continue
        relocation = _RELOCATION.match(line)
        if (
            relocation is not None
            and relocation.group("name") == spec.PM_CALLEE
        ):
            relocations.append(int(relocation.group("address"), 16))

    if len(relocations) != 2:
        raise TraceContractError(
            "parent function must have exactly two runtime-resume calls"
        )
    offsets = []
    for address in relocations:
        if address not in instructions or not instructions[address].startswith("bl"):
            raise TraceContractError("runtime-resume relocation is not on BL")
        following = address + 4
        if following not in instructions:
            raise TraceContractError("runtime-resume post-call instruction missing")
        offset = following - parent.address
        if offset <= 0 or offset % 4 != 0:
            raise TraceContractError("invalid runtime-resume post-call offset")
        offsets.append(offset)
    result = tuple(offsets)
    if result != tuple(sorted(result)) or result[0] == result[1]:
        raise TraceContractError("runtime-resume post-call order is ambiguous")
    return result  # type: ignore[return-value]


def derive_contract(
    *,
    module: Path,
    vmlinux: Path,
    nm: str = "aarch64-linux-gnu-nm",
    objdump: str = "aarch64-linux-gnu-objdump",
) -> dict[str, Any]:
    if sha256_path(module) != spec.EXACT_DWC3_MSM_SHA256:
        raise TraceContractError("exact dwc3-msm module hash mismatch")
    module_nm = _run([nm, "-an", str(module)])
    module_disassembly = _run(
        [objdump, "-dr", f"--disassemble={spec.PARENT_SYMBOL}", str(module)]
    )
    offsets = derive_parent_post_call_offsets(
        nm_text=module_nm, disassembly=module_disassembly
    )
    kernel_symbols = parse_nm(_run([nm, "-an", str(vmlinux)]))
    for event in spec.events_for_phase(spec.PHASE_BIND):
        require_exact_symbol(
            kernel_symbols, event.symbol, kinds=frozenset(("t", "T"))
        )
    definitions = {
        phase: tuple(
            event.definition(offsets)
            for event in spec.events_for_phase(phase)
        )
        for phase in (spec.PHASE_ROLE, spec.PHASE_BIND)
    }
    return {
        "schema": "s22plus_fyg8_p280_derived_trace_contract_v1",
        "module_sha256": sha256_path(module),
        "vmlinux_sha256": sha256_path(vmlinux),
        "parent_symbol": spec.PARENT_SYMBOL,
        "parent_pm_post_call_offsets": list(offsets),
        "event_definitions": {
            phase: list(values) for phase, values in definitions.items()
        },
    }


def _run(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
    except subprocess.TimeoutExpired as error:
        raise TraceContractError(
            f"command timed out: {' '.join(command)}"
        ) from error
    if result.returncode != 0:
        raise TraceContractError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}"
        )
    return result.stdout


def parse_trace(text: str) -> tuple[TraceRecord, ...]:
    records = []
    known = {f"p280_{event.name}" for event in spec.TRACE_EVENTS}
    for line in text.splitlines():
        match = _TRACE_LINE.fullmatch(line.rstrip())
        if match is None:
            continue
        event = match.group("event")
        if event not in known:
            continue
        fields = {
            field.group("name"): int(field.group("value"))
            for field in _FIELD.finditer(match.group("fields"))
        }
        records.append(
            TraceRecord(
                pid=int(match.group("pid")),
                counter=int(match.group("counter")),
                event=event.removeprefix("p280_"),
                fields=fields,
            )
        )
    return tuple(records)


def _values(
    records: tuple[TraceRecord, ...], name: str
) -> tuple[TraceRecord, ...]:
    return tuple(record for record in records if record.event == name)


def parse_role_trace(text: str) -> dict[str, Any]:
    records = parse_trace(text)
    starts = tuple(
        record
        for record in _values(records, "start_in")
        if record.fields.get("on") == 1
    )
    if not starts:
        return {"classification": "no-start", "clean": True}
    first = starts[0]
    decisive = tuple(
        record
        for record in records
        if record.counter >= first.counter and record.pid == first.pid
    )
    names = tuple(record.event for record in decisive)
    required = ("start_in", "parent_pm_out", "child_pm_out", "start_out")
    cursor = 0
    selected: dict[str, TraceRecord] = {}
    for name in required:
        while cursor < len(decisive) and decisive[cursor].event != name:
            cursor += 1
        if cursor == len(decisive):
            if name == "start_out":
                return {
                    "classification": "start-no-return",
                    "clean": True,
                    "pid": first.pid,
                }
            raise TraceContractError(
                f"role trace is missing required boundary {name}"
            )
        selected[name] = decisive[cursor]
        cursor += 1
    if len(starts) != 1:
        raise TraceContractError("role trace has conflicting DEVICE starts")
    parent_rc = selected["parent_pm_out"].fields.get("rc")
    child_rc = selected["child_pm_out"].fields.get("rc")
    start_rc = selected["start_out"].fields.get("rc")
    if None in (parent_rc, child_rc, start_rc):
        raise TraceContractError("role trace is missing signed return fields")
    if start_rc != 0:
        raise TraceContractError("void parent start returned nonzero")
    if parent_rc < 0:
        classification = "parent-pm-negative"
    elif child_rc < 0:
        classification = "child-pm-negative"
    else:
        classification = "complete"
    return {
        "classification": classification,
        "clean": True,
        "pid": first.pid,
        "parent_pm_rc": parent_rc,
        "child_pm_rc": child_rc,
        "start_rc": start_rc,
        "ordered_events": list(required),
        "observed_events": list(names),
    }


def parse_bind_trace(text: str) -> dict[str, Any]:
    records = parse_trace(text)
    if any(record.pid != 1 for record in records):
        raise TraceContractError("bind trace contains a non-PID1 event")
    pulls_in = _values(records, "pull_in")
    pulls_out = _values(records, "pull_out")
    if len(pulls_in) != 1 or len(pulls_out) != 1:
        raise TraceContractError("bind trace lacks one pull-up pair")
    if pulls_in[0].fields.get("on") != 1:
        raise TraceContractError("bind trace pull-up argument is not one")
    if pulls_out[0].fields.get("rc") != 0:
        raise TraceContractError("successful bind has nonzero pull-up return")
    if pulls_in[0].counter >= pulls_out[0].counter:
        raise TraceContractError("pull-up return precedes its entry")

    resume_in = _values(records, "resume_in")
    resume_out = _values(records, "resume_out")
    run_in = _values(records, "run_in")
    run_out = _values(records, "run_out")
    if len(resume_in) != len(resume_out) or len(run_in) != len(run_out):
        raise TraceContractError("bind trace has an incomplete nested pair")
    if len(resume_in) > 1 or len(run_in) > 1:
        raise TraceContractError("bind trace has duplicate nested pairs")
    if resume_in:
        if resume_in[0].counter >= resume_out[0].counter:
            raise TraceContractError("runtime resume return precedes entry")
        resume_rc = resume_out[0].fields.get("rc")
        if resume_rc is None or resume_rc < 0:
            raise TraceContractError(
                "successful bind has invalid runtime-resume return"
            )
    else:
        resume_rc = None
    run_rc = None
    if run_in:
        if run_in[0].fields.get("on") != 1:
            raise TraceContractError("run-stop argument is not one")
        if run_in[0].counter >= run_out[0].counter:
            raise TraceContractError("run-stop return precedes entry")
        run_rc = run_out[0].fields.get("rc")
        if run_rc is None:
            raise TraceContractError("run-stop return lacks signed result")
        if run_rc != 0:
            if not resume_in or not (
                resume_in[0].counter
                < run_in[0].counter
                < run_out[0].counter
                < resume_out[0].counter
            ):
                raise TraceContractError(
                    "nonzero run-stop was not swallowed in runtime resume"
                )
    if not run_in:
        classification = "pullup-without-run-stop"
    elif run_rc != 0:
        classification = "nested-run-stop-failure"
    else:
        classification = "run-stop-zero"
    return {
        "classification": classification,
        "clean": True,
        "pull_rc": 0,
        "resume_rc": resume_rc,
        "run_rc": run_rc,
    }


def detail_for_timeout(
    *, state: str, bind_trace: dict[str, Any] | None
) -> int:
    state_map = {
        "attached": 0xB23,
        "powered": 0xB23,
        "default": 0xB24,
        "addressed": 0xB25,
        "reconnecting": 0xB26,
        "unauthenticated": 0xB26,
        "suspended": 0xB26,
    }
    if state in state_map:
        return state_map[state]
    if state != "not attached":
        raise TraceContractError(f"unknown canonical UDC state: {state!r}")
    if not bind_trace or bind_trace.get("clean") is not True:
        return 0xB27
    classification = bind_trace.get("classification")
    if classification == "nested-run-stop-failure":
        return 0xB21
    if classification == "pullup-without-run-stop":
        return 0xB20
    if classification == "run-stop-zero":
        return 0xB22
    raise TraceContractError("clean bind trace has an unknown classification")


def _c_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def render_c_header(derived: dict[str, Any]) -> bytes:
    offsets_value = derived.get("parent_pm_post_call_offsets")
    if (
        not isinstance(offsets_value, list)
        or len(offsets_value) != 2
        or any(not isinstance(value, int) for value in offsets_value)
    ):
        raise TraceContractError("derived contract lacks two post-call offsets")
    offsets = (offsets_value[0], offsets_value[1])
    lines = [
        "/* Generated from s22plus_fyg8_p280_contract_spec.py. */",
        "#ifndef S22PLUS_FYG8_P280_TRACE_DESCRIPTOR_H",
        "#define S22PLUS_FYG8_P280_TRACE_DESCRIPTOR_H",
        "",
        f"#define P280_TRACE_BUFFER_KB {spec.TRACE_BUFFER_KB}U",
        f"#define P280_ROLE_DEADLINE_SEC {spec.ROLE_DEADLINE_SEC}LL",
        f"#define P280_ROLE_EVENT_COUNT "
        f"{len(spec.events_for_phase(spec.PHASE_ROLE))}U",
        f"#define P280_BIND_EVENT_COUNT "
        f"{len(spec.events_for_phase(spec.PHASE_BIND))}U",
        f"#define P280_DETAIL_COUNT {len(spec.DIAGNOSTIC_DETAILS)}U",
        "",
    ]
    for detail in spec.DIAGNOSTIC_DETAILS:
        macro = "P280_DETAIL_" + detail.name.upper().replace("-", "_")
        lines.append(f"#define {macro} 0x{detail.value:03x}U")
    lines.extend(
        (
            "",
            "struct p280_event_descriptor {",
            "    const char *name;",
            "    const char *definition;",
            "    const char *filter;",
            "};",
            "",
            "struct p280_detail_descriptor {",
            "    uint16_t value;",
            "    uint8_t outcome;",
            "    uint8_t stage_first;",
            "    uint8_t stage_last;",
            "};",
            "",
        )
    )
    for phase in (spec.PHASE_ROLE, spec.PHASE_BIND):
        lines.append(
            f"static const struct p280_event_descriptor "
            f"p280_{phase}_events[] = {{"
        )
        for event in spec.events_for_phase(phase):
            lines.append(
                "    {"
                f"{_c_string(event.name)}, "
                f"{_c_string(event.definition(offsets))}, "
                f"{_c_string(event.filter_expression)}"
                "},"
            )
        lines.extend(("};", ""))
    lines.append(
        "static const struct p280_detail_descriptor p280_details[] = {"
    )
    for detail in spec.DIAGNOSTIC_DETAILS:
        if len(detail.outcomes) != 1:
            raise TraceContractError("runtime detail must have one outcome")
        lines.append(
            "    {"
            f"0x{detail.value:03x}U, {detail.outcomes[0]}U, "
            f"0x{min(detail.stages):02x}U, 0x{max(detail.stages):02x}U"
            "},"
        )
    lines.extend(
        (
            "};",
            "",
            f"#define P280_PARENT_PM_POST_CALL_0 0x{offsets[0]:x}U",
            f"#define P280_PARENT_PM_POST_CALL_1 0x{offsets[1]:x}U",
            "",
            "#endif",
            "",
        )
    )
    data = "\n".join(lines).encode("ascii")
    for event in spec.TRACE_EVENTS:
        rendered = (
            f"{_c_string(event.name)}, "
            f"{_c_string(event.definition(offsets))}, "
            f"{_c_string(event.filter_expression)}"
        ).encode("ascii")
        if data.count(rendered) != 1:
            raise TraceContractError("rendered event definition drifted")
    for detail in spec.DIAGNOSTIC_DETAILS:
        if data.count(f"0x{detail.value:03x}U".encode("ascii")) < 2:
            raise TraceContractError("rendered diagnostic detail drifted")
    return data
