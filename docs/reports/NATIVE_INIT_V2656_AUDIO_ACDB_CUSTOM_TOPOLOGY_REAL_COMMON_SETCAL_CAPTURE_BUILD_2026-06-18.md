# NATIVE_INIT V2656 — ACDB custom-topology real-common SET capture build

Date: 2026-06-18

## Scope

Host-only build-only unit. No Android handoff, device flash, native replay, real
`AUDIO_SET_CALIBRATION`, mixer write, PCM write, or speaker playback occurred.
Raw ACDB bytes remain private-only.

## Decision

- `decision`: `v2656-acdb-custom-topology-real-common-setcal-capture-build-only`
- `ok`: `True`
- `build_root`: `workspace/private/builds/audio/v2656-acdb-custom-topology-real-common-setcal-capture-build-only`
- helper: `workspace/private/builds/audio/v2656-acdb-custom-topology-real-common-setcal-capture-build-only/bin/a90_acdb_custom_topology_real_common_setcal_capture_exec_linked_v2656`
- helper_sha256: `d93bbeb645dbb48f34f50451338058ce5c8b5648ee707aea889fcd03cd795406`
- preload: `workspace/private/builds/audio/v2656-acdb-custom-topology-real-common-setcal-capture-build-only/bin/liba90_acdb_custom_topology_real_common_setcal_capture_combined_preload_v2656.so`
- preload_sha256: `f513a3626a01386ac43334a6629b0fe20e9badb892ebfe938e14f4b2ad9aa7e1`

## Capture Contract

- helper call order: `init_v3 -> arm -> send_common_custom_topology -> send_audio_cal_v5`
- preinit is compiled with `-DA90_V2608_CALL_REAL_COMMON_TOPOLOGY=1` so the real common-topology path
  runs before the initialized-flag patch returns to `init_v3`
- preload is the V2630 fake-SET shim: dump SET arg bytes, mmap same-process dma-buf
  if present, then fake-success the SET so no kernel SET is delivered during capture
- target acceptance for the future live run: byte-exact SET records for cal_types
  `10`, `14`, and `24`
- cal_type `20` is retained as supplemental evidence, but cal20 alone is not success

## Source Checks

- required_ok: `True`
- prohibited_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'undefined_send_audio_cal_v5': True, 'undefined_or_weak_a90_arm_capture': True, 'undefined_common_topology': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True, 'soname_v2656': True}`

## Next Unit

A future live handoff can stage these artifacts into the existing V2490/V2631 Android-good
own-process runner. It must keep `A90_ACDB_FAKE_ALLOCATE=1`, pull the full private
`setcal-events.jsonl` plus raw files, and classify success only if cal_types `10`, `14`,
and `24` are captured byte-exact.

## Validation

- `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec were reread.
- source checks verify common-topology call order and fake-SET boundary.
- ARM32 build artifacts are private under `workspace/private/builds/audio/`.
- `py_compile`, focused unittest, build invocation, `file`/symbol checks, and
  `git diff --check` were run.
