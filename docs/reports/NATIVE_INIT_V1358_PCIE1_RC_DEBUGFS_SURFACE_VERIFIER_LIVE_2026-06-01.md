# Native Init V1358 pcie1 RC Debugfs Surface Verifier Live

## Summary

- Cycle: `V1358`
- Type: temporary-debugfs live verifier
- Decision: `v1358-icnss-debugfs-only-no-cnss-dev-boot`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_pcie1_rc_debugfs_surface_verifier_live_v1358.py`
- Evidence:
  - `tmp/wifi/v1358-pcie1-rc-debugfs-surface-verifier-live/manifest.json`
  - `tmp/wifi/v1358-pcie1-rc-debugfs-surface-verifier-live/summary.md`
  - `tmp/wifi/v1358-pcie1-rc-debugfs-surface-verifier-live/native/`

## Decision

debugfs exposes ICNSS, not CNSS2 dev_boot; cnss/dev_boot enumerate is unavailable on this live kernel

## Key Observations

| field | value |
| --- | --- |
| mounted_before | False |
| mounted_by_v1358 | True |
| mounted_during | True |
| mounted_after | False |
| cleanup_ok | True |
| cnss_debugfs_any | False |
| cnss_dev_boot_present | False |
| dev_boot_enumerate | False |
| icnss_debugfs_any | True |
| icnss_boot_wlan_seen | False |
| icnss_stats_readable | True |
| icnss_state_line | State: 0x80(SSR REGISTERED) |
| icnss_server_arrive_count | 0 |
| icnss_fw_ready_count | 0 |
| icnss_register_driver_count | 0 |
| pcie1_gdsc_seen | True |
| pcie1_gdsc_nonzero | False |
| pcie_clk_seen | True |
| gpio102_perst_seen | True |
| pci_device_count | 0 |
| mhi_device_count | 0 |
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
| debugfs-root-ls | True | 0 | ok | native/debugfs-root-ls.txt |
| cnss-debugfs-ls | False | 1 | error | native/cnss-debugfs-ls.txt |
| cnss-dev-boot-read | False | 1 | error | native/cnss-dev-boot-read.txt |
| cnss-debugfs-find | False | 1 | error | native/cnss-debugfs-find.txt |
| icnss-debugfs-ls | True | 0 | ok | native/icnss-debugfs-ls.txt |
| icnss-debugfs-find | True | 0 | ok | native/icnss-debugfs-find.txt |
| icnss-stats-read | True | 0 | ok | native/icnss-stats-read.txt |
| regulator-pcie-grep | False | 2 | error | native/regulator-pcie-grep.txt |
| clk-pcie-grep | True | 0 | ok | native/clk-pcie-grep.txt |
| gpio-pcie-grep | True | 0 | ok | native/gpio-pcie-grep.txt |
| pinctrl-pcie-find | True | 0 | ok | native/pinctrl-pcie-find.txt |
| pcie1-platform-uevent | True | 0 | ok | native/pcie1-platform-uevent.txt |
| pcie1-platform-driver-readlink | True | 0 | ok | native/pcie1-platform-driver-readlink.txt |
| dt-wlan-rc-num-find | True | 0 | ok | native/dt-wlan-rc-num-find.txt |
| dt-pcie-parent-find | True | 0 | ok | native/dt-pcie-parent-find.txt |
| pci-devices-ls | True | 0 | ok | native/pci-devices-ls.txt |
| mhi-devices-ls | True | 0 | ok | native/mhi-devices-ls.txt |
| proc-interrupts | True | 0 | ok | native/proc-interrupts.txt |
| debugfs-umount | True | 0 | ok | native/debugfs-umount.txt |
| mounts-after | True | 0 | ok | native/mounts-after.txt |
| post-selftest | True | 0 | ok | native/post-selftest.txt |
| post-status | True | 0 | ok | native/post-status.txt |

## Safety

- V1358 may temporarily mount debugfs if it is absent, then unmount it before exit.
- No debugfs file write, `cnss/dev_boot` write, platform bind/unbind, PCI rescan,
  PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect,
  credential handling, DHCP/routes, external ping, flash, boot image write,
  or partition write.

## Next

classify ICNSS/pci-msm platform entry options; do not use cnss/dev_boot
