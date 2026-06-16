# NATIVE_INIT V2602 — ACDB V2600 preload override live result

Date: 2026-06-16

## Scope

Android-good live handoff using the V2600 ACDB indirect-buffer tap as an override preload. The run stayed inside the measurement boundary: fake audio-cal allocation was enabled, real `AUDIO_SET_CALIBRATION` passthrough was suppressed, raw captures remained private, and checked rollback returned to V2321.

## Decision

- decision: `v2592-ownprocess-helper-sigsegv-no-events-rollback-pass`
- ok: `False`
- classification: `v2573-ownprocess-helper-sigsegv-no-events`
- private run: `workspace/private/runs/audio/v2592-acdb-perdevice-rx-capmask-argorder-20260616-173137`
- preload used: `workspace/private/builds/audio/v2600-acdb-indirect-buffer-tap-build-only/bin/liba90_acdb_indirect_buffer_tap_v2600.so`
- preload sha256: `a8afef2ebc8f64f6df041f5ed2b4b1808601ef5e3e24e222669c93f7b98fa746`

## Live Evidence

- helper rc: `139`
- helper stderr tail: `Segmentation fault`
- `acdbtap_row_count`: `0`
- `acdbtap_call_row_count`: `0`
- `acdbtap_event_path`: `None`
- `send_audio_cal_v5_reached`: `False`
- ioctl trace event count: `57`
- fake `AUDIO_ALLOCATE_CALIBRATION` count: `26`
- fake `AUDIO_DEALLOCATE_CALIBRATION` count: `1`
- fake `AUDIO_SET_CALIBRATION` count: `1`
- real `AUDIO_SET_CALIBRATION` passthrough count: `0`
- checked rollback: passed; result decision ended in `rollback-pass`

## Diagnosis

This is a host-composition failure, not a negative result for the V2600 tap or for `send_audio_cal_v5`.

The V2592 live runner was invoked with `--preload-path` pointing directly at the V2600 tap-only artifact. That artifact exports the guarded `acdb_ioctl`/`ioctl` interposers, but it does not include the V2572/V2591 preinit hook that calls `a90_arm_capture()` and then drives the corrected `send_audio_cal_v5` per-device path. With no hook, V2600 stayed unarmed and no `acdbtap` records were emitted before the known own-process helper SIGSEGV.

The fake allocation boundary still held: all allocation/deallocation/SET calls were intercepted in-process and no real SET was passed to `/dev/msm_audio_cal`.

## Correct Next Unit

Build a combined preload rather than overriding with tap-only V2600:

- V2600 tap behavior: post-init/manual arm only, full `in_buf` capture, indirect `{length,pointer}` candidate capture.
- V2531 fake audio-cal ioctl behavior: fake allocate/deallocate/SET success with no real SET passthrough.
- V2572 preinit per-device hook with V2591 overrides:
  - `A90_SPEAKER_RX_PATH=1`
  - `A90_SEND_AUDIO_CAL_V5_FIXED_STACK_ORDER=1`

The next live attempt should use the V2591 helper plus that new combined preload. Re-running V2592 with the tap-only V2600 preload would only reproduce this composition error.

## Validation

- Parsed `/tmp/v2602-live.json` and private run metadata only.
- No raw ACDB payload bytes were read into the report or committed.
- `git diff --check`
