# NATIVE_INIT_V2474_AUDIO_ACDB_REPLAY_SCAFFOLD_2026-06-15

## Decision

`v2474-acdb-replay-scaffold-host-only`

V2474 implements the payload-independent native ACDB replay scaffold requested by
the 2026-06-15 `GOAL.md` operator nudge. It does **not** run on the device, does
**not** issue `/dev/msm_audio_cal` ioctls, and does **not** replay real
calibration. Native calibration ioctls remain blocked live until the real
`CORE_CUSTOM_TOPOLOGIES` payload bytes, length, SHA-256, mem-handle policy, and
cleanup policy are pinned.

## Scope

- Added source-controlled helper:
  `workspace/public/src/native-init/helpers/a90_acdb_replay_scaffold_v2474.c`
- Added host-only build/manifest planner:
  `workspace/public/src/scripts/revalidation/native_audio_acdb_replay_scaffold_v2474.py`
- Added focused tests:
  `tests/test_native_audio_acdb_replay_scaffold_v2474.py`
- Generated private-only artifacts under:
  `workspace/private/builds/audio/v2474-audio-acdb-replay-scaffold/`

No flash, Android boot, Magisk action, ADSP action, mixer write, PCM playback,
or calibration ioctl ran in this unit.

## Source-confirmed ABI basis

Local kernel source confirms the replay scaffold shape:

- `AUDIO_ALLOCATE_CALIBRATION`, `AUDIO_DEALLOCATE_CALIBRATION`, and
  `AUDIO_SET_CALIBRATION` are public `CAL_IOCTL_MAGIC 'a'` ioctls 200/201/203
  in `techpack/audio/4.0/include/uapi/linux/msm_audio_calibration.h`.
- `audio_cal_shared_ioctl()` copies the caller-provided request body, validates
  `data_size`, `cal_type`, `cal_type_size`, and `buffer_number`, then dispatches
  allocate/deallocate/set callbacks.
- `CORE_CUSTOM_TOPOLOGIES_CAL_TYPE` is cal type `39`.
- `cal_utils_set_cal()` requires a pre-existing cal block when `mem_handle > 0`;
  therefore the future live sequence must allocate before set.
- `create_cal_block()` stores `audio_cal_data.mem_handle` as the ION/dma-buf fd,
  and `msm_audio_ion_import()` imports it with `dma_buf_get(fd)`.
- This kernel's ION ABI returns a dma-buf fd directly from `ION_IOC_ALLOC` in
  `struct ion_allocation_data.fd`.

## Replay scaffold contract

The scaffold encodes the minimal topology replay shape from V2462:

1. Allocate an ION/dma-buf of the captured payload length.
2. Fill it with payload bytes.
3. Open `/dev/msm_audio_cal`.
4. Issue `AUDIO_ALLOCATE_CALIBRATION` for:
   - `cal_type=39`
   - `buffer_number=0`
   - `cal_size=0`
   - `mem_handle=<dmabuf fd>`
5. Issue `AUDIO_SET_CALIBRATION` for:
   - `cal_type=39`
   - `buffer_number=0`
   - `cal_size=4916`
   - `mem_handle=<same dmabuf fd>`
6. Keep both `/dev/msm_audio_cal` and dmabuf fds open across the bounded PCM
   probe.
7. Explicitly issue `AUDIO_DEALLOCATE_CALIBRATION` for the same
   cal-type/buffer/mem-handle, then close all fds.

The default compiled binary is intentionally **describe-only**. The live replay
path is behind compile-time guard `A90_ENABLE_NATIVE_CALIBRATION_EXECUTE`, and
the V2474 build does not define it. Accidental `--execute` in the built scaffold
fails closed before any device open or ioctl.

## Placeholder payload

The planner materialized a deterministic synthetic placeholder only for host
build/test:

- Path:
  `workspace/private/builds/audio/v2474-audio-acdb-replay-scaffold/placeholder-core-custom-topologies-4916.bin`
- Size: `4916`
- SHA-256:
  `b5428c64b3287c82d32b1fab12aa7b8d6d4cd35478d46a77590cfc6b509f5419`
- Mode: `0600`

This is **not** real ACDB data and is explicitly marked unusable for live replay.

## Private build artifact

The host-only planner built the default-disabled AArch64 scaffold:

- Path:
  `workspace/private/builds/audio/v2474-audio-acdb-replay-scaffold/bin/a90_acdb_replay_scaffold_v2474`
- SHA-256:
  `5e7552b7221fe1a2f355c8dd5897d942cd7bee50202fa9c2273f817c7450a233`
- `file`:
  `ELF 64-bit LSB executable, ARM aarch64, statically linked`
- Execute support compiled in: `false`

The binary is private/generated and is not committed.

## Cross-validation staging

The scaffold also records the private host cross-validation input layout:

- `workspace/private/inputs/audio/acdb_replay/acdbdata`
- `workspace/private/inputs/audio/acdb_replay/libs/libaudcal.so`
- `workspace/private/inputs/audio/acdb_replay/libs/libacdb-fts.so`
- `workspace/private/inputs/audio/acdb_replay/libs/libacdbrtac.so`
- `workspace/private/inputs/audio/acdb_replay/libs/libadiertac.so`

Current state: `ready=false` because those private inputs are not all staged.
They are proprietary/private inputs and must never be committed.

## Validation

Commands run:

```bash
PYTHONPATH=tests:workspace/public/src/scripts/revalidation \
  python3 -m unittest tests.test_native_audio_acdb_replay_scaffold_v2474 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_replay_scaffold_v2474.py \
    --dry-run --materialize-placeholder --build-helper --no-strip

git diff --check
```

Results:

- Focused tests: `6` passed.
- AArch64 static helper build: passed.
- Placeholder materialization: passed, `4916` bytes.
- Source safety guard: passed (`A90_ENABLE_NATIVE_CALIBRATION_EXECUTE` absent
  from build defines; default execute blocked).
- `git diff --check`: passed.

## Next boundary

Do not run native calibration ioctls from this scaffold yet. The next live
replay gate remains blocked until a report pins:

- real payload byte provenance and private path;
- real payload length and SHA-256;
- whether the native replay should use ION system heap, audio heap, or another
  specific heap/mem-handle policy;
- expected return values and abort policy for allocate/set/deallocate;
- bounded PCM probe ordering and cleanup behavior;
- why the sequence remains within the observed low-amplitude route envelope.

The operator-delivered capture spec
`docs/OPERATOR_ACDB_IOCTL_INTERPOSE_CAPTURE_SPEC_2026-06-15.md` defines the
current primary route to obtain those bytes: ARM32 `LD_PRELOAD` interposition of
`acdb_ioctl` inside the stock audio HAL process, dumping private `out_len==4916`
buffers before the dma-buf copy. That is the next payload-capture implementation
frontier; cross-process dmabuf/source-buffer snooping remains closed.
