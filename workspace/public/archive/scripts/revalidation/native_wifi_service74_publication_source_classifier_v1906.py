#!/usr/bin/env python3
"""V1906 host/source classifier for the service74 publication edge."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_V1905_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1905-servnotif-stateup-not-msg22-classifier" / "manifest.json"
DEFAULT_V1904_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1904-servnotif-passive-edge-handoff" / "manifest.json"
DEFAULT_SERVICE_NOTIFIER = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "drivers"
    / "soc"
    / "qcom"
    / "service-notifier.c"
)
DEFAULT_SERVICE_NOTIFIER_PRIVATE = DEFAULT_SERVICE_NOTIFIER.with_name("service-notifier-private.h")
DEFAULT_SERVICE_NOTIFIER_PUBLIC = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "include"
    / "soc"
    / "qcom"
    / "service-notifier.h"
)
DEFAULT_ICNSS = DEFAULT_SERVICE_NOTIFIER.with_name("icnss.c")
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1906-service74-publication-source-classifier"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1906_SERVICE74_PUBLICATION_SOURCE_CLASSIFIER_2026-06-03.md"
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


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def positive_csv(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and any(intish(part) > 0 for part in parts)


def zero_csv(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and all(intish(part) == 0 for part in parts)


def line_no(text: str, pattern: str) -> int | None:
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def line_ref(path: Path, line: int | None) -> str:
    return f"{rel(path)}:{line}" if line else f"{rel(path)}:missing"


def line_refs(path: Path, text: str, markers: dict[str, str]) -> dict[str, str]:
    return {name: line_ref(path, line_no(text, pattern)) for name, pattern in markers.items()}


def source_summary(service_notifier: Path,
                   service_notifier_private: Path,
                   service_notifier_public: Path,
                   icnss: Path) -> dict[str, Any]:
    sn = read_text(service_notifier)
    private = read_text(service_notifier_private)
    public = read_text(service_notifier_public)
    icnss_text = read_text(icnss)
    refs = {}
    refs.update(line_refs(service_notifier, sn, {
        "sn_new_server": r"static int service_notifier_new_server",
        "sn_new_server_log_instance": r"Connection established between QMI handle and %d service",
        "sn_new_server_work": r"static void new_server_work",
        "sn_register_listener": r"static int register_notif_listener",
        "sn_send_listener_req": r"&txn, SERVREG_NOTIF_REGISTER_LISTENER_REQ,",
        "sn_state_ind_handler": r"root_service_service_ind_cb",
        "sn_send_ind_ack": r"static void send_ind_ack",
        "sn_qmi_lookup_instance": r"qmi_add_lookup\(&qmi_data->clnt_handle,",
        "sn_pd_restart": r"int service_notif_pd_restart",
        "sn_register_api": r"void \*service_notif_register_notifier",
    }))
    refs.update(line_refs(service_notifier_private, private, {
        "msg_register_listener_0x20": r"QMI_SERVREG_NOTIF_REGISTER_LISTENER_REQ_V01\s+0x0020",
        "msg_state_updated_0x22": r"QMI_SERVREG_NOTIF_STATE_UPDATED_IND_V01\s+0x0022",
        "msg_ack_0x23": r"QMI_SERVREG_NOTIF_STATE_UPDATED_IND_ACK_REQ_V01\s+0x0023",
        "msg_restart_pd_0x24": r"QMI_SERVREG_NOTIF_RESTART_PD_REQ_V01\s+0x0024",
    }))
    refs.update(line_refs(service_notifier_public, public, {
        "state_up_0x1fffffff": r"SERVREG_NOTIF_SERVICE_STATE_UP_V01\s+=\s+0x1FFFFFFF",
        "state_uninit_0x7fffffff": r"SERVREG_NOTIF_SERVICE_STATE_UNINIT_V01\s+=\s+0x7FFFFFFF",
        "public_register_api": r"service_notif_register_notifier\(const char \*service_path, int instance_id",
        "public_pd_restart_api": r"int service_notif_pd_restart",
    }))
    refs.update(line_refs(icnss, icnss_text, {
        "icnss_locator_notify": r"static int icnss_get_service_location_notify",
        "icnss_domain_loop": r"for \(i = 0; i < pd->total_domains; i\+\+\)",
        "icnss_domain_debug": r"domain_name: %s, instance_id: %d",
        "icnss_register_notifier": r"service_notif_register_notifier\(pd->domain_list\[i\]\.name,",
        "icnss_stateup_notify": r"notification == SERVREG_NOTIF_SERVICE_STATE_UP_V01",
        "icnss_pd_restart_call": r"service_notif_pd_restart\(priv->service_notifier\[0\]\.name,",
    }))
    required_keys = [
        "sn_new_server", "sn_new_server_log_instance", "sn_new_server_work",
        "sn_register_listener", "sn_send_listener_req", "sn_state_ind_handler",
        "sn_send_ind_ack", "sn_qmi_lookup_instance", "sn_register_api",
        "msg_register_listener_0x20", "msg_state_updated_0x22", "msg_ack_0x23",
        "state_up_0x1fffffff", "state_uninit_0x7fffffff", "icnss_locator_notify",
        "icnss_domain_loop", "icnss_register_notifier", "icnss_stateup_notify",
    ]
    return {
        "service_notifier": rel(service_notifier),
        "service_notifier_private": rel(service_notifier_private),
        "service_notifier_public": rel(service_notifier_public),
        "icnss": rel(icnss),
        "refs": refs,
        "required_markers_ok": all(not refs[key].endswith(":missing") for key in required_keys),
        "restart_pd_source_present_forbidden": not refs["sn_pd_restart"].endswith(":missing") or not refs["icnss_pd_restart_call"].endswith(":missing"),
        "qmi_lookup_uses_instance_id": "instance_id);" in sn[sn.find("qmi_add_lookup"):sn.find("qmi_add_lookup") + 240] if "qmi_add_lookup" in sn else False,
        "icnss_register_uses_domain_instance": "pd->domain_list[i].instance_id" in icnss_text,
    }


def evidence_summary(v1905_path: Path, v1904_path: Path) -> dict[str, Any]:
    v1905 = read_json(v1905_path)
    v1904 = read_json(v1904_path)
    android = v1905.get("android") or {}
    native = v1905.get("native") or {}
    v1904_gate = v1904.get("gate") or {}
    return {
        "v1905_manifest": rel(v1905_path),
        "v1905_decision": v1905.get("decision", ""),
        "v1905_label": v1905.get("label", ""),
        "v1905_pass": boolish(v1905.get("pass")),
        "android_ordered_internal_stateup": boolish(android.get("ordered_internal_stateup")),
        "android_times_s": android.get("times_s") or {},
        "android_service74_count": intish(android.get("service74_count")),
        "android_service180_count": intish(android.get("service180_count")),
        "android_wlan_pd_count": intish(android.get("wlan_pd_count")),
        "android_wlanmdsp_count": intish(android.get("wlanmdsp_count")),
        "android_wlan0_time_s": android.get("wlan0_time_s"),
        "android_pm_msg22_hits": intish(android.get("pm_msg22_hits")),
        "android_pcie_mhi_before_wlan0": intish(android.get("pcie_mhi_before_wlan0")),
        "android_esoc_boot_failed_before_wlan0": intish(android.get("esoc_boot_failed_before_wlan0")),
        "android_degraded_257s_like": boolish(android.get("degraded_257s_like")),
        "native_open_path": native.get("open_context_path", ""),
        "native_open_fd": native.get("open_context_fd", ""),
        "native_open_power_state": native.get("open_context_power_state", ""),
        "native_pm_register_rc": native.get("pm_client_register_rc", ""),
        "native_pm_connect_rc": native.get("pm_client_connect_rc", ""),
        "native_msg22_hits": intish(native.get("post_ack_msg22_ind_hits")),
        "native_service180_counts": native.get("v1816_service180_counts") or v1904_gate.get("raw_service180_text_counts", ""),
        "native_service74_counts": native.get("v1816_service74_counts") or v1904_gate.get("raw_service74_text_counts", ""),
        "native_wlan_pd_counts": native.get("v1816_wlan_pd_counts") or v1904_gate.get("raw_wlan_pd_text_counts", ""),
        "native_servnotif_early": native.get("early_servnotif_state", "") or v1904_gate.get("servnotif_early_state", ""),
        "native_servnotif_late": native.get("late_servnotif_state", "") or v1904_gate.get("servnotif_late_listener_state", ""),
        "native_wlfw69_seen": native.get("wlfw_service69_seen", "") or v1904_gate.get("wlfw_service69_seen", ""),
        "native_requested_wlanmdsp": native.get("requested_wlanmdsp", "") or v1904_gate.get("requested_wlanmdsp", ""),
        "native_wlan0_present": native.get("wlan0_present", "") or v1904_gate.get("wlan0_present", ""),
        "v1904_manifest": rel(v1904_path),
        "v1904_decision": v1904.get("decision", ""),
        "v1904_label": v1904.get("label", ""),
        "v1904_pass": boolish(v1904.get("pass")),
    }


def classify(evidence: dict[str, Any], source: dict[str, Any]) -> tuple[str, bool, str, str]:
    normal_android = (
        evidence["v1905_pass"]
        and evidence["android_ordered_internal_stateup"]
        and evidence["android_service74_count"] > 0
        and evidence["android_service180_count"] > 0
        and evidence["android_wlan_pd_count"] > 0
        and evidence["android_wlanmdsp_count"] > 0
        and evidence["android_wlan0_time_s"] is not None
        and evidence["android_pm_msg22_hits"] == 0
        and evidence["android_pcie_mhi_before_wlan0"] == 0
        and evidence["android_esoc_boot_failed_before_wlan0"] == 0
        and not evidence["android_degraded_257s_like"]
    )
    native_gap = (
        evidence["native_open_path"] == "/dev/subsys_modem"
        and evidence["native_pm_register_rc"] == "0"
        and evidence["native_pm_connect_rc"] == "0"
        and evidence["native_msg22_hits"] == 0
        and positive_csv(evidence["native_service180_counts"])
        and zero_csv(evidence["native_service74_counts"])
        and zero_csv(evidence["native_wlan_pd_counts"])
        and evidence["native_servnotif_early"] == "uninit"
        and evidence["native_servnotif_late"] == "uninit"
        and str(evidence["native_wlfw69_seen"]) in {"", "0"}
        and str(evidence["native_requested_wlanmdsp"]) in {"", "0"}
        and str(evidence["native_wlan0_present"]) in {"", "0"}
    )
    source_ok = (
        source["required_markers_ok"]
        and source["qmi_lookup_uses_instance_id"]
        and source["icnss_register_uses_domain_instance"]
    )
    if not normal_android:
        return (
            "v1906-android-normal-service74-publication-incomplete",
            False,
            "Android-good evidence does not prove the normal internal service74/180 -> wlan_pd -> wlan0 path",
            "android-normal-service74-publication-incomplete",
        )
    if not native_gap:
        return (
            "v1906-native-service74-publication-gap-incomplete",
            False,
            "native post-open evidence does not match service180-present/service74-absent gap",
            "native-service74-publication-gap-incomplete",
        )
    if not source_ok:
        return (
            "v1906-service74-source-markers-incomplete",
            False,
            "kernel source markers for service-notifier instance lookup and ICNSS domain registration are incomplete",
            "service74-source-markers-incomplete",
        )
    return (
        "v1906-service74-root-service-publication-edge-host-pass",
        True,
        "Android normal publishes service-notifier instances 74 and 180 before WLFW/wlan_pd, while native post-open publishes only 180; source shows publication is QRTR service lookup by ICNSS-provided domain instance_id before listener msg20/state-up msg22/ACK msg23",
        "service74-root-service-publication-edge",
    )


def render_report(result: dict[str, Any]) -> str:
    evidence = result["evidence"]
    source = result["source"]
    refs = source["refs"]
    return "\n".join([
        "# Native Init V1906 Service74 Publication Source Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1906`",
        "- Type: host/source classifier over V1905 Android-good/native evidence and kernel service-notifier source",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Evidence Edge",
        "",
        f"- V1905 decision/label/pass: `{evidence['v1905_decision']}` / `{evidence['v1905_label']}` / `{evidence['v1905_pass']}`",
        f"- Android normal times: `{json.dumps(evidence['android_times_s'], sort_keys=True)}`",
        f"- Android service74/service180/wlan_pd/wlanmdsp/wlan0: `{evidence['android_service74_count']}` / `{evidence['android_service180_count']}` / `{evidence['android_wlan_pd_count']}` / `{evidence['android_wlanmdsp_count']}` / `{evidence['android_wlan0_time_s']}`",
        f"- Android contamination pre-wlan0 PCIe-MHI/eSoC/degraded257: `{evidence['android_pcie_mhi_before_wlan0']}` / `{evidence['android_esoc_boot_failed_before_wlan0']}` / `{evidence['android_degraded_257s_like']}`",
        f"- Android pm-service msg22 hits: `{evidence['android_pm_msg22_hits']}`",
        f"- Native PM/open/msg22: register `{evidence['native_pm_register_rc']}` connect `{evidence['native_pm_connect_rc']}` open `{evidence['native_open_path']}` fd `{evidence['native_open_fd']}` state `{evidence['native_open_power_state']}` msg22 `{evidence['native_msg22_hits']}`",
        f"- Native service180/service74/wlan_pd: `{evidence['native_service180_counts']}` / `{evidence['native_service74_counts']}` / `{evidence['native_wlan_pd_counts']}`",
        f"- Native listener/WLFW69/wlanmdsp/wlan0: `{evidence['native_servnotif_early']}` -> `{evidence['native_servnotif_late']}` / `{evidence['native_wlfw69_seen']}` / `{evidence['native_requested_wlanmdsp']}` / `{evidence['native_wlan0_present']}`",
        "",
        "## Source Edge",
        "",
        f"- ICNSS receives service-locator domains and registers each domain with service-notifier: `{refs['icnss_locator_notify']}`, `{refs['icnss_domain_loop']}`, `{refs['icnss_register_notifier']}`",
        f"- service-notifier creates a QRTR lookup keyed by the requested instance id and logs `new_server` with that instance: `{refs['sn_qmi_lookup_instance']}`, `{refs['sn_new_server']}`, `{refs['sn_new_server_log_instance']}`",
        f"- after `new_server`, listener registration sends SERVREG msg20, and state-up is msg22 with ACK msg23: `{refs['sn_new_server_work']}`, `{refs['sn_send_listener_req']}`, `{refs['msg_register_listener_0x20']}`, `{refs['msg_state_updated_0x22']}`, `{refs['msg_ack_0x23']}`",
        f"- state constants: UP `{refs['state_up_0x1fffffff']}`, UNINIT `{refs['state_uninit_0x7fffffff']}`",
        f"- restart-PD source exists but remains forbidden/non-selected: `{refs['sn_pd_restart']}`, `{refs['icnss_pd_restart_call']}`, `{refs['msg_restart_pd_0x24']}`",
        "",
        "## Selected Diff",
        "",
        f"- Label: `{result['label']}`.",
        "- The missing native edge is before listener msg20 and before wlan_pd state-up msg22: service-notifier never receives/publishes instance 74 in native, while Android normal does.",
        "- Opening `/dev/subsys_modem` remains only a modem `subsys_get()` precondition; it does not by itself make the WLAN guest PD root-service instance publish.",
        "- This keeps the target on internal modem service-notifier/WLFW state-up and excludes SDX50M, PCIe/MHI, eSoC, GDSC, PMIC, GPIO, regulator, restart-PD, and Wi-Fi HAL paths.",
        "",
        "## Safety Scope",
        "",
        "V1906 is host-only. It reads retained manifests and local kernel source, then writes local evidence/report artifacts. It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.",
        "",
        "## Next",
        "",
        "- Next live candidate should be read-only internal-modem observability around ICNSS service-locator domain registration and service-notifier instance 74 lookup/publication.",
        "- Do not attempt native Wi-Fi connect/ping until native init proves WLFW service69 and `wlan0`.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1905-manifest", type=Path, default=DEFAULT_V1905_MANIFEST)
    parser.add_argument("--v1904-manifest", type=Path, default=DEFAULT_V1904_MANIFEST)
    parser.add_argument("--service-notifier", type=Path, default=DEFAULT_SERVICE_NOTIFIER)
    parser.add_argument("--service-notifier-private", type=Path, default=DEFAULT_SERVICE_NOTIFIER_PRIVATE)
    parser.add_argument("--service-notifier-public", type=Path, default=DEFAULT_SERVICE_NOTIFIER_PUBLIC)
    parser.add_argument("--icnss", type=Path, default=DEFAULT_ICNSS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    evidence = evidence_summary(args.v1905_manifest, args.v1904_manifest)
    source = source_summary(
        args.service_notifier,
        args.service_notifier_private,
        args.service_notifier_public,
        args.icnss,
    )
    decision, pass_ok, reason, label = classify(evidence, source)
    result = {
        "cycle": "V1906",
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "evidence": evidence,
        "source": source,
        "device_commands_executed": False,
        "device_mutations_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "pmic_gpio_gdsc_regulator_write_executed": False,
        "forced_rc1_case_write_executed": False,
        "subsys_esoc0_open_executed": False,
        "fake_online_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "restart_pd_request_executed": False,
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    write_private_text(args.report, render_report(result))
    print(json.dumps({
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
    }, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
