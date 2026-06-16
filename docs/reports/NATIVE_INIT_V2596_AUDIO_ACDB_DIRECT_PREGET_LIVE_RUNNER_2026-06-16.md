# NATIVE_INIT V2596 — ACDB direct pre-GET live runner

Date: 2026-06-16

## Scope

Android own-process ACDB direct metadata probe wrapper. Dry-run mode only verifies the checked
V2490 Android handoff plan and selected V2595 private artifacts; live mode is recoverable to V2321.

## Result

- decision: `v2596-acdb-direct-preget-live-runner-dry-run`
- ok: `True`
- out_dir: `None`
- classification: `None`
- ret: `None`
- out_word: `None`
- out_nonzero: `None`

## Artifact Selection

- helper: `workspace/private/builds/audio/v2595-acdb-direct-preget-probe-build-only/bin/a90_acdb_direct_preget_exec_linked_v2595`
- helper_sha256: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
- preload: `workspace/private/builds/audio/v2595-acdb-direct-preget-probe-build-only/bin/liba90_acdb_direct_preget_probe_v2595.so`
- preload_sha256: `7019b5d44fa6d8bedd9065f42368354f67e5c57d97b863ec62a456cd307c255a`

## Contract

- stages the V2595 helper/preload via the V2490 Android-good handoff engine;
- sets `A90_ACDB_FAKE_ALLOCATE=1`; the ioctl preload fake-successes audio-cal ALLOC/DEALLOC/SET only;
- executes the helper once and pulls `/data/local/tmp/a90-acdb-ownget/` privately;
- classifies `acdb-v2595-direct-preget-events.jsonl`; and
- success requires `ret==0` and `out_word != 0`, not the requested 4-byte geometry alone.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_direct_preget_live_handoff_v2596.py tests/test_native_audio_acdb_direct_preget_live_handoff_v2596.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_direct_preget_live_handoff_v2596`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -p 'test_native_audio_acdb_direct_preget_live_handoff_v2596.py'`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_direct_preget_live_handoff_v2596.py --dry-run --write-report`
- `git diff --check`
