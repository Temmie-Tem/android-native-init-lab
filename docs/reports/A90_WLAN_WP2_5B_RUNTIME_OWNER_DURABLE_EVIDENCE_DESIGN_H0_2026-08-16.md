# A90 WP2-5b.2 runtime-owner and durable-evidence H0 design

Date: 2026-08-16
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 execution-boundary design
Device, USB, network, or live command: none
Local `/dev` incident: a shell-quoting error attempted to execute host
`/dev/kmsg` twice; both attempts were denied before any bytes were read
Disposition: design complete H0; runtime implementation remains absent

## Result

WP2-5b.2 fixes the ownership, ordering, durable-publication, receipt, and
crash-reconciliation contract that must surround the existing WP2-5b.1 trace
core. It does not implement the owner, writer, receipt producers, parent
effect dispatcher, qualification, recovery action, or a candidate.

The design preserves four separations:

1. the observer owns the campaign's sole `/dev/kmsg` reader FD and raw trace,
   but has no effect-dispatch authority;
2. the native parent owns qualification, durable effect intent, exact
   dispatch, driver-outcome binding, cleanup, and final health;
3. the journal publisher owns fixed canonical event records, but may never
   reconstruct or repeat an effect; and
4. the host consumer independently parses raw bytes and keeps experiment
   proof, device safety, and workflow state on separate axes.

The permanent `WP2_5B_KMSG_STREAM_COMPLETENESS` invariant remains in force.
The temporary `WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT` gate remains open because
this unit is a design, not a runtime implementation or qualification.

## Consumed-read faults are terminal

The selected `devkmsg_read()` constructs the record, then advances
`user->idx` and `user->seq` before either later failure:

```text
msg = log_from_idx(user->idx)
... render record ...
user->idx = log_next(user->idx)
user->seq++
unlock
if (len > count) return -EINVAL
if (copy_to_user(...)) return -EFAULT
```

Therefore `EINVAL` and `EFAULT` are not retryable reads. In both cases the
selected record is already gone from that reader's cursor. Retrying reads the
next record, not the failed record. A later sequence gap can corroborate the
loss, but it is not guaranteed: there may be no later record because the
consumed record may have been the last record in the epoch.

The runtime owner must consequently apply this exact rule:

- `EINVAL` emits one distinct `FAULT_EINVAL/EINVAL_CURSOR_ADVANCED` frame,
  permanently stops reading that descriptor, and never retries it;
- `EFAULT` emits one `FAULT_EFAULT/EFAULT_CURSOR_ADVANCED` frame, permanently
  stops reading that descriptor, and never retries it;
- either fault before durable effect intent stops with zero effect; either
  fault after intent yields `NO_PROOF_OBSERVER`, preserves no-replay, and
  continues only bounded observation, cleanup, recovery, and final health;
- a later gap never replaces the direct fault receipt; and
- increasing the buffer, seeking, reopening, or switching to `/proc/kmsg`
  cannot recover the consumed record.

The WP2-5b.1 generated vocabulary now retains its existing IDs and adds
`FAULT_EFAULT=10`. This is an append-only vocabulary extension, not a
renumbering of existing trace bytes.

## Exact process and FD ownership

The future runtime is limited to two trusted roles.

### Native parent

The parent alone may:

- bind the exact target, current boot, run, qualification, observer binary,
  trace contract, proof subject, and one fixed effect command;
- claim the private run directory;
- durably publish journal records;
- publish `EFFECT_INTENT` before dispatch and dispatch the effect once;
- obtain and bind the exact dispatch receipt separately from the command-bound
  journal event;
- obtain and bind driver-identity and interface-outcome receipts;
- send the one fixed close token after the driver outcome is bound; and
- perform cleanup, recovery, and final native-health work.

The parent never reads `/dev/kmsg`, writes raw trace frames, shares the campaign
reader FD, or asks the observer to dispatch an effect.

### Observer

The observer alone may:

- open and validate the exact `/dev/kmsg` character device;
- seek once to `SEEK_END` before arming;
- emit the trace header, `ARM`, `RECORD`, terminal `FAULT`, and `END` frames;
- continuously drain until the parent's fixed close token and final
  `EAGAIN`; and
- close its sole reader FD and prove the FD is absent before exit.

The parent creates two `pipe2(O_CLOEXEC)` channels and forks exactly one
observer child. Only the manifest-fixed control/status ends and the already
validated run-directory FD cross one exact static clean exec through one
audited CLOEXEC-clear transition; the observer re-arms CLOEXEC at entry,
validates the FD identities, creates `trace.pending` with `openat()` on the
fixed leaf, and closes the run-directory FD before opening `/dev/kmsg`. The
parent closes every child-side duplicate before accepting readiness. No
dynamic loader, `SCM_RIGHTS`, or pathname reopen substitutes for this
bootstrap.

