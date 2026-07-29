# S22+ FYG8 P2.84 post-suspend restart-gap focused analysis H0

Date: 2026-07-29 KST

## Verdict

`PASS_P284_POST_0X8F_GAP_LOCALIZED_HOST_ONLY`

with three load-bearing findings:

```text
OUTER_SM_WORK_QUIESCENCE_UNPROVED
OUTER_SM_WORK_WEDGE_CAUSE_UNRESOLVED
RESTART_HELPER_DEADLINE_NOT_CLOSED
```

The exact source exposes one complete mechanism that matches the retained
shape: after `0x8f`, the DEVICE-write helper can block in the vendor driver's
synchronous flush of the previous `dwc3_otg_sm_work`; after 30 seconds PID1
sends `SIGKILL` and then performs an unbounded blocking `wait4`, so it may
never reach a `0x90` checkpoint.

This identifies the silence-preserving wait, not why the outer work would fail
to finish. If the flush interpretation is correct, the outer worker itself
remained blocked for roughly the rest of the 300-second observation after the
nominal 30-second helper limit. The source has no expected wait of that scale.
The retained record contains no stack, outer-work trace, or parent-suspend
progress marker that identifies the blocking primitive. The mechanism is the
strongest source-and-evidence fit, not a unique live root-cause proof.

This unit was H0 only. It performed no device contact, kernel/userspace
candidate build, rebuild, image change, transfer, reboot, or flash, and it
grants no live authority.

## Frozen inputs and non-mutation

The analysis reopened:

- source contract
  `s22plus-fyg8-p284-sysfs-ingestion-correction-v1`;
- run ID `023060c8dd0ab036f8547a816624356f`;
- candidate intent preimage SHA256
  `4cdaf836a299eea4bf270dcf299ecef16fc3394dde6f2820a44bef4205941ec3`;
- candidate patch SHA256
  `cd47f84e6c9b62bc0cbdf03e4bd4a80895966cc295c4372e912f959708ca9aa1`;
- materialized runtime SHA256
  `b7e7b0029843fa6029fa8c43f984859912b6e4d8d676a7b456343057dd033135`;
- materialized trace descriptor SHA256
  `3e6b23544a2f5b23e9fbfefa824abd7ba226adb9a45211634ddbc0c0797f443a`;
- reconstructed `dwc3-msm-core.c` SHA256
  `1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021`;
- reconstructed `workqueue.c` SHA256
  `c36d68a4beb815eecd18d4ea2008e22b14f7ef65cbeaa608e798185665e49867`;
  and
- reconstructed `kprobes.c` SHA256
  `3ae68503a7c776b5eaead02c3e6663bce175ab5df4f7184db0368d8980c76a81`.

The original analysis started at HEAD
`66a38436b425bab8a86a43385237d5ee9cd80fd4`; this review correction started
from clean HEAD `dd5f5ff4bc1b56133c2f0eeacbf68bb024704895`. The selected
contract enumerated 60 `SOURCE_KEYS`; current receipts matched the frozen
post-B contract `60/60`. The report, `AGENTS.md`, `GOAL.md`, the new generic
name gate, and its test are outside that inventory. No selected source byte
was changed.

## Closed live evidence

The closed Process v2 transaction established:

- one candidate transfer and one exact rollback transfer, with no candidate
  replay;
- a full 300.033-second observer timeout with no accepted ACM endpoint;
- two byte-identical 2,097,136-byte retained reads;
- one exact P2.84 family and zero foreign families;
- generation 87 in slot 1:
  `stage=0x8e, outcome=progress, detail=0`;
- generation 88 in slot 0:
  `stage=0x8f, outcome=progress, detail=0xc18`;
- no exact second-boot record for the same run ID;
- operator confirmation of no boot loop; and
- exact rollback, final health, all eight canonical events, journal
  `CLOSED`, and no recovery requirement.

These facts remain a no-proof result for DEVICE restart, bind, bus state, and
ACM.

## Correction: `0x8e` did not prove the outer worker returned

