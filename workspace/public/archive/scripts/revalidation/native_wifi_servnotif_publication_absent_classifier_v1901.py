#!/usr/bin/env python3
"""V1901 host-only classifier for missing WLAN-PD service publication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1901"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1901-servnotif-publication-absent-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1901_SERVNOTIF_PUBLICATION_ABSENT_CLASSIFIER_2026-06-03.md"
)
LATEST_POINTER = REPO_ROOT / "tmp" / "wifi" / "latest-v1901-servnotif-publication-absent-classifier.txt"

DEFAULT_V1900_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1900-cnss-worker-servnotif-stateup-delta-classifier" / "manifest.json"
)
DEFAULT_V1898_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1898-servnotif-stateup-not-msg22-classifier" / "manifest.json"
DEFAULT_V1834_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1834-qipcrtr-bound-recv-poll-handoff" / "manifest.json"
DEFAULT_V1803_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1803-wlfw-qmi-readiness-classifier" / "manifest.json"
DEFAULT_V1819_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1819-publication-text-handoff" / "manifest.json"
DEFAULT_V1836_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1836-wlan-pd-uninit-transition-classifier" / "manifest.json"


def rel(path: Path | str) -> str:
    candidate = Path(path)
    try:
        return str(candidate.resolve().relative_to(REPO_ROOT))
    except (OSError, ValueError):
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except (TypeError, ValueError):
        return 0


def positive_count_list(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and any(intish(part) > 0 for part in parts)


def zero_count_list(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and all(intish(part) == 0 for part in parts)


def nested(data: dict[str, Any], *keys: str, default: object = "") -> object:
    value: object = data
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key, default)
    return value


def v1900_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    android = manifest.get("android_v1899") or {}
    native = manifest.get("native_latest_post_open") or {}
    return {
        "manifest": rel(path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": boolish(manifest.get("pass")),
        "android_requested_wlanmdsp": str(android.get("requested_wlanmdsp", "")),
        "android_wlan_pd_count": intish(android.get("wlan_pd_indication_count")),
        "android_wlanmdsp_count": intish(android.get("wlanmdsp_count")),
        "android_wlan0_time_s": android.get("wlan0_time_s"),
        "android_pcie_mhi_before_wlan0": intish(android.get("pcie_mhi_before_wlan0")),
        "android_degraded_257s_like": boolish(android.get("degraded_257s_like")),
        "native_service180_counts": str(native.get("service180_counts", "")),
        "native_service74_counts": str(native.get("service74_counts", "")),
        "native_wlan_pd_counts": str(native.get("wlan_pd_counts", "")),
        "native_servnotif_late_state": str(native.get("late_servnotif_state", "")),
        "native_wlfw_service69_seen": str(native.get("wlfw_service69_seen", "")),
        "native_requested_wlanmdsp": str(native.get("requested_wlanmdsp", "")),
        "native_wlan0_present": str(native.get("wlan0_present", "")),
    }


def v1898_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    android = manifest.get("android") or {}
    native = manifest.get("native") or {}
    return {
        "manifest": rel(path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": boolish(manifest.get("pass")),
        "android_ordered_internal_stateup": boolish(android.get("ordered_internal_stateup")),
        "android_service180_count": intish(android.get("service180_count")),
        "android_service74_count": intish(android.get("service74_count")),
        "android_wlan_pd_count": intish(android.get("wlan_pd_count")),
        "android_wlanmdsp_count": intish(android.get("wlanmdsp_count")),
        "android_wlan0_time_s": android.get("wlan0_time_s"),
        "android_pcie_mhi_before_wlan0": intish(android.get("pcie_mhi_before_wlan0")),
        "android_degraded_257s_like": boolish(android.get("degraded_257s_like")),
        "android_pm_msg22_hits": intish(android.get("pm_msg22_hits")),
        "native_service180_counts": str(native.get("v1885_service180_counts", "")),
        "native_service74_counts": str(native.get("v1816_service74_counts", "")),
        "native_wlan_pd_counts": str(native.get("v1885_wlan_pd_counts", "")),
        "native_early_servnotif_state": str(native.get("early_servnotif_state", "")),
        "native_late_servnotif_state": str(native.get("late_servnotif_state", "")),
        "native_wlfw_service69_seen": str(native.get("wlfw_service69_seen", "")),
        "native_requested_wlanmdsp": str(native.get("requested_wlanmdsp", "")),
        "native_wlan0_present": str(native.get("wlan0_present", "")),
        "subsys_esoc0_open": boolish(nested(manifest, "safety", "subsys_esoc0_open")),
    }


def v1834_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    gate = manifest.get("gate") or {}
    return {
        "manifest": rel(path),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "qipcrtr_label": str(gate.get("qipcrtr_bound_recv_label", "")),
        "qipcrtr_bound": boolish(gate.get("qipcrtr_bound_recv_bound")),
        "qipcrtr_port_nonzero": boolish(gate.get("qipcrtr_bound_recv_port_nonzero")),
        "qipcrtr_poll_timeout": boolish(gate.get("qipcrtr_bound_recv_poll_timeout")),
        "qipcrtr_recv_skip_reason": str(gate.get("qipcrtr_bound_recv_recv_skip_reason", "")),
        "qipcrtr_packet_received": boolish(gate.get("qipcrtr_bound_recv_packet_received")),
        "qipcrtr_no_connect": str(gate.get("qipcrtr_bound_recv_no_connect", "")),
        "qipcrtr_no_control": str(gate.get("qipcrtr_bound_recv_no_control_payload", "")),
        "qipcrtr_no_lookup_send": str(gate.get("qipcrtr_bound_recv_no_lookup_send", "")),
        "qipcrtr_no_send": str(gate.get("qipcrtr_bound_recv_no_send", "")),
        "qipcrtr_no_service_start": str(gate.get("qipcrtr_bound_recv_no_service_start", "")),
        "qrtr_registry_readable": boolish(gate.get("qrtr_registry_readable")),
        "qrtr_registry_wlan_pd_text_positive": boolish(gate.get("qrtr_registry_wlan_pd_text_positive")),
        "service180_counts": str(gate.get("raw_service180_text_counts", "")),
        "service74_counts": str(gate.get("raw_service74_text_counts", "")),
        "wlan_pd_counts": str(gate.get("raw_wlan_pd_text_counts", "")),
        "servnotif_early_state": str(gate.get("service_notifier_early_state", "")),
        "servnotif_late_state": str(gate.get("service_notifier_late_state", "")),
        "wlfw_service69_seen": str(gate.get("wlfw_service69_seen", "")),
        "requested_wlanmdsp": str(gate.get("requested_wlanmdsp", "")),
        "wlan0_present": str(gate.get("wlan0_present", "")),
    }


def v1803_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    details = manifest.get("details") or {}
    case_0 = details.get("qrtr_case_0") or {}
    case_1 = details.get("qrtr_case_1") or {}
    service_listener = details.get("service_notifier_listener") or {}
    late_listener = details.get("service_notifier_late_listener") or {}
    wlfw_request = details.get("wlfw_service_request") or {}
    ind_register = details.get("wlfw_ind_register_qmi") or {}
    cap_request = details.get("wlfw_cap_qmi") or {}
    return {
        "manifest": rel(path),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "qrtr_matrix": str(details.get("qrtr_matrix", "")),
        "qrtr_readback": str(details.get("qrtr_nameservice_readback", "")),
        "qrtr_case_0_service_events": intish(case_0.get("readback.service_events")),
        "qrtr_case_0_end_of_list": intish(case_0.get("readback.end_of_list")),
        "qrtr_case_1_service_events": intish(case_1.get("readback.service_events")),
        "qrtr_case_1_end_of_list": intish(case_1.get("readback.end_of_list")),
        "servnotif_early_state": str(service_listener.get("register_response.curr_state_name", "")),
        "servnotif_early_indication_seen": str(service_listener.get("indication_seen", "")),
        "servnotif_late_state": str(late_listener.get("register_response.curr_state_name", "")),
        "servnotif_late_indication_seen": str(late_listener.get("indication_seen", "")),
        "wlfw_service_request_hits": intish(wlfw_request.get("hit_count")),
        "wlfw_ind_register_hits": intish(ind_register.get("hit_count")),
        "wlfw_cap_hits": intish(cap_request.get("hit_count")),
        "wlfw_service69_seen": str(details.get("wlfw_service69_seen", "")),
        "requested_wlanmdsp": str(details.get("requested_wlanmdsp", "")),
        "wlan0_present": str(details.get("wlan0_present", "")),
    }


def v1819_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    gate = manifest.get("gate") or {}
    return {
        "manifest": rel(path),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "publication_text_label": str(gate.get("publication_text_label", "")),
        "publication_text_positive": boolish(gate.get("publication_text_positive")),
        "raw_service_locator_counts": str(gate.get("raw_service_locator_counts", "")),
        "raw_service180_counts": str(gate.get("raw_service180_text_counts", "")),
        "raw_service74_counts": str(gate.get("raw_service74_text_counts", "")),
        "raw_wlan_pd_counts": str(gate.get("raw_wlan_pd_text_counts", "")),
        "raw_wlan_pd_domain_counts": str(gate.get("raw_wlan_pd_domain_counts", "")),
        "raw_wlan_fw_counts": str(gate.get("raw_wlan_fw_counts", "")),
        "servnotif_early_state": str(gate.get("service_notifier_early_state", "")),
        "servnotif_late_state": str(gate.get("service_notifier_late_state", "")),
        "wlfw_service69_seen": str(gate.get("wlfw_service69_seen", "")),
        "requested_wlanmdsp": str(gate.get("requested_wlanmdsp", "")),
        "wlan0_present": str(gate.get("wlan0_present", "")),
    }


def v1836_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    current = nested(manifest, "details", "current", default={})
    if not isinstance(current, dict):
        current = {}
    return {
        "manifest": rel(path),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "qipcrtr_label": str(current.get("qipcrtr_label", "")),
        "qipcrtr_poll_timeout": str(current.get("qipcrtr_poll_timeout", "")),
        "qipcrtr_no_lookup": str(current.get("qipcrtr_no_lookup", "")),
        "qipcrtr_no_send": str(current.get("qipcrtr_no_send", "")),
        "qipcrtr_no_control": str(current.get("qipcrtr_no_control", "")),
        "qipcrtr_no_service_start": str(current.get("qipcrtr_no_service_start", "")),
        "qrtr_readback_label": str(current.get("qrtr_readback_label", "")),
        "service180_counts": str(current.get("raw_service180_counts", "")),
        "service74_counts": str(current.get("raw_service74_counts", "")),
        "wlan_pd_counts": str(current.get("raw_wlan_pd_counts", "")),
        "servnotif_early_state": str(current.get("servnotif_early_state", "")),
        "servnotif_late_state": str(current.get("servnotif_late_state", "")),
        "wlfw_service69_seen": str(current.get("wlfw_service69_seen", "")),
        "requested_wlanmdsp": str(current.get("requested_wlanmdsp", "")),
        "wlan0_present": str(current.get("wlan0_present", "")),
        "lower_mhi_present": boolish(current.get("lower_mhi_present")),
        "lower_service69_progress": boolish(current.get("lower_service69_progress")),
    }


def classify(summaries: dict[str, dict[str, Any]]) -> tuple[str, bool, str, str, dict[str, bool]]:
    v1900 = summaries["v1900"]
    v1898 = summaries["v1898"]
    v1834 = summaries["v1834"]
    v1803 = summaries["v1803"]
    v1819 = summaries["v1819"]
    v1836 = summaries["v1836"]

    android_normal_internal = (
        v1900["pass"]
        and v1900["label"] == "cnss-worker-parity-servnotif-stateup-gap"
        and v1900["android_requested_wlanmdsp"] == "1"
        and v1900["android_wlan_pd_count"] > 0
        and v1900["android_wlanmdsp_count"] > 0
        and v1900["android_wlan0_time_s"] is not None
        and v1900["android_pcie_mhi_before_wlan0"] == 0
        and not v1900["android_degraded_257s_like"]
        and v1898["pass"]
        and v1898["android_ordered_internal_stateup"]
        and v1898["android_service74_count"] > 0
        and v1898["android_wlan_pd_count"] > 0
        and v1898["android_wlanmdsp_count"] > 0
        and v1898["android_pcie_mhi_before_wlan0"] == 0
        and not v1898["android_degraded_257s_like"]
        and v1898["android_pm_msg22_hits"] == 0
    )
    native_publication_absent = (
        positive_count_list(v1900["native_service180_counts"])
        and zero_count_list(v1900["native_service74_counts"])
        and zero_count_list(v1900["native_wlan_pd_counts"])
        and v1900["native_servnotif_late_state"] == "uninit"
        and v1900["native_wlfw_service69_seen"] == "0"
        and v1900["native_requested_wlanmdsp"] == "0"
        and v1900["native_wlan0_present"] == "0"
        and positive_count_list(v1898["native_service180_counts"])
        and zero_count_list(v1898["native_service74_counts"])
        and zero_count_list(v1898["native_wlan_pd_counts"])
        and v1898["native_early_servnotif_state"] == "uninit"
        and v1898["native_late_servnotif_state"] == "uninit"
        and v1898["native_wlfw_service69_seen"] == "0"
        and v1898["native_requested_wlanmdsp"] == "0"
        and v1898["native_wlan0_present"] == "0"
        and not v1898["subsys_esoc0_open"]
    )
    qipcrtr_mechanics_ruled_out = (
        v1834["pass"]
        and v1834["qipcrtr_label"] == "qipcrtr-bound-recv-poll-timeout-passive"
        and v1834["qipcrtr_bound"]
        and v1834["qipcrtr_port_nonzero"]
        and v1834["qipcrtr_poll_timeout"]
        and v1834["qipcrtr_recv_skip_reason"] == "poll-timeout"
        and not v1834["qipcrtr_packet_received"]
        and v1834["qipcrtr_no_connect"] == "1"
        and v1834["qipcrtr_no_control"] == "1"
        and v1834["qipcrtr_no_lookup_send"] == "1"
        and v1834["qipcrtr_no_send"] == "1"
        and v1834["qipcrtr_no_service_start"] == "1"
        and not v1834["qrtr_registry_wlan_pd_text_positive"]
        and positive_count_list(v1834["service180_counts"])
        and zero_count_list(v1834["service74_counts"])
        and zero_count_list(v1834["wlan_pd_counts"])
    )
    wlfw_readback_empty = (
        v1803["pass"]
        and v1803["wlfw_service_request_hits"] > 0
        and v1803["wlfw_ind_register_hits"] == 0
        and v1803["wlfw_cap_hits"] == 0
        and v1803["qrtr_readback"] == "1"
        and v1803["qrtr_case_0_service_events"] == 0
        and v1803["qrtr_case_0_end_of_list"] > 0
        and v1803["qrtr_case_1_service_events"] == 0
        and v1803["qrtr_case_1_end_of_list"] > 0
        and v1803["servnotif_early_state"] == "uninit"
        and v1803["servnotif_late_state"] == "uninit"
        and v1803["servnotif_early_indication_seen"] == "0"
        and v1803["servnotif_late_indication_seen"] == "0"
        and v1803["wlfw_service69_seen"] == "0"
        and v1803["requested_wlanmdsp"] == "0"
        and v1803["wlan0_present"] == "0"
    )
    servloc_domain_absent = (
        v1819["pass"]
        and v1819["publication_text_label"] == "servloc-init-visible-domain-absent"
        and v1819["publication_text_positive"]
        and positive_count_list(v1819["raw_service_locator_counts"])
        and positive_count_list(v1819["raw_service180_counts"])
        and zero_count_list(v1819["raw_service74_counts"])
        and zero_count_list(v1819["raw_wlan_pd_counts"])
        and zero_count_list(v1819["raw_wlan_pd_domain_counts"])
        and zero_count_list(v1819["raw_wlan_fw_counts"])
        and v1819["servnotif_early_state"] == "uninit"
        and v1819["servnotif_late_state"] == "uninit"
        and v1819["wlfw_service69_seen"] == "0"
        and v1819["requested_wlanmdsp"] == "0"
        and v1819["wlan0_present"] == "0"
    )
    uninit_transition_consistent = (
        v1836["pass"]
        and v1836["qipcrtr_label"] == "qipcrtr-bound-recv-poll-timeout-passive"
        and v1836["qipcrtr_poll_timeout"] == "1"
        and v1836["qipcrtr_no_lookup"] == "1"
        and v1836["qipcrtr_no_send"] == "1"
        and v1836["qipcrtr_no_control"] == "1"
        and v1836["qipcrtr_no_service_start"] == "1"
        and v1836["qrtr_readback_label"] == "wlfw-readback-empty"
        and positive_count_list(v1836["service180_counts"])
        and zero_count_list(v1836["service74_counts"])
        and zero_count_list(v1836["wlan_pd_counts"])
        and v1836["servnotif_early_state"] == "uninit"
        and v1836["servnotif_late_state"] == "uninit"
        and v1836["wlfw_service69_seen"] == "0"
        and v1836["requested_wlanmdsp"] == "0"
        and v1836["wlan0_present"] == "0"
        and not v1836["lower_mhi_present"]
        and not v1836["lower_service69_progress"]
    )

    checks = {
        "android_normal_internal": android_normal_internal,
        "native_publication_absent": native_publication_absent,
        "qipcrtr_mechanics_ruled_out": qipcrtr_mechanics_ruled_out,
        "wlfw_readback_empty": wlfw_readback_empty,
        "servloc_domain_absent": servloc_domain_absent,
        "uninit_transition_consistent": uninit_transition_consistent,
    }
    if all(checks.values()):
        return (
            "v1901-servnotif-publication-absent-not-socket-mechanics-host-pass",
            True,
            "service74/msm/modem/wlan_pd publication remains absent after native post-open; QRTR socket, listener, and WLFW69 readback mechanics are not the blocker",
            "servnotif-publication-absent-not-socket-mechanics",
            checks,
        )
    failing = ",".join(key for key, value in checks.items() if not value)
    return (
        "v1901-servnotif-publication-absent-classifier-mismatch",
        False,
        f"required retained evidence did not match expected service publication gap checks: {failing}",
        "servnotif-publication-absent-unproven",
        checks,
    )


def render_report(result: dict[str, Any]) -> str:
    summaries = result["summaries"]
    checks = result["checks"]
    v1900 = summaries["v1900"]
    v1898 = summaries["v1898"]
    v1834 = summaries["v1834"]
    v1803 = summaries["v1803"]
    v1819 = summaries["v1819"]
    v1836 = summaries["v1836"]
    return "\n".join(
        [
            "# Native Init V1901 Service-notifier Publication Absent Classifier",
            "",
            "## Summary",
            "",
            f"- Cycle: `{CYCLE}`",
            "- Type: host-only classifier over retained Android-good/native service-notifier evidence",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: `{'PASS' if result['pass'] else 'FAIL'}`",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Gate Checks",
            "",
            "| check | result |",
            "| --- | --- |",
            *[f"| `{key}` | `{value}` |" for key, value in checks.items()],
            "",
            "## Android Normal Internal Path",
            "",
            f"- V1900 decision/label/pass: `{v1900['decision']}` / `{v1900['label']}` / `{v1900['pass']}`",
            "- V1900 Android requested_wlanmdsp/wlan_pd/wlanmdsp/wlan0: "
            f"`{v1900['android_requested_wlanmdsp']}` / `{v1900['android_wlan_pd_count']}` / "
            f"`{v1900['android_wlanmdsp_count']}` / `{v1900['android_wlan0_time_s']}`",
            "- V1900 Android pre-wlan0 pcie-mhi/degraded257: "
            f"`{v1900['android_pcie_mhi_before_wlan0']}` / `{v1900['android_degraded_257s_like']}`",
            f"- V1898 ordered service180/service74/wlan_pd/wlanmdsp: "
            f"`{v1898['android_service180_count']}` / `{v1898['android_service74_count']}` / "
            f"`{v1898['android_wlan_pd_count']}` / `{v1898['android_wlanmdsp_count']}`",
            f"- V1898 pm_msg22 hits: `{v1898['android_pm_msg22_hits']}`",
            "",
            "## Native Publication Gap",
            "",
            "- V1900 native service180/service74/wlan_pd: "
            f"`{v1900['native_service180_counts']}` / `{v1900['native_service74_counts']}` / "
            f"`{v1900['native_wlan_pd_counts']}`",
            "- V1900 native servnotif/WLFW69/wlanmdsp/wlan0: "
            f"`{v1900['native_servnotif_late_state']}` / `{v1900['native_wlfw_service69_seen']}` / "
            f"`{v1900['native_requested_wlanmdsp']}` / `{v1900['native_wlan0_present']}`",
            "- V1898 native service180/service74/wlan_pd: "
            f"`{v1898['native_service180_counts']}` / `{v1898['native_service74_counts']}` / "
            f"`{v1898['native_wlan_pd_counts']}`",
            "- V1898 native servnotif/WLFW69/wlanmdsp/wlan0: "
            f"`{v1898['native_late_servnotif_state']}` / `{v1898['native_wlfw_service69_seen']}` / "
            f"`{v1898['native_requested_wlanmdsp']}` / `{v1898['native_wlan0_present']}`",
            "",
            "## Mechanics Ruled Out",
            "",
            "- V1834 QIPCRTR bound/poll/recv/no-send: "
            f"`{v1834['qipcrtr_bound']}` / `{v1834['qipcrtr_poll_timeout']}` / "
            f"`{v1834['qipcrtr_packet_received']}` / `{v1834['qipcrtr_no_send']}`",
            "- V1834 service180/service74/wlan_pd/WLFW69: "
            f"`{v1834['service180_counts']}` / `{v1834['service74_counts']}` / "
            f"`{v1834['wlan_pd_counts']}` / `{v1834['wlfw_service69_seen']}`",
            "- V1803 WLFW request/ind-register/cap/WLFW69: "
            f"`{v1803['wlfw_service_request_hits']}` / `{v1803['wlfw_ind_register_hits']}` / "
            f"`{v1803['wlfw_cap_hits']}` / `{v1803['wlfw_service69_seen']}`",
            "- V1803 QRTR service69 readback events/end-of-list: "
            f"`{v1803['qrtr_case_0_service_events']},{v1803['qrtr_case_1_service_events']}` / "
            f"`{v1803['qrtr_case_0_end_of_list']},{v1803['qrtr_case_1_end_of_list']}`",
            "- V1819 servloc/service180/service74/wlan_pd-domain: "
            f"`{v1819['publication_text_label']}` / `{v1819['raw_service180_counts']}` / "
            f"`{v1819['raw_service74_counts']}` / `{v1819['raw_wlan_pd_domain_counts']}`",
            "- V1836 qipcrtr/qrtr-readback/servnotif: "
            f"`{v1836['qipcrtr_label']}` / `{v1836['qrtr_readback_label']}` / "
            f"`{v1836['servnotif_late_state']}`",
            "",
            "## Selected Boundary",
            "",
            "- Keep the path anchored on the internal modem WLAN-PD state-up sequence.",
            "- Do not chase pm-service msg22: Android-good state-up has zero msg22 hits in the normal path.",
            "- Do not chase QRTR socket mechanics: passive local bind and recv-poll execute without any inbound WLAN-PD publication.",
            "- The next useful native unit is read-only instrumentation of service-locator/service-notifier publication transitions that would create service74 and WLFW service69.",
            "",
            "## Safety Scope",
            "",
            "V1901 is host-only. It reads retained manifests and writes local classifier artifacts only. "
            "It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, "
            "scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, "
            "forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, "
            "PCI rescan, platform bind/unbind, firmware write, boot write, or partition write.",
            "",
            "## Next",
            "",
            "- Build the next bounded native read-only capture around service-notifier/service-locator publication and WLFW service69 readback after `/dev/subsys_modem` open.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0`.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1900-manifest", type=Path, default=DEFAULT_V1900_MANIFEST)
    parser.add_argument("--v1898-manifest", type=Path, default=DEFAULT_V1898_MANIFEST)
    parser.add_argument("--v1834-manifest", type=Path, default=DEFAULT_V1834_MANIFEST)
    parser.add_argument("--v1803-manifest", type=Path, default=DEFAULT_V1803_MANIFEST)
    parser.add_argument("--v1819-manifest", type=Path, default=DEFAULT_V1819_MANIFEST)
    parser.add_argument("--v1836-manifest", type=Path, default=DEFAULT_V1836_MANIFEST)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summaries = {
        "v1900": v1900_summary(REPO_ROOT / args.v1900_manifest),
        "v1898": v1898_summary(REPO_ROOT / args.v1898_manifest),
        "v1834": v1834_summary(REPO_ROOT / args.v1834_manifest),
        "v1803": v1803_summary(REPO_ROOT / args.v1803_manifest),
        "v1819": v1819_summary(REPO_ROOT / args.v1819_manifest),
        "v1836": v1836_summary(REPO_ROOT / args.v1836_manifest),
    }
    decision, passed, reason, label, checks = classify(summaries)
    store = EvidenceStore(REPO_ROOT / args.out_dir)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(store.run_dir),
        "report": rel(REPO_ROOT / args.report_path),
        "summaries": summaries,
        "checks": checks,
        "safety": {
            "host_only": True,
            "device_command": False,
            "wifi_hal_scan_connect_ping": False,
            "subsys_esoc0_open": False,
            "pcie_esoc_gdsc_path": False,
            "secret_material_written": False,
        },
    }
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    write_private_text(LATEST_POINTER, rel(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(REPO_ROOT / args.report_path, report)
    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"label:    {label}")
    print(f"reason:   {reason}")
    print(f"evidence: {rel(store.run_dir)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
