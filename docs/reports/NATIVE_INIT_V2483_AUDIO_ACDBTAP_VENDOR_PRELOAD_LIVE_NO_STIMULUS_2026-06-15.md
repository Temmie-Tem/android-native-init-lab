# NATIVE_INIT V2483 — ACDB tap vendor-preload live rerun classified as runner wiring failure

Date: 2026-06-15

## Decision

`v2481-acdbtap-vendor-preload-live-no-acdbtap-events-before-rollback-rollback-pass`

This is **not** evidence that the `acdb_ioctl` tap is ineffective. The live rerun did not
exercise the intended capture condition:

1. the APK AudioTrack stimulus was never installed, so `am start` failed with
   `Error type 3` / `Activity class ... does not exist`;
2. the manual `LD_PRELOAD` HAL process mapped `libacdbtap.so`, but Android audio logs and
   ACDB-loader activity remained on the init-managed HAL PID, not the manual process.

Therefore this run is a harness/wiring failure, not a negative ACDB capture result.

## Evidence

- Run directory:
  `workspace/private/runs/audio/v2481-acdbtap-vendor-preload-live-20260615-231724`
- V2480 module install and vendor-path exposure succeeded:
  - `/vendor/lib/libacdbtap.so`
  - `/system/vendor/lib/libacdbtap.so`
  - SHA-256: `7bf64bb04530202a8dc859db0826cd399ff34d51ea4628eb586808de82968be4`
- Capture directory setup succeeded, but `/data/local/tmp/a90-acdb-tap/` remained empty.
- Manual preload start output:
  - `A90_ACDBTAP_OLD_PIDS_STILL_PRESENT 3588`
  - `A90_ACDBTAP_MANUAL_HAL_PIDS 3588 4014`
  - `A90_ACDBTAP_PRELOAD_CONFIRMED pid=4014 path=/vendor/lib/libacdbtap.so`
- The pre-playback ACDB-loader and audio HAL logs were from PID `3588`, not PID `4014`.
- Playback stimulus did not run:
  - `playback-start-background.stdout.txt` reported:
    `Error: Activity class {com.a90.nativeinit.audio/com.a90.nativeinit.audio.A90AudioRouteStimulusActivity} does not exist.`
  - `stimulus-logcat.stdout.txt` showed the Activity start attempt, but no
    `A90_AUDIO_STIMULUS_*` markers.
- Rollback to V2321 passed:
  - `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
  - `selftest: pass=11 warn=1 fail=0`

## Classification

The private `result.json` currently reports:

```json
{
  "classification": "no-acdbtap-events",
  "event_count": 0,
  "raw_file_count": 0,
  "target_4916_count": 0,
  "partial_success": false,
  "counts_toward_fails_twice": true
}
```

That mechanical classification is misleading for this rerun because the stimulus failed before
AudioTrack playback and the preloaded process was not the service process handling audio. Treat
this as **runner-wiring failure** for planning, not as an ACDB-tap dead run.

The operator's updated policy still stands for future real capture attempts:
`captured-acdbtap-full-outbuf-set-no-4916` is an operator-valuable **partial success** and must be
preserved rather than counted as a dead retry.

## Next unit

V2484 should fix both wiring gaps before another live capture:

1. Stage/install the private V2373/V2376 AudioTrack APK before `am start`, and fail fast if
   `cmd package path com.a90.nativeinit.audio` is absent.
2. Stop relying on a parallel manual HAL process as sufficient. The runner must prove that the
   process handling Android audio has `libacdbtap.so` mapped, or move to an init-service overlay /
   wrapper strategy so the init-managed `vendor.audio-hal` starts with `LD_PRELOAD`.
3. Preserve the full `/data/local/tmp/a90-acdb-tap/` directory on every run. If any `out_len>0`
   records exist but no `4916` record appears, classify as partial success per operator policy.

## Validation

- Host analysis only for this report.
- No new device action.
- Raw captures remain private; no raw payload bytes are committed.
