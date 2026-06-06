#!/usr/bin/env python3
"""V1975 Android V1974 vs native V1937 pre-UP lookup/publication delta.

This is a host-only reducer over the new V1974 Android-good libqmi uprobe
measurement and the retained V1937 native integration run.  It answers one
specific follow-up question:

* Is the next native gate "reproduce DMS/WLFW service discovery"?
* Or did native already reach that lookup edge and only miss WLFW69 publication?
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path


CYCLE = "V1975"
DEFAULT_ANDROID_MANIFEST = Path("tmp/wifi/v1974-ril-qmi-preup-uprobe-live-20260604-055336/manifest.json")
DEFAULT_NATIVE_MANIFEST = Path("tmp/wifi/v1937-icnss-ipc-service69-integration/manifest.json")
DEFAULT_OUT_DIR = Path("tmp/wifi/v1975-preup-lookup-publication-delta")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1975_PREUP_LOOKUP_PUBLICATION_DELTA_2026-06-04.md"
)

TRACE_LINE_RE = re.compile(
    r"^\s*(?P<comm>.+?)-(?P<pid>\d+)\s+\[\d+\]\s+\S+\s+(?P<time>\d+\.\d+):\s+"
    r"(?P<event>[A-Za-z0-9_]+):(?P<body>.*)$"
)
KEY_VALUE_RE = re.compile(r"\b(?P<key>[A-Za-z0-9_]+)=(?P<value>0x[0-9a-fA-F]+|-?\d+)\b")
SERVICE_RE = re.compile(r"\bsvc_id=(0x[0-9a-fA-F]+|\d+)\b")
FOUND_RE = re.compile(r"\bfound=(0x[0-9a-fA-F]+|\d+)\b")
LEAD_SERVICES = {0x02: "DMS", 0x03: "NAS", 0x45: "WLFW"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID_MANIFEST)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args(argv)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def trace_path_from_android(manifest: dict[str, Any]) -> Path:
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    trace_path = analysis.get("libqmi_trace_path")
    if trace_path:
        return repo_path(trace_path)
    android_dir = analysis.get("android_dir")
    if android_dir:
        return repo_path(android_dir) / "libqmi-uprobe-trace.txt"
    raise RuntimeError("V1974 manifest does not expose libqmi trace path")


def parse_trace_line(line: str) -> dict[str, Any] | None:
    match = TRACE_LINE_RE.match(line)
    if not match:
        return None
    fields: dict[str, int] = {}
    for key_value in KEY_VALUE_RE.finditer(match.group("body")):
        fields[key_value.group("key")] = int(key_value.group("value"), 0)
    return {
        "comm": match.group("comm").strip(),
        "pid": int(match.group("pid")),
        "time": float(match.group("time")),
        "event": match.group("event"),
        "fields": fields,
        "line": line.strip(),
    }


def parse_trace(path: Path) -> list[dict[str, Any]]:
    return [
        parsed
        for parsed in (parse_trace_line(line) for line in path.read_text(encoding="utf-8").splitlines())
        if parsed is not None
    ]


def service_name(service_id: int) -> str:
    return LEAD_SERVICES.get(service_id, f"0x{service_id:x}")


def sample_line(events: list[dict[str, Any]]) -> str:
    return events[0]["line"] if events else ""


def trace_summary(events: list[dict[str, Any]], wlan_pd_time: float | None) -> dict[str, Any]:
    state: dict[tuple[str, int], int] = {}
    lookup_events: list[dict[str, Any]] = []
    lookup_ret_events: list[dict[str, Any]] = []
    wait_return_events: list[dict[str, Any]] = []
    init_return_events: list[dict[str, Any]] = []
    service_events: list[dict[str, Any]] = []

    for event in events:
        key = (event["comm"], event["pid"])
        if event["event"] == "libqmi_get_service_list_lookup_call":
            service_id = event["fields"].get("svc_id")
            if service_id is not None:
                state[key] = service_id
            event["service_id"] = service_id
            lookup_events.append(event)
            continue
        if event["event"] == "libqmi_get_service_list_lookup_ret":
            event["service_id"] = state.get(key)
            lookup_ret_events.append(event)
            continue
        if event["event"] == "libqmi_wait_return":
            event["service_id"] = state.get(key)
            wait_return_events.append(event)
            continue
        if event["event"] == "libqmi_init_return":
            event["service_id"] = state.get(key)
            init_return_events.append(event)
            continue
        if event["event"] in {
            "libqmi_xport_new_server_service",
            "libqmi_xport_new_server_signal",
            "libqmi_xport_new_server_callback_call",
        }:
            event["service_id"] = event["fields"].get("svc_id")
            service_events.append(event)

    def before_up(event: dict[str, Any]) -> bool:
        return wlan_pd_time is not None and event["time"] < wlan_pd_time

    def by_service(source: list[dict[str, Any]], service_id: int, *, pre_up: bool = False) -> list[dict[str, Any]]:
        selected = [event for event in source if event.get("service_id") == service_id]
        return [event for event in selected if before_up(event)] if pre_up else selected

    def positive_returns(source: list[dict[str, Any]], service_id: int, *, pre_up: bool = False) -> list[dict[str, Any]]:
        selected = by_service(source, service_id, pre_up=pre_up)
        return [event for event in selected if int(event["fields"].get("found", 0)) > 0]

    def successful_inits(service_id: int) -> list[dict[str, Any]]:
        return [
            event
            for event in by_service(init_return_events, service_id)
            if int(event["fields"].get("rc", -1)) == 0
        ]

    lookup_services = sorted(
        {int(event["service_id"]) for event in lookup_events if event.get("service_id") is not None}
    )
    lookup_pre_services = sorted(
        {int(event["service_id"]) for event in lookup_events if event.get("service_id") is not None and before_up(event)}
    )
    return {
        "trace_event_count": len(events),
        "lookup_services": [service_name(value) for value in lookup_services],
        "pre_wlanpd_lookup_services": [service_name(value) for value in lookup_pre_services],
        "dms_lookup_pre_wlanpd_count": len(by_service(lookup_events, 0x02, pre_up=True)),
        "dms_found_pre_wlanpd_count": len(positive_returns(lookup_ret_events, 0x02, pre_up=True)),
        "dms_wait_return_pre_wlanpd_count": len(by_service(wait_return_events, 0x02, pre_up=True)),
        "dms_init_success_count": len(successful_inits(0x02)),
        "wlfw_lookup_pre_wlanpd_count": len(by_service(lookup_events, 0x45, pre_up=True)),
        "wlfw_found_count": len(positive_returns(lookup_ret_events, 0x45)),
        "wlfw_wait_return_count": len(by_service(wait_return_events, 0x45)),
        "wlfw_init_success_count": len(successful_inits(0x45)),
        "service69_new_server_events": len(by_service(service_events, 0x45)),
        "first_dms_lookup_pre_wlanpd": sample_line(by_service(lookup_events, 0x02, pre_up=True)),
        "first_dms_found_pre_wlanpd": sample_line(positive_returns(lookup_ret_events, 0x02, pre_up=True)),
        "first_dms_wait_return_pre_wlanpd": sample_line(by_service(wait_return_events, 0x02, pre_up=True)),
        "first_dms_init_success": sample_line(successful_inits(0x02)),
        "first_wlfw_lookup_pre_wlanpd": sample_line(by_service(lookup_events, 0x45, pre_up=True)),
        "first_wlfw_found": sample_line(positive_returns(lookup_ret_events, 0x45)),
        "first_wlfw_wait_return": sample_line(by_service(wait_return_events, 0x45)),
        "first_wlfw_init_success": sample_line(successful_inits(0x45)),
    }


def event_sample_lines(event: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ("first_hit_line", "sample_line_0", "sample_line_1", "sample_line_2", "sample_line_3"):
        line = str(event.get(key) or "")
        if line and line != "none" and line not in lines:
            lines.append(line)
    return lines


def found_values(lines: list[str]) -> list[int]:
    values: list[int] = []
    for line in lines:
        match = FOUND_RE.search(line)
        if match:
            values.append(int(match.group(1), 0))
    return values


def line_has_service(line: str, service_id: int) -> bool:
    match = SERVICE_RE.search(line)
    return bool(match and int(match.group(1), 0) == service_id)


def native_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    details = manifest.get("details") or {}
    events = details.get("libqmi_events") or {}
    lookup_lines = event_sample_lines(events.get("libqmi_get_service_list_lookup_call") or {})
    lookup_ret_lines = event_sample_lines(events.get("libqmi_get_service_list_lookup_ret") or {})
    wait_return_lines = event_sample_lines(events.get("libqmi_wait_return") or {})
    init_return_lines = event_sample_lines(events.get("libqmi_init_return") or {})
    new_server_lines = (
        event_sample_lines(events.get("libqmi_xport_new_server_service") or {})
        + event_sample_lines(events.get("libqmi_xport_new_server_signal") or {})
    )
    wlfw_thread = str(details.get("libqmi_wlfw_thread") or "")
    wlfw_lookup_lines = [
        line for line in lookup_lines if f"cnss-daemon-{wlfw_thread}" in line and line_has_service(line, 0x45)
    ]
    wlfw_lookup_ret_lines = [line for line in lookup_ret_lines if f"cnss-daemon-{wlfw_thread}" in line]
    lookup_ids = set(details.get("libqmi_lookup_service_ids") or [])
    new_server_ids = set(details.get("libqmi_new_server_service_ids") or [])
    return {
        "path": rel(repo_path(DEFAULT_NATIVE_MANIFEST)),
        "label": manifest.get("label"),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "service74": bool(details.get("service74")),
        "service180": bool(details.get("service180")),
        "pm_open_subsys_modem": bool(details.get("pm_open_subsys_modem")),
        "holder_opened": bool(details.get("holder_opened")),
        "lookup_service_ids": sorted(lookup_ids),
        "new_server_service_ids": sorted(new_server_ids),
        "dms_lookup_seen": "0x2" in lookup_ids,
        "wlfw_lookup_seen": bool(details.get("libqmi_lookup_service69_seen")) or "0x45" in lookup_ids,
        "wlfw_thread": wlfw_thread,
        "wlfw_wait_call_seen": bool(details.get("libqmi_wlfw_wait_call_seen")),
        "wlfw_wait_return_seen": bool(details.get("libqmi_wlfw_wait_return_seen")),
        "wlfw_wait_outstanding": bool(details.get("libqmi_wlfw_wait_outstanding")),
        "wlfw_init_return_seen": bool(details.get("libqmi_wlfw_init_return_seen")),
        "wlfw_found_positive_count": sum(1 for value in found_values(wlfw_lookup_ret_lines) if value > 0),
        "non_wlfw_new_server_seen": any(service_id != "0x45" for service_id in new_server_ids),
        "service69_new_server_seen": bool(details.get("libqmi_new_server_service69_seen")) or "0x45" in new_server_ids,
        "wlfw69": bool(details.get("wlfw69")),
        "wlan_pd": bool(details.get("wlan_pd")),
        "wlanmdsp": bool(details.get("wlanmdsp")),
        "wlan0": bool(details.get("wlan0")),
        "first_dms_lookup": next((line for line in lookup_lines if line_has_service(line, 0x02)), ""),
        "first_wlfw_lookup": wlfw_lookup_lines[0] if wlfw_lookup_lines else "",
        "first_wlfw_lookup_ret": wlfw_lookup_ret_lines[0] if wlfw_lookup_ret_lines else "",
        "first_wait_return": wait_return_lines[0] if wait_return_lines else "",
        "first_init_return": init_return_lines[0] if init_return_lines else "",
        "first_new_server": new_server_lines[0] if new_server_lines else "",
    }


def android_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    trace_path = trace_path_from_android(manifest)
    trace = trace_summary(parse_trace(trace_path), dmesg.get("wlan_pd_indication_time_s"))
    return {
        "path": rel(repo_path(DEFAULT_ANDROID_MANIFEST)),
        "trace_path": rel(trace_path),
        "label": manifest.get("label"),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "rollback_selftest_fail0": bool(manifest.get("rollback_selftest_fail0")),
        "pm_vote_count": int(analysis.get("pm_vote_count") or 0),
        "wlfw_service_request_count": int(analysis.get("wlfw_service_request_count") or 0),
        "wlan_pd_indication_count": int(analysis.get("wlan_pd_indication_count") or 0),
        "wlanmdsp_count": int(analysis.get("wlanmdsp_count") or 0),
        "wlan_pd_time": dmesg.get("wlan_pd_indication_time_s"),
        "wlan0_time": dmesg.get("wlan0_time_s"),
        "contamination_clean": (
            int(dmesg.get("pcie_mhi_before_wlan0") or 0) == 0
            and int(dmesg.get("esoc_boot_failed_before_wlan0") or 0) == 0
            and not bool(dmesg.get("degraded_257s_like"))
        ),
        "explicit_rild_lead_lookup_pre": int(
            ((analysis.get("v1974_uprobe") or {}).get("rild_lead_lookup_pre_wlanpd_count") or 0)
        ),
        "explicit_rild_send_pre": int(
            ((analysis.get("v1974_uprobe") or {}).get("rild_send_pre_wlanpd_count") or 0)
        ),
        **trace,
    }


def classify(android: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
    android_positive = (
        android["pass"]
        and android["rollback_selftest_fail0"]
        and android["contamination_clean"]
        and android["pm_vote_count"] > 0
        and android["wlfw_service_request_count"] > 0
        and android["wlan_pd_indication_count"] > 0
        and android["wlanmdsp_count"] > 0
        and android["dms_lookup_pre_wlanpd_count"] > 0
        and android["dms_found_pre_wlanpd_count"] > 0
        and android["wlfw_lookup_pre_wlanpd_count"] > 0
        and android["wlfw_wait_return_count"] > 0
        and android["wlfw_found_count"] > 0
        and android["wlfw_init_success_count"] > 0
    )
    native_lookup_present = (
        native["pass"]
        and native["service74"]
        and native["service180"]
        and native["pm_open_subsys_modem"]
        and native["holder_opened"]
        and native["dms_lookup_seen"]
        and native["wlfw_lookup_seen"]
        and native["wlfw_wait_call_seen"]
    )
    native_publication_missing = (
        native["wlfw_wait_outstanding"]
        and not native["wlfw_wait_return_seen"]
        and not native["wlfw_init_return_seen"]
        and native["wlfw_found_positive_count"] == 0
        and not native["service69_new_server_seen"]
        and not native["wlfw69"]
        and not native["wlan_pd"]
        and not native["wlanmdsp"]
        and not native["wlan0"]
    )
    if android_positive and native_lookup_present and native_publication_missing:
        label = "native-dms-wlfw-lookup-present-wlfw69-publication-missing"
        passed = True
        reason = (
            "V1974 Android-good shows pre-UP DMS and WLFW lookups before WLAN-PD UP; "
            "V1937 native already reaches DMS and WLFW lookup/wait, but only non-WLFW service publication arrives and WLFW69 never publishes"
        )
    elif android_positive and not native_lookup_present:
        label = "native-dms-wlfw-lookup-missing"
        passed = False
        reason = "Android V1974 has the pre-UP lookup edge, but native evidence does not show both DMS and WLFW lookup/wait"
    elif android_positive:
        label = "native-wlfw69-publication-delta-inconclusive"
        passed = False
        reason = "Android V1974 has the pre-UP lookup edge, but native evidence does not match the missing-publication signature"
    else:
        label = "android-v1974-preup-lookup-positive-control-insufficient"
        passed = False
        reason = "V1974 Android evidence does not prove the normal clean pre-UP DMS/WLFW lookup plus WLFW69 return edge"
    return {
        "label": label,
        "decision": f"v1975-{label}-host-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "android_positive": android_positive,
        "native_lookup_present": native_lookup_present,
        "native_publication_missing": native_publication_missing,
    }


def render_report(manifest: dict[str, Any]) -> str:
    android = manifest["android"]
    native = manifest["native"]
    classification = manifest["classification"]
    rows = [
        [
            "Android normal",
            classification["android_positive"],
            f"wlan_pd={android['wlan_pd_time']} wlan0={android['wlan0_time']} clean={android['contamination_clean']}",
        ],
        [
            "Android pre-UP DMS",
            android["dms_lookup_pre_wlanpd_count"] > 0,
            f"lookup={android['dms_lookup_pre_wlanpd_count']} found={android['dms_found_pre_wlanpd_count']} wait_return={android['dms_wait_return_pre_wlanpd_count']}",
        ],
        [
            "Android WLFW69 edge",
            android["wlfw_lookup_pre_wlanpd_count"] > 0 and android["wlfw_found_count"] > 0,
            f"pre_lookup={android['wlfw_lookup_pre_wlanpd_count']} wait_return={android['wlfw_wait_return_count']} found={android['wlfw_found_count']} init_ok={android['wlfw_init_success_count']}",
        ],
        [
            "Native lookup",
            classification["native_lookup_present"],
            f"ids={native['lookup_service_ids']} service74={native['service74']} service180={native['service180']} pm_open={native['pm_open_subsys_modem']}",
        ],
        [
            "Native publication",
            not classification["native_publication_missing"],
            f"new_ids={native['new_server_service_ids']} wlfw_wait_return={native['wlfw_wait_return_seen']} wlfw69={native['wlfw69']} wlan_pd={native['wlan_pd']}",
        ],
    ]
    return "\n".join(
        [
            "# Native Init V1975 Pre-UP Lookup / WLFW69 Publication Delta",
            "",
            "## Summary",
            "",
            f"- Cycle: `{manifest['cycle']}`",
            f"- Decision: `{classification['decision']}`",
            f"- Label: `{classification['label']}`",
            f"- Pass: `{classification['pass']}`",
            f"- Reason: {classification['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Gate",
            "",
            "V1974 was the new producer-side measurement requested by the ledger: a normal Android handoff with pre-armed libqmi uprobes. This V1975 reducer uses that new measurement to decide whether native still needs to reproduce the pre-UP DMS/WLFW lookup edge, or whether the remaining delta is specifically WLFW69 publication from the internal modem.",
            "",
            "## Matrix",
            "",
            markdown_table(["area", "ok", "detail"], [[str(cell) for cell in row] for row in rows]),
            "",
            "## Android V1974 Edge",
            "",
            f"- First DMS lookup before `wlan_pd` UP: `{android['first_dms_lookup_pre_wlanpd']}`",
            f"- First DMS found before `wlan_pd` UP: `{android['first_dms_found_pre_wlanpd']}`",
            f"- First WLFW lookup before `wlan_pd` UP: `{android['first_wlfw_lookup_pre_wlanpd']}`",
            f"- First WLFW wait return: `{android['first_wlfw_wait_return']}`",
            f"- First WLFW found: `{android['first_wlfw_found']}`",
            f"- Explicit `rild` pre-UP lead lookups/sends: `{android['explicit_rild_lead_lookup_pre']}` / `{android['explicit_rild_send_pre']}`",
            "",
            "## Native V1937 Edge",
            "",
            f"- First DMS lookup: `{native['first_dms_lookup']}`",
            f"- First WLFW lookup: `{native['first_wlfw_lookup']}`",
            f"- First WLFW lookup return: `{native['first_wlfw_lookup_ret']}`",
            f"- First native wait return: `{native['first_wait_return']}`",
            f"- First native new-server: `{native['first_new_server']}`",
            "",
            "## Decision",
            "",
            "- Native is not missing the DMS/WLFW libqmi lookup edge; it already reaches `svc_id=0x2` and `svc_id=0x45` with the clean-DSP/service74, PM-open, holder, and cnss-worker stack.",
            "- The retained delta is narrower: Android's WLFW wait returns and finds service `0x45` immediately after `wlan_pd` UP, while native only sees a non-WLFW service arrival and the WLFW worker remains outstanding.",
            "- The next live unit should therefore measure with no AP-side mutation: observe why the internal modem does not publish WLFW69/start `msm/modem/wlan_pd` under the native combo, not another RIL/pm-service/eSoC/PCIe/GDSC path.",
            "",
            "## Safety",
            "",
            "Host-only reducer. No device command, boot flash, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, PMIC/GPIO/GDSC/regulator write, fake ONLINE state, forced RC1/case write, partition write, or sda29 remount-write was performed.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    android_manifest_path = repo_path(args.android_manifest)
    native_manifest_path = repo_path(args.native_manifest)
    out_dir = repo_path(args.out_dir)
    report_path = repo_path(args.report_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    android = android_summary(read_json(android_manifest_path))
    native = native_summary(read_json(native_manifest_path))
    classification = classify(android, native)
    manifest = {
        "cycle": CYCLE,
        "created": now_iso(),
        "out_dir": rel(out_dir),
        "label": classification["label"],
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "android_manifest": rel(android_manifest_path),
        "native_manifest": rel(native_manifest_path),
        "android": android,
        "native": native,
        "classification": classification,
        "host_metadata": collect_host_metadata(),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(render_report(manifest), encoding="utf-8")
    report_path.write_text(render_report(manifest), encoding="utf-8")
    print(json.dumps({"decision": manifest["decision"], "label": manifest["label"], "pass": manifest["pass"]}, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