The P2.82/P2.84 C structures name the first trace pair `stop_worker` and the
events `worker_in` and `worker_out`. Those names are semantically broader than
the actual probes. The exact generated descriptor attaches both events to:

```text
dwc3_msm:dwc3_otg_start_peripheral
```

It does not probe `dwc3_otg_sm_work`.

Therefore `0x8e/detail=0` proves:

1. the corrected normalized NONE readback matched;
2. `dwc3_otg_start_peripheral(..., 0)` entered;
3. that function returned; and
4. its return value was zero.

It does **not** prove that the enclosing `dwc3_otg_sm_work()` returned or that
the delayed-work item was quiescent. Earlier wording that called this an
authoritative “stop-worker return” is corrected by this report.

## The exact post-`0x8f` race window

The stop-side vendor path is:

```text
dwc3_otg_sm_work
  -> dwc3_otg_start_peripheral(..., 0)
       -> child pm_runtime_put_sync / runtime suspend
       -> set WAIT_FOR_LPM
       -> parent pm_runtime_put_sync
       -> return 0                 [current worker_out probe]
  -> parent pm_runtime_put_sync_suspend
  -> optional queue_delayed_work(sm_work)
  -> return                       [not currently probed]
```

PID1 sees the inner function return, publishes `0x8e`, confirms exact child
`runtime_status=suspended`, classifies the child suspend and zero-return
power-off helper, and publishes `0x8f`. Those actions can occur while the
workqueue thread is still in the outer parent suspend, requeue, or return
suffix. The live trace did not retain enough information to determine whether
that overlap occurred.

PID1 then immediately enters `p282_cycle_restart()` and forks the
PERIPHERAL-write helper. The helper performs:

```text
write(parent mode, "peripheral\n")
  -> mode_store
  -> dwc3_msm_set_role(USB_ROLE_DEVICE)
  -> dwc3_ext_event_notify
  -> flush_delayed_work(&mdwc->sm_work)
  -> update ID/B_SESS_VLD inputs
  -> queue_delayed_work(sm_work)
```

The flush happens before the new DEVICE inputs are installed and before the
new state-machine work is queued. It synchronously waits for the prior work
instance.

The writer does not hold `role_switch_mutex` across that flush:
`dwc3_msm_set_role()` releases the mutex before calling
`dwc3_ext_event_notify()`. The DEVICE inputs are also changed only after the
flush. Therefore the exact source does not expose a writer-held role lock or a
new DEVICE state change that could explain why the old worker stopped making
progress. Under the leading hypothesis, the old worker was already blocked in
its stop suffix and the DEVICE writer merely waited for it.

## What remains unexplained: why the outer worker did not return

After the traced `dwc3_otg_start_peripheral(..., 0)` return, the relevant outer
suffix is short:

```text
pm_runtime_put_sync_suspend(parent)
optional zero-delay self-requeue
return from dwc3_otg_sm_work
```

The parent runtime callback is not, however, one atomic primitive. The exact
module expands it through `dwc3_msm_runtime_suspend()` and
`dwc3_msm_suspend()`. Static review before D1 changes the priority of its eight
synchronous boundaries.

The tempting first hypothesis,
`cancel_delayed_work_sync(perf_vote_work)`, is not a same-workqueue
self-deadlock in this build. Exact source initializes `sm_work` and queues it
on the ordered `k_sm_usb` workqueue, but every `perf_vote_work` submission uses
`schedule_delayed_work()`, hence `system_wq`. Exact module disassembly confirms
the latter with a `system_wq` relocation in `msm_dwc3_perf_vote_work`.
Moreover, the already-returned
`dwc3_otg_start_peripheral(..., 0)` synchronously executes the same
`msm_dwc3_perf_vote_enable(..., false)` cancellation, and no enable occurs
between that proven return and the later parent suspend. The same-queue
premise is false and the later cancellation should find no pending or running
perf work.

The measurement priority is therefore:

