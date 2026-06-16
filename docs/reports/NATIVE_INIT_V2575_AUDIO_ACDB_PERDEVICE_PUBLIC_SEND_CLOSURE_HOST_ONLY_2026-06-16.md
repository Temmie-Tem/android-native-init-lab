# NATIVE_INIT V2575 — ACDB per-device public-send closure

Date: 2026-06-16

## Scope

Host-only follow-up to V2574. No device action, Android handoff, native replay, speaker write, or private raw ACDB payload was performed.

## Inputs

- V2574 live run: `workspace/private/runs/audio/v2574-acdb-perdevice-indirect-capture-20260616-125616/`
- V2571 strategy report and V2572 source/build reports.
- `libacdbloader.so` export/disassembly around `acdb_loader_send_audio_cal_v5` and lower-level getter exports.

## Findings

1. V2574 reached the V2572 hook stages: `skip_real_common_topology`, `patch_initialized_flag_return=0`, and `before_send_audio_cal_v5`.
2. V2574 then timed out before any real armed `acdb_ioctl` enter/before-real/return event. The sole `acdbtap` JSONL row was the old arm marker (`phase=armed`, all zero cmd/length fields), not an actual ACDB call.
3. The fake audio-cal transport stayed inside bounds: 25 fake `AUDIO_ALLOCATE_CALIBRATION` events returned 0; no real `AUDIO_SET_CALIBRATION` pass-through was observed.
4. Re-parsing the V2574 artifacts after the parser fix classifies the base ACDB tap state as `ownprocess-context-only-no-events` with `acdbtap_control_row_count=1` and `acdbtap_call_row_count=0`.
5. The public `acdb_loader_send_audio_cal_v5(15,0,0x11135,48000,48000,0,1)` strategy is now closed for this route. V2570 and V2574 independently reached the call boundary but produced no per-device GET rows before timeout.

## Code Change

`native_audio_acdb_ownprocess_get_live_handoff_v2490.py` now treats legacy `phase=armed` rows with zero command/length fields as ACDB tap control markers, not real `acdb_ioctl_call` rows. This prevents future reports from misclassifying manual arm as a no-return ACDB call.

## Next Direction

Do not rerun V2572/V2573 unchanged. The next substantive unit should be host-only direct-GET design for the lower-level getter path, using exported helpers such as `acdb_loader_get_audio_cal_v2`, `acdb_loader_adsp_get_audio_cal`, and `acdb_loader_get_calibration`, or direct `acdb_ioctl` command construction once the request structs are pinned.

Native replay and real `AUDIO_SET_CALIBRATION` remain blocked until per-device payload bytes/order and cleanup policy are pinned.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490`
- V2574 private artifact reparse confirms `acdbtap_call_row_count=0`, `acdbtap_control_row_count=1`.
- `git diff --check` passed before commit.
