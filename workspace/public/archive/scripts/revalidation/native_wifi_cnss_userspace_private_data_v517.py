#!/usr/bin/env python3
"""V517 CNSS userspace readiness retry with private /data/vendor/wifi sockets.

V516 proved helper-owned `cnss_diag` and `cnss-daemon` can start and cleanly
stop, but `cnss-daemon` reported that its user socket path was missing.  V517
keeps the same bounded no-Wi-Fi-bring-up scope and adds only the private
`/data/vendor/wifi/sockets` materialization already supported by the helper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_cnss_userspace_readiness_v516 as base


base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v517-cnss-userspace-private-data-wifi")
base.APPROVAL_PHRASE = (
    "approve v517 cnss userspace private data wifi proof only; "
    "no qcwlanstate write, no scan/connect/link-up and no external ping"
)

_base_helper_command = base.helper_command
_base_classify = base.classify
_base_render_summary = base.render_summary


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = _base_helper_command(args)
    if "--data-wifi-mode" in command:
        return command
    try:
        insert_at = command.index("--null-device-mode") + 2
    except ValueError:
        insert_at = 6
    return command[:insert_at] + ["--data-wifi-mode", "private-empty"] + command[insert_at:]


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    before = base.run_step(args, store, "dmesg-before", ["run", "/cache/bin/toybox", "dmesg"], 60.0)
    live = base.run_step(args, store, "v517-helper-run", helper_command(args), args.max_runtime_sec + 35.0)
    after = base.run_step(args, store, "dmesg-after", ["run", "/cache/bin/toybox", "dmesg"], 60.0)
    post_ps = base.run_step(args, store, "post-ps", ["run", "/cache/bin/toybox", "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    post_net = base.run_step(args, store, "post-proc-net-dev", ["cat", "/proc/net/dev"], 10.0)
    keys = base.parse_keys(base.step_payload([live], "v517-helper-run"))
    before_payload = base.step_payload([before], "dmesg-before")
    after_payload = base.step_payload([after], "dmesg-after")
    dmesg_delta = base.dmesg_delta_text(before_payload, after_payload)
    base.write_capture(store, "dmesg-delta", dmesg_delta)
    return {
        "before": before,
        "live": live,
        "after": after,
        "dmesg_delta": dmesg_delta,
        "post_ps": post_ps,
        "post_net": post_net,
        "keys": keys,
        "helper_result": keys.get("cnss_userspace_readiness.result", "missing"),
        "all_postflight_safe": keys.get("cnss_userspace_readiness.all_postflight_safe") == "1",
    }


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _base_classify(args, checks, live_result, dmesg)
    decision = decision.replace("v516-", "v517-")
    next_step = next_step.replace("V516", "V517")
    if decision == "v517-cnss-userspace-readiness-no-fw-marker":
        reason = reason + "; private /data/vendor/wifi/sockets was present"
        next_step = "inspect QRTR/modem/perfd/property prerequisites before qcwlanstate retry"
    return decision, pass_ok, reason, next_step, live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    return _base_render_summary(manifest).replace(
        "# V516 CNSS Userspace Readiness Proof",
        "# V517 CNSS Userspace Private Data-WiFi Readiness Proof",
    )


base.helper_command = helper_command
base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
