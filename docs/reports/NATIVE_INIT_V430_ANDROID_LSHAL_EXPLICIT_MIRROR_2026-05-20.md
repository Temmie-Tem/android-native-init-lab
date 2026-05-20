# Native Init V430 Android lshal Explicit Mirror Report

Date: 2026-05-20

## Summary

V430 added a boot-complete Android handoff runner and an Android-side read-only
`lshal` mirror collector.  The corrected live run passed with:

```text
decision: v430-android-explicit-targets-present-status-crash
pass: True
reason: Android neat lshal sees all Samsung ISehWifi targets, but explicit status query exited rc=136
wifi_bringup_executed: False
```

No Wi-Fi enable, scan, connect, link-up, credentials, DHCP, routing, rfkill/sysfs
write, module operation, persistent autostart change, or direct daemon start was
executed by the test.

## Implementation

- `scripts/revalidation/wifi_android_lshal_explicit_v430.py`
  - collects Android read-only service/process/property and `lshal` evidence;
  - runs V429-equivalent VINTF and binderized status commands;
  - keeps a binderized `--neat` Wi-Fi-filter fallback for target row evidence;
  - redacts serial/MAC/credential-like text and writes private evidence.
- `scripts/revalidation/android_lshal_explicit_handoff_v430.py`
  - reuses the V424/V425 flash, boot-complete, rollback, and private evidence
    patterns;
  - compares V430 Android evidence with V429 native `lshal-timeout` evidence.

## Static Validation

```text
python3 -m py_compile \
  scripts/revalidation/wifi_android_lshal_explicit_v430.py \
  scripts/revalidation/android_lshal_explicit_handoff_v430.py

git diff --check
```

Both checks passed.

Plan and dry-run evidence:

```text
tmp/wifi/v430-android-lshal-explicit-plan-20260520-145016/
tmp/wifi/v430-android-lshal-explicit-handoff-plan-20260520-145016/
tmp/wifi/v430-android-lshal-explicit-handoff-dryrun-20260520-145037/
tmp/wifi/v430-android-lshal-explicit-plan-fix-20260520-145450/
tmp/wifi/v430-android-lshal-explicit-handoff-dryrun-fix-20260520-145450/
```

## Live Evidence

Corrected live handoff:

```text
tmp/wifi/v430-android-lshal-explicit-handoff-live-fix-20260520-145456/
decision: v430-android-explicit-targets-present-status-crash
pass: True
device_commands_executed: True
device_mutations: True
wifi_bringup_executed: False
```

Collector evidence:

```text
tmp/wifi/v430-android-lshal-explicit-handoff-live-fix-20260520-145456/v430-android-lshal-explicit-run/
decision: v430-android-lshal-targets-present-status-crash
pass: True
adb_state: device
boot_complete: True
binderized_status_rc: 136
```

Rollback/postflight:

```text
version: A90 Linux init 0.9.61 (v319)
selftest: pass=11 warn=1 fail=0
status: rc=0 status=ok
```

## Target Findings

VINTF status query on Android boot-complete:

```text
vendor.samsung.hardware.wifi@2.0::ISehWifi/default: absent
vendor.samsung.hardware.wifi@2.1::ISehWifi/default: absent
vendor.samsung.hardware.wifi@2.2::ISehWifi/default: listed
```

Binderized status query:

```text
command: lshal list --types=binderized --neat -S
rc: 136
vendor.samsung.hardware.wifi@2.0::ISehWifi/default: declared-not-fetchable
vendor.samsung.hardware.wifi@2.1::ISehWifi/default: declared-not-fetchable
vendor.samsung.hardware.wifi@2.2::ISehWifi/default: declared-not-fetchable
```

Binderized neat fallback:

```text
vendor.samsung.hardware.wifi@2.0::ISehWifi/default: listed-not-fetchable
vendor.samsung.hardware.wifi@2.1::ISehWifi/default: listed-not-fetchable
vendor.samsung.hardware.wifi@2.2::ISehWifi/default: listed-not-fetchable
```

Android boot-complete also showed these relevant live process/service surfaces:

```text
android.hardware.wifi@1.0-service
vendor.samsung.hardware.wifi@2.0-service
wificond
wpa_supplicant
wifi / sem_wifi / wifiscanner framework services
```

## Interpretation

V430 changes the conclusion from “Android probably has richer service evidence”
to a narrower, test-backed result:

- Android boot-complete has all three Samsung `ISehWifi/default` target rows in
  binderized neat output, but the rows are not fetchable;
- Android `lshal -S` is not a reliable next probe on this image because it exits
  with rc `136`;
- VINTF still declares only `vendor.samsung.hardware.wifi@2.2::ISehWifi/default`;
- native V429 still times out on binderized status listing;
- Android already runs `vendor.samsung.hardware.wifi@2.0-service`,
  `android.hardware.wifi@1.0-service`, `wificond`, and `wpa_supplicant` after
  boot-complete without the V430 test starting them.

The next useful branch should stop trying to make `lshal -S` the decisive tool.
It should map Android's already-running Wi-Fi runtime services, init rc sources,
properties, sockets, and device nodes into a controlled native/Android-managed
bring-up plan.

## Next

Recommended next cycle: V431 Android Wi-Fi runtime gap map.

V431 should remain read-only and collect the exact Android-side runtime map for:

- init service definitions for `vendor.samsung.hardware.wifi@2.0-service`,
  `android.hardware.wifi@1.0-service`, `wificond`, and `wpa_supplicant`;
- relevant `init.svc.*`, `ro.vendor.*`, `persist.vendor.*`, and Wi-Fi framework
  properties without mutation;
- `/dev`, `/sys/class/net`, `/data/vendor/wifi`, and socket surfaces needed by
  the running daemons;
- deltas against the native private namespace materials.

Only after that map is complete should we decide whether the next live gate is
Android-managed Wi-Fi framework control or another native namespace repair.
