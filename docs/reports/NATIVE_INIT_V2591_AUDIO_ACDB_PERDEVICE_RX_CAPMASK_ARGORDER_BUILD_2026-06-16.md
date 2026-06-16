# NATIVE_INIT V2591 — ACDB per-device RX cap-mask corrected-arg-order build

Date: 2026-06-16

## Scope

Host-only build-only unit after V2590. No Android handoff, device flash, native replay SET,
speaker write, or raw ACDB payload publication was performed.

## Decision

- decision: `v2591-acdb-perdevice-rx-capmask-argorder-build-only`
- ok: `True`
- build_root: `workspace/private/builds/audio/v2591-acdb-perdevice-rx-capmask-argorder-build-only`
- helper: `workspace/private/builds/audio/v2591-acdb-perdevice-rx-capmask-argorder-build-only/bin/a90_acdb_perdevice_rx_capmask_argorder_exec_linked_v2591`
- helper_sha256: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
- preload: `workspace/private/builds/audio/v2591-acdb-perdevice-rx-capmask-argorder-build-only/bin/liba90_acdb_perdevice_rx_capmask_argorder_capture_v2591.so`
- preload_sha256: `e8e5273a76ebd409ecb84aa660372aded1b3559ee7ee3eaaba72fcad72693d93`

## Why This Unit

V2588 proved the RX cap-mask route reaches `send_audio_cal_v5`, then hangs before the first
real armed ACDB row. V2590 wrapper/prologue RE shows the prior build passed the trailing
stack args in the wrong semantic order. This unit creates the same V2572 generic direct/
indirect capture shape, compiles the second argument as RX cap mask `1`, and compiles the
v5 stack args as `(session/default=0, afe_sample_rate=48000, instance=1)`.

## Contract

- future per-device call: `acdb_loader_send_audio_cal_v5(15, 1, 0x11135, 48000, 0, 48000, 1)`
- real common-topology public call stays skipped; V2547 already pinned topology.
- capture arms only after the initialized-flag patch inside the pre-init hook.
- `A90_ACDB_FAKE_ALLOCATE=1` remains required for any future live run.
- success remains `ret==0` plus non-all-zero direct/indirect payload, never requested length alone.
- native calibration replay SET and speaker playback remain blocked.

## Build Evidence

- preinit_compile_ok: `True`
- preinit_compile_command_contains_capmask: `True`
- preinit_compile_command_contains_fixed_order: `True`
- helper_checks: `{'is_pie': True, 'entry_start': True, 'undefined_init_v3': True, 'needed_libacdbloader': True, 'needed_libaudcal': True, 'mode_0600': True}`
- preload_checks: `{'exports_acdb_ioctl': True, 'exports_ioctl': True, 'exports_common_topology': True, 'exports_a90_arm_capture': True, 'undefined_dlsym': True, 'undefined_errno': True, 'soname_v2591': True, 'mode_0600': True}`

## Next Unit

Add a V2592 live runner wrapper that selects these V2591 private artifacts and reuses the V2587
classification logic. The live unit should be a single rollbackable Android handoff and must
stop after preserving ordered ACDB tap records for operator Gate-2 mapping.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_perdevice_rx_capmask_argorder_v2591.py tests/test_build_android_acdb_perdevice_rx_capmask_argorder_v2591.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_perdevice_rx_capmask_argorder_v2591`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_perdevice_rx_capmask_argorder_v2591.py --build --write-report`
- `git diff --check`
