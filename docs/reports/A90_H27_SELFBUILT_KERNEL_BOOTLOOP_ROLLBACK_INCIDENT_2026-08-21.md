# A90 H27 self-built-kernel boot-loop and rollback incident — 2026-08-21

## Disposition

`H27 FAILED / RECOVERY_REQUIRED`, followed by an exact successful V2321
rollback and healthy Native return. The H27 failure cause is **unproved**.
Candidate replay is forbidden.

## Candidate result

The fresh attended H27 run passed exact H24 preflight and approval. In TWRP,
the reviewed helper then completed all boot-transfer integrity steps for the
58,368,000-byte H27 candidate:

- sealed local copy and SHA-256 verification;
- `adb push` and remote SHA-256 verification;
- one boot-partition write;
- boot-prefix readback matching the exact candidate SHA-256.

The helper's one-shot TWRP System reboot observation was uncertain and it did
not resend. A90 remained in TWRP. The operator then selected physical
**Reboot > System**. H27 did not reach a healthy Native terminal: the device
boot-looped and returned to recovery.

The minimal owner had already durably closed
`RECOVERY_REQUIRED / ROLLBACK_HEALTH_UNPROVED`. Its automatic rollback helper
had stopped before transfer because recovery ADB was already present. Thus the
candidate boot write was proved, while automatic rollback write count remained
zero.

## Recovery

Recovery continued from the durable rollback intent with the exact prebound
V2321 artifact. The checked helper selected only the exact A90 recovery
endpoint and proved:

- local V2321 size `60,882,944` and exact SHA-256;
- sealed copy, push, and remote SHA-256;
- one boot-partition rollback write;
- boot-prefix readback matching the exact V2321 SHA-256;
- TWRP System script completion and recovery exit;
- Native version `0.9.285`, build `v2321-usb-clean-identity-rodata`;
- self-test `pass=11 warn=1 fail=0`.

The separately connected Samsung endpoint remained outside the selected A90
transport and received no command.

This was a recovery deviation: the exact rollback continuation used the
reviewed `native_init_flash.py` directly because the minimal owner had already
consumed a no-transfer rollback-helper result and exposed no recovery-resume
action. The rollback artifact, target, partition, hashes, and helper were the
ones bound by the attended approval; no candidate retry or non-boot write was
performed.

## Evidence limits and next work

The final standalone `status` observation suffered serial framing loss and is
not evidence for pstore contents. Consequently no kernel panic, RKP/CFP,
ramdisk, init, or early-userspace cause is inferred here.

Before another A90 F1:

1. keep the failed H27 candidate guard consumed;
2. close the retained active-run guard only through the reviewed terminal-only
   recovery receipt after a fresh exact V2321 health observation;
3. retain the repaired owner path that lets an already-present bound recovery
   endpoint continue the same untransferred rollback attempt without another
   Native recovery request;
4. analyze any separately retrieved complete H27 boot evidence at H0; and
5. use a byte-distinct, independently qualified future candidate only after the
   failure cause or observation gap is bounded.

## Host-only repair status

The two missing mechanisms are implemented at H0 but are not active. The fixed
postrollback reconciler accepts no input, preserves the external rollback
outcome as unproved, requires fresh exact V2321 health, publishes an
append-only recovery closure, removes only the active-run guard, and leaves the
H27 candidate guard consumed. The ordinary rollback adapter now selects one
strict mode that reuses an already-present bound A90 recovery ADB endpoint or,
only when no recovery endpoint exists, sends the Native recovery request once.

Focused host tests pass. An independent Luna MAX full review closed the final
13-file execution closure
`e58746ea93270c43a28db5df20695a61a687eec942a5a665f562f4fe5173f077`
as `PASS_GO`, HIGH/MEDIUM/LOW `0/0/0`. The review found and forced repair of
guard-publication races, strict recovery error handling, hook symlink drift,
and unobserved fresh-state claims before passing. No guard, journal, device,
approval, candidate, or live authority was changed by this H0 repair or review.

## Connected terminal closure

One separately authorized connected read-only D0 ran the fixed postrollback
reconciler exactly once. It re-proved Native V2321 `0.9.285` with build
`v2321-usb-clean-identity-rodata`, healthy state, and recovery availability,
then appended canonical journal record 41 at SHA-256
`4d1da970b34d2a3cc9c6cce20858b0d8971a13a6ec057b5615fb1646a0b18930`.
The resulting terminal decision is
`V2321_HEALTHY_EXTERNAL_ROLLBACK_OUTCOME_UNPROVED`: candidate and rollback
replay are false, the external rollback outcome remains unproved, and no fresh
candidate-state absence is inferred.

The reconciler released only the active H27 guard. The exact consumed H27
candidate guard remains present. The other Samsung endpoint was inventoried
but received no command. This D0 used the existing Native ACM bridge and sent
no ADB command, reboot, payload, partition transfer, or F1 action.

The H27 recovery gap is now terminally closed without relabeling rollback
provenance or the still-unproved H27 boot-loop cause. H28 remains H0-only and
requires its own qualification, minimal manifest, connected D0, and fresh
attended approval before any F1.
