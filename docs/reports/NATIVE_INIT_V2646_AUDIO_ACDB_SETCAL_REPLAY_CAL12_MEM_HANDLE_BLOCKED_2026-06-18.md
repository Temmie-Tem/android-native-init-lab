# NATIVE_INIT V2646 — ACDB SET-cal replay cal_type 12 mem_handle blocker

Date: 2026-06-18

## Scope

One self-authorized V2639 native ACDB SET-cal replay rerun after the V2645
header-only replay policy fix. This run stayed inside the recoverable envelope:
boot partition only via the checked helper, runtime `/cache` staging, bounded
route setup, no PCM probe unless all SETs completed, cleanup, and rollback to
V2321.

Raw ACDB bytes remain private under the run directory and are not committed.

## Run

- private_run_dir: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-104246`
- decision: `v2639-acdb-setcal-replay-live-blocked`
- rolled_back: `True`
- rollback_version_ok: `True`
- rollback_selftest_fail0: `True`
- post-run independent health: V2321 `0.9.285`, `selftest fail=0`

## What Advanced

The V2645 helper fix worked. The helper no longer rejects cal_type `21` just
because the captured exact arg has non-zero `cal_size` and no external payload.
The live stderr contains:

```text
A90_ACDB_SETCAL_HEADER_ONLY_EXACT_ARG cal_type=21 buffer=0 cal_size=28 arg_len=72
```

The replay reached real `/dev/msm_audio_cal` SETs and completed:

```text
AUDIO_SET_CALIBRATION ok cal_type=39 ...
A90_ACDB_SETCAL_SET_OK index=0 cal_type=39 kind=1 has_payload=1
AUDIO_SET_CALIBRATION ok cal_type=13 ...
A90_ACDB_SETCAL_SET_OK index=1 cal_type=13 kind=2 has_payload=0
AUDIO_SET_CALIBRATION ok cal_type=9 ...
A90_ACDB_SETCAL_SET_OK index=2 cal_type=9 kind=2 has_payload=0
AUDIO_SET_CALIBRATION ok cal_type=11 ...
A90_ACDB_SETCAL_SET_OK index=3 cal_type=11 kind=2 has_payload=1
```

## New Blocker

The run stopped at the header/no-payload VOL record:

```text
AUDIO_SET_CALIBRATION failed rc=-1 errno=22 strerror=Invalid argument cal_type=12 buffer=0 cal_size=0 mem_handle=17 arg_len=48
```

Interpretation:

- This is no longer the V2644 helper payload-policy failure.
- It is a kernel `AUDIO_SET_CALIBRATION` rejection for cal_type `12`.
- The failing record is classified by V2634/V2636 as `VOL_HEADER_NO_PAYLOAD`
  with `dmabuf_expected=False` and `cal_size=0`.
- The captured arg still carries `mem_handle=17`; unlike cal_type `13` and `9`,
  which replayed successfully with `mem_handle=-1`, this stale handle appears to
  be invalid in native replay because no matching dma-buf allocation exists in
  this process.

The helper correctly deallocated the payload-backed records already allocated
before aborting:

```text
AUDIO_DEALLOCATE_CALIBRATION ok cal_type=11 ... mem_handle=6
A90_ACDB_SETCAL_DEALLOCATE_OK index=3 cal_type=11
AUDIO_DEALLOCATE_CALIBRATION ok cal_type=39 ... mem_handle=4
A90_ACDB_SETCAL_DEALLOCATE_OK index=0 cal_type=39
A90_ACDB_SETCAL_REPLAY_DONE rc=1
```

Route reset verification passed, runtime cleanup completed, and rollback to
V2321 passed.

## PCM Status

No PCM probe was attempted. The run failed closed before the final SET marker
`A90_ACDB_SETCAL_SET_OK index=8`, so the speaker `pcm_prepare()` frontier remains
unretested after ACDB SET replay.

## Next Unit

Host-only fix before any live rerun:

1. Inspect the captured header/no-payload exact args for cal_types `12`, `21`,
   `13`, `9`, and `23` to pin their `mem_handle` values.
2. Decide a bounded replay policy for header/no-payload records with
   `cal_size==0` and stale positive `mem_handle` values, likely patching
   `mem_handle=-1` for records without an external payload.
3. Preserve exact bytes for inline/nonzero header records unless evidence proves
   their mem_handle also needs neutralization.
4. Add tests and rebuild the private helper/deploy manifest before another
   single live rerun.

Do not blind-rerun V2639 unchanged.

## Validation Evidence

- Rollback image SHA before live: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
- Bridge/device preflight: V2321 `version` OK and `selftest fail=0`.
- V2639 dry-run: `ok=True`, `manual_approval_required=False`, `safe_to_run_native_replay=True`.
- Live run result: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-104246/result.json`.
- Failure detail: `workspace/private/runs/audio/v2639-acdb-setcal-replay-20260618-104246/58_acdb-setcal-replay-start-wait-all-set.txt`.
- Cleanup/rollback evidence: steps `72` through `75` in the same private run dir.