| Rank | Boundary | Exact-build reason |
| ---: | --- | --- |
| 1 | `suspend_resume_mutex` acquisition | mutex acquisition has no local deadline; absence of the first post-lock marker localizes the entry-to-post-lock interval, dominated by this wait |
| 2 | `disable_irq(PWR_EVNT_IRQ)` | synchronous IRQ drain has no local deadline, although the exact non-LPM handler is finite and does not take the suspend mutex |
| 3 | clock disable/rate framework | provider and framework lock waits have no local bound |
| 4 | GDSC/regulator collapse | framework waits remain possible, while the GDSC hardware poll itself is bounded to 1.5 ms |
| 5 | `icc_set_bw` bus votes | exact RPMh waits have a 10-second bound; ordinary write returns `-ETIMEDOUT` and batch write BUGs, unlike a silent 270-second wait |
| 6 | HS/SS PHY suspend callbacks | child suspend already put both PHYs into suspend; both exact callbacks fast-return when already suspended |
| 7 | `cancel_delayed_work_sync(perf_vote_work)` | distinct `system_wq`, prior synchronous cancel returned, and no intervening re-enable |
| 8 | wake-IRQ setup | the stopped state has neither host nor device mode, so this conditional block is skipped |

This ranks probe interpretation; it does not assert a root cause. The exact
offset markers remain necessary for every boundary, including the demoted
perf cancellation, so a surprising live path fails closed instead of being
explained away.

The usual L2 wait is not an unbounded candidate in this exact state.
`dwc3_otg_start_peripheral(..., 0)` has already set
`in_device_mode=false`, so `dwc3_msm_prepare_suspend()` returns immediately
when host mode is also false. Even on its other path its source loop is bounded
to 5 milliseconds.

Several of the remaining operations can sleep or synchronously wait, but the
retained P2.84 trace has no marker inside this callback. It is therefore not
valid to select one of them as the wedge cause. A bounded outer-return fence
would make this silence classifiable, but if one of these boundaries is truly
wedged it would only move the visible timeout from the DEVICE write to the
fence. It would not repair the stop path.

## Ordering correction: power-off is nested, not a PID1 post-stop helper

The proposed sequence

```text
stop -> outer return fence -> power-off -> DEVICE write
```

cannot be produced by moving a userspace fence in P2.84. PID1 has no direct
power-off call between stop and restart. `p282_cycle_suspend()` only reads the
child runtime status, refreshes the trace, classifies it, and publishes
`0x8f`.

The exact synchronous driver stack is instead:

```text
dwc3_otg_sm_work
  -> dwc3_otg_start_peripheral(..., 0)
       -> pm_runtime_put_sync(child)
            -> dwc3_runtime_suspend
                 -> dwc3_suspend_common
                      -> dwc3_core_exit
                           -> usb_phy_set_suspend(usb2, 1)
                                -> msm_hsphy_set_suspend(1)
                                     -> msm_hsphy_enable_power(false)
       -> pm_runtime_put_sync(parent)
       -> return                    [current worker_out]
  -> pm_runtime_put_sync_suspend(parent)
  -> return from dwc3_otg_sm_work   [currently unmeasured]
```

The trace parser requires the power-off pair to use the same PID and to be
nested between the stop-peripheral entry and return. Thus the retained
`0xc18` power-off return necessarily precedes both the current
`worker_out` event and the later outer parent-suspend call. It did not execute
concurrently underneath that later parent suspend.

The later parent callback invokes HS-PHY suspend again, but
`msm_hsphy_set_suspend()` returns immediately when `phy->suspended` is already
true. Its only override site sets and clears `PHY_SUS_OVERRIDE` synchronously
inside a separate EUD-spoof branch; that branch would return before queueing
the stop work and is incompatible with the observed stop trace. The exact
path therefore contains no second, recorded HS-PHY power removal underneath
the parent suspend.

The zero result also does not prove a regulator transition:
`msm_hsphy_enable_power()` returns zero immediately when
`phy->power_enabled` already equals the requested state. A real
outer-return-before-power-off experiment would require a new kernel mechanism
that defers or changes the child suspend sequence, not a reordered PID1 fence.
That is not justified before the stop path is measured.

