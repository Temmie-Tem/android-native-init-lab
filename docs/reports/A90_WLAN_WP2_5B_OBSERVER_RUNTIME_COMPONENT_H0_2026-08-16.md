# A90 WLAN WP2-5b.3a observer runtime component — H0

Date: 2026-08-16
Target: Samsung Galaxy A90 5G only
Status: `H0_COMPONENT_IMPLEMENTED_EXECUTION_QUALIFICATION_ABSENT`
Disposition: host-only component boundary; no live authority

## Outcome

WP2-5b.3a now has an effect-free static observer source, a generated scalar
pipe contract/header, an exact-file exec transition core, an exclusive waiter
reservation core, a launch-readback validation core, post-open confinement
source, and syscall-injected host tests. The component consumes no device
ordinal and exposes no effect, journal, receipt, property, handoff, recovery,
or installation API.

This implementation does **not** retire
`WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT`. No selected runtime profile, parent
integration, static target binary receipt, live kernel qualification, or
independent execution review exists. The durable final-name publication writer
and storage-reservation/parser owner remain absent, as do the driver/interface
receipt producers and the no-replay parent state machine.

device ordinals consumed: 0. Device, `/dev`, USB, network, and
`workspace/private` contact: 0.

## Generated boundary

The generator
`workspace/public/src/scripts/revalidation/a90_wp2_5b_observer_runtime_v1.py`
produces both:

- `schema/a90-wp2-5b-observer-runtime-v1.json`, which fixes H0 authority,
  source pins, the pipe grammar, launch/waiter/exec/confinement boundaries,
  implementation state, and next sequencing constraint; and
- `workspace/public/src/native-init/helpers/a90_wp2_5b_kmsg_owner.h`, which
  gives the C implementation the same constants, structs, and public API.

The generated contract pins the already reviewed WP2-5b.1 schema, header,
encoder core, and generator, plus the current 3a observer source and injected C
fixture. Its semantic validator rebuilds the full expected object from those
pinned bytes; changing an authority bit, descriptor, pipe rule, confinement
rule, observer source, or fixture cannot pass as an equivalent contract.

The two pipe directions each have one writer and reader. Frames use the fixed
`A90O3A1\0` magic, version 1, big-endian 24-byte header, reserved zero, and a
64-bit sequence beginning at zero and advancing by exactly one. The largest
frame is 228 bytes, below the contract's 512-byte atomic-write minimum. START,
CLOSE, ARMED, FAULTED, and CLOSED have exact payload sizes and cardinalities.
The observer accepts a CLOSE only when the control writer then reaches clean
EOF with no queued byte, preventing a later or duplicate token from being
laundered through closure. An explicit normal CLOSE is valid only before any
terminal observer fault, while an explicit fault CLOSE is valid only after the
FAULTED state. Parent control EOF remains the separately bound implicit cause.
Either explicit cause/state mismatch preserves the bounded fault prefix but
cannot emit END or CLOSED. The generated combined transcript validator applies
the same correlation instead of validating the control and status directions
as unrelated streams. After START, any CLOSE frame, header, payload, reserved,
cause, cardinality, or clean-writer-EOF failure permanently poisons the control
session: no later token and no subsequent EOF can resynchronize it or grant
closure authority.

## Observer process boundary

`a90_wp2_5b_kmsg_owner.c` implements only the observer side of the reviewed
WP2-5b.2 state machine:

1. re-arm `FD_CLOEXEC` on the fixed control, status, and run-directory FDs,
   while requiring the two scalar pipe ends to remain nonblocking;
2. prove the manifest exec FD is absent and validate null stdio plus the fixed
   pipe/directory identities and access modes;
3. parse exactly one generated START frame;
4. create `trace.pending` through the inherited directory FD with
   `O_WRONLY|O_APPEND|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`, mode 0600, link
   count one, and zero initial length;
5. close the directory FD before opening `/dev/kmsg` read-only, nonblocking,
   no-follow, and close-on-exec;
6. bind the trace and kmsg device/inode identities and exact kmsg rdev 1:11;
7. apply post-open confinement, perform exactly one `SEEK_END`, and re-read the
   same kmsg FD identity and flags;
8. emit and fsync the WP2-5b.1 header/ARM prefix before ARMED status;
9. drain records until an exact CLOSE or a terminal fault; and
10. close the sole kmsg FD without retry, emit END, fsync and close the trace,
    send CLOSED, then close the scalar pipes.

