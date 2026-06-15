# NATIVE_INIT V2516 — ACDB own-process Android settle retry hardening (host-only)

## Summary

- **Decision:** `v2516-acdb-ownprocess-android-settle-retry-host-only`
- **Scope:** host-only retry hardening for the V2490 own-process runner.
- **Device action:** none.
- **Flash action:** none.

V2515 did not reach the ACDB helper. It failed at `android-post-handoff-settle-1` with ADB `error: closed`, then rolled back to V2321 cleanly. This is a transport-stage gap before helper staging, not ACDB evidence. V2516 adds bounded retry for that exact class.

## Changes

Updated `workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py`:

- Added transport-only retry for `android-post-handoff-settle-0` and `android-post-handoff-settle-1`.
- Retry markers:
  - `error: closed`
  - `adb: no devices/emulators found`
  - `no devices/emulators found`
  - `device offline`
  - `failed to get feature set`
  - `protocol fault`
- Before retry attempts after the first, the runner issues `adb wait-for-device`.
- Semantic boot-complete failures still fail closed.
- Existing root recheck retry behavior is preserved.

Added tests in `tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py`:

- dry-run exposes retry metadata;
- `error: closed` is detected as retryable transport failure;
- semantic boot-complete failure text is not treated as retryable transport failure.

## Safety Boundary

This does not widen the ACDB action surface:

- No in-HAL injection.
- No Magisk module install.
- No HAL restart.
- No AudioTrack/playback.
- No native speaker write.
- No `/dev/msm_audio_cal` open or calibration ioctl.
- No `0xC00461CB` SET ioctl.

The retry applies only before helper staging and only for ADB transport failures.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
    --dry-run \
    --helper-path workspace/private/builds/audio/v2512-acdb-ownprocess-exec-linked-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2512 \
    --helper-sha256 aab66000e12d6c976a96b3d73d603e6bb9c935dcd5dc801d3f25410f46887dc6
```

Result:

- `py_compile` passed.
- Focused V2490 unittest passed: `14` tests.
- Dry-run remains `ok=True`, `live_ready=True`, `command_safety_ok=True`.
- Dry-run reports settle retry enabled with `attempts=3`, `sleep_sec=2.0`.
- `git diff --check` passed for the V2516-scoped paths.

## Next Step

Next live unit should rerun the V2490 own-process handoff with the V2512 helper and V2514/V2516 runner hardening:

- if transport flakes recur, the runner should retry pre-helper settle;
- if helper runs and still returns `-19`, the pulled diagnostics should classify the branch via `ACDB-LOADER` / AVC logs;
- if `acdb_ioctl` rows appear, proceed to ordered pure-read GET analysis.

