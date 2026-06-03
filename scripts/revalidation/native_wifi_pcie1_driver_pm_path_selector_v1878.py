#!/usr/bin/env python3
"""V1878 host-only pcie1 driver PM path selector."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "docs" / "reports"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1878-pcie1-driver-pm-path-selector"
DEFAULT_REPORT_PATH = (
    REPORTS / "NATIVE_INIT_V1878_PCIE1_DRIVER_PM_PATH_SELECTOR_2026-06-03.md"
)
DEFAULT_V1877_REPORT = REPORTS / "NATIVE_INIT_V1877_POWER_CLOCK_GATE_SELECTOR_2026-06-03.md"
DEFAULT_V1876_REPORT = (
    REPORTS / "NATIVE_INIT_V1876_LOWER_RESPONSE_READONLY_SAMPLER_HANDOFF_2026-06-03.md"
)
DEFAULT_V1549_REPORT = (
    REPORTS / "NATIVE_INIT_V1549_LOW_OVERHEAD_RESULT_CLASSIFIER_2026-06-02.md"
)
DEFAULT_V1354_REPORT = (
    REPORTS / "NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md"
)
DEFAULT_PCI_MSM_SOURCE = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v766-icnss-qcacld-patch-apply-build"
    / "source"
    / "drivers"
    / "pci"
    / "host"
    / "pci-msm.c"
)
DEFAULT_SM8150_PCIE_DTSI = (
    REPO_ROOT
    / "kernel_build"
    / "SM-A908N_KOR_12_Opensource"
    / "Kernel"
    / "arch"
    / "arm64"
    / "boot"
    / "dts"
    / "qcom"
    / "sm8150-pcie.dtsi"
)


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
        "v1877": read_text_artifact(args.v1877_report),
        "v1876": read_text_artifact(args.v1876_report),
        "v1549": read_text_artifact(args.v1549_report),
        "v1354": read_text_artifact(args.v1354_report),
        "pci_msm": read_text_artifact(args.pci_msm_source),
        "sm8150_pcie_dtsi": read_text_artifact(args.sm8150_pcie_dtsi),
    }

    checks = {
        "v1877_requires_source_selector_before_resource_gate": contains_all(
            artifacts["v1877"],
            [
                "v1877-clock-debug-surface-closed-pcie-resource-gate-needed-host-pass",
                "pcie1-driver-pm-resource-path-source-selector",
                "stop for explicit approval before building any narrowly targeted pcie1 resource/GDSC write gate",
            ],
        ),
        "current_prereqs_still_absent": contains_all(
            artifacts["v1876"],
            [
                "mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`",
                "max mdm-status/pci/mhi/ks: `0` / `0` / `0` / `0`",
                "Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present",
            ],
        ),
        "pcie1_dtsi_is_client_enumerated": contains_all(
            artifacts["sm8150_pcie_dtsi"],
            [
                "qcom,pcie@1c08000",
                "gdsc-vdd-supply = <&pcie_1_gdsc>;",
                "perst-gpio = <&tlmm 102 0>;",
                "wake-gpio = <&tlmm 104 0>;",
                "qcom,boot-option = <0x1>;",
                "linux,pci-domain = <1>;",
            ],
        ),
        "only_clean_pre_enumeration_driver_entry_is_enumerate": contains_all(
            artifacts["pci_msm"],
            [
                "int msm_pcie_enumerate(u32 rc_idx)",
                "ret = msm_pcie_enable(dev, PM_ALL);",
                "pci_scan_root_bus_bridge(bridge)",
                "pci_bus_add_devices(bus)",
                "EXPORT_SYMBOL(msm_pcie_enumerate);",
                "DEVICE_ATTR(enumerate, 0200, NULL, msm_pcie_enumerate_store)",
            ],
        ),
        "pm_resume_path_requires_existing_pci_dev": contains_all(
            artifacts["pci_msm"],
            [
                "int msm_pcie_pm_control(enum msm_pcie_pm_opt pm_opt, u32 busnr, void *user,",
                "PCIe: endpoint device is NULL",
                "pcie_dev = PCIE_BUS_PRIV_DATA(((struct pci_dev *)user)->bus);",
                "msm_pcie_pm_resume(dev, user, data, options)",
                "EXPORT_SYMBOL(msm_pcie_pm_control);",
            ],
        ),
        "debugfs_case_surfaces_are_broad_or_forbidden": contains_all(
            artifacts["pci_msm"],
            [
                "debugfs_create_file(\"rc_sel\", 0664,",
                "debugfs_create_file(\"case\", 0664,",
                "case MSM_PCIE_ENABLE_LINK:",
                "case MSM_PCIE_ENUMERATION:",
                "case MSM_PCIE_ASSERT_PERST:",
                "case MSM_PCIE_KEEP_RESOURCES_ON:",
                "gpio_set_value(dev->gpio[MSM_PCIE_GPIO_PERST].num,",
                "msm_pcie_keep_resources_on |= BIT(dev->rc_idx);",
            ],
        ),
        "previous_targeted_enumeration_did_not_create_downstream": contains_all(
            artifacts["v1549"],
            [
                "v1549-low-overhead-confirms-pre-fail-gpio-gdsc-no-l0",
                "trigger mode | sysfs_client_enumerate",
                "L0 / downstream | False / False",
                "pre-fail-pcie1-gdsc-zero-observed",
            ],
        )
        and contains_all(
            artifacts["v1354"],
            [
                "v1354-current-route-pcie1-rc-stayed-off",
                "timing_pci_dev_max | 0",
                "timing_mhi_bus_max | 0",
                "timing_wlan0_seen | False",
            ],
        ),
        "host_only_no_live_mutation": True,
    }

    pass_ok = all(checks.values())
    decision = (
        "v1878-no-safe-pcie1-driver-pm-userspace-path-host-pass"
        if pass_ok
        else "v1878-pcie1-driver-pm-path-selector-review"
    )
    label = "explicit-resource-gdsc-approval-needed" if pass_ok else "review"

    return {
        "cycle": "V1878",
        "type": "host-only pcie1 driver PM path selector",
        "decision": decision,
        "label": label,
        "pass": pass_ok,
        "reason": (
            "The source exposes targeted pcie1 client enumeration before PCI devices "
            "exist, but that path is the already-tested PM_ALL + root-bus scan path. "
            "The resume PM-control path requires an existing pci_dev, which the native "
            "route does not have. The remaining userspace debugfs surfaces are broad "
            "or explicitly forbidden, so a live driver-PM retry is not a new safe gate."
        ),
        "checks": checks,
        "inputs": {name: artifact["path"] for name, artifact in artifacts.items()},
        "summaries": {
            "v1877": summarize(
                artifacts["v1877"],
                ["Decision:", "Label:", "Preferred path:", "Fallback path:"],
            ),
            "v1876": summarize(
                artifacts["v1876"],
                ["mdm3/MHI/WLFW69/wlan0", "max mdm-status/pci/mhi/ks"],
            ),
            "v1549": summarize(
                artifacts["v1549"],
                ["Decision:", "trigger mode |", "L0 / downstream", "pre-fail-pcie1-gdsc-zero-observed"],
            ),
            "v1354": summarize(
                artifacts["v1354"],
                ["Decision", "timing_pci_dev_max", "timing_mhi_bus_max", "timing_wlan0_seen"],
            ),
            "pci_msm": summarize(
                artifacts["pci_msm"],
                [
                    "int msm_pcie_enumerate",
                    "ret = msm_pcie_enable(dev, PM_ALL);",
                    "DEVICE_ATTR(enumerate",
                    "int msm_pcie_pm_control",
                    "PCIe: endpoint device is NULL",
                    "debugfs_create_file(\"case\"",
                    "case MSM_PCIE_KEEP_RESOURCES_ON:",
                ],
            ),
            "sm8150_pcie_dtsi": summarize(
                artifacts["sm8150_pcie_dtsi"],
                ["qcom,pcie@1c08000", "gdsc-vdd-supply = <&pcie_1_gdsc>;", "qcom,boot-option = <0x1>;", "linux,pci-domain = <1>;"],
            ),
        },
        "selected_next_gate": {
            "cycle": "V1879",
            "label": "pcie1-resource-gdsc-gate-explicit-approval-required",
            "type": "stop-before-build unless explicit approval is given",
            "approval_boundary": (
                "Any helper or boot image containing a narrowly targeted pcie1 "
                "resource/GDSC write gate requires explicit approval before build or live use."
            ),
            "if_approved_preflight_contract": [
                "source/build-only first with fail-closed compile-time and runtime flags",
                "single named pcie1 resource/GDSC target only; no PMIC/GPIO/PERST writes",
                "no direct `/dev/subsys_esoc0`, fake ONLINE, eSoC notify, BOOT_DONE, forced RC1, PCI rescan, or platform bind/unbind",
                "artifact sanity must reject Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping strings",
                "live handoff still stops unless WLFW service 69 and `wlan0` become present",
            ],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    summaries = result["summaries"]
    next_gate = result["selected_next_gate"]
    return "\n".join([
        "# Native Init V1878 pcie1 Driver PM Path Selector",
        "",
        "## Summary",
        "",
        "- Cycle: `V1878`",
        "- Type: host-only pcie1 driver PM path selector",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "- Evidence: `tmp/wifi/v1878-pcie1-driver-pm-path-selector`",
        "",
        "## Checks",
        "",
        "| check | value |",
        "|---|---:|",
        *(f"| `{key}` | `{value}` |" for key, value in checks.items()),
        "",
        "## Evidence Chain",
        "",
        f"- V1877 selector: {summaries['v1877']['lines']['Decision:']} / {summaries['v1877']['lines']['Label:']}",
        f"- V1877 preferred path: {summaries['v1877']['lines']['Preferred path:']}",
        f"- V1877 fallback: {summaries['v1877']['lines']['Fallback path:']}",
        f"- V1876 prereqs: {summaries['v1876']['lines']['mdm3/MHI/WLFW69/wlan0']}",
        f"- V1876 lower counts: {summaries['v1876']['lines']['max mdm-status/pci/mhi/ks']}",
        f"- V1549 targeted enumerate result: {summaries['v1549']['lines']['Decision:']}",
        f"- V1549 trigger/downstream: {summaries['v1549']['lines']['trigger mode |']} / {summaries['v1549']['lines']['L0 / downstream']}",
        f"- V1354 private-route observer: {summaries['v1354']['lines']['Decision']}",
        f"- DTS pcie1 node: {summaries['sm8150_pcie_dtsi']['lines']['qcom,pcie@1c08000']}",
        f"- DTS pcie1 GDSC: {summaries['sm8150_pcie_dtsi']['lines']['gdsc-vdd-supply = <&pcie_1_gdsc>;']}",
        f"- DTS boot option/domain: {summaries['sm8150_pcie_dtsi']['lines']['qcom,boot-option = <0x1>;']} / {summaries['sm8150_pcie_dtsi']['lines']['linux,pci-domain = <1>;']}",
        f"- Driver enumerate entry: {summaries['pci_msm']['lines']['int msm_pcie_enumerate']}",
        f"- Driver enumerate action: {summaries['pci_msm']['lines']['ret = msm_pcie_enable(dev, PM_ALL);']}",
        f"- Driver sysfs enumerate: {summaries['pci_msm']['lines']['DEVICE_ATTR(enumerate']}",
        f"- Driver PM control entry: {summaries['pci_msm']['lines']['int msm_pcie_pm_control']}",
        f"- Driver PM control prerequisite: {summaries['pci_msm']['lines']['PCIe: endpoint device is NULL']}",
        f"- Driver debugfs broad case: {summaries['pci_msm']['lines']['debugfs_create_file(\"case\"']}",
        f"- Driver keep-resources case: {summaries['pci_msm']['lines']['case MSM_PCIE_KEEP_RESOURCES_ON:']}",
        "",
        "## Interpretation",
        "",
        "The pcie1 device tree is intentionally client-enumerated (`qcom,boot-option = <0x1>`), so the clean pre-PCI userspace-visible driver entry is the targeted `debug/enumerate` sysfs path. That path calls `msm_pcie_enumerate()`, which enables PM_ALL and starts the PCI root-bus scan. V1549 already used that targeted enumerate path and still reached no L0/downstream with `pcie_1_gdsc` at zero.",
        "",
        "`msm_pcie_pm_control()` is not usable as a new pre-enumeration path from native init: it requires an existing endpoint `pci_dev` user object and the current route has no PCI device, MHI bus, WLFW service, or `wlan0`. The remaining debugfs cases include rc selection, case dispatch, PERST mutation, keep-resources flags, and broad enable/enumeration actions, which overlap existing forbidden or already-tested surfaces.",
        "",
        "Therefore V1878 does not select a live driver-PM retry. The next write-capable gate crosses the approval boundary: a narrowly targeted pcie1 resource/GDSC preflight must be explicitly approved before build or live use.",
        "",
        "## Selected Next Gate",
        "",
        f"- Cycle: `{next_gate['cycle']}`",
        f"- Label: `{next_gate['label']}`",
        f"- Type: `{next_gate['type']}`",
        f"- Approval boundary: {next_gate['approval_boundary']}",
        *(f"- If approved preflight: {item}" for item in next_gate["if_approved_preflight_contract"]),
        "- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present.",
        "",
        "## Safety Scope",
        "",
        "V1878 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC/regulator controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1877-report", type=Path, default=DEFAULT_V1877_REPORT)
    parser.add_argument("--v1876-report", type=Path, default=DEFAULT_V1876_REPORT)
    parser.add_argument("--v1549-report", type=Path, default=DEFAULT_V1549_REPORT)
    parser.add_argument("--v1354-report", type=Path, default=DEFAULT_V1354_REPORT)
    parser.add_argument("--pci-msm-source", type=Path, default=DEFAULT_PCI_MSM_SOURCE)
    parser.add_argument("--sm8150-pcie-dtsi", type=Path, default=DEFAULT_SM8150_PCIE_DTSI)
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
