# NATIVE_INIT V2595 — ACDB direct pre-GET probe build

Date: 2026-06-16

## Scope

Host-only build unit after V2594. No Android handoff, native replay `SET`, speaker write,
ACDB command execution, or raw payload publication was performed.

## Decision

- decision: `v2595-acdb-direct-0x1122e-probe-build-ready`
- ok: `True`
- V2594 pinned the first `send_audio_cal_v5` dispatcher row as `acdb_ioctl(0x1122e, &0x11135, 4, out, 4)`.
- V2595 builds a narrower probe that bypasses the hanging `send_audio_cal_v5` local setup and calls that metadata row directly.

## Built Artifacts

- helper: `workspace/private/builds/audio/v2595-acdb-direct-preget-probe-build-only/bin/a90_acdb_direct_preget_exec_linked_v2595`
  - sha256: `5cc7b9c6f2bacdb7c4789bb9f9f62ec2f2ec7488e9124e97b0364b3644af023d`
  - ok: `True`
- preload: `workspace/private/builds/audio/v2595-acdb-direct-preget-probe-build-only/bin/liba90_acdb_direct_preget_probe_v2595.so`
  - sha256: `7019b5d44fa6d8bedd9065f42368354f67e5c57d97b863ec62a456cd307c255a`
  - ok: `True`

Private binaries remain under `workspace/private/builds/audio/` and are not committed.

## Probe Contract

- intercept `acdb_loader_send_common_custom_topology()` during `acdb_loader_init_v3()`;
- skip the real common-topology public call because topology cal_type 39 is already pinned;
- patch `acdb_loader_is_initialized`'s backing flag using the established V2572 offsets;
- call exactly `acdb_ioctl(0x1122e, &0x11135, 4, &out_word, 4)`;
- log `{ret,out_word,out_nonzero}` to `/data/local/tmp/a90-acdb-ownget/acdb-v2595-direct-preget-events.jsonl`; and
- `exit_group(0)` before libacdbloader's known init-tail crash.

The preget interposer does not import or call `acdb_loader_send_audio_cal_v5`, does not open
`/dev/msm_audio_cal`, and relies on the existing fake-allocate ioctl preload only to keep the
ACDB init transport measurement-only.

## Next Unit

Run V2596 as the recoverable Android-good live handoff for these V2595 artifacts:

1. stage the helper/preload/dependency closure under `/data/local/tmp/a90-acdb-ownget`;
2. set `LD_PRELOAD` to the V2595 preload and `A90_ACDB_FAKE_ALLOCATE=1`;
3. execute the helper once;
4. pull `acdb-v2595-direct-preget-events.jsonl` and `ioctl-trace-events.jsonl` privately;
5. classify whether `ret==0` and whether `out_word` is non-zero; and
6. rollback to V2321 and verify `selftest fail=0`.

If the direct `0x1122e` metadata probe succeeds, derive subsequent per-device pure-read request
structs from the returned word. If it fails or hangs, fall back to a more granular import-call tracer
around the two local pre-`0x1122e` helpers identified in V2594.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdb_direct_preget_probe_v2595.py tests/test_build_android_acdb_direct_preget_probe_v2595.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdb_direct_preget_probe_v2595`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -p 'test_build_android_acdb_direct_preget_probe_v2595.py'`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_direct_preget_probe_v2595.py --build --write-report`
- `file`/`readelf` artifact checks embedded in the manifest
- `git diff --check`
