# S22+ P437: exact retained root and rcS progress

Status: **H0_DESIGN_SELECTED_PENDING_SAFETY_REVIEW**. Only S22+ FYG8 is
selected. This prospective design grants no device effect. P432, P433, P434
and P436 remain consumed and Android-healthy; P435 remains unstarted.

## Bounded objective and completion

Prepare the smallest automatic Debian successor that can admit the now-known
historical root exactly and distinguish the rcS fork-record tail, parent wait
and child execution attempt. Keep the Debian initial-PID1 architecture, two
existing protected admissions, two declared writable lifetimes, fixed services,
one NCM attempt, original deadline and physical original-A recovery.

Completion requires a source-bound exact historical table, actual ARM64
producer/consumer and rejection evidence, qualified A/B image bytes, independent
review and a concrete finite attended proposal. A new grant is required only
after that reviewable package exists. No consumed image or grant is reused.

## Existing evidence and exact root accounting

[P436](S22PLUS_AUTOBOOT_EVIDENCE_P436_RUN_2026-10-18.md) authenticated P432's
early file and six-record, 1,024-byte runtime file against its physical build,
with matching boot and nonce identities. The runtime proves installed Debian
PID1 and the rcS hook's successful child fork. It does not prove the child's
exec, rcS completion, services, SSH or the return of the final record's own I/O.

The existing P434 table has 8,971 entries. Adding only that runtime file, at
its sealed path with root-owned 0600 mode, one link, exact size and hash, gives
8,972. With the same four fixed entries and one existing mutable entry, the
expected total is 8,977, matching P434's observed count. Its parent directory
already has the existing bounded mutable rule; no new ancestor is admitted.
This is prospective accounting, not a new physical full-root observation.
P434's `RECOVERY_NOT_PROVED` and its original selected table remain unchanged.

The proposed `post-autoboot-p436-v1` selection contains exactly three historical
rows: P430's early file, P432's early file and P432's runtime file. Their closed
writer/reader provenance and raw bytes must verify before generating a table.
The first two rows retain their original sources. The third uses P436's
authenticated retrieval; it cannot be supplied as an arbitrary caller path.
Historical single-link checks remain additional to table hashes and metadata.
Missing, changed, linked, misowned or extra files fail admission. Existing
finite mutable rules remain unchanged, including canonical boot-count bounds.

Select the automatic lane's existing first protected checker/full-tree
admission before its first write, subject to independent review of this new
selection. A separate read-only N is not selected by this design. This route
does not assume a clean superblock is sufficient: both current admissions
must independently pass their complete checks. P435's narrower requirement
for separate P434 full-root proof remains attached to P435; it is not silently
removed from that prepared candidate. Any prospective replacement requires
explicit common/target/policy adoption and independent review.

## Smallest useful observation

The last P432 runtime record is emitted after the parent receives a successful
fork result, but its timestamp precedes write, fsync, readback and close.
The parent then polls that child and sleeps; the child closes non-stdio
descriptors and attempts `/etc/init.d/rcS`. The retained script resolves through
the installed usr-merged symlinks and executes `/etc/init.d/rc S`. That script
may use its ordinary startpar ordering. None of these later steps is a proved
physical failure cause, so no installed script or service ordering is changed.

Reuse the existing bounded stock-logger observer. Retain its five transition
actors and add only the already existing rcS hook invocation and its fork
child as two distinct actors. No extra process, daemon, manager, persistent
file, writable lifetime or USB prerequisite is introduced. The runlevel hook
keeps its existing durable progress and service checks without new actors.

The rcS parent observes entry/state, the existing fork-boundary function's
BEGIN/RETURN, first wait result, first sleep, first heartbeat, child reaping
and rcS completion. The child observes descriptor cleanup, descriptor-3
absence and its exec attempt/failed return. Successful exec cannot return a
positive syscall result; a pre-exec marker alone is never exec proof.
Immediate errno, wait status and original failure handling must be preserved.

Parent and child have separate measured identities and sequences, with a
verified fork/parent join when both records survive. Inherited source identity
is valid only across the same pre-exec fork; it cannot stand for a later
executable. Each actor retains the 96-record/512-byte/2000-ms limits and the
original absolute deadline. Logging has no surviving descriptor and no
workload gate. Deadline checks after BEGIN must prevent logging from admitting
a fork or exec after the original workload deadline.

The existing local file format, write/synchronization/readback rules and
proof predicates stay unchanged. The fixed post-closure retained-log D0 may
observe the new qualified variant under its same returned-boot health binding.
Raw bytes precede interpretation. Missing or partial retained observations
cannot establish a stall, non-execution, cancellation or recovery authority.

## Validation and adoption

First verify the prospective table and actual retained script/source inputs
with inexpensive H0 checks. Then exercise the real ARM64 automatic path with
the third exact history row, normal service/SSH/shutdown and network-absent
local completion. Retain pre-write rejection checks for dirty state, changed
history and unexpected files, and add missing/changed/linked/wrong-mode runtime
history cases. The original two-file and consumed one-file selections keep
their historical identities and semantics.

Exercise actual rcS parent/child failures and pending observations, including
failed descriptor cleanup, failed exec, child exit, first sleep and the durable
fork-record tail. Verify source/boot/fork joins, malformed or contradictory
records, logging loss, deadline crossing and fd/errno preservation. Test-only
faults must remain confined to declared virtual copies; physical images have
none. Reuse unchanged evidence only with its original source provenance.

Independent review must cover all higher-precedence interactions, the exact
historical admission, reachable owner, new actor bounds and actual image/VM
consumers. Update the common-details hash pin if those details change, without
repinning consumed approvals or historical reviews. No new device owner is
opened by implementation, tests, this report or a capability PASS_GO.
