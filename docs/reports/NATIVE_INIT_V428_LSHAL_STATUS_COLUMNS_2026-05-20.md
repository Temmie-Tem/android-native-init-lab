# Native Init V428 lshal Status-Column Probe Report

Date: 2026-05-20

## Summary

V428 added helper v29 and ran the explicit `lshal -V -S` status-column probe.
The result is `v428-lshal-status-query-runtime-gap`: native private runtime can
show VINTF Wi-Fi declarations, but the bounded composite binderized/vintf
status query still times out before returning Samsung `ISehWifi/default` rows.

No Wi-Fi enable, scan, connect, link-up, credentials, DHCP, routing, persistent
autostart, firmware mutation, rfkill write, module operation, or Android
partition write was executed.

## Implementation

- `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - bumped helper marker to `a90_android_execns_probe v29`;
  - added `wifi-hal-lshal-vintf-status-list`;
  - added `wifi-hal-composite-lshal-status-list`;
  - kept query execution inside the helper-owned private namespace.
- `scripts/revalidation/wifi_execns_helper_v29_deploy_preflight.py`
  - deploys only `/cache/bin/a90_android_execns_probe`;
  - checks helper v29 status-query strings before deploy.
- `scripts/revalidation/wifi_hal_lshal_status_columns_v428_runner.py`
  - runs VINTF-only control first;
  - blocks composite live execution unless SELinuxfs status is visible;
  - runs bounded composite status-column query;
  - records clean postflight process and Wi-Fi link surfaces.

## Static Validation

```text
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v428-a90_android_execns_probe-v29/a90_android_execns_probe

artifact: tmp/wifi/v428-a90_android_execns_probe-v29/a90_android_execns_probe
sha256: fcb1a7440995d018a73d52e74fbdd826102cc3fa93ba5f46d50bdca585f2d1bb
readelf: There is no dynamic section in this file.
```

```text
python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v29_deploy_preflight.py \
  scripts/revalidation/wifi_hal_lshal_status_columns_v428_runner.py

git diff --check
```

Both checks passed.

## Evidence

Plan and preflight:

```text
tmp/wifi/v428-helper-v29-deploy-plan-20260520-141304/
tmp/wifi/v428-lshal-status-query-plan-20260520-141304/
tmp/wifi/v428-helper-v29-deploy-preflight-20260520-141317/
tmp/wifi/v428-lshal-status-query-preflight-postdeploy-20260520-142011/
```

Deploy:

```text
tmp/wifi/v428-helper-v29-deploy-live-20260520-141412/
decision: execns-helper-v29-deploy-pass
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

SELinuxfs prerequisite:

```text
tmp/wifi/v428-lshal-status-query-preflight-selinuxgate-20260520-142240/
decision: v428-lshal-status-query-blocked
reason: blocked before live run by selinuxfs-runtime-surface

tmp/wifi/v428-prereq-v401-selinuxfs-mount-20260520-142321/
decision: toybox-selinuxfs-mount-live-executor-run-pass
reason: selinuxfs status page is visible after toybox mount

tmp/wifi/v428-lshal-status-query-preflight-after-selinux-20260520-142335/
decision: v428-lshal-status-query-preflight-ready
```

Live:

```text
tmp/wifi/v428-lshal-status-query-live-after-selinux-20260520-142354/
decision: v428-lshal-status-query-runtime-gap
pass: True
reason: status query failed: lshal-timeout; VINTF rows present=True
device_commands_executed: True
device_mutations: True
daemon_start_executed: True
wifi_hal_start_executed: True
wifi_bringup_executed: False
```

## VINTF Control Findings

The VINTF-only control command exited nonzero because `lshal` still attempted
to obtain a default service manager:

```text
wifi_hal_service_query.variant=vintf-status-only
wifi_hal_service_query.result=service-query-runtime-gap
wifi_hal_service_query.reason=lshal-nonzero
Failed to get defaultServiceManager()!
```

It still emitted useful VINTF rows:

```text
DM,FC declared android.hardware.wifi.hostapd@1.2::IHostapd/default
DM,FC declared android.hardware.wifi.supplicant@1.3::ISupplicant/default
DM,FC declared android.hardware.wifi@1.4::IWifi/default
DM    declared vendor.samsung.hardware.wifi.hostapd@3.0::ISehHostapd/default
DM,FC declared vendor.samsung.hardware.wifi.supplicant@3.1::ISehSupplicant/default
DM,FC declared vendor.samsung.hardware.wifi@2.2::ISehWifi/default
```

Within the three V425 Samsung Wi-Fi targets, VINTF-only native evidence shows
only:

```text
vendor.samsung.hardware.wifi@2.2::ISehWifi/default: declared
```

It does not show native VINTF declarations for:

```text
vendor.samsung.hardware.wifi@2.0::ISehWifi/default
vendor.samsung.hardware.wifi@2.1::ISehWifi/default
```

## Composite Status Query Findings

The composite query started only:

```text
servicemanager
hwservicemanager
vendor.samsung.hardware.wifi@2.0-service
/system/bin/lshal list --types=binderized,vintf --neat -V -S -i -p -e -c
```

The query child timed out:

```text
wifi_hal_service_query.variant=binderized-vintf-status
wifi_hal_service_query.result=service-query-timeout
wifi_hal_service_query.reason=lshal-timeout
wifi_hal_composite_start.result=service-query-runtime-gap
wifi_hal_composite_start.reason=lshal-query-failed
```

Cleanup was safe:

```text
wifi_hal_composite_start.all_observable_at_timeout=1
wifi_hal_composite_start.all_postflight_safe=1
postflight.clean=True
postflight.processes=[]
postflight.wifi_links=[]
```

## Interpretation

V428 does not prove native `hwservicemanager` registration for Samsung
`ISehWifi/default`. It proves:

- native VINTF declaration surface includes
  `vendor.samsung.hardware.wifi@2.2::ISehWifi/default`;
- Android boot-complete rows for `@2.0`, `@2.1`, and `@2.2` are richer than the
  native VINTF-only declaration surface;
- the native bounded composite service stack still cannot return explicit
  binderized/vintf status rows before timeout;
- the composite cleanup path remains safe and no Wi-Fi bring-up happened.

## Next

Recommended next cycle: V429 minimal lshal status split.

V429 should avoid the expensive `-p -e -c` path first and split the questions:

1. VINTF-only status rows: `list --types=vintf --neat -V -S -i`;
2. binderized-only status rows: `list --types=binderized --neat -S`;
3. Android boot-complete mirror with the same explicit columns.

If binderized-only still times out while Android boot-complete remains richer,
the project should pivot toward Android-managed Wi-Fi runtime control rather
than deeper native service-manager reconstruction.
