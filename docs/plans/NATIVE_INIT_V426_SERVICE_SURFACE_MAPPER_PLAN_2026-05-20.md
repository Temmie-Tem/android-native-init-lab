# Native Init V426 Service Surface Mapper Plan

Date: 2026-05-20

## Scope

V426 is a host-only follow-up to V425.  V425 proved that boot-complete Android
has all three Samsung `ISehWifi/default` fqinstances, while native V422 still
cannot observe them through targeted `lshal wait`.  V426 maps the Android
boot-complete Wi-Fi service surface from V425 evidence and extracts the native
private-runtime gap before any Wi-Fi bring-up work.

V426 must not execute ADB, mutate the device, start daemons, enable Wi-Fi,
scan/connect/link-up, touch credentials, run DHCP, or change routing.  It parses
existing V425/V423 evidence only.

## Implementation

```text
scripts/revalidation/wifi_v426_service_surface_mapper.py
```

Modes:

```text
plan: identify the latest V425 live manifest and record a no-device-command plan
run: parse V425/V423 command evidence and emit a service-surface/gap manifest
```

## Inputs

Default input discovery:

```text
tmp/wifi/v425-settled-handoff-live-*/manifest.json
```

Parsed evidence under the selected V425 run:

```text
v423-android-hwservice-bootcomplete-run/commands/identity-props.txt
v423-android-hwservice-bootcomplete-run/commands/service-processes.txt
v423-android-hwservice-bootcomplete-run/commands/lshal-binderized-neat.txt
v423-android-hwservice-bootcomplete-run/commands/lshal-wifi-filter.txt
v423-android-hwservice-bootcomplete-run/commands/service-list-wifi.txt
v423-android-hwservice-bootcomplete-run/commands/dumpsys-service-names-wifi.txt
v423-android-hwservice-bootcomplete-run/commands/vintf-wifi-hal.txt
v423-android-hwservice-bootcomplete-run/commands/netdev-rfkill-readonly.txt
```

## Surface Checks

V426 records these checks as structured `surface_items`:

- Android boot complete;
- framework Wi-Fi services (`wifi`, `wifiscanner`, Samsung `sem_wifi`);
- `hwservicemanager` and `vendor.wifi_hal_ext` running;
- `wificond`, `wpa_supplicant`, AOSP Wi-Fi HAL, Samsung Wi-Fi HAL processes;
- all three Samsung `ISehWifi/default` fqinstances;
- supplicant HIDL declarations;
- VINTF Wi-Fi declaration lines;
- `dumpsys -l` Wi-Fi service names.

## Expected Decisions

```text
v426-service-surface-mapper-plan-ready
v426-missing-v425-evidence
v426-android-surface-incomplete
v426-native-registration-surface-gap
v426-native-hal-lifecycle-gap
v426-gap-unclassified
```

## Next Branch

If V426 reports `v426-native-registration-surface-gap`, the next step should be
V427: build a minimal native-side read-only service-query improvement plan.
The target is not Wi-Fi bring-up yet; it is to determine whether the native
private runtime can observe the Samsung Wi-Fi fqinstances by adding the smallest
missing service-manager/hwservice/framework/supplicant surface, or whether that
requires switching to an Android-managed runtime path.
