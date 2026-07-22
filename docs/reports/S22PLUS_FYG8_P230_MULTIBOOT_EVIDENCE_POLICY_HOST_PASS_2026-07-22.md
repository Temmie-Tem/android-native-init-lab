# S22+ FYG8 P2.30 multiboot evidence policy host pass

Date: 2026-07-22 KST
Tier: H0, host-only evidence-policy implementation and replay
Status: `PASS_P230_MULTIBOOT_EVIDENCE_POLICY_HOST_ONLY`
Live authority: none

## Result

P2.30 closes the cardinality mismatch exposed by P2.29 without rewriting its
immutable exact-one verdict. A new opt-in typed evidence kind and fixed policy
identity accept one or more pure exact USERSPACE records after a separately
clean retained baseline. The original P2.19 decoder remains byte-for-byte and
semantically unchanged; it still rejects duplicate records.

No device was contacted, no kernel or image was built, no AP or ready manifest
was created, and no D0, D1, F1, or live authority was granted.

## Acceptance Rule

The fixed P2.30 rule requires:

1. the unchanged P2.19 candidate contract and exact ENTRY, USERSPACE, UNSAT,
   long-family, and UNSAT-family bytes;
2. a separately collected baseline with zero exact records, zero family bytes,
   and no snapshot-edge partial;
3. one or more exact USERSPACE records in the post-rollback snapshot; and
4. zero ENTRY, UNSAT, foreign-family, malformed, mixed-state, or edge-partial
   evidence.

One exact USERSPACE record and repeated pure USERSPACE records are positive.
Repeated pure ENTRY or UNSAT records are diagnostic but not accepted. Zero is
still `ZERO_AMBIGUOUS`. The bounded snapshot supplies the storage bound; no
arbitrary boot-count cap is imposed because physical recovery may require more
than one candidate reboot.

`minimum_candidate_boots` is the exact-record count only when integrity is
clean. This lower bound follows from the candidate's source-pinned
one-USERSPACE-write-per-boot guard; it is not a claim about unobserved boots.

## Compatibility

The new policy is not selected by default and is not manifest-configurable in
its decoder, policy identity, accepted state, or minimum count. Its offline
contract reuses the exact P2.19 candidate/static artifacts while binding the
new policy identity. Execution-critical receipts include both decoders and the
supporting static checker, design model, and base checker.

Existing exact-one manifests, results, tests, and P2.29's durable
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` verdict are unchanged.

## Archived Replay

The private P2.29 raw snapshots were replayed without device contact:

- preparation baseline: clean `ZERO_AMBIGUOUS`;
- execute-time baseline: clean `ZERO_AMBIGUOUS`;
- old exact-one decoder: `AMBIGUOUS_INTEGRITY_FAILURE`, not accepted;
- P2.30 decoder: `USERSPACE_CALLBACK_REACHED_ONE_OR_MORE_BOOTS`, accepted;
- exact USERSPACE record count and minimum evidenced candidate boots: 2.

This validates the new rule against the event that motivated it. It does not
retroactively change the P2.29 F1 result.

## Independent Review

The first independent review found no implementation defect but withheld GO
for missing direct regression coverage of the new clean-baseline dispatch. It
also requested both foreign families and both snapshot edges in the decoder
matrix. Those cases were added: only ordinary family-free bytes can produce a
clean baseline, and every requested malformed/partial case fails closed.
The focused follow-up review found no remaining issue and issued `GO`.

## Boundary And Next Unit

P2.30 is an H0 evidence capability only. F1 remains inactive and all previous
bindings are consumed.

Planning correction from P2.31: advancing directly to E2 would skip unfinished
E1 work. The observation closes only the first procfs checkpoint. P2.32 must
first design continued E1 evidence for the remaining mounts, child lifecycle,
watchdog closure, and terminal success. It must not create a live candidate or
infer platform bind from module presence.
