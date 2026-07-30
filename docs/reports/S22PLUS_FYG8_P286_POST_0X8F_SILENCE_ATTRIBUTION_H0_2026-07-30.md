# S22+ FYG8 P2.86 post-0x8f silence attribution H0

Date: 2026-07-30 KST

Status:
`PASS_P286_POST_0X8F_GAP_RELOCALIZED_PREPUBLICATION_H0`

## Verdict

The retained P2.86 record proves more than the closing report stated, but the
P2.86 restart instrumentation proves less than intended.

The exact `0x8f/detail=0xc18` publication occurs only after the new exact
parent `runtime_status=suspended` wait succeeds. Parent suspended is therefore
live-proven for this run. The identical P2.84 detail did not carry that
meaning because P2.84 published it before any parent-status gate.

The next P2.86 operation with an unbounded kernel synchronization is not the
PERIPHERAL helper. It is the inherited, unmarked
`p282_cycle_refresh(P282_STAGE_RESTART)` before helper dispatch. That refresh
opens and reads the tracefs snapshot. The exact kernel open path takes
`trace_types_lock` and executes `synchronize_rcu()` while preparing ring-buffer
iterators. No userspace deadline bounds that syscall path.

If the refresh returns, the PERIPHERAL helper's parent-side protocol is
bounded to the 30-second restart deadline plus a one-second nonblocking reap
deadline. However, P2.86 immediately performs another unbounded trace snapshot
before classifying or publishing the helper outcome. A wedged helper can
therefore still be converted into silence by the post-helper refresh even
though blocking `wait4` was removed.

The retained A/B slots and the surrounding persistent-log bytes rule out the
two leading publication-loss explanations:

- no generation-89 checkpoint left even the target slot's first durable
  commit-CRC-clear mutation; and
- the Samsung retained-log `idx` did not drift during the candidate run, so
  the writer's pre-commit header check did not reject a later checkpoint as
  stale.

The strongest source-and-evidence fit is consequently a pre-publication block
inside one of the unmarked restart operations, with the first restart tracefs
snapshot as the highest-priority boundary. This is a localization, not a live
stack proof. The retained ABI cannot distinguish the first trace snapshot
from a later helper-write/post-helper-snapshot or sysfs-read block.

This was H0 only. It performed no device contact, build, image mutation,
transfer, reboot, flash, or live control and grants no device authority.

## Frozen inputs and non-mutation

The analysis reopened:

- source contract
  `s22plus-fyg8-p286-parent-tail-bounded-restart-v1`;
- run ID `c6cde593033d6f1be93f82c8ff5a81e8`;
- runtime SHA256
  `5b113ba31b162230656fd405c9ca060f54e3d9f7534db033abd51dc4dcd6ed16`;
- P2.86 classifier SHA256
  `14b82ca22e307708cc412b29fa2b7e4784dc791348298c376ab3d8bc4d66d09e`;
- inherited cycle classifier SHA256
  `e14a634ec39102d999f51e64b01b1350d9c000e465f01b639b106d51c36d483e`;
- candidate patch SHA256
  `21688248789b408572699a1ddb1cd9409d723a740fbbc25c9e96aa48005f204a`;
- materialized checkpoint client SHA256
  `84f38a96aa000159fbe1d06703dc6254f61a99bfa454e2df40e4f90811d6fb22`;
- exact `trace.c` SHA256
  `188ab5c325f34b25a606903ccf6e0ab169a58714256320627c98534922bddca3`;
- exact `ring_buffer.c` SHA256
  `c121f4ba38d9143c9e7496449e9b579bce89f24cfae2764517ff08958e4fb81f`;
- exact Samsung `sec_log_buf_main.c` SHA256
  `296f4fc175d958feb35b92c8736faf6361ade2e7c447d9a9af5a93f59bdb97b8`;
- exact Samsung `sec_log_buf_vh_logbuf.c` SHA256
  `a38235646050583ce5dbf9906218fe0060edabbcb2c8357072b43eb6856c9375`;
  and
