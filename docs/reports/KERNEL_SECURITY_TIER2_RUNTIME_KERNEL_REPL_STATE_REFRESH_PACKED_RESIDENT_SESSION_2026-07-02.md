# Kernel REPL packed resident-session state/time/memory refresh batch

Date: 2026-07-02 KST

## Scope

Refresh ten already handler-backed state/time/memory call-proof targets under the
repaired `dmesg -c` REPL result channel and the operator-corrected packed resident
cadence.

This unit does not build a new boot artifact. It flashes the existing v1-repl
candidate once, runs one packed batch, flushes every target result to disk, and rolls
back to v2321 once at the end.

## Batch

Targets:

- `can_do_mlock`
- `get_avenrun`
- `get_ddr_revision_id_1`
- `get_ddr_revision_id_2`
- `is_current_pgrp_orphaned`
- `ktime_get_real_seconds`
- `ktime_get_seconds`
- `ktime_get_ts64`
- `total_swapcache_pages`
- `vm_commit_limit`

Static gate:

- `call-safety-classify`: `ok=true`
- Tier counts: `SAFE-SCALAR=8`, `SAFE-WITH-VALID-PTR=2`
- All pointer-argument targets use owned result slots only.

Dry-run gate:

- `target_count=10`
- `max_batch_size=30`
- Candidate image SHA256:
  `b846ae9f74d8ceb922bbcd854d78b6795ef833d61e38465d3cc474cb6f0dfb65`
- Rollback v2321 SHA256:
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`

## Live Result

Private run directory:

`workspace/private/runs/kernel/repl-resident-session-state-refresh-batch-20260701T184431Z/`

Session summary:

- Decision: `a90-repl-resident-session-pass`
- Completed targets: `10/10`
- Completed batches: `1/1`
- Flash count: `2`
- Actual flash amortization: `0.2 flash/target`
- Raw runtime values: private only
- Timeline errors: `[]`
- Warm reboot before batch: yes
- Rollback flashed once at session end: yes

Target outcomes:

| Target | Outcome |
| --- | --- |
| `can_do_mlock` | Repeated no-argument calls returned a bool in contract. |
| `get_avenrun` | Owned three-slot load-average result buffer was written in contract; canary intact. |
| `get_ddr_revision_id_1` | Repeated reads were stable; low-byte DDR revision contract held. |
| `get_ddr_revision_id_2` | Repeated reads were stable; low-byte DDR revision contract held. |
| `is_current_pgrp_orphaned` | Repeated no-argument calls returned a bool in contract. |
| `ktime_get_real_seconds` | Repeated reads were nondecreasing across the proof window. |
| `ktime_get_seconds` | Repeated monotonic seconds reads stayed stable/nondecreasing. |
| `ktime_get_ts64` | Owned `timespec64` result slot was written twice with increasing time; canary intact. |
| `total_swapcache_pages` | Repeated reads returned a sane bounded swapcache page count. |
| `vm_commit_limit` | Repeated reads returned a sane stable commit-limit page count. |

No raw runtime pointers, KASLR slide, or private result payloads are promoted in this
report.

## Timing

Canonical `events:[{name,timestamp_utc}]` timeline was present with the required
flash, boot, live-session, and rollback phases.

- Candidate flash: `53.074s`
- Candidate boot/health: `42.970s`
- Warm reboot: `19.893s`
- Live batch window: `44.934s`
- Rollback flash: `64.213s`
- Rollback boot/health: `48.219s`
- Candidate-start to rollback-ready total: `307.035s`
- Measured wall time per target: `30.70s/target`

Run-timing aggregate after this pass:

- Canonical timelines parsed: `35/84`
- Resident-session projection with `batch_size=10`, `resident_batches=10`,
  `warm_reboot=15s`: `14.0s/target`, `21.3x` vs per-unit flash and `2.1x`
  vs per-unit in-boot batching

This measured run is slower per target than the max30 pass because it intentionally
used only ten queued refresh targets. It still follows the corrected packed-session
rule: no one-target resident session, one v1-repl flash, one rollback flash, and
per-target disk flush.

## Final Device State

Rollback health from the harness and an independent repo-local recheck confirmed clean
v2321:

- Resident build: `v2321-usb-clean-identity-rodata`
- `version`: `0.9.285 build=v2321-usb-clean-identity-rodata`
- `status`: `BOOT OK`, `selftest fail=0`
- `selftest`: `pass=11 warn=1 fail=0`

## Validation

Host validation:

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- Focused unittest set covering command-buffer helpers, live-math fake transport,
  call-safety classification, task lookup proofs, and packed fake PID borrowed batch:
  `Ran 26 tests`, `OK`
- `call-safety-classify` for the ten target names: `ok=true`,
  `SAFE-SCALAR=8`, `SAFE-WITH-VALID-PTR=2`
- `git diff --check`

Live validation:

- Packed resident-session run: `10/10` target pass
- Rollback clean to v2321
- Final independent health clean

## Decision

Promote the ten-target state/time/memory refresh as packed resident-session evidence
under the default `dmesg -c` result channel. Continue using packed sessions only:
accumulate target queues toward `max_batch_size=30`, flush each target result
immediately, warm-reboot between batches, and roll back once at session end.
