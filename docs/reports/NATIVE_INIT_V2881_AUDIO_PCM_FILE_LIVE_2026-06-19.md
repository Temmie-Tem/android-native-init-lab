# Native Init V2881 Audio PCM-File Live Handoff

## Summary

- Cycle: `V2881`
- Track: active Video playback pipeline; audio file-source validation for A/V bundles.
- Decision: `v2881-audio-pcm-file-live-pass-before-rollback`
- Result directory: `workspace/private/runs/audio/v2881-audio-pcm-file-20260619-203547`
- Candidate tag/version: `v2880-audio-pcm-file` / `0.10.26`
- Candidate image SHA256: `674c7ff223f295be0e53e3fd4636b2dd4f54a6c9615a7b6fa8833951fdf3dc44`
- Rollback attempted: `1`
- Rollback recovery fallback used: `0`
- Rollback health: version_ok=`1` selftest_fail0=`1`

## PCM Fixture

- Local private fixture: `workspace/private/runs/audio/v2881-audio-pcm-file-20260619-203547/fixture/tone.s16le`
- Remote fixture: `/cache/a90-runtime/pkg/audio/v2881/tone.s16le`
- Format: `48000 Hz`, `2` channels, `s16le`
- Duration / amplitude: `1000` ms / `80` milli
- Size / SHA256: `192000` / `ae0e4ecdaa2a456e2e5ea308a8f27cbf7ac5e93c7654e3ba0f8dec7457a87da7`
- Peak absolute sample: `2621`
- Transfer selected/control: `tcpctl` / `tcpctl`
- Remote SHA matched: `1`

## Playback Evidence

- Dry-run stdout: `workspace/private/runs/audio/v2881-audio-pcm-file-20260619-203547/13_candidate-audio-pcm-file-dry-run.txt`
- Execute stdout: `workspace/private/runs/audio/v2881-audio-pcm-file-20260619-203547/14_candidate-audio-pcm-file-execute.txt`
- Worker status done/attempts: `1` / `3`
- Worker status stdout: `workspace/private/runs/audio/v2881-audio-pcm-file-20260619-203547/17_candidate-audio-play-status-03.txt`
- Worker log stdout: `workspace/private/runs/audio/v2881-audio-pcm-file-20260619-203547/18_candidate-audio-pcm-file-worker-log.txt`
- PCM output pass: `1`
- `dry_run_ok`: `1`
- `execute_plan_source_pcm`: `1`
- `execute_plan_waveform_file`: `1`
- `execute_source_pcm`: `1`
- `integrated_done`: `1`
- `integrated_pcm_file`: `1`
- `listen_begin`: `1`
- `listen_end`: `1`
- `pcm_done`: `1`
- `pcm_file_amplitude_within_cap`: `1`
- `pcm_file_supported`: `1`
- `pcm_file_validated`: `1`
- `pcm_path_allowed`: `1`
- `pcm_source_selected`: `1`
- `pcm_write_attempted`: `1`
- `route_apply_ok`: `1`
- `route_reset_ok`: `1`
- `safety_amplitude`: `1`
- `safety_duration`: `1`
- `setcal_all_set`: `1`
- `setcal_deallocated`: `1`
- `worker_done`: `1`
- `worker_pcm_file`: `1`
- `worker_started`: `1`

## Safety

- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.
- Only the boot partition is flashed, then rolled back to `v2321`.
- No host ACDB payload deployment is performed; V2880 uses the bundled `/a90/audio` SET-cal package.
- The raw PCM fixture is generated under `workspace/private` and staged only under `/cache/a90-runtime`.
- Native source validates regular file type, size, seekability, and peak amplitude before ALSA writes.
- No Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path is used.
