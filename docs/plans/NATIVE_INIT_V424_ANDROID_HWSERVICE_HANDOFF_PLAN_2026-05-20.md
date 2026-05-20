# Native Init V424 Android hwservice Handoff Plan

Date: 2026-05-20

## Scope

V424 turns the V423 read-only Android hwservice collector into a bounded live
handoff:

1. verify native init control;
2. transition to recovery/TWRP;
3. flash a known Android boot image with SHA/readback verification;
4. boot Android and run only the V423 read-only hwservice/lshal inventory;
5. return to recovery and restore the latest verified native init image;
6. verify native init protocol recovery.

This is not Wi-Fi bring-up.  The handoff does not run `svc wifi`, `cmd wifi`,
scan/connect/link-up, credentials, DHCP, routing, rfkill/sysfs writes, module
load/unload, property mutation, or direct Wi-Fi daemon start commands.

## Inputs

- Android boot candidate: `backups/baseline_a_20260423_025322/boot.img`
- Native rollback image: `stage3/boot_linux_v319.img`
- Native rollback marker: `A90 Linux init 0.9.61 (v319)`
- Android collector: `scripts/revalidation/wifi_android_hwservice_inventory_v423.py`

## Implementation

```text
scripts/revalidation/android_hwservice_handoff_v424.py
```

Modes:

```text
plan: generate command/evidence plan only
dry-run: record the full step list without device commands
run: execute the approved handoff/rollback sequence
```

Live mode requires all explicit approval flags:

```text
--allow-android-boot-flash
--assume-yes
--i-understand-native-rollback
```

## Safety Contracts

- Android and native boot images must both be 4 KiB aligned Android boot images.
- The native rollback image must contain the expected v319 marker.
- The selected Android boot image must not contain the native marker.
- Android boot flash is verified by remote SHA and boot partition prefix readback
  before booting Android.
- `run` inserts `wait-android-before-rollback` after V423 collection so transient
  ADB reconnects do not skip rollback.
- `hide` responses that explicitly say `hide requested` are accepted as a valid
  native menu hide request.
- V423 classification reads the full private command evidence file for `lshal`
  matching, not the truncated manifest preview.

## Expected Decisions

```text
v424-handoff-plan-ready
v424-handoff-dryrun-ready
v424-handoff-approval-required
v424-handoff-missing-native-rollback
v424-handoff-missing-android-boot
v424-handoff-image-collision
v424-handoff-active-wifi-command-blocked
v424-handoff-pass
v424-handoff-v423-capture-failed-rollback-complete
```

## Next Branch

If V424 succeeds, interpret V423 Android evidence carefully.  ADB `device` does
not guarantee Android boot completion, so V425 should add a boot-complete/settle
gate and rerun the same read-only inventory before treating target presence as
final registration proof.
