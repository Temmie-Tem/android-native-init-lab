#!/usr/bin/env python3
"""V1836 host-only classifier for the WLAN-PD UNINIT transition target."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1836"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1836-wlan-pd-uninit-transition-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1836_WLAN_PD_UNINIT_TRANSITION_CLASSIFIER_2026-06-03.md"
)

V1835_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1835-qipcrtr-route-pivot-classifier" / "manifest.json"
V1804_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1804-post-pm-success-lower-state-classifier" / "manifest.json"
V1760_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1760-wlan-pd-request-trigger-surface-classifier" / "manifest.json"
V1738_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1738-wlan-pd-trigger-surface-classifier" / "manifest.json"
V1244_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1244-android-power-surface-classifier" / "manifest.json"


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return bool(value) and str(value) not in {"0", "False", "false", "None", ""}


def source_summary(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "label": manifest.get("label", ""),
    }


def collect_details(
    v1835: dict[str, Any],
    v1804: dict[str, Any],
    v1760: dict[str, Any],
    v1738: dict[str, Any],
    v1244: dict[str, Any],
) -> dict[str, Any]:
    d1835 = v1835.get("details") or {}
    d1804 = v1804.get("details") or {}
    android1760 = v1760.get("android") or {}
    native1760 = v1760.get("native") or {}
    native1760_gate = native1760.get("gate") or {}
    checks1738 = v1738.get("checks") or {}
    evidence1738 = v1738.get("evidence") or {}
    android1738 = evidence1738.get("android_good") or {}
    source1738 = evidence1738.get("source") or {}
    android1244 = v1244.get("android") or {}
    native1244 = v1244.get("native") or {}
    native1244_first = native1244.get("first_sample") or {}

    return {
        "sources": {
            "v1835": source_summary(v1835, V1835_MANIFEST),
            "v1804": source_summary(v1804, V1804_MANIFEST),
            "v1760": source_summary(v1760, V1760_MANIFEST),
            "v1738": source_summary(v1738, V1738_MANIFEST),
            "v1244": source_summary(v1244, V1244_MANIFEST),
        },
        "current": {
            "pm_projection_label": d1835.get("pm_service_devnode_projection_label", ""),
            "pm_service_names": d1835.get("pm_service_entry_names", ""),
            "pm_service_devnodes": d1835.get("pm_service_entry_devnodes", ""),
            "pm_service_list_commit_hits": d1835.get("pm_service_list_commit_hits", ""),
            "pm_service_init_fail_hits": d1835.get("pm_service_init_fail_hits", ""),
            "pm_client_register_rc": d1835.get("pm_client_register_rc", ""),
            "pm_client_connect_rc": d1835.get("pm_client_connect_rc", ""),
            "pm_init_return_path_rc": d1835.get("pm_init_return_path_rc", ""),
            "provider_seen": d1835.get("provider_seen", ""),
            "as_interface_hits": d1835.get("as_interface_hits", ""),
            "register_tx_hits": d1835.get("register_tx_hits", ""),
            "qipcrtr_label": d1835.get("qipcrtr_bound_recv_label", ""),
            "qipcrtr_poll_timeout_ms": d1835.get("qipcrtr_bound_recv_poll_timeout_ms", ""),
            "qipcrtr_poll_timeout": d1835.get("qipcrtr_bound_recv_poll_timeout", ""),
            "qipcrtr_recv_skip_reason": d1835.get("qipcrtr_bound_recv_recv_skip_reason", ""),
            "qipcrtr_no_connect": d1835.get("qipcrtr_bound_recv_no_connect", ""),
            "qipcrtr_no_send": d1835.get("qipcrtr_bound_recv_no_send", ""),
            "qipcrtr_no_lookup": d1835.get("qipcrtr_bound_recv_no_lookup_send", ""),
            "qipcrtr_no_control": d1835.get("qipcrtr_bound_recv_no_control_payload", ""),
            "qipcrtr_no_service_start": d1835.get("qipcrtr_bound_recv_no_service_start", ""),
            "qrtr_readback_label": d1835.get("qrtr_readback_label", ""),
            "servloc_domain_label": d1835.get("servloc_domain_label", ""),
            "servnotif_label": d1835.get("servnotif_label", ""),
            "servnotif_early_state": d1835.get("service_notifier_early_state", ""),
            "servnotif_late_state": d1835.get("service_notifier_late_state", ""),
            "servnotif_early_indication": (d1835.get("service_notifier_early") or {}).get("indication_seen", ""),
            "servnotif_late_indication": (d1835.get("service_notifier_late") or {}).get("indication_seen", ""),
            "raw_service180_counts": d1835.get("raw_service180_text_counts", ""),
            "raw_service74_counts": d1835.get("raw_service74_text_counts", ""),
            "raw_wlan_pd_counts": d1835.get("raw_wlan_pd_text_counts", ""),
            "lower_state_label": d1835.get("post_pm_lower_state_label", ""),
            "lower_mdm3_states": d1835.get("lower_mdm3_states", ""),
            "lower_mhi_present": d1835.get("lower_mhi_present"),
            "lower_service69_progress": d1835.get("lower_service69_progress"),
            "lower_wlan0_present": d1835.get("lower_wlan0_present"),
            "requested_wlanmdsp": d1835.get("requested_wlanmdsp", ""),
            "wlfw_service69_seen": d1835.get("wlfw_service69_seen", ""),
            "wlan0_present": d1835.get("wlan0_present", ""),
            "v1804_current_mdm3_before": d1804.get("current_mdm3_before", ""),
            "v1804_current_mdm3_after": d1804.get("current_mdm3_after_start", ""),
            "v1804_current_mhi_pipe_fd_count": d1804.get("current_mhi_pipe_fd_count", ""),
            "v1760_native_wlfw_start_hits": native1760_gate.get("wlfw_start_hit_count", ""),
            "v1760_native_wlfw_request_hits": native1760_gate.get("wlfw_service_request_hit_count", ""),
            "v1760_native_wlfw_worker_hits": native1760_gate.get("wlfw_worker_create_success_hit_count", ""),
            "v1760_native_requested_wlanmdsp": native1760_gate.get("requested_wlanmdsp", ""),
            "v1760_native_firmware_label": native1760_gate.get("old_firmware_serve_label", ""),
        },
        "android_positive": {
            "v1804_android_v739_mss": d1804.get("android_v739_mss_state", ""),
            "v1804_android_v739_mdm3": d1804.get("android_v739_mdm3_state", ""),
            "v1804_android_v739_counts": d1804.get("android_v739_wlanpd_counts") or {},
            "v1804_android_v852_mss": d1804.get("android_v852_mss_state", ""),
            "v1804_android_v852_mdm3": d1804.get("android_v852_mdm3_state", ""),
            "v1804_android_v852_hints": d1804.get("android_v852_hints") or {},
            "v1804_android_v852_timeline": d1804.get("android_v852_timeline") or {},
            "v1760_requested_wlanmdsp": android1760.get("requested_wlanmdsp"),
            "v1760_vendor_firmware_fallback": (android1760.get("served_path") or {}).get("vendor_firmware_attempt_seen"),
            "v1760_vendor_firmware_oack": (android1760.get("served_path") or {}).get("vendor_firmware_oack_size_seen"),
            "v1738_companion_services": checks1738.get("android_companion_services_running"),
            "v1738_reaches_wlan_pd_wlan0": checks1738.get("android_good_reaches_wlan_pd_and_wlan0"),
            "v1738_no_restart_pd_marker": checks1738.get("android_no_restart_pd_marker"),
            "v1738_wlfw_start_s": android1738.get("wlfw_start_s", ""),
            "v1738_wlfw_service_request_s": android1738.get("wlfw_service_request_s", ""),
            "v1738_icnss_qmi_s": android1738.get("icnss_qmi_s", ""),
            "v1738_wlan0_s": android1738.get("wlan0_s", ""),
            "v1244_pcie_rc1_line": android1244.get("pcie_rc1_report_line", ""),
            "v1244_android_pcie_rc1_present": android1244.get("pcie_rc1_report_present"),
        },
        "source_surface": {
            "icnss_fw_lookup_is_passive": checks1738.get("icnss_fw_lookup_is_passive"),
            "listener_register_is_state_query": checks1738.get("listener_register_is_state_query"),
            "restart_pd_is_explicit_recovery_api_only": checks1738.get("restart_pd_is_explicit_recovery_api_only"),
            "service_notifier_register_listener_line": source1738.get("service_notifier_register_listener_line", ""),
            "service_notifier_restart_pd_line": source1738.get("service_notifier_restart_pd_line", ""),
            "qmi_add_lookup_line": source1738.get("qmi_add_lookup_line", ""),
        },
        "legacy_power_gap_context": {
            "v1244_native_decision": native1244.get("decision", ""),
            "v1244_native_first_mdm3": native1244_first.get("mdm3_state", ""),
            "v1244_native_mhi_bus_count": native1244_first.get("mhi_bus_count", ""),
            "v1244_native_mhi_pipe_exists": native1244_first.get("mhi_pipe_exists", ""),
            "v1244_native_wlan0_exists": native1244_first.get("wlan0_exists", ""),
            "v1244_native_pcie1_gdsc_line": native1244_first.get("pcie1_gdsc_line", ""),
            "v1244_native_pmic_soft_reset_line": native1244_first.get("pmic_soft_reset_line", ""),
        },
    }


def current_pm_and_qrtr_cleared(details: dict[str, Any]) -> bool:
    current = details["current"]
    return (
        current["pm_projection_label"] == "list-commit-progress"
        and intish(current["pm_service_list_commit_hits"]) > 0
        and current["pm_service_init_fail_hits"] == "0"
        and current["pm_client_register_rc"] == "0"
        and current["pm_client_connect_rc"] == "0"
        and current["pm_init_return_path_rc"] == "0"
        and current["provider_seen"] == "1"
        and current["as_interface_hits"] == "1"
        and current["register_tx_hits"] == "1"
        and current["qipcrtr_label"] == "qipcrtr-bound-recv-poll-timeout-passive"
        and current["qipcrtr_poll_timeout"] == "1"
        and current["qipcrtr_recv_skip_reason"] == "poll-timeout"
        and all(current[key] == "1" for key in (
            "qipcrtr_no_connect",
            "qipcrtr_no_send",
            "qipcrtr_no_lookup",
            "qipcrtr_no_control",
            "qipcrtr_no_service_start",
        ))
        and current["qrtr_readback_label"] == "wlfw-readback-empty"
        and current["servloc_domain_label"] == "servloc-domain-wlan-pd-instance180"
        and current["servnotif_label"] == "service-notifier-uninit"
    )


def current_still_uninit(details: dict[str, Any]) -> bool:
    current = details["current"]
    return (
        current["servnotif_early_state"] == "uninit"
        and current["servnotif_late_state"] == "uninit"
        and intish(current["servnotif_early_indication"]) == 0
        and intish(current["servnotif_late_indication"]) == 0
        and current["raw_service180_counts"] == "1,1,1"
        and current["raw_service74_counts"] == "0,0,0"
        and current["raw_wlan_pd_counts"] == "0,0,0"
        and current["lower_state_label"] == "stable-mdm3-offlining"
        and current["lower_mdm3_states"] == "OFFLINING"
        and not boolish(current["lower_mhi_present"])
        and not boolish(current["lower_service69_progress"])
        and not boolish(current["lower_wlan0_present"])
        and current["requested_wlanmdsp"] == "0"
        and current["wlfw_service69_seen"] == "0"
        and current["wlan0_present"] == "0"
    )


def android_positive_lower_chain(details: dict[str, Any]) -> bool:
    android = details["android_positive"]
    v739_counts = android["v1804_android_v739_counts"]
    v852_hints = android["v1804_android_v852_hints"]
    return (
        android["v1804_android_v739_mss"] == "ONLINE"
        and android["v1804_android_v739_mdm3"] == "ONLINE"
        and intish(v739_counts.get("service_notifier_74")) > 0
        and intish(v739_counts.get("wlan_pd")) > 0
        and intish(v739_counts.get("qmi_server_connected")) > 0
        and intish(v739_counts.get("wlan0")) > 0
        and android["v1804_android_v852_mss"] == "ONLINE"
        and android["v1804_android_v852_mdm3"] == "ONLINE"
        and bool(v852_hints.get("has_wlan_pd"))
        and bool(v852_hints.get("has_wlfw"))
        and bool(v852_hints.get("has_wlan0"))
        and bool(android["v1760_requested_wlanmdsp"])
        and bool(android["v1760_vendor_firmware_fallback"])
        and bool(android["v1760_vendor_firmware_oack"])
        and bool(android["v1738_companion_services"])
        and bool(android["v1738_reaches_wlan_pd_wlan0"])
        and bool(android["v1738_no_restart_pd_marker"])
        and bool(android["v1244_android_pcie_rc1_present"])
    )


def source_surface_is_passive(details: dict[str, Any]) -> bool:
    source = details["source_surface"]
    return (
        bool(source["icnss_fw_lookup_is_passive"])
        and bool(source["listener_register_is_state_query"])
        and bool(source["restart_pd_is_explicit_recovery_api_only"])
    )


def classify(details: dict[str, Any]) -> tuple[str, bool, str]:
    sources = details["sources"]
    if not all(sources[key]["pass"] for key in sources):
        return "source-retained-evidence-missing", False, "one or more retained input classifiers did not pass"
    if sources["v1835"]["decision"] != "v1835-qipcrtr-mechanics-cleared-wlan-pd-uninit-blocker-host-pass":
        return "qipcrtr-pivot-not-closed", False, "V1835 did not close the QRTR mechanics pivot"
    if not current_pm_and_qrtr_cleared(details):
        return "current-pm-qipcrtr-shape-incomplete", False, "current V1835 evidence does not show both PM and QRTR mechanics cleared"
    if not current_still_uninit(details):
        return "current-lower-state-progress-or-incomplete", False, "current lower state is no longer the fixed uninit/offlining blocker shape"
    if not android_positive_lower_chain(details):
        return "android-positive-lower-chain-incomplete", False, "retained Android-positive evidence does not prove the lower WLAN-PD chain"
    if not source_surface_is_passive(details):
        return "source-surface-review", False, "retained AP-side source surface did not remain passive/read-only"
    return (
        "wlan-pd-uninit-lower-continuation-target",
        True,
        "PM list/register, service-object, service-locator/notifier, and QIPCRTR socket mechanics are cleared enough; native remains mdm3 OFFLINING with service-notifier uninit, no WLFW service 69, no wlanmdsp request, no MHI, and no wlan0 while Android-positive reaches mdm3 ONLINE, WLAN-PD UP, WLFW/BDF, and wlan0",
    )


def render_report(result: dict[str, Any]) -> str:
    details = result["details"]
    sources = details["sources"]
    current = details["current"]
    android = details["android_positive"]
    source = details["source_surface"]
    legacy = details["legacy_power_gap_context"]
    result_text = "PASS" if result["pass"] else "FAIL"
    return "\n".join(
        [
            "# Native Init V1836 WLAN-PD UNINIT Transition Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1836`",
            "- Type: host-only retained-evidence classifier over V1835 plus lower/Android-positive baselines",
            f"- Decision: `{result['decision']}`",
            f"- Result: {result_text}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Source Gates",
            "",
            f"- V1835: `{sources['v1835']['decision']}`",
            f"- V1804: `{sources['v1804']['decision']}`",
            f"- V1760: `{sources['v1760']['decision']}` / `{sources['v1760']['label']}`",
            f"- V1738: `{sources['v1738']['decision']}` / `{sources['v1738']['label']}`",
            f"- V1244: `{sources['v1244']['decision']}`",
            "",
            "## Current Cleared Mechanics",
            "",
            f"- PM projection/list/init-fail: `{current['pm_projection_label']}` / `{current['pm_service_list_commit_hits']}` / `{current['pm_service_init_fail_hits']}`",
            f"- PM provider/asInterface/register TX: `{current['provider_seen']}` / `{current['as_interface_hits']}` / `{current['register_tx_hits']}`",
            f"- PM client register/connect/return rc: `{current['pm_client_register_rc']}` / `{current['pm_client_connect_rc']}` / `{current['pm_init_return_path_rc']}`",
            f"- QIPCRTR label/poll/reason: `{current['qipcrtr_label']}` / `{current['qipcrtr_poll_timeout_ms']}ms timeout={current['qipcrtr_poll_timeout']}` / `{current['qipcrtr_recv_skip_reason']}`",
            f"- QRTR/service-locator/service-notifier labels: `{current['qrtr_readback_label']}` / `{current['servloc_domain_label']}` / `{current['servnotif_label']}`",
            f"- bound observer no connect/send/lookup/control/service-start: `{current['qipcrtr_no_connect']}` / `{current['qipcrtr_no_send']}` / `{current['qipcrtr_no_lookup']}` / `{current['qipcrtr_no_control']}` / `{current['qipcrtr_no_service_start']}`",
            "",
            "## Current Blocker Shape",
            "",
            f"- service-notifier early/late state: `{current['servnotif_early_state']}` / `{current['servnotif_late_state']}`",
            f"- service-notifier early/late indications: `{current['servnotif_early_indication']}` / `{current['servnotif_late_indication']}`",
            f"- raw service180/service74/wlan_pd: `{current['raw_service180_counts']}` / `{current['raw_service74_counts']}` / `{current['raw_wlan_pd_counts']}`",
            f"- lower state/mdm3/MHI: `{current['lower_state_label']}` / `{current['lower_mdm3_states']}` / `{current['lower_mhi_present']}`",
            f"- requested wlanmdsp / WLFW service69 / wlan0: `{current['requested_wlanmdsp']}` / `{current['wlfw_service69_seen']}` / `{current['wlan0_present']}`",
            f"- V1760 native WLFW start/request/worker/requested: `{current['v1760_native_wlfw_start_hits']}` / `{current['v1760_native_wlfw_request_hits']}` / `{current['v1760_native_wlfw_worker_hits']}` / `{current['v1760_native_requested_wlanmdsp']}`",
            "",
            "## Android-Positive Contrast",
            "",
            f"- V1804 Android mss/mdm3: `{android['v1804_android_v739_mss']}` / `{android['v1804_android_v739_mdm3']}`",
            f"- V739 service-notifier74/wlan_pd/qmi/wlan0 counts: `{android['v1804_android_v739_counts'].get('service_notifier_74')}` / `{android['v1804_android_v739_counts'].get('wlan_pd')}` / `{android['v1804_android_v739_counts'].get('qmi_server_connected')}` / `{android['v1804_android_v739_counts'].get('wlan0')}`",
            f"- V852 mdm3 and hints wlan_pd/WLFW/wlan0: `{android['v1804_android_v852_mdm3']}` / `{android['v1804_android_v852_hints'].get('has_wlan_pd')}` / `{android['v1804_android_v852_hints'].get('has_wlfw')}` / `{android['v1804_android_v852_hints'].get('has_wlan0')}`",
            f"- V1760 Android requested/fallback/OACK: `{android['v1760_requested_wlanmdsp']}` / `{android['v1760_vendor_firmware_fallback']}` / `{android['v1760_vendor_firmware_oack']}`",
            f"- V1738 Android companion/no-restart/WLAN-PD+wlan0: `{android['v1738_companion_services']}` / `{android['v1738_no_restart_pd_marker']}` / `{android['v1738_reaches_wlan_pd_wlan0']}`",
            f"- V1244 Android PCIe RC1 reference: `{android['v1244_pcie_rc1_line']}`",
            "",
            "## Source Surface",
            "",
            f"- ICNSS WLFW lookup passive: `{source['icnss_fw_lookup_is_passive']}`",
            f"- service-notifier listener is state query: `{source['listener_register_is_state_query']}`",
            f"- restart-PD API explicit recovery only: `{source['restart_pd_is_explicit_recovery_api_only']}`",
            f"- source lines listener/restart/lookup: `{source['service_notifier_register_listener_line']}` / `{source['service_notifier_restart_pd_line']}` / `{source['qmi_add_lookup_line']}`",
            "",
            "## Legacy Power-Gap Context",
            "",
            f"- V1244 native decision: `{legacy['v1244_native_decision']}`",
            f"- V1244 native first mdm3/MHI/wlan0: `{legacy['v1244_native_first_mdm3']}` / `{legacy['v1244_native_mhi_bus_count']}` / `{legacy['v1244_native_wlan0_exists']}`",
            f"- V1244 native PCIe1 GDSC: `{legacy['v1244_native_pcie1_gdsc_line']}`",
            f"- V1244 native PMIC soft-reset line: `{legacy['v1244_native_pmic_soft_reset_line']}`",
            "",
            "## Interpretation",
            "",
            "- V1835 rules out another QRTR socket-mechanics unit: bound local port allocation, passive poll/timeout, service-locator domain-list QMI, and service-notifier listener QMI are all classified.",
            "- The PM-service list/devnode and client register/connect blockers are also past the immediate boundary for this route.",
            "- The remaining fixed blocker is the WLAN-PD UNINIT transition below the PM vote boundary: native does not move mdm3 toward ONLINE/MHI, does not publish WLFW service 69, and never requests `wlanmdsp.mbn`.",
            "- The next unit should be host/source-only first and define a no-write lower-continuation observer/target around mdm3/ext-SDX50M state transition prerequisites; it should not add QRTR probes, PM actors, restart-PD, eSoC/RC1 actions, Wi-Fi HAL, or scan/connect.",
            "",
            "## Safety Scope",
            "",
            "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
            "",
        ]
    )


def main() -> int:
    v1835 = load_json(V1835_MANIFEST)
    v1804 = load_json(V1804_MANIFEST)
    v1760 = load_json(V1760_MANIFEST)
    v1738 = load_json(V1738_MANIFEST)
    v1244 = load_json(V1244_MANIFEST)
    details = collect_details(v1835, v1804, v1760, v1738, v1244)
    label, passed, reason = classify(details)
    status = "pass" if passed else "fail"
    result = {
        "cycle": CYCLE,
        "decision": f"v1836-{label}-host-{status}",
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = render_report(result)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(report, encoding="utf-8")
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": passed, "label": label}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
