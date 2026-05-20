# Native Init V425 Boot-complete hwservice Handoff Plan

Date: 2026-05-20

## Scope

V425 closes the V424 ambiguity: V424 proved the Android handoff/rollback path
and showed Samsung Wi-Fi target rows, but the capture happened before
`sys.boot_completed=1`.  V425 repeats the same bounded handoff but waits for
Android boot completion before collecting V423 read-only hwservice evidence.

This is still not Wi-Fi bring-up.  The runner must not execute Wi-Fi enable,
scan/connect/link-up, credentials, DHCP, routing, rfkill/sysfs writes, module
load/unload, property mutation, or direct Wi-Fi daemon start commands.

## Implementation

```text
scripts/revalidation/android_hwservice_settled_handoff_v425.py
```

The runner reuses the V424 image, flash, readback, recovery, rollback, and
private evidence patterns, then inserts two Android-only read gates before V423:

```text
wait-boot-complete: poll read-only getprop until sys.boot_completed=1
settle-after-boot-complete: bounded sleep plus read-only getprop snapshot
```

After V423 completes and native v319 is restored, V425 compares:

- boot-complete Android V423 target matches;
- native V422 targeted `lshal wait` result;
- native V407 composite HAL start-only result.

## Inputs

- Android boot image: `backups/baseline_a_20260423_025322/boot.img`
- Native rollback image: `stage3/boot_linux_v319.img`
- Native marker: `A90 Linux init 0.9.61 (v319)`
- Android collector: `scripts/revalidation/wifi_android_hwservice_inventory_v423.py`
- Native comparison evidence: latest V422 and V407 manifests

## Expected Decisions

```text
v425-handoff-plan-ready
v425-handoff-dryrun-ready
v425-handoff-approval-required
v425-handoff-missing-native-rollback
v425-handoff-missing-android-boot
v425-handoff-active-wifi-command-blocked
v425-bootcomplete-targets-present-native-gap
v425-bootcomplete-partial-targets-present
v425-bootcomplete-no-targets
v425-handoff-failed-wait-boot-complete-rollback-complete
v425-handoff-v423-capture-failed-rollback-complete
```

## Next Branch

If boot-complete Android target evidence is present and native V422 still times
out, the next useful branch is not immediate Wi-Fi bring-up.  V426 should map
what Android boot-complete has that the native private runtime lacks:

- real Android service-manager registration state;
- `wpa_supplicant`/supplicant HAL state;
- Wi-Fi framework binder services;
- minimal read-only native gap list for service registration query support.
