# Native Init V1368 Corrected-RC1 pci-msm Status Live

## Summary

- Cycle: `V1368`
- Type: bounded live corrected-RC1 status-read proof
- Decision: `v1368-corrected-rc1-status-proof-clean`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_pci_msm_corrected_rc1_status_live_v1368.py`
- Evidence:
  - `tmp/wifi/v1368-pci-msm-corrected-rc1-status-live/manifest.json`
  - `tmp/wifi/v1368-pci-msm-corrected-rc1-status-live/summary.md`
  - `tmp/wifi/v1368-pci-msm-corrected-rc1-status-live/native/`

## Decision

rc_sel=2 and case=26 emitted RC1 PERST/WAKE status with no PCI/MHI/link transition and device health remained clean

## Key Observations

| field | value |
| --- | --- |
| mounted_before | False |
| mounted_by_v1368 | True |
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
| pcie_link_seen | False |
| enumerate_seen | False |
| rc1_status_seen | True |
| rc1_perst_gpio102_value | 0 |
| rc1_wake_gpio104_value | 0 |
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
| write-rc1-bitmask2-case26-status-only | True | 0 | ok | native/write-rc1-bitmask2-case26-status-only.txt |
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

- V1368 writes only corrected `rc_sel=2` and status-read `case=26`.
- No `case=11` enumerate, PERST assert/deassert cases, MMIO write cases,
  boot option write, platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC
  direct write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential
  handling, DHCP/routes, external ping, flash, boot image write, or partition write.

## Next

V1369 decide whether to advance to pcie1 enumerate or prefer kernel-side shim; no enumerate yet
