# Native Init V1727 WLAN-PD Service-manager Bootstrap Handoff

## Summary

- Cycle: `V1727`
- Type: one-run rollbackable WLAN-PD service-manager-only bootstrap gate
- Decision: `v1727-wlfw-worker-thread-started-waiting-for-qmi-service-rollback-pass`
- Result: PASS
- Reason: one service-manager-only WLAN-PD gate produced a fixed nonlog label and rollback verified
- Evidence: `tmp/wifi/v1727-wlan-pd-service-manager-bootstrap-handoff`
- Rollback attempt: `from-native`

## Gate Label

- nonlog label: `wlfw-worker-thread-started-waiting-for-qmi-service`
- service-window label: `wlfw-start-reached`
- legacy firmware-serve label: `firmware-not-requested`
- service_manager: `1`
- service_manager_started: `1`
- companion order: `servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,subsys_modem_holder,cnss_diag,cnss_daemon,service-window-trigger-summary`
- cnss-daemon running: `1`
- tftp running: `1`
- WLFW service 69 seen: `0`
- requested `wlanmdsp`: `0`

## Uprobe Fields

- tracefs available: `1` (`errno=0`)
- wlfw_start hits: `1`
- wlfw_service_request hits: `1`
- wlfw worker create success hits: `1`
- wlfw indication-register QMI hits: `0`
- wlfw capability QMI hits: `0`
- peripheral defaultServiceManager hits: `None`
- peripheral service name hits: `None`
- peripheral service-manager get hits: `None`
- peripheral target path: `/tmp/a90-v231-547/root/vendor/lib64/libperipheral_client.so`
- cnss fd counts: `vndbinder=1`, `socket=10`

## Property Runtime

- Remote root: `/mnt/sdext/a90/private-property-v317/v1726/dev/__properties__`
- Uploaded files: `22`
- Uploaded bytes: `2759988`
- property_info SHA verified: `True`
- vendor_default_prop SHA verified: `True`

## Safety Scope

- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.
- PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.
- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.

## Next

- Stop after this one label.
- The service-manager-only gate moved past the old V1719 vendor Binder acquisition blocker.
- The active blocker is now downstream of cnss-daemon: `wlfw_service_request` worker starts, but WLFW service 69 is still absent and `wlanmdsp` is not requested.
- Do not add PM trio or `boot_wlan` from this result; the next unit should return to WLAN-PD image request / modem-side WLFW service publication evidence.
