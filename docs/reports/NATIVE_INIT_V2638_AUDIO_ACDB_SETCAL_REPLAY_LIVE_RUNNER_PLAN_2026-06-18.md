# NATIVE_INIT V2638 — ACDB SET-cal replay live runner plan

Date: 2026-06-18

## Scope

Host-only conversion of the V2636 exact SET-cal deployment manifest into a
future checked live-runner contract. This unit does not stage files, flash,
issue calibration ioctls, or run PCM playback.

## Result

- decision: `v2638-setcal-replay-live-runner-plan-gate-satisfied`
- ok: `True`
- execution_contract_ok: `True`
- private_manifest: `workspace/private/builds/audio/v2638-audio-acdb-setcal-replay-live-runner-plan/runner-plan.json`
- source_v2636_manifest: `workspace/private/builds/audio/v2636-audio-acdb-setcal-replay-deploy-plan/deploy-plan.json`
- safe_to_run_native_replay: `True`
- native_replay_ready: `True`

## Replay Contract

- remote_dir: `/cache/a90-acdb-setcal-replay-v2636`
- remote_file_count: `13`
- replay_entry_count: `9`
- final_set_index: `8`
- final_set_marker: `A90_ACDB_SETCAL_SET_OK index=8`
- payload_entry_indices_requiring_deallocate: `[0, 3, 5, 7]`
- remote_script_paths: `{'start_and_wait_all_set': '/cache/a90-runtime/bin/v2639-setcal-replay-scripts/setcal-start-and-wait-all-set.sh', 'deallocate_check': '/cache/a90-runtime/bin/v2639-setcal-replay-scripts/setcal-deallocate-check.sh', 'runtime_cleanup': '/cache/a90-runtime/bin/v2639-setcal-replay-scripts/setcal-runtime-cleanup.sh'}`
- route_apply_count: `13`
- route_reset_count: `12`
- app_type_gate_enabled: `True`
- pcm_probe: `['/cache/a90-runtime/bin/v2379-speaker-pilot/a90_pcm_write_probe_v2386', '/cache/a90-runtime/bin/v2379-speaker-pilot/pilot_48k_s16le_stereo_0p02_1s.wav', '-D', '0', '-d', '0']`

## Gate Blockers


## Future Live Sequence

- verify rollback V2321 and current selftest fail=0
- flash V2334 audio candidate through checked helper and verify health
- boot ADSP and materialize /dev/snd nodes
- stage 13 V2636 replay files plus tinymix, PCM probe, and generated low-amplitude WAV
- stage long replay shell scripts as files and run only short shell commands
- verify all staged ACDB file SHA-256 values on device
- take tinymix baseline snapshot
- apply V2407 App Type and V2377 route controls
- start V2635 exact SET replay helper in background and wait for final SET index 8
- run bounded PCM probe during helper hold window
- wait for replay done and reverse deallocation markers
- reverse-reset route controls and verify reset against baseline
- cleanup runtime dir and rollback to V2321

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py tests/test_native_audio_acdb_setcal_replay_live_runner_plan_v2638.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_runner_plan_v2638 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py --write-report`
- `git diff --check`
