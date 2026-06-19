# Native Init V2861 Audio Screen Matrix Latest Live Validation

## Summary

- Cycle: `V2861`
- Track: post-promotion audio Tier C display/read-only screen matrix.
- Decision: `v2861-audio-status-selftest-device-pass`
- Result directory: `workspace/private/runs/audio/v2861-audio-status-selftest-live-20260619-181237`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2859_audio_changelog_latest_refresh.img`
- Candidate SHA256: `1361e405171cf975d30c7b2c3c64aab145450f7bc866d21e641a60311e56e8b7`
- Candidate version/tag expected: `0.10.19` / `v2859-audio-changelog-latest-refresh`
- Candidate version/tag observed OK: `1`
- `audio status` marker pass: `1` (33/33)
- `selftest verbose` audio marker pass: `1` (8/8)
- `screenapp about-version` marker pass: `1` (6/6)
- `candidate-screenapp-about-changelog` marker pass: `1` (6/6)
- `candidate-screenapp-audio-status` marker pass: `1` (6/6)
- `candidate-screenapp-audio-profile` marker pass: `1` (6/6)
- `candidate-screenapp-audio-stages` marker pass: `1` (6/6)
- `candidate-screenapp-audio-map` marker pass: `1` (6/6)
- `candidate-screenapp-audio-chime` marker pass: `1` (6/6)
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2861 flashes the V2859 `0.10.19` candidate and validates the latest ABOUT/audio screen matrix on hardware.
- The unit covers `about-version`, `about-changelog`, `audio-status`, `audio-profile`, `audio-stages`, `audio-map`, and `audio-chime` through display-only `screenapp` routes.
- This validation intentionally performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, playback, chime, or stop-execute command.

## Missing Markers

- `audio status`: `[]`
- `selftest verbose`: `[]`
- `screenapp about-version`: `[]`
- `candidate-screenapp-about-changelog`: `[]`
- `candidate-screenapp-audio-status`: `[]`
- `candidate-screenapp-audio-profile`: `[]`
- `candidate-screenapp-audio-stages`: `[]`
- `candidate-screenapp-audio-map`: `[]`
- `candidate-screenapp-audio-chime`: `[]`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is written.
- No forbidden partitions are touched.
- Public report contains metadata only; full serial transcripts stay under `workspace/private/runs/audio/`.
