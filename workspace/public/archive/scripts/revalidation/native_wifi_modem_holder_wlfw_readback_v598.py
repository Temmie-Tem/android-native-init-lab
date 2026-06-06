#!/usr/bin/env python3
"""V598 modem-holder WLFW QRTR nameservice registration proof.

This reuses V596's global firmware mounts, `subsys_modem`-only holder, QRTR RX
gate, and companion start-only replay. It adds only QRTR nameservice readback
for WLFW service 69 instances 0 and 1 to classify whether the post-sysmon
service registration path is visible in native init. It does not send QMI
payloads, open `esoc0`, start service-manager, start Wi-Fi HAL, write
qcwlanstate, scan, connect, run DHCP, change routes, use credentials, or ping
externally.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_modem_holder_companion_v596 as base


base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v598-modem-holder-wlfw-readback")
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v598-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v598 modem holder WLFW QRTR readback only; "
    "no QMI payload, no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_orig_companion_command = base.companion_command
_orig_run_live = base.run_live
_orig_decide = base.decide
_orig_render_summary = base.render_summary
READBACK_KEY_RE = re.compile(r"^(wifi_companion_qrtr_readback\.[A-Za-z0-9_.-]+)=(.*)$")


def _int_value(values: dict[str, str], key: str) -> int:
    try:
        return int(values.get(key, "0"), 0)
    except ValueError:
        return 0


def _readback_rows(values: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in (0, 1):
        prefix = f"wifi_companion_qrtr_readback.case_{index}"
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


def _readback_summary(values: dict[str, str]) -> dict[str, Any]:
    return {
        "allowed": values.get("wifi_companion_qrtr_readback.allowed", ""),
        "send_attempted": values.get("wifi_companion_qrtr_readback.send_attempted", ""),
        "result": values.get("wifi_companion_qrtr_readback.result", ""),
        "service_events": sum(_int_value(values, f"wifi_companion_qrtr_readback.case_{index}.readback.service_events") for index in (0, 1)),
        "timeouts": sum(_int_value(values, f"wifi_companion_qrtr_readback.case_{index}.readback.timeout") for index in (0, 1)),
        "end_of_list": sum(_int_value(values, f"wifi_companion_qrtr_readback.case_{index}.readback.end_of_list") for index in (0, 1)),
        "qmi_attempted": sum(_int_value(values, f"wifi_companion_qrtr_readback.case_{index}.qmi_attempted") for index in (0, 1)),
        "rows": _readback_rows(values),
    }


def _readback_values_from_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = READBACK_KEY_RE.match(raw_line.strip())
        if match:
            values[match.group(1)] = match.group(2).strip()
    return values


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = _orig_companion_command(args)
    if base.approved(args):
        command.append("--allow-qrtr-ns-readback")
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    result = _orig_run_live(args, store, steps, mount_preflight)
    result["qrtr_readback"] = _readback_summary(_readback_values_from_text(base.step_payload(steps, "companion-start-only-with-holder")))
    return result


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v598-wlfw-readback-plan-ready",
            True,
            "plan-only; no device command executed",
            "run current-boot V401/V490 preconditions, then V598 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return (
            "v598-wlfw-readback-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "resolve blockers before V598",
            False,
        )
    if args.command == "preflight":
        return (
            "v598-wlfw-readback-preflight-ready",
            True,
            "preflight ready; live run needs approval and uses reboot cleanup",
            "run V598 live proof",
            False,
        )

    decision, pass_ok, reason, next_step, live_executed = _orig_decide(args, checks, live)
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed
    if not pass_ok:
        return decision, pass_ok, reason, next_step, live_executed

    readback = live.get("qrtr_readback") or {}
    if int(readback.get("qmi_attempted") or 0):
        return (
            "v598-wlfw-readback-qmi-guard-failed",
            False,
            f"unexpected qmi_attempted={readback.get('qmi_attempted')}",
            "stop and inspect helper before any further Wi-Fi live action",
            live_executed,
        )
    if readback.get("send_attempted") != "1":
        return (
            "v598-wlfw-readback-not-sent",
            False,
            "WLFW QRTR readback send path did not execute",
            "inspect helper approval flag and command contract",
            live_executed,
        )
    service_events = int(readback.get("service_events") or 0)
    if service_events:
        return (
            "v598-wlfw-readback-services",
            True,
            f"WLFW QRTR nameservice returned service_events={service_events}",
            "advance to bounded qcwlanstate/HAL retry; still block scan/connect until wlan0 or FW-ready appears",
            live_executed,
        )
    if int(readback.get("end_of_list") or 0):
        return (
            "v598-wlfw-readback-empty",
            True,
            f"WLFW QRTR readback reached end-of-list; timeouts={readback.get('timeouts')}",
            "inspect missing service-notifier/WLAN-PD registration before qcwlanstate/HAL retry",
            live_executed,
        )
    return (
        "v598-wlfw-readback-timeout",
        True,
        f"WLFW QRTR readback produced no service events; timeouts={readback.get('timeouts')}",
        "inspect missing service-notifier/WLAN-PD registration before qcwlanstate/HAL retry",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _orig_render_summary(manifest).replace(
        "# V596 Modem Holder Companion Proof",
        "# V598 Modem Holder WLFW QRTR Readback Proof",
        1,
    )
    live = manifest.get("live") or {}
    readback = live.get("qrtr_readback") or {}
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
        for row in (readback.get("rows") or [])
    ]
    return "\n".join([
        text,
        "",
        "## WLFW QRTR Readback",
        "",
        f"- allowed: `{readback.get('allowed', '')}`",
        f"- send_attempted: `{readback.get('send_attempted', '')}`",
        f"- result: `{readback.get('result', '')}`",
        f"- service_events: `{readback.get('service_events', 0)}`",
        f"- timeouts: `{readback.get('timeouts', 0)}`",
        f"- end_of_list: `{readback.get('end_of_list', 0)}`",
        f"- qmi_attempted: `{readback.get('qmi_attempted', 0)}`",
        "",
        base.markdown_table(
            ["case", "service", "instance", "socket_rc", "new_lookup_rc", "del_lookup_rc", "events", "service_events", "end_of_list", "timeout", "qmi_attempted", "status"],
            rows,
        ) if rows else "- none",
    ])


base.companion_command = companion_command
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
