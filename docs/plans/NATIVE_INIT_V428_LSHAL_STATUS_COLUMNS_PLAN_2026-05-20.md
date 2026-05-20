# Native Init V428 lshal Status-Column Probe Plan

Date: 2026-05-20

## Goal

V428 answers the narrow question left by V427: whether the Android-side
Samsung Wi-Fi hwservice rows are only VINTF declarations or are observable as
live native `hwservicemanager` registrations when the bounded native composite
trio is running.

## Scope

Allowed:

- deploy only `a90_android_execns_probe v29` to `/cache/bin/a90_android_execns_probe`;
- run a no-daemon-start VINTF-only control:
  `/system/bin/lshal list --types=vintf --neat -V -S -i`;
- run one bounded composite start-only query with `servicemanager`,
  `hwservicemanager`, and `vendor.samsung.hardware.wifi@2.0-service`;
- query:
  `/system/bin/lshal list --types=binderized,vintf --neat -V -S -i -p -e -c`;
- require SELinuxfs `/sys/fs/selinux/status` to be visible before composite
  execution.

Not allowed:

- Wi-Fi enable, scan, connect, link-up, credentials, DHCP, or routing;
- `wificond`, `wpa_supplicant`, `hostapd`, `cnss-daemon`, or `cnss_diag` start;
- persistent boot/autostart changes;
- Android partition, firmware, rfkill, module, or driver bind/unbind writes.

## Implementation

- Helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - marker: `a90_android_execns_probe v29`
  - new read-only mode: `wifi-hal-lshal-vintf-status-list`
  - new composite mode: `wifi-hal-composite-lshal-status-list`
- Deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v29_deploy_preflight.py`
- Live runner:
  `scripts/revalidation/wifi_hal_lshal_status_columns_v428_runner.py`

## Validation Plan

```text
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v428-a90_android_execns_probe-v29/a90_android_execns_probe

python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v29_deploy_preflight.py \
  scripts/revalidation/wifi_hal_lshal_status_columns_v428_runner.py

git diff --check
```

Live gates:

1. deploy helper v29 only;
2. verify V428 preflight;
3. if SELinuxfs is absent, run the existing bounded V401 toybox mount executor;
4. rerun V428 preflight;
5. execute V428 live status-column query.

## Expected Decisions

- `execns-helper-v29-deploy-pass`
- `v428-lshal-status-query-preflight-ready`
- `v428-lshal-status-query-pass` or
  `v428-lshal-status-query-runtime-gap`

Either runtime-gap result is acceptable evidence as long as cleanup is safe,
postflight process surface is clean, and `wifi_bringup_executed=False`.
