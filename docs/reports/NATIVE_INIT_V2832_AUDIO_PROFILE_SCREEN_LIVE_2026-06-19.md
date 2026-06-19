# Native Init V2832 Audio Profile Screen Live Validation

## Summary

- Cycle: `V2832`
- Track: post-promotion audio Tier C profile observability.
- Decision: `v2832-audio-status-selftest-device-pass`
- Result directory: `workspace/private/runs/audio/v2832-audio-status-selftest-live-20260619-134821`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2831_audio_profile_screen.img`
- Candidate SHA256: `4edcc6bb871e71d6d25713811d956940e950c6ff0ba2d05a0500b13e1d95915c`
- Candidate version/tag observed: `1`
- `audio status` marker pass: `1` (16/16)
- `selftest verbose` audio marker pass: `1` (8/8)
- `screenapp audio-profile` marker pass: `1` (6/6)
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2832 flashes the V2831 `0.10.7` profile-screen candidate and validates that the image boots, preserves `audio status` and `selftest verbose` markers, and renders the display-only `screenapp audio-profile` surface.
- The profile screen exposes compiled profile/stage metadata: profile id, endpoint, PCM tuple, App Type Config tuples, ordered ACDB SET list, and stage counts.
- The validation is intentionally display/KMS only; it performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, or playback.

## Missing Markers

- `audio status`: `[]`
- `selftest verbose`: `[]`
- `screenapp audio-profile`: `[]`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is written.
- No forbidden partitions are touched.
- Public report contains metadata only; full serial transcripts stay under `workspace/private/runs/audio/`.
