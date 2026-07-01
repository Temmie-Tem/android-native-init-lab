# Kernel Tier-2 REPL live-call proof: sched_clock_cpu

Date: 2026-07-01

## Result

`sched_clock_cpu(int cpu)` is live-proven only under a target-specific scalar
CPU0 read contract:

- Input: `cpu=0`.
- Expected return: `u64` sched-clock value, either zero if the clock path is not
  running or nondecreasing across short repeated CPU0 proof calls with a
  conservative delta bound.
- Live result: three repeated calls returned nonzero, nondecreasing values.
- Observed first value: `0xa115db8ff`.
- Max observed short-run delta: `0x24ee361f`, below the `10,000,000,000ns`
  proof bound.
- Proof status: `trusted-under-sched-clock-cpu0-read-only-contract`.
- Auto-call policy: target-specific proof only; the global call-safety gate
  remains `DENY`.

Private run evidence:
`workspace/private/runs/kernel/repl-resident-session-sched-clock-cpu-20260701T135937Z/`

## Static Gate

- Symbol: `sched_clock_cpu`
- Link address: `0xffffff80080f72d4`
- Resolution: `disasm-signature+xref+map`, direct BL xrefs `16`.
- Next symbol boundary: `running_clock` at `+0x40`.
- Source signature:
  `extern u64 sched_clock_cpu(int cpu)` at
  `include/linux/sched/clock.h:21`.
- Source contract: scalar CPU id only; no pointer arguments.
- Current-image body: `sched_clock_running` global read, branch to zero return
  when not running, otherwise one call to `sched_clock`.
- Prefix/body words pinned:
  `ca1103d0 a9bf43fd 910003fd d0015908 b94fc908 340000a8 9401de62 a8c143fd ca11021e d65f03c0 aa1f03e0 a8c143fd ca11021e d65f03c0 d503201f 00be7bad`.
- Static arg-taint evidence: no caller-provided scalar argument is used as a
  memory base; pointer arg indices are empty.

The target is intentionally not added to `CALL_SAFETY_SEEDS`. It is accepted
only through the target-specific source/disassembly advisory because the
generic gate must remain fail-closed for non-seeded calls.

`find_vpid(int nr)` was rejected before implementation in this unit: the
source header says PID hash lookup must be called with `tasklist_lock` or
`rcu_read_lock` held, and the current v1-repl call primitive cannot bracket
the call with that lock/RCU section.

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

Timeline events are canonical top-level `events` only and include the required
eight phase events plus batch sub-events.

Selected phase timings:

- Candidate flash: `65.090659s`
- Candidate boot/health: `54.384747s`
- Warm reboot: `32.650446s`
- Batch REPL selftest wait: `28.057977s`
- Batch target call window: `3.575183s`
- Live session total: `65.597561s`
- Rollback flash: `64.381883s`
- Rollback boot-ready marker: `0.895789s`
- Candidate-flash-start to rollback-boot-ready total: `250.367856s`

Final resident after rollback and bridge restart:

- `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- `selftest: pass=11 warn=1 fail=0`

## Host Validation

Commands run:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/revalidation/a90_repl.py \
  workspace/public/src/scripts/revalidation/a90_repl_resident_session.py

PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_a90_repl.CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe \
  tests.test_a90_repl.CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args \
  tests.test_a90_repl.SelftestIntegrationTests.test_call_proof_sched_clock_cpu_passes_with_bounded_counter_contract \
  tests.test_a90_repl_resident_session

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl.py call-safety-classify \
  --map workspace/private/runs/kernel/v2c-c2b-kallsyms-padding-fix/System.map \
  --image workspace/private/inputs/boot_images/boot_linux_tier2_repl_v1_repl.img \
  sched_clock_cpu

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/revalidation/a90_repl_resident_session.py \
  --dry-run --batch sched_clock_cpu --max-batch-size 30

PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/analysis/analyze_repl_run_timing.py \
  --runs-dir workspace/private/runs/kernel \
  --batch-size 10 --resident-batches 10 --warm-reboot-sec 15 --json
```

Validation results:

- `py_compile`: pass
- Focused unittest: pass
- Resident-session unit tests: `9` tests pass
- Classifier: host-only pass; target remains global `DENY`, not seed-whitelisted
- Resident-session dry-run: pass
- Canonical timeline schema check: pass, no missing required events and no
  top-level keys other than `events`
- Timing aggregator after this run: `17/65` canonical timelines, resident
  projection `20 -> 2` flashes, `13.160s/target`, `20.79x` vs per-unit flash,
  `2.08x` vs per-unit in-boot batching
- `git diff --check`: pass

## Function Map Entry

```json
{
  "symbol": "sched_clock_cpu",
  "status": "live-proven",
  "trusted_input_contract": "scalar CPU id fixed to 0; current image body is pinned as sched_clock_running check plus sched_clock-or-zero return path; no caller-provided pointer arguments",
  "return_contract": "u64 sched-clock value is either stable zero when not running or nondecreasing across short repeated CPU0 proof calls with a conservative bounded delta",
  "observed_return_value": "repeated scalar CPU0 calls returned nondecreasing sched-clock values starting at 0xa115db8ff with max short-run delta 0x24ee361f",
  "cleanup": "n/a-sched-clock-scalar-read-only",
  "auto_call_policy": "target-specific-proof-only-not-global-auto-call"
}
```
