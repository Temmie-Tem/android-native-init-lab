#!/usr/bin/env python3
"""Derive and parse the exact P2.86 cycle, outer-work, and bind contract."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import s22plus_fyg8_p286_contract_spec as spec
import s22plus_fyg8_p280_trace_contract as p280_trace


class TraceContractError(ValueError):
    pass


_NM_LINE = re.compile(
    r"^(?P<address>[0-9a-fA-F]+)\s+(?P<kind>[A-Za-z])\s+(?P<name>\S+)$"
)
_TRACE_LINE = re.compile(
    r"^(?P<prefix>.*?)-(?P<pid>[0-9]+)\s+\[[^\]]+\]\s+\S+\s+"
    r"(?P<counter>[0-9]+):\s+"
    r"(?P<event>[a-z0-9_]+):\s*(?P<fields>.*)$"
)
_FIELD = re.compile(r"(?:^|\s)(?P<name>[a-z_]+)=(?P<value>-?[0-9]+)")
_OWNED_FIELD_NAMES = frozenset(("on", "suspend", "rc"))


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


def _module_symbol_names(module_name: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            event.symbol
            for event in spec.TRACE_EVENTS
            if event.module == module_name
        )
    )


def _verify_module(
    path: Path,
    *,
    expected_sha256: str,
    module_name: str,
    nm: str,
    objdump: str,
) -> dict[str, Any]:
    digest = sha256_path(path)
    if digest != expected_sha256:
        raise TraceContractError(f"exact {module_name} module hash mismatch")
    symbols = parse_nm(_run([nm, "-an", str(path)]))
    verified = []
    for name in _module_symbol_names(module_name):
        symbol = require_exact_symbol(
            symbols, name, kinds=frozenset(("t", "T"))
        )
        verified.append(
            {"name": name, "address": symbol.address, "kind": symbol.kind}
        )
    result = {
        "path": str(path),
        "sha256": digest,
        "module": module_name,
        "symbols": verified,
    }
    if module_name == spec.DWC3_MSM_MODULE_RUNTIME_NAME:
        disassembly = _run(
            [
                objdump,
                "-dr",
                f"--disassemble={spec.PARENT_SYMBOL}",
                str(path),
            ]
        )
        result["parent_pm_post_call_offsets"] = list(
            p280_trace.derive_parent_post_call_offsets(
                nm_text=_run([nm, "-an", str(path)]),
                disassembly=disassembly,
            )
        )
    return result


def derive_module_contract(
    *,
    dwc3_msm_module: Path,
    hsphy_module: Path,
    nm: str = "aarch64-linux-gnu-nm",
    objdump: str = "aarch64-linux-gnu-objdump",
) -> dict[str, Any]:
    modules = (
        _verify_module(
            dwc3_msm_module,
            expected_sha256=spec.EXACT_DWC3_MSM_SHA256,
            module_name=spec.DWC3_MSM_MODULE_RUNTIME_NAME,
            nm=nm,
            objdump=objdump,
        ),
        _verify_module(
            hsphy_module,
            expected_sha256=spec.EXACT_HSPHY_SHA256,
            module_name=spec.HSPHY_MODULE_RUNTIME_NAME,
            nm=nm,
            objdump=objdump,
        ),
    )
    offsets = modules[0].get("parent_pm_post_call_offsets")
    if (
        not isinstance(offsets, list)
        or len(offsets) != 2
        or any(type(value) is not int for value in offsets)
    ):
        raise TraceContractError("parent post-call offsets are unavailable")
    return {
        "schema": "s22plus_fyg8_p286_module_trace_contract_v1",
        "modules": list(modules),
        "event_definitions": {
            phase: [
                event.definition(tuple(offsets))
                for event in spec.events_for_phase(phase)
            ]
            for phase in (
                spec.PHASE_ROLE,
                spec.PHASE_CYCLE,
                spec.PHASE_BIND,
            )
        },
    }


def derive_contract(
    *,
    dwc3_msm_module: Path,
    hsphy_module: Path,
    vmlinux: Path,
    nm: str = "aarch64-linux-gnu-nm",
    objdump: str = "aarch64-linux-gnu-objdump",
) -> dict[str, Any]:
    result = derive_module_contract(
        dwc3_msm_module=dwc3_msm_module,
        hsphy_module=hsphy_module,
        nm=nm,
        objdump=objdump,
    )
    kernel_symbols = parse_nm(_run([nm, "-an", str(vmlinux)]))
    kernel_verified = []
    for event in spec.TRACE_EVENTS:
        if event.module is not None:
            continue
        symbol = require_exact_symbol(
            kernel_symbols, event.symbol, kinds=frozenset(("t", "T"))
        )
        kernel_verified.append(
            {
                "name": event.symbol,
                "address": symbol.address,
                "kind": symbol.kind,
            }
        )
    return {
        **result,
        "schema": "s22plus_fyg8_p286_derived_trace_contract_v1",
        "vmlinux_sha256": sha256_path(vmlinux),
        "kernel_symbols": list(
            dict(
                (row["name"], row) for row in kernel_verified
            ).values()
        ),
    }


def parse_trace(text: str) -> tuple[TraceRecord, ...]:
    records = []
    known = {event.name for event in spec.TRACE_EVENTS}
    for raw_line in text.splitlines(keepends=True):
        terminated = raw_line.endswith("\n")
        line = raw_line[:-1] if terminated else raw_line
        owned = any(f": {name}:" in line for name in known)
        if owned and not terminated:
            raise TraceContractError("owned trace line is truncated")
        match = _TRACE_LINE.fullmatch(line.rstrip())
        if match is None:
            if owned:
                raise TraceContractError("owned trace line is malformed")
            continue
        event = match.group("event")
        if event not in known:
            raise TraceContractError("owned trace event is unknown")
        fields_text = match.group("fields")
        for name in _OWNED_FIELD_NAMES:
            for token in re.findall(
                rf"(?:^|\s){name}=([^\s]+)", fields_text
            ):
                if re.fullmatch(r"-?[0-9]+", token) is None:
                    raise TraceContractError(
                        f"owned trace field {name} is malformed"
                    )
        fields = {
            field.group("name"): int(field.group("value"))
            for field in _FIELD.finditer(fields_text)
        }
        records.append(
            TraceRecord(
                pid=int(match.group("pid")),
                counter=int(match.group("counter")),
                event=event,
                fields=fields,
            )
        )
    if any(
        left.counter >= right.counter
        for left, right in zip(records, records[1:])
    ):
        raise TraceContractError("owned trace counters are not increasing")
    return tuple(records)


def _values(
    records: tuple[TraceRecord, ...], name: str
) -> tuple[TraceRecord, ...]:
    return tuple(record for record in records if record.event == name)


def _pair_in_window(
    records: tuple[TraceRecord, ...],
    *,
    entry_name: str,
    return_name: str,
    pid: int,
    lower: int,
    upper: int,
    argument: tuple[str, int] | None = None,
) -> dict[str, Any]:
    entries = tuple(
        record
        for record in records
        if record.event == entry_name
        and record.pid == pid
        and lower < record.counter < upper
        and (
            argument is None
            or record.fields.get(argument[0]) == argument[1]
        )
    )
    returns = tuple(
        record
        for record in records
        if record.event == return_name
        and record.pid == pid
        and lower < record.counter < upper
    )
    if len(entries) > 1 or len(returns) > 1:
        raise TraceContractError(f"conflicting {entry_name} trace pair")
    if not entries:
        if returns:
            raise TraceContractError(f"{return_name} lacks its entry")
        return {"entered": False, "returned": False, "rc": None}
    entry = entries[0]
    matching_returns = tuple(
        record for record in returns if record.counter > entry.counter
    )
    if len(matching_returns) > 1:
        raise TraceContractError(f"conflicting {return_name} records")
    if not matching_returns:
        return {"entered": True, "returned": False, "rc": None}
    returned = matching_returns[0]
    rc = returned.fields.get("rc")
    if rc is None:
        raise TraceContractError(f"{return_name} lacks signed return")
    return {
        "entered": True,
        "returned": True,
        "rc": rc,
        "entry_counter": entry.counter,
        "return_counter": returned.counter,
    }


def _parent_window(
    records: tuple[TraceRecord, ...], on: int
) -> tuple[TraceRecord, TraceRecord | None]:
    all_entries = _values(records, "start_peripheral_in")
    entries = tuple(
        record
        for record in all_entries
        if record.fields.get("on") == on
    )
    if len(entries) != 1:
        raise TraceContractError(
            f"expected one parent on={on} entry, found {len(entries)}"
        )
    entry = entries[0]
    later_entries = tuple(
        record
        for record in all_entries
        if record.pid == entry.pid and record.counter > entry.counter
    )
    upper = (
        min(record.counter for record in later_entries)
        if later_entries
        else (1 << 64) - 1
    )
    returns = tuple(
        record
        for record in _values(records, "start_peripheral_out")
        if (
            record.pid == entry.pid
            and entry.counter < record.counter < upper
        )
    )
    if len(returns) > 1:
        raise TraceContractError(f"parent on={on} has multiple returns")
    return entry, returns[0] if returns else None


def _outer_state(records: tuple[TraceRecord, ...]) -> dict[str, bool]:
    relevant = tuple(
        record
        for record in records
        if record.event in ("outer_sm_work_in", "outer_sm_work_out")
    )
    entered = False
    returned = False
    open_work = False
    for index, record in enumerate(relevant):
        same_pid_before = tuple(
            candidate
            for candidate in relevant[:index]
            if candidate.pid == record.pid
        )
        same_pid_after = tuple(
            candidate
            for candidate in relevant[index + 1 :]
            if candidate.pid == record.pid
        )
        if record.event == "outer_sm_work_out":
            if (
                not same_pid_before
                or same_pid_before[-1].event != "outer_sm_work_in"
                or "rc" not in record.fields
            ):
                raise TraceContractError("outer return lacks its exact entry")
            returned = True
            continue
        entered = True
        if not same_pid_after:
            open_work = True
        elif same_pid_after[0].event != "outer_sm_work_out":
            raise TraceContractError("outer entry overlaps on one worker")
    return {
        "entered": entered,
        "returned": returned,
        "open": open_work,
    }


def parse_cycle_trace(text: str) -> dict[str, Any]:
    records = parse_trace(text)
    stop_in, stop_out = _parent_window(records, 0)
    restart_in, restart_out = _parent_window(records, 1)
    if stop_in.counter >= restart_in.counter:
        raise TraceContractError("restart parent precedes stop parent")
    stop_upper = stop_out.counter if stop_out else restart_in.counter
    restart_upper = (
        restart_out.counter if restart_out else (1 << 64) - 1
    )
    if stop_out is not None and stop_out.counter >= restart_in.counter:
        raise TraceContractError("stop parent overlaps restart parent")
    if stop_out is not None and stop_out.fields.get("rc") is None:
        raise TraceContractError("stop parent return lacks signed result")
    if restart_out is not None and restart_out.fields.get("rc") is None:
        raise TraceContractError("restart parent return lacks signed result")

    stop = {
        "parent_entered": True,
        "parent_returned": stop_out is not None,
        "parent_rc": None if stop_out is None else stop_out.fields["rc"],
        "child_suspend": _pair_in_window(
            records,
            entry_name="child_suspend_in",
            return_name="child_suspend_out",
            pid=stop_in.pid,
            lower=stop_in.counter,
            upper=stop_upper,
        ),
        "phy_suspend": _pair_in_window(
            records,
            entry_name="phy_suspend_in",
            return_name="phy_suspend_out",
            pid=stop_in.pid,
            lower=stop_in.counter,
            upper=stop_upper,
            argument=("suspend", 1),
        ),
        "power_off": _pair_in_window(
            records,
            entry_name="phy_power_in",
            return_name="phy_power_out",
            pid=stop_in.pid,
            lower=stop_in.counter,
            upper=stop_upper,
            argument=("on", 0),
        ),
    }
    restart = {
        "parent_entered": True,
        "parent_returned": restart_out is not None,
        "parent_rc": (
            None if restart_out is None else restart_out.fields["rc"]
        ),
        "child_resume": _pair_in_window(
            records,
            entry_name="child_resume_in",
            return_name="child_resume_out",
            pid=restart_in.pid,
            lower=restart_in.counter,
            upper=restart_upper,
        ),
        "phy_init": _pair_in_window(
            records,
            entry_name="phy_init_in",
            return_name="phy_init_out",
            pid=restart_in.pid,
            lower=restart_in.counter,
            upper=restart_upper,
        ),
        "power_on": _pair_in_window(
            records,
            entry_name="phy_power_in",
            return_name="phy_power_out",
            pid=restart_in.pid,
            lower=restart_in.counter,
            upper=restart_upper,
            argument=("on", 1),
        ),
        "notify": _pair_in_window(
            records,
            entry_name="notify_connect_in",
            return_name="notify_connect_out",
            pid=restart_in.pid,
            lower=restart_in.counter,
            upper=restart_upper,
        ),
    }
    child_suspend = stop["child_suspend"]
    phy_suspend = stop["phy_suspend"]
    power_off = stop["power_off"]
    if (
        child_suspend["returned"]
        and phy_suspend["returned"]
        and not (
            child_suspend["entry_counter"]
            < phy_suspend["entry_counter"]
            < phy_suspend["return_counter"]
            < child_suspend["return_counter"]
        )
    ):
        raise TraceContractError(
            "stop trace nesting contradicts the pinned source"
        )
    if (
        power_off["returned"]
        and phy_suspend["returned"]
        and not (
            phy_suspend["entry_counter"]
            < power_off["entry_counter"]
            < power_off["return_counter"]
            < phy_suspend["return_counter"]
        )
    ):
        raise TraceContractError(
            "power-off trace nesting contradicts the pinned source"
        )
    child_resume = restart["child_resume"]
    phy_init = restart["phy_init"]
    power_on = restart["power_on"]
    notify = restart["notify"]
    if (
        child_resume["returned"]
        and phy_init["returned"]
        and not (
            child_resume["entry_counter"]
            < phy_init["entry_counter"]
            < phy_init["return_counter"]
            < child_resume["return_counter"]
        )
    ):
        raise TraceContractError(
            "restart trace nesting contradicts the pinned source"
        )
    if (
        power_on["returned"]
        and phy_init["returned"]
        and not (
            phy_init["entry_counter"]
            < power_on["entry_counter"]
            < power_on["return_counter"]
            < phy_init["return_counter"]
        )
    ):
        raise TraceContractError(
            "power-on trace nesting contradicts the pinned source"
        )
    if (
        notify["returned"]
        and child_resume["returned"]
        and notify["entry_counter"] <= child_resume["return_counter"]
    ):
        raise TraceContractError(
            "connect-notify order contradicts the pinned source"
        )
    return {
        "classification": "authoritative",
        "clean": True,
        "stop": stop,
        "restart": restart,
        "outer_sm_work": _outer_state(records),
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

    resume = _pair_in_window(
        records,
        entry_name="resume_in",
        return_name="resume_out",
        pid=1,
        lower=pulls_in[0].counter,
        upper=pulls_out[0].counter,
    )
    run = _pair_in_window(
        records,
        entry_name="run_in",
        return_name="run_out",
        pid=1,
        lower=pulls_in[0].counter,
        upper=pulls_out[0].counter,
        argument=("on", 1),
    )
    if resume["entered"] != resume["returned"]:
        raise TraceContractError("bind trace has an incomplete resume pair")
    if run["entered"] != run["returned"]:
        raise TraceContractError("bind trace has an incomplete run-stop pair")
    if resume["returned"] and resume["rc"] < 0:
        raise TraceContractError("successful bind has negative resume return")
    if run["returned"] and resume["returned"]:
        if not (
            resume["entry_counter"]
            < run["entry_counter"]
            < run["return_counter"]
            < resume["return_counter"]
        ):
            raise TraceContractError(
                "run-stop is not nested inside runtime resume"
            )
    if not run["entered"]:
        classification = "pullup-without-run-stop"
    elif run["rc"] != 0:
        if not resume["returned"]:
            raise TraceContractError(
                "direct nonzero run-stop contradicts successful bind"
            )
        classification = "resume-run-stop-negative"
    elif resume["returned"]:
        classification = "resume-run-stop-zero"
    else:
        classification = "direct-run-stop-zero"
    return {
        "classification": classification,
        "clean": True,
        "pull_rc": 0,
        "resume_rc": resume["rc"],
        "run_rc": run["rc"],
    }


def _c_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def _stage_mask(stages: tuple[int, ...]) -> int:
    mask = 0
    for stage in stages:
        offset = stage - spec.ROLE_UDC_STAGE
        if offset < 0 or offset > 7:
            raise TraceContractError("detail stage is outside exact mask domain")
        mask |= 1 << offset
    return mask


def render_c_header(derived: dict[str, Any]) -> bytes:
    if derived.get("schema") not in {
        "s22plus_fyg8_p286_module_trace_contract_v1",
        "s22plus_fyg8_p286_derived_trace_contract_v1",
    }:
        raise TraceContractError("derived P2.86 trace schema is invalid")
    modules = derived.get("modules")
    if not isinstance(modules, list) or not modules:
        raise TraceContractError("derived P2.86 modules are invalid")
    offsets = modules[0].get("parent_pm_post_call_offsets")
    if (
        not isinstance(offsets, list)
        or len(offsets) != 2
        or any(type(value) is not int for value in offsets)
    ):
        raise TraceContractError("derived parent offsets are invalid")
    offset_tuple = (offsets[0], offsets[1])
    phases = (
        spec.PHASE_ROLE,
        spec.PHASE_CYCLE,
        spec.PHASE_BIND,
    )
    lines = [
        "/* Generated from s22plus_fyg8_p286_contract_spec.py. */",
        "#ifndef S22PLUS_FYG8_P282_TRACE_DESCRIPTOR_H",
        "#define S22PLUS_FYG8_P282_TRACE_DESCRIPTOR_H",
        "",
        f"#define P282_TRACE_BUFFER_KB {spec.TRACE_BUFFER_KB}U",
        f"#define P282_ROLE_DEADLINE_SEC {spec.ROLE_DEADLINE_SEC}LL",
        f"#define P282_ROLE_EVENT_COUNT "
        f"{len(spec.events_for_phase(spec.PHASE_ROLE))}U",
        f"#define P282_CYCLE_EVENT_COUNT "
        f"{len(spec.events_for_phase(spec.PHASE_CYCLE))}U",
        f"#define P282_BIND_EVENT_COUNT "
        f"{len(spec.events_for_phase(spec.PHASE_BIND))}U",
        f"#define P282_DETAIL_COUNT {len(spec.DIAGNOSTIC_DETAILS)}U",
        "",
    ]
    for name, value in spec.RUNTIME_STRING_CONSTANTS:
        lines.append(f"#define {name} {_c_string(value)}")
    lines.append("")
    for detail in p280_trace.spec.DIAGNOSTIC_DETAILS:
        macro = "P282_DETAIL_" + detail.name.upper().replace("-", "_")
        lines.append(f"#define {macro} 0x{detail.value:03x}U")
    lines.extend(
        (
            "",
            "struct p282_event_descriptor {",
            "    const char *name;",
            "    const char *definition;",
            "    const char *filter;",
            "};",
            "",
            "struct p282_detail_descriptor {",
            "    uint16_t value;",
            "    uint8_t outcome;",
            "    uint8_t stage_mask;",
            "};",
            "",
            "static const char *const p282_descriptor_udc_states[] = {",
        )
    )
    for value in spec.UDC_STATES:
        lines.append(f"    {_c_string(value)},")
    lines.extend(
        (
            "};",
            "",
            "static const char *const p282_descriptor_usb_speeds[] = {",
        )
    )
    for value in spec.USB_SPEEDS:
        lines.append(f"    {_c_string(value)},")
    lines.extend(("};", ""))
    for phase in phases:
        lines.append(
            f"static const struct p282_event_descriptor "
            f"p282_{phase}_events[] = {{"
        )
        for event in spec.events_for_phase(phase):
            lines.append(
                "    {"
                f"{_c_string(event.name)}, "
                f"{_c_string(event.definition(offset_tuple))}, "
                f"{_c_string(event.filter_expression)}"
                "},"
            )
        lines.extend(("};", ""))
    lines.append(
        "static const struct p282_detail_descriptor p282_details[] = {"
    )
    for detail in spec.DIAGNOSTIC_DETAILS:
        if len(detail.outcomes) != 1:
            raise TraceContractError("runtime detail must have one outcome")
        lines.append(
            "    {"
            f"0x{detail.value:03x}U, {detail.outcomes[0]}U, "
            f"0x{_stage_mask(detail.stages):02x}U"
            "},"
        )
    lines.extend(("};", "", "#endif", ""))
    data = (
        spec.render_classifier_contract_c().encode("ascii")
        + b"\n"
        + "\n".join(lines).encode("ascii")
    )
    for event in spec.TRACE_EVENTS:
        rendered = (
            f"{_c_string(event.name)}, "
            f"{_c_string(event.definition(offset_tuple))}, "
            f"{_c_string(event.filter_expression)}"
        ).encode("ascii")
        if data.count(rendered) != 1:
            raise TraceContractError("rendered event definition drifted")
    return data