- exact `dwc3-msm-core.c` SHA256
  `1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021`.

The analysis started from clean HEAD
`13951f7fb9482f0e67d1eb9b292f9301a889d3b9`. Current and frozen source
inventories both contain 70 keys and compare as:

```text
CURRENT_SOURCE_KEYS 70
INTENT_SOURCE_KEYS 70
CHANGED_KEYS []
```

This report and the historical-report/goal corrections are outside those 70
keys. No candidate, verifier, decoder, packager, or other source-key byte was
changed.

## Correction: parent suspended is proven

The P2.86 `p282_cycle_suspend()` order is:

```text
wait child runtime_status == suspended
refresh and classify child suspend / power-off
wait parent runtime_status == suspended
classify parent result
abort as c50 on a clean non-match
abort as c51 on a read error
publish the inherited child classification as 0x8f/c18
```

The load-bearing source order is:

- child wait and child classification:
  `s22plus_fyg8_p286_e3_runtime.inc.c:2646-2695`;
- parent exact wait:
  `:2697-2702`;
- parent classification and abort:
  `:2703-2718`; and
- `0x8f` publication:
  `:2720-2724`.

`p282_classify_suspend()` can emit `0xc18` only when trace evidence is still
authoritative, child status is suspended, the power-off helper entered and
returned, and its return is zero. P2.86 then withholds that already-selected
classification until the parent gate passes. A retained P2.86 `0xc18` thus
also proves the parent exact readback.

It still does not prove:

- return from the enclosing `dwc3_otg_sm_work`;
- a regulator vote change or physical rail collapse;
- entry into `p282_cycle_restart`;
- a restart trace snapshot;
- PERIPHERAL helper dispatch; or
- any later restart, bind, bus-state, or ACM boundary.

Parent status becomes `RPM_SUSPENDED` before every caller-side PM tail has
necessarily returned. The parent proof therefore closes the parent callback,
not the outer delayed-work return.

## Exact interval after the retained publication

The main path calls `p282_cycle_restart()` immediately after
`p282_cycle_suspend()` returns. Before the first possible later checkpoint,
restart executes:

```text
clock_gettime and derive a 30-second deadline
if trace-authoritative:
    p282_cycle_refresh(RESTART)             [unmarked]
snapshot residual_outer_open
run bounded PERIPHERAL helper
if trace-authoritative:
    p282_cycle_refresh(RESTART)             [unmarked]
classify helper and publish on failure
wait child runtime_status == active
wait parent mode == peripheral
wait exact UDC membership
refresh until restart worker return/deadline
disable trace and read final trace/profile
classify restart
publish 0x90/c5c cleanup-pending marker
perform trace cleanup
```

The relevant source is
`s22plus_fyg8_p286_e3_runtime.inc.c:2748-2922`.

The first refresh at `:2757-2759` precedes the helper call at `:2761-2766`.
The second refresh at `:2770-2772` precedes helper classification at
`:2773-2789`. The `0x90/c5c` marker is much later: its helper is at
`:2521-2533`, and restart does not call it until `:2918`.

Therefore absence of `0x90/c5c` does not prove a restart write was dispatched
or that cleanup was reached. It proves only that no later checkpoint commit
survived.

## The first unbounded primitive is tracefs snapshot synchronization

`p282_cycle_refresh()` calls `p282_trace_read_snapshot()`, which calls the
generic `p282_read_file()` on:

```text
/sys/kernel/tracing/instances/p282/trace
```

The userspace reader uses blocking `openat`, repeated blocking `read`, one
possible extra `read`, and `close` with no timer or nonblocking flag
(`s22plus_fyg8_p286_e3_runtime.inc.c:158-209,1063-1079,2478-2493`).

This is the trace snapshot file, not `trace_pipe`; it does not intentionally
wait for a future event. Its finite C parser is also not an infinite-loop
candidate: input length is capped at 65,535 bytes, record count at 64, and all
record/outer-state loops advance over those fixed bounds.

