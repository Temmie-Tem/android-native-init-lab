# NATIVE_INIT V2759 — Audio SET-cal Prepare Dry-run API

Date: 2026-06-19  
Scope: host-only implementation and static validation  
Device action: none  
Raw payloads: not committed; private ACDB bytes remain under `workspace/private/`

## Goal

Advance the V2758 manifest verifier into an execution-adjacent prepare boundary
without crossing into `/dev/ion` or `/dev/msm_audio_cal`.  The native command now
has a callable stage that verifies the private SET bundle and reports the exact
arg/payload byte plan that a later SET executor must load.

## Changes

- Added `audio setcal <profile> --manifest <path> --prepare --dry-run`.
- Added staged contract entry `prepare-acdb-payload-bundle` between:
  - `verify-private-acdb-manifest`
  - `replay-acdb-setcal-sequence`
- Extended the native manifest parser to accumulate:
  - entry count
  - arg entry count
  - payload entry count
  - total arg bytes
  - total payload bytes
- `--prepare` includes manifest verification and then emits:
  - `audio.setcal.prepare.entry.count`
  - `audio.setcal.prepare.arg_entries`
  - `audio.setcal.prepare.payload_entries`
  - `audio.setcal.prepare.arg_bytes`
  - `audio.setcal.prepare.payload_bytes`
  - `audio.setcal.prepare.devices_opened=0`
  - `audio.setcal.prepare.ioctl_attempted=0`
  - `audio.setcal.prepare_ok=1`

## Safety Boundary

- `--prepare` opens only the manifest and declared regular files for SHA-256
  verification.
- It does not open `/dev/ion`, `/dev/msm_audio_cal`, or ALSA control/PCM nodes.
- It issues no audio calibration ioctl and keeps `ioctl_attempted=0`.
- `--execute` remains blocked with
  `execute-not-implemented-native-setcal-ioctl`.
- No raw ACDB bytes, compiled helpers, boot images, or private payloads are
  committed.

## Host Validation

Commands:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py \
  tests/test_native_audio_stage_api_contract_v2756.py \
  tests/test_native_audio_setcal_manifest_command_v2757.py \
  tests/test_native_audio_setcal_prepare_api_v2759.py \
  tests/test_native_audio_command_profile_contract_v2751.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_stage_api_contract_v2756 \
  tests.test_native_audio_setcal_manifest_command_v2757 \
  tests.test_native_audio_setcal_prepare_api_v2759 \
  tests.test_native_audio_command_profile_contract_v2751

aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror \
  -Iworkspace/public/src/native-init \
  -c workspace/public/src/native-init/a90_audio.c \
  -o /tmp/a90_audio_v2759.o
```

Results:

- Focused tests: 20 passed.
- `a90_audio.c` object SHA-256:
  `16dc2b9083aae30f42ef28daff52834ac152c7dc38f57f325d62298f6de76bd9`.
- `git diff --check`: passed.

## Next Boundary

The next meaningful unit is the first native SET executor scaffold behind the
same manifest contract.  It should still default to refusal unless explicitly
compiled/selected, then add file loading and `/dev/ion` allocation before any
`AUDIO_SET_CALIBRATION` ioctl is enabled.
