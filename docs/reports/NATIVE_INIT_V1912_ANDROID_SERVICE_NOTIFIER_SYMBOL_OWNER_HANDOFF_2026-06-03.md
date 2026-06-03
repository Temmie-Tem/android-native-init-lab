# Native Init V1912 Android Service-notifier Symbol-owner Handoff

- Cycle: `V1912`
- Type: rollbackable Android-good read-only kallsyms/module-owner capture
- Decision: `v1912-android-service-notifier-register-builtin-normal-stateup-pass`
- Label: `android-service-notifier-register-builtin-normal-stateup`
- Result: `PASS`
- Reason: normal Android state-up captured and service_notif_register_notifier is built into the kernel, not owned by a loadable module
- Evidence: `tmp/wifi/v1912-android-service-notifier-symbol-owner-handoff-live-20260603-220803`

## Android-good State-up

| field | value |
| --- | --- |
| service74/service180/wlan_pd/wlanmdsp/wlan0 | 1/1/2/10/15.379517 |
| wlfw service request | 3 |
| contamination pcie-mhi/esoc/degraded257 | 0/0/False |
| first service74 | [    7.374392]  [5: kworker/u16:10:  342] service-notifier: service_notifier_new_server: Connection established between QMI handle and 74 service |
| first wlan_pd | [    9.714467]  [5: kworker/u16:11:  343] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1 |

## Symbol Ownership

| field | value |
| --- | --- |
| service_notif_register_notifier count | 1 |
| owners | ["builtin"] |
| target lines | [{"symbol": "service_notif_register_notifier", "module": "builtin", "line": "0000000000000000 T service_notif_register_notifier"}] |
| related kallsyms lines | 50 |
| sys_modules | ["icnss", "qmi_rmnet", "service_locator", "subsystem_restart", "vservices", "vservices_serial", "wlan"] |

## Files

| field | value |
| --- | --- |
| base | tmp/wifi/v1912-android-service-notifier-symbol-owner-handoff-live-20260603-220803/android-postfs-evidence/a90-v1912-servnotif-owner |
| files | {"dmesg": true, "done": false, "kallsyms_related": true, "kallsyms_target": true, "modules": false, "owners": true, "props": true, "samples": true, "status": true, "sys_modules": true} |
| sample_count | 2 |
| status | A90_V1912_STATUS early 42.23<br>A90_V1521_STATUS early 42.23 |
| rollback selftest fail=0 | True |

## Safety Scope

Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module and bounded evidence directory. The module reads `/proc/kallsyms`, `/proc/modules`, `/sys/module`, dmesg, logcat, and properties. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, restart-PD request, tracefs write, or partition write beyond the declared boot-image handoff/rollback.

## Next

- If the owner is `builtin`, keep the trigger search on the internal-modem kernel/servreg publication edge and do not pivot to SDX50M/PCIe/GDSC.
- Do not attempt Wi-Fi credentials/connect/ping until native proves WLFW service69 and `wlan0`.
