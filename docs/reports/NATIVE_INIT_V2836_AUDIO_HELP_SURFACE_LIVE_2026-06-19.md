# Native Init V2836 Audio Help Surface Live Validation

## Summary

- Cycle: `V2836`
- Track: post-promotion audio Tier C help/discoverability observability.
- Decision: `v2836-audio-status-selftest-device-pass`
- Result directory: `workspace/private/runs/audio/v2836-audio-status-selftest-live-20260619-142643`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2835_audio_help_surface.img`
- Candidate SHA256: `53ef5d1155b7833dcb05d6ecc6d9dfabfd336b9c66f695b1aa789eb9e5ba6aca`
- Candidate version/tag expected: `0.10.9` / `v2835-audio-help-surface`
- Candidate version/tag observed OK: `1`
- `audio status` marker pass: `1` (16/16)
- `selftest verbose` audio marker pass: `1` (8/8)
- `help` audio usage marker pass: `1` (1/1)
- `cmdmeta verbose` audio usage marker pass: `1` (2/2)
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2836 flashes the V2835 `0.10.9` help-surface candidate and validates that the image boots, preserves `audio status` and `selftest verbose` markers, and exposes the current audio subcommands in both `help` and `cmdmeta verbose`.
- The validation is read-only: it performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, or playback.

## Missing Markers

- `audio status`: `[]`
- `selftest verbose`: `[]`
- `help`: `[]`
- `cmdmeta verbose`: `[]`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is written.
- No forbidden partitions are touched.
- Public report contains metadata only; full serial transcripts stay under `workspace/private/runs/audio/`.
