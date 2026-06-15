# NATIVE_INIT V2493 — audio ACDB own-process RTLD_NOW-only fix

Date: 2026-06-16

## Decision

`v2493-ownprocess-rtld-now-only-host-fix`

V2492 used the V2491 `dlerror()` instrumentation and localized the first live
own-process blocker to bionic rejecting the helper's `dlopen()` flag word:

```json
{"stage":"dlopen-libaudcal","detail":"dlopen failed: invalid flags to dlopen: 102"}
```

The helper was using `RTLD_NOW | RTLD_GLOBAL`; bionic reported that as invalid
before loading `libaudcal.so`. V2493 removes `RTLD_GLOBAL` and keeps the minimal
`RTLD_NOW` mode for both vendor library loads.

## Scope

Host-only code/build/test update. No live device run in this iteration.

Changed public files:

- `workspace/public/src/android/acdb_payload_capture/a90_acdb_ownprocess_get_v2489.c`
- `workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py`
- `tests/test_build_android_acdb_ownprocess_get_v2489.py`

Private regenerated helper artifact:

- `workspace/private/builds/audio/v2489-acdb-ownprocess-get-host-only/bin/a90_acdb_ownprocess_get_v2489`
- SHA256: `de19a7ed44a51946d64479c7422fab50a3b4c018f7cb873c1d31e20f7ed81ba0`

No private binary is committed.

## Implementation

The helper now calls:

```c
dlopen("libaudcal.so", A90_RTLD_NOW);
dlopen("libacdbloader.so", A90_RTLD_NOW);
```

The verifier now requires:

- no `A90_RTLD_GLOBAL` token in the source;
- `libaudcal.so` and `libacdbloader.so` loaded with `A90_RTLD_NOW` only;
- `dlerror()` detail support retained.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest \
  tests.test_build_android_acdb_ownprocess_get_v2489 \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490 -v

python3 workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py --build
```

Results:

- Python compile: pass
- Unit tests: `13` run, `OK`
- Build: pass
- `file`: ELF 32-bit LSB shared object, ARM, interpreter `/system/bin/linker`
- dynamic dependency: `libdl.so`
- undefined imports include `dlopen`, `dlsym`, and `dlerror`
- source-state marker `uses_rtld_now_only=True`
- source-state marker `uses_dlerror_detail=True`

## Boundary

The path remains own-process and pure-read. No HAL injection, no Magisk module,
no playback, no native speaker writes, and no `/dev/msm_audio_cal` calibration
SET ioctl.

## Next

Rerun the V2490 live handoff with this V2493 helper. Expected outcomes:

- if `libaudcal.so` now loads, classify the next actual namespace/dependency or
  `libacdbloader.so` blocker using `dlerror()`;
- if all loads pass, collect the ordered ACDB GET result set and preserve any
  no-4916 out-buffer set as operator-valuable partial evidence;
- always rollback to V2321 and confirm native selftest `fail=0`.
