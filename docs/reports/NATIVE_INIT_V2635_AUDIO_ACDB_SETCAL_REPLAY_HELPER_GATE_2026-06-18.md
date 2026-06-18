# NATIVE_INIT V2635 — ACDB exact SET-cal replay helper gate

Date: 2026-06-18

## Scope

Host-only build gate for the future native ACDB replay helper. This unit
builds a private AArch64 helper capable of mixed replay: topology as a
basic payload packet, and V2633 SET-layer records as exact SET-argument
bytes with fresh dmabuf handle patching only for payload-backed records.

No device action, flash, `/dev/msm_audio_cal` ioctl, PCM probe, or raw
payload publication occurred.

## Result

- decision: `v2635-setcal-replay-helper-gate-ready`
- ok: `True`
- source_v2634_manifest: `workspace/private/builds/audio/v2634-audio-acdb-setcal-replay-gate/setcal-replay-gate-manifest.json`
- source_v2634_ready: `True`
- future_entry_count: `9`
- native_replay_ready: `False`
- safe_to_run_native_replay: `False`

## Helper

- source: `workspace/public/src/native-init/helpers/a90_acdb_setcal_replay_scaffold_v2635.c`
- built: `True`
- private_tool: `workspace/private/builds/audio/v2635-audio-acdb-setcal-replay-helper-gate/bin/a90_acdb_setcal_replay_execute_v2635`
- private_tool_sha256: `d1f061a8c0ab2df011d98cd0c4539d7a809e757cdce2c3b73f0ccdeba634b4bf`
- private_tool_file: `workspace/private/builds/audio/v2635-audio-acdb-setcal-replay-helper-gate/bin/a90_acdb_setcal_replay_execute_v2635: ELF 64-bit LSB executable, ARM aarch64, version 1 (GNU/Linux), statically linked, BuildID[sha1]=9162939d57360ae9964a75a8a392a278fce8d3b7, for GNU/Linux 3.7.0, stripped`

## Contract

- `--basic-payload CAL_TYPE:BUFFER:PAYLOAD` supports the operator-verified topology payload.
- `--exact-set ARG` replays header-only SET records exactly.
- `--exact-set ARG:PAYLOAD` allocates a fresh ION dmabuf, copies the payload, patches `mem_handle`, then sends the captured SET arg.
- Payload-backed records are deallocated in reverse order; header-only records are not deallocated.
- The helper keeps `/dev/msm_audio_cal` and all payload fds open across the future bounded PCM probe window.

## Gate

- V2635 removes the local helper-format blocker from V2634.
- Native replay remains blocked until operator Gate-2 accepts the V2633/V2634 SET-layer package.
- Future live replay requires a separate checked runner, staged hash verification, bounded PCM probe, reverse cleanup, and V2321 rollback health.

## Validation

- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_helper_gate_v2635.py tests/test_native_audio_acdb_setcal_replay_helper_gate_v2635.py`
- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_helper_gate_v2635 -v`
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_helper_gate_v2635.py --build-helper --write-report`
- `git diff --check`
