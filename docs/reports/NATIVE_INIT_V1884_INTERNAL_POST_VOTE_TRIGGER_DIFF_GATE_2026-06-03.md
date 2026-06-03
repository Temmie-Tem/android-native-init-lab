# Native Init V1884 Internal Post-vote Trigger Diff Gate

## Summary

- Cycle: `V1884`
- Type: host-only selector for the internal-modem post-vote QMI/servreg guest-PD trigger diff
- Decision: `v1884-post-pm-success-guest-pd-trigger-diff-selected-host-pass`
- Label: `post-pm-success-wlfw-qmi-servreg-trigger-gap`
- Result: PASS
- Reason: Android normal reaches PM vote, wlan_pd indication, and wlanmdsp request without PCIe/MHI; native reaches PM success and /dev/subsys_modem open but stops before WLFW QMI indication/capability sends, WLFW service 69, and wlanmdsp request.
- Evidence: `tmp/wifi/v1884-internal-post-vote-trigger-diff-gate`

## Android Normal Trigger

- Evidence: `tmp/wifi/v1753-android-good-wlan-pd-firmware-request/android-postfs-evidence/a90-v1753-wlan-pd-fwreq`
- PM register/vote counts: `2` / `2`
- PM vote / WLFW request / wlanmdsp first times: `04:17:30.688` / `04:17:30.756` / `04:17:31.380`
- wlfw_start / wlan_pd / wlan0 seconds: `8.688967` / `9.672951` / `15.242158`
- wlanmdsp lines: `10`
- PCIe-or-MHI lines before wlan0: `0`

## Native Post-vote State

- V1847 decision/pass: `v1847-open-context-modem-success-static-rollback-pass` / `True`
- PM client register/connect rc: `0` / `0`
- open context path/fd/power-state: `/dev/subsys_modem` / `0x7` / `0x2`
- V1802 decision/pass: `v1802-wlfw-worker-waiting-for-qmi-service-host-pass` / `True`
- source PM server/list/register labels: `pm-server-register-success-return` / `2` / `1`
- PM register/connect/WLFW request/DMS hits: `1` / `1` / `1` / `1`
- WLFW ind-register/capability QMI hits: `0` / `0`
- V1803 decision/pass: `v1803-wlan-pd-servnotif-uninit-wlfw-service69-absent-host-pass` / `True`
- requested wlanmdsp / WLFW service69 / wlan0: `0` / `0` / `0`
- service-notifier early/late state: `uninit` / `uninit`
- QRTR WLFW case0/case1 service events: `0` / `0`

## Source Surface

- V1883 decision/label/pass: `v1883-internal-guest-pd-trigger-comparison-unrun-host-pass` / `internal-guest-pd-trigger-comparison-unrun` / `True`
- pm-service QMI restart/imports/vote strings: `True` / `True` / `True`
- libperipheral PM register/Binder descriptor: `True` / `True`
- source artifacts: `{"libperipheral-client-bn-ontransact-0x85bc-0x8860.S": "host/libperipheral-client-bn-ontransact-0x85bc-0x8860.S", "libperipheral-client-pm-register-connect-0x612c-0x6700.S": "host/libperipheral-client-pm-register-connect-0x612c-0x6700.S", "libperipheral-client-trigger-strings.txt": "host/libperipheral-client-trigger-strings.txt", "pm-service-qmi-main-0x7000-0x7f00.S": "host/pm-service-qmi-main-0x7000-0x7f00.S", "pm-service-qmi-requests-0x8b00-0x9f00.S": "host/pm-service-qmi-requests-0x8b00-0x9f00.S", "pm-service-qmi-trigger-strings.txt": "host/pm-service-qmi-trigger-strings.txt"}`

## Selected Diff

- Label: `post-pm-success-wlfw-qmi-servreg-trigger-gap`.
- The next useful unit is a read-only Android-normal versus native-post-vote diff for the QMI/servreg/SSCTL request that moves `msm/modem/wlan_pd` from `uninit` to an indication state and causes the `wlanmdsp.mbn` request.
- The SDX50M/PCIe/eSoC/GDSC path remains rejected for wlan0; do not optimize against degraded 257s boots.

## Safety Scope

V1884 is host-only. It reads retained evidence and local source/disassembly summaries only. It performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or device partition write.

## Next

- Build the constrained read-only comparator around Android normal `per_mgr_vote`/pm-service QMI/servreg/SSCTL and native post-`/dev/subsys_modem` open absence.
- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are both present in native init.