The static observer ELF is itself executed from one already opened, no-follow
regular-file FD whose owner/mode/link-count/size/SHA-256 and mount identity the
parent validates immediately before fork. The blocked child uses one reviewed
FD-based `execveat(..., AT_EMPTY_PATH)`/equivalent exact-file primitive; the
executable FD closes on successful exec and is absent from the bootstrap FD
set. Runtime support for that exact primitive is a qualification prerequisite.
Path-only `execve`, `/proc/self/fd` re-resolution, an interpreter, dynamic
loading, or reopen-after-hash is forbidden.

After that bootstrap, the observer's exact live FD set is limited to null
stdio, one parent-to-observer fixed control pipe, one observer-to-parent fixed
status pipe, one append-only trace-pending regular-file FD, and one `/dev/kmsg` FD.
No AF_UNIX socket, inherited directory FD, effect/control socket, shell,
or second writer is allowed. “Sole reader” means the one campaign/run FD and
all of its possible duplicates; a pre-existing independent OS reader has a
separate source-proved `devkmsg_user` cursor and cannot move this FD's cursor.
The pipes carry fixed scalar frames only. EOF, an
extra writer, an unknown token, duplicate token, interleaving, or a surviving
duplicate FD is a boundary fault.

The future pipe contract is byte-derived, not ad hoc structs or text. Each
direction has one writer and one reader and a fixed magic/version, big-endian
kind, an unsigned 64-bit sequence starting at zero and advancing by exactly
one for every frame, exact payload length, reserved-zero bytes, and total frame
size no larger than the qualified `PIPE_BUF`. A forward gap, duplicate,
regression, or required next frame after `UINT64_MAX` is terminal; the last
case is detected before writing or accepting another frame. Each frame is
issued by one direct `write()` only after bounded `POLLOUT`; a short write,
unknown return, `EPIPE`, exhausted `EAGAIN`/`EINTR`, partial read at EOF,
extra/trailing byte, unknown kind, or wrong sequence is terminal. The parent
reads and validates complete frames before deriving any journal record, then
durably binds the raw status-frame hash; ephemeral pipe state is never itself
a receipt. The observer has no journal-directory or event-file FD.

The final implementation must bind the observer PID/start identity, exact
executable bytes, scheduler/cgroup placement, FD numbers/flags/identities,
credential/capability set, signal mask/dispositions, and parent relationship.
It must also bind one fixed argv, an empty environment, root/cwd/umask,
supplementary groups, rlimits, affinity, and clean-exec mapping set. Those
values and numeric budgets are not selected by this H0 design.

The child remains at its pre-exec barrier while the parent normalizes and
rereads its scheduling policy/priority, nice value, reset-on-fork state,
affinity/cpuset, I/O priority, uclamp state, and dedicated aggregate cgroup.
The accepted profile must be a measured non-RT/non-deadline policy with a
native parent/recovery reserve and enough bounded service to continuously
drain the qualified record rate. `RLIMIT_RTPRIO=0`, bounded `RLIMIT_RTTIME`,
and no `CAP_SYS_NICE`/`CAP_SYS_RESOURCE` survive. The child cannot enter exec
until those facts and the cgroup/controller identities are bound; unsupported
controls or an inherited FIFO/RR/DEADLINE/high-priority state are `NO_GO`.

The observer is an exclusively owned direct child. Before fork, the parent
blocks SIGCHLD and proves the disposition is default with neither `SIG_IGN`
nor `SA_NOCLDWAIT`. The child remains blocked until its PID/start identity is
registered in one exact waiter reservation that every resident
`waitpid(-1)`/reaper path must honor. No handler, thread, helper, or second
waiter may reap it. The parent retains direct-child ownership, verifies the
zombie/non-reuse invariant when applicable, then waits and reaps only the
reserved identity. SIGCHLD and the resident reaper may return to their exact
prestate only after the reservation is removed. If the current native parent
cannot prove this exclusion, the runtime design is infeasible (`NO_GO`); PID
or start-time comparison after an unintended reap is not a repair.

