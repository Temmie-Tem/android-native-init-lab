# NATIVE_INIT_V2769_AUDIO_SETCAL_ION_REQUEST_PLAN_HOST_ONLY_2026-06-19

## Summary

V2769 adds the ION request-plan boundary for native `audio setcal --execute`.

After the verified SET-cal manifest is materialized, after `/dev/ion` and `/dev/msm_audio_cal` open successfully, and after the dmabuf allocation work-list is built, native-init now derives an `audio_setcal_ion_request_plan`. Each request records the payload length, ION heap mask, ION flags, cal type, role, sequence, and unallocated `dmabuf_fd=-1` / `mem_handle=-1` placeholders.

No ION allocation ioctl is called in this unit.

## Why

The future native SET replay path needs to convert private payload-bearing ACDB entries into per-payload ION allocation requests before patching fresh native dma-buf fds into the exact captured `AUDIO_SET_CALIBRATION` args. V2768 selected the dmabuf payload work-list. V2769 gives that work-list a typed request representation, using the same cached system heap contract as the proven V2635 scaffold.

## Behavior

- Adds ION request constants:
  - `AUDIO_ION_SYSTEM_HEAP_ID=25`
  - `AUDIO_ION_SYSTEM_HEAP_MASK=(1U << 25)`
  - `AUDIO_ION_FLAG_CACHED=1`
- Adds `audio_setcal_ion_request_slot` and `audio_setcal_ion_request_plan`.
- Builds one request only for each positive-length active allocation slot.
- Initializes result fields as unallocated placeholders: `dmabuf_fd=-1`, `mem_handle=-1`.
- Emits `audio.setcal.execute.ion.plan.*` telemetry before descriptor close and before final execute refusal.
- Keeps `alloc_attempted=0` and `ioctl_attempted=0`.

## Safety

- Host-only source/test change; no boot image was built or flashed.
- No `/dev/ion` allocation ioctl is called.
- No `/dev/msm_audio_cal` calibration ioctl is called.
- No `AUDIO_ALLOCATE_CALIBRATION`, `AUDIO_SET_CALIBRATION`, or `AUDIO_DEALLOCATE_CALIBRATION` execution path is introduced.
- The native command still refuses before the first ioctl.

## Validation

```text
python3 -m py_compile tests/test_native_audio_setcal_ion_request_plan_v2769.py tests/test_native_audio_setcal_allocation_plan_v2768.py tests/test_native_audio_setcal_open_boundary_v2767.py
PYTHONPATH=tests python3 -m unittest tests.test_native_audio_setcal_ion_request_plan_v2769 tests.test_native_audio_setcal_allocation_plan_v2768 tests.test_native_audio_setcal_open_boundary_v2767
# 14 tests OK

aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror -Iworkspace/public/src/native-init -c workspace/public/src/native-init/a90_audio.c -o /tmp/a90_audio_v2769.o
file /tmp/a90_audio_v2769.o
# ELF 64-bit LSB relocatable, ARM aarch64
sha256sum /tmp/a90_audio_v2769.o
# 4f273168d61c7afabc93234a9a0eda856ae40f47b883b67ffbd0fa519c7ae73a

PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_native_audio_*v27*.py'
# 153 tests OK

git diff --check
# pass
```

## Next

The next non-churn executor step is to add the concrete ION allocation result model and gated executor stub that can populate `dmabuf_fd`/`mem_handle` only behind a separate live/device approval. Until then, the command remains metadata-only after the open boundary.
