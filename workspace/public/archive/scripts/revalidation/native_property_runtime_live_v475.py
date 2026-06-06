#!/usr/bin/env python3
"""V475 Android-readable private property runtime live proof.

This is the V472 live deploy flow with Android-compatible runtime file modes:
private evidence stays host-private, while the device-side property area is
installed under a helper-only private root as 0755 directories and 0444 property
files so Android service/HAL children running as uid 1000 can map it read-only.
It does not install a global /dev/__properties__, start daemons, or bring Wi-Fi
up.
"""

from __future__ import annotations

from pathlib import Path

import native_property_runtime_live_v472 as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v475-android-readable-private-property-runtime-live")
base.REMOTE_WORKDIR = "/mnt/sdext/a90/private-property-v317/v475"
base.REMOTE_PROP_ROOT = base.REMOTE_WORKDIR + "/dev/__properties__"
base.APPROVAL_PHRASE = (
    "approve v475 Android-readable private property runtime deploy and lookup proof only; "
    "no daemon start and no Wi-Fi bring-up"
)

_BASE_DECIDE = base.decide
_BASE_RENDER_SUMMARY = base.render_summary


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_error: str) -> tuple[str, bool, str, str]:
    decision, pass_ok, reason, next_step = _BASE_DECIDE(args, checks, live_error)
    return (
        decision.replace("v472-extended-property-runtime", "v475-android-readable-property-runtime"),
        pass_ok,
        reason.replace("V472", "V475"),
        next_step.replace("V472", "V475"),
    )


def render_summary(manifest: dict[str, object]) -> str:
    return _BASE_RENDER_SUMMARY(manifest).replace(
        "# V472 Extended Private Property Runtime Live Proof",
        "# V475 Android-Readable Private Property Runtime Live Proof",
        1,
    )


base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
