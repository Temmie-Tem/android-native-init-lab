"""Supervisor runner for A90 host-side validation modules."""

from __future__ import annotations

import time
from pathlib import Path

from a90harness.device import DeviceClient
from a90harness.evidence import EvidenceStore
from a90harness.module import ModuleContext, ModuleOutcome, TestModule, run_step
from a90harness.observer import ObserverSummary, run_observer


class ModuleRunner:
    """Run one validation module with optional observer evidence."""

    def __init__(self,
                 *,
                 repo_root: Path,
                 store: EvidenceStore,
                 client: DeviceClient,
                 expect_version: str,
                 host: str,
                 port: int,
                 timeout: float) -> None:
        self.repo_root = repo_root
        self.store = store
        self.client = client
        self.expect_version = expect_version
        self.host = host
        self.port = port
        self.timeout = timeout

    def run(self,
            module: TestModule,
            *,
            profile: str = "smoke",
            observer_duration_sec: float = 0.0,
            observer_interval_sec: float = 5.0) -> tuple[ModuleOutcome, ObserverSummary | None]:
        started = time.monotonic()
        self.store.mkdir("modules")
        module_dir = self.store.mkdir("modules", module.name)
        ctx = ModuleContext(
            repo_root=self.repo_root,
            store=self.store,
            client=self.client,
            module_dir=module_dir,
            expect_version=self.expect_version,
            host=self.host,
            port=self.port,
            timeout=self.timeout,
            profile=profile,
        )

        observer_summary: ObserverSummary | None = None
        if observer_duration_sec > 0:
            observer_summary = run_observer(
                self.client,
                self.store,
                duration_sec=observer_duration_sec,
                interval_sec=observer_interval_sec,
            )

        steps = [
            run_step("prepare", lambda: module.prepare(ctx)),
            run_step("run", lambda: module.run(ctx)),
            run_step("cleanup", lambda: module.cleanup(ctx)),
            run_step("verify", lambda: module.verify(ctx)),
        ]
        metadata = module.metadata()
        metadata["duration_sec"] = time.monotonic() - started
        ok = all(step.ok for step in steps) and (observer_summary is None or observer_summary.ok)
        skipped = any(step.skipped for step in steps)
        outcome = ModuleOutcome(module.name, ok, skipped, steps, module.artifacts(ctx), metadata)
        self.store.write_json(f"modules/{module.name}/module-result.json", outcome.to_dict())
        return outcome, observer_summary
