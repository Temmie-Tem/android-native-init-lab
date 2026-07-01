# Kernel Tier-2 REPL live-call proof: task_cputime_adjusted

Date: 2026-07-01

## Result

`task_cputime_adjusted(struct task_struct *p, u64 *ut, u64 *st)` is live-proven
only under a target-specific borrowed-task plus owned dual-result-slot contract:

- Input: `x0=&init_task` as a borrowed global `task_struct *`, `x1=&utime`,
  `x2=&stime`, with both result slots in one owned `kmalloc` buffer.
- Static exception: this target performs pinned pre-call `x0` field reads from
  the borrowed `init_task`; that exception is target-specific and is not a
  global auto-call rule.
- Expected output: the two `u64` result slots are overwritten with sane adjusted
  user/system cputime values, the trailing canary remains intact, and `init_task`
  is never owned or freed by the proof.
- Live result: two repeated calls wrote `utime=0x0`, `stime=0x0`.
- Canary: preserved for both calls.
- Cleanup: owned result buffer freed with `kfree`.
- Proof status:
  `trusted-under-borrowed-init-task-precall-field-read-dual-owned-cputime-result-slot-contract`.
- Auto-call policy: target-specific proof only; the global call-safety gate
  remains `DENY`.

Private run evidence:
`workspace/private/runs/kernel/repl-resident-session-task-cputime-adjusted-20260701T145629Z/`

## Static Gate

- Symbol: `task_cputime_adjusted`
- Link address: `0xffffff80080f7f2c`
- Generic resolution: unverified by default because the map target has a pre-call
  `x0` deref (`map-target-precall-x0-deref:+0x28/imm=0x148/word=0xf940a408`).
- Target-specific C1 identity: verified by `export-recovery` with
  `allow_pre_arg_deref=true`, map/export agreement, JOPP entry, and direct BL
  xrefs `4`.
- Global classifier: `DENY`, `auto_call_allowed=false`, not seed-whitelisted.
- Generic advisory: `DENY`, `candidate_safe=false`, with
  `identity-not-c1-verified` and
  `unseeded-arg-memory-flow-without-gate-pointer-contract`.
- Target-specific contract: accepted only with borrowed `init_task`, pinned
  `init_task` field loads, and owned `utime`/`stime` result slots.
- Next symbol boundary: `cputime_adjust` at `+0x70`.
- Source signature:
  `extern void task_cputime_adjusted(struct task_struct *p, u64 *ut, u64 *st)`
  at `include/linux/sched/cputime.h:55`.
- Pointer arg indices from source: `[0, 1, 2]`.
- Current-image body: no context-sensitive calls, fixed callees
  `cputime_adjust` and stack-check failure path.
- Pinned pre-call borrowed `init_task` derefs:
  `x0+328`, `x0+1936`, `x0+1944`.
- Body words pinned:
  `d100c3ff ca1103d0 a90243fd 910083fd d0015908 aa0203e3 aa0103e2 911ee001 f9478508 f81f83a8 f940a408 f943c809 f943cc0a 910003e0 f90003e9 a900a3ea 9400000c d0015909 f85f83a8 f9478529 eb08013f 540000a1 a94243fd ca11021e 9100c3ff d65f03c0 97feeaf8 00be7bad`.

The target is intentionally not added to `CALL_SAFETY_SEEDS`. It stays outside
the global auto-call gate and is accepted only inside this proof because the
harness supplies the borrowed/owned pointer contract and validates canary
preservation plus cleanup.

## Live Run

Resident-session mode was used:

`v1-repl flash once -> warm reboot -> one bounded batch -> per-target flush -> v2321 rollback once`.

Run summary:

- Session decision: `a90-repl-resident-session-pass`
- Batch count: `1`
- Completed target count: `1`
- Flash count: `2`
- Candidate flashed once: `true`
- Rollback flashed once: `true`
- Warm reboot between batches: `true`
- Timeline errors: `[]`
- Per-target flush file:
  `batch-001/target-results/001-task_cputime_adjusted.json`

Timeline events are canonical top-level `events` only and include the required
eight phase events plus batch sub-events.

Selected phase timings:

- Candidate flash: `64.240308s`
- Candidate boot/health: `53.938049s`
- Warm reboot: `33.011283s`
- Batch target call window: `13.616407s`
- Rollback flash: `64.834542s`
- Rollback boot-ready marker: `48.034962s`
- Candidate-flash-start to rollback-boot-ready total: `311.223365s`

Final resident after rollback:

- `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- `selftest: pass=11 warn=1 fail=0`

## Host Validation

Commands run:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_task_cputime_adjusted_passes_with_init_task_precall_dual_owned_slot_contract \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_thread_group_cputime_adjusted_passes_with_init_task_dual_owned_slot_contract \
  tests.test_a90_repl_resident_session

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --limit 0 --no-objdump task_cputime_adjusted

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl_resident_session.py \
  --dry-run --batch task_cputime_adjusted --max-batch-size 30 \
  --run-dir workspace/private/runs/kernel/repl-resident-session-task-cputime-adjusted-dryrun

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/analysis/analyze_repl_run_timing.py \
  --runs-dir workspace/private/runs/kernel \
  --batch-size 10 --resident-batches 10 --warm-reboot-sec 15 --json

git diff --check
```

Validation results:

- `py_compile`: pass
- Focused `a90_repl` plus resident-session unittest: `13` tests pass
- Classifier sweep: host-only pass; target remains global `DENY`, not
  seed-whitelisted
- Resident-session dry-run: pass
- Rollback image precondition: v2321/v2237/v48 present; v2321/v2237 SHA matched
  the gate values; v1-repl candidate SHA matched
- Recovery path: flash helper entered recovery, observed ADB recovery readiness,
  wrote only `/dev/block/by-name/boot`, verified readback SHA, and rebooted via
  TWRP
- Canonical timeline schema check: pass, no missing required events and no
  top-level keys other than `events`
- Timing aggregator after this run: `20/68` canonical timelines, resident
  projection `20 -> 2` flashes, `12.945s/target`, `21.46x` vs per-unit flash,
  `2.15x` vs per-unit in-boot batching
- `git diff --check`: pass

## Function Map Entry

```json
{
  "symbol": "task_cputime_adjusted",
  "status": "live-proven",
  "trusted_input_contract": "borrowed global init_task task_struct pointer plus two owned u64 result slots in one kmalloc buffer: x0=&init_task, x1=&utime, x2=&stime; proof permits the pinned function's pre-call init_task field reads, pre-fills both slots plus trailing canary, and frees the buffer after validation",
  "return_contract": "void call writes sane adjusted user/system cputime values for init_task into the owned utime/stime slots on each short-repeat call, preserves the trailing canary, and leaves the borrowed init_task pointer unowned",
  "observed_return_value": "owned dual u64 result slots contained sane adjusted init_task utime/stime values",
  "cleanup": "kfree-owned-task-cputime-result-slot-ok",
  "auto_call_policy": "target-specific-proof-only-not-global-auto-call"
}
```
