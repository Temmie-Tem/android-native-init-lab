# NATIVE_INIT V2613 — ACDB meta-list indirect-layout capture build

Date: 2026-06-16

## Scope

Host-only build-only unit after V2612. No Android handoff, device flash, native replay SET,
speaker write, ACDB command execution, or raw ACDB payload publication was performed.

## Decision

- decision: `v2613-acdb-meta-list-indirect-layout-capture-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2613-acdb-meta-list-indirect-layout-capture-build-only`
- helper: `workspace/private/builds/audio/v2613-acdb-meta-list-indirect-layout-capture-build-only/bin/a90_acdb_meta_list_indirect_layout_capture_exec_linked_v2613`
- helper_sha256: `e9c06a6b8228cbfd3aea833ba390b3d1731f2f9c5eea360b19454dc110ecf6f5`
- preload: `workspace/private/builds/audio/v2613-acdb-meta-list-indirect-layout-capture-build-only/bin/liba90_acdb_meta_list_indirect_layout_capture_combined_preload_v2613.so`
- preload_sha256: `cba96cb0e9f5ca292ecdf6e39239df8e915680e2688b5f2a56aa284125f7f8db`

## Why This Unit

V2612 reached `init_v3_return` and `send_audio_cal_v5_return` cleanly, but every direct
`acdb_ioctl` `out_buf` record was a four-byte size/status word. The useful per-device
payloads are indirect buffers whose pointers are embedded in the input structs for the
successful GET commands.

## Indirect Layout Contract

- `0x13265`: AUDPROC common: ptr=in_word4, cap=in_word3, len=out_word0
- `0x13269`: AUDPROC stream: ptr=in_word2, cap=in_word1, len=out_word0
- `0x1326e`: AUDPROC gain/VOL: ptr=in_word4, cap=in_word3, len=out_word0 when ret==0
- `0x1326f`: AFE common: ptr=in_word3, cap=in_word2, len=out_word0

The V2613 tap dumps these only after the real `acdb_ioctl` returns `ret==0`, uses
`out_word0` as the payload length, rejects zero length, rejects `len > cap`, and allows
high ARM32 Android user VAs such as the `0xeb...` pointers observed in V2612.

## Boundary

- no new helper behavior beyond the V2611 init/meta-list/send path
- no real `/dev/msm_audio_cal` allocate/deallocate/SET in fake mode
- no native replay, mixer, PCM, AudioTrack, or speaker write
- raw ACDB bytes remain private-only and are not committed

## Build Evidence

- source_required_ok: `True`
- source_prohibited_ok: `True`
- helper_compile_ok: `True`
- tap_compile_ok: `True`
- preinit_compile_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'undefined_send_audio_cal_v5': True, 'undefined_or_weak_a90_arm_capture': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True, 'soname_v2613': True}`

## Next Unit

Run a bounded Android-good live handoff with the V2613 helper/preload override. The expected
win is private `ind-ap-common`, `ind-ap-stream`, and `ind-afe-common` raw files with
`ret==0` and non-all-zero payloads. A no-4916 result remains partial success if these
per-device payloads are captured.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_meta_list_indirect_layout_capture_v2613.py tests/test_build_android_acdb_meta_list_indirect_layout_capture_v2613.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_meta_list_indirect_layout_capture_v2613 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_meta_list_indirect_layout_capture_v2613.py --build --write-report`
- `git diff --check`
