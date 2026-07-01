# Kernel Tier-2 REPL live-call proof: get_iowait_load

Date: 2026-07-01

## Result

`get_iowait_load(unsigned long *nr_waiters, unsigned long *load)` is
live-proven only under a target-specific owned dual-result-slot contract:

- Input: `x0=&nr_waiters`, `x1=&load`, both pointing into one owned `kmalloc`
  buffer. The proof pre-fills both slots plus a trailing canary.
- Expected output: both unsigned-long result slots are overwritten with sane
  scheduler iowait/load values, and the trailing canary remains intact.
- Live result: two repeated calls wrote `nr_waiters=0x0`, `load=0x100000`.
- Canary: preserved for both calls.
- Cleanup: owned result buffer freed with `kfree`.
- Proof status: `trusted-under-owned-dual-iowait-load-result-slot-contract`.
- Auto-call policy: target-specific proof only; the global call-safety gate
  remains `DENY`.

Private run evidence:
`workspace/private/runs/kernel/repl-resident-session-get-iowait-load-20260701T141901Z/`

## Static Gate

- Symbol: `get_iowait_load`
- Link address: `0xffffff80080ee0ec`
- Generic resolution: `unverified`, intentionally blocked by
  `map-target-no-helper-call-before-return-or-scan-limit`.
- Global classifier: `DENY`, `auto_call_allowed=false`, not seed-whitelisted.
- Target-specific identity: `target-specific-leaf-map+xref+word-boundary`.
- Direct BL xrefs: `1` (`0xffffff800929c75c`).
- Next symbol boundary: `sched_exec` at `+0x28`.
- Source signature:
  `extern void get_iowait_load(unsigned long *nr_waiters, unsigned long *load)`
  at `include/linux/sched/stat.h:23`.
- Pointer arg indices from source: `[0, 1]`.
- Current-image body: BL-free leaf; two caller-provided memory bases only:
  `str x9, [x0]` and `str x8, [x1]`, then `ret`.
- Prefix/body words pinned:
  `b0013149 d538d088 91240129 8b090108 b9893909 f9000009 f9402508 f9000028 d65f03c0 00be7bad`.

The target is intentionally not added to `CALL_SAFETY_SEEDS`. It stays outside
the global auto-call gate and is accepted only inside this proof because the
harness supplies owned output slots and validates canary preservation plus
cleanup.

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
  `batch-001/target-results/001-get_iowait_load.json`

Timeline events are canonical top-level `events` only and include the required
eight phase events plus batch sub-events.

Selected phase timings:

- Candidate flash: `64.163958s`
- Candidate boot/health: `53.783280s`
- Warm reboot: `32.635658s`
- Batch REPL selftest wait: `32.353124s`
- Batch target call window: `13.821801s`
- Live session total: `80.121533s`
- Rollback flash: `65.799174s`
- Rollback boot-ready marker: `45.610431s`
- Candidate-flash-start to rollback-boot-ready total: `309.495289s`

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
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_get_iowait_load_passes_with_dual_owned_slot_contract \
  tests.test_a90_repl_resident_session

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  get_iowait_load

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl_resident_session.py \
  --dry-run --batch get_iowait_load --max-batch-size 30

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/analysis/analyze_repl_run_timing.py \
  --runs-dir workspace/private/runs/kernel \
  --batch-size 10 --resident-batches 10 --warm-reboot-sec 15 --json

git diff --check
```

Validation results:

- `py_compile`: pass
- Focused unittest: `12` tests pass
- Classifier: host-only pass; target remains global `DENY`, not
  seed-whitelisted
- Resident-session dry-run: pass
- Canonical timeline schema check: pass, no missing required events and no
  top-level keys other than `events`
- Timing aggregator after this run: `18/66` canonical timelines, resident
  projection `20 -> 2` flashes, `13.085s/target`, `21.06x` vs per-unit flash,
  `2.11x` vs per-unit in-boot batching
- `git diff --check`: pass

## Function Map Entry

```json
{
  "symbol": "get_iowait_load",
  "status": "live-proven",
  "trusted_input_contract": "two owned unsigned long result slots in one kmalloc buffer: x0=&nr_waiters, x1=&load; proof pre-fills both slots plus trailing canary and frees the buffer after validation",
  "return_contract": "void call writes sane unsigned long nr_waiters and load values into the two owned slots on each short-repeat call and preserves the trailing canary",
  "observed_return_value": "owned dual unsigned-long result slots contained sane nr_waiters/load values",
  "cleanup": "kfree-owned-iowait-load-result-slot-ok",
  "auto_call_policy": "target-specific-proof-only-not-global-auto-call"
}
```
