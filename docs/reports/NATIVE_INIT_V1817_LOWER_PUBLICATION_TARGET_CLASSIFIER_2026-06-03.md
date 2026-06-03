# Native Init V1817 Lower Publication Target Classifier

## Summary

- Cycle: `V1817`
- Type: host-only classifier over V1816 lower publication preconditions and Android-positive baselines
- Decision: `v1817-wlan-pd-service-locator-visibility-target-host-pass`
- Result: PASS
- Reason: Native has MSS/subsys/PIL/QMI context but no pd-mapper text, wlan_pd text, service-notifier 74, WLFW service 69, or wlan0 while Android-good has service locator, service 74, wlan_pd, qmi-server, WLFW, and wlan0
- Evidence: `tmp/wifi/v1817-lower-publication-target-classifier`
- Source evidence: `tmp/wifi/v1816-lower-publication-precondition-handoff`

## Native V1816 Shape

- V1816 decision: `v1816-service74-raw-absent-preconditions-visible-rollback-pass`
- labels lower-publication/service74/PM-client/handoff/lower-state: `service74-raw-absent-preconditions-visible` / `service74-raw-absent` / `pm-client-return-success` / `servnotif-klog-progress-still-uninit` / `stable-mdm3-offlining`
- PM-client register/connect/return rc: `0` / `0` / `0`
- raw service180/service74/wlan_pd counts: `1,1,1` / `0,0,0` / `0,0,0`
- lower precondition counts pd-mapper/subsys/pil/qmi/wlfw: `0,0,0` / `9,10,10` / `5,5,5` / `7,7,7` / `30,30,30`
- lower precondition positives pd-mapper/subsys/pil/qmi/wlfw: `False` / `True` / `True` / `True` / `True`
- Broad native WLFW text is treated only as context because WLFW service 69 and `wlan0` remain absent.
- `after_holder_start` counts pd-mapper/subsys/pil/qmi/wlfw: `0` / `9` / `5` / `7` / `30`
- `after_holder_start` last pd-mapper/wlan_pd: `missing` / `missing`
- `after_early_listener` counts pd-mapper/subsys/pil/qmi/wlfw: `0` / `10` / `5` / `7` / `30`
- `after_early_listener` last pd-mapper/wlan_pd: `missing` / `missing`
- `after_post_listener_window` counts pd-mapper/subsys/pil/qmi/wlfw: `0` / `10` / `5` / `7` / `30`
- `after_post_listener_window` last pd-mapper/wlan_pd: `missing` / `missing`

## Native Lower State

- service-notifier early/late state: `uninit` / `uninit`
- service-notifier early/late indication: `0` / `0`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- safety ok: `True`

## Android-positive Baseline

- V739/V852 decisions: `v739-mdm3-online-delta-active-blocker` / `v852-android-mdm3-online-provider-surface-captured`
- Android V622 counts service-locator/SN180/SN74/wlan_pd/ack/qmi-server/WLFW/wlan0: `1` / `1` / `1` / `2` / `1` / `1` / `1` / `3`
- Android V622 deltas sysmon→locator, sysmon→SN180, SN180→SN74, SN180→wlan_pd, SN180→WLFW, wlan_pd→qmi-server: `2.446` / `30.43` / `6.561` / `2427.362` / `1415.75` / `2.509`
- Android V852 mss/mdm3: `ONLINE` / `ONLINE`
- Android V852 hints wlan_pd/WLFW/wlan0: `True` / `True` / `True`

## Interpretation

- PM-client success, sysmon/QMI context, and service-notifier 180 are no longer the blocker.
- Native also has lower MSS/subsys/PIL/QMI context, so the next useful surface is the missing publication path into pd-mapper/service locator and wlan_pd/service-notifier 74.
- The next source/build should remain read-only and target bounded service-locator/domain-QMI evidence for wlan_pd publication, not Wi-Fi HAL or scan/connect.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