The status payload binds the trace device/inode, kmsg device/inode/rdev,
last successfully fsynced durable byte length, fault tuple, and bounded
auxiliary value. Written-but-unfsynced bytes are never reported as durable.
When the trace
core detects malformed text, sequence drift, or a count/byte cap, the owner
extracts the exact emitted fault tuple, fsyncs that prefix, invalidates and
closes the sole kmsg FD exactly once, and only then sends the same reason in
FAULTED. The stream-core fault adoption path advances the bound durable length
to that successful fault-prefix fsync before sending FAULTED; it cannot reuse
the older ARMED length. `EPIPE`, `POLLERR`, `EINVAL`, and `EFAULT` are terminal; there is no
kmsg read afterward. The post-fault control-only wait consumes an exact
START-bound poll-call budget and exits with the bounded ARMED/FAULTED prefix
if the parent remains alive without sending CLOSE. In particular,
consumed-record `EINVAL` and `EFAULT` are never retried.
If the exact-once reader close itself fails or is interrupted on any fault,
normal-CLOSE, or parent-EOF path, the local FD is invalidated, a boundary fault
is appended and fsynced only when that remains safe, no FAULTED, END, or CLOSED
status is emitted, no control wait occurs, and the observer returns immediately
so process teardown closes any kernel FD whose close state remained uncertain.
Likewise, fault-frame write/fsync failure or a failed FAULTED status write exits
immediately after the reader-close attempt; it performs no control wait and
cannot later emit END or CLOSED.
END write, final trace fsync, trace close, or CLOSED-status write failure also
returns without a complete CLOSED status. Only a fully fsynced END and
successful trace close can precede CLOSED. A CLOSED without a preceding
FAULTED status must carry the all-zero fault tuple; the combined validator
rejects a nonzero finalization fault masquerading as a successful close. The
durable length strictly increases from ARMED to optional FAULTED to CLOSED;
equality is impossible because each transition fsyncs a nonempty new frame and
is rejected as stale evidence.

## Clean exec, scheduler, and waiter gates

The exec helper clears and rereads CLOEXEC only for FDs 3, 4, and 5, calls the
already-open FD 6 with `execveat(..., AT_EMPTY_PATH)`, the single fixed argv,
and an empty environment, and re-arms and rereads every inherited FD if exec
returns, including a hostile impossible-success return in the injected
fixture. Path exec, `/proc/self/fd` resolution, interpreter, and loader fallback
are absent.

The launch-readback validation core accepts a parent-produced snapshot only
when it carries positive bindings for SCHED_OTHER/priority
zero/reset-on-fork, nonnegative qualified nice, affinity/cpuset, I/O priority,
uclamp, cgroup and native reserve, RT rlimits, capabilities, SIGCHLD state,
waiter reservation, static ELF identity, maps, FD set, argv/environment,
null stdio, root/cwd/umask, credentials/groups/rlimits, signal state, observer
and parent identities. Variable byte sets are represented by nonzero SHA-256
bindings; a boolean or missing field is rejected. It does not collect or
normalize those facts; parent integration remains absent. Numeric profile
values and a cgroup backend remain deliberately unselected until measurement.

The waiter core refuses a nonempty/stale reservation, binds one PID/starttime,
makes the generic reaper skip only that exact identity, permits one exact reap,
and releases only after it. Resident-reaper integration is not part of this
unit.

## Post-open confinement

The real confinement path requires empty supplementary groups and exact real,
effective, and saved UID/GID. It sets and rereads `RLIMIT_CORE=0` and
non-dumpable state, drops and rereads every kernel-supported bounding
capability plus effective/permitted/inheritable/ambient sets, sets and rereads
`PR_SET_NO_NEW_PRIVS`, and then installs an architecture-checked default-kill
seccomp filter.

The filter is built with the actual trace and kmsg FD numbers fixed at seal
time. It permits only the measured read/write/close/fstat/fsync/fcntl/lseek,
poll, signal-return, and exit calls. Read/write/close/fstat/fsync/lseek/fcntl
are FD- and, where relevant, argument-constrained. `F_DUPFD*`, fcntl mutation,
path open, socket, ioctl, exec, namespace, mount, ptrace/process-memory,
pidfd duplication, keyring, BPF, perf, and unknown architecture/syscall paths
fall through to kill. Real post-seal wrappers use direct fixed syscalls rather
than allowing libc to select a wider syscall surface.

This source is not proof that the A90 live kernel accepts the filter or that a
qualified static observer can sustain the future measured rate. Those remain
execution-qualification evidence, not H0 assumptions.

## Host validation

The focused Python suite checks generated-byte equality, semantic drift,
strict type handling, every pipe field, counter/order/cardinality rules,
authority closure, source surface, and the complete launch snapshot. Its C
fixture drives the same owner state machine through injected open/fstat/fcntl/
lseek/read/write/poll/fsync/confinement calls without opening a host device.
That alternate-ops entry point is compiled only under
`A90_WP2_5B_HOST_TESTING`; the production header/source exports no callable
confinement-bypass runner.

