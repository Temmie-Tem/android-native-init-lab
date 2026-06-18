# NATIVE_INIT V2722 — corrected core-39 ACDB SET replay live handoff

Date: 2026-06-18

## Scope

Live native-init replay of the V2721 corrected ACDB SET manifest using the
existing V2639 SET-cal replay runner. This unit used the current GOAL correction:
replay byte-exact cal_type 39, real-HAL cal_type 20 headers, and the captured
per-device set; do **not** replay stale cal_type 10/14/24 subsystem custom
payloads.

Device actions stayed inside the recoverable envelope: checked V2334 boot,
ADSP/snd materialization, one-shot `/dev/msm_audio_cal` SET replay, bounded
low-amplitude PCM probe, reverse deallocate/route cleanup, and rollback to V2321.

## Command

```bash
PYTHONPATH=workspace/public/src/scripts/revalidation \
  python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py \
  --run-live \
  --v2636-manifest workspace/private/builds/audio/v2721-audio-acdb-corrected-core39-replay-deploy-plan/deploy-plan.json \
  --manifest-path workspace/private/builds/audio/v2722-corrected-core39-setcal-replay-live-handoff/preflight.json
```

## Result

- decision: `v2639-acdb-setcal-replay-live-blocked`
- public V-iteration decision: `v2722-corrected-core39-setcal-replay-reached-new-frontier`
- runner rc: `1`
- private run dir: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-212439`
- SET replay reached final marker: `A90_SETCAL_REPLAY_ALL_SET_OK pid=856 final_index=10`
- replay order: `[39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21]`
- stale cal_type 10/14/24 replayed: `False`
- PCM probe attempted: `True`
- PCM result: `A90_PCM_PROBE_WRITE_ERROR errno=22 cannot prepare channel`
- reverse deallocate cleanup: `ok=True`
- route reset verification: `ok=True`
- rollback to V2321: `rolled_back=True`, `rollback_version_ok=True`, `rollback_selftest_fail0=True`

## Key Evidence

The corrected manifest changes the failure mode in the expected direction:

- The helper verified every staged SET arg/payload and printed
  `A90_SETCAL_REPLAY_ALL_SET_OK ... final_index=10`, proving all 11 corrected
  SET records were submitted.
- The previous self-inflicted `send_asm_custom_topology` / command `0x10dbe`
  `ADSP_EBADPARAM` signature is absent from the playback-failure dmesg window.
- The playback attempt now reaches the real stream prepare path and fails at a
  different frontier:
  - `__afe_port_start: port id: 0x4000`
  - `afe_callback: cmd = 0x100ef returned error = 0x2`
  - `afe_send_cal_block: AFE cal for port 0x4000 failed -22`
  - `q6asm_callback: cmd = 0x10da1 returned error = 0x12`
  - `q6asm_send_cal: audio audstrm cal send failed`
  - `adm_open:port 0x4000 path:1 rate:48000 mode:1 perf_mode:0,topo_id 0x10004000`
  - `adm_open: DSP returned error[ADSP_EFAILED]`
  - `msm_pcm_playback_prepare: stream reg failed ret:-22`

## Interpretation

V2722 validates the current GOAL correction. Dropping stale 10/14/24 avoids the
old per-subsystem custom-topology `0x10dbe` failure, so the prior ASM custom
payload chase is closed for this path.

The new live frontier is not cal_type 10/14/24. It is the stock-kernel prepare
path after corrected ACDB replay: AFE port `0x4000` calibration is rejected by
DSP (`ADSP_EBADPARAM`), q6asm reports `ADSP_ENEEDMORE`, and ADM open for topology
`0x10004000` still fails. The next useful unit should analyze the real-HAL AFE /
AUDPROC / ASM SET geometry and native replay ordering against this exact dmesg
frontier, not reintroduce subsystem custom topology records.

## Validation

- Re-read `GOAL.md`, `AGENTS.md`, `CLAUDE.md`, and the ACDB operator spec.
- Verified rollback images before live run.
- V2721 manifest passed V2639 deployment-integrity dry-run:
  `execution_contract_ok=True`, `safe_to_run_native_replay=True`, no gate blockers.
- Live run completed cleanup and rollback.
- Final live verification after rollback:
  - `a90ctl.py version` → `0.9.285 (v2321-usb-clean-identity-rodata)`
  - `a90ctl.py selftest verbose` → `fail=0`
