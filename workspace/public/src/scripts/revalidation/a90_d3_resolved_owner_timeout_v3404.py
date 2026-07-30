#!/usr/bin/env python3
"""Host-only error model and source gate for the V3404 D3 handoff."""

from __future__ import annotations

from dataclasses import dataclass

import a90_d3_immutable_handoff_v3403 as previous


EBUSY = -16


@dataclass(frozen=True)
class DisplayCleanupOutcome:
    rc: int
    owner_timeouts: int
    resolved_owner_timeouts: int
    remaining_owners: int


def evaluate_display_cleanup(
    *,
    strict_mode: bool = True,
    service_rcs: tuple[int, ...] = (),
    owner_rcs: tuple[int, ...] = (),
    final_scan_rc: int = 0,
    remaining_owners: int = 0,
) -> DisplayCleanupOutcome:
    """Model the exact V3404 error-selection policy."""

    final_rc = 0
    owner_timeouts = 0

    for rc in service_rcs:
        if rc < 0:
            final_rc = rc
    for rc in owner_rcs:
        if strict_mode and rc == EBUSY:
            owner_timeouts += 1
        elif rc < 0:
            final_rc = rc

    resolved_owner_timeouts = 0
    if final_scan_rc < 0:
        if final_rc >= 0:
            final_rc = final_scan_rc
    elif remaining_owners != 0:
        final_rc = EBUSY
    else:
        resolved_owner_timeouts = owner_timeouts

    return DisplayCleanupOutcome(
        rc=final_rc,
        owner_timeouts=owner_timeouts,
        resolved_owner_timeouts=resolved_owner_timeouts,
        remaining_owners=remaining_owners,
    )


def _function_body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start < 0:
        return ""
    brace = source.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    for pos in range(brace, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start : pos + 1]
    return ""


def validate_source_contract(source: str) -> tuple[str, ...]:
    """Require V3403 ordering plus the narrow V3404 timeout resolution."""

    issues = list(previous.validate_source_contract(source))
    body = _function_body(
        source,
        "static int d_handoff_stop_display_owners_mode("
        "const char *tag, bool preserve_dpublic)",
    )
    if not body:
        issues.append("missing display-owner cleanup function")
        return tuple(issues)

    ordered_tokens = (
        "unsigned int owner_timeouts = 0;",
        "int scan_rc;",
        "rc = d_handoff_stop_drm_owner(tag, pid);",
        "if (!preserve_dpublic && rc == -EBUSY) {",
        "owner_timeouts++;",
        "} else if (rc < 0) {",
        "final_rc = rc;",
        "scan_rc = d_handoff_count_display_owners(preserve_dpublic, &remaining);",
        "if (scan_rc < 0) {",
        "final_rc = final_rc < 0 ? final_rc : scan_rc;",
        "} else if (remaining != 0U) {",
        "final_rc = -EBUSY;",
        "} else if (owner_timeouts != 0U) {",
        "resolved_by_zero_owner_scan=1",
    )
    cursor = -1
    for token in ordered_tokens:
        pos = body.find(token, cursor + 1)
        if pos < 0:
            issues.append(f"missing or out-of-order V3404 token: {token}")
            continue
        cursor = pos

    timeout_start = body.find("if (!preserve_dpublic && rc == -EBUSY) {")
    timeout_end = body.find("} else if (rc < 0) {", timeout_start)
    if timeout_start >= 0 and timeout_end > timeout_start:
        timeout_branch = body[timeout_start:timeout_end]
        if "final_rc =" in timeout_branch:
            issues.append("per-owner EBUSY still writes final_rc before final rescan")

    zero_start = body.find("} else if (owner_timeouts != 0U) {")
    zero_end = body.find("\n    }", zero_start)
    if zero_start >= 0 and zero_end > zero_start:
        zero_branch = body[zero_start:zero_end]
        if "final_rc =" in zero_branch:
            issues.append("zero-owner resolution rewrites an unrelated final_rc")

    return tuple(issues)