Any privilege needed to open the exact read-only `/dev/kmsg` FD is bootstrap
only. Before seek, `ARM`, or readiness, the observer must drop every effective,
permitted, inheritable, ambient, and bounding capability, become
non-dumpable, set `RLIMIT_CORE=0`, set `PR_SET_NO_NEW_PRIVS`, and install one
all-ABI fail-closed syscall filter. The final filter permits only the measured
fixed-FD read/poll/write/fsync/lseek/fstat/close/status/exit and bounded
memory/time/signal operations. `lseek`, status/write FDs, and any required
`fcntl` are argument-constrained; `fcntl` may expose only exact read-only
`F_GETFD`/`F_GETFL`, never `F_DUPFD*` or state mutation. Anonymous memory calls
must reject file-backed mappings. The filter rejects every path open, socket,
ioctl, exec, namespace,
mount, ptrace/process-memory, pidfd duplication, keyring, BPF/perf, and effect
dispatch path. Unknown architectures and syscall numbers are fatal. The
parent binds and independently rereads the exact credentials, capability sets,
dumpability, no-new-privileges, seccomp mode, mappings, and FD set before it
accepts confinement. A missing kernel control is `NO_GO`, not a broader
allowlist.

## Runtime ordering

The sole success-path order is below. A qualification or run-directory claim
failure before a private run exists is a zero-effect host decline and creates
no attempt journal. Any failure after `RUN_DIR_CLAIMED` branches immediately
to the branch-specific `TERMINAL_INPUT` rule after blocking new effects; it may
not advance through a success state merely to reach cleanup.

1. `QUALIFIED`: validate all immutable inputs and measured caps without
   opening a device or dispatching an effect.
2. `RUN_DIR_CLAIMED`: open one private, direct, no-symlink run-directory FD
   and prove its exact empty child set.
3. `OBSERVER_EXEC_READY`: complete the exact fork/clean-exec FD transition,
   validate the manifest-fixed bootstrap FD set, and close every unrelated or
   duplicate pipe end in both processes. The exclusive waiter reservation is
   already active; scheduling/cgroup normalization is verified, and the child
   cannot reach bootstrap code before both gates.
4. `TRACE_PENDING_CREATED`: observer creates the one fixed trace-pending regular file
   with `O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`, mode 0600, link count one.
   It opens the file append-only, closes the inherited run-directory FD, and
   proves that directory FD absent.
5. `KMSG_OPENED`: no-follow open `/dev/kmsg` exactly read-only, nonblocking,
   close-on-exec; bind path and FD to one character device with rdev 1:11 and
   stable device/inode/rdev identity.
6. `OBSERVER_CONFINED`: apply the capability, dumpability, core, no-new-privs,
   and all-ABI syscall boundary above; parent independently verifies the exact
   process/FD/mapping state. No later path open or privilege transition is
   permitted.
7. `KMSG_AT_END`: perform exactly `lseek(fd, 0, SEEK_END)` and reread the same
   FD identity/flags.
8. `ARM_PREFIX_DURABLE`: emit header plus `ARM`, fsync the trace-pending FD,
   and report its inode and exact prefix length. The parent hashes exactly
   those prefix bytes through its retained directory FD; later append-only
   records may grow the same inode but cannot rewrite the bound prefix.
9. `OBSERVER_ARMED`: atomically publish and directory-fsync the canonical
   journal record binding that durable prefix. Only now may qualification
   expose the effect-intent transition.
10. `EFFECT_INTENT`: durably publish the exact proof-subject payload. The
   attempt is consumed here; every later prefix has `effectReplayAllowed=false`.
11. `EFFECT_DISPATCHED`: send the one fixed command once. If the exact
    immutable `dispatch-receipt-v1` is available, validate and bind it first,
    then publish the existing journal event with its unchanged payload:
    `SHA256(qualified exact command)`. The event never names the dispatch
    receipt. A missing or uncertain receipt takes the consumed-uncertain
    failure branch and never permits resend or a fabricated event.
12. `DRIVER_OUTCOME_BOUND`: publish the canonical same-run driver-outcome
    receipt after both subordinate receipts validate.
13. `CLOSE_REQUESTED`: parent sends one fixed close token. The observer drains
    until `EAGAIN`; any other terminal read/poll state becomes `FAULT`.
14. `CAPTURE_CLOSED`: observer closes the sole `/dev/kmsg` FD, emits `END`,
    fsyncs and closes the trace-pending FD, sends one fixed closed status, and
    exits. The parent consumes pipe EOF, waits/reaps that exact child, proves
    no observer or reader FD survives, validates the closed pending inode,
    publishes the trace final name without replacement, and durably binds its
    full identity and SHA-256.
