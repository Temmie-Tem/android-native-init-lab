# Native Init V1845 Post-Ack Modem-Open Classifier

## Summary

- Cycle: `V1845`
- Type: host-only classifier over V1844 rollback-verified post-ack evidence
- Decision: `v1845-post-ack-modem-open-no-ext-powerup-host-pass`
- Label: `post-ack-modem-open-no-ext-powerup`
- Result: PASS
- Reason: V1844 proves the current post-ack PM-service branch opens /dev/subsys_modem successfully, while the external SDX50M/eSoC lower state remains static
- Evidence: `tmp/wifi/v1845-post-ack-modem-open-classifier`

## Input

- V1844: `v1844-post-ack-open-branch-reached-rollback-pass` / pass `True`
- V1844 rollback/post-version/post-selftest: `True` / `True` / `True`

## V1844 Open Evidence

- post-ack label/total: `post-ack-open-branch-reached` / `20`
- callback/ack label/total: `callback-ack-present-no-powerup` / `28`
- open call/return hits: `1` / `1`
- open path/rc: `/dev/subsys_modem` / `0x7`
- supported PM map: `{'SDX50M': '/dev/subsys_esoc0', 'modem': '/dev/subsys_modem'}`
- open call line: `Binder:596_2-601   [000] ....     6.740667: pm_service_post_ack_power_on_open_call: (0x5565f7cccc) path="/dev/subsys_modem"`
- open return line: `Binder:596_2-601   [000] ....     6.740711: pm_service_post_ack_power_on_open_ret: (0x5565f7ccd4) open_rc=0x7`

## Static Lower State

- lower-continuation/lower-state: `lower-continuation-static-gap` / `stable-mdm3-offlining`
- powerup threads / inferred esoc0 opens: `[0, 0]` / `[0, 0]`
- PM focus changes/status-delta/MHI-wlan0-progress: `[]` / `0` / `False`
- mdm3/MHI/WLFW69/wlan0: `OFFLINING` / `False` / `False` / `False`
- service-notifier / QIPCRTR bound labels: `service-notifier-uninit` / `qipcrtr-bound-recv-poll-timeout-passive`

## Interpretation

- The current route is no longer blocked before PM-service post-ack action: ack implementation, action branch, timer/state checks, and an open call all fired.
- The open target is `/dev/subsys_modem`, not `/dev/subsys_esoc0`; this can succeed without creating the external SDX50M/eSoC powerup thread or WLFW/MHI/wlan0 progress.
- The next boundary is PM-service peripheral selection/state for the post-ack open path, not callback delivery, PM ack completion, QRTR, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.

## Next

- Next unit should be source/build-only first: decode PM-service post-ack open context around `0x8cc8`/`0x8cd4` to capture peripheral name/devnode/state/fd fields.
- Do not force `/dev/subsys_esoc0` or proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.
