# Native Init V1938 WLAN-PD State-up Before WLFW Arrive

## Summary

- Cycle: `V1938`
- Decision: `v1938-wlan-pd-stateup-missing-before-wlfw-arrive-host-pass`
- Label: `wlan-pd-stateup-missing-before-wlfw-arrive`
- Pass: `True`
- Reason: Android advances from ICNSS PD registration to WLAN-PD state-up and WLFW service69 arrival; native reaches PD registration but service-notifier remains UNINIT and no WLFW arrive/new-server69 occurs
- Evidence: `tmp/wifi/v1938-wlan-pd-stateup-before-wlfw-arrive`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | wlan-pd-stateup-missing-before-wlfw-arrive | Android advances from ICNSS PD registration to WLAN-PD state-up and WLFW service69 arrival; native reaches PD registration but service-notifier remains UNINIT and no WLFW arrive/new-server69 occurs |
| Android positive | True | stateup=True indications=2 v1934=android-libqmi-service69-wait-return-positive-control |
| Native PD registration | True | notify=True pd_domain=True reg=True |
| Native state-up | False | late_state=uninit indication=0 raw_wlan_pd=0,0,0 |
| Native WLFW | False | lookup69=True wait=True arrive=False wlan0=False |
| Source passive | True | WLFW server arrive is qmi_add_lookup callback; restart-PD exists but remains out of scope |

## Source Anchors

| anchor | path | line | text |
| --- | --- | --- | --- |
| icnss_get_service_location | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/soc/qcom/icnss.c | 2064 | ret = get_service_location(ICNSS_SERVICE_LOCATION_CLIENT_NAME, |
| icnss_pd_registration_log | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/soc/qcom/icnss.c | 2031 | icnss_pr_dbg("PD notification registration happened, state: 0x%lx\n", |
| icnss_pd_restart | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/soc/qcom/icnss.c | 2603 | ret = service_notif_pd_restart(priv->service_notifier[0].name, |
| icnss_qmi_wlfw_new_server | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/soc/qcom/icnss_qmi.c | 1217 | static int wlfw_new_server(struct qmi_handle *qmi, |
| icnss_qmi_wlfw_arrive_log | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/soc/qcom/icnss_qmi.c | 1224 | icnss_pr_dbg("WLFW server arrive: node %u port %u\n", |
| icnss_qmi_event_post | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/soc/qcom/icnss_qmi.c | 1239 | icnss_driver_event_post(ICNSS_DRIVER_EVENT_SERVER_ARRIVE, |
| icnss_qmi_add_lookup | tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/soc/qcom/icnss_qmi.c | 1277 | ret = qmi_add_lookup(&priv->qmi, WLFW_SERVICE_ID_V01, |

## Interpretation

- Native already reaches the AP-side ICNSS service-location/domain-list path and registers for `msm/modem/wlan_pd` notifications.
- The missing edge before WLFW service69 is the remote WLAN-PD state-up indication; without that, `wlfw_new_server` never posts `SERVER_ARRIVE` and `cnss-daemon` stays in the service69 wait.
- The next live unit should observe remote WLAN-PD state-up inputs only: service-notifier response/indication payload timing, SSCTL/sysmon state for modem child PDs, and relevant RFS/tftp/rmtfs reads. It must not call `service_notif_pd_restart`, start HAL, scan/connect, use credentials, or touch eSoC/PCIe/GDSC.

## Inputs

- Android V1917: `tmp/wifi/v1917-android-icnss-ipc-log-edge-handoff/manifest.json`
- Android V1934: `tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/manifest.json`
- Native V1937: `tmp/wifi/v1937-icnss-ipc-service69-integration/manifest.json`
- Native inner: `tmp/wifi/v1937-icnss-ipc-service69-integration/v1936-handoff/manifest.json`

## Safety Scope

Host-only classifier. No live device command, flash, reboot, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.
