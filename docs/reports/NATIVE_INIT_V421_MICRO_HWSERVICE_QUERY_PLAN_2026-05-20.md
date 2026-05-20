# Native Init V421 Micro Hwservice Query Plan

Date: 2026-05-20

## Scope

V421 is a host-only plan packet for the next Wi-Fi registration proof after the
V419 bounded binderized `lshal` timeout.  It executed no bridge/device command,
deployed no helper, started no daemon/HAL, and did not attempt Wi-Fi bring-up.

## Implementation

```text
scripts/revalidation/wifi_v421_micro_hwservice_query_plan.py
docs/plans/NATIVE_INIT_V421_MICRO_HWSERVICE_QUERY_PLAN_2026-05-20.md
```

Evidence:

```text
tmp/wifi/v421-micro-hwservice-query-plan-20260520-124904/
```

## Result

```text
decision: v421-micro-hwservice-query-plan-ready
pass: True
reason: V420 requires a narrower hwservicemanager query and V414 target patterns are available
next: implement helper v28 micro listByInterface mode and fail-closed runner
proposed_helper_version: a90_android_execns_probe v28
proposed_helper_mode: wifi-hal-composite-hwservice-listbyinterface
proposed_runner: scripts/revalidation/wifi_hal_micro_hwservice_query_v421_runner.py
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

Target queries:

```text
listByInterface(vendor.samsung.hardware.wifi@2.0::ISehWifi) expect default
listByInterface(vendor.samsung.hardware.wifi@2.1::ISehWifi) expect default
listByInterface(vendor.samsung.hardware.wifi@2.2::ISehWifi) expect default
```

Future live approval phrase:

```text
approve v421 micro hwservicemanager listByInterface proof only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Rationale

V419 proved that even binderized-only `lshal` is still too broad or slow for
this private namespace.  V421 therefore narrows the next runtime question to a
single `hwservicemanager` method: `IServiceManager.listByInterface(fqName)`.

The first micro gate intentionally excludes `getService`/`get`, scan/connect,
link-up, credentials, DHCP, routing, and any Wi-Fi bring-up.

## References

```text
https://android.googlesource.com/platform/system/libhidl/+/refs/heads/android12L-tests-dev/transport/manager/1.0/IServiceManager.hal
https://android.googlesource.com/platform/system/hwservicemanager/+/refs/heads/master/ServiceManager.cpp
https://android.googlesource.com/platform/frameworks/native/+/013be5f/cmds/lshal/ListCommand.cpp
```
