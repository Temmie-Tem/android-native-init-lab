# NATIVE_INIT V2758 — Audio SET-cal Private Manifest Verify Boundary

Date: 2026-06-19  
Scope: host-only implementation and static validation  
Device action: none  
Raw payloads: not committed; private ACDB bytes remain under `workspace/private/`

## Goal

Turn the proven speaker SET-cal replay inputs into a callable native-init boundary
without yet implementing `/dev/msm_audio_cal` SET replay.  The immediate product
need is an API-like function that can verify the private SET arg/payload bundle by
path, size, and SHA-256 before any runtime audio calibration ioctl is attempted.

## Changes

- Added native `audio setcal <profile> --manifest <path> --verify --dry-run`.
- Added the stage `verify-private-acdb-manifest` before the still-blocked
  `replay-acdb-setcal-sequence` stage.
- Added a line-oriented private manifest schema:
  - `version 1`
  - `profile internal-speaker-safe`
  - `entry_count 11`
  - `entry <seq> <cal_type> <role> <dmabuf_expected> <arg_path> <arg_size> <arg_sha256> <payload_path> <payload_size> <payload_sha256>`
- Added `native_audio_setcal_payload_manifest_v2758.py` to generate the private
  manifest from the V2725 deploy plan while emitting only remote runtime paths,
  sizes, and SHA-256 metadata.
- Exported the existing native-init SHA-256 file verifier as
  `a90_helper_sha256_file()` instead of duplicating hash code.

## Safety Boundary

- `audio.setcal.ioctl_attempted=0` remains invariant for verify and execute
  refusal paths.
- `--execute` still returns `-EPERM` with
  `execute-not-implemented-native-setcal-ioctl`.
- Manifest path is limited to `/cache/a90-runtime`.
- Payload paths are limited to `/cache/a90-runtime` or the legacy replay cache
  prefix `/cache/a90-acdb-setcal-replay-`.
- `..` path components are rejected.
- The verifier uses `O_NOFOLLOW` and regular-file `lstat()` checks before hashing.
- No raw ACDB bytes, compiled helpers, boot images, or private paths are committed.

## Host Validation

Commands:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py \
  workspace/public/src/scripts/revalidation/native_audio_setcal_payload_manifest_v2758.py \
  tests/test_native_audio_setcal_private_manifest_v2758.py \
  tests/test_native_audio_setcal_manifest_command_v2757.py \
  tests/test_native_audio_stage_api_contract_v2756.py \
  tests/test_native_audio_command_profile_contract_v2751.py

PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_native_audio_*v275*.py'

aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror \
  -Iworkspace/public/src/native-init \
  -c workspace/public/src/native-init/a90_audio.c \
  -o /tmp/a90_audio_v2758.o

aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror \
  -Iworkspace/public/src/native-init \
  -c workspace/public/src/native-init/a90_helper.c \
  -o /tmp/a90_helper_v2758.o
```

Results:

- Unit tests: 44 passed.
- `a90_audio.c` object SHA-256:
  `9c948a332641179b5bbacaf9f8a1fdc758e553203682b7dbb0f0ab7dbc597eca`.
- `a90_helper.c` object SHA-256:
  `e4e08b0aac529c7d0249f36280730bb9e3b65ecedeff4a749f4ba9add68a17fb`.
- Real private V2725 deploy-plan conversion to `/tmp` produced 11 entries with
  replay order `39,20,20,13,9,11,12,15,23,16,21` and no local private paths.

## Next Boundary

The next meaningful unit is the native SET replay executor behind the already
verified manifest.  It should keep the same manifest contract, preserve the
`ioctl_attempted=0` refusal until the executor is compiled in, and implement
payload loading before touching `/dev/ion` or `/dev/msm_audio_cal`.
