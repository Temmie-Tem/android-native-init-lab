# NATIVE_INIT V2611 — ACDB meta-list post-init send_audio_cal_v5 build

Date: 2026-06-16

## Scope

Host-only build-only unit after V2610. No Android handoff, device flash, native replay SET,
speaker write, ACDB command execution, or raw ACDB payload publication was performed.

## Decision

- decision: `v2611-acdb-meta-list-postinit-send-v5-combined-preload-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2611-acdb-meta-list-postinit-send-v5-combined-preload-build-only`
- helper: `workspace/private/builds/audio/v2611-acdb-meta-list-postinit-send-v5-combined-preload-build-only/bin/a90_acdb_meta_list_postinit_send_v5_exec_linked_v2611`
- helper_sha256: `e9c06a6b8228cbfd3aea833ba390b3d1731f2f9c5eea360b19454dc110ecf6f5`
- preload: `workspace/private/builds/audio/v2611-acdb-meta-list-postinit-send-v5-combined-preload-build-only/bin/liba90_acdb_meta_list_postinit_send_v5_combined_preload_v2611.so`
- preload_sha256: `7773add347fb7762aecd9b1ab1715bac1d1bd7ff3b5e1c9f82550bd606cba9a5`

## Why This Unit

V2609 proved the V2608 post-init route still crashed before `init_v3` returned. V2610
mapped the crash to `init_v4` dereferencing `arg0+8`, which `init_v3` fills from its
third argument. Passing `0` was therefore not a safe scalar flag; it made the init-tail
list walk dereference NULL.

## Contract

- helper prepares a process-local empty circular meta-list head and passes it as `init_v3` arg3.
- preload remains the V2608 no-send preinit hook: skip common topology, patch initialized flag, return.
- helper calls `a90_arm_capture()` only after `acdb_loader_init_v3` returns `0`.
- helper then calls `acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)`.
- future live success remains `ret==0` plus non-all-zero ACDB buffers; requested length alone is failure.

## Build Evidence

- source_required_ok: `True`
- source_prohibited_ok: `True`
- helper_compile_ok: `True`
- preinit_compile_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'undefined_send_audio_cal_v5': True, 'undefined_or_weak_a90_arm_capture': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True, 'soname_v2611': True}`

## Next Unit

Run the existing Android-good own-process runner with the V2611 helper/preload override.
Expected discriminator: `init_v3_return` should appear. If it does and `send_audio_cal_v5`
emits real armed `acdb_ioctl` rows, the per-device route remains viable. If it still crashes
before return, stop this route and continue direct pure-read getters.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_meta_list_postinit_send_v5_combined_preload_v2611.py tests/test_build_android_acdb_meta_list_postinit_send_v5_combined_preload_v2611.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_meta_list_postinit_send_v5_combined_preload_v2611 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_meta_list_postinit_send_v5_combined_preload_v2611.py --build --write-report`
- `git diff --check`
