# S22+ FYG8 P2.84 post-suspend restart-gap focused analysis H0

Date: 2026-07-29 KST

## Verdict

`PASS_P284_POST_0X8F_GAP_LOCALIZED_HOST_ONLY`

with two load-bearing findings:

```text
OUTER_SM_WORK_QUIESCENCE_UNPROVED
RESTART_HELPER_DEADLINE_NOT_CLOSED
```

The exact source exposes one complete mechanism that matches the retained
shape: after `0x8f`, the DEVICE-write helper can block in the vendor driver's
synchronous flush of the previous `dwc3_otg_sm_work`; after 30 seconds PID1
sends `SIGKILL` and then performs an unbounded blocking `wait4`, so it may
never reach a `0x90` checkpoint.

This is the strongest source-and-evidence fit, not a unique live root-cause
proof. The retained record contains no stack, trace snapshot, or sidecar that
can prove the helper was actually waiting in that function.

This unit was H0 only. It performed no device contact, build, rebuild, image
change, transfer, reboot, or flash, and it grants no live authority.

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

At starting HEAD
`66a38436b425bab8a86a43385237d5ee9cd80fd4`, `git status --short` was
empty. The selected contract enumerated 60 `SOURCE_KEYS`; current receipts
matched the frozen post-B contract `60/60`. The report, `AGENTS.md`, and
`GOAL.md` paths are outside that inventory. No selected source byte was
changed.

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

1. **Best fit, live-unproved:** the PERIPHERAL helper entered
   `flush_delayed_work()` before the prior outer `dwc3_otg_sm_work` became
   quiescent; PID1 then converted the nominal timeout into blocking `wait4`.
   This predicts the exact last checkpoint, no ACM, no terminal mutation, and
   no candidate replay.
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

## Narrowest successor discriminator

Do not replay or rebuild P2.84. A successor must have a new versioned source
contract and identity. Before another candidate is selected, its H0 design
must:

1. probe actual `dwc3_otg_sm_work` entry and return separately from
   `dwc3_otg_start_peripheral`;
2. require a bounded, balanced, stable stop-side outer-work quiescence fence
   before issuing the DEVICE write;
3. make helper dispatch/entry distinguishable from helper completion;
4. guarantee that helper timeout evidence can be checkpointed without a
   blocking reap or a possibly blocking cleanup first;
5. use only nonblocking reap after timeout and explicitly classify an
   unreaped helper;
6. distinguish prior-work flush timeout, DEVICE-write completion,
   start-peripheral entry/no-return, and later readback failure; and
7. execute host/QEMU fault injections that hold the helper indefinitely and
   prove the retained timeout path itself remains bounded.

The exact sequencing of a terminal checkpoint versus trace cleanup and a
possibly unreaped helper is execution-critical and requires the ordinary
independent safety review before any successor Full-LTO or manifest work.

No successor candidate, D0, D1, F1 manifest, or approval is created here.
