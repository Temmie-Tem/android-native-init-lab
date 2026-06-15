# NATIVE_INIT_V2534 — ACDB fake-allocate own-process GET attempt

Date: 2026-06-16

## Scope

Operator handover requested bypassing the V2533 `AUDIO_ALLOCATE_CALIBRATION` `EINVAL` by reusing the V2531 `ioctl()` preload as an interposer:

- `AUDIO_ALLOCATE_CALIBRATION` (`0xc00461c8`) returns success without a kernel ioctl.
- `AUDIO_DEALLOCATE_CALIBRATION` (`0xc00461c9`) returns success without a kernel ioctl.
- No native speaker write and no intended `AUDIO_SET_CALIBRATION` kernel SET.
- Rollback target remains V2321.

This remained an own-process Android handoff measurement. Raw artifacts and binaries remain private.

## Implementation

Changed `workspace/public/src/android/acdb_payload_capture/a90_ioctl_trace_preload_v2531.c` from observer-only to env-gated interposition:

- Default mode remains pass-through observation.
- `A90_ACDB_FAKE_ALLOCATE=1` enables fake-success mode.
- The preload still does not open `/dev/msm_audio_cal`, does not call `acdb_ioctl`, and does not issue extra ioctls.
- It logs `intercept` and an audio-cal argument snapshot for known audio-cal ioctls.

The live V2534 run used the first rebuilt preload SHA:

```text
1ef46f4a061ed63e7639cb2ba9f7520217a24b25798470a237cfb4ab83e95785
```

After live analysis, the preload was hardened host-only so fake mode also no-ops `AUDIO_SET_CALIBRATION`; the current rebuilt private SHA is:

```text
3fddb586520fe277af9d1f2102cb3ad35d089dbc81bf1fab28b33ce1a635dd23
```

No second live run was executed after that hardening.

## Live run

Private run directory:

```text
workspace/private/runs/audio/v2534-acdb-fake-allocate-get-20260616-061334
```

Runner result:

```text
v2490-ownprocess-context-only-no-events-before-rollback-rollback-pass
```

Final device state:

```text
version: 0.9.285 build=v2321-usb-clean-identity-rodata
selftest: pass=11 warn=1 fail=0
```

## Evidence

The fake allocate path did change the blocker: `AUDIO_ALLOCATE_CALIBRATION` no longer failed with `EINVAL`.

Current parser summary over the pulled artifacts:

```json
{
  "classification": "ownprocess-context-only-no-events",
  "ioctl_trace_event_count": 57,
  "audio_allocate_ioctl_count": 26,
  "audio_allocate_ioctl_ret_values": [0],
  "audio_allocate_ioctl_errno_values": [0],
  "audio_allocate_ioctl_intercepts": ["fake-success"],
  "audio_allocate_ioctl_fake_success_count": 26,
  "audio_deallocate_ioctl_count": 1,
  "audio_deallocate_ioctl_intercepts": ["fake-success"],
  "audio_deallocate_ioctl_fake_success_count": 1,
  "audio_set_ioctl_count": 1,
  "audio_set_ioctl_intercepts": ["pass-through"],
  "audio_set_ioctl_fake_success_count": 0
}
```

Representative allocate snapshot:

```json
{
  "request": "0xc00461c8",
  "name": "AUDIO_ALLOCATE_CALIBRATION",
  "ret": 0,
  "errno": 0,
  "intercept": "fake-success",
  "arg_snapshot": {
    "data_size": 32,
    "version": 0,
    "cal_type": 39,
    "cal_type_size": 16,
    "type_version": 0,
    "buffer_number": 0,
    "cal_size": 4916,
    "mem_handle": 30
  }
}
```

The ACDB loader reached the custom-topology path:

```text
ACDB -> send_common_custom_topology
ACDB -> ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_SIZE_V3
Reallocate memory for Custom Topology to size: 4916
ACDB -> allocate_cal_block: mmap
ACDB -> ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_V3
ACDB -> ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_V3: size:0x1334 ret=0
ACDB -> CORE_CUSTOM_TOPOLOGIES
ACDB -> acdb_loader_send_common_custom_topology: Common custom topology in use
```

However, the live preload allowed one real kernel SET pass-through:

```json
{
  "request": "0xc00461cb",
  "name": "AUDIO_SET_CALIBRATION",
  "ret": 0,
  "errno": 0,
  "intercept": "pass-through",
  "arg_snapshot": {
    "data_size": 32,
    "version": 0,
    "cal_type": 39,
    "cal_type_size": 16,
    "type_version": 0,
    "buffer_number": 0,
    "cal_size": 4916,
    "mem_handle": 30
  }
}
```

The helper then crashed:

```text
ownget.rc: 139
ownget.stderr.txt: Segmentation fault
```

No `acdb-ownget-events.jsonl` rows or raw GET `.bin` payloads were produced.

## Interpretation

- The V2533 `AUDIO_ALLOCATE_CALIBRATION` `EINVAL` was bypassed in-process: 26 allocate calls returned fake success.
- The ACDB engine progressed far enough to fetch the 4916-byte custom topology internally.
- The old fake mode was not pure-read in practice because `send_common_custom_topology` reached its normal `AUDIO_SET_CALIBRATION` path and the preload passed it through.
- Because no raw `acdb_ioctl` out-buffer rows were produced and the helper ended with `SIGSEGV`, V2534 is not a capture success.
- This run is still valuable because it proves the fake-allocate idea advances ACDB init, and it exposes that fake mode must also suppress SET to preserve the measurement boundary.

## Host-only correction after stop

The current source now treats fake mode as:

```text
A90_ACDB_FAKE_ALLOCATE=1 => fake-success for AUDIO_ALLOCATE_CALIBRATION, AUDIO_DEALLOCATE_CALIBRATION, and AUDIO_SET_CALIBRATION only
```

All unrelated ioctls still pass through. This prevents another real SET from escaping if the same route is retried.

## Validation

Host validation after the SET-blocking correction:

```text
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/build_android_ioctl_trace_preload_v2531.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py \
  tests/test_build_android_ioctl_trace_preload_v2531.py \
  tests/test_native_audio_acdb_ownprocess_get_live_handoff_v2490.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_build_android_ioctl_trace_preload_v2531 \
  tests.test_native_audio_acdb_ownprocess_get_live_handoff_v2490

Ran 29 tests in 0.662s — OK
```

Private rebuilt preload:

```text
workspace/private/builds/audio/v2531-acdb-ioctl-trace-preload-host-only/bin/liba90_ioctl_trace_v2531.so
sha256=3fddb586520fe277af9d1f2102cb3ad35d089dbc81bf1fab28b33ce1a635dd23
```

Dry-run with `--fake-audio-cal-allocate`:

```text
live_ready=true
command_safety.ok=true
fake_mode_env=A90_ACDB_FAKE_ALLOCATE=1
```

Device rollback health after live run:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

## Next

Do not advance to replay from V2534. The viable next measurement, if pursued, is a single rerun with the corrected fake mode that suppresses SET as well as allocate/deallocate, then require:

- `AUDIO_SET_CALIBRATION` count may be nonzero, but every SET event must have `intercept=fake-success`.
- No real kernel SET pass-through.
- `acdb_ioctl` rows must include `ret==0` and non-zero raw out-buffers; `out_len==4916` success still requires non-zero SHA.
- Rollback to V2321 and selftest `fail=0`.
