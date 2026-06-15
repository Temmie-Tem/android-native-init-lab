# NATIVE_INIT V2537 — ACDB own-process stacked preload negative result

Date: 2026-06-16
Scope: ACDB own-process capture, measurement-only.
Boundary: no native speaker write, no real `AUDIO_SET_CALIBRATION`, raw payloads private only, checked rollback to V2321.

## Question

Can the own-process ACDB helper run with two separate ARM32 `LD_PRELOAD` libraries so that:

1. `libacdbtap.so` interposes `acdb_ioctl` and dumps internal ACDB GET output buffers, while
2. `liba90_ioctl_trace_v2531.so` fakes `AUDIO_ALLOCATE_CALIBRATION` / `AUDIO_DEALLOCATE_CALIBRATION` / `AUDIO_SET_CALIBRATION` success and records ioctl metadata?

This was intended to catch the internal `send_common_custom_topology` GET path that V2535 reached before the helper crashed.

## Host changes

Updated `native_audio_acdb_ownprocess_get_live_handoff_v2490.py` to support a diagnostic stacked-preload mode:

- `--enable-acdbtap-preload` stages the V2475 `libacdbtap.so` and pulls `/data/local/tmp/a90-acdb-tap/` into the private run artifacts.
- Parser now validates acdbtap rows with the same V2530 discriminator: success requires `ret==0` and a non-all-zero raw output buffer. Requested `out_len==4916` alone is not success.
- Parser reports both own-helper rows and acdbtap rows separately.
- Tests cover stacked dry-run, acdbtap non-zero `4916` success, and failed/all-zero `4916` rejection.

## Validation

Host static validation:

```sh
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py
PYTHONPATH=tests python3 -m unittest \
  tests.test_build_android_acdbtap_v2475 \
  tests.test_build_android_ioctl_trace_preload_v2531 \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490
```

Result: `Ran 39 tests ... OK`.

Dry-run with fake allocation + acdbtap enabled:

- `live_ready=True`
- `command_safety.ok=True`
- `libacdbtap.so` is ordered before `liba90_ioctl_trace_v2531.so`
- no forbidden `0xc00461cb` command literal in the planned shell commands

## Live run V2536 — colon-separated preload

Private run directory:

`workspace/private/runs/audio/v2536-acdbtap-stacked-fake-allocate-20260616-064005`

Plan used `LD_PRELOAD=/data/local/tmp/a90-acdb-ownget/libacdbtap.so:/data/local/tmp/a90-acdb-ownget/liba90_ioctl_trace_v2531.so`.

Result:

- decision: `v2490-helper-timeout-ownprocess-context-only-no-events-before-rollback-rollback-pass`
- classification: `ownprocess-context-only-no-events`
- own ACDB GET rows: `0`
- acdbtap rows: `0`
- ioctl trace events: `0`
- ACDB log stopped after `ACDB -> ACDB_CMD_INITIALIZE_V2`
- rollback: V2321 booted
- post-rollback health: `version 0.9.285`, `selftest fail=0`

## Live run V2537 — space-separated preload

Private run directory:

`workspace/private/runs/audio/v2537-acdbtap-stacked-space-preload-20260616-064616`

Plan used `LD_PRELOAD='/data/local/tmp/a90-acdb-ownget/libacdbtap.so /data/local/tmp/a90-acdb-ownget/liba90_ioctl_trace_v2531.so'`.

Result:

- decision: `v2490-helper-timeout-ownprocess-context-only-no-events-before-rollback-rollback-pass`
- classification: `ownprocess-context-only-no-events`
- own ACDB GET rows: `0`
- acdbtap rows: `0`
- ioctl trace events: `0`
- ACDB log again stopped after `ACDB -> ACDB_CMD_INITIALIZE_V2`
- rollback: V2321 booted
- post-rollback health: `version 0.9.285`, `selftest fail=0`

## Interpretation

This is a negative result for the **two separate `LD_PRELOAD` libraries** approach, not a negative result for ACDB capture itself.

The key evidence is that both V2536 and V2537 produced zero `ioctl_trace` events. V2535 proved the V2531 ioctl preload works alone and reaches the fake allocate/fake SET path. Therefore, once `libacdbtap.so` is added as a second preload, the helper no longer reaches the V2531 interception path and hangs during ACDB initialization before `AUDIO_ALLOCATE_CALIBRATION` logging.

The two delimiter variants both failed, so this theme is saturated under the anti-churn rule. Do not retry separate stacked preloads.

## Next step

Build a single combined ARM32 preload that exports both interposed symbols in one `.so`:

- `acdb_ioctl`: call real `acdb_ioctl` via `RTLD_NEXT`, dump all `out_len>0` buffers, success only on `ret==0` + non-zero raw.
- `ioctl`: reuse V2531 fake-success policy for `AUDIO_ALLOCATE_CALIBRATION`, `AUDIO_DEALLOCATE_CALIBRATION`, and `AUDIO_SET_CALIBRATION`; pass through all other ioctls.

This avoids Android linker/multi-preload ambiguity and preserves the measurement-only boundary. Live execution should be a single bounded attempt after host build/test.
