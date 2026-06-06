#!/usr/bin/env python3
"""V1935 Android/native WLFW service69 wait-return diff.

Host-only classifier.  It compares:

* Android-good V1934: WLFW service 0x45 lookup waits, returns, then a
  service-list lookup finds service69 and `qmi_client_init_instance` returns.
* Native V1930: WLFW service 0x45 lookup occurs, but the WLFW thread remains
  blocked in libqmi wait while WLAN-PD/WLFW69/wlanmdsp/wlan0 stay absent.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1935"
DEFAULT_NATIVE_MANIFEST = Path("tmp/wifi/v1930-libqmi-service-id-integration/manifest.json")
DEFAULT_ANDROID_MANIFEST = Path(
    "tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/manifest.json"
)
DEFAULT_OUT_DIR = Path("tmp/wifi/v1935-android-native-service69-wait-return-diff")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1935_ANDROID_NATIVE_SERVICE69_WAIT_RETURN_DIFF_2026-06-04.md"
)
SERVICE_RE = re.compile(r"\bsvc_id=(0x[0-9a-fA-F]+|\d+)\b")
FOUND_RE = re.compile(r"\bfound=(0x[0-9a-fA-F]+|\d+)\b")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE_MANIFEST)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args(argv)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def event_sample_lines(event: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ("first_hit_line", "sample_line_0", "sample_line_1", "sample_line_2", "sample_line_3"):
        value = str(event.get(key) or "")
        if value and value != "none" and value not in lines:
            lines.append(value)
    return lines


def service_ids_from_lines(lines: list[str]) -> list[str]:
    values: set[int] = set()
    for line in lines:
        match = SERVICE_RE.search(line)
        if match:
            values.add(int(match.group(1), 0))
    return [f"0x{value:x}" for value in sorted(values)]


def found_values_from_lines(lines: list[str]) -> list[int]:
    values: list[int] = []
    for line in lines:
        match = FOUND_RE.search(line)
        if match:
            values.append(int(match.group(1), 0))
    return values


def native_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    details = manifest.get("details") or {}
    events = details.get("libqmi_events") or {}
    lookup_lines = event_sample_lines(events.get("libqmi_get_service_list_lookup_call") or {})
    lookup_ret_lines = event_sample_lines(events.get("libqmi_get_service_list_lookup_ret") or {})
    wait_return_lines = event_sample_lines(events.get("libqmi_wait_return") or {})
    init_return_lines = event_sample_lines(events.get("libqmi_init_return") or {})
    wlfw_thread = str(details.get("libqmi_wlfw_thread") or "")
    wlfw_lookup_lines = [line for line in lookup_lines if f"cnss-daemon-{wlfw_thread}" in line and "svc_id=0x45" in line]
    wlfw_lookup_ret_lines = [line for line in lookup_ret_lines if f"cnss-daemon-{wlfw_thread}" in line]
    wlfw_found_values = found_values_from_lines(wlfw_lookup_ret_lines)
    wlfw_wait_return_lines = [line for line in wait_return_lines if f"cnss-daemon-{wlfw_thread}" in line]
    wlfw_init_return_lines = [line for line in init_return_lines if f"cnss-daemon-{wlfw_thread}" in line]
    return {
        "path": rel(repo_path(DEFAULT_NATIVE_MANIFEST)),
        "label": manifest.get("label"),
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "wlfw_thread": wlfw_thread,
        "combined_prereqs": bool(details.get("service74") and details.get("pm_open_subsys_modem") and details.get("holder_opened")),
        "wlfw69": bool(details.get("wlfw69")),
        "wlan_pd": bool(details.get("wlan_pd")),
        "wlanmdsp": bool(details.get("wlanmdsp")),
        "wlan0": bool(details.get("wlan0")),
        "lookup_service_ids": details.get("libqmi_lookup_service_ids") or service_ids_from_lines(lookup_lines),
        "new_server_service_ids": details.get("libqmi_new_server_service_ids") or [],
        "lookup69_seen": bool(details.get("libqmi_lookup_service69_seen")),
        "wait_call_seen": bool(details.get("libqmi_wlfw_wait_call_seen")),
        "wait_return_seen": bool(details.get("libqmi_wlfw_wait_return_seen")),
        "init_return_seen": bool(details.get("libqmi_wlfw_init_return_seen")),
        "wait_outstanding": bool(details.get("libqmi_wlfw_wait_outstanding")),
        "found_positive_count": sum(1 for value in wlfw_found_values if value > 0),
        "first_lookup69": wlfw_lookup_lines[0] if wlfw_lookup_lines else "",
        "first_lookup_ret": wlfw_lookup_ret_lines[0] if wlfw_lookup_ret_lines else "",
        "first_wait_return": wlfw_wait_return_lines[0] if wlfw_wait_return_lines else "",
        "first_init_return": wlfw_init_return_lines[0] if wlfw_init_return_lines else "",
    }


def android_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = (manifest.get("context") or {}).get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    return {
        "path": rel(repo_path(DEFAULT_ANDROID_MANIFEST)),
        "label": manifest.get("label"),
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "rollback_selftest_fail0": bool(manifest.get("rollback_selftest_fail0")),
        "normal_stateup": bool(
            int(analysis.get("pm_vote_count") or 0) > 0
            and int(analysis.get("wlfw_service_request_count") or 0) > 0
            and int(analysis.get("wlan_pd_indication_count") or 0) > 0
            and int(analysis.get("wlanmdsp_count") or 0) > 0
            and dmesg.get("wlan0_time_s") is not None
        ),
        "contamination_clean": (
            int(dmesg.get("pcie_mhi_before_wlan0") or 0) == 0
            and int(dmesg.get("esoc_boot_failed_before_wlan0") or 0) == 0
            and not bool(dmesg.get("degraded_257s_like"))
        ),
        "wlan0_time_s": dmesg.get("wlan0_time_s"),
        "wlan_pd_indication_time_s": dmesg.get("wlan_pd_indication_time_s"),
        "lookup_service_ids": analysis.get("libqmi_lookup_service_ids") or [],
        "new_server_service_ids": analysis.get("libqmi_new_server_service_ids") or [],
        "lookup69_seen": bool(analysis.get("libqmi_lookup_service69_seen")),
        "new_server69_seen": bool(analysis.get("libqmi_new_server_service69_seen")),
        "found_positive_count": int(analysis.get("libqmi_service69_found_count") or 0),
        "wait_return_count": int(analysis.get("libqmi_service69_wait_return_count") or 0),
        "init_return_count": int(analysis.get("libqmi_service69_init_return_count") or 0),
        "service69_threads": analysis.get("libqmi_service69_threads") or [],
        "first_lookup69": analysis.get("libqmi_first_service69_lookup") or "",
        "first_found": analysis.get("libqmi_first_service69_found") or "",
        "first_wait_return": analysis.get("libqmi_first_service69_wait_return") or "",
        "first_init_return": analysis.get("libqmi_first_service69_init_return") or "",
    }


def classify(native: dict[str, Any], android: dict[str, Any]) -> dict[str, Any]:
    android_positive = (
        android["normal_stateup"]
        and android["contamination_clean"]
        and android["lookup69_seen"]
        and android["found_positive_count"] > 0
        and android["wait_return_count"] > 0
        and android["init_return_count"] > 0
    )
    native_missing = (
        native["combined_prereqs"]
        and native["lookup69_seen"]
        and native["wait_call_seen"]
        and native["wait_outstanding"]
        and not native["wait_return_seen"]
        and not native["init_return_seen"]
        and native["found_positive_count"] == 0
        and not native["wlfw69"]
        and not native["wlan_pd"]
        and not native["wlanmdsp"]
        and not native["wlan0"]
    )
    if android_positive and native_missing:
        label = "native-wlfw-service69-wait-return-missing"
        passed = True
        reason = (
            "Android-good proves WLFW service69 wait-return/found-service/init-return in the clean internal-modem boot, "
            "while native reaches the same WLFW lookup and wait call but never receives the service69 wait return"
        )
    elif android_positive:
        label = "native-service69-wait-diff-inconclusive"
        passed = False
        reason = "Android-good positive edge is present, but native evidence no longer matches the missing wait-return signature"
    else:
        label = "android-service69-positive-control-insufficient"
        passed = False
        reason = "Android-good evidence does not prove the service69 wait-return positive edge"
    return {
        "label": label,
        "decision": f"v1935-{label}-host-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "android_positive": android_positive,
        "native_missing": native_missing,
    }


def render_report(manifest: dict[str, Any]) -> str:
    native = manifest["native"]
    android = manifest["android"]
    classification = manifest["classification"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        [
            "Android normal",
            android["normal_stateup"],
            f"wlan_pd={android['wlan_pd_indication_time_s']} wlan0={android['wlan0_time_s']} clean={android['contamination_clean']}",
        ],
        [
            "Android service69",
            f"{android['lookup69_seen']}/{android['found_positive_count']}/{android['wait_return_count']}/{android['init_return_count']}",
            f"threads={android['service69_threads']} new69={android['new_server69_seen']}",
        ],
        [
            "Native prereq",
            native["combined_prereqs"],
            f"lookup69={native['lookup69_seen']} wait_call={native['wait_call_seen']} thread={native['wlfw_thread']}",
        ],
        [
            "Native missing",
            native["wait_outstanding"],
            f"found={native['found_positive_count']} wait_return={native['wait_return_seen']} init_return={native['init_return_seen']} wlan_pd={native['wlan_pd']} wlanmdsp={native['wlanmdsp']} wlan0={native['wlan0']}",
        ],
    ]
    edge_rows = [
        ["Android first lookup69", android["first_lookup69"]],
        ["Android first wait return", android["first_wait_return"]],
        ["Android first found", android["first_found"]],
        ["Android first init return", android["first_init_return"]],
        ["Native first lookup69", native["first_lookup69"]],
        ["Native first lookup ret", native["first_lookup_ret"]],
        ["Native first wait return", native["first_wait_return"] or "none"],
        ["Native first init return", native["first_init_return"] or "none"],
    ]
    return "\n".join(
        [
            "# Native Init V1935 Android/Native Service69 Wait-return Diff",
            "",
            "## Summary",
            "",
            f"- Cycle: `{CYCLE}`",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Matrix",
            "",
            markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in matrix_rows]),
            "",
            "## Edge Lines",
            "",
            markdown_table(["edge", "line"], edge_rows),
            "",
            "## Interpretation",
            "",
            "- V1934 changes the comparison target: the reliable Android-positive signal is not decoded `new-server69`; it is the WLFW thread's service69 wait returning, followed by `found=0x1` service-list lookup and `qmi_client_init_instance` return.",
            "- Native V1930 reaches the same WLFW service69 lookup/wait call, but the WLFW thread stays outstanding with `found=0`, no wait return, no init return, and no WLAN-PD/WLFW69/wlanmdsp/wlan0.",
            "- The next live native unit should instrument the remote SERVREG/WLAN-PD state-up to WLFW service69 wait-return edge. Do not pivot to pm-service msg22, SDX50M/eSoC/PCIe/GDSC, or Wi-Fi HAL/connect.",
            "",
            "## Inputs",
            "",
            f"- Android: `{android['path']}`",
            f"- Native: `{native['path']}`",
            "",
            "## Safety Scope",
            "",
            "Host-only manifest diff. No live device command, flash, reboot, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("host")
    native_manifest = read_json(args.native_manifest)
    android_manifest = read_json(args.android_manifest)
    native = native_summary(native_manifest)
    native["path"] = rel(repo_path(args.native_manifest))
    android = android_summary(android_manifest)
    android["path"] = rel(repo_path(args.android_manifest))
    classification = classify(native, android)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(repo_path(args.out_dir)),
        "label": classification["label"],
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "classification": classification,
        "android": android,
        "native": native,
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    report = render_report(manifest)
    store.write_text("summary.md", report)
    report_path = repo_path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(
        f"{'PASS' if manifest['pass'] else 'FAIL'} "
        f"label={manifest['label']} out_dir={manifest['out_dir']}"
    )
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
