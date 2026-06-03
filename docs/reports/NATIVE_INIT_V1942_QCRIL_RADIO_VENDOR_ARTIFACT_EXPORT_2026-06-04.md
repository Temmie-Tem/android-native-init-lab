# Native Init V1942 QCRIL/Radio Vendor Artifact Export

## Summary

- Cycle: `V1942`
- Type: live read-only bounded vendor artifact export from `sda29`
- Decision: `v1942-qcril-radio-artifacts-exported-readonly-pass`
- Label: `qcril-radio-artifacts-exported-readonly`
- Pass: `True`
- Reason: bounded QCRIL/radio/peripheral vendor artifacts were exported read-only for host/source comparison
- Evidence: `tmp/wifi/v1942-qcril-radio-vendor-artifact-export`

## Matrix

| area | value | detail |
| --- | --- | --- |
| version matches | True | A90 Linux init 0.9.68 (v724) |
| post selftest fail=0 | True | tmp/wifi/v1942-qcril-radio-vendor-artifact-export/native/commands/post-selftest.txt |
| cleanup ok | True | /tmp/a90-v1942-live-20260603-182043/vendor |
| target count | 33 | direct targets plus bounded directory matches |
| pulled files | 12 | 2762616 bytes |
| skip libs | True | direct artifacts only when true |
| interesting string files | 3 | host strings over copied artifacts only |

## Pulled QCRIL/Radio/Peripheral Artifacts

| path | size | sha256 prefix | reason |
| --- | --- | --- | --- |
| bin/pm-service | 54888 | 0ef4d72ab242e2e3 | direct-target |
| lib64/libperipheral_client.so | 55648 | e92e05976d7c04c0 | direct-target |
| lib/libperipheral_client.so | 39984 | ec6814abb0835c01 | direct-target |
| bin/hw/rild | 16096 | 50859c33f9ff94c6 | directory-match |
| lib64/libril_sem.so | 716976 | e2758dd3d1803de2 | directory-match |
| lib64/librilutils.so | 15104 | 1104be52ae862964 | directory-match |
| lib64/vendor.samsung.hardware.radio.bridge@2.0.so | 174464 | 4e8e2b80297b6705 | directory-match |
| lib64/vendor.samsung.hardware.radio.bridge@2.1.so | 90536 | cc4d6f938aa75b5d | directory-match |
| lib64/vendor.samsung.hardware.radio.channel@2.0.so | 122784 | fbf9bd0d10dd24ba | directory-match |
| lib64/vendor.samsung.hardware.radio@2.0.so | 549784 | 42825dd132ca71b0 | directory-match |
| lib64/vendor.samsung.hardware.radio@2.1.so | 446232 | fa03843552c3ca73 | directory-match |
| lib64/vendor.samsung.hardware.radio@2.2.so | 480120 | ecc6a79d8fe0223f | directory-match |

## Host String Hits

| path | hit count | status | sample |
| --- | --- | --- | --- |
| bin/pm-service | 28 | ok | _ZN7android11BnInterfaceINS_18IPeripheralManagerEE10onAsBinderEv \| _ZN7android18IPeripheralManager10descriptorE \| _ZN7android18IPeripheralManagerC2Ev |
| lib64/libperipheral_client.so | 47 | ok | _ZN7android16pm_client_unlockEPNS_23PeripheralManagerClientE \| _ZN7android18IPeripheralManager11asInterfaceERKNS_2spINS_7IBinderEEE \| _ZN7android18ServerDiedNotifierC1EPNS_23PeripheralManagerClientE |
| lib/libperipheral_client.so | 54 | ok | _ZN7android16pm_client_unlockEPNS_23PeripheralManagerClientE \| _ZN7android18IPeripheralManager11asInterfaceERKNS_2spINS_7IBinderEEE \| _ZN7android18ServerDiedNotifierC1EPNS_23PeripheralManagerClientE |

## ELF Dependency Samples

| path | readelf | needed sample |
| --- | --- | --- |
| none |  |  |

## Missing / Skipped Sample

| path | reason |
| --- | --- |
| bin/hw/vendor.qti.hardware.radio@1.0-service | stat-failed |
| bin/hw/vendor.qti.hardware.radio@1.1-service | stat-failed |
| bin/hw/vendor.qti.hardware.radio@1.2-service | stat-failed |
| bin/hw/vendor.qti.hardware.radio@1.3-service | stat-failed |
| bin/hw/vendor.qti.hardware.radio@1.4-service | stat-failed |
| bin/hw/vendor.qti.hardware.radio@1.5-service | stat-failed |
| bin/hw/vendor.qti.hardware.radio@1.6-service | stat-failed |
| bin/hw/vendor.samsung.hardware.radio@1.2-service | stat-failed |
| bin/qcrild | stat-failed |
| bin/rild | stat-failed |
| lib64/libqcrilNr.so | stat-failed |
| lib64/libqcrilFramework.so | stat-failed |
| lib64/libqcrilDataModule.so | stat-failed |
| lib64/libril-qc-hal-qmi.so | stat-failed |
| lib64/libril-qcril-hook-oem.so | stat-failed |
| lib64/libperipheral_client_qcci.so | stat-failed |
| lib/libqcrilNr.so | stat-failed |
| lib/libqcrilFramework.so | stat-failed |
| lib/libril-qc-hal-qmi.so | stat-failed |
| lib/libril-qcril-hook-oem.so | stat-failed |
| lib/libperipheral_client_qcci.so | stat-failed |

## Interpretation

- This is source/diff evidence only; no QCRIL/radio daemon was executed on native.
- The export keeps QCRIL as a read-only comparison lead because Android's QCRIL vote remains SDX50M-coupled in V1941.
- Next host-only step: disassemble/string-diff the exported QCRIL/peripheral artifacts against the Android PM voter window and isolate any internal-modem WLAN-PD servreg/SSCTL producer action that is not SDX50M/eSoC/PCIe coupled.

## Safety Scope

- Temporary `sda29` mount only, exact `ext4 ro,noload`.
- No vendor/firmware/partition write, no remount-write, no daemon execution.
- No `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
