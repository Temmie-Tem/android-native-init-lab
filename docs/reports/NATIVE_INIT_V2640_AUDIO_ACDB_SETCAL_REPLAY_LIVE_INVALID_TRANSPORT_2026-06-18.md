# NATIVE_INIT V2640 — ACDB SET-cal replay live invalid transport result

Date: 2026-06-18

## Scope

Live execution of the V2639 ACDB SET-cal native replay runner after the 2026-06-18
GOAL policy update removed the manual approval/Gate-2 blockers.

The device step stayed inside the recoverable envelope: boot-only candidate flash,
runtime ACDB/route/PCM actions, route reset attempt, runtime cleanup, and checked
rollback to V2321.

## Result

- decision: `v2639-acdb-setcal-replay-live-blocked`
- classification: `invalid-live-run-start-script-transport-corruption`
- private_run_dir: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-095645`
- candidate rollback: `rolled_back=True`
- rollback version: `rollback_version_ok=True`
- rollback selftest: `rollback_selftest_fail0=True`
- post-run host health check: V2321 `0.9.285`, `selftest fail=0`

## Key Finding

The run did not validly test ACDB SET replay. The generated remote
`start_and_wait_all_set` shell body was too large for the serial `cmdv1x` command
path and was split/corrupted into hex fragments. The device printed
`[err] unknown command: ...` in `55_acdb-setcal-replay-start-wait-all-set.txt`.

Because the start script did not execute reliably, the V2635 helper did not
produce a trustworthy `A90_ACDB_SETCAL_REPLAY_DONE rc=0` / deallocate sequence.
The later PCM probe therefore ran without a proven SET replay and reproduced the
old prepare failure.

## Observed PCM/Dmesg Frontier

The bounded PCM probe still failed before the first write:

- `A90_PCM_PROBE_PCM_OPEN_OK buffer_frames=4096 buffer_bytes=16384`
- `A90_PCM_PROBE_WRITE_ERROR chunk=0 rc=-1 errno=22 strerror="Invalid argument" pcm_error="cannot prepare channel: Invalid argument"`

The captured dmesg again shows the previous missing calibration frontier:

- `afe_get_cal_topology_id: cal_type 8 not initialized for this port 16384`
- `afe_get_cal_topology_id: cal_type 9 not initialized for this port 16384`
- `send_afe_cal_type cal_block not found!!`
- `q6asm_send_cal: cal_block is NULL`
- `adm_open: DSP returned error[ADSP_EFAILED]`
- `msm-pcm-dsp ... ASoC: platform prepare error: -22`

These lines are not evidence that the SET replay failed; they are evidence that
this run did not get past the transport bug before probing PCM.

## Cleanup / Safety

- route reset commands completed and reset verification reported no mismatches
- runtime replay dir cleanup completed
- checked rollback to V2321 completed
- post-run `version/status/selftest` over the bridge confirmed V2321 and `fail=0`

## Next Unit

Fix V2639/V2638 runner transport before any SET replay rerun:

1. Generate the long start/deallocate/cleanup shell bodies as run-local files.
2. Transfer them to the device under the existing runtime directory.
3. Execute short commands such as `/bin/busybox sh <remote-script>` instead of
   inlining multi-kilobyte scripts through serial `cmdv1x`.
4. Treat protocol-noise / `[err] unknown command` as a hard failure before PCM.
5. Rerun only after focused tests prove the long scripts are staged, not inlined.

## Validation

- V2639 live run completed with rollback to V2321.
- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 - <<'PY' ...` host health check confirmed V2321 `version/status/selftest` after the run.
- This report contains no raw ACDB payloads or private binary dumps.