15. `TERMINAL_INPUT_BOUND`: publish a separate fixed branch-input file before any
    cleanup. The exact tagged union has a pre-effect arm/decline branch with
    explicit `NOT_INTENDED`/`NOT_RUN` driver and property fields, and a
    post-intent branch with an explicit property-result state. It is either
    `PROPERTY_RESULT_PRESENT_EXACT`, binding the canonical WP2-4 result's
    inode/size/SHA-256, or `PROPERTY_RESULT_MISSING_OR_INVALID`, binding
    absence or the exact invalid input bytes/findings without promoting them.
    Every post-intent branch also binds either the exact immutable
    dispatch-receipt inode/size/SHA-256 or the explicit state
    `MISSING_AFTER_INTENT`; absence is never converted into a receipt. Every
    branch binds the raw journal prefix, effect state, experiment proof state,
    pre-cleanup device-safety/workflow state, original fault, exact cleanup
    intent, and owned identities. The parent publishes the canonical input
    no-replace, fsyncs it and the directory, closes every writable FD to that
    input, and retains its exact inode/size/SHA-256. It is not a seventh journal
    event and never replaces a WP2-4 result or a dispatch receipt.
16. `TERMINAL`: after required cleanup/final-health evidence, publish the
    existing journal event with its unchanged payload binding:
    `SHA256(canonical WP2-4 property result)`. It never names the tagged union.
17. `FINAL_RESULT`: publish a separate generated wrapper that binds the exact
    terminal-input SHA-256, the full raw journal-chain SHA-256, the canonical
    WP2-4 result SHA-256, the dispatch-receipt state and SHA-256 when present,
    cleanup/final-health receipts, effect/proof/safety axes, and the bound
    identities. The host accepts none of the bound objects alone. A lost host
    return may re-emit only these exact final bytes, never repeat a device
    effect. States 16 and 17 require
    `PROPERTY_RESULT_PRESENT_EXACT`. A post-intent
    `PROPERTY_RESULT_MISSING_OR_INVALID` branch may continue bounded cleanup,
    recovery, and final-health observation but publishes only the separately
    generated `RECOVERY_PARKED_PROPERTY_RESULT_UNAVAILABLE` status. That status
    binds the terminal-input SHA-256, full raw journal-chain SHA-256,
    dispatch-receipt state, cleanup/final-health receipts, axes, and identities,
    fixes experiment proof to `NO_PROOF_OBSERVER`, and is neither `TERMINAL`
    nor `FINAL_RESULT`. A pre-effect branch closes with the exact
    `DECLINED_PRE_EFFECT` object outside the attempt journal. Neither branch
    invents a property-bound terminal or final wrapper.

An observer fault does not skip `END`: when framing remains writable, the
single terminal `FAULT` is followed by `END` so the consumer can bind the
bounded partial epoch. A trace-write failure can leave only a truncated
pending file and must never be relabeled as a complete trace.

Control-pipe EOF before normal close is not a wait condition. The observer
emits `FAULT_BOUNDARY`, uses a prequalified parent-EOF close-binding digest,
closes the reader without retry, finishes the bounded partial trace when the
trace writer still works, and exits. A failed or interrupted `close()` is also
terminal and is never retried because descriptor reuse would make a retry
unsafe.

`captureCloseBindingSha256` binds one finite close-policy object before the
run, not a caller-selected late value. The only causes are
`NORMAL_AFTER_DRIVER_OUTCOME`, `FAULT_AFTER_TERMINAL_INPUT`, and
`PARENT_CONTROL_EOF`; the actual cause remains visible in the fault/status and
journal/terminal-input bytes. On a terminal reader fault, the observer emits
the single trace `FAULT`, fsyncs that prefix when the trace writer remains
usable, invalidates and closes the reader exactly once, and emits one fixed
`FAULTED` status binding the pending inode and durable prefix length. It
performs zero later kmsg reads while waiting boundedly on only the control FD.
The parent validates and hashes that exact prefix, first publishes the branch
terminal input, then sends the same fixed close token. A trace write/fsync or
status failure is itself bound as observer loss and never fabricates a durable
fault frame. A missing driver receipt never forces an observation loop or a fake
`DRIVER_OUTCOME_BOUND`; it takes the failure-close branch. Unknown, duplicate,
or out-of-order close causes are boundary faults. If the parent disappears,
control EOF selects the already bound EOF cause and cannot authorize an effect.

A pre-effect arm/read/confinement fault therefore has a durable host-reporting
path: keep `effectState=NOT_INTENDED`, publish the pre-effect `TERMINAL_INPUT`
with the exact observer/journal/partial-trace state, close and reap the
observer, remove only the bound owned prefix, and publish
`DECLINED_PRE_EFFECT` with ordinal zero outside the attempt-journal sequence.
No missing `OBSERVER_ARMED`/intent/dispatch/outcome event is synthesized, no
driver/property receipt is invented, and no effect command becomes reachable.
After `EFFECT_INTENT`, the analogous input records
`effectState=CONSUMED_UNCERTAIN`; later observation and cleanup may improve
device safety but can never change the original effect or proof state.

