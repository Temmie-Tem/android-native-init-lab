# S22+ FYG8 P2.37 E1A F1 live pass

Date: 2026-07-23 KST
Tier: F1
Status: `PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK`
F1 authority: consumed; none active

## Result

A fresh host closure and connected read-only D0 preparation bound one exact
P2.34 E1A boot-only candidate, one exact Magisk rollback, one healthy attended
S22+ target, and the repaired USBFS-arrival execution closure. The operator
supplied the exact approval once.

The candidate and rollback each completed one Odin boot-only transfer. The
operator observed no candidate boot loop and entered physical Download mode
after the bounded candidate observation. The runner then transferred the
preapproved rollback and verified final Android health. The durable result
closed with no recovery requirement.

## E1A Evidence

Two rollback-time `/proc/last_kmsg` reads were byte-identical. The strict P2.34
decoder found exactly one related record and classified it as
`E1A_SUCCESS_ONE_OR_MORE_BOOTS`:

- profile E1A and the exact candidate-bound run identity;
- active A/B generation 9 at terminal stage `E1A_SUCCESS` (`0x2f`), outcome
  success, zero detail;
- valid fallback generation 8 at `CHILD_REAPED` (`0x22`);
- one exact record and one family record;
- zero UNSAT, failure, foreign, historical, malformed, delimiter-mismatch, or
  partial records; and
- no integrity issue or fallback recovery.

Together with the independently closed source and artifact contract, terminal
E1A success proves this candidate's PID 1 path completed procfs, sysfs, dev
tmpfs, and run tmpfs mounts and readbacks, verified the required device node,
executed the static child, verified its exact token, and reaped it.

This does not prove watchdog-module loading, platform bind, UDC, ACM bytes,
NCM, a shell, or Debian.

## Process Closure

- Candidate transfer: `odin_transfer_completed`.
- Candidate completed: true.
- Rollback transfer: `odin_transfer_completed`.
- Rollback completed: true.
- Final health verified: true.
- Marker accepted: true.
- Journal state: `CLOSED`.
- Timeline: all eight canonical events in order.
- Final Android: boot complete, boot animation stopped, FYG8 kernel, Magisk
  root verified, Odin endpoint absent.

The interactive rollback instruction preceded the final JSON on stdout in this
run. The durable result was recovered without repeating any device transition
and passed `validate_live_result()` against the closed journal. The host-only
follow-up moves that instruction to stderr so later stdout remains one JSON
document; a focused regression covers the stream separation.

Host follow-up validation passed Python compilation and the 152-test F1,
USBFS-transition, measured-identity, evidence, and manifest regression set. An
independent `gpt-5.6-sol` high-reasoning review found no change to device,
journal, approval, fail-closed, or recovery semantics and returned `GO`.

The private manifest, approval binding, raw retained reads, Odin output, and
journal remain under `workspace/private/`. This report grants no new live
authority.

## Next Gate

E1A is complete. The next bounded unit is H0 design and artifact preparation
for E1B, which must repeat the full E1A path and then prove the five watchdog
modules before its own terminal success. Any later F1 requires a new candidate,
fresh H0 closure, connected D0 preparation, and fresh exact approval.
