# Native Init V1525 MHI PM-Resume Position Classifier

## Summary

- Cycle: `V1525`
- Type: host-only source/evidence classifier
- Decision: `v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger`
- Result: PASS
- Reason: MHI PM-resume requires an existing pci_dev and is registered after MHI PCI probe, so it is downstream of first L0/PCI device creation; the first native blocker remains the Android-only initial enumerate/readiness trigger, not MHI resume

## Inputs

| input | path |
| --- | --- |
| v1524 | tmp/wifi/v1524-endpoint-trigger-attribution-classifier/manifest.json |
| v852_dmesg | tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/android/commands/dmesg-focus.txt |
| v1517_native_dmesg | tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/test-v1393-dmesg.stdout.txt |
| mhi_arch_source | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/bus/mhi/controllers/mhi_arch_qcom.c |
| mhi_qcom_source | kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/bus/mhi/controllers/mhi_qcom.c |
| pcie_source | {'kind': 'gitiles', 'url': 'https://android.googlesource.com/kernel/msm/+/0f3994dddbd64529255b281be6df783792110892/drivers/pci/host/pci-msm.c', 'raw_url': 'https://android.googlesource.com/kernel/msm/+/0f3994dddbd64529255b281be6df783792110892/drivers/pci/host/pci-msm.c?format=TEXT', 'sha256': '49deddb5e4f2d18142660e0f86e18d51821fad264ab780fa44f62cd321518137'} |

## Checks

| check | status | detail |
| --- | --- | --- |
| v1524-fixed-point | pass | V1524 raised MHI PM-resume as the candidate to validate |
| pm-resume-requires-existing-pci-dev | pass | MHI PM-resume path dereferences a pci_dev and pci-msm validates it against pcidev_table |
| pm-resume-hook-is-after-mhi-pci-probe | pass | eSoC power-on hook is registered from MHI PCI init/probe, so it is not the first PCI device creation path |
| pm-resume-not-initial-l0-trigger | pass | PM-resume can explain later link resumes but cannot create the first pci_dev/L0 by itself |
| test11-remains-initial-enumerate-path | pass | TEST:11/enumerate is the source path that creates PCI bus/device state after L0 |
| android-first-l0-before-esoc-ssctl | pass | Android V852 reaches first L0 before esoc0 SSCTL publication, consistent with initial enumeration before MHI/SSCTL maturity |
| android-initial-not-debugfs-test11 | pass | Android initial L0 has no pci-msm debugfs TEST marker in the positive reference |
| native-test11-fail-still-valid | pass | Native explicit TEST:11 still reaches LTSSM but fails before L0 |
| active-source-enumerate-callers-limited | pass | Local OSRC only exposes concrete msm_pcie_enumerate callers in the inactive CNSS2 branch; ICNSS path has no direct enumerate caller |

## Key Comparison

| field | value |
| --- | --- |
| Android first esoc0 | 8.54144 |
| Android first RC1 assert | 8.796369 |
| Android first L0 | 8.820231 |
| Android first esoc0 SSCTL | 11.582522 |
| Android has debugfs TEST marker | False |
| Native TEST:11 | True |
| Native link failed | 9.341767 |
| Native L0 | False |

## Source Positioning

| fact | value |
| --- | --- |
| MHI power-on uses existing pci_dev | True |
| MHI eSoC hook registered inside MHI PCI init | True |
| MHI PCI probe requires pci_dev | True |
| MHI PCI ID includes 17cb:0305 | True |
| pci-msm PM control requires user | True |
| pci-msm PM control validates pcidev_table | True |
| PM resume uses PM subset | True |
| TEST:11 enumerate uses PM_ALL | True |
| TEST:11 creates PCI bus/device state | True |
| Concrete OSRC enumerate callers | 1 |

## Key Lines

### MHI/eSoC