The exact kernel snapshot path is nevertheless not deadline-bounded:

1. `tracing_open()` calls `__tracing_open()`;
2. `__tracing_open()` takes `trace_types_lock`;
3. it prepares one iterator per tracing CPU;
4. `ring_buffer_read_prepare_sync()` calls `synchronize_rcu()`; and
5. seq-file iteration takes `trace_event_sem` for read and the all-CPU trace
   access lock.

The exact locations are `kernel/trace/trace.c:4340-4440,4573-4610,4740-4748`
and `kernel/trace/ring_buffer.c:4881-4923`.

This does not prove an RCU stall happened. The suspend-side refresh immediately
before the parent wait returned successfully, so a spontaneous permanent
tracefs stall needs a state change in the short intervening interval. It does
prove that the first post-`0x8f` operation can wait outside every userspace
deadline and that P2.86 placed no checkpoint before it.

## The helper deadline is closed, but its evidence path is not

P2.86 removed the blocking child-specific `wait4(..., 0)`. The parent side:

- creates a nonblocking pipe;
- polls it and `wait4(..., WNOHANG)`;
- declares timeout when the shared 30-second deadline expires;
- sends `SIGKILL`;
- polls `wait4(..., WNOHANG)` for one additional second;
- classifies a clock failure or surviving child as unreaped; and
- returns to the caller.

The exact implementation is at
`s22plus_fyg8_p286_e3_runtime.inc.c:2203-2328`. A clock-read failure makes the
main deadline expire and makes the reap path classify unreaped; it does not
open an infinite polling path.

If the child remains in the vendor driver's uninterruptible
`flush_delayed_work()` wait, the parent can therefore return with:

```text
timed_out = 1
unreaped = 1
```

The classifier would select `0xc53/helper-unreaped`. If the child exits but
the write merely times out, the restart-specific classes are:

- `0xc57/peripheral-flush-timeout`;
- `0xc58/residual-outer-tail-timeout`; or
- `0xc59/start-peripheral-no-return`.

But PID1 refreshes trace before it calls that classifier. A block in the
second trace snapshot suppresses all four publications. P2.86 fixed the reap
bound but left the observation-to-publication corridor unbounded.

## Other deadline gaps before c5c

The restart deadline also does not preempt a syscall already in progress.
`p282_wait_exact_value()` calls `p260_expect_value()` before checking the
deadline. That reader performs blocking `openat`, `read`, an extra `read`, and
`close`. A blocked child-status or parent-mode sysfs read therefore defeats
the nominal restart deadline.

After those reads, restart has more unmarked trace snapshots and
`p286_cycle_capture()` disables tracing and reads both the trace snapshot and
kprobe profile before any cleanup-pending marker. These are later
silence-compatible boundaries, although they require the earlier helper and
checks to have returned.

The abort-path order itself is correct. `p282_cycle_abort()` publishes the
terminal checkpoint first and only then performs best-effort trace finish
(`:2445-2459`). A cleanup stall after entry to that function cannot erase the
terminal record. The gap is that several unbounded operations occur before
the code decides to enter the abort function.

The normal-path `0xc5c` marker protects only the final unregister/cleanup at
`:2530`. It does not protect the earlier restart snapshots or sysfs reads.

## Retained-slot proof: no generation-89 commit start survived

The exact record starts at raw offset 1,647,270. Its slots decode as:

```text
slot 1: generation 87, stage 0x8e, progress, detail 0, valid
slot 0: generation 88, stage 0x8f, progress, detail 0xc18, valid
active: slot 0
fallback_used: false
slot_status: [valid, valid]
```

Generation 89 would target slot 1. The checkpoint writer validates the request,
header, active record, next slot, and family set before its first mutation.
Its commit order is:

1. zero target `commit_crc`;
2. flush that zero;
3. write and flush the six-byte slot body; and
4. write and flush the new CRC last.

The exact code is in `candidate.patch:711-810`; the first mutation is
`:776-780`.

A focused mutation of the retained record that only clears slot 1's commit CRC
decodes as:

