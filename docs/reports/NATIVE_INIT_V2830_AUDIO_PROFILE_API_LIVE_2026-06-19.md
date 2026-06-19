# Native Init V2830 Audio Profile API Live Validation

## Summary

- Cycle: `V2830`
- Track: post-promotion audio Tier C read-only command API validation.
- Decision: `v2830-audio-profile-api-device-pass`
- Result directory: `workspace/private/runs/audio/v2830-audio-profile-api-live-20260619-133305`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2828_audio_route_map_safety.img`
- Candidate SHA256: `f7ad559ec519c7c9d8f537d3549ec4699dac911900ae5cb972ae50681133d69f`
- Candidate version/tag observed: `1`
- `audio-profiles` marker pass: `1` (4/4)
- `audio-profile` marker pass: `1` (21/21)
- `audio-stages` marker pass: `1` (17/17)
- `audio-speaker-map` marker pass: `1` (19/19)
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2830 flashes the latest `0.10.6` audio observability candidate and validates the read-only profile API on hardware.
- The run proves the callable native API surfaces expose the canonical internal-speaker profile, stage contract, and per-speaker route map without issuing audio runtime writes.
- This validation intentionally performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, or playback.

## Missing Markers

- `audio-profiles`: `[]`
- `audio-profile`: `[]`
- `audio-stages`: `[]`
- `audio-speaker-map`: `[]`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is written.
- No forbidden partitions are touched.
- Public report contains metadata only; full serial transcripts stay under `workspace/private/runs/audio/`.
