# S22+ FYG8 post-P2.96 gadget-start return attribution (H0)

Date: 2026-08-03

## Verdict

`PASS_POST_P296_GADGET_START_RETURN_SELECTED_H0`

Follow-up design gates:

- `PASS_P296_FULL_LTO_GADGET_START_CALLSITE_OUT_OF_LINE_H0`; and
- `PASS_CANDIDATE_PID1_BIND_TRACE_PLACEMENT_H0`.

The earliest source-level predicate not resolved by P2.96 is the signed return
from built-in `__dwc3_gadget_start()`. The exact FYG8
`dwc3_gadget_pullup(true)` caller ignores that return and then overwrites its
local `ret` with the later `dwc3_gadget_run_stop(..., true)` result. A failed
EP0 start can therefore coexist with the P2.96 observations
`DCTL.RUN_STOP=1`, `DSTS.DEVCTRLHLT=0`, and UDC `not attached`/`UNKNOWN`.

The selected next discriminator is one matched entry/return trace pair for
`__dwc3_gadget_start()` inside the existing bind-phase trace window. Event and
PHY observations remain downstream and are not selected yet.

This was host-only source and evidence analysis. It performed no build,
package, manifest, transfer, reboot, flash, or device contact. S22+ received
zero commands, and the concurrent A90 worktree paths were neither read as S22+
evidence nor modified.

## Immutable source and evidence replay

The analysis re-pinned the exact P2.96 identity before interpreting the result:

- profile `E2`;
- source contract
  `s22plus-fyg8-p296-builtin-dwc3-telemetry-v1`;
- all `113/113` immutable `SOURCE_KEYS` matched the candidate intent;
- the selected Tier-1 source set had zero intersection with current worktree
  changes; and
- the exact run patch remained 32,353 bytes with SHA256
  `81986794755b1763ec4dce99521a12c72f9b91bb90f86dbabd3ce697c98889e4`.

The source-matched built-in `gadget.c` is SHA256
`c121003d37f4fc9ab951f5d8811fe32736b21dadab985214996606578160c730`.
The P2.96 Full-LTO `vmlinux` and `System.map` are respectively SHA256
`3fc474a73e742ce924e45f49a3f5faf2293296cd573d49d4f5bc1e3b5207ef52`
and
`ab89f13bf6c2538aac45b193c885e03002438b5a90985c6a789a3682e5e72e16`.

The two post-rollback retained reads were replayed through the exact P2.96
decoder. They remained byte-identical, decoded as `E2_FAILURE_OBSERVED`, and
contained one integrity-clean terminal sequence:

- generation 106, stage `0x92`, detail `0x0c60`: `USBLNKST=0`; then
- generation 107, stage `0x93`, detail `0x0c72`:
  `digital-control-state-nominal-not attached-UNKNOWN-coreidle-1-susphy-0`.

No source mutation, retained-record ambiguity, or integrity failure was found.

## What the P2.96 tuple does and does not say

P2.96 samples DCTL, DSTS, GCTL, and GUSB2PHYCFG immediately after the
successful run-stop poll. Its bind trace is then closed and classified. The
runtime separately polls UDC `state` and `current_speed` until a stable success
or the 30-second final deadline, and only then publishes the adjacent retained
pair.

That timing creates two distinct observations:

1. immediate post-run-stop `USBLNKST=0`, `RUN_STOP=1`, `DEVCTRLHLT=0`,
   `COREIDLE=1`, device PRTCAP, and `SUSPHY=0`; and
2. later stable sysfs UDC `not attached` and `current_speed=UNKNOWN`.

The terminal word `UNKNOWN` is the sysfs UDC speed. It is not the raw
`DSTS.CONNECTSPD` field. P2.96 did capture raw `CONNECTSPD`, but its classifier
compares that field only when the sysfs speed is nonzero. With sysfs
`UNKNOWN`, the raw value is not encoded in the retained detail and cannot be
recovered from generation 107.

`USBLNKST=0` is source-defined as U0 for SuperSpeed and ON for High Speed. In
this tuple it is not proof of enumeration, a negotiated speed, a host reset,
or descriptor traffic. `COREIDLE=1` reports core idle, not event delivery.
`SUSPHY=0` also cannot prove whether `dwc3_enable_susphy()` ran because the
exact helper clears the USB2 SUSPHY bit when `dis_u2_susphy_quirk` is set.

## Exact control-flow proof

The source-matched `dwc3_gadget_pullup(true)` path is:

```text
vdwc->softconnect = true
pm_runtime_get_sync() > 0
dwc3_core_soft_reset()              return checked
dwc3_event_buffers_setup()
__dwc3_gadget_start()               return ignored
  __dwc3_gadget_ep_enable(ep0-out)  may return error
  __dwc3_gadget_ep_enable(ep0-in)   may return error
  dwc3_ep0_out_start()
  dwc3_gadget_enable_irq()
  dwc3_enable_susphy(true)
dwc3_gadget_run_stop(true)          result overwrites ret
  pullups_connected = true
  DCTL.RUN_STOP = 1
  poll DSTS.DEVCTRLHLT == 0
return run-stop result
```

