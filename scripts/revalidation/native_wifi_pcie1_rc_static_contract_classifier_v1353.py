#!/usr/bin/env python3
"""V1353 host-only pcie1 RC static contract classifier.

This classifier implements the 2026-06-01 eSoC-provider pivot:

* do not continue upper eSoC / ESOC_REQ_IMG / ks / MHI / CNSS-WLFW probing;
* classify the static PCIe RC1 contract for SDX50M first;
* produce the read-only surface list for the next live observer.

It reads only repository files. It does not contact the device, bridge, NCM, or
any live runtime surface.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1353-pcie1-rc-static-contract-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1353-pcie1-rc-static-contract-classifier.txt")
SOURCE_ROOT = workspace_private_input_path(
    "kernel_source", "SM-A908N_KOR_12_Opensource", "Kernel"
)

PATHS = {
    "pcie_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi",
    "mhi_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-mhi.dtsi",
    "sdx50m_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi",
    "external_soc_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi",
    "pinctrl_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-pinctrl.dtsi",
    "gdsc_dtsi": SOURCE_ROOT / "arch/arm64/boot/dts/qcom/sm8150-gdsc.dtsi",
    "r3q_overlay": SOURCE_ROOT
    / "arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r03.dts",
    "esoc_static_report": Path("docs/reports/ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md"),
    "v1306_report": Path("docs/reports/NATIVE_INIT_V1306_EXT_MDM_PMIC_GDSC_BRANCH_CLASSIFIER_2026-05-31.md"),
    "v1328_report": Path("docs/reports/NATIVE_INIT_V1328_MDM2AP_TIMING_SAMPLER_LIVE_2026-05-31.md"),
    "v1345_report": Path("docs/reports/NATIVE_INIT_V1345_CURRENT_ROUTE_MDM2AP_TIMING_SAMPLER_LIVE_2026-06-01.md"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def first_line(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    return ""


def contains_all(text: str, needles: tuple[str, ...]) -> bool:
    return all(needle in text for needle in needles)


def source_line(path: Path, needle: str) -> str:
    text = read_text(path)
    for line_number, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return f"{path}:{line_number}: {line.strip()}"
    return f"{path}: missing {needle!r}"


def build_contract(inputs: dict[str, str]) -> dict[str, Any]:
    pcie = inputs["pcie_dtsi"]
    mhi = inputs["mhi_dtsi"]
    sdx50m = inputs["sdx50m_dtsi"]
    external_soc = inputs["external_soc_dtsi"]
    pinctrl = inputs["pinctrl_dtsi"]
    gdsc = inputs["gdsc_dtsi"]
    overlay = inputs["r3q_overlay"]

    return {
        "pcie1_node": {
            "dt_node": first_line(pcie, "pcie1: qcom,pcie@1c08000"),
            "compatible": first_line(pcie, 'compatible = "qcom,pci-msm"'),
            "cell_index": first_line(pcie, "cell-index = <1>"),
            "linux_pci_domain": first_line(pcie, "linux,pci-domain = <1>"),
            "rc_child": first_line(pcie, "pcie_rc1: pcie_rc1"),
            "rc_pci_ids": first_line(pcie, 'pci-ids = "17cb:0108"'),
        },
        "pcie1_power": {
            "gdsc": first_line(pcie, "gdsc-vdd-supply = <&pcie_1_gdsc>"),
            "gdsc_definition": first_line(gdsc, "pcie_1_gdsc: qcom,gdsc@0x18d004"),
            "gdsc_regulator_name": first_line(gdsc, 'regulator-name = "pcie_1_gdsc"'),
            "vreg_1p8": first_line(pcie, "vreg-1.8-supply = <&pm8150l_l3>"),
            "vreg_0p9": first_line(pcie, "vreg-0.9-supply = <&pm8150_l5>"),
            "vreg_cx": first_line(pcie, "vreg-cx-supply = <&VDD_CX_LEVEL>"),
        },
        "pcie1_reset_gpio": {
            "perst_gpio": first_line(pcie, "perst-gpio = <&tlmm 102 0>"),
            "wake_gpio": first_line(pcie, "wake-gpio = <&tlmm 104 0>"),
            "clkreq_pinctrl": first_line(pinctrl, "pcie1_clkreq_default:"),
            "clkreq_pin": source_line(PATHS["pinctrl_dtsi"], 'pins = "gpio103"'),
            "perst_pinctrl": first_line(pinctrl, "pcie1_perst_default:"),
            "perst_pin": source_line(PATHS["pinctrl_dtsi"], 'pins = "gpio102"'),
            "sdx50m_wake_override": first_line(sdx50m, "pcie1_sdx50m_wake_default:"),
            "wake_override_pin": source_line(PATHS["sdx50m_dtsi"], 'pins = "gpio104"'),
        },
        "pcie1_clocks": {
            "clock_names": [
                "pcie_1_pipe_clk",
                "pcie_1_ref_clk_src",
                "pcie_1_aux_clk",
                "pcie_1_cfg_ahb_clk",
                "pcie_1_mstr_axi_clk",
                "pcie_1_slv_axi_clk",
                "pcie_1_ldo",
                "pcie_1_slv_q2a_axi_clk",
                "pcie_tbu_clk",
                "pcie_phy_refgen_clk",
                "pcie_phy_aux_clk",
            ],
            "clock_refs": [
                "GCC_PCIE_1_PIPE_CLK",
                "RPMH_CXO_CLK",
                "GCC_PCIE_1_AUX_CLK",
                "GCC_PCIE_1_CFG_AHB_CLK",
                "GCC_PCIE_1_MSTR_AXI_CLK",
                "GCC_PCIE_1_SLV_AXI_CLK",
                "GCC_PCIE_1_CLKREF_CLK",
                "GCC_PCIE_1_SLV_Q2A_AXI_CLK",
                "GCC_AGGRE_NOC_PCIE_TBU_CLK",
                "GCC_PCIE1_PHY_REFGEN_CLK",
                "GCC_PCIE_PHY_AUX_CLK",
            ],
            "resets": ["GCC_PCIE_1_BCR", "GCC_PCIE_1_PHY_BCR"],
        },
        "mhi_endpoint": {
            "mhi_node": first_line(mhi, "mhi_0: qcom,mhi@0"),
            "pci_ids": first_line(mhi, 'pci-ids = "17cb:0305"'),
            "mhi_name": first_line(mhi, 'mhi,name = "esoc0"'),
            "sdx50m_esoc_names": first_line(sdx50m, 'esoc-names = "mdm"'),
            "sdx50m_esoc_0": first_line(sdx50m, "esoc-0 = <&mdm3>"),
            "sdx50m_addr_window": first_line(sdx50m, "qcom,addr-win ="),
        },
        "mdm3_esoc_provider": {
            "mdm3_node": first_line(external_soc, "mdm3: qcom,mdm3"),
            "compatible": first_line(sdx50m, 'compatible = "qcom,ext-sdx50m"'),
            "link_info": first_line(sdx50m, 'qcom,mdm-link-info = "0305_01.01.00"'),
            "mdm2ap_status_gpio": first_line(external_soc, "qcom,mdm2ap-status-gpio"),
            "ap2mdm_status_gpio": first_line(external_soc, "qcom,ap2mdm-status-gpio"),
            "pon_gpio": first_line(external_soc, "qcom,ap2mdm-soft-reset-gpio"),
            "no_regulator_supply": "regulator-supply" not in external_soc
            and "vdd-supply" not in external_soc,
        },
        "r3q_overlay": {
            "mdm3_ext_sdx50m": first_line(overlay, 'compatible = "qcom,ext-sdx50m"'),
            "mdm_link_info": first_line(overlay, 'qcom,mdm-link-info = "0305_01.01.00"'),
            "mhi_fw_name": first_line(overlay, 'mhi,fw-name = "debug.mbn"'),
            "mhi_esoc_0": first_line(overlay, "esoc-0 = <0x3b>"),
            "pcie1_overlay_bus_name": first_line(overlay, 'qcom,msm-bus,name = "pcie1"'),
            "pcie1_sdx50m_wake": first_line(overlay, "pcie1_sdx50m_wake_default"),
        },
    }


def build_live_readonly_contract() -> list[dict[str, str]]:
    return [
        {
            "surface": "pcie1 platform node",
            "paths": "/sys/devices/platform/soc/1c08000.qcom,pcie, /sys/bus/platform/devices/1c08000.qcom,pcie",
            "read": "current_link_state, link_state, power/runtime_status, power/control, uevent, modalias, resource, irq",
        },
        {
            "surface": "pcie1 GDSC/regulators",
            "paths": "/sys/kernel/debug/regulator/regulator_summary, /sys/kernel/debug/regulator_summary",
            "read": "pcie_1_gdsc, pcie_0_gdsc, pm8150l_l3, pm8150_l5, VDD_CX_LEVEL lines only",
        },
        {
            "surface": "pcie1 clocks/refclk",
            "paths": "/sys/kernel/debug/clk/clk_summary",
            "read": "GCC_PCIE_1_*, GCC_PCIE1_PHY_REFGEN_CLK, RPMH_CXO_CLK, pcie_phy_aux_clk lines only",
        },
        {
            "surface": "pcie1 pinctrl/PERST/CLKREQ/WAKE",
            "paths": "/sys/kernel/debug/pinctrl/*/{pins,pinmux-pins,pinconf-pins,gpio-ranges}",
            "read": "GPIO102/PERST, GPIO103/CLKREQ, GPIO104/WAKE; include GPIO135/GPIO142 and PM8150L GPIO9 for correlation",
        },
        {
            "surface": "PCI/MHI enumeration",
            "paths": "/sys/bus/pci/devices, /sys/bus/mhi/devices, /dev",
            "read": "PCI device count, MHI device count, /dev/mhi* existence; no bind/unbind/rescan writes",
        },
        {
            "surface": "interrupts and dmesg",
            "paths": "/proc/interrupts, dmesg/klog read",
            "read": "GPIO142/MDM2AP, errfatal, pcie1/msm_pcie/LTSSM/MHI markers with timestamps",
        },
    ]


def build_checks(inputs: dict[str, str], contract: dict[str, Any]) -> list[dict[str, str]]:
    esoc_report = inputs["esoc_static_report"]
    v1306 = inputs["v1306_report"]
    v1328 = inputs["v1328_report"]
    v1345 = inputs["v1345_report"]

    return [
        {
            "name": "pcie1-node-contract-present",
            "result": "pass"
            if contains_all(
                inputs["pcie_dtsi"],
                (
                    "pcie1: qcom,pcie@1c08000",
                    "gdsc-vdd-supply = <&pcie_1_gdsc>",
                    "GCC_PCIE_1_CLKREF_CLK",
                    "GCC_PCIE1_PHY_REFGEN_CLK",
                    "perst-gpio = <&tlmm 102 0>",
                ),
            )
            else "fail",
            "detail": "pcie1 DTS contains RC node, GDSC, refclk, refgen, and PERST GPIO",
        },
        {
            "name": "sdx50m-mhi-esoc-link-present",
            "result": "pass"
            if contains_all(
                inputs["sdx50m_dtsi"],
                ('esoc-0 = <&mdm3>', 'qcom,addr-win = <0x0 0xa0000000 0x0 0xa4bfffff>')
            )
            and contains_all(inputs["mhi_dtsi"], ('pci-ids = "17cb:0305"', 'mhi,name = "esoc0"'))
            else "fail",
            "detail": "mhi_0 is tied to mdm3/esoc0 and SDX50M PCI IDs",
        },
        {
            "name": "provider-does-not-power-pcie",
            "result": "pass"
            if (
                "Zero** PCIe/MHI/GDSC/regulator" in esoc_report
                and "provider does NOT power `pcie1`" in esoc_report
            )
            else "fail",
            "detail": "2026-06-01 static analysis redirects next gate below provider to pcie1/PON",
        },
        {
            "name": "native-prior-gdsc-zero-evidence",
            "result": "pass"
            if "pcie_1_gdsc" in v1306 and "0mV" in v1306 else "fail",
            "detail": "V1306 observed pcie1 GDSC at 0mV in native lower window",
        },
        {
            "name": "native-prior-full-window-no-transition",
            "result": "pass"
            if "timing_gpio142_irq_delta | `0`" in v1328
            and "timing_pcie_rc1_transition_seen | `false`" in v1328
            and "timing_pcie_rc1_transition_seen | False" in v1345
            else "fail",
            "detail": "V1328/V1345 show no GPIO142 or pcie1 transition during bounded lower windows",
        },
        {
            "name": "hard-exclusions-preserved",
            "result": "pass",
            "detail": "host-only classifier; no device command, writes, Wi-Fi HAL, scan/connect, DHCP/routes, external ping, or flash",
        },
    ]


def render_table(headers: list[str], rows: list[list[Any]]) -> str:
    rendered = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        rendered.append("| " + " | ".join(str(value).replace("\n", " ") for value in row) + " |")
    return "\n".join(rendered)


def write_summary(out_dir: Path, manifest: dict[str, Any]) -> None:
    contract = manifest["contract"]
    live_surfaces = manifest["live_readonly_contract"]
    rows = [
        ["pcie1 node", contract["pcie1_node"]["dt_node"], "RC1 platform node"],
        ["GDSC", contract["pcie1_power"]["gdsc"], contract["pcie1_power"]["gdsc_definition"]],
        ["PERST", contract["pcie1_reset_gpio"]["perst_gpio"], "TLMM102"],
        ["CLKREQ", contract["pcie1_reset_gpio"]["clkreq_pin"], "TLMM103"],
        ["WAKE", contract["pcie1_reset_gpio"]["wake_gpio"], "TLMM104; SDX50M override disables bias"],
        ["clocks", ", ".join(contract["pcie1_clocks"]["clock_names"]), "includes clkref/refgen"],
        ["MHI", contract["mhi_endpoint"]["sdx50m_esoc_0"], contract["mhi_endpoint"]["pci_ids"]],
        ["provider", contract["mdm3_esoc_provider"]["compatible"], "GPIO/ioctl only; no pcie power"],
    ]
    checks = [[check["name"], check["result"], check["detail"]] for check in manifest["checks"]]
    surfaces = [[item["surface"], item["paths"], item["read"]] for item in live_surfaces]
    summary = f"""# V1353 pcie1 RC Static Contract Classifier

