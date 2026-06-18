# NATIVE_INIT_V2763_AUDIO_SETCAL_EXECUTE_GATE_HOST_ONLY_2026-06-19

## Scope

Host-only Audio Tier-A/B bridge unit. This turns `audio setcal --execute` from a
bare refusal into a safer API gate: the command now requires the private SET
manifest, verifies it, drains the declared arg/payload files, emits a concrete
native replay ABI plan, and then refuses before opening audio devices or issuing
calibration ioctls.

No device action, flash, playback, mixer write, `/dev/ion` open,
`/dev/msm_audio_cal` open, or `AUDIO_SET_CALIBRATION` ioctl occurred.

## Changes

- Added named native SET-cal ABI constants:
  - `/dev/ion`
  - `/dev/msm_audio_cal`
  - `AUDIO_ALLOCATE_CALIBRATION = 0xc00461c8`
  - `AUDIO_DEALLOCATE_CALIBRATION = 0xc00461c9`
  - `AUDIO_SET_CALIBRATION = 0xc00461cb`
- `audio setcal --execute` now:
  - requires `--manifest`;
  - runs the existing manifest verifier;
  - auto-loads verified private arg/payload files;
  - prints `audio.setcal.execute.plan.*` fields for the future executor;
  - exits with `execute-not-implemented-native-setcal-ioctl` before runtime device access.
- Updated tests to treat ioctl constants as published ABI metadata while still
  asserting `devices_opened=0` and `ioctl_attempted=0` for this unit.

## Safety Boundary

This is still a non-mutating host/static unit. The execute gate does not call
`open()` on audio devices and does not call `ioctl()`. The only file reads in the
execute path are the already verified private manifest payload files under the
allowed runtime/replay prefixes.

## Validation

```bash
python3 -m py_compile \
  tests/test_native_audio_setcal_execute_gate_v2763.py \
  tests/test_native_audio_setcal_manifest_command_v2757.py \
  tests/test_native_audio_setcal_load_api_v2760.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_setcal_execute_gate_v2763 \
  tests.test_native_audio_setcal_manifest_command_v2757 \
  tests.test_native_audio_setcal_prepare_api_v2759 \
  tests.test_native_audio_setcal_load_api_v2760
# Ran 18 tests: OK

PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_native_audio_*v27*.py'
# Ran 127 tests: OK

aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror \
  -Iworkspace/public/src/native-init \
  -c workspace/public/src/native-init/a90_audio.c \
  -o /tmp/a90_audio_v2763.o
file /tmp/a90_audio_v2763.o
# ELF 64-bit LSB relocatable, ARM aarch64, version 1 (SYSV), not stripped
sha256sum /tmp/a90_audio_v2763.o
# 0f1ea8eb94928110e39f25de607cbd0314636db4635e06a4bee50b134336e1a2
```

## Result

`audio setcal --execute` is now an API-shaped executor gate rather than a plain
stub. It proves the manifest and bytes are available, exposes the replay ABI and
sequence, and preserves the hard stop before volatile calibration ioctls. Next
unit can move one of the planned steps behind a similarly bounded implementation
boundary.
