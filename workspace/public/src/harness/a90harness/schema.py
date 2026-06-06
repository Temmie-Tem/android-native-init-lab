"""Common result schema for A90 host-side validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CommandRecord:
    name: str
    command: list[str]
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    transcript: str
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HarnessResult:
    label: str
    ok: bool
    checks: list[CheckResult]
    commands: list[CommandRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
            "commands": [command.to_dict() for command in self.commands],
            "failed_checks": [check.to_dict() for check in self.checks if not check.ok],
            "failed_commands": [command.to_dict() for command in self.commands if not command.ok],
        }

