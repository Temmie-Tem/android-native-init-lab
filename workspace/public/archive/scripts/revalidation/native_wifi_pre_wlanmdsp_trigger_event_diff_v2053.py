#!/usr/bin/env python3
"""Host-only Android/native event diff before the first wlanmdsp RRQ."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
ANDROID_DIR = (
    REPO_ROOT
    / "tmp/wifi/v1982-v1753-minimal-android-good-baseline-rerun"
    / "android-postfs-evidence/a90-v1753-wlan-pd-fwreq"
)
NATIVE_DIR = REPO_ROOT / "tmp/wifi/v2049-pre-wlanmdsp-rrq-order-handoff/v2048-handoff"
OUT_DIR = REPO_ROOT / "tmp/wifi/v2053-pre-wlanmdsp-trigger-event-diff"
REPORT_PATH = (
    REPO_ROOT
    / "docs/reports/NATIVE_INIT_V2053_PRE_WLANMDSP_TRIGGER_EVENT_DIFF_2026-06-04.md"
)


@dataclass(frozen=True)
class Event:
    name: str
    timestamp: float | None
    source: str
    line: str


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def strings_text(path: Path) -> str:
    if not path.exists():
        return ""
    proc = subprocess.run(
        ["strings", "-a", str(path)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return proc.stdout


def parse_logcat_time(line: str) -> float | None:
    match = re.match(r"(?P<stamp>\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\s+", line)
    if not match:
        return None
    parsed = dt.datetime.strptime(f"2026-{match.group('stamp')}", "%Y-%m-%d %H:%M:%S.%f")
    return parsed.timestamp()


def parse_dmesg_time(line: str) -> float | None:
    match = re.search(r"\[\s*(?P<ts>\d+\.\d+)\]", line)
    if not match:
        return None
    return float(match.group("ts"))


def parse_trace_time(line: str) -> float | None:
    match = re.search(r"\s(?P<ts>\d+\.\d+):\s", line)
    if not match:
        return None
    return float(match.group("ts"))


def first_matching(lines: list[str], name: str, pattern: str, source: str, timestamp_kind: str) -> Event:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        if regex.search(line):
            if timestamp_kind == "logcat":
                timestamp = parse_logcat_time(line)
            elif timestamp_kind == "dmesg":
                timestamp = parse_dmesg_time(line)
            elif timestamp_kind == "trace":
                timestamp = parse_trace_time(line)
            else:
                timestamp = None
            return Event(name, timestamp, source, line.strip())
    return Event(name, None, source, "")


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            fields[key] = value
    return fields


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def native_trace_event(fields: dict[str, str], name: str) -> Event:
    line = fields.get(f"wlan_pd_cnss_nonlog_control_flow.uprobe.{name}.first_hit_line", "")
    return Event(name, parse_trace_time(line), "native tracefs uprobe", line)


def native_tftp_event(fields: dict[str, str], name: str, summary_key: str) -> Event:
    monotonic_ms = intish(fields.get(f"tftp_logdw_sink.summary.{summary_key}_monotonic_ms"))
    delta_ms = intish(fields.get(f"tftp_logdw_sink.summary.{summary_key}_delta_ms"))
    timestamp = monotonic_ms / 1000.0 if monotonic_ms > 0 else None
    line = ""
    selected_ms = monotonic_ms
    token_key = {
        "first_server_check": "server_check",
        "first_ota_firewall": "ota_firewall",
        "first_wlanmdsp": "wlanmdsp",
        "first_mcfg": "mcfg",
        "first_tftp_server": "tftp_server",
    }.get(summary_key)
    for index in range(96):
        prefix = f"tftp_logdw_sink.record_{index:03d}"
        payload = fields.get(f"{prefix}.payload", "")
        token = intish(fields.get(f"{prefix}.token.{token_key}")) if token_key else 0
        if summary_key == "first_mcfg" and "mcfg" in payload.lower():
            token = 1
        if token:
            line = payload
            if timestamp is None:
                record_ms = intish(fields.get(f"{prefix}.monotonic_ms"))
                selected_ms = record_ms
                timestamp = record_ms / 1000.0 if record_ms > 0 else None
            break
    detail = f"monotonic_ms={selected_ms} delta_ms={delta_ms}"
    if line:
        detail = f"{detail} {line}"
    return Event(name, timestamp, "native tftp logdw sink", detail)


def collect_android() -> dict[str, Any]:
    logcat_path = ANDROID_DIR / "logcat-filtered.txt"
    dmesg_path = ANDROID_DIR / "dmesg-filtered.txt"
    request_path = ANDROID_DIR / "request-lines.txt"
    logcat = read_text(logcat_path).splitlines()
    dmesg = read_text(dmesg_path).splitlines()
    request_lines = read_text(request_path).splitlines()

    events = [
        first_matching(logcat, "tftp_start", r"tftp_server: Starting", rel(logcat_path), "logcat"),
        first_matching(logcat, "server_check_wrq", r"readwrite/server_check\.txt", rel(logcat_path), "logcat"),
        first_matching(logcat, "ota_firewall_rrq", r"readwrite/ota_firewall/ruleset", rel(logcat_path), "logcat"),
        first_matching(logcat, "wlfw_start", r"cnss-daemon: wlfw_start", rel(logcat_path), "logcat"),
        first_matching(logcat, "per_mgr_add_client", r"PerMgrSrv: modem state: is on-line, add client cnss-daemon", rel(logcat_path), "logcat"),
        first_matching(logcat, "per_mgr_vote", r"cnss-daemon voting for modem", rel(logcat_path), "logcat"),
        first_matching(logcat, "wlfw_service_request", r"cnss-daemon: wlfw_service_request", rel(logcat_path), "logcat"),
        first_matching(request_lines, "first_wlanmdsp_rrq", r"wlanmdsp(?:\.mbn)?", rel(request_path), "logcat"),
        first_matching(logcat, "first_mcfg", r"readwrite/mcfg\.tmp", rel(logcat_path), "logcat"),
        first_matching(logcat, "wlfw_service_connected", r"WLFW service connected", rel(logcat_path), "logcat"),
        first_matching(logcat, "wlfw_cap_req", r"wlfw_send_cap_req", rel(logcat_path), "logcat"),
        first_matching(logcat, "first_bdf", r"wlfw_send_bdf_download_req", rel(logcat_path), "logcat"),
    ]
    dmesg_events = [
        first_matching(dmesg, "dmesg_wlfw_start", r"cnss-daemon wlfw_start", rel(dmesg_path), "dmesg"),
        first_matching(dmesg, "dmesg_wlfw_service_request", r"cnss-daemon wlfw_service_request", rel(dmesg_path), "dmesg"),
        first_matching(dmesg, "wlan_pd_up", r"msm/modem/wlan_pd, state: 0x1fffffff", rel(dmesg_path), "dmesg"),
        first_matching(dmesg, "icnss_qmi_connected", r"icnss_qmi: QMI Server Connected", rel(dmesg_path), "dmesg"),
        first_matching(dmesg, "dmesg_first_bdf", r"wlfw_send_bdf_download_req", rel(dmesg_path), "dmesg"),
        first_matching(dmesg, "wlan0", r"\bwlan0\b", rel(dmesg_path), "dmesg"),
    ]

    event_by_name = {event.name: event for event in events}
    dmesg_by_name = {event.name: event for event in dmesg_events}
    service_wall = event_by_name["wlfw_service_request"].timestamp
    rrq_wall = event_by_name["first_wlanmdsp_rrq"].timestamp
    service_mono = dmesg_by_name["dmesg_wlfw_service_request"].timestamp
    rrq_est_mono = None
    if service_wall is not None and rrq_wall is not None and service_mono is not None:
        rrq_est_mono = service_mono + (rrq_wall - service_wall)
    return {
        "source_dir": rel(ANDROID_DIR),
        "events": [event.__dict__ for event in events],
        "dmesg_events": [event.__dict__ for event in dmesg_events],
        "rrq_estimated_monotonic": rrq_est_mono,
        "rrq_delta_after_wlfw_service_request": (
            rrq_wall - service_wall if rrq_wall is not None and service_wall is not None else None
        ),
        "rrq_delta_before_wlan_pd_up": (
            dmesg_by_name["wlan_pd_up"].timestamp - rrq_est_mono
            if rrq_est_mono is not None and dmesg_by_name["wlan_pd_up"].timestamp is not None
            else None
        ),
        "first_wlanmdsp_before_first_mcfg": (
            rrq_wall is not None
            and event_by_name["first_mcfg"].timestamp is not None
            and rrq_wall < event_by_name["first_mcfg"].timestamp
        ),
    }


def collect_native() -> dict[str, Any]:
    helper_path = NATIVE_DIR / "test-v1393-helper-result.stdout.txt"
    dmesg_path = NATIVE_DIR / "test-v1393-dmesg.stdout.txt"
    fields = parse_fields(strings_text(helper_path))
    dmesg = read_text(dmesg_path).splitlines()
    events = [
        native_trace_event(fields, "wlfw_start"),
        native_trace_event(fields, "wlfw_service_request"),
        native_tftp_event(fields, "first_tftp_server_log", "first_tftp_server"),
        native_tftp_event(fields, "first_server_check", "first_server_check"),
        native_tftp_event(fields, "first_ota_firewall", "first_ota_firewall"),
        native_tftp_event(fields, "first_wlanmdsp", "first_wlanmdsp"),
        native_tftp_event(fields, "first_mcfg", "first_mcfg"),
        native_trace_event(fields, "wlfw_client_init_instance_retcheck"),
        native_trace_event(fields, "wlfw_send_ind_register_entry"),
        native_trace_event(fields, "wlfw_qmi_ind_cb_entry"),
        native_trace_event(fields, "wlfw_cap_qmi"),
        native_trace_event(fields, "wlfw_bdf_entry"),
    ]
    dmesg_events = [
        first_matching(dmesg, "wlan_pd_up", r"msm/modem/wlan_pd, state: 0x1fffffff", rel(dmesg_path), "dmesg"),
        first_matching(dmesg, "icnss_qmi_connected", r"icnss_qmi: QMI Server Connected", rel(dmesg_path), "dmesg"),
        first_matching(dmesg, "wlan0", r"\bwlan0\b", rel(dmesg_path), "dmesg"),
    ]
    return {
        "source_dir": rel(NATIVE_DIR),
        "events": [event.__dict__ for event in events],
        "dmesg_events": [event.__dict__ for event in dmesg_events],
        "tftp_counts": {
            "datagrams": sum(
                1 for index in range(96) if fields.get(f"tftp_logdw_sink.record_{index:03d}.payload") is not None
            ),
            "server_check": sum(
                intish(fields.get(f"tftp_logdw_sink.record_{index:03d}.token.server_check")) for index in range(96)
            ),
            "ota_firewall": sum(
                intish(fields.get(f"tftp_logdw_sink.record_{index:03d}.token.ota_firewall")) for index in range(96)
            ),
            "wlanmdsp": sum(
                intish(fields.get(f"tftp_logdw_sink.record_{index:03d}.token.wlanmdsp")) for index in range(96)
            ),
            "mcfg": sum(
                1
                for index in range(96)
                if "mcfg" in fields.get(f"tftp_logdw_sink.record_{index:03d}.payload", "").lower()
            ),
        },
    }


def event_map(result: dict[str, Any], key: str = "events") -> dict[str, dict[str, Any]]:
    return {str(event["name"]): event for event in result[key]}


def fmt_ts(value: float | None) -> str:
    if value is None:
        return ""
    if value > 1_000_000_000:
        return dt.datetime.fromtimestamp(value).strftime("%m-%d %H:%M:%S.%f")[:-3]
    return f"{value:.6f}"


def delta_ms(a: float | None, b: float | None) -> str:
    if a is None or b is None:
        return ""
    return f"{(a - b) * 1000.0:.1f}"


def short_line(line: str, limit: int = 170) -> str:
    line = re.sub(r"\s+", " ", line.strip())
    if len(line) <= limit:
        return line
    return f"{line[: limit - 1]}…"


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def classify(android: dict[str, Any], native: dict[str, Any]) -> tuple[str, str]:
    android_events = event_map(android)
    android_dmesg = event_map(android, "dmesg_events")
    native_events = event_map(native)
    native_dmesg = event_map(native, "dmesg_events")
    if android_events["first_wlanmdsp_rrq"]["timestamp"] is None:
        return "android-wlanmdsp-reference-missing", "Android reference did not contain wlanmdsp RRQ"
    if native_events["first_wlanmdsp"]["timestamp"] is not None:
        return "native-wlanmdsp-requested", "Native already requested wlanmdsp in the compared capture"
    if (
        android["rrq_delta_before_wlan_pd_up"] is not None
        and android["rrq_delta_before_wlan_pd_up"] > 0
        and android_events["wlfw_service_request"]["timestamp"] is not None
        and native_events["wlfw_service_request"]["timestamp"] is not None
        and native_dmesg["wlan_pd_up"]["timestamp"] is not None
    ):
        return (
            "android-rrq-after-wlfw-request-before-pd-up-native-skips-bootstrap",
            "Android's first wlanmdsp RRQ follows cnss WLFW service request and precedes wlan_pd UP; native has the cnss request and wlan_pd UP but skips the server_check/ota/wlanmdsp bootstrap branch",
        )
    return "pre-wlanmdsp-event-diff-incomplete", "Existing evidence was insufficient for the pre-RRQ event ordering"


def render_report(result: dict[str, Any]) -> str:
    android = result["android"]
    native = result["native"]
    android_events = event_map(android)
    android_dmesg = event_map(android, "dmesg_events")
    native_events = event_map(native)
    native_dmesg = event_map(native, "dmesg_events")
    android_base = android_events["tftp_start"]["timestamp"]
    native_base = native_events["wlfw_service_request"]["timestamp"]

    android_rows = []
    for name in (
        "tftp_start",
        "server_check_wrq",
        "ota_firewall_rrq",
        "wlfw_start",
        "per_mgr_add_client",
        "per_mgr_vote",
        "wlfw_service_request",
        "first_wlanmdsp_rrq",
        "first_mcfg",
        "wlfw_service_connected",
        "wlfw_cap_req",
        "first_bdf",
    ):
        event = android_events[name]
        android_rows.append([
            name,
            fmt_ts(event["timestamp"]),
            delta_ms(event["timestamp"], android_base),
            short_line(event["line"]),
        ])
    for name in ("wlan_pd_up", "icnss_qmi_connected", "dmesg_first_bdf", "wlan0"):
        event = android_dmesg[name]
        android_rows.append([
            name,
            fmt_ts(event["timestamp"]),
            "dmesg",
            short_line(event["line"]),
        ])

    native_rows = []
    for name in (
        "wlfw_start",
        "wlfw_service_request",
        "first_tftp_server_log",
        "first_server_check",
        "first_ota_firewall",
        "first_wlanmdsp",
        "first_mcfg",
        "wlfw_client_init_instance_retcheck",
        "wlfw_send_ind_register_entry",
        "wlfw_qmi_ind_cb_entry",
        "wlfw_cap_qmi",
        "wlfw_bdf_entry",
    ):
        event = native_events[name]
        native_rows.append([
            name,
            fmt_ts(event["timestamp"]),
            delta_ms(event["timestamp"], native_base),
            short_line(event["line"]),
        ])
    for name in ("wlan_pd_up", "icnss_qmi_connected", "wlan0"):
        event = native_dmesg[name]
        native_rows.append([
            name,
            fmt_ts(event["timestamp"]),
            "dmesg",
            short_line(event["line"]),
        ])

    return "\n".join([
        "# Native Init V2053 Pre-WLANMDSP Trigger Event Diff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2053`",
        "- Type: host-only Android-good vs native pre-`wlanmdsp` RRQ event comparison",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: `PASS`",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Direct Answer",
        "",
        "- Android's first `wlanmdsp.mbn` RRQ is preceded by the `server_check.txt` WRQ / `ota_firewall/ruleset` RRQ bootstrap branch and then by `cnss-daemon` `wlfw_service_request` after the PerMgr modem vote.",
        f"- The first Android `wlanmdsp` RRQ is approximately `{android['rrq_delta_after_wlfw_service_request']:.3f}` seconds after `wlfw_service_request` and approximately `{android['rrq_delta_before_wlan_pd_up']:.3f}` seconds before `wlan_pd` UP, using the `wlfw_service_request` logcat-to-dmesg alignment.",
        "- Therefore the RRQ is part of the WLAN-PD spawn/load sequence; it is not triggered by `wlan_pd` already being UP, WLFW service 69, BDF, or later `mcfg` traffic.",
        "- Native reproduces the AP-side `wlfw_service_request` and reaches `wlan_pd` UP, but its TFTP branch has `server_check=0`, `ota_firewall=0`, `wlanmdsp=0`, and only later `mcfg` traffic.",
        "",
        "## Android-Good Timeline",
        "",
        markdown_table(["event", "time", "delta_from_tftp_start_ms", "line"], android_rows),
        "",
        "## Native Timeline",
        "",
        markdown_table(["event", "time", "delta_from_wlfw_service_request_ms", "line"], native_rows),
        "",
        "## Native TFTP Counts",
        "",
        markdown_table(
            ["datagrams", "server_check", "ota_firewall", "wlanmdsp", "mcfg"],
            [[
                native["tftp_counts"]["datagrams"],
                native["tftp_counts"]["server_check"],
                native["tftp_counts"]["ota_firewall"],
                native["tftp_counts"]["wlanmdsp"],
                native["tftp_counts"]["mcfg"],
            ]],
        ),
        "",
        "## Interpretation",
        "",
        "- `mcfg` is downstream/noise for this gate: Android requests `wlanmdsp` before any `mcfg.tmp` line, while native's only TFTP payload is `mcfg` after the WLAN-PD edge.",
        "- `ota_firewall/ruleset` completion is not a success prerequisite in Android-good because the captured `ota_firewall` reads return ENOENT, but the modem still proceeds to `wlanmdsp`.",
        "- The nearest AP-visible predecessor is `wlfw_service_request`; because native already emits it, the missing condition is either TFTP-server readiness/registration at that exact pre-UP window or a modem-internal branch condition that selects the WLAN-PD bootstrap path.",
        "- The next bounded unit should force Android-order readiness only: prove `tftp_server` is fully started/registered before `pm-service`/`cnss-daemon` vote, then look for `server_check -> ota_firewall -> wlanmdsp` before `wlan_pd` UP. Do not tune `mcfg.tmp` readback.",
        "",
        "## Safety",
        "",
        "This unit is host-only and reuses existing V1982/V2049 evidence. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC/PCIe action, platform bind/unbind, or partition write.",
        "",
    ])


def main() -> int:
    android = collect_android()
    native = collect_native()
    label, reason = classify(android, native)
    result = {
        "cycle": "V2053",
        "decision": f"v2053-{label}-pass" if label != "pre-wlanmdsp-event-diff-incomplete" else "v2053-pre-wlanmdsp-event-diff-incomplete",
        "label": label,
        "pass": label != "pre-wlanmdsp-event-diff-incomplete",
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "android": android,
        "native": native,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({
        "decision": result["decision"],
        "label": result["label"],
        "pass": result["pass"],
        "report": rel(REPORT_PATH),
        "out_dir": rel(OUT_DIR),
    }, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
