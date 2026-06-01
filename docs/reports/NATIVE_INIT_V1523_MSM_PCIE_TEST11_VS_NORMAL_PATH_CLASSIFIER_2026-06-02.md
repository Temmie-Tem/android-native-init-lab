# Native Init V1523 MSM PCIe TEST:11 vs Normal Path Classifier

## Summary

- Cycle: `V1523`
- Type: host-only static/callgraph classifier
- Decision: `v1523-test11-shares-enable-normal-trigger-readiness-gap`
- Result: PASS
- Reason: TEST:11 is not missing the core AP-side enable sequence; pcie1 probe is intentionally deferred and normal callers converge on msm_pcie_enumerate, so the remaining gap is endpoint readiness/trigger semantics before enumerate

## Inputs

| input | path |
| --- | --- |
| v1498 | tmp/wifi/v1498-msm-pcie-test11-static-analysis/manifest.json |
| v1522 | tmp/wifi/v1522-android-native-rc1-source-parity-classifier/manifest.json |
| pcie_source | {'kind': 'gitiles', 'url': 'https://android.googlesource.com/kernel/msm/+/0f3994dddbd64529255b281be6df783792110892/drivers/pci/host/pci-msm.c', 'raw_url': 'https://android.googlesource.com/kernel/msm/+/0f3994dddbd64529255b281be6df783792110892/drivers/pci/host/pci-msm.c?format=TEXT', 'sha256': '49deddb5e4f2d18142660e0f86e18d51821fad264ab780fa44f62cd321518137'} |
| pcie_dts | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/qcom/sm8150-pcie.dtsi |

## Checks

| check | status | detail |
| --- | --- | --- |
| v1498-test11-fixed-point | pass | V1498 already proves TEST:11 enters corrected RC1 enumerate and native fails pre-L0 |
| v1522-sampled-sources-closed | pass | V1522 closes sampled GPIO/GDSC/IRQ low/off states as a discriminating root cause |
| test11-reaches-common-enable | pass | debugfs TEST:11 calls msm_pcie_enumerate, which calls msm_pcie_enable(PM_ALL) |
| pcie1-probe-enumeration-deferred | pass | SM8150 pcie1 has qcom,boot-option=<0x1>, setting NO_PROBE_ENUMERATION |
| normal-alternate-callers-converge | pass | sysfs/client or endpoint-wake paths converge on the same msm_pcie_enumerate function |
| no-ap-side-enable-op-missing-from-test11 | pass | The AP-side enable sequence is shared after enumerate; remaining difference is trigger/readiness semantics before enumerate |

## Path Summary

- pcie1 `qcom,boot-option`: `<0x1>` / parsed `1`
- NO_PROBE_ENUMERATION set: `True`
- NO_WAKE_ENUMERATION set: `False`
- wake enumeration allowed: `True`
- TEST:11 enum value: `11`
- TEST:11 calls `msm_pcie_enumerate`: `True`
- common enumerate calls `msm_pcie_enable(PM_ALL)`: `True`
- common enumerate calls PCI root scan: `True`

## Call Chains

- `debugfs_test11`: `debugfs pci-msm case write` -> `case MSM_PCIE_ENUMERATION` -> `msm_pcie_enumerate(dev->rc_idx)` -> `msm_pcie_enable(dev, PM_ALL)` -> `pci_scan_root_bus_bridge / pci_bus_add_devices if link succeeds`
- `sysfs_enumerate`: `platform sysfs enumerate attribute` -> `msm_pcie_enumerate(pcie_dev->rc_idx)` -> `msm_pcie_enable(dev, PM_ALL)`
- `endpoint_wake`: `GPIO104/WAKE falling IRQ` -> `handle_wake_irq` -> `schedule_work(handle_wake_work)` -> `handle_wake_func` -> `msm_pcie_enumerate(dev->rc_idx)` -> `msm_pcie_enable(dev, PM_ALL)`
- `probe_boot`: `msm_pcie_probe` -> `read qcom,boot-option` -> `return before probe enumeration if MSM_PCIE_NO_PROBE_ENUMERATION is set` -> `otherwise msm_pcie_enumerate(rc_idx)`

## Shared Enable Operations

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

## Normal-Path Entry Points

- `msm_pcie_probe`: lines `5835-6308`, checks NO_PROBE_ENUMERATION `True`, calls enumerate `True`.
- `msm_pcie_enumerate_store`: lines `2025-2036`, calls enumerate `True`.
- `handle_wake_irq`: lines `4754-4793`, checks NO_WAKE_ENUMERATION `True`, schedules wake work `True`.
- `handle_wake_func`: lines `4547-4618`, calls enumerate `True`.

## Key Source Lines

| line | text |
| --- | --- |
| 367 | MSM_PCIE_NO_PROBE_ENUMERATION = BIT(0), |
| 368 | MSM_PCIE_NO_WAKE_ENUMERATION = BIT(1) |
| 1475 | case MSM_PCIE_ENUMERATION: |
| 1482 | if (!msm_pcie_enumerate(dev->rc_idx)) |
| 2033 | msm_pcie_enumerate(pcie_dev->rc_idx); |
| 4370 | int msm_pcie_enumerate(u32 rc_idx) |
| 4517 | EXPORT_SYMBOL(msm_pcie_enumerate); |
| 4559 | "PCIe: Start enumeration for RC%d upon the wake from endpoint.\n", |
| 4562 | ret = msm_pcie_enumerate(dev->rc_idx); |
| 4770 | MSM_PCIE_NO_WAKE_ENUMERATION)) { |
| 4772 | schedule_work(&dev->handle_wake_work); |
| 6270 | MSM_PCIE_NO_PROBE_ENUMERATION) { |
| 6278 | ret = msm_pcie_enumerate(rc_idx); |

## Interpretation

V1523 does not find a missing AP-side `msm_pcie_enable()` operation in TEST:11. The debugfs TEST:11 path, sysfs/client path, endpoint-wake work path, and non-deferred probe path all converge on `msm_pcie_enumerate()`, which calls `msm_pcie_enable(dev, PM_ALL)` and then scans the PCI root bus if link training succeeds.

For this board, DTS sets `qcom,boot-option=<0x1>`, so probe-time enumeration is intentionally skipped. Android's successful RC1 path therefore comes from a later normal trigger, not from immediate probe enumeration. Since V1522 shows sampled GPIO/GDSC states are not discriminating, the next blocker is the pre-enumerate trigger/readiness condition that Android satisfies and native TEST:11 does not.

Firmware, MHI, WLFW, scan/connect, credentials, DHCP/routes, and external ping remain downstream until native RC1 reaches L0 and PCI enumeration exists.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.

## Next

- V1524 endpoint-readiness trigger classifier: Classify Android-good and native-fail evidence for the trigger that causes normal msm_pcie_enumerate: endpoint wake IRQ/GPIO104, sysfs/client caller, or vendor client request. Do this host-only/read-only first; do not add another blind TEST:11 timing retry.
