# Native Init V1934 Android Libqmi Service69 Positive Control

## Summary

- Cycle: `V1934`
- Decision: `v1934-android-libqmi-service69-wait-return-positive-control-rollback-pass`
- Label: `android-libqmi-service69-wait-return-positive-control`
- Pass: `True`
- Reason: normal Android state-up captured WLFW service 0x45 lookup, wait return, successful service-list lookup, and qmi_client_init_instance return; decoded new-server69 was not exposed by the transport fetch
- Evidence: `tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139`

## Android Normal Edge

| field | value |
| --- | --- |
| android_dir | tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/android-postfs-evidence/a90-v1934-libqmi69 |
| recovered/sampler_done | True/False |
| PM vote/WLFW request/wlan_pd/wlanmdsp/wlan0 | 2/5/2/20/15.342477 |
| contamination pcie-mhi/esoc/degraded257 | 0/0/False |
| libqmi trace lines | 2813 |
| libqmi lookup service IDs | ["0x1", "0x2", "0x3", "0x4", "0x5", "0x7", "0x9", "0xa", "0xb", "0xc", "0x10", "0x11", "0x16", "0x18", "0x1a", "0x22", "0x2a", "0x2f", "0x39", "0x40", "0x44", "0x45", "0xe3", "0xe8", "0x190"] |
| libqmi new-server service IDs | ["0x1", "0x2", "0x3", "0x4", "0x5"] |
| libqmi lookup69/found/wait-return/init-return/new69 | True/4/1/1/False |
| first service69 lookup | <...>-1282  [004] ....     8.733971: libqmi_get_service_list_lookup_call: (0x726c014eec) xport=0x0 xport_id=0x0 svc_id=0x45 idl_version=0x1 capacity_ptr=0x71e340399c list_ptr=0x71e3403ae0 lookup_fn=0x726c018a30 |
| first service69 found | <...>-1282  [006] ....     9.582904: libqmi_get_service_list_lookup_ret: (0x726c014ef0) found=0x1 list=0x71e3403ae0 capacity_ptr=0x71e3403a14 count_ptr=0x71e3403a10 offset=0x0 xport_index=0x0 |
| first service69 wait return | <...>-1282  [006] ....     9.582752: libqmi_wait_return: (0x726c016908) |
| first service69 init return | <...>-1282  [006] ....     9.584217: libqmi_init_return: (0x726c016970) rc=0x0 |
| libqmi summary | {"armed": "1", "hit_count": "2813", "libqmi_service": "/vendor/lib64/libqmi_cci.so", "lookup69_hit_count": "6", "new69_hit_count": "0", "result": "libqmi_uprobe_attempted_prearmed", "tracefs": "/sys/kernel/tracing"} |
| libqmi trace | tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/android-postfs-evidence/a90-v1934-libqmi69/libqmi-uprobe-trace.txt |

## Parser Chain

| parser | decision | label | pass | out_dir |
| --- | --- | --- | --- | --- |
| V1894 | v1894-android-stateup-pending-client-observability-gap-host-pass | android-stateup-pending-client-observability-gap | True | tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/v1894-parser |
| V1888 | v1888-android-stateup-msg22-observability-gap-host-pass | android-stateup-without-msg22-log-observability-gap | True | tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/v1888-parser |

## Comparison Target

- Native V1930 already saw WLFW lookup for QMI service `0x45` but no `new-server69`.
- Android-good shows the missing positive edge as WLFW service69 wait return plus found service-list/init return; the decoded transport new-server fetch only exposed low transport IDs.
- Next native unit should target why the native WLFW thread never receives this wait-return/found-service edge, still below HAL and not SDX50M/eSoC/PCIe/GDSC.

## Rollback Gate

- native rollback selftest fail=0: `True`
- base handoff decision/pass: `v1521-magisk-postfs-partial-android-lower-no-pre-window-rollback-pass` / `True`

## Steps

| step | status | rc | duration | file |
| --- | --- | --- | --- | --- |
| capture-android-dmesg-filtered | ok | 0 | 0.000s | steps/capture-android-dmesg-filtered.txt |
| cleanup-v1521-module-android | ok | 0 | 0.000s | steps/cleanup-v1521-module-android.txt |
| cleanup-v1521-module-recovery-best-effort | ok | 0 | 0.000s | steps/cleanup-v1521-module-recovery-best-effort.txt |
| flash-android-boot | ok | 0 | 0.000s | steps/flash-android-boot.txt |
| hide-menu | ok | 0 | 0.000s | steps/hide-menu.txt |
| install-v1899-module-android-su | ok | 0 | 0.000s | steps/install-v1899-module-android-su.txt |
| native-recovery | ok | 0 | 0.000s | steps/native-recovery.txt |
| native-status-redacted | ok | 0 | 0.000s | steps/native-status-redacted.txt |
| native-version-redacted | ok | 0 | 0.000s | steps/native-version-redacted.txt |
| post-rollback-native-status-redacted | ok | 0 | 0.000s | steps/post-rollback-native-status-redacted.txt |
| prepare-v1899-magisk-module | ok | 0 | 0.000s | steps/prepare-v1899-magisk-module.txt |
| pull-v1521-sampler-evidence | ok | 0 | 0.000s | steps/pull-v1521-sampler-evidence.txt |
| push-android-boot | ok | 0 | 0.000s | steps/push-android-boot.txt |
| push-v1899-module-prop-android | ok | 0 | 0.000s | steps/push-v1899-module-prop-android.txt |
| push-v1899-post-fs-data-android | ok | 0 | 0.000s | steps/push-v1899-post-fs-data-android.txt |
| push-v1899-sepolicy-android | ok | 0 | 0.000s | steps/push-v1899-sepolicy-android.txt |
| push-v1899-strace-android | ok | 0 | 0.000s | steps/push-v1899-strace-android.txt |
| readback-android-boot | ok | 0 | 0.000s | steps/readback-android-boot.txt |
| reboot-android-with-v1521-module | ok | 0 | 0.000s | steps/reboot-android-with-v1521-module.txt |
| reboot-android | ok | 0 | 0.000s | steps/reboot-android.txt |
| reboot-recovery-for-rollback | ok | 0 | 0.000s | steps/reboot-recovery-for-rollback.txt |
| remote-android-sha | ok | 0 | 0.000s | steps/remote-android-sha.txt |
| restore-native | ok | 0 | 0.000s | steps/restore-native.txt |
| wait-android-boot-complete-for-install | ok | 0 | 0.000s | steps/wait-android-boot-complete-for-install.txt |
| wait-android-ready-for-module-push | ok | 0 | 0.000s | steps/wait-android-ready-for-module-push.txt |
| wait-android-second | ok | 0 | 0.000s | steps/wait-android-second.txt |
| wait-android | ok | 0 | 0.000s | steps/wait-android.txt |
| wait-recovery | ok | 0 | 0.000s | steps/wait-recovery.txt |
| wait-rollback-recovery | ok | 0 | 0.000s | steps/wait-rollback-recovery.txt |
| wait-v1521-sampler-done | fail | 1 | 0.000s | steps/wait-v1521-sampler-done.txt |

## Safety

Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module, bounded evidence directory, and bounded tracefs uprobe/kprobe controls for CNSS/WLFW/QRTR/libqmi observation. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or partition write beyond declared boot-image handoff/rollback.
