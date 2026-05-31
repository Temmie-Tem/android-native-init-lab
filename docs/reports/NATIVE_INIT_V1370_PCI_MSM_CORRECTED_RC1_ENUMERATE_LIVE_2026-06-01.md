# Native Init V1370 Corrected-RC1 pci-msm Enumerate Live

## Summary

- Cycle: `V1370`
- Type: bounded live corrected-RC1 enumerate proof
- Decision: `v1370-corrected-rc1-link-training-no-l0-clean`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_pcie1_enumerate_live_v1370.py`
- Evidence:
  - `tmp/wifi/v1370-pci-msm-corrected-rc1-enumerate-live/manifest.json`
  - `tmp/wifi/v1370-pci-msm-corrected-rc1-enumerate-live/summary.md`
  - `tmp/wifi/v1370-pci-msm-corrected-rc1-enumerate-live/native/`

## Decision

rc_sel=2 and case=11 reached RC1 enumerate and transient RC1 PHY/LTSSM link training, but did not reach L0 or create PCI/MHI devices; device health remained clean

## Key Observations

| field | value |
| --- | --- |
| mounted_before | False |
| mounted_by_v1370 | True |
| mounted_during | True |
| mounted_after | False |
| cleanup_ok | True |
| write_ok | True |
| reset_after_write | False |
| after_captures_ok | True |
| before_pci_count | 0 |
| after_pci_count | 0 |
| before_mhi_present | False |
| after_mhi_present | False |
| gdsc_changed | False |
| clk_changed | False |
| steady_state_change_seen | False |
| pcie_link_seen | False |
| pcie_enable_attempt_seen | True |
| pcie_release_reset_seen | True |
| pcie_phy_ready_seen | True |
| ltssm_poll_active_seen | True |
| ltssm_poll_compliance_seen | True |
| pcie_link_failed_seen | True |
| transient_link_training_seen | True |
| enumerate_seen | True |
| rc1_enumerate_seen | True |
| post_selftest_fail0 | True |

## Captures

| name | ok | rc | status | file |
| --- | --- | --- | --- | --- |
| version | True | 0 | ok | native/version.txt |
| selftest | True | 0 | ok | native/selftest.txt |
| status | True | 0 | ok | native/status.txt |
| mounts-before | True | 0 | ok | native/mounts-before.txt |
| debugfs-mount | True | 0 | ok | native/debugfs-mount.txt |
| mounts-during | True | 0 | ok | native/mounts-during.txt |
| pci-msm-find | True | 0 | ok | native/pci-msm-find.txt |
| pci-msm-case-read | True | 0 | ok | native/pci-msm-case-read.txt |
| before-regulator-pcie | True | 0 | ok | native/before-regulator-pcie.txt |
| before-clk-pcie | True | 0 | ok | native/before-clk-pcie.txt |
| before-gpio-pcie | True | 0 | ok | native/before-gpio-pcie.txt |
| before-pci-devices | True | 0 | ok | native/before-pci-devices.txt |
| before-mhi-devices | True | 0 | ok | native/before-mhi-devices.txt |
| before-interrupts | True | 0 | ok | native/before-interrupts.txt |
| before-dmesg-pcie-tail | True | 0 | ok | native/before-dmesg-pcie-tail.txt |
| write-rc1-bitmask2-case11-enumerate | True | 0 | ok | native/write-rc1-bitmask2-case11-enumerate.txt |
| settle | True | 0 | ok | native/settle.txt |
| after-regulator-pcie | True | 0 | ok | native/after-regulator-pcie.txt |
| after-clk-pcie | True | 0 | ok | native/after-clk-pcie.txt |
| after-gpio-pcie | True | 0 | ok | native/after-gpio-pcie.txt |
| after-pci-devices | True | 0 | ok | native/after-pci-devices.txt |
| after-mhi-devices | True | 0 | ok | native/after-mhi-devices.txt |
| after-interrupts | True | 0 | ok | native/after-interrupts.txt |
| after-dmesg-pcie-tail | True | 0 | ok | native/after-dmesg-pcie-tail.txt |
| debugfs-umount | True | 0 | ok | native/debugfs-umount.txt |
| mounts-after | True | 0 | ok | native/mounts-after.txt |
| post-selftest | True | 0 | ok | native/post-selftest.txt |
| post-status | True | 0 | ok | native/post-status.txt |

## Safety

- V1370 writes only corrected `rc_sel=2` and enumerate `case=11`.
- No PERST assert/deassert cases, MMIO write cases,
  boot option write, platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC
  direct write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential
  handling, DHCP/routes, external ping, flash, boot image write, or partition write.

## Next

classify why RC1 stops at LTSSM poll/compliance before any Wi-Fi HAL or network bring-up
