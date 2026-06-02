# Native Init V1683 WLAN-PD Service-window Trigger Handoff

## Summary

- Cycle: `V1683`
- Type: one-run rollbackable WLAN-PD service-window trigger gate
- Decision: `v1683-service-window-still-no-wlfw-rollback-pass`
- Result: PASS
- Reason: one WLAN-PD service-window trigger gate run produced a fixed label and rollback verified
- Evidence: `tmp/wifi/v1683-wlan-pd-service-window-handoff`
- Rollback attempt: `from-native`

## Gate Label

- Label: `service-window-still-no-wlfw`
- legacy firmware-serve label: `firmware-not-requested`
- tftp running: `1`
- subsys_modem holder opened: `1`
- cnss-daemon started: `1`
- wlfw_start seen: `0`
- wlfw_service_request seen: `0`
- WLFW service 69 seen: `0`
- requested wlanmdsp: `0`
- companion order: `servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,cnss_daemon,service-window-trigger-summary`

## Safety Scope

- `/dev/subsys_esoc0`, raw eSoC ioctl, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, and BOOT_DONE spoof were not used.
- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was test boot flash followed by rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label.
- If label is `wlfw-start-reached`, the next gate may inspect WLFW service 69 / WLAN-PD / firmware serving.
- If label is `service-window-still-no-wlfw`, inspect missing Android property/binder/service inputs before adding lower-layer work.
- Do not proceed to MSA/BDF, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping until WLFW service 69 or `wlfw-start-reached` appears.