- Cycle: `V1353`
- Type: host-only classifier
- Decision: `{manifest["decision"]}`
- Result: `{"PASS" if manifest["pass"] else "FAIL"}`
- Evidence: `{out_dir / "manifest.json"}`

## Contract Table

{render_table(["surface", "source", "meaning"], rows)}

## Checks

{render_table(["check", "result", "detail"], checks)}

## V1354 Read-only Surface Contract

{render_table(["surface", "paths", "read-only fields"], surfaces)}

## Next

Run V1354 only after this static contract is accepted. V1354 should observe the
listed read-only pcie1/GDSC/clock/PERST/refclk surfaces before and during the
existing bounded current-route lower window, without any sysfs/debugfs writes or
new PCIe/eSoC mutation.
"""
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    missing = [str(path) for path in PATHS.values() if not path.exists()]
    if missing:
        manifest = {
            "cycle": "V1353",
            "decision": "v1353-inputs-missing",
            "pass": False,
            "created_at": now_iso(),
            "missing": missing,
        }
        (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 1

    inputs = {name: read_text(path) for name, path in PATHS.items()}
    contract = build_contract(inputs)
    checks = build_checks(inputs, contract)
    passed = all(check["result"] == "pass" for check in checks)
    manifest: dict[str, Any] = {
        "cycle": "V1353",
        "type": "host-only classifier",
        "decision": "v1353-pcie1-rc-static-contract-ready" if passed else "v1353-pcie1-rc-static-contract-incomplete",
        "pass": passed,
        "created_at": now_iso(),
        "inputs": {name: str(path) for name, path in PATHS.items()},
        "contract": contract,
        "live_readonly_contract": build_live_readonly_contract(),
        "checks": checks,
        "hard_exclusions": [
            "no device command",
            "no bridge or NCM use",
            "no sysfs/debugfs write",
            "no PMIC/GPIO/GDSC write",
            "no eSoC notify or BOOT_DONE",
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no flash, boot image write, or partition write",
        ],
        "next_step": "V1354 pcie1 RC live read-only power observer",
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_summary(args.out_dir, manifest)
    LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
    LATEST_POINTER.write_text(str(args.out_dir) + "\n", encoding="utf-8")
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(args.out_dir)}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
