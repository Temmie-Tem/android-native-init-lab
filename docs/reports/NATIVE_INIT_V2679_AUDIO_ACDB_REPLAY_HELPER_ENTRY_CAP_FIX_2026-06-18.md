# NATIVE_INIT V2679 — ACDB replay helper entry-cap fix

Date: 2026-06-18

## Scope

Host/helper fix for the V2678 live blocker. V2678 proved the expanded V2677 custom-topology
manifest needs `11` replay entries, but the V2635 native replay helper accepted only `10`.

This unit changes only the helper capacity and host-side planning support:

- no device action;
- no flash;
- no `/dev/msm_audio_cal` ioctl;
- no PCM probe;
- no raw payload publication.

## Result

- decision: `v2679-helper-entry-cap-fixed`
- source change: `A90_MAX_REPLAY_ENTRIES 10 -> 16`
- private helper manifest: `workspace/private/builds/audio/v2679-acdb-setcal-helper-entry-cap/helper-manifest.json`
- private helper SHA-256: `5da19e3127255702f7ef2389d7252b4edf30c59185792f30057aa36a2ca33d18`
- helper max_replay_entries: `16`
- private deploy manifest: `workspace/private/builds/audio/v2679-acdb-custom-topology-replay-deploy-plan/deploy-plan.json`
- private deploy source_helper_manifest: `workspace/private/builds/audio/v2679-acdb-setcal-helper-entry-cap/helper-manifest.json`
- private deploy helper SHA-256: `5da19e3127255702f7ef2389d7252b4edf30c59185792f30057aa36a2ca33d18`
- V2679 replay cal_type order: `[24, 14, 13, 9, 11, 12, 15, 23, 16, 21]`
- V2638 runner-plan with V2679 manifest: `ok=True`, `execution_contract_ok=True`
- V2639 dry-run with V2679 manifest: `ok=True`, `safe_to_run_native_replay=True`
- final expected marker for next live run: `A90_ACDB_SETCAL_SET_OK index=10`

## Why This Fix Is Sufficient For The V2678 Blocker

V2678 failed before any DSP conclusion:

```text
A90_SETCAL_REPLAY_HELPER_EXITED_BEFORE_ALL_SET
invalid --exact-set: /cache/a90-acdb-setcal-replay-v2677/10-set-arg-cal21.bin
```

The helper source had `A90_MAX_REPLAY_ENTRIES 10`. The V2677/V2679 manifest has:

- entry `0`: cal_type `39` basic topology payload;
- entries `1..10`: ten exact SET records.

The cap `16` gives bounded headroom while staying far below any unbounded argument surface. The
same reverse-deallocate logic remains unchanged; V2638 detects the payload-backed entries as
`[0, 1, 2, 5, 7, 9]` for the expanded manifest.

## Private Artifact Hygiene

Raw ACDB arg/payload bytes and the rebuilt helper binary remain under `workspace/private/`.
Only metadata, sizes, order, and SHA-256 values are recorded here.

## Next Unit

Run one self-authorized V2639 live replay using:

```text
workspace/private/builds/audio/v2679-acdb-custom-topology-replay-deploy-plan/deploy-plan.json
```

Expected discriminator:

- If the helper reaches `A90_ACDB_SETCAL_SET_OK index=10`, the V2678 local cap blocker is closed and the run reaches the real DSP/PCM discriminator.
- If playback still fails, classify from dmesg whether the previous ADM/AFE/ASM custom-topology rejection changed.
- Roll back to V2321 and require `selftest fail=0`.

## Validation

- `python3 -m py_compile` on touched V2635/V2677 scripts and tests.
- focused unittest:
  - `tests.test_native_audio_acdb_setcal_replay_helper_gate_v2635`
  - `tests.test_native_audio_acdb_custom_topology_replay_deploy_plan_v2677`
- rebuilt private AArch64 helper with `aarch64-linux-gnu-gcc`.
- generated V2679 deploy manifest with helper override.
- generated V2638 runner-plan with V2679 deploy manifest.
- generated V2639 dry-run with V2679 deploy manifest.
- full `python3 -m unittest discover -s tests -v`.
- `git diff --check`.
