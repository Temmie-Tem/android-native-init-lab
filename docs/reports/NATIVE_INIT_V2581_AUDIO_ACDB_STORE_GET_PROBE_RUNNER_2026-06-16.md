# NATIVE_INIT V2581 — ACDB store-get probe runner

Date: 2026-06-16

## Scope

Host-only runner unit after V2580. No live Android handoff, ACDB command execution, native calibration SET, or speaker write was performed in this iteration.

## Decision

- decision: `v2581-acdb-store-get-probe-live-runner-dry-run`
- ok: `True`
- live_ready: `True`
- live_blockers: `[]`

## Runner Contract

- exact live gate: `AUD-ACDB-V2581-store-get-probe go: one-shot gated store_get metadata capture on Android, fake allocate preload, no SET replay, no speaker write, rollback to V2321`
- marker path: `/data/local/tmp/a90-acdb-ownget/V2580_STORE_GET_GO`
- Without the marker, the V2580 helper exits before `acdb_loader_init_v3()` or `acdb_loader_store_get_audio_cal()`.
- Live execution must use the V2531 ioctl-only preload with `A90_ACDB_FAKE_ALLOCATE=1`; no `acdb_ioctl` tap is loaded for this probe.
- Success requires `ret==0` plus `all_zero=false` in V2580 `case_return` metadata; requested length alone is not success.
- Native replay SET, speaker playback, and raw payload publication remain blocked.

## Artifacts

- helper_sha256: `365137f08502ba03b02c03bd0f4f56f299589f6c81e703a74a71d17308ed0c39`
- ioctl_trace_preload_sha256: `3fddb586520fe277af9d1f2102cb3ad35d089dbc81bf1fab28b33ce1a635dd23`

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_store_get_probe_live_handoff_v2581.py tests/test_native_audio_acdb_store_get_probe_live_handoff_v2581.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_store_get_probe_live_handoff_v2581`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_store_get_probe_live_handoff_v2581.py --write-report`
- `git diff --check`
