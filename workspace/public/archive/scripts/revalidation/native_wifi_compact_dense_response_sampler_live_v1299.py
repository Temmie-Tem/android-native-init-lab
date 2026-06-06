#!/usr/bin/env python3
"""V1299 bounded compact dense no-write late per_proxy response sampler.

This wraps the V1242 response sampler with helper v272 and injects both dense
and compact response sampler flags. It keeps the V1295 live actor scope but
requires the compact path to finish the full dense window below the helper
stdout cap.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


DENSE_RESPONSE_SAMPLER_FLAG = "--pm-observer-late-per-proxy-dense-response-sampler"
COMPACT_RESPONSE_SAMPLER_FLAG = "--pm-observer-late-per-proxy-compact-response-sampler"
EXPECTED_MIN_SAMPLE_COUNT = 42

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1299-compact-dense-response-sampler-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1299-compact-dense-response-sampler-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v272"
base.HELPER_SHA256 = "1344b4ac101aa0cde56a46f1274b2d01f25d11b424158d822bff71234a1e7885"
base.CYCLE_LABEL = "v1299"
base.CYCLE_NAME = "V1299"
base.SUMMARY_HEADING = "V1299 Compact Dense Response Sampler"
base.EVIDENCE_FILE_PREFIX = "v1299"

_ORIGINAL_DECIDE = base.decide_v1242


def _force_compact_dense_response_sampler_child_command(original):
    def command(args: Any) -> list[str]:
        result = original(args)
        for flag in (
            base.RESPONSE_SAMPLER_FLAG,
            DENSE_RESPONSE_SAMPLER_FLAG,
            COMPACT_RESPONSE_SAMPLER_FLAG,
        ):
            if flag not in result:
                result.append(flag)
        return result

    return command


def _decision(suffix: str) -> str:
    return f"{base.CYCLE_LABEL}-{suffix}"


def decide_v1299(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            _decision("compact-dense-response-sampler-plan-ready"),
            True,
            "plan-only; no device mutation or live actor executed",
            "run V1299 bounded compact dense no-write response sampler",
        )

    sampler = manifest.get("response_sampler") or {}
    mode = str(sampler.get("mode") or "")
    sample_count = int(sampler.get("sample_count") or 0)
    ended = bool(sampler.get("ended"))

    if "dense-compact" not in mode:
        return (
            _decision("compact-dense-mode-missing"),
            False,
            f"helper output mode did not prove compact dense sampler: mode={mode!r}",
            "verify helper v272 deploy and compact flag injection",
        )
    if not ended:
        return (
            _decision("compact-dense-truncated-or-incomplete"),
            False,
            "compact dense sampler did not emit response_sampler.end",
            "inspect transcript for remaining output cap or runtime interruption",
        )
    if sample_count < EXPECTED_MIN_SAMPLE_COUNT:
        return (
            _decision("compact-dense-short-window"),
            False,
            f"compact dense sampler emitted {sample_count} samples; expected at least {EXPECTED_MIN_SAMPLE_COUNT}",
            "inspect compact sampler loop and transcript before rerunning live",
        )

    decision, passed, reason, next_step = _ORIGINAL_DECIDE(manifest)
    if not passed:
        return decision, passed, reason, next_step
    return (
        _decision("compact-dense-full-window-" + decision.removeprefix(base.CYCLE_LABEL + "-")),
        True,
        f"compact dense sampler completed full window ({sample_count} samples) before classification: {reason}",
        next_step,
    )


base._force_response_sampler_child_command = _force_compact_dense_response_sampler_child_command
base.decide_v1242 = decide_v1299


if __name__ == "__main__":
    raise SystemExit(base.main())
