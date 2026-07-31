# S22+ FYG8 P2.90 post-commit tail and child-observer H0

Date: 2026-07-31 KST

Tier: H0

Status:
`NO_REUSABLE_CHILD_AT_GEN88_SIMPLE_CHILD_OBSERVER_REQUIRES_NEW_KERNEL_PROTOCOL`

## Questions

P2.90 retained a valid generation 88 but no adjacent generation 89. The exact
materialized-kernel audit left two one-channel branches:

1. the primary generation-88 publication did not return after its durable
   commit; or
2. it returned an error after that commit and the fallback then returned an
   error or did not return.

Before selecting another candidate, this H0 asks:

1. does the exact materialized writer contain a blocking operation after its
   commit?
2. is an existing child still alive when generation 88 is published?
3. can such a child distinguish the two branches using the existing retained
   API?

No device was contacted and no candidate source was changed.

## Exact inputs

The P2.90 intent-bound `candidate.patch` has SHA256
`f64f93f7e750187bb69e2f8dabca68b0c52ef31bf181bd1b0c06b5d6935853f1e`.
The materialized E3 include and checkpoint client have SHA256 values
`c737dfa5ff273472b150f2aca1f25b8188129ad2f3188c7625c5fdd984c00725`
and
`2a4ef815ccfd151503acca96411abfc2e8c949e5a303d3c1196fd67882632f72`.

Both Full-LTO `vmlinux` files are byte-identical with SHA256
`f1d1d751f0032c9f46367c24aeb22560389285c421bef1ec0157f2b4a0e1f5cd`.
The linked disassembly below is therefore candidate-bound, not an audit of the
historical checkpoint patch.

## H0-1: exact writer tail

The materialized source writes one slot in three persistent phases:

1. clear `commit_crc`, flush, and barrier;
2. copy and flush the six-byte slot body; and
3. copy and flush the four-byte commit CRC.

After the final commit-CRC flush returns, the source performs only:

- a write barrier;
- retained-header and new-slot memory comparisons;
- a possible `-ESTALE` return;
- five in-kernel state-byte stores;
- file-position addition; and
- return.

There is no mutex, completion, workqueue flush, RCU synchronization, sleep, or
I/O call in that source tail.

The exact linked `s22_fyg8_e1_write` confirms the same normal path. Its last
call before the final validation is `__flush_dcache_area`. After that call
returns, the linked path contains a barrier, loads/comparisons, state stores,
file-position storage, stack-canary comparison, and return. It makes no normal
path function call.

For this four-byte commit field, linked `__flush_dcache_area` executes one
cache-line `dc civac`, `dsb sy`, and return. Thus there is no loop whose bound
depends on device or USB state. This does not prove that cache maintenance or
the architectural barrier returned during the live run; a system-wide
progress failure can still stop there. It does prove that no later
candidate-specific blocking primitive exists inside the writer.

The exact proc entry supplies only `.proc_write`; it has no custom `.flush` or
`.proc_release`. `proc_reg_write` performs only its callback and PDE reference
release. The generic successful-write return path can still execute fsnotify,
`file_end_write`, fd-position unlock/reference release, and the userspace
client's `close`. Those are outside the materialized writer and remain the
residual return corridor. No source in that corridor can convert a successful
write into a later close errno through a custom checkpoint hook.

Therefore the non-return branch is narrowed to:

- the final cache-maintenance/barrier return itself; or
- generic procfs/VFS/syscall close or userspace return handling after the
  writer callback.

The concrete returned-error branch remains the writer's final `-ESTALE`
validation before its in-kernel state advance.

## H0-2: child lifetime at generation 88

The materialized runtime has exactly three `sys_clone()` call sites:

1. the initial E1 executable child;
2. the initial peripheral-role helper; and
3. the bounded NONE/PERIPHERAL role helper.

There is no watchdog or persistent supervisor child.

The initial E1 child is synchronously verified and reaped at
`CHILD_REAPED`, before the 60-module plan starts.

The initial peripheral-role phase returns normally only from conditions that
include `child_reaped`. Its timeout and contradiction paths publish a failure
and never enter the later cycle.

The cycle's NONE helper returns a successful observation only after both a
complete record and exact child reap. `unreaped`, malformed, timed-out, or
write-error observations are classified at STOP and abort before SUSPENDED.
The retained generation-88 SUSPENDED record therefore implies that the NONE
helper was already reaped. No clone occurs in `p282_cycle_suspend()`.

The next helper child would be created only after the missing restart-helper
dispatch positions. That code was not reached.

Consequently there was no existing userspace child alive at the generation-88
publication boundary. A child observer must be a new dedicated process, not a
reuse of P2.90's helper.

