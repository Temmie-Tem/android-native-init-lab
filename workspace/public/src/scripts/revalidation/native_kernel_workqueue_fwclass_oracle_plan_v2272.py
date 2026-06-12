#!/usr/bin/env python3
"""Define the V2272 workqueue firmware_class function-pointer oracle."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root


REPO_ROOT = repo_root()
SOURCE_ROOT = REPO_ROOT / "tmp" / "wifi" / "v766-icnss-qcacld-patch-apply-build" / "source"
WORKQUEUE_TRACE = SOURCE_ROOT / "include" / "trace" / "events" / "workqueue.h"
FIRMWARE_CLASS = SOURCE_ROOT / "drivers" / "base" / "firmware_class.c"
V2216_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V2216_PERF_REGS_CODEWORD_SAMPLE_RING_LIVE_2026-06-12.md"
V2253_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V2253_FWCLASS_BOUNDARY_STACK_LIVE_2026-06-12.md"
DEFAULT_OUT = REPO_ROOT / "docs" / "artifacts" / "native-init-frontier-candidates.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--write", action="store_true", help="write the public candidate JSON")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def regex_present(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.MULTILINE | re.DOTALL) is not None


def firmware_tracepoint_source_absent() -> bool:
    trace_root = SOURCE_ROOT / "include" / "trace" / "events"
    if not trace_root.exists():
        return False
    for path in trace_root.glob("*.h"):
        text = read_text(path)
        if path.name == "firmware.h" or "TRACE_SYSTEM firmware" in text or "TRACE_SYSTEM(firmware)" in text:
            return False
    return True


def build_plan() -> dict[str, Any]:
    workqueue_text = read_text(WORKQUEUE_TRACE)
    firmware_text = read_text(FIRMWARE_CLASS)
    v2216_text = read_text(V2216_REPORT)
    v2253_text = read_text(V2253_REPORT)

    checks = {
        "workqueue_trace_source_exists": WORKQUEUE_TRACE.exists(),
        "workqueue_queue_work_has_function_field": regex_present(
            workqueue_text,
            r"TRACE_EVENT\(workqueue_queue_work,.*?__field\(\s*void \*,\s*function\).*?__entry->function\s*=\s*work->func",
        ),
        "workqueue_execute_start_has_function_field": regex_present(
            workqueue_text,
            r"TRACE_EVENT\(workqueue_execute_start,.*?__field\(\s*void \*,\s*function\).*?__entry->function\s*=\s*work->func",
        ),
        "firmware_nowait_worker_exists": regex_present(
            firmware_text,
            r"static void request_firmware_work_func\(struct work_struct \*work\).*?_request_firmware",
        ),
        "firmware_nowait_schedules_worker": regex_present(
            firmware_text,
            r"INIT_WORK\(&fw_work->work,\s*request_firmware_work_func\);\s*schedule_work\(&fw_work->work\);",
        ),
        "firmware_tracepoint_source_absent": firmware_tracepoint_source_absent(),
        "v2216_exact_codeword_slide_reported": "Decision: `v2216-codeword-slide-exact`" in v2216_text
        and "Codeword exact slide accepted: `true`" in v2216_text,
        "v2253_fwclass_boundary_closed": "target-stack-visible-before-feed" in v2253_text
        and "sampler-miss artifact" in v2253_text,
    }
    ready = all(checks.values())
    candidate = {
        "id": "t1-workqueue-fwclass-function-pointer-oracle",
        "track": "T1",
        "status": "ready_for_next_v_iteration" if ready else "blocked_by_missing_evidence",
        "safe_actionable_now": ready,
        "summary": (
            "Use stock workqueue tracepoints as an independent firmware_class/qcacld-HDD tail oracle: "
            "collect workqueue_queue_work and workqueue_execute_start function pointers, then classify them "
            "with the per-boot exact codeword slide."
        ),
        "why_independent": [
            "It does not reuse generic CPU-clock sampling.",
            "It does not rely on /proc/*/stack boundary snapshots from V2253.",
            "It observes the static kernel workqueue function pointer copied from work->func.",
        ],
        "next_runner_contract": [
            "Capture workqueue:workqueue_queue_work and workqueue:workqueue_execute_start around the post-FWREADY boot_wlan/firmware_class window.",
            "Record work pointer, function pointer, workqueue pointer, requested CPU, and executing CPU where available.",
            "Classify function pointers with the V2216/V2217 exact-slide/codeword method for the same boot.",
            "Treat hits on request_firmware_work_func or adjacent qcacld/CNSS workers as code-path identity evidence, not as a network functional test.",
            "Keep Wi-Fi scan/connect/DHCP/ping and credentials out of scope unless a later V-iteration explicitly requires them.",
        ],
        "expected_discriminator": {
            "positive": "function pointer sequence includes firmware_class request_firmware_work_func or source-backed qcacld/CNSS worker functions in the target window",
            "negative": "target window has workqueue activity but no firmware_class/qcacld-HDD function pointer hits, narrowing the tail gap to a non-workqueue/synchronous path",
            "inconclusive": "tracepoint unavailable live, function pointers cannot be symbolized for the same boot, or capture starts after the target window",
        },
    }
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "decision": "v2272-workqueue-fwclass-oracle-defined" if ready else "v2272-workqueue-fwclass-oracle-not-ready",
        "checks": checks,
        "candidates": [candidate],
        "source_paths": {
            "workqueue_trace": rel(WORKQUEUE_TRACE),
            "firmware_class": rel(FIRMWARE_CLASS),
            "v2216_report": rel(V2216_REPORT),
            "v2253_report": rel(V2253_REPORT),
        },
    }


def render_text(data: dict[str, Any]) -> str:
    candidate = data["candidates"][0]
    lines = [
        f"decision={data['decision']}",
        f"candidate={candidate['id']}",
        f"status={candidate['status']}",
        f"safe_actionable_now={candidate['safe_actionable_now']}",
    ]
    for name, value in data["checks"].items():
        lines.append(f"check.{name}={value}")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    data = build_plan()
    if args.write:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.write:
        print(render_text(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
