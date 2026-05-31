# Native Init V1360 MHI Platform Surface Verifier Live

## Summary

- Cycle: `V1360`
- Type: live read-only verifier
- Decision: `v1360-mhi-surface-present-no-live-device`
- Result: PASS
- Script: `scripts/revalidation/native_wifi_mhi_platform_surface_verifier_live_v1360.py`
- Evidence:
  - `tmp/wifi/v1360-mhi-platform-surface-verifier-live/manifest.json`
  - `tmp/wifi/v1360-mhi-platform-surface-verifier-live/summary.md`
  - `tmp/wifi/v1360-mhi-platform-surface-verifier-live/native/`

## Decision

MHI-related sysfs/debugfs surface exists, but no live MHI device node is present

## Key Observations

| field | value |
| --- | --- |
| mounted_before | False |
| mounted_by_v1360 | True |
| mounted_during | True |
| mounted_after | False |
| cleanup_ok | True |
| dt_mhi_count | 875 |
| dt_has_mhi_1c0b000 | True |
| dt_has_esoc_ref | True |
| platform_mhi_any | True |
| platform_driver_any | True |
| pcie1_bound_pci_msm | True |
| mhi_bus_present | True |
| mhi_bus_device_count | 0 |
| mhi_bus_driver_count | 7 |
| pci_device_count | 0 |
| dev_mhi_count | 0 |
| class_mhi_count | 1 |
| debugfs_mhi_any | True |
| dmesg_mhi_seen | True |
| dmesg_pcie_link_seen | False |
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
| dt-mhi-nodes | True | 0 | ok | native/dt-mhi-nodes.txt |
| dt-esoc0-refs | True | 0 | ok | native/dt-esoc0-refs.txt |
| platform-mhi-devices | True | 0 | ok | native/platform-mhi-devices.txt |
| platform-mhi-drivers | True | 0 | ok | native/platform-mhi-drivers.txt |
| platform-mhi-find | True | 0 | ok | native/platform-mhi-find.txt |
| pcie1-platform-uevent | True | 0 | ok | native/pcie1-platform-uevent.txt |
| pcie1-platform-driver-readlink | True | 0 | ok | native/pcie1-platform-driver-readlink.txt |
| mhi-bus-tree | True | 0 | ok | native/mhi-bus-tree.txt |
| mhi-bus-devices | True | 0 | ok | native/mhi-bus-devices.txt |
| mhi-bus-drivers | True | 0 | ok | native/mhi-bus-drivers.txt |
| pci-bus-devices | True | 0 | ok | native/pci-bus-devices.txt |
| dev-mhi-nodes | True | 0 | ok | native/dev-mhi-nodes.txt |
| class-mhi-surfaces | True | 0 | ok | native/class-mhi-surfaces.txt |
| debugfs-mhi-find | True | 0 | ok | native/debugfs-mhi-find.txt |
| debugfs-mhi-ls | True | 0 | ok | native/debugfs-mhi-ls.txt |
| proc-modules-mhi | True | 0 | ok | native/proc-modules-mhi.txt |
| dmesg-pcie-mhi-tail | True | 0 | ok | native/dmesg-pcie-mhi-tail.txt |
| debugfs-umount | True | 0 | ok | native/debugfs-umount.txt |
| mounts-after | True | 0 | ok | native/mounts-after.txt |
| post-selftest | True | 0 | ok | native/post-selftest.txt |
| post-status | True | 0 | ok | native/post-status.txt |

## Safety

- V1360 may temporarily mount debugfs if it is absent, then unmount it before exit.
- No debugfs/sysfs file write, platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC
  write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credential handling,
  DHCP/routes, external ping, flash, boot image write, or partition write.

## Next

classify the MHI surface ownership and whether it is upstream or downstream of pcie1 enumeration
