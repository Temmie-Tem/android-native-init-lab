# NATIVE_INIT V2569 — ACDB pre-init-tail per-device live runner build

Date: 2026-06-16

## Scope

Host-only implementation of the live handoff wrapper for the V2568 ACDB pre-init-tail
capture artifacts. No Android boot, device flash, native replay, speaker write, or live ACDB
execution was performed in this iteration.

## Implementation

New public source:

```text
workspace/public/src/scripts/revalidation/native_audio_acdb_preinit_perdevice_capture_live_handoff_v2569.py
```

The runner:

- reuses the V2490 checked Android boot/stage/pull/rollback engine;
- builds/selects the V2568 private helper and combined preload;
- forces `A90_ACDB_FAKE_ALLOCATE=1`;
- stages one combined preload with `acdb_ioctl`, `ioctl`, `a90_arm_capture`, and
  `acdb_loader_send_common_custom_topology`;
- parses pulled private artifacts for:
  - V2568 helper stages,
  - V2568 pre-init hook stages,
  - complete ordered `acdbtap` rows,
  - real-vs-faked `AUDIO_SET_CALIBRATION` boundary;
- classifies full success only when both are present:
  - a valid non-zero 4916-byte topology record,
  - at least one valid non-zero non-topology per-device ACDB out-buffer after
    `send_audio_cal_v5` is reached.

Raw ACDB buffers remain private under the future run directory and are never committed.

## Dry-Run Result

Command:

```text
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_preinit_perdevice_capture_live_handoff_v2569.py \
  --dry-run \
  --build-v2568-artifacts \
  --v2568-build-root workspace/private/builds/audio/v2568-acdb-preinit-perdevice-capture-host-only \
  --v2568-manifest-path workspace/private/builds/audio/v2568-acdb-preinit-perdevice-capture-host-only/manifest.json
```

Result:

```text
ok=True
live_ready=True
live_blockers=[]
command_safety.ok=True
```

Selected private artifacts:

```text
a90_acdb_preinit_perdevice_exec_linked_v2568
  ee6f66ccbf35bbf5c01aa2f56d8fbc082a3bbd8778a57dca44f3ff8ba08a58a0

liba90_acdb_preinit_perdevice_capture_v2568.so
  469f92b966992e8d5bb39aa6a5ebe621b84df8ce956cd6d2031c47a242d6ecdd
```

## Validation

Commands run:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_preinit_perdevice_capture_live_handoff_v2569.py \
  workspace/public/src/scripts/revalidation/build_android_acdb_preinit_perdevice_capture_v2568.py

PYTHONPATH=tests \
python3 -m unittest tests.test_native_audio_acdb_preinit_perdevice_capture_live_handoff_v2569

PYTHONPATH=tests \
python3 -m unittest discover tests

git diff --check
```

Focused tests:

```text
Ran 6 tests in 0.003s
OK
```

Full suite:

```text
Ran 1439 tests in 44.052s
OK
```

The tests cover:

- V2490 argument wiring (`combined_preload`, fake allocate, no separate acdbtap preload);
- full-success classification with topology plus per-device non-topology records;
- zero-buffer rejection;
- real `AUDIO_SET_CALIBRATION` pass-through boundary violation;
- dry-run blocker when V2568 artifacts are absent;
- V2568 manifest artifact selection.

## Next Gate

The next meaningful unit is the V2569 live handoff:

```text
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_preinit_perdevice_capture_live_handoff_v2569.py \
  --run-live \
  --write-report \
  --build-v2568-artifacts
```

This is inside the GOAL.md recoverable envelope only if it uses the V2490 Android handoff and
checked rollback to V2321. It must preserve these boundaries:

- no native ACDB replay;
- no speaker write;
- no real `AUDIO_SET_CALIBRATION` pass-through;
- raw ACDB buffers private only;
- final rollback to V2321 with native `selftest fail=0`.
