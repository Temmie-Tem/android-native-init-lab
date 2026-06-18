# NATIVE_INIT V2680 — ACDB custom-topology replay live result

Date: 2026-06-18

## Scope

One self-authorized live replay using the V2679 deploy manifest:

```text
workspace/private/builds/audio/v2679-acdb-custom-topology-replay-deploy-plan/deploy-plan.json
```

This stayed inside the recoverable envelope:

- boot-only checked flash to the V2334 audio candidate;
- runtime-only `/dev/msm_audio_cal` replay of captured ACDB SET args/payloads;
- bounded low-amplitude PCM probe;
- reverse-deallocate cleanup;
- runtime directory cleanup;
- rollback to V2321 with `selftest fail=0`.

No forbidden partitions, persistent calibration writes, smart-amp gain changes, or raw payload bytes
were committed.

## Result

- decision: `v2680-custom-topology-replay-reaches-all-set-then-asm-ebadparam`
- private run dir: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-152256`
- runner result: `v2639-acdb-setcal-replay-live-blocked`
- V2678 local blocker: **closed**
  - helper accepted the expanded `11`-entry manifest;
  - reached `A90_SETCAL_REPLAY_ALL_SET_OK pid=862 final_index=10`.
- ACDB replay outcome: **all SET records accepted by `/dev/msm_audio_cal`**
  - `A90_ACDB_SETCAL_SET_OK index=0 cal_type=39`
  - `A90_ACDB_SETCAL_SET_OK index=1 cal_type=24`
  - `A90_ACDB_SETCAL_SET_OK index=2 cal_type=14`
  - `A90_ACDB_SETCAL_SET_OK index=3 cal_type=13`
  - `A90_ACDB_SETCAL_SET_OK index=4 cal_type=9`
  - `A90_ACDB_SETCAL_SET_OK index=5 cal_type=11`
  - `A90_ACDB_SETCAL_SET_OK index=6 cal_type=12`
  - `A90_ACDB_SETCAL_SET_OK index=7 cal_type=15`
  - `A90_ACDB_SETCAL_SET_OK index=8 cal_type=23`
  - `A90_ACDB_SETCAL_SET_OK index=9 cal_type=16`
  - `A90_ACDB_SETCAL_SET_OK index=10 cal_type=21`
- cleanup outcome:
  - reverse deallocate observed for payload-backed entries `0,1,2,5,7,9`;
  - `A90_ACDB_SETCAL_REPLAY_DONE rc=0`;
  - `A90_SETCAL_REPLAY_RUNTIME_CLEANUP_DONE`.
- PCM outcome:
  - probe failed at PCM open with `A90_PCM_PROBE_PCM_OPEN_ERROR`;
  - user-space error: `cannot open device 0 for card 0: Cannot allocate memory`;
  - kernel error: `q6asm_callback: cmd = 0x10dbe returned error = 0x2`;
  - kernel classification: `send_asm_custom_topology: DSP returned error[ADSP_EBADPARAM]`;
  - ALSA platform result: `ASoC: failed to start FE -12`.
- rollback:
  - `rolled_back=True`;
  - `rollback_version_ok=True`;
  - `rollback_selftest_fail0=True`;
  - post-run live check reconfirmed V2321 `version` and `status`.

## Interpretation

V2680 is real progress, not a replay plumbing failure:

1. The V2678 helper-cap blocker is gone.
2. The custom-topology payloads `24` and `14` are now actually replayed before stream open.
3. `/dev/msm_audio_cal` accepts the complete 11-entry sequence, including final cal_type `21`.
4. The remaining blocker moved into DSP validation of the ASM topology:
   `send_asm_custom_topology -> ADSP_EBADPARAM`.

This is narrower than V2648. The previous failure included broader ADM/AFE/ASM symptoms. With the
V2679 custom-topology manifest, the captured failure surfaced specifically at the ASM topology send
for q6asm command `0x10dbe`.

## Evidence

Private evidence remains in:

```text
workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-152256/
```

Key files:

- `62_acdb-setcal-replay-start-wait-all-set.txt` — all staged files verified and final SET marker reached.
- `63_tinyplay-low-amplitude-speaker-pilot.txt` — PCM open failure and exit code `20`.
- `64_dmesg-after-setcal-playback-failure-before-reset.txt` — q6asm `ADSP_EBADPARAM`.
- `65_acdb-setcal-helper-deallocate-check.txt` — reverse deallocate and replay-done markers.
- `79_runtime-dir-cleanup-after-setcal-reset.txt` — runtime cleanup marker.
- `81_rollback-version-attempt-1.txt` — V2321 rollback version.
- `82_rollback-selftest-content-attempt-1-attempt-1.txt` — V2321 `selftest fail=0`.

## Next Unit

Do not rerun the same V2679 manifest blindly. The next useful unit is host/source analysis of the
ASM custom-topology payload and SET argument geometry:

- verify whether cal_type `14` is the exact ASM custom topology block expected by
  `send_asm_custom_topology`;
- compare the captured cal_type `14` arg/payload shape against the kernel q6asm topology command
  expectations;
- check whether ADM custom topology cal_type `10` is still required before ASM despite the current
  capture set lacking it;
- if a manifest change is justified, generate a new deploy manifest and run one bounded replay.

## Validation

- V2679 preflight:
  - rollback images SHA verified for V2321, V2237, and V48.
  - bridge was up on `127.0.0.1:54321`.
  - current V2321 `version`, `status`, and `selftest fail=0` checked before live replay.
- V2680 live:
  - checked helper flashed V2334 candidate;
  - candidate boot and audio materialization completed;
  - all ACDB SET records replayed;
  - PCM probe failed with q6asm `ADSP_EBADPARAM`;
  - cleanup and rollback completed;
  - final V2321 `version`, `status`, and `selftest fail=0` checked.