## Why the 30-second helper deadline is not a bound

The exact workqueue implementation reduces `flush_delayed_work()` to
`flush_work()`. Its active-work path calls:

```text
wait_for_completion(&barr.done)
```

The exact completion implementation documents that call as non-interruptible
and without a timeout, and uses `MAX_SCHEDULE_TIMEOUT` with
`TASK_UNINTERRUPTIBLE`.

The userspace helper protocol sends its only result record after the sysfs
write returns. PID1 polls the pipe and `wait4(..., WNOHANG)` until the nominal
30-second deadline. On expiry it executes:

```text
kill(helper, SIGKILL)
wait4(helper, ..., 0)
```

The second call is blocking and has no deadline. If the helper is asleep in
the uninterruptible completion wait, `SIGKILL` remains pending and the helper
cannot exit until the awaited work completes. PID1 then waits for the helper
instead of returning `ETIMEDOUT`, running trace cleanup, or publishing the
classified `0x90` failure.

Thus the source contract's advertised 30-second helper limit is not closed
for this path.

## Retained-slot localization

Generation 88 is active in slot 0, so generation 89 would target slot 1. The
kernel checkpoint writer's first mutation is:

1. zero the target slot's `commit_crc`;
2. flush that CRC to memory;
3. write and flush the six-byte body; then
4. write and flush the new CRC last.

The retained slot 1 still contains the valid generation-87 CRC
`86ce81b1`. Both complete reads are byte-identical and both slots validate.
Consequently no generation-89 checkpoint reached even the writer's first
durable CRC-clear step.

This localizes the gap to one of:

- execution before the kernel checkpoint writer;
- a userspace open/write rejection before any record mutation; or
- a reset or loss that occurred before a later candidate record was seeded.

It is not merely a torn `0x90` write.

## Why an ordinary restart timeout is insufficient

If the PERIPHERAL helper returns, the exact runtime keeps one 30-second
restart deadline while it polls:

- child `runtime_status=active`;
- parent mode `peripheral`;
- exact real-UDC membership; and
- the traced `dwc3_otg_start_peripheral(..., 1)` return.

Ordinary helper errors, sysfs errors, readback misses, UDC misses, trace
classifications, and deadline expiry all route toward a stage-`0x90` failure.
The absence of any generation-89 mutation therefore cannot be explained by a
normal, successfully returned timeout path alone. It requires an additional
pre-checkpoint block, checkpoint rejection, cleanup block, or reset.

Trace cleanup is a weaker blocking candidate than the helper path. Exact
kretprobe unregister performs an RCU synchronization and then marks active
kretprobe instances orphaned; it does not join the probed function's return.
Tracefs I/O or an RCU stall has no explicit userspace deadline and cannot be
fully excluded, but it is reached only after the helper has returned or PID1
has escaped its wait.

## Ranked interpretation

1. **Best fit, live-unproved:** the prior outer `dwc3_otg_sm_work` failed to
   return at an unidentified stop-side PM boundary; the PERIPHERAL helper then
   entered `flush_delayed_work()`, and PID1 converted its nominal timeout into
   blocking `wait4`. This predicts the exact last checkpoint, no ACM, no
   terminal mutation, and no candidate replay. It does not identify which
   parent-suspend primitive blocked.
2. **Possible but unsupported:** a proc-checkpoint open/write rejection,
   tracefs/RCU cleanup stall, or another unbounded kernel wait before the
   first generation-89 mutation. Previous 88 sequential checkpoint commits
   make a spontaneous checkpoint-path failure less parsimonious.
3. **Disfavored, not excluded:** kernel reset or crash. One exact retained
   family and the operator's no-boot-loop observation weigh against a
   candidate reboot reaching PID1 again. A failure before a second record
   could be seeded remains possible.
4. **Rejected as a complete explanation:** an ordinary bounded child-resume,
   mode-readback, UDC, or start-peripheral timeout. Those paths should attempt
   a `0x90` failure record.

