# Native Init V429 lshal Minimal Split Report

Date: 2026-05-20

## Summary

V429 added helper v30 and reran the V428 status question with a narrower
binderized-only `lshal` query. The result is still
`v429-lshal-minimal-split-runtime-gap`: the VINTF-only control emits Wi-Fi
declaration rows, but native bounded `lshal list --types=binderized --neat -S`
times out before returning Samsung `ISehWifi/default` registrations.

No Wi-Fi enable, scan, connect, link-up, credentials, DHCP, routing, persistent
autostart, firmware mutation, rfkill write, module operation, or Android
partition write was executed.

## Implementation

- `stage3/linux_init/helpers/a90_android_execns_probe.c`
  - bumped helper marker to `a90_android_execns_probe v30`;
  - added `wifi-hal-composite-lshal-binderized-status-list`;
  - query child argv:
    `/system/bin/lshal list --types=binderized --neat -S`.
- `scripts/revalidation/wifi_execns_helper_v30_deploy_preflight.py`
  - deploys only `/cache/bin/a90_android_execns_probe`;
  - checks v30 minimal split strings before deploy.
- `scripts/revalidation/wifi_hal_lshal_minimal_split_v429_runner.py`
  - runs VINTF-only control first;
  - blocks live execution unless SELinuxfs status is visible;
  - runs bounded binderized-only status query;
  - records clean postflight process and Wi-Fi link surfaces.

## Static Validation

```text
scripts/revalidation/build_android_execns_probe_helper.sh \
  tmp/wifi/v429-a90_android_execns_probe-v30/a90_android_execns_probe

artifact: tmp/wifi/v429-a90_android_execns_probe-v30/a90_android_execns_probe
sha256: 65b279db9f5a66979140b71688cd3998ddc5832c1ca374e2187db981d5c17757
readelf: There is no dynamic section in this file.
```

```text
python3 -m py_compile \
  scripts/revalidation/wifi_execns_helper_v30_deploy_preflight.py \
  scripts/revalidation/wifi_hal_lshal_minimal_split_v429_runner.py

git diff --check
```

Both checks passed.

## Evidence

Plan and preflight:

```text
tmp/wifi/v429-helper-v30-deploy-plan-20260520-143308/
tmp/wifi/v429-lshal-minimal-split-plan-20260520-143308/
tmp/wifi/v429-helper-v30-deploy-preflight-20260520-143314/
tmp/wifi/v429-lshal-minimal-split-preflight-predeploy-20260520-143333/
```

Deploy:

```text
tmp/wifi/v429-helper-v30-deploy-live-20260520-143348/
decision: execns-helper-v30-deploy-pass
device_mutations: True
daemon_start_executed: False
wifi_bringup_executed: False
```

Live:

```text
tmp/wifi/v429-lshal-minimal-split-preflight-postdeploy-20260520-144017/
decision: v429-lshal-minimal-split-preflight-ready

tmp/wifi/v429-lshal-minimal-split-live-20260520-144031/
decision: v429-lshal-minimal-split-runtime-gap
pass: True
reason: status query failed: lshal-timeout; VINTF rows present=True
device_commands_executed: True
device_mutations: True
daemon_start_executed: True
wifi_hal_start_executed: True
wifi_bringup_executed: False
```

Postflight:

```text
status: rc=0 status=ok
selftest: pass=11 warn=1 fail=0
```

## VINTF Control Findings

The VINTF-only control still exits nonzero because `lshal` attempts to obtain a
default service manager, but it emits declaration rows before exit:

```text
wifi_hal_service_query.variant=vintf-status-only
wifi_hal_service_query.result=service-query-runtime-gap
wifi_hal_service_query.reason=lshal-nonzero
Failed to get defaultServiceManager()!
```

Wi-Fi declaration rows include:

```text
DM,FC declared android.hardware.wifi.hostapd@1.2::IHostapd/default
DM,FC declared android.hardware.wifi.supplicant@1.3::ISupplicant/default
DM,FC declared android.hardware.wifi@1.4::IWifi/default
DM    declared vendor.samsung.hardware.wifi.hostapd@3.0::ISehHostapd/default
DM,FC declared vendor.samsung.hardware.wifi.supplicant@3.1::ISehSupplicant/default
DM,FC declared vendor.samsung.hardware.wifi@2.2::ISehWifi/default
```

Target interpretation:

```text
vendor.samsung.hardware.wifi@2.0::ISehWifi/default: absent
vendor.samsung.hardware.wifi@2.1::ISehWifi/default: absent
vendor.samsung.hardware.wifi@2.2::ISehWifi/default: declared
```

## Binderized Status Query Findings

The live binderized-only query used the reduced argv:

```text
wifi_hal_service_query.variant=binderized-status
wifi_hal_service_query.child.argv.1=list
wifi_hal_service_query.child.argv.2=--types=binderized
wifi_hal_service_query.child.argv.3=--neat
wifi_hal_service_query.child.argv.4=-S
```

It still timed out:

```text
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

V429 rules out V428's `-p -e -c` and mixed `binderized,vintf` output as the
primary cause. Even binderized-only status listing does not return under the
native private composite stack. The live native stack can keep
`servicemanager`, `hwservicemanager`, and the first Samsung Wi-Fi HAL process
alive and cleanly stop them, but it still does not prove Samsung
`ISehWifi/default` hwservice registration.

The strongest current conclusion is:

- native VINTF surface declares `vendor.samsung.hardware.wifi@2.2::ISehWifi/default`;
- Android boot-complete evidence remains richer, showing `@2.0`, `@2.1`, and
  `@2.2` target rows;
- native binderized `lshal` queries still time out without Wi-Fi bring-up;
- postflight cleanup remains reliable.

## Next

Recommended next cycle: V430 Android explicit-column mirror.

V430 should boot Android to `sys.boot_completed=1`, run read-only `lshal`
commands with the same minimal columns, then restore native v319. This directly
answers whether Android boot-complete returns binderized status rows that native
private runtime cannot. If Android returns the rows and native still times out,
the next design should pivot toward Android-managed Wi-Fi runtime control
instead of deeper native service-manager reconstruction.