| line | text |
| --- | --- |
| 91 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| 171 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| 194 | static int mhi_arch_esoc_ops_power_on(void *priv, unsigned int flags) |
| 198 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| 222 | ret = msm_pcie_pm_control(MSM_PCIE_RESUME, pci_dev->bus->number, |
| 230 | ret = mhi_pci_probe(pci_dev, NULL); |
| 240 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| 259 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| 427 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| 483 | int mhi_arch_pcie_init(struct mhi_controller *mhi_cntrl) |
| 572 | esoc_ops->esoc_link_power_on = |
| 573 | mhi_arch_esoc_ops_power_on; |
| 752 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| 802 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |
| 812 | ret = msm_pcie_pm_control(MSM_PCIE_RESUME, mhi_cntrl->bus, pci_dev, |
| 844 | struct pci_dev *pci_dev = mhi_dev->pci_dev; |

### MHI PCI Probe

| line | text |
| --- | --- |
| 837 | int mhi_pci_probe(struct pci_dev *pci_dev, |
| 909 | {PCI_DEVICE(MHI_PCIE_VENDOR_ID, 0x0305)}, |
| 926 | module_pci_driver(mhi_pcie_driver); |

### pci-msm

| line | text |
| --- | --- |
| 212 | #define PM_ALL (PM_IRQ \| PM_CLK \| PM_GPIO \| PM_VREG \| PM_PIPE_CLK) |
| 363 | MSM_PCIE_LINK_DISABLED |
| 4064 | dev->link_status = MSM_PCIE_LINK_DISABLED; |
| 4116 | dev->link_status = MSM_PCIE_LINK_DISABLED; |
| 4233 | dev_table_t[index].dev = pcidev; |
| 4387 | ret = msm_pcie_enable(dev, PM_ALL); |
| 4436 | ret = pci_scan_root_bus_bridge(bridge); |
| 4450 | dev->enumerated = true; |
| 4664 | if (dev->link_status == MSM_PCIE_LINK_DISABLED) { |
| 4815 | dev->link_status = MSM_PCIE_LINK_DISABLED; |
| 6607 | static int msm_pcie_pm_resume(struct pci_dev *dev, |
| 6625 | ret = msm_pcie_enable(pcie_dev, PM_PIPE_CLK \| PM_CLK \| PM_VREG); |
| 6683 | if ((pcie_dev->link_status != MSM_PCIE_LINK_DISABLED) \|\| |
| 6706 | if ((pcie_dev->link_status != MSM_PCIE_LINK_DISABLED) \|\| |
| 6721 | int msm_pcie_pm_control(enum msm_pcie_pm_opt pm_opt, u32 busnr, void *user, |
| 6733 | if (!user) { |
| 6739 | pcie_dev = PCIE_BUS_PRIV_DATA(((struct pci_dev *)user)->bus); |
| 6757 | if (user == pcie_dev->pcidev_table[i].dev) { |
| 6780 | if (!msm_pcie_dev[rc_idx].drv_ready) { |
| 6831 | case MSM_PCIE_RESUME: |
| 6835 | MSM_PCIE_LINK_DISABLED) { |
| 6996 | if (reg->user == pcie_dev->pcidev_table[i].dev) { |

### Concrete `msm_pcie_enumerate` Callers In Local OSRC

| path | line | text |
| --- | --- | --- |
| drivers/net/wireless/cnss2/pci.c | 3797 | ret = msm_pcie_enumerate(rc_num); |

## Interpretation

V1525 corrects the V1524 PM-resume pivot. The MHI/eSoC `MSM_PCIE_RESUME` path is real, but it requires an already existing `pci_dev`: `mhi_arch_esoc_ops_power_on()` reads `mhi_dev->pci_dev`, `msm_pcie_pm_control()` casts the caller to `struct pci_dev`, and pci-msm validates that user against `pcidev_table`. The eSoC hook is registered from MHI PCI initialization/probe, so it cannot be the operation that creates the first PCI device or the first L0 link by itself.

That makes the Android first-L0 trigger a narrower problem: Android reaches first RC1 L0 without a debugfs TEST marker, while native explicit TEST:11 reaches LTSSM polling and fails before L0. The MHI PM-resume path can explain later Android RC1 suspend/resume cycles after the endpoint has already enumerated, not the missing native first-L0 transition.

Firmware, MHI deep dive, WLFW, scan/connect, credentials, DHCP/routes, and external ping remain downstream until native first L0 and PCI enumeration exist.

## Safety Scope

This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.

## Next

- V1526 Android initial RC1 trigger capture design: Capture or classify the Android-only first-L0 trigger below Wi-Fi connect: endpoint wake IRQ timing, pci-msm sysfs/client enumerate, or another kernel caller. Prefer read-only Android tracepoint/IRQ/dmesg capture before adding another native mutation; do not continue the MHI PM-resume branch as the first-L0 fix.
