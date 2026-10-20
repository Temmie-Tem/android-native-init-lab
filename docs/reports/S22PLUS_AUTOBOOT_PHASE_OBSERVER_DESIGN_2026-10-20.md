# S22+ Debian startup: bounded watchdog and rcS phase observation

Status: **DESIGN / H0; no device grant**.
The operator requested continuation through a new physical experiment.
Only `SM-S906N/g0q/S906NKSS7FYG8` is selected. P441 is consumed and closed;
its original observations, recovery and current native_data uncertainty remain.

## Objective and sequence

Keep the Debian-owned initial PID1, protected root admission, installed SysVinit,
ordinary rcS/runlevel 2, 120-second local service proof and same-boot SSH goal.
Add observations that distinguish the dynamic branches left by the
[P441 follow-up](S22PLUS_P441_WATCHDOG_FOLLOWUP_H0_2026-10-20.md).
No new permanent supervisor or diagnostic-only product architecture is selected.

First prepare fresh P442 using the existing mountless `autoboot-pair` reader.
Seal exactly the closed P441 early/runtime paths, metadata and existing bounds.
Preserve raw acquisition before authentication and keep dirty home-block,
missing, partial and complete results distinct. This reader makes no filesystem
write, mount, replay or installed-code execution. Its result can select the
smallest necessary later recovery/history work; it cannot itself admit a new
writable boot. No repair is preselected from Android health or prior patterns.

In parallel with that H0 preparation, establish the smallest phase observer
using the actual retained Image/modules and existing tracefs/kprobe precedent.
The exact Image enables KPROBES and KPROBE_EVENTS; FUNCTION_TRACER is disabled.
These config facts show an available mechanism, not current tracefs health or
authority to configure it. A new observation selection still needs its own
changed-closure review and qualification.

## Selected design questions before implementation

Use exact module-local callsites rather than broad system-wide probes.
Candidate points are timer callback, thread exit from its timer wait,
the fixed per-CPU synchronous ping caller before/after its call, pet before/
after its call with the return register, and notifier/timer-rearm boundaries.
Derive offsets and register meanings from the hash-bound ELF, relocations and
the selected source. CFI jump tables, PAC/SCS, kprobe blacklist and ARM64
instruction support must be checked; a source function name alone is inadequate.
No register/memory writer, instruction skip, forced return or watchdog control
is part of the observer.

Prefer a dedicated bounded tracefs instance consumed by the existing installed
hooks, with fixed event definitions and a short absolute early-boot window.
The actual feasibility check must decide setup timing, finite event/read/byte
budgets, disable/cleanup ownership and transition between existing rcS/runlevel
parents. Trace-ring loss, kprobe missed hits, parsing failures and logging loss
must remain explicit. Reuse the prior incident's `profile_hits >= records`
invariant; equality is not a losslessness predicate. No indefinite drain,
unbounded generic trace or extra resident process is admitted by this design.

For rcS, preserve the selected serial script order and command results.
Evaluate a hash-bound RAM copy of the selected rc dispatcher, emitting only
fixed script IDs and begin/end/result values to its existing parent. Any pipe
must be nonblocking, bounded, exclusive and closed for invoked service scripts;
ordinary daemons must not inherit an observation descriptor. Record failure
must not change workload status or turn into retry authority. The installed
root script bytes must remain untouched. Child execution proof must derive
from the actual selected script and channel, not another exec-intent marker.

Each record must preserve source/run/boot provenance and distinguish the event
time from the later userspace collection time. A missing return is not a stall
proof. A successful pet API return is separate from verified hardware renewal.
Use the existing retained RAM logger and authenticated projection where feasible;
any new persistent record belongs only to a separately admitted existing file
lifetime and must justify its necessity. Missing records remain unknown.

## Qualification and completion

Before a costly build, resolve callsite/config/ABI questions using existing
exact inputs and prior P280/P309/P311 checks. Their old capability and consumed
device results grant no new effect. The P311 profile-window and evidence-routing
incidents must be exercised in the actual new producer/consumer, not only mocks.

H0 completion requires representative actual ARM64 probe/channel execution,
failure and loss handling, source-bound A/B artifacts, actual package consumption,
independent review and the normal integrated VM service/SSH/shutdown evidence.
Observation does not waive complete protected admission, exact target/original-A
binding, finite budgets, one-shot transfer/operation or physical recovery.
The final instrumentation mechanism and limits will be recorded after these
feasibility checks; this report does not claim they are already implemented.

The physical sequence follows the existing activated lanes. P442 requires its
concrete returned one-operation/1800-second attended grant after qualification.
Any later fixed journal recovery and integrated boot require their applicable
fresh concrete grants and health/admission. Complete the authorized H0 work and
prepare each reviewable operation before requesting a missing lane-specific
approval. Physical Download/original-A recovery remains necessary when native
return is unavailable. Do not renew or replay P441.

Report functional progress, retained evidence, shutdown/filesystem state and
Android closure separately. A90 and S20+ receive no command. Preserve unrelated
working-tree changes. The 800-line prior goal is archived byte-for-byte at
`docs/archive/roadmaps/GOAL_THROUGH_P441_FOLLOWUP_2026-10-20.md`.

## First H0 feasibility result

The retained Image/module review supports twelve fixed entry/offset probes,
using the actual function bodies and no return-address interception. A full
eight-CPU cycle would produce at most 26 events. Probe registration, timing,
loss accounting, handover and cleanup remain unimplemented and unqualified.

A private rcS prototype now uses a RAM copy of the exact serial dispatcher
and a nonblocking Unix datagram socket to its existing parent. In an isolated,
diskless ARM64 VM, the selected Debian dash and dispatcher execute sixteen
fixture services in their exact original order. Normal observation yields
34 complete datagrams, including one deliberately nonzero service return.
Full-queue and deterministically disconnected-peer cases preserve the same
sequence and final dispatcher status. Invoked helpers and services inherit
no extra descriptor, including any shell-saved copy of the socket, and retain
the normal SIGPIPE disposition. The receiver checks truncation and empty
packets, drains after child reaping, and does not treat a closed datagram peer
as stream EOF.

The first feasibility VM checked only fd 3 and did not order peer closure
before the fork. Independent review identified those fixture limitations;
a distinct second VM strengthens both checks and verifies every script name
and order. Both runs, source snapshots and raw output remain private under
`workspace/private/outputs/s22plus-autoboot-phase-h0-20261020-1/`.
These are channel/dispatcher results with fixture services, not real service
functionality, physical-kernel behavior, production observer qualification or
device authority. Public execution sources remain frozen for prepared P442.
