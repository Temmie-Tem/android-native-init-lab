# A90 V3406 Phase 2 Display F1 Closed No-Proof

Date: 2026-07-31

Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

## Decision

Run `a90-v3406-debian-display-f1-20260731-02` is closed. It completed one
checked boot-only candidate transfer, one handoff, one exact V2321 rollback,
and final V2321 health verification. The candidate was not replayed. No
non-boot partition was written, and no command was sent to the separately
connected S22+.

The run adds valid mechanism-level evidence but does not satisfy the atomic
Phase 2 display F1 acceptance condition. Debian sysvinit became PID 1 and the
native display release completed. The Debian presenter then exhausted three
attempts with `rc=1`, the operator observed a black screen, and the candidate
did not return within the bounded return contract. Display acquisition and the
overall F1 proof therefore remain false.

All F1 and attended-continuation acknowledgements for this run are consumed
and non-reusable. No A90 live authority remains.

## Durable Transaction Result

The append-only journal closed with:

- candidate transfer count `1`;
- candidate replay `false`;
- candidate transfer uncertainty `false`;
- rollback transfer count `1`;
- final health restored `true`;
- Debian PID1 atomic-result field `false`;
- display acquisition proven `false`; and
- status `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.

The canonical eight-event timeline is complete from `live_session_start`
through `live_session_end`. Raw flash logs, the structured observation, the
journal, the result, and the timeline remain private under the run directory.

## Candidate and Handoff Evidence

The exact V3404-derived candidate booted as native-init `0.11.161` with the
expected build identity and selftest `fail=0`. Before handoff the runner
revalidated the exact immutable source, absent work copy, clean pstore, exact
target, candidate health, and USB-local NCM route.

The one handoff transcript proves:

- initial, post-display-cleanup, work-copy, and post-copy-source hashes all
  matched the manifest-bound source;
- native KMS teardown returned `rc=0`, dropped DRM master, closed the native
  descriptor, and left zero PID 1 and other-process DRM descriptors;
- the native release marker was written into the verified work root;
- the loop root mounted and `/sbin/init` was executable; and
- `exec_switch_root_now` was reached.

USB-local Dropbear observation then read:

- `pid1_comm=init`;
- `proc1_exe=/usr/sbin/init`;
- `dropbear_started=1`;
- an exact native release marker; and
- the terminal display failure marker with `attempt=3` and `rc=1`.

These lines establish a real switch-root-to-Debian PID1 subproof and a real
native display-release subproof. They do not establish Debian display
acquisition or visible output.

## Display Failure

The Debian presenter did not publish the ready marker. It published the
bounded terminal failure marker after its third attempt with `rc=1`. The
operator independently reported that the screen was off. No visible-display
confirmation token was opened or accepted.

The retained work image is the only authoritative runtime filesystem evidence
for the presenter failure. Preserve it until a later read-only extraction or
equivalent host-side reproduction identifies the exact failing DRM operation.
Do not remove it merely to prepare another run.

## Observer CRLF Defect

The structured observer additionally reported:

`native KMS release success line is absent`

That classification is a host parser defect, not the device result. The
preserved handoff transcript contains the exact expected success line, but ACM
transport text is CRLF-terminated. The Phase 2D regular expression anchors the
line immediately before `\n` and does not accept the preceding `\r`.

A host-only replay produced:

```text
crlf_count 34
raw ContractError native KMS release success line is absent
normalized PASS
```

This defect explains why the closed structured result does not retain the
otherwise valid Debian PID1/native-release subproof. It does not explain the
presenter `rc=1`, the black screen, or the missing bounded return, and it does
not permit retroactive promotion of the F1 result.

## Return and Rollback

The return observer ended with `A90P1 END marker not found` and no bounded
candidate-return proof. The exact A90 native USB identity reappeared shortly
after the observation timeout, permitting the pre-authorized rollback through
the checked `from-native` route. A late reappearance is recovery evidence, not
bounded-return proof.

The rollback helper wrote and read back the exact V2321 boot once, rebooted,
and verified V2321 selftest `fail=0`. A later native channel check corrupted an
exact `hide` frame after the rollback had already been durably recorded as
flashed. Rollback recovery resumed from that journal state, did not reflash,
performed only final-health verification, and closed the transaction with:

- version `0.9.285`;
- build `v2321-usb-clean-identity-rodata`;
- selftest `fail=0`; and
- pstore entries `0`.

## Next Safe Unit

Remain H0. Before any new A90 candidate or approval:

1. make the Phase 2D display observer transport-normalize CRLF or explicitly
   accept it, add the preserved live line shape as a redacted regression
   fixture, and independently review the changed execution-critical closure;
2. diagnose presenter attempt-3 `rc=1` from preserved work-image evidence or a
   host-equivalent DRM-contract reproduction;
3. diagnose the bounded-return framing/deadline miss without increasing the
   deadline merely to turn the existing observation into a pass; and
4. separately plan retained-work cleanup only after its evidence has been
   preserved and reviewed.

No next unit may reuse this candidate transfer, handoff, approval, attended
continuation, or rollback transition.
