# NATIVE_INIT_V2452_AUDIO_ACDB_M1_HYBRID_LIVE_ADB_STAGE_GAP_2026-06-15

## Summary

V2452 executed the exact-gated AUD-5L hybrid late-observer live path using the V2451
runner. The run did not reach module staging, late observer startup, AudioTrack playback, or
payload collection.

The checked Android boot handoff passed, Android boot/root settle passed, and the runner
rolled back to V2321 cleanly. The failure was a transient ADB availability gap before the
stage-2 shell command.

## Private Evidence

- Run dir: `workspace/private/runs/audio/v2452-acdb-m1-hybrid-late-observer-20260615-164429`
- Host log: `workspace/private/runs/audio/v2452-acdb-m1-hybrid-late-observer-20260615-164429.host.log`
- Result decision: `v2451-acdb-m1-hybrid-late-observer-failed-before-rollback`
- Error: `stage-2 failed rc=1`
- Stage-2 stderr: `adb: no devices/emulators found`

## What Ran

- `flash-android`: passed through checked helper.
- Android post-handoff wait/boot/root settle: passed.
- `stage-0` and `stage-1` readonly Magisk namespace probes: passed.
- `stage-2` pre-residue check: failed before script execution because ADB reported no device.
- Cleanup finalizer: removed the temporary module/run paths if present.
- Android recovery reboot + checked V2321 rollback: passed.

Rollback evidence from private `rollback-v2321.stdout.txt`:

- `selftest: pass=11 warn=1 fail=0`
- `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`

## Classification

`android-adb-stage-gap-before-module-staging`

This is not ACDB evidence and not a negative payload result. The failure occurred before:

- module file transfer;
- module install;
- Android reboot for Magisk `service.sh`;
- late observer startup;
- AudioTrack playback;
- artifact pull.

## Root Cause

The V2451 runner only inserts `adb wait-for-device` before `adb push` and `adb install`
stage commands. V2452 shows Android ADB can transiently disappear between shell stage
commands after the initial Android root settle. The next runner must wait for ADB before
every stage command, not just push/install.

## Next Unit

V2453 should harden the V2451 runner host-only:

- add `adb wait-for-device` before every staged `adb shell`, `adb push`, and `adb install`
  command;
- expose the expanded wait plan in dry-run output;
- add regression tests proving shell stage commands are covered;
- keep all V2451 safety boundaries unchanged.

Then rerun AUD-5L as a fresh live iteration.
