#!/usr/bin/env python3
"""V1550 host-only classifier for pcie1 GDSC/regulator semantics.

V1549 fixed the active native Wi-Fi blocker at:

    RC1 PHY/LTSSM progress -> LTSSM_POLL_COMPLIANCE -> link failed -> no L0

while the low-overhead sampler still printed a `pcie_1_gdsc ... 0mV` line from
`regulator_summary`. This classifier reconciles that observation against the
stock source tree so the next gate does not over-interpret a debugfs voltage
column as a physical power-domain measurement.

It reads only repository files and existing evidence. It performs no device
command, tracefs write, flash, reboot, Wi-Fi action, or sysfs/debugfs mutation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1550-pcie1-power-domain-semantics-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1550_PCIE1_POWER_DOMAIN_SEMANTICS_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1550-pcie1-power-domain-semantics-classifier.txt")

SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
OSRC_DTS_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'arch', 'arm64', 'boot', 'dts', 'qcom')

PATHS = {
    "v1549_manifest": Path("tmp/wifi/v1549-low-overhead-result-classifier/manifest.json"),
    "v1549_report": Path("docs/reports/NATIVE_INIT_V1549_LOW_OVERHEAD_RESULT_CLASSIFIER_2026-06-02.md"),
    "v1315_report": Path("docs/reports/NATIVE_INIT_V1315_TRACEFS_LOWER_EVENT_PREFLIGHT_2026-05-31.md"),
    "pci_msm": SOURCE_ROOT / "drivers/pci/host/pci-msm.c",
    "regulator_core": SOURCE_ROOT / "drivers/regulator/core.c",
    "gdsc_regulator": SOURCE_ROOT / "drivers/clk/qcom/gdsc-regulator.c",
    "pcie_dtsi": OSRC_DTS_ROOT / "sm8150-pcie.dtsi",
    "gdsc_dtsi": OSRC_DTS_ROOT / "sm8150-gdsc.dtsi",
    "sm8150_dtsi": OSRC_DTS_ROOT / "sm8150.dtsi",
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


def source_line(path: Path, needle: str) -> str:
    text = read_text(path)
    for line_number, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return f"{rel(path)}:{line_number}: {line.strip()}"
    return f"{rel(path)}: missing {needle!r}"


def source_line_after(path: Path, anchor: str, needle: str) -> str:
    text = read_text(path)
    armed = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if anchor in line:
            armed = True
        if armed and needle in line:
            return f"{rel(path)}:{line_number}: {line.strip()}"
    return f"{rel(path)}: missing {needle!r} after {anchor!r}"


def source_line_after_last(path: Path, anchor: str, needle: str) -> str:
    lines = read_text(path).splitlines()
    start = None
    for line_number, line in enumerate(lines, start=1):
        if anchor in line:
            start = line_number
    if start is None:
        return f"{rel(path)}: missing anchor {anchor!r}"
    for line_number, line in enumerate(lines[start - 1 :], start=start):
        if needle in line:
            return f"{rel(path)}:{line_number}: {line.strip()}"
    return f"{rel(path)}: missing {needle!r} after last {anchor!r}"


def has_all(text: str, needles: tuple[str, ...]) -> bool:
    return all(needle in text for needle in needles)


def v1549_summary(manifest: dict[str, Any], report: str) -> dict[str, Any]:
    progress = manifest.get("manifest")
    if not isinstance(progress, dict):
        progress = {}
    wifi_progress = progress.get("wifi_progress")
    if not isinstance(wifi_progress, dict):
        wifi_progress = {}
    return {
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "native_no_l0_fixed": (
            "rc1-ltssm-link-failed-no-l0" in json.dumps(manifest, sort_keys=True)
            or "rc1-ltssm-link-failed-no-l0" in report
        ),
        "pre_fail_gdsc_zero_reported": (
            "`pcie_1_gdsc` is still reported as 0mV" in report
            or "pre-fail-pcie1-gdsc-zero-observed" in json.dumps(manifest, sort_keys=True)
        ),
        "wifi_progress": wifi_progress,
    }


def build_source_semantics() -> dict[str, Any]:
    pci = read_text(PATHS["pci_msm"])
    regulator = read_text(PATHS["regulator_core"])
    gdsc = read_text(PATHS["gdsc_regulator"])
    pcie_dtsi = read_text(PATHS["pcie_dtsi"])
    gdsc_dtsi = read_text(PATHS["gdsc_dtsi"])
    sm8150_dtsi = read_text(PATHS["sm8150_dtsi"])
    v1315 = read_text(PATHS["v1315_report"])

    return {
        "pcie_contract": {
            "pm_all": source_line(PATHS["pci_msm"], "#define PM_ALL"),
            "enumerate_uses_pm_all": source_line_after(PATHS["pci_msm"], "int msm_pcie_enumerate", "ret = msm_pcie_enable(dev, PM_ALL);"),
            "debugfs_enumerate_calls_enumerate": source_line_after(PATHS["pci_msm"], "static ssize_t msm_pcie_enumerate_store", "msm_pcie_enumerate(pcie_dev->rc_idx);"),
            "gdsc_handle": source_line(PATHS["pci_msm"], 'devm_regulator_get(&pdev->dev, "gdsc-vdd")'),
            "pcie1_gdsc_supply": source_line(PATHS["pcie_dtsi"], "gdsc-vdd-supply = <&pcie_1_gdsc>"),
            "pcie1_gdsc_definition": source_line(PATHS["gdsc_dtsi"], "pcie_1_gdsc: qcom,gdsc@0x18d004"),
            "pcie1_gdsc_enabled_in_sm8150": source_line(PATHS["sm8150_dtsi"], "&pcie_1_gdsc {"),
        },
        "enable_path": {
            "perst_assert": source_line(PATHS["pci_msm"], "PCIe: Assert the reset of endpoint of RC%d"),
            "vreg_enable_stage": source_line_after(PATHS["pci_msm"], "static int msm_pcie_enable", "ret = msm_pcie_vreg_init(dev);"),
            "clk_enable_stage": source_line_after(PATHS["pci_msm"], "static int msm_pcie_enable", "ret = msm_pcie_clk_init(dev);"),
            "gdsc_enable_in_clk_init": source_line(PATHS["pci_msm"], "rc = regulator_enable(dev->gdsc);"),
            "pipe_clock_stage": source_line_after(PATHS["pci_msm"], "static int msm_pcie_enable", "ret = msm_pcie_pipe_clk_init(dev);"),
            "phy_ready_log": source_line(PATHS["pci_msm"], "PCIe RC%d PHY is ready!"),
            "perst_release": source_line(PATHS["pci_msm"], "PCIe: Release the reset of endpoint of RC%d"),
            "ltssm_enable": source_line(PATHS["pci_msm"], "/* enable link training */"),
            "link_fail_cleanup": source_line(PATHS["pci_msm"], "PCIe RC%d link initialization failed"),
            "cleanup_pipe": source_line_after(PATHS["pci_msm"], "link_fail:", "msm_pcie_pipe_clk_deinit(dev);"),
            "cleanup_clk": source_line_after(PATHS["pci_msm"], "link_fail:", "msm_pcie_clk_deinit(dev);"),
            "cleanup_vreg": source_line_after(PATHS["pci_msm"], "clk_fail:", "msm_pcie_vreg_deinit(dev);"),
        },
        "regulator_summary_columns": {
            "name_use_open_bypass": source_line(PATHS["regulator_core"], 'rdev->use_count, rdev->open_count, rdev->bypass_count'),
            "voltage_column": source_line(PATHS["regulator_core"], '_regulator_get_voltage(rdev) / 1000'),
            "current_column": source_line(PATHS["regulator_core"], '_regulator_get_current_limit(rdev) / 1000'),
            "get_voltage_no_state": source_line(PATHS["regulator_core"], "NOTE: If the regulator is disabled it will return the voltage value."),
            "get_voltage_no_ops_fallback": source_line_after_last(PATHS["regulator_core"], "static int _regulator_get_voltage", "return -EINVAL;"),
            "enable_increments_use_count": source_line_after_last(PATHS["regulator_core"], "static int _regulator_enable", "rdev->use_count++;"),
            "disable_decrements_use_count": source_line_after_last(PATHS["regulator_core"], "static int _regulator_disable", "rdev->use_count--;"),
        },
        "gdsc_regulator_semantics": {
            "compatible": source_line(PATHS["gdsc_regulator"], '{ .compatible = "qcom,gdsc" }'),
            "rdesc_voltage": source_line(PATHS["gdsc_regulator"], "sc->rdesc.type = REGULATOR_VOLTAGE;"),
            "ops": source_line(PATHS["gdsc_regulator"], "static struct regulator_ops gdsc_ops"),
            "ops_enable": source_line(PATHS["gdsc_regulator"], ".enable = gdsc_enable"),
            "ops_disable": source_line(PATHS["gdsc_regulator"], ".disable = gdsc_disable"),
            "ops_lacks_get_voltage": ".get_voltage" not in gdsc and ".list_voltage" not in gdsc,
            "enable_poll_status": source_line(PATHS["gdsc_regulator"], "ret = poll_gdsc_status(sc, ENABLED);"),
            "disable_poll_status": source_line(PATHS["gdsc_regulator"], "ret = poll_gdsc_status(sc, DISABLED);"),
        },
        "tracefs_path": {
            "v1315_decision": "v1315-tracefs-lower-event-preflight-pass" in v1315,
            "regulator_events": "regulator:regulator_enable" in v1315
            and "regulator_enable_complete" in v1315,
            "clk_events": "clk:clk_enable" in v1315 and "clk_enable_complete" in v1315,
            "gpio_events": "gpio:gpio_direction" in v1315 and "gpio_value" in v1315,
        },
        "raw_source_checks": {
            "pci_enable_has_pm_all": has_all(pci, ("#define PM_ALL", "ret = msm_pcie_enable(dev, PM_ALL);")),
            "pci_enable_requests_gdsc": "rc = regulator_enable(dev->gdsc);" in pci,
            "pci_link_fail_cleans_resources": has_all(
                pci,
                ("link_fail:", "msm_pcie_pipe_clk_deinit(dev);", "msm_pcie_clk_deinit(dev);", "msm_pcie_vreg_deinit(dev);"),
            ),
            "regulator_summary_uses_use_count": "rdev->use_count" in regulator and "rdev->open_count" in regulator,
            "gdsc_regulator_lacks_voltage_ops": ".get_voltage" not in gdsc and ".list_voltage" not in gdsc,
            "pcie1_maps_to_gdsc_supply": "gdsc-vdd-supply = <&pcie_1_gdsc>" in pcie_dtsi
            and 'regulator-name = "pcie_1_gdsc"' in gdsc_dtsi,
            "tracefs_regulator_clk_gpio_available": "v1315-tracefs-lower-event-preflight-pass" in v1315
            and "regulator:regulator_enable" in v1315
            and "clk:clk_enable" in v1315
            and "gpio:gpio_direction" in v1315
            and "gpio_value" in v1315,
        },
    }


def build_checks(v1549: dict[str, Any], semantics: dict[str, Any]) -> list[dict[str, str]]:
    raw = semantics["raw_source_checks"]
    gdsc_sem = semantics["gdsc_regulator_semantics"]
    return [
        {
            "name": "v1549-fixed-no-l0-input-present",
            "result": "pass" if v1549["pass"] and v1549["native_no_l0_fixed"] else "fail",
            "detail": "V1549 evidence fixes current blocker at RC1 link failed / no L0",
        },
        {
            "name": "pcie1-enable-path-requests-gdsc",
            "result": "pass" if raw["pci_enable_has_pm_all"] and raw["pci_enable_requests_gdsc"] else "fail",
            "detail": "`msm_pcie_enumerate()` calls `msm_pcie_enable(PM_ALL)`, and `msm_pcie_clk_init()` calls `regulator_enable(dev->gdsc)`",
        },
        {
            "name": "pcie1-dts-maps-gdsc-vdd-to-pcie-1-gdsc",
            "result": "pass" if raw["pcie1_maps_to_gdsc_supply"] else "fail",
            "detail": "DTS maps `gdsc-vdd` to the `pcie_1_gdsc` qcom,gdsc regulator node",
        },
        {
            "name": "regulator-summary-zero-mv-is-not-state-proof",
            "result": "pass"
            if raw["regulator_summary_uses_use_count"] and gdsc_sem["ops_lacks_get_voltage"]
            else "fail",
            "detail": "`regulator_summary` prints a voltage column via `_regulator_get_voltage`; qcom GDSC has enable/disable/is_enabled ops but no voltage getter/list op",
        },
        {
            "name": "link-fail-cleans-up-gdsc-and-clocks",
            "result": "pass" if raw["pci_link_fail_cleans_resources"] else "fail",
            "detail": "After link failure, `msm_pcie_enable()` deinitializes pipe clocks, PCIe clocks/GDSC, and vregs unless keep-resources is set",
        },
        {
            "name": "next-observer-can-use-existing-tracefs-events",
            "result": "pass" if raw["tracefs_regulator_clk_gpio_available"] else "fail",
            "detail": "V1315 already proved target regulator/clk/gpio tracefs events and formats exist",
        },
    ]


def classify() -> dict[str, Any]:
    v1549_manifest = read_json(PATHS["v1549_manifest"])
    v1549_report = read_text(PATHS["v1549_report"])
    v1549 = v1549_summary(v1549_manifest, v1549_report)
    semantics = build_source_semantics()
    checks = build_checks(v1549, semantics)
    passed = all(item["result"] == "pass" for item in checks)
    return {
        "cycle": "V1550",
        "type": "host-only source/evidence classifier",
        "created_at": now_iso(),
        "host": collect_host_metadata(),
        "paths": {name: rel(path) for name, path in PATHS.items()},
        "decision": "v1550-pcie1-gdsc-summary-is-not-power-proof-tracefs-needed"
        if passed
        else "v1550-pcie1-power-domain-semantics-incomplete",
        "pass": passed,
        "v1549": v1549,
        "checks": checks,
        "semantics": semantics,
        "interpretation": {
            "fixed_blocker": "RC1 reaches PHY/LTSSM, then fails at LTSSM_POLL_COMPLIANCE without L0.",
            "source_path": "`msm_pcie_enumerate()` reaches `msm_pcie_enable(PM_ALL)`, so the normal source path requests vregs, GDSC, clocks, PHY, pipe clock, PERST release, and LTSSM.",
            "gdsc_voltage_column": "`pcie_1_gdsc ... 0mV` in `regulator_summary` is not direct physical-voltage proof: the GDSC regulator ops do not expose a voltage getter/list op, and `regulator_summary` still prints `_regulator_get_voltage()/1000`.",
            "remaining_use_count_gap": "The leading `0` use_count in sampled `pcie_1_gdsc` rows is still meaningful but not decisive with the current sampler; the source path should enable and then disable it around link failure, so event-level enable/disable timing is needed.",
            "not_next": "Do not repeat enumerate-only retries and do not move to firmware/MHI/WLFW/scan/connect until native RC1 L0 and PCI enumeration exist.",
        },
        "next_gate": {
            "cycle": "V1551",
            "summary": "bounded targeted tracefs observer for pcie1 regulator/clk/gpio events around the existing sysfs-client enumerate window",
            "must_capture": [
                "regulator:regulator_enable and regulator_enable_complete names containing pcie_1_gdsc, pm8150l_l3, pm8150_l5, VDD_CX_LEVEL",
                "regulator disable timing for the same names after link failure",
                "clk enable/complete timing for GCC_PCIE_1_* and pcie_phy/refgen clocks if names are present in trace lines",
                "gpio_value/gpio_direction events for GPIO102/PERST, GPIO104/WAKE, GPIO135/AP2MDM, GPIO142/MDM2AP",
                "dmesg LTSSM/link-fail timestamps for alignment",
            ],
            "guardrails": [
                "tracefs mount/write only inside bounded observer with cleanup verification",
                "no PMIC/GPIO/GDSC direct write from userspace",
                "no global PCI rescan or platform bind/unbind",
                "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
                "rollbackable test-boot handoff only if live capture is required",
            ],
        },
        "safety": {
            "host_only": True,
            "device_command_executed": False,
            "tracefs_write_executed": False,
            "flash_executed": False,
            "wifi_hal_or_connect_executed": False,
            "network_external_executed": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    semantics = result["semantics"]
    source = semantics["pcie_contract"] | semantics["enable_path"]
    regulator = semantics["regulator_summary_columns"]
    gdsc = semantics["gdsc_regulator_semantics"]
    tracefs = semantics["tracefs_path"]
    next_gate = result["next_gate"]
    return "\n".join(
        [
            "# Native Init V1550 PCIe1 Power-Domain Semantics Classifier",
            "",
            "## Summary",
            "",
            f"- Cycle: `{result['cycle']}`",
            f"- Type: `{result['type']}`",
            f"- Decision: `{result['decision']}`",
            f"- Result: `{'PASS' if result['pass'] else 'FAIL'}`",
            f"- Evidence: `{result['paths']['v1549_report']}`",
            "",
            "V1550 is host-only. It reconciles the V1549 pre-fail `pcie_1_gdsc ... 0mV` observation with `pci-msm.c`, the regulator core, the Qualcomm GDSC regulator driver, and SM8150 DTS. The active blocker remains `rc1-ltssm-link-failed-no-l0`; firmware/MHI/WLFW/connect-side work remains downstream.",
            "",
            "## Checks",
            "",
            markdown_table(
                ["check", "result", "detail"],
                [[item["name"], item["result"], item["detail"]] for item in checks],
            ),
            "",
            "## PCIe1 Source Path",
            "",
            markdown_table(
                ["field", "source line"],
                [
                    ["PM_ALL", source["pm_all"]],
                    ["sysfs enumerate", source["debugfs_enumerate_calls_enumerate"]],
                    ["enumerate PM_ALL", source["enumerate_uses_pm_all"]],
                    ["gdsc handle", source["gdsc_handle"]],
                    ["pcie1 gdsc supply", source["pcie1_gdsc_supply"]],
                    ["PERST assert", source["perst_assert"]],
                    ["vreg stage", source["vreg_enable_stage"]],
                    ["GDSC enable", source["gdsc_enable_in_clk_init"]],
                    ["pipe clock stage", source["pipe_clock_stage"]],
                    ["PHY ready", source["phy_ready_log"]],
                    ["PERST release", source["perst_release"]],
                    ["LTSSM enable", source["ltssm_enable"]],
                    ["link-fail cleanup", source["link_fail_cleanup"]],
                    ["cleanup pipe", source["cleanup_pipe"]],
                    ["cleanup clk/GDSC", source["cleanup_clk"]],
                    ["cleanup vreg", source["cleanup_vreg"]],
                ],
            ),
            "",
            "## Regulator/GDSC Semantics",
            "",
            markdown_table(
                ["field", "source line"],
                [
                    ["summary use/open/bypass", regulator["name_use_open_bypass"]],
                    ["summary voltage column", regulator["voltage_column"]],
                    ["summary current column", regulator["current_column"]],
                    ["get_voltage note", regulator["get_voltage_no_state"]],
                    ["get_voltage no-op fallback", regulator["get_voltage_no_ops_fallback"]],
                    ["enable increments use_count", regulator["enable_increments_use_count"]],
                    ["disable decrements use_count", regulator["disable_decrements_use_count"]],
                    ["GDSC compatible", gdsc["compatible"]],
                    ["GDSC type", gdsc["rdesc_voltage"]],
                    ["GDSC ops", gdsc["ops"]],
                    ["GDSC enable op", gdsc["ops_enable"]],
                    ["GDSC disable op", gdsc["ops_disable"]],
                    ["GDSC lacks voltage ops", gdsc["ops_lacks_get_voltage"]],
                ],
            ),
            "",
            "The `0mV` value is a debugfs voltage-column artifact for this GDSC class, not a direct proof that the physical PCIe1 power domain never turned on. The use-count column still needs precise event-level timing because source code says `regulator_enable(dev->gdsc)` should increment use_count before the PHY/LTSSM path and link-fail cleanup should later disable it.",
            "",
            "## Tracefs Readiness",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["V1315 preflight decision present", tracefs["v1315_decision"]],
                    ["regulator events available", tracefs["regulator_events"]],
                    ["clk events available", tracefs["clk_events"]],
                    ["gpio events available", tracefs["gpio_events"]],
                ],
            ),
            "",
            "## Interpretation",
            "",
            f"- Fixed blocker: {result['interpretation']['fixed_blocker']}",
            f"- Source path: {result['interpretation']['source_path']}",
            f"- GDSC voltage column: {result['interpretation']['gdsc_voltage_column']}",
            f"- Remaining gap: {result['interpretation']['remaining_use_count_gap']}",
            f"- Parked work: {result['interpretation']['not_next']}",
            "",
            "## Next Gate",
            "",
            f"- Cycle: `{next_gate['cycle']}`",
            f"- Summary: {next_gate['summary']}",
            *(f"- Capture: {item}" for item in next_gate["must_capture"]),
            *(f"- Guardrail: {item}" for item in next_gate["guardrails"]),
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, tracefs write, reboot, flash, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, global PCI rescan, or platform bind/unbind.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = classify()
    report = render_report(result)
    store = EvidenceStore(repo_path(args.out_dir))
    result["out_dir"] = str(store.run_dir)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "next_gate": result["next_gate"]["cycle"],
                "out_dir": rel(args.out_dir),
                "pass": result["pass"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
