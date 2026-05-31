# Native Init V1348 Android WLFW Request Path Classifier

## Summary

- Cycle: `V1348`
- Type: host-only evidence classifier
- Decision: `v1348-cnss-wlfw-request-path-before-lower-mutation`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1348-android-wlfw-request-path-classifier/manifest.json`
  - `tmp/wifi/v1348-android-wlfw-request-path-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_android_wlfw_request_path_classifier_v1348.py`

## Key Facts

| fact | value |
| --- | --- |
| native V1345 lower window | powerup=True samples=120 GPIO142=0 errfatal=0 PCIe=False MHI=0 ks=0 WLFW=0 wlan0=False |
| Android V1347 response chain | WLFW=8.035751s eSoC=8.251801s QMI=9.353921s BDF=9.517672s FW-ready=14.464681s wlan0=14.779047s |
| Android public lower surfaces | PCIe=0/0 MHI=0 pipe=0 ks=0 pci_sysfs=False mhi_sysfs=False |
| V1347 process/fd limitation | process_fds_ok=False duration=30.002513961997465s |

## Decision

Android reaches cnss-daemon wlfw_start before the captured subsys_get(esoc0) marker and then reaches ICNSS QMI, BDF, firmware-ready, and wlan0; native already reaches mdm_subsys_powerup with no lower response

Do not add PMIC/GPIO/GDSC/eSoC mutation based on V1345 alone. V1347's positive Android anchors are the `cnss-daemon` WLFW request path, ICNSS QMI connection, BDF transfer, firmware-ready event, and `wlan0` creation. The next unit should classify what Android has in the CNSS/WLFW runtime path that native still lacks.

## Next

V1349 should classify Android-vs-native cnss-daemon/WLFW runtime prerequisites before any PMIC/GPIO/GDSC/eSoC mutation

## Safety

Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
