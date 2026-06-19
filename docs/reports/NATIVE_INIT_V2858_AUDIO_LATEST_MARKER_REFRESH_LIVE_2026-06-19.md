# Native Init V2858 Audio Latest Marker Refresh Live Validation

## Summary

- Cycle: `V2858`
- Track: post-promotion audio Tier C productization observability.
- Decision: `v2858-audio-status-selftest-device-pass`
- Result directory: `workspace/private/runs/audio/v2858-audio-status-selftest-live-20260619-173946`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2857_audio_latest_marker_refresh.img`
- Candidate SHA256: `feceae0a52a05193dbe9c1be49767f1ecf82254df55a2bd8fd2ad495766598ad`
- Candidate version/tag expected: `0.10.18` / `v2857-audio-latest-marker-refresh`
- Candidate version/tag observed OK: `1`
- `audio status` marker pass: `1` (33/33)
- `selftest verbose` audio marker pass: `1` (8/8)
- `screenapp audio-status` marker pass: `1` (6/6)
- `screenapp about-changelog` marker pass: `1` (6/6)
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2858 flashes the V2857 `0.10.18` marker-refresh candidate and validates that `audio status` now reports the V2855/V2856 latest-candidate chime/stop evidence.
- The live unit also revalidates the static `selftest verbose` audio row, display-only `screenapp audio-status`, and unchanged `screenapp about-changelog` path.
- This validation intentionally performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, playback, chime, or stop-execute command.

## Missing Markers

- `audio status`: `[]`
- `selftest verbose`: `[]`
- `screenapp audio-status`: `[]`
- `screenapp about-changelog`: `[]`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is written.
- No forbidden partitions are touched.
- Public report contains metadata only; full serial transcripts stay under `workspace/private/runs/audio/`.
