# NATIVE_INIT V2500 — audio ACDB linker symbol fallback host-only

Date: 2026-06-16

## Decision

`v2500-acdb-linker-symbol-fallback-host-only`

V2499 proved the direct `dlsym(libdl, "android_get_exported_namespace")` path is
not available in this Android helper context. V2500 does not retry live. It adds
a host-only fallback resolver that probes both public and loader-private linker
symbols through `libdl` and the process default symbol scope, while preserving the
same pure-read ACDB GET boundary.

## Current Evidence

V2499 live result:

```text
classification: namespace-api-symbol-missing
stage: dlsym-android_get_exported_namespace
error detail: undefined symbol: android_get_exported_namespace
rollback: V2321, selftest fail=0
```

Private artifact inspection:

```text
real /system/lib/libdl.so: not present in current private dumps
real /system/bin/linker: not present in current private dumps
vendor ACDB libs: present only under workspace/private/runs/audio/v2324-aud0-inventory/vendor_dump
```

So V2500 relies on V2499 live evidence plus AOSP primary-source behavior, not a
local device-matched `libdl.so` symbol table.

## AOSP Source Basis

Primary-source checks:

- bionic `libdl_android.cpp` shows `android_get_exported_namespace()` is a weak
  libdl wrapper over `__loader_android_get_exported_namespace()`.
  - Source: https://android.googlesource.com/platform/bionic/+/refs/heads/main/libdl/libdl_android.cpp
- the original bionic change adding exported namespaces states that the API is
  platform-only, returns only namespaces with `visible = true`, and adds
  `__loader_android_get_exported_namespace` in the linker synthetic symbol table.
  - Source: https://android.googlesource.com/platform/bionic/+/d7c4832%5E%21/
- bionic `linker/dlfcn.cpp` exposes `__loader_android_dlopen_ext()` with the
  loader-private four-argument signature including `caller_addr`, and exposes
  `__loader_android_get_exported_namespace()`.
  - Source: https://android.googlesource.com/platform/bionic/+/refs/heads/main/linker/dlfcn.cpp
- Android's `android/dlext.h` defines `ANDROID_DLEXT_USE_NAMESPACE = 0x200` and
  `android_dlextinfo.library_namespace`.
  - Source: https://android.googlesource.com/platform/bionic/+/main/libc/include/android/dlext.h
- Android linker namespace documentation states that a visible namespace such as
  `sphal` can be returned by `android_get_exported_namespace()` and that Android
  11+ generates linker config under `/linkerconfig` at runtime.
  - Source: https://source.android.com/docs/core/architecture/vndk/linker-namespace

This makes a bounded next attempt coherent: do not assume only the public libdl
wrapper is present; also probe the loader-private symbols.

## Implementation

Updated the existing ARM32 own-process helper to emit `symbol_probe` events and
try these candidates in order:

```text
libdl:android_get_exported_namespace
default:android_get_exported_namespace
default:__loader_android_get_exported_namespace
libdl:__loader_android_get_exported_namespace
libdl:android_dlopen_ext
default:android_dlopen_ext
default:__loader_android_dlopen_ext
libdl:__loader_android_dlopen_ext
```

If the resolved `android_dlopen_ext` entry is the loader-private symbol, the
helper calls it with the four-argument signature:

```text
__loader_android_dlopen_ext(filename, flags, extinfo, caller_addr)
```

The helper still records namespace probes and namespace load attempts only after
both required linker entrypoints are resolved.

## Boundary Check

Unchanged boundaries:

- no `/dev/msm_audio_cal`
- no `0xC00461CB`
- no `AUDIO_SET_CALIBRATION` / `AUDIO_ALLOCATE_CALIBRATION`
- no `acdb_loader_send_common_custom_topology`
- no HAL injection, no Magisk module install, no playback, no native speaker write
- raw ACDB bytes and vendor `.so` remain private-only

The public helper still imports only `dlopen`, `dlsym`, and `dlerror`; the
Android namespace symbols are runtime-probed strings, not ELF undefined imports.

## Private Build Artifact

Private build output, not committed:

```text
path: workspace/private/builds/audio/v2489-acdb-ownprocess-get-host-only/bin/a90_acdb_ownprocess_get_v2489
sha256: 176253735d7fc42e49909c75b0aeb7a2864db73f43c00ca3c81b63626b9ed413
file: ELF 32-bit LSB shared object, ARM, EABI5, dynamically linked, interpreter /system/bin/linker
readelf NEEDED: libdl.so
readelf undefined imports: dlopen, dlsym, dlerror only
```

## Validation

Commands run:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py \
  tests/test_build_android_acdb_ownprocess_get_v2489.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest \
  tests.test_build_android_acdb_ownprocess_get_v2489 -v

python3 workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_v2489.py --build

readelf -Ws workspace/private/builds/audio/v2489-acdb-ownprocess-get-host-only/bin/a90_acdb_ownprocess_get_v2489
readelf -d workspace/private/builds/audio/v2489-acdb-ownprocess-get-host-only/bin/a90_acdb_ownprocess_get_v2489
```

Result:

```text
source required_ok: true
source prohibited_ok: true
unit tests: 5 passed
build: ok
```

## Next Unit

Run one bounded Android handoff using the V2500 helper. Expected additional
signal compared with V2499:

- a `symbol_probe` record for every attempted public/private symbol;
- if `__loader_android_get_exported_namespace` is visible, namespace probing can
  finally start;
- if both public and private symbols are absent, the blocker becomes
  device/linker-build-specific rather than a helper implementation gap.

Do not retry V2499's old helper SHA. The next live runner must use helper SHA
`176253735d7fc42e49909c75b0aeb7a2864db73f43c00ca3c81b63626b9ed413`.
