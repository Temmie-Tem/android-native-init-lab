# Native Init V1887 Normal Android PM Msg-id Capture Contract

## Summary

- Cycle: `V1887`
- Type: host-only capture contract for the normal-Android PM msg-id/servreg/SSCTL trigger diff
- Decision: `v1887-normal-android-pm-msgid-capture-contract-host-pass`
- Label: `normal-android-pm-msgid-capture-contract-ready`
- Result: PASS
- Reason: normal-Android read-only capture contract is ready for the PM msg-id/servreg/SSCTL diff; no live capture ran because Android ADB is absent in the current state
- Evidence: `tmp/wifi/v1887-normal-android-pm-msgid-capture-contract`

## Source Anchors

- pm-service binary/tag: `tmp/wifi/v1073-host-only/vendor-extract/files/pm-service` / `PerMgrSrv`
- PM register/vote string offsets: `3f13` / `4b41`
- msg20/msg21/msg22 string offsets: `4098` / `43d9` / `4a51`
- pm-service source checks: `{"libperipheral_qmi_imports": false, "pm_msg22_request_string": true, "pm_msg22_response_call": true, "pm_msgid_0x22_dispatch": true, "pm_post_ack_msg22_indication": true, "pm_post_ack_pending_restart_client_slot": true}`
- pm-service trace points: `[{"expected_msg_id": "0x20", "meaning": "system restart request path; must not be used for WLAN bring-up", "name": "pm_msg20_system_restart_request", "offset": "0x6ebc"}, {"expected_msg_id": "0x21", "meaning": "system shutdown request path; must not be used for WLAN bring-up", "name": "pm_msg21_system_shutdown_request", "offset": "0x7014"}, {"expected_msg_id": "0x22", "meaning": "peripheral restart request handler; candidate WLAN-PD state-up edge", "name": "pm_msg22_peripheral_restart_request", "offset": "0x716c"}, {"expected_msg_id": "0x22", "meaning": "QMI response call for msg22 request handler", "name": "pm_msg22_response_call", "offset": "0x725c"}, {"expected_msg_id": "0x22", "meaning": "post-ack indication call using the pending restart client slot", "name": "pm_msg22_post_ack_indication_call", "offset": "0x8a4c"}]`
- CNSS QMI sync calls: `{"dms_get_wlan_address": {"function": "dms_get_wlan_address", "message": "0x5c", "req": "0x4", "resp": "0x18", "site": "0xe59c", "timeout": "10000 ms"}, "dms_service_request": {"function": "dms_service_request", "message": "0x33", "req": "0x7", "resp": "0x8", "site": "0xea90", "timeout": "10000 ms"}, "wlfw_send_bdf_download_req": {"function": "wlfw_send_bdf_download_req", "message": "0x25", "req": "0x1824", "resp": "0x18", "site": "0xfc44", "timeout": "10000 ms"}, "wlfw_send_cap_req": {"function": "wlfw_send_cap_req", "message": "0x24", "req": "0x1", "resp": "0x108", "site": "0xf460", "timeout": "10000 ms"}, "wlfw_send_ind_register_req": {"function": "wlfw_send_ind_register_req", "message": "0x20", "req": "0x30", "resp": "0x18", "site": "0xf32c", "timeout": "10000 ms"}}`

## Capture Contract

- boot class/start/stop: `normal Android boot only` / `before vendor.per_mgr PM vote for modem` / `after first wlanmdsp.mbn tftp request or wlan0 event`
- reject-if: `["wlan0 appears near 257s degraded path", "esoc0_boot_failed appears before wlan0", "PCIe/MHI events appear before wlan0"]`
- logcat tags: `["PerMgrSrv", "PerMgrLib", "cnss-daemon", "tftp_server", "vendor.rmt_storage", "service-notifier", "servloc", "sysmon-qmi"]`
- dmesg markers: `["sysmon-qmi SSCTL", "service-notifier 180", "service-notifier 74", "msm/modem/wlan_pd state indication", "icnss_qmi QMI Server Connected", "wlanmdsp.mbn request", "wlan0 event", "PCIe/MHI contamination check"]`
- process targets: `["pm-service", "per_mgr", "cnss-daemon", "tftp_server", "rmt_storage"]`
- PM msg-id signals: `["msg 0x20 request/response/indication count", "msg 0x21 request/response/indication count", "msg 0x22 request/response/indication count", "pending restart client slot nonzero before post-ack msg22 indication"]`
- fixed labels: `["android-msg22-stateup-observed-native-absent", "android-stateup-without-msg22-log-observability-gap", "android-normal-capture-contaminated", "native-post-open-msg22-still-absent", "capture-incomplete"]`

## Selected Diff

- Label: `normal-android-pm-msgid-capture-contract-ready`.
- The next live unit is not another SDX50M/eSoC/PCIe/GDSC probe; it is the normal-Android PM msg-id/servreg/SSCTL capture across PM vote to first `wlanmdsp.mbn`.
- The required discriminator is whether Android emits pm-service msg `0x22` and a service-notifier state-up path before `wlanmdsp.mbn`, and whether native post-open still lacks that edge.
- If Android reaches WLAN-PD state-up but msg-id evidence is still absent, the correct label is an observability gap, not proof that msg22 is false.

## Safety Scope

V1887 is host-only. It reads retained manifests/reports and local binaries, then writes local contract artifacts only. It performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.

## Next

- Run the contract only when normal Android ADB/root capture is available; current state has no ADB device attached.
- Use the normal ~14s boot path only; reject degraded 257s captures and any pre-wlan0 PCIe/MHI path.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.
