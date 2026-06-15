# NATIVE_INIT_V2525_AUDIO_ACDB_OWNPROCESS_ALLOCATE_CAL_CLASSIFIER_HOST_ONLY_2026-06-16

## Scope

- Unit: V2525 host-only parser fix for the V2490 own-process ACDB runner.
- Trigger: V2524 was correctly evidenced as `AUDIO_ALLOCATE_CALIBRATION` / `allocate_cal_block` failure, but the runner over-classified it as a vendor audio property denial.
- Goal: make future summaries classify the actual ACDB init blocker before broader AVC/vendor-property heuristics.

## Changes

- Added a new ACDB init-v3 classification bucket:
  - `init-v3-block-audio-allocate-calibration-failed`
- Added diagnostics flag:
  - `has_audio_allocate_calibration_failed`
- Detection matches the V2524 decisive ACDB log lines:
  - `Sending AUDIO_ALLOCATE_CALIBRATION`
  - `allocate_cal_block failed`
  - `Cannot allocate memory`
- Tightened vendor property denial detection so it requires a direct property-denial line or a `vendor_audio_prop` denial in the filtered log/dmesg source, not merely a readable `vendor_audio_prop` metadata line plus an unrelated `avc: denied` line.
- Precedence under `acdb_loader_init_v3` is now:
  1. ACDB files load failure
  2. ACPH init failure
  3. audio allocate-calibration failure
  4. `/dev/msm_audio_cal` open denial
  5. vendor audio property denial
  6. generic AVC/denial

## Regression Coverage

- Added a V2524-shaped test that includes:
  - root/Magisk run context;
  - ACDB init progress through ACPH/RTAC/MCS/FTS/ADIE RTAC;
  - `AUDIO_ALLOCATE_CALIBRATION` failure;
  - an unrelated AVC denial;
  - a readable `vendor_audio_prop` metadata line.
- Added a negative test proving the parser does not infer vendor-prop denial from unrelated denial text.
- Re-parsed the private V2524 artifact set with the patched code:
  - classification: `init-v3-block-audio-allocate-calibration-failed`
  - `has_audio_allocate_calibration_failed=true`
  - `has_vendor_audio_prop_denied=false`
  - `has_msm_audio_cal_open_denied=false`
  - `row_count=0`
  - `error_count=1`

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py`
  - Result: `21` tests passed.
- Private V2524 artifact reparse matched the intended new classification.

## Safety Boundary

- Host-only parser/test unit.
- No device action, no flash, no HAL injection, no playback, no native speaker write, and no native `/dev/msm_audio_cal` SET ioctl.

## Next Unit

- Audit/fix the own-process helper behavior after `acdb_loader_init_v3` returns an error code.
- The helper should emit the existing JSONL error event and exit promptly instead of hanging until the runner timeout.
- Do not rerun live until that error-exit behavior is understood or fixed.
