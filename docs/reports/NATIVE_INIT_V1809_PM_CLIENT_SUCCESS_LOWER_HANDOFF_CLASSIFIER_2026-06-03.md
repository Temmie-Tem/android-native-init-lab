# Native Init V1809 PM-client-success Lower-handoff Classifier

## Summary

- Cycle: `V1809`
- Type: host-only classifier over V1808 PM-client return evidence and Android-positive lower-handoff baselines
- Decision: `v1809-pm-client-success-servnotif-uninit-lower-handoff-missing-host-pass`
- Result: PASS
- Reason: PM-client register/connect/return values are zero, but native wlan_pd service-notifier remains uninit with no indication and WLFW service 69 absent while Android-good reaches service-notifier 180/74, wlan_pd, WLFW, and wlan0
- Evidence: `tmp/wifi/v1809-pm-client-success-lower-handoff-classifier`
- Source evidence: `tmp/wifi/v1808-pm-client-return-fetchargs-handoff`

## Current Native Gate

- V1808 decision: `v1808-pm-client-return-success-still-offlining-rollback-pass`
- PM-client label: `pm-client-return-success-still-offlining`
- lower-state label: `stable-mdm3-offlining`
- projection / PM server labels: `list-commit-progress` / `pm-server-register-success-return`
- list commit / PM server success hits: `2` / `1`
- PM-client register/connect/return rc: `0` / `0` / `0`

## Current Lower State

- MSS states: `ONLINE,ONLINE`
- mdm3 states: `OFFLINING`
- mdm status IRQ totals: `0,0,0,0,0,0,0,0,0,0,0,0,0`
- MHI counts/present: `0,0,0,0,0,0,0,0,0,0,0,0,0` / `False`
- requested `wlanmdsp` / WLFW service69 / wlan0: `0` / `0` / `False`
- early listener endpoint/status: `found` node `0` port `2`
- early listener response: success `1`, state `uninit` (`0x7fffffff`)
- early listener indication/ack/result: `0` / `0` / `listener-response-success`
- early listener hold/poll/phase: `15009` / `1` / `early-window`
- late listener endpoint/status: `found` node `0` port `2`
- late listener response: success `1`, state `uninit` (`0x7fffffff`)
- late listener indication/ack/result: `0` / `0` / `listener-response-success`
- late listener hold/poll/phase: `15014` / `1` / `late-post-window-before-cleanup`
- `case_0` service/instance/status: `69` / `0` / `complete`
- `case_0` service/empty/end/timeout: `0` / `1` / `1` / `0`
- `case_1` service/instance/status: `69` / `1` / `complete`
- `case_1` service/empty/end/timeout: `0` / `1` / `1` / `0`
- service_notifier debugfs count: `0 shown=0 truncated=0`

## Android-positive Baselines

- V739 decision: `v739-mdm3-online-delta-active-blocker`
- V852 decision: `v852-android-mdm3-online-provider-surface-captured`
- Android V622 counts service-notifier 180/74, wlan_pd, ack, WLFW start, qmi-server: `1` / `1` / `2` / `1` / `1` / `1`
- Android V622 deltas sysmon_modem→SN180, SN180→wlan_pd, SN180→WLFW, wlan_pd→qmi-server: `30.43` / `2427.362` / `1415.75` / `2.509`
- Android V620 causality SN before esoc0 / wlan_pd before esoc0 / raw esoc no-retry: `True` / `True` / `True`
- Android V852 mss/mdm3: `ONLINE` / `ONLINE`
- Android V852 counts mdm3/WLFW/BDF/MHI: `83` / `18` / `8` / `13`
- Android V852 hints wlan_pd/WLFW/BDF/wlan0: `True` / `True` / `True` / `True`

## Interpretation

- PM-service list/register and `cnss-daemon` PM-client register/connect are now proven to return success in native init.
- The remaining blocker is below that successful PM-client boundary: wlan_pd service-notifier state remains `uninit` early and late, no indication is produced, and WLFW service 69 is absent.
- Android-good evidence shows service-notifier 180/74, wlan_pd UP/ACK, qmi-server, WLFW/BDF, and `wlan0` occur without requiring native to open `/dev/subsys_esoc0` directly.
- Next work should observe the service-notifier/sysmon/subsys lower handoff after PM-client success; Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain premature.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.
