# S22+ first-renewal watchdog observation: inactive H0 implementation

## Bounded task

Implement and check the smallest observation of the existing watchdog task in
the existing Debian boot path. Completion means real C producer/host consumer
checks, ARM64 compilation/execution, failure-path checks and independent review.
This does not select, qualify or activate a physical candidate. Existing consumed
P437 grants, retained source provenance and the seven-actor capability stay as
recorded. No device command is part of this work; A90 and S20+ remain untouched.

The [preceding audit](S22PLUS_P437_BOOT_REQUIREMENTS_WATCHDOG_H0_2026-10-19.md)
identified a first-boot watchdog reset before the old heartbeat became due.
The exact retained module exports `disable` and `wakeup_enable` attributes;
conditional userspace-pet attributes are compiled out. These attributes do not
expose timer expiry, CPU-ping completion or a pet counter. A proc task snapshot
can narrow the next investigation but cannot prove any of those phases.

## Implementation and limits

`S22_AUTOBOOT_WATCHDOG_TRACE` is an inactive compile option requiring the existing
automatic rcS observer. No build profile enables it. It calls a small proc reader
from the existing rcS parent and later runlevel parent's wait loops; no extra
process or timer is added. The existing absolute workload deadline remains.
Each owner has at most five opportunities: an initial snapshot before 8.5s and
at 9/10/11/12s BOOTTIME, with 250ms allowed lateness. The observer never waits
for an opportunity and does not extend rcS lifetime. Expired opportunities are
skipped, so a later runlevel owner can observe remaining slots. Read errors or
logging loss disable further sampling in that owner. Missing samples leave the
phase unknown.

Discovery examines at most 4096 proc directory entries once per owner. An exact
`gh-watchdog` name, PF_KTHREAD flag, one thread and a unique match identify the
task. Subsequent reads recheck PID and start ticks before/after `wchan`; CPU ticks
must not reverse. Only `comm`, `stat` and `wchan` are read, with procfs/type,
no-follow, byte and call limits. All descriptors are closed within the call,
after the script fork, so none crosses into that child. Errors preserve the
workload's errno and last functional stage. They never cause a retry, signal,
watchdog write, scheduler change, filesystem write or new workload decision.

Proc work has a measured 250ms total allowance per owner, at most 100ms for
discovery and 25ms for each cached read. This shares the existing 2000ms actor
observation allowance with executable measurement and checked kmsg emission.
Checks cannot cancel a kernel syscall that never returns; these are admission
and elapsed-time bounds, not a demonstrated recovery mechanism. Reading and
logging add scheduling load and could perturb the event being observed.

The existing authenticated 128-byte S22AT1 framing binds executable/run/boot.
Stages 79/80 describe task/wait-symbol observations from actors 6/8; 81/82
describe the new runlevel observer entry/state load. The separately selected
eight-actor decoder does not reinterpret these as child-wait or service proof.
Stages 0–78 retain their original numbers and meanings.

For stages 79/80, the existing result/child/status/done/worker-result slots hold
CPU ticks or wait-symbol class, observed PID, start ticks, packed state/CPU/
policy/priority, and `(acquisition_ms << 3) | slot`. Packed properties use four
successive bytes in that order. Error records zero the data fields and retain
only error and acquisition/slot. The acquisition timestamp precedes logging;
the reads are not atomic. Wait-symbol classes are zero/running/unavailable/
hidden, qcom_wdt_kthread, smp_call_function_single, csd_lock_wait,
wait_for_completion, schedule_timeout, or other. No raw address or arbitrary
symbol text is emitted. A class is an observation, not a watchdog phase proof.

Independent task/slot conflicts suppress a coherent watchdog interpretation
without erasing separately valid old transition facts. Actor/source/boot/
sequence contradictions retain the existing fail-closed behavior. Missing
records never establish non-execution, a stall, recovery, pet success or cause.

## Validation and remaining boundary

The 14 watchdog test methods passed, compiling and running the actual C reader
and authenticated producer on the host and ARM64 through qemu-user. Synthetic
proc files exercise exact reads, PID reuse before/during acquisition, multiple
matches, missing tasks, wrong filesystem type, symlinks, malformed/oversized
stat data, EINTR/EIO, short reads, close failure, read overruns, exhausted
budgets, logging loss/delay, late owner entry and the final observation window.
They check descriptor settlement, errno/last-stage preservation, no read retry,
acquisition-time decoding and limits on evidence interpretation. The proc
filesystem identity, clock and kmsg device are test fixtures; this does not
exercise Samsung timer/IPI/SMC behavior.

The existing 15 transition and 21 rcS decoder tests and 12 repository boundary
tests passed. Touched Python compiles. The full physical hook cross-compiles as
static ARM64 with the optional observer enabled, with identical A/B outputs.
With it disabled, the new full hook is byte-identical to the retained P437 hook.
Both H0 and runtime source closures include the new header. No build selector
enables the feature and no previous approval, grant or capability is repinned.

Independent review additionally checked nine edge cases on both host and
ARM64 (18 executions): integer limits/overflow, embedded NULs, empty wchan,
noncanonical PID directories and symlinked task directories. Replaying the
current decoder over all 41 retained P437 VM captures gives exactly the old
projections. That is consumer regression evidence, not a new VM run or
qualification of the optional producer. Independent review concluded
**PASS_H0_INACTIVE**, scope **H0_ONLY_INACTIVE**, with no findings. It rechecked
the current 14 watchdog methods, source closures and final full-hook outputs.
This qualifies this inactive change only, not a device capability or candidate.

Private evidence is under
`workspace/private/outputs/s22plus-watchdog-observer-h0-20261019-1/`, including
`inputs/source-audit.json`, focused test logs, `build/hook-builds-final.json`,
`build/source-closure-check.json`, and independent review/edge-case/retained
projection receipts. The original 41-case VM results apply to their original
runtime. An enabled candidate still needs its normal integration/qualification
and authority binding. This H0 change neither grants a boot nor a repair/replay
of consumed P437; native_data consistency remains unknown.
