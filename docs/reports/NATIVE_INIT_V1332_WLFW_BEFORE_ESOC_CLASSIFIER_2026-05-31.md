# Native Init V1332 WLFW-before-eSoC Classifier

## Summary

- Cycle: `V1332`
- Type: host-only classifier
- Decision: `v1332-native-missing-early-wlfw-provider-state`
- Result: PASS
- Evidence:
  - `tmp/wifi/v1332-wlfw-before-esoc-classifier/manifest.json`
  - `tmp/wifi/v1332-wlfw-before-esoc-classifier/summary.md`
- Script: `scripts/revalidation/native_wifi_wlfw_before_esoc_classifier_v1332.py`

V1332 compares the Android-positive V1331 timeline with the native V1328
full-window no-response evidence. Android recorded `wlfw_start` before the
first captured `__subsystem_get(esoc0)`, then BDF download and `wlan0`.
Native started `cnss_daemon` before `mdm_helper`/late `per_proxy` and reached
`mdm_subsys_powerup`, but still recorded no WLFW/BDF/MHI/ks/`wlan0`.

## Key Evidence

| item | value |
| --- | --- |
| android_wlfw_time | 8.39641 |
| android_esoc_time | 8.449943 |
| android_bdf_time | 9.513055 |
| android_wlan0_time | 14.772258 |
| native_order | servicemanager,hwservicemanager,vndservicemanager,vndservicemanager_ready,pm_proxy_helper,per_mgr,vndservice_query,per_proxy_deferred,cnss_daemon,mdm_helper,late_per_proxy,vndservice_query |
| native_wlfw_kmsg_max | 0 |
| native_mhi_bus_max | 0 |
| native_ks_process_max | 0 |

## Decision

The next native gate should not be a longer wait after `mdm_subsys_powerup`.
It should prove whether native `cnss-daemon` can reach the same early WLFW
userspace state that Android reaches before the captured eSoC trigger.

## Safety

Host-only classifier. No device command, helper deploy, actor start, tracefs
write, live eSoC ioctl/notify, PMIC/GPIO write, Wi-Fi HAL start, scan/connect,
credential use, DHCP/routes, external ping, flash, boot image write, or
partition write occurred.
