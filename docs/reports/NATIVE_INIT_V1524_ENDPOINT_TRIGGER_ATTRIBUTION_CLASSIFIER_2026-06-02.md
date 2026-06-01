# Native Init V1524 Endpoint Trigger Attribution Classifier

## Summary

- Cycle: `V1524`
- Type: host-only static/evidence classifier
- Decision: `v1524-trigger-attribution-pivots-to-esoc-mhi-pm-resume`
- Result: PASS
- Reason: Android-good initial RC1 is not a debugfs TEST:11 path, endpoint wake is not consistently attributable, and source shows an eSoC/MHI MSM_PCIE_RESUME path that must be modeled before the next mutation

## Inputs

| input | path |
| --- | --- |
| v1523 | tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier/manifest.json |
| v852_dmesg | tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt |
| v852_interrupts | tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/android/commands/interrupts-focus.txt |
| v1521_samples | tmp/wifi/v1521-android-rc1-magisk-postfs-handoff/android-postfs-evidence/a90-v1521-rc1-postfs-sampler/samples.log |
| v1521_host_dmesg | tmp/wifi/v1521-android-rc1-magisk-postfs-handoff/android-postfs-evidence/host-dmesg-filtered.txt |
| v1517_native_dmesg | tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/test-v1393-dmesg.stdout.txt |
| mhi_arch_source | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/bus/mhi/controllers/mhi_arch_qcom.c |
| msm_pcie_header | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/linux/msm_pcie.h |
| pcie_source | {'kind': 'gitiles', 'url': 'https://android.googlesource.com/kernel/msm/+/0f3994dddbd64529255b281be6df783792110892/drivers/pci/host/pci-msm.c', 'raw_url': 'https://android.googlesource.com/kernel/msm/+/0f3994dddbd64529255b281be6df783792110892/drivers/pci/host/pci-msm.c?format=TEXT', 'sha256': '49deddb5e4f2d18142660e0f86e18d51821fad264ab780fa44f62cd321518137'} |

## Checks

| check | status | detail |
| --- | --- | --- |
| v1523-fixed-point | pass | V1523 proves TEST:11 reaches the common enumerate/enable path but still leaves trigger/readiness attribution open |
| android-v852-esoc-to-l0 | pass | Android V852 shows esoc0 followed by RC1 enable and LTSSM_L0 |
| android-v852-not-debugfs-test11 | pass | Android V852 initial RC1 sequence has no pci-msm TEST/debugfs marker |
| native-v1517-debugfs-test11-fails | pass | Native V1517 uses explicit TEST:11 and fails before L0 |
| mhi-esoc-pm-resume-source-candidate | pass | Local MHI eSoC hook can request MSM_PCIE_RESUME, which dispatches to msm_pcie_enable via pm_resume |
| endpoint-wake-not-attributed | pass | Existing Android-good evidence has contradictory GPIO104 IRQ visibility, so endpoint wake cannot be treated as the proven initial trigger |

## Android-Good vs Native-Fail Trigger Evidence

| field | Android V852 | Android V1521 | Native V1517 |
| --- | --- | --- | --- |
| esoc0 ts | 8.54144 |  | 9.190933 |
| RC1 assert ts | 8.796369 |  | 9.226972 |
| RC1 L0 / link fail | 8.820231 |  | 9.341767 |
| debugfs TEST marker | False |  | True |
| GPIO104 IRQ total | 7 | 0 |  |
| GPIO142 IRQ total | 1 | 0 |  |
| WLFW/BDF/wlan0 | 8.392748/9.489583/see V852 lower chain | 8.585121/9.673077/14.843021 | False |

## Source Candidate Added To The Model

| source fact | value |
| --- | --- |
| MHI eSoC power-on line | 194 |
| MHI eSoC hook registration line | 572 |
| MHI hook calls `MSM_PCIE_RESUME` | True |
| MHI hook calls `mhi_pci_probe` | True |
| `msm_pcie_pm_control` dispatches resume | True |
| resume path calls `msm_pcie_enable` subset | True |
| resume flag subset | PM_PIPE_CLK \| PM_CLK \| PM_VREG |
| TEST:11 flag set | PM_ALL |

## Key Lines

### MHI eSoC Hook

| line | text |
| --- | --- |
| 194 | static int mhi_arch_esoc_ops_power_on(void *priv, unsigned int flags) |
| 222 | ret = msm_pcie_pm_control(MSM_PCIE_RESUME, pci_dev->bus->number, |
| 230 | ret = mhi_pci_probe(pci_dev, NULL); |
| 572 | esoc_ops->esoc_link_power_on = |
| 812 | ret = msm_pcie_pm_control(MSM_PCIE_RESUME, mhi_cntrl->bus, pci_dev, |

### PCIe PM Path

| line | text |
| --- | --- |
| 212 | #define PM_ALL (PM_IRQ \| PM_CLK \| PM_GPIO \| PM_VREG \| PM_PIPE_CLK) |
| 6607 | static int msm_pcie_pm_resume(struct pci_dev *dev, |
| 6625 | ret = msm_pcie_enable(pcie_dev, PM_PIPE_CLK \| PM_CLK \| PM_VREG); |
| 6721 | int msm_pcie_pm_control(enum msm_pcie_pm_opt pm_opt, u32 busnr, void *user, |
| 6831 | case MSM_PCIE_RESUME: |
| 6844 | ret = msm_pcie_pm_resume(dev, user, data, options); |

## Interpretation

V1524 keeps the V1523 result but tightens the next blocker. TEST:11 is a valid way to reach `msm_pcie_enable()`, but Android's first successful RC1 sequence is not observed as a debugfs TEST path. Existing Android evidence also does not cleanly prove endpoint wake GPIO104 as the initial trigger: V852 shows a nonzero post-boot wake count, while V1521 reaches WLFW/BDF/`wlan0` with sampled GPIO104 counts staying zero.

The missing model piece is the eSoC/MHI PCIe PM path. Local source shows `mhi_arch_esoc_ops_power_on()` registers as an eSoC client hook, calls `msm_pcie_pm_control(MSM_PCIE_RESUME, ...)`, and then calls `mhi_pci_probe()`. The public `pci-msm.c` path dispatches `MSM_PCIE_RESUME` to `msm_pcie_pm_resume()`, which calls `msm_pcie_enable()` with `PM_PIPE_CLK | PM_CLK | PM_VREG`, while TEST:11 enumeration uses `PM_ALL`.

Therefore the next work should compare Android-path PM-resume semantics against TEST:11 semantics before any new live mutation. Firmware, MHI deep dive, WLFW, scan/connect, credentials, DHCP/routes, and external ping remain downstream until native RC1 reaches L0 and PCI enumeration exists.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.

## Next

- V1525 eSoC/MHI PM-resume vs TEST:11 path classifier: Compare msm_pcie_enable options/state prerequisites for TEST:11 PM_ALL versus MHI eSoC MSM_PCIE_RESUME (PM_PIPE_CLK|PM_CLK|PM_VREG), then decide whether a source/build-only Android-path observer or shim is justified. Do not retry blind TEST:11 timing and do not move to firmware/connect before L0.
