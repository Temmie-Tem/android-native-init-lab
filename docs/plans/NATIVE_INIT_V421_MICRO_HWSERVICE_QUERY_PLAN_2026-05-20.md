# Native Init V421 Micro Hwservice Query Plan

Date: 2026-05-20

## Goal

V421 narrows the post-V419 runtime-registration question.  The bounded
binderized `lshal` query timed out, so the next gate should not retry broad
`lshal`; it should ask `hwservicemanager` for only the Samsung Wi-Fi HAL
interface candidates selected by V414.

## Inputs

```text
V419 query: v411-hal-registration-query-runtime-gap
V420 gate: v416-current-gate-micro-query-needed
V414 primary target: vendor.samsung.hardware.wifi@2.0-2::ISehWifi/default
```

Runtime match patterns:

```text
vendor.samsung.hardware.wifi@2.0::ISehWifi/default
vendor.samsung.hardware.wifi@2.1::ISehWifi/default
vendor.samsung.hardware.wifi@2.2::ISehWifi/default
```

## Reference Basis

- AOSP `IServiceManager.hal` defines `listByInterface(string fqName)` returning the instance names running that interface.
- AOSP `hwservicemanager` implements `listByInterface` by looking up a single `fqName` in its service map and returning only live instance names.
- AOSP `lshal` is a broader diagnostic path around HIDL service-manager state, so it remains useful context but is not the next live primitive after the timeout.

References:

```text
https://android.googlesource.com/platform/system/libhidl/+/refs/heads/android12L-tests-dev/transport/manager/1.0/IServiceManager.hal
https://android.googlesource.com/platform/system/hwservicemanager/+/refs/heads/master/ServiceManager.cpp
https://android.googlesource.com/platform/frameworks/native/+/013be5f/cmds/lshal/ListCommand.cpp
```

## Proposed Contract

Add helper v28 and a fail-closed runner:

```text
helper version: a90_android_execns_probe v28
helper mode: wifi-hal-composite-hwservice-listbyinterface
runner: scripts/revalidation/wifi_hal_micro_hwservice_query_v421_runner.py
```

Execution model:

1. Reuse the V411 private namespace materialization inputs.
2. Start only bounded `servicemanager`, `hwservicemanager`, and the first Wi-Fi HAL candidate.
3. Query only `android.hidl.manager@1.0::IServiceManager.listByInterface(fqName)`.
4. Try the V414 primary patterns in ranked order.
5. Mark pass only when the returned instance list contains `default`.
6. Do not call `getService`/`get` in the first micro gate.
7. Always terminate/reap bounded children and prove postflight clean.

## Boundary

Still out of scope:

```text
Wi-Fi scan/connect/link-up
credentials, DHCP, routing
wificond, supplicant, hostapd
CNSS lifecycle changes or diag daemon
rfkill writes, driver bind/unbind, firmware mutation
Android partition writes or persistence/autostart
```

Future approval phrase:

```text
approve v421 micro hwservicemanager listByInterface proof only; no scan/connect/link-up and no Wi-Fi bring-up
```

## Success Criteria

```text
v421-micro-hwservice-query-pass:
  listByInterface(target_fqName) returns default
  postflight clean
  wifi_bringup_executed=False

v421-micro-hwservice-query-no-registration:
  all target fqNames return empty lists
  postflight clean
  wifi_bringup_executed=False

v421-micro-hwservice-query-runtime-gap:
  query fails or times out
  postflight clean
  wifi_bringup_executed=False
```

## Next Step

Implement helper v28 and the V421 runner, then run plan/preflight first.  Live
execution remains separately gated even in bypass mode because it starts the
bounded manager/HAL trio.
