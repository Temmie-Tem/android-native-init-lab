# A90 uncertain-return failed-boot evidence continuation — H0

Date: 2026-08-22
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 host-only implementation and static review
Device contact: none
Authority: none — no candidate, D0, D1, F1, approval, transfer, reboot,
rollback, replay, or live authority is created

Follow-up: `A90_CONTINUATION_POSTROLLBACK_REVIEW_BLOCKER_REPAIR_H0_2026-08-22.md`
records the full-review NO_GO findings, their bounded repairs, and the final
current continuation/postrollback `PASS_GO` artifacts. It does not revise this
report's implementation-time evidence or grant live authority.

## Result

The candidate-return continuation now preserves one bounded failed-boot
evidence opportunity when an attended TWRP System return ends at the same
qualified TWRP recovery rather than a visible Native candidate. This closes
the evidence omission identified after H27/H28/H29 without pretending that
TWRP presence proves whether the candidate ever reached userspace.

The attribution is therefore fixed as `UNCERTAIN`, its only permitted use is
`EVIDENCE_ONLY_NO_DEVICE_REFUTATION`, and
`deviceContradictionEligible` is always `false`. The evidence can explain a
failure later; it cannot turn this branch into PASS or REFUTED.

This unit changes only:

- `a90_f1_candidate_return_continuation_v1.py`;
- its fixed production backend; and
- focused host-only tests.

The minimal F1 owner and candidate-neutral postrollback recovery owner are
unchanged. The earlier first-opportunity observer and its fixed raw-source
policy are reused rather than duplicated.

## Exact sequence

The physical continuation branch is now:

1. publish main-journal record `25-candidate-observation-intent.json` before
   contact, including the fixed evidence intent;
2. perform the already bounded post-physical observation;
3. only for exact state `TWRP_RETURNED_AFTER_PHYSICAL` with attribution
   `BOUND_TWRP_RETURNED_AFTER_PHYSICAL`, invoke the fixed observer;
4. read only `/proc/cmdline` and `/proc/last_kmsg` through the existing fixed
   recovery adapter, with no mount and the existing 60-second total budget;
5. publish one mode-`0600`, no-clobber, file-fsynced and directory-fsynced
   private result sidecar; and
6. continue to the existing one-shot rollback only when the observer result
   proves every child quiescent. A non-quiescent result parks without rollback.

No new approval, manifest field, operator step, partition, transfer helper,
mount, caller-selected command, retry, or candidate replay is added.

## One sidecar, not a second journal

Record `25` is the durable intent and remains part of the existing canonical
main journal. The only new durable object is:

```text
<RUN_ROOT>/<runId>-candidate-return-uncertain-evidence-result.json
```

The result binds the run and manifest, pending candidate receipt, exact record
`25` digest, exact triggering observation and digest, attribution and proof-use
labels, `candidateReplay:false`, `rollbackReplay:false`, and the strictly typed
existing `FailedBootEvidenceResult` payload. Publication uses
`O_EXCL|O_NOFOLLOW`, a direct regular link-count-one file, exact owner/group,
file fsync, directory fsync, and byte-exact readback.

Raw evidence remains in the existing private observer output. The structured
sidecar carries only the already bounded evidence receipt metadata; it is not
a terminal result or a device-proof receipt.

## Crash cuts and no-replay behavior

The new crash cuts are deliberately asymmetric:

- durable `25` with no result sidecar: the observation/evidence opportunity is
  consumed; a later invocation makes zero device contact and does not retry
  observation, capture, candidate, or rollback;
- a malformed, substituted, or nonphysical sidecar context: zero device
  contact and no rollback;
- a valid non-quiescent result: durable recovery-required park, no rollback;
- a valid quiescent result with no record `30`: a later attended finalize loads
  and validates the sidecar, repeats neither post-physical observation nor
  evidence capture, and may enter only the existing one-shot rollback; and
- once record `30` exists, the ordinary rollback/recovery machinery owns the
  run. This continuation cannot replay it.

An ordinary fixed-observer failure may produce a quiescent
`NO_PROOF_OBSERVER`, allowing safety recovery while retaining no proof. An
unexpected backend-contract exception is converted to non-quiescent
`COMMAND_NONQUIESCENT`, persisted, and parked. Lease loss is never downgraded.

## Review and activation state

The initial independent H0 delta review accepted the conditional trigger,
evidence-only typing, one-sidecar publication, and quiescence gate. A second
independent delta review examined the host-cut case after a durable sidecar but
before rollback intent and returned `PASS_GO_H0_DELTA`. It confirmed that a
valid result resumes only rollback; missing, invalid, or nonphysical state
causes zero device operation; and observation, capture, candidate, and
rollback effects are not replayed.

The current execution closures are:

- minimal owner:
  `c22b5a8ae6b630a178c31db22b6a9167ac6ed969b1d894a29c3399275db44c5e`;
- candidate-return continuation:
  `d8a50ee0ca7527d4a4a6b80e63ae1e2071b88c9917947ed8107a4aeedcaa955b`;
- postrollback recovery:
  `a6bf12eef5a5c9514a2c8613cbfdcd4c4e0c8f5800f393b6b728b3048827af2c`.

The canonical current continuation review still binds stale closure
`d053e137ca6d984709e53a1200d1e980f6d766ab4dd30cbb012cef2ddd3ee9e1`.
Therefore the live review gate fails closed. This H0 report and its delta
review do not replace the canonical independent review artifact.

## Validation

- 211 focused continuation/backend tests passed;
- 347 adjacent A90 owner, adapter, receipt, continuation, backend, and
  postrollback tests passed;
- all four touched Python files passed `py_compile`; and
- no test invoked ADB, USB inventory, a device, a network endpoint, or private
  live-run evidence.

The final scoped repository checks are recorded at commit time. The report
body, rather than only its filename, must be staged and inspected before
commit.

## Consequence

This unit makes the next failed candidate materially more diagnosable without
changing its proof status or delaying a quiescent rollback. It does not
qualify H30 or any rebuilt kernel and does not authorize D0 or F1.

The next sequence remains: obtain a fresh canonical continuation-closure
review, then close the remaining RTIC/stock-equivalence question before any
new candidate qualification and attended F1 proposal.
