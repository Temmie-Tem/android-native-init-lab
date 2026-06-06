#!/usr/bin/env python3
"""V1886 host-only classifier for servloc-present versus WLAN-PD state-up."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1886-internal-servloc-msg22-stateup-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1886_INTERNAL_SERVLOC_MSG22_STATEUP_CLASSIFIER_2026-06-03.md"
)
DEFAULT_V1737_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1737-wlan-pd-start-trigger-classifier" / "manifest.json"
DEFAULT_V1834_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1834-qipcrtr-bound-recv-poll-handoff" / "manifest.json"
DEFAULT_V1834_REPORT = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1834_QIPCRTR_BOUND_RECV_POLL_HANDOFF_2026-06-03.md"
)
DEFAULT_V1885_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1885-internal-pm-qmi-servreg-trigger-source-diff" / "manifest.json"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def line_value(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.strip().startswith(prefix):
            return line.strip()
    return ""


def code_values(line: str) -> list[str]:
    return re.findall(r"`([^`]*)`", line)


def v1834_summary(manifest_path: Path, report_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    gate = manifest.get("gate") or {}
    report_text = read_text(report_path)
    domain_label_line = line_value(report_text, "- service-locator domain label:")
    endpoint_line = line_value(report_text, "- service-locator endpoint/status/result:")
    domain_line = line_value(report_text, "- service-locator domain/name/instance:")
    early_line = line_value(report_text, "- service-notifier early qmi/state/indication/result:")
    late_line = line_value(report_text, "- service-notifier late qmi/state/indication/result:")
    endpoint_values = code_values(endpoint_line)
    domain_values = code_values(domain_line)
    early_values = code_values(early_line)
    late_values = code_values(late_line)
    return {
        "manifest": rel(manifest_path),
        "report": rel(report_path),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "domain_label": (code_values(domain_label_line) or [""])[0],
        "endpoint_node": endpoint_values[0] if len(endpoint_values) > 0 else "",
        "endpoint_port": endpoint_values[1] if len(endpoint_values) > 1 else "",
        "endpoint_status": endpoint_values[2] if len(endpoint_values) > 2 else "",
        "endpoint_result": endpoint_values[3] if len(endpoint_values) > 3 else "",
        "domain_present": domain_values[0] if len(domain_values) > 0 else "",
        "domain_name": domain_values[1] if len(domain_values) > 1 else "",
        "domain_instance": domain_values[2] if len(domain_values) > 2 else "",
        "early_qmi": early_values[0] if len(early_values) > 0 else "",
        "early_state": early_values[1] if len(early_values) > 1 else gate.get("service_notifier_early_state", ""),
        "early_indication": early_values[2] if len(early_values) > 2 else "",
        "early_result": early_values[3] if len(early_values) > 3 else "",
        "late_qmi": late_values[0] if len(late_values) > 0 else "",
        "late_state": late_values[1] if len(late_values) > 1 else gate.get("service_notifier_late_state", ""),
        "late_indication": late_values[2] if len(late_values) > 2 else "",
        "late_result": late_values[3] if len(late_values) > 3 else "",
        "raw_service_locator_counts": gate.get("raw_service_locator_counts", ""),
        "raw_servloc_domain_counts": gate.get("raw_servloc_domain_counts", ""),
        "raw_service180_counts": gate.get("raw_service180_text_counts") or gate.get("klog_service180_counts", ""),
        "raw_service74_counts": gate.get("raw_service74_text_counts") or gate.get("klog_service74_counts", ""),
        "raw_wlan_pd_counts": gate.get("raw_wlan_pd_text_counts", ""),
        "wlfw_service69_seen": gate.get("wlfw_service69_seen", ""),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp", ""),
        "wlan0_present": gate.get("wlan0_present", ""),
    }


def v1885_summary(manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    source = manifest.get("source") or {}
    android = manifest.get("android_normal") or {}
    native = manifest.get("native_post_open") or {}
    return {
        "manifest": rel(manifest_path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": bool(manifest.get("pass")),
        "source_pm_msg22_dispatch": bool(source.get("pm_msgid_0x22_dispatch")),
        "source_pm_msg22_request_string": bool(source.get("pm_msg22_request_string")),
        "source_pm_msg22_response_call": bool(source.get("pm_msg22_response_call")),
        "source_pm_msg22_indication": bool(source.get("pm_post_ack_msg22_indication")),
        "source_pm_msg22_pending_slot": bool(source.get("pm_post_ack_pending_restart_client_slot")),
        "libperipheral_qmi_imports": bool(source.get("libperipheral_qmi_imports")),
        "android_pm_vote_time": android.get("pm_vote_first_time", ""),
        "android_wlfw_request_time": android.get("wlfw_service_request_first_time", ""),
        "android_wlanmdsp_time": android.get("wlanmdsp_first_time", ""),
        "android_wlan_pd_time_s": android.get("wlan_pd_indication_time_s"),
        "android_wlan0_time_s": android.get("wlan0_time_s"),
        "android_pcie_mhi_before_wlan0": intish(android.get("pcie_or_mhi_before_wlan0")),
        "android_msg22_log_hits": intish(android.get("pm_qmi_msg22_log_hits")),
        "android_msg22_observable": bool(android.get("pm_qmi_trace_observability")),
        "android_servnotif_line": android.get("servnotif_wlan_pd_line", ""),
        "android_wlfw_connected_line": android.get("wlfw_connected_line", ""),
        "native_pm_register_rc": native.get("pm_client_register_rc", ""),
        "native_pm_connect_rc": native.get("pm_client_connect_rc", ""),
        "native_open_path": native.get("open_context_path", ""),
        "native_open_fd": native.get("open_context_fd", ""),
        "native_open_state": native.get("open_context_power_state", ""),
        "native_post_ack_open_hits": intish(native.get("post_ack_open_call_hits")),
        "native_post_ack_msg22_hits": intish(native.get("post_ack_qmi_restart_ind_hits")),
        "native_wlfw_request_hits": intish(native.get("wlfw_service_request_hits")),
        "native_wlfw_ind_register_hits": intish(native.get("wlfw_ind_register_qmi_hits")),
        "native_wlfw_cap_hits": intish(native.get("wlfw_cap_qmi_hits")),
        "native_requested_wlanmdsp": native.get("requested_wlanmdsp", ""),
        "native_wlfw_service69": native.get("wlfw_service69_seen", ""),
        "native_wlan0": native.get("wlan0_present", ""),
        "native_early_state": native.get("early_servnotif_state", ""),
        "native_late_state": native.get("late_servnotif_state", ""),
    }


def v1737_summary(manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    return {
        "manifest": rel(manifest_path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": bool(manifest.get("pass")),
    }


def classify(v1737: dict[str, Any], v1834: dict[str, Any], v1885: dict[str, Any]) -> tuple[str, bool, str, str]:
    prior_start_gap = (
        v1737["pass"]
        and v1737["label"] == "modem-side-wlan-pd-start-trigger-gap"
    )
    servloc_domain_present = (
        v1834["pass"]
        and v1834["domain_label"] == "servloc-domain-wlan-pd-instance180"
        and v1834["domain_present"] == "1"
        and v1834["domain_name"] == "msm/modem/wlan_pd"
        and v1834["domain_instance"] == "180"
    )
    servnotif_uninit = (
        v1834["early_qmi"] == "1"
        and v1834["late_qmi"] == "1"
        and v1834["early_state"] == "uninit"
        and v1834["late_state"] == "uninit"
        and v1834["early_indication"] == "0"
        and v1834["late_indication"] == "0"
    )
    pm_msg22_source_mapped = (
        v1885["source_pm_msg22_dispatch"]
        and v1885["source_pm_msg22_request_string"]
        and v1885["source_pm_msg22_response_call"]
        and v1885["source_pm_msg22_indication"]
        and v1885["source_pm_msg22_pending_slot"]
        and not v1885["libperipheral_qmi_imports"]
    )
    android_normal_transition = (
        v1885["pass"]
        and v1885["android_pm_vote_time"]
        and v1885["android_wlfw_request_time"]
        and v1885["android_wlanmdsp_time"]
        and v1885["android_wlan_pd_time_s"] is not None
        and v1885["android_pcie_mhi_before_wlan0"] == 0
    )
    native_post_open_still_uninit = (
        v1885["native_pm_register_rc"] == "0"
        and v1885["native_pm_connect_rc"] == "0"
        and v1885["native_open_path"] == "/dev/subsys_modem"
        and v1885["native_post_ack_open_hits"] > 0
        and v1885["native_post_ack_msg22_hits"] == 0
        and v1885["native_wlfw_request_hits"] > 0
        and v1885["native_wlfw_ind_register_hits"] == 0
        and v1885["native_wlfw_cap_hits"] == 0
        and v1885["native_requested_wlanmdsp"] == "0"
        and v1885["native_wlfw_service69"] == "0"
        and v1885["native_wlan0"] == "0"
        and v1885["native_early_state"] == "uninit"
        and v1885["native_late_state"] == "uninit"
    )
    if not prior_start_gap:
        return (
            "v1886-prior-internal-start-gap-missing",
            False,
            "prior internal-modem WLAN-PD start-gap label is missing",
            "prior-start-gap-missing",
        )
    if not servloc_domain_present:
        return (
            "v1886-servloc-domain-evidence-incomplete",
            False,
            "retained service-locator domain-list evidence does not prove msm/modem/wlan_pd instance 180",
            "servloc-domain-incomplete",
        )
    if not servnotif_uninit:
        return (
            "v1886-servnotif-state-evidence-mismatch",
            False,
            "retained service-notifier listener evidence does not prove early/late uninit with no indication",
            "servnotif-state-mismatch",
        )
    if not pm_msg22_source_mapped:
        return (
            "v1886-pm-msg22-source-map-incomplete",
            False,
            "pm-service msg22 source map or libperipheral Binder-only split is incomplete",
            "pm-msg22-source-map-incomplete",
        )
    if not android_normal_transition:
        return (
            "v1886-android-normal-stateup-window-incomplete",
            False,
            "normal Android retained window does not prove PM vote to WLAN-PD state-up to wlanmdsp without PCIe/MHI",
            "android-normal-stateup-window-incomplete",
        )
    if not native_post_open_still_uninit:
        return (
            "v1886-native-post-open-stateup-gap-mismatch",
            False,
            "native post-open retained state no longer matches the expected no-msg22/no-WLFW/no-wlanmdsp gap",
            "native-post-open-stateup-gap-mismatch",
        )
    return (
        "v1886-servloc-present-msg22-stateup-missing-host-pass",
        True,
        "native already resolves the internal WLAN-PD service-locator domain and PM/open succeeds, so discovery is not the trigger; the missing edge is the post-PM msg22/servreg state-up transition that Android normal reaches before wlanmdsp",
        "servloc-domain-present-msg22-stateup-missing",
    )


def render_report(result: dict[str, Any]) -> str:
    v1737 = result["v1737_prior"]
    v1834 = result["v1834_servloc"]
    v1885 = result["v1885_msg22"]
    return "\n".join(
        [
            "# Native Init V1886 Internal Servloc/msg22 State-up Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1886`",
            "- Type: host-only reconciliation classifier for internal-modem WLAN-PD discovery versus state-up",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Reconciled Inputs",
            "",
            f"- V1737 prior decision/label/pass: `{v1737['decision']}` / `{v1737['label']}` / `{v1737['pass']}`",
            f"- V1834 decision/pass: `{v1834['decision']}` / `{v1834['pass']}`",
            f"- V1885 decision/label/pass: `{v1885['decision']}` / `{v1885['label']}` / `{v1885['pass']}`",
            "",
            "## Service-locator Is Not The Trigger",
            "",
            f"- Domain label: `{v1834['domain_label']}`",
            f"- service-locator endpoint/status/result: `{v1834['endpoint_node']}`:`{v1834['endpoint_port']}` / `{v1834['endpoint_status']}` / `{v1834['endpoint_result']}`",
            f"- service-locator domain/name/instance: `{v1834['domain_present']}` / `{v1834['domain_name']}` / `{v1834['domain_instance']}`",
            f"- service-notifier early qmi/state/indication/result: `{v1834['early_qmi']}` / `{v1834['early_state']}` / `{v1834['early_indication']}` / `{v1834['early_result']}`",
            f"- service-notifier late qmi/state/indication/result: `{v1834['late_qmi']}` / `{v1834['late_state']}` / `{v1834['late_indication']}` / `{v1834['late_result']}`",
            f"- raw service-locator/servloc-domain/service180/service74/wlan_pd counts: `{v1834['raw_service_locator_counts']}` / `{v1834['raw_servloc_domain_counts']}` / `{v1834['raw_service180_counts']}` / `{v1834['raw_service74_counts']}` / `{v1834['raw_wlan_pd_counts']}`",
            "",
            "## Msg22/State-up Edge",
            "",
            f"- pm-service msg22 dispatch/request/response/indication/pending-slot: `{v1885['source_pm_msg22_dispatch']}` / `{v1885['source_pm_msg22_request_string']}` / `{v1885['source_pm_msg22_response_call']}` / `{v1885['source_pm_msg22_indication']}` / `{v1885['source_pm_msg22_pending_slot']}`",
            f"- libperipheral QMI imports: `{v1885['libperipheral_qmi_imports']}`",
            f"- Android PM vote / WLFW request / wlanmdsp times: `{v1885['android_pm_vote_time']}` / `{v1885['android_wlfw_request_time']}` / `{v1885['android_wlanmdsp_time']}`",
            f"- Android wlan_pd / wlan0 seconds and PCIe/MHI-before-wlan0: `{v1885['android_wlan_pd_time_s']}` / `{v1885['android_wlan0_time_s']}` / `{v1885['android_pcie_mhi_before_wlan0']}`",
            f"- Android retained msg22 log hits / observable: `{v1885['android_msg22_log_hits']}` / `{v1885['android_msg22_observable']}`",
            f"- Native PM register/connect/open: `{v1885['native_pm_register_rc']}` / `{v1885['native_pm_connect_rc']}` / `{v1885['native_open_path']}` fd `{v1885['native_open_fd']}` state `{v1885['native_open_state']}`",
            f"- Native post-ack open/msg22-ind hits: `{v1885['native_post_ack_open_hits']}` / `{v1885['native_post_ack_msg22_hits']}`",
            f"- Native WLFW request/ind-register/cap hits: `{v1885['native_wlfw_request_hits']}` / `{v1885['native_wlfw_ind_register_hits']}` / `{v1885['native_wlfw_cap_hits']}`",
            f"- Native wlanmdsp/WLFW69/wlan0 and states: `{v1885['native_requested_wlanmdsp']}` / `{v1885['native_wlfw_service69']}` / `{v1885['native_wlan0']}` / `{v1885['native_early_state']}` -> `{v1885['native_late_state']}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- Native already has the internal `msm/modem/wlan_pd` service-locator domain response for instance `180`, so the remaining blocker is not domain discovery.",
            "- Native PM register/connect succeeds and pm-service opens `/dev/subsys_modem`, but the post-ack msg22 indication path stays at zero and service-notifier remains `uninit`.",
            "- Android normal reaches PM vote, WLAN-PD state indication, WLFW connection, `wlanmdsp.mbn`, and `wlan0` with zero PCIe/MHI contamination; retained Android logs still lack pm-service msg-id observability.",
            "- The next live comparison must trace pm-service QMI msg IDs plus service-locator/service-notifier/SSCTL across the normal Android PM-vote to `wlanmdsp` window, then the same native post-open window.",
            "",
            "## Safety Scope",
            "",
            "V1886 is host-only. It reads retained manifests/reports and writes local classifier artifacts only. It performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.",
            "",
            "## Next",
            "",
            "- Capture only a normal Android boot window, not the degraded 257s boot: PM vote through first `wlanmdsp.mbn` request.",
            "- Required read-only signals: pm-service QMI msg `0x20/0x21/0x22` request/response/indication, service-locator domain-list, service-notifier state/indication/ACK, SSCTL, tftp `wlanmdsp.mbn`, and absence of PCIe/MHI before `wlan0`.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1737-manifest", type=Path, default=DEFAULT_V1737_MANIFEST)
    parser.add_argument("--v1834-manifest", type=Path, default=DEFAULT_V1834_MANIFEST)
    parser.add_argument("--v1834-report", type=Path, default=DEFAULT_V1834_REPORT)
    parser.add_argument("--v1885-manifest", type=Path, default=DEFAULT_V1885_MANIFEST)
    args = parser.parse_args()

    EvidenceStore(args.out_dir)
    v1737 = v1737_summary(args.v1737_manifest)
    v1834 = v1834_summary(args.v1834_manifest, args.v1834_report)
    v1885 = v1885_summary(args.v1885_manifest)
    decision, passed, reason, label = classify(v1737, v1834, v1885)
    result = {
        "cycle": "V1886",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "v1737_prior": v1737,
        "v1834_servloc": v1834,
        "v1885_msg22": v1885,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credential_use": False,
            "dhcp_routes": False,
            "external_ping": False,
            "pmic_gpio_gdsc_write": False,
            "forced_rc1_case": False,
            "subsys_esoc0_open": False,
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
