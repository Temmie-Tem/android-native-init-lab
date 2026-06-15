# NATIVE_INIT_V2529_AUDIO_ACDB_OWNPROCESS_SOFTFAIL_GET_HELPER_HOST_ONLY_2026-06-16

## Scope

Host-only implementation of the V2528 decision: continue the bounded pure-read
`acdb_ioctl` GET matrix after the now-reproducible `acdb_loader_init_v3 == -12`
allocation-side-effect failure.

No device action was run in this unit.  No native `/dev/msm_audio_cal` calibration
ioctl is issued by the helper source.

## Why this change

V2527 proved the own-process helper now exits promptly but stops before every
GET attempt:

```text
acdb_loader_init_v3 -> -12
ACDB -> Error: Sending AUDIO_ALLOCATE_CALIBRATION, result = -1
ACDB -> allocate_cal_block failed!
ACDB -> Cannot allocate memory!
```

V2528 host RE narrowed this to a side effect inside full `libacdbloader` init,
after DB load plus ACPH/RTAC init succeeded.  Therefore an unchanged live rerun
only reproduces the same zero-row outcome.

The new discriminator is narrow:

```text
If init_v3 returns -12 after DB/ACPH/RTAC setup, does direct pure-read
acdb_ioctl still return any out-buffer records?
```

## Implementation

Touched public files:

- `workspace/public/src/android/acdb_payload_capture/a90_acdb_ownprocess_get_exec_linked_v2512.c`
- `workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2512.py`
- `workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py`
- focused tests under `tests/`

Behavior change:

```c
#define A90_INIT_RET_ALLOCATE_CAL_FAILED (-12)

init_ret = acdb_loader_init_v3(A90_ACDB_FILES_PATH, A90_DELTA_DIR, 0U);
if (init_ret != 0) {
    a90_write_error_event("acdb_loader_init_v3", init_ret,
                          init_ret == -12
                              ? "soft_continue_after_allocate_cal_failure"
                              : NULL);
    if (init_ret != -12)
        a90_exit(29);
}

/* same bounded pure-read GET matrix */
```

Only the `-12` allocation-failure return is soft-continued.  Other init failures
still stop exactly as before.

The builder now tags the private artifact as:

```text
run_id: V2529
build_tag: v2529-acdb-ownprocess-softfail-get-host-only
artifact: a90_acdb_ownprocess_get_exec_linked_v2529
```

The V2490 live runner default helper selection now points at that exec-linked
V2529 build instead of the older V2489 dlopen-era helper.

## Hard boundaries preserved

Source/build invariants verify:

- no `/dev/msm_audio_cal` path in the helper source;
- no `AUDIO_ALLOCATE_CALIBRATION` / `AUDIO_SET_CALIBRATION` symbols;
- no direct SET ioctl constant `0xC00461CB`;
- no `acdb_loader_send_common_custom_topology` call path;
- no in-HAL injection, playback, `tinyplay`, `tinymix`, or AudioTrack;
- raw output remains private only.

## Private build

Private artifact, not committed:

```text
workspace/private/builds/audio/v2529-acdb-ownprocess-softfail-get-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2529
sha256: c97b17dc0cc35f0450f04d179ec2e2cbb1b6ec5c11cdfa58bee20c53c927a9c4
file: ELF 32-bit LSB shared object, ARM, EABI5, interpreter /system/bin/linker
DT_NEEDED: libacdbloader.so, libaudcal.so, libdiag.so, libacdb-fts.so, libacdbrtac.so, libadiertac.so
```

Runner dry-run now resolves this artifact by default:

```text
live_ready=True
helper_ok=True
helper_path=workspace/private/builds/audio/v2529-acdb-ownprocess-softfail-get-host-only/bin/a90_acdb_ownprocess_get_exec_linked_v2529
command_safety.ok=True
live_blockers=[]
```

## Validation

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2512.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  tests/test_build_android_acdb_ownprocess_get_exec_linked_v2512.py \
  tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_build_android_acdb_ownprocess_get_exec_linked_v2512 \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490
# Ran 26 tests: OK

python3 workspace/public/src/scripts/revalidation/build_android_acdb_ownprocess_get_exec_linked_v2512.py \
  --dry-run --build \
  --build-root workspace/private/builds/audio/v2529-acdb-ownprocess-softfail-get-host-only \
  --manifest-path workspace/private/builds/audio/v2529-acdb-ownprocess-softfail-get-host-only/manifest.json

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py --dry-run
```

## Next unit

A future live run can use the existing V2490 Android-handoff runner with the new
V2529 helper selected by default.  Expected discriminators:

- `acdb-get-success-4916`: topology bytes captured privately;
- `acdb-get-full-outbuf-set-no-4916`: valuable ordered out-buffer set, partial success;
- `init-v3-block-audio-allocate-calibration-failed` with zero rows: soft-continue did
  not reach a usable initialized ACDB engine, so the next host-only unit must find a
  true DB-only init path or a lower-level load+GET entry.

No live step was executed in V2529.
