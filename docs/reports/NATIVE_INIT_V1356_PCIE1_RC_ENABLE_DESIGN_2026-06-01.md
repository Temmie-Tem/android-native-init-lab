# Native Init V1356 pcie1 RC Enable Design

## Summary

- Cycle: `V1356`
- Type: host-only design classifier
- Decision: `v1356-pcie1-rc-enable-design-ready-readonly-surface-next`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_pcie1_rc_enable_design_v1356.py`
- Evidence:
  - `tmp/wifi/v1356-pcie1-rc-enable-design/manifest.json`
  - `tmp/wifi/v1356-pcie1-rc-enable-design/summary.md`

## Inputs

| input | path |
| --- | --- |
| esoc_static_analysis | docs/reports/ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md |
| v1353_static_contract | docs/reports/NATIVE_INIT_V1353_PCIE1_RC_STATIC_CONTRACT_CLASSIFIER_2026-06-01.md |
| v1354_live_observer | docs/reports/NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md |
| v1355_pon_parity | docs/reports/NATIVE_INIT_V1355_PMIC_GPIO9_PON_PARITY_CLASSIFIER_2026-06-01.md |
| sm8150_pcie_dtsi | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi |
| sm8150_sdx50m_dtsi | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi |
| sm8150_mhi_dtsi | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-mhi.dtsi |
| sm8150_dtsi | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150.dtsi |
| r3q_overlay | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r03.dts |
| msm_pcie_h | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/linux/msm_pcie.h |
| cnss_h | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/net/cnss.h |
| cnss2_debug_c | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/net/wireless/cnss2/debug.c |
| cnss2_pci_c | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/net/wireless/cnss2/pci.c |
| cnss2_main_c | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/net/wireless/cnss2/main.c |
| mhi_arch_qcom_c | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/bus/mhi/controllers/mhi_arch_qcom.c |

## Checks

| check | pass |
| --- | --- |
| cnss2_rc_num_mismatch_risk_identified | true |
| cnss_dev_boot_enumerate_exists | true |
| hard_exclusions_preserved | true |
| mhi_hook_downstream_of_pci_dev | true |
| msm_pcie_enumerate_exported | true |
| pcie1_static_contract_present | true |
| sdx50m_mhi_endpoint_on_pcie1 | true |
| v1354_pcie1_rc_off_confirmed | true |
| v1355_pon_parity_closed | true |

## Decision

V1354 proves the current lower route reaches mdm_subsys_powerup while pcie1 RC stays off, and V1355 closes blind PON mutation. The only defensible next step is a read-only live surface verifier that proves a narrow RC1 control path before any bounded enumerate/link-up attempt.

The shortest confirmed blocker is now RC-side PCIe readiness. V1354
proved the current native lower route reaches `mdm_subsys_powerup`
while `pcie_1_gdsc`, pcie1 clkref/pipe, GPIO102/PERST, PCI, MHI,
GPIO142/MDM2AP, WLFW, and `wlan0` stay absent. V1355 closes blind
PM8150L GPIO9/PON mutation as the next branch. Therefore the next
work must prove the available RC1 control surface before any write.

## Candidate Control Surfaces

| surface | status | evidence | required action |
| --- | --- | --- | --- |
| msm_pcie_enumerate(1) | best semantic kernel operation, no direct userspace entry yet | int msm_pcie_enumerate(u32 rc_idx); | V1357 must find an existing kernel-exposed caller before any write |
| cnss2 debugfs dev_boot enumerate | possible but unproven and likely board-mismatched until live read-only checks pass | debugfs supports enumerate/linkup/powerup; generic cnss2 DTS uses wlan-rc-num=0 while A90 active path is ICNSS pcie-parent pcie1 | read-only verify /sys/kernel/debug/cnss/dev_boot existence and RC mapping first |
| platform driver bind/probe for 1c08000.qcom,pcie | possible but source-incomplete and higher risk | pcie1 platform node exists in DTS; Qualcomm PCIe core implementation is not present in the staged OSRC tree | read-only enumerate platform device/driver names and bind files only |
| /sys/bus/pci/rescan or broad bus rescan | rejected as first mutation | global side effects; does not prove RC1-specific GDSC/refclk/PERST control | do not use unless narrower RC1-specific surfaces are absent and a later plan narrows risk |
| direct PMIC/GPIO/GDSC/debugfs writes | rejected | V1355 closes PON parity; V1354 points at missing RC1 enable, not blind PON/GDSC pokes | keep excluded |

## V1357 Read-only Verifier Plan

| step | read-only collection | purpose |
| --- | --- | --- |
| pcie1 platform surface | list /sys/devices/platform/soc/*1c08000*, /sys/bus/platform/devices/*1c08000*, driver symlinks, modalias, uevent, power/runtime_status | prove the RC1 platform device and bound driver names before considering bind/probe writes |
| cnss debugfs surface | stat/read /sys/kernel/debug/cnss/dev_boot if present; read-only capture usage text and nearby cnss debug files | decide whether dev_boot exists and whether it can plausibly target pcie1 rather than generic RC0 |
| live devicetree mapping | read /sys/firmware/devicetree/base qcom,wlan-rc-num and qcom,pcie-parent nodes if exposed | prevent using a cnss2 debug hook bound to the wrong root complex |
| power and clock baseline | pcie_1_gdsc, pcie1 clkref/refgen/pipe clocks, PERST/CLKREQ/WAKE, PCI/MHI device counts | confirm V1354 off-state before any later bounded mutation |
| log and interrupt baseline | focused dmesg/klog and /proc/interrupts for pcie1, LTSSM, MHI, GPIO142, errfatal | separate existing boot noise from mutation-caused transitions |

## First Mutation Contract

This is not approved by V1356. It is the contract a later V1358-style
bounded experiment must satisfy after V1357 proves the surface.

| gate | requirement |
| --- | --- |
| preflight | V1357 proves one narrow RC1-specific surface, maps it to pcie1, and baseline is still off |
| candidate A | if cnss/dev_boot is present and proven RC1-safe, only consider 'enumerate' first; do not use 'powerup' |
| candidate B | if only platform bind/probe exists, stop for a new design; do not bind blindly |
| observe window | 2-5s bounded observation of GDSC/refclk/PERST/LTSSM/PCI/MHI/GPIO142 with timeout |
| cleanup | always cleanup by reboot; do not chain eSoC notify, BOOT_DONE, HAL, scan, DHCP, routes, or external ping |
| stop conditions | stop if GDSC/refclk/PERST remain off, if wrong RC is indicated, if kernel reports PCIe errors, or if device health check fails |

## Safety

- Host-only; no device command or live runtime access.
- No sysfs/debugfs write, platform bind, PCI rescan, `cnss/dev_boot` write,
  PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL,
  scan/connect, credential handling, DHCP/routes, external ping, flash,
  boot image write, or partition write.

## Next

Implement V1357 as a live read-only pcie1 RC control-surface verifier.
Do not execute the RC enable experiment until V1357 proves a narrow
RC1-specific path and records a clean preflight baseline.
