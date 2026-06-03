# Native Init V1935 Android/Native Service69 Wait-return Diff

## Summary

- Cycle: `V1935`
- Decision: `v1935-native-wlfw-service69-wait-return-missing-host-pass`
- Label: `native-wlfw-service69-wait-return-missing`
- Pass: `True`
- Reason: Android-good proves WLFW service69 wait-return/found-service/init-return in the clean internal-modem boot, while native reaches the same WLFW lookup and wait call but never receives the service69 wait return
- Evidence: `tmp/wifi/v1935-android-native-service69-wait-return-diff`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | native-wlfw-service69-wait-return-missing | Android-good proves WLFW service69 wait-return/found-service/init-return in the clean internal-modem boot, while native reaches the same WLFW lookup and wait call but never receives the service69 wait return |
| Android normal | True | wlan_pd=9.580204 wlan0=15.342477 clean=True |
| Android service69 | True/4/1/1 | threads=['1282'] new69=False |
| Native prereq | True | lookup69=True wait_call=True thread=637 |
| Native missing | True | found=0 wait_return=False init_return=False wlan_pd=False wlanmdsp=False wlan0=False |

## Edge Lines

| edge | line |
| --- | --- |
| Android first lookup69 | <...>-1282  [004] ....     8.733971: libqmi_get_service_list_lookup_call: (0x726c014eec) xport=0x0 xport_id=0x0 svc_id=0x45 idl_version=0x1 capacity_ptr=0x71e340399c list_ptr=0x71e3403ae0 lookup_fn=0x726c018a30 |
| Android first wait return | <...>-1282  [006] ....     9.582752: libqmi_wait_return: (0x726c016908) |
| Android first found | <...>-1282  [006] ....     9.582904: libqmi_get_service_list_lookup_ret: (0x726c014ef0) found=0x1 list=0x71e3403ae0 capacity_ptr=0x71e3403a14 count_ptr=0x71e3403a10 offset=0x0 xport_index=0x0 |
| Android first init return | <...>-1282  [006] ....     9.584217: libqmi_init_return: (0x726c016970) rc=0x0 |
| Native first lookup69 | cnss-daemon-637   [003] ....     6.783727: libqmi_get_service_list_lookup_call: (0x7fa9f6deec) xport=0x0 xport_id=0x0 svc_id=0x45 idl_version=0x1 capacity_ptr=0x7f1f4e199c list_ptr=0x7f1f4e1ae0 lookup_fn=0x7fa9f71a30 |
| Native first lookup ret | cnss-daemon-637   [003] ....     6.784757: libqmi_get_service_list_lookup_ret: (0x7fa9f6def0) found=0x0 list=0x7f1f4e1ae0 capacity_ptr=0x7f1f4e1a14 count_ptr=0x7f1f4e1a10 offset=0x0 xport_index=0x0 |
| Native first wait return | none |
| Native first init return | none |

## Interpretation

- V1934 changes the comparison target: the reliable Android-positive signal is not decoded `new-server69`; it is the WLFW thread's service69 wait returning, followed by `found=0x1` service-list lookup and `qmi_client_init_instance` return.
- Native V1930 reaches the same WLFW service69 lookup/wait call, but the WLFW thread stays outstanding with `found=0`, no wait return, no init return, and no WLAN-PD/WLFW69/wlanmdsp/wlan0.
- The next live native unit should instrument the remote SERVREG/WLAN-PD state-up to WLFW service69 wait-return edge. Do not pivot to pm-service msg22, SDX50M/eSoC/PCIe/GDSC, or Wi-Fi HAL/connect.

## Inputs

- Android: `tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/manifest.json`
- Native: `tmp/wifi/v1930-libqmi-service-id-integration/manifest.json`

## Safety Scope

Host-only manifest diff. No live device command, flash, reboot, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
