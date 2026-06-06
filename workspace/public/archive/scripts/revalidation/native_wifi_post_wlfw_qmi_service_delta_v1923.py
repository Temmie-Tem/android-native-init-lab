#!/usr/bin/env python3
"""V1923 host-only post-WLFW QMI service delta classifier."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore

import native_wifi_post_wlfw_qmi_wait_classifier_v1922 as prev1922


CYCLE = "V1923"
OUT_DIR = repo_path("tmp/wifi/v1923-post-wlfw-qmi-service-delta")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1923_POST_WLFW_QMI_SERVICE_DELTA_2026-06-04.md")
V1919_MANIFEST = repo_path("tmp/wifi/v1919-modem-jsn-rfs-gate/manifest.json")
V1922_MANIFEST = repo_path("tmp/wifi/v1922-post-wlfw-qmi-wait/manifest.json")
NATIVE_V1920_HELPER = repo_path("tmp/wifi/v1920-clean-dsp-pm-open-integration/v1847-handoff/test-v1393-helper-result.stdout.txt")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": rel(path), "invalid": str(exc)}
    return data if isinstance(data, dict) else {"exists": True, "path": rel(path), "invalid": "not-object"}


def intish(value: object) -> int:
    return prev1922.intish(value)


def boolish(value: object) -> bool:
    return prev1922.boolish(value)


def helper_hit(fields: dict[str, str], name: str) -> int:
    return prev1922.helper_hit(fields, name)


def helper_line(fields: dict[str, str], name: str) -> str:
    return prev1922.helper_first_line(fields, name)


def helper_time(fields: dict[str, str], name: str) -> float | None:
    return prev1922.helper_first_time(fields, name)


def android_marker(android: dict[str, Any], source: str, marker: str) -> dict[str, Any]:
    section = android.get("dmesg", {}).get(source, {})
    markers = section.get("markers") if isinstance(section.get("markers"), dict) else {}
    marker_data = markers.get(marker, {})
    return marker_data if isinstance(marker_data, dict) else {}


def delta_ms(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return round((end - start) * 1000.0, 3)


def qrtr_absent(fields: dict[str, str], index: int) -> bool:
    prefix = f"wifi_companion_qrtr_readback.case_{index}.readback."
    return (
        intish(fields.get(prefix + "service_events")) == 0
        and intish(fields.get(prefix + "empty_events")) > 0
        and intish(fields.get(prefix + "end_of_list")) > 0
        and intish(fields.get(prefix + "timeout")) == 0
        and fields.get(f"wifi_companion_qrtr_readback.case_{index}.status") == "complete"
    )


def build_native_details(native: dict[str, Any], fields: dict[str, str]) -> dict[str, Any]:
    return {
        "service74": native.get("service74"),
        "service180": native.get("service180"),
        "pm_open_subsys_modem": native.get("pm_open_subsys_modem"),
        "holder_opened": native.get("holder_opened"),
        "holder_started": native.get("holder_started"),
        "holder_postflight_safe": native.get("holder_postflight_safe"),
        "holder_fd": native.get("holder_fd"),
        "order": native.get("order"),
        "servloc_result": fields.get("wifi_companion_servloc_domain_list.result", ""),
        "servloc_domain_count": fields.get("wifi_companion_servloc_domain_list.domain_count", ""),
        "servloc_wlan_domain": fields.get("wifi_companion_servloc_domain_list.domain.0.name", ""),
        "servloc_wlan_instance": fields.get("wifi_companion_servloc_domain_list.domain.0.instance_id", ""),
        "servnotif_late_state": fields.get("wifi_companion_service_notifier_late_listener.response_curr_state_name", ""),
        "servnotif_late_indication": fields.get("wifi_companion_service_notifier_late_listener.indication_seen", ""),
        "servnotif_late_hold_ms": fields.get("wifi_companion_service_notifier_late_listener.timing.hold_ms", ""),
        "qrtr_case_0_absent": qrtr_absent(fields, 0),
        "qrtr_case_1_absent": qrtr_absent(fields, 1),
        "qrtr_case_0_service_events": fields.get("wifi_companion_qrtr_readback.case_0.readback.service_events", ""),
        "qrtr_case_1_service_events": fields.get("wifi_companion_qrtr_readback.case_1.readback.service_events", ""),
        "wlfw_start_hit": helper_hit(fields, "wlfw_start"),
        "dms_service_request_hit": helper_hit(fields, "dms_service_request"),
        "wlfw_service_request_hit": helper_hit(fields, "wlfw_service_request"),
        "wlfw_worker_success_hit": helper_hit(fields, "wlfw_worker_pthread_create_success"),
        "wlfw_ind_register_hit": helper_hit(fields, "wlfw_ind_register_qmi"),
        "wlfw_cap_hit": helper_hit(fields, "wlfw_cap_qmi"),
        "wlfw_start_time": helper_time(fields, "wlfw_start"),
        "dms_service_request_time": helper_time(fields, "dms_service_request"),
        "wlfw_service_request_time": helper_time(fields, "wlfw_service_request"),
        "wlfw_worker_success_time": helper_time(fields, "wlfw_worker_pthread_create_success"),
        "wlfw_ind_register_time": helper_time(fields, "wlfw_ind_register_qmi"),
        "wlfw_cap_time": helper_time(fields, "wlfw_cap_qmi"),
        "wlfw_start_line": helper_line(fields, "wlfw_start"),
        "dms_service_request_line": helper_line(fields, "dms_service_request"),
        "wlfw_service_request_line": helper_line(fields, "wlfw_service_request"),
        "wlfw_worker_success_line": helper_line(fields, "wlfw_worker_pthread_create_success"),
        "wlfw_ind_register_line": helper_line(fields, "wlfw_ind_register_qmi"),
        "wlfw_cap_line": helper_line(fields, "wlfw_cap_qmi"),
        "wlfw69": native.get("wlfw69"),
        "wlan_pd": native.get("wlan_pd"),
        "wlanmdsp": native.get("wlanmdsp"),
        "wlan0": native.get("wlan0"),
        "wlfw_nonlog_label": native.get("wlfw_nonlog_label"),
    }


def build_android_details(android: dict[str, Any]) -> dict[str, Any]:
    sources: dict[str, Any] = {}
    for name in ("v1899", "v1909"):
        wlfw_request = android_marker(android, name, "wlfw_request")
        wlan_pd = android_marker(android, name, "wlan_pd")
        qmi_server = android_marker(android, name, "qmi_server")
        fw_ready = android_marker(android, name, "fw_ready")
        wlan0 = android_marker(android, name, "wlan0")
        sources[name] = {
            "path": android.get("dmesg", {}).get(name, {}).get("path", ""),
            "service74_time": android_marker(android, name, "service74").get("time"),
            "service180_time": android_marker(android, name, "service180").get("time"),
            "wlfw_start_time": android_marker(android, name, "wlfw_start").get("time"),
            "wlfw_request_time": wlfw_request.get("time"),
            "wlan_pd_time": wlan_pd.get("time"),
            "qmi_server_time": qmi_server.get("time"),
            "fw_ready_time": fw_ready.get("time"),
            "wlan0_time": wlan0.get("time"),
            "wlfw_to_wlan_pd_ms": delta_ms(wlfw_request.get("time"), wlan_pd.get("time")),
            "wlan_pd_to_qmi_server_ms": delta_ms(wlan_pd.get("time"), qmi_server.get("time")),
            "wlfw_to_wlan0_ms": delta_ms(wlfw_request.get("time"), wlan0.get("time")),
            "wlfw_request_line": wlfw_request.get("line", ""),
            "wlan_pd_line": wlan_pd.get("line", ""),
            "qmi_server_line": qmi_server.get("line", ""),
        }
    return {
        "service74": android.get("service74"),
        "service180": android.get("service180"),
        "wlfw_start": android.get("wlfw_start"),
        "wlfw_request": android.get("wlfw_request"),
        "wlan_pd": android.get("wlan_pd"),
        "qmi_server": android.get("qmi_server"),
        "wlanmdsp": android.get("wlanmdsp"),
        "fw_ready": android.get("fw_ready"),
        "wlan0": android.get("wlan0"),
        "sources": sources,
    }


def classify(v1919: dict[str, Any], v1922: dict[str, Any], android: dict[str, Any], native: dict[str, Any]) -> tuple[str, str, bool]:
    v1919_label = v1919.get("label") or v1919.get("classification", {}).get("label")
    v1922_label = v1922.get("label") or v1922.get("classification", {}).get("label")
    jsn_closed = bool(v1919.get("pass")) and v1919_label == "android-modem-no-jsn-read"
    v1922_closed = bool(v1922.get("pass")) and v1922_label == "service74-pm-open-holder-wlfw-worker-qmi-service-wait"
    android_normal = (
        bool(android.get("service74"))
        and bool(android.get("service180"))
        and bool(android.get("wlfw_request"))
        and bool(android.get("wlan_pd"))
        and bool(android.get("qmi_server"))
        and bool(android.get("wlanmdsp"))
        and bool(android.get("wlan0"))
    )
    native_prereqs = (
        bool(native.get("service74"))
        and bool(native.get("service180"))
        and bool(native.get("pm_open_subsys_modem"))
        and bool(native.get("holder_opened"))
        and bool(native.get("holder_postflight_safe"))
        and intish(native.get("dms_service_request_hit")) > 0
        and intish(native.get("wlfw_service_request_hit")) > 0
        and intish(native.get("wlfw_worker_success_hit")) > 0
    )
    native_wait = (
        intish(native.get("wlfw_ind_register_hit")) == 0
        and intish(native.get("wlfw_cap_hit")) == 0
        and bool(native.get("qrtr_case_0_absent"))
        and bool(native.get("qrtr_case_1_absent"))
        and native.get("servnotif_late_state") == "uninit"
        and intish(native.get("servnotif_late_indication")) == 0
        and not bool(native.get("wlfw69"))
        and not bool(native.get("wlan_pd"))
        and not bool(native.get("wlanmdsp"))
        and not bool(native.get("wlan0"))
    )
    if jsn_closed and v1922_closed and android_normal and native_prereqs and native_wait:
        return (
            "post-wlfw-qmi-service-unavailable-before-ind-cap",
            "V1919 closes the .jsn/RFS lead, Android normal boots publish WLAN-PD/QMI about one second after wlfw_service_request, and native V1920 reaches service74+PM-open+holder+DMS/WLFW worker but never sees WLFW69 or the first WLFW indication/capability QMI path",
            True,
        )
    if not jsn_closed:
        return "jsn-gate-not-closed", "V1919 did not prove android-modem-no-jsn-read", False
    if not android_normal:
        return "android-normal-baseline-incomplete", "retained Android captures do not prove the normal internal WLAN-PD path", False
    if not native_prereqs:
        return "native-combined-prereq-regression", "native evidence no longer proves service74+PM-open+holder+DMS/WLFW worker", False
    if not native_wait:
        return "native-post-wlfw-progress-review", "native post-WLFW state changed and needs review", True
    return "post-wlfw-delta-incomplete", "post-WLFW delta inputs were incomplete", False


def render_source_rows(v1919: dict[str, Any], v1922: dict[str, Any]) -> list[list[str]]:
    return [
        [
            "V1919 .jsn gate",
            str(v1919.get("label", "")),
            str(v1919.get("reason", "")),
        ],
        [
            "V1922 QMI wait",
            str(v1922.get("label", "")),
            str(v1922.get("reason", "")),
        ],
    ]


def render_android_rows(android: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name, data in android["sources"].items():
        rows.append(
            [
                name,
                str(data["wlfw_to_wlan_pd_ms"]),
                f"wlfw={data['wlfw_request_time']} wlan_pd={data['wlan_pd_time']} qmi={data['qmi_server_time']} wlan0={data['wlan0_time']}",
            ]
        )
    return rows


def render_native_rows(native: dict[str, Any]) -> list[list[str]]:
    return [
        [
            "combined prereqs",
            str(all(bool(native.get(key)) for key in ("service74", "service180", "pm_open_subsys_modem", "holder_opened"))),
            f"service74={native['service74']} pm_open={native['pm_open_subsys_modem']} holder={native['holder_opened']}",
        ],
        [
            "worker edge",
            str(native["wlfw_service_request_hit"]),
            f"dms={native['dms_service_request_hit']} worker={native['wlfw_worker_success_hit']} ind={native['wlfw_ind_register_hit']} cap={native['wlfw_cap_hit']}",
        ],
        [
            "publication",
            str(native["wlfw69"]),
            f"servnotif={native['servnotif_late_state']}/{native['servnotif_late_indication']} qrtr69={native['qrtr_case_0_service_events']},{native['qrtr_case_1_service_events']} wlan_pd={native['wlan_pd']} wlanmdsp={native['wlanmdsp']} wlan0={native['wlan0']}",
        ],
        [
            "servloc domain",
            str(native["servloc_result"]),
            f"domains={native['servloc_domain_count']} first={native['servloc_wlan_domain']} instance={native['servloc_wlan_instance']}",
        ],
    ]


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    native = manifest["native"]
    android = manifest["android"]
    lines = [
        "# Native Init V1923 Post-WLFW QMI Service Delta\n\n",
        "## Summary\n\n",
        f"- Cycle: `{CYCLE}`\n",
        f"- Decision: `{manifest['decision']}`\n",
        f"- Label: `{manifest['label']}`\n",
        f"- Pass: `{manifest['pass']}`\n",
        f"- Reason: {manifest['reason']}\n",
        f"- Evidence: `{manifest['out_dir']}`\n\n",
        "## Source Closure\n\n",
        markdown_table(["source", "label", "reason"], render_source_rows(manifest["v1919"], manifest["v1922"])),
        "\n\n## Android Normal Timing\n\n",
        markdown_table(["source", "wlfw_to_wlan_pd_ms", "timing"], render_android_rows(android)),
        "\n\n## Native Edge\n\n",
        markdown_table(["area", "value", "detail"], render_native_rows(native)),
        "\n\n## Native First Lines\n\n",
        f"- DMS request: `{native['dms_service_request_line']}`\n",
        f"- WLFW worker request: `{native['wlfw_service_request_line']}`\n",
        f"- WLFW worker create success: `{native['wlfw_worker_success_line']}`\n",
        f"- WLFW indication QMI: `{native['wlfw_ind_register_line']}`\n",
        f"- WLFW capability QMI: `{native['wlfw_cap_line']}`\n\n",
        "## Interpretation\n\n",
        "- The modem `.jsn`/RFS hypothesis is not the active gate for this unit: V1919 shows normal Android requested `wlanmdsp.mbn` with no pre-request `.jsn` read; native MPSS `.jsn` absence is therefore not the deciding gate.\n",
        "- The clean-DSP/sibling-sysmon companion, PM `/dev/subsys_modem` open, modem holder, DMS request, and CNSS WLFW worker are all present together in V1920.\n",
        "- Native stops before WLFW indication/capability QMI because WLFW service 69/WLAN-PD publication never arrives; Android normal boots make that transition about one second after `wlfw_service_request`.\n",
        "- The next live unit should instrument the worker wait primitive or QMI service wait target around WLFW service 69 publication, still below Wi-Fi HAL and without SDX50M/eSoC/PCIe/GDSC work.\n\n",
        "## Safety Scope\n\n",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, write firmware/partitions, remount-write, open `/dev/subsys_esoc0`, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, external ping, force RC1/case, touch PMIC/GPIO/GDSC/regulators, rescan PCI, bind/unbind platforms, fake ONLINE, or send eSoC notify/BOOT_DONE.\n",
    ]
    classification["rendered_sections"] = ["source closure", "android timing", "native edge"]
    return "".join(lines)


def main() -> int:
    store = EvidenceStore(OUT_DIR)
    store.mkdir("host")
    v1919 = read_json(V1919_MANIFEST)
    v1922 = read_json(V1922_MANIFEST)
    fields = prev1922.parse_kv_text(NATIVE_V1920_HELPER)
    android_raw = prev1922.android_summary()
    native_raw = prev1922.native_summary()
    android = build_android_details(android_raw)
    native = build_native_details(native_raw, fields)
    label, reason, passed = classify(v1919, v1922, android, native)
    decision = f"v1923-{label}-host-{'pass' if passed else 'fail'}"
    host_metadata = collect_host_metadata()
    host_metadata["repo"] = "."
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "pass": passed,
        "decision": decision,
        "label": label,
        "reason": reason,
        "classification": {
            "label": label,
            "decision": decision,
            "pass": passed,
            "reason": reason,
            "jsn_closed": bool(v1919.get("pass")) and (v1919.get("label") == "android-modem-no-jsn-read"),
            "v1922_closed": bool(v1922.get("pass")) and (v1922.get("label") == "service74-pm-open-holder-wlfw-worker-qmi-service-wait"),
        },
        "v1919": {
            "manifest": rel(V1919_MANIFEST),
            "label": v1919.get("label", ""),
            "pass": v1919.get("pass", False),
            "reason": v1919.get("reason", ""),
        },
        "v1922": {
            "manifest": rel(V1922_MANIFEST),
            "label": v1922.get("label", ""),
            "pass": v1922.get("pass", False),
            "reason": v1922.get("reason", ""),
        },
        "android": android,
        "native": native,
        "host_metadata": host_metadata,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"{'PASS' if passed else 'FAIL'} label={label} out_dir={manifest['out_dir']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
