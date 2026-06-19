# Native Init V2827 Audio Menu Screens Live Validation

## Summary

- Cycle: `V2827`
- Track: post-promotion audio Tier C menu/screen observability.
- Decision: `v2827-audio-status-selftest-device-pass`
- Result directory: `workspace/private/runs/audio/v2827-audio-status-selftest-live-20260619-130418`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v2826_audio_menu_screens.img`
- Candidate SHA256: `0662749d76651d50db837685b7778aedbbe83cc7071d16c703ea060e9e9d47a6`
- Candidate version/tag observed: `1`
- `audio status` marker pass: `1` (16/16)
- `selftest verbose` audio marker pass: `1` (8/8)
- `screenapp audio-map` marker pass: `1` (6/6)
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## Finding

- V2827 flashes the V2826 `0.10.5` APPS/AUDIO menu candidate and validates that the image boots, exposes `audio status`, and still renders the display-only audio route-map screen.
- V2826 source tests cover the APPS/AUDIO touch-menu wiring (`AUDIO STATUS` and `ROUTE MAP` actions). This live run checks the candidate image and renderer on hardware after that menu surface was added.
- The screenapp validation is intentionally display/KMS only; it performs no ADSP boot, `/dev/snd` materialization, route apply/reset, ACDB SET, PCM open, mixer write, speaker write, or playback.

## Missing Markers

- `audio status`: `[]`
- `selftest verbose`: `[]`
- `screenapp audio-map`: `[]`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is written.
- No forbidden partitions are touched.
- Public report contains metadata only; full serial transcripts stay under `workspace/private/runs/audio/`.
