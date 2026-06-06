#!/usr/bin/env python3
"""V554 bounded companion QRTR WLFW readback.

This reuses the V553 fd-detail mapper and expects helper v80. The live path
starts the companion service set in the existing bounded window, then sends only
QRTR nameservice NEW_LOOKUP plus cleanup DEL_LOOKUP for WLFW service 69
instances 0 and 1. It does not send QMI payload, start Wi-Fi HAL, scan/connect,
link up, DHCP, route, or ping.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_companion_fd_detail_v553 as v553


base = v553.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v554-companion-qrtr-readback")
base.DEFAULT_HELPER_SHA256 = "f263ee8f15eb9d193b5e063cd2dfd67f8916f0a0b116626d2af6444a22a70f90"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v80"
base.PROOF_VERSION = "V554"
base.PROOF_SLUG = "v554-companion-qrtr-readback"
base.LIVE_HELPER_STEP_NAME = "v554-helper-run"
base.APPROVAL_PHRASE = (
    "approve v554 companion WLFW QRTR readback only; "
    "no QMI payload, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

MAX_CMDV1_COMMAND_ARGS = 30
KEY_RE = re.compile(r"^wifi_companion_qrtr_readback\.(?P<key>[^=]+)=(?P<value>.*)$")

_orig_helper_command = base.helper_command
_orig_run_live = base.run_live
_orig_render_summary = base.render_summary
_orig_classify = base.classify


def helper_command(args: base.argparse.Namespace) -> list[str]:
    command = _orig_helper_command(args)
    if base.approved(args):
        command.append("--allow-qrtr-ns-readback")
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(
            f"V554 helper command has {len(command)} args; cmdv1 safely carries "
            f"at most {MAX_CMDV1_COMMAND_ARGS} command args"
        )
    return command


def _qrtr_readback_keys(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = KEY_RE.match(line.strip())
        if match:
            values[match.group("key")] = match.group("value")
    return values


def _int_value(values: dict[str, str], key: str) -> int:
    try:
        return int(values.get(key, "0"), 0)
    except ValueError:
        return 0


def _case_rows(values: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in (0, 1):
        prefix = f"case_{index}"
        rows.append({
            "case": str(index),
            "service": values.get(f"{prefix}.service", ""),
            "instance": values.get(f"{prefix}.instance", ""),
            "socket_rc": values.get(f"{prefix}.socket.rc", ""),
            "new_lookup_rc": values.get(f"{prefix}.new_lookup_send.rc", ""),
            "del_lookup_rc": values.get(f"{prefix}.del_lookup_send.rc", ""),
            "events": values.get(f"{prefix}.readback.events", ""),
            "service_events": values.get(f"{prefix}.readback.service_events", ""),
            "end_of_list": values.get(f"{prefix}.readback.end_of_list", ""),
            "timeout": values.get(f"{prefix}.readback.timeout", ""),
            "qmi_attempted": values.get(f"{prefix}.qmi_attempted", ""),
            "status": values.get(f"{prefix}.status", ""),
        })
    return rows


def run_live(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    result = _orig_run_live(args, store)
    live_text = base.step_payload([result.get("live", {})], base.LIVE_HELPER_STEP_NAME)
    keys = _qrtr_readback_keys(live_text)
    result["qrtr_readback_keys"] = keys
    result["qrtr_readback_rows"] = _case_rows(keys)
    result["qrtr_readback_service_events"] = sum(
        _int_value(keys, f"case_{index}.readback.service_events") for index in (0, 1)
    )
    result["qrtr_readback_timeouts"] = sum(
        _int_value(keys, f"case_{index}.readback.timeout") for index in (0, 1)
    )
    result["qrtr_readback_end_of_list"] = sum(
        _int_value(keys, f"case_{index}.readback.end_of_list") for index in (0, 1)
    )
    result["qrtr_readback_qmi_attempted"] = sum(
        _int_value(keys, f"case_{index}.qmi_attempted") for index in (0, 1)
    )
    return result


def classify(args: base.argparse.Namespace,
             checks: list[base.Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _orig_classify(args, checks, live_result, dmesg)
    if args.command != "run" or not live_result:
        return decision, pass_ok, reason, next_step, live_executed
    if not live_result.get("all_postflight_safe"):
        return decision, pass_ok, reason, next_step, live_executed
    if live_result.get("helper_result") != "companion-window-pass":
        return decision, pass_ok, reason, next_step, live_executed

    keys = live_result.get("qrtr_readback_keys") or {}
    service_events = int(live_result.get("qrtr_readback_service_events") or 0)
    timeouts = int(live_result.get("qrtr_readback_timeouts") or 0)
    end_of_list = int(live_result.get("qrtr_readback_end_of_list") or 0)
    qmi_attempted = int(live_result.get("qrtr_readback_qmi_attempted") or 0)
    if qmi_attempted:
        return (
            "v554-wlfw-qrtr-readback-qmi-guard-failed",
            False,
            f"unexpected qmi_attempted={qmi_attempted}",
            "stop and inspect helper before any further live action",
            live_executed,
        )
    if keys.get("send_attempted") != "1":
        return (
            "v554-wlfw-qrtr-readback-not-sent",
            False,
            "QRTR readback send path did not execute despite V554 approval",
            "inspect helper approval flag and command length",
            live_executed,
        )
    if service_events:
        return (
            "v554-wlfw-qrtr-readback-services",
            True,
            f"WLFW QRTR nameservice returned service_events={service_events}",
            "run bounded Wi-Fi HAL start-only retry; still no scan/connect until HAL registration is proven",
            live_executed,
        )
    if end_of_list:
        return (
            "v554-wlfw-qrtr-readback-empty",
            True,
            f"WLFW QRTR readback reached end-of-list without service events; timeouts={timeouts}",
            "compare Android modem/QRTR companion readiness and add missing QRTR/QMI companion service before HAL retry",
            live_executed,
        )
    return (
        "v554-wlfw-qrtr-readback-timeout",
        True,
        f"WLFW QRTR readback produced no service events; timeouts={timeouts}",
        "compare Android modem/QRTR companion readiness and add missing QRTR/QMI companion service before HAL retry",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest)
    live = manifest.get("live_result") or {}
    rows = [
        [
            row["case"],
            row["service"],
            row["instance"],
            row["socket_rc"],
            row["new_lookup_rc"],
            row["del_lookup_rc"],
            row["events"],
            row["service_events"],
            row["end_of_list"],
            row["timeout"],
            row["qmi_attempted"],
            row["status"],
        ]
        for row in (live.get("qrtr_readback_rows") or [])
    ]
    return "\n".join([
        text,
        "",
        "## QRTR WLFW Readback",
        "",
        f"- service_events: `{live.get('qrtr_readback_service_events', 0)}`",
        f"- timeouts: `{live.get('qrtr_readback_timeouts', 0)}`",
        f"- end_of_list: `{live.get('qrtr_readback_end_of_list', 0)}`",
        f"- qmi_attempted: `{live.get('qrtr_readback_qmi_attempted', 0)}`",
        "",
        base.markdown_table(
            ["case", "service", "instance", "socket_rc", "new_lookup_rc", "del_lookup_rc", "events", "service_events", "end_of_list", "timeout", "qmi_attempted", "status"],
            rows,
        ) if rows else "- none",
    ])


base.helper_command = helper_command
base.run_live = run_live
base.classify = classify
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
