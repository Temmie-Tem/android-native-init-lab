# S22+ FYG8 P3.35 attended resident-session H0 design

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Status: `H0_DESIGN_ONLY`

## Decision

P3.35 is the smallest useful successor to the P3.34 authenticated two-session
PASS. It will keep one freshly flashed native-PID1 boot available as an
attended, current-boot research session after proving one host close/reopen.
It will not yet promote that image as a reboot-persistent baseline.

This distinction avoids building an A90-sized installation system before the
S22+ listener has proved that it can remain available. P3.35 adds no Magisk
module, Android service, filesystem persistence, interactive PTY, file
transfer, unattended control, generic shell argument, or non-boot payload.

## Reused proof

P3.34 already proves the exact S328/HMAC data plane, two logical sessions on
one device tty descriptor, six fixed BusyBox command results, distinct kernel
nonces, clean framing, and the first console call's return. P3.35 retains that
protocol and child cleanup and changes only the post-proof lifecycle:

1. use a fresh run identity and distinct boot-only AP;
2. complete the two P3.34-shaped sessions;
3. close and reopen the host tty once on the same endpoint and topology;
4. complete one more authenticated fixed-command session;
5. prove that all sessions carry one unchanged, nonzero per-boot identity; and
6. keep the device-side listener waiting for later named sessions.

The P3.34 AP is consumed and is never reused.

## One-F1 resident lease

P3.35 is one attended F1 transaction, not a probe followed by a second flash.
Its fresh approval binds the candidate, exact Magisk rollback, listener and
observer closure, command catalog, duration, action count, endpoint topology,
and recovery owner before candidate intent.

After candidate transfer, any failure or ambiguity before the three-session
reconnect proof immediately selects the already-approved rollback. On proof
success, the ordinary F1 journal remains open at `OBSERVED` and a separate
no-clobber resident lease records
`RESIDENT_SESSION_ACTIVE`. The candidate is not reported `CLOSED`, healthy
Android is not claimed, and no campaign-ledger closure row is written while
the lease remains active.

The initial lease is attended, lasts at most one hour, and permits at most 16
named actions. These are usability bounds, not repeated approval gates.
The operator's original P3.35 approval covers the complete fixed catalog, so
individual actions need no new F1 approval. Each action still receives one
durable intent and one result and is never automatically resent after an
uncertain dispatch.

## Initial named catalog

The first implementation exposes only the three already exercised commands:

- `identity`: `/bin/busybox id`
- `kernel`: `/bin/busybox uname -a`
- `session-nonce`: the fixed P3.35 run-identity echo

The public CLI accepts these names, not a command string, shell fragment,
path, executable, or environment. The private HMAC key remains unpublished.
The device parser's inherited printable-command capability is not promoted as
a device-side allowlist claim; authority is limited by the reviewed host
catalog and exact private binding.

Additional read-only profiles may be added later as small reviewed catalog
deltas. Interactive PTY, arbitrary shell, file transfer, persistent mutation,
package installation, mount, property/service change, and reboot remain out of
scope for P3.35.

## Listener behavior

The device keeps the P3.34 authenticated console and process-group cleanup.
After the initial proof it waits at low duty for another host session on the
same device tty. Expected no-peer or idle timeout outcomes return only to the
wait state. A protocol, authentication, command, child-cleanup, or unexpected
I/O failure parks the listener and cannot replay a command.

The listener creates one fresh nonzero per-boot identity before serving the
first session and authenticates the same value in every later session. The
host binds that value in the lease. A static P3.35 run identity or a new
per-session challenge is not accepted as proof that a later connection still
belongs to the same boot.

Every host action freshly reopens the exact P3.35 lease, candidate identity,
physical topology, endpoint properties, private key receipt, and listener
banner before sending one fixed command tuple. Endpoint or target ambiguity
does not fall back to ADB or another Samsung device.

## Stop and recovery

Explicit operator stop, deadline, action-budget exhaustion, target drift,
unexpected reboot, lost recovery path, or a listener safety failure ends the
lease. The only partition transition then available is the exact P3.35
rollback branch already bound by the original approval. Candidate replay and
a replacement artifact are forbidden.

The durable order is candidate observation, ordinary `OBSERVED` transition,
its `candidate_boot_ready` event, no-clobber lease/guard publication and
directory fsync, then release of the candidate-observer guard and host session
lock. No named action can start before the complete lease exists. An uncertain
action intent does not reopen the lease for more commands; it selects only the
rollback owner.

The lease schema is
`s22plus_fyg8_p335_resident_lease_v1`; it owns the monotonic deadline and a
separate append-only action intent/result journal. Initial proof consumes two
same-FD sessions plus one close/reopen session. Each of the later 16 actions
owns at most one listener session, with no hidden retry or reconnect budget.
These actions exist only inside this still-active P335 F1 lease and are not
independent D1 or standing authority.

After exact rollback and final rooted FYG8 Android health, the original F1 run
may close with one candidate transfer and one rollback transfer, publish its
single result, and append its single ledger row. A host cut while the lease is
active resumes only the retained journal and exact rollback owner; it never
restarts the candidate action or invents success.

## Deferred permanent promotion

A later reboot-persistent `RESIDENT_HEALTHY` baseline would need its own
target-contract terminal, boot-to-boot health proof, recovery owner, and
independent boundary review. P3.35 deliberately does not add that machinery.
Its useful result is a bounded live research session on the current native
boot, followed by the existing rollback closure.

This document grants no D0, D1, F1, device, Odin, or live authority.
