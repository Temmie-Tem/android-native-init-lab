# NATIVE_INIT V2508 — audio ACDB own-process exec-linked helper host-only

## Decision

`v2508-acdb-ownprocess-exec-linked-host-only`

V2508 adds a host-built ARM32 own-process ACDB GET helper variant that avoids the
V2507 bionic TLS blocker by making the stock ACDB libraries part of the process
initial load set.  It does this with DT_NEEDED dependencies instead of late
`dlopen()` / linker-namespace probing.

No device step ran in this unit.  No flash, HAL injection, Magisk module,
AudioTrack playback, native speaker write, `/dev/msm_audio_cal`, or calibration
SET ioctl was used.

## Why this unit exists

V2507 solved the local dependency closure through `libdiag.so`, but the helper
then failed while late-loading staged `libaudcal.so`:

```text
TLS symbol "(null)" in dlopened "/apex/com.android.runtime/lib/bionic/libc.so"
referenced from "/apex/com.android.runtime/lib/bionic/libc.so" using IE access model
```

That means the next useful discriminator is not another same-context `dlopen()`
variant.  The new hypothesis is that the ACDB closure must be loaded by the
Android dynamic linker at process startup so initial-exec/static TLS allocation
is available before user code runs.

## Implementation

New public source:

- `workspace/public/src/android/acdb_payload_capture/a90_acdb_ownprocess_get_exec_linked_v2508.c`

New public builder:

- `workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2508.py`

New tests:

- `tests/test_build_android_acdb_ownprocess_get_exec_linked_v2508.py`

Private build output:

- `workspace/private/builds/audio/v2508-acdb-ownprocess-exec-linked-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2508`
- SHA256: `73c2ab686e2462e59c09c27b2f0e0d3ce8d84c2a3a814b0f787c3faba6bc1bda`
- Size: `6844` bytes

The helper directly declares and calls:

```c
acdb_loader_init_v3("/vendor/etc/acdbdata", "/data/local/tmp/a90-acdb-ownget/delta", 0);
acdb_ioctl(cmd, in, in_len, out, out_len);
```

It keeps the same bounded pure-read GET matrix:

| Field | Values |
|---|---|
| commands | `0x11394`, `0x12e01`, `0x130da`, `0x130dc` |
| input lengths | `0`, `4`, `8`, `16`, `32` |
| output lengths | `4`, `4916` |
| maximum calls | `40` |

The helper records one JSONL row per returned buffer and writes raw buffers only
under `/data/local/tmp/a90-acdb-ownget/` for private pull handling.

## Linkage result

`readelf -d` shows the desired startup-load ACDB dependency set:

```text
NEEDED libacdbloader.so
NEEDED libaudcal.so
NEEDED libdiag.so
NEEDED libacdb-fts.so
NEEDED libacdbrtac.so
NEEDED libadiertac.so
```

`readelf -Ws` confirms `acdb_loader_init_v3` and `acdb_ioctl` remain dynamic
imports resolved from those dependencies, while `dlopen`, `dlsym`, and `dlerror`
are not imported.

`file` confirms the output shape:

```text
ELF 32-bit LSB shared object, ARM, EABI5 version 1 (SYSV), dynamically linked, interpreter /system/bin/linker
```

## Safety boundaries

Preserved:

- no in-HAL injection;
- no wrapper-exec Magisk module;
- no HAL restart;
- no AudioTrack/playback;
- no native speaker write;
- no `/dev/msm_audio_cal` open/ioctl;
- no `0xC00461CB` calibration SET ioctl;
- no `acdb_loader_send_common_custom_topology` path;
- no committed raw payloads or vendor libraries.

This unit is host-only.  The built binary and manifest are private artifacts and
must not be committed.

## Validation

Commands run:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2508.py \
  tests/test_build_android_acdb_ownprocess_get_exec_linked_v2508.py
PYTHONPATH=tests python3 -m unittest tests.test_build_android_acdb_ownprocess_get_exec_linked_v2508 -v
python3 workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2508.py --build
readelf -d workspace/private/builds/audio/v2508-acdb-ownprocess-exec-linked-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2508
file workspace/private/builds/audio/v2508-acdb-ownprocess-exec-linked-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2508
```

Results:

- `py_compile`: pass
- V2508 unittest module: `5` tests pass
- ARM32 build: pass
- DT_NEEDED ACDB closure: pass
- prohibited symbol/source scan: pass through `source_state()` tests

## Next unit

V2509 should be the live Android handoff using the existing own-process runner
with this helper supplied through `--helper-path` and `--helper-sha256`.

Expected live discriminator:

1. If startup loading succeeds, the helper reaches `acdb_loader_init_v3` and then
   the pure-read `acdb_ioctl` GET matrix.
2. If the dynamic linker still fails before helper code starts, the runner should
   classify that as an exec-linked startup-loadability block from process stderr
   and pulled artifacts.
3. Any captured `out_len==4916` raw payload remains private and uncommitted.
4. A non-4916 out-buffer set remains operator-valuable partial evidence, not a
   dead run.
