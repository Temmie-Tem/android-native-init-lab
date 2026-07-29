# S22+ FYG8 P2.84 stock-trace PM-order correction H0

Date: 2026-07-29 KST

## Verdict

`PASS_P284_PARENT_RUNTIME_STATUS_GATE_SELECTED_HOST_ONLY`

The D1 v2 raw trace disproves one unconditional ordering claim in the prior
gap analysis: on stock Android, child and parent runtime-suspend callbacks did
not execute inside the first stop-side `dwc3_otg_sm_work`. They ran later on
the generic PM workqueue.

That stock ordering does not transfer unchanged to the closed P2.84 bare-PID1
run. P2.84's accepted `0xc18` classification required the child suspend and
nested HS-PHY power-off pairs to use the same PID and lie between
`dwc3_otg_start_peripheral(..., 0)` entry and return. The live candidate
therefore proved a synchronous child-suspend callback in the inner helper,
while stock proved a deferred callback. Runtime-PM reference and child-count
state, not the source-level call name alone, selects the path.

The narrow successor correction is nevertheless valid:

```text
NONE
  -> child runtime_status == suspended
  -> parent runtime_status == suspended (bounded, same deadline)
  -> PERIPHERAL
```

An exact parent `suspended` read cannot occur while
`dwc3_msm_runtime_suspend()` or `dwc3_msm_suspend()` is still executing. It
therefore removes the callback-and-mutex portion of the parent-suspend overlap
that P2.84 left open and converts a parent-callback wedge into a pre-write
timeout. It does not prove that the enclosing `dwc3_otg_sm_work` returned:
optional requeue bookkeeping and the worker return remain after PM core marks
the parent suspended. No kernel change is required, but outer-work probes and
a bounded classified PERIPHERAL-write helper remain required.

This is a conditional mechanism validation, not retrospective root-cause
proof. P2.84 retained no parent-suspend marker, so it remains unknown whether
the parent callback actually wedged. The unbounded helper `SIGKILL` plus
blocking `wait4` defect also remains a separate mandatory userspace fix.

This unit was H0 only. It performed no device contact, D0, D1, F1, build,
image/package creation, reboot, transfer, or partition action and grants no
live authority.

## Frozen inputs and non-mutation

The analysis started from clean HEAD
`2825a920fe13ea04edc9da4397874147773677d1`.

The selected P2.84 source contract still has exactly 60 keys. Current source
receipts match the frozen intent `60/60`; no selected source file was changed.
The raw stock trace remains private and has SHA256:

```text
97911a1a9a1a0d0e2a2ec01eb90b7e740bc573e4f0165d3da420727c6448d90a
```

The reopened exact FYG8 inputs retain these hashes:

```text
dwc3-msm-core.c
  1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021
power-sysfs.c
  8d1ef4c7799f79af6c4d59958157d30e793cac3b3e0748b57446cfaa37c19321
dwc3-msm.ko
  8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1
```

The correction report and posture updates are outside the 60-key identity
domain. P2.84 remains immutable, closed, and non-replayable.

## Raw stock timeline

With `t0` equal to the first NONE `mode_store_in`, the trace gives:

| Relative time | Event | Context |
| --- | --- | --- |
| `0.000..0.091 ms` | NONE `mode_store`, `rc=5` | D1 lane |
| `0.123..0.264 ms` | outer SM work 1 | `kworker/u16:0`, CPU 3 |
| `0.268..0.291 ms` | outer SM work 2 | `kworker/u16:0`, CPU 3 |
| `12.139..16.653 ms` | child runtime suspend | `kworker/0:1`, CPU 0 |
| `16.719..19.509 ms` | parent runtime-suspend wrapper | `kworker/0:1`, CPU 0 |
| `17.873..19.504 ms` | `dwc3_msm_suspend` | `kworker/0:1`, CPU 0 |
| `19.523..19.547 ms` | outer SM work 3 | `kworker/u16:2`, CPU 2 |
| `129.614..136.617 ms` | child runtime suspend 2 | `kworker/0:0`, CPU 0 |
| `1349.895..1351.703 ms` | parent runtime suspend 2 | `kworker/0:0`, CPU 0 |
| `41139.102..41139.352 ms` | PERIPHERAL `mode_store`, `rc=11` | D1 lane |
| `41139.397 ms` | outer SM work 5 begins | `kworker/u16:3`, CPU 0 |

The first two outer invocations finished before the first child callback
started. The first parent callback began only after the child callback
returned, held `suspend_resume_mutex`, and finished before outer invocation 3.
This is not a nested outer-work call stack.

The PERIPHERAL sysfs write returned in `0.250 ms`; its new outer work began
`0.045 ms` later. Stock therefore did not block in the write-side flush.

The lane's first post-write marker was delayed about 20.1 seconds by watchdog
disarm, and the false outer-timeout path added another roughly 20.9 seconds.
Consequently restoration occurred after 41 seconds, on a fully settled
system. No overlap challenge was executed.

## Why stock deferred the callbacks

The exact vendor source contains synchronous-looking calls:

```text
dwc3_otg_start_peripheral(..., 0)
  -> pm_runtime_put_sync(child)
  -> pm_runtime_put_sync(parent)

dwc3_otg_sm_work
  -> pm_runtime_put_sync_suspend(parent)
```

Those calls do not guarantee that the corresponding driver callback runs in
the caller. A put can return while a usage count remains positive, while a
child blocks parent suspension, or after an autosuspend request is scheduled.

The PM core sets a child to `RPM_SUSPENDED` only after its callback succeeds.
It then issues an asynchronous idle request for the parent when the parent's
child count permits. This exactly fits the observed `kworker/0:*` child then
parent sequence. The stock trace is direct evidence for that execution, and
the old report's unconditional synchronous-stack wording is withdrawn.

