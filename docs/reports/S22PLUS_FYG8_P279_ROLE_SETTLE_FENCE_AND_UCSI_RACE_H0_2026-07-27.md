# S22+ FYG8 P2.79 role-settle fence and UCSI race analysis

Date: 2026-07-27 KST
Tier: H0
Status: `FOCUSED_ANALYSIS_COMPLETE`
Device contact: none

## Question

P2.78 left one bounded candidate direction:

```text
initial role
  -> none
  -> peripheral
  -> bounded settle
  -> exact UDC bind
  -> configured/high-speed observation
```

This unit resolves three design questions before that direction is implemented:

1. Is there an existing parent-visible completion fence for DWC3-MSM
   `sm_work`, instead of a blind settle delay?
2. Does the new delay require a larger Process v2 observer window?
3. Can UCSI race the explicit `none` transition by reasserting DEVICE?

The source-backed result is:

```text
existing stable userspace completion fence: none found
fixed ROLE_SETTLE delay: timing slack only, not proof
current observer bound: 180 seconds, not the retired 120 seconds
next observer bound: must be regenerated after the exact wait budget is fixed
UCSI DEVICE reassertion: structurally possible
one failed none readback: not sufficient to attribute the source to UCSI
none observed and then lost before candidate peripheral write:
  proves an external role producer, with UCSI the leading source
```

## Boundary and Method

This is host-only, read-only source analysis. It performs no build, image
generation, candidate mutation, D0, approval, transaction, reboot, flash, or
device write.

The analysis uses:

- the exact P2.76 runtime and private timing receipts;
- the matching FYG8 DWC3-MSM, generic DWC3, UDC, UCSI, and IPC-logging source;
- the exact FYG8 DT overlay and module order already reconstructed in P2.78;
  and
- the P2.76 ready2 manifest and observation-margin report.

## A. Parent Completion Fence

### Parent sysfs exposes inputs, not completion

The matching FYG8 `dwc3-msm-core.c` registers exactly four parent attributes:

```text
orientation
mode
speed
bus_vote
```

`mode_show()` derives its answer only from `vbus_active` and `id_state`.
`mode_store()` updates those fields and returns after
`dwc3_ext_event_notify()` has queued the new `sm_work`. It does not wait for
that new work to complete.

`speed_show()` explicitly reports the maximum supported DWC3 speed, not the
current operating speed. `orientation` and `bus_vote` do not encode role-work
completion.

The two load-bearing completion fields are internal:

```text
mdwc->drd_state
mdwc->in_device_mode
```

The source exposes neither as sysfs, a role-switch getter, nor another stable
userspace ABI.

### Child and UDC attributes are not parent fences

The child role-switch getter reports `dwc->current_dr_role`. The parent start
path updates that child role near the end of
`dwc3_otg_start_peripheral()`, but this is not a direct readback of the parent
work item and the child defaults to DEVICE for the applicable NONE/default
case.

The UDC attributes report:

```text
state         = gadget bus state
current_speed = negotiated gadget speed
```

They become informative after pull-up and host bus activity. They are valid
end-to-end USB evidence, but not a pre-bind fence for parent role-work
completion.

### Debug and IPC evidence

The generic DWC3 `link_state` debugfs file reads controller link state and
runtime-resumes the controller. It is a terminal diagnostic with side effects,
not a stable parent completion fence.

DWC3-MSM emits:

```text
StrtGdgt gsync
StopGdgt psync
```

The latter is emitted after the body of `dwc3_otg_start_peripheral()` for both
start and stop calls. It could identify completion only with an exact
transition-specific baseline and ordered marker sequence.

That IPC path is not dependable in the current target posture. The IPC core
returns one shared dummy context when Samsung debug is disabled and the dummy
context already exists. In that case the per-device `a600000_ssusb` debugfs
context is not created. Marker absence is therefore unavailable evidence, not
failure.

### Synchronization already provided by the second write

There is one useful conditional source-level fence inside the planned
transition:

1. the `none` write queues the stop-side `sm_work`;
2. the later `peripheral` write reaches `dwc3_ext_event_notify()`; and
3. `dwc3_ext_event_notify()` calls `flush_delayed_work(&mdwc->sm_work)` before
   updating inputs and queueing the new peripheral work.

Therefore a candidate `peripheral` request that reaches
`dwc3_ext_event_notify()` serializes completion of the preceding `none` work.
A separate blind dwell for stop completion is unnecessary.

This is conditional, not proof that the candidate's write performed the
flush. UCSI can reassert DEVICE in the short interval before that write. The
candidate call can then take the same-role no-op, while the UCSI call performs
the flush and queues the DEVICE work through the same callback. In both cases
the desired parent path is scheduled, but current evidence cannot attribute
the scheduling call to PID1 versus UCSI.

The new peripheral work remains asynchronous after that write returns. No
existing stable userspace fence for that final work was found.

### Disposition

Do not claim a true `ROLE_SETTLE` fence without new kernel instrumentation.
For the next minimal candidate:

- keep one dedicated fixed settle budget after the final peripheral write;
- do not reuse the current early-exit role/UDC loop as the settle mechanism;
- describe the budget as timing slack that cannot prove worker completion;
- keep IPC and `link_state` optional diagnostics only; and
- use configured/high-speed plus the armed host sidecar as the actual
  end-to-end result.

Adding a new kernel-owned read-only completion attribute would create a real
fence, but it also expands the kernel/module change and qualification surface.
It is not justified before one correctly discriminated minimal candidate.

## B. UDC Lifetime Across `none`

The parent stop path clears VBUS override, connection state, PHY/redriver
notifications, and `in_device_mode`. It does not call `dwc3_gadget_exit()` and
does not remove the registered UDC.

The generic child role-switch maps NONE/default to DEVICE when the configured
default is not HOST. At this stage the configfs gadget has not yet been bound.

The existing E3 runtime also revalidates all established E2 gates while waiting
at the later configured stage. An unexpected UDC disappearance is already
represented as the current frontier stage plus the existing UDC regression
detail.

Disposition:

```text
new UDC-disappearance stage: reject
post-cycle UDC revalidation: retain
unexpected disappearance: existing regression semantics
```

## C. UCSI Reassertion Race

### Exact producer path

The FYG8 overlay connects the UCSI connector graph to the parent
`a600000.ssusb` role switch. UCSI:

1. obtains that role switch from the connector fwnode;
2. maps a DFP partner to `USB_ROLE_DEVICE`; and
3. calls `usb_role_switch_set_role()`.

The parent switch callback invokes the same `dwc3_msm_set_role()` used by
`mode_store()`. Registration and connector-change work can therefore issue a
DEVICE request independently of PID1.

### Observable cases

A successful candidate `none` write followed by one `peripheral` read does not
identify UCSI. It can mean:

- the DP-active branch returned success without applying NONE;
- UCSI or another producer reasserted DEVICE before readback; or
- an unexpected path/read error was collapsed.

A stronger bounded discriminator is:

```text
write none
  -> require exact none at least once
  -> sample for a short fixed stability interval
  -> candidate has not yet written peripheral
```

Interpretation:

| Observation | Supported conclusion |
|---|---|
| NONE is never observed | NONE was not established; DP no-op and immediate external reassertion remain distinct possibilities |
| NONE is observed and remains stable | candidate established a bounded NONE interval; no permanent exclusion of a later producer |
| NONE is observed, then DEVICE appears before candidate peripheral write | an external role producer is proved; UCSI is the leading source but not uniquely proved |
| HOST appears | unexpected external HOST assertion; stop |
| read/path error | path or validation failure; do not classify as a role producer |

Use structured detail under the existing role stage. Do not add a new stage
only for this race, and do not label the external-producer case `UCSI_PROVED`
unless independent UCSI evidence is also captured.

The stability interval is a discriminator for external reassertion, not a
completion fence. The subsequent role request that actually reaches
`dwc3_ext_event_notify()` flushes the prior NONE work before queueing the new
peripheral work. That may be the candidate request or a racing UCSI DEVICE
request.

## D. Observation Window

The active P2.76 ready2 manifest uses:

```text
observation.timeout_sec = 180
```

The 120-second value belongs to retired ready1. The old 180-second model was:

```text
120 seconds conservative pre-E3 allowance
+ 45 seconds explicit E3 waits
+ 15 seconds margin
= 180 seconds
```

P2.76 exhausted the full 180-second observer window. Its retained checkpoint
has no timestamp, so that run does not reveal when stage `0x8f` was reached and
does not provide a measured positive margin.

The next manifest must be generated only after the exact NONE stability and
ROLE_SETTLE budgets are fixed. For example, with a 1-second NONE stability
window and a 30-second final-role slack replacing the old 5-second role loop,
the explicit E3 wait ceiling becomes approximately:

```text
5 tty + 5 banner + 1 none stability + 30 role slack + 30 configured = 71 sec
```

The same conservative model then requires at least `120 + 71 + 15 = 206`
seconds. A rounded 240-second observer bound is the recommended design value:

- it preserves additional synchronous-operation margin;
- it remains below the 300-second transient udev-guard lifetime; and
- the P2.76 host overhead before observation was about 17 seconds, leaving
  roughly 43 seconds before that guard deadline.

This is a data-only manifest choice after candidate qualification. It does not
justify changing the existing runner or observer schema.

## Design Inputs

The next design should preserve these constraints:

1. capture initial role;
2. write NONE and require bounded exact evidence;
3. distinguish never-established NONE from observed-then-reasserted NONE;
4. forbid HOST writes;
5. write peripheral exactly once;
6. use a dedicated non-short-circuiting role-settle slack;
7. revalidate exact parent role, UDC membership, and earlier gates;
8. keep gadget composition, module closure, firmware, and reconnect unchanged;
9. require a durably armed host kernel/udev trace before F1;
10. keep optional IPC/link-state evidence non-fatal; and
11. regenerate the immutable manifest with a recalculated observer bound.

No F1 is authorized by this report.