The separate bindings are deliberate. The frozen WP2-5b.1 contract keeps
`EFFECT_DISPATCHED.payloadSha256 = SHA256(qualified exact command)` and
`TERMINAL.payloadSha256 = SHA256(canonical WP2-4 property result)`. Neither
event names the new sidecar object. The future `FINAL_RESULT` schema/consumer
accepts only `PROPERTY_RESULT_PRESENT_EXACT` and binds the immutable
dispatch-receipt state/digest and terminal-input digest alongside the complete
journal-chain digest. The separate recovery-parked schema accepts only
`PROPERTY_RESULT_MISSING_OR_INVALID` and has no path to either existing journal
event or the final wrapper. The dispatch receipt itself binds
the target, boot, run, command digest, one transport generation/endpoint, one
attempt identity, exact return/result status and bytes or explicit return loss,
and its producer identity. The parent must reread each present sidecar through
the same bound inode and hash immediately before cleanup and final publication;
any writable alias, substitution, command/receipt or input/result digest
crossover, or missing wrapper is `RECOVERY_PARKED`. WP2-5b.3b must generate
both final/recovery schemas and test that the command/event,
dispatch-receipt, terminal-input, and property-result digests or result states
are not interchangeable before any execution qualification.

## Read and poll decision table

| Observation | Cursor meaning | Required action |
|---|---|---|
| positive read, canonical record | exactly one record consumed | append one `RECORD`; continue immediate drain |
| `EAGAIN` after drain | no record consumed | current drain boundary only; wait unless closing |
| `EINTR` before a record result | no proved record consumption | bounded retry under the same call budget; budget exhaustion is `FAULT_BOUNDARY` |
| `EPIPE` or `POLLERR` | retained data was lost/reset | emit `FAULT_EPIPE`; never retry/reopen/fallback |
| `EINVAL` | one record already consumed | emit `FAULT_EINVAL`; never issue another read |
| `EFAULT` | one record already consumed | emit `FAULT_EFAULT`; never issue another read |
| zero-length read, `POLLHUP`, `POLLNVAL`, unknown revents | invalid boundary | emit the exact poll/read/boundary fault; stop reads |
| interrupted/failed reader `close()` | close state uncertain | never retry close; emit/bind boundary uncertainty and exit |
| any other read/poll errno | observer failure | emit `FAULT_READ` or `FAULT_POLL`; stop reads |
| core format/sequence/count/byte rejection | trace invalid | retain the core's terminal fault; stop reads |

The owner does not sleep after one record. It drains until `EAGAIN`, then uses
bounded poll. Neither timeout nor absence of a signature is proof until the
parent-bound close transition and final drain complete.

## Durable raw trace and journal publication

The implementation must use one already-validated private run-directory FD;
no later path re-resolution is allowed. All leaf names are compile-time fixed.
The exact run child set is limited to the pending/final trace, fixed journal
records, fixed subordinate receipts, terminal input, and final or
recovery-parked result.
The directory must be a fixed native, non-shared-storage location owned by the
runtime identity with mode 0700, enumerated no-follow through the bound FD; its
directory link count is never evidence. Qualification binds the filesystem,
mount identity/options, and working `O_EXCL`, hard-link, file-fsync, and
directory-fsync semantics. Unsupported or changed durability semantics are
`NO_GO`, not a rename/overwrite fallback.

Before arming, qualification must also bind one exact storage-reservation
backend and prove capacity for the maximum trace plus every remaining journal,
terminal-input, terminal, cleanup receipt, directory entry, and a separate
native recovery reserve. A `statfs()` snapshot alone is not a reservation.
The selected backend must exclude concurrent consumption or use an exact
quota/preallocation protocol whose artifact, ownership, lifetime, crash
cleanup, and child-set entry are part of the manifest. `ENOSPC`/`EDQUOT` before
intent declines with zero effect; after intent it parks recovery and never
permits replay. The backend and numeric sizes remain unset in H0, so execution
qualification cannot yet pass.

### Trace file

`trace.pending` is the sole long-lived observer-owned mutable trace file. The
observer creates and writes it append-only. Journal, receipt, terminal-input,
and final-wrapper pending leaves may exist only inside their fixed bounded
parent/producer publication transaction and may never become a second trace or
unbounded mutable store. The parent can only inspect the trace through a
separately opened read-only FD after
the observer has fsynced the relevant prefix or closed it. `OBSERVER_ARMED`
binds the fsynced header-plus-ARM prefix and the pending inode, not a future
whole-file hash.

