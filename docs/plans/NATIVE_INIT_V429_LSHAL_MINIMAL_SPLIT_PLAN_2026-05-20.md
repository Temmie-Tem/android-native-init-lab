# Native Init V429 lshal Minimal Split Plan

Date: 2026-05-20

## Goal

V429 narrows V428's timeout by removing expensive `lshal` columns and splitting
the query into:

1. a no-daemon-start VINTF-only control:
   `/system/bin/lshal list --types=vintf --neat -V -S -i`;
2. a bounded composite binderized-only status query:
   `/system/bin/lshal list --types=binderized --neat -S`.

The goal is to determine whether the V428 timeout came from broad
`binderized,vintf` output plus `-p -e -c`, or from native `hwservicemanager`
query behavior itself.

## Scope

Allowed:

- deploy only `a90_android_execns_probe v30` to `/cache/bin/a90_android_execns_probe`;
- run the existing no-daemon-start VINTF-only control;
- start only `servicemanager`, `hwservicemanager`, and
  `vendor.samsung.hardware.wifi@2.0-service` inside the helper-owned private
  namespace;
- run only the binderized status query above;
- require SELinuxfs `/sys/fs/selinux/status` before live execution.

Not allowed:

- Wi-Fi enable, scan, connect, link-up, credentials, DHCP, or routing;
- `wificond`, `wpa_supplicant`, `hostapd`, `cnss-daemon`, or `cnss_diag` start;
- persistent boot/autostart changes;
- Android partition, firmware, rfkill, module, or driver bind/unbind writes.

## Implementation

- Helper: `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - marker: `a90_android_execns_probe v30`
  - new composite mode: `wifi-hal-composite-lshal-binderized-status-list`
- Deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v30_deploy_preflight.py`
- Live runner:
  `scripts/revalidation/wifi_hal_lshal_minimal_split_v429_runner.py`

## Validation Plan

```text
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v429-a90_android_execns_probe-v30/a90_android_execns_probe

python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v30_deploy_preflight.py \
  scripts/revalidation/wifi_hal_lshal_minimal_split_v429_runner.py

git diff --check
```

Live sequence:

1. helper v30 deploy preflight;
2. helper v30 deploy only;
3. V429 minimal split preflight;
4. V429 live minimal split query;
5. postflight `status` and `selftest`.

## Expected Decisions

- `execns-helper-v30-deploy-pass`
- `v429-lshal-minimal-split-preflight-ready`
- `v429-lshal-minimal-split-pass` or
  `v429-lshal-minimal-split-runtime-gap`

Runtime-gap is acceptable evidence if postflight cleanup is clean and
`wifi_bringup_executed=False`.
