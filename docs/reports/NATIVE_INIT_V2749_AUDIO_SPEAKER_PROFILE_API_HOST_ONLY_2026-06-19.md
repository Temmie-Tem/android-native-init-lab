# NATIVE_INIT V2749 — Audio Speaker Profile API Host-Only Refactor

Date: 2026-06-19 KST

## Scope

Convert the V2748-proven native speaker path from scattered runner constants into
a reusable host-side profile/API layer. This is a host-only refactor: no flash,
no ADSP boot, no mixer write, no ACDB SET, and no PCM playback were performed.

## Motivation

V2748 proved audible native-init speaker output. The next engineering need is not
another basic playback probe; it is making the proven path callable and maintainable:

- one authoritative place for endpoint/profile metadata;
- one API for global/stream app-type values;
- one API for safe probe/listen amplitude and duration limits;
- one API for observer control allowlists and dmesg/mixer focus patterns;
- a future extension point for additional outputs, such as headphones or a more
  detailed per-speaker profile, without editing the live runner in multiple places.

## Changes

- Added `workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py`.
- Added the `internal-speaker-safe` profile, pinning the V2748 contract:
  - endpoint: `internal-speaker`
  - card/device: `0/0`
  - app type tuple: `1 69941 48000 16`
  - stream app type tuple: `69941 15 48000 2`
  - ACDB SET order: `[39,20,20,13,9,11,12,15,23,16,21]`
  - stale forbidden cal types: `[10,14,24]`
  - listen limit: default `0.15` for `8000 ms`, cap `0.20` / `10000 ms`
  - observer allowlist: 20 focused WSA/speaker/App-Type controls
- Updated `native_audio_acdb_setcal_replay_live_handoff_v2639.py` to expose
  `--audio-profile internal-speaker-safe` and export the selected profile in dry-run
  metadata as `v2749_audio_speaker_profile`.
- Kept runtime behavior unchanged for the default path; the refactor only centralizes
  constants and validation policy.

## Dry-Run Evidence

Dry-run command:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py \
  --dry-run \
  --v2636-manifest workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json \
  --manifest-path workspace/private/builds/audio/v2749-speaker-profile-api/manifest.json
```

Summary from `workspace/private/builds/audio/v2749-speaker-profile-api/dry-run.json`:

- decision: `v2639-setcal-replay-live-handoff-dry-run`
- profile_id: `internal-speaker-safe`
- endpoint: `internal-speaker`
- global_app_type_values: `['1', '69941', '48000', '16']`
- set_order: `[39,20,20,13,9,11,12,15,23,16,21]`
- listen_limits: `0.15/8000 ms`, capped at `0.20/10000 ms`
- observer_controls: `20`
- private_leak: `false`

## Validation

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py \
  tests/test_native_audio_speaker_profiles_v2749.py \
  tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest \
  tests.test_native_audio_speaker_profiles_v2749 \
  tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v
```

Result: 22 tests passed.

## Boundaries

This is not yet an on-device `audio play` command surface. It is the first
host-side API boundary that makes such a command surface practical. Future work
should consume this profile API rather than copying the V2748 constants again.
