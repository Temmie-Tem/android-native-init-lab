# Native Init V1353 pcie1 RC Static Contract Classifier

## Summary

- Cycle: `V1353`
- Type: host-only classifier
- Decision: `v1353-pcie1-rc-static-contract-ready`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_pcie1_rc_static_contract_classifier_v1353.py`
- Evidence:
  - `tmp/wifi/v1353-pcie1-rc-static-contract-classifier/manifest.json`
  - `tmp/wifi/v1353-pcie1-rc-static-contract-classifier/summary.md`

V1353 implements the 2026-06-01 eSoC-provider pivot as a static classifier.
It does not contact the device. It reads the OSRC DTS sources plus existing
reports and turns the pcie1 RC requirement into a concrete read-only contract
for the next live observer.

## Inputs

| Input | Path |
| --- | --- |
| eSoC provider pivot | `docs/reports/ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md` |
| pcie1 DTS | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi` |
| MHI DTS | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-mhi.dtsi` |
| SDX50M DTS | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi` |
| external eSoC DTS | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sdx5xm-external-soc.dtsi` |
| pinctrl DTS | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pinctrl.dtsi` |
| GDSC DTS | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-gdsc.dtsi` |
| r3q overlay | `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r03.dts` |
| native GDSC evidence | `docs/reports/NATIVE_INIT_V1306_EXT_MDM_PMIC_GDSC_BRANCH_CLASSIFIER_2026-05-31.md` |
| no-transition evidence | `docs/reports/NATIVE_INIT_V1328_MDM2AP_TIMING_SAMPLER_LIVE_2026-05-31.md`, `docs/reports/NATIVE_INIT_V1345_CURRENT_ROUTE_MDM2AP_TIMING_SAMPLER_LIVE_2026-06-01.md` |

## Static Contract

| Surface | Contract |
| --- | --- |
| RC node | `pcie1: qcom,pcie@1c08000`, `compatible = "qcom,pci-msm"`, `cell-index = <1>`, `linux,pci-domain = <1>` |
| GDSC | `gdsc-vdd-supply = <&pcie_1_gdsc>`; GDSC definition is `qcom,gdsc@0x18d004`, regulator name `pcie_1_gdsc` |
| Supplies | `vreg-1.8-supply = <&pm8150l_l3>`, `vreg-0.9-supply = <&pm8150_l5>`, `vreg-cx-supply = <&VDD_CX_LEVEL>` |
| PERST | `perst-gpio = <&tlmm 102 0>`; pinctrl `pcie1_perst_default`, GPIO102, function `gpio`, bias-pull-down |
| CLKREQ | pinctrl `pcie1_clkreq_default`, GPIO103, function `pci_e1`, bias-pull-up |
| WAKE | `wake-gpio = <&tlmm 104 0>`; SDX50M override uses `pcie1_sdx50m_wake_default`, GPIO104, bias-disable |
| Clock inputs | `pcie_1_pipe_clk`, `pcie_1_ref_clk_src`, `pcie_1_aux_clk`, `pcie_1_cfg_ahb_clk`, `pcie_1_mstr_axi_clk`, `pcie_1_slv_axi_clk`, `pcie_1_ldo`, `pcie_1_slv_q2a_axi_clk`, `pcie_tbu_clk`, `pcie_phy_refgen_clk`, `pcie_phy_aux_clk` |
| Reset controls | `GCC_PCIE_1_BCR`, `GCC_PCIE_1_PHY_BCR` |
| MHI endpoint | `mhi_0: qcom,mhi@0`, PCI IDs `17cb:0305`, `17cb:0306`, `17cb:0307`, `17cb:0308`, `mhi,name = "esoc0"` |
| SDX50M binding | `esoc-0 = <&mdm3>`, `qcom,addr-win = <0x0 0xa0000000 0x0 0xa4bfffff>`, `mhi,use-bb`, `mhi,allow-m1` |
| eSoC provider | `mdm3 = qcom,ext-sdx50m`; AP2MDM = TLMM135, MDM2AP = TLMM142, PON = PM8150L GPIO9; no mdm3 regulator supply |

## Classification

| Check | Result | Meaning |
| --- | --- | --- |
| pcie1 RC node contract | pass | DTS contains RC1 node, GDSC, refclk/refgen clocks, and PERST GPIO |
| SDX50M MHI/eSoC link | pass | `mhi_0` is tied to `mdm3/esoc0` and SDX50M PCI IDs |
| provider does not power pcie1 | pass | 2026-06-01 host analysis proves the eSoC provider is GPIO/ioctl-only |
| prior native GDSC zero | pass | V1306 observed `pcie_1_gdsc` at `0mV` in the native lower window |
| prior full-window no-transition | pass | V1328/V1345 observed no GPIO142, pcie1, PCI, MHI, ks, WLFW, or wlan0 transition |
| safety | pass | host-only; no device command and no mutation |

## V1354 Read-only Observer Contract

V1354 should be live read-only. It should observe the following surfaces before
and during the existing bounded current-route lower window:

| Surface | Read-only path set |
| --- | --- |
| pcie1 platform node | `/sys/devices/platform/soc/1c08000.qcom,pcie`, `/sys/bus/platform/devices/1c08000.qcom,pcie` |
| pcie1 state files | `current_link_state`, `link_state`, `power/runtime_status`, `power/control`, `uevent`, `modalias`, `resource`, `irq` |
| GDSC/regulators | `/sys/kernel/debug/regulator/regulator_summary`, `/sys/kernel/debug/regulator_summary`; filter `pcie_1_gdsc`, `pcie_0_gdsc`, `pm8150l_l3`, `pm8150_l5`, `VDD_CX_LEVEL` |
| clocks/refclk | `/sys/kernel/debug/clk/clk_summary`; filter `GCC_PCIE_1_*`, `GCC_PCIE1_PHY_REFGEN_CLK`, `RPMH_CXO_CLK`, `pcie_phy_aux_clk` |
| pinctrl | `/sys/kernel/debug/pinctrl/*/{pins,pinmux-pins,pinconf-pins,gpio-ranges}`; filter GPIO102/PERST, GPIO103/CLKREQ, GPIO104/WAKE, plus GPIO135/GPIO142 and PM8150L GPIO9 for correlation |
| bus enumeration | `/sys/bus/pci/devices`, `/sys/bus/mhi/devices`, `/dev/mhi*` |
| interrupts/logs | `/proc/interrupts`, focused dmesg/klog lines for GPIO142/MDM2AP, errfatal, `pcie1`, `msm_pcie`, LTSSM, and MHI |

## Decision

The next active blocker is not upper CNSS/WLFW behavior. V1353 confirms the
next useful gate is V1354: observe whether pcie1 RC power, clocks/refclk,
PERST/CLKREQ/WAKE pinctrl, and GDSC state transition when the already-existing
lower `pm-service -> subsys_esoc0 -> mdm_subsys_powerup` path runs.

## Safety

- No device command, bridge command, NCM, helper deploy, or live runtime access.
- No sysfs/debugfs write.
- No PMIC/GPIO/GDSC write.
- No eSoC notify, `BOOT_DONE`, Wi-Fi HAL, scan/connect, credential handling,
  DHCP/routes, external ping, flash, boot image write, or partition write.

## Validation

```bash
python3 -m py_compile scripts/revalidation/native_wifi_pcie1_rc_static_contract_classifier_v1353.py
python3 scripts/revalidation/native_wifi_pcie1_rc_static_contract_classifier_v1353.py run
```

Both passed. The classifier returned
`v1353-pcie1-rc-static-contract-ready`.
