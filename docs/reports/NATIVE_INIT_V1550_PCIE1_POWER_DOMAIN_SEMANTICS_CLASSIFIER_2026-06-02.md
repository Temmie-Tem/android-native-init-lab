# Native Init V1550 PCIe1 Power-Domain Semantics Classifier

## Summary

- Cycle: `V1550`
- Type: `host-only source/evidence classifier`
- Decision: `v1550-pcie1-gdsc-summary-is-not-power-proof-tracefs-needed`
- Result: `PASS`
- Evidence: `docs/reports/NATIVE_INIT_V1549_LOW_OVERHEAD_RESULT_CLASSIFIER_2026-06-02.md`

V1550 is host-only. It reconciles the V1549 pre-fail `pcie_1_gdsc ... 0mV` observation with `pci-msm.c`, the regulator core, the Qualcomm GDSC regulator driver, and SM8150 DTS. The active blocker remains `rc1-ltssm-link-failed-no-l0`; firmware/MHI/WLFW/connect-side work remains downstream.

## Checks

| check | result | detail |
| --- | --- | --- |
| v1549-fixed-no-l0-input-present | pass | V1549 evidence fixes current blocker at RC1 link failed / no L0 |
| pcie1-enable-path-requests-gdsc | pass | `msm_pcie_enumerate()` calls `msm_pcie_enable(PM_ALL)`, and `msm_pcie_clk_init()` calls `regulator_enable(dev->gdsc)` |
| pcie1-dts-maps-gdsc-vdd-to-pcie-1-gdsc | pass | DTS maps `gdsc-vdd` to the `pcie_1_gdsc` qcom,gdsc regulator node |
| regulator-summary-zero-mv-is-not-state-proof | pass | `regulator_summary` prints a voltage column via `_regulator_get_voltage`; qcom GDSC has enable/disable/is_enabled ops but no voltage getter/list op |
| link-fail-cleans-up-gdsc-and-clocks | pass | After link failure, `msm_pcie_enable()` deinitializes pipe clocks, PCIe clocks/GDSC, and vregs unless keep-resources is set |
| next-observer-can-use-existing-tracefs-events | pass | V1315 already proved target regulator/clk/gpio tracefs events and formats exist |

## PCIe1 Source Path

