#!/usr/bin/env python3
"""V1873 host/source-only lower-response input contract selector."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1873-lower-response-input-contract"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1873_LOWER_RESPONSE_INPUT_CONTRACT_2026-06-03.md"
)
REPORTS = REPO_ROOT / "docs" / "reports"
DEFAULT_V1872_REPORT = REPORTS / "NATIVE_INIT_V1872_LOWER_RESPONSE_INPUT_RECONCILE_2026-06-03.md"
DEFAULT_V1870_REPORT = REPORTS / "NATIVE_INIT_V1870_SDX50M_PRIVATE_MOUNT_SUMMARY_HANDOFF_2026-06-03.md"
DEFAULT_V1239_REPORT = REPORTS / "NATIVE_INIT_V1239_POST_ESOC0_POWERUP_GAP_CLASSIFIER_2026-05-31.md"
DEFAULT_V1371_REPORT = REPORTS / "NATIVE_INIT_V1371_RC1_LTSSM_FAILURE_CLASSIFIER_2026-06-01.md"
DEFAULT_V1502_REPORT = REPORTS / "NATIVE_INIT_V1502_WIFI_PRE_L0_PARITY_CLASSIFIER_2026-06-01.md"
DEFAULT_V1525_REPORT = REPORTS / "NATIVE_INIT_V1525_MHI_PM_RESUME_POSITION_CLASSIFIER_2026-06-02.md"
DEFAULT_V1662_REPORT = REPORTS / "NATIVE_INIT_V1662_ANDROID_NATIVE_POWER_DIFF_CLASSIFIER_2026-06-02.md"
DEFAULT_V1752_REPORT = REPORTS / "NATIVE_INIT_V1752_WLAN_PD_DOWNSTREAM_CLASSIFIER_2026-06-03.md"
DEFAULT_V1763_REPORT = REPORTS / "NATIVE_INIT_V1763_WLAN_PD_FIRMWARE_REQUEST_GATE_RECONCILIATION_2026-06-03.md"
DEFAULT_HELPER_SOURCE = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text_artifact(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path), "text": ""}
    return {
        "exists": True,
        "path": rel(path),
        "text": path.read_text(encoding="utf-8", errors="replace"),
    }


def contains_all(artifact: dict[str, Any], markers: list[str]) -> bool:
    text = str(artifact.get("text") or "")
    return bool(artifact.get("exists")) and all(marker in text for marker in markers)


def contains_none(artifact: dict[str, Any], markers: list[str]) -> bool:
    text = str(artifact.get("text") or "")
    return bool(artifact.get("exists")) and all(marker not in text for marker in markers)


def first_matching_line(artifact: dict[str, Any], needle: str) -> str:
    for line in str(artifact.get("text") or "").splitlines():
        if needle in line:
            stripped = line.strip()
            if stripped.startswith("- "):
                return stripped[2:].strip()
            return stripped
    return ""


def summarize(artifact: dict[str, Any], needles: list[str]) -> dict[str, Any]:
    return {
        "exists": bool(artifact.get("exists")),
        "path": artifact.get("path", ""),
        "lines": {needle: first_matching_line(artifact, needle) for needle in needles},
    }


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    artifacts = {
        "v1872": read_text_artifact(args.v1872_report),
        "v1870": read_text_artifact(args.v1870_report),
        "v1239": read_text_artifact(args.v1239_report),
        "v1371": read_text_artifact(args.v1371_report),
        "v1502": read_text_artifact(args.v1502_report),
        "v1525": read_text_artifact(args.v1525_report),
        "v1662": read_text_artifact(args.v1662_report),
        "v1752": read_text_artifact(args.v1752_report),
        "v1763": read_text_artifact(args.v1763_report),
        "helper_source": read_text_artifact(args.helper_source),
    }

    checks = {
        "v1872_selected_lower_response_input_contract": contains_all(
            artifacts["v1872"],
            [
                "v1872-pm-vote-closed-lower-response-input-next-host-pass",
                "lower-response-input-contract-source-only",
                "Do not attempt Wi-Fi connect or ping until WLFW service 69",
            ],
        ),
        "v1870_current_private_route_has_no_wifi_prereq": contains_all(
            artifacts["v1870"],
            [
                "v1870-private-mount-sdx50m-selected-rollback-pass",
                "mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`",
                "PM-client register/connect/return-path rc: `0` / `0` / `0`",
            ],
        ),
        "v1239_places_gap_after_powerup_before_response": contains_all(
            artifacts["v1239"],
            [
                "v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw",
                "GPIO142 IRQ | `1` | not observed",
                "PCIe RC1 | RC1 reset/L0 present | not observed in lower publication",
                "`ks` / MHI pipe | present | absent",
            ],
        ),
        "v1371_proves_endpoint_readiness_gap_after_rc1_power": contains_all(
            artifacts["v1371"],
            [
                "v1371-endpoint-readiness-gap-after-rc1-power-proven",
                "stops in poll/compliance before L0",
                "native_created_no_pci_or_mhi",
                "native_released_perst",
            ],
        ),
        "v1502_confirms_pre_l0_endpoint_lines_low": contains_all(
            artifacts["v1502"],
            [
                "v1502-pre-l0-parity-confirms-rc1-link-fail-with-endpoint-lines-low",
                "GPIO142 mdm-status IRQ counts stay zero",
                "MHI/WLFW/BDF/FW-ready/wlan0: `False/False/False/False/False`",
            ],
        ),
        "v1525_parks_mhi_resume_until_first_l0_exists": contains_all(
            artifacts["v1525"],
            [
                "v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger",
                "MHI PM-resume requires an existing pci_dev",
                "Firmware, MHI deep dive, WLFW, scan/connect, credentials, DHCP/routes, and external ping remain downstream",
            ],
        ),
        "v1662_requires_power_clock_snapshot_without_write_gate": contains_all(
            artifacts["v1662"],
            [
                "v1662-android-native-power-diff-power-vote-gap-pass",
                "pcie_1_gdsc",
                "gcc_pcie1_phy_refgen_clk",
                "no_autonomous_write_gate",
            ],
        ),
        "wlanpd_firmware_lane_not_connect_ready": contains_all(
            artifacts["v1752"],
            [
                "v1752-pure-route-default-sm-blocker-reconciled-service-route-downstream-pass",
                "no WLFW service 69",
                "no `wlan0`",
            ],
        )
        and contains_all(
            artifacts["v1763"],
            [
                "v1763-v1739-equivalent-firmware-request-gate-closed-host-pass",
                "Label: `firmware-not-requested`",
                "Do not return to route minimization",
            ],
        ),
        "helper_has_post_pm_private_lower_observer_surface": contains_all(
            artifacts["helper_source"],
            [
                "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
                "pm_observer_private_cnss_daemon_sdx50m",
                "private_cnss_daemon.expected_c_string=SDX50M",
                "wlfw_service69_seen",
                "sys_class_net_wlan0",
            ],
        ),
        "contract_not_already_implemented": contains_none(
            artifacts["helper_source"],
            [
                "lower-response-input-contract",
                "lower_response_input_contract",
            ],
        ),
    }

    pass_ok = all(checks.values())
    label = "lower-response-readonly-sampler-source-build-next" if pass_ok else "review"
    decision = (
        "v1873-lower-response-input-contract-selected-host-pass"
        if pass_ok
        else "v1873-lower-response-input-contract-review"
    )

    return {
        "cycle": "V1873",
        "type": "host/source-only lower-response input contract selector",
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": (
            "The current private SDX50M route and historical post-esoc0 evidence converge on a pre-Wi-Fi "
            "lower-response input gap; the next useful unit is a read-only sampler contract around GPIO142, "
            "PCIe RC1/L0, pcie1 power/clock state, SSCTL/sysmon, MHI, ks, WLFW, and wlan0, not a connect attempt."
        ),
        "checks": checks,
        "inputs": {name: artifact["path"] for name, artifact in artifacts.items()},
        "summaries": {
            "v1872": summarize(artifacts["v1872"], ["Decision:", "Label:", "Scope:"]),
            "v1870": summarize(artifacts["v1870"], ["Decision:", "mdm3/MHI/WLFW69/wlan0", "PM-client register/connect"]),
            "v1239": summarize(artifacts["v1239"], ["decision:", "| GPIO142 IRQ |", "| PCIe RC1 |", "`ks` / MHI pipe"]),
            "v1371": summarize(artifacts["v1371"], ["Decision:", "native_created_no_pci_or_mhi", "native_released_perst"]),
            "v1502": summarize(artifacts["v1502"], ["Decision:", "GPIO142 mdm-status IRQ counts stay zero", "MHI/WLFW/BDF/FW-ready/wlan0"]),
            "v1525": summarize(artifacts["v1525"], ["Decision:", "MHI PM-resume requires an existing pci_dev"]),
            "v1662": summarize(artifacts["v1662"], ["Decision:", "| pcie_1_gdsc |", "| gcc_pcie1_phy_refgen_clk |"]),
            "v1763": summarize(artifacts["v1763"], ["Decision:", "Fixed label:"]),
        },
        "selected_next_gate": {
            "cycle": "V1874",
            "label": "lower-response-readonly-sampler-source-build",
            "type": "source/build-only first; live disabled until artifact sanity",
            "base": "extend the v356 `wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only` route",
            "scope": [
                "trigger only from the existing PM-service/CNSS private SDX50M path; do not directly open `/dev/subsys_esoc0`",
                "sample GPIO142/MDM2AP IRQ and readable AP2MDM/MDM2AP pin state at dense post-powerup offsets",
                "sample pcie1 GDSC/regulator/clock/link-state/read-only dmesg markers without rc_sel/case, PCI rescan, or bind/unbind",
                "sample SSCTL/sysmon, MHI bus/devices, `ks` process/fd state, QRTR WLFW service 69, BDF, firmware-ready, and `wlan0`",
                "classify lower progress before any Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
            ],
            "labels": [
                "lower-input-mdm2ap-silent",
                "lower-input-rc1-natural-attempt-no-l0",
                "lower-input-power-clock-snapshot-gap",
                "lower-input-mhi-or-wlfw-progress-readonly-stop",
                "lower-input-wifi-prereq-present-readonly-stop",
            ],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    summaries = result["summaries"]
    next_gate = result["selected_next_gate"]
    return "\n".join([
        "# Native Init V1873 Lower Response Input Contract",
        "",
        "## Summary",
        "",
        "- Cycle: `V1873`",
        "- Type: host/source-only lower-response input contract selector",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "- Evidence: `tmp/wifi/v1873-lower-response-input-contract`",
        "",
        "## Checks",
        "",
        "| check | value |",
        "|---|---:|",
        *(f"| `{key}` | `{value}` |" for key, value in checks.items()),
        "",
        "## Evidence Chain",
        "",
        f"- V1872 selector: {summaries['v1872']['lines']['Decision:']} / {summaries['v1872']['lines']['Label:']}",
        f"- V1870 current lower state: {summaries['v1870']['lines']['mdm3/MHI/WLFW69/wlan0']}",
        f"- V1870 PM return: {summaries['v1870']['lines']['PM-client register/connect']}",
        f"- V1239 response gap: {summaries['v1239']['lines']['decision:']}",
        f"- V1239 GPIO142: {summaries['v1239']['lines']['| GPIO142 IRQ |']}",
        f"- V1239 PCIe: {summaries['v1239']['lines']['| PCIe RC1 |']}",
        f"- V1239 ks/MHI: {summaries['v1239']['lines']['`ks` / MHI pipe']}",
        f"- V1371 RC1: {summaries['v1371']['lines']['Decision:']}",
        f"- V1502 pre-L0: {summaries['v1502']['lines']['Decision:']}",
        f"- V1525 MHI position: {summaries['v1525']['lines']['Decision:']}",
        f"- V1662 power/clock diff: {summaries['v1662']['lines']['Decision:']}",
        f"- V1763 firmware-request lane: {summaries['v1763']['lines']['Decision:']} / {summaries['v1763']['lines']['Fixed label:']}",
        "",
        "## Interpretation",
        "",
        "V1873 keeps the blocker below the current PM-client/register path and before Wi-Fi connectivity. V1870 proves the latest private SDX50M run still has no WLFW service 69 or `wlan0`, while V1239/V1371/V1502/V1525 place the actionable gap before first usable PCIe L0/MHI/WLFW publication. V1662 adds a required read-only pcie1 power/clock snapshot dimension, but it does not authorize a power/clock write gate.",
        "",
        "The WLAN-PD firmware-request lane remains useful evidence, but it is not a connect-ready lane: V1763 fixes the label as `firmware-not-requested`, and the current private SDX50M route still lacks WLFW service 69 and `wlan0`. Therefore the next unit should be a source/build-only read-only sampler contract, not Wi-Fi HAL, scan/connect, DHCP, routes, or ping.",
        "",
        "## Next Contract",
        "",
        f"- Cycle: `{next_gate['cycle']}`",
        f"- Label: `{next_gate['label']}`",
        f"- Type: `{next_gate['type']}`",
        f"- Base: {next_gate['base']}",
        *(f"- Scope: {item}" for item in next_gate["scope"]),
        *(f"- Output label: `{item}`" for item in next_gate["labels"]),
        "- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.",
        "",
        "## Safety Scope",
        "",
        "V1873 is host/source-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1872-report", type=Path, default=DEFAULT_V1872_REPORT)
    parser.add_argument("--v1870-report", type=Path, default=DEFAULT_V1870_REPORT)
    parser.add_argument("--v1239-report", type=Path, default=DEFAULT_V1239_REPORT)
    parser.add_argument("--v1371-report", type=Path, default=DEFAULT_V1371_REPORT)
    parser.add_argument("--v1502-report", type=Path, default=DEFAULT_V1502_REPORT)
    parser.add_argument("--v1525-report", type=Path, default=DEFAULT_V1525_REPORT)
    parser.add_argument("--v1662-report", type=Path, default=DEFAULT_V1662_REPORT)
    parser.add_argument("--v1752-report", type=Path, default=DEFAULT_V1752_REPORT)
    parser.add_argument("--v1763-report", type=Path, default=DEFAULT_V1763_REPORT)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_result(args)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    report = render_report(result)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "label": result["label"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
