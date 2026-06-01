# Native Init V1498 MSM PCIe TEST:11 Static Analysis

## Summary

- Cycle: `V1498`
- Type: host-only static classifier over V1496 evidence, local DTS, and public `pci-msm.c` reference source
- Decision: `v1498-msm-pcie-test11-enumerate-path-confirmed-endpoint-response-gap`
- Result: PASS
- Reason: Public pci-msm source maps debugfs TEST:11 to the enumerate path, and enumerate calls msm_pcie_enable(PM_ALL). The device DTS binds RC1 to PERST GPIO102, wake GPIO104, pcie_1 clocks/resets, and SDX50M/MHI. V1496 therefore did exercise the intended RC1 enumerate/link-training path, but the endpoint still failed before L0.
- V1496 evidence: `tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff`
- Public PCIe source reference: https://android.googlesource.com/kernel/msm/+/0f3994dddbd64529255b281be6df783792110892/drivers/pci/host/pci-msm.c

## V1496 Failure Fixed Point

- V1496 decision: `v1496-test-boot-downstream-progress-rollback-pass`
- handoff/rollback pass: `True` / `True`
- corrected RC1 enumerate dmesg confirmed: `True`
- provider trigger: `True`
- RC1 progress: `True`
- RC1 L0: `False`
- RC1 link failed: `True`
- MHI/WLFW/BDF/FW-ready/wlan0: `False` / `False` / `False` / `False` / `False`
- case after provider ms: `46.817`
- PHY ready after case ms: `5.775`
- link fail after case ms: `114.737`

## TEST:11 Source Contract

- `MSM_PCIE_ENUMERATION` enum value: `11`
- enum line range: `371-404`
- TEST case line range: `1475-1491`
- TEST case calls `msm_pcie_enumerate`: `True`
- `msm_pcie_enumerate` line range: `4370-4516`
- `msm_pcie_enumerate` calls `msm_pcie_enable(dev, PM_ALL)`: `True`
- `msm_pcie_enable` line range: `3817-4100`

The relevant public `pci-msm.c` source maps debugfs TEST case `11` to the
enumeration path. That path calls the same enable routine that covers the
PERST, vreg, clock, PHY, pipe-clock, LTSSM, and link-check sequence used by
the observed RC1 dmesg markers. Samsung's exact vendor driver source is not
present in the local OSRC tree, so this remains a reference-source
classifier; matching dmesg strings make it actionable, but live evidence
still has priority.

## Enable-path Operations Seen In Source

- assert_perst: `True`
- vreg_init: `True`
- clk_init: `True`
- phy_init: `True`
- pipe_clk_init: `True`
- phy_ready: `True`
- release_perst: `True`
- ltssm_enable: `True`
- ltssm_poll: `True`
- confirm_linkup: `True`
- link_fail_message: `True`

## Local DTS Contract

- `pcie1` file: `kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi`
- `pcie1` line range: `286-551`
- compatible: `['qcom,pci-msm']`
- cell-index: `<1>`
- PERST GPIO: `102`
- WAKE GPIO: `104`
- GDSC supply: `<&pcie_1_gdsc>`
- vreg supplies: `<&pm8150l_l3>`, `<&pm8150_l5>`, `<&VDD_CX_LEVEL>`
- clock names: `pcie_1_pipe_clk, pcie_1_ref_clk_src, pcie_1_aux_clk, pcie_1_cfg_ahb_clk, pcie_1_mstr_axi_clk, pcie_1_slv_axi_clk, pcie_1_ldo, pcie_1_slv_q2a_axi_clk, pcie_tbu_clk, pcie_phy_refgen_clk, pcie_phy_aux_clk`
- reset names: `pcie_1_core_reset, pcie_1_phy_reset`
- RC1 bridge PCI ID: `['17cb:0108']`
- MHI PCI IDs: `['17cb:0305', '17cb:0306', '17cb:0307', '17cb:0308']`
- SDX50M compatible/link-info: `['qcom,ext-sdx50m']` / `['0305_01.01.00']`
- MHI eSoC mapping: `['mdm']` / `<&mdm3>`

## Interpretation

- V1496 no longer supports a provider-entry failure model: provider trigger occurred and RC1 entered PHY/LTSSM progress.
- TEST:11 is not just a no-op status probe in the reference source; it is the enumerate path and reaches `msm_pcie_enable(PM_ALL)`.
- The failure is still pre-L0: LTSSM reaches polling/compliance and then link initialization fails; no downstream MHI/WLFW/BDF/FW-ready/`wlan0` marker appears.
- Firmware, MHI pipe, WLFW, BDF, scan/connect, credentials, DHCP/routes, and external ping stay parked until RC1 reaches L0 and PCI enumeration exists.

## Safety Scope

This classifier was host-only. It fetched/read source and local DTS files,
parsed existing V1496 evidence, and wrote private evidence output. It did
not issue device commands, flash, reboot, start Wi-Fi HAL, scan/connect,
use credentials, configure DHCP/routes, perform external ping, write
PMIC/GPIO/GDSC controls, or write pci-msm debugfs controls.

## Next

V1499 should be source/build-only: add a pre-L0 endpoint parity observer that captures RC1 PERST/refclk/clock/GDSC/GPIO102/GPIO103/GPIO104/GPIO135/GPIO142 and LTSSM timing around the provider-trigger plus corrected RC1 enumerate window. Do not start Wi-Fi HAL or use credentials.