```text
slot_status: [valid, uncommitted]
active_generation: 88
fallback_used: true
```

The actual record remains `[valid, valid]` with no fallback. No generation-89
checkpoint left the first durable CRC-clear step on the retained medium. This
does not prove the checkpoint syscall was never entered; it rejects a torn or
partially committed later checkpoint under the exact ordered writer protocol.

## Retained-log layout rejects in-run header drift

The checkpoint writer also returns `-ESTALE` before CRC clear if the Samsung
retained-log header no longer exactly matches its seed `idx` and `boot_cnt`.
That was initially a serious alternative: one ordinary printk after the seed
would advance `idx` and make every later checkpoint fail silently at the
userspace abort wrapper.

The exact retained bytes close it.

The observer payload is 2,097,136 bytes, exactly the Samsung ring payload
after its 16-byte header. `__log_buf_copy_to_buffer()` emits a wrapped full
ring in chronological order by copying from `idx % size` to the end and then
from the start to the cursor (`sec_log_buf_main.c:209-230`).

The candidate record is written immediately behind the seed cursor without
advancing `idx` (`candidate.patch:637-709`). In the retained payload:

```text
record start     1,647,270
record size              45
suffix size         449,821
total             2,097,136
```

The identity is exact:

```text
1,647,270 + 45 + 449,821 = 2,097,136
```

The first byte after the record starts:

```text
PM: Driver Init # SPMI Transn: 664
** XBL(3579, warm reset, valid magic) **
```

The XBL marker begins 37 bytes after the record and explicitly identifies the
next warm-reset boot. There are 13,255 Samsung kernel timestamp prefixes in
the retained payload and zero after the record. The target DT selects
`sec,strategy = <3>`, the VH-logbuf implementation, which writes a timestamp
and process prefix before each accepted new printk record. The kernel log
writer's only persistent-header mutation is `idx += count`; it does not change
`boot_cnt`.

Consequently the first indexed bytes after the seed are next-boot firmware
bytes. There was no indexed Samsung log write during the candidate interval.
The header `idx` remained equal to `seed_idx` until the operator-initiated
reboot, after the 300-second observation. Header-drift `-ESTALE` cannot explain
the missing in-run generation 89.

The exact next-stage contract independently accepts all restart outcomes that
the P2.86 runtime can intentionally publish at generation 89:

```text
0xc52, 0xc53, 0xc54,
0xc57, 0xc58, 0xc59, 0xc5a, 0xc5b,
0xc5c
```

Ordinary negative syscall errors through `0x7ff` are also accepted. Previous
88 commits, exact stage progression, and the stable header make a spontaneous
proc-checkpoint rejection substantially less parsimonious than a
pre-publication block.

## Ranked interpretation

1. **Highest-priority, live-unproved: the first restart tracefs snapshot did
   not return.** It is the first unbounded primitive after the exact last
   checkpoint, it is inherited unchanged from P2.84, and it executes before
   any P2.86 restart-helper evidence. A stall would produce exactly the
   observed record and no ACM. Exact source proves the unbounded lock/RCU path,
   not that a particular lock or grace period stalled live.
2. **Possible: PERIPHERAL helper dispatch occurred, its write wedged, and the
   post-helper trace snapshot suppressed the bounded result.** The helper
   parent itself would escape after at most the restart deadline plus the
   one-second reap window. Absence of `0xc53/0xc57/0xc58/0xc59` then requires
   the unmarked refresh before classification to block or an equally early
   publication failure.
3. **Possible but later: a child-status, mode-readback, UDC, trace-loop, or
   final-capture syscall blocked after a successful helper return.** The
   userspace deadlines do not preempt those reads, and `0xc5c` is after all of
   them.
4. **Unsupported residual: scheduler-wide/kernel hang, unexpected userspace
   park, or transient memory corruption before generation 89.** The retained
   format cannot mathematically exclude arbitrary transient corruption, but
   there is no affirmative evidence for it.
5. **Rejected: parent status was never suspended.** P2.86 publishes the
   retained `0xc18` only after that exact match.
