# NATIVE_INIT V2601 — ACDB tap post-init arm default guard

Date: 2026-06-16

## Scope

Host-only source hardening after the operator handover requiring `acdb_ioctl` dump work to stay disabled until an explicit post-init/manual arm point. No Android handoff, device flash, ACDB execution, native replay `SET`, speaker write, or raw payload publication was performed.

## Decision

- decision: `v2601-acdbtap-auto-arm-default-off`
- ok: `True`
- touched sources:
  - `workspace/public/src/android/acdb_payload_capture/libacdbtap_v2475.c`
  - `workspace/public/src/android/acdb_payload_capture/libacdbtap_v2572.c`

## Change

- Changed the source default for `A90_ACDBTAP_AUTO_ARM_ON_INITIALIZE` from `1` to `0`.
- Builds that intentionally need post-`INITIALIZE_V2` auto-arm must now opt in with an explicit compile flag.
- Existing manual-arm builds such as V2562, V2576, V2577, and V2600 already pass `-DA90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=0`; the V2600 rebuilt private artifact kept the same SHA-256.

## Safety Rationale

- Unarmed `acdb_ioctl` calls now only call the real symbol and return: no dump, file I/O, hashing, raw writes, or target exit.
- This makes the safe behavior the default for any future tap build and prevents accidental regression to init-time dumping, which previously destabilized `INITIALIZE_V2`.
- The zero-buffer discriminator remains unchanged: a capture only counts when `ret==0` and the raw buffer is not all-zero.

## Private Artifact Check

- V2600 rebuild SHA-256: `a8afef2ebc8f64f6df041f5ed2b4b1808601ef5e3e24e222669c93f7b98fa746`
- The SHA matches the prior V2600 artifact because that build already compiled with explicit auto-arm disabled.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdbtap_v2475.py workspace/public/src/scripts/revalidation/build_android_acdb_indirect_buffer_tap_v2600.py tests/test_build_android_acdbtap_v2475.py tests/test_build_android_acdb_indirect_buffer_tap_v2600.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_build_android_acdbtap_v2475 tests.test_build_android_acdb_indirect_buffer_tap_v2600 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/build_android_acdb_indirect_buffer_tap_v2600.py --build --write-report`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest discover -s tests -v` — 1521 tests OK
- `git diff --check`

## Next Unit

Use the V2600 tap in a separate Android-good live handoff for per-device calibration capture, preserving all raw buffers privately and classifying records by `{cmd, buffer, in_len, out_len, ret, sha256, all_zero}` before any replay-manifest use.
