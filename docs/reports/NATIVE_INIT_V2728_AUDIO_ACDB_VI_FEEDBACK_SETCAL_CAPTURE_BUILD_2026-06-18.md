# NATIVE_INIT V2728 — vi-feedback ACDB SET capture build

Date: 2026-06-18

## Scope

Host-only build-only unit. No Android handoff, device flash, native replay SET,
mixer write, PCM write, AudioTrack, or speaker write was performed. Raw ACDB bytes
remain private-only.

## Decision

- decision: `v2728-acdb-vi-feedback-setcal-capture-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2728-acdb-vi-feedback-setcal-capture-build-only`
- helper: `workspace/private/builds/audio/v2728-acdb-vi-feedback-setcal-capture-build-only/bin/a90_acdb_vi_feedback_setcal_capture_exec_linked_v2728`
- helper_sha256: `89c32a607f931c7f019aed77b517ecc5c2c6344c88eab468cd171d3f42dfc911`
- preload: `workspace/private/builds/audio/v2728-acdb-vi-feedback-setcal-capture-build-only/bin/liba90_acdb_vi_feedback_setcal_capture_combined_preload_v2728.so`
- preload_sha256: `1212a2886d4eaaf37a4f9b0152dfab465a247550a5e7f257e751d5ad4edc9735`

## Why This Unit

V2726 proved the corrected native speaker ACDB SET sequence reaches the kernel
successfully but PCM prepare still fails at AFE/q6asm/ADM. V2727 re-read Android-good
evidence and identified a preceding `vi-feedback` ACDB path that native has not
captured or replayed: `acdb_id=102`, `path=1`, `app_type=0x11132`, 8000 Hz, and
`AUDIO_SET_AFE_CAL cal_type[17]`.

## Capture Contract

- reuses the V2630 fake `AUDIO_SET_CALIBRATION` arg + dma-buf capture shim
- keeps the V2611/V2613 meta-list init path so `acdb_loader_init_v3` can return cleanly
- arms capture only after `init_v3` returns
- calls `acdb_loader_send_audio_cal_v5(102, 1, 0x11132, 8000, 0, 8000, 1)`
- future live success requires byte-captured vi-feedback SET records, especially `cal_type=17` / `acdb_id=102`
- guessed geometry from this report must not be replayed natively before live capture verification

## Boundary

- no helper `/dev/msm_audio_cal` open and no helper ioctl
- no real `AUDIO_SET_CALIBRATION` pass-through
- no native replay, mixer, PCM, AudioTrack, or speaker write
- no raw payloads or proprietary libraries in public paths

## Build Evidence

- source_required_ok: `True`
- source_prohibited_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'undefined_send_audio_cal_v5': True, 'undefined_or_weak_a90_arm_capture': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True, 'soname_v2728': True}`
- helper_compile_ok: `True`
- preload_compile_ok: `True`

## Next Unit

Run the rollbackable Android-good own-process capture handoff with these artifacts,
force `A90_ACDB_FAKE_ALLOCATE=1`, pull `acdb-v2728-vi-feedback-setcal-events.jsonl`,
`setcal-events.jsonl`, `ioctl-trace-events.jsonl`, and private `setcal-*` raw files,
then rollback to V2321. Classify before any native replay extension.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_vi_feedback_setcal_capture_v2728.py tests/test_build_android_acdb_vi_feedback_setcal_capture_v2728.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_vi_feedback_setcal_capture_v2728 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_vi_feedback_setcal_capture_v2728.py --build --write-report`
- `git diff --check`
