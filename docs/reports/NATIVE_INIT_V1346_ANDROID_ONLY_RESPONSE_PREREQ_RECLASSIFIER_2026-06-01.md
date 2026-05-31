# Native Init V1346 Android-only Response Prerequisite Reclassifier

## Summary

- Cycle: `V1346`
- Type: host-only evidence reclassifier
- Decision: `v1346-need-android-earliest-response-recapture`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1346-android-only-response-prereq-reclassifier/manifest.json`
  - `tmp/wifi/v1346-android-only-response-prereq-reclassifier/summary.md`
- Script: `scripts/revalidation/native_wifi_android_only_response_prereq_reclassifier_v1346.py`

## Key Facts

| fact | value |
| --- | --- |
| current native lower window | powerup=True samples=120 GPIO142=0 errfatal=0 PCIe=False MHI=0 ks=0 WLFW=0 wlan0=False |
| Android-positive lower chain | WLFW=8.39641s eSoC=8.449943s BDF=9.513055s wlan0=14.772258s |
| Android timing gap | PCIe_count=0 MHI_count=0 |
| provider/SDX50M route | provider-positive=1/1 sdx50m=True esoc=True |

## Decision

current native route reaches mdm_subsys_powerup with no lower transition, but the Android-positive timeline still lacks enough PCIe/MHI ordering detail on the same monotonic record as the early WLFW marker

Do not proceed to PMIC/GPIO/GDSC/eSoC mutation or Wi-Fi HAL/scan/connect from V1345 alone. The next safest branch is an Android read-only recapture that puts the first SDX50M response markers on one timeline.

## Next

V1347 should perform an Android read-only recapture for earliest GPIO142/PCIe RC1/LTSSM/MHI/ks/WLFW/BDF/wlan0 relative to PM/provider/CNSS markers, then roll back to native

## Safety

Host-only classifier. No device command, helper deploy, daemon start, PM actor, tracefs/sysfs/debugfs write, eSoC ioctl/notify, PMIC/GPIO/GDSC write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, flash, boot image write, or partition write occurred.
