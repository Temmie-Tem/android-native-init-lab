#!/usr/bin/env python3
"""V1876 rollbackable handoff for the V1874 lower-response read-only sampler."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_sdx50m_private_mount_handoff_v1864 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
V1874_OUT = REPO_ROOT / "tmp" / "wifi" / "v1874-lower-response-readonly-sampler-test-boot"
BASE_CLASSIFY_GATE = base.classify_gate
BASE_RENDER_REPORT = base.render_report


def configure_constants() -> None:
    base.CYCLE = "V1876"
    base.V1863_OUT = V1874_OUT
    base.REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1874/dev/__properties__"
    base.DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1876-lower-response-readonly-sampler-handoff"
    base.DEFAULT_REPORT_PATH = (
        REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1876_LOWER_RESPONSE_READONLY_SAMPLER_HANDOFF_2026-06-03.md"
    )
    base.TEST_EXPECT_VERSION = "A90 Linux init 0.9.170 (v1874-lower-response-readonly-sampler)"
    base.TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1874.log"
    base.TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1874.summary"
    base.TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1874-helper.result"
    base.TEST_IMAGE = V1874_OUT / "boot_linux_v1874_lower_response_readonly_sampler.img"
    base.DMESG_PATTERN = (
        base.DMESG_PATTERN.replace("A90v1863", "A90v1874")
        + "|wlan_pd_lower_response_input_contract|post_powerup_dense|lower_response"
    )


def matching_ints(fields: dict[str, str], contains: str, suffix: str) -> list[int]:
    values: list[int] = []
    for key, value in fields.items():
        if contains in key and key.endswith(suffix):
            values.append(base.intish(value))
    return values


def any_field_equals(fields: dict[str, str], contains: str, suffix: str, expected: str) -> bool:
    return any(
        contains in key and key.endswith(suffix) and value == expected
        for key, value in fields.items()
    )


def contract_details(evidence_dir: Path) -> dict[str, Any]:
    fields = base.runner().fwbase.parse_helper_fields(evidence_dir)
    contract_prefix = "wlan_pd_lower_response_input_contract.post_powerup_dense"
    response_prefix = "pm_service_trigger_observer.response_sample.post_powerup_dense.offset_"
    lower_prefix = "wlan_pd_post_pm_lower_state_observer.post_powerup_dense.offset_"
    sample_indices = matching_ints(fields, "wlan_pd_lower_response_input_contract.post_powerup_dense.offset_", ".sample_index")
    mdm_status_counts = matching_ints(fields, response_prefix, ".mdm_status_count_total")
    pci_counts = matching_ints(fields, response_prefix, ".pci_dev_count") + matching_ints(fields, lower_prefix, ".pci_device_count")
    mhi_counts = matching_ints(fields, response_prefix, ".mhi_bus_count") + matching_ints(fields, lower_prefix, ".mhi_device_count")
    ks_counts = matching_ints(fields, response_prefix, ".ks_process_count")
    mhi_pipe_exists = matching_ints(fields, response_prefix, ".mhi_pipe_exists") + matching_ints(fields, lower_prefix, ".mhi_pipe_exists")
    wlan0_exists = matching_ints(fields, response_prefix, ".wlan0_exists") + matching_ints(fields, lower_prefix, ".wlan0_exists")
    pcie1_gdsc_seen = matching_ints(fields, response_prefix, ".pcie1_gdsc_seen")
    return {
        "contract_sample_count_configured": base.intish(fields.get(f"{contract_prefix}.sample_count")),
        "contract_offsets_ms": fields.get(f"{contract_prefix}.offsets_ms", ""),
        "contract_sample_count_observed": len(set(sample_indices)),
        "contract_read_only": fields.get(f"{contract_prefix}.read_only") == "1",
        "contract_no_esoc0_open": fields.get(f"{contract_prefix}.no_esoc0_open") == "1",
        "contract_no_rc_sel_case_write": fields.get(f"{contract_prefix}.no_rc_sel_case_write") == "1",
        "contract_no_pci_rescan_or_bind": fields.get(f"{contract_prefix}.no_pci_rescan_or_bind") == "1",
        "contract_no_wifi_hal_scan_connect": fields.get(f"{contract_prefix}.no_wifi_hal_scan_connect") == "1",
        "contract_max_mdm_status_count_total": max(mdm_status_counts, default=-1),
        "contract_max_pci_dev_count": max(pci_counts, default=-1),
        "contract_max_mhi_bus_count": max(mhi_counts, default=-1),
        "contract_max_ks_process_count": max(ks_counts, default=-1),
        "contract_mhi_pipe_seen": max(mhi_pipe_exists, default=0) > 0,
        "contract_wlan0_seen": max(wlan0_exists, default=0) > 0,
        "contract_pcie1_gdsc_line_seen": max(pcie1_gdsc_seen, default=0) > 0,
        "contract_pcie_current_link_state_present": any_field_equals(fields, response_prefix, ".pcie_current_link_state", "0"),
        "contract_guard_ok": all([
            fields.get(f"{contract_prefix}.read_only") == "1",
            fields.get(f"{contract_prefix}.no_esoc0_open") == "1",
            fields.get(f"{contract_prefix}.no_rc_sel_case_write") == "1",
            fields.get(f"{contract_prefix}.no_pci_rescan_or_bind") == "1",
            fields.get(f"{contract_prefix}.no_wifi_hal_scan_connect") == "1",
        ]),
    }


def classify_contract(details: dict[str, Any]) -> tuple[str, str]:
    lower_service69 = bool(details.get("lower_service69_progress"))
    lower_wlan0 = bool(details.get("lower_wlan0_present")) or bool(details.get("contract_wlan0_seen"))
    lower_mhi = bool(details.get("lower_mhi_present")) or bool(details.get("contract_mhi_pipe_seen"))
    max_pci = base.intish(details.get("contract_max_pci_dev_count"))
    max_mhi = base.intish(details.get("contract_max_mhi_bus_count"))
    if lower_service69 and lower_wlan0:
        return (
            "lower-input-wifi-prereq-present-readonly-stop",
            "WLFW service 69 and wlan0 are both present; stop for a separate connect prerequisite check.",
        )
    if lower_service69 or lower_wlan0 or lower_mhi or max_mhi > 0:
        return (
            "lower-input-mhi-or-wlfw-progress-readonly-stop",
            "read-only sampler observed MHI, WLFW, wlan0, or related lower publication progress; stop before connect.",
        )
    if max_pci > 0:
        return (
            "lower-input-rc1-natural-attempt-no-l0",
            "read-only sampler observed PCIe device state but no complete MHI/WLFW/wlan0 publication.",
        )
    if bool(details.get("contract_pcie1_gdsc_line_seen")):
        return (
            "lower-input-power-clock-snapshot-gap",
            "read-only sampler captured pcie1 power/clock surface but lower publication stayed absent.",
        )
    return (
        "lower-input-mdm2ap-silent",
        "private SDX50M route ran but GPIO142/MDM2AP, PCIe/MHI/WLFW, and wlan0 stayed silent.",
    )


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    decision, passed, reason, details = BASE_CLASSIFY_GATE(args, test_flash, rollback_result, evidence_dir)
    details.update(contract_details(evidence_dir))
    if not passed:
        return decision, passed, reason, details
    contract_label, contract_reason = classify_contract(details)
    details["lower_response_input_contract_label"] = contract_label
    return f"{args.cycle.lower()}-{contract_label}-rollback-pass", True, contract_reason, details


def render_contract(gate: dict[str, Any]) -> str:
    return "\n".join([
        "## Lower Response Input Contract",
        "",
        f"- contract label: `{gate.get('lower_response_input_contract_label')}`",
        f"- sample configured/observed: `{gate.get('contract_sample_count_configured')}` / `{gate.get('contract_sample_count_observed')}`",
        f"- offsets ms: `{gate.get('contract_offsets_ms')}`",
        f"- guard read-only/no-esoc0/no-rc/no-pci/no-hal: `{gate.get('contract_read_only')}` / `{gate.get('contract_no_esoc0_open')}` / `{gate.get('contract_no_rc_sel_case_write')}` / `{gate.get('contract_no_pci_rescan_or_bind')}` / `{gate.get('contract_no_wifi_hal_scan_connect')}`",
        f"- max mdm-status/pci/mhi/ks: `{gate.get('contract_max_mdm_status_count_total')}` / `{gate.get('contract_max_pci_dev_count')}` / `{gate.get('contract_max_mhi_bus_count')}` / `{gate.get('contract_max_ks_process_count')}`",
        f"- mhi-pipe/wlan0/pcie1-gdsc-line: `{gate.get('contract_mhi_pipe_seen')}` / `{gate.get('contract_wlan0_seen')}` / `{gate.get('contract_pcie1_gdsc_line_seen')}`",
        "",
    ])


def render_report(result: dict[str, Any]) -> str:
    text = BASE_RENDER_REPORT(result)
    return text.replace("\n## Safety Scope\n", "\n" + render_contract(result.get("gate", {})) + "\n## Safety Scope\n")


def main(argv: list[str] | None = None) -> int:
    configure_constants()
    base.classify_gate = classify_gate
    base.render_report = render_report
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
