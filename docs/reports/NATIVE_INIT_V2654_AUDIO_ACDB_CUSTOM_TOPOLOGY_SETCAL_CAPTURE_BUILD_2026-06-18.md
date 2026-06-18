# NATIVE_INIT V2654 — ACDB custom-topology SET capture build

Date: 2026-06-18

## Scope

Host-only build-only unit. No Android handoff, device flash, native replay, real
`AUDIO_SET_CALIBRATION`, mixer write, PCM write, or speaker playback occurred.
Raw ACDB bytes remain private-only.

## Decision

- `decision`: `v2654-acdb-custom-topology-setcal-capture-build-only`
- `ok`: `True`
- `build_root`: `workspace/private/builds/audio/v2654-acdb-custom-topology-setcal-capture-build-only`
- helper: `workspace/private/builds/audio/v2654-acdb-custom-topology-setcal-capture-build-only/bin/a90_acdb_custom_topology_setcal_capture_exec_linked_v2654`
- helper_sha256: `d93bbeb645dbb48f34f50451338058ce5c8b5648ee707aea889fcd03cd795406`
- preload: `workspace/private/builds/audio/v2654-acdb-custom-topology-setcal-capture-build-only/bin/liba90_acdb_custom_topology_setcal_capture_combined_preload_v2654.so`
- preload_sha256: `b74a36f94f9433383e31d9505d03257c77060d7fb43627daba7f775d261b9853`

## Capture Contract

- helper call order: `init_v3 -> arm -> send_common_custom_topology -> send_audio_cal_v5`
- preload is the V2630 fake-SET shim: dump SET arg bytes, mmap same-process dma-buf
  if present, then fake-success the SET so no kernel SET is delivered during capture
- target acceptance for the future live run: byte-exact SET records for cal_types
  `10`, `14`, and `24`
- cal_type `20` is retained as supplemental evidence, but cal20 alone is not success

## Source Checks

- required_ok: `True`
- prohibited_ok: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True, 'undefined_send_audio_cal_v5': True, 'undefined_or_weak_a90_arm_capture': True, 'undefined_common_topology': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'mode_0600': True, 'does_not_export_pthread_mutex_lock': True, 'does_not_export_pthread_mutex_unlock': True, 'does_not_export_android_log_print': True, 'soname_v2654': True}`

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
