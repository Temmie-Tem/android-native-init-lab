#!/usr/bin/env python3
"""V1931 host-only Android service-notifier vs native libqmi service69 diff."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path

CYCLE = "V1931"
DEFAULT_ANDROID_SERVNOTIF = repo_path(
    "tmp/wifi/v1912-android-service-notifier-symbol-owner-handoff-live-20260603-220803/manifest.json"
)
DEFAULT_ANDROID_SERVLOC = repo_path(
    "tmp/wifi/v1909-android-servloc-domain-handoff-live-20260603-213346/manifest.json"
)
DEFAULT_NATIVE = repo_path("tmp/wifi/v1930-libqmi-service-id-integration/manifest.json")
DEFAULT_OUT_DIR = repo_path("tmp/wifi/v1931-android-servnotif-native-libqmi69-diff")
DEFAULT_REPORT = repo_path(
    "docs/reports/NATIVE_INIT_V1931_ANDROID_SERVNOTIF_NATIVE_LIBQMI69_DIFF_2026-06-04.md"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: Any) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "ok"}


def android_servnotif_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = manifest.get("context", {}).get("analysis", {})
    return {
        "path": rel(DEFAULT_ANDROID_SERVNOTIF),
        "label": manifest.get("label", ""),
        "decision": manifest.get("decision", ""),
        "service180_count": intish(analysis.get("service180_count")),
        "service74_count": intish(analysis.get("service74_count")),
        "wlan_pd_indication_count": intish(analysis.get("wlan_pd_indication_count")),
        "wlanmdsp_count": intish(analysis.get("wlanmdsp_count")),
        "wlfw_service_request_count": intish(analysis.get("wlfw_service_request_count")),
        "first_service180_line": analysis.get("first_service180_line", ""),
        "first_service74_line": analysis.get("first_service74_line", ""),
        "first_wlan_pd_line": analysis.get("first_wlan_pd_line", ""),
        "first_wlanmdsp_line": analysis.get("first_wlanmdsp_line", ""),
        "service_notifier_owner": ",".join(analysis.get("service_notif_register_notifier_owners") or []),
        "sys_modules": analysis.get("sys_modules") or [],
    }


def android_servloc_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = manifest.get("context", {}).get("analysis", {})
    dmesg = analysis.get("dmesg", {})
    return {
        "path": rel(DEFAULT_ANDROID_SERVLOC),
        "label": manifest.get("label", ""),
        "decision": manifest.get("decision", ""),
        "query_domain180_seen": boolish(analysis.get("query_domain180_seen")),
        "query_domain74_seen": boolish(analysis.get("query_domain74_seen")),
        "query_instances": analysis.get("query_instances") or [],
        "query_names": analysis.get("query_names") or [],
        "query_success_count": intish(analysis.get("query_success_count")),
        "service180_count": intish(analysis.get("service180_count")),
        "service74_count": intish(analysis.get("service74_count")),
        "wlan_pd_indication_count": intish(analysis.get("wlan_pd_indication_count")),
        "wlanmdsp_count": intish(analysis.get("wlanmdsp_count")),
        "wlan0_time_s": dmesg.get("wlan0_time_s"),
        "degraded_257s_like": boolish(dmesg.get("degraded_257s_like")),
        "pcie_mhi_before_wlan0": intish(dmesg.get("pcie_mhi_before_wlan0")),
        "esoc_boot_failed_before_wlan0": intish(dmesg.get("esoc_boot_failed_before_wlan0")),
        "first_service180_line": analysis.get("first_service180_line", ""),
        "first_service74_line": analysis.get("first_service74_line", ""),
        "first_wlan_pd_line": analysis.get("first_wlan_pd_line", ""),
        "first_wlanmdsp_line": analysis.get("first_wlanmdsp_line", ""),
    }


def native_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    details = manifest.get("details", {})
    return {
        "path": rel(DEFAULT_NATIVE),
        "label": manifest.get("label", ""),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "service74": boolish(details.get("service74")),
        "service180": boolish(details.get("service180")),
        "servnotif_late_state": details.get("servnotif_late_state", ""),
        "servnotif_late_indication": intish(details.get("servnotif_late_indication")),
        "servloc_result": details.get("servloc_result", ""),
        "servloc_domain": details.get("servloc_domain", ""),
        "servloc_instance": str(details.get("servloc_instance", "")),
        "libqmi_lookup_service_ids": details.get("libqmi_lookup_service_ids") or [],
        "libqmi_new_server_service_ids": details.get("libqmi_new_server_service_ids") or [],
        "libqmi_lookup_service69_seen": boolish(details.get("libqmi_lookup_service69_seen")),
        "libqmi_new_server_service69_seen": boolish(details.get("libqmi_new_server_service69_seen")),
        "qrtr69_case0_events": intish(details.get("qrtr69_case0_events")),
        "qrtr69_case1_events": intish(details.get("qrtr69_case1_events")),
        "wlfw69": boolish(details.get("wlfw69")),
        "wlan_pd": boolish(details.get("wlan_pd")),
        "wlanmdsp": boolish(details.get("wlanmdsp")),
        "wlan0": boolish(details.get("wlan0")),
        "wlfw_thread": str(details.get("libqmi_wlfw_thread", "")),
        "wlfw_wait_outstanding": boolish(details.get("libqmi_wlfw_wait_outstanding")),
        "first_service69_lookup": details.get("libqmi_events", {}).get("libqmi_get_service_list_lookup_call", {}).get("first_hit_line", ""),
        "first_new_server_service": details.get("libqmi_events", {}).get("libqmi_xport_new_server_service", {}).get("first_hit_line", ""),
    }


def classify(android_sn: dict[str, Any], android_sl: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
    android_normal = (
        android_sn["service180_count"] > 0
        and android_sn["service74_count"] > 0
        and android_sn["wlan_pd_indication_count"] > 0
        and android_sn["wlanmdsp_count"] > 0
        and android_sl["query_domain180_seen"]
        and not android_sl["degraded_257s_like"]
        and android_sl["pcie_mhi_before_wlan0"] == 0
    )
    native_reaches_lookup = (
        native["service74"]
        and native["service180"]
        and native["servloc_result"] == "domain-list-response-success"
        and native["servloc_instance"] == "180"
        and native["libqmi_lookup_service69_seen"]
    )
    native_missing_publication = (
        not native["libqmi_new_server_service69_seen"]
        and native["qrtr69_case0_events"] == 0
        and native["qrtr69_case1_events"] == 0
        and not native["wlfw69"]
        and not native["wlan_pd"]
        and not native["wlanmdsp"]
        and not native["wlan0"]
    )
    if android_normal and native_reaches_lookup and native_missing_publication:
        return {
            "label": "android-servnotif-stateup-native-libqmi69-publication-missing",
            "pass": True,
            "reason": "Android normal publishes service-notifier 180/74 and reaches WLAN-PD, while native reaches service69 lookup but never gets service69/QRTR69 publication",
            "android_normal": android_normal,
            "native_reaches_lookup": native_reaches_lookup,
            "native_missing_publication": native_missing_publication,
        }
    return {
        "label": "servnotif-libqmi69-diff-incomplete",
        "pass": False,
        "reason": "host-only evidence did not cover the Android normal publication and native missing-publication sides simultaneously",
        "android_normal": android_normal,
        "native_reaches_lookup": native_reaches_lookup,
        "native_missing_publication": native_missing_publication,
    }


def render_report(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    android_sn = manifest["android_servnotif"]
    android_sl = manifest["android_servloc"]
    native = manifest["native"]
    matrix = [
        ["label", c["label"], c["reason"]],
        ["android_stateup", c["android_normal"], f"service180={android_sn['service180_count']} service74={android_sn['service74_count']} wlan_pd={android_sn['wlan_pd_indication_count']} wlanmdsp={android_sn['wlanmdsp_count']}"],
        ["android_servloc", android_sl["query_domain180_seen"], f"instances={android_sl['query_instances']} names={android_sl['query_names']} degraded={android_sl['degraded_257s_like']} pcie_mhi_before_wlan0={android_sl['pcie_mhi_before_wlan0']}"],
        ["native_lookup", c["native_reaches_lookup"], f"service74={native['service74']} service180={native['service180']} servloc={native['servloc_result']}:{native['servloc_instance']} lookup_ids={native['libqmi_lookup_service_ids']}"],
        ["native_publication", not c["native_missing_publication"], f"new_server_ids={native['libqmi_new_server_service_ids']} new69={native['libqmi_new_server_service69_seen']} qrtr69={native['qrtr69_case0_events']},{native['qrtr69_case1_events']} wlan_pd={native['wlan_pd']} wlanmdsp={native['wlanmdsp']} wlan0={native['wlan0']}"],
    ]
    return "\n".join([
        "# Native Init V1931 Android Servnotif vs Native Libqmi69 Diff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{manifest['cycle']}`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{c['label']}`",
        f"- Pass: `{c['pass']}`",
        f"- Reason: {c['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Matrix",
        "",
        markdown_table(["area", "value", "detail"], [[str(v) for v in row] for row in matrix]),
        "",
        "## Android Normal Edge",
        "",
        f"- Service-notifier 180: `{android_sn['first_service180_line']}`",
        f"- Service-notifier 74: `{android_sn['first_service74_line']}`",
        f"- WLAN-PD indication: `{android_sn['first_wlan_pd_line']}`",
        f"- First wlanmdsp: `{android_sn['first_wlanmdsp_line']}`",
        f"- `service_notif_register_notifier` owner: `{android_sn['service_notifier_owner']}`",
        "",
        "## Native Missing Edge",
        "",
        f"- First service69 lookup: `{native['first_service69_lookup']}`",
        f"- First non-WLFW new-server: `{native['first_new_server_service']}`",
        f"- Native service IDs: lookup `{native['libqmi_lookup_service_ids']}`, new-server `{native['libqmi_new_server_service_ids']}`",
        f"- Native servnotif state/indication: `{native['servnotif_late_state']}` / `{native['servnotif_late_indication']}`",
        "",
        "## Decision",
        "",
        "- This closes the retained-host comparison: Android normal has the built-in service-notifier publication path; native reaches the WLFW service69 lookup but lacks the corresponding service69/QRTR69 publication.",
        "- The next useful unit is a read-only source/caller observer for who emits the Android service-notifier 180 -> WLAN-PD publication edge, not another pm-service/msg22 or eSoC/PCIe/GDSC path.",
        "- Do not attempt Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until native exposes service69/WLAN-PD and `wlan0`.",
        "",
        "## Safety",
        "",
        "- Host-only reparse of retained Android and native manifests; no boot, flash, device write, Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping, `/dev/subsys_esoc0`, PCIe/MHI/eSoC, PMIC/GPIO/GDSC/regulator action, forced RC1/case, or platform bind/unbind was used.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-servnotif", type=Path, default=DEFAULT_ANDROID_SERVNOTIF)
    parser.add_argument("--android-servloc", type=Path, default=DEFAULT_ANDROID_SERVLOC)
    parser.add_argument("--native", type=Path, default=DEFAULT_NATIVE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    android_sn = android_servnotif_summary(load_json(args.android_servnotif))
    android_sl = android_servloc_summary(load_json(args.android_servloc))
    native = native_summary(load_json(args.native))
    classification = classify(android_sn, android_sl, native)
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(out_dir),
        "decision": f"v1931-{classification['label']}-host-{'pass' if classification['pass'] else 'blocked'}",
        "pass": classification["pass"],
        "classification": classification,
        "android_servnotif": android_sn,
        "android_servloc": android_sl,
        "native": native,
        "inputs": {
            "android_servnotif": rel(args.android_servnotif),
            "android_servloc": rel(args.android_servloc),
            "native": rel(args.native),
        },
        "host_metadata": collect_host_metadata(),
    }
    report = render_report(manifest)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(report, encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"{'PASS' if classification['pass'] else 'BLOCKED'} label={classification['label']} out_dir={rel(out_dir)}")
    return 0 if classification["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
