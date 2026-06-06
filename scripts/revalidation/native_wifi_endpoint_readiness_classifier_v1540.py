#!/usr/bin/env python3
"""V1540 host-only endpoint-readiness classifier after sysfs enumerate no-L0."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1540-endpoint-readiness-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1540_ENDPOINT_READINESS_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1540-endpoint-readiness-classifier.txt")

V1539_MANIFEST = Path("tmp/wifi/v1539-sysfs-enumerate-result-classifier/manifest.json")
V1538_DMESG = Path("tmp/wifi/v1538-wifi-sysfs-client-enumerate-handoff/test-v1393-dmesg.stdout.txt")
V1538_WINDOW = Path("tmp/wifi/v1538-wifi-sysfs-client-enumerate-handoff/test-rc1-window-result.stdout.txt")
V852_DMESG = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt"
)
V852_INTERRUPTS = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/android/commands/interrupts-focus.txt"
)

SOURCE_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')
PCIE_DTSI = SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi"
SDX50M_DTSI = SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi"
EXT_SOC_DTSI = SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi"
MHI_DTSI = SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-mhi.dtsi"
PCI_MSM_SOURCE = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c")


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


def first_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
        if match:
            return float(match.group(1))
    return None


def matching_lines(text: str, pattern: str, limit: int = 24) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def source_lines(text: str, needles: tuple[str, ...], limit: int = 32) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), 1):
        if any(needle in line for needle in needles):
            rows.append({"line": index, "text": line.strip()})
            if len(rows) >= limit:
                break
    return rows


def extract_node_block(text: str, marker: str) -> tuple[int | None, int | None, str]:
    lines = text.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        if marker in line:
            start_index = index
            break
    if start_index is None:
        return None, None, ""
    depth = 0
    seen_open = False
    for index in range(start_index, len(lines)):
        line = lines[index]
        depth += line.count("{")
        if "{" in line:
            seen_open = True
        depth -= line.count("}")
        if seen_open and depth <= 0 and "};" in line:
            return start_index + 1, index + 1, "\n".join(lines[start_index : index + 1])
    return start_index + 1, None, "\n".join(lines[start_index:])


def first_line_in_block(block: str, needle: str) -> str:
    for line in block.splitlines():
        if needle in line:
            return line.strip()
    return ""


def gpio_level_values(text: str, gpio: int) -> list[int]:
    values: list[int] = []
    regex = re.compile(rf"\bgpio{gpio}\s*:\s*(?:in|out)\s+([01])\b")
    for match in regex.finditer(text):
        values.append(int(match.group(1)))
    return values


def irq_totals(text: str, gpio: int) -> list[int]:
    totals: list[int] = []
    for line in text.splitlines():
        if f"msmgpio-dc {gpio}" not in line and f"msmgpio-dc  {gpio}" not in line:
            continue
        prefix = line.split("msmgpio-dc", 1)[0]
        numbers = [int(value) for value in re.findall(r"\b\d+\b", prefix)]
        if len(numbers) > 1:
            totals.append(sum(numbers[1:]))
    return totals


def pcie1_gdsc_rows(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if "pcie_1_gdsc" in line]


def extract_function_body(source: str, signature: str) -> tuple[int | None, int | None, str]:
    match = re.search(signature, source, re.M)
    if not match:
        return None, None, ""
    prefix = source[: match.start()]
    start_line = prefix.count("\n") + 1
    brace_start = source.find("{", match.end())
    if brace_start < 0:
        return start_line, None, ""
    depth = 0
    for index in range(brace_start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                body = source[match.start() : index + 1]
                end_line = source[: index + 1].count("\n") + 1
                return start_line, end_line, body
    return start_line, None, source[match.start() :]


def extract_named_slice(source: str, start_needle: str, next_needle: str) -> tuple[int | None, int | None, str]:
    start = source.find(start_needle)
    if start < 0:
        return None, None, ""
    end = source.find(next_needle, start + len(start_needle))
    if end < 0:
        end = len(source)
    start_line = source[:start].count("\n") + 1
    end_line = source[:end].count("\n") + 1
    return start_line, end_line, source[start:end]


def analyze_sources() -> dict[str, Any]:
    pcie_dtsi = read_text(PCIE_DTSI)
    sdx50m_dtsi = read_text(SDX50M_DTSI)
    ext_soc_dtsi = read_text(EXT_SOC_DTSI)
    mhi_dtsi = read_text(MHI_DTSI)
    pci_msm = read_text(PCI_MSM_SOURCE)
    pcie1_start, pcie1_end, pcie1_block = extract_node_block(pcie_dtsi, "pcie1: qcom,pcie@1c08000")
    enable_start, enable_end, enable_body = extract_named_slice(
        pci_msm,
        "static int msm_pcie_enable(struct msm_pcie_dev_t *dev, u32 options)",
        "static void msm_pcie_disable(struct msm_pcie_dev_t *dev, u32 options)",
    )

    enable_events = [
        ("assert PERST", "Assert the reset of endpoint" in enable_body and "gpio_set_value" in enable_body),
        ("enable vreg", "msm_pcie_vreg_init(dev)" in enable_body),
        ("enable clk", "msm_pcie_clk_init(dev)" in enable_body),
        ("init phy", "pcie_phy_init(dev)" in enable_body),
        ("enable pipe clock", "msm_pcie_pipe_clk_init(dev)" in enable_body),
        ("wait PHY ready", "pcie_phy_is_ready(dev)" in enable_body),
        ("release PERST", "Release the reset of endpoint" in enable_body),
        ("enable LTSSM", "PCIE20_PARF_LTSSM" in enable_body and "BIT(8)" in enable_body),
        ("poll link", "LTSSM_STATE" in enable_body and "LINK_UP_CHECK_MAX_COUNT" in enable_body),
        ("reassert PERST on fail", "link initialization failed" in enable_body and "Assert the reset" in enable_body),
    ]

    return {
        "pcie1_dtsi": {
            "path": rel(PCIE_DTSI),
            "present": bool(pcie_dtsi),
            "node_line_start": pcie1_start,
            "node_line_end": pcie1_end,
            "perst_gpio": first_line_in_block(pcie1_block, "perst-gpio = <&tlmm 102 0>"),
            "wake_gpio": first_line_in_block(pcie1_block, "wake-gpio = <&tlmm 104 0>"),
            "gdsc": first_line_in_block(pcie1_block, "gdsc-vdd-supply = <&pcie_1_gdsc>"),
            "vreg_1p8": first_line_in_block(pcie1_block, "vreg-1.8-supply = <&pm8150l_l3>"),
            "vreg_0p9": first_line_in_block(pcie1_block, "vreg-0.9-supply = <&pm8150_l5>"),
            "clkref": "GCC_PCIE_1_CLKREF_CLK" in pcie1_block,
            "phy_refgen": "GCC_PCIE1_PHY_REFGEN_CLK" in pcie1_block,
            "pipe_clk": "GCC_PCIE_1_PIPE_CLK" in pcie1_block,
            "boot_option": first_line_in_block(pcie1_block, "qcom,boot-option"),
            "ep_latency": first_line_in_block(pcie1_block, "qcom,ep-latency"),
            "pci_ids": first_line_in_block(pcie1_block, 'pci-ids = "17cb:0108"'),
        },
        "sdx50m": {
            "sdx50m_path": rel(SDX50M_DTSI),
            "ext_soc_path": rel(EXT_SOC_DTSI),
            "mhi_path": rel(MHI_DTSI),
            "compatible_ext_sdx50m": 'compatible = "qcom,ext-sdx50m"' in sdx50m_dtsi,
            "esoc_0_mdm3": "esoc-0 = <&mdm3>" in sdx50m_dtsi,
            "mhi_pci_ids": 'pci-ids = "17cb:0305"' in mhi_dtsi,
            "mhi_pci_ids_line": first_line_in_block(mhi_dtsi, 'pci-ids = "17cb:0305"'),
            "mhi_name_esoc0": 'mhi,name = "esoc0"' in mhi_dtsi,
            "mhi_name_line": first_line_in_block(mhi_dtsi, 'mhi,name = "esoc0"'),
            "ap2mdm_status_gpio": first_line_in_block(ext_soc_dtsi, "qcom,ap2mdm-status-gpio"),
            "mdm2ap_status_gpio": first_line_in_block(ext_soc_dtsi, "qcom,mdm2ap-status-gpio"),
            "pon_gpio": first_line_in_block(ext_soc_dtsi, "qcom,ap2mdm-soft-reset-gpio"),
            "no_regulator_supply": "regulator-supply" not in ext_soc_dtsi and "vdd-supply" not in ext_soc_dtsi,
        },
        "pci_msm_enable": {
            "path": rel(PCI_MSM_SOURCE),
            "present": bool(pci_msm),
            "line_start": enable_start,
            "line_end": enable_end,
            "events": [{"event": name, "present": present} for name, present in enable_events],
            "has_poll_compliance_symbol": "MSM_PCIE_LTSSM_POLL_COMPLIANCE" in pci_msm,
            "has_l0_symbol": "MSM_PCIE_LTSSM_L0" in pci_msm,
            "key_lines": source_lines(
                pci_msm,
                (
                    "static int msm_pcie_enable",
                    "Assert the reset of endpoint",
                    "msm_pcie_vreg_init(dev)",
                    "msm_pcie_clk_init(dev)",
                    "pcie_phy_init(dev)",
                    "msm_pcie_pipe_clk_init(dev)",
                    "PCIe RC%d PHY is ready",
                    "Release the reset of endpoint",
                    "PCIE20_PARF_LTSSM",
                    "LTSSM_STATE",
                    "link initialization failed",
                ),
            ),
        },
    }


def analyze_evidence() -> dict[str, Any]:
    v1539 = read_json(V1539_MANIFEST)
    v1538_dmesg = read_text(V1538_DMESG)
    v1538_window = read_text(V1538_WINDOW)
    v852_dmesg = read_text(V852_DMESG)
    v852_interrupts = read_text(V852_INTERRUPTS)
    gpio102 = gpio_level_values(v1538_window, 102)
    gpio103 = gpio_level_values(v1538_window, 103)
    gpio104 = gpio_level_values(v1538_window, 104)
    gpio135 = gpio_level_values(v1538_window, 135)
    gpio142 = gpio_level_values(v1538_window, 142)
    irq104 = irq_totals(v1538_window, 104)
    irq142 = irq_totals(v1538_window, 142)
    gdsc_rows = pcie1_gdsc_rows(v1538_window)

    return {
        "v1539": {
            "path": rel(V1539_MANIFEST),
            "decision": v1539.get("decision"),
            "pass": bool(v1539.get("pass")),
            "ap_side_closed": bool(
                (v1539.get("classification") or {}).get("ap_side_caller_semantics_empirically_closed")
            ),
            "active_blocker": (v1539.get("classification") or {}).get("active_blocker"),
        },
        "native_v1538": {
            "dmesg_path": rel(V1538_DMESG),
            "window_path": rel(V1538_WINDOW),
            "esoc0_ts": first_ts(v1538_dmesg, r"__subsystem_get.*esoc0 count:0"),
            "rc1_assert_ts": first_ts(v1538_dmesg, r"Assert the reset of endpoint of RC1"),
            "rc1_phy_ready_ts": first_ts(v1538_dmesg, r"PCIe RC1 PHY is ready"),
            "rc1_release_ts": first_ts(v1538_dmesg, r"Release the reset of endpoint of RC1"),
            "poll_compliance_ts": first_ts(v1538_dmesg, r"LTSSM_POLL_COMPLIANCE"),
            "link_failed_ts": first_ts(v1538_dmesg, r"link initialization failed"),
            "has_l0": bool(re.search(r"LTSSM_STATE:\s+LTSSM_L0|Current GEN", v1538_dmesg)),
            "has_mhi_wlfw_wlan0": bool(re.search(r"mhi_0305|/dev/mhi|wlfw|BDF|FW ready|wlan0", v1538_dmesg, re.I)),
            "gpio102_samples_max": max(gpio102) if gpio102 else None,
            "gpio103_samples_max": max(gpio103) if gpio103 else None,
            "gpio104_samples_max": max(gpio104) if gpio104 else None,
            "gpio135_samples_max": max(gpio135) if gpio135 else None,
            "gpio142_samples_max": max(gpio142) if gpio142 else None,
            "gpio104_irq_max": max(irq104) if irq104 else None,
            "gpio142_irq_max": max(irq142) if irq142 else None,
            "pcie1_gdsc_samples": len(gdsc_rows),
            "pcie1_gdsc_nonzero": any(" 0mV " not in f" {row} " for row in gdsc_rows),
            "key_dmesg_lines": matching_lines(
                v1538_dmesg,
                r"__subsystem_get.*esoc0|Assert the reset of endpoint of RC1|PHY is ready|Release the reset of endpoint of RC1|LTSSM_STATE|link initialization failed|failed to enable RC1",
                32,
            ),
            "key_window_lines": matching_lines(
                v1538_window,
                r"rc1_micro_writer_summary|gpio102\s*:|gpio103\s*:|gpio104\s*:|gpio135\s*:|gpio142\s*:|msmgpio-dc\s+104|msmgpio-dc\s+142|pcie_1_gdsc",
                28,
            ),
        },
        "android_v852": {
            "dmesg_path": rel(V852_DMESG),
            "interrupts_path": rel(V852_INTERRUPTS),
            "esoc0_ts": first_ts(v852_dmesg, r"__subsystem_get.*esoc0 count:0"),
            "rc1_assert_ts": first_ts(v852_dmesg, r"Assert the reset of endpoint of RC1"),
            "rc1_release_ts": first_ts(v852_dmesg, r"Release the reset of endpoint of RC1"),
            "rc1_l0_ts": first_ts(v852_dmesg, r"LTSSM_STATE:\s+LTSSM_L0"),
            "current_gen_ts": first_ts(v852_dmesg, r"Current GEN"),
            "wlfw_start_ts": first_ts(v852_dmesg, r"wlfw_start"),
            "bdf_ts": first_ts(v852_dmesg, r"BDF file"),
            "wlan0_ts": first_ts(v852_dmesg, r"dev : wlan0"),
            "gpio104_irq_total": max(irq_totals(v852_interrupts, 104) or [0]),
            "gpio142_irq_total": max(irq_totals(v852_interrupts, 142) or [0]),
            "key_lines": matching_lines(
                v852_dmesg,
                r"__subsystem_get.*esoc0|Assert the reset of endpoint of RC1|Release the reset of endpoint of RC1|LTSSM_STATE|Current GEN|wlfw_start|BDF file|dev : wlan0",
                28,
            ),
        },
    }


def candidate_rows(result: dict[str, Any]) -> list[dict[str, str]]:
    evidence = result["evidence"]
    native = evidence["native_v1538"]
    rows = [
        {
            "candidate": "AP-side enumerate caller",
            "status": "closed",
            "basis": "V1538 sysfs/client enumerate write succeeded and still failed before L0.",
        },
        {
            "candidate": "RC1 software enable path",
            "status": "partially healthy",
            "basis": "V1538 reaches PERST assert/release, PHY ready, and LTSSM polling/compliance.",
        },
        {
            "candidate": "SDX50M endpoint response",
            "status": "active blocker",
            "basis": "No L0, no GPIO142 IRQ/level, no MHI/WLFW/BDF/wlan0 after RC1 link training starts.",
        },
        {
            "candidate": "PERST/refclk/GDSC/electrical parity",
            "status": "next focus",
            "basis": "DTS ties RC1 to GPIO102 PERST, GPIO104 WAKE, pcie_1_gdsc, clkref/refgen; V1538 samples keep pcie1 GDSC at 0mV and GPIO102/135/142 low.",
        },
        {
            "candidate": "firmware/MHI/WLFW",
            "status": "deferred",
            "basis": "No native L0 or PCI device exists, so these remain downstream.",
        },
        {
            "candidate": "Wi-Fi HAL / scan / connect",
            "status": "blocked downstream",
            "basis": "wlan0 is absent; credentials, DHCP/routes, and external ping remain out of scope.",
        },
    ]
    if native["pcie1_gdsc_nonzero"]:
        rows[3]["status"] = "needs-review"
        rows[3]["basis"] = "V1538 shows nonzero pcie1 GDSC in at least one sample; re-check timing before prioritizing GDSC."
    return rows


def classify() -> dict[str, Any]:
    sources = analyze_sources()
    evidence = analyze_evidence()
    native = evidence["native_v1538"]
    android = evidence["android_v852"]
    source_events = sources["pci_msm_enable"]["events"]
    checks = {
        "v1539-fixed-point-pass": evidence["v1539"]["pass"]
        and evidence["v1539"]["decision"] == "v1539-sysfs-client-enumerate-closes-ap-side-trigger-no-l0",
        "pcie1-dts-contract-present": bool(sources["pcie1_dtsi"]["perst_gpio"])
        and bool(sources["pcie1_dtsi"]["wake_gpio"])
        and bool(sources["pcie1_dtsi"]["gdsc"])
        and sources["pcie1_dtsi"]["clkref"]
        and sources["pcie1_dtsi"]["phy_refgen"],
        "sdx50m-esoc-mhi-contract-present": sources["sdx50m"]["compatible_ext_sdx50m"]
        and sources["sdx50m"]["esoc_0_mdm3"]
        and sources["sdx50m"]["mhi_pci_ids"]
        and sources["sdx50m"]["mhi_name_esoc0"]
        and "135" in sources["sdx50m"]["ap2mdm_status_gpio"]
        and "142" in sources["sdx50m"]["mdm2ap_status_gpio"],
        "pci-msm-enable-sequence-present": all(event["present"] for event in source_events),
        "native-v1538-rc1-reaches-link-training": native["rc1_assert_ts"] is not None
        and native["rc1_phy_ready_ts"] is not None
        and native["rc1_release_ts"] is not None
        and native["poll_compliance_ts"] is not None,
        "native-v1538-fails-before-l0": native["link_failed_ts"] is not None
        and not native["has_l0"],
        "native-v1538-no-endpoint-response": native["gpio142_irq_max"] == 0
        and native["gpio142_samples_max"] == 0
        and not native["has_mhi_wlfw_wlan0"],
        "android-good-has-l0-and-downstream": android["rc1_l0_ts"] is not None
        and android["current_gen_ts"] is not None
        and android["wlfw_start_ts"] is not None
        and android["bdf_ts"] is not None
        and android["wlan0_ts"] is not None,
    }
    pass_ok = all(checks.values())
    result: dict[str, Any] = {
        "cycle": "V1540",
        "generated_at": now_iso(),
        "decision": (
            "v1540-endpoint-readiness-gap-after-sysfs-enumerate"
            if pass_ok
            else "v1540-endpoint-readiness-model-needs-review"
        ),
        "pass": pass_ok,
        "reason": (
            "sysfs/client enumerate and RC1 software enable are proven, but the SDX50M endpoint still does not respond before L0; next focus is endpoint electrical/readiness parity"
            if pass_ok
            else "one or more endpoint-readiness fixed points did not match the expected no-L0 model"
        ),
        "inputs": {
            "v1539_manifest": rel(V1539_MANIFEST),
            "v1538_dmesg": rel(V1538_DMESG),
            "v1538_window": rel(V1538_WINDOW),
            "android_v852_dmesg": rel(V852_DMESG),
            "android_v852_interrupts": rel(V852_INTERRUPTS),
            "pcie_dtsi": rel(PCIE_DTSI),
            "sdx50m_dtsi": rel(SDX50M_DTSI),
            "external_soc_dtsi": rel(EXT_SOC_DTSI),
            "mhi_dtsi": rel(MHI_DTSI),
            "pci_msm_source": rel(PCI_MSM_SOURCE),
        },
        "host": collect_host_metadata(),
        "checks": checks,
        "sources": sources,
        "evidence": evidence,
        "candidates": candidate_rows({"evidence": evidence}),
        "classification": {
            "active_blocker": "SDX50M endpoint readiness/electrical/reset/refclk/PERST response before native RC1 L0",
            "closed_branches": [
                "AP-side sysfs/client enumerate caller semantics",
                "debugfs TEST:11 caller semantics",
                "MHI PM-resume as first-L0 trigger",
                "ICNSS workqueue as first-L0 trigger",
                "firmware/WLFW/BDF before native L0",
            ],
            "native_fixed_failure": "PERST assert/release + PHY ready + LTSSM poll/compliance, then link initialization failed without L0",
            "highest_value_next_observables": [
                "GPIO102 PERST effective level around RC1 release",
                "pcie_1_gdsc and pcie_1_* clocks/refclk/refgen in the sub-120ms link window",
                "GPIO103 CLKREQ and GPIO104 WAKE effective/IRQ state",
                "GPIO135 AP2MDM and GPIO142 MDM2AP effective/IRQ state",
                "Android-good matched endpoint electrical/reference timeline if a sufficiently early hook is available",
            ],
            "firmware_mhi_wlfw_scan_connect_deferred_until_native_l0": True,
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
            "esoc_notify_boot_done_spoof_executed": False,
            "global_pci_rescan_executed": False,
            "platform_bind_unbind_executed": False,
            "boot_or_partition_write_executed": False,
        },
        "next_gate": {
            "cycle": "V1541",
            "summary": "source/build-only endpoint electrical observer design: sample PERST/refclk/GDSC/CLKREQ/WAKE/AP2MDM/MDM2AP in the exact RC1 link-training window without new writes",
            "guardrails": [
                "do not repeat enumerate until a new endpoint input is identified",
                "no PMIC/GPIO/GDSC direct write",
                "no global PCI rescan or platform bind/unbind",
                "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
                "no firmware/MHI/WLFW branch until native L0 and PCI enumeration exist",
            ],
        },
    }
    return result


def render_report(result: dict[str, Any]) -> str:
    src = result["sources"]
    evidence = result["evidence"]
    native = evidence["native_v1538"]
    android = evidence["android_v852"]
    return "\n".join(
        [
            "# Native Init V1540 Endpoint Readiness Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1540`",
            "- Type: host-only evidence/source classifier",
            f"- Decision: `{result['decision']}`",
            f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
            f"- Reason: {result['reason']}",
            "",
            "## Inputs",
            "",
            markdown_table(["input", "path"], [[name, path] for name, path in result["inputs"].items()]),
            "",
            "## Fixed-Point Checks",
            "",
            markdown_table(["check", "value"], [[name, value] for name, value in result["checks"].items()]),
            "",
            "## Endpoint Candidate Classification",
            "",
            markdown_table(
                ["candidate", "status", "basis"],
                [[row["candidate"], row["status"], row["basis"]] for row in result["candidates"]],
            ),
            "",
            "## RC1 / SDX50M Source Contract",
            "",
            markdown_table(
                ["fact", "value"],
                [
                    ["pcie1 node lines", f"{src['pcie1_dtsi']['node_line_start']}-{src['pcie1_dtsi']['node_line_end']}"],
                    ["PERST", src["pcie1_dtsi"]["perst_gpio"]],
                    ["WAKE", src["pcie1_dtsi"]["wake_gpio"]],
                    ["GDSC", src["pcie1_dtsi"]["gdsc"]],
                    ["vreg 1.8 / 0.9", f"{src['pcie1_dtsi']['vreg_1p8']} / {src['pcie1_dtsi']['vreg_0p9']}"],
                    ["clkref/refgen/pipe", f"{src['pcie1_dtsi']['clkref']}/{src['pcie1_dtsi']['phy_refgen']}/{src['pcie1_dtsi']['pipe_clk']}"],
                    ["boot option / ep latency", f"{src['pcie1_dtsi']['boot_option']} / {src['pcie1_dtsi']['ep_latency']}"],
                    ["MHI endpoint", f"{src['sdx50m']['mhi_pci_ids_line']} / {src['sdx50m']['mhi_name_line']}"],
                    ["AP2MDM / MDM2AP / PON", f"{src['sdx50m']['ap2mdm_status_gpio']} / {src['sdx50m']['mdm2ap_status_gpio']} / {src['sdx50m']['pon_gpio']}"],
                ],
            ),
            "",
            "## pci-msm Enable Order",
            "",
            markdown_table(
                ["event", "present"],
                [[row["event"], row["present"]] for row in src["pci_msm_enable"]["events"]],
            ),
            "",
            "## Android-Good vs Native-Fail",
            "",
            markdown_table(
                ["field", "Android V852", "Native V1538"],
                [
                    ["esoc0 timestamp", android["esoc0_ts"], native["esoc0_ts"]],
                    ["RC1 assert", android["rc1_assert_ts"], native["rc1_assert_ts"]],
                    ["RC1 release", android["rc1_release_ts"], native["rc1_release_ts"]],
                    ["RC1 L0", android["rc1_l0_ts"], native["has_l0"]],
                    ["Current GEN", android["current_gen_ts"], ""],
                    ["poll compliance", "", native["poll_compliance_ts"]],
                    ["link failed", "", native["link_failed_ts"]],
                    ["GPIO142 IRQ total/max", android["gpio142_irq_total"], native["gpio142_irq_max"]],
                    ["MHI/WLFW/BDF/wlan0", f"{android['wlfw_start_ts']}/{android['bdf_ts']}/{android['wlan0_ts']}", native["has_mhi_wlfw_wlan0"]],
                ],
            ),
            "",
            "## Native V1538 Window Signals",
            "",
            markdown_table(
                ["signal", "value"],
                [
                    ["GPIO102/PERST sample max", native["gpio102_samples_max"]],
                    ["GPIO103/CLKREQ sample max", native["gpio103_samples_max"]],
                    ["GPIO104/WAKE sample max", native["gpio104_samples_max"]],
                    ["GPIO104 IRQ max", native["gpio104_irq_max"]],
                    ["GPIO135/AP2MDM sample max", native["gpio135_samples_max"]],
                    ["GPIO142/MDM2AP sample max", native["gpio142_samples_max"]],
                    ["GPIO142 IRQ max", native["gpio142_irq_max"]],
                    ["pcie1 GDSC samples/nonzero", f"{native['pcie1_gdsc_samples']}/{native['pcie1_gdsc_nonzero']}"],
                ],
            ),
            "",
            "## Key Native V1538 Dmesg Lines",
            "",
            "\n".join(f"- `{line}`" for line in native["key_dmesg_lines"]),
            "",
            "## Key Native V1538 Window Lines",
            "",
            "\n".join(f"- `{line}`" for line in native["key_window_lines"]),
            "",
            "## Key pci-msm Source Lines",
            "",
            markdown_table(
                ["line", "text"],
                [[row["line"], row["text"]] for row in src["pci_msm_enable"]["key_lines"]],
            ),
            "",
            "## Interpretation",
            "",
            "V1540 fixes the active blocker below AP-side caller semantics. The kernel source shows `msm_pcie_enable()` asserts PERST, enables vregs/clocks/PHY/pipe clock, waits for PHY ready, releases PERST, enables LTSSM, then polls for link-up. V1538 reaches that sequence and fails at LTSSM poll/compliance without L0.",
            "",
            "The next useful work is not another enumerate retry and not firmware/MHI/WLFW. The evidence now points at the endpoint readiness/electrical boundary: PERST/refclk/GDSC/CLKREQ/WAKE/AP2MDM/MDM2AP around the first RC1 link-training window. Until native L0 and PCI enumeration exist, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, firmware transfer, and MHI pipe work remain downstream.",
            "",
            "## Next Gate",
            "",
            f"- Cycle: `{result['next_gate']['cycle']}`",
            f"- Summary: {result['next_gate']['summary']}",
            *(f"- Guardrail: {item}" for item in result["next_gate"]["guardrails"]),
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.",
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
                "pass": result["pass"],
                "out_dir": rel(args.out_dir),
                "next_gate": result["next_gate"]["cycle"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
