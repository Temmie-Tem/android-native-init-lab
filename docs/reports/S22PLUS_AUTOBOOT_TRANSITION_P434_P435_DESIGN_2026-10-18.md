# S22+ P434/P435: observe cleanup through installed-init entry

Status: **H0_QUALIFIED; P434_CLOSED_ROOT_NOT_ADMITTED**. The operator requested stronger observation and
preparation of the next experiment. This unit grants no device effect. P432 and
P433 remain consumed and closed healthy; only S22+ FYG8 is selected.

The later [P434 physical run](S22PLUS_JOURNAL_RECOVERY_P434_RUN_2026-10-18.md)
completed strict replay and its read-only checker, but one tree entry remained
outside selected accounting. P434 is consumed and closed Android-healthy;
P435 was not started. The H0 preparation below retains its original evidence
and grants no authority to skip the failed full-root admission.

## Bounded objective

Preserve the existing Debian-owned automatic boot and distinguish file close,
unmount/protection restoration, child settlement, automatic PID1 entry, second
root admission, root activation, mount transition and installed-init entry.
Use production-present authenticated records that remain independently useful
when a later record, persistent file or SSH connection is absent. Do not add a
native manager, daemon, USB prerequisite or another writable lifetime.

Completion means actual ARM64 producer/consumer and failure qualification,
byte-bound physical packaging, independent review and concrete preparation of
the next permitted operation. Physical startup remains contingent on exact
clean-root admission and its own finite attended grant.

## Evidence and present prerequisite

The [P433 read](S22PLUS_AUTOBOOT_EVIDENCE_P433_RUN_2026-10-18.md) authenticated
P432's complete early file through the final record at BOOTTIME 3,565 ms. That
record precedes file close and unmount. The runtime file was absent in the
dirty home-block view, with `state=1 recover=1 orphan=0`. This cannot locate a
failed call or prove post-replay file absence.

P432's retained file helper has only broad cleanup state in its supervisor.
Its automatic entry and witness write their transition trace into a RAM memfd;
without installed SSH that trace is not recovered after physical return.
The pre-change retained-log D0 dispatcher excludes the automatic-boot profile.
Existing VM-only console messages are diagnostic aids, not physical observation.

Prepare P434 as a separate fresh strict-journal-recovery candidate under the
existing recovery lane. Keep the exact pathless replayer, one original intent,
no retry, restored partition RO, separate read-only checker and full root
comparison. Its comparison must bind the two already authenticated historical
files: P430's file and P432's early file. They are immutable inputs, with exact
metadata, size, content hash and closed-owner provenance; no wildcard is added.
An unexpected post-replay runtime file remains a root-comparison failure. It
must be retrieved and qualified separately, never silently admitted or removed.

P435 can be built and tested against that precise expected root. Its physical
startup cannot proceed until separate recovery proves the full selected root
and returns Android healthy. A mere clean superblock, replay exit zero or
Android health cannot substitute for complete root admission. No recovery or
P435 transfer is authorized by this design.

## Selected observation mechanism

Use the stock logger and checked bounded kernel-log transport already present
in the physical boot. Add a fixed optional observer to five existing actors:
the file worker and its existing supervisor, automatic PID1 entry, post-switch
RAM witness and the installed init hook's initial invocation. No new process
is added. Each actor emits a finite set of independently
authenticated BEGIN, RETURN and STOP observations. Records bind the run,
kernel boot, actor, sequence, absolute BOOTTIME, PID/parent and measured producer
executable. The host must match the executable hash to the qualified physical
build; virtual substitutions retain their own identities.

Distinguish the syscall's immediate result/errno from a checked function's
result and from observation failure. Save errno before logging and restore it
afterward. A BEGIN is a pre-call observation, not proof that the kernel entered
the call. A missing RETURN is not proof of a stall or cancellation. An isolated
authenticated RETURN remains useful if its BEGIN was lost. Contradictory or
duplicate authenticated records must not become a complete execution story.

Instrumentation covers file and parent close, unmount, partition RO restore,
post-cleanup checks and RAM-receipt publication. The existing supervisor emits
its independently measured wait outcome and shared completion state, preserving
settlement and publication failure as separate facts. It then covers automatic-entry checks,
second protected admission/checker, root activation, fixed mount moves,
switch-root attempt, actual witness entry, installed-init exec attempt and the
hook's validated installed-PID1 observation immediately after `dh_actual_init`
and before runtime-file creation. A pre-exec marker alone never
proves installed init ran. Existing explicit STOP paths publish their error
through the same physical channel before parking where possible.

The observer is bounded and best effort. It adds no workload gate and cannot
turn a logging failure into a storage failure or successful cleanup. Bound the
number, size and total logging time per actor; retain the existing absolute
device deadline. No descriptor survives an observation call or is carried
across a mount transition. Before and after the fixed `/dev` move, use only the
corresponding fixed kernel-log path; cache checked boot/source measurements
before moving `/proc`. Kernel stalls remain outside userspace cancellation.

The existing early and installed-service files retain their formats, write
bounds and ownership. A third persistent file would depend on the very cleanup
and root transition being diagnosed, so this unit uses the retained kernel log
for that gap while keeping both existing local files. Retention remains an
observed capability, not a guarantee that the last record survives.

## Retrieval, authority and historical compatibility

