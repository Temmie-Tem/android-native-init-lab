# S22+ FYG8 post-P2.98 event-ingress and IRQ attribution (H0)

Date: 2026-08-04

## Verdict

`PASS_POST_P298_EVENT_INGRESS_IRQ_SELECTED_H0`

P2.98 proved one successful `__dwc3_gadget_start()` return, both ordered EP0
enable calls, the direct run-stop result, and a healthy rollback. The earliest
unresolved interval is now between successful gadget-start and a processed
RESET or CONNECT_DONE device event.

The selected successor is P3.00,
`s22plus-fyg8-p300-event-ingress-irq-attribution-v1`. It must classify one
candidate run across the following ordered boundaries:

1. event-buffer and DEVTEN programming at successful run-stop;
2. entry and return from the DWC3 IRQ top half;
3. entry into the threaded IRQ handler; and
4. the first device-specific raw event before dispatch.

This was host-only source and linked-binary analysis. It performed no package,
manifest, transfer, reboot, flash, connected read, or other device action.
S22+ received zero commands, and the concurrent A90 files were not modified or
used as S22+ evidence.

## Exact source chain

The source-matched `common/` and `msm-kernel/` copies of `gadget.c` are
byte-identical at SHA-256
`c121003d37f4fc9ab951f5d8811fe32736b21dadab985214996606578160c730`.
Their `core.c` copies are also byte-identical at SHA-256
`77db45ab1091f37dd935fcd827309b898bb3866b4e09e3f9751cdfaa542dd4e3`.

The successful source path is:

```text
dwc3_event_buffers_setup(dwc)
  evt = dwc->ev_buf
  GEVNTADRLO/HI = evt->dma
  GEVNTSIZ = evt->length
  GEVNTCOUNT = 0

__dwc3_gadget_start(dwc)
  enable EP0-OUT
  enable EP0-IN
  dwc3_ep0_out_start(dwc)
  dwc3_gadget_enable_irq(dwc)
    DEVTEN includes USBRSTEN and CONNECTDONEEN
  dwc3_enable_susphy(dwc, true)

dwc3_gadget_run_stop(dwc, true)
  DCTL.RUN_STOP = 1
  wait for DSTS.DEVCTRLHLT = 0
```

`dwc3_event_buffers_setup()` returns zero even when `dwc->ev_buf` is null, so
its return alone is not a useful discriminator. The earlier successful
`request_threaded_irq(..., IRQF_SHARED, "dwc3", dwc->ev_buf)` path makes a null
shared-IRQ identity unlikely, but it does not prove the later MMIO programming
remained correct. P3.00 therefore reads back the configuration directly while
runtime PM is still held.

The IRQ source path is:

```text
dwc3_interrupt(irq, evt)
  dwc3_check_event_buf(evt)
    runtime suspended                         -> IRQ_HANDLED (1)
    DWC3_EVENT_PENDING already set            -> IRQ_HANDLED (1)
    (GEVNTCOUNT & 0xfffc) == 0                 -> IRQ_NONE (0)
    count > 0; cache and acknowledge event(s)  -> IRQ_WAKE_THREAD (2)

dwc3_thread_interrupt(irq, evt)
  dwc3_process_event_buf(evt)
    dwc3_process_event_entry(dwc, raw)
      device event type 1 -> dwc3_gadget_reset_interrupt(dwc)
      device event type 2 -> dwc3_gadget_conndone_interrupt(dwc)
```

If the first top-half call occurs while runtime suspended, the source sets
`pending_events`, requests resume, disables the IRQ, and returns 1. Runtime
resume later calls both `dwc3_interrupt()` and `dwc3_thread_interrupt()`
directly before clearing `pending_events` and re-enabling the IRQ. P3.00 must
therefore parse an ordered sequence of 0/1/2 returns rather than assume one
hardware IRQ produces exactly one top-half record.

## Raw device-event decoding

The exact event union is a little-endian 32-bit word. Bit 0 marks a
device-specific event, bits 1 through 7 must be zero for a DWC3 device event,
and bits 8 through 11 hold its type. RESET and CONNECT_DONE therefore have
base low patterns `0x101` and `0x201`; event-info bits may make the complete
word larger. The classifier must decode with masks, never compare the complete
word to only those two constants.

The built-in `dwc3_event` tracepoint is not selected as the sole observer.
Although its prototype receives `struct dwc3 *`, its trace record stores only
the raw event and EP0 state. It cannot attribute a record to the exact P2.98
controller pointer, and it occurs only after the threaded path has already
been reached. An entry probe on `dwc3_process_event_entry()` supplies both the
exact `dwc` and raw word at the earliest dispatch boundary.