The fixture covers a healthy record, `EPIPE`, `POLLERR`, consumed `EINVAL`,
consumed `EFAULT`, read/poll `EINTR` exhaustion, zero/unknown-error reads,
poll failure and HUP, sequence gap, duplicate close, partial close at EOF,
parent EOF, a live parent that never sends post-fault CLOSE, interrupted reader
close with zero retry/wait/status, fault-prefix fsync failure with immediate
reader close and no later wait/status, failed FAULTED status with immediate
exit, normal-CLOSE and parent-EOF finalization
close uncertainty with no END/terminal status, wrong kmsg rdev/flags,
both hostile close-cause substitutions (FAULTED plus normal CLOSE and a
nonfaulted observer plus fault CLOSE) with no END/CLOSED,
unknown-cause, reserved-nonzero, unknown-kind, partial, and already-faulted
invalid-first CLOSE followed by a syntactically valid second FAULT CLOSE, all
with permanent protocol poison and no END/CLOSED,
partial END write, final fsync `ENOSPC`/`EIO`/`EINTR`, interrupted trace close,
and short CLOSED status with last-fsync-only durability and no complete CLOSED,
plus malformed record, sequence gap, count cap, and byte cap with a FAULTED
durable length strictly beyond ARMED and equal to the fsynced FAULT prefix,
confinement/seek/ARM-fsync failure, retained exec FD, short status write,
failed-exec CLOEXEC restoration, stale/exact waiter ownership,
launch-snapshot drift, and direct interpretation of the generated seccomp
bytecode over allowed and forbidden syscall/FD/argument tuples. It asserts one
terminal fault, immediate exact-once reader close before FAULTED, zero reads
after fault, the exact bounded control-only poll budget, exact status ordering,
one seek, one confinement transition, and no surviving trace or kmsg FD. The
fixture is compiled and run with undefined-behaviour
sanitization. The owner and fixture also cross-compile warning-clean as
AArch64 relocatable objects.

Validation receipts are recorded after the final current-byte run below; no
test may be described as live target qualification.

## Host validation and independent review receipt

The final pre-receipt public closure contained 33 exact ordered files,
947,065 bytes, with aggregate SHA-256
`51066f3ba24645a8e5590fe9fb257edab4360e55f6d4e7f03d673c5e14f1b842`.
Its start and end hashes matched.

The final local host run passed 12 public A90 modules, 173/173 tests. The
generated contract/header checks passed 2/2; touched Python compiled; four
JSON documents parsed; host and AArch64 owner/fixture objects were
warning-clean; `file` confirmed the expected architectures; the host injected
state machine passed normal, ASan/UBSan, and `-fanalyzer` validation; and the
production symbol table excluded the injected-ops runner. Scoped diff checks
were clean.

The independent public-only review returned
`PASS_H0_DOCUMENTATION_BOUNDARY`, HIGH 0 / MEDIUM 0 / LOW 0. Its permitted
public suites passed 107/107 and generator checks passed 2/2. An independent
nine-case status-length matrix rejected zero ARMED, equal adjacent lengths
(including maximum-equals-maximum), regression, and incomplete prefixes. It
accepted the exact healthy and fault progressions, including the strictly
increasing `UINT64_MAX-1` to `UINT64_MAX` boundary, without overflow or
exception. It also revalidated the malformed-CLOSE permanent
poison, parent-EOF branch, exact-once reader close, last-successful-fsync
durability, final-publication failure prefixes, production symbol boundary,
host sanitizer/analyzer build, and AArch64 warning-clean objects.

All of this validation was host-only. It contacted no device, `/dev`, USB,
network, other target, or private evidence, wrote no repository bytes during
the independent pass, and granted no live authority.

## Open gates and exact next unit

Still absent:

- a manifest-pinned static A90 binary and current-kernel qualification;
- selected scheduler/cgroup identities, numeric caps, storage budget, session
  count, and ordinal budget;
- parent readback and resident reaper integration;
- the strict raw canonical writer/parser, storage reservation, and crash
  fixture;
- driver and interface receipt producers;
- parent journal/effect integration and observation-only reconciliation; and
- an independent execution review plus any fresh live authority.

The exact next unit remains WP2-5b.3b: strict raw canonical writer/parser,
selected storage-reservation backend, and crash-prefix fixture. It remains H0.
WP2-5b.3c and 3d follow only in the order fixed by the reviewed design.

## Authority

This report and its generated/component bytes grant no candidate identity,
D0, D1, F1, observer installation, effect dispatch, property provisioning,
handoff, UFS mutation, recovery, or live execution authority. Option C remains
research-only and `H0D01-H0D10` remain unproved.
