# Native Init V1978 Android RIL QMI PID Attribution

## Summary

- Cycle: `V1978`
- Decision: `v1978-android-capture-rejected-degraded-or-pcie-mhi`
- Label: `android-capture-rejected-degraded-or-pcie-mhi`
- Pass: `False`
- Reason: Android capture was rejected because it is degraded or has pre-wlan0 PCIe/MHI/eSoC contamination
- Evidence: `tmp/wifi/v1978-android-ril-qmi-pid-attribution-handoff`

## Producer Attribution

| field | value |
| --- | --- |
| wlan_pd UP | 9.638521 |
| wlan0 | 15.110341 |
| contamination pcie-mhi/esoc/degraded257 | 30/0/False |
| libqmi events/send/rild-send | 3568/569/0 |
| pre-UP lead lookups | 5 |
| pre-UP WLFW lookups | 2 |
| attributed PIDs | 131 |
| pre-UP lead rild count | 0 |
| pre-UP lead unresolved count | 5 |
| task map present | True |
| process counts | {"unattributed": 5} |
| first lead lookup | {"line": "<...>-2393  [004] ....     8.955059: libqmi_get_service_list_lookup_call: (0x7166273eec) xport=0x0 xport_id=0x0 svc_id=0x2 idl_version=0x1 capacity_ptr=0x70e0462f5c list_ptr=0x70e04630a0 lookup_fn=0x7166277a30", "pid": 2393, "process": "unattributed", "rild": false, "service": "DMS", "svc_id": 2, "thread": "unattributed", "time": 8.955059} |

## Pre-UP Lead Rows

| time | pid | service | rild | process |
| --- | --- | --- | --- | --- |
| 8.955059 | 2393 | DMS | False | unattributed |
| 8.956217 | 2393 | DMS | False | unattributed |
| 9.401213 | 2393 | DMS | False | unattributed |
| 9.41313 | 2393 | DMS | False | unattributed |
| 9.416059 | 2393 | DMS | False | unattributed |

## Parser Chain

| parser | decision | label | pass | out_dir |
| --- | --- | --- | --- | --- |
| V1894 | v1894-android-pending-client-capture-contaminated-host-pass | android-pending-client-capture-contaminated | True | tmp/wifi/v1978-android-ril-qmi-pid-attribution-handoff/v1894-parser |
| V1888 | v1888-android-normal-capture-contaminated-host-pass | android-normal-capture-contaminated | True | tmp/wifi/v1978-android-ril-qmi-pid-attribution-handoff/v1888-parser |

## Scope

- Internal-modem Android-handoff producer measurement only; contaminated captures are explicitly rejected.
- Direct libqmi uprobes are pre-armed before `rild` starts, and V1978 adds live `/proc` PID/TGID attribution for libqmi trace threads.
- The result is a producer classifier, not a native Wi-Fi bring-up attempt.

## Safety

Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module, bounded evidence directory, and bounded tracefs uprobe/kprobe controls for observation. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or partition write beyond declared boot-image handoff/rollback.

## Rollback Gate

- native rollback selftest fail=0: `True`
- base handoff decision/pass: `v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass` / `True`
