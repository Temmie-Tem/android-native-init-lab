#!/usr/bin/env python3
"""Audit S22+ USB trace names against their rendered probe attachments.

The event name is evidence-facing.  A syntactically valid kprobe definition is
not enough: the name must describe the function body to which tracefs actually
attaches it.  This module is intentionally independent of any frozen candidate
source contract so new contracts can use it as a pre-LTO gate.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


class ProbeNameGateError(ValueError):
    pass


_DEFINITION = re.compile(
    r"^(?P<kind>[pr]):(?P<group>[A-Za-z0-9_]+)/"
    r"(?P<name>[A-Za-z0-9_]+) "
    r"(?P<target>\S+)(?: .*)?$"
)
_TRACEFS_READBACK = re.compile(
    r"^(?P<prefix>p|r(?P<maxactive>[1-9][0-9]*)?):"
    r"(?P<group>[A-Za-z0-9_]+)/(?P<name>[A-Za-z0-9_]+) "
    r"(?P<target>\S+)(?: .*)?$"
)

# Every actual attachment symbol must opt in to every permitted evidence-facing
# stem.  Generic labels such as "worker" are deliberately absent.
DEFAULT_ALLOWED_STEMS = MappingProxyType(
    {
        "dwc3_otg_start_peripheral": frozenset(
            (
                "start",
                "parent_pm",
                "child_pm",
                "stop_peripheral",
                "restart_peripheral",
            )
        ),
        "dwc3_otg_sm_work": frozenset(("outer_sm_work",)),
        "mode_store": frozenset(("mode_store",)),
        "dwc3_msm_runtime_suspend": frozenset(
            ("parent_runtime_suspend",)
        ),
        "dwc3_runtime_suspend": frozenset(("child_suspend",)),
        "dwc3_runtime_resume": frozenset(("child_resume", "resume")),
        "msm_hsphy_set_suspend": frozenset(("phy_suspend",)),
        "msm_hsphy_enable_power": frozenset(("phy_power",)),
        "msm_hsphy_init": frozenset(("phy_init",)),
        "msm_hsphy_notify_connect": frozenset(("notify_connect",)),
        "dwc3_gadget_pullup": frozenset(("pull",)),
        "dwc3_gadget_resume": frozenset(("gadget_resume",)),
        "dwc3_gadget_run_stop": frozenset(("run",)),
        "dwc3_msm_suspend": frozenset(
            (
                "parent_suspend",
                "parent_mutex_acquired",
                "parent_perf_cancel_done",
                "parent_prepare_done",
                "parent_irq_disabled",
                "parent_hsphy_done",
                "parent_ssphy_done",
                "parent_clocks_done",
                "parent_gdsc_done",
                "parent_bus_vote_done",
                "parent_wake_irq_done",
                "parent_mutex_released",
            )
        ),
    }
)


@dataclass(frozen=True)
class AuditIssue:
    code: str
    phase: str
    event_name: str
    declared_symbol: str
    attached_symbol: str
    detail: str


def event_stem(name: str) -> str:
    for suffix in ("_in", "_out"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _render_definition(
    event: Any,
    post_call_offsets: tuple[int, int],
) -> str:
    offsets = (
        post_call_offsets
        if getattr(event, "post_call_ordinal", None) is not None
        else None
    )
    definition = event.definition(offsets)
    if not isinstance(definition, str):
        raise ProbeNameGateError("probe definition is not text")
    return definition.removesuffix("\n")


def _attached_symbol(target: str) -> str:
    unqualified = target.rsplit(":", 1)[-1]
    return unqualified.split("+", 1)[0]


def _target_components(target: str) -> tuple[str | None, str, int | None]:
    if ":" in target:
        module, unqualified = target.rsplit(":", 1)
    else:
        module = None
        unqualified = target
    if "+" in unqualified:
        symbol, raw_offset = unqualified.split("+", 1)
        try:
            offset = int(raw_offset, 0)
        except ValueError as error:
            raise ProbeNameGateError(
                f"invalid tracefs readback offset {raw_offset!r}"
            ) from error
    else:
        symbol = unqualified
        offset = None
    return module, symbol, offset


def audit_events(
    events: Iterable[Any],
    *,
    post_call_offsets: tuple[int, int] = (0, 0),
    allowed_stems: Mapping[str, frozenset[str]] = DEFAULT_ALLOWED_STEMS,
) -> tuple[AuditIssue, ...]:
    issues: list[AuditIssue] = []
    for event in events:
        phase = str(getattr(event, "phase", ""))
        name = str(getattr(event, "name", ""))
        declared_symbol = str(getattr(event, "symbol", ""))
        definition = _render_definition(event, post_call_offsets)
        match = _DEFINITION.fullmatch(definition)
        if match is None:
            issues.append(
                AuditIssue(
                    "definition-malformed",
                    phase,
                    name,
                    declared_symbol,
                    "",
                    definition,
                )
            )
            continue

        attached_symbol = _attached_symbol(match.group("target"))
        if match.group("name") != name:
            issues.append(
                AuditIssue(
                    "definition-event-name-mismatch",
                    phase,
                    name,
                    declared_symbol,
                    attached_symbol,
                    f"rendered name is {match.group('name')!r}",
                )
            )

        declared_kind = getattr(event, "probe_kind", "")
        if declared_kind not in {"entry", "return"}:
            issues.append(
                AuditIssue(
                    "declared-probe-kind-invalid",
                    phase,
                    name,
                    declared_symbol,
                    attached_symbol,
                    f"declared kind is {declared_kind!r}",
                )
            )
        expected_kind = "r" if declared_kind == "return" else "p"
        if match.group("kind") != expected_kind:
            issues.append(
                AuditIssue(
                    "definition-probe-kind-mismatch",
                    phase,
                    name,
                    declared_symbol,
                    attached_symbol,
                    f"rendered kind is {match.group('kind')!r}",
                )
            )

        if attached_symbol != declared_symbol:
            issues.append(
                AuditIssue(
                    "definition-symbol-mismatch",
                    phase,
                    name,
                    declared_symbol,
                    attached_symbol,
                    "rendered attachment differs from declared symbol",
                )
            )

        permitted = allowed_stems.get(attached_symbol)
        if permitted is None:
            issues.append(
                AuditIssue(
                    "unknown-attached-symbol",
                    phase,
                    name,
                    declared_symbol,
                    attached_symbol,
                    "symbol has no reviewed evidence-name mapping",
                )
            )
            continue

        stem = event_stem(name)
        if stem not in permitted:
            issues.append(
                AuditIssue(
                    "descriptor-semantic-mismatch",
                    phase,
                    name,
                    declared_symbol,
                    attached_symbol,
                    f"stem {stem!r} is not one of {sorted(permitted)!r}",
                )
            )

    return tuple(issues)


def audit_tracefs_readback(
    text: str,
    events: Iterable[Any],
    *,
    group: str,
) -> tuple[AuditIssue, ...]:
    """Compare kernel-normalized kprobe_events readback to the declarations.

    Kretprobe input uses ``r:`` when maxactive is omitted.  The kernel fills
    the default during registration and renders it back as, for example,
    ``r16:``.  Readback validation must normalize that field rather than
    treating the input spelling as invariant.
    """

    if not isinstance(text, str):
        raise ProbeNameGateError("tracefs readback is not text")
    if not isinstance(group, str) or not group:
        raise ProbeNameGateError("tracefs readback group is empty")

    declared = tuple(events)
    expected = {str(event.name): event for event in declared}
    if len(expected) != len(declared):
        raise ProbeNameGateError("declared event names are not unique")

    issues: list[AuditIssue] = []
    observed: dict[str, int] = {}
    marker = f":{group}/"
    for line in text.splitlines():
        if marker not in line:
            continue
        match = _TRACEFS_READBACK.fullmatch(line)
        if match is None:
            issues.append(
                AuditIssue(
                    "readback-definition-malformed",
                    "",
                    "",
                    "",
                    "",
                    line,
                )
            )
            continue
        name = match.group("name")
        event = expected.get(name)
        if event is None:
            issues.append(
                AuditIssue(
                    "readback-event-unexpected",
                    "",
                    name,
                    "",
                    _attached_symbol(match.group("target")),
                    line,
                )
            )
            continue

        observed[name] = observed.get(name, 0) + 1
        if observed[name] > 1:
            issues.append(
                AuditIssue(
                    "readback-event-duplicate",
                    str(getattr(event, "phase", "")),
                    name,
                    str(getattr(event, "symbol", "")),
                    _attached_symbol(match.group("target")),
                    line,
                )
            )
            continue

        prefix = match.group("prefix")
        actual_kind = "return" if prefix.startswith("r") else "entry"
        declared_kind = str(getattr(event, "probe_kind", ""))
        module, symbol, offset = _target_components(match.group("target"))
        declared_module = getattr(event, "module", None)
        declared_symbol = str(getattr(event, "symbol", ""))
        declared_offset = getattr(event, "offset", None)
        phase = str(getattr(event, "phase", ""))

        if actual_kind != declared_kind:
            issues.append(
                AuditIssue(
                    "readback-probe-kind-mismatch",
                    phase,
                    name,
                    declared_symbol,
                    symbol,
                    f"readback kind is {actual_kind!r}",
                )
            )
        if symbol != declared_symbol or module != declared_module:
            issues.append(
                AuditIssue(
                    "readback-attachment-mismatch",
                    phase,
                    name,
                    declared_symbol,
                    symbol,
                    f"readback target is {match.group('target')!r}",
                )
            )
        if offset != declared_offset:
            issues.append(
                AuditIssue(
                    "readback-offset-mismatch",
                    phase,
                    name,
                    declared_symbol,
                    symbol,
                    f"readback offset is {offset!r}, expected {declared_offset!r}",
                )
            )

    for name, event in expected.items():
        if name not in observed:
            issues.append(
                AuditIssue(
                    "readback-event-missing",
                    str(getattr(event, "phase", "")),
                    name,
                    str(getattr(event, "symbol", "")),
                    "",
                    f"no {group!r} readback entry",
                )
            )

    return tuple(issues)


def require_clean(
    events: Iterable[Any],
    *,
    post_call_offsets: tuple[int, int] = (0, 0),
    allowed_stems: Mapping[str, frozenset[str]] = DEFAULT_ALLOWED_STEMS,
) -> None:
    issues = audit_events(
        events,
        post_call_offsets=post_call_offsets,
        allowed_stems=allowed_stems,
    )
    if issues:
        first = issues[0]
        raise ProbeNameGateError(
            f"{len(issues)} probe attachment-name issue(s); "
            f"first={first.code}:{first.event_name}:"
            f"{first.attached_symbol}"
        )


def require_tracefs_readback_clean(
    text: str,
    events: Iterable[Any],
    *,
    group: str,
) -> None:
    issues = audit_tracefs_readback(text, events, group=group)
    if issues:
        first = issues[0]
        raise ProbeNameGateError(
            f"{len(issues)} tracefs readback issue(s); "
            f"first={first.code}:{first.event_name}:"
            f"{first.attached_symbol}"
        )


def _parse_offset(value: str) -> int:
    try:
        result = int(value, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError("offset must be an integer") from error
    if result < 0:
        raise argparse.ArgumentTypeError("offset must be nonnegative")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec_module")
    parser.add_argument(
        "--events-attribute",
        default="TRACE_EVENTS",
    )
    parser.add_argument(
        "--post-call-offset",
        action="append",
        type=_parse_offset,
        default=[],
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    offsets = tuple(args.post_call_offset)
    if offsets and len(offsets) != 2:
        raise ProbeNameGateError(
            "provide either zero or exactly two post-call offsets"
        )
    post_call_offsets = offsets if offsets else (0, 0)

    module = importlib.import_module(args.spec_module)
    events = tuple(getattr(module, args.events_attribute))
    issues = audit_events(
        events,
        post_call_offsets=post_call_offsets,
    )
    payload = {
        "schema": "s22plus_probe_attachment_name_audit_v1",
        "spec_module": args.spec_module,
        "event_count": len(events),
        "issue_count": len(issues),
        "issues": [asdict(issue) for issue in issues],
        "verdict": (
            "PASS_PROBE_ATTACHMENT_NAMES"
            if not issues
            else "FAIL_PROBE_ATTACHMENT_NAMES"
        ),
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
