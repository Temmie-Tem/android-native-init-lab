"""Safety gate evaluation for A90 validation modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from a90harness.module import TestModule


@dataclass
class GateOptions:
    allow_ncm: bool = False
    allow_usb_rebind: bool = False
    allow_destructive: bool = False
    assume_yes: bool = False


@dataclass
class GateResult:
    allowed: bool
    reasons: list[str]
    required_flags: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_gate(module: TestModule, options: GateOptions) -> GateResult:
    reasons: list[str] = []
    required_flags: list[str] = []
    if module.requires_ncm and not options.allow_ncm:
        reasons.append("requires host USB NCM precondition")
        required_flags.append("--allow-ncm")
    if module.requires_usb_rebind and not options.allow_usb_rebind:
        reasons.append("may rebind/reset USB control channel")
        required_flags.append("--allow-usb-rebind")
    if module.destructive and not options.allow_destructive:
        reasons.append("declared destructive")
        required_flags.append("--allow-destructive")
    if module.operator_confirm_required and not options.assume_yes:
        reasons.append("requires explicit operator confirmation")
        required_flags.append("--assume-yes")
    return GateResult(
        allowed=not reasons,
        reasons=reasons,
        required_flags=required_flags,
        metadata=module.metadata(),
    )
