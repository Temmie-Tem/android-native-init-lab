# NATIVE_INIT_V2768_AUDIO_SETCAL_ALLOCATION_PLAN_HOST_ONLY_2026-06-19

## Summary

V2768 adds the next SET-cal executor boundary: a typed allocation work-list derived from the verified `audio_setcal_manifest_plan`.

The command still does not call `AUDIO_ALLOCATE_CALIBRATION`, `AUDIO_SET_CALIBRATION`, or `AUDIO_DEALLOCATE_CALIBRATION`. After `audio setcal --execute` verifies and loads the manifest and successfully opens `/dev/ion` plus `/dev/msm_audio_cal`, it now builds an `audio_setcal_allocation_plan` containing only the manifest entries that require dmabuf-backed payload allocation.

## Why

The future native SET replay needs to allocate dmabuf slots only for payload-bearing cal types while replaying header-only entries directly. V2766 materialized trusted manifest entries; V2767 added the open-only device boundary. V2768 converts those manifest entries into the exact allocation work-list needed by the later ION/ioctl executor.

## Behavior

- Adds `audio_setcal_allocation_slot` and `audio_setcal_allocation_plan`.
- Builds the allocation plan only from `present && dmabuf_expected` manifest entries.
- Tracks per-slot sequence, cal type, role, payload size, and loaded payload bytes.
- Prints `audio.setcal.execute.allocate.plan.*` telemetry after device-open success and before descriptor close.
- Keeps `allocate_attempted=0` and `ioctl_attempted=0`.
- If device open fails, it closes any opened descriptors and returns before allocation-plan emission.

## Safety

- Host-only source/test change; no boot image was built or flashed.
- No calibration ioctl is called.
- No ION allocation ioctl is called.
- The code still refuses before the first calibration ioctl.
- All opened descriptors are closed before returning.

## Validation

```text
python3 -m py_compile tests/test_native_audio_setcal_allocation_plan_v2768.py tests/test_native_audio_setcal_open_boundary_v2767.py tests/test_native_audio_setcal_manifest_plan_v2766.py
PYTHONPATH=tests python3 -m unittest tests.test_native_audio_setcal_allocation_plan_v2768 tests.test_native_audio_setcal_open_boundary_v2767 tests.test_native_audio_setcal_manifest_plan_v2766
# 14 tests OK

aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror -Iworkspace/public/src/native-init -c workspace/public/src/native-init/a90_audio.c -o /tmp/a90_audio_v2768.o
file /tmp/a90_audio_v2768.o
# ELF 64-bit LSB relocatable, ARM aarch64
sha256sum /tmp/a90_audio_v2768.o
# d989d6ffe078b32f0dc4584a5c484ccaa0f873ae9360903709a4a7fba2def80d

PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_native_audio_*v27*.py'
# 148 tests OK

git diff --check
# pass
```

## Next

The next non-churn executor step is to add an ION allocation object/boundary that can represent returned fd/handle metadata, while still refusing before the first real `AUDIO_ALLOCATE_CALIBRATION` ioctl unless a live-gated device unit explicitly authorizes it.
