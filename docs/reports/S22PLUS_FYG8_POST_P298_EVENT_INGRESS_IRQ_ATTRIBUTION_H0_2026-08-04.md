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
4. the raw event-dispatch boundary, retaining device-event records while using
   the pre-filter profile count to distinguish an empty pass from a
   non-device event pass.

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
  r32 return from dwc3_interrupt
  rc=$retval:s32
  filter: common_pid >= 0

thread_in
  dwc3_thread_interrupt
  evt=%x1 dwc=+40(%x1) evt_count=+24(%x1):u32 evt_flags=+28(%x1):u32
  filter: common_pid >= 0

device_event_in
  dwc3_process_event_entry
  dwc=%x0 raw=+0(%x1):u32 low=+0(%x1):u8
      type=+0(%x1):b4@8/32
  filter: common_pid >= 0 && low == 1
  trigger: traceoff:1 if type == 2
```

The all-context top-half filter is mandatory. A hard IRQ inherits whichever
task it interrupted, including PID 0, so P2.98's ordinary
`common_pid > 0` filter must not be copied to `irq_in` or `irq_out`. The
threaded and runtime-resume paths normally have a positive task PID, but
`thread_in` is also deliberately all-context so its profile count and retained
records can be compared without a PID-filter ambiguity.

The return probe is fixed to `r32:p282/irq_out`. The actual P2.98 A/B
configuration has `CONFIG_PREEMPT=y` and `CONFIG_NR_CPUS=32`.
`dwc3_interrupt()` is nonrecursive, does not sleep, and belongs to the one
Waipio DWC3 instance. The hardware IRQ path is serialized by the IRQ core, and
the pending-event resume path disables that IRQ before its direct call. A
32-instance pool therefore covers the per-CPU concurrency bound without
depending on the kernel's implicit kretprobe default. Any nonzero `nmissed`
still invalidates the observer.

`device_event_in` filters on low byte 1. This retains all DWC3 device events
while excluding endpoint and other non-device union members from the trace
records. Its kprobe profile hit count increments before that filter is tested.
When the CONNECT_DONE cutoff did not fire, the difference between the complete
profile hit count and the retained device records is therefore the exact
non-device event count. It is named `nondevice`, not `endpoint`, because the
same union also contains generic-event members. The parser independently
checks the complete raw mask and requires the fetched four-bit `type` to agree
with `(raw >> 8) & 0xf`.

`thread_in` records the source-verified offsets `evt->count == 24` and
`evt->flags == 28`; `DWC3_EVENT_PENDING` is bit 0. With no cutoff, every
pending nonzero count contributes exactly `count / 4` entries to
`dwc3_process_event_entry()`. The summed count must equal the unfiltered
profile hits. A thread entry with zero count or without the pending bit is an
empty pass. A pending nonzero count with no corresponding profile hits is an
observer contradiction, not `THREAD_EMPTY_PASS`.

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

## Trace-integrity and cutoff contract

P3.00 does not inherit P2.98's fixed 64-record bind parser. The final trace
file is read incrementally and parsed line by line with constant aggregate
state. A bounded line buffer is permitted only with a source-derived maximum
for these exact event formats; an overlong or partial line is a distinct
observer failure. There is no fixed total-record ceiling in the bind parser.

The first CONNECT_DONE record invokes the event-local post-trigger
`traceoff:1 if type == 2`. Kernel source marks `traceoff` as a post-trigger, so
the matching CONNECT_DONE record is committed before tracing stops. Setup must
first clear the trace, set `tracing_on=1`, enable the event group, and only then
arm and read back the trigger at `count=1`. This prevents probe hits before the
recording window from incrementing `nhit` without records.

Finalization reads the remaining trigger count, removes and verifies the
trigger while the event group is still enabled, reads `tracing_on`, disables
the group, then writes `tracing_on=0`. In the no-cutoff case it requires
remaining count 1 and the post-removal tracing state 1. A CONNECT_DONE result
requires the post-removal tracing state 0. Remaining count 0 proves an earlier
firing; remaining count 1 plus final tracing state 0 is the explicitly
accepted close-race where the post-trigger fired between the count read and
removal. It is accepted only with the retained CONNECT_DONE record and every
ring/parser predicate. Remaining count 0 with tracing state 1 is impossible
and rejected. Thus neither a count alone nor `tracing_on == 0` alone proves
firing.

Ring integrity is independent of parser capacity. P3.00 must validate the
trace header's `entries-in-buffer/entries-written` relationship and every
online per-CPU stats file, requiring zero `overrun`, zero `commit overrun`, and
zero `dropped events`. The instance `overwrite` option is set and read back
explicitly. Any loss is an observer failure even when a useful-looking USB
record survived.

The kprobe profile counter is global to the installed probe and increments
before event filters and before the traceoff state is tested. The resulting
relations are therefore:

- every profile row is present, every `nmissed` is zero, and every profile hit
  count is greater than or equal to its retained-record count;
- when the CONNECT_DONE cutoff did not fire, the all-context `irq_in`,
  `irq_out`, and `thread_in` events require exact profile/record equality;
- in that same no-cutoff case, `device_event_in` profile hits equal the summed
  `evt_count / 4`, and profile hits minus retained device records is the exact
  non-device count;
- PID-filtered prefix and snapshot events are validated by their required
  record sequence and the monotone profile relation, not false equality; and
- after a proved cutoff, profile-record deltas carry no USB meaning because
  probes remain installed while tracing is off. They are used only as lower
  bounds until cleanup.

Every exact no-cutoff profile relation additionally requires the durable
runtime state that the recording window closed in the order above. A missing
window-close proof is an observer contradiction, even if the numerical profile
and record counts happen to match.

Thus a high-volume successful enumeration cannot invalidate itself merely by
continuing after CONNECT_DONE, while a missing trace record, lost return
instance, ring overwrite, malformed stream, or impossible profile relation
cannot be relabelled as a device conclusion.

## Same-F1 result contract

Every valid terminal A/B family must imply all of the following: trace setup
and registration succeeded, gadget-start returned zero, both EP0 enable calls
were observed, the event configuration was valid, all controller/event-buffer
pointers agreed, every IRQ entry had one ordered return, the explicit
`r32` pool had zero missed instances, the cutoff/profile/ring contract above
held, and trigger plus probe cleanup was verified. Earlier setup checkpoints
may be overwritten by the adjacent two-slot final publication only because
those implications move into the final family.

The exact Waipio target has one controller, `dwc3@a600000`. The MTP, QRD, CDP,
and RUMI sources modify that same node; they do not instantiate a second DWC3.
P3.00 therefore pairs the unadorned `irq_out` return with the immediately open
`irq_in`, but makes the prerequisite explicit: every `irq_in`, `thread_in`,
and device record must carry the one snapshot `evt`/`dwc` identity, no foreign
entry may appear, and top-half calls must be strictly nonnested and one-to-one.
Any violation is an observer contradiction.

The A record encodes link state in the low nibble plus exactly one
highest-information ingress class. The allocation is complete, not deferred:

| Detail family | Ingress class | Exact meaning |
|---|---|---|
| `0xD00-0xD0F` | `NO_TOP_COUNT_ZERO` | Configuration was valid; the immediate count was zero; no matching top-half entry was observed. Later event generation versus IRQ delivery remains open. |
| `0xD10-0xD1F` | `NO_TOP_COUNT_NONZERO` | A hardware event count was already nonzero, but no matching top-half entry was observed; the boundary moves to IRQ delivery/handler invocation. |
| `0xD20-0xD2F` | `TOP_NONE_ONLY` | Matching top-half call(s) returned only `IRQ_NONE`. A shared IRQ may have belonged to another source. |
| `0xD30-0xD3F` | `HANDLED_NO_WAKE` | A matching call returned `IRQ_HANDLED`, but no later `IRQ_WAKE_THREAD`, thread entry, or raw event appeared. |
| `0xD40-0xD4F` | `WAKE_NO_THREAD` | A matching call returned `IRQ_WAKE_THREAD`, but no matching threaded-handler entry followed. |
| `0xD50-0xD5F` | `THREAD_EMPTY_PASS` | At least one matching thread path ran, every such pass had zero count or no pending bit, and no raw entry was dispatched. |
| `0xD60-0xD6F` | `THREAD_NONDEVICE_ONLY` | A pending nonzero thread pass dispatched one or more raw entries, but all were filtered non-device union members. |
| `0xD70-0xD7F` | `DEVICE_OTHER_ONLY` | One or more valid device events arrived, but neither RESET nor CONNECT_DONE did. The exact other type is not retained in the two-slot ABI. |
| `0xD80-0xD8F` | `RESET_NO_CONNECT_DONE` | RESET reached raw dispatch, but CONNECT_DONE did not. |
| `0xD90-0xD9F` | `CONNECT_DONE_NO_RESET` | CONNECT_DONE reached raw dispatch without an earlier RESET. Failure is downstream of connection-done dispatch. |
| `0xDA0-0xDAF` | `RESET_AND_CONNECT_DONE` | Both RESET and CONNECT_DONE reached raw dispatch in a source-consistent order. Failure is downstream of connection-done dispatch. |

This is exactly `0xB0 == 176 == 11 * 16` values. It does not overlap the
unchanged final-state B family `0xE00-0xE83`. RESET presence in a CONNECT_DONE
result is mandatory and cannot be discarded for space.

The inherited observer details remain `0xF60-0xF72`. P3.00 reserves the
currently free `0xF73-0xF7F` values, one each, for conditional-trigger setup,
trigger-state contradiction, trace-stream read failure, overlong/malformed
line, ring overwrite/drop, invalid event configuration, foreign pointer,
IRQ pairing/order, IRQ return-domain, thread-snapshot, raw-event,
profile-relation, and final-classification contradictions. Existing fixed
controller mismatch values start at `0xF80`, so this allocation is disjoint.

Impossible ordering, nested/unpaired IRQ records, a return outside `{0,1,2}`,
pointer mismatch, a raw device event without the required upstream path,
duplicate snapshots, filter/trigger/readback disagreement, stream truncation,
ring loss, nonzero missed count, or cleanup failure is an observer
contradiction. None may be relabelled as a USB or device conclusion.

The immediate GEVNTCOUNT snapshot is not a terminal register sample. A zero
value proves only that no count was pending at that instant. If the final class
is `NO_TOP_COUNT_ZERO`, one conditional follow-up may still be required to
separate later event generation from IRQ delivery. That residual is planned,
not silently treated as a completed root cause.

## Same-F1 host USB sidecar

The existing private-only
`workspace/public/src/scripts/revalidation/device_action_usb_trace_sidecar_v1.py`
is selected as the passive observer for the same attended F1 window. The
current P3.00 core pins its exact Tier-3 source but does not yet integrate or
launch it. Before F1 readiness, a host-only integration must bind its
start/end receipts, kernel journal, udev monitor, and bounded `lsusb` snapshots
to the exact campaign ID, attempt ID, candidate hash, and durable Process-v2
journal interval. It must start before candidate transfer and close only after
candidate observation is durable. It never opens the candidate ACM endpoint,
sends a device command, or grants authority.

The sidecar is not a gate 0 and does not replace the device observer. It makes
the result a diagnostic matrix without consuming another F1:

| Host USB evidence | Device ingress evidence | Meaning |
|---|---|---|
| present | present | correlate host enumeration stage with RESET/CONNECT_DONE ingress |
| present | absent | narrow to device physical/ingress delivery after host activity |
| absent | present | host logging/visibility or post-ingress response path remains open |
| absent | absent | move to the earliest type-C/extcon/PHY or host-attach boundary |

Only an integrity-clean sidecar may populate the host axis. A sidecar failure
leaves that axis `UNKNOWN`; it does not erase an integrity-clean retained
P3.00 device result or get encoded as a device failure.

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

## Built-in-only 16th-slot audit

The actual P2.98 A/B `System.map` and configuration contain built-in
`dwc3_set_mode`, `usb_udc_vbus_handler`, `usb_gadget_vbus_connect`,
`extcon_get_state`, and the generic QCOM DWC3 support. None is a sound 16th
P3.00 event:

- the exact Waipio node uses the vendor `qcom,dwc-usb3-msm` wrapper;
- its `vbus_active`, role derivation, VBUS notifier, and
  `dwc3_msm_notify_event()` live in external `dwc3-msm.ko`, absent from the
  A/B `vmlinux` symbol table;
- the generic built-in helper symbols do not expose that wrapper state and are
  not guaranteed to execute in the bind-to-final observation window; and
- `dwc3_set_mode` would duplicate the already retained GCTL PRTCAP state rather
  than establish connector or VBUS presence.

P3.00 therefore stays at 15 of 16 events and preserves one spare slot. Before
any no-host/no-ingress follow-up is designed, H0 must first prove that its
exact connector/role/VBUS target is linked into `vmlinux` and executes in the
candidate window. An external `dwc3-msm.ko` target repeats P2.94's delivery
blocker and must stop before packaging; the boot-only lane does not inject a
replacement module.

## Implementation gates

The next work is H0 implementation only:

1. derive fresh P3.00 transform, schema, streaming parser, decoder, source
   contract, and tests without changing any P2.98 `SOURCE_KEY` byte;
2. implement the fixed `0xD00-0xDAF` and `0xF73-0xF7F` allocations above;
3. execute focused registration, trigger, recording-window, cleanup, ordering,
   pointer, raw-mask, line/header parser, and profile-relation faults; retain
   source-order plus integrated-compile validation for ring-stat, aggregate
   stream-count, and `nmissed` readback predicates;
4. validate `r32`, the actual filters, the conditional post-trigger and its
   count transition through the tracefs fixture;
5. cross-compile the generated userspace and run the focused regressions;
6. bind the existing passive host USB sidecar into the future same-F1 timeline;
7. obtain a fresh independent review because trace/schema/parser, trigger and
   built-in snapshot machinery change; and
8. only after fresh qualification, two clean Full-LTO builds, linked A/B
   audit, package/rollback closure, exact D0, and attended presence may a later
   step prepare F1.

This report grants no live authority and creates no candidate identity.
