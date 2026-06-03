#!/usr/bin/env python3
"""V1900 host-only classifier for CNSS worker parity vs service-notifier state-up."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1900-cnss-worker-servnotif-stateup-delta-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1900_CNSS_WORKER_SERVNOTIF_STATEUP_DELTA_2026-06-03.md"
)
DEFAULT_V1899_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1899-android-cnss-qrtr-stateup-live2-20260603-200642" / "manifest.json"
)
DEFAULT_V1736_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
DEFAULT_V1885_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1885-internal-pm-qmi-servreg-trigger-source-diff" / "manifest.json"
)
DEFAULT_V1898_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1898-servnotif-stateup-not-msg22-classifier" / "manifest.json"
DEFAULT_V1760_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1760-wlan-pd-request-trigger-surface-classifier" / "manifest.json"
)


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
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
    except ValueError:
        return 0


def positive_count_list(value: object) -> bool:
    return any(intish(part.strip()) > 0 for part in str(value or "").split(",") if part.strip())


def zero_count_list(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and all(intish(part) == 0 for part in parts)


def android_v1899_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    analysis = ((manifest.get("context") or {}).get("analysis") or {})
    dmesg = analysis.get("dmesg") or {}
    cnss_summary = analysis.get("cnss_uprobe_summary") or {}
    request_summary = analysis.get("request_summary") or {}
    return {
        "manifest": rel(path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": boolish(manifest.get("pass")),
        "rollback_selftest_fail0": boolish(manifest.get("rollback_selftest_fail0")),
        "android_dir": rel(analysis.get("android_dir", "")),
        "cnss_uprobe_hit_count": intish(cnss_summary.get("hit_count")),
        "cnss_worker_entry_hit_count": intish(cnss_summary.get("worker_entry_hit_count")),
        "cnss_uprobe_excerpt": analysis.get("cnss_uprobe_excerpt", ""),
        "pm_msg22_count": intish(analysis.get("pm_msg22_count")),
        "pending_qmi_client_count": intish(analysis.get("pending_qmi_client_count")),
        "wlfw_service_request_count": intish(analysis.get("wlfw_service_request_count")),
        "wlan_pd_indication_count": intish(analysis.get("wlan_pd_indication_count")),
        "wlanmdsp_count": intish(analysis.get("wlanmdsp_count")),
        "requested_wlanmdsp": str(analysis.get("requested_wlanmdsp", "")),
        "request_summary_requested_wlanmdsp": str(request_summary.get("requested_wlanmdsp", "")),
        "wlan0_time_s": dmesg.get("wlan0_time_s"),
        "pcie_mhi_before_wlan0": intish(dmesg.get("pcie_mhi_before_wlan0")),
        "esoc_boot_failed_before_wlan0": intish(dmesg.get("esoc_boot_failed_before_wlan0")),
        "degraded_257s_like": boolish(dmesg.get("degraded_257s_like")),
    }


def native_v1736_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    gate = manifest.get("gate") or {}
    return {
        "manifest": rel(path),
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "wlfw_start_hit_count": intish(gate.get("wlfw_start_hit_count")),
        "wlfw_service_request_hit_count": intish(gate.get("wlfw_service_request_hit_count")),
        "wlfw_worker_create_success_hit_count": intish(gate.get("wlfw_worker_create_success_hit_count")),
        "wlfw_ind_register_qmi_hit_count": intish(gate.get("wlfw_ind_register_qmi_hit_count")),
        "wlfw_cap_qmi_hit_count": intish(gate.get("wlfw_cap_qmi_hit_count")),
        "requested_wlanmdsp": str(gate.get("requested_wlanmdsp", "")),
        "wlfw_service69_seen": str(gate.get("wlfw_service69_seen", "")),
    }


def native_latest_summary(v1885_path: Path, v1898_path: Path) -> dict[str, Any]:
    v1885 = read_json(v1885_path)
    v1898 = read_json(v1898_path)
    post_open = v1885.get("native_post_open") or {}
    native_1898 = v1898.get("native") or {}
    return {
        "v1885_manifest": rel(v1885_path),
        "v1885_decision": v1885.get("decision", ""),
        "v1885_label": v1885.get("label", ""),
        "v1885_pass": boolish(v1885.get("pass")),
        "v1898_manifest": rel(v1898_path),
        "v1898_decision": v1898.get("decision", ""),
        "v1898_label": v1898.get("label", ""),
        "v1898_pass": boolish(v1898.get("pass")),
        "pm_client_register_rc": str(post_open.get("pm_client_register_rc", "")),
        "pm_client_connect_rc": str(post_open.get("pm_client_connect_rc", "")),
        "open_context_path": str(post_open.get("open_context_path", "")),
        "open_context_fd": str(post_open.get("open_context_fd", "")),
        "open_context_power_state": str(post_open.get("open_context_power_state", "")),
        "post_ack_msg22_ind_hits": intish(post_open.get("post_ack_qmi_restart_ind_hits")),
        "dms_service_request_hits": intish(post_open.get("dms_service_request_hits")),
        "wlfw_service_request_hits": intish(post_open.get("wlfw_service_request_hits")),
        "wlfw_ind_register_qmi_hits": intish(post_open.get("wlfw_ind_register_qmi_hits")),
        "wlfw_cap_qmi_hits": intish(post_open.get("wlfw_cap_qmi_hits")),
        "requested_wlanmdsp": str(post_open.get("requested_wlanmdsp", "")),
        "wlfw_service69_seen": str(post_open.get("wlfw_service69_seen", "")),
        "wlan0_present": str(post_open.get("wlan0_present", "")),
        "early_servnotif_state": str(post_open.get("early_servnotif_state", "")),
        "late_servnotif_state": str(post_open.get("late_servnotif_state", "")),
        "service180_counts": str(native_1898.get("v1885_service180_counts", post_open.get("klog_service180_counts", ""))),
        "service74_counts": str(native_1898.get("v1816_service74_counts", "")),
        "wlan_pd_counts": str(native_1898.get("v1885_wlan_pd_counts", post_open.get("raw_wlan_pd_text_counts", ""))),
    }


def legacy_request_generation_summary(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    return {
        "manifest": rel(path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": boolish(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
    }


def classify(android: dict[str, Any],
             native_worker: dict[str, Any],
             native_latest: dict[str, Any],
             legacy_request: dict[str, Any]) -> tuple[str, bool, str, str]:
    android_worker_stateup = (
        android["pass"]
        and android["rollback_selftest_fail0"]
        and android["label"] == "android-cnss-wlfw-worker-not-msg22"
        and android["cnss_worker_entry_hit_count"] > 0
        and android["pm_msg22_count"] == 0
        and android["pending_qmi_client_count"] == 0
        and android["requested_wlanmdsp"] == "1"
        and android["wlan_pd_indication_count"] > 0
        and android["wlanmdsp_count"] > 0
        and android["wlan0_time_s"] is not None
        and android["pcie_mhi_before_wlan0"] == 0
        and android["esoc_boot_failed_before_wlan0"] == 0
        and not android["degraded_257s_like"]
    )
    native_worker_parity = (
        native_worker["pass"]
        and native_worker["wlfw_start_hit_count"] > 0
        and native_worker["wlfw_worker_create_success_hit_count"] > 0
        and native_worker["wlfw_service_request_hit_count"] > 0
        and native_worker["wlfw_ind_register_qmi_hit_count"] == 0
        and native_worker["wlfw_cap_qmi_hit_count"] == 0
        and native_worker["requested_wlanmdsp"] == "0"
        and native_worker["wlfw_service69_seen"] == "0"
    )
    native_post_open_stateup_gap = (
        native_latest["v1885_pass"]
        and native_latest["v1898_pass"]
        and native_latest["open_context_path"] == "/dev/subsys_modem"
        and native_latest["pm_client_register_rc"] == "0"
        and native_latest["pm_client_connect_rc"] == "0"
        and native_latest["post_ack_msg22_ind_hits"] == 0
        and native_latest["dms_service_request_hits"] > 0
        and native_latest["wlfw_service_request_hits"] > 0
        and native_latest["wlfw_ind_register_qmi_hits"] == 0
        and native_latest["wlfw_cap_qmi_hits"] == 0
        and native_latest["requested_wlanmdsp"] == "0"
        and native_latest["wlfw_service69_seen"] == "0"
        and native_latest["wlan0_present"] == "0"
        and native_latest["late_servnotif_state"] == "uninit"
        and positive_count_list(native_latest["service180_counts"])
        and zero_count_list(native_latest["service74_counts"])
        and zero_count_list(native_latest["wlan_pd_counts"])
    )
    legacy_consistent = legacy_request["pass"] and legacy_request["label"] == "request-generation-gap-before-firmware-serving"
    if not android_worker_stateup:
        return (
            "v1900-android-cnss-worker-stateup-incomplete",
            False,
            "V1899 Android-good evidence does not prove clean CNSS worker -> wlan_pd/wlanmdsp/wlan0 state-up with msg22 absent",
            "android-cnss-worker-stateup-incomplete",
        )
    if not native_worker_parity:
        return (
            "v1900-native-cnss-worker-parity-unproven",
            False,
            "native historical CNSS evidence does not prove worker/request parity before the downstream gap",
            "native-cnss-worker-parity-unproven",
        )
    if not native_post_open_stateup_gap:
        return (
            "v1900-native-post-open-stateup-gap-mismatch",
            False,
            "latest native post-open evidence does not match service180-present/service74-wlan_pd-absent state-up gap",
            "native-post-open-stateup-gap-mismatch",
        )
    if not legacy_consistent:
        return (
            "v1900-legacy-request-generation-gap-mismatch",
            False,
            "legacy request-generation classifier is missing or inconsistent",
            "legacy-request-generation-gap-mismatch",
        )
    return (
        "v1900-cnss-worker-parity-servnotif-stateup-gap-host-pass",
        True,
        "Android-good proves CNSS worker execution is sufficient only when service-notifier service74/wlan_pd state-up follows; native already reaches the worker/request path but remains service74/wlan_pd absent, service-notifier uninit, and no WLFW69/wlanmdsp/wlan0",
        "cnss-worker-parity-servnotif-stateup-gap",
    )


def render_report(result: dict[str, Any]) -> str:
    android = result["android_v1899"]
    native_worker = result["native_v1736_worker"]
    native_latest = result["native_latest_post_open"]
    legacy_request = result["legacy_v1760_request_generation"]
    return "\n".join(
        [
            "# Native Init V1900 CNSS Worker Service-notifier State-up Delta",
            "",
            "## Summary",
            "",
            "- Cycle: `V1900`",
            "- Type: host-only classifier over Android V1899 worker trace and native worker/post-open evidence",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Android Worker State-up",
            "",
            f"- V1899 decision/label/pass/rollback fail=0: `{android['decision']}` / `{android['label']}` / `{android['pass']}` / `{android['rollback_selftest_fail0']}`",
            f"- CNSS uprobe/worker hits: `{android['cnss_uprobe_hit_count']}` / `{android['cnss_worker_entry_hit_count']}`",
            f"- msg22/pending-client hits: `{android['pm_msg22_count']}` / `{android['pending_qmi_client_count']}`",
            f"- WLFW request/wlan_pd/wlanmdsp/wlan0: `{android['wlfw_service_request_count']}` / `{android['wlan_pd_indication_count']}` / `{android['wlanmdsp_count']}` / `{android['wlan0_time_s']}`",
            f"- contamination pre-wlan0 PCIe-MHI/eSoC/degraded257: `{android['pcie_mhi_before_wlan0']}` / `{android['esoc_boot_failed_before_wlan0']}` / `{android['degraded_257s_like']}`",
            "- CNSS trace: `wlfw_start -> dms_init -> pthread_create -> worker_create_success -> wlfw_service_request_entry`.",
            "",
            "## Native Worker Parity",
            "",
            f"- V1736 decision/pass: `{native_worker['decision']}` / `{native_worker['pass']}`",
            f"- WLFW start/worker/request hits: `{native_worker['wlfw_start_hit_count']}` / `{native_worker['wlfw_worker_create_success_hit_count']}` / `{native_worker['wlfw_service_request_hit_count']}`",
            f"- WLFW ind-register/cap/requested-wlanmdsp/service69: `{native_worker['wlfw_ind_register_qmi_hit_count']}` / `{native_worker['wlfw_cap_qmi_hit_count']}` / `{native_worker['requested_wlanmdsp']}` / `{native_worker['wlfw_service69_seen']}`",
            f"- V1760 legacy label/pass: `{legacy_request['label']}` / `{legacy_request['pass']}`",
            "",
            "## Latest Native Post-open",
            "",
            f"- V1885 decision/label/pass: `{native_latest['v1885_decision']}` / `{native_latest['v1885_label']}` / `{native_latest['v1885_pass']}`",
            f"- V1898 decision/label/pass: `{native_latest['v1898_decision']}` / `{native_latest['v1898_label']}` / `{native_latest['v1898_pass']}`",
            f"- PM register/connect/open: `{native_latest['pm_client_register_rc']}` / `{native_latest['pm_client_connect_rc']}` / `{native_latest['open_context_path']}` fd `{native_latest['open_context_fd']}` state `{native_latest['open_context_power_state']}`",
            f"- DMS/WLFW request/ind-register/cap/msg22: `{native_latest['dms_service_request_hits']}` / `{native_latest['wlfw_service_request_hits']}` / `{native_latest['wlfw_ind_register_qmi_hits']}` / `{native_latest['wlfw_cap_qmi_hits']}` / `{native_latest['post_ack_msg22_ind_hits']}`",
            f"- service180/service74/wlan_pd: `{native_latest['service180_counts']}` / `{native_latest['service74_counts']}` / `{native_latest['wlan_pd_counts']}`",
            f"- service-notifier/WLFW69/wlanmdsp/wlan0: `{native_latest['early_servnotif_state']}` -> `{native_latest['late_servnotif_state']}` / `{native_latest['wlfw_service69_seen']}` / `{native_latest['requested_wlanmdsp']}` / `{native_latest['wlan0_present']}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- Do not chase pm-service msg22: Android state-up still has zero msg22/pending-client hits.",
            "- Do not chase CNSS worker creation: Android proves the worker path, and native V1736 already reached worker/request without downstream progress.",
            "- Do not chase firmware serving: Android requests and serves `wlanmdsp.mbn`; native still has no request.",
            "- The remaining blocker is the internal service-notifier/WLFW server state-up edge: service74/`msm/modem/wlan_pd` publication and WLFW service 69 before `wlanmdsp.mbn`.",
            "",
            "## Safety Scope",
            "",
            "V1900 is host-only. It parses retained manifests/reports and writes local classifier artifacts only. It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or partition write.",
            "",
            "## Next",
            "",
            "- Next live/native unit should instrument the service-notifier service74/180 and WLFW service 69 transition around native post-open without changing eSoC/PCIe/GDSC or Wi-Fi connection state.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0`.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1899-manifest", type=Path, default=DEFAULT_V1899_MANIFEST)
    parser.add_argument("--v1736-manifest", type=Path, default=DEFAULT_V1736_MANIFEST)
    parser.add_argument("--v1885-manifest", type=Path, default=DEFAULT_V1885_MANIFEST)
    parser.add_argument("--v1898-manifest", type=Path, default=DEFAULT_V1898_MANIFEST)
    parser.add_argument("--v1760-manifest", type=Path, default=DEFAULT_V1760_MANIFEST)
    args = parser.parse_args()

    store = EvidenceStore(args.out_dir)
    android = android_v1899_summary(args.v1899_manifest)
    native_worker = native_v1736_summary(args.v1736_manifest)
    native_latest = native_latest_summary(args.v1885_manifest, args.v1898_manifest)
    legacy_request = legacy_request_generation_summary(args.v1760_manifest)
    decision, passed, reason, label = classify(android, native_worker, native_latest, legacy_request)
    result = {
        "cycle": "V1900",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "android_v1899": android,
        "native_v1736_worker": native_worker,
        "native_latest_post_open": native_latest,
        "legacy_v1760_request_generation": legacy_request,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credential_use": False,
            "dhcp_routes": False,
            "external_ping": False,
            "pmic_gpio_gdsc_regulator_write": False,
            "forced_rc1_case": False,
            "subsys_esoc0_open": False,
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    store.write_text("host/android-v1899-worker-parse.json", json.dumps(android, indent=2, sort_keys=True) + "\n")
    store.write_text("host/native-v1736-worker-parse.json", json.dumps(native_worker, indent=2, sort_keys=True) + "\n")
    store.write_text("host/native-latest-post-open-parse.json", json.dumps(native_latest, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
