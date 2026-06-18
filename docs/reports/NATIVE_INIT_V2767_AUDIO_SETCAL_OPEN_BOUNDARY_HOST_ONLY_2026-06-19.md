# NATIVE_INIT_V2767_AUDIO_SETCAL_OPEN_BOUNDARY_HOST_ONLY_2026-06-19

## Summary

V2767 advances `audio setcal --execute` from a manifest-plan-only gate to the first executor boundary: after a verified private manifest is materialized into an `audio_setcal_manifest_plan`, native-init now attempts to open the two runtime devices required by the future SET-cal replay executor:

- `/dev/ion`
- `/dev/msm_audio_cal`

It then closes any opened descriptors and refuses before the first calibration ioctl. This is still not SET replay; it is an open-only executor boundary with explicit telemetry and `ioctl_attempted=0` markers.

## Why

The audio epic needs the one-shot SET-cal replay scaffold to become a native-init command surface. V2766 created a trusted manifest-plan object. V2767 connects that plan to the first concrete executor resource boundary without crossing into `AUDIO_ALLOCATE_CALIBRATION`, `AUDIO_SET_CALIBRATION`, or `AUDIO_DEALLOCATE_CALIBRATION`.

## Behavior

- Adds `audio_setcal_execute_open_state` to track `/dev/ion` and `/dev/msm_audio_cal` descriptors.
- Adds `audio_setcal_open_execute_devices()` and close helpers.
- `audio setcal --execute` now:
  1. verifies and loads the manifest,
  2. prints the manifest-backed execute plan,
  3. opens `/dev/ion` and `/dev/msm_audio_cal` with `O_RDWR|O_CLOEXEC`,
  4. closes both descriptors,
  5. refuses before any ioctl.
- If either open fails, the command reports `execute-open-failed-before-ioctl` and returns that open error.
- Full SET replay remains unimplemented and blocked before ioctl.

## Safety

- Host-only source/test change; no boot image was built or flashed.
- No calibration ioctl is called.
- No `AUDIO_SET_CALIBRATION` execution path is introduced.
- Any opened descriptor is closed before returning.
- Existing private payload hygiene remains unchanged.

## Validation

```text
python3 -m py_compile tests/test_native_audio_setcal_open_boundary_v2767.py tests/test_native_audio_setcal_manifest_plan_v2766.py tests/test_native_audio_setcal_execute_gate_v2763.py
PYTHONPATH=tests python3 -m unittest tests.test_native_audio_setcal_open_boundary_v2767 tests.test_native_audio_setcal_manifest_plan_v2766 tests.test_native_audio_setcal_execute_gate_v2763
# 13 tests OK

aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror -Iworkspace/public/src/native-init -c workspace/public/src/native-init/a90_audio.c -o /tmp/a90_audio_v2767.o
file /tmp/a90_audio_v2767.o
# ELF 64-bit LSB relocatable, ARM aarch64
sha256sum /tmp/a90_audio_v2767.o
# 8e6d1f58b2fe06de6a537463e488ae3947298b78c77a9f578b8d02a1be9a775a

PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_native_audio_*v27*.py'
# 144 tests OK

git diff --check
# pass
```

## Next

The next executor step should keep the same monotonic safety ladder:

1. add an allocation-plan boundary that refuses before `AUDIO_ALLOCATE_CALIBRATION`, or
2. implement the first dry-run/executor object that can pair manifest-plan entries with ION allocation metadata while still refusing before `AUDIO_SET_CALIBRATION`.

Actual calibration ioctls and live speaker replay remain separate device-gated work.