## Why this does not clear the bare-PID1 path

The P2.84 cycle parser does not merely count child events. For the stop side it
requires:

1. one `dwc3_otg_start_peripheral(..., 0)` entry;
2. one stop-helper PID;
3. child-suspend entry and return from that same PID;
4. both child events strictly between stop-helper entry and return; and
5. the PHY suspend and power-off pairs nested inside the child interval.

`0xc18` is reachable only after those constraints pass and the child
`runtime_status` reads exact `suspended`. Thus the bare candidate had already
executed child suspend synchronously before the probed inner helper returned.

Once that child is suspended, the following outer
`pm_runtime_put_sync_suspend(parent)` is no longer blocked by that child. It
may execute the parent callback synchronously in the outer worker. P2.84 did
not probe that callback or outer return, so this remains the leading
source-compatible overlap, not a proven event.

The correct conclusion is therefore:

```text
stock D1: child/parent PM callbacks deferred to pm_wq
P2.84 F1: child callback nested in the stop helper
P2.84 parent callback: unobserved and context-dependent
```

The stock trace corrects the universal model; it does not refute the
candidate-specific model established by the retained trace classifier.

## Parent runtime-status gate

The already verified parent path is:

```text
/sys/devices/platform/soc/a600000.ssusb/power/runtime_status
```

The exact `runtime_status_show()` maps the PM enum to `active`, `suspending`,
`resuming`, or `suspended`. It does not wait for the callback. A poll during
the callback reads `suspending`; only PM-core completion changes it to
`suspended`.

The exact parent callback unlocks `suspend_resume_mutex` before returning.
The PM core changes the status to `RPM_SUSPENDED` only after that successful
return. Therefore an exact `suspended` read proves both:

- the parent callback returned successfully; and
- `suspend_resume_mutex` is no longer held by that suspend.

The callback clears `WAIT_FOR_LPM` and may queue one final `sm_work` before it
returns. On a subsequent PERIPHERAL write, `dwc3_ext_event_notify()` flushes
any such old work before installing DEVICE inputs. This establishes ordering,
not liveness: userspace may observe parent `suspended` while the enclosing
outer worker still has its requeue-and-return tail. The stock trace places the
next observed boundary only `0.019 ms` after `parent_suspend_out`, suggesting a
much smaller window than the callback body, but it cannot prove that the bare
tail is absent or bounded.

If the parent callback wedges, its status remains `suspending`. The existing
`p282_wait_exact_value()` treats the resulting value mismatch as retryable
`-EIO` and continues to the existing deadline. A successor must convert
`matched == 0` into a stage-`0x8f` failure and must not call
`p282_cycle_restart()`. If parent `suspended` is observed, the following
PERIPHERAL helper must still have a closed deadline and distinguish dispatch,
flush wait, write completion, actual start-peripheral entry/return, and later
readback failure.

## Exact successor scope

The mechanism is userspace-only but is not literally an unversioned one-line
edit. A correct successor must:

1. add the exact parent runtime-status path to its versioned runtime contract;
2. reuse the existing normalized read and bounded `p282_wait_exact_value()`;
3. wait for parent `suspended` after child `suspended` and before publishing
   successful stage `0x8f`;
4. on parent miss or read error, publish an allowed stage-`0x8f` failure
   before any PERIPHERAL write;
5. preserve the same 30-second stop deadline rather than creating an
   additional wait budget;
6. retain actual `dwc3_otg_sm_work` entry/return probes and a bounded
   classified PERIPHERAL-write path for the residual outer tail;
7. test `active`, `suspending`, `error`, timeout, successful suspended, and
   unreturned-helper transitions; and
8. derive a new source contract and run ID. Never edit or rebuild P2.84.

Separately, the restart helper must stop using blocking `wait4` after a
deadline. Fault injection must prove PID1 can publish the classified failure
when a role-write child remains indefinitely uninterruptible. The parent gate
removes the callback/mutex portion of the overlap; it does not close the
outer-tail window or justify leaving a generic unbounded helper path.

No new stock D1 is needed to validate this ordering gate. The next bounded
unit is H0 implementation and static validation of a versioned successor.
Full-LTO, packaging, D0, approval, and F1 remain later, separate steps.

## Static validation

- a mechanical parse found `2/2` mode writes, `6/6` outer works, `2/2` child
  suspends, `2/2` parent wrappers, and `2/2` parent suspend bodies;
- the ordering assertions
  `outer2-out < child1-in < child1-out < parent1-in < parent1-out < outer3-in`
  and `restore-out < outer5-in` pass;
- the frozen P2.84 source receipts match the intent `60/60`;
- all 40 focused P2.84 contract, pre-LTO, D1-spec, and attachment-name tests,
  ten P2.86 freeze tests, and eight active-contract tests pass;
- `AGENTS.md` is 220 lines and the archived 899-line goal payload is preserved
  byte-for-byte while active `GOAL.md` is 215 lines; and
- `git diff --check` passes.

## Superseded claims

This report supersedes only these prior claims:

- that stock child and parent suspend callbacks were necessarily nested in
  the stop-side outer work;
- that `outer-return - child-suspended-observation` was the load-bearing
  overlap window; and
- that an outer-work return fence was the primary repair target.

It preserves the prior conclusions that:

- the historical `worker_*` names actually attach to
  `dwc3_otg_start_peripheral`;
- the P2.84 restart helper's deadline is not closed because of blocking
  `wait4`;
- retained-slot CRC state proves no generation-89 write reached its first
  durable CRC clear;
- P2.84 remains no-proof and must not be replayed; and
- the D1 v2 approval is consumed and the device returned healthy.
