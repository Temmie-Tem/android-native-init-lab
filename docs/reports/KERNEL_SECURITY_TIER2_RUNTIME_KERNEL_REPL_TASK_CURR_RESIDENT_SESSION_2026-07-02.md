# Kernel Tier-2 REPL live-call proof: task_curr

Date: 2026-07-02

## Result

`task_curr(const struct task_struct *p)` is live-proven only under a
target-specific borrowed `init_task` leaf-reader contract:

- Input: `x0=&init_task` as a borrowed global `task_struct *`.
- Static exception: the leaf body performs one pinned pre-call `x0` field read
  (`task->cpu`, immediate `132`). That exception is target-specific and is not
  a global auto-call rule.
- Expected return: exact boolean `0` or `1`; repeat values may legitimately
  differ if scheduler state changes.
- Live result: three repeated calls returned `0x1`, `0x1`, `0x1`.
- Cleanup: none; the pointer is borrowed/read-only and never freed.
- Proof status:
  `trusted-under-borrowed-init-task-leaf-current-state-contract`.
- Auto-call policy: target-specific proof only; the global call-safety gate
  remains `DENY`.

Private run evidence:
`workspace/private/runs/kernel/repl-resident-session-task-curr-20260701T151106Z/`

## Static Gate

- Symbol: `task_curr`
- Link address: `0xffffff80080eb9fc`
- Generic resolution: unverified by default because the map target has a
  pre-call `x0` deref
  (`map-target-precall-x0-deref:+0x0/imm=0x84/word=0xb9408408`) and has no
  helper call before return.
- Target-specific C1 identity: verified by map address, next-symbol boundary,
  direct BL xrefs, fixed body words, and pinned borrowed-pointer deref.
- Global classifier: `DENY`, `auto_call_allowed=false`, not seed-whitelisted.
- Generic advisory: `DENY`, `candidate_safe=false`, with
  `identity-not-c1-verified` and
  `unseeded-arg-memory-flow-without-gate-pointer-contract`.
- Target-specific contract: accepted only with borrowed global `init_task`,
  the pinned leaf body, and boolean-return validation.
- Next symbol boundary: `check_preempt_curr` at `+0x30`.
- Source signature:
  `extern int task_curr(const struct task_struct *p)` at
  `include/linux/sched.h:1734`.
- Pointer arg indices from source: `[0]`.
- Current-image body: leaf, no BL instructions, no context-sensitive calls.
- Pinned pre-call borrowed `init_task` deref: `x0+132`.
- Body words pinned:
  `b9408408 f0015969 911b0129 f8687928 90013169 91240129 8b090108 f9447d08 eb00011f 1a9f17e0 d65f03c0 00be7bad`.

The target is intentionally not added to `CALL_SAFETY_SEEDS`. It stays outside
the global auto-call gate and is accepted only inside this proof because the
harness supplies the borrowed pointer contract and validates the return as a
boolean scheduler current-state observation.

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
- Per-target flush file: `batch-001/target-results/001-task_curr.json`

Timeline events are canonical top-level `events` only and include the required
eight phase events plus batch sub-events.

Selected phase timings:

- Candidate flash: `64.317s`
- Candidate boot/health: `35.941s`
- Warm reboot: `33.273s`
- Batch target call window: `3.626s`
- Rollback flash: `63.792s`
- Rollback boot-ready marker: `1.023s`
- Candidate-flash-start to rollback-boot-ready total: `243.512s`

Final resident after rollback:

- `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- `selftest: pass=11 warn=1 fail=0`

## Host Validation

Commands run:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  tests/test_a90_repl.py \
  workspace/public/src/scripts/revalidation/a90_repl_resident_session.py \
  workspace/public/src/scripts/analysis/analyze_repl_run_timing.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_task_curr_passes_with_init_task_leaf_boolean_contract \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_task_prio_passes_with_init_task_direct_field_contract \
  tests.test_a90_repl_resident_session

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-sweep \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  --source-root workspace/private/inputs/kernel_source/SM-A908N_KOR_12_Opensource/Kernel \
  --limit 0 --no-objdump task_curr

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl_resident_session.py \
  --dry-run --batch task_curr --max-batch-size 30 \
  --run-dir workspace/private/runs/kernel/repl-resident-session-task-curr-dryrun

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
- Recovery path: flash helper entered recovery, wrote only
  `/dev/block/by-name/boot`, verified readback SHA, and rebooted via TWRP
- Canonical timeline schema check: pass, no missing required events and no
  top-level keys other than `events`
- Timing aggregator after this run: `21/69` canonical timelines, resident
  projection `20 -> 2` flashes, `12.852s/target`, `21.49x` vs per-unit flash,
  `2.15x` vs per-unit in-boot batching
- Final sequential resident health: v2321 `version/status/selftest` passed,
  `selftest fail=0`

## Function Map Entry

```json
{
  "symbol": "task_curr",
  "status": "live-proven",
  "trusted_input_contract": "global init_task task_struct pointer; global pointer is borrowed/read-only and is not freed; proof permits the pinned leaf body's one task->cpu field read",
  "return_contract": "int return is exactly a boolean 0/1 task-current state observation for init_task; repeated proof calls may legitimately differ if scheduler state changes",
  "observed_return_value": "repeated borrowed-init_task calls returned boolean values 0x1,0x1,0x1",
  "cleanup": "n/a-borrowed-pointer-read-only",
  "auto_call_policy": "target-specific-proof-only-not-global-auto-call"
}
```
