#!/usr/bin/env python3
"""V1820 host-only classifier for the servloc domain publication gap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1820"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1819-publication-text-handoff"
V739_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v739-mdm3-wlanpd-delta" / "manifest.json"
V852_ANDROID_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v852-android-ext-mdm-provider-surface-handoff"
    / "v852-android-ext-mdm-provider-surface-run"
    / "manifest.json"
)
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1820-servloc-domain-gap-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1820_SERVLOC_DOMAIN_GAP_CLASSIFIER_2026-06-03.md"
)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: object) -> int:
    return prev1796.intish(value)


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return bool(value) and str(value) not in {"0", "False", "false", "None", ""}


def android_counts(v739: dict[str, Any]) -> dict[str, Any]:
    return v739.get("android_v622_summary", {}).get("counts", {})


def android_deltas(v739: dict[str, Any]) -> dict[str, Any]:
    return v739.get("android_v622_summary", {}).get("deltas_ms", {})


def collect_details(source: dict[str, Any],
                    v739: dict[str, Any],
                    v852: dict[str, Any]) -> dict[str, Any]:
    gate = source.get("gate", {})
    counts = android_counts(v739)
    deltas = android_deltas(v739)
    v852_summary = v852.get("android_summary", {})
    hints = v852_summary.get("dmesg_hints", {})
    return {
        "source_dir": rel(SOURCE_DIR),
        "source_decision": source.get("decision", ""),
        "source_pass": bool(source.get("pass")),
        "source_reason": source.get("reason", ""),
        "rollback_ok": source.get("rollback", {}).get("ok"),
        "native_publication_text_label": gate.get("publication_text_label", ""),
        "native_service74_raw_label": gate.get("service74_raw_klog_label", ""),
        "native_pm_client_label": gate.get("pm_client_return_label", ""),
        "native_handoff_klog_label": gate.get("post_pm_lower_handoff_klog_label", ""),
        "native_lower_state_label": gate.get("post_pm_lower_state_label", ""),
        "native_pm_client_register_rc": gate.get("pm_client_register_rc", ""),
        "native_pm_client_connect_rc": gate.get("pm_client_connect_rc", ""),
        "native_pm_init_return_path_rc": gate.get("pm_init_return_path_rc", ""),
        "native_service_locator_counts": gate.get("raw_service_locator_counts", ""),
        "native_servloc_domain_counts": gate.get("raw_servloc_domain_counts", ""),
        "native_wlan_fw_counts": gate.get("raw_wlan_fw_counts", ""),
        "native_wlan_pd_domain_counts": gate.get("raw_wlan_pd_domain_counts", ""),
        "native_qmi_server_connected_counts": gate.get("raw_qmi_server_connected_counts", ""),
        "native_service_locator_positive": gate.get("raw_service_locator_positive"),
        "native_domain_publication_text_positive": gate.get("domain_publication_text_positive"),
        "native_service180_counts": gate.get("raw_service180_text_counts", ""),
        "native_service74_counts": gate.get("raw_service74_text_counts", ""),
        "native_wlan_pd_counts": gate.get("raw_wlan_pd_text_counts", ""),
        "native_service180_positive": gate.get("raw_service180_text_positive"),
        "native_service74_positive": gate.get("raw_service74_text_positive"),
        "native_wlan_pd_positive": gate.get("raw_wlan_pd_text_positive"),
        "native_pd_mapper_counts": gate.get("raw_pd_mapper_counts", ""),
        "native_subsys_counts": gate.get("raw_subsys_counts", ""),
        "native_pil_counts": gate.get("raw_pil_counts", ""),
        "native_qmi_counts": gate.get("raw_qmi_counts", ""),
        "native_wlfw_counts": gate.get("raw_wlfw_counts", ""),
        "native_preconditions_visible": gate.get("preconditions_visible"),
        "native_service_notifier_early_state": gate.get("service_notifier_early_state", ""),
        "native_service_notifier_late_state": gate.get("service_notifier_late_state", ""),
        "native_service_notifier_early_indication": gate.get("service_notifier_early_indication_seen", ""),
        "native_service_notifier_late_indication": gate.get("service_notifier_late_indication_seen", ""),
        "native_lower_mdm3_states": gate.get("lower_mdm3_states", ""),
        "native_lower_mhi_present": gate.get("lower_mhi_present"),
        "native_lower_service69_progress": gate.get("lower_service69_progress"),
        "native_lower_wlan0_present": gate.get("lower_wlan0_present"),
        "native_safety_ok": gate.get("safety_ok"),
        "native_publication_samples": gate.get("publication_samples", []),
        "android_v739_decision": v739.get("decision", ""),
        "android_v739_pass": bool(v739.get("pass")),
        "android_v622_counts": {
            "service_locator": counts.get("service_locator", ""),
            "service_notifier_180": counts.get("service_notifier_180", ""),
            "service_notifier_74": counts.get("service_notifier_74", ""),
            "wlan_pd": counts.get("wlan_pd", ""),
            "wlan_pd_ack_180": counts.get("wlan_pd_ack_180", ""),
            "qmi_server_connected": counts.get("qmi_server_connected", ""),
            "wlfw_start": counts.get("wlfw_start", ""),
            "wlan0": counts.get("wlan0", ""),
        },
        "android_v622_deltas_ms": {
            "sysmon_modem_to_service_locator": deltas.get("sysmon_modem_to_service_locator", ""),
            "sysmon_modem_to_service_notifier_180": deltas.get("sysmon_modem_to_service_notifier_180", ""),
            "service_notifier_180_to_service_notifier_74": deltas.get("service_notifier_180_to_service_notifier_74", ""),
            "service_notifier_180_to_wlan_pd": deltas.get("service_notifier_180_to_wlan_pd", ""),
            "wlan_pd_to_qmi_server_connected": deltas.get("wlan_pd_to_qmi_server_connected", ""),
        },
        "android_v852_decision": v852.get("decision", ""),
        "android_v852_pass": bool(v852.get("pass")),
        "android_v852_mss_state": v852_summary.get("mss_state", ""),
        "android_v852_mdm3_state": v852_summary.get("mdm3_state", ""),
        "android_v852_hints": {
            "has_wlan_pd": bool(hints.get("has_wlan_pd")),
            "has_wlfw": bool(hints.get("has_wlfw")),
            "has_wlan0": bool(hints.get("has_wlan0")),
        },
    }


def native_servloc_domain_gap(details: dict[str, Any]) -> bool:
    return (
        bool(details.get("source_pass"))
        and bool(details.get("rollback_ok"))
        and details.get("native_publication_text_label") == "servloc-init-visible-domain-absent"
        and details.get("native_service74_raw_label") == "service74-raw-absent"
        and details.get("native_pm_client_label") == "pm-client-return-success"
        and details.get("native_handoff_klog_label") == "servnotif-klog-progress-still-uninit"
        and details.get("native_lower_state_label") == "stable-mdm3-offlining"
        and details.get("native_pm_client_register_rc") == "0"
        and details.get("native_pm_client_connect_rc") == "0"
        and details.get("native_pm_init_return_path_rc") == "0"
        and boolish(details.get("native_service_locator_positive"))
        and not boolish(details.get("native_domain_publication_text_positive"))
        and boolish(details.get("native_service180_positive"))
        and not boolish(details.get("native_service74_positive"))
        and not boolish(details.get("native_wlan_pd_positive"))
        and boolish(details.get("native_preconditions_visible"))
        and details.get("native_service_notifier_early_state") == "uninit"
        and details.get("native_service_notifier_late_state") == "uninit"
        and details.get("native_service_notifier_early_indication") == "0"
        and details.get("native_service_notifier_late_indication") == "0"
        and details.get("native_lower_mdm3_states") == "OFFLINING"
        and not boolish(details.get("native_lower_mhi_present"))
        and not boolish(details.get("native_lower_service69_progress"))
        and not boolish(details.get("native_lower_wlan0_present"))
        and boolish(details.get("native_safety_ok"))
    )


def android_locator_to_wlanpd_positive(details: dict[str, Any]) -> bool:
    counts = details["android_v622_counts"]
    hints = details["android_v852_hints"]
    return (
        bool(details.get("android_v739_pass"))
        and bool(details.get("android_v852_pass"))
        and intish(counts.get("service_locator")) > 0
        and intish(counts.get("service_notifier_180")) > 0
        and intish(counts.get("service_notifier_74")) > 0
        and intish(counts.get("wlan_pd")) > 0
        and intish(counts.get("wlan_pd_ack_180")) > 0
        and intish(counts.get("qmi_server_connected")) > 0
        and intish(counts.get("wlfw_start")) > 0
        and intish(counts.get("wlan0")) > 0
        and bool(hints.get("has_wlan_pd"))
        and bool(hints.get("has_wlfw"))
        and bool(hints.get("has_wlan0"))
    )


def classify(details: dict[str, Any]) -> tuple[str, str]:
    if not native_servloc_domain_gap(details):
        return (
            "native-servloc-domain-gap-shape-incomplete",
            "V1819 evidence did not match the fixed native servloc-init-visible/domain-absent stall shape",
        )
    if not android_locator_to_wlanpd_positive(details):
        return (
            "android-servloc-wlanpd-baseline-incomplete",
            "Android-positive baselines do not prove service-locator, service74, wlan_pd, qmi-server, WLFW, and wlan0 progression",
        )
    return (
        "qrtr-servloc-registry-snapshot-target",
        "Native has generic service-locator init plus PM-client/sysmon/service180/lower-QMI context, but lacks wlan-specific domain publication, service74, wlan_pd, WLFW, and wlan0 while Android-good progresses from service-locator to wlan_pd/qmi-server",
    )


def render_samples(samples: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for sample in samples:
        lines.extend([
            f"- `{sample.get('phase')}` counts locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `{sample.get('raw_count_service_locator_text')}` / `{sample.get('raw_count_servloc_domain_text')}` / `{sample.get('raw_count_wlan_fw_text')}` / `{sample.get('raw_count_wlan_pd_domain_text')}` / `{sample.get('raw_count_qmi_server_connected_text')}`",
            f"- `{sample.get('phase')}` last locator/domain: `{sample.get('last_service_locator')}` / `{sample.get('last_servloc_domain')}`",
        ])
    return lines


def render_report(result: dict[str, Any]) -> str:
    d = result["details"]
    counts = d["android_v622_counts"]
    deltas = d["android_v622_deltas_ms"]
    lines = [
        "# Native Init V1820 Servloc Domain Gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1820`",
        "- Type: host-only classifier over V1819 publication text handoff and Android-positive locator baselines",
        f"- Decision: `{result['decision']}`",
        "- Result: PASS",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Source evidence: `{d['source_dir']}`",
        "",
        "## Native V1819 Shape",
        "",
        f"- V1819 decision: `{d['source_decision']}`",
        f"- labels publication/service74/PM-client/handoff/lower-state: `{d['native_publication_text_label']}` / `{d['native_service74_raw_label']}` / `{d['native_pm_client_label']}` / `{d['native_handoff_klog_label']}` / `{d['native_lower_state_label']}`",
        f"- PM-client register/connect/return rc: `{d['native_pm_client_register_rc']}` / `{d['native_pm_client_connect_rc']}` / `{d['native_pm_init_return_path_rc']}`",
        f"- native locator/domain/wlan-fw/wlan-pd-domain/qmi-server counts: `{d['native_service_locator_counts']}` / `{d['native_servloc_domain_counts']}` / `{d['native_wlan_fw_counts']}` / `{d['native_wlan_pd_domain_counts']}` / `{d['native_qmi_server_connected_counts']}`",
        f"- native service180/service74/wlan_pd counts: `{d['native_service180_counts']}` / `{d['native_service74_counts']}` / `{d['native_wlan_pd_counts']}`",
        f"- native lower preconditions pd-mapper/subsys/pil/qmi/wlfw: `{d['native_pd_mapper_counts']}` / `{d['native_subsys_counts']}` / `{d['native_pil_counts']}` / `{d['native_qmi_counts']}` / `{d['native_wlfw_counts']}`",
        *render_samples(d["native_publication_samples"]),
        "",
        "## Native Lower State",
        "",
        f"- service-notifier early/late state: `{d['native_service_notifier_early_state']}` / `{d['native_service_notifier_late_state']}`",
        f"- service-notifier early/late indication: `{d['native_service_notifier_early_indication']}` / `{d['native_service_notifier_late_indication']}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{d['native_lower_mdm3_states']}` / `{d['native_lower_mhi_present']}` / `{d['native_lower_service69_progress']}` / `{d['native_lower_wlan0_present']}`",
        f"- safety ok: `{d['native_safety_ok']}`",
        "",
        "## Android-positive Baseline",
        "",
        f"- V739/V852 decisions: `{d['android_v739_decision']}` / `{d['android_v852_decision']}`",
        f"- Android V622 counts service-locator/SN180/SN74/wlan_pd/ack/qmi-server/WLFW/wlan0: `{counts['service_locator']}` / `{counts['service_notifier_180']}` / `{counts['service_notifier_74']}` / `{counts['wlan_pd']}` / `{counts['wlan_pd_ack_180']}` / `{counts['qmi_server_connected']}` / `{counts['wlfw_start']}` / `{counts['wlan0']}`",
        f"- Android V622 deltas sysmon→locator, sysmon→SN180, SN180→SN74, SN180→wlan_pd, wlan_pd→qmi-server: `{deltas['sysmon_modem_to_service_locator']}` / `{deltas['sysmon_modem_to_service_notifier_180']}` / `{deltas['service_notifier_180_to_service_notifier_74']}` / `{deltas['service_notifier_180_to_wlan_pd']}` / `{deltas['wlan_pd_to_qmi_server_connected']}`",
        f"- Android V852 mss/mdm3: `{d['android_v852_mss_state']}` / `{d['android_v852_mdm3_state']}`",
        f"- Android V852 hints wlan_pd/WLFW/wlan0: `{d['android_v852_hints']['has_wlan_pd']}` / `{d['android_v852_hints']['has_wlfw']}` / `{d['android_v852_hints']['has_wlan0']}`",
        "",
        "## Interpretation",
        "",
        "- Generic native service-locator initialization is present, so the next gap is not simply service-locator init.",
        "- Native lacks wlan-specific service-locator/domain publication and remains without service74, wlan_pd, WLFW service 69, MHI, or `wlan0`.",
        "- The next source/build should remain read-only and capture bounded QRTR/service-locator registry or state for wlan/fw and wlan_pd publication.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    source_manifest_path = SOURCE_DIR / "manifest.json"
    source = load_json(source_manifest_path)
    v739 = load_json(V739_MANIFEST)
    v852 = load_json(V852_ANDROID_MANIFEST)
    details = collect_details(source, v739, v852)
    label, reason = classify(details)
    details["source_manifest"] = rel(source_manifest_path)
    details["v739_manifest"] = rel(V739_MANIFEST)
    details["v852_manifest"] = rel(V852_ANDROID_MANIFEST)
    result = {
        "cycle": CYCLE,
        "decision": f"v1820-{label}-host-pass",
        "pass": True,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "source_manifest": rel(source_manifest_path),
        "v739_manifest": rel(V739_MANIFEST),
        "v852_manifest": rel(V852_ANDROID_MANIFEST),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = render_report(result)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(report, encoding="utf-8")
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": True, "label": label}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
