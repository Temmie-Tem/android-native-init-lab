# Native Init V1363 pci-msm Debugfs Surface Verifier Live

## Summary

- Cycle: `V1363`
- Type: live read-only verifier
- Decision: `v1363-pci-msm-debugfs-rc-control-candidate`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_pci_msm_debugfs_surface_verifier_live_v1363.py`
- Evidence:
  - `tmp/wifi/v1363-pci-msm-debugfs-surface-verifier-live/manifest.json`
  - `tmp/wifi/v1363-pci-msm-debugfs-surface-verifier-live/summary.md`
  - `tmp/wifi/v1363-pci-msm-debugfs-surface-verifier-live/native/`

## Decision

pci-msm debugfs exists and exposes enumerate/RC-selection-like read-only surface names

## Key Observations

| field | value |
| --- | --- |
| mounted_before | False |
| mounted_by_v1363 | True |
| mounted_during | True |
| mounted_after | False |
| cleanup_ok | True |
| pci_msm_present | True |
| enumerate_name_seen | True |
| rc_select_seen | False |
| boot_option_seen | True |
| linkup_or_power_seen | True |
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
| pci-msm-ls | True | 0 | ok | native/pci-msm-ls.txt |
| pci-msm-find | True | 0 | ok | native/pci-msm-find.txt |
| pci-msm-file-heads | True | 0 | ok | native/pci-msm-file-heads.txt |
| pci-msm-dmesg-tail | True | 0 | ok | native/pci-msm-dmesg-tail.txt |
| debugfs-umount | True | 0 | ok | native/debugfs-umount.txt |
| mounts-after | True | 0 | ok | native/mounts-after.txt |
| post-selftest | True | 0 | ok | native/post-selftest.txt |
| post-status | True | 0 | ok | native/post-status.txt |

## Safety

- V1363 may temporarily mount debugfs if it is absent, then unmount it before exit.
- No debugfs/sysfs write, pci-msm debugfs control write, platform bind/unbind,
  PCI rescan, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL,
  scan/connect, credential handling, DHCP/routes, external ping, flash,
  boot image write, or partition write.

## Next

V1364 host-only source/kallsyms contract for pci-msm debugfs RC1 control before any write
