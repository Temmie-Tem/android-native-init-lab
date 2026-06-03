# Native Init V1944 RILD Loader Gap Classifier

## Summary

- Cycle: `V1944`
- Type: host-only ELF/strings classifier over V1942 vendor-source
- Decision: `v1944-rild-dlopen-ril-impl-missing-from-v1942-source-host-pass`
- Label: `rild-dlopen-ril-impl-missing-from-v1942-source`
- Pass: `True`
- Reason: exported rild has dlopen/vendor.sec.rild.libpath/libsec/RIL_Init hints, but the likely RIL implementation library is not in the V1942 export; exported Samsung radio HAL artifacts do not directly reference libperipheral_client, so the PM-voter caller is likely in the dynamically loaded RIL implementation
- Evidence: `tmp/wifi/v1944-rild-loader-gap-classifier`

## Matrix

| area | value | detail |
| --- | --- | --- |
| rild present | True | bin/hw/rild |
| rild loader gap | True | dlopen + vendor.sec.rild.libpath + libsec + missing libsec-ril.so |
| no exported radio PM client user | True | pm_client symbols only in pm-service/libperipheral_client |
| rild needed | libc++.so, libc.so, libcutils.so, libdl.so, liblog.so, libm.so, libril_sem.so | readelf -d |
| missing likely impls | libqcrilNr.so, libreference-ril.so, libril-qc-qmi-1.so, libsec-ril-dsds.so, libsec-ril.so, libsecril-client.so | not copied by V1942 target set |

## RILD Loader Hints

| string |
| --- |
| dlopen |
| RIL_Init Stop, No libsec-ril |
| rilLibPath = %s |
| RIL_SAP_Init not defined or exported in %s: %s |
| dlopen failed: %s |
| RIL_SAP_Init |
| RIL_Init RIL_register completed |
| RIL_Init rilInit completed |
| RIL_Init starting sleep loop |
| vendor.sec.rild.libpath |
| RIL_Init not defined or exported in %s |
| RIL_Init argc = %d clientId = %s |
| RIL_Init |
| libsec |
| RIL_SAP_Init defined as null in %s. SAP Not usable |

## Needed Libraries

| path | readelf | needed |
| --- | --- | --- |
| bin/hw/rild | ok | libc++.so, libc.so, libcutils.so, libdl.so, liblog.so, libm.so, libril_sem.so |
| bin/pm-service | ok | libbinder.so, libc++.so, libc.so, libcutils.so, libdl.so, liblog.so, libm.so, libmdmdetect.so, libperipheral_client.so, libqmi_cci.so, libqmi_common_so.so, libqmi_csi.so, libqmi_encdec.so, libutils.so |
| lib64/libperipheral_client.so | ok | libbinder.so, libc++.so, libc.so, libcutils.so, libdl.so, liblog.so, libm.so, libmdmdetect.so, libutils.so |

## PM Client Symbol Owners

| path | readelf | sample |
| --- | --- | --- |
| bin/pm-service | ok | 9: 0000000000000000     0 OBJECT  GLOBAL DEFAULT  UND _ZN7android18IPeripheralManager10descriptorE \| 10: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND _ZN7android18IPeripheralManagerC2Ev \| 11: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND _ZN7android18IPeripheralManagerD0Ev \| 12: 0000000000000000     0 FUNC    GLOBAL DEFAULT  UND _ZN7android18IPeripheralManagerD1Ev |
| lib/libperipheral_client.so | ok | 100: 00005e29     6 FUNC    GLOBAL DEFAULT   14 _ZN7android16pm_client_unlockEPNS_23PeripheralManagerClientE \| 103: 00006919   336 FUNC    GLOBAL DEFAULT   14 pm_client_unregister \| 104: 0000bb8c     4 OBJECT  GLOBAL DEFAULT   22 _ZN7android18IPeripheralManager10descriptorE \| 105: 0000a128   188 OBJECT  GLOBAL DEFAULT   16 _ZTCN7android19BnPeripheralManagerE0_NS_11BnInterfaceINS_18IPeripheralManagerEEE |
| lib64/libperipheral_client.so | ok | 108: 0000000000006700    64 FUNC    GLOBAL DEFAULT   14 _ZN7android18ServerDiedNotifierC1EPNS_23PeripheralManagerClientE \| 109: 000000000000612c  1492 FUNC    GLOBAL DEFAULT   14 _ZN7android19pm_register_connectEPNS_23PeripheralManagerClientEP8pm_event \| 110: 000000000000d928     8 OBJECT  GLOBAL DEFAULT   23 _ZN7android18IPeripheralManager12default_implE \| 111: 0000000000006740    48 FUNC    GLOBAL DEFAULT   14 _ZN7android18ServerDiedNotifierC2EPNS_23PeripheralManagerClientE |

## Interpretation

- V1943 narrowed `QCRIL` to a `PerMgrSrv` client-name vote, not a standalone QTI qcrild artifact.
- V1944 narrows the missing source object further: current exported rild/radio HAL files do not contain the PM-client caller; `rild` expects a dynamically loaded RIL implementation via `vendor.sec.rild.libpath`/`libsec`.
- Next bounded read-only step: export the actual RIL implementation path (`libsec-ril.so` family and related init/property evidence) from `sda29`, then repeat the PM-client symbol/string/callgraph scan. Do not execute rild/radio/QCRIL.

## Inputs

- V1942 manifest: `tmp/wifi/v1942-qcril-radio-vendor-artifact-export/manifest.json`
- V1942 vendor source: `tmp/wifi/v1942-qcril-radio-vendor-artifact-export/vendor-source`
- V1943 report: `docs/reports/NATIVE_INIT_V1943_QCRIL_OWNER_CLASSIFIER_2026-06-04.md`

## Safety Scope

Host-only parser over already exported files. No live device command, flash, reboot, rild/radio/QCRIL start, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or restart-PD request was used.