The P2.83 stock physical reconnect controls do not close this gap. They prove
that stock Android can traverse parent resume, child resume, HS-PHY init,
RUN_STOP, and notify-connect at both SuperSpeed and high speed in about
33 milliseconds. They do not prove quiescence of the P2.84 bare-PID1 stop-side
outer work item before the immediate restart write.

## Probe feasibility is proven from the exact artifacts

The exact stock `dwc3-msm.ko` pinned by P2.84 has SHA256
`8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1`.
Its ELF symbol table contains distinct local function bodies:

```text
dwc3_msm_runtime_suspend   0x7734
dwc3_msm_suspend           0x8ef0
dwc3_otg_sm_work           0xa854, size 1576
dwc3_otg_start_peripheral  0xcc3c, size 3452
```

The P2.84 Full-LTO configuration has `CONFIG_KALLSYMS=y`,
`CONFIG_KALLSYMS_ALL=y`, `CONFIG_KPROBES=y`, and
`CONFIG_KRETPROBES=y`. The vendor glue is the pinned prebuilt module rather
than a body eliminated by the core-kernel LTO link. Existing P2.83 controls
already proved tracefs attachment to local bodies in these exact modules.
`dwc3_otg_sm_work` is therefore an observed artifact fact, not merely an
expectation from its `INIT_DELAYED_WORK` address use.

Not every source helper remains a probeable body. In this module
`msm_dwc3_perf_vote_enable()` and `dwc3_msm_config_gdsc()` are inlined, while
`dwc3_msm_update_bus_bw()` remains a local symbol. Parent-suspend progress
must consequently use uniquely derived, instruction-aligned offsets inside
the exact `dwc3_msm_suspend` body for the inlined boundaries. A design that
assumes source names survived is rejected.

## Required stock D1 discriminator before successor design

Do not replay or rebuild P2.84, and do not select a successor yet. The next
live-capable unit is a stock-Android D1 control prepared under a fresh
approval. It is a one-way discriminator:

- a positive reproduction of outer non-return or a blocked PERIPHERAL write
  is decisive for the shared vendor stop mechanism;
- a negative result does not clear a bare-PID1 successor because Android's USB
  framework, services, and scheduling context remain present; and
- Android interference or a missed overlap window is an explicit no-proof,
  not a reason to retry under the same approval.

The bounded trace must distinguish:

1. module-qualified `mode_store` entry/return, retaining the trace header's
   caller `comm` and PID;
2. actual `dwc3_otg_sm_work` entry and return, with no return-value claim for
   the void function;
3. `dwc3_otg_start_peripheral(..., 0)` entry and return;
4. child runtime-suspend and nested HS-PHY power-off entry/return;
5. `dwc3_msm_runtime_suspend` and `dwc3_msm_suspend` entry/return; and
6. exact parent-suspend progress markers after mutex acquisition, perf-work
   cancellation, prepare-suspend, IRQ disable, PHY callbacks, clocks, GDSC,
   bus-vote, wake-IRQ, and final mutex-release boundaries.

One approved transaction may contain a fenced control lane followed by one
racy challenge lane, with stop-on-first-ambiguity. The challenge is not
trace-gated:

```text
control:
  NONE
    -> poll child runtime_status until exact "suspended"
    -> wait for actual outer return (bounded)
    -> final suspended read immediately followed by PERIPHERAL restore
    -> health
  then classify the completed trace and timing

challenge:
  NONE
    -> poll child runtime_status until exact "suspended"
    -> one immediate PERIPHERAL write
    -> bounded result or predeclared normal-reboot recovery
  only then classify whether the write actually overlapped outer work
```

The challenge does not call power-off separately; it observes the nested
power-off performed by NONE. It neither polls the trace nor branches on an
outer-return event before the PERIPHERAL write. Its authoritative measurements
are:

- NONE dispatch to outer return;
- first exact child-suspended read completion to outer return;
- the control restoration's final suspended-read completion to its
  module-qualified `mode_store` entry;