After final drain, the observer fsyncs and closes the pending FD, sends closed
status, and exits. Only after exact wait/reap and zero-reader proof does the
parent publish it. Publication uses an atomic no-replace hard-link from
`trace.pending` to `trace.bin`, then a
directory fsync. Before publication the pending file must be a private regular
file, mode 0600, link count one, and within the qualified cap. During the
published-but-not-cleaned crash prefix, pending and final must be the same
inode with link count exactly two. After unlinking pending and fsyncing the
directory, final must be regular, mode 0600, link count one, exact size, and
exact SHA-256. Any extra hardlink, symlink, special file, inode mismatch,
mutable alias, or unexpected child is a stop.

Raw trace and device receipts remain private evidence. They are never emitted
to stdout, a terminal, or a tracked repository path. Any future host retrieval
requires its own exact filename/size/hash/no-clobber contract and writes only
under `workspace/private/`; this design grants no retrieval action.

### Journal records

Each event is one fixed-name ASCII canonical-JSON file with a trailing newline.
The writer rejects duplicate keys, non-string keys, floats, booleans in integer
fields, noncanonical escapes/numbers/whitespace, extra or missing keys, and
semantic-only equivalence. It writes one fixed pending leaf with
`O_CREAT|O_EXCL|O_NOFOLLOW`, writes all bytes, fsyncs, validates the same FD,
publishes a no-replace hardlink to the final event name, fsyncs the directory,
removes the pending link, fsyncs again, and validates final link count one.

Direct final-name writes, overwrite rename, truncation, append to a published
record, link count above the exact prefix state, or a second writer are
invalid. Journal sequence and previous-record hash are read from raw canonical
bytes, not reconstructed from a permissive JSON object.

## Receipt producer contract

The following producers are separate from the kmsg observer and remain
unimplemented:

- `dispatch-receipt-v1` binds target, boot, run, exact command digest,
  transport generation/endpoint, one attempt identity, producer identity, and
  exact return/result status and bytes or explicit return loss;
- `driver-identity-receipt-v1` binds target, boot, run, qualification,
  driver-init epoch, producer binary, the exact approved read set, and the
  current driver's stable identity;
- `interface-outcome-receipt-v1` binds the same identities plus the exact
  `wlan0` instance/outcome and its linkage to that driver-init epoch; and
- the existing `a90-wp2-5b-driver-outcome-receipt-v1` binds the two receipt
  hashes and normalizes only `WLAN0_UP_EXACT_DRIVER`,
  `MAC_INIT_FAILED_EXACT_SIGNATURE`, or `OTHER_OR_UNPROVED`.

Every receipt uses one compile-time fixed leaf, strict canonical bytes, one
writer, and the same pending-file/no-replace-hardlink/file-fsync/directory-fsync
publication discipline as a journal record. The parent accepts only the final
regular inode at link count one and rereads its exact raw bytes and SHA-256.
The dispatch receipt must be durable before `EFFECT_DISPATCHED`; neither the
known command digest nor an in-memory return may synthesize it.

The dispatch schema must be generated from the final approved exact-command
and transport contract. The driver/interface schemas must be generated from
the final approved read contract. No path, interface name, module string, boot
value, or digest is caller supplied. A read error, disappeared object,
identity change, mixed epoch, unknown field, duplicate receipt, noncanonical
bytes, or disagreement between the two subordinate driver receipts yields no
driver-outcome proof. This design does not invent the final read set before
the runtime integration source exists.

## Crash-prefix reconciliation

