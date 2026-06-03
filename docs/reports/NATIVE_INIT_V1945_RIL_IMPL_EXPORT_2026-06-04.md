# Native Init V1945 RIL Implementation Export

## Summary

- Cycle: `V1945`
- Type: live read-only bounded export from `sda29` for rild dynamic RIL implementation
- Decision: `v1945-ril-impl-artifacts-exported-readonly-pass`
- Label: `ril-impl-artifacts-exported-readonly`
- Pass: `True`
- Reason: bounded dynamic RIL implementation artifacts were exported read-only for host callgraph analysis
- Evidence: `tmp/wifi/v1945-ril-impl-export`

## Matrix

| area | value | detail |
| --- | --- | --- |
| version matches | True | A90 Linux init 0.9.68 (v724) |
| post selftest fail=0 | True | tmp/wifi/v1945-ril-impl-export/native/commands/post-selftest.txt |
| cleanup ok | True | /tmp/a90-v1945-live-20260603-183338/vendor |
| target count | 25 | direct libsec/secril/sitril plus bounded directory matches |
| pulled files | 11 | 6431382 bytes |
| skip libs | True | direct RIL artifacts only when true |

## Pulled RIL Implementation Candidates

| path | size | sha256 prefix | reason |
| --- | --- | --- | --- |
| lib64/libsec-ril.so | 5596160 | b61f6a910aaa56c3 | direct-target:chunked |
| lib64/libsecril-client.so | 40912 | 06ce1210bf7d38c9 | direct-target |
| lib/libsecril-client.so | 33708 | e66718c6f2950536 | direct-target |
| build.prop | 8913 | ec1f0d48d2412443 | direct-target |
| lib64/libril_sem.so | 716976 | e2758dd3d1803de2 | directory-match |
| lib64/librilutils.so | 15104 | 1104be52ae862964 | directory-match |
| lib64/libsec_semRil.so | 11336 | 3c5ac327f8198eb3 | directory-match |
| lib/libsec_semRil.so | 5608 | f5ec62f4e0fe2897 | directory-match |
| etc/init/init.vendor.rilcarrier.rc | 245 | 638dbcb8d6f9d52a | directory-match |
| etc/init/init.vendor.rilchip.rc | 1571 | f9c9b9abaf094556 | directory-match |
| etc/init/init.vendor.rilcommon.rc | 849 | f198a1f6cb1caa33 | directory-match |

## Property / Loader Hits

| path | mode | hit count | sample |
| --- | --- | --- | --- |
| lib64/libsec-ril.so | strings | 12 | PeripheralInfo \| _ZN9ModemBoot21PeripheralManagerInitEiPc \| _ZN9ModemBoot21PeripheralManagerVoteEi \| _ZN9ModemBoot23PeripheralManagerDeinitEv |
| build.prop | text | 1 | vendor.sec.rild.libpath=/vendor/lib64/libsec-ril.so |

## Missing / Skipped Sample

| path | reason |
| --- | --- |
| lib64/libsec-ril-dsds.so | stat-failed |
| lib64/libsec-ril-shannon.so | stat-failed |
| lib64/libsitril-client.so | stat-failed |
| lib64/libsitril.so | stat-failed |
| lib/libsec-ril.so | stat-failed |
| lib/libsec-ril-dsds.so | stat-failed |
| lib/libsec-ril-shannon.so | stat-failed |
| lib/libsitril-client.so | stat-failed |
| lib/libsitril.so | stat-failed |
| etc/init/rild.rc | stat-failed |
| etc/init/init.rilcommon.rc | stat-failed |
| etc/init/init.rilchip.rc | stat-failed |
| etc/init/vendor.rild.rc | stat-failed |
| etc/prop.default | stat-failed |

## Interpretation

- This keeps V1944 bounded: observe the `libsec-ril*`/secril/sitril implementation candidates and related RIL rc/property evidence only.
- Next host-only step: run the V1944 PM-client symbol/string/callgraph scan over these exported RIL implementation artifacts, without executing rild/radio/QCRIL.

## Safety Scope

- Temporary `sda29` mount only, exact `ext4 ro,noload`.
- No vendor/firmware/partition write, no remount-write, no daemon execution.
- No `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.
