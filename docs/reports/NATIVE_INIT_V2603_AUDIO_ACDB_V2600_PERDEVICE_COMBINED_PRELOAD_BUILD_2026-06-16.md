# NATIVE_INIT V2603 — ACDB V2600 per-device combined preload build

Date: 2026-06-16

## Scope

Host-only build-only unit after V2602. No Android handoff, device flash, native replay SET,
speaker write, or raw ACDB payload publication was performed.

## Decision

- decision: `v2603-acdb-v2600-perdevice-combined-preload-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2603-acdb-v2600-perdevice-combined-preload-build-only`
- helper: `workspace/private/builds/audio/v2603-acdb-v2600-perdevice-combined-preload-build-only/bin/a90_acdb_perdevice_rx_capmask_argorder_exec_linked_v2603`
- helper_sha256: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
- preload: `workspace/private/builds/audio/v2603-acdb-v2600-perdevice-combined-preload-build-only/bin/liba90_acdb_v2600_perdevice_combined_preload_v2603.so`
- preload_sha256: `eb979d3a732aaa27003d0547efdc8226bc052c2ea389accceec32474ed0e42bd`

## Why This Unit

V2602 used the V2600 tap-only shared object as the live override preload. That omitted
the preinit hook that arms capture and drives `send_audio_cal_v5`, so the run emitted
zero `acdbtap` events before the known own-process helper SIGSEGV. This build creates
the missing single preload with all three required pieces linked together.

## Contract

- tap: V2600 full `in_buf` dump plus bounded indirect `{length,pointer}` candidate capture.
- ioctl shim: V2531 fake allocate/deallocate/SET when `A90_ACDB_FAKE_ALLOCATE=1`; no real SET passthrough.
- preinit hook: V2572 per-device hook with V2591 `A90_SPEAKER_RX_PATH=1` and fixed stack-order compile flags.
- future per-device call: `acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)`.
- success remains `ret==0` plus non-all-zero direct/indirect payload, never requested length alone.
- native calibration replay SET and speaker playback remain blocked.

## Build Evidence

- tap_compile_ok: `True`
- tap_compile_has_inbuf_flag: `True`
- tap_compile_has_indirect_flag: `True`
- preinit_compile_ok: `True`
- preinit_compile_has_rx_flag: `True`
- preinit_compile_has_fixed_order_flag: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'soname_v2603': True, 'mode_0600': True}`

## Next Unit

Run the V2592 Android-good handoff with the V2591 helper and this V2603 combined preload
as the preload override. Do not use the V2600 tap-only shared object as the live preload again.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_v2600_perdevice_combined_preload_v2603.py tests/test_build_android_acdb_v2600_perdevice_combined_preload_v2603.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_v2600_perdevice_combined_preload_v2603 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_v2600_perdevice_combined_preload_v2603.py --build --write-report`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v` — 1525 tests OK
- `git diff --check`