| Last durable fact | Effect state | Only allowed continuation |
|---|---|---|
| run directory or trace pending only | zero effect | block the transition, publish pre-effect terminal input, validate/remove exact owned prefix, close `DECLINED_PRE_EFFECT` with zero ordinal |
| `OBSERVER_ARMED` only | zero effect | no dispatch; publish pre-effect terminal input, validate/close observer and owned prefix, then decline |
| `EFFECT_INTENT` without a validated dispatch receipt/event | consumed/uncertain | never dispatch or replay; bind `MISSING_AFTER_INTENT`, observe current state, cleanup/recover, publish original uncertainty |
| dispatch receipt present, `EFFECT_DISPATCHED` event absent | consumed; dispatch receipt bound | validate the same immutable receipt and publish only the uniquely derived command-bound event; never resend |
| `EFFECT_DISPATCHED` without driver outcome | consumed/uncertain | observation and recovery only; no resend; preserve the separate receipt binding |
| driver outcome without closed trace | consumed; trace incomplete | never reopen a proof epoch; close as `NO_PROOF_OBSERVER`, retain driver fact separately, prove final safety |
| trace pending only after effect | consumed; no complete trace | validate bounded partial, never parse as complete, cleanup/recover only |
| pending and final same inode/link count two | consumed; no replay | validate exact bytes, unlink only pending, directory-fsync, continue publication |
| final trace present, `CAPTURE_CLOSED` absent | consumed; no replay | validate exact raw trace and prior journal; publish the missing record only if uniquely derivable |
| pre-effect terminal input present, decline absent | zero effect | verify the pre-effect branch, finish exact cleanup, and publish only `DECLINED_PRE_EFFECT` outside the attempt journal; never publish a property-bound terminal/wrapper |
| post-intent input has `PROPERTY_RESULT_PRESENT_EXACT`, journal terminal absent | consumed; no replay | verify the immutable input and dispatch-receipt state, cleanup/final-health only, publish the unchanged property-bound journal terminal, then the combined final wrapper |
| post-intent input has `PROPERTY_RESULT_MISSING_OR_INVALID` | consumed; proof unavailable | cleanup/recovery/final-health observation only; publish only `RECOVERY_PARKED_PROPERTY_RESULT_UNAVAILABLE`; never publish `TERMINAL` or `FINAL_RESULT` |
| journal terminal present, final wrapper absent | consumed; no replay | validate input + raw journal + result + health and publish only the uniquely derived wrapper |
| final wrapper present, stdout/host return lost | complete | re-emit the exact final-wrapper bytes only |
| recovery-parked status present, stdout/host return lost | consumed; proof unavailable | re-emit the exact recovery-status bytes only; never create a journal terminal, wrapper, or effect |

Every failure path first blocks new effects, durably records the original
failure and cleanup intent with bound identities, and only then removes owned
state. Cleanup results append separately and never overwrite the first fault.
Foreign, malformed, extra, or ambiguous state is `RECOVERY_PARKED`, not a
repair license.

## Required negative corpus

Before execution qualification, hostile tests must include:

- symlink/replaced/wrong-rdev `/dev/kmsg`, changed FD flags, second campaign
  reader, and retained/duplicated campaign FD;
- dynamic/non-clean exec, argv/env/root/cwd/umask/group/rlimit/mapping drift,
  retained capability, dumpable/core-enabled state, missing no-new-privs,
  wrong seccomp architecture, unknown syscall, post-seal path open/socket, and
  a parent/observer confinement-readback mismatch;
- executable path swap, symlink/hardlink/mount drift, wrong exact-file FD,
  missing FD-based exec support, surviving executable FD, interpreter/dynamic
  loader, and path-only or `/proc/self/fd` exec fallback;
- SIGCHLD `SIG_IGN`/`SA_NOCLDWAIT`, unblocked fork/reservation windows,
  resident `waitpid(-1)` theft, alternate waiter/helper reap, premature
  reservation removal, PID reuse, and wrong-child wait status;
- inherited FIFO/RR/DEADLINE/high-priority/nice/affinity/ioprio/uclamp drift,
  wrong or missing cgroup/controller, aggregate resource exhaustion, absent
  native reserve, and child release before scheduler/cgroup readback;
- `EPIPE`, `POLLERR`, `EINVAL`, and `EFAULT`, proving exactly one fault and
  zero subsequent reads for each consumed/lost state;
- fault-frame write/fsync/status cuts, proving the parent binds only a verified
  durable prefix and never invents a missing fault frame;
- `EINTR` exhaustion, zero read, unknown revents, early EOF, close-token
  duplication, wrong writer, parent EOF, interrupted close, child wait/reap,
  and pipe EOF;
- short/partial/trailing pipe frames, wrong magic/version/reserved/length,
  wrong initial sequence, forward gap, duplicate/regressed sequence, counter
  overflow, unknown token, write `EPIPE`, and bounded `EAGAIN`/`EINTR`
  exhaustion, with no journal derivation from an incomplete frame;
- missing/invalid driver receipt followed by the exact failure-close path,
  proving terminal input precedes the close token, no driver outcome is
  fabricated, and no kmsg read follows the terminal fault;
- record gap/duplicate/regression/wrap, malformed canonical text, count/byte
  cap, trace total cap, and trace-writer failure;
- every byte cut of pending trace, hard-link publication, pending unlink, and
  both directory fsyncs;
- shared-storage/wrong-owner/wrong-mode run directories, changed filesystem or
  mount identity, unsupported hard links, false directory-link-count evidence,
  and any stdout/tracked-path raw-evidence sink;
- absent/insufficient storage reservation, concurrent space consumption,
  wrong quota/preallocation identity, and `ENOSPC`/`EDQUOT` at every trace,
  journal, terminal, cleanup, link, unlink, and directory-fsync cut;
