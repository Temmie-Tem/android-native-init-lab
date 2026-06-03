# Native Init V1811 Post-PM Lower Handoff Klog Handoff

## Summary

- Cycle: `V1811`
- Type: one-run rollbackable WLAN-PD post-PM lower handoff klog discriminator
- Decision: `v1811-servnotif-klog-progress-still-uninit-rollback-pass`
- Result: PASS
- Reason: service-notifier klog count was present while QRTR service-notifier state remained uninit
- Evidence: `tmp/wifi/v1811-post-pm-lower-handoff-klog-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- post-PM lower handoff klog label: `servnotif-klog-progress-still-uninit`
- post-PM lower-state label: `stable-mdm3-offlining`
- PM-client return label: `pm-client-return-success`
- PM-service projection label: `list-commit-progress`
- safety ok: `True`

## Klog Samples

- contract/safety: `True` / `True`
- sysmon counts positive/increased: `1,1,1` / `True` / `False`
- service 180 counts positive/increased: `1,1,1` / `True` / `False`
- service 74 counts positive/increased: `0,0,0` / `False` / `False`
- `after_holder_start` counts sysmon/180/74: `1` / `1` / `0`
- `after_holder_start` syslog/errno/safety: `1` / `0` / `1,1,1`
- `after_holder_start` last sysmon: `<6>[    5.362812]  [1:  kworker/u16:8:  292] sysmon-qmi: ssctl_new_server: Connection established between QMI handle and modem's SSCTL service`
- `after_holder_start` last service74: `missing`
- `after_early_listener` counts sysmon/180/74: `1` / `1` / `0`
- `after_early_listener` syslog/errno/safety: `1` / `0` / `1,1,1`
- `after_early_listener` last sysmon: `<6>[    5.362812]  [1:  kworker/u16:8:  292] sysmon-qmi: ssctl_new_server: Connection established between QMI handle and modem's SSCTL service`
- `after_early_listener` last service74: `missing`
- `after_post_listener_window` counts sysmon/180/74: `1` / `1` / `0`
- `after_post_listener_window` syslog/errno/safety: `1` / `0` / `1,1,1`
- `after_post_listener_window` last sysmon: `<6>[    5.362812]  [1:  kworker/u16:8:  292] sysmon-qmi: ssctl_new_server: Connection established between QMI handle and modem's SSCTL service`
- `after_post_listener_window` last service74: `missing`

## Service-notifier State

- early/late response state: `uninit` / `uninit`
- early/late response success: `1` / `1`
- early/late indication seen: `0` / `0`
- still uninit: `True`

## PM-client Return Values

- register/connect/return-path rc: `0` / `0` / `0`
- return fetchargs seen/nonzero: `True` / `False`

## Lower-state Samples

- sample total: `13`
- mdm3 states: `OFFLINING`
- mdm status IRQ totals/increased: `0,0,0,0,0,0,0,0,0,0,0,0,0` / `False`
- MHI counts/pipes/present: `0,0,0,0,0,0,0,0,0,0,0,0,0` / `0,0,0,0,0,0,0,0,0,0,0,0,0` / `False`
- wlan0 samples/present: `0,0,0,0,0,0,0,0,0,0,0,0,0` / `False`
- WLFW service69 progress: `False`
- `after_holder_start` begin/end/count/interval: `sample-only` / `sample-only` / `` / ``
- `after_holder_start` first mdm3/MHI/wlan0/irq: `OFFLINING` / `0` pipe `0` / `0` / `0`
- `after_holder_start` last mdm3/MHI/wlan0/irq: `OFFLINING` / `0` pipe `0` / `0` / `0`
- `post_listener_window` begin/end/count/interval: `1` / `1` / `12` / `500`
- `post_listener_window` first mdm3/MHI/wlan0/irq: `OFFLINING` / `0` pipe `0` / `0` / `0`
- `post_listener_window` last mdm3/MHI/wlan0/irq: `OFFLINING` / `0` pipe `0` / `0` / `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1810/dev/__properties__`
- Transport: `serial-uudecode-tar-gz`
- Uploaded files/bytes: `22` / `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- The route did not open `/dev/subsys_esoc0`, did not fake ONLINE, and did not write PMIC/GPIO/GDSC controls.
- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, `boot_wlan`, restart-PD request, forced RC1, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label; do not proceed to Wi-Fi HAL/scan/connect unless lower progress reaches WLFW/wlan0 readiness first.
