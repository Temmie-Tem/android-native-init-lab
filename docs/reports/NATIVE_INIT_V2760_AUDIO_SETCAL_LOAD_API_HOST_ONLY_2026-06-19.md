# NATIVE_INIT_V2760_AUDIO_SETCAL_LOAD_API_HOST_ONLY_2026-06-19

## Decision

`audio setcal <profile> --manifest <path> --load --dry-run` is now the next host-first native-init ACDB SET API step after verify/prepare.

## What changed

- Added native stage `load-acdb-payload-files` between `prepare-acdb-payload-bundle` and blocked `replay-acdb-setcal-sequence`.
- Added `--load` to `audio setcal`.
- The command verifies the manifest, opens only the manifest-declared regular arg/payload files with `O_RDONLY|O_NOFOLLOW`, drains them to EOF, and reports loaded entry/file/byte totals.
- The command reports `audio.setcal.load.devices_opened=0` and `audio.setcal.load.ioctl_attempted=0`.

## Safety boundary

This is host-only/static behavior. It does not open `/dev/ion`, does not open `/dev/msm_audio_cal`, does not issue `AUDIO_SET_CALIBRATION`, and does not flash or run on-device.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py tests/test_native_audio_setcal_load_api_v2760.py tests/test_native_audio_stage_api_contract_v2756.py tests/test_native_audio_setcal_prepare_api_v2759.py tests/test_native_audio_command_profile_contract_v2751.py` passed.
- `PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_native_audio_*v27*.py'` passed: 113 tests.
- `aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror -Iworkspace/public/src/native-init -c workspace/public/src/native-init/a90_audio.c -o /tmp/a90_audio_v2760.o` passed.
- `/tmp/a90_audio_v2760.o` SHA-256: `1bed4b504618a5ae0175c527f168161bfe944a5482b84cc33e61fe950ddd6240`.
- `git diff --check` passed.
