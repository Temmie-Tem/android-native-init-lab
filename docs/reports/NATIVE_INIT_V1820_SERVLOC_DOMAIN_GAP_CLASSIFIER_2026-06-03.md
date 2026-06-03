# Native Init V1820 Servloc Domain Gap Classifier

## Summary

- Cycle: `V1820`
- Type: host-only classifier over V1819 publication text handoff and Android-positive locator baselines
- Decision: `v1820-qrtr-servloc-registry-snapshot-target-host-pass`
- Result: PASS
- Reason: Native has generic service-locator init plus PM-client/sysmon/service180/lower-QMI context, but lacks wlan-specific domain publication, service74, wlan_pd, WLFW, and wlan0 while Android-good progresses from service-locator to wlan_pd/qmi-server
- Evidence: `tmp/wifi/v1820-servloc-domain-gap-classifier`
- Source evidence: `tmp/wifi/v1819-publication-text-handoff`

## Native V1819 Shape

- V1819 decision: `v1819-servloc-init-visible-domain-absent-rollback-pass`
- labels publication/service74/PM-client/handoff/lower-state: `servloc-init-visible-domain-absent` / `service74-raw-absent` / `pm-client-return-success` / `servnotif-klog-progress-still-uninit` / `stable-mdm3-offlining`
- PM-client register/connect/return rc: `0` / `0` / `0`
- native locator/domain/wlan-fw/wlan-pd-domain/qmi-server counts: `2,2,2` / `0,0,0` / `0,0,0` / `0,0,0` / `0,0,0`
- native service180/service74/wlan_pd counts: `1,1,1` / `0,0,0` / `0,0,0`
- native lower preconditions pd-mapper/subsys/pil/qmi/wlfw: `0,0,0` / `9,10,10` / `5,5,5` / `7,7,7` / `30,30,30`
- `after_holder_start` counts locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `2` / `0` / `0` / `0` / `0`
- `after_holder_start` last locator/domain: `<6>[    2.833137]  [7:    kworker/7:1:   74] servloc: init_service_locator: Service locator initialized` / `missing`
- `after_early_listener` counts locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `2` / `0` / `0` / `0` / `0`
- `after_early_listener` last locator/domain: `<6>[    2.833137]  [7:    kworker/7:1:   74] servloc: init_service_locator: Service locator initialized` / `missing`
- `after_post_listener_window` counts locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `2` / `0` / `0` / `0` / `0`
- `after_post_listener_window` last locator/domain: `<6>[    2.833137]  [7:    kworker/7:1:   74] servloc: init_service_locator: Service locator initialized` / `missing`

## Native Lower State

- service-notifier early/late state: `uninit` / `uninit`
- service-notifier early/late indication: `0` / `0`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- safety ok: `True`

## Android-positive Baseline

- V739/V852 decisions: `v739-mdm3-online-delta-active-blocker` / `v852-android-mdm3-online-provider-surface-captured`
- Android V622 counts service-locator/SN180/SN74/wlan_pd/ack/qmi-server/WLFW/wlan0: `1` / `1` / `1` / `2` / `1` / `1` / `1` / `3`
- Android V622 deltas sysmon→locator, sysmon→SN180, SN180→SN74, SN180→wlan_pd, wlan_pd→qmi-server: `2.446` / `30.43` / `6.561` / `2427.362` / `2.509`
- Android V852 mss/mdm3: `ONLINE` / `ONLINE`
- Android V852 hints wlan_pd/WLFW/wlan0: `True` / `True` / `True`

## Interpretation

- Generic native service-locator initialization is present, so the next gap is not simply service-locator init.
- Native lacks wlan-specific service-locator/domain publication and remains without service74, wlan_pd, WLFW service 69, MHI, or `wlan0`.
- The next source/build should remain read-only and capture bounded QRTR/service-locator registry or state for wlan/fw and wlan_pd publication.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
