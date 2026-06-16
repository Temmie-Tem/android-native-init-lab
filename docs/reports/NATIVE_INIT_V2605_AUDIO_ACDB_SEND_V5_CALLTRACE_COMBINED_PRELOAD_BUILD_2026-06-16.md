# NATIVE_INIT V2605 — ACDB send_audio_cal_v5 calltrace combined preload build

Date: 2026-06-16

## Scope

Host-only build-only unit after V2604. No Android handoff, device flash, native replay SET,
speaker write, ACDB command execution, or raw ACDB payload publication was performed.

## Decision

- decision: `v2605-acdb-send-v5-calltrace-combined-preload-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2605-acdb-send-v5-calltrace-combined-preload-build-only`
- helper: `workspace/private/builds/audio/v2605-acdb-send-v5-calltrace-combined-preload-build-only/bin/a90_acdb_perdevice_rx_capmask_argorder_exec_linked_v2605`
- helper_sha256: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
- preload: `workspace/private/builds/audio/v2605-acdb-send-v5-calltrace-combined-preload-build-only/bin/liba90_acdb_send_v5_calltrace_combined_preload_v2605.so`
- preload_sha256: `b2cc5735813de666c2705f5a6b7895c3fcc71361e57afc780a32cf1fd0ca3d07`

## Why This Unit

V2604 proved the V2603 combined preload arms capture and reaches `before_send_audio_cal_v5`,
but the helper then times out before the first armed `acdb_ioctl` row. Another unchanged live
run would be low-information. V2605 adds import-call telemetry around the pre-first-GET region
so the next live run can classify whether the stop is at the initial mutex, at an Android log
call boundary after local setup, or deeper in an internal helper before the dispatcher GET.

## Contract

- base artifact: V2603 combined preload behavior is preserved.
- new hooks: `pthread_mutex_lock`, `pthread_mutex_unlock`, and `__android_log_print`.
- filter: only caller offsets in `acdb_loader_send_audio_cal_v5` range `0x9d30..0xa100` are logged.
- logged data: hook name, enter/return phase, pid/tid, caller address, caller offset, first argument pointer, and return code.
- no payload data, ACDB request buffers, speaker writes, or real `AUDIO_SET_CALIBRATION` are introduced.
- future live success remains `ret==0` plus non-all-zero ACDB buffers; this unit only localizes pre-GET control flow.

## Build Evidence

- calltrace_compile_ok: `True`
- calltrace_command_contains_source: `['pthread_mutex_lock', 'pthread_mutex_unlock', '__android_log_print']`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'soname_v2605': True, 'exports_pthread_mutex_lock': True, 'exports_pthread_mutex_unlock': True, 'exports_android_log_print': True, 'does_not_export_audio_set_helper': True}`

## Next Unit

Use the existing V2592 Android-good handoff with the V2605 preload override. The analysis should
read both `acdb-v2605-send-v5-calltrace-events.jsonl` and the existing `acdbtap` events. If
`pthread_mutex_lock enter` appears with no return, the stop is the initial mutex. If mutex returns
and Android-log call offsets advance but no `0x1122e` row appears, the stop is inside the local
pre-dispatch helper region. Do not proceed to native replay until operator-verified per-device bytes exist.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_send_v5_calltrace_combined_preload_v2605.py tests/test_build_android_acdb_send_v5_calltrace_combined_preload_v2605.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_send_v5_calltrace_combined_preload_v2605 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_send_v5_calltrace_combined_preload_v2605.py --build --write-report`
- `git diff --check`
