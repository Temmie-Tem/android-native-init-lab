# S22+ FYG8 P3.25 ACM-primary F1 pass

Date: 2026-09-02 KST

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: `PASS_F1_V2_P325_ACM_PRIMARY_NATIVE_PID1_USB_ARRIVAL_AND_ROLLED_BACK`

## Result

P3.25 is the first S22+ run to retain the exact primary ACM banner. The
candidate observer captured exactly 49 bytes, SHA-256
`72653f08249ec15c01ec44dade168f87910c2bb5718d68465f7fadc3bbbffd7d`,
classified it `accepted`, and durably recorded
`candidate_arrival_proof.proof=true`. The tty-node guard was released normally,
the exact P324 Type-C lane inventory remained single and continuous, and the
candidate Download endpoint was absent during the accepted observation.

This proves arrival of the P3.25 native PID1 ACM publisher and successful USB
data delivery to the host. The operator also observed a normal candidate boot
without a loop. That observation is supportive but is not used in place of the
exact retained receipt.

The retained stock Carrier is separately classified `NO_PROOF_OBSERVER`.
Therefore this pass does not promote a Max77705 scientific result, a causal
MUX result, or the supplemental Carrier path. The proved result is the declared
ACM-primary native-PID1 arrival claim.

## Execution and recovery

The first approved execution stopped before transaction creation because a
host mount rotation changed only the global consumed-registry lock `st_dev`
values. No device command, candidate intent, Download request, Odin session, or
transfer occurred, and that approval was not reused. A reviewed one-shot
host-only rebind preserved the exact registry content and six-record hash chain.
A fresh D0 preparation and fresh exact approval then selected the P3.25 run.

Candidate AP 27,279,401 bytes/SHA-256
`486fd1f2dcb8fbca9f31cb6bce438bb38945cf98e9bb9422f5d5301a7b0abdf4`
transferred exactly once. The first rollback-endpoint measurement failed after
candidate observation; recovery resumed only the durable journal and never
resent the candidate. Exact Magisk rollback AP 23,367,721 bytes/SHA-256
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
then transferred exactly once.

Final rooted FYG8 health passed: Android boot completed, boot animation stopped,
root was verified, the Download endpoint was absent, and the supporting
partition identities matched. The journal is `CLOSED` with 19 records,
candidate/rollback attempts are 1/1, no attempt 2 exists, and
`recovery_required=false`.

## Host result publication

The already-valid live state is 30,011 bytes/SHA-256
`c6094a55993fb3751a153d9eae781a3ea378b2d94ef3dc1fbc8fab9d8b91a3f8`.
The ordinary post-close publisher then stopped because the complete canonical
result is 33,677 bytes, 909 bytes above the shared 32 KiB host record limit.
This was a host reporting failure after device closure, not an experiment or
rollback failure.

The exact-run finalizer
`s22plus_fyg8_p325_closed_result_finalizer.py` reconstructs only this frozen
run and the exact 33,677-byte result under a local 64 KiB publication bound. It
does not alter live state or the shared bound and has no device, ADB, USB,
backend, Odin, candidate, rollback, or replay path. Its six focused tests and
noncreating audit passed; independent review returned
`PASS_GO_P325_CLOSED_RESULT_FINALIZER_H0`.

The published mode-`0400`, single-link `live-result.json` has SHA-256
`c96b7900d9f7fe615a7da889dabb4d5bb58d85029c455bd1d332e274e9e3572c`.
Post-publication audit rederived the same bytes and formal outcome
`p325_acm_primary_native_pid1_usb_arrival_rollback_verified` with zero device
actions.

P3.25 is closed, consumed, and never replayable. A successor should reuse the
proved ACM/PID1 path as evidence, not the consumed candidate or approval.
