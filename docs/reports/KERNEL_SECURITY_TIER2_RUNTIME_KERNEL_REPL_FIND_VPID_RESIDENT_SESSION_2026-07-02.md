# Kernel REPL resident-session proof: find_vpid

Date: 2026-07-02 KST

## Scope

Promote `find_vpid` as a target-specific scalar PID lookup proof under the resident-session
REPL harness. The proof composes with the already proven `find_get_pid(1)` owned reference:
`find_get_pid(1)` establishes a stable pid anchor, then `find_vpid(1)` must return the same
`struct pid *` as a borrowed pointer without changing the observed refcount.

The global call gate remains closed: `find_vpid` is an explicit `DENY` seed and is callable
only through this bounded proof contract.

## Static gate

- Target: `find_vpid`
- Link address: `0xffffff80080d7ddc`
- Resolution: verified by relocated export recovery; one export candidate; map agrees with export
- Source declaration: `extern struct pid * find_vpid(int nr)` at `include/linux/pid.h:119`
- Signature shape: scalar-only input, no pointer args
- Body pin: exact body words, leaf/no in-body BL, next symbol `task_active_pid_ns` at `+0xa8`
- Generic call-safety: `DENY`, `auto_call_allowed=false`, seeded
- Target-specific advisory: `SAFE-SCALAR`
- Anchor: `find_get_pid`, link `0xffffff80080d82ec`, declaration
  `extern struct pid * find_get_pid(int nr)`, still generic `DENY` and target-specific
  `CONTEXT-SENSITIVE` due the RCU call pair
- Cleanup: `put_pid`, link `0xffffff80080d753c`, next symbol `free_pid` at `+0x70`,
  source declaration `extern void put_pid(struct pid *pid)`

## Live result

Successful resident-session run:

`workspace/private/runs/kernel/repl-resident-session-find-vpid-20260701T171834Z/`

Result:

- `decision`: `a90-repl-live-call-proof-find_vpid-pass`
- Contract: `find_get_pid(1)` owned anchor, then `find_vpid(1)` borrowed lookup
- Embedded pid number: `0x1`
- Return check: `find_vpid(1)` returned the same pid pointer as the owned `find_get_pid(1)` anchor
- Refcount path: `6 -> 6 -> 5` after anchor, after `find_vpid`, after `put_pid`
- Cleanup: `put_pid` called once for the anchor ref, OK
- Raw runtime pointers and KASLR slide: private-only/redacted from public report

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

- Candidate flash: `65.037s`
- Candidate boot/health: `42.969s`
- Warm reboot: `33.309s`
- Batch REPL selftest readiness after warm reboot: `40.265s`
- Live target batch: `6.831s`
- Rollback flash: `65.917s`
- Rollback boot/health: `48.195s`
- Candidate-start to rollback-ready total: `303.855s`

Timing aggregator after this run:

- Timelines found: `77`
- Canonical runs used: `29`
- Resident projection: `13.898s/target`
- Speedup vs unbatched per-unit flash: `21.35x`
- Speedup vs per-unit in-boot batching: `2.13x`
- Modeled flash count: `20 -> 2`

## Validation

Host validation:

- `python3 -m py_compile workspace/public/src/scripts/revalidation/a90_repl.py tests/test_a90_repl.py`
- Focused unittest set:
  - `CallSafetyClassificationTests.test_proven_live_call_targets_stay_safe`
  - `CallSafetyClassificationTests.test_seed_inventory_summary_counts_tiers`
  - `CallSafetyClassificationTests.test_source_signature_oracle_distinguishes_scalar_and_pointer_args`
  - `SelftestIntegrationTests.test_call_proof_find_get_pid_passes_with_balanced_refcount_contract`
  - `SelftestIntegrationTests.test_call_proof_find_vpid_passes_with_borrowed_pid_contract`
- `a90_repl.py call-safety-classify ... find_vpid find_get_pid put_pid`
- `git diff --check`

Live validation:

- `a90_repl_resident_session.py --batch find_vpid`
- Final `a90ctl version/status/selftest` independently confirmed rollback health.

## Function-map entry

`find_vpid` is live-proven only under this target-specific contract:

`scalar PID number 1 only; proof first obtains an owned find_get_pid(1) reference as a stable
cross-check pointer, then calls find_vpid(1) and treats the return as borrowed`.

It remains unsuitable for global auto-call.
