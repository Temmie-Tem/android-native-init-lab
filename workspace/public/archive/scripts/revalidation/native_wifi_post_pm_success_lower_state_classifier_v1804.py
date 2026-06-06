#!/usr/bin/env python3
"""V1804 host-only classifier for post-PM-success lower modem/WLAN-PD state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_post_pm_success_wlfw_classifier_v1802 as prev1802
import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1804"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1801-pm-service-devnode-projection-handoff"
V1803_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1803-wlfw-qmi-readiness-classifier" / "manifest.json"
V739_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v739-mdm3-wlanpd-delta" / "manifest.json"
V852_ANDROID_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v852-android-ext-mdm-provider-surface-handoff"
    / "v852-android-ext-mdm-provider-surface-run"
    / "manifest.json"
)
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1804-post-pm-success-lower-state-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1804_POST_PM_SUCCESS_LOWER_STATE_CLASSIFIER_2026-06-03.md"
)

UPROBE_PREFIX = "wlan_pd_cnss_nonlog_control_flow.uprobe."
PERIPHERAL_PREFIX = "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe."


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: object) -> int:
    return prev1796.intish(value)


def event(fields: dict[str, str], name: str) -> dict[str, str]:
    return prev1802.event(fields, name)


def peripheral_event(fields: dict[str, str], name: str) -> dict[str, str]:
    prefix = PERIPHERAL_PREFIX + name + "."
    return {
        "hit_count": fields.get(prefix + "hit_count", ""),
        "first_hit_line": fields.get(prefix + "first_hit_line", ""),
        "registered": fields.get(prefix + "registered", ""),
        "enabled": fields.get(prefix + "enabled", ""),
        "register_rc": fields.get(prefix + "register_rc", ""),
        "enable_rc": fields.get(prefix + "enable_rc", ""),
    }


def has_android_line(android_manifest: dict[str, Any], needle: str) -> bool:
    lines = android_manifest.get("android_summary", {}).get("focused_lines", {}).get("dmesg", [])
    return any(needle in str(line) for line in lines)


def android_line_count(android_manifest: dict[str, Any], needle: str) -> int:
    lines = android_manifest.get("android_summary", {}).get("focused_lines", {}).get("dmesg", [])
    return sum(1 for line in lines if needle in str(line))


def collect_details(
    fields: dict[str, str],
    source_manifest: dict[str, Any],
    v1803: dict[str, Any],
    v739: dict[str, Any],
    v852: dict[str, Any],
) -> dict[str, Any]:
    android_summary = v852.get("android_summary", {})
    android_hints = android_summary.get("dmesg_hints", {})
    android_surface = android_summary.get("surface", {})
    android_counts = android_summary.get("counts", {})
    return {
        "source_dir": rel(SOURCE_DIR),
        "source_decision": source_manifest.get("decision", ""),
        "source_pass": bool(source_manifest.get("pass")),
        "source_projection_label": source_manifest.get("gate", {}).get("pm_service_devnode_projection_label", ""),
        "source_pm_server_label": source_manifest.get("gate", {}).get("pm_server_label", ""),
        "source_list_commit_hits": source_manifest.get("gate", {}).get("pm_service_add_peripheral_list_commit_hits", ""),
        "source_pm_register_success_hits": source_manifest.get("gate", {}).get("pm_server_success_return_hits", ""),
        "v1803_decision": v1803.get("decision", ""),
        "v1803_pass": bool(v1803.get("pass")),
        "v1803_reason": v1803.get("reason", ""),
        "pm_init_pm_client_register_retcheck": event(fields, "pm_init_pm_client_register_retcheck"),
        "pm_init_pm_client_connect_retcheck": event(fields, "pm_init_pm_client_connect_retcheck"),
        "periph_binder_object_present_check": peripheral_event(fields, "periph_binder_object_present_check"),
        "periph_as_interface_call": peripheral_event(fields, "periph_as_interface_call"),
        "periph_manager_register_tx_retcheck": peripheral_event(fields, "periph_manager_register_tx_retcheck"),
        "periph_success_path": peripheral_event(fields, "periph_success_path"),
        "current_mss_before": fields.get("wifi_companion_start.subsys_hold.wlan_pd_modem_before.mss_state", ""),
        "current_mdm3_before": fields.get("wifi_companion_start.subsys_hold.wlan_pd_modem_before.mdm3_state", ""),
        "current_mss_after_start": fields.get("wifi_companion_start.subsys_hold.wlan_pd_modem_after_start.mss_state", ""),
        "current_mdm3_after_start": fields.get("wifi_companion_start.subsys_hold.wlan_pd_modem_after_start.mdm3_state", ""),
        "current_rpmsg_ipcrtr_present": fields.get(
            "wifi_companion_start.subsys_hold.wlan_pd_modem_after_start.rpmsg_ipcrtr_present", ""
        ),
        "current_rpmsg_count": fields.get("wifi_companion_start.subsys_hold.wlan_pd_modem_after_start.rpmsg_count", ""),
        "current_mhi_pipe_fd_count": fields.get("wlan_pd_cnss_nonlog_control_flow.global.mhi_pipe_fd_count", ""),
        "current_requested_wlanmdsp": fields.get("wlan_pd_service_object_visible_trigger.requested_wlanmdsp", ""),
        "current_wlfw_service69_seen": fields.get("wlan_pd_service_object_visible_trigger.wlfw_service69_seen", ""),
        "current_wlan0_present": fields.get("wlan_pd_service_object_visible_trigger.wlan0_present", ""),
        "current_servnotif_state": v1803.get("details", {})
        .get("service_notifier_late_listener", {})
        .get("response_curr_state_name", ""),
        "current_servnotif_indication_seen": v1803.get("details", {})
        .get("service_notifier_late_listener", {})
        .get("indication_seen", ""),
        "current_qrtr_service69_case0_events": v1803.get("details", {})
        .get("qrtr_case_0", {})
        .get("readback.service_events", ""),
        "current_qrtr_service69_case1_events": v1803.get("details", {})
        .get("qrtr_case_1", {})
        .get("readback.service_events", ""),
        "android_v739_decision": v739.get("decision", ""),
        "android_v739_reason": v739.get("reason", ""),
        "android_v739_mss_state": v739.get("android_v590_summary", {}).get("mss_state", ""),
        "android_v739_mdm3_state": v739.get("android_v590_summary", {}).get("mdm3_state", ""),
        "android_v739_wlanpd_counts": {
            "service_notifier_180": v739.get("android_v611_summary", {}).get("counts", {}).get("service_notifier_180", ""),
            "service_notifier_74": v739.get("android_v611_summary", {}).get("counts", {}).get("service_notifier_74", ""),
            "wlan_pd": v739.get("android_v611_summary", {}).get("counts", {}).get("wlan_pd", ""),
            "wlan0": v739.get("android_v611_summary", {}).get("counts", {}).get("wlan0", ""),
            "qmi_server_connected": v739.get("android_v611_summary", {}).get("counts", {}).get("qmi_server_connected", ""),
        },
        "android_v852_decision": v852.get("decision", ""),
        "android_v852_pass": bool(v852.get("pass")),
        "android_v852_mss_state": android_summary.get("mss_state", ""),
        "android_v852_mdm3_state": android_summary.get("mdm3_state", ""),
        "android_v852_hints": {
            "has_wlan_pd": bool(android_hints.get("has_wlan_pd")),
            "has_wlfw": bool(android_hints.get("has_wlfw")),
            "has_bdf": bool(android_hints.get("has_bdf")),
            "has_wlan0": bool(android_hints.get("has_wlan0")),
        },
        "android_v852_surface": {
            "raw_esoc_node_present": bool(android_surface.get("raw_esoc_node_present")),
            "esoc0_sysfs_present": bool(android_surface.get("esoc0_sysfs_present")),
            "mdm3_sysfs_present": bool(android_surface.get("mdm3_sysfs_present")),
            "subsys9_present": bool(android_surface.get("subsys9_present")),
        },
        "android_v852_counts": {
            "wlfw": android_counts.get("wlfw", ""),
            "wlan0": android_counts.get("wlan0", ""),
            "mhi": android_counts.get("mhi", ""),
            "sdx50": android_counts.get("sdx50", ""),
        },
        "android_v852_timeline": {
            "esoc0_get": has_android_line(v852, "__subsystem_get: esoc0 count:0"),
            "wlan_pd_up": has_android_line(v852, "msm/modem/wlan_pd, state: 0x1fffffff"),
            "wlan_pd_ack": has_android_line(v852, "Indication ACKed"),
            "bdf_events": android_line_count(v852, "wlfw_send_bdf_download_req"),
            "wlan0_events": android_line_count(v852, "dev : wlan0"),
        },
    }


def classify(details: dict[str, Any]) -> tuple[str, str]:
    pm_success = (
        bool(details.get("source_pass"))
        and intish(details.get("source_list_commit_hits")) > 0
        and intish(details.get("source_pm_register_success_hits")) > 0
        and intish(details["pm_init_pm_client_connect_retcheck"].get("hit_count")) > 0
        and intish(details["periph_success_path"].get("hit_count")) > 0
    )
    current_lower_stalled = (
        details.get("current_mss_after_start") == "ONLINE"
        and details.get("current_mdm3_after_start") == "OFFLINING"
        and details.get("current_servnotif_state") == "uninit"
        and intish(details.get("current_servnotif_indication_seen")) == 0
        and intish(details.get("current_wlfw_service69_seen")) == 0
        and intish(details.get("current_requested_wlanmdsp")) == 0
    )
    android_lower_positive = (
        bool(details.get("android_v852_pass"))
        and details.get("android_v852_mss_state") == "ONLINE"
        and details.get("android_v852_mdm3_state") == "ONLINE"
        and bool(details.get("android_v852_hints", {}).get("has_wlan_pd"))
        and bool(details.get("android_v852_hints", {}).get("has_wlfw"))
        and bool(details.get("android_v852_hints", {}).get("has_wlan0"))
    )
    if not bool(details.get("v1803_pass")):
        return "source-v1803-not-pass", "V1803 source classifier was not PASS"
    if not pm_success:
        return "pm-success-not-established", "V1801 does not prove PM service-object/register/connect success"
    if current_lower_stalled and android_lower_positive:
        return (
            "post-pm-success-mdm3-offlining-before-wlanpd-up",
            "V1801 repaired PM register/connect and reached MSS ONLINE, but mdm3 stayed OFFLINING and wlan_pd remained uninit while Android-good reaches mdm3 ONLINE, wlan_pd UP, WLFW/BDF, and wlan0",
        )
    if current_lower_stalled:
        return "current-lower-stall-without-android-positive", "Current lower stall is present but Android-positive baseline is incomplete"
    return "post-pm-lower-state-incomplete", "Post-PM lower-state discriminator was incomplete"


def render_event(name: str, data: dict[str, str]) -> list[str]:
    return [
        f"- `{name}` hits/registered/enabled: `{data.get('hit_count')}` / `{data.get('registered')}` / `{data.get('enabled')}`",
        f"- `{name}` first hit: `{data.get('first_hit_line')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    d = result["details"]
    android_counts = d["android_v739_wlanpd_counts"]
    android_hints = d["android_v852_hints"]
    android_surface = d["android_v852_surface"]
    android_timeline = d["android_v852_timeline"]
    lines = [
        "# Native Init V1804 Post-PM-success Lower-state Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1804`",
        "- Type: host-only classifier over V1801/V1803 current evidence and retained Android-positive lower-state evidence",
        f"- Decision: `{result['decision']}`",
        "- Result: PASS",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Current PM Gate",
        "",
        f"- V1801 decision: `{d['source_decision']}`",
        f"- V1803 decision: `{d['v1803_decision']}`",
        f"- projection / PM server labels: `{d['source_projection_label']}` / `{d['source_pm_server_label']}`",
        f"- list commit / PM register success hits: `{d['source_list_commit_hits']}` / `{d['source_pm_register_success_hits']}`",
        *render_event("pm_init_pm_client_register_retcheck", d["pm_init_pm_client_register_retcheck"]),
        *render_event("pm_init_pm_client_connect_retcheck", d["pm_init_pm_client_connect_retcheck"]),
        *render_event("periph_binder_object_present_check", d["periph_binder_object_present_check"]),
        *render_event("periph_as_interface_call", d["periph_as_interface_call"]),
        *render_event("periph_manager_register_tx_retcheck", d["periph_manager_register_tx_retcheck"]),
        *render_event("periph_success_path", d["periph_success_path"]),
        "",
        "## Current Lower State",
        "",
        f"- mss before/after holder: `{d['current_mss_before']}` / `{d['current_mss_after_start']}`",
        f"- mdm3 before/after holder: `{d['current_mdm3_before']}` / `{d['current_mdm3_after_start']}`",
        f"- rpmsg count/ipcrtr: `{d['current_rpmsg_count']}` / `{d['current_rpmsg_ipcrtr_present']}`",
        f"- MHI pipe fd count: `{d['current_mhi_pipe_fd_count']}`",
        f"- service-notifier state/indication: `{d['current_servnotif_state']}` / `{d['current_servnotif_indication_seen']}`",
        f"- WLFW service69 QRTR case events: `{d['current_qrtr_service69_case0_events']}` / `{d['current_qrtr_service69_case1_events']}`",
        f"- requested `wlanmdsp` / summary service69 / wlan0: `{d['current_requested_wlanmdsp']}` / `{d['current_wlfw_service69_seen']}` / `{d['current_wlan0_present']}`",
        "",
        "## Android-positive Baseline",
        "",
        f"- V739 decision: `{d['android_v739_decision']}`",
        f"- V739 Android mss/mdm3: `{d['android_v739_mss_state']}` / `{d['android_v739_mdm3_state']}`",
        f"- V739 Android service-notifier 180/74, wlan_pd, wlan0, QMI connected: `{android_counts['service_notifier_180']}` / `{android_counts['service_notifier_74']}` / `{android_counts['wlan_pd']}` / `{android_counts['wlan0']}` / `{android_counts['qmi_server_connected']}`",
        f"- V852 decision: `{d['android_v852_decision']}`",
        f"- V852 Android mss/mdm3: `{d['android_v852_mss_state']}` / `{d['android_v852_mdm3_state']}`",
        f"- V852 hints wlan_pd/WLFW/BDF/wlan0: `{android_hints['has_wlan_pd']}` / `{android_hints['has_wlfw']}` / `{android_hints['has_bdf']}` / `{android_hints['has_wlan0']}`",
        f"- V852 surface raw_esoc/esoc0_sysfs/mdm3_sysfs/subsys9: `{android_surface['raw_esoc_node_present']}` / `{android_surface['esoc0_sysfs_present']}` / `{android_surface['mdm3_sysfs_present']}` / `{android_surface['subsys9_present']}`",
        f"- V852 timeline esoc0_get/wlan_pd_up/ack/BDF_events/wlan0_events: `{android_timeline['esoc0_get']}` / `{android_timeline['wlan_pd_up']}` / `{android_timeline['wlan_pd_ack']}` / `{android_timeline['bdf_events']}` / `{android_timeline['wlan0_events']}`",
        "",
        "## Interpretation",
        "",
        "- V1801/V1803 close the previous PM service-object/register/connect blocker enough to treat PM client voting as reached.",
        "- The current native stall is now below that PM vote boundary: MSS is online and rpmsg/IPCRTR exists, but mdm3 remains `OFFLINING`; wlan_pd service-notifier remains `uninit`, WLFW service 69 is absent, and no firmware request or `wlan0` follows.",
        "- Android-positive evidence on the same stock kernel reaches mdm3 `ONLINE`, wlan_pd UP/ACK, WLFW/BDF, and `wlan0`; this makes the active blocker a safe mdm3/ext-sdx50m continuation discriminator, not Wi-Fi HAL, credentials, DHCP, or external ping.",
        "- The next unit should classify PM-service-owned lower continuation around modem vote to mdm3/ext-sdx50m state without direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify, PCI rescan/bind, platform unbind, or PMIC/GPIO/GDSC writes.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    source_manifest_path = SOURCE_DIR / "manifest.json"
    source_manifest = load_json(source_manifest_path)
    v1803 = load_json(V1803_MANIFEST)
    v739 = load_json(V739_MANIFEST)
    v852 = load_json(V852_ANDROID_MANIFEST)
    fields = prev1796.runner.fwbase.parse_helper_fields(SOURCE_DIR)
    details = collect_details(fields, source_manifest, v1803, v739, v852)
    label, reason = classify(details)
    result = {
        "cycle": CYCLE,
        "decision": f"v1804-{label}-host-pass",
        "pass": True,
        "reason": reason,
        "source_manifest": rel(source_manifest_path),
        "v1803_manifest": rel(V1803_MANIFEST),
        "v739_manifest": rel(V739_MANIFEST),
        "v852_android_manifest": rel(V852_ANDROID_MANIFEST),
        "out_dir": rel(OUT_DIR),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(render_report(result), encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": True, "label": label}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