| field | source line |
| --- | --- |
| PM_ALL | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:236: #define PM_ALL (PM_IRQ \| PM_CLK \| PM_GPIO \| PM_VREG \| PM_PIPE_CLK) |
| sysfs enumerate | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:2419: msm_pcie_enumerate(pcie_dev->rc_idx); |
| enumerate PM_ALL | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:5280: ret = msm_pcie_enable(dev, PM_ALL); |
| gdsc handle | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4197: dev->gdsc = devm_regulator_get(&pdev->dev, "gdsc-vdd"); |
| pcie1 gdsc supply | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi:459: gdsc-vdd-supply = <&pcie_1_gdsc>; |
| PERST assert | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4632: PCIE_INFO(dev, "PCIe: Assert the reset of endpoint of RC%d.\n", |
| vreg stage | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4642: ret = msm_pcie_vreg_init(dev); |
| GDSC enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:3715: rc = regulator_enable(dev->gdsc); |
| pipe clock stage | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4716: ret = msm_pcie_pipe_clk_init(dev); |
| PHY ready | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4755: PCIE_INFO(dev, "PCIe RC%d PHY is ready!\n", dev->rc_idx); |
| PERST release | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4780: PCIE_INFO(dev, "PCIe: Release the reset of endpoint of RC%d.\n", |
| LTSSM enable | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4826: /* enable link training */ |
| link-fail cleanup | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4856: PCIE_ERR(dev, "PCIe RC%d link initialization failed (LTSSM_STATE:0x%x)\n", |
| cleanup pipe | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4973: msm_pcie_pipe_clk_deinit(dev); |
| cleanup clk/GDSC | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4974: msm_pcie_clk_deinit(dev); |
| cleanup vreg | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/pci/host/pci-msm.c:4980: msm_pcie_vreg_deinit(dev); |

## Regulator/GDSC Semantics

| field | source line |
| --- | --- |
| summary use/open/bypass | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/regulator/core.c:4880: rdev->use_count, rdev->open_count, rdev->bypass_count); |
| summary voltage column | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/regulator/core.c:4882: seq_printf(s, "%5dmV ", _regulator_get_voltage(rdev) / 1000); |
| summary current column | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/regulator/core.c:4883: seq_printf(s, "%5dmA ", _regulator_get_current_limit(rdev) / 1000); |
| get_voltage note | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/regulator/core.c:3286: * NOTE: If the regulator is disabled it will return the voltage value. This |
| get_voltage no-op fallback | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/regulator/core.c:3272: return -EINVAL; |
| enable increments use_count | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/regulator/core.c:2204: rdev->use_count++; |
| disable decrements use_count | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/regulator/core.c:2320: rdev->use_count--; |
| GDSC compatible | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/qcom/gdsc-regulator.c:1059: { .compatible = "qcom,gdsc" }, |
| GDSC type | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/qcom/gdsc-regulator.c:878: sc->rdesc.type = REGULATOR_VOLTAGE; |
| GDSC ops | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/qcom/gdsc-regulator.c:677: static struct regulator_ops gdsc_ops = { |
| GDSC enable op | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/qcom/gdsc-regulator.c:679: .enable = gdsc_enable, |
| GDSC disable op | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/clk/qcom/gdsc-regulator.c:680: .disable = gdsc_disable, |
| GDSC lacks voltage ops | True |

The `0mV` value is a debugfs voltage-column artifact for this GDSC class, not a direct proof that the physical PCIe1 power domain never turned on. The use-count column still needs precise event-level timing because source code says `regulator_enable(dev->gdsc)` should increment use_count before the PHY/LTSSM path and link-fail cleanup should later disable it.

## Tracefs Readiness

| field | value |
| --- | --- |
| V1315 preflight decision present | True |
| regulator events available | True |
| clk events available | True |
| gpio events available | True |

## Interpretation

- Fixed blocker: RC1 reaches PHY/LTSSM, then fails at LTSSM_POLL_COMPLIANCE without L0.
- Source path: `msm_pcie_enumerate()` reaches `msm_pcie_enable(PM_ALL)`, so the normal source path requests vregs, GDSC, clocks, PHY, pipe clock, PERST release, and LTSSM.
- GDSC voltage column: `pcie_1_gdsc ... 0mV` in `regulator_summary` is not direct physical-voltage proof: the GDSC regulator ops do not expose a voltage getter/list op, and `regulator_summary` still prints `_regulator_get_voltage()/1000`.
- Remaining gap: The leading `0` use_count in sampled `pcie_1_gdsc` rows is still meaningful but not decisive with the current sampler; the source path should enable and then disable it around link failure, so event-level enable/disable timing is needed.
- Parked work: Do not repeat enumerate-only retries and do not move to firmware/MHI/WLFW/scan/connect until native RC1 L0 and PCI enumeration exist.

## Next Gate

- Cycle: `V1551`
- Summary: bounded targeted tracefs observer for pcie1 regulator/clk/gpio events around the existing sysfs-client enumerate window
- Capture: regulator:regulator_enable and regulator_enable_complete names containing pcie_1_gdsc, pm8150l_l3, pm8150_l5, VDD_CX_LEVEL
- Capture: regulator disable timing for the same names after link failure
- Capture: clk enable/complete timing for GCC_PCIE_1_* and pcie_phy/refgen clocks if names are present in trace lines
- Capture: gpio_value/gpio_direction events for GPIO102/PERST, GPIO104/WAKE, GPIO135/AP2MDM, GPIO142/MDM2AP
- Capture: dmesg LTSSM/link-fail timestamps for alignment
- Guardrail: tracefs mount/write only inside bounded observer with cleanup verification
- Guardrail: no PMIC/GPIO/GDSC direct write from userspace
- Guardrail: no global PCI rescan or platform bind/unbind
- Guardrail: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping
- Guardrail: rollbackable test-boot handoff only if live capture is required

## Safety Scope

This classifier is host-only. It performs no device command, tracefs write, reboot, flash, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, global PCI rescan, or platform bind/unbind.
