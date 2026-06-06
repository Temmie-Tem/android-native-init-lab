#!/usr/bin/env python3
"""V1762 source-only helper contract-gap classifier for WLAN-PD request trigger.

V1761 classified the blocker as a PeripheralManager service-object visibility
gap before the modem requests wlanmdsp.mbn.  This source-only unit checks whether
the current execns helper already exposes a narrow mode that composes that
service-object proof with the V1736 WLAN-PD SM route, without falling back to
the broad PM actor march that V1686 falsified.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
HELPER_SOURCE = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c"
V1761_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1761-wlan-pd-autoload-trigger-contract-classifier" / "manifest.json"
V1686_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1686-wlan-pd-pm-trio-handoff" / "manifest.json"
V1736_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1762-wlan-pd-helper-contract-gap-classifier"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1762_WLAN_PD_HELPER_CONTRACT_GAP_CLASSIFIER_2026-06-03.md"
)
SM_ROUTE_ORDER = (
    "servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,"
    "subsys_modem_holder,cnss_diag,cnss_daemon,service-window-trigger-summary"
)
PM_ROUTE_ORDER = (
    "servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,"
    "pm_proxy_helper,per_mgr,per_proxy,subsys_modem_holder,cnss_diag,cnss_daemon,"
    "pm-service-window-trigger-summary"
)


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": display_path(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["present"] = True
    data["path"] = display_path(path)
    return data


def string_present(source: str, needle: str) -> bool:
    return needle in source


def extract_execns_version(source: str) -> str | None:
    match = re.search(r'#define\s+EXECNS_VERSION\s+"([^"]+)"', source)
    return match.group(1) if match else None


def collect() -> dict[str, Any]:
    source = read_text(HELPER_SOURCE)
    v1761 = load_json(V1761_MANIFEST)
    v1686 = load_json(V1686_MANIFEST)
    v1736 = load_json(V1736_MANIFEST)
    sm_mode = "wifi-companion-wlan-pd-service-window-trigger-start-only"
    pm_mode = "wifi-companion-wlan-pd-pm-service-window-trigger-start-only"
    provider_observe_mode = "wifi-companion-android-order-pre-cnss-provider-observe-only"
    service74_provider_first = "wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only"
    facts = {
        "helper_source_present": HELPER_SOURCE.exists(),
        "execns_version": extract_execns_version(source),
        "v1761_service_object_gap": v1761.get("label") == "pm-service-object-gap-before-wlanmdsp-request",
        "v1736_wlfw_reached": v1736.get("decision") == "v1736-wlfw-start-reached-downstream-block-rollback-pass",
        "v1686_broad_pm_regressed": v1686.get("gate", {}).get("wlfw_service_request_seen") == "0"
        and v1686.get("gate", {}).get("requested_wlanmdsp") == "0",
        "sm_mode_present": string_present(source, sm_mode),
        "pm_mode_present": string_present(source, pm_mode),
        "provider_observe_mode_present": string_present(source, provider_observe_mode),
        "service74_provider_first_mode_present": string_present(source, service74_provider_first),
        "pm_mode_summary_is_broad": string_present(source, "pm-trio-plus-internal-modem-holder"),
        "pm_mode_order_has_pm_trio_before_cnss": string_present(
            source,
            PM_ROUTE_ORDER,
        ),
        "sm_mode_order_has_v1736_route": string_present(
            source,
            SM_ROUTE_ORDER,
        ),
        "narrow_service_object_mode_present": string_present(source, "wlan-pd-provider-visible-service-window")
        or string_present(source, "wlan-pd-service-object-visible"),
        "peripheral_uprobe_summary_present": string_present(
            source,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.%s.hit_count",
        ),
        "manager_register_tx_probe_present": string_present(source, "periph_manager_register_tx_call"),
        "null_branch_probe_present": string_present(source, "pm_init_null_peripheral_branch"),
    }
    return {
        "paths": {
            "helper_source": display_path(HELPER_SOURCE),
            "v1761_manifest": display_path(V1761_MANIFEST),
            "v1686_manifest": display_path(V1686_MANIFEST),
            "v1736_manifest": display_path(V1736_MANIFEST),
        },
        "mode_orders": {
            "sm_route": SM_ROUTE_ORDER if string_present(source, SM_ROUTE_ORDER) else None,
            "pm_route": PM_ROUTE_ORDER if string_present(source, PM_ROUTE_ORDER) else None,
        },
        "facts": facts,
    }


def classify(collected: dict[str, Any]) -> tuple[str, bool, str, str]:
    facts = collected["facts"]
    prerequisites = (
        facts["helper_source_present"],
        facts["v1761_service_object_gap"],
        facts["v1736_wlfw_reached"],
        facts["sm_mode_present"],
        facts["peripheral_uprobe_summary_present"],
        facts["manager_register_tx_probe_present"],
        facts["null_branch_probe_present"],
    )
    if not all(prerequisites):
        return (
            "v1762-helper-contract-prerequisite-incomplete",
            False,
            "helper source or retained V1761/V1736 evidence is incomplete",
            "helper-contract-prerequisite-incomplete",
        )
    if (
        facts["pm_mode_present"]
        and facts["pm_mode_summary_is_broad"]
        and facts["pm_mode_order_has_pm_trio_before_cnss"]
        and facts["v1686_broad_pm_regressed"]
        and not facts["narrow_service_object_mode_present"]
    ):
        return (
            "v1762-helper-needs-new-narrow-service-object-mode-source-pass",
            True,
            "current helper has V1736 SM-route and peripheral uprobes, but its PM route is a broad pm-trio path already falsified by V1686; no narrow service-object-visible mode exists",
            "new-narrow-service-object-mode-needed",
        )
    if facts["narrow_service_object_mode_present"]:
        return (
            "v1762-helper-narrow-service-object-mode-present-source-pass",
            True,
            "helper appears to contain a narrow service-object-visible mode; prepare artifact sanity before any live run",
            "narrow-service-object-mode-present",
        )
    return (
        "v1762-helper-contract-gap-inconclusive",
        False,
        "helper mode surface does not match a known safe or unsafe contract",
        "helper-contract-gap-inconclusive",
    )


def md_bool(value: bool) -> str:
    return "`true`" if value else "`false`"


def render_report(result: dict[str, Any]) -> str:
    facts = result["facts"]
    lines = [
        "# Native Init V1762 WLAN-PD Helper Contract-gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1762`",
        "- Type: source-only helper contract-gap classifier",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Source Facts",
        "",
        f"- Helper source: `{result['paths']['helper_source']}`",
        f"- Execns version marker: `{facts['execns_version']}`",
        "- V1761 service-object gap input: " + md_bool(facts["v1761_service_object_gap"]),
        "- V1736 WLFW SM route input: " + md_bool(facts["v1736_wlfw_reached"]),
        "- V1686 broad PM route regression input: " + md_bool(facts["v1686_broad_pm_regressed"]),
        "- V1736 SM route mode present: " + md_bool(facts["sm_mode_present"]),
        "- PM service-window mode present: " + md_bool(facts["pm_mode_present"]),
        "- PM service-window mode is broad PM trio: " + md_bool(facts["pm_mode_summary_is_broad"]),
        "- PM route order starts `pm_proxy_helper,per_mgr,per_proxy` before CNSS: "
        + md_bool(facts["pm_mode_order_has_pm_trio_before_cnss"]),
        "- Narrow service-object-visible mode present: " + md_bool(facts["narrow_service_object_mode_present"]),
        "- Peripheral uprobe summary present: " + md_bool(facts["peripheral_uprobe_summary_present"]),
        "- Manager register TX probe present: " + md_bool(facts["manager_register_tx_probe_present"]),
        "- Null PeripheralManager branch probe present: " + md_bool(facts["null_branch_probe_present"]),
        "",
        "## Existing Orders",
        "",
        f"- SM route order: `{result['mode_orders'].get('sm_route')}`",
        f"- PM route order: `{result['mode_orders'].get('pm_route')}`",
        "",
        "## Interpretation",
        "",
        "- The helper already has the V1736 SM route and the uprobe markers needed to detect the PM service-object branch.",
        "- The only existing WLAN-PD PM service-window route is the broad PM trio path; V1686 already showed that path regresses WLFW/request progress.",
        "- Therefore the next implementation unit should not reuse the broad PM service-window mode as-is.",
        "- The missing source unit is a narrow mode that preserves V1736 ordering and only proves the PeripheralManager service-object visibility/PM register-vote contract before measuring `requested_wlanmdsp`.",
        "",
        "## Next",
        "",
        "- V1763 should be source/build-only: add a fail-closed helper mode for `service-object-visible + V1736 SM route` with explicit output keys for service object non-null, `asInterface`, manager register TX, PM vote/log evidence, `requested_wlanmdsp`, WLFW service 69, and `wlan0`.",
        "- The new mode must not start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, external ping, `boot_wlan`, restart-PD, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, PCI rescan, platform bind/unbind, firmware writes, or partition writes.",
        "- Live remains blocked until source/build artifact sanity proves the new mode is bounded and rollbackable.",
        "",
        "## Safety Scope",
        "",
        "This classifier is source-only. It performs no device contact, flash, reboot, actor start, tracefs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, or partition write.",
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    collected = collect()
    decision, pass_ok, reason, label = classify(collected)
    result = {
        "cycle": "V1762",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "label": label,
        "out_dir": display_path(args.out_dir),
        **collected,
    }
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    report = render_report(result)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(
        json.dumps(
            {
                "decision": decision,
                "pass": pass_ok,
                "label": label,
                "out_dir": display_path(args.out_dir),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
