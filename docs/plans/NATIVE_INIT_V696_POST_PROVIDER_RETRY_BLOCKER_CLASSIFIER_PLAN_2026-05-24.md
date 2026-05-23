# Native Init V696 Post-provider Retry Blocker Classifier Plan

- date: `2026-05-24 KST`
- cycle: `v696`
- type: host-only classifier

## Goal

V695 proved that `vendor.qcom.PeripheralManager` is registered and that a fresh
`cnss-daemon` retry tail runs after that registration. WLFW/BDF/`wlan0` still
remain absent. V696 classifies the remaining post-provider blocker without
another live action.

The classifier compares:

- V695 native dmesg/service surface;
- V695 manifest provider/query/retry result;
- Android reference dmesg from V515.

## Gate

Primary classification candidates:

- `cnss-daemon` Binder/runtime continuation remains the primary pre-WLFW
  blocker.
- duplicate `pm_qos_add_request()` is a primary kernel-side blocker.
- evidence is insufficient and more Android/native dmesg windows are needed.

Expected success label:

- `v696-cnss-binder-continuation-remains-primary`

## Guardrails

V696 must not:

- contact the device;
- start daemons, service managers, Wi-Fi HAL, `wificond`, supplicant, or
  hostapd;
- scan, connect, link up, use credentials, run DHCP, change routes, or external
  ping;
- write sysfs/debugfs, boot images, or partitions.

## Implementation

- Add a host-only timeline parser for Android and V695 dmesg.
- Extract first timestamps and counts for service `74`, CNSS netlink,
  CNSS Binder `-22`, duplicate `pm_qos`, WLFW, WLAN-PD, BDF, firmware-ready,
  and `wlan0`.
- Rank Binder vs `pm_qos` using timing:
  - Android reaches `wlfw_start` shortly after `cnss-daemon` netlink.
  - Native reaches CNSS netlink and Binder `-22`, but never reaches WLFW.
  - Native duplicate `pm_qos` is tracked as a native-only secondary warning
    unless Binder repair fails to move WLFW.

## Validation Plan

```bash
python3 -m py_compile scripts/revalidation/native_wifi_post_provider_retry_blocker_classifier_v696.py
python3 scripts/revalidation/native_wifi_post_provider_retry_blocker_classifier_v696.py \
  --out-dir tmp/wifi/v696-post-provider-retry-blocker-classifier-rerun \
  run
```
