# NATIVE_INIT V2756 — Audio Stage API Contract (Host-only)

## Decision

`v2756-audio-stage-api-contract-host-only`

The V2748/V2639 audible speaker path is now exposed as an ordered stage contract
in both the host-side speaker profile API and the native-init `audio` command
surface.  This is a read-only/API-shaping unit: no device action, no flash, no
ACDB SET, no mixer write, and no PCM playback were performed.

## Why

The audio proof path is now viable, but the implementation must stop growing as
one-off runner glue.  The next productization step is to make each functional
piece callable and inspectable before promoting more live write commands:

1. profile selection
2. ADSP bring-up
3. `/dev/snd` materialization
4. global App-Type Config
5. ACDB SET replay
6. core speaker route apply/reset
7. bounded PCM playback
8. rollback boundary

V2756 records that as a versioned API contract and explicitly marks which stages
are already native-init implemented versus still private-helper/planned.

## Changes

- Host profile API:
  - Added `AudioFeatureStage`.
  - Added `staged_contract()` and `stage_manifests(profile_id)`.
  - Embedded `staged_contract` and `stage_api` into `profile_manifest()`.
- Host entrypoint:
  - Replaced its local staged-contract list with the shared profile API.
  - Exposes `stage_api` in the generated plan.
- Native init:
  - Added read-only `audio stages [profile]`.
  - Prints stage id/order/owner/phase/command/speaker scope.
  - Prints `native_implemented`, `writes_runtime_state`, and rollback boundary flags.
  - Keeps `audio.stages.all_native_ready=0` because ACDB replay and PCM playback are not yet first-class native commands.

## Stage Summary

| Stage | Owner | Native now? | Runtime write? | Notes |
| --- | --- | ---: | ---: | --- |
| `preflight-v2321-health` | host | no | no | rollback health checkpoint |
| `adsp-boot-once` | native-init | yes | yes | bounded one-shot ADSP boot |
| `snd-materialize-once` | native-init | yes | yes | ALSA devnode materialization |
| `write-global-app-type-config` | native-init | yes | yes | V2735 app-type tuple |
| `replay-acdb-setcal-sequence` | private-helper | no | yes | next target for native API |
| `apply-core-speaker-route` | native-init | yes | yes | core layer only |
| `bounded-pcm-playback` | native-init | no | yes | planned `audio play` API |
| `reset-core-speaker-route` | native-init | yes | yes | reverse core reset |
| `rollback-v2321` | host | no | yes | checked boot rollback |

## Safety

- `audio stages` is read-only.
- No new live write path was introduced.
- Smart-amp boost remains blocked by the route policy.
- Amplitude and duration caps stay profile-owned.
- ACDB SET replay and PCM playback are marked not native-ready, preventing accidental claims that the native command surface is complete.

## Validation

Commands run:

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py \
  workspace/public/src/scripts/revalidation/native_audio_speaker_feature_entrypoint_v2750.py \
  tests/test_native_audio_stage_api_contract_v2756.py

PYTHONPATH=tests python3 -m unittest \
  tests.test_native_audio_speaker_profiles_v2749 \
  tests.test_native_audio_speaker_feature_entrypoint_v2750 \
  tests.test_native_audio_command_profile_contract_v2751 \
  tests.test_native_audio_stage_api_contract_v2756

python3 -m unittest discover -s tests -p 'test_native_audio_*v275*.py'

aarch64-linux-gnu-gcc -std=gnu99 -Wall -Wextra -Werror \
  -fsyntax-only -I workspace/public/src/native-init \
  workspace/public/src/native-init/a90_audio.c
```

Results:

- `py_compile`: pass
- focused unit tests: `20` tests OK
- V275x audio test subset: `35` tests OK
- native C syntax-only cross-check: pass

## Next

1. Move ACDB SET replay from the private scaffold into a native-init callable stage.
2. Add `audio play <profile>` with bounded tone generation and profile-owned amplitude caps.
3. Add `audio stop <profile>` to consolidate reverse-deallocate and route reset.
4. Only after those APIs exist, build/flash a new test image and run a bounded live validation.
