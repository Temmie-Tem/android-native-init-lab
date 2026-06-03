# Native Init V1979 Android RIL QMI Strace QRTR

## Summary

- Cycle: `V1979`
- Decision: `v1979-android-capture-rejected-degraded-or-pcie-mhi`
- Label: `android-capture-rejected-degraded-or-pcie-mhi`
- Pass: `False`
- Reason: Android capture was rejected because it is degraded or has pre-wlan0 PCIe/MHI/eSoC contamination
- Evidence: `tmp/wifi/v1979-android-ril-qmi-strace-qrtr-handoff`

## Producer Attribution

| field | value |
| --- | --- |
| wlan_pd UP | 9.688596 |
| wlan0 | 15.088118 |
| contamination pcie-mhi/esoc/degraded257 | 30/0/False |
| libqmi events/send/rild-send | 3716/606/0 |
| daemon strace lines | {"cnss_daemon": 30, "pm_service": 174, "rild": 451} |
| daemon strace send/recv | {"cnss_daemon": {"recvmsg": 2, "sendmsg": 0}, "pm_service": {"recvmsg": 0, "sendmsg": 0}, "rild": {"recvmsg": 5, "sendmsg": 0}} |
| QRTR lookup cases | 9 |
| QRTR service cases | [] |
| unfiltered dmesg lines | 8958 |
| pre-UP lead lookups | 5 |
| pre-UP WLFW lookups | 2 |
| attributed PIDs | 135 |
| pre-UP lead rild count | 0 |
| pre-UP lead unresolved count | 0 |
| task map present | True |
| process counts | {"/system/vendor/bin/cnss-daemon -n -l": 5} |
| first lead lookup | {"line": "<...>-2777  [006] ....     8.671721: libqmi_get_service_list_lookup_call: (0x74acf15eec) xport=0x0 xport_id=0x0 svc_id=0x2 idl_version=0x1 capacity_ptr=0x74295fcf5c list_ptr=0x74295fd0a0 lookup_fn=0x74acf19a30", "pid": 2777, "process": "/system/vendor/bin/cnss-daemon -n -l", "rild": false, "service": "DMS", "svc_id": 2, "thread": "/system/vendor/bin/cnss-daemon -n -l", "time": 8.671721} |

## Pre-UP Lead Rows

| time | pid | service | rild | process |
| --- | --- | --- | --- | --- |
| 8.671721 | 2777 | DMS | False | /system/vendor/bin/cnss-daemon -n -l |
| 8.673411 | 2777 | DMS | False | /system/vendor/bin/cnss-daemon -n -l |
| 9.408949 | 2777 | DMS | False | /system/vendor/bin/cnss-daemon -n -l |
| 9.409324 | 2777 | DMS | False | /system/vendor/bin/cnss-daemon -n -l |
| 9.40983 | 2777 | DMS | False | /system/vendor/bin/cnss-daemon -n -l |

## Parser Chain

| parser | decision | label | pass | out_dir |
| --- | --- | --- | --- | --- |
| V1894 | v1894-android-pending-client-capture-contaminated-host-pass | android-pending-client-capture-contaminated | True | tmp/wifi/v1979-android-ril-qmi-strace-qrtr-handoff/v1894-parser |
| V1888 | v1888-android-normal-capture-contaminated-host-pass | android-normal-capture-contaminated | True | tmp/wifi/v1979-android-ril-qmi-strace-qrtr-handoff/v1888-parser |

## Scope

- Internal-modem Android-handoff producer measurement only; contaminated captures are explicitly rejected.
- Direct libqmi uprobes are pre-armed before `rild` starts; V1979 also attaches exact `sendmsg`/`recvmsg`/`sendto`/`recvfrom` strace to `rild`, `cnss-daemon`, and `pm-service` as soon as each process appears.
- QRTR enumeration uses only nameservice `NEW_LOOKUP`/`DEL_LOOKUP` control packets with no QMI payload.
- The result is a producer classifier, not a native Wi-Fi bring-up attempt.

## Safety

Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module, bounded evidence directory, bounded tracefs uprobe/kprobe controls, strace attach, and QRTR nameservice lookup/readback controls for observation. No QMI payload replay, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or partition write beyond declared boot-image handoff/rollback.

## Rollback Gate

- native rollback selftest fail=0: `True`
- base handoff decision/pass: `v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass` / `True`
