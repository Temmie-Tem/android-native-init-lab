#!/usr/bin/env python3
"""V1839 host-only classifier for the V1838 lower-continuation static gap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1839"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1839-lower-continuation-gap-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1839_LOWER_CONTINUATION_GAP_CLASSIFIER_2026-06-03.md"
)

V1838_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1838-wlan-pd-lower-continuation-sampler-handoff" / "manifest.json"
V1836_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1836-wlan-pd-uninit-transition-classifier" / "manifest.json"
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
    return str(value) in {"1", "True", "true", "yes"}


def source_summary(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "label": manifest.get("label", ""),
        "reason": manifest.get("reason", ""),
    }


def sample_field(samples: list[dict[str, Any]], key: str) -> list[Any]:
    return [sample.get(key, "") for sample in samples]


def collect_details(
    v1838: dict[str, Any],
    v1836: dict[str, Any],
    v1760: dict[str, Any],
    v1738: dict[str, Any],
    v1244: dict[str, Any],
) -> dict[str, Any]:
    gate = v1838.get("gate") or {}
    samples = gate.get("pm_focus_samples") or []
    current1836 = (v1836.get("details") or {}).get("current") or {}
    android1760 = v1760.get("android") or {}
    native1760 = (v1760.get("native") or {}).get("gate") or {}
    checks1738 = v1738.get("checks") or {}
    source1738 = (v1738.get("evidence") or {}).get("source") or {}
    android1244 = v1244.get("android") or {}
    native1244 = v1244.get("native") or {}
    native1244_first = native1244.get("first_sample") or {}

    return {
        "sources": {
            "v1838": source_summary(v1838, V1838_MANIFEST),
            "v1836": source_summary(v1836, V1836_MANIFEST),
            "v1760": source_summary(v1760, V1760_MANIFEST),
            "v1738": source_summary(v1738, V1738_MANIFEST),
            "v1244": source_summary(v1244, V1244_MANIFEST),
        },
        "v1838": {
            "handoff_pass": bool(v1838.get("pass")),
            "rollback_ok": bool((v1838.get("rollback") or {}).get("ok")),
            "post_version_ok": bool((v1838.get("post_rollback_verification") or {}).get("version_ok")),
            "post_selftest_fail_zero": bool((v1838.get("post_rollback_verification") or {}).get("selftest_fail_zero")),
            "lower_continuation_label": gate.get("lower_continuation_label", ""),
            "pm_focus_contract_ok": bool(gate.get("pm_focus_contract_ok")),
            "pm_focus_safety_ok": bool(gate.get("pm_focus_safety_ok")),
            "pm_focus_change_fields": gate.get("pm_focus_change_fields") or [],
            "pm_focus_mdm_status_delta": gate.get("pm_focus_mdm_status_delta"),
            "pm_focus_mhi_wlan0_progress": bool(gate.get("pm_focus_mhi_wlan0_progress")),
            "powerup_thread_counts": sample_field(samples, "powerup_powerup_thread_count"),
            "subsys_esoc0_open_inferred": sample_field(samples, "powerup_subsys_esoc0_open_inferred"),
            "per_mgr_process_counts": sample_field(samples, "powerup_per_mgr_process_count"),
            "mdm3_states": sample_field(samples, "mdm3_state"),
            "mdm_status_counts": sample_field(samples, "mdm_status_count_total"),
            "pcie1_gdsc_lines": sample_field(samples, "pcie1_gdsc_line"),
            "pcie0_gdsc_lines": sample_field(samples, "pcie0_gdsc_line"),
            "pmic_soft_reset_lines": sample_field(samples, "pmic_soft_reset_line"),
            "mhi_bus_counts": sample_field(samples, "mhi_bus_count"),
            "mhi_pipe_exists": sample_field(samples, "mhi_pipe_exists"),
            "wlan0_exists": sample_field(samples, "wlan0_exists"),
            "line_request_flags": sample_field(samples, "gpiochip_line_request_executed"),
            "pmic_write_flags": sample_field(samples, "pmic_write_executed"),
            "esoc_ioctl_flags": sample_field(samples, "esoc_ioctl_executed"),
            "pm_service_first_count": gate.get("pm_service_first_count", ""),
            "pm_service_second_count": gate.get("pm_service_second_count", ""),
            "pm_service_first_add_names": gate.get("pm_service_first_add_names", ""),
            "pm_service_first_add_devnodes": gate.get("pm_service_first_add_devnodes", ""),
            "pm_service_list_commit_hits": gate.get("pm_service_add_peripheral_list_commit_hits", ""),
            "pm_service_init_fail_hits": gate.get("pm_service_add_peripheral_init_fail_hits", ""),
            "pm_server_label": gate.get("pm_server_label", ""),
            "pm_server_success_return_hits": gate.get("pm_server_success_return_hits", ""),
            "provider_seen": gate.get("provider_seen", ""),
            "as_interface_hits": gate.get("as_interface_hits", ""),
            "register_tx_hits": gate.get("register_tx_hits", ""),
            "requested_wlanmdsp": gate.get("requested_wlanmdsp", ""),
            "servnotif_label": gate.get("servnotif_label", ""),
            "qipcrtr_bound_recv_label": gate.get("qipcrtr_bound_recv_label", ""),
            "lower_state_label": gate.get("post_pm_lower_state_label", ""),
            "lower_mdm3_states": gate.get("lower_mdm3_states", ""),
            "lower_mhi_present": gate.get("lower_mhi_present"),
            "lower_service69_progress": gate.get("lower_service69_progress"),
            "lower_wlan0_present": gate.get("lower_wlan0_present"),
        },
        "prior": {
            "v1836_reason": v1836.get("reason", ""),
            "v1836_requested_wlanmdsp": current1836.get("requested_wlanmdsp", ""),
            "v1836_wlfw_service69": current1836.get("wlfw_service69_seen", ""),
            "v1836_wlan0": current1836.get("wlan0_present", ""),
            "v1760_android_requested_wlanmdsp": android1760.get("requested_wlanmdsp"),
            "v1760_android_vendor_firmware_fallback": (android1760.get("served_path") or {}).get("vendor_firmware_attempt_seen"),
            "v1760_native_requested_wlanmdsp": native1760.get("requested_wlanmdsp", ""),
            "v1738_android_companion_services": checks1738.get("android_companion_services_running"),
            "v1738_android_reaches_wlan_pd_wlan0": checks1738.get("android_good_reaches_wlan_pd_and_wlan0"),
            "v1738_android_no_restart_pd": checks1738.get("android_no_restart_pd_marker"),
            "v1738_icnss_lookup_passive": checks1738.get("icnss_fw_lookup_is_passive"),
            "v1738_listener_state_query": checks1738.get("listener_register_is_state_query"),
            "v1738_restart_pd_explicit": checks1738.get("restart_pd_is_explicit_recovery_api_only"),
            "v1738_source_lookup_line": source1738.get("qmi_add_lookup_line", ""),
            "v1738_source_restart_pd_line": source1738.get("service_notifier_restart_pd_line", ""),
            "v1244_android_pcie_rc1": android1244.get("pcie_rc1_report_line", ""),
            "v1244_native_decision": native1244.get("decision", ""),
            "v1244_native_first_mdm3": native1244_first.get("mdm3_state", ""),
            "v1244_native_pcie1_gdsc": native1244_first.get("pcie1_gdsc_line", ""),
            "v1244_native_pmic_soft_reset": native1244_first.get("pmic_soft_reset_line", ""),
        },
    }


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    v1838 = details["v1838"]
    sources_ok = all(source["pass"] for source in details["sources"].values())
    rollback_ok = (
        v1838["handoff_pass"]
        and v1838["rollback_ok"]
        and v1838["post_version_ok"]
        and v1838["post_selftest_fail_zero"]
    )
    pm_registered = (
        v1838["pm_service_first_count"] == "2"
        and "SDX50M" in v1838["pm_service_first_add_names"].split(",")
        and "modem" in v1838["pm_service_first_add_names"].split(",")
        and "/dev/subsys_esoc0" in v1838["pm_service_first_add_devnodes"].split(",")
        and "/dev/subsys_modem" in v1838["pm_service_first_add_devnodes"].split(",")
        and intish(v1838["pm_service_list_commit_hits"]) >= 2
        and intish(v1838["pm_service_init_fail_hits"]) == 0
        and v1838["pm_server_label"] == "pm-server-register-success-return"
        and intish(v1838["pm_server_success_return_hits"]) > 0
        and v1838["provider_seen"] == "1"
        and v1838["as_interface_hits"] == "1"
        and v1838["register_tx_hits"] == "1"
    )
    no_powerup = (
        all(intish(value) == 0 for value in v1838["powerup_thread_counts"])
        and all(intish(value) == 0 for value in v1838["subsys_esoc0_open_inferred"])
        and intish(v1838["pm_focus_mdm_status_delta"]) == 0
        and not v1838["pm_focus_change_fields"]
        and not v1838["pm_focus_mhi_wlan0_progress"]
    )
    static_lower = (
        v1838["lower_continuation_label"] == "lower-continuation-static-gap"
        and v1838["servnotif_label"] == "service-notifier-uninit"
        and v1838["qipcrtr_bound_recv_label"] == "qipcrtr-bound-recv-poll-timeout-passive"
        and v1838["lower_state_label"] == "stable-mdm3-offlining"
        and v1838["lower_mdm3_states"] == "OFFLINING"
        and not boolish(v1838["lower_mhi_present"])
        and not boolish(v1838["lower_service69_progress"])
        and not boolish(v1838["lower_wlan0_present"])
        and v1838["requested_wlanmdsp"] == "0"
    )
    safety_ok = (
        v1838["pm_focus_contract_ok"]
        and v1838["pm_focus_safety_ok"]
        and all(intish(value) == 0 for value in v1838["line_request_flags"])
        and all(intish(value) == 0 for value in v1838["pmic_write_flags"])
        and all(intish(value) == 0 for value in v1838["esoc_ioctl_flags"])
    )

    if not sources_ok:
        return "input-review", "v1839-input-review", "one or more source manifests did not pass", False
    if not rollback_ok:
        return "rollback-review", "v1839-rollback-review", "V1838 handoff or rollback verification is not clean", False
    if not safety_ok:
        return "safety-review", "v1839-safety-review", "V1838 safety flags are not clean", False
    if pm_registered and no_powerup and static_lower:
        return (
            "pm-connect-return-without-powerup-trigger",
            "v1839-pm-connect-return-without-powerup-trigger-host-pass",
            "V1838 proves PM list/register success and static PMIC/GDSC lower state with no mdm_subsys_powerup thread or inferred subsys_esoc0 open",
            True,
        )
    return (
        "lower-continuation-evidence-review",
        "v1839-lower-continuation-evidence-review",
        "V1838 evidence does not match the fixed PM-register-success/no-powerup/static-lower classifier",
        False,
    )


def render_report(result: dict[str, Any]) -> str:
    details = result["details"]
    v1838 = details["v1838"]
    prior = details["prior"]
    sources = details["sources"]
    return "\n".join([
        "# Native Init V1839 Lower-Continuation Gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1839`",
        "- Type: host-only classifier over V1838 live evidence and retained Android-positive references",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Inputs",
        "",
        f"- V1838: `{sources['v1838']['decision']}` / pass `{sources['v1838']['pass']}`",
        f"- V1836: `{sources['v1836']['decision']}` / pass `{sources['v1836']['pass']}`",
        f"- V1760: `{sources['v1760']['decision']}` / pass `{sources['v1760']['pass']}`",
        f"- V1738: `{sources['v1738']['decision']}` / pass `{sources['v1738']['pass']}`",
        f"- V1244: `{sources['v1244']['decision']}` / pass `{sources['v1244']['pass']}`",
        "",
        "## V1838 Current State",
        "",
        f"- handoff/rollback/post-version/post-selftest: `{v1838['handoff_pass']}` / `{v1838['rollback_ok']}` / `{v1838['post_version_ok']}` / `{v1838['post_selftest_fail_zero']}`",
        f"- lower-continuation label: `{v1838['lower_continuation_label']}`",
        f"- PM focus contract/safety/change/delta: `{v1838['pm_focus_contract_ok']}` / `{v1838['pm_focus_safety_ok']}` / `{v1838['pm_focus_change_fields']}` / `{v1838['pm_focus_mdm_status_delta']}`",
        f"- PM-service count/names/devnodes/list-commit/init-fail: `{v1838['pm_service_first_count']}` / `{v1838['pm_service_first_add_names']}` / `{v1838['pm_service_first_add_devnodes']}` / `{v1838['pm_service_list_commit_hits']}` / `{v1838['pm_service_init_fail_hits']}`",
        f"- PM-server/provider/asInterface/registerTX/success: `{v1838['pm_server_label']}` / `{v1838['provider_seen']}` / `{v1838['as_interface_hits']}` / `{v1838['register_tx_hits']}` / `{v1838['pm_server_success_return_hits']}`",
        f"- powerup threads / inferred esoc0 opens: `{v1838['powerup_thread_counts']}` / `{v1838['subsys_esoc0_open_inferred']}`",
        f"- mdm3/status counts: `{v1838['mdm3_states']}` / `{v1838['mdm_status_counts']}`",
        f"- pcie1/pcie0 GDSC: `{v1838['pcie1_gdsc_lines']}` / `{v1838['pcie0_gdsc_lines']}`",
        f"- PMIC soft-reset: `{v1838['pmic_soft_reset_lines']}`",
        f"- MHI/wlan0 samples: bus `{v1838['mhi_bus_counts']}` pipe `{v1838['mhi_pipe_exists']}` wlan0 `{v1838['wlan0_exists']}`",
        f"- service-notifier / QRTR bound labels: `{v1838['servnotif_label']}` / `{v1838['qipcrtr_bound_recv_label']}`",
        f"- lower mdm3/MHI/WLFW69/wlan0/requested-wlanmdsp: `{v1838['lower_mdm3_states']}` / `{v1838['lower_mhi_present']}` / `{v1838['lower_service69_progress']}` / `{v1838['lower_wlan0_present']}` / `{v1838['requested_wlanmdsp']}`",
        "",
        "## Android-Positive Contrast",
        "",
        f"- V1760 Android requested wlanmdsp/vendor fallback: `{prior['v1760_android_requested_wlanmdsp']}` / `{prior['v1760_android_vendor_firmware_fallback']}`",
        f"- V1760 native requested wlanmdsp: `{prior['v1760_native_requested_wlanmdsp']}`",
        f"- V1738 Android companion/WLAN-PD+wlan0/no-restart-PD: `{prior['v1738_android_companion_services']}` / `{prior['v1738_android_reaches_wlan_pd_wlan0']}` / `{prior['v1738_android_no_restart_pd']}`",
        f"- V1244 Android PCIe RC1: `{prior['v1244_android_pcie_rc1']}`",
        f"- V1244 native first mdm3/pcie1/PMIC: `{prior['v1244_native_first_mdm3']}` / `{prior['v1244_native_pcie1_gdsc']}` / `{prior['v1244_native_pmic_soft_reset']}`",
        "",
        "## Interpretation",
        "",
        "- V1838 moves the immediate boundary below PM-service list population and PM-server register success: both SDX50M and modem records are present and list commits succeed.",
        "- The same V1838 route does not enter the lower powerup window: powerup-thread count is zero, inferred `/dev/subsys_esoc0` open is zero, mdm-status count stays zero, PMIC/GDSC text is unchanged, MHI/WLFW/`wlan0` remain absent, and service-notifier stays `uninit`.",
        "- V1244 remains useful as downstream power-surface context, but V1838 shows the immediate current-route target is earlier: PM-client/register-success to PM-service `mdm_subsys_powerup` trigger generation.",
        "- The next unit should be source/build-only first and instrument or classify the read-only PM-client callback/vote-to-powerup transition. It should not add actors, direct eSoC opens, restart-PD, PMIC/GPIO/GDSC writes, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
    ])


def main() -> int:
    v1838 = load_json(V1838_MANIFEST)
    v1836 = load_json(V1836_MANIFEST)
    v1760 = load_json(V1760_MANIFEST)
    v1738 = load_json(V1738_MANIFEST)
    v1244 = load_json(V1244_MANIFEST)
    details = collect_details(v1838, v1836, v1760, v1738, v1244)
    label, decision, reason, pass_ok = classify(details)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": reason,
        "details": details,
        "out_dir": rel(OUT_DIR),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(render_report(result), encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"decision": decision, "label": label, "pass": pass_ok}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
