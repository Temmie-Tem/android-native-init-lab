# Native Init V1922 Post-WLFW QMI Wait

## Summary

- Cycle: `V1922`
- Decision: `v1922-service74-pm-open-holder-wlfw-worker-qmi-service-wait-host-pass`
- Label: `service74-pm-open-holder-wlfw-worker-qmi-service-wait`
- Pass: `True`
- Reason: native V1920 has service74/service180, PM /dev/subsys_modem open, holder open, and WLFW worker creation, but the worker waits before WLFW indication/capability QMI and Android advances to wlan_pd/wlanmdsp/wlan0
- Evidence: `tmp/wifi/v1922-post-wlfw-qmi-wait`

## Matrix

| area | value | detail |
| --- | --- | --- |
| label | service74-pm-open-holder-wlfw-worker-qmi-service-wait | native V1920 has service74/service180, PM /dev/subsys_modem open, holder open, and WLFW worker creation, but the worker waits before WLFW indication/capability QMI and Android advances to wlan_pd/wlanmdsp/wlan0 |
| Android full | True | wlan_pd=True wlanmdsp=True wlan0=True |
| Native combined | True | service74=True pm_open=True holder=True |
| Native post-WLFW | False | ind_qmi=False cap_qmi=False wlfw69=False wlan_pd=False wlanmdsp=False |

## Native Edge

- Order: `servicemanager,hwservicemanager,vndservicemanager,qrtr_ns,pd_mapper,rmt_storage,tftp_server,pm_proxy_helper,per_mgr,vndservice_query,subsys_modem_holder,cnss_diag,cnss_daemon,service-object-visible-summary`
- PM open: `/dev/subsys_modem` fd `0x8`
- Holder: started/opened/postflight `True` / `True` / `True` fd `27`
- WLFW start/request/worker times: `6.695305` / `6.700862` / `6.700823`
- WLFW QMI ind/cap: `False` / `False`
- Labels: `wlfw-worker-thread-started-waiting-for-qmi-service` / `modem-holder-regression` / `provider-visible-modem-holder-regression`
- Late service-notifier state/indication: `uninit` / `0`

## First Native Lines

- wlfw_start: `cnss-daemon-624   [002] ....     6.695305: wlfw_start: (0x5575697c00)`
- wlfw_service_request: `cnss-daemon-635   [001] ....     6.700862: wlfw_service_request: (0x55756969fc)`
- worker_create_success: `cnss-daemon-624   [002] ....     6.700823: wlfw_worker_pthread_create_success: (0x5575697da0)`
- ind_register_qmi: `none`
- cap_qmi: `none`

## Interpretation

- The requested service74 + CNSS worker + PM-service integration is already present in V1920 evidence; the blocker is later than `wlfw_service_request` worker creation.
- The next bounded unit should characterize the worker's wait for WLFW QMI service availability versus Android's normal WLFW69/WLAN-PD publication window.
- Still no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` control, forced RC1/case, PMIC/GPIO/GDSC/regulator writes, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE.
