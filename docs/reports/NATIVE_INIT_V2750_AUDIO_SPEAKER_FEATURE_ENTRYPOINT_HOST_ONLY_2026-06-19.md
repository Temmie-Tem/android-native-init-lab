# NATIVE_INIT V2750 — Audio Speaker Feature Entrypoint Host-Only Plan

Date: 2026-06-19 KST

## Scope

Add the first clean host-side feature entrypoint for the V2748-proven native
speaker path. This is Tier-A consolidation only: no flash, no ADSP boot, no
mixer write, no ACDB SET, and no PCM playback were performed.

## Result

Added `workspace/public/src/scripts/revalidation/native_audio_speaker_feature_entrypoint_v2750.py`.

The entrypoint consumes the V2749 `internal-speaker-safe` profile and emits a
single staged contract for the feature path:

1. `preflight-v2321-health`
2. `flash-v2334-audio-candidate`
3. `adsp-boot-once`
4. `snd-materialize-once`
5. `install-profile-artifacts`
6. `write-global-app-type-config`
7. `write-stream-app-type-config`
8. `apply-speaker-route`
9. `replay-acdb-setcal-sequence`
10. `bounded-pcm-playback`
11. `capture-dmesg-and-focused-state`
12. `reverse-deallocate`
13. `reverse-route-reset`
14. `rollback-v2321`
15. `post-rollback-selftest`

It also emits the exact legacy V2639 live command needed to execute the current
implementation. This keeps the behavior path unchanged while giving the project
one API/CLI facade to target in later refactors.

## Dry-Run Evidence

Command:

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
python3 workspace/public/src/scripts/revalidation/native_audio_speaker_feature_entrypoint_v2750.py \
  --plan \
  --mode listen
```

Summary from `workspace/private/builds/audio/v2750-speaker-feature-entrypoint/plan.json`:

- decision: `v2750-audio-speaker-feature-entrypoint-plan`
- profile_id: `internal-speaker-safe`
- endpoint: `internal-speaker`
- mode: `listen`
- amplitude: `0.15`
- duration_ms: `8000`
- staged steps: `15`
- delegates_to_v2639: `true`
- native_init_command_surface: `false`
- private_leak: `false`

## Validation

```bash
python3 -m py_compile \
  workspace/public/src/scripts/revalidation/native_audio_speaker_profiles_v2749.py \
  workspace/public/src/scripts/revalidation/native_audio_speaker_feature_entrypoint_v2750.py \
  workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py \
  tests/test_native_audio_speaker_profiles_v2749.py \
  tests/test_native_audio_speaker_feature_entrypoint_v2750.py \
  tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py

PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest \
  tests.test_native_audio_speaker_feature_entrypoint_v2750 \
  tests.test_native_audio_speaker_profiles_v2749 \
  tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v
```

Result: 27 tests passed.

## Boundaries

- This is still host-side orchestration. It is not yet the Tier-B native-init
  `audio status` / `audio route` / `audio play` / `audio stop` command surface.
- Live execution remains delegated to the V2639 runner until a later unit moves
  the replay/playback pieces into native-init or a smaller device-side helper.
- Safety caps remain profile-owned: listen mode defaults to `0.15` for `8000 ms`
  and caps at `0.20` / `10000 ms` until WSA/VI-sense safety telemetry is proven.
