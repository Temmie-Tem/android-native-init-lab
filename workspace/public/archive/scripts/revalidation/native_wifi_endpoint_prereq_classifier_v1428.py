#!/usr/bin/env python3
"""V1428 host-only classifier for post-RC1 endpoint prerequisite work."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1428-endpoint-prereq-classifier"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1428_ENDPOINT_PREREQ_CLASSIFIER_2026-06-01.md"
)


@dataclass(frozen=True)
class InputPath:
    name: str
    path: Path
    required_markers: tuple[str, ...]


INPUTS: tuple[InputPath, ...] = (
    InputPath(
        "v1353_pcie1_static_contract",
        REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1353_PCIE1_RC_STATIC_CONTRACT_CLASSIFIER_2026-06-01.md",
        (
            "v1353-pcie1-rc-static-contract-ready",
            "GPIO102",
            "GPIO103",
            "GPIO104",
            "pcie_1_gdsc",
        ),
    ),
    InputPath(
        "v1354_current_route_rc_off",
        REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md",
        (
            "v1354-current-route-pcie1-rc-stayed-off",
            "pcie_1_gdsc remained 0mV",
            "PERST stayed low",
        ),
    ),
    InputPath(
        "v1355_pon_parity",
        REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1355_PMIC_GPIO9_PON_PARITY_CLASSIFIER_2026-06-01.md",
        (
            "v1355-pon-parity-closed-pcie1-rc-next",
            "PON is closed",
            "PM8150L GPIO9",
        ),
    ),
    InputPath(
        "v1368_rc1_status_read",
        REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1368_PCI_MSM_CORRECTED_RC1_STATUS_LIVE_2026-06-01.md",
        (
            "v1368-corrected-rc1-status-proof-clean",
            "rc1_perst_gpio102_value",
            "rc1_wake_gpio104_value",
        ),
    ),
    InputPath(
        "v1370_corrected_rc1",
        REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1370_PCI_MSM_CORRECTED_RC1_ENUMERATE_LIVE_2026-06-01.md",
        (
            "v1370-corrected-rc1-link-training-no-l0-clean",
            "PHY/LTSSM link training",
            "did not reach L0",
        ),
    ),
    InputPath(
        "v1372_provider_held",
        REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1372_PROVIDER_HELD_PCIE1_ENUMERATE_LIVE_2026-06-01.md",
        (
            "v1372-provider-held-still-no-l0-clean",
            "provider-held",
            "stopped before L0",
        ),
    ),
    InputPath(
        "v1423_gpio135",
        REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1423_GPIO135_PARITY_CLASSIFIER_2026-06-01.md",
        (
            "v1423-gpio135-low-is-not-actionable-by-itself",
            "GPIO142/MDM2AP IRQ",
            "PCIe L0",
        ),
    ),
    InputPath(
        "v1424_timing",
        REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1424_RC1_TIMING_PARITY_CLASSIFIER_2026-06-01.md",
        (
            "v1424-rc1-timing-precondition-parity-but-endpoint-no-l0",
            "esoc-to-assert gap",
            "after PERST release",
        ),
    ),
    InputPath(
        "v1427_retry_handoff",
        REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1427_WIFI_TEST_BOOT_RC1_RETRY_HANDOFF_2026-06-01.md",
        (
            "v1427-test-boot-downstream-progress-rollback-pass",
            "`TEST: 11` count: `3`",
            "L0 count: `0`",
            "MHI/WLFW/BDF/FW-ready/`wlan0`: absent",
        ),
    ),
)

DEFAULT_V1424_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1424-rc1-timing-parity-classifier" / "manifest.json"
DEFAULT_V1427_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1427-wifi-test-boot-rc1-retry-handoff" / "manifest.json"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def marker_checks(input_path: InputPath) -> dict[str, Any]:
    exists = input_path.path.exists()
    text = read_text(input_path.path) if exists else ""
    markers = {marker: marker in text for marker in input_path.required_markers}
    return {
        "path": rel(input_path.path),
        "exists": exists,
        "markers": markers,
        "pass": exists and all(markers.values()),
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify(v1424_manifest: dict[str, Any], v1427_manifest: dict[str, Any], checks: dict[str, Any]) -> dict[str, Any]:
    wifi_progress = v1427_manifest.get("wifi_progress", {})
    watcher_text = str(wifi_progress.get("pid1_rc1_watcher_result_file", ""))
    timing = v1424_manifest.get("comparison", {})
    v1424_native = v1424_manifest.get("native", {})

    closed = {
        "static_pcie1_contract_known": checks["v1353_pcie1_static_contract"]["pass"],
        "current_route_initial_rc_off_observed": checks["v1354_current_route_rc_off"]["pass"],
        "pm8150l_pon_blind_mutation_not_next": checks["v1355_pon_parity"]["pass"],
        "status_read_surface_known": checks["v1368_rc1_status_read"]["pass"],
        "corrected_rc1_entry_known": checks["v1370_corrected_rc1"]["pass"],
        "provider_held_ordering_not_sufficient": checks["v1372_provider_held"]["pass"],
        "gpio135_low_not_actionable": checks["v1423_gpio135"]["pass"],
        "rc1_timing_close": bool(timing.get("timing_close_50ms")),
        "rc1_int_mask_parity": bool(timing.get("int_mask_parity")),
        "single_attempt_not_primary": (
            v1427_manifest.get("pass") is True
            and wifi_progress.get("rc1_progress") is True
            and wifi_progress.get("rc1_l0") is False
            and "retry_count=2" in watcher_text
        ),
        "retry_widening_not_next": (
            wifi_progress.get("rc1_link_failed") is True
            and wifi_progress.get("pid1_rc1_window_has_post_500ms") is True
            and wifi_progress.get("mhi_progress") is False
            and wifi_progress.get("wlfw_progress") is False
            and wifi_progress.get("wlan0_present") is False
        ),
    }

    downstream_blocked = (
        wifi_progress.get("rc1_l0") is False
        and wifi_progress.get("mhi_progress") is False
        and wifi_progress.get("wlfw_progress") is False
        and wifi_progress.get("wlan0_present") is False
        and v1424_native.get("downstream_absent") is True
    )
    prerequisite_scope = {
        "perst_gpio102": "read around RC1 release",
        "clkreq_gpio103": "read around RC1 release",
        "wake_gpio104": "read around RC1 release",
        "pcie_1_gdsc": "read immediately before and after corrected RC1",
        "pcie1_refclk_pipe_clocks": "read immediately before and after corrected RC1",
        "gpio142_mdm2ap_irq": "read across the RC1 window",
        "ltssm_terminal_state": "classify post-release endpoint response",
    }

    all_inputs_pass = all(item["pass"] for item in checks.values())
    all_closed = all(closed.values())
    passed = all_inputs_pass and all_closed and downstream_blocked
    decision = (
        "v1428-rc1-retry-closed-pre-rc1-endpoint-prereq-next"
        if passed
        else "v1428-endpoint-prereq-classifier-needs-more-evidence"
    )
    reason = (
        "timing, ordering, GPIO135, PON, and retry-count branches are closed enough; the next useful work is endpoint prerequisite parity around PERST release"
        if passed
        else "one or more required inputs did not prove the endpoint prerequisite pivot"
    )

    return {
        "cycle": "V1428",
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "checks": checks,
        "closed_branches": closed,
        "downstream_blocked": downstream_blocked,
        "next_prerequisite_scope": prerequisite_scope,
        "next_gate": "V1429 source/build-only read-only Wi-Fi test-boot endpoint-prerequisite sampler",
        "guardrails": {
            "host_only": True,
            "device_command_executed": False,
            "flash_executed": False,
            "wifi_hal_scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_external_ping_executed": False,
            "pmic_gpio_gdsc_write_executed": False,
            "esoc_notify_boot_done_executed": False,
            "platform_bind_unbind_executed": False,
            "global_pci_rescan_executed": False,
        },
    }


def render_report(result: dict[str, Any], args: argparse.Namespace) -> str:
    closed = result["closed_branches"]
    scope = result["next_prerequisite_scope"]
    checks = result["checks"]
    return "\n".join(
        [
            "# Native Init V1428 Endpoint Prerequisite Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1428`",
            "- Type: host-only/read-only classifier over existing reports and manifests",
            f"- Decision: `{result['decision']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{rel(args.out_dir / 'manifest.json')}`",
            "",
            "## Inputs",
            "",
            "| Input | Path | Pass |",
            "| --- | --- | --- |",
            *[
                f"| `{name}` | `{item['path']}` | `{item['pass']}` |"
                for name, item in checks.items()
            ],
            "",
            "## Closed Branches",
            "",
            "| Branch | Result | Meaning |",
            "| --- | --- | --- |",
            f"| static pcie1 contract | `{closed['static_pcie1_contract_known']}` | RC1 GPIO/clock/GDSC surfaces are known from DTS |",
            f"| current-route RC off | `{closed['current_route_initial_rc_off_observed']}` | older current-route run observed pcie1 RC off before corrected enumerate work |",
            f"| PM8150L PON blind write | `{closed['pm8150l_pon_blind_mutation_not_next']}` | PON parity is closed enough to avoid direct PMIC mutation |",
            f"| corrected RC1 status surface | `{closed['status_read_surface_known']}` | status-read case can expose PERST/WAKE without enumeration |",
            f"| corrected RC1 entry | `{closed['corrected_rc1_entry_known']}` | corrected RC1 reaches PHY/LTSSM but not L0 |",
            f"| provider-held ordering | `{closed['provider_held_ordering_not_sufficient']}` | holding the provider path still does not reach L0 |",
            f"| GPIO135/AP2MDM low | `{closed['gpio135_low_not_actionable']}` | GPIO135 low alone does not justify a direct GPIO/PMIC write |",
            f"| RC1 timing parity | `{closed['rc1_timing_close']}` | V1424 put native RC1 assert within the Android timing window |",
            f"| RC1 INT mask parity | `{closed['rc1_int_mask_parity']}` | native and Android share the same RC1 INT mask path |",
            f"| single attempt hypothesis | `{closed['single_attempt_not_primary']}` | V1427 executed initial plus two retries |",
            f"| retry widening | `{closed['retry_widening_not_next']}` | all retry attempts failed before L0 with no MHI/WLFW/`wlan0` |",
            "",
            "## Classification",
            "",
            "V1427 closes the simple test-boot retry branch. Three corrected-RC1",
            "attempts produced the same reset/release/LTSSM path and failed before",
            "L0. V1424 already made the timing close enough to Android, so adding",
            "more retries is lower value than proving the endpoint prerequisites at",
            "the exact PERST-release boundary.",
            "",
            f"- Downstream still blocked: `{result['downstream_blocked']}`",
            "- The next proof point is not Wi-Fi scan/connect. It is whether SDX50M",
            "  sees the expected RC1 preconditions when PERST is released.",
            "",
            "## V1429 Candidate",
            "",
            "Build a source/build-only test boot that keeps the V1425 rollbackable",
            "shape but replaces retry expansion with read-only endpoint-prerequisite",
            "sampling around the corrected-RC1 window.",
            "",
            "| Surface | Required observation |",
            "| --- | --- |",
            *[f"| `{name}` | {description} |" for name, description in scope.items()],
            "",
            "The sampler should capture these states before the corrected RC1 write,",
            "immediately after PERST release, and after the terminal LTSSM result.",
            "It should not add new PMIC/GPIO/GDSC writes and should not start any",
            "connect-side Wi-Fi work until L0/MHI/WLFW/`wlan0` progress exists.",
            "",
            "## Safety Scope",
            "",
            "This cycle was host-only. It did not run device commands, flash, reboot,",
            "write partitions, handle credentials, scan/connect Wi-Fi, run DHCP/routes,",
            "ping externally, write PMIC/GPIO/GDSC controls, spoof eSoC notify/",
            "`BOOT_DONE`, run global PCI rescan, or bind/unbind platform devices.",
            "",
            "## Validation",
            "",
            "```bash",
            "python3 -m py_compile scripts/revalidation/native_wifi_endpoint_prereq_classifier_v1428.py",
            "python3 scripts/revalidation/native_wifi_endpoint_prereq_classifier_v1428.py --write-report",
            "```",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1424-manifest", type=Path, default=DEFAULT_V1424_MANIFEST)
    parser.add_argument("--v1427-manifest", type=Path, default=DEFAULT_V1427_MANIFEST)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checks = {input_path.name: marker_checks(input_path) for input_path in INPUTS}
    v1424_manifest = load_json(args.v1424_manifest)
    v1427_manifest = load_json(args.v1427_manifest)
    result = classify(v1424_manifest, v1427_manifest, checks)
    result["inputs"] = {
        "v1424_manifest": rel(args.v1424_manifest),
        "v1427_manifest": rel(args.v1427_manifest),
    }
    report = render_report(result, args)

    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(args.report_path, report)

    print(
        json.dumps(
            {
                "decision": result["decision"],
                "pass": result["pass"],
                "out_dir": rel(args.out_dir),
                "next_gate": result["next_gate"],
                "downstream_blocked": result["downstream_blocked"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
