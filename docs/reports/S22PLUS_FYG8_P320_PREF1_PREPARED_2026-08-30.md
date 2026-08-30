# S22+ FYG8 P3.20 pre-F1 prepared record

Date: 2026-08-30 KST

Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: **prepared; F1 not authorized or executed**

This report records the bounded D1/D0 baseline work and the fresh Process-v2
prepare for P3.20. It grants no replay, Download, Odin, candidate-transfer, or
F1 authority. Device serial and raw device content remain private. A90 and
S20+ state and files were not used or changed.

## Candidate and recovery

- Ready manifest:
  `workspace/public/src/device-action/manifests/s22plus_fyg8_p320_process_v2_ready_1.json`
- Bundle SHA-256:
  `76e85f457b63622ae033a1737301ce2e47c3f027b2494026ed0f9803daf0df1e`
- Candidate AP SHA-256:
  `5b2bf78801948ab4c85067b5e9703e05d88f4b723aa537adc177ca576b2af8e5`
- Exact rollback AP SHA-256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- Host validation verdict: `PASS_DEVICE_ACTION_F1_LIVE_V2_HOST_READY`

The P3.19 candidate remains consumed and was not reused. P3.20 is a distinct
candidate with a distinct run ID and artifact identity.

## D1 incident and fresh result

The first D1 ordinal stopped after its durable arm because the exact S22+ was
connected in ADB `recovery`, not normal Android `device` state. Its start and
result records are absent, `reboot_dispatch_possible=false`, and the terminal
is `STOP_P320_D1_FRESH_BASELINE_CONSUMED_NO_REPLAY`. No reboot, write, Odin,
Download transition, or partition transfer occurred. That ordinal remains
consumed and is never replayed.

The operator returned the device to normal Android. Fresh ordinal
`p320-d1-fresh-baseline-2` then completed one exact normal reboot and verified
the same bound serial/topology, a changed boot ID, rooted healthy FYG8 Android,
and no Download endpoint. Its result is 13,447 bytes, mode `0400`, SHA-256
`38696e8a55925d5b108bdbb72862db3ede142fb75de14a368a959cc03bfba085`,
with verdict `PASS_P320_D1_FRESH_BASELINE_EXACT_NORMAL_REBOOT_RETURN_HEALTH`.

## D0 baseline

The first D0 invocation stopped before its arm and before device contact when
the host validator required a `run_directory` field that the bound P2.96 D1
producer does not emit. Commit `f2ec9700ff` removed only that mismatched
payload predicate; the fixed result path, exact binding receipt, ordinal, run
ID, serial/topology, changed boot IDs, and all safety flags remain enforced.
The repair passed independent `PASS_GO`, seven focused tests, an actual D1
result reopen, and the current-tree raw-first audit.

Corrected ordinal `p320-d0-fresh-baseline-2` then captured `/proc/last_kmsg`
once through the raw-first path. The retained 2,097,136-byte raw file is mode
`0400`, SHA-256
`cb49b368130e1ea2089f77ac504db66a98bbda9d1b31cbae6d80969b748f35d3`.
It is not an all-zero file; `ZERO_AMBIGUOUS` means zero accepted P3.20 records.
The classifier reports `baseline_clean=true`, `integrity_issue=false`,
`accepted=false`, `candidate_success=false`, and
`causal_result_allowed=false`. The D0 result is 5,981 bytes, mode `0400`,
SHA-256
`dc94de20091e4740ba86e97de9b48452b9736c731dffdf9e6be4afb9ab4fdeac`.

## Process-v2 prepare and stop point

Fresh run directory:
`workspace/private/runs/device-action-f1-live-v2/p320-ready1-prepared-20260830-1`

`load_prepared()` reopened the complete bundle and receipts successfully. The
prepared approval-binding SHA-256 is
`38489453dbcacccfb30ba968b32005343b2890d8d2ae1d67c76deee3269154be`.
`prepared.json` is 12,055 bytes, mode `0400`, SHA-256
`86dedb5ec303b925f6099a98e692aca53c051760dafeb8459ad916828fbbd8bd`.

The prepared record has `device_contact=true`, `device_writes=false`,
`partition_transfer=false`, `f1_authorized=false`, and
`live_authorized=false`. The run has no `transaction`, `f1-session`,
candidate/rollback attempt intent, `live-result.json`, or global candidate
claim. The required stop point has therefore been reached: do not invoke
`--execute` without the next explicit attended F1 action.

## Claim boundary

D1 proves only the fresh normal-reboot return and health continuity. D0 proves
only a clean pre-candidate P3.20 record baseline. Process-v2 prepare proves
only that the exact candidate, rollback, target preflight, observer closure,
and approval binding reopen successfully. None of these proves USB success,
candidate execution, causality, or an F1 result.