If either EP0 enable fails, `__dwc3_gadget_start()` returns before
`dwc3_ep0_out_start()`, `dwc3_gadget_enable_irq()`, and
`dwc3_enable_susphy(true)`. The caller still invokes run-stop. A later
run-stop return zero therefore proves the DCTL write and cleared controller
halt bit, but it does not prove that EP0 start or device-event enable completed.

The exact source has no separate DCTL soft-disconnect bit. The ordinary
disconnect path clears `DCTL.RUN_STOP`; conversely this P2.96 snapshot has
source-established `softconnect=true`, `pullups_connected=true`, and
`RUN_STOP=1`. This closes a lingering software soft-disconnect explanation at
the snapshot while leaving physical cable/VBUS facts unproved.

The event path is strictly downstream. Only the success tail of
`__dwc3_gadget_start()` enables RESET, CONNECT_DONE, DISCONNECT, and related
device events. `dwc3_process_event_entry()` emits the built-in `dwc3_event`
tracepoint before dispatching RESET or CONNECT_DONE. A missing event is thus
not interpretable until gadget-start success is established.

## Hypothesis disposition

| Candidate predicate | P2.96/source disposition | Decision |
|---|---|---|
| Software session/VBUS request | The inherited P2.92 prefix proves start-peripheral and notify-connect; the exact wrapper writes UTMI VBUS-valid. Physical VBUS remains unproved. | Not the earliest unknown |
| Pullup or software disconnect | `softconnect=true`, `pullups_connected=true`, `RUN_STOP=1`, and `DEVCTRLHLT=0`; the exact source has no independent DCTL soft-disconnect bit. | Closed at the snapshot |
| Gadget/EP0 start | Its return is ignored and can fail before EP0 receive setup, DEVTEN, and SUSPHY programming while run-stop still succeeds. | **Earliest open predicate** |
| Device-event generation or event-buffer handling | Requires the gadget-start success tail to have enabled the relevant events. P2.96 also ends its bind trace immediately after bind. | Deferred until start return is zero |
| PHY/link training | `USBLNKST=0`, `COREIDLE=1`, and `SUSPHY=0` do not prove an electrical attach or negotiated speed. | Deferred until start return is zero |

This conclusion agrees with the earlier P2.80 evidence correction, which
already recorded that `__dwc3_gadget_start()` was invoked without its return
being consumed. P2.96 makes that known source gap the lowest unresolved branch
rather than introducing a new speculative root cause.

## Selected boot-deliverable observable

The exact P2.96 `System.map` contains the built-in local text symbol:

```text
ffffffc008e3b128 t __dwc3_gadget_start
```

The same kernel enables `CONFIG_EVENT_TRACING`, `CONFIG_TRACING`,
`CONFIG_FTRACE`, and `CONFIG_KPROBE_EVENTS`. P2.96 already proved the dynamic
kprobe/kretprobe mechanism on other built-in static DWC3 functions. The next
contract can therefore add exactly one nested pair without any external
`dwc3-msm.ko` dependency:

```text
p:.../__dwc3_gadget_start_in  __dwc3_gadget_start
r:.../__dwc3_gadget_start_out __dwc3_gadget_start rc=$retval:s32
```

The pair must be matched to the one pullup-on invocation and precede the
run-stop entry in the same authoritative bind trace. Its interpretation is
closed:

- `rc < 0`: prove an early gadget/EP0 initialization failure and terminalize
  before any physical-link claim, preserving the exact errno or a freshly
  declared typed detail;
- `rc == 0`: prove both EP0 enable calls returned zero and control reached
  EP0 receive setup, DEVTEN enable, and the SUSPHY helper call; only then may a
  later unit select event or PHY evidence; and
- a missing, duplicated, out-of-order, or unpaired entry/return: classify a
  trace-source contradiction, never assume success.

This is a pre-final gate, so it requires no third retained slot. A future
implementation must preserve the 45-byte two-slot ABI, the P2.96 adjacent A/B
publication rule, the full P2.92 prefix, and the Stage-C identity split.

## Full-LTO call-site closure

The P2.96 intent patches
`kernel_platform/common/drivers/usb/dwc3/gadget.c`. The same checkout's
`kernel_platform/msm-kernel/drivers/usb/dwc3/gadget.c` mirror is byte-identical;
both have the pinned `gadget.c` SHA256 above. The machine-code conclusion below
comes from the actually linked P2.96 `vmlinux`, so it does not depend on which
mirror name is used when quoting the source.

Both reproducible kernels have `CONFIG_LTO=y`, `CONFIG_LTO_CLANG=y`, and
`CONFIG_LTO_CLANG_FULL=y`. Repro A and B have byte-identical `vmlinux` and
`System.map` files. GNU AArch64 disassembly of both files produced the same
normalized call-site excerpt, SHA256
`a5962f0ec420039e1ee2eef5ffa90c20d2730c49a22a0f22f4b5b2b79ea65af1`.

