# NATIVE_INIT V2639/V2730 — ACDB SET-cal replay live handoff

Date: 2026-06-18

## Scope

Checked live handoff for native replay of the V2636 SET-cal manifest.
Default validation is host-only. Live mode is self-authorized under the
recoverable envelope and is gated by deployment integrity plus the
operational invariants: one-shot exact SET args, bounded PCM probe,
reverse-deallocate cleanup, dmesg instrumentation, and rollback to V2321.

## Result

- decision: `v2639-setcal-replay-live-handoff-dry-run`
- execution_contract_ok: `True`
- safe_to_run_native_replay: `True`
- live_runner_implemented: `True`
- manifest_path: `workspace/private/builds/audio/v2733-setcal-replay-atomic-appcfg-dry-run/manifest.json`
- global_app_type_config: `{'enabled': True, 'name': 'v2733-atomic-app-type-config', 'role': 'global_app_type_cfg_gate', 'source': 'V2732 write-semantics recon', 'control': 'App Type Config', 'values': ['1', '69941', '48000', '16'], 'entry': '69941:48000:16', 'writer': 'atomic-alsa-elem-write', 'argv': ['/cache/a90-runtime/bin/v2379-speaker-pilot/a90_alsa_app_type_config_writer_v2733', '--card', '0', '--control', 'App Type Config', '--entry', '69941:48000:16'], 'expected_effect': 'adm_open bit_width 0->16 and no app-type fallback for app_type 0x11135', 'transport': 'serial-cmdv1x'}`
- dmesg_focus_pattern: `q6core|register_topolog|map_memory|avcs|adsp.*ready|adm_open|app type|bit_width|msm_pcm_routing|get_app_type|send_afe_cal|q6asm|AFE_PORT|ASM`

## V2730 Update

V2730 updates the existing V2639 runner for the current GOAL frontier:

- writes the global `App Type Config` mixer control via serial before the
  older per-stream `Audio Stream 0 App Type Cfg` and route controls;
- uses the speaker tuple `1 69941 48000 16`, targeting the kernel
  `app_type_cfg[]` table rather than `fe_dai_app_type_cfg[]`;
- V2733 replaces the old `tinymix` write with an atomic ALSA elem writer
  because V2732 showed `tinymix` performs per-index integer writes;
- captures focused dmesg greps for `q6core`, topology-registration,
  `adm_open`, app-type fallback, and `bit_width` before and after the PCM probe;
- keeps the replay manifest, exact SET bytes, bounded PCM probe, reverse
  deallocate cleanup, route reset, and V2321 rollback contract unchanged.

## Gate Blockers


## Future Live Sequence

- verify rollback V2321 and current selftest fail=0
- flash V2334 audio candidate through checked helper and verify health
- boot ADSP and materialize /dev/snd nodes
- stage the ACDB replay manifest files plus tinymix, PCM probe, and generated low-amplitude WAV
- stage long replay shell scripts as files and run only short shell commands
- verify all staged ACDB file SHA-256 values on device
- take tinymix baseline snapshot
- write global App Type Config atomically as 1 69941 48000 16, then apply V2407 stream App Type and V2377 route controls
- start V2635 exact SET replay helper in background and wait for final SET index 8
- run bounded PCM probe during helper hold window
- wait for replay done and reverse deallocation markers
- reverse-reset route controls and verify reset against baseline
- cleanup runtime dir and rollback to V2321

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --dry-run --write-report`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --run-live` deployment-integrity gate check
- `git diff --check`