## Exact Full-LTO evidence

The read-only P2.98 Full-LTO A/B pair is byte-identical. Each `vmlinux` is
476,979,440 bytes at SHA-256
`3067680949754f7c5bd418136bc8c21cc9522f55aa8394a666fa0b21e1a2968d`.
Both contain the same local-text symbols:

```text
ffffffc008e37564 t dwc3_interrupt
ffffffc008e37584 t dwc3_thread_interrupt
ffffffc008e3770c t dwc3_process_event_buf
ffffffc008e37c3c t dwc3_process_event_entry
ffffffc008e3a8d4 t dwc3_check_event_buf
```

Disassembly proves:

- `dwc3_interrupt()` makes one direct call to `dwc3_check_event_buf()` and
  returns its `w0` unchanged;
- `dwc3_thread_interrupt()` directly calls `dwc3_process_event_buf()` with the
  event-buffer pointer;
- `dwc3_process_event_buf()` loads `evt->dwc`, reads one raw cache word, and
  directly calls `dwc3_process_event_entry(dwc, &event)`; and
- the device-event switch inside `dwc3_process_event_entry()` directly calls
  the out-of-line RESET and CONNECT_DONE handlers.

`dwc3_gadget_interrupt()` itself has no out-of-line Full-LTO symbol and is not
a valid dynamic-probe target. P3.00 deliberately avoids it. It also avoids an
instruction-offset probe at the common `dwc3_check_event_buf()` epilogue:
register allocation differs across the count and tracepoint cold paths, so an
apparently convenient return-edge register tuple is not a stable source
contract.

Future P3.00 Full-LTO A/B must repeat this proof on the actual linked pair.
Symbol presence alone is insufficient. Inline, clone, tail-call, missing,
return-transforming, or A/B-divergent forms fail closed.

## Selected 15-event observer

P2.98 has 12 bind events and a fixed cycle capacity of 16. P3.00 keeps the ten
events through `ep_enable_in`, removes the now-subsumed RESET and CONNECT_DONE
handler entries, and adds these five events:

```text
event_config
  s22_p300_dwc3_event_config_snapshot
  dwc=%x0 evt=%x1 devten=%x2 gevntsiz=%x3 gevntcount=%x4
  evt_length=%x5 evt_count=%x6 evt_flags=%x7
  filter: common_pid > 0

irq_in
  dwc3_interrupt
  evt=%x1 dwc=+40(%x1)
  filter: common_pid >= 0

irq_out
  return from dwc3_interrupt
  rc=$retval:s32
  filter: common_pid >= 0

thread_in
  dwc3_thread_interrupt
  evt=%x1 dwc=+40(%x1)
  filter: common_pid > 0

device_event_in
  dwc3_process_event_entry
  dwc=%x0 raw=+0(%x1):u32 low=+0(%x1):u8
  filter: common_pid > 0 && low == 1
```

The all-context top-half filter is mandatory. A hard IRQ inherits whichever
task it interrupted, including PID 0, so P2.98's ordinary
`common_pid > 0` filter must not be copied to `irq_in` or `irq_out`. The
threaded and runtime-resume paths have a positive task PID.

`device_event_in` filters on low byte 1. This retains all DWC3 device events
while excluding potentially numerous endpoint events from the bounded
64-record buffer. The parser still validates the complete raw mask and exact
profile hit count.

The new noinline built-in snapshot helper will be called beside the existing
post-run-stop snapshot, before the pullup path drops its runtime-PM reference.
Its eight register arguments preserve the exact controller and event-buffer
pointers plus DEVTEN, GEVNTSIZ, GEVNTCOUNT, `evt->length`, `evt->count`, and
`evt->flags`. It will perform three read-only MMIO reads and no write. A valid
configuration requires:

- nonzero `dwc` and `evt`, matching every later attributed record;
- event-buffer length 4096;
- DEVTEN RESET and CONNECT_DONE bits set; and
- GEVNTSIZ size bits equal to the event-buffer length.

GEVNTSIZ INTMASK, GEVNTCOUNT, software count, and pending flags are recorded
but not required to be zero. A host event can race immediately after RUN_STOP
and legitimately change them before the snapshot. The ingress classifier uses
`gevntcount & 0xfffc`; the separate EHB bit is never treated as an event count.

## Same-F1 result contract

