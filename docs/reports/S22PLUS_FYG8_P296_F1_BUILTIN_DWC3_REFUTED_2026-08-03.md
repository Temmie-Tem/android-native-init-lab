# S22+ FYG8 P2.96 F1 built-in DWC3 telemetry result

Date: 2026-08-03

## Outcome

P2.96 closed `HEALTHY` with one candidate transfer, one exact Magisk rollback
transfer, and no candidate replay or retransmission. The Process-v2 verdict is
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK` because the success acceptance was not
present. The experiment result is nevertheless information-bearing
`REFUTED`: the two byte-identical post-rollback reads contain one exact,
integrity-clean P2.96 terminal failure record for the bound run ID.
The typed evidence classifier is `E2_FAILURE_OBSERVED`.

The canonical eight events are complete. Final Android boot, boot-animation,
root, boot, vendor_boot, DTBO, recovery, and Download-endpoint-absence health
all match the FYG8 Magisk profile.

## Exact retained result

The adjacent valid slots are:

- generation 106, stage `0x92`, detail `0x0c60`: built-in DWC3
  `USBLNKST=0`; and
- generation 107, stage `0x93`, detail `0x0c72`: terminal
  `digital-control-state-nominal-not attached-UNKNOWN-coreidle-1-susphy-0`.

The terminal record is explicit failure, not progress, fallback, corruption,
foreign evidence, or an UNSAT record. Both slots are valid and adjacent. The
record proves that the P2.96 built-in snapshot was delivered and executed on
device without the rejected P2.94 external `dwc3-msm.ko` dependency.

The candidate-side CDC-ACM endpoint did not appear during the bounded
five-minute observer window. The operator independently observed a completed
candidate boot with no boot loop. That observation is supportive only; the
formal result is the retained failure record plus verified rollback health.

## Recovery and transfer accounting

After candidate observation closed, the first measured recovery USB inventory
failed while the physical Download handoff was in progress. The live execute
invocation stopped without repeating the candidate or starting rollback. The
exact `04e8:685d` Download endpoint then appeared, and `--recover` resumed the
same durable journal with no second approval or new candidate authority.

The recovery path transferred only the prebound Magisk rollback once. It then
verified two byte-identical retained reads and exact final health. This was an
existing host-observer/endpoint-arrival failure class, not target ambiguity,
rollback deviation, or a device-health incident.

Transfer accounting:

- candidate: `1` completed;
- rollback: `1` completed;
- candidate replay: `0`;
- candidate retransmission: `0`;
- rollback retransmission: `0`; and
- A90 commands: `0`.

Private structured evidence is under
`workspace/private/runs/device-action-f1-live-v2/p296-ready1-prepared-20260803-1/`.
The validated final result SHA256 is
`35a407dc2de3acfc07c39521bd175296a825578f57db517b6ed2275761c7607a`.

## Interpretation and limits

P2.96 preserves the P2.92 direct-bind prefix and adds a delivered built-in
snapshot. The result rules out the hypothesis that removing the external
wrapper dependency would reveal a configured or attached controller state in
this run. It does not by itself identify whether the remaining boundary is
VBUS/session validity, pullup or soft-disconnect state, missing connection
events, event-buffer handling, or PHY/link training.

`USBLNKST=0` must not be read as proof of host enumeration. In the same exact
snapshot closure the UDC state remains `not attached`, connection speed remains
`UNKNOWN`, and no host CDC-ACM endpoint appeared.

## Next bounded unit

Remain H0. Correlate the exact `USBLNKST=0`, `COREIDLE=1`, `SUSPHY=0`, nominal
digital-control predicates, and absent `CONNECTSPD` with the source-matched
built-in DWC3 gadget/event path. Identify the lowest boot-deliverable predicate
that distinguishes session/VBUS absence, pullup/soft-disconnect state, missing
connect events, and PHY/link non-entry. Do not name or build a successor
candidate until that static attribution produces one bounded discriminating
observable.