- duplicate-key/noncanonical journal bytes, direct-final writes, overwrite,
  extra hardlinks, wrong inode, extra run child, and same-event replay;
- command/event versus dispatch-receipt digest substitution in both directions,
  wrong transport/attempt/producer identity, missing receipt relabeled as
  present, terminal-input/property-result digest substitution in both
  directions, sidecar writable alias or inode swap, journal-only/input-only/
  receipt-only/wrapper-only acceptance, and a wrapper with the wrong raw
  journal-chain hash;
- missing/invalid property result relabeled as `PROPERTY_RESULT_PRESENT_EXACT`,
  `PROPERTY_RESULT_MISSING_OR_INVALID` followed by a journal terminal or final
  wrapper, absent/invalid-byte substitution, and a recovery-parked status
  relabeled as experiment proof;
- mixed run/boot/driver epoch, receipt swapping, missing subordinate receipt,
  driver/interface contradiction, and post-effect identity drift;
- pre-effect failure at every arm/confinement state, proving branch-specific
  terminal input precedes cleanup, driver/property fields remain `NOT_RUN`,
  and the terminal is `DECLINED_PRE_EFFECT` with ordinal zero; and
- every crash prefix above, with assertions that no path invokes the effect
  dispatcher twice or converts observer loss into device refutation.

## Open gates and next implementation split

WP2-5b.2 closes only the H0 design. Implementation should remain split so a
single review surface does not combine effect authority with observation:

1. `WP2-5b.3a`: exact static observer, FD-based exec, exclusive waiter,
   scheduler/cgroup and post-open confinement, generated pipe contract, plus
   syscall-injected host tests;
2. `WP2-5b.3b`: strict raw canonical writer/parser, selected storage
   reservation backend, and crash-prefix fixture;
3. `WP2-5b.3c`: driver/interface receipt producers and exact read-set closure;
4. `WP2-5b.3d`: parent integration with no dispatch API exposed by the
   observer, followed by measured budgets and independent execution review.

The selected runtime paths, numeric caps, scheduling/cgroup reserve, session
count, ordinal budget, candidate integration hashes, recovery binding, and
fresh live authority all remain unset. No implementation subunit may retire
`WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT` alone.

## Source anchors

Matching operator-staged A90 kernel source, read only:

- `kernel/printk/printk.c:930-989` for `devkmsg_read()`;
- `kernel/printk/printk.c:853-861,1052-1083` for one private
  `devkmsg_user` cursor per opened reader file;
- `kernel/printk/printk.c:956-960` for `EPIPE` reset/loss;
- `kernel/printk/printk.c:965-984` for cursor advance before `EINVAL/EFAULT`;
- `kernel/printk/printk.c:991-1024` for per-reader seeks; and
- `fs/proc/kmsg.c:23-57` for the forbidden global-cursor fallback.

Tracked implementation boundary:

- `workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_stream.c`;
- `workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_contract.h`;
- `workspace/public/src/scripts/revalidation/a90_wp2_5b_kmsg_trace_v1.py`;
- `docs/reports/A90_WLAN_WP2_5B_STREAMING_KMSG_OBSERVER_H0_2026-08-16.md`;
  and
- `docs/reports/A90_WLAN_WP2_5B_KMSG_TRACE_CORE_H0_2026-08-16.md`.

## Independent validation

An independent host-only review recomputed the exact ordered 35-file closure
at both start and end as
`7d0b3566f21e7bb4f265615440074a1e92f2bc0c9e55888371ffaad04e3c5fce`
(`1,801,886` bytes) and returned `PASS_H0_DOCUMENTATION_BOUNDARY` with
HIGH/MEDIUM/LOW `0/0/0`.

The review ran the eleven focused suites (`175/175 PASS`), both generated
contract/header checks, touched Python compilation, three JSON parses, host
x86-64 and AArch64 `-Wall -Wextra -Werror` builds plus `file`, and scoped
worktree/cached diff checks. The reviewer reported zero device, `/dev`, USB,
network, other-target, or repository/private-write contact; the approved
operator-staged A90 kernel source was read only and transient artifacts stayed
under `/tmp`.

This validation paragraph is a receipt-only delta after that frozen review. It
changes no execution semantics or authority and requires its own end-to-end
closure rehash before commit.

## Authority

This is H0 design work only. It grants no candidate identity, runtime binary,
observer installation, qualification, D0, D1, F1, effect, property
provisioning, handoff, UFS mutation, recovery action, generation promotion, or
device authority. No A90, S22+, or S20+ device was contacted, and no
other-target evidence was used. The two denied local-host `/dev/kmsg` execution
attempts recorded in the header produced no read, observer, or device effect.