- PERIPHERAL dispatch to write return; and
- the last completed parent-suspend sub-boundary if outer return is absent.

The control gates challenge eligibility quantitatively. Let `W` be
`outer-return - first-suspended-observation` and let `R` be the measured
control restoration latency from its final suspended-read completion to the
known writer's `mode_store` entry. Challenge is permitted only when
`W >= max(10 ms, 4 * R)`. If outer return precedes the suspended observation,
if the total NONE-to-outer interval cannot expose that window, or if this
margin fails, the transaction records `CONTROL_WINDOW_TOO_SHORT`, restores
health, and ends without challenge. A 15-second missing control return is
already a positive non-return reproduction and also suppresses challenge.

Each lane binds the one writer's exact `comm` and PID before its first role
write. The long-lived lane process performs its own `open`/`write`; it does not
fork an `echo` or shell-redirection helper. Any `mode_store` entry from a
different pair is observed Android
interference, produces no-proof, and stops the transaction after cleanup.
Thus a negative result cannot silently assume the framework stayed idle.

The on-device trace capture must be detached and durable across expected ADB
loss. A recovery watchdog, one exact normal Android reboot contingency,
physical attendance, cleanup, and final FYG8 Android/root health must all be
declared in the fresh D1 approval. If the outer worker or writer remains
blocked, the candidate test stops and the exact recovery executes; there is no
same-approval challenge retry. TCP ADB may be added only if a connected D0
first proves a usable network address; only the volatile
`service.adb.tcp.port` plus an `adbd` restart may be considered, never the
persistent property. No such D1 approval exists in this H0 unit.

Only after this control is classified may a successor design decide between:

- a finite-overlap fence before DEVICE, which can prevent a flush race but is
  not a remedy for an independently wedged outer worker;
- a kernel stop-order change, if the control localizes the wedge to the
  sequential child-power-off/parent-collapse boundary; or
- a different repair targeted at the measured parent-suspend primitive.

Any eventual successor must also make helper dispatch distinguishable from
completion, checkpoint timeout evidence before blocking cleanup, use only
nonblocking reap after timeout, and pass fault injections that hold the helper
indefinitely. A new candidate still requires a versioned source contract,
independent execution-critical review, Full-LTO/static/package closure,
immutable manifest, connected D0, and fresh F1 approval.

## Permanent descriptor-name gate

This unit adds
`s22plus_probe_attachment_name_gate.py`, independent of every frozen P2.84
source key. It parses each rendered tracefs definition, extracts the actual
attached symbol, and requires the evidence-facing event stem to be an approved
semantic name for that symbol. Unknown symbols, rendered/declarative drift,
generic `worker` labels, and probe-kind drift fail closed.

The gate proves:

- all ten P2.80 descriptors pass;
- frozen P2.82/P2.84 are detected with exactly two historical issues,
  `worker_in` and `worker_out`, both actually attached to
  `dwc3_otg_start_peripheral`; and
- `outer_sm_work_in/out` pass only when attached to
  `dwc3_otg_sm_work`.

The frozen historical contract is not edited or waived into a new candidate.
Every new S22+ USB trace contract must pass with zero issues before pre-LTO
qualification.

## Host validation

- `py_compile` passed for the gate and its test;
- 36 focused P2.80/P2.82/name-gate tests passed;
- the P2.80 CLI audit returned `PASS_PROBE_ATTACHMENT_NAMES` for 10 events;
- the historical P2.82 audit returned exactly the two expected semantic
  mismatches and no others;
- all 60 current P2.84 `SOURCE_KEYS` receipts remain byte-identical to the
  frozen post-B identity preimage; and
- `git diff --check` passed.

This focused-analysis unit created no successor candidate, D0, D1 execution,
F1 manifest, or live approval. The later source-priority correction,
quantitative lane design, and read-only transport D0 are recorded in
`S22PLUS_FYG8_P284_STOCK_OUTER_D1_REFINED_DESIGN_AND_D0_2026-07-29.md`;
they do not retroactively authorize a live action.
