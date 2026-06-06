#!/usr/bin/env python3
"""V1908 one-run native service-locator domain-list live observer.

This wraps the V1904 rollbackable internal-modem observer and selects the
current blocker more explicitly: native service-locator returns only
`msm/modem/wlan_pd` instance 180, while service-notifier instance 74 and
`wlan_pd` state-up remain absent. It does not start Wi-Fi HAL, scan/connect,
use credentials, DHCP/routes, ping, restart-PD, or touch eSoC/PCIe/GDSC/PMIC/GPIO.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_servnotif_passive_edge_handoff_v1904 as v1904


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1908"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1908-servloc-domain-list-live-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1908_SERVLOC_DOMAIN_LIST_LIVE_HANDOFF_2026-06-03.md"
)
V1907_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1907-servloc-domain-service74-gap-classifier" / "manifest.json"
DMESG_PATTERN = v1904.DMESG_PATTERN + "|get_domain|domain_list|domain_name|LOCATOR_UP|Service locator initialized"


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


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def configure_runner() -> None:
    v1904.CYCLE = CYCLE
    v1904.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1904.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    v1904.DMESG_PATTERN = DMESG_PATTERN
    v1904.configure_runner()


def source_gate() -> dict[str, Any]:
    manifest = read_json(V1907_MANIFEST)
    return {
        "manifest": rel(V1907_MANIFEST),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": boolish(manifest.get("pass")),
        "single_real_register_caller_is_icnss": boolish(
            (manifest.get("source") or {}).get("single_real_register_caller_is_icnss")
        ),
    }


def domain_180_only(details: dict[str, Any]) -> bool:
    return (
        str(details.get("servloc_domain_result", "")) == "domain-list-response-success"
        and str(details.get("servloc_domain_count", "")) == "1"
        and details.get("servloc_domain0_name") == "msm/modem/wlan_pd"
        and str(details.get("servloc_domain0_instance_id", "")) == "180"
    )


def native_absence(details: dict[str, Any]) -> bool:
    return (
        positive_csv(details.get("raw_service180_text_counts"))
        and zero_csv(details.get("raw_service74_text_counts"))
        and zero_csv(details.get("raw_wlan_pd_text_counts"))
        and details.get("servnotif_early_state") == "uninit"
        and details.get("servnotif_late_listener_state") == "uninit"
        and str(details.get("wlfw_service69_seen", "")) in {"", "0"}
        and str(details.get("requested_wlanmdsp", "")) in {"", "0"}
        and str(details.get("wlan0_present", "")) in {"", "0"}
    )


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    base_decision, base_pass, base_reason, details = v1904.classify_gate(
        args, test_flash, rollback_result, evidence_dir
    )
    gate = source_gate()
    details["v1907_manifest"] = gate["manifest"]
    details["v1907_decision"] = gate["decision"]
    details["v1907_label"] = gate["label"]
    details["v1907_pass"] = gate["pass"]
    details["v1907_single_real_register_caller_is_icnss"] = gate["single_real_register_caller_is_icnss"]
    details["servloc_domain_180_only"] = domain_180_only(details)
    details["servloc_native_service74_absence"] = native_absence(details)

    if not base_pass:
        return base_decision, base_pass, base_reason, details
    if not gate["pass"] or not gate["single_real_register_caller_is_icnss"]:
        details["servloc_live_label"] = "source-gate-incomplete"
        return (
            f"{args.cycle.lower()}-source-gate-incomplete-rollback-pass",
            False,
            "V1907 source gate is missing or no longer proves ICNSS is the only real service-notifier register caller",
            details,
        )
    if v1904.prev1834.actual_publication_progress(details) or not boolish(details.get("requested_wlanmdsp_absent")):
        details["servloc_live_label"] = "servloc-domain-list-progress-readonly-stop"
        return (
            f"{args.cycle.lower()}-servloc-domain-list-progress-readonly-stop-rollback-pass",
            True,
            "service74, wlan_pd, WLFW69, requested wlanmdsp, or wlan0 progressed during read-only observer",
            details,
        )
    if bool(details["servloc_domain_180_only"]) and bool(details["servloc_native_service74_absence"]):
        details["servloc_live_label"] = "servloc-domain-list-180-only-service74-missing"
        return (
            f"{args.cycle.lower()}-servloc-domain-list-180-only-service74-missing-rollback-pass",
            True,
            "native service-locator live response returns only msm/modem/wlan_pd instance 180, and service-notifier 74/wlan_pd/WLFW69/wlan0 remain absent",
            details,
        )
    details["servloc_live_label"] = "servloc-domain-list-live-incomplete"
    return (
        f"{args.cycle.lower()}-servloc-domain-list-live-incomplete-rollback-pass",
        True,
        "live domain-list and service-notifier fields did not match a fixed progress or 180-only absence discriminator",
        details,
    )


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    return "\n".join([
        "# Native Init V1908 Service-locator Domain-list Live Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1908`",
        "- Type: one-run rollbackable native service-locator domain-list observer",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{gate.get('servloc_live_label')}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Live Domain Edge",
        "",
        f"- service-locator result/count/name/instance: `{gate.get('servloc_domain_result')}` / `{gate.get('servloc_domain_count')}` / `{gate.get('servloc_domain0_name')}` / `{gate.get('servloc_domain0_instance_id')}`",
        f"- service-locator endpoint/status: `{gate.get('servloc_domain_endpoint_node')}`:`{gate.get('servloc_domain_endpoint_port')}` / `{gate.get('servloc_domain_endpoint_status')}`",
        f"- domain 180-only discriminator: `{gate.get('servloc_domain_180_only')}`",
        f"- V1907 source gate: `{gate.get('v1907_decision')}` / `{gate.get('v1907_label')}` / `{gate.get('v1907_pass')}` / single caller `{gate.get('v1907_single_real_register_caller_is_icnss')}`",
        "",
        "## Service-notifier / Lower Gates",
        "",
        f"- service180/service74/wlan_pd raw counts: `{gate.get('raw_service180_text_counts')}` / `{gate.get('raw_service74_text_counts')}` / `{gate.get('raw_wlan_pd_text_counts')}`",
        f"- service-notifier early/late state: `{gate.get('servnotif_early_state')}` / `{gate.get('servnotif_late_listener_state')}`",
        f"- native service74 absence discriminator: `{gate.get('servloc_native_service74_absence')}`",
        f"- WLFW69/requested-wlanmdsp/wlan0: `{gate.get('wlfw_service69_seen')}` / `{gate.get('requested_wlanmdsp')}` / `{gate.get('wlan0_present')}`",
        f"- PM register/connect/open path: `{gate.get('pm_client_register_rc')}` / `{gate.get('pm_client_connect_rc')}` / `{gate.get('open_context_path')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Transport: `{property_deploy.get('transport')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Selected Diff",
        "",
        "- Native live confirms the current blocker as service-locator domain-list 180-only before service-notifier instance 74 publication.",
        "- This remains on the internal modem path and keeps `/dev/subsys_modem` as a precondition, not a WLAN guest-PD start trigger.",
        "- The next comparison should query/capture Android-good service-locator domain-list in the normal ~15s boot to verify whether Android receives instance 74 from the locator or publishes it by another kernel path.",
        "",
        "## Safety Scope",
        "",
        "- Rollbackable native test boot plus `stage3/boot_linux_v724.img` rollback only.",
        "- No Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, restart-PD request, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, forced RC1/case, or PMIC/GPIO/GDSC/regulator writes.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    configure_runner()
    runner = v1904.get_runner()
    runner.deploy_property_root = v1904.prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.deploy_property_root_serial
    runner.classify_gate = classify_gate
    runner.render_report = render_report
    rc = runner.main(argv)
    v1904.prev1834.prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
