# NATIVE_INIT V2491 — audio ACDB own-process dlerror instrumentation

Date: 2026-06-16

## Decision

`v2491-acdb-ownprocess-dlerror-instrumentation-host-only`

V2490 proved the new own-process ACDB GET route can be staged, executed under
Android, and rolled back to V2321 cleanly, but the only captured event was:

```json
{"event":"error","stage":"dlopen-libaudcal","code":-1}
```

That was enough to classify the first live blocker as dynamic-linker loadability,
but not enough to identify whether the failure is a missing search path, vendor
namespace denial, bitness mismatch, dependency failure, or another linker error.
V2491 therefore adds `dlerror()` capture to the own-process helper before the next
live loadability unit.

## Scope

Host-only instrumentation update. No device live run in this iteration.

Public source changed:

- `workspace/public/src/android/acdb_payload_capture/a90_acdb_ownprocess_get_v2489.c`
- `workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py`
- `tests/test_build_android_acdb_ownprocess_get_v2489.py`

Private generated artifact rebuilt for future live use:

- `workspace/private/builds/audio/v2489-acdb-ownprocess-get-host-only/bin/a90_acdb_ownprocess_get_v2489`
- SHA256: `57797e74856724aa7cd8bf6add679e6e3069c8a7cd4a8d38f5f2f63e586a313e`

The historical V2489 host-only artifact SHA is superseded for future live runs by
this dlerror-instrumented rebuild. No private binary is committed.

## Implementation

The helper now:

- declares `dlerror()` explicitly, matching the no-libc-header style of the helper;
- clears stale linker errors before each `dlopen()` / `dlsym()` operation;
- writes an optional JSON `detail` field on loader/symbol failures;
- JSON-escapes detail text and bounds it to 512 bytes;
- keeps the ACDB path pure-read: no `/dev/msm_audio_cal` open and no SET ioctl.

Instrumented failure stages:

- `dlopen-libaudcal`
- `dlopen-libacdbloader`
- `dlsym-acdb_loader_init_v3`
- `dlsym-acdb_ioctl`

`acdb_loader_init_v3` nonzero return still records the numeric return code only.

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
- source-state marker `uses_dlerror_detail=True`

## Boundary

This does not resume the in-HAL injection path. It preserves the operator pivot:
own-process ARM32 helper only, pure-read ACDB GET calls only, private raw output
only, and no native calibration SET ioctl.

Next meaningful unit: run the existing V2490 live handoff with the V2491 helper to
capture the actual `dlerror()` detail, then choose the smallest loadability fix
(run location, linker namespace handling, or dependency staging) based on that
string.
