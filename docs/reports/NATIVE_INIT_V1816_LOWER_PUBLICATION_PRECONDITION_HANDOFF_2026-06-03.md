# Native Init V1816 Lower Publication Precondition Handoff

## Summary

- Cycle: `V1816`
- Type: one-run rollbackable lower publication precondition discriminator
- Decision: `v1816-service74-raw-absent-preconditions-visible-rollback-pass`
- Result: PASS
- Reason: service 180 and lower precondition klogs were visible, but raw service 74 and wlan_pd text remained absent
- Evidence: `tmp/wifi/v1816-lower-publication-precondition-handoff`
- Rollback attempt: `from-native`
- Rollback ok: `True`

## Gate Label

- lower publication label: `service74-raw-absent-preconditions-visible`
- service74 raw label: `service74-raw-absent`
- PM-client return label: `pm-client-return-success`
- lower-state label: `stable-mdm3-offlining`
- safety ok: `True`

## Precondition Counters

- pd-mapper/subsys/pil/qmi/wlfw: `0,0,0` / `9,10,10` / `5,5,5` / `7,7,7` / `30,30,30`
- positives pd-mapper/subsys/pil/qmi/wlfw: `False` / `True` / `True` / `True` / `True`
- service180/service74/wlan_pd raw: `1,1,1` / `0,0,0` / `0,0,0`
- wlan_pd raw positive: `False`
- Broad WLFW text is precondition context only; WLFW service 69 or `wlan0` are the lower-progress gates.
- `after_holder_start` pd-mapper/subsys/pil/qmi/wlfw: `0` / `9` / `5` / `7` / `30`
- `after_holder_start` last qmi/wlfw/wlan_pd: `<6>[    5.314553]  [2:  kworker/u16:9:  297] sysmon-qmi: ssctl_new_server: Connection established between QMI handle and modem's SSCTL service` / `<6>[    1.926037]  [7:a90_android_exe:  546] trace_uprobe: Event a90cnss/wlfw_worker_pthread_create_success doesn't exist.` / `missing`
- `after_early_listener` pd-mapper/subsys/pil/qmi/wlfw: `0` / `10` / `5` / `7` / `30`
- `after_early_listener` last qmi/wlfw/wlan_pd: `<6>[    5.314553]  [2:  kworker/u16:9:  297] sysmon-qmi: ssctl_new_server: Connection established between QMI handle and modem's SSCTL service` / `<6>[    1.926037]  [7:a90_android_exe:  546] trace_uprobe: Event a90cnss/wlfw_worker_pthread_create_success doesn't exist.` / `missing`
- `after_post_listener_window` pd-mapper/subsys/pil/qmi/wlfw: `0` / `10` / `5` / `7` / `30`
- `after_post_listener_window` last qmi/wlfw/wlan_pd: `<6>[    5.314553]  [2:  kworker/u16:9:  297] sysmon-qmi: ssctl_new_server: Connection established between QMI handle and modem's SSCTL service` / `<6>[    1.926037]  [7:a90_android_exe:  546] trace_uprobe: Event a90cnss/wlfw_worker_pthread_create_success doesn't exist.` / `missing`

## Lower State

- early/late service-notifier state: `uninit` / `uninit`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- PM-client register/connect/return-path rc: `0` / `0` / `0`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1815/dev/__properties__`
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
