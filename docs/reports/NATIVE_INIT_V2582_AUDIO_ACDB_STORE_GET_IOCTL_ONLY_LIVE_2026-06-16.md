# NATIVE_INIT V2582 — ACDB store-get probe ioctl-only live handoff

Date: 2026-06-16

## Scope

Run the V2580 gated store-get metadata probe through the V2490 checked Android
handoff/rollback engine after correcting the V2581 runner to use the V2531
ioctl-only fake-allocation preload instead of the V2538 combined `acdb_ioctl`
tap. No native replay SET, speaker write, or raw payload publication was
performed.

## Result

- decision: `v2581-store-get-no-case-return-rollback-pass`
- ok: `False`
- private out_dir: `workspace/private/runs/audio/v2581-acdb-store-get-probe-20260616-143644`
- engine decision: `v2490-ownprocess-helper-sigsegv-no-events-before-rollback-rollback-pass`
- rollback: `True`
- final native health: V2321 resident, `selftest fail=0`

## What Changed

- V2581 runner now stages `liba90_ioctl_trace_v2531.so` only.
- `LD_PRELOAD` no longer includes `liba90_acdb_combined_preload_v2538.so`.
- The exact-gated helper command creates `V2580_STORE_GET_GO`, removes it after
  helper exit, and keeps `A90_ACDB_FAKE_ALLOCATE=1`.
- Static dry-run reports `live_ready=True`, `command_safety.ok=True`, and the
  marker dry-run confirms `uses_ioctl_trace=True`, `uses_combined=False`.

## Live Evidence

- V2580 helper events stopped after:
  - `start`
  - `before_init_v3`
- `acdb_loader_init_v3()` did not return, so no `case_return` rows were emitted.
- The V2538 init-time hang is resolved: Android logcat progressed through
  `ACDB_CMD_INITIALIZE_V2`, ACDB version checks, ACPH/RTAC/MCS/FTS init, and
  `send_common_custom_topology`.
- V2531 fake allocation worked: ioctl trace captured fake-success
  `AUDIO_ALLOCATE_CALIBRATION` for cal types including `11`, `12`, `15`, `16`,
  and `39`.
- A fake-success `AUDIO_SET_CALIBRATION` for topology cal type `39`, size `4916`,
  was observed in-process; no real SET pass-through occurred.
- The helper then SIGSEGVed inside `libacdbloader.so` after
  `acdb_loader_send_common_custom_topology: Common custom topology in use`.

## Interpretation

The V2582 fix separated two blockers:

1. The previous V2581/V2538 `acdb_ioctl` interposer was the cause of the
   `INITIALIZE_V2` hang. Using ioctl-only fake allocation removes that blocker.
2. The V2580 store-get probe still cannot execute because
   `acdb_loader_init_v3()` itself runs common topology and crashes before
   returning to the helper.

This is not a store-get negative. The direct store-get request cases were never
reached. The next safe unit should skip or stub the init-time common-topology
send inside the own-process init path, then run the same gated store-get cases.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_store_get_probe_live_handoff_v2581.py tests/test_native_audio_acdb_store_get_probe_live_handoff_v2581.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_store_get_probe_live_handoff_v2581`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_store_get_probe_live_handoff_v2581.py --write-report`
- V2581 marker dry-run: `uses_ioctl_trace=True`, `uses_combined=False`, `command_safety_ok=True`
- V2582 live handoff + checked rollback to V2321, final `selftest fail=0`
- `git diff --check`