The direct pullup-on branch is:

```text
dwc3_gadget_pullup+0x100  bl  __dwc3_gadget_start
dwc3_gadget_pullup+0x104  mov w1, #1
dwc3_gadget_pullup+0x108  mov x0, x19
dwc3_gadget_pullup+0x10c  bl  dwc3_gadget_run_stop
dwc3_gadget_pullup+0x110  mov w21, w0
```

This proves the exact P2.96 call is not inlined or redirected to a clone. It is
an actual `bl` to the out-of-line local text symbol. No instruction consumes
the first call's `w0`; `mov x0, x19` destroys it before run-stop, and only the
second call's `w0` is saved.

The independent resume call site supplies the machine-code control:

```text
dwc3_gadget_resume+0x28  bl    __dwc3_gadget_start
dwc3_gadget_resume+0x2c  tbnz  w0, #31, error
```

The same linked function return is checked in resume and dropped in pullup.
The kretprobe target is therefore valid for this exact Full-LTO pair.

This proof is not transferable to a future build. Every future Full-LTO A/B
qualification must disassemble the actual linked pair and fail closed unless:

1. both A and B contain exactly one direct pullup-path `bl` to the exact
   `__dwc3_gadget_start` symbol;
2. that call lies after event-buffer setup and before direct run-stop;
3. no instruction consumes or branches on its return before the return is
   overwritten; and
4. the A/B normalized call-site excerpts are identical.

An inlined, cloned, tail-called, missing, or A/B-divergent form is a host
qualification failure. Symbol presence alone must never substitute for this
call-site proof or silently fall back to the proposed kretprobe.

## Candidate-runtime trace placement

The trace controller belongs inside the boot-only candidate, not stock Android
or the post-rollback baseline. The exact P2.96 candidate proves the reusable
placement:

- its static ramdisk `/init` is 66,384 bytes with SHA256
  `52bccd74613cc74326e9df0edb5345fa9559000d70bcfb12ffca7d5b4068631f`;
- the candidate builder replaces ramdisk `init`, re-extracts it from the final
  boot image, and requires byte equality with that binary;
- `_start()` parks unless it is PID 1, then reaches `p290_e3_run()`;
- `p290_e3_run()` reaches `p282_phase_bind()` after the one stop, suspend, and
  restart sequence;
- `p282_phase_bind()` arms the isolated tracefs instance immediately before
  the one `p260_bind_udc()` call, then disables, snapshots, profiles, and
  removes the probes immediately after that bind returns; and
- the bind parser rejects every trace record whose PID is not exactly 1.

The current bind descriptor has seven events. The future descriptor adds only
the `__dwc3_gadget_start` entry and signed-return events, raising that exact
bind count to nine while remaining below the existing 16-event control bound.
The required runtime order is:

```text
candidate static /init as PID 1
  -> trace setup, registration readback, filters, clear, enable
  -> pull_in(on=1)
     -> gadget_start_in
     -> gadget_start_out(rc=$retval:s32)
     -> run_in(on=1)
        -> one built-in state snapshot
     -> run_out
  -> pull_out
  -> trace disable, snapshot, zero-missed-hit profile, cleanup
  -> bind classification
  -> only on gadget-start rc==0, enter final UDC polling
```

Exactly one start pair must be nested inside the selected direct pullup pair
and strictly precede the selected direct run-stop pair. Any extra, missing,
unpaired, different-PID, out-of-order, or kprobe-profile-missed record is a
trace-source contradiction. A negative return is the selected early failure;
zero is the only success gate; a positive return is also a source
contradiction rather than implicit success.

The P2.96 retained built-in snapshot already proves that this candidate-owned
trace setup, bind window, readback, parser, and cleanup path executed on the
live candidate. Stock Android does not contain this replacement PID1 or arm
these dynamic events. A stock D0 or rollback boot therefore cannot answer the
candidate-path return question.

## Causal limit

The discarded-return branch completely reconciles the observed P2.96 tuple
with an EP0-start failure. It does not yet prove that either EP0 enable actually
failed in that run; a zero gadget-start return followed by a later event or PHY
failure remains source-compatible. Only the selected candidate-runtime return
pair can promote the explanation into an observed cause.

## Next bound and authority

The call-site and runtime-placement design is closed. The next unit remains H0:
implement the two-event descriptor, exact PID/counter pairing, exhaustive
classifier outcomes, and mandatory post-Full-LTO call-site audit. Do not name,
build, package, manifest, or run a successor candidate from this report alone.

Any payload-affecting implementation starts with a fresh complete
`SOURCE_KEYS` identity, qualification, Full-LTO A/B, boot-only closure, and
review for changed execution-critical hashes before connected work. The
consumed P2.96 intent, token, prepared binding, journal, and candidate remain
historical and non-reusable. This H0 verdict grants no D0, D1, or F1 authority.
