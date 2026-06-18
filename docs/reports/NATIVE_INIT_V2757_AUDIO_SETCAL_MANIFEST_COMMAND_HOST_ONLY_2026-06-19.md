# NATIVE_INIT V2757 — Audio SETCAL Manifest Command (Host-only)

## Decision

`v2757-audio-setcal-manifest-command-host-only`

The native-init `audio` surface now has a read-only ACDB SET replay manifest API:
`audio setcal [profile] [--dry-run|--execute]`.

This is **not** ACDB replay execution.  It performs no device action, no flash,
no `/dev/msm_audio_cal` open, no `/dev/ion` open, no `AUDIO_SET_CALIBRATION`,
no mixer write, and no PCM playback.

## Why

V2756 made the speaker path inspectable as ordered stages, but the ACDB replay
stage still pointed at a private helper.  Raw SET args and dma-buf payloads must
remain private and cannot be committed into native-init source.  The safe next
step is therefore to commit the public replay **contract** into the native command
surface first:

- the corrected replay order
- the per-entry role labels
- which entries require private dma-buf payload bytes
- forbidden stale cal types
- explicit refusal of execute mode

This creates a stable API boundary for the later private payload loader/executor.

## Native API

Command:

```text
audio setcal [profile] [--dry-run|--execute]
```

Dry-run output includes:

- `audio.setcal.replay_order=39,20,20,13,9,11,12,15,23,16,21`
- `audio.setcal.forbidden_stale_cal_types=10,14,24`
- `audio.setcal.entry.N.cal_type`
- `audio.setcal.entry.N.role`
- `audio.setcal.entry.N.dmabuf_expected`
- `audio.setcal.private_payloads_required=1`
- `audio.setcal.execute_supported=0`
- `audio.setcal.ioctl_attempted=0`

`--execute` is parsed but explicitly refused with:

```text
audio.setcal.refused=execute-not-implemented-native-manifest-only
audio.setcal.ioctl_attempted=0
```

## Manifest Entries

| Seq | Cal type | Role | dmabuf expected |
| ---: | ---: | --- | ---: |
| 0 | 39 | `CORE_CUSTOM_TOPOLOGIES_BYTE_EXACT_SET` | 1 |
| 1 | 20 | `AFE_FB_SPKR_PROT_HEADER_REAL_HAL_1` | 0 |
| 2 | 20 | `AFE_FB_SPKR_PROT_HEADER_REAL_HAL_2` | 0 |
| 3 | 13 | `APP_META_HEADER` | 0 |
| 4 | 9 | `AFE_TOPOLOGY_HEADER` | 0 |
| 5 | 11 | `AUDPROC_COMMON_PAYLOAD` | 1 |
| 6 | 12 | `VOL_HEADER_NO_PAYLOAD` | 0 |
| 7 | 15 | `ASM_STREAM_PAYLOAD` | 1 |
| 8 | 23 | `AFE_TOPOLOGY_ID_HEADER` | 0 |
| 9 | 16 | `AFE_COMMON_PAYLOAD` | 1 |
| 10 | 21 | `SPEAKER_VI_HEADER` | 0 |

## Safety

- `audio setcal --dry-run` is metadata-only.
- `audio setcal --execute` is refused before any ioctl.
- The command does not reference private paths or raw payload bytes.
- Stale subsystem-topology cal types `10/14/24` remain explicitly forbidden.
- Stage API now points `replay-acdb-setcal-sequence` to `audio setcal <profile> --dry-run`, while keeping the full stage marked `native_implemented=false`.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py \
  tests/test_native_audio_setcal_manifest_command_v2757.py \
  tests/test_native_audio_stage_api_contract_v2756.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_setcal_manifest_command_v2757 \
  tests.test_native_audio_stage_api_contract_v2756 \
  tests.test_native_audio_command_profile_contract_v2751 \
  tests.test_native_audio_speaker_profiles_v2749

aarch64-linux-gnu-gcc -std=gnu99 -Wall -Wextra -Werror \
  -fsyntax-only -I workspace/public/src/native-init \
  workspace/public/src/native-init/a90_audio.c
```

Results:

- `py_compile`: pass
- focused tests: `20` tests OK
- native C syntax-only cross-check: pass

## Next

The next meaningful unit is a private-payload boundary design for native-init:
how `audio setcal --execute` would safely locate, validate, hash-check, load, and
replay private SET args/payloads without committing raw bytes or proprietary
artifacts.  Execution must remain blocked until that loader contract exists and
is tested.
