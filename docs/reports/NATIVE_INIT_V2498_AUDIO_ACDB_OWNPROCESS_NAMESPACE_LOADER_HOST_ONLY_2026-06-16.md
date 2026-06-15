# NATIVE_INIT V2498 — audio ACDB own-process namespace loader host-only implementation

Date: 2026-06-16

## Decision

`v2498-acdb-ownprocess-namespace-loader-host-only`

Implemented the V2497 namespace-aware loader design in the existing ARM32
own-process ACDB GET helper. This unit is host-only: no device action, no
Android handoff, no playback, and no `/dev/msm_audio_cal` ioctl.

## What changed

- The helper now resolves Android linker namespace APIs from `libdl.so` at
  runtime with `dlsym()`:
  - `android_get_exported_namespace`
  - `android_dlopen_ext`
- The helper probes exported namespaces in this order:
  - `sphal`
  - `vendor`
  - `default`
  - `vndk`
- The helper loads `/vendor/lib/libaudcal.so` and
  `/vendor/lib/libacdbloader.so` using `android_dlopen_ext()` with
  `ANDROID_DLEXT_USE_NAMESPACE = 0x200` and the selected namespace.
- The helper records namespace observability into the private JSONL event stream:
  - `namespace_probe`
  - `namespace_load`
  - `namespace_selected`
- The ACDB behavior is unchanged after library load:
  - resolve `acdb_loader_init_v3`
  - resolve `acdb_ioctl`
  - call `acdb_loader_init_v3("/vendor/etc/acdbdata", "/data/local/tmp/a90-acdb-ownget/delta", 0)`
  - run the bounded pure-read GET matrix over commands `0x11394`, `0x12e01`,
    `0x130da`, `0x130dc`, input lengths `0/4/8/16/32`, and output lengths
    `4/4916`

The implementation uses runtime `dlsym()` for the namespace APIs rather than
hard undefined imports. This preserves the future live-run classification bucket
`namespace-api-symbol-missing`: if either API is unavailable, the helper can emit
a JSONL `error` event before exiting instead of failing before `_start`.

## Boundary check

Still prohibited/absent from the public helper source:

- no `/dev/msm_audio_cal`
- no `0xC00461CB`
- no `AUDIO_SET_CALIBRATION` / `AUDIO_ALLOCATE_CALIBRATION`
- no `acdb_loader_send_common_custom_topology`
- no `tinymix`, `tinyplay`, `AudioTrack`, HAL injection, or Magisk module install
- no committed raw ACDB payload bytes or vendor `.so` files

## Private build artifact

The build output is private and must not be committed.

```text
path: workspace/private/builds/audio/v2489-acdb-ownprocess-get-host-only/bin/a90_acdb_ownprocess_get_v2489
sha256: 277915a34f4f0619f9c11abc681755ef2c609ed878dea665e47d6b920c66ac12
file: ELF 32-bit LSB shared object, ARM, EABI5, dynamically linked, interpreter /system/bin/linker
```

## Validation

Commands run:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  tests/test_build_android_acdb_ownprocess_get_v2489.py \
  tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest \
  tests.test_build_android_acdb_ownprocess_get_v2489 \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490 -v

python3 workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py --build
```

Result:

```text
source required_ok: true
source prohibited_ok: true
unit tests: 13 passed
build: ok
readelf undefined imports: dlopen, dlsym, dlerror only
readelf NEEDED: libdl.so
no direct android_get_exported_namespace/android_dlopen_ext imports
```

## Next live classification buckets

A future V2499 live run should classify into exactly one of these buckets:

- `namespace-api-symbol-missing`
- `namespace-none-visible`
- `namespace-visible-load-failed`
- `libaudcal-loaded-libacdbloader-block`
- `init-v3-block`
- `acdb-get-success-4916`
- `acdb-get-full-outbuf-set-no-4916`

The last bucket is a partial success, not a dead retry, because the ordered
out-buffer set is still operator-valuable.

## Source basis

This implementation follows the already committed V2497 design, which cited the
Android linker namespace documentation, AOSP `libvndksupport` namespace loading
strategy, Android NDK `libdl` documentation, and bionic `dlext.h` for
`ANDROID_DLEXT_USE_NAMESPACE = 0x200`.
