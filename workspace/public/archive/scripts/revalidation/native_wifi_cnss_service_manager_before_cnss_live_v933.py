#!/usr/bin/env python3
"""V933 bounded CNSS/service-manager before-CNSS live proof.

Thin wrapper around the V931 matrix runner. It keeps the same helper v154,
guardrails, and WLFW-precondition gate, but changes the default matrix order to
`before-cnss`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_cnss_service_manager_matrix_live_v931 as v931


v931.base.DEFAULT_OUT_DIR = Path("tmp/wifi/v933-cnss-service-manager-before-cnss-live")
v931.base.LATEST_POINTER = Path("tmp/wifi/latest-v933-cnss-service-manager-before-cnss-live.txt")
v931.DEFAULT_SERVICE_MANAGER_ORDER = "before-cnss"

_original_decide = v931.decide
_original_render_summary = v931.render_summary


def _v933_label(label: str) -> str:
    if label.startswith("v931-"):
        return "v933-" + label[len("v931-") :]
    return label


def decide(
    args: Any,
    local: dict[str, Any],
    steps: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> tuple[str, bool, str, str]:
    decision, pass_ok, reason, next_step = _original_decide(args, local, steps, analysis)
    return _v933_label(decision), pass_ok, reason, next_step.replace("V931", "V933")


def render_summary(manifest: dict[str, Any]) -> str:
    text = _original_render_summary(manifest)
    text = text.replace("# V931 CNSS Service-Manager Matrix Live", "# V933 CNSS Service-Manager Before-CNSS Live")
    return text.replace("V931", "V933")


v931.decide = decide
v931.render_summary = render_summary
v931.base.decide = decide
v931.base.render_summary = render_summary
v931.v923.decide = decide
v931.v923.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(v931.base.main())
