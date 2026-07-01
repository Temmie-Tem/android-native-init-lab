# Kernel REPL resident-session proof: find_get_pid

Date: 2026-07-02 KST

## Scope

Promote `find_get_pid` as a target-specific scalar PID lookup proof under the resident-session
REPL harness. The global call gate remains closed: `find_get_pid` is an explicit `DENY` seed and
is callable only through this bounded proof contract.

## Static gate

- Target: `find_get_pid`
- Link address: `0xffffff80080d82ec`
- Resolution: verified by relocated export recovery; one export candidate; map agrees with export
- Source declaration: `extern struct pid * find_get_pid(int nr)` at `include/linux/pid.h:124`
- Signature shape: scalar-only input, no pointer args
- Body pin: exact first/body words, next symbol `pid_nr_ns` at `+0xe8`
- In-body callees: `__rcu_read_lock`, `__rcu_read_unlock`
- Generic call-safety: `DENY`, `auto_call_allowed=false`, seeded
- Target-specific advisory: `CONTEXT-SENSITIVE` due RCU call pair
- Cleanup: `put_pid`, link `0xffffff80080d753c`, next symbol `free_pid` at `+0x70`,
  source declaration `extern void put_pid(struct pid *pid)`

## Live result

Successful resident-session run:

`workspace/private/runs/kernel/repl-resident-session-find-get-pid-pid1-20260701T170346Z/`

Result:

- `decision`: `a90-repl-live-call-proof-find_get_pid-pass`
- Contract: `find_get_pid(1)` twice, both returns must be the same sane `struct pid *`
- Embedded pid number: `0x1`
- Refcount path: `6 -> 7 -> 6 -> 5`
- Cleanup: `put_pid` called twice, both OK
- Raw runtime pointers and KASLR slide: private-only/redacted from public report

The first live attempt:

`workspace/private/runs/kernel/repl-resident-session-find-get-pid-20260701T165432Z/`

failed the host contract before promotion because `find_get_pid(0)` returned `0x0`. This is now
treated as an operator/host contract error: the direct `init_task->thread_pid` object has PID
number 0, but PID 0 is not a useful hash lookup proof target for `find_get_pid`. The harness rolled
back through its `finally` path and final health was clean before the corrected PID 1 run.

## Resident-session compliance

Successful run summary:

- Candidate `v1-repl` flashed once
- Mandatory warm reboot before the batch: yes
- Completed batches: `1/1`
- Completed targets: `1/1`
- Rollback `v2321` flashed once at session end
- Flash count: `2`
- Timeline schema: canonical top-level `events` only; `timeline_errors=[]`

Final device health after rollback:

- Resident build: `v2321-usb-clean-identity-rodata`
- `selftest`: `pass=11 warn=1 fail=0`

Phase timings from the successful run:

- Candidate flash: `64.312s`
- Candidate boot/health: `54.987s`
- Warm reboot: `32.671s`
- Live target batch: `7.952s`
- Rollback flash: `63.906s`
- Candidate-start to rollback-ready total: `258.466s`

Timing aggregator after this run:

- Timelines found: `76`
- Canonical runs used: `28`
- Resident projection: `13.970s/target`
- Speedup vs unbatched per-unit flash: `21.22x`
- Speedup vs per-unit in-boot batching: `2.12x`
- Modeled flash count: `20 -> 2`

## Validation

Host validation:

- `python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- Focused unittest set:
  - `CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe`
  - `CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers`
  - `CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args`
  - `SelftestIntegrationTests.test_call_proof_get_task_pid_passes_with_balanced_refcount_contract`
  - `SelftestIntegrationTests.test_call_proof_find_get_pid_passes_with_balanced_refcount_contract`
- `a90_repl.py call-safety-classify ... find_get_pid`
- `git diff --check`

Live validation:

- `a90_repl_resident_session.py --batch find_get_pid`
- Final `a90ctl version/status/selftest` after bridge restart confirmed rollback health.

## Function-map entry

`find_get_pid` is live-proven only under this target-specific contract:

`scalar PID number 1 only; two consecutive lookups must return the same sane struct pid pointer, and
both returned references are always balanced with put_pid before proof exit`.

It remains unsuitable for global auto-call.
