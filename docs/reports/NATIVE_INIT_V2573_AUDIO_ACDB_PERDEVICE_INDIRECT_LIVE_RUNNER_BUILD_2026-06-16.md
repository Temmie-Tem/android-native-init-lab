# NATIVE_INIT V2573 — ACDB per-device indirect live runner build

Date: 2026-06-16

## Scope

Host-only runner unit after V2572. No live Android handoff was executed, no native replay ran, no
speaker/mixer/PCM write was issued, and no raw ACDB payload bytes are committed.

## Purpose

V2572 built the ARM32 helper/preload pair for a generic direct/indirect ACDB capture route. V2573
adds the checked live-handoff wrapper that can stage those V2572 private artifacts through the
existing V2490 Android boot/stage/pull/rollback engine in a future live iteration.

## Runner Behavior

- Selects V2572 artifacts from `workspace/private/builds/audio/v2572-acdb-perdevice-indirect-capture-host-only/manifest.json` or builds them privately with `--build-v2572-artifacts`.
- Forces the V2490 engine into combined-preload mode with `A90_ACDB_FAKE_ALLOCATE=1`.
- Classifies pulled `acdbtap` records by raw-file validity, SHA-256 match, non-zero content, and
  command/length family.
- Treats topology as already pinned; live success requires at least one non-zero direct or indirect
  per-device record with `ret==0` and `out_len` not in `{4, 4916}` after the V2572 preinit hook
  reaches `before_send_audio_cal_v5`.
- Treats any real `AUDIO_SET_CALIBRATION` pass-through as a boundary violation.

## Dry-run Result

- decision: `v2573-acdb-perdevice-indirect-capture-live-runner-dry-run`
- ok: `True`
- live_ready: `True`
- live_blockers: `[]`
- command_safety_ok: `True`
- manual_arm_after_preinit_patch: `True`
- skips_real_common_topology: `True`
- generic_indirect_capture: `True`
- pointer_filter: `True`

## Selected Private Artifacts

- Helper: `workspace/private/builds/audio/v2572-acdb-perdevice-indirect-capture-host-only/bin/a90_acdb_perdevice_indirect_exec_linked_v2572`
  - SHA-256: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
- Preload: `workspace/private/builds/audio/v2572-acdb-perdevice-indirect-capture-host-only/bin/liba90_acdb_perdevice_indirect_capture_v2572.so`
  - SHA-256: `08046bcb104a9da948a8d05bba7d0126d07f35de30a9978231d445153189a7d4`

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573.py workspace/public/src/scripts/revalidation/build_android_acdb_perdevice_indirect_capture_v2572.py`
- `PYTHONPATH=tests python3 -m unittest tests.test_native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_perdevice_indirect_capture_live_handoff_v2573.py --dry-run --build-v2572-artifacts`
- `git diff --check` passed before commit.

## Next Step

A future live unit can run V2573 with `--run-live --write-report` under the checked Android
handoff/rollback envelope. That live unit remains separate from this build-only runner unit and must
preserve V2321 rollback, raw-payload privacy, and the no-real-SET boundary.
