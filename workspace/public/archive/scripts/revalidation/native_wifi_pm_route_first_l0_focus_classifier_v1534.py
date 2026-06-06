#!/usr/bin/env python3
"""V1534 host-only classifier: PM route status vs first-L0 blocker."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1534-pm-route-first-l0-focus-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1534_PM_ROUTE_FIRST_L0_FOCUS_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1534-pm-route-first-l0-focus-classifier.txt")

INPUTS = {
    "v1178": Path("docs/reports/NATIVE_INIT_V1178_PM_DEPENDENCY_INIT_CLASSIFIER_2026-05-28.md"),
    "v1343": Path("tmp/wifi/v1343-provider-ready-sdx50m-route-live/manifest.json"),
    "v1345": Path("tmp/wifi/v1345-current-route-mdm2ap-timing-sampler-live/manifest.json"),
    "v1496": Path("tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/manifest.json"),
    "v1517": Path("tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/manifest.json"),
    "v1523": Path("tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier/manifest.json"),
    "v1525": Path("tmp/wifi/v1525-mhi-pm-resume-position-classifier/manifest.json"),
    "v1533": Path("tmp/wifi/v1533-v1532-queue-pair-classifier/manifest.json"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def get_path(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def classify() -> dict[str, Any]:
    manifests = {name: read_json(path) for name, path in INPUTS.items() if path.suffix == ".json"}
    texts = {name: read_text(path) for name, path in INPUTS.items() if path.suffix != ".json"}
    v1343 = manifests.get("v1343", {})
    v1345 = manifests.get("v1345", {})
    v1496 = manifests.get("v1496", {})
    v1517 = manifests.get("v1517", {})
    v1523 = manifests.get("v1523", {})
    v1525 = manifests.get("v1525", {})
    v1533 = manifests.get("v1533", {})
    v1343_analysis = v1343.get("analysis") or {}
    v1221_route = v1343_analysis.get("v1221_route") or {}
    v1345_analysis = v1345.get("analysis") or {}
    response_sampler = v1345.get("response_sampler") or {}
    wifi_progress_1496 = v1496.get("wifi_progress") or {}
    wifi_progress_1517 = v1517.get("wifi_progress") or {}
    v1533_checks = v1533.get("checks") or {}
    v1523_checks = v1523.get("checks") or {}
    v1525_checks = v1525.get("checks") or {}
    v1178_text = texts.get("v1178", "")

    facts = {
        "old_pm_dependency_gap_known": "dependency_flag=0" in v1178_text and "Repair Strategy" in v1178_text,
        "current_sdx50m_route_reaches_pm_esoc0": v1221_route.get("sdx50m_registered") is True and v1221_route.get("per_mgr_esoc0_any") is True,
        "current_route_reaches_powerup": v1345.get("pass") is True and "reached mdm_subsys_powerup" in str(v1345.get("reason")),
        "native_v1345_no_lower_response": v1345.get("decision") == "v1345-current-route-mdm2ap-full-window-no-transition",
        "native_v1496_rc1_progress_no_l0": bool(wifi_progress_1496.get("rc1_progress")) and not bool(wifi_progress_1496.get("rc1_l0")),
        "native_v1496_link_failed": bool(wifi_progress_1496.get("rc1_link_failed")),
        "native_v1517_rc1_progress_no_l0": bool(wifi_progress_1517.get("rc1_progress")) and not bool(wifi_progress_1517.get("rc1_l0")),
        "test11_common_enable_not_missing": v1523.get("decision") == "v1523-test11-shares-enable-normal-trigger-readiness-gap",
        "mhi_pm_resume_downstream": v1525.get("decision") == "v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger",
        "icnss_workqueue_not_first_l0": v1533.get("decision") == "v1533-icnss-queue-pair-is-hdd-register-path-not-first-l0-trigger",
        "wifi_goal_still_not_reached": not bool(wifi_progress_1496.get("connect_ready")) and not bool(wifi_progress_1517.get("connect_ready")),
    }
    route = {
        "v1178_old_gap": "late per_proxy caused dependency flag/order gap; useful historical model, not the active lowest blocker once current SDX50M route reaches esoc/powerup",
        "v1343_current_route": {
            "decision": v1343.get("decision"),
            "sdx50m_registered": v1221_route.get("sdx50m_registered"),
            "per_mgr_esoc0_any": v1221_route.get("per_mgr_esoc0_any"),
            "wlfw_or_wlan_dmesg_seen": v1221_route.get("wlfw_or_wlan_dmesg_seen"),
            "wlan0_up": v1221_route.get("wlan0_up"),
        },
        "v1345_lower_response": {
            "decision": v1345.get("decision"),
            "reason": v1345.get("reason"),
            "timing_pm_service_powerup_seen": response_sampler.get("timing_pm_service_powerup_seen"),
            "gpio142_irq_delta": response_sampler.get("timing_gpio142_irq_delta"),
            "pcie_transition_seen": response_sampler.get("timing_pcie_rc1_transition_seen"),
            "mhi_pipe_seen": response_sampler.get("timing_mhi_pipe_seen"),
            "wlan0_seen": response_sampler.get("timing_wlan0_seen"),
        },
        "v1496_rc1": {
            "decision": v1496.get("decision"),
            "progress_decision": wifi_progress_1496.get("final_decision"),
            "provider_trigger": wifi_progress_1496.get("provider_trigger"),
            "rc1_progress": wifi_progress_1496.get("rc1_progress"),
            "rc1_l0": wifi_progress_1496.get("rc1_l0"),
            "rc1_link_failed": wifi_progress_1496.get("rc1_link_failed"),
            "mhi_progress": wifi_progress_1496.get("mhi_progress"),
            "wlan0_present": wifi_progress_1496.get("wlan0_present"),
        },
        "v1533_icnss": {
            "decision": v1533.get("decision"),
            "icnss_queue_to_pm_esoc0_ms": get_path(v1533, "deltas_ms", "icnss_queue_to_pm_esoc0_get"),
            "icnss_queue_to_qmi_ms": get_path(v1533, "deltas_ms", "icnss_queue_to_qmi"),
        },
    }
    all_checks = all(facts.values())
    decision = "v1534-current-pm-route-supersedes-old-gap-first-l0-focus"
    reason = (
        "Current SDX50M PM route already reaches pm-service/esoc0 and mdm_subsys_powerup; "
        "native now reaches RC1 LTSSM but fails before L0, while ICNSS workqueue and MHI PM-resume are downstream or non-trigger leads"
    )
    if not all_checks:
        decision = "v1534-pm-route-first-l0-focus-review"
        reason = "one or more fixed-point checks need manual review before selecting the next live gate"
    return {
        "cycle": "V1534",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": all_checks,
        "reason": reason,
        "inputs": {name: rel(path) for name, path in INPUTS.items()},
        "host": collect_host_metadata(),
        "facts": facts,
        "route": route,
        "classification": {
            "pm_actionability_status": "superseded for the active blocker: current route has positive SDX50M registration and per_mgr_esoc0 evidence",
            "active_lowest_blocker": "PCIe RC1 endpoint readiness/link training: LTSSM progresses but L0 is absent and link fails",
            "not_next": [
                "repeat old late-per_proxy dependency repair as the primary blocker",
                "ICNSS workqueue/FW-ready/BDF analysis before native L0",
                "MHI PM-resume or ks/MHI pipe analysis before PCI enumeration",
                "Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            ],
        },
        "next_gate": {
            "cycle": "V1535",
            "summary": "design a bounded first-L0 trigger/readiness observer or test-boot focused on endpoint readiness around msm_pcie_enumerate, not PM registration or firmware/MHI",
            "recommended_work": [
                "classify Android-good vs native-fail first-L0 trigger candidates using V1523 normal callers: endpoint wake GPIO104, sysfs/client enumerate, or vendor request path",
                "if live is needed, capture only PCIe RC1/PERST/refclk/LTSSM/WAKE around the current provider trigger with rollback; do not start scan/connect",
                "keep PM actor changes limited to already proven current SDX50M route unless evidence shows pm-service no longer opens esoc0",
            ],
        },
        "safety": {
            "host_only_classifier": True,
            "device_commands_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "global_pci_rescan_executed": False,
            "platform_bind_unbind_executed": False,
        },
    }


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Native Init V1534 PM Route First-L0 Focus Classifier",
            "",
            f"- Generated: `{manifest['generated_at']}`",
            f"- Decision: `{manifest['decision']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            "",
            "## Fixed-Point Checks",
            "",
            markdown_table(["check", "value"], [[key, value] for key, value in manifest["facts"].items()]),
            "",
            "## Route Summary",
            "",
            markdown_table(
                ["surface", "value"],
                [[key, json.dumps(value, sort_keys=True)] for key, value in manifest["route"].items()],
            ),
            "",
            "## Classification",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in manifest["classification"].items()]),
            "",
            "## Interpretation",
            "",
            "- V1178 remains useful history for why late `per_proxy` could miss the dependency flag, but it is no longer the active lowest blocker once the current SDX50M route reaches `per_mgr_esoc0` and `mdm_subsys_powerup`.",
            "- V1343/V1345 prove PM/eSoC actionability is available but lower response is absent; V1496/V1517 then move the failure further down to RC1 LTSSM progress with no L0.",
            "- V1523 proves TEST:11 and normal pci-msm callers share the core enumerate/enable path, so the remaining difference is endpoint readiness or trigger semantics before successful L0.",
            "- V1525 and V1533 close MHI PM-resume and ICNSS workqueue as immediate first-L0 leads.",
            "",
            "## Next Gate",
            "",
            f"- Cycle: `{manifest['next_gate']['cycle']}`",
            f"- Summary: {manifest['next_gate']['summary']}",
            *(f"- Recommended: {item}" for item in manifest["next_gate"]["recommended_work"]),
            "",
            "## Safety",
            "",
            "Host-only classifier. It reads existing manifests and reports only; it performs no device command, flash, reboot, PM actor start, tracefs/sysfs/debugfs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, PCI rescan, or platform bind/unbind.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = classify()
    manifest["out_dir"] = str(store.run_dir)
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), report)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
