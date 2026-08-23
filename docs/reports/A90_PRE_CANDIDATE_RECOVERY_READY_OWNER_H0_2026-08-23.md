# A90 pre-candidate Recovery-ready owner repair

Date: 2026-08-23
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0
Status: `IMPLEMENTED_AND_INDEPENDENTLY_REVIEWED_PASS_GO`

## Result

H35 proved that the old owner could consume a candidate before it knew that
Recovery was usable. Its Native `recovery` line was sent once, the serial
response disappeared with the reboot, and the helper returned
`PRE_WRITE_FAILURE` before checking the authoritative Recovery arrival. H35
was therefore consumed with zero candidate writes.

The repaired order is:

1. `prepare` proves the exact healthy A90 and exact artifacts, creates the run,
   and acquires only `active-run.guard`;
2. exact attended approval is recorded;
3. `11-recovery-transition-intent.json` is durable before one Native
   `recovery` send;
4. the helper polls only USB while Native is present or the endpoint is absent;
5. only after exact single-Samsung `04e8:6860` appears does it open ADB and
   require exactly one manifest-bound row in state `recovery`;
6. `12-recovery-ready.json` records the USB/ADB/serial digests and the
   diagnostic command-response outcome;
7. only then does the owner create the permanent candidate-SHA guard, record
   candidate intent, and launch a helper in `--reuse-bound-recovery-only` mode;
8. that candidate helper revalidates the same Recovery role and sends no
   Native recovery command.

The command response is not relaxed into success. `CONFIRMED`,
`UNCERTAIN_RESPONSE`, `BUSY_RESPONSE`, and `ERROR_RESPONSE` are diagnostic
values only. Exact Recovery USB plus exact bound Recovery ADB is the sole
success predicate.

## Failure and crash behavior

If exact Recovery readiness is not proved, the owner publishes
`13-recovery-transition-parked.json`, retains the active guard, and has no
candidate guard, candidate intent, candidate helper, boot write, or rollback
helper. The transition is never resent. A separately reviewed closure must
first establish device state before that candidate can be considered again.

An intent-only crash consumes only the Recovery transition. A crash after the
ready record but before candidate intent remains an active-guard park; the
permanent candidate guard must be inspected before making any eligibility
claim. Once candidate intent exists, the existing candidate no-replay and
rollback rules are unchanged.

Historical H27-H35 journals keep their original public path constants and
remain parseable. New paths use distinct `CURRENT_*` constants. The current
candidate-return and postrollback consumers accept both grammars without
rewriting historical evidence.

## Directory repair

`a90_bridge.py repair-dirs` no longer treats owner-writable `0775` as success.
It requires exact target owner/group and mode `0700` for
`workspace/private`, `workspace/private/logs`,
`workspace/private/logs/bridge`, and `workspace/private/run`. Symlink or
special targets fail. The repair changes only those directory entries; it does
not recursively rewrite private inputs, artifacts, logs, or receipts.

## Closure and authority

The host-computed closures at this implementation checkpoint are:

- owner: `b7c6809cf0388da2a44f2aa9fbca99cc60e9e00d6fdddc32d39e91c70bc3ce6f`;
- candidate-return continuation:
  `603b5467efee0dabd84ea1fa463452a303cc8cf4bc4ae55e3bc2c45d25860c3e`;
- postrollback finalizer:
  `4e30bc7ac67bec18157cfafa0994fb28f0738957b7e02deb74787ec59f7835be`.

Every prior current review binds older bytes and is stale. The replacement
review is
`A90_PRE_CANDIDATE_RECOVERY_READY_OWNER_INDEPENDENT_REVIEW_2026-08-23.json`:
canonical 753-byte JSON, SHA-256
`2c21f00057fa6bcf81b8fccb4ed1c5c566007bc5b670744f19833859d92e6cd9`,
with verdict `PASS_GO`, no material findings, all contact counters zero, and
the three exact closure digests above. It reviewed the changed target-contract
clause together with the owner, candidate-return, postrollback, and bridge
repair behavior.

Host validation executed 568 tests across 18 isolated affected modules: 567
passed, and the one private H35 manifest test remained explicitly opt-in and
was skipped. Touched Python passed `py_compile`, and the tracked diff passed
`git diff --check`.

That review qualifies only this reusable H0 capability. A separately
qualified H36 identity may now be allocated, but none exists yet. Fresh
candidate qualification, manifest, connected D0, attendance, and exact
approval remain separate. This report and review grant no D0, D1, F1,
candidate, manifest, approval, Recovery transition, device contact, or live
authority.
