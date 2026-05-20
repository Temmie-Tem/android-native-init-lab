# Native Init V423 Android hwservice Inventory Plan

Date: 2026-05-20

## Scope

V423 collects read-only Android-side evidence for the post-V422 registration
question.  V422 showed that the private native runtime can launch targeted
`lshal wait` probes and cleanly recover, but none of the V414 Samsung
`ISehWifi/default` targets became observable there.

V423 therefore asks the same target question in the full Android runtime:

```text
vendor.samsung.hardware.wifi@2.0::ISehWifi/default
vendor.samsung.hardware.wifi@2.1::ISehWifi/default
vendor.samsung.hardware.wifi@2.2::ISehWifi/default
```

## Guardrails

The collector is read-only and must not:

```text
svc wifi
cmd wifi set-wifi-enabled
scan/connect/link-up
rfkill or sysfs writes
module load/unload
setprop
reboot/flash/partition write
wificond/supplicant/hostapd/CNSS/Wi-Fi HAL daemon start command
```

It may run only passive inventory commands such as:

```text
adb devices -l
adb get-state
getprop selected service state
ps service/HAL filters
lshal list --types=binderized --neat
service list name filter
dumpsys -l name filter
VINTF grep
ip link show and rfkill state reads
```

## Implementation

```text
scripts/revalidation/wifi_android_hwservice_inventory_v423.py
```

Modes:

```text
plan: no device command
preflight: adb state only
run: read-only Android inventory only if adb state is device
```

## Expected Decisions

```text
v423-android-hwservice-inventory-plan-ready
v423-android-hwservice-adb-online
v423-android-hwservice-waiting-for-android
v423-android-hwservice-targets-present
v423-android-hwservice-wifi-present-target-mismatch
v423-android-hwservice-no-wifi-targets
v423-android-hwservice-lshal-incomplete
```

## Next Branch

If Android is not currently booted, the next step is a separate handoff packet
that boots Android, runs the V423 collector, and rolls back to native init with
boot-image readback verification.
