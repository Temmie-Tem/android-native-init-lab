"""Host-only fresh-process probe for the generic Process-v2 attempt journal.

This helper intentionally lives outside revalidation/ because it is a test
driver, not a device observer. It invokes only Journal and attempt-start
functions in disposable directories; no backend, ADB, USB, or Odin call is
made.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any


def _child(script_dir: Path, run_dir: Path, root: Path, stage: str) -> dict[str, Any]:
    code = f'''import json, sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, {str(script_dir)!r})
import device_action_f1_v2 as core
import device_action_f1_live_v2 as live

class ForbiddenBackend:
    calls = 0
    def transfer(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("backend transfer invoked by journal probe")

run = Path({str(run_dir)!r})
binding = "a" * 64
prepared = SimpleNamespace(run_dir=run, binding_sha256=binding)
backend = ForbiddenBackend()
def forbidden_backend_call(*args, **kwargs):
    backend.calls += 1
    raise AssertionError("device/backend function invoked by journal probe")
for method in ("transfer", "request_download", "wait_download", "recheck_android", "observe_candidate", "verify_final"):
    setattr(live.SamsungOdinBackend, method, forbidden_backend_call)
if {stage!r} == "first":
    run.mkdir(parents=True, exist_ok=True)
    journal = core.Journal.create(run / "transaction", binding, {{"host_only": True}})
    journal.transition("APPROVED", "ok", {{"host_only": True}})
    journal.transition("DOWNLOAD_IDENTIFIED", "ok", {{"host_only": True}})
elif {stage!r} in {{"second", "third"}}:
    journal = core.Journal.reopen(run / "transaction", binding)
else:
    raise AssertionError("bad probe stage")
if {stage!r} in {{"first", "second"}}:
    attempt, prefix, _ = live._begin_transfer_attempt(prepared, journal, "candidate")
    print(json.dumps({{"attempt": attempt, "prefix": prefix, "backend_calls": backend.calls}}))
else:
    try:
        live._begin_transfer_attempt(prepared, journal, "candidate")
    except Exception as exc:
        print(json.dumps({{"rejected": True, "error": str(exc), "backend_calls": backend.calls}}))
    else:
        raise AssertionError("third attempt was accepted")
'''
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{stage}: {completed.stderr[-1000:]}")
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{stage}: child did not return JSON") from exc
    return value


def run_probe(script_dir: Path, run_dir: Path, root: Path) -> list[dict[str, Any]]:
    return [_child(script_dir, run_dir, root, stage) for stage in ("first", "second", "third")]
