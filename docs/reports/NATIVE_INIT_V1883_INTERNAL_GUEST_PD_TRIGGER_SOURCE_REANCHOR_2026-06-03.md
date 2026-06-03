# Native Init V1883 Internal Guest-PD Trigger Source Re-anchor

## Summary

- Cycle: `V1883`
- Type: host/source-only re-anchor from SDX50M/PCIe back to internal modem WLAN guest-PD trigger
- Decision: `v1883-internal-guest-pd-trigger-comparison-unrun-host-pass`
- Label: `internal-guest-pd-trigger-comparison-unrun`
- Result: PASS
- Reason: Normal Android-good reaches internal wlan_pd/wlanmdsp without PCIe/MHI, while native only opens /dev/subsys_modem and leaves wlan_pd uninit; the next unit is the read-only Android-vs-native per_mgr_vote/QMI/servreg/SSCTL trigger diff.
- Evidence: `tmp/wifi/v1883-internal-guest-pd-trigger-source-reanchor`

## Android Normal Anchor

- Evidence: `tmp/wifi/v1753-android-good-wlan-pd-firmware-request/android-postfs-evidence/a90-v1753-wlan-pd-fwreq`
- requested wlanmdsp / PD image: `True` / `True`
- wlfw_start / wlan_pd indication / wlan0 seconds: `8.688967` / `9.672951` / `15.242158`
- first wlanmdsp logcat time / lines: `04:17:31.380` / `10`
- PCIe-or-MHI lines before wlan0: `0`

## Native PM-Service Anchor

- V1847 decision/pass: `v1847-open-context-modem-success-static-rollback-pass` / `True`
- PM client register/connect rc: `0` / `0`
- open context path/fd: `/dev/subsys_modem` / `0x7`
- callback/post-ack/service-notifier labels: `callback-ack-present-no-powerup` / `post-ack-open-branch-reached` / `service-notifier-uninit`
- lower WLFW69/wlan0/MHI present: `False` / `False` / `False`
- V1803 decision/pass: `v1803-wlan-pd-servnotif-uninit-wlfw-service69-absent-host-pass` / `True`
- V1803 requested wlanmdsp / WLFW69: `0` / `0`

## Source Surface

- pm-service QMI restart strings/imports: `True` / `True`
- pm-service vote strings: `True`
- libperipheral_client PM register/Binder descriptor: `True` / `True`
- libperipheral_client QMI imports: `False`
- Source artifacts: `{"libperipheral-client-bn-ontransact-0x85bc-0x8860.S": "host/libperipheral-client-bn-ontransact-0x85bc-0x8860.S", "libperipheral-client-pm-register-connect-0x612c-0x6700.S": "host/libperipheral-client-pm-register-connect-0x612c-0x6700.S", "libperipheral-client-trigger-strings.txt": "host/libperipheral-client-trigger-strings.txt", "pm-service-qmi-main-0x7000-0x7f00.S": "host/pm-service-qmi-main-0x7000-0x7f00.S", "pm-service-qmi-requests-0x8b00-0x9f00.S": "host/pm-service-qmi-requests-0x8b00-0x9f00.S", "pm-service-qmi-trigger-strings.txt": "host/pm-service-qmi-trigger-strings.txt"}`

## Selected Label

- `internal-guest-pd-trigger-comparison-unrun`: the decisive comparison is not PCIe/GDSC. It is the read-only diff of Android per_mgr_vote to modem-side wlan_pd trigger versus native's post-vote path after `/dev/subsys_modem` opens.

## Next

- Run one read-only comparison that captures Android normal `per_mgr_vote` -> QMI/servreg/SSCTL -> `msm/modem/wlan_pd` -> `wlanmdsp.mbn`, and the equivalent native post-open absence.
- Do not run GDSC/PMIC/GPIO/regulator writes, forced RC1/case, `/dev/subsys_esoc0`, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

## Safety Scope

V1883 is host/source-only. It reads existing artifacts and local binaries, writes local evidence/report files, and performs no device command, flash, reboot, property staging, tracefs write, service start, Wi-Fi operation, partition write, or hardware mutation.
