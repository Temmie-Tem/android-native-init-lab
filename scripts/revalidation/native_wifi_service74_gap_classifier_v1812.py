#!/usr/bin/env python3
"""V1812 host-only classifier for native service-notifier 74 gap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1812"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1811-post-pm-lower-handoff-klog-handoff"
V739_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v739-mdm3-wlanpd-delta" / "manifest.json"
V852_ANDROID_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v852-android-ext-mdm-provider-surface-handoff"
    / "v852-android-ext-mdm-provider-surface-run"
    / "manifest.json"
)
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1812-service74-gap-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1812_SERVICE74_GAP_CLASSIFIER_2026-06-03.md"
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
    return {
        "source_dir": rel(SOURCE_DIR),
        "source_decision": source.get("decision", ""),
        "source_pass": bool(source.get("pass")),
        "source_reason": source.get("reason", ""),
        "rollback_ok": source.get("rollback", {}).get("ok"),
        "native_klog_label": gate.get("post_pm_lower_handoff_klog_label", ""),
        "native_pm_client_label": gate.get("pm_client_return_label", ""),
        "native_lower_state_label": gate.get("post_pm_lower_state_label", ""),
        "native_pm_client_register_rc": gate.get("pm_client_register_rc", ""),
        "native_pm_client_connect_rc": gate.get("pm_client_connect_rc", ""),
        "native_pm_init_return_path_rc": gate.get("pm_init_return_path_rc", ""),
        "native_klog_contract_ok": gate.get("klog_contract_ok"),
        "native_klog_safety_ok": gate.get("klog_safety_ok"),
        "native_sysmon_counts": gate.get("klog_sysmon_qmi_counts", ""),
        "native_service180_counts": gate.get("klog_service180_counts", ""),
        "native_service74_counts": gate.get("klog_service74_counts", ""),
        "native_sysmon_positive": gate.get("klog_sysmon_qmi_positive"),
        "native_service180_positive": gate.get("klog_service180_positive"),
        "native_service74_positive": gate.get("klog_service74_positive"),
        "native_any_increased": gate.get("klog_any_increased"),
        "native_service_notifier_early_state": gate.get("service_notifier_early_state", ""),
        "native_service_notifier_late_state": gate.get("service_notifier_late_state", ""),
        "native_service_notifier_early_indication": gate.get("service_notifier_early_indication_seen", ""),
        "native_service_notifier_late_indication": gate.get("service_notifier_late_indication_seen", ""),
        "native_lower_mdm3_states": gate.get("lower_mdm3_states", ""),
        "native_lower_mhi_present": gate.get("lower_mhi_present"),
        "native_lower_service69_progress": gate.get("lower_service69_progress"),
        "native_lower_wlan0_present": gate.get("lower_wlan0_present"),
        "native_safety_ok": gate.get("safety_ok"),
        "native_klog_samples": gate.get("klog_samples", []),
        "android_v739_decision": v739.get("decision", ""),
        "android_v739_pass": bool(v739.get("pass")),
        "android_v622_counts": {
            "service_notifier_180": counts.get("service_notifier_180", ""),
            "service_notifier_74": counts.get("service_notifier_74", ""),
            "wlan_pd": counts.get("wlan_pd", ""),
            "wlan_pd_ack_180": counts.get("wlan_pd_ack_180", ""),
            "wlfw_start": counts.get("wlfw_start", ""),
            "qmi_server_connected": counts.get("qmi_server_connected", ""),
        },
        "android_v622_deltas_ms": {
            "sysmon_modem_to_service_notifier_180": deltas.get("sysmon_modem_to_service_notifier_180", ""),
            "service_notifier_180_to_wlan_pd": deltas.get("service_notifier_180_to_wlan_pd", ""),
            "service_notifier_180_to_wlfw_start": deltas.get("service_notifier_180_to_wlfw_start", ""),
            "wlan_pd_to_qmi_server_connected": deltas.get("wlan_pd_to_qmi_server_connected", ""),
        },
        "android_v852_decision": v852.get("decision", ""),
        "android_v852_pass": bool(v852.get("pass")),
        "android_v852_mss_state": v852_summary.get("mss_state", ""),
        "android_v852_mdm3_state": v852_summary.get("mdm3_state", ""),
        "android_v852_hints": {
            "has_wlan_pd": bool(v852_summary.get("dmesg_hints", {}).get("has_wlan_pd")),
            "has_wlfw": bool(v852_summary.get("dmesg_hints", {}).get("has_wlfw")),
            "has_wlan0": bool(v852_summary.get("dmesg_hints", {}).get("has_wlan0")),
        },
    }


def android_positive(details: dict[str, Any]) -> bool:
    counts = details["android_v622_counts"]
    hints = details["android_v852_hints"]
    return (
        bool(details.get("android_v739_pass"))
        and bool(details.get("android_v852_pass"))
        and intish(counts.get("service_notifier_180")) > 0
        and intish(counts.get("service_notifier_74")) > 0
        and intish(counts.get("wlan_pd")) > 0
        and intish(counts.get("wlfw_start")) > 0
        and intish(counts.get("qmi_server_connected")) > 0
        and details.get("android_v852_mdm3_state") == "ONLINE"
        and bool(hints.get("has_wlan_pd"))
        and bool(hints.get("has_wlfw"))
        and bool(hints.get("has_wlan0"))
    )


def native_service74_gap(details: dict[str, Any]) -> bool:
    return (
        bool(details.get("source_pass"))
        and bool(details.get("rollback_ok"))
        and details.get("native_klog_label") == "servnotif-klog-progress-still-uninit"
        and details.get("native_pm_client_label") == "pm-client-return-success"
        and details.get("native_pm_client_register_rc") == "0"
        and details.get("native_pm_client_connect_rc") == "0"
        and details.get("native_pm_init_return_path_rc") == "0"
        and boolish(details.get("native_klog_contract_ok"))
        and boolish(details.get("native_klog_safety_ok"))
        and boolish(details.get("native_sysmon_positive"))
        and boolish(details.get("native_service180_positive"))
        and not boolish(details.get("native_service74_positive"))
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


def classify(details: dict[str, Any]) -> tuple[str, str]:
    if not native_service74_gap(details):
        return (
            "native-service74-gap-shape-incomplete",
            "V1811 evidence did not match the fixed native service180-present/service74-absent uninit stall shape",
        )
    if not android_positive(details):
        return (
            "android-service74-positive-baseline-incomplete",
            "Android-positive baselines do not prove service-notifier 74, wlan_pd, WLFW, and wlan0 progression",
        )
    return (
        "native-service180-present-service74-absent-uninit",
        "Native reaches PM-client success, sysmon_qmi, and service-notifier 180 klog publication, but service-notifier 74 stays absent and QRTR listener state remains uninit while Android-good reaches service 74, wlan_pd, WLFW, and wlan0",
    )


def render_klog_samples(samples: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for sample in samples:
        lines.extend([
            f"- `{sample.get('phase')}` counts sysmon/180/74: `{sample.get('count_sysmon_qmi')}` / `{sample.get('count_180')}` / `{sample.get('count_74')}`",
            f"- `{sample.get('phase')}` last service74: `{sample.get('last_74')}`",
        ])
    return lines


def render_report(result: dict[str, Any]) -> str:
    d = result["details"]
    counts = d["android_v622_counts"]
    deltas = d["android_v622_deltas_ms"]
    lines = [
        "# Native Init V1812 Service-notifier 74 Gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1812`",
        "- Type: host-only classifier over V1811 klog handoff and Android-positive service-notifier baselines",
        f"- Decision: `{result['decision']}`",
        "- Result: PASS",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Source evidence: `{d['source_dir']}`",
        "",
        "## Native V1811 Shape",
        "",
        f"- V1811 decision: `{d['source_decision']}`",
        f"- labels klog/PM-client/lower-state: `{d['native_klog_label']}` / `{d['native_pm_client_label']}` / `{d['native_lower_state_label']}`",
        f"- PM-client register/connect/return rc: `{d['native_pm_client_register_rc']}` / `{d['native_pm_client_connect_rc']}` / `{d['native_pm_init_return_path_rc']}`",
        f"- klog contract/safety: `{d['native_klog_contract_ok']}` / `{d['native_klog_safety_ok']}`",
        f"- klog sysmon/180/74 counts: `{d['native_sysmon_counts']}` / `{d['native_service180_counts']}` / `{d['native_service74_counts']}`",
        f"- klog any increased: `{d['native_any_increased']}`",
        *render_klog_samples(d["native_klog_samples"]),
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
        f"- Android V622 counts SN180/SN74/wlan_pd/ack/WLFW/qmi-server: `{counts['service_notifier_180']}` / `{counts['service_notifier_74']}` / `{counts['wlan_pd']}` / `{counts['wlan_pd_ack_180']}` / `{counts['wlfw_start']}` / `{counts['qmi_server_connected']}`",
        f"- Android V622 deltas sysmon→SN180, SN180→wlan_pd, SN180→WLFW, wlan_pd→qmi-server: `{deltas['sysmon_modem_to_service_notifier_180']}` / `{deltas['service_notifier_180_to_wlan_pd']}` / `{deltas['service_notifier_180_to_wlfw_start']}` / `{deltas['wlan_pd_to_qmi_server_connected']}`",
        f"- Android V852 mss/mdm3: `{d['android_v852_mss_state']}` / `{d['android_v852_mdm3_state']}`",
        f"- Android V852 hints wlan_pd/WLFW/wlan0: `{d['android_v852_hints']['has_wlan_pd']}` / `{d['android_v852_hints']['has_wlfw']}` / `{d['android_v852_hints']['has_wlan0']}`",
        "",
        "## Interpretation",
        "",
        "- The remaining native gap is no longer PM-client return or service-notifier 180 publication.",
        "- Native has service-notifier 180 in klog before the first post-PM lower sample, but service-notifier 74 remains absent across the V1811 window.",
        "- Android-good evidence includes service-notifier 74, wlan_pd, WLFW, and `wlan0`; native remains `uninit` with no indication and no WLFW service 69.",
        "- Next work should distinguish missing service-notifier 74 publication from a parser/visibility miss using read-only evidence before any actor expansion.",
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
        "decision": f"v1812-{label}-host-pass",
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