6. **Rejected: final trace cleanup swallowed the result.** Successful restart
   reaches `0xc5c` before cleanup; abort reaches a terminal publish before
   cleanup. Neither record exists.
7. **Rejected: an ordinary bounded helper timeout alone.** Once the
   post-helper refresh returns, the exact classifier attempts a generation-89
   failure.
8. **Rejected: a torn/lost generation-89 slot or in-run retained-header
   drift.** Both slots remain committed, and the raw ring adjacency proves no
   indexed write before the next boot.

The result does not justify naming `synchronize_rcu`, `trace_types_lock`, or
the USB flush as the live root cause. It does justify moving the next
discriminator before all three.

## Why static/fault validation missed this

The P2.86 source contract correctly requires:

- timeout classification before bounded reap;
- terminal publish before abort-path trace cleanup;
- final trace capture before parsing;
- `0xc5c` before final unregister/cleanup; and
- a pre-dispatch refresh before freezing `residual_outer_open`.

The last requirement made the newly discovered gap mandatory. The AArch64
fault harness proved that an injected infinite `p282_trace_finish()` after
`p282_cycle_abort()` cannot suppress a terminal checkpoint. It did not inject
a block into:

- the first restart `p282_cycle_refresh()`;
- the second refresh before helper classification;
- a sysfs read inside a deadline loop; or
- `p286_cycle_capture()` before `0xc5c`.

The tests proved the local order they asserted. They did not prove that every
path from the last progress record to the next publication was bounded.

## Successor design constraints

No P2.88 implementation is selected by this report. A source-complete
successor design must satisfy all of the following before intent derivation:

1. place an attributable durable boundary before the first restart tracefs
   open/read;
2. never put a trace refresh, trace cleanup, blocking reap, or blocking sysfs
   read between a completed/timed-out helper observation and its failure
   publication;
3. treat a userspace deadline checked after a blocking syscall as
   non-preemptive, not bounded;
4. place a durable boundary before final trace disable/snapshot/profile
   capture, not merely before unregister cleanup;
5. fault-inject permanent blocks independently into the pre-dispatch trace
   snapshot, post-helper snapshot, child-status read, mode read, final capture,
   and cleanup;
6. preserve the two-slot evidence budget so the last two records remain the
   most diagnostic pair; and
7. explicitly solve the stage-sequence problem.

The current retained ABI permits one monotonic publication at stage `0x90`.
Moving `0xc5c` to restart entry would consume that stage and prevent a later
stage-`0x90` failure. Multiple early boundaries therefore require a reviewed
stage/ABI redesign, a separately bounded evidence channel, or removal of the
unbounded operation—not merely one additional detail constant.

The cheapest first design question is whether restart diagnostics need a
pre-dispatch trace snapshot at all. If they do, it must be isolated so its
failure cannot block PID1's durable progress. If they do not, helper dispatch
and its bounded outcome should precede optional trace enrichment.

## Host validation

The focused H0 checks established:

- current/frozen P2.86 source receipts: `70/70`, changed keys `[]`;
- exact retained reads: byte-identical, expected SHA256;
- exact record offset and ring-size identity;
- zero Samsung kernel timestamp prefixes after the record;
- exact next-boot XBL adjacency;
- actual decode: both slots valid, no fallback;
- simulated next-slot commit clear: one uncommitted slot and fallback;
- all reachable generation-89 P2.86 restart details accepted by the exact
  contract;
- no blocking child-specific `wait4`;
- bounded main helper and reap loops under clock failure;
- finite trace parser loops; and
- exact tracefs snapshot open/read lock and RCU synchronization paths.

Final documentation validation also passes `git diff --check`, all referenced
report paths exist, `GOAL.md` is 311 lines, and the frozen/current source
receipts remain `70/70` with changed keys `[]`. Only these three documentation
paths enter the scoped commit.

No D0, D1, F1 manifest, approval, live run, or replay is created. P2.86 remains
closed and immutable.
