# NATIVE_INIT V2592 — ACDB per-device RX cap-mask runner

Date: 2026-06-16

## Scope

Host-only runner unit after V2591. No live Android handoff, native replay SET, speaker write,
or raw ACDB payload publication was performed in this iteration.

## Decision

- decision: `v2592-acdb-perdevice-rx-capmask-argorder-live-runner-dry-run`
- ok: `True`
- live_ready: `True`
- live_blockers: `[]`

## Runner Contract

- exact live gate: `AUD-ACDB-V2592-perdevice-rx-capmask-argorder go: one-shot send_audio_cal_v5 arg2=1 corrected-stack-order per-device capture on Android, fake allocate preload, no SET replay, no speaker write, rollback to V2321`
- stages the V2591 helper/preload artifacts where `send_audio_cal_v5` arg2 is `1` and stack args are `(0, 48000, 1)`.
- reuses V2573 generic direct/indirect ACDB tap classification.
- forces `A90_ACDB_FAKE_ALLOCATE=1`; native replay SET and speaker playback remain blocked.
- success requires `ret==0` and non-all-zero raw payload; requested length alone is not success.

## Artifacts

- helper_sha256: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
- preload_sha256: `e8e5273a76ebd409ecb84aa660372aded1b3559ee7ee3eaaba72fcad72693d93`

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_perdevice_rx_capmask_argorder_live_handoff_v2592.py tests/test_native_audio_acdb_perdevice_rx_capmask_argorder_live_handoff_v2592.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_perdevice_rx_capmask_argorder_live_handoff_v2592`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_perdevice_rx_capmask_argorder_live_handoff_v2592.py --build-v2591-artifacts --write-report`
- `git diff --check`
