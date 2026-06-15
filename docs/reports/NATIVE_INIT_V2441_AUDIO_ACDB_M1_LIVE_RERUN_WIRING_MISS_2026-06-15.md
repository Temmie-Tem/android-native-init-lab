# NATIVE_INIT_V2441_AUDIO_ACDB_M1_LIVE_RERUN_WIRING_MISS_2026-06-15

## Summary

V2441 ran the exact-gated M1 Magisk-module ACDB payload-capture route using the V2440
runner. The recoverable envelope held: the Android boot handoff ran through the checked
helper, the temporary module files were staged and installed, cleanup removed the module
and run directory, and the device rolled back to the V2321 native-init checkpoint with
final `selftest fail=0`.

The run did **not** reach logcat, playback, or artifact collection. It failed immediately
after the Magisk `service.sh` activation reboot at the same single-shot root-check edge as
V2439:

- `android-post-handoff-settle-0`: `adb wait-for-device` passed after `35.480s`.
- `android-post-handoff-settle-1`: Android boot-complete recheck passed.
- `android-post-handoff-settle-2`: `adb shell su -c id` failed with
  `adb: no devices/emulators found`.

Source inspection after the run explains the mismatch: V2440 added
`run_post_module_reboot_settle()`, but `run_live()` calls it immediately after the initial
Android flash handoff, before module staging. After the actual module-activation reboot,
`run_live()` still calls the older `v2396.run_android_post_handoff_settle()` single-shot
root check. Therefore V2441 validates that V2440's intended retry logic was wired into the
wrong reboot boundary.

## Safety and Cleanup

- Exact live approval phrase was accepted.
- Android boot image was flashed through `native_init_flash.py` with the expected Android
  SHA and readback SHA.
- Temporary M1 module install reached `A90_M1_INSTALL_OK` again.
- Cleanup-finally succeeded:
  - `A90_M1_CLEANUP_OK`
  - `/data/adb/modules/a90_audio_acdb_m1_v2429`: absent after cleanup.
  - `/data/local/tmp/a90-audio-acdb-m1-v2429`: absent after cleanup.
- Rollback used the checked V2321 boot image and completed successfully.
- Final resident native-init health:
  - `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
  - `selftest: pass=11 warn=1 fail=0`

No native speaker/mixer/PCM write, no native `/dev/msm_audio_cal` ioctl, no ACDB replay,
and no Wi-Fi action was performed.

## Evidence

Private run directory:

```text
workspace/private/runs/audio/v2441-acdb-m1-magisk-module-retry-20260615-142841
```

Key private evidence files:

```text
android-post-handoff-settle-2.stderr.txt
cleanup-finally-2.stdout.txt
cleanup-finally-3.stdout.txt
rollback-v2321.stdout.txt
result.json
```

Relevant public source wiring in V2440:

```text
workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_retry_live_handoff_v2440.py
```

`run_live()` currently does this:

1. Flash Android.
2. Call `run_post_module_reboot_settle(...)` before module staging.
3. Stage/install the M1 module.
4. Reboot Android for Magisk `service.sh` activation.
5. Call `v2396.run_android_post_handoff_settle(...)`, which is still the single-shot
   post-handoff root check.

That is the wrong boundary for V2440's retry logic.

## Classification

```text
post-module-reboot-settle-retry-wired-to-wrong-boundary
```

V2441 says nothing about whether the M1 observer can capture `/dev/msm_audio_cal` payload
ioctls. The temporary module still reaches install successfully. The remaining blocker is
host runner wiring, not Magisk module namespace, not staging, and not payload observer
semantics.

## Next Unit

V2442 should be host-only:

- Preserve V2438/V2440 module staging, SHA validation, observer payload, playback stimulus,
  cleanup, rollback, and native-audio boundaries.
- Use the normal Android post-handoff settle after the initial Android flash, or at least do
  not label it as post-module activation.
- Call `run_post_module_reboot_settle()` **after** `android-reboot-for-magisk-service`.
- Add a focused regression test proving `android-reboot-for-magisk-service` is followed by
  `android-post-module-reboot-root-check-*`, not `android-post-handoff-settle-2`.
- Do not rerun live until the dry-run and focused tests prove the retry loop is wired to the
  module-activation reboot.
