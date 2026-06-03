#!/usr/bin/env python3
"""V1907 host/source classifier for the service-locator domain-list service74 gap."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1906_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1906-service74-publication-source-classifier" / "manifest.json"
DEFAULT_V1905_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1905-servnotif-stateup-not-msg22-classifier" / "manifest.json"
DEFAULT_V1904_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1904-servnotif-passive-edge-handoff" / "manifest.json"
KERNEL_ROOT = REPO_ROOT / "kernel_build" / "SM-A908N_KOR_12_Opensource" / "Kernel"
DEFAULT_SERVICE_LOCATOR = KERNEL_ROOT / "drivers" / "soc" / "qcom" / "service-locator.c"
DEFAULT_SERVICE_LOCATOR_PUBLIC = KERNEL_ROOT / "include" / "soc" / "qcom" / "service-locator.h"
DEFAULT_SERVICE_LOCATOR_PRIVATE = KERNEL_ROOT / "drivers" / "soc" / "qcom" / "service-locator-private.h"
DEFAULT_ICNSS = KERNEL_ROOT / "drivers" / "soc" / "qcom" / "icnss.c"
DEFAULT_SERVICE_NOTIFIER = KERNEL_ROOT / "drivers" / "soc" / "qcom" / "service-notifier.c"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1907-servloc-domain-service74-gap-classifier"
DEFAULT_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1907_SERVLOC_DOMAIN_SERVICE74_GAP_CLASSIFIER_2026-06-03.md"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


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


def zero_csv(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and all(intish(part) == 0 for part in parts)


def positive_csv(value: object) -> bool:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    return bool(parts) and any(intish(part) > 0 for part in parts)


def line_no(text: str, pattern: str) -> int | None:
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def line_ref(path: Path, text: str, pattern: str) -> str:
    line = line_no(text, pattern)
    return f"{rel(path)}:{line}" if line else f"{rel(path)}:missing"


def rg_callers() -> list[str]:
    proc = subprocess.run(
        ["rg", "-n", r"service_notif_register_notifier\(", rel(KERNEL_ROOT), "-g", "*.[ch]"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def source_summary(args: argparse.Namespace) -> dict[str, Any]:
    sl = read_text(args.service_locator)
    sl_pub = read_text(args.service_locator_public)
    sl_priv = read_text(args.service_locator_private)
    icnss = read_text(args.icnss)
    sn = read_text(args.service_notifier)
    callers = rg_callers()
    real_callers = [line for line in callers if "/include/" not in line and "service-notifier.c" not in line]
    refs = {
        "locator_get_domain_api": line_ref(args.service_locator, sl, r"int get_service_location\("),
        "locator_qmi_send_domain_req": line_ref(args.service_locator, sl, r"QMI_SERVREG_LOC_GET_DOMAIN_LIST_REQ_V01"),
        "locator_store_response": line_ref(args.service_locator, sl, r"static void store_get_domain_list_response"),
        "locator_copy_instance": line_ref(args.service_locator, sl, r"pd->domain_list\[i\]\.instance_id\s*="),
        "locator_copy_name": line_ref(args.service_locator, sl, r"strlcpy\(pd->domain_list\[i\]\.name"),
        "locator_notify_up": line_ref(args.service_locator, sl, r"notifier_call\(pdqw->notifier, LOCATOR_UP, data\)"),
        "public_domain_entry": line_ref(args.service_locator_public, sl_pub, r"struct servreg_loc_entry_v01"),
        "public_instance_id_field": line_ref(args.service_locator_public, sl_pub, r"uint32_t instance_id"),
        "private_domain_resp": line_ref(args.service_locator_private, sl_priv, r"struct qmi_servreg_loc_get_domain_list_resp_msg_v01"),
        "private_domain_list_len": line_ref(args.service_locator_private, sl_priv, r"uint32_t domain_list_len"),
        "private_domain_list": line_ref(args.service_locator_private, sl_priv, r"domain_list\[QMI_SERVREG_LOC_LIST_LENGTH_V01\]"),
        "icnss_get_service_location": line_ref(args.icnss, icnss, r"get_service_location\(ICNSS_SERVICE_LOCATION_CLIENT_NAME"),
        "icnss_locator_notify": line_ref(args.icnss, icnss, r"static int icnss_get_service_location_notify"),
        "icnss_domain_loop": line_ref(args.icnss, icnss, r"for \(i = 0; i < pd->total_domains; i\+\+\)"),
        "icnss_register_notifier": line_ref(args.icnss, icnss, r"service_notif_register_notifier\(pd->domain_list\[i\]\.name,"),
        "sn_new_server_instance": line_ref(args.service_notifier, sn, r"Connection established between QMI handle and %d service"),
    }
    required = [
        "locator_get_domain_api", "locator_qmi_send_domain_req", "locator_store_response",
        "locator_copy_instance", "locator_copy_name", "locator_notify_up", "public_domain_entry",
        "public_instance_id_field", "private_domain_resp", "private_domain_list_len",
        "private_domain_list", "icnss_get_service_location", "icnss_locator_notify",
        "icnss_domain_loop", "icnss_register_notifier", "sn_new_server_instance",
    ]
    return {
        "refs": refs,
        "required_markers_ok": all(not refs[key].endswith(":missing") for key in required),
        "register_callers": callers,
        "real_register_callers": real_callers,
        "single_real_register_caller_is_icnss": len(real_callers) == 1 and "icnss.c" in real_callers[0],
    }


def evidence_summary(args: argparse.Namespace) -> dict[str, Any]:
    v1906 = read_json(args.v1906_manifest)
    v1905 = read_json(args.v1905_manifest)
    v1904 = read_json(args.v1904_manifest)
    android = v1905.get("android") or {}
    native = v1905.get("native") or {}
    gate = v1904.get("gate") or {}
    return {
        "v1906_decision": v1906.get("decision", ""),
        "v1906_label": v1906.get("label", ""),
        "v1906_pass": boolish(v1906.get("pass")),
        "v1905_decision": v1905.get("decision", ""),
        "v1905_label": v1905.get("label", ""),
        "v1905_pass": boolish(v1905.get("pass")),
        "android_ordered": boolish(android.get("ordered_internal_stateup")),
        "android_service74_count": intish(android.get("service74_count")),
        "android_service180_count": intish(android.get("service180_count")),
        "android_wlan_pd_count": intish(android.get("wlan_pd_count")),
        "android_wlan0_time_s": android.get("wlan0_time_s"),
        "android_pcie_mhi_before_wlan0": intish(android.get("pcie_mhi_before_wlan0")),
        "android_degraded_257s_like": boolish(android.get("degraded_257s_like")),
        "native_service180_counts": native.get("v1816_service180_counts", ""),
        "native_service74_counts": native.get("v1816_service74_counts", ""),
        "native_wlan_pd_counts": native.get("v1816_wlan_pd_counts", ""),
        "native_servloc_domain_count": gate.get("servloc_domain_count", ""),
        "native_servloc_domain0_name": gate.get("servloc_domain0_name", ""),
        "native_servloc_domain0_instance_id": gate.get("servloc_domain0_instance_id", ""),
        "native_servloc_result": gate.get("servloc_domain_result", ""),
        "native_servloc_endpoint_status": gate.get("servloc_domain_endpoint_status", ""),
        "native_wlfw69_seen": native.get("wlfw_service69_seen", ""),
        "native_wlan0_present": native.get("wlan0_present", ""),
    }


def classify(evidence: dict[str, Any], source: dict[str, Any]) -> tuple[str, bool, str, str]:
    android_ok = (
        evidence["v1906_pass"] and evidence["v1905_pass"] and evidence["android_ordered"]
        and evidence["android_service74_count"] > 0 and evidence["android_service180_count"] > 0
        and evidence["android_wlan_pd_count"] > 0 and evidence["android_wlan0_time_s"] is not None
        and evidence["android_pcie_mhi_before_wlan0"] == 0 and not evidence["android_degraded_257s_like"]
    )
    native_ok = (
        positive_csv(evidence["native_service180_counts"])
        and zero_csv(evidence["native_service74_counts"])
        and zero_csv(evidence["native_wlan_pd_counts"])
        and str(evidence["native_servloc_domain_count"]) == "1"
        and evidence["native_servloc_domain0_name"] == "msm/modem/wlan_pd"
        and str(evidence["native_servloc_domain0_instance_id"]) == "180"
        and str(evidence["native_wlfw69_seen"]) in {"", "0"}
        and str(evidence["native_wlan0_present"]) in {"", "0"}
    )
    source_ok = source["required_markers_ok"] and source["single_real_register_caller_is_icnss"]
    if not android_ok:
        return ("v1907-android-service74-domain-edge-incomplete", False,
                "Android-good evidence does not prove service74/180 before wlan_pd/wlan0", "android-service74-domain-edge-incomplete")
    if not native_ok:
        return ("v1907-native-servloc-domain-gap-incomplete", False,
                "native evidence does not prove one-domain service-locator response with only instance 180", "native-servloc-domain-gap-incomplete")
    if not source_ok:
        return ("v1907-servloc-source-caller-gap-incomplete", False,
                "source does not prove service-locator domain-list is the unique ICNSS path into service-notifier registration", "servloc-source-caller-gap-incomplete")
    return ("v1907-servloc-domain-list-missing-service74-host-pass", True,
            "native service-locator returns only msm/modem/wlan_pd instance 180, while Android normal reaches service-notifier 74+180; source shows ICNSS is the only real service-notifier register caller and consumes service-locator domain_list entries", "servloc-domain-list-missing-service74")


def render_report(result: dict[str, Any]) -> str:
    ev = result["evidence"]
    src = result["source"]
    refs = src["refs"]
    return "\n".join([
        "# Native Init V1907 Service-locator Domain Service74 Gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1907`",
        "- Type: host/source classifier over service-locator, ICNSS, service-notifier source and V1904/V1905/V1906 evidence",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Evidence Edge",
        "",
        f"- V1906 decision/label/pass: `{ev['v1906_decision']}` / `{ev['v1906_label']}` / `{ev['v1906_pass']}`",
        f"- Android service74/service180/wlan_pd/wlan0: `{ev['android_service74_count']}` / `{ev['android_service180_count']}` / `{ev['android_wlan_pd_count']}` / `{ev['android_wlan0_time_s']}`",
        f"- Android contamination pre-wlan0 PCIe-MHI/degraded257: `{ev['android_pcie_mhi_before_wlan0']}` / `{ev['android_degraded_257s_like']}`",
        f"- Native service180/service74/wlan_pd: `{ev['native_service180_counts']}` / `{ev['native_service74_counts']}` / `{ev['native_wlan_pd_counts']}`",
        f"- Native service-locator domain count/name/instance/result: `{ev['native_servloc_domain_count']}` / `{ev['native_servloc_domain0_name']}` / `{ev['native_servloc_domain0_instance_id']}` / `{ev['native_servloc_result']}`",
        f"- Native lower gates WLFW69/wlan0: `{ev['native_wlfw69_seen']}` / `{ev['native_wlan0_present']}`",
        "",
        "## Source Edge",
        "",
        f"- service-locator sends get-domain-list QMI and copies response entries into `pd->domain_list`: `{refs['locator_get_domain_api']}`, `{refs['locator_qmi_send_domain_req']}`, `{refs['locator_store_response']}`, `{refs['locator_copy_instance']}`, `{refs['locator_copy_name']}`",
        f"- service-locator delivers `LOCATOR_UP` with that domain list to ICNSS: `{refs['locator_notify_up']}`, `{refs['icnss_get_service_location']}`, `{refs['icnss_locator_notify']}`",
        f"- ICNSS loops over each domain and calls service-notifier with `name` and `instance_id`: `{refs['icnss_domain_loop']}`, `{refs['icnss_register_notifier']}`",
        f"- service-notifier new-server log exposes the same instance id: `{refs['sn_new_server_instance']}`",
        f"- real service-notifier register callers: `{json.dumps(src['real_register_callers'], ensure_ascii=False)}`",
        "",
        "## Selected Diff",
        "",
        f"- Label: `{result['label']}`.",
        "- Native is missing service-locator domain-list entry/instance 74 before service-notifier lookup, listener msg20, wlan_pd state-up msg22, WLFW69, and wlan0.",
        "- Android normal proves that the internal modem can publish both service-notifier instances 74 and 180 before wlan_pd and wlan0 without PCIe/MHI or pm-service msg22.",
        "- The next useful live unit is a read-only internal-modem observer for the service-locator get-domain-list response and ICNSS domain registration arguments.",
        "",
        "## Safety Scope",
        "",
        "V1907 is host-only. It reads retained manifests and local kernel source only, and writes local evidence/report artifacts. It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.",
        "",
        "## Next",
        "",
        "- Build the next rollbackable native observer to capture service-locator response domain entries and ICNSS `service_notif_register_notifier` arguments before any functional Wi-Fi bring-up attempt.",
        "- Do not attempt Wi-Fi connect/ping until native init proves WLFW service69 and `wlan0`.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1906-manifest", type=Path, default=DEFAULT_V1906_MANIFEST)
    parser.add_argument("--v1905-manifest", type=Path, default=DEFAULT_V1905_MANIFEST)
    parser.add_argument("--v1904-manifest", type=Path, default=DEFAULT_V1904_MANIFEST)
    parser.add_argument("--service-locator", type=Path, default=DEFAULT_SERVICE_LOCATOR)
    parser.add_argument("--service-locator-public", type=Path, default=DEFAULT_SERVICE_LOCATOR_PUBLIC)
    parser.add_argument("--service-locator-private", type=Path, default=DEFAULT_SERVICE_LOCATOR_PRIVATE)
    parser.add_argument("--icnss", type=Path, default=DEFAULT_ICNSS)
    parser.add_argument("--service-notifier", type=Path, default=DEFAULT_SERVICE_NOTIFIER)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    evidence = evidence_summary(args)
    source = source_summary(args)
    decision, pass_ok, reason, label = classify(evidence, source)
    result = {
        "cycle": "V1907",
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
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    write_private_text(args.report, report)
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
