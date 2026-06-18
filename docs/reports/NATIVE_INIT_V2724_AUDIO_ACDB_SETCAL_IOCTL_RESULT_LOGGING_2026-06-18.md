# V2724 — ACDB SET replay ioctl-result instrumentation

Date: 2026-06-18  
Scope: host-only helper/runner instrumentation  
Device action: none  
Flash action: none

## Decision

`v2724-setcal-ioctl-result-instrumentation-ready`

V2724 adds the missing diagnostic split for the corrected ACDB SET replay path:

1. The SET replay helper now emits one uniform result marker for every calibration ioctl it issues:
   `A90_ACDB_SETCAL_IOCTL_RESULT name=<...> request=<...> rc=<...> errno=<...> cal_type=<...> ...`.
2. The V2639 live runner now captures a bounded dmesg tail immediately after SET replay reaches the final SET marker and before the PCM probe starts.

This prepares the next live run to distinguish:

- kernel ioctl acceptance/rejection during `AUDIO_ALLOCATE_CALIBRATION` / `AUDIO_SET_CALIBRATION` / cleanup;
- DSP-side failures that appear only when `pcm_prepare()` starts the AFE/q6asm/ADM path.

## Changes

- `workspace/public/src/native-init/helpers/a90_acdb_setcal_replay_scaffold_v2635.c`
  - Added `A90_ACDB_SETCAL_IOCTL_RESULT` after each calibration ioctl.
  - Preserves existing success/failure text and `A90_ACDB_SETCAL_SET_OK` compatibility markers.
- `workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_helper_gate_v2635.py`
  - Adds source/static string checks for the uniform ioctl result marker.
  - Records `logs_uniform_ioctl_results=true` in the helper contract.
- `workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py`
  - Adds `dmesg-after-setcal-replay-before-pcm` after final SET marker and before playback/probe.
  - Records the artifact as `post_set_dmesg` in future live results.
- `tests/test_native_audio_acdb_setcal_replay_helper_gate_v2635.py`
  - Asserts the new source token and helper contract.
- `tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
  - Asserts the pre-PCM dmesg capture exists and occurs before playback is marked attempted.

## Private build verification

Private helper build root:

`workspace/private/builds/audio/v2724-acdb-setcal-helper-ioctl-result/`

Private helper artifact:

`workspace/private/builds/audio/v2724-acdb-setcal-helper-ioctl-result/bin/a90_acdb_setcal_replay_execute_v2635`

Artifact metadata:

- SHA256: `aa9160278a344b706ef644fb1b27b5af39e58553697bbfc4a39f2635282c7751`
- Size: `663472`
- File type: `ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped`
- Private only: yes; not committed

Static probe from the private build manifest:

- `strings_has_start_marker=true`
- `strings_has_set_marker=true`
- `strings_has_ioctl_result_marker=true`
- `strings_has_exact_set_format=true`
- `strings_has_basic_payload_format=true`

Manual string check also found:

- `A90_ACDB_SETCAL_IOCTL_RESULT name=%s request=0x%lx rc=%d errno=%d strerror=%s cal_type=%d buffer=%d cal_size=%d mem_handle=%d arg_len=%zu`
- `A90_ACDB_SETCAL_SET_OK index=%zu cal_type=%d kind=%d has_payload=%d`

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_helper_gate_v2635.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py \
  tests/test_native_audio_acdb_setcal_replay_helper_gate_v2635.py \
  tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest \
  tests.test_native_audio_acdb_setcal_replay_helper_gate_v2635 \
  tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v

PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_helper_gate_v2635.py \
  --build-helper \
  --build-root workspace/private/builds/audio/v2724-acdb-setcal-helper-ioctl-result \
  --manifest-path workspace/private/builds/audio/v2724-acdb-setcal-helper-ioctl-result/helper-manifest.json \
  --report workspace/private/builds/audio/v2724-acdb-setcal-helper-ioctl-result/helper-report-v2635.md \
  --write-report

file workspace/private/builds/audio/v2724-acdb-setcal-helper-ioctl-result/bin/a90_acdb_setcal_replay_execute_v2635
strings workspace/private/builds/audio/v2724-acdb-setcal-helper-ioctl-result/bin/a90_acdb_setcal_replay_execute_v2635 | rg 'A90_ACDB_SETCAL_IOCTL_RESULT|A90_ACDB_SETCAL_SET_OK'
```

Results:

- `py_compile`: pass
- focused unittest: `10` tests pass
- private AArch64 helper build: pass
- `file`: pass, AArch64 static stripped executable
- `strings` marker check: pass

## Next unit

Build a fresh corrected replay deploy plan that points to the V2724 private helper artifact, then run one bounded live replay. Acceptance for the next live run is not “sound”; it is classification of the SET/PCM boundary using:

- per-ioctl `A90_ACDB_SETCAL_IOCTL_RESULT` markers;
- `post_set_dmesg` before PCM prepare;
- existing playback-failure dmesg after PCM prepare;
- rollback to V2321 with `selftest fail=0`.
