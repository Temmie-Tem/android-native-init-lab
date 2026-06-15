# NATIVE_INIT_V2454_AUDIO_ACDB_M1_HYBRID_LIVE_POST_MODULE_BOOTCOMPLETE_GAP_2026-06-15

## Summary

V2454 reran the exact AUD-5L hybrid late-observer live path after V2453 stage ADB wait
hardening. The V2453 fix worked: every staged shell/push/install step had a preceding
`adb wait-for-device`, and all module/APK staging steps passed.

The run still did not reach late observer startup, AudioTrack playback, or payload
collection. The new blocker is the hard post-module boot-complete recheck after the Android
reboot that activates the temporary Magisk `service.sh`.

## Private Evidence

- Run dir: `workspace/private/runs/audio/v2454-acdb-m1-hybrid-late-observer-20260615-165424`
- Host log: `workspace/private/runs/audio/v2454-acdb-m1-hybrid-late-observer-20260615-165424.host.log`
- Result decision: `v2451-acdb-m1-hybrid-late-observer-failed-before-rollback`
- Error: `android-post-module-reboot-settle-1-boot-complete failed rc=1`
- Boot-complete stdout: `boot-complete recheck failed: sys= dev=`

## What Passed

- Checked Android flash/handoff: passed.
- Initial Android `adb wait-for-device`, boot-complete recheck, and Magisk root check: passed.
- All V2453 staged waits: passed.
- `stage-0` / `stage-1` readonly Magisk namespace probes: passed.
- `stage-2` pre-residue check: passed.
- `stage-3` run/incoming/artifact setup: passed.
- `stage-4` through `stage-7` module file pushes: passed.
- `stage-8` APK install: passed.
- `stage-9` module install: passed with all incoming SHA checks and `A90_M1_INSTALL_OK`.
- Cleanup finalizer removed module/run paths.
- Android recovery reboot + checked V2321 rollback: passed.

Rollback evidence from private `rollback-v2321.stdout.txt`:

- `selftest: pass=11 warn=1 fail=0`
- `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`

## Classification

`post-module-boot-complete-hard-gate-before-late-observer`

This is not ACDB evidence and not a negative payload result. The failure occurred before:

- late observer startup;
- logcat capture window;
- AudioTrack playback;
- helper completion wait;
- artifact pull.

## Root Cause

V2451 still uses the V2450 post-module settle helper. That helper hard-fails a single
30-second boot-complete property recheck after post-module `adb wait-for-device`.

In V2454, `adb wait-for-device` returned after about `207.6s`, but `sys.boot_completed` and
`dev.bootcomplete` were still empty for the next 30 seconds. Cleanup immediately afterward
was able to use ADB and `su`, so the hard boot-complete gate is too brittle for this
post-module path.

## Next Unit

V2455 should harden the post-module settle path host-only:

- keep the long `adb wait-for-device` step;
- make the post-module boot-complete recheck a recorded soft gate or give it its own longer
  retry budget;
- continue to require Magisk root before late observer/playback;
- expose the behavior in dry-run output and tests;
- keep cleanup and V2321 rollback behavior unchanged.

Then rerun AUD-5L as a fresh live iteration.
