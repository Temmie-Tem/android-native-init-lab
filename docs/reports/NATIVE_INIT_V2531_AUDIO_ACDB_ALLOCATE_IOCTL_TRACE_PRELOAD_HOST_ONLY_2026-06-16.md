# NATIVE_INIT_V2531_AUDIO_ACDB_ALLOCATE_IOCTL_TRACE_PRELOAD_HOST_ONLY_2026-06-16

## Scope

Host-only implementation of the next discriminator after V2530:

```text
Why does libacdbloader's AUDIO_ALLOCATE_CALIBRATION ioctl fail during
acdb_loader_init_v3?
```

No device action was run in this unit.  No native `/dev/msm_audio_cal` SET ioctl
or replay path was executed.

## Context

Operator verification reclassified the V2529/V2530 live run as a false positive:

- all direct GET rows returned `ret == -2`;
- all `out_len == 4` and `out_len == 4916` buffers were zero-filled;
- `acdb_loader_init_v3` returned `-12` because the internal
  `allocate_cal_block -> AUDIO_ALLOCATE_CALIBRATION` ioctl failed before the
  ACDB engine became usable.

Therefore the soft-fail GET matrix is closed as a dead end.  The next useful
measurement is syscall-level observation of the allocation ioctl return and
errno, plus AVC/dmesg context around the same run.

## Implementation

Added a small ARM32 preload library:

```text
workspace/public/src/android/acdb_payload_capture/a90_ioctl_trace_preload_v2531.c
```

It exports:

```c
int ioctl(int fd, unsigned long request, ...);
```

The wrapper:

- calls the real kernel ioctl via raw ARM EABI syscall `__NR_ioctl == 54`;
- mirrors libc-style `-1` plus `errno` for callers;
- logs each observed ioctl to
  `/data/local/tmp/a90-acdb-ownget/ioctl-trace-events.jsonl`;
- names the known calibration requests:
  - `0xc00461c8` = `AUDIO_ALLOCATE_CALIBRATION`;
  - `0xc00461c9` = `AUDIO_DEALLOCATE_CALIBRATION`;
  - `0xc00461cb` = `AUDIO_SET_CALIBRATION`.

Boundary: the preload only observes existing calls made by `libacdbloader.so`.
It does not open `/dev/msm_audio_cal`, does not call `acdb_ioctl`, does not call
`acdb_loader_init_v3`, and does not issue any extra ioctl.

## Builder

Added host-only builder:

```text
workspace/public/src/scripts/revalidation/build_android_ioctl_trace_preload_v2531.py
```

Private artifact, not committed:

```text
workspace/private/builds/audio/v2531-acdb-ioctl-trace-preload-host-only/bin/liba90_ioctl_trace_v2531.so
sha256: 01a0b6a3ac112a275a89f81be04873d7a574d7b332f051809ffa57bd8a4fe797
mode: 0600
file: ELF 32-bit LSB shared object, ARM, EABI5
```

Symbol verification:

```text
exports_ioctl: true
undefined_errno: true
does_not_import_acdb: true
```

`undefined_errno` is expected: the preload resolves bionic `__errno()` from the
own-process Android runtime and uses it only to preserve caller semantics after
the raw ioctl syscall.

## Runner Integration

Updated the existing own-process Android handoff runner:

```text
workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py
```

New behavior:

- stages `liba90_ioctl_trace_v2531.so` by default;
- runs the helper with:

```text
LD_PRELOAD=/data/local/tmp/a90-acdb-ownget/liba90_ioctl_trace_v2531.so
LD_LIBRARY_PATH=/data/local/tmp/a90-acdb-ownget:/vendor/lib:/system/lib:/system_ext/lib:/product/lib
```

- pulls `ioctl-trace-events.jsonl` with the existing private artifact directory;
- parses allocation ioctl diagnostics:
  - `audio_allocate_ioctl_count`;
  - `audio_allocate_ioctl_ret_values`;
  - `audio_allocate_ioctl_errno_values`;
  - `audio_set_ioctl_count`.

The existing log capture already preserves:

```text
logcat-avc-acdb-filter.txt
dmesg-avc-acdb-filter.txt
```

which covers the operator-requested AVC/dmesg context around the same run.

## Dry-Run State

The live runner dry-run is ready with the trace preload enabled:

```text
ok: true
live_ready: true
live_blockers: []
command_safety.ok: true
ioctl_trace_preload.ok: true
ioctl_trace_preload.mode: 0600
```

## Validation

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_ioctl_trace_preload_v2531.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  tests/test_build_android_ioctl_trace_preload_v2531.py \
  tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_build_android_ioctl_trace_preload_v2531 \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490
# Ran 26 tests: OK

python3 workspace/public/src/scripts/revalidation/build_android_ioctl_trace_preload_v2531.py \
  --build \
  --manifest-path workspace/private/builds/audio/v2531-acdb-ioctl-trace-preload-host-only/manifest.json

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py --dry-run
```

## Next Unit

Run the same checked Android handoff with the V2529 helper plus V2531 ioctl trace
preload, then rollback to V2321.

Expected decisive evidence:

- `ioctl-trace-events.jsonl` contains `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`)
  with exact `ret` and `errno`;
- `dmesg-avc-acdb-filter.txt` and `logcat-avc-acdb-filter.txt` show whether this
  is SELinux ioctl filtering, kernel argument rejection, or a non-AVC path;
- no `AUDIO_SET_CALIBRATION` success is required or expected for this measurement.

Do not rerun the soft-fail GET matrix without the V2531 ioctl trace; it cannot
distinguish transport failure from ACDB request failure.
