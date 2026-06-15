# NATIVE_INIT_V2475_AUDIO_ACDBTAP_INTERPOSER_BUILD_2026-06-15

## Decision

`v2475-acdbtap-interposer-build-host-only`

V2475 implements the operator-provided ACDB capture spec as a **host-only
build artifact**: a 32-bit ARM shared object that interposes `acdb_ioctl` and
captures bounded output buffers before the HAL copies them into the opaque
dma-buf. No Android boot, Magisk staging, HAL restart, playback, native speaker
write, or `/dev/msm_audio_cal` calibration ioctl ran in this unit.

## Scope

- Added interposer source:
  `workspace/public/src/android/acdb_payload_capture/libacdbtap_v2475.c`
- Added host-only builder:
  `workspace/public/src/scripts/revalidation/build_android_acdbtap_v2475.py`
- Added focused tests:
  `tests/test_build_android_acdbtap_v2475.py`
- Generated private artifact:
  `workspace/private/builds/audio/v2475-acdbtap-interposer-build/bin/libacdbtap.so`

The generated `.so` is private build output and is not committed.

## Interposer contract

The source exports:

```c
int32_t acdb_ioctl(uint32_t cmd,
                   const uint8_t *in,
                   uint32_t in_len,
                   uint8_t *out,
                   uint32_t out_len);
```

At runtime it:

1. Resolves the real symbol lazily with `dlsym(RTLD_NEXT, "acdb_ioctl")`.
2. Calls the real `acdb_ioctl`.
3. If `out != NULL` and `0 < out_len <= 65536`, computes SHA-256 over
   `out[0:out_len]`.
4. Writes raw output bytes to private path
   `/data/local/tmp/a90-acdb-tap/acdbtap-<seq>-cmd-<cmd>-len-<out_len>.bin`.
5. Appends one JSONL metadata record to
   `/data/local/tmp/a90-acdb-tap/acdbtap-events.jsonl`.

The metadata flags both:

- `out_len == 4916` target payload candidates;
- `out_len == 4` size-query candidates.

The source is freestanding: no libc headers, no malloc, no liblog, and no
pthread dependency. It uses raw ARM EABI syscalls for `openat`, `write`, `close`,
`getpid`, and `gettid`, leaving only `dlsym` unresolved for the Android loader
to resolve in-process.

## Build result

Private build output:

- Path:
  `workspace/private/builds/audio/v2475-acdbtap-interposer-build/bin/libacdbtap.so`
- SHA-256:
  `7bf64bb04530202a8dc859db0826cd399ff34d51ea4628eb586808de82968be4`
- Size: `5864`
- `file`:
  `ELF 32-bit LSB shared object, ARM, EABI5 version 1 (SYSV), dynamically linked`
- Target: `armv7a-linux-androideabi29`
- Dynamic symbol check:
  - exports `acdb_ioctl`: `true`
  - leaves `dlsym` undefined for runtime resolution: `true`

The private toolchain needed compatibility host libraries for the build tools:

- `libtinfo.so.5` from `workspace/private/inputs/toolchains/compat-libs/`
- `libxml2.so.2` symlinked to host `/usr/lib/x86_64-linux-gnu/libxml2.so.16`
  under the private build `host-libs` directory

## Safety boundary

This unit is measurement-only and host-only.

It does **not**:

- open `/dev/msm_audio_cal`;
- issue `AUDIO_ALLOCATE_CALIBRATION`, `AUDIO_SET_CALIBRATION`, or any other
  native calibration ioctl;
- write mixer controls;
- play PCM;
- stage Magisk files;
- restart Android audio HAL;
- capture or commit raw ACDB bytes.

Future live use still needs a separate recoverable Android handoff runner that
stages this `.so` privately, creates `/data/local/tmp/a90-acdb-tap`, injects it
into `android.hardware.audio.service`, restarts the HAL, runs the bounded
AudioTrack speaker stimulus, pulls private artifacts, cleans up, and rolls back
to `v2321` with final `selftest fail=0`.

## Validation

Commands run:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 -m py_compile workspace/public/src/scripts/revalidation/build_android_acdbtap_v2475.py

python3 -m py_compile tests/test_build_android_acdbtap_v2475.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_build_android_acdbtap_v2475 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/build_android_acdbtap_v2475.py \
    --dry-run --build

git diff --check
```

Results:

- Focused tests: `4` passed.
- ARM32 shared-object build: passed.
- `file`: confirmed ARM 32-bit shared object.
- `readelf`: confirmed exported `acdb_ioctl` and unresolved `dlsym`.
- Source safety scan: required tokens present, prohibited native calibration /
  playback / persistent Magisk tokens absent.
- `git diff --check`: passed.

## Next boundary

The next meaningful unit is **host-only live-runner design** for the recoverable
Android/Magisk measurement capsule that will use `libacdbtap.so`. Do not jump
directly to live execution. That design must pin:

- how `LD_PRELOAD` is introduced into `android.hardware.audio.service`;
- how the HAL is restarted and later restored;
- exact SELinux/AVC observation and abort behavior;
- private raw artifact pull/cleanup;
- rollback to `v2321`;
- public redaction policy: only command id, lengths, return code, and SHA-256.