Every valid terminal A/B family must imply all of the following: trace setup
and registration succeeded, gadget-start returned zero, both EP0 enable calls
were observed, the event configuration was valid, all controller/event-buffer
pointers agreed, every IRQ entry had one ordered return, profile missed counts
were zero, trace records equaled profile hits, and cleanup was verified.
Earlier setup checkpoints may be overwritten by the adjacent two-slot final
publication only because those implications move into the final family.

The A record encodes link state plus exactly one highest-information ingress
class:

| Ingress class | Exact meaning |
|---|---|
| `NO_TOP_COUNT_ZERO` | Configuration was valid; the immediate count was zero; no matching top-half entry was observed. Later event generation versus IRQ delivery remains open. |
| `NO_TOP_COUNT_NONZERO` | A hardware event count was already nonzero, but no matching top-half entry was observed; the boundary moves to IRQ delivery/handler invocation. |
| `TOP_NONE_ONLY` | Matching top-half call(s) returned only `IRQ_NONE`; each sampled call read zero event count. A shared IRQ may have belonged to another source. |
| `HANDLED_NO_WAKE` | A matching call returned `IRQ_HANDLED`, but no later `IRQ_WAKE_THREAD` or device event appeared; runtime-suspended versus already-pending handling is the next narrow branch. |
| `WAKE_NO_THREAD` | A matching call returned `IRQ_WAKE_THREAD`, but no matching threaded-handler entry followed. |
| `THREAD_NO_DEVICE_EVENT` | The matching thread path ran, but no device-specific raw event was recorded; an endpoint-only event or empty pending pass remains possible. |
| `DEVICE_OTHER_ONLY` | One or more device events arrived, but neither RESET nor CONNECT_DONE did. The retained raw type set supplies the next discriminator. |
| `RESET_NO_CONNECT_DONE` | RESET reached raw dispatch, but CONNECT_DONE did not. |
| `CONNECT_DONE` | CONNECT_DONE reached raw dispatch, with RESET presence retained as a sub-bit if space permits. Failure is downstream of event ingress and connection-done dispatch. |

Impossible ordering, nested/unpaired IRQ records, a return outside `{0,1,2}`,
pointer mismatch, a raw device event without the required upstream path,
duplicate snapshots, filter/readback disagreement, buffer overflow, nonzero
missed count, or cleanup failure is an observer contradiction. None may be
relabelled as a USB or device conclusion.

The immediate GEVNTCOUNT snapshot is not a terminal register sample. A zero
value proves only that no count was pending at that instant. If the final class
is `NO_TOP_COUNT_ZERO`, one conditional follow-up may still be required to
separate later event generation from IRQ delivery. That residual is planned,
not silently treated as a completed root cause.

## Rejected or secondary observers

- Generic DWC3 `regdump` is not load-bearing. Its debugfs read calls
  `pm_runtime_get_sync()` and can wake or perturb the controller being
  diagnosed.
- The static `dwc3_event` tracepoint lacks the exact controller pointer in its
  stored fields and starts too far downstream.
- `/proc/interrupts` can be optional corroboration, but its Linux IRQ number is
  dynamic and the line is shared; it cannot replace the attributed entry and
  return pair.
- `SUSPHY=0` is not selected as a failure predicate. The exact Waipio child has
  `snps,dis_u2_susphy_quirk`, so the source intentionally clears USB2 SUSPHY.
- P2.96 remains the historical no-probe behavioral baseline. No dedicated
  control F1 is planned unless prefix/tuple drift, a probe contradiction, a
  health anomaly, or a new hazard reopens it.

## Implementation gates

The next work is H0 implementation only:

1. derive fresh P3.00 transform, schema, parser, decoder, source contract, and
   tests without changing any P2.98 `SOURCE_KEY` byte;
2. allocate exact 12-bit detail families for the nine ingress classes and all
   observer failures; 148 was a prior-domain count, not an ABI ceiling;
3. fault-test all registration, no-reach, ordering, pointer, raw-mask,
   overflow, missed-hit, readback, and cleanup branches;
4. validate the actual filter strings through the tracefs fixture;
5. cross-compile the generated userspace and run the focused regressions;
6. obtain a fresh independent review because trace/schema/parser and the
   built-in snapshot helper change; and
7. only after fresh qualification, two clean Full-LTO builds, linked A/B
   audit, package/rollback closure, exact D0, and attended presence may a later
   step prepare F1.

This report grants no live authority and creates no candidate identity.