## Why the one-flag child proposal is not yet executable

Four independent contract obstacles remain.

First, the materialized kernel rejects every checkpoint write whose current
PID is not 1 with `-EPERM`, before request validation or retained mutation.
An ordinary child cannot publish through `/proc/s22_checkpoint`.

Second, P2.90's plain `clone(SIGCHLD)` gives fork-style copy-on-write memory.
A global SET/CLEAR byte is not shared. A successor needs an explicit bounded
IPC or shared mapping. A nonblocking fixed-record pipe is already supported by
the runtime and is the smaller mechanism.

Third, the checkpoint client generation is userspace state. A child forked
before generation 88 keeps generation 87 even if the kernel commits and
advances to 88. If the kernel instead returns post-commit `-ESTALE`, its state
can remain at 87 while the retained slot already contains generation 88. The
current write-only API gives the child no safe way to distinguish or
resynchronize those states.

Fourth, the retained writer is a deliberately single-writer protocol with no
concurrency lock. Merely relaxing the PID check permits the child to race the
parent on the same state and alternating slot. Adding a conventional mutex is
not sufficient: if the parent is the non-returning lock owner, the observer
blocks behind the failure it is meant to classify.

A single SET/CLEAR flag is also too coarse for the stated question. It says
only that the whole wrapper did not return. It cannot distinguish a
non-returning primary from a returned primary error followed by a
non-returning fallback. The observer signal must encode publication phase.

## Minimum viable successor protocol

A viable design requires a versioned kernel/userspace observer protocol, not a
userspace-only edit.

1. Spawn one dedicated observer and complete a ready handshake before the
   USB stop/suspend state transition. Keep only a fixed nonblocking control
   pipe open.
2. PID 1 registers that exact child PID plus run identity and a one-shot
   observer nonce through a separate observer control operation. Ordinary
   checkpoint writes remain PID1-only.
3. Signal exact phases over the pipe: primary armed, primary write returned
   with its errno, close armed/returned, fallback armed, fallback returned,
   and disarmed. The child uses one monotonic bounded deadline per armed phase.
4. The observer write does not trust a forked checkpoint client. The kernel
   derives the next legal position from its own state and validates the
   registered PID, nonce, run identity, phase, and one-shot budget.
5. Add an atomic writer-phase takeover protocol. The ordinary writer marks
   pre-commit, commit complete, finalizing, and idle. After timeout the
   observer may take ownership only from a commit-complete state. The parent
   and child must never write one retained slot concurrently.
6. Allow exact observer failure details at both possible active ordinals:
   state not advanced after a committed slot, and state advanced but the
   userspace publication did not return. The active generation then
   distinguishes the two cases without trusting child-local generation.
7. Make observer publication terminal and one-shot. If the parent later
   resumes, it must observe the takeover/terminal state and must not resume the
   ordinary fallback write.

The same source of truth must generate the ordinary position sequence,
observer phases/details, materialized kernel validator, userspace client, and
decoder. The linked audit must cover both ordinary PID1 requests and the
registered observer path. This integration is load-bearing and belongs in the
same new identity as the observer.

Required host tests include:

- unregistered PID, wrong PID, wrong nonce, wrong run, early observer, and
  duplicate observer rejection before retained mutation;
- parent-wins and observer-wins races at every writer phase;
- exact absence of concurrent writes to one slot;
- generation-87-state/committed-88 and advanced-generation-88 cases;
- primary-returned-error and fallback-non-return phase separation;
- child ready, timeout, exit, and exact reap;
- exhaustive source/linked request validation; and
- a fault where the parent publication never returns while the observer still
  produces the declared terminal record.

## Residual limit

If the USB runtime-suspend/PHY-off state prevents the observer process from
being scheduled, the child will be silent too. Likewise, a stop before the
writer reaches the safe commit-complete takeover phase cannot be rewritten by
the observer without racing an in-flight slot update.

Therefore another unchanged `0x8f` plus silence after this design would not
prove a code-location hang. It would classify the residual as observer
unscheduled, observer channel unavailable, or pre-takeover writer stop, and
the investigation must then move from code position to the system-state
transition.

## Decision

The two free H0 checks are complete:

- the materialized writer has no explicit blocking operation after its final
  commit flush returns; and
- no reusable child exists at generation 88.

Do not implement the simple SET/CLEAR proposal and do not request F1. The next
bounded unit is a pre-intent design/fault model for the registered,
phase-aware, single-writer-safe observer protocol above. Only after that
closure may a new source contract, intent, Full-LTO A/B pair, manifest, D0,
and fresh F1 approval be created.
