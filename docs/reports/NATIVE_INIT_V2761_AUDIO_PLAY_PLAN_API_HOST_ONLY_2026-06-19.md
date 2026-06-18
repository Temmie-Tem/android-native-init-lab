# NATIVE_INIT_V2761_AUDIO_PLAY_PLAN_API_HOST_ONLY_2026-06-19

## Decision

`audio play` now exists as a first-class native-init command surface for bounded speaker playback planning. It is still dry-run only; PCM execution remains blocked until the native ACDB SET executor is implemented and live-validated.

## What changed

- Added `audio play [profile] [--mode probe|listen] [--amplitude-milli N] [--duration-ms N] [--dry-run|--execute]`.
- Added native stage `plan-bounded-pcm-playback` before blocked `bounded-pcm-playback`.
- The dry-run command reports card, PCM device, channels, sample rate, bit width, format, selected amplitude, selected duration, safety caps, and required prior stages.
- The command enforces the profile amplitude and duration caps before any playback path can run.
- `--execute` remains refused with `execute-not-implemented-native-pcm` and reports `playback_attempted=0`.

## Safety boundary

This is host-only/static behavior. The play command does not open ALSA, does not issue ALSA ioctls, does not write mixer controls, does not touch WSA smart-amp gain/boost, and does not flash or run on-device.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py tests/test_native_audio_play_plan_api_v2761.py tests/test_native_audio_stage_api_contract_v2756.py tests/test_native_audio_command_profile_contract_v2751.py` passed.
- `PYTHONPATH=tests python3 -m unittest tests.test_native_audio_play_plan_api_v2761 tests.test_native_audio_stage_api_contract_v2756 tests.test_native_audio_command_profile_contract_v2751` passed: 16 tests.
- `PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_native_audio_*v27*.py'` passed: 119 tests.
- `aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror -Iworkspace/public/src/native-init -c workspace/public/src/native-init/a90_audio.c -o /tmp/a90_audio_v2761.o` passed.
- `/tmp/a90_audio_v2761.o` SHA-256: `13b9a21a288e5293f003f8f88b4a9efe97b878a0b4c4601eb4b4c5337ad918d4`.
- `git diff --check` passed.
