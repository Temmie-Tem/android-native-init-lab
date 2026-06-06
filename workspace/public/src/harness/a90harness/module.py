"""Module contract for A90 host-side validation runs."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from a90harness.device import DeviceClient
from a90harness.evidence import EvidenceStore


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str
    duration_sec: float
    error: str = ""
    skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModuleOutcome:
    name: str
    ok: bool
    skipped: bool
    steps: list[StepResult]
    artifacts: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "skipped": self.skipped,
            "steps": [step.to_dict() for step in self.steps],
            "artifacts": self.artifacts,
            "metadata": self.metadata,
            "failed_steps": [step.to_dict() for step in self.steps if not step.ok],
        }


@dataclass
class ModuleContext:
    repo_root: Path
    store: EvidenceStore
    client: DeviceClient
    module_dir: Path
    expect_version: str
    host: str
    port: int
    timeout: float
    profile: str = "smoke"


class TestModule:
    """Base class for bounded validation modules."""

    name = "unnamed"
    description = ""
    cycle_label = "v172"
    read_only = True
    destructive = False
    requires_ncm = False
    requires_usb_rebind = False
    operator_confirm_required = False
    external_bridge_client = False

    def prepare(self, ctx: ModuleContext) -> StepResult:
        return StepResult("prepare", True, "no-op", 0.0)

    def run(self, ctx: ModuleContext) -> StepResult:
        raise NotImplementedError

    def cleanup(self, ctx: ModuleContext) -> StepResult:
        return StepResult("cleanup", True, "no-op", 0.0)

    def verify(self, ctx: ModuleContext) -> StepResult:
        return StepResult("verify", True, "no-op", 0.0)

    def artifacts(self, ctx: ModuleContext) -> list[str]:
        if not ctx.module_dir.exists():
            return []
        return sorted(
            str(path.relative_to(ctx.store.run_dir))
            for path in ctx.module_dir.rglob("*")
            if path.is_file()
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "cycle_label": self.cycle_label,
            "read_only": self.read_only,
            "destructive": self.destructive,
            "requires_ncm": self.requires_ncm,
            "requires_usb_rebind": self.requires_usb_rebind,
            "operator_confirm_required": self.operator_confirm_required,
            "external_bridge_client": self.external_bridge_client,
        }


def run_step(name: str, callback: Callable[[], StepResult]) -> StepResult:
    started = time.monotonic()
    try:
        result = callback()
        if result.duration_sec <= 0:
            result.duration_sec = time.monotonic() - started
        return result
    except Exception as exc:  # noqa: BLE001 - module runner records exact failure
        return StepResult(
            name,
            False,
            f"{type(exc).__name__}: {exc}",
            time.monotonic() - started,
            error=f"{type(exc).__name__}: {exc}",
        )
