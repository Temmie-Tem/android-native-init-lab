# Native Init V1923 Post-WLFW QMI Service Delta

## Summary

- Cycle: `V1923`
- Decision: `v1923-post-wlfw-qmi-service-unavailable-before-ind-cap-host-pass`
- Label: `post-wlfw-qmi-service-unavailable-before-ind-cap`
- Pass: `True`
- Reason: V1919 closes the .jsn/RFS lead, Android normal boots publish WLAN-PD/QMI about one second after wlfw_service_request, and native V1920 reaches service74+PM-open+holder+DMS/WLFW worker but never sees WLFW69 or the first WLFW indication/capability QMI path
- Evidence: `tmp/wifi/v1923-post-wlfw-qmi-service-delta`

## Source Closure

| source | label | reason |
| --- | --- | --- |
| V1919 .jsn gate | android-modem-no-jsn-read | existing normal-Android tftp/rmtfs captures request wlanmdsp.mbn with zero pre-wlanmdsp .jsn/modemuw.jsn hits |
| V1922 QMI wait | service74-pm-open-holder-wlfw-worker-qmi-service-wait | native V1920 has service74/service180, PM /dev/subsys_modem open, holder open, and WLFW worker creation, but the worker waits before WLFW indication/capability QMI and Android advances to wlan_pd/wlanmdsp/wlan0 |

## Android Normal Timing

| source | wlfw_to_wlan_pd_ms | timing |
| --- | --- | --- |
| v1899 | 1071.401 | wlfw=8.601181 wlan_pd=9.672582 qmi=9.674706 wlan0=14.83251 |
| v1909 | 941.55 | wlfw=8.617059 wlan_pd=9.558609 qmi=9.561469 wlan0=14.904181 |

## Native Edge

| area | value | detail |
| --- | --- | --- |
| combined prereqs | True | service74=True pm_open=True holder=True |
| worker edge | 1 | dms=1 worker=1 ind=0 cap=0 |
| publication | False | servnotif=uninit/0 qrtr69=0,0 wlan_pd=False wlanmdsp=False wlan0=False |
| servloc domain | domain-list-response-success | domains=1 first=msm/modem/wlan_pd instance=180 |

## Native First Lines

- DMS request: `cnss-daemon-634   [003] ....     6.700779: dms_service_request: (0x5575697808)`
- WLFW worker request: `cnss-daemon-635   [001] ....     6.700862: wlfw_service_request: (0x55756969fc)`
- WLFW worker create success: `cnss-daemon-624   [002] ....     6.700823: wlfw_worker_pthread_create_success: (0x5575697da0)`
- WLFW indication QMI: `none`
- WLFW capability QMI: `none`

## Interpretation

- The modem `.jsn`/RFS hypothesis is not the active gate for this unit: V1919 shows normal Android requested `wlanmdsp.mbn` with no pre-request `.jsn` read; native MPSS `.jsn` absence is therefore not the deciding gate.
- The clean-DSP/sibling-sysmon companion, PM `/dev/subsys_modem` open, modem holder, DMS request, and CNSS WLFW worker are all present together in V1920.
- Native stops before WLFW indication/capability QMI because WLFW service 69/WLAN-PD publication never arrives; Android normal boots make that transition about one second after `wlfw_service_request`.
- The next live unit should instrument the worker wait primitive or QMI service wait target around WLFW service 69 publication, still below Wi-Fi HAL and without SDX50M/eSoC/PCIe/GDSC work.

## Safety Scope

Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, write firmware/partitions, remount-write, open `/dev/subsys_esoc0`, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, external ping, force RC1/case, touch PMIC/GPIO/GDSC/regulators, rescan PCI, bind/unbind platforms, fake ONLINE, or send eSoC notify/BOOT_DONE.