Extend the existing fixed post-closure D0 dispatcher only for the qualified
observation-enabled automatic image. It must bind the closed owner, exact
returned Android boot, reviewed sources and before/after Android health, then
perform its unchanged bounded `/proc/last_kmsg` read. Save raw bytes before
decoding. Run/boot/source joins, partial channels and observation limits must
remain explicit; no arbitrary read or pre-closure acquisition is added.

Review the common/target interactions for the exact two historical inputs and
the retained-log selection. Preserve P432's old producer shape and P433's old
review and captured evidence; new observation and recovery use new capability
records. Neither a new review nor readiness renews any consumed grant.

## Qualification

Use actual producer code in real ARM64 VMs and independently parse its emitted
records. Cover normal completion, file-close/unmount/RO/post-check failures,
missing or invalid RAM receipt, second-admission failure, root activation and
mount-move failure, pre-exec versus post-exec evidence, invalid installed-init
identity, logging loss/partial records and a pending call without a fabricated
return. Preserve original fault errno and settlement evidence. Demonstrate
that logging bounds and failure do not introduce a retry or new workload gate.

Qualify the recovery post-comparison against both exact historical files and
reject changed, missing, linked or unexpected files, including a runtime file
appearing after replay. Keep replay/checker/complete-root outcomes separate.
Reuse unchanged strict-replayer validation, while testing the changed consumer
and actual packaged table. Validate real A/B archives and source closures;
cross-compilation alone is insufficient.

Applicable checklist: ABI/IO for actual calls, logging limits and fd lifetimes;
SEMANTIC/WIRE for pre-call, return, error and lost-channel distinctions;
PERSIST/ROUTE/ARTIFACT for production presence and actual retrieval; AUDIT for
the exact P432/P433 evidence; RETURN for one original-A closure. Display and
kernel changes are outside this unit. Independent review must resolve concrete
findings before any capability is declared ready.

## Implementation and observed validation

The implementation adds an optional measured five-actor observer, a shared
fixed stage declaration and an independent retained-log consumer. Existing
record formats and writable lifetimes are unchanged. The recovery successor
selects two exact historical table rows; its strict replay tool is unchanged.

Independent instrumentation review found and resolved two timing defects:
BEGIN logging could cross the workload deadline, and executable measurement
could exceed the actor logging budget. Actual-header host and static ARM64
harnesses now preserve single-call/errno/fd behavior and bound settled short
reads to 2000 ms. These controlled I/O checks are distinct from kernel VM tests.

Actual ARM64 normal and network-absent executions produced 103 authenticated
transition records across all five actors. Their initial decoder rejected the
installed hook's observed intermediate-shell parent. The corrected consumer
retains the measured parent and relies on the hook's actual installed-PID1
check. Duplicate or contradictory stage lifecycles suppress aggregate claims;
pre-exec evidence and absent returns remain distinct from completed execution.

The new recovery comparison was exercised after actual strict replay and its
separate checker. Exact files and the canonical maximum count pass; missing,
changed, linked, wrong-mode or unexpected runtime files and noncanonical count
are rejected. Missing/link/count admission errors retain the owner's original
incomplete `NO_PROOF` outcome and physical-return requirement. They were not
converted into complete recovery results to satisfy the VM harness.

The final automatic-boot corpus passes all 30 ARM64 VM cases, including the
pending-call and logger-loss cases. Nine selected recovery VM cases pass their
expected positive or negative predicates. These use ARM64 virtual hardware
with declared Samsung platform substitutions; they do not prove physical
Samsung boot, retention or installed services. The 76 focused host tests
(15 transition, 24 automatic-boot/retention, eight recovery, 17 file-first and
12 repository-boundary tests), touched-Python compilation and whitespace
checks pass.

The actual P434 image initially failed the V3 consumer because its top-level
runtime selection retained the legacy journal binding. The builder now carries
the selected recovery declaration through that binding. Fresh A/B packaging
and the actual consumer pass; helper, replay/checker and comparison-table
bytes are unchanged. The rejected package is retained privately, not promoted.
Independent P434 review passes against the exact 139 host and 169 runtime
sources, including actual AP/CPIO bytes and the nine recovery cases.

H0 preparation produced a concrete P434 offline proposal for one 1800-second
attended operation. Its pre-execution status was `READY_H0_PRELIVE_ONLY`, with
no grant, current connected health, current root admission or image transfer.
P435's final A/B package and actual V3 image consumer also pass. Its independent
review binds the same 139 host sources, 146 runtime sources, actual AP/boot/CPIO
and all 30 cases through the unmodified production qualification consumer.
The separate per-case audit rederives raw authenticated records and checks the
actual virtual archives and unchanged disk bytes outside native_data.

The new [P434 capability](../../workspace/public/src/device-action/bindings/s22plus_native_journal_recovery_p434_review.json)
and [P435 capability](../../workspace/public/src/device-action/bindings/s22plus_debian_autoboot_p435_review.json)
are independently `PASS_GO`, with no remaining findings and no device
authority. Old capability files retain their original provenance. The exact
365-file union of reviewed host/runtime sources and both capability records
is preserved privately. Review binds those actual working-tree bytes;
pre-existing unrelated changes are excluded from this unit's commit.

That preparation selected P434 as the first device operation. P435 has a
qualified image, but no live task or grant is prepared before complete
selected-root proof and healthy Android closure. Unexpected post-replay files
still stop admission. The linked physical report owns P434's later result and
consumed grant; its failed full-root admission keeps P435 ineligible. Fresh
exact attended authority and current machine checks remain required for each
lane. The H0 preparation itself performed no device action. The physical
close-to-init stop location remains unknown; A90 and S20+ were untouched.
