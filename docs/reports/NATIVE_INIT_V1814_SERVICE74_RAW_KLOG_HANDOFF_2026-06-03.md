# Native Init V1814 Service-notifier 74 Raw Klog Handoff

## Summary

- Cycle: `V1814`
- Type: one-run rollbackable service-notifier 74 raw klog discriminator
- Decision: `v1814-service74-raw-absent-rollback-pass`
- Result: PASS
- Reason: service 180 was present, but raw service 74 text and exact service 74 count remained absent
- Evidence: `tmp/wifi/v1814-service74-raw-klog-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- service74 raw klog label: `service74-raw-absent`
- lower handoff klog label: `servnotif-klog-progress-still-uninit`
- PM-client return label: `pm-client-return-success`
- lower-state label: `stable-mdm3-offlining`
- safety ok: `True`

## Raw Klog Counters

- raw service-notifier/new-server/qmi counts: `1,1,1` / `1,1,1` / `2,2,2`
- raw service180/service74/wlan_pd counts: `1,1,1` / `0,0,0` / `0,0,0`
- raw service74 positive/increased: `False` / `False`
- exact service180/service74 counts: `1,1,1` / `0,0,0`
- `after_holder_start` raw notifier/new/qmi: `1` / `1` / `2`
- `after_holder_start` raw 180/74/wlan_pd: `1` / `0` / `0`
- `after_holder_start` last 180: `<6>[    5.389388]  [3:  kworker/u16:9:  297] service-notifier: service_notifier_new_server: Connection established between QMI handle and 180 service`
- `after_early_listener` raw notifier/new/qmi: `1` / `1` / `2`
- `after_early_listener` raw 180/74/wlan_pd: `1` / `0` / `0`
- `after_early_listener` last 180: `<6>[    5.389388]  [3:  kworker/u16:9:  297] service-notifier: service_notifier_new_server: Connection established between QMI handle and 180 service`
- `after_post_listener_window` raw notifier/new/qmi: `1` / `1` / `2`
- `after_post_listener_window` raw 180/74/wlan_pd: `1` / `0` / `0`
- `after_post_listener_window` last 180: `<6>[    5.389388]  [3:  kworker/u16:9:  297] service-notifier: service_notifier_new_server: Connection established between QMI handle and 180 service`

## Service-notifier And Lower State

- early/late state: `uninit` / `uninit`
- early/late indication seen: `0` / `0`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`

## PM-client Return Values

- register/connect/return-path rc: `0` / `0` / `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1813/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The route did not open `/dev/subsys_esoc0`, did not fake ONLINE, and did not write PMIC/GPIO/GDSC controls.
- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, `boot_wlan`, restart-PD request, forced RC1, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
