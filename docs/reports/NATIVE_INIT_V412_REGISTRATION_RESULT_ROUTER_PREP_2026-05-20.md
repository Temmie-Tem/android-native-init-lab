# Native Init V412 Registration Result Router Prep

Date: 2026-05-20

## Scope

V412 prepares the next branch after V411 without changing the device.  It reads
V411 binderized registration evidence and routes the next safe action.

This pass executed no bridge/device command, helper deploy, daemon start, Wi-Fi
HAL start, scan/connect/link-up, or Wi-Fi bring-up.

## Implementation

```text
scripts/revalidation/wifi_v412_registration_result_router.py
```

The router consumes a V411 manifest and optionally the V411
`native/run-registration-query.txt` capture referenced by that manifest.

## Static Checks

```text
python3 -m py_compile scripts/revalidation/wifi_v412_registration_result_router.py
```

Wi-Fi service candidate parser smoke:

```text
android.hardware.wifi@1.0::IWifi/default -> parsed
vendor.qti.hardware.wifi.hostapd@1.0::IHostapd/default -> parsed
noise without target -> ignored
```

## Current Evidence

```text
tmp/wifi/v412-registration-router-current-20260520-115708/
```

Result:

```text
decision: v412-registration-router-waiting-for-v411-deploy
pass: True
reason: V411 query is still blocked before live run
next: execute exact-approved V411 helper v27 deploy, then rerun V411 query preflight
device_commands_executed: False
device_mutations: False
wifi_bringup_executed: False
```

## Interpretation

V412 is prepared, but it does not supersede the current live gate.  The current
V411 evidence still routes to helper v27 deploy first because the remote helper
is v26.

Next required action remains:

```text
approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up
```

After that deploy, rerun V411 preflight and then use the router again to select
between:

- waiting for V411 live query;
- Wi-Fi service candidates ready;
- no Wi-Fi service parsed;
- micro registration query needed;
- lshal tool missing.

## References

- AOSP HAL overview: <https://source.android.com/docs/core/architecture/hal>
- AOSP lshal source: <https://android.googlesource.com/platform/frameworks/native/+/013be5f/cmds/lshal/ListCommand.cpp>
