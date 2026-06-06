#!/usr/bin/env python3
"""V1892 host-only classifier for the PM ack/open versus WLAN guest-PD trigger boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1892-pm-ack-open-trigger-boundary"
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1892_PM_ACK_OPEN_TRIGGER_BOUNDARY_2026-06-03.md"
)
DEFAULT_V1842_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1842-post-ack-no-powerup-classifier" / "manifest.json"
DEFAULT_V1885_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1885-internal-pm-qmi-servreg-trigger-source-diff" / "manifest.json"
)
DEFAULT_V1886_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1886-internal-servloc-msg22-stateup-classifier" / "manifest.json"
)
DEFAULT_V1888_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1888-pm-msgid-capture-diff-classifier" / "manifest.json"
DEFAULT_V1891_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1891-android-capture-parser-handoff" / "manifest.json"


def rel(path: Path) -> str:
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


def callback_ack_summary(v1842: dict[str, Any]) -> dict[str, Any]:
    details = v1842.get("details") or {}
    v1841 = details.get("v1841") or {}
    return {
        "manifest_label": v1842.get("label", ""),
        "manifest_decision": v1842.get("decision", ""),
        "manifest_pass": boolish(v1842.get("pass")),
        "callback_ack_label": v1841.get("callback_ack_label", ""),
        "callback_ack_total": intish(v1841.get("callback_ack_hit_count_total")),
        "missing_callback_ack_keys": v1841.get("missing_callback_ack_keys") or [],
        "zero_callback_ack_keys": v1841.get("zero_callback_ack_keys") or [],
        "pm_client_register_rc": str(v1841.get("pm_client_register_rc", "")),
        "pm_client_connect_rc": str(v1841.get("pm_client_connect_rc", "")),
        "requested_wlanmdsp": str(v1841.get("requested_wlanmdsp", "")),
        "lower_service69_progress": boolish(v1841.get("lower_service69_progress")),
        "lower_wlan0_present": boolish(v1841.get("lower_wlan0_present")),
        "servnotif_label": v1841.get("servnotif_label", ""),
    }


def native_post_open_summary(v1885: dict[str, Any]) -> dict[str, Any]:
    native = v1885.get("native_post_open") or {}
    source = v1885.get("source") or {}
    return {
        "manifest_label": v1885.get("label", ""),
        "manifest_decision": v1885.get("decision", ""),
        "manifest_pass": boolish(v1885.get("pass")),
        "open_context_path": native.get("open_context_path", ""),
        "open_context_fd": native.get("open_context_fd", ""),
        "open_context_power_state": native.get("open_context_power_state", ""),
        "pm_client_register_rc": str(native.get("pm_client_register_rc", "")),
        "pm_client_connect_rc": str(native.get("pm_client_connect_rc", "")),
        "post_ack_label": native.get("post_ack_label", ""),
        "post_ack_open_call_hits": intish(native.get("post_ack_open_call_hits")),
        "post_ack_open_ret_hits": intish(native.get("post_ack_open_ret_hits")),
        "post_ack_msg22_ind_hits": intish(native.get("post_ack_qmi_restart_ind_hits")),
        "wlfw_service_request_hits": intish(native.get("wlfw_service_request_hits")),
        "wlfw_ind_register_hits": intish(native.get("wlfw_ind_register_qmi_hits")),
        "wlfw_cap_hits": intish(native.get("wlfw_cap_qmi_hits")),
        "requested_wlanmdsp": str(native.get("requested_wlanmdsp", "")),
        "wlfw_service69_seen": str(native.get("wlfw_service69_seen", "")),
        "wlan0_present": str(native.get("wlan0_present", "")),
        "early_servnotif_state": native.get("early_servnotif_state", ""),
        "late_servnotif_state": native.get("late_servnotif_state", ""),
        "pm_msg22_source_ready": (
            bool(source.get("pm_msgid_0x22_dispatch"))
            and bool(source.get("pm_msg22_request_string"))
            and bool(source.get("pm_msg22_response_call"))
            and bool(source.get("pm_post_ack_msg22_indication"))
        ),
        "libperipheral_qmi_imports": bool(source.get("libperipheral_qmi_imports")),
    }


def servloc_summary(v1886: dict[str, Any]) -> dict[str, Any]:
    servloc = v1886.get("v1834_servloc") or {}
    return {
        "manifest_label": v1886.get("label", ""),
        "manifest_decision": v1886.get("decision", ""),
        "manifest_pass": boolish(v1886.get("pass")),
        "domain_present": str(servloc.get("domain_present", "")),
        "domain_name": servloc.get("domain_name", ""),
        "domain_instance": str(servloc.get("domain_instance", "")),
        "early_state": servloc.get("early_state", ""),
        "late_state": servloc.get("late_state", ""),
        "early_indication": str(servloc.get("early_indication", "")),
        "late_indication": str(servloc.get("late_indication", "")),
        "raw_service180_counts": servloc.get("raw_service180_counts", ""),
        "raw_service74_counts": servloc.get("raw_service74_counts", ""),
        "raw_wlan_pd_counts": servloc.get("raw_wlan_pd_counts", ""),
        "wlfw_service69_seen": str(servloc.get("wlfw_service69_seen", "")),
        "requested_wlanmdsp": str(servloc.get("requested_wlanmdsp", "")),
        "wlan0_present": str(servloc.get("wlan0_present", "")),
    }


def android_summary(v1888: dict[str, Any]) -> dict[str, Any]:
    android = v1888.get("android_capture") or {}
    return {
        "manifest_label": v1888.get("label", ""),
        "manifest_decision": v1888.get("decision", ""),
        "manifest_pass": boolish(v1888.get("pass")),
        "android_dir": android.get("android_dir", ""),
        "pm_vote_count": intish(android.get("pm_vote_count")),
        "wlfw_service_request_count": intish(android.get("wlfw_service_request_count")),
        "wlan_pd_indication_count": intish(android.get("wlan_pd_indication_count")),
        "wlanmdsp_count": intish(android.get("wlanmdsp_count")),
        "wlan0_time_s": android.get("wlan0_time_s"),
        "pcie_mhi_before_wlan0": intish(android.get("pcie_mhi_before_wlan0")),
        "esoc_boot_failed_before_wlan0": intish(android.get("esoc_boot_failed_before_wlan0")),
        "degraded_257s_like": boolish(android.get("degraded_257s_like")),
        "pm_msg22_hits": intish(android.get("pm_msg22_hits")),
        "pm_msg22_first_line": android.get("pm_msg22_first_line", ""),
        "servnotif_first_line": android.get("servnotif_first_line", ""),
        "wlanmdsp_first_line": android.get("wlanmdsp_first_line", ""),
    }


def handoff_summary(v1891: dict[str, Any]) -> dict[str, Any]:
    checks = v1891.get("checks") or {}
    return {
        "manifest_label": v1891.get("label", ""),
        "manifest_decision": v1891.get("decision", ""),
        "manifest_pass": boolish(v1891.get("pass")),
        "required_parser_inputs_declared": boolish(checks.get("required_parser_inputs_declared")),
        "forbidden_command_surface_absent": boolish(checks.get("forbidden_command_surface_absent")),
        "future_commands": v1891.get("future_commands") or [],
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1842 = read_json(args.v1842_manifest)
    v1885 = read_json(args.v1885_manifest)
    v1886 = read_json(args.v1886_manifest)
    v1888 = read_json(args.v1888_manifest)
    v1891 = read_json(args.v1891_manifest)
    ack = callback_ack_summary(v1842)
    native = native_post_open_summary(v1885)
    servloc = servloc_summary(v1886)
    android = android_summary(v1888)
    handoff = handoff_summary(v1891)
    try:
        wlan0_time = float(android["wlan0_time_s"])
    except (TypeError, ValueError):
        wlan0_time = 9999.0
    checks = {
        "callback_ack_present": (
            ack["manifest_pass"]
            and ack["manifest_label"] == "post-ack-no-powerup-gap"
            and ack["callback_ack_total"] > 0
            and not ack["missing_callback_ack_keys"]
            and not ack["zero_callback_ack_keys"]
            and ack["pm_client_register_rc"] == "0"
            and ack["pm_client_connect_rc"] == "0"
        ),
        "callback_ack_not_trigger": (
            ack["requested_wlanmdsp"] == "0"
            and not ack["lower_service69_progress"]
            and not ack["lower_wlan0_present"]
            and ack["servnotif_label"] == "service-notifier-uninit"
        ),
        "modem_open_present": (
            native["manifest_pass"]
            and native["open_context_path"] == "/dev/subsys_modem"
            and native["open_context_fd"] != ""
            and native["pm_client_register_rc"] == "0"
            and native["pm_client_connect_rc"] == "0"
            and native["post_ack_open_call_hits"] > 0
            and native["post_ack_open_ret_hits"] > 0
        ),
        "modem_open_not_trigger": (
            native["post_ack_msg22_ind_hits"] == 0
            and native["wlfw_ind_register_hits"] == 0
            and native["wlfw_cap_hits"] == 0
            and native["requested_wlanmdsp"] == "0"
            and native["wlfw_service69_seen"] == "0"
            and native["wlan0_present"] == "0"
            and native["early_servnotif_state"] == "uninit"
            and native["late_servnotif_state"] == "uninit"
        ),
        "pm_msg22_source_candidate": native["pm_msg22_source_ready"] and not native["libperipheral_qmi_imports"],
        "servloc_discovery_not_trigger": (
            servloc["manifest_pass"]
            and servloc["domain_present"] == "1"
            and servloc["domain_name"] == "msm/modem/wlan_pd"
            and servloc["domain_instance"] == "180"
            and servloc["early_state"] == "uninit"
            and servloc["late_state"] == "uninit"
            and servloc["requested_wlanmdsp"] == "0"
            and servloc["wlfw_service69_seen"] == "0"
            and servloc["wlan0_present"] == "0"
        ),
        "android_normal_stateup": (
            android["manifest_pass"]
            and android["pm_vote_count"] > 0
            and android["wlfw_service_request_count"] > 0
            and android["wlan_pd_indication_count"] > 0
            and android["wlanmdsp_count"] > 0
            and wlan0_time <= 120.0
            and android["pcie_mhi_before_wlan0"] == 0
            and android["esoc_boot_failed_before_wlan0"] == 0
            and not android["degraded_257s_like"]
        ),
        "android_msgid_observability_gap": (
            android["manifest_label"] == "android-stateup-without-msg22-log-observability-gap"
            and android["pm_msg22_hits"] == 0
        ),
        "capture_handoff_ready": (
            handoff["manifest_pass"]
            and handoff["manifest_label"] == "android-capture-parser-handoff-ready"
            and handoff["required_parser_inputs_declared"]
            and handoff["forbidden_command_surface_absent"]
        ),
    }
    if all(checks.values()):
        decision = "v1892-pm-ack-open-not-guest-pd-trigger-host-pass"
        label = "pm-ack-open-not-guest-pd-trigger"
        reason = (
            "PM callback/ack and /dev/subsys_modem open are both proven on native, but neither produces "
            "msg22 indication, wlan_pd state-up, WLFW service 69, wlanmdsp, or wlan0; the remaining discriminator "
            "is the normal-Android post-vote msg22/servreg/SSCTL transition"
        )
        passed = True
    else:
        decision = "v1892-pm-ack-open-boundary-incomplete"
        label = "pm-ack-open-boundary-incomplete"
        reason = "one or more prior ack/open/servloc/Android-normal/handoff prerequisites are missing"
        passed = False
    return {
        "cycle": "V1892",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "inputs": {
            "v1842_manifest": rel(args.v1842_manifest),
            "v1885_manifest": rel(args.v1885_manifest),
            "v1886_manifest": rel(args.v1886_manifest),
            "v1888_manifest": rel(args.v1888_manifest),
            "v1891_manifest": rel(args.v1891_manifest),
        },
        "checks": checks,
        "callback_ack": ack,
        "native_post_open": native,
        "servloc": servloc,
        "android_normal": android,
        "handoff": handoff,
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
            "esoc_notify_boot_done": False,
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    ack = result["callback_ack"]
    native = result["native_post_open"]
    servloc = result["servloc"]
    android = result["android_normal"]
    checks = result["checks"]
    safety = result["safety"]
    handoff = result["handoff"]
    future_commands = handoff["future_commands"]
    capture_command = future_commands[0] if len(future_commands) > 0 else ""
    parser_command = future_commands[1] if len(future_commands) > 1 else ""
    return "\n".join(
        [
            "# Native Init V1892 PM Ack/Open Trigger Boundary",
            "",
            "## Summary",
            "",
            "- Cycle: `V1892`",
            "- Type: host-only classifier for PM callback/ack and `/dev/subsys_modem` open versus WLAN guest-PD trigger",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Boundary Checks",
            "",
            f"- callback ack present/not-trigger: `{checks['callback_ack_present']}` / `{checks['callback_ack_not_trigger']}`",
            f"- modem open present/not-trigger: `{checks['modem_open_present']}` / `{checks['modem_open_not_trigger']}`",
            f"- msg22 source candidate: `{checks['pm_msg22_source_candidate']}`",
            f"- servloc discovery not-trigger: `{checks['servloc_discovery_not_trigger']}`",
            f"- Android normal state-up/msgid gap: `{checks['android_normal_stateup']}` / `{checks['android_msgid_observability_gap']}`",
            f"- capture handoff ready: `{checks['capture_handoff_ready']}`",
            "",
            "## Native Proven Boundary",
            "",
            f"- PM callback/ack label/hits: `{ack['callback_ack_label']}` / `{ack['callback_ack_total']}`",
            f"- PM register/connect rc: `{ack['pm_client_register_rc']}` / `{ack['pm_client_connect_rc']}`",
            f"- open path/fd/state: `{native['open_context_path']}` / `{native['open_context_fd']}` / `{native['open_context_power_state']}`",
            f"- post-ack open/msg22 hits: `{native['post_ack_open_call_hits']}` / `{native['post_ack_msg22_ind_hits']}`",
            f"- native WLFW ind/cap/wlanmdsp/WLFW69/wlan0: `{native['wlfw_ind_register_hits']}` / `{native['wlfw_cap_hits']}` / `{native['requested_wlanmdsp']}` / `{native['wlfw_service69_seen']}` / `{native['wlan0_present']}`",
            f"- native service-notifier state: `{native['early_servnotif_state']}` -> `{native['late_servnotif_state']}`",
            "",
            "## Servloc And Android",
            "",
            f"- servloc domain/name/instance: `{servloc['domain_present']}` / `{servloc['domain_name']}` / `{servloc['domain_instance']}`",
            f"- servloc state/indication: `{servloc['early_state']}` -> `{servloc['late_state']}` / `{servloc['early_indication']}` -> `{servloc['late_indication']}`",
            f"- Android PM vote/WLFW request/wlan_pd/wlanmdsp/wlan0: `{android['pm_vote_count']}` / `{android['wlfw_service_request_count']}` / `{android['wlan_pd_indication_count']}` / `{android['wlanmdsp_count']}` / `{android['wlan0_time_s']}`",
            f"- Android contamination counts: PCIe-MHI `{android['pcie_mhi_before_wlan0']}` / esoc-boot-failed `{android['esoc_boot_failed_before_wlan0']}` / degraded257 `{android['degraded_257s_like']}`",
            f"- retained Android msg22 hits: `{android['pm_msg22_hits']}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- The native PM callback/transact/ack path and `/dev/subsys_modem` open are sufficient to prove PM plumbing, but insufficient to start `msm/modem/wlan_pd`.",
            "- Service-locator discovery is also insufficient: the `msm/modem/wlan_pd` domain is resolvable while the service-notifier state stays `uninit`.",
            "- The remaining trigger evidence must come from a normal Android post-vote PM msg-id/servreg/SSCTL capture, then V1888 parsing against native post-open absence.",
            "",
            "## Handoff Commands",
            "",
            f"- Capture command: `{capture_command}`",
            f"- Parser command: `{parser_command}`",
            "",
            "## Safety Scope",
            "",
            f"- host-only/device-contact: `{safety['host_only']}` / `{safety['device_contact']}`",
            f"- Wi-Fi HAL/scan-connect/credential/DHCP/routes/ping: `{safety['wifi_hal']}` / `{safety['scan_connect']}` / `{safety['credential_use']}` / `{safety['dhcp_routes']}` / `{safety['external_ping']}`",
            f"- PMIC-GPIO-GDSC/forced-RC1/subsys-esoc0/eSoC notify/PCI rescan/platform bind: `{safety['pmic_gpio_gdsc_write']}` / `{safety['forced_rc1_case']}` / `{safety['subsys_esoc0_open']}` / `{safety['esoc_notify_boot_done']}` / `{safety['pci_rescan']}` / `{safety['platform_bind_unbind']}`",
            "",
            "## Next",
            "",
            "- Run the capture command only on normal Android with ADB/root available; reject degraded 257s captures and any pre-wlan0 PCIe/MHI path.",
            "- Do not replay native msg22, force subsystem state, or touch eSoC/PCIe/GDSC; first prove the Android post-vote request that precedes `wlanmdsp.mbn`.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1842-manifest", type=Path, default=DEFAULT_V1842_MANIFEST)
    parser.add_argument("--v1885-manifest", type=Path, default=DEFAULT_V1885_MANIFEST)
    parser.add_argument("--v1886-manifest", type=Path, default=DEFAULT_V1886_MANIFEST)
    parser.add_argument("--v1888-manifest", type=Path, default=DEFAULT_V1888_MANIFEST)
    parser.add_argument("--v1891-manifest", type=Path, default=DEFAULT_V1891_MANIFEST)
    args = parser.parse_args()

    result = analyze(args)
    store = EvidenceStore(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    store.write_text("host/boundary-checks.json", json.dumps(result["checks"], indent=2, sort_keys=True) + "\n")
    store.write_text("host/native-boundary.json", json.dumps(result["native_post_open"], indent=2, sort_keys=True) + "\n")
    store.write_text("host/android-normal.json", json.dumps(result["android_normal"], indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
