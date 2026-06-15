# NATIVE_INIT V2495 — audio ACDB own-process absolute vendor dlopen

Date: 2026-06-16

## Decision

`v2495-ownprocess-absolute-vendor-dlopen-host-fix`

V2494 proved the vendor ACDB libraries exist on disk but soname lookup from the
`/data/local/tmp` + `su` own-process helper context cannot find `libaudcal.so`,
even with `LD_LIBRARY_PATH` set by the runner:

```json
{"stage":"dlopen-libaudcal","detail":"dlopen failed: library \"libaudcal.so\" not found"}
```

V2495 changes the helper to bypass soname search and call bionic `dlopen()` with
absolute vendor paths:

```c
dlopen("/vendor/lib/libaudcal.so", A90_RTLD_NOW);
dlopen("/vendor/lib/libacdbloader.so", A90_RTLD_NOW);
```

This is the smallest next loadability discriminator. It does not change the ACDB
GET matrix, output capture, or calibration boundary.

## Scope

Host-only source/build/test update. No device live run in this iteration.

Changed public files:

- `workspace/public/src/android/acdb_payload_capture/a90_acdb_ownprocess_get_v2489.c`
- `workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py`
- `tests/test_build_android_acdb_ownprocess_get_v2489.py`

Private regenerated helper artifact:

- `workspace/private/builds/audio/v2489-acdb-ownprocess-get-host-only/bin/a90_acdb_ownprocess_get_v2489`
- SHA256: `4d793aa6a91d3f5212896903b6cbf08f8a423e6f9ec85174a0b01bf4c403198c`

No private binary is committed.

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
- source-state marker `uses_absolute_vendor_paths=True`
- source-state marker `uses_rtld_now_only=True`
- source-state marker `uses_dlerror_detail=True`
- `required_ok=True`, `prohibited_ok=True`

## Boundary

The helper remains own-process and pure-read. It does not use in-HAL injection,
Magisk modules, HAL restart, AudioTrack playback, native speaker writes, or
`/dev/msm_audio_cal` calibration SET ioctls.

## Next

Run the existing checked Android handoff with the V2495 helper. If absolute-path
`libaudcal.so` succeeds, the next result will classify either `libacdbloader.so`,
`dlsym`, `acdb_loader_init_v3`, or actual ACDB GET behavior. If absolute-path
`libaudcal.so` still fails, the own-process route has a real linker namespace or
policy wall that requires a different run location/namespace strategy.
